"""LABEL ARTWORK: a printed label rebuilt as crisp artwork from a written layout - the way game studios make labels.
The words are set in real type, so every letter is exact at any zoom; colors and positions are measured from the
real photo. No painting AI touches the letters (it can't spell small print - proven by the label test 2026-10-02).

The layout (JSON), in reading orientation (for a battery: the plus end at the left), positions as fractions of the
label (0..1 across, 0..1 down):
  {"width_mm": 50.3, "height_mm": 45.6, "background": "#101010",
   "shapes": [ {"type": "rect", "x": 0, "y": 0, "w": 0.36, "h": 1, "fill": "#c87533", "metal": true,
                "shade": "copper"},
               {"type": "rect", ..., "stroke": "#2e9c46", "stroke_w": 0.006, "fill": null},
               {"type": "ellipse", "x": .., "y": .., "w": .., "h": .., "fill": "#f2f2f2"},
               {"type": "bar", "x": .., "y": .., "w": .., "h": .., "colors": ["#3fbf4f", "#f4f4f4", "#e8402a"],
                "stops": [0, 0.55, 0.75, 1]} ],
   "texts":  [ {"text": "BRAND", "x": 0.4, "y": 0.05, "h": 0.12, "color": "#ffffff", "weight": "black",
                "w": 0.5, "align": "left", "rotate": 0} ] }
  text "h" = letter height as a fraction of the label height; "w" (optional) = squeeze/stretch to exactly that
  width; "weight": regular | bold | black; "mark": "registered" | "tm" adds the small symbol after it.

    from labelart import render
    color_png, metal_rough_png = render(layout, out_dir, px=4096)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = {   # this Mac's own fonts first, then free fallbacks
    "black": ["/System/Library/Fonts/Supplemental/Arial Black.ttf", "/Library/Fonts/Arial Black.ttf",
              "/System/Library/Fonts/HelveticaNeue.ttc", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"],
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/HelveticaNeue.ttc",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"],
    "regular": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/freefont/FreeSans.ttf"],
}
MARKS = {"registered": "®", "tm": "™"}


def font(weight, px):
    for p in FONTS.get(weight, FONTS["bold"]):
        if os.path.exists(p):
            return ImageFont.truetype(p, max(int(px), 4))
    return ImageFont.load_default()


def rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _box(t, W, H, d):
    """Where a line of text will really land: (x0, y0, x1, y1) in pixels."""
    hpx = t["h"] * H
    f = font(t.get("weight", "bold"), hpx * 1.38)
    x0, y0, x1, y1 = d.textbbox((0, 0), t["text"], font=f)
    w = t["w"] * W if t.get("w") else (x1 - x0 + 8) * hpx / max(y1 - y0 + 8, 1)
    if t.get("mark"):
        w += hpx * 0.6
    x = t["x"] * W - (w / 2 if t.get("align") == "center" else w if t.get("align") == "right" else 0)
    return x, t["y"] * H, x + w, t["y"] * H + hpx


def no_overlaps(texts, W, H, d, gap=0.012):
    """No two lines of text may touch: where one would run into the line below it (overlapping side to side),
    it is made just short enough to stop a small gap above. Shrinks only; keeps every line's top and its words."""
    for _ in range(3):
        boxes = [_box(t, W, H, d) for t in texts]
        changed = False
        for i, a in enumerate(boxes):
            for j, b in enumerate(boxes):
                if i == j or texts[i].get("rotate") or texts[j].get("rotate"):
                    continue
                side = min(a[2], b[2]) - max(a[0], b[0]) > 0
                if side and a[1] <= b[1] < a[3]:            # line i starts above line j and runs into it
                    new_h = (b[1] - a[1]) / H - gap
                    if new_h > 0.01 and new_h < texts[i]["h"]:
                        if texts[i].get("w"):
                            texts[i]["w"] *= new_h / texts[i]["h"]    # keep its letters' proportions
                        texts[i]["h"] = new_h
                        changed = True
        if not changed:
            break
    return texts


def render(layout, out_dir, px=4096, name="label"):
    """-> (color png, metal/roughness png in the glTF layout: G roughness, B metallic), reading orientation."""
    os.makedirs(out_dir, exist_ok=True)
    W = px
    H = int(round(px * layout["height_mm"] / layout["width_mm"]))
    img = Image.new("RGB", (W, H), rgb(layout.get("background", "#ffffff")))
    mr = Image.new("RGB", (W, H), (0, int(255 * layout.get("roughness", 0.45)), 0))
    d, dm = ImageDraw.Draw(img), ImageDraw.Draw(mr)
    box = lambda s: (s["x"] * W, s["y"] * H, (s["x"] + s["w"]) * W, (s["y"] + s["h"]) * H)
    for s in layout.get("shapes", []):
        b = box(s)
        t = s.get("type", "rect")
        if t == "bar":
            cols = [np.array(rgb(c), float) for c in s["colors"]]
            stops = s.get("stops") or list(np.linspace(0, 1, len(cols)))
            x0, y0, x1, y1 = [int(v) for v in b]
            dm.rectangle(b, fill=(0, int(255 * layout.get("roughness", 0.45)), 0))    # (plain ink: not metal)
            for x in range(x0, x1):
                f = (x - x0) / max(x1 - x0 - 1, 1)
                k = max(i for i in range(len(stops)) if stops[i] <= f) if f > 0 else 0
                k = min(k, len(cols) - 2)
                u = (f - stops[k]) / max(stops[k + 1] - stops[k], 1e-6)
                c = cols[k] * (1 - u) + cols[k + 1] * u
                d.line([(x, y0), (x, y1)], fill=tuple(int(v) for v in c))
            continue
        fill = rgb(s["fill"]) if s.get("fill") else None
        outline = rgb(s["stroke"]) if s.get("stroke") else None
        if t == "arrow":                                 # a printed arrow (labels point at things: "press here")
            d.polygon(arrow(b, s.get("dir", "right")), fill=fill or outline or (20, 20, 20))
            dm.polygon(arrow(b, s.get("dir", "right")), fill=(0, int(255 * layout.get("roughness", 0.45)), 0))
            continue
        width = int((s.get("stroke_w") or 0) * H) or (1 if outline else 0)
        if s.get("shade") == "copper" and fill:          # metal ink: an even color with a faint brushed grain.
            x0, y0, x1, y1 = [int(v) for v in b]         # NO painted-in light - the renderer lights it (a texture
            base = np.array(fill, float)                 # with light baked in looks fake from every other angle)
            grain = np.random.default_rng(3).normal(0, 1, max(x1 - x0, 1))
            grain = np.convolve(grain, np.ones(9) / 9, "same")
            for i, x in enumerate(range(x0, x1)):
                k = 1 + 0.025 * grain[i]
                d.line([(x, y0), (x, y1)], fill=tuple(int(min(255, v * k)) for v in base))
        elif t == "ellipse":
            d.ellipse(b, fill=fill, outline=outline, width=width)
        else:
            d.rectangle(b, fill=fill, outline=outline, width=width)
        if s.get("metal"):
            (dm.ellipse if t == "ellipse" else dm.rectangle)(b, fill=(0, int(255 * s.get("roughness", 0.3)), 255))
        elif fill:                                       # plain ink drawn OVER metal ink is not metal any more
            (dm.ellipse if t == "ellipse" else dm.rectangle)(b, fill=(0, int(255 * layout.get("roughness", 0.45)), 0))
    ground = np.asarray(img).astype(float)               # the print under the words (shapes only), for the
    #                                                      measured can-it-be-read check
    texts = no_overlaps([dict(t) for t in layout.get("texts", [])], W, H, d)
    placed = []                                          # every line's final box, for the exact overlap check
    for tx in texts:
        mark = MARKS.get(tx.get("mark"), "")
        text = tx["text"]
        hpx = tx["h"] * H
        f = font(tx.get("weight", "bold"), hpx * 1.38)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        tw, th = x1 - x0, y1 - y0
        layer = Image.new("L", (int(tw) + 8, int(th) + 8), 0)
        ImageDraw.Draw(layer).text((4 - x0, 4 - y0), text, font=f, fill=255)
        tgt_h = int(hpx)
        tgt_w = int(tx["w"] * W) if tx.get("w") else int(layer.width * tgt_h / max(layer.height, 1))
        layer = layer.resize((max(tgt_w, 1), max(tgt_h, 1)), Image.LANCZOS)
        if tx.get("rotate"):
            layer = layer.rotate(tx["rotate"], expand=True, resample=Image.BICUBIC)
        x = tx["x"] * W
        if tx.get("align") == "center":
            x -= layer.width / 2
        elif tx.get("align") == "right":
            x -= layer.width
        # words printed on a panel stay inside that panel (2026-10-03: "JAN 2001" ran out of the bottom of its tan
        # box): the smallest filled box under the words' middle, and the words shrunk to fit it with a margin
        cx, cy = x + 0.15 * layer.width, tx["y"] * H + 0.3 * layer.height   # (where the words start: a panel
        #                                                       they overflow may not hold their middle)
        under = [box(s) for s in layout.get("shapes", []) if s.get("fill") and s.get("type", "rect") == "rect"
                 and box(s)[0] <= cx <= box(s)[2] and box(s)[1] <= cy <= box(s)[3]
                 and (box(s)[2] - box(s)[0]) * (box(s)[3] - box(s)[1]) < 0.5 * W * H]
        if under:
            bx0, by0, bx1, by1 = min(under, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            m = 0.06 * min(bx1 - bx0, by1 - by0)
            y = tx["y"] * H
            if x < bx0 + m or y < by0 + m or x + layer.width > bx1 - m or y + layer.height > by1 - m:
                k = min(1.0, (bx1 - bx0 - 2 * m) / max(layer.width, 1), (by1 - by0 - 2 * m) / max(layer.height, 1))
                if k > 0.3:
                    layer = layer.resize((max(1, int(layer.width * k)), max(1, int(layer.height * k))), Image.LANCZOS)
                    x = min(max(x, bx0 + m), bx1 - m - layer.width)
                    tx = dict(tx, y=min(max(y, by0 + m), by1 - m - layer.height) / H)
        img.paste(Image.new("RGB", layer.size, rgb(tx.get("color", "#000000"))), (int(x), int(tx["y"] * H)), layer)
        placed.append({"text": text, "box": [x / W, tx["y"] * H / H, (x + layer.width) / W, (tx["y"] * H + layer.height) / H],
                       **legible(ground, (int(x), int(tx["y"] * H), int(x) + layer.width, int(tx["y"] * H) + layer.height),
                                 rgb(tx.get("color", "#000000")))})
        if not tx.get("metal"):                          # the letters' ink is not metal, even on a copper band
            mr.paste(Image.new("RGB", layer.size, (0, int(255 * layout.get("roughness", 0.45)), 0)),
                     (int(x), int(tx["y"] * H)), layer)
        if mark:                                    # (R) / TM: small and raised, like real print
            fm = font("bold", hpx * 0.5)
            mx0, my0, mx1, my1 = d.textbbox((0, 0), mark, font=fm)
            d.text((int(x) + layer.width + hpx * 0.04 - mx0, int(tx["y"] * H) - my0), mark, font=fm,
                   fill=rgb(tx.get("color", "#000000")))
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=40, threshold=2))
    c, m = os.path.join(out_dir, name + ".png"), os.path.join(out_dir, name + "_mr.png")
    img.save(c)
    mr.save(m)
    json.dump({"texts": placed, "overlaps": overlaps(placed), "off_label": off_label(placed),
               "unreadable": unreadable(placed)},
              open(os.path.join(out_dir, name + "_boxes.json"), "w"), indent=1)
    return c, m


def overlaps(placed, least=0.15):
    """Lines of text printed on top of each other, MEASURED from where each really landed (rotated lines included):
    every pair whose boxes share more than `least` of the smaller box. [(text a, text b, share)]"""
    out = []
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            ax0, ay0, ax1, ay1 = a["box"]
            bx0, by0, bx1, by1 = b["box"]
            ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
            iy = max(0.0, min(ay1, by1) - max(ay0, by0))
            small = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
            if small > 0 and ix * iy / small > least:
                out.append({"a": a["text"], "b": b["text"], "share": round(ix * iy / small, 2)})
    return out


def arrow(b, way="right"):
    """A plain printed arrow filling box b: a shaft and a triangle head pointing `way` (right/left/up/down)."""
    x0, y0, x1, y1 = b
    if way in ("up", "down"):                            # drawn pointing right in a turned box, then turned back
        pts = arrow((y0, x0, y1, x1), "right" if way == "down" else "left")
        return [(x, y) for y, x in pts]
    w, h, cy = x1 - x0, y1 - y0, (y0 + y1) / 2
    pts = [(0, cy - 0.18 * h), (0.5 * w, cy - 0.18 * h), (0.5 * w, y0), (w, cy), (0.5 * w, y1),
           (0.5 * w, cy + 0.18 * h), (0, cy + 0.18 * h)]
    return [(x0 + px, py) if way == "right" else (x1 - px, py) for px, py in pts]


def _lum(c):
    """WCAG 2 relative luminance of an sRGB color (0..1)."""
    v = np.asarray(c, float) / 255
    v = np.where(v <= 0.03928, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return float(v @ [0.2126, 0.7152, 0.0722])


def contrast(a, b):
    """WCAG 2 contrast ratio of two colors: 1 (the same) .. 21 (black on white)."""
    la, lb = sorted((_lum(a), _lum(b)))
    return (lb + 0.05) / (la + 0.05)


def legible(ground, box, color, near=40.0):
    """Can this line be read where it landed - MEASURED on the print under it (shapes only): is it on one plain
    ground (no dot, panel edge or band edge under part of it) and does its ink stand out from that ground?
    (2026-10-09: "PRESS DOTS" was set dark brown on a black box, and a white test dot sat on "Made in U.S.A." -
    the look-compare called it 9/10.) -> {"ground": share of the box on its main ground color, "contrast": WCAG}"""
    H, W = ground.shape[:2]
    x0, y0, x1, y1 = max(box[0], 0), max(box[1], 0), min(box[2], W), min(box[3], H)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return {"ground": 1.0, "contrast": 21.0}
    g = ground[y0:y1, x0:x1]
    # a crossing is an EDGE under the words (a dot's rim, a box's side, a band's end), not a smooth change: words
    # printed on a color-gradient meter bar are fine (2026-10-09: the PowerCheck's "100%" on its green-to-white
    # bar was flagged by a deviation-from-the-middle-color test). An edge = neighbouring pixels differing by more
    # than `near`; the box crosses something when its edge pixels add up to a quarter of the letters' height.
    ex = np.abs(np.diff(g, axis=1)).max(-1) > near
    ey = np.abs(np.diff(g, axis=0)).max(-1) > near
    edge = int(ex.sum() + ey.sum())
    share = 1.0 - min(1.0, edge / max(0.25 * (y1 - y0), 1)) * 0.5     # 1 = plain ground; <= 0.5 = an edge under it
    med = np.median(g.reshape(-1, 3), 0)
    return {"ground": round(share, 2), "contrast": round(contrast(color, med), 2)}


def unreadable(placed, least_ground=0.6, least_contrast=2.0):
    """Lines that can't be read clean: half on something else (a dot or a panel edge under them), or ink too close
    to the ground under it (WCAG contrast under 2:1 - the guideline asks 4.5:1 for text; 2 is plainly unreadable)."""
    out = []
    for p in placed:
        if p.get("ground", 1) < least_ground:
            out.append({"text": p["text"], "why": "crosses"})
        elif p.get("contrast", 21) < least_contrast:
            out.append({"text": p["text"], "why": "faint"})
    return out


def off_label(placed, tol=0.005):
    """Lines that run past the label's edge."""
    return [p["text"] for p in placed if p["box"][0] < -tol or p["box"][1] < -tol or p["box"][2] > 1 + tol or p["box"][3] > 1 + tol]


if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1])), sys.argv[2]))
