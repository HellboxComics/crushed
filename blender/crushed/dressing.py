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
    b = Builder(name)
    b.loft(rings, mat="steel")
    # crimp seal on the front face
    seal_z = rng.uniform(-0.06, 0.06)
    b.box((w + 0.006, 0.006, 0.05), loc=(x, -half - 0.003, seal_z), mat="seal", bevel=0.001)
    for dz in (-0.013, 0.013):
        b.box((w + 0.008, 0.0035, 0.006), loc=(x, -half - 0.0065, seal_z + dz), mat="seal", bevel=0.0008)
    slots = ["steel", "seal"]
    specs = {"steel": ("rust", {"amount": 0.35 if cond == "CLEAN" else 0.9 if cond == "SOAKED" else 0.6,
                                "base": (0.2, 0.18, 0.2) if cond == "BURNT" else (0.42, 0.42, 0.44)}),
             "seal": ("rust", {"amount": 0.3, "base": (0.5, 0.5, 0.52)})}
    if stamp_text:
        b.plane(0.04, 0.012, loc=(x, -half - 0.0061, seal_z), rot=(math.pi / 2, 0, math.pi / 2), mat="stamp", cuts=2)
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


def wires(coll, rng, count, faces=("-Y", "+X", "+Z", "+Y", "-X")):
    b = Builder("wires")
    cols = ["w0", "w1", "w2", "w3"]
    for k in range(count):
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
