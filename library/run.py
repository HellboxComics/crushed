"""THE ASSET MAKER - one catalog item in, one finished, real-size 3D asset out (.glb .fbx .usdc .blend).
Runs on your Mac with your own AI. The same steps for every item, a Duracell, a Furby, a Duncan yo-yo or Gak:

  0. card     your AI writes the item's card once: which build route, what you can SEE that marks this exact
              version, what marks a wrong one, what a collector would search (cards.py)
  1. hunt     Google Images with the card's searches, plus your own photos first (hunt.py)
  2. cut out  each photo's item exactly (BiRefNet in the drawing room)
  3. rank     the judge scores every photo against the card (how many right-version marks it shows, any
              wrong-version mark, real photo or ad); the real size from the catalog throws out wrong shapes
  4. pick     the best 9 go to your phone (Hart's Telegram); you tap the true one, or "None of these" and it
              digs deeper
  5. build    by the card's route:
                round  the exact shape traced from your photo at real size (or a measured master like the AA);
                       the AI redraws one flat, perfect label to fit it (skin.py)
                box    the exact box at real size; every face redrawn flat by the AI at its measured size
                flat   the same, two faces
                free   Hunyuan3D makes the shape and paint from your photo; Blender sets the real size
  6. check    studio pictures from four sides; the judge compares them with your photo
  7. you      the pictures go to your phone with Keep / Redo. Kept assets go to ~/Desktop/Asset Library/<item>

    .venv/bin/python library/run.py --only furby_gray_pink_1998 [--wait] [--redo]
    .venv/bin/python library/run.py --queue 2          (the clock: the next 2 items in library/queue.txt)
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ownmods  # noqa: E402  the asset maker's own files always win over same-named files of other tools
ownmods.install()
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "ai", "remaster"), os.path.join(ROOT, "ai"), "~/.hellbox/ai"):
    ownmods.add_path(_p)                                   # other tools' folders: at the END of the search list
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "library")
SHELF = os.path.expanduser("~/Desktop/Asset Library")
PY = sys.executable
STATUS = os.path.join(OUT, "status.json")
WAIT = False          # --wait: a run you started yourself waits for your tap instead of moving on
TRIAL = os.environ.get("CRUSHED_TRIAL") == "1"   # your AI's engineer testing a fix: build + check only, nothing sent
RESTART = False       # your AI's engineer kept a fix: finish here so the clock starts the fixed code
HB = os.path.expanduser("~/.hellbox")


def jload(p, d):
    if p == STATUS:                                   # the shared status file: a broken one never stops the loop
        s = read_status()
        return s if isinstance(s, dict) else d
    try:
        return json.load(open(p))
    except Exception:
        return d


def _atomic_json(path, data):
    """Write a JSON file whole or not at all (a crash or a reader mid-write never sees half a file)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json_safe(path, default):
    """A shared JSON file (status, picks, approvals) that never crashes the loop: a broken one is copied to
    WORK/_broken/ (once per broken version) and its last good backup (<file>.bak) is used instead."""
    import hashlib
    if not os.path.exists(path):
        return default
    raw = b""
    try:
        raw = open(path, "rb").read()
        data = json.loads(raw)
        if isinstance(data, type(default)):
            return data
    except Exception:
        pass
    try:
        broken = os.path.join(WORK, "_broken")
        os.makedirs(broken, exist_ok=True)
        keep = os.path.join(broken, f"{os.path.basename(path)}-{hashlib.sha1(raw).hexdigest()[:10]}")
        if not os.path.exists(keep):
            open(keep, "wb").write(raw)
            say(f"[status] {os.path.basename(path)} was broken - a copy is in {keep}; its last good backup is used")
    except Exception:
        pass
    try:
        data = json.load(open(path + ".bak"))
        if isinstance(data, type(default)):
            return data
    except Exception:
        pass
    return default


def update_json(path, change, default=None, backup=True):
    """Read-change-write one shared JSON file under a lock (the sidecar <file>.lock), so two writers never undo
    each other's change; written whole or not at all, with a backup copy (<file>.bak) to recover from.
    change(data) changes data in place (or returns the new data)."""
    import fcntl
    default = {} if default is None else default
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            data = read_json_safe(path, default)
            out = change(data)
            data = data if out is None else out
            _atomic_json(path, data)
            if backup:
                _atomic_json(path + ".bak", data)
            return data
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def read_status():
    """status.json, never crashing: a broken one is set aside and the last good backup is used."""
    return read_json_safe(STATUS, {})


def pipeline(cid, redo=False):
    import cards
    import hunt
    import turnaround as T
    import vet as V
    from PIL import Image
    d = os.path.join(OUT, cid)
    os.makedirs(d, exist_ok=True)
    mdir = os.path.join(d, "model")

    # your Keep / Redo from last time
    ap = jload(os.path.join(HB, "approvals.json"), {})
    if ap.get(cid, {}).get("say") == "keep":
        r = file_away(cid, d)
        if not r.get("ok"):
            status(cid, step=f"stopped: delivery check failed: {r.get('why')}"[:300], ok=False)
        return
    fresh = redo                                                 # the dossier is made again on --redo or your Redo
    if ap.get(cid, {}).get("say") == "redo":
        start_over(cid, d)
        fresh = True                                             # (the photos it found before are kept)

    card = cards.make(cid, log=say)
    cards.construction(cid, card, log=say)                       # how the real thing is made: layers, materials, details
    ev = cards.era_version(cid, card, V.model(), log=say, evidence=era_evidence(d))   # its own name and look in its
    card["searches"] = list(dict.fromkeys(list(ev.get("searches") or []) + list(card.get("searches") or [])))  # era
    ehk = " | ".join(ev.get("names") or [])
    if ev.get("searches") and card.get("era_hunted") != ehk and \
            jload(os.path.join(HB, "picks.json"), {}).get(cid, {}).get("pick", "none") == "none":
        say(f"[hunt] {cid}: hunting the era's own version ({ehk})")   # not picked yet: look for it by its real name
        hunt.run(cid, card["product"].split(",")[0], card.get("year"), log=say, extra=ev["searches"])
        card["era_hunted"] = ehk
        if not TRIAL:
            json.dump(card, open(cards.path(cid), "w"), indent=1)
    if card.pop("era_print", None) is not None and not TRIAL:    # box words once written from your AI's memory:
        json.dump(card, open(cards.path(cid), "w"), indent=1)     # never used again - facts come from the dossier
        say("[dossier] the box words your AI once wrote from memory are dropped from the card - every printed fact "
            "now comes from the dossier, with its receipt")
    product, size, year, route = card["product"], card["size"], card.get("year"), card["route"]
    import notes as NT                                           # your notes on this item: your AI follows them
    note = NT.text(cid)
    if note:
        card["owner_note"] = note
        if NT.apply_repick(cid, d, HB, log=say):                 # a note asking for another version: hunt + pick again
            status(cid, product=product, route=route, step=f"your note: \"{note[:80]}\" - hunting that version")
            extra = NT.searches(card, note, V.model(), log=say)
            hunt.run(cid, product.split(",")[0], year, log=say, extra=extra or card["searches"])
            fresh = True
    disp = product + (f" (the owner's note: {note})" if note else "")   # what the photo judge looks for

    def go(picked, others, use, n_found, n_good):
        """Know the object before building it: the dossier (every side planned, every fact with a receipt) is
        made or refreshed right after the pick, then the build follows it."""
        import dossier as DS
        import families
        status(cid, step="4/7 your AI decides what kind of thing it is (its family) from the photo")
        make_room("judging")
        fl = families.classify(card, picked["file"], use, log=say, redo=fresh, notes=note)
        family_of(card, use)                                 # its manufacturing family too (recipes, contents)
        if not TRIAL:
            json.dump(card, open(cards.path(cid), "w"), indent=1)
        say(f"[family] {cid}: {fl['family']} ({fl['confidence']}/10): {fl['why']}")
        status(cid, step="4/7 your AI gets to know the item: every side hunted, every fact with a receipt")
        make_room("judging")
        DS.ensure(cid, card, picked, use=use, redo=fresh, log=progress(cid, "4/7 your AI gets to know the item"))
        card["dossier_path"] = DS.path(cid)
        return build(cid, card, picked, others, use, d, mdir, n_found, n_good)

    cf = os.path.join(d, "candidates.json")
    def dig_deeper():
        rounds = len([1 for k in os.listdir(d) if k.startswith("round_")])
        if rounds >= 3:
            status(cid, step="3 rounds and none was right - it needs a photo of your own: put it in "
                             f"~/crushed-render/remaster/refs-mine named {cid}_1.jpg", ok=False)
            return
        open(os.path.join(d, f"round_{rounds + 1}"), "w").write("")
        status(cid, step=f"you said none fit - digging deeper (round {rounds + 2})")
        import cards as CD                                        # what was it really called back then? asked again
        CD.era_version(cid, card, V.model(), log=say, evidence=era_evidence(d), refresh=True)   # with what photos
        hunt.run(cid, product.split(",")[0], year, log=say, extra=more_searches(card, V.model()))   # showed
        return pipeline(cid, redo=False)

    picks = jload(os.path.join(HB, "picks.json"), {})
    if picks.get(cid, {}).get("pick") == "none" and os.path.exists(cf):
        # you turned the photos on your phone down: that answer is taken first (before any new ranking), those
        # photos are never shown again, and it digs deeper
        your_pick(cid, product, [], d)
        return dig_deeper()
    if picks.get(cid, {}).get("pick", "none") != "none" and os.path.exists(cf):
        # you already picked: straight to building, no hunting or ranking again
        status(cid, product=product, route=route, step="your pick is in - building")
        cands = json.load(open(cf))["files"]
        picked = your_pick(cid, product, cands, d)
        use = V.model()
        return go(picked, [c for c in cands if c["file"] != picked["file"]], use, 0, len(cands))
    if jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape"):
        route = "round"                                          # it has a measured master shape (the AA)
    status(cid, product=product, route=route, step="1/7 hunting photos (Google Images, your photos)")
    fj = os.path.join(WORK, "hunt", cid, "found.json")
    found = jload(fj, None) if os.path.exists(fj) and not redo else None
    if found is None:
        found = hunt.run(cid, product.split(",")[0], year, log=say, extra=card["searches"])

    status(cid, step="2/7 ranking the photos against the card")
    make_room("judging")
    vj = os.path.join(d, "vetted.json")
    old = {v["file"]: v for v in jload(vj, [])} if not redo else {}
    use, quick = V.model(), V.quick_model()
    seen_q = collections.Counter()
    q_of = lambda f: str(f.get("title", "")).replace("Google Images:", "").split("|")[0].strip().lower()
    for i, f in enumerate(found):
        seen_q[q_of(f)] += 1
        f["order"] = seen_q[q_of(f)] - 1                         # its place in its OWN search (a later hunt's photos
        f["vet"] = (old.get(f["file"]) or {}).get("vet")         # are not pushed down for coming later)
        fv = f["vet"]
        if fv and note and (fv.get("note") != note[:200] or fv.get("note_rule") != V.NOTE_RULE):
            f["vet"] = fv = None                                 # judged before your note: looked at again with it
        if fv and (card.get("era_version") or {}).get("names") and fv.get("era_names") != card["era_version"]["names"]:
            f["vet"] = fv = None                                 # judged before it knew the era's own name and look
        if fv and not note and fv.get("note"):
            for k in ("note", "note_ok", "note_rule"):           # judged against a note since taken off: that part
                fv.pop(k, None)                                  # of the answer no longer counts
        if fv and fv.get("made_year") not in (None, "", "null") and year:
            import era as ERA                                    # how far outside the era ("90s"), by today's rule
            o = ERA.off(fv.get("made_year"), year)
            fv.pop("year_off", None) if o is None else fv.__setitem__("year_off", o)
    era_q = {s.lower().strip() for s in (card.get("era_version") or {}).get("searches") or []}
    todo = sorted([f for f in found if not f["vet"]], key=lambda f: (q_of(f) not in era_q, f["order"]))[:60]
    # 60 a round: photos found by the era's own name first ("90s Duracell PowerCheck"), each search in Google's order
    careful = 6                                              # the careful look (thinking on) for the best 6 only:
    if quick and len(todo) > careful:                         # the quick look already sorts out the misses
        seen_n = [0]

        def quick_done(i, res):
            f = todo[i]
            f["quick"] = res if isinstance(res, dict) else {}
            seen_n[0] += 1
            say(f"[quick look {seen_n[0]}/{len(todo)}] {os.path.basename(f['file'])}: match {f['quick'].get('match')}, "
                f"marks seen {f['quick'].get('seen')}, {f['quick'].get('kind')}")
        V.parallel(lambda f: V.vet(f["file"], disp, use=quick, think=False, card=card) or {}, todo, quick_done)
        todo.sort(key=lambda f: -rank(dict(f, vet=f["quick"])))
        for f in todo[careful:]:
            f["vet"] = dict(f["quick"], only_quick=True)       # (judged by the quick look only)
        todo = todo[:careful]
        _atomic_json(vj, found)                                  # saved as it goes: a restart keeps every look
    looked = [0]

    def careful_done(i, res):                                 # (several at once when the brain server allows it)
        f = todo[i]
        f["vet"] = res if isinstance(res, dict) else {"match": 0, "problems": f"could not judge: {res}"}
        looked[0] += 1
        status(cid, step=f"3/7 {use} ranks the best photos: {looked[0]} of {len(todo)}")
        say(f"[check] {os.path.basename(f['file'])}: {json.dumps(f['vet'])[:160]}")
        _atomic_json(vj, found)
    V.parallel(lambda f: V.vet(f["file"], disp, use=use, think=True, card=card), todo, careful_done)
    json.dump(found, open(vj, "w"), indent=1)

    # cut out only the photos good enough to be shown to you (not all of them)
    good = sorted([f for f in found if f.get("vet") and f["vet"].get("match", 0) >= 7], key=lambda f: -rank(f))[:24]
    status(cid, step=f"4/7 cutting out the best {len(good)} photos")
    make_room("drawing")
    fails = 0
    for f in good:
        try:
            f["mask"] = T.photo_mask(f["file"], timeout=180)
        except Exception as e:
            say(f"[cut out] {os.path.basename(f['file'])}: {e}")
            fails += 1
            if fails >= 2:
                raise RuntimeError("the drawing room (ComfyUI) is not answering - restart it: "
                                   "launchctl kickstart -k gui/$(id -u)/com.hellbox.ai.draw")
    make_room("judging")
    shown = jload(os.path.join(d, "shown.json"), [])
    cands = [f for f in found if f.get("mask") and f.get("vet") and f["vet"].get("match", 0) >= 7
             and f["vet"].get("sharp", True) is not False and f["vet"].get("whole", True) is not False
             and f["vet"].get("era_ok", True) is not False
             and f["file"] not in shown and size_fits(f, size)]
    cands.sort(key=lambda f: -rank(f))
    auto_pick(cid, cands[:9], d)                              # a clear winner is picked without asking you
    picked = your_pick(cid, product, cands[:9], d)
    if isinstance(picked, dict):
        mine = jload(os.path.join(HB, "picks.json"), {})
        st_now = read_status()
        yours = [c for c, p in mine.items() if c != cid and isinstance(p, dict) and not p.get("auto")
                 and p.get("pick") not in (None, "none")
                 and str((st_now.get(c) or {}).get("step", "")).startswith("waiting for your pick")]
        if yours:                                                 # you picked another item first: that one builds
            status(cid, step="picked - builds right after the item you picked")   # first, this one right after
            return
    if picked == "none":                                          # you said none: dig deeper, then ask again
        return dig_deeper()
    if not picked:
        return
    return go(picked, [c for c in cands if c["file"] != picked["file"]], use, len(found), len(cands))


def route_of_card(card, cid):
    """(route, family entry) for an item exactly as build() chooses its builder - so a test build's own check and the
    real build's check measure the same sides."""
    import families
    fam = families.get((card.get("family_lib") or {}).get("family", "general"))
    bld, _ = families.builder(fam)
    if jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape"):
        bld = "lathe"
    route = {"lathe": "round", "pcb": "pcb", "carton": "box", "box": fam.get("route", "box"),
             "organic": "free", "assembly": "assembly"}.get(bld, "assembly")
    return route, fam


def check_model(cid, card, picked, d, glb, route, fam, shots, close, use):
    """THE WHOLE CHECK of a finished model, the same for a real build and for the asset maker's own check of a test
    build: the exact checks first (measure.py: size, every side, barcode scan, printed words read off the model,
    materials, mesh, inside parts showing through, the phone copy - measured, never guessed), then each side next to
    the real photo of that side judged twice (judge.py), then the realism look in the phone viewer (inspect).
    Anything that could not be checked counts as failed."""
    import dossier as DS
    import judge
    import measure
    product = card["product"]
    mdir = os.path.join(d, "model")
    dos_now = DS.load(cid) or {"size_m": card.get("size"), "faces": {}, "facts": {}}
    status(cid, step="6/7 the exact checks: real size, every side, barcode, printed words, materials, insides")
    m = measure.run(cid, d, glb, dos_now, route if route in ("round", "flat", "pcb") else "box", fam=fam,
                    shots=[x for x in (shots, close) if x], web_glb=os.path.join(mdir, cid + "_web.glb"), use=use,
                    log=say)
    say(f"[measure] {cid}: " + ("every exact check passed" if m["pass"] else "; ".join(m["problems"])[:600]))
    status(cid, step="6/7 each side of the model next to the real photo of that side, judged twice")
    j = judge.sides(cid, m["renders"], dos_now, use, route, product=product, log=say)
    verdict = inspect(shots, picked["file"], product, use, card=card, close=close)
    looked = verdict.get("problems")
    looked = looked if isinstance(looked, list) else ([str(looked)] if looked else [])
    looked_failed = list(verdict.get("failed", []))
    if not verdict.get("pass") and not looked_failed:        # the look itself failed (timeout, bad answer): never a pass
        looked_failed = ["inspect"]
    failed = [f"measure_{k}" for k in m["failed"]] + j["failed"] + looked_failed
    verdict = dict(verdict, failed=failed, measure=m["checks"], sides=j["faces"],
                   problems=m["problems"] + j["problems"] + looked)
    verdict["pass"] = not failed
    return verdict


def build(cid, card, picked, others, use, d, mdir, n_found, n_good, redo=False):
    """5-7: build by the card's route, check it, send it to you for Keep / Redo. A box, flat thing or circuit card
    follows its dossier (made by pipeline right after your pick; made here if it isn't there yet, and made again
    with redo=True)."""
    from PIL import Image
    import families
    product, size = card["product"], card["size"]
    # WHAT KIND OF THING IS THIS: the family your AI read from the photo decides the builder (family_library.json)
    fl = card.get("family_lib") or families.classify(card, picked["file"], use, log=say,
                                                     notes=card.get("owner_note", ""))
    route, fam = route_of_card(card, cid)
    bld, why = families.builder(fam)
    if jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape"):
        bld, why = "lathe", "a measured master shape"          # the AA battery, measured by hand
    say(f"[family] {cid}: {fam['family']} -> built by '{bld}' ({why})")
    card["built_by"] = {"family": fam["family"], "builder": bld, "why": why, "gaps": fam.get("gaps", [])}
    status(cid, family=fam["family"], builder={"lathe": "the round builder", "pcb": "the circuit-card builder",
                                               "carton": "the carton builder (folded like the factory)",
                                               "box": "the box builder", "organic": "Hunyuan (organic shapes)",
                                               "assembly": "the one-off parts builder"}.get(bld, bld))
    if not TRIAL:                                            # kept on the card: the catalog record reads it
        import cards as _cards
        json.dump(card, open(_cards.path(cid), "w"), indent=1)
    import dossier as DS                                     # every route knows the object before it is built -
    dos = DS.ensure(cid, card, picked, use=use, redo=redo,            # made once here, used by every route below
                    log=progress(cid, "4/7 your AI gets to know the item"))

    # 5. BUILD by the family's builder
    if route == "round":
        import metal
        import outline
        import skin
        import kits
        master = jload(os.path.join(HERE, "families.json"), {}).get(cid, {})
        sp = os.path.join(HERE, "shapes", "specs", master.get("shape", "") + ".json")
        kit_name = (card.get("family_lib") or {}).get("family", "")
        variant, vwhy = kits.pick_variant(kits.get(kit_name), card)
        say(f"[kit] {cid}: {kit_name or 'no kit'} - size: {variant or 'none'} ({vwhy})")
        kspec = None if master.get("shape") else kits.spec_for(kit_name, variant)
        if master.get("shape") and os.path.exists(sp) or kspec:
            # a thing with a standard size: its exact shape from the kit (a battery's AA / AAA / C / D), never traced
            spec = json.load(open(sp)) if master.get("shape") and os.path.exists(sp) else kspec
            if kspec:
                say(f"[kit] {cid}: {kit_name} {variant} - the exact shape from its standard size ({spec['name']})")
                sp = os.path.join(d, "shape.json")
                json.dump(spec, open(sp, "w"), indent=1)
            if spec.get("construction"):                               # measured: its build is the truth
                card["construction"] = spec["construction"]
        else:
            status(cid, step="5/7 tracing the exact round shape from your photo at real size")
            vs = ((kits.get(kit_name).get("variants") or {}).get(variant) or {}).get("size_mm")
            if vs:                                                 # the kit's standard size (a 12 oz can) wins
                size = [x / 1000 for x in vs]
                say(f"[kit] {cid}: {kit_name} {variant} - traced from your photo at its standard size {vs} mm")
            spec = outline.from_photo(picked, size, card.get("standing") or "upright", cid=cid)
            spec = outline.apply_construction(spec, card)          # its real layers, seam, lips, metal ends
            try:                                                       # what's inside, from the family's recipe
                sys.path.insert(0, os.path.join(HERE, "factory"))
                import factory
                rec = factory.recipe_for(card, model=use, log=say)
                spec["recipe_inline"] = {"inside": rec.get("inside", []),
                                         "outside": {}, "shell_mm": {}}
                spec["family"] = rec.get("family")
            except Exception as e:
                say(f"[factory] recipe skipped ({e})")
            sp = os.path.join(d, "shape.json")
            json.dump(spec, open(sp, "w"), indent=1)
        along, around = skin.label_size(spec)
        reads = spec.get("label_reads") or card.get("label_reads") or "around"
        w_mm, h_mm = (along, around) if reads == "along" else (around, along)   # the label as it is read
        tex = os.path.join(d, "texture")
        os.makedirs(tex, exist_ok=True)
        hand = os.path.join(HERE, "labels", cid + ".json")
        import labelart
        if os.path.exists(hand):                                   # a layout measured by hand: used as it is
            status(cid, step="5/7 texture map: drawing the measured label layout (exact type)")
            lay = json.load(open(hand))
            lay["width_mm"], lay["height_mm"] = w_mm, h_mm
            png, mr = labelart.render(lay, tex, px=4096)
        else:
            # the real label from your photo AND the other photos of this very item (the dossier's): each unrolled
            # flat (read the right way up) - your pick at the front, the side it can't show from another photo at
            # the back - and the words on them, each confirmed by two reads
            views = [picked] + same_design(picked, others, use, want=3, dossier=dos)
            lab, cov = skin.compose(views, along, around)
            say(f"[texture] the label from {len(views)} photo(s) of this item: real pixels cover "
                f"{(cov.max(0) > 0.05).mean():.0%} of the way around")
            lab = skin.continue_bands(lab, cov < 0.05)
            real = Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8))
            if reads == "along":
                real = real.rotate(90, expand=True)
            real_png = os.path.join(tex, "real.png")
            real.save(real_png)
            make_room("judging")
            parts = []
            for vf in views:
                try:
                    got = skin.sides(vf, "along" if reads == "along" else "around") if vf.get("mask") else []
                except Exception as e:
                    say(f"[texture] {os.path.basename(vf['file'])}: could not unroll ({e})")
                    got = []
                for part in got:
                    pp = os.path.join(tex, f"side{len(parts) + 1}.png")
                    part.save(pp)
                    parts.append(pp)
            words = label_words(parts, use)
            status(cid, step=f"5/7 texture map: your AI rebuilds the label as artwork ({len(words)} words, exact type)")
            import layout as LAY
            png, mr, score = LAY.make(product, real_png, words, w_mm, h_mm, tex, model=use, log=say,
                                      typical=kits.typical(kits.get(kit_name), "label"))
        lab_png, mr_png = os.path.join(d, "label.png"), os.path.join(d, "label_mr.png")
        img, mimg = Image.open(png).convert("RGB"), Image.open(mr).convert("RGB")
        if reads == "along":                                        # onto the UV map: the plus/top end up
            img, mimg = img.rotate(-90, expand=True), mimg.rotate(-90, expand=True)
        img.save(lab_png)
        mimg.save(mr_png)
        status(cid, step="5/7 Blender: mesh + UV map + texture map + material")
        run_blender("lathe.py", sp, mdir, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png"))
        for ext in ("glb", "fbx", "usdc", "blend"):
            if os.path.exists(os.path.join(mdir, spec["id"] + "." + ext)):
                shutil.copy(os.path.join(mdir, spec["id"] + "." + ext), os.path.join(mdir, cid + "." + ext))
    elif route == "pcb":
        # a circuit card is a board with parts standing on it - built part by part, never a printed slab
        import dossier as DS
        import skin
        W, H = size[0], size[2]
        # its top and bottom, planned (the dossier made above)
        status(cid, step="5/7 the board: its top, straightened, with its real outline")
        make_room("drawing")
        skin.box_skin(product, W, 0.002, H, [picked] + same_design(picked, others, use, want=2, dossier=dos),
                      os.path.join(d, "skin"), flat=True, judge=use, log=say, dossier=dos)
        status(cid, step="5/7 your AI finds every part on the board (chips, memory, capacitors, connectors)")
        make_room("judging")
        parts = board_parts(os.path.join(d, "skin", "front.png"), product, use)
        json.dump(parts, open(os.path.join(d, "parts.json"), "w"), indent=1)
        say(f"[pcb] {cid}: {len(parts)} parts found on the board")
        status(cid, step=f"5/7 Blender: the board and its {len(parts)} parts, each its own solid")
        run_blender("pcb.py", str(W), str(H), mdir, os.path.join(d, "skin", "front.png"),
                    os.path.join(d, "skin", "front_mask.png"), os.path.join(d, "parts.json"), cid)
    elif route in ("box", "flat"):
        import dossier as DS
        import skin
        W, D, H = size[:3]
        if route == "flat":
            D = min(D, 0.002)
        # every side planned, facts with receipts (the dossier made above)
        import cards
        mats = cards.materials(card)
        surface = ("card" if "printed_card" in mats else "plastic" if "molded_plastic" in mats else
                   "card" if any(k in str(card.get("mat", "")).lower() for k in ("card", "paper", "board")) else "plastic")
        surface = {"rigid_case": "plastic", "flat_printed": "card", "folding_carton": "card"}.get(fam["family"], surface)
        era = None
        if (dos.get("identity") or {}).get("kind", "packaging") == "packaging" and dos.get("facts"):
            import eraprint                              # the printed facts with receipts, for the sides no photo shows
            era = eraprint.from_dossier(dos)
        status(cid, step="5/7 texture map: every box face at its measured size, each from its plan")
        make_room("drawing")
        shots = [picked] + same_design(picked, others, use, want=5, dossier=dos)
        shots += other_sides(cid, card, picked, use, have=shots, dossier=dos)   # backs and sides the dossier found
        atlas, got = skin.box_skin(product, W, D, H, shots, os.path.join(d, "skin"),
                                   flat=route == "flat", judge=use, log=say, era=era, dossier=dos)
        status(cid, step="5/7 Blender: the carton made like the factory makes it (flat sheet, creased, folded)"
               if bld == "carton" else "5/7 Blender: mesh + UV map + texture map + material")
        if bld == "carton":                              # a folding carton: its dieline, folded, with what's inside
            import facts as FX
            contents = FX.carton_contents(dos, W, D, H, os.path.join(d, "contents.json")) or ""
            cf_ = (dos.get("facts") or {}).get("contents") or {}
            say(f"[contents] {cid}: " + (f"{json.dumps(cf_.get('value'))} ({cf_.get('status')})" if contents else
                                        "nothing known to be inside - the box is built empty"))
            run_blender("carton.py", str(W), str(D), str(H), mdir, os.path.join(d, "skin"), cid, contents)
        else:
            run_blender("box.py", str(W), str(max(D, 0.0003)), str(H), mdir, atlas, "-", cid,
                        "0.3" if route == "flat" else "0.6", surface)
    elif route == "assembly":
        # THE GENERAL ONE-OFF BUILDER: your AI breaks the object into its real parts from every photo of it, and
        # each part is built as its own solid with its own material, at real size (parts.py + shapes/assembly.py)
        import dossier as DS
        import parts as PT
        status(cid, step="5/7 your AI breaks the object into its real parts (every side the dossier found)")
        make_room("judging")
        plan = PT.plan(cid, card, dos, use, os.path.join(d, "parts_plan.json"), log=say,
                       notes=card.get("owner_note", ""))
        status(cid, step=f"5/7 Blender: {len(plan['parts'])} parts, each its own solid with its own material")
        run_blender("assembly.py", os.path.join(d, "parts_plan.json"), mdir, cid)
    else:
        if not families.organic_ready():
            raise RuntimeError("the organic builder (Hunyuan3D) has not proven it works on this Mac yet")
        ref = reference(picked, d)
        status(cid, step="5/7 Hunyuan3D makes the shape and paint from your photo")
        make_room("drawing")
        make_room("judging")                                       # Hunyuan gets the memory to itself
        painted = hunyuan_paint(ref, os.path.join(mdir, "hunyuan"))
        status(cid, step="5/7 Blender: real size, every format")
        run_blender("resize.py", painted, str(max(size)), mdir, cid)
    glb = os.path.join(mdir, cid + ".glb")
    status(cid, step="5/7 every format (.obj .mtl .3ds .ma), textures, and a cutaway of the insides")
    finish_files(cid, d)
    if not TRIAL:
        pend = os.path.join(ROOT, "assets", "models_pending", cid)   # so the phone page can spin it in 3D right away
        os.makedirs(pend, exist_ok=True)
        web = os.path.join(mdir, cid + "_web.glb")
        shutil.copy(web if os.path.exists(web) else glb, os.path.join(pend, "model.glb"))

    # 6. CHECK: four sides against your photo
    status(cid, step="6/7 pictures from four sides and the judge's check")
    subprocess.run([PY, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(d, "view.png"), "0,90,180,270"],
                   check=True, capture_output=True)
    sheet_views([os.path.join(d, f"view_{a:03d}.png") for a in (0, 90, 180, 270)], os.path.join(d, "views.jpg"))
    shots, close = os.path.join(d, "views.jpg"), None
    try:                                                    # the check shots: the same viewer as your phone page
        import viewshot
        shots, close = viewshot.shoot(glb, os.path.join(d, "check"))
    except Exception as e:
        say(f"[check] viewer shots skipped ({e}) - the studio pictures are used")
    make_room("judging")
    verdict = check_model(cid, card, picked, d, glb, route, fam, shots, close, use)
    say(f"[check] {cid}: " + ("passed every realism check" if verdict.get("pass") else
                              "failed: " + ", ".join(verdict.get("failed", [])) + " - " + str(verdict.get("problems"))[:300]))
    if TRIAL:                                                # the engineer's test: the result, nothing sent anywhere
        json.dump({"verdict": verdict, "shots": shots, "close": close, "photo": picked["file"]},
                  open(os.path.join(d, "trial.json"), "w"), indent=1)
        return verdict

    # 7. YOU: Keep or Redo on your phone
    import askfirst
    probs = verdict.get("problems")
    note = ("The judge: looks right." if verdict.get("pass") else "The judge: " + (", ".join(probs) if isinstance(probs, list) else str(probs)))
    if setting("auto_keep") and verdict.get("pass"):           # the judge passed it: filed without asking you
        status(cid, verdict=verdict, views=os.path.relpath(shots, WORK),
               ref=os.path.relpath(picked["file"], WORK))
        r = file_away(cid, d)
        if not r.get("ok"):
            status(cid, step=f"stopped: delivery check failed: {r.get('why')}"[:300], ok=False)
        return
    if not verdict.get("pass") and engineer_turn(cid):         # your AI's engineer works out why, and fixes the cause
        status(cid, step="failed the realism check - your AI's engineer is working out why", verdict=verdict,
               views=os.path.relpath(shots, WORK), ref=os.path.relpath(picked["file"], WORK))
        try:
            import engineer
            res = engineer.fix(cid, card, verdict, shots, close, picked["file"], d, log=say, beat=beat,
                               status=lambda **k: status(cid, **k))
        except Exception as e:
            import traceback
            traceback.print_exc()
            res = {"kept": False, "why": f"the engineer stopped: {e}"}
        if res.get("kept"):
            global RESTART
            RESTART = True
            status(cid, step=f"your AI's engineer fixed the builder ({', '.join(res.get('before', []))} -> "
                             f"{', '.join(res.get('after', [])) or 'all checks pass'}) - rebuilding with the fix",
                   engineer={k: res.get(k) for k in ("sha", "summary", "before", "after")})
            return
        verdict = dict(verdict, engineer=(res.get("summary") or res.get("why") or "")[:600])
    if not verdict.get("pass"):                                  # never shown to you as finished when it isn't
        failed = ", ".join(verdict.get("failed", [])) or "the judge's check"
        tried = (" - your AI's engineer: " + verdict["engineer"][:200]) if verdict.get("engineer") else ""
        status(cid, step=f"failed the realism check ({failed}) - not sent to you{tried}",
               ok=False, verdict=verdict, views=os.path.relpath(shots, WORK), ref=os.path.relpath(picked["file"], WORK))
        say(f"[check] {cid}: not sent to your phone - failed: {failed}")
        return
    sent = askfirst.ask_review(cid, product, shots, note[:600])
    if not sent:
        say(f"[phone] {cid}: the Keep/Redo message did not reach your phone - it is sent again every minute until it does")
    tex = next((p for p in (os.path.join(d, "label.png"), os.path.join(d, "skin", "atlas.png"),
                            os.path.join(d, "reference.png")) if os.path.exists(p)), None)
    status(cid, step="waiting for your Keep or Redo on your phone", ok=bool(verdict.get("pass")), verdict=verdict,
           photos=n_found, good=n_good, views=os.path.relpath(shots, WORK),
           label=os.path.relpath(tex, WORK) if tex else None, ref=os.path.relpath(picked["file"], WORK), note="",
           sent=bool(sent))


def resend():
    """A Keep/Redo message that never reached your phone (Telegram hiccup) is sent again, every minute, until it
    does - the page never says "on your phone" for something that isn't there."""
    st = jload(STATUS, {})
    ap = jload(os.path.join(HB, "approvals.json"), {})
    late = [k for k, v in st.items() if str(v.get("step", "")).startswith("waiting for your Keep")
            and v.get("sent") is False and k not in ap]
    if not late:
        return
    ownmods.add_path("~/.hellbox/ai")
    import askfirst
    for cid in late:
        v = st[cid]
        sheet = os.path.join(WORK, v.get("views", ""))
        if not os.path.exists(sheet):
            continue
        ver = v.get("verdict") or {}
        probs = ver.get("problems")
        note = ("The judge: looks right." if ver.get("pass") else "The judge: " +
                (", ".join(map(str, probs)) if isinstance(probs, list) else str(probs or "")))
        if askfirst.ask_review(cid, v.get("product", cid), sheet, note[:600]):
            say(f"[phone] {cid}: Keep/Redo message delivered")
            status(cid, sent=True)


def sheet_views(paths, out, cell=(300, 400)):
    """The four studio pictures side by side, each cropped to the object (same crop for all four, so sizes stay
    comparable) so it fills its picture instead of sitting small in a big gray frame."""
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in paths]
    boxes = []
    for im in ims:
        a = np.asarray(im).astype(int)
        diff = np.abs(a - a[2, 2]).sum(-1) > 30                   # anything that isn't the plain backdrop
        ys, xs = np.where(diff)
        if len(ys):
            boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
    if boxes:
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hh = (y1 - y0) * 1.12 / 2
        hw = max((x1 - x0) * 1.12 / 2, hh * cell[0] / cell[1])
        hh = max(hh, hw * cell[1] / cell[0])
        crop = (int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh))
        ims = [im.crop(crop) for im in ims]
    sheet = Image.new("RGB", (cell[0] * len(ims), cell[1]), ims[0].getpixel((2, 2)))
    for k, im in enumerate(ims):
        sheet.paste(im.resize(cell, Image.LANCZOS), (k * cell[0], 0))
    sheet.save(out, quality=90)
    return out


def make_room(for_what):
    """Your Mac's memory, one kind of work at a time: before drawing, the judging AIs are let go (Ollama's own
    keep_alive 0); before judging, the drawing room lets go of its models (ComfyUI's own /free). Both load again
    by themselves when next needed."""
    import turnaround as T
    import vet as V
    if for_what == "judging":
        T.free_room()
        return
    ps = lambda: [m["name"] for m in json.loads(urllib.request.urlopen(V.OLLAMA + "/api/ps", timeout=20).read())
                  .get("models", [])]
    try:
        asked = {}
        for name in ps():
            asked[name] = V._call("/api/generate", {"model": name, "keep_alive": 0}, timeout=60)
        t = time.time()
        while ps() and time.time() - t < 30:       # a brain answering another of your tools lets go when it's done
            time.sleep(2)
        left = ps()
        if left:
            say(f"(still loaded - another of your tools is using it: {', '.join(left)})")
        return asked, left
    except Exception as e:
        say(f"(could not free the judging AIs: {e})")
        return {}, []


def read_words(png, use):
    """The judge reads every word and number on a picture, exactly as spelled."""
    import vet as V
    q = 'Read every word and number printed in this picture, exactly as spelled. Answer ONLY JSON: {"words": ["..."]}'
    try:
        return [w for w in V.ask(use, q, [png], think=False).get("words", []) if isinstance(w, str) and w.strip()]
    except Exception as e:
        say(f"[texture] could not read the words: {e}")
        return []


def label_words(pngs, use):
    """The words printed on a label, each confirmed by two independent reads before it may be printed: your AI reads
    every picture twice (two different questions) and the text reader (Apple's own) reads it once; a line counts
    when both AI reads saw it, or the text reader saw it too. A word only one read 'saw' is never printed."""
    import difflib
    import vet as V
    import measure as MS
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    q2 = ('Read the printed words in this picture again, slowly, line by line, exactly as spelled (keep numbers, '
          'symbols like (R) and TM, and capitals as printed). Answer ONLY JSON: {"lines": ["..."]}')
    out = []
    for png in pngs:
        a = read_words(png, use)
        try:
            b = [x for x in V.ask(use, q2, [png], think=False).get("lines", []) if isinstance(x, str)]
        except Exception:
            b = []
        try:
            o = MS.read_lines(png)
        except Exception:
            o = []
        an, bn, on = [norm(x) for x in a], [norm(x) for x in b], [norm(x) for x in o]
        like = lambda w, pool: any(difflib.SequenceMatcher(None, norm(w), x).ratio() >= 0.8 for x in pool if x)
        for w in a:                                        # the first read, confirmed by the second or the reader
            if norm(w) and like(w, bn + on) and w not in out:
                out.append(w)
        for w in o:                                        # the reader's lines, confirmed by either AI read
            if norm(w) and like(w, an + bn) and not like(w, [norm(x) for x in out]):
                out.append(w)
    say(f"[texture] words confirmed by two reads: {out}")
    return out


def run_blender(script, *args):
    r = subprocess.run([PY, os.path.join(HERE, "shapes", script), "--", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Blender ({script}) failed: " + (r.stderr or r.stdout)[-400:])


def setting(name):
    """Your switches, in ~/crushed-render/remaster/settings.json (both on unless you turn them off):
    auto_pick - a clear-winner photo is used without asking you; auto_keep - a judge-passed asset is filed
    without asking you. Close calls and failures always come to your phone."""
    return jload(os.path.join(WORK, "settings.json"), {}).get(name, True)


def _item_px(f):
    """How many pixels the item spans in its photo (its cut-out's longer side) - measured, not judged."""
    try:
        from PIL import Image
        im = Image.open(f["file"])
        m = np.asarray(Image.open(f["mask"]).convert("L").resize(im.size)) > 127
        ys, xs = np.where(m)
        if not len(xs):
            return 0
        px = max(int(np.ptp(ys)) + 1, int(np.ptp(xs)) + 1)
        # a blown-up thumbnail has many pixels but little in them: under half a bit per pixel as a JPEG, its
        # real detail is counted as at most 400 px
        return px if os.path.getsize(f["file"]) * 16 >= im.size[0] * im.size[1] else min(px, 400)
    except Exception:
        return 0


def auto_pick(cid, cands, d):
    """Pick for you only when it's clear: the top photo is a real photo showing at least 3 of the card's marks of
    the right version, no wrong-version mark, and it beats the next one by a wide margin."""
    pf, cf = os.path.join(HB, "picks.json"), os.path.join(d, "candidates.json")
    picks = jload(pf, {})
    if not setting("auto_pick") or cid in picks or os.path.exists(cf) or not cands:
        return
    v = cands[0].get("vet") or {}
    lead = rank(cands[0]) - (rank(cands[1]) if len(cands) > 1 else 0)
    import notes as NT
    note = NT.text(cid)
    if v.get("only_quick") or v.get("note") == "only the quick look":       # (the second: as written before)
        say("[pick] not picked by itself: the top photo had only the quick look - you choose")
        return
    if note and (v.get("note_ok") is not True or v.get("note") != note[:200]):
        say("[pick] not picked by itself: the top photo was not judged to show what your note asks for - you choose")
        return                                                # your note decides the version: never guessed past it
    big = _item_px(cands[0])
    if big < 800:                                             # a small or blown-up web picture can't carry the print
        say(f"[pick] not picked by itself: the item in the top photo is only {big} px tall - too small to build "
            "from - you choose")
        return
    if isinstance(v.get("year_off"), int) and v["year_off"] > 0:
        say(f"[pick] not picked by itself: the top photo's item was made about {v['year_off']} years outside the "
            "item's era (read off its printed dates) - you choose")
        return
    if v.get("kind") == "photo" and int(v.get("seen") or 0) >= 3 and v.get("avoid_seen") is not True and lead >= 4:
        json.dump({"files": [{"file": c["file"], "mask": c["mask"], "vet": c["vet"]} for c in cands],
                   "asked": time.time(), "auto": True}, open(cf, "w"), indent=1)
        picks[cid] = {"pick": "1", "at": time.time(), "auto": True}
        json.dump(picks, open(pf, "w"), indent=1)
        say(f"[pick] clear winner, picked by itself: {os.path.basename(cands[0]['file'])} (lead {lead:.1f})")


def rank(f):
    """Which photos you see first - the same rule for every item: the card's right-version marks it shows count
    most, a wrong-version mark sinks it, a real photo beats an ad or a render, Google's own order breaks ties."""
    v = f["vet"] or {}
    r = v.get("match", 0) + 3 * min(int(v.get("seen") or 0), 5)
    r -= 8 if v.get("avoid_seen") is True else 0
    r -= 8 if v.get("era_ok") is False else 0                 # a modern redesign is not this item
    if isinstance(v.get("year_off"), int):                    # made outside the item's era ("90s"), read off its
        r -= 2 * v["year_off"]                                 # printed dates: the further outside, the lower
    r += 6 if v.get("note_ok") is True else -12 if v.get("note_ok") is False else 0   # your note decides the version
    r += {"photo": 4, "package": 1, "render": -2, "ad": -4}.get(v.get("kind"), 0)
    r += 0.5 if v.get("view") == "front" else 0
    return r - f.get("order", 0) * 0.02


def size_fits(f, size_m, tol=0.35):
    """The item's outline in the photo must have the proportions of the real thing (any two of its catalog
    sides), so a D cell never passes for an AA and a tub never for a bottle. Several touching items can't be
    measured one by one, so those are left for you to judge."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    m = np.asarray(Image.open(f["mask"]).convert("L")) > 127
    lab, n = ndimage.label(m)
    if not n:
        return False
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == k)
    h, w = int(np.ptp(ys)) + 1, int(np.ptp(xs)) + 1
    got = max(h, w) / max(min(h, w), 1)
    dims = sorted(x for x in size_m if x > 0)
    wants = {dims[i] / dims[j] for i in range(len(dims)) for j in range(i) if dims[j] > 0}
    if any(abs(got - w) / w <= tol for w in wants):
        return True
    return int((f.get("vet") or {}).get("count") or 1) > 1


def era_evidence(d):
    """Names read on photos a judge placed in the item's era (a real photo, a fair match): what the item was really
    called on its label back then, from the photos themselves."""
    out = []
    for f in jload(os.path.join(d, "vetted.json"), []):
        v = f.get("vet") or {}
        if v.get("era_ok") is True and v.get("kind") == "photo" and int(v.get("match") or 0) >= 4 and v.get("version_seen"):
            out.append(str(v["version_seen"])[:80])
    return out


def more_searches(card, use):
    """When you turn every photo down: different searches than last time, the way a collector digs. Search words
    only (never facts); none that already ran."""
    import vet as V
    ran = {s.lower().strip() for s in card.get("searches", [])}
    ran |= {str(f.get("title", "")).replace("Google Images:", "").strip().lower()
            for f in jload(os.path.join(WORK, "hunt", card.get("id", ""), "found.json"), [])}
    ev = card.get("era_version") or {}
    import era as ERA
    era_w = ERA.words(card.get("year")) if card.get("year") else ""
    q = (f"I need real photos of this exact old product: {card['product']}"
         + (f" - in the {era_w} it was sold as {' / '.join(ev['names'])}" if ev.get("names") else "")
         + f". It is recognized by: {'; '.join(list(ev.get('marks') or []) + card.get('recognize', []))}. "
         + f"These searches did not find it: {'; '.join(sorted(ran)[:20])}. "
         "Give 5 different Google Images searches a collector would type (other names it was sold under, its "
         "model or catalog number, 'vintage', 'NOS', 'eBay', the decade), each 2 to 7 words. "
         "Answer ONLY JSON: {\"searches\": [\"...\"]}")
    try:
        body = {"model": use, "stream": False, "format": "json", "think": True, "options": {"temperature": 0.4},
                "messages": [{"role": "user", "content": q}]}
        out = [x for x in json.loads(V._call("/api/chat", body)["message"]["content"]).get("searches", [])
               if isinstance(x, str)]
    except Exception as e:
        say(f"[hunt] no new searches from your AI: {e}")
        out = []
    name = (ev.get("names") or [card["product"].split(",")[0]])[0]   # the era's own name first
    plain = [f"{era_w} {name}", f"vintage {name} {era_w}", f"{name} NOS", f"old {name} ebay"]   # a collector's
    out = [re.sub(r"\s+", " ", ERA.in_words(x, card.get("year")) if card.get("year") else x).strip()   # plain searches
           for x in out + plain]
    out = list(dict.fromkeys(x for x in out if x and x.lower() not in ran and len(x.split()) <= 9))[:5]
    say("[hunt] digging deeper with: " + "; ".join(out))
    return out


def finish_files(cid, d):
    """Every format and the check pictures for one asset (into <build>/model/export), right after the build:
    .obj + .mtl, .3ds, .ma and every texture as PNG + JPG (exports.py), the phone page's light copy (webglb.py) and
    a cutaway picture of the insides (cutaway.py). Each step has a time limit, and each output must be newer than
    this run's start - a file left over from an older build counts as missing, and is set aside in
    <build>/model/stale-<time> so nothing can pick it up as new. The builder's own .blend .glb .fbx .usdc are
    matched against its made.json (the fingerprint of each file it wrote).
    -> {"ok", "started", "built_at", "steps": {step: {"ok", "why", "seconds", ...}}}, also kept as
    model/export/finish.json for file_away."""
    import deliver
    started = time.time()
    mdir = os.path.join(d, "model")
    exp = os.path.join(mdir, "export")
    prev = os.path.join(exp, "previews")
    blend, glb = os.path.join(mdir, cid + ".blend"), os.path.join(mdir, cid + ".glb")
    web, cut = os.path.join(mdir, cid + "_web.glb"), os.path.join(d, "check", "cutaway.png")
    os.makedirs(prev, exist_ok=True)
    os.makedirs(os.path.dirname(cut), exist_ok=True)
    stale = os.path.join(mdir, "stale-" + time.strftime("%Y%m%d-%H%M%S"))
    res = {"ok": False, "started": started, "built_at": None, "steps": {}}

    def fresh(p, since=started):
        return os.path.exists(p) and os.path.getmtime(p) >= since - 2

    def set_aside(paths):                                 # moved, never deleted: <build>/model/stale-<time>/
        for p in paths:
            if os.path.exists(p):
                os.makedirs(stale, exist_ok=True)
                shutil.move(p, os.path.join(stale, os.path.relpath(p, d).replace(os.sep, "__")))

    # the builder's files: exactly the ones this build wrote (made.json), not leftovers from an older build
    made = jload(os.path.join(mdir, "made.json"), None)
    b = {"ok": False, "why": "", "good": [], "sha1": {}}
    bad = []
    for ext in ("blend", "glb", "fbx", "usdc"):
        p = os.path.join(mdir, f"{cid}.{ext}")
        if not os.path.exists(p):
            bad.append(f".{ext} was not made" + (f" ({made['failed'][ext]})" if made and ext in made.get("failed", {})
                                                 else ""))
            continue
        h = deliver.sha1(p)
        rec = (made or {}).get("files", {}).get(ext)
        if made and not rec:
            bad.append(f".{ext} is not from this build ({made.get('failed', {}).get(ext, 'the builder did not write it')})")
            set_aside([p])
        elif made and rec["sha1"] != h:
            bad.append(f".{ext} is an older file, not the one this build wrote")
            set_aside([p])
        elif not made and os.path.exists(blend) and abs(os.path.getmtime(p) - os.path.getmtime(blend)) > 900:
            bad.append(f".{ext} is much older or newer than the .blend (not from the same build)")
            set_aside([p])
        else:
            b["good"].append(ext)
            b["sha1"][ext] = h
    if made:
        res["built_at"] = made.get("started") or made.get("at")
        if (made.get("files") or {}).get("physics.json"):
            b["physics_sha1"] = made["files"]["physics.json"]["sha1"]
    elif os.path.exists(blend):
        res["built_at"] = os.path.getmtime(blend) - 900
        b["note"] = "no builder record (built before the delivery check existed) - the file times were used"
    b["ok"], b["why"] = not bad, "; ".join(bad)
    res["steps"]["builder"] = b
    if bad:
        say(f"[finish] {cid}: builder files: {b['why']}")

    def step(name, script, args, timeout, outputs, src_ok):
        r = {"ok": False, "why": "", "seconds": 0.0, "outputs": [os.path.relpath(o, d) for o in outputs]}
        res["steps"][name] = r
        if not src_ok:
            r["why"] = f"nothing to make it from ({os.path.basename(args[0])} is missing or from an older build)"
        else:
            t0 = time.time()
            tag = "[" + script.split(".")[0] + "]"
            try:
                p = subprocess.run([PY, os.path.join(HERE, script), "--", *args], capture_output=True, text=True,
                                   timeout=timeout)
                lines = (p.stdout or "").splitlines()
                for line in lines:
                    if line.startswith(tag):
                        say(line)
                late = [os.path.basename(o) for o in outputs if not fresh(o)]
                if p.returncode != 0:
                    said = [l for l in lines if l.startswith(tag) and "FAILED" in l]
                    err = [l for l in (p.stderr or "").splitlines() if l.strip()]
                    r["why"] = f"stopped with an error (code {p.returncode}): " + \
                               ((said[-1] if said else "") or (err[-1] if err else "no message"))[-300:]
                elif late:
                    r["why"] = "did not make " + ", ".join(late)
                else:
                    r["ok"] = True
            except subprocess.TimeoutExpired:
                r["why"] = f"took longer than {timeout // 60} minutes and was stopped"
            except Exception as e:
                r["why"] = f"could not run: {e}"
            r["seconds"] = round(time.time() - t0, 1)
        if not r["ok"]:
            set_aside([o for o in outputs if os.path.exists(o) and not fresh(o)])
            say(f"[finish] {cid}: {name} FAILED - {r['why']}")
        return r["ok"]

    blend_ok, glb_ok = "blend" in b["good"], "glb" in b["good"]
    exp_out = [os.path.join(exp, f"{cid}.{x}") for x in ("obj", "mtl", "3ds", "ma")] + [os.path.join(exp, "exports.json")]
    if step("exports", "exports.py", [blend, exp, cid], 600, exp_out, blend_ok) and \
            not jload(os.path.join(exp, "exports.json"), {}).get("ok"):
        res["steps"]["exports"].update(ok=False, why="exports.json does not say every file was written")
    step("web_glb", "webglb.py", [blend, web], 600, [web], blend_ok)          # the phone page's light copy
    if step("cutaway", "cutaway.py", [glb, cut], 900, [cut], glb_ok):
        try:
            deliver.picture_pair(cut, os.path.join(prev, "cutaway"))
        except Exception as e:
            res["steps"]["cutaway"].update(ok=False, why=f"the picture could not be saved: {e}")
    if not res["steps"]["cutaway"]["ok"]:
        set_aside([p for p in (os.path.join(prev, "cutaway.png"), os.path.join(prev, "cutaway.jpg"))
                   if os.path.exists(p) and not fresh(p)])
    res["ok"] = all(s.get("ok") for s in res["steps"].values())
    json.dump(res, open(os.path.join(exp, "finish.json"), "w"), indent=1)
    say(f"[finish] {cid}: " + ("every format, the phone copy and the cutaway made" if res["ok"] else
                               "NOT all made: " + "; ".join(f"{k}: {v['why']}" for k, v in res["steps"].items()
                                                            if not v.get("ok"))))
    return res


def file_away(cid, d):
    """You said Keep (or the check passed): the asset's own folder in ~/Desktop/Asset Library/<item>, holding every
    format (.blend .fbx .obj+.mtl .3ds .ma .glb .usdc), textures/ (PNG + JPG), previews/ (PNG + JPG: all around,
    close-ups, cutaway, studio, the photo it was made from), physics.json (how each part crushes), made_of.json
    (how it's made) and README.txt (exactly what is in the folder, what isn't and why, where each side came from).
    The folder is put together fresh in a hidden folder next to it, every file in it is opened again from scratch
    (deliver.py), and only if every one opens whole is it moved into place. An older folder for the item goes to
    ~/Desktop/_to delete/asset-library/<item>-<time> with a note - never deleted. Only files THIS build made go in
    (an output older than its build counts as missing). PNG and JPG of every texture and every preview.
    -> deliver.verify's result. On success it is marked done here. On failure nothing is filed or marked: the
    attempt goes to _to delete with a note and {"ok": False, "why": ...} comes back for the caller to show. A build
    that already failed is not put together again for 6 hours (so a waiting Keep can't fill _to delete).
    CRUSHED_SHELF points the Asset Library elsewhere (tests); _to delete follows HOME."""
    import deliver
    shelf = os.path.expanduser(os.environ.get("CRUSHED_SHELF") or SHELF)
    trash = os.path.expanduser("~/Desktop/_to delete/asset-library")
    mdir = os.path.join(d, "model")
    exp = os.path.join(mdir, "export")
    ts = time.strftime("%Y%m%d-%H%M%S")

    def put_aside(path, label, note):                    # into _to delete with a note, never deleted
        os.makedirs(trash, exist_ok=True)
        to, k = os.path.join(trash, label), 2
        while os.path.exists(to):
            to, k = os.path.join(trash, f"{label}-{k}"), k + 1
        shutil.move(path, to)
        open(to + ".txt", "w").write(note)
        return to

    os.makedirs(shelf, exist_ok=True)
    for n in os.listdir(shelf):                           # an attempt left half-done when a run stopped
        if n.startswith(f".{cid}.incoming-"):
            put_aside(os.path.join(shelf, n), f"{cid}-unfinished-{ts}",
                      f"A half-made copy of {cid} left in your Asset Library when a run stopped partway. "
                      "Nothing in it was filed. Safe to delete.\n")
    fin = jload(os.path.join(exp, "finish.json"), None)
    if not fin or not fin.get("steps"):                   # built before this record existed: make the files now
        say(f"[keep] {cid}: no record of the finishing step - making every format now")
        fin = finish_files(cid, d)
    stamp = os.path.join(exp, "delivery.json")
    last = jload(stamp, {})
    if last.get("started") == fin["started"] and last.get("ok") is False and time.time() - last.get("at", 0) < 6 * 3600:
        say(f"[keep] {cid}: this build already failed the delivery check ({last.get('why')}) - not tried again "
            "until it is rebuilt (or in 6 hours)")
        return dict(last, again=True)
    steps, built = fin.get("steps", {}), fin.get("built_at") or 0
    tmp = os.path.join(shelf, f".{cid}.incoming-{ts}")
    os.makedirs(os.path.join(tmp, "textures"))
    os.makedirs(os.path.join(tmp, "previews"))
    not_here, extra = [], []

    def fresh(p, since):
        return os.path.exists(p) and os.path.getmtime(p) >= since - 2

    # the builder's formats: only the files this build wrote, checked again by fingerprint
    bstep = steps.get("builder", {})
    for ext in bstep.get("good", []):
        src = os.path.join(mdir, f"{cid}.{ext}")
        if os.path.exists(src) and deliver.sha1(src) == bstep.get("sha1", {}).get(ext):
            shutil.copy2(src, tmp)
        else:
            extra.append(f"{cid}.{ext}: changed since this build was finished - rebuild it")
    if not bstep.get("ok"):
        not_here.append(f"from the builder: {bstep.get('why') or 'no record'}")
    # .obj .mtl .3ds .ma and every texture (PNG + JPG): exactly what exports.py wrote for this build
    man = jload(os.path.join(exp, "exports.json"), {})
    if steps.get("exports", {}).get("ok") and man.get("ok") and man.get("started", 0) >= fin["started"] - 2:
        for rel in man.get("files", []):
            src = os.path.join(exp, rel)
            if fresh(src, fin["started"]):
                os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
                shutil.copy2(src, os.path.join(tmp, rel))
    else:
        not_here.append(".obj .mtl .3ds .ma and the texture maps: the export step failed - " +
                        (steps.get("exports", {}).get("why") or "it never ran"))
    utex = os.path.join(mdir, "textures")                 # pictures the .usdc names that exports didn't write
    if "usdc" in bstep.get("good", []) and os.path.isdir(utex):
        for f in sorted(os.listdir(utex)):
            src, stem = os.path.join(utex, f), os.path.splitext(f)[0]
            if f.lower().endswith((".png", ".jpg", ".jpeg")) and fresh(src, built) and \
                    not os.path.exists(os.path.join(tmp, "textures", f)):
                deliver.picture_pair(src, os.path.join(tmp, "textures", stem))
    # previews, PNG + JPG: only pictures made after this build
    shots = ((os.path.join(d, "check", "viewer_around.jpg"), "all_around", built, "the all-around pictures"),
             (os.path.join(d, "check", "viewer_close.jpg"), "close_ups", built, "the close-up pictures"),
             (os.path.join(exp, "previews", "cutaway.png"), "cutaway", fin["started"], "the cutaway picture"),
             (os.path.join(d, "views.jpg"), "studio", built, "the four studio pictures"))
    for src, name, since, what in shots:
        if fresh(src, since):
            deliver.picture_pair(src, os.path.join(tmp, "previews", name))
        else:
            why = steps.get("cutaway", {}).get("why") if name == "cutaway" else ""
            not_here.append(f"{what}: not made for this build" + (f" ({why})" if why else ""))
    if not any(os.path.exists(os.path.join(tmp, "previews", n + ".png")) for n in ("studio", "all_around")):
        extra.append("previews/: no picture of the outside was made for this build")
    ref = jload(STATUS, {}).get(cid, {}).get("ref")
    if ref and os.path.exists(os.path.join(WORK, ref)):
        deliver.picture_pair(os.path.join(WORK, ref), os.path.join(tmp, "previews", "made_from_photo"))
    phys = os.path.join(mdir, "physics.json")
    if os.path.exists(phys) and (deliver.sha1(phys) == bstep.get("physics_sha1") or
                                 ("physics_sha1" not in bstep and bstep.get("note") and fresh(phys, built))):
        shutil.copy2(phys, tmp)
    product = cid
    try:
        import cards
        c = cards.make(cid)
        product = c.get("product") or cid
        json.dump({"product": c.get("product"), "construction": c.get("construction"), "size_m": c.get("size")},
                  open(os.path.join(tmp, "made_of.json"), "w"), indent=1)
    except Exception as e:
        say(f"[keep] {cid}: made_of.json skipped ({e})")
    dossier = jload(os.path.join(WORK, "dossier", cid + ".json"), None)
    try:                                                   # the master-asset record (catalog.py): asset.json
        import cards
        import catalog
        catalog.record(cid, tmp, cards.make(cid), dossier if isinstance(dossier, dict) else None,
                       jload(os.path.join(tmp, "physics.json"), {}))     # the central copy only once it is filed
    except Exception as e:
        say(f"[keep] {cid}: the catalog record could not be written ({e})")
    deliver.write_readme(tmp, cid, product, not_here, dossier if isinstance(dossier, dict) else None)

    res = deliver.verify(tmp, cid)
    res["problems"] += extra
    res["ok"] = res["ok"] and not extra
    res["not_here"] = not_here
    if not res["ok"]:
        cause = [f"the {k} step failed: {v.get('why')}" for k, v in steps.items()
                 if k in ("builder", "exports") and not v.get("ok")]
        why = deliver.summary(res) + (" - because " + "; ".join(cause) if cause else "")
        aside = put_aside(tmp, f"{cid}-failed-check-{ts}",
                          f"A copy of {cid} that FAILED the delivery check, so it was not put in your Asset Library "
                          f"(any older copy there is untouched).\nWhy: {why}\n\nEvery problem found:\n" +
                          "\n".join(["  - missing: " + p for p in res["missing"]] + ["  - " + p for p in res["problems"]])
                          + "\n\nSafe to delete.\n")
        out = {"ok": False, "why": why, "started": fin["started"], "at": time.time(), "set_aside": aside,
               "missing": res["missing"], "problems": res["problems"]}
        json.dump(out, open(stamp, "w"), indent=1)
        say(f"[keep] {cid}: delivery check failed - {why}. Not filed (the attempt is in {aside})")
        return dict(res, **out)
    dst = os.path.join(shelf, cid)
    if os.path.lexists(dst):
        put_aside(dst, f"{cid}-{ts}", f"The older copy of {cid} from your Asset Library, replaced "
                                      f"{time.strftime('%B %-d, %Y at %-I:%M %p')} by a newer build that passed the "
                                      "delivery check. Safe to delete once you have looked.\n")
    os.rename(tmp, dst)
    if not TRIAL:                                          # so the phone page spins the newest build
        pend = os.path.join(ROOT, "assets", "models_pending", cid)
        os.makedirs(pend, exist_ok=True)
        web = os.path.join(mdir, cid + "_web.glb")
        light = steps.get("web_glb", {}).get("ok") and fresh(web, fin["started"])
        shutil.copy(web if light else os.path.join(dst, cid + ".glb"), os.path.join(pend, "model.glb"))
    json.dump({"ok": True, "why": "", "started": fin["started"], "at": time.time(), "folder": dst},
              open(stamp, "w"), indent=1)
    try:                                                   # filed: now the central catalog gets its record
        import catalog
        rec = jload(os.path.join(dst, "asset.json"), None)
        if rec:
            catalog.save_central(rec)
    except Exception as e:
        say(f"[keep] {cid}: the central catalog record could not be written ({e})")
    status(cid, step="done - kept in your Asset Library", ok=True, note=dst)
    say(f"[keep] {cid} -> {dst} (every file opened whole)")
    return dict(res, ok=True, why="", folder=dst)


def start_over(cid, d):
    """You said Redo: the build is set aside (in _to delete, never deleted) and it is made again from your pick."""
    ap = jload(os.path.join(HB, "approvals.json"), {})
    ap.pop(cid, None)
    json.dump(ap, open(os.path.join(HB, "approvals.json"), "w"), indent=1)
    trash = os.path.expanduser(f"~/Desktop/_to delete/remaster/{cid}-redo-{time.strftime('%Y%m%d-%H%M%S')}")
    for name in ("model", "skin"):
        if os.path.exists(os.path.join(d, name)):
            os.makedirs(trash, exist_ok=True)
            shutil.move(os.path.join(d, name), os.path.join(trash, name))
    say(f"[redo] {cid}: the old build is in {trash}")


def say(*a):
    print(*a, flush=True)


def progress(cid, stage):
    """A log that also puts what your AI is doing right now on your phone page (the page itself refreshes at most
    every 90 seconds): "4/7 your AI gets to know the item - careful look 3 of 9 ..." instead of one old line."""
    def log(*a):
        say(*a)
        msg = " ".join(str(x) for x in a)
        if msg.startswith(("[dossier]", "[facts]", "[family]", "[parts]")):
            short = re.sub(r"^\[\w+\]\s*", "", msg)
            short = short[len(cid) + 1:].strip() if short.startswith(cid + ":") else short
            status(cid, step=f"{stage} - {short[:150]}")
    return log


def beat(doing):
    """The heartbeat the watchdog reads: when the run last did anything, and what."""
    try:
        json.dump({"at": time.time(), "doing": doing}, open(os.path.join(WORK, "heartbeat.json"), "w"))
    except Exception:
        pass


def _beating():
    """While the run waits on one long job (a drawing, Hunyuan), it still says it's alive every minute - but only
    while those jobs really are moving: the drawing room is checked to be answering."""
    import threading

    def loop():
        while True:
            time.sleep(60)
            try:
                urllib.request.urlopen(os.environ.get("DRAWING_ROOM", "http://127.0.0.1:8188") + "/system_stats",
                                       timeout=15).read()
                beat("waiting on a long job (drawing room answering)")
            except Exception:
                pass
    threading.Thread(target=loop, daemon=True).start()


def status(cid, **kw):
    beat(f"{cid}: {kw.get('step', '')}")
    if TRIAL:                                         # a test build: the real status and your page are left alone
        if kw.get("step"):
            say(f"[trial] {kw['step']}")
        return
    os.makedirs(OUT, exist_ok=True)

    def change(s):
        if "product" in kw or not isinstance(s.get(cid), dict):   # a fresh run: nothing left over from the last one
            s[cid] = {}
        s[cid].update(kw, at=time.time())
    update_json(STATUS, change)                      # locked, whole-or-nothing, with a backup
    global _LAST
    final = kw.get("step", "").startswith(("done", "stopped", "no ")) or "ok" in kw
    if final or time.time() - _LAST > 90:          # the phone page updates at most every 90 s, and always at the end
        _LAST = time.time()
        try:
            page()
        except Exception as e:
            say(f"(page skipped: {e})")


_LAST = 0.0


def your_pick(cid, product, cands, d):
    """The photo you picked on your phone, or None while we wait (or if you said none of these)."""
    picks_f = os.path.expanduser("~/.hellbox/picks.json")
    cf = os.path.join(d, "candidates.json")
    picks = json.load(open(picks_f)) if os.path.exists(picks_f) else {}
    p = picks.get(cid)
    if p and os.path.exists(cf):
        shown = json.load(open(cf))["files"]
        if p["pick"] == "none":
            sf = os.path.join(d, "shown.json")
            old = json.load(open(sf)) if os.path.exists(sf) else []
            json.dump(old + [x["file"] for x in shown], open(sf, "w"), indent=1)
            os.remove(cf)
            picks.pop(cid)
            json.dump(picks, open(picks_f, "w"), indent=1)
            return "none"
        f = shown[int(p["pick"]) - 1]
        return next((x for x in cands if x["file"] == f["file"]), f)
    if os.path.exists(cf):
        status(cid, step="waiting for your pick on your phone (Telegram)", ok=False)
        if WAIT:                                       # started by hand: wait here for the tap (up to 30 min)
            for _ in range(180):
                time.sleep(10)
                picks = json.load(open(picks_f)) if os.path.exists(picks_f) else {}
                if cid in picks:
                    say("[pick] you picked " + picks[cid]["pick"])
                    return your_pick(cid, product, cands, d)
        return None
    if not cands:
        status(cid, step="no usable photo found", ok=False)
        return None
    st = jload(STATUS, {})
    asking = [k for k, v in st.items() if str(v.get("step", "")).startswith("waiting for your pick") and k not in picks]
    if len(asking) >= 5:                               # never more than 5 photo sets waiting on your phone
        status(cid, step="in line for your pick (5 are already on your phone)", ok=False)
        return None
    if cid in picks:                                   # a tap on an older photo sheet must not count for this one
        picks.pop(cid)
        json.dump(picks, open(picks_f, "w"), indent=1)
    sheet = pick_sheet(cands, os.path.join(d, "pick_sheet.jpg"))
    ownmods.add_path("~/.hellbox/ai")
    import askfirst
    if not askfirst.ask_pick(cid, product, sheet, len(cands)):
        status(cid, step="could not send the photo choice to your phone - will try again next run", ok=False)
        return None
    json.dump({"files": [{"file": c["file"], "mask": c["mask"], "vet": c["vet"]} for c in cands], "asked": time.time()},
              open(cf, "w"), indent=1)
    status(cid, step="waiting for your pick on your phone (Telegram)", ok=False, pick_sheet=os.path.relpath(sheet, WORK))
    say("[pick] the best photos are on your phone (Hart's Telegram) - tap the true one")
    return your_pick(cid, product, cands, d) if WAIT else None


def pick_sheet(cands, out):
    """The photos side by side, big numbers on each, for your phone."""
    from PIL import Image, ImageDraw, ImageFont
    S = 512
    cols = 3 if len(cands) > 2 else len(cands)        # up to 9: three rows of three
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * S, rows * S), "white")
    try:
        font = ImageFont.load_default(size=72)
    except TypeError:
        font = ImageFont.load_default()
    for k, c in enumerate(cands):
        im = Image.open(c["file"]).convert("RGB")
        im.thumbnail((S - 16, S - 16), Image.LANCZOS)
        x, y = (k % cols) * S, (k // cols) * S
        sheet.paste(im, (x + (S - im.width) // 2, y + (S - im.height) // 2))
        dr = ImageDraw.Draw(sheet)
        dr.rectangle([x + 8, y + 8, x + 100, y + 100], fill="black")
        dr.text((x + 30, y + 14), str(k + 1), fill="yellow", font=font)
        dr.rectangle([x, y, x + S - 1, y + S - 1], outline="black", width=3)
    sheet.save(out, quality=90)
    return out


def reference(f, d, upright=False):
    """Your photo's item, cut out, centered on white with room around it - what Hunyuan looks at."""
    import numpy as np
    from PIL import Image
    import skin
    im, m = skin.one_item(f, upright)
    rgba = np.dstack([np.asarray(im), (m * 255).astype(np.uint8)])
    obj = Image.fromarray(rgba)
    side = int(max(obj.size) * 1.15)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(obj, ((side - obj.width) // 2, (side - obj.height) // 2), obj)
    out = os.path.join(d, "reference.png")
    sq.resize((1024, 1024), Image.LANCZOS).save(out)
    return out


PARTS_Q = ("Picture 1 is a straight-on photo of the top of a {product}. List every part soldered on it that stands up "
           "from the board - chips, memory chips, capacitors, crystals, connectors, pin headers, heatsinks, voltage "
           "regulators and transistors, sockets, jumpers, LEDs, inductors - biggest first, up to 60. For each: its type "
           "(one of chip, memory_chip, capacitor_electrolytic, capacitor_ceramic, resistor, crystal, connector, "
           "pin_header, heatsink, inductor, transistor, socket, led, jumper), its box as fractions of the picture "
           "(x0, y0, x1, y1 - 0..1 from the left edge and from the top edge) and its height in millimeters. "
           "Answer ONLY JSON: {{\"parts\": [{{\"type\": \"chip\", \"box\": [x0, y0, x1, y1], \"height_mm\": 2.4}}]}}")


def board_parts(front, product, use):
    """Every part on a circuit board, read off the photo by your AI (checked for sense)."""
    import vet as V
    try:
        r = V.ask(use, PARTS_Q.format(product=product), [front], think=False, side=1280)
    except Exception as e:
        say(f"[pcb] parts not read: {e}")
        return []
    out = []
    for p in r.get("parts", []) if isinstance(r, dict) else []:
        try:
            b = [float(v) for v in p["box"]]
            if max(b) > 1.5:                                    # answered in 0..1000
                b = [v / 1000 for v in b]
            x0, y0, x1, y1 = b
            if 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and (x1 - x0) * (y1 - y0) > 0.0004:
                out.append({"type": str(p.get("type", "chip")), "box": [x0, y0, x1, y1],
                            "height_mm": float(p.get("height_mm") or 0) or None})
        except Exception:
            continue
    return out


def family_of(card, use=None):
    """The item's manufacturing family (your AI names it once; kept on its card)."""
    if card.get("family"):
        return card["family"]
    try:
        sys.path.insert(0, os.path.join(HERE, "factory"))
        import factory
        import cards
        card["family"] = factory.family_of(card, model=use)
        json.dump(card, open(cards.path(card["id"]), "w"), indent=1)
    except Exception as e:
        say(f"[factory] family not named: {e}")
        card["family"] = ""
    return card["family"]


def other_sides(cid, card, picked, use, have=(), most=12, log=None, dossier=None):
    """A box has six sides and a buyer turns it over. The dossier (library/dossier.py) has already hunted every side
    three ways (this item, its sister flavors, nearby years) and planned which photo serves each side - including
    the backs and sides the FIRST hunt found, so a rebuild never loses them. This hands the box builder the photos
    its plan uses (this item's own, and the sister boxes whose item-specific parts get swapped), each cut out."""
    import dossier as DS
    log = log or say
    dos = dossier or DS.ensure(cid, card, picked, use=use, log=log)
    seen = {p["file"] for p in have}
    out = [p for p in DS.face_photos(dos, ("exact_photo", "template_photo")) if p["file"] not in seen][:most]
    for p in out:
        log(f"[texture] the plan's {p['plan']}: {os.path.basename(p['file'])} "
            f"({'this item' if p['source'] == 'exact_photo' else 'a sister box, its own parts swapped'})")
    return DS.with_masks(out, log)


def same_design(picked, others, use, want=2, dossier=None):
    """More photos of the very same design as your pick (for consistency): with a dossier, the photos its careful
    look found to be this exact item; without one, the judge compares the candidates with your pick."""
    import dossier as DS
    if dossier and dossier.get("faces"):
        out = [p for p in DS.face_photos(dossier, ("exact_photo",)) if p["file"] != picked["file"]][:want]
        say(f"[texture] the same item as your pick, from the dossier: {len(out)} more photo(s)")
        return DS.with_masks(out, say)
    import vet as V
    q = ("Do these two photos show the very same product design version (same label artwork, same words and "
         "layout, same colors), even if the angle or lighting differs? Answer ONLY JSON: {\"same\": true/false}")
    out = []
    for f in others[:8]:
        try:
            if V.ask(use, q, [picked["file"], f["file"]], think=False).get("same") is True:
                out.append(f)
        except Exception:
            pass
        if len(out) >= want:
            break
    say(f"[texture] same design as your pick: {len(out)} more photo(s)")
    return out


def hunyuan_paint(ref, out, bare=None):
    """Hunyuan3D 2.1 (Apple-chip build) in its own Python. With an exact shape: paints it. Without: makes the
    shape from the photo too (soft things)."""
    import hunyuan
    hy = hunyuan.home()
    if not hy:
        raise RuntimeError("Hunyuan3D is not installed yet - run the setup paste")
    glb = os.path.join(out, "textured.glb")
    if os.path.exists(glb):                     # made before a restart: kept (a Redo moves the model folder away first)
        return glb
    cmd = [os.path.join(hy, ".venv", "bin", "python"), os.path.join(HERE, "hunyuan.py"), ref, out]
    if bare:
        cmd += ["--paint", bare]
    r = subprocess.run(cmd, capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if line.startswith("[hunyuan]"):
            say(line)
    if r.returncode != 0 or not os.path.exists(glb):
        raise RuntimeError("Hunyuan3D did not finish: " + (r.stderr or r.stdout)[-400:])
    return glb


CHECKS = {
    "shape": "same shape and proportions as the real one",
    "print": "all the printing is there, crisp, spelled right and in the right places (no smeared or invented words)",
    "materials": "each part looks like what it is made of ({mats}): metal reads as real metal (never white or flat "
                 "gray paint), plastic as plastic, card as printed card; glossy where the real one is glossy",
    "layers": "separate layers read as separate, with real edges where they meet (a label or sleeve over a can, a "
              "cap on a bottle, flaps on a box, a seam where a wrap's ends meet)",
    "details": "these real details are there: {closeups}",
    "no_painted_light": "no light, shadow or glare is painted into the colors (a bright patch or dark side that "
                        "doesn't belong to the print)",
    "finished": "every side is finished: nothing blank, stretched, smeared, repeated, blurry or cut off",
    "not_cg": "the surfaces have the faint variation of a real object (gloss that changes, grain, slight wear) - "
              "nothing looks like perfectly clean computer plastic",
}


def inspect(sheet, photo, product, use, card=None, close=None):
    """The judge checks the finished model the way you'd look at it - in the same viewer your phone page uses, all
    around and up close - against the real photo and a fixed realism checklist built from how the item is made.
    Every check must pass for it to be kept without asking you; the failed ones are named."""
    import vet as V
    if not use:
        return {"pass": False, "problems": "no vision model installed"}
    c = (card or {}).get("construction") or {}
    mats = ", ".join(f"{L.get('part')}: {L.get('material', '').replace('_', ' ')}" for L in c.get("layers", [])) or "as the photo shows"
    closeups = "; ".join(c.get("closeups", [])) or "the small real details visible in the photo"
    lines = "\n".join(f' "{k}": {v.format(mats=mats, closeups=closeups)}' for k, v in CHECKS.items())
    def grid(f):                                           # a long row of 4 views -> 2 x 2, so each view is
        from PIL import Image                              # read bigger for the same reading time
        im = Image.open(f).convert("RGB")
        if im.width < 3 * im.height:
            return f
        w4 = im.width // 4
        g = Image.new("RGB", (2 * w4, 2 * im.height))
        for i in range(4):
            g.paste(im.crop((i * w4, 0, (i + 1) * w4, im.height)), ((i % 2) * w4, (i // 2) * im.height))
        out = f[:-4] + "_grid.jpg"
        g.save(out, quality=90)
        return out
    pics = [grid(sheet)] + ([grid(close)] if close else []) + [photo]
    what = ("Picture 1 shows the 3D model all around" + ("; picture 2 shows it up close (ends, seams, edges)" if close
            else "") + f"; the last picture is a real photo.")
    q = (f"{what} The product: {product}. A professional, photoreal product model must pass ALL of these checks. "
         f"Answer each one true or false:\n{lines}\nAnswer ONLY JSON: {{" +
         ", ".join(f'"{k}": true/false' for k in CHECKS) + ', "problems": ["short and specific, for each false"]}')
    try:
        v = V.ask(use, q, pics, side=1024)                 # (bigger pictures cost minutes of reading per item)
    except Exception as e:
        return {"pass": False, "problems": f"could not inspect: {e}"}
    failed = [k for k in CHECKS if v.get(k) is not True]
    v["failed"] = failed
    v["pass"] = not failed
    return v


PAGE_CSS = """
:root{--bench:#16171a;--panel:#1f2125;--ink:#ece9e2;--muted:#9c988f;--line:#2d2f34;--copper:#d38945;
 --ok:#3fae63;--bad:#d9573f;--work:#6fa3d8;--display:"Archivo Narrow","Arial Narrow",system-ui,sans-serif;
 --body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bench);color:var(--ink);font:15px/1.45 var(--body);padding-inline:16px;padding-block:14px 40px}
.wrap{max-width:980px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:6px 16px}
h1{font:700 1.5rem/1.1 var(--display);margin:0;letter-spacing:.01em}
.when{font:12px var(--mono);color:var(--muted)}
.tally{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
.tally div{background:var(--panel);border-radius:8px;padding:8px 12px}
.tally b{display:block;font:700 1.4rem var(--display);font-variant-numeric:tabular-nums}
.tally span{font:11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;display:grid;gap:10px;
 grid-template-columns:minmax(0,1fr)}
.top{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}
h2{font:700 1.08rem/1.2 var(--display);margin:0;flex:1 1 220px;min-width:0;text-wrap:balance}
.chip{font:11px var(--mono);letter-spacing:.05em;text-transform:uppercase;padding:3px 8px;border-radius:99px;border:1px solid}
.chip.you{color:var(--copper);border-color:var(--copper)}
.chip.kept{color:var(--ok);border-color:var(--ok)}
.chip.work{color:var(--work);border-color:var(--work)}
.chip.bad{color:var(--bad);border-color:var(--bad)}
.chip.line{color:var(--muted);border-color:var(--line)}
.step{margin:0;color:var(--muted);font-size:.9rem}
.notes{margin:0;font-size:.85rem;color:var(--ink)}
.notes em{font-style:normal;color:var(--muted)}
.pics{display:grid;grid-template-columns:minmax(0,1fr) 96px;gap:8px;align-items:start}
.pics img{width:100%;max-width:100%;border-radius:8px;display:block;background:#101113}
.pics figure{margin:0;display:grid;gap:4px}.pics figcaption{font:10px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.spin{justify-self:start;font:600 .9rem var(--body);color:var(--bench);background:var(--copper);padding:8px 14px;
 border-radius:8px;text-decoration:none}
.spin:focus-visible{outline:2px solid var(--ink);outline-offset:2px}

"""
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@700&'
         'family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@400;600&display=swap">')


def _state(v, cid="", picks=None, ap=None):
    """(chip class, chip words, sort order) for one item - what it needs, at a glance. Only says it needs you when
    it truly does: a tap already made shows as next up, a message that didn't arrive shows as being resent."""
    step = str(v.get("step", ""))
    if step.startswith("done"):
        return "kept", "kept", 3
    if step.startswith("waiting for your Keep"):
        if ap and cid in ap:
            return "line", "your tap is in - next up", 2
        if v.get("sent") is False:
            return "work", "resending to your phone", 2
        return "you", "your keep / redo", 0
    if step.startswith("waiting for your pick"):
        if picks and cid in picks:
            return "line", "your pick is in - next up", 2
        return "you", "your photo pick", 0
    if step.startswith(("stopped", "3 rounds", "no usable", "you said none", "failed")):
        return "bad", "needs attention", 1
    if step.startswith("in line"):
        return "line", "in line", 4
    return "work", "working", 2


def page():
    """The phone page, https://crushed-remaster.pages.dev: what needs you first, then what's being made, then
    what's kept. Every built item has its finished 3D model to spin (the newest build, never an older one)."""
    import html
    s = jload(STATUS, {})
    picks = jload(os.path.join(HB, "picks.json"), {})
    ap = jload(os.path.join(HB, "approvals.json"), {})
    cards, tally = [], {"you": 0, "work": 0, "kept": 0, "bad": 0}
    for cid, v in sorted(s.items(), key=lambda kv: (_state(kv[1], kv[0], picks, ap)[2], -kv[1].get("at", 0))):
        cls, words, _ = _state(v, cid, picks, ap)
        tally[cls] = tally.get(cls, 0) + 1
        ver = v.get("verdict") or {}
        probs = ver.get("problems")
        probs = ", ".join(map(str, probs)) if isinstance(probs, list) else str(probs or "")
        judge = ""
        if ver:
            judge = "<p class=notes><em>Judge:</em> " + (html.escape(probs) if probs else "looks right") + "</p>"
        pics = ""
        if v.get("views"):
            ref = (f'<figure><img src="{html.escape(v["ref"])}" alt="the photo it was made from">'
                   '<figcaption>made from</figcaption></figure>') if v.get("ref") else ""
            pics = (f'<div class=pics><img src="{html.escape(v["views"])}" alt="the finished 3D model from four sides">'
                    f'{ref}</div><a class=spin href="view.html?m={html.escape(cid)}&v={int(v.get("at", 0))}">'
                    "Spin it in 3D</a>")
        cards.append(f'<section class=card><div class=top><h2>{html.escape(v.get("product", cid))}</h2>'
                     f'<span class="chip {cls}">{words}</span></div>'
                     f'<p class=step>{html.escape(words.capitalize() if cls == "line" or words.startswith("resending") else str(v.get("step", "")))}</p>'
                     + (f'<p class=notes><em>Kind of thing:</em> {html.escape(str(v["family"]).replace("_", " "))}'
                        f' - built by {html.escape(str(v.get("builder", "")))}</p>' if v.get("family") else "")
                     + f'{judge}{pics}</section>')
    t = (f'<div class=tally><div><b>{tally["you"]}</b><span>need you</span></div><div><b>{tally["work"]}</b>'
         f'<span>being made</span></div><div><b>{tally["kept"]}</b><span>kept</span></div>'
         f'<div><b>{tally["bad"]}</b><span>need attention</span></div></div>')
    doc = (f"<!doctype html><meta charset=utf-8><title>Crushed Asset Library</title>{FONTS}<style>{PAGE_CSS}</style>"
           f'<div class=wrap><header><h1>Crushed Asset Library</h1><span class=when>updated '
           f'{time.strftime("%a %-I:%M %p")}</span></header>{t}{"".join(cards)}</div>')
    open(os.path.join(WORK, "index.html"), "w").write(doc)
    open(os.path.join(WORK, "view.html"), "w").write(VIEW)
    import remaster as RM
    RM.publish(force=True)


VIEW = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<meta name=robots content=noindex><title>Spin It in 3D</title>""" + FONTS + """
<script type=module src="https://unpkg.com/@google/model-viewer@4.0.0/dist/model-viewer.min.js"></script>
<style>""" + PAGE_CSS + """
html,body{height:100%}body{display:flex;flex-direction:column;gap:10px}
model-viewer{flex:1;min-height:420px;width:100%;border:1px solid var(--line);border-radius:12px;
 background:radial-gradient(circle at 50% 45%,#2b2d32 0%,var(--bench) 72%)}
a.back{color:var(--copper);font:13px var(--mono);text-decoration:none}
</style>
<a class=back href="./">&larr; all items</a><h1 id=n></h1>
<model-viewer id=m camera-controls auto-rotate rotation-per-second="18deg" shadow-intensity="1" exposure="1.05"
 environment-image="neutral" tone-mapping="aces" interaction-prompt="none" alt="the finished 3D model"></model-viewer>
<p class=step>Drag to turn it, pinch to zoom. This is the newest build of the file saved on your Mac.</p>
<script>
const q = new URLSearchParams(location.search), id = q.get("m") || location.hash.slice(1);
document.getElementById("n").textContent = id.replace(/_/g, " ");
document.getElementById("m").src = "models/" + id + ".glb?v=" + (q.get("v") || Date.now());
</script>"""


def engineer_turn(cid):
    """May your AI's engineer take this failed model now? (on unless settings.json says "engineer": false; at most
    3 tries per item a day, so one stubborn item can't hold up the rest of the queue; never while its safety rules
    fail the self-test)"""
    if TRIAL or not setting("engineer"):
        return False
    if jload(os.path.join(WORK, "selftest.json"), {}).get("engineer_guard_ok") is False:
        say("[engineer] its safety rules failed the self-test - it is not used until they pass (send this to Claude)")
        return False
    ok = []

    import notes as NT
    n_ = NT.get(cid)                                       # your new note on the item: a fresh start for its tries
    since = max(float(n_.get("at") or 0), float(n_.get("reopened") or 0))

    def change(a):
        recent = [t for t in a.get(cid, []) if isinstance(t, (int, float)) and time.time() - t < 86400 and t > since]
        if len(recent) < 3:
            recent.append(time.time())
            ok.append(True)
        a[cid] = recent
    update_json(os.path.join(WORK, "engineer", "attempts.json"), change, backup=False)
    if not ok:
        say(f"[engineer] {cid}: already tried 3 times today - left for tomorrow")
    return bool(ok)


def _trial_copies(cid, tdir, cards_dir="cards"):
    """A test build gets its own copies of the item's card, the factory recipes and the item's dossier, and every
    write goes to those copies - never to the real ones. The settings are environment variables, so they reach
    every module and every program the test build starts."""
    cdir, rdir, ddir = (os.path.join(tdir, n) for n in (cards_dir, "recipes", "dossier"))
    for p in (cdir, rdir, ddir):
        os.makedirs(p, exist_ok=True)
    card = os.path.join(WORK, "cards", cid + ".json")
    if os.path.exists(card):
        shutil.copy2(card, os.path.join(cdir, cid + ".json"))
    if os.path.isdir(os.path.join(HERE, "factory", "recipes")):
        shutil.copytree(os.path.join(HERE, "factory", "recipes"), rdir, dirs_exist_ok=True)
    dos = os.path.join(WORK, "dossier")
    if os.path.isdir(dos):
        for n in os.listdir(dos):
            if n == cid or n.startswith(cid + "."):
                src, dst = os.path.join(dos, n), os.path.join(ddir, n)
                (shutil.copytree(src, dst, dirs_exist_ok=True) if os.path.isdir(src) else shutil.copy2(src, dst))
    os.environ.update(CRUSHED_CARDS_DIR=cdir, CRUSHED_RECIPES_DIR=rdir, CRUSHED_DOSSIER_DIR=ddir)


def _judge_trial(cid, tdir, card, picked):
    """The asset maker's OWN check of a test build's model (run from the running code, never the engineer's copy):
    the same viewer pictures and the same judge as a real build, against the item's real card. The engineer keeps a
    fix only when this agrees with its own test build."""
    import vet as V
    glb = os.path.join(tdir, "model", cid + ".glb")
    shots = close = verdict = None
    if not os.path.exists(glb):
        verdict = {"pass": False, "problems": "could not inspect: the test build made no model"}
    else:
        try:
            import viewshot
            shots, close = viewshot.shoot(glb, os.path.join(tdir, "judge_check"))
        except Exception as e:
            verdict = {"pass": False, "problems": f"could not inspect: the viewer pictures failed ({e})"}
    if verdict is None:
        make_room("judging")
        route, fam = route_of_card(card, cid)
        verdict = check_model(cid, card, picked, tdir, glb, route, fam, shots, close, V.model())
    _atomic_json(os.path.join(tdir, "judged.json"), {"verdict": verdict, "shots": shots, "close": close})
    say(f"[judge] {cid}: " + ("passed every realism check" if verdict.get("pass") else
                              "failed: " + ", ".join(verdict.get("failed", [])) + " " + str(verdict.get("problems"))[:300]))
    return verdict


def trial(cid, tdir, clear=(), judge_only=False):
    """Your AI's engineer testing a fix (run from its own copy of the code): this item rebuilt from your pick into
    tdir and checked - the steps it didn't change are reused from the last build, nothing is sent or filed, and the
    card / recipes / dossier it writes are its own copies in tdir. judge_only: only the asset maker's own check of
    the model already built in tdir (run from the running code)."""
    tdir = os.path.abspath(tdir)
    os.makedirs(tdir, exist_ok=True)
    _trial_copies(cid, tdir, "judge_cards" if judge_only else "cards")
    import cards
    cards.DIR = os.environ["CRUSHED_CARDS_DIR"]                 # even if something loaded it before
    sys.path.insert(0, os.path.join(HERE, "factory"))
    import factory
    factory.RECIPES = os.environ["CRUSHED_RECIPES_DIR"]
    import vet as V
    d0 = os.path.join(OUT, cid)
    cf = os.path.join(d0, "candidates.json")
    pick = jload(os.path.join(HB, "picks.json"), {}).get(cid, {}).get("pick", "none")
    if not os.path.exists(cf) or pick == "none":
        raise SystemExit(f"{cid}: no picked photo to build from")
    cands = json.load(open(cf))["files"]
    picked = cands[int(pick) - 1]
    if judge_only:
        return _judge_trial(cid, tdir, cards.make(cid, log=say), picked)
    skip = {"model", "check", "trial.json", "judged.json", "judge_check", "cards", "recipes", "dossier",
            "judge_cards", "trial.log", "judge.log"} | set(clear)
    if os.path.isdir(d0):
        for n in os.listdir(d0):
            if n in skip or n.startswith(("view", "round_")):
                continue
            src, dst = os.path.join(d0, n), os.path.join(tdir, n)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    if "parts" in clear and os.path.exists(os.path.join(tdir, "parts.json")):
        os.remove(os.path.join(tdir, "parts.json"))
    card = cards.make(cid, log=say)
    for k in clear:
        card.pop(k, None)
    cards.construction(cid, card, log=say)
    os.makedirs(os.path.join(tdir, "model"), exist_ok=True)
    return build(cid, card, picked, [c for c in cands if c["file"] != picked["file"]], V.model(), tdir,
                 os.path.join(tdir, "model"), 0, len(cands), redo="dossier" in clear)


SYNC_STATE = os.path.join(WORK, "sync_state.json")
UPDATE_NOTE = "_asset_maker_update"                   # the one line on your page while a newer version is stuck


def _update_note(text):
    """A line on your page (and in status.json) while a newer version can't be added; removed once it is."""
    if TRIAL:
        return

    def change(s):
        if text:
            s[UPDATE_NOTE] = {"product": "Asset maker update", "step": "stopped updating: " + text, "ok": False,
                              "at": time.time()}
        else:
            s.pop(UPDATE_NOTE, None)
    try:
        update_json(STATUS, change)
        page()
    except Exception as e:
        say(f"(page skipped: {e})")


def _sync_stuck(upstream, why=""):
    """Remember - and say ONCE - that the newest version can't be added right now, so nothing stops over and over
    for it (the loop and the watchdog both read this); cleared as soon as the code is up to date."""
    st = jload(SYNC_STATE, {})
    if not upstream:
        if st.get("stuck_at"):
            _atomic_json(SYNC_STATE, {})
            _update_note(None)
            say("[update] the code is up to date again")
        return
    if st.get("stuck_at") == upstream:
        return
    _atomic_json(SYNC_STATE, {"stuck_at": upstream, "why": why, "at": time.time()})
    say(f"[update] a newer version is waiting but could not be added ({why}) - carrying on with the version that "
        "runs now. Send this to Claude.")
    _update_note(f"a newer version could not be added ({why[:160]}) - the older one keeps running")


def _save_local_edits(g, why):
    """Before git changes any file: edits in the code folder that were never committed, and new files that would be
    in the way of the newer version, are saved to ~/Desktop/_to delete/asset-maker-local-edits-<time>/ with a note
    (the edited files copied, the in-the-way files moved, every changed line in changes.diff) - never lost.
    Returns that folder, or None when there was nothing to save."""
    tracked, untracked = [], []
    for e in g("status", "--porcelain", "-z", "-uall", "--no-renames").stdout.split("\0"):
        if len(e) >= 4:
            (untracked if e[:2] == "??" else tracked).append(e[3:])
    upstream = set(g("ls-tree", "-r", "-z", "--name-only", "@{u}").stdout.split("\0")) - {""}
    collide = [r for r in untracked if r in upstream]
    if not tracked and not collide:
        return None
    dest = os.path.expanduser("~/Desktop/_to delete/asset-maker-local-edits-" + time.strftime("%Y%m%d-%H%M%S"))
    n = 1
    while os.path.exists(dest + ("" if n == 1 else f"-{n}")):
        n += 1
    dest += "" if n == 1 else f"-{n}"
    os.makedirs(dest)
    diff = g("diff", "--binary", "HEAD").stdout
    if diff:
        open(os.path.join(dest, "changes.diff"), "w").write(diff)
    for rel in tracked:
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(dest, "edited", rel)), exist_ok=True)
            shutil.copy2(src, os.path.join(dest, "edited", rel))
    for rel in collide:
        os.makedirs(os.path.dirname(os.path.join(dest, "in-the-way", rel)), exist_ok=True)
        shutil.move(os.path.join(ROOT, rel), os.path.join(dest, "in-the-way", rel))
    open(os.path.join(dest, "NOTE.txt"), "w").write(
        f"What this is: changes that were sitting in the asset maker's code folder ({ROOT}) without being saved,\n"
        f"found when a newer version came in ({why}). They were saved here before the newer version was put in.\n\n"
        "  changes.diff  every changed line (a list of the edits)\n"
        "  edited/       copies of the edited files, exactly as they were\n"
        "  in-the-way/   new files that had the same name as a file in the newer version (moved here)\n\n"
        "The asset maker now runs the newer version. If any of this was wanted, send this folder to Claude.\n"
        "If not, you can throw this folder away.\n")
    g("reset", "-q", "--hard", "HEAD")                  # saved above; taken out so the newer version can go in
    say(f"[update] edits in the code folder that were never committed are saved in {dest} (nothing lost)")
    return dest


def sync_code():
    """Combine your AI's own kept fixes (local commits) with the newest version from GitHub. Uncommitted edits are
    saved first (see _save_local_edits). In order: fast-forward; else put the local fixes on top (rebase); else keep
    the local fixes on a branch of their own (engineer-kept-<time>, never lost) and take the newest version. If it
    still can't be added, that is said once and the current code keeps running. Returns True when the code changed
    (the run then restarts itself on it)."""
    def g(*a, timeout=180):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout)

    def count(r):
        x = g("rev-list", "--count", r)
        return int(x.stdout.strip() or 0) if x.returncode == 0 else 0
    try:
        gd = g("rev-parse", "--git-dir").stdout.strip()
        gd = gd if os.path.isabs(gd) else os.path.join(ROOT, gd)
        if os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply")):
            g("rebase", "--abort")
        if os.path.exists(os.path.join(gd, "CHERRY_PICK_HEAD")):
            g("cherry-pick", "--abort")
        if os.path.exists(os.path.join(gd, "MERGE_HEAD")):
            g("merge", "--abort")
        if g("fetch", "-q", timeout=120).returncode != 0:
            return False
        up = g("rev-parse", "@{u}")
        if up.returncode != 0:
            return False
        up = up.stdout.strip()
        ahead, behind = count("@{u}..HEAD"), count("HEAD..@{u}")
        if not behind:
            _sync_stuck(None)
            return False
        old = g("rev-parse", "HEAD").stdout.strip()
        _save_local_edits(g, f"{behind} newer change(s) from GitHub")
        why = ""
        who = [] if g("config", "user.email").stdout.strip() else \
            ["-c", "user.name=Asset maker", "-c", "user.email=asset-maker@hellbox.local"]   # rebase needs a name
        if not ahead and g("merge", "-q", "--ff-only", "@{u}").returncode == 0:
            say("[update] the newest version is in")
        elif g(*who, "rebase", "-q", "@{u}").returncode == 0:
            say(f"[update] the newest version, with your AI's {ahead} own fix(es) on top")
        else:
            r = g("rebase", "--abort")
            if ahead:
                keep = "engineer-kept-" + time.strftime("%Y%m%d-%H%M%S")
                g("branch", keep)
            r = g("reset", "-q", "--hard", "@{u}")
            why = (r.stderr or r.stdout).strip()[-200:]
            if r.returncode == 0 and ahead:
                say(f"[update] your AI's own fixes could not be combined with the newest version - they are kept on "
                    f"branch {keep} (nothing lost); the newest version runs")
        if count("HEAD..@{u}") > 0:
            _sync_stuck(up, why or "git refused")
            return g("rev-parse", "HEAD").stdout.strip() != old
        _sync_stuck(None)
        return True
    except Exception as e:
        say(f"[update] could not check for a newer version ({e}) - carrying on with this one")
        return False


def newer_version():
    """Is there a newer version that can actually be added? (checked between items, never mid-item; a version that
    was already found impossible to add does not count, so the loop never stops for it over and over)"""
    try:
        subprocess.run(["git", "fetch", "-q"], cwd=ROOT, capture_output=True, timeout=60)
        r = subprocess.run(["git", "rev-list", "--count", "HEAD..@{u}"], cwd=ROOT, capture_output=True, text=True,
                           timeout=30)
        if r.returncode != 0 or int(r.stdout.strip() or 0) == 0:
            return False
        up = subprocess.run(["git", "rev-parse", "@{u}"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        return jload(SYNC_STATE, {}).get("stuck_at") != up.stdout.strip()
    except Exception:
        return False


RETRIES = os.path.join(WORK, "retries.json")
RETRY_AFTER = (("stopped", 3600), ("failed the realism check", 6 * 3600))   # how long a parked item waits
RETRIES_PER_DAY = 3


def retry_due(cid, v, tries, now):
    """For an item that stopped (an error) or failed the realism check: True when it may be tried again by itself
    now (1 hour after stopping, 6 hours after failing, at most 3 times a day), False while it waits, None when it is
    not in a state that is retried by itself (done, or waiting on you)."""
    step = str((v or {}).get("step", ""))
    wait = next((w for p, w in RETRY_AFTER if step.startswith(p)), None)
    if wait is None:
        return None
    today = [t for t in tries.get(cid, []) if isinstance(t, (int, float)) and now - t < 86400]
    try:
        at = float(v.get("at") or 0)
    except (TypeError, ValueError):
        at = 0.0
    if step.startswith("stopped") and at < code_time():
        wait = 0                                    # it stopped on older code: a fix may be in - tried again now
    return len(today) < RETRIES_PER_DAY and now - at >= wait


_CODE_TIME = []


def code_time():
    """When the code this run uses was made (its git commit time; 0 if unknown)."""
    if not _CODE_TIME:
        try:
            _CODE_TIME.append(float(subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=ROOT, capture_output=True,
                                                   text=True, timeout=20).stdout.strip() or 0))
        except Exception:
            _CODE_TIME.append(0.0)
    return _CODE_TIME[0]


def note_retry(cid):
    """Just before an item starts: when it is an automatic retry, count it (3 a day at most) and say so."""
    v = read_status().get(cid, {})
    step = str(v.get("step", "")) if isinstance(v, dict) else ""
    if not any(step.startswith(p) for p, _ in RETRY_AFTER):
        return
    now = time.time()

    def change(t):
        t[cid] = [x for x in t.get(cid, []) if isinstance(x, (int, float)) and now - x < 86400] + [now]
    t = update_json(RETRIES, change, backup=False)
    try:
        hours = (now - float(v.get("at") or now)) / 3600
    except (TypeError, ValueError):
        hours = 0
    say(f"[retry] {cid}: trying again by itself ({step[:100]} - {hours:.0f} h ago), try {len(t[cid])} of "
        f"{RETRIES_PER_DAY} today")


def queue(n):
    """The next n items to make, in the order of library/queue.txt (one item per line), skipping ones done and
    ones waiting on you (a pick or a Keep/Redo you haven't given yet). An item that stopped is tried again after
    1 hour (right away when newer code has arrived since), one that failed the realism check after 6 hours (each at
    most 3 times a day)."""
    q = [l.strip() for l in open(os.path.join(HERE, "queue.txt")) if l.strip() and not l.startswith("#")] \
        if os.path.exists(os.path.join(HERE, "queue.txt")) else []
    st = read_status()
    picks = jload(os.path.join(HB, "picks.json"), {})
    ap = jload(os.path.join(HB, "approvals.json"), {})
    tries = jload(RETRIES, {})
    now = time.time()
    out = []
    asking = sum(1 for k, v in st.items() if isinstance(v, dict) and str(v.get("step", "")).startswith(
        "waiting for your pick") and k not in picks)
    import notes as NT
    for cid in q:
        v = st.get(cid) if isinstance(st.get(cid), dict) else {}
        step = str(v.get("step", ""))
        if step.startswith("in line") and asking >= 5:
            continue
        try:
            n_ = NT.get(cid)
            noted = max(float(n_.get("at") or 0), float(n_.get("reopened") or 0)) > float(v.get("at") or 0)
        except (TypeError, ValueError):
            noted = False
        if noted and step.startswith(("failed", "stopped", "3 rounds", "no usable")):
            out.append(cid)                         # your new note on a parked item puts it back in line right away
            continue
        due = retry_due(cid, v, tries, now)
        if due is False:
            continue
        if due is None and step.startswith(("done", "stopped", "3 rounds", "no usable", "failed")):
            continue
        if step.startswith("waiting for your pick") and cid not in picks:
            continue
        if step.startswith("waiting for your Keep") and cid not in ap:
            continue
        out.append(cid)
    # an item you have just answered on your phone (a pick, "none") goes first: you are waiting on it
    out.sort(key=lambda c: 0 if c in picks or c in ap else 1)
    return out[:n]


HUNYUAN_PINS = {"timm": "timm==1.0.27",            # Hunyuan3D-2.1's requirements.txt lists timm without a version
                "pygltflib": "pygltflib==1.16.3",   # the version Hunyuan3D-2.1's requirements.txt pins
                # the painter trims the shape to ~40,000 faces with trimesh's simplify_quadric_decimation, which
                # needs this (2026-10-03: the Furby stopped there); 0.2.0 has a ready-made Apple-chip wheel for
                # Python 3.11 and needs only numpy, already there
                "fast_simplification": "fast-simplification==0.2.0"}


def pip_install(python, pkgs, no_deps=False, timeout=900):
    """Install packages into one Python. The asset maker's and Hunyuan's Pythons were made by uv and have no pip
    inside them, so uv is used when it is on this Mac (pip otherwise). Returns (ok, message)."""
    uv = next((u for u in (shutil.which("uv"), os.path.expanduser("~/.local/bin/uv"), "/opt/homebrew/bin/uv")
               if u and os.path.exists(u)), None)
    extra = ["--no-deps"] if no_deps else []
    cmd = ([uv, "pip", "install", "-q", "--python", python, *extra, *pkgs] if uv else
           [python, "-m", "pip", "install", "-q", *extra, *pkgs])
    pr = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return pr.returncode == 0, ("ok" if pr.returncode == 0 else (pr.stderr or pr.stdout)[-300:])


def hunyuan_test_request():
    """Claude asked (WORK/hunyuan_test.request): does Hunyuan make a shape from its own demo picture? Only the two
    packages its folder is known to be missing are installed - at fixed versions, without touching anything they
    depend on (so the PyTorch setup is never upgraded) - then its own test runs, with time limits."""
    req = os.path.join(WORK, "hunyuan_test.request")
    if not os.path.exists(req):
        return
    os.replace(req, req + ".done")
    import engineer
    import hunyuan
    hy = hunyuan.home()
    if not hy:
        say("[hunyuan test] Hunyuan3D is not installed on this Mac - nothing to test")
        open(os.path.join(WORK, "hunyuan_test.log"), "w").write("Hunyuan3D is not installed on this Mac\n")
        return
    py = os.path.join(hy, ".venv", "bin", "python")
    if not os.path.exists(py):
        say(f"[hunyuan test] Hunyuan3D's own Python is missing ({py}) - nothing to test")
        return
    missing = []
    for mod in HUNYUAN_PINS:
        try:
            if subprocess.run([py, "-c", f"import {mod}"], capture_output=True, timeout=180).returncode != 0:
                missing.append(mod)
        except subprocess.TimeoutExpired:
            missing.append(mod)
    if missing:
        try:
            ok, msg = pip_install(py, [HUNYUAN_PINS[m] for m in missing], no_deps=True, timeout=600)
            say(f"[hunyuan test] installed {missing}: {msg}")
        except subprocess.TimeoutExpired:
            say(f"[hunyuan test] installing {missing} took over 10 minutes and was stopped")
    log = os.path.join(WORK, "hunyuan_test.log")
    rc, took = engineer.run_group([py, os.path.join(HERE, "hunyuan.py"), "--test"], 3600, log, cwd=HERE,
                                  beat=lambda: beat("hunyuan test: making a shape from its own demo picture"))
    out = open(log, errors="replace").read()
    say("[hunyuan test] " + ("ran over an hour and was stopped" if rc is None else f"finished in {took} s (exit {rc})"))
    for line in out.splitlines()[-200:]:
        if line.startswith("[hunyuan]") or "Error" in line or "error" in line:
            say("[hunyuan test] " + line[:300])
    still = sorted(set(re.findall(r"No module named '([A-Za-z0-9_.]+)", out)))
    if still:
        say(f"[hunyuan test] still missing: {', '.join(still)} - not installed by itself (it could change the "
            "PyTorch setup); send this to Claude")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--queue", type=int, default=0, help="make up to N items from library/queue.txt")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--wait", action="store_true", help="wait for your photo pick on the phone")
    ap.add_argument("--loop", action="store_true", help="keep working through the queue: an item waiting on "
                    "your tap is set aside and picked up again the minute you tap; stops after 3 quiet hours")
    ap.add_argument("--trial", nargs=2, metavar=("ITEM", "FOLDER"), help="(your AI's engineer) test-build one item")
    ap.add_argument("--judge", nargs=2, metavar=("ITEM", "FOLDER"),
                    help="(your AI's engineer) the asset maker's own check of a test build")
    ap.add_argument("--clear", default="")
    ap.add_argument("--sync", action="store_true", help="add the newest version now (only when no run is going)")
    a = ap.parse_args()
    WAIT = a.wait
    if a.trial:                                         # the engineer's test build: no lock, nothing sent
        TRIAL = True
        trial(a.trial[0], a.trial[1], [c for c in a.clear.split(",") if c])
        sys.exit(0)
    if a.judge:                                         # the asset maker's own check of a test build
        TRIAL = True
        trial(a.judge[0], a.judge[1], judge_only=True)
        sys.exit(0)
    # ONE run at a time on this Mac, whoever starts it (the clock, the watchdog, a paste): a second one leaves
    # at once. Two runs drawing together ran the memory out and crashed the drawing room (2026-10-02).
    import fcntl
    os.makedirs(WORK, exist_ok=True)
    _lock = open(os.path.join(WORK, "run.lock"), "w")
    try:
        fcntl.flock(_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        say("another asset run is already going - leaving it alone" +
            (" (it adds a newer version itself, between items)" if a.sync else ""))
        sys.exit(0)
    if a.sync:                                          # the clock: update the code only while no run is going
        say("[update] " + ("the newest version is in" if sync_code() else "nothing new was added"))
        sys.exit(0)
    clash = sorted(f[:-3] for f in os.listdir(HERE) if f.endswith(".py") and f[:-3] in sys.stdlib_module_names)
    if clash:                                           # a file named like Python's own module breaks other tools
        say(f"STOP: library files named like Python's own modules: {clash} - rename them")
        sys.exit(1)
    beat("starting")
    _beating()
    if a.loop and os.path.exists(os.path.join(WORK, "PAUSE")):
        # Cody paused the asset maker (2026-10-02) until the redesigned one is installed: nothing is built
        say("paused - " + open(os.path.join(WORK, "PAUSE")).read().strip()[:200])
        sys.exit(0)
    if a.loop and sync_code():                         # newest code (with your AI's own fixes): start again on it
        _lock.close()
        os.execv(PY, [PY] + sys.argv)
    if a.loop:
        installed = False
        sreq = os.path.join(WORK, "setup.request")  # Cody approved installing these free tools
        if os.path.exists(sreq):
            os.replace(sreq, sreq + ".done")
            allowed = {"zxing-cpp", "ocrmac"}           # only these, ever: the exact checks' readers
            want = [w for w in open(sreq + ".done").read().split() if w in allowed]
            if want:
                installed, msg = pip_install(PY, want)  # this Python was made by uv: no pip inside it
                say(f"[setup] installed {', '.join(want)}: {msg}")
        try:
            resend()                                    # first: anything that never reached your phone
        except Exception as e:
            say(f"[phone] resend skipped: {e}")
        if not queue(a.queue or 3):                     # nothing to make right now: done in a second
            sys.exit(0)
        import selftest
        last = jload(os.path.join(WORK, "selftest.json"), {})
        age = time.time() - last.get("at", 0)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not last.get("ok", True) and age < 3600 and not installed and last.get("code") == head:
            # failed lately with this same code: no rerun for an hour (a fix pushed since, or a missing tool just
            # installed: every piece is checked again right away)
            sys.exit(0)
        fresh = last.get("ok") and age < 6 * 3600 and last.get("code") == head and not installed   # new code: all again
        if not fresh and not selftest.run_all():        # every piece checked first; a broken one stops it here
            say("self-test failed - nothing run (the reason is on your phone)")
            sys.exit(1)
        try:
            import speed                                # the brain answers several questions at once (measured)
            speed.setup(log=say)
        except Exception as e:
            say(f"[speed] skipped: {e}")
        try:
            import brainjobs                            # one brain per job, chosen by a photo exam (timed)
            brainjobs.setup(log=say)
        except Exception as e:
            say(f"[brains] skipped: {e}")
        try:
            import families                             # the organic builder not proven yet: test it once a day
            tlog = os.path.join(WORK, "hunyuan_test.log")
            if not families.organic_ready() and (not os.path.exists(tlog) or time.time() - os.path.getmtime(tlog) > 86400):
                open(os.path.join(WORK, "hunyuan_test.request"), "w").write("daily check: not proven yet\n")
            hunyuan_test_request()                      # does Hunyuan make a shape from its own demo picture?
        except Exception as e:
            say(f"[hunyuan test] skipped: {e}")
        quiet = 0
        while quiet < 20:                               # 10 quiet minutes: leave, so the clock can start a fresh one
            try:
                resend()
            except Exception as e:
                say(f"[phone] resend skipped: {e}")
            todo = queue(a.queue or 3)
            for cid in todo:
                if os.path.exists(os.path.join(WORK, "PAUSE")):   # paused while running: stop between items
                    say("paused - stopping between items")
                    sys.exit(0)
                if RESTART:                             # your AI's engineer kept a fix: start again on the fixed code
                    say("[update] your AI's engineer kept a fix - restarting on the fixed code")
                    _lock.close()
                    os.execv(PY, [PY] + sys.argv)
                if newer_version() and sync_code():     # between items: a newer version that could be added -
                    say("[update] a newer version is in - restarting on it between items")
                    _lock.close()                       # start again on it (one that can't be added is said once
                    os.execv(PY, [PY] + sys.argv)       # and the current code carries on)
                try:
                    note_retry(cid)
                    pipeline(cid, False)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    status(cid, step=f"stopped: {e}"[:300], ok=False)
            if RESTART:
                say("[update] your AI's engineer kept a fix - restarting on the fixed code")
                _lock.close()
                os.execv(PY, [PY] + sys.argv)
            st = read_status()
            busy = [c for c in todo if not str((st.get(c) or {}).get("step", "")).startswith(
                ("waiting", "done", "stopped", "3 rounds", "in line", "no usable", "failed"))]
            quiet = 0 if busy else quiet + 1
            time.sleep(0 if busy else 30)
        sys.exit(0)
    todo = a.only or (queue(a.queue) if a.queue else [])
    if a.queue and not todo:
        say("nothing waiting: every queued item is made or waiting on you")
    for cid in todo:
        try:
            if not a.only:
                note_retry(cid)
            pipeline(cid, a.redo)
        except Exception as e:
            import traceback
            traceback.print_exc()
            status(cid, step=f"stopped: {e}"[:300], ok=False)
    say("done - https://crushed-remaster.pages.dev")
