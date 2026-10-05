"""The label's pixels come from the cleanest exact photo, never from the pick by right (2026-10-05: the pick showed
three cells crossing under a caption; it was forced as the label's source and the model came out wearing the
caption in letters a third of the label tall). The pick is the identity. Proven on records and on a drawn photo."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import dossier as DS  # noqa: E402
import facts as FX  # noqa: E402
import skin  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


# 1. overlay words: a misread of the caption is still the caption
p = {"overlays": [{"what": "title text", "text": "Remember these?", "box": [0.42, 0.05, 0.9, 0.5]}], "panel": {"overlay_text": []}}
ow = FX._overlay_words(p)
check(FX._on_overlay("kemember", ow) and FX._on_overlay("Rememher these", ow), "a letter-off misread of an overlay word is the overlay")
check(not FX._on_overlay("DURACELL", ow) and not FX._on_overlay("ALKALINE BATTERY", ow) and not FX._on_overlay("MN 1500 LR6", ow),
      "label words are not")

# 2. the plan: the pick (3 cells, caption) vs a clean single-cell straight-on exact photo
os.makedirs(os.path.join(W, "p"))
files = {}
for n in ("pick", "clean", "angled"):
    f = os.path.join(W, "p", n + ".jpg")
    Image.new("RGB", (800, 600), (60, 60, 60)).save(f)
    files[n] = f
era = [1995, 1999]


def photo(f, items, straight, overlays, q, match="exact"):
    return {"file": f, "labeled": True, "match": match, "same_artwork": True, "product_shown": "X AA cell", "years": era,
            "quality": q, "items": items, "overlays": overlays, "elements": [], "text": [], "size": [800, 600],
            "faces": [{"face": "label", "box": [0.1, 0.2, 0.9, 0.8], "straight_on": straight, "edge_on": False, "turn": 0}],
            "face": "label", "also": [], "kind": "photo", "quick": {"same_item": True, "same_line": True, "kind": "photo", "years": era, "useful": 9}}


def dossier_with(photos):
    return {"route": "round", "picked": files["pick"], "identity": {"name": "X AA", "years": era, "year": 1998},
            "photos": photos, "faces": {}, "gaps": [], "searches": [], "family_lib": "cylindrical_cell", "facts": {}}


pick = photo(files["pick"], 3, True, [{"what": "title text", "text": "Remember these?", "box": [0.42, 0.05, 0.9, 0.5]}], 7)
clean = photo(files["clean"], 1, True, [], 6)
angled = photo(files["angled"], 1, False, [], 8)
dos = dossier_with([pick, clean, angled])
faces, gaps = DS.plan(dos)
check(faces["label"]["photo"] == files["clean"], f"the clean single straight-on photo is the label's source, not the pick ({os.path.basename(faces['label']['photo'])})")
check(any("3 of the item" in g for g in gaps) and faces["label"]["note"].startswith("the cleanest exact photo"),
      "the pick's shortcomings are written as gaps; the note says the pick is the identity")
check(faces["label"]["view"].get("box") == [0.1, 0.2, 0.9, 0.8], "the source's label box is kept for the unroll")
dos2 = dossier_with([photo(files["pick"], 1, True, [], 7), clean])
faces2, _ = DS.plan(dos2)
check(faces2["label"]["photo"] == files["pick"], "a clean pick wins the tie (its quality is higher)")
dos3 = dossier_with([pick])
faces3, gaps3 = DS.plan(dos3)
check(faces3["label"]["photo"] == files["pick"] and DS._poor_source(dos3 | {"faces": faces3}, "label"),
      f"with no other exact photo the pick is used and called poor: {DS._poor_source(dos3 | {'faces': faces3}, 'label')}")

# 3. label_views carries box, overlays and the count; the pick is only there when it is a source
dos["faces"] = faces
views = DS.label_views(dos, {"file": files["pick"]})
check(views and views[0]["file"] == files["clean"] and views[0]["box"] == [0.1, 0.2, 0.9, 0.8] and views[0]["items"] == 1,
      "label_views: the clean photo first, with its box and count")
pv = next((v for v in views if v["file"] == files["pick"]), None)
check(pv is None or (pv["overlays"] == [[0.42, 0.05, 0.9, 0.5]] and pv["items"] == 3),
      "the pick, if listed as an alternate, carries its overlay box and its count")

# 4. the unroll takes the box and masks the overlay: a drawn photo with the item in a box and a caption above it
f = os.path.join(W, "p", "drawn.png")
m = os.path.join(W, "p", "drawn_mask.png")
im = np.zeros((600, 800, 3), np.uint8)
mk = np.zeros((600, 800), np.uint8)
im[300:560, 100:700] = (200, 120, 40)                 # the item (a lying cell)
mk[300:560, 100:700] = 255
im[40:200, 350:750] = (255, 255, 255)                 # a caption laid over the top (white block)
mk[40:200, 350:750] = 255                             # the cut-out wrongly kept it (it touched nothing but was 'bright')
Image.fromarray(im).save(f)
Image.fromarray(mk).save(m)
parts = skin.all_items({"file": f, "mask": m, "box": [0.1, 0.45, 0.9, 0.95], "overlays": [[0.42, 0.05, 0.95, 0.35]], "items": 1})
check(len(parts) == 1, f"one item comes out of the boxed, overlay-masked photo ({len(parts)})")
crop, cm = parts[0]
a = np.asarray(crop)
check(cm.shape[0] <= 300 and not (np.all(a[cm > 0.5] > 240, axis=-1)).any(),
      "the piece is the item's region only: no caption pixels, nothing above the box")
parts0 = skin.all_items({"file": f, "mask": m})
check(any(pm.shape[0] > 300 for _, pm in parts0) or len(parts0) == 2, "without the box and overlays the caption would have been part of the cut-out")

print(f"ALL {ok} PASS")
