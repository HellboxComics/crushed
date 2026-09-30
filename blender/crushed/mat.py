"""Material factory.

Every surface is a Principled BSDF whose inputs are built from a small graph.
Textures read the "rest" attribute (the vertex position before crushing), so
prints, grain and scratches bend with the geometry instead of swimming.

A condition (JUNK / CLEAN / BURNT / SOAKED / BIOHAZARD / GOLD) is applied at
the socket level before the BSDF, so the whole block reacts consistently.
"""
import bpy

from . import tex

COND = {"name": "JUNK", "clean": None, "glow": None}


def set_condition(name, clean=None, glow=None):
    COND["name"] = name
    COND["clean"] = clean
    COND["glow"] = glow


class G:
    """Thin helper around a node tree to keep the recipes readable."""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links
        self.n.clear()
        self.out = self.n.new("ShaderNodeOutputMaterial")
        self.bsdf = self.n.new("ShaderNodeBsdfPrincipled")
        self._rest = None

    def link(self, a, b):
        self.l.new(a, b)

    def rest(self):
        if self._rest is None:
            a = self.n.new("ShaderNodeAttribute")
            a.attribute_name = "rest"
            self._rest = a.outputs["Vector"]
        return self._rest

    def world(self):
        return self.n.new("ShaderNodeNewGeometry").outputs["Position"]

    def noise(self, scale, detail=4.0, rough=0.55, vec=None, dist=0.0):
        t = self.n.new("ShaderNodeTexNoise")
        t.inputs["Scale"].default_value = scale
        t.inputs["Detail"].default_value = detail
        t.inputs["Roughness"].default_value = rough
        t.inputs["Distortion"].default_value = dist
        self.link(vec or self.rest(), t.inputs["Vector"])
        return t

    def voronoi(self, scale, feature="F1", metric="EUCLIDEAN", vec=None, rand=1.0):
        t = self.n.new("ShaderNodeTexVoronoi")
        t.feature = feature
        t.distance = metric
        t.inputs["Scale"].default_value = scale
        t.inputs["Randomness"].default_value = rand
        self.link(vec or self.rest(), t.inputs["Vector"])
        return t

    def ramp(self, src, stops, interp="LINEAR"):
        r = self.n.new("ShaderNodeValToRGB")
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position, els[0].color = stops[0][0], _rgba(stops[0][1])
        for pos, col in stops[1:]:
            e = els.new(pos)
            e.color = _rgba(col)
        self.link(src, r.inputs["Fac"])
        return r.outputs["Color"]

    def math(self, op, a, b=None, clamp=False):
        m = self.n.new("ShaderNodeMath")
        m.operation = op
        m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def maprange(self, src, a0, a1, b0=0.0, b1=1.0):
        m = self.n.new("ShaderNodeMapRange")
        m.inputs["From Min"].default_value = a0
        m.inputs["From Max"].default_value = a1
        m.inputs["To Min"].default_value = b0
        m.inputs["To Max"].default_value = b1
        self.link(src, m.inputs["Value"])
        return m.outputs["Result"]

    def mix(self, fac, a, b, blend="MIX"):
        m = self.n.new("ShaderNodeMix")
        m.data_type = "RGBA"
        m.blend_type = blend
        self._set(m.inputs[0], fac)
        self._set(m.inputs[6], a)
        self._set(m.inputs[7], b)
        return m.outputs[2]

    def mixf(self, fac, a, b):
        m = self.n.new("ShaderNodeMix")
        m.data_type = "FLOAT"
        self._set(m.inputs[0], fac)
        self._set(m.inputs[2], a)
        self._set(m.inputs[3], b)
        return m.outputs[0]

    def _set(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = _rgba(v)
        else:
            self.link(v, sock)

    def bump(self, h, strength=0.2, dist=0.002, normal=None):
        b = self.n.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = dist
        self.link(h, b.inputs["Height"])
        if normal is not None:
            self.link(normal, b.inputs["Normal"])
        return b.outputs["Normal"]

    def image(self, img, extension="EXTEND"):
        t = self.n.new("ShaderNodeTexImage")
        t.image = img
        t.extension = extension
        uv = self.n.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        self.link(uv.outputs["UV"], t.inputs["Vector"])
        return t


def _rgba(c):
    return (*c, 1.0) if len(c) == 3 else tuple(c)


def _lin(c):
    """sRGB display colour -> linear, so palettes can be written by eye."""
    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return tuple(f(x) for x in c[:3])


# ---------------------------------------------------------------------------

_CACHE = {}


def get(spec, rng):
    """spec: (kind, params-dict). Returns a bpy material (cached by spec)."""
    kind, p = spec
    clean = COND["clean"]
    if clean and kind not in ("steel", "rust", "floor", "goo", "gold", "core", "water") and not p.get("keep"):
        kind, p = clean
    key = (kind, tuple(sorted((k, str(v)) for k, v in p.items())), COND["name"])
    if key in _CACHE and not p.get("unique"):
        return _CACHE[key]
    m = bpy.data.materials.new(f"{kind}")
    g = G(m)
    fn = KINDS[kind]
    s = fn(g, p, rng)
    _finish(g, s, kind, p)
    _CACHE[key] = m
    return m


def _finish(g, s, kind, p):
    b = g.bsdf
    cond = COND["name"]
    col = s.get("color", (0.5, 0.5, 0.5))
    rough = s.get("rough", 0.5)
    metal = s.get("metal", 0.0)
    normal = s.get("normal")
    trans = s.get("trans", 0.0)
    emit = s.get("emit")
    estr = s.get("estr", 0.0)
    hard = kind in ("steel", "rust", "floor", "goo", "water")

    if kind not in ("floor", "water"):
        ao = g.n.new("ShaderNodeAmbientOcclusion")
        ao.samples = 8
        ao.inputs["Distance"].default_value = 0.025
        cav = g.maprange(ao.outputs["AO"], 0.0, 1.0, 0.2, 1.0)
        col = g.mix(g.math("SUBTRACT", 1.0, cav), col, (0.0, 0.0, 0.0))

    if kind not in ("floor", "goo") and cond != "CLEAN":
        # grime lives in the cracks and on upward faces: everything was on a floor once
        dn = g.noise(18.0, 6.0, 0.7)
        dirt = g.maprange(dn.outputs["Fac"], 0.5, 0.75, 0.0, 0.55 if cond == "JUNK" else 0.3)
        col = g.mix(dirt, col, _lin((0.23, 0.2, 0.16)), "MULTIPLY")
        rough = g.mixf(dirt, rough, 0.9)

    if cond == "BURNT" and not hard:
        w = g.world()
        n1 = g.noise(5.0, 8.0, 0.7, vec=w)
        char = g.maprange(n1.outputs["Fac"], 0.22, 0.42)
        col = g.mix(char, col, _lin((0.018, 0.015, 0.013)))
        # scorched edge band between char and surviving colour
        edge = g.math("MULTIPLY", g.maprange(n1.outputs["Fac"], 0.12, 0.22), g.maprange(n1.outputs["Fac"], 0.32, 0.22))
        col = g.mix(edge, col, _lin((0.25, 0.12, 0.04)), "MULTIPLY")
        blister = g.noise(70.0, 6.0, 0.7, vec=w)
        rough = g.mixf(char, rough, g.maprange(blister.outputs["Fac"], 0.3, 0.7, 0.35, 0.9))
        metal = g.mixf(char, metal, 0.0)
        trans = g.mixf(char, trans, 0.0)
        cr = g.voronoi(90.0, "DISTANCE_TO_EDGE", vec=w, rand=1.0)
        crack = g.maprange(cr.outputs["Distance"], 0.012, 0.0)
        hot = g.maprange(g.noise(2.5, 3.0, 0.6, vec=w).outputs["Fac"], 0.56, 0.66)
        glow = g.math("MULTIPLY", g.math("MULTIPLY", crack, hot), char)
        emit = g.mix(glow, (0, 0, 0), _lin((1.0, 0.3, 0.04)))
        estr = 9.0
        normal = g.bump(g.math("ADD", g.math("MULTIPLY", blister.outputs["Fac"], char), crack), 0.4, 0.002)
    elif cond == "SOAKED" and not hard:
        wet = g.maprange(g.noise(4.0, 3.0, 0.5, vec=g.world()).outputs["Fac"], 0.35, 0.5)
        col = g.mix(wet, col, g.mix(0.5, col, (0.0, 0.0, 0.0), "MULTIPLY"))
        col = g.mix(g.math("MULTIPLY", wet, 0.55), col, _lin((0.2, 0.22, 0.1)), "MULTIPLY")
        rough = g.mixf(wet, rough, 0.06)
        mold = g.voronoi(55.0, "SMOOTH_F1", vec=g.world())
        mn = g.noise(9.0, 5.0, 0.6, vec=g.world())
        mm = g.math("MULTIPLY", g.maprange(mold.outputs["Distance"], 0.25, 0.05),
                    g.maprange(mn.outputs["Fac"], 0.55, 0.7))
        col = g.mix(mm, col, _lin((0.78, 0.82, 0.7)))
        rough = g.mixf(mm, rough, 1.0)
        rust = g.maprange(g.noise(14.0, 6.0, 0.65).outputs["Fac"], 0.45, 0.6)
        if kind in ("metal", "chrome"):
            col = g.mix(rust, col, _lin((0.35, 0.13, 0.04)))
            metal = g.mixf(rust, metal, 0.0)
            rough = g.mixf(rust, rough, 0.9)
        normal = g.bump(mn.outputs["Fac"], 0.25, 0.002, normal)
    elif cond == "BIOHAZARD" and not hard:
        w = g.world()
        sc = g.n.new("ShaderNodeVectorMath")
        sc.operation = "MULTIPLY"
        sc.inputs[1].default_value = (4.0, 4.0, 0.6)
        g.link(w, sc.inputs[0])
        drip = g.noise(3.0, 4.0, 0.6, vec=sc.outputs[0])
        goo = g.maprange(drip.outputs["Fac"], 0.56, 0.61)
        col = g.mix(goo, col, _lin((0.45, 1.0, 0.05)))
        rough = g.mixf(goo, rough, 0.05)
        trans = g.mixf(goo, trans, 0.0)
        emit = g.mix(goo, (0, 0, 0), _lin((0.4, 1.0, 0.02)))
        estr = 1.2
        stain = g.maprange(g.noise(8.0, 5.0, 0.6, vec=w).outputs["Fac"], 0.45, 0.62, 0, 0.7)
        col = g.mix(stain, col, _lin((0.55, 0.6, 0.15)), "MULTIPLY")

    _set = g._set
    _set(b.inputs["Base Color"], col)
    _set(b.inputs["Roughness"], rough)
    _set(b.inputs["Metallic"], metal)
    _set(b.inputs["Transmission Weight"], trans)
    if "ior" in s:
        b.inputs["IOR"].default_value = s["ior"]
    if "coat" in s:
        b.inputs["Coat Weight"].default_value = s["coat"]
    if "film" in s:
        b.inputs["Thin Film Thickness"].default_value = s["film"]
    if "sss" in s:
        b.inputs["Subsurface Weight"].default_value = s["sss"]
    if "sheen" in s:
        b.inputs["Sheen Weight"].default_value = s["sheen"]
    if "alpha" in s:
        _set(b.inputs["Alpha"], s["alpha"])
    if emit is not None:
        _set(b.inputs["Emission Color"], emit)
        b.inputs["Emission Strength"].default_value = estr
    if normal is not None:
        g.link(normal, b.inputs["Normal"])
    if "fade" in s:
        # the floor falls off to true black, specular included
        black = g.n.new("ShaderNodeBsdfDiffuse")
        black.inputs["Color"].default_value = (0, 0, 0, 1)
        mx = g.n.new("ShaderNodeMixShader")
        g.link(s["fade"], mx.inputs[0])
        g.link(black.outputs[0], mx.inputs[1])
        g.link(b.outputs[0], mx.inputs[2])
        g.link(mx.outputs[0], g.out.inputs["Surface"])
    else:
        g.link(b.outputs[0], g.out.inputs["Surface"])


# -- kinds -----------------------------------------------------------------------

def _scratches(g, scale=1.0):
    """Fine directional scuffs: stretched noise, thresholded, sparse."""
    vm = g.n.new("ShaderNodeVectorMath")
    vm.operation = "MULTIPLY"
    vm.inputs[1].default_value = (600.0 * scale, 18.0 * scale, 18.0 * scale)
    g.link(g.rest(), vm.inputs[0])
    t = g.n.new("ShaderNodeTexNoise")
    t.inputs["Scale"].default_value = 1.0
    t.inputs["Detail"].default_value = 2.0
    g.link(vm.outputs[0], t.inputs["Vector"])
    lines = g.maprange(t.outputs["Fac"], 0.68, 0.76)
    mask = g.maprange(g.noise(6.0, 2.0, 0.5).outputs["Fac"], 0.5, 0.65)
    return g.math("MULTIPLY", lines, mask)


def plastic(g, p, rng):
    c = _lin(p.get("color", (0.8, 0.78, 0.7)))
    n = g.noise(90.0, 3.0, 0.5)
    col = g.mix(g.maprange(n.outputs["Fac"], 0.3, 0.7, 0, 0.08), c, (0, 0, 0))
    scratch = _scratches(g)
    rough = g.mixf(scratch, p.get("rough", 0.38), 0.7)
    col = g.mix(g.math("MULTIPLY", scratch, 0.3), col, (0.9, 0.9, 0.9), "SCREEN")
    tex_ = p.get("texture", 0.15)
    normal = g.bump(g.math("ADD", g.math("MULTIPLY", n.outputs["Fac"], tex_), scratch), 0.1, 0.001)
    return {"color": col, "rough": rough, "normal": normal, "coat": p.get("coat", 0.0)}


def translucent(g, p, rng):
    c = _lin(p.get("color", (0.4, 0.1, 0.7)))
    scratch = _scratches(g)
    rough = g.mixf(scratch, p.get("rough", 0.12), 0.5)
    return {"color": c, "rough": rough, "trans": 1.0, "ior": 1.49,
            "normal": g.bump(scratch, 0.1, 0.001)}


def rubber(g, p, rng):
    c = _lin(p.get("color", (0.06, 0.06, 0.06)))
    n = g.noise(200.0, 2.0, 0.5)
    return {"color": c, "rough": 0.85, "normal": g.bump(n.outputs["Fac"], 0.2, 0.0005)}


def metal(g, p, rng):
    c = _lin(p.get("color", (0.75, 0.75, 0.76)))
    n = g.noise(60.0, 6.0, 0.6)
    scratch = _scratches(g, 1.5)
    rough = g.mixf(scratch, p.get("rough", 0.3), 0.12)
    rough = g.math("ADD", rough, g.maprange(n.outputs["Fac"], 0.3, 0.7, -0.08, 0.12))
    return {"color": c, "rough": rough, "metal": 1.0,
            "normal": g.bump(g.math("ADD", n.outputs["Fac"], scratch), 0.1, 0.001)}


def chrome(g, p, rng):
    return metal(g, {"color": p.get("color", (0.95, 0.95, 0.96)), "rough": p.get("rough", 0.08)}, rng)


def gold(g, p, rng):
    return metal(g, {"color": (1.0, 0.78, 0.34), "rough": p.get("rough", 0.18)}, rng)


def glass(g, p, rng):
    c = _lin(p.get("color", (0.85, 0.9, 0.9)))
    v = g.voronoi(p.get("crack_scale", 12.0), "DISTANCE_TO_EDGE")
    crack = g.maprange(v.outputs["Distance"], 0.02, 0.0)
    return {"color": g.mix(crack, c, (1, 1, 1)), "rough": g.mixf(crack, p.get("rough", 0.02), 0.4),
            "trans": p.get("trans", 1.0), "ior": 1.5, "normal": g.bump(crack, 0.6, 0.002)}


def screen(g, p, rng):
    img = p["image"]
    t = g.image(img)
    v = g.voronoi(p.get("crack_scale", 10.0), "DISTANCE_TO_EDGE")
    crack = g.maprange(v.outputs["Distance"], 0.025, 0.0)
    col = g.mix(crack, g.mix(0.6, t.outputs["Color"], (0.02, 0.02, 0.02), "MULTIPLY"), (0.8, 0.8, 0.8))
    return {"color": col, "rough": g.mixf(crack, 0.05, 0.5), "coat": 1.0,
            "emit": t.outputs["Color"], "estr": COND["glow"] or p.get("glow", 0.0),
            "normal": g.bump(crack, 0.8, 0.002)}


def printed(g, p, rng):
    """Image on UVs: labels, stickers, cans, packets, keypads."""
    t = g.image(p["image"], p.get("ext", "EXTEND"))
    n = g.noise(120.0, 2.0, 0.5)
    col = t.outputs["Color"]
    if p.get("fade", 0) > 0:
        col = g.mix(p["fade"], col, (0.9, 0.88, 0.8))
    s = {"color": col, "rough": p.get("rough", 0.45), "metal": p.get("metal", 0.0),
         "normal": g.bump(n.outputs["Fac"], 0.1, 0.0005)}
    if p.get("alpha_from_image"):
        s["alpha"] = t.outputs["Alpha"]
    return s


def paper(g, p, rng):
    c = _lin(p.get("color", (0.93, 0.92, 0.88)))
    n = g.noise(30.0, 8.0, 0.6)
    fold = g.voronoi(12.0, "DISTANCE_TO_EDGE")
    crease = g.maprange(fold.outputs["Distance"], 0.03, 0.0)
    col = g.mix(g.math("MULTIPLY", crease, 0.4), c, (0.3, 0.28, 0.25), "MULTIPLY")
    return {"color": col, "rough": 0.9, "sheen": 0.3,
            "normal": g.bump(g.math("ADD", n.outputs["Fac"], crease), 0.4, 0.001)}


def cardboard(g, p, rng):
    c = _lin(p.get("color", (0.62, 0.47, 0.3)))
    w = g.n.new("ShaderNodeTexWave")
    w.inputs["Scale"].default_value = 120.0
    g.link(g.rest(), w.inputs["Vector"])
    n = g.noise(25.0, 6.0, 0.6)
    col = g.mix(g.maprange(n.outputs["Fac"], 0.3, 0.7, 0, 0.3), c, (0.3, 0.22, 0.12))
    return {"color": col, "rough": 0.92, "normal": g.bump(w.outputs["Fac"], 0.08, 0.001)}


def foam(g, p, rng):
    c = _lin(p.get("color", (0.95, 0.75, 0.2)))
    v = g.voronoi(300.0, "F1")
    return {"color": c, "rough": 1.0, "sss": 0.3, "normal": g.bump(v.outputs["Distance"], 0.6, 0.002)}


def fabric(g, p, rng):
    c = _lin(p.get("color", (0.9, 0.9, 0.9)))
    w = g.n.new("ShaderNodeTexWave")
    w.inputs["Scale"].default_value = 400.0
    w.inputs["Distortion"].default_value = 2.0
    g.link(g.rest(), w.inputs["Vector"])
    n = g.noise(20.0, 6.0, 0.6)
    col = g.mix(g.maprange(n.outputs["Fac"], 0.3, 0.8, 0, 0.3), c, (0.2, 0.18, 0.15), "MULTIPLY")
    return {"color": col, "rough": 0.95, "sheen": 0.6, "normal": g.bump(w.outputs["Fac"], 0.25, 0.0008)}


def tape(g, p, rng):
    return {"color": _lin((0.12, 0.07, 0.04)), "rough": 0.15, "metal": 0.3}


def disc(g, p, rng):
    """Optical media: silver, green-gold or blue data side, with thin-film sheen."""
    c = _lin(p.get("color", (0.82, 0.82, 0.85)))
    n = g.noise(40.0, 3.0, 0.5)
    return {"color": c, "rough": 0.06, "metal": 1.0, "film": p.get("film", 520.0),
            "normal": g.bump(n.outputs["Fac"], 0.05, 0.0005)}


def wax(g, p, rng):
    return {"color": _lin(p.get("color", (0.9, 0.1, 0.1))), "rough": 0.35, "sss": 0.4}


def crust(g, p, rng):
    n = g.noise(35.0, 8.0, 0.65)
    col = g.ramp(n.outputs["Fac"], [(0.3, (0.35, 0.16, 0.05)), (0.55, (0.7, 0.45, 0.2)), (0.7, (0.85, 0.65, 0.35))])
    return {"color": col, "rough": 0.7, "sss": 0.1, "normal": g.bump(n.outputs["Fac"], 0.6, 0.003)}


def pcb(g, p, rng):
    t = g.image(p["image"], "REPEAT")
    return {"color": t.outputs["Color"], "rough": 0.3, "coat": 0.5}


def copper(g, p, rng):
    return metal(g, {"color": (0.95, 0.55, 0.35), "rough": 0.25}, rng)


def steel(g, p, rng):
    n = g.noise(30.0, 6.0, 0.6)
    return {"color": g.mix(g.maprange(n.outputs["Fac"], 0.3, 0.7), _lin((0.5, 0.5, 0.52)), _lin((0.35, 0.36, 0.38))),
            "rough": 0.4, "metal": 1.0, "normal": g.bump(n.outputs["Fac"], 0.1, 0.001)}


def rust(g, p, rng):
    """Strap steel: bare metal under patchy orange-brown scale."""
    amt = p.get("amount", 0.55)
    n = g.noise(9.0, 8.0, 0.7)
    fine = g.noise(90.0, 6.0, 0.7)
    mask = g.maprange(g.math("ADD", n.outputs["Fac"], g.math("MULTIPLY", fine.outputs["Fac"], 0.35)),
                      0.8 - amt * 0.3, 0.88 - amt * 0.3)
    rc = g.ramp(fine.outputs["Fac"], [(0.3, _lin((0.12, 0.05, 0.025))), (0.5, _lin((0.3, 0.11, 0.035))),
                                      (0.62, _lin((0.55, 0.22, 0.05))), (0.75, _lin((0.2, 0.08, 0.03)))])
    base = p.get("base", (0.42, 0.42, 0.44))
    stain = g.maprange(g.noise(30.0, 4.0, 0.6).outputs["Fac"], 0.4, 0.7, 0.0, 0.6)
    col = g.mix(mask, g.mix(stain, _lin(base), _lin((0.12, 0.1, 0.09))), rc)
    return {"color": col, "metal": g.mixf(mask, 1.0, 0.0), "rough": g.mixf(mask, 0.35, 0.9),
            "normal": g.bump(g.math("ADD", fine.outputs["Fac"], mask), 0.35, 0.0015)}


def core(g, p, rng):
    """The compressed mass visible between recognisable objects: deep, dark, dense.
    Nearly black, with just enough glint to read as more crushed stuff."""
    pal = p["palette"]
    n = g.noise(60.0, 8.0, 0.75)
    stops = [(i / len(pal), tuple(x * 0.05 for x in _lin(c))) for i, c in enumerate(pal)]
    col = g.ramp(g.voronoi(45.0, "F1").outputs["Color"], stops, "CONSTANT")
    col = g.mix(g.maprange(n.outputs["Fac"], 0.45, 0.7), (0.0, 0.0, 0.0), col)
    return {"color": col, "rough": g.maprange(n.outputs["Fac"], 0.3, 0.7, 0.25, 0.7),
            "normal": g.bump(n.outputs["Fac"], 1.0, 0.004)}


def floor(g, p, rng):
    s = _floor(g, p, rng)
    s["fade"] = _vignette(g)
    return s


def _floor(g, p, rng):
    w = g.world()
    n = g.noise(1.5, 8.0, 0.6, vec=w)
    n2 = g.noise(12.0, 8.0, 0.7, vec=w)
    base = g.ramp(g.math("ADD", n.outputs["Fac"], g.math("MULTIPLY", n2.outputs["Fac"], 0.5)),
                  [(0.5, _lin((0.05, 0.048, 0.046))), (1.0, _lin((0.1, 0.095, 0.09)))])
    stain = g.maprange(g.noise(0.8, 3.0, 0.5, vec=w).outputs["Fac"], 0.45, 0.65)
    col = g.mix(g.math("MULTIPLY", stain, 0.6), base, _lin((0.05, 0.045, 0.04)))
    rough = g.mixf(stain, 0.85, 0.55)
    cond = COND["name"]
    geo = g.n.new("ShaderNodeNewGeometry")
    sep = g.n.new("ShaderNodeSeparateXYZ")
    g.link(geo.outputs["Position"], sep.inputs[0])
    r = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", sep.outputs[0], sep.outputs[0]),
                               g.math("MULTIPLY", sep.outputs[1], sep.outputs[1])))
    pn = g.noise(6.0, 4.0, 0.6, vec=w).outputs["Fac"]
    rr = g.math("ADD", r, g.math("MULTIPLY", pn, 0.12))
    if cond == "SOAKED":
        pud = g.maprange(rr, 0.42, 0.36)
        col = g.mix(pud, col, _lin((0.02, 0.025, 0.02)))
        rough = g.mixf(pud, rough, 0.02)
    elif cond == "BIOHAZARD":
        pud = g.maprange(rr, 0.33, 0.29)
        col = g.mix(pud, col, _lin((0.35, 0.9, 0.03)))
        rough = g.mixf(pud, rough, 0.03)
        return {"color": col, "rough": rough, "emit": g.mix(pud, (0, 0, 0), _lin((0.3, 0.9, 0.02))), "estr": 0.8,
                "normal": g.bump(n2.outputs["Fac"], 0.15, 0.002)}
    elif cond == "BURNT":
        soot = g.maprange(rr, 0.55, 0.25)
        col = g.mix(soot, col, _lin((0.01, 0.01, 0.01)))
    return {"color": col, "rough": rough, "normal": g.bump(n2.outputs["Fac"], 0.15, 0.002)}


def _vignette(g):
    geo = g.n.new("ShaderNodeNewGeometry")
    sep = g.n.new("ShaderNodeSeparateXYZ")
    g.link(geo.outputs["Position"], sep.inputs[0])
    r = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", sep.outputs[0], sep.outputs[0]),
                               g.math("MULTIPLY", sep.outputs[1], sep.outputs[1])))
    return g.maprange(r, 0.6, 0.2)


def goo(g, p, rng):
    return {"color": _lin((0.4, 1.0, 0.05)), "rough": 0.03, "trans": 0.4, "sss": 0.3,
            "emit": _lin((0.35, 1.0, 0.02)), "estr": 1.5}


def water(g, p, rng):
    return {"color": (1.0, 1.0, 1.0), "rough": 0.0, "trans": 1.0, "ior": 1.33}


def lens(g, p, rng):
    return {"color": _lin(p.get("color", (0.1, 0.1, 0.12))), "rough": 0.02, "metal": 0.0, "coat": 1.0,
            "film": p.get("film", 300.0)}


def gem(g, p, rng):
    return {"color": _lin((0.98, 0.99, 1.0)), "rough": 0.0, "trans": 1.0, "ior": 2.42}


def army(g, p, rng):
    return plastic(g, {"color": p.get("color", (0.32, 0.38, 0.2)), "rough": 0.55, "texture": 0.3}, rng)


def slime(g, p, rng):
    return {"color": _lin(p.get("color", (0.3, 0.9, 0.2))), "rough": 0.05, "trans": 0.5, "sss": 0.5}


def wood(g, p, rng):
    w = g.n.new("ShaderNodeTexWave")
    w.wave_type = "RINGS"
    w.inputs["Scale"].default_value = 6.0
    w.inputs["Distortion"].default_value = 6.0
    w.inputs["Detail"].default_value = 4.0
    g.link(g.rest(), w.inputs["Vector"])
    col = g.ramp(w.outputs["Fac"], [(0.2, _lin((0.35, 0.2, 0.1))), (0.8, _lin((0.6, 0.4, 0.22)))])
    return {"color": col, "rough": 0.5, "normal": g.bump(w.outputs["Fac"], 0.1, 0.001)}


KINDS = {
    "plastic": plastic, "translucent": translucent, "rubber": rubber, "metal": metal, "chrome": chrome,
    "gold": gold, "glass": glass, "screen": screen, "printed": printed, "paper": paper, "cardboard": cardboard,
    "foam": foam, "fabric": fabric, "tape": tape, "disc": disc, "wax": wax, "crust": crust, "pcb": pcb,
    "copper": copper, "steel": steel, "rust": rust, "core": core, "floor": floor, "goo": goo, "lens": lens,
    "gem": gem, "water": water, "army": army, "slime": slime, "wood": wood,
}

__all__ = ["get", "set_condition", "tex"]
