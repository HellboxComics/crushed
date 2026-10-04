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
if os.path.join(os.path.dirname(HERE), "ai", "remaster") not in sys.path:   # other tools' folders at the END
    sys.path.append(os.path.join(os.path.dirname(HERE), "ai", "remaster"))

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
    place around the label (the fullest at the front; one showing a clearly different side at the back). A photo
    that shows only part of the length (a close-up of one end) covers only that part, at the end it shows
    (mosaic.placed) - never stretched over the whole label.
    -> (label RGB float H x W in the map layout: rows along with the top/plus end up, columns around with the
        front in the middle), coverage 0..1 per pixel)."""
    import mosaic
    H = int(round(W * along_mm / around_mm))
    expect = along_mm / (around_mm / math.pi)                    # the real length in diameters
    lab = np.zeros((H, W, 3))
    cov = np.zeros((H, W))

    def unrolled(f):
        got = []
        for im, m in all_items(f):
            try:
                objs = mosaic.objects(im, m)
                o, om = max(objs, key=lambda x: x[1].sum())
                l, w, ab = mosaic.placed(o, om, W, H, expect)
                if w.max() > 0:
                    got.append((l, w))
            except Exception:
                pass
        return got
    strips = unrolled(photos[0]) if photos else []
    if not strips:
        raise RuntimeError("could not unroll the label from your photo")
    strips.sort(key=lambda lw: -lw[1].sum())
    keep = [strips[0]]
    small = lambda x: x[::16, ::16]

    def unlike(k, s):
        """How different two unrolled views look where both saw the label (0 = nothing in common)."""
        both = (small(k[1]) > 0.05) & (small(s[1]) > 0.05)
        if not both.any():
            return 0
        return np.abs(small(k[0]).mean(-1)[both] - small(s[0]).mean(-1)[both]).mean()
    other_side = 0.10       # measured 2026-10-03: the same side in two photos differs ~0.07-0.09, the opposite ~0.14
    diffs = [unlike(keep[0], s) for s in strips[1:]]
    if diffs and max(diffs) > other_side:                                   # the most different one shows another side
        l, w = strips[1 + int(np.argmax(diffs))]
        keep.append((np.roll(l, W // 2, axis=1), np.roll(w, W // 2, axis=1)))     # it goes at the back
    if len(keep) == 1 and len(photos) > 1:
        # your pick shows only one side: the other photos of this very item (the dossier's) fill the back - the one
        # that looks most unlike the front is the opposite side, the same rule as several items in one photo
        more = []
        for f in photos[1:]:
            if f.get("mask"):                                    # (a photo without its cut-out can't be unrolled)
                more += unrolled(f)
        if more:
            d = [unlike(keep[0], s) for s in more]
            if max(d) > other_side:
                l, w = more[int(np.argmax(d))]
                keep.append((np.roll(l, W // 2, axis=1), np.roll(w, W // 2, axis=1)))
    for l, w in keep:
        better = w > cov
        lab = np.where(better[..., None], l, lab)
        cov = np.maximum(cov, w)
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


LOGO = ("Picture 1 is the flat front of a product's box. Find the brand name and product name lockup (the main logo "
        "words, e.g. the maker's name and the product's name, together). Answer ONLY JSON with its box as fractions "
        "of the picture (0..1 from the left and from the top): {\"x0\": , \"y0\": , \"x1\": , \"y1\": }")


def logo_box(front_png, judge=None, log=print):
    """Where the logo is on the real front (fractions), for a sister side whose layout shows a logo there. Checked
    for sense; if the AI's answer isn't usable -> None (never a fixed crop of the front; audit 2026-10-04)."""
    try:
        import vet as V
        b = V.ask(judge or V.model(), LOGO, [front_png], think=False, side=768)   # finding a logo needs no big picture
        x0, y0, x1, y1 = (float(b[k]) for k in ("x0", "y0", "x1", "y1"))
        if max(x0, y0, x1, y1) > 1.5:                    # answered in 0..1000 instead of fractions
            x0, y0, x1, y1 = (v / 1000 for v in (x0, y0, x1, y1))
        if 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and (x1 - x0) * (y1 - y0) > 0.04:
            return (x0, y0, x1, y1)
        log(f"[texture] logo answer not usable: {b}")
    except Exception as e:
        log(f"[texture] logo not found by the AI: {e}")
    return None


_NEXT = {"front": {"left": "left", "right": "right"}, "back": {"left": "right", "right": "left"},
         "left": {"left": "back", "right": "front"}, "right": {"left": "front", "right": "back"}}


PHOTO_Q = ("Picture 1 is the flat front of a product's box. Find the main product picture on it (the food, toy or "
           "product shown, not the words). Answer ONLY JSON with its box as fractions of the picture (0..1 from the "
           "left and from the top): {\"x0\": , \"y0\": , \"x1\": , \"y1\": }")


def photo_box(front_png, judge=None, log=print):
    try:
        import vet as V
        b = V.ask(judge or V.model(), PHOTO_Q, [front_png], think=False, side=768)
        x0, y0, x1, y1 = (float(b[k]) for k in ("x0", "y0", "x1", "y1"))
        if max(x0, y0, x1, y1) > 1.5:
            x0, y0, x1, y1 = (v / 1000 for v in (x0, y0, x1, y1))
        if 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and (x1 - x0) * (y1 - y0) > 0.05:
            return (x0, y0, x1, y1)
        log(f"[texture] product picture answer not usable: {b}")
    except Exception as e:
        log(f"[texture] product picture not found by the AI: {e}")
    return None                                          # never a fixed crop of the front (audit 2026-10-04)


SHAPE_TOL = math.log(1.2)       # a side's shape in the photo must match the real side within 20%, both ways
EDGE_ON = 0.35                  # a side squeezed below 35% of its real depth is seen edge-on: never used


def _turn_box(b, turn):
    """A box (fractions) inside a picture turned `turn` degrees clockwise."""
    if not b or not turn:
        return b
    x0, y0, x1, y1 = b
    if turn == 180:
        return [1 - x1, 1 - y1, 1 - x0, 1 - y0]
    if turn == 90:
        return [1 - y1, x0, 1 - y0, x1]
    if turn == 270:
        return [y0, 1 - x1, y1, 1 - x0]
    return b


def _sharp(im):
    """How sharp a straightened side is (the spread of its fine detail)."""
    import cv2
    g = cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2GRAY)
    s = 640 / max(g.shape)
    g = cv2.resize(g, (max(8, int(g.shape[1] * s)), max(8, int(g.shape[0] * s))))
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def _chroma(c):
    return max(c) - min(c)


def _neutralize(png, paper, ref):
    """Takes a colored cast out of one photographed side (the box's white paper looking pink under a warm lamp),
    using the paper of the most neutral real side as the true paper. Only a mild cast on light paper is fixed."""
    gain = np.clip(np.array(ref, np.float32) / np.maximum(np.array(paper, np.float32), 1), 0.75, 1.35)
    gain *= np.mean(paper) / max(float(np.mean(np.array(paper) * gain)), 1)          # same brightness as before
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.float32) * gain
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(png)


def box_skin(product, W, D, H, photos, out_dir, flat=False, judge=None, log=print, era=None, dossier=None):
    """All six sides of a box (two for a flat thing) -> one atlas laid out the way shapes/box.py maps it.

    With the item's dossier (library/dossier.py) each side follows its plan:
      - this item's own photo: every photo that shows the side is a candidate and the BEST VIEW WINS (straight-on,
        big in the frame, sharp) - not simply the first photo. A side's shape must match the real side within 20%
        both ways; a side seen nearly edge-on is never used.
      - a sister box's photo (same line, same era): straightened, its item-specific parts (flavor name, nutrition
        panel, barcode...) covered with the panel's own background and this item's verified fact drawn in their place
      - rebuilt: from facts only (eraprint), in the closest sister's layout when one was seen
    Without a dossier: the photos given, best view wins, and the box's own color plus the real logo elsewhere.
    No painting AI draws any side (it can't spell). skin/sources.json records what each side came from."""
    import panels
    import turnaround as T
    os.makedirs(out_dir, exist_ok=True)
    mm = lambda x: x * 1000
    dims = {"front": (W, H), "back": (W, H)} if flat else \
        {"front": (W, H), "back": (W, H), "left": (D, H), "right": (D, H), "top": (W, D), "bottom": (W, D)}
    dos = dossier or {}
    alias = {"top": "front", "bottom": "back"} if dos.get("route") == "pcb" else {}
    plan = {alias.get(k, k): v for k, v in (dos.get("faces") or {}).items()}
    recs = {p["file"]: p for p in dos.get("photos", []) if p.get("file")}
    masks = {p["file"]: p.get("mask") for p in photos if p.get("mask")}

    # ---- 1. every side every photo shows, each a candidate with a score
    cands = {}
    for n, p in enumerate(photos):
        rec = recs.get(p["file"], {})
        if rec.get("match") not in (None, "exact") and p["file"] != dos.get("picked"):
            continue                                          # a sister box is used only through its plan (swapped)
        rfaces = [dict(f, face=alias.get(f["face"], f["face"])) for f in rec.get("faces", [])]
        edge = {f["face"] for f in rfaces if f.get("edge_on")}
        q_ai = float(rec.get("quality") or 6)
        try:
            im = Image.open(p["file"]).convert("RGB")
        except Exception as e:
            log(f"[texture] photo {n + 1} would not open: {e}")
            continue
        found = []
        if p.get("mask") and os.path.exists(p["mask"]):
            m = np.asarray(Image.open(p["mask"]).convert("L").resize(im.size)) / 255.0
            quads, how = panels.find_faces(m)
            view = (rfaces[0]["face"] if rfaces else None) or (p.get("vet") or {}).get("view") or "front"
            if view == "side":
                view = p.get("plan") if p.get("plan") in ("left", "right") else "left"
            view = view if view in dims else "front"
            if quads:
                log(f"[texture] photo {n + 1} ({os.path.basename(p['file'])}): {how}; the biggest side is the {view}")
                c0 = panels.order_quad(quads[0]).mean(0)
                found.append((view, quads[0], m))
                for q in quads[1:]:
                    dx, dy = panels.order_quad(q).mean(0) - c0
                    if abs(dy) > abs(dx):
                        side = ("top" if dy < 0 else "bottom") if view in ("front", "back") else None
                    else:
                        side = _NEXT.get(view, {}).get("right" if dx > 0 else "left")
                    if side and side in dims:
                        found.append((side, q, m))
        primary = found[0][1] if found else None
        pw0, ph0 = panels.quad_size(primary) if primary is not None else (0, 0)
        for side, q, m in found:
            if side in edge:
                log(f"[texture] {side}: photo {n + 1} sees it edge-on - not used")
                continue
            pw, ph = dims[side]
            w, h = canvas(mm(pw), mm(ph), mp=1.2e6)
            qw, qh = panels.quad_size(q)
            short = 1.0
            if q is primary:
                ok = abs(math.log((qw / max(qh, 1)) / (pw / ph))) < SHAPE_TOL
                if not ok and n == 0:
                    log(f"[texture] {side}: your pick's shape is off by more than 20% - used anyway (it is your pick)")
                    ok = True
            else:
                if side in ("top", "bottom"):                     # shares the width edge with the front/back
                    shared = abs(math.log(max(qw, 1) / max(pw0, 1)))
                    short = (qh / max(qw, 1)) / (ph / pw)
                else:                                             # shares the height edge
                    shared = abs(math.log(max(qh, 1) / max(ph0, 1)))
                    short = (qw / max(qh, 1)) / (pw / ph)
                ok = shared < SHAPE_TOL and EDGE_ON <= short <= 1.25
                if short < EDGE_ON:
                    log(f"[texture] {side}: photo {n + 1} sees it nearly edge-on ({short:.2f} of its depth) - not used")
                    continue
            if not ok:
                log(f"[texture] {side}: the shape in photo {n + 1} doesn't fit a {side} - not used")
                continue
            face_im = panels.warp_quad(im, m, q, w, h)
            if (p.get("vet") or {}).get("view") == "back" and side in ("top", "bottom"):
                face_im = face_im.rotate(180)
            cover = min(1.0, (qw * qh) / (w * h))
            cands.setdefault(side, []).append({"im": face_im, "q": q, "m": m, "n": n, "p": p, "cover": cover,
                                               "short": min(1.0, short), "ai": q_ai, "sharp": _sharp(face_im),
                                               "how": "straightened from the photo", "px": qw * qh, "wh": (w, h)})
        # a flat, straight-on side the careful look boxed (a carton laid flat) - no cut-out needed
        for f in rfaces:
            side = f["face"] if f["face"] in dims else (p.get("plan") if f["face"] == "side" else None)
            if not side or side not in dims or not f.get("box") or not f.get("straight_on") or f.get("edge_on"):
                continue
            if any(c["p"] is p for c in cands.get(side, [])):
                continue
            b = f["box"]
            crop = im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height)))
            if f.get("turn"):
                crop = crop.rotate(-f["turn"], expand=True)
            pw, ph = dims[side]
            if abs(math.log((crop.width / max(crop.height, 1)) / (pw / ph))) >= SHAPE_TOL:
                log(f"[texture] {side}: the boxed side in photo {n + 1} doesn't have the side's shape - not used")
                continue
            w, h = canvas(mm(pw), mm(ph), mp=1.2e6)
            face_im = crop.resize((w, h), Image.LANCZOS)
            cands.setdefault(side, []).append({"im": face_im, "q": None, "m": None, "n": n, "p": p,
                                               "cover": min(1.0, crop.width * crop.height / (w * h)), "short": 1.0,
                                               "ai": q_ai, "sharp": _sharp(face_im), "how": "a flat side, cut out",
                                               "px": crop.width * crop.height, "wh": (w, h)})

    # ---- 2. the best view of each side wins
    faces, src = {}, {}
    for side, cs in cands.items():
        top_sharp = max(c["sharp"] for c in cs) or 1.0
        for c in cs:
            c["score"] = (c["cover"] ** 0.5) * c["short"] * (c["sharp"] / top_sharp) ** 0.3 * (0.6 + c["ai"] / 25)
        cs.sort(key=lambda c: -c["score"])
        best = cs[0]
        w, h = best["wh"]
        if best["q"] is not None:
            panels.warp_mask(best["m"], best["q"], w, h).save(os.path.join(out_dir, f"{side}_mask.png"))
        face_im = panels.delight(best["im"])
        out = os.path.join(out_dir, f"{side}.png")
        face_im.save(out)
        if best["px"] < 0.6 * w * h:                          # the photo had fewer pixels than the panel: sharpen up
            try:
                T.upscale(out, force=True)
                Image.open(out).convert("RGB").resize((w, h), Image.LANCZOS).save(out)
            except Exception as e:
                log(f"[texture] {side}: sharpening skipped ({e})")
        p = best["p"]
        rec = recs.get(p["file"], {})
        faces[side] = out
        src[side] = {"source": "photo", "photo": p["file"], "url": rec.get("url", p.get("url", "")),
                     "page": rec.get("page", p.get("page", "")), "match": rec.get("match") or "your pick",
                     "how": best["how"], "score": round(best["score"], 3),
                     "beat": [os.path.basename(c["p"]["file"]) for c in cs[1:4]],
                     "note": f"best of {len(cs)} view(s), straightened to {mm(dims[side][0]):.0f} x "
                             f"{mm(dims[side][1]):.0f} mm, room light taken out"}
        log(f"[texture] {side}: real photo {best['n'] + 1} ({os.path.basename(p['file'])}) - the best of {len(cs)} "
            f"view(s) (score {best['score']:.2f}), straightened to {mm(dims[side][0]):.0f} x {mm(dims[side][1]):.0f} mm")
    if "front" not in faces:
        raise RuntimeError("no photo shows the front clearly enough to straighten")
    front = Image.open(faces["front"]).convert("RGB")
    box = None                                                # found only when a sister's layout places a logo
    pbox = None
    need_logo = any(e.get("source") == "template_photo" or any(x.get("kind") == "logo" for x in (e.get("layout") or []))
                    for e in plan.values())
    if need_logo:
        box = logo_box(faces["front"], judge, log)

    # ---- 3. sides from a sister box: straightened, its item-specific parts replaced by this item's facts
    import eraprint
    c = era if isinstance(era, dict) else None                # the printable facts (packaging only)
    for side, e in plan.items():
        if side in faces or side not in dims or e.get("source") != "template_photo" or not e.get("photo"):
            continue
        pw, ph = dims[side]
        w, h = canvas(mm(pw), mm(ph), mp=1.2e6)
        if pbox is None and any(x.get("kind") in ("graphic", "picture") for x in e.get("swap_boxes") or []):
            pbox = photo_box(faces["front"], judge, log) or False     # asked once; False = not found
        got = _template_face(e, side, w, h, (mm(pw), mm(ph)), c or {}, front, box, pbox, masks, log)
        if got is None:
            log(f"[texture] {side}: the sister box's photo could not be straightened - rebuilt instead")
            e["source"] = "rebuilt"
            continue
        img, swapped, blank = got
        out = os.path.join(out_dir, f"{side}.png")
        img.save(out)
        rec = recs.get(e["photo"], {})
        faces[side] = out
        src[side] = {"source": "template", "photo": e["photo"], "url": rec.get("url", ""), "page": e.get("page", ""),
                     "match": e.get("match"), "product_shown": e.get("product_shown", ""), "swapped": swapped,
                     "left_blank": blank, "note": e.get("note", "")}
        log(f"[texture] {side}: a {str(e.get('match')).replace('_', ' ')} box's photo ({os.path.basename(e['photo'])}),"
            f" swapped: {'; '.join(swapped) or 'nothing'}" + (f"; covered, nothing known to print: {', '.join(blank)}"
                                                             if blank else ""))

    # ---- one paper for the whole box: a colored cast on a photographed side is taken out
    papers = {s: panels.paper_color(Image.open(f).convert("RGB")) for s, f in faces.items()}
    exact = [s for s in papers if src[s]["source"] == "photo"]
    ref = min((papers[s] for s in exact), key=_chroma) if exact else papers["front"]
    for s, pc in papers.items():
        if len(exact) >= 2 and _chroma(ref) < 15 and 15 < _chroma(pc) < 45 and _chroma(pc) > _chroma(ref) + 12:
            _neutralize(faces[s], pc, ref)
            src[s]["note"] = src[s].get("note", "") + f"; color cast taken out (its paper {pc} -> like {ref})"
            log(f"[texture] {s}: a colored cast taken out (paper {pc}, the most neutral real side's paper is {ref})")
    front = Image.open(faces["front"]).convert("RGB")
    paper = ref

    # ---- 4. sides no photo shows: the measured paper color plus ONLY facts with receipts (audit 2026-10-04, RC3:
    #         no logo crop, no product picture, no brand panel, no invented layout - a sister box's layout when one
    #         was found places the facts; otherwise they are stacked plainly). What was drawn, from which receipt,
    #         is written in sources.json so nothing on the model is without a source.
    biggest = max(max(d) for d in dims.values())
    facts_all = (dossier or {}).get("facts") or {}
    def receipts(ks):
        out = {}
        for k in ks:
            fs = [facts_all.get(k)] + ([facts_all.get("count")] if k == "net_weight" else [])
            out[k] = [x.get("url") or x.get("file") or x.get("quote") or "" for f in fs if isinstance(f, dict)
                      for x in f.get("sources") or []]
        return out
    for side, (pw, ph) in dims.items():
        if side in faces:
            continue
        w, h = canvas(mm(pw), mm(ph), mp=1.2e6)
        out = os.path.join(out_dir, f"{side}.png")
        e = plan.get(side, {})
        used = []
        if c is not None and min(pw, ph) >= 0.12 * biggest:   # printed packaging: the facts, in real type
            if e.get("layout") and any(x.get("kind") == "picture" for x in e["layout"]) and pbox is None:
                pbox = photo_box(faces["front"], judge, log) or False
            img, used, missing = eraprint.panel_notes(side, c, front, box, pbox, w, h, paper, (mm(pw), mm(ph)),
                                                      e.get("layout"), e.get("want"))
            if used:
                img.save(out)
                src[side] = {"source": "rebuilt", "drawn": used, "no_fact_for": missing, "receipts": receipts(used),
                             "layout_from": e.get("layout_from", ""),
                             "note": "no photo of this side: the measured paper color and only facts with receipts"
                                     + (" in a sister box's layout" if e.get("layout") else ", stacked plainly")}
        if not used:
            panels.brand_panel(front, None, w, h, side).save(out)
            src[side] = {"source": "plain", "note": "no photo of this side and no fact with a receipt to print: the "
                                                    "measured paper color only, nothing invented"}
        faces[side] = out
        log(f"[texture] {side}: {src[side]['note']}" + (f" - drew {', '.join(src[side].get('drawn', []))}"
                                                        if src[side].get("drawn") else ""))
    atlas = panels.assemble(faces, W, D, H)
    out = os.path.join(out_dir, "atlas.png")
    atlas.save(out)
    json.dump(src, open(os.path.join(out_dir, "sources.json"), "w"), indent=1)
    return out, src


def _template_face(e, side, w, h, size_mm, c, front, logo_b, photo_b, masks, log):
    """A sister box's side, straightened to w x h, with each item-specific part covered by the panel's own
    background and this item's fact drawn in its place. -> (image, [swapped], [covered, nothing to draw]) or None"""
    import eraprint
    import panels
    try:
        im = Image.open(e["photo"]).convert("RGB")
    except Exception:
        return None
    fe = e.get("view") or {}
    face_im = None
    mk = masks.get(e["photo"])
    pw_mm, ph_mm = size_mm
    if mk and os.path.exists(mk) and not fe.get("box"):         # a box in the round: its side found in the cut-out
        m = np.asarray(Image.open(mk).convert("L").resize(im.size)) / 255.0
        quads, _ = panels.find_faces(m)
        for q in quads:
            qw, qh = panels.quad_size(q)
            if abs(math.log((qw / max(qh, 1)) / (pw_mm / ph_mm))) < SHAPE_TOL:
                face_im = panels.warp_quad(im, m, q, w, h)
                break
    if face_im is None and fe.get("box"):
        b = fe["box"]
        face_im = im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height)))
        if fe.get("turn"):
            face_im = face_im.rotate(-fe["turn"], expand=True)
        if abs(math.log((face_im.width / max(face_im.height, 1)) / (pw_mm / ph_mm))) >= math.log(1.25):
            return None
        face_im = face_im.resize((w, h), Image.LANCZOS)
    if face_im is None:
        return None
    face_im = panels.delight(face_im)
    a = np.asarray(face_im).copy()
    paper = panels.paper_color(face_im)
    ink = eraprint.ink_color(front, panels.paper_color(front))
    ppm = w / pw_mm
    swapped, blank = [], []
    pending = []
    for sb in e.get("swap_boxes") or []:
        import dossier as DS
        rb = DS._rel(sb.get("box"), fe.get("box")) if fe.get("box") else sb.get("box")
        rb = _turn_box(rb, fe.get("turn") or 0)
        if not rb:
            continue
        x0, y0, x1, y1 = int(rb[0] * w), int(rb[1] * h), int(np.ceil(rb[2] * w)), int(np.ceil(rb[3] * h))
        x0, y0, x1, y1 = max(0, x0 - 3), max(0, y0 - 3), min(w, x1 + 3), min(h, y1 + 3)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        r = max(8, int(0.02 * max(w, h)))
        ring = np.concatenate([a[max(0, y0 - r):y0, x0:x1].reshape(-1, 3), a[y1:y1 + r, x0:x1].reshape(-1, 3),
                               a[y0:y1, max(0, x0 - r):x0].reshape(-1, 3), a[y0:y1, x1:x1 + r].reshape(-1, 3)])
        bg = np.array(paper, np.float32)
        if len(ring):                                             # the paper around it, not the ink next to it
            lum = ring.mean(1).astype(np.float32)
            local = np.median(ring[lum >= np.percentile(lum, 75)], 0).astype(np.float32)
            gray_shade = (local.max() - local.min()) < 30 and local.mean() < bg.mean() - 20
            bg = bg if gray_shade else local                  # a shadowed bit of white paper is still white paper
        a[y0:y1, x0:x1] = bg                                      # covered with the panel's own background
        pending.append((sb, (x0, y0, x1, y1), tuple(int(v) for v in bg)))
    img = Image.fromarray(a)
    for sb, (x0, y0, x1, y1), bg in pending:
        k = {"graphic": "picture", "barcode": "upc"}.get(sb.get("kind"), sb.get("kind"))
        el = eraprint.element(k, c, x1 - x0, y1 - y0, ppm, bg, front, logo_b, photo_b, ink) \
            if k in ("upc", "nutrition", "ingredients", "maker_lines", "legal_lines", "net_weight", "name", "logo",
                     "picture") else None
        if el is None:
            blank.append(sb.get("what", k))
            continue
        img.paste(el, (x0 + (x1 - x0 - el.width) // 2, y0 + (y1 - y0 - el.height) // 2), el if el.mode == "RGBA" else None)
        swapped.append(f"{sb.get('what')} -> this item's {k.replace('_', ' ')}")
    return img, swapped, blank
