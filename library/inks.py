"""A stitched, still-lit label -> clean flat art: every pixel assigned to one of the real inks, each ink one exact
color. Inks are found by color (k-means in Lab, lightness counted half so light and shade of one ink stay
together), lighting variants of one ink are merged (same hue, or both colorless on the same side of mid-grey), and
edges are kept smooth by assigning at 4x with soft weights."""
import numpy as np
from PIL import Image


def _lab(rgb):
    a = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = a @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def find(lab_img, cover, k=10, seed=0):
    vis = lab_img[:, cover > 1e-4]
    L = _lab(vis.reshape(-1, 3))
    feat = L * np.array([0.5, 1, 1])
    rng = np.random.default_rng(seed)
    sub = feat[rng.choice(len(feat), min(len(feat), 150000), replace=False)]
    cen = sub[rng.choice(len(sub), k, replace=False)]
    for _ in range(30):
        lab = np.argmin(((sub[:, None] - cen[None]) ** 2).sum(-1), 1)
        cen = np.array([sub[lab == j].mean(0) if (lab == j).any() else cen[j] for j in range(k)])
    pop = np.bincount(lab, minlength=k) / len(sub)
    full = cen / np.array([0.5, 1, 1])
    group = list(range(k))
    def root(i):
        while group[i] != i:
            i = group[i]
        return i
    for i in range(k):
        for j in range(i + 1, k):
            Li, ai, bi = full[i]; Lj, aj, bj = full[j]
            ci, cj = np.hypot(ai, bi), np.hypot(aj, bj)
            if ci > 12 and cj > 12:
                dh = abs((np.degrees(np.arctan2(bi, ai)) - np.degrees(np.arctan2(bj, aj)) + 180) % 360 - 180)
                same = dh < 18 and abs(ci - cj) < 0.6 * max(ci, cj)
            elif ci <= 12 and cj <= 12:
                same = (Li > 55) == (Lj > 55)
            else:
                same = False
            if same:
                group[root(j)] = root(i)
    roots = sorted(set(root(i) for i in range(k)))
    inks = []
    for r in roots:
        mem = [i for i in range(k) if root(i) == r]
        w = pop[mem]
        if w.sum() < 0.004:
            continue
        inks.append({"members": mem, "share": float(w.sum())})
    return cen, inks


def flat(lab_img, cover, cen, inks, scale=2):
    """Assign every pixel to an ink and paint it in that ink's color (the light side of its own pixels)."""
    H, W = lab_img.shape[:2]
    big = np.asarray(Image.fromarray((lab_img * 255).astype(np.uint8)).resize((W * scale, H * scale), Image.BICUBIC)) / 255.0
    feat = _lab(big.reshape(-1, 3)) * np.array([0.5, 1, 1])
    d = np.stack([((feat - cen[j]) ** 2).sum(-1) for j in range(len(cen))], -1)
    cl = np.argmin(d, -1)
    ink_of = np.full(len(cen), -1)
    for n, ink in enumerate(inks):
        ink_of[ink["members"]] = n
    idx = ink_of[cl]
    px = big.reshape(-1, 3)
    cols = []
    for n in range(len(inks)):
        p = px[idx == n]
        lum = p.mean(-1)
        cols.append(np.median(p[lum >= np.percentile(lum, 60)], 0) if len(p) else np.zeros(3))
    cols = np.array(cols)
    out = np.where(idx[:, None] >= 0, cols[np.maximum(idx, 0)], px).reshape(H * scale, W * scale, 3)
    return out, idx.reshape(H * scale, W * scale), cols
