"""CRUSHED generator.

Runs either inside Blender or with the `bpy` module from PyPI:

    blender -b -P blender/generate.py -- --token 44
    python3 blender/generate.py --token 44 --res 2048 --samples 128
    python3 blender/generate.py --range 1 100 --res 768
    python3 blender/generate.py --token 44 --turntable 96
    python3 blender/generate.py --manifest
    python3 blender/generate.py --metadata ipfs://<images-cid> [--anim-base ipfs://<video-cid>]
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


def token(tid, offset=0):
    """Token id -> its recipe. Before reveal offset is 0 and they're the same thing;
    after reveal the contract's offset decides (Crushed.recipeOf)."""
    rid = ((tid - 1 + offset) % recipe.SUPPLY) + 1
    r = recipe.recipe(rid)
    r["id"] = tid
    r["name"] = f"CRUSHED #{tid:04d}"
    return r


def render_token(tid, out, res, samples, turntable=0, save_blend=False, offset=0):
    r = token(tid, offset)
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
    print(f"[crushed] #{tid:04d} {r['condition']:<11} {r['era']} build {t1 - t0:.1f}s "
          f"render {time.time() - t1:.1f}s crypto={r['crypto']}", flush=True)
    return r


def write_manifest(out):
    """manifest.json is the whole collection, frozen. Its sha256 is the provenance hash."""
    rows = []
    for tid in range(1, recipe.SUPPLY + 1):
        r = recipe.recipe(tid)
        rows.append({"id": tid, "seed": r["seed"], "traits": dict(r["traits"]), "weight_lb": r["weight_lb"],
                     "items": r["items"], "heroes": r["heroes"], "crypto": r["crypto"]})
    blob = json.dumps({"collection": "CRUSHED", "supply": recipe.SUPPLY, "collection_seed": recipe.COLLECTION_SEED,
                       "tokens": rows}, sort_keys=True, separators=(",", ":")).encode()
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "manifest.json"), "wb") as f:
        f.write(blob)
    digest = "0x" + hashlib.sha256(blob).hexdigest()
    with open(os.path.join(out, "provenance.txt"), "w") as f:
        f.write(digest + "\n")
    write_rarity(out, rows)
    print("provenance:", digest)


def write_rarity(out, rows):
    """Trait frequencies and a statistical rarity rank (sum of 1/frequency)."""
    n = len(rows)
    freq = {}
    for row in rows:
        for k, v in row["traits"].items():
            freq.setdefault(k, {}).setdefault(v, 0)
            freq[k][v] += 1
    for row in rows:
        row["score"] = round(sum(n / freq[k][v] for k, v in row["traits"].items()), 2)
    ranked = sorted(rows, key=lambda r: -r["score"])
    for i, row in enumerate(ranked):
        row["rank"] = i + 1
    with open(os.path.join(out, "rarity.json"), "w") as f:
        json.dump({"traits": freq, "ranks": {r["id"]: {"rank": r["rank"], "score": r["score"]} for r in rows}},
                  f, indent=1, sort_keys=True)
    lines = ["# CRUSHED rarity", "", f"{n} blocks. Every count below is exact.", ""]
    for k, table in freq.items():
        lines += [f"## {k}", "", "| Value | Count | % |", "|---|---:|---:|"]
        for v, c in sorted(table.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {v} | {c} | {100 * c / n:.1f}% |")
        lines.append("")
    lines += ["## Top 25", "", "| Rank | Token | Condition | Headliner | Contaminant |", "|---:|---|---|---|---|"]
    for row in ranked[:25]:
        t = row["traits"]
        lines.append(f"| {row['rank']} | #{row['id']:04d} | {t['Condition']} | {t['Headliner']} | {t['Contaminant']} |")
    with open(os.path.join(out, "RARITY.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_metadata(out, base_image_uri, base_anim_uri=None, offset=0):
    """One JSON file per token, named by token id (tokenURI = baseURI + id)."""
    os.makedirs(out, exist_ok=True)
    for tid in range(1, recipe.SUPPLY + 1):
        r = token(tid, offset)
        anim = f"{base_anim_uri}/{tid:04d}.mp4" if base_anim_uri else None
        with open(os.path.join(out, str(tid)), "w") as f:
            json.dump(recipe.metadata(r, f"{base_image_uri}/{tid:04d}.png", anim), f, indent=1)
    print(f"metadata: {recipe.SUPPLY} files -> {out}")


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
    ap.add_argument("--offset", type=int, default=0, help="the contract's reveal offset (post-reveal only)")
    ap.add_argument("--sealed", action="store_true", help="render the pre-reveal image (renders/sealed.png)")
    ap.add_argument("--showcase", action="store_true", help="the 100 blocks shown on the site's pile page")
    a = ap.parse_args(argv)

    if a.manifest:
        write_manifest(os.path.join(ROOT, "collection"))
    if a.metadata:
        write_metadata(os.path.join(ROOT, "collection", "metadata"), a.metadata, a.anim_base, a.offset)
    if a.sealed:
        r = recipe.recipe(1)
        r.update(sealed=True, condition="JUNK", one_of_one=None, clean=None)
        sc = build.build(r, res=a.res, samples=a.samples)
        os.makedirs(a.out, exist_ok=True)
        sc.render.filepath = os.path.abspath(os.path.join(a.out, "sealed.png"))
        bpy.ops.render.render(write_still=True)
    ids = list(a.token or [])
    if a.range:
        ids += list(range(a.range[0], a.range[1] + 1))
    if a.showcase:
        ids += recipe.showcase()
    bad = [t for t in ids if not 1 <= t <= recipe.SUPPLY]
    if bad:
        ap.error(f"token ids must be 1..{recipe.SUPPLY}: {bad}")
    for tid in ids:
        if a.skip_existing and os.path.exists(os.path.join(a.out, f"{tid:04d}.png")):
            continue
        render_token(tid, a.out, a.res, a.samples, a.turntable, a.blend, a.offset)


if __name__ == "__main__":
    main()
