"""SURFACE LOOKS: what a material's surface does to light up close, as a tiling normal map (and sheen for fur).

A plush toy's fur, a shirt's weave, a wallet's leather grain, a brushed steel plate: the color comes from the photos,
but the SURFACE is the material's own, and a flat shaded color never reads as any of them (the Furby looked like
painted blocks). Each material kind here gets a procedural normal map built from periodic noise (seamless, so it
tiles over any UV map), and the glTF carries it with the base color. Nothing here is item-specific.

    png = looks.normal_map("plush_fur", out_png)      # -> the file, or None for a smooth kind
    looks.LOOKS[kind]                                 # {"kind", "strength", "sheen", "scale"} for the material node
"""
import os

import numpy as np

LOOKS = {
    "plush_fur": {"kind": "fur", "strength": 1.0, "sheen": 0.8, "scale": 6.0},
    "fabric": {"kind": "weave", "strength": 0.6, "sheen": 0.3, "scale": 24.0},
    "nylon": {"kind": "weave", "strength": 0.4, "sheen": 0.2, "scale": 40.0},
    "felt": {"kind": "fur", "strength": 0.4, "sheen": 0.4, "scale": 10.0},
    "leather": {"kind": "grain", "strength": 0.5, "sheen": 0.0, "scale": 8.0},
    "soft_rubber": {"kind": "grain", "strength": 0.2, "sheen": 0.0, "scale": 12.0},
    "foam": {"kind": "grain", "strength": 0.6, "sheen": 0.0, "scale": 14.0},
    "corrugated_card": {"kind": "grain", "strength": 0.25, "sheen": 0.0, "scale": 10.0},
    "bare_steel": {"kind": "brushed", "strength": 0.25, "sheen": 0.0, "scale": 3.0},
    "aluminum": {"kind": "brushed", "strength": 0.2, "sheen": 0.0, "scale": 3.0},
    "wood": {"kind": "brushed", "strength": 0.35, "sheen": 0.0, "scale": 2.0},
    "food_baked": {"kind": "grain", "strength": 0.7, "sheen": 0.0, "scale": 5.0},
}


def _noise(n, seed, stretch=(1.0, 1.0), power=2.0):
    """Periodic noise (built in frequency space, so its edges wrap): stretch > 1 along an axis makes streaks."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] * stretch[0]
    g = np.fft.fftfreq(n)[None, :] * stretch[1]
    r = np.sqrt(f * f + g * g)
    r[0, 0] = 1
    spec = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / r ** power
    spec[0, 0] = 0
    h = np.real(np.fft.ifft2(spec))
    return (h - h.min()) / max(h.max() - h.min(), 1e-9)


def _height(kind, n, seed):
    if kind == "fur":                                   # fine fibers lying mostly one way, in clumps
        fibers = _noise(n, seed, stretch=(14.0, 1.0), power=1.2)      # fibers run down (along v)
        clumps = _noise(n, seed + 1, power=2.6)
        return 0.7 * fibers + 0.3 * clumps
    if kind == "weave":                                 # threads over and under, two ways
        y, x = np.mgrid[0:n, 0:n] / n
        k = 2 * np.pi * 32
        threads = 0.5 * (np.abs(np.sin(k * x)) ** 0.5 + np.abs(np.sin(k * y)) ** 0.5)   # rounded threads, a grid
        return 0.75 * threads + 0.25 * _noise(n, seed, power=1.5)
    if kind == "brushed":                               # long straight scratches one way
        return _noise(n, seed, stretch=(60.0, 1.0), power=1.0)
    return 0.6 * _noise(n, seed, power=1.8) + 0.4 * _noise(n, seed + 3, power=1.0)   # grain: pebbly


def normal_map(kind, out_png, n=1024, seed=7):
    """The material kind's tiling normal map as a PNG (OpenGL convention, as glTF wants). None for a smooth kind."""
    look = LOOKS.get(kind)
    if not look:
        return None
    from PIL import Image
    h = _height(look["kind"], n, seed)
    dx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
    dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    slope = np.sqrt(dx * dx + dy * dy)
    k = look["strength"] * 0.45 / max(float(np.percentile(slope, 90)), 1e-9)   # the steep spots tilt ~25 deg x strength
    nx, ny, nz = -dx * k, dy * k, np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([(nx / L + 1) / 2, (ny / L + 1) / 2, (nz / L + 1) / 2], -1)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    Image.fromarray((rgb * 255).astype(np.uint8), "RGB").save(out_png)
    return out_png
