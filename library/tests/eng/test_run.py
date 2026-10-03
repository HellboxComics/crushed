"""Unit tests for run.py: status file, locked JSON helper, queue retries, engineer_turn, sync_code, trial isolation,
the Hunyuan test hook."""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

T, HOME, REPO, WORK = C.make("run")
os.environ.update(HOME=HOME, CRUSHED_REMASTER_WORK=WORK)
os.environ.pop("CRUSHED_TRIAL", None)
sys.path.insert(0, os.path.join(REPO, "library"))
import run  # noqa: E402

assert run.WORK == WORK and run.HERE == os.path.join(REPO, "library")
check = C.Check()
SAID = []
_say = run.say
run.say = lambda *a: (SAID.append(" ".join(map(str, a))), _say(*a))

# =========================================================== status.json
print("\n1. status.json: whole-or-nothing writes, a broken file never stops the loop")
os.makedirs(run.OUT, exist_ok=True)
shutil.move(run.STATUS, os.path.join(T, "status-from-setup.json"))
run.status("a", product="A", step="working")
s = json.load(open(run.STATUS))
check(s.get("a", {}).get("step") == "working" and json.load(open(run.STATUS + ".bak")) == s, "written, with a backup")
check(not glob.glob(run.STATUS + ".tmp*"), "no half-written temp file left")
open(run.STATUS, "w").write('{"a": {"step": "wor')                     # what a crash mid-write used to leave
got = run.read_status()
check(got.get("a", {}).get("step") == "working", "a broken status.json: the last good backup is used")
check(run.jload(run.STATUS, {}).get("a", {}).get("step") == "working", "every jload(STATUS) reader recovers too")
run.read_status()
check(len(glob.glob(os.path.join(WORK, "_broken", "status.json-*"))) == 1, "one copy of the broken file is kept")
run.status("b", step="x")
s = json.load(open(run.STATUS))
check(set(s) == {"a", "b"}, "the next write heals the file without losing anything")
real_dump = json.dump


def boom(*a, **k):
    raise OSError("disk full")


run.json.dump = boom
try:
    run.status("c", step="y")
except OSError:
    pass
run.json.dump = real_dump
check(set(json.load(open(run.STATUS))) == {"a", "b"}, "a write that dies half way leaves the old file whole")

print("\n2. the locked read-change-write helper: 4 programs x 50 changes at once lose nothing")
counter = os.path.join(WORK, "counter.json")
code = ("import sys; sys.path.insert(0, %r); import run\n"
        "for _ in range(50):\n"
        "    run.update_json(%r, lambda d: d.__setitem__('n', d.get('n', 0) + 1))\n") % (run.HERE, counter)
ps = [subprocess.Popen([sys.executable, "-c", code], env=C.env_for(HOME, WORK)) for _ in range(4)]
rcs = [p.wait() for p in ps]
check(rcs == [0, 0, 0, 0] and json.load(open(counter))["n"] == 200, f"count is {json.load(open(counter)).get('n')}")

# =========================================================== queue retries
print("\n3. queue: stopped items retried after 1 h, failed ones after 6 h, at most 3 a day; waiting ones left alone")
now = time.time()
items = ["s1", "s2", "f1", "f2", "f3", "w1", "d1", "r1", "k1", "n1"]
open(os.path.join(run.HERE, "queue.txt"), "w").write("\n".join(items) + "\n")
fail = "failed the realism check (print) - not sent to you"
st = {"s1": {"step": "stopped: boom", "at": now - 1800}, "s2": {"step": "stopped: boom", "at": now - 7200},
      "f1": {"step": fail, "at": now - 5 * 3600}, "f2": {"step": fail, "at": now - 7 * 3600},
      "f3": {"step": fail, "at": now - 7 * 3600}, "w1": {"step": "waiting for your pick on your phone (Telegram)"},
      "d1": {"step": "done - kept in your Asset Library"}, "r1": {"step": "3 rounds and none was right"},
      "k1": {"step": "waiting for your Keep or Redo on your phone"}}
run._atomic_json(run.STATUS, st)
run._atomic_json(run.RETRIES, {"f3": [now - 100, now - 200, now - 300], "s2": [now - 90000]})
run._CODE_TIME[:] = [now - 30 * 3600]                 # the code is older than every stop: the waits hold
q = run.queue(20)
check(q == ["s2", "f2", "n1"], f"due now: {q}")
run._CODE_TIME[:] = [now - 600]                       # newer code arrived after s1 stopped: s1 is tried right away
q2 = run.queue(20)
check(q2 == ["s1", "s2", "f1", "f2", "n1"], f"newer code since s1 stopped and f1 failed -> due now: {q2}")
run._CODE_TIME[:] = [now - 30 * 3600]
run.note_retry("s2")
run.note_retry("n1")
r = json.load(open(run.RETRIES))
check(len(r["s2"]) == 1 and "n1" not in r, "a retry is counted (old ones fall off after a day); a new item is not")
check(any("[retry] s2" in x for x in SAID), "the retry is said in the log")
for _ in range(3):
    run.note_retry("f2")
check("f2" not in run.queue(20), "after 3 tries today it waits for tomorrow")

# =========================================================== engineer_turn
print("\n4. engineer_turn: 3 a day; never while its safety rules fail the self-test")
got = [run.engineer_turn("e1") for _ in range(4)]
check(got == [True, True, True, False], f"{got}")
run._atomic_json(os.path.join(WORK, "selftest.json"), {"ok": True, "engineer_guard_ok": False})
check(run.engineer_turn("e2") is False, "safety rules failed -> not used")
os.rename(os.path.join(WORK, "selftest.json"), os.path.join(WORK, "selftest.json.old"))

# =========================================================== sync_code
print("\n5. sync_code on throwaway repo pairs")


def g(*a, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, capture_output=True,
                          text=True)


def pair(name):
    base = os.path.join(T, "sync", name)
    os.makedirs(base)
    o, a, b = (os.path.join(base, n) for n in ("origin.git", "A", "B"))
    g("init", "-q", "--bare", "-b", "main", o, cwd=base)
    g("clone", "-q", o, b, cwd=base)
    for f in ("a.txt", "b.txt", "c.txt", "e.txt"):
        open(os.path.join(b, f), "w").write(f + "\n")
    g("add", "-A", cwd=b)
    g("commit", "-qm", "base", cwd=b)
    g("push", "-q", "origin", "HEAD:main", cwd=b)
    g("clone", "-q", o, a, cwd=base)
    run.ROOT = a
    run.SYNC_STATE = os.path.join(base, "sync_state.json")
    return a, b


def push(b, f, text):
    open(os.path.join(b, f), "w").write(text)
    g("add", "-A", cwd=b)
    g("commit", "-qm", "upstream " + f, cwd=b)
    g("push", "-q", "origin", "HEAD:main", cwd=b)


def head(a, r="HEAD"):
    return g("rev-parse", r, cwd=a).stdout.strip()


trash = os.path.join(HOME, "Desktop", "_to delete")
a, b = pair("behind")
push(b, "b.txt", "new\n")
check(run.sync_code() is True and head(a) == head(a, "@{u}"), "behind only: fast-forwarded")

a, b = pair("ahead")
open(os.path.join(a, "a.txt"), "w").write("local fix\n")
g("commit", "-qam", "local fix", cwd=a)
h = head(a)
check(run.sync_code() is False and head(a) == h, "ahead only: nothing to do")

a, b = pair("diverged")
open(os.path.join(a, "a.txt"), "w").write("local fix\n")
g("commit", "-qam", "local fix", cwd=a)
push(b, "b.txt", "upstream\n")
check(run.sync_code() is True and head(a, "HEAD^") == head(a, "@{u}") and
      open(os.path.join(a, "a.txt")).read() == "local fix\n", "diverged: the local fix is put on top of the newest")

a, b = pair("conflict")
open(os.path.join(a, "c.txt"), "w").write("local\n")
g("commit", "-qam", "local c", cwd=a)
mine = head(a)
push(b, "c.txt", "upstream\n")
check(run.sync_code() is True and head(a) == head(a, "@{u}"), "conflict: the newest version runs")
kept = [x for x in g("branch", "--format=%(refname:short)", cwd=a).stdout.split() if x.startswith("engineer-kept-")]
check(len(kept) == 1 and head(a, kept[0]) == mine, f"conflict: the local fix is kept on {kept}")

a, b = pair("local-edits")
before = set(os.listdir(trash)) if os.path.isdir(trash) else set()
open(os.path.join(a, "e.txt"), "w").write("an edit nobody committed\n")
open(os.path.join(a, "new.txt"), "w").write("my own new file\n")
open(os.path.join(a, "mine-only.txt"), "w").write("not in the way\n")
push(b, "new.txt", "upstream new file\n")
check(run.sync_code() is True and head(a) == head(a, "@{u}"), "local edits: the newest version is in")
saved = sorted(set(os.listdir(trash)) - before) if os.path.isdir(trash) else []
d = os.path.join(trash, saved[0]) if saved else ""
check(len(saved) == 1 and saved[0].startswith("asset-maker-local-edits-"), f"saved to _to delete: {saved}")
check(d and "an edit nobody committed" in open(os.path.join(d, "changes.diff")).read() and
      open(os.path.join(d, "edited", "e.txt")).read() == "an edit nobody committed\n" and
      open(os.path.join(d, "in-the-way", "new.txt")).read() == "my own new file\n" and
      "throw this folder away" in open(os.path.join(d, "NOTE.txt")).read(),
      "the diff, a copy of the edited file, the in-the-way file and a plain note are there")
check(open(os.path.join(a, "new.txt")).read() == "upstream new file\n" and
      open(os.path.join(a, "mine-only.txt")).read() == "not in the way\n", "files not in the way are left alone")

a, b = pair("edits-not-behind")
open(os.path.join(a, "e.txt"), "w").write("work in progress\n")
before = set(os.listdir(trash))
check(run.sync_code() is False and open(os.path.join(a, "e.txt")).read() == "work in progress\n" and
      set(os.listdir(trash)) == before, "nothing newer: local edits are not touched at all")

a, b = pair("stuck")
push(b, "b.txt", "upstream\n")
h = head(a)
open(os.path.join(a, ".git", "index.lock"), "w").write("")       # git refuses every change while this exists
SAID.clear()
r1 = run.sync_code()
r2 = run.sync_code()
said = [x for x in SAID if "could not be added" in x]
check(r1 is False and r2 is False and head(a) == h, "stuck: carries on with the current code (no exit)")
check(len(said) == 1, f"stuck: said once, not every time ({len(said)})")
check(run.read_status().get(run.UPDATE_NOTE, {}).get("step", "").startswith("stopped updating"),
      "stuck: a line on the status page")
check(run.newer_version() is False, "stuck: the loop is not told to stop for that version again")
os.rename(os.path.join(a, ".git", "index.lock"), os.path.join(T, "index.lock.moved"))
check(run.sync_code() is True and head(a) == head(a, "@{u}") and run.UPDATE_NOTE not in run.read_status() and
      not json.load(open(run.SYNC_STATE)), "unstuck: added, the page line and the note are cleared")
run.ROOT = REPO

# =========================================================== trial isolation
print("\n6. a test build writes its card, recipes and dossier into its own folder, never the real ones")
os.makedirs(os.path.join(WORK, "dossier"))
open(os.path.join(WORK, "dossier", C.CID + ".json"), "w").write('{"real": true}')


def tree_hash(p):
    h = hashlib.sha1()
    for f in sorted(glob.glob(os.path.join(p, "**"), recursive=True)):
        if os.path.isfile(f):
            h.update(f.encode() + open(f, "rb").read())
    return h.hexdigest()


real = {p: tree_hash(p) for p in (os.path.join(WORK, "cards"), os.path.join(WORK, "dossier"),
                                  os.path.join(REPO, "library", "factory", "recipes"))}
tdir = os.path.join(T, "trial1")
drv = os.path.join(T, "trial_driver.py")
open(drv, "w").write(f"""
import json, os, sys
sys.path.insert(0, {run.HERE!r})
import run, vet
vet.model = lambda: "fake-judge"
def fake_build(cid, card, picked, others, use, d, mdir, n_found, n_good, **kw):
    import cards, factory
    json.dump(dict(card, touched=True), open(cards.path(cid), "w"))
    json.dump({{"family": "made_in_trial"}}, open(os.path.join(factory.RECIPES, "made_in_trial.json"), "w"))
    dd = os.environ.get("CRUSHED_DOSSIER_DIR", os.path.join(run.WORK, "dossier"))
    json.dump({{"from": "trial"}}, open(os.path.join(dd, cid + ".json"), "w"))
    child = os.popen("python3 -c 'import os; print(os.environ.get(\\"CRUSHED_CARDS_DIR\\"))'").read().strip()
    open(os.path.join(d, "child_saw.txt"), "w").write(child)
    os.makedirs(mdir, exist_ok=True)
    open(os.path.join(mdir, cid + ".glb"), "w").write("model")
    return {{"pass": False, "failed": ["print"]}}
run.build = fake_build
if sys.argv[1] == "judge":
    import types
    vs = types.ModuleType("viewshot")
    vs.shoot = lambda glb, out: (os.path.join(out, "a.jpg"), os.path.join(out, "c.jpg"))
    sys.modules["viewshot"] = vs
    run.make_room = lambda w: None
    def fake_inspect(sheet, photo, product, use, card=None, close=None):
        json.dump({{"card_touched": bool(card.get("touched")), "sheet": sheet}}, open(os.path.join(sys.argv[2], "inspect_saw.json"), "w"))
        return {{"pass": False, "failed": ["details"], "problems": ["x"]}}
    run.inspect = fake_inspect
    print(json.dumps(run.trial({C.CID!r}, sys.argv[2], judge_only=True)))
else:
    print(json.dumps(run.trial({C.CID!r}, sys.argv[2], [])))
""")
env = dict(C.env_for(HOME, WORK), CRUSHED_TRIAL="1")
r = subprocess.run([sys.executable, drv, "build", tdir], env=env, capture_output=True, text=True)
check(r.returncode == 0 and '"failed": ["print"]' in r.stdout, "the test build ran: " + (r.stderr or "")[-300:])
check(all(tree_hash(p) == h for p, h in real.items()), "the real cards, dossier and recipes are unchanged")
check(json.load(open(os.path.join(tdir, "cards", C.CID + ".json"))).get("touched") is True and
      os.path.exists(os.path.join(tdir, "recipes", "made_in_trial.json")) and
      os.path.exists(os.path.join(tdir, "recipes", "alkaline_cylindrical_cell.json")) and
      json.load(open(os.path.join(tdir, "dossier", C.CID + ".json"))) == {"from": "trial"},
      "its card, recipe and dossier writes are in the trial folder (it started from copies)")
check(open(os.path.join(tdir, "child_saw.txt")).read() == os.path.join(tdir, "cards"),
      "programs the test build starts get the same settings")
r = subprocess.run([sys.executable, drv, "judge", tdir], env=env, capture_output=True, text=True)
saw = json.load(open(os.path.join(tdir, "inspect_saw.json"))) if os.path.exists(os.path.join(tdir, "inspect_saw.json")) else {}
check(r.returncode == 0 and "details" in json.load(open(os.path.join(tdir, "judged.json")))["verdict"]["failed"],
      "judge mode writes judged.json: " + (r.stderr or "")[-300:])
check(saw.get("card_touched") is False and saw.get("sheet", "").startswith(os.path.join(tdir, "judge_check")),
      "judge mode uses the item's real card (not the test build's) and its own fresh viewer pictures")

# =========================================================== Hunyuan hook
print("\n7. the Hunyuan test hook")
req = os.path.join(WORK, "hunyuan_test.request")
open(req, "w").write("")
SAID.clear()
run.hunyuan_test_request()
check(any("not installed" in x for x in SAID) and os.path.exists(req + ".done"), "no Hunyuan: said plainly, no crash")
hy = os.path.join(HOME, ".hellbox", "hunyuan3d-mlx")
os.makedirs(os.path.join(hy, "hy3dshape"))
os.makedirs(os.path.join(hy, ".venv", "bin"))
calls_log = os.path.join(T, "hy_calls.log")
fake = os.path.join(hy, ".venv", "bin", "python")
open(fake, "w").write(f"""#!/bin/bash
echo "$@" >> {calls_log}
if [ "$1" = "-c" ]; then exit 1; fi
if [ "$1" = "-m" ]; then exit 0; fi
echo "[hunyuan] test picture: demo.png"
echo "ModuleNotFoundError: No module named 'torchvision'"
exit 1
""")
os.chmod(fake, 0o755)
open(req, "w").write("")
SAID.clear()
_pi = []
_real_pi = run.pip_install
def _fake_pi(python, pkgs, no_deps=False, timeout=900):
    _pi.append((python, list(pkgs), no_deps))
    open(calls_log, "a").write("-m pip install -q " + ("--no-deps " if no_deps else "") + " ".join(pkgs) + "\n")
    return True, "ok"
run.pip_install = _fake_pi
run.hunyuan_test_request()
run.pip_install = _real_pi
log = open(calls_log).read()
check("-m pip install -q --no-deps timm==1.0.27 pygltflib==1.16.3" in log, "only timm and pygltflib, pinned, no "
      "dependencies touched")
check("torch" not in log.replace("torchvision", "") and "--upgrade" not in log, "the PyTorch setup is never touched")
check(any("still missing: torchvision" in x for x in SAID), "what is still missing is said, not installed")
check(any("[hunyuan test] [hunyuan] test picture" in x for x in SAID), "its own log lines are passed on")

check.done()
