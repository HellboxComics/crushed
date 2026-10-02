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
    from hy3dshape.pipeline_mlx import ShapePipeline
    pipe = ShapePipeline.from_pretrained("dgrauet/hunyuan3d-2.1-mlx")
    mesh = pipe(photo, num_inference_steps=50, guidance_scale=7.5, octree_resolution=256, seed=42)
    mesh.export(shape)
    print(f"[hunyuan] shape: {len(mesh.faces)} faces in {time.time() - t:.0f}s", flush=True)
    del pipe, mesh
    gc.collect()
    if shape_only:
        return shape
    t = time.time()
    from textureGenPipeline_mlx import Hunyuan3DPaintConfigMLX, Hunyuan3DPaintPipelineMLX
    paint = Hunyuan3DPaintPipelineMLX(Hunyuan3DPaintConfigMLX(max_num_view=6, resolution=512))
    obj = os.path.join(out, "textured.obj")
    paint(mesh_path=shape, image_path=photo, output_mesh_path=obj, use_remesh=True, save_glb=True)
    print(f"[hunyuan] paint done in {time.time() - t:.0f}s", flush=True)
    return obj[:-4] + ".glb"


def check():
    """The self-test: load both halves exactly the way a real build does (same script, same folder, same imports)."""
    hy = home()
    if not hy:
        sys.exit("Hunyuan3D is not installed")
    os.chdir(hy)
    sys.path[:0] = [os.path.join(hy, "hy3dshape"), os.path.join(hy, "hy3dpaint"), hy]
    import torch._dynamo  # noqa: F401  (what failed on 2026-10-02)
    from hy3dshape.pipeline_mlx import ShapePipeline  # noqa: F401
    from textureGenPipeline_mlx import Hunyuan3DPaintPipelineMLX  # noqa: F401
    print("ok")


if __name__ == "__main__":
    a = sys.argv
    if "--check" in a:
        check()
        sys.exit(0)
    print(main(a[1], a[2], "--shape-only" in a, a[a.index("--paint") + 1] if "--paint" in a else None))
