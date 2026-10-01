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
    fails = 0
    # every one-of-one is made of at least 10 different things, all of which exist and have a name
    from crushed import lore
    for one in recipe.ONE_OF_ONES:
        # generic debris (paper, film, shards) has no name and doesn't count as one of the ten
        names = {n for n, _ in recipe.MONOCULTURES.get(one, [])} | set(recipe.ONE_FILLERS.get(one, ()))
        missing = [n for n in names if n not in reg]
        names = {n for n in names if n in lore.NAMES}
        if missing:
            fails += 1
            print(f"FAIL one-of-one {one}: unknown or unnamed items {missing}")
        if one not in ("EMPTY", "UNCRUSHED", "SOLID GOLD") and len(names) < 10:
            fails += 1
            print(f"FAIL one-of-one {one}: only {len(names)} different items (needs 10)")
        if one not in lore.ONE_OF_ONES or one not in recipe.ONE_OF_ONE_FLAVOR:
            fails += 1
            print(f"FAIL one-of-one {one}: no lore text or flavor row")
    for n in reg:
        if n not in lore.NAMES and reg[n].group != "filler":
            fails += 1
            print(f"FAIL {n}: no display name")
    sc = stage.reset()
    coll = bpy.data.collections.new("t")
    sc.collection.children.link(coll)
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
    # the gift recipe ids the contract pins must be the ids the deck actually dealt
    import generate
    conds, _ = recipe.deck()
    for rid, name in zip(generate.GIFT_RECIPES, generate.GIFT_NAMES):
        if conds[rid - 1] != name:
            fails += 1
            print(f"FAIL gift {name}: deck has it at {conds.index(name) + 1}, generate.GIFT_RECIPES says {rid}")
    print(f"selftest: {len(reg)} objects x {seeds} seeds, {recipe.SUPPLY} recipes, {fails} failures")
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
