"""ITEM CARDS: what the asset maker needs to know about each catalog item, written once by your local AI from the
catalog (name, era, real size, material) and kept in ~/crushed-render/remaster/cards/<item>.json.

    route        round  - one shape spun around an axis (battery, can, bottle, jar, tube, cup, tub, yo-yo, crayon)
                 box    - a rectangular box or block (cereal box, VHS, cassette, game cartridge, book, carton)
                 flat   - a thin sheet or card (trading card, ticket, sticker, CD sleeve, flyer)
                 free   - everything else (toys, plush, figures, clothes, gadgets, food) - made by a 3D-maker AI
    standing     round things: "upright" (axis up, like a can) or "lying" (like a battery on its side)
    label_reads  round things: "around" (words run around it, like a can) or "along" (like a battery) or "none"
    recognize    3-5 things you can SEE in a photo that mark this exact version from that time
    avoid        things that would mean a photo shows a different/newer/older version
    searches     what a collector would type into Google Images to find this exact old version

No dates, no battery rules: the same card works for a Furby, a Duncan yo-yo, Gak or a Pop-Tarts box.

    python library/cards.py furby_gray_pink_1998        (prints the card, making it if needed)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
DIR = os.environ.get("CRUSHED_CARDS_DIR") or os.path.join(WORK, "cards")   # a test build uses its own copies

ASK = """You are preparing a real product for a professional 3D model. Use what you know about it.
Product: {product}
Real size (width x depth x height, meters): {size}
Main material: {mat}
Answer ONLY JSON, no other words:
{{"route": "round" if it is basically one shape spun around an axis (battery, can, bottle, jar, tube, cup, tub, yo-yo, crayon, lipstick, roll), "box" if basically a rectangular box or block (cereal box, VHS tape, cassette, game cartridge, book, carton, brick-shaped gadget), "flat" if a thin sheet or card (trading card, ticket, sticker, flyer, CD sleeve, coaster), "free" for anything else (toys, plush, figures, clothing, shoes, gadgets with shaped bodies, food, tools, masks),
 "standing": "upright" if a round thing normally stands on its end like a can, "lying" if it normally lies on its side like a battery or crayon, else "",
 "label_reads": for a round thing: "around" if its printed words run around it (cans, bottles), "along" if they run along its length (batteries, pens, crayons), "none" if unprinted; else "",
 "recognize": [3 to 5 short things you can SEE in a photo that identify THIS exact version from that time (colors, logos, shapes, special features), each a few words],
 "avoid": [1 to 3 short visible things that would mean a photo shows a newer, older or different version],
 "searches": [4 Google Images searches a collector would type to find photos of this exact old version; short, like people really search],
 "parts": "one short line: the main parts and what each is made of"}}"""


BUILD = """You are the lead 3D artist for a studio known for photoreal product models. Before modeling a real product you
write down HOW IT IS REALLY MADE, layer by layer, so nothing that makes it look real gets missed (the overlap seam of
a battery's plastic sleeve, the sleeve's edge rolled over the ends, the pressed rings in a steel cap, the glued flap
of a carton, the cracked ink along a box's folds, the mold seam on a toy, the stitching on fabric).
Product: {product}
Real size (width x depth x height, meters): {size}
Answer ONLY JSON:
{{"layers": [{{"part": "short name", "material": one of {materials}, "on_top_of": "part it covers or empty",
              "details": [any that apply, from {details}]}}],
 "closeups": [4 to 8 short things a close-up photo of the real one shows that a cheap model would miss]}}"""

MATERIALS = ["printed_plastic_sleeve", "printed_paper_label", "printed_card", "bare_steel", "aluminum", "chrome",
             "copper", "brass", "gold_plate", "glass", "clear_plastic", "molded_plastic", "soft_rubber", "fabric",
             "plush_fur", "painted_metal", "wood", "leather", "foam"]
DETAILS = ["sleeve_seam", "rolled_lip", "pressed_rings", "rolled_button", "crimp_ring", "can_rim", "pull_tab",
           "cap_ridges", "screw_threads", "glue_flap", "flap_seams", "worn_edges", "cracked_ink_folds", "mold_seam",
           "screws", "stitching", "fur_pile", "sticker", "scratches", "dents", "fingerprints", "dust", "faded_print"]


def construction(cid, card=None, model=None, log=print):
    """How the real thing is made (layers, materials, the small real details), written once by your local AI and
    kept on the item's card. The builders use it to build each layer as its own part with its own material."""
    card = card or make(cid, log=log)
    if card.get("construction"):
        return card["construction"]
    sys.path.insert(0, HERE)
    import vet as V
    model = model or V.model()
    body = {"model": model, "stream": False, "format": "json", "think": False,      # a list, not a puzzle: no long
            "options": {"temperature": 0.2, "num_predict": 1200},                      # thinking (it took 4+ minutes)
            "messages": [{"role": "user", "content": BUILD.format(product=card["product"], size=card["size"],
                                                                  materials=MATERIALS, details=DETAILS)}]}
    try:
        txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
        c = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        log(f"[card] {cid}: how-it's-made step failed ({e}) - built with the defaults for its route")
        return {}
    for L in c.get("layers", []):
        if L.get("material") not in MATERIALS:
            L["material"] = "molded_plastic"
        L["details"] = [d for d in L.get("details", []) if d in DETAILS]
    card["construction"] = c
    json.dump(card, open(path(cid), "w"), indent=1)
    log(f"[card] {cid}: made of " + "; ".join(f"{L.get('part')} ({L.get('material')}: {', '.join(L['details']) or '-'})"
                                         for L in c.get("layers", [])))
    return c


def details(card):
    """Every detail named for any layer of this item (a set)."""
    return {d for L in (card.get("construction") or {}).get("layers", []) for d in L.get("details", [])}


def materials(card):
    return [L.get("material") for L in (card.get("construction") or {}).get("layers", [])]


def path(cid):
    return os.path.join(DIR, cid + ".json")


def catalog(cid):
    try:                                                     # an item Cody asked for on his phone (portal.py)
        import portal
        e = portal.catalog_entry(cid)
        if e:
            return e
    except Exception:
        pass
    plan = json.load(open(os.path.join(ROOT, "assets", "plan", "items.json")))
    beh = json.load(open(os.path.join(ROOT, "assets", "plan", "behavior.json")))
    p = plan.get(cid, {})
    return {"product": p.get("product") or p.get("display") or cid.replace("_", " "),
            "size": p.get("size") or beh.get(cid, {}).get("size") or [0.1, 0.1, 0.1],
            "mat": beh.get(cid, {}).get("mat", "plastic"),
            "master": json.load(open(os.path.join(ROOT, "assets", "plan", "shapes.json"))).get(cid)}


def year_of(text):
    m = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", text)
    return int(m.group(1)) if m else None


def make(cid, model=None, redo=False, log=print):
    """The item's card: read it if made before, else ask your local AI once and keep it."""
    if os.path.exists(path(cid)) and not redo:
        return json.load(open(path(cid)))
    sys.path.insert(0, HERE)
    import vet as V
    c = catalog(cid)
    model = model or V.model()
    body = {"model": model, "stream": False, "format": "json", "think": True, "options": {"temperature": 0.2},
            "messages": [{"role": "user", "content": ASK.format(product=c["product"], size=c["size"], mat=c["mat"])}]}
    txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
    card = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    if card.get("route") not in ("round", "box", "flat", "free"):
        card["route"] = "free"
    card.update(id=cid, product=c["product"], size=c["size"], mat=c["mat"], year=year_of(c["product"]),
                master=c["master"], model=model)
    yr = card["year"]
    card["searches"] = list(dict.fromkeys(
        [s for s in card.get("searches", []) if isinstance(s, str)][:4]
        + ([f"{str(yr)[2]}0s {c['product'].split(',')[0]}" if yr and yr < 2000 else c["product"].split(",")[0]])))
    os.makedirs(DIR, exist_ok=True)
    json.dump(card, open(path(cid), "w"), indent=1)
    log(f"[card] {cid}: {card['route']}; recognize: {'; '.join(card.get('recognize', []))}")
    return card


ERA_Q = """Catalog item: {product}. Its era: {era} (any year in that range).
A catalog name can use a later or more general name than the one printed on the item back then. From what you know
about this product line, answer for THAT era's version only:
{{"names": [1 to 3 names it was actually sold under in {words}, exactly as its own label or package said them then
            (brand + line + version, e.g. a model or feature name of that time)],
 "marks": [3 to 5 things you can SEE on that era's version that a later or earlier one doesn't have (a feature
           printed on it, a logo style, colors, a tester, a slogan)],
 "not_then": [1 to 3 visible things that would mean a photo shows a later or earlier version],
 "searches": [5 short Google Images searches (2 to 6 words) that find photos of THAT era's version: use its own
              name from then and era words like "{words}" or "vintage" - never one exact year]}}
Answer ONLY the JSON."""


def _era_web(card, words, log=print):
    """What sellers and pages call old ones of this item: web search titles and snippets (free search, no key),
    for the item's full name and for its brand + kind without the catalog's line name (a catalog name can carry a
    later line name)."""
    try:
        import websearch as W
    except Exception:
        return []
    name = str(card.get("product", "")).split(",")[0].strip()
    toks = name.split()
    qs = [f"vintage {name} {words}"]
    if len(toks) > 3:
        qs.append(f"vintage {toks[0]} {' '.join(toks[2:])} {words}")       # brand + kind, without the line name
    out = []
    for q in qs:
        try:
            for r in W.search(q, n=8, browser=False) or []:
                t = re.sub(r"\s+", " ", f"{r.get('title', '')} - {r.get('snippet', '')}").strip(" -")
                if t:
                    out.append(t[:160])
        except Exception as e:
            log(f"[card] web search for the era's version skipped: {e}")
    return list(dict.fromkeys(out))[:14]


def era_version(cid, card, model=None, log=print, evidence=(), refresh=False):
    """What the item was called and looked like IN ITS ERA ("90s"), from your AI's own knowledge plus what the photos
    found so far showed (evidence: names read on photos judged to be from the right era). The catalog may call a
    1998 Duracell "Coppertop" while the 90s battery itself said "PowerCheck" (2026-10-03) - the hunt, the photo
    judge and the pick all use the era's own names and marks. Kept on the card; asked again when the evidence or
    the era changes."""
    import era as ERA
    sys.path.insert(0, HERE)
    import vet as V
    y = card.get("year")
    if not y:
        return card.get("era_version") or {}
    ev = sorted({str(e).strip()[:80] for e in evidence if str(e).strip()})[:12]
    old = card.get("era_version") or {}
    if old.get("era") == ERA.words(y) and old.get("names") and not refresh and \
            (old.get("web") is not None) and (old.get("evidence") or not ev):
        return old                                    # worked out once; asked again after you turn photos down or
    #                                                   when photos from the era give it something new to go on
    q = ERA_Q.format(product=card.get("product"), era=ERA.describe(y), words=ERA.words(y))
    web = _era_web(card, ERA.words(y), log)
    if web:
        q += ("\nWeb results about old ones (sellers' listing titles and pages): " + " || ".join(web)
              + ". The names sellers of old ones put in their titles are good evidence of what it said back then.")
    if ev:
        q += ("\nPhotos already found that a judge placed in that era show the item labeled as: " + "; ".join(ev)
              + ". Use them: a name printed on those photos is better evidence than memory.")
    model = model or V.model()
    try:
        body = {"model": model, "stream": False, "format": "json", "think": True, "options": {"temperature": 0},
                "messages": [{"role": "user", "content": q}]}
        txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
        v = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        log(f"[card] {cid}: could not work out the era's own version ({e})")
        return old
    clean = lambda k, n: [str(x).strip()[:80] for x in v.get(k) or [] if str(x).strip()][:n]
    ev_out = {"era": ERA.words(y), "evidence": ev, "web": web, "names": clean("names", 3), "marks": clean("marks", 5),
              "not_then": clean("not_then", 3),
              "searches": [ERA.in_words(x, y) for x in clean("searches", 5)]}
    card["era_version"] = ev_out
    if os.environ.get("CRUSHED_TRIAL") != "1":
        os.makedirs(DIR, exist_ok=True)
        json.dump(card, open(path(cid), "w"), indent=1)
    log(f"[card] {cid}: in the {ev_out['era']} it was sold as {', '.join(ev_out['names']) or '?'}; marks of that "
        f"version: {'; '.join(ev_out['marks'])}")
    return ev_out


if __name__ == "__main__":
    print(json.dumps(make(sys.argv[1], redo="--redo" in sys.argv), indent=1))
