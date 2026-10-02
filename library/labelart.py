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
   "texts":  [ {"text": "DURACELL", "x": 0.4, "y": 0.05, "h": 0.12, "color": "#ffffff", "weight": "black",
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
        width = int((s.get("stroke_w") or 0) * H) or (1 if outline else 0)
        if s.get("shade") == "copper" and fill:          # a brushed copper band: soft light along it
            x0, y0, x1, y1 = [int(v) for v in b]
            base = np.array(fill, float)
            for y in range(y0, y1):
                f = (y - y0) / max(y1 - y0, 1)
                k = 0.82 + 0.3 * np.exp(-((f - 0.35) / 0.18) ** 2)
                d.line([(x0, y), (x1, y)], fill=tuple(int(min(255, v * k)) for v in base))
        elif t == "ellipse":
            d.ellipse(b, fill=fill, outline=outline, width=width)
        else:
            d.rectangle(b, fill=fill, outline=outline, width=width)
        if s.get("metal"):
            (dm.ellipse if t == "ellipse" else dm.rectangle)(b, fill=(0, int(255 * s.get("roughness", 0.3)), 255))
    for tx in layout.get("texts", []):
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
        img.paste(Image.new("RGB", layer.size, rgb(tx.get("color", "#000000"))), (int(x), int(tx["y"] * H)), layer)
        if mark:                                    # (R) / TM: small and raised, like real print
            fm = font("bold", hpx * 0.5)
            mx0, my0, mx1, my1 = d.textbbox((0, 0), mark, font=fm)
            d.text((int(x) + layer.width + hpx * 0.04 - mx0, int(tx["y"] * H) - my0), mark, font=fm,
                   fill=rgb(tx.get("color", "#000000")))
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=40, threshold=2))
    c, m = os.path.join(out_dir, name + ".png"), os.path.join(out_dir, name + "_mr.png")
    img.save(c)
    mr.save(m)
    return c, m


if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1])), sys.argv[2]))
