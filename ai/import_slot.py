#!/usr/bin/env python3
"""
IMPORT A PICTURE INTO A SLOT -- any PNG or JPG, from anywhere, resized to the slot's exact shape.

    python3 ai/import_slot.py poster ~/Desktop/mypinup.png            -> assets/slots/poster_mypinup.png
    python3 ai/import_slot.py mag_cover cover1.jpg cover2.jpg          several variants at once
    python3 ai/import_slot.py --list                                   every slot and its size

The picture is center-cropped to the slot's proportions, then resized. The original is never touched.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ai"))
from draw_slots import SLOTS, sizes  # noqa: E402


def main():
    sz = sizes()
    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        for s, (w, h) in sz.items():
            print(f"{s:16s} {w}x{h}")
        return
    slot, files = sys.argv[1], sys.argv[2:]
    if slot not in sz:
        sys.exit(f"no such slot: {slot}  (python3 ai/import_slot.py --list)")
    if not files:
        sys.exit("give it at least one picture")
    from PIL import Image
    w, h = sz[slot]
    for f in files:
        f = os.path.expanduser(f)
        stem = "".join(c if c.isalnum() else "_" for c in os.path.splitext(os.path.basename(f))[0]).strip("_") or "pic"
        out = os.path.join(SLOTS, f"{slot}_{stem}.png")
        with Image.open(f) as im:
            im = im.convert("RGB")
            iw, ih = im.size
            k = max(w / iw, h / ih)
            im = im.resize((max(w, int(iw * k + 0.5)), max(h, int(ih * k + 0.5))), Image.LANCZOS)
            L, T = (im.width - w) // 2, (im.height - h) // 2
            im.crop((L, T, L + w, T + h)).save(out, optimize=True)
        print(f"-> {os.path.relpath(out, ROOT)}  ({w}x{h})")


if __name__ == "__main__":
    main()
