"""The brain jobs: the judge is the best thinker; the sorter the fastest of the best SORTERS (reading not counted);
a rule change takes effect from the stored exam without a new exam."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, "/home/claude/crushed/library")
import brainjobs as B

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


ids = [i["id"] for i in B.EXAM]


def mk(oks, sec, think=None):
    r = {"quick": {"score": sum(oks), "seconds": sec * 6, "items": [{"id": i, "ok": bool(o), "seconds": sec}
                                                                     for i, o in zip(ids, oks)]}}
    if think:
        r["think"] = {"score": think[0], "seconds": think[1]}
    return r


res = {"fast_bad": mk([1, 1, 0, 1, 1, 0], 4), "fast_good": mk([1, 1, 1, 1, 1, 0], 5),
       "slow_best": mk([1, 1, 1, 1, 1, 1], 28, (6, 900)), "mid": mk([1, 1, 1, 1, 1, 0], 14, (6, 500))}
j = B.choose(res)
check(j["sort"] == "fast_good", f"sorter: the fastest that gets every sorting question right ({j['sort']}), not the "
      "faster one that lets a D cell through")
check(j["judge"] == "mid", f"judge: best thinking score, then the faster ({j['judge']})")
check(B.choose({}) == {}, "no results -> no jobs (the usual brains are used)")

# a stored exam under older rules: the jobs are worked out again without a new exam
B.inventory = lambda: [{"name": n, "vision": True, "family": n, "params": "", "quant": "", "size_gb": 1,
                        "thinking": True} for n in res]
vis = sorted(res)
import hashlib
key = hashlib.sha1(json.dumps([vis, []]).encode()).hexdigest()[:12]
import time
json.dump({"version": B.VERSION, "key": key, "at": time.time(), "exam": res,
           "jobs": {"judge": "slow_best", "sort": "fast_bad"}}, open(B.OUT, "w"))
B.exam = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no new exam should run"))
got = B.setup(log=print)
check(got == {"judge": "mid", "sort": "fast_good"} and B.job("sort") == "fast_good",
      f"older stored jobs re-worked from the stored exam: {got}")
print(f"\n{ok} checks passed")

# an exam cut short by a restart carries on from where it stopped (only the brains not yet taken sit it)
import importlib
importlib.reload(B)
os.remove(B.OUT)
B.inventory = lambda: [{"name": n, "vision": True, "family": n, "params": "", "quant": "", "size_gb": 1,
                        "thinking": True} for n in res]
B.EXAM = [dict(it, photo="x.jpg") for it in B.EXAM]
B.HUNT = W
open(os.path.join(W, "x.jpg"), "w").close()
asked = []


def fake_one(m, it, think):
    asked.append((m, think))
    good = res[m]["quick"]["items"][[i["id"] for i in B.EXAM].index(it["id"])]["ok"]
    return ({"match": 9, "era_ok": True, "note_ok": False} if good else {"match": 0}) if not it.get("read") else \
        ("JAN 2001" if good else ""), 1.0, 10


B._one = fake_one
B._testing = lambda: False
import vet
vet._call = lambda *a, **k: {}
vet.PREFER = ["slow_best"]
part = {"fast_bad": {"quick": res["fast_bad"]["quick"]}, "fast_good": {"quick": res["fast_good"]["quick"]}}
json.dump({"version": B.VERSION, "key": key, "exam": part}, open(B.OUT + ".partial", "w"))
jobs = B.setup(log=print)
check(not any(m in ("fast_bad", "fast_good") and not t for m, t in asked),
      "the two brains taken before the restart are not asked their quick exam again")
check(any(m == "mid" and not t for m, t in asked) and jobs.get("sort") and jobs.get("judge"),
      f"the rest sat it and the jobs were set: {jobs}")
check(not os.path.exists(B.OUT + ".partial"), "the half-taken exam is cleared once the whole exam is done")
print(f"\n{ok} checks passed")
