"""A FOLDING CARTON, MADE THE WAY THE FACTORY MAKES IT (factory/recipes/folding_carton.json):

  1. the flat die-cut sheet (the dieline): back | left side | front | right side | glue flap across, the tuck lid and
     its tuck flap above the back, dust flaps above the sides, the bottom flaps below - printed on the outside
  2. real board thickness (0.45 mm): printed outside, plain recycled gray inside, cut edges showing the board
  3. creased and folded: the glue flap inside the back, the bottom flaps folded in (small ones first, then the two
     big ones), the product put in, the dust flaps in, the lid over and its tuck flap tucked inside the front
  4. inside: what the box really holds (foil pouches with the pastries), each part its own solid
Every part carries its crush physics (factory/physics.json). Saved as .blend .glb .fbx .usdc + physics.json.

    python carton.py -- W D H out_dir panels_dir name [contents]
      W D H in meters; panels_dir holds front.png back.png left.png right.png top.png bottom.png (library/skin.py)
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import json
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (after bpy)
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image

argv = sys.argv[sys.argv.index("--") + 1:]
W, D, H = (float(x) * 1000 for x in argv[:3])          # millimeters from here on
OUT, PANELS, NAME = argv[3], argv[4], argv[5]
CONTENTS = argv[6] if len(argv) > 6 else ""
LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB)
import finish                                          # noqa: E402

R = json.load(open(os.path.join(LIB, "factory", "recipes", "folding_carton.json")))
PHYS = json.load(open(os.path.join(LIB, "factory", "physics.json")))
T = R["board"]["thickness_mm"]
F = R["flaps_mm"]
G, TUCK = F["glue"], F["tuck"]
DUST = D * F["dust_fraction"]
BIN = D * F["bottom_inner_fraction"]
S = 0.001
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ 1. the dieline (flat, mm; v up)
xb, xs1, xf, xs2, xg = 0.0, W, W + D, 2 * W + D, 2 * W + 2 * D
PANEL = {   # name: (x0, v0, x1, v1, art, rotate_art_180)
    "back": (xb, 0, xs1, H, "back", False), "left": (xs1, 0, xf, H, "left", False),
    "front": (xf, 0, xs2, H, "front", False), "right": (xs2, 0, xg, H, "right", False),
    "glue": (xg, 0, xg + G, H, None, False),
    "lid": (xb, H, xs1, H + D, "top", True), "tuck": (xb, H + D, xs1, H + D + TUCK, None, False),
    "dust_l": (xs1, H, xf, H + DUST, None, False), "dust_r": (xs2, H, xg, H + DUST, None, False),
    "bottom": (xf, -D, xs2, 0, "bottom", False), "bottom_in": (xb, -BIN, xs1, 0, None, False),
    "minor_l": (xs1, -BIN * 0.8, xf, 0, None, False), "minor_r": (xs2, -BIN * 0.8, xg, 0, None, False),
}
HINGE = {   # child: (parent, (x0, v0), (x1, v1) of the crease, layer offset outward-normal steps)
    "left": ("front", (xf, 0), (xf, H)), "back": ("left", (xs1, 0), (xs1, H)),
    "right": ("front", (xs2, 0), (xs2, H)), "glue": ("right", (xg, 0), (xg, H)),
    "lid": ("back", (xb, H), (xs1, H)), "tuck": ("lid", (xb, H + D), (xs1, H + D)),
    "dust_l": ("left", (xs1, H), (xf, H)), "dust_r": ("right", (xs2, H), (xg, H)),
    "bottom": ("front", (xf, 0), (xs2, 0)), "bottom_in": ("back", (xb, 0), (xs1, 0)),
    "minor_l": ("left", (xs1, 0), (xf, 0)), "minor_r": ("right", (xs2, 0), (xg, 0)),
}
LAYER = {"glue": 1, "dust_l": 1, "dust_r": 1, "tuck": 1, "bottom_in": 1, "minor_l": 2, "minor_r": 2}  # inside the others
VMIN, VMAX, XMAX = -D, H + D + TUCK, xg + G
PPM = 10                                               # print resolution: 10 px per mm (254 dpi)

# ------------------------------------------------------------------ the printed sheet
cw, ch = int(XMAX * PPM), int((VMAX - VMIN) * PPM)
paper = None
sheet = Image.new("RGB", (cw, ch), (235, 230, 222))
for name, (x0, v0, x1, v1, art, rot) in PANEL.items():
    if not art:
        continue
    p = os.path.join(PANELS, art + ".png")
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    if rot:
        im = im.rotate(180)
    box = (int(x0 * PPM), int((VMAX - v1) * PPM), int(x1 * PPM), int((VMAX - v0) * PPM))
    sheet.paste(im.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
    if name == "front":
        import panels as PN
        paper = PN.paper_color(im)
if paper:                                              # flaps and the glue strip: the board's printed base color
    a = np.asarray(sheet).copy()
    for name, (x0, v0, x1, v1, art, rot) in PANEL.items():
        if art:
            continue
        a[int((VMAX - v1) * PPM):int((VMAX - v0) * PPM), int(x0 * PPM):int(x1 * PPM)] = paper
    sheet = Image.fromarray(a)
tex_dir = os.path.join(OUT, "textures")
os.makedirs(tex_dir, exist_ok=True)

# ------------------------------------------------------------------ the finish: creases, cracked ink, worn cut edges
base = np.asarray(sheet).astype(np.float32) / 255
hgt = np.zeros(base.shape[:2], np.float32)
wear = np.zeros(base.shape[:2], np.float32)
yy, xx = np.mgrid[0:ch, 0:cw]
for child, (par, (x0, v0), (x1, v1)) in HINGE.items():  # every crease: a groove and cracked ink along it
    if x0 == x1:
        d = np.abs(xx - x0 * PPM)
        span = (yy >= (VMAX - max(v0, v1)) * PPM) & (yy <= (VMAX - min(v0, v1)) * PPM)
    else:
        d = np.abs(yy - (VMAX - v0) * PPM)
        span = (xx >= min(x0, x1) * PPM) & (xx <= max(x0, x1) * PPM)
    hgt -= 3.0 * np.exp(-(d / (0.6 * PPM)) ** 2) * span
    n = finish._noise(ch, cw, 2.0, seed=sum(map(ord, child)))
    wear += span * np.clip(np.exp(-(d / (1.0 * PPM)) ** 2) * (0.5 + 0.9 * n), 0, 1)
k = np.clip(wear * 0.6, 0, 0.6)[..., None]
base = base * (1 - k) + np.array([0.93, 0.92, 0.88], np.float32) * k
cardm = finish.card(cw, ch, 0.5)
nrm = np.asarray(cardm["normal"]).astype(np.float32) / 127.5 - 1
gy, gx = np.gradient(hgt)
nrm[..., 0] += -gx * 0.6
nrm[..., 1] += gy * 0.6
nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
rough = np.clip(np.asarray(cardm["rough"])[..., 1] / 255 + 0.25 * wear, 0, 1)
Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tex_dir, NAME + "_print.png"))
Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(tex_dir, NAME + "_print_normal.png"))
mr = np.zeros((ch, cw, 3), np.uint8)
mr[..., 1] = (rough * 255).astype(np.uint8)
Image.fromarray(mr).save(os.path.join(tex_dir, NAME + "_print_mr.png"))
sheet.save(os.path.join(tex_dir, NAME + "_dieline.png"))          # the flat printed sheet, as the factory has it

# ------------------------------------------------------------------ 2-3. the sheet, folded
bpy.ops.wm.read_factory_settings(use_empty=True)


def flat3(x, v):
    """Flat sheet point -> 3D before folding: the front panel sits where the finished front is."""
    return Vector(((x - xf - W / 2) * S, -D / 2 * S, v * S))


def rot_about(a, b, ang):
    axis = (b - a).normalized()
    return Matrix.Translation(a) @ Matrix.Rotation(ang, 4, axis) @ Matrix.Translation(-a)


M = {"front": Matrix.Identity(4)}


def fold(name):
    if name in M:
        return M[name]
    par, p0, p1 = HINGE[name]
    a, b = flat3(*p0), flat3(*p1)
    x0, v0, x1, v1 = PANEL[name][:4]
    c = flat3((x0 + x1) / 2, (v0 + v1) / 2)
    best = None
    for ang in (math.pi / 2, -math.pi / 2):            # inward = toward the inside of the box (+Y in the flat frame)
        r = rot_about(a, b, ang)
        y = (r @ c).y
        if best is None or y > best[0]:
            best = (y, r)
    M[name] = fold(par) @ best[1]
    return M[name]


bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
STEP = 4.0                                              # mm between grid lines (fine enough to crush and bend)
for name, (x0, v0, x1, v1, art, rot) in PANEL.items():
    mtx = fold(name) if name != "front" else Matrix.Identity(4)
    nx, nv = max(1, int(round((x1 - x0) / STEP))), max(1, int(round((v1 - v0) / STEP)))
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nx + 1):
            x, v = x0 + (x1 - x0) * i / nx, v0 + (v1 - v0) * j / nv
            p = mtx @ flat3(x, v)
            row.append((bm.verts.new(p), (x / XMAX, (v - VMIN) / (VMAX - VMIN))))
        grid.append(row)
    for j in range(nv):
        for i in range(nx):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            f = bm.faces.new([c[0] for c in q])         # faces point out of the printed side (-Y in the flat frame)
            for loop, c in zip(f.loops, q):
                loop[uvl].uv = c[1]
            f.material_index = 0
    if name in LAYER:                                    # flaps that sit inside another layer of board
        n = (mtx.to_3x3() @ Vector((0, -1, 0))).normalized()
        off = -n * LAYER[name] * T * S
        for row in grid:
            for vtx, _ in row:
                vtx.co += off
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)  # the creases join: one continuous sheet of board
me = bpy.data.meshes.new(NAME + "_box")
bm.to_mesh(me)
bm.free()
box = bpy.data.objects.new(NAME + "_box", me)
bpy.context.scene.collection.objects.link(box)


def material(name, color=None, metallic=0.0, roughness=0.5, tex=None, normal=None, mr=None, coat=0.0):
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    nt = mt.node_tree
    b = nt.nodes["Principled BSDF"]
    if color:
        b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex)
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if mr:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(mr)
        t.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(normal)
        t.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.25
    return mt


box.data.materials.append(material("print", tex=os.path.join(tex_dir, NAME + "_print.png"),
                                   normal=os.path.join(tex_dir, NAME + "_print_normal.png"),
                                   mr=os.path.join(tex_dir, NAME + "_print_mr.png"), coat=0.3))
box.data.materials.append(material("board_inside", color=R["board"]["inside_color"], roughness=0.9))
box.data.materials.append(material("board_edge", color=[0.62, 0.6, 0.55], roughness=0.95))
sol = box.modifiers.new("board", "SOLIDIFY")            # the board's real thickness, inward
sol.thickness = T * S
sol.offset = -1
sol.use_even_offset = True
sol.use_rim = True
sol.material_offset = 1
sol.material_offset_rim = 2
bpy.context.view_layer.objects.active = box
bpy.ops.object.modifier_apply(modifier="board")
for p in box.data.polygons:
    p.use_smooth = False


def physics(ob, kind, part):
    ob["part"], ob["material_kind"] = part, kind
    for k, v in PHYS.get(kind, {}).items():
        ob[k] = v


physics(box, R["board"]["kind"], "carton")
parts = [box]

# ------------------------------------------------------------------ 4. what's inside
C = (json.load(open(CONTENTS)) if CONTENTS.endswith(".json") and os.path.exists(CONTENTS)   # from the item's dossier
     else R.get("contents", {}).get(CONTENTS))
if C:
    pw, ph, pd = C["pouch_mm"]
    sw, sh, sd = C["pastry_mm"]
    rng = np.random.default_rng(5)
    # the foil: crinkled, a little uneven in its shine
    nz = finish._noise(1024, 1024, 70) + 0.15 * finish._noise(1024, 1024, 12)   # soft wrinkles, a few sharp creases
    crinkle = np.abs(nz) ** 0.8
    gy, gx = np.gradient(crinkle)
    n = np.stack([-gx * 2.5, gy * 2.5, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(tex_dir, "foil_normal.png"))
    foil = material("foil", color=[0.78, 0.78, 0.8], metallic=1.0, roughness=0.22,
                    normal=os.path.join(tex_dir, "foil_normal.png"))
    # the pastry: crust edge, frosting with sprinkles on top
    tw, th = 768, 532
    top = np.zeros((th, tw, 3), np.float32)
    yy2, xx2 = np.mgrid[0:th, 0:tw]
    edge = np.minimum.reduce([xx2, yy2, tw - 1 - xx2, th - 1 - yy2]) / (0.07 * tw)
    crust = np.array([0.82, 0.6, 0.38])
    frost = np.array([0.97, 0.93, 0.93]) + 0.02 * finish._noise(th, tw, 3)[..., None]
    inside = np.clip((edge - 1) * 2, 0, 1)[..., None]
    top = crust * (1 - inside) + frost * inside
    for _ in range(900):
        y, x = int(rng.uniform(0.12, 0.88) * th), int(rng.uniform(0.1, 0.9) * tw)
        col = [(0.86, 0.15, 0.25), (0.95, 0.45, 0.6), (0.98, 0.8, 0.2), (0.3, 0.6, 0.9), (0.4, 0.75, 0.4)][rng.integers(0, 5)]
        top[max(0, y - 2):y + 2, max(0, x - 3):x + 3] = col
    Image.fromarray((np.clip(top, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tex_dir, "pastry_top.png"))
    pastry_mat = material("pastry", tex=os.path.join(tex_dir, "pastry_top.png"), roughness=0.7)
    crust_mat = material("crust", color=[0.78, 0.55, 0.33], roughness=0.85)

    def rounded_box(name, sx, sy, sz, at, mats, bevel):
        bpy.ops.mesh.primitive_cube_add(size=1, location=at)
        o = bpy.context.active_object
        o.name = o.data.name = name
        o.scale = (sx * S, sy * S, sz * S)
        bpy.ops.object.transform_apply(scale=True)
        bv = o.modifiers.new("round", "BEVEL")
        bv.width, bv.segments = bevel * S, 3
        bpy.ops.object.modifier_apply(modifier="round")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=max(sx, sy, sz) * S)
        bpy.ops.object.mode_set(mode="OBJECT")
        for m in mats:
            o.data.materials.append(m)
        return o

    k = 0
    rows_, cols_ = int(C.get("rows", 2)), int(C.get("cols", 2))
    for row in range(rows_):                               # how many high
        for col in range(cols_):                           # how many deep
            if k >= int(C.get("pouches", rows_ * cols_)):
                break
            cx = 0.0
            cy = -D / 2 + T * 3 + pd / 2 + col * (pd + 0.6)
            cz = T * 4 + ph / 2 + row * (ph + 1.0)
            k += 1
            if not C.get("loose"):                         # items packed in pouches; loose items sit in the box
                po = rounded_box(f"pouch_{k}", pw, pd, ph, (cx * S, cy * S, cz * S), [foil], bevel=4)
                # a pouch is a pillow: its middle bulges a little, its sealed ends are pinched flat
                for v in po.data.vertices:
                    fx = 1 - min(1, abs(v.co.x) / (pw / 2 * S))
                    v.co.y = cy * S + (v.co.y - cy * S) * (0.75 + 0.25 * math.sin(math.pi * min(1, fx * 1.6) / 2))
                physics(po, C["pouch_kind"], "pouch")
                po["inside"] = True                        # inside the box: must never show through it
                parts.append(po)
            for s_ in range(C["per_pouch"]):               # the pastries in it, stacked
                py = cy - pd / 2 + 2.5 + sd / 2 + s_ * (sd + 0.4)
                pa = rounded_box(f"pastry_{k}_{s_ + 1}", sw, sd, sh, (cx * S, py * S, cz * S), [pastry_mat, crust_mat],
                                 bevel=3)
                physics(pa, C["pastry_kind"], "pastry")
                pa["inside"] = True
                parts.append(pa)

json.dump({o.name: {k: o[k] for k in o.keys() if not k.startswith("_")} for o in parts},
          open(os.path.join(OUT, "physics.json"), "w"), indent=1)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saveall                                         # noqa: E402  library/shapes/saveall.py

saveall.blend(OUT, NAME)                               # every picture packed inside the .blend: it opens anywhere
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = box
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), use_selection=True, export_yup=True,
                          export_extras=True)
saveall.rest(OUT, NAME, "carton", extras=("physics.json",))   # .fbx (pictures inside) + .usdc + made.json
print("[carton]", NAME, "parts:", len(parts))
