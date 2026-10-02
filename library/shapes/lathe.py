"""Master shape for anything round (battery, can, bottle, jar, cup): built exactly from its real profile.

    blender -b -P lathe.py -- spec.json out_dir [label.png]

The profile is a list of parts (label, steel, cap ...), each a run of (radius, height) points in mm. Each part is
its own smooth strip, so the edges between parts are crisp. The label part gets one clean map: u once around
(0.5 = the front, facing -Y), v from the bottom of the label to its top, in true proportion. Everything else gets
a flat top-down map. Saved as .blend, .glb, .fbx and .usdc at real size (meters)."""
import json
import math
import os
import sys

import bpy
import bmesh

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
spec = json.load(open(argv[0]))
out = argv[1]
label_png = argv[2] if len(argv) > 2 else None
label_mr = argv[3] if len(argv) > 3 else None          # glTF layout: G roughness, B metallic
os.makedirs(out, exist_ok=True)
S = 0.001 if spec.get("units", "mm") == "mm" else 1.0
N = spec.get("segments", 128)

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new(spec["id"])
ob = bpy.data.objects.new(spec["id"], me)
bpy.context.scene.collection.objects.link(ob)
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
parts = list(dict.fromkeys(p["part"] for p in spec["profile"]))
rmax = max(r for p in spec["profile"] for r, z in p["pts"])

lab_pts = [pt for p in spec["profile"] if p["part"] == "label" for pt in p["pts"]]
lab_len = sum(math.dist(lab_pts[i], lab_pts[i + 1]) for i in range(len(lab_pts) - 1)) or 1

def columns(part):
    """The angles a part is built at. A printed sleeve (the label) is a real wrapped film: its last few degrees
    lie OVER its first few, so at the back there is a true overlap - a thin raised layer that ends in a crisp
    step (the seam you see on every real battery and bottle label), and a soft ramp where it climbs over."""
    cols = [(-math.pi + 2 * math.pi * j / N, 0.0, False) for j in range(N + 1)]
    sm = part.get("seam") if isinstance(part.get("seam"), dict) else ({} if part.get("seam") else None)
    if sm is None:
        return cols
    d = math.radians(sm.get("overlap_deg", 6.0))
    ramp = math.radians(sm.get("ramp_deg", 2.0))
    out = []
    for phi, _, _ in cols:
        if -math.pi < phi < -math.pi + d:
            continue
        f = 1.0 if phi <= -math.pi + 1e-9 else 0.0
        if phi > math.pi - ramp:
            x = (phi - (math.pi - ramp)) / ramp
            f = x * x * (3 - 2 * x)
        out.append((phi, f, False))
    k = 1                                                 # the overlap: raised, then the film's edge (a hard step)
    extra = [(-math.pi + d * t / 4, 1.0, False) for t in (1, 2, 3)] + [(-math.pi + d, 1.0, False), (-math.pi + d, 0.0, True)]
    out = out[:k] + extra + out[k:]
    return out


for p in spec["profile"]:
    pts = p["pts"]
    mi = parts.index(p["part"])
    acc = [0.0]
    for i in range(len(pts) - 1):
        acc.append(acc[-1] + math.dist(pts[i], pts[i + 1]))
    cols = columns(p)
    t = (p.get("seam") or {}).get("thickness_mm", 0.08) if isinstance(p.get("seam"), dict) else 0.08
    rings = []
    for (r, z) in pts:
        ring = []
        for phi, f, _ in cols:
            rr = r + (t * f if r > 0 else 0)
            ring.append(bm.verts.new((rr * math.sin(phi) * S, -rr * math.cos(phi) * S, z * S)))
        rings.append(ring)
    for i in range(len(pts) - 1):
        for j in range(len(cols) - 1):
            a, b, c, d = rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]
            if pts[i][0] == 0 and pts[i + 1][0] == 0:
                continue
            try:
                f = bm.faces.new((a, b, c, d) if pts[i + 1][1] >= pts[i][1] or pts[i + 1][0] < pts[i][0] else (a, d, c, b))
            except ValueError:
                continue
            f.material_index = mi
            f.smooth = not cols[j + 1][2]                 # the film's edge stays crisp
            for loop, (jj, ii) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)) if f.verts[1] == b
                                      else ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                phi = cols[jj][0]
                if p["part"] == "label":
                    loop[uvl].uv = ((phi + math.pi) / (2 * math.pi), acc[ii] / lab_len)
                else:
                    r, z = pts[ii]
                    loop[uvl].uv = (0.5 + 0.5 * r / rmax * math.sin(phi), 0.5 - 0.5 * r / rmax * math.cos(phi))

bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.co.xy.length < 1e-9], dist=1e-9)
bm.normal_update()
bm.to_mesh(me)
bm.free()
me.validate()
# faces must point outward: a closed lathe's normals are checked against the axis
for poly in me.polygons:
    c = poly.center
    n = poly.normal
    if (c.x * n.x + c.y * n.y) < -1e-12 and abs(n.z) < 0.9:
        poly.flip()
me.update()
for poly in me.polygons:
    if abs(poly.normal.z) > 0.9:
        if (poly.center.z > 0.5 * max(z for p in spec["profile"] for r, z in p["pts"]) * S) != (poly.normal.z > 0):
            poly.flip()
me.update()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import finish                                            # noqa: E402  surface detail: library/finish.py
import numpy as np                                       # noqa: E402
from PIL import Image                                    # noqa: E402

DEFAULT_FINISH = {"label": "wrap"}


def _img(mt, path, color=False):
    t = mt.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.abspath(path))
    if not color:
        t.image.colorspace_settings.name = "Non-Color"
    t.extension = "REPEAT"
    return t


def _green(mt, tex):
    sep = mt.node_tree.nodes.new("ShaderNodeSeparateColor")
    mt.node_tree.links.new(tex.outputs["Color"], sep.inputs["Color"])
    return sep


fin_dir = os.path.join(out, "finish")
for name in parts:
    m = spec["materials"].get(name, {})
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    L = mt.node_tree.links
    bsdf = mt.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*m.get("color", [0.8, 0.8, 0.8]), 1)
    bsdf.inputs["Metallic"].default_value = m.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = m.get("roughness", 0.5)
    kind = m.get("finish", DEFAULT_FINISH.get(name))
    px = 2048 if name == "label" else 1024              # small parts don't need big maps (keeps the file light)
    kw = {"base_rough": m.get("roughness", 0.4)}
    if kind == "wrap":                                    # a real (built) seam replaces the painted-on one
        kw["seam"] = not any(q.get("seam") for q in spec["profile"] if q["part"] == name)
    maps = finish.make(kind, fin_dir, name, w=px, h=px, **kw) if kind else {}
    if name == "label" and label_png:
        tex = _img(mt, label_png, color=True)
        tex.extension = "EXTEND"
        L.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mr_path = None
    if name == "label" and label_mr:                      # the label's own ink/metal map + the finish's variation
        a = np.asarray(Image.open(label_mr).convert("RGB")).astype(float)
        if maps.get("rough"):
            v = np.asarray(Image.open(maps["rough"]).resize((a.shape[1], a.shape[0])))[..., 1].astype(float)
            a[..., 1] = np.clip(a[..., 1] + (v - 255 * m.get("roughness", 0.4)), 0, 255)
        mr_path = os.path.join(fin_dir, name + "_mr.png")
        Image.fromarray(a.astype(np.uint8)).save(mr_path)
    elif maps.get("rough"):                               # glTF reads metal from the same map's B: put it there
        a = np.asarray(Image.open(maps["rough"]).convert("RGB")).copy()
        a[..., 2] = int(round(255 * m.get("metallic", 0.0)))
        mr_path = os.path.join(fin_dir, name + "_mr.png")
        Image.fromarray(a).save(mr_path)
    if mr_path:
        t2 = _img(mt, mr_path)
        sep = _green(mt, t2)
        L.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if maps.get("normal") and name == "label" and label_mr:  # metal ink on the label: brushed foil sheen
        metal = np.asarray(Image.open(label_mr).convert("RGB"))[..., 2].astype(np.float32) / 255
        if metal.max() > 0.5:
            maps["normal"] = finish.brushed(maps["normal"], metal, os.path.join(fin_dir, name + "_normal_brushed.png"))
    if maps.get("normal"):
        tn = _img(mt, maps["normal"])
        nm = mt.node_tree.nodes.new("ShaderNodeNormalMap")
        L.new(tn.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if maps.get("coat"):                                   # a glossy clear sleeve over the print
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat IOR"].default_value = 1.5
        tc = _img(mt, maps["coat"])
        L.new(_green(mt, tc).outputs["Green"], bsdf.inputs["Coat Roughness"])
    me.materials.append(mt)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, spec["id"] + ".blend"))
bpy.ops.object.select_all(action="DESELECT")
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, spec["id"] + ".glb"), use_selection=True, export_yup=True)
for fmt, call in (("fbx", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=True)),
                  ("usdc", lambda p: bpy.ops.wm.usd_export(filepath=p, selected_objects_only=True))):
    try:
        call(os.path.join(out, spec["id"] + "." + fmt))
    except Exception as e:
        print(f"[lathe] {fmt} export unavailable here: {e}")
print("[lathe]", spec["id"], "verts", len(me.vertices), "faces", len(me.polygons))
