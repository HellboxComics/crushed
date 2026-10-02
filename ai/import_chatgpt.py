#!/usr/bin/env python3
"""
IMPORT -- turn ChatGPT's creative-pass replies (ASSET / ONE / ITEM lines) into the build.

    python3 ai/import_chatgpt.py ai/remaster/chatgpt/*.txt

Reads every line that starts with ASSET, ONE or ITEM (anything else is ignored), and writes:
  assets/plan/items.json      every object: display name, real size (m), eras, group, mass, notes
  assets/plan/behavior.json   how it crushes, how hard, what it is made of, real size
  assets/plan/shapes.json     {object: the object whose 3D shape it reuses} (same_shape_as)
  assets/plan/ones.json       every one-of-one recipe (ONE + its ITEM lines)
  ai/remaster/prompts/<id>.txt / .turn.txt / .inside.txt / .query   the words the Mac draws from
Later batches win over earlier ones for the same id. Problems are printed in plain words, never guessed around.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "assets", "plan")
PROMPTS = os.path.join(ROOT, "ai", "remaster", "prompts")
MATS = {"plastic", "soft_plastic", "metal", "foil", "paper", "card", "glossy_print", "fabric", "rubber", "clay", "ceramic",
        "glass", "wood", "food", "chocolate", "candy", "foam", "wax"}
HOWS = {"crumple", "fold", "squish", "dent", "snap", "crumble"}
HOW_ALIAS = {"bend": "fold", "tear": "fold", "shatter": "snap", "crack": "snap", "flatten": "crumple", "crush": "crumple",
             "stretch": "squish", "buckle": "dent", "warp": "fold", "rip": "fold"}
MAT_ALIAS = {"vinyl": "soft_plastic", "denim": "fabric", "nylon": "fabric", "cotton": "fabric", "fleece": "fabric",
             "leather": "fabric", "suede": "fabric", "shell": "ceramic", "silicone": "rubber", "latex": "rubber",
             "cardboard": "card", "fiber": "card", "felt": "fabric", "synthetic": "fabric", "composite": "plastic", "aluminum": "metal", "steel": "metal", "tin": "metal", "porcelain": "ceramic"}
DENSITY = {"metal": 2.0, "glass": 1.2, "ceramic": 1.1, "wood": 0.6, "clay": 1.2, "plastic": 0.5, "soft_plastic": 0.4,
           "rubber": 0.6, "food": 0.6, "chocolate": 0.9, "candy": 0.9, "wax": 0.8, "paper": 0.4, "card": 0.3,
           "glossy_print": 0.4, "fabric": 0.2, "foam": 0.05, "foil": 0.1}      # rough, of the bounding box, g/cm3
SOURCES = re.compile(r"\.\s+(?:[A-Z][\w'&.-]*\s?){1,4}\.?\s*$")           # "... screws. MusicBrainz"


def clean(s):
    s = s.strip()
    m = SOURCES.search(s)
    if m and not re.search(r"[a-z]{3,}\s+[a-z]{3,}", m.group(0)[2:]):      # a trailing name, not a sentence
        s = s[:m.start() + 1]
    return " ".join(s.split())


def era_of(year):
    return 0 if year <= 1990 else 1 if year <= 1996 else 2 if year <= 2002 else 3 if year <= 2008 else 4


def years(s):
    ys = [int(y) for y in re.findall(r"(19[5-9]\d|20[0-2]\d)", s)]
    return ys


def size_m(s):
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)[:3]]
    if len(n) != 3:
        return None
    return [round(x / 100, 4) for x in n]                                 # cm -> m, [width, depth, height]


def main(files):
    os.makedirs(PLAN, exist_ok=True)
    load = lambda f: json.load(open(os.path.join(PLAN, f))) if os.path.exists(os.path.join(PLAN, f)) else {}
    items, beh, shapes, ones = load("items.json"), load("behavior.json"), load("shapes.json"), load("ones.json")
    probs, n_asset, n_item, n_one = [], 0, 0, 0
    catalog = set()
    for f in files:                                        # every regular catalog id first, whichever batch it is in
        for raw in open(f, encoding="utf-8", errors="replace"):
            p = [x.strip() for x in raw.split("|")]
            if p and p[0].upper() == "ASSET" and len(p) >= 16:
                catalog.add(re.sub(r"[^a-z0-9_]", "_", p[2].lower()).strip("_"))
    for f in files:
        for raw in open(f, encoding="utf-8", errors="replace"):
            line = raw.strip()
            kind = line.split("|", 1)[0].strip().upper()
            if kind not in ("ASSET", "ITEM", "ONE"):
                continue
            p = [x.strip() for x in line.split("|")]
            if kind == "ONE":
                if len(p) < 8:
                    probs.append(f"ONE line too short: {line[:80]}")
                    continue
                t = p[1].upper().replace("’", "'")
                ys = years(p[7])
                ones[t] = dict(ones.get(t, {}), theme=p[2], lore=clean(p[3]), flavor=[p[4], p[5], p[6]],
                               era=sorted({era_of(y) for y in range(min(ys), max(ys) + 1)}) if ys else [0, 1, 2, 3, 4],
                               mix=[], no_wires=True)
                n_one += 1
                continue
            if kind == "ASSET":
                if len(p) < 16:
                    probs.append(f"ASSET line has {len(p)} parts, needs 16: {line[:90]}")
                    continue
                _, fam, oid, same, name, qty, size, mat, how, hard, role, rep, themes, query, looks, inside = p[:16]
                count, rare = None, None
            else:
                if len(p) < 14:
                    probs.append(f"ITEM line has {len(p)} parts, needs 14: {line[:90]}")
                    continue
                _, title, oid, same, name, count, size, mat, how, hard, rare, query, looks, inside = p[:14]
                fam, role, themes = "one-of-one", "main", title
            oid = re.sub(r"[^a-z0-9_]", "_", oid.lower()).strip("_")
            if kind == "ITEM" and oid in catalog:          # already a regular catalog object: the recipe just uses it
                t = title.upper().replace("’", "'")
                o = ones.setdefault(t, {"mix": [], "no_wires": True})
                try:
                    k = max(1, int(re.findall(r"\d+", count)[0]))
                except (IndexError, ValueError):
                    k = 1
                o["mix"] = [m for m in o.get("mix", []) if m[0] != oid] + [[oid, k]]
                n_item += 1
                continue
            if kind == "ASSET":
                catalog.add(oid)
            sz = size_m(size)
            if not sz or min(sz) <= 0 or max(sz) > 12.0:
                probs.append(f"{oid}: size '{size}' doesn't read as W x D x H in cm")
                continue
            if max(sz) > 3.0:                                  # a long strand (light string, garland, cord): it
                L = sorted(sz)                                 # lives in the cube bunched up, so that's its size
                side = (L[0] * L[1] * L[2] * 4 / 0.4) ** (1 / 3)
                long_m = max(sz)
                sz = [round(side, 4), round(side, 4), round(side * 0.4, 4)]
                size = (f"{sz[0] * 100:.0f} x {sz[1] * 100:.0f} x {sz[2] * 100:.0f} cm, a {long_m:.1f} m strand "
                        f"bunched up loosely")
            mat = mat.lower().replace(" ", "_")
            mat = MAT_ALIAS.get(mat, mat)
            if mat not in MATS:
                probs.append(f"{oid}: material '{mat}' not on the list, used plastic")
                mat = "plastic"
            how = HOW_ALIAS.get(how.lower(), how.lower())
            if how not in HOWS:
                probs.append(f"{oid}: crush '{how}' not on the list, used fold")
                how = "fold"
            try:
                hard = max(0.0, min(1.0, float(hard)))
            except ValueError:
                hard = 0.5
            ys = years(name)
            e0 = era_of(min(ys)) if ys else 0
            eras = list(range(e0, min(4, e0 + 1) + 1))                    # its own era and the next (still around)
            vol = sz[0] * sz[1] * sz[2] * 1e6
            mass = round(max(0.002, vol * DENSITY[mat] / 1000 * 0.35), 3)  # objects aren't solid boxes
            regular = kind == "ASSET" or rare.lower().startswith("y")
            display = re.sub(r",?\s*(19|20)\d\d\s*$", "", name).strip()
            items[oid] = dict(items.get(oid, {}), display=display, product=name, size=[sz[0], sz[1], sz[2]], eras=eras,
                              group="era" if regular else "special",
                              weight=(1.0 if kind == "ASSET" else 0.12) if regular else 1.0,
                              mass=mass, family=fam, role=role.lower(), themes=themes,
                              notes=items.get(oid, {}).get("notes") or [name])
            beh[oid] = {"how": how, "hard": hard, "mat": mat, "size": [sz[0], sz[1], sz[2]]}
            base = re.sub(r"[^a-z0-9_]", "_", same.lower()).strip("_")
            if base and base != "none" and base != oid:
                shapes[oid] = base
            os.makedirs(PROMPTS, exist_ok=True)
            w = lambda ext, txt: open(os.path.join(PROMPTS, oid + ext), "w").write(txt.strip() + "\n")
            w(".txt", f"{name}. {clean(looks)}")
            w(".turn.txt", f"{name}, real size {size}, made of {mat.replace('_', ' ')}. {clean(looks)}")
            w(".inside.txt", clean(inside))
            w(".query", query)
            if kind == "ITEM":
                t = title.upper().replace("’", "'")
                o = ones.setdefault(t, {"mix": [], "no_wires": True})
                try:
                    k = max(1, int(re.findall(r"\d+", count)[0]))
                except (IndexError, ValueError):
                    k = 1
                o["mix"] = [m for m in o.get("mix", []) if m[0] != oid] + [[oid, k]]
                n_item += 1
            else:
                n_asset += 1
    for t, o in ones.items():
        o.setdefault("lore", "")
        o.setdefault("flavor", ["", "", ""])
    for f, d in (("items.json", items), ("behavior.json", beh), ("shapes.json", shapes), ("ones.json", ones)):
        json.dump(d, open(os.path.join(PLAN, f), "w"), indent=0, sort_keys=True)
    missing = sorted({b for b in shapes.values() if b not in items})
    print(f"loaded {n_asset} catalog assets, {n_one} one-of-ones, {n_item} one-of-one items; "
          f"{len(items)} planned objects in all, {len(set(shapes.values()))} shared shapes")
    if missing:
        print("waiting on shapes not loaded yet: " + ", ".join(missing))
    for p in probs:
        print("PROBLEM: " + p)


if __name__ == "__main__":
    main(sorted(sum((glob.glob(a) for a in sys.argv[1:]), [])))
