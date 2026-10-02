"""THE TEXTURE MAP: the flat image laid on an exact mesh's UV map (the battery's label rectangle, a box's six
faces), made from real photos.

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


FILL = ("This is a flat printed label laid out like a sheet. The gray areas are parts of the label nobody "
        "photographed. Fill ONLY those gray areas so the label continues seamlessly: the same background colors, "
        "bands and patterns carried across. Do not add any new words, numbers or logos there, and do not change "
        "anything outside the gray areas. The product: ")


def compose(photos, along_mm, around_mm, W=2048):
    """The label made from the photos' REAL pixels: each item in your photo unrolled flat by math and laid at its
    place around the label (the fullest at the front; one showing a clearly different side at the back).
    -> (label RGB float H x W in the map layout: rows along with the top/plus end up, columns around with the
        front in the middle), coverage 0..1 per pixel)."""
    import mosaic
    H = int(round(W * along_mm / around_mm))
    lab = np.zeros((H, W, 3))
    cov = np.zeros((H, W))
    strips = []
    for f in photos[:1]:
        for im, m in all_items(f):
            objs = mosaic.objects(im, m)
            o, om = max(objs, key=lambda x: x[1].sum())
            try:
                strips.append(mosaic.strip(o, om, W, H))
            except Exception:
                pass
    if not strips:
        raise RuntimeError("could not unroll the label from your photo")
    strips.sort(key=lambda lw: -lw[1].sum())
    keep = [strips[0]]
    small = lambda x: x[::16, ::16].mean(-1)
    diffs = []
    for l, w in strips[1:]:
        k = keep[0]
        both = (k[1] > 0.05) & (w > 0.05)
        diffs.append(np.abs(small(k[0])[:, both[::16]] - small(l)[:, both[::16]]).mean() if both.any() else 0)
    if diffs and max(diffs) > 0.05:                                         # the most different one shows another side
        l, w = strips[1 + int(np.argmax(diffs))]
        keep.append((np.roll(l, W // 2, axis=1), np.roll(w, W // 2)))     # it goes at the back
    for l, w in keep:
        better = w[None, :] > cov
        lab = np.where(better[..., None], l, lab)
        cov = np.maximum(cov, np.broadcast_to(w[None, :], cov.shape))
    return lab, cov


def make(product, photos, along_mm, around_mm, out_dir, reads="along", tries=1, judge=None, log=print):
    """The finished flat label: real pixels wherever your photo shows the label; the AI fills only the parts no
    photo shows (it cannot touch the rest), then Real-ESRGAN sharpens it. -> (label png in the map layout, score)"""
    import turnaround as T
    os.makedirs(out_dir, exist_ok=True)
    lab, cov = compose(photos, along_mm, around_mm)
    gaps = cov < 0.05
    real = os.path.join(out_dir, "label_real.png")
    Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8)).save(real)
    log(f"[texture] real pixels cover {(~gaps).mean():.0%} of the label")
    out = os.path.join(out_dir, "label.png")
    if gaps.mean() > 0.01:
        log(f"[texture] the {gaps.mean():.0%} nobody photographed: the real colors carried across (no AI, no invented words)")
        lab = continue_bands(lab, gaps)
    Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8)).save(out)
    clean = os.path.join(out_dir, "cleaned.png")
    try:
        log("[texture] the AI cleans off glare and shine (an edit: everything else kept)")
        cleanup(product, out, clean, reads)
        if same_words(out, clean, judge, log):
            Image.open(clean).convert("RGB").resize(Image.open(out).size, Image.LANCZOS).save(out)
        else:
            log("[texture] the clean-up changed some words - kept the real-pixel label instead")
    except Exception as e:
        log(f"[texture] clean-up skipped: {e}")
    T.upscale(out, force=True)
    return out, float((~gaps).mean())


CLEAN = ("This is a flat printed label photographed in poor light. Remove the glare, shine, reflections, creases, "
         "dirt and blur so it looks like the clean printed original. Keep EVERYTHING else exactly as it is: every "
         "word, number, letter, logo, color and position unchanged. Do not add or remove anything. The product: ")


def cleanup(product, src, out, reads="along"):
    """Qwen-Image-Edit as an editor (its strength), not a painter: glare and wear off, nothing else changed."""
    import turnaround as T
    im = Image.open(src).convert("RGB")
    if reads == "along":
        im = im.rotate(90, expand=True)
    w, h = canvas(im.width, im.height)
    tmp = out[:-4] + "_in.png"
    im.resize((w, h), Image.LANCZOS).save(tmp)
    T.draw_from_photos(product, [tmp], out, width=w, height=h, prefix=CLEAN, seed=11)
    got = Image.open(out).convert("RGB")
    if reads == "along":
        got = got.rotate(-90, expand=True)
    got.save(out)


def same_words(a, b, judge=None, log=print):
    """The judge reads every word on both labels; the clean-up is kept only if the words are the same."""
    import vet as V
    judge = judge or V.model()
    q = 'Read every word and number printed in this picture. Answer ONLY JSON: {"words": ["...", "..."]}'
    try:
        wa = [w.lower() for w in V.ask(judge, q, [a], think=False).get("words", []) if isinstance(w, str)]
        wb = [w.lower() for w in V.ask(judge, q, [b], think=False).get("words", []) if isinstance(w, str)]
    except Exception as e:
        log(f"[texture] could not read the words: {e}")
        return False
    if not wa:
        return True
    keep = sum(1 for w in wa if w in wb) / len(wa)
    extra = sum(1 for w in wb if w not in wa) / max(len(wb), 1)
    log(f"[texture] words kept {keep:.0%}, new words {extra:.0%}")
    return keep >= 0.85 and extra <= 0.15


def continue_bands(lab, gaps):
    """Fill what no photo shows the way a texture artist would: each row of the label (one band along the length -
    the copper end, the black body, a stripe) continues its own real color across the gap, blending from the real
    pixels on each side. Plain math: nothing can be invented, no words."""
    out = lab.copy()
    H, W, _ = lab.shape
    for y in range(H):
        g = gaps[y]
        if not g.any():
            continue
        real = np.where(~g)[0]
        if len(real) == 0:
            continue
        # the row's own color from its real pixels, robust to print and glare
        base = np.median(lab[y, real], 0)
        idx = np.arange(W)
        # nearest real pixel on each side (wrapping around the label), blended toward the row color in the middle
        left = np.searchsorted(real, idx) - 1
        right = left + 1
        lp = real[left % len(real)]
        rp = real[right % len(real)]
        dl = (idx - lp) % W
        dr = (rp - idx) % W
        t = (dl / np.maximum(dl + dr, 1))[:, None]
        edge = (1 - t) * lab[y, lp] + t * lab[y, rp]
        far = np.minimum(dl, dr)[:, None]
        mix = np.clip(far / 40.0, 0, 1)                                    # near the real edge: its color; farther: the band
        fillrow = (1 - mix) * edge + mix * base
        out[y, g] = fillrow[g]
    from scipy.ndimage import gaussian_filter
    soft = np.stack([gaussian_filter(out[..., c], sigma=2) for c in range(3)], -1)
    out[gaps] = soft[gaps]                                                  # no hard streaks
    return out


def fill(product, src_png, mask_png, out, seed=7):
    """Qwen-Image-Edit-2511 in the drawing room, allowed to change only the masked part (ComfyUI's own
    SetLatentNoiseMask): the rest of the picture is kept exactly."""
    import turnaround as T
    fast = os.path.exists(os.path.join(T.LORA_DIR, T.EDIT_LORA))
    w, h = Image.open(src_png).size
    img = T._upload(open(src_png, "rb").read(), f"crushed_fill_{os.getpid()}.png")
    msk = T._upload(open(mask_png, "rb").read(), f"crushed_fillmask_{os.getpid()}.png")
    text = FILL + product
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": T.EDIT_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["11", 0] if fast else ["1", 0], "shift": 3.1}},
        "12": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "20": {"class_type": "LoadImage", "inputs": {"image": img}},
        "21": {"class_type": "LoadImage", "inputs": {"image": msk}},
        "22": {"class_type": "ImageToMask", "inputs": {"image": ["21", 0], "channel": "red"}},
        "23": {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["3", 0]}},
        "24": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["23", 0], "mask": ["22", 0]}},
        "5": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "prompt": text, "vae": ["3", 0], "image1": ["20", 0]}},
        "6": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "prompt": "", "vae": ["3", 0], "image1": ["20", 0]}},
        "15": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["5", 0], "reference_latents_method": "index_timestep_zero"}},
        "16": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["12", 0], "positive": ["15", 0], "negative": ["16", 0],
                                                    "latent_image": ["24", 0], "seed": seed, "steps": 8 if fast else 40,
                                                    "cfg": 1.0 if fast else 3.0, "sampler_name": "euler",
                                                    "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "crushed_fill"}},
    }
    if fast:
        wf["11"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": T.EDIT_LORA, "strength_model": 1.0}}
    return T._run(wf, out, 1800)


# ------------------------------------------------------------------ boxes and flat things: one face at a time

FACE = ("Picture 1 is one side of a real product's box or package, already straightened flat from a photograph (it "
        "may be creased, shiny, faded or blurry). Pictures 2 and 3, when given, are more photographs of the same "
        "product. Draw THIS SIDE as one perfectly flat, clean, print-ready panel, like the original artwork file sent "
        "to the printer: it fills the whole image edge to edge, straight-on, no background, no shadows, no glare, no "
        "creases, no perspective, no wear. Keep every word, number, logo, picture and color exactly as printed, in the "
        "same places and sizes, spelled exactly the same, crisp and sharp. The product: ")

FACE_NEW = ("Picture 1 is the clean front panel of a real product's box or package. Draw its {side} panel - the {side} "
            "side of the very same box - as one perfectly flat, clean panel that fills the whole image edge to "
            "edge, straight-on, no background, no shadows. Use the same background colors, color bands, patterns "
            "and graphic style as the front. NO words, letters, numbers, logos or barcodes at all: only color and "
            "graphic design. The product: ")


def face(product, side, w_mm, h_mm, out_dir, photo=None, refs=(), front=None, judge=None, log=print, tries=2):
    """One side of a box as a flat print-ready panel at exactly w_mm x h_mm. From its own photo when there is
    one (straightened, then redrawn clean), else drawn by the AI from the clean front."""
    import panels
    import turnaround as T
    import vet as V
    os.makedirs(out_dir, exist_ok=True)
    done = os.path.join(out_dir, f"{side}.png")
    if os.path.exists(done):                   # finished before a restart: kept, never drawn again (a Redo starts clean)
        log(f"[texture] {side}: already finished - kept")
        return done
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
    if imgs:                                   # this side was photographed: its REAL pixels, straightened, sharpened
        out = os.path.join(out_dir, f"{side}.png")
        Image.open(imgs[0]).convert("RGB").save(out)
        T.upscale(out, force=True)
        log(f"[texture] {side}: real photo, straightened to {w_mm:.0f} x {h_mm:.0f} mm")
        return out
    prefix = FACE_NEW.format(side=side)
    if not front:
        return None
    imgs = [front]
    judge = judge or V.model()
    best, best_score = None, -1
    for t in range(tries):
        png = os.path.join(out_dir, f"{side}_try{t + 1}.png")
        log(f"[texture] {side}: Qwen-Image-Edit draws it flat, {w}x{h} ({w_mm:.0f} x {h_mm:.0f} mm), try {t + 1}")
        T.draw_from_photos(product, imgs, png, width=w, height=h, prefix=prefix, seed=2000 + t)
        try:
            v = V.ask(judge, JUDGE.format(product=product).replace("flat printed label", f"flat printed {side} panel"),
                      [png, (photo or {}).get("file") or imgs[0]])
        except Exception as e:
            v = {"flat_label": False, "problems": f"could not judge: {e}"}
        score = (v.get("same_design", 0) + (3 if v.get("crisp") else 0)) if v.get("flat_label") else -1
        log(f"[texture] {side} try {t + 1}: {json.dumps(v)[:160]}")
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
