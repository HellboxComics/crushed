"""The label is REDRAWN whole from all the evidence - the stitched real pieces and whole photos of the item from other
sides go to Qwen-Image-Edit as references, the exact words in the prompt - each try checked by reading the words back
and by the judge, the best kept; the stitched photo is only the fallback (Cody, 2026-10-06 12:48)."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import run  # noqa: E402
import turnaround as T  # noqa: E402
import measure as MS  # noqa: E402
import vet as V  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


tex = os.path.join(W, "tex")
os.makedirs(tex)
real = os.path.join(tex, "real.png")
Image.fromarray(np.full((300, 700, 3), 30, np.uint8)).save(real)
refs = []
for i in (1, 2):
    f = os.path.join(tex, f"item{i}.png")
    Image.new("RGB", (100, 300), (200, 120, 60)).save(f)
    refs.append(f)
words = ["DURACELL", "POWERCHECK", "BEST IF INSTALLED BY:", "JAN 2001", "MN 1500", "LR6"]
calls = []


def fake_draw(description, photos, out, width=None, height=None, prefix=None, seed=None, timeout=3600):
    calls.append({"photos": list(photos), "w": width, "h": height, "prefix": prefix, "seed": seed})
    Image.new("RGB", (width, height), (10, 10 * len(calls), 10)).save(out)
    return out


T.draw_from_photos = fake_draw
T.upscale = lambda png, force=False: png
reads = iter([["DURACELL", "POWERCHECK"], ["DURACELL POWERCHECK BEST IF INSTALLED BY: JAN 2001 MN 1500 LR6"]])
MS.read_lines = lambda png, **k: next(reads)
looks = iter([{"match": 5, "wrong": ["meter missing"]}, {"match": 9, "wrong": []}])
V.ask = lambda use, q, imgs, think=False, **k: next(looks)
png, notes = run.draw_label_full("Duracell AA", real, refs, words, tex, "judge", 50.5, 45.5, log=lambda *a: None)
check(calls and calls[0]["photos"][0] == real and calls[0]["photos"][1:] == refs, "picture 1 is the stitched real pieces, pictures 2-3 whole photos of the item")
check(all('"JAN 2001"' in c["prefix"] and "COMPLETE printed label" in c["prefix"] for c in calls), "the prompt asks for the complete label with the exact words")
check(abs(calls[0]["w"] / calls[0]["h"] - 50.5 / 45.5) < 0.05, "drawn at the label's own proportions")
check(len(calls) == 2 and png and notes["match"] == 9 and notes["words_found"] == 1.0, f"a weak try is drawn again; the strong one stops the tries ({notes.get('tries')})")
check(Image.open(png).size == Image.open(real).size, "the kept drawing is the label, at the real label's size")
check(os.path.exists(os.path.join(tex, "label_complete.json")), "the label is marked drawn whole (the painter then infers nothing)")

# nothing good enough: no label from the drawing, the caller falls back to the stitched photo
calls.clear()
os.remove(os.path.join(tex, "label_complete.json"))
MS.read_lines = lambda png, **k: ["DURACELL"]
V.ask = lambda use, q, imgs, think=False, **k: {"match": 3, "wrong": ["wrong layout"]}
png2, notes2 = run.draw_label_full("Duracell AA", real, refs, words, tex, "judge", 50.5, 45.5, log=lambda *a: None)
check(png2 is None and len(calls) == 3 and "good enough" in notes2["why"], "three weak tries: no drawing passes, said why")
check(not os.path.exists(os.path.join(tex, "label_complete.json")), "and the label is not marked drawn whole")
src = open(run.__file__).read()
check("drawn, dnotes = draw_label_full(" in src and "png, mr, notes = photo_label(" in src, "the build draws first and keeps the stitched photo as the fallback")
check('os.path.exists(os.path.join(tex, "label_complete.json"))' in src, "the painter skips a label drawn whole")
print(f"ALL {ok} PASS")
