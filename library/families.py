"""WHAT KIND OF THING IS THIS? Before anything is built, your AI looks at the picked photo and decides which family of
the family library (library/family_library.json) the item belongs to - a folding carton, a circuit card, a battery
cell, a soft bag, a molded gadget ... The family then decides how the item is hunted, researched, built and checked.

    fam = families.classify(card, picked_photo, use)    # {"family", "confidence", "why", ...} kept on the card
    f = families.get(fam["family"])                      # the family's whole entry
    families.builder(f)                                  # which builder makes it NOW (never a wrong one)

Rules:
  - The family is read from the PHOTO (with the catalog name as a hint), not guessed from the name alone - the
    "AAA roadside emergency kit in zippered bag" is a soft bag, whatever a name-only guess said.
  - Unsure (confidence under 6 of 10) means "general": the one-off builder makes it from its parts.
  - A family whose own builder is missing goes to the general builder; if that can't make it either, the item
    waits with a plain reason - it is never built with a builder made for something else.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
LIB = os.path.join(HERE, "family_library.json")
VERSION = 1

ASK = """[family] Picture 1 is the photo picked as the true "{product}" (catalog size {size} mm, year {year}).
{notes}Decide what KIND of physical object this is, from what you SEE in the photo (the name is only a hint).
The families:
{menu}
Answer ONLY JSON:
{{"family": "<one family key from the list>",
 "confidence": 0-10 (10 = certain from the photo),
 "why": "what in the photo shows it, in one sentence",
 "second": "<the next most likely family key>",
 "kind_name": "if NO family truly fits, the kind of thing in plain words any person would use (e.g. 'plush toy', 'jeans', 'sneaker', 'graphics card', 'magazine'); else empty",
 "material_outside": "what the outside is made of, e.g. printed paperboard, molded ABS plastic, nylon fabric, steel",
 "is_package": true if it is a package that holds a product, false if it is the product itself}}"""


def library():
    import kits
    return kits.library()                                   # (the hand-written kits plus the ones your AI wrote)


def get(name):
    lib = library()["families"]
    return dict(lib.get(name) or lib["general"], family=name if name in lib else "general")


def menu():
    out = []
    for k, f in library()["families"].items():
        bits = f"- {k}: {f['what']}"
        if f.get("looks_like"):
            bits += f" (e.g. {', '.join(f['looks_like'][:6])})"
        if f.get("not"):
            bits += f"; NOT {', '.join(f['not'][:4])}"
        out.append(bits)
    return "\n".join(out)


def organic_ready():
    """The organic builder (Hunyuan3D) counts as ready only when its test made a real shape AND painted it, the whole
    way a build uses it (a shape-only proof from before 2026-10-03 does not count)."""
    try:
        p = json.load(open(os.path.join(WORK, "hunyuan_proven.json")))
        return p.get("ok") is True and p.get("painted") is True
    except Exception:
        return False


def builder(f):
    """(builder, why) for a family entry right now: its own builder, else the general one, else None + the reason."""
    b, s = f.get("builder"), f.get("builder_status", "missing")
    if b == "organic":
        # a soft or molded thing is built from its PARTS (the kit's: body, eyes, beak, feet...), each its own solid
        # with its own material; a one-photo organic guess of the whole thing is never a master asset (the Furby,
        # 2026-10-03: a blank back, the hang tag built in, the photo's light baked in)
        return "assembly", "built from its parts (a soft or molded thing is never guessed whole from one photo)"
    if b and s in ("ready", "partial"):
        return b, ("ready" if s == "ready" else "works, with known gaps: " + "; ".join(f.get("gaps", [])))
    return "assembly", f"no {f.get('family')} builder yet - the general builder makes it from its parts"


def classify(card, picked, use=None, log=print, redo=False, notes=""):
    """The item's family, read from the picked photo. Kept on the card (card["family_lib"]) until a Redo."""
    have = card.get("family_lib") or {}
    lib = library()["families"]
    import kits
    if have.get("family") and have.get("version") == VERSION and not redo and have.get("picked") == picked \
            and (have["family"] == "general" or kits.finished(lib.get(have["family"]) or {})):
        return have                                         # (a family still without a kit is looked at again)
    size = "x".join(str(round(x * 1000)) for x in (card.get("size") or [0, 0, 0])[:3])
    got = {}
    if use and picked:
        try:
            import vet as V
            got = V.ask(use, ASK.format(product=card.get("product", ""), size=size, year=card.get("year") or "?",
                                        notes=(f"Notes from the owner about this item: {notes}\n" if notes else ""),
                                        menu=menu()), [picked], think=True, side=1280) or {}
        except Exception as e:                              # no answer is not an answer: never guessed, never kept
            raise RuntimeError(f"your AI could not look at the photo to decide what kind of thing it is ({e})")
    if not got:
        raise RuntimeError("your AI gave no answer about what kind of thing this is")
    fam = re.sub(r"[^a-z_]", "", str(got.get("family", "")).lower())
    conf = got.get("confidence") if isinstance(got.get("confidence"), (int, float)) else 0
    if (fam not in lib or conf < 6 or fam == "general") and str(got.get("kind_name") or "").strip() and use and picked:
        import kitmaker                                     # a kind none of the kits covers: studied and written now
        kk, kit = kitmaker.ensure(str(got["kind_name"]).strip(), card, picked, use, log)
        if kk:
            lib = library()["families"]
            fam, conf = kk, max(conf, 6)
            got["why"] = (got.get("why") or "") + f" - a kind your AI studied itself: {kk}"
    if fam in lib and fam != "general" and conf >= 6 and not kits.finished(lib[fam]) and use and picked:
        import kitmaker                                     # a family without a finished kit: your AI studies the
        kind = str(got.get("kind_name") or "").strip()      # KIND it named (an "electronic plush toy", not the vague
        kk, kit = kitmaker.ensure(kind or fam, card, picked, use, log)   # "organic toy") and that kit is used
        lib = library()["families"]
        if kk and kk in lib:
            fam = kk
            got["why"] = (got.get("why") or "") + f" - a kind your AI studied itself: {kk}"
    if fam not in lib or conf < 6:
        why = (f"unsure ({fam or 'no answer'}, confidence {conf}/10)" if fam in lib or fam else "the photo could not be read")
        fam, conf = "general", conf
        got["why"] = (got.get("why") or "") + f" - {why}: the general one-off builder makes it from its parts"
    out = {"family": fam, "confidence": conf, "why": str(got.get("why", ""))[:300],
           "second": str(got.get("second", ""))[:40], "material_outside": str(got.get("material_outside", ""))[:80],
           "is_package": got.get("is_package") is True, "picked": picked, "version": VERSION}
    card["family_lib"] = out
    f = lib[fam]
    card["route"] = f["route"] if f["route"] in ("round", "box", "flat", "free") else (
        "box" if f["route"] == "pcb" else "free")
    if f.get("recipe"):
        card["recipe_family"] = f["recipe"]
    log(f"[family] {card.get('id', '')}: {fam} ({conf}/10) - {out['why']}")
    return out


if __name__ == "__main__":
    print(menu())
