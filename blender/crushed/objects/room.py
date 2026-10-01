"""The bedroom, every decade of it: blacklight posters, lava lamps, plasma balls, glow stars, beaded curtains,
trolls, mood rings, dream catchers, inflatable chairs, bean bags, neon signs. Regular-cube stock (group "era")."""
import math

import numpy as np

from .. import tex
from . import BLACK, MET, P, PR, T, WHITE, obj

R = dict(group="era")
NEONS = [(1.0, 0.1, 0.8), (0.2, 1.0, 0.2), (1.0, 0.55, 0.0), (0.1, 0.6, 1.0), (1.0, 1.0, 0.1), (0.6, 0.1, 1.0)]


def _fuzzy_print(rng, name):
    """A flocked blacklight poster: a black field with day-glo shapes (mushrooms, a skull, a peace sign, a tiger,
    a psychedelic eye) glowing under UV."""
    c = tex.Canvas(256, 352, bg=(0.02, 0.02, 0.03, 1))
    cols = [NEONS[i] for i in rng.permutation(len(NEONS))]
    kind = int(rng.integers(0, 4))
    if kind == 0:                                   # mushrooms
        for i, (x, y, r) in enumerate(((0.3, 0.35, 0.16), (0.68, 0.42, 0.2), (0.5, 0.2, 0.1))):
            c.rect(x - r * 0.25, 0.05, x + r * 0.25, y, cols[(i + 1) % 6])
            c.circle(x, y, r, cols[i])
            for _ in range(5):
                c.circle(x + rng.uniform(-r, r) * 0.7, y + rng.uniform(0, r) * 0.6, r * 0.12, cols[(i + 2) % 6])
    elif kind == 1:                                 # the eye
        for k in range(8, 0, -1):
            c.circle(0.5, 0.5, 0.06 * k, cols[k % 6])
        c.circle(0.5, 0.5, 0.08, (0.02, 0.02, 0.03))
    elif kind == 2:                                 # peace sign in rings
        c.circle(0.5, 0.52, 0.4, cols[0], ring=0.05)
        c.rect(0.475, 0.14, 0.525, 0.9, cols[0])
        c.poly([(0.5, 0.52), (0.18, 0.28), (0.21, 0.24), (0.5, 0.46)], cols[0])
        c.poly([(0.5, 0.52), (0.82, 0.28), (0.79, 0.24), (0.5, 0.46)], cols[0])
        for i in range(30):
            c.circle(rng.uniform(0.02, 0.98), rng.uniform(0.02, 0.98), 0.012, cols[i % 6])
    else:                                           # zigzag waves
        for i in range(10):
            y = 0.06 + i * 0.095
            pts = [(x / 10, y + (0.03 if x % 2 else -0.03)) for x in range(11)]
            c.line(pts, 0.025, cols[i % 6])
    c.noise(rng, 0.05)                              # the flock
    return c.image(name)


@obj("fuzzy_poster", eras=(0, 1, 2), mass=0.05, weight=1.6, hero=(0, -1, 0), **R)
def fuzzy_poster(b, rng, pal):
    """A flocked velvet blacklight poster, curling off the wall, thumbtack holes in the corners."""
    b.plane(0.17, 0.23, rot=(math.pi / 2, 0, 0), mat="poster", cuts=12)
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.cyl(0.004, 0.004, loc=(sx * 0.078, -0.002, sz * 0.108), rot=(math.pi / 2, 0, 0), mat="tack", seg=8)
    return {"poster": PR(_fuzzy_print(rng, "fz"), 0.95, glow=0.9),
            "tack": MET(tuple(rng.choice([(0.85, 0.2, 0.2), (0.2, 0.4, 0.9), (0.85, 0.8, 0.2)])), 0.3)}


@obj("blacklight", eras=(0, 1, 2), mass=0.4, weight=1.0, hero=(0, -1, 0), **R)
def blacklight(b, rng, pal):
    """An 18-inch blacklight tube in its black plastic fixture, the tube glowing purple."""
    b.box((0.2, 0.03, 0.03), mat="housing", bevel=0.004)
    b.cyl(0.011, 0.19, loc=(0, -0.018, 0), rot=(0, math.pi / 2, 0), mat="tube", seg=16)
    b.tube([(0.1, 0, 0), (0.13, 0.01, -0.02), (0.15, -0.01, -0.05)], 0.003, mat="housing", seg=6)
    return {"housing": P(BLACK, 0.5), "tube": P((0.45, 0.1, 1.0), 0.2, glow=3.0)}


@obj("lava_lamp_era", eras=(0, 1, 2, 3, 4), mass=0.6, weight=1.6, hero=(0, -1, 0), tags=("upright",), **R)
def lava_lamp_era(b, rng, pal):
    """The rocket-shaped lava lamp: gold cone base, tapered glass, glowing wax blobs, gold cap."""
    b.lathe([(0.0, 0.0), (0.028, 0.0), (0.042, 0.05), (0.03, 0.17), (0.02, 0.2), (0.0, 0.2)], loc=(0, 0, -0.1),
            mat="glass", seg=28)
    b.lathe([(0.0, 0.0), (0.046, 0.0), (0.03, 0.075), (0.0, 0.075)], loc=(0, 0, -0.175), mat="base", seg=28)
    b.cyl(0.019, 0.028, loc=(0, 0, 0.112), mat="base", seg=20, r2=0.012)
    for z, r in ((-0.075, 0.02), (-0.03, 0.016), (0.02, 0.014), (0.06, 0.011)):
        b.sphere(r, loc=(float(rng.normal(0, 0.004)), float(rng.normal(0, 0.004)), z), scale=(1, 1, 1.5), mat="wax",
                 seg=14)
    pairs = [((1.0, 0.25, 0.05), (0.9, 0.85, 0.2)), ((1.0, 0.2, 0.6), (0.2, 0.1, 0.5)), ((0.2, 0.9, 0.2), (0.1, 0.3, 0.8)),
             ((1.0, 0.6, 0.1), (0.6, 0.05, 0.1))]
    goo, liq = pairs[int(rng.integers(len(pairs)))]
    return {"glass": ("glass", {"color": liq, "trans": 1.0, "rough": 0.03}),
            "base": MET(tuple(rng.choice([(0.85, 0.72, 0.35), (0.75, 0.75, 0.78), (0.1, 0.1, 0.12)])), 0.3),
            "wax": P(goo, 0.25, glow=2.0)}


@obj("plasma_ball", eras=(1, 2, 3), mass=0.8, weight=1.2, hero=(0, -1, 0), tags=("upright",), **R)
def plasma_ball(b, rng, pal):
    """A plasma ball: clear globe on a black base, a glowing core, purple lightning filaments to the glass."""
    b.sphere(0.06, loc=(0, 0, 0.03), mat="glass", seg=28)
    b.lathe([(0.0, 0.0), (0.045, 0.0), (0.04, 0.05), (0.025, 0.06), (0.0, 0.06)], loc=(0, 0, -0.085), mat="base", seg=24)
    b.sphere(0.01, loc=(0, 0, 0.03), mat="bolt", seg=12)
    for _ in range(9):
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        pts = [(0, 0, 0.03)]
        for k in range(1, 7):
            p = d * 0.055 * k / 6 + rng.normal(0, 0.004, 3)
            pts.append((float(p[0]), float(p[1]), float(p[2] + 0.03)))
        b.tube(pts, 0.0012, mat="bolt", seg=5)
    return {"glass": ("glass", {"color": (0.9, 0.9, 1.0), "trans": 1.0, "rough": 0.02}), "base": P(BLACK, 0.4),
            "bolt": P((0.75, 0.3, 1.0), 0.2, glow=6.0)}


@obj("glow_stars", eras=(1, 2, 3), mass=0.01, weight=1.4, hero=(0, 0, 1), **R)
def glow_stars(b, rng, pal):
    """A handful of glow-in-the-dark ceiling stars and a crescent moon, sticky putty still on the backs."""
    def star(cx, cy, r):
        return [(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(math.pi / 2 + i * math.pi / 5),
                 cy + (r if i % 2 == 0 else r * 0.45) * math.sin(math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    for _ in range(int(rng.integers(5, 9))):
        cx, cy = rng.uniform(-0.06, 0.06, 2)
        b.extrude(star(float(cx), float(cy), float(rng.uniform(0.012, 0.024))), 0.002, loc=(0, 0, float(rng.uniform(0, 0.004))), mat="glow")
    moon = [(0.03 * math.cos(a), 0.03 * math.sin(a)) for a in np.linspace(-1.9, 1.9, 16)]
    moon += [(0.012 + 0.022 * math.cos(a), 0.022 * math.sin(a)) for a in np.linspace(1.6, -1.6, 14)]
    b.extrude(moon, 0.002, loc=(0.04, -0.05, 0), mat="glow")
    return {"glow": P((0.75, 1.0, 0.65), 0.6, glow=1.8)}


@obj("beaded_curtain", eras=(0, 1, 2), mass=0.2, weight=1.0, hero=(0, -1, 0), **R)
def beaded_curtain(b, rng, pal):
    """A tangle of strands torn off a beaded curtain: clear and colored plastic beads on string."""
    for i in range(7):
        x = -0.06 + i * 0.02
        pts = [(x + 0.01 * math.sin(k * 0.7 + i), 0.0, 0.1 - k * 0.012) for k in range(17)]
        b.tube(pts, 0.0006, mat="string", seg=4)
        for k, p in enumerate(pts[::2]):
            b.sphere(0.0045, loc=p, scale=(1, 1, 1.3), mat=f"bead{(i + k) % 3}", seg=10)
    return {"string": P(WHITE, 0.6), "bead0": T(tuple(rng.choice(NEONS)), 0.1), "bead1": T((0.9, 0.9, 0.95), 0.05),
            "bead2": T(tuple(rng.choice(NEONS)), 0.1)}


@obj("troll_doll", eras=(1, 2), mass=0.08, weight=1.4, hero=(0, -1, 0), tags=("upright",), **R)
def troll_doll(b, rng, pal):
    """A pencil-topper troll: chubby vinyl body, wide grin, a tall shock of neon hair."""
    b.sphere(0.022, loc=(0, 0, -0.02), scale=(1, 0.9, 1.1), mat="skin", seg=20)
    b.sphere(0.02, loc=(0, 0, 0.018), mat="skin", seg=20)
    for sx in (-1, 1):
        b.sphere(0.005, loc=(sx * 0.007, -0.017, 0.022), mat="eye", seg=10)
        b.sphere(0.006, loc=(sx * 0.022, 0, 0.018), scale=(0.6, 1, 1.4), mat="skin", seg=10)
        b.cyl(0.006, 0.014, loc=(sx * 0.01, 0, -0.046), mat="skin", seg=10)
    b.box((0.012, 0.002, 0.002), loc=(0, -0.019, 0.01), mat="eye")
    for _ in range(40):
        a, t = rng.uniform(0, 6.28), rng.uniform(-0.4, 0.4)
        base = (0.008 * math.cos(a), 0.008 * math.sin(a), 0.036)
        top = (base[0] * 2.5 + t * 0.02, base[1] * 2.5, 0.036 + rng.uniform(0.04, 0.06))
        b.tube([base, top], 0.0012, mat="hair", seg=4)
    return {"skin": P((0.95, 0.75, 0.6), 0.6), "eye": P((0.05, 0.05, 0.08), 0.3), "hair": P(tuple(rng.choice(NEONS)), 0.7)}


@obj("mood_ring", eras=(0, 1), mass=0.01, weight=1.0, hero=(0, 0, 1), **R)
def mood_ring(b, rng, pal):
    """A mood ring: thin silver band, a big oval stone shifting blue-green-purple."""
    b.torus(0.009, 0.0015, mat="band", seg=28, rseg=8)
    b.sphere(0.008, loc=(0, -0.01, 0.0), scale=(1.3, 0.5, 1.0), mat="stone", seg=18)
    return {"band": MET((0.8, 0.8, 0.82), 0.25), "stone": ("glass", {"color": tuple(rng.choice([(0.1, 0.5, 0.9),
            (0.2, 0.9, 0.5), (0.5, 0.1, 0.8), (0.1, 0.1, 0.1)])), "trans": 0.4, "rough": 0.05})}


@obj("dream_catcher", eras=(1, 2), mass=0.04, weight=1.0, hero=(0, -1, 0), **R)
def dream_catcher(b, rng, pal):
    """A mall dream catcher: suede-wrapped hoop, a web, plastic beads, three dangling feathers."""
    b.torus(0.05, 0.003, rot=(math.pi / 2, 0, 0), mat="hoop", seg=40, rseg=8)
    for i in range(8):
        a = i * math.pi / 4
        b.tube([(0.05 * math.cos(a), 0, 0.05 * math.sin(a)), (0.012 * math.cos(a + 0.6), 0, 0.012 * math.sin(a + 0.6))],
               0.0006, mat="web", seg=4)
    for i, x in enumerate((-0.03, 0.0, 0.03)):
        b.tube([(x, 0, -0.05), (x, 0, -0.08)], 0.0007, mat="web", seg=4)
        b.sphere(0.004, loc=(x, 0, -0.075), mat="bead", seg=8)
        b.extrude([(0, 0), (0.006, -0.02), (0, -0.05), (-0.006, -0.02)], 0.001, loc=(x, 0, -0.08), rot=(math.pi / 2, 0, 0), mat="feather")
    return {"hoop": ("fabric", {"color": (0.45, 0.28, 0.15)}), "web": P((0.9, 0.88, 0.8), 0.7),
            "bead": P(tuple(rng.choice(NEONS)), 0.3), "feather": ("fabric", {"color": tuple(rng.choice([(0.95, 0.95, 0.9), (0.6, 0.4, 0.25), (0.2, 0.6, 0.9)]))})}


@obj("inflatable_chair", eras=(1, 2), mass=0.6, weight=1.0, hero=(0, -1, 0), big=True, **R)
def inflatable_chair(b, rng, pal):
    """A crushed inflatable chair: translucent neon vinyl tubes, the valve, the seams."""
    for k in range(3):
        b.torus(0.07 - k * 0.006, 0.022, loc=(0, 0, k * 0.035), mat="vinyl", seg=36, rseg=14)
    b.cyl(0.006, 0.01, loc=(0.075, 0, 0.03), rot=(0, math.pi / 2, 0), mat="valve", seg=10)
    return {"vinyl": T(tuple(rng.choice(NEONS)), 0.15), "valve": P(WHITE, 0.4)}


@obj("bean_bag_chunk", eras=(1, 2, 3), mass=0.5, weight=1.0, hero=(0, 0, 1), **R)
def bean_bag_chunk(b, rng, pal):
    """A torn corner of a bean bag chair: vinyl or corduroy, the zipper, foam beads spilling out."""
    b.sphere(0.07, scale=(1.2, 1.0, 0.55), mat="cover", seg=24)
    b.box((0.09, 0.004, 0.004), loc=(0, -0.06, 0.0), mat="zip")
    for _ in range(60):
        p = rng.normal(0, 1, 3) * np.array([0.05, 0.05, 0.02]) + np.array([0.06, -0.03, 0.03])
        b.sphere(0.003, loc=tuple(float(x) for x in p), mat="bead", seg=6)
    return {"cover": ("fabric", {"color": tuple(rng.choice([(0.9, 0.1, 0.5), (0.1, 0.1, 0.12), (0.3, 0.1, 0.6), (0.95, 0.5, 0.05)]))}),
            "zip": MET((0.7, 0.7, 0.7), 0.3), "bead": P((0.97, 0.97, 0.95), 0.6)}


@obj("neon_sign", eras=(0, 1, 2, 3, 4), mass=0.5, weight=1.0, hero=(0, -1, 0), **R)
def neon_sign(b, rng, pal):
    """A small bent-glass neon sign (a heart, a lightning bolt, a cocktail glass) on a black backing grid."""
    b.box((0.18, 0.006, 0.12), mat="back")
    kind = int(rng.integers(0, 3))
    if kind == 0:
        pts = [(0.06 * math.sin(t) ** 3 * 1.6, -0.006, 0.04 * math.cos(t) - 0.016 * math.cos(2 * t) - 0.006 * math.cos(3 * t))
               for t in np.linspace(0, 2 * math.pi, 40)]
    elif kind == 1:
        pts = [(-0.02, -0.006, 0.05), (0.02, -0.006, 0.01), (-0.01, -0.006, 0.0), (0.03, -0.006, -0.05)]
    else:                                           # cocktail glass: rim, cone, stem, foot, olive
        pts = [(-0.045, -0.006, 0.045), (0.045, -0.006, 0.045), (0.0, -0.006, -0.01), (-0.045, -0.006, 0.045)]
        b.tube([(0.0, -0.006, -0.01), (0.0, -0.006, -0.045)], 0.0035, mat="glass", seg=8)
        b.tube([(-0.025, -0.006, -0.048), (0.025, -0.006, -0.048)], 0.0035, mat="glass", seg=8)
        b.torus(0.008, 0.003, loc=(0.012, -0.006, 0.028), rot=(math.pi / 2, 0, 0), mat="glass", seg=16, rseg=6)
    b.tube([tuple(map(float, p)) for p in pts], 0.004, mat="glass", seg=8)
    return {"back": P(BLACK, 0.5), "glass": P(tuple(rng.choice(NEONS)), 0.2, glow=5.0)}


@obj("tie_dye_shirt", eras=(0, 1, 2), mass=0.2, weight=1.2, hero=(0, 0, 1), **R)
def tie_dye_shirt(b, rng, pal):
    """A wadded tie-dye T-shirt, the spiral of the dye still showing."""
    c = tex.Canvas(256, 256)
    cols = [NEONS[i] for i in rng.permutation(len(NEONS))]
    for k in range(24, 0, -1):
        c.circle(0.5, 0.5, 0.03 * k, cols[k % 4], soft=0.02)
    b.plane(0.16, 0.18, mat="cloth", cuts=14)
    return {"cloth": PR(c.image("td"), 0.95)}


LORE_NAMES = {"fuzzy_poster": "Fuzzy Blacklight Poster", "blacklight": "Blacklight Tube", "lava_lamp_era": "Lava Lamp",
              "plasma_ball": "Plasma Ball", "glow_stars": "Glow-in-the-Dark Stars", "beaded_curtain": "Beaded Curtain",
              "troll_doll": "Troll Doll", "mood_ring": "Mood Ring", "dream_catcher": "Mall Dream Catcher",
              "inflatable_chair": "Inflatable Chair", "bean_bag_chunk": "Bean Bag Chair (Torn)", "neon_sign": "Neon Sign",
              "tie_dye_shirt": "Tie-Dye Shirt"}
LORE_NOTES = {
    "fuzzy_poster": ["only looked good under the blacklight", "bought at the mall kiosk next to the incense",
                     "four thumbtacks, one missing"],
    "blacklight": ["made every white sock glow", "mom thought it was for plants"],
    "lava_lamp_era": ["took an hour to warm up, watched every minute", "never turned off, never moved"],
    "plasma_ball": ["everyone touched it", "Spencer's Gifts, 1996"],
    "glow_stars": ["stuck to the ceiling in a real constellation, allegedly", "glowed for eleven minutes"],
    "beaded_curtain": ["the door you didn't have", "clacked every time"],
    "troll_doll": ["on the end of a pencil", "hair rubbed for luck before every test"],
    "mood_ring": ["always black", "it said you were calm, you were not"],
    "dream_catcher": ["hung from a rearview mirror", "caught nothing"],
    "inflatable_chair": ["popped by a cat", "stuck to your legs in summer"],
    "bean_bag_chunk": ["beads everywhere for a decade", "the vacuum never recovered"],
    "neon_sign": ["bought it, never hung it", "the buzz you could hear in the next room"],
    "tie_dye_shirt": ["made at camp", "dyed your hands for a week"],
}
