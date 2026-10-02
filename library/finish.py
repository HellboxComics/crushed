"""FINISH: the surface detail that makes a 3D object read as a real thing instead of clean CG - the same pass for
every asset, picked by what the surface is made of (the competition's models all have it).

  wrap     a printed plastic sleeve or film (battery label, bottle label): glossy clear coat over the ink, with
           faint smudges and fingerprints in the gloss, a fine orange-peel ripple, and the overlap seam
           where the sleeve's two ends meet (at the back, u = 0/1)
  spun     stamped / spun metal (battery ends, can lids, bottle caps): fine circular machining lines and a
           little unevenness in the shine
  card     printed card or paper (boxes, cards): paper grain in the bump, satin varnish, scuffed edges
  plastic  molded plastic: very fine texture, slightly uneven shine

Each one writes real texture maps (so it carries into .glb / .fbx / .usdc for any game engine):
  <name>_normal.png  (tangent-space normal map)       <name>_rough.png  (roughness in G, glTF layout)
and, for wrap, <name>_coat.png (clear-coat roughness in G).

    import finish
    maps = finish.make("wrap", out_dir, "label", w=2048, h=2048)
"""
import os

import numpy as np
from PIL import Image

RNG = np.random.default_rng(7)


def _blur(a, s):
    """Gaussian blur by FFT (wraps around: maps tile with no seam)."""
    if s <= 0:
        return a
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * s) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def _noise(h, w, s, seed=None):
    r = (np.random.default_rng(seed) if seed is not None else RNG).standard_normal((h, w))
    n = _blur(r, s)
    return (n - n.mean()) / (n.std() + 1e-9)


def _normal(height, strength):
    """Height field -> tangent-space normal map (OpenGL / glTF convention: +Y up)."""
    gy, gx = np.gradient(height)
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(height)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))


def _g(v):
    """A single-channel value 0..1 -> RGB image with it in G (the glTF roughness slot)."""
    v = np.clip(v, 0, 1)
    z = np.zeros_like(v)
    return Image.fromarray((np.stack([z, v, z], -1) * 255).astype(np.uint8))


def wrap(w, h, base_rough=0.42, coat=0.06, seam=True):
    # gloss: mostly crisp, with soft smudges (low, blotchy) and a few fingerprint-sized patches
    smudge = np.clip(_noise(h, w, w / 40) * 0.6 + _noise(h, w, w / 120) * 0.4 - 0.55, 0, None)
    prints = np.clip(_noise(h, w, w / 220) - 1.6, 0, None)
    coat_r = coat + 0.05 * smudge + 0.07 * prints + 0.008 * _noise(h, w, 1.5)     # faint: shows only in a highlight
    # bump: orange peel + the overlap seam (a soft step and a tiny ridge at the back)
    # (strengths are in surface slope: real shrink film is almost mirror-flat - the peel only shows in a highlight)
    height = 0.06 * _noise(h, w, 3) + 0.12 * _noise(h, w, 14)
    if seam:
        u = np.arange(w)[None, :] / w
        d = np.minimum(u, 1 - u) * w
        height = height + 1.2 * np.exp(-(d / 2.5) ** 2) + 0.6 * (u < 0.5) * np.exp(-(d / 8.0) ** 2)
    rough = base_rough + 0.012 * _noise(h, w, w / 25)     # the ink under the sleeve: nearly even
    return {"normal": _normal(height, 0.15), "rough": _g(rough), "coat": _g(coat_r)}


def spun(w, h, base_rough=0.3):
    """Planar map of a round end (center = middle of the image): circular machining lines."""
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
    t = np.arctan2(yy - h / 2, xx - w / 2)
    lines = np.sin(r * 900 + 2 * _noise(h, w, 6)) * 0.5 + 0.5 * np.sin(r * 2300 + t * 3)
    height = 0.25 * lines + 0.04 * _noise(h, w, 3)
    rough = base_rough + 0.04 * lines + 0.02 * _noise(h, w, w / 30) + 0.03 * np.clip(_noise(h, w, w / 50) - 1.2, 0, None)
    return {"normal": _normal(height, 0.12), "rough": _g(rough)}


def card(w, h, base_rough=0.55):
    fibers = _noise(h, w, 1.2) * 0.6 + _blur(RNG.standard_normal((h, w)), 0.6) * 0.4
    height = fibers + 0.5 * _noise(h, w, 20)
    rough = base_rough + 0.03 * _noise(h, w, w / 40)
    ys, xs = np.mgrid[0:h, 0:w]
    edge = np.minimum.reduce([xs, ys, w - 1 - xs, h - 1 - ys]) / (0.02 * min(w, h))
    rough = rough + 0.2 * np.clip(1 - edge, 0, 1) * (_noise(h, w, 4) > 0.3)      # worn, scuffed edges
    return {"normal": _normal(height, 0.08), "rough": _g(rough)}


def plastic(w, h, base_rough=0.4):
    height = 0.5 * _noise(h, w, 1.5) + 0.3 * _noise(h, w, 12)
    rough = base_rough + 0.025 * _noise(h, w, w / 40)
    return {"normal": _normal(height, 0.04), "rough": _g(rough)}


KINDS = {"wrap": wrap, "spun": spun, "card": card, "plastic": plastic}


def make(kind, out_dir, name, w=2048, h=2048, **kw):
    """-> {"normal": path, "rough": path[, "coat": path]}"""
    os.makedirs(out_dir, exist_ok=True)
    maps = KINDS[kind](w, h, **kw)
    out = {}
    for k, im in maps.items():
        p = os.path.join(out_dir, f"{name}_{k}.png")
        im.save(p)
        out[k] = p
    return out
