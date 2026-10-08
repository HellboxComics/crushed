"""Google Images, the way your X bot uses X: its own ordinary Chromium window with its own profile folder
(~/.hellbox/ref-browser), started by Playwright itself and driven at a person's pace. Never your browser or your
accounts.
If Google ever shows "I'm not a robot", nothing answers it: the hunt says so, you tick it once in that window,
and the next search goes on - and Google is left alone for half an hour first (REST), from every item.
Manners (2026-10-04, after the robot check stopped an item twice in one night): the window does not announce itself
as automated (navigator.webdriver is false, as in a person's Chrome); searches happen in ONE tab; the words are typed
into the search box when it is on the page (the address is the fallback); the wait between searches is uneven
(45-120 s), never a fixed beat; a few scrolls of different lengths, like reading.

    search(q)        -> [(image url, width, height)]                      (what the hunt has always used)
    search_full(q)   -> [{"url", "w", "h", "page", "title"}]              (also the web page each photo is on and
                                                                            its title, when Google's page has them)
    web_search(q)    -> [{"title", "url", "snippet"}]                     (Google's ordinary results, same window)

    python library/google_images.py "90s duracell aa battery"      prints the full-size image links
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HB = os.path.expanduser("~/.hellbox")
PROFILE = os.path.join(HB, "ref-browser")
PORT = 9334                                   # Hart's X window uses 9333
GAP = (45, 120)                               # seconds between searches: uneven, like a person (never a fixed beat)
REST = 30 * 60                                # after a robot check: no Google at all for this long, from any item
REST_FILE = os.path.join(HB, "google-rest.json")
_last = [0.0]
_PAGE = [None]                                # the one tab searches are made in (a person uses one tab, not a new one per search)
SEARCH_HOSTS = ("google.",)                   # pages whose search box is typed into (tests add their local page)
INFO = {}                                     # image url -> {"page", "title"} for every photo seen this run


def _exe():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        return pw.chromium.executable_path


def _up():
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", PORT))
        return True
    except Exception:
        return False
    finally:
        s.close()


_PW = [None, None]    # Playwright and the thread it was started in (sync Playwright is bound to one thread)
_CTX = [None]         # the bot's own browser window (a persistent context on PROFILE), kept open across searches


def _flags():
    extra = os.environ.get("CRUSHED_BROWSER_FLAGS", "").split()      # (tests: --headless=new --no-sandbox)
    headless = any(x.startswith("--headless") for x in extra)
    return headless, [x for x in extra if not x.startswith("--headless")]


def _close_old():
    """A reference browser from before 2026-10-04 (started by hand on the debugging port) or a stray Chromium still
    holding the profile folder: closed, so Playwright's own can open the profile. Nothing of Cody's: only
    processes started on this profile folder or this port."""
    for pat in (f"remote-debugging-port={PORT}", f"user-data-dir={PROFILE}"):
        try:
            subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=20)
        except Exception:
            pass
    for _ in range(20):
        if not _up():
            break
        time.sleep(0.5)
    time.sleep(1)


def _context(log=print):
    """The bot's own browser window, started by Playwright itself (so the two always match - 2026-10-04: a
    browser started by hand on the debugging port stopped matching the Playwright that drove it and every hunt
    failed) and kept open across searches, so a captcha Cody ticks once stays ticked. Started again when it was
    closed."""
    ctx = _CTX[0]
    if ctx is not None:
        try:
            _ = ctx.pages
            if ctx.browser is None or ctx.browser.is_connected():
                return ctx
        except Exception:
            pass
        _CTX[0] = None
    import threading
    from playwright.sync_api import sync_playwright
    if _PW[0] is not None and _PW[1] != threading.get_ident():     # started in another thread (the self-test's
        close()                                                    # probe): let go and start in this one
        try:
            _PW[0].stop()
        except Exception:
            pass
        _PW[0] = None
    if _PW[0] is None:
        _PW[0] = sync_playwright().start()
        _PW[1] = threading.get_ident()
    os.makedirs(PROFILE, exist_ok=True)
    headless, args = _flags()
    # Chromium under automation sets navigator.webdriver = true - a flag any site can read that says "a robot is
    # driving" (measured 2026-10-04: True by default, False with this switch). A person's Chrome never sets it.
    args = args + ["--disable-blink-features=AutomationControlled"]
    for attempt in (1, 2):
        try:
            _CTX[0] = _PW[0].chromium.launch_persistent_context(PROFILE, headless=headless, args=args, no_viewport=True,
                                                               ignore_default_args=["--enable-automation"])
            break
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"the reference browser did not start: {str(e).splitlines()[0][:200]}")
            log(f"[google] the reference browser could not open its profile ({str(e).splitlines()[0][:100]}) - closing "
                "whatever still holds it and trying once more")
            _close_old()
    import atexit
    atexit.register(lambda: close())
    return _CTX[0]


def close(stop=False):
    """The window closed (and, stop=True, Playwright let go too - the self-test's probe thread ends with it)."""
    try:
        if _CTX[0] is not None:
            _CTX[0].close()
    except Exception:
        pass
    _CTX[0] = None
    _PAGE[0] = None
    if stop and _PW[0] is not None:
        try:
            _PW[0].stop()
        except Exception:
            pass
        _PW[0] = _PW[1] = None


def ensure(log=print):
    """The bot's browser window is open and driven by this Playwright."""
    _context(log)


def restart(log=print):
    """Closed and started again (a fresh Chromium from the current Playwright)."""
    close()
    _close_old()
    _context(log)
    log("[google] the reference browser was started again")


def probe():
    """Really usable: a page can be opened. -> how many pages the window has (for the self-test)."""
    ctx = _context()
    p = ctx.new_page()
    try:
        p.goto("about:blank", timeout=15000)
        return len(ctx.pages)
    finally:
        p.close()


def resting():
    """Seconds Google is still being left alone after a robot check (0 when it is not). Shared by every item and
    every run through REST_FILE: one item hitting the check must not have the next item knock a minute later."""
    try:
        until = float(json.load(open(REST_FILE)).get("until") or 0)
    except Exception:
        return 0
    return max(0.0, until - time.time())


def _rest_now(log=print):
    try:
        json.dump({"until": time.time() + REST, "at": time.time()}, open(REST_FILE, "w"))
    except Exception:
        pass
    log(f"[google] Google is left alone for {REST // 60} minutes now (any item) - knocking again right after a robot "
        "check is what a robot does")


def _pace():
    """Wait like a person between searches: an uneven gap, never the same beat twice."""
    import random
    gap = random.uniform(*GAP) if isinstance(GAP, tuple) else GAP
    wait = gap - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()


def _tab(ctx):
    """The one tab searches happen in, opened once and reused (a person searches again in the same tab)."""
    pg = _PAGE[0]
    try:
        if pg is not None and not pg.is_closed():
            return pg
    except Exception:
        pass
    pages = [p for p in ctx.pages if not p.is_closed()]       # the window opens with one blank tab: use it
    _PAGE[0] = pages[0] if pages else ctx.new_page()
    return _PAGE[0]


def _type_search(page, q, log=print):
    """Search the way a person does when the search box is on the page: click it, type the words (with a short
    pause per key), press Enter, and see the page really go to that search. -> True when it did; False when the
    box was not there or Enter did not search (then the search goes by address, as before - never a guess that
    the page in front of us is the one we asked for)."""
    try:
        box = page.locator("textarea[name='q'], input[name='q']").first
        if box.count() == 0:
            return False
        before = page.url
        box.click(timeout=4000)
        box.fill("", timeout=4000)
        box.type(q, delay=70, timeout=15000)
        page.wait_for_timeout(400)
        box.press("Enter", timeout=4000)
        page.wait_for_function("u => location.href !== u", arg=before, timeout=15000)
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        got = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query).get("q", [""])[0]
        if " ".join(got.split()).lower() != " ".join(q.split()).lower():
            log(f"[google] the page went to '{got[:60]}', not the words typed - searching by address")
            return False
        return True
    except Exception as e:
        log(f"[google] the search box could not be used ({str(e).splitlines()[0][:80]}) - searching by address")
        return False


def _open(url, scroll=True, js=None, log=print, typed=None):
    """One search in the bot's own window, at a person's pace: the same tab as before, the words typed into the
    search box when it is on the page (typed = the words; the address is the fallback), an uneven wait between
    searches, a scroll like a person reading. -> (html, js result) or (None, None) when Google asks for a person
    to tick 'I'm not a robot' (never answered here; Google is then left alone for REST)."""
    left = resting()
    if left > 0:
        log(f"[google] Google is being left alone for another {int(left // 60) + 1} min after a robot check - no search")
        return None, None
    _pace()
    try:
        ctx = _context(log)
        page = _tab(ctx)
    except Exception as e:
        log(f"[google] the reference browser could not be used ({str(e).splitlines()[0][:120]}) - starting it again")
        restart(log)
        ctx = _context(log)
        page = _tab(ctx)
    done = False
    if typed and any(h in (page.url or "") for h in SEARCH_HOSTS) and "/sorry/" not in page.url:
        done = _type_search(page, typed, log)
    if not done:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    if scroll:
        import random
        for _ in range(random.randint(1, 3)):              # a person scrolls a few times, not one fixed jump
            page.mouse.wheel(0, random.randint(700, 1400))
            page.wait_for_timeout(random.randint(500, 1200))
    if "/sorry/" in page.url:
        log("[google] Google wants a person to tick 'I'm not a robot' in the reference browser window "
            "on your Mac. Tick it once; the next search goes on. Nothing here answers it.")
        _rest_now(log)
        return None, None
    return page.content(), (page.evaluate(js) if js else None)


def _unesc(s):
    """A string as written inside Google's page data (\\u003d, \\u0026, \\") -> plain text."""
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s.encode().decode("unicode_escape", "ignore") if "\\u" in s else s


_IMG = re.compile(r'\["(https?://[^"]+?)",(\d+),(\d+)\]')
_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')
_PIC = re.compile(r"\.(jpe?g|png|webp|gif|bmp|avif)(\?|$)", re.I)


def _page_info(seg, img=""):
    """The web page a photo is on and its title, from the part of Google's page data that follows the photo's own
    entry (up to the next photo). The page is the first web address there that isn't Google's or a picture file;
    the title is the first real phrase after it. -> (page, title), ('', '') when the data doesn't have them."""
    strs = [_unesc(m.group(1)) for m in _STR.finditer(seg)]
    for i, s in enumerate(strs):
        if not s.startswith(("http://", "https://")):
            continue
        host = urllib.parse.urlparse(s).netloc.lower()
        if not host or s == img or "google." in host or "gstatic." in host or "googleusercontent." in host \
                or _PIC.search(s):
            continue
        title = next((t for t in strs[i + 1:i + 6] if len(t) >= 6 and " " in t.strip()
                      and not t.startswith(("http://", "https://"))), "")
        return s, title[:300]
    return "", ""


def parse(html, min_side=500):
    """Every full-size photo on a Google Images page: [{"url", "w", "h", "page", "title"}], in Google's order."""
    hits = list(_IMG.finditer(html or ""))
    seen, out = set(), []
    for i, m in enumerate(hits):
        u, h, w = m.groups()
        u = _unesc(u)
        if "gstatic.com" in u or "encrypted-tbn" in u or u in seen:
            continue
        if int(w) < min_side or int(h) < min_side:
            continue
        seen.add(u)
        end = hits[i + 1].start() if i + 1 < len(hits) else len(html)
        page, title = _page_info(html[m.end():min(end, m.end() + 8000)], u)
        out.append({"url": u, "w": int(w), "h": int(h), "page": page, "title": title})
        INFO[u] = {"page": page, "title": title}
    return out


class Captcha(Exception):
    """Google wants a person to tick 'I'm not a robot'. A search that hit it is NOT a search with no results
    (audit 2026-10-04: it was counted as 0 photos, recorded as done, and the dossier marked complete)."""


BRAVE_KEY = os.path.expanduser("~/.hellbox/brave.json")       # {"key": "..."} - Cody's own Brave Search API key


def brave_key():
    try:
        return (json.load(open(BRAVE_KEY)) or {}).get("key") or None
    except Exception:
        return None


def brave_images(q, most=30, min_side=500, log=print):
    """Brave's official image search (Cody said yes, 2026-10-05 22:57): GET api.search.brave.com/res/v1/images/search
    with q, count (1-200), safesearch, country; header X-Subscription-Token; each result carries properties.url /
    .width / .height (the full image), url (its web page), title, confidence (api-dashboard.search.brave.com/
    api-reference/images/image_search). -> the same records the Google path gives, or None when there is no key."""
    key = brave_key()
    if not key:
        return None
    req = urllib.request.Request("https://api.search.brave.com/res/v1/images/search?" + urllib.parse.urlencode(
        {"q": q[:400], "count": str(min(200, max(1, most * 3))), "safesearch": "off", "country": "US"}),
        headers={"X-Subscription-Token": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    out = []
    for it in data.get("results") or []:
        pr = it.get("properties") or {}
        u, w, h = pr.get("url"), pr.get("width") or 0, pr.get("height") or 0
        if not u or (w and h and (int(w) < min_side or int(h) < min_side)):
            continue
        out.append({"url": u, "w": int(w or 0), "h": int(h or 0), "page": it.get("url") or "", "title": (it.get("title") or "")[:300],
                    "confidence": it.get("confidence")})
        INFO[u] = {"page": out[-1]["page"], "title": out[-1]["title"]}
    log(f"[brave] '{q}': {len(out)} full-size photos ({sum(1 for o in out if o['page'])} with their web page)")
    return out[:most]


def search_full(q, most=30, min_side=500, log=print):
    """[{"url", "w", "h", "page", "title"}] for an image search, largest real photos first. Brave's official API
    when its key is on this Mac (no browser, no robot checks); else the browser path against Google Images.
    page / title are '' when the source doesn't carry them. Raises Captcha when Google blocks."""
    if brave_key():
        try:
            got = brave_images(q, most, min_side, log)
            if got is not None:
                return got
        except Exception as e:
            log(f"[brave] '{q}': the API call failed ({str(e)[:120]}) - the browser path is used")
    left = resting()
    if left > 0:
        raise Captcha(f"Google is being left alone for another {int(left // 60) + 1} min after a robot check")
    html, _ = _open("https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "2", "hl": "en"}),
                    log=log, typed=q)
    if html is None:
        raise Captcha("Google Images asks a person to tick 'I'm not a robot' in the reference browser on the Mac")
    out = parse(html, min_side)
    log(f"[google] '{q}': {len(out)} full-size photos ({sum(1 for o in out if o['page'])} with their web page)")
    return out[:most]


def search(q, most=30, min_side=500, log=print):
    """[(image url, width, height)] for a Google Images search, largest real photos first."""
    return [(o["url"], o["w"], o["h"]) for o in search_full(q, most, min_side, log)]


WEB_JS = """() => { const out = [], seen = new Set();
  document.querySelectorAll('a h3').forEach(h => {
    const a = h.closest('a'); if (!a || !a.href || !/^https?:/.test(a.href)) return;
    let host = ''; try { host = new URL(a.href).hostname; } catch (e) { return; }
    if (/(^|\\.)google\\./.test(host) || seen.has(a.href)) return;
    seen.add(a.href);
    const title = (h.innerText || '').trim();
    let box = a;
    for (let i = 0; i < 6 && box.parentElement; i++) {
      box = box.parentElement;
      if ((box.innerText || '').length > title.length + 80) break;
    }
    const snip = (box.innerText || '').replace(title, '').replace(/\\s+/g, ' ').trim().slice(0, 400);
    out.push({title: title, url: a.href, snippet: snip});
  });
  return out; }"""


def web_search(q, most=8, log=print):
    """Google's ordinary web results in the same window: [{"title", "url", "snippet"}] (each result's title is a
    heading inside its link - the way Google has marked results for years)."""
    _, rows = _open("https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "hl": "en"}), scroll=False,
                    js=WEB_JS, log=log)
    rows = [r for r in (rows or []) if r.get("url")]
    log(f"[google] web '{q}': {len(rows)} results")
    return rows[:most]


# ------------------------------------------------------------------ marketplace listings
# (Cody, 2026-10-07 00:32: "one easy search on ebay and I find every angle you could possibly ask for. why isn't AI
# checking there for images as well?") A seller's listing is ONE physical copy of the item photographed from every
# side - the most complete set of views a round label can get. Same window, same manners as the image search.
_ITEM = re.compile(r'https?://www\.ebay\.com/itm/(\d{9,14})')
_EBIMG = re.compile(r'https?://i\.ebayimg\.com/images/g/([A-Za-z0-9~_\-]{6,})/s-l\d+\.(?:jpg|jpeg|webp|png)', re.I)


def listing_ids(html, most=8):
    """The item numbers on an eBay search page, in the page's order, each once."""
    out = []
    for m in _ITEM.finditer(html or ""):
        if m.group(1) not in out and m.group(1) != "123456":
            out.append(m.group(1))
    return out[:most]


def listing_photos(html, most=16):
    """Every gallery photo of one eBay listing, each at the largest size eBay serves (s-l1600), each once."""
    out = []
    for m in _EBIMG.finditer(html or ""):
        u = f"https://i.ebayimg.com/images/g/{m.group(1)}/s-l1600.jpg"
        if u not in out:
            out.append(u)
    return out[:most]


_SOLD_SIGNIN = [False]
LINKS_JS = """() => Array.from(document.querySelectorAll('a[href*="/itm/"]')).map(a => [a.href, (a.innerText || a.getAttribute('aria-label') || '').trim()])"""


def search_listings(q, most=24, log=print):
    """[{"id", "page", "title"}] on eBay's search pages for q - for sale AND sold (Cody, 2026-10-07 00:51) - read
    off the result links themselves (their text is the listing's title). Pages are not opened here."""
    out, seen = [], set()
    for extra, what in (({}, "for sale"), ({"LH_Sold": "1", "LH_Complete": "1"}, "sold")):
        if what == "sold" and _SOLD_SIGNIN[0]:           # eBay asked for a sign-in once: not asked again this run
            continue                                    # (each try cost a paced page load - 2026-10-07 21:20)
        html, rows = _open("https://www.ebay.com/sch/i.html?" + urllib.parse.urlencode(dict({"_nkw": q}, **extra)),
                           js=LINKS_JS, log=log)
        n = 0
        for href, text in (rows or []):
            m = re.search(r"/itm/(?:[^/?#]+/)?(\d{9,14})", href or "")
            if not m or m.group(1) == "123456":
                continue
            title = re.sub(r"\s+", " ", text or "").replace("Opens in a new window or tab", "").strip()[:200]
            if m.group(1) in seen:                        # each result has several links (the picture's has no
                row = next((r for r in out if r["id"] == m.group(1)), None)   # text): the longest text is the title
                if row is not None and len(title) > len(row["title"]):
                    row["title"] = title
                continue
            seen.add(m.group(1))
            out.append({"id": m.group(1), "page": f"https://www.ebay.com/itm/{m.group(1)}", "title": title, "sold": what == "sold"})
            n += 1
        if not n and html and "<title>Sign in" in html:   # eBay shows sold results only to a signed-in person
            _SOLD_SIGNIN[0] = True
            log(f"[ebay] eBay asks for a sign-in before it shows {what} listings - sign in once in the reference "
                "browser window on the Mac if you want them; nothing here signs in")
        if not n and html:                                # nothing read: the page is kept to see why
            try:
                open(os.path.join(HB, f"ebay-{what.replace(' ', '-')}-last.html"), "w").write(html)
            except Exception:
                pass
        log(f"[ebay] '{q}' ({what}): {n} listings")
    return out[:most]


def listing(page, log=print):
    """One listing's whole photo gallery: [url, ...] at eBay's largest size."""
    h, _ = _open(page, scroll=False, log=log)
    return listing_photos(h)


def listings(q, most=8, log=print):
    """[{"page", "title", "photos": [url, ...]}] - the first `most` listings of a search with their galleries."""
    out = []
    for L in search_listings(q, log=log)[:most]:
        photos = listing(L["page"], log)
        if photos:
            out.append(dict(L, photos=photos))
    return out

if __name__ == "__main__":
    for o in search_full(" ".join(sys.argv[1:])):
        print(o["w"], o["h"], o["url"], "|", o["page"], "|", o["title"])


# ------------------------------------------------------------------ listings on other marketplaces
# (Cody, 2026-10-08 11:28: "ebay is one of many sources it should be looking") A collector's or seller's page on
# Etsy, WorthPoint (sold-item archive), Mercari, Ruby Lane, ShopGoodwill, Poshmark - or a collector's post on
# Reddit or Flickr - is, like an eBay listing, one real copy photographed from several sides. Found through Google's
# ordinary web search with its documented site: and OR operators; each page's own large photos are read off it.
MARKETS = ("etsy.com", "worthpoint.com", "mercari.com", "rubylane.com", "shopgoodwill.com", "poshmark.com",
           "reddit.com", "flickr.com")
PAGE_IMG_JS = """(least) => { const out = new Set();
  const add = (u) => { if (u && /^https?:/.test(u)) out.add(u); };
  document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]').forEach(m => add(m.content));
  document.querySelectorAll('img').forEach(i => {
    const big = Math.max(i.naturalWidth || 0, i.naturalHeight || 0);
    const ss = (i.getAttribute('srcset') || i.getAttribute('data-srcset') || '').split(',').map(x => x.trim().split(' ')[0]).filter(Boolean);
    if (big >= least) add(i.currentSrc || i.src);
    if (ss.length && big >= least / 2) add(ss[ss.length - 1]);
    const lazy = i.getAttribute('data-src') || i.getAttribute('data-zoom-src') || i.getAttribute('data-full');
    if (lazy && big >= least / 3) add(lazy);
  });
  return Array.from(out); }"""


def market_pages(q, most=12, log=print):
    """[{"id", "page", "title"}] - pages on other marketplaces and collectors' sites for q (one Google web search)."""
    sites = " OR ".join(f"site:{m}" for m in MARKETS)
    rows = web_search(f"{q} ({sites})", most=most * 2, log=log)
    out = []
    for r in rows:
        host = urllib.parse.urlparse(r["url"]).netloc.lower()
        if any(host == m or host.endswith("." + m) for m in MARKETS):
            out.append({"id": r["url"], "page": r["url"], "title": r.get("title", ""), "site": host})
    log(f"[market] '{q}': {len(out)} pages on " + ", ".join(sorted({o['site'] for o in out})[:6]))
    return out[:most]


def page_photos(page, most=12, least=500, log=print):
    """The large photos on one marketplace page: [url, ...] (the page's share image first, then its gallery)."""
    _, urls = _open(page, scroll=True, js=f"() => ({PAGE_IMG_JS})({least})", log=log)
    urls = [u for u in (urls or []) if not re.search(r"(logo|icon|avatar|sprite|badge|placeholder)", u, re.I)]
    return urls[:most]
