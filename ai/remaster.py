#!/usr/bin/env python3
"""
REMASTER -- the local AI rebuilds every object in the collection as a real Blender model, hands off.

    python3 ai/remaster.py                  the next objects that have no remaster yet (resumes where it stopped)
    python3 ai/remaster.py --only gremlin   just that one (add --redo to make it again)
    python3 ai/remaster.py --sheet          the review sheet: every pending remaster next to the code version
    python3 ai/remaster.py --approve gremlin console_64      move those into the collection
    python3 ai/remaster.py --approve all                     every pending one
    python3 ai/remaster.py --status         how many are done, pending, approved

For each object:
  1. REFERENCE   the drawing room (~/Desktop/AI/draw.py, FLUX on this Mac) paints a 2x2 reference sheet of the
                 real thing from ai/remaster/prompts/<name>.txt: front, back, left side, right side.
  2. SHAPE       the sheet goes into ~/3D Drop; the sculptor (Hunyuan3D-2mv, on this Mac) turns it into a 3D shape.
  3. INSIDE      the drawing room paints what it is made of inside (ai/remaster/prompts/<name>.inside.txt): the
                 circuit board in a cartridge, the filling in a chocolate, the foam in a shoe.
  4. BLENDER     blender/remaster_texture.py fits the shape to the object's real size, paints the sheet onto it,
                 and adds the inside as an inner layer. Crushing tears holes in the shell so the inside shows.
  5. REVIEW      assets/models_pending/<name>/review.png: the remaster's four sides above the code version's.
Nothing reaches the collection until it is approved. An approved model lives in assets/models/<name>/model.glb
and replaces the code-built object in every cube (crushed the same way), and is hashed into the manifest.

The prompts are plain text. Edit any of them and run --only <name> --redo.
Never deletes anything: a remaster that gets redone is moved to ~/Desktop/_to delete/remaster/ first.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(ROOT, "ai", "remaster", "prompts")
PENDING = os.path.join(ROOT, "assets", "models_pending")
MODELS = os.path.join(ROOT, "assets", "models")
WORK = os.path.expanduser("~/crushed-render/remaster")
DROP = os.path.expanduser("~/3D Drop")
DRAW_PY = os.path.expanduser(os.environ.get("CRUSHED_DRAW", "~/Desktop/AI/draw.py"))
TRASH = os.path.expanduser("~/Desktop/_to delete/remaster")
PY = os.path.join(ROOT, ".venv", "bin", "python")
SHEET_STYLE = ("Product reference sheet, a 2x2 grid of four photos of the same single object on a plain white "
               "background: top left the FRONT, top right the BACK, bottom left the LEFT side, bottom right the "
               "RIGHT side. Same object, same size, same colors in all four. Studio product photography, soft even "
               "light, true colors, real materials, sharp detail, whole object in frame, no props, no hands, no "
               "text captions. The object: ")


def names():
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(PROMPTS, "*.txt"))
                  if not p.endswith(".inside.txt"))


def say(msg):
    print(msg, flush=True)


def trash(path):
    os.makedirs(TRASH, exist_ok=True)
    shutil.move(path, os.path.join(TRASH, f"{os.path.basename(path)}-{time.strftime('%Y%m%d-%H%M%S')}"))


def draw_sheet(name, out):
    prompt = SHEET_STYLE + open(os.path.join(PROMPTS, name + ".txt")).read().strip()
    r = subprocess.run([sys.executable, DRAW_PY, prompt, "--out", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


INSIDE_STYLE = ("Extreme close-up photo, filling the whole frame edge to edge, of the INSIDE of this object after it "
                "was crushed and split open: only the inner material, no outer shell, no background. The inside: ")


def draw_inside(name, out):
    p = os.path.join(PROMPTS, name + ".inside.txt")
    if not os.path.exists(p):
        return False
    prompt = INSIDE_STYLE + open(p).read().strip()
    r = subprocess.run([sys.executable, DRAW_PY, prompt, "--out", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def sculpt(name, sheet, timeout=3600):
    """Hand the sheet to the sculptor and wait for the shape."""
    tag = f"remaster_{name}"
    os.makedirs(DROP, exist_ok=True)
    shutil.copy(sheet, os.path.join(DROP, tag + ".png"))
    done = os.path.join(DROP, "done", tag, tag + ".glb")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(done):
            return done
        if os.path.exists(os.path.join(DROP, "_problem", tag + ".png")):
            return None
        time.sleep(15)
    return None


def remaster(name, redo=False):
    out = os.path.join(PENDING, name)
    if os.path.exists(os.path.join(out, "model.glb")) and not redo:
        return "already pending"
    if os.path.exists(out):
        trash(out)
    os.makedirs(WORK, exist_ok=True)
    sheet = os.path.join(WORK, name + "_sheet.png")
    if not draw_sheet(name, sheet):
        return "the drawing room did not answer (is ComfyUI open?)"
    shape = sculpt(name, sheet)
    if not shape:
        return "the sculptor could not make a shape (see ~/3D Drop/_PROBLEM.txt)"
    inside = os.path.join(WORK, name + "_inside.png")
    extra = ["--inside", inside] if draw_inside(name, inside) else []
    r = subprocess.run([PY, os.path.join(ROOT, "blender", "remaster_texture.py"), "--name", name, "--shape", shape,
                        "--sheet", sheet, "--out", PENDING] + extra, capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(out, "model.glb")):
        return "Blender pass failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]
    shutil.copy(sheet, os.path.join(out, "reference.png"))
    return "ok"


def status():
    all_ = names()
    pend = [n for n in all_ if os.path.exists(os.path.join(PENDING, n, "model.glb"))]
    appr = [n for n in all_ if os.path.exists(os.path.join(MODELS, n, "model.glb"))]
    say(f"{len(all_)} objects: {len(appr)} approved, {len(pend)} waiting for review, "
        f"{len(all_) - len(appr) - len(pend)} not made yet")
    return all_, pend, appr


def approve(which):
    _, pend, _ = status()
    pick = pend if which == ["all"] else [n for n in which if n in pend]
    for n in pick:
        dst = os.path.join(MODELS, n)
        if os.path.exists(dst):
            trash(dst)
        os.makedirs(MODELS, exist_ok=True)
        shutil.move(os.path.join(PENDING, n), dst)
        say(f"approved {n}")
    if pick:
        say("Approved models change the collection: re-freeze it before rendering "
            "(python3 blender/generate.py --manifest).")


def sheet():
    from PIL import Image, ImageDraw
    _, pend, _ = status()
    if not pend:
        return
    tiles = []
    for n in pend:
        im = Image.open(os.path.join(PENDING, n, "review.png")).convert("RGB")
        im = im.resize((720, int(720 * im.height / im.width)))
        ImageDraw.Draw(im).text((8, 6), n, fill=(255, 255, 0))
        tiles.append(im)
    cols = 3
    h = max(t.height for t in tiles)
    out = Image.new("RGB", (720 * cols, h * ((len(tiles) + cols - 1) // cols)), (30, 30, 30))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * 720, (i // cols) * h))
    p = os.path.expanduser("~/Desktop/crushed remaster review.png")
    out.save(p)
    say(f"review sheet: {p}  (top row of each = remaster, bottom row = code version)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--limit", type=int, default=6, help="how many to make this run (the clock calls it often)")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--approve", nargs="*")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        status(); return
    if a.sheet:
        sheet(); return
    if a.approve:
        approve(a.approve); return
    # an object is ready once its prompts are written: the inside prompt is the last one the AI writes
    todo = a.only or [n for n in names() if not os.path.exists(os.path.join(PENDING, n, "model.glb"))
                      and not os.path.exists(os.path.join(MODELS, n, "model.glb"))
                      and os.path.exists(os.path.join(PROMPTS, n + ".inside.txt"))]
    if not todo:
        say("nothing ready: write the prompts (see the brief); an object is ready once <name>.inside.txt exists")
    for i, n in enumerate(todo[:a.limit] if not a.only else todo):
        t0 = time.time()
        res = remaster(n, a.redo)
        say(f"[{i + 1}/{len(todo)}] {n}: {res} ({time.time() - t0:.0f}s)")
        if res.startswith("the drawing room"):
            break
    status()


if __name__ == "__main__":
    main()
