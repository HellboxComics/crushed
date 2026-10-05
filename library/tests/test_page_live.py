"""The phone page shows the work as it happens (Cody, 2026-10-05): every step the build has done so far, newest
first, with its pictures, your AI's own score and its notes; on a kept item the cutaway, the parts with their crush
numbers and WHERE the numbers come from, and every side with where it came from."""
import json
import os
import sys
import tempfile
import time

W = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
os.environ["HOME"] = HOME
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
import run  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def png(path, color=(200, 120, 60)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (64, 64), color).save(path)
    return path


now = time.time()
os.makedirs(os.path.join(run.HB), exist_ok=True)
json.dump({}, open(os.path.join(run.HB, "picks.json"), "w"))
json.dump({}, open(os.path.join(run.HB, "approvals.json"), "w"))

# a working item with a review sheet (older step, newer step) and a label try newer than both
d = os.path.join(W, "library", "item_a")
mesh = png(os.path.join(d, "check", "mesh.png"))
label1 = png(os.path.join(d, "texture", "round1.png"), (20, 20, 20))
json.dump({"steps": [
    {"step": "mesh + UV map", "at": now - 600, "note": "", "files": [mesh],
     "checks": [{"check": "one clean UV map per part", "ok": True, "detail": "3 parts"},
                {"check": "size matches the catalog", "ok": True, "detail": "50.5 x 14.5 mm"}]},
    {"step": "label words read", "at": now - 300, "note": "29 words confirmed by two reads", "files": [],
     "checks": [{"check": "every word traces to a photo", "ok": False, "detail": "PHOTOGRAPHIC traces to nothing"}]},
]}, open(os.path.join(d, "review.json"), "w"))
json.dump([{"round": 1, "match": 6, "colors": 1.0, "fixes": ["'PRESS DOTS' is printed on top of 'BEST IF INSTALLED BY:' - move or shrink one"]}],
          open(os.path.join(d, "texture", "rounds.json"), "w"))
os.utime(label1, (now - 60, now - 60))

# a kept item: cutaway, physics, dossier faces
k = os.path.join(W, "library", "item_k")
cut = png(os.path.join(k, "check", "cutaway.png"), (90, 90, 90))
views = png(os.path.join(k, "check", "views.jpg"))
os.makedirs(os.path.join(k, "model"))
json.dump({"item_k_body": {"part": "body", "material_kind": "bare_steel", "density": 7850, "stiffness": 2e11, "yield": 2.5e8, "fails": "dent_fold", "sheet_mm": 0.25},
           "item_k_sleeve": {"part": "sleeve", "material_kind": "printed_plastic_sleeve", "density": 1380, "stiffness": 3e9, "yield": 5e7, "fails": "tear", "sheet_mm": 0.08}},
          open(os.path.join(k, "model", "physics.json"), "w"))
os.makedirs(os.path.join(W, "dossier"))
json.dump({"faces": {"label": {"source": "photo", "photo": "/x/p123.jpg"},
                     "top": {"source": "rebuilt", "note": "no photo of this side - rebuilt from facts only"},
                     "bottom": {"source": "plain"}}}, open(os.path.join(W, "dossier", "item_k.json"), "w"))

json.dump({"item_a": {"product": "Item A", "step": "5/7 texture map", "at": now - 60, "code": run.code_sha()},
           "item_k": {"product": "Item K", "step": "done - kept", "at": now - 3600, "code": run.code_sha(),
                      "check_version": run.check_version(), "views": os.path.relpath(views, W)}},
          open(run.STATUS, "w"))

import remaster as RM  # noqa: E402
RM.publish = lambda force=True: None
run.say = lambda *a, **k: None
run.page(force=False)
import html as _h
html = _h.unescape(open(os.path.join(W, "index.html")).read())

# 1. live steps, newest first, with pictures, scores and notes
a = html.split("Item A")[1].split("<section class=card>")[0]
i_label, i_words, i_mesh = a.find("label art, try 1"), a.find("label words read"), a.find("mesh + UV map")
check(0 <= i_label < i_words < i_mesh, f"steps newest first: label try, then words, then mesh ({i_label}, {i_words}, {i_mesh})")
check("match 6 of 10 by your AI's own eye" in a and "colors 100% right" in a and "PRESS DOTS" in a,
      "the label try shows your AI's own score and the fix it named")
check(os.path.relpath(label1, W) in a and os.path.relpath(mesh, W) in a, "each step shows its pictures (paths the publisher ships)")
check("✓ one clean UV map per part" in a and "✗ every word traces to a photo" in a and "PHOTOGRAPHIC traces to nothing" in a,
      "each step's own checks: what passed, what did not, and why")
check("29 words confirmed by two reads" in a, "a step's note is shown")
check("steps so far (3)" in a, "the count of steps so far")

# 2. the kept card: cutaway, parts with crush numbers and their source, sides with their source
kk = html.split("Item K")[1]
check("inside (cutaway)" in kk and os.path.relpath(cut, W) in kk, "the kept card shows the cutaway")
check("<b>body</b>: bare_steel" in kk and "density 7850" in kk and "fails dent_fold" in kk, "the parts list with each part's crush numbers")
check("handbook values" in kk and "not measured from the item" in kk, "a from: line says where the numbers come from, honestly")
check("<b>label</b> <em>from:</em> a photo (p123.jpg)" in kk, "a side from a photo names the photo")
check("<b>top</b> <em>from:</em> rebuilt from facts with receipts" in kk, "a rebuilt side says so")
check("<b>bottom</b> <em>from:</em> plain: no photo and no fact" in kk, "a plain side says so")
check("steps so far" not in kk, "a kept item shows its deliverables, not the step list")

print(f"ALL {ok} PASS")
