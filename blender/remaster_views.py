"""Four matching views of the code-built object (front, back, left, right), straight on, on white, as the starting
point for the drawing room. Every view shows the SAME object at the SAME size, so after the drawing room makes them
look real they still agree with each other, and the sculptor gets one object from four sides instead of four
different objects.

    python3 blender/remaster_views.py --name game_cart --out ~/crushed-render/remaster/views/game_cart
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

# the sculptor's layout: front looks along +Y (camera at -Y), back from +Y, left from -X, right from +X
SIDES = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (-1, 0, 0), "right": (1, 0, 0)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", type=int, default=768)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from crushed import build, models
    from crushed.objects import Palette, load
    reg = load()
    d = reg[a.name]
    sc = bpy.context.scene
    coll = bpy.data.collections.new("v")
    sc.collection.children.link(coll)
    rng = np.random.default_rng(0)
    b = build.Builder(a.name)
    specs = d.fn(b, rng, Palette(d.eras[0], rng))
    ob = b.build(coll)
    for key in b.slots:
        ob.data.materials.append(build.mat.get(specs.get(key, ("plastic", {})), rng))
    # stand it the way it is shown: its hero face toward the front camera
    hero = Vector(d.hero).normalized()
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = hero.rotation_difference(Vector((0, -1, 0)))
    bpy.context.view_layer.update()
    v = np.array([(ob.matrix_world @ x.co)[:] for x in ob.data.vertices])
    c = Vector(((v.min(0) + v.max(0)) / 2).tolist())
    ext = float(np.ptp(v, axis=0).max())
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    for loc, e in (((2, -3, 4), 3.0), ((-3, -2, 2), 1.5), ((0, 3, 3), 1.5)):
        L = bpy.data.objects.new("l", bpy.data.lights.new("l", "SUN"))
        L.data.energy = e
        L.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(L)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ext * 1.25
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    os.makedirs(a.out, exist_ok=True)
    for side, dvec in SIDES.items():
        dv = Vector(dvec)
        cam.location = c + dv * (ext * 4)
        cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(a.out, side + ".png")
        bpy.ops.render.render(write_still=True)
    print(f"[views] {a.name} -> {a.out}")


if __name__ == "__main__":
    main()
