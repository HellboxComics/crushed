"""Everything that isn't an object: the core mass, straps, tape, wires, goo."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from . import crush, mat, noise, tex
from .geo import Builder
from .stage import H

STRAP_T = 0.0022


def _assign(ob, specs, slots, rng):
    for key in slots:
        ob.data.materials.append(mat.get(specs[key], rng))


def core(coll, rng, palette, seed):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2 * H * 0.985)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=44, use_grid_fill=True)
    me = bpy.data.meshes.new("core")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("core", me)
    coll.objects.link(ob)
    v = crush.verts(me)
    crush.store_rest(me, v)
    v = crush.core_mesh(v, seed)
    crush.set_verts(me, v)
    me.shade_smooth()
    me.materials.append(mat.get(("core", {"palette": tuple(palette)}), rng))
    return ob


def _strap_path(x, half, radius, n_side=18, n_corner=8):
    """Rounded square loop in the YZ plane at X = x. Returns points, outward normals."""
    pts, nrm = [], []
    c = half - radius
    corners = [((c, c), 0.0), ((-c, c), 90.0), ((-c, -c), 180.0), ((c, -c), 270.0)]
    for i, ((cy, cz), a0) in enumerate(corners):
        for k in range(n_corner + 1):
            a = math.radians(a0 + 90.0 * k / n_corner)
            d = Vector((0, math.cos(a), math.sin(a)))
            pts.append(Vector((x, cy, cz)) + d * radius)
            nrm.append(d)
        (ny, nz), _ = corners[(i + 1) % 4]
        a = math.radians(a0 + 90.0)
        d = Vector((0, math.cos(a), math.sin(a)))
        p0 = Vector((x, cy, cz)) + d * radius
        p1 = Vector((x, ny, nz)) + d * radius
        for k in range(1, n_side):
            pts.append(p0.lerp(p1, k / n_side))
            nrm.append(d)
    return pts, nrm


def strap(coll, rng, x, cond, stamp_text=None, name="strap", empty=False):
    half = H - 0.0045 + 0.0004 if not empty else H + 0.001
    pts, nrm = _strap_path(x, half, 0.014)
    w = crush.STRAP_W
    rings = []
    X = Vector((1, 0, 0))
    for p, n in zip(pts, nrm):
        rings.append([p - X * w / 2, p + X * w / 2, p + X * w / 2 + n * STRAP_T, p - X * w / 2 + n * STRAP_T])
    rings.append([p.copy() for p in rings[0]])      # close the loop: no loose end at the seam
    b = Builder(name)
    b.loft(rings, mat="steel", cap=False)
    # the crimp seal: a thin sleeve that hugs the strap, two shallow crimps pressed into it. Nothing sticks out.
    seal_z = rng.uniform(-0.06, 0.06)
    b.box((w + 0.0016, 0.0016, 0.042), loc=(x, -half - STRAP_T - 0.0008, seal_z), mat="seal", bevel=0.0004)
    for dz in (-0.012, 0.012):
        b.box((w + 0.0018, 0.0006, 0.004), loc=(x, -half - STRAP_T - 0.0019, seal_z + dz), mat="seal", bevel=0.0002)
    slots = ["steel", "seal"]
    specs = {"steel": ("rust", {"amount": 0.12 if cond == "CLEAN" else 0.9 if cond == "SOAKED" else 0.6,
                                "base": (0.2, 0.18, 0.2) if cond == "BURNT" else (0.42, 0.42, 0.44)}),
             "seal": ("rust", {"amount": 0.3, "base": (0.5, 0.5, 0.52)})}
    if stamp_text:
        # the number plate lies flat on the face of the seal, between its two crimps (it used to stand edge-on and
        # stick out sideways like a loose tab)
        b.plane(0.03, 0.0075, loc=(x, -half - STRAP_T - 0.0018, seal_z), rot=(math.pi / 2, 0, 0), mat="stamp", cuts=2)
        slots.append("stamp")
        specs["stamp"] = ("printed", {"image": tex.stamp(rng, "stamp", stamp_text), "rough": 0.35, "metal": 1.0})
    ob = b.build(coll)
    me = ob.data
    crush.densify(me, 0.01)
    v = crush.verts(me)
    crush.store_rest(me, v)
    # hammered, not machined
    v = v + noise.fbm_vec(v, 1.0 / 0.04, 3, int(rng.integers(1 << 20))) * 0.0012
    crush.set_verts(me, v)
    me.set_sharp_from_angle(angle=math.radians(50))
    _assign(ob, specs, b.slots, rng)
    return ob


def tape_ribbon(coll, rng, loops=2, loose=True):
    b = Builder("tape")
    for L in range(loops):
        a = Vector(rng.normal(0, 1, 3)).normalized()
        e1 = a.orthogonal().normalized()
        e2 = a.cross(e1).normalized()
        n = 260
        seed = int(rng.integers(1 << 20))
        left, right = [], []
        prev = None
        lift_phase = rng.uniform(0, 2 * math.pi)
        for i in range(n + 1):
            th = 2 * math.pi * i / n
            d = e1 * math.cos(th) + e2 * math.sin(th)
            d += Vector(noise.fbm_vec(np.array([[th, L, 0.0]]), 1.5, 2, seed)[0]) * 0.25
            m = max(abs(d.x), abs(d.y), abs(d.z))
            lift = 0.0012
            if loose:
                lift += max(0.0, math.sin(th * 3 + lift_phase)) ** 8 * 0.005
            p = d / m * (H + 0.003)
            # smoothed outward normal of the cube at p
            wts = [abs(c) ** 12 for c in p]
            s = sum(wts) + 1e-12
            nrm = Vector((math.copysign(wts[0], p.x), math.copysign(wts[1], p.y), math.copysign(wts[2], p.z))) / s
            nrm.normalize()
            p = p + nrm * lift
            if prev is not None:
                t = (p - prev).normalized()
                side = nrm.cross(t).normalized()
                twist = math.sin(th * 5 + seed) * 0.6 * min(1.0, lift * 60)
                side = side * math.cos(twist) + nrm * math.sin(twist)
                wdt = 0.0042
                left.append(p - side * wdt)
                right.append(p + side * wdt)
            prev = p
        vl = [b.bm.verts.new(p) for p in left]
        vr = [b.bm.verts.new(p) for p in right]
        for i in range(len(vl) - 1):
            try:
                b.bm.faces.new((vl[i], vl[i + 1], vr[i + 1], vr[i]))
            except ValueError:
                pass
        b._tag(vl + vr, "tape")
    ob = b.build(coll)
    ob.data.materials.append(mat.get(("tape", {"keep": True}), rng))
    crush.store_rest(ob.data, crush.verts(ob.data))
    return ob


def wires(coll, rng, count, faces=("-Y", "+X", "+Z", "+Y", "-X"), anchors=None):
    """Loose wires. With `anchors` (points on the block where corded objects sit) every wire comes out next
    to one of them, so a wire always belongs to something."""
    b = Builder("wires")
    cols = ["w0", "w1", "w2", "w3"]
    for k in range(count):
        if anchors:
            a = Vector(anchors[int(rng.integers(0, len(anchors)))])
            f = max(faces, key=lambda name: a.dot(crush.FACES[name][0]))
            nrm, t1, t2 = crush.FACES[f]
            u = float(np.clip(a.dot(t1) + rng.normal(0, 0.02), -0.8 * H, 0.8 * H))
            v = float(np.clip(a.dot(t2) + rng.normal(0, 0.02), -0.8 * H, 0.8 * H))
        else:
            f = faces[rng.integers(0, len(faces))]
            nrm, t1, t2 = crush.FACES[f]
            u, v = rng.uniform(-0.8, 0.8, 2) * H
        base = nrm * H + t1 * u + t2 * v
        pts = [base - nrm * 0.03, base]
        p = base.copy()
        dirn = (nrm + t1 * rng.normal(0, 0.5) + t2 * rng.normal(0, 0.5)).normalized()
        L = rng.uniform(0.03, 0.11)
        steps = 10
        for i in range(steps):
            dirn = (dirn + Vector(rng.normal(0, 0.35, 3)) + Vector((0, 0, -0.08))).normalized()
            if (p + dirn * (L / steps)).dot(nrm) < H + 0.003:
                dirn = (dirn + nrm).normalized()
            p = p + dirn * (L / steps)
            pts.append(p.copy())
        r = rng.uniform(0.0014, 0.003)
        b.tube(pts, r, mat=cols[k % 4], seg=8)
        tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.008
        b.tube([pts[-1], tip], r * 0.5, mat="cu", seg=6)
        if rng.random() < 0.5:
            b.tube([pts[-1], tip + Vector(rng.normal(0, 0.004, 3))], r * 0.45, mat="cu", seg=6)
    ob = b.build(coll)
    pal = [(0.85, 0.1, 0.08), (0.08, 0.08, 0.08), (0.92, 0.92, 0.9), (0.95, 0.8, 0.1), (0.1, 0.35, 0.85),
           (0.2, 0.6, 0.2)]
    rng.shuffle(pal)
    specs = {c: ("plastic", {"color": pal[i], "rough": 0.35}) for i, c in enumerate(cols)}
    specs["cu"] = ("copper", {})
    _assign(ob, specs, b.slots, rng)
    crush.store_rest(ob.data, crush.verts(ob.data))
    return ob


def goo(coll, rng, count):
    b = Builder("goo")
    for _ in range(count):
        f = ["-Y", "+X", "+Y", "-X"][rng.integers(0, 4)]
        nrm, t1, t2 = crush.FACES[f]
        u = rng.uniform(-0.85, 0.85) * H
        z = rng.uniform(-0.2, 0.9) * H
        p = nrm * (H + 0.002) + t1 * u + Vector((0, 0, z))
        L = rng.uniform(0.03, 0.15)
        pts = []
        for i in range(12):
            q = p + Vector((0, 0, -L * i / 11)) + t1 * math.sin(i * 0.7) * 0.004
            pts.append(q)
        r0 = rng.uniform(0.004, 0.009)
        b.tube(pts, lambda t: r0 * (1 - 0.5 * t), mat="goo", seg=10)
        b.sphere(r0 * 0.9, loc=pts[-1], scale=(1, 1, 1.3), mat="goo", seg=12)
        b.sphere(r0 * 1.6, loc=p, scale=(1.4, 1.4, 0.6) if f in ("+Z",) else (1.3, 1.3, 1.3), mat="goo", seg=12)
    # a few blobs oozing out of the top
    for _ in range(rng.integers(2, 5)):
        u, v = rng.uniform(-0.8, 0.8, 2) * H
        b.sphere(rng.uniform(0.01, 0.022), loc=(u, v, H + 0.001), scale=(1.6, 1.3, 0.35), mat="goo", seg=16)
    ob = b.build(coll)
    ob.data.materials.append(mat.get(("goo", {}), rng))
    crush.store_rest(ob.data, crush.verts(ob.data))
    return ob


def droplets(coll, rng, count):
    b = Builder("water")
    for _ in range(count):
        f = ["-Y", "+X", "+Y", "-X", "+Z"][rng.integers(0, 5)]
        nrm, t1, t2 = crush.FACES[f]
        u, v = rng.uniform(-0.9, 0.9, 2) * H
        r = rng.uniform(0.0015, 0.005)
        p = nrm * (H + 0.001) + t1 * u + t2 * v
        b.sphere(r, loc=p, scale=(1, 1, 1), mat="w", seg=10)
    ob = b.build(coll)
    ob.data.materials.append(mat.get(("water", {}), rng))
    crush.store_rest(ob.data, crush.verts(ob.data))
    return ob


SIDES = {"-Y": ((1, 0), (0, -1)), "+Y": ((-1, 0), (0, 1)), "+X": ((0, 1), (1, 0)), "-X": ((0, -1), (-1, 0))}


def strata(coll, rng, pal, seed, inten=1.0, per_side=56, prints=(), borrow=(), borrow_share=0.0):
    """What a baler does to everything that isn't a recognizable object: presses it into thin flat layers stacked
    top to bottom. On every side of the bale you see their edges, a stripe per layer. This is what makes a bale
    read as crushed instead of stuffed."""
    from .objects import MET, P, PR, T
    b = Builder("strata")
    papers = [(0.93, 0.92, 0.86), (0.86, 0.8, 0.62), (0.95, 0.88, 0.42), (0.8, 0.84, 0.92), (0.95, 0.95, 0.95)]
    specs = {"card": ("cardboard", {}), "card2": ("cardboard", {}),
             "paper": ("paper", {"color": tuple(papers[int(rng.integers(len(papers)))])}),
             "paper2": ("paper", {"color": tuple(papers[int(rng.integers(len(papers)))])}),
             "film": T((0.25, 0.25, 0.27), 0.2), "foil": MET((0.78, 0.78, 0.8), 0.25),
             "pl1": pal.body(loud=0.6), "pl2": pal.body(loud=0.6), "pl3": P(pal.color("loud"), 0.45),
             "dark": P((0.08, 0.08, 0.09), 0.55)}
    for i, img in enumerate(prints[:3]):
        specs[f"pr{i}"] = PR(img, 0.5)
    keys = list(specs)
    weights = np.array([2.2 if k.startswith("card") else 1.6 if k.startswith("paper") else 1.2 if k.startswith("pr")
                        else 0.8 if k == "dark" else 1.0 for k in keys])
    weights /= weights.sum()
    picks = [borrow[int(i)] for i in rng.permutation(len(borrow))[:12]] if borrow else []
    for side, ((tx, ty), (nx, ny)) in SIDES.items():
        n = int(per_side * rng.uniform(0.85, 1.15))
        for _ in range(n):
            w = rng.uniform(0.05, 0.24)
            d = rng.uniform(0.02, 0.06)
            t = rng.uniform(0.0015, 0.0045)
            u = rng.uniform(-H, H)
            z = rng.uniform(-H + 0.004, H - 0.004)
            poke = rng.uniform(-0.009, -0.002)
            cx = tx * u + nx * (H - d / 2 + poke)
            cy = ty * u + ny * (H - d / 2 + poke)
            rot = (0, 0, 0) if tx else (0, 0, math.pi / 2)
            if picks and rng.random() < borrow_share:
                key = f"own{int(rng.integers(len(picks)))}"
            else:
                key = str(rng.choice(keys, p=weights))
            b.box((w, d, t), loc=(cx, cy, z), rot=rot, mat=key)
    ob = b.build(coll)
    me = ob.data
    crush.densify(me, 0.011)
    v = crush.verts(me)
    crush.store_rest(me, v)
    # pressed, not cut: the layers ripple, droop and crumple a little where they were squeezed out the sides
    v = v + noise.fbm_vec(v, 1.0 / 0.03, 3, seed) * np.array([0.002, 0.002, 0.0045]) * (0.6 + 0.6 * inten)
    v = crush.compact(v, rng.uniform(-0.006, -0.003), seed + 7, margin=0.006, strength=inten)
    crush.set_verts(me, v)
    me.set_sharp_from_angle(angle=math.radians(40))
    for key in b.slots:
        me.materials.append(picks[int(key[3:])] if key.startswith("own") else mat.get(specs[key], rng))
    return ob


def _label_pool(rng, borrow):
    """The printed labels this block's crushed packaging wears: mostly its own (the wrappers, covers and boxes of the
    things in it), the rest from its era's parody shelf."""
    from .objects import PR
    pool = list(borrow)
    makers = [tex.can_print, tex.beer_print, tex.ramen, tex.sun_label, tex.tissue_print, tex.foil_print,
              tex.matchbook_print, tex.sanitizer_label, tex.battery, tex.vape_print, tex.sticker]
    want = max(4, 10 - len(pool))
    for i in range(want):
        fn = makers[int(rng.integers(len(makers)))]
        try:
            img = fn(rng, f"pk{i}")
        except TypeError:
            continue
        pool.append(mat.get(PR(img, float(rng.uniform(0.2, 0.45)), metal=float(rng.random() < 0.6)), rng))
    return pool


def products(coll, rng, pal, seed, inten, n, borrow=()):
    """What a real bale is made of: hundreds of crushed products, every one still wearing its label. Cans pressed
    flat with the can end showing, cartons folded in on themselves, chip bags and wrappers crumpled tight. They
    tile the whole surface between the objects, so the bale reads as stuff all the way through."""
    from .objects import MET
    labels = _label_pool(rng, borrow)
    metal_end = mat.get(MET((0.82, 0.82, 0.84), 0.22), rng)
    faces = {"-Y": 1.0, "+X": 1.0, "+Z": 1.0, "+Y": 0.85, "-X": 0.85}
    keys, w = list(faces), np.array(list(faces.values()))
    w = w / w.sum()
    out = []
    for k in range(n):
        kind = rng.choice(["can", "can", "carton", "bag", "wrapper"])
        b = Builder(f"pk_{kind}")
        if kind == "can":
            r, h = rng.uniform(0.026, 0.034), rng.uniform(0.09, 0.125)
            b.lathe([(0.0, 0.0), (r * 0.82, 0.0), (r, 0.006), (r, h - 0.006), (r * 0.82, h), (0.0, h)], mat="lbl", seg=20)
            b.cyl(r * 0.8, 0.002, loc=(0, 0, h + 0.0005), mat="end", seg=20)
            hero = (0, 0, 1) if rng.random() < 0.45 else (1, 0, 0)    # end-on: the can lid ring, like a real bale
        elif kind == "carton":
            sx, sy, sz = rng.uniform(0.05, 0.11), rng.uniform(0.07, 0.15), rng.uniform(0.02, 0.05)
            b.box((sx, sy, sz), mat="lbl")
            hero = (0, 0, 1)
        elif kind == "bag":
            b.plane(rng.uniform(0.09, 0.15), rng.uniform(0.12, 0.18), mat="lbl", cuts=10)
            hero = (0, 0, 1)
        else:
            b.plane(rng.uniform(0.06, 0.11), rng.uniform(0.025, 0.045), mat="lbl", cuts=8)
            hero = (0, 0, 1)
        ob = b.build(coll)
        lab = labels[int(rng.integers(len(labels)))]
        for key in b.slots:
            ob.data.materials.append(metal_end if key == "end" else lab)
        me = ob.data
        v = crush.verts(me)
        ext = np.ptp(v, axis=0)
        s = min(1.0, rng.uniform(0.07, 0.12) / max(ext.max(), 1e-6))
        v = (v - (v.min(axis=0) + v.max(axis=0)) / 2) * s
        if kind == "bag":                                   # air still in the bag before the press
            rr = np.hypot(v[:, 0] / (np.ptp(v[:, 0]) / 2 + 1e-6), v[:, 1] / (np.ptp(v[:, 1]) / 2 + 1e-6))
            v[:, 2] += np.clip(1 - rr, 0, 1) * 0.012 * np.sign(rng.normal())
        crush.set_verts(me, v)
        crush.densify(me, 0.006)
        me.set_sharp_from_angle(angle=math.radians(35))
        v = crush.verts(me)
        crush.store_rest(me, v)
        # crushed hard: folded, crumpled, dented, every one differently
        v = crush.bend(v, rng, 0.7 * inten)
        v = crush.fold(v, rng, int(rng.integers(1, 3)), 1.2 * inten)
        v = crush.crumple(v, rng, rng.uniform(0.6, 1.3) * inten)
        v = crush.dents(v, rng, int(rng.integers(1, 5)), rng.uniform(0.004, 0.012) * inten)
        face = keys[int(rng.choice(len(keys), p=w))]
        nrm, t1, t2 = crush.FACES[face]
        q = crush.orient(rng, hero, nrm, tilt=0.55)
        uv = rng.uniform(-0.98, 0.98, 2) * H
        v = crush.place(v, q, nrm, uv, t1, t2, rng.uniform(0.0, 0.008), rng.uniform(0.018, 0.035))
        # behind the recognizable objects: the products fill around them, they never paper over them
        v = crush.compact(v, rng.uniform(-0.007, -0.0008), seed + 3000 + k, margin=0.007, strength=inten)
        crush.set_verts(me, v)
        out.append(ob)
    return out
