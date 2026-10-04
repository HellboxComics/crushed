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


T = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/judge_t"
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
print(f"\n{ok} checks passed")
