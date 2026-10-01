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
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    dead = []
    for f in bm.faces:
        n = f.normal
        if n.length < 1e-9:
            dead.append(f)
            continue
        c = f.calc_center_median()
        side = n.orthogonal().normalized()
        side2 = n.cross(side)
        seen = False
        for base in (n, -n):
            for d in (base, (base + side * 0.6).normalized(), (base - side * 0.6).normalized(),
                      (base + side2 * 0.6).normalized(), (base - side2 * 0.6).normalized()):
                hit = tree.ray_cast(c + d * 0.0002, d, 2.0)
                if hit[0] is None:
                    seen = True
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


def export(tid, out, size=4096, samples=16, device="auto"):
    r = generate.token(tid)
    t0 = time.time()
    sc = build.build(r, res=256, samples=samples)
    if device != "cpu":
        stage.use_gpu(sc)
    sc.cycles.samples = samples
    coll = bpy.data.collections["block"]
    objs = [o for o in coll.objects if o.type == "MESH" and len(o.data.polygons)]
    for o in bpy.data.objects:
        o.select_set(False)
    # one mesh, one UV layout for the bake
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = f"crushed_{tid:04d}"
    cull_hidden(ob)
    bake_uv = ob.data.uv_layers.new(name="bake")
    ob.data.uv_layers.active = bake_uv
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    def target(name, non_color=False):
        im = bpy.data.images.new(name, size, size, alpha=False)
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

    sc.render.bake.margin = 6
    # metals and glass have no "diffuse" color, so a plain color bake turns gold black. Take their metal and
    # see-through settings off for the color bake, and bake how metal each spot is into its own map.
    metal_src = {}
    for slot in ob.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        bs = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bs:
            continue
        sock = bs.inputs["Metallic"]
        metal_src[m.name] = (sock.links[0].from_socket if sock.links else None, sock.default_value)
        for name in ("Metallic", "Transmission Weight"):
            for l in list(bs.inputs[name].links):
                m.node_tree.links.remove(l)
            bs.inputs[name].default_value = 0.0
    # 1. the surface color itself, no light in it: the viewer lights it live, so it reads as a real object
    col = target("color")
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_pass_color = True
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    # 2. how shiny each spot is
    rough = target("rough", non_color=True)
    bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    # 2b. how metal each spot is: route each material's metal value into its glow and bake the glow
    metal = target("metal", non_color=True)
    for slot in ob.material_slots:
        m = slot.material
        if not m or m.name not in metal_src:
            continue
        nt_ = m.node_tree
        bs = next(n for n in nt_.nodes if n.type == "BSDF_PRINCIPLED")
        src, val = metal_src[m.name]
        for l in list(bs.inputs["Emission Color"].links):
            nt_.links.remove(l)
        if src is not None:
            nt_.links.new(src, bs.inputs["Emission Color"])
        else:
            bs.inputs["Emission Color"].default_value = (val, val, val, 1.0)
        bs.inputs["Emission Strength"].default_value = 1.0
    bpy.ops.object.bake(type="EMIT", use_clear=True)
    # 3. the crevices: how buried each spot is, multiplied into the color so the crush keeps its depth
    ao = target("ao", non_color=True)
    bpy.ops.object.bake(type="AO", use_clear=True)
    import numpy as np
    c = np.array(col.pixels[:], dtype=np.float32).reshape(-1, 4)
    o = np.array(ao.pixels[:], dtype=np.float32).reshape(-1, 4)
    c[:, :3] *= (0.25 + 0.75 * o[:, :1])
    col.pixels.foreach_set(c.ravel())
    t1 = time.time()
    # one real material: color + roughness, lit by the viewer
    um = bpy.data.materials.new("baked")
    um.use_nodes = True
    nt = um.node_tree
    nt.nodes.clear()
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "bake"
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = col
    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = rough
    for t_ in (tc, tr):
        nt.links.new(uvn.outputs["UV"], t_.inputs["Vector"])
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    tm = nt.nodes.new("ShaderNodeTexImage")
    tm.image = metal
    nt.links.new(uvn.outputs["UV"], tm.inputs["Vector"])
    nt.links.new(tm.outputs["Color"], bsdf.inputs["Metallic"])
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], outn.inputs["Surface"])
    ob.data.materials.clear()
    ob.data.materials.append(um)
    for uv in [u for u in ob.data.uv_layers if u.name == "UVMap"]:
        ob.data.uv_layers.remove(uv)
    ob.parent = None
    ob.location = (0, 0, 0)
    os.makedirs(out, exist_ok=True)
    path = os.path.abspath(os.path.join(out, f"{tid:04d}.glb"))
    for o in bpy.data.objects:
        o.select_set(o == ob)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=88, export_materials="EXPORT",
                              export_yup=True, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6)
    print(f"[glb] #{tid:04d} bake {t1 - t0:.0f}s export {time.time() - t1:.0f}s -> {path} "
          f"({os.path.getsize(path) / 1e6:.1f} MB, {len(ob.data.polygons)} faces)")
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
