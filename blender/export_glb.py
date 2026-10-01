"""Export a block as a 3D object (GLB) you can spin on OpenSea: `animation_url` pointing at the .glb.

    python3 blender/export_glb.py --token 44 --out renders/glb --size 2048

The block's materials are procedural shader graphs, which no 3D viewer can show. So every surface of the
block is baked, lighting included, into one texture, and the GLB is exported "unlit": it looks the same as
the render from every angle, in any viewer. The straps, tape, wires, goo and droplets are baked in with it;
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


def export(tid, out, size=2048, samples=32, device="auto"):
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
    bake_uv = ob.data.uv_layers.new(name="bake")
    ob.data.uv_layers.active = bake_uv
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("bake", size, size, alpha=False)
    # every material needs an active image node pointing at the bake target
    for slot in ob.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        uvn = m.node_tree.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        m.node_tree.links.new(uvn.outputs["UV"], n.inputs["Vector"])
        m.node_tree.nodes.active = n
    sc.render.bake.use_pass_direct = True
    sc.render.bake.use_pass_indirect = True
    sc.render.bake.margin = 4
    bpy.ops.object.bake(type="COMBINED", use_clear=True)
    t1 = time.time()
    # replace every material with one unlit material that shows the bake
    um = bpy.data.materials.new("baked")
    um.use_nodes = True
    nt = um.node_tree
    nt.nodes.clear()
    tex_n = nt.nodes.new("ShaderNodeTexImage")
    tex_n.image = img
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "bake"
    nt.links.new(uvn.outputs["UV"], tex_n.inputs["Vector"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex_n.outputs["Color"], em.inputs["Color"])
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], outn.inputs["Surface"])
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
                              export_image_format="JPEG", export_jpeg_quality=85, export_materials="EXPORT",
                              export_yup=True)
    print(f"[glb] #{tid:04d} bake {t1 - t0:.0f}s export {time.time() - t1:.0f}s -> {path} "
          f"({os.path.getsize(path) / 1e6:.1f} MB, {len(ob.data.polygons)} faces)")
    return path


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", type=int, nargs="+", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "renders", "glb"))
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"])
    a = ap.parse_args(argv)
    for t in a.token:
        export(t, a.out, a.size, a.samples, a.device)


if __name__ == "__main__":
    main()
