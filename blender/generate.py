"""CRUSHED IT generator.

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

from crushed import build, recipe, stage, tex  # noqa: E402

ROOT = os.path.dirname(HERE)


GIFT_RECIPES = [240, 718, 813, 796]     # tokens 41..44: LOW RES, CCFF00, STOP THE PRESSES, CLAY DAY
FIRST_GIFT = 41


def recipe_of(tid, offset):
    """The contract's recipeOf(), mirrored exactly: gifts pinned, the other 884 tokens shifted by the offset
    over the 884 non-gift recipes."""
    if FIRST_GIFT <= tid < FIRST_GIFT + len(GIFT_RECIPES):
        return GIFT_RECIPES[tid - FIRST_GIFT]
    shuffled = recipe.SUPPLY - len(GIFT_RECIPES)
    rank = tid - 1 if tid < FIRST_GIFT else tid - 1 - len(GIFT_RECIPES)
    r = (rank + offset) % shuffled + 1
    for g in sorted(GIFT_RECIPES):
        if g <= r:
            r += 1
    return r


def token_of(rid, offset):
    """Inverse of recipe_of: which token shows recipe `rid`. Before the reveal (offset None) only the gifts
    are known; everything else is reported by its serial."""
    if rid in GIFT_RECIPES:
        return FIRST_GIFT + GIFT_RECIPES.index(rid)
    if offset is None:
        return rid
    for tid in range(1, recipe.SUPPLY + 1):
        if recipe_of(tid, offset) == rid:
            return tid
    raise ValueError(rid)


def token(rid, offset=None):
    """Recipe id (the serial stamped on the strap and in every file name) -> the block, named for the token
    that shows it. Renders never depend on the offset; names and metadata do."""
    r = recipe.recipe(rid)
    tid = token_of(rid, offset)
    one = r["one_of_one"]
    r["token_id"] = tid
    r["name"] = f"CRUSHED IT #{tid:04d}" + (f": {one}" if one else "")
    r["traits"] = r["traits"] + [("Serial", f"{rid:04d}")]
    return r


def render_token(tid, out, res, samples, turntable=0, save_blend=False, offset=None, look="studio"):
    r = token(tid)
    stale = os.path.join(out, f"{tid:04d}.part.png")
    if os.path.exists(stale):
        os.remove(stale)
    t0 = time.time()
    sc = build.build(r, res=res, samples=samples, turntable=turntable, look=look)
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
        # render to a .part file and rename, so a killed run never leaves a half-written PNG that --skip-existing trusts
        part = os.path.abspath(stem + ".part")
        sc.render.filepath = part
        bpy.ops.render.render(write_still=True)
        os.replace(part + ".png", os.path.abspath(stem + ".png"))
    print(f"[crushed] #{tid:04d} {r['condition']:<11} {r['era']} build {t1 - t0:.1f}s "
          f"render {time.time() - t1:.1f}s device={stage.DEVICE['used'] or 'CPU'} crypto={r['crypto']}", flush=True)
    return r


def manifest_blob():
    rows = []
    for tid in range(1, recipe.SUPPLY + 1):
        r = recipe.recipe(tid)
        rows.append({"id": tid, "seed": r["seed"], "traits": dict(r["traits"]), "weight_lb": r["weight_lb"],
                     "items": r["items"], "heroes": r["heroes"], "crypto": r["crypto"]})
    blob = json.dumps({"collection": "CRUSHED IT", "supply": recipe.SUPPLY, "collection_seed": recipe.COLLECTION_SEED,
                       "slots": tex.slot_hashes(), "tokens": rows}, sort_keys=True, separators=(",", ":")).encode()
    return blob, rows


def verify_manifest():
    """Recompute the whole collection on this machine and compare it with the frozen provenance hash.
    A different numpy, a changed object, or a different slot file all show up here, before a render is wasted."""
    blob, _ = manifest_blob()
    digest = "0x" + hashlib.sha256(blob).hexdigest()
    with open(os.path.join(ROOT, "collection", "provenance.txt")) as f:
        frozen = f.read().strip()
    if digest != frozen:
        print(f"[verify] MISMATCH\n  this machine: {digest}\n  frozen:       {frozen}")
        sys.exit(2)
    print(f"[verify] ok, this machine reproduces the frozen collection: {digest}")


def write_manifest(out):
    """manifest.json is the whole collection, frozen. Its sha256 is the provenance hash."""
    blob, rows = manifest_blob()
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
    lines = ["# CRUSHED IT rarity", "", f"{n} blocks. Every count below is exact.", ""]
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


def write_metadata(out, base_image_uri, base_anim_uri=None, offset=None):
    """One JSON file per recipe, named by its serial (the contract's tokenURI is baseURI + recipeOf(token))."""
    os.makedirs(out, exist_ok=True)
    for rid in range(1, recipe.SUPPLY + 1):
        r = token(rid, offset)
        anim = f"{base_anim_uri}/{rid:04d}.mp4" if base_anim_uri else None
        with open(os.path.join(out, str(rid)), "w") as f:
            json.dump(recipe.metadata(r, f"{base_image_uri.rstrip('/')}/{rid:04d}.png", anim), f, indent=1)
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
    ap.add_argument("--verify", action="store_true", help="recompute the collection and compare it with provenance.txt")
    ap.add_argument("--metadata", metavar="IMAGE_BASE_URI")
    ap.add_argument("--anim-base", metavar="ANIM_BASE_URI")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"],
                    help="auto uses a GPU if Cycles finds one; cpu forces the processor")
    ap.add_argument("--look", default="studio", choices=["classic", "studio", "showroom", "daylight"], help="stage look (lights and floor only); studio is the release look")
    ap.add_argument("--offset", type=int, default=None, help="the contract's reveal offset (post-reveal only)")
    ap.add_argument("--sealed", action="store_true", help="render the pre-reveal image (renders/sealed.png)")
    ap.add_argument("--showcase", action="store_true", help="the 100 blocks shown on the site's pile page")
    a = ap.parse_args(argv)
    stage.DEVICE["want"] = a.device

    if a.verify:
        verify_manifest()
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
        render_token(tid, a.out, a.res, a.samples, a.turntable, a.blend, a.offset, a.look)


if __name__ == "__main__":
    main()
