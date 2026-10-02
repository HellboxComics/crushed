"""Blender pass of the remaster: take the sculptor's shape and the drawing room's 2x2 reference sheet, and make
a finished model.

    python3 blender/remaster_texture.py --name gremlin --shape shape.glb --sheet sheet.png --out assets/models_pending

1. The shape is turned so its longest sides line up with the code-built object's, centered, and scaled to the
   code-built object's real size (so a console is console-sized, a ring candy is ring-sized).
2. The sheet is painted onto it: each face takes the view it faces (front, back, left, right; top and bottom
   borrow the front), projected straight on. Seams blend over a band between views.
3. Saved as model.glb with a preview (four sides) and a side-by-side with the code-built version, for review.

The sheet layout is the sculptor's: top left FRONT, top right BACK, bottom left LEFT side, bottom right RIGHT side.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

# view: (quadrant u0, v0 in the sheet (0..1, v up), facing direction, screen-right axis, screen-up axis)
VIEWS = {
    "front": ((0.0, 0.5), (0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "back": ((0.5, 0.5), (0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "left": ((0.0, 0.0), (-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "right": ((0.5, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
}


def code_size(name):
    """The bounding size of the code-built object (seed 0): the real-world size the remaster must match."""
    from crushed import build, stage
    from crushed.objects import Palette, load
    reg = load()
    d = reg[name]
    sc = bpy.context.scene
    coll = bpy.data.collections.new("_size")
    sc.collection.children.link(coll)
    rng = np.random.default_rng(0)
    ob = build.make_object(d, rng, Palette(d.eras[0], rng), coll) if name not in _skip else None
    v = np.array([vt.co[:] for vt in ob.data.vertices])
    ext = np.ptp(v, axis=0)
    bpy.data.objects.remove(ob)
    bpy.data.collections.remove(coll)
    return ext, d


_skip = set()


def import_shape(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in meshes:
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world.identity()
    ob = meshes[0]
    if len(meshes) > 1:
        with bpy.context.temp_override(active_object=ob, selected_editable_objects=meshes):
            bpy.ops.object.join()
    for o in [o for o in bpy.data.objects if o not in before and o != ob]:
        bpy.data.objects.remove(o)
    return ob


def fit(ob, target):
    """Center, keep the sculptor's up as up, turn 90 degrees if its footprint runs the wrong way, scale to size."""
    me = ob.data
    v = np.array([vt.co[:] for vt in me.vertices])
    v -= (v.min(0) + v.max(0)) / 2
    ext = np.ptp(v, axis=0)
    if (ext[0] > ext[1]) != (target[0] > target[1]) and abs(ext[0] - ext[1]) > 0.08 * ext.max():
        v = v[:, [1, 0, 2]] * np.array([-1, 1, 1])
        ext = np.ptp(v, axis=0)
    v *= float(np.median(target / np.maximum(ext, 1e-6)))
    me.vertices.foreach_set("co", v.astype(np.float32).ravel())
    me.update()


def project(ob, sheet_path):
    me = ob.data
    img = bpy.data.images.load(sheet_path)
    v = np.array([vt.co[:] for vt in me.vertices])
    lo, hi = v.min(0), v.max(0)
    span = np.maximum(hi - lo, 1e-6)
    uv = me.uv_layers.new(name="sheet")
    me.uv_layers.active = uv
    m = 0.03                                             # inset, so a view never samples its neighbor
    for poly in me.polygons:
        n = np.array(poly.normal)
        best, score = None, -2
        for k, (_, f, _, _) in VIEWS.items():
            s = float(np.dot(n, -np.array(f)))           # a face that faces the camera of this view
            if s > score:
                best, score = k, s
        (u0, v0), f, r, up = VIEWS[best]
        r, up = np.array(r, float), np.array(up, float)
        for li in poly.loop_indices:
            p = v[me.loops[li].vertex_index] - lo
            x = float(np.dot(p, np.abs(r)) / np.dot(span, np.abs(r)))
            if r.sum() < 0:
                x = 1 - x
            y = float(np.dot(p, up) / np.dot(span, up))
            uv.data[li].uv = (u0 + m + x * (0.5 - 2 * m), v0 + m + y * (0.5 - 2 * m))
    mt = bpy.data.materials.new("remaster")
    mt.use_nodes = True
    nt = mt.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    me.materials.clear()
    me.materials.append(mt)
    for u in [u for u in me.uv_layers if u.name != "sheet"]:
        me.uv_layers.remove(u)
    me.uv_layers["sheet"].name = "UVMap"


def add_inside(ob, inside_path):
    """What it's made of inside: a slightly smaller copy of the shape, wearing the inside picture (circuit board,
    filling, foam, wires), mapped straight onto each side. The crusher tears holes in the outer shell, so this is
    what shows through them."""
    import bmesh
    me = ob.data
    mt = bpy.data.materials.new("inside")
    mt.use_nodes = True
    nt = mt.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(inside_path)
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    me.materials.append(mt)
    k = len(me.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    v = np.array([x.co[:] for x in bm.verts])
    c = (v.min(0) + v.max(0)) / 2
    lo, span = v.min(0), np.maximum(np.ptp(v, axis=0), 1e-6)
    dup = bmesh.ops.duplicate(bm, geom=bm.faces[:])
    for x in [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]:
        x.co = Vector((c + (np.array(x.co[:]) - c) * 0.9).tolist())
    for f in [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]:
        f.material_index = k
        ax = int(np.argmax(np.abs(np.array(f.normal[:]))))
        a, b = [i for i in range(3) if i != ax]
        for l in f.loops:
            p = (np.array(l.vert.co[:]) - lo) / span
            l[uv].uv = (float(p[a]), float(p[b]))
    bm.to_mesh(me)
    bm.free()


def preview(ob, out, extra=None):
    """Four sides of the model (and, below, the code-built version) on grey."""
    from PIL import Image
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.55, 1)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 12
    sc.render.resolution_x = sc.render.resolution_y = 360
    cam = bpy.data.objects.new("pc", bpy.data.cameras.new("pc"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    rows = []
    for o in [ob] + ([extra] if extra else []):
        for x in bpy.data.objects:
            if x.type == "MESH":
                x.hide_render = x != o
        v = np.array([vt.co[:] for vt in o.data.vertices]) @ np.array(o.matrix_world)[:3, :3].T + np.array(o.matrix_world)[:3, 3]
        c = Vector(((v.min(0) + v.max(0)) / 2).tolist())
        cam.data.ortho_scale = float(np.ptp(v, axis=0).max()) * 1.5
        tiles = []
        for i, az in enumerate((0, 90, 180, 270)):
            a = math.radians(az)
            d = Vector((math.sin(a), -math.cos(a), 0.45)).normalized()
            cam.location = c + d * 3
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            p = f"{out}_{len(rows)}{i}.png"
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            tiles.append(Image.open(p).convert("RGB"))
            os.remove(p)
        rows.append(tiles)
    sheet = Image.new("RGB", (360 * 4, 360 * len(rows)))
    for j, tiles in enumerate(rows):
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * 360, j * 360))
    sheet.save(out + ".png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--shape", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inside", default=None, help="picture of what it looks like inside, broken open")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    target, d = code_size(a.name)
    from crushed import models as _m
    real = _m.props(a.name).get("size")              # the real size the Mac's AI looked up wins over the code's
    if real:
        target = np.array([float(x) for x in real])
    ob = import_shape(a.shape)
    fit(ob, target)
    project(ob, a.sheet)
    if a.inside:
        add_inside(ob, a.inside)
    od = os.path.join(a.out, a.name)
    os.makedirs(od, exist_ok=True)
    for o in bpy.data.objects:
        o.select_set(o == ob)
    bpy.ops.export_scene.gltf(filepath=os.path.join(od, "model.glb"), export_format="GLB", use_selection=True,
                              export_image_format="JPEG", export_jpeg_quality=90)
    # the code-built version next to it, for review
    from crushed import build
    from crushed.objects import Palette
    rng = np.random.default_rng(0)
    coll = bpy.data.collections.new("_cmp")
    bpy.context.scene.collection.children.link(coll)
    if build.models.path(a.name):
        extra = None
    else:
        extra = build.make_object(d, rng, Palette(d.eras[0], rng), coll)
    if ob.name not in bpy.context.scene.collection.objects and not ob.users_collection:
        bpy.context.scene.collection.objects.link(ob)
    preview(ob, os.path.join(od, "review"), extra)
    print(f"[remaster] {a.name} -> {od}/model.glb")


if __name__ == "__main__":
    main()
