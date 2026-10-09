"""YOUR AI WRITES THE LABEL LAYOUT: it looks at the real label (unrolled flat from your photo), is given the exact
words read off it, and writes the layout labelart.py draws (colors, bands, boxes, every word with its position and
size). The drawn label goes back to it next to the real one; it fixes what differs, round after round while anything
is left to fix (up to 4 rounds); the best kept.
Words are set in real type, so they are always spelled exactly as read.

    png, mr_png, score = make(product, real_flat_png, words, width_mm, height_mm, out_dir)
"""
import json
import os
import re

import labelart
import vet as V

SCHEMA = """Write the layout as JSON, positions as fractions of the label (0..1 across from the left, 0..1 down from
the top), sizes as fractions too:
{"width_mm": W, "height_mm": H, "background": "#rrggbb",
 "shapes": [{"type": "rect" | "ellipse", "x": , "y": , "w": , "h": , "fill": "#rrggbb" or null,
             "stroke": "#rrggbb" or null, "stroke_w": line thickness as a fraction of the label's height (0.005 =
             a thin line), "metal": true for metallic ink/foil areas,
             "shade": "copper" for a copper/gold metallic band},
            {"type": "bar", "x": , "y": , "w": , "h": , "colors": ["#..", "#.."], "stops": [0, .., 1]}   (a color gradient),
            {"type": "arrow", "x": , "y": , "w": , "h": , "fill": "#rrggbb", "dir": "right" | "left" | "up" | "down"}],
 "texts": [{"text": "EXACT WORDS", "x": , "y": , "h": letter height, "w": width it spans, "color": "#..",
            "weight": "regular" | "bold" | "black", "align": "left" | "center", "rotate": 0}]}
List shapes from back to front (big background areas first)."""

FIRST = """Picture 1 is the real printed label of: {product}, unrolled flat from photos of it (the middle is the
side facing the camera in the main photo, the two outer edges the opposite side when another photo showed it; blurry,
shiny or smeared parts are where no photo could see). It is {w:.1f} mm wide and {h:.1f} mm tall.
The words printed on it, each confirmed by two reads: {words}.
{typical}Picture 1 is ONLY the printed label: the item's unprinted parts (its ends, caps, buttons, rims) are not part of
it - never draw them. Rebuild this label as clean artwork: every colored area, band, box and graphic, and every one of those
words in its place, size, weight and color. Use only those words, spelled exactly; a word can appear more than once
(a logo printed again on the other side). Where no photo could see (smeared, streaked parts), carry the design
across plainly and put there only those confirmed words that belong there.
""" + SCHEMA.replace("{", "{{").replace("}", "}}") + "\nAnswer ONLY the JSON."   # (its braces are not blanks)

AGAIN = """Picture 1 is your rebuilt label, drawn from your layout below. Picture 2 is the real label.
Your layout: {layout}
A careful comparison found these differences to fix: {fixes}
Fix them and every other difference: positions, sizes, colors, missing or extra elements. Shapes marked "base"
are the label's measured background bands: keep them exactly as they are. Words: only these,
spelled exactly: {words} (a fix asking for a word that is not in this list can't be made - leave that word out).
Answer ONLY the corrected JSON (the whole layout)."""

STRICT = """Picture 1 is your rebuilt label, drawn from your layout below. Picture 2 is the real label.
Your layout: {layout}
You sent this layout back unchanged, but these differences are still there. Make EVERY numbered change below in the
layout - add, move, resize or recolor the shapes and words it names (a "small mark ... white on the real label" is a
white dot or mark to add there; an area "brown on the real label" is a brown panel to add there):
{todo}
Shapes marked "base" stay exactly as they are. Words: only these, spelled exactly: {words}.
Answer ONLY the corrected JSON (the whole layout) - it must differ from the one above."""

COMPARE = """Picture 1 is flat printed artwork for a label. Picture 2 is the real label, unrolled flat from photos
of a round object: it still carries the photo's light, shade, glare, curvature and metal sheen, and smeared streaks
where no photo saw - none of that is part of the printed design and none of it can or should be drawn into picture
1. Compare ONLY the printed design: where each area, panel, bar, dot, logo and word sits, its size, its color, its
words. Answer ONLY JSON:
{"match": 0-10 how closely picture 1's printed design matches picture 2's,
 "fixes": ["short list of what to change in picture 1's printed design - never lighting, shading, texture, 3D
   shape, caps or terminals"]}"""


def _json(txt):
    return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))


def _ask(model, text, images, think=True, temp=0.2):
    # num_ctx 32768: two 1536-px pictures, the whole layout and the brain's thinking overran 16384 - Ollama cuts what
    # does not fit (its docs: num_ctx is the whole window), and the brain answered with the old layout unchanged
    # (2026-10-09, the Duracell's label stopped after one round with its white dots still missing)
    body = {"model": model, "stream": False, "format": "json", "think": think, "options": {"temperature": temp,
            "num_ctx": 32768}, "messages": [{"role": "user", "content": text, "images": [V._img(p, 1536) for p in images]}]}
    return _json(V._call("/api/chat", body, timeout=1800).get("message", {}).get("content", "{}"))


def neutral(c, dark=25, light=40):
    """A photo's light tints black and white ink (warm room light: the Duracell's black read #191e0d, olive, and its
    white letters cream #f0e8d0 - the judge: "correct the label black to true black"). A color that is nearly gray -
    a dark one whose channels differ by under 25, a light one by under 40 - is that gray: the cast taken out (the
    gray-world assumption, applied only to inks that are near gray). Real colored dark or light inks (navy, forest
    green, cream) differ by more and are kept."""
    try:
        r, g, b = (int(str(c).lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return c
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    spread = max(r, g, b) - min(r, g, b)
    if (lum < 70 and spread < dark) or (lum > 185 and spread < light):
        v = int(round(lum))
        return "#%02x%02x%02x" % (v, v, v)
    return c


def _neutral_all(lay):
    for s in lay.get("shapes", []):
        for k in ("fill", "stroke"):
            if s.get(k):
                s[k] = neutral(s[k])
        if s.get("colors"):
            s["colors"] = [neutral(c) for c in s["colors"]]
    for t in lay.get("texts", []):
        if t.get("color"):
            t["color"] = neutral(t["color"])
    if lay.get("background"):
        lay["background"] = neutral(lay["background"])
    return lay


def clean_layout(lay, w_mm, h_mm, words, base=()):
    """Keep it drawable: numbers in range, only the read words (anything else the AI typed is dropped); the measured
    base bands first, and none of the AI's own guesses at them (a rect spanning the whole label is a band)."""
    lay["width_mm"], lay["height_mm"] = w_mm, h_mm
    if base:
        axis_w = any(s.get("h") == 1.0 for s in base)
        own = []
        for s in lay.get("shapes", []):
            try:
                full = (float(s.get("h", 0)) >= 0.9 and float(s.get("w", 0)) >= 0.15) if axis_w else \
                    (float(s.get("w", 0)) >= 0.9 and float(s.get("h", 0)) >= 0.15)
            except (TypeError, ValueError):
                full = False
            if not (s.get("type", "rect") == "rect" and full and not s.get("stroke")):
                own.append(s)
        lay["shapes"] = [dict(s) for s in base] + own
        widest = max(base, key=lambda s: s["w"] * s["h"])
        lay["background"] = widest["fill"]
    import review
    out_t = []
    for t in review.only_words(lay.get("texts", []), words):   # (locked: only words read off real photos)
        for k in ("x", "y", "h", "w"):
            if k in t and t[k] is not None:
                t[k] = float(min(max(float(t[k]), 0.0), 1.0))
        t.setdefault("h", 0.05)
        out_t.append(t)
    lay["texts"] = out_t
    shapes = []
    for s in lay.get("shapes", []):
        try:
            for k in ("x", "y", "w", "h"):
                s[k] = float(min(max(float(s.get(k, 0)), 0.0), 1.0))
            sw = float(s.get("stroke_w") or 0)
            if sw > 0.05:                              # given in mm (or px), not as a fraction: a "1.2" outline
                sw = sw / h_mm if sw <= 5 else 0.006   # was drawn 1.2 label-heights wide and painted it all
            s["stroke_w"] = min(max(sw, 0.0), 0.03)    # (2026-10-03, the Duracell's whole label went green)
            if s.get("metal") and not s.get("fill"):   # metal ink with no color given: its real color
                s["fill"] = "#b87333" if s.get("shade") == "copper" else "#c0c0c0"
            shapes.append(s)
        except Exception:
            pass
    lay["shapes"] = shapes
    return _neutral_all(lay)


# ------------------------------------------------------------------ the exact color check (measured, not judged)
NAMED = {"black": (20, 20, 20), "white": (240, 240, 240), "gray": (128, 128, 128), "silver": (190, 190, 195),
         "copper": (184, 115, 51), "gold": (212, 175, 55), "tan": (210, 160, 100), "brown": (110, 75, 45),
         "red": (210, 40, 35), "orange": (240, 130, 30), "yellow": (240, 220, 40), "green": (40, 180, 60),
         "blue": (40, 80, 200), "purple": (120, 50, 160), "pink": (240, 150, 180)}


def _name(rgb):
    import numpy as np
    c = np.asarray(rgb, float)
    return min(NAMED, key=lambda k: float(((np.asarray(NAMED[k]) - c) ** 2).sum()))


WARM = {"copper", "gold", "tan", "orange", "brown"}       # metal ink and its lit / shaded tones in a photo


def _family(rgb):
    """A color as a photo's light can't change it: dark, warm metal, light, or its own color."""
    import numpy as np
    lum = float(np.dot(np.asarray(rgb, float), [0.299, 0.587, 0.114]))
    if lum < 70:
        return "dark"
    n = _name(rgb)
    return "warm" if n in WARM else "light" if n in ("white", "silver") else n


def _boxes(out_dir, name):
    try:
        return json.load(open(os.path.join(out_dir, name + "_boxes.json")))
    except Exception:
        return {}


def color_check(png, real_png, cover_png=None, cols=20, rows=10):
    """The drawn label against the real one, part by part (a 20 x 10 grid), by measuring colors - the comparison
    brain said "match 9" for a Duracell drawn all black with no copper top (2026-10-03). Only parts a photo really
    saw count (cover_png: how well each pixel was seen), and a photo's light and shade never count as a different
    color (copper lit or shaded is still copper). -> (share of seen parts whose color matches 0..1, [fixes])"""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    small = lambda f: np.asarray(Image.open(f).convert("RGB").resize((cols, rows), Image.BOX)).astype(float)
    a, b = small(png), small(real_png)
    seen = np.ones((rows, cols), bool)
    if cover_png and os.path.exists(cover_png):
        seen = np.asarray(Image.open(cover_png).convert("L").resize((cols, rows), Image.BOX)) > 0.5 * 255
    na = np.array([[_name(a[y, x]) for x in range(cols)] for y in range(rows)])
    nb = np.array([[_name(b[y, x]) for x in range(cols)] for y in range(rows)])
    fa = np.array([[_family(a[y, x]) for x in range(cols)] for y in range(rows)])
    fb = np.array([[_family(b[y, x]) for x in range(cols)] for y in range(rows)])
    far = np.sqrt(((a - b) ** 2).sum(-1)) > 90
    bad = (fa != fb) & far & seen
    fixes = []
    for want, got in sorted({(nb[y, x], na[y, x]) for y, x in zip(*np.where(bad))}):
        lab, n = ndimage.label(bad & (nb == want) & (na == got))
        for k in range(1, n + 1):
            ys, xs = np.where(lab == k)
            if len(ys) < 2:
                continue                                # one small part: a detail, not a wrong area
            fixes.append(f"the area x {xs.min() / cols:.2f}-{(xs.max() + 1) / cols:.2f}, y {ys.min() / rows:.2f}-"
                         f"{(ys.max() + 1) / rows:.2f} is {want} on the real label but {got} in yours")
    # small marks (a dot, a seal, a short stripe) are one cell or less on the coarse grid and were dropped above as
    # "a detail": a finer pass (3x) finds them - the real label has a mark where the drawn one has none, or the
    # other way round (2026-10-04: the PowerCheck's second white test dot was never flagged)
    c2, r2 = cols * 3, rows * 3
    small2 = lambda f: np.asarray(Image.open(f).convert("RGB").resize((c2, r2), Image.BOX)).astype(float)
    a2, b2 = small2(png), small2(real_png)
    seen2 = np.ones((r2, c2), bool)
    if cover_png and os.path.exists(cover_png):
        seen2 = np.asarray(Image.open(cover_png).convert("L").resize((c2, r2), Image.BOX)) > 0.5 * 255
    fa2 = np.array([[_family(a2[y, x]) for x in range(c2)] for y in range(r2)])
    fb2 = np.array([[_family(b2[y, x]) for x in range(c2)] for y in range(r2)])
    far2 = np.sqrt(((a2 - b2) ** 2).sum(-1)) > 90
    bad2 = (fa2 != fb2) & far2 & seen2
    lab2, n2 = ndimage.label(bad2)
    marks = 0
    for k in range(1, n2 + 1):
        ys, xs = np.where(lab2 == k)
        if len(ys) < 3 or len(ys) > 40:                     # a sliver at a band's edge, or a big area (the coarse pass)
            continue
        want, got = _name(b2[ys, xs].mean(0)), _name(a2[ys, xs].mean(0))
        if want == got:
            continue
        marks += 1
        if marks <= 8:
            fixes.append(f"a small mark at x {(xs.min() + xs.max() + 1) / 2 / c2:.2f}, y {(ys.min() + ys.max() + 1) / 2 / r2:.2f} "
                         f"(about {(xs.max() - xs.min() + 1) / c2:.2f} wide, {(ys.max() - ys.min() + 1) / r2:.2f} tall) "
                         f"is {want} on the real label but {got} in yours")
    return float(1 - bad.sum() / max(seen.sum(), 1)), fixes


# ------------------------------------------------------------------ the base layout, MEASURED (never guessed)
def base_bands(real_png, cover_png=None, least=0.04):
    """The label's background bands, measured from the unrolled real label: the copper end, the black body, a
    stripe - as rect shapes spanning the label, in order. Measured along whichever axis has the bands (along the
    item for a battery, around for most cans). Only columns a photo saw count. The AI then only places words,
    panels and marks on top - it can no longer draw the whole label black, or put copper at the wrong end
    (2026-10-03, Duracell builds 3 and 4). -> (shapes, axis "x" | "y" | None)"""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(real_png).convert("RGB")).astype(float)
    H, W = a.shape[:2]
    seen = np.ones((H, W), bool)
    if cover_png and os.path.exists(cover_png):
        # "seen" is what the rest of the pipeline calls seen: weight > 0.05 (mosaic.placed's weight is a QUALITY
        # score - angle x closeness x sharpness - so a soft or distant photo is fully seen at 0.2; 2026-10-05 19:22:
        # this read > 0.5, saw nothing, returned no bands in silence, and the writer painted the copper end black)
        seen = np.asarray(Image.open(cover_png).convert("L").resize((W, H))) > 0.05 * 255

    def runs(axis):
        n = W if axis == "x" else H
        fams, cols = [], []
        for i in range(n):
            px = a[:, i][seen[:, i]] if axis == "x" else a[i][seen[i]]
            if len(px) < 8:
                fams.append(None)
                cols.append(None)
                continue
            m = np.median(px, 0)
            fams.append(_family(m))
            cols.append(m)
        out, start = [], 0
        for i in range(1, n + 1):
            if i == n or fams[i] != fams[start]:
                if fams[start] is not None and (i - start) / n >= least:
                    cs = np.array([c for c in cols[start:i] if c is not None])
                    # the band's print color: the brighter side of its columns (a photo's shade darkens, never lightens)
                    out.append((start / n, i / n, fams[start], np.percentile(cs, 65, axis=0)))
                start = i
        # neighbours of the same family (split by an unseen gap) are one band
        merged = []
        for b in out:
            if merged and merged[-1][2] == b[2] and b[0] - merged[-1][1] < 0.08:
                merged[-1] = (merged[-1][0], b[1], b[2], (merged[-1][3] + b[3]) / 2)
            else:
                merged.append(b)
        return merged
    def residual(bands, axis):
        """How far the seen pixels are, on average, from their band's color: the axis whose bands explain the
        label better wins (not the one with more bands - stitching streaks make false bands)."""
        if not bands:
            return 1e9
        tot, n = 0.0, 0
        for p0, p1, fam, col in bands:
            sl = (slice(None), slice(int(p0 * W), max(int(p1 * W), int(p0 * W) + 1))) if axis == "x" else \
                (slice(int(p0 * H), max(int(p1 * H), int(p0 * H) + 1)), slice(None))
            px = a[sl][seen[sl]]
            if len(px):
                tot += np.abs(px - col).sum()
                n += len(px)
        return tot / max(n, 1)
    rx, ry = runs("x"), runs("y")
    bands, axis = (rx, "x") if residual(rx, "x") <= residual(ry, "y") else (ry, "y")
    if len(bands) < 1:
        return [], None
    shapes = []
    for i, (p0, p1, fam, col) in enumerate(bands):
        p0 = 0.0 if i == 0 else p0                      # the bands cover the whole label edge to edge
        p1 = 1.0 if i == len(bands) - 1 else bands[i + 1][0]
        hexcol = "#%02x%02x%02x" % tuple(int(min(255, max(0, v))) for v in col)
        s = {"type": "rect", "fill": hexcol, "stroke": None, "stroke_w": 0, "base": True}
        if axis == "x":
            s.update(x=round(p0, 4), y=0.0, w=round(p1 - p0, 4), h=1.0)
        else:
            s.update(x=0.0, y=round(p0, 4), w=1.0, h=round(p1 - p0, 4))
        if fam == "warm":
            s.update(metal=True, shade="copper" if _name(col) in ("copper", "brown", "tan") else None)
        shapes.append(s)
    return shapes, axis


def describe_bands(shapes, axis):
    if not shapes:
        return ""
    where = "left to right (along the label)" if axis == "x" else "top to bottom"
    parts = []
    for s in shapes:
        p0, p1 = (s["x"], s["x"] + s["w"]) if axis == "x" else (s["y"], s["y"] + s["h"])
        parts.append(f"{_name(tuple(int(s['fill'][i:i + 2], 16) for i in (1, 3, 5)))}"
                     f"{' (metal ink)' if s.get('metal') else ''} from {p0:.2f} to {p1:.2f}")
    return (f"MEASURED from the real photo, the label's background bands, {where}: " + "; ".join(parts) +
            ". These bands are already drawn as the first shapes of your layout - do not redraw them, do not change "
            "their colors or edges, and never cover a whole band. Draw only what sits ON them: panels, boxes, "
            "bars, dots, logos and words.\n")


def make(product, real_png, words, w_mm, h_mm, out_dir, model=None, rounds=4, log=print, typical=(), cover_png=None,
         marks=()):
    """typical: what is normally printed on this kind of label (from its kit) - so the parts no photo shows get what
    belongs there, from the confirmed words only."""
    model = model or V.model()
    os.makedirs(out_dir, exist_ok=True)
    said = ", ".join(f'"{w}"' for w in words)
    best = (-1, None, None, None, None)
    tries = []                                         # each try's match and whether it changed (the review sheet)
    tip = ("A label like this normally carries: " + "; ".join(typical) + ".\n") if typical else ""
    if marks:                                             # what THIS version is known by: each must be on the label,
        tip += ("This exact version is known by these marks - each must be on the label as the real photo shows it, "
                "in the same number and place (count repeated marks): " + "; ".join(str(m) for m in marks) + ".\n")
    try:
        base, axis = base_bands(real_png, cover_png)
    except Exception as e:
        log(f"[texture] the label's bands could not be measured ({e})")
        base, axis = [], None
    if base:
        log("[texture] " + describe_bands(base, axis).split(". These")[0])
    else:
        log("[texture] the label's bands could not be measured: no band covers 4% of the label where a photo saw it")
    tip = describe_bands(base, axis) + tip
    lay = clean_layout(_ask(model, FIRST.format(product=product, w=w_mm, h=h_mm, words=said, typical=tip), [real_png]),
                       w_mm, h_mm, words, base)
    for r in range(1, rounds + 1):
        png, mr = labelart.render(lay, out_dir, px=2048, name=f"round{r}")
        try:
            c = _ask(model, COMPARE, [png, real_png], think=False)
        except Exception as e:
            c = {"match": 0, "fixes": [str(e)]}
        try:                                           # the measured colors overrule a kind look
            share, cfix = color_check(png, real_png, cover_png)
        except Exception as e:
            share, cfix = 1.0, []
            log(f"[texture] the color check could not run: {e}")
        judged = c.get("match") or 0
        # exact: no two lines printed on top of each other, none past the edge (measured from where each landed)
        bx = _boxes(out_dir, f"round{r}")
        ofix = [f"'{o['a']}' is printed on top of '{o['b']}' ({o['share']:.0%} of the smaller) - move or shrink one"
                for o in bx.get("overlaps", [])] + [f"'{t}' runs off the label" for t in bx.get("off_label", [])] + \
            [f"'{u['text']}' " + ("is printed across a shape (a dot, a box or a band edge sits under part of it) - "
                                  "move it onto plain ground as the real label has it" if u["why"] == "crosses" else
                                  "can't be read: its color is almost the color under it - set it where the real "
                                  "label has it, in a color that stands out")
             for u in bx.get("unreadable", [])]
        c = dict(c, judged=judged, colors=round(share, 2),
                 match=min(judged, int(round(10 * share)), 6 if ofix else 10),   # overlapping text is never "good"
                 fixes=ofix + cfix + list(c.get("fixes") or []), overlaps=len(bx.get("overlaps", [])))
        log(f"[texture] label round {r}: match {c['match']} (looked {judged}, colors {share:.0%} right) - "
            f"{'; '.join(map(str, c.get('fixes', [])))[:300]}")
        json.dump(lay, open(os.path.join(out_dir, f"round{r}.json"), "w"), indent=1)
        tries.append({"round": r, "match": c.get("match"), "judged": judged, "colors": c["colors"],
                      "fixes": c.get("fixes", []), "changed": True})
        json.dump(tries, open(os.path.join(out_dir, "rounds.json"), "w"), indent=1)
        rank = (c.get("match") or 0, judged, share)       # equal matches (a cap at 6): the better-looking, truer-
        if best[0] == -1 or rank > best[4]:                #   colored round wins, not simply the first
            best = (c.get("match") or 0, lay, png, mr, rank)
        # it stops only when nothing is left to fix (a 9 with "remove the white dot" is not done - the standard is
        # perfect), when the rounds are used up, or when a round changes nothing
        if ((c.get("match") or 0) >= 10 and not c.get("fixes")) or r == rounds:
            break
        fixes = "; ".join(map(str, c.get("fixes") or [])) or "(none listed - compare the two pictures yourself)"
        try:
            new = clean_layout(_ask(model, AGAIN.format(layout=json.dumps(lay), words=said, fixes=fixes),
                                    [png, real_png]), w_mm, h_mm, words, base)
        except Exception as e:
            log(f"[texture] could not improve the layout: {e}")
            break
        if json.dumps(new, sort_keys=True) == json.dumps(lay, sort_keys=True) and c.get("fixes"):
            # unchanged with fixes still listed is a stall, not "done": asked once more, each fix numbered, warmer
            todo = "\n".join(f"{i}. {f}" for i, f in enumerate(c.get("fixes") or [], 1))
            log("[texture] the layout came back unchanged with fixes still listed - asking again, each fix numbered")
            try:
                new = clean_layout(_ask(model, STRICT.format(layout=json.dumps(lay), words=said, todo=todo),
                                        [png, real_png], temp=0.6), w_mm, h_mm, words, base)
            except Exception as e:
                log(f"[texture] could not improve the layout: {e}")
                break
        if json.dumps(new, sort_keys=True) == json.dumps(lay, sort_keys=True):
            log("[texture] the layout came back unchanged - no point drawing it again")
            tries.append({"round": r + 1, "match": None, "changed": False})
            json.dump(tries, open(os.path.join(out_dir, "rounds.json"), "w"), indent=1)
            break
        lay = new
    score, lay, _, _, _ = best
    json.dump(lay, open(os.path.join(out_dir, "layout.json"), "w"), indent=1)
    png, mr = labelart.render(lay, out_dir, px=4096, name="label")
    return png, mr, score
