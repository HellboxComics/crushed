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
PLACEHOLDER = "The real object as it was sold and used"      # the stand-in prompt, before the real one is written
PAUSE = os.path.join(ROOT, "ai", "remaster", "PAUSE")         # while this file exists, nothing new is made
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
    """Real photos first (ai/remaster/refs.py): if any were found, the sheet is painted over them so it copies the real
    product; if none, from the words alone."""
    prompt = SHEET_STYLE + open(os.path.join(PROMPTS, name + ".txt")).read().strip()
    sys.path.insert(0, os.path.join(ROOT, "ai", "remaster"))
    import comfy
    import refs
    try:
        refs.fetch(name)
    except Exception:
        pass
    pics = refs.photos(name)
    if pics:
        try:
            init = comfy.sheet_from_photos(pics, os.path.join(WORK, name + "_start.png"))
            if comfy.draw_guided(prompt, init, out):
                return True
        except Exception:
            pass
    r = subprocess.run([sys.executable, DRAW_PY, prompt, "--out", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


INSIDE_STYLE = ("Extreme close-up photo, filling the whole frame edge to edge, of the INSIDE of this object after it "
                "was crushed and split open: only the inner material, no outer shell, no background. The inside: ")


def draw_inside(name, out):
    p = os.path.join(PROMPTS, name + ".inside.txt")
    if not os.path.exists(p):
        return False
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(p):
        return True                       # already painted from these words
    prompt = INSIDE_STYLE + open(p).read().strip()
    r = subprocess.run([sys.executable, DRAW_PY, prompt, "--out", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def sculpt(name, sheet, timeout=3600):
    """Hand the sheet to the sculptor and wait for the shape."""
    tag = f"remaster_{name}"
    os.makedirs(DROP, exist_ok=True)
    done = os.path.join(DROP, "done", tag, tag + ".glb")
    turn = os.path.join(WORK, name + "_turn.png")
    if os.path.exists(done) and os.path.exists(turn) and os.path.getmtime(done) > os.path.getmtime(turn):
        return done                       # already sculpted from this very drawing: only the painting is redone
    # an older shape or an older failure must not be mistaken for this one: both moved aside first, never deleted
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if os.path.isdir(os.path.dirname(done)):
        old = os.path.join(DROP, "done", "_older versions")
        os.makedirs(old, exist_ok=True)
        shutil.move(os.path.dirname(done), os.path.join(old, f"{tag}-{stamp}"))
    bad = os.path.join(DROP, "_problem", tag + ".png")
    if os.path.exists(bad):
        shutil.move(bad, os.path.join(DROP, "_problem", f"{tag}-{stamp}.png"))
    shutil.copy(sheet, os.path.join(DROP, tag + ".png"))
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(done):
            return done
        if os.path.exists(os.path.join(DROP, "_problem", tag + ".png")):
            return None
        time.sleep(15)
    return None


import threading
_LOCK = threading.Lock()


def step(name, what):
    """Say what's happening right now, for the progress page."""
    os.makedirs(WORK, exist_ok=True)
    json.dump({"name": name, "step": what, "since": time.time()}, open(os.path.join(WORK, "now.json"), "w"))
    with _LOCK:
        page()
        publish()


def heartbeat(every=75):
    """Keep the phone page current the whole run: a finished model shows up within a minute or two, even while the
    next object spends minutes in one step (a skipped publish used to wait for the next step)."""
    def loop():
        while True:
            time.sleep(every)
            try:
                with _LOCK:
                    page()
                    publish(force=True)
            except Exception as e:
                say(f"(page refresh skipped: {e})")
    threading.Thread(target=loop, daemon=True).start()


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
        cache = os.path.join(WORK, ".thumbs", name)
        if not os.path.exists(cache) or os.path.getmtime(cache) < os.path.getmtime(src):
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            im = Image.open(src).convert("RGB")
            im.thumbnail((900, 900))
            im.save(cache, quality=80)
        shutil.copy(cache, os.path.join(site, "img", name))
        return f'src="img/{name}"'
    html_ = re.sub(r'src="([^"]+)"', swap, html_)
    html_ = html_.replace("<meta charset=utf-8>", "<meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                          "<meta name=robots content=noindex>")
    open(os.path.join(site, "index.html"), "w").write(html_)
    if os.path.exists(os.path.join(WORK, "view.html")):
        shutil.copy(os.path.join(WORK, "view.html"), os.path.join(site, "view.html"))
    os.makedirs(os.path.join(site, "models"))
    for base in (MODELS, PENDING):                      # every model that exists, so any of them can be spun on the phone
        for g in glob.glob(os.path.join(base, "*", "model.glb")):
            n = os.path.basename(os.path.dirname(g))
            dst = os.path.join(site, "models", n + ".glb")
            if not os.path.exists(dst) and os.path.getsize(g) < 24 * 1024 * 1024:   # the host takes 25 MB a file
                shutil.copy(g, dst)
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


def record(name, result, secs=None):
    p = os.path.join(WORK, "results.json")
    try:
        r = json.load(open(p))
    except Exception:
        r = {}
    r[name] = {"result": result, "at": time.time(), **({"secs": round(secs)} if secs else {})}
    json.dump(r, open(p, "w"), indent=1)


def forget(name):
    p = os.path.join(WORK, "results.json")
    try:
        r = json.load(open(p))
        if r.pop(name, None) is not None:
            json.dump(r, open(p, "w"), indent=1)
    except Exception:
        pass


def shape_base(name):
    """The object whose sculpted shape this one reuses (assets/plan/shapes.json), or itself."""
    p = os.path.join(ROOT, "assets", "plan", "shapes.json")
    seen, n = set(), name
    m = json.load(open(p)) if os.path.exists(p) else {}
    while n in m and n not in seen:
        seen.add(n)
        n = m[n]
    return n


def turnaround_sheet(name, redo=False):
    """The six-view turnaround (ai/remaster/turnaround.py): the local language model writes the real product, Qwen-Image
    paints it from six sides. Returns (sculptor sheet, texture atlas)."""
    sys.path.insert(0, os.path.join(ROOT, "ai", "remaster"))
    import turnaround as T
    cat = json.load(open(os.path.join(ROOT, "ai", "remaster", "catalog.json"))).get(name, {})
    seedp = os.path.join(PROMPTS, name + ".txt")
    seed = open(seedp).read().strip() if os.path.exists(seedp) else ""
    if PLACEHOLDER in seed:
        seed = ""
    # a written description is kept on a redo (redo = make the model again); delete <name>.turn.txt to rewrite it
    desc = T.describe(name, cat.get("display", name), cat.get("years", ""), cat.get("notes", ""), seed)
    turn = os.path.join(WORK, name + "_turn.png")
    tp = os.path.join(PROMPTS, name + ".turn.txt")
    fresh = os.path.exists(turn) and os.path.exists(tp) and os.path.getmtime(turn) > os.path.getmtime(tp)
    if not fresh:                         # a drawing newer than its words is reused; delete the png to draw again
        T.draw(desc, turn)
    cells = T.split(turn)
    sheet = T.sheet2x2(cells, os.path.join(WORK, name + "_sheet.png"))
    atlas = T.atlas(turn, os.path.join(WORK, name + "_atlas.png"))
    return sheet, atlas


def remaster(name, redo=False):
    out = os.path.join(PENDING, name)
    if os.path.exists(os.path.join(out, "model.glb")) and not redo:
        return "already pending"
    if os.path.exists(out):
        trash(out)
    os.makedirs(WORK, exist_ok=True)
    forget(name)                          # an old failure is not shown while it is made again
    step(name, "1/4 the writer describes the real product, the drawing room paints it from six sides")
    try:
        sheet, atlas = turnaround_sheet(name, redo)
    except Exception as e:
        return f"drawing failed: {e}"[:300]
    turn = os.path.join(WORK, name + "_turn.png")
    words = os.path.join(PROMPTS, name + ".turn.txt")
    sys.path.insert(0, os.path.join(ROOT, "ai", "remaster"))
    import turnaround as T
    import views as Vw
    try:                                  # round or a box: built exactly from the drawing, no sculptor needed
        spec = Vw.classify(Vw.load(turn), open(words).read() if os.path.exists(words) else "")
    except Exception as e:
        spec = {"kind": "sculpt", "why": f"could not read the views: {e}"}
    json.dump({k: v for k, v in spec.items() if k != "profile"}, open(os.path.join(WORK, name + "_shape.json"), "w"))
    shape = None
    if spec["kind"] in ("lathe", "box"):
        step(name, "2/4 " + ("round: turned exactly from its real outline" if spec["kind"] == "lathe"
                             else "a box: built exactly to its real corners") + " (seconds, no sculptor)")
    else:
        base = shape_base(name)
        if base != name:                  # same physical shape as another object: reuse its sculpt, new paint only
            tag = f"remaster_{base}"
            shape = os.path.join(DROP, "done", tag, tag + ".glb")
            if not os.path.exists(shape):
                return f"waiting for its shape ({base}) to be sculpted first"
        else:
            step(name, "2/4 the sculptor is making the shape (a complex object)")
            T.free_room()                 # the drawing model out of memory while the sculptor works
            shape = sculpt(name, sheet)
        if not shape:
            return "the sculptor could not make a shape (see ~/3D Drop/_PROBLEM.txt)"
    inside = os.path.join(WORK, name + "_inside.png")
    step(name, "3/4 painting the inside")
    extra = ["--inside", inside] if draw_inside(name, inside) else []
    step(name, "4/4 Blender: real size, one seamless paint job from all six views, review pictures")
    cmd = [PY, os.path.join(ROOT, "blender", "remaster_texture.py"), "--name", name, "--turn", turn,
           "--words", words, "--out", PENDING] + (["--shape", shape] if shape else []) + extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(WORK, name + "_blender.log"), "w").write(r.stdout[-20000:] + "\n" + r.stderr[-20000:])
    if r.returncode or not os.path.exists(os.path.join(out, "model.glb")):
        return "Blender pass failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]
    shutil.copy(os.path.join(WORK, name + "_turn.png"), os.path.join(out, "reference.png"))
    if extra:
        shutil.copy(inside, os.path.join(out, "inside.png"))
    return "ok"


def expected():
    """Every object the collection needs, from ai/remaster/expected.txt (written by ai/plan_check.py from the code
    library and the plan), plus anything that already has a prompt."""
    p = os.path.join(ROOT, "ai", "remaster", "expected.txt")
    ex = [l.strip() for l in open(p) if l.strip()] if os.path.exists(p) else []
    return sorted(set(ex) | set(names()))


def refit_big(limit_mb=24):
    """Models made before the mesh slimming (hundreds of MB): redo only the Blender step, from the sheet, shape and
    inside picture already made. Minutes each, no drawing or sculpting again."""
    for g in glob.glob(os.path.join(PENDING, "*", "model.glb")):
        if os.path.getsize(g) < limit_mb * 1024 * 1024:
            continue
        n = os.path.basename(os.path.dirname(g))
        tag = f"remaster_{n}"
        shape = os.path.join(DROP, "done", tag, tag + ".glb")
        sheet = os.path.join(WORK, n + "_sheet.png")
        inside = os.path.join(WORK, n + "_inside.png")
        if not (os.path.exists(shape) and os.path.exists(sheet)):
            continue
        say(f"slimming {n} ({os.path.getsize(g) // (1024 * 1024)} MB)")
        tmp = os.path.join(WORK, "_refit")
        shutil.rmtree(tmp, ignore_errors=True)
        r = subprocess.run([PY, os.path.join(ROOT, "blender", "remaster_texture.py"), "--name", n, "--shape", shape,
                            "--sheet", sheet, "--out", tmp] + (["--inside", inside] if os.path.exists(inside) else []),
                           capture_output=True, text=True)
        new = os.path.join(tmp, n)
        if r.returncode == 0 and os.path.exists(os.path.join(new, "model.glb")):
            for f in ("reference.png", "inside.png"):
                if os.path.exists(os.path.join(PENDING, n, f)):
                    shutil.copy(os.path.join(PENDING, n, f), os.path.join(new, f))
            trash(os.path.join(PENDING, n))
            shutil.move(new, os.path.join(PENDING, n))
            say(f"  {n}: now {os.path.getsize(os.path.join(PENDING, n, 'model.glb')) // (1024 * 1024)} MB")


def page():
    """~/crushed-render/remaster/index.html, the phone page: what is being made right now, then EVERY object in the
    collection as a card (its state, the real photos, the reference sheet, the four-side review), filterable, with a
    tap-to-spin 3D view of every model that exists. Refreshes itself every 60 seconds."""
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
    plan = json.load(open(os.path.join(ROOT, "assets", "plan", "items.json"))) if os.path.exists(
        os.path.join(ROOT, "assets", "plan", "items.json")) else {}
    job = set(plan) | {n for n in names() if os.path.exists(os.path.join(PROMPTS, n + ".inside.txt"))}
    old_lib = sorted(set(expected()) - job)           # code-built objects the new catalog replaces: not remade
    allx = sorted(job)
    appr = {n for n in allx if os.path.exists(os.path.join(MODELS, n, "model.glb"))}
    pend = {n for n in allx if os.path.exists(os.path.join(PENDING, n, "model.glb"))}
    ready = {n for n in allx if os.path.exists(os.path.join(PROMPTS, n + ".inside.txt"))}

    def txt(n, ext=".txt"):
        p = os.path.join(PROMPTS, n + ext)
        return html.escape(open(p).read().strip()) if os.path.exists(p) else ""

    def state(n):
        if n in appr:
            return "approved", "APPROVED"
        if n in pend:
            v = verdicts.get(n, "")
            return ("redo", "AI SAYS REDO") if v.startswith("REDO") else ("review", "WAITING FOR YOU")
        r = results.get(n, {}).get("result")
        if now and now.get("name") == n and time.time() - now["since"] < 3 * 3600:
            return "togo", "MAKING NOW"                      # an old failure doesn't count while it is being remade
        if r and r != "ok":
            return "problem", "PROBLEM: " + r
        if n not in ready:
            return "prompts", "NEEDS PROMPTS"
        return "togo", "IN LINE"

    def card(n):
        k, label = state(n)
        d = os.path.join(MODELS if n in appr else PENDING, n)
        pics = []
        for f, c in (("review.png", "new (top) vs code (bottom)"), ("reference.png", "reference sheet"), ("inside.png", "inside")):
            if os.path.exists(os.path.join(d, f)):
                pics.append((os.path.join(d, f), c))
        rd = os.path.join(WORK, "refs", n)
        if os.path.isdir(rd):
            pics += [(os.path.join(rd, f), "real photo") for f in sorted(os.listdir(rd)) if f.startswith("ref")]
        imgs = "".join(f'<figure><img src="{rel(p)}" loading="lazy"><figcaption>{c}</figcaption></figure>' for p, c in pics)
        glb = os.path.join(d, "model.glb")
        spin = f'<a class=spin href="view.html#{n}">spin in 3D</a>' if os.path.exists(glb) else ""
        v = verdicts.get(n, "")
        return (f'<section class="c {k}" data-k="{k}" data-n="{html.escape(n)}"><h2>{html.escape(n)} '
                f'<span class=st>{html.escape(label)}</span>{f" <span class=v>AI: {html.escape(v)}</span>" if v else ""}{spin}</h2>'
                f'<div class=imgs>{imgs}</div><details><summary>prompts</summary><p><b>outside</b> {txt(n)}</p>'
                f'<p><b>inside</b> {txt(n, ".inside.txt")}</p><p class=fix>wrong direction? edit '
                f'<code>ai/remaster/prompts/{n}.txt</code>, then <code>.venv/bin/python ai/remaster.py --only {n} --redo</code>'
                f'</p></details></section>')

    counts = {}
    for n in allx:
        counts[state(n)[0]] = counts.get(state(n)[0], 0) + 1
    order = {"review": 0, "redo": 1, "problem": 2, "approved": 3, "togo": 4, "prompts": 5}
    done_order = sorted(allx, key=lambda n: (order[state(n)[0]], -results.get(n, {}).get("at", 0), n))
    nowhtml = ""
    if now and time.time() - now["since"] < 3 * 3600:
        sh = os.path.join(WORK, now["name"] + "_turn.png")       # only this run's picture, never an older one
        if os.path.exists(sh) and os.path.getmtime(sh) < now["since"]:
            sh = ""
        mins = (time.time() - now["since"]) / 60
        rv = os.path.join(PENDING, now["name"], "review.png")
        rv = rv if os.path.exists(rv) and os.path.getmtime(rv) >= now["since"] - 5 else ""
        nowhtml = (f'<section class=now><h2>making now: {html.escape(now["name"])}</h2><p>{html.escape(now["step"])} '
                   f'({mins:.0f} min)</p>' + (f'<img src="{rel(sh)}">' if sh and os.path.exists(sh) else "")
                   + (f'<img src="{rel(rv)}">' if rv else "") + '</section>')
    tabs = [("all", "all", len(allx)), ("review", "waiting for you", counts.get("review", 0)),
            ("redo", "AI says redo", counts.get("redo", 0)), ("approved", "approved", counts.get("approved", 0)),
            ("togo", "in line", counts.get("togo", 0)), ("prompts", "needs prompts", counts.get("prompts", 0)),
            ("problem", "problems", counts.get("problem", 0))]
    left = len(allx) - len(appr) - len(pend)
    catalog = sum(1 for d in plan.values() if d.get("family") != "one-of-one")
    one_items = sum(1 for d in plan.values() if d.get("family") == "one-of-one")
    try:
        recipes = sum(1 for o in json.load(open(os.path.join(ROOT, "assets", "plan", "ones.json"))).values() if o.get("mix"))
    except Exception:
        recipes = 0
    future = max(0, 888 - catalog)                  # catalog items ChatGPT hasn't written yet
    secs = sorted(r["secs"] for r in results.values() if r.get("result") == "ok" and r.get("secs"))
    per = secs[len(secs) // 2] if len(secs) >= 3 else 8 * 60          # the real median once a few are made
    lab_listed = sum(1 for f in glob.glob(os.path.join(ROOT, "ai", "remaster", "labels", "*.txt"))
                     for line in open(f) if line.count("|") >= 2)
    lab_made = len(glob.glob(os.path.join(ROOT, "assets", "labels*", "*", "*.png")))
    body = (f'<h1>crushed.buzz remaster</h1><p class=count>{len(appr)} approved &middot; {len(pend)} waiting for you '
            f'&middot; {left} to make, of {len(allx)} &middot; catalog {catalog} of 888 written'
            f'{f" ({future} still to come from ChatGPT)" if future else ""} &middot; one-of-one recipes {recipes} of 88'
            f'{f" ({one_items} of their objects listed)" if one_items else ""} &middot; labels {lab_made} made of '
            f'{lab_listed or "~200"} &middot; about {(left + future) * per / 86400:.1f} days of Mac time left at '
            f'{per / 60:.0f} min each &middot; updated {time.strftime("%-I:%M %p")}</p>'
            + nowhtml +
            '<div class=tabs>' + "".join(f'<button data-t="{k}">{l} <b>{c}</b></button>' for k, l, c in tabs) +
            '</div><input id=q type=search placeholder="search an object">' +
            "".join(card(n) for n in done_order) +
            (f'<details class=old><summary>old code-built library: {len(old_lib)} objects the new catalog replaces '
             f'(not remade)</summary><p>{html.escape(", ".join(old_lib))}</p></details>' if old_lib else "") +
            '<script>let T="all";const go=()=>{const q=document.getElementById("q").value.toLowerCase();'
            'document.querySelectorAll(".c").forEach(e=>{e.hidden=!((T=="all"||e.dataset.k==T)&&e.dataset.n.includes(q))});'
            'document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("on",b.dataset.t==T))};'
            'document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{T=b.dataset.t;go()});'
            'document.getElementById("q").oninput=go;go()</script>')
    style = ('body{background:#0b0b0b;color:#e9e6df;font:14px/1.5 ui-monospace,Menlo,monospace;margin:0;padding:16px}'
             'h1{color:#ccff00;font-size:20px;margin:0 0 4px}h2{font-size:14px;margin:0 0 8px}.count{color:#999}'
             'section{border:1px solid #2a2926;padding:12px;margin:12px 0;border-radius:6px}.now{border-color:#ccff00}'
             '.st{color:#ccff00;font-size:11px;margin-left:6px}.redo .st,.problem .st{color:#f90}.togo .st,.prompts .st{color:#777}'
             '.v{color:#f90;font-size:11px}.spin{float:right;color:#ccff00;font-size:12px}'
             '.imgs{display:flex;gap:8px;flex-wrap:wrap}figure{margin:0}figure img{max-width:100%;height:auto;max-height:240px;'
             'border:1px solid #333}figcaption{color:#888;font-size:11px}.now img{max-width:420px;width:100%}'
             'code{background:#1b1b1b;padding:1px 5px}.fix{color:#999;font-size:12px}summary{color:#888;cursor:pointer}'
             '.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.tabs button{background:#151515;color:#ccc;border:1px solid #333;'
             'padding:6px 10px;font:12px ui-monospace,monospace;border-radius:4px}.tabs button.on{border-color:#ccff00;color:#ccff00}'
             '#q{width:100%;box-sizing:border-box;background:#151515;color:#eee;border:1px solid #333;padding:9px;font:14px ui-monospace,monospace}'
             '[hidden]{display:none!important}')
    open(os.path.join(WORK, "index.html"), "w").write(
        '<!doctype html><meta charset=utf-8><title>remaster</title><style>' + style + '</style>' + body)
    open(os.path.join(WORK, "view.html"), "w").write(
        '<!doctype html><meta charset=utf-8><title>model</title><meta name=viewport content="width=device-width,initial-scale=1">'
        '<script type=module src="https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script>'
        '<style>body{margin:0;background:#0b0b0b;color:#ccff00;font:14px ui-monospace,monospace}model-viewer{width:100vw;height:88vh}'
        'a{color:#ccff00;margin:12px;display:inline-block}</style><a href="index.html">&larr; all objects</a> <span id=n></span>'
        '<model-viewer id=m camera-controls auto-rotate shadow-intensity=1 exposure=1.1></model-viewer>'
        '<script>const n=location.hash.slice(1);document.getElementById("n").textContent=n;'
        'document.getElementById("m").src="models/"+n+".glb"</script>')


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
    ap.add_argument("--limit", type=int, default=40, help="how many to make this run (the clock calls it often)")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--approve", nargs="*")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--publish-setup", action="store_true", help="make the phone page and print its link")
    a = ap.parse_args()
    if a.publish_setup:
        refit_big(); publish_setup(); return
    if a.status:
        status(); page(); return
    if a.sheet:
        sheet(); return
    if a.approve:
        approve(a.approve); return
    refit_big()
    # an object is ready once its prompts are written: the inside prompt is the last one the AI writes
    todo = a.only or [n for n in names() if not os.path.exists(os.path.join(PENDING, n, "model.glb"))
                      and not os.path.exists(os.path.join(MODELS, n, "model.glb"))
                      and os.path.exists(os.path.join(PROMPTS, n + ".inside.txt"))
]
    plan = set(json.load(open(os.path.join(ROOT, "assets", "plan", "items.json")))) if os.path.exists(
        os.path.join(ROOT, "assets", "plan", "items.json")) else set()
    # the new real-product catalog first, shapes before the objects that reuse them; older prompted objects after
    todo = sorted(todo, key=lambda n: (n not in plan, shape_base(n) != n, n)) if not a.only else todo
    if os.path.exists(PAUSE) and not a.only:
        say("paused: " + open(PAUSE).read().strip())
        todo = []
    if not todo:
        say("nothing ready: write the prompts (see the brief); an object is ready once <name>.inside.txt exists")
    if todo:
        heartbeat()
    for i, n in enumerate(todo[:a.limit] if not a.only else todo):
        t0 = time.time()
        res = remaster(n, a.redo)
        record(n, res, time.time() - t0)
        say(f"[{i + 1}/{len(todo)}] {n}: {res} ({time.time() - t0:.0f}s)")
        if res.startswith("the drawing room"):
            break
    nowp = os.path.join(WORK, "now.json")
    if os.path.exists(nowp):
        os.remove(nowp)                   # the run is over: nothing is being made right now
    status()
    with _LOCK:
        page()
        publish(force=True)


if __name__ == "__main__":
    main()
