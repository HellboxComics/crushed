"""YOUR AI'S FACTORY RESEARCH: before a new kind of item is built, your local AI works out how that kind of thing is
manufactured - the parts in assembly order, what each is made of, how thick, and what is inside - writes it down as a
recipe, then checks it against what Google shows (teardowns, cross-sections, maker pages) with its own browser and
fixes what doesn't match. One recipe serves the whole family (every can, every battery size, every plush toy).

    recipe = factory.recipe_for(card)        # the family's recipe: made once, kept in factory/recipes/<family>.json

A round item's recipe describes its insides relative to its outside, so it fits any size the photo traces:
    {"shape": "wall",  "thickness_mm": 0.1}             a wall just inside the outer surface (a can's aluminum)
    {"shape": "fill",  "fraction": 0.92}                 the inside filled to a height (a drink, a lotion)
    {"shape": "core",  "radius_fraction": 0.3}           a solid rod up the middle (a crayon's wax core, a pen refill)
Free-form items (toys, gadgets) list inside parts as boxes and cylinders placed by fractions of the outer size.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
RECIPES = os.path.join(HERE, "recipes")
sys.path.insert(0, LIB)

PHYS = json.load(open(os.path.join(HERE, "physics.json")))
KINDS = sorted(k for k in PHYS if not k.startswith("_"))

FAMILY = """Product: {product}
Name the manufacturing FAMILY this belongs to - the kind of thing a factory makes the same way, whatever the brand
(examples: alkaline_cylindrical_cell, folding_carton, aluminum_beverage_can, plastic_bottle, glass_bottle,
plush_toy_with_mechanism, molded_plastic_toy, wax_crayon, printed_circuit_card, cassette_tape, vhs_tape, sneaker).
Answer ONLY JSON: {{"family": "lowercase_with_underscores"}}"""

WRITE = """You are a manufacturing engineer. Write how a {family} is made in a factory - example product: {product}
(real size, width x depth x height in meters: {size}). List the parts in assembly order with what each is made of
and how thick, and what is INSIDE it (what you'd see if it were crushed or cut open).
Materials must be one of: {kinds}.
Answer ONLY JSON:
{{"family": "{family}",
 "how_it_is_made": ["step 1 ...", "step 2 ...", "..."],
 "outside": [{{"part": "...", "kind": "<material>", "thickness_mm": 0.0, "details": ["..."]}}],
 "inside":  [{{"part": "...", "kind": "<material>", "color": [r, g, b], "roughness": 0.5,
              "shape": "wall" | "fill" | "core" | "box" | "cylinder",
              "thickness_mm": 0.0, "fraction": 0.0, "radius_fraction": 0.0,
              "at": [x, y, z], "size": [x, y, z]}}],
 "look_up": ["2 to 4 Google searches that would show this family's insides (teardown, cross section)"]}}
For round things use wall / fill / core; for others box / cylinder with "at" and "size" as fractions (0..1) of the
outer size. Colors are 0..1 RGB of the real material."""

CHECK = """Picture 1 is a photo found by searching "{q}". Our recipe says a {family} contains: {parts}.
Does the photo show this kind of item's insides or construction? If it does, list what in our recipe is wrong or
missing. Answer ONLY JSON: {{"relevant": true/false, "wrong": ["..."], "missing": ["..."]}}"""

FIX = """Here is a manufacturing recipe and what real photos showed about it. Correct the recipe: fix what is wrong,
add what is missing, keep the same JSON shape. Recipe: {recipe}
Photo findings: {findings}
Answer ONLY the corrected JSON."""


def _ask(text, images=(), model=None, think=False):
    import vet as V
    model = model or V.model()
    if images:
        return V.ask(model, text, list(images), think=think, side=896)
    body = {"model": model, "stream": False, "format": "json", "think": think,
            "options": {"temperature": 0.2, "num_predict": 2500}, "messages": [{"role": "user", "content": text}]}
    txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
    return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))


def _fetch(url, ua):
    """One photo from the web into ~/crushed-render/remaster/factory_refs (None if it can't be had)."""
    import hashlib
    import io
    import urllib.request
    from PIL import Image
    d = os.path.join(os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster")),
                     "factory_refs")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, hashlib.sha1(url.encode()).hexdigest()[:12] + ".jpg")
    if os.path.exists(p):
        return p
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(p, quality=90)
        return p
    except Exception:
        return None


def family_of(card, model=None):
    if card.get("family"):
        return card["family"]
    f = _ask(FAMILY.format(product=card["product"]), model=model).get("family", "")
    return re.sub(r"[^a-z0-9_]", "", str(f).lower()) or "general_object"


def clean(r):
    for sect in ("outside", "inside"):
        for p in r.get(sect, []):
            if p.get("kind") not in PHYS:
                p["kind"] = "molded_plastic"
    return r


def recipe_for(card, model=None, log=print, check=True):
    """The family's recipe (made once, then reused for every item of that family)."""
    fam = family_of(card, model)
    path = os.path.join(RECIPES, fam + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    log(f"[factory] {fam}: your AI writes how it's made")
    r = clean(_ask(WRITE.format(family=fam, product=card["product"], size=card.get("size"), kinds=KINDS), model=model))
    r["family"] = fam
    findings = []
    if check:                                               # the web check: real teardown / cross-section photos
        try:
            import google_images as G
            import hunt
            parts = ", ".join(f"{p.get('part')} ({p.get('kind')})" for p in r.get("inside", []))
            for q in r.get("look_up", [])[:3]:
                urls = G.search(q, most=4, log=log)
                for u, w, h in urls[:3]:
                    f = _fetch(u, hunt.UA)
                    if not f:
                        continue
                    v = _ask(CHECK.format(q=q, family=fam, parts=parts), [f], model=model)
                    if v.get("relevant"):
                        findings.append({"search": q, "wrong": v.get("wrong", []), "missing": v.get("missing", [])})
            if findings:
                r = clean(_ask(FIX.format(recipe=json.dumps(r), findings=json.dumps(findings)), model=model))
                r["family"] = fam
        except Exception as e:
            log(f"[factory] web check skipped: {e}")
    r["checked_against"] = findings or [{"note": "written from your AI's knowledge; no matching photos found to check"}]
    os.makedirs(RECIPES, exist_ok=True)
    json.dump(r, open(path, "w"), indent=1)
    log(f"[factory] {fam}: recipe saved ({len(r.get('inside', []))} inside parts, {len(findings)} photo checks)")
    return r


if __name__ == "__main__":
    import cards
    print(json.dumps(recipe_for(cards.make(sys.argv[1])), indent=1))
