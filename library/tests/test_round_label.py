"""The whole round-label path end to end (run.round_label), with stand-ins for your AI's brain and the text reader:
photos unrolled, words read and confirmed, the real photo made the texture (2026-10-05: nothing redrawn), every step on the review sheet.
(2026-10-03: this path had never run in a test - a broken prompt reached the Mac.)"""
import json
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

W_ = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W_
sys.path.insert(0, "/home/claude/crushed/library")
import run
import vet
import measure
import layout

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


d = os.path.join(W_, "build")
tex = os.path.join(d, "texture")
os.makedirs(tex)
# a battery photo: plus end at the left, copper third, black body with white print
im = Image.new("RGB", (1400, 900), (235, 235, 235))
mk = Image.new("L", im.size, 0)
dr, dm = ImageDraw.Draw(im), ImageDraw.Draw(mk)
x0, y0, L, H = 150, 300, 1100, 316
dr.rectangle([x0, y0, x0 + 0.3 * L, y0 + H], fill=(190, 110, 50))
dr.rectangle([x0 + 0.3 * L, y0, x0 + L, y0 + H], fill=(20, 20, 20))
dr.text((x0 + 0.4 * L, y0 + H / 2), "DURACELL", fill=(255, 255, 255))
dm.rectangle([x0, y0, x0 + L, y0 + H], fill=255)
a = np.asarray(im).astype(float) + np.random.default_rng(2).normal(0, 15, (900, 1400))[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(W_, "p.png"))
mk.save(os.path.join(W_, "p_mask.png"))
picked = {"file": os.path.join(W_, "p.png"), "mask": os.path.join(W_, "p_mask.png"), "vet": {"count": 1}}

asked = []


def fake_ask(model, q, images, think=False, side=None, **k):
    asked.append(q)
    if "unrolling the printed label" in q:
        return {"problems": [], "ok": True}
    if "Read every word" in q:
        return {"words": ["DURACELL", "DURA"]}
    if "again, slowly" in q:
        return {"lines": ["DURACELL", "DURA"]}
    return {}


vet.ask = fake_ask
measure.read_lines = lambda png, **k: ["DURACELL"]
lay = {"width_mm": 1, "height_mm": 1, "background": "#141414",
       "shapes": [{"type": "rect", "x": 0, "y": 0, "w": 0.3, "h": 1, "fill": "#b87333", "metal": True, "shade": "copper"}],
       "texts": [{"text": "DURACELL", "x": 0.42, "y": 0.47, "h": 0.03, "w": 0.06, "color": "#ffffff"}]}
layout._ask = lambda m, t, i, think=True: ({"match": 8, "fixes": []} if t.startswith("Picture 1 is a rebuilt")
                                          else json.loads(json.dumps(lay)))
run.same_design = lambda *a, **k: []
run.make_room = lambda *a, **k: None
run.status = lambda *a, **k: None
png, mr = run.round_label("t", "Duracell AA", picked, [], "stand-in", {}, d, tex, 48.0, np.pi * 14.5, "along",
                          48.0, np.pi * 14.5, "cylindrical_cell")
check(os.path.exists(png) and os.path.exists(mr), "the label and its metal map are drawn")
rv = json.load(open(os.path.join(d, "review.json")))["steps"]
names = [s["step"].split(" (")[0] for s in rv]
check(names == ["unrolled label", "what every label of this kind carries", "words on the label", "the whole label drawn from every photo", "label texture"], f"every step is on the review sheet: {names}")
lt = rv[4]["checks"]
check(all(c["ok"] is not False for c in lt), f"the label texture's own checks (the real photo, nothing redrawn): {[(c['check'][:30], c['ok'], c['detail'][:40]) for c in lt]}")
w = [c for s in rv for c in s["checks"] if c["check"].startswith("no word")][0]
check(w["ok"] is True, "the cut-off 'DURA' never reached the label (printed as the whole word)")
art = rv[2]["checks"]
check(all(c["ok"] is not False for c in art), f"the label art's own checks: {[(c['check'][:30], c['ok'], c['detail']) for c in art]}")
check(not any("unrolling the printed label" in q for q in asked), "streamlined: no separate judge call on the unrolled label (the finished model is judged)")
print(f"\n{ok} checks passed")
