"""Hunyuan3D 2.1 (Tencent), Apple-chip (MLX) version, for soft and odd shapes: one clean photo -> a 3D shape ->
real surface paint (color + metal/roughness maps, 4096 px). Runs in its own folder and Python (set up by the
setup paste) so it never disturbs anything else.

    <hunyuan folder>/.venv/bin/python library/hunyuan.py photo.png out_dir [--shape-only]
    <hunyuan folder>/.venv/bin/python library/hunyuan.py photo.png out_dir --paint exact_shape.glb [--part label]
        (paint only: our exact Blender shape keeps its true geometry AND its UV layout; Hunyuan paints every side
         of it - the unseen side inferred from the photo; --part paints one named part of a multi-part model)

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


def paint_only(photo, out, shape, part=None):
    """Paint an exact shape we built ourselves, in ITS OWN UV layout (Hunyuan3D-Paint keeps a pre-wrapped mesh's
    UVs - its pipeline: "a hand-authored UV layout produces much cleaner textures"). The geometry is not touched.
    The WHOLE object is painted (the model is made for closed objects - 2026-10-05 21:40: an isolated open label
    sleeve came back as nonsense); a model's parts each own a 0..1 UV space, so they are packed into ONE atlas
    first: `part` (the label) takes the top half full-width, the other parts share the bottom half in a grid.
    out/atlas.json says where each part's map sits (u0, v0, u1, v1), so the caller cuts its region back out in
    the part's own layout. Writes out/textured.obj + .glb with the color map (paint_pbr.png in the Apple-chip
    build, textured.jpg in the PyTorch build)."""
    import json
    import numpy as np
    import trimesh
    m = trimesh.load(shape)
    geoms = {}
    if isinstance(m, trimesh.Scene):
        geoms = {k: g for k, g in m.geometry.items() if isinstance(g, trimesh.Trimesh)}
    else:
        geoms = {"mesh": m}
    with_uv = {k: g for k, g in geoms.items() if getattr(getattr(g, "visual", None), "uv", None) is not None
               and len(g.visual.uv) == len(g.vertices)}
    if not with_uv:
        raise RuntimeError("no part has a UV map - this build needs pre-wrapped meshes (no xatlas here)")
    main_key = None
    if part:
        keys = [k for k in with_uv if part.lower() in k.lower()]
        if not keys:
            raise RuntimeError(f"no part named like '{part}' in {shape} (parts: {', '.join(with_uv)})")
        main_key = min(keys, key=len)
    others = [k for k in with_uv if k != main_key]
    atlas = {}
    if main_key:
        atlas[main_key] = (0.0, 0.5, 1.0, 1.0)
        cols = max(1, int(np.ceil(np.sqrt(len(others))))) if others else 1
        rows = max(1, int(np.ceil(len(others) / cols))) if others else 1
        for n, k in enumerate(others):
            c, r = n % cols, n // cols
            atlas[k] = (c / cols, 0.5 * (1 - (r + 1) / rows), (c + 1) / cols, 0.5 * (1 - r / rows))
    else:
        cols = max(1, int(np.ceil(np.sqrt(len(with_uv)))))
        rows = max(1, int(np.ceil(len(with_uv) / cols)))
        for n, k in enumerate(with_uv):
            c, r = n % cols, n // cols
            atlas[k] = (c / cols, 1 - (r + 1) / rows, (c + 1) / cols, 1 - r / rows)
    V, F, UV = [], [], []
    off = 0
    for k, g in with_uv.items():
        u0, v0, u1, v1 = atlas[k]
        uv = np.asarray(g.visual.uv, dtype=float) % 1.0
        UV.append(np.stack([u0 + uv[:, 0] * (u1 - u0), v0 + uv[:, 1] * (v1 - v0)], 1))
        V.append(np.asarray(g.vertices))
        F.append(np.asarray(g.faces) + off)
        off += len(g.vertices)
    bare = trimesh.Trimesh(vertices=np.vstack(V), faces=np.vstack(F),
                           visual=trimesh.visual.TextureVisuals(uv=np.vstack(UV)), process=False)
    os.makedirs(out, exist_ok=True)
    src = os.path.join(out, "exact_shape.obj")
    bare.export(src, include_texture=True)
    json.dump({"atlas": atlas, "main": main_key, "parts": list(with_uv)}, open(os.path.join(out, "atlas.json"), "w"), indent=1)
    t = time.time()
    from textureGenPipeline_mlx import Hunyuan3DPaintConfigMLX, Hunyuan3DPaintPipelineMLX
    paint = Hunyuan3DPaintPipelineMLX(Hunyuan3DPaintConfigMLX(max_num_view=6, resolution=512))
    obj = os.path.join(out, "textured.obj")
    paint(mesh_path=src, image_path=photo, output_mesh_path=obj, use_remesh=False, save_glb=True)
    print(f"[hunyuan] painted the exact shape ({len(with_uv)} parts in one atlas"
          f"{', ' + main_key + ' on the top half' if main_key else ''}) in {time.time() - t:.0f}s", flush=True)
    return obj[:-4] + ".glb"


def main(photo, out, shape_only=False, paint=None, part=None):
    hy = home()
    if not hy:
        sys.exit("Hunyuan3D is not installed (looked in " + ", ".join(FOLDERS) + ")")
    photo, out = os.path.abspath(photo), os.path.abspath(out)
    paint = os.path.abspath(paint) if paint else None          # before we step into Hunyuan's folder
    os.makedirs(out, exist_ok=True)
    os.chdir(hy)                                    # its settings files are found from its own folder
    sys.path[:0] = [os.path.join(hy, "hy3dshape"), os.path.join(hy, "hy3dpaint"), hy]
    if paint:
        return paint_only(photo, out, paint, part)
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


def _old_names_load():
    """Hunyuan3D 2.1's saved image encoder (DINOv2) uses the layer names of the transformers version it was made
    with (attention.attention.query / key / value, attention.output.dense). The transformers installed here (5.x)
    names the same layers attention.q_proj / k_proj / v_proj / o_proj, so loading stopped with "missing keys"
    (2026-10-02 log). Same weights, new names: each old name is matched to the name the model now expects."""
    import torch.nn as nn
    if getattr(nn.Module.load_state_dict, "_hellbox_renames", False):
        return
    orig = nn.Module.load_state_dict
    rules = [("attention.attention.query", "attention.q_proj"), ("attention.attention.key", "attention.k_proj"),
             ("attention.attention.value", "attention.v_proj"), ("attention.output.dense", "attention.o_proj"),
             ("attention.output.dense", "attention.out_proj"), ("attention.output.dense", "attention.output")]

    def load(self, state_dict, strict=True, *a, **k):
        want = set(self.state_dict().keys())
        if not (set(state_dict) - want):
            return orig(self, state_dict, strict, *a, **k)
        renamed, n = {}, 0
        for key, v in state_dict.items():
            if key not in want:
                for old, new in rules:
                    c = key.replace(old, new)
                    if c != key and c in want:
                        key, n = c, n + 1
                        break
            renamed[key] = v
        if n:
            print(f"[hunyuan] {n} saved layer names matched to this transformers version's names", flush=True)
        return orig(self, renamed, strict, *a, **k)
    load._hellbox_renames = True
    nn.Module.load_state_dict = load


def shape_torch(photo):
    """The original Hunyuan3D 2.1 shape model (Tencent's PyTorch code) on the Mac's GPU (Apple 'mps'). The Apple-chip
    (MLX) port returned the same surface value everywhere - even on its own demo picture (2026-10-02) - so it never
    made a shape; the original runs on the same chip, a little slower."""
    try:
        import torch
        from PIL import Image
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
        _old_names_load()
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
    """Hunyuan on its own demo picture, the WHOLE way a real build uses it: the shape, then the painter (which first
    trims the shape to about 40,000 faces). The proof is written only when both work - a shape alone once counted
    as proof, and the Furby then stopped in the painter's trim step (2026-10-03)."""
    hy = home()
    demo = next((os.path.join(hy, p) for p in ("assets/demo.png", "assets/example_images/004.png", "demo.png")
                 if os.path.exists(os.path.join(hy, p))), None)
    if not demo:
        import glob
        demo = (glob.glob(os.path.join(hy, "assets", "**", "*.png"), recursive=True) or [None])[0]
    print(f"[hunyuan] test picture: {demo}", flush=True)
    work = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
    out = os.path.join(work, "hunyuan_test")
    proof = os.path.join(work, "hunyuan_proven.json")
    if os.path.exists(proof):                       # an old proof never stands in for this test
        os.replace(proof, proof + ".before")
    os.makedirs(out, exist_ok=True)
    for old in ("shape.glb", "textured.glb", "textured.obj"):   # nothing from an earlier test counts
        if os.path.exists(os.path.join(out, old)):
            os.replace(os.path.join(out, old), os.path.join(out, old + ".before"))
    import json
    res = {"ok": False, "painted": False, "at": time.time(), "shape": "", "textured": ""}
    try:
        res["textured"] = main(demo, out)           # exactly what a build runs: the shape, then the paint
    except BaseException as e:                      # (SystemExit too) the reason goes in the proof file
        res["note"] = f"stopped: {type(e).__name__}: {e}"[:400]
        print(f"[hunyuan] the whole run stopped: {res['note']}", flush=True)
    try:
        import trimesh
        shape = os.path.join(out, "shape.glb")
        if os.path.exists(shape):
            m = trimesh.load(shape, force="mesh")
            res.update(shape=shape, faces=int(len(m.faces)),
                       shape_ok=bool(len(m.faces) > 1000 and float(min(m.extents)) > 0))
        tex = res.get("textured") or os.path.join(out, "textured.glb")
        if tex and os.path.exists(tex):
            sc = trimesh.load(tex)
            geoms = list(sc.geometry.values()) if hasattr(sc, "geometry") else [sc]
            mats = [getattr(g.visual, "material", None) for g in geoms]
            has_map = any(getattr(m, "baseColorTexture", None) is not None or getattr(m, "image", None) is not None
                          for m in mats)
            res.update(textured=tex, painted_faces=int(sum(len(g.faces) for g in geoms)), painted=bool(has_map))
        res["ok"] = bool(res.get("shape_ok") and res.get("painted"))
        res.setdefault("note", "proven: made and painted a real shape from its own demo picture" if res["ok"] else
                       "not proven: " + ("the shape came out empty" if not res.get("shape_ok") else
                                         "the painter made no color map"))
    except Exception as e:
        res["note"] = res.get("note") or f"no proof: {e}"
    json.dump(res, open(proof, "w"), indent=1)
    print(f"[hunyuan] proof: {res['note']} (shape {res.get('faces', 0)} faces, painted {res.get('painted')})",
          flush=True)


if __name__ == "__main__":
    a = sys.argv
    if "--check" in a:
        check()
        sys.exit(0)
    if "--test" in a:
        test()
        sys.exit(0)
    print(main(a[1], a[2], "--shape-only" in a, a[a.index("--paint") + 1] if "--paint" in a else None,
               a[a.index("--part") + 1] if "--part" in a else None))
