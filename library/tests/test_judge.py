"""The judge's inputs: each side cropped from its photo, the four label turns as a 2x2 grid, unlit + lit pictures."""
import json
import os
import sys

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
import judge  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


import shutil  # noqa: E402
T = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/judge_t"
shutil.rmtree(T, ignore_errors=True)
shutil.rmtree(os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "kept", "judge-side"), ignore_errors=True)
os.makedirs(T, exist_ok=True)
photo = os.path.join(T, "photo.jpg")
im = Image.new("RGB", (1500, 2000), (200, 200, 200))
im.paste((255, 0, 0), (180, 740, 540, 1040))                       # the bottom end sits in this box
im.save(photo)
renders, lit = {}, {}
for n in ("label_0", "label_90", "label_180", "label_270", "top", "bottom"):
    renders[n] = os.path.join(T, n + ".png")
    Image.new("RGB", (800, 800), (10, 10, 10)).save(renders[n])
    lit[n] = os.path.join(T, n + "_lit.png")
    Image.new("RGB", (800, 800), (90, 90, 90)).save(lit[n])

crop = judge._side_crop(photo, [0.12, 0.37, 0.36, 0.52], renders["bottom"], "ref_bottom.png")
c = Image.open(crop)
check(c.width < 600 and c.height < 500 and c.getpixel((c.width // 2, c.height // 2))[0] > 240,
      f"the side's crop (with a margin) is what the judge sees, not the whole photo ({c.size})")
check(judge._side_crop(photo, [0.02, 0.02, 0.98, 0.99], renders["bottom"], "x.png") is None, "a box covering the whole photo is no crop")
grid = Image.open(judge._strip([renders[n] for n in ("label_0", "label_90", "label_180", "label_270")], renders["label_0"]))
check(grid.size == (1600, 1600), f"four turns go in a 2x2 grid ({grid.size})")

asked = []


def fake(use, text, images):
    asked.append((text, list(images)))
    return {"same_layout": True, "all_elements": True, "missing": [], "print_ok": True, "problems": [], "pass": True}


judge._ask = fake
dos = {"faces": {"label": {"source": "exact_photo", "photo": photo, "must_show": []},
                 "bottom": {"source": "exact_photo", "photo": photo, "view": {"box": [0.12, 0.37, 0.36, 0.52]}, "must_show": []},
                 "top": {"source": "rebuilt", "photo": None, "must_show": []}}}
r = judge.sides("t", renders, dos, "brain", "round", product="AA cell", lit=lit)
check(r["pass"] and set(r["faces"]) == {"label", "bottom", "top"}, "every side judged")
bottom_q = [a for a in asked if "its bottom side" in a[0]]
check(len(bottom_q) == 2 and all(len(a[1]) == 3 for a in bottom_q) and
      all(any(os.path.basename(p) == "ref_bottom.png" for p in a[1]) for a in bottom_q),
      "the bottom is judged twice, each time with the unlit side, the lit side and the photo's bottom crop")
check("no light" in bottom_q[0][0] and "studio light" in bottom_q[0][0], "the judge is told which picture is unlit and which is lit")
label_q = [a for a in asked if "its label side" in a[0]]
check(all(any("label_all_turns" in os.path.basename(p) for p in a[1]) for a in label_q), "the label is judged as its 2x2 grid of turns")
top_q = [a for a in asked if "its top side" in a[0]]
check(len(top_q) == 1 and len(top_q[0][1]) == 2 and "There is no real photo" in top_q[0][0], "a side with no photo: one look, unlit + lit, told so")


# the two looks disagree: a third look decides, checking the named problems one by one
seq = {"n": 0}


def flaky(use, text, images):
    asked.append((text, list(images)))
    if text.startswith("[side] ") and "Two careful looks" in text:
        return {"confirmed": [], "not_there": ["copper band misplaced"], "pass": True}
    seq["n"] += 1
    if seq["n"] % 2 == 0:
        return {"same_layout": False, "all_elements": True, "missing": [], "print_ok": True,
                "problems": ["copper band misplaced"], "pass": False}
    return {"same_layout": True, "all_elements": True, "missing": [], "print_ok": True, "problems": [], "pass": True}


judge._ask = flaky
asked.clear()
shutil.rmtree(os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "kept", "judge-side"), ignore_errors=True)
r = judge.sides("t", renders, {"faces": {"bottom": dos["faces"]["bottom"]}}, "brain", "round", product="AA cell", lit=lit)
check(r["pass"] and r["faces"]["bottom"]["looks"] == 3 and r["faces"]["bottom"]["agreed"] is False,
      "one look fails, one passes: a third look finds nothing and the side passes")
check(sum(1 for a in asked if "Two careful looks" in a[0]) == 1 and "copper band misplaced" in
      [a for a in asked if "Two careful looks" in a[0]][0][0], "the third look is asked about the named problems")


def flaky2(use, text, images):
    if "Two careful looks" in text:
        return {"confirmed": ["copper band misplaced: the address block sits on copper in picture 1"], "pass": False}
    return flaky(use, text, images)


judge._ask = flaky2
seq["n"] = 0
shutil.rmtree(os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "kept", "judge-side"), ignore_errors=True)
r = judge.sides("t", renders, {"faces": {"bottom": dos["faces"]["bottom"]}}, "brain", "round", product="AA cell", lit=lit)
check(not r["pass"] and "address block" in r["problems"][0], "a third look that confirms the problem fails the side, naming where")


# a side that passed stays passed while its pictures are the same (within render noise); a changed picture is judged again
shutil.rmtree(os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "kept", "judge-side"), ignore_errors=True)
judge._ask = fake
asked.clear()
d1 = {"faces": {"bottom": dos["faces"]["bottom"]}}
judge.sides("t", renders, d1, "brain", "round", product="AA cell", lit=lit)
n1 = len(asked)
r = judge.sides("t", renders, d1, "brain", "round", product="AA cell", lit=lit)
check(len(asked) == n1 and r["pass"] and r["faces"]["bottom"].get("kept") is True,
      "the same pictures again: the pass is kept, the judge is not asked")
Image.new("RGB", (800, 800), (10, 10, 10)).save(renders["bottom"])
from PIL import ImageDraw
im = Image.open(renders["bottom"]); ImageDraw.Draw(im).text((400, 400), "X", fill=(255, 255, 255)); im.save(renders["bottom"])
r = judge.sides("t", renders, d1, "brain", "round", product="AA cell", lit=lit)
check(len(asked) > n1 and not r["faces"]["bottom"].get("kept"), "a changed picture is judged again")

# the pass is computed from what the look reported, never the brain's own word
check(judge.look_ok({"pass": True, "same_layout": True, "all_elements": True, "print_ok": True, "missing": [],
                     "inventory": [{"element": "white dot", "real_count": 2, "model_count": 2}]}) is True, "a clean look passes")
v = {"pass": True, "same_layout": True, "all_elements": True, "print_ok": True, "missing": [],
     "inventory": [{"element": "white dot", "real_count": 2, "model_count": 1}]}
check(judge.look_ok(v) is False and "white dot: 2 on the real one, 1 on the model" in v["_counts"],
      "a look that says pass but counts 2 dots on the real one and 1 on the model FAILS, naming the count")
check(judge.look_ok({"pass": True, "same_layout": False, "all_elements": True, "print_ok": True, "missing": []}) is False,
      "pass with same_layout false is not a pass")
v = {"pass": True, "same_layout": True, "all_elements": True, "print_ok": True, "missing": [], "extra": ["a code '01' not on the real one"]}
check(judge.look_ok(v) is False and any("not on the real one" in p for p in v["problems"]),
      "something on the model that the real side does not have fails the look and is named")
check('"extra"' in judge.Q and "nothing may be invented" in judge.Q, "the judge is asked for extras")
print(f"\n{ok} checks passed")
