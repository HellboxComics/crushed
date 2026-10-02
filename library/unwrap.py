"""Real photo of a round object (battery, can, bottle) -> its flat label, straightened.

The photo shows the object lying sideways or standing, straight on. Every column across the object is a slice of
the cylinder: a point at height y on that slice sits at angle asin((center - y) / radius) around the side. So the
label is read back out exactly, pixel for pixel, for the part of the label the photo can see (about 140 degrees).
Lighting is taken out with the object's own plain band (copper, white, metal): its brightness across the curve
is the shading, divided away, so the label is the printed colors only. What no photo shows is the row's own base
color, never invented print."""
import numpy as np
from PIL import Image


def _edges(m):
    """Top and bottom edge of a horizontal object per column (sub-pixel), from its mask."""
    H, W = m.shape
    cols = np.where((m > 0.5).sum(0) > H * 0.05)[0]
    top, bot = [], []
    for x in cols:
        c = m[:, x]
        ys = np.where(c > 0.5)[0]
        top.append(ys[0]); bot.append(ys[-1])
    return cols, np.array(top, float), np.array(bot, float)


def straighten(img, m):
    """Rotate so the object's long axis is exactly horizontal (fit lines to its top and bottom edges)."""
    cols, t, b = _edges(m)
    keep = slice(len(cols) // 10, len(cols) * 9 // 10)            # the ends are rounded: fit the straight middle
    k1 = np.polyfit(cols[keep], t[keep], 1)[0]
    k2 = np.polyfit(cols[keep], b[keep], 1)[0]
    ang = np.degrees(np.arctan((k1 + k2) / 2))
    im = img.rotate(ang, resample=Image.BICUBIC, expand=False)
    mm = Image.fromarray((m * 255).astype(np.uint8)).rotate(ang, resample=Image.BILINEAR)
    return im, np.asarray(mm) / 255.0, ang


def unwrap(img, m, out_w=2048, max_deg=72, plus_end="left"):
    """-> (label RGB float array H x W in 0..1, coverage 0..1 per column). Rows: along the axis, top row = the
    plus end. Columns: around the object, the center column = the side facing the camera."""
    img, m, ang = straighten(img, m)
    a = np.asarray(img.convert("RGB")).astype(float) / 255
    cols, t, b = _edges(m)
    mid = slice(len(cols) // 10, len(cols) * 9 // 10)
    c = (np.median(t[mid]) + np.median(b[mid])) / 2                 # one straight axis: the middle is reliable
    r = (np.median(b[mid]) - np.median(t[mid])) / 2
    full = np.median(b[mid] - t[mid])
    body = cols[(b - t) > 0.9 * full]                               # the straight side, not the rounded ends
    x0, x1 = body[0], body[-1]
    L = x1 - x0
    out_h = int(round(out_w * L / (2 * np.pi * r)))                 # true proportions: length vs circumference
    phis = (np.arange(out_w) + 0.5) / out_w * 2 * np.pi - np.pi     # -pi..pi, 0 = facing the camera
    seen = np.abs(phis) <= np.radians(max_deg)
    xs = x0 + (np.arange(out_h) + 0.5) / out_h * L
    if plus_end != "left":
        xs = xs[::-1]
    ys = c - r * np.sin(phis[seen])                                 # screen-right on the upright object = up here
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    lab = np.zeros((out_h, out_w, 3))
    lab[:, seen] = _bilinear(a, X, Y)
    return lab, seen.astype(float), phis


def _bilinear(a, X, Y):
    H, W = a.shape[:2]
    X = np.clip(X, 0, W - 1.001); Y = np.clip(Y, 0, H - 1.001)
    x0 = np.floor(X).astype(int); y0 = np.floor(Y).astype(int)
    fx = (X - x0)[..., None]; fy = (Y - y0)[..., None]
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) +
            a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def delight(lab, seen, phis, plain_rows=None):
    """Divide out the shading and shine across the curve. For every row, brightness at each angle is compared with
    the same row facing the camera; the median over all reasonably bright rows is the shading (print is an outlier
    in a single row, never in most rows)."""
    v = lab[:, seen].mean(-1)
    c = np.abs(phis[seen]) < np.radians(8)
    ref = np.median(v[:, c], 1)
    ok = ref > 0.12
    ratio = np.median(v[ok] / ref[ok, None], 0)
    ratio = np.convolve(np.pad(ratio, 20, mode="edge"), np.ones(41) / 41, "same")[20:-20]
    g = np.clip(1 / np.maximum(ratio, 1e-3), 0.4, 3.0)
    out = lab.copy()
    out[:, seen] = np.clip(lab[:, seen] * g[None, :, None], 0, 1)
    return out


def fill_unseen(lab, seen, phis, feather_deg=8):
    """Columns no photo saw get each row's own base color (the bigger of its two color groups), blended in."""
    from numpy.linalg import norm
    vis = lab[:, seen]
    base = np.zeros((lab.shape[0], 3))
    for i, row in enumerate(vis):
        lum = row.mean(-1)
        thr = (np.percentile(lum, 15) + np.percentile(lum, 85)) / 2
        lo, hi = row[lum <= thr], row[lum > thr]
        base[i] = (lo if len(lo) >= len(hi) else hi).mean(0) if len(lo) and len(hi) else row.mean(0)
    base = _bands(base)
    lim = np.abs(phis[seen]).max()
    w = np.clip((lim - np.abs(phis)) / np.radians(feather_deg), 0, 1)   # 1 well inside the seen part, 0 outside
    return lab * w[None, :, None] + base[:, None, :] * (1 - w[None, :, None]), base


def plain_rows(lab, seen, phis, frac=0.15):
    """Rows that are one plain printed color across the visible face (lowest color spread)."""
    c = np.abs(phis) < np.radians(50)
    sd = lab[:, c].std(1).mean(-1)
    return sd <= np.quantile(sd, frac)


def _bands(base, most=4, tol=0.08):
    """Per-row base colors -> a few clean flat bands (copper / black ...): k-means along the rows, short runs
    merged into their neighbors, so the unseen back has no streaks."""
    best = None
    for k in range(1, most + 1):
        cen = base[np.linspace(0, len(base) - 1, k).astype(int)].copy()
        for _ in range(30):
            lab = np.argmin(((base[:, None] - cen[None]) ** 2).sum(-1), 1)
            cen = np.array([base[lab == j].mean(0) if (lab == j).any() else cen[j] for j in range(k)])
        err = np.sqrt(((base - cen[lab]) ** 2).sum(-1)).mean()
        best = (cen, lab)
        if err < tol:
            break
    cen, lab = best
    n = len(lab); minrun = max(3, n // 40)
    i = 0
    while i < n:                                                     # runs shorter than minrun take the run before
        j = i
        while j < n and lab[j] == lab[i]:
            j += 1
        if j - i < minrun and i > 0:
            lab[i:j] = lab[i - 1]
        i = j
    return cen[lab]


def clean(lab, seen, phis, soft=(0.07, 0.17), cover=None):
    """The production label: each printed band becomes one flat color (no shine, no shading, no grain), and only
    the print on it (letters, logos, lines) is kept from the photo, lifted off the band's own lighting. What no
    photo saw is the flat band color."""
    v = (cover > 1e-4) if cover is not None else (np.abs(phis) <= np.abs(phis[seen]).max())
    rowbase = np.zeros((lab.shape[0], 3))
    vis = lab[:, v]
    for i, row in enumerate(vis):
        lum = row.mean(-1)
        thr = (np.percentile(lum, 15) + np.percentile(lum, 85)) / 2
        lo, hi = row[lum <= thr], row[lum > thr]
        rowbase[i] = (lo if len(lo) >= len(hi) else hi).mean(0) if len(lo) and len(hi) else row.mean(0)
    flat = _bands(rowbase)                                           # per-row flat band color
    out = np.repeat(flat[:, None, :], lab.shape[1], 1)
    bands = np.unique(flat, axis=0)
    pv = phis[v] if cover is None else None
    for col in bands:
        rows = np.all(np.isclose(flat, col), 1)
        blk = lab[rows][:, v]                                        # this band, seen part
        bright = col.mean() > 0.22
        if bright:                                                   # a light/colored band: same hue, any shade
            ch = blk / np.maximum(blk.sum(-1, keepdims=True), 1e-3)
            near = (np.abs(ch - col / max(col.sum(), 1e-3)).sum(-1) < 0.08) & (blk.mean(-1) > 0.03)
        else:                                                        # a dark band: close in plain color
            near = np.sqrt(((blk - col) ** 2).sum(-1)) < 0.22
        w = near[..., None].astype(float)
        curve = (blk * w).sum(0) / np.maximum(w.sum(0), 1)           # band background per angle (light + shine)
        has = w.sum(0)[:, 0] > max(3, 0.10 * blk.shape[0])           # enough plain band seen at this angle
        curve[~has] = col
        curve = np.stack([np.convolve(np.pad(curve[:, j], 15, mode="edge"), np.ones(31) / 31, "same")[15:-15]
                          for j in range(3)], -1)
        if bright:                                                   # print = what differs from the band's shade
            cl = np.maximum(curve.mean(-1), 0.04)[None]                  # how lit the band is at this angle
            if cover is None:
                has &= cl[0] >= 0.55 * cl.max()                          # only well-lit angles are trusted
            dev = (blk - curve[None]) * (col.mean() / cl)[..., None]     # print, brought to the band's true light
            a_ = np.clip((np.abs(dev).max(-1) - 0.10) / 0.12, 0, 1)
            val = np.clip(col + dev, 0, 1)
        else:                                                        # dark band: oblique edges read as mush
            if cover is None:
                has &= np.abs(pv) <= np.radians(66)
            dev = blk - curve[None]
            a_ = np.clip((np.abs(dev).max(-1) - soft[0]) / (soft[1] - soft[0]), 0, 1)
            val = np.clip(col + dev, 0, 1)
        a_[:, ~has] = 0
        a_ = _whole_marks_only(a_, has)
        a_ = a_[..., None]
        out[np.ix_(np.where(rows)[0], np.where(v)[0])] = col * (1 - a_) + val * a_
    return out


def _whole_marks_only(a, has):
    """A printed mark (an icon, a word) that runs into the part of the photo too dark to read is dropped whole:
    half a recycling bin is worse than none."""
    from scipy import ndimage
    lab, n = ndimage.label(ndimage.binary_dilation(a > 0.35, iterations=2))
    edge = np.zeros_like(has)
    edge[1:] |= has[1:] & ~has[:-1]
    edge[:-1] |= has[:-1] & ~has[1:]
    cut = np.unique(lab[:, edge | ~has])
    bad = np.isin(lab, cut[cut > 0])
    a = a.copy()
    a[bad] = 0
    return a
