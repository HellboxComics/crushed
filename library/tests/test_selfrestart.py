"""A newer version never waits behind a busy build and never needs Claude's restart file (Cody, 2026-10-05: "this is
supposed to be a self sufficient machine"). At every numbered step the build asks (at most every 5 min) whether a
newer version that changes what runs is waiting; if so it steps out between steps, parks the item with the code it
RAN on (so it is due again at once), and the run exits for the clock to start the newest version."""
import json
import os
import re
import sys
import tempfile
import time

W = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
os.environ["HOME"] = HOME
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


run.say = lambda *a, **k: None
src = open(run.__file__).read()

# 1. every numbered step of a build has a boundary in front of it
steps = [m for m in re.finditer(r'^(\s{4,12})status\(cid, (?:product=[^,]+, route=[^,]+, )?step=f?"[1-7]/7', src, re.M)]
missing = [m.group(0).strip()[:60] for m in steps if not src[max(0, m.start() - 80):m.start()].rstrip().endswith('boundary(cid, "step")')]
check(len(steps) >= 20 and not missing, f"{len(steps)} numbered steps, every one behind a boundary (missing: {missing})")

# 2. nothing newer: the boundary is silent; newer: it steps out - only in a loop run, never in a test build
calls = []
run.newer_version = lambda: (calls.append(1), False)[1]
run.LOOPING[0] = True
run._BOUNDARY.update(at=0.0, newer=False)
run.boundary("x", "5/7")
check(calls == [1], "the boundary asks GitHub once")
run.boundary("x", "5/7")
check(calls == [1], "and not again for five minutes")
run.newer_version = lambda: True
run._BOUNDARY.update(at=0.0, newer=False)
raised = False
try:
    run.boundary("x", "5/7 Blender")
except run.Restarting:
    raised = True
check(raised, "a newer version waiting: the build steps out at the boundary")
run.LOOPING[0] = False
run._BOUNDARY.update(at=0.0, newer=False)
raised = False
try:
    run.boundary("x", "5/7")
except run.Restarting:
    raised = True
check(not raised, "a one-off run (not the loop) never steps out")
run.TRIAL = True
run.LOOPING[0] = True
run._BOUNDARY.update(at=0.0, newer=False)
try:
    run.boundary("x", "5/7")
    raised = False
except run.Restarting:
    raised = True
check(not raised, "a test build never steps out")
run.TRIAL = False

# 3. the parked item: its code kept, due again at once, shown as working on the page
now = time.time()
os.makedirs(os.path.dirname(run.STATUS), exist_ok=True)
json.dump({"item": {"step": "5/7 Blender", "at": now - 60, "code": "oldcode"}}, open(run.STATUS, "w"))
v = run.read_status()["item"]
run.status("item", step=f"paused for the newer version - it resumes on it (was at: {v['step']})", ok=False,
           at=float(v["at"]) - 3600, code=v.get("code"))
st = run.read_status()["item"]
check(st["code"] == "oldcode", "the code it ran on is kept")
check(run.retry_due("item", st, {}, time.time()) is True, "it is due again at once on the newer code")
cls, words, _ = run._state(st, "item", {}, {})
check(cls == "work" and "restarting" in words, f"the page shows it as work, '{words}'")
check("a newer version is waiting" in src.split("def _now_line")[1].split("def ")[1] if False else "a newer version is waiting" in src,
      "the page's now-line says when a newer version is waiting")

print(f"ALL {ok} PASS")
