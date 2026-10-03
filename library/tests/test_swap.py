"""skin._template_face on photo 9 (a 1990s Frosted Assortment 24-pack end panel, a sister box): its item-specific
parts (nutrition panel, item number, count) are covered with the panel's own background and this item's facts drawn
where a fact exists. Run on a made-up face of the same shape (126 x 100 mm) so the shape check passes."""
import json
import os
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
os.environ["CRUSHED_REMASTER_WORK"] = SCR + "/mine_work"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
sys.path.insert(0, SCR)
from PIL import Image  # noqa: E402
import recorded as R  # noqa: E402
import dossier as DS  # noqa: E402
import eraprint  # noqa: E402
import skin  # noqa: E402

dos = DS.load("poptarts_frosted_strawberry_1997")
p9 = next(p for p in dos["photos"] if p["file"].endswith(R.B[9]))
fe = p9["faces"][0]
els = [e for e in p9["elements"] if e["face"] == fe["face"]]
entry = {"photo": p9["file"], "view": fe, "match": "sister",
         "swap_boxes": [{"what": e["what"], "kind": DS.fact_kind(e) or e["kind"], "box": e["box"]}
                        for e in els if e["item_specific"] and e.get("box")]}
print("swap boxes:", [(s["what"], s["kind"]) for s in entry["swap_boxes"]])
front = Image.open(SCR + "/skin_test/front.png").convert("RGB")
c = eraprint.from_dossier(dos)
c["nutrition"] = {"serving": "ONE PASTRY (52 g)", "servings": "6", "calories": 200,     # renderer exercise only
                  "rows": [["Protein", "2 g"], ["Carbohydrate", "37 g"], ["Fat", "5 g"]], "vitamins": []}
c["nutrition_format"] = "pre_nlea"
w, h = skin.canvas(126, 100, mp=1.2e6)
img, swapped, blank = skin._template_face(entry, "left", w, h, (126, 100), c, front, (0.02, 0.03, 0.8, 0.56),
                                          (0.08, 0.63, 0.98, 0.93), {}, print)
print("swapped:", swapped)
print("covered, nothing to draw:", blank)
img.save(SCR + "/skin_test/swap_test.png")
im = Image.open(p9["file"])
b = fe["box"]
im.crop((int(b[0] * im.width), int(b[1] * im.height), int(b[2] * im.width), int(b[3] * im.height))).save(SCR + "/skin_test/swap_before.png")
assert any("nutrition" in s for s in swapped) and any("item number" in s for s in blank)
print("OK")
