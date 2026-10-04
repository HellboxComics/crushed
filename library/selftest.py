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
sys.path.insert(0, HERE)
import ownmods  # noqa: E402  the asset maker's own files always win over same-named files of other tools
ownmods.install()
for p in (os.path.join(ROOT, "ai", "remaster"), os.path.join(ROOT, "ai"), "~/.hellbox/ai"):
    ownmods.add_path(p)
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


def t_own_files():
    """Every file name the asset maker shares with your other tools (facts.py, dossier.py ...) loads the asset maker's
    own, even after those tools put their folders in front (ownmods.py). Without this every dossier failed."""
    import importlib.util
    import glob
    import vet as V                                       # loads the suite's testlock the way a real run does
    V._test_running()
    try:
        import askfirst  # noqa: F401                     # (it puts the phone bot's folder in front)
    except ImportError:
        pass
    import ownmods
    others = [os.path.expanduser(p) for p in ("~/.hellbox/ai", "~/.hellbox/ai/hart")] + \
        [os.path.join(ROOT, "ai"), os.path.join(ROOT, "ai", "remaster")]
    shared = sorted({os.path.basename(f)[:-3] for d in others for f in glob.glob(os.path.join(d, "*.py"))
                     if os.path.exists(os.path.join(HERE, os.path.basename(f)))})
    bad = [n for n in shared if os.path.dirname(importlib.util.find_spec(n).origin) != HERE]
    bad += [f"{n} (loaded from {f})" for n, f in ownmods.wrong()]
    if bad:
        raise RuntimeError("these load another tool's file instead of the asset maker's: " + ", ".join(bad))
    return "shared names load the asset maker's own: " + (", ".join(shared) or "none shared")


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


def t_kit_study():
    """Your AI can write a kit for a kind it has never met - proved on a plain kind with no photo (brain knowledge
    alone). Once written it is a real learned kit and the proof is instant from then on; it is studied again only
    when the kit format (kitmaker.VERSION) or the brain changes."""
    import kitmaker
    import kits
    import vet as V
    m = V.model()
    if not m:
        raise RuntimeError("no brain to study with")
    kind = "wooden pencil"
    card = {"id": "selftest_pencil", "product": "Dixon Ticonderoga No. 2 wooden pencil, circa 1998", "size": [0.007, 0.007, 0.19]}
    L = kitmaker.learned()
    had = L.get(kitmaker.key(kind))
    if had and had.get("learned", {}).get("version") == kitmaker.VERSION and had.get("learned", {}).get("by") == m \
            and kits.finished(had):
        return f"'{kind}' kit on file from {m}: {len(had.get('parts') or [])} parts, built by {had.get('builder')}"
    if had:
        L.pop(kitmaker.key(kind), None)
        kitmaker._save(L)
    kk, kit = kitmaker.ensure(kind, card, None, m, log=lambda *a: None)
    if not kk or not kits.finished(kit):
        raise RuntimeError(f"your AI could not write a finished kit for a '{kind}' - nothing can be built for a new kind")
    return f"'{kind}' studied by {m}: {len(kit.get('parts') or [])} parts, zones {', '.join(kit.get('faces') or [])}, built by {kit.get('builder')}"


def t_free_judges():
    """The judging brains are let go when the drawing room needs the memory: every 'let go' is accepted by the brain
    server. (A brain still answering one of your other tools stays until it's done - the server is shared - so
    what is still loaded a moment later is reported, not counted as broken: 2026-10-03 your suite was mid-answer.)"""
    import run
    asked, left = run.make_room("drawing")
    bad = [n for n, a in asked.items() if not (isinstance(a, dict) and (a.get("done_reason") == "unload" or a.get("done")))]
    if bad:
        raise RuntimeError("the brain server did not accept letting go of: " + ", ".join(bad))
    return (f"let go of {', '.join(asked) or 'nothing loaded'}" +
            (f"; still answering another tool: {', '.join(left)}" if left else ""))


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
    import kits                                          # a kit's standard shape (an AAA from the AA master)
    sp = os.path.join(TMP, "aaa.json")
    json.dump(kits.spec_for("cylindrical_cell", "AAA"), open(sp, "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", "lathe.py"), "--", sp, os.path.join(TMP, "aaa")],
                       capture_output=True, text=True, timeout=240)
    glb = os.path.join(TMP, "aaa", "aaa_cell.glb")
    if not os.path.exists(glb):
        raise RuntimeError("the AAA kit shape: " + (r.stderr or r.stdout)[-300:])
    ext = sorted(glb_size_mm(glb))
    if abs(ext[2] - 44.5) > 0.3 or abs(ext[1] - 10.5) > 0.3:
        raise RuntimeError(f"the AAA kit shape came out {ext[1]:.1f} x {ext[2]:.1f} mm, not 10.5 x 44.5")
    # the parts builder: a soft part lofted from outlines (an ear) next to a hard one (an eye)
    plan = {"cid": "t", "size_mm": [60, 40, 80], "pictures": [], "family": "general", "fixed": [], "not_modeled": [],
            "parts": [{"name": "ear", "shape": "organic", "size_mm": [30, 16, 50], "at_mm": [0, 0, 25],
                       "front_outline": [0.3, 0.7, 1.0, 0.9, 0.6, 0.3, 0.0], "side_outline": [0.6, 1.0, 0.9, 0.7, 0.5, 0.3, 0.0],
                       "lean_mm": [[0, 0], [4, 0]], "rotate_deg": [0, 0, 0], "bevel_mm": 0, "axis": "z", "profile_mm": [],
                       "path_mm": [], "radius_mm": 1, "material": "plush_fur", "color": [0.6, 0.6, 0.6],
                       "roughness": 0.9, "metallic": 0, "print": None, "inside": False, "why": "test"},
                      {"name": "eye", "shape": "sphere", "size_mm": [12, 12, 12], "at_mm": [0, -10, 60],
                       "rotate_deg": [0, 0, 0], "bevel_mm": 0, "axis": "z", "profile_mm": [], "path_mm": [],
                       "radius_mm": 1, "material": "clear_plastic", "color": [0.1, 0.1, 0.1], "roughness": 0.1,
                       "metallic": 0, "print": None, "inside": False, "why": "test"}]}
    pp = os.path.join(TMP, "parts_plan.json")
    json.dump(plan, open(pp, "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", "assembly.py"), "--", pp, os.path.join(TMP, "parts"),
                        "t_parts"], capture_output=True, text=True, timeout=300)
    glb = os.path.join(TMP, "parts", "t_parts.glb")
    if not os.path.exists(glb):
        raise RuntimeError("the parts builder: " + (r.stderr or r.stdout)[-300:])
    ear = mesh_size_mm(glb, "ear")
    if not ear or abs(ear[2] - 50) > 4 or abs(max(ear[0], ear[1]) - 30) > 3:
        raise RuntimeError(f"the lofted ear came out {ear}, not about 30 x 16 x 50 mm")
    # the circuit board: a tiny board with a real solder-side photo (the bottom must be that photo, not invented)
    from PIL import Image
    pdir = os.path.join(TMP, "pcb")
    os.makedirs(pdir, exist_ok=True)
    Image.new("RGB", (256, 128), (40, 90, 50)).save(os.path.join(pdir, "front.png"))
    Image.new("L", (256, 128), 255).save(os.path.join(pdir, "front_mask.png"))
    Image.new("RGB", (256, 128), (200, 30, 30)).save(os.path.join(pdir, "back.png"))
    json.dump([{"type": "chip", "box": [0.3, 0.3, 0.5, 0.6], "height_mm": 2.5}], open(os.path.join(pdir, "parts.json"), "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", "pcb.py"), "--", "0.1", "0.05", pdir,
                        os.path.join(pdir, "front.png"), os.path.join(pdir, "front_mask.png"), os.path.join(pdir, "parts.json"),
                        "t_pcb", os.path.join(pdir, "back.png")], capture_output=True, text=True, timeout=300)
    if not os.path.exists(os.path.join(pdir, "t_pcb.glb")):
        raise RuntimeError("the circuit board builder: " + (r.stderr or r.stdout)[-300:])
    bottom = Image.open(os.path.join(pdir, "textures", "t_pcb_board_bottom.png")).convert("RGB").resize((8, 4))
    if max(abs(a - b) for px in bottom.getdata() for a, b in zip(px, (200, 30, 30))) > 8:
        raise RuntimeError("the circuit board's solder side is not its real photo")
    return "box, round, kit (AAA), lofted soft part and circuit board (real solder side) built"


def mesh_size_mm(glb, name):
    """One named mesh's own size in mm inside a .glb (its corner points), or None."""
    import struct
    with open(glb, "rb") as f:
        f.read(12)
        n, _ = struct.unpack("<II", f.read(8))
        g = json.loads(f.read(n))
    for m in g.get("meshes", []):
        if m.get("name") == name:
            acc = [g["accessors"][p["attributes"]["POSITION"]] for p in m["primitives"]]
            lo = [min(a["min"][i] for a in acc) for i in range(3)]
            hi = [max(a["max"][i] for a in acc) for i in range(3)]
            s = [1000 * (h - l) for l, h in zip(lo, hi)]
            return [s[0], s[2], s[1]]                       # glTF is y-up: back to x, y(depth), z(up)
    return None


def glb_size_mm(glb):
    """A .glb's overall size in mm, read from its own header (every part's corner points; no extra library)."""
    import struct
    with open(glb, "rb") as f:
        f.read(12)
        n, _ = struct.unpack("<II", f.read(8))
        g = json.loads(f.read(n))
    acc = [g["accessors"][p["attributes"]["POSITION"]] for m in g.get("meshes", []) for p in m["primitives"]]
    lo = [min(a["min"][i] for a in acc) for i in range(3)]
    hi = [max(a["max"][i] for a in acc) for i in range(3)]
    return [1000 * (h - l) for l, h in zip(lo, hi)]


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
            "materials.json", "families.py", "family_library.json", "notes.py", "catalog.py", "era.py", "jsonsafe.py", "speed.py", "brainjobs.py",
            "ownmods.py", "review.py", "labelparts.py", "portal.py", "kitmaker.py"]
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
    order = [("the asset maker's own files", t_own_files, 30),
             (GUARD, t_engineer_guard, 30),
             ("memory: what is loaded", t_memory, 20),
             ("phone buttons (Hart's bot)", t_phone, 30),
             ("judge (Ollama vision)", t_judge, 900),   # (the brain server is shared: your other tools' long
             #                                               questions go first - 2026-10-03 one made this wait 5 min)
             ("kit study (a kind it has never met)", t_kit_study, 600),
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
