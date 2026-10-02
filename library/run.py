"""The asset pipeline, run on the Mac by itself, start to finish, for each catalog item:

  1. hunt     every photo of the real product: eBay listings, your own photos, free photo sites (hunt.py)
  2. cut out  each photo's object exactly (BiRefNet in the drawing room)
  3. check    the local vision model keeps only photos of this exact product, right era, sharp, straight-on (vet.py)
  4. skin     the good photos flattened onto the label and stitched all the way round (mosaic.py)
  5. build    the exact master shape with that skin, metal parts shiny (shapes/lathe.py in Blender)
  6. inspect  studio pictures from every side; the vision model compares them with the real photos
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


def say(*a):
    print(*a, flush=True)


def status(cid, **kw):
    os.makedirs(OUT, exist_ok=True)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s.setdefault(cid, {}).update(kw, at=time.time())
    json.dump(s, open(STATUS, "w"), indent=1)
    try:
        page()
    except Exception as e:
        say(f"(page skipped: {e})")


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
    import mosaic
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

    status(cid, product=product, step="1/6 hunting photos (eBay, your photos, free sites)")
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
    quick = V.QUICK if V.has(V.QUICK) else None
    say(f"[check] vision model: {use}" + (f" (quick first look: {quick})" if quick else ""))
    todo = [f for f in found if not (f["file"] in old and "vet" in old[f["file"]])]
    for f in found:
        if f not in todo:
            f["vet"] = old[f["file"]]["vet"]
    if quick and len(todo) > 16:                         # many photos: the small model throws out the obvious misses
        for f in todo:
            f["quick"] = V.vet(f["file"], product, era, quick) or {}
        todo.sort(key=lambda f: -(f["quick"].get("match", 0) + 3 * (f["quick"].get("era_ok") is True)))
        for f in todo[16:]:
            f["vet"] = dict(f["quick"], note="only the quick look")
        todo = todo[:16]
    for f in todo:
        f["vet"] = V.vet(f["file"], product, era, use)
        say(f"[check] {os.path.basename(f['file'])}: {json.dumps(f['vet'])[:160]}")
    json.dump(found, open(vj, "w"), indent=1)
    good = [f for f in found if V.good(f["vet"]) and f.get("mask")]
    good.sort(key=lambda f: (-(f["vet"].get("view") == "front"), -f["vet"].get("match", 0)))
    if not good:
        status(cid, step="no usable photo found", ok=False, photos=len(found))
        return

    status(cid, step=f"4/6 stitching the label from {len(good)} good photos")
    objs = []
    for f in good:
        im = Image.open(f["file"]).convert("RGB")
        m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
        objs += mosaic.objects(im, m)
    spec = json.load(open(os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json")))
    lab_pts = [pt for p in spec["profile"] if p["part"] == "label" for pt in p["pts"]]
    import math
    lab_len = sum(math.dist(lab_pts[i], lab_pts[i + 1]) for i in range(len(lab_pts) - 1))
    circ = 2 * math.pi * max(r for r, z in lab_pts)
    log = []
    lab, cov = mosaic.build(objs, W=2048, aspect=lab_len / circ, metal_top=fam.get("metal_top", False),
                            log=lambda s: (say(s), log.append(s)))
    covered = float((cov > 1e-3).mean())
    import metal
    base, mr = metal.metal_maps(Image.fromarray((lab * 255).astype(np.uint8)))
    base.save(os.path.join(d, "label.png"))
    mr.save(os.path.join(d, "label_mr.png"))

    status(cid, step="5/6 building the 3D model", covered=covered)
    mdir = os.path.join(d, "model")
    subprocess.run([PY, os.path.join(HERE, "shapes", "lathe.py"), "--", os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json"),
                    mdir, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png")], check=True,
                   capture_output=True)
    glb = os.path.join(mdir, spec["id"] + ".glb")
    pend = os.path.join(ROOT, "assets", "models_pending", cid)
    os.makedirs(pend, exist_ok=True)
    import shutil
    shutil.copy(glb, os.path.join(pend, "model.glb"))

    status(cid, step="6/6 pictures from every side and the vision model's inspection")
    subprocess.run([PY, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(d, "view.png"), "0,90,180,270"],
                   check=True, capture_output=True)
    views = [os.path.join(d, f"view_{a:03d}.png") for a in (0, 90, 180, 270)]
    sheet = Image.new("RGB", (4 * 300, 400), "white")
    for k, v in enumerate(views):
        sheet.paste(Image.open(v).convert("RGB").resize((300, 400)), (k * 300, 0))
    sheet.save(os.path.join(d, "views.jpg"), quality=88)
    verdict = inspect(views[0], good[0]["file"], product, use)
    missing = 1 - covered
    ok = verdict.get("pass", False) and missing < 0.1
    status(cid, step="done", ok=ok, verdict=verdict, covered=covered, photos=len(found), good=len(good),
           label=os.path.relpath(os.path.join(d, "label.png"), WORK), views=os.path.relpath(os.path.join(d, "views.jpg"), WORK),
           ref=os.path.relpath(good[0]["file"], WORK), stitch=log[-8:],
           note=("" if missing < 0.1 else f"{missing:.0%} of the way round has no photo yet - needs a photo of that side"))


def inspect(render, photo, product, use):
    import base64
    import vet as V
    if not use:
        return {"pass": False, "problems": "no vision model installed"}
    q = (f"Picture 1 is a 3D model of: {product}. Picture 2 is a real photo of it. Is the 3D model a faithful, "
         "finished, game-quality copy of the real product (same design, colors, printing, readable words, no smears, "
         "no seams, no holes)? Answer ONLY JSON: {\"pass\": true/false, \"problems\": \"short list or empty\"}")
    body = {"model": use, "stream": False, "format": "json", "think": False, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": q, "images": [base64.b64encode(open(p, "rb").read()).decode()
                                                                    for p in (render, photo)]}]}
    try:
        return json.loads(V._call("/api/chat", body).get("message", {}).get("content", "{}"))
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
    ap.add_argument("--only", nargs="+", required=True)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    for cid in a.only:
        try:
            pipeline(cid, a.redo)
        except Exception as e:
            import traceback
            traceback.print_exc()
            status(cid, step=f"stopped: {e}"[:300], ok=False)
    say("done - https://crushed-remaster.pages.dev")
