"""Photo hunt for one catalog item, run on the Mac by the local pipeline (no Claude, no paid service).

Sources, in order:
  1. your own photos (remaster/refs-mine/<id>*.jpg) - always used
  2. eBay listings (a real browser engine, Playwright + Chromium, so eBay sees an ordinary visitor; every photo
     of each matching listing is saved, full size)
  3. Open Food Facts, Wikimedia Commons, Openverse (free photo sites, plain web requests)
Listing titles must match the item and, when the catalog gives a year, carry no year outside its era (era.py).
Photos are only saved here; the local vision model decides later which ones are usable.

    python library/hunt.py <catalog id> "<search words>" [year]
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Safari/605.1.15")


def era_ok(title, year):
    """A listing that names only years outside the item's era ("90s", "early 2000s" - era.py) is another version."""
    if not year:
        return True
    import era as ERA
    a, b = ERA.span(year)
    ys = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", title)]
    return not ys or any(a <= y <= b for y in ys)


def words_ok(title, words):
    """Most of the important search words must be in the title."""
    ws = [w for w in re.findall(r"[a-z0-9]+", words.lower()) if len(w) > 2 and w not in ("vintage", "the", "and")]
    t = title.lower()
    return not ws or (ws[0] in t and sum(w in t for w in ws) >= max(1, int(0.4 * len(ws))))


KEYS = os.path.expanduser("~/.hellbox/ebay.json")      # your free eBay developer keys, kept outside the repo
_TOKEN = {}


def _ebay_token():
    """An application token from eBay's own sign-in service (client credentials, 2 hours)."""
    import base64
    if _TOKEN.get("exp", 0) > time.time() + 60:
        return _TOKEN["tok"]
    k = json.load(open(KEYS))
    auth = base64.b64encode(f"{k['client_id']}:{k['client_secret']}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    req = urllib.request.Request("https://api.ebay.com/identity/v1/oauth2/token", data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Authorization": "Basic " + auth})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    _TOKEN.update(tok=r["access_token"], exp=time.time() + int(r.get("expires_in", 7200)))
    return _TOKEN["tok"]


def _ebay_get(path):
    req = urllib.request.Request("https://api.ebay.com/buy/browse/v1/" + path, headers={
        "Authorization": "Bearer " + _ebay_token(), "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"})
    return json.loads(urllib.request.urlopen(req, timeout=40).read())


def _big(url):
    return re.sub(r"/s-l\d+\.(jpg|jpeg|png|webp)", r"/s-l1600.jpg", url)


def ebay_api(words, year=None, listings=12, log=print):
    """eBay's official search for developers (Browse API): every photo of each matching listing, full size."""
    q = (words + (" vintage" if year and year < 2015 else "")).strip()
    res = _ebay_get("item_summary/search?" + urllib.parse.urlencode({"q": q, "limit": 100}))
    items = res.get("itemSummaries", [])
    good = [it for it in items if words_ok(it.get("title", ""), words) and era_ok(it.get("title", ""), year)]
    log(f"[hunt] eBay: {len(items)} listings, {len(good)} match the item and era")
    out = []
    for it in good[:listings]:
        try:
            full = _ebay_get("item/" + urllib.parse.quote(it["itemId"]))
        except Exception as e:
            full = it
        urls = [full.get("image", {}).get("imageUrl")] + [a.get("imageUrl") for a in full.get("additionalImages", [])]
        for u in [u for u in urls if u][:12]:
            out.append((_big(u), it.get("itemWebUrl", ""), it.get("title", "")))
        time.sleep(0.3)
    return out


def ebay(words, year=None, listings=12, log=print):
    if os.path.exists(KEYS):
        return ebay_api(words, year, listings, log)
    log("[hunt] no eBay developer keys yet (~/.hellbox/ebay.json): trying the browser instead")
    return ebay_browser(words, year, listings, log)


def ebay_browser(words, year=None, listings=12, log=print):
    """[(photo url, listing url, title)] from eBay search results, every photo of each good listing."""
    from playwright.sync_api import sync_playwright
    q = (words + (" vintage" if year and year < 2015 else "")).strip()
    out = []
    found, pg, b = {}, None, None
    with sync_playwright() as p:
        # an ordinary visible-capable browser first (new headless mode of full Chromium), then a real window:
        # eBay turns away the stripped-down "headless shell". A sign-in or "are you a robot" page is never answered.
        for how in ({"headless": True, "channel": "chromium"}, {"headless": False}):
            try:
                b = p.chromium.launch(**how)
                pg = b.new_page(viewport={"width": 1400, "height": 1000}, locale="en-US")   # its own true browser name
                pg.goto("https://www.ebay.com/sch/i.html?_nkw=" + urllib.request.quote(q) + "&_ipg=120", timeout=60000)
                pg.wait_for_timeout(3000)
                found = pg.evaluate("""() => { const m = {};
                    document.querySelectorAll('a[href*="/itm/"]').forEach(a => {
                      const id = (a.href.match(/itm\\/(\\d+)/) || [])[1]; if (!id) return;
                      const li = a.closest('li'); if (!li) return;
                      const t = ((li.querySelector('.s-item__title, .s-card__title, [role=heading]') || {}).innerText || '');
                      if (!(id in m)) m[id] = ''; if (t && !m[id]) m[id] = t.split('\\n')[0];
                    }); return m; }""")
            except Exception as e:
                log(f"[hunt] eBay ({'window' if not how['headless'] else 'background'} browser) failed: {e}")
                found = {}
            if found:
                break
            title = pg.title() if pg else ""
            try:
                shot = os.path.join(WORK, "hunt", "_ebay_last_page.png")
                pg.screenshot(path=shot)
            except Exception:
                shot = ""
            log(f"[hunt] eBay showed '{title}' with no listings ({'window' if not how['headless'] else 'background'} browser); "
                f"picture of it: {shot}")
            if b:
                b.close()
                b = None
        if not found:
            return out
        good = [(i, t) for i, t in found.items() if t and t != "Shop on eBay" and words_ok(t, words) and era_ok(t, year)]
        log(f"[hunt] eBay: {len(found)} listings, {len(good)} match the item and era")
        for item, title in good[:listings]:
            try:
                pg.goto(f"https://www.ebay.com/itm/{item}", timeout=60000)
                pg.wait_for_timeout(1500)
                html = pg.content()
            except Exception as e:
                log(f"[hunt] listing {item} would not open: {e}")
                continue
            # the listing's own photos share the listing's upload stamp (the last 4 letters of the photo id)
            ids = list(dict.fromkeys(re.findall(r"images/g/([A-Za-z0-9~_-]{16})/s-l", html)))
            stamp = {}
            for i in ids:
                stamp.setdefault(i[-4:-1], []).append(i)
            mine = max(stamp.values(), key=len) if stamp else []
            for i in mine[:12]:
                out.append((f"https://i.ebayimg.com/images/g/{i}/s-l1600.jpg", f"https://www.ebay.com/itm/{item}", title))
            time.sleep(1.0)
        b.close()
    return out


def free_sites(words):
    if os.path.join(os.path.dirname(HERE), "ai", "remaster") not in sys.path:
        sys.path.append(os.path.join(os.path.dirname(HERE), "ai", "remaster"))
    import refs as R
    out = []
    for f in R.openfoodfacts(words, n=6) + R.commons(words, n=8) + R.openverse(words, n=8):
        if any(k in f["license"].lower() for k in R.OK_LICENSES):
            out.append((f["url"], f["page"], f.get("by", "") + " / " + f["license"]))
    return out


def queries(words, year):
    """How a person digs up an old product: the decade and the brand first ('90s duracell', which found the
    1990s PowerCheck batteries at once), then decade + the product, then vintage + product + year."""
    import era as ERA
    brand = words.split()[0] if words else ""
    ew = ERA.words(year) if year else ""                  # "90s", "early 2000s" - never one exact year
    qs = []
    if year and year < 2010:
        qs += [f"{ew} {brand}", f"{ew} {words}", f"vintage {words} {ew}"]
    else:
        qs += [words, f"{words} {ew}" if year else words + " product photo"]
    return list(dict.fromkeys(qs))


def run(cid, words, year=None, log=print, extra=()):
    """extra: more searches to run (the collector searches after you turn every photo down). Photos found
    before are kept; new ones are added."""
    d = os.path.join(WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    got = []
    mine = os.path.join(WORK, "refs-mine")
    for f in sorted(os.listdir(mine)) if os.path.isdir(mine) else []:
        if f.startswith(cid) and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            got.append({"file": os.path.join(mine, f), "from": "your photo", "page": "", "title": ""})
    hits = []
    try:
        import google_images as G
        import era as ERA
        qs = [ERA.in_words(q, year) if year else q for q in (list(extra) if extra else queries(words, year))]
        for q in dict.fromkeys(qs):                     # every search says the era ("90s"), never one exact year
            for r in G.search_full(q, most=15 if extra else 40, log=log):     # each photo with its source page
                hits.append((r["url"], r.get("page", ""), f"Google Images: {q}" + (f" | {r['title']}" if r.get("title") else "")))
    except Exception as e:
        log(f"[hunt] Google Images did not work here: {e}")
        if "robot" in str(e) or type(e).__name__ == "Captcha":
            raise RuntimeError(str(e))                  # a captcha stops the item (it is tried again later), never
    if os.path.exists(KEYS):                            # a hunt that "found nothing"                            # eBay only if you ever add its free keys
        try:
            hits += ebay_api(words, year, log=log)
        except Exception as e:
            log(f"[hunt] eBay: {e}")
    hits += free_sites(words)
    seen = set()
    hits = [h for h in hits if not (h[0] in seen or seen.add(h[0]))]
    from PIL import Image
    import hashlib
    for url, page, title in hits:
        p = os.path.join(d, "p" + hashlib.sha1(url.encode()).hexdigest()[:12] + ".jpg")   # one file per photo link
        if not os.path.exists(p):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=40).read())).convert("RGB")
                if min(im.size) < 400:
                    continue
                im.thumbnail((2000, 2000))
                im.save(p, quality=92)
            except Exception:
                continue
        src = "Google Images" if title.startswith("Google") else ("eBay" if "ebay" in url else "free photo site")
        got.append({"file": p, "from": src, "url": url, "page": page, "title": title})
    fj = os.path.join(d, "found.json")
    if extra and os.path.exists(fj):                    # a deeper round adds to what was found before
        before = json.load(open(fj))
        have = {g["file"] for g in before}
        got = before + [g for g in got if g["file"] not in have]
    json.dump(got, open(fj, "w"), indent=1)
    log(f"[hunt] {cid}: {len(got)} photos saved")
    return got


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
