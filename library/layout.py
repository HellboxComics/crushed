"""YOUR AI WRITES THE LABEL LAYOUT: it looks at the real label (unrolled flat from your photo), is given the exact
words read off it, and writes the layout labelart.py draws (colors, bands, boxes, every word with its position and
size). The drawn label goes back to it next to the real one; it fixes what differs; up to 3 rounds, the best kept.
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
             "stroke": "#rrggbb" or null, "stroke_w": line thickness, "metal": true for metallic ink/foil areas,
             "shade": "copper" for a copper/gold metallic band},
            {"type": "bar", "x": , "y": , "w": , "h": , "colors": ["#..", "#.."], "stops": [0, .., 1]}   (a color gradient)],
 "texts": [{"text": "EXACT WORDS", "x": , "y": , "h": letter height, "w": width it spans, "color": "#..",
            "weight": "regular" | "bold" | "black", "align": "left" | "center", "rotate": 0}]}
List shapes from back to front (big background areas first)."""

FIRST = """Picture 1 is the real printed label of: {product}, unrolled flat from photos of it (the middle is the
side facing the camera in the main photo, the two outer edges the opposite side when another photo showed it; blurry,
shiny or smeared parts are where no photo could see). It is {w:.1f} mm wide and {h:.1f} mm tall.
The words printed on it, each confirmed by two reads: {words}.
{typical}Rebuild this label as clean artwork: every colored area, band, box and graphic, and every one of those words
in its place, size, weight and color. Use only those words, spelled exactly. Where no photo could see, carry the
design across plainly and put there only those confirmed words that belong there.
""" + SCHEMA + "\nAnswer ONLY the JSON."

AGAIN = """Picture 1 is your rebuilt label, drawn from your layout below. Picture 2 is the real label.
Your layout: {layout}
Fix every difference: positions, sizes, colors, missing or extra elements. Keep the words exactly: {words}.
Answer ONLY the corrected JSON (the whole layout)."""

COMPARE = """Picture 1 is a rebuilt label; picture 2 is the real one it copies. Answer ONLY JSON:
{"match": 0-10 how closely picture 1 matches picture 2 in layout, colors, graphics and words,
 "fixes": ["short list of what to change in picture 1"]}"""


def _json(txt):
    return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))


def _ask(model, text, images, think=True):
    body = {"model": model, "stream": False, "format": "json", "think": think, "options": {"temperature": 0.2,
            "num_ctx": 16384}, "messages": [{"role": "user", "content": text, "images": [V._img(p, 1536) for p in images]}]}
    return _json(V._call("/api/chat", body, timeout=1800).get("message", {}).get("content", "{}"))


def clean_layout(lay, w_mm, h_mm, words):
    """Keep it drawable: numbers in range, only the read words (anything else the AI typed is dropped)."""
    lay["width_mm"], lay["height_mm"] = w_mm, h_mm
    allowed = " ".join(words).lower()
    out_t = []
    for t in lay.get("texts", []):
        if not isinstance(t, dict) or not str(t.get("text", "")).strip():
            continue
        if not all(tok.lower().strip(".,:;") in allowed for tok in str(t["text"]).split()):
            continue                                   # a word that isn't on the real label: dropped
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
            shapes.append(s)
        except Exception:
            pass
    lay["shapes"] = shapes
    return lay


def make(product, real_png, words, w_mm, h_mm, out_dir, model=None, rounds=3, log=print, typical=()):
    """typical: what is normally printed on this kind of label (from its kit) - so the parts no photo shows get what
    belongs there, from the confirmed words only."""
    model = model or V.model()
    os.makedirs(out_dir, exist_ok=True)
    said = ", ".join(f'"{w}"' for w in words)
    best = (-1, None, None, None)
    tip = ("A label like this normally carries: " + "; ".join(typical) + ".\n") if typical else ""
    lay = clean_layout(_ask(model, FIRST.format(product=product, w=w_mm, h=h_mm, words=said, typical=tip), [real_png]),
                       w_mm, h_mm, words)
    for r in range(1, rounds + 1):
        png, mr = labelart.render(lay, out_dir, px=2048, name=f"round{r}")
        try:
            c = _ask(model, COMPARE, [png, real_png], think=False)
        except Exception as e:
            c = {"match": 0, "fixes": [str(e)]}
        log(f"[texture] label round {r}: match {c.get('match')} - {'; '.join(map(str, c.get('fixes', [])))[:200]}")
        json.dump(lay, open(os.path.join(out_dir, f"round{r}.json"), "w"), indent=1)
        if (c.get("match") or 0) > best[0]:
            best = (c.get("match") or 0, lay, png, mr)
        if (c.get("match") or 0) >= 9 or r == rounds:
            break
        try:
            lay = clean_layout(_ask(model, AGAIN.format(layout=json.dumps(lay), words=said), [png, real_png]),
                               w_mm, h_mm, words)
        except Exception as e:
            log(f"[texture] could not improve the layout: {e}")
            break
    score, lay, _, _ = best
    json.dump(lay, open(os.path.join(out_dir, "layout.json"), "w"), indent=1)
    png, mr = labelart.render(lay, out_dir, px=4096, name="label")
    return png, mr, score
