"""S4 - SIZE AND PICK VERIFIED (audit 2026-10-04, RC5/RC6): no default size; the catalog size must agree with the
shape of the item in the pick or the build stops and asks; a size from the phone wins; kit sizes need their numbers
in the source; the right-version marks are counted by name; an auto-pick needs a rival and must pass its own careful
look; era names need backing."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
os.environ["HOME"] = HOME
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import sizecheck  # noqa: E402
import cards  # noqa: E402
import portal as P  # noqa: E402
import kitmaker  # noqa: E402
import run  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def mask(w, h, name):
    a = np.zeros((h + 40, w + 40), np.uint8)
    a[20:20 + h, 20:20 + w] = 255
    p = os.path.join(W, name)
    Image.fromarray(a).save(p)
    return p


# 1. sizecheck: an AA (14.5 x 14.5 x 50.5) seen from the front is 3.48:1; a D cell (34 x 34 x 61) is 1.8:1
aa, dcell = [0.0145, 0.0145, 0.0505], [0.034, 0.034, 0.061]
tall = mask(100, 348, "tall.png")
r = sizecheck.agree(aa, tall, "front")
check(r["ok"] is True and r["nearest"] == "front", f"an AA photo agrees with the AA size: {r['why']}")
r = sizecheck.agree(dcell, tall, "front")
check(r["ok"] is False and "apart" in r["why"], f"an AA photo disagrees with a D cell size: {r['why']}")
r = sizecheck.agree([0.1, 0.1, 0.1], tall, "mixed")
check(r["ok"] is False, "a 0.1 m cube never agrees with a tall thing")
r = sizecheck.agree(dcell, tall, "front", whole=False)
check(r["ok"] is None, "a cut-off item can't be measured (not a failure, not a pass)")
r = sizecheck.agree(dcell, tall, "front", count=4)
check(r["ok"] is None, "several touching items can't be measured")
r = sizecheck.agree(aa, mask(100, 100, "sq.png"), "top")
check(r["ok"] is True, "the round end from above is square: agrees with top")
r = sizecheck.agree([0.0, 0, 0], tall, "front")
check(r["ok"] is False and "no catalog size" in r["why"], "no size = disagree")

# 2. cards.catalog: no made-up size, ever
plan = os.path.join(cards.ROOT, "assets", "plan")
items = json.load(open(os.path.join(plan, "items.json")))
nosize = next((k for k, v in items.items() if not v.get("size")), None)
if nosize:
    try:
        cards.catalog(nosize)
        check(False, "an item with no catalog size must not get a default")
    except RuntimeError as e:
        check("no real size" in str(e), f"no catalog size -> stop, never a 0.1 m cube: {str(e)[:80]}")
else:
    print("skip: every catalog item has a size")
try:
    cards.catalog("not_a_real_item_xyz")
    check(False, "an unknown item must not get a default")
except RuntimeError as e:
    check("no catalog" in str(e), "an unknown item stops")
withsize = next(k for k, v in items.items() if v.get("size"))
c = cards.catalog(withsize)
check(c["size"] == [float(x) for x in items[withsize]["size"]] and c["size_source"] == "the catalog",
      f"a catalog size comes through with its source: {withsize} {c['size']}")

# 3. the phone: "<item>: size W x D x H mm" for ANY known item, in mm / cm / in; it wins over the catalog
sent = []
P._reply = lambda t: sent.append(t)
os.makedirs(P.DIR, exist_ok=True)
json.dump([{"id": 1, "text": f"{withsize.replace('_', ' ')}: size 3.4 x 3.4 x 6.1 cm", "photo": None}], open(P.INBOX, "w"))
P.process(log=print, model="stand-in")
g = P.given_size(withsize)
check(g and [round(x, 4) for x in g["size"]] == [0.034, 0.034, 0.061] and "phone" in g["source"],
      f"a size from the phone is written down: {g}")
check(sent and "next" in sent[0], f"and answered: {sent[0]}")
c = cards.catalog(withsize)
check([round(x, 4) for x in c["size"]] == [0.034, 0.034, 0.061] and "phone" in c["size_source"],
      "the given size wins over the catalog")
check(P.queue_first() and P.queue_first()[0] == withsize, "and the item goes first in line")
json.dump([{"id": 2, "text": f"{withsize.replace('_', ' ')}: the 3 x 4 x 5 pack version please", "photo": None}], open(P.INBOX, "w"))
P.process(log=print, model="stand-in")
check([round(x, 4) for x in P.given_size(withsize)["size"]] == [0.034, 0.034, 0.061], "a note with numbers is not a size")

# 4. run.size_gate: a disagreeing size stops the build (Waiting) and asks the phone; a trial only writes it down
run.say = lambda *a, **k: None
phoned = []
run.phone = lambda t: phoned.append(t)
card = {"product": "Duracell D cell, 1998", "size": dcell, "size_source": "the catalog"}
picked = {"file": tall, "mask": tall, "vet": {"view": "front", "whole": True, "count": 1}}
try:
    run.size_gate("t_item", card, picked)
    check(False, "a disagreeing size must stop the build")
except run.Waiting as e:
    check(str(e).startswith("waiting for your size"), f"the build waits for the real size: {str(e)[:60]}")
check(phoned and "size W x D x H mm" in phoned[0] and "t item" in phoned[0], f"and the phone is asked: {phoned[0][:120]}")
st = run.read_status().get("t_item") or {}
check(str(st.get("step", "")).startswith("waiting for your size"), "the status says what it waits for")
check(run._state(st, "t_item")[0] == "you", "the phone page puts it under 'needs you'")
check(not run.size_in("t_item", st), "no size in yet")
P._size_reply("t_item", "size 14.5 x 14.5 x 50.5 mm") if "t_item" in P._known_items() else None
q = run.size_gate("t_item", dict(card, size=aa), picked)
check(q[0][1] is True, f"the agreeing size goes through: {q[0][2][:80]}")
run.TRIAL = True
q = run.size_gate("t_item", card, picked)
check(q[0][1] is False and len(phoned) == 1, "a test build writes the check down, stops nothing, phones nobody")
run.TRIAL = False

# 5. marks counted by name; an auto-pick needs a rival and 3 named marks
v = {"marks_seen": ["PowerCheck tester strip", "Copper and black", "nonsense", "x"], "marks_listed": ["PowerCheck tester strip", "copper and black", "Duracell logo"]}
check(run.marks_seen(v) == 2, f"marks counted only by name against the listed marks: {run.marks_seen(v)}")
check(run.marks_seen({"seen": 5, "marks_listed": ["a", "b"]}) == 0, "a bare count is worth nothing")
check(run.marks_seen({"marks_seen": ["a", "b"], "marks_listed": []}) == 0, "no listed marks: nothing to count")
d = os.path.join(W, "pickd")
os.makedirs(d, exist_ok=True)
run.setting = lambda k, default=True: True
run._item_px = lambda f: 1200
import notes
notes.text = lambda cid: ""
best = {"file": tall, "mask": tall, "vet": {"kind": "photo", "match": 9, "marks_seen": ["PowerCheck tester strip", "copper and black", "Duracell logo"],
                                              "marks_listed": ["PowerCheck tester strip", "copper and black", "Duracell logo"]}}
run.auto_pick("solo", [best], d)
picks = run.jload(os.path.join(run.HB, "picks.json"), {})
check("solo" not in picks, "one candidate alone is never auto-picked")
rival = {"file": tall, "mask": tall, "vet": {"kind": "photo", "match": 5, "marks_seen": []}}
run.auto_pick("pair", [best, rival], d)
picks = run.jload(os.path.join(run.HB, "picks.json"), {})
check(picks.get("pair", {}).get("auto") is True, "a clear winner over a rival is auto-picked")

# 6. pick_gate: the pick's own careful look. Cody's pick stands; an auto-pick that is not exact is un-picked
dos = {"photos": [{"file": tall, "labeled": True, "look_match": "sister", "product_shown": "Duracell AAA 4-pack"}]}
json.dump({"pair": {"pick": "1", "auto": True}, "mine": {"pick": "2"}}, open(os.path.join(run.HB, "picks.json"), "w"))
q = run.pick_gate("mine", dos, {"file": tall})
check(q[0][1] is None and "your pick stands" in q[0][2], f"your own pick stands, the look is shown: {q[0][2][:70]}")
os.makedirs(os.path.join(run.OUT, "pair"), exist_ok=True)
json.dump({"files": [{"file": tall}]}, open(os.path.join(run.OUT, "pair", "candidates.json"), "w"))
try:
    run.pick_gate("pair", dos, {"file": tall})
    check(False, "an auto-pick the look calls sister must be un-picked")
except run.Waiting as e:
    check(str(e).startswith("choosing the photo again"), f"an auto-pick that fails its own look is un-picked: {str(e)[:60]}")
picks = run.jload(os.path.join(run.HB, "picks.json"), {})
shown = run.jload(os.path.join(run.OUT, "pair", "shown.json"), [])
check("pair" not in picks and tall in shown and not os.path.exists(os.path.join(run.OUT, "pair", "candidates.json")),
      "the photo is set aside and the choice is open again")
dos["photos"][0]["look_match"] = "exact"
q = run.pick_gate("pair", dos, {"file": tall})
check(q[0][1] is True, "an exact look passes")

# 7. kit sizes need their numbers in the source; era names need a listing or a photo behind them
check(kitmaker.numbers_missing([14.5, 14.5, 50.5], "AA: 14.5 mm diameter and 50.5 mm long") == [], "mm numbers in the source")
check(kitmaker.numbers_missing([66, 66, 122], "2.6 in wide, 4.83 in tall") == [], "inches in the source count")
check(kitmaker.numbers_missing([66, 66, 122], "a can of soda") == [66, 66, 122], "no numbers: dropped")
kept, dropped = cards.backed_names(["Duracell PowerCheck AA", "Duracell Ultra AA", "Duracell Coppertop AA"],
                                   ["Vintage Duracell PowerCheck AA lot 1996"], [], "Duracell Coppertop AA battery, 1998")
check(kept == ["Duracell PowerCheck AA", "Duracell Coppertop AA"] and dropped == ["Duracell Ultra AA"],
      f"era names from memory alone are dropped: kept {kept}, dropped {dropped}")
kept, dropped = cards.backed_names(["Duracell Ultra AA"], [], ["DURACELL ULTRA"], "Duracell Coppertop AA battery, 1998")
check(kept == ["Duracell Ultra AA"], "a name read on a photo from the era backs itself")

print(f"ALL {ok} PASS")
