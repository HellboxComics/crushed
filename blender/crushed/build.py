"""Assemble one token's scene from its recipe."""
import math

import bpy
import numpy as np
from mathutils import Euler, Vector

from . import crush, dressing, mat, stage
from .geo import Builder
from .objects import PALETTES, Palette, load
from .stage import H

LIFT = H + 0.004           # centre height of the block above the floor

FACE_WEIGHTS = {"-Y": 0.32, "+X": 0.26, "+Z": 0.24, "+Y": 0.09, "-X": 0.09}
VISIBLE = ("-Y", "+X", "+Z")


def make_object(defn, rng, pal, coll, override=None):
    b = Builder(defn.name)
    specs = defn.fn(b, rng, pal)
    ob = b.build(coll)
    for key in b.slots:
        spec = override or specs.get(key, ("plastic", {}))
        ob.data.materials.append(mat.get(spec, rng))
    return ob


def prepare(ob, scale_limit, rng):
    """Scale to crush size, densify, mark sharp edges, store rest position."""
    me = ob.data
    v = crush.verts(me)
    if len(v) == 0:
        return None
    ext = np.ptp(v, axis=0)
    s = min(1.0, scale_limit / max(ext.max(), 1e-6))
    v = (v - (v.min(axis=0) + v.max(axis=0)) / 2) * s
    crush.set_verts(me, v)
    crush.densify(me, max(0.0035, min(0.007, ext.max() * s / 12)))
    me.set_sharp_from_angle(angle=math.radians(38))
    v = crush.verts(me)
    crush.store_rest(me, v)
    return v


def damage(v, rng, inten, brittle=False, keep_shape=False):
    """keep_shape: recognisable objects get dented and bent, not destroyed."""
    if brittle:
        return crush.dents(v, rng, int(rng.integers(0, 2)), 0.002)
    if keep_shape:
        v = crush.bend(v, rng, 0.3 * inten)
        if rng.random() < 0.35 * inten:
            v = crush.fold(v, rng, 1, 0.6 * inten)
        v = crush.crumple(v, rng, rng.uniform(0.15, 0.5) * inten)
        return crush.dents(v, rng, int(rng.integers(1, 4)), rng.uniform(0.002, 0.008) * inten)
    v = crush.bend(v, rng, 0.55 * inten)
    v = crush.fold(v, rng, int(rng.integers(1, 4)), 1.1 * inten)
    v = crush.crumple(v, rng, rng.uniform(0.35, 1.0) * inten)
    v = crush.dents(v, rng, int(rng.integers(0, 4)), rng.uniform(0.002, 0.012) * inten)
    return v


class Faces:
    def __init__(self, rng):
        self.rng = rng
        self.placed = {f: [] for f in crush.FACES}

    def pick_face(self, weights=FACE_WEIGHTS):
        keys = list(weights)
        w = np.array([weights[k] for k in keys])
        return keys[self.rng.choice(len(keys), p=w / w.sum())]

    def pick_uv(self, face, radius, spread=0.82):
        best, best_score = None, -1e9
        for _ in range(18):
            uv = self.rng.uniform(-spread, spread, 2) * H
            score = min([np.hypot(*(uv - p)) - r - radius for p, r in self.placed[face]] or [1.0])
            if score > best_score:
                best, best_score = uv, score
        self.placed[face].append((best, radius))
        return best


def build_block(r, coll, rng):
    reg = load()
    era = r["era_index"]
    inten = r["intensity"]
    pal = Palette(era, rng)
    crush.STRAPS = r["straps"]
    faces = Faces(rng)
    objs = []

    # the dense undifferentiated mass behind everything
    core_pal = list(PALETTES[era]["body"]) + list(PALETTES[era]["loud"])
    if r["clean"]:
        c = r["clean"][1][1].get("color", (0.8, 0.8, 0.8))
        core_pal = [tuple(x * k for x in c) for k in (0.5, 0.7, 0.85, 1.0)]
    objs.append(dressing.core(coll, rng, core_pal, r["seed"]))

    # the headliner goes front and centre; then big things (the back layer); then the rest
    rest = sorted(range(1, len(r["heroes"])), key=lambda i: not reg[r["heroes"][i]].big)
    order = ([0] if r["heroes"] else []) + rest
    for rank, i in enumerate(order):
        d = reg[r["heroes"][i]]
        head = i == 0
        override = ("gold", {}) if r["gold_index"] == i else None
        ob = make_object(d, rng, pal, coll, override)
        limit = rng.uniform(0.15, 0.21) if d.big else 0.17
        if head:
            limit = 0.21 if d.big else 0.19
        v = prepare(ob, limit, rng)
        if v is None:
            continue
        v = damage(v, rng, inten * (0.6 if head else 1.0), keep_shape=head or not d.big)
        if head:
            face = "-Y"
        else:
            face = faces.pick_face(FACE_WEIGHTS if override is None else {k: 1.0 for k in VISIBLE})
        nrm, t1, t2 = crush.FACES[face]
        ext = np.ptp(v, axis=0)
        radius = float(np.sort(ext)[1]) * 0.5
        uv = faces.pick_uv(face, radius, spread=0.2 if head else 0.82)
        q = crush.orient(rng, d.hero, nrm, tilt=0.2 if head else 0.35)
        if head:
            poke, depth, layer = rng.uniform(0.004, 0.01), 0.07, 0.004
        elif d.big:
            poke, depth, layer = rng.uniform(0.01, 0.04), rng.uniform(0.05, 0.08), rng.uniform(-0.003, 0.0)
        else:
            poke, depth, layer = rng.uniform(0.003, 0.012), rng.uniform(0.04, 0.09), rng.uniform(0.0, 0.003)
        if override:
            poke, layer = rng.uniform(0.0, 0.008), 0.005
        v = crush.place(v, q, nrm, uv, t1, t2, poke, depth)
        v = crush.compact(v, layer, r["seed"] + rank, strength=inten)
        crush.set_verts(ob.data, v)
        objs.append(ob)

    if r["crypto"]:
        d = reg[r["crypto"]]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.14, rng)
        v = damage(v, rng, inten * 0.6, brittle=d.name == "diamond", keep_shape=True)
        face = VISIBLE[int(rng.integers(0, 3))]
        nrm, t1, t2 = crush.FACES[face]
        uv = faces.pick_uv(face, 0.03, spread=0.7)
        q = crush.orient(rng, d.hero, nrm, tilt=0.8)
        v = crush.place(v, q, nrm, uv, t1, t2, rng.uniform(-0.002, 0.004), 0.2)
        v = crush.compact(v, 0.006, r["seed"] + 999, strength=inten * 0.5)
        crush.set_verts(ob.data, v)
        objs.append(ob)

    fill_faces = {"-Y": 1.0, "+X": 1.0, "+Z": 1.0, "+Y": 0.7, "-X": 0.7}
    for k, name in enumerate(r["fillers"]):
        d = reg[name]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.09, rng)
        if v is None:
            continue
        brittle = name in ("glass_shard", "bottle_cap", "spring")
        if name in ("crumpled_paper", "receipt", "fabric_scrap", "gum_wrapper", "plastic_film"):
            v = crush.crumple(v, rng, 3.0)
        v = damage(v, rng, inten, brittle)
        face = faces.pick_face(fill_faces)
        nrm, t1, t2 = crush.FACES[face]
        uv = rng.uniform(-0.95, 0.95, 2) * H
        q = crush.orient(rng, (0, 0, 1), nrm, tilt=1.2)
        sheet = name in ("housing_fragment", "packaging", "plastic_film", "cardboard_scrap", "pcb_chunk")
        q = crush.orient(rng, (0, 0, 1), nrm, tilt=0.5) if sheet else q
        poke = rng.uniform(0.006, 0.02) if sheet else rng.uniform(-0.008, 0.012)
        v = crush.place(v, q, nrm, uv, t1, t2, poke, 0.06)
        layer = rng.uniform(-0.008, -0.002) if sheet else rng.uniform(-0.005, 0.002)
        v = crush.compact(v, layer, r["seed"] + 500 + k, strength=inten)
        crush.set_verts(ob.data, v)
        objs.append(ob)

    if r["tape_loops"]:
        objs.append(dressing.tape_ribbon(coll, rng, r["tape_loops"]))
    objs.append(dressing.wires(coll, rng, r["wires"]))
    if r["condition"] == "BIOHAZARD":
        objs.append(dressing.goo(coll, rng, int(rng.integers(6, 12))))
    if r["condition"] == "SOAKED":
        objs.append(dressing.droplets(coll, rng, int(rng.integers(40, 90))))
    for j, x in enumerate(r["straps"]):
        objs.append(dressing.strap(coll, rng, x, r["condition"], stamp_text=f"{r['id']:04d}" if j == 0 else None))
    return objs


def build_empty(r, coll, rng):
    objs = []
    for j, x in enumerate(r["straps"]):
        objs.append(dressing.strap(coll, rng, x, r["condition"], stamp_text=f"{r['id']:04d}" if j == 0 else None,
                                   empty=True))
    return objs


def build_pile(r, coll, rng):
    """UNCRUSHED: the pile as it was, sitting where the block should be."""
    reg = load()
    pal = Palette(r["era_index"], rng)
    names = list(r["heroes"]) + ([r["crypto"]] if r["crypto"] else []) + list(r["fillers"][:14])
    names.sort(key=lambda n: not reg[n].big)
    grid = 48
    ext_xy = 0.36
    hmap = np.zeros((grid, grid))
    objs = []
    for name in names:
        d = reg[name]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.22 if d.big else 0.16, rng)
        if v is None:
            continue
        if d.group == "filler" and name in ("crumpled_paper", "receipt", "fabric_scrap"):
            v = crush.crumple(v, rng, 2.0)
        R = np.array(Euler(rng.uniform(0, 2 * math.pi, 3)).to_matrix())
        v = v @ R.T
        # drop it onto the heap
        rad = rng.uniform(0, 0.2) ** 1.0
        ang = rng.uniform(0, 2 * math.pi)
        cx, cy = rad * math.cos(ang) - 0.02, rad * math.sin(ang) * 0.8 + 0.03
        v[:, 0] += cx - v[:, 0].mean()
        v[:, 1] += cy - v[:, 1].mean()
        ix = np.clip(((v[:, 0] + ext_xy) / (2 * ext_xy) * grid).astype(int), 0, grid - 1)
        iy = np.clip(((v[:, 1] + ext_xy) / (2 * ext_xy) * grid).astype(int), 0, grid - 1)
        base = hmap[ix, iy].max()
        v[:, 2] += base - v[:, 2].min() - 0.01 * (base > 0)
        np.maximum.at(hmap, (ix, iy), v[:, 2])
        crush.set_verts(ob.data, v)
        ob.location.z = 0.0
        objs.append(ob)
    # the straps, cut and discarded in front of the pile
    for j in range(2):
        b = Builder("cut_strap")
        rings = []
        x0, y0 = rng.uniform(-0.25, 0.1), -0.27 + j * 0.05
        a0 = rng.uniform(-0.4, 0.4)
        for i in range(40):
            t = i / 39
            x = x0 + math.cos(a0) * t * 0.4
            y = y0 + math.sin(a0) * t * 0.4 + 0.02 * math.sin(t * 7 + j)
            z = 0.0011 + 0.03 * max(0, math.sin(t * math.pi * 1.3 - 0.3)) ** 3
            w = crush.STRAP_W
            n = Vector((-math.sin(a0), math.cos(a0), 0))
            p = Vector((x, y, z))
            rings.append([p - n * w / 2, p + n * w / 2, p + n * w / 2 + Vector((0, 0, 0.0022)),
                          p - n * w / 2 + Vector((0, 0, 0.0022))])
        b.loft(rings, mat="steel")
        ob = b.build(coll)
        ob.data.materials.append(mat.get(("rust", {"amount": 0.6}), rng))
        crush.store_rest(ob.data, crush.verts(ob.data))
    return objs


def build(r, res=1024, samples=96, turntable=0):
    sc = stage.reset()
    rng = np.random.default_rng(r["seed"])
    one = r.get("one_of_one")
    cond = r["condition"] if not one else ("CLEAN" if one == "SOLID GOLD" else "JUNK")
    mat.set_condition(cond, r["clean"][1] if r["clean"] else None, glow=3.0 if one == "SCREEN TIME" else None)
    stage.build(sc, rng, res, samples)
    coll = bpy.data.collections.new("block")
    sc.collection.children.link(coll)

    if r["condition"] == "EMPTY":
        build_empty(r, coll, rng)
    elif r["condition"] == "UNCRUSHED":
        build_pile(r, coll, rng)
        return sc
    else:
        build_block(r, coll, rng)

    pivot = bpy.data.objects.new("pivot", None)
    sc.collection.objects.link(pivot)
    for ob in coll.objects:
        ob.location.z += LIFT
        ob.parent = pivot
    if turntable:
        sc.frame_start, sc.frame_end = 1, turntable
        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert("rotation_euler", index=2, frame=1)
        pivot.rotation_euler = (0, 0, 2 * math.pi * turntable / (turntable))
        pivot.keyframe_insert("rotation_euler", index=2, frame=turntable + 1)
        for fc in _fcurves(pivot):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return sc


def _fcurves(ob):
    ad = ob.animation_data
    if ad is None or ad.action is None:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out
