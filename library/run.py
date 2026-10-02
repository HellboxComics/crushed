"""THE ASSET MAKER - one catalog item in, one finished, real-size 3D asset out (.glb .fbx .usdc .blend).
Runs on your Mac with your own AI. The same steps for every item, a Duracell, a Furby, a Duncan yo-yo or Gak:

  0. card     your AI writes the item's card once: which build route, what you can SEE that marks this exact
              version, what marks a wrong one, what a collector would search (cards.py)
  1. hunt     Google Images with the card's searches, plus your own photos first (hunt.py)
  2. cut out  each photo's item exactly (BiRefNet in the drawing room)
  3. rank     the judge scores every photo against the card (how many right-version marks it shows, any
              wrong-version mark, real photo or ad); the real size from the catalog throws out wrong shapes
  4. pick     the best 9 go to your phone (Hart's Telegram); you tap the true one, or "None of these" and it
              digs deeper
  5. build    by the card's route:
                round  the exact shape traced from your photo at real size (or a measured master like the AA);
                       the AI redraws one flat, perfect label to fit it (skin.py)
                box    the exact box at real size; every face redrawn flat by the AI at its measured size
                flat   the same, two faces
                free   Hunyuan3D makes the shape and paint from your photo; Blender sets the real size
  6. check    studio pictures from four sides; the judge compares them with your photo
  7. you      the pictures go to your phone with Keep / Redo. Kept assets go to ~/Desktop/Asset Library/<item>

    .venv/bin/python library/run.py --only furby_gray_pink_1998 [--wait] [--redo]
    .venv/bin/python library/run.py --queue 2          (the clock: the next 2 items in library/queue.txt)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "ai", "remaster"))
sys.path.insert(0, os.path.join(ROOT, "ai"))
sys.path.insert(0, os.path.expanduser("~/.hellbox/ai"))
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "library")
SHELF = os.path.expanduser("~/Desktop/Asset Library")
PY = sys.executable
STATUS = os.path.join(OUT, "status.json")
WAIT = False          # --wait: a run you started yourself waits for your tap instead of moving on
HB = os.path.expanduser("~/.hellbox")


def jload(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def pipeline(cid, redo=False):
    import cards
    import hunt
    import turnaround as T
    import vet as V
    from PIL import Image
    d = os.path.join(OUT, cid)
    os.makedirs(d, exist_ok=True)
    mdir = os.path.join(d, "model")

    # your Keep / Redo from last time
    ap = jload(os.path.join(HB, "approvals.json"), {})
    if ap.get(cid, {}).get("say") == "keep":
        file_away(cid, d)
        return
    if ap.get(cid, {}).get("say") == "redo":
        start_over(cid, d)

    card = cards.make(cid, log=say)
    product, size, year, route = card["product"], card["size"], card.get("year"), card["route"]
    if jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape"):
        route = "round"                                          # it has a measured master shape (the AA)
    status(cid, product=product, route=route, step="1/7 hunting photos (Google Images, your photos)")
    fj = os.path.join(WORK, "hunt", cid, "found.json")
    found = jload(fj, None) if os.path.exists(fj) and not redo else None
    if found is None:
        found = hunt.run(cid, product.split(",")[0], year, log=say, extra=card["searches"])

    status(cid, step=f"2/7 cutting out {len(found)} photos")
    T.free_room()
    for f in found:
        try:
            f["mask"] = T.photo_mask(f["file"])
        except Exception as e:
            say(f"[cut out] {os.path.basename(f['file'])}: {e}")

    status(cid, step="3/7 ranking the photos against the card")
    T.free_room()
    vj = os.path.join(d, "vetted.json")
    old = {v["file"]: v for v in jload(vj, [])} if not redo else {}
    use, quick = V.model(), V.quick_model()
    for i, f in enumerate(found):
        f["order"] = i
        f["vet"] = (old.get(f["file"]) or {}).get("vet")
    todo = [f for f in found if not f["vet"] and f.get("mask")][:60]   # 60 a round, in Google's order
    if quick and len(todo) > 12:
        for k, f in enumerate(todo, 1):
            f["quick"] = V.vet(f["file"], product, use=quick, think=False, card=card) or {}
            say(f"[quick look {k}/{len(todo)}] {os.path.basename(f['file'])}: match {f['quick'].get('match')}, "
                f"marks seen {f['quick'].get('seen')}, {f['quick'].get('kind')}")
        todo.sort(key=lambda f: -rank(dict(f, vet=f["quick"])))
        for f in todo[12:]:
            f["vet"] = dict(f["quick"], note="only the quick look")
        todo = todo[:12]
    for k, f in enumerate(todo, 1):
        status(cid, step=f"3/7 {use} ranks the best photos: {k} of {len(todo)}")
        f["vet"] = V.vet(f["file"], product, use=use, think=False, card=card)
        say(f"[check] {os.path.basename(f['file'])}: {json.dumps(f['vet'])[:160]}")
    json.dump(found, open(vj, "w"), indent=1)

    shown = jload(os.path.join(d, "shown.json"), [])
    cands = [f for f in found if f.get("mask") and f.get("vet") and f["vet"].get("match", 0) >= 7
             and f["vet"].get("sharp", True) is not False and f["vet"].get("whole", True) is not False
             and f["file"] not in shown and size_fits(f, size)]
    cands.sort(key=lambda f: -rank(f))
    picked = your_pick(cid, product, cands[:9], d)
    if picked == "none":                                          # you said none: dig deeper, then ask again
        rounds = len([1 for k in os.listdir(d) if k.startswith("round_")])
        if rounds >= 3:
            status(cid, step="3 rounds and none was right - it needs a photo of your own: put it in "
                             f"~/crushed-render/remaster/refs-mine named {cid}_1.jpg", ok=False)
            return
        open(os.path.join(d, f"round_{rounds + 1}"), "w").write("")
        status(cid, step=f"you said none fit - digging deeper (round {rounds + 2})")
        hunt.run(cid, product.split(",")[0], year, log=say, extra=more_searches(card, use))
        return pipeline(cid, redo=False)
    if not picked:
        return
    others = [c for c in cands if c["file"] != picked["file"]]

    # 5. BUILD by the card's route
    if route == "round":
        import metal
        import profile
        import skin
        fam = jload(os.path.join(HERE, "families.json"), {}).get(cid, {})
        sp = os.path.join(HERE, "shapes", "specs", fam.get("shape", "") + ".json")
        if fam.get("shape") and os.path.exists(sp):
            spec = json.load(open(sp))                                # a measured master (the AA battery)
        else:
            status(cid, step="5/7 tracing the exact round shape from your photo at real size")
            spec = profile.from_photo(picked, size, card.get("standing") or "upright", cid=cid)
            sp = os.path.join(d, "shape.json")
            json.dump(spec, open(sp, "w"), indent=1)
        along, around = skin.label_size(spec)
        same = same_design(picked, others, use)
        status(cid, step=f"5/7 the AI draws the flat label from {1 + len(same)} photos ({along:.0f} x {around:.0f} mm)")
        reads = spec.get("label_reads") or card.get("label_reads") or "around"
        lab_png, _ = skin.make(product, [picked] + same, along, around, os.path.join(d, "skin"),
                               reads="along" if reads == "along" else "around", judge=use, log=say)
        base, mr = metal.metal_maps(Image.open(lab_png).convert("RGB"))
        base.save(os.path.join(d, "label.png"))
        mr.save(os.path.join(d, "label_mr.png"))
        status(cid, step="5/7 Blender builds the exact shape wearing the label")
        run_blender("lathe.py", sp, mdir, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png"))
        for ext in ("glb", "fbx", "usdc", "blend"):
            if os.path.exists(os.path.join(mdir, spec["id"] + "." + ext)):
                shutil.copy(os.path.join(mdir, spec["id"] + "." + ext), os.path.join(mdir, cid + "." + ext))
    elif route in ("box", "flat"):
        import skin
        W, D, H = size[:3]
        if route == "flat":
            D = min(D, 0.002)
        same = same_design(picked, others, use, want=5)
        status(cid, step="5/7 the AI draws every face flat at its measured size")
        atlas, got = skin.box_skin(product, W, D, H, [picked] + same, os.path.join(d, "skin"),
                                   flat=route == "flat", judge=use, log=say)
        status(cid, step="5/7 Blender builds the exact box wearing its faces")
        run_blender("box.py", str(W), str(max(D, 0.0003)), str(H), mdir, atlas, "-", cid,
                    "0.3" if route == "flat" else "0.6")
    else:
        ref = reference(picked, d)
        status(cid, step="5/7 Hunyuan3D makes the shape and paint from your photo")
        painted = hunyuan_paint(ref, os.path.join(mdir, "hunyuan"))
        status(cid, step="5/7 Blender: real size, every format")
        run_blender("resize.py", painted, str(max(size)), mdir, cid)
    glb = os.path.join(mdir, cid + ".glb")

    # 6. CHECK: four sides against your photo
    status(cid, step="6/7 pictures from four sides and the judge's check")
    subprocess.run([PY, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(d, "view.png"), "0,90,180,270"],
                   check=True, capture_output=True)
    sheet = Image.new("RGB", (4 * 300, 400), "white")
    for k, a in enumerate((0, 90, 180, 270)):
        sheet.paste(Image.open(os.path.join(d, f"view_{a:03d}.png")).convert("RGB").resize((300, 400)), (k * 300, 0))
    sheet.save(os.path.join(d, "views.jpg"), quality=88)
    verdict = inspect(os.path.join(d, "views.jpg"), picked["file"], product, use)

    # 7. YOU: Keep or Redo on your phone
    import askfirst
    probs = verdict.get("problems")
    note = ("The judge: looks right." if verdict.get("pass") else "The judge: " + (", ".join(probs) if isinstance(probs, list) else str(probs)))
    askfirst.ask_review(cid, product, os.path.join(d, "views.jpg"), note[:600])
    tex = next((p for p in (os.path.join(d, "label.png"), os.path.join(d, "skin", "atlas.png"),
                            os.path.join(d, "reference.png")) if os.path.exists(p)), None)
    status(cid, step="waiting for your Keep or Redo on your phone", ok=bool(verdict.get("pass")), verdict=verdict,
           photos=len(found), good=len(cands), views=os.path.relpath(os.path.join(d, "views.jpg"), WORK),
           label=os.path.relpath(tex, WORK) if tex else None, ref=os.path.relpath(picked["file"], WORK), note="")


def run_blender(script, *args):
    r = subprocess.run([PY, os.path.join(HERE, "shapes", script), "--", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Blender ({script}) failed: " + (r.stderr or r.stdout)[-400:])


def rank(f):
    """Which photos you see first - the same rule for every item: the card's right-version marks it shows count
    most, a wrong-version mark sinks it, a real photo beats an ad or a render, Google's own order breaks ties."""
    v = f["vet"] or {}
    r = v.get("match", 0) + 3 * min(int(v.get("seen") or 0), 5)
    r -= 8 if v.get("avoid_seen") is True else 0
    r += {"photo": 4, "package": 1, "render": -2, "ad": -4}.get(v.get("kind"), 0)
    r += 0.5 if v.get("view") == "front" else 0
    return r - f.get("order", 0) * 0.02


def size_fits(f, size_m, tol=0.35):
    """The item's outline in the photo must have the proportions of the real thing (any two of its catalog
    sides), so a D cell never passes for an AA and a tub never for a bottle. Several touching items can't be
    measured one by one, so those are left for you to judge."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    m = np.asarray(Image.open(f["mask"]).convert("L")) > 127
    lab, n = ndimage.label(m)
    if not n:
        return False
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == k)
    h, w = int(np.ptp(ys)) + 1, int(np.ptp(xs)) + 1
    got = max(h, w) / max(min(h, w), 1)
    dims = sorted(x for x in size_m if x > 0)
    wants = {dims[i] / dims[j] for i in range(len(dims)) for j in range(i) if dims[j] > 0}
    if any(abs(got - w) / w <= tol for w in wants):
        return True
    return int((f.get("vet") or {}).get("count") or 1) > 1


def more_searches(card, use):
    """When you turn every photo down: different searches than last time, the way a collector digs."""
    import vet as V
    q = (f"I need real photos of this exact old product: {card['product']}. It is recognized by: "
         f"{'; '.join(card.get('recognize', []))}. These searches did not find it: {'; '.join(card.get('searches', []))}. "
         "Give 5 different Google Images searches a collector would type (other names it was sold under, its "
         "model or catalog number, 'vintage', 'NOS', 'eBay', the decade). Answer ONLY JSON: {\"searches\": [\"...\"]}")
    try:
        body = {"model": use, "stream": False, "format": "json", "think": True, "options": {"temperature": 0.4},
                "messages": [{"role": "user", "content": q}]}
        out = [x for x in json.loads(V._call("/api/chat", body)["message"]["content"]).get("searches", [])
               if isinstance(x, str)][:5]
    except Exception as e:
        say(f"[hunt] no new searches: {e}")
        out = []
    say("[hunt] digging deeper with: " + "; ".join(out))
    return out


def file_away(cid, d):
    """You said Keep: every format, the textures and your reference photo into ~/Desktop/Asset Library/<item>."""
    dst = os.path.join(SHELF, cid)
    os.makedirs(dst, exist_ok=True)
    mdir = os.path.join(d, "model")
    for ext in ("glb", "fbx", "usdc", "blend"):
        p = os.path.join(mdir, cid + "." + ext)
        if os.path.exists(p):
            shutil.copy(p, dst)
    if os.path.isdir(os.path.join(mdir, "textures")):
        shutil.copytree(os.path.join(mdir, "textures"), os.path.join(dst, "textures"), dirs_exist_ok=True)
    for name in ("label.png", "label_mr.png", "views.jpg", "reference.png"):
        if os.path.exists(os.path.join(d, name)):
            shutil.copy(os.path.join(d, name), dst)
    if os.path.exists(os.path.join(d, "skin", "atlas.png")):
        shutil.copy(os.path.join(d, "skin", "atlas.png"), dst)
    pend = os.path.join(ROOT, "assets", "models_pending", cid)
    os.makedirs(pend, exist_ok=True)
    if os.path.exists(os.path.join(mdir, cid + ".glb")):
        shutil.copy(os.path.join(mdir, cid + ".glb"), os.path.join(pend, "model.glb"))
    status(cid, step="done - kept in your Asset Library", ok=True, note=dst)
    say(f"[keep] {cid} -> {dst}")


def start_over(cid, d):
    """You said Redo: the build is set aside (in _to delete, never deleted) and it is made again from your pick."""
    ap = jload(os.path.join(HB, "approvals.json"), {})
    ap.pop(cid, None)
    json.dump(ap, open(os.path.join(HB, "approvals.json"), "w"), indent=1)
    trash = os.path.expanduser(f"~/Desktop/_to delete/remaster/{cid}-redo-{time.strftime('%Y%m%d-%H%M%S')}")
    for name in ("model", "skin"):
        if os.path.exists(os.path.join(d, name)):
            os.makedirs(trash, exist_ok=True)
            shutil.move(os.path.join(d, name), os.path.join(trash, name))
    say(f"[redo] {cid}: the old build is in {trash}")


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


def your_pick(cid, product, cands, d):
    """The photo you picked on your phone, or None while we wait (or if you said none of these)."""
    picks_f = os.path.expanduser("~/.hellbox/picks.json")
    cf = os.path.join(d, "candidates.json")
    picks = json.load(open(picks_f)) if os.path.exists(picks_f) else {}
    p = picks.get(cid)
    if p and os.path.exists(cf):
        shown = json.load(open(cf))["files"]
        if p["pick"] == "none":
            sf = os.path.join(d, "shown.json")
            old = json.load(open(sf)) if os.path.exists(sf) else []
            json.dump(old + [x["file"] for x in shown], open(sf, "w"), indent=1)
            os.remove(cf)
            picks.pop(cid)
            json.dump(picks, open(picks_f, "w"), indent=1)
            return "none"
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
    if cid in picks:                                   # a tap on an older photo sheet must not count for this one
        picks.pop(cid)
        json.dump(picks, open(picks_f, "w"), indent=1)
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
    cols = 3 if len(cands) > 2 else len(cands)        # up to 9: three rows of three
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
    """Your photo's item, cut out, centered on white with room around it - what Hunyuan looks at."""
    import numpy as np
    from PIL import Image
    import skin
    im, m = skin.one_item(f, upright)
    rgba = np.dstack([np.asarray(im), (m * 255).astype(np.uint8)])
    obj = Image.fromarray(rgba)
    side = int(max(obj.size) * 1.15)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(obj, ((side - obj.width) // 2, (side - obj.height) // 2), obj)
    out = os.path.join(d, "reference.png")
    sq.resize((1024, 1024), Image.LANCZOS).save(out)
    return out


def same_design(picked, others, use, want=2):
    """Up to two more photos the judge says show the very same design as your pick (for consistency)."""
    import vet as V
    q = ("Do these two photos show the very same product design version (same label artwork, same words and "
         "layout, same colors), even if the angle or lighting differs? Answer ONLY JSON: {\"same\": true/false}")
    out = []
    for f in others[:8]:
        try:
            if V.ask(use, q, [picked["file"], f["file"]], think=False).get("same") is True:
                out.append(f)
        except Exception:
            pass
        if len(out) >= want:
            break
    say(f"[skin] same design as your pick: {len(out)} more photo(s)")
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


def queue(n):
    """The next n items to make, in the order of library/queue.txt (one item per line), skipping ones done and
    ones waiting on you (a pick or a Keep/Redo you haven't given yet)."""
    q = [l.strip() for l in open(os.path.join(HERE, "queue.txt")) if l.strip() and not l.startswith("#")] \
        if os.path.exists(os.path.join(HERE, "queue.txt")) else []
    st = jload(STATUS, {})
    picks = jload(os.path.join(HB, "picks.json"), {})
    ap = jload(os.path.join(HB, "approvals.json"), {})
    out = []
    for cid in q:
        step = st.get(cid, {}).get("step", "")
        if step.startswith(("done", "stopped", "3 rounds")):
            continue
        if step.startswith("waiting for your pick") and cid not in picks:
            continue
        if step.startswith("waiting for your Keep") and cid not in ap:
            continue
        out.append(cid)
    return out[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--queue", type=int, default=0, help="make up to N items from library/queue.txt")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--wait", action="store_true", help="wait for your photo pick on the phone")
    ap.add_argument("--loop", action="store_true", help="keep working through the queue: an item waiting on "
                    "your tap is set aside and picked up again the minute you tap; stops after 3 quiet hours")
    a = ap.parse_args()
    WAIT = a.wait
    if a.loop:
        quiet = 0
        while quiet < 360:
            todo = queue(a.queue or 3)
            for cid in todo:
                try:
                    pipeline(cid, False)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    status(cid, step=f"stopped: {e}"[:300], ok=False)
            busy = [c for c in todo if not jload(STATUS, {}).get(c, {}).get("step", "").startswith(("waiting", "done", "stopped", "3 rounds"))]
            quiet = 0 if busy else quiet + 1
            time.sleep(0 if busy else 30)
        sys.exit(0)
    todo = a.only or (queue(a.queue) if a.queue else [])
    if a.queue and not todo:
        say("nothing waiting: every queued item is made or waiting on you")
    for cid in todo:
        try:
            pipeline(cid, a.redo)
        except Exception as e:
            import traceback
            traceback.print_exc()
            status(cid, step=f"stopped: {e}"[:300], ok=False)
    say("done - https://crushed-remaster.pages.dev")
