"""MEASURING THE BUILT MODEL (run in Blender by library/measure.py - never on its own):
  1. its real size (meters), part by part and overall
  2. every part's material: base color, metallic, roughness (factors, or the average of the texture maps)
  3. mesh health per part: faces pointing inward, holes (open edges), degenerate faces
  4. INSIDE FIT: thousands of rays shot at the model from every direction, like eyes looking at it; any ray whose
     first hit is an inside part means that inside part shows through the outside (a steel can poking out past a
     battery label, a pastry through its foil)
  5. one picture of each side, flat-lit and straight on (orthographic), at a set number of pixels per mm - so the
     printed words and the barcode can be read off the model itself, UV map and all

    PY measure_blender.py -- model.glb out_dir route px_per_mm
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.abspath(__file__)))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import json
import math
import os
import sys

import bpy  # noqa: I001
import bmesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes"))
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT, ROUTE, PXMM = argv[0], argv[1], argv[2], float(argv[3])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
res = {"parts": {}, "overall": {}, "inside_fit": {}, "renders": {}}


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


lo, hi = world_bbox(meshes)
sized = [o for o in meshes if not o.get("beyond_size")] or meshes   # attached hardware (a card's bracket) aside
slo, shi = world_bbox(sized)
res["overall"] = {"size_m": [round(shi[i] - slo[i], 5) for i in range(3)], "parts": len(meshes),
                  "left_out_of_size": [o.name for o in meshes if o.get("beyond_size")]}


def img_mean(node, mask=None):
    """Average of a texture map's channels (0..1) over the texels the part's UVs cover (mask: uvstats.coverage),
    else over the whole map. Sampled on a grid so big maps stay fast."""
    img = getattr(node, "image", None)
    if not img or not img.size[0]:
        return None
    px = np.array(img.pixels[:], dtype=np.float32)
    if not px.size:
        return None
    px = px.reshape(img.size[1], img.size[0], img.channels)[::-1]      # Blender stores rows bottom-up; the mask is a picture
    step = max(1, int(max(img.size) / 256))
    sub = px[::step, ::step, :3]
    if mask is not None:
        from PIL import Image
        m = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((sub.shape[1], sub.shape[0]), Image.NEAREST)) > 0
        if m.sum() >= 16:                                                # enough covered texels to mean something
            return [float(x) for x in sub[m].reshape(-1, 3).mean(0)]
    return [float(x) for x in sub.reshape(-1, 3).mean(0)]


def follow(sock):
    """The image node feeding a material input (through separate/normal-map nodes), if any."""
    if not sock.is_linked:
        return None, None
    link = sock.links[0]
    n, out = link.from_node, link.from_socket.name
    seen = 0
    while n.type != "TEX_IMAGE" and seen < 6:
        ins = [i for i in n.inputs if i.is_linked]
        if not ins:
            return None, None
        out = ins[0].links[0].from_socket.name
        n = ins[0].links[0].from_node
        seen += 1
    return (n, out) if n.type == "TEX_IMAGE" else (None, None)


for o in meshes:
    me = o.data
    info = {"material_kind": o.get("material_kind", ""), "inside": bool(o.get("inside", False)),
            "verts": len(me.vertices), "faces": len(me.polygons)}
    plo, phi = world_bbox([o])
    info["size_m"] = [round(phi[i] - plo[i], 5) for i in range(3)]
    mats = []
    try:
        import uvstats
        cover = uvstats.coverage(o)
    except Exception:
        cover = None
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes:
            continue
        p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not p:
            continue
        d = {"name": m.name}
        for key, inp in (("base", "Base Color"), ("metallic", "Metallic"), ("roughness", "Roughness")):
            s = p.inputs[inp]
            node, chan = follow(s)
            if node is not None:
                mean = img_mean(node, cover)
                if mean is None:
                    continue
                if key == "base":
                    d[key] = mean
                else:                                       # glTF: metallic = blue, roughness = green
                    d[key] = mean[2] if key == "metallic" else mean[1]
                    d[key + "_from"] = "map"
            else:
                v = s.default_value
                d[key] = list(v)[:3] if key == "base" else float(v)
        mats.append(d)
    info["materials"] = mats
    # mesh health
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(o.matrix_world)
    # a glb stores a vertex once per UV seam / sharp edge it sits on, so a closed can comes back as thousands of
    # one-face edges (2026-10-05: steel 3268 "holes" on a watertight part). Join what the export split (a hair
    # apart, 0.001 mm), then count: a real hole stays open, a seam does not.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    degen = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    vol = bm.calc_volume(signed=True) if open_edges == 0 else None
    info.update({"open_edges": open_edges, "non_manifold_edges": nonman, "degenerate_faces": degen,
                 "edges": len(bm.edges), "signed_volume_mm3": round(vol * 1e9, 3) if vol is not None else None})
    try:
        import uvstats                                      # library/shapes/uvstats.py (the contract's own measure)
        info["uv"] = uvstats.stats(o)
    except Exception as e:
        info["uv"] = {"has_uv": bool(me.uv_layers), "error": str(e)[:200]}
    # spikes: vertices far outside the part's own bulk (a welded seam gone wrong)
    co = np.array([v.co[:] for v in bm.verts]) if bm.verts else np.zeros((0, 3))
    if len(co) > 20:
        med = np.median(co, 0)
        dist = np.linalg.norm(co - med, axis=1)
        q = np.percentile(dist, 99)
        info["spikes"] = int((dist > q * 1.6 + 1e-4).sum())
    bm.free()
    res["parts"][o.name] = info

# INSIDE FIT: rays from all around; a ray whose FIRST hit is an inside part = that part shows through
inside = {o.name for o in meshes if o.get("inside")}
if inside:
    dg = bpy.context.evaluated_depsgraph_get()
    center = (lo + hi) / 2
    radius = (hi - lo).length * 0.75 + 0.01
    rng = np.random.default_rng(1)
    n = 6000
    dirs = rng.normal(size=(n, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    targets = np.array(lo[:]) + rng.random((n, 3)) * np.array((hi - lo)[:])
    hits, seen = {}, 0
    for dvec, t in zip(dirs, targets):
        origin = Vector(t) + Vector(dvec) * radius
        ok, loc, nor, idx, ob, mat = scene.ray_cast(dg, origin, -Vector(dvec), distance=radius * 2.5)
        if not ok:
            continue
        seen += 1
        if ob and ob.name in inside:
            hits[ob.name] = hits.get(ob.name, 0) + 1
    res["inside_fit"] = {"rays_hitting": seen, "inside_parts": sorted(inside),
                         "showing_through": {k: round(v / max(seen, 1), 5) for k, v in hits.items()}}
else:
    res["inside_fit"] = {"rays_hitting": 0, "inside_parts": [], "showing_through": {}}

# TWO STRAIGHT-ON PICTURES OF EACH SIDE
# 1. LIT, with the real materials and a soft studio light: what the judge compares with the real photo - a bare steel
#    end with its raised button, a brushed copper band, a glossy sleeve. (2026-10-03: the judge was shown the unlit
#    picture, saw a flat gray disc where the + button is, and failed every Duracell for "no raised button".)
# 2. UNLIT: every material shows exactly its printed color (an emission of its base color or base-color map), so the
#    exact checks read what is PRINTED, not the lighting. Opaque: a map's alpha never makes a label see-through.
def _studio():
    import math
    # a key, a fill, a back light, and two low raking lights (one from each end) that throw the shadow that shows a
    # raised button or a pressed ring on an end seen straight-on
    # (no light sits straight above or below: a polished end would mirror it into the end-on camera and wash out)
    for loc, e, sz in (((0.45, -0.45, 0.22), 22, 0.5), ((-0.5, -0.2, 0.15), 12, 0.6), ((0.2, 0.5, 0.18), 14, 0.6),
                       ((0.55, 0.1, 0.06), 12, 0.25), ((-0.5, -0.1, -0.06), 12, 0.25)):
        L = bpy.data.lights.new("studio", "AREA")
        L.energy, L.size = e, sz
        o = bpy.data.objects.new("studio", L)
        scene.collection.objects.link(o)
        o.location = c + Vector(loc) * max(size.length * 6, 0.6) / 0.6
        o.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        yield o


def _unlit():
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        nt = m.node_tree
        p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        outn = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if not p or not outn:
            continue
        em = nt.nodes.new("ShaderNodeEmission")
        bc = p.inputs["Base Color"]
        if bc.is_linked:
            nt.links.new(bc.links[0].from_socket, em.inputs["Color"])
        else:
            em.inputs["Color"].default_value = bc.default_value
        nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
        try:
            m.blend_method = "OPAQUE"
        except Exception:
            pass
scene.render.engine = "CYCLES"
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False
if not scene.world:
    scene.world = bpy.data.worlds.new("w")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (1.0, 0.0, 1.0, 1)     # magenta: never a real print color, easy to mask out
    bg.inputs["Strength"].default_value = 1.0
size = hi - lo
c = (lo + hi) / 2
VIEWS = {   # side: (camera direction from the center, width axis, height axis)
    "front": (Vector((0, -1, 0)), 0, 2), "back": (Vector((0, 1, 0)), 0, 2), "left": (Vector((-1, 0, 0)), 1, 2),
    "right": (Vector((1, 0, 0)), 1, 2), "top": (Vector((0, 0, 1)), 0, 1), "bottom": (Vector((0, 0, -1)), 0, 1)}
if ROUTE == "round":
    sides = {"label_0": (Vector((0, -1, 0)), 0, 2), "label_90": (Vector((1, 0, 0)), 1, 2),
             "label_180": (Vector((0, 1, 0)), 0, 2), "label_270": (Vector((-1, 0, 0)), 1, 2),
             "top": VIEWS["top"], "bottom": VIEWS["bottom"]}
elif ROUTE == "flat":
    sides = {k: VIEWS[k] for k in ("front", "back")}
elif ROUTE == "pcb":
    sides = {"top": VIEWS["top"], "bottom": VIEWS["bottom"]}   # a board lies flat: its faces point up and down
else:
    sides = VIEWS
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
def _aim(d, wa, ha):
    w_m, h_m = size[wa], size[ha]
    cam_data.ortho_scale = max(w_m, h_m) * 1.04
    dist = size.length + 0.05
    cam.location = c + d * dist
    f = (-d).normalized()                                   # the camera looks at the center; picture-up is
    u = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))   # world up for sides, the back for top/bottom
    r = f.cross(u).normalized()
    up = r.cross(f).normalized()
    from mathutils import Matrix
    cam.rotation_euler = Matrix((r, up, -f)).transposed().to_euler()
    cam_data.clip_start = 0.0005                            # never clip the near side of a small object
    cam_data.clip_end = dist * 3
    return w_m, h_m


res["renders_lit"] = {}
lights = list(_studio())                                    # 1. lit, real materials (the judge's pictures)
if bg:                                                      # a soft gray studio: metal reflects it, not magenta
    bg.inputs["Color"].default_value = (0.45, 0.45, 0.47, 1)
    bg.inputs["Strength"].default_value = 0.6
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
for name, (d, wa, ha) in sides.items():
    w_m, h_m = _aim(d, wa, ha)
    px = min(1536, max(512, int(max(w_m, h_m) * 1000 * PXMM)))
    scene.render.resolution_x = scene.render.resolution_y = px
    p = os.path.join(OUT, f"{name}_lit.png")
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    res["renders_lit"][name] = {"file": p, "px": px, "size_mm": [round(w_m * 1000, 1), round(h_m * 1000, 1)]}
for o in lights:
    bpy.data.objects.remove(o)
if bg:
    bg.inputs["Color"].default_value = (1.0, 0.0, 1.0, 1)
    bg.inputs["Strength"].default_value = 1.0
_unlit()                                                    # 2. unlit, the print only (the exact checks' pictures)
scene.cycles.samples = 8
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0
for name, (d, wa, ha) in sides.items():
    w_m, h_m = _aim(d, wa, ha)
    px = min(4096, max(256, int(max(w_m, h_m) * 1000 * PXMM)))
    scene.render.resolution_x = scene.render.resolution_y = px
    p = os.path.join(OUT, f"{name}.png")
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    res["renders"][name] = {"file": p, "px": px, "px_per_mm": round(px / (max(w_m, h_m) * 1000 * 1.04), 2),
                            "size_mm": [round(w_m * 1000, 1), round(h_m * 1000, 1)]}
json.dump(res, open(os.path.join(OUT, "measure_blender.json"), "w"), indent=1)
print("MEASURED", os.path.join(OUT, "measure_blender.json"))
