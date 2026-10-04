"""The local vision model looks at every hunted photo and says, as JSON: is it this exact product, is it from the
right era, which side shows, is it straight-on, sharp and the whole object. Only good photos go on.
Uses Qwen 3.8 (27B, the newest local vision model, chosen 2026-10-02), all on the Mac through Ollama."""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ownmods  # noqa: E402  (nearly every part of the asset maker loads this file: its own files always win)
ownmods.install()

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA = OLLAMA if OLLAMA.startswith("http") else "http://" + OLLAMA
PREFER = ["qwen3.8:27b-q8_0", "qwen3.8:27b", "qwen3.8:latest", "qwen3.5:122b-a10b", "qwen2.5vl:7b"]   # best first
QUICK = ["qwen3.6:35b", "qwen3.5:9b"]     # fast first look (thinking off)


THINK_WORDS, PLAIN_WORDS = 8192, 4096   # the most tokens one answer may take (thinking + JSON / JSON alone)
CTX = 32768   # one memory size for every question to the brain: Ollama reloads a model whenever the size changes,
#               and a question with a photo plus a long think must never run out of room (it is cut silently)


def _test_running():
    """One of Cody's brain tests is scoring a brain right now (the suite's testlock): hands off the brain server -
    his rule, 2026-09-23: "When a brain is testing, all other operations that use said brain need to be refused"."""
    try:
        import ownmods
        testlock = ownmods.outside("~/.hellbox/ai/testlock.py", "testlock")   # (it puts its folder in front)
        return bool(testlock) and testlock.testing() and not testlock.mine()
    except Exception:
        return False


def _call(path, body, timeout=900):
    if path in ("/api/chat", "/api/generate") and (body.get("messages") or body.get("prompt")):
        waited = 0
        while _test_running() and waited < 3 * 3600:      # wait for the test to finish (checked every minute)
            time.sleep(60)
            waited += 60
    if path in ("/api/chat", "/api/generate") and body.get("model") and (body.get("messages") or body.get("prompt")):
        body = dict(body, options=dict(body.get("options") or {}))
        if int(body["options"].get("num_ctx") or 0) < CTX:
            body["options"]["num_ctx"] = CTX
        body["options"].setdefault("num_predict", THINK_WORDS if body.get("think") else PLAIN_WORDS)   # a budget, always
        body.setdefault("keep_alive", "30m")
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def workers():
    """How many questions to ask the brain at the same time - measured on this Mac by speed.py (the brain server
    answering 2 at once makes about twice the words a minute); 1 until measured."""
    try:
        w = int(json.load(open(os.path.join(os.path.expanduser(os.environ.get(
            "CRUSHED_REMASTER_WORK", "~/crushed-render/remaster")), "speed.json"))).get("workers") or 1)
        return max(1, min(w, 4))
    except Exception:
        return 1


def parallel(fn, items, done=None):
    """fn(item) for every item, `workers()` at a time; results in the same order (an error is kept as the result).
    done(i, result) is called in THIS thread as each one finishes (for progress lines and saving)."""
    items = list(items)
    out = [None] * len(items)
    w = workers()
    if w <= 1 or len(items) <= 1:
        for i, it in enumerate(items):
            try:
                out[i] = fn(it)
            except Exception as e:
                out[i] = e
            if done:
                done(i, out[i])
        return out
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception as e:
                out[i] = e
            if done:
                done(i, out[i])
    return out


def has(name):
    try:
        have = [m["name"] for m in json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=20).read()).get("models", [])]
    except Exception:
        return False
    return name in have or name + ":latest" in have


def _first(names):
    try:
        have = \
            [m["name"] for m in json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=20).read()).get("models", [])]
    except Exception:
        return None
    for m in names:
        if m in have or m + ":latest" in have:
            return m
    return None


def _job(name):
    try:
        import brainjobs
        return brainjobs.job(name)
    except Exception:
        return None


def model():
    """The judge (careful looks): the brain that did best on the photo exam (brainjobs.py); else the usual list."""
    return _job("judge") or _first(PREFER)


def quick_model():
    """The quick look (sorting many photos): the fastest brain that still sorts right on the exam; else the list."""
    q = _job("sort") or _first(QUICK)
    return q if q and q != model() else None


ASK = """Product: {display}
Its era: {era} - any year in that range is the right era
Things that mark the right version: {recognize}
Things that would mean a different version: {avoid}
Look at this photo and answer ONLY with JSON, no other words:
{{"match": 0-10 how surely this shows EXACTLY this product: the right brand, line, flavor/model/version and count,
           in the design of that era (a different flavor or version, or a modern redesign, is at most 4),
  "era_ok": true if the package/design looks like it is from the product's era ({era}), false if not,
  "made_year": the year THIS physical item was most likely made, worked out from what is printed on it: copyright
           years, the design, and dates - a "best if installed by", "expires" or "best by" date comes AFTER it was
           made, so subtract the usual shelf life for this kind of product in that era; null if nothing tells,
  "made_year_why": "what you read and how you worked the year out (e.g. 'best if installed by MAR 2003, this kind
           of product carried a date N years after it was made')",
  "version_seen": "the flavor / model / version and count you can read in the photo, or empty",
  "marks_seen": [each "right version" thing you can ACTUALLY SEE in this photo, written exactly as listed above;
          an empty list if none - never count what you cannot see],
  "avoid_seen": true if any of the "different version" things is visible,
  "count": how many of the product are visible,
  "view": which side faces the camera most: "front", "back", "left", "right", "top", "bottom" or "mixed",
  "straight_on": true if the camera looks squarely at that side,
  "sharp": true if it is in focus and its printing is readable,
  "whole": true if the whole item is in the picture (not cut off, not mostly hidden),
  "kind": "photo" if a real photograph of a physical item, "render" if computer-made, "ad" if an advertisement or
          graphic with added words, "package" if the item is still inside retail packaging (when the product IS
          a package - a box, a bag, a can - a real photo of it is "photo"),
  "problems": "short note of anything wrong, or empty"{note_field}}}"""
NOTE_FIELD = """,
  "note_ok": true ONLY if this photo plainly shows what the owner's note asks for; false ONLY if it plainly shows
           something the note rules out; null when this photo can't tell (the owner's note: "{note}")"""
NOTE_RULE = 2      # how note_ok is asked (2: true / false / null) - an answer asked another way is asked again


def _img(path, side=1280):
    """Photos go to the model at most 1280 px on the long side: big enough to read small print, and about
    a fifth of the reading time of a full-size camera photo."""
    import io
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((side, side), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92)
    return base64.b64encode(b.getvalue()).decode()


_NO_THINK = set()        # brains that answered 400 to think=True: asked plainly from then on (no wasted first call)


def ask(use, text, images, think=True, side=1280):
    """One question to a vision model, answer as JSON. Thinking on gives better judgment; if a model can't think,
    ask again without it rather than failing (and remember that for the rest of the run)."""
    if think and use in _NO_THINK:
        think = False
    # every question has a word budget: a brain that thinks in circles (at temperature 0 it can) would otherwise
    # run to the end of its memory - 30,000 words, half an hour, with the whole line waiting behind it
    body = {"model": use, "stream": False, "format": "json", "think": think,
            "options": {"temperature": 0, "num_predict": THINK_WORDS if think else PLAIN_WORDS},
            "messages": [{"role": "user", "content": text,
                          "images": [_img(p, side) for p in images]}]}
    try:
        txt = _call("/api/chat", body).get("message", {}).get("content", "{}")
    except urllib.error.HTTPError as e:
        if think and e.code == 400:
            _NO_THINK.add(use)
            return ask(use, text, images, think=False, side=side)
        raise
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:                                              # it used its budget up thinking: once more, plainly
        if think:
            return ask(use, text, images, think=False, side=side)
        raise ValueError("the brain gave no answer in JSON")
    return json.loads(m.group(0))


def vet(path, display, era="", use=None, think=True, card=None):
    """One photo judged against the item's card (what marks the right version, what marks a wrong one)."""
    use = use or model()
    if not use:
        return None
    card = card or {}
    note = str(card.get("owner_note") or "").strip()
    import era as ERA
    ev = card.get("era_version") or {}                  # what it was called and looked like in its era
    if ev.get("names"):
        display = f"{display} - in its era it was sold as: {' / '.join(ev['names'])}"
    marks = [str(m) for m in list(ev.get("marks") or []) + list(card.get("recognize", []))]
    q = ASK.format(display=display, era=ERA.describe(card.get("year")) if card.get("year") else "unknown",
                   recognize="; ".join(marks) or "(none listed)",
                   avoid="; ".join(list(ev.get("not_then") or []) + list(card.get("avoid", []))) or "(none listed)",
                   note_field=NOTE_FIELD.format(note=note.replace('"', "'")) if note else "")
    v = ask(use, q, [path], think)                     # an error is an error (never a stored "match 0", 2026-10-04)
    v["model"] = use
    v["marks_listed"] = marks                           # what it was asked to find: run.marks_seen checks names
    if not isinstance(v.get("marks_seen"), list):       # an answer asked another way counts no marks
        v["marks_seen"] = []
    if card.get("year") and v.get("made_year") not in (None, "", "null"):
        o = ERA.off(v.get("made_year"), card.get("year"))      # years outside the item's era (0 = inside it)
        if o is not None:
            v["year_off"] = o
    v["era_names"] = list(ev.get("names") or [])        # judged knowing the era's own names (changed: look again)
    if note:
        v["note"] = note[:200]                          # judged against this note (a new note means a new look)
        v["note_rule"] = NOTE_RULE
        if v.get("note_ok") not in (True, False):
            v["note_ok"] = None                         # can't tell from this photo
    return v


def good(v, need=7):
    return (v and v.get("match", 0) >= need and v.get("era_ok", True) is not False and v.get("sharp", True)
            and v.get("whole", True) and v.get("straight_on", True))


if __name__ == "__main__":
    print(json.dumps(vet(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""), indent=1))
