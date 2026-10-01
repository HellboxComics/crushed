"""Holiday one-of-ones: the stuff every holiday left in the junk drawer, 1985 to now. All original shapes;
every brand on them is a parody."""
import math

from .. import tex
from . import BLACK, CHROME, MET, P, PR, T, WHITE, obj

G = dict(group="special", eras=(0, 1, 2, 3, 4))
FILL = dict(group="filler", eras=(0, 1, 2, 3, 4))


def _heart(w, h, n=24):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 32 * w, y / 32 * h))
    return pts


# -- VALENTINE'S ------------------------------------------------------------------------------------

@obj("candy_heart", mass=0.004, weight=1.0, **G)
def candy_heart(b, rng, pal):
    s = float(rng.uniform(0.03, 0.042))
    b.extrude(_heart(s, s), 0.008, mat="candy", bevel=0.0015)
    b.plane(s * 0.62, s * 0.62, loc=(0, -0.002, 0.0042), mat="words", cuts=2)
    img = tex.candy_heart(rng, "ch")
    col = tuple(img.pixels[0:3])
    return {"candy": P(col, 0.55), "words": PR(img, 0.55)}


@obj("chocolate_box", mass=0.4, weight=1.0, **G)
def chocolate_box(b, rng, pal):
    """The heart-shaped box: red foil lid, a few chocolates left in their brown cups."""
    w = 0.16
    b.extrude(_heart(w, w * 0.95, 32), 0.03, mat="box", bevel=0.003)
    b.extrude(_heart(w * 0.95, w * 0.9, 32), 0.004, loc=(0, 0, 0.016), mat="foil", bevel=0.001)
    for _ in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.uniform(-0.035, 0.035, 2))
        b.cyl(0.013, 0.008, loc=(x, y, 0.021), mat="cup", seg=14, r2=0.015)
        b.sphere(0.011, loc=(x, y, 0.027), scale=(1, 1, 0.7), mat="choc", seg=12)
    b.box((0.03, 0.006, 0.002), loc=(0.02, 0.04, 0.0185), rot=(0, 0, 0.6), mat="ribbon")
    return {"box": P((0.75, 0.04, 0.12), 0.3, coat=0.8), "foil": MET((0.85, 0.1, 0.2), 0.2),
            "cup": P((0.35, 0.2, 0.1), 0.6), "choc": P((0.28, 0.14, 0.06), 0.35, coat=0.4),
            "ribbon": P((0.98, 0.85, 0.9), 0.4)}


@obj("valentine_card", mass=0.003, weight=1.0, **G)
def valentine_card(b, rng, pal):
    b.plane(0.1, 0.07, rot=(0, 0, float(rng.normal(0, 0.1))), mat="card", cuts=3)
    return {"card": PR(tex.valentine_card(rng, "vc"), 0.6)}


@obj("rose", mass=0.03, weight=1.0, **G)
def rose(b, rng, pal):
    b.tube([(0, 0, -0.08), (0.004, 0, -0.03), (0, 0.002, 0.02)], 0.0025, mat="stem", seg=6)
    for k in range(5):
        a = k * 1.3
        b.sphere(0.012 - k * 0.0012, loc=(0.003 * math.cos(a), 0.003 * math.sin(a), 0.028 + k * 0.002),
                 scale=(1.0, 0.75, 1.15), rot=(0, 0, a), mat="petal", seg=12)
    b.sphere(0.012, loc=(0.008, 0, -0.03), scale=(1.6, 0.5, 0.2), rot=(0, 0.4, 0.3), mat="leaf", seg=8)
    return {"stem": P((0.15, 0.4, 0.12), 0.6), "leaf": P((0.15, 0.45, 0.15), 0.5),
            "petal": P(tuple(rng.choice([(0.7, 0.02, 0.08), (0.9, 0.3, 0.45), (0.55, 0.02, 0.05)])), 0.45)}


# -- HALLOWEEN --------------------------------------------------------------------------------------

@obj("pumpkin_pail", mass=0.15, weight=1.0, hero=(0, -1, 0), **G)
def pumpkin_pail(b, rng, pal):
    """The plastic jack-o'-lantern candy bucket, black handle and all."""
    R = 0.07
    b.lathe([(0.0, -0.05), (R * 0.8, -0.05), (R, -0.02), (R * 1.02, 0.02), (R * 0.85, 0.05), (R * 0.82, 0.052),
             (R * 0.78, 0.04), (0.0, 0.04)], mat="pail", seg=36, scale=(1, 1, 1))
    f = -R * 0.99
    for sx in (-1, 1):
        b.extrude([(-0.012, -0.008), (0.012, -0.008), (0.0, 0.012)], 0.004, loc=(sx * 0.025, f, 0.016),
                  rot=(math.pi / 2, 0, 0), mat="face")
    b.extrude([(-0.008, -0.006), (0.008, -0.006), (0.0, 0.008)], 0.004, loc=(0, f, -0.002), rot=(math.pi / 2, 0, 0),
              mat="face")
    mouth = [(-0.04, 0.0), (-0.025, -0.008), (-0.015, 0.0), (0.0, -0.01), (0.015, 0.0), (0.025, -0.008), (0.04, 0.0),
             (0.03, -0.022), (0.0, -0.028), (-0.03, -0.022)]
    b.extrude(mouth, 0.004, loc=(0, f, -0.016), rot=(math.pi / 2, 0, 0), mat="face")
    b.tube([(-R * 0.82, 0, 0.045), (-R * 0.6, 0, 0.11), (0, 0, 0.13), (R * 0.6, 0, 0.11), (R * 0.82, 0, 0.045)], 0.003,
           mat="handle", seg=8)
    return {"pail": P((1.0, 0.45, 0.02), 0.35, coat=0.3), "face": P(BLACK, 0.5), "handle": P(BLACK, 0.4)}


@obj("fun_size_bar", mass=0.02, weight=1.0, **G)
def fun_size_bar(b, rng, pal):
    b.box((0.07, 0.035, 0.012), mat="wrap", bevel=0.003)
    b.plane(0.068, 0.034, loc=(0, 0, 0.0062), mat="label", cuts=3)
    for sx in (-1, 1):
        b.box((0.006, 0.036, 0.003), loc=(sx * 0.038, 0, 0), mat="wrap")
    img = tex.fun_size(rng, "fs")
    return {"wrap": P(tuple(img.pixels[0:3]), 0.3, coat=0.5), "label": PR(img, 0.3)}


@obj("candy_corn", mass=0.003, weight=1.0, **G)
def candy_corn(b, rng, pal):
    for _ in range(int(rng.integers(3, 7))):
        x, y = (float(v) for v in rng.normal(0, 0.012, 2))
        rot = (0, 0, float(rng.uniform(0, 6.28)))
        b.extrude([(-0.007, -0.009), (0.007, -0.009), (0.0, 0.012)], 0.006, loc=(x, y, 0), rot=rot, mat="white",
                  bevel=0.001)
        b.extrude([(-0.0072, -0.009), (0.0072, -0.009), (0.0046, -0.002), (-0.0046, -0.002)], 0.0062,
                  loc=(x, y, 0), rot=rot, mat="yellow", bevel=0.001)
        b.extrude([(-0.005, -0.002), (0.005, -0.002), (0.0028, 0.004), (-0.0028, 0.004)], 0.0062, loc=(x, y, 0),
                  rot=rot, mat="orange", bevel=0.001)
    return {"white": P((0.98, 0.96, 0.9), 0.4), "yellow": P((0.98, 0.8, 0.1), 0.4), "orange": P((1.0, 0.45, 0.05), 0.4)}


@obj("costume_mask", mass=0.05, weight=1.0, hero=(0, -1, 0), **G)
def costume_mask(b, rng, pal):
    """A cheap drugstore vacuum-formed mask, the kind with the staple and the elastic that snapped."""
    kind = int(rng.integers(0, 3))
    b.sphere(0.06, loc=(0, 0, 0), scale=(0.85, 0.35, 1.05), mat="face", seg=24)
    for sx in (-1, 1):
        b.sphere(0.011, loc=(sx * 0.02, -0.02, 0.012), scale=(1.3, 0.6, 0.8), mat="hole", seg=10)
        b.cyl(0.0025, 0.004, loc=(sx * 0.05, 0.0, 0.0), rot=(0, math.pi / 2, 0), mat="staple", seg=6)
    b.sphere(0.008, loc=(0, -0.022, -0.028), scale=(1.8, 0.5, 0.7), mat="hole", seg=10)
    b.tube([(-0.05, 0.0, 0.0), (-0.06, 0.03, 0.0), (-0.05, 0.06, -0.01)], 0.0012, mat="elastic", seg=5)
    col = [(0.95, 0.95, 0.92), (0.35, 0.75, 0.25), (0.95, 0.55, 0.1)][kind]       # ghoul, witch, pumpkin-head
    return {"face": P(col, 0.25, coat=0.6), "hole": P(BLACK, 0.8), "staple": CHROME(), "elastic": P(BLACK, 0.6)}


@obj("rubber_spider", mass=0.005, weight=1.0, **G)
def rubber_spider(b, rng, pal):
    b.sphere(0.012, scale=(1.3, 1.0, 0.6), mat="body", seg=12)
    b.sphere(0.007, loc=(0.014, 0, 0.001), mat="body", seg=10)
    for sy in (-1, 1):
        for k in range(4):
            a = sy * (0.6 + k * 0.4)
            b.tube([(0, 0, 0), (0.02 * math.cos(a), 0.02 * math.sin(a), 0.01), (0.034 * math.cos(a), 0.034 * math.sin(a), -0.004)],
                   0.0012, mat="body", seg=5)
    return {"body": P(tuple(rng.choice([(0.05, 0.05, 0.05), (0.4, 0.05, 0.6), (1.0, 0.45, 0.02)])), 0.6)}


# -- CHRISTMAS -------------------------------------------------------------------------------------

@obj("ornament", mass=0.02, weight=1.0, **G)
def ornament(b, rng, pal):
    R = float(rng.uniform(0.022, 0.032))
    b.sphere(R, mat="glass", seg=20)
    b.cyl(R * 0.3, R * 0.3, loc=(0, 0, R * 1.05), mat="cap", seg=12)
    b.torus(R * 0.15, R * 0.04, loc=(0, 0, R * 1.3), rot=(math.pi / 2, 0, 0), mat="cap", seg=10, rseg=5)
    col = tuple(rng.choice([(0.8, 0.05, 0.1), (0.05, 0.45, 0.2), (0.85, 0.7, 0.2), (0.15, 0.3, 0.8), (0.85, 0.85, 0.9)]))
    return {"glass": MET(col, 0.12), "cap": MET((0.8, 0.75, 0.6), 0.3)}


@obj("light_strand", mass=0.08, weight=1.0, **G)
def light_strand(b, rng, pal):
    """Old fat C9 bulbs on green wire, the strand nobody could untangle."""
    pts = [(-0.11 + 0.22 * i / 16, 0.03 * math.sin(i * 0.9), 0.006 * math.sin(i * 1.7)) for i in range(17)]
    b.tube(pts, 0.0018, mat="wire", seg=6)
    specs = {"wire": P((0.08, 0.3, 0.12), 0.5), "base": P((0.1, 0.35, 0.12), 0.5)}
    cols = [(1.0, 0.1, 0.1), (0.1, 0.8, 0.2), (0.1, 0.4, 1.0), (1.0, 0.75, 0.1), (1.0, 0.4, 0.8)]
    for k, i in enumerate(range(1, 16, 3)):
        x, y, z = pts[i]
        b.cyl(0.004, 0.008, loc=(x, y - 0.006, z), rot=(math.pi / 2, 0, 0), mat="base", seg=8)
        b.lathe([(0.0, 0.0), (0.006, 0.0), (0.008, 0.008), (0.006, 0.02), (0.0, 0.024)],
                loc=(x, y - 0.01, z), rot=(math.pi / 2, 0, 0), mat=f"bulb{k}", seg=12)
        specs[f"bulb{k}"] = T(cols[(k + int(rng.integers(0, 5))) % 5], 0.15)
    return specs


@obj("candy_cane", mass=0.01, weight=1.0, **G)
def candy_cane(b, rng, pal):
    pts = [(0, 0, -0.07 + 0.014 * i) for i in range(9)]
    pts += [(0.018 * (1 - math.cos(a)), 0, 0.042 + 0.018 * math.sin(a)) for a in [math.pi * k / 8 for k in range(1, 9)]]
    b.tube(pts, 0.0045, mat="cane", seg=10)
    return {"cane": PR(tex.candy_stripe(rng, "cc"), 0.3)}


@obj("present", mass=0.2, weight=1.0, **G)
def present(b, rng, pal):
    w, d, h = (float(v) for v in rng.uniform(0.06, 0.1, 3))
    b.box((w, d, h * 0.7), mat="paper", bevel=0.001)
    b.box((w + 0.001, 0.012, h * 0.7 + 0.001), mat="ribbon")
    b.box((0.012, d + 0.001, h * 0.7 + 0.001), mat="ribbon")
    for a in (0.5, -0.5):
        b.torus(0.012, 0.004, loc=(0, 0, h * 0.35 + 0.006), rot=(math.pi / 2, 0, a), mat="ribbon", seg=14, rseg=6)
    return {"paper": PR(tex.wrap_paper(rng, "wp"), 0.5),
            "ribbon": P(tuple(rng.choice([(0.95, 0.8, 0.2), (0.85, 0.05, 0.1), (0.95, 0.95, 0.95)])), 0.3, coat=0.6)}


@obj("tinsel", mass=0.003, weight=2.0, **FILL)
def tinsel(b, rng, pal):
    for _ in range(int(rng.integers(5, 10))):
        x = float(rng.normal(0, 0.01))
        pts = [(x + 0.004 * math.sin(i * 1.3), 0.0, -0.04 + 0.01 * i) for i in range(9)]
        b.tube(pts, 0.0006, mat="foil", seg=4)
    return {"foil": MET(tuple(rng.choice([(0.85, 0.85, 0.9), (0.85, 0.7, 0.3), (0.85, 0.15, 0.2)])), 0.12)}


# -- EASTER ------------------------------------------------------------------------------------------

@obj("plastic_egg", mass=0.01, weight=1.0, **G)
def plastic_egg(b, rng, pal):
    b.sphere(0.022, scale=(1, 1, 1.3), mat="shell", seg=18)
    b.torus(0.0221, 0.0012, loc=(0, 0, 0.0), mat="seam", seg=18, rseg=4)
    return {"shell": PR(tex.egg_print(rng, "egg"), 0.25), "seam": P((0.95, 0.95, 0.95), 0.3)}


@obj("choc_bunny", mass=0.15, weight=1.0, hero=(0, -1, 0), **G)
def choc_bunny(b, rng, pal):
    """A hollow chocolate rabbit, ears bitten off first, in foil."""
    b.sphere(0.03, loc=(0, 0, 0.0), scale=(1, 0.8, 1.2), mat="choc", seg=18)
    b.sphere(0.02, loc=(0, -0.004, 0.045), mat="choc", seg=16)
    bitten = rng.random() < 0.6
    for sx in (-1, 1):
        if not (bitten and sx < 0):
            b.sphere(0.006, loc=(sx * 0.008, 0, 0.075), scale=(0.9, 0.5, 2.6), mat="choc", seg=10)
    b.sphere(0.02, loc=(0, 0, -0.035), scale=(1.4, 1.1, 0.4), mat="foil", seg=14)
    b.sphere(0.004, loc=(0.007, -0.02, 0.05), mat="eye", seg=6)
    return {"choc": P((0.32, 0.17, 0.07), 0.35, coat=0.3),
            "foil": MET(tuple(rng.choice([(0.85, 0.7, 0.25), (0.3, 0.5, 0.9), (0.85, 0.25, 0.5)])), 0.25),
            "eye": P(WHITE, 0.4)}


@obj("marshmallow_chick", mass=0.005, weight=1.0, **G)
def marshmallow_chick(b, rng, pal):
    col = tuple(rng.choice([(1.0, 0.92, 0.2), (1.0, 0.6, 0.8), (0.6, 0.85, 1.0), (0.75, 0.6, 1.0)]))
    for k in range(int(rng.integers(1, 4))):
        x = k * 0.026
        b.sphere(0.012, loc=(x, 0, 0.0), scale=(1.3, 0.8, 0.8), mat="sugar", seg=12)
        b.sphere(0.008, loc=(x + 0.008, 0, 0.012), mat="sugar", seg=10)
        b.sphere(0.0015, loc=(x + 0.012, -0.006, 0.015), mat="eye", seg=6)
    return {"sugar": ("foam", {"color": col}), "eye": P(BLACK, 0.4)}


@obj("easter_grass", mass=0.002, weight=2.0, **FILL)
def easter_grass(b, rng, pal):
    for _ in range(int(rng.integers(8, 14))):
        x, y = (float(v) for v in rng.normal(0, 0.01, 2))
        pts = [(x + 0.01 * math.sin(i * 0.9 + x * 50), y + 0.006 * math.cos(i * 1.3), -0.02 + 0.006 * i) for i in range(8)]
        b.tube(pts, 0.0009, mat="grass", seg=4)
    return {"grass": P(tuple(rng.choice([(0.3, 0.85, 0.3), (1.0, 0.6, 0.8), (0.7, 0.5, 1.0)])), 0.25, coat=0.6)}


# -- 4TH OF JULY ------------------------------------------------------------------------------------

@obj("firework", mass=0.05, weight=1.0, **G)
def firework(b, rng, pal):
    """A cardboard tube with a fuse, label and all; some already went off."""
    h = float(rng.uniform(0.06, 0.12))
    r = float(rng.uniform(0.012, 0.022))
    b.cyl(r, h, mat="label", seg=18)
    b.cyl(r * 0.9, 0.004, loc=(0, 0, h / 2 + 0.001), mat="end", seg=16)
    b.tube([(0, 0, h / 2), (0.003, 0.002, h / 2 + 0.012), (0.008, -0.002, h / 2 + 0.02)], 0.0012, mat="fuse", seg=5)
    spent = rng.random() < 0.4
    return {"label": PR(tex.firework_label(rng, "fw"), 0.6), "end": P((0.05, 0.04, 0.03) if spent else (0.85, 0.8, 0.7), 0.9),
            "fuse": P((0.6, 0.15, 0.1), 0.7)}


@obj("sparkler", mass=0.005, weight=1.0, **FILL)
def sparkler(b, rng, pal):
    for k in range(int(rng.integers(1, 4))):
        a = float(rng.uniform(-0.4, 0.4))
        b.tube([(k * 0.006, 0, -0.06), (k * 0.006 + 0.05 * math.sin(a), 0, -0.06 + 0.12 * math.cos(a))], 0.0011,
               mat="wire", seg=5)
        b.tube([(k * 0.006 + 0.02 * math.sin(a), 0, -0.04 + 0.05 * math.cos(a)),
                (k * 0.006 + 0.05 * math.sin(a), 0, -0.06 + 0.12 * math.cos(a))], 0.0022, mat="burnt", seg=6)
    return {"wire": MET((0.45, 0.45, 0.47), 0.5), "burnt": P((0.12, 0.11, 0.1), 0.95)}


@obj("mini_flag", mass=0.005, weight=1.0, **G)
def mini_flag(b, rng, pal):
    b.cyl(0.0015, 0.14, loc=(0, 0, 0), mat="stick", seg=6)
    b.plane(0.07, 0.045, loc=(0.035, 0, 0.045), rot=(math.pi / 2, 0, 0), mat="flag", cuts=4)
    return {"stick": P((0.25, 0.25, 0.27), 0.5), "flag": PR(tex.stars_stripes(rng, "flag"), 0.7)}


@obj("party_cup", mass=0.01, weight=1.0, **G)
def party_cup(b, rng, pal):
    """The red party cup, crushed flat on one side like they all were by the end."""
    b.lathe([(0.0, -0.05), (0.024, -0.05), (0.034, 0.05), (0.032, 0.05), (0.022, -0.046), (0.0, -0.046)], mat="cup",
            seg=24, scale=(1.0, float(rng.uniform(0.5, 1.0)), 1.0))
    for z in (-0.02, 0.0, 0.02):
        b.torus(0.024 + (z + 0.05) * 0.1, 0.0008, loc=(0, 0, z), mat="cup", seg=24, rseg=4)
    return {"cup": P(tuple(rng.choice([(0.8, 0.05, 0.08), (0.8, 0.05, 0.08), (0.1, 0.25, 0.75)])), 0.35, coat=0.3)}


# -- THANKSGIVING -----------------------------------------------------------------------------------

@obj("hand_turkey", mass=0.005, weight=1.0, **G)
def hand_turkey(b, rng, pal):
    b.plane(0.12, 0.15, rot=(0, 0, float(rng.normal(0, 0.12))), mat="paper", cuts=4)
    return {"paper": PR(tex.hand_turkey(rng, "ht"), 0.9)}


@obj("pilgrim_hat", mass=0.02, weight=1.0, **G)
def pilgrim_hat(b, rng, pal):
    """The construction-paper pilgrim hat from second grade."""
    b.cyl(0.06, 0.004, mat="paper", seg=24)
    b.cyl(0.035, 0.07, loc=(0, 0, 0.037), mat="paper", seg=20, r2=0.03)
    b.cyl(0.0335, 0.012, loc=(0, 0, 0.018), mat="band", seg=20)
    b.box((0.022, 0.004, 0.018), loc=(0, -0.034, 0.018), mat="buckle")
    return {"paper": P((0.06, 0.06, 0.07), 0.95), "band": P((0.95, 0.95, 0.9), 0.95), "buckle": P((0.95, 0.8, 0.2), 0.8)}


@obj("cranberry_log", mass=0.25, weight=1.0, **G)
def cranberry_log(b, rng, pal):
    """Canned cranberry sauce, still holding the can's rings."""
    b.cyl(0.035, 0.1, rot=(0, math.pi / 2, 0), mat="jelly", seg=24)
    for x in (-0.03, 0.0, 0.03):
        b.torus(0.035, 0.0015, loc=(x, 0, 0), rot=(0, math.pi / 2, 0), mat="jelly", seg=24, rseg=4)
    return {"jelly": T((0.55, 0.02, 0.08), 0.15)}


@obj("drumstick", mass=0.1, weight=1.0, **G)
def drumstick(b, rng, pal):
    b.sphere(0.03, loc=(0.02, 0, 0), scale=(1.4, 1.0, 0.9), mat="meat", seg=16)
    b.cyl(0.006, 0.05, loc=(-0.035, 0, 0), rot=(0, math.pi / 2, 0), mat="bone", seg=10)
    b.sphere(0.008, loc=(-0.06, 0.004, 0), mat="bone", seg=8)
    b.sphere(0.008, loc=(-0.06, -0.004, 0), mat="bone", seg=8)
    return {"meat": P((0.6, 0.32, 0.12), 0.35, coat=0.5), "bone": P((0.92, 0.88, 0.78), 0.6)}


# -- NEW YEAR'S (Y2K) -----------------------------------------------------------------------------

@obj("party_hat", mass=0.01, weight=1.0, **G)
def party_hat(b, rng, pal):
    b.cyl(0.035, 0.09, mat="hat", seg=20, r2=0.002)
    b.sphere(0.008, loc=(0, 0, 0.048), mat="pom", seg=8)
    b.torus(0.035, 0.003, loc=(0, 0, -0.045), mat="pom", seg=20, rseg=5)
    return {"hat": MET(tuple(rng.choice([(0.85, 0.7, 0.2), (0.75, 0.75, 0.8), (0.2, 0.3, 0.8), (0.8, 0.1, 0.4)])), 0.25),
            "pom": P(tuple(rng.choice([(0.95, 0.95, 0.95), (0.95, 0.8, 0.2)])), 0.8)}


@obj("noisemaker", mass=0.005, weight=1.0, **G)
def noisemaker(b, rng, pal):
    b.cyl(0.006, 0.03, rot=(0, math.pi / 2, 0), loc=(-0.05, 0, 0), mat="mouth", seg=10)
    pts = [(-0.035 + 0.012 * i, 0.0, 0.012 * math.sin(i * 0.7) * (i / 8)) for i in range(9)]
    b.tube(pts, 0.006, mat="horn", seg=8)
    return {"mouth": P(tuple(rng.choice([(0.9, 0.2, 0.2), (0.2, 0.5, 0.9)])), 0.4),
            "horn": MET(tuple(rng.choice([(0.85, 0.7, 0.2), (0.75, 0.2, 0.6), (0.2, 0.7, 0.4)])), 0.3)}


@obj("y2k_glasses", mass=0.02, weight=1.0, hero=(0, -1, 0), **G)
def y2k_glasses(b, rng, pal):
    """The 2000 glasses: the two zeros in the middle are the lenses."""
    b.box((0.16, 0.004, 0.06), mat="frame", bevel=0.001)
    b.plane(0.16, 0.06, loc=(0, -0.0022, 0), rot=(math.pi / 2, 0, 0), mat="front", cuts=2)
    for sx in (-1, 1):
        b.box((0.004, 0.11, 0.004), loc=(sx * 0.078, 0.055, 0.008), mat="arm")
    img = tex.y2k_glasses(rng, "y2k")
    return {"front": PR(img, 0.25, metal=0.6), "frame": P((0.03, 0.03, 0.04), 0.4), "arm": P(BLACK, 0.4)}


@obj("champagne", mass=0.6, weight=1.0, **G)
def champagne(b, rng, pal):
    b.lathe([(0.0, -0.12), (0.035, -0.12), (0.037, 0.02), (0.015, 0.07), (0.013, 0.12), (0.0, 0.12)], mat="glass",
            seg=24, rot=(0, math.pi / 2, 0))
    b.lathe([(0.0, 0.07), (0.016, 0.07), (0.0145, 0.125), (0.0, 0.125)], mat="foil", seg=18, rot=(0, math.pi / 2, 0))
    b.cyl(0.0375, 0.07, loc=(-0.03, 0, 0), rot=(0, math.pi / 2, 0), mat="label", seg=24)
    return {"glass": ("glass", {"color": (0.08, 0.25, 0.1), "rough": 0.05}), "foil": MET((0.85, 0.7, 0.25), 0.25),
            "label": P((0.95, 0.92, 0.85), 0.5)}


# -- ST. PATRICK'S --------------------------------------------------------------------------------

@obj("green_bowler", mass=0.05, weight=1.0, **G)
def green_bowler(b, rng, pal):
    b.cyl(0.07, 0.004, mat="hat", seg=28)
    b.sphere(0.045, loc=(0, 0, 0.01), scale=(1, 1, 0.9), mat="hat", seg=24)
    b.cyl(0.046, 0.012, loc=(0, 0, 0.008), mat="band", seg=24)
    b.extrude(_heart(0.022, 0.022), 0.003, loc=(0.0, -0.047, 0.01), rot=(math.pi / 2, 0, 0), mat="clover")
    return {"hat": P((0.05, 0.55, 0.15), 0.3, coat=0.4), "band": P(BLACK, 0.4), "clover": P((0.95, 0.8, 0.2), 0.3)}


@obj("shamrock_beads", mass=0.02, weight=1.0, **FILL)
def shamrock_beads(b, rng, pal):
    n = 26
    for i in range(n):
        a = 2 * math.pi * i / n
        b.sphere(0.0045, loc=(0.035 * math.cos(a), 0.022 * math.sin(a) + 0.004 * math.sin(3 * a), 0), mat="bead", seg=8)
    return {"bead": MET((0.1, 0.65, 0.2), 0.2)}


@obj("pin_button", mass=0.005, weight=1.0, **G)
def pin_button(b, rng, pal):
    b.cyl(0.028, 0.004, mat="rim", seg=24)
    b.plane(0.05, 0.05, loc=(0, 0, 0.0021), mat="face", cuts=2)
    return {"rim": MET((0.8, 0.8, 0.82), 0.3), "face": PR(tex.pin_print(rng, "pin"), 0.3)}


# -- UNDER THE MATTRESS ----------------------------------------------------------------------------

def _ear(lean, s, n=14):
    """One tall rabbit ear as an outline: narrow at the head, round at the tip, leaning out by `lean` radians."""
    pts = []
    for i in range(n + 1):                                   # up the outer edge and round the tip
        t = i / n
        a = math.pi * t
        x, y = 0.22 * s * math.cos(a), 1.55 * s + 0.22 * s * math.sin(a)
        pts.append((x, y))
    pts += [(-0.16 * s, 0.25 * s), (0.16 * s, 0.25 * s)]     # down to the base
    c, sn = math.cos(lean), math.sin(lean)
    return [(x * c - y * sn, x * sn + y * c) for x, y in pts]


@obj("bunny_charm", mass=0.03, weight=1.0, hero=(0, 0, 1), tags=("upright",), **G)
def bunny_charm(b, rng, pal):
    """Our rabbit (the same one on the magazine covers), as a glossy black keepsake: round head, two tall ears
    leaning apart, one eye, a bow tie. Nobody's logo; everybody's bunny."""
    s = float(rng.uniform(0.026, 0.034))
    d = 0.009
    head = [(s * math.cos(2 * math.pi * i / 32), s * math.sin(2 * math.pi * i / 32)) for i in range(32)]
    b.extrude(head, d, mat="black", bevel=0.0015)
    for lean, dx in ((0.38, -0.012), (-0.16, 0.012)):
        b.extrude(_ear(lean, s), d * 0.85, loc=(dx * s / 0.03, 0, 0), mat="black", bevel=0.0012)
    bow = [(-0.75 * s, -1.05 * s), (0, -1.2 * s), (0.75 * s, -1.05 * s), (0.75 * s, -1.6 * s), (0, -1.42 * s),
           (-0.75 * s, -1.6 * s)]
    b.extrude(bow, d * 0.7, mat="black", bevel=0.001)
    b.cyl(0.13 * s, 0.002, loc=(0.32 * s, 0.12 * s, d / 2 + 0.0004), mat="eye", seg=16)
    if rng.random() < 0.5:                                   # some were keychains
        b.tube([(0, s * 1.05, 0), (0.004, s * 1.35, 0), (0, s * 1.6, 0)], 0.0012, mat="ring", seg=6)
    return {"black": P((0.012, 0.012, 0.014), 0.1), "eye": P((0.92, 0.92, 0.9), 0.3), "ring": CHROME()}
