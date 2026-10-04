"""THE PORTAL: Cody talks to the asset maker directly, from his phone (Cody, 2026-10-03: "give me a portal so I can
communicate with it directly for any other object after it's done with its current list").

He writes to his own phone bot (Hart). Two kinds of message:
  1. a note on an item in the list      "note duracell: the 1999 version with the hologram"
                                        "poptarts: build the blue box"           (an item's words, a colon, the note)
  2. a NEW object                        "Furby 1998 gray with pink ears"  /  "90s Walkman WM-FX101"  / a photo with
                                        a caption - anything that isn't a note
A new object becomes an item the same as any catalog item: the asset maker's own brain reads the message (and the
photo), names it the catalog way ("Sony Walkman WM-FX101 cassette player, circa 1996"), finds its real size with a
web search and keeps the receipt, and puts it FIRST in line. His photo goes into the item's hunt as one more photo
(ranked like any other). He gets one reply: what was understood, the size and its source, and that it is next.
Nothing he writes is ever invented around: a size with no source is asked for, not guessed.

Files (all in ~/crushed-render/remaster/portal/): inbox.json (written by the phone bot), items.json (the new items'
catalog entries), queue.txt (the new items, first in line), done.json (replies sent).
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
DIR = os.path.join(WORK, "portal")
INBOX, ITEMS, QUEUE, DONE = (os.path.join(DIR, n) for n in ("inbox.json", "items.json", "queue.txt", "done.json"))

UNDERSTAND = """Someone typed this to the asset maker on their phone: "{text}"{photo}
They want a real-size 3D model of one real-world object. Answer ONLY JSON:
{{"product": "the object the catalog way: brand, line, version, what it is, ', circa YEAR' - e.g. 'Sony Walkman WM-FX101 cassette player, circa 1996'",
 "year": the year it is from (a number; the one they said, else the middle of the era they meant, else null),
 "kind": "battery | can | bottle | box | cassette | vhs | cd | cartridge | toy | garment | gadget | food | other",
 "size_known_mm": [width, depth, height] in mm if you KNOW this exact object's standard size for sure, else null,
 "size_search": "a short web search that would find its real dimensions",
 "is_note": true if this is really a direction about an item already being made (a version, a color, a design) and not a new object}}"""

SIZE_Q = """We need the real size of: {product}. Here are web search results (title - snippet):
{hits}
Answer ONLY JSON: {{"size_mm": [width, depth, height] in mm, or null if no result states real measurements,
 "source": "the title of the result the numbers come from", "quote": "the words that give the numbers"}}
Never estimate: null when no result states it."""


def _load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def _save(p, v):
    os.makedirs(DIR, exist_ok=True)
    tmp = p + ".tmp"
    json.dump(v, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def items():
    return _load(ITEMS, {})


def queue_first():
    """The portal's items, first in line (newest first)."""
    try:
        return [l.strip() for l in open(QUEUE) if l.strip()]
    except OSError:
        return []


def slug(product, year):
    s = re.sub(r"[^a-z0-9]+", "_", product.split(",")[0].lower()).strip("_")[:50]
    return f"{s}_{year}" if year else s


def _known_items():
    """Every item the asset maker knows, by id -> product (the catalog and the portal's)."""
    out = {}
    try:
        plan = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "plan", "items.json")))
        out.update({k: v.get("product", k) for k, v in plan.items()})
    except Exception:
        pass
    out.update({k: v.get("product", k) for k, v in items().items()})
    return out


def match_item(words):
    """The item whose id or name carries every word given ("duracell" -> duracell_coppertop_aa_1998), or None."""
    ws = [w for w in re.findall(r"[a-z0-9]+", words.lower()) if len(w) >= 3]
    if not ws:
        return None
    hits = [k for k, p in _known_items().items() if all(w in (k + " " + p).lower() for w in ws)]
    if len(hits) > 1:                                      # several: the ones being worked on now come first
        try:
            st = json.load(open(os.path.join(WORK, "library", "status.json")))
            working = [k for k in hits if k in st]
            hits = working or hits
        except Exception:
            pass
    return hits[0] if len(hits) == 1 else None


def choices(words, most=6):
    ws = [w for w in re.findall(r"[a-z0-9]+", words.lower()) if len(w) >= 3]
    return [k for k, p in _known_items().items() if ws and all(w in (k + " " + p).lower() for w in ws)][:most]


def _reply(text):
    try:
        sys.path.insert(0, os.path.expanduser("~/.hellbox/ai/hart"))
        import hart as H
        H.send(text)
    except Exception:
        pass


def _size_from_web(product, search, model, log):
    import vet as V
    import websearch
    try:
        hits = websearch.search(search or f"{product} dimensions mm", n=8, log=log)
    except Exception as e:
        log(f"[portal] the size search did not work: {e}")
        hits = []
    if not hits:
        return None, ""
    txt = "\n".join(f"- {h.get('title', '')} - {h.get('snippet', '')}"[:300] for h in hits[:8])
    try:
        v = V.ask(model, SIZE_Q.format(product=product, hits=txt), [], think=True) or {}
    except Exception as e:
        log(f"[portal] the size could not be read from the results: {e}")
        return None, ""
    s = v.get("size_mm")
    if isinstance(s, list) and len(s) == 3 and all(isinstance(x, (int, float)) and 1 <= x <= 3000 for x in s):
        return [float(x) for x in s], f"{v.get('source', '')}: {v.get('quote', '')}"[:300]
    return None, ""


def process(log=print, model=None):
    """Every message in the inbox: a note on an item, or a new item put first in line. Each gets one reply."""
    inbox = _load(INBOX, [])
    done = _load(DONE, {})
    todo = [m for m in inbox if str(m.get("id")) not in done]
    if not todo:
        return []
    import vet as V
    import notes as NT
    model = model or V.model()
    out = []
    for m in todo:
        mid = str(m.get("id"))
        text = str(m.get("text") or "").strip()
        photo = m.get("photo") if m.get("photo") and os.path.exists(str(m.get("photo"))) else None
        try:
            # 1. a note: "note <item>: ..." or "<item words>: ..."
            mm = re.match(r"^(?:note\s+)?([^:]{3,60}):\s*(.+)$", text, re.S | re.I)
            cid = match_item(mm.group(1)) if mm else None
            if mm and cid and cid in items() and not items()[cid].get("size") and _size_reply(cid, mm.group(2)):
                _reply(f"Thanks - {items()[cid]['product']} at that size is first in line.")
                done[mid] = {"kind": "size", "item": cid, "at": time.time()}
                continue
            if mm and cid:
                NT.add(cid, mm.group(2).strip(), repick=bool(re.search(r"version|design|color|colour|box|label|instead",
                                                                        mm.group(2), re.I)))
                _reply(f"Noted for {cid.replace('_', ' ')}: \"{mm.group(2).strip()}\". It follows that from now on.")
                done[mid] = {"kind": "note", "item": cid, "at": time.time()}
                out.append(("note", cid))
                continue
            # 2. a new object
            if not text and not photo:
                done[mid] = {"kind": "empty", "at": time.time()}
                continue
            u = V.ask(model, UNDERSTAND.format(text=text or "(no words, a photo only)",
                                               photo=" They also sent this photo." if photo else ""),
                      [photo] if photo else [], think=True) or {}
            if mm and not cid and choices(mm.group(1)):
                _reply("Which one? " + ", ".join(choices(mm.group(1))) + f". Write it as \"<its id>: {mm.group(2).strip()[:60]}\".")
                done[mid] = {"kind": "which", "at": time.time()}
                continue
            if u.get("is_note") and not photo:
                _reply(f"That sounds like a direction about an item already in the list. Write it as "
                       f"\"<item>: <what to do>\" (for example \"duracell coppertop aa: the 1999 version\").")
                done[mid] = {"kind": "unclear", "at": time.time()}
                continue
            product = str(u.get("product") or text)[:160]
            year = u.get("year") if isinstance(u.get("year"), int) else None
            cid = slug(product, year)
            size, src = (u.get("size_known_mm"), "the brain's own knowledge of the standard size") \
                if isinstance(u.get("size_known_mm"), list) and len(u.get("size_known_mm")) == 3 else (None, "")
            if not size:
                size, src = _size_from_web(product, u.get("size_search"), model, log)
            if not size:
                _reply(f"I'd make \"{product}\" but I can't find its real size anywhere, and I never guess a size. "
                       f"Reply \"{cid}: size W x D x H mm\" and it goes first in line.")
                its = items()
                its[cid] = {"product": product, "year": year, "kind": u.get("kind"), "size": None,
                            "photo": photo, "asked_size": time.time(), "from": text}
                _save(ITEMS, its)
                done[mid] = {"kind": "needs_size", "item": cid, "at": time.time()}
                continue
            its = items()
            its[cid] = {"product": product, "year": year, "kind": u.get("kind"), "size": [x / 1000 for x in size],
                        "size_source": src, "photo": photo, "from": text, "at": time.time()}
            _save(ITEMS, its)
            if photo:
                _add_photo(cid, photo)
            q = [c for c in queue_first() if c != cid]
            os.makedirs(DIR, exist_ok=True)
            open(QUEUE, "w").write("\n".join([cid] + q) + "\n")
            _reply(f"Got it: {product}. Real size I'll build: {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm "
                   f"({src[:120]}). It's first in line" + (" - your photo is in its photos." if photo else "."))
            done[mid] = {"kind": "new", "item": cid, "at": time.time()}
            out.append(("new", cid))
            log(f"[portal] new item from your phone: {cid} ({product}) - first in line")
        except Exception as e:
            log(f"[portal] message {mid} could not be handled: {e}")
            done[mid] = {"kind": "error", "why": str(e)[:200], "at": time.time()}
            _reply("Sorry - that message could not be handled (" + str(e)[:80] + "). Try again in other words.")
        finally:
            _save(DONE, done)                              # after EVERY message (a 'continue' skipped this before:
    return out                                             # replies repeated and notes were rewritten each run)


def _size_reply(cid, text):
    """"<item>: size 66 x 66 x 122 mm" for an item that waited for its size."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm|in)?", text, re.I)
    if not m:
        return False
    k = {"cm": 10, "in": 25.4}.get((m.group(4) or "mm").lower(), 1)
    size = [float(m.group(i)) * k for i in (1, 2, 3)]
    its = items()
    if cid not in its:
        return False
    its[cid].update(size=[x / 1000 for x in size], size_source="given by Cody on the phone")
    _save(ITEMS, its)
    open(QUEUE, "w").write("\n".join([cid] + [c for c in queue_first() if c != cid]) + "\n")
    return True


def _add_photo(cid, photo):
    """His photo joins the item's hunt as one more photo (ranked like any other)."""
    import hashlib
    import shutil
    d = os.path.join(WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "p" + hashlib.sha1(open(photo, "rb").read()).hexdigest()[:12] + ".jpg")
    if not os.path.exists(p):
        shutil.copy(photo, p)
    fj = os.path.join(d, "found.json")
    found = _load(fj, [])
    if not any(f.get("file") == p for f in found):
        found.insert(0, {"file": p, "url": "", "page": "", "title": "your photo", "source": "your phone"})
        json.dump(found, open(fj, "w"), indent=1)


def catalog_entry(cid):
    """The portal item's catalog entry, as cards.catalog() needs it (None when it isn't a portal item)."""
    it = items().get(cid)
    if not it or not it.get("size"):
        return None
    return {"product": it["product"], "size": it["size"], "mat": "plastic", "master": None,
            "size_source": it.get("size_source", "")}
