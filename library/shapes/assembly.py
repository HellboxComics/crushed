"""THE GENERAL ONE-OFF BUILDER, PART 2: builds your AI's parts plan (library/parts.py) in Blender.

Mesh first, then the UV map, then the texture map, then the material - for every part:
  rounded_box   a box with rounded edges (bevel); a printed side carries its artwork cut from the photo
  cylinder      along x, y or z; a printed side wraps the front half
  lathe         a profile spun around z
  sheet         a thin panel (a rounded box with one tiny side)
  tube          a bent rod, strap or cable along points
  sphere        a ball, scaled to its size
  organic       a soft or sculpted part lofted from your AI's outlines (ears, tufts, tails, plush bodies), or a
                sculpted .glb when the plan gives one
Each part is its own object with its own material and its physics values (factory/physics.json), at real size.

    python assembly.py -- plan.json out_dir name
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import json
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it provides bmesh)
import bmesh
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
PLAN, OUT, NAME = argv[0], argv[1], argv[2]
S = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = json.load(open(os.path.join(os.path.dirname(HERE), "factory", "physics.json")))
P = json.load(open(PLAN))
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
NORMALS = {"+x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "+y": Vector((0, 1, 0)), "-y": Vector((0, -1, 0)),
           "+z": Vector((0, 0, 1)), "-z": Vector((0, 0, -1))}


sys.path.insert(0, HERE)
import realmat                                              # noqa: E402  every material in its real-world range


def material(name, color, rough, metal, image=None, kind=None):
    if kind:
        color, metal, rough = realmat.fit(kind, color, metal, rough, name)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if image:
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(image)
        t.image.colorspace_settings.name = "sRGB"
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


def print_image(part):
    """The part's artwork, cut from its photo (a crop of the region your AI pointed at)."""
    pr = part.get("print")
    if not pr or not os.path.exists(pr["photo"]):
        return None
    from PIL import Image
    im = Image.open(pr["photo"]).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = pr["box"]
    crop = im.crop((int(x0 * W), int(y0 * H), max(int(x1 * W), int(x0 * W) + 4), max(int(y1 * H), int(y0 * H) + 4)))
    out = os.path.join(OUT, "textures", f"{part['name'].replace(' ', '_')}_print.png")
    crop.save(out)
    return out


def physics(ob, part):
    ob["part"], ob["material_kind"] = part["name"], part["material"]
    for k, v in PHYS.get(part["material"], {}).items():
        ob[k] = v
    ob["inside"] = bool(part.get("inside"))


def side_uv(bm, uv, side):
    """Planar UV for the faces facing `side`, so the artwork fills that side reading the right way."""
    n = NORMALS[side]
    faces = [f for f in bm.faces if f.normal.dot(n) > 0.9]
    if not faces:
        return []
    ax = {"x": 0, "y": 1, "z": 2}
    u_ax, v_ax, flip = {"-y": ("x", "z", False), "+y": ("x", "z", True), "-x": ("y", "z", True),
                        "+x": ("y", "z", False), "+z": ("x", "y", False), "-z": ("x", "y", True)}[side]
    vs = [v.co for f in faces for v in f.verts]
    lo = [min(c[i] for c in vs) for i in range(3)]
    hi = [max(c[i] for c in vs) for i in range(3)]
    for f in faces:
        for loop in f.loops:
            c = loop.vert.co
            u = (c[ax[u_ax]] - lo[ax[u_ax]]) / max(1e-9, hi[ax[u_ax]] - lo[ax[u_ax]])
            v = (c[ax[v_ax]] - lo[ax[v_ax]]) / max(1e-9, hi[ax[v_ax]] - lo[ax[v_ax]])
            loop[uv].uv = (1 - u if flip else u, v)
    return faces


def finish(ob, part, bevel=0.0):
    ob.name = ob.data.name = part["name"]
    base = material(part["name"], part["color"], part["roughness"], part["metallic"], kind=part["material"])
    ob.data.materials.append(base)
    img = print_image(part)
    if img and ob.type == "MESH":
        pm = material(part["name"] + "_print", part["color"], part["roughness"], part["metallic"], img,
                      kind=part["material"])
        ob.data.materials.append(pm)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        uv = bm.loops.layers.uv.verify()
        for f in side_uv(bm, uv, part["print"]["side"]):
            f.material_index = 1
        bm.to_mesh(ob.data)
        bm.free()
    if bevel > 0 and ob.type == "MESH":
        m = ob.modifiers.new("round", "BEVEL")
        m.width, m.segments, m.limit_method = bevel * S, 3, "ANGLE"
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="round")
    ob.rotation_euler = Euler([math.radians(a) for a in part["rotate_deg"]], "XYZ")
    for poly in ob.data.polygons:
        poly.use_smooth = bevel > 0 or part["shape"] in ("cylinder", "lathe", "tube", "sphere", "organic")
    physics(ob, part)
    return ob


def box(part, size, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[c * S for c in part["at_mm"]])
    ob = bpy.context.active_object
    ob.scale = [s * S for s in size]
    bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    for side in NORMALS:                                    # every side gets a clean planar UV map
        side_uv(bm, uv, side)
    bm.to_mesh(ob.data)
    bm.free()
    return finish(ob, part, bevel)


def cylinder(part):
    """size_mm = [diameter, diameter, length]; axis = the direction of its length."""
    r, length = min(part["size_mm"][0], part["size_mm"][1]) / 2, part["size_mm"][2]
    ax = part["axis"]
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r * S, depth=length * S,
                                        location=[c * S for c in part["at_mm"]],
                                        rotation=(0, math.pi / 2, 0) if ax == "x" else
                                        ((math.pi / 2, 0, 0) if ax == "y" else (0, 0, 0)))
    ob = bpy.context.active_object
    bpy.ops.object.transform_apply(rotation=True)
    return finish(ob, part, part["bevel_mm"])


def lathe(part):
    prof = part["profile_mm"]
    bm = bmesh.new()
    seg = 96
    rings = []
    zmid = (min(z for _, z in prof) + max(z for _, z in prof)) / 2        # built around its center, like every part
    for r, z in prof:
        ring = [bm.verts.new((r * S * math.cos(2 * math.pi * k / seg), r * S * math.sin(2 * math.pi * k / seg),
                              (z - zmid) * S)) for k in range(seg)]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if prof[0][0] > 0:
        bm.faces.new(list(reversed(rings[0])))
    if prof[-1][0] > 0:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part["name"])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(part["name"], me)
    bpy.context.collection.objects.link(ob)
    ob.location = [c * S for c in part["at_mm"]]              # at_mm is the part's center; a turn pivots there
    return finish(ob, part)


def tube(part):
    cu = bpy.data.curves.new(part["name"], "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    pts = part["path_mm"]
    sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts):
        p_.co = (q[0] * S, q[1] * S, q[2] * S, 1)
    cu.bevel_depth = part["radius_mm"] * S
    cu.bevel_resolution = 4
    ob = bpy.data.objects.new(part["name"], cu)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.active_object
    part = dict(part, rotate_deg=[0, 0, 0])                 # a tube's points are already where they belong
    return finish(ob, part)


def sphere(part):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.5,
                                         location=[c * S for c in part["at_mm"]])
    ob = bpy.context.active_object
    ob.scale = [s * S for s in part["size_mm"]]
    bpy.ops.object.transform_apply(scale=True)
    return finish(ob, part)


def organic(part):
    mesh = part.get("mesh")
    if mesh and os.path.exists(mesh):                       # a sculpted part from the organic builder
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=mesh)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if new:
            bpy.ops.object.select_all(action="DESELECT")
            for o in new:
                o.select_set(True)
            bpy.context.view_layer.objects.active = new[0]
            if len(new) > 1:
                bpy.ops.object.join()
            ob = bpy.context.active_object
            dims = ob.dimensions
            ob.scale = [part["size_mm"][i] * S / max(dims[i], 1e-9) for i in range(3)]
            bpy.ops.object.transform_apply(scale=True)
            ob.location = [c * S for c in part["at_mm"]]
            return finish(ob, part)
    return form(part)


def _resample(vals, n):
    """A list of outline values spread over n slices (straight lines between the given ones)."""
    vals = [float(v) for v in vals]
    if len(vals) == 1:
        return vals * n
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(vals) - 1)
        j = min(int(t), len(vals) - 2)
        f = t - j
        out.append(vals[j] * (1 - f) + vals[j + 1] * f)
    return out


def form(part, slices=24, around=48):
    """A soft or sculpted part LOFTED from your AI's outlines (read off the photos): elliptical slices from the
    part's bottom to its top, each slice as wide (x) and as deep (y) as the outlines say, its center shifted by the
    lean, the whole smoothed. Ears, tufts, tails, plush bodies, molded faces - never a box stand-in."""
    sx, sy, sz = [float(v) for v in part["size_mm"]]
    fo = part.get("front_outline") or list(EGG)
    so = part.get("side_outline") or fo
    lean = part.get("lean_mm") or []
    fx = _resample(fo, slices)
    fy = _resample(so, slices)
    lx = _resample([q[0] for q in lean], slices) if lean else [0.0] * slices
    ly = _resample([q[1] for q in lean], slices) if lean else [0.0] * slices
    tiny = 0.015
    rxs = [max(max(fx[i], 0.0) * sx / 2, tiny * sx) for i in range(slices)]
    rys = [max(max(fy[i], 0.0) * sy / 2, tiny * sy) for i in range(slices)]
    # the lean must not push the part past its own size: the whole is fitted back into size x / size y
    x0, x1 = min(lx[i] - rxs[i] for i in range(slices)), max(lx[i] + rxs[i] for i in range(slices))
    y0, y1 = min(ly[i] - rys[i] for i in range(slices)), max(ly[i] + rys[i] for i in range(slices))
    kx, ky = sx / max(x1 - x0, 1e-9), sy / max(y1 - y0, 1e-9)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bm = bmesh.new()
    rings = []
    for i in range(slices):
        z = -sz / 2 + sz * i / (slices - 1)
        ox, oy = (lx[i] - cx) * kx, (ly[i] - cy) * ky
        rx, ry = rxs[i] * kx, rys[i] * ky
        if fx[i] * sx / 2 < tiny * sx and fy[i] * sy / 2 < tiny * sy and i in (0, slices - 1):   # a closed end
            rings.append([bm.verts.new((ox * S, oy * S, z * S))])
            continue
        ring = []
        for k in range(around):
            a = 2 * math.pi * k / around
            ring.append(bm.verts.new(((ox + rx * math.cos(a)) * S, (oy + ry * math.sin(a)) * S, z * S)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for k in range(around):
                bm.faces.new((a[0], b[(k + 1) % around], b[k]))
        elif len(b) == 1:
            for k in range(around):
                bm.faces.new((a[k], a[(k + 1) % around], b[0]))
        else:
            for k in range(around):
                bm.faces.new((a[k], a[(k + 1) % around], b[(k + 1) % around], b[k]))
    if len(rings[0]) > 1:                                      # an open end gets a flat cap
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part["name"])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(part["name"], me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    ob.location = [c * S for c in part["at_mm"]]
    sub = ob.modifiers.new("soft", "SUBSURF")
    sub.levels = sub.render_levels = 1
    bpy.ops.object.modifier_apply(modifier="soft")
    ob["lofted_from_outlines"] = True
    return finish(ob, part)


EGG = (0.0, 0.6, 0.9, 1.0, 0.95, 0.75, 0.4, 0.0)


made, flags = [], []
for part in P["parts"]:
    try:
        sh = part["shape"]
        if sh == "rounded_box":
            ob = box(part, part["size_mm"], part["bevel_mm"])
        elif sh == "sheet":
            ob = box(part, part["size_mm"], min(part["bevel_mm"], min(part["size_mm"]) / 2.2))
        elif sh == "cylinder":
            ob = cylinder(part)
        elif sh == "lathe":
            ob = lathe(part)
        elif sh == "tube":
            ob = tube(part)
        elif sh == "sphere":
            ob = sphere(part)
        else:
            ob = organic(part)
        made.append(ob)
    except Exception as e:
        flags.append(f"{part['name']}: could not be built ({e})")
        print(f"[assembly] {part['name']}: {e}", flush=True)
if not made:
    raise SystemExit("[assembly] no part could be built")

json.dump({o.name: {k: o[k] for k in o.keys() if not k.startswith("_")} for o in made},
          open(os.path.join(OUT, "physics.json"), "w"), indent=1, default=str)
json.dump({"parts": len(made), "flags": flags}, open(os.path.join(OUT, "assembly.json"), "w"), indent=1)
sys.path.insert(0, HERE)
import saveall                                              # noqa: E402

saveall.blend(OUT, NAME)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), export_format="GLB", use_selection=True,
                          export_extras=True)
saveall.rest(OUT, NAME, "assembly", extras=("physics.json", "assembly.json"))
print(f"[assembly] {NAME}: {len(made)} parts" + (f"; {len(flags)} flagged" if flags else ""), flush=True)
