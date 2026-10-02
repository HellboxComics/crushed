"""THE BUILDER AND THE BAKER -- exact shapes for simple objects, one seamless painted skin for every object.

build_lathe()  a round object (battery, can, bottle, cup) turned from its real outline, to its real size
build_box()    a box with its real corners (cereal box, cassette, Game Boy, card), to its real size
bake()         paints the model from the six-view turnaround: every spot on the model takes its color from the
               views that face it, blended softly where two views meet, never from a view where that spot is hidden,
               never from the white background. One texture, no seams, nothing mirrored.

Runs inside Blender's Python (bpy + numpy). The views come from ai/remaster/views.py.
"""
import math

import numpy as np

AXES = {
    "front": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "back": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "bottom": ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
}
SIDES = ("front", "left", "back", "right")


# ------------------------------------------------------------------ shapes (vertices, quad/tri faces), meters

def build_lathe(profile, size):
    """profile: outline width down the object, top first, 0..1 of the widest point. size: real W, D, H (m).
    Oval cross-section when W and D differ (a flask), round when they match (a can)."""
    W, D, H = size
    p = np.asarray(profile, float)
    n_z, n_t, n_cap = len(p), 96, 8
    z = np.linspace(H / 2, -H / 2, n_z)
    t = np.linspace(0, 2 * math.pi, n_t, endpoint=False)
    V = []
    for i in range(n_z):
        for j in range(n_t):
            V.append((W / 2 * p[i] * math.cos(t[j]), D / 2 * p[i] * math.sin(t[j]), z[i]))
    F = []
    for i in range(n_z - 1):
        for j in range(n_t):
            a, b = i * n_t + j, i * n_t + (j + 1) % n_t
            F.append((a, a + n_t, b + n_t, b))                       # outward with this winding (checked by outward())
    for end, ring0, zc, pr in ((0, 0, H / 2, p[0]), (1, (n_z - 1) * n_t, -H / 2, p[-1])):
        prev = list(range(ring0, ring0 + n_t))
        for k in range(1, n_cap):                                    # concentric rings so the crusher can bend the cap
            s = 1 - k / n_cap
            base = len(V)
            for j in range(n_t):
                V.append((W / 2 * pr * s * math.cos(t[j]), D / 2 * pr * s * math.sin(t[j]), zc))
            cur = list(range(base, base + n_t))
            for j in range(n_t):
                q = (prev[j], prev[(j + 1) % n_t], cur[(j + 1) % n_t], cur[j])
                F.append(q if end == 0 else q[::-1])
            prev = cur
        c = len(V)
        V.append((0.0, 0.0, zc))
        for j in range(n_t):
            tri = (prev[j], prev[(j + 1) % n_t], c)
            F.append(tri if end == 0 else tri[::-1])
    return np.array(V), F


def build_box(size, corner_front=0.0):
    """A box W x D x H with gently rounded edges; corner_front rounds the corners seen from the front (a Game Boy,
    a cassette shell, a phone), as a fraction of the front's shorter side. Dense enough for the crusher to bend."""
    W, D, H = size
    half = np.array([W, D, H]) / 2
    step = max(W, D, H) / 40
    n = [int(min(48, max(4, round(s / step)))) for s in (W, D, H)]
    pts, F = [], []
    for ax in range(3):                                              # six faces of a fine grid on the cube
        u, v = [a for a in range(3) if a != ax]
        for sgn in (-1, 1):
            base = len(pts)
            nu, nv = n[u], n[v]
            for i in range(nu + 1):
                for j in range(nv + 1):
                    q = np.zeros(3)
                    q[ax] = sgn * half[ax]
                    q[u] = -half[u] + 2 * half[u] * i / nu
                    q[v] = -half[v] + 2 * half[v] * j / nv
                    pts.append(q)
            for i in range(nu):
                for j in range(nv):
                    a = base + i * (nv + 1) + j
                    quad = (a, a + nv + 1, a + nv + 2, a + 1)
                    F.append(quad if sgn > 0 else quad[::-1])
    P = np.array(pts)
    rr = corner_front * min(W, H)
    e = 0.015 * min(W, D, H)                                        # the slight softness every real edge has
    if rr > e:                                                      # rounded in the front's plane (X, Z), sharp-ish along Y
        q = P.copy()
        for a in (0, 2):
            q[:, a] = np.clip(P[:, a], -(half[a] - rr), half[a] - rr)
        d = P - q
        d[:, 1] = 0
        L = np.linalg.norm(d, axis=1)
        ok = L > 1e-12
        P[ok] = q[ok] + d[ok] / L[ok, None] * rr
        P[ok, 1] = np.clip(P[ok, 1], -half[1], half[1])
    else:
        q = np.clip(P, -(half - e), half - e)
        d = P - q
        L = np.linalg.norm(d, axis=1)
        ok = L > 1e-12
        P[ok] = q[ok] + d[ok] / L[ok, None] * e
    return P, F


# ------------------------------------------------------------------ the rasterizer (numpy, no GPU)

def raster(P2, attrs, W, H, depth=None):
    """Draw triangles P2 (T,3,2 in pixels) carrying attrs (T,3,K) into a W x H buffer. With depth (T,3), the nearest
    surface wins (a z-buffer). Returns (buffer HxWxK, covered HxW)."""
    K = attrs.shape[2]
    buf = np.zeros((H, W, K), np.float32)
    cov = np.zeros((H, W), bool)
    zb = np.full((H, W), np.inf, np.float32) if depth is not None else None
    for i in range(len(P2)):
        (x0, y0), (x1, y1), (x2, y2) = P2[i]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        xa, xb = int(max(0, math.floor(min(x0, x1, x2)))), int(min(W - 1, math.ceil(max(x0, x1, x2))))
        ya, yb = int(max(0, math.floor(min(y0, y1, y2)))), int(min(H - 1, math.ceil(max(y0, y1, y2))))
        if xa > xb or ya > yb:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        l2 = 1 - l0 - l1
        tol = -1e-4
        inside = (l0 >= tol) & (l1 >= tol) & (l2 >= tol)
        if not inside.any():
            continue
        sub = (slice(ya, yb + 1), slice(xa, xb + 1))
        if zb is not None:
            z = l0 * depth[i, 0] + l1 * depth[i, 1] + l2 * depth[i, 2]
            inside &= z < zb[sub]
            zb[sub][inside] = z[inside]
        a = attrs[i]
        val = l0[..., None] * a[0] + l1[..., None] * a[1] + l2[..., None] * a[2]
        buf[sub][inside] = val[inside]
        cov[sub] |= inside
    return (buf, cov, zb) if zb is not None else (buf, cov)


def _bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _dilate(tex, have, steps=24):
    """Spread colors outward into the empty texels around each painted island, so filtering never shows a seam."""
    tex, have = tex.copy(), have.copy()
    for _ in range(steps):
        if have.all():
            break
        acc = np.zeros_like(tex)
        cnt = np.zeros(have.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            h2 = np.roll(np.roll(have, dy, 0), dx, 1)
            t2 = np.roll(np.roll(tex, dy, 0), dx, 1)
            acc += t2 * h2[..., None]
            cnt += h2
        new = (~have) & (cnt > 0)
        tex[new] = acc[new] / cnt[new, None]
        have |= new
    return tex, have


# ------------------------------------------------------------------ the baker

class Views:
    """The six views as the baker uses them: color and outline arrays, and how each maps onto the model."""

    def __init__(self, views, swap=False, top_rot=0, bottom_rot=0, use_ends=False):
        self.v = {}
        for k, d in views.items():
            name = {"left": "right", "right": "left"}.get(k, k) if swap else k
            rgb, m = d["rgb"].astype(np.float32) / 255.0, d["mask"]
            rot = top_rot if k == "top" else bottom_rot if k == "bottom" else 0
            if rot:
                rgb, m = np.rot90(rgb, rot).copy(), np.rot90(m, rot).copy()
            if k in ("top", "bottom") and not use_ends:
                continue
            r_ = max(2, int(min(m.shape) * 0.006))            # the outline's edge pixels are half background:
            core = m.copy()                                    # only colors from safely inside it are used
            for dy in range(-r_, r_ + 1):
                for dx in range(-r_, r_ + 1):
                    if dy * dy + dx * dx <= r_ * r_:
                        core &= np.roll(np.roll(m, dy, 0), dx, 1)
            core[:r_], core[-r_:], core[:, :r_], core[:, -r_:] = False, False, False, False
            k_ = max(1, int(min(m.shape) * 0.03))              # a softened copy for comparing views
            c = np.cumsum(np.cumsum(np.pad(rgb, ((k_, k_), (k_, k_), (0, 0)), mode="edge"), 0), 1)
            c = np.pad(c, ((1, 0), (1, 0), (0, 0)))
            n2 = 2 * k_
            soft = (c[n2:, n2:] - c[:-n2, n2:] - c[n2:, :-n2] + c[:-n2, :-n2]) / (n2 * n2)
            soft = soft[:rgb.shape[0], :rgb.shape[1]]
            cols = np.where(m.any(0))[0]
            lo = np.full(m.shape[1], -1)
            hi = np.full(m.shape[1], -1)
            for c in cols:
                r = np.nonzero(m[:, c])[0]
                lo[c], hi[c] = r.min(), r.max()
            # where the outline's edge would be sampled, use the nearest safely-inside color instead
            if core.any() and (~core & m).any():
                fill = rgb.copy()
                have = core.copy()
                for _ in range(r_ + 2):
                    nb = np.zeros_like(fill)
                    cnt = np.zeros(m.shape, np.float32)
                    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                        h2 = np.roll(np.roll(have, dy, 0), dx, 1)
                        nb += np.roll(np.roll(fill, dy, 0), dx, 1) * h2[..., None]
                        cnt += h2
                    new = (~have) & (cnt > 0)
                    fill[new] = nb[new] / cnt[new, None]
                    have |= new
                rgb = np.where(have[..., None], fill, rgb)
            self.v[name] = dict(rgb=rgb, mask=m, lo=lo, hi=hi, soft=soft.astype(np.float32))


def _project(Pts, k, lo, span):
    """Model points -> (x, y) pixels in view k's tight crop, plus depth toward that camera (smaller = nearer)."""
    f, r, up = (np.array(a, float) for a in AXES[k])
    pr, pu = Pts @ r, Pts @ up
    lr, sr = lo @ np.abs(r), span @ np.abs(r)
    lu, su = lo @ np.abs(up), span @ np.abs(up)
    xr = (pr - (lr if r.sum() > 0 else -(lr + sr))) / sr
    yu = (pu - (lu if up.sum() > 0 else -(lu + su))) / su
    return xr, yu, -(Pts @ f)


_ZB = {}


def _per_view(V, F, uvP, uvN, cov, views, lo, span, power, ends_fallback=True, radial=False, glance=False):
    """For every covered texel: each view's color, weight and whether it may be used."""
    pts, nrm = uvP[cov], uvN[cov]
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    out = {}
    for k, d in views.v.items():
        h, w = d["mask"].shape
        xr, yu, dep = _project(pts, k, lo, span)
        px, py = xr * (w - 1), (1 - yu) * (h - 1)
        # the z-buffer of the model seen from this camera, at this view's own resolution
        key = (id(V), k, w, h)
        if key not in _ZB:
            vx, vy, vd = _project(V, k, lo, span)
            tri = np.stack([vx[F] * (w - 1), (1 - vy[F]) * (h - 1)], -1)
            _ZB[key] = raster(tri, np.zeros((len(F), 3, 1), np.float32), w, h, depth=vd[F])[2]
        zb = _ZB[key]
        ix, iy = np.clip(np.round(px).astype(int), 0, w - 1), np.clip(np.round(py).astype(int), 0, h - 1)
        eps = 0.02 * float(np.max(span))
        seen = dep <= np.nan_to_num(zb[iy, ix], posinf=1e9) + eps
        inmask = d["mask"][iy, ix]
        facing = np.clip(nrm @ np.array(AXES[k][0], float), 0, 1)
        if glance:                                       # anything this camera can see at all, even edge-on
            facing = np.clip(nrm @ np.array(AXES[k][0], float) + 0.15, 0, 1) * 0.1 + 1e-3
        wgt = facing ** power * seen * inmask
        col = _bilinear(d["rgb"], px, py)
        if ends_fallback and k in SIDES:                 # for the ends (caps, box tops) when no straight-down view
            if radial:                                   # a round end: rings of the color its rim and middle show
                c = lo + span / 2
                rd = np.sqrt(((pts[:, 0] - c[0]) / (span[0] / 2)) ** 2 + ((pts[:, 1] - c[1]) / (span[1] / 2)) ** 2)
                fbs = []
                for sg in (-1, 1):
                    qx = np.clip((0.5 + sg * rd / 2) * (w - 1), 0, w - 1)
                    qi = np.round(qx).astype(int)
                    okc = d["lo"][qi] >= 0
                    qy = np.where(okc, np.clip(py, d["lo"][qi] + 2, np.maximum(d["lo"][qi] + 2, d["hi"][qi] - 2)), py)
                    fbs.append(_bilinear(d["rgb"], qx, qy))
                fb = (fbs[0] + fbs[1]) / 2
            else:                                        # a box end: each side's edge color, no streaks
                top = pts[:, 2] > (lo[2] + span[2] / 2)
                rows = d["mask"].any(1).nonzero()[0]
                band = max(2, len(rows) // 25)
                tr, br = rows[:band], rows[-band:]
                ct = d["rgb"][tr][d["mask"][tr]].mean(0) if d["mask"][tr].any() else np.array([0.5, 0.5, 0.5])
                cb = d["rgb"][br][d["mask"][br]].mean(0) if d["mask"][br].any() else np.array([0.5, 0.5, 0.5])
                fb = np.where(top[:, None], ct[None], cb[None]).astype(np.float32)
        else:
            fb = None
        out[k] = (col, wgt, fb)
    return out


def _combine(per, n, sides_fallback=True):
    acc = np.zeros((n, 3), np.float32)
    ws = np.zeros(n, np.float32)
    for k, (col, wgt, _) in per.items():
        acc += col * wgt[:, None]
        ws += wgt
    have = ws > 1e-6
    res = np.zeros((n, 3), np.float32)
    res[have] = acc[have] / ws[have, None]
    if sides_fallback:
        fbs = [fb for k, (_, _, fb) in per.items() if fb is not None]
        if fbs and (~have).any():
            res[~have] = np.mean([fb[~have] for fb in fbs], axis=0)
            have = np.ones(n, bool)
    return res, have


def _fill_from_neighbors(pts, col, seen, lo, span, n=48):
    """Colors for unseen points from the nearest seen ones, through a coarse 3D grid grown outward step by step."""
    g = np.clip(((pts - lo) / span * (n - 1)).round().astype(int), 0, n - 1)
    acc = np.zeros((n, n, n, 3), np.float32)
    cnt = np.zeros((n, n, n), np.float32)
    np.add.at(acc, (g[seen, 0], g[seen, 1], g[seen, 2]), col[seen])
    np.add.at(cnt, (g[seen, 0], g[seen, 1], g[seen, 2]), 1)
    have = cnt > 0
    acc[have] /= cnt[have, None]
    for _ in range(n):
        if have.all():
            break
        nb = np.zeros_like(acc)
        c2 = np.zeros_like(cnt)
        for ax in range(3):
            for sh in (-1, 1):
                hv = np.roll(have, sh, ax)
                nb += np.roll(acc, sh, ax) * hv[..., None]
                c2 += hv
        new = (~have) & (c2 > 0)
        acc[new] = nb[new] / c2[new, None]
        have |= new
    for _ in range(2):                                  # soften the grid's blocks
        sm = acc.copy()
        for ax in range(3):
            sm += np.roll(acc, 1, ax) + np.roll(acc, -1, ax)
        acc = sm / 7
    u = ~seen
    return acc[g[u, 0], g[u, 1], g[u, 2]]


def mesh_arrays(ob):
    """Triangles, their UVs and smooth corner normals, from a Blender mesh."""
    me = ob.data
    me.calc_loop_triangles()
    V = np.array([v.co[:] for v in me.vertices], np.float64)
    T = len(me.loop_triangles)
    F = np.zeros((T, 3), int)
    L = np.zeros((T, 3), int)
    me.loop_triangles.foreach_get("vertices", F.ravel())
    me.loop_triangles.foreach_get("loops", L.ravel())
    uv = np.zeros((len(me.loops), 2))
    me.uv_layers.active.data.foreach_get("uv", uv.ravel())
    cn = np.zeros((len(me.loops), 3))
    me.corner_normals.foreach_get("vector", cn.ravel())
    return V, F, uv[L], cn[L]


def bake(ob, views_raw, res=2048, use_ends=False, radial=False, fill3d=False, min_fit=0.0, log=print):
    """Paint ob from the turnaround. Tries the few ways the drawing model may have meant 'left' and turned the
    top view, keeps the one where neighboring views agree best, and bakes one seamless texture. Returns an image
    array (res x res x 3, 0..1) laid out on ob's active UV map."""
    V, F, UV, CN = mesh_arrays(ob)
    lo, hi = V.min(0), V.max(0)
    span = np.maximum(hi - lo, 1e-9)

    def texels(r):
        tri = np.stack([UV[..., 0] * r, (1 - UV[..., 1]) * r], -1)
        attrs = np.concatenate([V[F], CN], -1).astype(np.float32)
        buf, cov = raster(tri, attrs, r, r)
        return buf[..., :3], buf[..., 3:], cov

    # 1. pick how the views fit together: the arrangement where neighboring views agree along the edges they share
    VN = np.zeros((len(ob.data.vertices), 3))
    ob.data.vertices.foreach_get("normal", VN.ravel())

    def score(vw, names):
        cols, wts = [], []
        for k in names:
            if k not in vw.v:
                continue
            d = vw.v[k]
            h, w = d["mask"].shape
            xr, yu, dep = _project(V, k, lo, span)
            px, py = xr * (w - 1), (1 - yu) * (h - 1)
            key = (id(V), k, w, h)
            if key not in _ZB:
                tri = np.stack([xr[F] * (w - 1), (1 - yu[F]) * (h - 1)], -1)
                _ZB[key] = raster(tri, np.zeros((len(F), 3, 1), np.float32), w, h, depth=dep[F])[2]
            ix, iy = np.clip(np.round(px).astype(int), 0, w - 1), np.clip(np.round(py).astype(int), 0, h - 1)
            seen = dep <= np.nan_to_num(_ZB[key][iy, ix], posinf=1e9) + 0.02 * float(span.max())
            fac = VN @ np.array(AXES[k][0], float)
            wts.append(np.where(fac > 0.2, fac, 0) * seen * d["mask"][iy, ix])
            cols.append(_bilinear(d["soft"], px, py))
        cols, wts = np.stack(cols), np.stack(wts)
        both = (wts > 0).sum(0) >= 2
        if not both.any():
            return 0.0
        mean = (cols * wts[..., None]).sum(0) / np.maximum(wts.sum(0), 1e-9)[:, None]
        var = (wts[..., None] * (cols - mean) ** 2).sum(-1).sum(0)
        return float(var[both].sum() / wts[:, both].sum())

    def fits(rot, k):                     # a top view turned sideways must still have the top's proportions
        if k not in views_raw or rot % 2 == 0:
            return True
        hh, ww = views_raw[k]["mask"].shape
        return abs(math.log((hh / ww) / (span[0] / span[1]))) < math.log(1.3)

    def pick(options, sc, default):
        """The clearly best option; when no option clearly wins (a box's faces meet at hard edges, so their colors
        can't vouch for each other), the drawing model's usual layout stands."""
        got = sorted((sc(o), o) for o in options)
        log("[bake]   fit scores " + ", ".join(f"{o}: {v:.5f}" for v, o in got))
        if len(got) > 1 and got[0][0] < 0.7 * got[1][0]:
            return got[0][1]
        return default

    s = pick((False, True), lambda sw: score(Views(views_raw, swap=sw), SIDES), False)
    t = b = 0
    if use_ends:
        t = pick([r for r in range(4) if fits(r, "top")],
                 lambda r: score(Views(views_raw, swap=s, top_rot=r, use_ends=True), SIDES + ("top",)), 0)
        b = pick([r for r in range(4) if fits(r, "bottom")],
                 lambda r: score(Views(views_raw, swap=s, bottom_rot=r, use_ends=True), SIDES + ("bottom",)), 0)
    log(f"[bake] views fit best with left/right {'swapped' if s else 'as drawn'}"
        + (f", top turned {t * 90} deg, bottom turned {b * 90} deg" if use_ends else ""))
    # 2. bake at full size
    P, N, C = texels(res)
    vw = Views(views_raw, swap=s, top_rot=t, bottom_rot=b, use_ends=use_ends)
    for k in list(vw.v):                  # a view whose outline isn't the model's from that side is not used:
        d = vw.v[k]                       # the drawing model sometimes draws a three-quarter view there instead
        h, w = d["mask"].shape
        key = (id(V), k, w, h)
        if key not in _ZB:
            xr, yu, dep = _project(V, k, lo, span)
            tri = np.stack([xr[F] * (w - 1), (1 - yu[F]) * (h - 1)], -1)
            _ZB[key] = raster(tri, np.zeros((len(F), 3, 1), np.float32), w, h, depth=dep[F])[2]
        cov = np.isfinite(_ZB[key])
        iou = float((cov & d["mask"]).sum() / max(1, (cov | d["mask"]).sum()))
        import os as _os
        if _os.environ.get("BAKE_DEBUG"):
            from PIL import Image as _I
            dbg = np.zeros((h, w, 3), np.uint8)
            dbg[..., 0] = cov * 255
            dbg[..., 1] = d["mask"] * 255
            _I.fromarray(dbg).save(_os.path.join(_os.environ["BAKE_DEBUG"], f"fit_{k}.png"))
        if iou < min_fit and k != "front":
            log(f"[bake] {k} view left out: its outline matches the model only {iou:.0%}")
            del vw.v[k]
        else:
            log(f"[bake] {k} view matches the model {iou:.0%}")
    per = _per_view(V, F, P, N, C, vw, lo, span, power=24, radial=radial)
    col, have = _combine(per, int(C.sum()))
    if not use_ends and not fill3d:                     # the ends face no drawn view: ring or edge colors
        nz = N[C][:, 2] / np.maximum(np.linalg.norm(N[C], axis=1), 1e-9)
        cap = np.abs(nz) > 0.8
        fbs = {k: fb for k, (_, _, fb) in per.items() if fb is not None}
        if fbs and cap.any():
            if radial:
                col[cap] = np.mean([fb[cap] for fb in fbs.values()], axis=0)
            else:                                       # nearer an edge, more of that side's color
                p = P[C][cap]
                c0 = lo + span / 2
                acc, ws = np.zeros((int(cap.sum()), 3), np.float32), np.zeros(int(cap.sum()), np.float32)
                for k, fb in fbs.items():
                    f = np.array(AXES[k][0], float)
                    dist = np.abs((p - c0) @ f) / np.maximum(np.abs(span @ f) / 2, 1e-9)     # 0 middle .. 1 at edge
                    wk = np.clip(dist, 0, 1) ** 4 + 1e-4
                    acc += fb[cap] * wk[:, None]
                    ws += wk
                col[cap] = acc / ws[:, None]
    if fill3d:                                          # spots no view faces squarely:
        ws = sum(w for _, w, _ in per.values())
        seen = ws > 1e-4
        if (~seen).any():                               # 1. the views that see them at a glancing angle (stretched
            per2 = _per_view(V, F, P, N, C, vw, lo, span, power=1, glance=True)   # but continuous)
            acc = np.zeros((len(col), 3), np.float32)
            w2 = np.zeros(len(col), np.float32)
            for c2, wk, _ in per2.values():
                acc += c2 * wk[:, None]
                w2 += wk
            ok = (~seen) & (w2 > 1e-6)
            col[ok] = acc[ok] / w2[ok, None]
            seen = seen | ok
        if (~seen).any() and seen.any():                # 2. the rest (tucked-away spots) from the nearest painted
            col[~seen] = _fill_from_neighbors(P[C], col, seen, lo, span, n=96)    # surface
            have = np.ones(len(col), bool)
    tex = np.ones((res, res, 3), np.float32) * 0.5
    got = np.zeros((res, res), bool)
    idx = np.nonzero(C)
    tex[idx] = col
    got[idx] = have
    tex, _ = _dilate(tex, got)
    return tex


def silhouette_turn(V, F, views, log=print):
    """Which way the sculptor's shape faces: tries it turned 0, 90, 180 and 270 degrees about its up axis and keeps
    the turn whose outline from the front and the side best matches the drawing's (an asymmetric object, a water gun
    or a phone, must have its front where the drawing's front is). Returns quarter turns (0..3)."""
    from PIL import Image
    span0 = np.ptp(V, axis=0)
    best = None
    for q in range(4):
        c, s_ = round(math.cos(q * math.pi / 2)), round(math.sin(q * math.pi / 2))
        R = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]], float)
        P = V @ R.T
        lo, span = P.min(0), np.maximum(np.ptp(P, axis=0), 1e-9)
        tot = 0.0
        for k in ("front", "left", "back", "right"):
            if k not in views:
                continue
            m = views[k]["mask"]
            sm = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((96, 96))) > 127
            xr, yu, dep = _project(P, k, lo, span)
            tri = np.stack([xr[F] * 96, (1 - yu[F]) * 96], -1)
            _, cov = raster(tri, np.zeros((len(F), 3, 1), np.float32), 96, 96)
            tot += (cov & sm).sum() / max(1, (cov | sm).sum())
        if best is None or tot > best[0]:
            best = (tot, q)
    log(f"[remaster] sculpted shape turned {best[1] * 90} deg to face like the drawing")
    return best[1]


def rectify_box(views, size, log=print):
    """The drawing model shows a box's sides slightly turned, so a side view also holds a thin slice of the front.
    Each side view is cut to the width that side really has (from the real size), placed where the box's corner
    edges are (the strongest vertical edges), so a side face carries only that side."""
    import copy
    W, D, H = size
    want = {"front": W / H, "back": W / H, "left": D / H, "right": D / H}
    out = copy.copy(views)
    for k, ratio in want.items():
        if k not in views:
            continue
        rgb, m = views[k]["rgb"], views[k]["mask"]
        h, w = m.shape
        we = int(round(h * ratio))
        if we >= w * 0.96 or we < 8:
            continue
        g = np.abs(np.diff(rgb.astype(np.float32).mean(-1), axis=1)).mean(0)      # vertical-edge strength per column
        g = np.concatenate([g, [0]])
        best = max(range(0, w - we + 1), key=lambda o: g[max(0, o - 2):o + 3].max() + g[max(0, o + we - 3):o + we + 2].max())
        out[k] = {"rgb": rgb[:, best:best + we].copy(), "mask": m[:, best:best + we].copy()}
        log(f"[bake] {k} view cut to its real width ({w} -> {we} px)")
    return out
