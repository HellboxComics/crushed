"""Cleaned flat art (a label, a box panel) -> sharp vector art -> a picture at any size.

The art is a few real ink colors. Those are found (k-means), the in-between colors that only exist along edges
(anti-aliasing, blur) are folded into the inks on either side, white is made white (the photo's color cast is
taken out using the brightest near-neutral ink), every pixel is snapped to its ink and traced into smooth shapes
(vtracer, MIT). Rendered back (resvg) at the size asked for, the edges stay sharp however close the camera gets."""
import io

import numpy as np
from PIL import Image


def inks(a, most=8, seed=0):
    px = a.reshape(-1, 3).astype(float)
    sub = px[np.random.default_rng(seed).choice(len(px), min(len(px), 200000), replace=False)]
    best = None
    for k in range(2, most + 1):
        cen = sub[np.random.default_rng(seed).choice(len(sub), k, replace=False)]
        for _ in range(25):
            lab = np.argmin(((sub[:, None] - cen[None]) ** 2).sum(-1), 1)
            cen = np.array([sub[lab == j].mean(0) if (lab == j).any() else cen[j] for j in range(k)])
        err = np.sqrt(((sub - cen[lab]) ** 2).sum(-1)).mean()
        best = (cen, np.bincount(lab, minlength=k) / len(sub))
        if err < 9:
            break
    cen, pop = best
    keep = list(range(len(cen)))
    changed = True
    while changed:                                   # an edge blend: lies between two inks and is rarer than both
        changed = False
        for c in list(keep):
            for i in keep:
                for j in keep:
                    if len({c, i, j}) < 3:
                        continue
                    A, B, C = cen[i], cen[j], cen[c]
                    t = np.clip(np.dot(C - A, B - A) / max(np.dot(B - A, B - A), 1e-6), 0, 1)
                    if t > 0.1 and t < 0.9 and np.linalg.norm(A + t * (B - A) - C) < 22 and pop[c] < min(pop[i], pop[j]):
                        keep.remove(c); changed = True
                        break
                if changed:
                    break
            if changed:
                break
    return cen[keep]


def white_balance(cen):
    """Gains that make the brightest near-neutral ink pure white (the photo's tint out of every ink)."""
    s = cen.max(1) - cen.min(1)
    neutral = [i for i in range(len(cen)) if s[i] < 0.25 * cen[i].max() and cen[i].mean() > 110]
    if not neutral:
        return np.ones(3)
    w = cen[max(neutral, key=lambda i: cen[i].mean())]
    return 245.0 / np.maximum(w, 1)


def snap(a, cen, win=151, need=0.15):
    """Each pixel takes its nearest ink, but only an ink that is really used around it: a grey edge between white
    letters and black is not allowed to become copper just because copper is the nearest color in between."""
    from scipy import ndimage
    flat = a.reshape(-1, 3).astype(float)
    d = np.empty((len(flat), len(cen)))
    for s in range(0, len(flat), 500000):
        d[s:s + 500000] = ((flat[s:s + 500000, None] - cen[None]) ** 2).sum(-1)
    d = d.reshape(*a.shape[:2], len(cen))
    first = np.argmin(d, -1)
    for _ in range(2):
        share = np.stack([ndimage.uniform_filter((first == k).astype(float), win) for k in range(len(cen))], -1)
        dd = np.where(share >= need, d, np.inf)
        dd[np.isinf(dd).all(-1)] = d[np.isinf(dd).all(-1)]
        first = np.argmin(dd, -1)
    return first


def vectorize(img, out_svg, scale=2, most=8):
    import vtracer
    a = np.asarray(img.convert("RGB"))
    cen = inks(a, most)
    idx = snap(a, cen)
    g = white_balance(cen)
    pal = np.clip(cen * g, 0, 255).astype(np.uint8)
    q = Image.fromarray(pal[idx]).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)
    tmp = out_svg[:-4] + "_ink.png"
    q.save(tmp)
    vtracer.convert_image_to_svg_py(tmp, out_svg, colormode="color", hierarchical="stacked", mode="spline",
                                    filter_speckle=6, color_precision=8, layer_difference=4, corner_threshold=60,
                                    length_threshold=4.0, splice_threshold=45, path_precision=3)
    return out_svg, pal


def render(svg_path, width):
    import resvg_py
    png = resvg_py.svg_to_bytes(svg_string=open(svg_path).read(), width=width)
    return Image.open(io.BytesIO(bytes(png))).convert("RGB")
