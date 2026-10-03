"""Master shape for anything box-like (cereal box, game box, VHS case, carton, card, ticket): built exactly to its
real size, with one clean texture laid out like the flattened box (a cross):

             [ top  ]
    [ left ][ front ][ right ][ back ]
             [bottom]

Each panel's place in the texture is in true proportion to the real panel, so print is never stretched.

    blender -b -P box.py -- W D H out_dir atlas.png [mr.png] [name] [bevel_mm]
W, D, H in meters (width across the front, depth front-to-back, height). Saves .blend .glb .fbx .usdc.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
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
surface = argv[8] if len(argv) > 8 else "card"          # what it's made of: card | plastic (library/finish.py)
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
    if surface == "card" and D > 0.005:            # the top closes with a lid flap: built as its own layer of card
        bm = bmesh.new()                            # (one card thick), its front edge tucked in - a real free edge
        bm.from_mesh(me)                            # and the shadow line every real carton has
        uv = bm.loops.layers.uv.verify()
        t, g, e = 0.00035, 0.0009, 0.0002
        x0, x1, y0, y1, z0, z1 = -w + e, w - e, -d + g, d - e, h, h + t
        u0, v0, u1, v1 = L["top"]
        U = lambda x: u0 + (x + w) / (2 * w) * (u1 - u0)
        V = lambda y: v0 + (y + d) / (2 * d) * (v1 - v0)
        quads = [[(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],              # lid top
                 [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],              # its front (free) edge
                 [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
                 [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
                 [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)]]
        for q in quads:
            f = bm.faces.new([bm.verts.new(c) for c in q])
            for loop, c in zip(f.loops, q):
                loop[uv].uv = (U(c[0]), V(c[1]))
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        me.update()
    for p in me.polygons:
        p.use_smooth = False
    mt = bpy.data.materials.new(name + "_print")
    mt.use_nodes = True
    bsdf = mt.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.45
    fin = {}
    if atlas not in ("", "-") and not mr:          # the real thing's surface: folds, grain, varnish, worn edges
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import finish
        fin = finish.box_atlas(atlas, L, os.path.join(out, "finish"), kind=surface, name=name)
        atlas, mr = fin["base"], fin["mr"]
    if atlas not in ("", "-"):                    # "-" = bare shape, painted later
        tex = mt.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(os.path.abspath(atlas))
        tex.extension = "EXTEND"
        mt.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if fin.get("normal"):
        tn = mt.node_tree.nodes.new("ShaderNodeTexImage")
        tn.image = bpy.data.images.load(os.path.abspath(fin["normal"]))
        tn.image.colorspace_settings.name = "Non-Color"
        nm = mt.node_tree.nodes.new("ShaderNodeNormalMap")
        mt.node_tree.links.new(tn.outputs["Color"], nm.inputs["Color"])
        mt.node_tree.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if mr:
        t2 = mt.node_tree.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(os.path.abspath(mr))
        t2.image.colorspace_settings.name = "Non-Color"
        sep = mt.node_tree.nodes.new("ShaderNodeSeparateColor")
        mt.node_tree.links.new(t2.outputs["Color"], sep.inputs["Color"])
        mt.node_tree.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        mt.node_tree.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    me.materials.append(mt)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import saveall                                     # library/shapes/saveall.py
    saveall.blend(out, name)                           # every picture packed inside the .blend: it opens anywhere
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), use_selection=True, export_yup=True)
    saveall.rest(out, name, "box")                     # .fbx (pictures inside) + .usdc + made.json
    json.dump(L, open(os.path.join(out, "layout.json"), "w"))
    print("[box]", name, W, D, H)
