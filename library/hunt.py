"""Photo hunt for one catalog item, run on the Mac by the local pipeline (no Claude, no paid service).

Sources, in order:
  1. your own photos (remaster/refs-mine/<id>*.jpg) - always used
  2. eBay listings (a real browser engine, Playwright + Chromium, so eBay sees an ordinary visitor; every photo
     of each matching listing is saved, full size)
  3. Open Food Facts, Wikimedia Commons, Openverse (free photo sites, plain web requests)
Listing titles must match the item and, when the catalog gives a year, carry no year outside the era (+/- 3).
Photos are only saved here; the local vision model decides later which ones are usable.

    python library/hunt.py <catalog id> "<search words>" [year]
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Safari/605.1.15")


def era_ok(title, year, slack=3):
    """A listing that names a year outside year +/- slack is another version of the product."""
    if not year:
        return True
    ys = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", title)]
    return not ys or any(abs(y - year) <= slack for y in ys)


def words_ok(title, words):
    """Most of the important search words must be in the title."""
    ws = [w for w in re.findall(r"[a-z0-9]+", words.lower()) if len(w) > 2 and w not in ("vintage", "the", "and")]
    t = title.lower()
    return not ws or sum(w in t for w in ws) >= max(1, int(0.6 * len(ws)))


def ebay(words, year=None, listings=8, log=print):
    """[(photo url, listing url, title)] from eBay search results, every photo of each good listing."""
    from playwright.sync_api import sync_playwright
    q = (words + (" vintage" if year and year < 2015 else "")).strip()
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent=UA, viewport={"width": 1400, "height": 1000})
        pg.goto("https://www.ebay.com/sch/i.html?_nkw=" + urllib.request.quote(q) + "&_ipg=120", timeout=60000)
        pg.wait_for_timeout(2500)
        found = pg.evaluate("""() => { const m = {};
            document.querySelectorAll('a[href*="/itm/"]').forEach(a => {
              const id = (a.href.match(/itm\\/(\\d+)/) || [])[1]; if (!id) return;
              const li = a.closest('li'); if (!li) return;
              const t = ((li.querySelector('.s-item__title, .s-card__title, [role=heading]') || {}).innerText || '');
              if (!(id in m)) m[id] = ''; if (t && !m[id]) m[id] = t.split('\\n')[0];
            }); return m; }""")
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
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ai", "remaster"))
    import refs as R
    out = []
    for f in R.openfoodfacts(words, n=6) + R.commons(words, n=8) + R.openverse(words, n=8):
        if any(k in f["license"].lower() for k in R.OK_LICENSES):
            out.append((f["url"], f["page"], f.get("by", "") + " / " + f["license"]))
    return out


def run(cid, words, year=None, log=print):
    d = os.path.join(WORK, "hunt", cid)
    os.makedirs(d, exist_ok=True)
    got = []
    mine = os.path.join(WORK, "refs-mine")
    for f in sorted(os.listdir(mine)) if os.path.isdir(mine) else []:
        if f.startswith(cid) and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            got.append({"file": os.path.join(mine, f), "from": "your photo", "page": "", "title": ""})
    try:
        hits = ebay(words, year, log=log)
    except Exception as e:
        log(f"[hunt] eBay search did not work here: {e}")
        hits = []
    hits += free_sites(words)
    from PIL import Image
    for n, (url, page, title) in enumerate(hits):
        p = os.path.join(d, f"p{n:03d}.jpg")
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
        got.append({"file": p, "from": "eBay" if "ebay" in url else "free photo site", "page": page, "title": title})
    json.dump(got, open(os.path.join(d, "found.json"), "w"), indent=1)
    log(f"[hunt] {cid}: {len(got)} photos saved")
    return got


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
