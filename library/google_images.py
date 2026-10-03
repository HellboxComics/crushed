"""Google Images, the way your X bot uses X: its own ordinary Chromium window with its own profile folder
(~/.hellbox/ref-browser), started normally and driven at a person's pace. Never your browser or your accounts.
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


def ensure():
    if _up():
        return
    os.makedirs(PROFILE, exist_ok=True)
    subprocess.Popen([_exe(), f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
                      "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
                      "https://www.google.com/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(40):
        if _up():
            time.sleep(3)
            return
        time.sleep(0.5)
    raise RuntimeError("the reference browser did not start")


def _open(url, scroll=True, js=None, log=print):
    """One page in the bot's own window, at a person's pace (20 s between searches). -> (html, js result) or
    (None, None) when Google asks for a person to tick 'I'm not a robot' (never answered here)."""
    from playwright.sync_api import sync_playwright
    ensure()
    wait = GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    with sync_playwright() as pw:
        br = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = br.contexts[0] if br.contexts else br.new_context()
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


def search_full(q, most=30, min_side=500, log=print):
    """[{"url", "w", "h", "page", "title"}] for a Google Images search, largest real photos first in Google's
    order. page / title are '' when Google's page doesn't carry them."""
    html, _ = _open("https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "2", "hl": "en"}),
                    log=log)
    if html is None:
        return []
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
