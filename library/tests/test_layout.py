"""The label your AI writes (layout.py) runs end to end: the prompt fills in (its JSON example intact), the layout is
drawn, compared, improved and drawn at full size - with a stand-in for the brain (no Ollama here)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, "/home/claude/crushed/library")
import layout as LAY
from PIL import Image

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


out = tempfile.mkdtemp()
real = os.path.join(out, "real.png")
Image.new("RGB", (900, 500), (20, 20, 20)).save(real)
asked = []
words = ["DURACELL", "BEST IF INSTALLED BY:", "JAN 2001", "Bethel, CT. 06801"]
first = {"width_mm": 1, "height_mm": 1, "background": "#111111",
         "shapes": [{"type": "rect", "x": 0, "y": 0.8, "w": 1, "h": 0.2, "fill": "#b87333", "metal": True,
                     "shade": "copper"},
                    {"type": "bar", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.05, "colors": ["#ffffff", "#ffcc00"],
                     "stops": [0, 1]}],
         "texts": [{"text": "DURACELL", "x": 0.3, "y": 0.4, "h": 0.2, "w": 0.4, "color": "#ffffff", "weight": "black",
                    "align": "center"},
                   {"text": "JAN 2001", "x": 0.7, "y": 0.1, "h": 0.06, "color": "#ffffff"},
                   {"text": "ALKALINE BATTERY 9000 HOURS", "x": 0.1, "y": 0.6, "h": 0.05}]}


import labelart as _la                                  # the "real" label: what the layout draws (colors match)
_p, _ = _la.render(dict(first, width_mm=50.0, height_mm=46.0), out, px=900, name="real_src")
Image.open(_p).save(real)


def fake(model, text, images, think=True):
    asked.append(text)
    if text.startswith("Picture 1 is a rebuilt label"):
        return {"match": 6 if len(asked) < 4 else 9, "fixes": ["move the logo up"]}
    lay = json.loads(json.dumps(first))
    if "Your layout:" in text:                               # the improved layout: the logo moved up
        lay["texts"][0]["y"] = 0.3
    return lay


LAY._ask = fake
png, mr, score = LAY.make("Duracell PowerCheck AA", real, words, 50.0, 46.0, out, model="stand-in",
                          typical=["the brand logo", "a date code"], log=print)
check('"width_mm": W' in asked[0] and "{product}" not in asked[0], "the first prompt filled in, its JSON example intact")
check("A label like this normally carries: the brand logo; a date code." in asked[0], "the kit's typical contents told")
check(os.path.exists(png) and os.path.exists(mr) and Image.open(png).size[0] >= 4000, "the label drawn at full size")
lay = json.load(open(os.path.join(out, "layout.json")))
check(all(t["text"] != "ALKALINE BATTERY 9000 HOURS" for t in lay["texts"]), "words not on the real label are dropped")
check(score == 9, f"the best round is kept (match {score})")
check(any("move the logo up" in a for a in asked if "Your layout:" in a), "the judge's fixes are given to the writer")
check(any("ONLY the printed sleeve" in a for a in asked[:1]), "the writer is told the metal ends are not the label")
# a layout that comes back unchanged is not drawn again and again
asked.clear()
LAY._ask = lambda m, t, i, think=True: (asked.append(t) or ({"match": 5, "fixes": []} if t.startswith("Picture 1 is a rebuilt")
                                                         else json.loads(json.dumps(first))))
LAY.make("Duracell PowerCheck AA", real, words, 50.0, 46.0, out, model="stand-in", log=print)
check(sum(1 for a in asked if "Your layout:" in a) == 1, "an unchanged layout stops the rounds")
# metal ink covered by plain ink is not metal (2026-10-03: a copper background under a black body made the whole
# Duracell label read as metal, and the materials check failed it)
import labelart
import numpy as np
lay = {"width_mm": 50, "height_mm": 46, "background": "#000000",
       "shapes": [{"type": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "fill": "#b87333", "metal": True, "shade": "copper"},
                  {"type": "rect", "x": 0.3, "y": 0, "w": 0.7, "h": 1, "fill": "#111111"}],
       "texts": [{"text": "DURACELL", "x": 0.02, "y": 0.4, "h": 0.1, "w": 0.25, "color": "#000000"}]}
c, m = labelart.render(lay, out, px=1000, name="metal")
share = (np.asarray(Image.open(m))[..., 2] > 127).mean()
check(0.2 < share < 0.3, f"only the uncovered copper is metal ({share:.0%}); black ink and letters on it are not")
# a line thickness given in mm, and copper ink with no color, still draw what was meant (2026-10-03: "stroke_w": 1.2
# painted the whole Duracell label green; copper with "fill": null drew nothing)
bad = {"width_mm": 50, "height_mm": 46, "background": "#000000",
       "shapes": [{"type": "rect", "x": 0, "y": 0, "w": 0.3, "h": 1, "fill": None, "metal": True, "shade": "copper"},
                  {"type": "rect", "x": 0.4, "y": 0.3, "w": 0.5, "h": 0.2, "fill": "#000000", "stroke": "#1fd43a",
                   "stroke_w": 1.2}], "texts": []}
fixed = LAY.clean_layout(bad, 50, 46, [])
c, m = labelart.render(fixed, out, px=600, name="stroke")
px = np.asarray(Image.open(c).convert("RGB")).astype(int)
green = ((px[..., 1] > 150) & (px[..., 0] < 100)).mean()
copper = ((px[..., 0] > 140) & (px[..., 2] < 90)).mean()
check(green < 0.12 and copper > 0.25, f"a mm line stays a line ({green:.0%} green) and copper ink gets its color ({copper:.0%})")
# words on a panel stay inside it (2026-10-03: "JAN 2001" ran out of the bottom of its tan box)
pan = {"width_mm": 50, "height_mm": 46, "background": "#000000",
       "shapes": [{"type": "rect", "x": 0.5, "y": 0.5, "w": 0.3, "h": 0.1, "fill": "#d99a5b"}],
       "texts": [{"text": "JAN 2001", "x": 0.52, "y": 0.55, "h": 0.12, "w": 0.3, "color": "#ffffff"}]}
c, m = labelart.render(pan, out, px=1000, name="panel")
px = np.asarray(Image.open(c).convert("RGB")).astype(int)
white = (px.min(-1) > 200)
ys, xs = np.where(white)
check(len(ys) and ys.min() >= 0.5 * px.shape[0] and ys.max() <= 0.6 * px.shape[0] and xs.max() <= 0.8 * px.shape[1],
      "words printed on a panel are drawn inside it")
# the measured color check catches a missing copper end the comparison brain called "match 9" (2026-10-03),
# and does not count a photo's light and shade as a different color
real = np.zeros((300, 400, 3), np.uint8)
real[:, :120] = (196, 120, 60)                         # copper end (lit)
real[:150, :120] = (150, 90, 40)                       # (in shade - still copper)
real[:, 120:] = (25, 22, 20)
rp = os.path.join(out, "realc.png")
Image.fromarray(real).save(rp)
blk = os.path.join(out, "black.png")
Image.fromarray(np.full((300, 400, 3), 20, np.uint8)).save(blk)
good = real.copy()
good[:, :120] = (184, 115, 51)
gp = os.path.join(out, "good.png")
Image.fromarray(good).save(gp)
s_bad, f_bad = LAY.color_check(blk, rp)
s_good, f_good = LAY.color_check(gp, rp)
check(s_bad < 0.75 and any("copper on the real label but black" in f for f in f_bad),
      f"a label drawn without its copper end is caught ({s_bad:.0%}): {f_bad[:1]}")
check(s_good > 0.95 and not f_good, f"copper in light and in shade is still copper ({s_good:.0%})")
# a word the photo's edge cut off is printed as the whole word
import run
ww = run.whole_words(["DURACELL®", "JAN 2001", "DURA", "ALKALINE", "ALKALINE BATTERY"])
check("DURA" not in ww and "ALKALINE" in ww, f"'DURA' (cut off at the photo's edge) becomes the whole word: {ww}")
print(f"\n{ok} checks passed")
