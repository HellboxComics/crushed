"""YOUR AI, THE ASSET ENGINEER. When a model fails the realism check, it is not sent to you and it is not sent to
Claude: your own AI takes it. It looks at the failed pictures up close, measures the model and its texture maps,
reads the code that built it, works out the CAUSE, fixes the builder or the family recipe (never the one asset by
hand), rebuilds, looks again, and keeps only what really made it better. What it learns goes into
playbook/lessons.md - but only together with a fix that was kept - so the next item of that kind comes out right.

    import engineer
    result = engineer.fix(cid, card, verdict, shots, close, photo, build_dir, log=say, beat=beat)

It works in its OWN copy of the code (a git worktree in ~/crushed-render/remaster/engineer/wt, on a branch named
engineer/<item>-<time>) - the running asset maker is never edited mid-run. A fix is kept only when ALL of this holds:
  - every check that passed before still passes, and at least one failed check now passes;
  - a SECOND rebuild with exactly the same code comes out the same, and the asset maker's own check (its own,
    untouched code, in a separate program) agrees - so a lucky answer from the judge is never kept;
  - other items already built that use the changed files did not start failing a new check;
  - nothing it changed touches the checks (see LOCKED below) - also re-checked after every test build, in case a
    test build changed files by itself.
Kept fixes become a local commit in your repo, by "Asset Engineer (your AI)"; the asset maker then restarts on the
fixed code and rebuilds the item. A fix that can't be added cleanly stays on its own branch for review.

Its brain is the one in settings.json "engineer_brain", otherwise your judge. Hard limits: its own code copy only,
the library folder only, never the checks or the judge, never your finished assets, nothing pushed anywhere, and
3 hours in all (test builds of other items included) - a test build that runs over is stopped with everything it
started (Blender, Hunyuan, browsers).
"""
import ast
import base64
import collections
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "library")
ENG = os.path.join(WORK, "engineer")
WT = os.path.join(ENG, "wt")
SCRATCH = os.path.join(ENG, "scratch")             # its refused / undone / left-over files (never inside library/)
PENDING = os.path.join(ENG, "lessons-pending")     # lessons written during a session, before the fix is kept
REJECTED = os.path.join(ENG, "lessons-rejected.md")  # what was tried and NOT kept, so dead ends aren't repeated
PY = sys.executable
MAX_TURNS = 90
MAX_REBUILDS = 6                       # its own test builds of this item (the confirmation is not counted)
MAX_SECONDS = 3 * 3600                 # the whole session, every test build included
REBUILD_TIMEOUT = 3600                 # one test build at most
JUDGE_TIMEOUT = 1800                   # the asset maker's own check of a test build at most
MIN_RESERVE = 1800                     # time always kept back for the confirmation and the other items
KEEP_PICTURES = 3                      # only the newest few picture sets stay in its memory (the rest it can re-look)
KEEP_FULL_TURNS = 8                    # tool results older than this many turns are cut short
OLD_RESULT_CHARS = 600
AUTHOR = ["-c", "user.name=Asset Engineer (your AI)", "-c", "user.email=engineer@hellbox.local"]

ROUTE_FILES = {                         # which shared files each kind of build uses (for the "still works" check)
    "round": ("shapes/lathe.py", "shapes/realmat.py", "finish.py", "outline.py", "labelart.py", "layout.py",
              "skin.py", "shapes/specs/", "factory/", "labels/", "metal.py", "inks.py"),
    "box": ("skin.py", "panels.py", "eraprint.py", "shapes/carton.py", "shapes/box.py", "finish.py", "factory/"),
    "flat": ("skin.py", "panels.py", "eraprint.py", "shapes/box.py", "finish.py"),
    "pcb": ("shapes/pcb.py", "skin.py", "panels.py", "finish.py"),
    "free": ("hunyuan.py", "shapes/resize.py"),
    "assembly": ("parts.py", "shapes/assembly.py", "shapes/realmat.py", "skin.py", "panels.py"),
    "all": ("run.py", "exports.py", "webglb.py", "viewshot.py", "cutaway.py", "vet.py", "cards.py", "preview.py",
            "shapes/saveall.py"),
}


# ---------------------------------------------------------------- LOCKED: what it may never change
# Paths are inside library/, in lower case (the Mac's disk ignores case: Vet.py IS vet.py there).
LOCKED_FILES = {"vet.py", "viewshot.py", "measure.py", "measure_blender.py", "materials.json", "judge.py",
                "engineer.py", "selftest.py", "watchdog.py", "dossier.py", "facts.py", "notes.py", "queue.txt",
                "families.json", "families.py", "family_library.json", "catalog.py", "era.py", "jsonsafe.py", "speed.py", "brainjobs.py",
                "ownmods.py", "review.py", "labelparts.py", "portal.py", "kitmaker.py"}
# Its rulebook and lessons only. The label layouts (labels/) and measured shapes (shapes/specs/) are BUILD data it
# may correct: the checks never read them (size is checked against the dossier, print against the real photo), and
# a wrong hand-made layout is exactly what it must be able to fix (2026-10-03: the AA label had the big DURACELL
# logo beside the PowerCheck meter; on the real battery they are on opposite sides).
LOCKED_DIRS = ("playbook/",)
# file names no new file may have anywhere in library/ (a copy elsewhere on the search path would be loaded instead)
LOCKED_NAMES = {"vet.py", "viewshot.py", "measure.py", "measure_blender.py", "judge.py", "engineer.py",
                "selftest.py", "watchdog.py", "dossier.py", "facts.py", "notes.py", "run.py", "era.py", "jsonsafe.py",
                "speed.py", "brainjobs.py", "ownmods.py", "review.py", "labelparts.py", "portal.py", "kitmaker.py",
                "sitecustomize.py",
                "usercustomize.py"}
# run.py: the checklist, the judge's question, the test-build verdict and every line that handles the verdict
RUN_PROTECTED = {"CHECKS", "inspect", "verdict", "measure", "judge"}
RUN_FROZEN_DEFS = {"inspect", "trial", "_judge_trial", "_trial_copies", "_atomic_json", "read_json_safe",
                   "update_json", "read_status", "jload"}
RUN_COUNTED = RUN_PROTECTED | {"build", "trial", "TRIAL", "status", "engineer_turn", "jload", "say", "beat"}

# Things a builder never needs and that could fool the check from inside a test build (judged by whether the change
# ADDS any of them compared with the code as it was).
_RISKY_IMPORTS = {"__main__", "builtins", "importlib", "ctypes", "atexit", "gc", "inspect", "runpy", "run",
                  "engineer", "selftest", "watchdog", "judge", "measure", "measure_blender", "dossier", "facts",
                  "viewshot", "ownmods", "review",
                  "sitecustomize", "usercustomize"}
_RISKY_NAMES = {"setattr", "delattr", "globals", "vars", "exec", "eval", "compile", "__import__", "breakpoint",
                "__builtins__"}
_RISKY_ATTRS = {"__dict__", "__code__", "__globals__", "__builtins__", "__defaults__", "__kwdefaults__",
                "__closure__", "__subclasses__", "f_globals", "f_locals", "f_back", "putenv"}
_GUARDED_MODULES = {"vet", "judge", "measure", "viewshot", "run", "__main__", "dossier", "facts", "engineer", "review",
                    "labelparts",
                    "cards", "json", "subprocess", "sys", "os", "shutil", "builtins", "time", "io"}
_MUTATORS = {"append", "extend", "insert", "pop", "remove", "clear", "update", "setdefault", "popitem", "add",
             "discard", "__setitem__", "__delitem__", "sort", "reverse"}
_RISKY_STRINGS = ("trial.json", "judged.json", "status.json", "approvals.json", "picks.json", "Asset Library",
                  "CRUSHED_", ".git", "playbook", "lessons", "heartbeat", "selftest.json", "settings.json")
_INSTALLED = {"bpy", "bmesh", "mathutils", "numpy", "scipy", "pil", "cv2", "torch", "playwright", "trimesh",
              "skimage", "requests", "urllib3", "certifi", "mlx", "transformers", "diffusers"}


# ---------------------------------------------------------------- small helpers

def git(*a, cwd=ROOT, timeout=300):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def jload(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def _update_json(path, change, default=None):
    """Read-change-write one small JSON file under a lock (the same sidecar <file>.lock the asset maker uses), written
    whole or not at all."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            data = jload(path, {} if default is None else default)
            out = change(data)
            data = data if out is None else out
            tmp = f"{path}.tmp-{os.getpid()}"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return data
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def setting(name, default=None):
    return jload(os.path.join(WORK, "settings.json"), {}).get(name, default)


def brain():
    """The engineer's brain: the coding brain the exam chose (brainjobs job "code"), else the judge."""
    sys.path.insert(0, HERE)
    import vet as V
    if setting("engineer_brain"):
        return setting("engineer_brain")
    try:
        import brainjobs
        return brainjobs.job("code") or V.model()
    except Exception:
        return V.model()


def can_see(model):
    """Does this brain take pictures? (Ollama's own capabilities list)"""
    try:
        import urllib.request
        sys.path.insert(0, HERE)
        import vet as V
        req = urllib.request.Request(V.OLLAMA + "/api/show", data=json.dumps({"model": model}).encode(),
                                     headers={"content-type": "application/json"})
        return "vision" in (json.loads(urllib.request.urlopen(req, timeout=30).read()).get("capabilities") or [])
    except Exception:
        return True


def _judge_model():
    sys.path.insert(0, HERE)
    import vet as V
    return V.model()


def _release(model):
    """Let go of a brain's memory now (Ollama's own keep_alive 0) - so a test build can load the judge."""
    try:
        sys.path.insert(0, HERE)
        import vet as V
        V._call("/api/generate", {"model": model, "keep_alive": 0}, timeout=60)
    except Exception:
        pass


def _b64(im, side=1024):
    from PIL import Image
    im = im.convert("RGB")
    if max(im.size) > side:
        im.thumbnail((side, side), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=90)
    return base64.b64encode(b.getvalue()).decode()


def _grid(path):
    """A row of 4 viewer shots (2400 x 600) as 2 x 2, so each view is read bigger."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.width < 3 * im.height:
        return im
    w4 = im.width // 4
    g = Image.new("RGB", (2 * w4, 2 * im.height))
    for i in range(4):
        g.paste(im.crop((i * w4, 0, (i + 1) * w4, im.height)), ((i % 2) * w4, (i // 2) * im.height))
    return g


def _fails(v):
    return list((v or {}).get("failed", [])) if isinstance(v, dict) else []


def _fails_of(v, first):
    """A trial's failures measured against the first (full) check: a test build whose exact checks failed was not
    judged (fail fast) - every judge check that failed at first counts as still failing."""
    f = set(_fails(v))
    if "not_judged" in f:
        f.discard("not_judged")
        f |= {x for x in _fails(first) if not x.startswith("measure_")}
    return f


# which file makes which step, per route - so the engineer opens the right file first instead of reading run.py
# top to bottom (the 3dfx session spent 20 minutes reading run.py before it looked at a single builder)
STEP_FILES = {
    "assembly": ("parts.py (the parts PLAN: what your AI is asked, how its answer is cleaned and fitted - parts_plan.json "
                 "is its output) -> shapes/assembly.py (each part built: box/cylinder/lathe/tube/sphere, form() lofts "
                 "soft parts from outlines, material()+shapes/looks.py the surfaces) -> measure.py (exact checks)"),
    "round": ("skin.py compose/sides (the label unrolled from the photos) -> run.py label_words/whole_words (the "
              "words) -> labelparts.py (what every label of this kind carries) -> layout.py (the label's layout, "
              "rounds, measured color check) -> labelart.py (drawn in exact type) -> shapes/lathe.py + shapes/specs "
              "(the body, the ends, the insides) -> measure.py"),
    "box": ("dossier.py (every side planned: photo / sister / rebuilt) -> skin.py box_skin + panels.py (each side's "
            "art, atlas.png) -> shapes/box.py or shapes/carton.py (the box) -> measure.py"),
    "flat": "skin.py box_skin -> shapes/box.py (a thin box) -> measure.py",
    "pcb": ("skin.py box_skin flat=True (top + solder side straightened) -> run.py board_parts (parts read off the "
            "top photo, parts.json) -> shapes/pcb.py (the board's outline, each part as a solid, bracket) -> measure.py"),
    "organic": "hunyuan.py (shape + paint from the photo) -> shapes/resize.py -> measure.py",
}


def _route_of(card, d):
    if os.path.exists(os.path.join(d, "parts_plan.json")):     # built by the general one-off builder
        return "assembly"
    if os.path.exists(os.path.join(d, "parts.json")):
        return "pcb"
    if os.path.exists(os.path.join(d, "label.png")):
        return "round"
    return (card or {}).get("route", "free")


def _scratch(label):
    """A fresh folder for its own junk (refused files, undone files, left-overs), outside the code."""
    p = os.path.join(SCRATCH, f"{_stamp()}-{re.sub(r'[^A-Za-z0-9_.-]+', '_', label)[:80]}")
    n, q = 1, p
    while os.path.exists(q):
        n += 1
        q = f"{p}-{n}"
    os.makedirs(q)
    return q


def _move_to_scratch(path, label):
    dst = os.path.join(_scratch(label), os.path.basename(path))
    shutil.move(path, dst)
    return dst


def nothing_to_fix(verdict):
    """Why there is nothing for the engineer to work on ('' when there is): no verdict, a pass, or the judge could
    not look at it at all (that is not a builder problem)."""
    if not isinstance(verdict, dict):
        return "there is no check result to work from"
    probs = str(verdict.get("problems") or "")
    if "could not inspect" in probs or "no vision model" in probs:
        return f"the judge could not look at the model ({probs[:200]}) - that is not something to fix in the builder"
    if verdict.get("pass"):
        return "it passed every check"
    if not isinstance(verdict.get("failed"), list) or not verdict.get("failed"):
        return "the check result names no failed check"
    return ""


def _refund_attempt(cid):
    """A session that never started does not use up one of the item's 3 tries for the day."""
    def change(a):
        ts = sorted(t for t in a.get(cid, []) if isinstance(t, (int, float)))
        if ts and time.time() - ts[-1] < 600:
            ts.pop()
        a[cid] = ts
    try:
        _update_json(os.path.join(ENG, "attempts.json"), change)
    except Exception:
        pass


# ---------------------------------------------------------------- running a test build (time limits)

def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _kill_group(p, grace=10):
    """Stop a test build and everything it started (its own process group: Blender, Hunyuan, the viewer's browser)."""
    pgid = p.pid
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            break
        t = time.time()
        while time.time() - t < (grace if sig == signal.SIGTERM else 5):
            p.poll()
            if not _group_alive(pgid):
                break
            time.sleep(0.2)
        if not _group_alive(pgid):
            break
    p.poll()


def run_group(cmd, timeout, log_path, env=None, cwd=None, beat=None):
    """Run one program in its own process group with a hard time limit; on time-out the whole group is stopped.
    Everything it prints goes to log_path. Returns (exit code or None when stopped, seconds taken)."""
    t0 = time.time()
    timeout = max(1, int(timeout))
    with open(log_path, "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, env=env, cwd=cwd, start_new_session=True)
        rc = None
        while True:
            try:
                rc = p.wait(timeout=max(0.2, min(30, timeout - (time.time() - t0))))
                break
            except subprocess.TimeoutExpired:
                if time.time() - t0 >= timeout:
                    _kill_group(p)
                    rc = None
                    break
                if beat:
                    beat()
    if _group_alive(p.pid):                           # anything it left running in the background: stopped too
        _kill_group(p, grace=3)
    return rc, int(time.time() - t0)


def _trial_cmd(cid, tdir, clear):
    """A test build: the item rebuilt with the engineer's code copy and checked (run.py --trial)."""
    return [PY, os.path.join(WT, "library", "run.py"), "--trial", cid, tdir, "--clear", ",".join(clear)]


def _judge_cmd(cid, tdir):
    """The asset maker's OWN check (its own untouched code, a separate program) of a test build's model."""
    return [PY, os.path.join(HERE, "run.py"), "--judge", cid, tdir]


# ---------------------------------------------------------------- its own copy of the code

def _common_dir(cwd):
    r = git("rev-parse", "--git-common-dir", cwd=cwd)
    if r.returncode:
        return None
    d = r.stdout.strip()
    return os.path.realpath(d if os.path.isabs(d) else os.path.join(cwd, d))


def _is_our_worktree():
    return os.path.exists(os.path.join(WT, ".git")) and _common_dir(WT) == _common_dir(ROOT)


def _new_branch(cid):
    base = "engineer/" + re.sub(r"[^a-z0-9_.-]", "_", cid.lower()) + "-" + _stamp()
    name, n = base, 1
    while git("rev-parse", "-q", "--verify", "refs/heads/" + name).returncode == 0:
        n += 1
        name = f"{base}-{n}"
    return name


def _save_leftovers():
    """Changes an earlier session left in its code copy (it stopped half way) are saved to scratch, not thrown away."""
    git("add", "-A", "-N", "--", ".", cwd=WT)
    d = git("diff", "--binary", "HEAD", cwd=WT).stdout
    git("reset", "-q", cwd=WT)
    extra = [f for f in git("ls-files", "--others", "--exclude-standard", "-z", cwd=WT).stdout.split("\0") if f]
    if not d.strip() and not extra:
        return None
    s = _scratch("unfinished-session")
    if d.strip():
        open(os.path.join(s, "changes.diff"), "w").write(d)
    for f in extra:
        os.makedirs(os.path.dirname(os.path.join(s, "files", f)), exist_ok=True)
        shutil.move(os.path.join(WT, f), os.path.join(s, "files", f))
    open(os.path.join(s, "NOTE.txt"), "w").write(
        "Changes your AI's engineer had made in its own copy of the code when a session stopped half way.\n"
        "They were never tested or kept. Safe to throw away.\n")
    return s


def _tidy_branches(keep):
    """Its old session branches that hold nothing new (every commit already in the running code) are removed; any
    branch with a commit of its own is left exactly as it is, for review."""
    out = git("for-each-ref", "--format=%(refname:short)", "refs/heads/engineer/").stdout.split()
    for b in out:
        if b == keep:
            continue
        if git("merge-base", "--is-ancestor", b, "HEAD").returncode == 0:
            git("branch", "-q", "-d", b)


def fresh_worktree(cid):
    """A clean copy of the code exactly as it runs now, on a new branch of its own (never reusing or resetting an
    old branch, so a fix kept for review is never lost). Returns (code version, branch)."""
    os.makedirs(ENG, exist_ok=True)
    git("worktree", "prune")
    sha = git("rev-parse", "HEAD").stdout.strip()
    if not sha:
        raise RuntimeError("could not read which version of the code is running (git rev-parse HEAD)")
    branch = _new_branch(cid)
    if not _is_our_worktree():
        if os.path.lexists(WT):                                   # a leftover folder that is not its code copy
            _move_to_scratch(WT, "old-code-copy")
            git("worktree", "prune")
        r = git("worktree", "add", "-q", "-b", branch, WT, sha)
        if r.returncode:
            raise RuntimeError("could not make the engineer's code copy: " + r.stderr[-300:])
    else:
        _save_leftovers()
        r = git("checkout", "-q", "-f", "-b", branch, sha, cwd=WT)
        if r.returncode:
            raise RuntimeError("could not start the engineer's code copy: " + r.stderr[-300:])
    _tidy_branches(keep=branch)
    return sha, branch


# ---------------------------------------------------------------- the rules for what it changes

def _norm(rel):
    return unicodedata.normalize("NFC", rel.replace(os.sep, "/")).casefold().strip("/")


def locked(rel):
    """rel = a path inside library/ (any case). True when the engineer may never change or create it."""
    r = _norm(rel)
    while "//" in r:
        r = r.replace("//", "/")
    parts = r.split("/")
    if ".." in parts or "." in parts:
        return True
    if r in LOCKED_FILES or any(r == d.rstrip("/") or r.startswith(d) for d in LOCKED_DIRS):
        return True
    name = parts[-1]
    if name in LOCKED_NAMES and r != "run.py":
        return True
    return any(p.startswith(".") for p in parts)                  # .gitignore, .gitattributes, hidden folders


def _binds(node):
    """Names one module-level statement binds."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [(a.asname or a.name).split(".")[0] for a in node.names]
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        targets = [node.target]
    out = []
    for t in targets:
        for n in ast.walk(t):
            if isinstance(n, ast.Name):
                out.append(n.id)
    return out


def _mentions(nodes, names):
    for top in nodes:
        if top is None:
            continue
        for n in ast.walk(top):
            if isinstance(n, ast.Name) and n.id in names:
                return True
            if isinstance(n, ast.Attribute) and n.attr in names:
                return True
            if isinstance(n, ast.alias) and ((n.asname or n.name).split(".")[0] in names):
                return True
            if isinstance(n, (ast.Global, ast.Nonlocal)) and set(n.names) & names:
                return True
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names:
                return True
    return False


def _header(node):
    """The part of a statement that is its own (for a compound statement: its first line, not its body)."""
    if isinstance(node, (ast.If, ast.While)):
        return [node.test]
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [node.target, node.iter]
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return [i.context_expr for i in node.items] + [i.optional_vars for i in node.items]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return list(node.decorator_list) + list(node.args.defaults) + [d for d in node.args.kw_defaults if d]
    if isinstance(node, ast.ClassDef):
        return list(node.decorator_list) + list(node.bases)
    if isinstance(node, ast.Try) or (hasattr(ast, "TryStar") and isinstance(node, ast.TryStar)):
        return [h.type for h in node.handlers if h.type]
    if hasattr(ast, "Match") and isinstance(node, ast.Match):
        return [node.subject]
    return [node]


def run_fingerprint(text):
    """Everything in run.py the engineer may never change, as one string: the checklist, the judge's question, the
    test-build command, the end of build() (pictures, check, verdict), every TRIAL block, every line that touches
    the verdict / checklist / judge, and how often the key names are defined."""
    tree = ast.parse(text)
    parts = []
    counts = collections.Counter(n for node in tree.body for n in _binds(node))
    parts.append("dups " + ",".join(sorted(n for n, c in counts.items() if c > 1)))
    parts.append("counted " + repr(sorted((n, counts[n]) for n in RUN_COUNTED)))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in RUN_FROZEN_DEFS:
            parts.append(ast.dump(node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and set(_binds(node)) & {"CHECKS", "TRIAL"}:
            parts.append(ast.dump(node))
        elif isinstance(node, ast.If) and _mentions([node.test], {"__name__"}):
            parts.append(ast.dump(node))                          # the program's own start (trial / judge modes)
        elif isinstance(node, ast.FunctionDef) and node.name == "build":
            k = next((i for i, s in enumerate(node.body) if isinstance(s, ast.If) and _mentions([s.test], {"route"})),
                     None)
            tail = node.body[k + 1:] if k is not None else node.body
            parts += ["build-tail " + ast.dump(s) for s in tail]
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.name in RUN_PROTECTED:
            parts.append("except-as " + ast.dump(node))
        if not isinstance(node, ast.stmt):
            continue
        if isinstance(node, ast.If) and _mentions([node.test], {"TRIAL"}):
            parts.append("trial-block " + ast.dump(node))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in RUN_PROTECTED:
            parts.append("def " + ast.dump(node))
        own = _header(node)
        if _mentions(own, RUN_PROTECTED):
            parts.append("touches " + "|".join(ast.dump(x) for x in own if x is not None))
    return "\n".join(parts)


def _root(node):
    """(the name a target or call chain starts from, how deep: 0 = the name itself)."""
    depth = 0
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        node = node.func if isinstance(node, ast.Call) else node.value
        depth += 1
    return (node.id if isinstance(node, ast.Name) else None), depth


def risky(text):
    """Counts of the things in one Python file a builder never needs and that could fool the check from inside a
    test build: reaching into the judge's or the asset maker's own modules, replacing functions of shared modules,
    running code from strings, touching the asset maker's own files."""
    tree = ast.parse(text)
    alias, objs = {}, {}
    c = collections.Counter()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                root = a.name.split(".")[0]
                alias[a.asname or root] = root
                if root in _RISKY_IMPORTS:
                    c[f"imports {root}"] += 1
        elif isinstance(n, ast.ImportFrom):
            root = "." if n.level else (n.module or "").split(".")[0]
            if root in _RISKY_IMPORTS:
                c[f"imports from {root}"] += 1
            for a in n.names:
                objs[a.asname or a.name] = root

    def guarded(name):
        m = alias.get(name) or objs.get(name)
        return m if m in _GUARDED_MODULES else None

    docs = set()                                      # docstrings are words for people, not code
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            s = n.body[0]
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                docs.add(id(s.value))
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in _RISKY_NAMES:
            c[f"uses {n.id}"] += 1
        elif isinstance(n, ast.Attribute):
            if n.attr in _RISKY_ATTRS:
                c[f"uses .{n.attr}"] += 1
            if (n.attr in ("modules", "path", "meta_path", "path_hooks") and isinstance(n.value, ast.Name)
                    and alias.get(n.value.id) == "sys"):
                c[f"uses sys.{n.attr}"] += 1
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete)):
            targets = n.targets if isinstance(n, (ast.Assign, ast.Delete)) else [n.target]
            for t in targets:
                for tt in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                    name, depth = _root(tt)
                    m = guarded(name) if name else None
                    if m and depth > 0:
                        c[f"changes something inside {m}"] += 1
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MUTATORS:
            name, depth = _root(n.func.value)
            m = guarded(name) if name else None
            if m and (depth > 0 or name in objs):
                c[f"changes something inside {m}"] += 1
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            for s in _RISKY_STRINGS:
                if s in n.value:
                    c[f"names '{s}'"] += 1
    return c


def _module_stems(skip=None):
    out = set()
    for d, dirs, fs in os.walk(os.path.join(WT, "library")):
        dirs[:] = [x for x in dirs if x != "__pycache__" and not x.startswith(".")]
        for f in fs:
            if f.endswith(".py") and os.path.join(d, f) != skip:
                out.add(f[:-3].casefold())
    return out


def _shadows(path):
    """Would a NEW .py file with this name be loaded instead of another module (Python's own, an installed one, or
    one of the asset maker's)? That would change programs that never import it on purpose."""
    stem = os.path.basename(path)[:-3]
    s = stem.casefold()
    if s in {m.casefold() for m in getattr(sys, "stdlib_module_names", ())} | _INSTALLED:
        return f"{stem}.py has the same name as a module Python or the asset maker already uses"
    if s in _module_stems(skip=path):
        return f"{stem}.py has the same name as another file in library/"
    try:
        import importlib.util
        spec = importlib.util.find_spec(stem)
        if spec is not None:
            return f"{stem}.py has the same name as an installed module"
    except Exception:
        pass
    return ""


def _base_text(rel):
    r = git("show", f"HEAD:{rel}", cwd=WT)
    return r.stdout if r.returncode == 0 else None


def check_change(rel, text, new_file=False):
    """The hard rules for one file's new content (rel = path from the code copy's top, e.g. library/finish.py).
    Returns why it is refused, or ''."""
    lib = rel[len("library/"):] if rel.startswith("library/") else rel
    if locked(lib):
        return (f"{lib} is locked - the checks, the judge, the dossier, the playbook, the queue and the engineer "
                "itself are never yours to change. Fix the builder, the recipe, the label layout (labels/) or the "
                "measured shape (shapes/specs/) instead")
    if not rel.endswith(".py"):
        return ""
    if new_file:
        bad = _shadows(os.path.join(WT, rel))
        if bad:
            return bad + " - pick another name"
    try:
        after = risky(text)
    except SyntaxError as e:
        return f"Python does not parse: {e}"
    base = _base_text(rel)
    before = collections.Counter()
    if base is not None:
        try:
            before = risky(base)
        except SyntaxError:
            pass
    added = sorted(k for k in after if after[k] > before.get(k, 0))
    if added:
        return ("that change does things a builder never needs and that could fool the check from inside a test "
                "build (" + "; ".join(added[:6]) + ") - fix how the model is built, never how it is judged")
    if lib == "run.py":
        try:
            same = base is not None and run_fingerprint(base) == run_fingerprint(text)
        except SyntaxError:
            same = False
        if not same:
            return ("that changes the realism checklist, the judge's question, the test build, the check at the end "
                    "of build(), or a line that handles the verdict - fix the build, not the check")
    return ""


# ---------------------------------------------------------------- the tools it works with

TOOLS = [
    ("look", "Look at pictures. what = 'check' (the model all around in the phone viewer), 'close' (close-ups: top, "
             "bottom, back seam, an edge), 'photo' (the real product photo), 'cutaway' (the model cut open), "
             "'before' (the check shots of the build that failed, for comparison), or a file in the build folder "
             "(e.g. 'label.png', 'label_mr.png', 'skin/back.png', 'model/export/textures/<name>.png'). "
             "box = [left, top, right, bottom] as fractions 0..1 to zoom into part of it.",
     {"what": "string", "box": "array"}, ["what"]),
    ("pixel_stats", "Measure an image (or part of it): size, and per channel mean/min/max/spread on 0..255. For a "
                    "*_mr.png metal/roughness map, G = roughness and B = metallic.",
     {"what": "string", "box": "array"}, ["what"]),
    ("mesh_info", "Measure the built model: every part (object) with its real size in mm, vertex/face counts, and "
                  "its material (base color, metallic, roughness, clearcoat, which texture maps are connected).",
     {}, []),
    ("list_files", "List files in a folder of the code (e.g. 'library', 'library/shapes', 'library/factory/recipes') "
                   "or of the build folder (prefix 'build/').", {"path": "string"}, ["path"]),
    ("read_file", "Read a code or data file (lines start..end, at most 400 lines at a time). Prefix 'build/' to read "
                  "a file from the build folder (e.g. 'build/shape.json', 'build/parts.json').",
     {"path": "string", "start": "integer", "end": "integer"}, ["path"]),
    ("grep", "Search the code for a regular expression; returns file:line: text.",
     {"pattern": "string", "path": "string"}, ["pattern"]),
    ("edit_file", "Change a file in YOUR copy of the code: replace the exact text old (must appear exactly once, "
                  "copy it from read_file without the line numbers) with new. Python must still compile and JSON "
                  "must still parse, or the edit is refused. Locked files (the checks, the judge, the dossier, "
                  "the playbook, the queue) are refused; builders, recipes, label layouts (labels/) and measured "
                  "shapes (shapes/specs/) are yours to fix.",
     {"path": "string", "old": "string", "new": "string"}, ["path", "old", "new"]),
    ("new_file", "Create a NEW file in your copy of library/ (a helper module, a recipe). It may not share a name "
                 "with another module.",
     {"path": "string", "content": "string"}, ["path", "content"]),
    ("diff", "Show every change you have made so far.", {}, []),
    ("revert", "Undo your changes to one file (path), or all of them (path = 'all'). A change your last rebuild proved "
               "(it fixed a failure and broke nothing) is not undone unless sure=true.",
     {"path": "string", "sure": "boolean"}, ["path"]),
    ("rebuild", "Rebuild this item with YOUR copy of the code and run the realism check again (takes minutes). "
                "clear = cached steps to redo instead of reuse: 'skin' (box faces from photos), 'texture' (label "
                "art), 'dossier' (what it knows about the item: every side, its facts and their receipts), 'construction' (how it is made), 'parts' "
                "(circuit card parts). Clear a step whenever you changed the code that makes it.",
     {"clear": "array", "why": "string"}, ["why"]),
    ("lesson", "Write down what you learned: the symptom you saw, its cause, the fix. It goes into the playbook "
               "only if your fix is kept; if not, it is filed under 'tried and not kept'.",
     {"symptom": "string", "cause": "string", "fix": "string"}, ["symptom", "cause", "fix"]),
    ("compare_colors", "MEASURE two pictures against each other, part by part (a 20 x 10 grid): the share of parts "
                       "whose color matches and a list of the parts that differ, in words ('x 0.00-0.30 is copper in "
                       "picture 2 but black in picture 1'). Light and shade don't count as a different color. Use it "
                       "on a drawn label vs the real one (e.g. 'texture/round1.png' vs 'texture/real.png'), or a "
                       "model side vs its photo - a measurement, never a guess.",
     {"a": "string", "b": "string"}, ["a", "b"]),
    ("read_words", "Read the printed words off a picture with the text reader (and the vision brain, twice): the "
                   "lines it can read. Use it to check what a label or a model side really says.",
     {"what": "string"}, ["what"]),
    ("ask_eyes", "Ask the vision brain a specific question about a picture (any 'what' that look accepts) and get "
                 "its answer in words - e.g. 'Is the copper band at the top or the bottom end?', 'Which words are "
                 "cut off?'. Use it when you need eyes on a detail; measure with compare_colors / pixel_stats when "
                 "a number will do.",
     {"what": "string", "question": "string", "box": "array"}, ["what", "question"]),
    ("review_sheet", "The build's review sheet: every step's own checks in order (unrolled photos, words, label "
                     "tries, box sides, finished model) and the FIRST step that went wrong, with its pictures' "
                     "names (look at them with look('step:<file name>')).", {}, []),
    ("finish", "You are done: every check passes, or you made it as good as you can. Say what you changed and why, "
               "and what (if anything) is still wrong and its likely cause. Your fix is then confirmed by a second "
               "rebuild and the asset maker's own check before it is kept.", {"summary": "string"}, ["summary"]),
]


def tool_specs():
    out = []
    for name, desc, props, req in TOOLS:
        P = {}
        for k, t in props.items():
            P[k] = {"type": t} if t != "array" else {"type": "array", "items": {"type": "string" if k == "clear" else "number"}}
        out.append({"type": "function", "function": {"name": name, "description": desc,
                                                       "parameters": {"type": "object", "properties": P, "required": req}}})
    return out


PROBE = r'''
import bpy, json, sys
glb = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
out = []
for ob in bpy.context.scene.objects:
    if ob.type != "MESH":
        continue
    bb = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
    dims = [round((max(v[i] for v in bb) - min(v[i] for v in bb)) * 1000, 2) for i in range(3)]
    mats = []
    for slot in ob.material_slots:
        m = slot.material
        if not m:
            continue
        info = {"name": m.name}
        if m.use_nodes:
            p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if p:
                def val(k):
                    s = p.inputs.get(k)
                    if s is None:
                        return None
                    if s.is_linked:
                        n = s.links[0].from_node
                        while n.type not in ("TEX_IMAGE",) and n.inputs and any(i.is_linked for i in n.inputs):
                            n = next(i for i in n.inputs if i.is_linked).links[0].from_node
                        img = getattr(n, "image", None)
                        return "map " + (f"{img.name} {img.size[0]}x{img.size[1]}" if img else n.type)
                    v = s.default_value
                    try:
                        return [round(x, 3) for x in v]
                    except TypeError:
                        return round(v, 3)
                for k in ("Base Color", "Metallic", "Roughness", "Normal", "Coat Weight", "Coat Roughness",
                          "Transmission Weight", "Alpha"):
                    info[k] = val(k)
        mats.append(info)
    out.append({"part": ob.name, "size_mm": dims, "verts": len(ob.data.vertices), "faces": len(ob.data.polygons),
                "materials": mats, "extras": {k: ob[k] for k in ob.keys() if not k.startswith("_")}})
print("PROBE" + json.dumps(out, default=str))
'''


def _hash(p):
    try:
        return hashlib.sha1(open(p, "rb").read()).hexdigest()
    except OSError:
        return "gone"


def _root_watch():
    """What the running asset maker's own code looks like on disk outside its commits (edits and new files in
    library/, Python files anywhere) plus the real item cards - so a test build that writes into them is caught at
    once. None when git can't tell (then this extra watch is skipped and said in the log)."""
    try:
        st = git("status", "--porcelain", "-z", "-uall", "--no-renames", cwd=ROOT, timeout=120)
    except Exception:
        return None
    if st.returncode:
        return None
    out = {}
    for e in st.stdout.split("\0"):
        if len(e) < 4:
            continue
        rel = e[3:]
        if rel.startswith("library/") or rel.casefold().endswith((".py", ".pth")):
            out[rel] = _hash(os.path.join(ROOT, rel))
    cards = os.path.join(WORK, "cards")
    if os.path.isdir(cards):
        for n in os.listdir(cards):
            if n.endswith(".json"):
                out["(your cards) " + n] = _hash(os.path.join(cards, n))
    return out


class Bench:
    """Everything the engineer can see and touch for one item."""

    def __init__(self, cid, card, verdict, shots, close, photo, build_dir, log, beat, base=None):
        self.cid, self.card, self.log, self.beat = cid, card or {}, log, beat
        self.photo = photo
        self.base = base
        self.first = {"verdict": verdict, "shots": shots, "close": close, "dir": build_dir}
        self.cur = dict(self.first)                    # the latest build (the failed one until it rebuilds)
        self.trials = []
        self.pictures = []                             # images waiting to go to its eyes with the next message
        self.done = None
        self.lessons = []
        self.accepted = None
        self.redo_only = 0                             # the one rebuild allowed with no code change (a step redone)
        self.proven = None                             # the last code that fixed something and broke nothing
        self.decided = {}                              # code version (diff hash) -> (kept?, why): never re-rolled
        self.stopped = None                            # set when the session must stop at once
        self.model = None
        self.judge = None
        self.t0 = time.time()
        self.deadline = self.t0 + MAX_SECONDS
        self.watch = _root_watch()
        if self.watch is None:
            log("[engineer] (git could not list the running code's changed files - the extra watch on it is off)")

    # -- time
    def left(self):
        return self.deadline - time.time()

    def _longest(self):
        return max([t["took"] for t in self.trials] or [900])

    def reserve(self):
        """Time kept back so a good fix can always be confirmed (a second rebuild, the asset maker's own check and
        up to two other items)."""
        return int(min(MAX_SECONDS / 2, max(MIN_RESERVE, 3.5 * self._longest() + 300)))

    # -- seeing
    def _file(self, what):
        what = (what or "").strip()
        named = {"check": self.cur.get("shots"), "close": self.cur.get("close"), "photo": self.photo,
                 "before": self.first.get("shots"), "before_close": self.first.get("close"),
                 "cutaway": os.path.join(self.cur["dir"], "check", "cutaway.png")}
        if what.startswith("step:"):                       # a picture from the review sheet, by its file name
            want = what[5:].strip()
            try:
                steps = json.load(open(os.path.join(self.cur["dir"], "review.json"))).get("steps", [])
            except Exception:
                steps = []
            p = next((f for s in steps for f in s.get("files", []) if os.path.basename(f) == want), None)
        elif what in named:
            p = named[what]
        else:
            p = os.path.realpath(os.path.join(self.cur["dir"], what.removeprefix("build/")))
            if not p.startswith(os.path.realpath(self.cur["dir"])) and not p.startswith(os.path.realpath(WORK)):
                raise ValueError("only files in the build folder")
        if not p or not os.path.exists(p):
            raise FileNotFoundError(f"{what}: no such picture" + (" (this build made none)" if what in named else ""))
        return p

    def _crop(self, im, box):
        if not box:
            return im
        x0, y0, x1, y1 = [max(0.0, min(1.0, float(b))) for b in box[:4]]
        if x1 <= x0 or y1 <= y0:
            raise ValueError("box must be [left, top, right, bottom] with left<right, top<bottom")
        W, H = im.size
        return im.crop((int(x0 * W), int(y0 * H), max(int(x1 * W), int(x0 * W) + 8), max(int(y1 * H), int(y0 * H) + 8)))

    def look(self, what, box=None):
        from PIL import Image
        p = self._file(what)
        if what not in ("check", "close", "before", "before_close"):
            try:
                Image.open(p).close()
            except Exception:
                have = [n for n, f in {"check": self.cur.get("shots"), "close": self.cur.get("close"),
                                       "photo": self.photo}.items() if f and os.path.exists(str(f))]
                return (f"{os.path.basename(p)} is not a picture (a model or data file), so there is nothing to look "
                        f"at in it. To SEE the model, look at {' / '.join(repr(h) for h in have)} (its sides, lit, "
                        f"next to the real photo) or a picture named on the review sheet (look 'step:<file>'); for "
                        f"its numbers use mesh_info.")
        im = _grid(p) if what in ("check", "close", "before", "before_close") else Image.open(p)
        im = self._crop(im, box)
        if box and max(im.size) < 1024:                # zoomed: shown bigger
            s = 1024 / max(im.size)
            im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        self.pictures.append((f"{what}" + (f" zoomed to {box}" if box else ""), _b64(im)))
        w, h = Image.open(p).size
        return f"looking at {what} ({os.path.basename(p)}, {w}x{h} px)" + \
               (f", zoomed to {box}" if box else "") + " - the picture comes with the next message."

    def compare_colors(self, a, b):
        import layout
        pa, pb = self._file(a), self._file(b)
        share, fixes = layout.color_check(pa, pb)
        return json.dumps({"colors_match": round(share, 2),
                           "differences": [f.replace("on the real label", "in picture 2").replace("in yours", "in picture 1")
                                           for f in fixes][:12]})

    def read_words(self, what):
        import measure
        p = self._file(what)
        lines = []
        try:
            lines = measure.read_lines(p)
        except Exception:
            pass
        try:
            txt = measure.read_text(p, use=self.judge)
        except Exception as e:
            txt = f"(the vision brain could not read it: {e})"
        return json.dumps({"text_reader": lines[:40], "vision_brain": str(txt)[:1500]})

    def ask_eyes(self, what, question, box=None):
        from PIL import Image
        sys.path.insert(0, HERE)
        import vet as V
        p = self._file(what)
        im = self._crop(Image.open(p), box)
        tmp = os.path.join(ENG, "eyes.png")
        im.convert("RGB").save(tmp)
        q = (f"Look at this picture carefully and answer in plain words, in at most 80 words. {question} "
             'Answer ONLY JSON: {"answer": "..."}')
        try:
            v = V.ask(self.judge or V.model(), q, [tmp], think=False, side=1280) or {}
            return str(v.get("answer") or v)[:1200]
        except Exception as e:
            return f"the vision brain could not answer: {e}"

    def review_sheet(self):
        import review
        if not os.path.exists(os.path.join(self.cur["dir"], "review.json")):
            return "this build wrote no review sheet"
        return review.load(self.cur["dir"]).text()

    def pixel_stats(self, what, box=None):
        import numpy as np
        from PIL import Image
        p = self._file(what)
        im = self._crop(Image.open(p), box)
        a = np.asarray(im.convert("RGBA" if im.mode in ("RGBA", "LA") else "RGB")).astype(float)
        names = "RGBA"[:a.shape[2]]
        rows = {n: {"mean": round(a[..., i].mean(), 1), "min": int(a[..., i].min()), "max": int(a[..., i].max()),
                    "spread": round(a[..., i].std(), 1)} for i, n in enumerate(names)}
        return json.dumps({"file": os.path.basename(p), "size": im.size, "channels": rows})

    def mesh_info(self):
        glb = os.path.join(self.cur["dir"], "model", self.cid + ".glb")
        if not os.path.exists(glb):
            return "no model file in this build"
        if self.left() < 120:
            return "REFUSED: out of time"
        probe = os.path.join(ENG, "probe.py")
        open(probe, "w").write(PROBE)
        log = os.path.join(ENG, "probe.log")
        rc, _ = run_group([PY, probe, "--", glb], min(600, self.left() - 60), log)
        txt = open(log, errors="replace").read()
        m = re.search(r"PROBE(.*)", txt)
        if not m:
            return "could not measure: " + ("it ran over its time limit" if rc is None else txt[-500:])
        return json.dumps(json.loads(m.group(1)))[:9000]

    # -- reading code
    def _readable(self, path):
        rel = (path or "").strip().lstrip("/")
        if rel.startswith("wt/"):
            rel = rel[3:]
        if not rel.startswith("library") and not os.path.exists(os.path.join(WT, rel)):
            rel = os.path.join("library", rel)
        p = os.path.realpath(os.path.join(WT, rel))
        base = os.path.realpath(WT)
        if not (p == base or p.startswith(base + os.sep)) or "/.git" in p[len(base):]:
            raise ValueError(f"{rel}: outside what you may read")
        return p

    def _writable(self, path):
        """(real path, path from the code copy's top) - only inside library/, never through a link."""
        rel = (path or "").strip().replace("\\", "/").lstrip("/")
        if rel.startswith("wt/"):
            rel = rel[3:]
        if rel != "library" and not rel.startswith("library/"):
            rel = "library/" + rel
        top = os.path.realpath(WT)
        base = os.path.join(top, "library")
        full = os.path.normpath(os.path.join(top, rel))
        real = os.path.realpath(full)
        if not real.startswith(base + os.sep):
            raise ValueError(f"{path}: outside library/ (you may only change files in library/)")
        if real != full:
            raise ValueError(f"{path}: goes through a link - not allowed")
        return real, os.path.relpath(real, top).replace(os.sep, "/")

    def list_files(self, path):
        if path.startswith("build"):
            base = os.path.join(self.cur["dir"], path[5:].lstrip("/"))
            if not os.path.realpath(base).startswith(os.path.realpath(self.cur["dir"])):
                raise ValueError("only inside the build folder")
        else:
            base = self._readable(path)
        out = []
        for n in sorted(os.listdir(base)):
            if n.startswith(".") or n == "__pycache__":
                continue
            f = os.path.join(base, n)
            out.append(n + ("/" if os.path.isdir(f) else f"  ({os.path.getsize(f)} bytes)"))
        return "\n".join(out[:300])

    def read_file(self, path, start=1, end=None):
        if path.startswith("build/"):
            p = os.path.realpath(os.path.join(self.cur["dir"], path[6:]))
            if not p.startswith(os.path.realpath(self.cur["dir"])):
                raise ValueError("only inside the build folder")
        else:
            p = self._readable(path)
        lines = open(p, errors="replace").read().splitlines()
        start = max(1, int(start or 1))
        end = min(len(lines), int(end or start + 199), start + 399)
        body = "\n".join(f"{i:5d}  {lines[i - 1]}" for i in range(start, end + 1))
        return f"{path} lines {start}-{end} of {len(lines)}\n{body}"

    def grep(self, pattern, path="library"):
        base = self._readable(path or "library")
        rx = re.compile(pattern)
        hits = []
        files = [base] if os.path.isfile(base) else [os.path.join(d, f) for d, _, fs in os.walk(base)
                                                     if "__pycache__" not in d and "/.git" not in d for f in fs
                                                     if f.endswith((".py", ".json", ".md", ".txt"))]
        for f in sorted(files):
            try:
                for i, line in enumerate(open(f, errors="replace"), 1):
                    if rx.search(line):
                        hits.append(f"{os.path.relpath(f, WT)}:{i}: {line.rstrip()[:200]}")
                        if len(hits) >= 80:
                            return "\n".join(hits) + "\n(first 80 hits)"
            except Exception:
                continue
        return "\n".join(hits) or "no matches"

    # -- changing code (its own copy only)
    def _check_file(self, p):
        if p.endswith(".py"):
            r = subprocess.run([PY, "-m", "py_compile", p], capture_output=True, text=True, timeout=120)
            if r.returncode:
                return "Python does not compile: " + (r.stderr or "")[-600:]
        if p.endswith(".json"):
            try:
                json.load(open(p))
            except Exception as e:
                return f"JSON does not parse: {e}"
        return None

    def edit_file(self, path, old, new):
        try:
            p, rel = self._writable(path)
        except ValueError as e:
            return f"REFUSED: {e}"
        if locked(rel[len("library/"):]):
            return "REFUSED: " + check_change(rel, "")
        if not os.path.isfile(p):
            return f"REFUSED: {rel} does not exist (use new_file for a new file)"
        text = open(p).read()
        n = text.count(old) if old else 0
        how = ""
        if n == 0 and old.strip():
            # the same text with different spacing (it typed 4 spaces where the file has 1): found exactly once while
            # ignoring spacing, it is the same place - 2026-10-03 a whole session went on edits refused for spacing
            # alone. Its new text is set at the file's own indent there.
            olines = old.strip("\n").split("\n")
            words = lambda ln: r"[ \t]+".join(re.escape(w) for w in ln.split())
            pat = r"[ \t]*\r?\n[ \t]*".join(words(ln) for ln in olines if ln.strip())
            hits = list(re.finditer(pat, text))
            if len(hits) == 1:
                h = hits[0]
                ls = text.rfind("\n", 0, h.start()) + 1                  # where its first line starts
                at_line_start = text[ls:h.start()].strip() == ""
                file_indent = re.match(r"[ \t]*", text[ls:]).group(0) if at_line_start else ""
                old_indent = re.match(r"[ \t]*", olines[0]).group(0)
                nl = new.strip("\n").split("\n")
                out = [nl[0].lstrip(" \t") if at_line_start else nl[0]]
                out += [file_indent + ln[len(old_indent):] if ln.startswith(old_indent) else ln for ln in nl[1:]]
                start = ls + len(file_indent) if at_line_start else h.start()
                old, new, n = text[start:h.end()], "\n".join(out), 1
                how = " (found by ignoring spacing; your new text was set at the file's own indent)"
        if n != 1:
            near = ""
            key = (old.strip().splitlines() or [""])[0].strip()[:60]
            if key:
                near = "\n".join(f"  line {i}: {l.strip()[:160]}" for i, l in enumerate(text.splitlines(), 1)
                                 if key[:40] in l)[:1500]
            return (f"REFUSED: the old text appears {n} times in {rel} (it must appear exactly once - copy it exactly "
                    f"from read_file, without line numbers)." + (f" Lines that look like it:\n{near}" if near else ""))
        new_text = text.replace(old, new)
        bad = check_change(rel, new_text)
        if bad:
            return "REFUSED: " + bad
        open(p, "w").write(new_text)
        bad = self._check_file(p)
        if bad:
            open(p, "w").write(text)
            return "REFUSED (put back as it was): " + bad
        return f"changed {rel}{how}"

    def new_file(self, path, content):
        try:
            p, rel = self._writable(path)
        except ValueError as e:
            return f"REFUSED: {e}"
        if locked(rel[len("library/"):]):
            return "REFUSED: " + check_change(rel, "")
        tracked = git("ls-files", "--error-unmatch", rel, cwd=WT).returncode == 0
        if os.path.exists(p) and tracked:
            return f"REFUSED: {rel} already exists - use edit_file"
        if os.path.isdir(p):
            return f"REFUSED: {rel} is a folder"
        bad = check_change(rel, content, new_file=not os.path.exists(p))
        if bad:
            return "REFUSED: " + bad
        os.makedirs(os.path.dirname(p), exist_ok=True)
        old = open(p).read() if os.path.exists(p) else None
        open(p, "w").write(content)
        bad = self._check_file(p)
        if bad:
            keep = os.path.join(_scratch("refused-" + rel), os.path.basename(p) + ".refused")
            shutil.move(p, keep)                      # kept for a look, outside the code
            if old is not None:
                open(p, "w").write(old)
            return "REFUSED: " + bad
        return f"wrote {rel}"

    def diff(self):
        git("add", "-A", "-N", "--", "library", cwd=WT)
        d = git("diff", "HEAD", "--", "library", ":(exclude)library/playbook", cwd=WT).stdout
        return (d[:12000] + ("\n(diff cut short)" if len(d) > 12000 else "")) or "no changes yet"

    def revert(self, path, sure=False):
        proven = getattr(self, "proven", None)
        if proven and not sure and (path == "all" or any(
                os.path.normpath(path.strip().lstrip("/")).removeprefix("wt/").removeprefix("library/") ==
                os.path.normpath(f).removeprefix("library/") for f in proven["files"])):
            return (f"REFUSED: that change is part of the fix your last rebuild PROVED (it fixed {proven['fixed']} and "
                    "broke nothing). Undoing it throws that away. Keep it and add your next change on top; or call "
                    "finish now and it is kept. If you truly mean to undo it, call revert again with sure=true.")
        if path == "all":                                       # its whole code copy, back as it was
            git("reset", "-q", cwd=WT)
            git("checkout", "-q", "--", ".", cwd=WT)
            extra = [f for f in git("ls-files", "--others", "--exclude-standard", "-z", cwd=WT).stdout.split("\0") if f]
            if extra:
                s = _scratch("undone-new-files")
                for f in extra:
                    os.makedirs(os.path.dirname(os.path.join(s, f)), exist_ok=True)
                    shutil.move(os.path.join(WT, f), os.path.join(s, f + ".undone"))
            return "every change undone"
        try:
            p, rel = self._writable(path)
        except ValueError as e:
            return f"REFUSED: {e}"
        if git("ls-files", "--error-unmatch", rel, cwd=WT).returncode == 0:
            git("reset", "-q", "--", rel, cwd=WT)
            git("checkout", "-q", "--", rel, cwd=WT)
        elif os.path.exists(p):
            git("reset", "-q", "--", rel, cwd=WT)
            shutil.move(p, os.path.join(_scratch("undone-" + rel), os.path.basename(p) + ".undone"))
        return f"{rel} is back as it was"

    def _diff_hash(self):
        """Which code is being tested: every change in library/ except the playbook (so writing a lesson never makes
        a tested fix look untested)."""
        git("add", "-A", "-N", "--", "library", cwd=WT)
        d = git("diff", "--binary", "HEAD", "--", "library", ":(exclude)library/playbook", cwd=WT).stdout
        return hashlib.sha1(d.encode()).hexdigest()

    def changed(self):
        """Every path changed in its code copy (from the top of the code), with git's two status letters."""
        out = []
        st = git("status", "--porcelain", "-z", "-uall", "--no-renames", cwd=WT).stdout
        for e in st.split("\0"):
            if len(e) >= 4 and not e.endswith(".DS_Store"):
                out.append((e[:2], e[3:]))
        return out

    def audit(self):
        """Every change in its code copy against the hard rules - also catches a test build that changed files by
        itself while it ran. Returns what breaks the rules ('' when nothing does)."""
        problems = []
        for code, rel in self.changed():
            if not rel.startswith("library/"):
                problems.append(f"{rel} (outside library/) was changed")
                continue
            p = os.path.join(WT, rel)
            if os.path.islink(p):
                problems.append(f"{rel} is a link")
                continue
            if "D" in code or not os.path.exists(p):
                if locked(rel[8:]):
                    problems.append(f"{rel} is locked and was removed")
                continue
            try:
                text = open(p, errors="replace").read()
            except OSError as e:
                problems.append(f"{rel}: {e}")
                continue
            bad = check_change(rel, text, new_file=_base_text(rel) is None)
            if bad:
                problems.append(f"{rel}: {bad}")
        return "; ".join(problems)[:3000]

    # -- testing
    def _own_trials(self):
        return [t for t in self.trials if t["cid"] == self.cid and t["kind"] == "try"]

    def _check_root(self):
        """Did a test build write into the running asset maker's own code or your real cards? Then everything
        stops."""
        if self.watch is None:
            return True
        now = _root_watch()
        if now is None:
            return True
        bad = sorted(k for k, v in now.items() if self.watch.get(k) != v)
        if bad:
            self.stopped = ("a test build changed the running asset maker's own files or your real cards (" +
                            ", ".join(bad[:8]) + ") - the session was stopped and nothing is kept. Send this to Claude.")
            self.log(f"[engineer] {self.cid}: STOPPED - {self.stopped}")
        return not bad

    def _run_trial(self, cid, clear, why, kind):
        """One test build (and its check) with the engineer's code copy, inside the time left."""
        if self.left() < 90:
            return None, "out of time"
        timeout = min(REBUILD_TIMEOUT, self.left() - 30)
        if self.model and self.judge and self.model != self.judge:
            _release(self.model)                       # the test build loads the judge: its own brain lets go
        tdir = os.path.join(ENG, "trials", cid, _stamp())
        n = 1
        while os.path.exists(tdir):
            n += 1
            tdir = os.path.join(ENG, "trials", cid, f"{_stamp()}-{n}")
        os.makedirs(tdir)
        clear = [c for c in (clear or []) if isinstance(c, str) and re.fullmatch(r"[a-z_]{1,30}", c)]
        h = self._diff_hash()
        self.beat(f"engineer: test build of {cid} ({kind})")
        env = dict(os.environ, CRUSHED_TRIAL="1", CRUSHED_REMASTER_WORK=WORK)
        rc, took = run_group(_trial_cmd(cid, tdir, clear), timeout, os.path.join(tdir, "trial.log"), env=env,
                             cwd=WT, beat=lambda: self.beat(f"engineer: test build of {cid} running ({kind})"))
        res = jload(os.path.join(tdir, "trial.json"), {})
        v = res.get("verdict") if rc is not None else None
        t = {"cid": cid, "dir": tdir, "verdict": v if isinstance(v, dict) else None, "shots": res.get("shots"),
             "close": res.get("close"), "diff": h, "took": took, "why": why, "clear": clear, "kind": kind,
             "stopped": rc is None}
        self.trials.append(t)
        self._check_root()
        out = open(os.path.join(tdir, "trial.log"), errors="replace").read()
        tail = "\n".join(l for l in out.splitlines()[-40:] if l.strip())[-3000:]
        if rc is None:
            tail = f"the test build ran over its time limit ({timeout} s) and was stopped with everything it started\n" + tail
        return t, tail

    def _judge_own(self, t):
        """The asset maker's own check of a test build's model: its own untouched code, in a separate program."""
        if self.left() < 90:
            return None
        timeout = min(JUDGE_TIMEOUT, self.left() - 30)
        if self.model and self.judge and self.model != self.judge:
            _release(self.model)
        env = dict(os.environ, CRUSHED_TRIAL="1", CRUSHED_REMASTER_WORK=WORK)
        rc, _ = run_group(_judge_cmd(t["cid"], t["dir"]), timeout, os.path.join(t["dir"], "judge.log"), env=env,
                          cwd=ROOT, beat=lambda: self.beat(f"engineer: the asset maker's own check of {t['cid']}"))
        v = jload(os.path.join(t["dir"], "judged.json"), {}).get("verdict") if rc is not None else None
        return v if isinstance(v, dict) else None

    def rebuild(self, clear=None, why=""):
        if self.stopped:
            return "REFUSED: " + self.stopped
        n = len(self._own_trials()) + 1
        if n > MAX_REBUILDS:
            return "REFUSED: out of rebuilds for this item - call finish with what you found"
        need = self.reserve() + self._longest()
        if self.left() < need:
            return (f"REFUSED: not enough time left for another test build ({int(self.left() / 60)} min left; "
                    f"{int(self.reserve() / 60)} min are kept for confirming a fix) - call finish now")
        bad = self.audit()
        if bad:
            return "REFUSED: your changes break the rules, so they can't be tested: " + bad
        if self.diff() == "no changes yet":
            if not clear:
                return ("REFUSED: you have changed nothing, so a rebuild would make the same model again (a rebuild takes "
                        "minutes). Find the cause first - look, measure (compare_colors, mesh_info, read_words), read the "
                        "code that makes that part - then edit it, then rebuild. If you only want a step redone from "
                        "scratch, say which with clear=[...].")
            if self.redo_only:                             # one redo-from-scratch per session; after that, a fix
                return ("REFUSED: you already redid a step from scratch with no code change (rebuild "
                        f"{self.redo_only}) and it failed the same way - redoing it again is a gamble, not a fix. "
                        "Read the step's code (the review sheet names the step; parts.py plans the parts, "
                        "shapes/assembly.py builds them), change what makes it wrong, then rebuild.")
            self.redo_only = n
        self.log(f"[engineer] {self.cid}: rebuild {n} with its fix ({why[:160]})")
        t, tail = self._run_trial(self.cid, clear, why, "try")
        if t is None:
            return "REFUSED: " + tail
        if self.stopped:
            return "STOPPED: " + self.stopped
        v = t["verdict"]
        if not v:
            return f"THE REBUILD FAILED before the check (it took {t['took']} s). The end of its log:\n{tail}"
        before = sorted(_fails_of(self.cur.get("verdict"), self.first["verdict"]))
        first = set(_fails(self.first["verdict"]))
        now = _fails_of(v, self.first["verdict"])
        unjudged = "not_judged" in _fails(v)
        self.cur = {"verdict": v, "shots": t["shots"], "close": t["close"], "dir": t["dir"]}
        progress = {}
        if now < first:                                    # this code fixed something and broke nothing: proven
            self.proven = {"diff": t["diff"], "fixed": sorted(first - now), "files": [c[1] for c in self.changed()]}
            progress = {"PROGRESS": f"this change fixed {sorted(first - now)} and broke nothing. KEEP IT - do not "
                                    "revert it. Work on what is left ON TOP of it, or call finish now and this fix is "
                                    "kept for every item of this kind."}
        for w in ("check", "close"):
            try:
                self.look(w)
            except Exception:
                pass
        return json.dumps({"rebuilt_in_seconds": t["took"], "passed_every_check": bool(v.get("pass")),
                           "failed_before": before, "failed_now": sorted(now),
                           "now_passing_that_failed_at_first": sorted(first - now),
                           "NEW_failures_that_passed_at_first": sorted(now - first),
                           "judge_says": v.get("problems"), **progress,
                           **({"not_judged": "an exact check still fails, so the judge did not look at this build (it "
                                             "looks the moment every exact check passes); the judge's checks count "
                                             "as still failing until then"} if unjudged else {}),
                           "note": "the new check and close-up pictures come with the next message - look at them "
                                   "yourself before you decide whether this change helped. A fix is kept only if "
                                   "nothing that passed at first fails now and at least one failure is gone."},
                          default=str)

    def lesson(self, symptom, cause, fix):
        """Kept aside until the fix is kept (then it goes into the playbook with it); never written into the code
        copy during the session."""
        item = {"symptom": str(symptom).strip()[:600], "cause": str(cause).strip()[:600], "fix": str(fix).strip()[:600]}
        self.lessons.append(item)
        os.makedirs(PENDING, exist_ok=True)
        with open(os.path.join(PENDING, self.cid + ".md"), "a") as f:
            f.write(_lesson_line(self.cid, item))
        return "written down - it goes into the playbook if your fix is kept (otherwise it is filed as tried)"

    def finish(self, summary):
        self.done = str(summary)
        return "ok"


def _lesson_line(cid, item, tag=""):
    clean = {k: " ".join(str(item.get(k, "")).split()) for k in ("symptom", "cause", "fix")}
    return (f"- ({time.strftime('%Y-%m-%d')}, {cid}){tag} SEEN: {clean['symptom']} | CAUSE: {clean['cause']} | "
            f"FIX: {clean['fix']}\n")


# ---------------------------------------------------------------- the conversation with its brain

def _describe(judge, im_b64):
    """The vision brain describes a picture for a brain that can't see: what is there, where, what is wrong."""
    sys.path.insert(0, HERE)
    import vet as V
    import base64
    tmp = os.path.join(ENG, "describe.png")
    open(tmp, "wb").write(base64.b64decode(im_b64))
    q = ("Describe this picture for an engineer who cannot see it: what object or picture it is, every part and "
         "printed thing you can see and WHERE it sits (top/bottom/left/right, fractions), its colors and materials, "
         "and anything that looks wrong, odd, missing or unreal. Plain, exact, at most 150 words. "
         'Answer ONLY JSON: {"description": "..."}')
    try:
        v = V.ask(judge or V.model(), q, [tmp], think=False, side=1280) or {}
        return str(v.get("description") or v)[:1500]
    except Exception as e:
        return f"(could not describe: {e})"


def _chat(model, messages, tools, timeout=2400):
    sys.path.insert(0, HERE)
    import urllib.error
    import vet as V
    body = {"model": model, "stream": False, "think": True, "messages": messages, "tools": tools,
            "keep_alive": "30m", "options": {"temperature": 0.6, "num_ctx": 65536, "num_predict": 8192}}
    try:
        return V._call("/api/chat", body, timeout=timeout).get("message", {})
    except urllib.error.HTTPError as e:
        if e.code == 400:                                     # a brain that can't think out loud: ask plainly
            body["think"] = False
            return V._call("/api/chat", body, timeout=timeout).get("message", {})
        raise


CUT_NOTE = " [cut short to save room - run the tool again if you need all of it]"


def _prune(messages):
    """Only the newest picture sets stay in its memory, and only the last few turns' tool results stay whole - the
    older ones it can look at or read again if it needs to."""
    seen = 0
    for m in reversed(messages):
        if m.get("images"):
            seen += 1
            if seen > KEEP_PICTURES:
                m.pop("images")
                m["content"] += " [these pictures were taken out of memory to save room - look again if needed]"
    turns = [i for i, m in enumerate(messages) if m.get("role") == "assistant"]
    if len(turns) <= KEEP_FULL_TURNS:
        return
    cutoff = turns[-KEEP_FULL_TURNS]
    for m in messages[:cutoff]:
        c = m.get("content")
        if m.get("role") == "tool" and isinstance(c, str) and len(c) > OLD_RESULT_CHARS and not c.endswith(CUT_NOTE):
            m["content"] = c[:OLD_RESULT_CHARS] + CUT_NOTE


def _system(b):
    pb = open(os.path.join(WT, "library", "playbook", "playbook.md")).read()
    lessons = open(os.path.join(WT, "library", "playbook", "lessons.md")).read()[-6000:]
    tried = ""
    if os.path.exists(REJECTED):
        tried = open(REJECTED, errors="replace").read()[-3000:]
        tried = ("\n\n## Tried before and NOT kept (do not repeat these unless you have new evidence)\n" + tried
                 if tried.strip() else "")
    c = b.card.get("construction") or {}
    route = _route_of(b.card, b.first["dir"])
    files = ", ".join("library/" + f for f in ROUTE_FILES.get(route, ()) + ROUTE_FILES["all"])
    return (pb + "\n\n" + lessons + tried +
            f"\n\n## This item\nproduct: {b.card.get('product')}\nreal size (m, width x depth x height): "
            f"{b.card.get('size')}\nbuild route: {route}\nhow it is made (its card): {json.dumps(c)[:2500]}\n"
            f"what marks the real thing: {b.card.get('recognize')}\nfiles this route uses: {files}\n"
            "Your code copy is the folder 'library/...'. The build folder (its pictures, textures, model) is 'build/'.")


def _file_old_pending(cid):
    """Lessons an earlier session of this item wrote but never finished: filed as tried-and-not-kept."""
    p = os.path.join(PENDING, cid + ".md")
    if os.path.exists(p):
        txt = open(p, errors="replace").read()
        if txt.strip():
            with open(REJECTED, "a") as f:
                f.write(txt.replace(f", {cid})", f", {cid}) [session stopped half way]"))
        _move_to_scratch(p, f"lessons-{cid}-filed")


def fix(cid, card, verdict, shots, close, photo, build_dir, log=print, beat=lambda s: None, status=None, newer=None):
    """Your AI works on one failed model until it passes or it runs out of ideas. Returns what happened."""
    say = log
    status = status or (lambda **k: None)
    why = nothing_to_fix(verdict)
    if why:
        say(f"[engineer] {cid}: not started - {why}")
        _refund_attempt(cid)
        return {"kept": False, "why": "not started: " + why, "started": False}
    model = brain()
    if not model:
        return {"kept": False, "why": "no brain installed for the engineer", "started": False}
    os.makedirs(ENG, exist_ok=True)
    _file_old_pending(cid)
    base_sha, branch = fresh_worktree(cid)
    b = Bench(cid, card, verdict, shots, close, photo, build_dir, log, beat, base=base_sha)
    b.model = model
    try:
        b.judge = _judge_model()
    except Exception:
        b.judge = None
    say(f"[engineer] {cid}: your AI ({model}) takes the failed model: {', '.join(_fails(verdict))} "
        f"(its code copy: branch {branch})")
    for w in ("check", "close", "photo"):
        try:
            b.look(w)
        except Exception:
            pass
    first = (f"The model of {(card or {}).get('product')} failed the realism check.\nFailed checks: {_fails(verdict)}\n"
             f"The judge said: {json.dumps(verdict.get('problems'))}\n"
             "With this message: the model all around, its close-ups, and the real photo. Follow the playbook: look "
             "closely (zoom in where each problem is), measure (mesh_info, pixel_stats on its maps), find the code "
             "that makes it, fix the cause in your code copy, rebuild, look again. Start by looking.")
    try:                                                     # every step's own checks: start where it first went wrong
        import review
        if os.path.exists(os.path.join(build_dir, "review.json")):
            first += ("\n\nThe build's review sheet - every step's own checks, in order (look at a step's pictures "
                      "with look('step:<file name>')):\n" + review.load(build_dir).text() +
                      "\nStart at the FIRST step that went wrong: fix that step's code, not the finished model.")
    except Exception:
        pass
    route = _route_of(card, build_dir)
    if STEP_FILES.get(route):
        first += (f"\n\nThis item was built by the '{route}' route. The files that make each step, in order: "
                  f"{STEP_FILES[route]}. Open the file of the step that went wrong; read_file takes start/end lines.")
    messages = [{"role": "system", "content": _system(b)}, {"role": "user", "content": first}]
    tools = tool_specs()
    sees = can_see(model)
    eyes = "sees pictures itself" if sees else f"a coding brain - the judge {b.judge} is its eyes"
    say(f"[engineer] {cid}: brain {model} ({eyes})")
    fns = {"look": b.look, "pixel_stats": b.pixel_stats, "mesh_info": b.mesh_info, "list_files": b.list_files,
           "read_file": b.read_file, "grep": b.grep, "edit_file": b.edit_file, "new_file": b.new_file,
           "diff": b.diff, "revert": b.revert, "rebuild": b.rebuild, "lesson": b.lesson, "finish": b.finish,
           "compare_colors": b.compare_colors, "read_words": b.read_words, "ask_eyes": b.ask_eyes,
           "review_sheet": b.review_sheet}
    allowed = {name: set(props) for name, _, props, _ in TOOLS}
    nudged = 0
    last_newer = 0.0                                          # checked on the first turn, then every 10 minutes
    for turn in range(MAX_TURNS):
        if b.stopped:
            break
        if b.left() < b.reserve():
            say(f"[engineer] {cid}: time is nearly up - what it has is checked now")
            break
        # newer code is in and it has changed nothing yet: the build is remade on the new code first - working out
        # a failure of code that is already replaced wastes its hours (checked every 10 minutes, cheap)
        if newer and time.time() - last_newer > 600:
            last_newer = time.time()
            try:
                fresh = bool(newer())
            except Exception:
                fresh = False
            if fresh and b.diff() == "no changes yet" and not b.trials:
                say(f"[engineer] {cid}: newer code is in and it has changed nothing yet - this build is remade on "
                    "the new code first")
                b.newer_code = True
                break
        if b.pictures:
            if sees:
                messages.append({"role": "user", "content": "Pictures: " + "; ".join(n for n, _ in b.pictures),
                                 "images": [im for _, im in b.pictures]})
            else:                                             # a coding brain without eyes: the judge describes
                told = []
                for n, im in b.pictures:
                    told.append(f"[{n}] " + _describe(b.judge, im))
                messages.append({"role": "user", "content": "What the vision brain sees in each picture (ask it "
                                 "more with ask_eyes):\n" + "\n".join(told)})
            b.pictures = []
        _prune(messages)
        beat(f"engineer thinking about {cid} (turn {turn + 1})")
        try:
            msg = _chat(model, messages, tools, timeout=int(max(60, min(2400, b.left() - b.reserve()))))
        except Exception as e:
            say(f"[engineer] {cid}: its brain did not answer ({e})")
            break
        calls = msg.get("tool_calls") or []
        messages.append({"role": "assistant", "content": msg.get("content", ""), **({"tool_calls": calls} if calls else {})})
        if msg.get("thinking"):
            say(f"[engineer] thinks: {msg['thinking'].strip()[:300]}")
        if not calls:
            nudged += 1
            if nudged > 3:
                break
            messages.append({"role": "user", "content": "Use your tools to keep working (look, measure, read, edit, "
                                                        "rebuild), or call finish with your summary."})
            continue
        for c in calls:
            f = c.get("function", {})
            name, args = f.get("name", ""), f.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            args = {k: v for k, v in args.items() if k in allowed.get(name, ())}   # only the inputs it was given
            try:
                res = fns[name](**args) if name in fns else f"no tool called {name}"
            except TypeError as e:
                res = f"wrong inputs for {name}: {e}"
            except Exception as e:
                res = f"{name} failed: {e}"
            short = json.dumps(args)[:200]
            say(f"[engineer] {name} {short} -> {str(res)[:200]}")
            status(step=f"your AI's engineer is fixing it: {name} {short[:120]}")
            messages.append({"role": "tool", "tool_name": name, "content": str(res)[:16000]})
        if b.done is not None:
            ok, why = _accept(b, say)
            if ok:
                b.accepted = b._diff_hash()
            if ok or why.startswith("nothing") or b.stopped:
                break
            b.done = None                                           # not good enough: it hears why and goes on
            messages.append({"role": "user", "content": why})
    return _keep(b, base_sha, branch, say)


def _accept(b, say):
    """May its changes be kept? Only when (1) nothing breaks the rules, (2) the rebuild WITH THESE EXACT CHANGES fixed
    at least one failed check and broke none that passed, (3) a second rebuild of the same code comes out the same
    and the asset maker's own check agrees, (4) the other built items of the same kind gained no new failure."""
    if b.stopped:
        return False, b.stopped
    if not [c for c in b.changed() if not c[1].startswith("library/playbook/")]:
        return False, "nothing changed"
    h = b._diff_hash()
    if h in b.decided:
        ok, why = b.decided[h]
        return ok, (why if ok else "Same code as before, so the same answer: " + why)
    bad = b.audit()
    if bad:
        return False, "Your changes break the rules and can't be kept: " + bad + ". Revert them."
    tried = b._own_trials()
    if tried and tried[-1]["diff"] == h and not tried[-1]["verdict"]:
        return False, ("Your last rebuild with these changes did not finish (it broke or ran over its time) - nothing "
                       "is kept that was not checked. Look at why, fix it, and rebuild.")
    mine = [t for t in tried if t["verdict"]]
    last = mine[-1] if mine else None
    if not last or last["diff"] != h:
        return False, ("You changed code after your last rebuild (or never rebuilt). Rebuild with exactly these changes "
                       "first - nothing is kept that was not tested.")
    F0, F1 = set(_fails(b.first["verdict"])), _fails_of(last["verdict"], b.first["verdict"])
    if not F1 < F0:
        worse = sorted(F1 - F0)
        msg = (f"Your last rebuild failed {sorted(F1)} (at first: {sorted(F0)}). " +
               (f"It broke checks that passed before: {worse}. " if worse else "No failed check was fixed. ") +
               "A fix is kept only if nothing that passed fails now and at least one failure is gone. Look at the new "
               "pictures, revert what did not help, and try the real cause - or call finish again if you truly have "
               "no other idea.")
        b.decided[h] = (False, msg)
        return False, msg

    def decide(ok, why):
        b.decided[h] = (ok, why)
        return ok, why

    say(f"[engineer] {b.cid}: {sorted(F0)} -> {sorted(F1)} - confirming with a second rebuild and the asset maker's "
        "own check")
    t, tail = b._run_trial(b.cid, last["clear"], "confirm: the same code again", "confirm")
    if b.stopped:
        return False, b.stopped
    if t is None or not t["verdict"]:
        return decide(False, "The confirmation rebuild of the same code did not finish (" +
                      (tail or "")[-600:] + ") - nothing is kept that can't be repeated.")
    F2 = _fails_of(t["verdict"], b.first["verdict"])
    own = b._judge_own(t)
    if b.stopped:
        return False, b.stopped
    if own is None or "failed" not in own:
        return decide(False, "The asset maker's own check could not judge the confirmation rebuild" +
                      (f" ({str((own or {}).get('problems'))[:300]})" if own else "") + " - nothing is kept unconfirmed.")
    Fp = _fails_of(own, b.first["verdict"])
    # three checks of the same code (its rebuild, the confirmation rebuild, the asset maker's own check): the judge
    # is a brain and two looks at the same model can differ - a check counts as failing when at least two of the
    # three say so (2026-10-04: a real fix was thrown away because one look of three added 'materials')
    from collections import Counter
    votes = Counter(F1) + Counter(F2) + Counter(Fp)
    maj = {f for f, n in votes.items() if n >= 2}
    if F2 != F1 or Fp != F1:
        say(f"[engineer] {b.cid}: the three checks disagree - first {sorted(F1)}, second {sorted(F2)}, the asset "
            f"maker's own {sorted(Fp)}; failing in at least two of three: {sorted(maj)}")
    if not maj < F0:
        return decide(False, f"The same code was checked three times (two rebuilds and the asset maker's own check): "
                             f"first {sorted(F1)}, second {sorted(F2)}, own {sorted(Fp)}. Counting a check as failed "
                             f"when at least two of the three say so: {sorted(maj)} - against {sorted(F0)} at first, "
                             + ("that breaks checks that passed: " + str(sorted(maj - F0)) if maj - F0 else
                                "no failure is gone") + ". That is not a real fix - find a change that helps every time.")
    for other in _neighbors(b):
        o, otail = b._run_trial(other["cid"], [], "does this fix break other items?", "neighbor")
        if b.stopped:
            return False, b.stopped
        if o is None or not o["verdict"]:
            return decide(False, f"Your fix broke the build of {other['cid']}: {(otail or '')[-1500:]}")
        new = sorted(set(_fails(o["verdict"])) - set(other["fails"]))
        if new:
            return decide(False, f"Your fix made {other['cid']} worse: it now also fails {new} (before it failed "
                                 f"{sorted(other['fails'])}; judge: {o['verdict'].get('problems')}). Fix the cause "
                                 "without breaking it.")
    if b._diff_hash() != h:
        return decide(False, "The code changed by itself while the fix was being confirmed (a test build wrote into "
                             "the code copy) - nothing is kept.")
    bad = b.audit()
    if bad:
        return decide(False, "A test build changed files it must not: " + bad)
    return decide(True, "ok")


def _neighbors(b, most=2):
    """Other items already built whose build uses the files it changed (to prove the fix doesn't break them)."""
    changed = [rel[len("library/"):] for code, rel in b.changed()
               if rel.startswith("library/") and not rel.startswith("library/playbook/")]
    if not changed:
        return []
    st = jload(os.path.join(OUT, "status.json"), None)
    if not isinstance(st, dict):                            # broken right now: its last good backup
        st = jload(os.path.join(OUT, "status.json.bak"), {})
    out = []
    for cid, v in (st.items() if isinstance(st, dict) else []):
        if cid == b.cid or not isinstance(v, dict) or not isinstance(v.get("verdict"), dict):
            continue
        d = os.path.join(OUT, cid)
        if not os.path.exists(os.path.join(d, "candidates.json")):
            continue
        route = _route_of(jload(os.path.join(WORK, "cards", cid + ".json"), {}), d)
        uses = ROUTE_FILES.get(route, ()) + ROUTE_FILES["all"]
        if any(c.startswith(u) or u.startswith(c) for c in changed for u in uses):
            out.append({"cid": cid, "fails": _fails(v["verdict"])})
    return sorted(out, key=lambda x: len(x["fails"]))[:most]


def _file_rejected(b, why):
    """Nothing kept: its lessons (and what it changed) go under 'tried and not kept', so the next session doesn't
    walk the same dead end."""
    files = sorted({rel for _, rel in b.changed() if not rel.startswith("library/playbook/")})
    p = os.path.join(PENDING, b.cid + ".md")
    if not b.lessons and not files:
        if os.path.exists(p):
            _move_to_scratch(p, f"lessons-{b.cid}-filed")
        return
    with open(REJECTED, "a") as f:
        f.write(f"- ({time.strftime('%Y-%m-%d')}, {b.cid}) NOT KEPT ({' '.join(str(why).split())[:240]}); "
                f"changed: {', '.join(files)[:300] or 'nothing'}\n")
        for item in b.lessons:
            f.write("  " + _lesson_line(b.cid, item, tag=" [not kept]"))
    if os.path.exists(p):
        _move_to_scratch(p, f"lessons-{b.cid}-filed")


def _keep(b, base_sha, branch, say):
    if getattr(b, "newer_code", False):
        return {"kept": False, "newer_code": True, "branch": branch, "trials": 0,
                "why": "newer code arrived before it changed anything - the item is rebuilt on the new code first"}
    if b.stopped:
        ok, why = False, b.stopped
    elif b.accepted and b.accepted == b._diff_hash():
        ok, why = True, "ok"
    elif b.done is None and b.trials:                       # out of turns or time: what it has, if it is better
        ok, why = _accept(b, say)
    else:
        ok, why = False, "nothing better was found"
    if not ok:
        say(f"[engineer] {b.cid}: nothing kept ({why[:200]})")
        _file_rejected(b, why)
        return {"kept": False, "why": why, "summary": b.done, "trials": len(b.trials),
                "fails_now": _fails(b.cur.get("verdict")), "branch": branch}
    last = [t for t in b._own_trials() if t["verdict"]][-1]
    if b.lessons:                                           # the lessons go into the playbook WITH the kept fix
        with open(os.path.join(WT, "library", "playbook", "lessons.md"), "a") as f:
            for item in b.lessons:
                f.write(_lesson_line(b.cid, item))
    p = os.path.join(PENDING, b.cid + ".md")
    msg = (f"Asset engineer (your AI): {b.cid} - {sorted(_fails(b.first['verdict']))} -> {sorted(_fails(last['verdict']))}"
           f"\n\n{(b.done or '').strip()[:1500]}\n\nConfirmed by a second rebuild and the asset maker's own check."
           "\n\nLessons: " + "; ".join(l["symptom"] for l in b.lessons))
    git("add", "-A", "--", "library", ":(exclude)*.DS_Store", cwd=WT)
    r = git(*AUTHOR, "commit", "-q", "-m", msg, cwd=WT)
    if r.returncode:
        _file_rejected(b, "could not save the fix")
        return {"kept": False, "why": "could not save the fix: " + (r.stderr or r.stdout)[-300:], "branch": branch}
    if os.path.exists(p):
        _move_to_scratch(p, f"lessons-{b.cid}-kept")
    sha = git("rev-parse", "HEAD", cwd=WT).stdout.strip()
    if git("rev-parse", "HEAD").stdout.strip() != base_sha:
        say(f"[engineer] the code moved while it worked - its fix is kept on branch {branch} for review")
        return {"kept": False, "why": f"its fix passed, but the code changed while it worked - kept on branch {branch} "
                                      "for review", "branch": branch, "sha": sha, "summary": b.done}
    r = git("merge", "-q", "--ff-only", sha)
    if r.returncode:
        r = git(*AUTHOR, "cherry-pick", sha)
        if r.returncode:
            git("cherry-pick", "--abort")
            say(f"[engineer] {b.cid}: the fix could not be added to the running code - it is kept on branch {branch}")
            return {"kept": False, "why": "could not add the fix: " + (r.stderr or r.stdout)[-300:], "sha": sha,
                    "branch": branch, "summary": b.done}
    say(f"[engineer] {b.cid}: KEPT - {sorted(_fails(b.first['verdict']))} -> {sorted(_fails(last['verdict']))}: "
        f"{(b.done or '')[:300]}")
    return {"kept": True, "sha": git("rev-parse", "HEAD").stdout.strip(), "summary": b.done,
            "before": _fails(b.first["verdict"]), "after": _fails(last["verdict"]),
            "pass": bool(last["verdict"].get("pass")), "lessons": b.lessons, "branch": branch}


if __name__ == "__main__":
    # by hand: .venv/bin/python library/engineer.py <item id>   (works on the item's last failed build)
    cid = sys.argv[1]
    sys.path.insert(0, HERE)
    import cards
    st = jload(os.path.join(OUT, "status.json"), {}).get(cid, {})
    d = os.path.join(OUT, cid)
    print(json.dumps(fix(cid, cards.make(cid), st.get("verdict") or {}, os.path.join(d, "check", "viewer_around.jpg"),
                         os.path.join(d, "check", "viewer_close.jpg"), os.path.join(WORK, st.get("ref", "")), d),
                     indent=1, default=str))
