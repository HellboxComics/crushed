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
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
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


def step(name, what):
    """Say what's happening right now, for the progress page."""
    os.makedirs(WORK, exist_ok=True)
    json.dump({"name": name, "step": what, "since": time.time()}, open(os.path.join(WORK, "now.json"), "w"))
    page()
    publish()


PROJECT = "crushed-remaster"          # the phone page: https://crushed-remaster.pages.dev


def _npx():
    for p in (shutil.which("npx"), "/opt/homebrew/bin/npx", "/usr/local/bin/npx"):
        if p and os.path.exists(p):
            return p
    return None


def publish(force=False):
    """Put the progress page online (Cloudflare Pages, free) so it opens on the phone. At most every 90 seconds."""
    import re
    stamp = os.path.join(WORK, ".published")
    if not force and os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < 90:
        return
    npx = _npx()
    if not npx:
        return
    site = os.path.join(WORK, "site")
    shutil.rmtree(site, ignore_errors=True)
    os.makedirs(os.path.join(site, "img"))
    html_ = open(os.path.join(WORK, "index.html")).read()
    from PIL import Image

    def swap(m):
        src = os.path.normpath(os.path.join(WORK, m.group(1)))
        if not os.path.exists(src):
            return m.group(0)
        name = re.sub(r"[^a-z0-9_]+", "_", os.path.relpath(src, os.path.dirname(WORK)).lower()) + ".jpg"
        im = Image.open(src).convert("RGB")
        im.thumbnail((900, 900))
        im.save(os.path.join(site, "img", name), quality=80)
        return f'src="img/{name}"'
    html_ = re.sub(r'src="([^"]+)"', swap, html_)
    html_ = html_.replace("<meta charset=utf-8>", "<meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                          "<meta name=robots content=noindex>")
    open(os.path.join(site, "index.html"), "w").write(html_)
    r = subprocess.run([npx, "--yes", "wrangler@3", "pages", "deploy", site, "--project-name", PROJECT, "--branch", "main",
                        "--commit-dirty=true"], capture_output=True, text=True)
    open(stamp, "w").write(r.stdout[-500:] + r.stderr[-500:])


def publish_setup():
    npx = _npx()
    if not npx:
        say("STOP: Node isn't installed (https://nodejs.org, LTS button).")
        return
    subprocess.run([npx, "--yes", "wrangler@3", "pages", "project", "create", PROJECT, "--production-branch", "main"],
                   capture_output=True, text=True)
    page()
    publish(force=True)
    say(f"phone page: https://{PROJECT}.pages.dev  (updates itself while the remaster works)")


def record(name, result):
    p = os.path.join(WORK, "results.json")
    try:
        r = json.load(open(p))
    except Exception:
        r = {}
    r[name] = {"result": result, "at": time.time()}
    json.dump(r, open(p, "w"), indent=1)


def remaster(name, redo=False):
    out = os.path.join(PENDING, name)
    if os.path.exists(os.path.join(out, "model.glb")) and not redo:
        return "already pending"
    if os.path.exists(out):
        trash(out)
    os.makedirs(WORK, exist_ok=True)
    sheet = os.path.join(WORK, name + "_sheet.png")
    step(name, "1/4 painting the reference sheet")
    if not draw_sheet(name, sheet):
        return "the drawing room did not answer (is ComfyUI open?)"
    step(name, "2/4 the sculptor is making the shape (the slow part)")
    shape = sculpt(name, sheet)
    if not shape:
        return "the sculptor could not make a shape (see ~/3D Drop/_PROBLEM.txt)"
    inside = os.path.join(WORK, name + "_inside.png")
    step(name, "3/4 painting the inside")
    extra = ["--inside", inside] if draw_inside(name, inside) else []
    step(name, "4/4 Blender: sizing, painting it on, review pictures")
    r = subprocess.run([PY, os.path.join(ROOT, "blender", "remaster_texture.py"), "--name", name, "--shape", shape,
                        "--sheet", sheet, "--out", PENDING] + extra, capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(out, "model.glb")):
        return "Blender pass failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]
    shutil.copy(sheet, os.path.join(out, "reference.png"))
    if extra:
        shutil.copy(inside, os.path.join(out, "inside.png"))
    return "ok"


def page():
    """~/crushed-render/remaster/index.html: what's being made right now, and every result so far, newest first,
    with its pictures and prompts. Refreshes itself every 20 seconds."""
    import html
    os.makedirs(WORK, exist_ok=True)
    rel = lambda p: os.path.relpath(p, WORK)
    try:
        now = json.load(open(os.path.join(WORK, "now.json")))
    except Exception:
        now = None
    try:
        results = json.load(open(os.path.join(WORK, "results.json")))
    except Exception:
        results = {}
    verdicts = {}
    vp = os.path.join(ROOT, "ai", "remaster", "verdicts.txt")
    if os.path.exists(vp):
        for line in open(vp):
            if line.strip():
                k, _, v = line.strip().partition(" ")
                verdicts[k] = v
    all_ = names()
    appr = {n for n in all_ if os.path.exists(os.path.join(MODELS, n, "model.glb"))}
    pend = {n for n in all_ if os.path.exists(os.path.join(PENDING, n, "model.glb"))}

    def txt(n, ext=".txt"):
        p = os.path.join(PROMPTS, n + ext)
        return html.escape(open(p).read().strip()) if os.path.exists(p) else ""

    def card(n):
        d = os.path.join(MODELS if n in appr else PENDING, n)
        state = "APPROVED" if n in appr else "WAITING FOR YOU" if n in pend else results.get(n, {}).get("result", "")
        imgs = "".join(f'<figure><img src="{rel(os.path.join(d, f))}" loading="lazy"><figcaption>{c}</figcaption></figure>'
                       for f, c in (("review.png", "new (top) vs now (bottom)"), ("reference.png", "reference"),
                                    ("inside.png", "inside")) if os.path.exists(os.path.join(d, f)))
        v = verdicts.get(n, "")
        return (f'<section><h2>{html.escape(n)} <span class="st">{html.escape(state)}</span>'
                f'{f" <span class=v>AI says: {html.escape(v)}</span>" if v else ""}</h2><div class=imgs>{imgs}</div>'
                f'<p><b>outside</b> {txt(n)}</p><p><b>inside</b> {txt(n, ".inside.txt")}</p>'
                f'<p class=fix>wrong direction? edit <code>ai/remaster/prompts/{n}.txt</code>, then '
                f'<code>.venv/bin/python ai/remaster.py --only {n} --redo</code></p></section>')

    done = sorted(results, key=lambda n: -results[n]["at"])
    nowhtml = ""
    if now and time.time() - now["since"] < 3 * 3600 and now["name"] not in done[:1]:
        sh = os.path.join(WORK, now["name"] + "_sheet.png")
        mins = (time.time() - now["since"]) / 60
        nowhtml = (f'<section class=now><h2>making now: {html.escape(now["name"])}</h2><p>{html.escape(now["step"])} '
                   f'({mins:.0f} min)</p>' + (f'<img src="{rel(sh)}">' if os.path.exists(sh) else "") +
                   f'<p><b>outside</b> {txt(now["name"])}</p></section>')
    queue = [n for n in all_ if n not in appr and n not in pend and n not in results][:15]
    body = (f'<h1>crushed.buzz remaster</h1><p class=count>{len(appr)} approved &middot; {len(pend)} waiting for you '
            f'&middot; {len(all_) - len(appr) - len(pend)} to go &middot; updated {time.strftime("%-I:%M %p")}</p>'
            + nowhtml + "".join(card(n) for n in done) +
            f'<p class=q>next up: {", ".join(queue)}</p>')
    open(os.path.join(WORK, "index.html"), "w").write(
        '<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=20><title>remaster</title><style>'
        'body{background:#0b0b0b;color:#e9e6df;font:14px/1.5 ui-monospace,Menlo,monospace;margin:0;padding:18px}'
        'h1{color:#ccff00;font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:0 0 8px}.count{color:#999}'
        'section{border:1px solid #2a2926;padding:14px;margin:14px 0;border-radius:6px}.now{border-color:#ccff00}'
        '.st{color:#ccff00;font-size:12px;margin-left:8px}.v{color:#f90;font-size:12px}'
        '.imgs{display:flex;gap:10px;flex-wrap:wrap}figure{margin:0}figure img{max-width:100%;height:auto;'
        'max-height:300px;border:1px solid #333}figcaption{color:#888;font-size:11px}.now img{max-width:420px;width:100%}'
        'code{background:#1b1b1b;padding:1px 5px}.fix{color:#999;font-size:12px}.q{color:#777}</style>' + body)


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
    p = os.path.join(WORK, "review sheet.png")      # background jobs can't write to the Desktop
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
    ap.add_argument("--publish-setup", action="store_true", help="make the phone page and print its link")
    a = ap.parse_args()
    if a.publish_setup:
        publish_setup(); return
    if a.status:
        status(); page(); return
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
        record(n, res)
        say(f"[{i + 1}/{len(todo)}] {n}: {res} ({time.time() - t0:.0f}s)")
        if res.startswith("the drawing room"):
            break
    status()
    page()
    publish(force=True)


if __name__ == "__main__":
    main()
