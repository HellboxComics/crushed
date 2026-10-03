"""Round labels from several photos: a photo that shows only PART of the length (a close-up of one end) covers only
that part of the label, at the end it shows - never stretched over the whole length (2026-10-03: a close-up of a
Duracell's plus end was stretched over the whole label and the AI drew from that)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "/home/claude/crushed/library")
import skin

T = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/compose_t"
ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


L_MM, D_MM = 48.0, 14.5                       # the label's length and the item's diameter


def battery(name, scale, x0, body, size=(1400, 1100)):
    """A battery lying on its side: plus end at the left; body = colors along its length (fractions)."""
    im = Image.new("RGB", size, (235, 235, 235))
    mk = Image.new("L", size, 0)
    d, dm = ImageDraw.Draw(im), ImageDraw.Draw(mk)
    h = int(D_MM * scale)
    w = int(L_MM * scale)
    y0 = size[1] // 2 - h // 2
    for (a, b, col) in body:
        d.rectangle([x0 + a * w, y0, x0 + b * w, y0 + h], fill=col)
    dm.rectangle([x0, y0, x0 + w, y0 + h], fill=255)
    a = np.asarray(im).astype(float)                       # fine print texture, as a real photo has (sharpness)
    rng = np.random.default_rng(1)
    a += rng.normal(0, 18, a.shape[:2])[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    f = os.path.join(T, name + ".png")
    im.save(f)
    mk.save(os.path.join(T, name + "_mask.png"))
    return {"file": f, "mask": os.path.join(T, name + "_mask.png"), "vet": {"count": 1}}


front = [(0, 0.3, (190, 110, 50)), (0.3, 1.0, (20, 20, 20))]                 # copper end, black body
full = battery("full", 20, 220, front)                                        # all 48 mm in the picture
back = [(0, 0.3, (190, 110, 50)), (0.3, 1.0, (30, 160, 40))]                  # its other side: green body
close = battery("close", 60, 60, back)                                        # 3x closer: only the plus end shows
lab, cov = skin.compose([full, close], L_MM, np.pi * D_MM, W=1024)
H, W = cov.shape
backcols = slice(W // 2 - 300, W // 2 + 300)
backcols = np.r_[0:200, W - 200:W]                                            # the back = the label's two edges
rows_seen = np.where(cov[:, backcols].max(1) > 0.05)[0]
print("close-up covers rows", rows_seen.min() if len(rows_seen) else None, "-", rows_seen.max() if len(rows_seen) else None, "of", H)
check(len(rows_seen) and rows_seen.min() == 0, "the close-up starts at the plus end (the end it shows)")
frac = (rows_seen.max() + 1) / H
check(0.3 < frac < 0.5, f"and covers only the part of the length it shows ({frac:.0%}), not the whole label")
mid = lab[int(0.15 * H), backcols].mean(0) * 255
check(mid[0] > 150 and mid[2] < 100, f"its copper is at the copper end on the back ({mid.round()})")
far = lab[int(0.9 * H), backcols]
check(cov[int(0.9 * H), backcols].max() < 0.05, "past the close-up the back is left unseen (filled later from the bands)")
front_rows = cov[:, W // 2]
check(front_rows.min() > 0.05, "the full photo covers the whole length at the front")
# a close-up of the OTHER end (the frame cuts the plus end off): it goes at the bottom end
close2 = battery("close2", 60, 1400 - 60 - int(L_MM * 60), back)
lab2, cov2 = skin.compose([full, close2], L_MM, np.pi * D_MM, W=1024)
rows2 = np.where(cov2[:, backcols].max(1) > 0.05)[0]
check(len(rows2) and rows2.max() == H - 1 and rows2.min() > 0.4 * H,
      f"a close-up of the bottom end covers the bottom part only (rows {rows2.min() if len(rows2) else None}-{rows2.max() if len(rows2) else None})")
print(f"\n{ok} checks passed")
