"""Deterministic, vectorised 3D noise in numpy.

Blender's own mathutils.noise uses a global seed and is slow per-vertex from
Python; this is seedable and runs on whole vertex arrays at once.
"""
import numpy as np

_M = np.uint64(0xFFFFFFFFFFFFFFFF)


def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint64) * np.uint64(0x9E3779B185EBCA87)
         ^ iy.astype(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F)
         ^ iz.astype(np.uint64) * np.uint64(0x165667B19E3779F9)
         ^ np.uint64(seed * 0x27D4EB2F165667C5 & 0xFFFFFFFFFFFFFFFF))
    h ^= h >> np.uint64(29)
    h *= np.uint64(0xBF58476D1CE4E5B9)
    h ^= h >> np.uint64(32)
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF) * 2.0 - 1.0


def value3(p, seed=0):
    """Smooth value noise in [-1, 1] for an (N, 3) array of points."""
    p = np.asarray(p, dtype=np.float64)
    i = np.floor(p).astype(np.int64)
    f = p - i
    u = f * f * f * (f * (f * 6 - 15) + 10)
    x0, y0, z0 = i[:, 0], i[:, 1], i[:, 2]
    x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1
    c = {}
    for a, xa in ((0, x0), (1, x1)):
        for b, yb in ((0, y0), (1, y1)):
            for d, zd in ((0, z0), (1, z1)):
                c[a, b, d] = _hash(xa, yb, zd, seed)
    ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
    x00 = c[0, 0, 0] + (c[1, 0, 0] - c[0, 0, 0]) * ux
    x10 = c[0, 1, 0] + (c[1, 1, 0] - c[0, 1, 0]) * ux
    x01 = c[0, 0, 1] + (c[1, 0, 1] - c[0, 0, 1]) * ux
    x11 = c[0, 1, 1] + (c[1, 1, 1] - c[0, 1, 1]) * ux
    y0_ = x00 + (x10 - x00) * uy
    y1_ = x01 + (x11 - x01) * uy
    return y0_ + (y1_ - y0_) * uz


def fbm(p, freq=1.0, octaves=4, seed=0, gain=0.5, lac=2.03):
    p = np.asarray(p, dtype=np.float64) * freq
    out = np.zeros(len(p))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        out += value3(p, seed + o * 101) * amp
        norm += amp
        amp *= gain
        p = p * lac + 17.31
    return out / norm


def fbm_vec(p, freq=1.0, octaves=4, seed=0):
    return np.stack([fbm(p, freq, octaves, seed + k * 7919) for k in range(3)], axis=1)
