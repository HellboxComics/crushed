"""Debris that fills the gaps: the stuff you can't name but can't stop looking at."""
import math

from .. import tex
from . import MET, P, PR, T, obj

F = dict(group="filler", eras=(0, 1, 2, 3))


@obj("crumpled_paper", mass=0.005, weight=2.0, **F)
def crumpled_paper(b, rng, pal):
    r = rng.uniform(0.018, 0.035)
    b.sphere(r, scale=(1, rng.uniform(0.6, 1), rng.uniform(0.5, 0.9)), mat="paper", seg=14)
    kind = rng.random()
    if kind < 0.4:
        return {"paper": PR(tex.notebook(rng, "cp"), 0.9)}
    return {"paper": ("paper", {"color": tuple(rng.choice([(0.95, 0.95, 0.92), (0.9, 0.85, 0.7),
                                                           (0.95, 0.9, 0.5), (0.8, 0.85, 0.95)]))})}


@obj("foam_chunk", mass=0.003, weight=1.5, **F)
def foam_chunk(b, rng, pal):
    s = rng.uniform(0.02, 0.05, 3)
    b.box(tuple(s), mat="foam", bevel=0.003)
    return {"foam": ("foam", {"color": tuple(rng.choice([(0.95, 0.8, 0.3), (0.95, 0.95, 0.9), (0.5, 0.5, 0.52),
                                                         (0.3, 0.6, 0.9)]))})}


@obj("plastic_shard", mass=0.01, weight=2.5, **F)
def plastic_shard(b, rng, pal):
    n = rng.integers(3, 6)
    ang = sorted(rng.uniform(0, 2 * math.pi, n))
    rad = rng.uniform(0.015, 0.06, n)
    b.extrude([(math.cos(a) * r, math.sin(a) * r) for a, r in zip(ang, rad)], rng.uniform(0.002, 0.004),
              mat="p", bevel=0.0005)
    return {"p": pal.body(loud=0.4)}


@obj("glass_shard", mass=0.01, weight=1.0, **F)
def glass_shard(b, rng, pal):
    ang = sorted(rng.uniform(0, 2 * math.pi, 3))
    rad = rng.uniform(0.015, 0.04, 3)
    b.extrude([(math.cos(a) * r, math.sin(a) * r) for a, r in zip(ang, rad)], 0.003, mat="g")
    return {"g": ("glass", {"color": (0.8, 0.9, 0.88), "crack_scale": 40.0})}


@obj("bottle_cap", mass=0.003, weight=1.0, **F)
def bottle_cap(b, rng, pal):
    b.lathe([(0.0, 0.003), (0.013, 0.003), (0.0145, 0.0), (0.0155, -0.003)], mat="m", seg=21)
    return {"m": MET(tuple(rng.choice([(0.8, 0.1, 0.1), (0.8, 0.75, 0.3), (0.2, 0.3, 0.8), (0.75, 0.75, 0.75)])),
                     0.3)}


@obj("pcb_chunk", mass=0.03, weight=1.8, **F)
def pcb_chunk(b, rng, pal):
    w, h = rng.uniform(0.04, 0.09, 2)
    b.box((w, h, 0.0016), mat="board")
    b.plane(w, h, loc=(0, 0, 0.0009), mat="traces")
    for _ in range(rng.integers(2, 6)):
        b.box((rng.uniform(0.006, 0.02), rng.uniform(0.006, 0.014), 0.003),
              loc=(rng.uniform(-w / 3, w / 3), rng.uniform(-h / 3, h / 3), 0.0025), mat="chip")
    for _ in range(rng.integers(1, 4)):
        b.cyl(0.003, 0.009, loc=(rng.uniform(-w / 3, w / 3), rng.uniform(-h / 3, h / 3), 0.005), mat="cap", seg=12)
    return {"board": P((0.05, 0.3, 0.12)), "traces": ("pcb", {"image": tex.pcb(rng, "pcb")}),
            "chip": P((0.04, 0.04, 0.04), 0.4),
            "cap": P(tuple(rng.choice([(0.1, 0.2, 0.6), (0.1, 0.1, 0.1), (0.6, 0.5, 0.2)])), 0.3)}


@obj("spring", mass=0.005, weight=0.7, **F)
def spring(b, rng, pal):
    from ..geo import helix
    b.tube(helix(0.006, 0.004, rng.uniform(4, 9), 16), 0.0008, mat="m", seg=6)
    return {"m": MET((0.7, 0.7, 0.7), 0.25)}


@obj("receipt", mass=0.002, weight=1.2, **F)
def receipt(b, rng, pal):
    b.plane(0.06, 0.18, mat="r", cuts=16)
    return {"r": PR(tex.sticker(rng, "rc", base=(0.96, 0.95, 0.92), lines=0,
                                words=rng.choice(["TOTAL 4.99", "THANK YOU", "CASH", "VOID"])), 0.9)}


@obj("fabric_scrap", mass=0.02, weight=1.0, **F)
def fabric_scrap(b, rng, pal):
    b.plane(rng.uniform(0.06, 0.12), rng.uniform(0.06, 0.12), mat="f", cuts=12)
    return {"f": ("fabric", {"color": pal.color("loud") if rng.random() < 0.5 else
                             tuple(rng.choice([(0.2, 0.25, 0.45), (0.8, 0.8, 0.78), (0.1, 0.1, 0.1)]))})}


@obj("cardboard_scrap", mass=0.02, weight=1.0, **F)
def cardboard_scrap(b, rng, pal):
    b.box((rng.uniform(0.05, 0.12), rng.uniform(0.04, 0.1), 0.004), mat="c")
    return {"c": ("cardboard", {})}


@obj("wire_bit", mass=0.01, weight=1.5, **F)
def wire_bit(b, rng, pal):
    pts = [(0, 0, 0)]
    x = y = z = 0.0
    for _ in range(8):
        x += rng.uniform(0.005, 0.015)
        y += rng.normal(0, 0.008)
        z += rng.normal(0, 0.008)
        pts.append((x, y, z))
    b.tube(pts, 0.0018, mat="ins", seg=6)
    b.tube([pts[-1], (x + 0.006, y, z)], 0.0009, mat="cu", seg=5)
    return {"ins": P(tuple(rng.choice([(0.8, 0.1, 0.1), (0.1, 0.1, 0.1), (0.9, 0.9, 0.9), (0.9, 0.8, 0.1),
                                       (0.1, 0.4, 0.8)])), 0.4), "cu": ("copper", {})}


@obj("gum_wrapper", mass=0.001, weight=0.8, **F)
def gum_wrapper(b, rng, pal):
    b.plane(0.07, 0.02, mat="w", cuts=10)
    return {"w": MET(tuple(rng.choice([(0.8, 0.8, 0.82), (0.85, 0.7, 0.3)])), 0.2)}


@obj("clear_chunk", mass=0.01, weight=1.0, **F)
def clear_chunk(b, rng, pal):
    s = rng.uniform(0.015, 0.035, 3)
    b.box(tuple(s), mat="t", bevel=0.002)
    return {"t": T(pal.color("loud"), 0.12)}


@obj("housing_fragment", mass=0.05, weight=5.0, **F)
def housing_fragment(b, rng, pal):
    """A flattened chunk of some device's shell. Most of the surface is this."""
    w, h = rng.uniform(0.05, 0.13, 2)
    b.box((w, h, rng.uniform(0.002, 0.006)), mat="p", bevel=0.001)
    if rng.random() < 0.35:
        for i in range(rng.integers(2, 6)):
            b.box((w * 0.8, 0.0015, 0.0016), loc=(0, -h / 3 + i * 0.006, 0.003), mat="p")
    out = {"p": pal.body(loud=0.35)}
    if rng.random() < 0.3:
        b.plane(w * 0.5, h * 0.4, loc=(rng.uniform(-w / 5, w / 5), 0, 0.0035), mat="lbl")
        out["lbl"] = PR(tex.sticker(rng, "hf", base=tuple(rng.choice([(0.95, 0.95, 0.9), (0.95, 0.85, 0.2),
                                                                     (0.8, 0.1, 0.1)])), lines=2,
                                    words=str(rng.choice(["WARNING", "MADE IN", "9V DC", "MODEL", "CE", "FCC"]))))
    return out


@obj("packaging", mass=0.03, weight=1.6, **F)
def packaging(b, rng, pal):
    w, h = rng.uniform(0.06, 0.14, 2)
    b.box((w, h, 0.003), mat="c")
    b.plane(w * 0.95, h * 0.95, loc=(0, 0, 0.0016), mat="art")
    img = tex.griptape_art(rng, "pk") if rng.random() < 0.5 else tex.can_print(rng, "pk")
    return {"c": ("cardboard", {}), "art": PR(img, 0.5)}


@obj("plastic_film", mass=0.005, weight=1.2, **F)
def plastic_film(b, rng, pal):
    b.plane(rng.uniform(0.08, 0.16), rng.uniform(0.08, 0.16), mat="f", cuts=14)
    return {"f": T(tuple(rng.choice([(0.9, 0.92, 0.95), (0.3, 0.3, 0.32), (0.95, 0.9, 0.6)])), 0.3)}
