"""FACTS WITH RECEIPTS: the printed facts of one item, each with where it was found (his rule, 2026-10-02: facts are
never invented, every fact has a receipt - a web page address or a photo file).

    facts = facts.gather(dossier, log)      # -> {"upc": {"value", "sources", "checks", "status"}, ...}

The facts: upc, net_weight, count, nutrition and ingredients (food only), maker_lines, legal_lines, contents (what
is inside the package: how many, in what packs, their real sizes). Looked for in this order:
  a. real photos of that era's panels: your local AI reads the printed words (it is told to copy only what it can
     read, never to fill in), and a barcode in a photo is scanned by zxing-cpp when it is installed
  b. web pages: UPC databases (upcitemdb, Barcode Spider, Buycott), Open Food Facts, retailer pages
Checks: the UPC's check digit; the maker's prefix (first 6 digits) the same across sources and the same as the
brand's other products on the same pages; how many independent sources agree (2 or more = verified, 1 =
single_source); nutrition math (calories ~ 4 x carbs + 4 x protein + 9 x fat, within 15%); the Nutrition Facts
format of the year. A fact that can't be found is "missing" and says so in plain words - never made up.
Nutrition and ingredients change over the years, so a web page counts only if it is from the item's own era.
"""
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eraprint  # noqa: E402  (check digit, nutrition format and math)
import websearch  # noqa: E402

KEYS = ["upc", "net_weight", "count", "nutrition", "ingredients", "maker_lines", "legal_lines", "contents"]

PANEL_Q = """[panel-text] This photo shows a package of: {shown}.
Copy ONLY what is printed and readable in this photo. Never fill anything in from memory: leave a field empty or
null when it can't be read clearly. Words laid ON TOP of the photo are NOT printed on the package - a watermark, a
photographer's or seller's name, an email or web address over the picture, a price or store sticker: never copy
them into the fields below, list them in "overlay_text" instead. Answer ONLY JSON:
{{"upc_digits": "every digit printed under the barcode, in order, or empty",
 "net_weight": "the net weight line exactly as printed, or empty",
 "count": "the count line exactly as printed, e.g. '8 TOASTER PASTRIES', or empty",
 "nutrition": null, or {{"format": "pre_nlea" (titled 'Nutrition Information', U.S. RDA percentages) | "1994_nlea"
     ('Nutrition Facts' with 'Calories from Fat') | "2006_trans" (also a 'Trans Fat' row) | "2020_new" (huge
     calories number, 'Includes Xg Added Sugars'),
     "serving": "", "servings": "", "calories": , "fat_calories": ,
     "rows": [["Total Fat", "5g", "8%", 0], ["Saturated Fat", "1.5g", "8%", 1]], "vitamins": ["Vitamin A 10%"]}},
 "ingredients": "the ingredients text exactly as printed, or empty",
 "maker_lines": ["the 'distributed by' / 'manufactured by' lines and address, exactly"],
 "legal_lines": ["copyright, trademark, recycled-carton and made-in lines, exactly"],
 "contents_lines": ["any line saying how the items are packed inside, e.g. '4 pouches of 2 pastries'"],
 "codes": ["carton numbers, item numbers, date codes, exactly"],
 "overlay_text": ["words laid over the photo that are not printed on the package (watermark, credit, sticker)"]}}"""


# ------------------------------------------------------------------ small helpers
def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _toks(s):
    return [t for t in _norm(s).split() if len(t) > 1 and t not in ("the", "and", "with", "of", "s")]


def sizes(text):
    """Every net-weight number in a text: {'oz': {14.7}, 'g': {416}}."""
    t = str(text or "").lower().replace(",", ".")
    oz = {round(float(x), 1) for x in re.findall(r"(\d{1,3}(?:\.\d{1,2})?)\s*(?:fl\.?\s*)?(?:oz|ounces?)\b", t)}
    g = {round(float(x)) for x in re.findall(r"(\d{2,4}(?:\.\d)?)\s*(?:g|grams?)\b", t)}
    return {"oz": oz, "g": g}


def counts(text):
    """Every package count in a text ('8 ct', '8 count', '8 toaster pastries', '8-pack') -> {8}."""
    t = str(text or "").lower()
    return {int(x) for x in re.findall(r"\b(\d{1,3})\s*[-]?\s*(?:ct|count|pk|pack|pastries|toaster pastries|bars|"
                                       r"pieces|cookies|batteries|cells|ea)\b", t) if 0 < int(x) < 500}


def count_set(t):
    """{8} from '8', 8, '8 TOASTER PASTRIES' or '8 ct'."""
    if isinstance(t, (int, float)) and t > 0:
        return {int(t)}
    t = str(t or "").strip()
    return {int(t)} if t.isdigit() else counts(t)


def _same_size(a, b):
    sa, sb = sizes(a), sizes(b)
    return bool({round(x, 1) for x in sa["oz"]} & {round(x, 1) for x in sb["oz"]}) or \
        any(abs(x - y) <= 2 for x in sa["g"] for y in sb["g"])


COPYRIGHT = re.compile(r"(?i)©|\(c\)\s*(?:19|20)\d\d|copyright")   # a copyright line (its year is that box's own;
#                                                                   an address's ZIP+4 like 49016-1986 is not a year)

# Words that are on the PHOTO, never on the product: a photographer's or seller's watermark, an email, an @name, a
# photo / stock / auction site's name. Found 2026-10-03: a Flickr photographer's name and email ("(c) 2015 <name>
# <email>" over a battery photo) was read as the battery's legal lines - and legal lines get printed on rebuilt sides.
NOT_PRINTED = re.compile(
    r"(?i)[\w.+-]+@[\w-]+\.[\w.]+|(?:^|\s)@[a-z0-9_.]{3,}|"
    r"\b(?:alamy|shutterstock|getty\s*images|gettyimages|istock(?:photo)?|dreamstime|123rf|depositphotos|"
    r"adobe\s*stock|bigstock|flickr|worthpoint|picclick|ebay|etsy|pinterest|mercari|poshmark|craigslist|kijiji|"
    r"imgur|wikimedia)\b|"
    r"\b(?:photo|photograph|photography|image|picture|pic)(?:s|ed)?\s+(?:by|from|credit|courtesy)\b|"
    r"\bwatermark")


def not_printed(line):
    """True when a line read off a photo belongs to the photo (watermark, credit, email, site name), not the product."""
    return bool(NOT_PRINTED.search(str(line or "")))


def _overlay_words(p):
    """Every word the careful look or the panel reader said was laid ON TOP of this photo (watermark, sticker...)."""
    out = [str(o.get("text", "")) for o in p.get("overlays") or [] if isinstance(o, dict)]
    out += [str(t) for t in ((p.get("panel") or {}).get("overlay_text") or []) if t]
    return [_norm(t) for t in out if _norm(t)]


def _on_overlay(line, words):
    n = _norm(line)
    return bool(n) and any(n in w or (len(w) >= 4 and w in n) for w in words)


def marked(p):
    """Does this photo carry a watermark / credit / sticker? (then its lines count only when another photo agrees)"""
    if p.get("watermarked") or p.get("overlays") or (p.get("panel") or {}).get("overlay_text"):
        return True
    panel = p.get("panel") or {}
    return any(not_printed(x) for k in ("maker_lines", "legal_lines", "codes", "contents_lines")
               for x in (panel.get(k) or []) if isinstance(x, str))


def clean_lines(lines, p=None):
    """The lines that are really printed on the product (watermarks, credits, emails, site names and anything the
    looks said was laid over the photo taken out)."""
    words = _overlay_words(p or {})
    return [ln for ln in lines or [] if isinstance(ln, str) and ln.strip() and not not_printed(ln)
            and not _on_overlay(ln, words)]


def _years(text):
    return [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", str(text or ""))]


def _status(n_sources, conflict=False):
    if conflict:
        return "unverified"
    return "verified" if n_sources >= 2 else "single_source" if n_sources == 1 else "missing"


def _host(url):
    return urllib.parse.urlparse(url or "").netloc.lower().replace("www.", "")


def _photo_src(p, quote):
    return {"kind": "photo", "url": p.get("url", ""), "file": p.get("file", ""), "page": p.get("page", ""),
            "phash": p.get("phash", ""), "quote": str(quote)[:300]}


def _web_src(url, quote):
    return {"kind": "web", "url": url, "file": "", "quote": re.sub(r"\s+", " ", str(quote))[:300]}


def _independent(sources):
    """How many separate places agree: each web site counts once, each photo counts once - and the same picture
    saved twice from two links (same fingerprint) is still one photo."""
    keys, pics = set(), []
    for s in sources:
        if s.get("kind") != "photo":
            keys.add(_host(s.get("url")))
            continue
        h = s.get("phash", "")
        if h and any(h2 and bin(int(h, 16) ^ int(h2, 16)).count("1") <= 6 for h2 in pics):
            continue
        if s.get("file") in keys:
            continue
        keys.add(s.get("file"))
        pics.append(h)
    return len(keys)


# ------------------------------------------------------------------ the checks
def upc_check(code):
    """{'ok': bool, 'upc': 12 digits or None, 'why': plain words}"""
    try:
        return {"ok": True, "upc": eraprint.upc12(code), "why": "check digit adds up"}
    except ValueError as e:
        return {"ok": False, "upc": None, "why": str(e)}


def prefix(code12, n=6):
    """The maker's part of a UPC-A (the classic 6-digit company prefix: number system digit + 5)."""
    return str(code12)[:n]


def calories_check(n):
    return eraprint.calories_check(n)


def nutrition_format(year):
    return eraprint.nutrition_format(year)


def _era_ok(years, era):
    """Do a source's years fall inside the item's era (catalog year +/- 3)? None when the source has no date."""
    if not years:
        return None
    return any(era[0] <= y <= era[1] for y in years)


# ------------------------------------------------------------------ (a) photos: printed words and barcodes
def scan_barcodes(path):
    """Barcodes in a photo, read by zxing-cpp when it is installed ([] when it isn't): ['038000317101', ...]"""
    try:
        import zxingcpp
        from PIL import Image
    except Exception:
        return []
    out = []
    try:
        im = Image.open(path).convert("RGB")
        for scale in (1.0, 2.0):                                     # small barcodes read better enlarged
            img = im if scale == 1.0 else im.resize((int(im.width * scale), int(im.height * scale)))
            for b in zxingcpp.read_barcodes(img):
                t = re.sub(r"\D", "", b.text or "")
                fmt = str(b.format)
                if ("UPC" in fmt or "EAN" in fmt) and len(t) in (12, 13):
                    c = upc_check(t)
                    if c["ok"] and c["upc"] not in out:
                        out.append(c["upc"])
            if out:
                break
    except Exception:
        return out
    return out


def clean_panel(p):
    """Takes everything that is on the photo but not on the product out of one photo's read panel; marks the photo
    as watermarked when anything was. Returns what was taken out."""
    panel = p.get("panel")
    if not isinstance(panel, dict):
        return []
    dropped = []
    for k in ("maker_lines", "legal_lines", "contents_lines", "codes"):
        v = panel.get(k)
        if isinstance(v, list):
            keep = clean_lines(v, p)
            dropped += [str(x) for x in v if x not in keep and str(x).strip()]
            panel[k] = keep
    for k in ("ingredients", "net_weight", "count", "upc_digits"):
        if isinstance(panel.get(k), str) and panel[k] and not clean_lines([panel[k]], p):
            dropped.append(panel[k])
            panel[k] = ""
    if dropped or panel.get("overlay_text") or p.get("overlays"):
        p["watermarked"] = True
    return dropped


def read_panels(dos, use=None, log=print, most=8):
    """Your local AI copies the printed facts off the era's photos (this exact item first, then its sister boxes of
    the same era). Kept on each photo as 'panel', so nothing is read twice."""
    import vet as V
    use = use or V.model()
    era = dos["identity"]["years"]
    picked = dos.get("picked")
    order = [p for p in dos.get("photos", []) if p.get("match") == "exact" or p.get("file") == picked]
    order += sorted([p for p in dos.get("photos", []) if p.get("match") in ("sister", "near_year")
                     and _era_ok(p.get("years"), era) is not False],
                    key=lambda p: -(p.get("quality") or 0))[:4]
    n = 0
    for p in order:
        if "panel" in p:
            clean_panel(p)                     # read before the watermark rule: cleaned now (the same rule)
        if "panel" in p or n >= most or not use:
            continue
        n += 1
        try:
            p["panel"] = V.ask(use, PANEL_Q.format(shown=p.get("product_shown") or dos["identity"].get("name", "")),
                               [p["file"]], think=False, side=1600)
        except Exception as e:
            log(f"[facts] could not read {os.path.basename(p['file'])}: {e}")
            p["panel"] = {}
        dropped = clean_panel(p)
        if dropped:
            log(f"[facts] {os.path.basename(p['file'])}: on the photo, not the product (left out): "
                + "; ".join(dropped)[:200])
        p["barcodes"] = scan_barcodes(p["file"])
        log(f"[facts] read {os.path.basename(p['file'])} ({p.get('match') or 'your pick'}): "
            + ", ".join(k for k, v in (p["panel"] or {}).items() if v) + (f"; barcode {p['barcodes']}" if p["barcodes"] else ""))
    return order


# ------------------------------------------------------------------ (b) web: UPC databases and pages
def _upc_pages(code12):
    return [f"https://www.upcitemdb.com/upc/{code12}",
            f"https://world.openfoodfacts.org/api/v2/product/0{code12}.json?fields=product_name,brands,quantity,"
            "code,serving_size,created_t,last_modified_t",
            f"https://www.barcodespider.com/{code12}",
            f"https://www.buycott.com/upc/{code12}"]


def _matches_item(text, idn):
    """Is this text about our exact item: our product line and variant, and our size or count?"""
    t = " " + _norm(text) + " "
    line = [w for w in _toks(idn.get("line")) if w not in _toks(idn.get("brand"))] or _toks(idn.get("line"))
    brand = _toks(idn.get("brand"))
    var = _toks(idn.get("variant"))
    has = lambda ws: bool(ws) and all((" " + w + " ") in t or w in t.replace(" ", "") for w in ws)
    if (line or brand) and not (has(line) or has(brand)):     # its product line, or at least its brand
        return False
    if var and not all((" " + w) in t for w in var):
        return False
    have = sizes(text)
    if idn.get("size_text") and (have["oz"] or have["g"]):      # a size is given: it must be ours
        return _same_size(text, idn.get("size_text"))
    return bool(count_set(idn.get("count")) & counts(text))


def _quote_near(text, needle, n=220):
    i = text.find(needle) if needle else -1
    if i < 0:
        return text[:n]
    return text[max(0, i - 60):i + n]


BUNDLE = re.compile(r"(?i)\(\s*\d+\s*-?\s*(?:pack|pk|ct|count)\s*\)|\bpack\s+of\s+\d+|\bcase\s+of\b|\blot\s+of\b|"
                    r"\bbundle\b|\b\d+\s*x\s*\d+\s*(?:ct|count|pack)?\b")


def upc_candidates_web(idn, log=print):
    """UPC codes the web gives for this item, with the brand's other codes seen on the same pages:
    -> ({code12: [sources]}, [brand codes seen])"""
    cands, brand_codes = {}, []
    name = " ".join(x for x in (idn.get("line"), idn.get("variant")) if x)
    size = idn.get("size_text") or ""
    sz = sizes(size)
    size_q = (f"{min(sz['oz'])} oz" if sz["oz"] else f"{min(sz['g'])} g" if sz["g"] else
              (f"{idn.get('count')} ct" if idn.get("count") else ""))
    # upcitemdb's own product search (a plain page, no search engine needed): this item, then the whole product line
    # (the brand's other codes show the maker's prefix)
    for i, words in enumerate((f"{name} {size_q}".strip(), idn.get("line") or name)):
        q = urllib.parse.urlencode({"s": words, "type": "2"})
        raw = websearch.get(f"https://www.upcitemdb.com/query?{q}", log=log)
        for m in re.finditer(r'href="/upc/(\d{11,13})"[^>]*>\s*\d+\s*</a>\s*<p>(.*?)</p>', raw, re.S):
            title = websearch.text_of(m.group(2))
            c = upc_check(m.group(1).zfill(12) if len(m.group(1)) == 11 else m.group(1))
            if not c["ok"] or BUNDLE.search(title):           # a reseller's multi-pack listing is not the box
                continue
            if any(w in _norm(title) for w in _toks(idn.get("line"))[:1]) and c["upc"] not in brand_codes:
                brand_codes.append(c["upc"])
            if i == 0 and _matches_item(title, idn):
                cands.setdefault(c["upc"], [])
    # an ordinary web search for the code
    for qq in (f"{name} {size_q} UPC", f"{idn.get('brand', '')} {name} barcode"):
        for r in websearch.search(qq.strip(), n=8, log=log):
            blob = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('url', '')}"
            for code in re.findall(r"(?<!\d)(\d{12,13})(?!\d)", blob):
                c = upc_check(code)
                if c["ok"] and _matches_item(blob, idn):
                    cands.setdefault(c["upc"], [])
    return cands, brand_codes


def confirm_upc(code12, idn, log=print):
    """The pages that say this code is our item: [web sources]. Each site counts once."""
    out = []
    for url in _upc_pages(code12):
        text = websearch.read(url, 8000, log=log)
        if not text:
            continue
        if url.endswith(".json") or "openfoodfacts" in url:
            try:
                j = json.loads(text)
            except Exception:
                continue
            p = j.get("product") or {}
            if j.get("status") != 1:
                continue
            blob = f"{p.get('brands', '')} {p.get('product_name', '')} {p.get('quantity', '')}"
            if _matches_item(blob, idn):
                out.append(_web_src(url.split("?")[0], f"{blob} (code {p.get('code')})"))
            continue
        if code12 not in re.sub(r"\D", "", text[:20000]) or re.search(r"(?i)not found|no results|invalid upc", text[:400]):
            continue
        if _matches_item(text[:4000], idn):
            out.append(_web_src(url, _quote_near(text, code12)))
    return out


# ------------------------------------------------------------------ gather everything
def gather(dos, log=print, use=None, web=True):
    """All the item's facts with their receipts and checks. Changes dos['photos'] (adds what was read) and returns
    the facts dict; also adds plain-words gap lines to dos['gaps']."""
    idn = dos["identity"]
    era = idn.get("years") or [None, None]
    facts, gaps = {}, dos.setdefault("gaps", [])
    if idn.get("kind") == "object":                           # the thing itself, not a package: no barcode, net
        off = {"value": None, "sources": [], "checks": {"applies": False}, "status": "missing"}   # weight or contents
        facts.update({k: dict(off) for k in ("upc", "net_weight", "count", "contents")})
        keep_gaps = list(gaps)
        got = gather(dict(dos, identity=dict(idn, kind="packaging")), log, use, web=False)
        dos["gaps"][:] = keep_gaps + [g for g in dos["gaps"][len(keep_gaps):]
                                      if g.split(":")[0].replace(" ", "_") in ("maker_lines", "legal_lines")]
        facts.update({k: got[k] for k in ("maker_lines", "legal_lines")})
        return facts
    photos = read_panels(dos, use, log) if use is not False else []
    picked = dos.get("picked")
    exact = [p for p in photos if p.get("match") == "exact" or p.get("file") == picked]
    sisters = [p for p in photos if p.get("match") in ("sister", "near_year")]
    era_txt = f"{era[0]}-{era[1]}" if era[0] else "its era"

    # --- UPC
    cands = {}
    for p in exact:
        for code in p.get("barcodes") or []:
            cands.setdefault(code, []).append(_photo_src(p, f"barcode scanned in the photo: {code}"))
        dig = (p.get("panel") or {}).get("upc_digits")
        c = upc_check(dig) if dig and len(re.sub(r"\D", "", dig)) >= 12 else {"ok": False}
        if c["ok"]:
            cands.setdefault(c["upc"], []).append(_photo_src(p, f"digits under the barcode: {dig}"))
    brand_codes, sister_codes = [], [c for p in sisters for c in (p.get("barcodes") or [])]
    if web:
        try:
            wc, brand_codes = upc_candidates_web(idn, log)
            for code in wc:
                cands.setdefault(code, [])
        except Exception as e:
            log(f"[facts] web UPC lookup failed: {e}")
    # the maker's prefix: the one most of the brand's codes on the same pages share; a code with another prefix is
    # a reseller's own bundle code ("pack of 12"), not the maker's barcode on the box
    from collections import Counter
    pc = Counter(prefix(c) for c in set(brand_codes + sister_codes + list(cands)))
    brand_prefix, nbp = pc.most_common(1)[0] if pc else ("", 0)
    resold = []
    if nbp >= 2 and list(pc.values()).count(nbp) == 1:
        for code in list(cands):
            if prefix(code) != brand_prefix and not any(x["kind"] == "photo" for x in cands[code]):
                resold.append(code)
                cands.pop(code)
    if web:
        for code in list(cands)[:5]:                          # the pages that say each code is this item
            try:
                cands[code] += confirm_upc(code, idn, log)
            except Exception as e:
                log(f"[facts] could not check {code} on the web: {e}")
    if cands:
        codes_seen = [c for p in exact for c in ((p.get("panel") or {}).get("codes") or [])]

        def overlap(code):                     # a carton / item number on the photo sharing 4 digits with the code
            return [c for c in codes_seen if any(code[6:11][i:i + 4] in re.sub(r"\D", "", c) for i in range(2))]
        ranked = sorted(cands.items(), key=lambda kv: (-any(s["kind"] == "photo" for s in kv[1]), -_independent(kv[1]),
                                                       -len(overlap(kv[0]))))
        best, srcs = ranked[0]
        n = _independent(srcs)
        rivals = [(c, _independent(s)) for c, s in ranked[1:] if _independent(s) >= max(1, n)
                  and not any(x["kind"] == "photo" for x in srcs) and not (overlap(best) and not overlap(c))]
        pre = prefix(best)
        same_brand = [c for c in brand_codes + sister_codes if c != best]
        checks = {"check_digit": upc_check(best)["ok"],
                  "maker_prefix": pre,
                  "brand_prefix_on_the_pages": f"{brand_prefix} ({nbp} of {sum(pc.values())} codes for this brand)",
                  "prefix_agrees_across_sources": all(prefix(c) == pre for c in cands if cands[c]),
                  "reseller_codes_left_out": resold,
                  "brand_codes_with_same_prefix": f"{sum(prefix(c) == pre for c in same_brand)} of {len(same_brand)}",
                  "sources_agreeing": n,
                  "other_codes": {c: k for c, k in rivals} or {c: _independent(s) for c, s in ranked[1:4]},
                  "photo_codes_matching": sorted(set(overlap(best))),
                  "size_on_pages_matches_photo": bool(idn.get("size_text")) and n > 0}
        if same_brand and sum(prefix(c) == pre for c in same_brand) == 0:
            checks["warning"] = "none of the brand's other codes share this maker prefix"
        conflict = bool(rivals) or not checks["check_digit"]
        facts["upc"] = {"value": best if n else None, "sources": srcs, "checks": checks,
                        "status": _status(n, conflict) if n else "missing"}
        if rivals:
            gaps.append(f"UPC: two codes are given for this item ({best} and {', '.join(c for c, _ in rivals)}) with "
                        "the same support - the barcode is left off until one is confirmed")
    else:
        facts["upc"] = {"value": None, "sources": [], "checks": {}, "status": "missing"}
    if facts["upc"]["status"] == "missing":
        gaps.append("UPC: no photo of this item's barcode and no web page with its code was found - no barcode is drawn")

    # --- net weight and count (the photo of the exact item first, then the pages that confirmed the UPC)
    upc_pages = [s for s in facts["upc"]["sources"] if s["kind"] == "web"] if facts["upc"]["value"] else []
    for key, field, same in (("net_weight", "net_weight", _same_size),
                             ("count", "count", lambda a, b: bool(count_set(a) & count_set(b)))):
        srcs, value = [], None
        for p in exact:
            t = (p.get("panel") or {}).get(field)
            if not t and p.get("file") == picked:                 # what your AI read off your pick for its identity
                t = idn.get("size_text") if key == "net_weight" else idn.get("count")
            t = str(t) if t not in (None, "") else ""
            if t and (value is None or same(t, value)):
                value = value or t
                srcs.append(_photo_src(p, t))
        for s in upc_pages:
            if value and same(s["quote"] + " " + websearch.read(s["url"], 6000), value):
                srcs.append(dict(s, quote=f"{s['quote'][:200]} (same {key.replace('_', ' ')})"))
        n = _independent(srcs)
        facts[key] = {"value": value, "sources": srcs, "checks": {"sources_agreeing": n}, "status": _status(n)}
        if not value:
            gaps.append(f"{key.replace('_', ' ')}: not readable on any photo of this item")

    # --- nutrition and ingredients: only this item's own panel from its own era (recipes change over the years)
    for key in ("nutrition", "ingredients"):
        if not idn.get("food"):
            continue
        srcs, value, fmt = [], None, None
        for p in exact:
            v = (p.get("panel") or {}).get(key)
            if not v or _era_ok(p.get("years"), era) is False:
                continue
            if value is None:
                value = v
                fmt = (v.get("format") if isinstance(v, dict) else None)
            srcs.append(_photo_src(p, json.dumps(v)[:300] if isinstance(v, dict) else v))
        checks = {"era_ok": True if value else None}
        if key == "nutrition" and value:
            checks["format"] = fmt if fmt in ("pre_nlea", "1994_nlea", "2006_trans", "2020_new") else nutrition_format(idn.get("year"))
            checks["format_expected_for_year"] = nutrition_format(idn.get("year"))
            checks["math"] = calories_check(value)
        status = _status(_independent(srcs))
        if key == "nutrition" and value and checks["math"].get("ok") is False:
            status = "unverified"
            gaps.append(f"nutrition: the numbers read off the photo don't add up ({checks['math']}) - not printed")
        ref = None
        if not value and web and facts["upc"]["value"]:
            ref = _web_reference(key, facts["upc"]["value"], era, log)
        facts[key] = {"value": value, "sources": srcs, "checks": checks, "status": status}
        if ref:                                            # a newer source: kept as reference, never printed
            facts[key].update(reference=ref, status="unverified")
            facts[key]["checks"]["era_ok"] = False
        if not value:
            gaps.append(f"{key}: no photo of this item's own {key} panel from {era_txt} was found"
                        + (" (a newer web source exists but describes a later recipe, so it isn't printed)" if ref else "")
                        + " - that panel is left off")

    # --- maker and legal lines
    _lines(facts, gaps, photos, exact, sisters, idn, era)

    # --- what is inside
    facts["contents"] = contents_fact(dos, facts, log, web)
    return facts


def recheck_lines(dos, log=print):
    """A dossier made before the watermark rule: its maker and legal lines worked out again from the photos already
    read (no new looks, nothing downloaded). Returns the lines that were taken out."""
    facts = dos.get("facts") or {}
    old = {k: list((facts.get(k) or {}).get("value") or []) for k in ("maker_lines", "legal_lines")}
    picked = dos.get("picked")
    photos = [p for p in dos.get("photos", []) if isinstance(p.get("panel"), dict)]
    for p in photos:
        clean_panel(p)
    exact = [p for p in photos if p.get("match") == "exact" or p.get("file") == picked]
    sisters = [p for p in photos if p.get("match") in ("sister", "near_year")]
    gaps = []
    new = {}
    _lines(new, gaps, photos, exact, sisters, dos.get("identity") or {}, (dos.get("identity") or {}).get("years") or [None, None])
    for k in ("maker_lines", "legal_lines"):
        if (facts.get(k) or {}).get("checks", {}).get("applies") is False:
            continue
        facts[k] = new[k]
    word = ("maker lines:", "legal lines:")
    dos["gaps"] = [g for g in dos.get("gaps", []) if not g.startswith(word)] + gaps
    dos["facts"] = facts
    gone = [ln for k in old for ln in old[k] if ln not in ((facts.get(k) or {}).get("value") or [])]
    if gone:
        log(f"[facts] {dos.get('cid', '')}: on a photo, not on the product - taken out of its facts: " + "; ".join(gone)[:200])
    return gone


def _lines(facts, gaps, photos, exact, sisters, idn, era):
    """Maker and legal lines: this item's own photos; if they show none, the ONE sister box closest to it (same maker,
    same era - the same flavor first, then the nearest year); other photos that print the same line count as
    agreeing sources. Never a watermark, credit or email; a watermarked photo's lines only when a clean one agrees."""
    y = idn.get("year") or 0

    def lines_of(p, mine):
        out = []
        for ln in clean_lines((p.get("panel") or {}).get(key) or [], p):   # never a watermark, credit or email
            ln = str(ln).strip()
            late = COPYRIGHT.search(ln) and _years(ln) and era[1] and min(_years(ln)) > era[1] + 1
            if ln and (mine or not COPYRIGHT.search(ln)) and not late:   # (a copyright years after the item was
                out.append(ln)                                 # made is a photo's) another box's year is not ours
        if marked(p):                                          # a watermarked photo: its words count only when a
            out = [ln for ln in out if seen_by.get(_norm(ln), set()) - {p.get("file")}]   # clean photo agrees
        return out
    seen_by = {}                                               # line -> the clean (unmarked) photos that print it
    for p in photos:
        if marked(p):
            continue
        for k in ("maker_lines", "legal_lines"):
            for ln in clean_lines((p.get("panel") or {}).get(k) or [], p):
                seen_by.setdefault(_norm(ln), set()).add(p.get("file"))
    near = sorted([s for s in sisters if _era_ok(s.get("years"), era) is not False],
                  key=lambda s: (-(_norm(idn.get("variant")) in _norm(s.get("product_shown"))),
                                 min([abs(v - y) for v in s.get("years") or [y + 9]]), -(s.get("quality") or 0)))
    for key in ("maker_lines", "legal_lines"):
        lines, srcs, base = [], [], None
        for p in exact:
            got = lines_of(p, True)
            if got:
                base = base or p
                lines += [ln for ln in got if _norm(ln) not in {_norm(x) for x in lines}]
        if not lines:
            base = next((s for s in near if lines_of(s, False)), None)
            lines = lines_of(base, False) if base else []
        if lines:
            want = {_norm(x) for x in lines}
            for p in exact + near:
                same = [ln for ln in lines_of(p, p in exact) if _norm(ln) in want]
                if same:
                    srcs.append(dict(_photo_src(p, " / ".join(same)), match="exact" if p in exact else p.get("match")))
        n = _independent(srcs)
        from_sister = bool(srcs) and base is not None and base not in exact
        facts[key] = {"value": lines or None, "sources": srcs,
                      "checks": {"sources_agreeing": n, "from": "a sister box of the same era" if from_sister else
                                 "this item's own photos" if srcs else ""},
                      "status": _status(n)}
        if from_sister:
            gaps.append(f"{key.replace('_', ' ')}: copied from a sister box of the same era (same maker), not this "
                        "exact box")
        if not lines:
            gaps.append(f"{key.replace('_', ' ')}: not readable on any photo of this item or its era")


def _web_reference(key, code12, era, log):
    """A web source for nutrition / ingredients, kept only as a reference: Open Food Facts (with the date it was
    filed). It is printed only if it is dated inside the item's era (it never is for an old item)."""
    url = (f"https://world.openfoodfacts.org/api/v2/product/0{code12}.json?fields=product_name,serving_size,"
           "nutriments,ingredients_text,created_t,last_modified_t")
    try:
        j = json.loads(websearch.read(url, 60000, log=log) or "{}")
    except Exception:
        return None
    p = j.get("product") or {}
    if j.get("status") != 1:
        return None
    import datetime
    yrs = [datetime.datetime.fromtimestamp(p[k], datetime.timezone.utc).year for k in ("created_t",) if p.get(k)]
    val = p.get("ingredients_text") if key == "ingredients" else \
        {k: v for k, v in (p.get("nutriments") or {}).items() if k.endswith("_serving")} or None
    if not val:
        return None
    return {"value": val, "source": _web_src(url.split("?")[0], f"{p.get('product_name', '')} - filed {yrs}"),
            "years": yrs, "era_ok": _era_ok(yrs, era)}


PACK_RX = re.compile(r"(?i)\b(\d{1,2})\s*(?:individually\s+wrapped\s+)?(pouch|pouches|packs?|packets?|bags?|sleeves?|"
                     r"wrappers?|trays?)\s+(?:of|with|containing)\s+(\d{1,2})\b|\b(\d{1,2})\s+(?:\w+\s+){0,2}per\s+"
                     r"(pouch|pack|packet|bag|sleeve|wrapper|tray)\b")


def _packs_in(text):
    """'4 pouches of 2' -> (4, 2, 'pouch'); '2 pastries per pouch' -> (None, 2, 'pouch')"""
    for m in PACK_RX.finditer(str(text or "")):
        if m.group(1):
            return int(m.group(1)), int(m.group(3)), re.sub(r"(es|s)$", "", m.group(2).lower())
        if m.group(4):
            return None, int(m.group(4)), m.group(5).lower()
    return None


def contents_fact(dos, facts, log=print, web=True):
    """What is inside: the count (a fact), how they are packed (a photo or page that says so, else the family's
    typical packing marked unverified), sizes (only if a source gives them; else estimated to fill the box and
    marked so)."""
    idn = dos["identity"]
    total = None
    for t in (facts.get("count") or {}).get("value"), idn.get("count"):
        got = count_set(t)
        if got:
            total = max(got)
            break
    srcs, packs, per, kind = [], None, None, None
    for p in dos.get("photos", []):
        if p.get("match") != "exact" and p.get("file") != dos.get("picked"):
            continue
        for ln in (p.get("panel") or {}).get("contents_lines") or []:
            got = _packs_in(ln)
            if got:
                packs, per, kind = got[0] or packs, got[1], got[2]
                srcs.append(_photo_src(p, ln))
    if web and per is None and total and idn.get("line"):
        q = f"{idn.get('line')} {idn.get('variant', '')} {total} count how many per pouch"
        for r in websearch.search(re.sub(r"\s+", " ", q), n=8, log=log):
            got = _packs_in(f"{r.get('title', '')}. {r.get('snippet', '')}")
            if got and (not got[0] or got[0] * got[1] == total) and total % got[1] == 0:
                per, kind = got[1], got[2]
                packs = got[0] or total // got[1]
                srcs.append(_web_src(r["url"], r.get("snippet") or r.get("title")))
    status = _status(_independent(srcs))
    note = ""
    if per is None and total:
        fam = _family_typical(dos, total)
        if fam:
            packs, per, kind = fam["packs"], fam["per_pack"], fam["pack"]
            srcs.append(fam["source"])
            status = "unverified"
            note = "how they are packed is the family's usual packing (no photo or page of this item says it)"
    if per and not packs and total:
        packs = total // per
    value = {"count": total, "packs": packs, "per_pack": per, "pack": kind, "item": idn.get("unit") or "",
             "sizes_mm": None, "sizes_note": "no source gives the inside sizes - estimated to fill the box"} \
        if total else None
    if not total:
        status = "missing"
        dos["gaps"].append("contents: how many items are inside was not found - the box is built empty")
    elif per is None:
        dos["gaps"].append("contents: how the items are packed inside was not found - built as loose items")
    elif note:
        dos["gaps"].append("contents: " + note)
    return {"value": value, "sources": srcs, "checks": {"packs_x_per_pack_equals_count":
                                                        bool(value and packs and per and packs * per == total),
                                                        "note": note}, "status": status}


def _family_typical(dos, total):
    """The family recipe's usual packing for this count (factory/recipes/<family>.json, 'contents' entries whose
    packs x per pack equals this item's count) - marked unverified, with the recipe's own receipt."""
    fams = [dos.get("family"), "folding_carton"]
    for fam in [f for f in fams if f]:
        p = os.path.join(HERE, "factory", "recipes", fam + ".json")
        try:
            r = json.load(open(p))
        except Exception:
            continue
        refs = [c.get("url") for c in r.get("checked_against", []) if isinstance(c, dict) and c.get("url")]
        for name, c in (r.get("contents") or r.get("typical_contents") or {}).items():
            n, k = c.get("pouches") or c.get("packs"), c.get("per_pouch") or c.get("per_pack")
            if n and k and n * k == total:
                return {"packs": n, "per_pack": k, "pack": "pouch" if c.get("pouches") else "pack",
                        "source": {"kind": "web" if refs else "photo", "url": refs[0] if refs else "",
                                   "file": "" if refs else p,
                                   "quote": f"family recipe {fam}.json '{name}': {n} x {k} ({c.get('sizes_note', '')})"[:300]},
                        "sizes": (c.get("pouch_mm"), c.get("pastry_mm"))}
    return None


def carton_contents(dos, W, D, H, out_path, board_mm=0.45):
    """The inside of a carton for shapes/carton.py, as a JSON file (None when nothing is known to be inside):
    {"pouches", "per_pouch", "pouch_mm": [w, h, d], "pastry_mm": [w, h, d], "rows", "cols", "pouch_kind",
     "pastry_kind", "layout", "sizes_note", "status", "sources"}. Sizes no source gives are worked out to fill the
    box's real inside, and say so."""
    f = (dos.get("facts") or {}).get("contents") or {}
    v = f.get("value") or {}
    if not v.get("count"):
        return None
    W, D, H = W * 1000, D * 1000, H * 1000
    iw, idp, ih = W - 6 * board_mm - 8, D - 6 * board_mm - 2, H - 8 * board_mm - 4
    total = int(v["count"])
    per = int(v.get("per_pack") or 1)
    packs = int(v.get("packs") or total // per)
    pack_d = per * 10.0 + 3                                   # about 10 mm a piece, to choose rows and columns
    cols = max(1, min(packs, int(round(idp / pack_d))))
    rows = -(-packs // cols)
    pd = idp / cols - 0.6
    ph = ih / rows - 1.0
    pw = iw
    item = [pw - 22, ph - 19, max(4.0, (pd - 3) / per - 0.4)]
    out = {"pouches": packs, "per_pouch": per, "pouch_mm": [round(pw, 1), round(ph, 1), round(pd, 1)],
           "pastry_mm": [round(x, 1) for x in item], "rows": rows, "cols": cols,
           "pouch_kind": "foil_laminate" if v.get("pack") in ("pouch", "packet", "wrapper") else "paper",
           "pastry_kind": "food_baked" if (dos.get("identity") or {}).get("food") else "molded_plastic",
           "loose": not v.get("per_pack"),
           "layout": f"{cols} deep, {rows} high, standing on their long edge",
           "sizes_note": "sizes worked out to fill this box's real inside "
                         f"({W:.0f} x {D:.0f} x {H:.0f} mm), not measured from the real {v.get('pack') or 'item'}",
           "status": f.get("status"), "sources": f.get("sources", [])}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=1)
    return out_path


if __name__ == "__main__":
    import dossier
    d = dossier.load(sys.argv[1])
    print(json.dumps(gather(d), indent=1)[:6000])
