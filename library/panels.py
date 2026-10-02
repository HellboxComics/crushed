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
