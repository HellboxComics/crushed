"""THE SIDES NO PHOTO SHOWS, REBUILT ONLY FROM FACTS WITH RECEIPTS (his rule, 2026-10-02: facts are never invented).

Every word on a rebuilt side comes from the item's dossier (library/dossier.py): a fact read off a real photo of that
era, or found on a real web page, each with its receipt. Nothing comes from an AI's memory: no made-up ad copy, no
promos, no phone numbers, no how-to steps. If the back of the box has no source at all, it gets a clean back made of
what IS known (the real logo cut from the real front, the product name, net weight, the maker's lines) and the gap is
written down. Every word is set in real type; nothing is painted by an AI.

  - Nutrition Facts only for food, only when the real panel was found, drawn in the format of its year
    (before mid-1994: the old "Nutrition Information" list; 1994-2005: the 1994 FDA box; 2006-2019: with trans fat;
    2020 on: the new big-calories box).
  - The UPC barcode at its real printed size (GS1: 0.33 mm per bar module at 100%, 37.29 mm wide with its quiet
    zones, 22.85 mm bars; 80% to 200% allowed), full bar height, the check digit worked out from the 11 digits.
    A code that doesn't add up is never drawn, never padded or shifted.

    c = eraprint.from_dossier(dossier)                    # only the facts that can be printed
    img = eraprint.panel(side, c, front_img, logo_box, photo_box, w, h, paper, size_mm=(w_mm, h_mm))
"""
import re

import numpy as np
from PIL import Image, ImageDraw

import labelart

USABLE = ("verified", "single_source")          # a fact is printed only with at least one real receipt


# ------------------------------------------------------------------ facts -> what may be printed
def _usable(f):
    return isinstance(f, dict) and f.get("status") in USABLE and f.get("value") not in (None, "", [], {})


def from_dossier(dos):
    """The printable facts of one item: only facts with a receipt (verified or one real source). Nutrition and
    ingredients only for food, and only when the source is from the item's own era."""
    dos = dos or {}
    idn = dos.get("identity") or {}
    facts = dos.get("facts") or {}
    c = {"food": bool(idn.get("food")), "name": " ".join(x for x in (idn.get("line"), idn.get("variant")) if x),
         "variant": idn.get("variant") or "", "line": idn.get("line") or "", "brand": idn.get("brand") or "",
         "year": idn.get("year"), "left_out": []}
    for k in ("upc", "net_weight", "count", "maker_lines", "legal_lines", "nutrition", "ingredients"):
        f = facts.get(k)
        if k in ("nutrition", "ingredients") and not c["food"]:
            continue
        if _usable(f) and (f.get("checks") or {}).get("era_ok", True) is not False:
            c[k] = f["value"]
        elif f is not None:
            c["left_out"].append(k)
    n = facts.get("nutrition")
    if "nutrition" in c:
        c["nutrition_format"] = (n.get("checks") or {}).get("format") or nutrition_format(c["year"])
    return c


def nutrition_format(year):
    """Which Nutrition Facts layout a package of that year carried (FDA rules: NLEA from May 1994, trans fat added
    from 2006, the new format from 2020)."""
    try:
        y = int(year)
    except (TypeError, ValueError):
        return "1994_nlea"
    if y <= 1993:
        return "pre_nlea"
    if y <= 2005:
        return "1994_nlea"
    if y <= 2019:
        return "2006_trans"
    return "2020_new"


# ------------------------------------------------------------------ type
def _font(weight, px):
    return labelart.font(weight, px)


def _text(d, xy, s, px, weight="regular", fill=(0, 0, 0), anchor="la"):
    d.text(xy, s, font=_font(weight, px), fill=fill, anchor=anchor)


def _wrap(s, px, width, weight="regular"):
    """Lines that really fit in width pixels, measured with the SAME font they are drawn in (a word too long for one
    line is split, so nothing ever runs off the panel)."""
    f = _font(weight, px)
    lines, cur = [], ""
    for w in str(s or "").split():
        while f.getlength(w) > width and len(w) > 1:         # one word wider than the panel: split it
            k = len(w)
            while k > 1 and f.getlength(w[:k]) > width:
                k -= 1
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:k])
            w = w[k:]
        t = (cur + " " + w).strip()
        if f.getlength(t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return [ln for ln in lines if ln]


def paragraph(s, W, px=26, weight="regular", color=(20, 20, 20), align="left"):
    """A block of text W pixels wide, wrapped with the font it is drawn in."""
    W = max(int(W), 8)
    lines = _wrap(s, px, W - 8, weight)
    lh = px * 1.22
    img = Image.new("RGBA", (W, int(len(lines) * lh) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 4
    for line in lines:
        if align == "center":
            _text(d, (W / 2, y), line, px, weight, fill=color, anchor="ma")
        else:
            _text(d, (4, y), line, px, weight, fill=color)
        y += lh
    return img


def lines_block(lines, W, px, weight="regular", color=(20, 20, 20), align="left"):
    """Several printed lines, each wrapped on its own (a maker's name over its address)."""
    parts = [paragraph(s, W, px, weight, color, align) for s in lines if str(s).strip()]
    if not parts:
        return None
    img = Image.new("RGBA", (int(W), sum(p.height for p in parts)), (0, 0, 0, 0))
    y = 0
    for p in parts:
        img.paste(p, (0, y), p)
        y += p.height
    return img


# ------------------------------------------------------------------ Nutrition Facts, by the year's format
def _num(v):
    try:
        return float(re.sub(r"[^\d.]", "", str(v)) or "x")
    except ValueError:
        return None


def nutrition(n, W=900, fmt="1994_nlea"):
    """The Nutrition Facts box as printed in that era, black on white, W pixels wide. n = what the real panel says:
    {"serving", "servings", "calories", "fat_calories", "rows": [[label, amount, daily value, indent]], "vitamins"}"""
    if fmt == "pre_nlea":
        return _nutrition_pre(n, W)
    if fmt == "2020_new":
        return _nutrition_2020(n, W)
    u = W / 300.0
    rows = [r for r in n.get("rows", []) if isinstance(r, (list, tuple)) and len(r) >= 2]
    H = int(u * (130 + 20 * len(rows) + 14 * ((len(n.get("vitamins", [])) + 1) // 2) + 60))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    pad = 8 * u
    y = pad
    _text(d, (pad, y), "Nutrition Facts", 34 * u, "black")
    y += 38 * u
    if n.get("serving"):
        _text(d, (pad, y), f"Serving Size {n['serving']}", 11 * u)
        y += 14 * u
    if n.get("servings"):
        _text(d, (pad, y), f"Servings Per Container {n['servings']}", 11 * u)
        y += 16 * u
    d.rectangle([pad, y, W - pad, y + 7 * u], fill=(0, 0, 0))
    y += 10 * u
    _text(d, (pad, y), "Amount Per Serving", 9 * u, "bold")
    y += 13 * u
    if n.get("calories") not in (None, ""):
        _text(d, (pad, y), f"Calories {n['calories']}", 11 * u, "bold")
    if n.get("fat_calories") not in (None, ""):
        _text(d, (W - pad, y), f"Calories from Fat {n['fat_calories']}", 11 * u, anchor="ra")
    y += 15 * u
    d.rectangle([pad, y, W - pad, y + 3 * u], fill=(0, 0, 0))
    y += 5 * u
    _text(d, (W - pad, y), "% Daily Value*", 9 * u, "bold", anchor="ra")
    y += 13 * u
    for r in rows:
        label, amt = str(r[0]), str(r[1])
        dv = str(r[2]) if len(r) > 2 and r[2] not in (None,) else ""
        indent = bool(r[3]) if len(r) > 3 else False
        d.line([pad, y - 2 * u, W - pad, y - 2 * u], fill=(0, 0, 0), width=max(1, int(u * 0.8)))
        x = pad + (12 * u if indent else 0)
        wt = "regular" if indent else "bold"
        _text(d, (x, y), label, 11 * u, wt)
        _text(d, (x + _font(wt, 11 * u).getlength(label) + 4 * u, y), amt, 11 * u)
        if dv:
            _text(d, (W - pad, y), dv, 11 * u, "bold", anchor="ra")
        y += 18 * u
    d.rectangle([pad, y, W - pad, y + 7 * u], fill=(0, 0, 0))
    y += 10 * u
    vit = [str(v) for v in n.get("vitamins", [])]
    for i in range(0, len(vit), 2):
        _text(d, (pad, y), vit[i], 10 * u)
        if i + 1 < len(vit):
            _text(d, (W - pad, y), vit[i + 1], 10 * u, anchor="ra")
        y += 14 * u
    d.line([pad, y, W - pad, y], fill=(0, 0, 0), width=max(1, int(u)))
    y += 4 * u
    # the footnote the 1994 rules require on every panel (fixed regulation wording, not product facts)
    for line in _wrap("*Percent Daily Values are based on a 2,000 calorie diet. Your daily values may be higher or "
                      "lower depending on your calorie needs.", 8 * u, W - 2 * pad):
        _text(d, (pad, y), line, 8 * u)
        y += 10 * u
    y += pad
    img = img.crop((0, 0, W, int(min(y, img.height))))
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, W - 2, img.height - 2], outline=(0, 0, 0), width=max(2, int(u)))
    return img


def _nutrition_2020(n, W):
    """The 2020 format: servings first, big bold calories, '% Daily Value' rows, the newer footnote."""
    u = W / 300.0
    rows = [r for r in n.get("rows", []) if isinstance(r, (list, tuple)) and len(r) >= 2]
    vit = [str(v) for v in n.get("vitamins", [])]
    img = Image.new("RGB", (W, int(u * (170 + 20 * len(rows) + 16 * len(vit) + 70))), (255, 255, 255))
    d = ImageDraw.Draw(img)
    pad = 8 * u
    y = pad
    _text(d, (pad, y), "Nutrition Facts", 34 * u, "black")
    y += 40 * u
    if n.get("servings"):
        _text(d, (pad, y), f"{n['servings']} servings per container", 11 * u)
        y += 15 * u
    if n.get("serving"):
        _text(d, (pad, y), "Serving size", 13 * u, "black")
        _text(d, (W - pad, y), str(n["serving"]), 13 * u, "black", anchor="ra")
        y += 17 * u
    d.rectangle([pad, y, W - pad, y + 9 * u], fill=(0, 0, 0))
    y += 12 * u
    _text(d, (pad, y), "Amount per serving", 9 * u, "bold")
    y += 11 * u
    if n.get("calories") not in (None, ""):
        _text(d, (pad, y), "Calories", 22 * u, "black")
        _text(d, (W - pad, y - 6 * u), str(n["calories"]), 30 * u, "black", anchor="ra")
    y += 30 * u
    d.rectangle([pad, y, W - pad, y + 5 * u], fill=(0, 0, 0))
    y += 8 * u
    _text(d, (W - pad, y), "% Daily Value*", 9 * u, "bold", anchor="ra")
    y += 13 * u
    for r in rows:
        label, amt = str(r[0]), str(r[1])
        dv = str(r[2]) if len(r) > 2 and r[2] else ""
        indent = bool(r[3]) if len(r) > 3 else False
        d.line([pad, y - 2 * u, W - pad, y - 2 * u], fill=(0, 0, 0), width=max(1, int(u * 0.8)))
        x = pad + (12 * u if indent else 0)
        wt = "regular" if indent else "bold"
        _text(d, (x, y), label, 11 * u, wt)
        _text(d, (x + _font(wt, 11 * u).getlength(label) + 4 * u, y), amt, 11 * u)
        if dv:
            _text(d, (W - pad, y), dv, 11 * u, "bold", anchor="ra")
        y += 18 * u
    d.rectangle([pad, y, W - pad, y + 9 * u], fill=(0, 0, 0))
    y += 12 * u
    for v in vit:
        _text(d, (pad, y), v, 10 * u)
        y += 15 * u
    d.rectangle([pad, y, W - pad, y + 4 * u], fill=(0, 0, 0))
    y += 7 * u
    for line in _wrap("*The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to a "
                      "daily diet. 2,000 calories a day is used for general nutrition advice.", 8 * u, W - 2 * pad):
        _text(d, (pad, y), line, 8 * u)
        y += 10 * u
    y += pad
    img = img.crop((0, 0, W, int(min(y, img.height))))
    ImageDraw.Draw(img).rectangle([1, 1, W - 2, img.height - 2], outline=(0, 0, 0), width=max(2, int(u)))
    return img


def _nutrition_pre(n, W):
    """Before mid-1994: 'NUTRITION INFORMATION PER SERVING' as a plain list, then the U.S. RDA percentages."""
    u = W / 300.0
    rows = [r for r in n.get("rows", []) if isinstance(r, (list, tuple)) and len(r) >= 2]
    vit = [str(v) for v in n.get("vitamins", [])]
    img = Image.new("RGB", (W, int(u * (90 + 13 * (len(rows) + 3) + 13 * ((len(vit) + 1) // 2) + 30))), (255, 255, 255))
    d = ImageDraw.Draw(img)
    pad = 8 * u
    y = pad
    _text(d, (W / 2, y), "NUTRITION INFORMATION PER SERVING", 11 * u, "bold", anchor="ma")
    y += 16 * u
    top = []
    if n.get("serving"):
        top.append(("SERVING SIZE", str(n["serving"])))
    if n.get("servings"):
        top.append(("SERVINGS PER PACKAGE", str(n["servings"])))
    if n.get("calories") not in (None, ""):
        top.append(("CALORIES", str(n["calories"])))
    for label, amt in top + [(str(r[0]).upper(), str(r[1])) for r in rows]:
        _text(d, (pad, y), label, 9 * u)
        _text(d, (W - pad, y), amt, 9 * u, anchor="ra")
        y += 13 * u
    if vit:
        y += 4 * u
        _text(d, (W / 2, y), "PERCENTAGE OF U.S. RECOMMENDED DAILY ALLOWANCES (U.S. RDA)", 7.5 * u, "bold", anchor="ma")
        y += 13 * u
        for i in range(0, len(vit), 2):
            _text(d, (pad, y), vit[i].upper(), 8.5 * u)
            if i + 1 < len(vit):
                _text(d, (W / 2 + pad, y), vit[i + 1].upper(), 8.5 * u)
            y += 13 * u
    y += pad
    return img.crop((0, 0, W, int(min(y, img.height))))


def calories_check(n):
    """Do the calories add up? (4 per gram of carbohydrate and protein, 9 per gram of fat, within 15%)"""
    rows = {str(r[0]).lower(): r[1] for r in n.get("rows", []) if isinstance(r, (list, tuple)) and len(r) >= 2}
    get = lambda k: next((_num(v) for lab, v in rows.items() if lab.startswith(k)), None)
    fat, carb, prot, cal = get("total fat") or get("fat"), get("total carb") or get("carb"), get("protein"), \
        _num(n.get("calories"))
    if None in (fat, carb, prot, cal) or not cal:
        return {"ok": None, "why": "not enough numbers to check"}
    est = 4 * carb + 4 * prot + 9 * fat
    off = abs(est - cal) / cal
    return {"ok": off <= 0.15, "calories": cal, "from_grams": round(est, 1), "off_by": round(off, 3)}


# ------------------------------------------------------------------ UPC-A at its real printed size
L_CODE = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
X_MM = 0.33          # GS1 nominal bar module at 100%
BAR_MM = 22.85       # GS1 nominal bar height at 100%
QUIET = 9            # GS1 quiet zone, modules, each side (UPC-A)


def check_digit(first11):
    d = [int(c) for c in first11]
    return (10 - (sum(d[0::2]) * 3 + sum(d[1::2])) % 10) % 10


def upc12(code):
    """The 12 digits of a UPC-A, or ValueError. 11 digits: the check digit is worked out from them. 12 digits (or
    13 with a leading 0, the same code as EAN-13): the check digit must add up. Never padded, cut or shifted."""
    d = re.sub(r"\D", "", str(code or ""))
    if len(d) == 13 and d[0] == "0":
        d = d[1:]
    if len(d) == 11:
        return d + str(check_digit(d))
    if len(d) == 12:
        if check_digit(d[:11]) != int(d[11]):
            raise ValueError(f"UPC {d}: the check digit doesn't add up (should be {check_digit(d[:11])})")
        return d
    raise ValueError(f"'{code}' is not a UPC-A code (needs 11 or 12 digits, has {len(d)})")


def upc(code, px_per_mm=12.0, magnification=1.0):
    """A real, scannable UPC-A barcode at its true printed size: X = 0.33 mm x magnification per module, 113 modules
    wide with the 9-module quiet zones, 22.85 mm bars (the guard bars and the first and last digits' bars run 5
    modules longer), the digits under it. -> RGB image (white background)."""
    s = upc12(code)
    digits = [int(c) for c in s]
    bits = "101" + "".join(L_CODE[x] for x in digits[:6]) + "01010" + \
        "".join("".join("1" if b == "0" else "0" for b in L_CODE[x]) for x in digits[6:]) + "101"
    M = 10                                                     # drawn at 10 px per module, then sized exactly
    total = len(bits) + 2 * QUIET                              # 113 modules
    bar = int(round(BAR_MM / X_MM * M))
    ext = 5 * M
    txt = int(8.5 * M)
    img = Image.new("RGB", (total * M, bar + ext + txt // 3 + 2 * M), (255, 255, 255))
    d = ImageDraw.Draw(img)
    long_ = set(range(0, 3)) | set(range(3, 10)) | set(range(45, 50)) | set(range(85, 92)) | set(range(92, 95))
    x0 = QUIET * M
    for i, b in enumerate(bits):
        if b == "1":
            d.rectangle([x0 + i * M, M, x0 + (i + 1) * M - 1, M + bar + (ext if i in long_ else 0)], fill=(0, 0, 0))
    px = int(7.5 * M)
    y = M + bar + M // 2
    _text(d, (x0 - 1.5 * M, M + bar + ext - px * 0.85), s[0], px * 0.8, anchor="ra")
    _text(d, (x0 + 27.5 * M, y), s[1:6], px, anchor="ma")
    _text(d, (x0 + 67.5 * M, y), s[6:11], px, anchor="ma")
    _text(d, (x0 + 96.5 * M, M + bar + ext - px * 0.85), s[11], px * 0.8)
    w_mm = total * X_MM * magnification
    scale = w_mm * px_per_mm / img.width
    return img.resize((max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale)))), Image.LANCZOS)


def fit_upc(code, max_w, max_h, px_per_mm):
    """The barcode at 100% if it fits the space, else the biggest size from 80% up that does, turned on its side if
    that helps. -> (image, magnification) or (None, reason) - never squeezed below the 80% GS1 allows."""
    try:
        upc12(code)
    except ValueError as e:
        return None, str(e)
    for mag in (1.0, 0.95, 0.9, 0.85, 0.8):
        im = upc(code, px_per_mm, mag)
        if im.width <= max_w and im.height <= max_h:
            return im, mag
        if im.height <= max_w and im.width <= max_h:
            return im.rotate(90, expand=True), mag
    return None, f"no room for the barcode even at 80% ({max_w / px_per_mm:.0f} x {max_h / px_per_mm:.0f} mm free)"


# ------------------------------------------------------------------ the real logo and picture, cut from the front
def _knock(logo, paper):
    """Only the ink of a crop, over the paper (same rule as panels.brand_panel)."""
    a = np.asarray(logo.convert("RGB")).astype(np.float32)
    L, Lp = a.mean(-1), float(np.mean(paper))
    sat = np.linalg.norm(a - L[..., None], axis=-1)
    sat_p = float(np.linalg.norm(np.array(paper, np.float32) - Lp))
    ink = np.maximum(0, Lp - L) + 1.5 * np.maximum(0, sat - sat_p)
    alpha = np.clip((ink - 45) / 30, 0, 1)
    import cv2
    n, lab, st, _ = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8))
    for k in range(1, n):                                 # slivers of the next line or picture cut by the crop: out
        x, y, ww, hh, area = st[k]
        Hh, Ww = alpha.shape
        sliver = (y == 0 and y + hh < 0.15 * Hh) or (y + hh >= Hh and y > 0.85 * Hh)   # bits of the next line
        corner = (x == 0 or x + ww >= Ww) and (y == 0 or y + hh >= Hh) and area < 0.01 * alpha.size  # a picture's edge
        if sliver or corner:
            alpha[lab == k] = 0
    return Image.fromarray(np.dstack([a, alpha * 255]).astype(np.uint8), "RGBA")


def _feather(im, frac=0.05):
    """A product picture printed with soft edges into the paper (no hard pasted rectangle)."""
    a = np.asarray(im.convert("RGB"))
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]) / (frac * min(w, h))
    alpha = np.clip(e, 0, 1) ** 1.5
    return Image.fromarray(np.dstack([a, alpha * 255]).astype(np.uint8), "RGBA")


def ink_color(front, paper):
    """The box's own printing color (its strongest colored ink on the front), for the words set on a rebuilt side."""
    a = np.asarray(front.convert("RGB").resize((160, 160))).reshape(-1, 3).astype(float)
    L = a.mean(1)
    sat = a.max(1) - a.min(1)
    pick = a[(sat > 60) & (L < np.mean(paper) - 40)]
    if len(pick) < 50:
        return (25, 25, 25)
    q = (pick // 24).astype(int)
    key = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    keys, counts = np.unique(key, return_counts=True)
    return tuple(int(v) for v in np.median(pick[key == keys[np.argmax(counts)]], 0))


# ------------------------------------------------------------------ one element, drawn into its own space
def element(kind, c, w, h, px_per_mm, paper, front=None, logo_box=None, photo_box=None, ink=(20, 20, 20)):
    """One printed thing for a w x h space (in pixels) from the facts: 'nutrition', 'ingredients', 'upc',
    'maker_lines', 'legal_lines', 'net_weight', 'name', 'logo', 'picture'. -> RGBA image no bigger than the space,
    or None when the fact isn't known (then nothing is drawn there)."""
    w, h = max(int(w), 8), max(int(h), 8)
    small = max(10, min(int(2.2 * px_per_mm), int(w / 12)))   # about 2.2 mm type, like real side panels
    im = None
    if kind == "nutrition" and c.get("nutrition"):
        im = nutrition(c["nutrition"], max(300, w), c.get("nutrition_format") or "1994_nlea")
    elif kind == "ingredients" and c.get("ingredients"):
        t = str(c["ingredients"])
        im = paragraph(t if t.upper().startswith("INGREDIENT") else "INGREDIENTS: " + t, w, px=small)
    elif kind == "upc" and c.get("upc"):
        im, _ = fit_upc(c["upc"], w, h, px_per_mm)
        if im is not None:
            im = im.convert("RGBA")
    elif kind == "maker_lines" and c.get("maker_lines"):
        im = lines_block(c["maker_lines"], w, small)
    elif kind == "legal_lines" and c.get("legal_lines"):
        im = lines_block(c["legal_lines"], w, small)
    elif kind == "net_weight" and (c.get("net_weight") or c.get("count")):
        im = lines_block([x for x in (c.get("count"), c.get("net_weight")) if x], w, int(small * 1.3), "bold", ink)
    elif kind == "name" and c.get("name"):
        im = paragraph(c["variant"] or c["name"], w, px=max(small * 2, int(min(w / 9, h / 2.5))), weight="black",
                       color=ink, align="center")
    elif kind in ("logo", "picture") and front is not None:
        b = logo_box if kind == "logo" else photo_box
        if b:
            fw, fh = front.size
            crop = front.crop((int(b[0] * fw), int(b[1] * fh), int(b[2] * fw), int(b[3] * fh)))
            im = _knock(crop, paper) if kind == "logo" else _feather(crop)
            if h > 1.8 * w and im.width > im.height:          # a tall narrow space: the logo reads upward
                im = im.rotate(90, expand=True)
    if im is None:
        return None
    s = min(w / im.width, h / im.height, 1.0 if kind == "upc" else 99)
    if kind == "upc":                                          # the barcode keeps its real size (fit_upc chose it)
        s = min(1.0, s)
        if s < 1.0:
            return None
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


# ------------------------------------------------------------------ one rebuilt side
DEFAULT = {   # what each side carries when no photo of that era shows its layout (facts only, in this order)
    "back": ["logo", "name", "picture", "net_weight", "maker_lines"],
    "left": ["nutrition", "ingredients"],
    "right": ["logo", "maker_lines", "legal_lines"],
    "top": ["logo"],
    "bottom": ["upc", "legal_lines"],
}


def panel_notes(side, c, front, logo_box, photo_box, w, h, paper, size_mm=None, layout=None, want=None):
    """One rebuilt side as a w x h picture, from facts only. layout (optional) = where a real box of that era put
    each kind of thing on this side ([{"kind", "box": [x0, y0, x1, y1] fractions}], from the closest sister box's
    photo); want (optional) = which kinds of things this side carries, in order; else the side's usual order.
    -> (image, [kinds drawn], [kinds with no fact to draw])"""
    c = c or {}
    img = Image.new("RGB", (w, h), tuple(int(v) for v in paper))
    ppm = (w / size_mm[0]) if size_mm and size_mm[0] else (w / 140.0)
    ink = ink_color(front, paper) if front is not None else (25, 25, 25)
    used, missing = [], []
    if not want:
        want = DEFAULT.get(side, ["logo"])
        if side == "left" and not c.get("food"):
            want = ["logo", "name", "net_weight"]
    known = lambda k: bool(c.get(k)) or (k == "net_weight" and bool(c.get("count")))
    if not any(known(k) for k in want if k not in ("logo", "name", "picture")):
        want = ["logo", "name"] + [k for k in want if k not in ("logo", "name")]   # nothing known for this side:
        #                                                     a clean side with the real logo and the product name
    if layout:                                                 # a real box's layout for this side: same places
        for el in layout:
            k, b = el.get("kind"), el.get("box")
            if not b or k not in ("nutrition", "ingredients", "upc", "maker_lines", "legal_lines", "net_weight",
                                  "name", "logo", "picture"):
                continue
            bw, bh = int((b[2] - b[0]) * w), int((b[3] - b[1]) * h)
            im = element(k, c, bw, bh, ppm, paper, front, logo_box, photo_box, ink)
            if im is None:
                missing.append(k)
                continue
            x = int(b[0] * w + (bw - im.width) / 2)
            y = int(b[1] * h + (bh - im.height) / 2)
            img.paste(im, (x, y), im if im.mode == "RGBA" else None)
            used.append(k)
        if used:
            return img, used, missing
    m = int(0.06 * min(w, h))
    if side == "bottom":                                       # side by side on a shallow bottom
        x = m
        for k in want:
            room = (w - x - m, h - 2 * m)
            im = element(k, c, room[0] if k != "upc" else min(room[0], w * 0.6), room[1], ppm, paper, front,
                         logo_box, photo_box, ink)
            if im is None:
                missing.append(k)
                continue
            img.paste(im, (x, (h - im.height) // 2), im if im.mode == "RGBA" else None)
            x += im.width + m
            used.append(k)
        return img, used, missing
    blocks = []
    tall = h > 2 * w
    for k in want:                                             # stacked top to bottom, each fitted to the width
        bh = h - 2 * m if k in ("nutrition", "ingredients", "picture") else \
            int((h - 2 * m) * (0.45 if tall and k == "logo" else 0.3))     # a tall side: the logo reads upward
        im = element(k, c, w - 2 * m, bh, ppm, paper, front, logo_box, photo_box, ink)
        if im is None:
            missing.append(k)
            continue
        blocks.append((k, im))
        used.append(k)
    total = sum(b.height for _, b in blocks) + m * max(0, len(blocks) - 1)
    kf = min(1.0, (h - 2 * m) / max(total, 1))
    y = m + int(((h - 2 * m) - total * kf) / 2)
    for k, b in blocks:
        if kf < 1.0 and k != "upc":
            b = b.resize((max(1, int(b.width * kf)), max(1, int(b.height * kf))), Image.LANCZOS)
        img.paste(b, ((w - b.width) // 2, y), b if b.mode == "RGBA" else None)
        y += b.height + int(m * kf)
    return img, used, missing


def panel(side, c, front, logo_box, photo_box, w, h, paper, size_mm=None, layout=None, want=None):
    """One rebuilt side as a w x h picture (see panel_notes)."""
    return panel_notes(side, c, front, logo_box, photo_box, w, h, paper, size_mm, layout, want)[0]
