"""Assemble one token's scene from its recipe."""
import math

import bpy
import numpy as np
from mathutils import Euler, Vector

from . import crush, dressing, mat, stage, tex
from .geo import Builder
from .objects import PALETTES, Palette, load
from .recipe import WIRED
from .stage import H

LIFT = H + 0.004           # center height of the block above the floor

# how much of a baler it is: strata = how many pressed layers show on the sides, ram = how flat the top-down press
# squashes things on the sides, borrow = how many of the layers are made of this block's own stuff (its wrappers,
# its plastics) instead of plain card and paper. 0/0 is the old "pressed into the core" look.
BALE = {"strata": 0.55, "ram": 0.6, "borrow": 0.75}      # option C, pending the pick

# every side but the bottom gets covered: the block turns in 3D, so there is no back
FACE_WEIGHTS = {"-Y": 0.23, "+X": 0.22, "+Z": 0.21, "+Y": 0.17, "-X": 0.17}
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
    """keep_shape: recognizable objects get dented and bent, not destroyed."""
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
    pal = Palette(era, rng)
    crush.STRAPS = r["straps"]
    faces = Faces(rng)
    objs = []
    anchors = []            # where the corded things ended up: loose wires come out there

    # the dense undifferentiated mass behind everything
    # the base everything is crushed into: CCFF00, so a gap reads as the brand, never as a hole
    core_pal = [(0.8, 1.0, 0.0), (0.62, 0.8, 0.0), (0.7, 0.9, 0.0), (0.5, 0.66, 0.0)]
    if r["clean"]:
        c = r["clean"][1][1].get("color", (1.0, 0.78, 0.34) if r["clean"][1][0] == "gold" else (0.8, 0.8, 0.8))
        core_pal = [tuple(x * k for x in c) for k in (0.5, 0.7, 0.85, 1.0)]
    if r.get("core"):
        core_pal = [tuple(c) for c in r["core"]]
    objs.append(dressing.core(coll, rng, core_pal, r["seed"]))
    soft = r.get("soft", 1.0)
    inten = r["intensity"]

    def kz_for(lo, hi, floor=0.3):
        """How flat the ram presses a thing on a side: harder in the later, more crushed blocks."""
        k = rng.uniform(lo, hi) - 0.18 * (inten - 0.75)
        return float(np.clip(1 - (1 - k) * soft * BALE["ram"], floor, 1.0))

    # the headliner goes front and center; then big things (the back layer); then the rest
    rest = sorted(range(1, len(r["heroes"])), key=lambda i: not reg[r["heroes"][i]].big)
    order = ([0] if r["heroes"] else []) + rest
    for rank, i in enumerate(order):
        d = reg[r["heroes"][i]]
        head = i == 0
        override = ("gold", {}) if r["gold_index"] == i else None
        ob = make_object(d, rng, pal, coll, override)
        limit = rng.uniform(0.15, 0.21) if d.big else 0.17
        if head or override:
            limit = 0.21 if d.big else 0.19
        v = prepare(ob, limit, rng)
        if v is None:
            continue
        v = damage(v, rng, inten * (0.6 if head or override else 1.0) * r.get("soft", 1.0),
                   keep_shape=head or override or not d.big)
        if head:
            face = "-Y"
        elif override:
            face = "-Y" if rng.random() < 0.5 else "+X"
        else:
            face = faces.pick_face(FACE_WEIGHTS)
        nrm, t1, t2 = crush.FACES[face]
        ext = np.ptp(v, axis=0)
        radius = float(np.sort(ext)[1]) * 0.5
        uv = faces.pick_uv(face, radius, spread=0.2 if head else 0.55 if override else 0.82)
        q = crush.orient(rng, d.hero, nrm, tilt=0.2 if head else 0.35, upright=head and "upright" in d.tags)
        if head:
            poke, depth, layer = rng.uniform(0.004, 0.01), 0.07, 0.004
        elif d.big:
            poke, depth, layer = rng.uniform(0.01, 0.04), rng.uniform(0.05, 0.08), rng.uniform(-0.003, 0.0)
        else:
            poke, depth, layer = rng.uniform(0.003, 0.012), rng.uniform(0.04, 0.09), rng.uniform(0.0, 0.003)
        if override:
            poke, layer = rng.uniform(0.0, 0.008), 0.005
        v = crush.place(v, q, nrm, uv, t1, t2, poke, depth)
        v = crush.ram(v, nrm, t1, kz_for(0.62, 0.8, 0.6) if head or override else kz_for(0.42, 0.66))
        v = crush.compact(v, layer, r["seed"] + rank, margin=0.008, strength=inten)
        crush.set_verts(ob.data, v)
        objs.append(ob)
        if d.name in WIRED:
            anchors.append(tuple(v.mean(axis=0)))

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

    fill_faces = {"-Y": 1.0, "+X": 1.0, "+Z": 1.0, "+Y": 0.9, "-X": 0.9}
    for k, name in enumerate(r["fillers"]):
        d = reg[name]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.12, rng)
        if v is None:
            continue
        brittle = name in ("glass_shard", "bottle_cap", "spring")
        if name in ("crumpled_paper", "receipt", "fabric_scrap", "gum_wrapper", "plastic_film"):
            v = crush.crumple(v, rng, 3.0)
        v = damage(v, rng, inten * r.get("soft", 1.0), brittle)
        face = faces.pick_face(fill_faces)
        nrm, t1, t2 = crush.FACES[face]
        uv = rng.uniform(-0.95, 0.95, 2) * H
        q = crush.orient(rng, (0, 0, 1), nrm, tilt=1.2)
        sheet = name in ("housing_fragment", "packaging", "plastic_film", "cardboard_scrap", "pcb_chunk")
        q = crush.orient(rng, (0, 0, 1), nrm, tilt=0.5) if sheet else q
        poke = rng.uniform(0.006, 0.02) if sheet else rng.uniform(-0.008, 0.012)
        v = crush.place(v, q, nrm, uv, t1, t2, poke, 0.06)
        v = crush.ram(v, nrm, t1, kz_for(0.32, 0.55, 0.25))
        layer = rng.uniform(-0.003, 0.001) if sheet else rng.uniform(-0.002, 0.003)     # on top of the base, not under it
        v = crush.compact(v, layer, r["seed"] + 500 + k, strength=inten)
        crush.set_verts(ob.data, v)
        objs.append(ob)

    # the layers a baler leaves: everything unnameable pressed into stacked sheets, edge-on at every side. Most of
    # them are this block's own stuff (its wrappers, its plastics), the rest plain card and paper.
    if BALE["strata"] > 0 and not r["clean"] and r.get("one_of_one") not in ("CCFF00", "SOLID GOLD"):
        own = []
        for ob in objs[1:]:
            for m in ob.data.materials:
                if m and m not in own and not m.name.startswith(("core", "gold")):
                    own.append(m)
        prints = [tex.can_print(rng, "st_a"), tex.sticker(rng, "st_b", lines=3), tex.notebook(rng, "st_c")]
        objs.append(dressing.strata(coll, rng, pal, r["seed"] + 77, inten,
                                    per_side=int((46 + 26 * inten) * BALE["strata"]), prints=prints,
                                    borrow=own, borrow_share=BALE["borrow"]))

    top = []
    if r["tape_loops"]:
        top.append(dressing.tape_ribbon(coll, rng, r["tape_loops"]))
    top.append(dressing.wires(coll, rng, r["wires"], anchors=anchors))
    if r["condition"] == "BIOHAZARD":
        top.append(dressing.goo(coll, rng, int(rng.integers(6, 12))))
    if r["condition"] == "SOAKED":
        top.append(dressing.droplets(coll, rng, int(rng.integers(40, 90))))
    for ob in top:                     # tape, wires and goo all go under the straps too
        if len(ob.data.vertices):
            crush.set_verts(ob.data, crush.under_straps(crush.verts(ob.data)))
    objs += top
    for j, x in enumerate(r["straps"]):
        objs.append(dressing.strap(coll, rng, x, "CLEAN" if r["clean"] else r["condition"],
                                   stamp_text=f"{r['id']:04d}" if j == 0 else None))
    return objs


def build_empty(r, coll, rng):
    """The straps, holding absolutely nothing. A few crumbs where the block used to be."""
    reg = load()
    pal = Palette(r["era_index"], rng)
    for k in range(22):
        d = reg[str(rng.choice(["plastic_shard", "crumpled_paper", "glass_shard", "wire_bit", "foam_chunk",
                                "bottle_cap", "receipt"]))]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.035, rng)
        v = crush.crumple(v, rng, 1.0)
        v = v - v.mean(axis=0)
        R = np.array(Euler((rng.normal(0, 0.2), rng.normal(0, 0.2), rng.uniform(0, 6.3))).to_matrix())
        v = v @ R.T
        v[:, 2] -= v[:, 2].min() + LIFT - 0.0005
        v[:, :2] += rng.uniform(-0.8, 0.8, 2) * H
        crush.set_verts(ob.data, v)
    objs = []
    for j, x in enumerate(r["straps"]):
        objs.append(dressing.strap(coll, rng, x, r["condition"], stamp_text=f"{r['id']:04d}" if j == 0 else None,
                                   empty=True))
    return objs


def build_sealed(coll, rng):
    """Pre-reveal: a block under black shrink-wrap. Every token looks like this until reveal."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2 * H * 0.99)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=60, use_grid_fill=True)
    me = bpy.data.meshes.new("wrap")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("wrap", me)
    coll.objects.link(ob)
    v = crush.verts(me)
    crush.store_rest(me, v)
    from . import noise
    lumps = noise.fbm(v, 1.0 / 0.07, 4, 99) * 0.012 + noise.fbm(v, 1.0 / 0.02, 2, 5) * 0.003
    dirn = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    v = v + dirn * lumps[:, None]
    v = crush.compact(v, 0.002, 7, strength=0.4)
    crush.set_verts(me, v)
    me.shade_smooth()
    me.materials.append(mat.get(("wrap", {"keep": True}), rng))
    crush.STRAPS = [-0.082, 0.082]
    for j, x in enumerate(crush.STRAPS):
        dressing.strap(coll, rng, x, "JUNK", stamp_text="????" if j == 0 else None)


def _funnel(coll, center, r0=0.16, r1=0.34, h=0.5, seg=24):
    """An invisible bin the pile is dumped into, so it heaps instead of scattering."""
    import bmesh
    bm = bmesh.new()
    lo = [bm.verts.new((r0 * math.cos(2 * math.pi * i / seg), r0 * math.sin(2 * math.pi * i / seg), 0.0))
          for i in range(seg)]
    hi = [bm.verts.new((r1 * math.cos(2 * math.pi * i / seg), r1 * math.sin(2 * math.pi * i / seg), h))
          for i in range(seg)]
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    me = bpy.data.meshes.new("funnel")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("funnel", me)
    ob.location = (center[0], center[1], 0.0)
    coll.objects.link(ob)
    return ob


def _settle(sc, objs, floor, frames=260, walls=None, release=120):
    """Drop everything and let Bullet sort it out, then bake the resting transforms."""
    vl = bpy.context.view_layer
    bpy.ops.rigidbody.world_add()
    rbw = sc.rigidbody_world
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = frames
    rbw.substeps_per_frame = 12
    rbw.solver_iterations = 20
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.rigidbody.objects_add(type="ACTIVE")
    for o in objs:
        rb = o.rigid_body
        rb.collision_shape = "CONVEX_HULL"
        rb.friction = 0.9
        rb.restitution = 0.02
        rb.linear_damping = 0.5
        rb.angular_damping = 0.9
        rb.collision_margin = 0.001
        o.select_set(False)
    passive = [floor] + ([walls] if walls else [])
    for o in passive:
        o.select_set(True)
    vl.objects.active = floor
    bpy.ops.rigidbody.objects_add(type="PASSIVE")
    for o in passive:
        o.rigid_body.collision_shape = "MESH"
        o.rigid_body.friction = 1.0
    if walls:
        # hold the heap together, then open the bin slowly so it slumps into a mound
        walls.rigid_body.kinematic = True
        walls.scale = (1, 1, 1)
        walls.keyframe_insert("scale", frame=release)
        walls.scale = (3.5, 3.5, 1)
        walls.keyframe_insert("scale", frame=release + 60)
    for f in range(1, frames + 1):
        sc.frame_set(f)
    rest = {o.name: o.matrix_world.copy() for o in objs}
    for o in vl.objects:
        o.select_set(o in objs or o in passive)
    bpy.ops.rigidbody.objects_remove()
    bpy.ops.rigidbody.world_remove()
    sc.frame_set(1)
    for o in objs:
        o.matrix_world = rest[o.name]
    if walls:
        bpy.data.objects.remove(walls)


def build_pile(r, coll, rng):
    """UNCRUSHED: the pile as it was, sitting where the block should be."""
    reg = load()
    pal = Palette(r["era_index"], rng)
    names = list(r["heroes"]) + ([r["crypto"]] if r["crypto"] else []) + list(r["fillers"][:14])
    names.sort(key=lambda n: not reg[n].big)
    objs = []
    n = len(names)
    for i, name in enumerate(names):
        d = reg[name]
        ob = make_object(d, rng, pal, coll)
        v = prepare(ob, 0.22 if d.big else 0.16, rng)
        if v is None:
            continue
        if d.group == "filler" and name in ("crumpled_paper", "receipt", "fabric_scrap", "plastic_film"):
            v = crush.crumple(v, rng, 2.0)
        v = v - (v.min(axis=0) + v.max(axis=0)) / 2
        crush.set_verts(ob.data, v)
        # golden-spiral drop points, staggered so they land one after another; the heap sits
        # a little back from the block's footprint so it's centered in the same frame
        a = i * 2.39996
        rad = 0.01 + 0.13 * math.sqrt(i / max(n - 1, 1))
        cx, cy = -0.07, 0.09
        ob.location = (cx + rad * math.cos(a), cy + rad * math.sin(a), 0.12 + i * 0.03)
        if d.big:
            # big things land showing their good side to the camera
            toward = Vector((math.sin(stage.AZIMUTH), -math.cos(stage.AZIMUTH), 0.9)).normalized()
            q = Vector(d.hero).rotation_difference(toward)
            ob.rotation_euler = q.to_euler()
            ob.location.z = 0.14 + i * 0.02
        else:
            ob.rotation_euler = tuple(rng.uniform(0, 2 * math.pi, 3))
        objs.append(ob)
    walls = _funnel(coll, (-0.07, 0.09))
    _settle(bpy.context.scene, objs, bpy.data.objects["floor"], walls=walls)
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


def build(r, res=1024, samples=96, turntable=0, look="studio"):
    sc = stage.reset()
    rng = np.random.default_rng(r["seed"])
    one = r.get("one_of_one")
    cond = r["condition"] if not one else ("CLEAN" if r["clean"] else "JUNK")
    glow = {"SCREEN TIME": 3.0, "STILL ALIVE": 2.0}.get(one)
    mat.set_condition(cond, r["clean"][1] if r["clean"] else None, glow=glow)
    tex.SCREENS_ON["on"] = one in ("SCREEN TIME", "STILL ALIVE")
    tex.ERA["i"] = r.get("era_index")          # the parody shelf stocks the brands of this block's years
    stage.build(sc, rng, res, samples, look=look)
    coll = bpy.data.collections.new("block")
    sc.collection.children.link(coll)

    if r.get("sealed"):
        build_sealed(coll, rng)
    elif r["condition"] == "EMPTY":
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
