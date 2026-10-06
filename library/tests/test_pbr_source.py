"""Material numbers come from a published database where it covers them - physicallybased.info v2 (CC0), kept as
a snapshot - not from a hand-typed table (2026-10-05 20:51). Roughness depends on finish and stays per kind."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import measure as M  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
snap = json.load(open(os.path.join(HERE, "factory", "physicallybased_v2.json")))
check(snap["header"]["license"].startswith("CC0") and "physicallybased.info" in snap["header"]["origin"], "the snapshot names its source and its CC0 license")
by = {m["name"]: m for m in snap["data"]}
P = json.load(open(os.path.join(HERE, "factory", "physics.json")))
n = 0
for kind, k in M.RANGES.items():
    src = k.get("source")
    if not src:
        continue
    n += 1
    m = by[src["material"]]
    mean = sum(m["color"]) / 3
    if m["metalness"] == 1:
        check(abs(k["base"][0] - max(0, mean - 0.15)) < 1e-3 and k["metallic"] == [0.9, 1.0],
              f"{kind}: base range centered on {src['material']}'s linear color ({mean:.3f}), metal")
    else:
        check(k["metallic"][0] == 0.0, f"{kind}: {src['material']} is no metal")
    if kind in P and P[kind].get("from"):
        dens = m["density"]
        check(P[kind]["density"] == round(sum(dens) / len(dens)) and src["material"] in P[kind]["from"]["density"],
              f"{kind}: density {P[kind]['density']} from the database, said so")
check(n >= 12, f"{n} kinds take their numbers from the database")
check("source" not in M.RANGES["zinc_gel"], "a paste (zinc gel) is not mapped to solid zinc")
check(all("roughness_note" in k for k in M.RANGES.values() if k.get("source")), "roughness is marked finish-dependent on every sourced kind")
print(f"ALL {ok} PASS")
