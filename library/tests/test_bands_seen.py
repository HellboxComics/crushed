"""The label's background bands are measured wherever a photo SAW the label - seen means weight > 0.05, the same
definition the rest of the pipeline uses (2026-10-05 19:22: the Duracell's strip had weights of 0.2 - a quality
score, not a yes/no - the measurer counted only > 0.5, saw nothing, returned no bands in silence, and the writer
painted the copper end black). Checked on that build's own real.png when it is at hand, and on a drawn one."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import layout as L  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


W = tempfile.mkdtemp()
H, Wd = 400, 900
a = np.zeros((H, Wd, 3), np.uint8)
a[:, :int(0.38 * Wd)] = (200, 125, 70)          # copper end
a[:, int(0.38 * Wd):] = (18, 18, 18)            # black body
real = os.path.join(W, "real.png"); Image.fromarray(a).save(real)
cov = np.zeros((H, Wd), np.uint8)
cov[int(0.3 * H):int(0.65 * H)] = int(0.2 * 255)     # a strip seen at weight 0.2 across a third of the way around
seen = os.path.join(W, "real_seen.png"); Image.fromarray(cov).save(seen)
bands, axis = L.base_bands(real, seen)
check(axis == "x" and len(bands) == 2, f"two bands along the label are measured from a strip of weight 0.2 ({axis}, {len(bands)})")
check(bands and bands[0].get("metal") and abs(bands[0]["w"] - 0.38) < 0.03, f"the first is the copper end, 38% of the length ({bands[0].get('w') if bands else None})")
check(bands and bands[1]["fill"].lower() in ("#121212", "#131313", "#111111", "#141414", "#101010", "#0f0f0f") or (bands and int(bands[1]["fill"][1:3], 16) < 40),
      f"the second is the black body ({bands[1]['fill'] if len(bands) > 1 else None})")
cov0 = np.zeros((H, Wd), np.uint8); cov0[int(0.3 * H):int(0.65 * H)] = int(0.03 * 255)
seen0 = os.path.join(W, "real_seen0.png"); Image.fromarray(cov0).save(seen0)
b0, ax0 = L.base_bands(real, seen0)
check(not b0, "a weight under 0.05 is not seen (nothing is measured from it)")

# the build's own pictures, when they are at hand (the cloud session stages them here)
D = "/mnt/user-data/uploads/crushed-render/remaster/library/duracell_coppertop_aa_1998/texture"
if os.path.exists(os.path.join(D, "real.png")) and os.path.exists(os.path.join(D, "real_seen.png")):
    b, ax = L.base_bands(os.path.join(D, "real.png"), os.path.join(D, "real_seen.png"))
    print("the build's bands:", ax, [(round(s["x"], 2), round(s["w"], 2), s["fill"], s.get("shade")) for s in b])
    check(ax == "x" and len(b) >= 2 and b[0].get("metal"), "the Duracell's own reference measures a copper band first, then black")
print(f"ALL {ok} PASS")
