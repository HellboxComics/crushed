"""Studio pictures of a finished asset from several sides (Cycles), to check it against the real thing.

    blender -b -P preview.py -- model.glb out.png [degrees,...]"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
angles = [float(a) for a in argv[2].split(",")] if len(argv) > 2 else [0, 45, 90, 180, 270]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector([min(min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in obs) for i in range(3)])
hi = Vector([max(max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in obs) for i in range(3)])
ctr, size = (lo + hi) / 2, max(hi - lo)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 600, 800
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
for loc, e in (((2, -3, 3), 150), ((-3, -1, 2), 60), ((0, 3, 2), 80)):
    L = bpy.data.lights.new("l", "AREA"); L.energy = e * size * size * 40; L.size = size * 2
    lo_ = bpy.data.objects.new("l", L); sc.collection.objects.link(lo_)
    lo_.location = ctr + Vector(loc) * size * 1.5
    lo_.rotation_euler = (ctr - lo_.location).to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.cameras.new("c"); cam.lens = 85
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
frames = []
for a in angles:
    r = math.radians(a)
    d = size * 4.2
    co.location = ctr + Vector((math.sin(r) * d, -math.cos(r) * d, size * 0.35))
    co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
    p = out[:-4] + f"_{int(a):03d}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    frames.append(p)
print("[preview]", " ".join(frames))
