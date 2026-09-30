"""2009-2026. The phone ate everything. What's left is chargers, masks and regret.

Generic shapes only, like the rest of the library: a slab is a slab.
"""
import math

from mathutils import Matrix

from .. import tex
from ..geo import rounded_rect
from . import BLACK, CHARCOAL, MET, P, PR, RUB, SILVER, T, WHITE, obj

M = dict(eras=(4,))
ROSE = (0.85, 0.62, 0.55)


def _slab_colors(rng):
    return MET(tuple(rng.choice([SILVER, (0.1, 0.1, 0.12), ROSE, (0.2, 0.3, 0.45), (0.82, 0.82, 0.84)])), 0.3)


@obj("smartphone", mass=0.17, weight=2.0, **M)
def smartphone(b, rng, pal):
    w, h, d = 0.072, 0.152, 0.0078
    b.box((w, h, d), mat="body", bevel=0.0065, seg=3)
    b.plane(w * 0.93, h * 0.955, loc=(0, 0, d / 2 + 0.0003), mat="lcd", cuts=6)
    b.box((0.034, 0.034, 0.0018), loc=(-0.0135, h / 2 - 0.0225, -d / 2 - 0.0008), mat="bump", bevel=0.005)
    for (x, y) in ((-0.0225, h / 2 - 0.0155), (-0.0045, h / 2 - 0.0155), (-0.0225, h / 2 - 0.0295),
                   (-0.0045, h / 2 - 0.0295)):
        b.cyl(0.0048, 0.0016, loc=(x, y, -d / 2 - 0.0018), mat="lens", seg=16)
    cased = rng.random() < 0.55
    if cased:
        for sx in (-1, 1):
            b.box((0.0045, h + 0.006, d + 0.004), loc=(sx * (w / 2 + 0.0015), 0, 0), mat="case", bevel=0.0015)
        for sy in (-1, 1):
            b.box((w + 0.009, 0.0045, d + 0.004), loc=(0, sy * (h / 2 + 0.0015), 0), mat="case", bevel=0.0015)
    body = _slab_colors(rng)
    return {"body": body, "bump": body, "lens": ("lens", {}),
            "case": RUB(tuple(rng.choice([(0.9, 0.3, 0.45), (0.1, 0.1, 0.1), (0.3, 0.7, 0.9), (0.8, 1.0, 0.0)]))),
            "lcd": ("screen", {"image": (tex.app_grid if rng.random() < 0.6 else tex.lockscreen)(rng, "ph"),
                               "glow": 0.3, "crack_scale": float(rng.uniform(6, 14))})}


@obj("tablet", mass=0.47, weight=1.2, **M)
def tablet(b, rng, pal):
    w, h, d = 0.17, 0.24, 0.0075
    b.box((w, h, d), mat="body", bevel=0.007, seg=3)
    b.plane(w * 0.92, h * 0.93, loc=(0, 0, d / 2 + 0.0003), mat="lcd", cuts=6)
    b.cyl(0.0045, 0.0015, loc=(-w / 2 + 0.01, h / 2 - 0.012, -d / 2 - 0.001), mat="lens", seg=12)
    if rng.random() < 0.6:
        for sx in (-1, 1):
            b.box((0.011, h + 0.01, d + 0.008), loc=(sx * (w / 2 + 0.002), 0, 0), mat="case", bevel=0.003)
        for sy in (-1, 1):
            b.box((w + 0.02, 0.011, d + 0.008), loc=(0, sy * (h / 2 + 0.002), 0), mat="case", bevel=0.003)
    return {"body": _slab_colors(rng), "lens": ("lens", {}),
            "case": RUB(tuple(rng.choice([(0.15, 0.6, 0.95), (0.95, 0.4, 0.2), (0.3, 0.8, 0.4), (0.1, 0.1, 0.1)]))),
            "lcd": ("screen", {"image": tex.app_grid(rng, "tb"), "glow": 0.3, "crack_scale": 5.0})}


@obj("earbuds_case", mass=0.05, weight=1.6, **M)
def earbuds_case(b, rng, pal):
    w, h, d = 0.058, 0.046, 0.022
    b.extrude(rounded_rect(w, h, 0.016, 5), d * 0.55, loc=(0, 0, -d * 0.225), mat="body")
    ang = rng.uniform(1.7, 2.5)
    b.frame = Matrix.Translation((0, h / 2, d * 0.05)) @ Matrix.Rotation(-ang, 4, "X")
    b.extrude(rounded_rect(w, h, 0.016, 5), d * 0.45, loc=(0, -h / 2, d * 0.22), mat="body")
    b.frame = Matrix.Identity(4)
    for sx in (-1, 1):
        x = sx * 0.0135
        b.sphere(0.0085, loc=(x, 0.002, d * 0.05 + 0.006), scale=(1, 1, 0.9), mat="bud", seg=14)
        b.tube([(x, 0.002, d * 0.05 + 0.004), (x + sx * 0.0015, -0.006, d * 0.05 + 0.0015)], 0.0024, mat="bud", seg=8)
    b.sphere(0.0018, loc=(0, -h / 2 + 0.004, d * 0.05), mat="led", seg=8)
    col = P(tuple(rng.choice([WHITE, BLACK, (0.85, 0.75, 0.9), (0.75, 0.9, 0.85)])), 0.35)
    return {"body": col, "bud": P(WHITE, 0.3), "led": P((0.3, 1.0, 0.4), 0.3, glow=3.0)}


@obj("smartwatch", mass=0.06, weight=1.0, hero=(0, 1, 0), **M)
def smartwatch(b, rng, pal):
    R, sw = 0.027, 0.022
    a0, a1 = math.radians(112), math.radians(68 + 360)
    n = 28
    outer = [((R + 0.0035) * math.cos(a0 + (a1 - a0) * i / n), (R + 0.0035) * math.sin(a0 + (a1 - a0) * i / n))
             for i in range(n + 1)]
    inner = [((R - 0.0008) * math.cos(a0 + (a1 - a0) * i / n), (R - 0.0008) * math.sin(a0 + (a1 - a0) * i / n))
             for i in range(n, -1, -1)]
    b.extrude(outer + inner, sw, mat="strap")
    b.box((0.04, 0.0115, 0.046), loc=(0, R + 0.0015, 0), mat="body", bevel=0.005)
    b.plane(0.034, 0.04, loc=(0, R + 0.0015 + 0.0059, 0), rot=(-math.pi / 2, 0, 0), mat="lcd")
    b.cyl(0.0035, 0.004, loc=(0.0215, R + 0.0015, 0.008), rot=(0, math.pi / 2, 0), mat="body", seg=10)
    return {"strap": RUB(tuple(rng.choice([(0.1, 0.1, 0.1), (0.9, 0.3, 0.4), (0.2, 0.5, 0.9), (0.8, 1.0, 0.0)]))),
            "body": _slab_colors(rng),
            "lcd": ("screen", {"image": tex.watch_face(rng, "sw"), "glow": 0.4, "crack_scale": 14.0})}


@obj("vr_headset", mass=0.5, weight=1.3, big=True, **M)
def vr_headset(b, rng, pal):
    b.box((0.19, 0.094, 0.06), mat="shell", bevel=0.02, seg=4)
    b.plane(0.17, 0.075, loc=(0, 0, 0.0306), mat="visor", cuts=4)
    b.box((0.15, 0.07, 0.025), loc=(0, 0, -0.0425), mat="pad", bevel=0.01, seg=3)
    for sx in (-1, 1):
        b.cyl(0.022, 0.004, loc=(sx * 0.03, 0, -0.056), mat="lens", seg=20)
    pts = [(0.095 * math.cos(a), 0.0, 0.17 * math.sin(a))
           for a in [math.pi + math.pi * i / 16 for i in range(17)]]
    b.tube(pts, 0.0065, mat="strap", seg=8)
    return {"shell": P(tuple(rng.choice([WHITE, (0.85, 0.85, 0.88), (0.1, 0.1, 0.12)])), 0.3),
            "visor": P((0.02, 0.02, 0.03), 0.06, coat=1.0), "pad": ("foam", {"color": (0.12, 0.12, 0.13)}),
            "lens": ("lens", {}), "strap": ("fabric", {"color": (0.12, 0.12, 0.14)})}


@obj("drone", mass=0.3, weight=1.3, big=True, **M)
def drone(b, rng, pal):
    b.box((0.07, 0.05, 0.022), mat="body", bevel=0.008)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c, s = math.cos(a), math.sin(a)
        b.box((0.11, 0.012, 0.008), loc=(0.055 * c, 0.055 * s, 0), rot=(0, 0, a), mat="body", bevel=0.002)
        b.cyl(0.0125, 0.014, loc=(0.11 * c, 0.11 * s, 0), mat="motor", seg=14)
        b.box((0.1, 0.011, 0.0012), loc=(0.11 * c, 0.11 * s, 0.0085), rot=(0, 0, rng.uniform(0, 3.1)), mat="prop")
        b.cyl(0.0015, 0.02, loc=(0.085 * c, 0.085 * s, -0.012), mat="body", seg=6)
    b.sphere(0.013, loc=(0.037, 0, -0.012), mat="body", seg=12)
    b.cyl(0.006, 0.004, loc=(0.048, 0, -0.012), rot=(0, math.pi / 2, 0), mat="lens", seg=12)
    return {"body": pal.body(loud=0.3), "motor": MET((0.2, 0.2, 0.22), 0.4),
            "prop": T(tuple(rng.choice([(0.9, 0.2, 0.2), (0.1, 0.1, 0.1), (0.3, 0.8, 0.4)])), 0.2),
            "lens": ("lens", {})}


@obj("fidget_spinner", mass=0.05, weight=1.5, **M)
def fidget_spinner(b, rng, pal):
    off = rng.uniform(0, 2)
    for k in range(3):
        a = off + 2 * math.pi * k / 3
        x, y = 0.024 * math.cos(a), 0.024 * math.sin(a)
        b.box((0.024, 0.022, 0.008), loc=(x / 2, y / 2, 0), rot=(0, 0, a), mat="body")
        b.cyl(0.015, 0.008, loc=(x, y, 0), mat="body", seg=24)
        b.cyl(0.0085, 0.0095, loc=(x, y, 0), mat="cap", seg=16)
    b.cyl(0.014, 0.008, mat="body", seg=24)
    b.cyl(0.0075, 0.0105, mat="cap", seg=16)
    body = rng.choice(["p", "m", "m"])
    return {"body": P(tuple(rng.choice([(0.95, 0.25, 0.3), (0.2, 0.6, 0.95), (0.95, 0.85, 0.15), (0.6, 0.3, 0.9)])), 0.3)
            if body == "p" else MET(tuple(rng.choice([(0.85, 0.7, 0.2), (0.3, 0.4, 0.8), (0.75, 0.75, 0.78),
                                                      (0.6, 0.15, 0.5)])), 0.25), "cap": MET(SILVER, 0.2)}


@obj("selfie_stick", mass=0.2, weight=1.0, **M)
def selfie_stick(b, rng, pal):
    segs = [(-0.105, 0.09, 0.0078, "grip"), (-0.015, 0.09, 0.0066, "tube"), (0.06, 0.06, 0.0056, "tube"),
            (0.115, 0.05, 0.0048, "tube")]
    for x, L, r, m in segs:
        b.cyl(r, L, loc=(x, 0, 0), rot=(0, math.pi / 2, 0), mat=m, seg=14)
    b.sphere(0.008, loc=(0.145, 0, 0), mat="tube", seg=12)
    b.box((0.014, 0.065, 0.014), loc=(0.157, 0, 0), mat="clamp", bevel=0.003)
    for sy in (-1, 1):
        b.box((0.016, 0.006, 0.02), loc=(0.158, sy * 0.0365, 0.006), mat="clamp", bevel=0.001)
    loop = [(-0.15, 0, 0)] + [(-0.15 - 0.03 * math.sin(math.pi * t), 0.025 * math.cos(math.pi * t) * -1, 0)
                               for t in [i / 10 for i in range(11)]]
    b.tube(loop, 0.0014, mat="strap", seg=6)
    return {"grip": RUB(), "tube": MET(tuple(rng.choice([SILVER, (0.1, 0.1, 0.1)])), 0.3), "clamp": P(BLACK, 0.5),
            "strap": ("fabric", {"color": (0.1, 0.1, 0.1)})}


@obj("ring_light", mass=0.6, weight=1.0, big=True, **M)
def ring_light(b, rng, pal):
    b.torus(0.085, 0.009, mat="led", seg=40, rseg=10)
    b.torus(0.094, 0.004, mat="frame", seg=40, rseg=8)
    b.box((0.026, 0.03, 0.05), loc=(0, -0.104, 0), mat="frame", bevel=0.004)
    b.box((0.05, 0.012, 0.012), loc=(0, 0.0, 0.0), mat="frame", bevel=0.002)
    b.cyl(0.004, 0.06, loc=(0, -0.104, -0.05), mat="frame", seg=10)
    return {"led": P((1.0, 0.97, 0.9), 0.3, glow=3.0), "frame": P(BLACK, 0.4)}


@obj("vape", mass=0.04, weight=1.5, **M)
def vape(b, rng, pal):
    b.extrude(rounded_rect(0.024, 0.095, 0.009, 4), 0.0135, mat="body")
    b.plane(0.085, 0.02, loc=(0, 0, 0.0069), rot=(0, 0, math.pi / 2), mat="print", cuts=3)
    b.box((0.012, 0.012, 0.008), loc=(0, 0.052, 0), mat="tip", bevel=0.002)
    b.box((0.004, 0.0015, 0.001), loc=(0, -0.046, 0.0072), mat="led")
    return {"body": P((0.1, 0.1, 0.12), 0.25), "print": PR(tex.vape_print(rng, "vp"), 0.2, coat=1.0),
            "tip": P(BLACK, 0.4), "led": P((0.4, 1.0, 0.6), 0.3, glow=4.0)}


@obj("face_mask", mass=0.004, weight=1.0, **M)
def face_mask(b, rng, pal):
    for k, y in enumerate((-0.033, 0.0, 0.033)):
        b.box((0.175, 0.034, 0.0015), loc=(0, y, 0.002 * (1 - abs(k - 1))), rot=(0.22 * (1 - k), 0, 0), mat="cloth")
    for sx in (-1, 1):
        loop = [(sx * 0.0875, 0.045 * s, 0.0) for s in (1, 0.8, 0.4, 0, -0.4, -0.8, -1)]
        pts = [(sx * (0.0875 + 0.035 * math.sin(math.pi * (i / 10))), 0.045 * math.cos(math.pi * (i / 10)), 0.0)
               for i in range(11)]
        b.tube(pts, 0.0012, mat="loop", seg=6)
    return {"cloth": ("fabric", {"color": tuple(rng.choice([(0.45, 0.72, 0.9), (0.95, 0.95, 0.95), (0.1, 0.1, 0.12),
                                                            (0.9, 0.5, 0.6)]))}),
            "loop": P((0.95, 0.95, 0.95), 0.6)}


@obj("hand_sanitizer", mass=0.15, weight=1.0, **M)
def hand_sanitizer(b, rng, pal):
    b.lathe([(0.0, -0.055), (0.021, -0.055), (0.022, -0.048), (0.022, 0.03), (0.016, 0.05), (0.0115, 0.055),
             (0.0115, 0.06), (0.0, 0.06)], mat="bottle", seg=24)
    b.cyl(0.0226, 0.042, loc=(0, 0, -0.01), mat="label", seg=24)
    b.cyl(0.008, 0.012, loc=(0, 0, 0.066), mat="pump", seg=14)
    b.box((0.03, 0.012, 0.009), loc=(0.007, 0, 0.075), mat="pump", bevel=0.002)
    b.tube([(0.02, 0, 0.075), (0.028, 0, 0.073)], 0.0025, mat="pump", seg=6)
    return {"bottle": T(tuple(rng.choice([(0.7, 0.9, 1.0), (0.8, 1.0, 0.8), (0.95, 0.95, 0.95)])), 0.08),
            "label": PR(tex.sanitizer_label(rng, "hs"), 0.3), "pump": P(WHITE, 0.4)}


@obj("bluetooth_speaker", mass=0.4, weight=1.5, **M)
def bluetooth_speaker(b, rng, pal):
    b.cyl(0.038, 0.11, rot=(0, math.pi / 2, 0), mat="grille", seg=28)
    for sx in (-1, 1):
        b.cyl(0.04, 0.009, loc=(sx * 0.0555, 0, 0), rot=(0, math.pi / 2, 0), mat="cap", seg=28)
    b.sphere(0.003, loc=(0, -0.0, 0.0385), mat="led", seg=8)
    b.tube([(-0.05, 0.0, 0.04), (-0.03, 0.0, 0.056), (0.03, 0.0, 0.056), (0.05, 0.0, 0.04)], 0.002, mat="cap", seg=6)
    return {"grille": ("fabric", {"color": tuple(rng.choice([(0.12, 0.12, 0.14), (0.2, 0.3, 0.5), (0.5, 0.15, 0.2)]))}),
            "cap": RUB(), "led": P((0.3, 0.6, 1.0), 0.3, glow=4.0)}


@obj("power_bank", mass=0.25, weight=1.0, **M)
def power_bank(b, rng, pal):
    w, h, d = 0.068, 0.125, 0.0225
    b.box((w, h, d), mat="body", bevel=0.006, seg=3)
    for i in range(4):
        b.plane(0.0045, 0.0045, loc=(-0.012 + i * 0.008, h / 2 - 0.012, d / 2 + 0.0003), mat="led")
    b.plane(0.05, 0.03, loc=(0, -0.012, d / 2 + 0.0003), mat="label")
    b.box((0.012, 0.004, 0.006), loc=(0.0, h / 2, 0.0), mat="port")
    pts = [(0.0, h / 2, 0.0), (0.0, h / 2 + 0.03, 0.004), (0.03, h / 2 + 0.06, -0.01), (-0.02, h / 2 + 0.09, 0.0)]
    b.tube(pts, 0.0018, mat="cord", seg=6)
    return {"body": P(tuple(rng.choice([BLACK, WHITE, (0.3, 0.5, 0.9), (0.9, 0.3, 0.4)])), 0.35),
            "led": P((0.3, 1.0, 0.4), 0.3, glow=4.0), "label": PR(tex.sticker(rng, "pbk", words="10000")),
            "port": P(BLACK, 0.6), "cord": P(WHITE, 0.6)}
