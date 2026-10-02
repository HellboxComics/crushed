"""Hunyuan3D 2.1 (Tencent), Apple-chip (MLX) version, for soft and odd shapes: one clean photo -> a 3D shape ->
real surface paint (color + metal/roughness maps, 4096 px). Runs in its own folder and Python (set up by the
setup paste) so it never disturbs anything else.

    <hunyuan folder>/.venv/bin/python library/hunyuan.py photo.png out_dir [--shape-only]

Writes out_dir/shape.glb (bare shape) and out_dir/textured.glb (painted). Settings are the ones the Apple-chip
build was checked with (50 steps, 6 views at 512 px, remeshed to about 40,000 faces before painting)."""
import gc
import os
import sys
import time

FOLDERS = ["~/.hellbox/hunyuan3d-mlx", "~/.hellbox/hunyuan21-mlx"]


def home():
    for f in FOLDERS:
        f = os.path.expanduser(f)
        if os.path.exists(os.path.join(f, "hy3dshape")):
            return f
    return None


def main(photo, out, shape_only=False):
    hy = home()
    if not hy:
        sys.exit("Hunyuan3D is not installed (looked in " + ", ".join(FOLDERS) + ")")
    photo, out = os.path.abspath(photo), os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    os.chdir(hy)                                    # its settings files are found from its own folder
    sys.path[:0] = [os.path.join(hy, "hy3dshape"), os.path.join(hy, "hy3dpaint"), hy]
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


if __name__ == "__main__":
    print(main(sys.argv[1], sys.argv[2], "--shape-only" in sys.argv))
