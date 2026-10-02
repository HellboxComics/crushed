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


def strip(img, m, W, H, max_deg=62, flip=False):
    """One photo -> (label H x W, how straight-on each column was 0..1 or 0 = unseen)."""
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)  # = turned 180 degrees
        m = m[::-1, ::-1]
    cols, t, b = U._edges(m)
    radius_px = np.median(b - t) / 2                                    # how close-up and sharp the photo is
    g = np.asarray(img.convert("L")).astype(float)
    sharp = np.abs(np.diff(g, axis=1))[m[:, 1:] > 0.5].mean() if (m > 0.5).any() else 1.0
    lab, seen, phis = U.unwrap(img, m, out_w=W, max_deg=max_deg)
    lab = np.asarray(Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    lab = U.delight(lab, seen > 0, phis)
    sv = seen > 0
    lum = lab.mean(-1)
    hi = np.percentile(lum[:, sv], 98)
    lab = np.clip(lab * (0.9 / max(hi, 1e-3)), 0, 1)                    # same exposure for every photo
    w = np.where(sv, np.cos(phis) ** 2, 0) * min(1.0, radius_px / 250) * min(1.0, sharp / 12)
    prof = np.median(lab.mean(-1), 0)                                   # glare: a column brighter than its
    k = 61                                                              # surroundings in most rows
    pad = np.pad(prof, k, mode="edge")
    base = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(len(prof))])
    glare = sv & (prof > 1.25 * base + 0.02)
    w = np.where(glare, w * 0.3, w)
    return lab, w


def metal_end_top(lab, w):
    """True when the metal-ink band (copper, gold) is in the top half: that end is the battery's plus end."""
    v = lab[:, w > 0.3][::8, ::8]
    mx, mn = v.max(-1), v.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = v[..., 0], v[..., 1], v[..., 2]
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    met = ((hue > 8) & (hue < 55) & (sat > 0.35) & (mx > 0.25)).mean(1)
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
    return out


def profile(lab, w):
    """Average color of each row (along the object) over the straight-on part of a strip: where the bands and
    the big print sit, which lines photos up along the length whatever side they show."""
    c = w > 0.5
    return np.median(lab[:, c], 1) if c.any() else lab.mean(1)


def align_rows(ref, p):
    """(scale, shift) that slides/stretches row profile p onto ref (bands at the same heights)."""
    H = len(ref)
    def nz(a):
        a = a - a.mean(0)
        return a / (np.linalg.norm(a) + 1e-9)
    r = nz(ref)
    best = (-2, 1.0, 0.0)
    for sc in np.arange(0.85, 1.151, 0.01):
        for sh in np.arange(-0.10, 0.101, 0.005):
            q = _vwarp(p, sc, sh)
            c = (r * nz(q)).sum()
            if c > best[0]:
                best = (c, sc, sh)
    return best[1], best[2]


def register(base, bw, lab, w, min_overlap=0.04, small=360, need_margin=0.08):
    """Best (score, column shift) placing lab onto base, from print edges where both are seen."""
    from PIL import Image as I
    W, H = base.shape[1], base.shape[0]
    h = int(small * H / W)
    def sm(a):
        return np.asarray(I.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((small, h), I.BILINEAR)) / 255.0
    fb, fl = _feat(sm(base)), _feat(sm(lab))
    bws = np.interp(np.linspace(0, W - 1, small), np.arange(W), bw)
    ws = np.interp(np.linspace(0, W - 1, small), np.arange(W), w)
    scores = np.full(small, -1.0)
    for s in range(small):
        wl = np.roll(ws, s)
        ov = (bws > 1e-3) & (wl > 0.2)
        if ov.mean() < min_overlap:
            continue
        a = fb[:, ov].ravel(); b = np.roll(fl, s, axis=1)[:, ov].ravel()
        a = a - a.mean(); b = b - b.mean()
        scores[s] = (a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9)
    k = int(np.argmax(scores))
    if scores[k] < 0:
        return (-1.0, None)
    far = np.abs((np.arange(small) - k + small // 2) % small - small // 2) > small * 30 / 360
    second = scores[far].max() if far.any() else -1.0
    margin = scores[k] - second                      # a match that fits just as well somewhere else is a guess
    return (float(scores[k]) if margin >= need_margin else -1.0, int(round(k * W / small)))


def _match_colors(lab, ref, mask):
    """Shift/scale each color channel of lab so the shared part looks like ref (photos differ in white balance
    and exposure)."""
    out = lab.copy()
    for c in range(3):
        x, y = lab[..., c][mask], ref[..., c][mask]
        sx, sy = x.std() + 1e-4, y.std() + 1e-4
        out[..., c] = (lab[..., c] - x.mean()) * np.clip(sy / sx, 0.6, 1.6) + y.mean()
    return np.clip(out, 0, 1)


def _blend(strips, W, H):
    """Each column taken from the photo that saw it most straight-on; the seams between photos hidden by
    multi-band blending (OpenCV): fine detail switches sharply, broad color changes fade over a wide zone."""
    import cv2
    ws = np.stack([w for _, w in strips])
    owner = np.argmax(ws, 0)
    seen = ws.max(0) > 1e-3
    bl = cv2.detail_MultiBandBlender(0, 5)
    bl.prepare((0, 0, W, H))
    for k, (lab, w) in enumerate(strips):
        m = ((owner == k) & seen).astype(np.uint8) * 255
        if not m.any():
            continue
        img = (np.clip(lab, 0, 1) * 255).astype(np.int16)
        bl.feed(img, np.repeat(m[None, :], H, 0), (0, 0))
    res, _ = bl.blend(None, None)
    out = np.clip(res.astype(float) / 255, 0, 1)
    out[:, ~seen] = 0
    return out, ws.max(0)


def _refine(cur, wsum, lab, w):
    """Fine 2-D nudge (a few pixels around, a little along) where the coarse match left print doubled."""
    W, H = lab.shape[1], lab.shape[0]
    ov = (wsum > 0.05) & (w > 0.05)
    if ov.sum() < 10:
        return lab, w
    fb = _feat(cur)[:, ov]
    best = (-2, 0, 1.0, 0.0)
    for du in range(-6, 7, 2):
        l2 = np.roll(lab, du, axis=1)
        for sc in (0.98, 0.99, 1.0, 1.01, 1.02):
            for sh in (-0.01, -0.005, 0, 0.005, 0.01):
                f = _feat(_vwarp(l2, sc, sh))[:, ov]
                a = fb - fb.mean(); b = f - f.mean()
                c = (a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9)
                if c > best[0]:
                    best = (c, du, sc, sh)
    _, du, sc, sh = best
    return _vwarp(np.roll(lab, du, axis=1), sc, sh), np.roll(w, du)


def build(photos, W=2048, aspect=48.0 / 45.55, metal_top=True, min_score=0.42, log=print):
    """photos: [(PIL image, mask)], the first is the front. -> (label H x W, coverage weight per column).
    The first photo is turned so its metal band is at the top (a battery's plus end); every other photo is tried
    both ways round, slid and stretched along its length to match the bands, then slid around to match the print,
    and its colors matched to what is already placed. Then every column comes from the photo that saw it most
    straight-on, with the seams blended away."""
    H = int(round(W * aspect))
    first = strip(*photos[0], W, H)
    if metal_top and not metal_end_top(*first):
        first = strip(*photos[0], W, H, flip=True)
    ref = profile(*first)
    placed_strips = [first]
    pending = []
    for i, (im, m) in enumerate(photos[1:], 1):
        for fl in (False, True):
            lab, w = strip(im, m, W, H, flip=fl)
            sc, sh = align_rows(ref, profile(lab, w))
            pending.append((i, fl, _vwarp(lab, sc, sh), w))
    placed = set()
    for stage, (need, margin, newcov) in enumerate(((min_score, 0.08, 0.0), (0.33, 0.04, 0.3))):
      while True:
          ws = np.stack([w for _, w in placed_strips])
          wsum = ws.max(0)
          cur = sum(l * w[None, :, None] for l, w in placed_strips) / np.maximum(ws.sum(0), 1e-9)[None, :, None]
          best = None
          for i, fl, lab, w in pending:
              if i in placed:
                  continue
              score, s = register(cur, wsum, lab, w, need_margin=margin)
              if s is not None and newcov > 0:      # second round: only photos that add a side not seen yet
                  fresh = ((np.roll(w, s) > 0.2) & (wsum < 0.05)).sum() / max((w > 0.2).sum(), 1)
                  if fresh < newcov:
                      continue
              if s is not None and (best is None or score > best[0]):
                  best = (score, s, i, fl, lab, w)
          if best is None or best[0] < need:
              break
          score, s, i, fl, lab, w = best
          placed.add(i)
          lab, w = np.roll(lab, s, axis=1), np.roll(w, s)
          lab, w = _refine(cur, wsum, lab, w)
          ov = (wsum > 0.2) & (w > 0.2)
          if ov.sum() > 10:
              lab = _match_colors(lab, cur, np.repeat(ov[None, :], H, 0))
          placed_strips.append((lab, w))
          log(f"[mosaic] photo {i}: placed at {360 * s / W:.0f} degrees{' (turned round)' if fl else ''}, match {score:.2f}")
    left = sorted(set(i for i, *_ in pending) - placed)
    if left:
        log(f"[mosaic] photos {left}: could not be lined up, left out")
    return _blend(placed_strips, W, H)


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
