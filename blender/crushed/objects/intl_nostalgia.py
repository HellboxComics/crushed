"""Nostalgia: the world's childhood crazes, 1985-2008. The egg America banned, the sticker album nobody
finished, the Saturday paper bag of sweets, the capsule machine, the photo booth, the chip-bag discs, the
canned-ham gift box and the World Cup. Every shape is real-scaled; every brand on them is a parody, every
character our own."""
import math

import numpy as np

from .. import tex
from . import BLACK, CHROME, MET, P, PR, RUB, T, WHITE, obj
from .toys import _clear

PI = math.pi
SPECIAL = dict(group="special")
RARE = dict(group="era", weight=0.12)      # also turns up, rarely, in a regular cube from that era
INK = (0.06, 0.05, 0.05)
KRED = (0.86, 0.08, 0.1)
KORANGE = (1.0, 0.45, 0.05)
CHOC = (0.3, 0.15, 0.06)
MILK_CHOC = (0.42, 0.22, 0.09)
CAPSULE_YELLOW = (1.0, 0.8, 0.02)


def _ch(rng, seq):
    return seq[int(rng.integers(0, len(seq)))]


def _cv(w, h, bg):
    return tex.Canvas(w, h, (*bg, 1))


def _tw(c, s, size, spacing=1.0):
    return len(s) * 6 * (size / 7.0) * (c.h / c.w) * spacing


def _ct(c, s, cx, y, size, col, maxw=0.92, bold=True, spacing=1.0):
    """Centered text with its top at y, shrunk to fit maxw."""
    w = _tw(c, s, size, spacing)
    if w > maxw:
        size *= maxw / w
        w = maxw
    c.text(s, cx - w / 2, y, size, col, spacing=spacing, bold=bold)
    return size


def _star(cx, cy, r, n=5, inner=0.45, rot=0.0, asp=1.0):
    pts = []
    for i in range(n * 2):
        a = rot + PI / 2 + PI * i / n
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a) / asp, cy + rr * math.sin(a)))
    return pts


def _heart(cx, cy, r, asp=1.0, n=28):
    pts = []
    for i in range(n):
        t = 2 * PI * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x / 17 * r / asp, cy + y / 17 * r))
    return pts


def _pillow(b, w, h, th, mat, n=24, rings=14, puff=0.7):
    """A sealed snack pouch: wide in x, tall in z, puffed in y. The print's right half (u 0.5..1) is the front."""
    rs = []
    for j in range(rings):
        u = j / (rings - 1)
        z = -h / 2 + h * u
        t = th * math.sin(PI * u) ** puff + 0.001
        ww = w * (0.93 + 0.07 * math.sin(PI * u))
        rs.append([(ww / 2 * math.cos(2 * PI * i / n), t / 2 * math.sin(2 * PI * i / n), z) for i in range(n)])
    b.loft(rs, mat=mat)


def _crimps(b, w, h, mat, d=0.012):
    for s in (-1, 1):
        b.box((w, 0.0015, d), loc=(0, 0, s * (h / 2 + d / 2 - 0.001)), mat=mat)
        for k in range(int(w / 0.004)):                          # the serrated edge
            b.box((0.0016, 0.0016, 0.0025), loc=(-w / 2 + 0.002 + k * 0.004, 0, s * (h / 2 + d - 0.001)),
                  rot=(0, PI / 4, 0), mat=mat)


def _flow_bar(b, L, W, Hh, top, wrap, crimp=0.01):
    """A flow-wrapped bar lying flat: body, printed top, crimped ends. Label reads along x."""
    b.box((L, W, Hh), mat=wrap, bevel=min(0.003, Hh * 0.45))
    b.plane(L * 0.97, W * 0.96, loc=(0, 0, Hh / 2 + 0.0004), mat=top, cuts=3)
    for s in (-1, 1):
        b.box((crimp, W * 1.02, 0.0016), loc=(s * (L / 2 + crimp / 2 - 0.001), 0, 0), mat=wrap)


# ================================================================================================
# SURPRISE INSIDE: the chocolate egg with a toy in it, everywhere but America
# ================================================================================================

def _egg_foil(rng, name):
    c = _cv(512, 256, (0.97, 0.97, 0.95))
    c.rect(0, 0.74, 1, 1, KORANGE)
    c.rect(0, 0.7, 1, 0.75, KRED)
    for k in range(6):                                             # the orange swoosh round the bottom
        xs = np.linspace(0, 1, 40)
        ys = 0.2 + 0.05 * np.sin(xs * 2 * PI * 2 + k * 0.4) + k * 0.012
        c.line(list(zip(xs.tolist(), ys.tolist())), 0.012, (1.0, 0.6, 0.2) if k % 2 else KORANGE)
    for cx in (0.25, 0.75):
        _ct(c, "KINDA", cx, 0.66, 0.15, INK, maxw=0.3)
        _ct(c, "SURPRISE", cx, 0.47, 0.1, KRED, maxw=0.3)
        c.circle(cx + 0.12, 0.88, 0.055, CAPSULE_YELLOW)        # the capsule, drawn on the foil
        c.circle(cx + 0.12, 0.88, 0.055, (0.8, 0.6, 0.0), ring=0.012)
        c.text("?", cx + 0.105, 0.91, 0.07, INK, bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def _choc_half(b, R, H, loc, rot, out="choc", inner="milk", t=0.0022):
    prof = [(0.0, -H), (R * 0.5, -H * 0.95), (R * 0.85, -H * 0.66), (R, -H * 0.25), (R, 0.0)]
    inn = [(max(r - t, 0.0), z + (t if z < -0.001 else 0.0)) for r, z in reversed(prof)]
    b.lathe(prof + inn, loc=loc, rot=rot, mat=out, seg=24)
    b.lathe([(max(r - t - 0.0003, 0.0), z) for r, z in reversed(prof[1:])] + [(0.0, -H + t + 0.0004)],
            loc=loc, rot=rot, mat=inner, seg=24)


def _capsule(b, r, h, loc=(0, 0, 0), rot=(0, 0, 0), mat="cap", open_=False):
    """The yellow capsule: two halves, one sleeved over the other."""
    lo = [(0.0, -h / 2), (r * 0.55, -h / 2 + 0.0008), (r * 0.9, -h / 2 + r * 0.45), (r, -h / 2 + r), (r, 0.002),
          (r - 0.0008, 0.002), (r - 0.0008, -h / 2 + r), (0.0, -h / 2 + 0.0008)]
    hi = [(0.0, h / 2), (r * 0.6, h / 2 - 0.0008), (r * 0.95 + 0.0007, h / 2 - r * 0.45), (r + 0.0007, h / 2 - r),
          (r + 0.0007, -0.004), (r - 0.0001, -0.004), (r - 0.0001, h / 2 - r), (0.0, h / 2 - 0.0008)]
    b.lathe(lo, loc=loc, rot=rot, mat=mat, seg=22)
    if open_:
        b.lathe(hi, loc=(loc[0] + 0.03, loc[1] + 0.006, loc[2]), rot=(rot[0] + 2.4, rot[1], rot[2] + 0.5), mat=mat, seg=22)
    else:
        b.lathe(hi, loc=loc, rot=rot, mat=mat, seg=22)


@obj("surprise_egg", eras=(0, 1, 2, 3), mass=0.02, **RARE)
def surprise_egg(b, rng, pal):
    """The foil egg, or what is left once it was opened: two chocolate halves, white inside, and the capsule."""
    if rng.random() < 0.55:
        b.sphere(0.02, scale=(1, 1, 1.42), mat="foil", seg=26)
        b.sphere(0.0035, loc=(0, 0, 0.0285), scale=(1.3, 1.0, 0.6), mat="foil", seg=8)   # the twisted tip
        return {"foil": PR(_egg_foil(rng, "kfoil"), 0.3, metal=0.5)}
    _choc_half(b, 0.0195, 0.027, (0, 0, 0.0), (0, 0, 0))
    _choc_half(b, 0.0195, 0.027, (0.044, 0.004, -0.004), (2.7, 0.3, 0.0))
    _capsule(b, 0.0125, 0.034, loc=(0.0, 0.0, 0.006), rot=(0.3, 0.2, 0), mat="cap", open_=rng.random() < 0.4)
    b.plane(0.07, 0.05, loc=(0.0, -0.035, -0.022), rot=(float(rng.normal(0, 0.2)), float(rng.normal(0, 0.2)), 0.4),
            mat="foil", cuts=4)
    return {"choc": P(MILK_CHOC, 0.35, coat=0.3), "milk": P((0.97, 0.94, 0.86), 0.5), "cap": P(CAPSULE_YELLOW, 0.3),
            "foil": PR(_egg_foil(rng, "kfoil2"), 0.3, metal=0.5)}


@obj("surprise_capsule", eras=(0, 1, 2, 3), mass=0.006, **RARE)
def surprise_capsule(b, rng, pal):
    _capsule(b, 0.0125, 0.034, rot=(PI / 2, 0, float(rng.uniform(0, PI))), mat="cap", open_=rng.random() < 0.45)
    return {"cap": P(CAPSULE_YELLOW, 0.3)}


@obj("surprise_toy", eras=(0, 1, 2, 3), mass=0.004, hero=(0, -1, 0), **RARE)
def surprise_toy(b, rng, pal):
    """The toy: a painted little critter, a four-piece buggy, or the parts still on the sprue."""
    kind = int(rng.integers(0, 3))
    a, c2 = _ch(rng, [((0.55, 0.75, 0.95), (0.95, 0.45, 0.6)), ((0.95, 0.7, 0.2), (0.3, 0.6, 0.25)),
                      ((0.85, 0.3, 0.3), (0.2, 0.3, 0.8)), ((0.6, 0.85, 0.4), (0.95, 0.9, 0.3))])
    if kind == 0:   # a round, cheerful nobody: a bean with ears, holding a little sign
        b.sphere(0.011, loc=(0, 0, 0.0), scale=(1, 0.9, 1.1), mat="a", seg=14)
        b.sphere(0.009, loc=(0, -0.001, 0.016), mat="a", seg=14)
        for sx in (-1, 1):
            b.sphere(0.0035, loc=(sx * 0.0065, 0, 0.024), mat="b", seg=8)
            b.sphere(0.0013, loc=(sx * 0.0032, -0.0085, 0.018), mat="eye", seg=6)
            b.sphere(0.003, loc=(sx * 0.005, -0.002, -0.012), scale=(1, 1.4, 0.6), mat="b", seg=8)
        b.sphere(0.0028, loc=(0, -0.0092, 0.014), scale=(1.3, 0.7, 0.8), mat="b", seg=8)
        b.box((0.012, 0.0015, 0.008), loc=(0.009, -0.009, 0.004), rot=(0, 0.2, 0), mat="b")
        return {"a": P(a, 0.4), "b": P(c2, 0.4), "eye": P(BLACK, 0.3)}
    if kind == 1:   # a snap-together buggy with a sticker on the hood
        b.box((0.04, 0.018, 0.004), loc=(0, 0, 0.004), mat="a", bevel=0.001)
        b.box((0.018, 0.016, 0.009), loc=(-0.004, 0, 0.0105), mat="b", bevel=0.002)
        b.box((0.012, 0.014, 0.0005), loc=(0.011, 0, 0.0063), mat="stk")
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.cyl(0.0055, 0.004, loc=(sx * 0.014, sy * 0.011, 0.004), rot=(PI / 2, 0, 0), mat="tire", seg=14)
        return {"a": P(a, 0.35), "b": P(c2, 0.35), "tire": RUB(), "stk": P((0.97, 0.95, 0.9), 0.4)}
    # the sprue: a flat frame of runners with the pieces still attached
    b.tube([(-0.025, -0.015, 0), (0.025, -0.015, 0), (0.025, 0.015, 0), (-0.025, 0.015, 0), (-0.025, -0.015, 0)],
           0.0011, mat="a", seg=6)
    b.tube([(0, -0.015, 0), (0, 0.015, 0)], 0.0011, mat="a", seg=6)
    for x, y in ((-0.013, -0.006), (-0.013, 0.007), (0.012, -0.007), (0.012, 0.007)):
        b.cyl(0.005, 0.0025, loc=(x, y, 0), mat="a", seg=14)
        b.tube([(x, y, 0), (x, -0.015 if y < 0 else 0.015, 0)], 0.0005, mat="a", seg=4)
    return {"a": P(a, 0.35)}


def _slip_print(rng, name):
    c = _cv(768, 256, (0.97, 0.97, 0.95))
    ink = (0.25, 0.25, 0.27)
    for k in range(4):
        x0 = k * 0.25
        c.rect(x0 + 0.004, 0, x0 + 0.006, 1, (0.85, 0.85, 0.85))                  # fold lines
        c.circle(x0 + 0.04, 0.88, 0.06, ink)
        c.text(str(k + 1), x0 + 0.032, 0.92, 0.08, (1, 1, 1), bold=True)
        for _ in range(3):                                                      # parts in line drawing
            px, py = x0 + float(rng.uniform(0.06, 0.2)), float(rng.uniform(0.3, 0.7))
            if rng.random() < 0.5:
                c.circle(px, py, float(rng.uniform(0.04, 0.09)), ink, ring=0.012)
            else:
                w = float(rng.uniform(0.02, 0.05))
                c.rect(px - w, py - 0.06, px + w, py + 0.06, ink)
                c.rect(px - w + 0.004, py - 0.045, px + w - 0.004, py + 0.045, (0.97, 0.97, 0.95))
        c.line([(x0 + 0.06, 0.18), (x0 + 0.19, 0.18), (x0 + 0.17, 0.24)], 0.012, ink)                # arrow
    c.circle(0.93, 0.18, 0.11, INK, ring=0.02)                                  # the under-3 warning
    c.text("0-3", 0.905, 0.23, 0.08, INK, bold=True)
    c.line([(0.905, 0.08), (0.955, 0.28)], 0.02, INK)
    c.text("ATTENZIONE ACHTUNG WARNING", 0.52, 0.08, 0.045, ink, spacing=0.95)
    return c.image(name)


@obj("surprise_slip", eras=(0, 1, 2, 3), mass=0.001, **SPECIAL)
def surprise_slip(b, rng, pal):
    """The accordion-folded instruction slip, the part everyone threw away first."""
    W, H = 0.11, 0.036
    xs = [-W / 2 + W * i / 8 for i in range(9)]
    zs = [0.0, 0.002, 0.005, 0.002, 0.0, 0.002, 0.005, 0.002, 0.0]
    rings = [[(x, y, z) for x, z in zip(xs, zs)] for y in (-H / 2, H / 2)]
    b.loft(rings, mat="paper", closed=False)
    return {"paper": PR(_slip_print(rng, "kslip"), 0.85)}


def _choc_shell_bits(b, rng, n=None):
    for _ in range(n or int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.012, 2))
        r = float(rng.uniform(0.01, 0.018))
        pts = [(r * math.cos(a) * float(rng.uniform(0.6, 1.0)), r * math.sin(a) * float(rng.uniform(0.6, 1.0)))
               for a in np.linspace(0, 2 * PI, 7)[:-1]]
        b.extrude(pts, 0.0022, loc=(x, y, 0), rot=(float(rng.normal(0, 0.3)), float(rng.normal(0, 0.3)), 0), mat="choc")
        b.extrude([(px * 0.9, py * 0.9) for px, py in pts], 0.0006, loc=(x, y, 0.0013),
                  rot=(float(rng.normal(0, 0.05)), 0, 0), mat="milk")


@obj("choc_egg_shell", eras=(0, 1, 2, 3), mass=0.004, **SPECIAL)
def choc_egg_shell(b, rng, pal):
    """Broken shards of the egg: brown outside, white inside."""
    _choc_shell_bits(b, rng)
    return {"choc": P(MILK_CHOC, 0.35, coat=0.3), "milk": P((0.97, 0.94, 0.86), 0.5)}


def _bono_print(rng, name):
    c = _cv(512, 160, (0.97, 0.96, 0.93))
    xs = np.linspace(0, 1, 60)
    c.poly([(0, 0)] + [(x, 0.3 + 0.06 * math.sin(x * 14)) for x in xs] + [(1, 0)], MILK_CHOC)
    c.rect(0, 0.88, 1, 1, KRED)
    _ct(c, "KINDA", 0.2, 0.82, 0.28, INK, maxw=0.28)
    c.poly([(0.36, 0.48), (0.66, 0.48), (0.7, 0.8), (0.32, 0.8)], KORANGE)
    _ct(c, "BONO", 0.51, 0.75, 0.24, (0.35, 0.17, 0.06), maxw=0.3)
    for k in range(2):                                              # the two bars, drawn
        x0 = 0.72 + k * 0.03
        y0 = 0.38 + k * 0.17
        c.rect(x0, y0, x0 + 0.22, y0 + 0.12, (0.85, 0.65, 0.4))
        for j in range(5):
            c.line([(x0 + 0.01 + j * 0.045, y0 + 0.02), (x0 + 0.03 + j * 0.045, y0 + 0.1)], 0.03, CHOC)
    c.text("2 BARS 43G", 0.05, 0.22, 0.09, (0.97, 0.9, 0.8))
    return c.image(name)


@obj("hazelnut_wafer_bar", eras=(1, 2, 3), mass=0.045, **RARE)
def hazelnut_wafer_bar(b, rng, pal):
    """The two-bar hazelnut wafer, in its white wrapper, or one bar already out of it."""
    if rng.random() < 0.6:
        _flow_bar(b, 0.165, 0.05, 0.016, "top", "wrap")
        return {"wrap": P((0.96, 0.95, 0.92), 0.3, coat=0.5), "top": PR(_bono_print(rng, "bono"), 0.3)}
    for k in range(4):                                                  # the bumpy wafer
        b.sphere(0.012, loc=(-0.03 + k * 0.02, 0, 0), scale=(1.0, 1.05, 0.6), mat="wafer", seg=14)
    for k in range(9):                                                  # the chocolate drizzle
        x = -0.04 + k * 0.01
        b.tube([(x, -0.013, 0.004), (x + 0.006, 0, 0.0075), (x + 0.012, 0.013, 0.004)], 0.0012, mat="choc", seg=5)
    b.box((0.09, 0.026, 0.003), loc=(0, 0, -0.006), mat="choc", bevel=0.001)
    b.plane(0.08, 0.05, loc=(0.02, 0.03, -0.009), rot=(0.1, 0, 0.3), mat="top", cuts=3)
    return {"wafer": P((0.86, 0.66, 0.4), 0.6), "choc": P(CHOC, 0.35, coat=0.3),
            "top": PR(_bono_print(rng, "bono2"), 0.3)}


def _joy_print(rng, name, boy):
    acc = (0.2, 0.5, 0.95) if boy else (1.0, 0.45, 0.7)
    c = _cv(512, 256, (0.97, 0.97, 0.95))
    c.rect(0, 0.0, 1, 0.42, KORANGE)
    c.rect(0, 0.42, 1, 0.48, acc)
    for cx in (0.25, 0.75):
        _ct(c, "KINDA", cx, 0.78, 0.16, INK, maxw=0.3)
        _ct(c, "JOY", cx, 0.6, 0.12, KRED, maxw=0.2)
        c.circle(cx + 0.14, 0.24, 0.07, (0.5, 0.28, 0.12))            # the wafer balls
        c.circle(cx + 0.18, 0.2, 0.06, (0.5, 0.28, 0.12))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("joy_egg", eras=(2, 3, 4), mass=0.03, **SPECIAL)
def joy_egg(b, rng, pal):
    """The split plastic egg: in its foil, or opened, cream half and toy half, with the little spoon."""
    if rng.random() < 0.5:
        b.sphere(0.023, scale=(1, 1, 1.38), mat="foil", seg=26)
        return {"foil": PR(_joy_print(rng, "joy", rng.random() < 0.5), 0.3, metal=0.45)}
    R, H = 0.0225, 0.031
    prof = [(0.0, -H), (R * 0.6, -H * 0.94), (R * 0.9, -H * 0.6), (R, -H * 0.2), (R, 0.0), (R - 0.0012, 0.0),
            (R - 0.0012, -H * 0.2), (R * 0.9 - 0.0012, -H * 0.6), (0.0, -H + 0.0012)]
    b.lathe(prof, mat="orange", seg=28)
    b.cyl(R - 0.0013, 0.006, loc=(0, 0, -0.004), mat="cream_b", seg=28)
    b.cyl(R - 0.0013, 0.003, loc=(0, 0, -0.0005), mat="cream_w", seg=28)
    for sx in (-1, 1):
        b.sphere(0.0062, loc=(sx * 0.008, 0.002, 0.004), mat="wafer", seg=12)
    b.lathe(prof, loc=(0.052, 0.0, -0.002), rot=(2.8, 0.2, 0), mat="white", seg=28)
    _capsule(b, 0.012, 0.03, loc=(0.052, 0.0, 0.004), rot=(PI / 2, 0, 0.3), mat="cap")
    b.box((0.05, 0.007, 0.0015), loc=(-0.01, -0.03, -0.012), rot=(0, 0.1, 0.25), mat="spoon", bevel=0.0006)
    b.sphere(0.006, loc=(0.015, -0.024, -0.012), scale=(1.4, 1, 0.3), mat="spoon", seg=10)
    return {"orange": P(KORANGE, 0.3), "white": P((0.96, 0.96, 0.95), 0.3), "cream_b": P((0.55, 0.32, 0.15), 0.5),
            "cream_w": P((0.98, 0.95, 0.88), 0.5), "wafer": ("crust", {}), "cap": P(CAPSULE_YELLOW, 0.3),
            "spoon": P(_ch(rng, [(0.98, 0.5, 0.1), (0.2, 0.5, 0.95), (1.0, 0.45, 0.7)]), 0.35)}


def _kbar_print(rng, name):
    c = _cv(512, 128, (0.97, 0.96, 0.93))
    c.rect(0.0, 0.0, 0.08, 1, KRED)
    c.rect(0.92, 0.0, 1, 1, KRED)
    _ct(c, "KINDA", 0.3, 0.8, 0.42, INK, maxw=0.3)
    _ct(c, "CHOCOLATE", 0.3, 0.32, 0.18, MILK_CHOC, maxw=0.32)
    c.rect(0.5, 0.15, 0.78, 0.85, MILK_CHOC)                         # the cut bar: brown, white middle
    c.rect(0.52, 0.32, 0.76, 0.68, (0.98, 0.96, 0.9))
    c.circle(0.85, 0.5, 0.25, (0.75, 0.85, 1.0))                     # the glass of milk
    c.circle(0.85, 0.5, 0.18, (0.98, 0.98, 1.0))
    return c.image(name)


@obj("kids_choc_bar", eras=(0, 1, 2, 3, 4), mass=0.0125, **SPECIAL)
def kids_choc_bar(b, rng, pal):
    """The little single bar with the milky middle, wrapped or half-eaten."""
    if rng.random() < 0.6:
        _flow_bar(b, 0.1, 0.024, 0.01, "top", "wrap", crimp=0.008)
        return {"wrap": P((0.96, 0.95, 0.92), 0.3, coat=0.5), "top": PR(_kbar_print(rng, "kbar"), 0.3)}
    n = int(rng.integers(2, 5))
    for k in range(n):
        b.box((0.021, 0.022, 0.008), loc=(-0.033 + k * 0.022, 0, 0), mat="choc", bevel=0.002)
    b.box((0.0005, 0.016, 0.004), loc=(-0.033 + (n - 1) * 0.022 + 0.0107, 0, 0), mat="milk")
    return {"choc": P(MILK_CHOC, 0.35, coat=0.3), "milk": P((0.98, 0.95, 0.88), 0.5)}


# ================================================================================================
# GOT GOT NEED: the sticker album, the packets, the swap pile in the playground
# ================================================================================================

KITS = [((0.95, 0.95, 0.95), (0.1, 0.2, 0.6)), ((0.95, 0.85, 0.1), (0.1, 0.55, 0.25)), ((0.85, 0.1, 0.12), (0.95, 0.95, 0.95)),
        ((0.15, 0.35, 0.85), (0.95, 0.95, 0.95)), ((1.0, 0.5, 0.05), (0.95, 0.95, 0.95)), ((0.1, 0.55, 0.25), (0.95, 0.95, 0.95)),
        ((0.55, 0.75, 0.95), (0.95, 0.95, 0.95)), ((0.05, 0.05, 0.06), (0.95, 0.95, 0.95))]
SURN = ["RAMIREZ", "OKAFOR", "BRANDT", "KOWALSKI", "LINDQVIST", "MOREIRA", "DUPONT", "TAKEDA", "VOSS", "GALLO",
        "MENSAH", "HAGI-ISH", "PETROV", "ROSSO", "ALDANA", "BJORK"]
CUPS = [("COPA 90", (0.1, 0.45, 0.25)), ("COPA 94", (0.15, 0.25, 0.65)), ("COPA 98", (0.85, 0.1, 0.12))]


def _flagbar(c, x0, y0, x1, y1, rng):
    cols = [_ch(rng, KITS)[0] for _ in range(3)] if rng.random() < 0.3 else _ch(rng, [
        [(0.0, 0.55, 0.3), (0.97, 0.97, 0.97), (0.85, 0.1, 0.15)], [(0.0, 0.2, 0.6), (0.97, 0.97, 0.97), (0.85, 0.1, 0.15)],
        [(0.05, 0.05, 0.05), (0.85, 0.1, 0.12), (1.0, 0.8, 0.0)], [(0.95, 0.75, 0.0), (0.1, 0.25, 0.65), (0.85, 0.1, 0.12)]])
    vert = rng.random() < 0.5
    for k, col in enumerate(cols):
        if vert:
            c.rect(x0 + (x1 - x0) * k / 3, y0, x0 + (x1 - x0) * (k + 1) / 3, y1, col)
        else:
            c.rect(x0, y1 - (y1 - y0) * (k + 1) / 3, x1, y1 - (y1 - y0) * k / 3, col)


def _player_card(c, rng, x0, y0, x1, y1, num=None):
    """One sticker: a player head-and-shoulders (nobody real), surname bar, flag, number."""
    asp = c.w / c.h
    shirt, trim = _ch(rng, KITS)
    sky = _ch(rng, [(0.55, 0.75, 0.95), (0.3, 0.6, 0.35), (0.85, 0.85, 0.9), (0.95, 0.8, 0.4)])
    c.rect(x0, y0, x1, y1, (0.97, 0.97, 0.95))
    c.rect(x0 + 0.04 * (x1 - x0), y0 + 0.2 * (y1 - y0), x1 - 0.04 * (x1 - x0), y1 - 0.04 * (y1 - y0), sky)
    cx = (x0 + x1) / 2
    w = x1 - x0
    h = y1 - y0
    skin = _ch(rng, [(0.95, 0.8, 0.65), (0.75, 0.55, 0.4), (0.45, 0.3, 0.2), (0.88, 0.7, 0.55)])
    hair = _ch(rng, [(0.1, 0.07, 0.05), (0.35, 0.2, 0.1), (0.85, 0.7, 0.35), (0.05, 0.05, 0.05)])
    c.poly([(cx - 0.4 * w, y0 + 0.2 * h), (cx - 0.36 * w, y0 + 0.42 * h), (cx - 0.1 * w, y0 + 0.5 * h),
            (cx + 0.1 * w, y0 + 0.5 * h), (cx + 0.36 * w, y0 + 0.42 * h), (cx + 0.4 * w, y0 + 0.2 * h)], shirt)
    c.poly([(cx - 0.08 * w, y0 + 0.5 * h), (cx + 0.08 * w, y0 + 0.5 * h), (cx, y0 + 0.4 * h)], trim)
    c.rect(cx - 0.06 * w, y0 + 0.46 * h, cx + 0.06 * w, y0 + 0.54 * h, skin)
    c.circle(cx, y0 + 0.66 * h, 0.15 * h, hair)
    c.circle(cx, y0 + 0.63 * h, 0.13 * h, skin)
    if rng.random() < 0.5:                                            # a mullet or a mustache: it was the era
        c.rect(cx - 0.05 * w, y0 + 0.57 * h, cx + 0.05 * w, y0 + 0.59 * h, hair)
    for sx in (-1, 1):
        c.circle(cx + sx * 0.05 * w * 0.9, y0 + 0.65 * h, 0.012 * h, INK)
    c.rect(x0, y0, x1, y0 + 0.2 * h, trim if trim != (0.95, 0.95, 0.95) else (0.15, 0.2, 0.45))
    _ct(c, _ch(rng, SURN), cx - 0.08 * w, y0 + 0.16 * h, 0.1 * h, (1, 1, 1), maxw=0.7 * w)
    _flagbar(c, x1 - 0.22 * w, y0 + 0.04 * h, x1 - 0.05 * w, y0 + 0.15 * h, rng)
    c.text(str(num if num is not None else int(rng.integers(1, 448))), x0 + 0.06 * w, y1 - 0.06 * h, 0.07 * h, INK, bold=True)


def _sticker_print(rng, name):
    c = _cv(256, 320, (0.97, 0.97, 0.95))
    _player_card(c, rng, 0.0, 0.0, 1.0, 1.0)
    c.noise(rng, 0.015)
    return c.image(name)


def _sticker_back(rng, name, num=None):
    c = _cv(128, 160, (0.95, 0.95, 0.93))
    c.rect(0.0, 0.0, 1.0, 0.5, (0.9, 0.9, 0.88))
    c.line([(0.0, 0.5), (1.0, 0.5)], 0.012, (0.7, 0.7, 0.7))                 # the peel line
    _ct(c, "PANETTI", 0.5, 0.86, 0.1, (0.15, 0.25, 0.6))
    _ct(c, str(num if num is not None else int(rng.integers(1, 448))), 0.5, 0.7, 0.16, INK)
    c.text("MADE IN MODENA", 0.08, 0.35, 0.05, (0.4, 0.4, 0.42))
    return c.image(name)


@obj("football_sticker", eras=(0, 1, 2, 3), mass=0.001, **RARE)
def football_sticker(b, rng, pal):
    """One loose sticker, maybe a double, maybe the one you needed."""
    rot = (0, 0, float(rng.normal(0, 0.25)))
    b.box((0.05, 0.065, 0.0004), rot=rot, mat="edge")
    b.plane(0.05, 0.065, loc=(0, 0, 0.00025), rot=rot, mat="front", cuts=2)
    b.plane(0.05, 0.065, loc=(0, 0, -0.00025), rot=(PI, 0, rot[2]), mat="back", cuts=2)
    return {"edge": P((0.95, 0.95, 0.93), 0.5), "front": PR(_sticker_print(rng, "fbst"), 0.3),
            "back": PR(_sticker_back(rng, "fbbk"), 0.6)}


def _packet_print(rng, name):
    cup, col = _ch(rng, CUPS)
    c = _cv(512, 256, col)
    for i in range(14):                                                # foil sunburst
        a = 2 * PI * i / 14
        c.poly([(0.75, 0.5), (0.75 + 0.6 * math.cos(a) * 0.5, 0.5 + 0.6 * math.sin(a)),
                (0.75 + 0.6 * math.cos(a + 0.2) * 0.5, 0.5 + 0.6 * math.sin(a + 0.2))],
               tuple(min(1, v + 0.15) for v in col))
    c.rect(0.55, 0.76, 0.95, 0.94, (0.97, 0.97, 0.95))
    _ct(c, "PANETTI", 0.75, 0.92, 0.14, (0.15, 0.25, 0.6), maxw=0.36)
    _ct(c, cup, 0.75, 0.68, 0.16, (1, 0.85, 0.1), maxw=0.36)
    c.circle(0.75, 0.38, 0.13, (0.97, 0.97, 0.97))
    for k in range(5):
        a = 2 * PI * k / 5 + 0.3
        c.circle(0.75 + 0.05 * math.cos(a) * 0.5, 0.38 + 0.05 * math.sin(a), 0.035, INK)
    _ct(c, "5 FIGURINE", 0.75, 0.18, 0.08, (1, 1, 1), maxw=0.3)
    c.rect(0.0, 0, 0.5, 1, tuple(v * 0.8 for v in col))
    c.text("STICKERS - AUTOCOLLANTS", 0.04, 0.6, 0.05, (1, 1, 1))
    return c.image(name)


@obj("sticker_packet", eras=(0, 1, 2), mass=0.004, hero=(0, -1, 0), **RARE)
def sticker_packet(b, rng, pal):
    """A five-sticker packet, sealed or torn across the top with the stickers half out."""
    w, h = 0.055, 0.075
    torn = rng.random() < 0.45
    hh = h * (0.82 if torn else 1.0)
    _pillow(b, w, hh, 0.006, "print", rings=10)
    b.box((w, 0.0015, 0.008), loc=(0, 0, -hh / 2 - 0.003), mat="print2")
    if torn:
        for k in range(int(rng.integers(2, 4))):
            b.box((0.046, 0.0004, 0.062), loc=(0.002 * k, 0.0005 * k, 0.012 + 0.004 * k), rot=(0, 0.04 * k, 0), mat="stk")
    else:
        b.box((w, 0.0015, 0.008), loc=(0, 0, hh / 2 + 0.003), mat="print2")
    img = _packet_print(rng, "pkt")
    return {"print": PR(img, 0.25, metal=0.4), "print2": P(tuple(img.pixels[0:3]), 0.3, metal=0.4),
            "stk": P((0.96, 0.96, 0.94), 0.5)}


def _album_cover(rng, name, cup, col):
    c = _cv(320, 420, col)
    c.rect(0, 0, 1, 0.42, (0.15, 0.55, 0.2))                                  # the pitch
    for k in range(6):
        c.rect(0, k * 0.07, 1, k * 0.07 + 0.035, (0.2, 0.62, 0.25))
    c.line([(0.1, 0.0), (0.3, 0.42)], 0.008, (0.95, 0.95, 0.95))
    c.circle(0.62, 0.42, 0.16, (0.97, 0.97, 0.97))                           # the ball in flight
    for k in range(5):
        a = 2 * PI * k / 5
        c.circle(0.62 + 0.07 * math.cos(a) * 420 / 320, 0.42 + 0.07 * math.sin(a), 0.035, INK)
    c.circle(0.62, 0.42, 0.04, INK)
    _ct(c, "PANETTI", 0.5, 0.95, 0.06, (0.97, 0.97, 0.97))
    _ct(c, cup, 0.5, 0.86, 0.15, (1.0, 0.85, 0.1), maxw=0.86)
    _ct(c, "OFFICIAL STICKER ALBUM", 0.5, 0.68, 0.035, (0.97, 0.97, 0.97))
    c.rect(0.0, 0.0, 1.0, 0.06, (0.97, 0.97, 0.95))
    _ct(c, "LIRE 600 - 30P", 0.5, 0.05, 0.035, INK)
    c.noise(rng, 0.02)
    return c.image(name)


def _album_page(rng, name):
    c = _cv(320, 420, (0.92, 0.92, 0.88))
    c.rect(0, 0.88, 1, 1, (0.15, 0.25, 0.6))
    _flagbar(c, 0.04, 0.9, 0.18, 0.98, rng)
    _ct(c, _ch(rng, ["SQUADRA", "TEAM", "EQUIPE", "SELECCION"]), 0.6, 0.97, 0.06, (1, 1, 1))
    k = 1
    for r in range(4):
        for col in range(3):
            x0, y0 = 0.05 + col * 0.31, 0.66 - r * 0.21
            if rng.random() < 0.55:
                _player_card(c, rng, x0, y0, x0 + 0.27, y0 + 0.19, num=k)
            else:
                c.rect(x0, y0, x0 + 0.27, y0 + 0.19, (0.8, 0.8, 0.76))
                _ct(c, str(int(rng.integers(1, 448))), x0 + 0.135, y0 + 0.12, 0.04, (0.55, 0.55, 0.55))
            k += 1
    return c.image(name)


@obj("sticker_album", eras=(0, 1, 2), mass=0.2, **RARE)
def sticker_album(b, rng, pal):
    """The album, cover curling open on a page that is about half full. It was always about half full."""
    cup, col = _ch(rng, CUPS)
    W, H, T_ = 0.19, 0.26, 0.007
    b.box((W, H, T_), loc=(0, 0, 0), mat="pages")
    b.plane(W * 0.99, H * 0.99, loc=(0, 0, T_ / 2 + 0.0003), mat="page", cuts=2)
    ang = float(rng.uniform(0.15, 0.9)) if rng.random() < 0.6 else 0.0
    hx = -W / 2
    cx = hx + W / 2 * math.cos(ang)
    cz = T_ / 2 + 0.0012 + W / 2 * math.sin(ang)
    b.box((W, H, 0.0012), loc=(cx, 0, cz), rot=(0, -ang, 0), mat="cover_edge")
    b.plane(W, H, loc=(cx - 0.0007 * math.sin(ang), 0, cz + 0.0007 * math.cos(ang)), rot=(0, -ang, 0), mat="cover", cuts=2)
    b.box((W, H, 0.0012), loc=(0, 0, -T_ / 2 - 0.0006), mat="cover_edge")
    return {"pages": P((0.94, 0.93, 0.9), 0.8), "page": PR(_album_page(rng, "albp"), 0.6),
            "cover_edge": P(col, 0.4), "cover": PR(_album_cover(rng, "albc", cup, col), 0.35, coat=0.3)}


def _badge_print(rng, name):
    c = _cv(256, 300, (0.85, 0.75, 0.35))
    for i in range(40):                                                   # the foil sparkle
        x, y = float(rng.uniform(0, 1)), float(rng.uniform(0, 1))
        c.line([(x - 0.08, y - 0.08), (x + 0.08, y + 0.08)], 0.006, (1.0, 0.95, 0.7))
    a, b_ = _ch(rng, KITS)
    shield = [(0.2, 0.85), (0.8, 0.85), (0.8, 0.45), (0.5, 0.12), (0.2, 0.45)]
    c.poly(shield, (0.95, 0.85, 0.4))
    c.poly([(x * 0.85 + 0.075, y * 0.85 + 0.07) for x, y in shield], a)
    for k in range(3):
        c.poly([(0.3 + k * 0.15, 0.78), (0.37 + k * 0.15, 0.78), (0.37 + k * 0.15, 0.3), (0.3 + k * 0.15, 0.35)], b_)
    c.poly(_star(0.5, 0.92, 0.05, asp=256 / 300), (1.0, 0.95, 0.6))
    return c.image(name)


@obj("shiny_badge", eras=(0, 1, 2), mass=0.001, **SPECIAL)
def shiny_badge(b, rng, pal):
    """The shiny: a foil team crest. Worth five normal ones on the playground exchange rate."""
    rot = (0, 0, float(rng.normal(0, 0.3)))
    b.box((0.05, 0.065, 0.0004), rot=rot, mat="edge")
    b.plane(0.05, 0.065, loc=(0, 0, 0.00025), rot=rot, mat="foil", cuts=2)
    return {"edge": P((0.95, 0.95, 0.93), 0.5), "foil": PR(_badge_print(rng, "shiny"), 0.18, metal=0.85)}


@obj("swap_stack", eras=(0, 1, 2), mass=0.03, **SPECIAL)
def swap_stack(b, rng, pal):
    """The swaps: a fat stack of doubles held with a rubber band, thumbed until the corners went round."""
    n = int(rng.integers(25, 45))
    th = n * 0.0004
    b.box((0.05, 0.065, th), loc=(0, 0, 0), mat="edge", bevel=0.002)
    b.plane(0.049, 0.064, loc=(0, 0, th / 2 + 0.0002), mat="front", cuts=2)
    hz = th / 2 + 0.0012
    for k in range(int(rng.integers(1, 3))):
        ha = 0.0257 if k == 0 else 0.0332
        pts = []
        for i in range(33):                                      # a rounded rectangle hugging the stack
            t = 2 * PI * i / 32
            cx_, cz_ = math.cos(t), math.sin(t)
            m = max(abs(cx_) / ha, abs(cz_) / hz)
            u, z = cx_ / m, cz_ / m
            pts.append((u, 0.006, z) if k == 0 else (0.004, u, z))
        b.tube(pts, 0.0012, mat="band", seg=6)
    return {"edge": P((0.93, 0.93, 0.9), 0.7), "front": PR(_sticker_print(rng, "swaps"), 0.35),
            "band": RUB(_ch(rng, [(0.8, 0.6, 0.4), (0.85, 0.15, 0.15), (0.2, 0.4, 0.85)]))}


@obj("flick_figure", eras=(0, 1, 2), mass=0.006, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def flick_figure(b, rng, pal):
    """The table-football man: a painted little player glued to a disc on a weighted half-ball. Flick to kick."""
    shirt, shorts = _ch(rng, KITS)
    sock = shirt if rng.random() < 0.5 else shorts
    base = _ch(rng, [(0.85, 0.1, 0.12), (0.1, 0.25, 0.7), (0.95, 0.95, 0.95), (0.05, 0.05, 0.05)])
    b.lathe([(0.0, -0.007), (0.007, -0.0065), (0.0105, -0.004), (0.0115, 0.0), (0.0, 0.0)], mat="base", seg=24)
    b.cyl(0.012, 0.0015, loc=(0, 0, 0.0007), mat="ring", seg=24)
    z = 0.0015
    for sx in (-1, 1):
        b.cyl(0.0012, 0.008, loc=(sx * 0.0018, 0, z + 0.004), mat="sock", seg=6)
        b.box((0.0024, 0.004, 0.0015), loc=(sx * 0.0018, -0.001, z + 0.0008), mat="boot")
    b.box((0.006, 0.003, 0.004), loc=(0, 0, z + 0.0095), mat="shorts", bevel=0.0005)
    b.box((0.0065, 0.003, 0.0075), loc=(0, 0, z + 0.015), mat="shirt", bevel=0.0008)
    for sx in (-1, 1):
        b.cyl(0.001, 0.007, loc=(sx * 0.0042, 0, z + 0.014), rot=(0, sx * 0.25, 0), mat="shirt", seg=6)
    b.sphere(0.0022, loc=(0, 0, z + 0.0212), mat="skin", seg=10)
    b.sphere(0.0023, loc=(0, 0.0004, z + 0.0222), scale=(1, 1, 0.6), mat="hair", seg=10)
    return {"base": P(base, 0.3, coat=0.4), "ring": P((0.95, 0.95, 0.95), 0.4), "sock": P(sock, 0.45),
            "boot": P(BLACK, 0.4), "shorts": P(shorts, 0.45), "shirt": P(shirt, 0.45),
            "skin": P(_ch(rng, [(0.95, 0.78, 0.62), (0.6, 0.42, 0.3)]), 0.5), "hair": P((0.12, 0.08, 0.05), 0.6)}


def _ball_print(rng, name, base, spot):
    c = _cv(512, 256, base)
    verts = [(0.0, 90.0), (0.0, -90.0)] + [(72 * k, 26.57) for k in range(5)] + [(72 * k + 36, -26.57) for k in range(5)]
    for lon, lat in verts:
        r = 0.09
        cy = 0.5 + lat / 180.0
        if abs(lat) > 80:
            c.rect(0, cy - r * 0.8, 1, cy + r * 0.8, spot) if lat > 0 else c.rect(0, cy - r * 0.8, 1, cy + r * 0.8, spot)
            continue
        stretch = 1.0 / max(math.cos(math.radians(lat)), 0.3)
        for dx in (-1, 0, 1):
            cx = lon / 360.0 + dx
            pts = [(cx + r * stretch * 0.5 * math.cos(2 * PI * i / 5 + PI / 2), cy + r * math.sin(2 * PI * i / 5 + PI / 2))
                   for i in range(5)]
            c.poly(pts, spot)
    return c.image(name)


@obj("foam_football", eras=(0, 1, 2, 3), mass=0.03, **RARE)
def foam_football(b, rng, pal):
    """The soft indoor ball, the only kind allowed in the house. Still broke the lamp."""
    base, spot = _ch(rng, [((0.97, 0.97, 0.95), INK), ((1.0, 0.85, 0.1), (0.1, 0.3, 0.8)), ((1.0, 0.5, 0.05), INK),
                           ((0.95, 0.95, 0.95), (0.85, 0.1, 0.12))])
    b.sphere(0.05, scale=(1, 1, float(rng.uniform(0.75, 1.0))), mat="foam", seg=28)
    return {"foam": PR(_ball_print(rng, "fball", base, spot), 0.95)}


# ================================================================================================
# PICK 'N' MIX: the Saturday paper bag from the high-street sweet wall
# ================================================================================================

def _bag_print(rng, name):
    c = _cv(512, 256, (0.98, 0.97, 0.95))
    cols = [(0.9, 0.15, 0.3), (1.0, 0.75, 0.1), (0.2, 0.6, 0.9), (0.3, 0.75, 0.3)]
    for k in range(16):
        x = k / 16
        c.rect(x, 0, x + 0.022, 1, cols[k % 4])
    c.rect(0.55, 0.42, 0.95, 0.78, (0.98, 0.97, 0.95))
    _ct(c, "WOOLWORMS", 0.75, 0.74, 0.11, (0.85, 0.1, 0.15), maxw=0.36)
    _ct(c, "PICK 'N' MIX", 0.75, 0.58, 0.1, (0.2, 0.25, 0.6), maxw=0.36)
    c.text("PRICE PER 100G", 0.6, 0.47, 0.04, INK)
    c.noise(rng, 0.02)
    return c.image(name)


@obj("pick_bag", eras=(0, 1, 2, 3), mass=0.008, hero=(0, -1, 0), **SPECIAL)
def pick_bag(b, rng, pal):
    """The striped paper bag, top twisted shut, corners gone see-through from the sugar."""
    w, h = 0.13, 0.17
    rs = []
    n, rings = 24, 12
    for j in range(rings):
        u = j / (rings - 1)
        z = -h / 2 + h * u
        t = 0.05 * math.sin(PI * min(u * 1.25, 1.0)) ** 0.5 + 0.002
        ww = w * (1.0 - 0.55 * max(0.0, u - 0.7) / 0.3)            # gathered at the top
        rs.append([(ww / 2 * math.cos(2 * PI * i / n), t / 2 * math.sin(2 * PI * i / n), z) for i in range(n)])
    b.loft(rs, mat="paper")
    b.lathe([(0.0, h / 2 - 0.004), (0.016, h / 2), (0.012, h / 2 + 0.012), (0.02, h / 2 + 0.022), (0.0, h / 2 + 0.024)],
            rot=(0, 0, 0.3), mat="paper2", seg=10, scale=(1.4, 0.5, 1.0))
    img = _bag_print(rng, "pnm")
    return {"paper": PR(img, 0.85), "paper2": P((0.95, 0.94, 0.9), 0.9)}


@obj("candy_scoop", eras=(0, 1, 2, 3), mass=0.02, **SPECIAL)
def candy_scoop(b, rng, pal):
    """The scoop off the sweet wall, chained to nothing, in the bag by mistake."""
    L, W = 0.08, 0.05
    b.box((L, W, 0.0025), loc=(0, 0, -0.012), mat="p", bevel=0.001)
    for sy in (-1, 1):
        b.extrude([(-L / 2, 0.0), (L / 2, 0.0), (L / 2, 0.024), (-L / 2 + 0.03, 0.024)], 0.0025,
                  loc=(0, sy * W / 2, -0.0135), rot=(PI / 2, 0, 0), mat="p")
    b.box((0.0025, W, 0.026), loc=(-L / 2, 0, -0.0005), mat="p")
    b.tube([(-L / 2, 0, 0.006), (-L / 2 - 0.03, 0, 0.012), (-L / 2 - 0.07, 0, 0.016)], 0.0055, mat="p", seg=10)
    return {"p": P(_ch(rng, [(0.95, 0.95, 0.95), (0.9, 0.15, 0.2), (0.85, 0.9, 0.95)]), 0.25, coat=0.4)}


def _cola_bottle(b, loc, rot, mat, s=1.0):
    prof = [(0.0, -0.013), (0.0065, -0.0128), (0.0072, -0.006), (0.0058, 0.0), (0.0068, 0.004), (0.0045, 0.009),
            (0.0028, 0.012), (0.003, 0.0145), (0.0, 0.0148)]
    b.lathe([(r * s, z * s) for r, z in prof], loc=loc, rot=rot, mat=mat, seg=14)


@obj("cola_bottles", eras=(0, 1, 2, 3), mass=0.008, **RARE)
def cola_bottles(b, rng, pal):
    """Gummy cola bottles: brown at the bottom, clear at the top, sometimes rolled in fizzy sugar."""
    fizz = rng.random() < 0.35
    for k in range(int(rng.integers(3, 7))):
        x, y = (float(v) for v in rng.normal(0, 0.014, 2))
        _cola_bottle(b, (x, y, 0), (PI / 2 + float(rng.normal(0, 0.3)), 0, float(rng.uniform(0, 2 * PI))),
                     "gum" if k % 3 else "gum2", float(rng.uniform(0.95, 1.15)))
    if fizz:
        return {"gum": P((0.55, 0.25, 0.08), 0.9), "gum2": P((0.6, 0.3, 0.1), 0.9)}
    return {"gum": T((0.5, 0.2, 0.04), 0.25), "gum2": T((0.6, 0.28, 0.06), 0.25)}


@obj("foam_shrimps", eras=(0, 1, 2, 3), mass=0.006, **RARE)
def foam_shrimps(b, rng, pal):
    """Pink-and-white foam shrimps: curled, chalky, and nothing like a shrimp."""
    for k in range(int(rng.integers(3, 6))):
        x, y = (float(v) for v in rng.normal(0, 0.016, 2))
        a0 = float(rng.uniform(0, 2 * PI))
        pts = [(0.012 * math.cos(a0 + t), 0.012 * math.sin(a0 + t), 0.0) for t in np.linspace(0, 3.6, 9)]
        b.tube(pts, lambda u: 0.006 * (1 - 0.6 * u) + 0.0015, mat="pink", seg=10, loc=(x, y, 0.002))
        b.tube(pts, lambda u: 0.006 * (1 - 0.6 * u) + 0.0012, mat="white", seg=10, loc=(x, y, -0.002))
    return {"pink": ("foam", {"color": (1.0, 0.6, 0.72)}), "white": ("foam", {"color": (0.98, 0.95, 0.92)})}


@obj("fried_eggs", eras=(0, 1, 2, 3), mass=0.006, **SPECIAL)
def fried_eggs(b, rng, pal):
    """Gummy fried eggs: a white foam puddle and a yellow gummy yolk."""
    for k in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.02, 2))
        n = 12
        pts = [(0.016 * math.cos(2 * PI * i / n) * float(rng.uniform(0.8, 1.15)),
                0.016 * math.sin(2 * PI * i / n) * float(rng.uniform(0.8, 1.15))) for i in range(n)]
        rot = (float(rng.normal(0, 0.3)), float(rng.normal(0, 0.3)), 0)
        b.extrude(pts, 0.004, loc=(x, y, 0), rot=rot, mat="white", bevel=0.0015)
        b.sphere(0.0075, loc=(x, y, 0.002), rot=rot, scale=(1, 1, 0.55), mat="yolk", seg=14)
    return {"white": ("foam", {"color": (0.98, 0.97, 0.93)}), "yolk": P((1.0, 0.72, 0.05), 0.25, coat=0.7)}


@obj("white_mice", eras=(0, 1, 2), mass=0.005, hero=(0, -1, 0), **SPECIAL)
def white_mice(b, rng, pal):
    """Chalky sugar mice, white and pink, with a sugar-string tail."""
    for k in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.015, 2))
        a = float(rng.uniform(0, 2 * PI))
        ca, sa = math.cos(a), math.sin(a)
        col = "pink" if rng.random() < 0.35 else "white"
        b.sphere(0.009, loc=(x, y, 0), rot=(0, 0, a), scale=(1.6, 1.0, 0.85), mat=col, seg=14)
        for sy in (-1, 1):
            b.sphere(0.0035, loc=(x + 0.008 * ca - sy * 0.004 * sa, y + 0.008 * sa + sy * 0.004 * ca, 0.006),
                     rot=(0, 0, a), scale=(0.5, 1, 1), mat=col, seg=8)
        b.tube([(x - 0.014 * ca, y - 0.014 * sa, -0.002), (x - 0.024 * ca + 0.004 * sa, y - 0.024 * sa, -0.004),
                (x - 0.032 * ca, y - 0.03 * sa, -0.004)], 0.0008, mat="tail", seg=5)
    return {"white": P((0.97, 0.95, 0.92), 0.85), "pink": P((1.0, 0.75, 0.82), 0.85), "tail": P((0.9, 0.85, 0.8), 0.7)}


@obj("flying_saucers", eras=(0, 1, 2, 3), mass=0.003, **RARE)
def flying_saucers(b, rng, pal):
    """Rice-paper flying saucers full of sherbet. The paper stuck to the roof of your mouth."""
    cols = [(1.0, 0.75, 0.8), (0.75, 0.85, 1.0), (1.0, 0.95, 0.7), (0.8, 1.0, 0.8), (1.0, 0.85, 0.65), (0.9, 0.8, 1.0)]
    specs = {}
    for k in range(int(rng.integers(3, 7))):
        x, y = (float(v) for v in rng.normal(0, 0.018, 2))
        rot = (float(rng.normal(0, 0.5)), float(rng.normal(0, 0.5)), 0)
        m = f"p{k % 3}"
        b.lathe([(0.0, -0.005), (0.009, -0.004), (0.0125, -0.0008), (0.017, 0.0), (0.0125, 0.0008), (0.009, 0.004),
                 (0.0, 0.005)], loc=(x, y, 0), rot=rot, mat=m, seg=20)
        specs[m] = P(cols[(k * 2 + int(rng.integers(0, 6))) % 6], 0.95)
    return specs


@obj("fizzy_laces", eras=(0, 1, 2, 3), mass=0.008, **RARE)
def fizzy_laces(b, rng, pal):
    """Sour laces in sugar, tangled the way they came out of the jar."""
    cols = [(0.9, 0.12, 0.15), (0.35, 0.8, 0.2), (0.25, 0.45, 0.95), (1.0, 0.6, 0.1)]
    specs = {}
    for k in range(int(rng.integers(3, 6))):
        ph = float(rng.uniform(0, 6))
        yy = float(rng.normal(0, 0.01))
        pts = [(-0.08 + 0.004 * i, yy + 0.018 * math.sin(i * 0.225 + ph), 0.004 * math.sin(i * 0.42 + ph)) for i in range(41)]
        m = f"l{k}"
        b.tube(pts, 0.0022, mat=m, seg=7)
        specs[m] = P(cols[(k + int(rng.integers(0, 4))) % 4], 0.85)
    return specs


@obj("jelly_babies", eras=(0, 1, 2, 3), mass=0.006, hero=(0, -1, 0), **RARE)
def jelly_babies(b, rng, pal):
    """Floury little gummy babies in six colors. Heads first, always."""
    cols = [(0.9, 0.1, 0.15), (1.0, 0.55, 0.1), (1.0, 0.85, 0.15), (0.35, 0.75, 0.2), (0.25, 0.2, 0.3), (1.0, 0.6, 0.75)]
    specs = {}
    for k in range(int(rng.integers(3, 6))):
        x, y = (float(v) for v in rng.normal(0, 0.016, 2))
        a = float(rng.uniform(-0.6, 0.6))
        m = f"j{k}"
        z = 0.0
        b.sphere(0.0065, loc=(x, y, z), rot=(0, a, 0), scale=(0.8, 0.55, 1.15), mat=m, seg=12)
        if rng.random() < 0.8:                                          # not every head survived
            b.sphere(0.0048, loc=(x + 0.011 * math.sin(a), y, z + 0.011 * math.cos(a)), scale=(1, 0.75, 1), mat=m, seg=12)
        for sx in (-1, 1):
            b.sphere(0.0022, loc=(x + sx * 0.0058, y, z + 0.002), scale=(1, 0.7, 1.3), mat=m, seg=8)
            b.sphere(0.0025, loc=(x + sx * 0.003 - 0.009 * math.sin(a), y, z - 0.0085), scale=(1, 0.7, 1.2), mat=m, seg=8)
        specs[m] = P(cols[(k + int(rng.integers(0, 6))) % 6], 0.7)
    return specs


def _wham_print(rng, name):
    c = _cv(512, 128, (1.0, 0.35, 0.65))
    c.rect(0, 0, 1, 0.28, (0.2, 0.55, 0.95))
    c.rect(0, 0.72, 1, 1, (0.2, 0.55, 0.95))
    c.poly([(0.08, 0.95), (0.18, 0.95), (0.13, 0.55), (0.2, 0.55), (0.06, 0.05), (0.1, 0.45), (0.04, 0.45)], (1.0, 0.95, 0.1))
    _ct(c, "WHAMMO!", 0.5, 0.78, 0.55, (1.0, 0.95, 0.1), maxw=0.55)
    c.text("FIZZY CHEW BAR", 0.62, 0.22, 0.14, (1, 1, 1))
    c.poly(_star(0.9, 0.55, 0.3, 8, 0.6, asp=4.0), (1.0, 0.95, 0.1))
    c.text("2P", 0.875, 0.65, 0.2, (0.9, 0.1, 0.4), bold=True)
    return c.image(name)


@obj("chew_bar", eras=(0, 1, 2, 3), mass=0.017, **SPECIAL)
def chew_bar(b, rng, pal):
    """The fizzy chew bar: pink and blue wrapper, sherbet bits in the chew, two pence."""
    _flow_bar(b, 0.11, 0.025, 0.006, "top", "wrap", crimp=0.008)
    img = _wham_print(rng, "wham")
    return {"wrap": P((1.0, 0.35, 0.65), 0.3, coat=0.4), "top": PR(img, 0.3)}


# ================================================================================================
# GACHAPON: the capsule machines outside every shop in Japan
# ================================================================================================

@obj("gacha_capsule", eras=(0, 1, 2, 3, 4), mass=0.01, **RARE)
def gacha_capsule(b, rng, pal):
    """A capsule: clear top, colored bottom, a toy folded inside a paper slip."""
    R = 0.024
    bot = [(0.0, -R), (R * 0.5, -R * 0.87), (R * 0.87, -R * 0.5), (R, 0.0), (R - 0.001, 0.0), (R * 0.87 - 0.001, -R * 0.5),
           (0.0, -R + 0.001)]
    top = [(0.0, R), (R * 0.52, R * 0.87), (R * 0.88 + 0.0005, R * 0.5), (R + 0.0008, 0.0), (R + 0.0008, -0.004),
           (R - 0.0002, -0.004), (R - 0.0002, 0.0), (R * 0.87 - 0.0008, R * 0.5), (0.0, R - 0.0008)]
    opened = rng.random() < 0.35
    b.lathe(bot, mat="base", seg=28)
    if opened:
        b.lathe(top, loc=(0.052, 0.006, -0.004), rot=(PI - 0.4, 0.2, 0), mat="clear", seg=28)
    else:
        b.lathe(top, mat="clear", seg=28)
    b.sphere(0.012, loc=(0, 0, 0.002), scale=(1, 0.8, 0.9), mat="toy", seg=12)
    b.plane(0.03, 0.02, loc=(0.004, 0.012, -0.006), rot=(0.6, 0.2, 0.3), mat="slip", cuts=2)
    base = _ch(rng, [(0.95, 0.2, 0.3), (0.2, 0.5, 0.95), (1.0, 0.8, 0.1), (0.3, 0.8, 0.4), (0.97, 0.97, 0.97),
                     (0.6, 0.3, 0.85)])
    return {"base": P(base, 0.25, coat=0.5), "clear": _clear(rng, 0.18),
            "toy": P(_ch(rng, [(0.95, 0.6, 0.7), (0.5, 0.85, 0.95), (1.0, 0.9, 0.3)]), 0.4), "slip": P((0.97, 0.96, 0.93), 0.9)}


@obj("gacha_figure", eras=(0, 1, 2, 3, 4), mass=0.006, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def gacha_figure(b, rng, pal):
    """A 200-yen figure: a tiny robot, a lazy cat or a pocket dinosaur. Painted, slightly off-register."""
    kind = int(rng.integers(0, 3))
    a = _ch(rng, [(0.95, 0.95, 0.95), (0.95, 0.6, 0.2), (0.4, 0.75, 0.4), (0.55, 0.7, 0.95), (0.95, 0.7, 0.75)])
    if kind == 0:
        b.box((0.016, 0.012, 0.016), loc=(0, 0, 0.012), mat="a", bevel=0.002)
        b.box((0.014, 0.011, 0.011), loc=(0, 0, 0.0265), mat="a", bevel=0.002)
        b.box((0.01, 0.002, 0.004), loc=(0, -0.0062, 0.027), mat="visor")
        b.cyl(0.0006, 0.008, loc=(0, 0, 0.036), mat="trim", seg=6)
        b.sphere(0.0015, loc=(0, 0, 0.0405), mat="lamp", seg=8)
        for sx in (-1, 1):
            b.box((0.005, 0.008, 0.008), loc=(sx * 0.004, 0, 0.002), mat="trim", bevel=0.001)
            b.box((0.004, 0.005, 0.012), loc=(sx * 0.011, 0, 0.013), mat="trim", bevel=0.001)
        return {"a": P(a, 0.35), "trim": P((0.35, 0.35, 0.38), 0.4), "visor": P((0.1, 0.8, 0.9), 0.2),
                "lamp": P((1.0, 0.2, 0.2), 0.3)}
    if kind == 1:
        b.sphere(0.012, loc=(0, 0.004, 0.006), scale=(1.1, 1.4, 0.6), mat="a", seg=14)
        b.sphere(0.009, loc=(0, -0.01, 0.01), scale=(1.15, 1, 0.9), mat="a", seg=14)
        for sx in (-1, 1):
            b.extrude([(-0.003, 0), (0.003, 0), (0, 0.006)], 0.003, loc=(sx * 0.006, -0.01, 0.017), rot=(PI / 2, 0, 0), mat="a")
            b.box((0.004, 0.0006, 0.0008), loc=(sx * 0.004, -0.0185, 0.012), mat="ink")
        b.tube([(0, 0.02, 0.004), (0.01, 0.026, 0.004), (0.014, 0.018, 0.005)], 0.002, mat="a", seg=6)
        return {"a": P(a, 0.4), "ink": P(INK, 0.5)}
    b.sphere(0.011, loc=(0, 0.004, 0.012), scale=(1, 1.3, 1), mat="a", seg=14)
    b.sphere(0.008, loc=(0, -0.012, 0.024), scale=(1, 1.2, 0.9), mat="a", seg=14)
    for k in range(4):
        b.extrude([(-0.002, 0), (0.002, 0), (0, 0.004)], 0.002, loc=(0, 0.004 - k * 0.005, 0.023 + 0.001 * (2 - abs(k - 1.5))),
                  rot=(PI / 2, 0, PI / 2), mat="spike")
    for sx in (-1, 1):
        b.cyl(0.003, 0.008, loc=(sx * 0.006, 0.004, 0.003), mat="a", seg=8)
        b.sphere(0.0013, loc=(sx * 0.0045, -0.019, 0.026), mat="ink", seg=6)
    b.tube([(0, 0.016, 0.01), (0, 0.026, 0.005), (0.004, 0.032, 0.002)], lambda u: 0.004 * (1 - u) + 0.0008, mat="a", seg=8)
    return {"a": P(a, 0.4), "spike": P((0.95, 0.9, 0.3), 0.4), "ink": P(INK, 0.5)}


def _hero_figure(c, rng, cx, cy, r):
    """Our own caped kid hero with a bowl haircut and a lightning chest badge."""
    asp = c.w / c.h
    cape = _ch(rng, [(0.85, 0.1, 0.12), (0.1, 0.25, 0.7), (0.95, 0.75, 0.1)])
    suit = _ch(rng, [(0.15, 0.3, 0.8), (0.95, 0.95, 0.95), (0.2, 0.6, 0.3)])
    c.poly([(cx - 0.9 * r / asp, cy - 1.3 * r), (cx - 0.4 * r / asp, cy + 0.3 * r), (cx + 0.4 * r / asp, cy + 0.3 * r),
            (cx + 0.9 * r / asp, cy - 1.3 * r)], cape)
    c.rect(cx - 0.4 * r / asp, cy - 1.2 * r, cx + 0.4 * r / asp, cy + 0.3 * r, suit)
    c.poly([(cx - 0.05 * r / asp, cy + 0.1 * r), (cx + 0.15 * r / asp, cy - 0.2 * r), (cx, cy - 0.25 * r),
            (cx + 0.1 * r / asp, cy - 0.6 * r), (cx - 0.15 * r / asp, cy - 0.2 * r), (cx, cy - 0.15 * r)], (1.0, 0.85, 0.1))
    c.circle(cx, cy + 0.65 * r, 0.42 * r, (0.97, 0.8, 0.65))
    c.poly([(cx - 0.45 * r / asp, cy + 0.65 * r), (cx - 0.4 * r / asp, cy + 1.05 * r), (cx + 0.4 * r / asp, cy + 1.05 * r),
            (cx + 0.45 * r / asp, cy + 0.65 * r)], INK)
    for sx in (-1, 1):
        c.circle(cx + sx * 0.15 * r / asp, cy + 0.6 * r, 0.06 * r, INK)


def _menko_print(rng, name):
    c = _cv(256, 256, _ch(rng, [(0.95, 0.85, 0.3), (0.55, 0.8, 0.95), (0.95, 0.55, 0.45)]))
    for i in range(16):
        a = 2 * PI * i / 16
        c.poly([(0.5, 0.5), (0.5 + 0.8 * math.cos(a), 0.5 + 0.8 * math.sin(a)),
                (0.5 + 0.8 * math.cos(a + 0.2), 0.5 + 0.8 * math.sin(a + 0.2))], (1.0, 0.95, 0.85))
    _hero_figure(c, rng, 0.5, 0.42, 0.22)
    c.circle(0.5, 0.5, 0.48, (0.85, 0.1, 0.12), ring=0.05)
    for k, ch in enumerate(str(int(rng.integers(1, 99)))):
        c.text(ch, 0.12 + k * 0.07, 0.9, 0.12, INK, bold=True)
    return c.image(name)


@obj("menko_card", eras=(0, 1, 2), mass=0.003, **SPECIAL)
def menko_card(b, rng, pal):
    """A round slapping card, thick board, bent from being slammed on the pavement."""
    r = 0.03
    b.cyl(r, 0.0016, rot=(float(rng.normal(0, 0.06)), 0, 0), mat="edge", seg=32)
    _disc(b, r * 0.985, 0.0009, "face")
    img = _menko_print(rng, "menko")
    return {"edge": ("cardboard", {"color": (0.75, 0.68, 0.55)}), "face": PR(img, 0.6)}


def _seal_print(rng, name):
    c = _cv(256, 256, (0.85, 0.85, 0.9))
    for i in range(60):
        x, y = float(rng.uniform(0, 1)), float(rng.uniform(0, 1))
        c.line([(x - 0.05, y), (x + 0.05, y)], 0.008, _ch(rng, [(1, 0.6, 0.9), (0.6, 0.9, 1), (1, 1, 0.6), (1, 1, 1)]))
    wing = _ch(rng, [(0.97, 0.97, 1.0), (0.2, 0.15, 0.3)])
    for sx in (-1, 1):                                                    # an angel or a devil, our own
        c.poly([(0.5, 0.55), (0.5 + sx * 0.42, 0.85), (0.5 + sx * 0.38, 0.6), (0.5 + sx * 0.44, 0.45),
                (0.5 + sx * 0.2, 0.42)], wing)
    c.circle(0.5, 0.45, 0.2, (1.0, 0.85, 0.75))
    c.circle(0.5, 0.75, 0.12, (1.0, 0.85, 0.2), ring=0.02) if wing[0] > 0.5 else (
        c.poly([(0.38, 0.6), (0.34, 0.78), (0.44, 0.63)], (0.85, 0.1, 0.1)), c.poly([(0.62, 0.6), (0.66, 0.78), (0.56, 0.63)], (0.85, 0.1, 0.1)))
    for sx in (-1, 1):
        c.circle(0.5 + sx * 0.07, 0.48, 0.035, INK)
    c.rect(0.0, 0.0, 1.0, 0.14, (0.15, 0.1, 0.35))
    _ct(c, _ch(rng, ["HOLY PRINCE", "DEVIL KING", "SUPER ZEUSU", "ANGEL NO.7"]), 0.5, 0.11, 0.08, (1, 0.9, 0.3))
    return c.image(name)


@obj("seal_sticker", eras=(0, 1, 2), mass=0.001, **SPECIAL)
def seal_sticker(b, rng, pal):
    """The holographic sticker out of a 30-yen wafer. Kids bought the wafers and threw the wafers away."""
    rot = (0, 0, float(rng.normal(0, 0.3)))
    b.box((0.048, 0.048, 0.0004), rot=rot, mat="edge")
    b.plane(0.047, 0.047, loc=(0, 0, 0.00025), rot=rot, mat="foil", cuts=2)
    return {"edge": P((0.85, 0.82, 0.75), 0.5), "foil": PR(_seal_print(rng, "seal"), 0.15, metal=0.75)}


def _tomiko_box(rng, name):
    c = _cv(256, 128, (0.85, 0.08, 0.12))
    c.rect(0, 0, 1, 0.3, (0.97, 0.97, 0.97))
    c.rect(0, 0.3, 1, 0.38, (0.1, 0.2, 0.65))
    _ct(c, "TOMIKO", 0.4, 0.88, 0.36, (0.97, 0.97, 0.97), maxw=0.6)
    c.text(f"NO.{int(rng.integers(1, 120))}", 0.72, 0.85, 0.16, (1, 0.9, 0.2))
    c.text("1/64 DIE-CAST", 0.05, 0.25, 0.13, (0.1, 0.2, 0.65))
    return c.image(name)


@obj("pocket_diecast", eras=(0, 1, 2, 3, 4), mass=0.045, **RARE)
def pocket_diecast(b, rng, pal):
    """A palm-sized die-cast car with opening-nothing and suspension that actually bounces. Sometimes still in its box."""
    col = _ch(rng, [(0.95, 0.95, 0.95), (0.8, 0.1, 0.1), (0.1, 0.3, 0.7), (0.15, 0.15, 0.15), (0.95, 0.75, 0.1),
                    (0.85, 0.45, 0.1)])
    kind = int(rng.integers(0, 3))      # sedan, police, taxi
    if kind == 1:
        col = (0.05, 0.05, 0.06)
    b.box((0.068, 0.027, 0.012), loc=(0, 0, 0.009), mat="paint", bevel=0.004)
    b.box((0.032, 0.024, 0.01), loc=(-0.004, 0, 0.019), mat="paint", bevel=0.004)
    b.box((0.03, 0.0245, 0.007), loc=(-0.004, 0, 0.0195), mat="glass", bevel=0.002)
    if kind == 1:
        b.box((0.068, 0.0275, 0.005), loc=(0, 0, 0.006), mat="white", bevel=0.002)
        b.box((0.006, 0.014, 0.003), loc=(-0.004, 0, 0.025), mat="beacon")
    if kind == 2:
        b.box((0.008, 0.008, 0.004), loc=(-0.004, 0, 0.026), mat="beacon")
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.0055, 0.004, loc=(sx * 0.022, sy * 0.0125, 0.0045), rot=(PI / 2, 0, 0), mat="tire", seg=14)
            b.cyl(0.003, 0.0042, loc=(sx * 0.022, sy * 0.0125, 0.0045), rot=(PI / 2, 0, 0), mat="hub", seg=10)
    out = {"paint": MET(col, 0.25), "glass": T((0.3, 0.35, 0.4), 0.1), "white": MET((0.95, 0.95, 0.95), 0.25),
           "beacon": P((0.95, 0.15, 0.1) if kind == 1 else (1.0, 0.8, 0.2), 0.3), "tire": RUB(), "hub": CHROME()}
    if rng.random() < 0.35:
        b.box((0.078, 0.034, 0.039), loc=(0.0, 0.055, 0.0195), mat="box")
        b.plane(0.078, 0.039, loc=(0.0, 0.055 - 0.0171, 0.0195), rot=(PI / 2, 0, 0), mat="boxp", cuts=2)
        b.plane(0.078, 0.034, loc=(0.0, 0.055, 0.0392), mat="boxp", cuts=2)
        out["box"] = P((0.85, 0.08, 0.12), 0.7)
        out["boxp"] = PR(_tomiko_box(rng, "tmk"), 0.7)
    return out


def _cart_label(rng, name):
    sky = _ch(rng, [(0.3, 0.55, 0.95), (0.05, 0.05, 0.15), (0.95, 0.6, 0.3), (0.2, 0.6, 0.3)])
    c = _cv(256, 192, sky)
    c.rect(0, 0, 1, 0.25, (0.45, 0.3, 0.15))
    for k in range(10):
        c.rect(k * 0.1, 0.22, k * 0.1 + 0.08, 0.28, (0.8, 0.45, 0.2))
    _hero_figure(c, rng, float(rng.uniform(0.3, 0.7)), 0.45, 0.13)
    for _ in range(3):
        c.poly(_star(float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.55, 0.75)), 0.04, asp=256 / 192), (1, 0.9, 0.3))
    c.rect(0, 0.8, 1, 1, (0.97, 0.97, 0.95))
    _ct(c, _ch(rng, ["SUPER PLUMBERS", "ROCK BOY 2", "DRAGON QUESTO", "SPACE PIPE", "NINJA KUN"]), 0.5, 0.96, 0.12, (0.85, 0.1, 0.12))
    return c.image(name)


@obj("famicom_cart", eras=(0, 1), mass=0.045, **RARE)
def famicom_cart(b, rng, pal):
    """The short, wide Japanese cartridge in a candy color, grip ridges on the sides, label on the front."""
    W, H, D = 0.107, 0.068, 0.016
    col = _ch(rng, [(0.95, 0.85, 0.2), (0.85, 0.15, 0.15), (0.05, 0.05, 0.06), (0.95, 0.95, 0.93), (0.2, 0.55, 0.85),
                    (0.95, 0.5, 0.65)])
    b.box((W, H, D), mat="shell", bevel=0.003)
    b.plane(W * 0.72, H * 0.8, loc=(0, 0.002, D / 2 + 0.0003), mat="label", cuts=2)
    for sx in (-1, 1):
        for k in range(6):
            b.box((0.002, 0.004, D * 0.8), loc=(sx * (W / 2 - 0.004), 0.025 - k * 0.006, 0.0002), mat="shell")
    b.box((W * 0.8, 0.006, D * 0.55), loc=(0, -H / 2 - 0.002, 0), mat="pcb")
    return {"shell": P(col, 0.35), "label": PR(_cart_label(rng, "fcart"), 0.4),
            "pcb": P((0.1, 0.4, 0.15), 0.4)}


def _umaibo_print(rng, name):
    flav, col = _ch(rng, [("CORN POTAGE", (1.0, 0.85, 0.2)), ("MENTAI", (0.95, 0.4, 0.5)), ("CHEESE", (1.0, 0.7, 0.15)),
                          ("TERIYAKI", (0.55, 0.3, 0.15)), ("SALAMI", (0.85, 0.15, 0.15)), ("TAKOYAKI", (0.35, 0.55, 0.9))])
    c = _cv(512, 128, (0.95, 0.95, 0.95, ))
    c.rect(0, 0, 1, 1, (*col, 1))
    c.rect(0.0, 0.3, 1.0, 0.7, (0.97, 0.97, 0.95))
    _ct(c, "OISHIBO", 0.3, 0.66, 0.3, (0.85, 0.1, 0.12), maxw=0.4)
    _ct(c, flav, 0.72, 0.62, 0.22, INK, maxw=0.4)
    c.circle(0.9, 0.85, 0.12, (0.97, 0.97, 0.95))
    c.text("10", 0.875, 0.92, 0.14, (0.85, 0.1, 0.12), bold=True)
    return c.image(name)


@obj("umaibo", eras=(0, 1, 2, 3, 4), mass=0.006, **RARE)
def umaibo(b, rng, pal):
    """The ten-yen corn puff stick, in a printed wrapper, or bitten open with the hollow puff showing."""
    L, R = 0.115, 0.0125
    bitten = rng.random() < 0.3
    b.cyl(R, L * (0.85 if bitten else 1.0), loc=(-L * 0.075 if bitten else 0, 0, 0), rot=(0, PI / 2, 0), mat="wrap", seg=20)
    if not bitten:
        for s in (-1, 1):
            b.box((0.008, R * 2.2, 0.0016), loc=(s * (L / 2 + 0.003), 0, 0), mat="crimp")
    else:
        b.cyl(R * 0.95, 0.025, loc=(L / 2 - 0.004, 0, 0), rot=(0, PI / 2, 0), mat="puff", seg=9)
        b.cyl(R * 0.35, 0.026, loc=(L / 2 - 0.004, 0, 0), rot=(0, PI / 2, 0), mat="hole", seg=12)
    b.plane(L * 0.8, 0.02, loc=(0, 0, R + 0.0003), mat="label", cuts=2)
    img = _umaibo_print(rng, "umai")
    return {"wrap": PR(img, 0.25), "crimp": P(tuple(img.pixels[0:3]), 0.3), "label": PR(img, 0.25),
            "puff": ("crust", {}), "hole": P((0.45, 0.3, 0.12), 0.9)}


def _calpis_print(rng, name):
    c = _cv(512, 256, (0.97, 0.97, 0.98))
    for r in range(8):
        for k in range(22):
            c.circle((k + 0.5 * (r % 2)) / 22, (r + 0.5) / 8, 0.035, (0.2, 0.4, 0.85))
    c.rect(0.6, 0.35, 0.9, 0.7, (0.97, 0.97, 0.98))
    _ct(c, "KALPISU", 0.75, 0.65, 0.12, (0.15, 0.3, 0.75), maxw=0.28)
    _ct(c, "WATER 500ML", 0.75, 0.48, 0.06, (0.15, 0.3, 0.75), maxw=0.25)
    return c.image(name)


@obj("calpis_bottle", eras=(1, 2, 3, 4), mass=0.03, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def calpis_bottle(b, rng, pal):
    """The milky soft-drink bottle, white with blue polka dots. Tastes like a yogurt that went to heaven."""
    prof = [(0.0, -0.1), (0.028, -0.1), (0.032, -0.09), (0.032, 0.03), (0.022, 0.07), (0.013, 0.085), (0.013, 0.095),
            (0.0, 0.095)]
    b.lathe(prof, mat="pet", seg=28)
    b.cyl(0.0325, 0.07, loc=(0, 0, -0.045), mat="label", seg=28, cap=False)
    b.cyl(0.0145, 0.016, loc=(0, 0, 0.102), mat="cap", seg=20)
    return {"pet": P((0.96, 0.96, 0.95), 0.15, coat=0.8), "label": PR(_calpis_print(rng, "clp"), 0.3),
            "cap": P((0.2, 0.4, 0.85), 0.35)}


@obj("kinkeshi", eras=(0, 1), mass=0.004, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def kinkeshi(b, rng, pal):
    """A one-color rubber muscle-man eraser: masked, flexing, and useless for erasing."""
    col = _ch(rng, [(0.95, 0.6, 0.7), (0.95, 0.75, 0.4), (0.55, 0.7, 0.95), (0.7, 0.9, 0.6), (0.95, 0.95, 0.85),
                    (0.8, 0.65, 0.95)])
    b.sphere(0.008, loc=(0, 0, 0.022), scale=(1.3, 0.8, 1.0), mat="r", seg=12)
    b.sphere(0.006, loc=(0, 0, 0.012), scale=(1.0, 0.75, 0.9), mat="r", seg=12)
    b.sphere(0.0055, loc=(0, -0.001, 0.034), mat="r", seg=12)
    b.extrude([(-0.002, 0), (0.002, 0), (0, 0.006)], 0.0015, loc=(0, -0.002, 0.039), rot=(PI / 2, 0, 0), mat="r")
    for sx in (-1, 1):
        b.tube([(sx * 0.009, 0, 0.025), (sx * 0.015, -0.002, 0.026), (sx * 0.016, -0.003, 0.034)], 0.0028, mat="r", seg=8)
        b.sphere(0.0032, loc=(sx * 0.016, -0.003, 0.035), mat="r", seg=8)
        b.tube([(sx * 0.004, 0, 0.008), (sx * 0.006, -0.001, 0.003), (sx * 0.007, 0, -0.004)], 0.003, mat="r", seg=8)
        b.box((0.006, 0.008, 0.003), loc=(sx * 0.007, -0.001, -0.0055), mat="r", bevel=0.001)
    return {"r": ("rubber", {"color": col})}


def _knob_print(rng, name):
    c = _cv(256, 256, (0.95, 0.95, 0.93))
    c.rect(0.06, 0.78, 0.94, 0.94, (0.85, 0.1, 0.12))
    _ct(c, "100 YEN", 0.5, 0.92, 0.12, (1, 1, 1))
    c.circle(0.5, 0.42, 0.32, (0.2, 0.2, 0.22), ring=0.02)
    for k in range(8):
        a = 2 * PI * k / 8
        c.line([(0.5 + 0.34 * math.cos(a), 0.42 + 0.34 * math.sin(a)), (0.5 + 0.4 * math.cos(a), 0.42 + 0.4 * math.sin(a))],
               0.015, (0.2, 0.2, 0.22))
    c.text("TURN", 0.05, 0.1, 0.06, INK)
    return c.image(name)


@obj("gacha_knob", eras=(0, 1, 2, 3, 4), mass=0.35, **SPECIAL)
def gacha_knob(b, rng, pal):
    """The front plate off a capsule machine: the coin slot and the crank you turned until it clicked."""
    W, H = 0.1, 0.12
    b.box((W, H, 0.006), mat="plate", bevel=0.002)
    b.plane(W * 0.96, H * 0.96, loc=(0, 0, 0.0032), mat="face", cuts=2)
    b.cyl(0.032, 0.012, loc=(0, -0.01, 0.009), mat="metal", seg=32)
    b.box((0.06, 0.012, 0.014), loc=(0, -0.01, 0.022), mat="handle", bevel=0.004)
    b.box((0.012, 0.003, 0.004), loc=(0.0, 0.045, 0.004), mat="slot")
    return {"plate": MET((0.75, 0.75, 0.77), 0.3), "face": PR(_knob_print(rng, "knob"), 0.4), "metal": CHROME(),
            "handle": P(_ch(rng, [(0.85, 0.1, 0.12), (0.2, 0.4, 0.85), (0.95, 0.6, 0.1)]), 0.3), "slot": P(BLACK, 0.5)}


def _disc(b, r, z, mat, n=36, d=0.0002):
    """A round printed face (the print fills the circle, nothing sticks out past the edge)."""
    pts = [(r * math.cos(2 * PI * i / n), r * math.sin(2 * PI * i / n)) for i in range(n)]
    b.extrude(pts, d, loc=(0, 0, z), mat=mat)


# ================================================================================================
# PURIKURA: the photo-sticker booth, the phone with more charms than phone, Tokyo 1995-2008
# ================================================================================================

def _puri_print(rng, name):
    c = _cv(256, 384, (0.98, 0.9, 0.95))
    asp = 256 / 384
    for _ in range(80):
        c.circle(float(rng.uniform(0, 1)), float(rng.uniform(0, 1)), 0.004, _ch(rng, [(1, 0.8, 0.95), (0.8, 0.9, 1), (1, 1, 0.8)]))
    frames = [(1.0, 0.6, 0.8), (0.6, 0.85, 1.0), (1.0, 0.9, 0.4), (0.7, 1.0, 0.7), (0.85, 0.7, 1.0)]
    bgs = [(1.0, 0.85, 0.92), (0.85, 0.95, 1.0), (1.0, 0.97, 0.8), (0.9, 0.85, 1.0)]
    for r in range(4):
        for k in range(4):
            x0, y0 = 0.04 + k * 0.24, 0.04 + r * 0.24
            x1, y1 = x0 + 0.22, y0 + 0.22
            c.rect(x0, y0, x1, y1, _ch(rng, frames))
            c.rect(x0 + 0.015, y0 + 0.015 / asp * 0.67, x1 - 0.015, y1 - 0.015 / asp * 0.67, _ch(rng, bgs))
            heads = int(rng.integers(1, 3))
            for h in range(heads):                                        # two friends, nobody in particular
                cx = (x0 + x1) / 2 + (h - (heads - 1) / 2) * 0.08
                hair = _ch(rng, [(0.1, 0.06, 0.05), (0.55, 0.3, 0.12), (0.85, 0.6, 0.3), (0.95, 0.85, 0.5)])
                skin = _ch(rng, [(1.0, 0.85, 0.75), (0.95, 0.75, 0.6), (0.7, 0.5, 0.35)])
                c.circle(cx, y0 + 0.12, 0.055, hair)
                c.rect(cx - 0.05 * asp * 1.3, y0 + 0.03, cx + 0.05 * asp * 1.3, y0 + 0.12, hair)
                c.circle(cx, y0 + 0.11, 0.042, skin)
                c.rect(cx - 0.03, y0 + 0.015, cx + 0.03, y0 + 0.06, _ch(rng, frames))
                for sx in (-1, 1):
                    c.circle(cx + sx * 0.015, y0 + 0.115, 0.007, INK)
            if rng.random() < 0.6:                                         # the peace sign
                px = x1 - 0.04
                c.line([(px, y0 + 0.06), (px - 0.015, y0 + 0.12)], 0.012, (1.0, 0.85, 0.75))
                c.line([(px, y0 + 0.06), (px + 0.012, y0 + 0.12)], 0.012, (1.0, 0.85, 0.75))
            c.poly(_star(x0 + 0.04, y1 - 0.03, 0.025, asp=asp), (1.0, 0.95, 0.3))
            if rng.random() < 0.5:
                c.poly(_heart(x1 - 0.04, y1 - 0.04, 0.02, asp=asp), (1.0, 0.3, 0.55))
            if rng.random() < 0.4:
                c.text(_ch(rng, ["LOVE", "BFF", "2002", "KAWAII", "4EVER", "MAX!", "99"]), x0 + 0.03, y1 - 0.06, 0.02,
                       _ch(rng, [(1.0, 0.2, 0.5), (0.2, 0.3, 0.9), (1, 1, 1)]), bold=True)
    c.noise(rng, 0.012)
    return c.image(name)


@obj("purikura_sheet", eras=(2, 3), mass=0.002, **SPECIAL)
def purikura_sheet(b, rng, pal):
    """A sheet of photo-booth stickers, half of them already peeled off and stuck in somebody's notebook."""
    rot = (0, 0, float(rng.normal(0, 0.3)))
    b.box((0.09, 0.13, 0.0005), rot=rot, mat="back")
    b.plane(0.09, 0.13, loc=(0, 0, 0.0003), rot=rot, mat="front", cuts=3)
    return {"back": P((0.95, 0.95, 0.95), 0.5), "front": PR(_puri_print(rng, "puri"), 0.2, coat=0.6)}


def _charms(b, rng, start, n=4, specs=None):
    """A bunch of phone straps: cords, beads, a bell, a star, a little fluff ball."""
    specs = specs if specs is not None else {}
    cols = [(1.0, 0.45, 0.7), (0.4, 0.75, 1.0), (1.0, 0.85, 0.2), (0.6, 0.95, 0.6), (0.85, 0.6, 1.0), (1.0, 1.0, 1.0)]
    x0, y0, z0 = start
    for k in range(n):
        a = -PI / 2 + float(rng.uniform(-1.0, 1.0))
        L = float(rng.uniform(0.04, 0.07))
        ex, ey = x0 + L * math.cos(a), y0 + L * math.sin(a)
        b.tube([(x0, y0, z0), ((x0 + ex) / 2 + 0.004, (y0 + ey) / 2, z0 + 0.002), (ex, ey, z0)], 0.0007, mat="cord", seg=5)
        m = f"ch{k}"
        specs[m] = P(_ch(rng, cols), 0.3, coat=0.5)
        kind = int(rng.integers(0, 5))
        for j in range(int(rng.integers(2, 5))):                           # beads on the cord
            t = 0.2 + 0.15 * j
            b.sphere(0.0022, loc=(x0 + (ex - x0) * t, y0 + (ey - y0) * t, z0 + 0.001), mat=m, seg=8)
        if kind == 0:
            b.sphere(0.006, loc=(ex, ey, z0), mat="bell", seg=12)
            b.box((0.007, 0.001, 0.001), loc=(ex, ey - 0.002, z0 - 0.004), mat="cord")
        elif kind == 1:
            pts = _star(0, 0, 0.01, 5, 0.45)
            b.extrude(pts, 0.004, loc=(ex, ey, z0), mat=m, bevel=0.001)
        elif kind == 2:
            b.sphere(0.009, loc=(ex, ey, z0), mat="fluff", seg=12)
            specs["fluff"] = ("fabric", {"color": _ch(rng, cols)})
        elif kind == 3:
            b.extrude([(px, py) for px, py in _heart(0, 0, 0.009)], 0.004, loc=(ex, ey, z0), mat="gem", bevel=0.001)
        else:                                                              # a tiny bear-ish head
            b.sphere(0.007, loc=(ex, ey, z0), mat=m, seg=12)
            for sx in (-1, 1):
                b.sphere(0.003, loc=(ex + sx * 0.0055, ey + 0.005, z0), mat=m, seg=8)
    specs.update({"cord": P(_ch(rng, cols), 0.5), "bell": MET((0.95, 0.8, 0.35), 0.2), "gem": T((1.0, 0.3, 0.6), 0.05)})
    specs.setdefault("fluff", ("fabric", {"color": (1.0, 0.75, 0.85)}))
    return specs


@obj("charm_phone", eras=(2, 3), mass=0.14, **SPECIAL)
def charm_phone(b, rng, pal):
    """A clamshell phone with more charm than phone: rhinestones on the lid, straps by the fistful."""
    col = _ch(rng, [(1.0, 0.7, 0.82), (0.95, 0.95, 0.97), (0.78, 0.8, 0.85), (0.6, 0.8, 1.0), (0.95, 0.4, 0.55)])
    W, L = 0.05, 0.1
    b.box((W, L, 0.011), loc=(0, 0, -0.006), mat="body", bevel=0.004)
    b.box((W, L, 0.01), loc=(0, 0, 0.0055), mat="body", bevel=0.004)
    b.cyl(0.006, W * 0.94, loc=(0, L / 2 - 0.004, 0.0), rot=(0, PI / 2, 0), mat="hinge", seg=16)
    b.box((0.026, 0.02, 0.0012), loc=(0, 0.022, 0.0108), mat="sub", bevel=0.0006)
    b.cyl(0.005, 0.002, loc=(0, 0.042, 0.0108), mat="hinge", seg=16)
    b.cyl(0.003, 0.0024, loc=(0, 0.042, 0.0112), mat="lens", seg=12)
    for px, py in _heart(0, -0.018, 0.016):                                # rhinestones in a heart
        b.sphere(0.0016, loc=(px, py, 0.0108), scale=(1, 1, 0.6), mat="stone", seg=8)
    for _ in range(int(rng.integers(3, 7))):
        x, y = float(rng.uniform(-0.018, 0.018)), float(rng.uniform(-0.04, 0.04))
        b.cyl(0.004, 0.0006, loc=(x, y, 0.0106), mat=f"dec{_ % 2}", seg=12)
    specs = {"body": P(col, 0.25, coat=0.8), "hinge": MET((0.75, 0.75, 0.78), 0.25), "sub": ("screen", {"image": tex.lcd(rng, "sublcd", "12:34")}),
             "lens": T((0.1, 0.1, 0.12), 0.05), "stone": T((0.95, 0.95, 1.0), 0.02),
             "dec0": P((1.0, 0.3, 0.6), 0.3), "dec1": P((1.0, 0.9, 0.3), 0.3)}
    return _charms(b, rng, (-W / 2 + 0.004, L / 2 + 0.004, 0.0), int(rng.integers(3, 6)), specs)


@obj("keitai_strap", eras=(2, 3), mass=0.01, **SPECIAL)
def keitai_strap(b, rng, pal):
    """A clump of phone straps that outlived the phone."""
    b.torus(0.004, 0.0009, loc=(0, 0.004, 0), mat="cord", seg=12, rseg=5)
    return _charms(b, rng, (0, 0, 0), int(rng.integers(2, 5)))


def _pocko_print(rng, name, flav):
    col, acc = flav
    c = _cv(192, 384, col)
    for k in range(9):                                                       # the sticks, drawn on the diagonal
        x = -0.4 + k * 0.17
        c.line([(x, 0.08), (x + 0.6, 0.62)], 0.035, (0.92, 0.75, 0.45))
        c.line([(x + 0.12, 0.19), (x + 0.6, 0.62)], 0.045, acc)
    c.rect(0, 0.65, 1, 1, col)
    _ct(c, "POCKO", 0.5, 0.92, 0.11, (0.98, 0.98, 0.98), maxw=0.9)
    c.rect(0.15, 0.71, 0.85, 0.75, (0.98, 0.98, 0.98))
    _ct(c, "CHOCOLATE", 0.5, 0.7, 0.035, col, maxw=0.6)
    c.text("2 BAGS", 0.06, 0.06, 0.03, (1, 1, 1))
    return c.image(name)


POCKO = [((0.85, 0.08, 0.12), (0.35, 0.17, 0.08)), ((0.95, 0.55, 0.7), (0.98, 0.6, 0.7)), ((0.2, 0.15, 0.12), (0.2, 0.1, 0.05)),
         ((0.3, 0.6, 0.3), (0.55, 0.75, 0.4))]


@obj("stick_biscuit_box", eras=(0, 1, 2, 3, 4), mass=0.06, **RARE)
def stick_biscuit_box(b, rng, pal):
    """The chocolate-dipped biscuit sticks, red box, one end torn open with a few sticks sliding out."""
    flav = _ch(rng, POCKO)
    W, L, D = 0.072, 0.148, 0.014
    b.box((W, L, D), mat="box", bevel=0.001)
    b.plane(W, L, loc=(0, 0, D / 2 + 0.0003), mat="front", cuts=3)
    out = {"box": P(flav[0], 0.4), "front": PR(_pocko_print(rng, "pocko", flav), 0.35)}
    if rng.random() < 0.55:
        b.box((W, 0.018, 0.0008), loc=(0, L / 2 + 0.008, D / 2 + 0.004), rot=(0.6, 0, 0), mat="box")
        for k in range(int(rng.integers(2, 6))):
            x = -0.025 + k * 0.012 + float(rng.normal(0, 0.003))
            dy = float(rng.uniform(0.02, 0.07))
            a = float(rng.normal(0, 0.15))
            b.cyl(0.0022, 0.13, loc=(x, L / 2 - 0.06 + dy, 0.0), rot=(PI / 2, 0, a), mat="biscuit", seg=8)
            b.cyl(0.0027, 0.1, loc=(x + 0.015 * math.sin(a), L / 2 - 0.075 + dy, 0.0), rot=(PI / 2, 0, a), mat="dip", seg=8)
        out.update({"biscuit": P((0.9, 0.72, 0.45), 0.7), "dip": P(flav[1], 0.4)})
    return out


def _chew_print(rng, name, flav):
    fname, col = flav
    c = _cv(512, 160, (0.97, 0.97, 0.97))
    c.rect(0, 0, 1, 0.35, col)
    _ct(c, "HAI-CHOO", 0.33, 0.9, 0.36, (0.15, 0.2, 0.6), maxw=0.55)
    c.text(fname, 0.65, 0.88, 0.16, col, bold=True)
    for k in range(3):
        c.circle(0.7 + k * 0.1, 0.5, 0.16, col)
        c.circle(0.68 + k * 0.1, 0.56, 0.05, (1, 1, 1))
    c.text("12 PIECES", 0.04, 0.25, 0.12, (1, 1, 1))
    return c.image(name)


@obj("fruit_chew", eras=(1, 2, 3, 4), mass=0.05, **RARE)
def fruit_chew(b, rng, pal):
    """The soft fruit chew in its stick pack, or a few loose pieces in their little wrappers."""
    flav = _ch(rng, [("STRAWBERRY", (0.95, 0.3, 0.45)), ("GRAPE", (0.55, 0.25, 0.65)), ("GREEN APPLE", (0.45, 0.75, 0.2)),
                     ("MANGO", (1.0, 0.65, 0.1))])
    img = _chew_print(rng, "chew", flav)
    if rng.random() < 0.6:
        _flow_bar(b, 0.095, 0.026, 0.017, "top", "wrap", crimp=0.006)
        return {"wrap": P((0.97, 0.97, 0.97), 0.3, coat=0.4), "top": PR(img, 0.3)}
    for k in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.014, 2))
        rot = (0, 0, float(rng.uniform(0, PI)))
        b.box((0.023, 0.018, 0.007), loc=(x, y, 0), rot=rot, mat="wrap", bevel=0.002)
        b.plane(0.022, 0.017, loc=(x, y, 0.0038), rot=rot, mat="top", cuts=2)
    return {"wrap": P((0.97, 0.97, 0.97), 0.3, coat=0.4), "top": PR(img, 0.3)}


@obj("loose_socks", eras=(2, 3), mass=0.06, **SPECIAL)
def loose_socks(b, rng, pal):
    """One loose sock, bunched down the shin the way they were meant to be, held up with sock glue."""
    rings = []
    n = 18
    L = 0.17
    for j in range(64):
        u = j / 63
        x = -L / 2 + L * u
        r = 0.024 + 0.008 * math.sin(u * 22) * (1 - u * 0.3) + 0.008 * u
        bend = 0.012 * math.sin(u * PI)
        rings.append([(x, r * math.cos(2 * PI * i / n), 0.6 * r * math.sin(2 * PI * i / n) + bend) for i in range(n)])
    b.loft(rings, mat="sock")
    b.sphere(0.026, loc=(-L / 2 - 0.005, 0.0, -0.002), scale=(1.5, 1, 0.55), mat="sock", seg=14)
    return {"sock": ("fabric", {"color": (0.97, 0.97, 0.95)})}


@obj("magic_wand", eras=(1, 2, 3), mass=0.06, **SPECIAL)
def magic_wand(b, rng, pal):
    """A toy magical-girl wand of our own: star head, heart jewel, little wings, ribbons. The light-up button stopped."""
    col = _ch(rng, [(1.0, 0.55, 0.75), (0.65, 0.55, 1.0), (0.5, 0.85, 1.0), (1.0, 0.75, 0.4)])
    b.cyl(0.0055, 0.16, loc=(-0.04, 0, 0), rot=(0, PI / 2, 0), mat="stick", seg=14)
    for x in (-0.11, -0.07, 0.03):
        b.torus(0.006, 0.0018, loc=(x, 0, 0), rot=(0, PI / 2, 0), mat="gold", seg=14, rseg=6)
    b.sphere(0.009, loc=(-0.125, 0, 0), mat="gold", seg=12)
    b.extrude(_star(0, 0, 0.034, 5, 0.5, rot=-PI / 2), 0.01, loc=(0.065, 0, 0), mat="gold", bevel=0.002)
    b.extrude(_star(0, 0, 0.028, 5, 0.5, rot=-PI / 2), 0.0115, loc=(0.065, 0, 0), mat="head", bevel=0.002)
    b.extrude(_heart(0, 0, 0.013), 0.007, loc=(0.065, 0, 0.007), mat="gem", bevel=0.002)
    for sy in (-1, 1):
        for k, (L, a) in enumerate(((0.03, 0.5), (0.024, 0.95), (0.017, 1.35))):       # three feathers a side
            fx = [(L / 2 * math.cos(t), 0.0045 * math.sin(t)) for t in np.linspace(0, 2 * PI, 14, endpoint=False)]
            b.extrude(fx, 0.002, loc=(0.03 + L / 2 * math.cos(a) * 0.9, sy * (0.012 + L / 2 * math.sin(a)), -0.001 - k * 0.0005),
                      rot=(0, 0, sy * a), mat="wing")
        b.tube([(0.038, sy * 0.004, -0.004), (0.02, sy * 0.025, -0.006), (-0.01, sy * 0.02, -0.007), (-0.03, sy * 0.035, -0.006)],
               0.0024, mat="ribbon", seg=6)
    b.cyl(0.004, 0.003, loc=(-0.06, 0, 0.0055), mat="button", seg=12)
    return {"stick": P(col, 0.25, coat=0.6), "gold": MET((0.95, 0.8, 0.35), 0.2), "head": P(col, 0.25, coat=0.6),
            "gem": T((1.0, 0.25, 0.55), 0.03), "wing": P((0.97, 0.97, 1.0), 0.3, coat=0.5),
            "ribbon": P((1.0, 0.45, 0.7), 0.4), "button": P((1.0, 0.9, 0.3), 0.3)}


def _gbp_screen(rng, name):
    from .games import _pixel_scene
    return _pixel_scene(rng, name, palette=[(0.78, 0.8, 0.74), (0.55, 0.57, 0.52), (0.3, 0.32, 0.3), (0.08, 0.08, 0.09)])


def _gbp_face(rng, name, body):
    c = _cv(256, 420, body)
    c.rect(0.08, 0.5, 0.92, 0.95, (0.32, 0.33, 0.38))
    c.circle(0.15, 0.82, 0.012, (0.3, 0.05, 0.05))
    c.text("BATTERY", 0.11, 0.78, 0.012, (0.75, 0.75, 0.8))
    _ct(c, "GAME KID POCKET", 0.42, 0.47, 0.03, (0.2, 0.2, 0.35), maxw=0.7)
    for k in range(6):                                                    # the speaker slots
        c.line([(0.66 + k * 0.04, 0.06), (0.76 + k * 0.04, 0.16)], 0.012, (0.25, 0.25, 0.28))
    c.text("SELECT  START", 0.3, 0.18, 0.018, (0.3, 0.3, 0.4))
    return c.image(name)


@obj("gb_pocket", eras=(1, 2), mass=0.125, **RARE)
def gb_pocket(b, rng, pal):
    """The slimmed-down 1996 handheld: two AAA batteries, a black-and-white screen you could finally read."""
    body = _ch(rng, [(0.75, 0.76, 0.78), (0.85, 0.72, 0.35), (0.8, 0.12, 0.15), (0.95, 0.85, 0.2), (0.12, 0.12, 0.13),
                     (0.95, 0.6, 0.7), (0.3, 0.6, 0.35)])
    W, L, D = 0.0776, 0.1276, 0.0253
    clear = rng.random() < 0.15
    b.box((W, L, D), mat="body", bevel=0.005)
    b.plane(W * 0.98, L * 0.98, loc=(0, 0, D / 2 + 0.0002), mat="face", cuts=3)
    b.plane(0.042, 0.038, loc=(0.0, 0.03, D / 2 + 0.0005), mat="lcd", cuts=2)
    b.extrude([(-0.012, -0.004), (-0.004, -0.004), (-0.004, -0.012), (0.004, -0.012), (0.004, -0.004), (0.012, -0.004),
               (0.012, 0.004), (0.004, 0.004), (0.004, 0.012), (-0.004, 0.012), (-0.004, 0.004), (-0.012, 0.004)], 0.004,
              loc=(-0.02, -0.025, D / 2 + 0.0015), mat="btn", bevel=0.0008)
    for k, (x, y) in enumerate(((0.026, -0.018), (0.012, -0.028))):
        b.cyl(0.0048, 0.004, loc=(x, y, D / 2 + 0.0012), mat="btn", seg=16)
    for x in (-0.008, 0.008):
        b.box((0.008, 0.0025, 0.002), loc=(x, -0.046, D / 2 + 0.0008), rot=(0, 0, 0.5), mat="pill", bevel=0.0009)
    return {"body": T(body, 0.15) if clear else P(body, 0.3, coat=0.3), "face": PR(_gbp_face(rng, "gbpf", body), 0.3),
            "lcd": ("screen", {"image": _gbp_screen(rng, "gbps"), "glow": 0.0}), "btn": P((0.15, 0.15, 0.17), 0.35),
            "pill": RUB((0.3, 0.3, 0.32))}


# ================================================================================================
# TAZOS: the plastic discs in the chip bags, 1995-2000, Spain to Mexico to Buenos Aires
# ================================================================================================

def _tazo_front(rng, name):
    bg = _ch(rng, [(0.95, 0.85, 0.15), (0.2, 0.5, 0.95), (0.95, 0.3, 0.2), (0.3, 0.8, 0.4), (0.6, 0.3, 0.85), (0.1, 0.1, 0.12)])
    c = _cv(256, 256, bg)
    kind = int(rng.integers(0, 3))
    if kind == 0:
        from .games import _critter
        _critter(c, rng, 0.5, 0.45, 0.2, _ch(rng, [(0.95, 0.6, 0.2), (0.4, 0.75, 0.95), (0.9, 0.4, 0.6), (0.5, 0.85, 0.4)]))
    elif kind == 1:                                                       # a spiral, for the trick ones
        pts = [(0.5 + 0.02 * t * math.cos(t), 0.5 + 0.02 * t * math.sin(t)) for t in np.linspace(0, 22, 160)]
        c.line(pts, 0.04, (1, 1, 1))
    else:
        c.poly(_star(0.5, 0.5, 0.4, 8, 0.55), (1.0, 0.95, 0.4))
        _ct(c, _ch(rng, ["MEGA", "SUPER", "X-TREME", "TURBO"]), 0.5, 0.58, 0.14, (0.85, 0.1, 0.12), maxw=0.6)
    c.circle(0.5, 0.5, 0.47, (0.98, 0.98, 0.98), ring=0.035)
    _ct(c, str(int(rng.integers(1, 151))), 0.5, 0.17, 0.08, INK, maxw=0.3)
    return c.image(name)


def _tazo_back(rng, name):
    c = _cv(256, 256, (0.95, 0.95, 0.93))
    c.circle(0.5, 0.5, 0.42, (0.85, 0.1, 0.12))
    _ct(c, "TAZAS", 0.5, 0.62, 0.16, (1.0, 0.85, 0.1), maxw=0.6)
    _ct(c, "COLECCIONALOS!", 0.5, 0.4, 0.06, (1, 1, 1), maxw=0.6)
    _ct(c, f"{int(rng.integers(1, 151))}/150", 0.5, 0.25, 0.06, (1, 1, 1), maxw=0.4)
    return c.image(name)


@obj("tazo", eras=(1, 2), mass=0.002, **RARE)
def tazo(b, rng, pal):
    """One disc out of a chip bag. Some were shiny. You traded three for a shiny."""
    n = int(rng.integers(1, 4))
    shiny = rng.random() < 0.25
    for k in range(n):
        x, y = (float(v) for v in rng.normal(0, 0.012 * (n > 1), 2))
        rot = (float(rng.normal(0, 0.15)), 0, 0)
        z = k * 0.0018
        b.cyl(0.02, 0.0014, loc=(x, y, z), rot=rot, mat="edge", seg=36)
        b.extrude([(0.0197 * math.cos(2 * PI * i / 36), 0.0197 * math.sin(2 * PI * i / 36)) for i in range(36)], 0.0002,
                  loc=(x, y, z + 0.0008), rot=rot, mat=f"f{k}")
    specs = {"edge": P((0.95, 0.95, 0.93), 0.35)}
    for k in range(n):
        specs[f"f{k}"] = PR(_tazo_front(rng, f"tazo{k}"), 0.2 if shiny else 0.35, metal=0.7 if shiny else 0.0)
    return specs


def _crisp_print(rng, name, brand, col, chip):
    c = _cv(512, 320, col)
    c.circle(0.75, 0.9, 0.12, (1.0, 0.85, 0.1))
    c.rect(0.58, 0.58, 0.92, 0.76, (0.98, 0.97, 0.94))
    c.rect(0.59, 0.6, 0.91, 0.74, (0.1, 0.12, 0.35))
    _ct(c, brand, 0.75, 0.72, 0.12, (1.0, 0.85, 0.1), maxw=0.3)
    for _ in range(7):                                                        # the chips
        x, y = float(rng.uniform(0.58, 0.92)), float(rng.uniform(0.15, 0.45))
        c.circle(x, y, 0.06, chip)
        c.circle(x - 0.01, y + 0.015, 0.02, tuple(min(1, v + 0.1) for v in chip))
    c.poly(_star(0.88, 0.5, 0.11, 10, 0.75, asp=1.6), (1.0, 0.95, 0.2))         # the burst
    c.circle(0.88, 0.5, 0.06, (0.2, 0.5, 0.95))
    _ct(c, "TAZAS!", 0.88, 0.56, 0.035, (0.85, 0.1, 0.12), maxw=0.1)
    c.text("CON TAZAS GRATIS", 0.56, 0.1, 0.045, (1, 1, 1), bold=True)
    c.rect(0, 0, 0.5, 1, tuple(v * 0.85 for v in col))
    c.text("INGREDIENTES: PAPA, ACEITE, SAL", 0.03, 0.5, 0.03, (1, 1, 1))
    return c.image(name)


@obj("tazo_chip_bag", eras=(1, 2), mass=0.04, hero=(0, -1, 0), **RARE)
def tazo_chip_bag(b, rng, pal):
    """The bag you bought for the disc inside. The chips were a bonus."""
    brand, col = _ch(rng, [("CRISPITAS", (0.85, 0.1, 0.12)), ("PAPITAS", (0.95, 0.75, 0.1)), ("SABROSITAS", (0.2, 0.35, 0.85)),
                           ("CRUJIS", (0.15, 0.6, 0.3))])
    w, h = 0.15, 0.21
    _pillow(b, w, h, 0.055, "bag")
    img = _crisp_print(rng, "crisp", brand, col, (0.95, 0.8, 0.4))
    _crimps(b, w, h, "seal")
    return {"bag": PR(img, 0.2, metal=0.12), "seal": P(col, 0.25, metal=0.12)}


@obj("tazo_tube", eras=(1, 2), mass=0.06, **SPECIAL)
def tazo_tube(b, rng, pal):
    """The clear collector tube with the colored cap, packed with discs, rattling in a backpack."""
    L, R = 0.11, 0.0215
    b.cyl(R, L, rot=(0, PI / 2, 0), mat="tube", seg=28, cap=False)
    b.cyl(R - 0.0008, L, rot=(0, PI / 2, 0), mat="tube", seg=28, cap=False)
    for s in (-1, 1):
        b.cyl(R + 0.0015, 0.012, loc=(s * (L / 2 + 0.002), 0, 0), rot=(0, PI / 2, 0), mat="cap", seg=28)
    n = int(rng.integers(26, 40))
    cols = [(0.95, 0.85, 0.15), (0.2, 0.5, 0.95), (0.95, 0.3, 0.2), (0.3, 0.8, 0.4), (0.6, 0.3, 0.85), (0.92, 0.92, 0.9)]
    for k in range(n):
        b.cyl(0.0195, 0.0022, loc=(-L / 2 + 0.005 + k * 0.0025, 0, -0.0008), rot=(0, PI / 2 + float(rng.normal(0, 0.08)), 0),
              mat=f"d{k % 6}", seg=28)
    specs = {"tube": _clear(rng, 0.12), "cap": P(_ch(rng, [(0.85, 0.1, 0.12), (0.2, 0.4, 0.9), (1.0, 0.8, 0.1)]), 0.3)}
    for k in range(6):
        specs[f"d{k}"] = P(cols[(k + int(rng.integers(0, 6))) % 6], 0.35)
    return specs


@obj("puff_bag", eras=(1, 2, 3), mass=0.03, hero=(0, -1, 0), **RARE)
def puff_bag(b, rng, pal):
    """Cheese puffs: the orange bag, the orange dust, the orange fingers."""
    w, h = 0.12, 0.17
    _pillow(b, w, h, 0.045, "bag")
    img = _crisp_print(rng, "puff", _ch(rng, ["QUESITOS", "CHEESY POPS", "CHIZITOS"]), (1.0, 0.5, 0.05), (1.0, 0.6, 0.1))
    _crimps(b, w, h, "seal")
    for _ in range(int(rng.integers(2, 6))):
        x = float(rng.uniform(-0.05, 0.05))
        z = -h / 2 + float(rng.uniform(0.0, 0.02))
        a = float(rng.uniform(0, 6))
        b.tube([(x, -0.03, z), (x + 0.006 * math.cos(a), -0.04, z + 0.006), (x + 0.012 * math.cos(a), -0.045, z + 0.002)],
               0.0045, mat="puff", seg=8)
    return {"bag": PR(img, 0.2, metal=0.12), "seal": P((1.0, 0.5, 0.05), 0.25, metal=0.12),
            "puff": ("foam", {"color": (1.0, 0.55, 0.1)})}


def _board_print(rng, name):
    c = _cv(320, 448, (0.15, 0.3, 0.75))
    _ct(c, "TAZAS", 0.5, 0.97, 0.07, (1.0, 0.85, 0.1))
    _ct(c, "ALBUM COLECCIONADOR", 0.5, 0.89, 0.025, (1, 1, 1))
    asp = 320 / 448
    for r in range(4):
        for k in range(3):
            cx, cy = 0.2 + k * 0.3, 0.72 - r * 0.2
            c.circle(cx, cy, 0.085, (0.08, 0.15, 0.4))
            _ct(c, str(r * 3 + k + 1), cx, cy + 0.015, 0.025, (0.6, 0.7, 0.95), maxw=0.1)
    return c.image(name)


@obj("tazo_board", eras=(1, 2), mass=0.05, **SPECIAL)
def tazo_board(b, rng, pal):
    """The cardboard collector board with a round hole for every disc. It was never full."""
    W, H = 0.15, 0.21
    b.box((W, H, 0.003), mat="board")
    b.plane(W, H, loc=(0, 0, 0.0017), mat="face", cuts=2)
    specs = {"board": ("cardboard", {"color": (0.2, 0.3, 0.7)}), "face": PR(_board_print(rng, "tboard"), 0.6)}
    for r in range(4):
        for k in range(3):
            if rng.random() < 0.5:
                x, y = -W / 2 + (0.2 + k * 0.3) * W, -H / 2 + (0.72 - r * 0.2 + 0.0) * H
                m = f"t{(r + k) % 3}"
                b.extrude([(0.0195 * math.cos(2 * PI * i / 28), 0.0195 * math.sin(2 * PI * i / 28)) for i in range(28)], 0.0015,
                          loc=(x, y, 0.0022), mat=m)
    for k in range(3):
        specs[f"t{k}"] = PR(_tazo_front(rng, f"tb{k}"), 0.35)
    return specs


def _soda_label(rng, name, col, flav):
    c = _cv(512, 192, col)
    for cx in (0.25, 0.75):
        c.circle(cx, 0.5, 0.42, (0.98, 0.97, 0.94))
        c.circle(cx, 0.5, 0.36, col)
        c.circle(cx, 0.5, 0.42, (0.95, 0.75, 0.1), ring=0.04)
        _ct(c, "JARRONES", cx, 0.68, 0.16, (1, 1, 1), maxw=0.2)
        _ct(c, flav, cx, 0.42, 0.1, (1, 1, 1), maxw=0.18)
    for k in range(10):
        c.rect(k * 0.1, 0.0, k * 0.1 + 0.05, 0.06, col)
        c.rect(k * 0.1 + 0.05, 0.94, k * 0.1 + 0.1, 1.0, (0.98, 0.97, 0.94))
    return c.image(name)


@obj("glass_soda", eras=(0, 1, 2, 3, 4), mass=0.55, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def glass_soda(b, rng, pal):
    """The tall glass bottle of fruit soda, mandarin or tamarind or lime, with the paper-look label."""
    flav, col, juice = _ch(rng, [("MANDARINA", (1.0, 0.5, 0.05), (1.0, 0.5, 0.02)), ("TAMARINDO", (0.55, 0.3, 0.12), (0.5, 0.3, 0.1)),
                                 ("LIMA-LIMON", (0.3, 0.75, 0.2), (0.6, 0.9, 0.3)), ("TORONJA", (0.95, 0.4, 0.5), (1.0, 0.75, 0.6)),
                                 ("PINA", (1.0, 0.85, 0.1), (1.0, 0.9, 0.4))])
    prof = [(0.0, -0.115), (0.027, -0.115), (0.029, -0.105), (0.029, 0.02), (0.024, 0.055), (0.014, 0.085), (0.0125, 0.105),
            (0.014, 0.108), (0.0135, 0.113), (0.0, 0.113)]
    b.lathe(prof, mat="glass", seg=28)
    b.lathe([(0.0, -0.11), (0.026, -0.11), (0.026, 0.02), (0.021, 0.05), (0.0, 0.05)], mat="juice", seg=24)
    b.cyl(0.0295, 0.075, loc=(0, 0, -0.05), mat="label", seg=28, cap=False)
    b.cyl(0.0148, 0.007, loc=(0, 0, 0.115), mat="crown", seg=18)
    return {"glass": ("glass", {"color": (0.9, 0.95, 0.92), "rough": 0.03}), "juice": P(juice, 0.08, coat=1.0),
            "label": PR(_soda_label(rng, "jarr", col, flav), 0.35), "crown": MET(col, 0.3)}


# ================================================================================================
# SPAM GIFT SET: Chuseok in Korea, where the canned ham comes in a gift box with a handle
# ================================================================================================

SPAM_BLUE = (0.08, 0.18, 0.52)
SPAM_YEL = (1.0, 0.82, 0.05)


def _spam_print(rng, name, small=False):
    c = _cv(512, 256, SPAM_BLUE)
    c.rect(0, 0.0, 1, 0.12, SPAM_YEL)
    c.rect(0, 0.88, 1, 1, SPAM_YEL)
    c.poly([(0.08, 0.86), (0.92, 0.86), (0.86, 0.5), (0.14, 0.5)], SPAM_YEL)          # the yellow banner
    _ct(c, "SPLAM", 0.5, 0.84, 0.3, SPAM_BLUE, maxw=0.7)
    c.rect(0.28, 0.16, 0.72, 0.44, (0.97, 0.75, 0.68))                               # the slice on the plate
    c.rect(0.3, 0.18, 0.7, 0.42, (0.93, 0.55, 0.5))
    c.rect(0.31, 0.18, 0.69, 0.24, (0.85, 0.35, 0.25))                               # the fried edge
    c.text("CLASSIC", 0.04, 0.38, 0.06, (1, 1, 1), bold=True)
    c.text("200G" if small else "340G", 0.8, 0.38, 0.07, (1, 1, 1), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


def _spam_tin(b, loc, rot, s=1.0):
    """One rounded-rectangle tin standing up, label front and back, the pull-ring lid on top."""
    W, D, H = 0.09 * s, 0.05 * s, 0.07 * s
    x, y, z = loc
    rz = rot
    ca, sa = math.cos(rz), math.sin(rz)

    def at(dx, dy, dz):
        return (x + dx * ca - dy * sa, y + dx * sa + dy * ca, z + dz)
    b.box((W, D, H), loc=at(0, 0, 0), rot=(0, 0, rz), mat="tin", bevel=0.009 * s)
    for sy in (-1, 1):
        b.plane(W * 0.8, H * 0.86, loc=at(0, sy * (D / 2 + 0.0004), 0), rot=(PI / 2, 0, rz + (0 if sy < 0 else PI)),
                mat="label", cuts=2)
    b.box((W * 0.9, D * 0.82, 0.002), loc=at(0, 0, H / 2 + 0.0005), rot=(0, 0, rz), mat="tin", bevel=0.0008)
    b.torus(0.008 * s, 0.0012, loc=at(-W * 0.32, 0, H / 2 + 0.0022), rot=(0, 0, rz), mat="ring", seg=16, rseg=5)


@obj("spam_can", eras=(0, 1, 2, 3, 4), mass=0.34, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def spam_can(b, rng, pal):
    """The canned ham with the pull-ring lid. In Seoul it comes in a gift box and nobody laughs."""
    _spam_tin(b, (0, 0, 0), 0.0, s=float(_ch(rng, [1.0, 1.0, 0.85])))
    return {"tin": MET((0.78, 0.8, 0.82), 0.25), "label": PR(_spam_print(rng, "spam"), 0.3, metal=0.2),
            "ring": MET((0.85, 0.85, 0.87), 0.2)}


def _gift_lid(rng, name):
    c = _cv(512, 352, SPAM_BLUE)
    for k in range(9):                                                   # the gold wave lines
        xs = np.linspace(0, 1, 50)
        c.line(list(zip(xs.tolist(), (0.15 + k * 0.025 + 0.03 * np.sin(xs * 9 + k * 0.3)).tolist())), 0.006,
               (0.95, 0.78, 0.35))
    c.rect(0.0, 0.82, 1.0, 0.86, (0.95, 0.78, 0.35))
    _ct(c, "SPLAM", 0.5, 0.78, 0.2, SPAM_YEL, maxw=0.5)
    _ct(c, "PREMIUM GIFT SET", 0.5, 0.55, 0.07, (1, 1, 1), maxw=0.6)
    c.circle(0.86, 0.72, 0.09, (0.85, 0.12, 0.15))                       # the full moon, red seal style
    _ct(c, "CHUSEOK", 0.86, 0.75, 0.035, (1, 1, 1), maxw=0.12)
    for k in range(3):
        cx = 0.3 + k * 0.2
        c.rect(cx - 0.07, 0.25, cx + 0.07, 0.45, SPAM_YEL)
        c.rect(cx - 0.06, 0.27, cx + 0.06, 0.43, SPAM_BLUE)
        _ct(c, "SPLAM", cx, 0.4, 0.04, SPAM_YEL, maxw=0.1)
    c.text("8 CANS", 0.05, 0.1, 0.05, (1, 1, 1), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


@obj("spam_gift_box", eras=(0, 1, 2, 3, 4), mass=1.6, big=True, **SPECIAL)
def spam_gift_box(b, rng, pal):
    """The holiday gift set: a blue box, a plastic carry handle, cans in a molded tray. Given to bosses."""
    W, L, H = 0.25, 0.17, 0.055
    t = 0.003
    b.box((W, L, t), loc=(0, 0, -H / 2), mat="box")
    for sx in (-1, 1):
        b.box((t, L, H), loc=(sx * W / 2, 0, 0), mat="box")
    for sy in (-1, 1):
        b.box((W, t, H), loc=(0, sy * L / 2, 0), mat="box")
    b.box((W - 2 * t, L - 2 * t, 0.012), loc=(0, 0, -H / 2 + 0.008), mat="tray")
    n = int(rng.integers(4, 7))
    slots = [(-0.075, -0.04), (0.0, -0.04), (0.075, -0.04), (-0.075, 0.04), (0.0, 0.04), (0.075, 0.04)]
    for x, y in slots[:n]:                                               # the tins lie face up in the tray
        b.box((0.07, 0.072, 0.04), loc=(x, y, -H / 2 + 0.026), mat="tin", bevel=0.007)
        b.plane(0.062, 0.05, loc=(x, y, -H / 2 + 0.0465), mat="label", cuts=2)
    ang = float(rng.uniform(0.25, 1.2)) if rng.random() < 0.7 else 0.0
    hy = L / 2
    cy = hy - L / 2 * math.cos(ang)
    cz = H / 2 + 0.004 + L / 2 * math.sin(ang)
    b.box((W + 0.004, L + 0.004, 0.004), loc=(0, cy, cz), rot=(ang, 0, 0), mat="box")
    b.plane(W, L, loc=(0, cy - 0.0025 * math.sin(ang), cz + 0.0025 * math.cos(ang)), rot=(ang, 0, 0), mat="lid", cuts=2)
    b.tube([(-0.035, -L / 2 - 0.002, 0.01), (-0.03, -L / 2 - 0.022, 0.012), (0.03, -L / 2 - 0.022, 0.012),
            (0.035, -L / 2 - 0.002, 0.01)], 0.004, mat="handle", seg=8)
    return {"box": P(SPAM_BLUE, 0.5), "tray": P((0.95, 0.85, 0.4), 0.3, metal=0.6),
            "tin": MET((0.78, 0.8, 0.82), 0.25), "label": PR(_spam_print(rng, "spamg"), 0.3, metal=0.2),
            "lid": PR(_gift_lid(rng, "spamlid"), 0.4), "handle": P(_ch(rng, [(0.85, 0.12, 0.15), (0.95, 0.78, 0.35)]), 0.35)}


def _oil_print(rng, name):
    c = _cv(512, 160, (0.97, 0.96, 0.9))
    c.rect(0, 0, 1, 0.18, (0.15, 0.5, 0.2))
    c.rect(0, 0.82, 1, 1, (0.15, 0.5, 0.2))
    for cx in (0.25, 0.75):
        c.circle(cx - 0.1, 0.5, 0.18, (1.0, 0.85, 0.1))
        for i in range(8):                                               # the canola flower
            a = 2 * PI * i / 8
            c.circle(cx - 0.1 + 0.035 * math.cos(a), 0.5 + 0.11 * math.sin(a), 0.05, (1.0, 0.9, 0.2))
        _ct(c, "BAEKSEOL-ISH", cx + 0.05, 0.72, 0.13, (0.15, 0.5, 0.2), maxw=0.22)
        _ct(c, "CANOLA OIL", cx + 0.05, 0.45, 0.12, (0.85, 0.15, 0.1), maxw=0.2)
    return c.image(name)


@obj("gift_oil_bottle", eras=(0, 1, 2, 3, 4), mass=0.5, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def gift_oil_bottle(b, rng, pal):
    """The bottle of cooking oil every Korean gift set came with, wedged between the cans."""
    prof = [(0.0, -0.1), (0.031, -0.1), (0.033, -0.09), (0.033, 0.04), (0.026, 0.07), (0.013, 0.09), (0.013, 0.1),
            (0.0, 0.1)]
    b.lathe(prof, mat="pet", seg=28)
    b.lathe([(0.0, -0.098), (0.031, -0.098), (0.031, 0.035), (0.0, 0.035)], mat="oil", seg=24)
    b.cyl(0.0335, 0.07, loc=(0, 0, -0.035), mat="label", seg=28, cap=False)
    b.cyl(0.0145, 0.016, loc=(0, 0, 0.106), mat="cap", seg=20)
    return {"pet": _clear(rng, 0.07), "oil": P((1.0, 0.8, 0.2), 0.05, coat=1.0),
            "label": PR(_oil_print(rng, "oil"), 0.3), "cap": P((0.15, 0.5, 0.2), 0.35)}


@obj("songpyeon", eras=(0, 1, 2, 3, 4), mass=0.03, **SPECIAL)
def songpyeon(b, rng, pal):
    """Half-moon rice cakes in pastel colors, pinched shut over sesame or bean, steamed on pine needles."""
    cols = [(0.97, 0.95, 0.9), (1.0, 0.5, 0.62), (0.35, 0.6, 0.25), (1.0, 0.78, 0.25), (0.65, 0.45, 0.8)]
    specs = {}
    for k in range(int(rng.integers(3, 7))):
        x, y = (float(v) for v in rng.normal(0, 0.03, 2))
        L, Hm = 0.05, 0.027
        rings = []
        for xx in np.linspace(-L / 2, L / 2, 13):
            h = Hm * max(1 - (2 * xx / L) ** 2, 0.0) ** 0.5 + 0.002      # flat pinched edge at y=0, round belly
            rings.append([(float(xx), h / 2 - h / 2 * math.cos(t), 0.42 * h * math.sin(t) * (0.6 + 0.4 * math.sin(t / 2)))
                          for t in np.linspace(0, 2 * PI, 16, endpoint=False)])
        m = f"s{k % 4}"
        b.loft(rings, mat=m, loc=(x, y, 0), rot=(float(rng.normal(0, 0.2)), float(rng.normal(0, 0.2)), float(rng.uniform(0, 2 * PI))))
        specs[m] = ("clay", {"color": cols[(k + int(rng.integers(0, 5))) % 5], "smear": (1.0, 1.0, 1.0)})
    for _ in range(int(rng.integers(6, 14))):                            # the pine needles they steamed on
        x, y = (float(v) for v in rng.normal(0, 0.025, 2))
        a = float(rng.uniform(0, PI))
        b.tube([(x, y, -0.006), (x + 0.04 * math.cos(a), y + 0.04 * math.sin(a), -0.007)], 0.0005, mat="pine", seg=4)
    specs["pine"] = P((0.25, 0.4, 0.15), 0.6)
    return specs


@obj("persimmon", eras=(0, 1, 2, 3, 4), mass=0.2, **SPECIAL)
def persimmon(b, rng, pal):
    """A squat orange persimmon with its four-leaf cap. Sometimes a dried one, wrinkled and frosted."""
    dried = rng.random() < 0.25
    s = 0.6 if dried else 1.0
    b.sphere(0.036 * s, scale=(1, 1, 0.72), mat="fruit", seg=24)
    for i in range(4):
        a = PI / 2 * i + 0.4
        b.extrude([(0, -0.005), (0.011, -0.008), (0.016, 0), (0.011, 0.008), (0, 0.005)], 0.0012,
                  loc=(0.004 * math.cos(a), 0.004 * math.sin(a), 0.026 * s), rot=(0.25 * math.sin(a), -0.25 * math.cos(a), a),
                  mat="calyx", scale=(s, s, 1))
    b.cyl(0.0025, 0.008, loc=(0, 0, 0.03 * s), mat="calyx", seg=8)
    fruit = P((0.55, 0.25, 0.08), 0.75) if dried else P((1.0, 0.26, 0.0), 0.18, coat=0.6)
    return {"fruit": fruit, "calyx": P((0.25, 0.28, 0.1), 0.7)}


def _pear_skin(rng, name):
    c = _cv(256, 128, (0.78, 0.6, 0.32))
    for _ in range(500):                                                 # the lenticel freckles
        c.circle(float(rng.uniform(0, 1)), float(rng.uniform(0, 1)), float(rng.uniform(0.004, 0.009)), (0.9, 0.78, 0.5))
    c.noise(rng, 0.03)
    return c.image(name)


@obj("asian_pear", eras=(0, 1, 2, 3, 4), mass=0.6, **SPECIAL)
def asian_pear(b, rng, pal):
    """A Korean pear the size of a softball, golden-brown and freckled, in its white foam net sock."""
    R = 0.05
    b.sphere(R, scale=(1, 1, 0.9), mat="skin", seg=28)
    b.cyl(0.0022, 0.016, loc=(0.002, 0, R * 0.9 + 0.004), rot=(0.2, 0, 0), mat="stem", seg=8)
    net = rng.random() < 0.8
    if net:
        for d in (-1, 1):
            for k in range(10):
                a0 = 2 * PI * k / 10
                pts = []
                for t in np.linspace(-1.1, 1.1, 13):
                    a = a0 + d * t * 1.1
                    pts.append(((R + 0.003) * math.cos(t) * math.cos(a), (R + 0.003) * math.cos(t) * math.sin(a),
                                (R + 0.003) * 0.9 * math.sin(t)))
                b.tube(pts, 0.0022, mat="net", seg=5)
    return {"skin": PR(_pear_skin(rng, "pear"), 0.5), "stem": P((0.3, 0.2, 0.1), 0.7),
            "net": ("foam", {"color": (0.97, 0.97, 0.95)})}


HWATU_RED = (0.78, 0.07, 0.08)


def _hwatu_face(rng, name):
    c = _cv(128, 200, (0.97, 0.95, 0.88))
    asp = 128 / 200
    kind = int(rng.integers(0, 6))
    if kind == 0:                                                      # the moon over the black hill
        c.rect(0, 0, 1, 1, (0.85, 0.15, 0.1))
        c.circle(0.5, 0.72, 0.17, (0.98, 0.97, 0.92))
        c.poly([(0, 0), (0, 0.45), (0.5, 0.6), (1, 0.42), (1, 0)], (0.05, 0.05, 0.05))
    elif kind == 1:                                                    # pine, crane, red sun
        c.circle(0.65, 0.78, 0.13, (0.85, 0.12, 0.1))
        for k in range(4):
            c.poly([(0.05, 0.25 + k * 0.1), (0.95, 0.35 + k * 0.08), (0.5, 0.5 + k * 0.1)], (0.1, 0.35, 0.15))
        c.circle(0.35, 0.22, 0.12, (0.98, 0.98, 0.98))
        c.circle(0.35, 0.33, 0.03, (0.85, 0.1, 0.1))
    elif kind == 2:                                                    # blossom with the red poem ribbon
        for _ in range(9):
            cx, cy = float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.35, 0.95))
            c.circle(cx, cy, 0.07, (1.0, 0.65, 0.75))
            c.circle(cx, cy, 0.02, (0.9, 0.2, 0.3))
        c.poly([(0.42, 0.75), (0.58, 0.75), (0.56, 0.08), (0.44, 0.08)], HWATU_RED)
    elif kind == 3:                                                    # maple leaves and the deer's red ground
        for _ in range(6):
            c.poly(_star(float(rng.uniform(0.15, 0.85)), float(rng.uniform(0.4, 0.95)), 0.11, 5, 0.5, asp=asp), (0.85, 0.15, 0.1))
        c.rect(0, 0, 1, 0.25, (0.55, 0.35, 0.15))
    elif kind == 4:                                                    # peony, big and red
        c.circle(0.5, 0.55, 0.22, (0.85, 0.1, 0.25))
        c.circle(0.5, 0.55, 0.12, (1.0, 0.45, 0.55))
        for sx in (-1, 1):
            c.poly([(0.5, 0.35), (0.5 + sx * 0.4, 0.2), (0.5 + sx * 0.2, 0.45)], (0.1, 0.35, 0.15))
    else:                                                              # rain: the willow and the black slashes
        c.rect(0, 0, 1, 1, (0.85, 0.15, 0.1))
        for k in range(6):
            c.line([(0.1 + k * 0.15, 1.0), (0.05 + k * 0.15, 0.1)], 0.02, (0.05, 0.05, 0.05))
    c.rect(0.0, 0.0, 0.03, 1, (0.2, 0.2, 0.2))
    c.rect(0.97, 0.0, 1, 1, (0.2, 0.2, 0.2))
    return c.image(name)


@obj("hwatu_cards", eras=(0, 1, 2, 3, 4), mass=0.02, **SPECIAL)
def hwatu_cards(b, rng, pal):
    """Flower cards: little thick red-backed cards, twelve months of plants. Played on a blanket after dinner."""
    n = int(rng.integers(3, 8))
    specs = {"back": P(HWATU_RED, 0.3, coat=0.5), "edge": P((0.2, 0.18, 0.15), 0.4)}
    for k in range(n):
        x, y = (float(v) for v in rng.normal(0, 0.012, 2))
        rz = float(rng.normal(0, 0.6))
        z = k * 0.0013
        b.box((0.034, 0.054, 0.0011), loc=(x, y, z), rot=(0, 0, rz), mat="edge")
        if rng.random() < 0.65:
            m = f"f{k % 4}"
            b.plane(0.033, 0.053, loc=(x, y, z + 0.0006), rot=(0, 0, rz), mat=m, cuts=2)
            if m not in specs:
                specs[m] = PR(_hwatu_face(rng, f"hwatu{k % 4}"), 0.35)
        else:
            b.plane(0.033, 0.053, loc=(x, y, z + 0.0006), rot=(0, 0, rz), mat="back", cuts=2)
    return specs


@obj("yut_sticks", eras=(0, 1, 2, 3, 4), mass=0.08, **SPECIAL)
def yut_sticks(b, rng, pal):
    """Four half-round sticks for yut nori, the flat faces up or down; one has the X that sends you back."""
    specs = {"bark": P((0.7, 0.5, 0.3), 0.6), "flat": P((0.92, 0.82, 0.62), 0.7), "x": P((0.15, 0.1, 0.08), 0.6)}
    half = [(0.0085 * math.cos(a), 0.0085 * math.sin(a)) for a in np.linspace(0, PI, 12)]
    for k in range(4):
        x, y = float(rng.normal(0, 0.01)), -0.03 + k * 0.02 + float(rng.normal(0, 0.003))
        up = rng.random() < 0.5                                         # flat face up: that stick counts
        rz = float(rng.normal(0, 0.15))
        b.extrude(half, 0.16, loc=(x, y, 0.0), rot=(-PI / 2 if up else PI / 2, 0, rz - PI / 2), mat="bark")
        b.plane(0.16, 0.0168, loc=(x, y, 0.0002 if up else -0.0002), rot=(0 if up else PI, 0, rz), mat="flat", cuts=2)
        if k == 0:
            for s in (-1, 1):
                b.box((0.022, 0.0016, 0.0006), loc=(x, y, 0.0006 if up else -0.0006), rot=(0, 0, rz + s * 0.6), mat="x")
    return specs


def _pie_print(rng, name):
    c = _cv(512, 320, (0.85, 0.07, 0.1))
    c.rect(0, 0, 1, 0.08, (0.97, 0.9, 0.8))
    c.rect(0, 0.92, 1, 1, (0.97, 0.9, 0.8))
    _ct(c, "CHOCO PAI", 0.5, 0.86, 0.15, (0.97, 0.9, 0.8), maxw=0.6)
    c.poly(_heart(0.82, 0.68, 0.11, asp=1.6), (0.97, 0.9, 0.8))         # the heart: it means affection, honest
    c.poly(_heart(0.82, 0.68, 0.08, asp=1.6), (0.85, 0.07, 0.1))
    c.circle(0.42, 0.35, 0.22, (0.33, 0.17, 0.08))                        # the pie, cut, marshmallow showing
    c.rect(0.2, 0.33, 0.55, 0.38, (0.98, 0.97, 0.94))
    c.poly([(0.42, 0.35), (0.62, 0.15), (0.65, 0.4)], (0.85, 0.07, 0.1))
    c.text("12 PIES", 0.05, 0.2, 0.05, (0.97, 0.9, 0.8), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


@obj("choco_pie_box", eras=(0, 1, 2, 3, 4), mass=0.4, **RARE)
def choco_pie_box(b, rng, pal):
    """The red box of marshmallow chocolate cakes, or one cake in its red wrapper, or one cake with a bite out."""
    r = rng.random()
    img = _pie_print(rng, "pie")
    if r < 0.4:
        W, L, D = 0.24, 0.15, 0.05
        b.box((W, L, D), mat="box", bevel=0.0015)
        b.plane(W, L, loc=(0, 0, D / 2 + 0.0003), mat="front", cuts=2)
        return {"box": P((0.85, 0.07, 0.1), 0.5), "front": PR(img, 0.4)}
    if r < 0.75:
        _flow_bar(b, 0.09, 0.085, 0.024, "top", "wrap", crimp=0.01)
        return {"wrap": P((0.85, 0.07, 0.1), 0.3, coat=0.5), "top": PR(img, 0.3, metal=0.2)}
    b.lathe([(0.0, -0.011), (0.033, -0.011), (0.037, -0.006), (0.037, 0.005), (0.032, 0.011), (0.0, 0.011)],
            mat="coat", seg=28)
    b.box((0.03, 0.08, 0.03), loc=(0.032, 0, 0), rot=(0, 0, 0.4), mat="cake")
    b.box((0.012, 0.03, 0.004), loc=(0.015, 0, 0), rot=(0, 0, 1.97), mat="mallow")
    return {"coat": P((0.3, 0.15, 0.06), 0.4, coat=0.3), "cake": P((0.6, 0.38, 0.18), 0.85),
            "mallow": P((0.98, 0.97, 0.94), 0.7)}


def _bmilk_print(rng, name):
    c = _cv(512, 256, (1.0, 0.86, 0.42))
    _ct(c, "BINGO", 0.75, 0.62, 0.1, (0.15, 0.55, 0.25), maxw=0.18)
    _ct(c, "BANANA MILK", 0.75, 0.48, 0.07, (0.15, 0.55, 0.25), maxw=0.2)
    c.text("240ML", 0.71, 0.3, 0.04, (0.15, 0.55, 0.25))
    return c.image(name)


@obj("banana_milk", eras=(0, 1, 2, 3, 4), mass=0.26, hero=(0, -1, 0), tags=("upright",), **RARE)
def banana_milk(b, rng, pal):
    """The squat pale-yellow jug of banana milk with the foil peel top. Bought at every bathhouse and rest stop."""
    prof = [(0.0, -0.055), (0.028, -0.055), (0.032, -0.048), (0.035, -0.02), (0.034, 0.0), (0.03, 0.02), (0.02, 0.038),
            (0.016, 0.048), (0.017, 0.052), (0.017, 0.057), (0.0, 0.057)]
    b.lathe(prof, mat="jug", seg=32)
    b.cyl(0.0172, 0.0008, loc=(0, 0, 0.0574), mat="foil", seg=20)
    if rng.random() < 0.4:                                              # a straw through the foil
        b.cyl(0.003, 0.11, loc=(0.004, 0, 0.09), rot=(0.25, 0, 0), mat="straw", seg=10)
    return {"jug": PR(_bmilk_print(rng, "bmilk"), 0.35), "foil": MET((0.9, 0.9, 0.9), 0.25),
            "straw": P(_ch(rng, [(1.0, 0.9, 0.3), (0.3, 0.7, 0.35), (0.95, 0.95, 0.95)]), 0.3)}


# ================================================================================================
# GOLAZO: the World Cup, every four years, everywhere
# ================================================================================================

def _ico_dirs():
    t = (1 + 5 ** 0.5) / 2
    vs = []
    for a in (-1, 1):
        for c_ in (-t, t):
            vs += [(0, a, c_), (a, c_, 0), (c_, 0, a)]
    return np.array([np.array(v) / np.linalg.norm(v) for v in vs])


def _tango_print(rng, name, base, ink):
    """Twelve circles of three curved triads each, mapped onto the sphere's lat-long UVs."""
    c = _cv(768, 384, base)
    lon = (c.x - 0.5) * 2 * PI
    lat = (c.y - 0.5) * PI
    p = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1)
    V = _ico_dirs()
    dots = p @ V.T
    i = np.argmax(dots, -1)
    d = np.arccos(np.clip(np.max(dots, -1), -1, 1))
    v = V[i]
    up = np.where(np.abs(v[..., 2:3]) < 0.9, np.array([0, 0, 1.0]), np.array([1.0, 0, 0]))
    e1 = np.cross(v, up)
    e1 /= np.linalg.norm(e1, axis=-1, keepdims=True)
    e2 = np.cross(v, e1)
    az = np.arctan2((p * e2).sum(-1), (p * e1).sum(-1)) + i * 0.7
    wedge = np.abs(((az * 3 / (2 * PI)) % 1.0) - 0.5)                    # 0 at a triad center, 0.5 at the gap
    inner = 0.17 + 0.12 * wedge                                          # curved inner edge: thin at the gaps
    mask = ((d > inner) & (d < 0.36) & (wedge < 0.42)).astype(np.float32)
    c._blend(mask, ink)
    c._blend(((d > 0.385) & (d < 0.4)).astype(np.float32) * 0.35, ink)   # the seam ring
    c.noise(rng, 0.015)
    return c.image(name)


@obj("tango_football", eras=(0, 1, 2), mass=0.43, big=True, **RARE)
def tango_football(b, rng, pal):
    """A match ball with the twelve-circle triad pattern, scuffed grey from the street. Sometimes half flat."""
    flat = float(rng.uniform(0.7, 0.85)) if rng.random() < 0.3 else 1.0
    ink = _ch(rng, [INK, INK, (0.1, 0.25, 0.65), (0.1, 0.45, 0.25)])
    b.sphere(0.11, scale=(1, 1, flat), mat="ball", seg=40)
    return {"ball": PR(_tango_print(rng, "tango", (0.95, 0.95, 0.92), ink), 0.35)}


def _rot90(c):
    out = tex.Canvas(c.h, c.w, (0, 0, 0, 1))
    out.a = np.ascontiguousarray(np.rot90(c.a, -1))
    return out


TEAMS = [("FORZA", (0.1, 0.3, 0.75), (0.97, 0.97, 0.97)), ("ALLEZ", (0.1, 0.2, 0.55), (0.85, 0.1, 0.12)),
         ("VAMOS", (0.55, 0.75, 0.95), (0.97, 0.97, 0.97)), ("OLE OLE", (1.0, 0.85, 0.1), (0.1, 0.55, 0.25)),
         ("DAEHAN", (0.85, 0.1, 0.12), (0.97, 0.97, 0.97)), ("ORANJE-ISH", (1.0, 0.5, 0.05), (0.97, 0.97, 0.97))]


def _scarf_print(rng, name, team):
    word, a, bb = team
    c = _cv(1024, 160, a)
    for k in range(0, 1024, 128):                                         # the bar stripes
        c.rect(k / 1024, 0, (k + 40) / 1024, 1, bb)
    c.rect(0.12, 0.08, 0.88, 0.92, a)
    _ct(c, word, 0.5, 0.74, 0.5, bb, maxw=0.7, spacing=1.1)
    c.rect(0.0, 0.0, 1.0, 0.05, bb)
    c.rect(0.0, 0.95, 1.0, 1.0, bb)
    for _ in range(30):                                                   # the pilling
        c.circle(float(rng.uniform(0, 1)), float(rng.uniform(0, 1)), 0.01, tuple(min(1, v + 0.1) for v in a))
    return _rot90(c).image(name)


@obj("team_scarf", eras=(0, 1, 2, 3, 4), mass=0.18, **RARE)
def team_scarf(b, rng, pal):
    """A knitted bar scarf, folded three times, the team chant spelled down its length. Tassels on both ends."""
    team = _ch(rng, TEAMS)
    W = 0.17
    path = []
    layers = int(rng.integers(2, 4))
    L = 0.26
    for k in range(layers):
        d = 1 if k % 2 == 0 else -1
        z = k * 0.014
        for x in np.linspace(-L / 2, L / 2, 9)[:-1]:
            path.append((d * x, z + 0.002 * math.sin(x * 40)))
        for t in np.linspace(-PI / 2, PI / 2, 5)[:-1] if k < layers - 1 else []:
            path.append((d * (L / 2 + 0.007 * math.cos(t)), z + 0.007 + 0.007 * math.sin(t)))
    path.append((path[-1][0] + (0.02 if layers % 2 == 1 else -0.02), path[-1][1]))
    ys = np.linspace(-W / 2, W / 2, 9)
    rings = [[(x, float(y), z) for y in ys] for x, z in path]
    b.loft(rings, mat="knit", closed=False)
    b.loft([[(x, float(y), z - 0.003) for y in ys] for x, z in path], mat="back", closed=False)
    for end in (path[0], path[-1]):
        sgn = 1 if end[0] > 0 else -1
        for y in np.linspace(-W / 2 + 0.01, W / 2 - 0.01, 9):
            b.tube([(end[0], float(y), end[1]), (end[0] + sgn * 0.03, float(y) + float(rng.normal(0, 0.004)), end[1] - 0.004)],
                   0.0018, mat="tassel", seg=5)
    return {"knit": PR(_scarf_print(rng, "scarf", team), 0.95), "back": ("fabric", {"color": team[1]}),
            "tassel": ("fabric", {"color": team[2]})}


def _horn_print(rng, name, cols):
    c = _cv(256, 512, cols[0])
    n = len(cols)
    for k in range(12):
        c.rect(0, k / 12, 1, (k + 1) / 12, cols[k % n])
    return c.image(name)


@obj("vuvuzela", eras=(3, 4), mass=0.12, big=True, **SPECIAL)
def vuvuzela(b, rng, pal):
    """The bell half of a two-piece plastic stadium horn. One B-flat, ninety minutes, the whole summer of 2010."""
    prof_o = [(0.017, 0.0), (0.019, 0.12), (0.023, 0.22), (0.03, 0.28), (0.042, 0.315), (0.05, 0.33)]
    prof = prof_o + [(r - 0.0015, z) for r, z in reversed(prof_o)]
    b.lathe(prof, loc=(-0.165, 0, 0), rot=(0, PI / 2, 0), mat="horn", seg=28)
    if rng.random() < 0.5:                                               # the mouth half, pulled off
        mo = [(0.0105, 0.0), (0.0105, 0.012), (0.0075, 0.02), (0.012, 0.3), (0.016, 0.31)]
        m2 = mo + [(r - 0.0013, z) for r, z in reversed(mo)]
        b.lathe(m2, loc=(-0.15, 0.06, 0), rot=(0, PI / 2, 0.1), mat="horn2", seg=20)
    style = rng.random()
    cols = _ch(rng, [[(1.0, 0.85, 0.05)], [(0.1, 0.55, 0.25), (1.0, 0.85, 0.05)], [(0.95, 0.95, 0.95), (0.1, 0.3, 0.8)],
                     [(0.85, 0.1, 0.12), (0.97, 0.97, 0.97)], [(0.05, 0.45, 0.25), (0.97, 0.97, 0.97), (0.85, 0.1, 0.12)]])
    horn = PR(_horn_print(rng, "vuvu", cols), 0.35) if (style < 0.6 and len(cols) > 1) else P(cols[0], 0.35)
    return {"horn": horn, "horn2": P(cols[0], 0.35)}


def _airhorn_print(rng, name):
    c = _cv(512, 256, (0.95, 0.95, 0.93))
    c.rect(0, 0.0, 1, 0.2, (0.1, 0.2, 0.6))
    c.rect(0, 0.8, 1, 1, (0.1, 0.2, 0.6))
    for cx in (0.25, 0.75):
        c.poly(_star(cx - 0.08, 0.5, 0.2, 10, 0.6, asp=2.0), (1.0, 0.85, 0.1))
        _ct(c, "AIR BLAST", cx, 0.7, 0.13, (0.85, 0.1, 0.12), maxw=0.22)
        _ct(c, "STADIUM HORN", cx + 0.04, 0.45, 0.07, (0.1, 0.2, 0.6), maxw=0.18)
        c.text("130 DB!", cx - 0.02, 0.3, 0.06, INK, bold=True)
    return c.image(name)


@obj("air_horn", eras=(0, 1, 2, 3, 4), mass=0.2, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def air_horn(b, rng, pal):
    """The canned air horn with the red plastic trumpet. Banned at the gate, smuggled in a sock."""
    b.cyl(0.033, 0.12, loc=(0, 0, -0.03), mat="label", seg=28, cap=False)
    b.lathe([(0.0, -0.092), (0.033, -0.092), (0.033, -0.088)], mat="can", seg=28)
    b.lathe([(0.033, 0.03), (0.03, 0.04), (0.02, 0.048), (0.012, 0.05), (0.0, 0.051)], mat="can", seg=28)
    b.cyl(0.012, 0.014, loc=(0, 0, 0.057), mat="valve", seg=16)
    b.lathe([(0.0, 0.0), (0.012, 0.0), (0.012, 0.015), (0.016, 0.05), (0.026, 0.085), (0.038, 0.1), (0.0365, 0.1),
             (0.0245, 0.085), (0.0145, 0.05), (0.0105, 0.015), (0.0, 0.015)], loc=(0, 0, 0.062), mat="horn", seg=24)
    return {"label": PR(_airhorn_print(rng, "airh"), 0.3, metal=0.3), "can": MET((0.8, 0.8, 0.82), 0.25),
            "valve": P(BLACK, 0.4), "horn": P(_ch(rng, [(0.85, 0.1, 0.12), (0.95, 0.95, 0.95), (1.0, 0.85, 0.1)]), 0.3)}


def _plush_jersey(rng, name, a, bb):
    c = _cv(256, 128, a)
    c.rect(0, 0.82, 1, 1, bb)
    num = str(int(rng.integers(1, 24)))
    for cx in (0.25, 0.75):
        _ct(c, num, cx, 0.7, 0.4, bb, maxw=0.2)
    return c.image(name)


@obj("mascot_plush", eras=(0, 1, 2, 3, 4), mass=0.15, hero=(0, -1, 0), tags=("upright",), **SPECIAL)
def mascot_plush(b, rng, pal):
    """Our own tournament mascot, a big-mouthed frog in a jersey with a ball under one arm. Claw-machine quality."""
    team = _ch(rng, TEAMS)
    skin = _ch(rng, [(0.4, 0.75, 0.25), (0.3, 0.65, 0.35), (0.55, 0.8, 0.2)])
    b.sphere(0.04, loc=(0, 0, 0.04), scale=(1, 0.85, 1.0), mat="jersey", seg=20)
    b.sphere(0.045, loc=(0, -0.004, 0.105), scale=(1.15, 0.9, 0.75), mat="skin", seg=22)
    for sx in (-1, 1):
        b.sphere(0.016, loc=(sx * 0.024, -0.012, 0.136), mat="skin", seg=14)
        b.sphere(0.011, loc=(sx * 0.024, -0.022, 0.139), mat="eye", seg=12)
        b.sphere(0.006, loc=(sx * 0.024, -0.031, 0.14), mat="pupil", seg=10)
        b.tube([(sx * 0.035, 0, 0.06), (sx * 0.05, -0.01, 0.045), (sx * 0.055, -0.02, 0.03)], 0.009, mat="skin", seg=10)
        b.sphere(0.014, loc=(sx * 0.02, -0.022, 0.006), scale=(1, 1.6, 0.5), mat="skin", seg=12)
    b.tube([(-0.026, -0.04, 0.094), (0, -0.046, 0.088), (0.026, -0.04, 0.094)], 0.0028, mat="mouth", seg=6)
    b.sphere(0.022, loc=(0.058, -0.022, 0.035), mat="ball", seg=18)
    return {"jersey": PR(_plush_jersey(rng, "pjers", team[1], team[2]), 0.95), "skin": ("fabric", {"color": skin}),
            "eye": ("fabric", {"color": (0.97, 0.97, 0.95)}), "pupil": P(BLACK, 0.2, coat=0.8),
            "mouth": ("fabric", {"color": (0.85, 0.15, 0.2)}),
            "ball": PR(_tango_print(rng, "ptango", (0.95, 0.95, 0.92), INK), 0.9)}


def _flag_print(rng, name):
    c = _cv(128, 96, (0.97, 0.97, 0.97))
    _flagbar(c, 0.0, 0.0, 1.0, 1.0, rng)
    if rng.random() < 0.3:
        c.poly(_star(0.5, 0.5, 0.2, asp=128 / 96), (1.0, 0.85, 0.1))
    return c.image(name)


@obj("flag_bunting", eras=(0, 1, 2, 3, 4), mass=0.04, **SPECIAL)
def flag_bunting(b, rng, pal):
    """A string of little paper flags of every country in the group, off the front of the corner shop."""
    n = int(rng.integers(5, 9))
    pts = [(-0.18 + 0.36 * i / 20, 0.02 * math.sin(i * 0.5), 0.008 * math.sin(i * 0.9)) for i in range(21)]
    b.tube(pts, 0.0007, mat="string", seg=5)
    specs = {"string": P((0.95, 0.95, 0.93), 0.7)}
    for k in range(n):
        u = (k + 0.5) / n
        x = -0.18 + 0.36 * u
        i = int(u * 20)
        y = pts[i][1]
        m = f"f{k % 4}"
        b.plane(0.034, 0.05, loc=(x, y - 0.025, pts[i][2] + float(rng.normal(0, 0.002))),
                rot=(float(rng.normal(0, 0.25)), 0, float(rng.normal(0, 0.12))), mat=m, cuts=2)
        if m not in specs:
            specs[m] = PR(_flag_print(rng, f"bunt{k % 4}"), 0.85)
    return specs


def _wallchart_print(rng, name):
    c = _cv(512, 384, (0.93, 0.91, 0.84))
    c.rect(0, 0.88, 1, 1, (0.85, 0.1, 0.12))
    _ct(c, "WORLD CUP WALLCHART", 0.5, 0.97, 0.06, (1, 1, 1), maxw=0.8)
    ink = (0.2, 0.2, 0.22)
    for g in range(8):                                                   # the group tables
        x0 = 0.03 + (g % 4) * 0.165
        y0 = 0.82 - (g // 4) * 0.4
        c.text(f"GROUP {'ABCDEFGH'[g]}", x0, y0, 0.03, (0.85, 0.1, 0.12), bold=True)
        for r in range(4):
            yy = y0 - 0.06 - r * 0.07
            c.rect(x0, yy - 0.05, x0 + 0.15, yy, (0.85, 0.83, 0.76))
            _flagbar(c, x0 + 0.005, yy - 0.04, x0 + 0.03, yy - 0.01, rng)
            if rng.random() < 0.6:                                       # scores filled in, in biro
                c.text(f"{int(rng.integers(0, 4))}-{int(rng.integers(0, 4))}", x0 + 0.09, yy - 0.012, 0.028, (0.1, 0.2, 0.7))
    for k in range(8):                                                   # the knockout bracket
        y = 0.82 - k * 0.1
        c.line([(0.7, y), (0.78, y), (0.78, y - 0.05), (0.85, y - 0.05)], 0.006, ink)
    c.line([(0.85, 0.77), (0.85, 0.12), (0.93, 0.45), (0.97, 0.45)], 0.006, ink)
    c.noise(rng, 0.02)
    halves = []
    for k in range(2):
        h = tex.Canvas(c.w // 2, c.h)
        h.a = np.ascontiguousarray(c.a[:, k * (c.w // 2):(k + 1) * (c.w // 2)])
        halves.append(h.image(f"{name}{k}"))
    return halves


@obj("wallchart", eras=(0, 1, 2, 3), mass=0.03, **SPECIAL)
def wallchart(b, rng, pal):
    """The free newspaper wallchart, folded in half, groups filled in in pen until your team went out."""
    W, H = 0.3, 0.22
    ang = float(rng.uniform(0.15, 0.6))
    b.plane(W / 2, H, loc=(-W / 4, 0, 0), mat="l", cuts=3)
    b.plane(W / 2, H, loc=(W / 4 * math.cos(ang), 0, W / 4 * math.sin(ang)), rot=(0, -ang, 0), mat="r", cuts=3)
    left, right = _wallchart_print(rng, "wchart")
    return {"l": PR(left, 0.85), "r": PR(right, 0.85)}


LORE_NAMES = {
    "surprise_egg": "Kinda Surprise Egg",
    "surprise_capsule": "Yellow Toy Capsule",
    "surprise_toy": "Surprise Egg Toy",
    "surprise_slip": "Instruction Slip",
    "choc_egg_shell": "Chocolate Egg Shell",
    "hazelnut_wafer_bar": "Kinda Bono",
    "joy_egg": "Kinda Joy",
    "kids_choc_bar": "Kinda Chocolate Bar",
    "football_sticker": "Panetti Sticker",
    "sticker_packet": "Sticker Packet",
    "sticker_album": "Panetti Sticker Album",
    "shiny_badge": "Shiny Team Badge",
    "swap_stack": "Swaps Stack",
    "flick_figure": "Table Football Player",
    "foam_football": "Foam Football",
    "pick_bag": "Pick 'n' Mix Bag",
    "candy_scoop": "Candy Scoop",
    "cola_bottles": "Gummy Cola Bottles",
    "foam_shrimps": "Foam Shrimps",
    "fried_eggs": "Gummy Fried Eggs",
    "white_mice": "Sugar Mice",
    "flying_saucers": "Flying Saucers",
    "fizzy_laces": "Fizzy Laces",
    "jelly_babies": "Jelly Babies",
    "chew_bar": "Whammo! Bar",
    "gacha_capsule": "Gacha Capsule",
    "gacha_figure": "Capsule Figure",
    "menko_card": "Menko Card",
    "seal_sticker": "Wafer Seal Sticker",
    "pocket_diecast": "Tomiko Die-Cast",
    "famicom_cart": "Family Computer Cartridge",
    "umaibo": "Oishibo",
    "calpis_bottle": "Kalpisu Water",
    "kinkeshi": "Muscle Eraser",
    "gacha_knob": "Capsule Machine Crank",
    "purikura_sheet": "Purikura Sheet",
    "charm_phone": "Decorated Flip Phone",
    "keitai_strap": "Phone Straps",
    "stick_biscuit_box": "Pocko",
    "fruit_chew": "Hai-Choo",
    "loose_socks": "Loose Sock",
    "magic_wand": "Magical Girl Wand",
    "gb_pocket": "Game Kid Pocket",
    "tazo": "Taza",
    "tazo_chip_bag": "Chip Bag (Tazas Inside)",
    "tazo_tube": "Taza Collector Tube",
    "puff_bag": "Cheese Puffs",
    "tazo_board": "Taza Collector Board",
    "glass_soda": "Jarrones Soda",
    "spam_can": "Splam",
    "spam_gift_box": "Splam Gift Set",
    "gift_oil_bottle": "Gift Set Canola Oil",
    "songpyeon": "Songpyeon",
    "persimmon": "Persimmon",
    "asian_pear": "Korean Pear",
    "hwatu_cards": "Hwatu Cards",
    "yut_sticks": "Yut Sticks",
    "choco_pie_box": "Choco Pai",
    "banana_milk": "Banana Milk",
    "tango_football": "Match Ball",
    "team_scarf": "Bar Scarf",
    "vuvuzela": "Vuvuzela",
    "air_horn": "Air Horn",
    "mascot_plush": "Mascot Plush",
    "flag_bunting": "Paper Flag Bunting",
    "wallchart": "World Cup Wallchart",
}

LORE_NOTES = {
    "surprise_egg": ["illegal in the United States. legal everywhere you went on vacation.",
                     "foil peeled in one strip: a skill", "shook it next to your ear to guess the toy"],
    "surprise_capsule": ["the egg inside the egg", "pried open with a thumbnail, then a tooth",
                         "kept as a pill box, a bead box, a nothing box"],
    "surprise_toy": ["four pieces, one sticker, no glue", "the sticker went on crooked",
                     "found in a couch in 2004, still not built"],
    "surprise_slip": ["warnings in eleven languages", "thrown away first, needed second"],
    "choc_egg_shell": ["brown outside, white inside, mostly inside a sibling", "melted onto the capsule in the car"],
    "hazelnut_wafer_bar": ["two bars per pack: one to eat, one to also eat", "brought back in a suitcase by an aunt"],
    "joy_egg": ["the half that let America in on the joke", "spoon too small for the cream, used anyway",
                "toy half opened before the food half, every time"],
    "kids_choc_bar": ["the milky middle was the point", "sold one bar at a time at the register"],
    "football_sticker": ["got, got, got, need", "number on the back checked against a list in biro",
                         "peeled crooked, smoothed with a thumbnail, never straight again"],
    "sticker_packet": ["five stickers, three doubles", "opened with teeth at the newsagent counter"],
    "sticker_album": ["half full. it was always half full.", "the team that never came out of a packet",
                      "cover price in lire and pence, printed side by side"],
    "shiny_badge": ["worth five normal ones on the playground exchange", "the foil caught the light in the lunch line"],
    "swap_stack": ["thumbed so often the corners went round", "rubber band from the post", "\"got, got, need, got\""],
    "flick_figure": ["flick to kick, never with a fingernail", "the goalie lost his arms in 1991"],
    "foam_football": ["the only ball allowed in the house", "still broke the lamp", "chewed by the dog by the semifinal"],
    "pick_bag": ["priced by weight, filled by eye", "corners gone see-through from the sugar",
                 "the store closed. the bag survived."],
    "candy_scoop": ["you were supposed to use it", "went home in the bag by accident"],
    "cola_bottles": ["fizzy or not fizzy: the great debate", "brown at the bottom, clear at the top, gone in a minute"],
    "foam_shrimps": ["tasted of pink", "nothing like a shrimp. nobody minded."],
    "fried_eggs": ["the yolk went first", "breakfast for dessert"],
    "white_mice": ["chalky in a good way", "the tail was the best part"],
    "flying_saucers": ["rice paper stuck to the roof of your mouth", "sherbet went everywhere, mostly up the nose"],
    "fizzy_laces": ["measured against your arm before eating", "tied into a bracelet, then eaten"],
    "jelly_babies": ["head first, always", "dusted in starch, left fingerprints on everything"],
    "chew_bar": ["two pence of pure electricity", "pulled a filling, 1989"],
    "gacha_capsule": ["two hundred yen and a prayer", "you got the one nobody wanted. again.",
                      "the capsule outlived the toy by a decade"],
    "gacha_figure": ["slightly off-register, perfectly fine", "lined up on the windowsill by series"],
    "menko_card": ["slapped flat on the pavement to flip the other kid's", "bent from being slammed. that's the strategy."],
    "seal_sticker": ["kids bought the wafers, threw the wafers away", "the holographic one: traded for lunch money"],
    "pocket_diecast": ["the suspension actually bounces", "box kept, car lost, or the other way round"],
    "famicom_cart": ["shorter than the American one, and in a candy color", "blown into, also"],
    "umaibo": ["ten yen, for years and years", "corn potage flavor, which is a soup", "crumbs in the backpack seams"],
    "calpis_bottle": ["tastes like a yogurt that went to heaven", "the name sounds worse in English. we know."],
    "kinkeshi": ["an eraser that could not erase", "one color, a hundred wrestlers", "flicked across the desk in tournaments"],
    "gacha_knob": ["turn until it clicks", "the click before the capsule drops is the whole hobby"],
    "purikura_sheet": ["peace sign, every frame", "half of them stuck in a planner, the other half traded",
                       "decorated in the booth with a stylus and forty seconds"],
    "charm_phone": ["more charm than phone", "rhinestones applied one at a time on a Sunday",
                    "the straps weighed more than the handset"],
    "keitai_strap": ["outlived the phone", "one from every trip, one from every friend"],
    "stick_biscuit_box": ["the handle end is the trick: no chocolate fingers", "two bags in the box, shared, one stick at a time"],
    "fruit_chew": ["soft enough to stick to your molars", "the green apple went first"],
    "loose_socks": ["bunched down the shin on purpose", "held up with sock glue", "the longer the better, 1997"],
    "magic_wand": ["the light-up button stopped working on day two", "pointed at the cat with real conviction"],
    "gb_pocket": ["two AAA batteries, finally", "the screen you could actually read", "a link cable away from trading"],
    "tazo": ["bought the chips for the disc", "slammed on the patio until it chipped",
             "three normal ones for one shiny, no exceptions"],
    "tazo_chip_bag": ["the chips were a bonus", "shaken to find the disc before paying"],
    "tazo_tube": ["rattled in the backpack all of 1997", "the cap never stayed on"],
    "puff_bag": ["orange dust on the fingers, the controller, the couch", "eaten in the car on the way home"],
    "tazo_board": ["a round hole for every disc", "it was never full"],
    "glass_soda": ["mandarin, tamarind or lime, never the cola", "returned for the deposit, mostly"],
    "spam_can": ["in Seoul it comes in a gift box and nobody laughs", "fried, on rice, with an egg",
                 "the pull ring cut a thumb in 1993"],
    "spam_gift_box": ["the prestige holiday gift, honestly", "given to bosses, teachers and in-laws",
                      "the box with the handle was reused for years"],
    "gift_oil_bottle": ["wedged between the cans, every set", "nobody asked for it. everyone used it."],
    "songpyeon": ["pinched into half-moons by the whole family", "the ugly ones were yours",
                  "steamed on pine needles, a needle in every third bite"],
    "persimmon": ["left on the windowsill until it went soft", "the dried ones came on a string"],
    "asian_pear": ["the size of a softball", "foam net sock, kept for no reason"],
    "hwatu_cards": ["played on a blanket after the big dinner", "slapped down hard: that's the rule",
                    "one card always missing, replaced with a scrap of paper"],
    "yut_sticks": ["thrown high, counted fast", "the one with the X sends you back a step", "uncles argued about every throw"],
    "choco_pie_box": ["the heart on the box means affection, honest", "one in every lunchbox, every soldier's ration, every trip"],
    "banana_milk": ["bought at every bathhouse and every rest stop", "the jug shape that does not fit in a cupholder",
                    "pale yellow, because bananas are white inside"],
    "tango_football": ["twelve circles, made of triangles", "scuffed grey on the street, kept white in the box",
                       "signed by nobody, kicked by everybody"],
    "team_scarf": ["the chant spelled down the length", "worn in June, sweltering", "the tassels came off one by one"],
    "vuvuzela": ["one note, ninety minutes, a whole summer", "B-flat, they say", "the neighbors filed a complaint"],
    "air_horn": ["banned at the gate, smuggled in a sock", "used once, deafened a cousin"],
    "mascot_plush": ["our own mascot: a frog in a jersey", "won at a claw machine on the third try",
                     "the ball under its arm is glued on"],
    "flag_bunting": ["every country in the group, strung up off the shop front", "the paper ran in the rain"],
    "wallchart": ["free with the Sunday paper", "filled in with a pen until the team went out", "the knockout bracket left blank"],
}
