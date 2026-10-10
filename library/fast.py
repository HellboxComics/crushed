"""THE STREAMLINED ROUND BUILD (Cody, 2026-10-07 20:34: "it should take an hour or two, not weeks... it is STILL
copying and pasting the image rather than drawing one good image... cut out all the bullshit"; 20:36: "it does not
have to be a pixel for pixel match... it has to say words and make sense... reference the real world item for the
era and build as accurately and as convincing as possible").

Five steps, nothing else:
  1. references   eBay listings (one copy, every side; for sale + sold) and the Google image hunt
  2. sort         ONE quick look per photo: is it this item, which side faces the camera
  3. draw         Qwen-Image-Edit-2511 draws ONE clean studio photo of the item from a sheet of the best photos,
                  then its other side from the photos that show it (huggingface.co/Qwen/Qwen-Image-Edit-2511: a
                  clean product image from reference photos is what it does well - the drawn front scored 9-10/10
                  against the real photos on 2026-10-06/07); photos are references only, never the texture
  4. model        the drawn views unrolled onto the exact real-size shape (the same cylinder unroll as before),
                  Blender: mesh, UV map, texture map, material, insides; every format
  5. judge        one look at the finished model next to the real photos: realistic, right for its era, real words
                  that make sense. A miss is drawn again once with the judge's own words; a pass is filed in the
                  Asset Library.
"""
import json
import math
import os
import re
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

REF_Q = ("We are rebuilding this exact item as a 3D model: {product} (made around {year}). Look at the photo. Answer "
         "ONLY JSON: {{\"real_photo\": true if it is a real photograph (not a drawing, render or ad), \"score\": 0-10 how "
         "surely it shows THIS item - the same product line, printed design and size, from the right era (a newer "
         "redesign or another size scores low), \"side\": \"front\" if the side with the main logo or panel faces "
         "the camera, \"back\" if the opposite side (warnings, codes, a second logo), \"several\" if several copies "
         "show different sides, \"end\" if only an end, \"none\" if it is not the item, \"one_item\": true if exactly "
         "one copy is in the picture, \"kind\": \"item\" if it is the actual product itself, \"merch\" if it is "
         "merchandise or a look-alike (a pin, magnet, mug, toy, sign, display), \"package\" if only its packaging, "
         "\"ad\" for an advertisement}}")

VERSION_Q = (
    "Picture 1 is a sheet of real photos of ONE version of {product} as it was sold around {year} - our reference - "
    "showing its different sides (one side may carry the big logo, another the small print, a meter or a panel). "
    "Picture 2 is another photo. Could each item in picture 2 be one of the items in picture 1, seen from some side? "
    "Judge by the design: the logo's lettering style, the colors and where they sit, frames, meters, icons, the "
    "typefaces. A side picture 1 does not show is fine if its style matches. A redesign from another year or decade "
    "(a different logo style, a feature added or missing), another product line, another size or another brand is "
    "NOT the same version. Answer ONLY JSON: {{\"same\": \"all\" if every item in picture 2 is that same version, "
    "\"some\" if only some of them are, \"none\" if none are, \"why\": \"short\"}}")

DRAW_FRONT = (
    "Picture 1 is a sheet of real photos of {product}, made around {year}; picture 2 is its clearest photo. Make ONE "
    "clean, convincing studio product photo of exactly one {product} exactly as it looked in {year}: lying on its "
    "side, its long axis level and left to right, the side with its main logo and panel turned to the camera as in "
    "picture 2, centered and filling most of the width, on plain white, soft even light, sharp, true colors, no "
    "glare, no other objects, no hands. Its true proportions: {size}. Copy the printed design from the photos - "
    "logo, panels, colors, bands and small print in their real places. Every word printed on it is a real, correctly "
    "spelled word that makes sense for this product.{words}{fix}")
DRAW_BACK = (
    "The pictures are real photos of {product}, made around {year}, in which the OTHER side of its printed label "
    "faces the camera - not the side with the main panel. Make ONE clean studio product photo of exactly one "
    "{product} showing THAT side: lying on its side, long axis level and left to right, centered, filling most of "
    "the width, plain white background, soft even light, sharp, true colors, no glare, no other objects, no hands. "
    "Its true proportions: {size}. Copy that side's logos, panels and small print from the photos. Every word is a "
    "real, correctly spelled word that makes sense for this product.{words}{fix}")
PICK_Q = ("Picture 1 is a drawn studio photo of an item. Picture 2 is a real photo of {product} from around "
          "{year}. Does picture 1 look like a real photo of that same item from that era - the same printed design, "
          "logo, colors and layout, real words that make sense? Answer ONLY JSON: {{\"match\": 0-10, "
          "\"wrong\": [\"short, specific\"]}}")
JUDGE_Q = ("Pictures 1 and 2 show our finished 3D model of {product}: close-ups (left to right: the top end seen from "
           "above, the bottom end seen from below, the back, a top edge), and all the way around. Picture 3 "
           "is a sheet of real photos of that item from around {year}. The label must look printed all the way round: "
           "no blank or smeared stretches, no seam, no part where one side's colors differ from the other's. Judge it like a buyer of the best 3D product assets sold on "
           "TurboSquid or CGTrader would, and like a collector of the real thing. Answer ONLY JSON: "
           "{{\"realism\": 0-10 (does it look like a real physical object: shape, proportions, materials, print "
           "quality), \"era\": 0-10 (is it the right version of this product for {year}: logo, colors, design), "
           "\"words\": 0-10 (is the printed text made of real words that make sense for this product - not gibberish), "
           "\"fix\": [\"what to change, short and specific\"]}}")
PASS = 8                                                    # each of realism, era and words (production)


def tok(x):
    return set(re.findall(r"[a-z0-9]+", str(x).lower()))


def display(card):
    """The item as its era knew it: "Duracell Coppertop AA alkaline battery (sold then as Duracell PowerCheck)"."""
    n = card.get("era_names") or []
    return card["product"] + (f" (sold then as {n[0]})" if n else "")


def short_name(product):
    """What a person types into a search box: the catalog name without the era words or ratings."""
    n = re.sub(r"\(.*?\)", "", str(product))
    n = re.sub(r",?\s*(circa|c\.|from|made in)\b.*$", "", n, flags=re.I)
    n = re.sub(r"\b[\d.,]+\s*(volts?|v|mah|mm|in|oz|g|ct|count|pack)?\b", " ", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip(" ,")


MERCH = {"pin", "pins", "lapel", "mug", "mugs", "cup", "glass", "magnet", "keychain", "chain", "shirt", "tee",
         "hat", "cap", "sign", "poster", "ad", "advertisement", "advertising", "toy", "plush", "bunny",
         "figure", "figurine", "tin", "patch", "sticker", "decal", "ornament", "bag", "backpack",
         "clock", "lamp", "flashlight", "watch", "empty"}


MERCH_NO = ("pin", "lapel", "mug", "magnet", "keychain", "sign", "toy", "plush", "shirt", "poster", "figurine",
            "sticker")                                       # the ones a search leaves out, most common first


def kind_phrase(name):
    """The item itself in two or three words: its size (AA, 9V, 12 oz) and the kind of thing it is - the last word
    of its name ("Duracell Coppertop AA alkaline battery" -> "AA battery")."""
    ws = str(name).split()
    if not ws:
        return ""
    size = [w for w in ws[:-1] if re.fullmatch(r"(?i)(aaa|aa|[cd]|9v|\d+(\.\d+)?(v|oz|in|mm|ml|l|lb|g)?)", w)]
    return " ".join(size[:1] + [ws[-1]])


def rank_listings(rows, names, brand, year, kind=""):
    """eBay listings ranked by idf - a word's weight is how rare it is among the results' titles (Sparck Jones 1972)
    - plus the era's words for an old item; another brand is dropped, and so is a title without the item's own kind
    of thing (a battery) or one that names merchandise (a pin, a mug) the item is not (2026-10-08 11:10: of 56
    reference photos, pins, mugs, a bunny toy and a backpack outnumbered the battery)."""
    N = max(1, len(rows))
    df = {}
    for L in rows:
        for w in tok(L["title"]):
            df[w] = df.get(w, 0) + 1
    want = set().union(*[tok(n) for n in names]) if names else set()
    era = set()
    try:
        if int(year) <= time.localtime().tm_year - 15:
            era = {"vintage", "old", "nos", f"{str(int(year))[2]}0s", f"{str(int(year))[:3]}0s"}
    except (TypeError, ValueError):
        pass
    b = tok(brand)
    kd = [k[:5] for k in tok(kind) if len(k) >= 3]
    named = set().union(*[tok(n) for n in names]) if names else set()
    has = sum(1 for L in rows if any(w.startswith(k) for w in tok(L["title"]) for k in kd)) if kd else 0
    use_kind = bool(kd) and has >= min(3, max(1, len(rows) // 4))   # a wrong guess at the kind ("pink" for a
    #                                                                 Furby) would drop every listing: used only
    #                                                                 when the titles do say it

    size = [w for w in tok(kind) if re.fullmatch(r"aaa|aa|[cd]|9v|\d+(v|oz|in|mm|ml|l|lb|g)?", w)]
    with_size = sum(1 for L in rows if set(size) & tok(L["title"])) if size else 0
    use_size = bool(size) and with_size >= min(3, max(1, len(rows) // 4))
    common = {w for w, n in df.items() if n > 0.3 * N} if N >= 10 else set()   # a word most of MANY titles carry
    #   says nothing of the era (13:24: among 3 titles, "PowerCheck" itself counted as common and the listing fell)
    era_named = (set().union(*[tok(x) for x in names[:-1]]) - tok(names[-1])) if len(names) > 1 else set()
    #   the era's own names, less what today's name also says ("Coppertop" is still sold; "PowerCheck" is the era)
    years = set()
    try:
        years = {str(y) for y in range(int(year) - 5, int(year) + 6)}   # "circa 1998", "2001" on a date code
    except (TypeError, ValueError):
        pass
    era_words = (era | years | (era_named - b - common - set(size) - tok(kind))) if era else set()

    def score(L):
        t = tok(L["title"])
        if b and t and not (b & t):
            return -1.0
        if use_size and not (set(size) & t):               # another size (11:47: a 9 volt ranked first for an AA)
            return -1.0
        if era and not (era_words & t):                    # an old item: the title names its era ("vintage") or
            return -1.0                                    # its era's own name ("PowerCheck") - not Power Boost
        if use_kind and not any(w.startswith(k) for w in t for k in kd):
            return -1.0
        if (t & MERCH) - named:
            return -1.0
        return sum(math.log((N + 1) / (df.get(w, 0) + 1)) for w in want & t) + 2 * len(era & t)
    return sorted((L for L in rows if score(L) >= 0), key=lambda L: -score(L))


def references(cid, card, R, log, listings=10, google=25):
    """[{"file", "url", "page", "listing"}] - eBay listings first (each one copy from every side), then the Google
    hunt's photos. Downloaded into WORK/hunt/<cid>; kept between runs."""
    import google_images as G
    import dossier as DS
    import hunt
    d = os.path.join(R.WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    cache = os.path.join(d, "fast_refs.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    product, year = card["product"], card.get("year")
    name = short_name(product)
    brand = name.split()[0] if name else ""
    old = False
    try:
        old = int(year) <= time.localtime().tm_year - 15
    except (TypeError, ValueError):
        pass
    era_names = [short_name(n) for n in (card.get("era_names") or [])][:2]   # what it was SOLD as back then
    out, rows, seen = [], [], set()                         # ("Duracell PowerCheck"), not only the catalog's name
    kp = kind_phrase(name)                                  # every search names the item itself ("AA battery"):
    with_kind = lambda n: n if all(w in tok(n) for w in tok(kp)) else f"{n} {kp}"   # 11:28 "vintage Duracell
    #                                                         Coppertop" pulled up pins and memorabilia (Cody)
    qs = [q for n in era_names for q in (("vintage " + with_kind(n)) if old else "", with_kind(n))] \
        + [("vintage " + name) if old else "", name]
    no = " ".join("-" + w for w in MERCH_NO if w not in tok(name))   # eBay's minus sign leaves a word out
    for q in dict.fromkeys(qs):
        if not q:
            continue
        try:
            for L in G.search_listings(f"{q} {no}", log=log):
                if L["id"] not in seen:
                    seen.add(L["id"])
                    rows.append(L)
        except Exception as e:
            log(f"[fast] eBay could not be searched: {str(e)[:120]}")
    kind = kp                                                # its size and kind ("AA battery") - 12:44: given only
    rows = rank_listings(rows, era_names + [name], brand, year, kind=kind)   # "battery", a 9 volt ranked first
    log("[fast] eBay listings, best match first: " + " | ".join(L["title"][:50] for L in rows[:listings]))
    others = []                                              # the other marketplaces and collectors' pages
    for q in dict.fromkeys([q for q in qs if q][:2]):
        try:
            others += [L for L in G.market_pages(q, log=log) if L["id"] not in {o["id"] for o in others}]
        except Exception as e:
            log(f"[fast] the other marketplaces could not be searched: {str(e)[:120]}")
    others = rank_listings(others, era_names + [name], brand, year, kind=kind)
    log("[fast] other marketplaces, best match first: " + " | ".join(f"{L.get('site', '')}: {L['title'][:40]}" for L in others[:6]))
    for L in rows[:listings] + others[:6]:
        try:
            pics = G.listing(L["page"], log) if "ebay.com" in L["page"] else G.page_photos(L["page"], log=log)
            for u in pics[:12]:
                f = DS._download(u, d)
                if f:
                    out.append({"file": f, "url": u, "page": L["page"], "listing": L["id"], "title": L["title"]})
        except Exception as e:
            log(f"[fast] {L['page']} could not be opened: {str(e)[:80]}")
    try:
        found = hunt.run(cid, name, year, log=log)
    except Exception as e:
        log(f"[fast] the Google hunt did not run: {str(e)[:120]}")
        found = []
    have = {o["file"] for o in out}
    for f in found[:google]:
        if f.get("file") and f["file"] not in have and os.path.exists(f["file"]):
            out.append({"file": f["file"], "url": f.get("url", ""), "page": f.get("page", ""), "listing": None,
                        "title": f.get("title", "")})
    json.dump(out, open(cache, "w"), indent=1)
    log(f"[fast] {len(out)} reference photos ({sum(1 for o in out if o['listing'])} from {min(len(rows), listings)} eBay listings)")
    return out


def sort_refs(refs, card, R, log):
    """One quick look per photo (the fastest brain that sorts right). A listing whose best photo is this item lends
    all its real photos - one listing is one copy. -> the refs with "look" set, best first."""
    import vet as V
    q = REF_Q.format(product=display(card), year=card.get("year") or "its era")
    use = V.quick_model() or V.model()
    todo = [r for r in refs if "look" not in r]

    def look(r):
        return V.ask(use, q, [r["file"]], think=False, side=768) or {}

    def done(i, v):
        todo[i]["look"] = v if isinstance(v, dict) else {}
    if todo:
        V.parallel(look, todo, done)
    by_listing = {}
    for r in refs:
        if r.get("listing"):
            by_listing.setdefault(r["listing"], []).append(r)
    for lid, rs in by_listing.items():                       # one copy: its best look speaks for every photo of it
        best = max(int((r.get("look") or {}).get("score") or 0) for r in rs)
        for r in rs:
            r["listing_best"] = best
    for r in refs:
        lk = r.get("look") or {}
        s = int(lk.get("score") or 0)
        if (r.get("listing") and r.get("listing_best", 0) >= 7 and lk.get("real_photo") is not False
                and lk.get("kind", "item") == "item" and s >= 3):      # lent only to a photo of the item itself
            s = max(s, 7)                                    # (12:44: a lot's TrustFire photos, scored 0, were lent)
        # merchandise in the same artwork (a battery-shaped pin, a magnet - 2026-10-07 22:10: two were on the
        # drawing's sheet) and ads are no reference for the item itself
        r["score"] = s if lk.get("real_photo") is not False and lk.get("kind", "item") == "item" else 0
    good = sorted([r for r in refs if r["score"] >= 7], key=lambda r: (-r["score"], 0 if r.get("listing") else 1))
    listed = [r for r in good if r.get("listing")]
    if len(listed) >= 6:                                     # enough of the real thing from listings found by its
        good = listed                                        # era's names: the web's photos (modern packs, a newer
        #                                                      design the quick look scored 9 - 11:10) are left out
    log(f"[fast] {len(good)} of {len(refs)} photos show this item; "
        f"{sum(1 for r in good if (r.get('look') or {}).get('side') in ('back', 'several'))} show another side")
    return good


def unique_refs(refs):
    """Each photo once (2026-10-09: an eBay page's carousel photo of ANOTHER listing - a 1981 Duracell - was saved for
    two listings; read twice, its lines 'SIZE AA', '1.5 VOLTS', 'CAUTION...' counted as read on two photos and were
    printed on the 1998 label). The same picture under another name is the same photo too (its bytes' hash). A photo
    found under two different listings is marked "shared": it may belong to neither (a page's carousel), so it is
    never the reference copy."""
    import hashlib
    out, seen = [], {}
    for r in refs:
        try:
            key = hashlib.md5(open(r["file"], "rb").read()).hexdigest()
        except Exception:
            key = r.get("file")
        if key in seen:
            first = seen[key]
            if r.get("listing") and first.get("listing") and r.get("listing") != first.get("listing"):
                first["shared"] = True
            continue
        r = dict(r)
        seen[key] = r
        out.append(r)
    return out


_YES = ("all", "yes", "true", "same")
_NO = ("none", "no", "false", "different", "not", "other")


class Versions:
    """One version of the item only (2026-10-09: the photos held a 1981 Duracell, a later italic-logo Duracell and a
    modern one beside the 1998 PowerCheck; their words and a view of the italic one went onto the label).
    The reference is a SHEET of photos of one copy from its different sides - from the listing with the most photos
    of this item (one listing is one seller's copy), never a photo two listings share (a page's carousel), chosen to
    show as many sides as possible (each next photo the one whose printed lines overlap least with those already
    on the sheet). A single side was not enough: compared with only the logo side, the brain called the same
    battery's PowerCheck side "a different product line" and left out 5 of 7 good photos (2026-10-10 02:00).
    Every other photo, and every copy cut from a photo of several, is compared with the sheet by the vision brain.
    Answers are kept in the photo hunt's folder (a restart does not ask again); a failed or unclear answer is not
    kept and the photo stays (logged). same(file) -> "all" | "some" | "none"."""

    def __init__(self, cid, card, good, R, log, most=4):
        import hashlib
        self.card, self.log, self.R = card, log, R
        self.q = VERSION_Q.format(product=display(card), year=card.get("year") or "its era")
        self.qkey = hashlib.md5(self.q.encode()).hexdigest()[:6]
        d = os.path.join(R.WORK, "hunt", cid)
        self.path = os.path.join(d, "versions.json")
        try:
            self.cache = json.load(open(self.path))
        except Exception:
            self.cache = {}
        self._md5 = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
        self.failed = set()                                  # asked this run without a clear answer: not again now
        good = [r for r in good if os.path.exists(r.get("file") or "")]   # (a photo moved away by hand: skipped)
        self.sheet_files = self._pick(good, most)
        self.anchor, self.akey = None, ""
        if self.sheet_files:
            try:
                self.anchor = os.path.join(d, "version_sheet.jpg")
                self._tile(self.sheet_files, self.anchor)
                self.akey = hashlib.md5("".join(self._md5(f) for f in self.sheet_files).encode()).hexdigest()[:12] \
                    + self.qkey
            except Exception as e:
                log(f"[fast] the reference sheet could not be made ({str(e)[:80]}) - every photo kept")
                self.anchor, self.akey, self.sheet_files = None, "", []
        if self.anchor:
            log("[fast] the reference for its version, one copy from its sides: "
                + ", ".join(os.path.basename(f) for f in self.sheet_files))

    @staticmethod
    def _tile(files, out, cell=640):
        from PIL import Image
        ims = []
        for f in files:
            im = Image.open(f).convert("RGB")
            im.thumbnail((cell, cell))
            ims.append(im)
        cols = 2 if len(ims) > 1 else 1
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * cell + (cell - im.width) // 2, (i // cols) * cell + (cell - im.height) // 2))
        sheet.save(out, quality=92)
        return out

    def _pick(self, good, most):
        import measure as MS
        norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
        own = lambda r: int((r.get("look") or {}).get("score") or 0)
        cand = [r for r in good if not r.get("shared")] or good
        if not cand:
            return []
        prev = self.cache.get("_sheet") or []
        if prev and all(any(os.path.basename(r["file"]) == p for r in cand) for p in prev):
            return [next(r["file"] for r in cand if os.path.basename(r["file"]) == p) for p in prev]
        by = {}
        for r in cand:
            if r.get("listing"):
                by.setdefault(r["listing"], []).append(r)
        lst = max(by.values(), key=lambda rs: (len(rs), max(own(r) for r in rs))) if by else []
        if len(lst) >= 2:
            pool = lst                                       # one seller's copy, all its sides
        else:
            top = max(own(r) for r in cand)
            pool = [r for r in cand if own(r) >= top - 1]
        lines = {}
        for r in pool:
            try:
                lines[r["file"]] = {norm(l) for l in (MS.read_lines(r["file"]) or []) if len(norm(l)) >= 3}
            except Exception:
                lines[r["file"]] = set()
        left = sorted(pool, key=lambda r: (-own(r), -len(lines[r["file"]])))
        pick = [left.pop(0)]
        covered = set(lines[pick[0]["file"]])
        while left and len(pick) < most:                     # each next: the most NEW printed lines (another side)
            nxt = max(left, key=lambda r: (len(lines[r["file"]] - covered), len(lines[r["file"]]), own(r)))
            left.remove(nxt)
            pick.append(nxt)
            covered |= lines[nxt["file"]]
        files = [r["file"] for r in pick]
        if len(files) >= 3:                                  # each sheet photo must fit the others (leave one out):
            keep_ = []                                       # a carousel photo of another listing saved with this
            for f in files:                                  # one (2026-10-09: a 1981 Duracell) is taken off
                others = [g for g in files if g != f]
                try:
                    import tempfile
                    import vet as V
                    with tempfile.TemporaryDirectory() as td:
                        sh = self._tile(others, os.path.join(td, "others.jpg"))
                        v = V.ask(V.model(), self.q, [sh, f], think=False) or {}
                    a = v.get("same")
                    a = ("all" if a else "none") if isinstance(a, bool) else str(a or "").strip().lower()
                except Exception:
                    a = ""
                if a in _NO:
                    self.log(f"[fast] {os.path.basename(f)} does not fit the other photos of its listing "
                             f"({str(v.get('why') or '')[:120]}) - not on the reference sheet")
                else:
                    keep_.append(f)
            if len(keep_) >= 2:
                files = keep_
        self.cache["_sheet"] = [os.path.basename(f) for f in files]
        self._save()
        return files

    def _save(self):
        try:
            tmp = self.path + ".part"
            json.dump(self.cache, open(tmp, "w"), indent=1)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def _key(self, f):
        try:
            return self.akey + ":" + self._md5(f)[:12]
        except Exception:
            return None

    def _ask(self, f):
        import vet as V
        v = V.ask(V.model(), self.q, [self.anchor, f], think=False) or {}
        a = v.get("same")
        a = ("all" if a else "none") if isinstance(a, bool) else str(a or "").strip().lower()
        a = "all" if a in _YES else "some" if a == "some" else "none" if a in _NO else ""
        return {"same": a, "why": str(v.get("why") or "")[:160]}

    def _store(self, f, v):
        if isinstance(v, Exception) or not isinstance(v, dict) or not v.get("same"):
            why = str(v)[:80] if isinstance(v, Exception) else (v or {}).get("why", "") if isinstance(v, dict) else ""
            self.log(f"[fast] {os.path.basename(f)}: no clear answer on its version ({why or 'unclear'}) - kept")
            self.failed.add(f)
            return                                           # (not saved: asked again on the next run)
        self.cache[self._key(f)] = dict(v, file=os.path.basename(f))
        self._save()
        self.log(f"[fast] {os.path.basename(f)}: the same version as the reference? {v['same']}"
                 + (f" ({v['why']})" if v.get("why") else ""))

    def same(self, f):
        if not self.anchor or f in self.sheet_files:
            return "all"
        k = self._key(f)
        if k is None or f in self.failed:
            return "all"
        if k not in self.cache:
            try:
                self._store(f, self._ask(f))
            except Exception as e:
                self._store(f, e)
        return (self.cache.get(k) or {}).get("same") or "all"

    def keep(self, good):
        """The photos of this version: each marked r["version"] = "all", or "some" (only some copies are: only its
        cut copies, each checked, may be drawn; its lines are not read for the words). Asked together."""
        import vet as V
        good = [r for r in good if os.path.exists(r.get("file") or "")]
        todo = [r["file"] for r in good if self.anchor and r["file"] not in self.sheet_files
                and self._key(r["file"]) is not None and self._key(r["file"]) not in self.cache]
        if todo:
            V.parallel(self._ask, todo, lambda i, v: self._store(todo[i], v))
        out = []
        for r in good:
            v = self.same(r["file"])
            if v != "none":
                out.append(dict(r, version=v))
        dropped = len(good) - len(out)
        self.log(f"[fast] {len(out)} of {len(good)} photos show this version"
                 + (f"; {dropped} left out as another version" if dropped else ""))
        if len(out) * 2 < len(good):
            self.log("[fast] WARNING: most photos are another version than the reference sheet - check the sheet "
                     "(hunt/<item>/version_sheet.jpg) shows the right item")
        return out


def photo_words(good, log, most=8):
    """The printed lines on the best photos, read by Apple's own text reader (measure.read_lines) - kept when read on
    at least two different photos (majority voting across independent reads, ROVER). Qwen-Image renders exact text
    when it is GIVEN the words (its model card: precise text rendering); without them it invents (2026-10-07 22:10:
    'ALKAMEF ATERN', 'AUFALNE BATTEMP')."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    reads = []
    good = [g for g in unique_refs(good) if g.get("version", "all") == "all"]   # one version, each photo once
    for r in [g for g in good if (g.get("look") or {}).get("side") in ("front", "back", "several")][:most]:
        try:
            reads.append([l.strip() for l in (MS.read_lines(r["file"]) or []) if len(norm(l)) >= 3])
        except Exception:
            pass
    texts = [norm(" ".join(x)) for x in reads]
    out = []
    for lines in reads:
        for l in lines:
            n = norm(l)
            if any(norm(o) == n for o in out):
                continue
            hits = sum(1 for t in texts if (n in t if len(n) < 6 else fuzz.partial_ratio(n, t) >= 85))
            letters = sum(c.isalpha() for c in l) / max(1, len(l.replace(" ", "")))
            # a printed number with its unit is a real line too ("100%" on the PowerCheck meter, "1.5 V", "9V") -
            # the letters rule alone dropped it (2026-10-09)
            amount = re.fullmatch(r"\d{1,4}([.,]\d{1,2})?\s?(%|°[CF]?|V|mAh|mm|ml|oz|g)", l.strip(), re.I)
            if hits >= 2 and (letters >= 0.4 or amount):
                out.append(l)
    log(f"[fast] words read on at least two photos: {out[:20]}")
    return out[:30]


PROOF_Q = (
    "These are real photos of {product}, made around {year}. A text scanner read the lines below off them; it often "
    "misreads (it read DURAGEL for DURACELL, POWEDCHECKIN for POWERCHECK, 'Test al' for 'Test at', TOTEST for TO "
    "TEST). Scanner lines: {lines}. Look at the photos and give every one of those lines spelled EXACTLY as it is "
    "printed on the item - fix the scanner's mistakes, split or join words as printed, keep the (R) and (TM) marks as "
    "the symbols \u00ae and \u2122 where printed. Drop a scanner line that is not printed text on the item. Never add "
    "a line the scanner did not read. Answer ONLY JSON: {{\"lines\": [\"...\", ...]}}")


def proofread(words, photos, card, log):
    """The scanner's lines spelled as printed, by the vision brain that reads like a person (it knows the item) -
    each answer must be one of the scanner's own lines put right (70% alike or more), so nothing is added that
    the photos were not read to carry. 2026-10-08 20:40 (Cody): "The fuck is a duragel? ... a label for a battery
    in the 90s, fucking simple" - the scanner's misreadings were set as type. -> [lines] (the scanner's if it fails)."""
    import vet as V
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    if not words or not photos:
        return list(words)
    try:
        v = V.ask(V.model(), PROOF_Q.format(product=display(card), year=card.get("year") or "its era",
                                            lines=json.dumps(list(words), ensure_ascii=False)),
                  list(photos)[:4], think=True) or {}
    except Exception as e:
        log(f"[fast] the proofread did not run ({str(e)[:80]}) - the scanner's lines are used")
        return list(words)
    out = []
    for l in v.get("lines") or []:
        l = str(l).strip()
        if l and any(fuzz.ratio(norm(l), norm(w)) >= 70 or fuzz.partial_ratio(norm(l), norm(w)) >= 90 for w in words) \
                and l not in out:
            out.append(l)
    if len(out) < max(2, len(words) // 3):
        log(f"[fast] the proofread gave too few lines ({out}) - the scanner's lines are used")
        return list(words)
    log(f"[fast] the printed lines, proofread by the vision brain: {out}")
    return out


def words_back(png, words):
    """Share of the photos' words read back off a drawing (Apple's text reader)."""
    import measure as MS
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    if not words:
        return 1.0
    got = norm(" ".join(MS.read_lines(png) or []))
    return sum(1 for w in words if norm(w) in got) / len(words)


def size_text(w_mm, h_mm):
    dia = h_mm / math.pi
    return f"{w_mm:g} mm long and {dia:.1f} mm across, {w_mm / dia:.1f} times as long as it is wide"


DRAW_FACE = (
    "Picture 1 is a real photo of {product}, made around {year}. Make ONE clean, convincing studio product photo of "
    "exactly ONE of this item showing the SAME side of it that faces the camera in picture 1 - the same logo, panels, "
    "colors, bands and small print in the same places: lying on its side, long axis level and left to right, "
    "centered and filling most of the width, plain white background, soft even light, sharp focus, true colors, "
    "no glare, no other objects, no hands. Its true proportions: {size}. Print ONLY the words listed below, spelled "
    "exactly - where the photo's small print is too small to read, leave that spot plain; never invent small print, "
    "stickers, bars or boxes the photo does not show.{style}{words}{fix}")


def split_items(r, crop_dir, log):
    """A photo of several copies -> one reference per copy (skin.all_items: each outline on its own), each saved
    on its own. -> [refs]."""
    import skin
    import turnaround as T
    from PIL import Image
    out = []
    try:
        mask = T.photo_mask(r["file"], timeout=300)
        items = skin.all_items({"file": r["file"], "mask": mask})
    except Exception as e:
        log(f"[fast] {os.path.basename(r['file'])}: the copies could not be cut apart ({str(e)[:80]})")
        return out
    if len(items) < 2:
        return out
    os.makedirs(crop_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(r["file"]))[0]
    for k, (im, m) in enumerate(items[:6]):
        f = os.path.join(crop_dir, f"{base}_copy{k + 1}.png")
        a = np.asarray(im.convert("RGB")).astype(float)
        mm = (np.asarray(m) > 0.5)[..., None]
        Image.fromarray(np.where(mm, a, 255).astype(np.uint8)).save(f)   # the copy alone on white
        out.append(dict(r, file=f, look=dict(r.get("look") or {}, one_item=True), from_photo=r["file"]))
    log(f"[fast] {os.path.basename(r['file'])}: {len(out)} copies cut apart, each a view of its own")
    return out


def faces(good, vocab, log, most=8, want_ratio=None, extra=3, crop_dir=None, same=None):
    """The item's different printed sides, each from ONE clear photo of one copy: the photo read with the most words
    first, then the one whose words share least with it (2026-10-08 04:25: a sheet showing two sides at once was
    merged into one garbled side - the battery's big-logo side and its PowerCheck side). Each face carries the words
    read on ITS photo, spelled as two photos agree where they do. -> [(photo, [words])], at most 2."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    singles = [r for r in good if (r.get("look") or {}).get("one_item") and r.get("version", "all") == "all"]
    if crop_dir:                                             # several copies in one photo, each turned another way,
        for r in good:                                       # are the best evidence of the other sides (11:10: three
            if not (r.get("look") or {}).get("one_item"):    # standing batteries, three sides, were thrown away)
                for c in split_items(r, crop_dir, log):      # each copy is checked on its own: a photo of six can
                    if same is None or same(c["file"]) == "all":   # hold two versions (2026-10-09: a later italic-
                        singles.append(c)                    # logo Duracell beside the PowerCheck ones)
    singles = singles or good
    if want_ratio:                                           # a photo of the item in its own proportions only: a
        kept_ = []                                           # stubby one (seen end-on, or another size) is drawn
        for r in singles[:most * 3]:                         # stubby (2026-10-08 03:00: side 2 drawn 2.5 to 1 from
            q = drawn_ratio(r["file"])                       # its photo, three tries, for a 3.6 to 1 cell)
            if q is None or 0.8 * want_ratio <= q <= 1.25 * want_ratio:
                kept_.append(r)
            else:
                log(f"[fast] {os.path.basename(r['file'])}: the item shows {q:.1f} to 1 (it is {want_ratio:.1f} to 1) - not drawn from")
        singles = kept_ or singles
    read = []
    for r in singles[:most * 2]:
        try:
            lines = [l.strip() for l in (MS.read_lines(r["file"]) or []) if len(norm(l)) >= 3]
        except Exception:
            lines = []
        fixed = []
        for l in lines:                                      # ONLY words two photos agree on, in that spelling
            best = max(vocab, key=lambda v: fuzz.ratio(norm(v), norm(l)), default=None)   # (2026-10-08 01:10: a
            if best is not None and fuzz.ratio(norm(best), norm(l)) >= 80 and best not in fixed:   # misread "note"
                fixed.append(best)                                                             # was drawn huge)
        read.append((r, fixed))
    if not read:
        return []
    read.sort(key=lambda x: (-len(x[1]), -x[0].get("score", 0)))
    a = read[0]
    ta = {norm(w) for w in a[1]}
    other = None
    for r, ws in read[1:]:
        tb = {norm(w) for w in ws}
        if len(ws) >= 2 and len(ta & tb) / max(1, len(ta | tb)) < 0.3:
            other = (r, ws)
            break
    out = [(a[0]["file"], a[1])] + ([(other[0]["file"], other[1])] if other else [])
    if other:                                                # the views BETWEEN the two sides (13:24: two drawn sides
        tb = {norm(w) for w in other[1]}                     # left two stretches that a fill invented words on):
        both, sets = ta | tb, [ta, tb]                       # a photo sharing some words with them (so it can be
        cand = sorted(read[1:], key=lambda x: -min(len({norm(w) for w in x[1]} & ta), len({norm(w) for w in x[1]} & tb)))
        for r, ws in cand:                                   # placed by its matching features) but not the same view;
            t = {norm(w) for w in ws}                        # one sharing words with BOTH sides first: it sits between
            if r is other[0] or len(ws) < 2 or not (t & both):
                continue
            if all(len(t & q) / max(1, len(t | q)) < 0.7 for q in sets):
                out.append((r["file"], ws))
                sets.append(t)
            if len(out) >= 2 + extra:
                break
    log("[fast] the item's printed sides: " + " | ".join(f"{os.path.basename(f)}: {ws[:6]}" for f, ws in out))
    return out


def drawn_ratio(png):
    """Length to width of the item in a drawing, by its cut-out's principal axes (skin.shape_ratio). None if unknown."""
    import skin
    import turnaround as T
    from PIL import Image
    try:
        m = np.asarray(Image.open(T.photo_mask(png, timeout=300)).convert("L")) / 255.0
        return skin.shape_ratio(m)
    except Exception:
        return None


def draw(card, good, tex, along, around, R, log, fix="", tries=4, words=(), same=None):
    """Each printed side of the item drawn clean from ONE clear photo of that side, best of `tries` by the judge
    against that photo and by its words read back. -> (front, back or None, notes)."""
    import turnaround as T
    import vet as V
    product, year = display(card), card.get("year") or "its era"
    sheet = R.reference_sheet([r["file"] for r in good if r.get("version", "all") == "all"][:9] or
                              [r["file"] for r in good[:9]], os.path.join(tex, "refs_sheet.png"))
    st = size_text(along, around)
    fx = (" Fix these from the last try: " + "; ".join(fix)) if fix else ""
    vw, vh = 1344, 768
    fs = faces(good, list(words), log, want_ratio=along / (around / math.pi), crop_dir=os.path.join(tex, "copies"),
               same=same)
    if not fs:
        fs = [(good[0]["file"], list(words))]
    if len(fs[0][1]) < 4:                                    # no photo shows the printed side clearly: drawing from
        raise RuntimeError(                                  # a warnings strip (3 words) scored 1/10 - 13:24
            f"no photo shows the item's printed side clearly (the best reads {len(fs[0][1])} words: "
            f"{', '.join(fs[0][1][:4])}) - the photo hunt needs better listings")
    drawn, notes = [], {"tries": []}
    first_src = None
    for k, (photo, ws) in enumerate(fs):
        try:                                                 # the item alone on white: nothing else to copy
            mask = T.photo_mask(photo, timeout=300)
            import skin
            src = skin.cutout({"file": photo, "mask": mask}, os.path.join(tex, f"side{k + 1}_photo.png"))
        except Exception:
            src = photo
        turn = 0
        try:                                                 # lying down, like the drawing (05:15: drawn level from
            from PIL import Image                            # a standing photo, the judge called it mirrored), and
            im = Image.open(src)                             # its print the right way up: of the two turns, the one
            turns = (90, 270) if im.height > 1.3 * im.width else (0, 180)   # its words read in (text-orientation
            turn, read_, sc_ = upright(im, ws, turns)        # detection by reading, as Tesseract's OSD does) -
            if not read_ and k and first_src:                # no clear answer by reading: the turn
                turn = same_way(im, first_src, turns)        # whose bands run like side 1's (copper end where side
            if turn:                                         # 1 has it) - 2026-10-09: a copy turned upside down was drawn with
                flat = os.path.join(tex, f"side{k + 1}_level.png")   # mirrored garble, 3 tries x 2 sides every build
                im.rotate(turn, expand=True, fillcolor="white").save(flat)
                src = flat
                log(f"[fast] side {k + 1}: its photo turned {turn} degrees so its print reads the right way up "
                    f"({'by its words' if read_ else 'by its bands, like side 1' if k else 'as it lies'}; words read "
                    f"per turn {', '.join(f'{t}: {v:.0f}' for t, v in sc_.items())})")
        except Exception:
            pass
        if k == 0:
            first_src = src
        wd = (" The printed text, spelled exactly: " + ", ".join(f'"{w}"' for w in ws[:24]) + ".") if ws else ""
        best = None
        # a drawing that already matched its photo is KEPT across restarts (in the photo hunt's folder, kept on
        # resets): the same photo, turned the same way, with the same prompt and words is not drawn again - a restart
        # for a fix later in the line redrew all five sides, ~1.5 h, every time (2026-10-09)
        # The key is the photo itself (for a copy cut from a photo of several: that photo's bytes and the copy's
        # number - the cut-out's own pixels shift a little each time its outline is found again), its turn, the
        # prompt with its words, and the size. A drawing is kept only when it is good enough for what follows it:
        # side 1 must read back 3/4 of its words (the judge's words score is capped at that share - 8 needs 75%),
        # the other sides half their words (what label_from takes); all 7/10 against their photos.
        import hashlib
        import shutil
        bar_m, bar_w = (7, 0.75) if k == 0 else (7, 0.5)
        prompt_ = DRAW_FACE.format(product=product, year=year, size=st, fix=fx, words=wd, style="")
        cm = re.match(r"(.+)_copy(\d+)\.png$", os.path.basename(photo))
        parent = next((r["file"] for r in good if cm and os.path.splitext(os.path.basename(r["file"]))[0] == cm.group(1)),
                      None) if cm else photo
        try:
            pbytes = hashlib.md5(open(parent or photo, "rb").read()).hexdigest()
        except Exception:
            pbytes = ""
        key = hashlib.sha1((os.path.basename(photo) + "|" + pbytes + f"|{turn}|" + prompt_ + f"|{vw}x{vh}").encode()
                           ).hexdigest()[:16]
        cache_dir = os.path.join(R.WORK, "hunt", os.path.basename(os.path.dirname(os.path.abspath(tex))), "drawn")
        hit = os.path.join(cache_dir, key + ".json")
        from_cache = False
        try:
            c_ = json.load(open(hit))
            if os.path.exists(os.path.join(cache_dir, key + ".png")) and c_["match"] >= bar_m and c_["words"] >= bar_w:
                out = os.path.join(tex, f"side{k + 1}_1.png")
                shutil.copy(os.path.join(cache_dir, key + ".png"), out)
                best = ((True, c_["match"] + 5 * c_["words"]), out, c_["match"], c_["words"])
                from_cache = True
                log(f"[fast] side {k + 1}: its drawing from an earlier run matched its photo {c_['match']}/10 and read "
                    f"back {c_['words']:.0%} of its words - kept, not drawn again")
        except Exception:
            pass
        for t in range(0 if best else (tries if k < 2 else min(tries, 3))):
            out = os.path.join(tex, f"side{k + 1}_{t + 1}.png")
            # (no style picture: given side 1's drawing as a second picture, side 2 copied side 1's print - 05:55, four
            #  tries at 2/10. One look comes from matching the colors per band afterwards - match_bands)
            style_ref, sty = [], ""
            T.draw_from_photos(product, [src] + style_ref, out, width=vw, height=vh,
                               prefix=DRAW_FACE.format(product=product, year=year, size=st, fix=fx, words=wd, style=sty),
                               seed=int(time.time()) % 100000 + 37 * t)
            v = V.ask(V.model(), PICK_Q.format(product=product, year=year), [out, src], think=False) or {}
            m = int(v.get("match") or 0)
            wb = words_back(out, ws)
            ratio = drawn_ratio(out)                         # measured: a stubby drawing (a D cell's shape for an
            want = along / (around / math.pi)                # AA - 02:17) stretches its print when unrolled
            if ratio and not (0.8 * want <= ratio <= 1.25 * want):
                log(f"[fast] side {k + 1} try {t + 1} is drawn {ratio:.1f} to 1, the item is {want:.1f} to 1 - not used")
                m = min(m, 3)
            notes["tries"].append({"file": out, "side": k + 1, "match": m, "words": round(wb, 2), "wrong": v.get("wrong")})
            log(f"[fast] side {k + 1} drawing try {t + 1}: matches its photo {m}/10, {wb:.0%} of its words read back"
                + (f" ({'; '.join(v.get('wrong') or [])[:150]})" if v.get("wrong") else ""))
            score_ = (wb >= bar_w, m + 5 * wb)                # a try good enough for what follows ranks first
            if best is None or score_ > best[0]:              # (side 1 at 9/10 with 70% of its words can never
                best = (score_, out, m, wb)                   #  pass the words score; 8/10 with 80% can)
            if m >= max(8, bar_m) and wb >= max(0.6, bar_w):  # (side 1: 3/4 of its words, or it can never pass)
                break
        if best and not from_cache and best[2] >= bar_m and best[3] >= bar_w:   # (a fresh one good enough: kept)
            try:
                os.makedirs(cache_dir, exist_ok=True)
                shutil.copy(best[1], os.path.join(cache_dir, key + ".png"))
                json.dump({"match": best[2], "words": best[3], "photo": os.path.basename(photo)}, open(hit, "w"))
            except Exception:
                pass
        drawn.append(best)
        if best and best[2] < 7:
            log(f"[fast] side {k + 1}: no drawing reached 7/10 against its photo (best {best[2]}/10)")
    front = drawn[0]
    back = drawn[1] if len(drawn) > 1 and drawn[1][2] >= 7 and drawn[1][3] >= 0.5 else None
    if len(drawn) > 1 and not back:
        log("[fast] the other side's drawing did not match its photo - the front's bands carry round the back")
    extra = [d[1] for d in drawn[2:] if d and d[2] >= 7 and d[3] >= 0.5] if back else []
    if len(drawn) > 2:
        log(f"[fast] {len(extra)} of {len(drawn) - 2} views between the sides matched their photos")
    return front[1], back[1] if back else None, dict(notes, sheet=sheet, clear=fs[0][0], front_match=front[2],
                                                    front_words=front[3], extra=extra)


def upright(im, words, turns=(0, 180)):
    """Which of the turns puts the photo's print the right way up: the one whose read lines match the most letters of
    the item's known words (a reader reads upside-down print as junk or nothing). -> degrees to turn (0 = as is)."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    vocab = [norm(w) for w in words if len(norm(w)) >= 3]
    scores = {}
    for t in turns:
        rot = (im.rotate(t, expand=True, fillcolor="white") if t else im).convert("RGB")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = os.path.join(td, "turn.png")
            rot.save(tmp)
            try:
                lines = MS.read_lines(tmp, turns=(0,)) or []   # read AS turned (read_lines alone tries every turn)
            except Exception:
                lines = []
        score = 0.0
        for l in lines:
            n = norm(l)
            if len(n) < 3:
                continue
            m = max((fuzz.partial_ratio(n, v) for v in vocab), default=0) if vocab else 60
            if m >= 70:
                score += len(n) * m / 100
        scores[t] = score
    # decided only by a clear margin: Apple's reader reads upside-down print too, nearly as well (2026-10-09: side 1,
    # already the right way up, was turned 180 on a near tie) -> (turn, decided?, scores)
    order = sorted(scores, key=lambda t: -scores[t])
    a, b = scores[order[0]], scores[order[1]] if len(order) > 1 else 0.0
    # at least two words' worth of letters read (a lone 3-letter scrap decides nothing)
    return (order[0], True, scores) if a >= 8 and a >= 1.5 * b else (turns[0], False, scores)


def same_way(im, ref_png, turns=(0, 180)):
    """Of the turns, the one whose color along the item's length runs like the reference photo's (the copper end
    where side 1 has it): each picture's non-white pixels averaged per column into 48 steps, compared by correlation.
    -> degrees."""
    from PIL import Image
    def prof(img):
        a = np.asarray(img.convert("RGB").resize((48, 24)), float)
        keep = a.min(-1) < 235
        out = np.zeros((48, 3))
        for c in range(48):
            px = a[:, c][keep[:, c]]
            out[c] = px.mean(0) if len(px) else np.nan
        return out
    ref = prof(Image.open(ref_png))
    best, got = turns[0], -2.0
    for t in turns:
        p_ = prof(im.rotate(t, expand=True, fillcolor="white") if t else im)
        ok = ~np.isnan(p_).any(1) & ~np.isnan(ref).any(1)
        if ok.sum() < 8:
            continue
        x, y = p_[ok].ravel() - p_[ok].mean(), ref[ok].ravel() - ref[ok].mean()
        r = float((x * y).sum() / max(1e-9, np.sqrt((x * x).sum() * (y * y).sum())))
        if r > got:
            best, got = t, r
    return best


def view_words(art, cols):
    """The printed lines on one unrolled view with the label column each sits at: [(text, column)]. The print runs
    along the length (down the label's rows), so the strip is read turned a quarter, both ways, the way that reads
    more."""
    import measure as MS
    from PIL import Image
    if not len(cols):
        return []
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    im = Image.fromarray((np.clip(art[:, c0:c1], 0, 1) * 255).astype(np.uint8))
    cw = c1 - c0
    best = []
    for turn in (90,):                                       # the print reads from the top (plus) end down: one
        try:                                                 # turn, never the upside-down one (21:50 retype bug)
            got = MS.read_boxes(im.rotate(turn, expand=True))
        except Exception:
            got = []
        # turned 90 (counter-clockwise) a column x lands at row cw-1-x; turned 270 at row x
        lines = [(t, c0 + ((cw - 1) - cy * cw if turn == 90 else cy * cw)) for t, cx, cy in got]
        if sum(len(t) for t, _ in lines) > sum(len(t) for t, _ in best):
            best = lines
    return best


def overlap_ncc(va, sa, vb, sb, least=0.25, cols=24):
    """How well two placed views agree where both saw the label well: the normalized cross-correlation of their
    gray print over the shared columns (1 = the same print in the same place). None if they share too few columns."""
    if va.get("l") is None or vb.get("l") is None or va.get("wcol") is None or vb.get("wcol") is None:
        return None
    a, b = np.roll(va["l"], sa, axis=1), np.roll(vb["l"], sb, axis=1)
    # "seen well" relative to each view's own best column: the unroll's weights are a quality score that can top
    # out well under 0.3 (a soft photo) - a fixed 0.3 found no overlap at all and the check never ran (2026-10-09:
    # the later italic-logo Duracell was placed by its words again, unchecked)
    wa_, wb_ = np.asarray(va["wcol"], float), np.asarray(vb["wcol"], float)
    sa_ = np.roll(wa_ > max(0.05, least * wa_.max()), sa)
    sb_ = np.roll(wb_ > max(0.05, least * wb_.max()), sb)
    both = sa_ & sb_
    if both.sum() < cols:
        return None
    ga, gb = a.mean(-1), b.mean(-1)                          # the band colors out (each row's own mean over what
    ga = ga - ga[:, sa_].mean(1, keepdims=True)              # that view saw): the copper/black rows match in any two
    gb = gb - gb[:, sb_].mean(1, keepdims=True)              # views, only the print tells them apart
    ga, gb = ga[:, both].ravel(), gb[:, both].ravel()
    ga, gb = ga - ga.mean(), gb - gb.mean()
    den = float(np.sqrt((ga ** 2).sum() * (gb ** 2).sum()))
    return float((ga * gb).sum() / den) if den > 1e-9 else None


def by_print(va, vb, W, step=4, rows=4, least=0.25, floor=0.2, ratio=1.3):
    """Where view b sits relative to view a, by the print both show: normalized cross-correlation over every turn
    of b round the label (template matching, the standard registration measure), the band colors taken out first
    (each row's own mean) so only the print is compared, and only where both saw it. Kept only if the best spot is
    clear - at least `floor` and `ratio` x the best spot elsewhere (the ratio test of Lowe 2004, for one shift).
    2026-10-09: the meter side shared no word the scanner read with the others, was put opposite, and the label
    showed ALKALINE BATTERY / Test at / the meter twice. On that pair this finds the right spot (0.28 vs 0.19).
    -> (shift in columns, score, next best) or None."""
    if va.get("l") is None or vb.get("l") is None or va.get("wcol") is None or vb.get("wcol") is None:
        return None
    def prep(v):
        g = np.asarray(v["l"], float).mean(-1)[::rows, ::step]
        seen = np.asarray(v["wcol"])[::step] > 0.05
        if seen.sum() < 8:
            return None, None
        g = g - g[:, seen].mean(1, keepdims=True)
        return g, seen
    a, sa = prep(va)
    b, sb = prep(vb)
    if a is None or b is None:
        return None
    n = a.shape[1]
    need = max(8, int(least * min(sa.sum(), sb.sum())))
    score = np.full(n, -1.0)
    for s_ in range(n):
        both = sa & np.roll(sb, s_)
        if both.sum() < need:
            continue
        x = a[:, both].ravel()
        y = np.roll(b, s_, axis=1)[:, both].ravel()
        x, y = x - x.mean(), y - y.mean()
        den = float(np.sqrt((x * x).sum() * (y * y).sum()))
        if den > 1e-9:
            score[s_] = float((x * y).sum() / den)
    k = int(np.argmax(score))
    if score[k] < floor:
        return None
    gap = max(2, n // 40)                                    # the next best spot: away from the best one's slope
    far = np.array([min(abs(i - k), n - abs(i - k)) > gap for i in range(n)])
    r2 = float(score[far].max()) if far.any() else -1.0
    if score[k] < ratio * max(r2, 1e-6):
        return None
    return (k * step) % W, float(score[k]), r2


def place_by_words(views, W, log, least=5, tol=0.03, skip=(), need=2):
    """Where each view sits round the label: by the printed lines it shares with a view already placed - the same
    words are the same spot on the real label (2026-10-08 14:00: placed by matching shapes, the meter view found 18
    features and landed wrong; the logo side was assumed opposite the PowerCheck side and was not). The first view
    is the reference. -> {view index: column shift}."""
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    skips = [norm(k) for k in skip if len(norm(k)) >= 3]
    words = []
    for v in views:                                          # single words (a line runs along the length, so its
        ws = [(norm(x), c) for t, c in v.get("words") or [] for x in re.split(r"\s+", str(t))]   # words share its
        ws = [(x, c) for x, c in ws if len(x) >= least and not any(fuzz.ratio(x, k) >= 85 for k in skips)]
        #   (the item's own name - "DURACELL" - is printed in several places: no anchor; 20:10 it stacked the logo
        #    side on the PowerCheck side)                      column); a word read twice in one view ("DURACELL" in
        n = {}                                               # the logo and in "DURACELL INC.") says no one place
        for x, _ in ws:
            n[x] = n.get(x, 0) + 1
        words.append([(x, c) for x, c in ws if n[x] == 1])
    shifts = {0: 0}
    rejected = set()
    while True:
        best = None
        for j in range(len(views)):
            if j in shifts or j in rejected:
                continue
            cand = []
            for i, si in shifts.items():
                for a, ca in words[i]:
                    for b, cb in words[j]:
                        if fuzz.ratio(a, b) >= 88:
                            cand.append(((ca + si - cb) % W, a))
            if not cand:
                continue
            circ = lambda x, y: min(abs(x - y), W - abs(x - y))
            sup = [[c for c in cand if circ(c[0], d[0]) <= tol * W] for d in cand]
            grp = max(sup, key=len)
            ang_ = np.angle(np.mean([np.exp(2j * np.pi * c[0] / W) for c in grp])) * W / (2 * np.pi)
            if len({c[1] for c in grp}) < need:              # two different words that agree - or one long word
                wd1 = max((c[1] for c in grp), key=len)      # whose spot the PICTURES confirm: the two views agree
                ok1 = False                                  # do not disagree where they overlap (normalized
                if len(wd1) >= 8:                            # cross-correlation, the standard registration check).
                    rs = [overlap_ncc(views[i], shifts[i], views[j], int(round(ang_)) % W) for i in shifts]
                    rs = [r_ for r_ in rs if r_ is not None]  # 2026-10-09: the meter side shared only POWERCHECK
                    ok1 = not rs or max(rs) >= 0.1           # with the panel side, was put opposite, and the
                    if ok1:                                  # PowerCheck box was printed twice
                        log(f"[fast] view {j + 1}: one long word ({wd1}) places it" +
                            (f"; the pictures agree where they overlap ({max(rs):.2f})" if rs else ""))
                    else:                                    # the pictures contradict the word: never placed later
                        rejected.add(j)                      # by a guess either
                        log(f"[fast] view {j + 1}: its one shared word ({wd1}) is contradicted by the print where "
                            f"they overlap (agree {max(rs):.2f}) - left out")
                if not ok1:
                    continue
            ang = np.angle(np.mean([np.exp(2j * np.pi * c[0] / W) for c in grp])) * W / (2 * np.pi)
            if best is None or len(grp) > best[2]:
                best = (j, int(round(ang)) % W, len(grp), sorted({c[1] for c in grp}))
        if best is None:                                     # no shared words: the shared PRINT places it, if the
            reg = None                                       # pictures agree clearly at one spot (see by_print)
            for j in range(len(views)):
                if j in shifts or j in rejected:
                    continue
                for i in list(shifts):
                    got = by_print(views[i], views[j], W)
                    if got and (reg is None or got[1] > reg[2]):
                        reg = (j, (shifts[i] + got[0]) % W, got[1], got[2], i)
            if reg:
                j, sh, r_, r2, i = reg
                shifts[j] = sh
                log(f"[fast] view {j + 1} placed by the print it shares with view {i + 1} (pictures agree {r_:.2f}, "
                    f"next best spot {r2:.2f}): {sh * 360 // W} degrees round")
                continue
            back = next((k for k, v in enumerate(views) if k not in shifts and k not in rejected
                         and v.get("kind") == "back"), None)
            if back is not None:                             # nothing shared: the other side half a turn round (the
                rs = [r_ for r_ in (overlap_ncc(views[i], shifts[i], views[back], W // 2) for i in shifts)
                      if r_ is not None]                     # last resort) - unless it overlaps a placed view there
                if rs and max(rs) < 0.1:                     # and its print disagrees
                    rejected.add(back)
                    log(f"[fast] view {back + 1}: half a turn round, its print disagrees with the placed views "
                        f"(agree {max(rs):.2f}) - left out")
                    continue
                shifts[back] = W // 2                        # and the rest may chain off it
                log(f"[fast] view {back + 1} shares no printed words with the placed views - put opposite view 1")
                continue
            # any view still unplaced - by no words, no print - is LEFT OUT, never put in a guessed place: a guess put
            # the logo side over the meter side and the label showed the PowerCheck box twice (2026-10-09, 4cbbd2b)
            break
        j, sh, n, ws = best
        # the words agree - does the PRINT where the views overlap? A view whose print plainly disagrees there is
        # left out. (Not the guard against another VERSION: a later italic-logo Duracell shares its Patented panel
        # with the 1998 one and agreed 0.28 on the replay of the 2026-10-09 build - the Versions check before
        # drawing is that guard.)
        rs = [r_ for r_ in (overlap_ncc(views[i], shifts[i], views[j], sh) for i in shifts) if r_ is not None]
        if rs and max(rs) < 0.1:
            rejected.add(j)
            log(f"[fast] view {j + 1} shares words ({', '.join(ws[:3])}) but not the print where it overlaps the "
                f"placed views (agree {max(rs):.2f}) - left out")
            continue
        if not rs:
            log(f"[fast] view {j + 1}: no overlap with the placed views to check its print against")
        shifts[j] = sh
        log(f"[fast] view {j + 1} placed by {n} printed line(s) it shares with the others ({', '.join(ws[:3])}): "
            f"{sh * 360 // W} degrees round" + (f"; the print agrees where they overlap ({max(rs):.2f})" if rs else ""))
    return shifts


def pick_views(cands, log, seam=4.0, blend=16):
    """Which view each column of the label comes from: the one that saw it most squarely (its weight - the unroll's
    cos^2 of the angle from the camera), with a seam only where there is little print in both views - the view
    selection of multi-view texturing (Waechter, Moehrle & Goesele, "Let There Be Color!", ECCV 2014; Lempitsky &
    Ivanov 2007), here one row of choices around the label, so the exact best (Viterbi dynamic programming) is cheap.
    13:24: the first view's squeezed edge beat a later view's square-on print ("ALKALINE" read "ALAALING").
    -> (label H x W x 3, coverage H x W)."""
    H, W = cands[0][0].shape[:2]
    K = len(cands)
    wts = np.stack([np.asarray(w, float) for _, w in cands])           # K x W
    ok = wts > 0.05
    m = max(1e-6, float(wts.max()))
    unary = np.where(ok, 1.0 - wts / m, 1e3)                            # K views + one "unseen" choice
    unary = np.vstack([unary, np.where(ok.any(0), 1e3, 0.0)[None]])
    ink = []
    for px, _ in cands:                                                 # print in each column: mean edge strength
        g = px.mean(-1)
        ink.append(np.abs(np.diff(g, axis=1, append=g[:, -1:])).mean(0) + np.abs(np.diff(g, axis=0, append=g[-1:])).mean(0))
    ink.append(np.zeros(W))
    ink = np.stack(ink)
    ink = ink / max(1e-6, float(np.percentile(ink[:K][ok], 95))) if ok.any() else ink
    cost = unary[:, 0].copy()
    back = np.zeros((K + 1, W), int)
    for c in range(1, W):
        sw = seam * (ink[:, c][:, None] + ink[:, c][None, :])           # switching here cuts through this print
        np.fill_diagonal(sw, 0.0)
        tot = cost[None, :] + sw                                        # [to, from]
        back[:, c] = np.argmin(tot, axis=1)
        cost = tot[np.arange(K + 1), back[:, c]] + unary[:, c]
    pick = np.zeros(W, int)
    pick[-1] = int(np.argmin(cost))
    for c in range(W - 1, 0, -1):
        pick[c - 1] = back[pick[c], c]
    lab, cov = np.zeros((H, W, 3)), np.zeros((H, W))
    for k, (px, w) in enumerate(cands):
        sel = pick == k
        lab[:, sel] = px[:, sel]
        cov[:, sel] = np.maximum(np.asarray(w)[sel], 0.06)
    for c in range(1, W):                                    # a soft join where one view hands over to the next,
        k1, k2 = pick[c - 1], pick[c]                        # over the columns both saw (14:00: a hard seam split
        if k1 == k2 or K in (k1, k2):                        # the copper top)
            continue
        for d in range(-blend, blend):
            cc = c + d
            if 0 <= cc < W and ok[k1, cc] and ok[k2, cc]:
                t = (d + blend) / (2 * blend)
                lab[:, cc] = (1 - t) * cands[k1][0][:, cc] + t * cands[k2][0][:, cc]
    log("[fast] each column from the view that saw it most squarely: "
        + ", ".join(f"view {k + 1} {np.mean(pick == k):.0%}" for k in range(K)) + f", unseen {np.mean(pick == K):.0%}")
    return lab, cov


def match_bands(art, ref, edge):
    """Color transfer (Reinhard, Ashikhmin, Gooch, Shirley 2001: match the mean and spread of each channel in the
    Lab color space) done separately above and below the band edge, so side 2's copper becomes side 1's copper and
    its black side 1's black. -> art (H x w x 3, 0..1)."""
    try:
        from skimage import color
        to, back = color.rgb2lab, color.lab2rgb
    except Exception:                                        # (no scikit-image: the same transfer in RGB)
        to = back = (lambda x: x)
    out = art.copy()
    for a, b in ((0, edge), (edge, art.shape[0])):
        if b - a < 4:
            continue
        src, dst = to(np.clip(art[a:b], 0, 1)), to(np.clip(ref[a:b], 0, 1))
        ms, ss = src.reshape(-1, 3).mean(0), src.reshape(-1, 3).std(0) + 1e-6
        md, sd = dst.reshape(-1, 3).mean(0), dst.reshape(-1, 3).std(0) + 1e-6
        out[a:b] = np.clip(back((src - ms) / ss * sd + md), 0, 1)
    return out


def band_edge(art):
    """The row where the label's main band changes (a copper top meeting a black body): the biggest jump in the
    rows' mean color, smoothed, away from the ends. -> row index or None."""
    from scipy import ndimage
    H = art.shape[0]
    prof = ndimage.uniform_filter1d(art.mean(1), size=max(3, H // 60), axis=0)
    jump = np.linalg.norm(np.diff(prof, axis=0), axis=1)
    lo, hi = int(0.08 * H), int(0.92 * H)
    if hi <= lo:
        return None
    r = int(np.argmax(jump[lo:hi])) + lo
    return r if jump[r] > 0.05 else None


def label_from(front, back, along, around, tex, log, product="", words=(), year="its era", extra=()):
    """The production way a round label texture is made: the drawn views' straight-on middles (the camera saw
    them square - within 70 degrees of the middle, before the curve stretches the print) unrolled flat, each made
    with the light taken off each column by the unroll itself, the front centered, the other side opposite, the rest of each row its own background color
    (the row's median ink across both sides - never one side's edge carried round as stripes). No baked light:
    the 3D render lights it (2026-10-08 01:10: glare, edge stretch and green stripes baked into the label).
    -> (label png, all-seen png)."""
    import skin
    import turnaround as T
    from PIL import Image
    W = 2048
    H = int(round(W * along / around))
    views = []                                               # every drawn view, unrolled at its own place
    for i, f in enumerate([front] + ([back] if back else []) + list(extra or [])):
        try:
            got = skin.unroll_view({"file": f, "mask": T.photo_mask(f, timeout=300), "whole": True}, along, around, W, max_deg=70)
        except Exception as e:
            log(f"[fast] {os.path.basename(f)} could not be unrolled: {str(e)[:100]}")
            got = None
        if not got:
            continue
        l, w = got
        wcol = w.max(0)
        cols = np.where(wcol > 0.05)[0]
        if not len(cols):
            continue
        art = np.clip(l, 0, 1) * (wcol > 0.05)[None, :, None]
        if i < 2:
            Image.fromarray((art[:, cols.min():cols.max() + 1] * 255).astype(np.uint8)).save(os.path.join(tex, f"strip{i + 1}.png"))
        # (no generative "flatten" edit: asked to make the strip flat artwork, Qwen-Image-Edit redrew it as a
        #  picture of a battery - 2026-10-08 02:17. The unroll already takes the light off each column)
        views.append({"file": f, "l": art, "wcol": wcol, "cols": cols, "edge": band_edge(art[:, cols]),
                      "kind": "front" if i == 0 else ("back" if (back and i == 1) else "extra")})
    if not views:
        raise RuntimeError("the drawn item could not be unrolled onto the label")
    v0 = views[0]
    e0 = v0["edge"] if v0["edge"] is not None else H // 3
    art0 = v0["l"][:, v0["cols"]]
    for k, v in enumerate(views[1:], 2):                     # one battery: the bands at one height (03:55: two band
        if v["edge"] is not None and v0["edge"] is not None and abs(v["edge"] - v0["edge"]) < 0.15 * H:
            v["l"] = np.roll(v["l"], v0["edge"] - v["edge"], axis=0)        # heights), one ink per band (Reinhard
        v["l"][:, v["cols"]] = match_bands(v["l"][:, v["cols"]], art0[:, np.arange(len(v["cols"])) % art0.shape[1]], e0)
    log(f"[fast] {len(views)} drawn views unrolled; bands and colors matched to view 1")   # et al. 2001, per band)
    for v in views:
        v["words"] = view_words(v["l"], v["cols"])
    shifts = place_by_words(views, W, log, skip=re.findall(r"[A-Za-z0-9]+", product.split("(")[0])[:2])
    cands = []
    for k, v in enumerate(views):
        sh = shifts.get(k)
        if sh is None and k == 0:
            sh = 0
        if sh is None:
            log(f"[fast] view {k + 1} could not be placed by its words or its print - left out (never guessed)")
            continue
        cands.append((np.roll(v["l"], sh, axis=1), np.roll(v["wcol"], sh)))
    lab = cands[0][0].copy()
    cov = np.tile(np.asarray(cands[0][1]) > 0.05, (H, 1)).astype(float)
    if len(cands) > 1:                                       # each column from the view that saw it most squarely
        lab, cov = pick_views(cands, log)
    seen = cov > 0
    FILLED["share"] = float(seen.max(0).mean())
    log(f"[fast] the flat artwork covers {seen.max(0).mean():.0%} of the way around; each row's own background fills the rest")
    bg = np.stack([np.median(lab[r][seen[r]], axis=0) if seen[r].any() else np.zeros(3) for r in range(H)])
    from scipy import ndimage as _nd                         # the background changes only at a band's edge: each
    bg = _nd.median_filter(bg, size=(max(3, H // 20) | 1, 1), mode="nearest")   # row's color smoothed along the
    #                                                          length (a single row's text left ghost stripes)
    out = np.where(seen[..., None], lab, bg[:, None, :])
    e = max(2, int(0.015 * H))                               # the drawing's own rounded ends are not label: the
    out[:e] = out[e]                                         # first and last rows (the rolled lips) take the row
    out[-e:] = out[-e - 1]                                   # just inside (02:17: white lips at both ends)
    bg[:e], bg[-e:] = bg[e], bg[-e - 1]
    # a soft join (40 px) where the artwork meets the background, so no hard edge shows
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(seen)
    a = np.clip(dist / 40.0, 0, 1)[..., None]
    out = a * out + (1 - a) * bg[:, None, :]
    try:                                                     # the stretches no drawn view covers: the label's own
        out = quilt_fill(out, seen, log)                     # plain surface carried on (image quilting)
    except Exception as e:
        log(f"[fast] the uncovered stretches were not filled ({str(e)[:100]})")
    png = os.path.join(tex, "label.png")
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tex, "flat_ref.png"))  # the guide
    sharp = None
    try:                                                     # every matched printed line set again as real type,
        import retype                                        # crisp at the label's full size (16:30: the stitched
        sharp, rn = retype.retype(out, list(words), log, scale=2)   # letters were soft and blotchy at 4096 px)
    except Exception as e:
        log(f"[fast] the print could not be set again as type ({str(e)[:100]}) - the drawn print is sharpened instead")
    if sharp is not None:
        Image.fromarray((np.clip(sharp, 0, 1) * 255).astype(np.uint8)).save(png)
        im = Image.open(png).convert("RGB")
        if im.width < 4096:
            im = im.resize((4096, int(round(4096 * im.height / im.width))), Image.LANCZOS)
            im.save(png)
        log(f"[fast] the label texture is {im.width} x {im.height} px, its print set as type")
        cover = os.path.join(tex, "label_seen.png")
        Image.fromarray(np.full((H, W), 255, np.uint8)).save(cover)
        return png, cover
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(png)
    # saleable-asset resolution (Cody, 2026-10-08 01:22: "as high definition and as quality as the best saleable
    # assets"): Real-ESRGAN x4 (github.com/xinntao/Real-ESRGAN, tiled with overlap) and never under 4096 px around
    try:
        T.upscale(png, force=True)
    except Exception as e:
        log(f"[fast] the label was not sharpened ({str(e)[:80]})")
    im = Image.open(png).convert("RGB")
    if im.width < 4096:
        im = im.resize((4096, int(round(4096 * im.height / im.width))), Image.LANCZOS)
        im.save(png)
    log(f"[fast] the label texture is {im.width} x {im.height} px")
    cover = os.path.join(tex, "label_seen.png")
    Image.fromarray(np.full((H, W), 255, np.uint8)).save(cover)
    return png, cover


def roll_view(lab, center, out, vw=1344, vh=768):
    """The flat label wrapped back onto the item and seen from the side, column `center` facing the camera - the
    item lying down, its top (plus) end to the left, on white, like the drawn views (the inverse of
    skin.unroll_view). -> (png, the picture's item mask png)."""
    from PIL import Image
    H, W = lab.shape[:2]
    L = int(min(0.86 * vw, 0.8 * vh * math.pi * H / W))     # the item's length in the picture (a squat item: its
    #                                                          width across sets the scale)
    D = max(8, int(round(L * W / (math.pi * H))))            # its diameter: around / pi, to the length's scale
    x0, y0 = (vw - L) // 2, (vh - D) // 2
    img = np.ones((vh, vw, 3))
    msk = np.zeros((vh, vw))
    yy = (np.arange(D) + 0.5) / D * 2 - 1                    # -1..1 across the diameter
    phi = np.arcsin(np.clip(yy, -1, 1))                      # the angle round from the camera
    cols = (center - phi / (2 * math.pi) * W).astype(int) % W    # (this sense unrolls back onto the same columns:
    #                                                          round trip within 2% - tested 2026-10-08)
    rows = np.clip(((np.arange(L) + 0.5) / L * H).astype(int), 0, H - 1)
    face = lab[rows][:, cols]                                # L x D x 3: along x across
    shade = (0.62 + 0.38 * np.cos(phi))[None, :, None]       # soft studio light, darker toward the edges
    img[y0:y0 + D, x0:x0 + L] = np.transpose(face * shade, (1, 0, 2))
    msk[y0:y0 + D, x0:x0 + L] = 1
    nub = max(3, D // 4)                                     # the plus terminal's button at the top end
    img[vh // 2 - nub // 2: vh // 2 + nub // 2, x0 - nub // 2: x0] = 0.72
    msk[vh // 2 - nub // 2: vh // 2 + nub // 2, x0 - nub // 2: x0] = 1
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(out)
    mp = out[:-4] + "_mask.png"
    Image.fromarray((msk * 255).astype(np.uint8)).save(mp)
    return out, mp


FILLED = {}


def quilt_fill(out, seen, log, patch=64, overlap=16, seed=7):
    """The stretches round the label no drawn view covered, filled with the label's OWN plain surface - image
    quilting (Efros & Freeman, "Image Quilting for Texture Synthesis and Transfer", SIGGRAPH 2001): patches copied
    from print-free parts of the drawn views, each from the SAME rows (so the copper and the black bands carry on at
    their own heights), overlapped and feathered. Only the patches' fine grain (a high-pass) is quilted, on each
    row's own band color: whole patches carried their column's light and the meter's colors as blocks (tested on the
    06:49 label). Nothing is invented: no generative model draws here (2026-10-08:
    asked to finish the stretch with no print, Qwen-Image-Edit printed "DURACELL", "Pal", even "FINISHED" from its
    own instruction, on every try). -> out (H x W x 3)."""
    from scipy import ndimage
    H, W = out.shape[:2]
    seen_cols = seen.max(0) if seen.ndim == 2 else seen
    runs = gaps(seen_cols, least=0.0)
    if not runs:
        return out
    g = out.mean(-1)
    grad = ndimage.uniform_filter(np.abs(np.diff(g, axis=1, append=g[:, -1:])) + np.abs(np.diff(g, axis=0, append=g[-1:])), 7)
    thr = max(0.02, 2.5 * float(np.median(grad[:, seen_cols])))
    plain = (grad < thr) & seen_cols[None, :]
    # each row's band color: the plain pixels near the color most of the nearby rows have (the meter's green, yellow
    # and red are plain too, but a minority - first try, they streaked the fill), smoothed along the length
    sub = out[:, seen_cols][:, ::4]
    psub = plain[:, seen_cols][:, ::4]
    bg = np.zeros((H, 3))
    half = max(8, H // 40)
    for r in range(H):
        win = sub[max(0, r - half):r + half + 1][psub[max(0, r - half):r + half + 1]]
        if not len(win):
            win = sub[r]
        med = np.median(win, axis=0)
        row = sub[r][psub[r]] if psub[r].any() else sub[r]
        near = row[np.abs(row - med).sum(-1) < 0.15]
        bg[r] = np.median(near, axis=0) if len(near) else med
    bg = ndimage.gaussian_filter1d(bg, max(2, H // 300), axis=0)
    hp = out - ndimage.gaussian_filter(out, (3, 3, 0))       # the grain: no color, no light
    rng = np.random.default_rng(seed)
    acc, wsum = np.zeros((H, W, 3)), np.zeros((H, W))
    step = patch - overlap
    tent = lambda n: np.minimum(np.minimum(np.arange(n) + 1, np.arange(n)[::-1] + 1) / overlap, 1.0)
    ok_src = [c for c in np.where(seen_cols)[0] if seen_cols[np.arange(c, c + patch) % W].all()]
    used = fell = 0
    for start, width in runs:
        cols_all = (start - overlap + np.arange(width + 2 * overlap)) % W
        for j in range(0, len(cols_all), step):
            cols = cols_all[j:j + patch]
            for r0 in range(0, H, step):
                rows = np.arange(r0, min(H, r0 + patch))
                best, bf = None, -1.0
                for c in (rng.choice(ok_src, size=min(40, len(ok_src)), replace=False) if ok_src else []):
                    sc = (c + np.arange(len(cols))) % W
                    f = plain[np.ix_(rows, sc)].mean()
                    if f > bf:
                        best, bf = sc, f
                p_ = np.repeat(bg[rows][:, None, :], len(cols), axis=1)
                if best is not None and bf >= 0.97:
                    p_ = p_ + hp[np.ix_(rows, best)]
                    used += 1
                else:                                        # no print-free patch on these rows: the color alone
                    fell += 1
                wgt = tent(len(rows))[:, None] * tent(len(cols))[None, :]
                acc[np.ix_(rows, cols)] += p_ * wgt[..., None]
                wsum[np.ix_(rows, cols)] += wgt
    gap = ~seen_cols
    filled = np.where(wsum[..., None] > 0, acc / np.maximum(wsum, 1e-9)[..., None], out)
    d = ndimage.distance_transform_edt(np.tile(gap, (3, 1)))[1]          # crossfade into the drawn views' edges
    a = np.clip(d / 48.0, 0, 1)[None, :, None]
    out = np.where(gap[None, :, None], a * np.clip(filled, 0, 1) + (1 - a) * out, out)
    log(f"[fast] the {len(runs)} stretch(es) the drawn views did not cover, {gap.mean():.0%} of the way round, carry the "
        f"label's own plain surface on ({used} print-free patches, {fell} plain-color)")
    return out


# ------------------------------------------------------------ print on the label's rolled rims (its lips over the ends)
# The flat guide is unrolled from the SIDE, so print where the sleeve rolls over an end never reaches it - and the
# layout writer is told the ends are not label. The PowerCheck's second press dot sits there, on the minus end's rim
# (its own icon draws it as a half dot at the end, with an arrow pressing in from the end): missing on every build
# (2026-10-04 "the second white test dot"; Cody, 2026-10-10 05:25 "still missing a circle"). So the rims are asked
# about on their own, in the photos of this one version, read three times at most and kept only when two reads agree
# (self-consistency, Wang et al. 2022), and drawn on the label's lip zones, in line with the print they line up with.
RIMS_Q = """These are real photos of ONE version of {product}. Its printed label covers the side and rolls over the
rim at each end - the curved edge where the side turns into the end. Look closely at both rims in every photo.
End A: {a}. End B: {b}.
Is anything printed ON a rim - a dot, a ring, a band or another mark, in a color that is not the plain label color
there? Only print on the curved rim itself counts: a mark on the flat side, even close to the end, is NOT on the rim.
The bare metal end, its cap or button, glare, shine and reflections are not print. If no rim carries print, answer an
empty list.
Answer ONLY JSON: {{"marks": [{{"end": "A" or "B", "shape": "dot" or "ring" or "band" or "mark",
 "color": one of {colors},
 "size": its width compared with the item's width (0.1 small, 0.3 a third, 0.5 half),
 "beside": the line printed on the side that it lines up with along the item (at the same place round the item) -
           exactly one of: {lines} - or "none",
 "photos": in how many of the photos you can see it}}]}}"""


def lips(spec, along):
    """How far the label rolls over each end, as shares of its length in the artwork (reading orientation):
    (left, right). The lathe maps v = 0 to the label profile's FIRST point, and the artwork is turned so v = 1 is at
    its left (label_art) - so the left lip is the profile's last end, the right lip its first."""
    pts = [pt for p in spec.get("profile", []) if p["part"] == "label" for pt in p["pts"]]
    if len(pts) < 2 or not along:
        return 0.0, 0.0
    rmax = max(r for r, z in pts)

    def run(seq):                                            # from the end inward while the sleeve is still curling
        n = 0.0
        for a, b in zip(seq, seq[1:]):
            if a[0] >= rmax - 0.02:
                break
            n += math.dist(a, b)
        return n
    return run(pts[::-1]) / along, run(pts) / along


def _circ(a, b):
    """Distance round the label (0..1 down the artwork; its top and bottom edges meet when wrapped)."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def _row_of(name, lay):
    """Where round the label (0..1 down the artwork) the named printed line sits: the middle of the panel it is
    printed in (a meter box, a seal), else the middle of the line. None when no line of the layout is it."""
    from rapidfuzz import fuzz
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s or "").lower())
    if not norm(name) or norm(name) == "none":
        return None
    ts = [t for t in lay.get("texts", []) if t.get("text")]
    best = max(ts, key=lambda t: fuzz.ratio(norm(t["text"]), norm(name)), default=None)
    if not best or fuzz.ratio(norm(best["text"]), norm(name)) < 85:
        return None
    h, w = float(best.get("h") or 0.05), float(best.get("w") or 0.0)
    cy = float(best["y"]) + h / 2
    cx = float(best["x"]) - (w / 2 if best.get("align") == "center" else 0.0) + w / 2
    panels = [s for s in lay.get("shapes", []) if not s.get("base") and not s.get("lip")
              and s.get("type", "rect") == "rect" and (s.get("stroke") or s.get("fill"))
              and s["w"] * s["h"] < 0.5 and s["x"] <= cx <= s["x"] + s["w"] and s["y"] <= cy <= s["y"] + s["h"]]
    if panels:
        p = min(panels, key=lambda s: s["w"] * s["h"])
        return p["y"] + p["h"] / 2
    return cy


def _rim_color(c):
    import layout as LAY
    c = str(c or "").strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", c):
        return c
    for k, v in LAY.NAMED.items():
        if k in c.split() or k == c:
            return "#%02x%02x%02x" % v
    return None


def _rim_marks_of(raw, lay):
    """One read's answer made exact: the end, shape, ink, size, and the place round the label it lines up with
    (from the layout's own line or panel - a mark that lines up with nothing printed is not placed: never guessed)."""
    out = []
    for m in (raw or {}).get("marks") or []:
        if not isinstance(m, dict):
            continue
        end = str(m.get("end", "")).strip().upper()[:1]
        shape = str(m.get("shape", "")).strip().lower()
        col = _rim_color(m.get("color"))
        if end not in ("A", "B") or shape not in ("dot", "ring", "band", "mark") or not col:
            continue
        y = None if shape == "band" else _row_of(m.get("beside"), lay)
        if shape != "band" and y is None:
            continue
        try:
            size = float(m.get("size") or 0.3)
        except (TypeError, ValueError):
            size = 0.3
        out.append({"end": end, "shape": shape, "color": col, "size": min(max(size, 0.08), 0.6), "y": y,
                    "beside": m.get("beside")})
    return out


def _same_rim_mark(a, b):
    import labelart
    import layout as LAY
    return (a["end"] == b["end"] and a["shape"] == b["shape"]
            and LAY._family(labelart.rgb(a["color"])) == LAY._family(labelart.rgb(b["color"]))
            and (a["y"] is None) == (b["y"] is None) and (a["y"] is None or _circ(a["y"], b["y"]) <= 0.12))


def _agreed(reads):
    """The marks at least two reads report (one per mark: the middle place and size of the reads that saw it)."""
    kept = []
    for i, rd in enumerate(reads):
        for m in rd:
            if any(_same_rim_mark(m, k) for k in kept):
                continue
            hits = [m] + [next(o for o in r2 if _same_rim_mark(m, o)) for j, r2 in enumerate(reads)
                          if j != i and any(_same_rim_mark(m, o) for o in r2)]
            if len(hits) >= 2:                               # this read and at least one other
                ys = [x["y"] for x in hits if x["y"] is not None]
                kept.append(dict(m, y=float(np.median(ys)) if ys else None,
                                 size=float(np.median([x["size"] for x in hits]))))
    return kept


def _same_sets(a, b):
    return all(any(_same_rim_mark(x, y) for y in b) for x in a) and all(any(_same_rim_mark(y, x) for x in a) for y in b)


def rim_shapes(marks, lay, lip_lr, along, around, log):
    """The agreed rim marks as layout shapes on the lip zones. A mark that is the same as a mark already printed on
    the SIDE near that end (same ink and shape, in line with it) is the side mark misread as a rim mark: left out."""
    import labelart
    import layout as LAY
    D = around / math.pi                                     # the item's width
    out = []
    for m in marks:
        zone = (0.0, lip_lr[0]) if m["end"] == "A" else (1.0 - lip_lr[1], 1.0)
        if (zone[1] - zone[0]) * along < 0.3:
            log(f"[fast] a {m['color']} {m['shape']} was seen on end {m['end']}'s rim, but this label does not roll over "
                f"that end - not drawn")
            continue
        xm = (zone[0] + zone[1]) / 2
        fam = LAY._family(labelart.rgb(m["color"]))
        twin = None
        for s in lay.get("shapes", []):
            if s.get("base") or s.get("lip") or not s.get("fill") or s.get("type", "rect") not in ("rect", "ellipse"):
                continue
            if LAY._family(labelart.rgb(s["fill"])) != fam or (s.get("type") == "ellipse") != (m["shape"] in ("dot", "ring")):
                continue
            if abs(s["x"] + s["w"] / 2 - xm) <= 0.25 and (m["y"] is None or _circ(s["y"] + s["h"] / 2, m["y"]) <= 0.15):
                twin = s
                break
        if twin:
            log(f"[fast] the {m['shape']} reported on end {m['end']}'s rim is the one printed on the side next to it - "
                f"not drawn twice")
            continue
        d = m["size"] * D
        if m["shape"] == "band":
            shp = [{"type": "rect", "x": zone[0], "y": 0.0, "w": zone[1] - zone[0], "h": 1.0, "fill": m["color"],
                    "stroke": None, "stroke_w": 0.0}]
        else:
            w = d / along if m["shape"] != "mark" else min(d / along, zone[1] - zone[0])
            h = d / around
            ring = m["shape"] == "ring"
            one = {"type": "ellipse" if m["shape"] in ("dot", "ring") else "rect", "x": xm - w / 2, "y": m["y"] - h / 2,
                   "w": w, "h": h, "fill": None if ring else m["color"], "stroke": m["color"] if ring else None,
                   "stroke_w": 0.004 if ring else 0.0}
            shp = [one]
            if one["y"] < 0 or one["y"] + h > 1:              # across the wrap: the rest at the other edge (they meet)
                shp.append(dict(one, y=one["y"] + (1.0 if one["y"] < 0 else -1.0)))
        for s in shp:
            s["lip"] = True                                  # on the rim: not part of the side the rounds compared
        out += shp
        log(f"[fast] printed on end {m['end']}'s rim: a {LAY._name(labelart.rgb(m['color']))} {m['shape']}"
            + (f", in line with '{m.get('beside')}'" if m.get("beside") else "") + " - drawn on the label where it rolls over")
    return out


def rim_marks(product, photos, lay, lip_lr, along, around, log, cache=None, model=None, ask=None):
    """-> layout shapes for the print on the label's rolled rims (an empty list when none is agreed)."""
    import hashlib
    import labelart
    import layout as LAY
    if not photos or not (lip_lr[0] * along >= 0.3 or lip_lr[1] * along >= 0.3):
        return []
    base = [s for s in lay.get("shapes", []) if s.get("base")]

    def end_says(left):
        at = 0.0 if left else 1.0
        band = next((s for s in base if s["x"] <= at <= s["x"] + s["w"] and s.get("fill")), None)
        col = LAY._name(labelart.rgb(band["fill"])) if band else None
        ts = sorted([t for t in lay.get("texts", []) if t.get("text")],
                    key=(lambda t: float(t["x"])) if left else (lambda t: -(float(t["x"]) + float(t.get("w") or 0))))
        near = " and ".join(f"'{t['text']}'" for t in ts[:2])
        return col, near
    (ca, na), (cb, nb) = end_says(True), end_says(False)
    say = lambda c, n, other: (f"the end where the label is {c}" if c and c != other else "one end") + \
        (f" - the side print nearest it is {n}" if n else "")
    q = RIMS_Q.format(product=product, a=say(ca, na, cb), b=say(cb, nb, ca),
                      colors=", ".join(LAY.NAMED), lines=", ".join(f'"{t["text"]}"' for t in lay.get("texts", [])))
    md5 = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
    key = hashlib.md5((q + "|".join(md5(f) for f in photos)).encode()).hexdigest()[:16]
    store = {}
    if cache:
        try:
            store = json.load(open(cache))
        except Exception:
            store = {}
    raws = store.get("reads", []) if store.get("key") == key else []
    ask = ask or (lambda text, pics, temp: LAY._ask(model or __import__("vet").model(), text, pics, temp=temp))
    orders = [list(photos), list(photos)[::-1], list(photos)[1:] + list(photos)[:1]]
    reads = [_rim_marks_of(r, lay) for r in raws]
    for k in range(len(raws), 3):
        if len(reads) >= 2 and _same_sets(reads[0], reads[1]):
            break
        try:
            raw = ask(q, orders[k], 0.2 if k == 0 else 0.6)
        except Exception as e:
            log(f"[fast] the rims could not be read ({str(e)[:80]})")
            continue
        raws.append(raw)
        reads.append(_rim_marks_of(raw, lay))
        if cache:
            try:
                json.dump({"key": key, "reads": raws}, open(cache, "w"), indent=1)
            except Exception:
                pass
    if len(reads) < 2:
        log("[fast] the rims were not read twice - nothing drawn on them (never guessed)")
        return []
    agreed = _agreed(reads)
    if not agreed:
        log(f"[fast] print on the rolled rims: none that two reads agree on ({len(reads)} reads)")
        return []
    return rim_shapes(agreed, lay, lip_lr, along, around, log)


def gaps(seen_cols, least=0.03):
    """The runs of label columns no drawing covered (wrapping round) -> [(start, width)], widest first."""
    W = len(seen_cols)
    if seen_cols.all() or not seen_cols.any():
        return []
    s = int(np.argmax(seen_cols))                            # start the walk on a covered column
    runs, i = [], 0
    while i < W:
        c = (s + i) % W
        if not seen_cols[c]:
            j = i
            while j < W and not seen_cols[(s + j) % W]:
                j += 1
            if j - i >= least * W:
                runs.append(((s + i) % W, j - i))
            i = j
        else:
            i += 1
    return sorted(runs, key=lambda r: -r[1])


def label_art(product, tex, words, along, around, log, rounds=4, least=6, photos=(), lip_lr=(0.0, 0.0), rims=None):
    """The label made flat from the start, the way label artwork is made (Cody, 2026-10-08 21:57: "your method is
    still fucked" - stitched curved drawings, read back by a scanner and retyped, carried blur, seams, misreads and
    upside-down type). The stitched label is only the GUIDE: the vision brain writes the layout from it (bands,
    panels, meter, dots, every line from the proofread words - layout.py), labelart.py draws it crisp, the two are
    compared and the layout corrected, round after round. -> label png in the map's layout, or None when the
    drawn layout matches the guide under `least`/10 (the stitched label is kept)."""
    import layout as LAY
    from PIL import Image
    guide = os.path.join(tex, "flat_ref.png")
    if not os.path.exists(guide) or not words:
        return None
    g = Image.open(guide).convert("RGB")
    ga = np.asarray(g).astype(float) / 255.0
    Wg = ga.shape[1]
    ink = np.abs(np.diff(ga.mean(-1), axis=1, append=ga.mean(-1)[:, -1:])).mean(0)   # print in each column round
    from scipy import ndimage
    ink = ndimage.uniform_filter1d(ink, size=max(9, Wg // 40), mode="wrap")
    quiet = ink <= ink.min() + 0.15 * (ink.max() - ink.min())
    runs = gaps(~quiet, least=0.0) if not quiet.all() else [(0, Wg)]   # stretches of plain columns (wrapping)
    st, wd_ = runs[0] if runs else (int(np.argmin(ink)), 1)
    seam = (st + wd_ // 2) % Wg                              # the middle of the widest plain stretch: the seam goes there,
    ga = np.roll(ga, -seam, axis=1)                          # so nothing printed is cut by the label's two edges
    log(f"[fast] the label's seam is put at the plainest place round ({seam * 360 // Wg} degrees)")   # (05:05: the
    read = os.path.join(tex, "flat_ref_reading.png")         # logo sat on the edge - "DURACE", ALKALINE BATTERY
    Image.fromarray((ga * 255).astype(np.uint8)).rotate(90, expand=True).save(read)   # twice). Reading orientation:
    out_dir = os.path.join(tex, "art")                       # the plus end at the left
    try:
        png, mr, score = LAY.make(product, read, list(words), along, around, out_dir, rounds=rounds, log=log,
                                  typical=["each of the listed lines printed exactly once - never the same line twice",
                                           "each panel, box, meter and mark printed once: where two photos overlap, "
                                           "the picture can show the same box twice side by side - draw it once",
                                           "nothing crosses the top or bottom edge (they meet when wrapped)"])
    except Exception as e:
        log(f"[fast] the flat label artwork could not be made ({str(e)[:120]}) - the stitched label is kept")
        return None
    log(f"[fast] the flat label artwork matches the guide {score}/10")
    if (score or 0) < least:
        log(f"[fast] the artwork is under {least}/10 - the stitched label is kept")
        return None
    try:                                                     # print on the rolled rims, which the guide can't show
        import labelart
        lay = json.load(open(os.path.join(out_dir, "layout.json")))
        add = rim_marks(product, list(photos), lay, lip_lr, along, around, log, cache=rims)
        if add:
            lay["shapes"] = [s for s in lay.get("shapes", []) if not s.get("lip")] + add
            json.dump(lay, open(os.path.join(out_dir, "layout.json"), "w"), indent=1)
            png, _ = labelart.render(lay, out_dir, px=4096, name="label")
    except Exception as e:
        log(f"[fast] the rims could not be checked for print ({str(e)[:120]})")
    art = Image.open(png).convert("RGB").rotate(-90, expand=True)   # back to the map: rows from the plus end
    # (NOT turned back to the guide's old place round: that put the seam back through the print - 07:05, ALKALINE
    #  BATTERY cut at both edges. Which side faces the front does not matter; the seam stays on the plain stretch)
    if art.width < 4096:
        art = art.resize((4096, int(round(4096 * art.height / art.width))), Image.LANCZOS)
    dst = os.path.join(tex, "label.png")
    art.save(dst)
    log(f"[fast] the label is the flat artwork, {art.width} x {art.height} px")
    return dst


def unknown_words(png, vocab):
    """Words read off the finished label that no real photo carries (a made-up word, a misread drawn as print)."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    known = {norm(t) for v in vocab for t in re.findall(r"[A-Za-z0-9]+", v) if len(t) >= 2}
    for v in vocab:                                          # two printed words read as one ("BEST IF" -> "BESTIF")
        ts = re.findall(r"[A-Za-z0-9]+", v)
        known |= {norm(a + b) for a, b in zip(ts, ts[1:])}
    out = []
    for line in MS.read_lines(png) or []:
        for t in re.findall(r"[A-Za-z]{4,}", line):            # (3-letter scraps of real print read as noise)
            if not any(fuzz.ratio(norm(t), k) >= 85 for k in known):
                out.append(t)
    return out


def shape_spec(cid, card, d, R, log):
    """The exact real-size shape: a measured master shape, else the kit's standard size. -> (spec path, spec)."""
    import kits
    master = R.jload(os.path.join(HERE, "families.json"), {}).get(cid, {})
    sp = os.path.join(HERE, "shapes", "specs", master.get("shape", "") + ".json")
    if master.get("shape") and os.path.exists(sp):
        return sp, json.load(open(sp))
    kit_name = (card.get("family_lib") or {}).get("family", "")
    variant, why = kits.pick_variant(kits.get(kit_name), card)
    spec = kits.spec_for(kit_name, variant)
    if not spec:
        raise RuntimeError(f"no exact shape for {kit_name or 'this kind'} {variant or ''} - the full build is needed")
    log(f"[fast] {kit_name} {variant}: the exact shape from its standard size ({why})")
    sp = os.path.join(d, "shape.json")
    json.dump(spec, open(sp, "w"), indent=1)
    return sp, spec


def studio_views(glb, d, R, log):
    """Four sides of the finished model on one sheet: the phone viewer's pictures, else Blender's studio ones."""
    import subprocess
    try:                                                     # in its own process: the photo hunt's browser runs in
        import sys                                           # this one, and a second Playwright here refused ("Sync
        r = subprocess.run([sys.executable, "-c",            # API inside the asyncio loop" - 14:00)
                            "import sys, json; sys.path.insert(0, sys.argv[1]); import viewshot; "
                            "print(json.dumps(viewshot.shoot(sys.argv[2], sys.argv[3])[0]))",
                            HERE, glb, os.path.join(d, "check")], capture_output=True, text=True, timeout=900)
        shots = json.loads((r.stdout or "null").strip().splitlines()[-1]) if r.stdout.strip() else None
        if shots:
            return shots
        raise RuntimeError((r.stderr or "no pictures").strip().splitlines()[-1][:120] if r.stderr.strip() else "no pictures")
    except Exception as e:
        log(f"[fast] viewer pictures skipped ({str(e)[:80]}) - studio pictures")
    subprocess.run([R.PY, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(d, "view.png"), "0,90,180,270"],
                   check=True, capture_output=True)
    out = os.path.join(d, "views.jpg")
    R.sheet_views([os.path.join(d, f"view_{a:03d}.png") for a in (0, 90, 180, 270)], out)
    return out


def applies(cid, card, R):
    """Round items go this way (a measured master shape, or the card's round route)."""
    return bool(R.jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape")) or card.get("route") == "round"


def build(cid, card, d, R):
    """The whole build, five steps. R is the run module (status, boundary, Blender, filing)."""
    import shutil
    import skin
    import vet as V
    from PIL import Image
    log = R.say
    product = card["product"]
    mdir = os.path.join(d, "model")
    tex = os.path.join(d, "texture")
    os.makedirs(tex, exist_ok=True)
    os.makedirs(mdir, exist_ok=True)
    R.boundary(cid, "step")
    R.status(cid, product=product, route="round", step="1/5 reference photos: eBay listings (every side of one copy) and Google")
    try:                                                     # the era's own name and look ("90s Duracell PowerCheck")
        import cards
        ev = cards.era_version(cid, card, V.model(), log=log) or {}
        card["era_names"] = [str(n) for n in (ev.get("names") or []) if str(n).strip()][:3]
        log(f"[fast] in its era it was sold as: {', '.join(card['era_names']) or '(unknown)'}")
    except Exception as e:
        log(f"[fast] the era's own name could not be worked out ({str(e)[:80]})")
    refs = unique_refs(references(cid, card, R, log))
    R.boundary(cid, "step")
    R.status(cid, step=f"2/5 one quick look at each of {len(refs)} photos: is it this item, which side")
    R.make_room("judging")
    good = sort_refs(refs, card, R, log)
    json.dump(refs, open(os.path.join(R.WORK, "hunt", cid, "fast_refs.json"), "w"), indent=1)
    if not good:
        raise RuntimeError("no photo of this item was found - add one to ~/crushed-render/remaster/refs-mine as "
                           f"{cid}_1.jpg")
    if not card.get("family_lib") and not R.jload(os.path.join(HERE, "families.json"), {}).get(cid, {}).get("shape"):
        import families
        families.classify(card, good[0]["file"], V.model(), log=log)
    sp, spec = shape_spec(cid, card, d, R, log)
    along, around = skin.label_size(spec)
    R.status(cid, step="2/5 one version only: each photo compared with the clearest one")
    versions = Versions(cid, card, good, R, log)
    good = versions.keep(good)
    words = photo_words(good, log)
    whole = [g for g in good if g.get("version", "all") == "all"]
    words = proofread(words, [g["file"] for g in whole if g.get("look", {}).get("one_item")][:4] or [g["file"] for g in whole[:4]],
                      card, log)
    fix, last = [], None
    for rnd in range(2):
        R.boundary(cid, "step")
        R.status(cid, step=f"3/5 drawing the item from {min(len(good), 9)} photos" + (" (again: no drawing matched its photo)" if rnd else ""))
        R.make_room("drawing")
        front, back, dn = draw(card, good, tex, along, around, R, log, fix=fix, words=words, same=versions.same)
        if dn["front_match"] < 6 or dn["front_words"] < 0.5:     # nothing that does not match is built or filed
            fix = [f"the drawing must match the real item and carry its real words (it scored {dn['front_match']}/10, "
                   f"{dn['front_words']:.0%} of the words)"]
            last = {"realism": 0, "era": 0, "words": 0, "fix": fix, "shots": dn["sheet"], "front": front, "back": back}
            log(f"[fast] no drawing matched well enough (best {dn['front_match']}/10, {dn['front_words']:.0%} of the words) - drawn again")
            continue
        FILLED.clear()
        png, cover = label_from(front, back, along, around, tex, log, product=display(card), words=words,
                                year=card.get("year") or "its era", extra=dn.get("extra"))
        rim_pics = list(dict.fromkeys(list(versions.sheet_files or []) + [g["file"] for g in whole
                                                                          if "_copy" not in os.path.basename(g["file"])]))[:5]
        made = label_art(display(card), tex, words, along, around, log, photos=rim_pics, lip_lr=lips(spec, along),
                         rims=os.path.join(R.WORK, "hunt", cid, "rims.json"))
        if made:                                             # the artwork prints the whole label: the share the
            png = made                                       # stitched guide's views covered is no cap on it
            FILLED["share"] = 1.0                            # (09:00: realism held at 6 by the guide's 70%)
            try:                                             # its MEASURED faults left at the end (text on text,
                FILLED["art_defects"] = json.load(open(os.path.join(tex, "art", "defects.json"))).get("hard") or []
            except Exception:                                # unreadable text, a line printed twice): never kept
                FILLED["art_defects"] = []                   # with any of them, whatever the judge says
        mr = R.mr_from_bands(png, png, cover, tex, {})
        shutil.copy(png, os.path.join(d, "label.png"))
        shutil.copy(mr, os.path.join(d, "label_mr.png"))
        R.boundary(cid, "step")
        R.status(cid, step="4/5 Blender: real-size mesh, UV map, the drawn label, materials, insides; every format")
        R.run_blender("lathe.py", sp, mdir, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png"))
        for ext in ("glb", "fbx", "usdc", "blend"):
            p = os.path.join(mdir, spec["id"] + "." + ext)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(mdir, cid + "." + ext))
        R.run_blender("contract.py", os.path.join(mdir, cid + ".blend"), mdir, cid, str(card.get("mat") or ""))
        glb = os.path.join(mdir, cid + ".glb")
        R.finish_files(cid, d)
        R.boundary(cid, "step")
        R.status(cid, step="5/5 the judge: realistic, right for its era, real words")
        shots = studio_views(glb, d, R, log)
        R.make_room("judging")
        close = os.path.join(d, "check", "viewer_close.jpg")   # the judge looks CLOSE (01:10: thumbnails hid it)
        if not (os.path.exists(close) and os.path.getmtime(close) > time.time() - 3600):
            vs = [os.path.join(d, f"view_{a:03d}.png") for a in (0, 180)]
            if all(os.path.exists(p) for p in vs):
                close = os.path.join(d, "close_views.jpg")
                R.sheet_views(vs, close, cell=(900, 1200))
            else:
                close = shots
        all_round = os.path.join(d, "check", "viewer_around.jpg")
        if not (os.path.exists(all_round) and os.path.getmtime(all_round) > time.time() - 3600):
            all_round = shots
        pics = [close, all_round, dn["sheet"]]
        v = V.ask(V.model(), JUDGE_Q.format(product=display(card), year=card.get("year") or "its era"), pics,
                  think=True) or {}
        sc = {k: int(v.get(k) or 0) for k in ("realism", "era", "words")}
        sc["words"] = min(sc["words"], int(round(10 * dn["front_words"])))   # the words are MEASURED, not only judged
        bad = unknown_words(os.path.join(d, "label.png"), words)
        if bad:                                              # ANY made-up word on the label fails it (13:24: the judge
            sc["words"] = min(sc["words"], 4)                # passed "Pal", "POWEDCHECKIN", "PRESS DBTS TO TEST")
            v.setdefault("fix", []).append("made-up words on the label: " + ", ".join(bad[:6]))
        share = FILLED.get("share", 1.0)                     # measured, not judged: drawn from real views at least
        if share < 0.75:                                     # three quarters round (the rest is the label's own plain
            sc["realism"] = min(sc["realism"], 6)            # surface, quilted - no invented print)
            v.setdefault("fix", []).append(f"only {share:.0%} of the label was drawn from real views")
        if FILLED.get("art_defects"):                        # measured faults on the label art: not kept (the judge
            sc["realism"] = min(sc["realism"], 7)            # passed a label with a doubled box - 2026-10-09)
            v.setdefault("fix", []).extend(FILLED["art_defects"][:4])
            log(f"[fast] measured faults left on the label artwork: {'; '.join(FILLED['art_defects'][:4])[:300]}")
        log(f"[fast] {share:.0%} of the label was drawn from real views")
        log(f"[fast] words on the finished label no photo carries: {bad[:8] or 'none'}")
        log(f"[fast] the judge: realism {sc['realism']}/10, era {sc['era']}/10, words {sc['words']}/10"
            + (f" - fix: {'; '.join(v.get('fix') or [])[:300]}" if v.get("fix") else ""))
        last = dict(sc, fix=v.get("fix") or [], shots=shots, front=front, back=back)
        json.dump(last, open(os.path.join(d, "fast_verdict.json"), "w"), indent=1)
        if all(x >= PASS for x in sc.values()):
            R.status(cid, verdict={"pass": True, **sc}, views=os.path.relpath(shots, R.WORK),
                     ref=os.path.relpath(dn["clear"], R.WORK), label=os.path.relpath(os.path.join(d, "label.png"), R.WORK))
            r = R.file_away(cid, d)
            if not r.get("ok"):
                R.status(cid, step=f"stopped: delivery check failed: {r.get('why')}"[:300], ok=False)
            return last
        # the drawings matched their photos: they are kept, never redrawn with the judge's notes (09:40: notes about
        # the 3D ends - "make the top a raised button" - put into the drawing prompt took side 1 from 10/10 to 2/10).
        # Keep what came out right; the judge's notes are for the workflow, shown on the page.
        break
    R.status(cid, step=f"failed the realism check: the judge (realism {last['realism']}, era {last['era']}, words {last['words']}): "
                       + "; ".join(last["fix"])[:200], ok=False, views=os.path.relpath(last["shots"], R.WORK))
    return last
