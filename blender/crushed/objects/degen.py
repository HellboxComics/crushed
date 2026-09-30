"""The shelf nobody admits to. Adult, gambling and bad-decision props, sprinkled through every era.

Everything here is a generic shape with invented print: a fictional masthead, a silhouette, a word.
Nothing is explicit, nothing is a real brand.
"""
import math

from .. import tex
from ..geo import rounded_rect
from . import BLACK, MET, P, PR, RUB, T, WHITE, obj

ALL = (0, 1, 2, 3, 4)
FILLER = dict(group="filler", eras=ALL)


@obj("magazine", eras=(0, 1, 2, 3), mass=0.25, weight=1.2)
def magazine(b, rng, pal):
    n = int(rng.integers(1, 4))
    specs = {"pages": ("paper", {"color": (0.93, 0.92, 0.86)})}
    for i in range(n):
        z = i * 0.0052
        ang = float(rng.normal(0, 0.08))
        ox, oy = (float(v) for v in rng.normal(0, 0.008, 2))
        b.box((0.215, 0.28, 0.0045), loc=(ox, oy, z), rot=(0, 0, ang), mat="pages", bevel=0.0004)
        b.plane(0.213, 0.278, loc=(ox, oy, z + 0.00228), rot=(0, 0, ang), mat=f"cover{i}", cuts=6)
        specs[f"cover{i}"] = PR(tex.mag_cover(rng, f"mag{i}"), 0.22)
    return specs


def _tri(t):
    return t if t <= 1 else (2 - t if t <= 2 else t - 2)


@obj("centerfold", eras=(0, 1, 2, 3), mass=0.06, weight=1.0)
def centerfold(b, rng, pal):
    rows = []
    for j in range(8):
        y = -0.105 + 0.21 * j / 7
        rows.append([(-0.11 + 0.22 * i / 12, y, 0.008 * _tri(i / 4)) for i in range(13)])
    b.loft(rows, mat="poster", closed=False, cap=False)
    return {"poster": PR(tex.poster(rng, "cf"), 0.3)}


@obj("tissue_box", eras=ALL, mass=0.12, weight=1.4)
def tissue_box(b, rng, pal):
    b.box((0.11, 0.06, 0.055), mat="box", bevel=0.004)
    b.sphere(0.03, loc=(0, 0, 0.0278), scale=(1.6, 0.6, 0.02), mat="slot", seg=16)
    b.sphere(0.02, loc=(0.004, 0, 0.04), scale=(1.1, 0.5, 1.3), mat="tissue", seg=12)
    b.box((0.02, 0.012, 0.03), loc=(-0.006, 0.0, 0.05), rot=(0.3, 0.2, 0.4), mat="tissue")
    return {"box": PR(tex.tissue_print(rng, "tb"), 0.5), "slot": P(BLACK, 0.9),
            "tissue": ("paper", {"color": (0.98, 0.98, 0.96)})}


@obj("tissues", mass=0.004, weight=0.5, **FILLER)
def tissues(b, rng, pal):
    for _ in range(int(rng.integers(2, 5))):
        r = float(rng.uniform(0.011, 0.02))
        b.sphere(r, loc=tuple(float(x) for x in rng.normal(0, 0.012, 3)),
                 scale=(1, float(rng.uniform(0.7, 1)), float(rng.uniform(0.6, 0.95))), mat="tissue", seg=12)
    return {"tissue": ("paper", {"color": (0.97, 0.97, 0.95)})}


@obj("foil_packet", mass=0.002, weight=0.5, **FILLER)
def foil_packet(b, rng, pal):
    b.box((0.056, 0.056, 0.0016), mat="foil", bevel=0.0004)
    b.plane(0.052, 0.052, loc=(0, 0, 0.00085), mat="face", cuts=3)
    b.torus(0.016, 0.0012, loc=(0, 0, 0.0014), mat="foil", seg=24, rseg=6)
    return {"foil": MET((0.85, 0.75, 0.45), 0.25), "face": PR(tex.foil_print(rng, "fp"), 0.2, metal=0.6)}


_PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
         5: [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, 0)],
         6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)]}


@obj("dice", eras=ALL, mass=0.01, weight=1.0)
def dice(b, rng, pal):
    s = 0.016
    for k in range(2):
        ox = k * 0.022
        oy = float(rng.normal(0, 0.004))
        b.box((s, s, s), loc=(ox, oy, 0), rot=(0, 0, float(rng.uniform(0, 1.5))), mat="die", bevel=0.0022, seg=3)
        for (u, v) in _PIPS[int(rng.integers(1, 7))]:
            b.cyl(0.0011, 0.0006, loc=(ox + u * 0.0038, oy + v * 0.0038, s / 2), mat="pip", seg=8)
        for (u, v) in _PIPS[int(rng.integers(1, 7))]:
            b.cyl(0.0011, 0.0006, loc=(ox + u * 0.0038, oy - s / 2, v * 0.0038), rot=(math.pi / 2, 0, 0), mat="pip",
                  seg=8)
    red = rng.random() < 0.6
    return {"die": T((0.85, 0.05, 0.08), 0.1) if red else P((0.95, 0.95, 0.92), 0.25),
            "pip": P(WHITE if red else BLACK, 0.3)}


@obj("poker_chip", eras=ALL, mass=0.012, weight=1.0)
def poker_chip(b, rng, pal):
    col = tuple(rng.choice([(0.8, 0.08, 0.1), (0.1, 0.25, 0.7), (0.1, 0.5, 0.2), (0.07, 0.07, 0.08), (0.5, 0.15, 0.6)]))
    n = int(rng.integers(1, 5))
    for i in range(n):
        z = i * 0.0036
        b.cyl(0.02, 0.0035, loc=(0, 0, z), mat="chip", seg=28)
        for k in range(8):
            a = 2 * math.pi * k / 8
            b.box((0.007, 0.0028, 0.0037), loc=(0.0196 * math.cos(a), 0.0196 * math.sin(a), z), rot=(0, 0, a),
                  mat="stripe")
        b.cyl(0.013, 0.0004, loc=(0, 0, z + 0.0018), mat="stripe", seg=20)
    return {"chip": P(col, 0.3), "stripe": P((0.95, 0.95, 0.92), 0.35)}


@obj("scratch_ticket", eras=ALL, mass=0.002, weight=1.0)
def scratch_ticket(b, rng, pal):
    b.plane(0.06, 0.14, mat="face", cuts=6)
    return {"face": PR(tex.scratch_print(rng, "sc"), 0.35)}


@obj("beer_can", eras=ALL, mass=0.015, weight=1.3)
def beer_can(b, rng, pal):
    prof = [(0.0, -0.061), (0.027, -0.0615), (0.033, -0.056), (0.033, 0.052), (0.029, 0.06), (0.0285, 0.0615),
            (0.0, 0.0615)]
    b.lathe(prof, mat="print", seg=32, rot=(0, math.pi / 2, 0))
    return {"print": ("printed", {"image": tex.beer_print(rng, "beer"), "rough": 0.22, "metal": 0.6})}


@obj("shot_glass", eras=ALL, mass=0.08, weight=0.8)
def shot_glass(b, rng, pal):
    b.lathe([(0.0, -0.03), (0.017, -0.03), (0.017, -0.022), (0.0215, 0.03), (0.0195, 0.03), (0.0155, -0.018),
             (0.0, -0.018)], mat="glass", seg=24)
    b.lathe([(0.0, -0.018), (0.0155, -0.018), (0.0185, 0.004), (0.0, 0.004)], mat="drink", seg=24)
    return {"glass": ("glass", {"rough": 0.03, "crack_scale": 20.0}),
            "drink": T(tuple(rng.choice([(0.85, 0.55, 0.15), (0.95, 0.95, 0.95), (0.6, 0.1, 0.1)])), 0.05)}


@obj("matchbook", eras=(0, 1, 2, 3), mass=0.005, weight=0.8)
def matchbook(b, rng, pal):
    b.box((0.036, 0.052, 0.005), mat="book", bevel=0.0008)
    b.plane(0.034, 0.05, loc=(0, 0, 0.00255), mat="face", cuts=3)
    b.box((0.03, 0.004, 0.004), loc=(0, 0.027, -0.0005), mat="heads")
    return {"book": P((0.05, 0.05, 0.06), 0.6), "face": PR(tex.matchbook_print(rng, "mb"), 0.5),
            "heads": P((0.75, 0.1, 0.08), 0.6)}
