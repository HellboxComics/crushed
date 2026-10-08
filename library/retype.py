"""RETYPE: the printed lines on a flat label set again as real type - the way label artwork is made (the words are
type, never a picture of type). Each line is read off the assembled label with where it sits, matched to the
words read on the real photos (their spelling wins; a line no photo's words match is left as drawn), the old soft
letters of each matched line are painted out from the band around them (OpenCV inpainting, Telea 2004), the background is smoothed
with an edge-keeping filter (bilateral, Tomasi & Manduchi 1998) so the copper and black read as printed ink, not
noise, and each line is drawn again crisp at the size, place and color it had. A line printed twice (two views
overlapping) is printed once. (Cody, 2026-10-08: "as high definition and as quality as the best saleable
assets"; the stitched letters were soft and blotchy at 4096 px - each drawn view held the battery ~330 px across.)

    from retype import retype
    sharp, notes = retype(label_float_HxWx3, vocab_lines, log, scale=2)
"""
import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# the type: condensed sans-serif bold, as the era's battery labels used; the first face found on this Mac wins
FACES = {
    "bold": [("/System/Library/Fonts/HelveticaNeue.ttc", ("Condensed Bold", "Bold")),
             ("/System/Library/Fonts/Helvetica.ttc", ("Bold",)),
             ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", ()),
             ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", ())],
    "heavy": [("/System/Library/Fonts/HelveticaNeue.ttc", ("Condensed Black", "Bold")),
              ("/System/Library/Fonts/Supplemental/Arial Black.ttf", ()),
              ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", ())],
}
_FACE_CACHE = {}


def face(kind, px):
    """A font of `kind` (bold / heavy) at px pixels: a named style inside a font collection when it has one."""
    key = (kind, px)
    if key in _FACE_CACHE:
        return _FACE_CACHE[key]
    for path, styles in FACES[kind]:
        if not os.path.exists(path):
            continue
        if path.endswith(".ttc") and styles:
            for want in styles:
                for i in range(40):
                    try:
                        f = ImageFont.truetype(path, px, index=i)
                    except Exception:
                        break
                    if want.lower() == (f.getname()[1] or "").lower():
                        _FACE_CACHE[key] = f
                        return f
            continue
        try:
            f = ImageFont.truetype(path, px)
            _FACE_CACHE[key] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _FACE_CACHE[key] = f
    return f


def _norm(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def canonical(vocab):
    """One spelling per printed line: readings of the same line (85% alike) are one line, and the reading whose
    words the other readings share most wins ("DURACELL(R) POWERCHECK(TM)" over "...(TM)A"; "BEST IF INSTALLED BY:"
    over "...RY:"); stray end punctuation goes ("Patented ." -> "Patented"). 2026-10-08 18:30: the photos' own
    misreadings were set as crisp type."""
    from rapidfuzz import fuzz
    lines = [re.sub(r"\s+[.,:;]+$", "", str(v).strip()) for v in vocab if str(v).strip()]
    tokf = {}
    for v in lines:
        for t in {_norm(x) for x in v.split() if _norm(x)}:
            tokf[t] = tokf.get(t, 0) + 1
    groups = []
    for v in lines:
        for g in groups:
            if fuzz.ratio(_norm(v), _norm(g[0])) >= 85:
                g.append(v)
                break
        else:
            groups.append([v])
    small = {"a", "an", "at", "to", "of", "in", "by", "for", "on", "the", "and", "or", "if", "is", "it", "do", "not",
             "no", "be", "as", "with", "use", "only", "made", "test", "dots", "size"}   # common short words: a
    #   reading that has them ("Test at") beats one that turned them into near-misses ("Test al")
    best = lambda v: (sum(tokf.get(_norm(x), 0) + (1 if _norm(x) in small else 0) for x in v.split())
                      / max(1, len(v.split())), -len(v))
    return [max(g, key=best) for g in groups]


def snap(text, vocab, least=80):
    """The photos' own spelling of a line read off the label - ONLY ever a spelling from the (canonical) word list,
    never the reader's text - or None when no line matches (that line is left as drawn)."""
    from rapidfuzz import fuzz
    n = _norm(text)
    if len(n) < 2:
        return None
    best = max(vocab, key=lambda v: fuzz.ratio(_norm(v), n), default=None)
    if best is not None and fuzz.ratio(_norm(best), n) >= least:
        return best
    return None


def _lines(img, vocab):
    """The lines read off the label turned so its print reads across: (turn, [(text, snapped, x0, y0, x1, y1)])."""
    import measure as MS
    best = (90, [], -1)
    for turn in (90, 270):
        r = img.rotate(turn, expand=True)
        W, H = r.size
        got = []
        for t, x0, y0, x1, y1 in MS.read_boxes_full(r):
            got.append((t, snap(t, vocab), int(x0 * W), int(y0 * H), int(np.ceil(x1 * W)), int(np.ceil(y1 * H))))
        score = sum(len(g[1]) for g in got if g[1])
        if score > best[2]:
            best = (turn, got, score)
    return best[0], best[1]


def retype(lab, vocab, log, scale=2):
    """-> (label H*scale x W*scale x 3 float, notes)."""
    import cv2
    H, W = lab.shape[:2]
    img = Image.fromarray((np.clip(lab, 0, 1) * 255).astype(np.uint8))
    vocab = canonical(vocab)
    turn, lines = _lines(img, list(vocab))
    r = np.asarray(img.rotate(turn, expand=True)).copy()
    h, w = r.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    keep, seen = [], {}
    for t, s, x0, y0, x1, y1 in lines:
        x0, y0, x1, y1 = max(0, x0 - 2), max(0, y0 - 2), min(w, x1 + 2), min(h, y1 + 2)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        box = r[y0:y1, x0:x1].astype(float)
        edge = np.concatenate([box[0], box[-1], box[:, 0], box[:, -1]])
        bg = np.median(edge, axis=0)
        dist = np.abs(box - bg).sum(-1)
        ink = dist > 60
        if not s or not ink.any():                           # a line no photo's words match is left as it is (a
            continue                                         # misread of real print must not become a hole)
        mask[y0:y1, x0:x1] |= (ink * 255).astype(np.uint8)
        color = tuple(int(c) for c in np.median(box[ink], axis=0))
        area = (x1 - x0) * (y1 - y0)
        k = _norm(s)
        if k in seen and seen[k]["area"] >= area:            # printed twice (two views overlapping): once
            continue
        seen[k] = {"text": s, "box": (x0, y0, x1, y1), "color": color, "area": area}
    keep = list(seen.values())
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    clean = cv2.inpaint(r, mask, 5, cv2.INPAINT_TELEA)       # the old soft letters painted out from their band
    big = cv2.resize(clean, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)
    big = cv2.bilateralFilter(big, 9, 30, 9)                  # ink, not noise: smooth, edges kept
    out = Image.fromarray(big)
    heights = sorted(k["box"][3] - k["box"][1] for k in keep) or [1]
    med = heights[len(heights) // 2]
    for k in keep:                                           # each line again, crisp, at its size, place and color
        x0, y0, x1, y1 = [v * scale for v in k["box"]]
        bw, bh = x1 - x0, y1 - y0
        kind = "heavy" if (k["box"][3] - k["box"][1]) > 2.2 * med else "bold"
        f = face(kind, max(8, int(bh * 1.4)))
        tw = int(f.getlength(k["text"])) + 8
        layer = Image.new("L", (tw, int(bh * 2)), 0)
        ImageDraw.Draw(layer).text((4, 0), k["text"], font=f, fill=255)
        bb = layer.getbbox()
        if not bb:
            continue
        glyphs = layer.crop(bb).resize((max(1, bw), max(1, bh)), Image.LANCZOS)
        ink = Image.new("RGB", glyphs.size, k["color"])
        out.paste(ink, (x0, y0), glyphs)
    res = np.asarray(out.rotate(-turn, expand=True)).astype(float) / 255.0
    dropped = sorted({t for t, s, *_ in lines if not s})
    log(f"[retype] {len(keep)} printed lines set again as type ({', '.join(k['text'] for k in keep)[:200]}); "
        f"{len(dropped)} lines no photo's words match, left as drawn ({', '.join(dropped)[:120]})")
    return res, {"lines": [k["text"] for k in keep], "dropped": dropped, "turn": turn}
