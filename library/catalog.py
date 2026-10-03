"""THE MASTER-ASSET RECORD: one catalog record per finished asset, kept in its Asset Library folder (asset.json) and in
the central catalog (~/crushed-render/remaster/catalog/<item>.json). It is the object database the commercial
library and the crushed.buzz component registry both read - the two projects share the master asset, never money.

What it holds: item id, title, era, brand, category (family), real dimensions, materials and how each part behaves
(density, stiffness, how it fails), what is inside, which versions exist (high-detail master, game-ready, LODs,
collision, physics, crush states), texture sets (branded / clean), an IP class PROPOSED by the rules below (always
marked for review), marketplace fields (empty until listed), the master file's fingerprint, and notes.

IP classes (the owner's framework):
  A  commercial clean      generic or original objects
  B  branded - review      a recognizable brand or trade dress on a useful object
  C  clearance required    licensed characters, movies, games, album art, real people
  D  cleared / abandoned   only when research proves it - never proposed automatically

    rec = catalog.record(cid, folder, card, dossier, physics)     # written to folder/asset.json + the catalog
"""
import hashlib
import json
import os
import re
import time

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
CHARACTER = re.compile(r"disney|pixar|marvel|dc comics|star wars|pok[eé]mon|nintendo|sega|warner|looney|"
                       r"simpsons|batman|superman|spider-?man|barbie|hello kitty|sesame|muppet|power rangers|"
                       r"teenage mutant|ninja turtles|aladdin|lion king|toy story|movie|film|album|soundtrack|"
                       r"game cartridge|video game|tv show|cartoon", re.I)


def _sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ip_class(card, dossier):
    """(class, why) - a proposal for the owner's review, never a legal decision."""
    idn = (dossier or {}).get("identity") or {}
    text = " ".join(str(x) for x in (card.get("product"), idn.get("brand"), idn.get("line"), idn.get("variant")))
    if CHARACTER.search(text):
        return "C", "names a licensed character, movie, show, game or album - clearance needed before selling"
    if idn.get("brand") or re.search(r"[A-Z][a-z]+'s|®|™", str(card.get("product"))):
        return "B", f"branded ({idn.get('brand') or 'a brand name'}) - sell with a clean texture, or review the branded one"
    return "A", "no brand or licensed art found - generic object"


def record(cid, folder, card, dossier=None, physics=None):
    dossier = dossier or {}
    physics = physics or {}
    idn = dossier.get("identity") or {}
    fam = (card.get("family_lib") or {}).get("family", "")
    blend = os.path.join(folder, cid + ".blend")
    cls, why = ip_class(card, dossier)
    parts = {k: {"material": v.get("material_kind"), "density_kg_m3": v.get("density"),
                 "stiffness_pa": v.get("stiffness"), "yield_pa": v.get("yield"), "fails": v.get("fails"),
                 "inside": bool(v.get("inside"))} for k, v in physics.items() if isinstance(v, dict)}
    rec = {
        "item_id": cid, "canonical_component_id": cid, "title": card.get("product"),
        "year": card.get("year"), "era": (idn.get("years") or []), "brand": idn.get("brand") or "",
        "line": idn.get("line") or "", "variant": idn.get("variant") or "", "category": fam,
        "dimensions_mm": [round(x * 1000, 1) for x in (card.get("size") or [])[:3]],
        "materials": sorted({p["material"] for p in parts.values() if p["material"]}),
        "parts": parts,
        "internal_structure": [k for k, p in parts.items() if p["inside"]],
        "status": {"high_poly_master": os.path.exists(blend), "game_ready": False, "lods": False,
                   "collision": False, "physics_ready": bool(parts), "destructible": False, "crush_states": False},
        "texture_sets": {"branded": True, "clean": False},
        "ip_class": {"proposed": cls, "why": why, "needs_review": True},
        "marketplace": {"cgtrader_sku": "", "fab_sku": "", "turbosquid_sku": "", "price": None, "sales": 0,
                        "status": "not listed"},
        "version": 1, "master_file_sha1": _sha1(blend) if os.path.exists(blend) else "",
        "crushed": {"appearances": [], "count": 0, "one_of_one_only": False},
        "built_by": card.get("built_by") or {},
        "sides_came_from": {f: {"source": e.get("source"), "page": e.get("page", "")}
                            for f, e in (dossier.get("faces") or {}).items()},
        "gaps": dossier.get("gaps", []),
        "notes": card.get("owner_note", ""), "made_at": time.time(),
    }
    old = os.path.join(WORK, "catalog", cid + ".json")
    if os.path.exists(old):                                 # a rebuild: version goes up, the history is kept
        try:
            prev = json.load(open(old))
            rec["version"] = int(prev.get("version", 1)) + (prev.get("master_file_sha1") != rec["master_file_sha1"])
            rec["marketplace"] = prev.get("marketplace", rec["marketplace"])
            rec["crushed"] = prev.get("crushed", rec["crushed"])
            if prev.get("ip_class", {}).get("reviewed"):    # the owner's own decision is never overwritten
                rec["ip_class"] = prev["ip_class"]
        except Exception:
            pass
    os.makedirs(os.path.dirname(old), exist_ok=True)
    for p in (os.path.join(folder, "asset.json"), old):
        tmp = p + ".tmp"
        json.dump(rec, open(tmp, "w"), indent=1)
        os.replace(tmp, p)
    return rec
