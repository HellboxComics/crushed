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
        "be wrinkled, shiny, dirty, faded or blurry, and it only shows the part the camera could see). Pictures 2 "
        "and 3, when given, are more photographs of the same product. Draw the COMPLETE printed label of this product "
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


def one_item(f, upright=True):
    """(photo crop, mask crop) of a single item. Several touching round things standing side by side (the cut-out
    sees one blob) are cut into equal strips, one per item, and the fullest is kept."""
    from scipy import ndimage
    im = Image.open(f["file"]).convert("RGB")
    m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) / 255.0
    lab, n = ndimage.label(m > 0.5)
    if n > 1:
        k = np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))) + 1
        m = np.where(lab == k, m, 0)
    ys, xs = np.where(m > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    n_items = int((f.get("vet") or {}).get("count") or 1)
    if upright and n_items > 1 and (y1 - y0) < 1.5 * (x1 - x0):           # wider than one standing item can be
        w = (x1 - x0) / n_items
        best = max(range(n_items), key=lambda k: m[y0:y1, int(x0 + k * w):int(x0 + (k + 1) * w)].mean())
        x0, x1 = int(x0 + (best + 0.06) * w), int(x0 + (best + 0.94) * w)  # trim the neighbors' edges
    pad = 8
    box = (max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, im.width), min(y1 + pad, im.height))
    mm = np.zeros_like(m)
    mm[y0:y1, x0:x1] = m[y0:y1, x0:x1]
    return im.crop(box), mm[box[1]:box[3], box[0]:box[2]]


def flatten(f, reads="along"):
    """The part of the label one photo can see, unrolled flat by math, in reading orientation (for a battery: the
    plus end at the left, the words running left to right)."""
    import mosaic
    im, m = one_item(f)
    objs = mosaic.objects(im, m)                                           # lying sideways, top end at the left
    o, om = max(objs, key=lambda x: x[1].sum())
    lab, w = mosaic.strip(o, om, 1024, 1024)
    seen = np.where(w > 0.05)[0]
    part = Image.fromarray((np.clip(lab[:, seen.min():seen.max() + 1], 0, 1) * 255).astype(np.uint8))
    return part.rotate(90, expand=True) if reads == "along" else part     # rows run along: turn to read


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
    part = os.path.join(out_dir, "flat_part.png")
    flatten(photos[0], reads).save(part)
    refs = [part] + [cutout(p, os.path.join(out_dir, f"ref_{i}.png")) for i, p in enumerate(photos[1:3], 1)]
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
