#!/usr/bin/env python3
"""
PLAN CHECK -- run after any change to the plan. Says in plain words what's wrong, and writes the full list of
objects the remaster must make (ai/remaster/expected.txt) so the phone page counts everything.

    .venv/bin/python ai/plan_check.py

Checks assets/plan/items.json and assets/plan/ones.json (formats in ai/REMASTER_BRIEF.md):
  - every object has a size in meters that makes sense (0.003 to 0.6), eras 0..4, a display name and notes
  - every one-of-one has at least 10 distinct named objects (15+ is the bar; under 15 is listed as TO DO), all of which exist, lore, flavor and eras
  - every object (code-built or planned) has an outside prompt and an inside prompt (or is listed as missing)
  - assets/real/*.json only names objects and one-of-ones that exist
Exit 0 = all good. Nothing is changed except expected.txt.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(ROOT, "ai", "remaster", "prompts")
PLAN = os.path.join(ROOT, "assets", "plan")
REAL = os.path.join(ROOT, "assets", "real")

PROBE = r'''
import bpy, sys, json
sys.path.insert(0, "blender")
from crushed.objects import load
from crushed import recipe, lore
reg = load()
print(json.dumps({"objects": {n: d.group for n, d in reg.items()},
                  "ones": {t: [n for n, _ in recipe.MONOCULTURES.get(t, [])] + list(recipe.ONE_FILLERS.get(t, ())) for t in recipe.ONE_OF_ONES},
                  "named": sorted(lore.NAMES),
                  "lore": sorted(lore.ONE_OF_ONES), "flavor": sorted(recipe.ONE_OF_ONE_FLAVOR)}))
'''


def main():
    bad = []
    short = []          # Harrow's bar: every one-of-one has at least 15 things to discover (the more the better)
    items = json.load(open(os.path.join(PLAN, "items.json"))) if os.path.exists(os.path.join(PLAN, "items.json")) else {}
    ones = json.load(open(os.path.join(PLAN, "ones.json"))) if os.path.exists(os.path.join(PLAN, "ones.json")) else {}
    for n, it in items.items():
        if not n.replace("_", "").isalnum() or n.lower() != n:
            bad.append(f"object name '{n}': use lowercase letters, digits and _ only")
        s = it.get("size")
        if not (isinstance(s, list) and len(s) == 3 and all(0.003 <= float(x) <= 0.6 for x in s)):
            bad.append(f"{n}: size must be [width, depth, height] in meters, each 0.003-0.6 (a soda can is [0.066, 0.066, 0.122])")
        if not set(it.get("eras", [0])) <= {0, 1, 2, 3, 4}:
            bad.append(f"{n}: eras must be from 0..4")
        if it.get("group", "special") not in ("special", "era"):
            bad.append(f"{n}: group must be 'special' (one-of-ones only) or 'era' (also rare in regular cubes)")
        if not it.get("display") or not it.get("notes"):
            bad.append(f"{n}: needs a display name and 2-3 notes")
    beh = json.load(open(os.path.join(PLAN, "behavior.json"))) if os.path.exists(os.path.join(PLAN, "behavior.json")) else {}
    hows = ("crumple", "fold", "squish", "dent", "snap", "crumble")
    for n, b in beh.items():
        if b.get("how") not in hows or not 0 <= float(b.get("hard", -1)) <= 1:
            bad.append(f"{n}: behavior needs how (one of {', '.join(hows)}) and hard 0..1")
    for n in items:
        if n not in beh:
            bad.append(f"{n}: no crush behavior in assets/plan/behavior.json")
    for t, o in ones.items():
        for k in (() if "extra" in o and "mix" not in o else ("mix", "lore", "flavor", "era")):
            if k not in o:
                bad.append(f"one-of-one {t}: missing '{k}'")
    r = subprocess.run([os.path.join(ROOT, ".venv", "bin", "python") if os.path.exists(os.path.join(ROOT, ".venv"))
                        else sys.executable, "-c", PROBE], cwd=ROOT, capture_output=True, text=True)
    try:
        info = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print("STOP: the code library would not load:\n" + r.stderr[-1500:])
        sys.exit(1)
    objs = info["objects"]
    for t, names in info["ones"].items():
        if not names:
            continue
        missing = [n for n in set(names) if n not in objs]
        if missing:
            bad.append(f"one-of-one {t}: these objects don't exist: {', '.join(sorted(missing))}")
        named = set(names) & set(info["named"])           # loose debris (paper, film) has no name and doesn't count
        if len(named) < 10 and t not in ("EMPTY", "UNCRUSHED", "SOLID GOLD"):
            bad.append(f"one-of-one {t}: only {len(named)} distinct named objects, needs at least 10")
        elif len(named) < 15 and t not in ("EMPTY", "UNCRUSHED", "SOLID GOLD"):
            short.append(f"{t} ({len(named)})")
    for t in ones:
        if t not in info["lore"] or t not in info["flavor"]:
            bad.append(f"one-of-one {t}: lore or flavor didn't load")
    need = sorted(n for n, g in objs.items() if g != "filler")
    noprompt = [n for n in need if not os.path.exists(os.path.join(PROMPTS, n + ".inside.txt"))]
    for f in ("names.json", "notes.json"):
        p = os.path.join(REAL, f)
        if os.path.exists(p):
            for k in json.load(open(p)):
                if k not in objs:
                    bad.append(f"assets/real/{f}: '{k}' is not an object")
    p = os.path.join(REAL, "ones.json")
    if os.path.exists(p):
        for k in json.load(open(p)):
            if k not in info["ones"]:
                bad.append(f"assets/real/ones.json: '{k}' is not a one-of-one")
    open(os.path.join(ROOT, "ai", "remaster", "expected.txt"), "w").write("\n".join(need) + "\n")
    print(f"{len(need)} objects to remaster, {len(info['ones'])} one-of-ones, {len(noprompt)} objects still need prompts")
    if noprompt:
        print("  need prompts: " + ", ".join(noprompt[:60]) + (" ..." if len(noprompt) > 60 else ""))
    if short:
        print(f"TO DO: {len(short)} one-of-ones under 15 distinct objects: " + ", ".join(short))
    for b in bad:
        print("PROBLEM: " + b)
    print("ALL GOOD" if not bad else f"{len(bad)} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
