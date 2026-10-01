#!/usr/bin/env python3
"""
DRAW THE SLOTS -- the local drawing room paints every printed surface in the collection, hands off.

    python3 ai/draw_slots.py                 draw every slot that has no AI art yet (3 variants each)
    python3 ai/draw_slots.py --slot poster   just that one
    python3 ai/draw_slots.py --variants 6    more choices per slot
    python3 ai/draw_slots.py --redo          draw again even where art exists
    python3 ai/draw_slots.py --check         which slots are AI-drawn, which are still procedural

Each slot has a prompt in ai/prompts/<slot>.txt. The picture is drawn by ~/Desktop/AI/draw.py (ComfyUI,
FLUX.1 schnell, on this machine; nothing leaves it) at the slot's own shape, then resized to the exact
template size and saved as assets/slots/<slot>_ai<k>.png. The compositor picks those up on the next render,
deals one variant per object, and hashes them into the manifest.

Prints a progress line for every picture: [7/102] 7%  poster_ai2.png  (24s)
Never deletes anything. A picture you do not like: move it to "_to delete" on the Desktop.
"""
import argparse
import glob
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOTS = os.path.join(ROOT, "assets", "slots")
TEMPLATES = os.path.join(SLOTS, "_templates")
PROMPTS = os.path.join(ROOT, "ai", "prompts")
DRAW_PY = os.path.expanduser(os.environ.get("CRUSHED_DRAW", "~/Desktop/AI/draw.py"))


def sizes():
    """{slot: (w, h)} from the template PNGs (python3 blender/slots.py writes them)."""
    from PIL import Image
    out = {}
    for f in sorted(glob.glob(os.path.join(TEMPLATES, "*.png"))):
        name = os.path.basename(f)[:-4]
        with Image.open(f) as im:
            out[name] = im.size
    if not out:
        sys.exit("no templates in assets/slots/_templates: run  python3 blender/slots.py  first")
    return out


def draw_size(w, h, long_side=1024):
    """The drawing room wants multiples of 16 near 1024 on the long side; keep the slot's shape."""
    k = long_side / max(w, h)
    dw, dh = max(256, int(round(w * k / 16)) * 16), max(256, int(round(h * k / 16)) * 16)
    return dw, dh


def done(slot):
    return sorted(glob.glob(os.path.join(SLOTS, slot + "_ai*.png")))


def check(sz):
    filled = 0
    for s in sz:
        n = len(done(s)) + len(glob.glob(os.path.join(SLOTS, s + ".png"))) + \
            len([f for f in glob.glob(os.path.join(SLOTS, s + "_*.png")) if "_ai" not in f])
        filled += bool(n)
        print(f"{'ART ' if n else 'proc'}  {s:16s} {sz[s][0]}x{sz[s][1]}   {n} file(s)   prompt: "
              f"{'yes' if os.path.exists(os.path.join(PROMPTS, s + '.txt')) else 'MISSING'}")
    print(f"{filled}/{len(sz)} slots carry drop-in art; the rest render procedurally.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", action="append")
    ap.add_argument("--variants", type=int, default=3)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int, default=44)
    a = ap.parse_args()
    sz = sizes()
    if a.check:
        return check(sz)
    if not os.path.exists(DRAW_PY):
        sys.exit(f"the drawing room script is not at {DRAW_PY} (set CRUSHED_DRAW to where draw.py lives)")
    sys.path.insert(0, os.path.dirname(DRAW_PY))
    import draw  # noqa: E402   his own draw.py: ComfyUI on this machine
    if not draw.up():
        sys.exit("the drawing room is not answering. Open ComfyUI (Comfy Desktop) and try again.")
    from PIL import Image
    want = a.slot or sorted(sz)
    jobs = []
    for s in want:
        if s not in sz:
            sys.exit(f"no such slot: {s}")
        if not os.path.exists(os.path.join(PROMPTS, s + ".txt")):
            print(f"skip {s}: no prompt file at ai/prompts/{s}.txt")
            continue
        have = len(done(s))
        for k in range(a.variants):
            out = os.path.join(SLOTS, f"{s}_ai{k}.png")
            if os.path.exists(out) and not a.redo:
                continue
            jobs.append((s, k, out))
    if not jobs:
        print("nothing to draw: every slot already has its variants (use --redo to draw again)")
        return
    os.makedirs(SLOTS, exist_ok=True)
    t0 = time.time()
    for i, (s, k, out) in enumerate(jobs, 1):
        prompt = open(os.path.join(PROMPTS, s + ".txt")).read().strip()
        w, h = sz[s]
        dw, dh = draw_size(w, h)
        t = time.time()
        tmp = out[:-4] + ".part.png"
        draw.draw(prompt, tmp, w=dw, h=dh, seed=a.seed * 100000 + sum(map(ord, s)) * 10 + k)
        with Image.open(tmp) as im:
            im.convert("RGB").resize((w, h), Image.LANCZOS).save(out, optimize=True)
        os.remove(tmp)
        pct = int(100 * i / len(jobs))
        print(f"[{i}/{len(jobs)}] {pct}%  {os.path.basename(out)}  ({time.time() - t:.0f}s)", flush=True)
    print(f"done: {len(jobs)} pictures in {(time.time() - t0) / 60:.1f} min -> assets/slots/")
    print("next: python3 blender/catalog.py --group all --out /tmp/catalog.png   to see them on the objects")


if __name__ == "__main__":
    main()
