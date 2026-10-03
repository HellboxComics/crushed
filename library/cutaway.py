"""A cutaway picture: a quarter of the object cut away so the insides show (checks that what's inside is right).
    python cutaway.py -- model.glb out.png
Rendered next to its place and swapped in only when whole; ends with an error code if no picture was made."""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], os.path.abspath(argv[1])
tmp = out[:-4] + ".part.png"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not obs:
    print(f"[cutaway] FAILED: {src} has no mesh parts")
    sys.exit(1)
lo = Vector([min(min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in obs) for i in range(3)])
hi = Vector([max(max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in obs) for i in range(3)])
ctr, size = (lo + hi) / 2, max(hi - lo)
bpy.ops.mesh.primitive_cube_add(size=1)
cut = bpy.context.active_object
cut.scale = (size, size, size * 2)
cut.location = (ctr.x + size / 2, ctr.y - size / 2, ctr.z)          # the front-right quarter goes
cut.hide_render = True
for o in obs:
    m = o.modifiers.new("cut", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cut
    m.solver = "EXACT"
    m.use_hole_tolerant = True
    m.material_mode = "INDEX"                      # the cut face shows the part's own material (black cathode, gold nail)                     # folded board with overlapping flaps is not one closed solid
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 96
sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 900, 1200
sc.view_settings.view_transform = "AgX"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.11, 0.11, 0.12, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for loc, e in (((2.5, -3, 2.5), 70), ((-3, -2, 1.5), 30), ((0, 3, 3), 40)):
    L = bpy.data.lights.new("l", "AREA"); L.energy = e * size * size * 40; L.size = size * 2
    lo_ = bpy.data.objects.new("l", L); sc.collection.objects.link(lo_)
    lo_.location = ctr + Vector(loc) * size * 1.5
    lo_.rotation_euler = (ctr - lo_.location).to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.cameras.new("c"); cam.lens = 70; cam.clip_start = size * 0.01; cam.clip_end = size * 100
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
dz = (hi.z - lo.z)
co.location = ctr + Vector((0.9, -1.4, 0.35)).normalized() * size * 1.9
co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = tmp
bpy.ops.render.render(write_still=True)
if not os.path.exists(tmp) or os.path.getsize(tmp) < 1000:
    print("[cutaway] FAILED: the render wrote no picture")
    sys.exit(1)
os.replace(tmp, out)
print("[cutaway]", out)
