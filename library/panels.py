"""Real photos of a box -> its flat panels (front, back, sides, top, bottom), straightened, at true proportions,
laid out the way shapes/box.py maps them. A straight-on photo of one side: the object's outline (cut-out mask) is
found, its four corners located, and the photo is warped so that side fills its panel exactly. A side no photo
shows is left plain (its neighbors' edge color) and reported, never invented."""
import numpy as np
from PIL import Image


def corners(mask):
    """Four corners of the object's outline (largest region), ordered TL, TR, BR, BL."""
    import cv2
    m = (mask > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    q = None
    for eps in (0.01, 0.02, 0.03, 0.05):
        a = cv2.approxPolyDP(c, eps * peri, True)
        if len(a) == 4:
            q = a.reshape(4, 2).astype(np.float32)
            break
    if q is None:
        q = cv2.boxPoints(cv2.minAreaRect(c)).astype(np.float32)
    s, d = q.sum(1), np.diff(q, axis=1).ravel()
    return np.array([q[np.argmin(s)], q[np.argmin(d)], q[np.argmax(s)], q[np.argmax(d)]], np.float32)


def flatten(img, mask, out_w, out_h):
    import cv2
    q = corners(mask)
    if q is None:
        return None, 0.0
    a = np.asarray(img.convert("RGB"))
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], np.float32)
    M = cv2.getPerspectiveTransform(q, dst)
    warped = cv2.warpPerspective(a, M, (out_w, out_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # how well the outline is really four straight sides: area of the quad vs the outline
    quad_area = cv2.contourArea(q.reshape(-1, 1, 2))
    fit = float(min((mask > 0.5).sum(), quad_area) / max((mask > 0.5).sum(), quad_area, 1))
    return Image.fromarray(warped), fit


def aspect_ok(q, w, h, tol=0.25):
    """Does the photographed side have the shape of the panel it is said to be (front ~ W x H, side ~ D x H)?"""
    if q is None:
        return False
    ww = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    hh = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    return abs(np.log((ww / max(hh, 1)) / (w / h))) < tol


def build(photos, W, D, H, size=4096):
    """photos: [(PIL image, mask array, view)] with view in front/back/left/right/top/bottom.
    -> (atlas image, {panel: source or None})."""
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location("boxlayout", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes", "box.py"))
    src = open(spec.origin).read()
    ns = {}
    exec(src[src.index("def layout"):src.index("if __name__")], ns)
    L = ns["layout"](W, D, H)
    dims = {"front": (W, H), "back": (W, H), "left": (D, H), "right": (D, H), "top": (W, D), "bottom": (W, D)}
    atlas = np.zeros((size, size, 3), np.uint8)
    got = {}
    best = {}
    for img, mask, view in photos:
        if view not in dims:
            continue
        q = corners(mask)
        pw, ph = dims[view]
        if not aspect_ok(q, pw, ph):
            continue
        u0, v0, u1, v1 = L[view]
        x0, x1 = int(u0 * size), int(u1 * size)
        y0, y1 = int((1 - v1) * size), int((1 - v0) * size)
        face, fit = flatten(img, mask, x1 - x0, y1 - y0)
        if face is None or fit < 0.9:
            continue
        res = min(img.size) * fit
        if view not in best or res > best[view][0]:
            best[view] = (res, face, (x0, y0, x1, y1))
    for view, (res, face, (x0, y0, x1, y1)) in best.items():
        atlas[y0:y1, x0:x1] = np.asarray(face)
        got[view] = True
    edge = []
    for view, (_, face, _) in best.items():
        a = np.asarray(face)
        edge.append(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]))
    plain = np.median(np.concatenate(edge), 0).astype(np.uint8) if edge else np.array([200, 200, 200], np.uint8)
    for view in dims:
        if view not in best:
            u0, v0, u1, v1 = L[view]
            atlas[int((1 - v1) * size):int((1 - v0) * size), int(u0 * size):int(u1 * size)] = plain
            got[view] = None
    return Image.fromarray(atlas), got


def assemble(faces, W, D, H, size=4096):
    """{side: flat panel png} -> one atlas in box.py's layout. A side with no panel (a thin edge) takes the
    median edge color of the panels it has."""
    import os
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes", "box.py")).read()
    ns = {}
    exec(src[src.index("def layout"):src.index("if __name__")], ns)
    L = ns["layout"](W, D, H)
    atlas = np.zeros((size, size, 3), np.uint8)
    edge = []
    for side, png in faces.items():
        u0, v0, u1, v1 = L[side]
        x0, x1, y0, y1 = int(u0 * size), int(u1 * size), int((1 - v1) * size), int((1 - v0) * size)
        a = np.asarray(Image.open(png).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))
        atlas[y0:y1, x0:x1] = a
        edge.append(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]))
    plain = np.median(np.concatenate(edge), 0).astype(np.uint8) if edge else np.array([200, 200, 200], np.uint8)
    for side, (u0, v0, u1, v1) in L.items():
        if side not in faces:
            atlas[int((1 - v1) * size):int((1 - v0) * size), int(u0 * size):int(u1 * size)] = plain
    return Image.fromarray(atlas)


# ------------------------------------------------------------------ box faces from ordinary photos (2026-10-02)
# A real photo of a box usually shows two or three sides at once (front + top, front + side, a corner view).
# Each side is found on its own, straightened on its own, and only real pixels are used. A side that no photo
# shows is never drawn by a painting AI (it can't spell): it gets the box's own paper color and the real logo
# cut from the real front.

def _poly(mask, k):
    import cv2
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None, 0.0
    hull = cv2.convexHull(max(cs, key=cv2.contourArea))
    area = cv2.contourArea(hull)
    peri = cv2.arcLength(hull, True)
    for eps in np.linspace(0.003, 0.08, 80):
        a = cv2.approxPolyDP(hull, eps * peri, True).reshape(-1, 2).astype(np.float32)
        if len(a) <= k:
            return (a if len(a) == k else None), area
    return None, area


def _ang(u, v):
    a = np.degrees(np.arctan2(u[1], u[0]) - np.arctan2(v[1], v[0])) % 180
    return min(a, 180 - a)


def _quad_err(q):
    """A flat side seen in a photo: its opposite edges run close to parallel (perspective tilts them a little)."""
    e = [q[(i + 1) % 4] - q[i] for i in range(4)]
    return max(_ang(e[0], e[2]), _ang(e[1], e[3]))


def _lid_quad(m, big, small):
    """The printed panel of an open or torn lid: the fold it shares with the big side, and the outline corners
    right next to the fold's ends (not the flap tips sticking up past it)."""
    shared = [p for p in small if min(np.linalg.norm(big - p, axis=1)) < 1.0]
    if len(shared) != 2:
        return None
    for k in (8, 10, 7):
        v, _ = _poly(m, k)
        if v is None:
            continue
        ia = int(np.argmin(np.linalg.norm(v - shared[0], axis=1)))
        ib = int(np.argmin(np.linalg.norm(v - shared[1], axis=1)))
        n = len(v)
        side = [i for i in range(n) if i not in (ia, ib)]
        cb = big.mean(0)
        nxt = []
        for i, j in ((ia, ib), (ib, ia)):                     # the neighbor of each fold end, away from the big side
            cand = [(i - 1) % n, (i + 1) % n]
            cand = [c for c in cand if c != j]
            far = max(cand, key=lambda c: np.linalg.norm(v[c] - cb))
            nxt.append(far)
        q = np.array([v[ia], v[nxt[0]], v[nxt[1]], v[ib]], np.float32)
        if _quad_err(q) < 45 and len(set([ia, ib] + nxt)) == 4:     # a lid seen edge-on tapers strongly
            return q
    return None


def find_faces(mask):
    """-> ([quads, biggest first], how). Each quad is one side of the box as it sits in the photo."""
    import cv2
    m = mask > 0.5
    q4, hull_area = _poly(m, 4)
    if q4 is not None and cv2.contourArea(q4) > 0.96 * hull_area:
        return [q4], "one side"
    v, _ = _poly(m, 6)
    if v is None:
        return ([q4], "one side (rough)") if q4 is not None else ([], "no box outline")
    size = np.sqrt(hull_area)
    best = None
    for i in range(3):                                        # two sides: the fold joins two opposite corners
        A = np.array([v[(i + k) % 6] for k in range(4)])
        B = np.array([v[(i + 3 + k) % 6] for k in range(4)])
        big, small = sorted([A, B], key=lambda q: -cv2.contourArea(q.astype(np.float32)))
        e_big, e_small = _quad_err(big), _quad_err(small)
        if e_small < 25:
            keep = [big, small]
        else:                                                 # an open or torn lid: its printed panel is still
            lid = _lid_quad(m, big, small)                    # there - take the panel, leave the flaps
            keep = [big, lid] if lid is not None else [big]
        err = e_big + 0.3 * min(e_small, 25)
        if best is None or err < best[0]:
            best = (e_big, keep, "two sides" if len(keep) == 2 else "one clean side (the other is open or torn)")
    for s in (0, 1):                                          # three sides: an inner corner shared by all three
        ids = [s, s + 2, s + 4]
        P = np.array([v[i] + v[(i + 2) % 6] - v[(i + 1) % 6] for i in ids]).mean(0)
        spread = max(np.linalg.norm(v[i] + v[(i + 2) % 6] - v[(i + 1) % 6] - P) for i in ids) / size
        quads = [np.array([v[i], v[(i + 1) % 6], v[(i + 2) % 6], P]) for i in ids]
        err = max(_quad_err(q) for q in quads) + 100 * spread
        if err < best[0]:
            best = (err, quads, "three sides")
    err, quads, how = best
    if err > 25:
        return ([q4] if q4 is not None else []), f"one side (rough: no clear fold, {err:.0f} deg)"
    quads.sort(key=lambda q: -cv2.contourArea(q.astype(np.float32)))
    return quads, f"{how} ({err:.0f} deg)"


def order_quad(q):
    """Corners as top-left, top-right, bottom-right, bottom-left (as they sit in the photo)."""
    q = np.asarray(q, np.float32)
    c = q.mean(0)
    q = q[np.argsort(np.arctan2(q[:, 1] - c[1], q[:, 0] - c[0]))]
    return np.roll(q, -int(np.argmin(q.sum(1))), 0)


def quad_size(q):
    q = order_quad(q)
    return ((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2,
            (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2)


def warp_quad(img, mask, q, w, h, inset=0.006):
    """One side straightened to w x h. A hair inside the outline (no background slivers); any pixel the cut-out
    says isn't the object is filled from its neighbors."""
    import cv2
    q = order_quad(q)
    c = q.mean(0)
    q = c + (q - c) * (1 - 2 * inset)
    a = np.asarray(img.convert("RGB"))
    dst = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    M = cv2.getPerspectiveTransform(q.astype(np.float32), dst)
    out = cv2.warpPerspective(a, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    mm = cv2.warpPerspective((mask > 0.5).astype(np.uint8) * 255, M, (w, h), flags=cv2.INTER_NEAREST)
    hole = (mm < 128).astype(np.uint8)
    if hole.any():
        out = cv2.inpaint(out, hole, 5, cv2.INPAINT_TELEA)
    return Image.fromarray(out)


def delight(im):
    """Takes the room's light back out of a photographed side (a window making one end bright, the other dim), so
    the 3D viewer can light it fresh. Only a smooth, wide gradient is removed - the print itself is untouched."""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    h, w = a.shape[:2]
    lum = np.log(np.clip(a.mean(-1), 1e-3, 1))
    gy, gx = 8, 8
    ys, xs, vs = [], [], []
    for i in range(gy):
        for j in range(gx):
            blk = lum[i * h // gy:(i + 1) * h // gy, j * w // gx:(j + 1) * w // gx]
            vs.append(np.percentile(blk, 90))                 # the paper (brightest) in each block, not the ink
            ys.append((i + 0.5) / gy - 0.5)
            xs.append((j + 0.5) / gx - 0.5)
    X = np.array([[1, x, y, x * x, y * y, x * y] for x, y in zip(xs, ys)])
    coef, *_ = np.linalg.lstsq(X, np.array(vs), rcond=None)
    yy, xx = np.mgrid[0:h, 0:w]
    xx, yy = xx / w - 0.5, yy / h - 0.5
    field = coef[1] * xx + coef[2] * yy + coef[3] * xx * xx + coef[4] * yy * yy + coef[5] * xx * yy
    # even the light out around the photo's own middle brightness - never brighten the whole thing (on a dark
    # circuit board with white print, lifting everything to the brightest spot washed it gray), and never by more
    # than about a third either way
    field -= np.median(field)
    field = np.clip(field, -0.3, 0.3)
    out = np.clip(a * np.exp(-field)[..., None], 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8))


def paper_color(im):
    """The box's own paper: the commonest color among the lighter half of the front (pictures and big letters are
    the darker half), so every plain side, edge and logo background is the same paper."""
    a = np.asarray(im.convert("RGB").resize((160, 160))).reshape(-1, 3).astype(int)
    lum = a.mean(1)
    a = a[lum >= np.percentile(lum, 50)]
    q = a // 12
    key = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    keys, counts = np.unique(key, return_counts=True)
    return tuple(int(v) for v in np.median(a[key == keys[np.argmax(counts)]], 0))


def brand_panel(front, logo_box, w, h, side):
    """A side no photo shows: the box's paper color with the REAL logo (cut from the real front, its own
    background knocked out). Tall sides carry it turned to read upward, like real cartons."""
    import cv2
    bg = np.array(paper_color(front), np.float32)
    panel = np.ones((h, w, 3), np.float32) * bg
    if logo_box is None:
        return Image.fromarray(panel.astype(np.uint8))
    fw, fh = front.size
    pad = 0.02                                              # a little room so no letter touches the cut
    x0, y0 = max(0, int((logo_box[0] - pad) * fw)), max(0, int((logo_box[1] - pad) * fh))
    x1, y1 = min(fw, int((logo_box[2] + pad) * fw)), min(fh, int((logo_box[3] + pad) * fh))
    logo = np.asarray(front.convert("RGB").crop((x0, y0, x1, y1))).astype(np.float32)
    if h > 1.6 * w:                                             # a tall narrow side: reads bottom-to-top
        logo = np.rot90(logo, 1)
    lh, lw = logo.shape[:2]
    fit = {"back": 0.7, "top": 0.8, "bottom": 0.8}.get(side, 0.85)
    s = min(fit * w / lw, fit * h / lh)
    nw, nh = max(1, int(lw * s)), max(1, int(lh * s))
    logo = cv2.resize(logo, (nw, nh), interpolation=cv2.INTER_CUBIC)
    local = bg
    L, Lp = logo.mean(-1), local.mean()
    sat = np.linalg.norm(logo - L[..., None], axis=-1)
    sat_p = np.linalg.norm(local - Lp)
    ink = np.maximum(0, Lp - L) + 1.5 * np.maximum(0, sat - sat_p)   # ink is darker or more colorful than paper;
    alpha = np.clip((ink - 45) / 30, 0, 1)                   # lighter or grayer paper (photo light, color cast) is paper
    n, lab, st, _ = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8))
    for k in range(1, n):                                    # a sliver of a neighboring picture or line cut by the
        x, y, ww, hh, area = st[k]                           # crop's edge is not part of the logo: left out
        Hh, Ww = alpha.shape
        sliver = (y == 0 and y + hh < 0.15 * Hh) or (y + hh >= Hh and y > 0.85 * Hh)   # bits of the next line
        corner = (x == 0 or x + ww >= Ww) and (y == 0 or y + hh >= Hh) and area < 0.01 * alpha.size  # a picture's edge
        if sliver or corner:
            alpha[lab == k] = 0
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)[..., None]
    ox, oy = (w - nw) // 2, (h - nh) // 2 if side != "back" else int(h * 0.3 - nh / 2)
    oy = max(0, oy)
    region = panel[oy:oy + nh, ox:ox + nw]
    panel[oy:oy + nh, ox:ox + nw] = region * (1 - alpha[:region.shape[0], :region.shape[1]]) + \
        logo[:region.shape[0], :region.shape[1]] * alpha[:region.shape[0], :region.shape[1]]
    return Image.fromarray(np.clip(panel, 0, 255).astype(np.uint8))


def warp_mask(mask, q, w, h, inset=0.006):
    """The object's own outline, straightened the same way as its side (white = the object)."""
    import cv2
    q = order_quad(q)
    c = q.mean(0)
    q = c + (q - c) * (1 - 2 * inset)
    dst = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    M = cv2.getPerspectiveTransform(q.astype(np.float32), dst)
    m = cv2.warpPerspective((mask > 0.5).astype(np.uint8) * 255, M, (w, h), flags=cv2.INTER_LINEAR)
    return Image.fromarray(m)
