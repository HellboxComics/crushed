"""The label is REDRAWN from all the evidence: Qwen-Image-Edit draws the ITEM from a sheet of every same-size photo
(its strength - asked for a flat sheet it drew a battery on white, 2026-10-06 22:20), turns it 90/180/270 degrees,
and the same stitch used on real photos unrolls the four views into the flat label. Only words read on two photos
are given to it; D cells never reach its sheet. The stitched photo is only the fallback."""
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
import skin  # noqa: E402

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
for i in range(4):
    f = os.path.join(tex, f"item{i}.png")
    Image.new("RGB", (300, 200), (200, 120, 60 + i)).save(f)
    refs.append(f)
words = ["DURACELL", "POWERCHECK", "BEST IF INSTALLED BY:", "JAN 2001", "MN 1500", "LR6"]
calls = []


def fake_draw(description, photos, out, width=None, height=None, prefix=None, seed=None, timeout=3600):
    calls.append({"photos": list(photos), "w": width, "h": height, "prefix": prefix, "out": out})
    Image.new("RGB", (width, height), (10, 10 * len(calls) % 250, 10)).save(out)
    return out


T.draw_from_photos = fake_draw
T.upscale = lambda png, force=False: png
T.photo_mask = lambda f, timeout=300: f
composed = []


def fake_compose(vs, a, b, W=2048, log=None):
    composed.append([v["file"] for v in vs])
    return np.full((200, 400, 3), 0.5), np.ones((200, 400))


skin.compose = fake_compose
MS.read_lines = lambda png, **k: ["DURACELL POWERCHECK BEST IF INSTALLED BY: JAN 2001"] if "turn" not in png else ["MN 1500 LR6"]
looks = iter([{"match": 5, "wrong": ["meter missing"]}, {"match": 9, "wrong": []}])
V.ask = lambda use, q, imgs, think=False, **k: next(looks)
png, notes = run.draw_label_full("Duracell AA", real, refs, words, tex, "judge", 50.5, 45.5, log=lambda *a: None)
front_calls = [c for c in calls if "turn" not in c["out"]]
turn_calls = [c for c in calls if "turn" in c["out"]]
check(front_calls[0]["photos"] == [notes["sheet"], refs[0]] and notes["sheet_of"] == 3,
      "the front is drawn from one sheet of every photo plus the clearest single photo")
check("studio product photo" in front_calls[0]["prefix"] and '"JAN 2001"' in front_calls[0]["prefix"],
      "it is asked for the ITEM (what it draws well), with the exact words")
check(len(front_calls) == 2, f"a weak front is drawn again; a strong one stops the tries ({len(front_calls)})")
check([c["out"].rsplit("turn", 1)[1] for c in turn_calls] == ["90.png", "180.png", "270.png"]
      and all(c["photos"][0] == notes["file"] for c in turn_calls), "three turned views, each from the kept front")
check(composed and len(composed[-1]) == 4 and composed[-1][0] == notes["file"], "the four views are unrolled by the same stitch, the front first")
check(png and Image.open(png).size == Image.open(real).size, "the label comes out in the real label's layout and size")
check(os.path.exists(os.path.join(tex, "label_complete.json")), "the label is marked drawn whole (the painter then infers nothing)")

# not all the way around: no label from the drawing, said why
os.remove(os.path.join(tex, "label_complete.json"))
skin.compose = lambda vs, a, b, W=2048, log=None: (np.zeros((200, 400, 3)), np.pad(np.ones((200, 100)), ((0, 0), (0, 300))))
V.ask = lambda use, q, imgs, think=False, **k: {"match": 9, "wrong": []}
png2, notes2 = run.draw_label_full("Duracell AA", real, refs, words, tex, "judge", 50.5, 45.5, log=lambda *a: None)
check(png2 is None and "way around" in notes2["why"], f"views that cover a quarter of the way around do not pass ({notes2.get('why')})")
check(not os.path.exists(os.path.join(tex, "label_complete.json")), "and the label is not marked drawn whole")
# a front that does not match the photos: no turns drawn at all
calls.clear()
V.ask = lambda use, q, imgs, think=False, **k: {"match": 3, "wrong": ["wrong layout"]}
png3, notes3 = run.draw_label_full("Duracell AA", real, refs, words, tex, "judge", 50.5, 45.5, log=lambda *a: None)
check(png3 is None and len(calls) == 3 and "match" in notes3["why"], "three weak fronts: nothing turned, said why")

# the words: only what two photos agree on
by_png = {"a1.png": ["DURACELL POWERCHECK", "AUBACELLMIGAN"], "a2.png": ["DURACELL", "POWERCHECK", "Done"],
          "b1.png": ["DURACELL® POWERCHECK™", "SIACE", "MN 1500"]}
src_of = {"a1.png": "/p/a.jpg", "a2.png": "/p/a.jpg", "b1.png": "/p/b.jpg"}
kept_w, dropped = run.agreed_words(["DURACELL", "POWERCHECK", "AUBACELLMIGAN", "Done", "SIACE", "MN 1500", "Bethel, CT 06801"],
                                   by_png, src_of, keep=["Bethel, CT 06801"])
check(kept_w == ["DURACELL", "POWERCHECK", "Bethel, CT 06801"], f"read on two photos (or listed by the careful look) is kept: {kept_w}")
check(set(dropped) == {"AUBACELLMIGAN", "Done", "SIACE", "MN 1500"}, "a word read on one photo only is not (two strips of one photo are one photo)")

# a D cell never reaches the sheet
d = tempfile.mkdtemp()


def photo(name, L, D):
    im = np.zeros((500, 500, 3), np.uint8)
    yy, xx = np.mgrid[0:500, 0:500] - 250
    m = ((abs(xx) < L / 2) & (abs(yy) < D / 2))
    im[m] = (40, 40, 40)
    f = os.path.join(d, name + ".png")
    Image.fromarray(im).save(f)
    mf = os.path.join(d, name + "_mask.png")
    Image.fromarray((m * 255).astype(np.uint8)).save(mf)
    return {"file": f, "mask": mf}


said = []
got = run.same_size_photos([photo("aa", 350, 100), photo("dcell", 180, 100)], 50.5, 45.5, log=said.append)
check([os.path.basename(g["file"]) for g in got] == ["aa.png"] and any("dcell" in x for x in said), f"the D cell is left off the sheet ({said})")
src = open(run.__file__).read()
check("drawn, dnotes = draw_label_full(" in src and "png, mr, notes = photo_label(" in src, "the build draws first and keeps the stitched photo as the fallback")
check("dwords, dropped = agreed_words(" in src and "same_size_photos(" in src, "the build hands the drawing only agreed words and same-size photos")
check('os.path.exists(os.path.join(tex, "label_complete.json"))' in src, "the painter skips a label drawn whole")
print(f"ALL {ok} PASS")
