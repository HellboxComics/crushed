"""The kits: the right standard size is picked (and only when the name or the catalog size says so), every cell
template is a sound shape at its exact size when Blender builds it, and every side of a box knows what it carries."""
import json
import os
import subprocess
import sys

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
import kits

ok = 0
OUT = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/kit_shapes"
os.makedirs(OUT, exist_ok=True)


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


cell, can, box = kits.get("cylindrical_cell"), kits.get("beverage_can"), kits.get("folding_carton")
pv = kits.pick_variant
check(pv(cell, {"product": "Duracell Coppertop AA alkaline battery", "size": [0.0145, 0.0145, 0.0505]})[0] == "AA", "AA named")
check(pv(cell, {"product": "Energizer AAA", "size": [0.0105, 0.0105, 0.0445]})[0] == "AAA", "AAA named (not AA)")
check(pv(cell, {"product": "Rayovac D cell", "size": [0.034, 0.034, 0.061]})[0] == "D", "D named")
check(pv(cell, {"product": "Duracell C battery"})[0] == "C", "C named (no size needed)")
check(pv(cell, {"product": "an N cell battery", "size": [0.012, 0.012, 0.030]})[0] is None,
      "an N cell is not forced into an AA")
check(pv(cell, {"product": "Panasonic battery", "size": [0.0145, 0.0145, 0.050]})[0] == "AA",
      "no size in the name, catalog size of an AA -> AA")
check(pv(can, {"product": "Coca-Cola 12 oz can", "size": [0.07, 0.07, 0.15]})[0] == "12 fl oz", "12 oz can named")
check(pv(can, {"product": "Surge citrus soda can", "size": [0.066, 0.066, 0.123]})[0] == "12 fl oz",
      "a soda can at a 12 oz can's catalog size")
check(pv(can, {"product": "Campbell's tomato soup can", "size": [0.068, 0.068, 0.102]})[0] is None,
      "a soup can is not forced into a soda can's shape")
check(pv(can, {"product": "Celsius Sparkling Orange energy drink 12 oz can", "size": [0.066, 0.066, 0.157]})[0] is None,
      "a '12 oz' slim can whose catalog size is tall is not forced into the standard can")
check(pv(can, {"product": "Amstel 330 ml aluminum can", "size": [0.066, 0.066, 0.115]})[0] is None,
      "a 330 ml can (115 mm) is not a 12 oz can (122.7 mm)")
check(pv(can, {"product": "Canada Dry Ginger Ale 12 oz can", "size": [0.066, 0.066, 0.122]})[0] == "12 fl oz",
      "Canada Dry 12 oz can -> the standard can")
check(pv(box, {"product": "Pop-Tarts box", "size": [0.2, 0.05, 0.13]})[0] is None, "a box kit with no sizes -> none")

# every cell template: Blender builds it, and it is the standard's size
for v, dims in (cell.get("variants") or {}).items():
    spec = kits.spec_for("cylindrical_cell", v)
    check(spec is not None, f"{v}: a template shape")
    rs = [r for part in spec["profile"] for r, z in part["pts"]]
    zs = [z for part in spec["profile"] for r, z in part["pts"]]
    D, L = dims["size_mm"][0], dims["size_mm"][2]
    check(abs(2 * max(rs) - D) < 0.05 and abs(max(zs) - min(zs) - L) < 0.05,
          f"{v}: {2 * max(rs):.2f} x {max(zs) - min(zs):.2f} mm (standard {D} x {L})")
    for part in spec["profile"]:
        zz = [z for r, z in part["pts"]]
        check(all(r >= 0 for r, z in part["pts"]), f"{v} {part.get('name', '?')}: no point inside out")
    sp = os.path.join(OUT, f"{v}.json")
    json.dump(spec, open(sp, "w"))
    r = subprocess.run([sys.executable, os.path.join(LIB, "shapes", "lathe.py"), "--", sp, os.path.join(OUT, v)],
                       capture_output=True, text=True, timeout=300)
    glb = os.path.join(OUT, v, spec["id"] + ".glb")
    check(os.path.exists(glb), f"{v}: Blender built {os.path.basename(glb)}" + ("" if os.path.exists(glb) else
                                                                            (r.stderr or r.stdout)[-400:]))
    import trimesh
    m = trimesh.load(glb, force="mesh")
    ext = sorted(m.extents * 1000)
    check(abs(ext[2] - L) < 0.3 and abs(ext[1] - D) < 0.3, f"{v}: the built model is {ext[1]:.1f} x {ext[2]:.1f} mm")

# a traced can gets the lid a side photo can't show (CMI 202 end): a seamed rim, the countersink, the center panel
spec = {"profile": [{"part": "bottom", "pts": [[0, 0], [28, 0]]},
                    {"part": "label", "pts": [[28, 0], [33.05, 4], [33.05, 110], [27.05, 122.7]]},
                    {"part": "top", "pts": [[27.05, 122.7], [0, 122.7]]}]}
spec, done = kits.refine("beverage_can", "12 fl oz", spec)
top = spec["profile"][2]["pts"]
check(done and min(z for r, z in top) == round(122.7 - 6.86, 2) or abs(min(z for r, z in top) - (122.7 - 6.86)) < 1e-6,
      f"the can's lid drops 6.86 mm into the countersink: {done}")
check(abs(top[-1][1] - (122.7 - 6.86 + 2.29)) < 1e-6 and top[-1][0] == 0, "and its center panel is 2.29 mm up")
spec2, done2 = kits.refine("cylindrical_cell", "AA", {"profile": [{"part": "top", "pts": [[1, 1], [0, 1]]}]})
check(not done2, "a kit without a lid standard is left as it is")

# every side of a box knows what it carries; non-food boxes carry no nutrition
for z in ("front", "back", "left", "right", "top", "bottom"):
    els = kits.elements(box, z)
    check(els and kits.typical(box, z), f"carton {z}: draws {els}; normally carries {kits.typical(box, z)[:2]}...")
check("nutrition" not in kits.elements(box, "left", food=False), "a non-food box's side has no nutrition panel")
check(kits.elements(None, "back") == kits.GENERIC_ELEMENTS["back"], "a family with no kit gets the generic sides")
check(kits.typical(cell, "label") and kits.typical(can, "label"), "round labels know what they normally carry")

# the dossier and eraprint use the kit's list (one place, not three)
import dossier
import eraprint
check(not hasattr(dossier, "SIDE_DEFAULTS") and not hasattr(eraprint, "DEFAULT"), "no second copy of the side lists")
e = {}
ms = dossier._must_show_rebuilt(e, "top", "box", {}, True, "packaging", "folding_carton")
check(e.get("want") == ["logo", "name"] and [m["what"] for m in ms][:2] == ["the real logo from the front photo",
                                                                            "product name"],
      f"a rebuilt carton top: {e.get('want')} -> {[m['what'] for m in ms]}")
print(f"\n{ok} checks passed")
