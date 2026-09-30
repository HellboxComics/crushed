"""Render the item library: every individual object, uncrushed, on the stage.

    python3 blender/catalog.py --group era --era 2 --out docs/catalog_era2.png
    python3 blender/catalog.py --group crypto --out docs/catalog_crypto.png
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

from crushed import build, crush, mat, stage  # noqa: E402
from crushed.objects import Palette, load  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="era", choices=["era", "crypto", "filler"])
    ap.add_argument("--era", type=int, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", type=int, default=1600)
    ap.add_argument("--samples", type=int, default=48)
    a = ap.parse_args(argv)

    reg = load()
    defs = [d for d in reg.values() if d.group == a.group and (a.era is None or a.era in d.eras)]
    defs.sort(key=lambda d: d.name)
    sc = stage.reset()
    rng = np.random.default_rng(7)
    mat.set_condition("JUNK")
    stage.build(sc, rng, a.res, a.samples)
    coll = bpy.data.collections.new("catalog")
    sc.collection.children.link(coll)

    n = len(defs)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cell = 0.2
    for i, d in enumerate(defs):
        pal = Palette(a.era if a.era is not None else max(d.eras), rng)
        ob = build.make_object(d, rng, pal, coll)
        v = build.prepare(ob, 0.17, rng)
        # lay the hero face toward the camera-ish (up)
        q = Vector(d.hero).rotation_difference(Vector((0, 0, 1)))
        R = np.array(q.to_matrix())
        v = v @ R.T
        v -= (v.min(axis=0) + v.max(axis=0)) / 2
        v[:, 2] -= v[:, 2].min() - 0.0015   # flat prints sit just above the floor
        crush.set_verts(ob.data, v)
        c, r = i % cols, i // cols
        ob.location = ((c - (cols - 1) / 2) * cell, ((rows - 1) / 2 - r) * cell, 0.0)
    cam = sc.camera
    el, az = math.radians(58), math.radians(20)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = d * 20
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = cell * max(cols, rows) * 1.12
    # widen the floor pool for the grid
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.data.energy *= 1.6
    floor = bpy.data.objects["floor"]
    floor.data.materials.clear()
    m = bpy.data.materials.new("catalog_floor")
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    floor.data.materials.append(m)
    sc.render.filepath = os.path.abspath(a.out)
    bpy.ops.render.render(write_still=True)
    print("[catalog]", a.group, a.era, n, "items ->", a.out)
    print(", ".join(d.name for d in defs))


if __name__ == "__main__":
    main()
