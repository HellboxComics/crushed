"""Photo search through Brave's official image API when Cody's key is on the Mac (he said yes, 2026-10-05 22:57);
the browser path only without it. Checked against the documented response shape with a fake server reply."""
import io
import json
import os
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import google_images as G  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


check(G.brave_key() is None or isinstance(G.brave_key(), str), "no key: brave_key() is None")
d = tempfile.mkdtemp()
G.BRAVE_KEY = os.path.join(d, "brave.json")
check(G.brave_images("x") is None, "without a key the Brave door is closed (None), the browser path stays")
json.dump({"key": "k123"}, open(G.BRAVE_KEY, "w"))
seen = {}


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_open(req, timeout=60):
    seen["url"] = req.full_url
    seen["token"] = req.get_header("X-subscription-token")
    body = {"query": {"original": "duracell"}, "results": [
        {"title": "Duracell AA 1998", "url": "https://shop.example/p/1", "source": "shop.example",
         "thumbnail": {"src": "https://img.example/t.jpg", "width": 200, "height": 200},
         "properties": {"url": "https://img.example/full1.jpg", "width": 1600, "height": 1200}, "confidence": "high"},
        {"title": "tiny", "url": "https://x.example/2", "properties": {"url": "https://img.example/small.jpg", "width": 300, "height": 200}},
        {"title": "no size", "url": "https://x.example/3", "properties": {"url": "https://img.example/full3.jpg"}},
    ]}
    return FakeResp(json.dumps(body).encode())


urllib.request.urlopen = fake_open
got = G.search_full("duracell coppertop aa 1998", most=10, log=lambda *a: None)
check("api.search.brave.com/res/v1/images/search" in seen["url"] and "q=duracell" in seen["url"] and seen["token"] == "k123",
      "the documented endpoint, the query and the X-Subscription-Token header")
check([g["url"] for g in got] == ["https://img.example/full1.jpg", "https://img.example/full3.jpg"],
      f"full images kept (properties.url), a photo under 500 px dropped, one with no size kept ({[g['url'] for g in got]})")
check(got[0]["page"] == "https://shop.example/p/1" and got[0]["w"] == 1600 and got[0]["title"].startswith("Duracell"),
      "each record carries its web page, size and title like the Google path's records")
check(G.INFO["https://img.example/full1.jpg"]["page"] == "https://shop.example/p/1", "the page lookup table is filled too")
print(f"ALL {ok} PASS")
