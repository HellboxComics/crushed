"""The reference browser behaves like a person, not a bot (2026-10-04, after Google's robot check stopped the
Duracell twice in one night): it does not announce itself as automated, it searches in ONE tab, it types into the
search box when there is one (address as the fallback), it waits an uneven while between searches, and after a
robot check it leaves Google alone for a rest - from every item. Proven on a local page shaped like a search page."""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import time

HOME = tempfile.mkdtemp()
os.environ["HOME"] = HOME
os.environ["CRUSHED_BROWSER_FLAGS"] = "--headless=new --no-sandbox"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import google_images as G  # noqa: E402

G.HB = HOME
G.PROFILE = os.path.join(HOME, "ref-browser")
G.REST_FILE = os.path.join(HOME, "google-rest.json")
ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


PAGE = b"""<html><body><form action="/search"><textarea name="q"></textarea></form>
<script>document.querySelector('textarea').addEventListener('keydown', e => { if (e.key === 'Enter' && !location.search.includes('noenter')) { e.preventDefault(); document.forms[0].submit(); } });</script>
<script>document.title = 'q=' + new URLSearchParams(location.search).get('q') + ' webdriver=' + navigator.webdriver;</script>
<p id="q"></p><script>document.getElementById('q').textContent = 'QUERY:' + (new URLSearchParams(location.search).get('q') || '');</script>
</body></html>"""
SEEN = []


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        SEEN.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


srv = socketserver.TCPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"

# the pace is checked separately; here searches must not sleep a minute each
G.GAP = (0.1, 0.3)

# 1. the first search goes by address (no search page open yet); the browser does not say it is a robot
t0 = time.time()
html, wd = G._open(base + "/search?q=first+words", scroll=False, js="navigator.webdriver", log=lambda *a: None)
check(html and "QUERY:first words" in html, "a search by address loads")
check(wd is False, f"navigator.webdriver is {wd!r} - the window does not announce itself as automated")
tab1 = G._PAGE[0]

# 2. the second search: typed into the box on the page that is open, in the SAME tab
G.SEARCH_HOSTS = ("google.", "127.0.0.1")
SEEN.clear()
G._open(base + "/search?q=second+words", scroll=False, log=lambda *a: None, typed="second words")
page = G._PAGE[0]
check(page is tab1 and len(G._CTX[0].pages) == 1, f"one tab is reused ({len(G._CTX[0].pages)} open)")
check("QUERY:second words" in page.content() and SEEN == ["/search?q=second+words"],
      f"the words were typed into the box and submitted by the page's own form (server saw {SEEN})")
# a page whose box does NOT search on Enter (not the page we expected): the address is used, in the same tab
G._open(base + "/search?q=noenter+page", scroll=False, log=lambda *a: None)
SEEN.clear()
logs = []
G._open(base + "/search?q=third+words", scroll=False, log=logs.append, typed="third words")
check(SEEN == ["/search?q=third+words"] and "QUERY:third words" in G._PAGE[0].content() and any("by address" in l for l in logs),
      f"when Enter does not search, the address is used - never a stale page read as the answer ({logs[-1][:70] if logs else ''})")
G.SEARCH_HOSTS = ("google.",)
SEEN.clear()
G._open(base + "/search?q=fourth+words", scroll=False, log=lambda *a: None, typed="fourth words")
check(SEEN == ["/search?q=fourth+words"], "on a page that is not a search page the address is used, never a guess at a box")
src = open(G.__file__).read()

# 3. the pace: uneven, inside the band, never the fixed 20-second beat
G.GAP = (0.4, 0.9)
gaps = []
for i in range(5):
    G._last[0] = time.time()
    t = time.time()
    G._pace()
    gaps.append(time.time() - t)
check(all(0.38 <= g <= 1.0 for g in gaps) and len(set(round(g, 2) for g in gaps)) > 1,
      f"gaps between searches are uneven and inside the band: {[round(g, 2) for g in gaps]}")
check(G.GAP != 20 and isinstance(G.GAP, tuple), "no fixed beat")

# 4. a robot check -> Google is left alone (REST) for every item, through the shared file
G._rest_now(log=lambda *a: None)
left = G.resting()
check(G.REST - 5 < left <= G.REST, f"after a robot check Google rests {int(left)} s")
logs = []
html, _ = G._open(base + "/search?q=blocked", scroll=False, log=logs.append)
check(html is None and any("left alone" in l for l in logs) and not SEEN[-1].startswith("/search?q=blocked"),
      "while resting, no search is even attempted")
json.dump({"until": time.time() - 1}, open(G.REST_FILE, "w"))
check(G.resting() == 0, "the rest ends by itself")

# 5. the automation flag is really passed to the window
check("--disable-blink-features=AutomationControlled" in src.split("def _context")[1].split("def close")[0],
      "the window is started without the automation flag")

G.close(stop=True)
srv.shutdown()
print(f"ALL {ok} PASS")
