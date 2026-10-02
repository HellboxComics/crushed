#!/usr/bin/env python3
"""
REFS -- real photos of the real product, so the drawing room copies what it actually looked like instead of guessing.

    python3 ai/remaster/refs.py game_cart            fetch photos for one object
    python3 ai/remaster/refs.py --all                every object that has a prompt and no photos yet

Where the photos come from (free, no account, no key, licenses that allow reuse):
  1. Wikimedia Commons (the photo library behind Wikipedia)
  2. Openverse (WordPress's search over Flickr and other openly licensed photo sites)
What it searches for: ai/remaster/prompts/<name>.query if it exists (the local AI writes these: the exact product,
"Nintendo 64 console 1996"), otherwise the start of the prompt.
Saved to ~/crushed-render/remaster/refs/<name>/ref1.jpg .. ref3.jpg with sources.json (who took it, license, link).
The photos only GUIDE the drawing (shape, colors, where the logo sits). They are never pasted onto a model.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "prompts")
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
REFS = os.path.join(WORK, "refs")
UA = "crushed-remaster/1.0 (reference photos for a 3D art project)"
OK_LICENSES = ("cc0", "pdm", "public domain", "by", "by-sa", "cc by", "cc-by", "cc by-sa", "cc-by-sa")


def query_for(name):
    q = os.path.join(PROMPTS, name + ".query")
    if os.path.exists(q):
        return open(q).read().strip()
    p = os.path.join(PROMPTS, name + ".txt")
    if not os.path.exists(p):
        return name.replace("_", " ")
    t = open(p).read().strip()
    t = re.split(r"[,.;:(]", t)[0]
    t = re.sub(r"^(a|an|the|one)\s+", "", t, flags=re.I)
    return " ".join(t.split()[:8])


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def commons(q, n=6):
    u = ("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": n,
        "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1024}))
    out = []
    try:
        pages = json.loads(_get(u)).get("query", {}).get("pages", {})
    except Exception:
        return out
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if ii.get("thumburl"):
            out.append({"url": ii["thumburl"], "page": ii.get("descriptionurl", ""), "license": lic,
                        "by": re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", ""))[:120], "from": "Wikimedia Commons"})
    return out


def openverse(q, n=6):
    u = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({"q": q, "page_size": n, "mature": "false"})
    out = []
    try:
        res = json.loads(_get(u)).get("results", [])
    except Exception:
        return out
    for r in res:
        if r.get("url"):
            out.append({"url": r["url"], "page": r.get("foreign_landing_url", ""), "license": r.get("license", ""),
                        "by": r.get("creator", "") or "", "from": "Openverse"})
    return out


def fetch(name, keep=3, force=False):
    d = os.path.join(REFS, name)
    if not force and os.path.exists(os.path.join(d, "sources.json")):
        return json.load(open(os.path.join(d, "sources.json")))
    os.makedirs(d, exist_ok=True)
    q = query_for(name)
    found = commons(q) + openverse(q)
    from PIL import Image
    import io
    got = []
    for f in found:
        if len(got) >= keep:
            break
        if not any(k in f["license"].lower() for k in OK_LICENSES):
            continue
        try:
            im = Image.open(io.BytesIO(_get(f["url"]))).convert("RGB")
        except Exception:
            continue
        if min(im.size) < 240:
            continue
        im.thumbnail((1024, 1024))
        p = os.path.join(d, f"ref{len(got) + 1}.jpg")
        im.save(p, quality=88)
        got.append(dict(f, file=os.path.basename(p)))
        time.sleep(0.5)                       # be polite to free services
    info = {"query": q, "photos": got, "at": time.time()}
    json.dump(info, open(os.path.join(d, "sources.json"), "w"), indent=1)
    return info


def photos(name):
    d = os.path.join(REFS, name)
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith("ref") and f.endswith(".jpg")] \
        if os.path.isdir(d) else []


def main():
    args = sys.argv[1:]
    if args == ["--all"]:
        args = sorted(os.path.basename(p)[:-4] for p in os.listdir(PROMPTS) if p.endswith(".txt")
                      and not p.endswith(".inside.txt"))
        args = [os.path.basename(a) for a in args if not os.path.exists(os.path.join(REFS, a, "sources.json"))]
    force = "--redo" in args
    for n in [a for a in args if not a.startswith("--")]:
        info = fetch(n, force=force)
        print(f"{n}: {len(info['photos'])} photo(s) for \"{info['query']}\"", flush=True)


if __name__ == "__main__":
    main()
