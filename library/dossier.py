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
VERSION = 10                 # 10: a round label is looked at until it has sources to go AROUND (not just one)
#                               9: a plan rule changed (one copy outranks straight-on): kept dossiers planned again
#                              8: the label's pixel source is the best clean photo, not the pick by right; the look counts the items
#                              7: 2: a round item's wrapped side is its label; watermarks are never facts or copied sides
#                              3: the era is a range people use ("90s", "early 2000s"), never year +/- 3
#                              4: a round end's reference photo must show that end end-on (a disc)
#                              5: a round item's ends are told apart by the kit (the + button end is the top): the
#                                 careful looks that named an end are taken again
#                              6: a round label takes a sister pack's cell with the same artwork as a source: the
#                                 careful looks are asked "same_artwork" (taken again for sister photos of round items)
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
{{"brand": "the brand as printed (the maker's name on it)",
 "line": "the product line as printed (the product's own name)",
 "variant": "the flavor / version / model as printed",
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
 "product_shown": "brand, line, flavor/version and count you can read, in that order",
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
 "same_artwork": true when the item's own printed artwork in picture 1 is the SAME as ours (the same label or
   package art, words and colors) even though the count or pack differs - e.g. one cell of a 4-pack of the same
   batteries carries the very same label as our single cell; false when its artwork differs,
 "product_shown": "brand, line, flavor/version and count you can read",
 "years": [earliest, latest] year the package could be from (copyright dates, design, nutrition label format),
 "years_why": "what tells you the years",
 "text": ["every line of words you can read, exactly as printed"],
 "quality": 0-10 (10 = straight-on, filling the frame, sharp, evenly lit, nothing covering it),
 "items": how many separate copies of the product are in picture 1 (1 for a single one; 3 for three cells lying
   across each other; a pack of 4 counts as 4),
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
    planned = queries(dos["identity"], dos["route"], need, done, side_words)[:max(0, left)]
    wanted = list(dict.fromkeys(f for f, _ in planned))       # the sides this round meant to search
    searched = set()                                          # the sides that got at least one search this round
    ran = 0
    for face, q in planned:
        try:
            hits = G.search_full(q, most=12, min_side=500, log=log)
        except Exception as e:                            # not a search: nothing recorded
            # A block (a captcha, Google down) is NOT a hunt with no results. But it is not a void hunt either when
            # every side this round meant to search was searched at least once before the block (2026-10-04: the
            # Duracell ran 11 of 12 searches, 5+ for each end, then hit a captcha on the 12th - and the whole hunt
            # was thrown away, the item stopped, every retry stopped the same way). The searches that ran count;
            # the ones that did not are left for a later round. The hunt is incomplete only when a needed side
            # was never searched at all.
            never = [f for f in wanted if f not in searched]
            if never:
                log(f"[dossier] Google Images did not work: {e} - this search is not counted; the hunt is run again "
                    f"later (no search ran yet for: {', '.join(never)})")
                dos["hunt_incomplete"] = str(e)[:200]
            else:
                log(f"[dossier] Google Images stopped answering after {ran} searches: {e} - "
                    f"every side this round meant to search was searched; what was found counts, the rest is tried "
                    f"another time")
                dos.pop("hunt_incomplete", None)
            break
        dos.pop("hunt_incomplete", None)
        searched.add(face)
        ran += 1
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


SAME_DESIGN_Q = ("Picture 1 is a seller's photo; picture 2 is our item. Leave out date codes, best-by dates and lot "
                 "numbers - they change from batch to batch. Is the PRINTED DESIGN on the item in picture 1 the same as "
                 "on picture 2: the same logo, panels, meters, colors, bands and wording in the same places? The same "
                 "size of item too. Answer ONLY JSON: {\"same_design\": true or false, \"why\": \"short\"}")


def listing_query(idn):
    """What a person types into eBay for this item: its name without the era words ("circa 1998") or notes."""
    n = str(idn.get("name") or ((idn.get("brand") or "") + " " + (idn.get("line") or ""))).strip()
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r",?\s*(circa|c\.|from|made in)\b.*$", "", n, flags=re.I)
    n = re.sub(r"\b[\d.,]+\s*(volts?|v|mah|mm|in|oz|g|ct|count|pack)?\b", " ", n, flags=re.I)   # ratings and counts
    n = re.sub(r"\b(volts?)\b", " ", n, flags=re.I)  # vary per listing: never search words (07 12:30 "1.5 Volts")
    return re.sub(r"\s+", " ", n).strip(" ,")


def hunt_listings(dos, cid, use, log=print, most=10, good_enough=6):
    """eBay listings (Cody, 2026-10-07 00:32): each listing is ONE copy of the item photographed from every side.
    The careful look checks the listing's MAIN photo only; when it is this item (exact) or the same artwork, every
    photo of that listing is a source for the label - same copy, other angles (the stitch's size gate and feature
    matching still drop any photo that is not the item). Stops after `good_enough` good listings or 3 wrong ones
    in a row. Once per LISTINGS version. -> how many photos came in from good listings."""
    if dos.get("listings_hunted") == LISTINGS:
        return 0
    dos["listings_hunted"] = LISTINGS
    import google_images as G
    # two searches - the catalog's name for it and the name printed on it - and the listings ranked by how many of
    # those names' words their titles share, whole words only (2026-10-07 05:40: "DURACELL POWERCHECK" alone gave
    # AAA, C and D listings first; the AA ones came last and were never reached)
    cat_name = listing_query({"name": (dos.get("inputs") or {}).get("product") or ""})
    idn_name = listing_query(dos.get("identity") or {})
    yr0 = (dos.get("identity") or {}).get("year") or (dos.get("inputs") or {}).get("year")
    try:
        old_item = int(yr0) <= time.localtime().tm_year - 15
    except (TypeError, ValueError):
        old_item = False
    qs = [q for q in dict.fromkeys([("vintage " + idn_name) if old_item and idn_name else "", idn_name, cat_name]) if q]
    # the name PRINTED on this copy tells its version apart (POWERCHECK = the 90s cell); the catalog's name also fits
    # every modern pack (2026-10-07 06:15: the top 8 were all modern Coppertop packs). An old item also earns its
    # era words ("vintage", its decade).
    tok = lambda x: set(re.findall(r"[a-z0-9]+", str(x).lower()))
    printed, catalog = tok(idn_name), tok(cat_name)
    yr = (dos.get("identity") or {}).get("year") or (dos.get("inputs") or {}).get("year")
    era_w = set()
    try:
        if int(yr) <= time.localtime().tm_year - 15:
            era_w = {"vintage", "old", "nos", f"{str(int(yr))[2]}0s", f"{str(int(yr))[:3]}0s", str(int(yr))}
    except (TypeError, ValueError):
        pass
    rows, seen_ids = [], set()
    try:
        for q in qs:
            for L in G.search_listings(q, log=log):
                if L["id"] not in seen_ids:
                    seen_ids.add(L["id"])
                    rows.append(L)
    except Exception as e:
        log(f"[dossier] eBay could not be searched: {str(e)[:120]}")
        save(dos)
        return 0
    # each word weighted by how RARE it is among the results' titles - tf-idf's idf, log(N / titles with the word)
    # (Sparck Jones 1972; the standard text-retrieval weight): "powercheck" is rare and says which version, "volts",
    # "alkaline", "batteries" are on every listing and say nothing (2026-10-07 11:50: the printed name grew "1.5
    # Volts" and an Osco and an Energizer listing came first). A listing must carry the brand.
    import math as _m
    N = max(1, len(rows))
    df = {}
    for L in rows:
        for w in tok(L["title"]):
            df[w] = df.get(w, 0) + 1
    idf = lambda w: _m.log((N + 1) / (df.get(w, 0) + 1))
    brand = tok((dos.get("identity") or {}).get("brand") or "")
    want = printed | catalog

    def score(L):
        t = tok(L["title"])
        if brand and t and not (brand & t):
            return -1.0                                   # another brand
        return round(sum(idf(w) for w in want & t) + 2 * len(era_w & t), 2)
    rows = sorted((L for L in rows if score(L) >= 0), key=lambda L: -score(L))   # another brand: never opened
    log("[dossier] eBay listings, best match first: " + " | ".join(f"{score(L)} {L['title'][:50]}" for L in rows[:most]))
    q = " / ".join(qs)
    found = []
    for L in rows[:most]:
        try:
            ph = G.listing(L["page"], log)
        except Exception as e:
            log(f"[dossier] eBay listing {L['page']} could not be opened: {str(e)[:80]}")
            continue
        if ph:
            found.append(dict(L, photos=ph))
            log(f"[ebay] {L['page']}: {len(ph)} photos ({L['title'][:70]})")
    d = os.path.join(WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    have = {p["file"] for p in dos["photos"]}
    good, wrong_run, new = 0, 0, 0
    for L in found:
        files = [f for f in (_download(u, d) for u in L["photos"]) if f]
        if not files:
            continue
        recs = []
        for f, u in zip(files, L["photos"]):
            rec = next((p for p in dos["photos"] if p["file"] == f), None)
            if rec is None:
                rec = _record(f, u, L["page"], L["title"], "ebay: " + q, source="ebay listing")
                dos["photos"].append(rec)
                have.add(f)
            rec["listing"] = L["page"]
            recs.append(rec)
        main = recs[0]
        try:                                              # EVERY photo of the listing is looked at (Cody, 2026-10-07
            import vet as V                               # 00:51: "it should check all images in a listing") - the
            quick_look(dos, V.quick_model() or use, log)  # quick look on each, the careful look on the main photo
        except Exception as e:
            log(f"[dossier] the quick look at the listing's photos failed: {str(e)[:100]}")
        if not main.get("labeled") and use:
            careful_looks(dos, use, log, only=[main])
        ok = main.get("labeled") and (main.get("match") == "exact" or main.get("same_artwork"))
        # turned down ONLY for its years (a printed "best if installed by" date reads years after it was made -
        # 2026-10-07 12:30: Cody's own 6-cell PowerCheck listing, the same artwork on every side, was "wrong" for
        # MAR 2003): one focused question - the same printed design, date codes aside? - against the pick
        if not ok and use and str(main.get("why") or "").startswith("its years") and dos.get("picked"):
            ys, era = main.get("years") or [], (dos.get("identity") or {}).get("years") or []
            near = ys and era and ys[0] <= era[1] + 6 and ys[-1] >= era[0] - 6
            if near:
                v = _ask(use, SAME_DESIGN_Q, [main["file"], dos["picked"]], think=True) or {}
                if v.get("same_design") is True:
                    main.update(match="sister", same_artwork=True, why=f"the same printed design (date codes aside): {_str(v.get('why'), 120)}")
                    ok = True
        log(f"[dossier] eBay listing {L['page']}: {len(recs)} photos - main photo {main.get('match')}"
            + (" (same artwork)" if main.get("same_artwork") else ""))
        if not ok:
            wrong_run += 1
            save(dos)
            # every listing of the short ranked list is looked at (2026-10-07 09:40: a stop after three wrong in a
            # row - a pin, a pin, a 9V - came before the '6 AA' listing Cody found)
            continue
        wrong_run, good = 0, good + 1
        for r in recs[1:]:
            if r.get("labeled"):
                continue
            q_ = r.get("quick") or {}
            if q_ and (not q_.get("same_item") or q_.get("kind") in ("render", "ad")):
                r["not_source"] = "the quick look: " + (q_.get("product_shown") or q_.get("kind") or "not this item")[:80]
                continue
            r.update(labeled=True, match=main.get("match"), same_artwork=main.get("same_artwork"),
                     years=main.get("years") or [], product_shown=main.get("product_shown", ""),
                     quality=main.get("quality") or 0, items=None, overlays=[], from_listing=main["file"],
                     face="label", faces=[{"face": "label", "box": None}])
            new += 1
        save(dos)
        if good >= good_enough:
            break
    log(f"[dossier] eBay: {good} listing(s) of this item, {new} more photos of it from every side")
    if new:
        dos["faces"], _ = plan(dos)
        F = PRIMARY.get(dos.get("route"), "front")
        dos["faces"].setdefault(F, {})["alternates"] = [p["file"] for p in _round_sources(dos)
                                                        if p["file"] != dos["faces"].get(F, {}).get("photo")]
    save(dos)
    return new


def hunt_due(dos):
    """A round label short of real pixels still has a hunt to run: eBay's listings, or the image searches."""
    return dos.get("listings_hunted") != LISTINGS or dos.get("around_hunted") != VERSION


def hunt_around(dos, cid, log=print, use=None, quick=None, coverage=0.0):
    """A round label whose real pixels cover less than most of the way around after the stitch (2026-10-06 10:21:
    every same-item photo looked at, 4 clean exact ones, all of the same side - 32% real): one extra round of
    searches aimed at the OTHER side of the label, then quick and careful looks at what comes in. Once per dossier
    version (dos['around_hunted']). -> how many new photos came in."""
    import vet as V
    got = hunt_listings(dos, cid, use, log) if use else 0  # every angle of one copy first (eBay)
    if got or dos.get("around_hunted") == VERSION:
        return got
    dos["around_hunted"] = VERSION
    idn = dos.get("identity") or {}
    line = ((idn.get("brand") or "") + " " + (idn.get("line") or "")).strip().lower()
    y = idn.get("year")
    era = f" {y}" if y else ""
    qs = [f"{line}{era} back of label", f"{line}{era} label flat unrolled", f"{line}{era} wrapper", f"{line} label other side",
          f"{line}{era} rolling on table", f"{line}{era} lot of several", f"{line} vintage lot photo"]
    done = {s["q"] for s in dos.get("searches", [])} | set(dos.get("searched_before", []))
    qs = [q for q in qs if q not in done][:6]
    import google_images as G
    d = os.path.join(WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    have = {p["file"] for p in dos["photos"]}
    new = 0
    log(f"[dossier] the label's real pixels cover {coverage:.0%} of the way around - hunting for its other side ({len(qs)} searches)")
    for q in qs:
        try:
            hits = G.search_full(q, most=12, min_side=500, log=log)
        except Exception as e:
            log(f"[dossier] the hunt for the other side stopped: {str(e)[:120]}")
            break
        kept = 0
        for h in hits:
            if kept >= PER_SEARCH:
                break
            f = _download(h["url"], d)
            if not f or f in have:
                continue
            have.add(f)
            kept += 1
            new += 1
            dos["photos"].append(_record(f, h["url"], h.get("page", ""), h.get("title", ""), q))
        dos["searches"].append({"q": q, "n": kept, "at": time.time(), "for": "label (other side)"})
        log(f"[dossier] search for the label's other side: '{q}' -> {kept} new photos")
        save(dos)
    if new:
        quick_look(dos, quick or V.quick_model() or use or V.model(), log)
        cands = [p for p in dos["photos"] if not p.get("labeled") and (p.get("quick") or {}).get("same_item")
                 and (p.get("quick") or {}).get("kind") not in ("render", "ad")]
        cands.sort(key=lambda p: -_quick_score(p, idn.get("years") or []))
        if cands and use:                                 # one at a time, and stop when the hunt runs dry
            have_n, dry, looked = len(_round_sources(dos)), 0, 0  # (2026-10-06 20:57: 20 careful looks queued,
            for p in cands[:HUNT_LOOKS]:                          # ~5 min each, most a 9V or a D pack - frozen
                careful_looks(dos, use, log, only=[p])            # for Cody's eyes)
                looked += 1
                n = len(_round_sources(dos))
                dry = 0 if n > have_n else dry + 1
                have_n = n
                save(dos)
                if dry >= HUNT_DRY:
                    log(f"[dossier] the hunt for the other side ran dry: {dry} looks in a row added nothing - on to drawing")
                    break
        dos["faces"], _ = plan(dos)
        F = PRIMARY.get(dos.get("route"), "front")
        dos["faces"].setdefault(F, {})["alternates"] = [p["file"] for p in _round_sources(dos)
                                                        if p["file"] != dos["faces"].get(F, {}).get("photo")]
    save(dos)
    return new


# ------------------------------------------------------------------ 3. labels
def quick_look(dos, quick, log=print):
    """The quick first look at every photo not looked at yet (which side, which product, real photo or ad)."""
    idn = dos["identity"]
    q = QUICK_Q.format(name=idn["name"], year=idn.get("era") or idn.get("year") or "")
    todo = [p for p in dos["photos"] if "quick" not in p]
    import vet as V
    n_done = [0]

    def look(p):
        return _ask(quick, q, [p["file"]], think=False, side=768) or {}

    failed = [0]

    def done(i, v):                                       # (several at once when the brain server allows it)
        p = todo[i]
        if not isinstance(v, dict) or not v:              # a failed look is NOT a look: nothing stored, asked again
            failed[0] += 1                                # next time (2026-10-04: it was stored as "none, useless")
            return
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
    if failed[0]:
        log(f"[dossier] quick look: {failed[0]} of {len(todo)} looks failed (the brain did not answer) - not stored, "
            "looked at again next time")
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


def careful_looks(dos, use, log=print, only=None):
    """The careful look (thinking on) at your pick and at the best few photos for each side (only=[photos]: at
    exactly these - more candidates for one side)."""
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
    chosen = [p for p in chosen[:MOST_LOOKS] if not p.get("labeled")] if only is None else [p for p in only if not p.get("labeled")]
    if not chosen:
        return
    import vet as V
    hint = SIDES_HINT.get(route, "")
    if route == "round":                                  # which end is which, from the kit (a battery lying down:
        try:                                              # the copper + end was called "bottom", 2026-10-04)
            import kits
            kit = kits.get(dos.get("family_lib") or "")
            ends = [f"its {z} end is {'; '.join(kits.typical(kit, z))}" for z in ("top", "bottom") if kits.typical(kit, z)]
            if ends:
                hint += " Tell the ends apart by what they are: " + "; ".join(ends) + "."
        except Exception:
            pass

    def look(p):
        ref = ("Picture 2 is the front of our exact item (the photo picked as true) - compare with it."
               if p["file"] != picked and picked else
               "Picture 1 is the photo that was PICKED as our item - it has not been checked: judge it like any "
               "other photo and say honestly whether it is exactly this item (audit 2026-10-04).")
        imgs = [p["file"]] + ([picked] if p["file"] != picked and picked else [])
        return _ask(use, LABEL_Q.format(name=idn["name"], year=idn.get("era") or idn.get("year") or "", y0=era[0],
                                        y1=era[1], ref=ref, sides_hint=hint), imgs, think=True,
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
    look_match, look_why = match, why
    if is_pick:
        match = "exact"                                    # the pick is built as the item (run.pick_gate reads what
        why = ""                                           # the look itself said: look_match; an auto-pick that the
        #                                                    look calls not exact is un-picked, 2026-10-04)
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
    try:
        items = max(1, int(v.get("items")))
    except (TypeError, ValueError):
        items = None                                       # (an older look: not asked)
    overlays = [{"what": _str(o.get("what"), 60), "text": _str(o.get("text"), 200), "box": _box(o.get("box"))}
                for o in v.get("overlays") or [] if isinstance(o, dict) and (_str(o.get("what")) or _str(o.get("text")))]
    import facts as FX                                     # words on the photo that can only be a watermark or credit
    overlays += [{"what": "watermark or credit", "text": _str(t, 200), "box": None}
                 for t in (v.get("text") or []) if FX.not_printed(t)]
    p.update(labeled=True, faces=faces, face=faces[0]["face"] if faces else "none", also=[f["face"] for f in faces[1:]],
             match=match, same_artwork=(v.get("same_artwork") is True) or match == "exact",
             product_shown=_str(v.get("product_shown")), years=ys, years_why=_str(v.get("years_why")),
             text=[_str(t, 200) for t in (v.get("text") or []) if _str(t) and not FX.not_printed(t)][:60], quality=q,
             elements=[e for e in els if not FX.not_printed(e["text"])], overlays=overlays, items=items,
             kind=(p.get("quick") or {}).get("kind", "photo"))
    if is_pick:
        p["look_match"], p["look_why"] = look_match, look_why
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


MORE_FOR_PRIMARY = 6         # extra careful looks when the main side's source is poor
ROUND_SOURCES = 12           # credible source photos a round label wants before the looks stop
LISTINGS = 8                 # the eBay listing hunt's version (once per item per version)
HUNT_LOOKS = 8               # the most careful looks at the hunt's new photos
HUNT_DRY = 3                 # stop after this many in a row add no source
ROUND_LOOKS = 40             # the most extra careful looks a round item gets for that


def _round_sources(dos):
    """EVERY credible photo of this item lends a round label real pixels (Cody, 2026-10-06 10:37: "there is no
    front and back on a round object... reference all credible sources for a complete image"): an exact match or
    the same artwork (a nearby year's copy differs in its date code only - the exact front keeps authority over
    that), ONE OR SEVERAL copies in the picture (three cells turned three ways are three strips - the richest
    source of the way around; the stitcher unrolls each), nothing laid over the label. Single clean copies first."""
    out = []
    for p in dos.get("photos", []):
        if not isinstance(p, dict) or not p.get("labeled") or p.get("match") == "wrong":
            continue
        if p.get("match") != "exact" and not p.get("same_artwork"):
            continue
        fe = next((f for f in p.get("faces", []) if f.get("face") == "label"), None)
        if fe and not _covered(p, fe):
            out.append(p)
    out.sort(key=lambda p: (0 if (p.get("items") or 1) == 1 else 1, 0 if p.get("match") == "exact" else 1,
                            -float(p.get("quality") or 0)))
    return out


def _poor_source(dos, F):
    """Why the planned pixel source for side F is poor ("" when it is fine): something laid over it, several copies
    of the item in the picture, or not seen straight-on."""
    e = (dos.get("faces") or {}).get(F) or {}
    if e.get("source") != "exact_photo" or not e.get("photo"):
        return "no exact photo of this side"
    p = next((x for x in dos.get("photos", []) if x.get("file") == e["photo"]), {})
    fe = e.get("view") or {}
    why = []
    if _covered(p, fe):
        why.append("something laid over it")
    if (p.get("items") or 1) > 1:
        why.append(f"{p['items']} copies in the picture")
    if not fe.get("straight_on"):
        why.append("not seen straight-on")
    return ", ".join(why)


def source_rank(p, fe, q, picked=None):
    """Sort key for a side's pixel source, best first: nothing laid over it, seen straight-on, ONE copy of the item
    in the picture, then the look's quality; your pick wins only a tie. The pick is the identity; the pixels come
    from the best clean photo of this very item (2026-10-05)."""
    # one copy before straight-on: the unroll straightens an angle by math, but three cells crossing never become
    # one label (2026-10-05: the pick, three cells seen "straight-on", outranked a clean single cell lying flat)
    return (1 if _covered(p, fe) else 0, 0 if (p.get("items") or 1) == 1 else 1, 0 if fe.get("straight_on") else 1,
            -float(q or 0), 0 if p.get("file") == picked else 1)


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
        # a round item's wrapped label: a sister pack's cell with the SAME artwork (a 4-pack of the same batteries,
        # seen from other turns) is as good a source for the label as the single cell - the pick alone saw 67% of
        # the Duracell's label and the rest was in no "exact" photo (2026-10-04)
        exact = [c for c in cands if (c[1].get("match") == "exact" or (route == "round" and F == "label" and
                                                                     c[1].get("match") == "sister" and c[1].get("same_artwork")))
                 and c[0] >= 3 and free(c) and not _covered(c[1], c[2])]
        tmpl = [c for c in cands if c[1].get("match") in ("sister", "near_year") and c[0] >= 4 and free(c)
                and _shape_ok(c[1], c[2], dims.get(F)) and not _covered(c[1], c[2])]
        sister_seen = [c for c in cands if c[1].get("match") in ("sister", "near_year")]
        entry = {"source": "none", "photo": None, "page": "", "product_shown": "", "match": None, "swap": [],
                 "must_show": [], "note": "", "alternates": []}
        if F == PRIMARY[route] and picked:
            # YOUR PICK IS THE IDENTITY, NOT THE PIXELS BY RIGHT (2026-10-05: the pick showed three cells crossing
            # under a caption; it was forced as the label's source and the model came out wearing the caption).
            # The pick joins the exact candidates with its real marks; the best CLEAN source wins (below). What it
            # lacks is written as a gap either way.
            pp = next((p for p in dos["photos"] if p["file"] == picked), {"file": picked})
            fe = next((f for f in pp.get("faces", []) if face_name(route, f["face"]) == F), {"face": F})
            if route == "round":                              # the whole wrap, cropped to where the label is
                fe = {"face": F, "turn": fe.get("turn", 0), "straight_on": fe.get("straight_on", False),
                      "box": fe.get("box")}
            if _covered(pp, fe):
                gaps.append(f"{F}: your pick has something laid over this side ("
                            + ", ".join(f"{o['what']} {o['text']!r}" for o in pp.get("overlays", []))[:120]
                            + ") - it must not end up on the model")
            if (pp.get("items") or 1) > 1:
                gaps.append(f"{F}: your pick shows {pp['items']} of the item - one clean copy is the source for this side")
            exact = [(max(float(pp.get("quality") or 0), 3.0), pp, fe)] + [c for c in exact if c[1]["file"] != picked]
        if exact:
            exact.sort(key=lambda c: source_rank(c[1], c[2], c[0], picked))
            q, p, fe = exact[0]
            is_pick = p.get("file") == picked
            entry.update(source="exact_photo", photo=p["file"], page=p.get("page", ""), match="exact",
                         product_shown=p.get("product_shown", ""),
                         note=("your pick" if is_pick else "the cleanest exact photo of this side (your pick is the identity)")
                         + ("" if fe.get("straight_on") else ", seen at an angle in the photo")
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
            was = int(old.get("version") or 1)
            replan(old, log)                                  # newer rules: from the looks already taken, in seconds
            again = []
            if was < 7:                                       # 5/6: looks taken without the kit's help or the
                again = [p for p in old.get("photos", []) if p.get("labeled")   # same-artwork question: again;
                         and (old.get("route") == "round" and                    # 7: the pick's own look (not told
                              (was < 5 and any(f.get("face") in ("top", "bottom") for f in p.get("faces", []))   # the answer)
                               or p.get("match") == "sister" and "same_artwork" not in p)
                              or p.get("file") == old.get("picked") and "look_match" not in p)]
            if was < 8:                                       # 8: how many copies are in the picture (the label's
                again += [p for p in old.get("photos", []) if p.get("labeled") and "items" not in p   # source rule)
                          and (p.get("match") == "exact" or p.get("file") == old.get("picked")) and p not in again]
            for p in again:
                p["labeled"] = False
                p["faces"] = []
            if was < 10 and old.get("route") == "round" and len(_round_sources(old)) < ROUND_SOURCES and \
                    any(not p.get("labeled") and (p.get("quick") or {}).get("same_item") for p in old.get("photos", [])):
                old["done"] = False                           # 10: more careful looks, for the way around
                save(old)
                log(f"[dossier] {cid}: a round label with {len(_round_sources(old))} clean exact photo(s) - more of its "
                    "same-item photos get the careful look (for the way around)")
            if again:
                old["done"] = False
                save(old)
                log(f"[dossier] {cid}: {len(again)} careful look(s) are taken again under the newer rules (which end "
                    "is which; does a sister pack carry the same artwork; the pick judged without being told; how "
                    "many copies are in the picture)")
        if old.get("done"):
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

    # 1b. eBay FIRST (Cody, 2026-10-07 05:22: "it's using the same busted ass images" - after the reset the first
    #     hunt found the same Google photos again, and eBay only came in late, at the label): each good listing is
    #     one copy of the item from every side, its photos looked at with everything else from the start
    if web and use:
        hunt_listings(dos, cid, use, log)
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
    # the main side's pixel source is poor (something laid over it, several copies in the picture, seen at an
    # angle) and there are good quick-look candidates nobody looked at carefully: look at up to MORE_FOR_PRIMARY of
    # them and plan again (2026-10-05: the pick - three cells under a caption - was the only exact label photo
    # looked at, with 20 single-cell label photos waiting in the quick looks)
    F = PRIMARY[route]
    if web and use and _poor_source(dos, F):
        cands = [p for p in dos["photos"] if not p.get("labeled") and (p.get("quick") or {}).get("same_item")
                 and (p.get("quick") or {}).get("kind") not in ("render", "ad") and _could_show(p, F, route)
                 and _overlap((p.get("quick") or {}).get("years") or era, era)]
        cands.sort(key=lambda p: -_quick_score(p, era))
        if cands:
            log(f"[dossier] the {F}'s source is poor ({_poor_source(dos, F)}) - a careful look at "
                f"{min(len(cands), MORE_FOR_PRIMARY)} more photo(s) of it")
            careful_looks(dos, use, log, only=cands[:MORE_FOR_PRIMARY])
            dos["faces"], face_gaps = plan(dos)
    # A ROUND LABEL NEEDS THE WAY AROUND (2026-10-06 05:59: 335 photos, 72 the quick look called this very item,
    # 14 looked at carefully, 3 exact - none showing the back; the painter had to guess it and guessed noise). The
    # stitcher places real strips only where real photos overlap, so a round item keeps giving same-item photos
    # the careful look until ROUND_SOURCES clean exact photos exist (that many single-copy photos of a cell all
    # but surely include the back), ROUND_LOOKS at most. The careful look is the one cost; a guessed back is not.
    if web and use and route == "round":
        looked = 0
        while looked < ROUND_LOOKS and len(_round_sources(dos)) < ROUND_SOURCES:
            cands = [p for p in dos["photos"] if not p.get("labeled") and (p.get("quick") or {}).get("same_item")
                     and (p.get("quick") or {}).get("kind") not in ("render", "ad")
                     and _overlap((p.get("quick") or {}).get("years") or era, era)]
            if not cands:
                break
            cands.sort(key=lambda p: -_quick_score(p, era))
            batch = cands[:min(8, ROUND_LOOKS - looked)]
            log(f"[dossier] a round label needs photos all the way around: {len(_round_sources(dos))} clean exact "
                f"photo(s) so far, {ROUND_SOURCES} wanted - a careful look at {len(batch)} more ({len(cands)} waiting)")
            careful_looks(dos, use, log, only=batch)
            looked += len(batch)
            dos["faces"], face_gaps = plan(dos)
        dos["faces"].setdefault(PRIMARY[route], {})["alternates"] = [p["file"] for p in _round_sources(dos)
                                                                     if p["file"] != dos["faces"].get(PRIMARY[route], {}).get("photo")]
    dos["facts"] = FX.gather(dos, log, use, web=web)
    _sides_from_facts(dos)
    dos["gaps"] = face_gaps + dos["gaps"]
    dos["version"] = VERSION
    dos["made_at"] = time.time()
    # done only when it is complete: your AI read the identity, the hunt ran without a block, and at least one
    # careful look succeeded (audit 2026-10-04: a dossier with a failed identity read or a captcha was marked
    # done and reused forever)
    looked = sum(1 for p in dos["photos"] if p.get("labeled"))
    why_not = []
    if not use:
        why_not.append("no AI")
    if "catalog name only" in str(dos["identity"].get("read_from", "")):
        why_not.append("the identity could not be read from the photo")
    if dos.get("hunt_incomplete"):
        why_not.append("the photo hunt was blocked: " + str(dos["hunt_incomplete"]))
    if not looked:
        why_not.append("no careful look succeeded")
    dos["done"] = not why_not
    dos["incomplete"] = "; ".join(why_not)
    if why_not:
        log(f"[dossier] {cid}: NOT complete ({dos['incomplete']}) - it is finished next time")
    save(dos)
    log(f"[dossier] {cid}: " + "; ".join(f"{F} {e['source'].replace('_', ' ')}" for F, e in dos["faces"].items()))
    for g in dos["gaps"]:
        log(f"[dossier] gap: {g}")
    return dos


def ensure(cid, card, picked, use=None, redo=False, log=print):
    """build() for the asset maker. A dossier that cannot be made STOPS the build (audit 2026-10-04: it used to
    return an empty one and the item was built with no identity, no sides and no facts - and could pass). An
    incomplete dossier (identity unread, hunt blocked, no careful look) stops it too; the item is tried again later."""
    try:
        dos = build(cid, card, picked, log=log, use=use, redo=redo)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"the dossier could not be made ({e}) - nothing is built without knowing the item")
    if not dos.get("done"):
        raise RuntimeError("the dossier is not complete (" + str(dos.get("incomplete") or "unknown") +
                           ") - nothing is built without knowing the item; it is finished and built next time")
    return dos


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


def label_views(dos, picked, want=4):
    """The photos a round item's label is unrolled from, best source first: the plan's source for the label (with
    the box the careful look drew around the label and any overlay boxes, so the unroll takes the label and
    nothing laid over it), then its alternates. Your pick is the identity; it is in this list only when it is one
    of the clean sources. Masks are added by the caller."""
    F = PRIMARY.get(dos.get("route"), "front")
    e = (dos.get("faces") or {}).get(F) or {}
    files = ([e.get("photo")] if e.get("source") == "exact_photo" and e.get("photo") else []) + list(e.get("alternates") or [])
    if dos.get("route") == "round":
        # a round label reads its sources from the rule itself, every time - never from a list saved before the
        # rule changed (2026-10-06 12:14: the cached battery still stitched 4 photos after the rule took in every
        # credible photo of it)
        files += [p["file"] for p in _round_sources(dos)]
    photos = {p.get("file"): p for p in dos.get("photos", []) if isinstance(p, dict)}
    out, seen = [], set()
    for f in files:
        if not f or f in seen or not os.path.exists(f):
            continue
        seen.add(f)
        p = photos.get(f, {})
        fe = e.get("view") if f == e.get("photo") else next((x for x in p.get("faces", []) if face_name(dos.get("route"), x["face"]) == F), None)
        several = f != e.get("photo") and (p.get("items") or 1) > 1      # an alternate with several copies: every
        out.append({"file": f, "vet": {"view": F, "count": p.get("items")}, "plan": F, "source": "exact_photo",   # cell
                    "box": None if several else (fe or {}).get("box"),                                             # is a strip
                    "overlays": [o.get("box") for o in p.get("overlays") or [] if o.get("box")],
                    # a round item is unrolled from its WHOLE outline: the box says which item in the photo, it does
                    # not cut pixels (a label box that leaves out the copper end breaks the cylinder math)
                    "box_mode": "select" if dos.get("route") == "round" else "crop",
                    "items": p.get("items"), "is_pick": f == (picked or {}).get("file") if isinstance(picked, dict) else f == picked})
    return out[:want]


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
