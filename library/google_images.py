"""Google Images, the way your X bot uses X: its own ordinary Chromium window with its own profile folder
(~/.hellbox/ref-browser), started normally and driven at a person's pace. Never your browser or your accounts.
If Google ever shows "I'm not a robot", nothing answers it: the hunt says so, you tick it once in that window,
and the next search goes on.

    python library/google_images.py "90s duracell aa battery"      prints the full-size image links
"""
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


def search(q, most=30, min_side=500, log=print):
    """[(image url, width, height)] for a Google Images search, largest real photos first."""
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
            page.goto("https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "2", "hl": "en"}),
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            page.mouse.wheel(0, 2500)                         # the first rows load more as a person scrolls
            page.wait_for_timeout(1500)
            if "/sorry/" in page.url:
                log("[google] Google wants a person to tick 'I'm not a robot' in the reference browser window "
                    "on your Mac. Tick it once; the next search goes on. Nothing here answers it.")
                return []
            html = page.content()
        finally:
            page.close()
    seen, out = set(), []
    for u, h, w in re.findall(r'\["(https?://[^"]+?)",(\d+),(\d+)\]', html):
        u = u.encode().decode("unicode_escape") if "\\u" in u else u
        if "gstatic.com" in u or "encrypted-tbn" in u or u in seen:
            continue
        if int(w) < min_side or int(h) < min_side:
            continue
        seen.add(u)
        out.append((u, int(w), int(h)))
    log(f"[google] '{q}': {len(out)} full-size photos")
    return out[:most]


if __name__ == "__main__":
    for u, w, h in search(" ".join(sys.argv[1:])):
        print(w, h, u)
