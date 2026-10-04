"""The parts builder: your AI's plan is cleaned (outlines for soft parts), and the loft that builds a soft part
makes a closed, sane mesh of the planned size (Blender itself is not here, so its mesh tools are stood in for)."""
import ast
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import parts  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        sys.exit(1)
    ok += 1


# 1. clean(): outlines kept, bad ones replaced by the egg and written in 'fixed'
raw = {"parts": [
    {"name": "ear", "shape": "organic", "size_mm": [30, 16, 50], "at_mm": [0, 0, 25],
     "front_outline": [0.3, 0.7, 1.0, 0.9, 0.6, 0.3, 0.0], "side_outline": [0.6, 1.0, 0.9, 0.7, 0.5, 0.3, 0.0],
     "lean_mm": [[0, 0], [400, 0]], "material": "plush_fur"},
    {"name": "tuft", "shape": "organic", "size_mm": [20, 20, 20], "at_mm": [0, 0, 70], "material": "plush_fur"},
    {"name": "eye", "shape": "sphere", "size_mm": [10, 10, 10], "at_mm": [0, -10, 50], "material": "clear_plastic"}]}
p = parts.clean(raw, 60, 40, 80, [], ["plush_fur", "clear_plastic", "molded_plastic"])
ear, tuft, eye = p["parts"]
check(ear["front_outline"] == [0.3, 0.7, 1.0, 0.9, 0.6, 0.3, 0.0] and len(ear["side_outline"]) == 7,
      "a soft part keeps the outlines your AI read off the photos")
check(ear["lean_mm"][1][0] == 30.0, "a lean past the object's half width is held inside it")
check(tuft["front_outline"] == list(parts.EGG) and any("tuft: no front outline" in f for f in p["fixed"]),
      "a soft part with no outline gets the egg, and that is written down as a fix")
check("front_outline" not in eye or eye["front_outline"] == [], "a hard part carries no outline")

# 2. the loft itself (assembly.form) with Blender's mesh tools stood in for
src = open(os.path.join(LIB, "shapes", "assembly.py")).read()
tree = ast.parse(src)
want = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("_resample", "form")] + \
       [n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EGG"]
code = compile(ast.Module(body=want, type_ignores=[]), "assembly_form", "exec")


class V:
    def __init__(self, co):
        self.co = co


class Faces:
    def __init__(self):
        self.made = []

    def new(self, verts):
        verts = list(verts)
        assert len(set(id(v) for v in verts)) == len(verts), "a face uses one vertex twice"
        self.made.append(verts)
        return verts

    def __iter__(self):
        return iter(self.made)


class BM:
    def __init__(self):
        self.verts = types.SimpleNamespace(new=lambda co: V(co), made=[])
        self.faces = Faces()
        self.mesh = None

    def to_mesh(self, me):
        me.faces = list(self.faces.made)

    def free(self):
        pass


class Mods:
    def new(self, name, kind):
        return types.SimpleNamespace(levels=0, render_levels=0)


class Ob:
    def __init__(self, name, me):
        self.name, self.data, self.location, self.modifiers, self.d = name, me, None, Mods(), {}

    def select_set(self, v):
        pass

    def __setitem__(self, k, v):
        self.d[k] = v


bms = []


def _bm_new():
    b = BM()
    bms.append(b)
    return b


fake_bmesh = types.SimpleNamespace(new=_bm_new, ops=types.SimpleNamespace(recalc_face_normals=lambda bm, faces: None))
fake_bpy = types.SimpleNamespace(
    data=types.SimpleNamespace(meshes=types.SimpleNamespace(new=lambda n: types.SimpleNamespace(name=n, faces=[])),
                               objects=types.SimpleNamespace(new=lambda n, me: Ob(n, me))),
    context=types.SimpleNamespace(collection=types.SimpleNamespace(objects=types.SimpleNamespace(link=lambda o: None)),
                                  view_layer=types.SimpleNamespace(objects=types.SimpleNamespace(active=None))),
    ops=types.SimpleNamespace(object=types.SimpleNamespace(modifier_apply=lambda modifier: None)))
finished = []
ns = {"bmesh": fake_bmesh, "bpy": fake_bpy, "math": math, "S": 0.001, "finish": lambda ob, part: finished.append((ob, part)) or ob}
exec(code, ns)

ob = ns["form"](ear)
bm = bms[-1]
faces = bm.faces.made
verts = {id(v): v for f in faces for v in f}.values()
xs = [v.co[0] / 0.001 for v in verts]
ys = [v.co[1] / 0.001 for v in verts]
zs = [v.co[2] / 0.001 for v in verts]
check(abs((max(zs) - min(zs)) - 50) < 1e-6, f"the loft spans the part's height ({max(zs) - min(zs):.1f} mm)")
check(abs((max(xs) - min(xs)) - 30) < 3.5 and abs((max(ys) - min(ys)) - 16) < 1.0,
      f"and its width/depth ({max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} mm for 30 x 16)")
check(all(len(f) in (3, 4, 48) for f in faces) and len(faces) > 500, f"{len(faces)} faces: triangles, quads and a flat cap, no bad face")
# every edge is shared by exactly two faces -> a closed (watertight) surface
edges = {}
for f in faces:
    for a, b in zip(f, f[1:] + f[:1]):
        k = tuple(sorted((id(a), id(b))))
        edges[k] = edges.get(k, 0) + 1
check(all(n == 2 for n in edges.values()), "the lofted surface is closed (every edge shared by two faces)")
check(ob.d.get("lofted_from_outlines") is True and ob.location == [0, 0, 0.025], "built at the part's center")

# an egg (both ends closed) and an open-bottom cylinder-like outline both close up
ns["form"](dict(tuft, front_outline=list(parts.EGG), side_outline=list(parts.EGG)))
faces = bms[-1].faces.made
edges = {}
for f in faces:
    for a, b in zip(f, f[1:] + f[:1]):
        k = tuple(sorted((id(a), id(b))))
        edges[k] = edges.get(k, 0) + 1
check(all(n == 2 for n in edges.values()), "an egg (pointed at both ends) is closed too")
ns["form"](dict(tuft, front_outline=[1, 1, 1], side_outline=[1, 1, 1]))
faces = bms[-1].faces.made
check(any(len(f) > 4 for f in faces), "an open-ended outline gets flat caps")
print(f"\n{ok} checks passed")
