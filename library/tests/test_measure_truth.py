"""The exact measure tells the truth about a watertight part and a baked map (2026-10-05, 6:46 AM: the Duracell
failed 'mesh: steel 3268 open edges (holes)' and 'materials: steel metallic 0.71' - the part was closed and the
steel fully metallic. The glb stores a vertex once per UV seam, so a closed can came back as thousands of one-face
edges; and a baked map's black, uncovered background was averaged in with the metal). Now split vertices are
rejoined before holes are counted, and a map is averaged only where the part's UVs cover it."""
import json
import os
import subprocess
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import kits  # noqa: E402

ok = 0
PY = sys.executable


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def blender(script, *args, timeout=900):
    r = subprocess.run([PY, os.path.join(LIB, "shapes", script), "--", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{script}: " + (r.stderr or r.stdout)[-800:])


out = os.path.join(W, "cell")
os.makedirs(out)
spec = kits.spec_for("cylindrical_cell", "AA")
json.dump(spec, open(os.path.join(out, "spec.json"), "w"))
a = np.zeros((512, 1600, 3), np.uint8)
a[:, :, 0] = 200
Image.fromarray(a).save(os.path.join(out, "label.png"))
Image.fromarray(np.zeros((512, 1600, 3), np.uint8)).save(os.path.join(out, "label_mr.png"))
blender("lathe.py", os.path.join(out, "spec.json"), out, os.path.join(out, "label.png"), os.path.join(out, "label_mr.png"))
name = spec["id"]
blender("contract.py", os.path.join(out, name + ".blend"), out, name, "plastic")
glb = os.path.join(out, name + ".glb")
r = subprocess.run([PY, os.path.join(LIB, "measure_blender.py"), "--", glb, os.path.join(out, "m"), "round", "8"],
                   capture_output=True, text=True, timeout=900)
mb = json.load(open(os.path.join(out, "m", "measure_blender.json")))
parts = mb["parts"]

# 1. a closed part has no holes, however many UV seams its glb carries
holes = {p: i["open_edges"] for p, i in parts.items() if i["open_edges"]}
check(not holes, f"no part of a watertight battery shows holes (open edges: {holes or 'none'})")
check(all(i.get("signed_volume_mm3") is not None for i in parts.values()), "every part has a volume (only a closed mesh has one)")

# 2. a bare-steel part's maps are read where its UVs cover them, not over the black background
steel = next(m for m in parts["steel"]["materials"])
check(steel["metallic"] >= 0.95, f"steel reads fully metallic from its baked map ({steel['metallic']:.2f}, was 0.71 with the background counted)")
check(0.55 <= steel["base"][0] <= 0.85, f"its base color is the metal's, not darkened by background ({steel['base'][0]:.2f})")

# 3. a real hole is still a hole: cut a face out of the steel and measure again
import shutil
blend = os.path.join(out, name + ".blend")
script = os.path.join(out, "hole.py")
open(script, "w").write(f"""
import bpy, bmesh
bpy.ops.wm.open_mainfile(filepath={blend!r})
o = bpy.data.objects["steel"]
bm = bmesh.new(); bm.from_mesh(o.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[len(bm.faces) // 2]], context="FACES")
bm.to_mesh(o.data); bm.free()
for ob in bpy.data.objects:
    ob.select_set(ob.type == "MESH")
bpy.ops.export_scene.gltf(filepath={os.path.join(out, "holed.glb")!r}, use_selection=True, export_format="GLB")
""")
r = subprocess.run([PY, "-c", "import bpy, runpy; runpy.run_path(%r)" % script], capture_output=True, text=True, timeout=600)
check(os.path.exists(os.path.join(out, "holed.glb")), "a copy with one face cut out of the steel was made")
subprocess.run([PY, os.path.join(LIB, "measure_blender.py"), "--", os.path.join(out, "holed.glb"), os.path.join(out, "mh"), "round", "8"],
               capture_output=True, text=True, timeout=900)
mh = json.load(open(os.path.join(out, "mh", "measure_blender.json")))
check(mh["parts"]["steel"]["open_edges"] >= 3 and mh["parts"]["label"]["open_edges"] == 0,
      f"the cut shows as open edges on the steel only ({mh['parts']['steel']['open_edges']}); the label stays closed")

print(f"ALL {ok} PASS")
