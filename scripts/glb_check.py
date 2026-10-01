"""QA: open a finished .glb the way a viewer would (only what's in the file) and photograph it from 4 sides.
    python3 scripts/glb_check.py site/cube/0529.glb out.png"""
import math, sys
import bpy
from mathutils import Vector
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=src)
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.6, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.render.engine = "CYCLES"; sc.cycles.samples = 12; sc.cycles.use_denoising = True
sc.render.film_transparent = False
sc.render.resolution_x = sc.render.resolution_y = 700
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.55
import os
from PIL import Image
tiles = []
mesh = [o for o in sc.objects if o.type == "MESH"][0]
c = sum((mesh.matrix_world @ Vector(b) for b in mesh.bound_box), Vector()) / 8
for i, az in enumerate((38, 128, 218, 308)):
    a = math.radians(az); d = Vector((math.sin(a), -math.cos(a), 0.5)).normalized()
    cam.location = c + d * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    p = f"/tmp/_glbchk_{i}.png"; sc.render.filepath = p
    bpy.ops.render.render(write_still=True); tiles.append(Image.open(p))
sheet = Image.new("RGB", (1400, 1400))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 2) * 700, (i // 2) * 700))
sheet.save(out)
print("[check] faces", len(mesh.data.polygons), "->", out)
