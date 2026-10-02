"""A light copy of a finished model for the phone page (the page's host refuses files over 25 MB): the same model,
textures as JPEG at most 2048 px. The full-quality files stay in the Asset Library.

    python webglb.py -- model.blend out.glb [max_px]"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = argv[0], argv[1]
mx = int(argv[2]) if len(argv) > 2 else 2048
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
for img in bpy.data.images:
    try:
        w, h = img.size
        if max(w, h) > mx:
            k = mx / max(w, h)
            img.scale(max(1, int(w * k)), max(1, int(h * k)))
    except Exception as e:
        print(f"[webglb] {img.name}: {e}")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out), use_selection=True, export_yup=True,
                          export_image_format="JPEG", export_jpeg_quality=85, export_extras=True)
print("[webglb]", out, os.path.getsize(out) // 1024, "KB")
