"""KITS: the kinds of things the asset maker knows how to make (library/kits/DESIGN.md).

A kit is a family in family_library.json, plus what makes it a kit:
  variants   the standard sizes of this kind of thing (a battery: AA / AAA / C / D), with the measured sources
  template   how the variant's exact shape is made - no tracing from a photo for a thing that has a standard size
  zones      where its print goes and what kind of zone each is (wrap / rect / disc / fabric / form), and what is
             NORMALLY printed there on this kind of thing - so a side no photo shows is rebuilt with what belongs
             there (from verified facts), never left blank and never invented

    kit = kits.get("cylindrical_cell")
    v = kits.variant_of(kit, card)          # "AA"
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
    return json.load(open(LIB))


def get(name):
    return (library().get("families") or {}).get(name) or {}


def variant_of(kit, card):
    """The kit's variant this item is, from its catalog name (the longest name that matches wins: AAA before AA)."""
    vs = (kit or {}).get("variants") or {}
    text = " ".join(str(card.get(k, "")) for k in ("product", "display"))
    for name in sorted(vs, key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", text, re.I):
            return name
    return (kit or {}).get("variant_default")


def zones(kit):
    """The kit's print zones. A family without its own zone list gets them from its sides: a round thing has one
    wrapped label and two round ends; anything else six flat sides (or two, for a sheet)."""
    if (kit or {}).get("zones"):
        return kit["zones"]
    route = (kit or {}).get("route")
    faces = (kit or {}).get("faces") or []
    kind = {"round": lambda f: "wrap" if f == "label" else "disc"}.get(route, lambda f: "rect")
    return [{"name": f, "kind": kind(f), "typical": []} for f in faces]


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


def spec_for(kit_name, variant):
    """The exact shape spec for a kit's variant (the lathe builder's input), or None when the kit has no template."""
    kit = get(kit_name)
    fn = TEMPLATES.get(kit.get("template") or "")
    if not fn or not variant:
        return None
    return fn(variant, kit)
