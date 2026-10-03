"""A light copy of a finished model for the phone page (the page's host refuses files over 25 MB): the same model,
textures as JPEG at most 2048 px. The full-quality files stay in the Asset Library.

    python webglb.py -- model.blend out.glb [max_px]

The copy is written next to its place and swapped in only when it is whole and small enough, so an older copy is
never left looking new. Too big at 2048 px: tried again at 1024, then 512. Ends with an error code if it fails."""
import os
import sys

import bpy

LIMIT = 24 * 1024 * 1024                 # under the host's 25 MB, with room to spare

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
mx = int(argv[2]) if len(argv) > 2 else 2048
tmp = out[:-4] + ".part.glb"
size = None
for px in (mx, mx // 2, mx // 4):
    bpy.ops.wm.open_mainfile(filepath=blend)
    for img in bpy.data.images:
        try:
            w, h = img.size
            if max(w, h) > px:
                k = px / max(w, h)
                img.scale(max(1, int(w * k)), max(1, int(h * k)))
        except Exception as e:
            print(f"[webglb] {img.name}: could not shrink ({e})")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=tmp, use_selection=True, export_yup=True,
                              export_image_format="JPEG", export_jpeg_quality=85, export_extras=True)
    if not os.path.exists(tmp):
        print("[webglb] FAILED: Blender wrote no file")
        sys.exit(1)
    size = os.path.getsize(tmp)
    if size <= LIMIT:
        break
    print(f"[webglb] {size // (1024 * 1024)} MB with pictures at {px} px - too big for the phone page, trying smaller")
else:
    print(f"[webglb] FAILED: still {size // (1024 * 1024)} MB with pictures at {mx // 4} px (the host takes 25 MB)")
    sys.exit(1)
os.replace(tmp, out)
print("[webglb]", out, size // 1024, "KB")
