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
    quick = V.quick_model()
    say(f"[check] vision model: {use}" + (f" (quick first look: {quick})" if quick else ""))
    todo = [f for f in found if not (f["file"] in old and "vet" in old[f["file"]])]
    for f in found:
        if f not in todo:
            f["vet"] = old[f["file"]]["vet"]
    if quick and len(todo) > 16:                         # many photos: the small model throws out the obvious misses
        for f in todo:
            f["quick"] = V.vet(f["file"], product, era, quick, think=False) or {}
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

    plan = json.load(open(os.path.join(ROOT, "assets", "plan", "items.json"))).get(cid, {})
    size = plan.get("size") or [0.1, 0.1, 0.1]
    mdir = os.path.join(d, "model")
    log = []
    if fam["family"] == "round":
        glb, covered = build_round(cid, fam, good, d, mdir, log)
    elif fam["family"] in ("box", "flat"):
        glb, covered = build_box(cid, fam, good, d, mdir, size, log)
    elif fam["family"] == "soft":
        glb, covered = build_soft(cid, fam, good, d, mdir, size, log)
    else:
        status(cid, step=f"no builder for the '{fam['family']}' family yet", ok=False)
        return
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
    verdict = inspect(os.path.join(d, "views.jpg"), good[0]["file"], product, use)
    tex = os.path.join(d, "label.png") if os.path.exists(os.path.join(d, "label.png")) else os.path.join(d, "atlas.png")
    missing = 1 - covered
    ok = verdict.get("pass", False) and missing < 0.1
    status(cid, step="done", ok=ok, verdict=verdict, covered=covered, photos=len(found), good=len(good),
           label=os.path.relpath(tex, WORK) if os.path.exists(tex) else None, views=os.path.relpath(os.path.join(d, "views.jpg"), WORK),
           ref=os.path.relpath(good[0]["file"], WORK), stitch=log[-8:],
           note=("" if missing < 0.1 else f"{missing:.0%} of the way round has no photo yet - needs a photo of that side"))


def _objs(good):
    import numpy as np
    from PIL import Image
    out = []
    for f in good:
        im = Image.open(f["file"]).convert("RGB")
        m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
        out.append((f, im, m))
    return out


def build_round(cid, fam, good, d, mdir, log):
    """Round things (batteries, cans, bottles): the exact master shape, the label stitched from the photos."""
    import math
    import numpy as np
    from PIL import Image
    import metal
    import mosaic
    status(cid, step=f"4/6 stitching the label from {len(good)} good photos")
    objs = []
    for f, im, m in _objs(good):
        objs += mosaic.objects(im, m)
    spec = json.load(open(os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json")))
    lab_pts = [pt for p in spec["profile"] if p["part"] == "label" for pt in p["pts"]]
    lab_len = sum(math.dist(lab_pts[i], lab_pts[i + 1]) for i in range(len(lab_pts) - 1))
    circ = 2 * math.pi * max(r for r, z in lab_pts)
    lab, cov = mosaic.build(objs, W=2048, aspect=lab_len / circ, metal_top=fam.get("metal_top", False),
                            log=lambda s: (say(s), log.append(s)))
    covered = float((cov > 1e-3).mean())
    base, mr = metal.metal_maps(Image.fromarray((lab * 255).astype(np.uint8)))
    base.save(os.path.join(d, "label.png"))
    mr.save(os.path.join(d, "label_mr.png"))
    status(cid, step="5/6 building the 3D model", covered=covered)
    subprocess.run([PY, os.path.join(HERE, "shapes", "lathe.py"), "--", os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json"),
                    mdir, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png")], check=True, capture_output=True)
    return os.path.join(mdir, spec["id"] + ".glb"), covered


def build_box(cid, fam, good, d, mdir, size, log):
    """Boxes and flat things: the exact box at real size, each side straightened from a photo of that side."""
    import panels
    status(cid, step=f"4/6 straightening the sides from {len(good)} good photos")
    W, D, H = (fam.get("size") or size)[:3]
    if fam["family"] == "flat":
        D = max(D, 0.0003)
    photos = [(im, m, f["vet"].get("view", "")) for f, im, m in _objs(good)]
    atlas, got = panels.build(photos, W, D, H)
    atlas.save(os.path.join(d, "atlas.png"))
    area = {"front": W * H, "back": W * H, "left": D * H, "right": D * H, "top": W * D, "bottom": W * D}
    covered = sum(area[k] for k, v in got.items() if v) / sum(area.values())
    missing = [k for k, v in got.items() if not v]
    log.append("sides from photos: " + ", ".join(k for k, v in got.items() if v) + "; no photo yet: " + ", ".join(missing))
    status(cid, step="5/6 building the 3D model", covered=covered)
    subprocess.run([PY, os.path.join(HERE, "shapes", "box.py"), "--", str(W), str(D), str(H), mdir,
                    os.path.join(d, "atlas.png"), "-", cid, "0.3" if fam["family"] == "flat" else "0.6"],
                   check=True, capture_output=True)
    return os.path.join(mdir, cid + ".glb"), covered


def build_soft(cid, fam, good, d, mdir, size, log):
    """Soft and odd shapes (plush, food, toys): Hunyuan3D 2.1 (Apple-chip build) makes the shape and paints it
    from the best photo; Blender sets the real size and saves every format."""
    from PIL import Image
    import numpy as np
    status(cid, step="4/6 Hunyuan3D 2.1 is making the shape and paint from the best photo")
    f, im, m = _objs(good[:1])[0]
    ys, xs = np.where(m > 0.5)                          # crop to the object, square, with a little room around it
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    side = int(max(y1 - y0, x1 - x0) * 1.15)
    rgba = np.dstack([np.asarray(im), (m * 255).astype(np.uint8)])[y0:y1, x0:x1]
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(Image.fromarray(rgba), ((side - (x1 - x0)) // 2, (side - (y1 - y0)) // 2))
    ref = os.path.join(d, "reference.png")
    sq.resize((1024, 1024), Image.LANCZOS).save(ref)
    os.makedirs(mdir, exist_ok=True)
    sys.path.insert(0, HERE)
    import hunyuan
    hy = hunyuan.home()
    if not hy:
        raise RuntimeError("Hunyuan3D is not installed yet - run the setup paste")
    r = subprocess.run([os.path.join(hy, ".venv", "bin", "python"), os.path.join(HERE, "hunyuan.py"), ref,
                        os.path.join(mdir, "hunyuan")], capture_output=True, text=True)
    log.append((r.stdout + r.stderr)[-600:])
    if r.returncode != 0 or not os.path.exists(os.path.join(mdir, "hunyuan", "textured.glb")):
        raise RuntimeError("Hunyuan3D did not finish: " + (r.stderr or r.stdout)[-300:])
    status(cid, step="5/6 setting the real size and saving every format", covered=1.0)
    subprocess.run([PY, os.path.join(HERE, "shapes", "resize.py"), "--", os.path.join(mdir, "hunyuan", "textured.glb"),
                    str(max(size)), mdir, cid], check=True, capture_output=True)
    return os.path.join(mdir, cid + ".glb"), 1.0


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
    a = ap.parse_args()
    todo = a.only or []
    if a.queue:
        fam = {k: v for k, v in json.load(open(os.path.join(HERE, "families.json"))).items() if not k.startswith("_")}
        st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
        todo = [k for k in sorted(fam) if st.get(k, {}).get("step") != "done"][:a.queue]
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
