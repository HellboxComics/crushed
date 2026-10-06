"""The machine picks its own reference photo, always - never a pick on the phone (Cody, 2026-10-05 09:09 and
2026-10-06 15:43: "waiting for your pick on your phone... THIS IS WRONG"). A pick left over from an earlier build
whose photos are gone is replaced."""
import json
import os
import sys
import tempfile

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


os.makedirs(run.HB, exist_ok=True)
d = os.path.join(W, "library", "x_aa")
os.makedirs(d)
said, statuses = [], []
run.say = lambda *a, **k: said.append(" ".join(map(str, a)))
run.status = lambda cid, **k: statuses.append(k.get("step", ""))
run._item_px = lambda c: 500                                    # small: once a reason to ask, now only noted
cands = []
for i in range(2):
    f = os.path.join(W, f"p{i}.jpg")
    Image.new("RGB", (40, 40)).save(f)
    cands.append({"file": f, "mask": f, "vet": {"match": 8, "note": "only the quick look"}})
# a pick from an earlier build, its photos gone
json.dump({"x_aa": {"pick": "3", "at": 1}}, open(os.path.join(run.HB, "picks.json"), "w"))
got = run.your_pick("x_aa", "X AA", cands, d)
check(isinstance(got, dict) and got["file"] == cands[0]["file"], f"the machine picked the top photo itself ({got and os.path.basename(got['file'])})")
check(not any("phone" in s for s in statuses), f"nothing waits for a pick on the phone ({statuses})")
p = json.load(open(os.path.join(run.HB, "picks.json")))["x_aa"]
check(p.get("auto") and "only the quick look" in p.get("weak", []) and any("px tall" in w for w in p["weak"]), f"what makes the photo weak is noted, never asked: {p.get('weak')}")
check(any("[pick] picked by itself" in s for s in said), "the log says it picked by itself")
# a pick for THIS build's candidates stands
got2 = run.your_pick("x_aa", "X AA", cands, d)
check(got2["file"] == cands[0]["file"], "the pick for this build's photos stands on the next call")
print(f"ALL {ok} PASS")
