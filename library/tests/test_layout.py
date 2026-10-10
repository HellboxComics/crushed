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
                   {"text": "JAN 2001", "x": 0.5, "y": 0.1, "h": 0.06, "color": "#ffffff"},
                   {"text": "ALKALINE BATTERY 9000 HOURS", "x": 0.1, "y": 0.6, "h": 0.05}]}


import labelart as _la                                  # the "real" label: what the layout draws (colors match)
_p, _ = _la.render(dict(first, width_mm=50.0, height_mm=46.0), out, px=900, name="real_src")
Image.open(_p).save(real)


def fake(model, text, images, think=True):
    asked.append(text)
    if text.startswith("Picture 1 is flat printed artwork"):
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
check(sum(1 for a in asked if "Your layout:" in a) >= 2, "a 9 with fixes still listed is not done: another round is asked for")
check(any("move the logo up" in a for a in asked if "Your layout:" in a), "the judge's fixes are given to the writer")
check(any("ONLY the printed label" in a and "unprinted parts" in a for a in asked[:1]), "the writer is told the item's unprinted parts are not the label")
# lines printed on top of each other are measured where they landed (rotated lines too) and never pass as good
import labelart as LA
ov = {"width_mm": 50, "height_mm": 46, "background": "#111111",
      "texts": [{"text": "ALKALINE 1.5 Volts", "x": 0.5, "y": 0.4, "h": 0.08, "color": "#ffffff"},
                {"text": "MN1500 LR6", "x": 0.52, "y": 0.42, "h": 0.08, "color": "#ffffff"},
                {"text": "SIZE AA", "x": 0.1, "y": 0.1, "h": 0.06, "color": "#ffffff", "rotate": 90},
                {"text": "CAUTION", "x": 0.1, "y": 0.12, "h": 0.06, "color": "#ffffff", "rotate": 90},
                {"text": "EDGE", "x": 0.95, "y": 0.8, "h": 0.06, "color": "#ffffff"}]}
LA.render(ov, out, px=1024, name="ov")
bx = json.load(open(os.path.join(out, "ov_boxes.json")))
pairs = {tuple(sorted((o["a"], o["b"]))) for o in bx["overlaps"]}
check(("ALKALINE 1.5 Volts", "MN1500 LR6") in pairs or ("MN1500 LR6", "ALKALINE 1.5 Volts") in pairs,
      f"two lines printed over each other are measured: {bx['overlaps'][:2]}")
check(any("SIZE AA" in p and "CAUTION" in p for p in pairs), "rotated lines over each other are measured too")
check("EDGE" in bx["off_label"], "a line running off the label is named")
# a layout that comes back unchanged is not drawn again and again
asked.clear()
LAY._ask = lambda m, t, i, think=True: (asked.append(t) or ({"match": 5, "fixes": []} if t.startswith("Picture 1 is flat printed artwork")
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
# a small mark (a white test dot) on the real label that the drawn one lacks is named with its place and size
dot = real.copy()
dot[200:240, 40:80] = (245, 245, 245)                  # a ~10% x 13% white dot on the copper end
dp = os.path.join(out, "dot.png")
Image.fromarray(dot).save(dp)
s_dot, f_dot = LAY.color_check(gp, dp)
check(any("small mark" in f and "white" in f and "copper in yours" in f for f in f_dot),
      f"a missing small white dot is flagged with its place: {[f for f in f_dot if 'small mark' in f][:1]}")
s_rev, f_rev = LAY.color_check(dp, gp)
check(any("small mark" in f and "copper on the real label but white" in f for f in f_rev), "and a dot drawn where there is none")
# the background bands are measured, not guessed: a layout the AI wrote all black keeps the measured copper band
bb, axis = LAY.base_bands(rp)
check(axis == "x" and len(bb) == 2 and bb[0].get("metal") and bb[0]["w"] < 0.35 and not bb[1].get("metal"),
      f"copper end then black body measured along the label: {[(b['x'], b['w'], b['fill']) for b in bb]}")
blk_lay = {"width_mm": 1, "height_mm": 1, "background": "#000000",
           "shapes": [{"type": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "fill": "#000000"}], "texts": []}
fixed = LAY.clean_layout(blk_lay, 50, 46, [], bb)
check(fixed["shapes"][0].get("base") and fixed["shapes"][0].get("metal") and len(fixed["shapes"]) == 2,
      "the AI's all-black band is dropped and the measured bands come first")
# a word the photo's edge cut off is printed as the whole word
import run
ww = run.whole_words(["DURACELL®", "JAN 2001", "DURA", "ALKALINE", "ALKALINE BATTERY"])
check("DURA" not in ww and "ALKALINE" in ww, f"'DURA' (cut off at the photo's edge) becomes the whole word: {ww}")
# the measured can-it-be-read check (2026-10-09: "PRESS DOTS" dark on a black box, a white dot under "Made in U.S.A.")
import labelart as LA
rl = {"width_mm": 50.0, "height_mm": 46.0, "background": "#c87533",
      "shapes": [{"type": "rect", "x": 0.1, "y": 0.1, "w": 0.5, "h": 0.15, "fill": "#1a1a1a"},
                 {"type": "ellipse", "x": 0.2, "y": 0.5, "w": 0.1, "h": 0.1, "fill": "#ffffff"},
                 {"type": "arrow", "x": 0.7, "y": 0.1, "w": 0.1, "h": 0.06, "fill": "#1a1a1a", "dir": "up"}],
      "texts": [{"text": "PRESS DOTS", "x": 0.12, "y": 0.13, "h": 0.06, "color": "#3a2410"},
                {"text": "Made in U.S.A.", "x": 0.05, "y": 0.52, "h": 0.05, "color": "#3a2410"},
                {"text": "TO TEST", "x": 0.12, "y": 0.8, "h": 0.06, "color": "#3a2410"},
                {"text": "100%", "x": 0.42, "y": 0.69, "h": 0.04, "color": "#000000"}]}
rl["shapes"].append({"type": "bar", "x": 0.37, "y": 0.68, "w": 0.53, "h": 0.07, "colors": ["#00cc00", "#ffffff", "#ff0000"],
                     "stops": [0, 0.75, 1]})        # words on a gradient meter bar are on plain ground
LA.render(rl, out, px=1000, name="legible")
ub = {u["text"]: u["why"] for u in json.load(open(os.path.join(out, "legible_boxes.json")))["unreadable"]}
check(ub == {"PRESS DOTS": "faint", "Made in U.S.A.": "crosses"}, f"dark-on-black and a dot under words are measured: {ub}")
check(1.0 <= LA.contrast((0, 0, 0), (0, 0, 0)) < 1.01 and LA.contrast((0, 0, 0), (255, 255, 255)) > 20.9,
      "WCAG contrast: same color 1, black on white 21")
apx = Image.open(os.path.join(out, "legible.png")).convert("RGB").load()
check(apx[750, 100][0] < 60 and apx[750, 140][0] < 60 and apx[712, 140][0] > 150 and apx[712, 96][0] > 150, "an arrow is drawn, pointing up (head at the top)")
check(LAY.neutral("#191e0d") == "#1b1b1b" and LAY.neutral("#f0e8d0") == "#e8e8e8",
      f"a photo's tint on black and white ink is taken out ({LAY.neutral('#191e0d')}, {LAY.neutral('#f0e8d0')})")
check(LAY.neutral("#102a5c") == "#102a5c" and LAY.neutral("#c87533") == "#c87533" and LAY.neutral("#f3e0b0") == "#f3e0b0",
      "navy, copper and cream are real colors and kept")

# a layout sent back unchanged while fixes are listed is asked again (numbered, warmer), not taken as done
calls = []
_orig_ask = LAY._ask
def stall_ask(model, text, images, think=True, temp=0.2):
    calls.append((text[:40], temp))
    if text.startswith("Picture 1 is the real printed label"):
        return json.loads(json.dumps(first))
    if "Answer ONLY JSON:" in text and '"match"' in text:
        return {"match": 7, "fixes": ["add a white dot"]}
    if "You sent this layout back unchanged" in text:
        lay2 = json.loads(json.dumps(first)); lay2["shapes"].append({"type": "ellipse", "x": 0.1, "y": 0.1, "w": 0.05, "h": 0.05, "fill": "#ffffff"})
        return lay2
    return json.loads(json.dumps(first))
LAY._ask = stall_ask
_sd = tempfile.mkdtemp()
LAY.make("Duracell AA", real, words, 50.0, 46.0, _sd, rounds=3, log=lambda *a: None)
_r2 = json.load(open(os.path.join(_sd, "round2.json")))
check(any(t == 0.6 for _, t in calls) and any(sh.get("type") == "ellipse" and sh.get("fill") == "#ffffff" for sh in _r2["shapes"]),
      f"an unchanged layout with fixes listed is asked again, and the new answer is drawn ({[t for _, t in calls]})")
check(os.path.exists(os.path.join(_sd, "defects.json")) and "hard" in json.load(open(os.path.join(_sd, "defects.json"))),
      "the kept round's measured faults are written for the build (defects.json)")
LAY._ask = _orig_ask

# at the same capped score, the round with fewer measured faults is kept (not the one that merely looked better)
_over = json.loads(json.dumps(first)); _over["texts"] = [{"text": "DURACELL", "x": 0.3, "y": 0.4, "h": 0.2, "w": 0.4, "color": "#ffffff"},
                                                       {"text": "JAN 2001", "x": 0.32, "y": 0.42, "h": 0.15, "color": "#ffffff"}]
_clean = json.loads(json.dumps(first)); _clean["texts"] = [{"text": "DURACELL", "x": 0.3, "y": 0.4, "h": 0.2, "w": 0.4, "color": "#ffffff"},
                                                         {"text": "JAN 2001", "x": 0.5, "y": 0.1, "h": 0.06, "color": "#ffffff"}]
_seq = {"n": 0}
def rank_ask(model, text, images, think=True, temp=0.2):
    if text.startswith("Picture 1 is the real printed label"):
        return json.loads(json.dumps(_over))
    if "Answer ONLY JSON:" in text and '"match"' in text:
        _seq["n"] += 1
        return {"match": 9 if _seq["n"] == 1 else 6, "fixes": ["x"]}
    return json.loads(json.dumps(_clean))
LAY._ask = rank_ask
_rd = tempfile.mkdtemp()
LAY.make("Duracell AA", real, words, 50.0, 46.0, _rd, rounds=2, log=lambda *a: None)
_kept = json.load(open(os.path.join(_rd, "layout.json")))
_d = json.load(open(os.path.join(_rd, "defects.json")))
check(any(t["text"] == "JAN 2001" and abs(t["y"] - 0.1) < 0.01 for t in _kept["texts"]) and not _d["hard"],
      f"same capped score: the round without text on text is kept (faults: {_d['hard']})")
LAY._ask = _orig_ask

# the color fixes on the typed words are noise (letters a hair off the photo's); the rest are shown close up
_fx = ["a small mark at x 0.30, y 0.40 (about 0.04 wide, 0.04 tall) is black on the real label but white in yours",
       "a small mark at x 0.80, y 0.85 (about 0.04 wide, 0.04 tall) is brown on the real label but black in yours"]
_pl = [{"text": "DURACELL", "box": [0.2, 0.3, 0.6, 0.5]}]
check(LAY.off_text(_fx, _pl) == [_fx[1]], "a mark on the typed words is dropped; one off them is kept")
_rp = os.path.join(out, "real.png")
_dsp = LAY.diff_sheet(_rp, _rp, _fx, os.path.join(out, "diff_t.png"))
check(_dsp and Image.open(_dsp).height > 2 * 260, "the differences are shown close up, one numbered row each")
_seen_pics = []
def diff_ask(model, text, images, think=True, temp=0.2):
    if text.startswith("Picture 1 is the real printed label"):
        return json.loads(json.dumps(first))
    if "Answer ONLY JSON:" in text and '"match"' in text:
        return {"match": 8, "fixes": []}
    _seen_pics.append((len(images), "Picture 3 shows the measured differences" in text))
    return json.loads(json.dumps(first))
LAY._ask = diff_ask
_cc = LAY.color_check
LAY.color_check = lambda *a, **k: (0.95, list(_fx))
LAY.make("Duracell AA", _rp, words, 50.0, 46.0, tempfile.mkdtemp(), rounds=2, log=lambda *a: None)
LAY.color_check = _cc
LAY._ask = _orig_ask
check(_seen_pics and _seen_pics[0] == (3, True), f"the fix round gets the close-ups as picture 3 ({_seen_pics})")
# a (R) in a line is set small and raised
import labelart as _LA
_f = _LA.font("black", 200); _fm = _LA.font("black", 84)
_l1 = _LA.text_layer("DURACELL", _f, _fm); _l2 = _LA.text_layer("DURACELL®", _f, _fm)
import numpy as _np
_a2 = _np.asarray(_l2); _tail = _a2[:, _l1.width + 4:]
_ys = _np.where(_tail.max(1) > 128)[0]
check(len(_ys) and (_ys.max() - _ys.min()) < 0.6 * _l1.height, f"the (R) is small, not as tall as the letters ({_ys.max() - _ys.min() if len(_ys) else 0} vs {_l1.height})")

print(f"\n{ok} checks passed")
