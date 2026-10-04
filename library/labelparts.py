"""THE LABEL'S MISSING PARTS: your AI notices what its label lacks and goes and finds it (Cody, 2026-10-03: "it may be
missing more on the label than you think ... It should be able to realize this stuff and correct it").

The Duracell's label had only the side facing the camera in the pick: no size, no MN 1500 LR6 1.5 VOLTS, no caution
line, no Made in U.S.A. - no photo used showed the back, and nothing is ever printed that wasn't read off a photo.
So the label is checked against what every label of its kind carries (the kit's zone "expect" list), and for each
missing part your AI looks:
  1. through the photos already found for the item (the dossier's): flat or peeled labels first, then backs
  2. in a few new searches made for exactly what is missing (the back of the label, a peeled label, the caution...)
Words are read twice from each photo (run.label_words). From a flat or peeled label of this very item every line
counts (but a second date code never replaces the item's own); from any other photo only lines that ARE a missing
part. Every word keeps its receipt (which photo, which web page). What still can't be found is written down.

    added, receipts, still = labelparts.find(cid, dos, words, "cylindrical_cell", use, quick, read, log)
"""
import os
import re
import time

VERSION = 1                  # bump when the hunt's questions or filters change (a kept result is keyed on it)

SEARCHES = 4                     # new Google searches for the missing parts, at most
MOST_PHOTOS = 8                  # photos read for the missing parts, at most (two reads each)


def expected(kit_name, zone="label"):
    """What a zone of this kind of thing (nearly) always carries: [{"what", "pattern", "search"}]."""
    import kits
    for z in kits.zones(kits.get(kit_name or "")):
        if z.get("name") == zone:
            return list(z.get("expect") or [])
    return []


def missing(words, expect):
    """The expected parts no word matches."""
    text = "\n".join(str(w) for w in words)
    return [e for e in expect if not re.search(e["pattern"], text, re.I)]


def _overlap(ys, lo, hi):
    return not ys or (min(ys) <= hi and max(ys) >= lo)


def candidates(dos, skip=()):
    """Photos already found for the item that could show other parts of its label: the same product line, a real
    photo or a flat (peeled) label, from about the same years - flat labels first, then the same item, then backs."""
    idn = dos.get("identity") or {}
    era = idn.get("years") or []
    lo, hi = (era[0] - 6, era[-1] + 6) if era else (0, 9999)
    line_words = [w for w in re.findall(r"[a-z0-9]+", f"{idn.get('line', '')} {idn.get('variant', '')}".lower())
                  if len(w) >= 4]

    def ours(p, q):
        """This photo shows OUR product: the quick look says the exact item, or the careful look matched it, or the
        product it names carries our line's own words (a "Mallory mercury battery" said to be the same line by a
        quick glance is not - 2026-10-03)."""
        if q.get("same_item") or p.get("match") in ("exact", "sister"):
            return True
        shown = str(q.get("product_shown") or p.get("product_shown") or "").lower()
        return bool(line_words) and all(w in shown for w in line_words)
    out = []
    for p in dos.get("photos", []):
        q = p.get("quick") or {}
        if p["file"] in skip or not os.path.exists(p["file"]) or not q.get("same_line") or not ours(p, q):
            continue
        if q.get("kind") not in ("photo", "flat") or not _overlap(q.get("years"), lo, hi):
            continue
        if p["file"] == dos.get("picked"):
            continue
        out.append(p)
    rank = lambda p: ((p.get("quick") or {}).get("kind") == "flat", (p.get("quick") or {}).get("same_item"),
                      (p.get("quick") or {}).get("face") in ("back", "label", "several"),
                      float((p.get("quick") or {}).get("useful") or 0))
    return sorted(out, key=rank, reverse=True)


def queries(dos, still, done=()):
    """A few searches made for what is missing: a peeled label, the back, and the missing parts' own words."""
    import era as ERA
    idn = dos.get("identity") or {}
    name = " ".join(x for x in (idn.get("brand"), idn.get("line"), idn.get("variant")) if x) or idn.get("name", "")
    ew = ERA.words(idn["year"]) if idn.get("year") else ""
    base = f"{ew} {name}".strip()
    qs = [f"{base} label peeled off", f"{base} back of label"] + [f"{base} {e['search']}" for e in still]
    seen, out = {q.lower() for q in done}, []
    for q in qs:
        q = " ".join(dict.fromkeys(re.sub(r"\s+", " ", q).split()))
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:SEARCHES]


def hunt(dos, cid, still, quick, log=print):
    """New photos for the missing parts (a few searches), looked at quickly. -> the new photo records."""
    import dossier as DS
    import google_images as G
    d = os.path.join(DS.WORK, "hunt", cid)
    have = {p["file"] for p in dos["photos"]}
    done = [s["q"] for s in dos.get("searches", [])] + dos.get("searched_before", [])
    new = []
    for q in queries(dos, still, done):
        try:
            hits = G.search_full(q, most=12, min_side=500, log=log)
        except Exception as e:
            log(f"[label parts] Google Images did not work: {e}")
            break
        kept = 0
        for h in hits:
            if kept >= DS.PER_SEARCH:
                break
            f = DS._download(h["url"], d)
            if not f:
                continue
            kept += 1
            if f in have:
                continue
            have.add(f)
            rec = DS._record(f, h["url"], h.get("page", ""), h.get("title", ""), q, source="label parts hunt")
            dos["photos"].append(rec)
            new.append(rec)
        dos.setdefault("searches", []).append({"q": q, "n": kept, "at": time.time(), "for": "label parts"})
        log(f"[label parts] search for what the label lacks: '{q}' -> {kept} photos")
    DS.save(dos)
    if new:
        DS.quick_look(dos, quick, log)
    return new


DATE = r"\bBEST\b|\bEXP|\b(19|20)\d\d\b"


def find(cid, dos, words, kit_name, use, quick, read, log=print, web=True):
    """-> (words to add, receipts [{"word", "what", "photo", "url", "page"}], parts still missing [what])."""
    expect = expected(kit_name)
    still = missing(words, expect)
    if not expect or not still or not dos:
        return [], [], [e["what"] for e in still]
    log(f"[label parts] {cid}: the label lacks {', '.join(e['what'] for e in still)} - looking for them")
    added, receipts, looked = [], [], set()
    has_date = bool(re.search(DATE, "\n".join(words), re.I))
    for stage in ("found already", "new search"):
        if stage == "new search":
            if not web:
                break
            hunt(dos, cid, still, quick, log)
        for p in candidates(dos, looked)[:MOST_PHOTOS // 2]:            # half the reads for each stage
            looked.add(p["file"])
            got = read([p["file"]]) or []
            flat_same = (p.get("quick") or {}).get("kind") == "flat" and (p.get("quick") or {}).get("same_item")
            for w in got:
                w = str(w).strip()
                hit = [e for e in still if re.search(e["pattern"], w, re.I)]
                if not w or w in words or w in added:
                    continue
                if hit or (flat_same and not (has_date and re.search(DATE, w, re.I))):
                    added.append(w)
                    receipts.append({"word": w, "what": hit[0]["what"] if hit else "printed on a flat label of this item",
                                     "photo": p["file"], "url": p.get("url", ""), "page": p.get("page", "")})
            still = missing(words + added, expect)
            if not still:
                break
        if not still:
            break
    log(f"[label parts] {cid}: found {len(added)} line(s)" + (f": {added}" if added else "") +
        (f"; still missing: {', '.join(e['what'] for e in still)}" if still else "; nothing missing now"))
    return added, receipts, [e["what"] for e in still]
