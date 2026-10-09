"""Retype: a flat label's printed lines set again as crisp type, spelled as the photos spell them; a line no
photo's words match is left as drawn (never a hole); a line printed twice is printed once."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import retype  # noqa: E402
import measure as MS  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


H, W = 1100, 1000
lab = np.full((H, W, 3), 0.06)
lab[:300] = (0.8, 0.5, 0.25)
# the print runs along the length: drawn across a turned canvas, turned back
canvas = Image.new("RGB", (H, W), (15, 15, 15))
d = ImageDraw.Draw(canvas)
f = retype.face("bold", 40)
d.text((350, 200), "Patented", font=f, fill=(235, 235, 235))
d.text((350, 300), "Bethel, CT 06801", font=f, fill=(235, 235, 235))
d.text((350, 500), "Bethel, CT 06801", font=f, fill=(235, 235, 235))      # printed twice (two views overlap)
d.text((350, 700), "Qwzx Plimbo", font=f, fill=(235, 235, 235))          # no photo carries it
txt = np.asarray(canvas.rotate(-90, expand=True)).astype(float) / 255
lab[300:] = txt[300:H]
MS.read_boxes_full = lambda im, least=0.5: [("Patented", 0.35, 0.19, 0.5, 0.24), ("Bethe1, CT 06801", 0.35, 0.29, 0.62, 0.34),
                                             ("Bethel, CT 06801", 0.35, 0.49, 0.62, 0.54), ("Qwzx Plimbo", 0.35, 0.69, 0.6, 0.74)]
out, notes = retype.retype(lab, ["Patented", "Bethel, CT 06801"], lambda *a: None, scale=2)
check(out.shape[0] == 2 * H and out.shape[1] == 2 * W, f"the label comes back twice the size ({out.shape})")
check(notes["lines"].count("Bethel, CT 06801") == 1 and "Patented" in notes["lines"],
      f"each matched line set again once, spelled as the photos spell it ({notes['lines']})")
check(notes["junk"] == ["Qwzx Plimbo"], f"junk no photo's words come near is painted out ({notes['junk']})")
import retype as RT
cv = RT.canonical(["DURACELL® POWERCHECK™", "DURACELL® POWERCHECK™A", "DURACELLA POWEDCHECKIN", "Test at 70°F/ 21°C",
                   "Test al 70°F/21°C", "BEST IF INSTALLED BY:", "BEST IF INSTALLED RY:", "Patented ."])
check(cv == ["DURACELL® POWERCHECK™", "Test at 70°F/ 21°C", "BEST IF INSTALLED BY:", "Patented"], f"one spelling per line, the best-supported reading ({cv})")
check(RT.snap("DURACELLA POWEDCHECKIN", cv) == "DURACELL® POWERCHECK™" and RT.snap("Zorbex", cv) is None,
      "a misreading is set in the photos' spelling, never its own")
fx = RT.canonical(["TOTEST", "DURAGEL®", "DURACELL INC.,", "DURACELL® POWERCHECK™", "BEST IF INSTALLED RY:"])
check(fx == ["TO TEST", "DURACELL®", "DURACELL INC.,", "DURACELL® POWERCHECK™", "BEST IF INSTALLED BY:"],
      f"misread words put right: split, the common spelling, a confusable letter ({fx})")
check(RT.snap("DURACELLA DAWEnCHECKIN", fx) == "DURACELL® POWERCHECK™", "a long line read badly still names its line")
eb = np.zeros((400, 300, 3)); eb[:120] = (0.8, 0.5, 0.25); eb[:120, :150] *= 0.7; eb[120:] = 0.08
eo = RT.even_bands(eb)
check(np.abs(eo[:100, 20:130].mean((0, 1)) - eo[:100, 170:280].mean((0, 1))).max() < 0.02, "one copper all round: a darker view's copper takes the band's one color")
print(f"ALL {ok} PASS")
