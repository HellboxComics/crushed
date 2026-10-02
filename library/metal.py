"""Which parts of a printed label are metal ink (copper, gold): those get the real metal's color and shine.
Returns (base color image, metallic-roughness image in the glTF layout: G = roughness, B = metallic)."""
import colorsys

import numpy as np
from PIL import Image

METALS = {"copper": ((0.955, 0.637, 0.538), (8, 32)), "gold": ((1.0, 0.766, 0.336), (33, 55))}


def metal_maps(img, rough_print=0.38, rough_metal=0.3):
    a = np.asarray(img.convert("RGB")).astype(float) / 255
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in a.reshape(-1, 3)[::1]]).reshape(a.shape)
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
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
