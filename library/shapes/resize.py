"""Blender: take a generated model, make it real size, stand it on the floor facing front, save every format.
blender -b -P resize.py -- in.glb biggest_side_m out_dir name"""
import os
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
src, big, out, name = a[0], float(a[1]), a[2], a[3]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects:
    o.select_set(o in meshes)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not ob:
        bpy.data.objects.remove(o)
ob.name = ob.data.name = name
pts = [v.co for v in ob.data.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
s = big / max(hi - lo)
for v in ob.data.vertices:                                 # real size, centered, sitting on the floor
    v.co = Vector(((v.co.x - (lo.x + hi.x) / 2) * s, (v.co.y - (lo.y + hi.y) / 2) * s, (v.co.z - lo.z) * s))
ob.data.update()
bpy.ops.object.shade_smooth()
base = os.path.join(out, name)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saveall                                             # noqa: E402  library/shapes/saveall.py

saveall.blend(out, name)                                   # every picture packed inside the .blend: it opens anywhere
bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format="GLB", use_selection=False)
saveall.rest(out, name, "resize", selected=False)          # .fbx (pictures inside) + .usdc + made.json
print("size m:", [round(x, 4) for x in (hi - lo) * s])
