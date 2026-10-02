"""The asset pipeline, run on the Mac by itself, start to finish, for each catalog item:

  1. hunt     every photo of the real product: Google Images, your own photos, free photo sites (hunt.py)
  2. cut out  each photo's object exactly (BiRefNet in the drawing room)
  3. check    the local vision model keeps only photos of this exact product, right era, sharp, straight-on (vet.py)
  4. pick     the best 6 go to your phone (Telegram); you tap the true one -- the AI can't judge era
  5. build    the exact shape in Blender (lathe or box; Hunyuan's shape for soft things), Hunyuan Paint covers
              every side from your photo, Blender sets the real size and saves .glb .fbx .usdc .blend
  6. inspect  studio pictures from every side; the judge compares them with your photo
  7. page     everything onto the phone page, https://crushed-remaster.pages.dev

    .venv/bin/python library/run.py --only duracell_coppertop_aa_1998 [--redo]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "ai", "remaster"))
sys.path.insert(0, os.path.join(ROOT, "ai"))
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "library")
PY = sys.executable
STATUS = os.path.join(OUT, "status.json")
WAIT = False          # --wait: a run you started yourself waits for your tap instead of moving on


def say(*a):
    print(*a, flush=True)


def status(cid, **kw):
    os.makedirs(OUT, exist_ok=True)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s.setdefault(cid, {}).update(kw, at=time.time())
    json.dump(s, open(STATUS, "w"), indent=1)
    global _LAST
    final = kw.get("step", "").startswith(("done", "stopped", "no ")) or "ok" in kw
    if final or time.time() - _LAST > 90:          # the phone page updates at most every 90 s, and always at the end
        _LAST = time.time()
        try:
            page()
        except Exception as e:
            say(f"(page skipped: {e})")


_LAST = 0.0


def item(cid):
    plan = json.load(open(os.path.join(ROOT, "assets", "plan", "items.json")))
    p = plan.get(cid, {})
    product = p.get("product") or p.get("display") or cid.replace("_", " ")
    year = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", product)
    q = os.path.join(ROOT, "ai", "remaster", "prompts", cid + ".query")
    words = open(q).read().strip() if os.path.exists(q) else product
    words = re.sub(r"\b(circa|c\.)\s*", "", re.sub(r"\b(19|20)\d\d\b", "", words)).strip(" ,")
    return product, words, int(year.group(1)) if year else None


def pipeline(cid, redo=False):
    import hunt
    import turnaround as T
    import vet as V
    import numpy as np
    from PIL import Image
    fam = json.load(open(os.path.join(HERE, "families.json"))).get(cid)
    if not fam:
        status(cid, step="not sorted into a shape family yet", ok=False)
        return
    product, words, year = item(cid)
    era = f"{year - 3}-{year + 3}" if year else "any"
    d = os.path.join(OUT, cid)
    os.makedirs(d, exist_ok=True)

    status(cid, product=product, step="1/6 hunting photos (Google Images, your photos, free sites)")
    found = json.load(open(os.path.join(WORK, "hunt", cid, "found.json"))) if (
        not redo and os.path.exists(os.path.join(WORK, "hunt", cid, "found.json"))) else hunt.run(cid, words, year, log=say)

    status(cid, step=f"2/6 cutting out {len(found)} photos")
    T.free_room()
    for f in found:
        try:
            f["mask"] = T.photo_mask(f["file"])
        except Exception as e:
            say(f"[cut out] {os.path.basename(f['file'])}: {e}")

    status(cid, step=f"3/6 the vision model checks {len(found)} photos")
    T.free_room()
    vj = os.path.join(d, "vetted.json")
    old = {v["file"]: v for v in json.load(open(vj))} if os.path.exists(vj) and not redo else {}
    use = V.model()
    quick = V.quick_model()
    say(f"[check] vision model: {use}" + (f" (quick first look: {quick})" if quick else ""))
    todo = [f for f in found if not (f["file"] in old and "vet" in old[f["file"]])]
    for f in found:
        if f not in todo:
            f["vet"] = old[f["file"]]["vet"]
    if quick and len(todo) > 16:                         # many photos: the small model throws out the obvious misses
        for k, f in enumerate(todo, 1):
            f["quick"] = V.vet(f["file"], product, era, quick, think=False) or {}
            say(f"[quick look {k}/{len(todo)}] {os.path.basename(f['file'])}: match {f['quick'].get('match')}, "
                f"era ok {f['quick'].get('era_ok')}, {f['quick'].get('view')}")
            if k % 10 == 0:
                status(cid, step=f"3/6 quick look: {k} of {len(todo)} photos")
        todo.sort(key=lambda f: -(f["quick"].get("match", 0) + 3 * (f["quick"].get("era_ok") is True)))
        for f in todo[16:]:
            f["vet"] = dict(f["quick"], note="only the quick look")
        todo = todo[:16]
    for k, f in enumerate(todo, 1):
        status(cid, step=f"3/6 {use} judges the best photos carefully: {k} of {len(todo)}")
        f["vet"] = V.vet(f["file"], product, era, use)
        say(f"[check] {os.path.basename(f['file'])}: {json.dumps(f['vet'])[:160]}")
    json.dump(found, open(vj, "w"), indent=1)
    # 4. YOUR PICK: the AI can't tell a 1998 product from a 2020 one, so it shows you its best photos on your
    # phone and you tap the true one. Everything after this is built from that one photo.
    spec = json.load(open(os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json"))) if fam.get("shape") else None
    cands = [f for f in found if f.get("mask") and f.get("vet") and f["vet"].get("match", 0) >= 7
             and f["vet"].get("sharp", True) is not False and f["vet"].get("whole", True) is not False]
    if spec:
        cands = [f for f in cands if size_ok(f, spec)]
    cands.sort(key=lambda f: (-(f["vet"].get("era_ok") is True), -(f["vet"].get("view") == "front"),
                              -f["vet"].get("match", 0)))
    picked = your_pick(cid, product, cands[:6], d)
    if not picked:
        return

    plan = json.load(open(os.path.join(ROOT, "assets", "plan", "items.json"))).get(cid, {})
    size = fam.get("size") or plan.get("size") or [0.1, 0.1, 0.1]
    mdir = os.path.join(d, "model")
    os.makedirs(mdir, exist_ok=True)
    ref = reference(picked, d, upright=fam["family"] == "round")

    # 5. BUILD: the exact shape in Blender (or Hunyuan's shape for soft things), then Hunyuan Paint covers every
    # side of it from your photo, then Blender sets the real size and saves every format.
    if fam["family"] == "round":
        status(cid, step="5/6 building the exact shape in Blender")
        subprocess.run([PY, os.path.join(HERE, "shapes", "lathe.py"), "--", os.path.join(HERE, "shapes", "specs",
                        fam["shape"] + ".json"), os.path.join(mdir, "bare")], check=True, capture_output=True)
        bare = os.path.join(mdir, "bare", spec["id"] + ".glb")
        pts = [pt for p in spec["profile"] for pt in p["pts"]]
        biggest = (max(z for r, z in pts) - min(z for r, z in pts)) / 1000.0
    elif fam["family"] in ("box", "flat"):
        status(cid, step="5/6 building the exact box in Blender")
        W, D, H = size[:3]
        subprocess.run([PY, os.path.join(HERE, "shapes", "box.py"), "--", str(W), str(max(D, 0.0003)), str(H),
                        os.path.join(mdir, "bare"), "-", "-", cid, "0.3" if fam["family"] == "flat" else "0.6"],
                       check=True, capture_output=True)
        bare = os.path.join(mdir, "bare", cid + ".glb")
        biggest = max(W, D, H)
    elif fam["family"] == "soft":
        bare, biggest = None, max(size)
    else:
        status(cid, step=f"no builder for the '{fam['family']}' family yet", ok=False)
        return
    status(cid, step="5/6 Hunyuan Paint is painting every side from your photo (about 10 minutes)")
    painted = hunyuan_paint(ref, os.path.join(mdir, "hunyuan"), bare)
    status(cid, step="5/6 Blender: real size, every format")
    subprocess.run([PY, os.path.join(HERE, "shapes", "resize.py"), "--", painted, str(biggest), mdir, cid],
                   check=True, capture_output=True)
    glb = os.path.join(mdir, cid + ".glb")
    pend = os.path.join(ROOT, "assets", "models_pending", cid)
    os.makedirs(pend, exist_ok=True)
    import shutil
    shutil.copy(glb, os.path.join(pend, "model.glb"))

    # 6. INSPECT: studio pictures from four sides, judged against your photo
    status(cid, step="6/6 pictures from every side and the judge's inspection")
    subprocess.run([PY, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(d, "view.png"), "0,90,180,270"],
                   check=True, capture_output=True)
    views = [os.path.join(d, f"view_{a:03d}.png") for a in (0, 90, 180, 270)]
    sheet = Image.new("RGB", (4 * 300, 400), "white")
    for k, v in enumerate(views):
        sheet.paste(Image.open(v).convert("RGB").resize((300, 400)), (k * 300, 0))
    sheet.save(os.path.join(d, "views.jpg"), quality=88)
    verdict = inspect(os.path.join(d, "views.jpg"), picked["file"], product, use)
    status(cid, step="done", ok=bool(verdict.get("pass")), verdict=verdict, photos=len(found), good=len(cands),
           label=os.path.relpath(ref, WORK), views=os.path.relpath(os.path.join(d, "views.jpg"), WORK),
           ref=os.path.relpath(picked["file"], WORK), note="")


def size_ok(f, spec, tol=0.2):
    """Round things: the photo's object must have the right length-to-width (an AA is about 3.5 to 1, a D cell
    about 1.8 to 1). Measured on the cut-out, so a wrong size can never get in."""
    import numpy as np
    from PIL import Image
    import mosaic
    pts = [pt for p in spec["profile"] for pt in p["pts"]]
    want = (max(z for r, z in pts) - min(z for r, z in pts)) / (2 * max(r for r, z in pts))
    im = Image.open(f["file"]).convert("RGB")
    m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
    objs = mosaic.objects(im, m)
    if not objs:
        return False
    mm = objs[0][1] > 0.5
    ys, xs = np.where(mm)
    got = (xs.max() - xs.min() + 1) / max(ys.max() - ys.min() + 1, 1)      # lying sideways: length / width
    f["ratio"] = round(float(got), 2)
    return abs(got - want) / want <= tol


def your_pick(cid, product, cands, d):
    """The photo you picked on your phone, or None while we wait (or if you said none of these)."""
    picks_f = os.path.expanduser("~/.hellbox/picks.json")
    cf = os.path.join(d, "candidates.json")
    picks = json.load(open(picks_f)) if os.path.exists(picks_f) else {}
    p = picks.get(cid)
    if p and os.path.exists(cf):
        shown = json.load(open(cf))["files"]
        if p["pick"] == "none":
            status(cid, step="you said none of these photos fit - it needs better photos", ok=False)
            return None
        f = shown[int(p["pick"]) - 1]
        return next((x for x in cands if x["file"] == f["file"]), f)
    if os.path.exists(cf):
        status(cid, step="waiting for your pick on your phone (Telegram)", ok=False)
        if WAIT:                                       # started by hand: wait here for the tap (up to 30 min)
            for _ in range(180):
                time.sleep(10)
                picks = json.load(open(picks_f)) if os.path.exists(picks_f) else {}
                if cid in picks:
                    say("[pick] you picked " + picks[cid]["pick"])
                    return your_pick(cid, product, cands, d)
        return None
    if not cands:
        status(cid, step="no usable photo found", ok=False)
        return None
    sheet = pick_sheet(cands, os.path.join(d, "pick_sheet.jpg"))
    sys.path.insert(0, os.path.expanduser("~/.hellbox/ai"))
    import askfirst
    if not askfirst.ask_pick(cid, product, sheet, len(cands)):
        status(cid, step="could not send the photo choice to your phone - will try again next run", ok=False)
        return None
    json.dump({"files": [{"file": c["file"], "mask": c["mask"], "vet": c["vet"]} for c in cands], "asked": time.time()},
              open(cf, "w"), indent=1)
    status(cid, step="waiting for your pick on your phone (Telegram)", ok=False, pick_sheet=os.path.relpath(sheet, WORK))
    say("[pick] the best photos are on your phone (Hart's Telegram) - tap the true one")
    return your_pick(cid, product, cands, d) if WAIT else None


def pick_sheet(cands, out):
    """The photos side by side, big numbers on each, for your phone."""
    from PIL import Image, ImageDraw, ImageFont
    S = 512
    cols = 3 if len(cands) > 2 else len(cands)
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * S, rows * S), "white")
    try:
        font = ImageFont.load_default(size=72)
    except TypeError:
        font = ImageFont.load_default()
    for k, c in enumerate(cands):
        im = Image.open(c["file"]).convert("RGB")
        im.thumbnail((S - 16, S - 16), Image.LANCZOS)
        x, y = (k % cols) * S, (k // cols) * S
        sheet.paste(im, (x + (S - im.width) // 2, y + (S - im.height) // 2))
        dr = ImageDraw.Draw(sheet)
        dr.rectangle([x + 8, y + 8, x + 100, y + 100], fill="black")
        dr.text((x + 30, y + 14), str(k + 1), fill="yellow", font=font)
        dr.rectangle([x, y, x + S - 1, y + S - 1], outline="black", width=3)
    sheet.save(out, quality=90)
    return out


def reference(f, d, upright=False):
    """Your photo, cut out, centered on white with room around it - what the painter looks at."""
    import numpy as np
    from PIL import Image
    im = Image.open(f["file"]).convert("RGB")
    m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
    from scipy import ndimage
    lab, n = ndimage.label(m > 0.5)
    if n > 1:                                             # several in the photo: the biggest one
        k = np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))) + 1
        m = np.where(lab == k, m, 0)
    ys, xs = np.where(m > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([np.asarray(im), (m * 255).astype(np.uint8)])[y0:y1, x0:x1]
    obj = Image.fromarray(rgba)
    if upright and obj.width > obj.height:                # round things stand up, like the shape does
        obj = obj.rotate(90, expand=True)
    side = int(max(obj.size) * 1.15)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(obj, ((side - obj.width) // 2, (side - obj.height) // 2), obj)
    out = os.path.join(d, "reference.png")
    sq.resize((1024, 1024), Image.LANCZOS).save(out)
    return out


def hunyuan_paint(ref, out, bare=None):
    """Hunyuan3D 2.1 (Apple-chip build) in its own Python. With an exact shape: paints it. Without: makes the
    shape from the photo too (soft things)."""
    import hunyuan
    hy = hunyuan.home()
    if not hy:
        raise RuntimeError("Hunyuan3D is not installed yet - run the setup paste")
    cmd = [os.path.join(hy, ".venv", "bin", "python"), os.path.join(HERE, "hunyuan.py"), ref, out]
    if bare:
        cmd += ["--paint", bare]
    r = subprocess.run(cmd, capture_output=True, text=True)
    glb = os.path.join(out, "textured.glb")
    if r.returncode != 0 or not os.path.exists(glb):
        raise RuntimeError("Hunyuan3D did not finish: " + (r.stderr or r.stdout)[-400:])
    return glb


def inspect(sheet, photo, product, use):
    """The judge compares the finished model (studio pictures from four sides) with a real photo."""
    import vet as V
    if not use:
        return {"pass": False, "problems": "no vision model installed"}
    q = (f"Picture 1 shows a 3D model of: {product}, from the front, right, back and left. Picture 2 is a real photo "
         "of the product. Is the 3D model a faithful, finished, game-quality copy of the real product: same shape and "
         "proportions, same design, colors and printing, readable words, every side finished, no smears, no seams, "
         "no holes, nothing missing or invented? Answer ONLY JSON: "
         "{\"pass\": true/false, \"problems\": \"short list or empty\"}")
    try:
        return V.ask(use, q, [sheet, photo])
    except Exception as e:
        return {"pass": False, "problems": f"could not inspect: {e}"}


def page():
    import html
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    rows = []
    for cid, v in sorted(s.items(), key=lambda kv: -kv[1].get("at", 0)):
        badge = "PASS" if v.get("ok") else ("working" if v.get("step") != "done" else "NEEDS WORK")
        imgs = "".join(f'<img src="{html.escape(v[k])}">' for k in ("ref", "views", "label") if v.get(k))
        ver = v.get("verdict", {})
        rows.append(f"<div class=c><h3>{html.escape(v.get('product', cid))} <b class={badge.split()[0]}>{badge}</b></h3>"
                    f"<p>{html.escape(v.get('step', ''))}</p>"
                    f"<p>{'photos found: %s, usable: %s, label covered: %s' % (v.get('photos','-'), v.get('good','-'), format(v.get('covered',0),'.0%')) if 'covered' in v else ''}</p>"
                    f"<p>{html.escape(v.get('note', ''))}</p>"
                    f"<p>{html.escape(str(ver.get('problems', '')) if ver else '')}</p>{imgs}"
                    + (f'<p><a href="view.html#{cid}">spin the 3D model</a></p>' if v.get("step") == "done" else "")
                    + "</div>")
    doc = ("<!doctype html><meta charset=utf-8><title>Crushed asset library</title><style>"
           "body{font:16px system-ui;margin:12px;background:#111;color:#eee}img{width:100%;margin:4px 0;border-radius:6px}"
           ".c{background:#1c1c1c;padding:10px;margin:10px 0;border-radius:10px}b{padding:2px 6px;border-radius:4px}"
           ".PASS{background:#1a7f37}.NEEDS{background:#9a2a2a}.working{background:#7a5c00}a{color:#8cf}</style>"
           f"<h2>Asset library - updated {time.strftime('%H:%M')}</h2>" + "".join(rows))
    open(os.path.join(WORK, "index.html"), "w").write(doc)
    import remaster as RM
    RM.publish(force=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--queue", type=int, default=0, help="make up to N sorted items that are not done yet")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--wait", action="store_true", help="wait for your photo pick on the phone")
    a = ap.parse_args()
    WAIT = a.wait
    todo = a.only or []
    if a.queue:
        fam = {k: v for k, v in json.load(open(os.path.join(HERE, "families.json"))).items() if not k.startswith("_")}
        st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
        pf = os.path.expanduser("~/.hellbox/picks.json")
        picks = json.load(open(pf)) if os.path.exists(pf) else {}
        waiting = lambda k: st.get(k, {}).get("step", "").startswith("waiting for your pick") and k not in picks
        todo = [k for k in sorted(fam) if st.get(k, {}).get("step") != "done" and not waiting(k)][:a.queue]
        if not todo:
            say("nothing waiting: every sorted item is made")
    for cid in todo:
        try:
            pipeline(cid, a.redo)
        except Exception as e:
            import traceback
            traceback.print_exc()
            status(cid, step=f"stopped: {e}"[:300], ok=False)
    say("done - https://crushed-remaster.pages.dev")
