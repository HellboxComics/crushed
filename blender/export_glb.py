"""Export a block as a 3D object (GLB) you can spin on OpenSea: `animation_url` pointing at the .glb.

    python3 blender/export_glb.py --token 44 --out renders/glb --size 2048

The block's materials are procedural shader graphs, which no 3D viewer can show. So every surface is baked
into textures: its own color (with the crevices darkened, so the crush keeps its depth) and how shiny it is.
The viewer lights it live, so it turns like a real object. The straps, tape, wires, goo and droplets are baked in with it;
the floor is left out. The bake is the slow part (GPU strongly recommended).
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from crushed import build, stage  # noqa: E402
import generate  # noqa: E402


def cull_hidden(ob):
    """Delete every face nobody can see from outside. A crushed block is layers on layers pressed into the same
    few millimeters; a game-style viewer draws those as flicker (two surfaces fighting for the same pixel).
    A face stays only if a ray from it escapes the block in at least one of a few directions around its normal."""
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    keep = bm.faces.layers.int.get("keep")
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    dead = []
    for f in bm.faces:
        if keep is not None and f[keep]:
            continue                  # the lime core is what shows through every gap: never cut it
        n = f.normal
        if n.length < 1e-9:
            dead.append(f)
            continue
        side = n.orthogonal().normalized()
        side2 = n.cross(side)
        c = f.calc_center_median()
        # test the middle and every corner (pulled a little inward): a face half hidden under a scrap is still seen
        pts = [c] + [v.co.lerp(c, 0.15) for v in f.verts]
        seen = False
        for p in pts:
            for base in (n, -n):
                for d in (base, (base + side * 0.6).normalized(), (base - side * 0.6).normalized(),
                          (base + side2 * 0.6).normalized(), (base - side2 * 0.6).normalized()):
                    if tree.ray_cast(p + d * 0.0002, d, 2.0)[0] is None:
                        seen = True
                        break
                if seen:
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    before = len(bm.faces)
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(me)
    bm.free()
    print(f"[glb] hidden faces removed: {len(dead)} of {before}")


GROUP_NAMES = ["core", "straps", "items_a", "items_b", "items_c"]


def _area(o):
    return sum(p.area for p in o.data.polygons) * max(o.scale) ** 2


def _part(src, g, coll):
    """A copy of the joined block holding only the faces of group g."""
    import bmesh
    me = src.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.faces.layers.int.get("grp")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != g], context="FACES")
    n = len(bm.faces)
    bm.to_mesh(me)
    bm.free()
    if not n:
        bpy.data.meshes.remove(me)
        return None
    ob = bpy.data.objects.new(GROUP_NAMES[g], me)
    ob.matrix_world = src.matrix_world
    coll.objects.link(ob)
    me.attributes.remove(me.attributes["grp"])
    return ob


def _bake_part(sc, ob, size):
    """Bake one part's color (crevices darkened), roughness and metal into its own texture sheet."""
    import numpy as np
    for o in bpy.data.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    ob.data.uv_layers.active = ob.data.uv_layers.new(name="bake")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.001)
    try:
        bpy.ops.uv.pack_islands(rotate=True, margin=0.001)
    except (TypeError, RuntimeError):
        pass
    bpy.ops.object.mode_set(mode="OBJECT")

    def target(name, non_color=False):
        im = bpy.data.images.new(f"{ob.name}_{name}", size, size, alpha=False)
        if non_color:
            im.colorspace_settings.name = "Non-Color"
        for slot in ob.material_slots:
            m = slot.material
            if not m or not m.node_tree:
                continue
            n = m.node_tree.nodes.get("_bake") or m.node_tree.nodes.new("ShaderNodeTexImage")
            n.name = "_bake"
            n.image = im
            uvn = m.node_tree.nodes.get("_bake_uv") or m.node_tree.nodes.new("ShaderNodeUVMap")
            uvn.name = "_bake_uv"
            uvn.uv_map = "bake"
            m.node_tree.links.new(uvn.outputs["UV"], n.inputs["Vector"])
            m.node_tree.nodes.active = n
        return im

    col = target("color")
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    rough = target("rough", non_color=True)
    bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    metal = target("metal", non_color=True)
    bpy.ops.object.bake(type="EMIT", use_clear=True)      # the materials' glow carries their metal value here
    ao = target("ao", non_color=True)
    bpy.ops.object.bake(type="AO", use_clear=True)
    c = np.array(col.pixels[:], dtype=np.float32).reshape(-1, 4)
    o = np.array(ao.pixels[:], dtype=np.float32).reshape(-1, 4)
    c[:, :3] *= (0.25 + 0.75 * o[:, :1])
    col.pixels.foreach_set(c.ravel())
    um = bpy.data.materials.new(f"{ob.name}_baked")
    um.use_nodes = True
    nt = um.node_tree
    nt.nodes.clear()
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "bake"
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    for im, sock in ((col, "Base Color"), (rough, "Roughness"), (metal, "Metallic")):
        t_ = nt.nodes.new("ShaderNodeTexImage")
        t_.image = im
        nt.links.new(uvn.outputs["UV"], t_.inputs["Vector"])
        nt.links.new(t_.outputs["Color"], bsdf.inputs[sock])
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], outn.inputs["Surface"])
    return um


def export(tid, out, size=4096, samples=16, device="auto"):
    """The block is baked as five parts, each with its own texture sheet (the core, the straps, and the items
    split three ways), so every surface gets about five times the pixels one shared sheet could give it."""
    r = generate.token(tid)
    t0 = time.time()
    sc = build.build(r, res=256, samples=samples)
    if device != "cpu":
        stage.use_gpu(sc)
    sc.cycles.samples = samples
    sc.render.bake.margin = 4
    coll = bpy.data.collections["block"]
    objs = [o for o in coll.objects if o.type == "MESH" and len(o.data.polygons)]
    for o in bpy.data.objects:
        o.select_set(False)
    # which sheet each object goes on; items are dealt by size so the three item sheets fill evenly
    load = [0.0, 0.0, 0.0]
    grp = {}
    for o in sorted(objs, key=_area, reverse=True):
        if o.name.startswith("core"):
            grp[o.name] = 0
        elif o.name.startswith(("strap", "crimp", "seal")):
            grp[o.name] = 1
        else:
            k = load.index(min(load))
            load[k] += _area(o)
            grp[o.name] = 2 + k
    for o in objs:
        n = len(o.data.polygons)
        a = o.data.attributes.get("keep") or o.data.attributes.new("keep", "INT", "FACE")
        a.data.foreach_set("value", [1 if grp[o.name] == 0 else 0] * n)
        g = o.data.attributes.get("grp") or o.data.attributes.new("grp", "INT", "FACE")
        g.data.foreach_set("value", [grp[o.name]] * n)
    print("[glb] sheets:", {GROUP_NAMES[k]: sum(1 for v in grp.values() if v == k) for k in range(5)})
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    # the hidden-face cut needs the whole block at once (a face is hidden by its neighbors, whatever sheet they're on)
    cull_hidden(ob)
    ob.data.attributes.remove(ob.data.attributes["keep"])
    parts = [p for p in (_part(ob, g, coll) for g in range(5)) if p]
    bpy.data.objects.remove(ob, do_unlink=True)

    # metals and glass have no "diffuse" color, so a plain color bake turns gold black. Take their metal and
    # see-through settings off for the color bake, and send how metal each spot is out through the glow.
    for m in {s.material for p in parts for s in p.material_slots if s.material and s.material.node_tree}:
        nt_ = m.node_tree
        bs = next((n for n in nt_.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bs:
            continue
        sock = bs.inputs["Metallic"]
        src, val = (sock.links[0].from_socket if sock.links else None), sock.default_value
        for name in ("Metallic", "Transmission Weight", "Emission Color"):
            for l in list(bs.inputs[name].links):
                nt_.links.remove(l)
        bs.inputs["Metallic"].default_value = 0.0
        bs.inputs["Transmission Weight"].default_value = 0.0
        if src is not None:
            nt_.links.new(src, bs.inputs["Emission Color"])
        else:
            bs.inputs["Emission Color"].default_value = (val, val, val, 1.0)
        bs.inputs["Emission Strength"].default_value = 1.0
    baked = [(p, _bake_part(sc, p, size // 2 if p.name == "straps" else size)) for p in parts]
    t1 = time.time()
    for p, um in baked:
        p.data.materials.clear()
        p.data.materials.append(um)
        for uv in [u for u in p.data.uv_layers if u.name != "bake"]:
            p.data.uv_layers.remove(uv)
        p.name = f"crushed_{tid:04d}_{p.name}"
        p.location.z -= build.LIFT              # the block's center at the origin, like before
    os.makedirs(out, exist_ok=True)
    path = os.path.abspath(os.path.join(out, f"{tid:04d}.glb"))
    for o in bpy.data.objects:
        o.select_set(any(o == p for p, _ in baked))
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=90, export_materials="EXPORT",
                              export_yup=True, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6)
    faces = sum(len(p.data.polygons) for p, _ in baked)
    print(f"[glb] #{tid:04d} bake {t1 - t0:.0f}s export {time.time() - t1:.0f}s -> {path} "
          f"({os.path.getsize(path) / 1e6:.1f} MB, {faces} faces, {len(baked)} sheets)")
    return path


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", type=int, nargs="+", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "renders", "glb"))
    ap.add_argument("--size", type=int, default=4096)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"])
    a = ap.parse_args(argv)
    for t in a.token:
        export(t, a.out, a.size, a.samples, a.device)


if __name__ == "__main__":
    main()
