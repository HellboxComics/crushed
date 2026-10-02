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

# view: (cell corner u0, v0 in the sheet (0..1, v up), facing direction, screen-right axis, screen-up axis)
CELL = (0.5, 0.5)            # each view's cell size in the sheet; the 3x2 turnaround sets (1/3, 1/2)
# the turnaround the drawing room makes: top row FRONT, LEFT, BACK; bottom row RIGHT, TOP, BOTTOM
VIEWS6 = {
    "front": ((0.0, 0.5), (0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "left": ((1 / 3, 0.5), (-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "back": ((2 / 3, 0.5), (0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "right": ((0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "top": ((1 / 3, 0.0), (0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "bottom": ((2 / 3, 0.0), (0, 0, -1), (1, 0, 0), (0, -1, 0)),
}
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


def outward(ob):
    """Every face's normal pointing out of the object. The sculptor's meshes can come out inside-out, and then each
    face picks the picture from the OPPOSITE side (the battery got its back label, mirrored, on its front). Blender's
    own recalculation makes them consistent; a final check against the center makes them point out, not in."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.faces.ensure_lookup_table()
    c = sum((f.calc_center_median() for f in bm.faces), Vector()) / max(1, len(bm.faces))
    out = sum(f.normal.dot(f.calc_center_median() - c) * f.calc_area() for f in bm.faces)
    if out < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    print(f"[remaster] normals {'flipped to point out' if out < 0 else 'already point out'}")


MAX_FACES = 60000      # the sculptor's raw mesh is millions of faces (250 MB); a crushed bale needs a fraction of that


def slim(ob, max_faces=MAX_FACES):
    """Cut the sculptor's mesh down to a sane size without losing its shape (Blender's collapse decimation)."""
    n = len(ob.data.polygons)
    if n <= max_faces:
        return
    if not ob.users_collection:
        bpy.context.scene.collection.objects.link(ob)
    m = ob.modifiers.new("slim", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = max_faces / n
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=m.name)
    print(f"[remaster] slimmed {n} -> {len(ob.data.polygons)} faces")


def fit(ob, target, turn=True):
    """Center, keep the sculptor's up as up, turn 90 degrees if its footprint runs the wrong way, scale to size."""
    me = ob.data
    v = np.array([vt.co[:] for vt in me.vertices])
    v -= (v.min(0) + v.max(0)) / 2
    ext = np.ptp(v, axis=0)
    if turn and (ext[0] > ext[1]) != (target[0] > target[1]) and abs(ext[0] - ext[1]) > 0.08 * ext.max():
        v = v[:, [1, 0, 2]] * np.array([-1, 1, 1])
        ext = np.ptp(v, axis=0)
    v *= float(np.median(target / np.maximum(ext, 1e-6)))
    me.vertices.foreach_set("co", v.astype(np.float32).ravel())
    me.update()


def _boxes(sheet_path):
    """Each quadrant's object bounding box (sheet coordinates 0..1, v up), so the picture's white margin is never
    painted onto the model."""
    from PIL import Image
    im = np.asarray(Image.open(sheet_path).convert("RGB")).astype(int)
    H, W = im.shape[:2]
    out = {}
    for k, ((u0, v0), _, _, _) in VIEWS.items():
        x0, x1 = int(u0 * W), int((u0 + CELL[0]) * W)
        y0, y1 = int((1 - v0 - CELL[1]) * H), int((1 - v0) * H)      # image rows run top-down
        q = im[y0:y1, x0:x1]
        mask = np.abs(q - 255).sum(-1) > 45
        if mask.sum() < 50:
            out[k] = (u0 + 0.03, v0 + 0.03, CELL[0] - 0.06, CELL[1] - 0.06)
            continue
        ys, xs = np.nonzero(mask)
        bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
        out[k] = ((x0 + bx0 + 2) / W, 1 - (y0 + by1 - 2) / H, (bx1 - bx0 - 4) / W, (by1 - by0 - 4) / H)
    return out


def project(ob, sheet_path):
    me = ob.data
    img = bpy.data.images.load(sheet_path)
    v = np.array([vt.co[:] for vt in me.vertices])
    lo, hi = v.min(0), v.max(0)
    span = np.maximum(hi - lo, 1e-6)
    uv = me.uv_layers.new(name="sheet")
    me.uv_layers.active = uv
    m = 0.0
    boxes = _boxes(sheet_path)                           # where the object actually sits in each view
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
            bu0, bv0, bw, bh = boxes[best]
            uv.data[li].uv = (bu0 + x * bw, bv0 + y * bh)
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


def new_method(a, target):
    """The six views decide the shape: round and box objects are built exactly from their real outline and real size;
    anything else uses the sculptor's shape. Then one seamless texture is baked from all six views."""
    import json
    import remaster_bake as B
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ai", "remaster"))
    import views as Vw
    views = Vw.load(a.turn)
    words = open(a.words).read() if a.words and os.path.exists(a.words) else ""
    spec = Vw.classify(views, words)
    if a.kind == "sculpt":
        spec = {**spec, "kind": "sculpt"}
    print("[remaster] shape: " + json.dumps({k: v for k, v in spec.items() if k != "profile"}))
    size = true_size(views, words, [float(x) for x in target])
    target[:] = size
    if spec["kind"] in ("lathe", "box"):
        if spec["kind"] == "lathe":
            P, F = B.build_lathe(spec["profile"], size)
        else:
            P, F = B.build_box(size, spec.get("corner_front", 0.0))
        me = bpy.data.meshes.new(a.name)
        me.from_pydata([tuple(map(float, p)) for p in P], [], [tuple(f) for f in F])
        me.update()
        ob = bpy.data.objects.new(a.name, me)
        bpy.context.scene.collection.objects.link(ob)
        weld(ob)
    else:
        if not a.shape:
            raise SystemExit("[remaster] this object needs the sculptor's shape (--shape)")
        ob = import_shape(a.shape)
        slim(ob)
        # the sculptor's model always faces the way its front picture did (checked: its face sits at -Y, our
        # front), so it is never turned; silhouettes can't tell front from back and once painted a Furby backward
        fit(ob, target, turn=False)
    outward(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    unwrap(ob)
    if spec["kind"] == "box":
        views = B.rectify_box(views, size)
    tex = B.bake(ob, views, res=a.res, use_ends=spec.get("top_view") in ("round", "box"),
                 radial=spec["kind"] == "lathe", fill3d=spec["kind"] == "sculpt",
                 min_fit=0.8 if spec["kind"] == "sculpt" else 0.0,
                 label=(np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(a.label).convert("RGB"),
                                   np.float32) / 255) if a.label and spec["kind"] == "lathe" else None)
    od = os.path.join(a.out, a.name)
    os.makedirs(od, exist_ok=True)
    from PIL import Image
    tp = os.path.join(od, "texture.png")
    Image.fromarray((np.clip(tex, 0, 1) * 255).astype(np.uint8)).save(tp)
    json.dump({k: v for k, v in spec.items()}, open(os.path.join(od, "shape.json"), "w"), indent=1)
    mt = bpy.data.materials.new("remaster")
    mt.use_nodes = True
    nt = mt.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(tp)
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.4
    ob.data.materials.clear()
    ob.data.materials.append(mt)
    return ob


def true_size(views, words, planned):
    """Real width, depth, height (m). The size written in the description the drawing was made from comes first
    ("real size 5.5 x 3.8 x 12.0 cm", "1.45 cm across and 5.05 cm tall"), then the planned size. The three numbers
    are matched to the drawing's own proportions (which one is the height, which the depth), so a size written in
    another order, or one meant for a whole pack, never squashes the object."""
    import itertools
    import re
    real = None
    m = re.search(r"real size\s+([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)\s*cm", words or "", re.I)
    if m:
        real = [float(x) / 100 for x in m.groups()]
    else:
        m = re.search(r"([\d.]+)\s*cm\s+(?:across|wide|in diameter)[^.]*?([\d.]+)\s*cm\s+(?:tall|high|long)",
                      words or "", re.I)
        if m:
            d, h = float(m.group(1)) / 100, float(m.group(2)) / 100
            real = [d, d, h]
    real = real or planned
    sides = {k: views[k]["mask"].shape for k in ("front", "back", "left", "right") if k in views}
    wd = np.mean([sides[k][1] for k in ("front", "back") if k in sides])
    dd = np.mean([sides[k][1] for k in ("left", "right") if k in sides])
    hd = np.mean([v[0] for v in sides.values()])
    # the front is drawn straight on and is trustworthy; the side views are often turned a little, which makes the
    # depth look bigger than it is. So the front's width-to-height picks which number is which; depth is the rest
    # (and only breaks a tie between two orders whose fronts fit equally well).
    fr = math.log(wd / hd)
    best = min(itertools.permutations(real),
               key=lambda p: (round(abs(math.log(p[0] / p[2]) - fr), 2), abs(math.log(p[1] / p[2]) - math.log(dd / hd))))
    err = abs(math.log(best[0] / best[2]) - fr)
    if err > math.log(1.35):                    # the numbers can't describe this drawing: keep its proportions
        k = max(real) / max(wd, dd, hd)
        best = (wd * k, dd * k, hd * k)
        print(f"[remaster] size {real} does not fit the drawing; drawing's proportions at that largest size")
    print(f"[remaster] real size used: {[round(x * 100, 2) for x in best]} cm (W, D, H)")
    return [float(x) for x in best]


def weld(ob):
    """Join the seams of a built shape into one closed skin (the box's faces, the lathe's caps)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bm.to_mesh(ob.data)
    bm.free()


def unwrap(ob):
    """Lay the skin out flat for painting (Blender's own Smart UV Project)."""
    for u in list(ob.data.uv_layers):
        ob.data.uv_layers.remove(u)
    ob.data.uv_layers.new(name="UVMap")
    if not ob.users_collection:
        bpy.context.scene.collection.objects.link(ob)
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(o == ob)
    vl.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


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
    ap.add_argument("--shape", default=None)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inside", default=None, help="picture of what it looks like inside, broken open")
    ap.add_argument("--turnaround", action="store_true", help="the sheet is the 3x2 six-view turnaround")
    ap.add_argument("--turn", default=None, help="the raw six-view turnaround: exact shape when simple, seamless bake")
    ap.add_argument("--words", default=None, help="the description file (says round or box when the views can't)")
    ap.add_argument("--res", type=int, default=2048, help="texture size")
    ap.add_argument("--label", default=None, help="the flat printed wrap of a round object")
    ap.add_argument("--kind", default="auto", help="auto, or sculpt to use the sculptor's shape even for a simple object")
    a = ap.parse_args(argv)
    if a.turnaround:
        global CELL
        CELL = (1 / 3, 0.5)
        VIEWS.clear()
        VIEWS.update(VIEWS6)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    target, d = code_size(a.name)
    from crushed import models as _m
    real = _m.props(a.name).get("size")              # the real size the Mac's AI looked up wins over the code's
    if real:
        target = np.array([float(x) for x in real])
    if a.turn:
        ob = new_method(a, target)
    else:
        ob = import_shape(a.shape)
        slim(ob)
        outward(ob)
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
