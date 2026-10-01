"""Props for the one-of-ones. They never show up in the regular deal: a one-of-one is made of one idea,
and these are the ideas that needed their own objects."""
import math

from mathutils import Matrix

from .. import tex
from ..geo import rounded_rect
from . import BLACK, CHARCOAL, CHROME, MET, P, PR, RUB, SILVER, T, WHITE, obj

S = dict(group="special", eras=(0, 1, 2, 3, 4))


# -- LANDFILL DRIVE ---------------------------------------------------------------------

@obj("hdd", mass=0.65, weight=1.0, **S)
def hdd(b, rng, pal):
    w, h, d = 0.147, 0.102, 0.026
    b.box((w, h, d), mat="case", bevel=0.002)
    b.plane(0.1, 0.07, loc=(0.0, 0.0, d / 2 + 0.0003), mat="label", cuts=3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.0022, 0.0012, loc=(sx * 0.066, sy * 0.044, d / 2), mat="screw", seg=8)
    b.box((0.004, 0.064, 0.012), loc=(w / 2, 0, -0.004), mat="pins")
    return {"case": MET((0.78, 0.8, 0.82), 0.35), "label": PR(tex.hdd_label(rng, "hdd"), 0.4),
            "screw": CHROME(), "pins": P(BLACK, 0.6)}


# -- GAS FEES -----------------------------------------------------------------------------

@obj("gas_can", mass=0.35, weight=1.0, hero=(0, -1, 0), **S)
def gas_can(b, rng, pal):
    b.box((0.11, 0.06, 0.13), mat="red", bevel=0.012, seg=3)
    b.tube([(0.03, 0, 0.062), (0.045, 0, 0.09), (0.078, 0, 0.1)], 0.008, mat="cap", seg=10)
    b.cyl(0.013, 0.008, loc=(-0.03, 0, 0.067), mat="cap", seg=14)
    b.tube([(-0.02, 0, 0.062), (-0.015, 0, 0.092), (0.015, 0.0, 0.092), (0.02, 0, 0.062)], 0.005, mat="red", seg=8)
    b.plane(0.058, 0.044, loc=(0, -0.0304, 0.0), rot=(math.pi / 2, 0, 0), mat="label", cuts=3)
    return {"red": P((0.82, 0.06, 0.05), 0.35), "cap": P((0.95, 0.8, 0.1), 0.4),
            "label": PR(tex.gas_label(rng, "gc"), 0.4)}


# -- GM ------------------------------------------------------------------------------------

@obj("coffee_mug", mass=0.35, weight=1.0, **S)
def coffee_mug(b, rng, pal):
    b.lathe([(0.0, 0.0), (0.036, 0.0), (0.04, 0.004), (0.04, 0.09), (0.037, 0.09), (0.037, 0.008), (0.0, 0.008)],
            loc=(0, 0, -0.045), mat="cup", seg=28)
    b.tube([(0.038 + 0.034 * math.sin(math.pi * i / 10), 0, -0.03 + 0.064 * i / 10) for i in range(11)], 0.0058,
           mat="cup", seg=8)
    b.cyl(0.0365, 0.0008, loc=(0, 0, 0.035), mat="coffee", seg=24)
    return {"cup": PR(tex.mug_print(rng, "mug"), 0.25), "coffee": P((0.12, 0.06, 0.03), 0.1)}


# -- SLOW MOTION ---------------------------------------------------------------------------

@obj("rescue_can", mass=0.4, weight=1.0, **S)
def rescue_can(b, rng, pal):
    b.lathe([(0.0, -0.11), (0.018, -0.108), (0.03, -0.095), (0.033, -0.06), (0.033, 0.06), (0.03, 0.095),
             (0.018, 0.108), (0.0, 0.11)], mat="can", seg=28, rot=(0, math.pi / 2, 0))
    for x in (-0.04, 0.04):
        b.cyl(0.0336, 0.012, loc=(x, 0, 0), rot=(0, math.pi / 2, 0), mat="band", seg=28)
    b.tube([(-0.07 + 0.14 * i / 12, 0, 0.032 + 0.03 * math.sin(math.pi * i / 12)) for i in range(13)], 0.0035,
           mat="band", seg=8)
    b.tube([(0.095 + 0.03 * i, 0.02 * math.sin(i * 1.3), 0.004 * i) for i in range(6)], 0.0028, mat="band", seg=6)
    return {"can": P((0.88, 0.05, 0.05), 0.28, coat=0.6), "band": P((0.98, 0.85, 0.1), 0.4)}


@obj("whistle", mass=0.03, weight=1.0, **S)
def whistle(b, rng, pal):
    b.box((0.04, 0.018, 0.015), mat="body", bevel=0.005)
    b.box((0.022, 0.011, 0.009), loc=(-0.029, 0, -0.002), mat="body", bevel=0.002)
    b.torus(0.006, 0.0012, loc=(0.026, 0, 0.006), rot=(math.pi / 2, 0, 0), mat="ring", seg=16, rseg=6)
    b.sphere(0.0035, loc=(0.0, 0, 0.0078), scale=(1.6, 1.0, 0.25), mat="hole", seg=10)
    b.tube([(0.03, 0, 0.006), (0.06, 0.02, 0.0), (0.09, -0.01, 0.0), (0.12, 0.015, 0.0)], 0.0015, mat="cord", seg=6)
    return {"body": P((0.9, 0.1, 0.08), 0.3) if rng.random() < 0.6 else MET((0.78, 0.78, 0.8), 0.25),
            "ring": CHROME(), "hole": P(BLACK, 0.9), "cord": P((0.95, 0.85, 0.15), 0.5)}


@obj("sunscreen", mass=0.25, weight=1.0, hero=(0, -1, 0), **S)
def sunscreen(b, rng, pal):
    b.extrude(rounded_rect(0.06, 0.032, 0.012, 4), 0.11, mat="bottle")
    b.plane(0.056, 0.032, loc=(0, -0.0162, -0.005), rot=(math.pi / 2, 0, 0), mat="label", cuts=3)
    b.cyl(0.015, 0.02, loc=(0, 0, 0.065), mat="cap", seg=16)
    return {"bottle": P((0.97, 0.9, 0.3), 0.3), "label": PR(tex.sun_label(rng, "sun"), 0.3),
            "cap": P((0.1, 0.5, 0.95), 0.35)}


@obj("swimsuit", mass=0.05, weight=1.0, **S)
def swimsuit(b, rng, pal):
    pts = [(-0.05, 0.02), (-0.05, -0.02), (-0.038, -0.05), (-0.012, -0.085), (0.0, -0.075), (0.012, -0.085),
           (0.038, -0.05), (0.05, -0.02), (0.05, 0.02), (0.042, 0.05), (0.038, 0.095), (0.026, 0.095),
           (0.022, 0.05), (0.012, 0.038), (0.0, 0.034), (-0.012, 0.038), (-0.022, 0.05), (-0.026, 0.095),
           (-0.038, 0.095), (-0.042, 0.05)]
    b.extrude(pts, 0.003, scale=(1.3, 1.3, 1.0), mat="cloth", bevel=0.0006)
    return {"cloth": ("fabric", {"color": (0.88, 0.06, 0.06)})}


# -- UNDER THE MATTRESS ----------------------------------------------------------------------

@obj("flashlight", mass=0.25, weight=1.0, **S)
def flashlight(b, rng, pal):
    b.lathe([(0.0, -0.09), (0.0125, -0.09), (0.0125, 0.04), (0.0145, 0.046), (0.024, 0.072), (0.0, 0.072)],
            mat="body", seg=24, rot=(0, math.pi / 2, 0))
    b.cyl(0.0205, 0.002, loc=(0.0725, 0, 0), rot=(0, math.pi / 2, 0), mat="bulb", seg=22)
    b.box((0.014, 0.006, 0.004), loc=(0.0, 0, 0.0135), mat="switch", bevel=0.001)
    return {"body": P(tuple(rng.choice([(0.85, 0.1, 0.08), (0.08, 0.08, 0.1), (0.95, 0.8, 0.1)])), 0.35),
            "bulb": P((1.0, 0.95, 0.75), 0.2, glow=2.0), "switch": P(CHARCOAL, 0.4)}


@obj("sock", mass=0.04, weight=1.0, **S)
def sock(b, rng, pal):
    pts = [(-0.02, 0.13), (0.02, 0.13), (0.02, 0.0), (0.075, 0.0), (0.087, -0.02), (0.075, -0.04), (-0.02, -0.04)]
    b.extrude(pts, 0.012, mat="cloth", bevel=0.002)
    return {"cloth": PR(tex.sock_print(rng, "sock"), 0.9)}


# -- the Pixel Hood gift ---------------------------------------------------------------------

@obj("pixel_hoodie", mass=0.4, weight=1.0, hero=(0, -1, 0), **S)
def pixel_hoodie(b, rng, pal):
    """A hoodie laid flat, arms out, built from square steps so it reads as pixels."""
    s = 0.01
    b.box((9 * s, 2.4 * s, 10 * s), loc=(0, 0, -0.5 * s), mat="cloth", bevel=0.0008)
    for sx in (-1, 1):
        for step in range(3):
            b.box((3.3 * s, 2.2 * s, 2.6 * s), loc=(sx * (5.4 + step * 2.5) * s, 0, (1.6 - step * 2.4) * s),
                  mat="cloth", bevel=0.0008)
        b.box((1.4 * s, 2.3 * s, 2.7 * s), loc=(sx * 13.2 * s, 0, -5.6 * s), mat="cuff", bevel=0.0008)
    b.box((9 * s, 2.5 * s, 1.3 * s), loc=(0, 0, -6.1 * s), mat="cuff", bevel=0.0008)
    for w, z in ((7, 5.6), (5.4, 6.9), (3.6, 8.0)):
        b.box((w * s, 2.6 * s, 1.3 * s), loc=(0, 0.1 * s, z * s), mat="cloth", bevel=0.0008)
    b.box((2.6 * s, 0.6 * s, 2.6 * s), loc=(0, -1.3 * s, 6.2 * s), mat="void", bevel=0.0004)
    b.box((6 * s, 0.6 * s, 2.6 * s), loc=(0, -1.3 * s, -2.8 * s), mat="pocket", bevel=0.0006)
    for sx in (-1, 1):
        b.box((0.45 * s, 0.45 * s, 3.4 * s), loc=(sx * 1.3 * s, -1.3 * s, 2.6 * s), mat="string")
    cloth = [(0.42, 0.12, 0.65), (0.08, 0.08, 0.1), (0.25, 0.08, 0.4)][int(rng.choice(3, p=[0.6, 0.15, 0.25]))]
    return {"cloth": ("fabric", {"color": cloth}), "cuff": ("fabric", {"color": (0.55, 1.0, 0.1)}),
            "void": P((0.01, 0.01, 0.015), 0.9), "pocket": ("fabric", {"color": tuple(x * 0.7 for x in cloth)}),
            "string": P((0.55, 1.0, 0.1), 0.7)}


@obj("studio_headphones", mass=0.25, weight=1.0, hero=(0, -1, 0), **S)
def studio_headphones(b, rng, pal):
    b.tube([(0.075 * math.cos(a), 0, 0.09 * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]], 0.006,
           mat="band", seg=8)
    for sx in (-1, 1):
        b.cyl(0.039, 0.028, loc=(sx * 0.081, 0, 0), rot=(0, math.pi / 2, 0), mat="cup", seg=24)
        b.torus(0.03, 0.0095, loc=(sx * 0.064, 0, 0), rot=(0, math.pi / 2, 0), mat="pad", seg=22, rseg=8)
    return {"band": P(CHARCOAL, 0.4), "cup": MET(tuple(rng.choice([(0.1, 0.1, 0.11), SILVER, (0.85, 0.1, 0.1)])), 0.3),
            "pad": ("fabric", {"color": (0.08, 0.08, 0.09)})}


@obj("synth_keys", mass=0.6, weight=1.0, **S)
def synth_keys(b, rng, pal):
    n = 10
    for i in range(n):
        b.box((0.0233, 0.15, 0.02), loc=((i - (n - 1) / 2) * 0.0238, -0.03, 0.0), mat="white", bevel=0.001)
    for i in (0, 1, 3, 4, 5, 7, 8):
        b.box((0.014, 0.09, 0.013), loc=((i - (n - 1) / 2 + 0.5) * 0.0238, -0.0, 0.0145), mat="black", bevel=0.001)
    b.box((0.25, 0.06, 0.035), loc=(0, 0.075, 0.0075), mat="body", bevel=0.004)
    for i in range(6):
        b.cyl(0.0075, 0.012, loc=(-0.08 + i * 0.026, 0.085, 0.03), mat="knob", seg=14)
    b.plane(0.05, 0.022, loc=(0.085, 0.068, 0.0257), mat="lcd")
    return {"white": P((0.93, 0.92, 0.88), 0.4), "black": P((0.04, 0.04, 0.045), 0.35),
            "body": P(tuple(rng.choice([(0.12, 0.12, 0.14), (0.75, 0.15, 0.1), (0.75, 0.75, 0.78)])), 0.4),
            "knob": P((0.85, 0.85, 0.88), 0.3),
            "lcd": PR(tex.lcd(rng, "syn", "808", bg=(0.05, 0.2, 0.1), ink=(0.4, 1.0, 0.5)), 0.2)}


@obj("ribbon_cable", mass=0.05, weight=1.0, **S)
def ribbon_cable(b, rng, pal):
    rows = []
    for j in range(2):
        rows.append([(-0.11 + 0.22 * i / 14, 0.0075 * (j * 2 - 1), 0.004 * math.sin(i * 0.6)) for i in range(15)])
    b.loft(rows, mat="wires", closed=False, cap=False)
    for sx in (-1, 1):
        b.box((0.012, 0.03, 0.008), loc=(sx * 0.117, 0, 0), mat="plug", bevel=0.001)
    return {"wires": PR(tex.spectrum_print(rng, "rc"), 0.5), "plug": P(BLACK, 0.5)}


# -- CCFF00 --------------------------------------------------------------------------------

@obj("neon_tube", mass=0.05, weight=1.0, **S)
def neon_tube(b, rng, pal):
    kind = int(rng.integers(0, 3))
    if kind == 0:
        pts = [(-0.1 + 0.2 * i / 24, 0.03 * math.sin(i * 0.55), 0.0) for i in range(25)]
    elif kind == 1:
        pts = [(0.05 * math.cos(a), 0.05 * math.sin(a), 0.0) for a in [0.4 + 5.2 * i / 24 for i in range(25)]]
    else:
        pts = [(-0.09, 0.0, 0.0), (-0.06, 0.04, 0.0), (-0.03, -0.04, 0.0), (0.0, 0.04, 0.0), (0.03, -0.04, 0.0),
               (0.06, 0.04, 0.0), (0.09, 0.0, 0.0)]
    b.tube(pts, 0.0045, mat="glass", seg=10)
    for p in (pts[0], pts[-1]):
        b.cyl(0.0065, 0.012, loc=(p[0], p[1], 0.0), mat="cap", seg=10)
    col = tuple(rng.choice([(0.8, 1.0, 0.0), (1.0, 0.2, 0.6), (0.2, 0.8, 1.0)]))
    return {"glass": P(col, 0.15, glow=5.0), "cap": P(BLACK, 0.5)}


@obj("highlighter", mass=0.02, weight=1.0, **S)
def highlighter(b, rng, pal):
    b.lathe([(0.0, -0.06), (0.0078, -0.06), (0.0078, 0.03), (0.0055, 0.05), (0.0035, 0.055), (0.0, 0.055)],
            mat="body", seg=16, rot=(0, math.pi / 2, 0))
    b.cyl(0.0092, 0.04, loc=(-0.045, 0, 0), rot=(0, math.pi / 2, 0), mat="cap", seg=16)
    b.box((0.03, 0.002, 0.003), loc=(-0.05, 0, 0.0105), mat="body")
    col = tuple(rng.choice([(0.95, 1.0, 0.1), (1.0, 0.35, 0.7), (0.4, 1.0, 0.3), (1.0, 0.6, 0.1)]))
    return {"body": P(col, 0.35), "cap": T(col, 0.12)}


@obj("tennis_ball", mass=0.058, weight=1.0, **S)
def tennis_ball(b, rng, pal):
    R = 0.033
    b.sphere(R, mat="felt", seg=22)
    pts = []
    for i in range(41):
        t = 2 * math.pi * i / 40
        p = (0.62 * math.cos(t) + 0.2 * math.cos(3 * t), 0.62 * math.sin(t) - 0.2 * math.sin(3 * t),
             0.38 * math.sin(2 * t))
        n = math.sqrt(sum(c * c for c in p))
        pts.append(tuple(c / n * R * 1.003 for c in p))
    b.tube(pts, 0.0012, mat="seam", seg=6, cap=False)
    return {"felt": ("fabric", {"color": (0.85, 0.95, 0.15)}), "seam": P((0.95, 0.95, 0.9), 0.6)}


# -- Hood Street -----------------------------------------------------------------------------

@obj("street_sign", mass=0.35, weight=1.0, **S)
def street_sign(b, rng, pal):
    b.box((0.2, 0.05, 0.0018), mat="plate", bevel=0.0006)
    b.plane(0.198, 0.048, loc=(0, 0, 0.001), mat="face", cuts=4)
    for sx in (-1, 1):
        b.cyl(0.0025, 0.0025, loc=(sx * 0.09, 0, 0.0012), mat="bolt", seg=8)
    return {"plate": MET((0.7, 0.72, 0.74), 0.4), "face": PR(tex.street_sign(rng, "hs"), 0.3, metal=0.4),
            "bolt": CHROME()}


@obj("newspaper", mass=0.1, weight=1.0, **S)
def newspaper(b, rng, pal):
    rows = []
    for j in range(9):
        y = -0.12 + 0.24 * j / 8
        rows.append([(-0.085 + 0.17 * i / 8, y, 0.014 * (1 - abs(i - 4) / 4) + 0.001 * math.sin(j)) for i in range(9)])
    b.loft(rows, mat="paper", closed=False, cap=False)
    return {"paper": PR(tex.newspaper(rng, "np"), 0.9)}


@obj("microphone", mass=0.3, weight=1.0, **S)
def microphone(b, rng, pal):
    b.cyl(0.011, 0.11, loc=(0, 0, -0.03), mat="handle", seg=16)
    b.sphere(0.028, loc=(0, 0, 0.05), mat="grille", seg=20)
    b.torus(0.026, 0.004, loc=(0, 0, 0.03), mat="ring", seg=22, rseg=8)
    b.tube([(0, 0, -0.085), (0.01, 0.02, -0.11), (-0.02, 0.05, -0.12), (0.03, 0.09, -0.12)], 0.0025, mat="cord", seg=6)
    return {"handle": P((0.06, 0.06, 0.07), 0.45), "grille": MET((0.55, 0.56, 0.58), 0.5), "ring": CHROME(),
            "cord": P(BLACK, 0.6)}


@obj("press_badge", mass=0.02, weight=1.0, **S)
def press_badge(b, rng, pal):
    b.box((0.055, 0.085, 0.0022), mat="card", bevel=0.0008)
    b.plane(0.053, 0.083, loc=(0, 0, 0.00115), mat="face", cuts=3)
    b.box((0.014, 0.008, 0.003), loc=(0, 0.046, 0), mat="clip")
    b.tube([(-0.008, 0.05, 0.0), (-0.025, 0.09, 0.0), (0.0, 0.125, 0.0), (0.025, 0.09, 0.0), (0.008, 0.05, 0.0)],
           0.0035, mat="lanyard", seg=8)
    return {"card": P(WHITE, 0.4), "face": PR(tex.badge_print(rng, "pb"), 0.3), "clip": MET(SILVER, 0.3),
            "lanyard": ("fabric", {"color": (0.85, 0.1, 0.1)})}


@obj("play_money", mass=0.004, weight=1.0, **S)
def play_money(b, rng, pal):
    for i in range(3):
        b.plane(0.156, 0.066, loc=(float(rng.normal(0, 0.006)), float(rng.normal(0, 0.006)), i * 0.0006),
                rot=(0, 0, float(rng.normal(0, 0.12))), mat=f"bill{i}", cuts=6)
    return {f"bill{i}": PR(tex.play_money(rng, f"bill{i}"), 0.6) for i in range(3)}


@obj("playing_cards", mass=0.03, weight=1.0, **S)
def playing_cards(b, rng, pal):
    specs = {}
    for i in range(4):
        b.frame = Matrix.Translation((0, -0.03, 0.0009 * i)) @ Matrix.Rotation((i - 1.5) * 0.3, 4, "Z")
        b.plane(0.045, 0.064, loc=(0, 0.03, 0), mat=f"c{i}", cuts=3)
        specs[f"c{i}"] = PR(tex.card_print(rng, f"card{i}"), 0.35)
    b.frame = Matrix.Identity(4)
    return specs


# -- COLD STORAGE -------------------------------------------------------------------------

@obj("cold_wallet", mass=0.08, weight=1.0, **S)
def cold_wallet(b, rng, pal):
    """A hardware wallet at a size you can read from across a room. The screen keeps its own material, so
    it still says SEED? from inside the ice."""
    w, h, d = 0.125, 0.052, 0.014
    b.box((w, h, d), mat="body", bevel=0.004)
    b.plane(0.058, 0.022, loc=(-0.018, 0.0, d / 2 + 0.0004), mat="screen", cuts=2)
    for x in (0.036, 0.05):
        b.cyl(0.0042, 0.0016, loc=(x, 0.0, d / 2), mat="btn", seg=12)
    b.box((0.012, 0.03, 0.008), loc=(w / 2, 0, 0), mat="btn")
    return {"body": T((0.2, 0.2, 0.22), 0.3), "btn": MET((0.7, 0.7, 0.72), 0.3),
            "screen": PR(tex.lcd(rng, "cw", str(rng.choice(["SEED?", "PIN?", "WIPED", "CONFIRM"])),
                                 bg=(0.02, 0.02, 0.03), ink=(0.95, 0.97, 1.0)), 0.1, keep=True)}
