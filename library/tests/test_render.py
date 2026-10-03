"""eraprint renders from facts: bottom (UPC at GS1 size + legal lines) and left panels; the barcode must decode to
exactly 038000317101; the bold-wrap bug must be gone."""
import os
import sys

import numpy as np
from PIL import Image

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work"
sys.path.insert(0, "/home/claude/crushed/library")
import eraprint
import skin
import zxingcpp

OUT = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/renders"
os.makedirs(OUT, exist_ok=True)
SKIN = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work/library/poptarts_frosted_strawberry_1997/skin"
front = Image.open(os.path.join(SKIN, "front.png")).convert("RGB")
paper = (175, 176, 174)                      # the top flap's neutral paper (see the white-balance note)
logo_box = (0.0, 0.03, 0.80, 0.53)           # where the Kellogg's pop-tarts lockup sits on this front (looked at)

# the facts as the dossier gives them for Pop-Tarts 1997 (UPC verified on 3 sites; legal lines read off the top flap)
c = {"food": True, "name": "Pop-Tarts Frosted Strawberry", "variant": "Frosted Strawberry", "line": "Pop-Tarts",
     "brand": "Kellogg's", "year": 1997, "upc": "038000317101", "net_weight": "NET WT. 14.7 OZ. (416g)",
     "count": "8 TOASTER PASTRIES",
     "legal_lines": ["CARTON MADE FROM 100% RECYCLED PAPER", "MINIMUM 35% POST-CONSUMER CONTENT", "Ctn. No. K-3171C"],
     "maker_lines": ["DISTRIBUTED BY KELLOGG USA INC. BATTLE CREEK, MICH. 49016, U.S.A."]}

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def decode(img):
    """UPC-A only; zxing-cpp 3 reports a UPC-A's text in its 13-digit EAN form (one leading 0 added) - taken off."""
    got = [(str(b.format), b.text) for b in zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.UPCA)]
    print("  zxing raw:", got)
    return [(f, t[1:] if len(t) == 13 and t[0] == "0" else t) for f, t in got]


# --- the bottom: 140 x 50 mm
w, h = skin.canvas(140, 50, mp=1.2e6)
img, used, missing = eraprint.panel_notes("bottom", c, front, logo_box, None, w, h, paper, (140, 50))
img.save(os.path.join(OUT, "bottom.png"))
print("bottom drew", used, "missing", missing)
got = decode(img)
print("  decoded:", got)
check(any(t == "038000317101" for f, t in got), "bottom barcode decodes to exactly 038000317101")
ppm = w / 140
bar = eraprint.upc("038000317101", ppm)
check(abs(bar.width / ppm - 37.29) < 0.3, f"barcode is {bar.width / ppm:.2f} mm wide with quiet zones (GS1 100%: 37.29)")
a = np.asarray(bar.convert("L")) < 128
rows = np.where(a.any(1))[0]
cols = np.where(a[rows.min() + 5])[0]
print(f"  bars start {cols.min() / ppm:.2f} mm in (quiet zone 2.97 mm), bar height ~{(rows.max() - rows.min()) / ppm:.1f} mm")
check(abs(cols.min() / ppm - 2.97) < 0.3, "left quiet zone is 9 modules (2.97 mm)")
bar80 = eraprint.upc("038000317101", ppm, 0.8)
check(any(t == "038000317101" for f, t in decode(bar80)), "the 80% barcode decodes too")
check(eraprint.fit_upc("038000317101", int(20 * ppm), int(20 * ppm), ppm)[0] is None,
      "no room (20 x 20 mm): the barcode is left off, never squeezed below 80%")
try:
    eraprint.upc("038000317102", ppm)
    check(False, "a wrong check digit is never drawn")
except ValueError:
    check(True, "a wrong check digit is never drawn")

# --- the left side: Pop-Tarts 1997 as it is (no nutrition panel from 1994-2000 was found -> none drawn)
w, h = skin.canvas(50, 200, mp=1.2e6)
img, used, missing = eraprint.panel_notes("left", c, front, logo_box, None, w, h, paper, (50, 200))
img.save(os.path.join(OUT, "left_poptarts_1997.png"))
print("left (real Pop-Tarts facts) drew", used, "no fact for", missing)
check("nutrition" in missing and "nutrition" not in used, "no Nutrition Facts drawn when the era's panel wasn't found")
img, used, missing = eraprint.panel_notes("left", c, front, logo_box, None, w, h, paper, (50, 200),
                                          want=["logo", "maker_lines", "legal_lines"])
img.save(os.path.join(OUT, "left_poptarts_1997_maker.png"))
print("left with the twin's other content drew", used)

# --- renderer test only: a real pre-1994 panel read off photo 9 (a 1990s Frosted Cherry 24-pack, a sister box) and the
#     1994 format exercised with Open Food Facts' filed numbers for 038000317101 (2018-2020 data, NOT era data)
pre = {"serving": "ONE PASTRY (52 g)", "servings": "6", "calories": 200,
       "rows": [["Protein", "2 g"], ["Carbohydrate", "37 g"], ["Fat", "5 g"], ["Unsaturated", "4 g"],
                ["Saturated", "1 g"], ["Cholesterol", "0 mg"], ["Sodium", "220 mg"], ["Potassium", "50 mg"]],
       "vitamins": ["Protein 4", "Iron 10", "Vitamin A 10", "Vitamin B6 10", "Vitamin C 0", "Folic Acid 10",
                    "Thiamin 10", "Phosphorus 4", "Riboflavin 10", "Magnesium 2", "Niacin 10", "Zinc 2", "Calcium 0",
                    "Copper 4"]}
check(eraprint.calories_check(pre)["ok"] is True, "photo 9's panel adds up (4x37 + 4x2 + 9x5 = 201 vs 200)")
eraprint.nutrition(pre, 900, "pre_nlea").save(os.path.join(OUT, "nutrition_pre_nlea.png"))
nlea = {"serving": "1 Pastry (52g)", "servings": "8", "calories": 200, "fat_calories": "",
        "rows": [["Total Fat", "5g", "", 0], ["Saturated Fat", "1.5g", "", 1], ["Cholesterol", "0mg", "", 0],
                 ["Sodium", "165mg", "", 0], ["Total Carbohydrate", "38g", "", 0], ["Dietary Fiber", "1g", "", 1],
                 ["Sugars", "16g", "", 1], ["Protein", "2g", "", 0]], "vitamins": []}
for fmt in ("1994_nlea", "2006_trans", "2020_new"):
    eraprint.nutrition(nlea, 900, fmt).save(os.path.join(OUT, f"nutrition_{fmt}.png"))
cn = dict(c, nutrition=pre, nutrition_format="pre_nlea", ingredients="INGREDIENTS: CHERRY FILLING (CORN SYRUP, "
          "DEXTROSE, CHERRIES, CRACKERMEAL, WHEAT STARCH, APPLES, PARTIALLY HYDROGENATED SOYBEAN OIL, CITRIC ACID, "
          "COLOR ADDED, AND NATURAL FLAVORING), ENRICHED WHEAT FLOUR, SUGAR, PARTIALLY HYDROGENATED SOYBEAN OIL")
img, used, missing = eraprint.panel_notes("left", cn, front, logo_box, None, w, h, paper, (50, 200))
img.save(os.path.join(OUT, "left_renderer_test.png"))
check(used[:2] == ["nutrition", "ingredients"], "with a nutrition fact, the left side carries the panel + ingredients")

# --- the bold-wrap bug: bold text must stay inside its width
W = 300
p = eraprint.paragraph("DISTRIBUTED BY KELLOGG USA INC. BATTLE CREEK, MICHIGAN 49016 U.S.A. SUPERCALIFRAGILISTICEXPIALIDOCIOUSWORD",
                       W, px=28, weight="black")
al = np.asarray(p)[..., 3] > 0
xs = np.where(al.any(0))[0]
check(xs.max() < W, f"bold text stays inside the {W}px panel (rightmost ink at {xs.max()}px)")
print(f"\n{ok} checks passed; PNGs in {OUT}")
