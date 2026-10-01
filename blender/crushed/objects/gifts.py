"""Props for the gift one-of-ones. All original geometry, built to read at a glance once crushed.

CCFF00: flat lime squares, 45-degree diamonds and small cubes, with small black mono type.
HoodStreet: pigs (piggy banks, a tusked iron boar), bulls and bears, share certificates, ticker tape, ties.
"""
import math

from mathutils import Matrix

from .. import tex
from . import BLACK, CHARCOAL, CHROME, LIME, MET, NEON, P, PR, RUB, SILVER, T, WHITE, obj

G = dict(group="special", eras=(0, 1, 2, 3, 4))
FILL = dict(group="filler", eras=(0, 1, 2, 3, 4))


# -- CCFF00 -------------------------------------------------------------------------------------

def _lime(rough=0.3):
    return P(LIME, rough, coat=0.5, glow=NEON)


def _tile_mats(rng, neg, big=False, faces=1):
    """The lime body (or a black one), and `faces` printed faces that keep their ink."""
    specs = {"tile": (P((0.012, 0.012, 0.014), 0.22, coat=0.7, keep=True) if neg else _lime())}
    for i in range(faces):
        specs[f"face{i}"] = PR(tex.neon_tile(rng, f"nt{i}", neg=neg, big=big), 0.3, keep=True, glow=NEON * (1.6 if neg else 1.0))
    return specs


@obj("neon_square", mass=0.06, weight=1.0, **G)
def neon_square(b, rng, pal):
    s = float(rng.uniform(0.075, 0.125))
    t = float(rng.uniform(0.005, 0.009))
    rz = float(rng.normal(0, 0.05))
    b.box((s, s, t), rot=(0, 0, rz), mat="tile", bevel=0.0013)
    b.plane(s * 0.985, s * 0.985, loc=(0, 0, t / 2 + 0.0004), rot=(0, 0, rz), mat="face0", cuts=2)
    return _tile_mats(rng, rng.random() < 0.16)


@obj("neon_square_big", mass=0.2, weight=1.0, tags=("upright",), **G)
def neon_square_big(b, rng, pal):
    """The headliner: one big flat square that says what it is."""
    s, t = 0.11, 0.012          # fits between the two straps
    b.box((s, s, t), mat="tile", bevel=0.002)
    b.plane(s * 0.99, s * 0.99, loc=(0, 0, t / 2 + 0.0005), mat="face0", cuts=2)
    return _tile_mats(rng, False, big=True)


@obj("neon_diamond", mass=0.05, weight=1.0, **G)
def neon_diamond(b, rng, pal):
    s = float(rng.uniform(0.065, 0.1))
    t = float(rng.uniform(0.006, 0.011))
    rz = math.pi / 4 + float(rng.normal(0, 0.04))
    b.box((s, s, t), rot=(0, 0, rz), mat="tile", bevel=0.0015)
    b.plane(s * 0.985, s * 0.985, loc=(0, 0, t / 2 + 0.0004), rot=(0, 0, rz), mat="face0", cuts=2)
    return _tile_mats(rng, rng.random() < 0.14)


@obj("neon_cube", mass=0.07, weight=1.0, **G)
def neon_cube(b, rng, pal):
    s = float(rng.uniform(0.042, 0.066))
    e = 0.0004
    b.box((s, s, s), mat="tile", bevel=0.0035)
    b.plane(s * 0.94, s * 0.94, loc=(0, 0, s / 2 + e), mat="face0", cuts=2)
    b.plane(s * 0.94, s * 0.94, loc=(0, -s / 2 - e, 0), rot=(math.pi / 2, 0, 0), mat="face1", cuts=2)
    b.plane(s * 0.94, s * 0.94, loc=(s / 2 + e, 0, 0), rot=(0, math.pi / 2, 0), mat="face2", cuts=2)
    return _tile_mats(rng, rng.random() < 0.12, faces=3)


@obj("neon_stack", mass=0.12, weight=1.0, **G)
def neon_stack(b, rng, pal):
    s, t = 0.085, 0.0038
    n = int(rng.integers(5, 10))
    ang = 0.0
    for i in range(n):
        ang += float(rng.normal(0, 0.1))
        ox, oy = (float(v) for v in rng.normal(0, 0.003, 2))
        b.box((s, s, t), loc=(ox, oy, i * t * 1.04), rot=(0, 0, ang), mat="tile", bevel=0.0008)
    b.plane(s * 0.985, s * 0.985, loc=(ox, oy, (n - 1) * t * 1.04 + t / 2 + 0.0004), rot=(0, 0, ang), mat="face0", cuts=2)
    return _tile_mats(rng, False)


@obj("neon_frame", mass=0.05, weight=1.0, **G)
def neon_frame(b, rng, pal):
    """A square that is only the outline of one. The black shows through."""
    s = float(rng.uniform(0.11, 0.15))
    w, t = 0.017, 0.011
    b.box((s, w, t), loc=(0, (s - w) / 2, 0), mat="tile", bevel=0.0015)
    b.box((s, w, t), loc=(0, -(s - w) / 2, 0), mat="tile", bevel=0.0015)
    b.box((w, s - 2 * w, t), loc=((s - w) / 2, 0, 0), mat="tile", bevel=0.0015)
    b.box((w, s - 2 * w, t), loc=(-(s - w) / 2, 0, 0), mat="tile", bevel=0.0015)
    return {"tile": _lime()}


@obj("neon_bit", mass=0.004, weight=2.0, **FILL)
def neon_bit(b, rng, pal):
    """Loose pixels: tiny squares, diamonds and cubes, the filler between the big pieces."""
    for _ in range(int(rng.integers(2, 5))):
        s = float(rng.uniform(0.016, 0.034))
        loc = tuple(float(x) for x in rng.normal(0, 0.016, 2)) + (0.0,)
        kind = int(rng.integers(0, 3))
        if kind == 2:
            b.box((s, s, s), loc=loc, rot=(0, 0, float(rng.uniform(0, 1.5))), mat="tile", bevel=0.0018)
        else:
            rz = (math.pi / 4 if kind == 1 else 0.0) + float(rng.normal(0, 0.05))
            b.box((s, s, 0.004), loc=loc, rot=(0, 0, rz), mat="tile", bevel=0.0007)
    return {"tile": _lime()}


# -- HoodStreet ---------------------------------------------------------------------------------

def _sheet(b, w, h, mat, bow=0.012, n=9, wobble=0.0):
    """A sheet of paper with a gentle bow, UV-mapped 0..1 across the whole print."""
    rows = []
    for j in range(n):
        y = -h / 2 + h * j / (n - 1)
        rows.append([(-w / 2 + w * i / (n - 1), y,
                      bow * (1 - abs(i - (n - 1) / 2) / ((n - 1) / 2)) + wobble * math.sin(j * 1.3))
                     for i in range(n)])
    b.loft(rows, mat=mat, closed=False, cap=False)


@obj("piggy_bank", mass=0.5, weight=1.0, hero=(0, -1, 0), **G)
def piggy_bank(b, rng, pal):
    """Fat body, big snout, real ears, a curly tail and a coin slot. Five breeds: pink ceramic, gold, a tusked
    iron boar, plush, and chrome."""
    kind = int(rng.choice(5, p=[0.34, 0.16, 0.26, 0.14, 0.10]))
    boar = kind == 2
    b.sphere(0.05, loc=(0, 0, 0.056), scale=(1.35, 1.05, 0.92), mat="body", seg=32)
    b.sphere(0.04, loc=(0.058, 0, 0.06), scale=(1.0, 1.0, 0.95), mat="body", seg=24)
    b.lathe([(0.0, 0.0), (0.021, 0.0), (0.024, 0.006), (0.024, 0.02), (0.02, 0.024), (0.0, 0.024)],
            loc=(0.083, 0, 0.052), rot=(0, math.pi / 2, 0), mat="snout", seg=24)
    for sy in (-1, 1):
        b.cyl(0.0045, 0.004, loc=(0.1065, sy * 0.009, 0.052), rot=(0, math.pi / 2, 0), mat="dark", seg=10)
        b.cyl(0.016, 0.034, loc=(0.045, sy * 0.03, 0.096), rot=(-sy * 0.45, 0.35, 0), mat="body", seg=14, r2=0.002)
        b.sphere(0.0055, loc=(0.078, sy * 0.024, 0.071), mat="dark", seg=10)
        if boar:
            b.sphere(0.004, loc=(0.083, sy * 0.03, 0.08), mat="body", seg=8)    # a furrowed brow
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.015, 0.03, loc=(sx * 0.032, sy * 0.03, 0.014), mat="body", seg=14, r2=0.012)
    b.tube([(-0.062, 0, 0.065), (-0.076, 0, 0.07), (-0.084, 0, 0.082), (-0.077, 0, 0.093), (-0.067, 0, 0.088),
            (-0.071, 0, 0.079), (-0.079, 0, 0.082)], 0.0032, mat="body", seg=8)
    b.box((0.04, 0.007, 0.004), loc=(0, 0, 0.1015), mat="dark")
    if boar:
        for sy in (-1, 1):
            b.tube([(0.097, sy * 0.016, 0.042), (0.104, sy * 0.024, 0.051), (0.101, sy * 0.027, 0.066)],
                   lambda t: 0.0042 * (1 - t) + 0.0008, mat="tusk", seg=8)
    pink = (0.96, 0.55, 0.68)
    dark = P((0.03, 0.02, 0.025), 0.35)
    if kind == 0:
        body, snout = P(pink, 0.18, coat=0.9), P((0.88, 0.4, 0.55), 0.22, coat=0.7)
    elif kind == 1:
        body = snout = ("gold", {"rough": 0.2})
    elif kind == 2:
        body, snout = MET((0.12, 0.115, 0.115), 0.55), MET((0.18, 0.17, 0.17), 0.5)
    elif kind == 3:
        body, snout = ("fabric", {"color": (0.96, 0.62, 0.72)}), ("fabric", {"color": (0.88, 0.45, 0.58)})
    else:
        body = snout = ("chrome", {})
    return {"body": body, "snout": snout, "dark": dark, "tusk": P((0.92, 0.88, 0.76), 0.4)}


@obj("stock_cert", mass=0.01, weight=1.0, **G)
def stock_cert(b, rng, pal):
    _sheet(b, 0.16, 0.112, "cert", bow=0.011, wobble=0.0015)
    return {"cert": PR(tex.stock_cert(rng, "cert"), 0.7)}


@obj("ticker_tape", mass=0.02, weight=1.0, **G)
def ticker_tape(b, rng, pal):
    """A long strip of tape, coiled like it fell off the machine, with a loose end."""
    n, turns = 72, 2.3
    lo, hi = [], []
    for i in range(n):
        t = i / (n - 1)
        a = 2 * math.pi * turns * t
        r = 0.05 * (1 - 0.3 * t) + 0.012 * t * t
        z = 0.016 * t + 0.003 * math.sin(a * 0.5)
        x, y = r * math.cos(a), r * math.sin(a)
        lo.append((x, y, z - 0.0125))
        hi.append((x, y, z + 0.0125))
    b.loft([lo, hi], mat="tape", closed=False, cap=False)
    return {"tape": PR(tex.ticker_tape(rng, "tape"), 0.6)}


@obj("necktie", mass=0.04, weight=1.0, **G)
def necktie(b, rng, pal):
    poly = [(-0.012, 0.11), (0.012, 0.11), (0.016, 0.09), (0.013, 0.07), (0.012, 0.05), (0.02, 0.0), (0.03, -0.07),
            (0.0, -0.135), (-0.03, -0.07), (-0.02, 0.0), (-0.012, 0.05), (-0.013, 0.07), (-0.016, 0.09)]
    b.extrude(poly, 0.0045, mat="tie", bevel=0.0008)
    return {"tie": PR(tex.tie_print(rng, "tie"), 0.7)}


# -- CLAY (the Clay StonKz tribute) -------------------------------------------------------------
# Original hand-molded clay animals: a bull, a bear, a pig and a frog, with the hats and shades of a trading
# floor that never closes. Every one is lumps on lumps, like it was squeezed together on a desk.

CLAY_BG = [(0.03, 0.03, 0.035), (0.95, 0.95, 0.93), (0.8, 1.0, 0.0)]      # black, white, lime


def CL(c, smear=(0.95, 0.9, 0.85)):
    return ("clay", {"color": tuple(c), "smear": tuple(smear)})


def _clay_props(b, rng, head, r, specs):
    """Hat, shades, headband or a bare head; shirt is handled by the body."""
    hx, hy, hz = head
    kind = int(rng.choice(4, p=[0.35, 0.25, 0.2, 0.2]))
    if kind == 0:         # cowboy hat
        b.cyl(r * 1.6, r * 0.12, loc=(hx, hy, hz + r * 0.85), mat="hat", seg=20)
        b.lathe([(0.0, 0.0), (r * 0.75, 0.0), (r * 0.8, r * 0.5), (r * 0.6, r * 0.7), (r * 0.3, r * 0.6), (0.0, r * 0.72)],
                loc=(hx, hy, hz + r * 0.85), mat="hat", seg=18)
        b.torus(r * 0.78, r * 0.06, loc=(hx, hy, hz + r * 1.0), mat="band", seg=18, rseg=6)
        specs["hat"] = CL((0.45, 0.3, 0.15), (0.3, 0.2, 0.1))
        specs["band"] = CL((0.05, 0.05, 0.05))
    elif kind == 1:       # headband
        b.torus(r * 0.98, r * 0.09, loc=(hx, hy, hz + r * 0.45), mat="band", seg=20, rseg=6)
        specs["band"] = CL(tuple(rng.choice([(0.9, 0.1, 0.1), (0.1, 0.3, 0.9), (0.8, 1.0, 0.0)])))
    elif kind == 2:       # a tiny top hat
        b.cyl(r * 1.1, r * 0.1, loc=(hx, hy, hz + r * 0.88), mat="hat", seg=18)
        b.cyl(r * 0.7, r * 1.0, loc=(hx, hy, hz + r * 1.4), mat="hat", seg=18)
        specs["hat"] = CL((0.06, 0.06, 0.07), (0.2, 0.2, 0.22))
    # shades, on most of them
    if rng.random() < 0.65:
        for sy in (-1, 1):
            b.sphere(r * 0.3, loc=(hx + r * 0.78, hy + sy * r * 0.36, hz + r * 0.2), scale=(0.35, 1.0, 0.75), mat="lens", seg=12)
        b.box((r * 0.1, r * 0.3, r * 0.08), loc=(hx + r * 0.82, hy, hz + r * 0.22), mat="band2")
        specs["lens"] = ("plastic", {"color": (0.03, 0.03, 0.03), "rough": 0.15, "coat": 1.0})
        specs["band2"] = CL((0.05, 0.05, 0.05))
    else:                 # big googly eyes
        for sy in (-1, 1):
            b.sphere(r * 0.26, loc=(hx + r * 0.72, hy + sy * r * 0.36, hz + r * 0.22), mat="white", seg=12)
            b.sphere(r * 0.12, loc=(hx + r * 0.93, hy + sy * r * 0.36, hz + r * 0.24), mat="pupil", seg=8)
        specs["white"] = CL((0.97, 0.97, 0.95))
        specs["pupil"] = CL((0.03, 0.03, 0.03))


def _clay_body(b, rng, body_col, head_r, specs, shirt=True):
    """Fat lump of a body on four stubby legs, a lump of a head out front. Returns the head center."""
    b.sphere(0.045, loc=(0, 0, 0.05), scale=(1.25, 1.0, 0.9), mat="skin", seg=24)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.sphere(0.014, loc=(sx * 0.03, sy * 0.028, 0.013), scale=(1, 1, 0.9), mat="skin", seg=10)
    head = (0.06, 0.0, 0.07)
    b.sphere(head_r, loc=head, scale=(1.0, 1.05, 0.95), mat="skin", seg=24)
    if shirt:
        col = tuple(rng.choice([(0.95, 0.95, 0.93), (0.1, 0.1, 0.12), (0.9, 0.15, 0.15), (0.2, 0.45, 0.95), (0.8, 1.0, 0.0)]))
        b.sphere(0.047, loc=(-0.004, 0, 0.052), scale=(1.1, 1.03, 0.75), mat="shirt", seg=24)
        specs["shirt"] = CL(col, body_col)
    specs["skin"] = CL(body_col)
    return head


@obj("clay_bull", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_bull(b, rng, pal):
    specs = {}
    col = tuple(rng.choice([(0.55, 0.25, 0.12), (0.2, 0.12, 0.1), (0.75, 0.75, 0.72), (0.8, 1.0, 0.0)]))
    h = _clay_body(b, rng, col, 0.034, specs)
    hx, hy, hz = h
    for sy in (-1, 1):
        b.tube([(hx, hy + sy * 0.03, hz + 0.012), (hx + 0.005, hy + sy * 0.05, hz + 0.028), (hx + 0.012, hy + sy * 0.055, hz + 0.045)],
               lambda t: 0.006 * (1 - t) + 0.0015, mat="horn", seg=8)
    b.sphere(0.018, loc=(hx + 0.028, hy, hz - 0.008), scale=(0.8, 1.2, 0.7), mat="muzzle", seg=12)
    for sy in (-1, 1):
        b.sphere(0.0035, loc=(hx + 0.042, hy + sy * 0.008, hz - 0.008), mat="pupil", seg=8)
    b.torus(0.006, 0.0015, loc=(hx + 0.044, hy, hz - 0.016), rot=(0, math.pi / 2, 0), mat="ring", seg=12, rseg=6)
    _clay_props(b, rng, h, 0.034, specs)
    specs.update({"horn": CL((0.9, 0.85, 0.7)), "muzzle": CL((0.85, 0.6, 0.5)), "pupil": CL((0.03, 0.03, 0.03)),
                  "ring": ("gold", {"rough": 0.3})})
    return specs


@obj("clay_bear", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_bear(b, rng, pal):
    specs = {}
    col = tuple(rng.choice([(0.35, 0.22, 0.14), (0.12, 0.1, 0.1), (0.6, 0.45, 0.3), (0.95, 0.95, 0.93)]))
    h = _clay_body(b, rng, col, 0.036, specs)
    hx, hy, hz = h
    for sy in (-1, 1):
        b.sphere(0.011, loc=(hx - 0.008, hy + sy * 0.03, hz + 0.028), mat="skin", seg=10)
        b.sphere(0.006, loc=(hx - 0.005, hy + sy * 0.03, hz + 0.029), mat="muzzle", seg=8)
    b.sphere(0.016, loc=(hx + 0.03, hy, hz - 0.006), scale=(0.9, 1.1, 0.8), mat="muzzle", seg=12)
    b.sphere(0.006, loc=(hx + 0.045, hy, hz - 0.001), mat="pupil", seg=8)
    _clay_props(b, rng, h, 0.036, specs)
    specs.update({"muzzle": CL((0.85, 0.7, 0.55)), "pupil": CL((0.03, 0.03, 0.03))})
    return specs


@obj("clay_pig", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_pig(b, rng, pal):
    specs = {}
    col = tuple(rng.choice([(0.96, 0.55, 0.68), (0.9, 0.4, 0.5), (0.95, 0.75, 0.8), (0.8, 1.0, 0.0)]))
    h = _clay_body(b, rng, col, 0.035, specs)
    hx, hy, hz = h
    b.cyl(0.013, 0.014, loc=(hx + 0.038, hy, hz - 0.004), rot=(0, math.pi / 2, 0), mat="snout", seg=14)
    for sy in (-1, 1):
        b.cyl(0.0032, 0.002, loc=(hx + 0.0455, hy + sy * 0.0055, hz - 0.004), rot=(0, math.pi / 2, 0), mat="pupil", seg=8)
        b.cyl(0.011, 0.02, loc=(hx - 0.004, hy + sy * 0.026, hz + 0.034), rot=(-sy * 0.5, 0.3, 0), mat="skin", seg=10, r2=0.0015)
    b.tube([(-0.055, 0, 0.055), (-0.064, 0, 0.062), (-0.07, 0, 0.072), (-0.064, 0, 0.078), (-0.058, 0, 0.072)], 0.0028,
           mat="skin", seg=8)
    _clay_props(b, rng, h, 0.035, specs)
    specs.update({"snout": CL(tuple(x * 0.85 for x in col)), "pupil": CL((0.03, 0.03, 0.03))})
    return specs


@obj("clay_frog", mass=0.25, weight=1.0, hero=(0, -1, 0), **G)
def clay_frog(b, rng, pal):
    """Squat, wide mouth, eyes on top. Original lump of a frog."""
    specs = {}
    col = tuple(rng.choice([(0.3, 0.7, 0.2), (0.15, 0.5, 0.2), (0.8, 1.0, 0.0), (0.2, 0.3, 0.7)]))
    b.sphere(0.05, loc=(0, 0, 0.035), scale=(1.3, 1.1, 0.7), mat="skin", seg=24)
    b.sphere(0.04, loc=(0.03, 0, 0.045), scale=(1.1, 1.2, 0.6), mat="skin", seg=20)
    b.sphere(0.048, loc=(0.0, 0, 0.028), scale=(1.2, 1.0, 0.45), mat="belly", seg=20)
    for sy in (-1, 1):
        b.sphere(0.014, loc=(0.045, sy * 0.028, 0.068), mat="skin", seg=12)
        b.sphere(0.0105, loc=(0.052, sy * 0.028, 0.072), mat="white", seg=12)
        b.sphere(0.005, loc=(0.06, sy * 0.028, 0.074), mat="pupil", seg=8)
        b.sphere(0.016, loc=(-0.025, sy * 0.055, 0.018), scale=(1.4, 1.0, 0.7), mat="skin", seg=12)
        b.sphere(0.01, loc=(0.045, sy * 0.045, 0.012), scale=(1.5, 1.0, 0.6), mat="skin", seg=10)
    b.tube([(0.07, -0.03, 0.045), (0.078, -0.012, 0.04), (0.08, 0.012, 0.04), (0.07, 0.03, 0.045)], 0.002, mat="pupil", seg=6)
    h = (0.03, 0.0, 0.05)
    if rng.random() < 0.5:
        _clay_props(b, rng, h, 0.04, specs)
        specs.pop("white", None); specs.pop("pupil", None); specs.pop("lens", None); specs.pop("band2", None)
    specs.update({"skin": CL(col), "belly": CL((0.95, 0.9, 0.7), col), "white": CL((0.97, 0.97, 0.95)),
                  "pupil": CL((0.03, 0.03, 0.03))})
    return specs


@obj("clay_coin", mass=0.02, weight=1.0, **G)
def clay_coin(b, rng, pal):
    b.cyl(0.024, 0.006, mat="coin", seg=20)
    b.box((0.004, 0.02, 0.0075), loc=(0, 0, 0), mat="mark")
    b.box((0.016, 0.004, 0.0075), loc=(0, 0.007, 0), mat="mark")
    b.box((0.016, 0.004, 0.0075), loc=(0, -0.007, 0), mat="mark")
    return {"coin": CL((0.95, 0.75, 0.2), (0.8, 0.55, 0.1)), "mark": CL((0.6, 0.4, 0.05))}


@obj("clay_candle", mass=0.02, weight=1.0, **G)
def clay_candle(b, rng, pal):
    up = rng.random() < 0.5
    b.box((0.016, 0.016, 0.06), mat="body", bevel=0.002)
    b.box((0.004, 0.004, 0.1), mat="wick")
    col = (0.2, 0.85, 0.3) if up else (0.9, 0.15, 0.15)
    return {"body": CL(col), "wick": CL(col)}


@obj("clay_blob", mass=0.01, weight=2.0, **FILL)
def clay_blob(b, rng, pal):
    """Leftover clay: squeezed lumps in the colors of everything else on the desk."""
    for _ in range(int(rng.integers(1, 4))):
        r = float(rng.uniform(0.012, 0.028))
        b.sphere(r, loc=tuple(float(x) for x in rng.normal(0, 0.012, 3)),
                 scale=tuple(float(x) for x in rng.uniform(0.6, 1.3, 3)), mat="clay", seg=12)
    col = tuple(rng.choice([(0.96, 0.55, 0.68), (0.55, 0.25, 0.12), (0.3, 0.7, 0.2), (0.8, 1.0, 0.0), (0.35, 0.22, 0.14),
                            (0.95, 0.95, 0.93), (0.03, 0.03, 0.035)]))
    return {"clay": CL(col)}
