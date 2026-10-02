"""THE SKIN: one flat, perfect, print-ready label for an exact shape, made from real photos.

Each tool does only what it is best at:
  1. measure   the label's true size comes from the exact shape (an AA's label: 49.4 mm long, 45.6 mm around)
  2. flatten   math unrolls the part of the label each photo can see (the curve taken out, true proportions),
               so the AI never has to imagine 3D
  3. redraw    Qwen-Image-Edit-2511 (Apache 2.0, in the drawing room) gets that flat piece plus up to two more
               photos of the same product and draws the whole label clean: every word, logo and color kept,
               no wrinkles, glare or dirt, the sides no photo shows continued in the same design, at exactly
               the measured proportions
  4. check     the judge (Qwen 3.8) looks at each try next to the real photo: is it a flat label, does the print
               match, is the lettering crisp and spelled right. The best try wins; a picture of the object
               instead of a label never gets through
  5. sharpen   Real-ESRGAN doubles it so the lettering stays crisp up close

    from skin import make
    png = make(product, picked_and_two_more, along_mm, around_mm, reads="along", out_dir=...)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ai", "remaster"))

FLAT = ("Picture 1 is part of the printed label of a real product, already unrolled flat from a photograph (it may "
        "be wrinkled, shiny, dirty, faded or blurry, and it only shows the part the camera could see). Picture 2, "
        "when given, may be another part of the same label unrolled the same way (another side of it), or another "
        "photograph of the same product, as may picture 3. Draw the COMPLETE printed label of this product "
        "as one perfectly flat, clean, print-ready sheet, like the original artwork file sent to the printer: it "
        "fills the whole image edge to edge, seen straight-on, no background, no object, no shadows, no glare, no "
        "wrinkles, no curvature, no perspective, no dirt or wear. Keep every word, number, logo, symbol, color and "
        "graphic exactly as printed and in the same places and sizes, spelled exactly the same, crisp and sharp. "
        "Picture 1's part sits in the middle of the sheet, the same way up. The rest of the label, which the "
        "photographs may not show, continues in the same design, colors and lettering style; where nothing is "
        "known, continue the background color plainly and do not invent new words or logos. The left and right "
        "edges meet each other seamlessly when the sheet is wrapped around. The product: ")

JUDGE = ("Picture 1 should be the flat printed label of: {product}, unrolled flat like a sticker laid on a table. "
         "Picture 2 is a real photo of the product. Answer ONLY JSON: "
         "{{\"flat_label\": true if picture 1 is only a flat label filling the frame (not a picture of the object, "
         "no background, no perspective), \"same_design\": 0-10 how closely its printing (words, logos, colors, "
         "layout) matches picture 2, \"crisp\": true if its words are sharp and spelled correctly, "
         "\"problems\": \"short list or empty\"}}")


def label_size(spec):
    """(along_mm, around_mm) of the label part of a lathe spec: its length measured along the profile, and once
    around at its widest."""
    pts = [pt for p in spec["profile"] if p["part"] == "label" for pt in p["pts"]]
    along = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    around = 2 * math.pi * max(r for r, z in pts)
    return along, around


def all_items(f, upright=True):
    """Every single item in a photo as (photo crop, mask crop): separate items by their outlines, and several
    round things standing side by side and touching (one blob to the cut-out) cut into equal strips, one each."""
    from scipy import ndimage
    im = Image.open(f["file"]).convert("RGB")
    m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
    lab, n = ndimage.label(m > 0.5)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)) if n else []
    n_items = int((f.get("vet") or {}).get("count") or 1)
    out = []
    for k in [i + 1 for i in np.argsort(-np.asarray(sizes))]:
        if sizes[k - 1] < 0.15 * max(sizes):
            continue
        mk = np.where(lab == k, m, 0)
        ys, xs = np.where(mk > 0.5)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        strips = [(x0, x1)]
        if upright and n_items > 1 and (y1 - y0) < 1.5 * (x1 - x0):       # wider than one standing item can be
            per = max(1, round(n_items / max(1, len([s for s in sizes if s >= 0.15 * max(sizes)]))))
            w = (x1 - x0) / per
            strips = [(int(x0 + (j + 0.06) * w), int(x0 + (j + 0.94) * w)) for j in range(per)]
        for a0, a1 in strips:
            mm = np.zeros_like(m)
            mm[y0:y1, a0:a1] = mk[y0:y1, a0:a1]
            pad = 8
            box = (max(a0 - pad, 0), max(y0 - pad, 0), min(a1 + pad, im.width), min(y1 + pad, im.height))
            out.append((im.crop(box), mm[box[1]:box[3], box[0]:box[2]]))
    return out


def one_item(f, upright=True):
    """The fullest single item in a photo (see all_items)."""
    return max(all_items(f, upright), key=lambda x: (x[1] > 0.5).mean() * (x[1] > 0.5).sum() ** 0.5)


def _flat(im, m, reads):
    import mosaic
    objs = mosaic.objects(im, m)                                           # lying sideways, top end at the left
    o, om = max(objs, key=lambda x: x[1].sum())
    lab, w = mosaic.strip(o, om, 1024, 1024)
    seen = np.where(w > 0.05)[0]
    part = Image.fromarray((np.clip(lab[:, seen.min():seen.max() + 1], 0, 1) * 255).astype(np.uint8))
    return part.rotate(90, expand=True) if reads == "along" else part     # rows run along: turn to read


def flatten(f, reads="along"):
    """The part of the label one photo can see, unrolled flat by math, in reading orientation (for a battery: the
    plus end at the left, the words running left to right)."""
    return _flat(*one_item(f), reads)


def sides(f, reads="along", most=2):
    """A photo of several of the same item often shows different sides of the label (one turned to the front, one
    to the back). Each item is unrolled flat; the fullest comes first, then the one that looks most different
    from it, so the AI sees as much of the real label as the photo holds."""
    parts = []
    for im, m in all_items(f):
        try:
            parts.append(_flat(im, m, reads))
        except Exception:
            pass
    if not parts:
        return []
    small = [np.asarray(p.convert("RGB").resize((256, 96))).astype(float) for p in parts]
    first = 0
    out = [parts[first]]
    if len(parts) > 1 and most > 1:
        diff = [np.abs(sm - small[first]).mean() for sm in small]
        k = int(np.argmax(diff))
        if diff[k] > 12:                                                    # really a different side
            out.append(parts[k])
    return out


def cutout(f, out):
    """The photo's item on plain white (what the AI sees as pictures 2 and 3)."""
    im, m = one_item(f)
    a = np.asarray(im).astype(float)
    a = a * m[..., None] + 255 * (1 - m[..., None])
    Image.fromarray(a.astype(np.uint8)).save(out)
    return out


def canvas(width_mm, height_mm, mp=1.6e6):
    """Pixel size for the AI with exactly the label's proportions (both sides a multiple of 16)."""
    s = math.sqrt(mp / (width_mm * height_mm))
    return int(round(width_mm * s / 16)) * 16, int(round(height_mm * s / 16)) * 16


def make(product, photos, along_mm, around_mm, out_dir, reads="along", tries=3, judge=None, log=print):
    """photos: [picked, more of the same...] each {"file", "mask", "vet"}. Returns the finished label PNG in the
    shape's map orientation (u around, v along with the plus/top end up), or raises if no try passes."""
    import turnaround as T
    import vet as V
    os.makedirs(out_dir, exist_ok=True)
    refs = []
    for i, p in enumerate(sides(photos[0], reads)):                         # your photo, every side it shows
        refs.append(os.path.join(out_dir, f"flat_part{i + 1}.png"))
        p.save(refs[-1])
    refs += [cutout(p, os.path.join(out_dir, f"ref_{i}.png")) for i, p in enumerate(photos[1:], 1)][:3 - len(refs)]
    W_mm, H_mm = (along_mm, around_mm) if reads == "along" else (around_mm, along_mm)
    w, h = canvas(W_mm, H_mm)
    judge = judge or V.model()
    best, best_score = None, -1
    for t in range(tries):
        png = os.path.join(out_dir, f"try_{t + 1}.png")
        log(f"[skin] try {t + 1}: Qwen-Image-Edit draws the flat label, {w}x{h} ({W_mm:.1f} x {H_mm:.1f} mm)")
        T.draw_from_photos(product, refs, png, width=w, height=h, prefix=FLAT, seed=1000 + t)
        try:
            v = V.ask(judge, JUDGE.format(product=product), [png, photos[0]["file"]])
        except Exception as e:
            v = {"flat_label": False, "problems": f"could not judge: {e}"}
        score = (v.get("same_design", 0) + (3 if v.get("crisp") else 0)) if v.get("flat_label") else -1
        log(f"[skin] try {t + 1}: {json.dumps(v)[:200]}")
        json.dump(v, open(png[:-4] + ".json", "w"), indent=1)
        if score > best_score:
            best, best_score = png, score
        if v.get("flat_label") and v.get("same_design", 0) >= 9 and v.get("crisp"):
            break                                                          # good enough: stop early
    if best_score < 0:
        raise RuntimeError("none of the AI's label tries was a clean flat label")
    T.upscale(best, force=True)
    lab = Image.open(best).convert("RGB")
    if reads == "along":
        lab = lab.rotate(-90, expand=True)                                 # back to the map: plus end up
    lab = lab.resize((2048, int(round(2048 * along_mm / around_mm))), Image.LANCZOS)
    out = os.path.join(out_dir, "label.png")
    lab.save(out)
    return out, best_score


# ------------------------------------------------------------------ boxes and flat things: one face at a time

FACE = ("Picture 1 is one side of a real product's box or package, already straightened flat from a photograph (it "
        "may be creased, shiny, faded or blurry). Pictures 2 and 3, when given, are more photographs of the same "
        "product. Draw THIS SIDE as one perfectly flat, clean, print-ready panel, like the original artwork file sent "
        "to the printer: it fills the whole image edge to edge, straight-on, no background, no shadows, no glare, no "
        "creases, no perspective, no wear. Keep every word, number, logo, picture and color exactly as printed, in the "
        "same places and sizes, spelled exactly the same, crisp and sharp. The product: ")

FACE_NEW = ("Picture 1 is the clean front panel of a real product's box or package. Draw its {side} panel - the {side} "
            "side of the very same box - as one perfectly flat, clean, print-ready panel that fills the whole image "
            "edge to edge, straight-on, no background, no shadows. Use the same design, colors and lettering style "
            "as the front. Put only what that side of such a package really carries (for example the brand, the "
            "name, a short description, a plain panel); do not copy the front, and do not invent long blocks of "
            "small text, barcodes or prices. The product: ")


def face(product, side, w_mm, h_mm, out_dir, photo=None, refs=(), front=None, judge=None, log=print, tries=2):
    """One side of a box as a flat print-ready panel at exactly w_mm x h_mm. From its own photo when there is
    one (straightened, then redrawn clean), else drawn by the AI from the clean front."""
    import panels
    import turnaround as T
    import vet as V
    os.makedirs(out_dir, exist_ok=True)
    w, h = canvas(w_mm, h_mm, mp=1.2e6)
    imgs = []
    if photo is not None:
        im = Image.open(photo["file"]).convert("RGB")
        m = np.asarray(Image.open(photo["mask"]).convert("L").resize(im.size)) / 255.0
        flat, fit = panels.flatten(im, m, w, h)
        if flat is not None and fit >= 0.8:
            src = os.path.join(out_dir, f"{side}_photo.png")
            flat.save(src)
            imgs = [src] + [cutout(r, os.path.join(out_dir, f"{side}_ref{i}.png")) for i, r in enumerate(refs[:2], 1)]
    prefix = FACE if imgs else FACE_NEW.format(side=side)
    if not imgs:
        if not front:
            return None
        imgs = [front]
    judge = judge or V.model()
    best, best_score = None, -1
    for t in range(tries):
        png = os.path.join(out_dir, f"{side}_try{t + 1}.png")
        log(f"[skin] {side}: Qwen-Image-Edit draws it flat, {w}x{h} ({w_mm:.0f} x {h_mm:.0f} mm), try {t + 1}")
        T.draw_from_photos(product, imgs, png, width=w, height=h, prefix=prefix, seed=2000 + t)
        try:
            v = V.ask(judge, JUDGE.format(product=product).replace("flat printed label", f"flat printed {side} panel"),
                      [png, (photo or {}).get("file") or imgs[0]])
        except Exception as e:
            v = {"flat_label": False, "problems": f"could not judge: {e}"}
        score = (v.get("same_design", 0) + (3 if v.get("crisp") else 0)) if v.get("flat_label") else -1
        log(f"[skin] {side} try {t + 1}: {json.dumps(v)[:160]}")
        if score > best_score:
            best, best_score = png, score
        if score >= 11:
            break
    if best_score < 0:
        return None
    out = os.path.join(out_dir, f"{side}.png")
    Image.open(best).convert("RGB").resize((w, h), Image.LANCZOS).save(out)
    return out


def box_skin(product, W, D, H, photos, out_dir, flat=False, judge=None, log=print):
    """All six sides of a box (two for a flat thing) -> one atlas laid out the way shapes/box.py maps it.
    photos: [picked, more of the same...], each with its vet "view"."""
    import panels
    mm = lambda x: x * 1000
    sides = {"front": (W, H), "back": (W, H)} if flat else \
        {"front": (W, H), "back": (W, H), "left": (D, H), "right": (D, H), "top": (W, D), "bottom": (W, D)}
    by_view = {}
    for p in photos:
        v = (p.get("vet") or {}).get("view")
        if v in sides and v not in by_view and (p.get("vet") or {}).get("straight_on", True):
            by_view[v] = p
    by_view.setdefault("front", photos[0])
    faces = {}
    faces["front"] = face(product, "front", mm(W), mm(H), out_dir, photo=by_view["front"], refs=photos[1:3],
                          judge=judge, log=log)
    if not faces["front"]:
        raise RuntimeError("the AI could not draw a clean front")
    biggest = max(max(d) for d in sides.values())
    for side, (a, b) in sides.items():
        if side == "front":
            continue
        if min(a, b) < 0.12 * biggest:                        # a thin edge: plain, in the front's edge color
            faces[side] = None
            continue
        faces[side] = face(product, side, mm(a), mm(b), out_dir, photo=by_view.get(side), front=faces["front"],
                           judge=judge, log=log, tries=1)
    atlas = panels.assemble({k: v for k, v in faces.items() if v}, W, D, H)
    out = os.path.join(out_dir, "atlas.png")
    atlas.save(out)
    return out, {k: bool(v) for k, v in faces.items()}
