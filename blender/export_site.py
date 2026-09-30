"""Export renders into the static site.

    python3 blender/export_site.py --renders renders --pile            # renders/NNNN.png -> site/pile/
    python3 blender/export_site.py --turntable renders/0044_frames     # frames -> site/turntable/

Runs with plain python3 (needs Pillow and the bpy module for recipe metadata).
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy  # noqa: E402,F401  (mathutils for the object registry)
from PIL import Image  # noqa: E402

from crushed import recipe  # noqa: E402

SITE = os.path.join(ROOT, "site")


def pile(renders, full_px=1024, thumb_px=360):
    out = os.path.join(SITE, "pile")
    os.makedirs(out, exist_ok=True)
    rows = []
    for path in sorted(glob.glob(os.path.join(renders, "[0-9][0-9][0-9][0-9].png"))):
        tid = int(os.path.basename(path)[:4])
        r = recipe.recipe(tid)
        im = Image.open(path).convert("RGB")
        im.resize((full_px, full_px), Image.LANCZOS).save(os.path.join(out, f"{tid:04d}.webp"), quality=86, method=6)
        im.resize((thumb_px, thumb_px), Image.LANCZOS).save(os.path.join(out, f"{tid:04d}_t.webp"), quality=80,
                                                            method=6)
        m = recipe.metadata(r, f"pile/{tid:04d}.webp")
        rows.append({"id": tid, "name": m["name"], "description": m["description"], "image": m["image"],
                     "thumb": f"pile/{tid:04d}_t.webp", "attributes": m["attributes"]})
    with open(os.path.join(out, "pile.json"), "w") as f:
        json.dump(rows, f, indent=1)
    print(f"pile: {len(rows)} blocks -> {out}")
    if rows:
        first = Image.open(os.path.join(renders, f"{rows[0]['id']:04d}.png")).convert("RGB")
        og = Image.new("RGB", (1200, 630), (0, 0, 0))
        og.paste(first.resize((630, 630), Image.LANCZOS), (285, 0))
        og.save(os.path.join(SITE, "og.jpg"), quality=88)


def turntable(frames_dir, px=960, seconds=24):
    out = os.path.join(SITE, "turntable")
    os.makedirs(out, exist_ok=True)
    frames = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    for i, p in enumerate(frames):
        Image.open(p).convert("RGB").resize((px, px), Image.LANCZOS).save(
            os.path.join(out, f"f_{i + 1:04d}.webp"), quality=84, method=6)
    with open(os.path.join(out, "frames.json"), "w") as f:
        json.dump({"count": len(frames), "prefix": "f_", "ext": "webp", "seconds": seconds}, f)
    # favicon: the first frame, tiny
    im = Image.open(frames[0]).convert("RGB")
    w = im.width
    im.crop((int(w * 0.2), int(w * 0.16), int(w * 0.8), int(w * 0.76))).resize((64, 64), Image.LANCZOS).save(
        os.path.join(SITE, "favicon.png"))
    print(f"turntable: {len(frames)} frames -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", default=os.path.join(ROOT, "renders"))
    ap.add_argument("--pile", action="store_true")
    ap.add_argument("--turntable", metavar="FRAMES_DIR")
    a = ap.parse_args()
    if a.pile:
        pile(a.renders)
    if a.turntable:
        turntable(a.turntable)


if __name__ == "__main__":
    main()
