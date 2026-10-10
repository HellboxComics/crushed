"""Master shape for anything round (battery, can, bottle, jar, cup): built exactly from its real profile.

    blender -b -P lathe.py -- spec.json out_dir [label.png]

The profile is a list of parts (label, steel, cap ...), each a run of (radius, height) points in mm. Each part is
its own smooth strip, so the edges between parts are crisp. The label part gets one clean map: u once around
(0.5 = the front, facing -Y), v from the bottom of the label to its top, in true proportion. Everything else gets
a flat top-down map. Saved as .blend, .glb, .fbx and .usdc at real size (meters)."""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
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


def _area(profile):
    """The whole outline's signed area in (radius, height), closed along the axis: above 0 when it walks the usual
    way (bottom center -> out -> up the side -> top center)."""
    pts = [pt for p in profile for pt in p["pts"]]
    return sum(r0 * z1 - r1 * z0 for (r0, z0), (r1, z1) in zip(pts, pts[1:] + pts[:1])) / 2


# Which way each face points comes from the direction the outline walks - the outside is always on the same hand
# of it - never from guessing face by face. (2026-10-03: a guess by height and slope turned the small pressed groove
# on an AAA's end inside out, and giving the steel its thickness then threw spikes 100 mm out of the battery.)
USUAL = _area(spec["profile"]) >= 0
WRAPS = []
for p in spec["profile"]:
    pts = p["pts"]
    mi = parts.index(p["part"])
    acc = [0.0]
    for i in range(len(pts) - 1):
        acc.append(acc[-1] + math.dist(pts[i], pts[i + 1]))
    cols = columns(p)
    t = (p.get("seam") or {}).get("thickness_mm", 0.08) if isinstance(p.get("seam"), dict) else 0.08
    rings = []
    for k_, (r, z) in enumerate(pts):
        # the overlap's extra thickness follows the surface: full on the straight side, fading to nothing where the
        # sleeve curls over a shoulder or lip (pushing it straight out there cut a notch into the end)
        a, b = pts[max(k_ - 1, 0)], pts[min(k_ + 1, len(pts) - 1)]
        dz, dr = abs(b[1] - a[1]), abs(b[0] - a[0])
        upright = (dz / max(math.hypot(dz, dr), 1e-9)) ** 4 if (dz or dr) else 0.0
        ring = []
        for phi, f, _ in cols:
            rr = r + (t * f * upright if r > 0 else 0)
            ring.append(bm.verts.new((rr * math.sin(phi) * S, -rr * math.cos(phi) * S, z * S)))
        rings.append(ring)
    WRAPS.append(rings)
    for i in range(len(pts) - 1):
        for j in range(len(cols) - 1):
            a, b, c, d = rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]
            if pts[i][0] == 0 and pts[i + 1][0] == 0:
                continue
            try:
                f = bm.faces.new((a, b, c, d) if USUAL else (a, d, c, b))
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
# the wrap's start and end columns sit at the same spot: one vertex, so the shading runs smooth across it (two
# vertices there made a hard line - "a seam cut into the metal"). UVs are per corner, so the label's map still wraps.
# Only those pairs, only inside each part (welding everything joined separate parts and made spikes).
tm = {}
for rings_ in WRAPS:
    for ring in rings_:
        if len(ring) > 1 and ring[-1].is_valid and ring[0].is_valid and (ring[-1].co - ring[0].co).length < 1e-9:
            tm[ring[-1]] = ring[0]
if tm:
    bmesh.ops.weld_verts(bm, targetmap=tm)
# where a ring sits ON the axis (the pole of a cap) a quad has two corners in one place: after the welds those are
# zero-length edges and zero-area faces. Blender's own dissolve_degenerate removes them (2026-10-05: trimesh's
# is_watertight found 192 of them and 96 edges shared by six faces on the can wall; a print check would too).
bmesh.ops.dissolve_degenerate(bm, dist=1e-9, edges=bm.edges[:])
bm.normal_update()
bm.to_mesh(me)
bm.free()
me.validate()
# the check on the whole: the outside encloses a positive volume only when every face points out
vol = 0.0
for poly in me.polygons:
    vs = [me.vertices[i].co for i in poly.vertices]
    for k in range(1, len(vs) - 1):
        vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6
if vol < 0:
    print("[lathe] the outline walks the other way round - every face turned to point out")
    for poly in me.polygons:
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
    mkind = m.get("kind") or ("printed_plastic_sleeve" if name == "label" else "bare_steel" if name == "steel" else
                              "molded_plastic")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import realmat                                       # every material inside its real-world range
    col, met, rou = realmat.fit(mkind, m.get("color", [0.8, 0.8, 0.8]), m.get("metallic", 0.0),
                                m.get("roughness", 0.5), name) if name != "label" else \
        (m.get("color", [0.8, 0.8, 0.8]), m.get("metallic", 0.0), m.get("roughness", 0.5))
    m = dict(m, color=col, metallic=met, roughness=rou)
    bsdf.inputs["Base Color"].default_value = (*col, 1)
    bsdf.inputs["Metallic"].default_value = met
    bsdf.inputs["Roughness"].default_value = rou
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
            maps["normal"] = finish.brushed(maps["normal"], metal, os.path.join(fin_dir, name + "_normal_brushed.png"),
                                            strength=0.015)  # printed metal ink is near smooth: at 0.05 the copper
            #                                                  top read as brushed rings (judge + real photos, 2026-10-10)
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

# ---------------------------------------------------------------- built like the factory makes it (factory/recipes)
# Every part is its own solid object with real thickness, its own material, and how it behaves when crushed
# (density, stiffness, yield, how it fails) saved on it - so a crush bends steel like steel, tears the sleeve,
# crumbles the cathode and lets the gel ooze, and the right things are inside when it splits open.
HERE_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHYS = json.load(open(os.path.join(HERE_LIB, "factory", "physics.json")))
recipe = spec.get("recipe_inline") or {}
if spec.get("recipe") and not recipe:
    rp = os.path.join(HERE_LIB, "factory", "recipes", spec["recipe"] + ".json")
    recipe = json.load(open(rp)) if os.path.exists(rp) else {}
ref = recipe.get("reference_size_mm") or {}
rmax_mm = max(r for p in spec["profile"] for r, z in p["pts"])
zmax_mm = max(z for p in spec["profile"] for r, z in p["pts"])
SR = (2 * rmax_mm / ref["diameter"]) if ref.get("diameter") else 1.0      # one recipe, scaled to this size
SZ = (zmax_mm / ref["height"]) if ref.get("height") else 1.0


def physics(ob, kind, part):
    ph = PHYS.get(kind, {})
    ob["part"] = part
    ob["material_kind"] = kind
    for k in ("density", "stiffness", "yield", "fails", "sheet_mm"):
        if k in ph:
            ob[k] = ph[k]
    ob["physics_from"] = json.dumps(ph.get("from", "handbook"))   # where each number comes from (a record, as text:
    #                                                               Blender makes a nested dict an IDPropertyGroup)


bpy.ops.object.select_all(action="DESELECT")
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="MATERIAL")                   # one object per outside part
bpy.ops.object.mode_set(mode="OBJECT")
outside = recipe.get("outside") or {}
shell = recipe.get("shell_mm") or {}
parts_out = []
for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    name = o.data.materials[0].name if o.data.materials else "part"
    o.name = o.data.name = name
    kind = outside.get(name) or spec["materials"].get(name, {}).get("kind") or \
        ("printed_plastic_sleeve" if name == "label" else "bare_steel" if name == "steel" else "molded_plastic")
    t = shell.get(name) or PHYS.get(kind, {}).get("sheet_mm")
    if t:                                                # a real wall: the surface given its true thickness inward
        m = o.modifiers.new("thickness", "SOLIDIFY")
        m.thickness = t * S
        m.offset = -1
        m.use_rim = True
        m.use_even_offset = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="thickness")
    physics(o, kind, name)
    parts_out.append(o)


_ENV = [(a[0], a[1], b[0], b[1]) for p in spec["profile"] for a, b in zip(p["pts"], p["pts"][1:])]
_ZLO = min(min(e[1], e[3]) for e in _ENV)
_ZHI = max(max(e[1], e[3]) for e in _ENV)
_SKIN = max([PHYS.get(spec["materials"].get(p["part"], {}).get("kind", ""), {}).get("sheet_mm", 0) or 0
             for p in spec["profile"]] + [0.11]) + 0.05


def outer_r(z):
    """How far out the OUTSIDE reaches at height z (mm) - the inside of the item must stay within it."""
    best = 0.0
    for r0, z0, r1, z1 in _ENV:
        if min(z0, z1) - 1e-9 <= z <= max(z0, z1) + 1e-9:
            best = max(best, max(r0, r1) if abs(z1 - z0) < 1e-9 else r0 + (r1 - r0) * (z - z0) / (z1 - z0))
    return best


def fit_inside(poly):
    """THE INSIDE-FIT RULE (every round item): an inside part never reaches past the outside. Its outline is cut into
    0.25 mm steps and every point is kept inside the outer shell (less the shell's own thickness) - so a can wall
    follows the shoulder in under the label instead of poking out past it."""
    pts = []
    for (r0, z0), (r1, z1) in zip(poly, poly[1:] + poly[:1]):
        n = max(1, int(math.hypot(r1 - r0, z1 - z0) / 0.25))
        pts += [(r0 + (r1 - r0) * k / n, z0 + (z1 - z0) * k / n) for k in range(n)]
    out, moved = [], 0.0
    for r, z in pts:
        z2 = min(max(z, _ZLO + _SKIN), _ZHI - _SKIN)
        r2 = min(r, max(outer_r(z2) - _SKIN, 0.0))
        moved = max(moved, r - r2, abs(z - z2))
        out.append([r2, z2])
    return out, moved


def revolve(name, poly, segs=96):
    """A closed outline in (radius, height) mm spun into a watertight solid."""
    bm = bmesh.new()
    rings = []
    poly, moved = fit_inside([[r * SR, z * SZ] for r, z in poly])
    if moved > 0.01:
        print(f"[lathe] {name}: kept inside the outer shell (moved in up to {moved:.2f} mm)")
    for r, z in poly:
        if r <= 1e-9:
            rings.append([bm.verts.new((0, 0, z * S))])
        else:
            rings.append([bm.verts.new((r * math.sin(2 * math.pi * j / segs) * S, -r * math.cos(2 * math.pi * j / segs) * S,
                                        z * S)) for j in range(segs)])
    n = len(rings)
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        if len(a) == 1 and len(b) == 1:
            continue
        for j in range(segs):
            try:
                if len(a) == 1:
                    bm.faces.new((a[0], b[(j + 1) % segs], b[j]))
                elif len(b) == 1:
                    bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
                else:
                    bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
            except ValueError:
                pass
    bmesh.ops.dissolve_degenerate(bm, dist=1e-9, edges=bm.edges[:])      # (poles: zero-area faces, see above)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me2 = bpy.data.meshes.new(name)
    bm.to_mesh(me2)
    bm.free()
    for f in me2.polygons:
        f.use_smooth = True
    o2 = bpy.data.objects.new(name, me2)
    bpy.context.scene.collection.objects.link(o2)
    return o2


def relative_poly(q):
    """A recipe part described against the outside (wall / fill / core) turned into an outline at this item's size."""
    side = [pt for p in spec["profile"] if p["part"] == "label" for pt in p["pts"]] or \
        max((p["pts"] for p in spec["profile"]), key=len)
    side = sorted(side, key=lambda pt: pt[1])
    z0, z1 = side[0][1], side[-1][1]
    shape = q.get("shape")
    if shape == "wall":
        t = max(q.get("thickness_mm") or 0.2, 0.05)
        out = [[max(r - 0.1, 0.01), z] for r, z in side]
        return out + [[max(r - t, 0.0), z] for r, z in reversed(out)]
    if shape == "fill":
        top = z0 + (z1 - z0) * min(max(q.get("fraction") or 0.9, 0.05), 0.99)
        pts = [[max(r - 0.4, 0.01), z] for r, z in side if z <= top]
        above = [pt for pt in side if pt[1] > top]
        if pts and above:                                 # the liquid's surface, exactly at its height
            (ra, za), (rb, zb) = [pts[-1][0] + 0.4, pts[-1][1]], above[0]
            k = (top - za) / max(zb - za, 1e-9)
            pts.append([max(ra + (rb - ra) * k - 0.4, 0.01), top])
        return [[0.0, pts[0][1]]] + pts + [[0.0, pts[-1][1]]] if len(pts) > 1 else None
    if shape == "core":
        rr = max(r for r, z in side) * min(max(q.get("radius_fraction") or 0.3, 0.02), 0.95)
        return [[0.0, z0 + 0.5], [rr, z0 + 0.5], [rr, z1 - 0.5], [0.0, z1 - 0.5]]
    return None


for q in recipe.get("inside", []):
    if "poly" not in q:                                   # a researched recipe: parts relative to the outside
        if not ref:
            poly = relative_poly(q)
            if not poly:
                continue
            q = dict(q, poly=poly)
        else:
            continue
    polys = [q["poly"]]
    if q["part"] == "cathode" and recipe.get("cathode_pellets", 1) > 1:       # pressed as separate pellets
        (r0, z0), (r1, _), (_, z1), _ = q["poly"]
        k = recipe["cathode_pellets"]
        hz = (z1 - z0) / k
        polys = [[[r0, z0 + i * hz + 0.05], [r1, z0 + i * hz + 0.05], [r1, z0 + (i + 1) * hz - 0.05],
                  [r0, z0 + (i + 1) * hz - 0.05]] for i in range(k)]
    for i, poly in enumerate(polys):
        nm = q["part"] + (f"_{i + 1}" if len(polys) > 1 else "")
        o2 = revolve(nm, poly)
        mt2 = bpy.data.materials.new(nm)
        mt2.use_nodes = True
        b2 = mt2.node_tree.nodes["Principled BSDF"]
        import realmat                                   # inside parts too: real-world material values
        c2, m2, r2 = realmat.fit(q.get("kind", "molded_plastic"), q.get("color", [0.5, 0.5, 0.5]),
                                 q.get("metallic", 0.0), q.get("roughness", 0.5), nm)
        b2.inputs["Base Color"].default_value = (*c2, 1)
        b2.inputs["Metallic"].default_value = m2
        b2.inputs["Roughness"].default_value = r2
        o2.data.materials.append(mt2)
        physics(o2, q.get("kind", "molded_plastic"), q["part"])
        o2["inside"] = True                              # an inside part: it must never show through the outside
        parts_out.append(o2)

json.dump({o.name: {k: o[k] for k in o.keys() if not k.startswith("_")} for o in parts_out},
          open(os.path.join(out, "physics.json"), "w"), indent=1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saveall                                           # noqa: E402  library/shapes/saveall.py

saveall.blend(out, spec["id"])                           # every picture packed inside the .blend: it opens anywhere
bpy.ops.object.select_all(action="DESELECT")
for o in parts_out:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts_out[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(out, spec["id"] + ".glb"), use_selection=True, export_yup=True,
                          export_extras=True)            # each part's physics travels inside the .glb too
saveall.rest(out, spec["id"], "lathe", extras=("physics.json",))   # .fbx (pictures inside) + .usdc + made.json
print("[lathe]", spec["id"], "parts", ", ".join(o.name for o in parts_out))
