"""The box faces of Pop-Tarts 1997 built from the dossier's plan, through run.py's own wrappers (same_design,
other_sides) and skin.box_skin; then the carton contents file. The model's two box questions (logo, product picture)
are answered from what I measured on the front; the drawing room (cut-outs, sharpening) isn't in this sandbox."""
import json
import os
import shutil
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
os.environ["CRUSHED_REMASTER_WORK"] = SCR + "/mine_work"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
sys.path.insert(0, SCR)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import recorded as R  # noqa: E402
import run  # noqa: E402  (run.py's own wrappers)
import vet  # noqa: E402
import turnaround as T  # noqa: E402
import dossier as DS  # noqa: E402
import eraprint  # noqa: E402
import facts as FX  # noqa: E402
import skin  # noqa: E402


def fake_ask(model, text, images, think=True, side=1280):
    if "brand name and product name lockup" in text:
        return dict(R.LOGO_BOX)
    if "main product picture" in text:
        return dict(R.PHOTO_BOX)
    raise RuntimeError("no recorded answer: " + text[:60])


def no_room(*a, **k):
    raise RuntimeError("the drawing room isn't running in this sandbox")


vet.ask = fake_ask
T.upscale = no_room
T.photo_mask = no_room

CID = "poptarts_frosted_strawberry_1997"
W_ = os.environ["CRUSHED_REMASTER_WORK"]
card = json.load(open(os.path.join(W_, "cards", CID + ".json")))
picked = json.load(open(os.path.join(W_, "library", CID, "candidates.json")))["files"][0]
dos = DS.load(CID)
assert dos and dos.get("done")
# test only: photo 76 is the same picture as the pick at a bigger size - its cut-out is the pick's, scaled
p76 = os.path.join(W_, "hunt", CID, "pbbd9cdcebaba.jpg")
m76 = p76[:-4] + "_mask.png"
if not os.path.exists(m76):
    Image.open(picked["mask"]).convert("L").resize(Image.open(p76).size, Image.LANCZOS).save(m76)

shots = [picked] + run.same_design(picked, [], "qwen", want=5, dossier=dos)
shots += run.other_sides(CID, card, picked, "qwen", have=shots, dossier=dos)
print("photos handed to the box builder:", [(os.path.basename(s["file"]), s.get("plan"), bool(s.get("mask"))) for s in shots])
out = os.path.join(SCR, "skin_test")
shutil.rmtree(out, ignore_errors=True)
W, D, H = card["size"]
era = eraprint.from_dossier(dos)
print("printable facts:", {k: v for k, v in era.items() if k not in ("left_out",)}, "left out:", era["left_out"])
atlas, src = skin.box_skin(card["product"], W, D, H, shots, out, flat=False, judge="qwen", log=print, era=era, dossier=dos)
print(json.dumps(src, indent=1)[:3000])
cj = FX.carton_contents(dos, W, D, H, os.path.join(out, "contents.json"))
print("contents for carton.py:", open(cj).read() if cj else None)
im = Image.open(atlas)
im.thumbnail((1400, 1400))
im.save(os.path.join(SCR, "skin_test", "atlas_small.jpg"), quality=90)
faces = [Image.open(os.path.join(out, f + ".png")).convert("RGB") for f in ("front", "back", "left", "right")]
Hh = 900
row = [f.resize((int(f.width * Hh / f.height), Hh)) for f in faces]
sheet = Image.new("RGB", (sum(r.width for r in row) + 30, Hh), "black")
x = 0
for r in row:
    sheet.paste(r, (x, 0))
    x += r.width + 10
sheet.save(os.path.join(out, "sides.jpg"), quality=90)
tb = [Image.open(os.path.join(out, f + ".png")).convert("RGB") for f in ("top", "bottom")]
sheet2 = Image.new("RGB", (tb[0].width, tb[0].height + tb[1].height + 10), "black")
sheet2.paste(tb[0], (0, 0))
sheet2.paste(tb[1], (0, tb[0].height + 10))
sheet2.save(os.path.join(out, "top_bottom.jpg"), quality=90)
import zxingcpp  # noqa: E402
bt = [(str(b.format), b.text) for b in zxingcpp.read_barcodes(Image.open(os.path.join(out, "bottom.png")),
                                                             formats=zxingcpp.BarcodeFormat.UPCA)]
print("barcode on the built bottom:", bt)
assert bt and bt[0][1][-12:] == "038000317101"
print("OK")
