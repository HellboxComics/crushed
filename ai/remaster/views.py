"""THE VIEWS -- read the six-view turnaround like a 3D artist reads a reference sheet.

load(turn_png)      the six views, each cleaned to pure white, cut tight to the object, with its outline (mask)
classify(views)     what the object really is, shape-wise:
                      lathe  round all the way around (battery, can, bottle, cup, tube, coin): built exactly from its
                             real outline, turned on a lathe
                      box    a box, maybe with rounded corners on one side (cereal box, cassette, Game Boy, card,
                             Altoids tin): built exactly as a rounded box
                      sculpt anything else (a Furby, a water gun): the AI sculptor makes the shape
                    Simple shapes come out geometrically perfect in seconds; only truly complex ones wait on the sculptor.

Pure numpy + Pillow, so it runs in the repo's .venv and inside Blender's Python alike. Axes are Blender's: Z up, the
object's front faces the camera at -Y.
"""
import os
import sys
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# view: (facing normal = the way a surface points to face this camera, screen-right axis, screen-up axis)
AXES = {
    "front": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "back": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "bottom": ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
}


def _components(mask):
    """Connected pieces of a mask, biggest first, as lists of (row, col) arrays."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    parts = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        pts = []
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        parts.append(np.array(pts))
    return sorted(parts, key=len, reverse=True)


def _fill_holes(mask):
    """White printing inside the object is still the object: anything not reachable from the border is filled."""
    h, w = mask.shape
    outside = np.zeros_like(mask, bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    return ~outside


def _shrink(im, most=360):
    from PIL import Image
    s = most / max(im.size)
    return im if s >= 1 else im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def load(turn_png):
    """{view: {"rgb": HxWx3 uint8 cut tight to the object, "mask": HxW bool}}"""
    import turnaround as T
    from PIL import Image
    out = {}
    for k, cell in T.split(turn_png).items():
        clean = np.asarray(T.to_white(cell).convert("RGB"))
        small = np.asarray(_shrink(Image.fromarray(clean)))      # the outline is found at low size: fast, same answer
        m = (small < 250).any(-1)
        parts = _components(m)
        keep = np.zeros_like(m)
        if parts:
            big = len(parts[0])
            for p in parts:
                if len(p) >= big * 0.02:                         # drop specks and leftover divider bits
                    keep[p[:, 0], p[:, 1]] = True
        keep = _fill_holes(keep)
        full = np.asarray(Image.fromarray(keep.astype(np.uint8) * 255).resize((clean.shape[1], clean.shape[0]),
                                                                               Image.NEAREST)) > 127
        if not full.any():
            out[k] = {"rgb": clean, "mask": full}
            continue
        ys, xs = np.nonzero(full)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        out[k] = {"rgb": clean[y0:y1, x0:x1].copy(), "mask": full[y0:y1, x0:x1].copy()}
    return out


# ---------------------------------------------------------------- shape tests

def _ellipse_iou(m):
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w]
    e = ((xx + 0.5 - w / 2) / (w / 2)) ** 2 + ((yy + 0.5 - h / 2) / (h / 2)) ** 2 <= 1
    return float((e & m).sum() / max(1, (e | m).sum()))


def _corner_radius(m):
    """How rounded the outline's corners are, as a fraction of its shorter side (0 = sharp box corners)."""
    h, w = m.shape
    rs = []
    for flip_y in (False, True):
        for flip_x in (False, True):
            c = m[::-1] if flip_y else m
            c = c[:, ::-1] if flip_x else c
            n = min(h, w)
            d = 0
            while d < n and not c[d, d]:
                d += 1
            rs.append(d / 0.4142 / n)                      # diagonal gap = r(sqrt2 - 1)
    return float(min(0.5, np.median(rs)))


def _roundrect_iou(m, r):
    h, w = m.shape
    rr = r * min(h, w)
    yy, xx = np.mgrid[0:h, 0:w] + 0.5
    qx = np.clip(xx, rr, w - rr)
    qy = np.clip(yy, rr, h - rr)
    e = (xx - qx) ** 2 + (yy - qy) ** 2 <= rr ** 2 + 1e-9
    return float((e & m).sum() / max(1, (e | m).sum()))


def _symmetry(m):
    return float((m & m[:, ::-1]).sum() / max(1, (m | m[:, ::-1]).sum()))


def _widths(m, along_rows=True):
    """Outline width along the object's length: per row (rows run top to bottom) or per column."""
    a = m if along_rows else m.T
    w = np.zeros(a.shape[0])
    for i, row in enumerate(a):
        nz = np.nonzero(row)[0]
        if len(nz):
            w[i] = nz.max() - nz.min() + 1
    return w


def _resample(v, n):
    return np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v)


ROUND_WORDS = ("cylinder", "cylindrical", "can ", "can,", "can.", "bottle", "battery", "batteries", "tube", "jar",
               "cup", "canister", "tumbler", "roll ", "spool", "drum", "puck", "coin", "token", "disc", "disk")
BOX_WORDS = ("box", "carton", "rectangular", "rectangle", "case", "card", "cassette", "cartridge", "brick", "book",
             "slab", "block", "flat pack", "blister")


def _words(text):
    """Round or boxy, from the words describing it (only the opening, where the shape is said)."""
    t = " " + " ".join((text or "").lower().split()[:60]) + " "
    r = sum(t.count(w) for w in ROUND_WORDS)
    b = sum(t.count(w) for w in BOX_WORDS)
    return "round" if r > b else "box" if b > r else ""


def classify(views, words=""):
    """{"kind": "lathe"|"box"|"sculpt", ...}: the shape the object really is, with what the builder needs.
    The four side views decide most of it (the drawing model draws those reliably as flat side-on photos). The top
    view is used only when it really is a straight-down view; otherwise the describing words settle round vs box."""
    sm = {k: _mask_small(v["mask"]) for k, v in views.items() if v["mask"].any()}
    rep = {"kind": "sculpt", "why": ""}
    sides = ("front", "left", "back", "right")
    if not all(k in sm for k in sides):
        rep["why"] = "a side view is missing"
        return rep
    sym = min(_symmetry(sm[k]) for k in sides)
    prof = {k: _resample(_widths(sm[k]) / max(1, _widths(sm[k]).max()), 96) for k in sides}
    agree = 1 - max(float(np.mean(np.abs(prof[a] - prof[b]))) for a in sides for b in sides)
    w = {k: float(views[k]["mask"].shape[1]) for k in sides}
    wd = (w["front"] + w["back"]) / (w["left"] + w["right"])        # width over depth, as drawn
    top = None
    for k in ("top", "bottom"):
        if k in sm:
            m = sm[k]
            aspect = m.shape[1] / m.shape[0]
            if abs(aspect / wd - 1) < 0.15 and abs(views[k]["mask"].shape[1] / ((w["front"] + w["back"]) / 2) - 1) < 0.15:
                e, r = _ellipse_iou(m), _roundrect_iou(m, _corner_radius(m))
                top = top or ("round" if e >= 0.92 and e > r else "box" if r >= 0.93 else None)
    said = _words(words)
    rep.update(sides=dict(symmetric=round(sym, 3), agree=round(agree, 3), width_over_depth=round(wd, 3)),
               top_view=top or "not a straight-down view", words=said or "-")
    if sym >= 0.93 and agree >= 0.95 and (top or said) == "round":
        p = np.mean([prof[k] for k in sides], axis=0)
        p = np.convolve(np.pad(p, 2, mode="edge"), np.ones(5) / 5, mode="valid")    # smooth the pixel steps
        return {**rep, "kind": "lathe", "profile": [round(float(x), 4) for x in p]}
    rads = {k: _corner_radius(sm[k]) for k in sides}
    fits = {k: _roundrect_iou(sm[k], rads[k]) for k in sides}
    rep["box_fit"] = round(min(fits.values()), 3)
    if min(fits.values()) >= 0.95 and (top or said or "box") == "box":
        r_front = float(np.median([rads["front"], rads["back"]]))
        return {**rep, "kind": "box", "corner_front": round(r_front if r_front > 0.04 else 0.0, 4)}
    rep["why"] = "not round all the way around and not a box"
    return rep


def _mask_small(m, most=200):
    from PIL import Image
    im = Image.fromarray(m.astype(np.uint8) * 255)
    s = most / max(im.size)
    if s < 1:
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BILINEAR)
    return np.asarray(im) > 127


if __name__ == "__main__":
    import json
    v = load(sys.argv[1])
    words = open(sys.argv[2]).read() if len(sys.argv) > 2 else ""
    print(json.dumps({k: x for k, x in classify(v, words).items() if k != "profile"}, indent=1))
