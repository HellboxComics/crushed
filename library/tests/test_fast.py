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
_real_unroll = skin.unroll_view
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
_rl = MS.read_lines
MS.read_lines = lambda png, **k: ["DURACELL", "100%", "1.5 V", "|||", "06"]
wds2 = fast.photo_words(good, lambda *a: None)
check("100%" in wds2 and "1.5 V" in wds2 and "|||" not in wds2, f"a printed amount (the meter's 100%) is a line too ({wds2})")
MS.read_lines = _rl

# a listing lends its photos only to photos of the item itself (12:44: a lot's TrustFire photos, scored 0, got in)
V.ask = lambda use, q, imgs, think=False, side=1280: {"lz_a.jpg": {"real_photo": True, "score": 9, "side": "front", "one_item": True, "kind": "item"},
                                                      "lz_b.jpg": {"real_photo": True, "score": 0, "side": "none", "one_item": False, "kind": "item"},
                                                      "lz_c.jpg": {"real_photo": True, "score": 4, "side": "back", "one_item": True, "kind": "item"}}[os.path.basename(imgs[0])]
lz = [{"file": img(n), "listing": "9"} for n in ("lz_a.jpg", "lz_b.jpg", "lz_c.jpg")]
gz = [os.path.basename(g["file"]) for g in fast.sort_refs(lz, {"product": "Duracell AA", "year": 1998}, R, lambda *a: None)]
check(gz == ["lz_a.jpg", "lz_c.jpg"], f"a listing's photo scored 0 is not lent in ({gz})")
# draw: the item as a studio photo, the era and real words in the prompt; the other side from its own photos
calls = []


def fake_draw(description, photos, out, width=None, height=None, prefix=None, seed=None, timeout=3600):
    calls.append({"photos": list(photos), "prefix": prefix, "out": out})
    Image.new("RGB", (width, height), (200, 200, 200)).save(out)
    return out


T.draw_from_photos = fake_draw
fast.drawn_ratio = lambda png: 50.5 / (45.55 / 3.14159)     # drawn in the item's own proportions
R.reference_sheet = lambda files, out, cell=512, cols=None: (Image.new("RGB", (64, 64)).save(out) or out)
tex = os.path.join(W, "tex")
os.makedirs(tex)
picks = iter([{"match": 6, "wrong": ["meter missing"]}, {"match": 9}, {"match": 9}, {"match": 9}])
V.ask = lambda use, q, imgs, think=False, side=1280: next(picks)
T.photo_mask = lambda f, timeout=300: f
skin.cutout = lambda f, out: f["file"]
SIDES = {"l1a.jpg": ["DURACELL", "ALKALINE BATTERY", "PRESS DOTS TO TEST"],
         "l1b.jpg": ["DURACELL POWERCHECK", "Patented", "BEST IF INSTALLED BY", "JAN 2001"]}
MS.read_lines = lambda png, **k: [] if "_middle" in png else SIDES.get(os.path.basename(png), sum(SIDES.values(), []) if "side" in os.path.basename(png) else ["DURACELL", "ALKALINE BATTERY"])
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
    w = np.zeros((h, 2048)); w[:, 600:1450] = 1
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
judged = iter([{"realism": 8, "era": 8, "words": 9}])
PICK = {"m": 9}
def _ask(use, q, imgs, think=False, side=1280):
    if "real_photo" in q:
        return looks[os.path.basename(imgs[0])]
    if '"realism"' in q:
        return next(judged)
    return {"match": PICK["m"]}
V.ask = _ask
fast.photo_words = lambda good, log, most=8: sum(SIDES.values(), [])   # both sides' words agreed by two photos
calls.clear()
out = fast.build("x_aa", {"product": "Duracell AA", "year": 1998, "mat": "steel", "family_lib": {"family": "cylindrical_cell"}}, d, R2)
check(filed == ["x_aa"] and out["era"] == 8, "the pass is filed in the Asset Library")
check(any(a[0] == "lathe.py" for a in blend) and any(a[0] == "contract.py" for a in blend), "built by the real-size round builder and the deliverable contract")
check([s.get("step", "")[:3] for s in st if s.get("step")][:5] == ["1/5", "2/5", "3/5", "4/5", "5/5"], "five steps on the page")
# a judged miss: the matched drawings are kept, never redrawn with the judge's notes (they took side 1 to 2/10)
filed.clear(); blend.clear(); st.clear(); calls.clear()
judged = iter([{"realism": 5, "era": 8, "words": 9, "fix": ["make the top a raised button"]}])
out1 = fast.build("x_aa", {"product": "Duracell AA", "year": 1998, "mat": "steel", "family_lib": {"family": "cylindrical_cell"}}, d, R2)
check(not filed and not any("raised button" in (c["prefix"] or "") for c in calls) and len([c for c in calls if "side1_" in c["out"]]) == 1,
      f"a judged miss stops: nothing redrawn with the judge's notes ({len([c for c in calls if 'side1_' in c['out']])} side-1 drawings)")
check("failed" in st[-1].get("step", "") and "raised button" in st[-1].get("step", ""), "and the page says why")
# a drawing that never matches is never built or filed
filed.clear(); blend.clear(); st.clear()
PICK["m"] = 3
out2 = fast.build("x_aa", {"product": "Duracell AA", "year": 1998, "mat": "steel", "family_lib": {"family": "cylindrical_cell"}}, d, R2)
check(not filed and not blend and "failed" in st[-1].get("step", ""), f"no match, nothing built or filed: {st[-1].get('step', '')[:80]}")
MS.read_lines = lambda png, **k: ["DURACELL", "note", "Bethel", "Wqzzrt"]
bad = fast.unknown_words(os.path.join(tex, "label.png"), ["DURACELL", "Bethel, CT 06801"])
check(bad == ["note", "Wqzzrt"], f"made-up words on the finished label are found ({bad})")
src = open(os.path.join(os.path.dirname(fast.__file__), "run.py")).read()
check("if fast.applies(cid, card, sys.modules[__name__]):" in src, "the run sends round items down the five steps")
art = np.zeros((400, 50, 3)); art[:120] = (0.8, 0.5, 0.2)
check(abs(fast.band_edge(art) - 119) <= 4, f"the band edge (copper meets black) is found ({fast.band_edge(art)})")
check(len(s2) and len(s2[0]["photos"]) == 1, "side 2 is drawn from its own photo only (with side 1's drawing beside it, it copied side 1)")
a2 = np.zeros((400, 50, 3)); a2[:120] = (0.9, 0.4, 0.3); a2[120:] = (0.1, 0.1, 0.1)
r1 = np.zeros((400, 50, 3)); r1[:120] = (0.8, 0.55, 0.25); r1[120:] = (0.05, 0.05, 0.05)
mb = fast.match_bands(a2, r1, 120)
check(np.abs(mb[:120].mean((0, 1)) - (0.8, 0.55, 0.25)).max() < 0.05, "side 2's copper takes side 1's copper color")
import inspect
check("draw_from_photos" not in inspect.getsource(fast.label_from), "no generative edit redraws the unrolled strips (it drew a battery, not a label)")

# the empty stretches between the drawn sides are finished where they face the camera (TEXTure / Text2Tex)
Wt, Ht = 2048, 2273                                        # a label with bands, print blocks and grain (sharp)
rng = np.random.default_rng(1)
lab = np.zeros((Ht, Wt, 3)); lab[:Ht // 3] = (0.8, 0.5, 0.3); lab[Ht // 3:] = 0.08
for c0, r0 in ((150, 900), (500, 1300), (900, 1000), (1300, 1500), (1700, 1100)):
    lab[r0:r0 + 500, c0:c0 + 120] = 0.9
lab = np.clip(lab + rng.normal(0, 0.06, lab.shape), 0, 1)
v, vm = fast.roll_view(lab, 600, os.path.join(W, "rv.png"))
l, w = _real_unroll({"file": v, "mask": vm, "whole": True}, 50.5, 45.5, Wt, max_deg=70)
cols = np.where(w.max(0) > 0.05)[0]
errs = [np.abs(np.roll(lab, sh, axis=1)[::16, cols] - l[::16, cols]).mean() for sh in range(0, Wt, 4)]
check(abs(int(np.argmin(errs)) * 4 - (Wt // 2 - 600)) <= 16, f"the label wrapped back on the item and unrolled lands on the same columns ({int(np.argmin(errs)) * 4} vs {Wt // 2 - 600})")
sc = np.zeros(2048, bool); sc[700:1350] = True; sc[1700:2048] = True; sc[:20] = True
check(fast.gaps(sc) == [(20, 680), (1350, 350)], f"the empty stretches are found, wrapping round ({fast.gaps(sc)})")
seen = np.tile(sc, (128, 1))                              # image quilting: the uncovered stretch carries the
base = np.zeros((128, 2048, 3)); base[:40] = (0.8, 0.5, 0.3); base[40:] = 0.08   # label's own plain bands on, at
base = np.clip(base + rng.normal(0, 0.01, base.shape), 0, 1)                     # their own heights
base[60:100, 800:900] = 0.95                                                       # a word on a drawn side
base[:, ~sc] = 0.0                                                                  # the uncovered stretch: empty
got = fast.quilt_fill(base.copy(), seen, lambda *a: None)
gapc = ~sc
inner = np.zeros(2048, bool); inner[100:620] = True; inner[1420:1630] = True   # away from the soft edges
check(np.abs(got[:30][:, inner].mean((0, 1)) - (0.8, 0.5, 0.3)).max() < 0.05 and abs(got[50:][:, inner].mean() - 0.08) < 0.03,
      "the uncovered stretch carries the copper and the black on at their own heights")
check(got[42:][:, gapc].max() < 0.5, "and no print is copied into it (only print-free patches)")
check(np.allclose(got[:, sc], base[:, sc]), "the drawn views are untouched")
check("draw_from_photos" not in inspect.getsource(fast.quilt_fill), "nothing generative draws the uncovered stretch (it printed DURACELL, Pal, FINISHED)")
MS.read_lines = lambda png, **k: ["DURACELL", "Pal", "POWEDCHECKIN", "PRESS DBTS TO TEST"]
bad = fast.unknown_words(os.path.join(tex, "label.png"), ["DURACELL", "PRESS DOTS TO TEST", "DURACELL POWERCHECK"])
check(bad == ["POWEDCHECKIN", "DBTS"], f"near-miss made-up words are found ({bad})")
# views between the two sides: placed by their matching print, only onto what nothing covers yet
reg = []
def fake_reg(front, others, Wd, log=None):
    reg.append(1)
    l, w = others[0]
    return [front, (np.roll(l, 700, axis=1), np.roll(w, 700, axis=1))]
skin.register_strips = fake_reg
skin.unroll_view = fake_unroll
T.draw_from_photos = fake_draw
MS.read_lines = lambda png, **k: []
fast.FILLED.clear()
said_words = iter([[("BESTIFINSTALLED JANUARY", 1000)], [("ALKALINE BATTERY", 1000)], [("BESTIFINSTALLED JANUARY", 300)]])
fast.view_words = lambda art, cols: next(said_words)
png3, _ = fast.label_from(front, back, 50.5, 45.5, tex, lambda *a: None, extra=[front])
check(fast.FILLED["share"] >= 0.9, f"a view between the sides is placed by its words and fills its stretch ({fast.FILLED.get('share')})")

# the hunt: the item's own kind of thing, never merchandise
rows2 = [{"title": t} for t in ("Vintage Duracell PowerCheck Lapel Pin", "Duracell Copper Top Coffee Mug 1990s",
                                "Lot of 3 Vintage Duracell PowerCheck AA Batteries 1998", "Duracell Bunny Plush Toy",
                                "Vintage Duracell PowerCheck AA battery JAN 2001")]
rk2 = [r["title"] for r in fast.rank_listings(rows2, ["Duracell PowerCheck AA"], "Duracell", 1998, kind="battery")]
check(rk2 and all("Batter" in t or "batter" in t for t in rk2) and len(rk2) == 2, f"pins, mugs and toys are no listing for a battery ({rk2})")
rows3 = [{"title": t} for t in ("Duracell 9 Volt Battery MN1604 9V Vintage Still In", "Rare Set Of 4 Duracell Coppertop AA Batteries - Circa 1998",
                                "Duracell PowerCheck Power Check Meter 6 AA Batteries", "Duracell Coppertop Batteries AA Power Boost Alkaline 24",
                                "Duracell Coppertop Batteries AA Power Boost Alkaline 40", "Vintage Duracell Coppertop AA battery 1999", "Duracell Coppertop AA 20 pack")]
rk3 = sorted(r["title"][:12] for r in fast.rank_listings(rows3, ["Duracell Coppertop", "Duracell Powercheck", "Duracell Coppertop AA alkaline battery"], "Duracell", 1998, kind="AA battery"))
check(rk3 == ["Duracell Pow", "Rare Set Of ", "Vintage Dura"], f"another size and today's packs are left out; the era's own names and years count ({rk3})")
rows4 = [{"title": x} for x in ("Pair Vintage Duracell Powercheck AA Batteries For Collection Display 2001 90s",
                                "Lot Of 4 Vintage Duracell PowerCheck AA Batteries For Collection Display",
                                "Duracell PowerCheck Power Check Meter 6 AA Batteries - No Corrosion, SOLD AS IS")]
check(len(fast.rank_listings(rows4, ["Duracell Coppertop", "Duracell Powercheck", "Duracell Coppertop AA alkaline battery"], "Duracell", 1998, kind="AA battery")) == 3,
      "collectors' listings ('for collection display') and a few titles that all say PowerCheck are kept")
# views are placed round the label by the printed words they share (the meter view links PowerCheck and logo sides)
vw = [{"kind": "front", "words": [("DURACELL POWERCHECK", 1000), ("Patented", 1050)]},
      {"kind": "back", "words": [("ALKALINE BATTERY", 1020), ("Tested at 70F/21C", 900)]},
      {"kind": "extra", "words": [("Tested at 70F/21C", 1250), ("DURACELL POWERCHECK", 700)]}]
shz = fast.place_by_words(vw, 2048, lambda *a: None)
check(shz.get(2) == 300 and shz.get(1) == 650, f"the meter view sits by its PowerCheck words, the logo side by its test-at words ({shz})")
vw2 = [{"kind": "front", "words": [("Patented", 1050), ("DURACELL", 1000)]}, {"kind": "back", "words": [("ALKALINE BATTERY", 1020), ("DURACELL", 1000)]},
       {"kind": "extra", "words": [("ALKALINE BATTERY", 1100)]}]
shz2 = fast.place_by_words(vw2, 2048, lambda *a: None, skip=["Duracell"])
check(shz2.get(1) == 1024 and shz2.get(2) == (1020 + 1024 - 1100) % 2048, f"the item's own name is no anchor; nothing else shared: the other side half a turn round, and a view chains off it ({shz2})")
# a view sharing no two words with the placed ones goes in the widest stretch they did not see, never left out
# (2026-10-09: the big-logo side was left out and its logo quilted over)
_wc = lambda c0, c1: np.array([1.0 if c0 <= i < c1 else 0.0 for i in range(2048)])
vw3 = [{"kind": "front", "words": [("Patented", 1000)], "wcol": _wc(624, 1424)},
       {"kind": "back", "words": [("meter", 1000)], "wcol": _wc(624, 1424)},
       {"kind": "extra", "words": [("ALKALINE", 1000)], "wcol": _wc(624, 1424)}]
shz3 = fast.place_by_words(vw3, 2048, lambda *a: None)
check(shz3.get(1) == 1024 and shz3.get(2) in (512, 1536), f"the logo side fills a stretch no placed view saw ({shz3})")
# one long word places a view when the pictures do not disagree where they overlap (2026-10-09: the meter side
# shared only POWERCHECK with the panel side, went opposite, and the PowerCheck box was printed twice)
rng_ = np.random.default_rng(1)
lab_ = np.repeat(rng_.random((40, 2048, 1)), 3, axis=2)
vA = {"kind": "front", "words": [("POWERCHECK", 1200)], "wcol": _wc(624, 1424), "l": lab_.copy()}
vB = {"kind": "back", "words": [("POWERCHECK", 900)], "wcol": _wc(624, 1424), "l": np.roll(lab_, -300, axis=1)}
shz4 = fast.place_by_words([vA, vB], 2048, lambda *a: None)
check(shz4.get(1) == 300, f"one long shared word, pictures agree: placed by it ({shz4})")
vC = dict(vB, l=np.repeat(rng_.random((40, 2048, 1)), 3, axis=2))
shz5 = fast.place_by_words([vA, vC], 2048, lambda *a: None)
check(shz5.get(1) == 1024, f"one long word the pictures contradict is not trusted ({shz5})")
# no shared words read: the shared PRINT places a view - and unrelated print does not (2026-10-09: the meter side
# went opposite and the meter was printed twice)
rng2 = np.random.default_rng(7)
band = np.zeros((60, 2048, 3)); band[:20] = 0.7                  # a copper band and a black body: no clue alone
prt = rng2.random((60, 2048, 1)).repeat(3, axis=2) * 0.3 + band
vP = {"kind": "front", "words": [], "wcol": _wc(624, 1424), "l": prt * _wc(624, 1424)[None, :, None]}
mv = np.roll(prt, -500, axis=1)                                   # the same label, seen 500 columns further round
vQ = {"kind": "back", "words": [], "wcol": _wc(624, 1424), "l": mv * _wc(624, 1424)[None, :, None]}
shp = fast.place_by_words([vP, vQ], 2048, lambda *a: None)
check(shp.get(1) == 500, f"the shared print places the meter side ({shp})")
vR = dict(vQ, l=(rng2.random((60, 2048, 1)).repeat(3, axis=2) * 0.3 + band) * _wc(624, 1424)[None, :, None])
check(fast.by_print(vP, vR, 2048) is None, "print that is not shared places nothing (the other side still goes opposite)")
# a copy's photo is turned so its print reads the right way up; when nothing reads, its bands run like side 1's
# (2026-10-09: copies turned upside down were drawn as mirrored garble, 3 tries x 2 sides every build)
from PIL import Image as _I
refp = os.path.join(W, "ref_side1.png")
r_ = _I.new("RGB", (400, 100), "white"); r_.paste((190, 110, 50), (20, 20, 140, 80)); r_.paste((20, 20, 20), (140, 20, 380, 80)); r_.save(refp)
stand = r_.rotate(270, expand=True, fillcolor="white")          # standing, copper end at the top
check(fast.same_way(stand, refp, (90, 270)) == 90, "a standing copy is laid down with its copper end where side 1 has it")
check(fast.same_way(r_.rotate(180), refp, (0, 180)) == 180, "an upside-down copy is turned the right way round")
_rl2 = MS.read_lines
MS.read_lines = lambda png, **k: ["PRESS DOTS TO TEST"] if _I.open(png).size[0] > _I.open(png).size[1] and "turn" in png and _I.open(png).getpixel((30, 50))[0] > 150 else []
t_, ok_, _ = fast.upright(stand, ["PRESS DOTS"], (90, 270))
check(ok_ and t_ == 90, f"the turn whose words read wins ({t_}, {ok_})")
MS.read_lines = lambda png, **k: ["PRESS DOTS TO TEST"]            # a reader that reads both ways (Apple's)
t2_, ok2_, _ = fast.upright(r_, ["PRESS DOTS"], (0, 180))
check(t2_ == 0 and not ok2_, f"a near tie is no answer - the photo stays as it lies ({t2_}, {ok2_})")
MS.read_lines = _rl2
# a photo of ANOTHER version shares words but not print: left out (2026-10-09: a later italic-logo Duracell landed
# by 'Bethel CT 06801' and the label got a second logo)
vS = {"kind": "front", "words": [("Patented", 1100), ("Bethel", 1150)], "wcol": _wc(624, 1424), "l": prt * _wc(624, 1424)[None, :, None]}
vT_same = {"kind": "extra", "words": [("Patented", 800), ("Bethel", 850)], "wcol": _wc(624, 1424),
           "l": np.roll(prt, -300, axis=1) * _wc(624, 1424)[None, :, None]}
vT_other = dict(vT_same, l=(rng2.random((60, 2048, 1)).repeat(3, axis=2) * 0.3 + band) * _wc(624, 1424)[None, :, None])
check(fast.place_by_words([vS, vT_same], 2048, lambda *a: None).get(1) == 300, "the same version, words and print agree: placed")
check(1 not in fast.place_by_words([vS, vT_other], 2048, lambda *a: None), "another version (words agree, print does not): left out")
vS_soft = dict(vS, wcol=vS["wcol"] * 0.2); vT_soft = dict(vT_other, wcol=vT_other["wcol"] * 0.2)   # soft photos: weights top out at 0.2
check(1 not in fast.place_by_words([vS_soft, vT_soft], 2048, lambda *a: None), "the check runs on soft photos too (weights under 0.3)")
# the vision brain proofreads the scanner's lines; it may not add a line the scanner did not read
V.ask = lambda use, q, imgs, think=False, side=1280: {"lines": ["DURACELL", "BEST IF INSTALLED BY:", "TO TEST", "Made in Atlantis"]}
pr = fast.proofread(["DURAGEL", "BEST IF INSTALLED RY:", "TOTEST"], ["a.jpg"], {"product": "Duracell AA", "year": 1998}, lambda *a: None)
check(pr == ["DURACELL", "BEST IF INSTALLED BY:", "TO TEST"], f"misreadings put right, nothing added ({pr})")
# the label made flat from the start: the stitched label is only the guide, the artwork is drawn and turned back
import layout as LAYM
art_dir = os.path.join(W, "artt"); os.makedirs(art_dir, exist_ok=True)
Image.new("RGB", (300, 330), (20, 20, 20)).save(os.path.join(art_dir, "flat_ref.png"))      # map: 300 around, 330 along
seen_read = []
def fake_make(product, read, words, w, h, out_dir, rounds=4, log=print, typical=()):
    seen_read.append(Image.open(read).size)
    os.makedirs(out_dir, exist_ok=True)
    pth = os.path.join(out_dir, "label.png"); Image.new("RGB", (4096, int(4096 * h / w)), (200, 120, 40)).save(pth)
    return pth, pth, 8
LAYM.make = fake_make
got_art = fast.label_art("Duracell AA", art_dir, ["DURACELL"], 50.5, 45.5, lambda *a: None)
ga = Image.open(got_art)
check(seen_read == [(330, 300)] and ga.width >= 4096 and ga.height > ga.width,
      f"the guide is read with the plus end at the left; the artwork comes back in the map's layout ({seen_read}, {ga.size})")
gx = np.full((330, 300, 3), 20, np.uint8); gx[:, :40] = np.random.default_rng(3).integers(0, 255, (330, 40, 3))
Image.fromarray(gx).save(os.path.join(art_dir, "flat_ref.png"))                    # print at the left edge (round 0)
reads = []
def fake_make2(product, read, words, w, h, out_dir, rounds=4, log=print, typical=()):
    reads.append(np.asarray(Image.open(read)).astype(float)); return fake_make(product, read, words, w, h, out_dir)
LAYM.make = fake_make2
fast.label_art("Duracell AA", art_dir, ["DURACELL"], 50.5, 45.5, lambda *a: None)
rd = reads[-1]
check(rd[:15].std() < 5 and rd[-15:].std() < 5, "the seam is put at the plainest place round: nothing printed on the edges that meet")
LAYM.make = lambda *a, **k: (got_art, got_art, 4)
check(fast.label_art("Duracell AA", art_dir, ["DURACELL"], 50.5, 45.5, lambda *a: None) is None, "artwork under 6/10: the stitched label is kept")
# several copies in one photo: each cut out as a view of its own
grp = os.path.join(W, "three.png")
g3 = np.full((300, 500, 3), 255, np.uint8)
for x0 in (40, 200, 360):
    g3[30:270, x0:x0 + 80] = (60, 60, 60)
Image.fromarray(g3).save(grp)
T.photo_mask = lambda f, timeout=300: (Image.fromarray(((np.asarray(Image.open(f).convert("L")) < 128) * 255).astype(np.uint8)).save(f + "_m.png") or f + "_m.png")
cops = fast.split_items({"file": grp, "look": {"one_item": False, "score": 9}}, os.path.join(W, "copies"), lambda *a: None)
check(len(cops) == 3 and all(c["look"]["one_item"] for c in cops), f"three copies in one photo become three views ({len(cops)})")
# each column comes from the view that saw it most squarely; the seam avoids print
Hh, Ww = 40, 400
va = np.full((Hh, Ww, 3), 0.2); vb = np.full((Hh, Ww, 3), 0.2)
va[:, 150:170] = 0.9                                           # print near view A's squeezed edge
vb[:, 150:170] = 0.9                                           # the same print, square-on in view B
wa = np.clip(1 - np.abs(np.arange(Ww) - 100) / 120, 0, 1)      # A looks at column 100
wb = np.clip(1 - np.abs(np.arange(Ww) - 200) / 120, 0, 1)      # B looks at column 200
labp, covp = fast.pick_views([(va, wa), (vb, wb)], lambda *a: None)
check(np.allclose(labp[:, 150:170], 0.9) and covp[:, 380:].max() == 0 and covp[:, :50].max() > 0,
      "each column from the view that saw it squarely; what no view saw stays unseen")
print(f"ALL {ok} PASS")
