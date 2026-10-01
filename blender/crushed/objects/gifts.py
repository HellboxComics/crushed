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


def _clay_head(b, rng, kind, specs):
    """The canonical Clay StonKz framing: one big clay HEAD, bust-style, filling the view, with an oversized hat,
    shades and a shirt collar under it. kind: bull | bear | pig | frog. Face points -Y."""
    R = 0.055
    cols = {"bull": [(0.6, 0.3, 0.14), (0.22, 0.14, 0.1), (0.8, 0.78, 0.74), (0.95, 0.55, 0.3)],
            "bear": [(0.36, 0.22, 0.13), (0.14, 0.1, 0.09), (0.62, 0.48, 0.32), (0.95, 0.95, 0.93)],
            "pig": [(0.96, 0.55, 0.68), (0.9, 0.42, 0.52), (0.96, 0.78, 0.82), (0.75, 0.3, 0.4)],
            "frog": [(0.3, 0.7, 0.2), (0.18, 0.5, 0.22), (0.75, 1.0, 0.1), (0.25, 0.35, 0.75)]}
    skin = tuple(cols[kind][int(rng.integers(0, 4))])
    specs["skin"] = CL(skin, tuple(min(1, x * 1.25 + 0.05) for x in skin))
    # head and neck + shirt collar
    b.sphere(R, loc=(0, 0, 0.02), scale=(1.0, 0.95, 1.0 if kind != "frog" else 0.8), mat="skin", seg=32)
    b.cyl(R * 0.55, 0.04, loc=(0, 0.005, -0.045), mat="skin", seg=20)
    b.sphere(R * 1.05, loc=(0, 0.01, -0.075), scale=(1.15, 0.9, 0.5), mat="shirt", seg=24)
    shirt = tuple(rng.choice([(0.95, 0.95, 0.93), (0.1, 0.1, 0.12), (0.9, 0.15, 0.15), (0.2, 0.45, 0.95), (0.8, 1.0, 0.0), (0.2, 0.75, 0.65)]))
    specs["shirt"] = CL(shirt, skin)
    f = -R * 0.98          # the face plane, toward the camera
    if kind == "bull":
        b.sphere(R * 0.5, loc=(0, f * 0.7, -0.005), scale=(1.2, 0.8, 0.75), mat="muzzle", seg=16)
        for sy in (-1, 1):
            b.cyl(R * 0.1, R * 0.08, loc=(sy * R * 0.18, f * 1.08, -0.01), rot=(math.pi / 2, 0, 0), mat="dark", seg=10)
            b.tube([(sy * R * 0.6, 0.0, 0.045), (sy * R * 0.95, -0.01, 0.075), (sy * R * 1.0, -0.02, 0.115)],
                   lambda t: R * 0.16 * (1 - t) + 0.002, mat="horn", seg=10)
            b.cyl(R * 0.3, R * 0.25, loc=(sy * R * 0.95, 0.0, 0.0), rot=(0.3, sy * 1.2, 0), mat="skin", seg=12, r2=R * 0.1)
        b.torus(R * 0.14, R * 0.035, loc=(0, f * 0.98, -0.04), rot=(math.pi / 2, 0, 0), mat="ring", seg=14, rseg=6)
        specs.update({"muzzle": CL(tuple(min(1, x * 1.3 + 0.1) for x in skin), skin), "horn": CL((0.92, 0.85, 0.65), (0.6, 0.5, 0.3)),
                      "ring": ("gold", {"rough": 0.3})})
    elif kind == "bear":
        b.sphere(R * 0.42, loc=(0, f * 0.78, -0.012), scale=(1.1, 0.8, 0.8), mat="muzzle", seg=16)
        b.sphere(R * 0.16, loc=(0, f * 1.12, 0.0), scale=(1.3, 0.7, 0.9), mat="dark", seg=10)
        for sy in (-1, 1):
            b.sphere(R * 0.3, loc=(sy * R * 0.78, 0.0, 0.055), mat="skin", seg=14)
            b.sphere(R * 0.17, loc=(sy * R * 0.78, -0.012, 0.055), mat="muzzle", seg=12)
        specs["muzzle"] = CL((0.85, 0.7, 0.5), skin)
    elif kind == "pig":
        b.cyl(R * 0.36, R * 0.3, loc=(0, f * 0.85, -0.012), rot=(math.pi / 2, 0, 0), mat="snout", seg=18)
        for sy in (-1, 1):
            b.cyl(R * 0.08, R * 0.05, loc=(sy * R * 0.14, f * 1.12, -0.012), rot=(math.pi / 2, 0, 0), mat="dark", seg=10)
            b.cyl(R * 0.3, R * 0.6, loc=(sy * R * 0.62, 0.0, 0.07), rot=(-sy * 0.5, 0.0, 0), mat="skin", seg=12, r2=R * 0.04)
        specs["snout"] = CL(tuple(x * 0.85 for x in skin), skin)
    else:   # frog
        for sy in (-1, 1):
            b.sphere(R * 0.34, loc=(sy * R * 0.5, -0.01, 0.055), mat="skin", seg=14)
        b.tube([(-R * 0.6, f * 0.95, -0.02), (-R * 0.2, f * 1.02, -0.03), (R * 0.2, f * 1.02, -0.03), (R * 0.6, f * 0.95, -0.02)],
               R * 0.04, mat="dark", seg=8)
        b.sphere(R * 0.9, loc=(0, 0.0, -0.01), scale=(1.0, 0.9, 0.55), mat="belly", seg=20)
        specs["belly"] = CL((0.95, 0.9, 0.7), skin)
    specs["dark"] = CL((0.03, 0.03, 0.035))
    # eyes: aviators (most), a visor, or bare clay eyes
    e = int(rng.choice(3, p=[0.5, 0.25, 0.25]))
    ez = 0.065 if kind == "frog" else 0.02
    ey = -0.012 if kind == "frog" else f * 0.92
    if e == 0:
        for sy in (-1, 1):
            b.sphere(R * 0.33, loc=(sy * R * (0.5 if kind == "frog" else 0.4), ey, ez), scale=(1.0, 0.25, 0.85), mat="lens", seg=14)
        b.box((R * 0.2, R * 0.08, R * 0.08), loc=(0, ey, ez + R * 0.1), mat="dark")
        b.torus(R * 0.33, R * 0.03, loc=(-R * 0.4, ey, ez), rot=(math.pi / 2, 0, 0), mat="gold", seg=16, rseg=5)
        b.torus(R * 0.33, R * 0.03, loc=(R * 0.4, ey, ez), rot=(math.pi / 2, 0, 0), mat="gold", seg=16, rseg=5)
        specs["lens"] = ("plastic", {"color": (0.04, 0.04, 0.05), "rough": 0.12, "coat": 1.0})
        specs["gold"] = ("gold", {"rough": 0.3})
    elif e == 1:
        b.box((R * 1.7, R * 0.12, R * 0.5), loc=(0, ey, ez), mat="visor", bevel=R * 0.05)
        specs["visor"] = CL(tuple(rng.choice([(0.2, 0.75, 0.65), (0.9, 0.2, 0.3), (0.8, 1.0, 0.0)])), (0.1, 0.1, 0.1))
    else:
        for sy in (-1, 1):
            b.sphere(R * 0.2, loc=(sy * R * (0.5 if kind == "frog" else 0.4), ey, ez), mat="white", seg=12)
            b.sphere(R * 0.09, loc=(sy * R * (0.5 if kind == "frog" else 0.4), ey - R * 0.15, ez), mat="dark", seg=8)
        specs["white"] = CL((0.97, 0.97, 0.95))
    # hat
    h = int(rng.choice(4, p=[0.5, 0.2, 0.15, 0.15]))
    top = 0.02 + R * (0.8 if kind != "frog" else 1.05)
    if h == 0:        # cowboy hat, oversized, with a band
        b.lathe([(0.0, 0.0), (R * 1.5, 0.0), (R * 1.55, R * 0.2), (R * 0.92, R * 0.14), (R * 0.95, R * 1.1), (R * 0.7, R * 1.35), (R * 0.35, R * 1.15), (0.0, R * 1.3)],
                loc=(0, 0, top - R * 0.1), mat="hat", seg=24)
        b.torus(R * 0.97, R * 0.07, loc=(0, 0, top + R * 0.1), mat="band", seg=22, rseg=6)
        hc = tuple(rng.choice([(0.85, 0.82, 0.72), (0.4, 0.26, 0.15), (0.1, 0.1, 0.11), (0.8, 1.0, 0.0)]))
        specs["hat"] = CL(hc, tuple(x * 0.7 for x in hc)); specs["band"] = CL((0.35, 0.2, 0.1))
    elif h == 1:      # beanie
        b.sphere(R * 1.02, loc=(0, 0, top - R * 0.35), scale=(1, 1, 0.8), mat="hat", seg=24)
        b.torus(R * 0.98, R * 0.1, loc=(0, 0, top - R * 0.3), mat="band", seg=22, rseg=6)
        hc = tuple(rng.choice([(0.9, 0.15, 0.15), (0.2, 0.45, 0.95), (0.8, 1.0, 0.0)]))
        specs["hat"] = CL(hc); specs["band"] = CL(tuple(x * 0.8 for x in hc))
    elif h == 2:      # top hat
        b.cyl(R * 1.25, R * 0.1, loc=(0, 0, top), mat="hat", seg=22)
        b.cyl(R * 0.8, R * 1.1, loc=(0, 0, top + R * 0.6), mat="hat", seg=22)
        b.torus(R * 0.8, R * 0.06, loc=(0, 0, top + R * 0.2), mat="band", seg=22, rseg=6)
        specs["hat"] = CL((0.06, 0.06, 0.07), (0.2, 0.2, 0.22)); specs["band"] = CL((0.8, 1.0, 0.0))
    else:             # headband only
        b.torus(R * 0.98, R * 0.09, loc=(0, 0, top - R * 0.35), mat="band", seg=22, rseg=6)
        specs["band"] = CL(tuple(rng.choice([(0.9, 0.1, 0.1), (0.1, 0.3, 0.9), (0.8, 1.0, 0.0)])))


@obj("clay_bull", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_bull(b, rng, pal):
    specs = {}
    _clay_head(b, rng, "bull", specs)
    return specs


@obj("clay_bear", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_bear(b, rng, pal):
    specs = {}
    _clay_head(b, rng, "bear", specs)
    return specs


@obj("clay_pig", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def clay_pig(b, rng, pal):
    specs = {}
    _clay_head(b, rng, "pig", specs)
    return specs


@obj("clay_frog", mass=0.25, weight=1.0, hero=(0, -1, 0), **G)
def clay_frog(b, rng, pal):
    specs = {}
    _clay_head(b, rng, "frog", specs)
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


# -- LOW RES (the Pixelord gift) -----------------------------------------------------------------
# A bedroom studio at 3 A.M.: purple and acid green, a lava lamp, a skull candle, a black cat, mushrooms,
# a tiny arcade cabinet. All original props; the only tribute is the mood.

PURPLE = (0.42, 0.12, 0.65)
ACID = (0.55, 1.0, 0.1)


@obj("lava_lamp", mass=0.6, weight=1.0, hero=(0, -1, 0), **G)
def lava_lamp(b, rng, pal):
    b.lathe([(0.0, 0.0), (0.028, 0.0), (0.042, 0.05), (0.03, 0.17), (0.02, 0.2), (0.0, 0.2)], loc=(0, 0, -0.1),
            mat="glass", seg=28)
    b.lathe([(0.0, 0.0), (0.046, 0.0), (0.03, 0.075), (0.0, 0.075)], loc=(0, 0, -0.175), mat="base", seg=28)
    b.cyl(0.019, 0.028, loc=(0, 0, 0.112), mat="base", seg=20, r2=0.012)
    for z, r in ((-0.075, 0.02), (-0.03, 0.016), (0.02, 0.014), (0.06, 0.011)):
        b.sphere(r, loc=(float(rng.normal(0, 0.004)), float(rng.normal(0, 0.004)), z), scale=(1, 1, 1.5), mat="wax", seg=14)
    goo, liq = (tuple(rng.choice([ACID, (1.0, 0.3, 0.6), (1.0, 0.5, 0.1)])), tuple(rng.choice([PURPLE, (0.1, 0.3, 0.8), (0.15, 0.05, 0.3)])))
    return {"glass": ("glass", {"color": liq, "trans": 1.0, "rough": 0.03}),
            "base": MET((0.85, 0.75, 0.4), 0.3), "wax": P(goo, 0.25, glow=2.5)}


@obj("skull_candle", mass=0.2, weight=1.0, hero=(0, -1, 0), **G)
def skull_candle(b, rng, pal):
    """A skull-shaped candle, face toward -Y: cranium, brow, two deep sockets, a nose hole, a row of teeth."""
    b.sphere(0.034, loc=(0, 0.004, 0.012), scale=(1.0, 1.1, 1.0), mat="bone", seg=24)
    b.box((0.046, 0.034, 0.03), loc=(0, -0.006, -0.02), mat="bone", bevel=0.007)
    for sx in (-1, 1):
        b.sphere(0.0115, loc=(sx * 0.0135, -0.024, 0.01), scale=(1, 0.7, 1), mat="socket", seg=12)
    b.sphere(0.0055, loc=(0, -0.027, -0.008), scale=(1, 0.6, 1.5), mat="socket", seg=10)
    b.box((0.038, 0.004, 0.002), loc=(0, -0.0245, -0.026), mat="socket")
    for i in range(7):
        b.box((0.0042, 0.005, 0.009), loc=((i - 3) * 0.0056, -0.0245, -0.031), mat="bone", bevel=0.0006)
    b.cyl(0.004, 0.012, loc=(0, 0, 0.049), mat="wick", seg=8)
    b.sphere(0.006, loc=(0, 0, 0.06), scale=(1, 1, 1.8), mat="flame", seg=10)
    for _ in range(3):
        a = float(rng.uniform(0, 6.28))
        b.tube([(0.012 * math.cos(a), 0.012 * math.sin(a), 0.042),
                (0.03 * math.cos(a), 0.03 * math.sin(a), float(rng.uniform(-0.01, 0.025)))], 0.003, mat="bone", seg=6)
    col = tuple(rng.choice([(0.95, 0.93, 0.85), PURPLE, (0.06, 0.06, 0.07), ACID]))
    return {"bone": ("wax", {"color": col}), "socket": P((0.02, 0.01, 0.03), 0.7), "wick": P(BLACK, 0.8),
            "flame": P((1.0, 0.6, 0.15), 0.3, glow=6.0)}


@obj("black_cat", mass=0.3, weight=1.0, hero=(0, -1, 0), **G)
def black_cat(b, rng, pal):
    """A sitting cat figurine: tall, slim, ears up, tail wrapped around the front."""
    b.lathe([(0.0, 0.0), (0.036, 0.0), (0.03, 0.05), (0.02, 0.1), (0.0, 0.1)], loc=(0, 0, -0.06), mat="fur", seg=22)
    b.sphere(0.024, loc=(0.0, 0, 0.055), scale=(1, 1, 0.95), mat="fur", seg=20)
    for sy in (-1, 1):
        b.cyl(0.009, 0.02, loc=(0, sy * 0.014, 0.078), rot=(-sy * 0.3, 0, 0), mat="fur", seg=8, r2=0.0005)
        b.sphere(0.004, loc=(0.02, sy * 0.009, 0.058), scale=(0.5, 1, 1.3), mat="eye", seg=8)
    b.tube([(0.02, -0.03, -0.055), (0.035, 0.0, -0.058), (0.02, 0.03, -0.055), (-0.01, 0.038, -0.05)], 0.006, mat="fur", seg=8)
    b.torus(0.022, 0.0025, loc=(0, 0, 0.034), mat="collar", seg=18, rseg=6)
    return {"fur": P((0.03, 0.03, 0.035), 0.55), "eye": P(ACID, 0.2, glow=3.0), "collar": P(PURPLE, 0.3)}


@obj("mushroom_cluster", mass=0.08, weight=1.0, **G)
def mushroom_cluster(b, rng, pal):
    for i in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.018, 2))
        h = float(rng.uniform(0.03, 0.06))
        r = h * float(rng.uniform(0.4, 0.6))
        b.cyl(r * 0.3, h, loc=(x, y, h / 2 - 0.02), mat="stem", seg=10, r2=r * 0.22)
        b.sphere(r, loc=(x, y, h - 0.02), scale=(1, 1, 0.65), mat="cap", seg=16)
        for _ in range(4):
            a = float(rng.uniform(0, 6.28))
            b.sphere(r * 0.18, loc=(x + r * 0.6 * math.cos(a), y + r * 0.6 * math.sin(a), h - 0.02 + r * 0.42), mat="spot", seg=8)
    cap = tuple(rng.choice([PURPLE, ACID, (0.9, 0.15, 0.2), (0.1, 0.6, 0.9)]))
    return {"stem": P((0.92, 0.9, 0.82), 0.6), "cap": P(cap, 0.35, glow=0.6 if cap == ACID else 0.0), "spot": P(WHITE, 0.5)}


@obj("mini_arcade", mass=0.35, weight=1.0, hero=(0, -1, 0), **G)
def mini_arcade(b, rng, pal):
    b.extrude([(-0.03, -0.045), (0.03, -0.045), (0.03, -0.015), (0.045, -0.015), (0.045, 0.04), (0.03, 0.05),
               (0.03, 0.065), (-0.03, 0.065), (-0.03, 0.05), (-0.045, 0.04), (-0.045, -0.015), (-0.03, -0.015)],
              0.055, rot=(math.pi / 2, 0, 0), mat="cab", bevel=0.001)
    b.plane(0.052, 0.04, loc=(0, -0.0282, 0.022), rot=(math.pi / 2, 0, 0), mat="screen", cuts=3)
    b.plane(0.056, 0.012, loc=(0, -0.0282, 0.056), rot=(math.pi / 2, 0, 0), mat="marquee", cuts=2)
    b.box((0.056, 0.02, 0.004), loc=(0, -0.034, -0.006), mat="panel", bevel=0.0008)
    b.cyl(0.0025, 0.014, loc=(-0.015, -0.034, 0.002), mat="stick", seg=8)
    b.sphere(0.005, loc=(-0.015, -0.034, 0.011), mat="ball", seg=10)
    for i in range(2):
        b.cyl(0.004, 0.003, loc=(0.008 + i * 0.012, -0.034, -0.0025), mat="btn", seg=10)
    cab = tuple(rng.choice([PURPLE, (0.06, 0.06, 0.07), ACID]))
    return {"cab": P(cab, 0.35), "screen": ("screen", {"image": tex.screen(rng, "arc", kind="game"), "glow": 2.0}),
            "marquee": PR(tex.lcd(rng, "mq", str(rng.choice(["LOW RES", "INSERT COIN", "HI SCORE", "PLAYER 1"])),
                                  bg=(0.15, 0.02, 0.25), ink=ACID), 0.2, glow=1.5),
            "panel": P((0.08, 0.08, 0.09), 0.4), "stick": P(BLACK, 0.5), "ball": P((0.9, 0.1, 0.2), 0.2), "btn": P(ACID, 0.3)}
