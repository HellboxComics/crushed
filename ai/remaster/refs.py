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


MINE = os.path.join(WORK, "refs-mine")        # your own photos: <name>.jpg/.png (and <name>_2.jpg ...) always win
VISION = os.environ.get("CRUSHED_VISION", "qwen2.5vl:7b")
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA = OLLAMA if OLLAMA.startswith("http") else "http://" + OLLAMA


def queries(name, display=""):
    """Several searches, most specific first: the exact product line, then the product name, then brand + item."""
    qs = [query_for(name)]
    base = re.sub(r"\(.*?\)", "", (display or "").split(",")[0]).strip()
    base = re.sub(r"\b(circa|c\.)\s*(19|20)\d\d\b|\b(19|20)\d\d\b", "", base).strip()
    w = base.split()
    if base:
        qs.append(base)
    if len(w) >= 3:
        qs.append(" ".join(w[1:]))                       # without the maker: "Furby", "Pop-Tarts Frosted Strawberry"
        qs.append(" ".join(w[1:3]))
    if len(w) >= 2 and w[-1][:1].isupper():
        qs.append(w[-1])                                 # the product's own name ("Furby", "Discman")
    out = []
    for q in qs:
        q = " ".join(q.split())
        if q and q.lower() not in [x.lower() for x in out]:
            out.append(q)
    return out


def candidates(name, display="", most=12):
    """Real photos from the free libraries, downloaded into refs/<name>/cand*.jpg."""
    from PIL import Image
    import io
    d = os.path.join(REFS, name)
    os.makedirs(d, exist_ok=True)
    seen, got = set(), []
    for q in queries(name, display):
        per = 0
        for f in commons(q, n=8) + openverse(q, n=8):
            if len(got) >= most or per >= 4:            # a few from each search, so one weak search can't fill it
                break
            if f["url"] in seen or not any(k in f["license"].lower() for k in OK_LICENSES):
                continue
            seen.add(f["url"])
            try:
                im = Image.open(io.BytesIO(_get(f["url"]))).convert("RGB")
            except Exception:
                continue
            if min(im.size) < 300:
                continue
            im.thumbnail((1280, 1280))
            p = os.path.join(d, f"cand{len(got) + 1}.jpg")
            im.save(p, quality=90)
            got.append(dict(f, file=p, query=q))
            per += 1
            time.sleep(0.3)
        if len(got) >= most:
            break
    return got


def _ollama(path, body, timeout=600):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def ensure_vision():
    """The local vision model (Ollama's own pull; once, about 6 GB)."""
    try:
        tags = json.loads(_get(OLLAMA + "/api/tags"))
        if any(m.get("name", "").startswith(VISION) for m in tags.get("models", [])):
            return True
        _ollama("/api/pull", {"model": VISION, "stream": False}, timeout=7200)
        return True
    except Exception as e:
        print(f"vision model unavailable: {e}", flush=True)
        return False


def vet(path, display, looks=""):
    """0..10: how surely this photo shows exactly this real product, by the local vision model."""
    import base64
    q = (f"Product: {display}.\nWhat it looks like: {looks[:400]}\n\nLook at the photo. Rate from 0 to 10 how "
         "certainly it shows exactly this real product (the right brand, model, version and era), as one clearly "
         "visible item that a 3D artist could copy. 0 = a different thing, a drawing, a crowd of items or the product "
         "is tiny/hidden. Reply with only the number.")
    try:
        body = {"model": VISION, "stream": False, "options": {"temperature": 0},
                "messages": [{"role": "user", "content": q,
                              "images": [base64.b64encode(open(path, "rb").read()).decode()]}]}
        txt = json.loads(_ollama("/api/chat", body)).get("message", {}).get("content", "")
        m = re.search(r"\d+(\.\d+)?", txt)
        return min(10.0, float(m.group(0))) if m else 0.0
    except Exception as e:
        print(f"vet failed: {e}", flush=True)
        return 0.0


def choose(name, display="", looks="", keep=2, need=7.0):
    """The real photos the drawing copies: yours first; otherwise searched and checked by the local vision model.
    Returns (paths, how) where how says where they came from; ([], why) when nothing trustworthy was found."""
    mine = sorted(os.path.join(MINE, f) for f in (os.listdir(MINE) if os.path.isdir(MINE) else [])
                  if re.match(re.escape(name) + r"(_\d+)?\.(jpe?g|png|webp)$", f, re.I))
    if mine:
        return mine[:3], "your photo"
    d = os.path.join(REFS, name)
    vj = os.path.join(d, "vet.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
    else:
        cands = candidates(name, display)
        if not cands:
            v = {"picked": [], "why": "no photos found in the free libraries", "scores": []}
        elif not ensure_vision():
            v = {"picked": [], "why": "the vision model isn't available to check the photos", "scores": []}
        else:
            scores = [(vet(c["file"], display, looks), c) for c in cands]
            scores.sort(key=lambda x: -x[0])
            picked = [c["file"] for sc, c in scores if sc >= need][:keep]
            v = {"picked": picked, "why": "" if picked else f"no photo scored {need:.0f}+ for this exact product",
                 "scores": [{"score": sc, **{k: c[k] for k in ("file", "page", "license", "by", "from", "query")}}
                            for sc, c in scores]}
        json.dump(v, open(vj, "w"), indent=1)
    picked = [p for p in v["picked"] if os.path.exists(p)]
    return (picked, "found and checked") if picked else ([], v.get("why", "no reference"))


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


def judge(name, display, qa_png, review_png=None, photos=None):
    """The AI inspector's eyes: the local vision model looks at the finished model next to the real photo and the
    drawing and lists anything that would not pass in a finished video game. Returns (ok, [problems])."""
    import base64
    if not ensure_vision():
        return True, []
    imgs = [p for p in [qa_png, review_png] + list(photos or [])[:1] if p and os.path.exists(p)]
    q = (f"You are the final quality inspector for 3D game assets. The object is: {display}.\n"
         "Image 1: top row = the reference drawing from front, left, back and right; bottom row = the finished 3D "
         "model seen the same way. " + ("Image 2: the 3D model rendered from four angles. " if review_png else "")
         + ("The last image is a real photo of the real product. " if photos else "")
         + "List every visible defect that would not pass in a finished, polished video game: wrong shape or "
         "proportions, a different product than the real one, smeared, streaked, stretched or blurry paint, seams, "
         "background or white patches, mirrored or garbled text where the real product has clear text, parts "
         "floating or missing, holes, wrong colors. Reply in JSON only: {\"pass\": true|false, \"problems\": [\"...\"]}. "
         "Pass only if it is clean enough to ship.")
    try:
        body = {"model": VISION, "stream": False, "format": "json", "options": {"temperature": 0},
                "messages": [{"role": "user", "content": q,
                              "images": [base64.b64encode(open(p, "rb").read()).decode() for p in imgs]}]}
        v = json.loads(json.loads(_ollama("/api/chat", body)).get("message", {}).get("content", "{}"))
        probs = [str(x) for x in (v.get("problems") or [])][:8]
        return bool(v.get("pass")) and not probs, probs
    except Exception as e:
        print(f"inspector could not look: {e}", flush=True)
        return True, []
