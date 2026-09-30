"""Build every object under many seeds and push it through the whole crush pipeline.

    python3 blender/selftest.py            # no rendering; catches crashes in any object/era/seed
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from crushed import build, crush, mat, recipe, stage  # noqa: E402
from crushed.objects import Palette, load  # noqa: E402


def main(seeds=6):
    reg = load()
    sc = stage.reset()
    coll = bpy.data.collections.new("t")
    sc.collection.children.link(coll)
    fails = 0
    for name, d in sorted(reg.items()):
        for s in range(seeds):
            rng = np.random.default_rng(s)
            era = d.eras[s % len(d.eras)]
            try:
                ob = build.make_object(d, rng, Palette(era, rng), coll)
                v = build.prepare(ob, 0.17, rng)
                v = build.damage(v, rng, 1.0, keep_shape=bool(s % 2))
                nrm, t1, t2 = crush.FACES["-Y"]
                v = crush.place(v, crush.orient(rng, d.hero, nrm), nrm, (0.0, 0.0), t1, t2, 0.01, 0.08)
                v = crush.compact(v, 0.002, s)
                assert np.isfinite(v).all(), "non-finite vertices"
                crush.set_verts(ob.data, v)
                bpy.data.objects.remove(ob)
            except Exception:
                fails += 1
                print(f"FAIL {name} seed={s} era={era}")
                traceback.print_exc()
        mat._CACHE.clear()
    # every recipe must resolve and produce metadata
    for tid in range(1, recipe.SUPPLY + 1):
        r = recipe.recipe(tid)
        recipe.metadata(r, "x")
    print(f"selftest: {len(reg)} objects x {seeds} seeds, {recipe.SUPPLY} recipes, {fails} failures")
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
