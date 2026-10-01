"""Render the pin-up figure for the magazine covers and centerfolds from a 3D model (any .glb), several angles,
transparent background. Output: assets/slots/pinup_*.png (hashed into the collection like every slot file).

    python3 scripts/pinups.py path/to/model.glb
"""
import math
import os
import sys

import bpy
from mathutils import Vector

src = sys.argv[-1]
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "slots")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=src)
mesh = [o for o in sc.objects if o.type == "MESH"]
lo = Vector((min(min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in mesh) for i in range(3)))
hi = Vector((max(max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in mesh) for i in range(3)))
ctr, tall = (lo + hi) / 2, hi.z - lo.z
w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.3, 0.32, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6


def light(name, loc, power, color, size=1.0):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.color, l.size = power, color, size
    ob = bpy.data.objects.new(name, l)
    sc.collection.objects.link(ob)
    ob.location = Vector(loc) * tall + ctr
    ob.rotation_euler = (ctr - ob.location).to_track_quat("-Z", "Y").to_euler()
    return ob


rig = [light("key", (-1.2, -1.6, 0.6), 260, (1.0, 0.9, 0.82)), light("rim", (1.3, 1.2, 0.5), 340, (1.0, 0.55, 0.75)),
       light("fill", (1.5, -1.0, -0.2), 60, (0.75, 0.82, 1.0))]
sc.render.engine = "CYCLES"
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 640, 1280
sc.view_settings.view_transform = "AgX"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 85
cam.data.sensor_fit = "VERTICAL"
for i, yaw in enumerate((20, 38, 58, 78, 90, -30)):
    a = math.radians(yaw)
    d = tall * 4.6
    cam.location = ctr + Vector((math.sin(a) * d, -math.cos(a) * d, -tall * 0.12))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    for ob in rig:                                   # the lights turn with the camera
        pass
    sc.render.filepath = os.path.join(out, f"pinup_{i}.png")
    bpy.ops.render.render(write_still=True)
    print("[pinup]", sc.render.filepath)
