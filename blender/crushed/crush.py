"""Damage and compaction: how a bedroom becomes a 12-inch block."""
import math

import bmesh
import numpy as np
from mathutils import Quaternion, Vector

from . import noise
from .stage import H

# where the straps bite; set by the builder before compaction
STRAPS = []          # list of x positions
STRAP_W = 0.034


def verts(me):
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_verts(me, v):
    me.vertices.foreach_set("co", np.ascontiguousarray(v, dtype=np.float64).ravel())
    me.update()


def store_rest(me, v):
    attr = me.attributes.get("rest") or me.attributes.new("rest", "FLOAT_VECTOR", "POINT")
    attr.data.foreach_set("vector", np.ascontiguousarray(v, dtype=np.float32).ravel())


def densify(me, max_len, max_iter=7, max_verts=60000):
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(max_iter):
        if len(bm.verts) > max_verts:
            break
        long = [e for e in bm.edges if e.calc_length() > max_len]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        ng = [f for f in bm.faces if len(f.verts) > 4]
        if ng:
            bmesh.ops.triangulate(bm, faces=ng)
    bm.to_mesh(me)
    bm.free()


# -- per-object damage (local space) ----------------------------------------------------

def crumple(v, rng, amount):
    size = float(np.ptp(v, axis=0).max()) + 1e-6
    seed = int(rng.integers(0, 1 << 30))
    big = noise.fbm_vec(v, 1.0 / rng.uniform(0.05, 0.1), 3, seed) * size * 0.03 * amount
    fine = noise.fbm_vec(v, 1.0 / 0.011, 2, seed + 5) * 0.0009 * amount
    return v + big + fine


def bend(v, rng, max_angle):
    ext = np.ptp(v, axis=0)
    a = int(np.argmax(ext))
    c = int(np.argmin(ext))
    theta = rng.uniform(-max_angle, max_angle)
    if abs(theta) < 0.05:
        return v
    L = ext[a] + 1e-6
    R = L / theta
    ctr = v.mean(axis=0)
    u = v[:, a] - ctr[a]
    w = v[:, c] - ctr[c]
    ang = u / R
    out = v.copy()
    out[:, a] = ctr[a] + (R - w) * np.sin(ang)
    out[:, c] = ctr[c] + R - (R - w) * np.cos(ang)
    return out


def fold(v, rng, n, max_angle):
    """Sharp creases: rotate everything past a random plane about a hinge line."""
    if len(v) == 0:
        return v
    for _ in range(n):
        ctr = v.mean(axis=0) + rng.normal(0, 1, 3) * np.ptp(v, axis=0) * 0.2
        m = rng.normal(0, 1, 3)
        m /= np.linalg.norm(m)
        axis = np.cross(m, rng.normal(0, 1, 3))
        axis /= np.linalg.norm(axis) + 1e-9
        phi = rng.uniform(-max_angle, max_angle)
        s = (v - ctr) @ m
        w = np.clip(s / 0.004, 0, 1)                     # a crease a few mm wide
        ang = phi * w
        p = v - ctr
        # Rodrigues rotation, per-vertex angle
        cos, sin = np.cos(ang)[:, None], np.sin(ang)[:, None]
        k = axis[None, :]
        p = p * cos + np.cross(k, p) * sin + k * (p @ axis)[:, None] * (1 - cos)
        v = p + ctr
    return v


def dents(v, rng, n, depth):
    if len(v) == 0:
        return v
    ctr = v.mean(axis=0)
    size = float(np.ptp(v, axis=0).max())
    for _ in range(n):
        p = v[rng.integers(0, len(v))]
        d = p - ctr
        dn = d / (np.linalg.norm(d) + 1e-9)
        r = size * rng.uniform(0.12, 0.35)
        dist = np.linalg.norm(v - p, axis=1)
        f = np.clip(1 - (dist / r) ** 2, 0, 1) ** 2
        v = v - dn[None, :] * (f * depth * rng.uniform(0.4, 1.0))[:, None]
    return v


# -- placement -------------------------------------------------------------------------

FACES = {
    "-Y": (Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))),
    "+X": (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
    "+Z": (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))),
    "+Y": (Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1))),
    "-X": (Vector((-1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))),
}


def orient(rng, hero, normal, tilt=0.45, upright=False):
    q = Vector(hero).normalized().rotation_difference(normal)
    spin = Quaternion(normal, rng.normal(0, 0.1) if upright else rng.uniform(0, 2 * math.pi))
    ax = normal.orthogonal().normalized()
    ax.rotate(Quaternion(normal, rng.uniform(0, 2 * math.pi)))
    t = Quaternion(ax, rng.normal(0, tilt))
    return t @ spin @ q


def place(v, q, normal, uv, t1, t2, poke, depth_max):
    R = np.array(q.to_matrix())
    v = (v - v.mean(axis=0)) @ R.T
    n = np.array(normal)
    d = v @ n
    ext = d.max() - d.min()
    if ext > depth_max:
        k = depth_max / ext
        v = v - np.outer((d - d.max()) * (1 - k), n)
        # what gets squashed flat also spreads out a little (roughly volume-preserving)
        spread = min(1.35, (1 / k) ** 0.25)
        ctr = v.mean(axis=0)
        lat = (v - ctr) - np.outer((v - ctr) @ n, n)
        v = v + lat * (spread - 1)
        d = v @ n
    shift = n * (H + poke - d.max()) + np.array(t1) * uv[0] + np.array(t2) * uv[1]
    return v + shift


# -- compaction ------------------------------------------------------------------------

def soft_clamp(x, lim, m):
    ax = np.abs(x)
    over = ax > lim - m
    y = ax.copy()
    y[over] = lim[over] - m + m * np.tanh((ax[over] - (lim[over] - m)) / m)
    return np.sign(x) * y


def compact(v, layer, seed, margin=0.012, strength=1.0):
    """Press everything into the cube. `layer` offsets this object's face plane so
    overlapping flattened surfaces stack instead of z-fighting."""
    face_noise = noise.fbm(v * 1.0, 1.0 / 0.05, 3, seed) * 0.004 + noise.fbm(v, 1.0 / 0.012, 2, seed + 3) * 0.0012
    out = v.copy()
    for a in range(3):
        lim = np.full(len(v), H + layer) + face_noise
        # the straps bite into the block
        if a in (1, 2):
            for sx in STRAPS:
                band = np.clip(1 - (np.abs(v[:, 0] - sx) - STRAP_W / 2) / 0.008, 0, 1)
                lim = lim - band * 0.0045
        out[:, a] = soft_clamp(v[:, a], lim, margin)
    # rounded edges and corners, like a real bale
    k = 14.0
    r = (np.abs(out) / (H + 0.004)) ** k
    s = r.sum(axis=1) ** (1 / k)
    over = s > 1
    out[over] /= s[over, None]
    # wrinkles where material got squeezed hardest
    comp = np.linalg.norm(v - out, axis=1)
    wr = noise.fbm_vec(v, 1.0 / 0.018, 2, seed + 11) * np.clip(comp, 0, 0.04)[:, None] * 0.35 * strength
    return under_straps(out + wr)


def under_straps(v):
    """The straps are the top layer, always: nothing under a strap rises above its underside."""
    out = v.copy()
    for sx in STRAPS:
        band = np.clip(1 - (np.abs(out[:, 0] - sx) - STRAP_W / 2 - 0.002) / 0.006, 0, 1)
        lim = H - 0.0045 - 0.0012 + (1 - band) * 0.05
        for a in (1, 2):
            out[:, a] = np.sign(out[:, a]) * np.minimum(np.abs(out[:, a]), lim)
    return out


def core_mesh(me_verts, seed):
    """Displace the core box inward so gaps read as deep, dense debris."""
    v = me_verts
    n = noise.fbm(v, 1.0 / 0.03, 4, seed)
    r = np.abs(v).max(axis=1, keepdims=True)
    dirn = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    return v - dirn * (0.008 + np.abs(n)[:, None] * 0.02) * (r / H)
