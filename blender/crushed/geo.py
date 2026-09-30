"""Tiny procedural modelling kit on top of bmesh.

Every object in the library is assembled from these parts in real-world
metres. A Builder collects parts into one bmesh, tracks which material slot
each part uses, and turns the result into a Blender object.
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


def xform(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return (Matrix.Translation(Vector(loc))
            @ Euler(rot).to_matrix().to_4x4()
            @ Matrix.Diagonal((*scale, 1.0)))


class Builder:
    """Accumulates parts. Material keys are resolved later by the stage."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.slots = []
        self.frame = Matrix.Identity(4)

    # -- bookkeeping ---------------------------------------------------------
    def slot(self, key):
        if key not in self.slots:
            self.slots.append(key)
        return self.slots.index(key)

    def _faces(self, verts):
        return {f for v in verts for f in v.link_faces}

    def _tag(self, verts, mat):
        idx = self.slot(mat)
        faces = self._faces(verts)
        for f in faces:
            f.material_index = idx
            f.smooth = True
        return faces

    def _m(self, loc, rot, scale=(1, 1, 1)):
        return self.frame @ xform(loc, rot, scale)

    # -- primitives ----------------------------------------------------------
    def box(self, size, loc=(0, 0, 0), rot=(0, 0, 0), mat="body", bevel=0.0, seg=2):
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=self._m(loc, rot, size), calc_uvs=True)
        verts = r["verts"]
        if bevel > 0:
            edges = list({e for v in verts for e in v.link_edges})
            b = min(bevel, min(size) * 0.49)
            res = bmesh.ops.bevel(self.bm, geom=edges + list(verts), offset=b, segments=seg,
                                  affect="EDGES", profile=0.5, clamp_overlap=True)
            verts = list(set(verts) | set(res["verts"]))
            verts = [v for v in verts if v.is_valid]
        return self._tag(verts, mat)

    def cyl(self, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat="body", seg=24, r2=None, cap=True):
        res = bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r if r2 is None else r2, depth=depth,
                                    matrix=self._m(loc, rot), calc_uvs=True)
        return self._tag(res["verts"], mat)

    def sphere(self, r, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), mat="body", seg=16):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(6, seg // 2),
                                        radius=r, matrix=self._m(loc, rot, scale), calc_uvs=True)
        return self._tag(res["verts"], mat)

    def plane(self, w, h, loc=(0, 0, 0), rot=(0, 0, 0), mat="label", cuts=4):
        """A UV-mapped (0..1) quad, used for labels, screens and prints."""
        res = bmesh.ops.create_grid(self.bm, x_segments=cuts, y_segments=cuts, size=0.5,
                                    matrix=self._m(loc, rot, (w, h, 1)), calc_uvs=True)
        return self._tag(res["verts"], mat)

    def lathe(self, profile, loc=(0, 0, 0), rot=(0, 0, 0), mat="body", seg=24, scale=(1, 1, 1)):
        """Revolve a list of (radius, z) points around local Z."""
        m = self._m(loc, rot, scale)
        rings = []
        for (rad, z) in profile:
            ring = []
            for i in range(seg):
                a = 2 * math.pi * i / seg
                ring.append(self.bm.verts.new(m @ Vector((rad * math.cos(a), rad * math.sin(a), z))))
            rings.append(ring)
        faces = []
        for j in range(len(rings) - 1):
            for i in range(seg):
                a, b = rings[j][i], rings[j][(i + 1) % seg]
                c, d = rings[j + 1][(i + 1) % seg], rings[j + 1][i]
                try:
                    faces.append(self.bm.faces.new((a, b, c, d)))
                except ValueError:
                    pass
        for k, ring in ((0, rings[0]), (-1, rings[-1])):
            if profile[k][0] > 1e-5:
                try:
                    faces.append(self.bm.faces.new(ring if k == -1 else list(reversed(ring))))
                except ValueError:
                    pass
        self._uv_cyl(faces, profile, m.inverted())
        verts = [v for r in rings for v in r]
        return self._tag(verts, mat)

    def _uv_cyl(self, faces, profile, inv):
        zs = [p[1] for p in profile]
        z0, z1 = min(zs), max(zs) + 1e-6
        for f in faces:
            for l in f.loops:
                co = inv @ l.vert.co
                l[self.uv].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, (co.z - z0) / (z1 - z0))

    def tube(self, pts, r, mat="cord", seg=8, cap=True, loc=(0, 0, 0), rot=(0, 0, 0)):
        """Sweep a circle along a polyline (cords, handles, frames, wires)."""
        m = self._m(loc, rot)
        pts = [Vector(p) for p in pts]
        n = len(pts)
        if n < 2:
            return set()
        rings = []
        prev_side = None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev_side is None:
                up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                side = t.cross(up).normalized()
            else:
                side = (prev_side - t * prev_side.dot(t)).normalized()
            prev_side = side
            up2 = t.cross(side).normalized()
            rr = r(i / (n - 1)) if callable(r) else r
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                ring.append(self.bm.verts.new(m @ (p + (side * math.cos(a) + up2 * math.sin(a)) * rr)))
            rings.append(ring)
        faces = []
        for j in range(n - 1):
            for k in range(seg):
                a, b = rings[j][k], rings[j][(k + 1) % seg]
                c, d = rings[j + 1][(k + 1) % seg], rings[j + 1][k]
                try:
                    f = self.bm.faces.new((a, d, c, b))
                    faces.append(f)
                    for l, uv in zip(f.loops, ((k / seg, j / n), (k / seg, (j + 1) / n),
                                                ((k + 1) / seg, (j + 1) / n), ((k + 1) / seg, j / n))):
                        l[self.uv].uv = uv
                except ValueError:
                    pass
        if cap:
            for ring in (list(reversed(rings[0])), rings[-1]):
                try:
                    faces.append(self.bm.faces.new(ring))
                except ValueError:
                    pass
        return self._tag([v for r in rings for v in r], mat)

    def extrude(self, poly, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat="body", scale=(1, 1, 1), bevel=0.0):
        """Extrude a 2D outline (list of (x, y)) along +Z by depth, centred."""
        m = self._m(loc, rot, scale)
        bot = [self.bm.verts.new(m @ Vector((x, y, -depth / 2))) for x, y in poly]
        top = [self.bm.verts.new(m @ Vector((x, y, depth / 2))) for x, y in poly]
        faces = []
        try:
            faces.append(self.bm.faces.new(list(reversed(bot))))
            faces.append(self.bm.faces.new(top))
        except ValueError:
            pass
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            try:
                faces.append(self.bm.faces.new((bot[i], bot[j], top[j], top[i])))
            except ValueError:
                pass
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, y0 = min(xs), min(ys)
        sx, sy = (max(xs) - x0) or 1, (max(ys) - y0) or 1
        inv = m.inverted()
        for f in faces:
            for l in f.loops:
                c = inv @ l.vert.co
                l[self.uv].uv = ((c.x - x0) / sx, (c.y - y0) / sy)
        verts = bot + top
        if bevel > 0:
            edges = list({e for v in verts for e in v.link_edges})
            res = bmesh.ops.bevel(self.bm, geom=edges + verts, offset=bevel, segments=2,
                                  affect="EDGES", profile=0.5, clamp_overlap=True)
            verts = [v for v in set(verts) | set(res["verts"]) if v.is_valid]
        return self._tag(verts, mat)

    def torus(self, R, r, loc=(0, 0, 0), rot=(0, 0, 0), mat="body", seg=24, rseg=10, arc=2 * math.pi):
        closed = arc >= 2 * math.pi - 1e-6
        n = seg if closed else seg + 1
        pts = [(R * math.cos(arc * i / seg), R * math.sin(arc * i / seg), 0) for i in range(n)]
        if closed:
            pts.append(pts[0])
        f = self.tube(pts, r, mat=mat, seg=rseg, cap=not closed, loc=loc, rot=rot)
        if closed:
            bmesh.ops.remove_doubles(self.bm, verts=list({v for fa in f for v in fa.verts}), dist=1e-6)
        return f

    def loft(self, rings, mat="body", cap=True, loc=(0, 0, 0), rot=(0, 0, 0), closed=True):
        """Skin a list of point rings (each the same length) into a surface."""
        m = self._m(loc, rot)
        vr = [[self.bm.verts.new(m @ Vector(p)) for p in ring] for ring in rings]
        k = len(rings[0])
        n = len(vr)
        for j in range(n - 1):
            for i in range(k if closed else k - 1):
                a, b = vr[j][i], vr[j][(i + 1) % k]
                c, d = vr[j + 1][(i + 1) % k], vr[j + 1][i]
                try:
                    f = self.bm.faces.new((a, b, c, d))
                    for l, uv in zip(f.loops, ((i / k, j / n), ((i + 1) / k, j / n),
                                                ((i + 1) / k, (j + 1) / n), (i / k, (j + 1) / n))):
                        l[self.uv].uv = uv
                except ValueError:
                    pass
        if cap and closed:
            for ring in (list(reversed(vr[0])), vr[-1]):
                try:
                    self.bm.faces.new(ring)
                except ValueError:
                    pass
        return self._tag([v for r in vr for v in r], mat)

    # -- output --------------------------------------------------------------
    def build(self, collection):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        collection.objects.link(ob)
        return ob


def helix(radius, pitch, turns, steps_per_turn=24, start=(0, 0, 0), axis_len=None):
    pts = []
    n = int(turns * steps_per_turn)
    for i in range(n + 1):
        a = 2 * math.pi * i / steps_per_turn
        pts.append((start[0] + radius * math.cos(a), start[1] + radius * math.sin(a),
                    start[2] + pitch * i / steps_per_turn))
    return pts


def rounded_rect(w, h, r, seg=4):
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse(w, h, seg=24):
    return [(w / 2 * math.cos(2 * math.pi * i / seg), h / 2 * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
