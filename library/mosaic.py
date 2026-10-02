"""Several real photos of the same round object, each from a different side -> one complete label all the way
around. Each photo is unwrapped flat (unwrap.py) onto the same 360-degree strip; each next photo is slid around
the strip until its print lines up with what is already there (the shared print where the two photos overlap);
where photos overlap, the one that looked straight at that spot wins. Print is then lifted off its band's
lighting and the bands made flat (unwrap.clean)."""
import numpy as np
from PIL import Image

import unwrap as U


def plus_left(m):
    """True when the battery's plus button is at the left end: a short run of columns much narrower than the body
    (the button) sits beyond that end of the body."""
    cols, t, b = U._edges(m)
    h = b - t
    full = np.median(h)
    button = (h > 0.12 * full) & (h < 0.6 * full)
    n = len(cols)
    return button[: n // 6].sum() >= button[-(n // 6):].sum()


def strip(img, m, W, H, max_deg=70, flip=False):
    """One photo -> (label H x W, how straight-on each column was 0..1 or 0 = unseen)."""
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)  # = turned 180 degrees
        m = m[::-1, ::-1]
    lab, seen, phis = U.unwrap(img, m, out_w=W, max_deg=max_deg)
    lab = np.asarray(Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    lab = U.delight(lab, seen > 0, phis)
    sv = seen > 0
    lum = lab.mean(-1)
    hi = np.percentile(lum[:, sv], 98)
    lab = np.clip(lab * (0.9 / max(hi, 1e-3)), 0, 1)                    # same exposure for every photo
    w = np.where(sv, np.cos(phis) ** 2, 0)
    prof = np.median(lab.mean(-1), 0)                                   # glare: a column brighter than its
    k = 61                                                              # surroundings in most rows
    pad = np.pad(prof, k, mode="edge")
    base = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(len(prof))])
    glare = sv & (prof > 1.25 * base + 0.02)
    w = np.where(glare, w * 0.03, w)
    return lab, w


def metal_end_top(lab, w):
    """True when the metal-ink band (copper, gold) is in the top half: that end is the battery's plus end."""
    import colorsys
    v = lab[:, w > 0.3]
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in v[::8, ::8].reshape(-1, 3)]).reshape(v[::8, ::8].shape)
    met = ((hsv[..., 0] * 360 > 8) & (hsv[..., 0] * 360 < 55) & (hsv[..., 1] > 0.35) & (hsv[..., 2] > 0.25)).mean(1)
    half = len(met) // 2
    return met[:half].mean() >= met[half:].mean()


def _feat(lab):
    g = lab.mean(-1)
    gx = np.abs(np.diff(g, axis=1, append=g[:, -1:]))
    gy = np.abs(np.diff(g, axis=0, append=g[-1:, :]))
    return gx + gy


def _vwarp(lab, scale, shift):
    """Stretch/slide rows (along the object's length): photos never agree exactly on where the label starts."""
    H = lab.shape[0]
    y = (np.arange(H) - H / 2 - shift * H) / scale + H / 2
    y0 = np.clip(np.floor(y).astype(int), 0, H - 1); y1 = np.clip(y0 + 1, 0, H - 1)
    f = np.clip(y - y0, 0, 1)[:, None, None] if lab.ndim == 3 else np.clip(y - y0, 0, 1)[:, None]
    out = lab[y0] * (1 - f) + lab[y1] * f
    out[(y < 0) | (y > H - 1)] = 0
    return out


def register(base, bw, lab, w, min_overlap=0.05, small=256):
    """Best (score, column shift, row scale, row shift) placing lab onto base, from print edges where both are
    seen; score -1 when they never overlap."""
    from PIL import Image as I
    W, H = base.shape[1], base.shape[0]
    h = int(small * H / W)
    def sm(a):
        return np.asarray(I.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((small, h), I.BILINEAR)) / 255.0
    fb, fl0 = _feat(sm(base)), _feat(sm(lab))
    bws = np.interp(np.linspace(0, W - 1, small), np.arange(W), bw)
    ws = np.interp(np.linspace(0, W - 1, small), np.arange(W), w)
    best = (-1.0, None, 1.0, 0.0)
    for sc in np.arange(0.9, 1.101, 0.02):
        for sh in np.arange(-0.08, 0.081, 0.01):
            fl = _vwarp(fl0, sc, sh)
            for s in range(small):
                wl = np.roll(ws, s)
                ov = (bws > 1e-4) & (wl > 0.15)
                if ov.mean() < min_overlap:
                    continue
                a = fb[:, ov].ravel(); b = np.roll(fl, s, axis=1)[:, ov].ravel()
                a = a - a.mean(); b = b - b.mean()
                c = (a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9)
                if c > best[0]:
                    best = (c, int(round(s * W / small)), sc, sh)
    return best


def build(photos, W=2048, aspect=48.0 / 45.55, metal_top=True):
    """photos: [(PIL image, mask)], the first is the front. -> (label H x W, coverage weight per column).
    The first photo is turned so its metal band is at the top (a battery's plus end); every other photo is tried
    both ways round and kept the way its print lines up."""
    H = int(round(W * aspect))
    first = strip(*photos[0], W, H)
    if metal_top and not metal_end_top(*first):
        first = strip(*photos[0], W, H, flip=True)
    acc = first[0] * (first[1] ** 8)[None, :, None]
    wsum = first[1] ** 8
    for i, (im, m) in enumerate(photos[1:], 1):
        cur = acc / np.maximum(wsum, 1e-6)[None, :, None]
        best = None
        for fl in (False, True):
            lab, w = strip(im, m, W, H, flip=fl)
            score, s, sc, sh = register(cur, wsum, lab, w)
            if s is not None and (best is None or score > best[0]):
                best = (score, s, _vwarp(lab, sc, sh), w, fl)
        if best is None or best[0] < 0.25:
            print(f"[mosaic] photo {i}: nothing it can be lined up with ({best[0] if best else 0:.2f}), left out")
            continue
        score, s, lab, w, fl = best
        lab, w = np.roll(lab, s, axis=1), np.roll(w, s)
        ov = (wsum > 1e-4) & (w > 0.15)
        gain = np.median(cur[:, ov].reshape(-1, 3), 0) / np.maximum(np.median(lab[:, ov].reshape(-1, 3), 0), 1e-3)
        lab = np.clip(lab * gain, 0, 1)
        acc += lab * (w ** 8)[None, :, None]
        wsum += w ** 8
        print(f"[mosaic] photo {i}: lined up at {360 * s / W:.0f} degrees{' (turned round)' if fl else ''}, match {score:.2f}")
    return acc / np.maximum(wsum, 1e-6)[None, :, None], wsum


def objects(img, m, upright=True, min_frac=0.15):
    """Every separate object in one photo (three batteries side by side -> three photos), each turned to lie
    sideways with its top end at the left, as unwrap expects."""
    from scipy import ndimage
    lab, n = ndimage.label(m > 0.5)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    out = []
    for k in np.argsort(-sizes):
        if sizes[k] < min_frac * sizes.max():
            continue
        ys, xs = np.where(lab == k + 1)
        pad = 10
        box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, m.shape[1]), min(ys.max() + pad, m.shape[0]))
        im = img.crop(box)
        mm = np.where(lab[box[1]:box[3], box[0]:box[2]] == k + 1, m[box[1]:box[3], box[0]:box[2]], 0)
        if (ys.max() - ys.min()) > (xs.max() - xs.min()):          # standing up: top end goes to the left
            im = im.rotate(90, expand=True)
            mm = np.rot90(mm, 1)
        out.append((im, np.ascontiguousarray(mm)))
    return out
