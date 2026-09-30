"""CRUSHED generator.

Runs either inside Blender or with the `bpy` module from PyPI:

    blender -b -P blender/generate.py -- --token 44
    python3 blender/generate.py --token 44 --res 2048 --samples 128
    python3 blender/generate.py --range 1 100 --res 768
    python3 blender/generate.py --token 44 --turntable 96
    python3 blender/generate.py --manifest
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from crushed import build, recipe  # noqa: E402

ROOT = os.path.dirname(HERE)


def metadata(r, image_uri, animation_uri=None):
    attrs = [
        {"trait_type": "Era", "value": r["era"]},
        {"trait_type": "Condition", "value": r["condition"]},
        {"trait_type": "Weight (lb)", "value": r["weight_lb"], "display_type": "number"},
    ]
    if r["clean"]:
        attrs.append({"trait_type": "Finish", "value": r["clean"][0]})
    m = {"name": r["name"], "image": image_uri, "attributes": attrs}
    if animation_uri:
        m["animation_url"] = animation_uri
    return m


def render_token(tid, out, res, samples, turntable=0, save_blend=False):
    r = recipe.recipe(tid)
    t0 = time.time()
    sc = build.build(r, res=res, samples=samples, turntable=turntable)
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, f"{tid:04d}")
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(stem + ".blend"), compress=True)
    t1 = time.time()
    if turntable:
        fdir = stem + "_frames"
        os.makedirs(fdir, exist_ok=True)
        sc.render.filepath = os.path.abspath(os.path.join(fdir, "f_"))
        bpy.ops.render.render(animation=True)
    else:
        sc.render.filepath = os.path.abspath(stem + ".png")
        bpy.ops.render.render(write_still=True)
    print(f"[crushed] #{tid:04d} {r['condition']:<9} {r['era']} build {t1 - t0:.1f}s render {time.time() - t1:.1f}s"
          f" crypto={r['crypto']}", flush=True)
    return r


def write_manifest(out):
    rows = []
    for tid in range(1, recipe.SUPPLY + 1):
        r = recipe.recipe(tid)
        rows.append({k: r[k] for k in ("id", "era", "condition", "heroes", "crypto", "tape_loops", "seed",
                                         "weight_lb")} | {"finish": r["clean"][0] if r["clean"] else None})
    blob = json.dumps({"collection_seed": recipe.COLLECTION_SEED, "tokens": rows}, sort_keys=True,
                      separators=(",", ":")).encode()
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "manifest.json"), "wb") as f:
        f.write(blob)
    digest = hashlib.sha256(blob).hexdigest()
    with open(os.path.join(out, "provenance.txt"), "w") as f:
        f.write(f"0x{digest}\n")
    counts = {}
    for row in rows:
        counts[row["condition"]] = counts.get(row["condition"], 0) + 1
    print(json.dumps(counts, indent=1))
    print("contaminated:", sum(1 for row in rows if row["crypto"]))
    print("provenance: 0x" + digest)


def write_metadata(out, base_image_uri, base_anim_uri=None):
    os.makedirs(out, exist_ok=True)
    for tid in range(1, recipe.SUPPLY + 1):
        r = recipe.recipe(tid)
        anim = f"{base_anim_uri}/{tid:04d}.mp4" if base_anim_uri else None
        with open(os.path.join(out, str(tid)), "w") as f:
            json.dump(metadata(r, f"{base_image_uri}/{tid:04d}.png", anim), f, indent=1)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", type=int, nargs="*")
    ap.add_argument("--range", type=int, nargs=2)
    ap.add_argument("--out", default=os.path.join(ROOT, "renders"))
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--turntable", type=int, default=0, help="frames for a 360 turn")
    ap.add_argument("--blend", action="store_true", help="also save the .blend")
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--metadata", metavar="IMAGE_BASE_URI")
    ap.add_argument("--anim-base", metavar="ANIM_BASE_URI")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args(argv)

    if a.manifest:
        write_manifest(os.path.join(ROOT, "collection"))
    if a.metadata:
        write_metadata(os.path.join(ROOT, "collection", "metadata"), a.metadata, a.anim_base)
    ids = list(a.token or [])
    if a.range:
        ids += list(range(a.range[0], a.range[1] + 1))
    for tid in ids:
        if a.skip_existing and os.path.exists(os.path.join(a.out, f"{tid:04d}.png")):
            continue
        render_token(tid, a.out, a.res, a.samples, a.turntable, a.blend)


if __name__ == "__main__":
    main()
