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
print(f"\n{ok} checks passed")
