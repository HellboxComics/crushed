"""S9 - EFFICIENCY (audit 2026-10-04): a real build fails fast too (no judge while an exact check fails, unless
settings say judge_always); the studio pictures are made once, for the build that is filed; a test build writes no
exports, web copy or cutaway; a brain that can't think is asked plainly from then on; the disk is kept clear by moving
old leftovers aside (never deleting)."""
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
import run  # noqa: E402
import vet  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


run.say = lambda *a, **k: None
src = open(run.__file__).read()

# 1. fail fast in real builds, with the switch
check(run.setting("judge_always") is False and run.setting("auto_pick") is True, "judge_always is off by default, the others on")
os.makedirs(W, exist_ok=True)
json.dump({"judge_always": True}, open(os.path.join(W, "settings.json"), "w"))
check(run.setting("judge_always") is True, "and can be turned on")
os.remove(os.path.join(W, "settings.json"))
check('if not m["pass"] and (TRIAL or not setting("judge_always")):' in src, "check_model skips the judge while an exact check fails")

# 2. renders once: the viewer's pictures carry the checks; the studio pictures only as a fallback and at filing time
body = src.split("# 6. CHECK: the viewer's pictures")[1].split("make_room(\"judging\")")[0]
check("if not shots:" in body and "preview.py" in body.split("if not shots:")[1], "the studio render runs only when the viewer shots fail")
check('if not fresh(os.path.join(d, "views.jpg"), built) and os.path.exists(glb_now):' in src, "file_away makes the studio pictures for the filed build")

# 3. a test build writes no exports / web copy / cutaway, and measure does not ask for the web copy
check("if not TRIAL:                                            # (a test build is checked, never filed: no exports," in src,
      "finish_files is skipped in a test build")
check('web_glb=None if TRIAL else os.path.join(mdir, cid + "_web.glb")' in src, "and the web copy is not measured in one")

# 4. a brain that can't think: remembered
import urllib.error
calls = []


def fake_call(path, body, timeout=900):
    calls.append(body.get("think"))
    if body.get("think"):
        raise urllib.error.HTTPError("x", 400, "no think", {}, None)
    return {"message": {"content": '{"a": 1}'}}


vet._call = fake_call
vet._img = lambda p, side=1280: ""
vet._NO_THINK.clear()
vet.ask("plain-brain", "q", [], think=True)
vet.ask("plain-brain", "q", [], think=True)
check(calls == [True, False, False], f"the second question goes plainly at once: {calls}")

# 5. housekeeping: old trial builds and stale leftovers are MOVED to _to delete with a note, once a day
tri = os.path.join(W, "engineer", "trials", "item_a", "20260901-120000")
os.makedirs(tri)
open(os.path.join(tri, "x.txt"), "w").write("old")
old = time.time() - 10 * 86400
os.utime(tri, (old, old))
new = os.path.join(W, "engineer", "trials", "item_a", "20261004-120000")
os.makedirs(new)
st = os.path.join(W, "library", "item_b", "model", "stale-20260801-010101")
os.makedirs(st)
os.utime(st, (old, old))
keep = os.path.join(W, "library", "item_b", "model", "stale-20261004-010101")
os.makedirs(keep)
n = run.housekeeping(log=lambda *a: None)
trash = os.path.join(HOME, "Desktop", "_to delete", "build-leftovers")
moved = [f for d_ in os.listdir(trash) for f in os.listdir(os.path.join(trash, d_))] if os.path.isdir(trash) else []
check(n == 2 and not os.path.exists(tri) and not os.path.exists(st) and os.path.exists(new) and os.path.exists(keep),
      f"old leftovers moved, recent ones kept: {n} moved")
check(any(f.endswith(".txt") for f in moved) and any(f.startswith("trial-item_a") for f in moved) and any(f.startswith("stale-item_b") for f in moved),
      f"each moved with a note: {sorted(moved)}")
os.utime(new, (old, old))
check(run.housekeeping(log=lambda *a: None) == 0 and os.path.exists(new), "once a day: nothing more moved today")

# 6. a run that died mid-item is parked and queued again; the queue is fair (longest wait first)
import json as _j
now = time.time()
_j.dump({"a_item": {"step": "5/7 Blender: mesh + UV map", "at": now - 5 * 3600, "code": "x"},
         "b_item": {"step": "6/7 the judge", "at": now - 600, "code": "x"},
         "c_item": {"step": "waiting for your pick on your phone (Telegram)", "at": now - 9 * 3600, "code": "x"}},
        open(run.STATUS, "w"))
parked = run.park_stale()
st = run.read_status()
check(parked == ["a_item"] and st["a_item"]["step"].startswith("stopped: the run was interrupted while \"5/7 Blender")
      and st["b_item"]["step"].startswith("6/7") and st["c_item"]["step"].startswith("waiting"),
      f"a 5-hour-old 'working' status is parked as interrupted; a recent one and a waiting one are left: {parked}")
check(abs(st["a_item"]["at"] - (now - 5 * 3600)) < 5, "its time is kept, so the retry rules take it again at once")
open(os.path.join(os.path.dirname(run.__file__), "queue.txt")).read() if os.path.exists(os.path.join(os.path.dirname(run.__file__), "queue.txt")) else None
import shutil as _sh
qf = os.path.join(os.path.dirname(run.__file__), "queue.txt")
bak = qf + ".bak-test"
had = os.path.exists(qf)
if had:
    _sh.copy(qf, bak)
open(qf, "w").write("b_item\na_item\nd_item\n")
try:
    _j.dump({"a_item": {"step": "stopped: x", "at": now - 7200, "code": run.code_sha()},
             "b_item": {"step": "stopped: y", "at": now - 3 * 3600, "code": run.code_sha()},
             "d_item": {"step": "stopped: z", "at": now - 5000, "code": run.code_sha()}}, open(run.STATUS, "w"))
    q = run.queue(2)
    check(q == ["b_item", "a_item"], f"the two that waited longest go first, whatever the list order: {q}")
    _j.dump({"a_item": {"step": "stopped: x", "at": now - 7200, "code": run.code_sha()},
             "b_item": {"step": "done - kept", "at": now - 9 * 3600, "code": run.code_sha(), "check_version": "old"}}, open(run.STATUS, "w"))
    q = run.queue(3)
    check(q == ["a_item", "d_item", "b_item"], f"a parked retry, then a never-run item, then a kept item's re-check: {q}")
finally:
    if had:
        _sh.move(bak, qf)
    else:
        os.remove(qf)

print(f"ALL {ok} PASS")
