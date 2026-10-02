"""Master shape for anything box-like (cereal box, game box, VHS case, carton, card, ticket): built exactly to its
real size, with one clean texture laid out like the flattened box (a cross):

             [ top  ]
    [ left ][ front ][ right ][ back ]
             [bottom]

Each panel's place in the texture is in true proportion to the real panel, so print is never stretched.

    blender -b -P box.py -- W D H out_dir atlas.png [mr.png] [name] [bevel_mm]
W, D, H in meters (width across the front, depth front-to-back, height). Saves .blend .glb .fbx .usdc.
"""
import json
import os
import sys

import bpy
import bmesh

argv = sys.argv[sys.argv.index("--") + 1:]
W, D, H = (float(x) for x in argv[:3])
out, atlas = argv[3], argv[4]
mr = argv[5] if len(argv) > 5 and argv[5] not in ("", "-") else None
name = argv[6] if len(argv) > 6 else "box"
bevel = (float(argv[7]) if len(argv) > 7 else 0.6) / 1000.0
os.makedirs(out, exist_ok=True)


def layout(W, D, H):
    """Panel rectangles in the atlas (u0, v0, u1, v1), v up, all panels in true proportion."""
    tw, th = 2 * W + 2 * D, H + 2 * D
    s = 1.0 / max(tw, th)
    x = [0, D, D + W, 2 * D + W, 2 * D + 2 * W]
    y = [0, D, D + H, 2 * D + H]
    r = lambda x0, y0, x1, y1: (x0 * s, y0 * s, x1 * s, y1 * s)
    return {"left": r(x[0], y[1], x[1], y[2]), "front": r(x[1], y[1], x[2], y[2]), "right": r(x[2], y[1], x[3], y[2]),
            "back": r(x[3], y[1], x[4], y[2]), "top": r(x[1], y[2], x[2], y[3]), "bottom": r(x[1], y[0], x[2], y[1])}


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    w, d, h = W / 2, D / 2, H
    L = layout(W, D, H)
    # each face: corners in order bottom-left, bottom-right, top-right, top-left as seen from outside
    faces = {
        "front": [(-w, -d, 0), (w, -d, 0), (w, -d, h), (-w, -d, h)],
        "right": [(w, -d, 0), (w, d, 0), (w, d, h), (w, -d, h)],
        "back": [(w, d, 0), (-w, d, 0), (-w, d, h), (w, d, h)],
        "left": [(-w, d, 0), (-w, -d, 0), (-w, -d, h), (-w, d, h)],
        "top": [(-w, -d, h), (w, -d, h), (w, d, h), (-w, d, h)],
        "bottom": [(-w, d, 0), (w, d, 0), (w, -d, 0), (-w, -d, 0)],
    }
    for k, cs in faces.items():
        vs = [bm.verts.new(c) for c in cs]
        f = bm.faces.new(vs)
        u0, v0, u1, v1 = L[k]
        for loop, (uu, vv) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            loop[uv].uv = (uu, vv)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    if bevel > 0:                         # real cartons have softly rounded edges that catch light
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = min(bevel, 0.2 * min(W, D, H))
        m.segments = 3
        m.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="bevel")
    for p in me.polygons:
        p.use_smooth = False
    mt = bpy.data.materials.new(name + "_print")
    mt.use_nodes = True
    bsdf = mt.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.45
    tex = mt.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.abspath(atlas))
    tex.extension = "EXTEND"
    mt.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if mr:
        t2 = mt.node_tree.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(os.path.abspath(mr))
        t2.image.colorspace_settings.name = "Non-Color"
        sep = mt.node_tree.nodes.new("ShaderNodeSeparateColor")
        mt.node_tree.links.new(t2.outputs["Color"], sep.inputs["Color"])
        mt.node_tree.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        mt.node_tree.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    me.materials.append(mt)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, name + ".blend"))
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), use_selection=True, export_yup=True)
    for fmt, call in (("fbx", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=True)),
                      ("usdc", lambda p: bpy.ops.wm.usd_export(filepath=p, selected_objects_only=True))):
        try:
            call(os.path.join(out, name + "." + fmt))
        except Exception as e:
            print(f"[box] {fmt} export unavailable here: {e}")
    json.dump(L, open(os.path.join(out, "layout.json"), "w"))
    print("[box]", name, W, D, H)
