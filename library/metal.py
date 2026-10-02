"""Which parts of a printed label are metal ink (copper, gold): those get the real metal's color and shine.
Returns (base color image, metallic-roughness image in the glTF layout: G = roughness, B = metallic)."""
import colorsys

import numpy as np
from PIL import Image

METALS = {"copper": ((0.955, 0.637, 0.538), (8, 32)), "gold": ((1.0, 0.766, 0.336), (33, 55))}


def metal_maps(img, rough_print=0.38, rough_metal=0.3):
    a = np.asarray(img.convert("RGB")).astype(float) / 255
    mx, mn = a.max(-1), a.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    v = mx
    base = a.copy()
    metallic = np.zeros(a.shape[:2])
    for name, (col, (h0, h1)) in METALS.items():
        m = (h >= h0) & (h <= h1) & (s > 0.35) & (v > 0.25)
        base[m] = col
        metallic[m] = 1
    mr = np.zeros_like(a)
    mr[..., 1] = np.where(metallic > 0, rough_metal, rough_print)
    mr[..., 2] = metallic
    return Image.fromarray((base * 255).astype(np.uint8)), Image.fromarray((mr * 255).astype(np.uint8))
