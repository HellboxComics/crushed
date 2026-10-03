"""The local vision model looks at every hunted photo and says, as JSON: is it this exact product, is it from the
right era, which side shows, is it straight-on, sharp and the whole object. Only good photos go on.
Uses Qwen 3.8 (27B, the newest local vision model, chosen 2026-10-02), all on the Mac through Ollama."""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA = OLLAMA if OLLAMA.startswith("http") else "http://" + OLLAMA
PREFER = ["qwen3.8:27b-q8_0", "qwen3.8:27b", "qwen3.8:latest", "qwen3.5:122b-a10b", "qwen2.5vl:7b"]   # best first
QUICK = ["qwen3.6:35b", "qwen3.5:9b"]     # fast first look (thinking off)


def _call(path, body, timeout=900):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


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


def model():
    """The judge: the best vision model on the Mac."""
    return _first(PREFER)


def quick_model():
    """The quick first look, only used to throw out obvious misses when there are many photos."""
    q = _first(QUICK)
    return q if q and q != model() else None


ASK = """Product: {display}
Things that mark the right version: {recognize}
Things that would mean a different version: {avoid}
Look at this photo and answer ONLY with JSON, no other words:
{{"match": 0-10 how surely this shows EXACTLY this product: the right brand, line, flavor/model/version and count,
           in the design of that era (a different flavor or version, or a modern redesign, is at most 4),
  "era_ok": true if the package/design looks like it is from the product's era (its year +/- 3), false if not,
  "made_year": the year THIS physical item was most likely made, worked out from what is printed on it: copyright
           years, the design, and dates - a "best if installed by", "expires" or "best by" date comes AFTER it was
           made, so subtract the usual shelf life for this kind of product in that era; null if nothing tells,
  "made_year_why": "what you read and how you worked the year out (e.g. 'best if installed by MAR 2003, this kind
           of product carried a date N years after it was made')",
  "version_seen": "the flavor / model / version and count you can read in the photo, or empty",
  "seen": how many of the "right version" things you can actually see in this photo (0 if none),
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


def ask(use, text, images, think=True, side=1280):
    """One question to a vision model, answer as JSON. Thinking on gives better judgment; if a model can't think,
    ask again without it rather than failing."""
    body = {"model": use, "stream": False, "format": "json", "think": think, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": text,
                          "images": [_img(p, side) for p in images]}]}
    try:
        txt = _call("/api/chat", body).get("message", {}).get("content", "{}")
    except urllib.error.HTTPError as e:
        if think and e.code == 400:
            return ask(use, text, images, think=False, side=side)
        raise
    return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))


def vet(path, display, era="", use=None, think=True, card=None):
    """One photo judged against the item's card (what marks the right version, what marks a wrong one)."""
    use = use or model()
    if not use:
        return None
    card = card or {}
    note = str(card.get("owner_note") or "").strip()
    q = ASK.format(display=display, recognize="; ".join(card.get("recognize", [])) or "(none listed)",
                   avoid="; ".join(card.get("avoid", [])) or "(none listed)",
                   note_field=NOTE_FIELD.format(note=note.replace('"', "'")) if note else "")
    try:
        v = ask(use, q, [path], think)
    except Exception as e:
        return {"match": 0, "problems": f"could not judge: {e}"}
    v["model"] = use
    try:                                                # how far the item in the photo was made from the catalog year
        y, my = int(card.get("year") or 0), v.get("made_year")
        if y and my not in (None, "", "null") and 1900 < int(str(my)[:4]) < 2100:
            v["year_off"] = abs(int(str(my)[:4]) - y)
    except (TypeError, ValueError):
        pass
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
