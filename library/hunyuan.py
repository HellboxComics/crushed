"""Hunyuan3D 2.1 (Tencent), Apple-chip (MLX) version, for soft and odd shapes: one clean photo -> a 3D shape ->
real surface paint (color, metal, roughness, 4096 px). Runs in its own folder and Python
(~/.hellbox/hunyuan3d-mlx, set up by the setup paste) so it never disturbs anything else.

    ~/.hellbox/hunyuan3d-mlx/.venv/bin/python library/hunyuan.py photo.png out_dir [--shape-only]
"""
import os
import sys
import time

HY = os.path.expanduser("~/.hellbox/hunyuan3d-mlx")
for p in (HY, os.path.join(HY, "hy3dpaint"), os.path.join(HY, "hy3dshape")):
    if p not in sys.path:
        sys.path.insert(0, p)


def shape(photo, out_glb, steps=50, octree=256):
    from hy3dshape.hy3dshape.pipeline_mlx import ShapePipeline
    pipe = ShapePipeline.from_pretrained("dgrauet/hunyuan3d-2.1-mlx")
    mesh = pipe(photo, num_inference_steps=steps, guidance_scale=7.5, octree_resolution=octree)
    mesh.export(out_glb)
    return out_glb


def paint(mesh_glb, photo, out_obj):
    from textureGenPipeline_mlx import Hunyuan3DPaintConfigMLX, Hunyuan3DPaintPipelineMLX
    pipe = Hunyuan3DPaintPipelineMLX(Hunyuan3DPaintConfigMLX(max_num_view=6, resolution=512))
    pipe(mesh_path=mesh_glb, image_path=photo, output_mesh_path=out_obj, save_glb=True)
    return out_obj[:-4] + ".glb"


if __name__ == "__main__":
    photo, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    t = time.time()
    g = shape(photo, os.path.join(out, "shape.glb"))
    print(f"[hunyuan] shape done in {time.time() - t:.0f}s: {g}", flush=True)
    if "--shape-only" not in sys.argv:
        t = time.time()
        g = paint(g, photo, os.path.join(out, "textured.obj"))
        print(f"[hunyuan] paint done in {time.time() - t:.0f}s: {g}", flush=True)
