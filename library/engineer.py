"""YOUR AI, THE ASSET ENGINEER. When a model fails the realism check, it is not sent to you and it is not sent to
Claude: your own AI takes it. It looks at the failed pictures up close, measures the model and its texture maps,
reads the code that built it, works out the CAUSE, fixes the builder or the family recipe (never the one asset by
hand), rebuilds, looks again, and keeps only what really made it better. What it learns goes into
playbook/lessons.md, so the next item of that kind comes out right the first time.

    import engineer
    result = engineer.fix(cid, card, verdict, shots, close, photo, build_dir, log=say, beat=beat)

It works in its OWN copy of the code (a git worktree in ~/crushed-render/remaster/engineer/wt) - the running asset
maker is never edited mid-run. A fix is kept only when its rebuild is better (fewer failed checks) and the items
already built still pass as well as they did. Kept fixes become a local commit in your repo, by "Asset Engineer
(your AI)"; the asset maker then restarts on the fixed code and rebuilds the item.

Its brain is the one in settings.json "engineer_brain", otherwise your judge (the same brain that does the
looking, so only one is in memory). Hard limits: its own code copy only, the library folder only, never the
realism checklist or the judge's question, never your finished assets, nothing pushed anywhere.
"""
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "library")
ENG = os.path.join(WORK, "engineer")
WT = os.path.join(ENG, "wt")
PY = sys.executable
MAX_TURNS = 90
MAX_REBUILDS = 6
MAX_SECONDS = 3 * 3600
KEEP_PICTURES = 3                      # only the newest few picture sets stay in its memory (the rest it can re-look)
AUTHOR = ["-c", "user.name=Asset Engineer (your AI)", "-c", "user.email=engineer@hellbox.local"]

ROUTE_FILES = {                         # which shared files each kind of build uses (for the "still works" check)
    "round": ("shapes/lathe.py", "finish.py", "outline.py", "labelart.py", "layout.py", "skin.py",
              "shapes/specs/", "factory/", "labels/", "metal.py", "inks.py"),
    "box": ("skin.py", "panels.py", "eraprint.py", "shapes/carton.py", "shapes/box.py", "finish.py", "factory/"),
    "flat": ("skin.py", "panels.py", "eraprint.py", "shapes/box.py", "finish.py"),
    "pcb": ("shapes/pcb.py", "skin.py", "panels.py", "finish.py"),
    "free": ("hunyuan.py", "shapes/resize.py"),
    "all": ("run.py", "exports.py", "webglb.py", "viewshot.py", "cutaway.py", "vet.py", "cards.py", "preview.py"),
}


# ---------------------------------------------------------------- small helpers

def git(*a, cwd=ROOT, timeout=300):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def jload(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def setting(name, default=None):
    return jload(os.path.join(WORK, "settings.json"), {}).get(name, default)


def brain():
    sys.path.insert(0, HERE)
    import vet as V
    return setting("engineer_brain") or V.model()


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


def _route_of(card, d):
    if os.path.exists(os.path.join(d, "parts.json")):
        return "pcb"
    if os.path.exists(os.path.join(d, "label.png")):
        return "round"
    return (card or {}).get("route", "free")


# ---------------------------------------------------------------- its own copy of the code

def fresh_worktree(cid):
    """A clean copy of the code exactly as it runs now, on a local branch of its own."""
    os.makedirs(ENG, exist_ok=True)
    git("worktree", "prune")
    sha = git("rev-parse", "HEAD").stdout.strip()
    branch = "engineer/" + re.sub(r"[^a-z0-9_.-]", "_", cid.lower())
    if not os.path.exists(os.path.join(WT, ".git")):
        if os.path.exists(WT):                                   # a leftover folder that is not a worktree
            shutil.move(WT, WT + "-old-" + time.strftime("%Y%m%d-%H%M%S"))
        r = git("worktree", "add", "-q", "--force", "-B", branch, WT, sha)
        if r.returncode:
            raise RuntimeError("could not make the engineer's code copy: " + r.stderr[-300:])
    else:
        git("checkout", "-q", "-B", branch, sha, cwd=WT)
        git("reset", "-q", "--hard", sha, cwd=WT)
        git("clean", "-fdq", "--", "library", cwd=WT)             # only files it made itself in its own copy
    return sha


def _inside(rel, write=False):
    """A path in its code copy; writing only inside library/ (never the git folder)."""
    rel = (rel or "").strip().lstrip("/")
    if rel.startswith("wt/"):
        rel = rel[3:]
    if not rel.startswith("library") and not write:
        rel = rel if os.path.exists(os.path.join(WT, rel)) else os.path.join("library", rel)
    elif not rel.startswith("library"):
        rel = os.path.join("library", rel)
    p = os.path.realpath(os.path.join(WT, rel))
    base = os.path.realpath(os.path.join(WT, "library" if write else ""))
    if not (p == base or p.startswith(base + os.sep)) or "/.git" in p:
        raise ValueError(f"{rel}: outside what you may {'change' if write else 'read'}")
    return p, rel


def _protected(text):
    """The realism checklist and the judge's question: the parts of run.py it may never change."""
    a = text.find("CHECKS = {")
    b = text.find("def inspect(")
    c = text.find("\ndef ", b + 10) if b >= 0 else -1
    return (text[a:b] if a >= 0 and b > a else "") + (text[b:c] if b >= 0 else "")


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
                  "must still parse, or the edit is refused.",
     {"path": "string", "old": "string", "new": "string"}, ["path", "old", "new"]),
    ("new_file", "Create a NEW file in your copy of library/ (a helper module, a recipe, a spec).",
     {"path": "string", "content": "string"}, ["path", "content"]),
    ("diff", "Show every change you have made so far.", {}, []),
    ("revert", "Undo your changes to one file (path), or all of them (path = 'all').", {"path": "string"}, ["path"]),
    ("rebuild", "Rebuild this item with YOUR copy of the code and run the realism check again (takes minutes). "
                "clear = cached steps to redo instead of reuse: 'skin' (box faces from photos), 'texture' (label "
                "art), 'era_print' (the rebuilt box sides' words), 'construction' (how it is made), 'parts' "
                "(circuit card parts). Clear a step whenever you changed the code that makes it.",
     {"clear": "array", "why": "string"}, ["why"]),
    ("lesson", "Write down what you learned, for every future build: the symptom you saw, its cause, the fix.",
     {"symptom": "string", "cause": "string", "fix": "string"}, ["symptom", "cause", "fix"]),
    ("finish", "You are done: every check passes, or you made it as good as you can. Say what you changed and why, "
               "and what (if anything) is still wrong and its likely cause.", {"summary": "string"}, ["summary"]),
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


class Bench:
    """Everything the engineer can see and touch for one item."""

    def __init__(self, cid, card, verdict, shots, close, photo, build_dir, log, beat):
        self.cid, self.card, self.log, self.beat = cid, card or {}, log, beat
        self.photo = photo
        self.first = {"verdict": verdict, "shots": shots, "close": close, "dir": build_dir}
        self.cur = dict(self.first)                    # the latest build (the failed one until it rebuilds)
        self.trials = []
        self.pictures = []                             # images waiting to go to its eyes with the next message
        self.done = None
        self.lessons = []
        self.accepted = None
        self.t0 = time.time()

    # -- seeing
    def _file(self, what):
        what = (what or "").strip()
        named = {"check": self.cur.get("shots"), "close": self.cur.get("close"), "photo": self.photo,
                 "before": self.first.get("shots"), "before_close": self.first.get("close"),
                 "cutaway": os.path.join(self.cur["dir"], "check", "cutaway.png")}
        if what in named:
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
        im = _grid(p) if what in ("check", "close", "before", "before_close") else Image.open(p)
        im = self._crop(im, box)
        if box and max(im.size) < 1024:                # zoomed: shown bigger
            s = 1024 / max(im.size)
            im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        self.pictures.append((f"{what}" + (f" zoomed to {box}" if box else ""), _b64(im)))
        return f"looking at {what} ({os.path.basename(p)}, {Image.open(p).size[0]}x{Image.open(p).size[1]} px)" + \
               (f", zoomed to {box}" if box else "") + " - the picture comes with the next message."

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
        probe = os.path.join(ENG, "probe.py")
        open(probe, "w").write(PROBE)
        r = subprocess.run([PY, probe, "--", glb], capture_output=True, text=True, timeout=600)
        m = re.search(r"PROBE(.*)", r.stdout or "")
        if not m:
            return "could not measure: " + (r.stderr or r.stdout)[-500:]
        parts = json.loads(m.group(1))
        return json.dumps(parts)[:9000]

    # -- reading code
    def list_files(self, path):
        if path.startswith("build"):
            base = os.path.join(self.cur["dir"], path[5:].lstrip("/"))
            if not os.path.realpath(base).startswith(os.path.realpath(self.cur["dir"])):
                raise ValueError("only inside the build folder")
        else:
            base, _ = _inside(path)
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
            p, _ = _inside(path)
        lines = open(p, errors="replace").read().splitlines()
        start = max(1, int(start or 1))
        end = min(len(lines), int(end or start + 199), start + 399)
        body = "\n".join(f"{i:5d}  {lines[i - 1]}" for i in range(start, end + 1))
        return f"{path} lines {start}-{end} of {len(lines)}\n{body}"

    def grep(self, pattern, path="library"):
        base, _ = _inside(path or "library")
        rx = re.compile(pattern)
        hits = []
        files = [base] if os.path.isfile(base) else [os.path.join(d, f) for d, _, fs in os.walk(base)
                                                     if "__pycache__" not in d for f in fs
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
            r = subprocess.run([PY, "-m", "py_compile", p], capture_output=True, text=True)
            if r.returncode:
                return "Python does not compile: " + (r.stderr or "")[-600:]
        if p.endswith(".json"):
            try:
                json.load(open(p))
            except Exception as e:
                return f"JSON does not parse: {e}"
        return None

    def edit_file(self, path, old, new):
        p, rel = _inside(path, write=True)
        if rel.endswith("playbook/playbook.md"):
            return "REFUSED: the playbook's rules are not yours to change (write a lesson instead)"
        text = open(p).read()
        n = text.count(old)
        if n != 1:
            near = ""
            key = (old.strip().splitlines() or [""])[0].strip()[:60]
            if key:
                near = "\n".join(f"  line {i}: {l.strip()[:160]}" for i, l in enumerate(text.splitlines(), 1)
                                 if key[:40] in l)[:1500]
            return (f"REFUSED: the old text appears {n} times in {rel} (it must appear exactly once - copy it exactly "
                    f"from read_file, without line numbers)." + (f" Lines that look like it:\n{near}" if near else ""))
        new_text = text.replace(old, new)
        if rel.endswith("library/run.py") and _protected(text) != _protected(new_text):
            return "REFUSED: that changes the realism checklist or the judge's question - fix the build, not the check"
        open(p, "w").write(new_text)
        bad = self._check_file(p)
        if bad:
            open(p, "w").write(text)
            return "REFUSED (put back as it was): " + bad
        return f"changed {rel}"

    def new_file(self, path, content):
        p, rel = _inside(path, write=True)
        tracked = git("ls-files", "--error-unmatch", rel, cwd=WT).returncode == 0
        if os.path.exists(p) and tracked:
            return f"REFUSED: {rel} already exists - use edit_file"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(content)
        bad = self._check_file(p)
        if bad:
            os.replace(p, p + ".refused")
            return "REFUSED: " + bad
        return f"wrote {rel}"

    def diff(self):
        git("add", "-A", "-N", "library", cwd=WT)
        d = git("diff", "--", "library", cwd=WT).stdout
        return (d[:12000] + ("\n(diff cut short)" if len(d) > 12000 else "")) or "no changes yet"

    def revert(self, path):
        if path == "all":
            git("checkout", "-q", "--", "library", cwd=WT)
            git("clean", "-fdq", "--", "library", cwd=WT)
            return "every change undone"
        p, rel = _inside(path, write=True)
        if git("ls-files", "--error-unmatch", rel, cwd=WT).returncode == 0:
            git("checkout", "-q", "--", rel, cwd=WT)
        elif os.path.exists(p):
            os.replace(p, p + ".undone")
        return f"{rel} is back as it was"

    def _diff_hash(self):
        git("add", "-A", "-N", "library", cwd=WT)
        return hashlib.sha1(git("diff", "--", "library", cwd=WT).stdout.encode()).hexdigest()

    # -- testing
    def rebuild(self, clear=None, why="", cid=None, card=None):
        cid = cid or self.cid
        n = len([t for t in self.trials if t["cid"] == cid]) + 1
        if cid == self.cid and n > MAX_REBUILDS:
            return "REFUSED: out of rebuilds for this item - call finish with what you found"
        tdir = os.path.join(ENG, "trials", cid, time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(tdir, exist_ok=True)
        clear = [c for c in (clear or []) if isinstance(c, str)]
        self.log(f"[engineer] {cid}: rebuild {n} with its fix ({why[:160]})")
        self.beat(f"engineer: rebuilding {cid} to test a fix")
        env = dict(os.environ, CRUSHED_TRIAL="1", CRUSHED_REMASTER_WORK=WORK)
        h = self._diff_hash()
        t0 = time.time()
        try:
            r = subprocess.run([PY, os.path.join(WT, "library", "run.py"), "--trial", cid, tdir,
                                "--clear", ",".join(clear)], capture_output=True, text=True, env=env, timeout=3600)
            out = (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            out = "the rebuild ran over an hour and was stopped"
        open(os.path.join(tdir, "trial.log"), "w").write(out)
        res = jload(os.path.join(tdir, "trial.json"), {})
        v = res.get("verdict")
        t = {"cid": cid, "dir": tdir, "verdict": v, "shots": res.get("shots"), "close": res.get("close"),
             "diff": h, "took": int(time.time() - t0), "why": why}
        self.trials.append(t)
        tail = "\n".join(l for l in out.splitlines()[-40:] if l.strip())[-3000:]
        if not v:
            return f"THE REBUILD FAILED before the check (it took {t['took']} s). The end of its log:\n{tail}"
        if cid != self.cid:
            return json.dumps({"item": cid, "failed": _fails(v), "problems": v.get("problems")})
        before = _fails(self.cur.get("verdict"))
        self.cur = {"verdict": v, "shots": t["shots"], "close": t["close"], "dir": tdir}
        for w in ("check", "close"):
            try:
                self.look(w)
            except Exception:
                pass
        return json.dumps({"rebuilt_in_seconds": t["took"], "passed_every_check": bool(v.get("pass")),
                           "failed_before": before, "failed_now": _fails(v), "judge_says": v.get("problems"),
                           "note": "the new check and close-up pictures come with the next message - look at them "
                                   "yourself before you decide whether this change helped"}, default=str)

    def lesson(self, symptom, cause, fix):
        self.lessons.append({"symptom": symptom, "cause": cause, "fix": fix})
        p = os.path.join(WT, "library", "playbook", "lessons.md")
        with open(p, "a") as f:
            f.write(f"- ({time.strftime('%Y-%m-%d')}, {self.cid}) SEEN: {symptom.strip()} | CAUSE: {cause.strip()} | "
                    f"FIX: {fix.strip()}\n")
        return "written - every future build reads it"

    def finish(self, summary):
        self.done = summary
        return "ok"


# ---------------------------------------------------------------- the conversation with its brain

def _chat(model, messages, tools):
    sys.path.insert(0, HERE)
    import urllib.error
    import vet as V
    body = {"model": model, "stream": False, "think": True, "messages": messages, "tools": tools,
            "keep_alive": "30m", "options": {"temperature": 0.6, "num_ctx": 65536, "num_predict": 8192}}
    try:
        return V._call("/api/chat", body, timeout=2400).get("message", {})
    except urllib.error.HTTPError as e:
        if e.code == 400:                                     # a brain that can't think out loud: ask plainly
            body["think"] = False
            return V._call("/api/chat", body, timeout=2400).get("message", {})
        raise


def _prune(messages):
    """Only the newest picture sets stay in its memory - the older ones it can look at again if it needs to."""
    seen = 0
    for m in reversed(messages):
        if m.get("images"):
            seen += 1
            if seen > KEEP_PICTURES:
                m.pop("images")
                m["content"] += " [these pictures were taken out of memory to save room - look again if needed]"


def _system(b):
    pb = open(os.path.join(WT, "library", "playbook", "playbook.md")).read()
    lessons = open(os.path.join(WT, "library", "playbook", "lessons.md")).read()[-6000:]
    c = b.card.get("construction") or {}
    route = _route_of(b.card, b.first["dir"])
    files = ", ".join("library/" + f for f in ROUTE_FILES.get(route, ()) + ROUTE_FILES["all"])
    return (pb + "\n\n" + lessons +
            f"\n\n## This item\nproduct: {b.card.get('product')}\nreal size (m, width x depth x height): "
            f"{b.card.get('size')}\nbuild route: {route}\nhow it is made (its card): {json.dumps(c)[:2500]}\n"
            f"what marks the real thing: {b.card.get('recognize')}\nfiles this route uses: {files}\n"
            "Your code copy is the folder 'library/...'. The build folder (its pictures, textures, model) is 'build/'.")


def fix(cid, card, verdict, shots, close, photo, build_dir, log=print, beat=lambda s: None, status=None):
    """Your AI works on one failed model until it passes or it runs out of ideas. Returns what happened."""
    say = log
    status = status or (lambda **k: None)
    model = brain()
    if not model:
        return {"kept": False, "why": "no brain installed for the engineer"}
    base_sha = fresh_worktree(cid)
    b = Bench(cid, card, verdict, shots, close, photo, build_dir, log, beat)
    say(f"[engineer] {cid}: your AI ({model}) takes the failed model: {', '.join(_fails(verdict))}")
    for w in ("check", "close", "photo"):
        try:
            b.look(w)
        except Exception:
            pass
    first = (f"The model of {card.get('product')} failed the realism check.\nFailed checks: {_fails(verdict)}\n"
             f"The judge said: {json.dumps(verdict.get('problems'))}\n"
             "With this message: the model all around, its close-ups, and the real photo. Follow the playbook: look "
             "closely (zoom in where each problem is), measure (mesh_info, pixel_stats on its maps), find the code "
             "that makes it, fix the cause in your code copy, rebuild, look again. Start by looking.")
    messages = [{"role": "system", "content": _system(b)}, {"role": "user", "content": first}]
    tools = tool_specs()
    fns = {"look": b.look, "pixel_stats": b.pixel_stats, "mesh_info": b.mesh_info, "list_files": b.list_files,
           "read_file": b.read_file, "grep": b.grep, "edit_file": b.edit_file, "new_file": b.new_file,
           "diff": b.diff, "revert": b.revert, "rebuild": b.rebuild, "lesson": b.lesson, "finish": b.finish}
    nudged = 0
    for turn in range(MAX_TURNS):
        if time.time() - b.t0 > MAX_SECONDS:
            say(f"[engineer] {cid}: out of time")
            break
        if b.pictures:
            messages.append({"role": "user", "content": "Pictures: " + "; ".join(n for n, _ in b.pictures),
                             "images": [im for _, im in b.pictures]})
            b.pictures = []
        _prune(messages)
        beat(f"engineer thinking about {cid} (turn {turn + 1})")
        try:
            msg = _chat(model, messages, tools)
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
            if ok or why.startswith("nothing"):
                break
            b.done = None                                           # not good enough: it hears why and goes on
            messages.append({"role": "user", "content": why})
    return _keep(b, base_sha, say)


def _accept(b, say):
    """May its changes be kept? Only when the rebuild WITH THESE EXACT CHANGES is better than the failed build and the
    other built items of the same kind did not get worse."""
    h = b._diff_hash()
    if not git("diff", "--stat", "--", "library", cwd=WT).stdout.strip():
        return False, "nothing changed"
    mine = [t for t in b.trials if t["cid"] == b.cid and t["verdict"]]
    last = mine[-1] if mine else None
    if not last or last["diff"] != h:
        return False, ("You changed code after your last rebuild (or never rebuilt). Rebuild with exactly these changes "
                       "first - nothing is kept that was not tested.")
    if len(_fails(last["verdict"])) >= len(_fails(b.first["verdict"])):
        return False, (f"Your last rebuild failed {_fails(last['verdict'])} - no better than before "
                       f"({_fails(b.first['verdict'])}). Look at the new pictures, revert what did not help, and try "
                       "the real cause - or call finish again if you truly have no other idea.")
    for other in _neighbors(b):
        res = b.rebuild(why="does this fix break other items?", cid=other["cid"])
        try:
            got = json.loads(res)
        except Exception:
            return False, f"Your fix broke the build of {other['cid']}: {res[:1500]}"
        if len(got.get("failed", [])) > len(other["fails"]):
            return False, (f"Your fix made {other['cid']} worse: it now fails {got['failed']} (before: {other['fails']}; "
                           f"judge: {got.get('problems')}). Fix the cause without breaking it.")
    return True, "ok"


def _neighbors(b, most=2):
    """Other items already built whose build uses the files it changed (to prove the fix doesn't break them)."""
    changed = [l[len("library/"):] for l in git("diff", "--name-only", "--", "library", cwd=WT).stdout.split()]
    changed += [l[len("library/"):] for l in git("ls-files", "--others", "--exclude-standard", "library",
                                                    cwd=WT).stdout.split()]
    changed = [c for c in changed if not c.startswith("playbook/")]
    if not changed:
        return []
    st = jload(os.path.join(OUT, "status.json"), {})
    out = []
    for cid, v in st.items():
        if cid == b.cid or not isinstance(v.get("verdict"), dict):
            continue
        d = os.path.join(OUT, cid)
        if not os.path.exists(os.path.join(d, "candidates.json")):
            continue
        route = _route_of(jload(os.path.join(WORK, "cards", cid + ".json"), {}), d)
        uses = ROUTE_FILES.get(route, ()) + ROUTE_FILES["all"]
        if any(c.startswith(u) or u.startswith(c) for c in changed for u in uses):
            out.append({"cid": cid, "fails": _fails(v["verdict"])})
    return sorted(out, key=lambda x: len(x["fails"]))[:most]


def _keep(b, base_sha, say):
    if b.accepted and b.accepted == b._diff_hash():
        ok, why = True, "ok"
    elif b.done is None and b.trials:                       # out of turns or time: what it has, if it is better
        ok, why = _accept(b, say)
    else:
        ok, why = False, "nothing better was found"
    if not ok:
        say(f"[engineer] {b.cid}: nothing kept ({why[:200]})")
        return {"kept": False, "why": why, "summary": b.done, "trials": len(b.trials),
                "fails_now": _fails(b.cur.get("verdict"))}
    last = [t for t in b.trials if t["cid"] == b.cid][-1]
    msg = (f"Asset engineer (your AI): {b.cid} - {(_fails(b.first['verdict']))} -> {_fails(last['verdict'])}\n\n"
           f"{(b.done or '').strip()[:1500]}\n\nLessons: " + "; ".join(l["symptom"] for l in b.lessons))
    git("add", "-A", "--", "library", cwd=WT)
    r = git(*AUTHOR, "commit", "-q", "-m", msg, cwd=WT)
    if r.returncode:
        return {"kept": False, "why": "could not save the fix: " + r.stderr[-300:]}
    sha = git("rev-parse", "HEAD", cwd=WT).stdout.strip()
    if git("rev-parse", "HEAD").stdout.strip() != base_sha:
        say(f"[engineer] the code moved while it worked - its fix is kept on branch engineer/{b.cid} for review")
        return {"kept": False, "why": "code changed meanwhile", "branch": f"engineer/{b.cid}", "sha": sha}
    r = git(*AUTHOR, "cherry-pick", sha)
    if r.returncode:
        git("cherry-pick", "--abort")
        return {"kept": False, "why": "could not add the fix: " + r.stderr[-300:], "sha": sha}
    say(f"[engineer] {b.cid}: KEPT - {_fails(b.first['verdict'])} -> {_fails(last['verdict'])}: {(b.done or '')[:300]}")
    return {"kept": True, "sha": sha, "summary": b.done, "before": _fails(b.first["verdict"]),
            "after": _fails(last["verdict"]), "pass": bool(last["verdict"].get("pass")), "lessons": b.lessons}


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
