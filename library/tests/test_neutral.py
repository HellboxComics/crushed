"""S7 - NOTHING ITEM-SPECIFIC (audit 2026-10-04, RC9): no brand or one item's feature inside any prompt the brains see, no
battery-only or carton-only rule inside a shared builder (the kit carries what a kind of thing has)."""
import json
import os
import re
import sys

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB)
os.environ.setdefault("CRUSHED_REMASTER_WORK", "/tmp/crushed_neutral_test")

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


BRANDS = re.compile(r"duracell|powercheck|coppertop|pop-?tarts?|kellogg|furby|3dfx|voodoo|energizer", re.I)

# 1. every prompt constant the brains see, by module
import dossier, layout, vet, judge, run, kitmaker, families, review, cards, parts, labelparts, facts, eraprint  # noqa: E401,E402
prompts = {}
for mod in (dossier, layout, vet, judge, run, kitmaker, families, review, cards, parts, labelparts, facts, eraprint):
    for name in dir(mod):
        v = getattr(mod, name)
        if isinstance(v, str) and name.isupper() and len(v) > 80:
            prompts[f"{mod.__name__}.{name}"] = v
        elif isinstance(v, dict) and name.isupper():
            for k, x in v.items():
                if isinstance(x, str) and len(x) > 40:
                    prompts[f"{mod.__name__}.{name}[{k}]"] = x
check(len(prompts) > 20, f"{len(prompts)} prompt texts found to scan")
hits = {k: BRANDS.search(v).group(0) for k, v in prompts.items() if BRANDS.search(v)}
check(not hits, f"no brand or one item's feature inside any prompt: {hits}")

# 2. the kits carry kind knowledge, never one brand's feature as the example
fl = json.load(open(os.path.join(LIB, "family_library.json")))
txt = json.dumps(fl)
check(not BRANDS.search(txt), f"family_library.json names no brand ({(BRANDS.search(txt) or re.match('', '')).group(0)!r})")

# 3. shared builders: the lid flap is kit-driven; no battery-only orientation guess in the shared unroller
box = open(os.path.join(LIB, "shapes", "box.py")).read()
check("flap = (argv[9]" in box and "if flap and surface == \"card\"" in box, "box.py builds a lid flap only when told the item has one")
r = open(os.path.join(LIB, "run.py")).read()
check('re.search(r"flap|tuck", made_how' in r, "run.py tells box.py from the item's construction / kit")
mos = open(os.path.join(LIB, "mosaic.py")).read()
check("def plus_left" not in mos and "def metal_end_top" not in mos and "metal_top" not in mos,
      "mosaic.py has no battery-only plus-end guess")
check("the metal ends, the plus button" not in layout.FIRST and "unprinted parts" in layout.FIRST,
      "the label prompt speaks of any item's unprinted parts, not a battery's")
pcb = open(os.path.join(LIB, "shapes", "pcb.py")).read()
check("side_left" not in pcb, "pcb.py: no bracket by default")
carton = open(os.path.join(LIB, "shapes", "carton.py")).read()
check(not re.search(r"sprinkle|frost|pastry_mat|crust_mat", carton), "carton.py: no one product's contents")

print(f"ALL {ok} PASS")
