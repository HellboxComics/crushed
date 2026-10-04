"""S5 - NOTHING INVENTED (audit 2026-10-04, RC3): an unseen side is the measured paper color plus facts with receipts
only (no fallback logo or picture crops, no brand panel, no invented layout); the label writer may print only whole
read words in read runs; every word on the finished model must trace to a photo, a fact or a read word; no wear is
baked in; a circuit board has no invented traces or bracket; a carton's contents are plain parts from the facts."""
import json
import os
import re
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import review  # noqa: E402
import measure as M  # noqa: E402
import skin  # noqa: E402
import eraprint  # noqa: E402
import panels  # noqa: E402
import finish  # noqa: E402
import cards  # noqa: E402
import run  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


# 1. the label writer: whole read words, in read runs, no recombining, no ® without one read
words = ["DURACELL", "COPPERTOP", "ALKALINE BATTERY", "AA", "1.5V", "MN1500 LR6"]
got = [t["text"] for t in review.only_words([{"text": "CELL"}, {"text": "DURACELL CELL"}, {"text": "ALKALINE BATTERY"},
                                              {"text": "BATTERY ALKALINE"}, {"text": "AA 1.5V"}, {"text": "1.5V"},
                                              {"text": "MN1500"}, {"text": "A"}], words)]
check(got == ["ALKALINE BATTERY", "1.5V", "MN1500"], f"only whole read words in read runs survive: {got}")
t = review.only_words([{"text": "Duracell", "mark": "registered"}], ["DURACELL"])
check(t and "mark" not in t[0], "a ® nobody read is dropped")
t = review.only_words([{"text": "Duracell", "mark": "registered"}], ["DURACELL(R)"])
check(t and t[0].get("mark") == "registered", "a ® that was read stays")

# 2. the output check: words on the model that nothing accounts for
dos = {"photos": [{"labeled": True, "match": "exact", "text": ["DURACELL", "COPPERTOP", "ALKALINE BATTERY", "MN1500 LR6"]},
                  {"labeled": True, "match": "wrong", "text": ["ENERGIZER"]}],
       "identity": {"name": "Duracell Coppertop AA"}, "faces": {}, "facts": {}}
allowed = M.traceable_words(dos)
check("ENERGIZER" not in allowed and "COPPERTOP" in allowed, "a wrong photo's words are not allowed; the item's are")
check(M.untraceable("DURACELL COPPERTOP ALKALINE BATTERY TTBOVHNO", allowed) == [], "one stray token of reader noise is not invention")
check(M.untraceable("DURACELL ENERGIZER MAXIMUM POWER", allowed) == ["ENERGIZER", "MAXIMUM", "POWER"], "words nothing accounts for are called")
check(M.untraceable("DURACEL COPERTOP ALKALINEBATTERY", allowed) == [], "misreads and run-together words are not invention")
check(M.untraceable("DURACELL PHOTOGRAPHIC", allowed) == ["PHOTOGRAPHIC"], "one long invented word is enough")
bd = os.path.join(W, "b1", "texture")
os.makedirs(bd)
json.dump(["PATENTED", "POWERCHECK"], open(os.path.join(bd, "words.json"), "w"))
check("POWERCHECK" in M.traceable_words(dos, os.path.join(W, "b1")), "the label's read words count")
src = open(os.path.join(os.path.dirname(M.__file__), "measure.py")).read()
check('checks["text_traceable"]' in src and "untraceable(read[n], allowed)" in src, "the check runs on every rendered side")

# 3. unseen sides: no fallback crops; facts with receipts only; plain otherwise
import vet
vet.ask = lambda *a, **k: {"x0": 0.9, "y0": 0.9, "x1": 0.1, "y1": 0.1}      # a useless answer
front = os.path.join(W, "front.png")
Image.new("RGB", (400, 600), (230, 220, 200)).save(front)
check(skin.logo_box(front, "brain", log=lambda *a: None) is None, "a useless logo answer gives None, never a fixed crop")
check(skin.photo_box(front, "brain", log=lambda *a: None) is None, "a useless picture answer gives None, never a fixed crop")
fr = Image.open(front)
img, used, missing = eraprint.panel_notes("back", {"food": False, "name": "Duracell Coppertop", "brand": "Duracell"},
                                          fr, None, None, 300, 500, (230, 220, 200), (50, 80), None, None)
a = np.asarray(img)
check(used == [] and (np.abs(a.astype(int) - np.array([230, 220, 200])).max() <= 2),
      f"no facts, no sister layout: the measured paper color only - nothing drawn (drew {used})")
img, used, missing = eraprint.panel_notes("back", {"food": False, "name": "X", "upc": "012345678905", "maker_lines": ["Made in USA"]},
                                          fr, None, None, 600, 900, (230, 220, 200), (50, 80), None, None)
check(set(used) <= {"upc", "maker_lines", "net_weight"} and used and not {"logo", "name", "picture"} & set(used + missing),
      f"facts are drawn, the name and logo are not even tried: {used} / {missing}")
img, used, missing = eraprint.panel_notes("back", {"food": False, "name": "X", "upc": "012345678905"}, fr, None, None, 600, 900,
                                          (230, 220, 200), (50, 80), [{"kind": "logo", "box": [0.1, 0.1, 0.9, 0.3]},
                                                                      {"kind": "upc", "box": [0.1, 0.6, 0.9, 0.9]}], None)
check(used == ["upc"] and "logo" in missing, f"a sister layout places facts; a logo with no found box is left blank: {used} / {missing}")
p = panels.brand_panel(fr, None, 200, 300, "left")
check(np.abs(np.asarray(p).astype(int) - np.array([230, 220, 200])).max() <= 2, "a plain side is the paper color only")
ss = open(skin.__file__).read()
check("(0.04, 0.03, 0.96, 0.47)" not in ss and "(0.0, 0.55, 1.0, 0.92)" not in ss, "the fixed crops are gone from skin.py")
check('"source": "plain", "note": "no photo of this side and no fact with a receipt' in ss, "an unseen side with nothing to print is plain and says so")
bc = {c: (o, d) for c, o, d in review.box_checks({"front": {"source": "photo"}, "back": {"source": "plain"},
                                                  "left": {"source": "rebuilt", "drawn": ["upc"], "receipts": {"upc": ["http://x"]}},
                                                  "right": {"source": "rebuilt", "drawn": ["upc"], "receipts": {"upc": []}},
                                                  "top": {"source": "photo"}, "bottom": {"source": "photo"}})}
check(bc["every side comes from a photo or from facts with receipts"][0] is None and "back" in bc["every side comes from a photo or from facts with receipts"][1],
      "a plain side is a gap on the sheet")
check(bc["everything drawn on a rebuilt side has a receipt"][0] is False and "right" in bc["everything drawn on a rebuilt side has a receipt"][1],
      "a fact drawn without a receipt fails the sheet")

# 4. no baked wear anywhere
fs = open(finish.__file__).read()
check("wear" not in fs.split("def box_atlas")[1] and "scuffed edges" not in fs.split("def card")[1].split("def plastic")[0],
      "finish.py bakes no cracked ink, whitening, scuffs or flap seams")
cs = open(os.path.join(os.path.dirname(skin.__file__), "shapes", "carton.py")).read()
check("wear" not in cs and "sprinkle" not in cs.lower() and "frost" not in cs.lower() and "crust" not in cs.lower(),
      "carton.py: no whitened creases, no sprinkles, frosting or crust")
check('C.get("item_color") or' in cs and 'loose = bool(C.get("loose")) or C.get("status") not in ("verified", "single_source")' in cs,
      "carton contents: plain items in a measured or plain color; packs only with a receipted packing fact")
ps = open(os.path.join(os.path.dirname(skin.__file__), "shapes", "pcb.py")).read()
check("rng.integers" not in ps and 'p.get("type") == "bracket"' in ps and "side_left" not in ps,
      "pcb.py: no invented traces or solder joints; a bracket only when read off the photo")
check("bracket" in run.PARTS_Q and "never a part" in run.PARTS_Q, "the board reader may name a bracket it sees, never a usual one")
check("wear" not in run.CHECKS["not_cg"] or "no wear" in run.CHECKS["not_cg"], "the judge no longer asks for slight wear")
check("{closeups}" not in run.CHECKS["details"] and "REAL PHOTO" in run.CHECKS["details"], "details are judged against the photo, not a memory list")
check(not any(d in cards.DETAILS for d in ("worn_edges", "cracked_ink_folds", "scratches", "dust", "fingerprints", "faded_print")),
      "the construction card lists how a thing is made, never its wear")
for f in ("cards.py", "run.py", "layout.py", "panels.py", "eraprint.py", "finish.py"):
    txt = open(os.path.join(os.path.dirname(skin.__file__), f)).read()
    m = re.search(r"slight wear|cracked ink along", txt)
    check(not m or f == "finish.py" and "no cracked ink" in txt, f"{f}: no prompt or comment invites wear" + (f" ({m.group(0)})" if m else ""))

print(f"ALL {ok} PASS")
