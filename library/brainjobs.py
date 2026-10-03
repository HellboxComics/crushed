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
VERSION = 1
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
        sys.path.insert(0, os.path.expanduser("~/.hellbox/ai"))
        import testlock
        return testlock.testing() and not testlock.mine()
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


def exam(models, log=print):
    """Every brain takes the exam twice: thinking on (the judge job) and thinking off (the sort job)."""
    import vet as V
    items = [it for it in EXAM if os.path.exists(os.path.join(HUNT, it["photo"]))]
    res = {}
    for m in models:
        if _testing():
            log("[brains] one of your brain tests started - the exam stops here (a test owns the brain server)")
            break
        row = {}
        for think in (True, False):
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
        res[m] = row
        try:                                             # let it go before the next one loads
            V._call("/api/generate", {"model": m, "keep_alive": 0}, timeout=60)
        except Exception:
            pass
    return res


def choose(results):
    """judge: best thinking score, then the faster; sort: the fastest quick answerer within 1 of the best quick score."""
    if not results:
        return {}
    judge = sorted(results, key=lambda m: (-results[m]["think"]["score"], results[m]["think"]["seconds"]))[0]
    best_quick = max(r["quick"]["score"] for r in results.values())
    sort = sorted([m for m in results if results[m]["quick"]["score"] >= best_quick - 1],
                  key=lambda m: results[m]["quick"]["seconds"])[0]
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
    key = hashlib.sha1(json.dumps(vis).encode()).hexdigest()[:12]
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    if not force and old.get("version") == VERSION and old.get("key") == key and old.get("jobs") and \
            time.time() - float(old.get("at") or 0) < 30 * 86400:
        return old["jobs"]
    if _testing():
        log("[brains] one of your brain tests is running - the brain exam waits for next time")
        return old.get("jobs") or {}
    log(f"[brains] {len(vis)} brains on this Mac can see pictures: {', '.join(vis)} - each takes the photo exam "
        "(6 real photos with known answers), thinking on and off, timed")
    results = exam(vis, log)
    jobs = choose(results)
    json.dump({"version": VERSION, "key": key, "at": time.time(), "inventory": inv, "exam": results, "jobs": jobs},
              open(OUT, "w"), indent=1)
    if jobs:
        log(f"[brains] jobs set by the exam: careful looks -> {jobs['judge']}, quick looks -> {jobs['sort']}")
    return jobs


def job(name):
    """The brain chosen for a job by the exam, or None (then the usual list is used)."""
    try:
        return (json.load(open(OUT)).get("jobs") or {}).get(name)
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps(setup(force="--force" in sys.argv), indent=1))
