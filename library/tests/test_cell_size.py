"""A cell of another SIZE in the same artwork lends the label nothing, and the same photo saved twice counts once
(2026-10-06 12:25: the label's "front" was a D cell - the careful look called it exact because the artwork matched -
and two of six sources were the same picture). Measured: length to width by the cut-out's principal axes."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import skin  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def rect(L, D, ang, size=500):
    yy, xx = np.mgrid[0:size, 0:size] - size / 2.0
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    u, v = xx * c + yy * s, -xx * s + yy * c
    return ((abs(u) < L / 2) & (abs(v) < D / 2)).astype(float)


aa = 50.5 / 14.5
check(abs(skin.shape_ratio(rect(350, 100, 0)) - 3.5) < 0.1, "an AA lying flat measures 3.5 to 1")
check(abs(skin.shape_ratio(rect(350, 100, 37)) - 3.5) < 0.1, "and the same lying at an angle in the photo")
check(abs(skin.shape_ratio(rect(180, 100, 10)) - 1.8) < 0.1, "a D cell measures 1.8 to 1")
check(not (0.6 * aa <= skin.shape_ratio(rect(180, 100, 10)) <= 1.5 * aa), "a D cell is outside an AA's band")
check(0.6 * aa <= skin.shape_ratio(rect(250, 100, 0)) <= 1.5 * aa, "an AA seen foreshortened (2.5 to 1) is still inside")
check(skin.shape_ratio(np.zeros((50, 50))) is None, "an empty cut-out has no ratio")

# in compose: a D-cell photo and a duplicate are left out, said so
d = tempfile.mkdtemp()
said = []


def photo(name, L, D, color):
    im = np.zeros((500, 500, 3), np.uint8)
    m = rect(L, D, 0)
    im[m > 0.5] = color
    im[200:230, 200:300] = (255, 255, 255)
    f = os.path.join(d, name + ".png")
    Image.fromarray(im).save(f)
    mf = os.path.join(d, name + "_mask.png")
    Image.fromarray((m * 255).astype(np.uint8)).save(mf)
    return {"file": f, "mask": mf}


dcell = photo("dcell", 180, 100, (40, 40, 40))
aa1 = photo("aa1", 350, 100, (40, 40, 40))
aa1_copy = {"file": aa1["file"], "mask": aa1["mask"]}
try:
    skin.compose([dcell, aa1, aa1_copy], 50.5, np.pi * 14.5, W=512, log=said.append)
except Exception as e:
    said.append(f"compose raised {e}")
check(any("dcell" in x and "another size" in x for x in said), f"the D-cell photo is left out as another size: {[x for x in said if 'dcell' in x][:1]}")
check(any("same photo" in x for x in said), "the second copy of the same photo is counted once")
print(f"ALL {ok} PASS")
