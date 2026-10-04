"""KITS: the kinds of things the asset maker knows how to make (library/kits/DESIGN.md).

A kit is a family in family_library.json, plus what makes it a kit:
  variants   the standard sizes of this kind of thing (a battery: AA / AAA / C / D), with the measured sources
  template   how the variant's exact shape is made - no tracing from a photo for a thing that has a standard size
  zones      where its print goes and what kind of zone each is (wrap / rect / disc / fabric / form), and what is
             NORMALLY printed there on this kind of thing - so a side no photo shows is rebuilt with what belongs
             there (from verified facts), never left blank and never invented

    kit = kits.get("cylindrical_cell")
    v, why = kits.pick_variant(kit, card)  # ("AA", "named in the catalog"); (None, ...) when none fits
    spec = kits.spec_for("cylindrical_cell", "AA")   # the exact shape for the lathe builder (None: no template)
    for z in kits.zones(kit): ...           # {"name", "kind", "typical": [...]}
"""
import copy
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "family_library.json")


def library():
    """The hand-written kits (family_library.json) plus the kits your AI studied and wrote itself (kitmaker.py)."""
    lib = json.load(open(LIB))
    try:
        import kitmaker
        for k, v in kitmaker.learned().items():
            if k in lib["families"]:                      # a hand-written family your AI finished studying:
                for kk, vv in v.items():                  # its parts, zones, sizes and side words fill the gaps
                    if kk in ("parts", "zones", "variants", "variant_default", "side_words", "views_needed",
                              "construction", "learned") and not lib["families"][k].get(kk):
                        lib["families"][k][kk] = vv
            else:
                lib["families"][k] = v
    except Exception:
        pass
    return lib


def get(name):
    return (library().get("families") or {}).get(name) or {}


def _named(kit, card):
    """The variant the catalog name says (its own name or one of its other names; the longest match wins, so AAA
    before AA and "12 fl oz" before "12 oz"), or None."""
    vs = (kit or {}).get("variants") or {}
    text = " ".join(str(card.get(k, "")) for k in ("product", "display"))
    names = sorted(((n, v) for v, d in vs.items() for n in [v] + list(d.get("names") or [])),
                   key=lambda x: len(x[0]), reverse=True)
    for n, v in names:
        if re.search(r"(?<![A-Za-z0-9.])" + re.escape(n) + r"(?![A-Za-z0-9])", text, re.I):
            return v
    return None


def _fits(size_mm, card, within=0.05):
    """The catalog's size for the item agrees with a standard size (each side within 5%, or as given)."""
    s = card.get("size") or []
    if len(s) != 3 or not size_mm:
        return False
    a = sorted(1000 * float(x) for x in s)
    b = sorted(float(x) for x in size_mm)
    return all(abs(x - y) <= within * y for x, y in zip(a, b))


def pick_variant(kit, card):
    """(variant, why) - the kit's standard size this item is, or (None, why) when it is none of them.
    Trusted only when the catalog name says it (and the catalog's size doesn't disagree by more than 25%), or the
    catalog's size alone agrees within 5%: a soup can or a 330 ml can is not forced into a 12 oz soda can's shape,
    nor an N cell into an AA."""
    vs = (kit or {}).get("variants") or {}
    v = _named(kit, card)
    if v and card.get("size") and not _fits(vs[v].get("size_mm"), card, within=0.25):
        # the name says a size the catalog's measurements don't (a "12 oz" Celsius is a tall slim can, not the
        # standard 12 oz can): not forced into the standard - traced from the photo at the catalog size
        return None, (f"the name says {v} but the catalog size {[round(1000 * x, 1) for x in card['size']]} mm is "
                      f"not {vs[v].get('size_mm')} - traced from the photo at the catalog size")
    if v:
        return v, "named in the catalog"
    for name in sorted(vs, key=lambda n: n != (kit or {}).get("variant_default")):
        if _fits(vs[name].get("size_mm"), card, within=0.05):   # close: a 330 ml can (115 mm) is not a 12 oz (123)
            return name, "the catalog size agrees with the standard"
    return None, "not one of this kind's standard sizes - traced from the photo at the catalog size"


def variant_of(kit, card):
    """The kit's variant this item is (see pick_variant), or None."""
    return pick_variant(kit, card)[0]


def zones(kit):
    """The kit's print zones. A family without its own zone list gets them from its sides: a round thing has one
    wrapped label and two round ends; anything else six flat sides (or two, for a sheet)."""
    if (kit or {}).get("zones"):
        return kit["zones"]
    route = (kit or {}).get("route")
    faces = (kit or {}).get("faces") or []
    kind = {"round": lambda f: "wrap" if f == "label" else "disc"}.get(route, lambda f: "rect")
    return [{"name": f, "kind": kind(f), "typical": []} for f in faces]


# What a printed package's sides carry when its kit says nothing more specific - the things eraprint can draw from
# facts with receipts: logo, name, picture (cut from the real front), net_weight, maker_lines, legal_lines,
# nutrition, ingredients, upc. In the order they are drawn, top to bottom.
GENERIC_ELEMENTS = {
    "front": ["logo", "name", "picture", "net_weight"],
    "back": ["logo", "name", "picture", "net_weight", "maker_lines"],
    "left": ["nutrition", "ingredients"],
    "right": ["logo", "maker_lines", "legal_lines"],
    "top": ["logo"],
    "bottom": ["upc", "legal_lines"],
}
FOOD_ONLY = ("nutrition", "ingredients")


def elements(kit, zone, food=True):
    """What this zone of this kind of thing carries, as things that can be drawn from facts (see GENERIC_ELEMENTS):
    the kit's own list for the zone, else the generic package side's. Nutrition and ingredients only on food; a side
    left with nothing gets the logo, name and net weight."""
    els = None
    for z in zones(kit):
        if z.get("name") == zone and z.get("elements") is not None:
            els = list(z["elements"])
    if els is None:
        els = list(GENERIC_ELEMENTS.get(zone, ["logo"]))
    if not food:
        els = [e for e in els if e not in FOOD_ONLY] or ["logo", "name", "net_weight"]
    return els


def finished(kit):
    """A kit the asset maker can build from: it knows the print zones, and either the parts or a builder that
    makes the whole thing from its own recipe (the lathe, the carton, the circuit card, the box)."""
    kit = kit or {}
    if not kit.get("zones") and not kit.get("faces"):
        return False
    return bool(kit.get("parts")) or (kit.get("builder") in ("lathe", "carton", "pcb", "box")
                                      and kit.get("builder_status") in ("ready", "partial"))


def typical(kit, zone):
    """What is normally printed on this zone of this kind of thing ([] = nothing in particular)."""
    for z in zones(kit):
        if z.get("name") == zone:
            return list(z.get("typical") or [])
    return []


# ------------------------------------------------------------------ templates: exact shapes from standard sizes
def _cell(variant, kit):
    """A round cell at its standard size, made from the measured AA master (shapes/specs/aa_battery.json): the
    body stretched to the length, the shoulders, lips and end pressings kept at their real size, the + button set
    to the standard's size."""
    v = (kit.get("variants") or {}).get(variant) or {}
    if not v.get("size_mm"):
        return None
    master = json.load(open(os.path.join(HERE, "shapes", "specs", "aa_battery.json")))
    spec = copy.deepcopy(master)
    R0, L0 = 7.25, 50.51
    R, L = v["size_mm"][0] / 2, v["size_mm"][2]
    rb0, hb0 = 2.75, 0.91                                  # the AA master's button: radius, height
    bm = v.get("button_mm") or []
    rb = bm[0] / 2 if bm else rb0 * R / R0                 # the + button: the standard's size, else scaled across
    hb = bm[1] if len(bm) > 1 else hb0                     # its height: the standard's, else the AA's (never taller
    #                                                        than its surroundings - a scaled height dipped below them)
    lo, hi = 1.0, 48.9                                     # below / above: end details kept at their real size
    for part in spec["profile"]:
        pts = []
        for r, z in part["pts"]:
            top, bottom = z >= hi, z <= lo
            if bottom:
                z2 = z
            elif top:
                z2 = z + (L - L0)
            else:
                z2 = lo + (z - lo) * ((hi + (L - L0)) - lo) / (hi - lo)
            if r >= 5.0:                                   # the sleeve, its lip and the shoulder: real size
                r2 = R - (R0 - r)
            elif top and r <= rb0:                         # the + button
                r2 = r * rb / rb0
                if z > L0 - hb0:
                    z2 = L - (L0 - z) * hb / hb0
            elif top:                                      # the pressed rings between button and shoulder
                r2 = rb + (r - rb0) * ((R - (R0 - 5.0)) - rb) / (5.0 - rb0)
            else:                                          # the - end's pressings
                r2 = r * (R - (R0 - 5.0)) / 5.0
            pts.append([round(r2, 3), round(z2, 3)])
        part["pts"] = pts
    spec["id"] = f"{variant.lower()}_cell"
    spec["name"] = f"{variant} cell at its standard size ({v['size_mm'][0]} x {v['size_mm'][2]} mm)"
    spec["source"] = v.get("source", "") + " | shape: the measured AA master, stretched to this size"
    return spec


TEMPLATES = {"cell": _cell}


# ------------------------------------------------------------------ refining a traced shape with the kit's standards
def refine(kit_name, variant, spec):
    """A shape traced from a photo, given the parts every item of this kind has at their standard size - the parts a
    side photo can't show. A can's lid: the photo traces a flat top; a real 12 oz can's lid sits in a seamed rim,
    dropping 6.86 mm into the countersink and rising 2.29 mm to the center panel (CMI 202 end). Returns
    (spec, [what was done])."""
    kit = get(kit_name)
    v = (kit.get("variants") or {}).get(variant or "") or {}
    done = []
    end = v.get("end_mm")
    if end:
        top = next((p for p in spec.get("profile", []) if p.get("part") == "top"), None)
        side = next((p for p in spec.get("profile", []) if p.get("part") == "label"), None)
        if top and side:
            r0, H = side["pts"][-1]
            cs, depth, panel = end["countersink_diameter"] / 2, end["countersink_depth"], end["panel_height"]
            if r0 > cs + 1.5:
                top["pts"] = [[r0, H], [r0 - 0.6, H], [r0 - 1.2, H - 0.6], [r0 - 1.3, H - 2.5],
                              [cs + 0.5, H - depth + 0.26], [cs, H - depth], [cs - 0.5, H - depth + 0.26],
                              [cs - 0.6, H - depth + panel], [0, H - depth + panel]]
                done.append(f"the lid: seamed rim, countersink {depth} mm deep at {2 * cs:.1f} mm across, center "
                            f"panel {panel} mm up ({end.get('source', '').split('(')[0].strip()})")
    return spec, done


def spec_for(kit_name, variant):
    """The exact shape spec for a kit's variant (the lathe builder's input), or None when the kit has no template."""
    kit = get(kit_name)
    fn = TEMPLATES.get(kit.get("template") or "")
    if not fn or not variant:
        return None
    return fn(variant, kit)
