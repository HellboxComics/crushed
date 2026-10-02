#!/usr/bin/env python3
"""
LABELS -- the real printed labels for the crushed packaging behind the objects in every bale (the cans, cartons,
chip bags and wrappers). Without these the bale's background wears the code's parody prints.

    python3 ai/remaster/labels.py              make every listed label that isn't made yet
    python3 ai/remaster/labels.py --approve all    (or slugs) move pending labels into the collection

The list: ai/remaster/labels/<era>.txt, one label per line, written by the Mac's AI:
    surge_can | the 1997 Surge citrus soda can label, lime green with red and black SURGE lettering | Surge soda can 1997
      slug      what the label looks like (the drawing prompt)                                          photo search
<era> is 0..4: 1985-1990, 1991-1996, 1997-2002, 2003-2008, 2009-2026. Aim for 40 a decade: sodas, beers, energy
drinks, chips, candy, cereal, fast food cups, gum, batteries, cigarettes-free (no tobacco), cleaning products.
Made labels land in assets/labels_pending/<era>/<slug>.png; approved ones in assets/labels/<era>/ (used in renders).
"""
import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LISTS = os.path.join(HERE, "labels")
PEND = os.path.join(ROOT, "assets", "labels_pending")
DONE = os.path.join(ROOT, "assets", "labels")
DRAW_PY = os.path.expanduser(os.environ.get("CRUSHED_DRAW", "~/Desktop/AI/draw.py"))
STYLE = ("Flat scan of a product label, unwrapped and laid perfectly flat, filling the whole frame edge to edge, "
         "straight on, even light, true printed colors, crisp logo and lettering exactly as printed, no object, no "
         "background, no hands. The label: ")
sys.path.insert(0, HERE)


def entries():
    for f in sorted(glob.glob(os.path.join(LISTS, "*.txt"))):
        era = os.path.basename(f)[:-4]
        for line in open(f):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parts[0] and not parts[0].startswith("#"):
                yield era, parts[0], parts[1], (parts[2] if len(parts) > 2 else parts[1])


def make(era, slug, prompt, query):
    import subprocess
    import comfy
    import refs
    out = os.path.join(PEND, era, slug + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    key = f"label_{era}_{slug}"
    qf = os.path.join(refs.PROMPTS, key + ".query")
    if not os.path.exists(qf):
        open(qf, "w").write(query)
    try:
        refs.fetch(key)
    except Exception:
        pass
    pics = refs.photos(key)
    if pics:
        from PIL import Image
        start = os.path.join(refs.WORK, key + "_start.png")
        im = Image.open(pics[0]).convert("RGB")
        im.thumbnail((1024, 1024))
        c = Image.new("RGB", (1024, 1024), (255, 255, 255))
        c.paste(im.resize((1024, 1024)), (0, 0))
        c.save(start)
        if comfy.draw_guided(STYLE + prompt, start, out, denoise=0.68):
            return True
    r = subprocess.run([sys.executable, DRAW_PY, STYLE + prompt, "--out", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def approve(which):
    for p in sorted(glob.glob(os.path.join(PEND, "*", "*.png"))):
        era, slug = os.path.basename(os.path.dirname(p)), os.path.basename(p)[:-4]
        if which == ["all"] or slug in which:
            os.makedirs(os.path.join(DONE, era), exist_ok=True)
            shutil.move(p, os.path.join(DONE, era, slug + ".png"))
            print("approved label", era, slug)


def main():
    a = sys.argv[1:]
    if a[:1] == ["--approve"]:
        approve(a[1:] or ["all"])
        return
    n = 0
    for era, slug, prompt, query in entries():
        if os.path.exists(os.path.join(PEND, era, slug + ".png")) or os.path.exists(os.path.join(DONE, era, slug + ".png")):
            continue
        ok = make(era, slug, prompt, query)
        print(f"label {era}/{slug}: {'ok' if ok else 'drawing room did not answer'}", flush=True)
        if not ok:
            break
        n += 1
    print(f"{n} labels made this run")


if __name__ == "__main__":
    main()
