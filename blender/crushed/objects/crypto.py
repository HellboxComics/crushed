"""Contamination. Roughly one block in ten has one of these buried in it.

Never listed in metadata. You find it or you don't.
"""
import math

from mathutils import Matrix

from .. import tex
from . import MET, P, PR, obj

C = dict(group="crypto", eras=(0, 1, 2, 3))


@obj("broken_rocket", mass=0.2, **C)
def broken_rocket(b, rng, pal):
    snap = rng.uniform(0.35, 0.6)
    L = 0.16
    # nose half, tipped over
    b.frame = Matrix.Rotation(rng.uniform(0.4, 1.0), 4, "Y")
    b.lathe([(0.0, L * 0.5), (0.008, L * 0.44), (0.016, L * 0.33), (0.018, L * 0.22)], mat="nose", seg=20)
    b.cyl(0.018, L * (0.5 - snap * 0.6), loc=(0, 0, L * 0.22 - L * (0.5 - snap * 0.6) / 2), mat="body", seg=20)
    b.frame = Matrix.Translation((0.05, 0.0, -0.03))
    b.cyl(0.018, L * 0.35, loc=(0, 0, 0), mat="body", seg=20)
    b.plane(0.03, 0.05, loc=(0, -0.0185, 0.01), rot=(math.pi / 2, 0, 0), mat="window")
    for k in range(3):
        a = 2 * math.pi * k / 3
        b.frame = Matrix.Translation((0.05, 0, -0.03)) @ Matrix.Rotation(a, 4, "Z")
        b.extrude([(0.0, 0.0), (0.03, -0.03), (0.03, -0.01), (0.0, 0.03)], 0.003, loc=(0.017, 0, -0.03),
                  rot=(math.pi / 2, 0, 0), mat="fin")
    b.frame = Matrix.Translation((0.05, 0, -0.03))
    b.cyl(0.012, 0.015, r2=0.016, loc=(0, 0, -0.035), mat="nozzle", seg=16)
    b.frame = Matrix.Identity(4)
    return {"nose": P((0.85, 0.08, 0.08), 0.3), "body": P((0.95, 0.95, 0.95), 0.3), "fin": P((0.85, 0.08, 0.08)),
            "window": PR(tex.lcd(rng, "moon", "TO THE MOON", bg=(0.1, 0.1, 0.3), ink=(1, 1, 1))),
            "nozzle": MET((0.3, 0.3, 0.3), 0.5)}


@obj("gold_coin", mass=0.03, **C)
def gold_coin(b, rng, pal):
    n = rng.integers(1, 4)
    for i in range(n):
        b.lathe([(0.0, 0.0022), (0.016, 0.0022), (0.0175, 0.0014), (0.0175, -0.0014), (0.016, -0.0022),
                 (0.0, -0.0022)], loc=(i * 0.012, i * 0.006, i * 0.0045), rot=(rng.normal(0, 0.2), 0, 0),
                mat="gold", seg=36)
        b.plane(0.026, 0.026, loc=(i * 0.012, i * 0.006, i * 0.0045 + 0.0023), mat="face", cuts=4)
    return {"gold": ("gold", {}), "face": PR(tex.lcd(rng, "coin", rng.choice(["HODL", "GM", "WAGMI"]),
                                                     bg=(0.85, 0.65, 0.25), ink=(0.45, 0.3, 0.05)),
                                             rough=0.2, metal=1.0)}


def _candle(b, rng, x):
    h = rng.uniform(0.03, 0.06)
    b.box((0.014, 0.014, h), loc=(x, 0, 0), mat="wax", bevel=0.001)
    b.cyl(0.0012, rng.uniform(0.01, 0.025), loc=(x, 0, h / 2 + 0.008), mat="wick", seg=6)
    b.cyl(0.0012, rng.uniform(0.008, 0.02), loc=(x, 0, -h / 2 - 0.006), mat="wick", seg=6)


@obj("red_candle", mass=0.03, weight=1.3, **C)
def red_candle(b, rng, pal):
    _candle(b, rng, 0)
    return {"wax": ("wax", {"color": (0.85, 0.05, 0.05)}), "wick": P((0.05, 0.05, 0.05), 0.9)}


@obj("green_candle", mass=0.03, weight=1.1, **C)
def green_candle(b, rng, pal):
    _candle(b, rng, 0)
    return {"wax": ("wax", {"color": (0.1, 0.8, 0.25)}), "wick": P((0.05, 0.05, 0.05), 0.9)}


@obj("paper_hand", mass=0.01, **C)
def paper_hand(b, rng, pal):
    pts = [(-0.035, -0.05), (0.03, -0.05), (0.04, -0.005), (0.06, 0.02), (0.055, 0.03), (0.03, 0.012),
           (0.028, 0.06), (0.02, 0.062), (0.015, 0.02), (0.012, 0.075), (0.003, 0.076), (0.0, 0.022),
           (-0.006, 0.07), (-0.015, 0.069), (-0.014, 0.02), (-0.022, 0.058), (-0.031, 0.056), (-0.03, 0.0)]
    b.extrude(pts, 0.004, mat="paper", scale=(1.3, 1.3, 1))
    return {"paper": ("paper", {"color": (0.96, 0.95, 0.9)})}


@obj("diamond", mass=0.005, **C)
def diamond(b, rng, pal):
    s = rng.uniform(0.018, 0.03)
    b.lathe([(0.0, 0.3 * s), (0.55 * s, 0.3 * s), (1.0 * s, 0.0), (1.0 * s, -0.04 * s), (0.0, -0.85 * s)],
            mat="gem", seg=8)
    return {"gem": ("gem", {})}


@obj("hardware_wallet", mass=0.02, **C)
def hardware_wallet(b, rng, pal):
    b.box((0.065, 0.02, 0.009), mat="body", bevel=0.002)
    b.plane(0.03, 0.01, loc=(0.0, 0, 0.0047), mat="oled")
    for x in (-0.026, 0.026):
        b.cyl(0.0025, 0.002, loc=(x, 0, 0.0047), mat="btn", seg=10)
    b.box((0.008, 0.009, 0.0035), loc=(0.036, 0, 0), mat="btn")
    return {"body": MET((0.18, 0.18, 0.2), 0.35), "btn": MET((0.6, 0.6, 0.62), 0.3),
            "oled": PR(tex.lcd(rng, "hw", rng.choice(["PIN?", "CONFIRM", "WIPED", "SEED?"]), bg=(0.02, 0.02, 0.02),
                               ink=(0.95, 0.95, 0.95)), 0.1)}


@obj("crumpled_chart", mass=0.01, weight=1.2, **C)
def crumpled_chart(b, rng, pal):
    b.plane(0.2, 0.15, mat="chart", cuts=24)
    return {"chart": PR(tex.chart(rng, "chart"), 0.85)}


def _quad(b, body, head, legs, horns, tail, mat, dead, k=1.7):
    """A little cast-metal animal, k times the base scale."""
    body = tuple(x * k for x in body)
    head = (tuple(x * k for x in head[0]), tuple(x * k for x in head[1]))
    legs = [(x * k, y * k) for x, y in legs]
    horns = [[tuple(c * k for c in p) for p in h] for h in horns]
    tail = [tuple(c * k for c in p) for p in tail] if tail else None
    if dead:
        b.frame = Matrix.Rotation(math.pi, 4, "X")
    b.sphere(1.0, scale=body, mat=mat, seg=18)
    b.sphere(1.0, loc=head[0], scale=head[1], mat=mat, seg=14)
    for (x, y) in legs:
        b.cyl(body[2] * 0.3, body[2] * 1.6, loc=(x, y, -body[2] * 1.3), mat=mat, seg=10)
    for pts in horns:
        b.tube(pts, lambda t: (0.004 * (1 - t) + 0.0008) * k, mat=mat, seg=8)
    if tail:
        b.tube(tail, 0.0015 * k, mat=mat, seg=6)
    b.frame = Matrix.Identity(4)


@obj("bull", mass=0.3, **C)
def bull(b, rng, pal):
    dead = True
    _quad(b, (0.04, 0.02, 0.022), ((0.048, 0, 0.004), (0.017, 0.013, 0.014)),
          [(0.025, 0.012), (0.025, -0.012), (-0.025, 0.012), (-0.025, -0.012)],
          [[(0.052, 0.01, 0.014), (0.056, 0.025, 0.02), (0.066, 0.03, 0.034)],
           [(0.052, -0.01, 0.014), (0.056, -0.025, 0.02), (0.066, -0.03, 0.034)]],
          [(-0.04, 0, 0.01), (-0.05, 0, 0.0), (-0.055, 0.004, -0.02)], "bronze", dead)
    return {"bronze": MET((0.6, 0.38, 0.18), 0.35)}


@obj("bear", mass=0.3, **C)
def bear(b, rng, pal):
    dead = False
    _quad(b, (0.038, 0.024, 0.026), ((0.042, 0, 0.012), (0.017, 0.016, 0.016)),
          [(0.022, 0.014), (0.022, -0.014), (-0.022, 0.014), (-0.022, -0.014)], [], None, "bronze", dead)
    k = 1.7
    for sy in (-1, 1):
        b.sphere(0.006 * k, loc=(0.04 * k, sy * 0.012 * k, 0.03 * k), mat="bronze", seg=10)
    b.sphere(0.008 * k, loc=(0.058 * k, 0, 0.008 * k), scale=(1.2, 0.8, 0.7), mat="bronze", seg=10)
    return {"bronze": MET((0.25, 0.2, 0.17), 0.4)}


@obj("ramen_packet", mass=0.09, weight=1.3, **C)
def ramen_packet(b, rng, pal):
    rings = []
    for i in range(12):
        t = i / 11
        x = -0.06 + t * 0.12
        puff = math.sin(math.pi * t) ** 0.5
        ring = [(x, 0.05 * math.cos(2 * math.pi * k / 24), 0.012 * puff * math.sin(2 * math.pi * k / 24))
                for k in range(24)]
        rings.append(ring)
    b.loft(rings, mat="foil")
    b.plane(0.11, 0.09, loc=(0, 0, 0.0125), mat="print", cuts=8)
    return {"foil": P((0.85, 0.1, 0.05), 0.2, coat=0.8), "print": PR(tex.ramen(rng, "ramen"), 0.2)}


