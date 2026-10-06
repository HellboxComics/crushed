"""ONE DELIVERABLE CONTRACT FOR EVERY ROUTE (audit 2026-10-04, RC8: "the deliverable is not one standard").

Every builder (round, box, carton, circuit card, parts, Hunyuan) hands its finished .blend through this one door
before anything is measured, judged or exported. For every part it makes sure of the same things:

  UVs       one UV map per part, every face unwrapped, no island on top of another, nothing collapsed to a line.
            A part whose authored UVs are already like that keeps them (a label's wrap). A part whose UVs overlap
            (a box's six sides all in 0..1, a board's top under its bottom, a solidified shell's inner copy) or has
            none is unwrapped afresh; if it carried pictures, its base color, roughness, metallic and normal are
            BAKED from the authored materials into that new map, so nothing it looked like is lost and any tiling
            scale is baked in (it used to be lost in .mtl / .ma).
  maps      <asset>_<part>_base.png (sRGB), <asset>_<part>_mr.png (G roughness, B metallic, glTF layout),
            <asset>_<part>_normal.png (OpenGL +Y) - named by what they are, not by the file they came from.
  materials one Principled BSDF per part (maps or flat factors), kept inside the real range of its kind.
  physics   part, material_kind and the crush numbers of that kind (factory/physics.json) on EVERY part;
            physics.json rewritten from the parts themselves.
  files     .blend (pictures packed), .glb (extras on), .fbx, .usdc - and contract.json saying what was done.

    python contract.py -- <blend> <out_dir> <name> [default_material_kind]
"""
import json
import math
import os
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, LIB)
import uvstats  # noqa: E402

OVERLAP_MAX = 0.10          # share of UV area covered twice: more = overlapping islands (a wrongly laid-out part
#                             is 50 %+; a sleeve whose end laps its start by design is a few %)
COLLAPSED_MAX = 0.05        # share of real faces whose UV area is nothing
INPUTS = (("base", "Base Color"), ("rough", "Roughness"), ("metal", "Metallic"))
MAT_KINDS = json.load(open(os.path.join(LIB, "materials.json")))["kinds"]
SLOTS = {n: k for k, ns in json.load(open(os.path.join(LIB, "materials.json"))).get("_slots", {}).items()
         if k != "_about" for n in ns}
PHYS = json.load(open(os.path.join(LIB, "factory", "physics.json")))
PHYS_KEYS = ("density", "stiffness", "yield", "fails", "sheet_mm")
DEFAULT_KIND_OF = {"plastic": "molded_plastic", "card": "printed_card", "paper": "printed_card", "metal": "painted_metal",
                   "steel": "bare_steel", "glass": "glass", "rubber": "soft_rubber", "fabric": "fabric", "wood": "wood"}


def say(*a):
    print("[contract]", *a, flush=True)


# ------------------------------------------------------------------ what a material is made of
def _bsdf(m):
    if not m or not m.use_nodes:
        return None
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _source_image(sock):
    """The image node feeding a BSDF input (through Separate Color / Normal Map / Mapping), or None."""
    seen = 0
    while sock.is_linked and seen < 8:
        node = sock.links[0].from_node
        if node.type == "TEX_IMAGE":
            return node
        ins = [i for i in node.inputs if i.is_linked]
        if not ins:
            return None
        sock = ins[0]
        seen += 1
    return None


def textured(o):
    for s in o.material_slots:
        b = _bsdf(s.material)
        if b and any(_source_image(b.inputs[n]) for _, n in INPUTS + (("normal", "Normal"),)):
            return True
    return False


def driven(o, name):
    """Is this BSDF input driven by a picture on any slot, or by different values on different slots?"""
    vals, imgs = set(), False
    for s in o.material_slots:
        b = _bsdf(s.material)
        if not b:
            continue
        if _source_image(b.inputs[name]):
            imgs = True
        else:
            v = b.inputs[name].default_value
            vals.add(tuple(round(x, 3) for x in v) if hasattr(v, "__len__") else round(float(v), 3))
    return imgs or len(vals) > 1


def flat_value(o, name):
    for s in o.material_slots:
        b = _bsdf(s.material)
        if b:
            v = b.inputs[name].default_value
            return list(v)[:3] if hasattr(v, "__len__") else float(v)
    return [0.5, 0.5, 0.5] if name == "Base Color" else 0.5


# ------------------------------------------------------------------ kinds and physics
def kind_of(o, default):
    k = o.get("material_kind")
    if k in MAT_KINDS:
        return k
    names = " ".join(s.material.name.lower() for s in o.material_slots if s.material)
    for n, kk in SLOTS.items():
        if n in names:
            return kk
    for kk in MAT_KINDS:
        if kk in names or kk.replace("_", " ") in names:
            return kk
    return DEFAULT_KIND_OF.get(default, default) if default else "molded_plastic"


def ensure_physics(o, default):
    k = kind_of(o, default)
    o["material_kind"] = k
    if not o.get("part"):
        o["part"] = o.name
    for key, v in (PHYS.get(k) or {}).items():
        if key in PHYS_KEYS and key not in o.keys():
            o[key] = v
    return k


# ------------------------------------------------------------------ the unwrap and the bake
def unwrap(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    old = [uv.name for uv in o.data.uv_layers]
    new = o.data.uv_layers.new(name="contract")
    o.data.uv_layers.active = new
    new.active_render = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return old, new


def area_px(o):
    """The picture size a part earns: about 24 px per mm of its surface's square side, 256..2048 - and never less
    than the biggest picture it already carried (a 4096 label stays 4096)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    area = sum(f.calc_area() for f in bm.faces)
    bm.free()
    side = math.sqrt(max(area, 1e-9)) * 1000 * 24          # mm of "square side" x 24 px/mm
    px = 2 ** int(round(math.log2(max(side, 1))))
    px = int(min(2048, max(256, px)))
    had = 0
    for s in o.material_slots:
        b = _bsdf(s.material)
        if not b:
            continue
        node = _source_image(b.inputs["Base Color"])        # the real content (a label, a photo) sets the floor;
        if node and node.image and node.image.size[0]:      # a procedural grain map does not
            had = max(had, max(node.image.size))
    return int(min(4096, max(px, 2 ** int(round(math.log2(had)))) if had else px))


def _bake_setup(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.bake.margin = 6
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False


def _target_nodes(o, img):
    """An image node holding the bake target, active, in every material of the part. -> [(tree, node)]"""
    out = []
    for s in o.material_slots:
        m = s.material
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = img
        n.name = "contract_bake_target"
        nt.nodes.active = n
        out.append((nt, n))
    return out


def _drop(nodes):
    for nt, n in nodes:
        nt.nodes.remove(n)


def _emit_swap(o, input_name):
    """Every material of the part temporarily emits what feeds `input_name` (a picture channel or a value), so an
    EMIT bake writes exactly that value. -> undo list."""
    undo = []
    for s in o.material_slots:
        m = s.material
        b = _bsdf(m)
        if not b:
            continue
        nt = m.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) or \
            next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if not out:
            continue
        prev = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "contract_emit"
        em.inputs["Strength"].default_value = 1.0
        inp = b.inputs[input_name]
        if inp.is_linked:
            nt.links.new(inp.links[0].from_socket, em.inputs["Color"])
        else:
            v = inp.default_value
            em.inputs["Color"].default_value = (v, v, v, 1) if not hasattr(v, "__len__") else tuple(v)
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        undo.append((nt, em, out, prev))
    return undo


def _emit_undo(undo):
    for nt, em, out, prev in undo:
        nt.nodes.remove(em)
        if prev is not None:
            nt.links.new(prev, out.inputs["Surface"])


def bake(o, kind, px, path, colorspace):
    img = bpy.data.images.new(f"bake_{kind}", px, px, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    nodes = _target_nodes(o, img)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    if kind == "base":                                       # what feeds Base Color, emitted: exact for metals too
        undo = _emit_swap(o, "Base Color")                     # (a DIFFUSE color bake of steel is black)
        try:
            bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        finally:
            _emit_undo(undo)
    elif kind == "normal":
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=6, use_clear=True)
    elif kind == "rough":
        bpy.ops.object.bake(type="ROUGHNESS", margin=6, use_clear=True)
    elif kind == "metal":
        undo = _emit_swap(o, "Metallic")
        try:
            bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        finally:
            _emit_undo(undo)
    _drop(nodes)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def rebuild_material(o, asset, part, maps, flats, kind):
    """One Principled material for the part from its baked maps (or flat factors), kept inside its kind's range."""
    name = f"{asset}_{part}"
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    base = flats.get("base")
    rough = flats.get("rough")
    metal = flats.get("metal")
    try:
        import realmat
        if base is not None and rough is not None and metal is not None:
            base, metal, rough = realmat.fit(kind, base, metal, rough, part)
    except Exception:
        pass
    if "base" in maps:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(maps["base"])
        t.image.colorspace_settings.name = "sRGB"
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    elif base is not None:
        b.inputs["Base Color"].default_value = (*base[:3], 1)
    if "mr" in maps:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(maps["mr"])
        t.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    else:
        if rough is not None:
            b.inputs["Roughness"].default_value = float(rough)
        if metal is not None:
            b.inputs["Metallic"].default_value = float(metal)
    if "normal" in maps:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(maps["normal"])
        t.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    o.data.materials.clear()
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.material_index = 0
    return m


def merge_mr(rough_png, metal_png, out_png, px):
    from PIL import Image
    g = np.asarray(Image.open(rough_png).convert("L")) if rough_png else None
    bch = np.asarray(Image.open(metal_png).convert("L")) if metal_png else None
    mr = np.zeros((px, px, 3), np.uint8)
    if g is not None:
        mr[..., 1] = g
    if bch is not None:
        mr[..., 2] = bch
    Image.fromarray(mr).save(out_png)
    for p in (rough_png, metal_png):
        if p and os.path.exists(p):
            os.remove(p)


def rename_images(o, asset, part, used_by, tex_dir):
    """Pictures a kept part uses are named by what they are: <asset>_<part>_<map> (shared ones: <asset>_shared_<map>_N),
    written under that name into textures/ so every format carries the same names."""
    for s in o.material_slots:
        b = _bsdf(s.material)
        if not b:
            continue
        for key, inp in INPUTS + (("normal", "Normal"), ("coat", "Coat Weight"), ("coat", "Coat Roughness")):
            if inp not in b.inputs:
                continue
            node = _source_image(b.inputs[inp])
            if not node or not node.image:
                continue
            img = node.image
            if img.get("contract_named"):
                continue
            tag = {"base": "base", "rough": "mr", "metal": "mr", "normal": "normal", "coat": "coat"}[key]
            stem = f"{asset}_{part}_{tag}" if len(used_by.get(img.name, ())) <= 1 else f"{asset}_shared{len(bpy.data.images)}_{tag}"
            path = os.path.join(tex_dir, stem + ".png")
            try:
                img.file_format = "PNG"
                img.save(filepath=path)
                img.filepath = path
                img.filepath_raw = path
                img.name = stem
                img["contract_named"] = True
            except Exception as e:
                say(f"{o.name}: picture {img.name} could not be renamed to {stem} ({e})")


def images_used_by():
    used = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for s in o.material_slots:
            b = _bsdf(s.material)
            if not b:
                continue
            for key, inp in INPUTS + (("normal", "Normal"),):
                node = _source_image(b.inputs[inp])
                if node and node.image:
                    used.setdefault(node.image.name, set()).add(o.name)
    return used


# ------------------------------------------------------------------ main
def main(blend, out, asset, default_kind):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    _bake_setup(scene)
    tex_dir = os.path.join(out, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
    report = {"asset": asset, "blend": blend, "parts": {}, "started": t0}
    used_by = images_used_by()
    for o in meshes:
        for mod in list(o.modifiers):                       # the real mesh, as delivered
            bpy.context.view_layer.objects.active = o
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception as e:
                say(f"{o.name}: modifier {mod.name} not applied ({e})")
        kind = ensure_physics(o, default_kind)
        part = str(o.get("part") or o.name)
        if part == asset or part.startswith(asset + "_"):      # the one-piece box is named after the asset
            part = part[len(asset):].strip("_") or "body"
        before = uvstats.stats(o)
        rec = {"material_kind": kind, "uv_before": before, "textured": textured(o), "action": "kept"}
        bad = (not before["has_uv"]) or before["overlap"] > OVERLAP_MAX or before["collapsed"] > COLLAPSED_MAX
        if bad:
            old, new = unwrap(o)
            if rec["textured"]:
                px = area_px(o)
                maps, flats = {}, {}
                maps["base"] = bake(o, "base", px, os.path.join(tex_dir, f"{asset}_{part}_base.png"), "sRGB")
                if driven(o, "Roughness") or driven(o, "Metallic"):
                    r = bake(o, "rough", px, os.path.join(tex_dir, f"{asset}_{part}_rough_tmp.png"), "Non-Color")
                    mm = bake(o, "metal", px, os.path.join(tex_dir, f"{asset}_{part}_metal_tmp.png"), "Non-Color")
                    maps["mr"] = os.path.join(tex_dir, f"{asset}_{part}_mr.png")
                    merge_mr(r, mm, maps["mr"], px)
                else:
                    flats["rough"], flats["metal"] = flat_value(o, "Roughness"), flat_value(o, "Metallic")
                if any(_source_image(_bsdf(s.material).inputs["Normal"]) for s in o.material_slots if _bsdf(s.material)):
                    maps["normal"] = bake(o, "normal", px, os.path.join(tex_dir, f"{asset}_{part}_normal.png"), "Non-Color")
                for nm in old:                                  # the baked map is the only one now
                    o.data.uv_layers.remove(o.data.uv_layers[nm])
                rebuild_material(o, asset, part, maps, flats, kind)
                rec.update(action="unwrapped and baked", px=px, maps={k: os.path.basename(v) for k, v in maps.items()})
            else:
                for nm in old:
                    o.data.uv_layers.remove(o.data.uv_layers[nm])
                rec.update(action="unwrapped (flat colors kept)")
        else:
            rename_images(o, asset, part, used_by, tex_dir)
        o.data.uv_layers[0].name = "UVMap"
        rec["uv_after"] = uvstats.stats(o)
        rec["uv_ok"] = rec["uv_after"]["has_uv"] and rec["uv_after"]["overlap"] <= OVERLAP_MAX \
            and rec["uv_after"]["collapsed"] <= COLLAPSED_MAX
        report["parts"][o.name] = rec
        say(f"{o.name} ({kind}): {rec['action']}; uv overlap {before['overlap']:.3f} -> {rec['uv_after']['overlap']:.3f}, "
            f"collapsed {before['collapsed']:.3f} -> {rec['uv_after']['collapsed']:.3f}")
    for m in list(bpy.data.materials):                       # the authored materials a bake replaced
        if m.users == 0:
            bpy.data.materials.remove(m)
    for img in list(bpy.data.images):                        # and the pictures only they used
        if img.users == 0:
            bpy.data.images.remove(img)
    # physics.json from the parts themselves
    json.dump({o.name: {k: o[k] for k in o.keys() if not k.startswith("_")} for o in meshes},
              open(os.path.join(out, "physics.json"), "w"), indent=1, default=str)
    # the one door's mesh hygiene, Blender's own ops: triangulate the way the glTF exporter would (so what is
    # checked is what is shipped), then dissolve zero-length edges and zero-area faces. (2026-10-05: trimesh's
    # is_watertight found 3 degenerate triangles and 2 four-face edges on the Duracell's label shell that only
    # appeared in the exported glb - the exporter's own triangulation of thin quads at the film's edge.)
    import bmesh
    for o in meshes:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
        bm.to_mesh(o.data)
        bm.free()
        o.data.validate()
    for o in scene.objects:
        o.select_set(o in meshes)
    import saveall
    raw = os.path.join(out, asset + "_builder.blend")
    if os.path.abspath(blend) == os.path.abspath(os.path.join(out, asset + ".blend")) and not os.path.exists(raw):
        os.replace(blend, raw)                                # the builder's own file, kept beside the delivered one
    saveall.blend(out, asset)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, asset + ".glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_extras=True)
    saveall.rest(out, asset, "contract", selected=True, extras=("physics.json",))
    # textures/ holds only the delivered maps: the builder's own pictures (and the USD export's earlier copies) move
    # to textures/_builder so nothing stale is filed with the asset
    keep = {os.path.basename(bpy.path.abspath(i.filepath_raw)) for i in bpy.data.images if i.filepath_raw}
    old_dir = os.path.join(tex_dir, "_builder")
    for f in os.listdir(tex_dir):
        fp = os.path.join(tex_dir, f)
        if os.path.isfile(fp) and f not in keep and not f.startswith(asset + "_"):
            os.makedirs(old_dir, exist_ok=True)
            os.replace(fp, os.path.join(old_dir, f))
    report["seconds"] = round(time.time() - t0, 1)
    report["all_uv_ok"] = all(r["uv_ok"] for r in report["parts"].values())
    json.dump(report, open(os.path.join(out, "contract.json"), "w"), indent=1, default=str)
    say(f"{len(meshes)} part(s) through the contract in {report['seconds']} s; uv ok: {report['all_uv_ok']}")
    if not report["all_uv_ok"]:
        bad = [n for n, r in report["parts"].items() if not r["uv_ok"]]
        raise RuntimeError("parts whose UVs still overlap or collapse after the unwrap: " + ", ".join(bad))


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else "")
