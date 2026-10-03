"""KNOW THE OBJECT BEFORE BUILDING IT: one dossier per item, kept in ~/crushed-render/remaster/dossier/<item>.json.

Before a single face is drawn, your local AI works out what the item really is and finds every side of it:
  1. identity   it reads your picked photo: brand, product line, flavor/version, count, net weight, maker, whether
                it is food, and names the line's sister flavors of that era (sisters are only search words, never
                facts)
  2. hunt       every side of the item, three ways: this exact item; its sister flavors; this item in nearby years
                (the era is a range people use: a 1998 item is a "90s" item, a 2003 one
                "early 2000s" - library/era.py). Short, varied Google Images searches through your
                bot's own browser - at most 16 per item, 20 s apart, about 5 photos kept from each. Every photo
                ever looked at is written down and reused next time (the first hunt's photos too), so a rebuild
                never loses the backs and sides already found.
  3. label      a quick look at every photo (which side, which product, real photo or ad), then the careful look
                (thinking on) at the best few for each side: which side, exact / sister / nearby-year / wrong,
                year clues, the words it can read, a quality score, and everything printed on it - with the place of
                each item-specific part (flavor name, nutrition panel, barcode) so a sister's photo can be used with
                those parts replaced
  4. plan       for each side: this item's own photo, else a sister box's photo with its item-specific parts
                swapped for this item's facts, else rebuilt from facts only (in the closest sister's layout). Every
                gap is written down in plain words.
  5. facts      the printed facts with receipts (library/facts.py)

    d = dossier.build(cid, card, picked)      # reused next time unless redo=True or its inputs changed
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
DIR = os.environ.get("CRUSHED_DOSSIER_DIR") or os.path.join(WORK, "dossier")   # a test build keeps its own copy
VERSION = 4                  # 2: a round item's wrapped side is its label; watermarks are never facts or copied sides
#                              3: the era is a range people use ("90s", "early 2000s"), never year +/- 3
#                              4: a round end's reference photo must show that end end-on (a disc)
BUDGET = 16                  # Google searches per item, at most (20 s apart)
PER_SEARCH = 5               # photos kept from each search
LOOK = 2                     # careful looks per side (the quick look already ranks every photo)
MOST_LOOKS = 12              # careful looks per item, at most

FACES = {"box": ["front", "back", "left", "right", "top", "bottom"], "round": ["label", "top", "bottom"],
         "flat": ["front", "back"], "pcb": ["top", "bottom"],
         "free": ["front", "back", "left", "right", "top", "bottom"]}
PRIMARY = {"box": "front", "flat": "front", "free": "front", "round": "label", "pcb": "top"}
WORDS = {   # how a collector says each side in a search
    "box": {"back": ["box back", "back of box"], "left": ["box side panel", "box side nutrition facts"],
            "right": ["box side panel", "box side nutrition facts"], "top": ["box top", "box top flap"],
            "bottom": ["box bottom", "box bottom barcode"]},
    "round": {"label": ["label", "back label"], "top": ["top", "lid"], "bottom": ["bottom", "base"]},
    "flat": {"back": ["back", "reverse side"]},
    "pcb": {"top": ["card", "board"], "bottom": ["back of card", "solder side"]},
    "free": {"back": ["back", "back view"], "left": ["side", "side view"], "right": ["side", "side view"],
             "top": ["top", "top view"], "bottom": ["bottom", "underside"]},
}
NAMES = ["front", "back", "left", "right", "side", "top", "bottom", "label"]
# What a look calls a side -> the side it is for this kind of thing. A battery, can or bottle has ONE wrapped side
# (its label): its "front" and "back" in a photo are both parts of that label. (Found 2026-10-03: the Duracell's
# label had nothing to check its words against, because your AI called the label's two halves "front" and "back".)
FACE_ALIAS = {"round": {"front": "label", "back": "label", "left": "label", "right": "label", "side": "label"},
              "pcb": {"front": "top", "back": "bottom"},
              "flat": {"top": None, "bottom": None, "left": None, "right": None, "side": None}}


def face_name(route, f):
    """The side a look's face name means for this route (None: not a side this kind of thing has)."""
    return FACE_ALIAS.get(route, {}).get(f, f)

ID_Q = """[identity] Picture 1 is the photo picked as the true "{product}". Its catalog card says: real size
{size} mm (width x depth x height), year {year}.
Read the item in the photo. Copy brand, line, variant, count and size EXACTLY as printed; leave a field empty when
it can't be read - never fill it in from memory. Answer ONLY JSON:
{{"brand": "the brand as printed, e.g. Kellogg's",
 "line": "the product line as printed, e.g. Pop-Tarts",
 "variant": "the flavor / version / model as printed, e.g. Frosted Strawberry",
 "count": "how many the package holds, as printed, e.g. 8 TOASTER PASTRIES, or empty",
 "size_text": "the net weight / size line exactly as printed, or empty",
 "maker": "the company named on it, or empty",
 "unit": "what one item inside is called, e.g. toaster pastry, or empty",
 "kind": "packaging" if it is a package holding a product, "object" if it is the thing itself,
 "food": true if what it holds is food or drink, else false,
 "sisters": ["up to 6 other flavors / versions of this same product line sold around {year} - search words only"]}}"""

QUICK_Q = """[quick] We are rebuilding: {name} ({year}). Look at this photo. Answer ONLY JSON:
{{"face": which side fills most of the photo: "front", "back", "left", "right", "side" (a narrow side when you
   can't tell left from right), "top", "bottom", "label", "several" (a carton cut open and laid flat, or several
   sides flat), "mixed" (a corner view), or "none",
 "product_shown": "brand, line, flavor/version and count you can read, e.g. Kellogg's Pop-Tarts Frosted Cherry 6 ct",
 "same_line": true if it is the same brand and product line as ours (any flavor or version),
 "same_item": true if it is exactly our flavor / version and count,
 "kind": "photo" (a real photo of a real one), "flat" (a real package cut open and laid flat), "render"
   (a computer-made product picture), "ad" (an ad or graphic), or "other",
 "era": "the years the package design looks like, e.g. 1990s or 2018-2024",
 "useful": 0-10 how useful it is for seeing a side OTHER than the front of our product line in that era}}"""

LABEL_Q = """[label] We are rebuilding: {name} ({year}; same era = {y0} to {y1}). {ref}
Look at picture 1 carefully. Answer ONLY JSON:
{{"faces": [every side of the package visible in picture 1, the one filling most of the photo first:
   {{"face": "front" | "back" | "left" | "right" | "side" (a narrow side, left or right unknown) | "top" | "bottom" |
     "label", "box": [x0, y0, x1, y1] where that side is (fractions 0..1 of the photo, from the left and the top),
     "straight_on": true if seen squarely, "edge_on": true if seen so steeply it is a thin sliver,
     "turn": 0 | 90 | 180 | 270 (how many degrees to turn that side clockwise so its printing reads upright)}}],
 "match": "exact" (this very flavor/version and count, from that era), "sister" (the same line and era, another
   flavor/version or count), "near_year" (this item but a different year inside the era), or "wrong" (another
   product, or outside {y0}-{y1}, or a modern redesign),
 "product_shown": "brand, line, flavor/version and count you can read",
 "years": [earliest, latest] year the package could be from (copyright dates, design, nutrition label format),
 "years_why": "what tells you the years",
 "text": ["every line of words you can read, exactly as printed"],
 "quality": 0-10 (10 = straight-on, filling the frame, sharp, evenly lit, nothing covering it),
 "elements": [everything printed on the visible sides: {{"face": "...", "what": "short name, e.g. nutrition panel,
   flavor name, barcode, maker's address, logo, product picture, recycled-paper seal",
   "text": "its words exactly, or empty", "kind": "barcode" | "text" | "panel" | "graphic",
   "item_specific": true if it changes from flavor to flavor or box to box (flavor name, flavor picture,
   nutrition panel, ingredients, barcode, count, net weight, date code),
   "box": [x0, y0, x1, y1] fractions of the photo (required when item_specific)}}],
 "overlays": [everything laid ON TOP of the photo that is NOT printed on the item itself - a watermark, a
   photographer's or seller's name, an email or web address over the picture, a price or store sticker, a hand or
   finger covering print: {{"what": "short name", "text": "its words exactly, or empty", "box": [x0, y0, x1, y1]}}
   - an empty list when there is none]}}
{sides_hint}"""
SIDES_HINT = {"round": "This item is ROUND (a battery, can, bottle, jar or tube): its wrapped printed side is "
                       "\"label\" (call every part of the wrap \"label\"), its two ends are \"top\" and \"bottom\".",
              "pcb": "This item is a circuit card: the side with the chips is \"top\", the solder side is \"bottom\".",
              "flat": "This item is flat (a sheet or card): it only has a \"front\" and a \"back\"."}


# ------------------------------------------------------------------ files
def path(cid):
    return os.path.join(DIR, cid + ".json")


def load(cid):
    try:
        return json.load(open(path(cid)))
    except Exception:
        return None


def save(dos):
    os.makedirs(DIR, exist_ok=True)
    p = path(dos["cid"])
    tmp = p + ".tmp"
    json.dump(dos, open(tmp, "w"), indent=1)
    os.replace(tmp, p)
    return p


def _set_aside(cid, why):
    """An older dossier is moved to dossier/old/, never deleted."""
    p = path(cid)
    if os.path.exists(p):
        old = os.path.join(DIR, "old", f"{cid}-{time.strftime('%Y%m%d-%H%M%S')}.json")
        os.makedirs(os.path.dirname(old), exist_ok=True)
        shutil.move(p, old)
        open(old[:-5] + ".txt", "w").write(f"older dossier of {cid}, set aside because {why}\n")


def route_of(card):
    """Which faces this item has: by its family from the family library (read from the photo by families.py), else
    the card's build route (a circuit card is 'pcb', a measured master is round)."""
    fl = (card.get("family_lib") or {}).get("family")
    if fl:
        try:
            import families
            r = families.get(fl).get("route")
            if r in FACES:
                return r
        except Exception:
            pass
    if str(card.get("family", "")) == "printed_circuit_card":
        return "pcb"
    try:
        if json.load(open(os.path.join(HERE, "families.json"))).get(card.get("id", ""), {}).get("shape"):
            return "round"
    except Exception:
        pass
    r = card.get("route")
    return r if r in FACES else "free"


def _same_inputs(a, b):
    """The same item, size, year, route and pick? (the rules' version is not an input: a dossier made under older
    rules is brought up to date by replan() from the looks already taken, never thrown away for it)"""
    strip = lambda d: {k: v for k, v in (d or {}).items() if k != "version"}
    return bool(a) and strip(a) == strip(b)


def _inputs(card, picked):
    return {"product": card.get("product"), "size": card.get("size"), "year": card.get("year"),
            "route": route_of(card), "picked": (picked or {}).get("file") if isinstance(picked, dict) else picked,
            "version": VERSION}


# ------------------------------------------------------------------ small helpers
def parse_years(s):
    """'1990s' -> [1990, 1999]; 'late 1990s' -> [1995, 1999]; '1995-1999' -> [1995, 1999]; '1997' -> [1997, 1997]"""
    s = str(s or "").lower().replace("–", "-").replace("'", "")
    m = re.search(r"\b(19|20)?(\d)0s\b", s)
    if m and not re.search(r"\b(19[5-9]\d|20[0-4]\d)\s*-\s*(19[5-9]\d|20[0-4]\d)\b", s):
        c = m.group(1) or ("19" if m.group(2) in "56789" else "20")
        lo = int(c + m.group(2) + "0")
        if "early" in s:
            return [lo, lo + 4]
        if "late" in s:
            return [lo + 5, lo + 9]
        if "mid" in s:
            return [lo + 3, lo + 7]
        return [lo, lo + 9]
    ys = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", s)]
    return [min(ys), max(ys)] if ys else []


def _overlap(ys, era):
    return bool(ys) and len(ys) == 2 and ys[0] <= era[1] and ys[1] >= era[0]


def _box(b):
    """A box as fractions 0..1 (answers in 0..1000 are scaled), or None."""
    try:
        b = [float(v) for v in b][:4]
        if len(b) < 4:
            return None
        if max(b) > 1.5:
            b = [v / 1000 for v in b]
        x0, y0, x1, y1 = (min(max(v, 0.0), 1.0) for v in b)
        return [x0, y0, x1, y1] if x1 - x0 > 0.01 and y1 - y0 > 0.01 else None
    except Exception:
        return None


def _str(v, n=200):
    return str(v).strip()[:n] if v not in (None, False) else ""


def _download(url, d):
    """One photo from the web into the item's hunt folder, named the same way the first hunt names them (so a photo
    the first hunt already saved is never fetched twice). -> path or None."""
    import hunt
    from PIL import Image
    p = os.path.join(d, "p" + hashlib.sha1(url.encode()).hexdigest()[:12] + ".jpg")
    if os.path.exists(p):
        return p
    try:
        req = urllib.request.Request(url, headers={"User-Agent": hunt.UA})
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=40).read())).convert("RGB")
        if min(im.size) < 400:
            return None
        im.thumbnail((2000, 2000))
        os.makedirs(d, exist_ok=True)
        im.save(p, quality=92)
        return p
    except Exception:
        return None


def _ask(model, text, images, think=False, side=1280):
    import vet as V
    return V.ask(model, text, images, think=think, side=side)


# ------------------------------------------------------------------ 1. identity
def identity(card, picked, use, log=print):
    year = card.get("year")
    W, D, H = (round(x * 1000) for x in (card.get("size") or [0, 0, 0])[:3])
    base = {"brand": "", "line": card["product"].split(",")[0], "variant": "", "count": "", "size_text": "",
            "maker": "", "unit": "", "kind": "packaging" if card.get("route") in ("box", "flat") else "object",
            "food": False, "sisters": [], "read_from": ""}
    got = {}
    if use and picked:
        try:
            got = _ask(use, ID_Q.format(product=card["product"], size=f"{W} x {D} x {H}", year=year or "unknown"),
                       [picked], think=False, side=1280) or {}
        except Exception as e:
            log(f"[dossier] could not read the picked photo: {e}")
    idn = dict(base)
    for k in ("brand", "line", "variant", "count", "size_text", "maker", "unit"):
        if _str(got.get(k)):
            idn[k] = _str(got.get(k))
    if got.get("kind") in ("packaging", "object"):
        idn["kind"] = got["kind"]
    idn["food"] = got.get("food") is True
    idn["sisters"] = [_str(s, 60) for s in (got.get("sisters") or []) if _str(s) and
                      _str(s).lower() != idn["variant"].lower()][:6]
    idn["read_from"] = picked if got else "the catalog name only (the picked photo could not be read)"
    idn["year"] = year
    import era as ERA                                     # "90s", "early 2000s" - a range, never one exact year
    idn["years"] = list(ERA.span(year)) if year else [1900, 2100]
    idn["era"] = ERA.words(year)
    idn["name"] = " ".join(x for x in (idn["brand"], idn["line"], idn["variant"]) if x)
    return idn


# ------------------------------------------------------------------ 2. the hunt for every side
def queries(idn, route, need, done=(), side_words=None):
    """Short, varied searches for the sides still needed: this exact item, a sister flavor in a nearby year, this
    line in its decade. Never one that was already run. side_words: how this item's FAMILY names its sides (a
    battery's top is its "positive end", not a "lid") - from the family library."""
    words = dict(WORDS.get(route, WORDS["free"]), **(side_words or {}))
    line = (idn.get("line") or "").lower().replace("’", "'")
    brand = (idn.get("brand") or "").lower().replace("’", "'")
    if brand and brand.split()[0] not in line:                # the brand belongs in every search
        line = f"{brand} {line}".strip()
    line2 = re.sub(r"[-']", " ", line).replace("  ", " ").strip()
    var = (idn.get("variant") or "").lower()
    import era as ERA
    y = idn.get("year")
    ew = ERA.words(y) if y else ""                        # "90s" / "early 2000s": how sellers and collectors say it
    sis = [s.lower() for s in idn.get("sisters") or []] or [""]
    seen = {q.lower().strip() for q in done}
    out, k = [], 0
    for rnd in range(2):                                  # the second round: the other wording of each side
        for f in need:
            w = words.get(f)
            if not w:
                continue
            w0 = w[min(rnd, len(w) - 1)]
            w1 = w[min(1 - rnd, len(w) - 1)] if len(w) > 1 else w0
            s = sis[k % len(sis)]
            k += 1
            for q in (f"{ew} {line2} {var} {w0}", f"{line2} {s} {ew} {w0}" if s else "",
                      f"vintage {line if rnd == 0 else line2} {w1} {ew}"):
                q = re.sub(r"\s+", " ", q).strip()
                q = " ".join(dict.fromkeys(q.split()))       # a word once ("duracell duracell coppertop" -> once)
                if q and q.lower() not in seen:
                    seen.add(q.lower())
                    out.append((f, q))
    return out


def picture_hash(file):
    """A fingerprint of the picture itself (64-bit difference hash): the same photo saved at two sizes from two
    links gets the same fingerprint, so it never counts as two sources."""
    from PIL import Image
    try:
        with Image.open(file) as im:
            a = np.asarray(im.convert("L").resize((9, 8), Image.LANCZOS)).astype(int)
    except Exception:
        return ""
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return "%016x" % int("".join("1" if b else "0" for b in bits), 2)


def same_picture(h1, h2, most=6):
    return bool(h1) and bool(h2) and bin(int(h1, 16) ^ int(h2, 16)).count("1") <= most


def _record(file, url="", page="", title="", query="", source="face hunt"):
    from PIL import Image
    try:
        with Image.open(file) as im:
            size = list(im.size)
    except Exception:
        size = None
    return {"file": file, "url": url, "page": page, "title": title, "query": query, "source": source, "size": size,
            "phash": picture_hash(file), "face": None, "match": None, "product_shown": "", "years": [], "text": [],
            "quality": 0}


def hunt_faces(dos, cid, need, log=print, budget=BUDGET):
    """Google Images searches for the sides still needed (at most `budget` per item), about 5 photos kept from
    each. New photos are added to dos['photos']; nothing found before is dropped."""
    import google_images as G
    d = os.path.join(WORK, "hunt", cid)
    have = {p["file"] for p in dos["photos"]}
    done = [s["q"] for s in dos["searches"]] + dos.get("searched_before", []) + [p.get("query", "") for p in dos["photos"]]
    left = budget - len(dos["searches"])
    side_words = None
    try:                                                      # the family's own words for its sides
        import families
        side_words = families.get(dos.get("family_lib") or "general").get("side_words")
    except Exception:
        pass
    for face, q in queries(dos["identity"], dos["route"], need, done, side_words)[:max(0, left)]:
        try:
            hits = G.search_full(q, most=12, min_side=500, log=log)
        except Exception as e:
            log(f"[dossier] Google Images did not work: {e}")
            dos["searches"].append({"q": q, "n": 0, "at": time.time(), "for": face, "error": str(e)[:200]})
            break
        kept = 0
        for h in hits:
            if kept >= PER_SEARCH:
                break
            f = _download(h["url"], d)
            if not f:
                continue
            kept += 1
            if f in have:                                     # found before: its web page is added if now known
                rec = next((p for p in dos["photos"] if p["file"] == f), None)
                if rec is not None and h.get("page") and not rec.get("page"):
                    rec.update(page=h["page"], title=rec.get("title") or h.get("title", ""))
                continue
            have.add(f)
            dos["photos"].append(_record(f, h["url"], h.get("page", ""), h.get("title", ""), q))
        dos["searches"].append({"q": q, "n": kept, "at": time.time(), "for": face})
        log(f"[dossier] search for the {face}: '{q}' -> {kept} photos")
        save(dos)


# ------------------------------------------------------------------ 3. labels
def quick_look(dos, quick, log=print):
    """The quick first look at every photo not looked at yet (which side, which product, real photo or ad)."""
    idn = dos["identity"]
    q = QUICK_Q.format(name=idn["name"], year=idn.get("era") or idn.get("year") or "")
    todo = [p for p in dos["photos"] if "quick" not in p]
    import vet as V
    n_done = [0]

    def look(p):
        try:
            return _ask(quick, q, [p["file"]], think=False, side=768) or {}
        except Exception as e:
            return {"face": "none", "useful": 0, "note": f"could not look: {e}"}

    def done(i, v):                                       # (several at once when the brain server allows it)
        p = todo[i]
        v = v if isinstance(v, dict) else {"face": "none", "useful": 0, "note": f"could not look: {v}"}
        p["quick"] = {"face": v.get("face") if v.get("face") in NAMES + ["several", "mixed", "none"] else "none",
                      "product_shown": _str(v.get("product_shown")), "same_line": v.get("same_line") is True,
                      "same_item": v.get("same_item") is True, "kind": _str(v.get("kind"), 20) or "other",
                      "era": _str(v.get("era"), 40), "years": parse_years(v.get("era")),
                      "useful": float(v.get("useful") or 0) if str(v.get("useful", "")).replace(".", "").isdigit() else 0}
        n_done[0] += 1
        if n_done[0] % 10 == 0:
            save(dos)
            log(f"[dossier] quick look: {n_done[0]} of {len(todo)} photos")
    V.parallel(look, todo, done)
    save(dos)

def _quick_score(p, era):
    v = p.get("quick") or {}
    s = v.get("useful", 0) + 3 * v.get("same_line", False) + 3 * v.get("same_item", False)
    s += 3 if _overlap(v.get("years"), era) else (-6 if v.get("years") else 0)
    s += {"photo": 2, "flat": 3, "render": -5, "ad": -6}.get(v.get("kind"), 0)
    return s


def _could_show(p, face, route):
    f = (p.get("quick") or {}).get("face")
    if f == face or f in ("several", "mixed") or (f in NAMES and face_name(route, f) == face):
        return True
    return f == "side" and face in ("left", "right")


def careful_looks(dos, use, log=print):
    """The careful look (thinking on) at your pick and at the best few photos for each side."""
    idn = dos["identity"]
    era = idn["years"]
    route = dos["route"]
    picked = dos.get("picked")
    pick = [p for p in dos["photos"] if p["file"] == picked]
    chosen = pick[:]
    for face in FACES[route]:
        cands = [p for p in dos["photos"] if p not in chosen and (p.get("quick") or {}).get("same_line")
                 and (p.get("quick") or {}).get("kind") not in ("render", "ad")
                 and _could_show(p, face, route) and _overlap((p.get("quick") or {}).get("years") or era, era)]
        cands.sort(key=lambda p: -_quick_score(p, era))
        chosen += cands[:LOOK]
    chosen = [p for p in chosen[:MOST_LOOKS] if not p.get("labeled")]
    import vet as V

    def look(p):
        ref = ("Picture 2 is the front of our exact item (the photo picked as true) - compare with it."
               if p["file"] != picked and picked else "Picture 1 IS our exact item (picked as true).")
        imgs = [p["file"]] + ([picked] if p["file"] != picked and picked else [])
        return _ask(use, LABEL_Q.format(name=idn["name"], year=idn.get("era") or idn.get("year") or "", y0=era[0],
                                        y1=era[1], ref=ref, sides_hint=SIDES_HINT.get(route, "")), imgs, think=True,
                    side=1280) or {}

    def done(i, v):                                       # (several at once when the brain server allows it)
        p = chosen[i]
        if isinstance(v, Exception):
            log(f"[dossier] careful look failed for {os.path.basename(p['file'])}: {v}")
            return
        _apply_label(p, v, era, p["file"] == picked)
        if p.get("overlays"):
            log(f"[dossier] {os.path.basename(p['file'])}: laid over the photo (never copied, never a fact): "
                + "; ".join(f"{o['what']} {o['text']!r}" for o in p["overlays"])[:200])
        log(f"[dossier] {os.path.basename(p['file'])}: {p['face']} ({', '.join(f['face'] for f in p['faces'][1:])})"
            f" {p['match']}, {p['product_shown'][:60]}, years {p['years']}, quality {p['quality']}")
        save(dos)
    V.parallel(look, chosen, done)

def _apply_label(p, v, era, is_pick=False):
    faces = []
    for f in v.get("faces") or []:
        if not isinstance(f, dict) or f.get("face") not in NAMES:
            continue
        t = int(f.get("turn") or 0) if str(f.get("turn", 0)).lstrip("-").isdigit() else 0
        faces.append({"face": f["face"], "box": _box(f.get("box")), "straight_on": f.get("straight_on") is True,
                      "edge_on": f.get("edge_on") is True, "turn": t if t in (0, 90, 180, 270) else 0})
    match = v.get("match") if v.get("match") in ("exact", "sister", "near_year", "wrong") else "wrong"
    ys = [int(y) for y in (v.get("years") or []) if str(y).isdigit()][:2]
    ys = sorted(ys * 2)[:1] + sorted(ys)[-1:] if ys else []
    why = ""
    if ys and not _overlap(ys, era):
        match, why = "wrong", f"its years {ys} are outside the era {era}"
    if is_pick:
        match = "exact"                                    # your pick is the item, by definition
    els = []
    for e in v.get("elements") or []:
        if not isinstance(e, dict) or not _str(e.get("what")):
            continue
        els.append({"face": e.get("face") if e.get("face") in NAMES else (faces[0]["face"] if faces else None),
                    "what": _str(e.get("what"), 80), "text": _str(e.get("text"), 400),
                    "kind": e.get("kind") if e.get("kind") in ("barcode", "text", "panel", "graphic") else "text",
                    "item_specific": e.get("item_specific") is True, "box": _box(e.get("box"))})
    try:
        q = max(0.0, min(10.0, float(v.get("quality"))))
    except (TypeError, ValueError):
        q = 0.0
    overlays = [{"what": _str(o.get("what"), 60), "text": _str(o.get("text"), 200), "box": _box(o.get("box"))}
                for o in v.get("overlays") or [] if isinstance(o, dict) and (_str(o.get("what")) or _str(o.get("text")))]
    import facts as FX                                     # words on the photo that can only be a watermark or credit
    overlays += [{"what": "watermark or credit", "text": _str(t, 200), "box": None}
                 for t in (v.get("text") or []) if FX.not_printed(t)]
    p.update(labeled=True, faces=faces, face=faces[0]["face"] if faces else "none", also=[f["face"] for f in faces[1:]],
             match=match, product_shown=_str(v.get("product_shown")), years=ys, years_why=_str(v.get("years_why")),
             text=[_str(t, 200) for t in (v.get("text") or []) if _str(t) and not FX.not_printed(t)][:60], quality=q,
             elements=[e for e in els if not FX.not_printed(e["text"])], overlays=overlays,
             kind=(p.get("quick") or {}).get("kind", "photo"))
    if why:
        p["why"] = why


# ------------------------------------------------------------------ 4. the plan for every side
def face_dims(route, size_m):
    W, D, H = (list(size_m) + [0, 0, 0])[:3]
    if route == "pcb":
        return {"top": (W, H), "bottom": (W, H)}
    if route == "flat":
        return {"front": (W, H), "back": (W, H)}
    if route == "round":
        return {}
    return {"front": (W, H), "back": (W, H), "left": (D, H), "right": (D, H), "top": (W, D), "bottom": (W, D)}


def turn_box(b, turn):
    """A box (fractions) inside a picture that is turned `turn` degrees clockwise."""
    if not b or not turn:
        return b
    x0, y0, x1, y1 = b
    if turn == 180:
        return [1 - x1, 1 - y1, 1 - x0, 1 - y0]
    if turn == 90:
        return [1 - y1, x0, 1 - y0, x1]
    if turn == 270:
        return [y0, 1 - x1, y1, 1 - x0]
    return b


def _shape_ok(p, fe, dims, tol=1.25):
    """A straight-on side's shape (as the careful look boxed it) must be the side's real shape, within 25%."""
    if not dims or not fe.get("box") or not fe.get("straight_on") or not p.get("size"):
        return tol <= 1.25          # a copy is checked again when straightened; a layout needs a straight-on side
    b, (pw, ph) = fe["box"], p["size"]
    w, h = (b[2] - b[0]) * pw, (b[3] - b[1]) * ph
    if fe.get("turn") in (90, 270):
        w, h = h, w
    import math
    return abs(math.log((w / max(h, 1)) / (dims[0] / dims[1]))) < math.log(tol)


KIND_OF = [("upc", r"barcode|upc"), ("nutrition", r"nutrition"), ("ingredients", r"ingredient"),
           ("maker_lines", r"distribut|manufactur|address|consumer|comments|maker"),
           ("legal_lines", r"recycl|copyright|trademark|made in|©"),
           ("net_weight", r"net w|weight|count"), ("name", r"flavor|variety|product name|variant"),
           ("logo", r"logo|brand"), ("picture", r"product picture|photo of|pastry picture|product photo")]


def fact_kind(el):
    """Which of the item's facts a printed element is ('upc', 'nutrition', ... or None for ad copy and the like).
    A picture is a picture: an item-specific graphic (a flavor's fruit, a pastry photo) is this item's own product
    picture, never its name."""
    t = f"{el.get('what', '')} {el.get('kind', '')}".lower()
    if el.get("kind") == "graphic":
        if re.search(r"barcode|upc", t):
            return "upc"
        if re.search(r"logo|brand", t):
            return "logo"
        return "picture" if el.get("item_specific") else None
    for k, rx in KIND_OF:
        if re.search(rx, t):
            return k
    return None


def _ours(e, facts):
    """What this item shows where a sister box shows its own item-specific part: our fact's words, or '' when the
    fact isn't known (that part is then covered and left plain)."""
    k = fact_kind(e)
    f = (facts or {}).get(k) or {}
    if k and f.get("status") in ("verified", "single_source") and f.get("value"):
        v = f["value"]
        return v if isinstance(v, str) else json.dumps(v)[:300]
    return ""


def _els_on(p, fe, primary, route=None):
    import facts as FX
    want = face_name(route, fe["face"])
    return [e for e in p.get("elements", []) if (face_name(route, e.get("face")) == want if e.get("face") else primary)
            and not FX.not_printed(e.get("text"))]


def _end_on(fe):
    """A round item's end seen as a disc: squarely, and about as tall as wide in the photo (a battery seen lying
    down has its end as a thin ellipse at best)."""
    if not fe.get("straight_on"):
        return False
    b = fe.get("box")
    if not b:
        return True
    w, h = b[2] - b[0], b[3] - b[1]
    return w > 0 and h > 0 and 0.6 <= h / w <= 1.7


def _covered(p, fe):
    """Is something laid over this side in this photo (a watermark, a sticker, a hand)? A side that is covered is
    never copied onto the model (it may still show where things go)."""
    fb = fe.get("box")
    for o in p.get("overlays") or []:
        ob = o.get("box")
        if not ob or not fb:
            return True                                    # where it is isn't known: the whole photo counts as covered
        if min(ob[2], fb[2]) > max(ob[0], fb[0]) and min(ob[3], fb[3]) > max(ob[1], fb[1]):
            return True
    return False


def plan(dos):
    """For each side: its own photo > a sister's photo with the item-specific parts swapped > rebuilt from facts."""
    route = dos["route"]
    era = dos["identity"]["years"]
    dims = face_dims(route, dos.get("size_m") or [])
    picked = dos.get("picked")
    labeled = [p for p in dos["photos"] if p.get("labeled") and p.get("match") != "wrong"
               and p.get("kind") not in ("render", "ad")]
    taken = {}                                            # a narrow-side photo is used for one side only
    faces, gaps = {}, []
    for F in FACES[route]:
        cands = []
        for p in labeled:
            seen_here = set()
            for i, fe in enumerate(p.get("faces", [])):
                fn = face_name(route, fe["face"])
                if fn != F and not (fe["face"] == "side" and F in ("left", "right")):
                    continue
                if fe.get("edge_on") or (route == "round" and F in seen_here):
                    continue                                  # (a round item's label: the photo counts once)
                if route == "round" and F in ("top", "bottom") and not _end_on(fe):
                    continue                                  # a round end is only a reference seen END-ON (a disc):
                #                                               a battery lying down shows its label, not its end -
                #                                               the judge compared a bottom disc to a label (2026-10-03)
                seen_here.add(F)
                q = (p.get("quality") or 0) * (1.0 if i == 0 else 0.6) * (0.85 if fe["face"] == "side" else 1.0)
                cands.append((q, p, fe))
        cands.sort(key=lambda c: -c[0])
        free = lambda c: (c[1]["file"], c[2]["face"]) not in taken or c[2]["face"] != "side"
        exact = [c for c in cands if c[1].get("match") == "exact" and c[0] >= 3 and free(c) and not _covered(c[1], c[2])]
        tmpl = [c for c in cands if c[1].get("match") in ("sister", "near_year") and c[0] >= 4 and free(c)
                and _shape_ok(c[1], c[2], dims.get(F)) and not _covered(c[1], c[2])]
        sister_seen = [c for c in cands if c[1].get("match") in ("sister", "near_year")]
        entry = {"source": "none", "photo": None, "page": "", "product_shown": "", "match": None, "swap": [],
                 "must_show": [], "note": "", "alternates": []}
        if F == PRIMARY[route] and picked:
            pp = next((p for p in dos["photos"] if p["file"] == picked), {"file": picked})
            fe = next((f for f in pp.get("faces", []) if face_name(route, f["face"]) == F), {"face": F})
            if route == "round":                              # the whole wrap: every part of the label in the photo
                fe = {"face": F, "turn": fe.get("turn", 0), "straight_on": fe.get("straight_on", False)}
            entry.update(source="exact_photo", photo=picked, page=pp.get("page", ""), match="exact",
                         product_shown=pp.get("product_shown", ""), note="your pick")
            if _covered(pp, fe):
                gaps.append(f"{F}: your pick has something laid over this side ("
                            + ", ".join(f"{o['what']} {o['text']!r}" for o in pp.get("overlays", []))[:120]
                            + ") - it must not end up on the model")
            exact = [(10, pp, fe)] + [c for c in exact if c[1]["file"] != picked]
        if exact:
            q, p, fe = exact[0]
            if entry["source"] != "exact_photo":
                entry.update(source="exact_photo", photo=p["file"], page=p.get("page", ""), match="exact",
                             product_shown=p.get("product_shown", ""),
                             note=("seen at an angle in the photo" if not fe.get("straight_on") else "seen straight-on")
                             + (", as a narrow side of the photo" if fe["face"] == "side" else ""))
            entry["view"] = fe
            entry["alternates"] = [c[1]["file"] for c in exact[1:4]]
            entry["must_show"] = [{"what": e["what"], "text": e["text"], "kind": e["kind"],
                                   "item_specific": e["item_specific"]}
                                  for e in _els_on(p, fe, route == "round" or fe is (p.get("faces") or [None])[0], route)]
        elif tmpl:
            q, p, fe = tmpl[0]
            els = _els_on(p, fe, route == "round" or fe is (p.get("faces") or [None])[0], route)
            entry.update(source="template_photo", photo=p["file"], page=p.get("page", ""), match=p["match"],
                         product_shown=p.get("product_shown", ""), view=fe,
                         swap=[e["what"] for e in els if e["item_specific"]],
                         swap_boxes=[{"what": e["what"], "kind": fact_kind(e) or e["kind"], "box": e["box"]}
                                     for e in els if e["item_specific"] and e.get("box")],
                         must_show=[{"what": e["what"], "text": e["text"], "kind": e["kind"],
                                     "item_specific": e["item_specific"]} for e in els],      # (ours filled in below)
                         note=f"a {p['match'].replace('_', ' ')} box ({p.get('product_shown', '')}, "
                              f"{'-'.join(map(str, p.get('years') or [])) or 'era'})")
            gaps.append(f"{F}: no photo of this exact item's {F}; using a "
                        f"{'sister' if p['match'] == 'sister' else 'nearby-year'} box's {F} "
                        f"({p.get('product_shown', '')}, {'-'.join(map(str, p.get('years') or [])) or 'same era'}) "
                        + (f"with its {', '.join(entry['swap'])} replaced by this item's facts" if entry["swap"] else
                           "as it is (nothing printed on it is specific to its flavor)"))
        else:
            entry["source"] = "rebuilt"
            near = [c for c in sister_seen if _shape_ok(c[1], c[2], dims.get(F), tol=1.5)]
            if near:                                          # the closest sister's layout (a side of about the
                q, p, fe = near[0]                             # same shape, even if not close enough to copy)
                entry["layout_from"] = p["file"]
                entry["layout"] = [{"kind": fact_kind(e), "box": turn_box(_rel(e["box"], fe.get("box")),
                                                                          fe.get("turn") or 0), "what": e["what"]}
                                   for e in _els_on(p, fe, route == "round" or fe is (p.get("faces") or [None])[0], route)
                                   if fact_kind(e) and e.get("box")]
                entry["layout"] = [x for x in entry["layout"] if x["box"]] or None
            entry["note"] = "rebuilt from facts only" + (" in a sister box's layout" if entry.get("layout") else "")
            gaps.append(f"{F}: no photo of this side of this item or of a sister box from {era[0]}-{era[1]} was "
                        "found - rebuilt from facts only")
        if entry.get("view") and entry["view"].get("face") == "side":
            taken[(entry["photo"], "side")] = F
        faces[F] = entry
    # the narrow sides: a rebuilt side gets what its twin doesn't show (nutrition on one, the maker on the other)
    for a, b in (("left", "right"), ("right", "left")):
        if a in faces and faces[a]["source"] == "rebuilt" and b in faces and faces[b]["source"] != "rebuilt":
            twin = {fact_kind(e) for e in faces[b].get("must_show", [])}
            faces[a]["want"] = (["logo", "maker_lines", "legal_lines"] if "nutrition" in twin
                                else ["nutrition", "ingredients", "maker_lines"] if dos["identity"].get("food")
                                else ["logo", "name", "net_weight"])
    return faces, gaps


def _rel(b, fb):
    """An element's box inside its side's box (both fractions of the photo) -> fractions of the side."""
    if not b or not fb:
        return b
    w, h = fb[2] - fb[0], fb[3] - fb[1]
    if w <= 0 or h <= 0:
        return None
    r = [(b[0] - fb[0]) / w, (b[1] - fb[1]) / h, (b[2] - fb[0]) / w, (b[3] - fb[1]) / h]
    r = [min(max(v, 0.0), 1.0) for v in r]
    return r if r[2] - r[0] > 0.02 and r[3] - r[1] > 0.02 else None


def _must_show_rebuilt(entry, face, route, facts, food, kind="packaging", kit=None):
    """What a side rebuilt from facts must show. Only PACKAGING carries printed panels on its unseen sides; a battery
    end, a can bottom, a circuit card's solder side or the back of a gadget carries nothing it can be held to.
    What belongs on the side comes from the kit (what this kind of thing normally carries there, kits.elements),
    unless a real box of the era showed its layout."""
    if kind != "packaging" or route not in ("box", "flat"):
        return []
    import kits
    if not entry.get("want") and not entry.get("layout"):
        entry["want"] = kits.elements(kits.get(kit or ""), face, food)      # eraprint draws the same list
    want = entry.get("want") or [e["kind"] for e in entry.get("layout") or []]
    known = lambda k: (facts.get(k) or {}).get("status") in ("verified", "single_source") and (facts.get(k) or {}).get("value")
    if not any(known(k) for k in want if k not in ("logo", "name", "picture")):
        want = ["logo", "name"] + [k for k in want if k not in ("logo", "name")]     # as eraprint draws it
    out = []
    for k in want:
        f = facts.get(k) or {}
        if k in ("logo", "picture"):
            out.append({"what": f"the real {k} from the front photo", "text": "", "kind": "graphic",
                        "item_specific": k == "picture"})
        elif k == "name":
            out.append({"what": "product name", "text": "", "kind": "text", "item_specific": True})
        elif f.get("status") in ("verified", "single_source") and f.get("value"):
            v = f["value"]
            txt = ("Nutrition Facts" if k == "nutrition" else v if isinstance(v, str) else
                   " ".join(str(x) for x in v) if isinstance(v, list) else "")     # the words as printed
            out.append({"what": k.replace("_", " "), "text": txt,
                        "kind": "barcode" if k == "upc" else "panel" if k == "nutrition" else "text",
                        "item_specific": k in ("upc", "nutrition", "ingredients", "net_weight", "count")})
    return out


def _sides_from_facts(dos):
    """What each side must show, once the facts are known: a rebuilt side its facts; a sister's side our values in
    place of its own item-specific parts."""
    route = dos["route"]
    food = (dos.get("identity") or {}).get("food")
    for F, e in dos["faces"].items():
        if e["source"] == "rebuilt":
            e["must_show"] = _must_show_rebuilt(e, F, route, dos.get("facts") or {}, food,
                                                (dos.get("identity") or {}).get("kind", "packaging"),
                                                dos.get("family_lib"))
            got = [m["what"] for m in e["must_show"]]
            e["note"] += f" ({', '.join(got) or 'nothing known to print'})"
        elif e["source"] == "template_photo":                # a sister's side: its own parts replaced by ours
            for m in e["must_show"]:
                if m["item_specific"]:
                    m["sister_text"], m["text"] = m["text"], _ours(m, dos.get("facts") or {})


def replan(dos, log=print):
    """A dossier made under older rules, brought up to the current ones from the looks already taken - no new
    looks, nothing downloaded: words that can only be a watermark or credit come out of every look and fact, and
    the plan for every side is worked out again (a round item's wrapped side is its label)."""
    import era as ERA
    import facts as FX
    idn = dos.setdefault("identity", {})
    y = idn.get("year") or (dos.get("inputs") or {}).get("year")
    if y:                                                 # the era as a range people use ("90s", "early 2000s")
        idn["years"], idn["era"] = list(ERA.span(y)), ERA.words(y)
        for p in dos.get("photos", []):                   # a photo thrown out only for being outside the old,
            if str(p.get("why", "")).startswith("its years") and _overlap(p.get("years"), idn["years"]):   # narrower era
                p["match"] = "near_year"
                p["why"] = "inside the era once it became a range"
    for p in dos.get("photos", []):
        if not p.get("labeled"):
            continue
        bad = [t for t in p.get("text", []) if FX.not_printed(t)]
        bad += [e.get("text") for e in p.get("elements", []) if FX.not_printed(e.get("text"))]
        if bad:
            have = {o.get("text") for o in p.get("overlays", [])}
            p.setdefault("overlays", []).extend({"what": "watermark or credit", "text": t, "box": None}
                                                for t in dict.fromkeys(bad) if t not in have)
            p["text"] = [t for t in p.get("text", []) if not FX.not_printed(t)]
            p["elements"] = [e for e in p.get("elements", []) if not FX.not_printed(e.get("text"))]
    FX.recheck_lines(dos, log)
    before = {F: (e.get("source"), len(e.get("must_show") or [])) for F, e in (dos.get("faces") or {}).items()}
    dos["faces"], face_gaps = plan(dos)
    _sides_from_facts(dos)
    sides = set(NAMES) | set(FACES.get(dos["route"], []))
    dos["gaps"] = face_gaps + [g for g in dos.get("gaps", []) if g.split(":")[0].strip() not in sides]
    dos["version"] = VERSION
    save(dos)
    after = {F: (e.get("source"), len(e.get("must_show") or [])) for F, e in dos["faces"].items()}
    log(f"[dossier] {dos.get('cid', '')}: brought up to the newest rules (no new looks): "
        + "; ".join(f"{F} {after[F][0].replace('_', ' ')}, {after[F][1]} things it must show"
                    + (f" (was {before[F][1]})" if F in before and before[F][1] != after[F][1] else "")
                    for F in after))
    return dos


# ------------------------------------------------------------------ the whole dossier
def build(cid, card, picked=None, log=print, use=None, redo=False, quick=None, web=True):
    """The item's dossier (see the top of this file). Reused when it was finished for the same inputs (product,
    size, year, route, your pick); a half-finished one is carried on where it stopped. redo=True (your Redo) sets
    the old one aside in dossier/old/ and looks at every photo afresh - the photos found before are kept."""
    import vet as V
    pick = picked.get("file") if isinstance(picked, dict) else picked
    sig = _inputs(card, pick)
    old = load(cid)
    same = bool(old) and _same_inputs(old.get("inputs"), sig)
    if old and not redo and same and old.get("done"):
        log(f"[dossier] {cid}: known already ({len(old.get('photos', []))} photos, made "
            f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(old.get('made_at', 0)))}) - reused")
        if int(old.get("version") or 1) < VERSION:
            old["inputs"] = sig
            replan(old, log)                                  # newer rules: from the looks already taken, in seconds
        return old
    resume = bool(old) and not redo and same
    if old and not resume:
        _set_aside(cid, "you asked for a Redo" if redo else "its inputs changed (your pick, the product or its size)")
    use = use if use is not None else V.model()
    quick = quick if quick is not None else (V.quick_model() or use)
    route = route_of(card)
    dos = old if resume else {
        "cid": cid, "version": VERSION, "made_at": time.time(), "inputs": sig, "route": route,
        "family": card.get("family", ""), "family_lib": (card.get("family_lib") or {}).get("family", ""),
        "picked": pick, "identity": {}, "size_m": card.get("size"), "faces": {},
        "facts": {}, "photos": [], "searches": [], "gaps": [], "done": False}
    if not resume and old:                                    # never lose finds: every photo found before comes along
        keep = ("file", "url", "page", "title", "query", "source", "size", "phash")
        dos["photos"] = [{**{k: p.get(k, "") for k in keep}, "face": None, "match": None, "product_shown": "",
                          "years": [], "text": [], "quality": 0} for p in old.get("photos", []) if os.path.exists(p["file"])]
        dos["searches"] = []                                    # this build's own budget; never the same words twice
        dos["searched_before"] = list(dict.fromkeys(old.get("searched_before", []) + [x["q"] for x in old.get("searches", [])]))
    dos["gaps"] = []
    save(dos)
    log(f"[dossier] {cid}: getting to know the item before building it ({route}: {', '.join(FACES[route])})")

    # 1. identity
    if not dos["identity"].get("name"):
        dos["identity"] = identity(card, pick, use, log)
        log(f"[dossier] identity: {dos['identity']['name']}; count {dos['identity']['count'] or '?'}; size "
            f"{dos['identity']['size_text'] or '?'}; food {dos['identity']['food']}; sisters (search words only): "
            f"{', '.join(dos['identity']['sisters'])}")
        save(dos)
    # every photo found so far: your pick, the first hunt, earlier dossiers
    have = {p["file"] for p in dos["photos"]}
    fj = os.path.join(WORK, "hunt", cid, "found.json")
    try:
        found = json.load(open(fj))
    except Exception:
        found = []
    if pick and pick not in have:
        dos["photos"].insert(0, _record(pick, source="your pick"))
        have.add(pick)
    for f in found:
        if f.get("file") and f["file"] not in have and os.path.exists(f["file"]):
            t = f.get("title", "")
            dos["photos"].append(_record(f["file"], f.get("url", ""), f.get("page", ""),
                                         "" if t.startswith("Google Images:") else t,
                                         t.replace("Google Images:", "").strip() if t.startswith("Google Images:") else "",
                                         "first hunt"))
            have.add(f["file"])
    save(dos)

    # 2-3. a quick look at everything; then hunt the sides that still have no likely photo; quick look at those
    quick_look(dos, quick, log)
    era = dos["identity"]["years"]
    order = [f for f in FACES[route] if f != PRIMARY[route]]

    def likely(face):
        return [p for p in dos["photos"] if _could_show(p, face, route) and (p.get("quick") or {}).get("same_item")
                and _overlap((p.get("quick") or {}).get("years") or era, era)
                and (p.get("quick") or {}).get("kind") not in ("render", "ad")]
    need = [f for f in order if not likely(f)] + [f for f in order if likely(f)]
    if web:
        hunt_faces(dos, cid, need, log)
        quick_look(dos, quick, log)
    careful_looks(dos, use, log)

    # 4. the plan, 5. the facts
    import facts as FX
    dos["faces"], face_gaps = plan(dos)
    dos["facts"] = FX.gather(dos, log, use, web=web)
    _sides_from_facts(dos)
    dos["gaps"] = face_gaps + dos["gaps"]
    dos["version"] = VERSION
    dos["made_at"] = time.time()
    dos["done"] = bool(use)                                   # made without your AI: tried again next time
    save(dos)
    log(f"[dossier] {cid}: " + "; ".join(f"{F} {e['source'].replace('_', ' ')}" for F, e in dos["faces"].items()))
    for g in dos["gaps"]:
        log(f"[dossier] gap: {g}")
    return dos


def ensure(cid, card, picked, use=None, redo=False, log=print):
    """build() for the asset maker: never stops a build - if the dossier can't be made, an empty one (every side
    rebuilt plainly, every fact missing) is returned and the reason logged."""
    try:
        return build(cid, card, picked, log=log, use=use, redo=redo)
    except Exception as e:
        import traceback
        traceback.print_exc()
        log(f"[dossier] {cid}: could not be made ({e}) - built without it")
        route = route_of(card)
        return {"cid": cid, "version": VERSION, "route": route, "identity": {}, "faces": {}, "facts": {},
                "photos": [], "searches": [], "gaps": [f"no dossier: {e}"], "size_m": card.get("size"),
                "picked": picked.get("file") if isinstance(picked, dict) else picked}


def face_photos(dos, sources=("exact_photo",), with_alternates=True):
    """The photos the plan uses, as the box builder takes them: [{"file", "vet": {"view": side}, "plan": side}]
    (your pick first). Masks are added by the caller (the drawing room makes them)."""
    out, seen = [], set()
    for F, e in (dos.get("faces") or {}).items():
        if e.get("source") not in sources:
            continue
        for f in [e.get("photo")] + (e.get("alternates") or [] if with_alternates else []):
            if f and f not in seen and os.path.exists(f):
                seen.add(f)
                out.append({"file": f, "vet": {"view": F}, "plan": F, "source": e["source"]})
    pk = dos.get("picked")
    out.sort(key=lambda x: x["file"] != pk)
    return out


def with_masks(photos, log=print):
    """Each photo's cut-out (white = the object), made once by the drawing room and kept next to the photo. A photo
    whose cut-out fails is still handed on: a flat side the careful look boxed needs no cut-out."""
    try:
        import turnaround as T
    except Exception as e:
        log(f"[texture] cut-outs not available here ({e})")
        T = None
    for p in photos:
        if p.get("mask") and os.path.exists(p["mask"]):
            continue
        made = p["file"].rsplit(".", 1)[0] + "_mask.png"
        if os.path.exists(made):
            p["mask"] = made
            continue
        if T is None:
            continue
        try:
            p["mask"] = T.photo_mask(p["file"], timeout=180)
        except Exception as e:
            log(f"[texture] {os.path.basename(p['file'])}: cut-out failed ({e}) - used without it")
    return photos


if __name__ == "__main__":
    import cards
    c = cards.make(sys.argv[1])
    picks = json.load(open(os.path.expanduser("~/.hellbox/picks.json"))).get(sys.argv[1], {})
    cf = os.path.join(WORK, "library", sys.argv[1], "candidates.json")
    pk = json.load(open(cf))["files"][int(picks.get("pick", "1")) - 1]["file"] if os.path.exists(cf) else None
    d = build(sys.argv[1], c, pk, redo="--redo" in sys.argv)
    print(json.dumps({F: {k: e.get(k) for k in ("source", "photo", "match", "swap", "note")} for F, e in d["faces"].items()},
                     indent=1))
    print("\n".join(d["gaps"]))
