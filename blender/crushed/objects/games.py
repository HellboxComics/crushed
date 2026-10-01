"""Console wars: the consoles, controllers, handhelds and playground crazes of 1989-2008. Every shape evokes
the era; every name, emblem, creature and card back on them is our own parody."""
import math

import numpy as np

from .. import tex
from ..geo import ellipse, helix, rounded_rect
from . import BLACK, CHARCOAL, MET, P, PR, RUB, SILVER, T, WHITE, obj

SPECIAL = dict(group="special", eras=(0, 1, 2, 3))

N64_GREY = (0.33, 0.33, 0.35)
PS_GREY = (0.68, 0.68, 0.69)
INK = (0.05, 0.05, 0.06)


def _ch(rng, seq):
    return seq[int(rng.integers(0, len(seq)))]


# -- print helpers ------------------------------------------------------------------------------------

def _tw(c, s, size, spacing=1.0):
    return len(s) * 6 * (size / 7.0) * (c.h / c.w) * spacing


def _ct(c, s, cx, y, size, col, maxw=0.92, bold=True, spacing=1.0):
    """Centered text that shrinks to fit maxw."""
    w = _tw(c, s, size, spacing)
    if w > maxw:
        size *= maxw / w
        w = maxw
    c.text(s, cx - w / 2, y, size, col, spacing=spacing, bold=bold)
    return size


def _rainbow_text(c, s, cx, y, size, cols, maxw=0.9):
    w = _tw(c, s, size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    x = cx - w / 2
    step = w / len(s)
    for i, ch in enumerate(s):
        c.text(ch, x + i * step, y, size, cols[i % len(cols)], bold=True)


def _star(cx, cy, r, n=5, inner=0.45, rot=0.0, asp=1.0):
    pts = []
    for i in range(n * 2):
        a = rot + math.pi / 2 + math.pi * i / n
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a) / asp, cy + rr * math.sin(a)))
    return pts


def _critter(c, rng, cx, cy, r, body, kind=None):
    """An original pocket monster: a round body, ears or horns, big eyes, a tail. Never anybody's mascot."""
    asp = c.w / c.h
    kind = int(rng.integers(0, 4)) if kind is None else kind
    dark = tuple(v * 0.45 for v in body)
    if kind == 0:     # long-eared fire pig-rat with a flame tail
        c.poly([(cx - 0.6 * r / asp, cy + 0.5 * r), (cx - 0.9 * r / asp, cy + 1.6 * r), (cx - 0.15 * r / asp, cy + 0.8 * r)], dark)
        c.poly([(cx + 0.6 * r / asp, cy + 0.5 * r), (cx + 0.9 * r / asp, cy + 1.6 * r), (cx + 0.15 * r / asp, cy + 0.8 * r)], dark)
        c.poly(_star(cx + 1.25 * r / asp, cy + 0.2 * r, 0.5 * r, 6, 0.5, asp=asp), (1.0, 0.55, 0.05))
    elif kind == 1:   # a frog-blob with a shell spiral
        c.circle(cx - 0.55 * r / asp, cy + 0.85 * r, 0.32 * r, body)
        c.circle(cx + 0.55 * r / asp, cy + 0.85 * r, 0.32 * r, body)
    elif kind == 2:   # a leafy bulb on its back
        c.poly([(cx - 0.2 * r / asp, cy + 0.7 * r), (cx + 0.1 * r / asp, cy + 1.7 * r), (cx + 0.7 * r / asp, cy + 0.9 * r)],
               (0.15, 0.55, 0.2))
    else:             # zig-zag horns, bolt tail
        c.line([(cx - 0.4 * r / asp, cy + 0.7 * r), (cx - 0.7 * r / asp, cy + 1.2 * r), (cx - 0.45 * r / asp, cy + 1.35 * r),
                (cx - 0.8 * r / asp, cy + 1.75 * r)], 0.12 * r, dark)
        c.line([(cx + 0.4 * r / asp, cy + 0.7 * r), (cx + 0.7 * r / asp, cy + 1.2 * r), (cx + 0.45 * r / asp, cy + 1.35 * r),
                (cx + 0.8 * r / asp, cy + 1.75 * r)], 0.12 * r, dark)
        c.line([(cx + 0.9 * r / asp, cy - 0.2 * r), (cx + 1.3 * r / asp, cy + 0.3 * r), (cx + 1.15 * r / asp, cy + 0.5 * r),
                (cx + 1.6 * r / asp, cy + 0.9 * r)], 0.16 * r, (1.0, 0.85, 0.1))
    c.circle(cx, cy, r, body)
    c.circle(cx, cy - 0.35 * r, 0.55 * r, tuple(min(1, v * 0.6 + 0.45) for v in body))      # pale belly
    for sx in (-1, 1):
        c.circle(cx + sx * 0.38 * r / asp, cy + 0.22 * r, 0.24 * r, (1, 1, 1))
        c.circle(cx + sx * 0.33 * r / asp, cy + 0.2 * r, 0.14 * r, INK)
        c.circle(cx + sx * 0.3 * r / asp, cy + 0.26 * r, 0.05 * r, (1, 1, 1))
    c.line([(cx - 0.15 * r / asp, cy - 0.12 * r), (cx, cy - 0.2 * r), (cx + 0.15 * r / asp, cy - 0.12 * r)], 0.06 * r, INK)
    if kind == 1:
        c.circle(cx, cy - 0.35 * r, 0.3 * r, dark, ring=0.07 * r)


def _pixel_scene(rng, name, w=160, h=144, palette=None):
    """A handheld screen mid-game: tile floor, a hero sprite, a hit counter. All our own sprites."""
    palette = palette or [(0.78, 0.86, 0.42), (0.52, 0.66, 0.3), (0.25, 0.4, 0.2), (0.08, 0.16, 0.1)]
    c = tex.Canvas(w, h, (*palette[0], 1))
    kind = int(rng.integers(0, 3))
    if kind == 0:     # side-scroller
        for i in range(10):
            c.rect(i / 10, 0, i / 10 + 0.098, 0.12, palette[2])
            c.rect(i / 10 + 0.01, 0.12, i / 10 + 0.09, 0.15, palette[1])
        for i in range(3):
            x = float(rng.uniform(0.1, 0.9))
            c.rect(x, 0.35, x + 0.1, 0.42, palette[1])
        c.rect(0.2, 0.15, 0.28, 0.3, palette[3])
        c.circle(0.24, 0.34, 0.05, palette[3])
        c.circle(0.7, 0.2, 0.05, palette[2])
    elif kind == 1:   # monster battle
        c.circle(0.72, 0.68, 0.15, palette[3])
        c.circle(0.68, 0.72, 0.035, palette[0])
        c.rect(0.12, 0.25, 0.38, 0.45, palette[2])
        c.rect(0.05, 0.84, 0.5, 0.88, palette[3])
        c.rect(0.05, 0.84, 0.3, 0.88, palette[1])
        c.rect(0.0, 0.0, 1.0, 0.2, palette[0])
        c.rect(0.02, 0.02, 0.98, 0.18, palette[3], soft=0.0)
        c.rect(0.04, 0.04, 0.96, 0.16, palette[0])
        c.text("WILD MOANSTER APPEARED", 0.06, 0.145, 0.07, palette[3], spacing=0.95)
    else:             # falling blocks
        c.rect(0.25, 0.0, 0.75, 1.0, palette[1])
        for r in range(6):
            for k in range(10):
                if rng.random() < 0.75:
                    c.rect(0.25 + k * 0.05, r * 0.06, 0.25 + k * 0.05 + 0.046, r * 0.06 + 0.056, palette[3 - (r + k) % 2])
        c.rect(0.45, 0.7, 0.6, 0.756, palette[3])
        c.rect(0.5, 0.756, 0.55, 0.81, palette[3])
    c.text(f"{int(rng.integers(0, 99999)):05d}", 0.6, 0.97, 0.08, palette[3])
    return c.image(name)


def _color_scene(rng, name, w=192, h=144):
    pal = _ch(rng, [[(0.45, 0.75, 1.0), (0.3, 0.75, 0.25), (0.6, 0.35, 0.15), (0.1, 0.1, 0.2)],
                    [(0.15, 0.1, 0.3), (0.9, 0.3, 0.6), (0.3, 0.8, 0.9), (1.0, 1.0, 0.9)],
                    [(1.0, 0.85, 0.5), (0.95, 0.4, 0.1), (0.2, 0.55, 0.3), (0.1, 0.05, 0.1)]])
    return _pixel_scene(rng, name, w, h, pal)


def _badge(rng, name, text, bg, fg, w=256, h=48, rainbow=None):
    c = tex.Canvas(w, h, (*bg, 1))
    if rainbow:
        _rainbow_text(c, text, 0.5, 0.78, 0.56, rainbow)
    else:
        _ct(c, text, 0.5, 0.78, 0.56, fg)
    return c.image(name)


# -- cords --------------------------------------------------------------------------------------------

def _cord(b, rng, start, length, r, direction=(0, 1, 0), mat="cord", wig=0.02, n=14):
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    side = np.cross(d, (0, 0, 1))
    if np.linalg.norm(side) < 1e-6:
        side = np.array((1.0, 0, 0))
    side /= np.linalg.norm(side)
    pts = []
    ph = float(rng.uniform(0, 6))
    for i in range(n):
        t = i / (n - 1)
        p = (np.array(start) + d * length * t + side * wig * math.sin(ph + t * 7) * t
             + np.array((0, 0, 1.0)) * 0.004 * math.sin(ph * 2 + t * 5) * t)
        pts.append(tuple(float(v) for v in p))
    b.tube(pts, r, mat=mat, seg=8)
    return pts[-1]


# -- 64-BIT ERA ---------------------------------------------------------------------------------------

N64_GAMES = ["PERFECT DORK", "SMASH BRUHS", "WAVE RAVER 64", "TOO-ROCK: DINO HUNTED", "GOLDEN-I 00 SEVEN",
             "PARTY FOUL 64", "BANJO-KAZOO-WHO", "STAR FLOX 64", "BLAST CORPSE", "1080 SNOWBORED"]


def _cart_label(rng, name, title, w=256, h=200):
    hue = _ch(rng, [(0.85, 0.1, 0.1), (0.1, 0.3, 0.85), (0.1, 0.6, 0.2), (0.95, 0.65, 0.05), (0.5, 0.15, 0.7)])
    c = tex.Canvas(w, h, (*hue, 1))
    c.gradient(tuple(min(1, v + 0.25) for v in hue), tuple(v * 0.4 for v in hue))
    for _ in range(14):
        c.poly(_star(float(rng.uniform(0, 1)), float(rng.uniform(0.25, 0.8)), float(rng.uniform(0.02, 0.06)), asp=w / h),
               (1, 1, 1, 0.5))
    c.rect(0, 0.82, 1, 1, (0.05, 0.05, 0.05))
    _ct(c, "NINTENDON'T 64", 0.5, 0.96, 0.12, (1, 1, 1))
    _ct(c, title, 0.5, 0.55, 0.2, (1, 0.95, 0.2), maxw=0.9)
    c.rect(0, 0, 1, 0.12, (0.05, 0.05, 0.05))
    _ct(c, "MADE IN WHO KNOWS", 0.5, 0.1, 0.07, (0.8, 0.8, 0.8))
    return c.image(name)


@obj("console_64", eras=(1, 2), mass=1.1, weight=1.4, big=True)
def console_64(b, rng, pal):
    """The 64-bit grey slab: a raised spine with a cart slot, two sliders, four ports on the nose."""
    W, D, H = 0.26, 0.19, 0.045
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.01, seg=3)
    b.box((0.13, 0.15, 0.032), loc=(0, 0.015, H + 0.012), mat="body", bevel=0.012, seg=3)         # the spine
    for sx in (-1, 1):                                                                             # wing vents
        for i in range(6):
            b.box((0.05, 0.0035, 0.002), loc=(sx * 0.098, 0.05 - i * 0.012, H), mat="dark")
    top = H + 0.028
    b.box((0.095, 0.022, 0.004), loc=(0, 0.035, top), mat="dark", bevel=0.002)                     # cart slot
    b.box((0.103, 0.006, 0.004), loc=(0, 0.049, top + 0.001), mat="body", bevel=0.0015)
    b.box((0.103, 0.006, 0.004), loc=(0, 0.021, top + 0.001), mat="body", bevel=0.0015)
    for x, lab in ((-0.032, "s0"), (0.032, "s1")):                                                 # sliders
        b.box((0.026, 0.009, 0.002), loc=(x, -0.012, top), mat="dark")
        b.box((0.011, 0.012, 0.009), loc=(x - 0.006 if lab == "s0" else x + 0.006, -0.012, top + 0.003),
              mat=lab, bevel=0.002)
    b.box((0.09, 0.03, 0.002), loc=(0, -0.042, top - 0.001), mat="seam", bevel=0.004)             # expansion lid
    b.plane(0.1, 0.016, loc=(0, -0.077, H + 0.0004), mat="badge", cuts=2)
    for i in range(4):                                                                             # ports
        x = -0.084 + i * 0.056
        b.box((0.03, 0.006, 0.013), loc=(x, -D / 2 - 0.0005, 0.02), mat="port_rim", bevel=0.003)
        b.box((0.022, 0.006, 0.006), loc=(x, -D / 2 - 0.0015, 0.02), mat="dark", bevel=0.001)
    if rng.random() < 0.6:                                                                         # a cart left in
        b.box((0.09, 0.016, 0.06), loc=(0, 0.035, top + 0.03), mat="cart", bevel=0.004)
        for i in range(5):
            b.box((0.003, 0.017, 0.035), loc=(-0.035 + i * 0.006, 0.035, top + 0.035), mat="cart")
        b.plane(0.055, 0.042, loc=(0.012, 0.035 - 0.0085, top + 0.035), rot=(math.pi / 2, 0, 0), mat="label", cuts=2)
    body = rng.choice(4, p=[0.7, 0.1, 0.1, 0.1])
    bc = [N64_GREY, BLACK, None, None][body]
    bodym = P(bc, 0.5) if bc else T(_ch(rng, [(0.2, 0.5, 0.9), (0.5, 0.2, 0.8), (0.9, 0.3, 0.1)]), 0.15)
    rb = [(0.9, 0.1, 0.1), (0.1, 0.3, 0.9), (0.95, 0.75, 0.05), (0.1, 0.65, 0.2)]
    return {"body": bodym, "dark": P((0.03, 0.03, 0.035), 0.6), "seam": P(tuple(v * 0.85 for v in (bc or N64_GREY)), 0.5),
            "s0": P((0.2, 0.2, 0.22), 0.5), "s1": P((0.2, 0.2, 0.22), 0.5), "port_rim": P((0.2, 0.2, 0.21), 0.5),
            "badge": PR(_badge(rng, "n64badge", "NINTENDON'T 64", (0.1, 0.1, 0.11), (1, 1, 1), rainbow=rb), 0.4),
            "cart": P(N64_GREY, 0.5), "label": PR(_cart_label(rng, "n64cart", _ch(rng, N64_GAMES)), 0.35)}


@obj("trident_controller", eras=(1, 2), mass=0.2, weight=1.6)
def trident_controller(b, rng, pal):
    """Three handles, one stick dead center, a blue A, a green B and four yellow arrows."""
    t = 0.026
    b.extrude(rounded_rect(0.17, 0.062, 0.028, 6), t, loc=(0, 0.018, 0), mat="body", bevel=0.005)
    for x, ang in ((-0.068, -0.12), (0.0, 0.0), (0.068, 0.12)):
        poly = [(-0.017, 0.0), (0.017, 0.0), (0.015, -0.06), (0.011, -0.07), (0.0, -0.074), (-0.011, -0.07),
                (-0.015, -0.06)]
        b.extrude(poly, t * 0.92, loc=(x, 0.0, -0.001), rot=(0, 0, ang), mat="body", bevel=0.005)
    z = t / 2
    b.box((0.026, 0.009, 0.005), loc=(-0.066, 0.018, z + 0.002), mat="dark", bevel=0.0012)        # d-pad
    b.box((0.009, 0.026, 0.005), loc=(-0.066, 0.018, z + 0.002), mat="dark", bevel=0.0012)
    b.cyl(0.016, 0.003, loc=(-0.066, 0.018, z), mat="well", seg=24)
    b.cyl(0.014, 0.004, loc=(0, -0.012, z), mat="well", seg=24)                                    # the stick
    b.cyl(0.004, 0.012, loc=(0, -0.012, z + 0.006), mat="stick", seg=12)
    b.cyl(0.0095, 0.004, loc=(0, -0.012, z + 0.013), mat="stick", seg=20)
    for i in range(3):
        b.box((0.012, 0.0012, 0.001), loc=(0, -0.016 + i * 0.004, z + 0.0152), mat="well")
    b.cyl(0.0075, 0.006, loc=(0.054, 0.004, z + 0.001), mat="a", seg=20)                          # A
    b.cyl(0.0075, 0.006, loc=(0.042, 0.022, z + 0.001), mat="b", seg=20)                          # B
    for dx, dy in ((0, 0.011), (0, -0.011), (0.011, 0), (-0.011, 0)):                              # C x4
        b.cyl(0.0048, 0.006, loc=(0.072 + dx, 0.028 + dy, z + 0.001), mat="c", seg=14)
    b.cyl(0.0058, 0.005, loc=(0, 0.03, z + 0.001), mat="start", seg=18)
    for sx in (-1, 1):                                                                             # shoulders
        b.box((0.04, 0.008, 0.012), loc=(sx * 0.058, 0.049, 0.0), rot=(0, 0, -sx * 0.18), mat="shoulder", bevel=0.003)
    b.box((0.012, 0.016, 0.02), loc=(0, -0.034, -t / 2 - 0.006), mat="shoulder", bevel=0.003)    # Z trigger
    _cord(b, rng, (0, 0.05, 0), 0.25, 0.0022, (0.15, 1, 0))
    k = rng.choice(5, p=[0.62, 0.1, 0.1, 0.09, 0.09])
    body = [P((0.62, 0.62, 0.64), 0.45), P(BLACK, 0.45), T((0.2, 0.5, 0.95), 0.15), T((0.55, 0.15, 0.8), 0.15),
            P((0.95, 0.75, 0.1), 0.4)][k]
    return {"body": body, "dark": P((0.15, 0.15, 0.16), 0.45), "well": P((0.4, 0.4, 0.42), 0.5),
            "stick": P((0.5, 0.5, 0.52), 0.6), "a": P((0.1, 0.25, 0.85), 0.25, coat=0.6),
            "b": P((0.1, 0.6, 0.2), 0.25, coat=0.6), "c": P((0.98, 0.8, 0.05), 0.25, coat=0.6),
            "start": P((0.85, 0.1, 0.1), 0.25, coat=0.6), "shoulder": P((0.45, 0.45, 0.47), 0.5),
            "cord": P((0.3, 0.3, 0.32), 0.5)}


# -- HANDHELDS ----------------------------------------------------------------------------------------

GBC_COLORS = {"grape": (0.38, 0.12, 0.62), "teal": (0.05, 0.6, 0.6), "lime": (0.55, 0.85, 0.1),
              "berry": (0.85, 0.08, 0.3), "clear": (0.85, 0.87, 0.92)}


def _bezel(rng, name, title, w=256, h=240, bg=(0.18, 0.18, 0.24), sub=None):
    c = tex.Canvas(w, h, (*bg, 1))
    c.rect(0.06, 0.92, 0.6, 0.935, (0.6, 0.15, 0.4))
    c.rect(0.06, 0.94, 0.6, 0.955, (0.2, 0.3, 0.7))
    c.circle(0.08, 0.6, 0.025, (0.9, 0.1, 0.1))
    c.text("BATTERY", 0.03, 0.52, 0.035, (0.7, 0.7, 0.75))
    c.rect(0.15, 0.16, 0.85, 0.88, (0.02, 0.02, 0.03))
    _ct(c, title, 0.38 if sub else 0.5, 0.11, 0.06, (0.85, 0.85, 0.9), maxw=0.4 if sub else 0.7)
    if sub:
        _rainbow_text(c, sub, 0.72, 0.11, 0.06, [(0.9, 0.2, 0.2), (0.2, 0.6, 0.9), (0.95, 0.8, 0.1),
                                                 (0.3, 0.8, 0.3), (0.7, 0.3, 0.9)], maxw=0.25)
    return c.image(name)


def _gb_buttons(b, x, y, z, dz=0.003, mat_dpad="dpad", mat_btn="btn", bsp=(0.012, 0.007), r=0.0055):
    b.box((0.019, 0.0065, dz), loc=(x, y, z + dz / 2), mat=mat_dpad, bevel=0.001)
    b.box((0.0065, 0.019, dz), loc=(x, y, z + dz / 2), mat=mat_dpad, bevel=0.001)


@obj("pocket_handheld", eras=(1, 2), mass=0.14, weight=1.6)
def pocket_handheld(b, rng, pal):
    """The vertical pocket color handheld in see-through grape (or teal, lime, berry, clear)."""
    W, H, D = 0.078, 0.133, 0.027
    b.extrude(rounded_rect(W, H, 0.008, 4), D, mat="body", bevel=0.003)
    b.box((W - 0.012, H - 0.02, D - 0.008), mat="guts")                                            # see the board
    z = D / 2 + 0.0004
    b.plane(0.064, 0.058, loc=(0, 0.03, z), mat="bezel", cuts=2)
    b.plane(0.044, 0.04, loc=(0, 0.033, z + 0.0003), mat="lcd", cuts=2)
    _gb_buttons(b, -0.02, -0.025, D / 2)
    b.cyl(0.0057, 0.004, loc=(0.025, -0.019, D / 2 + 0.002), mat="btn", seg=18)
    b.cyl(0.0057, 0.004, loc=(0.011, -0.026, D / 2 + 0.002), mat="btn", seg=18)
    for x in (-0.008, 0.008):
        b.box((0.011, 0.003, 0.002), loc=(x, -0.046, D / 2 + 0.001), rot=(0, 0, 0.45), mat="dpad", bevel=0.0012)
    for i in range(6):                                                                             # speaker
        for j in range(3):
            b.cyl(0.001, 0.002, loc=(0.017 + i * 0.0035 - j * 0.0015, -0.055 + j * 0.0035, D / 2), mat="guts", seg=6)
    b.box((0.02, 0.004, 0.006), loc=(-0.024, H / 2, 0), mat="dpad", bevel=0.001)                  # power switch
    col = _ch(rng, list(GBC_COLORS))
    body = T(GBC_COLORS[col], 0.12) if col != "lime" or rng.random() < 0.5 else P(GBC_COLORS[col], 0.35)
    return {"body": body, "guts": P((0.06, 0.25, 0.12), 0.5),
            "bezel": PR(_bezel(rng, "gbcbez", "GAME BOI", sub="COLOR"), 0.3),
            "lcd": ("screen", {"image": _color_scene(rng, "gbcscr"), "glow": 0.25}),
            "dpad": P((0.08, 0.08, 0.1), 0.4),
            "btn": P(_ch(rng, [(0.35, 0.15, 0.45), (0.1, 0.1, 0.12), (0.8, 0.1, 0.25)]), 0.3)}


@obj("wide_handheld", eras=(2, 3), mass=0.14, weight=1.5)
def wide_handheld(b, rng, pal):
    """The landscape handheld: indigo, flared ends, two shoulder buttons."""
    W, H, D = 0.144, 0.082, 0.024
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        x, y = math.cos(a), math.sin(a)
        x = math.copysign(abs(x) ** 0.55, x) * W / 2
        y = y * H / 2 * (0.86 + 0.14 * abs(math.cos(a)))
        pts.append((x, y))
    b.extrude(pts, D, mat="body", bevel=0.004)
    z = D / 2 + 0.0004
    b.plane(0.078, 0.062, loc=(0, 0.004, z), mat="bezel", cuts=2)
    b.plane(0.06, 0.04, loc=(0, 0.007, z + 0.0003), mat="lcd", cuts=2)
    _gb_buttons(b, -0.053, 0.008, D / 2)
    b.cyl(0.0062, 0.004, loc=(0.06, 0.013, D / 2 + 0.002), mat="btn", seg=18)
    b.cyl(0.0062, 0.004, loc=(0.047, 0.002, D / 2 + 0.002), mat="btn", seg=18)
    for y in (-0.02, -0.03):
        b.cyl(0.0022, 0.002, loc=(-0.05, y, D / 2 + 0.001), mat="dpad", seg=10)
    for sx in (-1, 1):
        b.box((0.032, 0.008, 0.012), loc=(sx * 0.05, H / 2 - 0.004, 0.0), rot=(0, 0, -sx * 0.25), mat="shoulder",
              bevel=0.003)
        for i in range(3):
            b.box((0.0016, 0.012, 0.001), loc=(sx * (0.05 + i * 0.004), -0.026, D / 2), mat="dpad")
    col = rng.choice(5, p=[0.55, 0.15, 0.1, 0.1, 0.1])
    body = [P((0.25, 0.2, 0.55), 0.35), T((0.3, 0.25, 0.65), 0.12), P((0.75, 0.75, 0.78), 0.3),
            P((0.9, 0.45, 0.6), 0.35), T((0.85, 0.87, 0.92), 0.1)][col]
    return {"body": body, "bezel": PR(_bezel(rng, "gbabez", "GAME BOI ADVANSE", w=320, h=256), 0.3),
            "lcd": ("screen", {"image": _color_scene(rng, "gbascr", 240, 160), "glow": 0.25}),
            "dpad": P((0.08, 0.08, 0.1), 0.4), "btn": P((0.75, 0.75, 0.8), 0.3),
            "shoulder": P((0.55, 0.55, 0.62), 0.4)}


@obj("dual_screen_handheld", eras=(3,), mass=0.28, weight=1.4)
def dual_screen_handheld(b, rng, pal):
    """The silver clamshell, open, two screens, a stylus parked in the back."""
    W, Dp, t = 0.148, 0.084, 0.014
    b.extrude(rounded_rect(W, Dp, 0.012, 5), t, loc=(0, 0, t / 2), mat="body", bevel=0.003)
    z = t + 0.0004
    b.plane(0.072, 0.056, loc=(0, -0.002, z), mat="frame", cuts=2)
    b.plane(0.062, 0.047, loc=(0, -0.002, z + 0.0003), mat="lcd2", cuts=2)
    _gb_buttons(b, -0.056, 0.0, t)
    for dx, dy, k in ((0.0, 0.009, "x"), (0.0, -0.009, "b"), (0.009, 0, "a"), (-0.009, 0, "y")):
        b.cyl(0.0042, 0.004, loc=(0.056 + dx, dy, t + 0.002), mat="btn", seg=14)
    for y in (-0.02, -0.028):
        b.cyl(0.0022, 0.002, loc=(0.056, y, t + 0.001), mat="dpad", seg=10)
    b.cyl(0.0045, W * 0.86, loc=(0, Dp / 2, t + 0.002), rot=(0, math.pi / 2, 0), mat="hinge", seg=14)
    phi = math.radians(62)                                                                         # the lid, open
    hy, hz = Dp / 2, t + 0.002
    cy, cz = hy + Dp / 2 * math.cos(phi), hz + Dp / 2 * math.sin(phi)
    b.extrude(rounded_rect(W, Dp, 0.012, 5), 0.009, loc=(0, cy, cz), rot=(phi, 0, 0), mat="body", bevel=0.003)
    n = (0.0, -math.sin(phi), math.cos(phi))
    for off, w, h, m in ((0.0049, 0.076, 0.058, "frame"), (0.0053, 0.062, 0.047, "lcd1")):
        b.plane(w, h, loc=(0.0, cy + n[1] * off, cz + n[2] * off), rot=(phi, 0, 0), mat=m, cuts=2)
    b.plane(0.008, 0.008, loc=(0.0, cy + n[1] * 0.0049 + math.cos(phi) * 0.035, cz + n[2] * 0.0049 + math.sin(phi) * 0.035),
            rot=(phi, 0, 0), mat="dpad", cuts=1)
    col = _ch(rng, [SILVER, SILVER, (0.1, 0.1, 0.12), (0.92, 0.92, 0.94), (0.85, 0.4, 0.55), (0.2, 0.3, 0.6)])
    body = MET(col, 0.35) if col == SILVER else P(col, 0.25, coat=0.7)
    return {"body": body, "frame": P((0.08, 0.08, 0.09), 0.3), "hinge": P((0.2, 0.2, 0.22), 0.4),
            "lcd1": ("screen", {"image": _color_scene(rng, "ds1", 256, 192), "glow": 0.3}),
            "lcd2": ("screen", {"image": tex.screen(rng, "ds2", "blue"), "glow": 0.25}),
            "dpad": P((0.1, 0.1, 0.12), 0.4), "btn": P((0.85, 0.85, 0.88), 0.3)}


# -- DISC AND CUBE ERA --------------------------------------------------------------------------------

def _logo_disc(rng, name, text, bg, fg, mark="cube", w=256, h=256):
    c = tex.Canvas(w, h, (*bg, 1))
    if mark == "cube":
        c.poly([(0.5, 0.86), (0.78, 0.72), (0.5, 0.58), (0.22, 0.72)], fg)
        c.poly([(0.22, 0.68), (0.48, 0.55), (0.48, 0.3), (0.22, 0.43)], tuple(v * 0.8 for v in fg))
        c.poly([(0.52, 0.55), (0.78, 0.68), (0.78, 0.43), (0.52, 0.3)], tuple(v * 0.6 for v in fg))
        c.poly([(0.5, 0.74), (0.6, 0.69), (0.5, 0.64), (0.4, 0.69)], bg)
    elif mark == "pinwheel":
        for k in range(3):
            a = k * 2 * math.pi / 3
            pts = []
            for i in range(14):
                tt = i / 13
                r = 0.05 + 0.3 * tt
                aa = a + tt * 2.4
                pts.append((0.5 + r * math.cos(aa), 0.58 + r * math.sin(aa)))
            c.line(pts, 0.06 * (1.0), fg)
        c.circle(0.5, 0.58, 0.06, fg)
    _ct(c, text, 0.5, 0.2, 0.1, fg, maxw=0.9)
    return c.image(name)


@obj("cube_console", eras=(2, 3), mass=2.4, weight=1.4, big=True)
def cube_console(b, rng, pal):
    """The purple lunchbox: a cube, a round lid, a carry handle off the back."""
    W, D, H = 0.15, 0.16, 0.11
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.012, seg=3)
    b.cyl(0.058, 0.004, loc=(0, -0.008, H + 0.0005), mat="lid", seg=48)
    b.cyl(0.05, 0.002, loc=(0, -0.008, H + 0.003), mat="lid2", seg=48)
    b.plane(0.06, 0.06, loc=(0, -0.008, H + 0.0043), mat="logo", cuts=2)
    for sx in (-1, 1):                                                                             # handle
        b.box((0.012, 0.028, 0.016), loc=(sx * 0.058, D / 2 + 0.008, H - 0.012), mat="handle", bevel=0.004)
    b.tube([(-0.058, D / 2 + 0.02, H - 0.012), (-0.05, D / 2 + 0.034, H - 0.008), (0.05, D / 2 + 0.034, H - 0.008),
            (0.058, D / 2 + 0.02, H - 0.012)], 0.0085, mat="handle", seg=12)
    for i in range(4):                                                                             # ports
        x = -0.054 + i * 0.036
        b.box((0.024, 0.004, 0.022), loc=(x, -D / 2 - 0.001, 0.024), mat="dark", bevel=0.003)
        b.box((0.016, 0.004, 0.012), loc=(x, -D / 2 - 0.002, 0.024), mat="port", bevel=0.002)
    for i, x in enumerate((-0.035, 0.035)):                                                       # card flaps
        b.box((0.05, 0.003, 0.014), loc=(x, -D / 2 - 0.0005, 0.07), mat="dark", bevel=0.002)
    b.cyl(0.009, 0.004, loc=(-0.045, -0.035, H + 0.0015), mat="btn", seg=16)
    b.cyl(0.009, 0.004, loc=(0.045, -0.035, H + 0.0015), mat="btn", seg=16)
    k = rng.choice(4, p=[0.65, 0.15, 0.1, 0.1])
    bc = [(0.33, 0.22, 0.6), BLACK, SILVER, (0.95, 0.55, 0.1)][k]
    return {"body": P(bc, 0.3, coat=0.4), "lid": P(tuple(v * 0.75 for v in bc), 0.3),
            "lid2": P(tuple(v * 0.9 for v in bc), 0.25, coat=0.5), "handle": P(tuple(v * 0.8 for v in bc), 0.35),
            "logo": PR(_logo_disc(rng, "gclogo", "GAME CUBICLE", tuple(v * 0.9 for v in bc), (0.85, 0.85, 0.9)), 0.3),
            "dark": P((0.08, 0.06, 0.12), 0.5), "port": P((0.02, 0.02, 0.025), 0.6), "btn": P((0.75, 0.75, 0.78), 0.3)}


@obj("disc_console", eras=(1, 2), mass=1.5, weight=1.4, big=True)
def disc_console(b, rng, pal):
    """The grey disc box: a round lid on the left, three round buttons on the right."""
    W, D, H = 0.27, 0.188, 0.05
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.006, seg=3)
    b.box((W - 0.01, D - 0.04, 0.008), loc=(0, 0.01, H + 0.002), mat="body", bevel=0.004)
    cx = -0.035
    b.cyl(0.075, 0.003, loc=(cx, 0.012, H + 0.0062), mat="seam", seg=56)
    b.cyl(0.072, 0.004, loc=(cx, 0.012, H + 0.007), mat="body", seg=56)
    b.cyl(0.03, 0.001, loc=(cx, 0.012, H + 0.0092), mat="seam", seg=40)
    b.plane(0.12, 0.02, loc=(-0.06, -0.079, H + 0.0004), mat="logo", cuts=2)
    for i, (x, y) in enumerate(((0.09, 0.05), (0.09, -0.005), (0.09, -0.055))):
        b.cyl(0.0125, 0.004, loc=(x, y, H + 0.007), mat="btn" if i != 1 else "btn_open", seg=28)
    b.cyl(0.0025, 0.002, loc=(0.115, 0.05, H + 0.006), mat="led", seg=10)
    for i, x in enumerate((-0.07, 0.07)):                                                          # ports
        b.box((0.034, 0.006, 0.012), loc=(x, -D / 2 - 0.001, 0.016), mat="dark", bevel=0.002)
        b.box((0.03, 0.006, 0.004), loc=(x, -D / 2 - 0.001, 0.034), mat="dark", bevel=0.001)
    b.box((W, 0.004, 0.003), loc=(0, -D / 2 + 0.001, 0.026), mat="seam")
    led = (0.1, 0.9, 0.2) if rng.random() < 0.6 else (0.95, 0.2, 0.1)
    return {"body": P(PS_GREY, 0.42), "seam": P((0.52, 0.52, 0.54), 0.5), "btn": P((0.55, 0.55, 0.57), 0.4),
            "btn_open": P((0.58, 0.58, 0.6), 0.4), "dark": P((0.06, 0.06, 0.07), 0.5),
            "led": P(led, 0.3, glow=2.0),
            "logo": PR(_badge(rng, "pslogo", "PLAYSTATIONARY", PS_GREY, (0.15, 0.15, 0.17), w=320, h=64,
                              rainbow=[(0.9, 0.1, 0.1), (0.95, 0.75, 0.1), (0.1, 0.65, 0.3), (0.15, 0.3, 0.85)]), 0.4)}


def _twin_grip_shape(sc=1.0):
    pts = []
    n = 72
    for i in range(n):
        a = 2 * math.pi * i / n
        x = math.cos(a) * 0.078
        y = math.sin(a) * 0.03
        if y < 0:
            y *= 1.0 + 2.2 * math.exp(-(((abs(x) - 0.05) / 0.02) ** 2))
        pts.append((x * sc, y * sc))
    return pts


@obj("twin_grip_controller", eras=(1, 2), mass=0.2, weight=1.6)
def twin_grip_controller(b, rng, pal):
    """Grey, two long grips, two sticks low in the middle, four face buttons in a diamond."""
    t = 0.028
    b.extrude(_twin_grip_shape(), t, mat="body", bevel=0.006)
    z = t / 2
    for dx, dy in ((0, 0.009), (0, -0.009), (0.009, 0), (-0.009, 0)):                              # d-pad arrows
        rz = math.atan2(dy, dx)
        b.extrude([(0.0, -0.004), (0.009, -0.004), (0.012, 0.0), (0.009, 0.004), (0.0, 0.004)], 0.004,
                  loc=(-0.05 + dx * 0.35, 0.006 + dy * 0.35, z + 0.0015), rot=(0, 0, rz), mat="btn", bevel=0.0008)
    for i, (dx, dy) in enumerate(((0, 0.012), (0.012, 0), (0, -0.012), (-0.012, 0))):
        b.cyl(0.0056, 0.005, loc=(0.05 + dx, 0.006 + dy, z + 0.0015), mat=f"f{i}", seg=18)
    for sx in (-1, 1):
        b.cyl(0.013, 0.003, loc=(sx * 0.022, -0.02, z), mat="well", seg=24)
        b.cyl(0.0045, 0.01, loc=(sx * 0.022, -0.02, z + 0.005), mat="stick", seg=12)
        b.cyl(0.0105, 0.004, loc=(sx * 0.022, -0.02, z + 0.011), mat="stick", seg=24)
        b.torus(0.0085, 0.0012, loc=(sx * 0.022, -0.02, z + 0.013), mat="stick", seg=24, rseg=6)
        for k, dy in enumerate((0.0, 0.011)):
            b.box((0.026, 0.009, 0.008), loc=(sx * 0.05, 0.03 + dy * 0.3, -0.006 + k * 0.009), mat="shoulder",
                  bevel=0.003)
    b.box((0.008, 0.004, 0.003), loc=(-0.01, 0.008, z + 0.001), mat="btn", bevel=0.001)
    b.box((0.009, 0.005, 0.003), loc=(0.01, 0.008, z + 0.001), rot=(0, 0, 0), mat="btn", bevel=0.001)
    b.cyl(0.0035, 0.003, loc=(0, -0.008, z + 0.001), mat="well", seg=12)
    b.cyl(0.0015, 0.002, loc=(0, -0.0015, z + 0.001), mat="led", seg=8)
    _cord(b, rng, (0, 0.03, 0), 0.25, 0.0022, (-0.1, 1, 0))
    k = rng.choice(4, p=[0.65, 0.2, 0.08, 0.07])
    body = [P(PS_GREY, 0.45), P(BLACK, 0.4), T((0.3, 0.45, 0.85), 0.15), T((0.85, 0.87, 0.92), 0.1)][k]
    fc = [(0.1, 0.7, 0.35), (0.9, 0.15, 0.2), (0.25, 0.45, 0.95), (0.95, 0.45, 0.75)]
    m = {"body": body, "btn": P((0.4, 0.4, 0.42), 0.4), "well": P((0.12, 0.12, 0.13), 0.5),
         "stick": RUB((0.12, 0.12, 0.13)), "shoulder": P((0.5, 0.5, 0.52), 0.45),
         "led": P((1.0, 0.1, 0.05), 0.3, glow=2.5), "cord": P(BLACK, 0.5)}
    for i, col in enumerate(fc):
        m[f"f{i}"] = P(col, 0.3, coat=0.7)
    return m


@obj("slim_tower_console", eras=(2, 3), mass=2.2, weight=1.2, big=True, hero=(1, 0, 0))
def slim_tower_console(b, rng, pal):
    """The black monolith, standing up: half its side ribbed in parallel grooves, a tray seam, a blue badge."""
    Wx, Dy, Hz = 0.078, 0.18, 0.3
    b.box((Wx, Dy, Hz), loc=(0, 0, Hz / 2 + 0.012), mat="body", bevel=0.004, seg=2)
    b.box((0.1, 0.14, 0.012), loc=(0, 0, 0.006), mat="stand", bevel=0.004)                       # stand
    n = 16
    for i in range(n):                                                                            # the ribs
        z = 0.03 + i * 0.0085
        for sx in (-1, 1):
            b.box((0.003, Dy - 0.014, 0.004), loc=(sx * (Wx / 2 + 0.001), 0, z), mat="rib", bevel=0.0012)
    z0 = 0.03 + n * 0.0085 + 0.008
    b.plane(0.16, 0.035, loc=(Wx / 2 + 0.0006, 0, z0 + 0.03), rot=(math.pi / 2, 0, math.pi / 2), mat="logo", cuts=2)
    b.box((0.005, Dy - 0.01, 0.002), loc=(Wx / 2 + 0.0005, 0, z0 + 0.075), mat="gap")
    fy = -Dy / 2 - 0.0005                                                                          # the front
    b.box((0.003, 0.002, 0.24), loc=(0.01, fy, 0.16), mat="gap")                                  # tray seam
    b.box((0.012, 0.004, 0.008), loc=(-0.02, fy - 0.001, 0.29), mat="btn", bevel=0.002)
    b.box((0.012, 0.004, 0.008), loc=(-0.02, fy - 0.001, 0.275), mat="btn", bevel=0.002)
    b.plane(0.028, 0.028, loc=(-0.02, fy - 0.0012, 0.25), rot=(math.pi / 2, 0, 0), mat="badge", cuts=2)
    for z in (0.05, 0.09):                                                                         # ports
        b.box((0.03, 0.004, 0.012), loc=(-0.015, fy - 0.001, z), mat="gap", bevel=0.002)
    for z in (0.07, 0.11):
        b.box((0.008, 0.004, 0.03), loc=(0.024, fy - 0.001, z), mat="gap", bevel=0.001)
    blue = (0.15, 0.3, 0.9)
    bc = BLACK if rng.random() < 0.85 else (0.75, 0.76, 0.8)
    c = tex.Canvas(64, 64, (*bc, 1))
    c.rect(0.15, 0.15, 0.85, 0.85, blue)
    _ct(c, "2", 0.5, 0.75, 0.5, (1, 1, 1))
    return {"body": P(bc, 0.25, coat=0.5), "rib": P(tuple(v * 1.6 + 0.03 for v in bc), 0.3, coat=0.5),
            "stand": P((0.08, 0.08, 0.12), 0.4), "gap": P((0.01, 0.01, 0.012), 0.6),
            "btn": P((0.3, 0.3, 0.6), 0.3, glow=0.8), "badge": PR(c.image("ps2badge"), 0.3, glow=0.6),
            "logo": PR(_badge(rng, "ps2logo", "PLAYSTATIONARY 2", bc, (0.55, 0.6, 0.75), w=384, h=64), 0.3)}


def _jewel(rng, name, w=128, h=128):
    c = tex.Canvas(w, h, (0.05, 0.25, 0.05, 1))
    for i in range(12):
        t = i / 11
        c.circle(0.5, 0.5, 0.5 - 0.4 * t, (0.15 + 0.35 * t, 0.55 + 0.45 * t, 0.1 + 0.2 * t))
    # our own mark: a crossed hourglass of two fat chevrons
    for sx in (-1, 1):            # our own mark: four fangs aimed at an eye, not anybody's letter
        for sy in (-1, 1):
            bx, by = 0.5 + sx * 0.15, 0.5 + sy * 0.15
            px, py = -sy * 0.06, sx * 0.06
            c.poly([(0.5 + sx * 0.37, 0.5 + sy * 0.37), (bx + px, by + py), (bx - px, by - py)], (0.02, 0.06, 0.02))
    c.circle(0.5, 0.5, 0.09, (0.02, 0.06, 0.02))
    c.circle(0.5, 0.5, 0.04, (0.7, 1.0, 0.5))
    return c.image(name)


@obj("big_x_console", eras=(2, 3), mass=3.8, weight=1.2, big=True)
def big_x_console(b, rng, pal):
    """The huge black box with the crossed channel on top and the green glowing jewel."""
    W, D, H = 0.32, 0.26, 0.09
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.02, seg=4)
    for ang in (math.atan2(D, W), -math.atan2(D, W)):                                              # crossed ridges
        L = math.hypot(W, D) * 0.88
        b.box((L, 0.03, 0.012), loc=(0, 0, H + 0.002), rot=(0, 0, ang), mat="ridge", bevel=0.005)
    b.cyl(0.042, 0.016, loc=(0, 0, H + 0.004), mat="ridge", seg=40)
    b.cyl(0.034, 0.008, loc=(0, 0, H + 0.014), mat="jewel_rim", seg=40)
    b.lathe([(0.0, 0.0), (0.03, 0.0), (0.029, 0.004), (0.02, 0.009), (0.0, 0.011)], loc=(0, 0, H + 0.017),
            mat="jewel", seg=40)
    b.plane(0.034, 0.034, loc=(0, 0, H + 0.0285), mat="mark", cuts=2)
    fy = -D / 2 - 0.001
    b.box((0.16, 0.004, 0.006), loc=(0.02, fy, 0.065), mat="gap", bevel=0.002)                    # tray
    b.box((0.11, 0.006, 0.026), loc=(0.02, fy - 0.0015, 0.05), mat="tray", bevel=0.003)
    b.plane(0.08, 0.014, loc=(0.02, fy - 0.0048, 0.05), rot=(math.pi / 2, 0, 0), mat="logo", cuts=2)
    for i in range(4):
        x = -0.12 + i * 0.08
        b.box((0.032, 0.006, 0.016), loc=(x, fy, 0.018), mat="gap", bevel=0.003)
    for x in (-0.13, -0.105):
        b.cyl(0.008, 0.006, loc=(x, fy, 0.055), rot=(math.pi / 2, 0, 0), mat="btn", seg=16)
    return {"body": P((0.03, 0.03, 0.035), 0.3, coat=0.4), "ridge": P((0.06, 0.06, 0.07), 0.35, coat=0.4),
            "jewel_rim": MET((0.35, 0.35, 0.37), 0.3), "jewel": T((0.2, 0.9, 0.15), 0.05),
            "mark": PR(_jewel(rng, "xjewel"), 0.2, glow=2.0), "gap": P((0.005, 0.005, 0.006), 0.6),
            "tray": P((0.1, 0.1, 0.11), 0.3), "btn": P((0.15, 0.15, 0.16), 0.3),
            "logo": PR(_badge(rng, "xlogo", "X-BAWKS", (0.1, 0.1, 0.11), (0.35, 0.95, 0.25), w=192, h=40), 0.3,
                       glow=0.6)}


@obj("giant_controller", eras=(2, 3), mass=0.35, weight=1.3)
def giant_controller(b, rng, pal):
    """The brick: the biggest controller ever made, jewel in the middle, six face buttons."""
    t = 0.04
    pts = []
    n = 80
    for i in range(n):
        a = 2 * math.pi * i / n
        x = math.cos(a) * 0.12
        y = math.sin(a) * 0.05
        if y < 0:
            y *= 1.0 + 1.5 * math.exp(-(((abs(x) - 0.075) / 0.03) ** 2))
        pts.append((x, y))
    b.extrude(pts, t, mat="body", bevel=0.01)
    z = t / 2
    b.cyl(0.024, 0.006, loc=(0, 0.002, z + 0.001), mat="jewel_rim", seg=32)
    b.plane(0.034, 0.034, loc=(0, 0.002, z + 0.0042), mat="mark", cuts=2)
    for sx, sy in ((-0.068, 0.012), (0.035, -0.035)):                                             # sticks
        b.cyl(0.017, 0.003, loc=(sx, sy, z), mat="well", seg=24)
        b.cyl(0.005, 0.012, loc=(sx, sy, z + 0.006), mat="stick", seg=12)
        b.cyl(0.014, 0.005, loc=(sx, sy, z + 0.013), mat="stick", seg=24)
    b.cyl(0.017, 0.003, loc=(-0.035, -0.035, z), mat="well", seg=24)                              # d-pad
    b.box((0.026, 0.008, 0.005), loc=(-0.035, -0.035, z + 0.003), mat="dpad", bevel=0.0015)
    b.box((0.008, 0.026, 0.005), loc=(-0.035, -0.035, z + 0.003), mat="dpad", bevel=0.0015)
    for i, (x, y) in enumerate(((0.07, 0.024), (0.087, 0.012), (0.053, 0.012), (0.07, 0.0))):     # Y B X A
        b.cyl(0.0085, 0.006, loc=(x, y, z + 0.002), mat=f"f{i}", seg=20)
    b.cyl(0.006, 0.006, loc=(0.1, -0.008, z), mat="white", seg=16)
    b.cyl(0.006, 0.006, loc=(0.085, -0.02, z), mat="blackb", seg=16)
    for sx in (-1, 1):
        b.box((0.03, 0.012, 0.022), loc=(sx * 0.075, 0.045, -0.008), rot=(0, 0, -sx * 0.25), mat="dpad", bevel=0.004)
    _cord(b, rng, (0, 0.05, 0), 0.25, 0.0028, (0, 1, 0))
    k = rng.choice(3, p=[0.8, 0.1, 0.1])
    body = [P((0.03, 0.03, 0.035), 0.35), T((0.15, 0.6, 0.2), 0.15), P((0.2, 0.25, 0.4), 0.35)][k]
    m = {"body": body, "jewel_rim": MET((0.35, 0.35, 0.37), 0.3), "mark": PR(_jewel(rng, "dukejewel"), 0.2, glow=2.0),
         "well": P((0.08, 0.08, 0.09), 0.5), "stick": RUB((0.12, 0.12, 0.13)), "dpad": P((0.12, 0.12, 0.13), 0.4),
         "white": P((0.95, 0.95, 0.95), 0.3), "blackb": P((0.02, 0.02, 0.02), 0.3), "cord": P(BLACK, 0.5)}
    for i, col in enumerate([(0.95, 0.8, 0.1), (0.9, 0.15, 0.1), (0.15, 0.35, 0.9), (0.15, 0.75, 0.2)]):
        m[f"f{i}"] = T(col, 0.08)
    return m


@obj("swirl_console", eras=(2,), mass=1.5, weight=1.2, big=True)
def swirl_console(b, rng, pal):
    """The white rounded box with the orange pinwheel on its lid: dead too soon."""
    W, D, H = 0.19, 0.195, 0.07
    b.extrude(rounded_rect(W, D, 0.03, 6), H, loc=(0, 0, H / 2), mat="body", bevel=0.012)
    b.cyl(0.07, 0.003, loc=(0, 0.015, H + 0.0002), mat="seam", seg=56)
    b.cyl(0.068, 0.004, loc=(0, 0.015, H + 0.001), mat="body", seg=56)
    b.plane(0.06, 0.06, loc=(0, 0.015, H + 0.0032), mat="logo", cuts=2)
    b.cyl(0.009, 0.003, loc=(-0.07, -0.065, H + 0.001), mat="btn", seg=16)
    b.cyl(0.009, 0.003, loc=(0.07, -0.065, H + 0.001), mat="btn", seg=16)
    b.cyl(0.0025, 0.002, loc=(-0.07, -0.08, H + 0.0005), mat="led", seg=8)
    for i in range(4):
        x = -0.06 + i * 0.04
        b.box((0.028, 0.004, 0.022), loc=(x, -D / 2 - 0.001, 0.025), mat="port", bevel=0.003)
    b.plane(0.12, 0.016, loc=(0, -D / 2 - 0.0012, 0.055), rot=(math.pi / 2, 0, 0), mat="word", cuts=2)
    orange = (1.0, 0.45, 0.05)
    return {"body": P((0.93, 0.93, 0.91), 0.35), "seam": P((0.7, 0.7, 0.7), 0.5), "btn": P((0.8, 0.8, 0.8), 0.35),
            "led": P(orange, 0.3, glow=2.0), "port": P((0.1, 0.1, 0.11), 0.5),
            "logo": PR(_logo_disc(rng, "dclogo", "", (0.93, 0.93, 0.91), orange, mark="pinwheel"), 0.3),
            "word": PR(_badge(rng, "dcword", "WETDREAMCAST", (0.93, 0.93, 0.91), (0.2, 0.2, 0.25), w=320, h=48), 0.35)}


@obj("vmu_controller", eras=(2,), mass=0.25, weight=1.2)
def vmu_controller(b, rng, pal):
    """White, rounded, a memory card with its own little screen jammed in the top, cord out the bottom."""
    t = 0.035
    pts = []
    n = 64
    for i in range(n):
        a = 2 * math.pi * i / n
        x = math.cos(a) * 0.075
        y = math.sin(a) * 0.05
        if y < 0:
            y *= 1.0 + 0.9 * math.exp(-(((abs(x) - 0.05) / 0.025) ** 2))
            x *= 1.0 - 0.15 * (-y / 0.09)
        pts.append((x, y))
    b.extrude(pts, t, mat="body", bevel=0.008)
    z = t / 2
    b.box((0.045, 0.06, 0.012), loc=(0, 0.01, z + 0.003), mat="dark", bevel=0.002)                 # VMU slot
    b.box((0.04, 0.052, 0.008), loc=(0, 0.012, z + 0.008), mat="vmu", bevel=0.004)
    b.plane(0.026, 0.02, loc=(0, 0.02, z + 0.0122), mat="lcd", cuts=2)
    b.box((0.008, 0.003, 0.002), loc=(-0.008, -0.004, z + 0.0125), mat="dark")
    b.box((0.003, 0.008, 0.002), loc=(-0.008, -0.004, z + 0.0125), mat="dark")
    b.cyl(0.013, 0.003, loc=(-0.05, 0.012, z), mat="well", seg=24)                                 # stick
    b.cyl(0.0105, 0.006, loc=(-0.05, 0.012, z + 0.004), mat="well", seg=24, r2=0.009)
    b.box((0.022, 0.007, 0.004), loc=(-0.05, -0.022, z + 0.001), mat="dpad", bevel=0.001)
    b.box((0.007, 0.022, 0.004), loc=(-0.05, -0.022, z + 0.001), mat="dpad", bevel=0.001)
    for i, (x, y) in enumerate(((0.05, 0.022), (0.062, 0.01), (0.038, 0.01), (0.05, -0.002))):
        b.cyl(0.0058, 0.005, loc=(x, y, z + 0.001), mat=f"f{i}", seg=18)
    b.cyl(0.004, 0.003, loc=(0.0, -0.035, z), mat="dpad", rot=(0, 0, 0), seg=12)
    _cord(b, rng, (0, -0.065, -0.005), 0.22, 0.0022, (0.1, -1, 0))
    c = tex.Canvas(96, 64, (0.62, 0.72, 0.6, 1))
    c.text(_ch(rng, ["SAVE 1", "BLOCK 99", "FEED ME", "NO SAVE", "CHAO?"]), 0.06, 0.85, 0.22, (0.08, 0.12, 0.08))
    c.circle(0.5, 0.25, 0.14, (0.08, 0.12, 0.08), ring=0.03)
    m = {"body": P((0.93, 0.93, 0.91), 0.35), "dark": P((0.15, 0.15, 0.17), 0.5), "vmu": P((0.9, 0.9, 0.88), 0.3),
         "lcd": PR(c.image("vmulcd"), 0.2), "well": P((0.6, 0.6, 0.62), 0.5), "dpad": P((0.2, 0.2, 0.22), 0.4),
         "cord": P((0.85, 0.85, 0.85), 0.5)}
    for i, col in enumerate([(0.95, 0.8, 0.1), (0.15, 0.35, 0.9), (0.15, 0.7, 0.25), (0.9, 0.15, 0.15)]):
        m[f"f{i}"] = P(col, 0.3, coat=0.7)
    return m


@obj("console_16bit", eras=(0, 1), mass=1.3, weight=1.4, big=True)
def console_16bit(b, rng, pal):
    """The black 16-bit slab: the big round well in the middle and the lettering stamped into it."""
    W, D, H = 0.28, 0.21, 0.05
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.01, seg=3)
    b.cyl(0.085, 0.006, loc=(0.0, 0.0, H + 0.0015), mat="ring", seg=64)
    b.cyl(0.08, 0.006, loc=(0.0, 0.0, H + 0.0025), mat="body", seg=64)
    b.plane(0.11, 0.11, loc=(0, 0, H + 0.0056), mat="dial", cuts=2)
    b.box((0.08, 0.012, 0.004), loc=(0, 0.0, H + 0.006), mat="slot", bevel=0.002)                 # cart slot
    for i in range(12):                                                                            # side ribs
        b.box((0.03, 0.002, 0.0015), loc=(-0.115, 0.07 - i * 0.012, H), mat="ring")
    b.box((0.025, 0.007, 0.002), loc=(-0.11, -0.08, H), mat="slot")
    b.box((0.012, 0.012, 0.008), loc=(-0.115, -0.08, H + 0.003), mat="power", bevel=0.002)
    b.box((0.016, 0.01, 0.006), loc=(0.11, -0.08, H + 0.002), mat="power", bevel=0.002)
    b.plane(0.06, 0.016, loc=(0.1, 0.085, H + 0.0004), mat="word", cuts=2)
    for x in (-0.05, 0.05):
        b.box((0.03, 0.006, 0.015), loc=(x, -D / 2 - 0.001, 0.025), mat="slot", bevel=0.003)
    if rng.random() < 0.5:
        b.box((0.08, 0.022, 0.07), loc=(0, 0.0, H + 0.038), mat="cart", bevel=0.004)
        b.plane(0.06, 0.05, loc=(0, -0.0115, H + 0.042), rot=(math.pi / 2, 0, 0), mat="label", cuts=2)
    c = tex.Canvas(256, 256, (0.03, 0.03, 0.035, 1))
    for k in range(3):
        _ct(c, "16-BIT", 0.5 + 0.006 * k, 0.9 - 0.006 * k, 0.2,
            [(0.3, 0.3, 0.32), (0.6, 0.6, 0.62), (0.92, 0.92, 0.94)][k], maxw=0.92, spacing=1.15)
    _ct(c, "HIGH DEFINITION GRAPHIC", 0.5, 0.16, 0.07, (0.75, 0.75, 0.78), maxw=0.92)
    w = tex.Canvas(192, 48, (0.03, 0.03, 0.035, 1))
    _ct(w, "DEGENESIS", 0.5, 0.8, 0.55, (0.9, 0.9, 0.92))
    return {"body": P((0.03, 0.03, 0.035), 0.35), "ring": P((0.12, 0.12, 0.13), 0.4), "slot": P((0.0, 0.0, 0.0), 0.6),
            "dial": PR(c.image("gen16"), 0.35), "word": PR(w.image("genword"), 0.35),
            "power": P((0.85, 0.1, 0.1), 0.35), "cart": P((0.05, 0.05, 0.055), 0.4),
            "label": PR(_cart_label(rng, "gencart", _ch(rng, ["SONNY THE HEDGE FUND", "STREETS OF RAGEQUIT",
                                                               "MORTAL KOMBUCHA", "ALTERED BEAST MODE", "TOE JAM & EARWAX"])),
                        0.35)}


# -- POCKET MONSTERS ----------------------------------------------------------------------------------

MONSTER_VERSIONS = {"RED": (0.85, 0.1, 0.1), "BLUE": (0.12, 0.3, 0.85), "YELLOW": (0.98, 0.82, 0.1)}


@obj("monster_cart", eras=(1, 2), mass=0.03, weight=1.6)
def monster_cart(b, rng, pal):
    """The little grey cart, clipped corner, label in red, blue or yellow."""
    W, H, D = 0.057, 0.065, 0.008
    poly = [(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2 - 0.006), (W / 2 - 0.006, H / 2), (-W / 2, H / 2)]
    b.extrude(poly, D, mat="body", bevel=0.001)
    for i in range(5):
        b.box((W - 0.012, 0.0012, 0.0008), loc=(-0.003, H / 2 - 0.004 - i * 0.0025, D / 2), mat="body")
    b.plane(0.047, 0.042, loc=(0, -0.008, D / 2 + 0.0004), mat="label", cuts=2)
    b.extrude([(-0.004, 0), (0.004, 0), (0, -0.004)], 0.001, loc=(0, -H / 2 + 0.0035, D / 2), mat="dark")
    ver = _ch(rng, list(MONSTER_VERSIONS))
    col = MONSTER_VERSIONS[ver]
    c = tex.Canvas(192, 176, (*col, 1))
    c.rect(0.04, 0.04, 0.96, 0.96, tuple(min(1, v * 1.15 + 0.05) for v in col))
    c.rect(0, 0.74, 1, 1, (0.1, 0.15, 0.45))
    _ct(c, "POCKET", 0.5, 0.97, 0.11, (1.0, 0.85, 0.1))
    _ct(c, "MOANSTERS", 0.5, 0.86, 0.11, (1.0, 0.85, 0.1))
    _critter(c, rng, 0.5, 0.42, 0.17, tuple(v * 0.6 + 0.2 for v in col[::-1]))
    c.rect(0, 0.0, 1, 0.14, (1, 1, 1))
    _ct(c, f"{ver} VERSION", 0.5, 0.11, 0.08, col if ver != "YELLOW" else (0.6, 0.45, 0.0))
    return {"body": P((0.55, 0.55, 0.57), 0.5), "dark": P((0.2, 0.2, 0.22), 0.5), "label": PR(c.image("pmcart"), 0.3)}


MONSTER_NAMES = ["FLAMBOAR", "DRIPTOAD", "MOSSQUITO", "ZAPOSSUM", "GRUMBLEAF", "SOGGYMANDER", "VOLTERRIER",
                 "SPROUTLE", "CINDERAT", "BUBBLEBUTT"]
TYPES = [((0.95, 0.45, 0.15), "FIRE"), ((0.25, 0.55, 0.95), "WATER"), ((0.3, 0.75, 0.25), "GRASS"),
         ((0.98, 0.85, 0.15), "ZAP")]


def _monster_front(rng, name):
    c = tex.Canvas(252, 352, (0.98, 0.85, 0.15, 1))
    tcol, tname = _ch(rng, TYPES)
    c.rect(0.05, 0.035, 0.95, 0.965, tcol)
    c.rect(0.05, 0.035, 0.95, 0.965, (1, 1, 1, 0.25))
    c.text(_ch(rng, MONSTER_NAMES), 0.08, 0.95, 0.032, INK, bold=True)
    hp = int(rng.integers(3, 13)) * 10
    c.text(f"{hp} HP", 0.68, 0.95, 0.03, (0.8, 0.05, 0.05), bold=True)
    c.circle(0.9, 0.935, 0.025, tcol)
    c.circle(0.9, 0.935, 0.025, INK, ring=0.004)
    c.rect(0.1, 0.52, 0.9, 0.9, (0.75, 0.6, 0.15))
    c.rect(0.115, 0.53, 0.885, 0.89, (0.9, 0.95, 1.0))
    c.rect(0.115, 0.53, 0.885, 0.62, tuple(v * 0.6 + 0.35 for v in tcol))
    _critter(c, rng, 0.5, 0.68, 0.09, tcol)
    for k, y in enumerate((0.45, 0.32)):
        for e in range(k + 1):
            c.circle(0.12 + e * 0.07, y - 0.015, 0.022, tcol)
            c.circle(0.12 + e * 0.07, y - 0.015, 0.022, INK, ring=0.003)
        c.text(_ch(rng, ["TACKLE", "BODY SLAM", "EMBER", "SPLASH", "LEECH", "SHOCK", "SULK", "NAP", "GRIFT", "RUG PULL"]),
               0.3, y, 0.028, INK, bold=True)
        c.text(str(int(rng.integers(1, 9)) * 10), 0.82, y, 0.03, INK, bold=True)
        c.rect(0.1, y - 0.06, 0.9, y - 0.055, (0.3, 0.3, 0.3))
    c.text("WEAKNESS   RESIST   RETREAT", 0.08, 0.14, 0.018, INK)
    c.text("1ST EDITION? NO.", 0.08, 0.08, 0.018, (0.3, 0.3, 0.3))
    if rng.random() < 0.3:                                                     # holo shimmer
        for i in range(8):
            c.rect(0.115, 0.53 + i * 0.045, 0.885, 0.55 + i * 0.045, (0.7, 0.9, 1.0, 0.25))
    return c.image(name)


def _monster_back(rng, name):
    c = tex.Canvas(252, 352, (0.1, 0.25, 0.65, 1))
    for _ in range(40):
        c.circle(float(rng.uniform(0, 1)), float(rng.uniform(0, 1)), float(rng.uniform(0.03, 0.1)),
                 (0.25, 0.45, 0.9, 0.35))
    c.rect(0.04, 0.03, 0.96, 0.97, (0.05, 0.15, 0.45), soft=0.0)
    c.rect(0.06, 0.045, 0.94, 0.955, (0.15, 0.35, 0.8))
    for _ in range(30):
        c.circle(float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.02, 0.07)),
                 (0.3, 0.55, 0.95, 0.4))
    c.poly(_star(0.5, 0.5, 0.3, 8, 0.6, asp=252 / 352), (0.98, 0.8, 0.1))
    c.poly(_star(0.5, 0.5, 0.25, 8, 0.6, asp=252 / 352), (0.95, 0.25, 0.1))
    _ct(c, "POCKET", 0.5, 0.58, 0.05, (1.0, 0.92, 0.2), maxw=0.6)
    _ct(c, "MOANSTERS", 0.5, 0.5, 0.05, (1.0, 0.92, 0.2), maxw=0.6)
    _ct(c, "TRADING CARD GAME-ISH", 0.5, 0.42, 0.022, (1, 1, 1), maxw=0.6)
    return c.image(name)


def _card(b, rng, w, h, front, back, bend=0.004):
    rz = float(rng.normal(0, 0.15))
    rows_f, rows_b = [], []
    n = 6
    for j in range(n):
        y = -h / 2 + h * j / (n - 1)
        rf, rb = [], []
        for i in range(n):
            x = -w / 2 + w * i / (n - 1)
            z = bend * (1 - (2 * j / (n - 1) - 1) ** 2)
            rf.append((x, y, z + 0.0002))
            rb.append((-x, y, z - 0.0002))
        rows_f.append(rf)
        rows_b.append(rb)
    b.loft(rows_f, mat=front, closed=False, cap=False, rot=(0, 0, rz))
    b.loft(rows_b, mat=back, closed=False, cap=False, rot=(0, 0, rz))


@obj("monster_card", eras=(1, 2), mass=0.002, weight=1.8)
def monster_card(b, rng, pal):
    """A pocket-moanster trading card: yellow border, HP, energy pips, our own critter. Blue back."""
    _card(b, rng, 0.063, 0.088, "front", "back")
    return {"front": PR(_monster_front(rng, "pmfront"), 0.35), "back": PR(_monster_back(rng, "pmback"), 0.4)}


@obj("monster_dex", eras=(1, 2), mass=0.12, weight=1.2)
def monster_dex(b, rng, pal):
    """The red flip-open monster encyclopedia toy: big blue lens, three little lights, a screen, a lid."""
    W, H, D = 0.075, 0.115, 0.02
    b.extrude(rounded_rect(W, H, 0.006, 4), D, mat="body", bevel=0.003)
    z = D / 2
    b.box((W - 0.004, 0.02, 0.004), loc=(0, H / 2 - 0.012, z + 0.001), mat="body", bevel=0.002)
    b.cyl(0.0125, 0.004, loc=(-0.022, H / 2 - 0.013, z + 0.002), mat="white", seg=28)
    b.cyl(0.0098, 0.004, loc=(-0.022, H / 2 - 0.013, z + 0.004), mat="lens", seg=28)
    b.sphere(0.004, loc=(-0.025, H / 2 - 0.01, z + 0.006), mat="glint", seg=8)
    for i, m in enumerate(("l0", "l1", "l2")):
        b.cyl(0.0028, 0.003, loc=(0.0 + i * 0.008, H / 2 - 0.008, z + 0.003), mat=m, seg=10)
    b.plane(0.052, 0.044, loc=(0, 0.005, z + 0.0004), mat="frame", cuts=2)
    b.plane(0.04, 0.032, loc=(0.002, 0.007, z + 0.0007), mat="lcd", cuts=2)
    b.box((0.016, 0.005, 0.003), loc=(0.02, -0.038, z + 0.001), mat="dark", bevel=0.001)
    b.box((0.005, 0.016, 0.003), loc=(0.02, -0.038, z + 0.001), mat="dark", bevel=0.001)
    b.cyl(0.0045, 0.003, loc=(-0.022, -0.035, z + 0.001), mat="dark", seg=12)
    b.box((0.012, 0.003, 0.002), loc=(-0.005, -0.03, z + 0.001), mat="green", bevel=0.001)
    b.box((0.012, 0.003, 0.002), loc=(-0.005, -0.04, z + 0.001), mat="orange", bevel=0.001)
    b.cyl(0.004, H * 0.9, loc=(W / 2 + 0.002, 0, 0), rot=(math.pi / 2, 0, 0), mat="hinge", seg=12)
    lw = W * 0.95
    lx = W / 2 + 0.004 + lw / 2
    b.extrude(rounded_rect(lw, H * 0.92, 0.006, 4), 0.008, loc=(lx, -0.004, -0.003), rot=(0, -0.12, 0),
              mat="body", bevel=0.002)
    b.plane(0.05, 0.022, loc=(lx, 0.02, 0.0017 - 0.006 * 0.12), rot=(0, -0.12, 0), mat="lcd2", cuts=2)
    for r in range(2):
        for k in range(5):
            b.box((0.0085, 0.0065, 0.002), loc=(lx - 0.02 + k * 0.01, -0.012 - r * 0.009,
                                               0.0015 - (k * 0.01 - 0.02) * 0.12), rot=(0, -0.12, 0),
                  mat="keys", bevel=0.001)
    c = tex.Canvas(160, 128, (0.55, 0.85, 0.5, 1))
    _critter(c, rng, 0.45, 0.5, 0.22, (0.4, 0.4, 0.45))
    c.text(f"NO.{int(rng.integers(1, 151)):03d}", 0.05, 0.95, 0.1, INK)
    c2 = tex.Canvas(160, 64, (0.1, 0.15, 0.1, 1))
    c2.text(_ch(rng, MONSTER_NAMES), 0.05, 0.85, 0.25, (0.4, 1.0, 0.4))
    c2.text("SEEN 149  OWN 3", 0.05, 0.4, 0.2, (0.4, 1.0, 0.4))
    return {"body": P((0.85, 0.08, 0.08), 0.3, coat=0.6), "white": P((0.95, 0.95, 0.95), 0.3),
            "lens": T((0.2, 0.6, 1.0), 0.05), "glint": P((1, 1, 1), 0.1), "l0": P((0.95, 0.1, 0.1), 0.3, glow=1.0),
            "l1": P((0.98, 0.85, 0.1), 0.3, glow=1.0), "l2": P((0.2, 0.85, 0.2), 0.3, glow=1.0),
            "frame": P((0.9, 0.9, 0.9), 0.4), "lcd": ("screen", {"image": c.image("dexscr"), "glow": 0.2}),
            "lcd2": PR(c2.image("dexscr2"), 0.2, glow=0.4), "dark": P((0.08, 0.08, 0.1), 0.4),
            "green": P((0.15, 0.7, 0.2), 0.4), "orange": P((0.95, 0.5, 0.1), 0.4), "hinge": P((0.6, 0.05, 0.05), 0.35),
            "keys": P((0.2, 0.45, 0.85), 0.35)}


# -- DUEL CARDS ---------------------------------------------------------------------------------------

DUEL_NAMES = ["BLUE-EYED WHITE CLAW", "DARK MAGICIAN'T", "CELTIC GUARDIAN-ISH", "SUMMONED SKULLET", "EXODIA'S LEFT SOCK",
              "BABY DRAGONITE", "HARPIE'S OTHER SISTER", "MIRROR FORCE QUIT", "POT OF GREED-ISH", "TIME WIZARD OF OZZY"]


def _duel_front(rng, name):
    c = tex.Canvas(252, 368, (0.82, 0.55, 0.2, 1))
    kind = rng.random()
    frame = (0.82, 0.55, 0.2) if kind < 0.5 else ((0.3, 0.55, 0.45) if kind < 0.75 else (0.65, 0.3, 0.45))
    c.rect(0, 0, 1, 1, frame)
    c.rect(0.06, 0.88, 0.94, 0.96, (0.95, 0.9, 0.8))
    c.text_fit(_ch(rng, DUEL_NAMES), 0.08, 0.945, 0.74, 0.04, INK, bold=True)
    c.circle(0.89, 0.92, 0.03, (0.4, 0.1, 0.5))
    stars = int(rng.integers(3, 9))
    for i in range(stars):
        c.circle(0.86 - i * 0.075, 0.845, 0.028, (0.85, 0.15, 0.05))
        c.poly(_star(0.86 - i * 0.075, 0.845, 0.024, asp=252 / 368), (1.0, 0.85, 0.2))
    c.rect(0.1, 0.36, 0.9, 0.8, (0.25, 0.2, 0.15))
    c.rect(0.115, 0.37, 0.885, 0.79, (0.18, 0.08, 0.3))
    for _ in range(8):
        c.circle(float(rng.uniform(0.15, 0.85)), float(rng.uniform(0.4, 0.75)), float(rng.uniform(0.01, 0.04)),
                 (0.6, 0.4, 0.9, 0.5))
    # an original wyrm: a sweep of horns and a gaping jaw
    c.poly([(0.3, 0.45), (0.5, 0.72), (0.7, 0.45), (0.6, 0.5), (0.5, 0.58), (0.4, 0.5)], (0.8, 0.85, 0.9))
    c.poly([(0.42, 0.66), (0.33, 0.77), (0.46, 0.7)], (0.95, 0.9, 0.7))
    c.poly([(0.58, 0.66), (0.67, 0.77), (0.54, 0.7)], (0.95, 0.9, 0.7))
    c.circle(0.46, 0.6, 0.015, (0.2, 0.6, 1.0))
    c.circle(0.54, 0.6, 0.015, (0.2, 0.6, 1.0))
    c.rect(0.06, 0.06, 0.94, 0.33, (0.95, 0.9, 0.8))
    c.text("( DRAGON / EFFECT )", 0.08, 0.31, 0.025, INK)
    for i in range(4):
        c.rect(0.08, 0.26 - i * 0.04, float(rng.uniform(0.6, 0.92)), 0.265 - i * 0.04, (0.4, 0.38, 0.35))
    c.rect(0.06, 0.1, 0.94, 0.104, INK)
    atk, dfn = int(rng.integers(5, 31)) * 100, int(rng.integers(5, 26)) * 100
    c.text(f"ATK/{atk} DEF/{dfn}", 0.4, 0.09, 0.025, INK, bold=True)
    return c.image(name)


def _duel_back(rng, name):
    c = tex.Canvas(252, 368, (0.35, 0.2, 0.08, 1))
    c.gradient((0.45, 0.28, 0.12), (0.25, 0.13, 0.05))
    asp = 252 / 368
    for arm in range(2):
        pts = []
        for i in range(160):
            t = i / 159
            a = arm * math.pi + t * 6 * math.pi
            r = 0.02 + 0.55 * t
            pts.append((0.5 + r * math.cos(a) / asp * 0.7, 0.5 + r * math.sin(a)))
        c.line(pts, 0.025, (0.12, 0.06, 0.02))
        c.line(pts, 0.008, (0.6, 0.4, 0.15))
    c.circle(0.5, 0.5, 0.17, (0.08, 0.04, 0.02))
    c.circle(0.5, 0.5, 0.17, (0.75, 0.55, 0.2), ring=0.012)
    _ct(c, "DUEL", 0.5, 0.56, 0.05, (0.95, 0.75, 0.2), maxw=0.4)
    _ct(c, "MONSTAHS", 0.5, 0.48, 0.035, (0.95, 0.75, 0.2), maxw=0.42)
    c.rect(0, 0, 1, 0.025, (0.1, 0.05, 0.02))
    c.rect(0, 0.975, 1, 1, (0.1, 0.05, 0.02))
    c.rect(0, 0, 0.03, 1, (0.1, 0.05, 0.02))
    c.rect(0.97, 0, 1, 1, (0.1, 0.05, 0.02))
    return c.image(name)


@obj("duel_card", eras=(2, 3), mass=0.002, weight=1.6, hero=(0, 0, -1))
def duel_card(b, rng, pal):
    """A duel-monstahs card: stars, ATK/DEF, and the brown spiral back everyone knows from across a cafeteria."""
    _card(b, rng, 0.059, 0.086, "front", "back")
    return {"front": PR(_duel_front(rng, "ygofront"), 0.35), "back": PR(_duel_back(rng, "ygoback"), 0.4)}


# -- PLAYGROUND -------------------------------------------------------------------------------------

def _spiky(n, r0, r1, jag=0.35):
    pts = []
    for i in range(n * 3):
        a = 2 * math.pi * i / (n * 3)
        k = i % 3
        r = r1 if k == 0 else (r0 if k == 2 else r0 + (r1 - r0) * jag)
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


@obj("battle_top", eras=(2, 3), mass=0.05, weight=1.5)
def battle_top(b, rng, pal):
    """The battle top: a sharp tip, a heavy disc, a jagged attack ring, a printed chip on top."""
    b.lathe([(0.0, 0.0), (0.003, 0.001), (0.006, 0.008), (0.014, 0.012), (0.016, 0.016), (0.0, 0.016)],
            mat="tip", seg=24)
    b.lathe([(0.0, 0.016), (0.03, 0.016), (0.032, 0.02), (0.03, 0.024), (0.0, 0.024)], mat="disc", seg=40)
    b.extrude(_spiky(int(rng.integers(3, 7)), 0.024, 0.038, float(rng.uniform(0.2, 0.6))), 0.008,
              loc=(0, 0, 0.028), mat="ring", bevel=0.001)
    b.cyl(0.016, 0.006, loc=(0, 0, 0.034), mat="cap", seg=32)
    b.plane(0.022, 0.022, loc=(0, 0, 0.0372), mat="chip", cuts=2)
    c = tex.Canvas(96, 96, (0.05, 0.05, 0.08, 1))
    c.circle(0.5, 0.5, 0.48, _ch(rng, [(0.9, 0.2, 0.1), (0.1, 0.4, 0.95), (0.95, 0.75, 0.1), (0.2, 0.8, 0.3)]))
    beast = int(rng.integers(0, 3))
    if beast == 0:
        c.poly(_star(0.5, 0.5, 0.36, 4, 0.3), (1, 1, 1))
    elif beast == 1:
        c.poly([(0.2, 0.3), (0.5, 0.85), (0.8, 0.3), (0.5, 0.45)], (1, 1, 1))
    else:
        c.poly([(0.15, 0.5), (0.5, 0.8), (0.85, 0.5), (0.5, 0.2)], (1, 1, 1))
        c.circle(0.5, 0.5, 0.1, (0.05, 0.05, 0.08))
    ring = _ch(rng, [MET((0.75, 0.75, 0.78), 0.25), ("gold", {"rough": 0.25}), P((0.85, 0.1, 0.1), 0.25),
                     T((0.1, 0.5, 0.95), 0.1), P((0.1, 0.1, 0.12), 0.25)])
    return {"tip": P(_ch(rng, [(0.95, 0.85, 0.2), WHITE, (0.1, 0.1, 0.12)]), 0.35), "disc": MET((0.55, 0.55, 0.58), 0.3),
            "ring": ring, "cap": P(_ch(rng, [WHITE, (0.1, 0.1, 0.12), (0.2, 0.4, 0.9)]), 0.3),
            "chip": PR(c.image("beychip"), 0.3)}


@obj("ripcord_launcher", eras=(2, 3), mass=0.06, weight=1.3)
def ripcord_launcher(b, rng, pal):
    """The launcher: a toothed rip-cord half pulled out, the T-handle on the end."""
    b.cyl(0.024, 0.016, loc=(0, 0, 0), mat="body", seg=32)
    b.box((0.05, 0.022, 0.016), loc=(-0.03, 0, 0), mat="body", bevel=0.004)
    b.extrude([(-0.012, 0.0), (0.012, 0.0), (0.016, -0.05), (-0.008, -0.05)], 0.014, loc=(-0.05, -0.01, 0),
              rot=(0, 0, 0.3), mat="grip", bevel=0.003)
    b.cyl(0.016, 0.004, loc=(0, 0, 0.009), mat="dark", seg=24)
    for k in range(3):
        a = k * 2 * math.pi / 3
        b.box((0.006, 0.003, 0.004), loc=(0.012 * math.cos(a), 0.012 * math.sin(a), 0.011), rot=(0, 0, a), mat="body")
    L = float(rng.uniform(0.09, 0.15))
    teeth = []
    n = int(L / 0.005)
    for i in range(n):
        x = 0.02 + i * L / n
        teeth += [(x, 0.0), (x + L / n * 0.5, 0.003)]
    poly = [(0.02, -0.006)] + [(0.02 + L, -0.006)] + [(0.02 + L, 0.0)] + list(reversed(teeth))
    b.extrude(poly, 0.002, loc=(0, 0.004, 0), mat="cord", bevel=0.0003)
    b.box((0.008, 0.04, 0.008), loc=(0.024 + L, 0.001, 0), mat="handle", bevel=0.003)
    b.plane(0.04, 0.014, loc=(-0.032, 0, 0.0082), mat="label", cuts=2)
    col = _ch(rng, [(0.1, 0.4, 0.95), (0.9, 0.15, 0.1), (0.95, 0.75, 0.1), (0.15, 0.15, 0.17)])
    c = tex.Canvas(160, 56, (*col, 1))
    _ct(c, "BAYBLADED", 0.5, 0.8, 0.55, (1, 1, 1))
    return {"body": P(col, 0.35), "grip": P(tuple(v * 0.6 for v in col), 0.5), "dark": P((0.1, 0.1, 0.12), 0.4),
            "cord": P(_ch(rng, [WHITE, (0.95, 0.85, 0.2), (0.1, 0.1, 0.12)]), 0.4),
            "handle": P(_ch(rng, [(0.95, 0.85, 0.2), (0.9, 0.15, 0.1), WHITE]), 0.35),
            "label": PR(c.image("baylab"), 0.35)}


def _deck_rows(L, W, kick=0.006, n=24, k=7, z=0.0, inset=0.0):
    rows = []
    for j in range(n):
        u = j / (n - 1)
        x = -L / 2 + L * u
        e = abs(2 * u - 1)
        lift = kick * max(0.0, (e - 0.72) / 0.28) ** 1.6
        half = W / 2 - inset
        if e > 0.86:                                       # round nose and tail
            half *= math.sqrt(max(0.05, 1 - ((e - 0.86) / 0.14) ** 2))
        rows.append([(x, -half + 2 * half * i / (k - 1), z + lift) for i in range(k)])
    return rows


@obj("finger_skateboard", eras=(2, 3), mass=0.01, weight=1.4, hero=(0, 0, -1))
def finger_skateboard(b, rng, pal):
    """A finger board: kicked nose and tail, tiny trucks, a real printed graphic underneath."""
    L, W, t = 0.096, 0.026, 0.0016
    top = _deck_rows(L, W, z=t / 2)
    bot = _deck_rows(L, W, z=-t / 2)
    b.loft(top, mat="grip", closed=False, cap=False)
    b.loft([list(reversed(r)) for r in bot], mat="graphic", closed=False, cap=False)
    for sgn in (-1, 1):
        rows = []
        for rt, rb in zip(top, bot):
            pt = rt[0] if sgn < 0 else rt[-1]
            pb = rb[0] if sgn < 0 else rb[-1]
            rows.append([pb, pt])
        b.loft(rows, mat="ply", closed=False, cap=False)
    for x in (-0.032, 0.032):
        b.box((0.006, 0.014, 0.004), loc=(x, 0, -t / 2 - 0.002), mat="truck", bevel=0.001)
        b.cyl(0.0015, 0.03, loc=(x, 0, -t / 2 - 0.0045), rot=(math.pi / 2, 0, 0), mat="truck", seg=8)
        for sy in (-1, 1):
            b.cyl(0.0032, 0.0035, loc=(x, sy * 0.0135, -t / 2 - 0.0045), rot=(math.pi / 2, 0, 0), mat="wheel", seg=14)
    c = tex.Canvas(384, 112, (*_ch(rng, [(0.95, 0.85, 0.2), (0.15, 0.15, 0.2), (0.9, 0.2, 0.2), (0.2, 0.6, 0.9),
                                          (0.95, 0.95, 0.95)]), 1))
    ink = _ch(rng, [(0.9, 0.1, 0.4), (0.1, 0.1, 0.1), (0.2, 0.85, 0.3), (1.0, 0.55, 0.1)])
    kind = int(rng.integers(0, 3))
    if kind == 0:
        for i in range(6):
            c.poly([(0.1 + i * 0.14, 0.1), (0.17 + i * 0.14, 0.9), (0.24 + i * 0.14, 0.1)], ink)
    elif kind == 1:
        c.circle(0.5, 0.5, 0.35, ink)
        c.circle(0.46, 0.58, 0.07, (1, 1, 1))
        c.circle(0.54, 0.58, 0.07, (1, 1, 1))
        c.rect(0.47, 0.25, 0.53, 0.33, (1, 1, 1))
    else:
        c.gradient(ink, (0.1, 0.1, 0.15))
        c.poly(_star(0.5, 0.5, 0.4, 5, 0.45, asp=384 / 112), (1, 1, 1))
    _ct(c, _ch(rng, ["TECH DECKED", "FINGERBANGERS", "BLIND-ISH", "BIRDHOUSE PARTY", "WORLD INDUSTRIAL"]),
        0.5, 0.3, 0.2, (1, 1, 1) if kind != 1 else INK, maxw=0.7)
    g = tex.Canvas(64, 64, (0.06, 0.06, 0.07, 1))
    g.noise(rng, 0.05)
    return {"grip": PR(g.image("fbgrip"), 0.9), "graphic": PR(c.image("fbgfx"), 0.35), "ply": P((0.75, 0.6, 0.4), 0.6),
            "truck": MET((0.7, 0.7, 0.72), 0.3), "wheel": P(_ch(rng, [WHITE, (0.95, 0.85, 0.2), (0.9, 0.2, 0.2)]), 0.4)}


def _pog_art(rng, name, size=128):
    c = tex.Canvas(size, size, (*_ch(rng, [(0.95, 0.85, 0.2), (0.1, 0.1, 0.15), (0.9, 0.2, 0.3), (0.15, 0.6, 0.85),
                                           (0.3, 0.8, 0.3)]), 1))
    ink = _ch(rng, [(1, 1, 1), (0.05, 0.05, 0.05), (0.95, 0.3, 0.6), (1.0, 0.6, 0.1)])
    k = int(rng.integers(0, 4))
    if k == 0:                     # yin-yang-ish swirl
        c.circle(0.5, 0.5, 0.42, ink)
        c.poly([(0.5, 0.08), (0.92, 0.5), (0.5, 0.92)], tuple(1 - v for v in ink))
        c.circle(0.5, 0.29, 0.21, ink)
        c.circle(0.5, 0.71, 0.21, tuple(1 - v for v in ink))
    elif k == 1:                   # 8-ball
        c.circle(0.5, 0.5, 0.42, (0.03, 0.03, 0.03))
        c.circle(0.5, 0.55, 0.18, (1, 1, 1))
        _ct(c, "8", 0.5, 0.67, 0.22, (0.03, 0.03, 0.03))
    elif k == 2:                   # skull
        c.circle(0.5, 0.56, 0.3, ink)
        c.rect(0.36, 0.2, 0.64, 0.36, ink)
        for x in (0.4, 0.6):
            c.circle(x, 0.56, 0.08, (0.05, 0.05, 0.05))
    else:                          # a slogan
        c.circle(0.5, 0.5, 0.42, ink, ring=0.05)
        _ct(c, _ch(rng, ["NO FEAR-ISH", "SLAMMED", "DA BOMB", "AS IF", "PHAT", "BOO-YAH"]), 0.5, 0.56, 0.12,
            ink, maxw=0.7)
    c.circle(0.5, 0.5, 0.47, (0.05, 0.05, 0.05), ring=0.03)
    return c.image(name)


@obj("pog_slammer", eras=(1,), mass=0.03, weight=1.4)
def pog_slammer(b, rng, pal):
    """The heavy metal slammer: a thick disc with a raised rim and a stamped design."""
    r = 0.022
    b.lathe([(0.0, 0.0), (r - 0.001, 0.0), (r, 0.001), (r, 0.004), (r - 0.0025, 0.005), (r - 0.003, 0.0038),
             (0.0, 0.0038)], mat="metal", seg=48)
    b.plane(r * 1.7, r * 1.7, loc=(0, 0, 0.0039), mat="art", cuts=2)
    kind = int(rng.integers(0, 3))
    if kind == 0:
        return {"metal": ("chrome", {}), "art": PR(_pog_art(rng, "slam"), 0.2, metal=0.9)}
    if kind == 1:
        return {"metal": ("gold", {"rough": 0.25}), "art": PR(_pog_art(rng, "slam"), 0.25, metal=0.7)}
    return {"metal": P(_ch(rng, [(0.05, 0.05, 0.05), (0.9, 0.2, 0.3), (0.2, 0.4, 0.9)]), 0.3),
            "art": PR(_pog_art(rng, "slam"), 0.3)}


@obj("pog_tube", eras=(1,), mass=0.08, weight=1.2, hero=(0, -1, 0))
def pog_tube(b, rng, pal):
    """A clear tube of pogs, colored caps, the top pog showing its art."""
    R, L = 0.022, 0.11
    rot = (0, math.pi / 2, 0)
    b.lathe([(R, -L / 2), (R, L / 2)], rot=rot, mat="tube", seg=40)
    b.lathe([(R * 0.98, -L / 2 + 0.004), (R * 0.98, L / 2 - 0.004)], rot=rot, mat="tube", seg=40)
    for sx in (-1, 1):
        b.lathe([(0.0, 0.0), (R + 0.002, 0.0), (R + 0.002, 0.008), (R * 0.9, 0.009), (0.0, 0.009)],
                loc=(sx * (L / 2 + 0.004), 0, 0), rot=(0, sx * math.pi / 2, 0), mat="cap", seg=40)
    n = int(rng.integers(30, 50))
    for i in range(n):
        x = -L / 2 + 0.003 + i * (L - 0.006) / n
        b.cyl(R * 0.94, 0.0015, loc=(x, 0, 0), rot=rot, mat=f"edge{i % 3}", seg=24)
    b.lathe([(R + 0.0006, -0.022), (R + 0.0006, 0.022)], rot=(0, math.pi / 2, 0), mat="band", seg=40)
    c = tex.Canvas(256, 96, (0.1, 0.1, 0.15, 1))
    for i in range(10):
        c.circle(0.05 + i * 0.1, 0.5, 0.08, _ch(rng, [(0.9, 0.2, 0.3), (0.95, 0.85, 0.2), (0.2, 0.6, 0.9)]),
                 ring=0.04)
    c.rect(0, 0.3, 1, 0.7, (0.95, 0.85, 0.2))
    _ct(c, "POGFED OFFICIAL MILKCAPS", 0.25, 0.62, 0.22, (0.85, 0.1, 0.2), maxw=0.48)
    _ct(c, "POGFED OFFICIAL MILKCAPS", 0.75, 0.62, 0.22, (0.85, 0.1, 0.2), maxw=0.48)
    m = {"tube": T((0.88, 0.9, 0.95), 0.05), "cap": P(_ch(rng, [(0.9, 0.2, 0.3), (0.2, 0.4, 0.9), (0.95, 0.75, 0.1),
                                                                (0.3, 0.8, 0.3)]), 0.3),
         "band": PR(c.image("pogband"), 0.35)}
    for i in range(3):
        m[f"edge{i}"] = ("cardboard", {"color": _ch(rng, [(0.95, 0.9, 0.8), (0.9, 0.85, 0.75), (0.8, 0.75, 0.65)])})
    return m


# -- CONSOLE WARS (one-of-one extras) -----------------------------------------------------------------

@obj("av_cable", mass=0.12, weight=1.0, **SPECIAL)
def av_cable(b, rng, pal):
    """Red, white, yellow: the three plugs, the split, the flat multi-out on the other end."""
    hub = (0.0, 0.0, 0.0)
    for i, (m, dy) in enumerate((("red", -0.014), ("white", 0.0), ("yellow", 0.014))):
        tip = (-0.09 + float(rng.normal(0, 0.006)), dy * 1.6, 0.0)
        b.tube([(tip[0] + 0.022, tip[1], 0), (-0.04, dy * 1.2, 0.002), (-0.015, dy * 0.4, 0.001), hub], 0.0018,
               mat="lead", seg=8)
        b.cyl(0.0042, 0.02, loc=(tip[0] + 0.012, tip[1], 0), rot=(0, math.pi / 2, 0), mat=m, seg=16)
        b.cyl(0.0035, 0.008, loc=(tip[0], tip[1], 0), rot=(0, math.pi / 2, 0), mat="metal", seg=14)
        b.cyl(0.0012, 0.008, loc=(tip[0] - 0.008, tip[1], 0), rot=(0, math.pi / 2, 0), mat="metal", seg=8)
    b.cyl(0.005, 0.014, loc=(0.005, 0, 0), rot=(0, math.pi / 2, 0), mat="lead", seg=14)
    end = _cord(b, rng, (0.012, 0, 0), 0.11, 0.0028, (1, 0.2, 0), mat="lead", wig=0.03)
    b.box((0.012, 0.032, 0.009), loc=(end[0] + 0.006, end[1], end[2]), mat="plug", bevel=0.002)
    b.box((0.006, 0.026, 0.004), loc=(end[0] + 0.014, end[1], end[2]), mat="metal")
    return {"red": P((0.85, 0.08, 0.08), 0.3), "white": P((0.95, 0.95, 0.95), 0.3), "yellow": P((0.98, 0.8, 0.05), 0.3),
            "metal": MET((0.85, 0.82, 0.7), 0.2), "lead": P(BLACK, 0.45), "plug": P((0.1, 0.1, 0.11), 0.4)}


@obj("memory_card_stack", mass=0.03, weight=1.0, **SPECIAL)
def memory_card_stack(b, rng, pal):
    """A small stack of labeled memory cards, one of them holding a 60-hour save nobody backed up."""
    n = int(rng.integers(3, 6))
    poly = [(-0.026, -0.03), (0.026, -0.03), (0.026, 0.026), (0.02, 0.03), (-0.026, 0.03)]
    m = {}
    for i in range(n):
        rz = float(rng.normal(0, 0.35))
        loc = (float(rng.normal(0, 0.008)), float(rng.normal(0, 0.008)), i * 0.0062)
        b.extrude(poly, 0.0058, loc=loc, rot=(0, 0, rz), mat=f"c{i}", bevel=0.0008)
        b.plane(0.044, 0.03, loc=(loc[0], loc[1], loc[2] + 0.003), rot=(0, 0, rz), mat=f"l{i}", cuts=2)
        bc = _ch(rng, [PS_GREY, PS_GREY, (0.08, 0.08, 0.1), (0.85, 0.15, 0.15), (0.2, 0.35, 0.85)])
        m[f"c{i}"] = P(bc, 0.4) if rng.random() < 0.8 else T((0.3, 0.6, 0.95), 0.12)
        c = tex.Canvas(176, 120, (*bc, 1))
        c.rect(0.05, 0.08, 0.95, 0.92, (0.95, 0.95, 0.95))
        _ct(c, "MEMORY CARD", 0.5, 0.85, 0.14, INK, maxw=0.85)
        _ct(c, _ch(rng, ["1 MEG", "8 MB", "15 BLOCKS", "59 BLOCKS"]), 0.5, 0.62, 0.12, (0.8, 0.1, 0.1))
        c.scribble(rng, 0.1, 0.3, 0.85, 0.02, (0.1, 0.2, 0.7), 0.04)
        c.text(_ch(rng, ["DONT TOUCH", "MIKES", "FF7 DISC 3", "100% SAVE", "BROS SAVES"]), 0.1, 0.24, 0.1,
               (0.1, 0.2, 0.7))
        m[f"l{i}"] = PR(c.image(f"memlab{i}"), 0.4)
    return m


GAME_TITLES = ["GRAND THEFT AUTOPILOT", "FINAL FANTASIZE VII", "METAL GEAR STOLID", "PRO SKATER 2 (NOT TONY)",
               "MADDENING 2002", "HALLO: COMBAT DEVOLVED", "RESIDENT EVIL-ISH", "CRASH BANDIPOO", "GRAN TURISMOVE",
               "SPYRO THE DRAGGIN'"]


def _box_art(rng, name, title, w=256, h=360, brand="PLAYSTATIONARY 2", band=(0.05, 0.1, 0.3)):
    c = tex.Canvas(w, h, (0.1, 0.1, 0.12, 1))
    top = _ch(rng, [(0.9, 0.4, 0.1), (0.2, 0.3, 0.8), (0.5, 0.1, 0.6), (0.1, 0.5, 0.3), (0.85, 0.1, 0.15)])
    c.gradient(top, (0.02, 0.02, 0.04))
    for _ in range(6):
        x = float(rng.uniform(0.1, 0.9))
        c.poly([(x - 0.2, 0.15), (x, float(rng.uniform(0.4, 0.75))), (x + 0.2, 0.15)], (0, 0, 0, 0.45))
    c.circle(0.5, 0.42, 0.12, (0.05, 0.05, 0.06))
    c.poly([(0.38, 0.1), (0.5, 0.32), (0.62, 0.1)], (0.05, 0.05, 0.06))
    c.circle(0.46, 0.44, 0.02, (1.0, 0.85, 0.2))
    c.circle(0.54, 0.44, 0.02, (1.0, 0.85, 0.2))
    c.rect(0, 0.9, 1, 1, band)
    _ct(c, brand, 0.5, 0.975, 0.045, (1, 1, 1), maxw=0.9)
    words = title.split(" ")
    mid = (len(words) + 1) // 2
    _ct(c, " ".join(words[:mid]), 0.5, 0.86, 0.09, (1.0, 0.92, 0.3), maxw=0.92)
    if words[mid:]:
        _ct(c, " ".join(words[mid:]), 0.5, 0.75, 0.07, (1, 1, 1), maxw=0.92)
    c.rect(0.04, 0.02, 0.2, 0.1, (1, 1, 1))
    _ct(c, "M", 0.12, 0.09, 0.06, INK)
    c.text("MATURE-ISH 17+", 0.24, 0.07, 0.025, (0.9, 0.9, 0.9))
    return c.image(name)


@obj("game_case", mass=0.1, weight=1.0, **SPECIAL)
def game_case(b, rng, pal):
    """A black disc case with the sleeve art, and the disc half slid out of it."""
    W, H, D = 0.135, 0.19, 0.014
    b.box((W, H, D), mat="case", bevel=0.002)
    b.box((0.006, H, D + 0.001), loc=(-W / 2 + 0.003, 0, 0), mat="spine", bevel=0.001)
    b.plane(W - 0.012, H - 0.008, loc=(0.002, 0, D / 2 + 0.0005), mat="art", cuts=2)
    if rng.random() < 0.7:
        b.cyl(0.06, 0.0012, loc=(W / 2 + 0.01, -0.02, -0.002), mat="disc", seg=48)
        b.plane(0.11, 0.11, loc=(W / 2 + 0.01, -0.02, -0.0012), mat="disc_print", cuts=2)
    title = _ch(rng, GAME_TITLES)
    c = tex.Canvas(160, 160, (0.95, 0.95, 0.95, 0))
    c.circle(0.5, 0.5, 0.5, (0.9, 0.9, 0.92))
    c.circle(0.5, 0.5, 0.5, (0.1, 0.1, 0.12), ring=0.31)
    c.text_fit(title, 0.1, 0.83, 0.8, 0.07, INK, bold=True)
    c.circle(0.5, 0.5, 0.13, (0.85, 0.85, 0.88))
    c.circle(0.5, 0.5, 0.07, (0, 0, 0, 1))
    return {"case": P((0.03, 0.03, 0.035), 0.3), "spine": P((0.06, 0.06, 0.07), 0.3),
            "art": PR(_box_art(rng, "gcase", title), 0.25),
            "disc": ("disc", {"color": (0.35, 0.35, 0.45)}),
            "disc_print": PR(c.image("gdisc"), 0.25, alpha_from_image=True)}


@obj("strategy_guide", mass=0.6, weight=1.0, **SPECIAL)
def strategy_guide(b, rng, pal):
    """The official strategy guide: every secret, every map, a poster stapled in the middle."""
    W, H, D = 0.15, 0.2, 0.014
    b.box((W, H, 0.0012), loc=(0, 0, D / 2), mat="cover")
    b.box((W, H, 0.0012), loc=(0, 0, -D / 2), mat="cover")
    b.box((W - 0.004, H - 0.006, D - 0.002), loc=(0.001, 0, 0), mat="pages")
    b.box((0.003, H, D + 0.001), loc=(-W / 2, 0, 0), mat="spine", bevel=0.001)
    b.plane(W - 0.002, H - 0.002, loc=(0, 0, D / 2 + 0.0007), mat="art", cuts=2)
    title = _ch(rng, GAME_TITLES + ["POCKET MOANSTERS RED & BLUE", "PERFECT DORK", "SMASH BRUHS"])
    c = tex.Canvas(240, 320, (0.95, 0.95, 0.95, 1))
    c.rect(0, 0.82, 1, 1, (0.95, 0.15, 0.1))
    _ct(c, "PRIMO", 0.5, 0.98, 0.1, (1, 1, 1))
    _ct(c, "OFFICIAL STRATEGY GUIDE", 0.5, 0.88, 0.04, (1, 1, 1))
    top = _ch(rng, [(0.2, 0.3, 0.8), (0.5, 0.1, 0.6), (0.1, 0.5, 0.3), (0.9, 0.5, 0.1)])
    c.rect(0.06, 0.26, 0.94, 0.8, top)
    for _ in range(5):
        x = float(rng.uniform(0.1, 0.9))
        c.poly([(x - 0.15, 0.27), (x, float(rng.uniform(0.45, 0.7))), (x + 0.15, 0.27)], (0, 0, 0, 0.4))
    _ct(c, title, 0.5, 0.76, 0.07, (1, 0.92, 0.3), maxw=0.84)
    c.poly(_star(0.8, 0.36, 0.11, 12, 0.7, asp=0.75), (1.0, 0.9, 0.1))
    _ct(c, "100%", 0.8, 0.4, 0.04, (0.85, 0.1, 0.1), maxw=0.14)
    _ct(c, "MAPS!", 0.8, 0.35, 0.03, (0.85, 0.1, 0.1), maxw=0.14)
    c.text("EVERY SECRET!", 0.06, 0.22, 0.04, INK, bold=True)
    c.text("ALL CHEAT CODES!", 0.06, 0.15, 0.04, INK, bold=True)
    c.text("PULL-OUT POSTER INSIDE", 0.06, 0.08, 0.03, (0.85, 0.1, 0.1), bold=True)
    return {"cover": P((0.95, 0.95, 0.95), 0.4), "pages": ("paper", {"color": (0.93, 0.92, 0.88)}),
            "spine": P((0.95, 0.15, 0.1), 0.4), "art": PR(c.image("sgcover"), 0.4)}


BOX_BRANDS = [("NINTENDON'T 64", "64-BIT POWER!", (0.1, 0.1, 0.12)), ("PLAYSTATIONARY", "NOW WITH DISCS", (0.15, 0.15, 0.2)),
              ("GAME CUBICLE", "HANDLE INCLUDED", (0.3, 0.2, 0.55)), ("X-BAWKS", "IT'S HUGE", (0.05, 0.05, 0.05)),
              ("WETDREAMCAST", "IT'S THINKING", (0.95, 0.95, 0.95)), ("DEGENESIS", "BLAST PROCESSING-ISH", (0.05, 0.05, 0.05))]


@obj("console_box", mass=0.5, weight=1.0, big=True, **SPECIAL)
def console_box(b, rng, pal):
    """The retail box: brand across the top, the console on the front, starbursts everywhere."""
    W, H, D = 0.2, 0.14, 0.085
    brand, slogan, bg = _ch(rng, BOX_BRANDS)
    b.box((W, H, D), mat="card", bevel=0.001)
    b.plane(W - 0.002, H - 0.002, loc=(0, 0, D / 2 + 0.0004), mat="front", cuts=3)
    b.plane(W - 0.002, D - 0.002, loc=(0, -H / 2 - 0.0004, 0), rot=(math.pi / 2, 0, 0), mat="side", cuts=2)
    ink = (1, 1, 1) if sum(bg) < 1.5 else INK
    c = tex.Canvas(320, 224, (*bg, 1))
    c.rect(0, 0.82, 1, 1, (0.9, 0.1, 0.1))
    _ct(c, brand, 0.5, 0.98, 0.14, (1, 1, 1), maxw=0.9)
    c.rect(0.12, 0.2, 0.7, 0.6, (0.6, 0.6, 0.62))
    c.rect(0.15, 0.55, 0.67, 0.65, (0.5, 0.5, 0.52))
    c.rect(0.3, 0.6, 0.5, 0.63, (0.1, 0.1, 0.1))
    c.circle(0.8, 0.35, 0.14, (0.6, 0.6, 0.62))
    c.circle(0.8, 0.35, 0.04, (0.1, 0.1, 0.1))
    c.poly(_star(0.82, 0.68, 0.13, 14, 0.75, asp=320 / 224), (1.0, 0.9, 0.1))
    _ct(c, slogan, 0.82, 0.71, 0.05, (0.85, 0.1, 0.1), maxw=0.2)
    c.text("CONTROLLER INCLUDED", 0.05, 0.12, 0.05, ink, bold=True)
    c.text("AC ADAPTOR AND AV CABLE", 0.05, 0.06, 0.04, ink)
    s = tex.Canvas(320, 128, (*bg, 1))
    _ct(s, brand, 0.5, 0.8, 0.3, ink, maxw=0.9)
    _ct(s, "VIDEO GAME SYSTEM", 0.5, 0.35, 0.18, ink, maxw=0.8)
    return {"card": ("cardboard", {}), "front": PR(c.image("cbfront"), 0.45), "side": PR(s.image("cbside"), 0.45)}


@obj("rf_switch", mass=0.05, weight=1.0, **SPECIAL)
def rf_switch(b, rng, pal):
    """The RF switch box: TV / GAME slider, coax tail, two spade lugs for the screws on the back of the set."""
    W, H, D = 0.06, 0.04, 0.018
    b.box((W, H, D), mat="body", bevel=0.003)
    b.plane(0.046, 0.028, loc=(-0.003, 0, D / 2 + 0.0004), mat="label", cuts=2)
    b.box((0.012, 0.007, 0.006), loc=(0.016, 0.006, D / 2 + 0.002), mat="slider", bevel=0.0015)
    b.cyl(0.004, 0.01, loc=(W / 2 + 0.004, 0.008, 0), rot=(0, math.pi / 2, 0), mat="metal", seg=12)
    end = _cord(b, rng, (-W / 2, -0.008, 0), 0.08, 0.0022, (-1, -0.3, 0), mat="coax", wig=0.015)
    for dy in (-0.004, 0.004):
        b.tube([(-W / 2, 0.01 + dy, 0), (-W / 2 - 0.03, 0.02 + dy * 2, 0), (-W / 2 - 0.06, 0.026 + dy * 2, 0)], 0.0013,
               mat="twin", seg=6)
        b.extrude([(-0.004, -0.0015), (0.004, -0.0015), (0.004, 0.0015), (-0.004, 0.0015)], 0.001,
                  loc=(-W / 2 - 0.064, 0.026 + dy * 2, 0), mat="metal")
    b.cyl(0.0035, 0.012, loc=(end[0] - 0.006, end[1], end[2]), rot=(0, math.pi / 2, 0), mat="metal", seg=12)
    c = tex.Canvas(192, 116, (0.9, 0.88, 0.8, 1))
    c.text("RF SWITCH", 0.06, 0.92, 0.16, INK, bold=True)
    c.text("TV", 0.62, 0.62, 0.14, INK)
    c.text("GAME", 0.62, 0.36, 0.14, INK)
    c.text("CH 3  4", 0.06, 0.55, 0.12, (0.6, 0.1, 0.1))
    c.text("75 OHM", 0.06, 0.3, 0.1, INK)
    return {"body": P(_ch(rng, [(0.85, 0.82, 0.72), (0.3, 0.3, 0.32), (0.12, 0.12, 0.13)]), 0.4),
            "label": PR(c.image("rflab"), 0.4), "slider": P((0.12, 0.12, 0.12), 0.4), "metal": MET((0.8, 0.8, 0.8), 0.25),
            "coax": P(BLACK, 0.5), "twin": P((0.55, 0.45, 0.3), 0.5)}


@obj("light_gun", mass=0.2, weight=1.0, **SPECIAL)
def light_gun(b, rng, pal):
    """The orange light gun: point it at the screen, shoot the ducks, blame the dog."""
    b.cyl(0.013, 0.1, loc=(0.03, 0, 0.02), rot=(0, math.pi / 2, 0), mat="body", seg=20)
    b.box((0.06, 0.03, 0.036), loc=(-0.025, 0, 0.018), mat="body", bevel=0.006)
    b.cyl(0.015, 0.006, loc=(0.082, 0, 0.02), rot=(0, math.pi / 2, 0), mat="dark", seg=20)
    b.extrude([(-0.018, 0.0), (0.012, 0.0), (0.0, -0.075), (-0.032, -0.07)], 0.026, loc=(-0.035, 0, 0.005),
              rot=(math.pi / 2, 0, 0), mat="grip", bevel=0.005)
    b.box((0.006, 0.006, 0.02), loc=(-0.005, 0, -0.008), rot=(0, 0.3, 0), mat="dark", bevel=0.002)
    b.tube([(-0.02, 0, -0.002), (-0.012, 0, -0.03), (0.01, 0, -0.03), (0.014, 0, -0.002)], 0.0028, mat="body", seg=8)
    b.plane(0.034, 0.012, loc=(0.025, 0, 0.0332), mat="label", cuts=2)
    _cord(b, rng, (-0.06, 0, -0.06), 0.2, 0.0022, (-1, 0.3, -0.1), mat="dark")
    c = tex.Canvas(128, 44, (1.0, 0.45, 0.05, 1))
    _ct(c, "ZAPPED", 0.5, 0.82, 0.6, (0.1, 0.1, 0.1))
    col = (1.0, 0.42, 0.05) if rng.random() < 0.75 else (0.35, 0.35, 0.37)
    return {"body": P(col, 0.35), "grip": P(tuple(v * 0.9 for v in col), 0.45), "dark": P((0.1, 0.1, 0.1), 0.4),
            "label": PR(c.image("zaplab"), 0.35)}


@obj("extension_cable", mass=0.08, weight=1.0, **SPECIAL)
def extension_cable(b, rng, pal):
    """The controller extension cable: a coiled mess and two chunky ends, so you could sit on the couch."""
    pts = helix(0.04, 0.012, 3.2, 28, start=(0, 0, 0))
    pts = [(x, y + 0.005 * math.sin(i * 0.3), z) for i, (x, y, z) in enumerate(pts)]
    b.tube(pts, 0.0024, mat="cord", seg=8)
    a, e = pts[0], pts[-1]
    b.tube([a, (a[0] + 0.03, a[1] - 0.03, a[2]), (a[0] + 0.06, a[1] - 0.05, a[2])], 0.0024, mat="cord", seg=8)
    b.tube([e, (e[0] - 0.03, e[1] + 0.04, e[2]), (e[0] - 0.07, e[1] + 0.06, e[2])], 0.0024, mat="cord", seg=8)
    b.box((0.022, 0.012, 0.016), loc=(a[0] + 0.072, a[1] - 0.056, a[2]), rot=(0, 0, -0.5), mat="plug", bevel=0.003)
    b.box((0.012, 0.008, 0.01), loc=(a[0] + 0.086, a[1] - 0.064, a[2]), rot=(0, 0, -0.5), mat="pins", bevel=0.001)
    b.box((0.028, 0.018, 0.02), loc=(e[0] - 0.084, e[1] + 0.066, e[2]), rot=(0, 0, 0.4), mat="plug", bevel=0.004)
    b.box((0.002, 0.014, 0.012), loc=(e[0] - 0.098, e[1] + 0.072, e[2]), rot=(0, 0, 0.4), mat="pins")
    col = _ch(rng, [(0.3, 0.3, 0.32), BLACK, PS_GREY])
    return {"cord": P(col, 0.45), "plug": P(tuple(v * 0.8 for v in col), 0.4), "pins": P((0.02, 0.02, 0.02), 0.5)}


LORE_NAMES = {
    "console_64": "Nintendon't 64",
    "trident_controller": "Three-Handled Controller",
    "pocket_handheld": "Game Boi Color (Grape)",
    "wide_handheld": "Game Boi Advanse",
    "dual_screen_handheld": "Dual Scream Clamshell",
    "cube_console": "Game Cubicle",
    "disc_console": "PlayStationary",
    "twin_grip_controller": "Twin-Grip Rumble Pad",
    "slim_tower_console": "PlayStationary 2 (Standing)",
    "big_x_console": "X-Bawks",
    "giant_controller": "The Brick (X-Bawks Controller)",
    "swirl_console": "WetDreamcast",
    "vmu_controller": "WetDreamcast Pad + Memory Screen",
    "console_16bit": "Degenesis 16-Bit",
    "monster_cart": "Pocket Moansters Cartridge",
    "monster_card": "Pocket Moansters Trading Card",
    "monster_dex": "Moanster-Dex Toy",
    "duel_card": "Duel Monstahs Card",
    "battle_top": "Bayblade Battle Top",
    "ripcord_launcher": "Bayblade Rip-Cord Launcher",
    "finger_skateboard": "Finger Board",
    "pog_slammer": "Metal Slammer",
    "pog_tube": "Pogfed Milkcap Tube",
    "av_cable": "Red-White-Yellow AV Cable",
    "memory_card_stack": "Memory Card Stack",
    "game_case": "Game Case, Disc Hanging Out",
    "strategy_guide": "Primo Official Strategy Guide",
    "console_box": "Console Retail Box",
    "rf_switch": "RF Switch Box",
    "light_gun": "Zapped Light Gun",
    "extension_cable": "Controller Extension Cable",
}
LORE_NOTES = {
    "console_64": ["cart wouldn't read. blew in it. blew harder.", "four ports, four friends, one TV, zero screen-peeking rules honored",
                   "expansion lid pried off with a butter knife, 1999", "still smells like a basement"],
    "trident_controller": ["nobody ever held the left handle", "analog stick ground to dust by a minigame",
                           "palm blister: confirmed", "cord stretched across the living room, tripped Dad twice"],
    "pocket_handheld": ["see-through so you could watch the batteries die", "played under the covers by streetlight",
                        "AA batteries stolen from the TV remote", "link cable never found"],
    "wide_handheld": ["no backlight. sat by the window. squinted.", "shoulder button sticky with juice box",
                      "played on the bus, missed the stop"],
    "dual_screen_handheld": ["stylus lost within the week", "bottom screen scratched by a fingernail",
                             "hinge still holding, barely", "the dog game ran for six straight months"],
    "cube_console": ["carry handle used exactly once, to a sleepover", "mini discs only. tried a CD anyway.",
                     "purple. obviously purple.", "memory card 59 full, deleted a sibling's save"],
    "disc_console": ["played upside down so the laser would read", "lid spring shot across the room",
                     "the boot-up sound still lives in the walls", "demo disc had more hours on it than any game"],
    "twin_grip_controller": ["rumble motor worn smooth", "left stick drifts toward the fridge",
                             "cord chewed by the family dog", "start button pressed through the floor"],
    "slim_tower_console": ["stood up, fell over, stood up again", "doubled as the house DVD player",
                           "disc read error: 4,000 times", "fan sounded like a hair dryer by 2004"],
    "big_x_console": ["weighs as much as a small dog", "the green light means it is thinking about it",
                      "hard drive full of ripped CDs", "used as a footrest during the season finale"],
    "giant_controller": ["needed two hands and a forearm", "the black and white buttons did nothing anyone remembers",
                         "breakaway cable broke away", "could stop a door"],
    "swirl_console": ["dead before it was finished", "the orange light still blinks in the dark",
                      "modem plugged into the phone line, Mom on the other end", "fan noise legendary"],
    "vmu_controller": ["memory card has its own screen. pet still hungry.", "cord comes out the bottom. who did that.",
                       "beeped all through Sunday service"],
    "console_16bit": ["blast processing, allegedly", "cart pressed down hard to make it work",
                      "reset button hit mid-boss by a little brother", "the big circle was a coaster for years"],
    "monster_cart": ["save battery died. 150 hours gone.", "traded my best one for a dud. still mad.",
                     "label chewed at the corner", "the glitch bird duplicated item six"],
    "monster_card": ["rubber-banded with 400 others", "the holo one stayed in a sleeve, then didn't",
                     "traded at recess, banned at recess", "lunch money became booster packs"],
    "monster_dex": ["the lens lights up and does nothing", "batteries rattling around loose",
                    "it knew 150 names and none of them right"],
    "duel_card": ["played with the rules we made up", "the card that wins the game, in every deck",
                  "spiral back stared at from across the cafeteria", "trap card. not a joke. still a trap."],
    "battle_top": ["tip sanded sharp on the driveway", "lost under the couch mid-spin",
                   "stadium was a salad bowl", "let it rip. ripped."],
    "ripcord_launcher": ["teeth stripped from one bad yank", "the cord snapped back and took a knuckle",
                         "launcher outlived every top"],
    "finger_skateboard": ["did a kickflip off the lunch table", "teacher took it, kept it",
                          "wheels lost in the carpet", "the graphic was the whole reason"],
    "pog_slammer": ["played for keeps. lost for keeps.", "banned at school by Wednesday",
                    "heavy enough to dent a desk", "the skull one was the real flex"],
    "pog_tube": ["every pog in here is the same three designs", "tube cap lost; rubber band instead",
                 "came free in a juice box six-pack"],
    "av_cable": ["red and white swapped, nobody noticed", "the yellow one always half out",
                 "TV only had one input. unplugged the VCR."],
    "memory_card_stack": ["one of these holds a 60-hour save. nobody knows which.", "labeled in pen, smudged by thumb",
                          "the 8 MB one was a lie"],
    "game_case": ["disc kept loose, scratched in a rainbow", "case belonged to a different game",
                  "rental sticker peeled half off"],
    "strategy_guide": ["dog-eared at the water level", "map pages coffee-stained",
                       "the cheat codes were the whole point", "poster on the bedroom door by noon"],
    "console_box": ["kept the box. for resale. never resold.", "styrofoam still inside",
                    "Christmas morning, 6 a.m., wrapping paper everywhere"],
    "rf_switch": ["channel 3. no, 4. no, 3.", "screws on the back of the TV, done with a dime",
                  "static on every game, blamed the weather"],
    "light_gun": ["only works on a tube TV", "pressed right up to the screen to cheat",
                  "the dog laughed. we did not."],
    "extension_cable": ["so you could sit on the couch like a person", "yanked the console off the shelf",
                        "coiled, uncoiled, knotted forever"],
}
