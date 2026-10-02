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

for p in spec["profile"]:
    pts = p["pts"]
    mi = parts.index(p["part"])
    acc = [0.0]
    for i in range(len(pts) - 1):
        acc.append(acc[-1] + math.dist(pts[i], pts[i + 1]))
    rings = []
    for (r, z) in pts:
        ring = []
        for j in range(N + 1):                    # one extra column: the map's seam at the back
            phi = -math.pi + 2 * math.pi * (j % N) / N
            ring.append(bm.verts.new((r * math.sin(phi) * S, -r * math.cos(phi) * S, z * S)))
        rings.append(ring)
    for i in range(len(pts) - 1):
        for j in range(N):
            a, b, c, d = rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]
            if pts[i][0] == 0 and pts[i + 1][0] == 0:
                continue
            try:
                f = bm.faces.new((a, b, c, d) if pts[i + 1][1] >= pts[i][1] or pts[i + 1][0] < pts[i][0] else (a, d, c, b))
            except ValueError:
                continue
            f.material_index = mi
            f.smooth = True
            for loop, (jj, ii) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)) if f.verts[1] == b
                                      else ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                if p["part"] == "label":
                    loop[uvl].uv = (jj / N, acc[ii] / lab_len)
                else:
                    r, z = pts[ii]
                    phi = -math.pi + 2 * math.pi * (jj % N) / N
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

for name in parts:
    m = spec["materials"].get(name, {})
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    bsdf = mt.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*m.get("color", [0.8, 0.8, 0.8]), 1)
    bsdf.inputs["Metallic"].default_value = m.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = m.get("roughness", 0.5)
    if name == "label" and label_png:
        tex = mt.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(os.path.abspath(label_png))
        tex.extension = "EXTEND"
        mt.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if label_mr:
            t2 = mt.node_tree.nodes.new("ShaderNodeTexImage")
            t2.image = bpy.data.images.load(os.path.abspath(label_mr))
            t2.image.colorspace_settings.name = "Non-Color"
            t2.extension = "EXTEND"
            sep = mt.node_tree.nodes.new("ShaderNodeSeparateColor")
            mt.node_tree.links.new(t2.outputs["Color"], sep.inputs["Color"])
            mt.node_tree.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            mt.node_tree.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
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
