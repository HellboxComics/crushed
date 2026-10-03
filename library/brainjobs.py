"""ONE BRAIN PER JOB, CHOSEN BY A TEST ON REAL PHOTOS - not by a list someone typed.

Your Mac has many brains (Ollama models). The asset maker used to ask one of them everything, with long thinking every
time. Here every installed brain that can see pictures takes the same short exam - real photos from your own items,
with answers known for sure - and is timed. Then each job gets the brain that does it best:

  judge   the careful look (thinking on): the pick, the side comparisons - the best score, the faster one on a tie
  sort    the quick look (thinking off): sorting hundreds of photos - the fastest brain that still answers the
          sorting questions right

The exam (each answer is checked by code, not by another brain):
  1. the 90s Duracell PowerCheck AA you picked          -> a match (7+), from the era
  2. a blurry store picture of a later Duracell label   -> not the 90s PowerCheck version (5 or less, or wrong era)
  3. a fat D-size PowerCheck cell                       -> not an AA (5 or less)
  4. a white Pop-Tarts box, judged against the note "the blue box design"  -> the note is NOT met
  5. the same white box with no note                    -> a 90s Pop-Tarts Frosted Strawberry box (7+, right era)
  6. four Duracells: read the date printed on them      -> "JAN 2001"

Results: ~/crushed-render/remaster/brains.json (and the log). Taken again when the brains on the Mac change, or after 30
days. Never while one of your brain tests is running (the suite's testlock) - a test owns the brain server.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "brains.json")
VERSION = 2                  # 2: the coding exam (the engineer's brain)
HUNT = os.path.join(WORK, "hunt")

DURACELL = {"product": "Duracell Coppertop AA alkaline battery, circa 1998", "year": 1998,
            "recognize": ["black body with white DURACELL text", "copper-colored positive end"],
            "avoid": ["all-copper or gold body (later redesign)"],
            "era_version": {"names": ["Duracell PowerCheck AA"],
                            "marks": ["PowerCheck tester strip on the label", "white test dots"],
                            "not_then": ["bilingual 'PILE ALCALINE' label without a tester"]}}
POPTARTS = {"product": "Kellogg's Pop-Tarts Frosted Strawberry toaster pastries, circa 1997", "year": 1997,
            "recognize": ["Kellogg's red script logo", "pop-tarts lettering", "Frosted Strawberry"],
            "avoid": ["modern blue foil pouch design"]}

EXAM = [
    {"id": "picked_powercheck", "photo": "duracell_coppertop_aa_1998/p2db7abb9ae2a.jpg", "card": DURACELL,
     "ok": lambda v: int(v.get("match") or 0) >= 7 and v.get("era_ok") is not False},
    {"id": "later_label", "photo": "duracell_coppertop_aa_1998/p4da47f7bbf28.jpg", "card": DURACELL,
     "ok": lambda v: int(v.get("match") or 0) <= 5 or v.get("era_ok") is False},
    {"id": "d_size_cell", "photo": "duracell_coppertop_aa_1998/pbfae2d230fd1.jpg", "card": DURACELL,
     "ok": lambda v: int(v.get("match") or 0) <= 5},
    {"id": "note_not_met", "photo": "poptarts_frosted_strawberry_1997/pe22f1f6adeb3.jpg",
     "card": dict(POPTARTS, owner_note="Build the blue box design of this item (the blue Pop-Tarts box)."),
     "ok": lambda v: v.get("note_ok") is False},
    {"id": "right_box", "photo": "poptarts_frosted_strawberry_1997/pe22f1f6adeb3.jpg", "card": POPTARTS,
     "ok": lambda v: int(v.get("match") or 0) >= 7 and v.get("era_ok") is not False},
    {"id": "read_date", "photo": "duracell_coppertop_aa_1998/p18503eb26d9a.jpg", "read": True,
     "ok": lambda t: "JAN2001" in str(t).upper().replace(" ", "")},
]


def _get(path, body=None, timeout=60):
    import vet as V
    if body is None:
        return json.loads(urllib.request.urlopen(V.OLLAMA + path, timeout=timeout).read())
    req = urllib.request.Request(V.OLLAMA + path, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def _testing():
    """One of Cody's brain tests owns the brain server right now (the suite's testlock)."""
    try:
        import ownmods
        testlock = ownmods.outside("~/.hellbox/ai/testlock.py", "testlock")   # (it puts its folder in front)
        return bool(testlock) and testlock.testing() and not testlock.mine()
    except Exception:
        return False


def inventory():
    """[{name, size_gb, family, params, quant, vision, thinking}] for every brain installed on the Mac."""
    out = []
    for m in _get("/api/tags").get("models", []):
        name = m.get("name") or m.get("model")
        try:
            show = _get("/api/show", {"model": name}, timeout=60)
        except Exception:
            show = {}
        caps = show.get("capabilities") or []
        det = m.get("details") or show.get("details") or {}
        out.append({"name": name, "size_gb": round((m.get("size") or 0) / 1e9, 1), "family": det.get("family", ""),
                    "params": det.get("parameter_size", ""), "quant": det.get("quantization_level", ""),
                    "vision": "vision" in caps, "thinking": "thinking" in caps})
    return out


def _one(model, item, think):
    """(answer, seconds, words per second) for one exam question."""
    import vet as V
    t = time.time()
    photo = os.path.join(HUNT, item["photo"])
    if item.get("read"):
        body = {"model": model, "stream": False, "format": "json", "think": think, "options": {"temperature": 0},
                "messages": [{"role": "user", "content": 'Read every word printed on the items in this photo, '
                              'exactly as printed. Answer ONLY JSON: {"text": "..."}',
                              "images": [V._img(photo, 1600)]}]}
        r = V._call("/api/chat", body, timeout=1200)
        import re
        txt = r.get("message", {}).get("content", "{}")
        try:
            ans = json.loads(re.search(r"\{.*\}", txt, re.S).group(0)).get("text", "")
        except Exception:
            ans = txt
    else:
        ans = V.vet(photo, item["card"]["product"], use=model, think=think, card=item["card"]) or {}
        r = {}
    took = time.time() - t
    rate = (r.get("eval_count") or 0) / max((r.get("eval_duration") or 0) / 1e9, 0.01) if r else 0
    return ans, took, rate


def exam(models, log=print, finalists=2, done=None, save=None):
    """Every brain takes the exam with thinking off (the sort job, quick); the best few - and the brain doing the
    careful looks now - take it again with thinking on (the judge job). Thinking takes minutes an answer, so only
    brains that could win sit that part. done = results already taken (an exam cut short by a restart carries on
    where it stopped); save(res) is called after every brain."""
    import vet as V
    items = [it for it in EXAM if os.path.exists(os.path.join(HUNT, it["photo"]))]
    res = {m: dict(v) for m, v in (done or {}).items() if m in models}
    for think in (False, True):
        if think:
            quick = sorted(res, key=lambda m: (-res[m]["quick"]["score"], res[m]["quick"]["seconds"]))
            now = V._first(V.PREFER)
            todo = list(dict.fromkeys(quick[:finalists] + ([now] if now in res else [])))
        else:
            todo = list(models)
        for m in todo:
            if (res.get(m) or {}).get("think" if think else "quick"):
                continue                                 # taken before a restart
            if _testing():
                log("[brains] one of your brain tests started - the exam stops here (a test owns the brain server); "
                    "it carries on next time from where it stopped")
                return {}
            row = res.setdefault(m, {})
            score, secs, notes = 0, 0.0, []
            for it in items:
                try:
                    ans, took, _ = _one(m, it, think)
                    ok = bool(it["ok"](ans))
                except Exception as e:
                    ans, took, ok = {"error": str(e)[:120]}, 0.0, False
                score += ok
                secs += took
                notes.append({"id": it["id"], "ok": ok, "seconds": round(took, 1)})
            row["think" if think else "quick"] = {"score": score, "of": len(items), "seconds": round(secs, 1),
                                                  "items": notes}
            log(f"[brains] {m} ({'thinking' if think else 'quick'}): {score} of {len(items)} right, "
                f"{secs / max(len(items), 1):.0f} s an answer")
            if save:
                save(res)
            try:                                         # let it go before the next one loads
                V._call("/api/generate", {"model": m, "keep_alive": 0}, timeout=60)
            except Exception:
                pass
    return res


# ------------------------------------------------------------------ the coding brain (the engineer's hands)
CODE_EXAM = [
    {"id": "fix_off_by_one",
     "task": "This function should return the average of a list, or 0.0 for an empty list, but it is wrong. Answer "
             "ONLY the corrected Python function, nothing else.\n\ndef mean(xs):\n    return sum(xs) / len(xs)\n",
     "check": lambda ns: ns["mean"]([2, 4]) == 3.0 and ns["mean"]([]) == 0.0},
    {"id": "exact_edit",
     "task": "In the JSON below, change ONLY the value of \"stroke_w\" from 1.2 to 0.006 and answer ONLY the whole "
             "corrected JSON.\n\n{\"shapes\": [{\"type\": \"rect\", \"x\": 0.3, \"stroke\": \"#1fd43a\", "
             "\"stroke_w\": 1.2}, {\"type\": \"rect\", \"x\": 0.5, \"stroke_w\": 0.004}]}",
     "check": lambda ns: ns["json"]["shapes"][0]["stroke_w"] == 0.006 and ns["json"]["shapes"][1]["stroke_w"] == 0.004
     and ns["json"]["shapes"][0]["x"] == 0.3},
    {"id": "find_cause",
     "task": "A label is drawn all green although its layout says the background is black. The drawing code draws "
             "each shape's outline with width int(stroke_w * H) pixels where H is the picture height, and this layout "
             "has an outline with stroke_w = 1.2. In ONE sentence, what is the cause? Answer ONLY JSON: "
             "{\"cause\": \"...\"}",
     "check": lambda ns: any(w in str(ns["json"].get("cause", "")).lower() for w in ("1.2", "stroke_w", "width"))
     and any(w in str(ns["json"].get("cause", "")).lower() for w in ("height", "whole", "entire", "fraction", "covers", "cover", "fill", "larger", "wide"))},
]


def _code_one(model, item):
    import re
    import vet as V
    t = time.time()
    body = {"model": model, "stream": False, "think": False, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": item["task"]}]}
    r = V._call("/api/chat", body, timeout=900)
    txt = str(r.get("message", {}).get("content", ""))
    txt = re.sub(r"^```[a-z]*\n|```$", "", txt.strip(), flags=re.M).strip()
    ns = {}
    try:
        if item["id"] == "fix_off_by_one":
            exec(txt, {}, ns)
        else:
            ns["json"] = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        ok = bool(item["check"](ns))
    except Exception:
        ok = False
    return ok, time.time() - t


def code_exam(models, log=print):
    res = {}
    for m in models:
        if _testing():
            return res
        score, secs = 0, 0.0
        for it in CODE_EXAM:
            try:
                ok, took = _code_one(m, it)
            except Exception:
                ok, took = False, 0.0
            score += ok
            secs += took
        res[m] = {"score": score, "of": len(CODE_EXAM), "seconds": round(secs, 1)}
        log(f"[brains] {m} (coding): {score} of {len(CODE_EXAM)} right, {secs / len(CODE_EXAM):.0f} s an answer")
        try:
            V_release(m)
        except Exception:
            pass
    return res


def V_release(m):
    import vet as V
    V._call("/api/generate", {"model": m, "keep_alive": 0}, timeout=60)


def choose_code(results):
    """The engineer's coding brain: the best coding score, then the faster."""
    if not results:
        return None
    return sorted(results, key=lambda m: (-results[m]["score"], results[m]["seconds"]))[0]


def choose(results):
    """judge: the best thinking score (every question), then the faster.
    sort: the best quick score on the SORTING questions (is it this item, this size, this era, does it meet the
    note - not the reading question, which sorting never asks), then the fastest. No slack: a sorter that lets a
    D cell or a later label through costs more careful looks than its speed saves."""
    if not results:
        return {}
    thought = [m for m in results if "think" in results[m]]
    if not thought:
        return {}
    judge = sorted(thought, key=lambda m: (-results[m]["think"]["score"], results[m]["think"]["seconds"]))[0]
    reading = {it["id"] for it in EXAM if it.get("read")}

    def sorting(m):
        q = results[m].get("quick") or {}
        its = [x for x in q.get("items", []) if x["id"] not in reading]
        secs = sum(x["seconds"] for x in its) / max(len(its), 1)
        return -sum(bool(x["ok"]) for x in its), secs
    sort = sorted([m for m in results if results[m].get("quick")], key=sorting)[0]
    return {"judge": judge, "sort": sort}


def setup(log=print, force=False):
    """Inventory the brains; if they changed (or 30 days passed), take the exam and set one brain per job."""
    try:
        inv = inventory()
    except Exception as e:
        log(f"[brains] could not list the brains on this Mac ({e}) - the usual brains are used")
        return {}
    # one entry per real brain: a persona made from a brain (same family, size and packing) is the same brain
    by_base = {}
    for m in sorted(inv, key=lambda m: (m["family"].lower() not in m["name"].lower(), len(m["name"]))):
        if m["vision"] and "embed" not in m["name"]:
            by_base.setdefault((m["family"], m["params"], m["quant"]), m["name"])
    vis = sorted(by_base.values())
    coders = sorted({m["name"] for m in inv if "embed" not in m["name"] and
                     any(w in m["name"].lower() for w in ("coder", "coding", "devstral", "code"))})
    key = hashlib.sha1(json.dumps([vis, coders]).encode()).hexdigest()[:12]
    vis_key = hashlib.sha1(json.dumps(vis).encode()).hexdigest()[:12]
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    fresh = time.time() - float(old.get("at") or 0) < 30 * 86400
    # the photo exam already taken for these same vision brains is never taken again just because the coding brains
    # (or this file's version) changed: only the missing part is sat
    photo_done = {k: v for k, v in (old.get("exam") or {}).items() if not k.startswith("_")} \
        if old.get("vis_key", old.get("key")) == vis_key and fresh else {}
    if not force and photo_done and old.get("jobs") and not old["jobs"].get("code") and coders:
        if _testing():
            return old.get("jobs") or {}
        jobs = choose(photo_done) or old["jobs"]
        log(f"[brains] the photo exam is kept; {len(coders)} coding brains take the coding exam: {', '.join(coders)}")
        cres = code_exam(coders + ([jobs["judge"]] if jobs["judge"] not in coders else []), log)
        code = choose_code(cres)
        if code:
            jobs["code"] = code
        json.dump({"version": VERSION, "key": key, "vis_key": vis_key, "at": old.get("at"), "inventory": inv,
                   "exam": dict(photo_done, _coding=cres), "jobs": jobs}, open(OUT, "w"), indent=1)
        log(f"[brains] the engineer's code -> {jobs.get('code', jobs['judge'])}")
        return jobs
    if not force and old.get("version") == VERSION and old.get("key") == key and old.get("jobs") and fresh:
        jobs = choose({k: v for k, v in (old.get("exam") or {}).items() if not k.startswith("_")}) or old["jobs"]
        if jobs and old["jobs"].get("code"):
            jobs["code"] = old["jobs"]["code"]                  # the stored results, under the current rules
        if jobs != old["jobs"]:
            log(f"[brains] jobs worked out again from the last exam: careful looks -> {jobs['judge']}, quick looks "
                f"-> {jobs['sort']} (was {old['jobs'].get('judge')}, {old['jobs'].get('sort')})")
            old["jobs"] = jobs
            json.dump(old, open(OUT, "w"), indent=1)
        return jobs
    if _testing():
        log("[brains] one of your brain tests is running - the brain exam waits for next time")
        return old.get("jobs") or {}
    log(f"[brains] {len(vis)} brains on this Mac can see pictures: {', '.join(vis)} - each takes the photo exam "
        "(6 real photos with known answers), thinking on and off, timed")
    part = OUT + ".partial"                              # an exam cut short (a restart) carries on, not over
    try:
        p = json.load(open(part))
        done = p.get("exam") if p.get("key") == key and p.get("version") == VERSION else {}
    except Exception:
        done = {}
    done = dict(photo_done, **(done or {}))                # (and whatever the last full exam already knows)
    if done:
        log(f"[brains] carrying on the exam from before the restart ({len(done)} brains already taken)")

    def save(res):
        json.dump({"version": VERSION, "key": key, "exam": res}, open(part + ".tmp", "w"), indent=1)
        os.replace(part + ".tmp", part)
    results = exam(vis, log, done=done, save=save)
    jobs = choose(results)
    if jobs:
        log(f"[brains] {len(coders)} coding brains on this Mac: {', '.join(coders) or 'none'} - each takes the coding "
            "exam (a bug to fix, an exact edit, a cause to name)")
        cres = code_exam(coders + ([jobs["judge"]] if jobs["judge"] not in coders else []), log)
        code = choose_code(cres)
        if code:
            jobs["code"] = code
            results = dict(results, _coding=cres)
    if not jobs:                                         # stopped early (one of your tests): carried on next time
        return old.get("jobs") or {}
    json.dump({"version": VERSION, "key": key, "vis_key": vis_key, "at": time.time(), "inventory": inv,
               "exam": results, "jobs": jobs}, open(OUT, "w"), indent=1)
    try:
        os.remove(part)
    except OSError:
        pass
    if jobs:
        log(f"[brains] jobs set by the exam: careful looks -> {jobs['judge']}, quick looks -> {jobs['sort']}, "
            f"the engineer's code -> {jobs.get('code', jobs['judge'])}")
    return jobs


def job(name):
    """The brain chosen for a job by the exam, or None (then the usual list is used)."""
    try:
        return (json.load(open(OUT)).get("jobs") or {}).get(name)
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps(setup(force="--force" in sys.argv), indent=1))
