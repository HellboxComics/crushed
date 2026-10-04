"""Self-review: every step writes its work and its own checks; the first step that went wrong is found; the exact
checks catch today's label bugs (a word that is a piece, a close-up main photo, a label marked all metal)."""
import os
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, "/home/claude/crushed/library")
import review

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


d = tempfile.mkdtemp()
pic = os.path.join(d, "real.png")
Image.new("RGB", (64, 32)).save(pic)
R = review.Sheet(d)
R.step("unrolled label", files=[pic], checks=[("covers the whole length", True, "100%")])
R.step("words", checks=[("no word is only a piece of another", False, "DURA")])
R.step("label art", checks=[("best try 7+", False, "match 4")])
ff = review.load(d).first_failure()
check(ff and ff["step"] == "words" and ff["detail"] == "DURA", f"the first step that went wrong is found: {ff}")
t = review.load(d).text()
check("FIRST STEP THAT WENT WRONG: words" in t and "real.png" in t, "the sheet in words names it and the pictures")
check(review.pieces(["DURACELL®", "DURA", "JAN 2001", "ALKALINE", "ALKALINE BATTERY"]) == ["DURA"],
      "a piece of a longer word is caught (a whole word is not)")
cov = np.zeros((100, 200))
cov[:45, 90:110] = 1                                   # the main photo shows only 45% of the length
check(abs(review.front_length(cov) - 0.45) < 0.01, "a main photo that shows only part of the length is measured")
mr = os.path.join(d, "mr.png")
a = np.zeros((10, 10, 3), np.uint8)
a[..., 2] = 255
Image.fromarray(a).save(mr)
check(review.metal_share(mr) == 1.0, "a label marked all metal is measured as 100% metal")
src = {"front": {"source": "template"}, "back": {"source": "rebuilt", "no_fact_for": ["nutrition"]},
       "left": {"source": "photo"}, "right": {"source": "plain"}, "top": {"source": "plain"}}
bc = {c: (o, det) for c, o, det in review.box_checks(src)}
check(bc["the front is a real photo of this item"][0] is False, "a box front that is not a real photo of the item is caught")
check(bc["every side is made"] == (False, "bottom"), "a missing side is caught")
check(bc["rebuilt sides carry what this kind normally has"][0] is None and "nutrition" in
      bc["rebuilt sides carry what this kind normally has"][1], "a fact never found is reported, not called broken")

# the parts builder's own checks
plan = {"size_mm": [120, 120, 150], "fixed": [],
        "parts": [{"name": "body", "shape": "sphere", "size_mm": [120, 120, 120], "at_mm": [0, 0, 60]},
                  {"name": "ears", "shape": "rounded_box", "size_mm": [40, 20, 30], "at_mm": [0, 0, 135], "rotate_deg": [0, 30, 0]},
                  {"name": "feet", "shape": "cylinder", "axis": "x", "size_mm": [20, 20, 100], "at_mm": [0, 0, 10]}]}
pc = {c: (o, det) for c, o, det in review.parts_checks(plan, {"parts": 3, "flags": []}, [{"part": "eyes"}, {"part": "body"}])}
check(pc["the planned parts fill the real size (within 10% each way)"][0] is True, "a plan that fills the real size passes")
check(pc["parts that are turned (rotate_deg)"][0] is None and "ears" in pc["parts that are turned (rotate_deg)"][1],
      "a turned part is named, not called wrong")
check(pc["every part of this kind's kit is in the plan"] == (False, "missing: eyes"), "a kit part left out of the plan is caught")
plan["parts"].append({"name": "battery_box", "shape": "rounded_box", "size_mm": [40, 40, 40], "at_mm": [0, 0, 20], "inside": True})
pc = {c: (o, det) for c, o, det in review.parts_checks(plan, {"parts": 4, "flags": []})}
check(pc["every inside part fits within one outer part"] == (True, "1 inside part(s) fit"), "an inside part within the body fits")
plan["parts"][-1]["at_mm"] = [0, 0, 130]
pc = {c: (o, det) for c, o, det in review.parts_checks(plan, {"parts": 4, "flags": []})}
check(pc["every inside part fits within one outer part"][0] is False and "battery_box" in pc["every inside part fits within one outer part"][1],
      "an inside part poking out of every outer part is caught")
plan["parts"].pop()
plan["parts"][0]["size_mm"] = [60, 60, 60]
pc = {c: (o, det) for c, o, det in review.parts_checks(plan, {"parts": 2, "flags": ["feet: could not be built (x)", "body: a rounded stand-in (y)"]})}
check(pc["the planned parts fill the real size (within 10% each way)"][0] is False, "a plan smaller than the real size is caught")
check(pc["every planned part was built"][0] is False and pc["every soft part has its own outline read off the photos (no stand-in, no default egg)"][0] is False,
      "a part Blender could not build and a stand-in are caught")

# a circuit board's own checks
pcbc = {c: (o, det) for c, o, det in review.pcb_checks(
    {"front": {"source": "photo"}, "back": {"source": "plain"}},
    [{"type": "chip", "box": [0.1, 0.1, 0.3, 0.3], "height_mm": 3}, {"type": "capacitor", "box": [0.5, 0.5, 0.55, 0.6], "height_mm": None},
     {"type": "connector", "box": [0.0, 0.0, 0.7, 0.6], "height_mm": 8}],
    [{"part": "memory chips"}, {"part": "chip"}])}
check(pcbc["the top of the board is a real photo of this item"][0] is True, "a board top from a real photo passes")
check(pcbc["the solder side is planned from a photo (this item's or a sister card's)"][0] is False, "a plain solder side is caught")
check(pcbc["every part has a height"][0] is False and pcbc["no part covers more than a third of the board"][0] is False,
      "a part with no height and a part too big are caught")
check(pcbc["every part of this kind's kit was found"][0] is None and "memory" in pcbc["every part of this kind's kit was found"][1],
      "a kit part not found is reported, not called broken")

# words laid over a photo are never label text
by_png = {"side1.png": ["DURACELL", "Remember these?", "JAN 2001"], "item1.png": ["DURACELL", "Remember these?", "100%"],
          "side2.png": ["DURACELL®", "JAN 2001", "MAY EXPLODE OR LEAK.", "photo by retrocollector"]}
src = {"side1.png": "a.jpg", "item1.png": "a.jpg", "side2.png": "b.jpg"}
dos = {"photos": [{"file": "a.jpg", "overlays": [{"what": "caption", "text": "Remember these?", "box": None}]},
                  {"file": "b.jpg", "overlays": []}]}
words = ["DURACELL", "Remember these?", "JAN 2001", "100%", "MAY EXPLODE OR LEAK.", "photo by retrocollector", "+"]
kept, out = review.not_on_item(words, by_png, src, dos)
check(out == ["Remember these?", "photo by retrocollector"], f"a caption the dossier saw laid over the photo, and a credit line, are left out: {out}")
check(kept == ["DURACELL", "JAN 2001", "100%", "MAY EXPLODE OR LEAK.", "+"], "words on the item stay, even ones seen on one photo")
print(f"\n{ok} checks passed")
