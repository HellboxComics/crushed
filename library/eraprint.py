"""THE PANELS NO PHOTO SHOWS, REBUILT AS THEY WERE PRINTED IN THAT ERA (his choice, 2026-10-02): the Nutrition Facts
box in the FDA's 1994 format, the ingredients, the maker's name and address, a real scannable UPC-A barcode, and on
the back the real logo and the real product picture (cut from the real front) with the era's kind of copy. Every word
is set in real type - nothing is painted by an AI. The words themselves come from your local AI's knowledge of the
product (kept on the item's card as "era_print"), marked as rebuilt, not photographed.

    img = eraprint.panel(side, content, front_img, logo_box, photo_box, w, h, paper)
"""
import json
import os
import re

import numpy as np
from PIL import Image, ImageDraw

import labelart

ASK = """You are a packaging archivist. Product: {product}.
Write what was printed on the parts of this box that photos don't show, exactly as it was in that era, as accurately
as you know (real nutrition values for that era's recipe, the real ingredients wording, the maker's real address).
Answer ONLY JSON:
{{"nutrition": {{"serving": "1 Pastry (52g)", "servings": "8", "calories": 200, "fat_calories": 45,
   "rows": [["Total Fat", "5g", "8%", 0], ["Saturated Fat", "1.5g", "8%", 1], ["Cholesterol", "0mg", "0%", 0],
            ["Sodium", "170mg", "7%", 0], ["Total Carbohydrate", "37g", "12%", 0], ["Dietary Fiber", "1g", "3%", 1],
            ["Sugars", "16g", "", 1], ["Protein", "2g", "", 0]],
   "vitamins": ["Vitamin A 10%", "Vitamin C 0%", "Calcium 0%", "Iron 10%"]}},
 "ingredients": "INGREDIENTS: ...",
 "maker": ["Distributed by Kellogg USA Inc.", "Battle Creek, MI 49016 U.S.A."],
 "upc_first11": "03800031810",
 "back_headline": "short line in the era's ad style",
 "back_body": "two short sentences in the era's ad style",
 "bottom_lines": ["short printed lines found on the bottom, e.g. a code date line"]}}
(The example numbers are only the shape - use the real ones for this product.)"""


def content(product, model=None, log=print):
    import vet as V
    model = model or V.model()
    body = {"model": model, "stream": False, "format": "json", "think": False,
            "options": {"temperature": 0.1, "num_predict": 1500},
            "messages": [{"role": "user", "content": ASK.format(product=product)}]}
    txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
    c = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    c["_note"] = "rebuilt from your local AI's knowledge of the era's box, not photographed"
    return c


# ------------------------------------------------------------------ type
def _font(weight, px):
    return labelart.font(weight, px)


def _text(d, xy, s, px, weight="regular", fill=(0, 0, 0), anchor="la"):
    d.text(xy, s, font=_font(weight, px), fill=fill, anchor=anchor)


def _wrap(s, px, width, weight="regular"):
    f = _font(weight, px)
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def nutrition(n, W=900):
    """The 1994 FDA Nutrition Facts box, black on white, W pixels wide."""
    u = W / 300.0                                  # layout unit
    rows = n.get("rows", [])
    H = int(u * (120 + 22 * len(rows) + 70))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    pad = 8 * u
    y = pad
    _text(d, (pad, y), "Nutrition Facts", 34 * u, "black")
    y += 38 * u
    _text(d, (pad, y), f"Serving Size {n.get('serving', '')}", 11 * u)
    y += 14 * u
    _text(d, (pad, y), f"Servings Per Container {n.get('servings', '')}", 11 * u)
    y += 16 * u
    d.rectangle([pad, y, W - pad, y + 7 * u], fill=(0, 0, 0))
    y += 10 * u
    _text(d, (pad, y), "Amount Per Serving", 9 * u, "bold")
    y += 13 * u
    _text(d, (pad, y), f"Calories {n.get('calories', '')}", 11 * u, "bold")
    _text(d, (W - pad, y), f"Calories from Fat {n.get('fat_calories', '')}", 11 * u, anchor="ra")
    y += 15 * u
    d.rectangle([pad, y, W - pad, y + 3 * u], fill=(0, 0, 0))
    y += 5 * u
    _text(d, (W - pad, y), "% Daily Value*", 9 * u, "bold", anchor="ra")
    y += 13 * u
    for label, amt, dv, indent in rows:
        d.line([pad, y - 2 * u, W - pad, y - 2 * u], fill=(0, 0, 0), width=max(1, int(u * 0.8)))
        x = pad + (12 * u if indent else 0)
        _text(d, (x, y), label, 11 * u, "regular" if indent else "bold")
        lw = _font("regular" if indent else "bold", 11 * u).getlength(label)
        _text(d, (x + lw + 4 * u, y), amt, 11 * u)
        if dv:
            _text(d, (W - pad, y), dv, 11 * u, "bold", anchor="ra")
        y += 18 * u
    d.rectangle([pad, y, W - pad, y + 7 * u], fill=(0, 0, 0))
    y += 10 * u
    vit = n.get("vitamins", [])
    for i in range(0, len(vit), 2):
        _text(d, (pad, y), vit[i], 10 * u)
        if i + 1 < len(vit):
            _text(d, (W - pad, y), vit[i + 1], 10 * u, anchor="ra")
        y += 14 * u
    d.line([pad, y, W - pad, y], fill=(0, 0, 0), width=max(1, int(u)))
    y += 4 * u
    for line in _wrap("*Percent Daily Values are based on a 2,000 calorie diet. Your daily values may be higher or "
                      "lower depending on your calorie needs.", 8 * u, W - 2 * pad):
        _text(d, (pad, y), line, 8 * u)
        y += 10 * u
    y += pad
    img = img.crop((0, 0, W, int(y)))
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, W - 2, img.height - 2], outline=(0, 0, 0), width=max(2, int(u)))
    return img


def paragraph(s, W, px=26, weight="regular", color=(20, 20, 20), bold_lead=True):
    lines = _wrap(s, px, W - 8)
    img = Image.new("RGBA", (W, int(len(lines) * px * 1.22) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 4
    for i, line in enumerate(lines):
        _text(d, (4, y), line, px, weight, fill=color)
        y += px * 1.22
    return img


L_CODE = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]


def upc(first11, W=600):
    """A real UPC-A barcode (the check digit computed), with its numbers under it."""
    digits = [int(c) for c in re.sub(r"\D", "", first11)[:11].ljust(11, "0")]
    check = (10 - (sum(digits[0::2]) * 3 + sum(digits[1::2])) % 10) % 10
    digits.append(check)
    bits = "101" + "".join(L_CODE[x] for x in digits[:6]) + "01010" + \
        "".join("".join("1" if b == "0" else "0" for b in L_CODE[x]) for x in digits[6:]) + "101"
    mod = W / (len(bits) + 18)
    H = int(mod * 60)
    img = Image.new("RGB", (W, H + int(mod * 12)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    x0 = 9 * mod
    guard = set(list(range(0, 3)) + list(range(45, 50)) + list(range(92, 95)))
    for i, b in enumerate(bits):
        if b == "1":
            d.rectangle([x0 + i * mod, 2 * mod, x0 + (i + 1) * mod - 0.01, H + (5 * mod if i in guard else 0)],
                        fill=(0, 0, 0))
    s = "".join(map(str, digits))
    px = int(mod * 9)
    _text(d, (x0 - 7 * mod, H), s[0], px)
    _text(d, (x0 + 12 * mod, H + mod), s[1:6], px)
    _text(d, (x0 + 58 * mod, H + mod), s[6:11], px)
    _text(d, (x0 + 97 * mod, H), s[11], px)
    return img


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


def panel(side, c, front, logo_box, photo_box, w, h, paper):
    """One rebuilt side as a w x h picture."""
    img = Image.new("RGB", (w, h), tuple(int(v) for v in paper))
    fw, fh = front.size
    crop = lambda b: front.crop((int(b[0] * fw), int(b[1] * fh), int(b[2] * fw), int(b[3] * fh)))
    m = int(0.06 * min(w, h))
    blocks = []
    if side == "left":                                   # Nutrition Facts on top, ingredients under it
        blocks = [nutrition(c.get("nutrition", {}), w - 2 * m),
                  paragraph(c.get("ingredients", ""), w - 2 * m, px=max(12, int(w / 34)))]
    elif side == "right":
        lg = _knock(crop(logo_box), paper).rotate(90, expand=True) if logo_box else None
        blocks = ([lg] if lg else []) + [paragraph(" ".join(c.get("maker", [])), w - 2 * m, px=max(12, int(w / 26)))]
    elif side == "back":
        lg = _knock(crop(logo_box), paper) if logo_box else None
        ph = _feather(crop(photo_box)) if photo_box else None
        blocks = ([lg] if lg else []) + \
                 [paragraph(c.get("back_headline", ""), w - 2 * m, px=max(18, int(w / 16)), weight="black",
                            color=(200, 30, 45))] + \
                 ([ph] if ph else []) + [paragraph(c.get("back_body", ""), w - 2 * m, px=max(14, int(w / 30)))]
    elif side == "bottom":
        blocks = [upc(c.get("upc_first11", "03800000000"), int(min(w * 0.4, h * 1.2))),
                  paragraph("  ".join(c.get("bottom_lines", []) + c.get("maker", [])), int(w * 0.5), px=max(12, int(h / 14)))]
        x = m
        for b in blocks:                                  # side by side on the shallow bottom
            s = min((h - 2 * m) / b.height, 1.0)
            b = b.resize((max(1, int(b.width * s)), max(1, int(b.height * s))), Image.LANCZOS)
            img.paste(b, (x, (h - b.height) // 2), b if b.mode == "RGBA" else None)
            x += b.width + m
        return img
    elif side == "top":
        lg = _knock(crop(logo_box), paper) if logo_box else None
        blocks = [lg] if lg else []
    # stack the blocks top to bottom, each fitted to the width, the whole stack fitted to the height
    fit = []
    for b in blocks:
        if b is None or b.width == 0:
            continue
        s = (w - 2 * m) / b.width
        fit.append(b.resize((max(1, int(b.width * s)), max(1, int(b.height * s))), Image.LANCZOS))
    total = sum(b.height for b in fit) + m * (len(fit) - 1)
    k = min(1.0, (h - 2 * m) / max(total, 1))
    y = m + int(((h - 2 * m) - total * k) / 2)
    for b in fit:
        b = b.resize((max(1, int(b.width * k)), max(1, int(b.height * k))), Image.LANCZOS)
        img.paste(b, ((w - b.width) // 2, y), b if b.mode == "RGBA" else None)
        y += b.height + int(m * k)
    return img
