"""Hunyuan3D 2.1 (Tencent), Apple-chip (MLX) version, for soft and odd shapes: one clean photo -> a 3D shape ->
real surface paint (color + metal/roughness maps, 4096 px). Runs in its own folder and Python (set up by the
setup paste) so it never disturbs anything else.

    <hunyuan folder>/.venv/bin/python library/hunyuan.py photo.png out_dir [--shape-only]
    <hunyuan folder>/.venv/bin/python library/hunyuan.py photo.png out_dir --paint exact_shape.glb
        (paint only: our exact Blender shape keeps its true geometry; Hunyuan paints every side of it)

Writes out_dir/shape.glb (bare shape) and out_dir/textured.glb (painted). Settings are the ones the Apple-chip
build was checked with (50 steps, 6 views at 512 px, remeshed to about 40,000 faces before painting)."""
import gc
import os
import sys
import time

# Run as a script, Python looks in this folder first, so a file here named like one of Python's own modules
# (library/profile.py did: it broke torch's "import cProfile", 2026-10-02) would be loaded instead of the real
# one. Hunyuan needs nothing from this folder, so it is taken off the search list.
_HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__":                 # only when run as its own program - never when the asset maker imports it
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != _HERE]

FOLDERS = ["~/.hellbox/hunyuan3d-mlx", "~/.hellbox/hunyuan21-mlx"]


def home():
    for f in FOLDERS:
        f = os.path.expanduser(f)
        if os.path.exists(os.path.join(f, "hy3dshape")):
            return f
    return None


def paint_only(photo, out, shape):
    """Paint an exact shape we built ourselves. Its old maps are dropped so Hunyuan lays out one clean map for the
    whole object; the geometry is not touched (no remesh)."""
    import trimesh
    m = trimesh.load(shape, force="mesh")
    bare = trimesh.Trimesh(vertices=m.vertices, faces=m.faces, process=False)
    src = os.path.join(out, "exact_shape.obj")
    bare.export(src)
    t = time.time()
    from textureGenPipeline_mlx import Hunyuan3DPaintConfigMLX, Hunyuan3DPaintPipelineMLX
    paint = Hunyuan3DPaintPipelineMLX(Hunyuan3DPaintConfigMLX(max_num_view=6, resolution=512))
    obj = os.path.join(out, "textured.obj")
    paint(mesh_path=src, image_path=photo, output_mesh_path=obj, use_remesh=False, save_glb=True)
    print(f"[hunyuan] painted the exact shape in {time.time() - t:.0f}s", flush=True)
    return obj[:-4] + ".glb"


def main(photo, out, shape_only=False, paint=None):
    hy = home()
    if not hy:
        sys.exit("Hunyuan3D is not installed (looked in " + ", ".join(FOLDERS) + ")")
    photo, out = os.path.abspath(photo), os.path.abspath(out)
    paint = os.path.abspath(paint) if paint else None          # before we step into Hunyuan's folder
    os.makedirs(out, exist_ok=True)
    os.chdir(hy)                                    # its settings files are found from its own folder
    sys.path[:0] = [os.path.join(hy, "hy3dshape"), os.path.join(hy, "hy3dpaint"), hy]
    if paint:
        return paint_only(photo, out, paint)
    shape = os.path.join(out, "shape.glb")
    t = time.time()
    mesh = shape_torch(photo)                       # the original Hunyuan (PyTorch) on the Apple chip's GPU
    if mesh is not None:
        mesh.export(shape)
        print(f"[hunyuan] shape (PyTorch on the Apple GPU): {len(mesh.faces)} faces in {time.time() - t:.0f}s", flush=True)
    if mesh is None:
        mesh = shape_mlx(photo, shape)
    if shape_only:
        return shape
    gc.collect()
    t = time.time()
    from textureGenPipeline_mlx import Hunyuan3DPaintConfigMLX, Hunyuan3DPaintPipelineMLX
    paint = Hunyuan3DPaintPipelineMLX(Hunyuan3DPaintConfigMLX(max_num_view=6, resolution=512))
    obj = os.path.join(out, "textured.obj")
    paint(mesh_path=shape, image_path=photo, output_mesh_path=obj, use_remesh=True, save_glb=True)
    print(f"[hunyuan] paint done in {time.time() - t:.0f}s", flush=True)
    return obj[:-4] + ".glb"


def shape_torch(photo):
    """The original Hunyuan3D 2.1 shape model (Tencent's PyTorch code) on the Mac's GPU (Apple 'mps'). The Apple-chip
    (MLX) port returned the same surface value everywhere - even on its own demo picture (2026-10-02) - so it never
    made a shape; the original runs on the same chip, a little slower."""
    try:
        import torch
        from PIL import Image
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2.1", subfolder="hunyuan3d-dit-v2-1",
                                                                device=dev, dtype=torch.float16)
        im = Image.open(photo).convert("RGBA")
        mesh = pipe(image=im, num_inference_steps=50, guidance_scale=5.0, octree_resolution=256,
                    generator=torch.manual_seed(42))[0]
        if mesh is None or not len(mesh.faces):
            print("[hunyuan] PyTorch: empty shape", flush=True)
            return None
        return mesh
    except Exception as e:
        import traceback
        print(f"[hunyuan] PyTorch shape failed: {repr(e)[:300]}", flush=True)
        traceback.print_exc()
        return None


def shape_mlx(photo, shape):
    from hy3dshape.pipeline_mlx import ShapePipeline
    import mlx.core as mx
    mesh = None
    # Half precision (the default) is fast but can overflow into "not a number" on some photos, which leaves an
    # empty shape ("need at least one array to concatenate", the Furby, 2026-10-02). Then: full precision.
    for dtype, name in ((mx.float16, "half"), (mx.float32, "full")):
        try:
            pipe = ShapePipeline.from_pretrained("dgrauet/hunyuan3d-2.1-mlx", dtype=dtype)
            _dec = pipe.vae.decode_to_mesh

            def _checked(latents, *a, _dec=_dec, **k):          # the facts, in the log, if it goes wrong again
                l32 = latents.astype(mx.float32)
                print(f"[hunyuan] {name} precision: shape code nan={int(mx.isnan(l32).sum().item())} "
                      f"min={float(mx.min(l32).item()):.3g} max={float(mx.max(l32).item()):.3g}", flush=True)
                return _dec(latents, *a, **k)
            pipe.vae.decode_to_mesh = _checked
            _q = pipe.vae._query_sdf_volume

            def _sdf(pts, feats, n, _q=_q):                    # the surface values at each level: the facts
                import numpy as _np
                v = _q(pts, feats, n) if len(pts) else _np.zeros(0, _np.float32)
                if len(v):
                    print(f"[hunyuan] {name}: {len(v)} points, surface value min={float(v.min()):.3g} "
                          f"max={float(v.max()):.3g} inside={float((v > 0).mean()):.2f}", flush=True)
                else:
                    print(f"[hunyuan] {name}: no points near a surface at this level", flush=True)
                return v
            pipe.vae._query_sdf_volume = _sdf
            mesh = pipe(photo, num_inference_steps=50, guidance_scale=7.5, octree_resolution=256, seed=42)
            if mesh is not None and len(mesh.faces):
                break
            print(f"[hunyuan] {name} precision gave an empty shape", flush=True)
        except ValueError as e:
            print(f"[hunyuan] {name} precision gave an empty shape ({e})", flush=True)
        mesh = None
        gc.collect()
    if mesh is None:
        sys.exit("Hunyuan3D made an empty shape from this photo (PyTorch and the Apple-chip version)")
    mesh.export(shape)
    print(f"[hunyuan] shape (Apple-chip version): {len(mesh.faces)} faces", flush=True)
    return mesh


def check():
    """The self-test: load what a real build uses, exactly the way a real build does (same script, same folder, same
    imports): the original PyTorch shape maker (what makes every shape now - see shape_torch) and the Apple-chip
    painter. The Apple-chip shape port is only the fallback, so it can't fail the check; it is only reported."""
    hy = home()
    if not hy:
        sys.exit("Hunyuan3D is not installed")
    os.chdir(hy)
    sys.path[:0] = [os.path.join(hy, "hy3dshape"), os.path.join(hy, "hy3dpaint"), hy]
    import torch._dynamo  # noqa: F401  (what failed on 2026-10-02)
    from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline  # noqa: F401  (the real shape maker)
    from textureGenPipeline_mlx import Hunyuan3DPaintPipelineMLX  # noqa: F401
    try:
        from hy3dshape.pipeline_mlx import ShapePipeline  # noqa: F401  (the fallback)
    except Exception as e:
        print(f"[hunyuan] note: the Apple-chip shape fallback does not load ({repr(e)[:200]})", flush=True)
    print("ok")


def test():
    """Hunyuan on its own demo picture (does this Mac's Hunyuan make shapes at all?)."""
    hy = home()
    demo = next((os.path.join(hy, p) for p in ("assets/demo.png", "assets/example_images/004.png", "demo.png")
                 if os.path.exists(os.path.join(hy, p))), None)
    if not demo:
        import glob
        demo = (glob.glob(os.path.join(hy, "assets", "**", "*.png"), recursive=True) or [None])[0]
    print(f"[hunyuan] test picture: {demo}", flush=True)
    out = os.path.join(os.path.expanduser("~/crushed-render/remaster"), "hunyuan_test")
    print(main(demo, out, shape_only=True), flush=True)


if __name__ == "__main__":
    a = sys.argv
    if "--check" in a:
        check()
        sys.exit(0)
    if "--test" in a:
        test()
        sys.exit(0)
    print(main(a[1], a[2], "--shape-only" in a, a[a.index("--paint") + 1] if "--paint" in a else None))
