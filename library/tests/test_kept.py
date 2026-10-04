"""Keep what passed: a step's answer is kept by its inputs; rendered pictures match within render noise only."""
import os
import sys

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/kept_work"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import kept  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


import shutil  # noqa: E402
T = os.environ["CRUSHED_REMASTER_WORK"]
shutil.rmtree(T, ignore_errors=True)                       # a fresh store every run
os.makedirs(T, exist_ok=True)
a = os.path.join(T, "a.png")
Image.new("RGB", (300, 200), (120, 120, 120)).save(a)
k1 = kept.key("words", [a], "brain-x")
k2 = kept.key("words", [a], "brain-y")
check(k1 != k2, "a different brain is a different key")
Image.new("RGB", (300, 200), (121, 120, 120)).save(a)
check(kept.key("words", [a], "brain-x") != k1, "a changed picture (one level) is a different key for word reads (bytes)")
check(kept.get("words", k1) is None, "nothing kept yet")
kept.put("words", k1, ["DURACELL", "AA"])
check(kept.get("words", k1) == ["DURACELL", "AA"], "a kept answer comes back")

# rendered pictures: render noise matches, a changed word does not
rng = np.random.default_rng(1)
base = np.full((1024, 1024), 128, np.uint8)
d = Image.fromarray(base)
ImageDraw.Draw(d).text((300, 500), "DURACELL POWERCHECK", fill=255)
r1 = os.path.join(T, "r1.png")
d.save(r1)
noisy = np.clip(np.asarray(d).astype(np.int16) + rng.integers(-2, 3, base.shape), 0, 255).astype(np.uint8)
r2 = os.path.join(T, "r2.png")
Image.fromarray(noisy).save(r2)
d3 = Image.fromarray(base)
ImageDraw.Draw(d3).text((300, 500), "DURACELL POWERCHEEK", fill=255)       # one letter changed
r3 = os.path.join(T, "r3.png")
d3.save(r3)
check(kept.pics_match(kept.pic_sig(r1), kept.pic_sig(r2)), "the same render with sampling noise matches")
check(not kept.pics_match(kept.pic_sig(r1), kept.pic_sig(r3)), "one changed letter in a small word does not match")
kk = kept.key("judge-side", [], "item", "label", "must", "brain", 3)
kept.put_pictures("judge-side", kk, [r1], {"pass": True, "problems": []})
check(kept.get_pictures("judge-side", kk, [r2]) == {"pass": True, "problems": []}, "a kept pass is found for the noisy re-render")
check(kept.get_pictures("judge-side", kk, [r3]) is None, "and not for the changed one")
check(kept.get_pictures("judge-side", kk, [r1, r2]) is None, "a different number of pictures never matches")
print(f"\n{ok} checks passed")
