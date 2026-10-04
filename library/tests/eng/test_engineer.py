"""Scripted fake-brain engineer sessions on the Duracell data (no Ollama, no Blender: the brain is a script and the
test builds are fake_trial.py writing scripted verdicts)."""
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

T, HOME, REPO, WORK = C.make("engineer")
os.environ.update(HOME=HOME, CRUSHED_REMASTER_WORK=WORK)
sys.path.insert(0, os.path.join(REPO, "library"))
import engineer as E  # noqa: E402

assert E.ROOT == REPO and E.WORK == WORK, (E.ROOT, E.WORK)
check = C.Check()
FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_trial.py")
SCRIPT = os.path.join(T, "script.json")
os.environ.update(FAKE_SCRIPT=SCRIPT, FAKE_WT=E.WT, FAKE_ROOT=REPO)
BUILD = os.path.join(WORK, "library", C.CID)
CARD = json.load(open(os.path.join(WORK, "cards", C.CID + ".json")))
SHOTS = os.path.join(BUILD, "check", "viewer_around.jpg")
CLOSE = os.path.join(BUILD, "check", "viewer_close.jpg")
PHOTO = os.path.join(BUILD, "label.png")

E._trial_cmd = lambda cid, tdir, clear: [sys.executable, FAKE, cid, tdir, ",".join(clear)]
E._judge_cmd = lambda cid, tdir: [sys.executable, FAKE, "--judge", cid, tdir]
E.brain = lambda: "fake-engineer-brain"
E._judge_model = lambda: "fake-judge"
RELEASED = []
E._release = lambda m: RELEASED.append(m)


def script(trials, judge, **extra):
    for f in glob.glob(SCRIPT + ".*"):
        if ".used-" in f:
            os.remove(f)
        else:
            os.rename(f, f + ".used-" + str(time.time()))
    json.dump(dict({"trials": trials, "judge": judge, "shots_dir": os.path.join(BUILD, "check")}, **extra),
              open(SCRIPT, "w"))


def calls(kind, cid):
    f = f"{SCRIPT}.{kind}.{cid}"
    f += ".n"
    return int(open(f).read()) if os.path.exists(f) else 0


class Brain:
    """Plays a list of turns. A turn is a list of (tool, args) or a function(messages) -> list of (tool, args)."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.messages = None
        self.results = []

    def __call__(self, model, messages, tools, timeout=2400):
        self.messages = messages
        if not self.turns:
            return {"content": "I have no more ideas."}
        t = self.turns.pop(0)
        if callable(t):
            t = t(messages)
        return {"content": "", "tool_calls": [{"function": {"name": n, "arguments": a}} for n, a in t]}

    def tool_results(self):
        return [m["content"] for m in self.messages if m.get("role") == "tool"]


LOG = []


def run(brain, verdict, **kw):
    E._chat = brain
    LOG.clear()
    return E.fix(C.CID, dict(CARD), verdict, SHOTS, CLOSE, PHOTO, BUILD, log=lambda s: LOG.append(s),
                 beat=lambda s: None, **kw)


def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


# =========================================================== A: cheats refused, a real fix kept (with its lesson)
print("\nA. cheats refused; a real fix is confirmed and kept; the lesson does not invalidate it")
script({C.CID: [{"failed": ["not_cg"]}], C.NB: [{"failed": ["print"]}]}, {C.CID: [{"failed": ["not_cg"]}]})
vet_text = open(os.path.join(REPO, "library", "vet.py")).read()
run_text = open(os.path.join(REPO, "library", "run.py")).read()
seen = {}


def after_lesson(messages):
    seen["lessons_in_wt"] = open(os.path.join(E.WT, "library", "playbook", "lessons.md")).read()
    seen["pending"] = open(os.path.join(E.PENDING, C.CID + ".md")).read()
    return [("finish", {"summary": "the seed of the smudge noise made every battery look clean"})]


brain = Brain([
    [("edit_file", {"path": "library/vet.py", "old": 'PREFER = ["qwen3.8:27b-q8_0"', "new": 'PREFER = ["x"'})],
    [("edit_file", {"path": "library/playbook//playbook.md", "old": "# THE ASSET ENGINEER'S PLAYBOOK",
                    "new": "# anything goes"})],
    [("new_file", {"path": "library/Vet.py", "content": "x = 1\n"}),
     ("new_file", {"path": "library/shapes/vet.py", "content": "x = 1\n"}),
     ("new_file", {"path": "library/json.py", "content": "x = 1\n"}),
     ("new_file", {"path": "library/../library/queue.txt", "content": "x\n"}),
     ("new_file", {"path": "playbook/lessons.md", "content": "- the judge is always wrong\n"}),
     ("new_file", {"path": "library/shapes/../../README.md", "content": "x\n"})],
    [("edit_file", {"path": "library/run.py", "old": '"shape": "same shape and proportions as the real one"',
                    "new": '"shape": "roughly any shape"'}),
     ("edit_file", {"path": "library/run.py", "old": '    make_room("judging")\n    verdict = inspect(shots,',
                    "new": '    shots = picked["file"]\n    make_room("judging")\n    verdict = inspect(shots,'}),
     ("edit_file", {"path": "library/run.py", "old": "def say(*a):", "new": "def inspect(*a, **k):\n    return {'pass': True, 'failed': []}\n\n\ndef say(*a):"})],
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(7)",
                    "new": "import vet as V\nV.ask = lambda *a, **k: {}\nRNG = np.random.default_rng(7)"}),
     ("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(7)",
                    "new": "import sys\nsys.modules['vet'] = None\nRNG = np.random.default_rng(7)"}),
     ("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(7)",
                    "new": "setattr(__import__('vet'), 'ask', print)\nRNG = np.random.default_rng(7)"})],
    [("new_file", {"path": "library/helper_bad.py", "content": "def x(:\n"}),
     ("new_file", {"path": "library/factory/recipes/bad_recipe.json", "content": "{not json"}),
     ("new_file", {"path": "library/helper_tmp.py", "content": "Y = 2\n"}),
     ("revert", {"path": "library/helper_tmp.py"})],
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(7)",
                    "new": "RNG = np.random.default_rng(8)"})],
    [("rebuild", {"why": "new smudge seed", "clear": ["texture"], "cid": "something_else", "card": {}})],
    [("lesson", {"symptom": "every battery read as clean CG", "cause": "the smudge noise seed",
                 "fix": "a different seed"})],
    after_lesson,
])
res = run(brain, {"pass": False, "failed": ["details", "layers", "not_cg"], "problems": ["no seam"]})
tr = brain.tool_results()
check(tr[0].startswith("REFUSED") and "locked" in tr[0], "edit to vet.py refused")
check(tr[1].startswith("REFUSED") and "locked" in tr[1], "library/playbook//playbook.md refused")
check(all(r.startswith("REFUSED") for r in tr[2:8]), "new Vet.py / shapes/vet.py / json.py / queue.txt / lessons.md / "
      "outside library all refused: " + " || ".join(r[:70] for r in tr[2:8]))
check(all(r.startswith("REFUSED") for r in tr[8:11]), "run.py: weaker CHECKS, swapped shots, a second inspect() "
      "all refused")
check(all(r.startswith("REFUSED") and "fool the check" in r for r in tr[11:14]),
      "finish.py: V.ask = ..., sys.modules, setattr all refused")
check(tr[14].startswith("REFUSED") and "parse" in tr[14], "a new Python file that does not parse is refused unwritten")
check(tr[15].startswith("REFUSED") and "JSON" in tr[15], "a new JSON file that does not parse is refused")
check(open(os.path.join(REPO, "library", "vet.py")).read() == vet_text, "the real vet.py is untouched")
check(not glob.glob(os.path.join(E.WT, "library", "**", "*.refused"), recursive=True) and
      not glob.glob(os.path.join(E.WT, "library", "**", "*.undone"), recursive=True) and
      not os.path.exists(os.path.join(E.WT, "library", "factory", "recipes", "bad_recipe.json")),
      "no .refused / .undone / refused files inside library/")
check(glob.glob(os.path.join(E.SCRATCH, "*", "bad_recipe.json.refused")) and
      glob.glob(os.path.join(E.SCRATCH, "*", "helper_tmp.py.undone")), "refused and undone files are in scratch/")
check(json.loads(tr[19]).get("failed_now") == ["not_cg"], "rebuild ran with its own item only (extra inputs dropped)")
check("smudge noise seed" not in seen.get("lessons_in_wt", "") and "smudge noise seed" in seen.get("pending", ""),
      "the lesson waits in lessons-pending (not in the code copy) during the session")
check(res.get("kept") is True, f"the fix is kept: {res.get('why')}")
check(calls("trials", C.CID) == 2 and calls("judge", C.CID) == 1, "a second (confirmation) rebuild and the asset "
      f"maker's own check ran (trials {calls('trials', C.CID)}, judge {calls('judge', C.CID)})")
check(calls("trials", C.NB) == 1, "the neighbor item was rebuilt once")
check(len(RELEASED) >= 4 and set(RELEASED) == {"fake-engineer-brain"},
      f"the engineer brain was let go before each test build ({len(RELEASED)} times)")
head = git("log", "-1", "--format=%an|%s")
check(head.startswith("Asset Engineer (your AI)|"), f"the kept fix is a commit in the repo: {head}")
check("default_rng(8)" in open(os.path.join(REPO, "library", "finish.py")).read(), "the repo has the fix")
lessons = open(os.path.join(REPO, "library", "playbook", "lessons.md")).read()
check("smudge noise seed" in lessons, "the lesson went into lessons.md with the kept fix")
check(not os.path.exists(os.path.join(E.PENDING, C.CID + ".md")), "the pending lesson file was used up")
check(res.get("branch", "").startswith("engineer/" + C.CID + "-"), f"unique branch name: {res.get('branch')}")
branch_a = res.get("branch")

# =========================================================== B: set comparison, noise, cached answers, dead ends filed
print("\nB. set comparison; a second rebuild that disagrees is not kept; the same code gets the same answer")
script({C.CID: [{"failed": ["details", "shape"]}, {"failed": ["details"]}, {"failed": ["details", "print"]}]},
       {C.CID: [{"failed": ["details"]}]})
head_before = git("rev-parse", "HEAD")
counts = {}


def finish_again(messages):
    counts["before"] = calls("trials", C.CID)
    return [("finish", {"summary": "again"})]


brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(9)"})],
    [("rebuild", {"why": "seed 9"})],
    [("finish", {"summary": "fewer failures"})],
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(9)",
                    "new": "RNG = np.random.default_rng(10)"})],
    [("rebuild", {"why": "seed 10"})],
    [("lesson", {"symptom": "print smeared", "cause": "seed", "fix": "seed 10"})],
    [("finish", {"summary": "print fixed"})],
    finish_again,
])
res = run(brain, {"pass": False, "failed": ["details", "layers", "print"], "problems": ["smeared"]})
users = [m["content"] for m in brain.messages if m.get("role") == "user"]
check(any("broke checks that passed before: ['shape']" in u for u in users),
      "2 failures vs 3 at first is NOT better when 'shape' newly fails (sets, not counts)")
check(any("did not come out the same" in u for u in users), "a confirmation rebuild that disagrees is not kept")
check(counts.get("before") == calls("trials", C.CID) == 3, "finish again with the same code: same answer, no new "
      f"rebuild ({calls('trials', C.CID)} test builds)")
check(any(u.startswith("Same code as before") for u in users), "the cached answer is said plainly")
check(res.get("kept") is False and git("rev-parse", "HEAD") == head_before, "nothing kept, the repo did not move")
rej = open(E.REJECTED).read()
check("print smeared" in rej and "[not kept]" in rej and "NOT KEPT" in rej, "the lesson is filed as tried-and-not-kept")
check(res.get("branch") != branch_a, f"a new branch for the new session: {res.get('branch')}")
sysmsg = None


def look_system(messages):
    global sysmsg
    sysmsg = messages[0]["content"]
    return [("finish", {"summary": "nothing"})]


run(Brain([look_system]), {"pass": False, "failed": ["print"], "problems": ["x"]})
check("Tried before and NOT kept" in (sysmsg or "") and "print smeared" in (sysmsg or ""),
      "the next session's brain is told what was tried and not kept")

# =========================================================== C: a test build that runs over is stopped with its children
print("\nC. a test build over its time limit is stopped, grandchildren included")
pidf = os.path.join(T, "grandchild.pid")
script({C.CID: [{"hang": True}]}, {}, hang_pid_file=pidf)
E.REBUILD_TIMEOUT = 4
t0 = time.time()
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(11)"})],
    [("rebuild", {"why": "hang"})],
])
res = run(brain, {"pass": False, "failed": ["print"], "problems": ["x"]})
took = time.time() - t0
gpid = int(open(pidf).read()) if os.path.exists(pidf) else None
time.sleep(0.5)
check(gpid is not None and not C.alive(gpid), f"the grandchild ({gpid}) is gone")
check(any("ran over its time limit" in r for r in brain.tool_results()), "the brain is told it ran over")
check(took < 60, f"stopped quickly ({took:.0f} s)")
E.REBUILD_TIMEOUT = 3600

# =========================================================== D: nothing to fix
print("\nD. no session when there is nothing to fix")
attempts = os.path.join(E.ENG, "attempts.json")
json.dump({C.CID: [time.time() - 5]}, open(attempts, "w"))
nb = len(git("for-each-ref", "refs/heads/engineer/").splitlines())
r1 = E.fix(C.CID, CARD, {"pass": False, "problems": "could not inspect: the judge timed out"}, SHOTS, CLOSE, PHOTO,
           BUILD, log=lambda s: None)
r2 = E.fix(C.CID, CARD, {"pass": False, "problems": "?"}, SHOTS, CLOSE, PHOTO, BUILD, log=lambda s: None)
check(r1.get("started") is False and "could not look" in r1["why"], f"judge error: not started ({r1['why'][:80]})")
check(r2.get("started") is False and "no failed check" in r2["why"], "no failed list: not started")
check(len(git("for-each-ref", "refs/heads/engineer/").splitlines()) == nb, "no code copy / branch was made")
check(json.load(open(attempts)).get(C.CID) == [], "the day's try was given back")

# =========================================================== E: a test build that writes where it must not
print("\nE. a test build that changes locked files is caught")
script({C.CID: [{"failed": [], "tamper_wt": True}]}, {C.CID: [{"failed": []}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(12)"})],
    [("rebuild", {"why": "x"})],
    [("finish", {"summary": "all pass"})],
])
res = run(brain, {"pass": False, "failed": ["print"], "problems": ["x"]})
check(res.get("kept") is False and "vet.py" in str(res.get("why")), f"its own copy's vet.py changed by a test build: "
      f"not kept ({str(res.get('why'))[:90]})")
script({C.CID: [{"failed": [], "tamper_root": True}]}, {C.CID: [{"failed": []}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(13)"})],
    [("rebuild", {"why": "x"})],
    [("finish", {"summary": "all pass"})],
])
res = run(brain, {"pass": False, "failed": ["print"], "problems": ["x"]})
check(res.get("kept") is False and "running asset maker's own files" in str(res.get("why")),
      "the running code's vet.py changed by a test build: session stopped, not kept")
subprocess.run(["git", "checkout", "-q", "--", "library/vet.py"], cwd=REPO)
card_path = os.path.join(WORK, "cards", C.CID + ".json")
card_text = open(card_path).read()
script({C.CID: [{"failed": [], "tamper_card": True}]}, {C.CID: [{"failed": []}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(14)"})],
    [("rebuild", {"why": "x"})],
    [("finish", {"summary": "all pass"})],
])
res = run(brain, {"pass": False, "failed": ["print"], "problems": ["x"]})
check(res.get("kept") is False and "your real cards" in str(res.get("why")),
      "a test build that rewrites your real card: session stopped, not kept")
open(card_path, "w").write(card_text)

# =========================================================== G: kept for review when the code moves; never lost
print("\nG. a fix that passes while the code moved is kept on its own branch, and that branch is never reset")
script({C.CID: [{"failed": ["not_cg"]}], C.NB: [{"failed": ["print"]}]}, {C.CID: [{"failed": ["not_cg"]}]})


def code_moves(messages):
    open(os.path.join(REPO, "library", "notes_from_claude.txt"), "w").write("a newer version\n")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=REPO)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "newer"], cwd=REPO)
    return [("finish", {"summary": "seed 15"})]


brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(15)"})],
    [("rebuild", {"why": "x"})],
    code_moves,
])
res = run(brain, {"pass": False, "failed": ["details", "not_cg"], "problems": ["x"]})
kb = res.get("branch", "")
check(res.get("kept") is False and "kept on branch" in str(res.get("why")), f"kept for review: {res.get('why')}")
tip = git("log", "-1", "--format=%an %s", kb)
check(tip.startswith("Asset Engineer (your AI)"), f"the review branch holds the fix: {tip[:80]}")
sha_kb = git("rev-parse", kb)
run(Brain([look_system]), {"pass": False, "failed": ["print"], "problems": ["x"]})
run(Brain([look_system]), {"pass": False, "failed": ["print"], "problems": ["x"]})
check(git("rev-parse", kb) == sha_kb, "two sessions later the review branch is untouched")
check("default_rng(8)" in open(os.path.join(REPO, "library", "finish.py")).read(), "the running code did not take it")

# =========================================================== H: a rebuild with nothing changed
print("\nH. a rebuild with no code change: refused; one redo-from-scratch allowed, the second refused")
script({C.CID: [{"failed": ["shape"]}, {"failed": ["shape"]}]}, {C.CID: [{"failed": ["shape"]}]})
brain = Brain([
    [("rebuild", {"why": "same again"})],
    [("rebuild", {"why": "redo the plan", "clear": ["parts"]})],
    [("rebuild", {"why": "redo the plan once more", "clear": ["parts"]})],
    [("finish", {"summary": "gave up"})],
])
res = run(brain, {"pass": False, "failed": ["shape"], "problems": ["x"]})
tr = brain.tool_results()
check(tr[0].startswith("REFUSED") and "changed nothing" in tr[0], "rebuild with no change and no clear is refused")
check(not tr[1].startswith("REFUSED"), f"the first redo-from-scratch (clear only) runs: {tr[1][:60]}")
check(tr[2].startswith("REFUSED") and "gamble" in tr[2], "a second redo with still no code change is refused")
check(calls("trials", C.CID) == 1, f"only one test build ran ({calls('trials', C.CID)})")

# =========================================================== I: newer code arrives before it changed anything
print("\nI. newer code is in and the engineer has changed nothing: it steps aside, the item is remade on the new code")
script({C.CID: [{"failed": ["shape"]}]}, {C.CID: [{"failed": ["shape"]}]})
brain = Brain([
    [("read_file", {"path": "library/finish.py", "start": 1, "end": 5})],
    [("finish", {"summary": "x"})],
])
res = run(brain, {"pass": False, "failed": ["shape"], "problems": ["x"]}, newer=lambda: True)
check(res.get("newer_code") is True and res.get("kept") is False, f"it steps aside: {res.get('why')}")
check(calls("trials", C.CID) == 0, "no test build was run on the old code")
res = run(Brain([[("finish", {"summary": "x"})]]), {"pass": False, "failed": ["shape"], "problems": ["x"]}, newer=lambda: False)
check(not res.get("newer_code"), "with no newer code it works as before")

# =========================================================== J: fail fast - an unjudged test build
print("\nJ. a test build whose exact checks failed is not judged; its judge checks count as still failing")
script({C.CID: [{"failed": ["measure_size", "not_judged"]}]}, {C.CID: [{"failed": ["measure_size", "not_judged"]}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(31)"})],
    [("rebuild", {"why": "x"})],
    [("finish", {"summary": "x"})],
])
res = run(brain, {"pass": False, "failed": ["measure_size", "shape", "not_cg"], "problems": ["x"]})
tr = brain.tool_results()
rb = json.loads(tr[1])
check(rb.get("not_judged") and rb["failed_now"] == ["measure_size", "not_cg", "shape"],
      f"the rebuild says it was not judged and counts shape/not_cg as still failing: {rb['failed_now']}")
check(res.get("kept") is False, "nothing kept: no failure is gone")
script({C.CID: [{"failed": ["shape"]}, {"failed": ["shape"]}]}, {C.CID: [{"failed": ["shape"]}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "RNG = np.random.default_rng(8)",
                    "new": "RNG = np.random.default_rng(32)"})],
    [("rebuild", {"why": "x"})],
    [("finish", {"summary": "fixed the size"})],
])
res = run(brain, {"pass": False, "failed": ["measure_size", "shape", "not_cg"], "problems": ["x"]})
check(res.get("kept") is True, f"a fix that passes the exact checks and then the judge (fully judged) is kept: {res.get('why')}")

# =========================================================== K: a proven fix is not thrown away
print("\nK. a rebuild that fixed something says KEEP IT; revert of that file is refused unless sure")
script({C.CID: [{"failed": ["side_bottom"]}, {"failed": ["side_bottom"]}]}, {C.CID: [{"failed": ["side_bottom"]}]})
brain = Brain([
    [("edit_file", {"path": "library/finish.py", "old": "def _blur(a, s):",
                    "new": "STEEL_BASE = 0.6\n\n\ndef _blur(a, s):"})],
    [("rebuild", {"why": "steel color"})],
    [("revert", {"path": "library/finish.py"})],
    [("revert", {"path": "all"})],
    [("finish", {"summary": "steel color fixed details"})],
])
res = run(brain, {"pass": False, "failed": ["details", "side_bottom"], "problems": ["x"]})
tr = brain.tool_results()
print("   rebuild said:", tr[1][:300])
check("KEEP IT" in json.loads(tr[1]).get("PROGRESS", ""), "the rebuild result says the change fixed details and to keep it")
check(tr[2].startswith("REFUSED") and "PROVED" in tr[2] and tr[3].startswith("REFUSED"),
      "revert of the proven file, and revert all, are refused")
check(res.get("kept") is True, f"the proven fix is kept at finish: {res.get('why')}")
subprocess.run(["git", "checkout", "-q", "--", "library/finish.py"], cwd=REPO)

# =========================================================== F: context and fingerprint units
print("\nF. units: old tool results are cut short; the run.py fingerprint")
msgs = [{"role": "system", "content": "s"}]
for i in range(12):
    msgs += [{"role": "assistant", "content": ""}, {"role": "tool", "content": "x" * 5000}]
E._prune(msgs)
tools = [m["content"] for m in msgs if m["role"] == "tool"]
check(all(len(c) < 700 and c.endswith(E.CUT_NOTE) for c in tools[:4]) and all(len(c) == 5000 for c in tools[4:]),
      "only the last 8 turns keep full tool results")
fp = E.run_fingerprint(run_text)
check(E.run_fingerprint(run_text.replace("def finish_files(cid, d):", "def finish_files(cid, d):  # x")) == fp,
      "a harmless change elsewhere in run.py is allowed")
check(E.run_fingerprint(run_text.replace('"not_cg": "the surfaces', '"not_cg": "maybe the surfaces')) != fp,
      "a changed check text is caught")
check(E.run_fingerprint(run_text.replace("verdict = inspect(shots, picked[\"file\"], product, use, card=card, close=close)",
                                         "verdict = {\"pass\": True, \"failed\": []}")) != fp, "a faked verdict is caught")
check(E.run_fingerprint(run_text + "\n\ndef build(*a):\n    pass\n") != fp, "a second build() is caught")
check(E.locked("VET.py") and E.locked("Playbook/playbook.md") and not E.locked("factory/recipes/new.json"),
      "case-insensitive locks; recipes stay open")
shadow = os.path.join(E.WT, "library", "shapes", "random.py")
open(shadow, "w").write("x = 1\n")
b = E.Bench(C.CID, CARD, {"failed": ["print"]}, SHOTS, CLOSE, PHOTO, BUILD, log=lambda s: None, beat=lambda s: None)
b._diff_hash()                                           # (marks new files the way a session does)
check("random.py has the same name" in b.audit(), "a file a test build made that shadows a Python module is caught")
os.rename(shadow, os.path.join(T, "random.py.moved"))
check(b.audit() == "", "and the audit is clean again once it is gone")

check.done()
