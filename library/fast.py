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
JUDGE_Q = ("Picture 1 shows our finished 3D model of {product} from several sides. Picture 2 is a sheet of real "
           "photos of that item from around {year}. Judge it like a buyer of the best 3D product assets sold on "
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


def rank_listings(rows, names, brand, year):
    """eBay listings ranked by idf - a word's weight is how rare it is among the results' titles (Sparck Jones 1972)
    - plus the era's words for an old item; another brand is dropped."""
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

    def score(L):
        t = tok(L["title"])
        if b and t and not (b & t):
            return -1.0
        return sum(math.log((N + 1) / (df.get(w, 0) + 1)) for w in want & t) + 2 * len(era & t)
    return sorted((L for L in rows if score(L) >= 0), key=lambda L: -score(L))


def references(cid, card, R, log, listings=6, google=25):
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
    qs = [q for n in era_names for q in (("vintage " + n) if old else "", n)] + [("vintage " + name) if old else "", name]
    for q in dict.fromkeys(qs):
        if not q:
            continue
        try:
            for L in G.search_listings(q, log=log):
                if L["id"] not in seen:
                    seen.add(L["id"])
                    rows.append(L)
        except Exception as e:
            log(f"[fast] eBay could not be searched: {str(e)[:120]}")
    rows = rank_listings(rows, era_names + [name], brand, year)
    log("[fast] eBay listings, best match first: " + " | ".join(L["title"][:50] for L in rows[:listings]))
    for L in rows[:listings]:
        try:
            for u in G.listing(L["page"], log)[:10]:
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
        if r.get("listing") and r.get("listing_best", 0) >= 7 and lk.get("real_photo") is not False:
            s = max(s, 7)
        # merchandise in the same artwork (a battery-shaped pin, a magnet - 2026-10-07 22:10: two were on the
        # drawing's sheet) and ads are no reference for the item itself
        r["score"] = s if lk.get("real_photo") is not False and lk.get("kind", "item") == "item" else 0
    good = sorted([r for r in refs if r["score"] >= 7], key=lambda r: (-r["score"], 0 if r.get("listing") else 1))
    log(f"[fast] {len(good)} of {len(refs)} photos show this item; "
        f"{sum(1 for r in good if (r.get('look') or {}).get('side') in ('back', 'several'))} show another side")
    return good


def photo_words(good, log, most=8):
    """The printed lines on the best photos, read by Apple's own text reader (measure.read_lines) - kept when read on
    at least two different photos (majority voting across independent reads, ROVER). Qwen-Image renders exact text
    when it is GIVEN the words (its model card: precise text rendering); without them it invents (2026-10-07 22:10:
    'ALKAMEF ATERN', 'AUFALNE BATTEMP')."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    reads = []
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
            if hits >= 2 and letters >= 0.4:
                out.append(l)
    log(f"[fast] words read on at least two photos: {out[:20]}")
    return out[:30]


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
    "no glare, no other objects, no hands. Its true proportions: {size}. Every word is real and spelled right.{words}{fix}")


def faces(good, vocab, log, most=8):
    """The item's different printed sides, each from ONE clear photo of one copy: the photo read with the most words
    first, then the one whose words share least with it (2026-10-08 04:25: a sheet showing two sides at once was
    merged into one garbled side - the battery's big-logo side and its PowerCheck side). Each face carries the words
    read on ITS photo, spelled as two photos agree where they do. -> [(photo, [words])], at most 2."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    singles = [r for r in good if (r.get("look") or {}).get("one_item")] or good
    read = []
    for r in singles[:most]:
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


def draw(card, good, tex, along, around, R, log, fix="", tries=3, words=()):
    """Each printed side of the item drawn clean from ONE clear photo of that side, best of `tries` by the judge
    against that photo and by its words read back. -> (front, back or None, notes)."""
    import turnaround as T
    import vet as V
    product, year = display(card), card.get("year") or "its era"
    sheet = R.reference_sheet([r["file"] for r in good[:9]], os.path.join(tex, "refs_sheet.png"))
    st = size_text(along, around)
    fx = (" Fix these from the last try: " + "; ".join(fix)) if fix else ""
    vw, vh = 1344, 768
    fs = faces(good, list(words), log)
    if not fs:
        fs = [(good[0]["file"], list(words))]
    drawn, notes = [], {"tries": []}
    for k, (photo, ws) in enumerate(fs):
        try:                                                 # the item alone on white: nothing else to copy
            mask = T.photo_mask(photo, timeout=300)
            import skin
            src = skin.cutout({"file": photo, "mask": mask}, os.path.join(tex, f"side{k + 1}_photo.png"))
        except Exception:
            src = photo
        try:                                                 # lying down, like the drawing: a standing photo is
            from PIL import Image                            # turned a quarter (its top end to the left) - 05:15:
            im = Image.open(src)                             # drawn level from a standing photo, the judge called
            if im.height > 1.3 * im.width:                   # it mirrored and garbled
                flat = os.path.join(tex, f"side{k + 1}_level.png")
                im.rotate(90, expand=True, fillcolor="white").save(flat)
                src = flat
        except Exception:
            pass
        wd = (" The printed text, spelled exactly: " + ", ".join(f'"{w}"' for w in ws[:24]) + ".") if ws else ""
        best = None
        for t in range(tries):
            out = os.path.join(tex, f"side{k + 1}_{t + 1}.png")
            T.draw_from_photos(product, [src], out, width=vw, height=vh,
                               prefix=DRAW_FACE.format(product=product, year=year, size=st, fix=fx, words=wd),
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
            if best is None or m + 5 * wb > best[0]:
                best = (m + 5 * wb, out, m, wb)
            if m >= 8 and wb >= 0.6:
                break
        drawn.append(best)
    front = drawn[0]
    back = drawn[1] if len(drawn) > 1 and drawn[1][2] >= 6 and drawn[1][3] >= 0.4 else None
    if len(drawn) > 1 and not back:
        log("[fast] the other side's drawing did not match its photo - the front's bands carry round the back")
    return front[1], back[1] if back else None, dict(notes, sheet=sheet, clear=fs[0][0], front_match=front[2],
                                                    front_words=front[3])


def label_from(front, back, along, around, tex, log, product="", words=()):
    """The production way a round label texture is made: the drawn views' straight-on middles (the camera saw
    them square - within 60 degrees of the middle, before the curve stretches the print) unrolled flat, each made
    with the light taken off each column by the unroll itself, the front centered, the other side opposite, the rest of each row its own background color
    (the row's median ink across both sides - never one side's edge carried round as stripes). No baked light:
    the 3D render lights it (2026-10-08 01:10: glare, edge stretch and green stripes baked into the label).
    -> (label png, all-seen png)."""
    import skin
    import turnaround as T
    from PIL import Image
    W = 2048
    H = int(round(W * along / around))
    lab, cov = np.zeros((H, W, 3)), np.zeros((H, W))
    wd = (" The printed text, spelled exactly: " + ", ".join(f'"{w}"' for w in list(words)[:24]) + ".") if words else ""
    for i, f in enumerate([front] + ([back] if back else [])):
        try:
            got = skin.unroll_view({"file": f, "mask": T.photo_mask(f, timeout=300), "whole": True}, along, around, W, max_deg=60)
        except Exception as e:
            log(f"[fast] {os.path.basename(f)} could not be unrolled: {str(e)[:100]}")
            got = None
        if not got:
            continue
        l, w = got
        cols = np.where(w.max(0) > 0.05)[0]
        if not len(cols):
            continue
        c0, c1 = int(cols.min()), int(cols.max()) + 1
        strip = np.clip(l[:, c0:c1], 0, 1)
        sp = os.path.join(tex, f"strip{i + 1}.png")
        Image.fromarray((strip * 255).astype(np.uint8)).save(sp)
        # (no generative "flatten" edit: asked to make the strip flat artwork, Qwen-Image-Edit redrew it as a
        #  picture of a battery - rounded ends, white margins - 2026-10-08 02:17. The unroll already takes the
        #  light off each column (mosaic.strip -> unwrap.delight); the drawn studio photo has no glare to speak of)
        flat = sp
        art = np.asarray(Image.open(flat).convert("RGB").resize((c1 - c0, H), Image.LANCZOS)) / 255.0
        placed = np.zeros((H, W, 3))
        pw = np.zeros((H, W))
        placed[:, c0:c1], pw[:, c0:c1] = art, 1.0
        if i == 1:                                           # the other side: half a turn round
            placed, pw = np.roll(placed, W // 2, axis=1), np.roll(pw, W // 2, axis=1)
        new = (pw > 0) & (cov == 0)
        lab = np.where(new[..., None], placed, lab)
        cov = np.maximum(cov, pw)
    if cov.max() <= 0:
        raise RuntimeError("the drawn item could not be unrolled onto the label")
    seen = cov > 0
    log(f"[fast] the flat artwork covers {seen.max(0).mean():.0%} of the way around; each row's own background fills the rest")
    bg = np.stack([np.median(lab[r][seen[r]], axis=0) if seen[r].any() else np.zeros(3) for r in range(H)])
    from scipy import ndimage as _nd                         # the background changes only at a band's edge: each
    bg = _nd.median_filter(bg, size=(max(3, H // 20) | 1, 1), mode="nearest")   # row's color smoothed along the
    #                                                          length (a single row's text left ghost stripes)
    out = np.where(seen[..., None], lab, bg[:, None, :])
    # a soft join (40 px) where the artwork meets the background, so no hard edge shows
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(seen)
    a = np.clip(dist / 40.0, 0, 1)[..., None]
    out = a * out + (1 - a) * bg[:, None, :]
    png = os.path.join(tex, "label.png")
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


def unknown_words(png, vocab):
    """Words read off the finished label that no real photo carries (a made-up word, a misread drawn as print)."""
    import measure as MS
    from rapidfuzz import fuzz
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    known = {norm(t) for v in vocab for t in re.findall(r"[A-Za-z0-9]+", v) if len(t) >= 3}
    out = []
    for line in MS.read_lines(png) or []:
        for t in re.findall(r"[A-Za-z]{4,}", line):
            if not any(fuzz.ratio(norm(t), k) >= 80 for k in known):
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
    try:
        import viewshot
        shots, _ = viewshot.shoot(glb, os.path.join(d, "check"))
        if shots:
            return shots
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
    refs = references(cid, card, R, log)
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
    words = photo_words(good, log)
    fix, last = [], None
    for rnd in range(2):
        R.boundary(cid, "step")
        R.status(cid, step=f"3/5 drawing the item from {min(len(good), 9)} photos" + (" (again, with the judge's fixes)" if rnd else ""))
        R.make_room("drawing")
        front, back, dn = draw(card, good, tex, along, around, R, log, fix=fix, words=words)
        if dn["front_match"] < 6 or dn["front_words"] < 0.5:     # nothing that does not match is built or filed
            fix = [f"the drawing must match the real item and carry its real words (it scored {dn['front_match']}/10, "
                   f"{dn['front_words']:.0%} of the words)"]
            last = {"realism": 0, "era": 0, "words": 0, "fix": fix, "shots": dn["sheet"], "front": front, "back": back}
            log(f"[fast] no drawing matched well enough (best {dn['front_match']}/10, {dn['front_words']:.0%} of the words) - drawn again")
            continue
        png, cover = label_from(front, back, along, around, tex, log, product=display(card), words=words)
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
        pics = [close, dn["sheet"]]
        v = V.ask(V.model(), JUDGE_Q.format(product=display(card), year=card.get("year") or "its era"), pics,
                  think=True) or {}
        sc = {k: int(v.get(k) or 0) for k in ("realism", "era", "words")}
        sc["words"] = min(sc["words"], int(round(10 * dn["front_words"])))   # the words are MEASURED, not only judged
        bad = unknown_words(os.path.join(d, "label.png"), words)
        if len(bad) > 1:                                     # a made-up word on the label fails it
            sc["words"] = min(sc["words"], 4)
            v.setdefault("fix", []).append("made-up words on the label: " + ", ".join(bad[:6]))
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
        fix = [str(x)[:120] for x in (v.get("fix") or [])][:6]
    R.status(cid, step=f"failed the realism check: the judge, twice (realism {last['realism']}, era {last['era']}, words {last['words']}): "
                       + "; ".join(last["fix"])[:200], ok=False, views=os.path.relpath(last["shots"], R.WORK))
    return last
