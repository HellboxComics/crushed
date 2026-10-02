"""A CIRCUIT CARD, MADE THE WAY IT IS MADE: a fiberglass board (FR4, 1.6 mm) cut to its real outline - gold finger
tabs and notches included - printed with its traces and silkscreen (the real photo), then every part soldered on as
its own solid: the chips (their real markings on top), memory, capacitors, crystal, regulator, connectors, pin
headers, and the steel bracket on the end. Every part carries its crush physics. Saved as .blend .glb .fbx .usdc.

    python pcb.py -- W H out_dir front.png front_mask.png parts.json name
      W, H in meters (the board's length and height); parts.json from your AI reading the photo:
      [{"type": "chip", "box": [x0, y0, x1, y1], "height_mm": 2.5}, ...]   (box as fractions of front.png)
"""
import json
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (after bpy)
import numpy as np
from PIL import Image

argv = sys.argv[sys.argv.index("--") + 1:]
W, H = float(argv[0]) * 1000, float(argv[1]) * 1000
OUT, FRONT, MASK, PARTS, NAME = argv[2], argv[3], argv[4], argv[5], argv[6]
LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB)
import finish  # noqa: E402

PHYS = json.load(open(os.path.join(LIB, "factory", "physics.json")))
S, T = 0.001, 1.6
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
front = Image.open(FRONT).convert("RGB")
fw, fh = front.size
parts = json.load(open(PARTS)) if os.path.exists(PARTS) else []

# how tall each kind of part stands, and what it's made of (when the AI didn't say)
KIND = {"chip": (2.4, "molded_plastic", (0.05, 0.05, 0.055), 0.55),
        "memory_chip": (1.2, "molded_plastic", (0.05, 0.05, 0.055), 0.55),
        "capacitor_electrolytic": (7.0, "aluminum", None, 0.4), "capacitor_ceramic": (1.2, "molded_plastic", (0.6, 0.45, 0.3), 0.5),
        "resistor": (0.6, "molded_plastic", (0.08, 0.08, 0.08), 0.5), "crystal": (3.5, "bare_steel", (0.75, 0.75, 0.75), 0.3),
        "connector": (12.0, "molded_plastic", None, 0.45), "pin_header": (8.5, "molded_plastic", (0.05, 0.05, 0.05), 0.5),
        "heatsink": (10.0, "aluminum", (0.75, 0.76, 0.78), 0.35), "inductor": (4.0, "molded_plastic", (0.1, 0.1, 0.1), 0.6),
        "transistor": (4.0, "molded_plastic", (0.06, 0.06, 0.06), 0.5), "socket": (6.0, "molded_plastic", (0.1, 0.1, 0.1), 0.5),
        "led": (3.0, "clear_plastic", (0.2, 0.9, 0.3), 0.2), "jumper": (6.0, "molded_plastic", (0.05, 0.05, 0.05), 0.5)}

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []


def physics(ob, kind, part):
    ob["part"], ob["material_kind"] = part, kind
    for k, v in PHYS.get(kind, {}).items():
        ob[k] = v


def material(name, color=None, metallic=0.0, roughness=0.5, tex=None, normal=None):
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
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(normal)
        t.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return mt


def img_xy(u, v):
    """Fraction of the photo (u right, v down) -> board millimeters (x right, y up)."""
    return u * W, (1 - v) * H


# ------------------------------------------------------------------ the board, cut to its real outline
import cv2  # noqa: E402
m = np.asarray(Image.open(MASK).convert("L").resize((fw, fh))) > 127 if os.path.exists(MASK) else np.ones((fh, fw), bool)
m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
c = max(cs, key=cv2.contourArea)
poly = cv2.approxPolyDP(c, 0.0015 * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
top = [bm.verts.new((*[a * S for a in img_xy(x / fw, y / fh)], T * S)) for x, y in poly]
f = bm.faces.new(top)
if f.normal.z < 0:
    f.normal_flip()
uvs = {}
for loop in f.loops:
    x, y = loop.vert.co.x / S, loop.vert.co.y / S
    loop[uvl].uv = (x / W, y / H)
ext = bmesh.ops.extrude_face_region(bm, geom=[f])
bmesh.ops.translate(bm, vec=(0, 0, -T * S), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
bm.normal_update()
for face in bm.faces:                                # top: the photo; bottom: the solder side; edges: FR4
    face.material_index = 0 if face.normal.z > 0.9 else (1 if face.normal.z < -0.9 else 2)
    for loop in face.loops:
        loop[uvl].uv = (loop.vert.co.x / S / W, loop.vert.co.y / S / H)
bmesh.ops.triangulate(bm, faces=[x for x in bm.faces if len(x.verts) > 4])
me = bpy.data.meshes.new(NAME + "_board")
bm.to_mesh(me)
bm.free()
board = bpy.data.objects.new(NAME + "_board", me)
bpy.context.scene.collection.objects.link(board)
front.save(os.path.join(OUT, "textures", NAME + "_board_top.png"))
# the solder side: the board's own color with trace lines and pads (no photo of it)
bc = np.median(np.asarray(front.resize((64, 32))).reshape(-1, 3), 0) / 255
sol = np.ones((1024, 2048, 3), np.float32) * bc * 0.8
rng = np.random.default_rng(3)
for _ in range(400):
    y, x = rng.integers(0, 1024), rng.integers(0, 2048)
    L = rng.integers(20, 300)
    if rng.random() < 0.5:
        sol[y:y + 3, x:x + L] = bc * 1.25
    else:
        sol[y:y + L, x:x + 3] = bc * 1.25
for _ in range(1500):
    y, x = rng.integers(0, 1020), rng.integers(0, 2044)
    sol[y:y + 4, x:x + 4] = (0.75, 0.75, 0.72)                 # solder joints
Image.fromarray((np.clip(sol, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, "textures", NAME + "_board_bottom.png"))
fn = finish.make("plastic", os.path.join(OUT, "textures"), NAME + "_board", w=1024, h=512, base_rough=0.45)
board.data.materials.append(material("board_top", tex=os.path.join(OUT, "textures", NAME + "_board_top.png"),
                                     normal=fn["normal"], roughness=0.42))
board.data.materials.append(material("board_bottom", tex=os.path.join(OUT, "textures", NAME + "_board_bottom.png"),
                                     roughness=0.5))
board.data.materials.append(material("fr4_edge", color=(0.55, 0.5, 0.3), roughness=0.7))
physics(board, "circuit_board", "board")
objs.append(board)

# ------------------------------------------------------------------ every part on it
crops = os.path.join(OUT, "textures", "parts")
os.makedirs(crops, exist_ok=True)
for i, p in enumerate(parts):
    try:
        x0, y0, x1, y1 = [float(v) for v in p["box"]]
    except Exception:
        continue
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        continue
    kind = p.get("type", "chip")
    h_def, mkind, col, rough = KIND.get(kind, KIND["chip"])
    h = float(p.get("height_mm") or h_def)
    ax, ay = img_xy(x0, y1)
    bx, by = img_xy(x1, y0)
    cx, cy, sx, sy = (ax + bx) / 2, (ay + by) / 2, bx - ax, by - ay
    crop = front.crop((int(x0 * fw), int(y0 * fh), int(x1 * fw), int(y1 * fh)))
    cp = os.path.join(crops, f"{NAME}_part{i:03d}.png")
    crop.save(cp)
    side = col or tuple(np.median(np.asarray(crop).reshape(-1, 3), 0) / 255)
    name = f"{kind}_{i:03d}"
    if kind == "capacitor_electrolytic":
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=min(sx, sy) / 2 * S, depth=h * S,
                                            location=(cx * S, cy * S, (T + h / 2) * S))
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx * S, cy * S, (T + h / 2) * S))
        ob = bpy.context.active_object
        ob.scale = (sx * S, sy * S, h * S)
        bpy.ops.object.transform_apply(scale=True)
    ob = bpy.context.active_object
    ob.name = ob.data.name = name
    bv = ob.modifiers.new("edge", "BEVEL")
    bv.width, bv.segments = min(0.25, h * 0.1, sx * 0.1, sy * 0.1) * S, 2
    bpy.ops.object.modifier_apply(modifier="edge")
    ob.data.materials.append(material(name + "_side", color=side, roughness=rough,
                                      metallic=1.0 if mkind in ("aluminum", "bare_steel") else 0.0))
    ob.data.materials.append(material(name + "_top", tex=cp, roughness=rough,
                                      metallic=1.0 if mkind in ("aluminum", "bare_steel") else 0.0))
    me2 = ob.data
    uv2 = me2.uv_layers.new(name="UVMap")
    for poly in me2.polygons:                        # the top shows the real part from the photo (its markings)
        if poly.normal.z > 0.9:
            poly.material_index = 1
            for li in poly.loop_indices:
                v = me2.vertices[me2.loops[li].vertex_index].co
                uv2.data[li].uv = ((v.x / S - ax) / max(sx, 1e-6), (v.y / S - ay) / max(sy, 1e-6))
    physics(ob, mkind, kind)
    objs.append(ob)

# ------------------------------------------------------------------ the steel bracket on the end
side_left = any(p.get("type") == "connector" and float(p["box"][0]) < 0.2 for p in parts if "box" in p)
bx = 0.0 if side_left or not parts else W
bpy.ops.mesh.primitive_cube_add(size=1, location=((bx - 0.4) * S, H / 2 * S, 6.0 * S))
br = bpy.context.active_object
br.scale = (0.8 * S, (H + 14) * S, 18 * S)
bpy.ops.object.transform_apply(scale=True)
br.name = br.data.name = "bracket"
br.data.materials.append(material("bracket_steel", color=(0.72, 0.72, 0.7), metallic=1.0, roughness=0.32))
physics(br, "bare_steel", "bracket")
objs.append(br)
bpy.ops.mesh.primitive_cube_add(size=1, location=((bx - 5.5) * S, (H + 6.5) * S, 6.0 * S))  # the screw tab, bent 90°
tab = bpy.context.active_object
tab.scale = (10 * S, 0.8 * S, 18 * S)
bpy.ops.object.transform_apply(scale=True)
tab.name = tab.data.name = "bracket_tab"
tab.data.materials.append(bpy.data.materials["bracket_steel"])
physics(tab, "bare_steel", "bracket")
objs.append(tab)

json.dump({o.name: {k: o[k] for k in o.keys() if not k.startswith("_")} for o in objs},
          open(os.path.join(OUT, "physics.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
bpy.ops.object.select_all(action="DESELECT")
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = board
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), use_selection=True, export_yup=True,
                          export_extras=True)
for fmt, call in (("fbx", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=True)),
                  ("usdc", lambda p: bpy.ops.wm.usd_export(filepath=p, selected_objects_only=True))):
    try:
        call(os.path.join(OUT, NAME + "." + fmt))
    except Exception as e:
        print(f"[pcb] {fmt} export unavailable here: {e}")
print("[pcb]", NAME, "parts:", len(objs))
