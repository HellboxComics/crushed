"""SELF-TEST: every piece of the asset maker, checked on this Mac in a few minutes with short time limits,
before any real run. Each piece is reported PASS or FAIL with the reason; the first failure stops the run
and goes to your phone, so a broken piece is never found by waiting.

    .venv/bin/python library/selftest.py           (the loop runs this itself at the start)
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "ai", "remaster"), os.path.join(ROOT, "ai"), os.path.expanduser("~/.hellbox/ai")):
    sys.path.insert(0, p)
TMP = tempfile.mkdtemp(prefix="crushed-selftest-")
RESULTS = []


def check(name, fn, limit):
    try:
        import run
        run.beat("self-test: " + name)
    except Exception:
        pass
    t = time.time()
    try:
        note = fn() or ""
        ok = True
    except Exception as e:
        note, ok = f"{type(e).__name__}: {e}"[:300], False
    took = time.time() - t
    if ok and took > limit:
        ok, note = False, f"too slow: {took:.0f}s (limit {limit}s) {note}"
    RESULTS.append({"piece": name, "ok": ok, "seconds": round(took), "note": note})
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<34} {took:5.0f}s  {note}", flush=True)
    return ok


def sample_photo():
    """A small test picture: a dark cylinder with a copper top on white (no internet needed)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (512, 512), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([206, 150, 306, 230], fill=(190, 110, 50))
    d.rectangle([206, 230, 306, 470], fill=(20, 20, 20))
    d.text((230, 330), "TEST", fill="white")
    p = os.path.join(TMP, "sample.jpg")
    im.save(p)
    return p


def t_memory():
    import vet as V
    loaded = json.loads(urllib.request.urlopen(V.OLLAMA + "/api/ps", timeout=10).read()).get("models", [])
    return "loaded now: " + (", ".join(m["name"] for m in loaded) or "none")


def t_judge():
    import vet as V
    m = V.model()
    if not m:
        raise RuntimeError("no judge model installed in Ollama")
    v = V.ask(m, 'Answer ONLY JSON: {"color": the main color of the top part}', [SAMPLE], think=False)
    return f"{m} answered {v}"


def t_free_judges():
    import run
    run.make_room("drawing")
    import vet as V
    left = json.loads(urllib.request.urlopen(V.OLLAMA + "/api/ps", timeout=10).read()).get("models", [])
    if left:
        raise RuntimeError("still loaded: " + ", ".join(m["name"] for m in left))


def t_cutout():
    import turnaround as T
    out = T.photo_mask(SAMPLE, timeout=90)
    return os.path.basename(out)


def t_draw():
    import turnaround as T
    if not T.can_edit():
        raise RuntimeError("Qwen-Image-Edit-2511 is not in the drawing room")
    out = os.path.join(TMP, "draw.png")
    T.draw_from_photos("test cylinder", [SAMPLE], out, width=512, height=512,
                       prefix="Picture 1 shows an object. Draw its flat printed label, filling the image. ", seed=1,
                       timeout=420)
    from PIL import Image
    return "drew %dx%d" % Image.open(out).size


def t_blender():
    out = os.path.join(TMP, "box")
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", "box.py"), "--", "0.1", "0.05", "0.15", out,
                        "-", "-", "testbox", "0.5"], capture_output=True, text=True, timeout=240)
    if not os.path.exists(os.path.join(out, "testbox.glb")):
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", "lathe.py"), "--",
                        os.path.join(HERE, "shapes", "specs", "aa_battery.json"), os.path.join(TMP, "lathe")],
                       capture_output=True, text=True, timeout=240)
    if not os.path.exists(os.path.join(TMP, "lathe", "aa_battery.glb")):
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    return "box and round shapes built"


def t_hunyuan():
    import hunyuan
    hy = hunyuan.home()
    if not hy:
        raise RuntimeError("Hunyuan3D is not installed")
    r = subprocess.run([os.path.join(hy, ".venv", "bin", "python"), os.path.join(HERE, "hunyuan.py"), "--check"],
                       cwd=HERE, capture_output=True, text=True, timeout=240)      # exactly how a real build runs it
    if r.stdout.strip().splitlines()[-1:] != ["ok"]:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    notes = [l for l in r.stdout.splitlines() if l.startswith("[hunyuan] note")]
    return "the PyTorch shape maker and the painter load" + (f" ({notes[0][16:120]})" if notes else "")


def t_engineer_guard():
    """Your AI's engineer: its hard rules still refuse what they must (offline, about a second). If this fails the
    engineer is not used (the rest of the asset maker still runs)."""
    import ast
    import engineer as E
    must = ["vet.py", "VET.py", "viewshot.py", "judge.py", "measure.py", "engineer.py", "selftest.py", "watchdog.py",
            "dossier.py", "facts.py", "queue.txt", "families.json", "playbook/playbook.md", "playbook//playbook.md",
            "playbook/lessons.md", "shapes/vet.py", ".gitignore", "shapes/../vet.py", "measure_blender.py",
            "materials.json", "families.py", "family_library.json", "notes.py", "catalog.py", "era.py", "jsonsafe.py", "speed.py", "brainjobs.py"]
    bad = [p for p in must if not E.locked(p)]
    if bad:
        raise RuntimeError("not locked: " + ", ".join(bad))
    if E.locked("finish.py") or E.locked("shapes/lathe.py") or E.locked("factory/recipes/x.json") or \
            E.locked("labels/any.json") or E.locked("shapes/specs/aa_battery.json"):
        raise RuntimeError("build files (builders, recipes, label layouts, measured shapes) are locked by mistake")
    # what the engineer is TOLD must be what is true: every file its rulebook calls locked is locked, and nothing
    # it is told is its own is locked (2026-10-03: the label layouts were unlocked, the rulebook still said
    # "locked", and your AI gave up on a fix it was allowed to make)
    import re
    book = open(os.path.join(HERE, "playbook", "playbook.md")).read()
    rule = book[book.find("2. Never weaken the check"):book.find("3. One cause at a time")]
    said_locked = [w for w in re.findall(r"[\w./]+\.(?:py|json|txt|md)\b|[\w./]+/(?=[,\s])", rule.split("YOURS")[0])
                   if w not in ("run.py", "lessons.md")] + ["playbook/lessons.md"]
    said_mine = re.findall(r"[\w]+/(?:[\w]+/)?(?=[\s,.)])", rule.split("YOURS")[1]) if "YOURS" in rule else []
    wrong = [w for w in said_locked if not E.locked(w if "/" in w or "." in w else w + "/x")]
    wrong += [w + " (said to be yours)" for w in said_mine if E.locked(w + "x.json")]
    if wrong:
        raise RuntimeError("the engineer's rulebook and its real locks disagree: " + ", ".join(wrong))
    tree = ast.parse(open(os.path.join(HERE, "run.py")).read())
    same = ast.unparse(tree)
    for node in tree.body:                               # the checklist made weaker: must be caught
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "CHECKS" for t in node.targets):
            node.value.values[0] = ast.Constant("anything")
            break
    else:
        raise RuntimeError("the realism checklist (CHECKS) is not in run.py")
    if E.run_fingerprint(ast.unparse(tree)) == E.run_fingerprint(same):
        raise RuntimeError("a weaker checklist in run.py is not caught")
    if not E.risky("import vet as V\nV.ask = lambda *a, **k: {}\n"):
        raise RuntimeError("replacing the judge's function from a builder is not caught")
    return "locked files, the checklist and judge tricks are all refused"


def t_readers():
    """The exact checks' readers: the barcode reader (zxing-cpp) and the Mac's own text reader (ocrmac). Without
    them every barcode and every printed word would fail its check - so nothing is built until they are there."""
    import measure
    missing = []
    try:
        import zxingcpp  # noqa: F401
    except Exception:
        missing.append("zxing-cpp (barcode reader)")
    kind = measure.reader()
    if not kind:
        missing.append("ocrmac (the Mac's built-in text reader)")
    if missing:
        raise RuntimeError("missing: " + ", ".join(missing) + " - install into the asset maker's Python: "
                           ".venv/bin/pip install zxing-cpp ocrmac")
    return f"barcodes: zxing-cpp; words: {kind}"


def t_phone():
    import askfirst
    import hart as H
    me = H.tg("getMe")
    return "Hart's bot answers: @" + me.get("username", "?")


def t_google():
    import google_images as G
    G.ensure()
    return "its own browser is up"


def run_all(quiet_phone=False):
    global SAMPLE
    SAMPLE = sample_photo()
    print("SELF-TEST " + time.strftime("%H:%M"), flush=True)
    HY, GUARD = "Hunyuan3D loads", "your AI's engineer: safety rules"
    optional = {HY, GUARD}                             # these only switch off their own part, never the whole run
    order = [(GUARD, t_engineer_guard, 30),
             ("memory: what is loaded", t_memory, 20),
             ("phone buttons (Hart's bot)", t_phone, 30),
             ("judge (Ollama vision)", t_judge, 240),
             ("judges let go of memory", t_free_judges, 60),
             ("cut-out (drawing room)", t_cutout, 120),
             ("label drawer (Qwen-Image-Edit)", t_draw, 480),
             ("Blender: box and round shapes", t_blender, 300),
             ("exact-check readers (barcode, text)", t_readers, 60),
             (HY, t_hunyuan, 260),
             ("Google Images browser", t_google, 90)]
    for name, fn, limit in order:
        if not check(name, fn, limit) and name not in optional:   # Hunyuan only blocks free-form items
            break
    try:
        import turnaround as T
        T.free_room()
    except Exception:
        pass
    core = [r for r in RESULTS if r["piece"] not in optional]
    ok = all(r["ok"] for r in core) and len(core) == len(order) - len(optional)
    hy = next((r for r in RESULTS if r["piece"] == HY), {"ok": False, "note": "not checked"})
    guard = next((r for r in RESULTS if r["piece"] == GUARD), {"ok": False, "note": "not checked"})
    work = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
    os.makedirs(work, exist_ok=True)
    out = os.path.join(work, "selftest.json")
    with open(out + ".tmp", "w") as f:                 # written whole or not at all
        code = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(HERE), capture_output=True,
                              text=True).stdout.strip()
        json.dump({"ok": ok, "code": code, "hunyuan_ok": hy["ok"], "hunyuan_note": hy["note"], "engineer_guard_ok": guard["ok"],
                   "engineer_guard_note": guard["note"], "at": time.time(), "results": RESULTS}, f, indent=1)
    os.replace(out + ".tmp", out)
    if not guard["ok"] and not quiet_phone:
        try:
            import hart as H
            H.send(f"Asset maker self-test: your AI's engineer is switched off - its safety rules failed:\n"
                   f"{guard['note']}\nEverything else still runs. Send this to Claude.")
        except (Exception, SystemExit):
            pass
    if not ok and not quiet_phone:
        bad = next(r for r in RESULTS if not r["ok"] and r["piece"] not in optional)
        try:
            import hart as H
            H.send(f"Asset maker self-test FAILED at: {bad['piece']}\n{bad['note']}\nNothing was run. Send this to Claude.")
        except (Exception, SystemExit):
            pass
    print("SELF-TEST " + ("PASSED" if ok else "FAILED"), flush=True)
    return ok


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
