"""YOUR AI WRITES ITS OWN KITS (Cody, 2026-10-03: "a universal process for all products, whether battery, furby, pop
tarts, pants, shirt, shoes, cd, magazine, graphics card ... all on its own, without any of your input, ever").

A kit is what the asset maker knows about a KIND of thing before it builds one: its parts and what each is made
of, its print zones and what every zone normally carries, its standard sizes with their sources, how a collector
names its sides in a search. The first kits (battery, can, carton) were written by hand as examples of the format.
Every other kind your AI meets, it studies and writes down itself, once, here - in
~/crushed-render/remaster/kits/learned.json - and every later item of that kind uses it.

How it studies a kind:
  1. KIND      from the picked photo and the catalog name: what kind of thing is this, in a name any person would
               use ("plush toy", "jeans", "sneaker", "graphics card", "magazine")
  2. BUILD     how a factory makes one: the parts in assembly order, each part's material (one of the materials the
               crush physics knows), hard or soft, printed or plain
  3. ZONES     where print or pattern goes (wrap / rect / disc / fabric / form) and what each zone NORMALLY carries,
               with the patterns a label of that kind is checked against (size, model, warnings, "made in"...)
  4. SIZES     the standard sizes, if the kind has any (a 12 oz can, an AA cell, a CD, a VHS) - from a web search,
               each with its source; a size with no source is not a standard size
  5. SIDES     how sellers and collectors name each side in a photo search
  6. CHECK     the kit is checked by code (every part's material is a known one, every zone has a kind the builders
               know, sizes have sources) and written down with the photos and pages it came from

    kit = kitmaker.ensure(kind, card, photo, use, log)      # the kit for this kind, learned now if it is new
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
LEARNED = os.path.join(WORK, "kits", "learned.json")
# a test build (the engineer's) reads the shared learned kits but writes only its own copy (never shared state)
LEARNED_WRITE = os.path.join(os.path.expanduser(os.environ["CRUSHED_KEPT_WRITE"]), "learned_kits.json") \
    if os.environ.get("CRUSHED_KEPT_WRITE") else LEARNED
VERSION = 1
ZONE_KINDS = ("wrap", "rect", "disc", "fabric", "form")

STUDY = """[kit] {photo_note} "{product}" (catalog size {size} mm). We are teaching an asset maker how to
build EVERY object of this KIND, not just this one - the way a model maker studies a kind of thing before building.
The kind: "{kind}". Materials the crush physics knows (use ONLY these names for "material"): {materials}.
Answer ONLY JSON:
{{"what": "one line: what this kind of thing is",
 "looks_like": ["3-6 other things of this kind, e.g. for a plush toy: teddy bear, Beanie Baby"],
 "not": ["2-4 things that look similar but are a different kind"],
 "construction": "soft (sewn fabric, fur, foam)", "molded (plastic shell)", "stamped metal", "printed board", "folded card", "sewn garment", or "assembled (several hard parts)",
 "parts": [{{"part": "name", "material": "<one of the materials>", "hard": true/false, "printed": true/false,
            "how": "how the factory makes/attaches it, one line"}}  - in assembly order, 3 to 12 parts],
 "zones": [{{"name": "front | back | left | right | top | bottom | label | body | sole | sleeve ...",
            "kind": "wrap | rect | disc | fabric | form",
            "typical": ["what is NORMALLY there on this kind: a logo, a size tag, a barcode, a warning, a date..."],
            "expect": [{{"what": "a thing nearly every one of this kind carries in print", "pattern": "a short regular expression that would match it in read words, e.g. \\\\bSIZE\\\\b|\\\\b(S|M|L|XL)\\\\b", "search": "1-3 words to search for a photo showing it"}}]}}],
 "standard_sizes": true/false (does this KIND come in fixed standard sizes, like batteries, cans, discs, tapes?),
 "size_search": "a web search that finds the standard size(s) with numbers, if standard_sizes",
 "side_words": {{"front": ["how a seller names a photo of the front"], "back": ["..."], "left": ["..."], "right": ["..."], "top": ["..."], "bottom": ["..."]}},
 "views_needed": ["the photo views needed to build one well: front, back, left, right, top, bottom, flat label, inside..."]}}"""

SIZES = """We need the STANDARD sizes of this kind of thing: {kind} (an example: {product}). Web search results:
{hits}
Answer ONLY JSON: {{"variants": {{"<variant name, e.g. 12 fl oz>": {{"size_mm": [width, depth, height], "source": "the result's title and the words giving the numbers"}}}}}}
Only sizes a result states in numbers; none when no result states them. Never estimate."""


def learned():
    out = {}
    for p in dict.fromkeys([LEARNED, LEARNED_WRITE]):
        try:
            out.update(json.load(open(p)))
        except Exception:
            pass
    return out


def _save(d):
    os.makedirs(os.path.dirname(LEARNED_WRITE), exist_ok=True)
    json.dump(d, open(LEARNED_WRITE + ".tmp", "w"), indent=1)
    os.replace(LEARNED_WRITE + ".tmp", LEARNED_WRITE)


def key(kind):
    return re.sub(r"[^a-z0-9]+", "_", str(kind).lower()).strip("_")[:40]


def _materials():
    ph = json.load(open(os.path.join(HERE, "factory", "physics.json")))
    return sorted(k for k in ph if not k.startswith("_"))


def _route(k):
    """Which builder a learned kind goes to: round things to the lathe, folded card to the carton, hard assembled
    things to the parts builder, soft things to the parts builder too (its form parts are shaped from several
    views) - never the one-photo organic guess."""
    c = str(k.get("construction", "")).lower()
    zones = {z.get("kind") for z in k.get("zones") or []}
    if "wrap" in zones and "disc" in zones:
        return "round", "lathe"
    if "folded card" in c:
        return "box", "carton"
    if "printed board" in c:
        return "box", "pcb"
    return "free", "assembly"


def check(k):
    """Code checks on a studied kit: every part's material known, every zone's kind one the builders know, at least
    one zone and three parts, sizes only with sources. -> [problems]"""
    mats = set(_materials())
    probs = []
    parts = k.get("parts") or []
    if len(parts) < 3:
        probs.append("fewer than 3 parts")
    for p in parts:
        if p.get("material") not in mats:
            probs.append(f"part {p.get('part')}: material {p.get('material')!r} is not one the physics knows")
    zones = k.get("zones") or []
    if not zones:
        probs.append("no print zones")
    for z in zones:
        if z.get("kind") not in ZONE_KINDS:
            probs.append(f"zone {z.get('name')}: kind {z.get('kind')!r} is not one the builders know")
        for e in z.get("expect") or []:
            try:
                re.compile(e.get("pattern") or "")
            except re.error:
                probs.append(f"zone {z.get('name')}: a pattern does not compile")
    for v, d in (k.get("variants") or {}).items():
        s = d.get("size_mm")
        if not (isinstance(s, list) and len(s) == 3 and all(isinstance(x, (int, float)) and 0 < x < 5000 for x in s)):
            probs.append(f"size {v}: no usable numbers")
        if not d.get("source"):
            probs.append(f"size {v}: no source")
    return probs


def _sizes(kind, product, search, use, log):
    import vet as V
    import websearch
    try:
        hits = websearch.search(search or f"{kind} standard dimensions mm", n=8, log=log)
    except Exception as e:
        log(f"[kit] the size search did not work: {e}")
        return {}
    if not hits:
        return {}
    txt = "\n".join(f"- {h.get('title', '')} - {h.get('snippet', '')}"[:300] for h in hits[:8])
    try:
        v = V.ask(use, SIZES.format(kind=kind, product=product, hits=txt), [], think=True) or {}
    except Exception as e:
        log(f"[kit] the sizes could not be read: {e}")
        return {}
    out = {}
    for name, d in (v.get("variants") or {}).items():
        s = (d or {}).get("size_mm")
        if isinstance(s, list) and len(s) == 3 and all(isinstance(x, (int, float)) and 0 < x < 5000 for x in s) \
                and d.get("source"):
            missing = numbers_missing(s, txt)
            if missing:                                  # (audit 2026-10-04: a "source" the brain wrote itself is
                log(f"[kit] size {name} {s} dropped: {missing} not in any result - a size needs its numbers in the source")
                continue                                 # no source - the numbers must be IN the results)
            out[str(name)[:30]] = {"size_mm": [float(x) for x in s], "source": str(d["source"])[:300]}
    return out


def numbers_missing(size_mm, text):
    """The numbers of a size that do NOT appear in the text (as mm, cm or inches, to the usual rounding) - a size
    whose numbers are not in its source was remembered or guessed, never read. At most one may be missing (a depth
    equal to the width is often not repeated)."""
    import re
    nums = set()
    for t in re.findall(r"\d+(?:[.,]\d+)?", text or ""):
        try:
            nums.add(float(t.replace(",", ".")))
        except ValueError:
            pass
    miss = []
    for x in size_mm:
        x = float(x)
        forms = [x, x / 10, x / 25.4]                                     # mm, cm, in
        found = any(abs(n - f) <= max(0.015 * f, 0.051) for f in forms for n in nums)
        if not found:
            miss.append(x)
    seen = len(size_mm) - len(miss)
    return miss if seen < 2 else []


def study(kind, card, photo, use, log=print):
    """Your AI studies a kind of thing once and writes its kit. -> the kit (a family entry) or None with the why."""
    import vet as V
    size = "x".join(str(round(x * 1000)) for x in (card.get("size") or [0, 0, 0])[:3])
    k = V.ask(use, STUDY.format(product=card.get("product", ""), size=size, kind=kind, materials=", ".join(_materials()),
                                photo_note="Picture 1 is a real photo of" if photo else
                                "From what you know (no photo is given) about an example of this kind,"),
              [photo] if photo else [], think=True, side=1280) or {}
    if not k.get("parts"):
        log(f"[kit] {kind}: your AI gave no parts for this kind - not written")
        return None
    if k.get("standard_sizes"):
        k["variants"] = _sizes(kind, card.get("product", ""), k.get("size_search"), use, log)
        if k["variants"]:
            k["variant_default"] = sorted(k["variants"])[0]
    probs = check(k)
    for p in list(probs):                                  # a bad material is asked about once more, by name
        m = re.match(r"part (.*): material (.*) is not one", p)
        if m:
            k["parts"] = [dict(x, material="molded_plastic" if x.get("hard") else "fabric") if x.get("part") == m.group(1)
                          and x.get("material") not in _materials() else x for x in k["parts"]]
    probs = check(k)
    if probs:
        log(f"[kit] {kind}: the studied kit has problems: {'; '.join(probs)[:300]}")
        if any(not p.startswith("size") for p in probs):
            return None
    route, builder = _route(k)
    fam = {"what": k.get("what", kind), "looks_like": k.get("looks_like") or [], "not": k.get("not") or [],
           "route": route, "builder": builder, "builder_status": "partial", "gaps": [],
           "construction": k.get("construction"), "parts": k.get("parts"), "zones": k.get("zones"),
           "faces": [z["name"] for z in k.get("zones") or [] if z.get("name")],
           "side_words": k.get("side_words") or {}, "views_needed": k.get("views_needed") or [],
           "variants": k.get("variants") or {}, "variant_default": k.get("variant_default"),
           "learned": {"by": use, "from": card.get("id"), "photo": photo, "at": time.time(), "version": VERSION}}
    return fam


def ensure(kind, card, photo, use, log=print):
    """The kit for this kind: a hand-written one, a learned one, or studied now. -> (key, kit) or (None, None)."""
    import kits
    kk = key(kind)
    lib = kits.library()["families"]
    if kk in lib and kits.finished(lib[kk]):
        return kk, lib[kk]
    L = learned()
    if kk in L and L[kk].get("learned", {}).get("version") == VERSION:
        return kk, L[kk]
    log(f"[kit] {card.get('id', '')}: " + (f"the kind '{kk}' has no finished kit" if kk in lib else
                                           f"a new kind of thing ({kind})") + " - your AI studies it and writes its kit")
    fam = study(kind, card, photo, use, log)
    if not fam:
        return None, None
    L = learned()
    L[kk] = fam
    _save(L)
    log(f"[kit] {kk}: written - {len(fam['parts'])} parts, zones {', '.join(fam['faces'])}, "
        f"{len(fam['variants'])} standard size(s), built by {fam['builder']}")
    return kk, fam
