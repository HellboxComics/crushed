"""WEB SEARCH AND PAGE READING for the item's facts (no paid service, no API key, nothing to sign up for).

    results = websearch.search("pop tarts frosted strawberry 14.7 oz upc")   # [{title, url, snippet}]
    text = websearch.read("https://www.upcitemdb.com/upc/038000317101")      # the page's words, scripts removed

Searches are tried in this order until one answers:
  1. the free `ddgs` / `duckduckgo_search` Python library, if it is installed
  2. DuckDuckGo's plain "lite" page (an ordinary web request, the same way your AI's own search tool does it)
  3. DuckDuckGo's plain html page
  4. Google's ordinary results page, in your bot's own Chromium window (google_images.web_search), if nothing
     else answered
Polite: a normal browser name, timeouts, a pause between requests to the same site. Every answer and every page
read is kept under ~/crushed-render/remaster/web/ so nothing is fetched twice (searches for 30 days, pages for 90).
"""
import hashlib
import html as _html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
CACHE = os.path.join(WORK, "web")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Safari/605.1.15")
GAP = 1.5                          # seconds between two requests to the same site
SEARCH_DAYS, PAGE_DAYS = 30, 90
_last = {}


def _key(s):
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:20]


def _cache(kind, key, days, value=None):
    """Read (value None) or write one cached answer."""
    d = os.path.join(CACHE, kind)
    p = os.path.join(d, key + ".json")
    if value is None:
        try:
            got = json.load(open(p))
            if time.time() - got.get("at", 0) < days * 86400:
                return got
        except Exception:
            return None
        return None
    os.makedirs(d, exist_ok=True)
    value["at"] = time.time()
    tmp = p + ".tmp"
    json.dump(value, open(tmp, "w"), indent=1)
    os.replace(tmp, p)
    return value


def _polite(url):
    host = urllib.parse.urlparse(url).netloc
    wait = GAP - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()


def get(url, timeout=25, data=None, days=PAGE_DAYS, log=None):
    """The raw page (HTML or JSON text), '' if it can't be had. Kept for `days`."""
    key = _key(("POST " if data else "") + url + (json.dumps(data, sort_keys=True) if data else ""))
    got = _cache("pages", key, days)
    if got is not None:
        return got.get("raw", "")
    _polite(url)
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8",
                                                          "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(3_000_000)
            enc = r.headers.get_content_charset() or "utf-8"
            status = r.status
    except Exception as e:
        if log:
            log(f"[web] could not read {url[:90]}: {e}")
        return ""
    txt = raw.decode(enc, "replace")
    if status == 200 and txt.strip():
        _cache("pages", key, days, {"url": url, "status": status, "raw": txt})
    return txt


def text_of(html):
    """The words of a page: scripts, styles and tags out, entities decoded, spaces squeezed."""
    t = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", html or "")
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def read(url, chars=20000, log=None):
    """The words on one web page (at most `chars` of them), '' if it can't be read."""
    raw = get(url, log=log)
    if raw.lstrip().startswith(("{", "[")):                   # a JSON answer (Open Food Facts): kept as it is
        return raw[:chars]
    return text_of(raw)[:chars]


# ------------------------------------------------------------------ search engines, in order
def _ddgs_lib(q, n):
    for mod in ("ddgs", "duckduckgo_search"):
        try:
            m = __import__(mod)
        except Exception:
            continue
        with m.DDGS() as dd:
            rows = list(dd.text(q, max_results=n))
        return [{"title": r.get("title", ""), "url": r.get("href") or r.get("url", ""),
                 "snippet": r.get("body", "")} for r in rows if r.get("href") or r.get("url")]
    return None


def _real_link(href):
    """DuckDuckGo's redirect link (//duckduckgo.com/l/?uddg=...) -> the real page address."""
    href = _html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    q = urllib.parse.urlparse(href)
    if "duckduckgo.com" in q.netloc:
        u = urllib.parse.parse_qs(q.query).get("uddg")
        return u[0] if u else ""
    return href


def _clean(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_lite(html):
    """Results on DuckDuckGo's lite page: each a 'result-link' with its 'result-snippet' below it (ads, which go
    through duckduckgo.com/y.js, are left out)."""
    out = []
    links = list(re.finditer(r"<a[^>]+class=['\"]result-link['\"][^>]*>(.*?)</a>", html, re.S | re.I)) or \
        list(re.finditer(r"<a[^>]+rel=['\"]nofollow['\"][^>]*>(.*?)</a>", html, re.S | re.I))
    snips = re.findall(r"<td[^>]+class=['\"]result-snippet['\"][^>]*>(.*?)</td>", html, re.S | re.I)
    for i, m in enumerate(links):
        href = re.search(r"href=['\"]([^'\"]+)['\"]", m.group(0))
        url = _real_link(href.group(1) if href else "")
        if not url.startswith("http") or "duckduckgo.com/y.js" in url:
            continue
        out.append({"title": _clean(m.group(1)), "url": url, "snippet": _clean(snips[i]) if i < len(snips) else ""})
    return out


def parse_html(html):
    """Results on DuckDuckGo's html page: 'result__a' links with 'result__snippet' text."""
    out = []
    for blk in re.split(r"(?i)<div[^>]+class=['\"][^'\"]*result__body", html)[1:]:
        a = re.search(r"<a[^>]+class=['\"]result__a['\"][^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", blk, re.S | re.I) \
            or re.search(r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*class=['\"]result__a['\"][^>]*>(.*?)</a>", blk, re.S | re.I)
        if not a:
            continue
        url = _real_link(a.group(1))
        if not url.startswith("http") or "duckduckgo.com/y.js" in url:
            continue
        s = re.search(r"class=['\"]result__snippet['\"][^>]*>(.*?)</a>", blk, re.S | re.I)
        out.append({"title": _clean(a.group(2)), "url": url, "snippet": _clean(s.group(1)) if s else ""})
    return out


def _ddg_lite(q, n):
    raw = get("https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": q, "kl": "us-en"}), days=0)
    return parse_lite(raw)[:n] if raw else None


def _ddg_html(q, n):
    raw = get("https://html.duckduckgo.com/html/", data={"q": q, "kl": "us-en"}, days=0)
    return parse_html(raw)[:n] if raw else None


def _google(q, n):
    sys.path.insert(0, HERE)
    import google_images as G
    return G.web_search(q, most=n)


ENGINES = [("ddgs", _ddgs_lib), ("duckduckgo lite", _ddg_lite), ("duckduckgo html", _ddg_html),
           ("google (your bot's browser)", _google)]


def search(q, n=8, log=None, browser=True):
    """[{title, url, snippet}] for a web search, from the first engine that answers. Kept 30 days."""
    q = re.sub(r"\s+", " ", q).strip()
    got = _cache("search", _key(f"{q}|{n}"), SEARCH_DAYS)
    if got is not None:
        return got["results"]
    for name, fn in ENGINES:
        if fn is _google and not browser:
            continue
        try:
            res = fn(q, n)
        except Exception as e:
            if log:
                log(f"[web] {name} did not answer: {e}")
            res = None
        res = [r for r in (res or []) if r.get("url", "").startswith("http")]
        if res:
            if log:
                log(f"[web] '{q}': {len(res)} results ({name})")
            _cache("search", _key(f"{q}|{n}"), SEARCH_DAYS, {"q": q, "engine": name, "results": res[:n]})
            return res[:n]
    if log:
        log(f"[web] '{q}': no search engine answered")
    return []


if __name__ == "__main__":
    if sys.argv[1].startswith("http"):
        print(read(sys.argv[1])[:3000])
    else:
        for r in search(" ".join(sys.argv[1:]), log=print):
            print(r["url"], "|", r["title"], "|", r["snippet"][:120])
