"""The streamlined round build (Cody, 2026-10-07 20:34/20:36): references (eBay first) -> one quick look each ->
ONE drawn studio photo of the item (+ its other side) -> unrolled onto the real-size shape -> one judge (realism,
era, real words). Photos are never the texture. A miss is drawn again once with the judge's fixes."""
import json
import os
import sys
import tempfile
import types

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai", "remaster"))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import fast  # noqa: E402
import vet as V  # noqa: E402
import turnaround as T  # noqa: E402
import skin  # noqa: E402
import measure as MS  # noqa: E402
MS.read_lines = lambda png, **k: ["DURACELL", "PRESS DOTS TO TEST", "ALKALINE BATTERY"]

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


check(fast.display({"product": "Duracell AA", "era_names": ["Duracell PowerCheck"]}) == "Duracell AA (sold then as Duracell PowerCheck)", "the era's own name goes with the item")
check(fast.short_name("Duracell Coppertop AA alkaline battery, circa 1998") == "Duracell Coppertop AA alkaline battery", "the search name drops the era words")
rows = [{"title": t} for t in ("VINTAGE 1.5 Volts Osco Alkaline battery", "Pair Vintage Duracell Powercheck AA Batteries",
                               "Duracell AA Batteries 1.5 Volts Alkaline 24 pack", "Duracell AA Batteries 1.5 Volts Alkaline 40 pack")]
rk = fast.rank_listings(rows, ["Duracell PowerCheck AA"], "Duracell", 1998)
check(rk[0]["title"].startswith("Pair Vintage") and not any("Osco" in r["title"] for r in rk), "rare words and the era rank first; another brand is dropped")

# sort: a listing whose best photo is the item lends all its real photos
hunt = os.path.join(W, "hunt", "x_aa")
os.makedirs(hunt)


def img(name, color=(90, 60, 30)):
    f = os.path.join(hunt, name)
    Image.new("RGB", (300, 200), color).save(f)
    return f


refs = [{"file": img("l1a.jpg"), "listing": "1"}, {"file": img("l1b.jpg"), "listing": "1"},
        {"file": img("l2a.jpg"), "listing": "2"}, {"file": img("g1.jpg"), "listing": None},
        {"file": img("g2.jpg"), "listing": None}, {"file": img("g3.jpg"), "listing": None}]
looks = {"l1a.jpg": {"real_photo": True, "score": 9, "side": "front", "one_item": True},
         "l1b.jpg": {"real_photo": True, "score": 3, "side": "back", "one_item": False},
         "l2a.jpg": {"real_photo": True, "score": 2, "side": "front"},
         "g1.jpg": {"real_photo": False, "score": 9, "side": "front"},
         "g2.jpg": {"real_photo": True, "score": 8, "side": "several"},
         "g3.jpg": {"real_photo": True, "score": 9, "side": "front", "kind": "merch"}}
V.ask = lambda use, q, imgs, think=False, side=1280: looks[os.path.basename(imgs[0])] if "Answer ONLY JSON: {\"real_photo\"" in q else {}
V.quick_model = lambda: "quick"
V.model = lambda: "judge"
R = types.SimpleNamespace(WORK=W, say=lambda *a: None)
good = fast.sort_refs(refs, {"product": "Duracell AA", "year": 1998}, R, lambda *a: None)
names = [os.path.basename(g["file"]) for g in good]
check(names[0] == "l1a.jpg" and "l1b.jpg" in names, f"a good listing lends its other photos ({names})")
check("l2a.jpg" not in names and "g1.jpg" not in names and "g3.jpg" not in names, "a wrong listing, an ad and merchandise (a pin) do not count")
wds = fast.photo_words(good, lambda *a: None)
check("PRESS DOTS TO TEST" in wds, f"the words read on two photos go to the drawing ({wds})")

# draw: the item as a studio photo, the era and real words in the prompt; the other side from its own photos
calls = []


def fake_draw(description, photos, out, width=None, height=None, prefix=None, seed=None, timeout=3600):
    calls.append({"photos": list(photos), "prefix": prefix, "out": out})
    Image.new("RGB", (width, height), (200, 200, 200)).save(out)
    return out


T.draw_from_photos = fake_draw
R.reference_sheet = lambda files, out, cell=512, cols=None: (Image.new("RGB", (64, 64)).save(out) or out)
tex = os.path.join(W, "tex")
os.makedirs(tex)
picks = iter([{"match": 6, "wrong": ["meter missing"]}, {"match": 9}, {"match": 9}, {"match": 9}])
V.ask = lambda use, q, imgs, think=False, side=1280: next(picks)
T.photo_mask = lambda f, timeout=300: f
skin.cutout = lambda f, out: f["file"]
SIDES = {"l1a.jpg": ["DURACELL", "ALKALINE BATTERY", "PRESS DOTS TO TEST"],
         "l1b.jpg": ["DURACELL POWERCHECK", "Patented", "BEST IF INSTALLED BY", "JAN 2001"]}
MS.read_lines = lambda png, **k: SIDES.get(os.path.basename(png), sum(SIDES.values(), []) if "side" in os.path.basename(png) else ["DURACELL", "ALKALINE BATTERY"])
for g in good:                                             # both one-copy photos
    g["look"]["one_item"] = True
front, back, dn = fast.draw({"product": "Duracell AA", "year": 1998}, good, tex, 50.5, 45.5, R, lambda *a: None, words=wds + SIDES["l1b.jpg"])
s1 = [c for c in calls if "side1_" in c["out"]]
s2 = [c for c in calls if "side2_" in c["out"]]
check(s1 and s2, f"two printed sides found by their words, each drawn ({len(s1)}, {len(s2)})")
check(s1[0]["photos"] == [os.path.join(hunt, "l1a.jpg")] or os.path.basename(s1[0]["photos"][0]) in ("l1a.jpg", "l1b.jpg"),
      "each side drawn from ONE photo of that side")
check("studio product photo" in s1[0]["prefix"] and "1998" in s1[0]["prefix"] and '"Patented"' in "".join(c["prefix"] for c in s1 + s2),
      "drawn as the item from its era, with the words read on that side's photo")
# label: the drawn views unrolled, the back half a turn round
T.upscale = lambda png, force=False: png
H = int(round(2048 * 50.5 / 45.5))


def fake_unroll(v, a, b, Wd=2048, max_deg=62):
    h = int(round(Wd * a / b))
    w = np.zeros((h, 2048)); w[:, 700:1350] = 1
    return np.full((h, 2048, 3), 0.4), w


skin.unroll_view = fake_unroll
skin.continue_bands = lambda lab, gaps: lab
png, cover = fast.label_from(front, back, 50.5, 45.5, tex, lambda *a: None)
check(os.path.exists(png) and Image.open(png).width >= 4096 and abs(Image.open(png).height / Image.open(png).width - H / 2048) < 0.01, "the label is on its own layout, at least 4096 px around (saleable resolution)")

# the whole build: a pass is filed; a miss is drawn again with the judge's fixes; two misses stop with the reason
for k in ("label.png",):
    pass
st, filed, blend = [], [], []
d = os.path.join(W, "library", "x_aa")
os.makedirs(os.path.join(d, "model"))
json.dump([dict(r, look=looks[os.path.basename(r["file"])]) for r in refs], open(os.path.join(hunt, "fast_refs.json"), "w"))
spec = {"id": "aa", "profile": [{"part": "label", "pts": [[7.25, 0], [7.25, 50.5]]}]}
fast.shape_spec = lambda cid, card, d, R, log: (os.path.join(d, "shape.json"), spec)
fast.studio_views = lambda glb, d, R, log: img("views.jpg")
R2 = types.SimpleNamespace(WORK=W, say=lambda *a: None, boundary=lambda *a, **k: None, make_room=lambda *a: None,
                           status=lambda cid, **k: st.append(k), reference_sheet=R.reference_sheet,
                           mr_from_bands=lambda png, real, cov, tex, notes: (Image.new("RGB", (8, 8)).save(os.path.join(tex, "label_mr.png")) or os.path.join(tex, "label_mr.png")),
                           run_blender=lambda *a: blend.append(a), finish_files=lambda cid, d: None,
                           file_away=lambda cid, d: (filed.append(cid) or {"ok": True}), jload=lambda p, dflt: dflt)
answers = iter([{"match": 9}, {"match": 9}, {"realism": 8, "era": 5, "words": 8, "fix": ["the meter is the 2003 style"]},
                {"match": 9}, {"match": 9}, {"realism": 8, "era": 8, "words": 9}])
def _ask(use, q, imgs, think=False, side=1280):
    if "real_photo" in q:
        return looks[os.path.basename(imgs[0])]
    a = next(answers)
    return a
V.ask = _ask
fast.photo_words = lambda good, log, most=8: sum(SIDES.values(), [])   # both sides' words agreed by two photos
calls.clear()
out = fast.build("x_aa", {"product": "Duracell AA", "year": 1998, "mat": "steel", "family_lib": {"family": "cylindrical_cell"}}, d, R2)
second = [c for c in calls if "side1_1" in c["out"]][-1]
check("the meter is the 2003 style" in second["prefix"], "the second drawing carries the judge's own fixes")
check(filed == ["x_aa"] and out["era"] == 8, "the pass is filed in the Asset Library")
check(any(a[0] == "lathe.py" for a in blend) and any(a[0] == "contract.py" for a in blend), "built by the real-size round builder and the deliverable contract")
check([s.get("step", "")[:3] for s in st if s.get("step")][:5] == ["1/5", "2/5", "3/5", "4/5", "5/5"], "five steps on the page")
# a drawing that never matches is never built or filed
filed.clear(); blend.clear(); st.clear()
answers = iter([{"match": 3}] * 12)
out2 = fast.build("x_aa", {"product": "Duracell AA", "year": 1998, "mat": "steel", "family_lib": {"family": "cylindrical_cell"}}, d, R2)
check(not filed and not blend and "failed" in st[-1].get("step", ""), f"no match, nothing built or filed: {st[-1].get('step', '')[:80]}")
MS.read_lines = lambda png, **k: ["DURACELL", "note", "Bethel", "Wqzzrt"]
bad = fast.unknown_words(os.path.join(tex, "label.png"), ["DURACELL", "Bethel, CT 06801"])
check(bad == ["note", "Wqzzrt"], f"made-up words on the finished label are found ({bad})")
src = open(os.path.join(os.path.dirname(fast.__file__), "run.py")).read()
check("if fast.applies(cid, card, sys.modules[__name__]):" in src, "the run sends round items down the five steps")
print(f"ALL {ok} PASS")
