"""THE CATALOG SIZE AGAINST THE PHOTO (audit 2026-10-04, RC5: "size is never measured").

A build's size comes from the catalog (or from Cody's phone) - never guessed. Before anything is built, the outline
of the item in the picked photo is compared with that size: the side the camera sees (front/back = W x H, a side =
D x H, top/bottom = W x D) must have the same proportions, within SHAPE_TOL. A D cell is never built as an AA, a tub
never as a bottle, a 0.1 m cube never passes for anything. When they disagree the build STOPS and Cody is asked for
the size ("<item>: size W x D x H mm" on his phone) - the asset is not "used anyway".

    agree(size_m, mask_png, view, whole=True, count=1)  -> {"ok": True/False/None, ...}  (None: not measurable)
"""
import math

SHAPE_TOL = 0.20          # 20 % off in proportion = a different thing (or a wrong catalog size)

FACE_SIDES = {"front": (0, 2), "back": (0, 2), "left": (1, 2), "right": (1, 2), "top": (0, 1), "bottom": (0, 1)}
AXIS = "WDH"


def photo_ratio(mask_png):
    """The item's outline in a cut-out mask: (long/short of its box, width px, height px) of the largest piece."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    m = np.asarray(Image.open(mask_png).convert("L")) > 127
    lab, n = ndimage.label(m)
    if not n:
        return None
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == k)
    h, w = int(np.ptp(ys)) + 1, int(np.ptp(xs)) + 1
    return max(h, w) / max(min(h, w), 1), w, h


def catalog_ratios(size_m):
    """long/short of every face of the catalog box: {"front": 1.84, "top": 1.0, ...}."""
    out = {}
    for face, (a, b) in FACE_SIDES.items():
        try:
            x, y = float(size_m[a]), float(size_m[b])
        except (TypeError, ValueError, IndexError):
            continue
        if x > 0 and y > 0:
            out[face] = max(x, y) / min(x, y)
    return out


def agree(size_m, mask_png, view=None, whole=True, count=1, tol=SHAPE_TOL):
    """Does the catalog size agree with the photo's outline? ok None when the photo can't tell (the item is cut off,
    several are touching, no outline). off = how far the photo's proportion is from the nearest face that could be
    facing the camera (0.0 = the same)."""
    try:
        pr = photo_ratio(mask_png)
    except Exception as e:
        return {"ok": None, "why": f"no outline to measure ({e})"}
    if not pr:
        return {"ok": None, "why": "no outline to measure"}
    ratio, w, h = pr
    if whole is False:
        return {"ok": None, "why": "the item is cut off in the photo", "photo_ratio": round(ratio, 3)}
    if int(count or 1) > 1:
        return {"ok": None, "why": f"{count} items in the photo", "photo_ratio": round(ratio, 3)}
    cat = catalog_ratios(size_m)
    if not cat:
        return {"ok": False, "why": "no catalog size", "photo_ratio": round(ratio, 3)}
    faces = [view] if view in cat else list(cat)             # "mixed" or unknown: any face may be facing the camera
    best = min(faces, key=lambda f: abs(math.log(ratio / cat[f])))
    off = abs(math.log(ratio / cat[best]))
    ok = off <= -math.log(1 - tol)                           # within tol either way
    mm = [round(float(x) * 1000, 1) for x in size_m[:3]]
    want = {f: round(cat[f], 2) for f in faces}
    why = (f"the item in the photo is {ratio:.2f}:1 ({w}x{h} px, seen from the {view or 'unknown side'}); the catalog "
           f"size {mm[0]} x {mm[1]} x {mm[2]} mm would show {want} - " +
           ("they agree" if ok else f"{round((math.exp(off) - 1) * 100)}% apart: the catalog size or the pick is wrong"))
    return {"ok": ok, "photo_ratio": round(ratio, 3), "px": [w, h], "view": view, "catalog": want, "nearest": best,
            "off": round(off, 3), "why": why}
