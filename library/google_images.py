"""Google Images, the way your X bot uses X: its own ordinary Chromium window with its own profile folder
(~/.hellbox/ref-browser), started by Playwright itself and driven at a person's pace. Never your browser or your
accounts.
If Google ever shows "I'm not a robot", nothing answers it: the hunt says so, you tick it once in that window,
and the next search goes on.

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

HB = os.path.expanduser("~/.hellbox")
PROFILE = os.path.join(HB, "ref-browser")
PORT = 9334                                   # Hart's X window uses 9333
GAP = 20                                      # seconds between searches, like a person
_last = [0.0]
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


def _open(url, scroll=True, js=None, log=print):
    """One page in the bot's own window, at a person's pace (20 s between searches). -> (html, js result) or
    (None, None) when Google asks for a person to tick 'I'm not a robot' (never answered here)."""
    wait = GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        ctx = _context(log)
        page = ctx.new_page()
    except Exception as e:
        log(f"[google] the reference browser could not be used ({str(e).splitlines()[0][:120]}) - starting it again")
        restart(log)
        ctx = _context(log)
        page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        if scroll:
            page.mouse.wheel(0, 2500)                     # the first rows load more as a person scrolls
            page.wait_for_timeout(1500)
        if "/sorry/" in page.url:
            log("[google] Google wants a person to tick 'I'm not a robot' in the reference browser window "
                "on your Mac. Tick it once; the next search goes on. Nothing here answers it.")
            return None, None
        return page.content(), (page.evaluate(js) if js else None)
    finally:
        page.close()


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


def search_full(q, most=30, min_side=500, log=print):
    """[{"url", "w", "h", "page", "title"}] for a Google Images search, largest real photos first in Google's
    order. page / title are '' when Google's page doesn't carry them. Raises Captcha when Google blocks."""
    html, _ = _open("https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "2", "hl": "en"}),
                    log=log)
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


if __name__ == "__main__":
    for o in search_full(" ".join(sys.argv[1:])):
        print(o["w"], o["h"], o["url"], "|", o["page"], "|", o["title"])
