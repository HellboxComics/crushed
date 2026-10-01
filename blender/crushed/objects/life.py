"""Everyday kid life, 1985-2002: the school supply aisle, the lunch table trade, the sports card shop, and the
orange-splat kids' cable channel. All original shapes, characters and art; every brand is a parody.

Groups: school stuff rides in the regular cubes ("era"). LUNCH TRADE, SPORTS MEMORABILIA and SLIMED are the
one-of-one themes (tags "lunch", "sports", "slimed"); a few lunch snacks and the card packs are era-true enough
to show up in regular cubes too.
"""
import math

import numpy as np
from mathutils import Matrix

from .. import parody as _pd
from .. import tex
from . import BLACK, CHROME, MET, P, PR, RUB, SILVER, T, WHITE, obj
from ..geo import ellipse, helix, rounded_rect

PI = math.pi


# =====================================================================================================
# drawing helpers (tex.Canvas, in 0..1 canvas space, y up)
# =====================================================================================================

def _cv(w, h, bg):
    return tex.Canvas(w, h, (*tuple(bg)[:3], 1))


def _fit(c, s, maxw, size, spacing=1.0):
    need = len(s) * 6 * (size / 7.0) * (c.h / c.w) * spacing
    return size * min(1.0, maxw / need) if need > 0 else size


def _tw(c, s, size, spacing=1.0):
    return (len(s) * 6 * spacing - 1) * (size / 7.0) * (c.h / c.w)


def _ct(c, s, cx, y, maxw, size, col, out=None, spacing=1.0, bold=True, d=None):
    """Centered text, shrunk to fit maxw; `out` draws a fat cartoon outline behind it. y is the top."""
    size = _fit(c, s, maxw, size, spacing)
    x = cx - _tw(c, s, size, spacing) / 2
    if out is not None:
        d = d if d is not None else size * 0.1
        dx = d * c.h / c.w
        for ox, oy in ((-dx, -d), (dx, d), (dx, -d), (-dx, d), (0, -d * 1.4)):
            c.text(s, x + ox, y + oy, size, out, spacing=spacing, bold=bold)
    c.text(s, x, y, size, col, spacing=spacing, bold=bold)
    return size


def _lt(c, s, x, y, maxw, size, col, out=None, spacing=1.0, bold=True):
    """Left-aligned text with an optional outline."""
    size = _fit(c, s, maxw, size, spacing)
    if out is not None:
        d = size * 0.1
        dx = d * c.h / c.w
        for ox, oy in ((-dx, -d), (dx, d), (dx, -d), (-dx, d)):
            c.text(s, x + ox, y + oy, size, out, spacing=spacing, bold=bold)
    c.text(s, x, y, size, col, spacing=spacing, bold=bold)
    return size


def _star(c, cx, cy, r, col, n=5, inner=0.45, rot=0.0):
    a = c.h / c.w
    pts = []
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        t = rot + PI / 2 + PI * i / n
        pts.append((cx + rr * math.cos(t) * a, cy + rr * math.sin(t)))
    c.poly(pts, col)


def _burst(c, cx, cy, r, col, n=16, ring=None):
    if ring is not None:
        _star(c, cx, cy, r * 1.08, ring, n, 0.72)
    _star(c, cx, cy, r, col, n, 0.72)


def _ell(c, cx, cy, rx, ry, col, n=28):
    a = c.h / c.w
    c.poly([(cx + rx * a * math.cos(2 * PI * i / n), cy + ry * math.sin(2 * PI * i / n)) for i in range(n)], col)


def _splat_shape(rng, n=48, lobes=11, drip=0.5):
    """A cartoon goo splat, unit radius: a round body with fat bulging lobes and a few thin drips."""
    ph = rng.uniform(0, 6.28, 2)
    blobs = [(float(rng.uniform(0, 2 * PI)), float(rng.uniform(0.12, 0.3)), float(rng.uniform(0.12, 0.22)))
             for _ in range(lobes)]
    drips = [(float(rng.uniform(0, 2 * PI)), float(rng.uniform(0.3, 0.5)) * drip * 2, 0.06) for _ in range(3)]
    pts = []
    for i in range(n):
        t = 2 * PI * i / n
        r = 0.62 + 0.04 * math.sin(3 * t + ph[0]) + 0.03 * math.sin(7 * t + ph[1])
        for c0, amp, w in blobs + drips:
            dt = math.atan2(math.sin(t - c0), math.cos(t - c0))
            r += amp * math.exp(-(dt / w) ** 2)
        pts.append((r * math.cos(t), r * math.sin(t)))
    m = max(max(abs(x), abs(y)) for x, y in pts)
    return [(x / m, y / m) for x, y in pts]


def _splat(c, cx, cy, r, col, rng, out=None):
    pts = _splat_shape(rng)
    a = c.h / c.w
    if out is not None:
        c.poly([(cx + x * r * 1.06 * a, cy + y * r * 1.06) for x, y in pts], out)
    c.poly([(cx + x * r * a, cy + y * r) for x, y in pts], col)


def _zig(c, x0, x1, y, amp, n, w, col):
    c.line([(x0 + (x1 - x0) * i / n, y + (amp if i % 2 else -amp)) for i in range(n + 1)], w, col)


def _squig(c, x0, x1, y, amp, w, col, f=3.0):
    xs = np.linspace(x0, x1, 24)
    c.line([(float(x), float(y + amp * math.sin((x - x0) / max(x1 - x0, 1e-3) * f * 2 * PI))) for x in xs], w, col)


def _memphis(c, rng, cols, n=26):
    """90s binder-cover chaos: triangles, squiggles, zigzags, confetti dots, rings."""
    a = c.h / c.w
    for _ in range(n):
        k = int(rng.integers(0, 5))
        col = cols[int(rng.integers(0, len(cols)))]
        x, y = (float(v) for v in rng.uniform(0, 1, 2))
        s = float(rng.uniform(0.04, 0.1))
        if k == 0:
            r = float(rng.uniform(0, 6.28))
            c.poly([(x + s * a * math.cos(r + i * 2.094), y + s * math.sin(r + i * 2.094)) for i in range(3)], col)
        elif k == 1:
            _squig(c, x, x + s * 2.5 * a, y, s * 0.3, 0.012, col)
        elif k == 2:
            _zig(c, x, x + s * 2.5 * a, y, s * 0.25, 6, 0.012, col)
        elif k == 3:
            c.circle(x, y, s * 0.35, col)
        else:
            c.circle(x, y, s * 0.5, col, ring=0.012)


def _rot(c, k=1):
    """Rotate a canvas 90 deg counterclockwise (k=1): for text that runs along a lathe or a ribbon."""
    a = np.ascontiguousarray(np.rot90(c.a, k)).astype(np.float32)
    n = tex.Canvas(a.shape[1], a.shape[0])
    n.a = a
    return n


def _critter(c, cx, cy, r, col, rng, kind=None, shades=None, ink=(0.05, 0.05, 0.07)):
    """An original 90s cartoon mascot: fat outlined head, big goofy eyes, buck-tooth grin, odd ears."""
    a = c.h / c.w
    kind = int(rng.integers(0, 5)) if kind is None else kind
    dark = tuple(x * 0.7 for x in col)
    if kind == 0:      # pointy ears
        for s in (-1, 1):
            c.poly([(cx + s * r * 0.95 * a, cy + r * 0.25), (cx + s * r * 0.35 * a, cy + r * 0.75),
                    (cx + s * r * 1.2 * a, cy + r * 1.25)], ink)
            c.poly([(cx + s * r * 0.85 * a, cy + r * 0.35), (cx + s * r * 0.45 * a, cy + r * 0.7),
                    (cx + s * r * 1.08 * a, cy + r * 1.07)], col)
    elif kind == 1:    # antenna
        for s in (-1, 1):
            c.line([(cx + s * r * 0.3 * a, cy + r * 0.8), (cx + s * r * 0.7 * a, cy + r * 1.45)], r * 0.12, ink)
            c.circle(cx + s * r * 0.7 * a, cy + r * 1.45, r * 0.17, (1.0, 0.9, 0.1))
    elif kind == 2:    # floppy ears
        for s in (-1, 1):
            c.circle(cx + s * r * 1.0 * a, cy - r * 0.05, r * 0.42, ink)
            c.circle(cx + s * r * 1.0 * a, cy - r * 0.05, r * 0.34, dark)
    elif kind == 3:    # mohawk
        for i in range(5):
            x = cx + (i - 2) * r * 0.18 * a
            c.poly([(x - r * 0.12 * a, cy + r * 0.8), (x + r * 0.12 * a, cy + r * 0.8), (x, cy + r * 1.4)],
                   (1.0, 0.2, 0.6))
    else:              # horns
        for s in (-1, 1):
            c.poly([(cx + s * r * 0.5 * a, cy + r * 0.7), (cx + s * r * 0.8 * a, cy + r * 0.55),
                    (cx + s * r * 0.95 * a, cy + r * 1.35)], (0.95, 0.92, 0.8))
    c.circle(cx, cy, r * 1.08, ink)
    c.circle(cx, cy, r, col)
    c.circle(cx, cy - r * 0.45, r * 0.42, tuple(min(1, x * 1.25 + 0.15) for x in col))      # muzzle
    shades = rng.random() < 0.35 if shades is None else shades
    if shades:
        c.rect(cx - r * 0.85 * a, cy + r * 0.05, cx + r * 0.85 * a, cy + r * 0.38, ink)
        c.line([(cx - r * 0.6 * a, cy + r * 0.3), (cx - r * 0.3 * a, cy + r * 0.12)], r * 0.05, (0.6, 0.9, 1.0))
    else:
        for s, lean in ((-1, 0.0), (1, float(rng.uniform(-0.08, 0.08)))):
            c.circle(cx + s * r * 0.36 * a, cy + r * 0.22, r * 0.33, ink)
            c.circle(cx + s * r * 0.36 * a, cy + r * 0.22, r * 0.27, (1, 1, 1))
            c.circle(cx + s * r * (0.3 + lean) * a, cy + r * 0.16, r * 0.12, ink)
    c.circle(cx, cy - r * 0.2, r * 0.12, ink)                                                   # nose
    c.line([(cx - r * 0.45 * a, cy - r * 0.45), (cx - r * 0.15 * a, cy - r * 0.68), (cx + r * 0.2 * a, cy - r * 0.66),
            (cx + r * 0.5 * a, cy - r * 0.4)], r * 0.09, ink)                                  # grin
    c.rect(cx - r * 0.12 * a, cy - r * 0.78, cx + r * 0.12 * a, cy - r * 0.63, (1, 1, 1))        # buck teeth
    c.line([(cx, cy - r * 0.78), (cx, cy - r * 0.63)], r * 0.03, ink)


def _glitter(rng, name, col, n=180):
    c = _cv(64, 64, col)
    for _ in range(n):
        x, y = rng.uniform(0, 1, 2)
        c.circle(float(x), float(y), float(rng.uniform(0.006, 0.014)),
                 (1, 1, 1) if rng.random() < 0.5 else tuple(min(1, v * 1.5 + 0.2) for v in col))
    return c.image(name)


# shows, teams, players: all made up
SHOWS = ["TURBO TRASH PANDAS", "GALAXY GERBILS", "THE SNORKEL SQUAD", "RAD-ICAL ROBO DUDES", "SKATE BAT 3000",
         "CAPTAIN CRUSTY", "THE MALL RATS", "NINJA NARWHALS", "SPACE GRANNY"]
CABLE_SHOWS = ["CATDOGE", "AAAH!! REAL BILLS", "ROCKO'S MODERN MORTGAGE", "THE WILD THORNBUSHES",
               "DOUG FUNNYMONEY", "BOOGER BAY", "HEY, PALMER!", "THE ANGRY BEEFS"]
CABLE = "PICKLEODEON"
NEON = [(1.0, 0.15, 0.6), (0.1, 0.85, 0.9), (1.0, 0.9, 0.1), (0.55, 0.2, 0.95), (0.4, 1.0, 0.2), (1.0, 0.5, 0.05)]
ORANGE = (1.0, 0.45, 0.02)
SLIME_G = (0.45, 0.95, 0.1)

TEAMS = [("TOLEDO", "TORNADOES", (0.1, 0.2, 0.55), (0.95, 0.75, 0.1)),
         ("OMAHA", "OUTLAWS", (0.1, 0.1, 0.12), (0.85, 0.1, 0.15)),
         ("SPOKANE", "SPECTERS", (0.35, 0.15, 0.55), (0.1, 0.75, 0.7)),
         ("TULSA", "THUNDERHAWKS", (0.05, 0.45, 0.45), (0.95, 0.5, 0.1)),
         ("RENO", "ROLLERS", (0.85, 0.35, 0.05), (0.1, 0.1, 0.12)),
         ("BOISE", "BLIZZARD", (0.55, 0.75, 0.95), (0.1, 0.2, 0.45)),
         ("WICHITA", "WRECKERS", (0.75, 0.05, 0.1), (0.92, 0.92, 0.92)),
         ("MOBILE", "MOONSHOTS", (0.12, 0.12, 0.38), (0.95, 0.9, 0.5))]
PLAYERS = ["BUBBA ROCKETT", "SKIP DINGERSON", "MOOSE MCCRACKEN", "TONY TATERS", "DUKE BALLSWORTH",
           "CHET VANDERWHIFF", "DARNELL SWOOSHLEY", "REGGIE RUGPULL", "HODL HANSEN", "LEFTY O'BLIVION",
           "AL BUMPUS", "RANDY KOWALCZYK", "JUNIOR BIGWAGER", "STORMIN NORMAN NUTT", "DEWAYNE DUNKWORTH"]
CARD_BRANDS = ["UPPER DECKED", "TOPPED", "FLEERED", "DONRUSTY", "PRO SETBACK", "SCORE-ISH", "STADIUM CLUBBED"]
SPORTS = ["BASEBALL", "FOOTBALL", "BASKETBALL", "HOCKEY"]
SKIN = [(0.98, 0.82, 0.68), (0.88, 0.66, 0.5), (0.7, 0.48, 0.32), (0.48, 0.3, 0.2)]


def _team(rng):
    return TEAMS[int(rng.integers(0, len(TEAMS)))]


def _show_art(rng, name, w=320, h=256, title=None, shows=SHOWS, logo=None):
    """A Saturday-morning title card: sky, ground, a burst, the mascot (or two), the bubbly title banner."""
    title = title or str(shows[int(rng.integers(0, len(shows)))])
    sky = [(0.25, 0.75, 1.0), (0.55, 0.25, 0.85), (1.0, 0.55, 0.2), (0.1, 0.15, 0.35)][int(rng.integers(0, 4))]
    c = _cv(w, h, sky)
    c.gradient(tuple(min(1, x * 1.2 + 0.1) for x in sky), tuple(x * 0.6 for x in sky))
    _burst(c, 0.5, 0.48, 0.42, (1.0, 0.92, 0.3), n=20)
    for _ in range(6):
        _star(c, float(rng.uniform(0.05, 0.95)), float(rng.uniform(0.55, 0.95)), 0.03, (1, 1, 1))
    c.poly([(0, 0), (1, 0), (1, 0.22), (0.7, 0.28), (0.4, 0.2), (0, 0.27)],
           [(0.2, 0.75, 0.2), (0.9, 0.3, 0.6), (0.3, 0.3, 0.35)][int(rng.integers(0, 3))])
    cols = [NEON[int(i)] for i in rng.integers(0, len(NEON), 2)]
    if rng.random() < 0.5:
        _critter(c, 0.32, 0.42, 0.15, cols[0], rng)
        _critter(c, 0.68, 0.4, 0.13, cols[1], rng)
    else:
        _critter(c, 0.5, 0.42, 0.18, cols[0], rng)
    c.rect(0.03, 0.78, 0.97, 0.97, (0.05, 0.05, 0.07))
    c.rect(0.04, 0.79, 0.96, 0.96, tuple(NEON[int(rng.integers(0, len(NEON)))]))
    _ct(c, title, 0.5, 0.94, 0.88, 0.13, (1, 1, 1), out=(0.05, 0.05, 0.07))
    if logo:
        _splat(c, 0.87, 0.12, 0.09, ORANGE, rng, out=(1, 1, 1))
        _ct(c, logo, 0.87, 0.14, 0.16, 0.04, (1, 1, 1))
    c.noise(rng, 0.015)
    return c


def _player(c, cx, y0, hgt, jersey, trim, sport, skin, rng):
    """A flat action pose: legs, torso in team colors, number, head, helmet or cap, and the gear."""
    a = c.h / c.w
    u = hgt
    ink = (0.05, 0.05, 0.07)
    lean = float(rng.uniform(-0.1, 0.1))
    c.line([(cx - 0.05 * u * a, y0 + 0.45 * u), (cx - 0.14 * u * a, y0 + 0.2 * u), (cx - 0.1 * u * a, y0)],
           0.09 * u, (0.92, 0.92, 0.92) if sport == "BASEBALL" else trim)
    c.line([(cx + 0.05 * u * a, y0 + 0.45 * u), (cx + 0.16 * u * a, y0 + 0.22 * u), (cx + 0.22 * u * a, y0 + 0.02 * u)],
           0.09 * u, (0.92, 0.92, 0.92) if sport == "BASEBALL" else trim)
    tx = cx + lean * u * a
    c.poly([(cx - 0.11 * u * a, y0 + 0.42 * u), (cx + 0.11 * u * a, y0 + 0.42 * u), (tx + 0.15 * u * a, y0 + 0.78 * u),
            (tx - 0.15 * u * a, y0 + 0.78 * u)], jersey)
    c.line([(tx - 0.14 * u * a, y0 + 0.75 * u), (tx - 0.3 * u * a, y0 + 0.62 * u)], 0.06 * u, jersey)
    c.line([(tx + 0.14 * u * a, y0 + 0.75 * u), (tx + 0.3 * u * a, y0 + 0.92 * u)], 0.06 * u, jersey)
    c.circle(tx - 0.3 * u * a, y0 + 0.62 * u, 0.035 * u, skin)
    c.circle(tx + 0.3 * u * a, y0 + 0.92 * u, 0.035 * u, skin)
    c.text(str(int(rng.integers(1, 99))), tx - 0.07 * u * a, y0 + 0.68 * u, 0.12 * u, trim, bold=True)
    hx, hy = tx, y0 + 0.88 * u
    c.circle(hx, hy, 0.08 * u, skin)
    if sport in ("FOOTBALL", "HOCKEY"):
        c.circle(hx, hy + 0.01 * u, 0.095 * u, trim)
        c.rect(hx - 0.09 * u * a, hy - 0.04 * u, hx + 0.02 * u * a, hy + 0.0 * u, (0.6, 0.6, 0.62))
    elif sport == "BASEBALL":
        c.rect(hx - 0.085 * u * a, hy + 0.02 * u, hx + 0.085 * u * a, hy + 0.08 * u, jersey)
        c.rect(hx - 0.15 * u * a, hy + 0.02 * u, hx, hy + 0.04 * u, jersey)
        c.line([(tx + 0.3 * u * a, y0 + 0.92 * u), (tx + 0.05 * u * a, y0 + 1.12 * u)], 0.035 * u, (0.75, 0.55, 0.3))
    elif sport == "BASKETBALL":
        c.circle(tx + 0.36 * u * a, y0 + 1.0 * u, 0.07 * u, (0.95, 0.45, 0.1))
        c.line([(tx + 0.29 * u * a, y0 + 1.0 * u), (tx + 0.43 * u * a, y0 + 1.0 * u)], 0.008 * u, ink)
    if sport == "HOCKEY":
        c.line([(tx - 0.3 * u * a, y0 + 0.62 * u), (cx - 0.05 * u * a, y0 - 0.02 * u), (cx + 0.12 * u * a, y0 - 0.02 * u)],
               0.03 * u, (0.15, 0.15, 0.15))
    if sport == "FOOTBALL":
        _ell(c, tx + 0.36 * u * a, y0 + 0.98 * u, 0.07 * u, 0.04 * u, (0.5, 0.25, 0.1))


def _sports_card(rng, name, w=140, h=196, sport=None, back=False):
    """A 1989-1994 trading card: thick colored border, action photo, name bar, team, brand flag, foil seal."""
    city, nick, c1, c2 = _team(rng)
    sport = sport or SPORTS[int(rng.integers(0, len(SPORTS)))]
    player = str(PLAYERS[int(rng.integers(0, len(PLAYERS)))])
    brand = str(CARD_BRANDS[int(rng.integers(0, len(CARD_BRANDS)))])
    border = [(0.95, 0.95, 0.95), (0.1, 0.1, 0.12), c1, (0.2, 0.55, 0.3), (0.95, 0.8, 0.2)][int(rng.integers(0, 5))]
    c = _cv(w, h, border)
    if back:
        c.rect(0.06, 0.04, 0.94, 0.96, (0.85, 0.8, 0.62))
        c.rect(0.06, 0.82, 0.94, 0.96, c1)
        _ct(c, player, 0.5, 0.93, 0.84, 0.07, (1, 1, 1))
        for i in range(8):
            y = 0.72 - i * 0.075
            c.text(f"{87 + i}  {city[:3]}  {int(rng.integers(40, 160))}  .{int(rng.integers(200, 340))}",
                   0.1, y, 0.04, (0.15, 0.12, 0.1))
        c.text(f"NO. {int(rng.integers(1, 800))}", 0.68, 0.1, 0.04, (0.6, 0.1, 0.1))
        c.noise(rng, 0.02)
        return c
    sky = [(0.45, 0.7, 0.95), (0.25, 0.3, 0.4), (0.6, 0.65, 0.7)][int(rng.integers(0, 3))]
    c.rect(0.08, 0.2, 0.92, 0.94, sky)
    c.rect(0.08, 0.2, 0.92, 0.42, (0.25, 0.55, 0.2) if sport in ("BASEBALL", "FOOTBALL") else (0.75, 0.6, 0.4)
           if sport == "BASKETBALL" else (0.9, 0.95, 1.0))
    for i in range(10):
        c.circle(0.1 + i * 0.09, 0.62 + 0.03 * math.sin(i), 0.02, (0.2, 0.2, 0.25, 0.5))
    _player(c, 0.5, 0.24, 0.6, c1, c2, sport, SKIN[int(rng.integers(0, len(SKIN)))], rng)
    c.rect(0.0, 0.03, 1.0, 0.2, c1)
    c.rect(0.0, 0.17, 1.0, 0.2, c2)
    _ct(c, player, 0.5, 0.15, 0.9, 0.07, (1, 1, 1), out=(0, 0, 0))
    _ct(c, f"{city} {nick}", 0.5, 0.075, 0.9, 0.04, c2)
    c.rect(0.05, 0.86, 0.6, 0.97, (0.9, 0.1, 0.1) if brand != "UPPER DECKED" else (0.1, 0.1, 0.12))
    _lt(c, brand, 0.08, 0.95, 0.5, 0.06, (1, 1, 1))
    c.circle(0.82, 0.88, 0.07, (0.8, 0.8, 0.9))
    c.circle(0.82, 0.88, 0.05, (0.6, 0.85, 1.0), ring=0.02)
    if rng.random() < 0.3:
        _lt(c, "ROOKIE", 0.62, 0.32, 0.3, 0.05, (1, 0.9, 0.1), out=(0.6, 0.0, 0.0))
    c.noise(rng, 0.02)
    return c


# =====================================================================================================
# A) SCHOOL  (regular cubes)
# =====================================================================================================

def _keeper_art(rng, name, w=320, h=372):
    c = _cv(w, h, (0.05, 0.05, 0.07))
    v = int(rng.integers(0, 3))
    if v == 0:          # memphis chaos
        c.a[:] = (*NEON[int(rng.integers(0, len(NEON)))], 1)
        _memphis(c, rng, [(0.05, 0.05, 0.07), (1, 1, 1)] + NEON, 40)
    elif v == 1:        # neon grid sunset, an original wedge car
        c.gradient((0.15, 0.0, 0.3), (1.0, 0.3, 0.55))
        c.circle(0.5, 0.52, 0.22, (1.0, 0.75, 0.1))
        for i in range(5):
            c.rect(0.0, 0.42 + i * 0.05, 1.0, 0.43 + i * 0.05, (1.0, 0.3, 0.55))
        c.rect(0.0, 0.0, 1.0, 0.42, (0.05, 0.0, 0.12))
        for i in range(11):
            c.line([(0.5, 0.42), (-0.6 + i * 0.22, 0.0)], 0.006, (0.1, 0.9, 1.0))
        for i in range(6):
            yy = 0.42 * (1 - (i / 6) ** 0.6)
            c.line([(0, yy), (1, yy)], 0.006, (0.1, 0.9, 1.0))
        c.poly([(0.18, 0.2), (0.82, 0.2), (0.85, 0.26), (0.62, 0.28), (0.5, 0.35), (0.32, 0.35), (0.2, 0.27)],
               (0.95, 0.1, 0.25))
        c.poly([(0.36, 0.28), (0.48, 0.28), (0.47, 0.33), (0.38, 0.33)], (0.3, 0.8, 1.0))
        for x in (0.3, 0.7):
            c.circle(x, 0.2, 0.045, (0.05, 0.05, 0.05))
            c.circle(x, 0.2, 0.02, (0.8, 0.8, 0.85))
    else:               # paint-splatter tiger stripes over hot pink
        c.a[:] = (1.0, 0.2, 0.6, 1)
        for i in range(9):
            y = 0.08 + i * 0.11
            c.poly([(0, y), (0.45 + 0.1 * math.sin(i), y + 0.03), (0.0, y + 0.06)], (0.05, 0.05, 0.07))
            c.poly([(1, y + 0.05), (0.5 - 0.1 * math.cos(i), y + 0.08), (1.0, y + 0.11)], (0.05, 0.05, 0.07))
        for _ in range(30):
            c.circle(*(float(v) for v in rng.uniform(0, 1, 2)), float(rng.uniform(0.005, 0.02)),
                     NEON[int(rng.integers(0, len(NEON)))])
    c.rect(0.0, 0.0, 1.0, 0.11, (0.05, 0.05, 0.07))
    _lt(c, "TRAPPED KEEPER", 0.04, 0.085, 0.6, 0.06, (1, 1, 1))
    c.text("PATENT PENDING FOREVER", 0.66, 0.065, 0.025, (0.7, 0.7, 0.7))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("trapped_keeper", eras=(0, 1), mass=0.5, weight=1.2, tags=("school",))
def trapped_keeper(b, rng, pal):
    """The zip-around trapper binder: loud cover, chunky side zipper, the velcro flap that ripped in class."""
    w, d, t = 0.26, 0.3, 0.038
    b.box((w, d, t), mat="vinyl", bevel=0.006)
    b.plane(w * 0.97, d * 0.97, loc=(0, 0, t / 2 + 0.0004), mat="art", cuts=3)
    # the zipper: tape band + chunky teeth around the three open sides
    for side in ("top", "bot", "right"):
        if side == "right":
            b.box((0.003, d - 0.01, 0.008), loc=(w / 2 + 0.0005, 0, 0), mat="tape")
            for i in range(int((d - 0.02) / 0.0045)):
                b.box((0.0028, 0.0026, 0.005), loc=(w / 2 + 0.0025, -d / 2 + 0.01 + i * 0.0045, 0), mat="teeth")
        else:
            y = d / 2 if side == "top" else -d / 2
            b.box((w - 0.01, 0.003, 0.008), loc=(0, y + 0.0005 * np.sign(y), 0), mat="tape")
            for i in range(int((w - 0.02) / 0.0045)):
                b.box((0.0026, 0.0028, 0.005), loc=(-w / 2 + 0.01 + i * 0.0045, y + 0.0025 * np.sign(y), 0), mat="teeth")
    # slider and the fat vinyl pull tab
    b.box((0.012, 0.008, 0.012), loc=(w / 2 + 0.004, -d / 2 + 0.03, 0), mat="slider", bevel=0.002)
    b.box((0.03, 0.012, 0.003), loc=(w / 2 + 0.022, -d / 2 + 0.03, 0.002), rot=(0, 0.2, 0.15), mat="pull", bevel=0.0015)
    # the flap: wraps the right edge onto the cover, velcro square under its tip
    fl = rng.choice([0, 1])
    b.box((0.07, 0.11, 0.004), loc=(w / 2 - 0.03, 0, t / 2 + 0.0025 + 0.003 * fl), rot=(0, -0.04 * fl, 0),
          mat="flap", bevel=0.0018)
    b.box((0.012, 0.11, 0.03), loc=(w / 2 + 0.004, 0, 0.002), mat="flap", bevel=0.003)
    b.plane(0.064, 0.104, loc=(w / 2 - 0.03, 0, t / 2 + 0.0047 + 0.003 * fl), rot=(0, -0.04 * fl, 0), mat="flapart",
            cuts=2)
    b.box((0.03, 0.04, 0.002), loc=(w / 2 - 0.085, 0, t / 2 + 0.001), mat="velcro")
    fc = pal.color("loud")
    fr = _cv(208, 128, fc)
    _memphis(fr, rng, [(0.05, 0.05, 0.07), (1, 1, 1)], 10)
    fr.rect(0.04, 0.3, 0.96, 0.7, (0.05, 0.05, 0.07))
    _ct(fr, "TRAPPED KEEPER", 0.5, 0.6, 0.88, 0.2, (1, 1, 1))
    flap = _rot(fr, 3)
    return {"vinyl": P(pal.color("loud"), 0.35, coat=0.4), "art": PR(_keeper_art(rng, "tk"), 0.3),
            "tape": ("fabric", {"color": (0.06, 0.06, 0.07)}), "teeth": MET((0.8, 0.8, 0.82), 0.25),
            "slider": CHROME(), "pull": P((0.06, 0.06, 0.07), 0.4),
            "flap": P(fc, 0.35, coat=0.4), "flapart": PR(flap.image("tkf"), 0.3),
            "velcro": ("fabric", {"color": (0.9, 0.9, 0.88)})}


def _dolphin(c, x, y, s, col, flip=1):
    a = c.h / c.w
    pts = [(-1.0, 0.0), (-0.6, 0.25), (-0.1, 0.35), (0.05, 0.6), (0.2, 0.35), (0.6, 0.25), (0.85, 0.12), (1.15, 0.12),
           (0.9, 0.0), (0.6, -0.12), (0.2, -0.2), (0.25, -0.38), (0.0, -0.2), (-0.6, -0.12), (-0.85, -0.25),
           (-1.05, -0.38), (-0.95, -0.05)]
    c.poly([(x + flip * px * s * a, y + py * s) for px, py in pts], col)
    c.circle(x + flip * 0.7 * s * a, y + 0.1 * s, s * 0.05, (0.05, 0.05, 0.1))


def _unicorn(c, x, y, s, col, mane):
    a = c.h / c.w
    head = [(-0.3, 0.6), (0.1, 0.65), (0.45, 0.3), (0.85, 0.0), (0.9, -0.2), (0.6, -0.25), (0.25, -0.1),
            (0.0, -0.6), (-0.45, -0.6), (-0.45, 0.2)]
    for i, (dx, dy) in enumerate([(-0.45, 0.55), (-0.6, 0.25), (-0.65, -0.1), (-0.65, -0.45)]):
        c.circle(x + dx * s * a, y + dy * s, s * 0.22, mane[i % len(mane)])
    c.poly([(x + px * s * a, y + py * s) for px, py in head], col)
    c.poly([(x + 0.0 * s * a, y + 0.62 * s), (x + 0.18 * s * a, y + 0.58 * s), (x + 0.25 * s * a, y + 1.25 * s)],
           (1.0, 0.85, 0.3))
    c.poly([(x - 0.2 * s * a, y + 0.6 * s), (x - 0.05 * s * a, y + 0.62 * s), (x - 0.18 * s * a, y + 0.9 * s)], col)
    c.circle(x + 0.25 * s * a, y + 0.25 * s, s * 0.09, (0.1, 0.05, 0.2))
    c.circle(x + 0.27 * s * a, y + 0.28 * s, s * 0.03, (1, 1, 1))


def _folder_art(rng, name):
    c = _cv(288, 368, (1, 1, 1))
    top, bot = [((1.0, 0.3, 0.75), (0.3, 0.1, 0.8)), ((0.2, 0.95, 1.0), (0.9, 0.1, 0.7)),
                ((1.0, 0.9, 0.2), (1.0, 0.2, 0.6))][int(rng.integers(0, 3))]
    c.gradient(top, bot)
    for i, col in enumerate([(1, 0.1, 0.2), (1, 0.55, 0.1), (1, 0.95, 0.1), (0.2, 0.9, 0.3), (0.2, 0.5, 1), (0.6, 0.2, 0.9)]):
        c.circle(0.5, 0.25, 0.58 - i * 0.05, col, ring=0.05)
    c.rect(0, 0, 1, 0.25, (0.1, 0.4, 0.95))
    for k in range(6):
        _squig(c, 0, 1, 0.05 + k * 0.035, 0.012, 0.01, (0.5, 0.9, 1.0), f=4 + k)
    if rng.random() < 0.5:
        _dolphin(c, 0.3, 0.32, 0.17, (0.4, 0.7, 1.0))
        _dolphin(c, 0.7, 0.44, 0.15, (0.85, 0.5, 1.0), flip=-1)
    else:
        _unicorn(c, 0.5, 0.48, 0.2, (1, 1, 1), [(1, 0.3, 0.7), (0.6, 0.3, 1.0), (0.3, 0.85, 1.0)])
        _dolphin(c, 0.25, 0.14, 0.12, (0.5, 0.8, 1.0))
    for _ in range(14):
        _star(c, float(rng.uniform(0.05, 0.95)), float(rng.uniform(0.6, 0.97)), float(rng.uniform(0.015, 0.035)),
              (1, 1, 1))
    c.circle(0.15, 0.85, 0.05, (1, 1, 1))
    c.circle(0.15, 0.85, 0.035, (1, 0.4, 0.8))
    _lt(c, "LIZA FRANKLY", 0.62, 0.05, 0.34, 0.035, (1, 1, 1))
    c.noise(rng, 0.012)
    return c.image(name)


@obj("neon_folder", eras=(1, 2), mass=0.08, weight=1.2, tags=("school",))
def neon_folder(b, rng, pal):
    """The pocket folder from the book fair: rainbow, glitter dolphins, a unicorn who has seen things."""
    w, h = 0.23, 0.3
    b.box((w, h, 0.0012), loc=(0.004, 0.003, -0.0015), rot=(0, 0, 0.02), mat="back")
    b.box((w, h, 0.0012), mat="back")
    b.plane(w, h, loc=(0, 0, 0.0007), mat="art", cuts=3)
    b.box((w * 0.995, 0.09, 0.0008), loc=(0.004, -h / 2 + 0.045, -0.0008), rot=(0, 0, 0.02), mat="pocket")
    for _ in range(int(rng.integers(1, 4))):          # notebook paper sticking out of the pocket
        b.box((0.2, 0.26, 0.0004), loc=(float(rng.uniform(0.0, 0.03)), float(rng.uniform(0.0, 0.03)), -0.0012),
              rot=(0, 0, float(rng.normal(0, 0.05))), mat="paper")
    return {"back": P((1.0, 0.3, 0.75), 0.25, coat=0.6), "art": PR(_folder_art(rng, "lf"), 0.2),
            "pocket": P((0.3, 0.1, 0.8), 0.25), "paper": PR(tex.notebook(rng, "lfp"), 0.85)}


def _fivesub_cover(rng, name, col):
    c = _cv(256, 330, col)
    for i in range(14):
        c.rect(0, i / 14, 1, i / 14 + 0.025, tuple(x * 0.9 for x in col))
    c.rect(0.08, 0.6, 0.92, 0.92, (1, 1, 1))
    c.rect(0.1, 0.62, 0.9, 0.9, (0.05, 0.05, 0.07))
    _ct(c, "5", 0.25, 0.88, 0.2, 0.25, (1, 0.85, 0.1))
    _star(c, 0.25, 0.75, 0.06, (1, 1, 1))
    _lt(c, "FIVE", 0.42, 0.86, 0.45, 0.1, (1, 1, 1))
    _lt(c, "STARVED", 0.42, 0.74, 0.45, 0.1, (1, 0.85, 0.1))
    _lt(c, "5 SUBJECT  200 SHEETS  COLLEGE RULED", 0.1, 0.56, 0.8, 0.03, (1, 1, 1))
    _lt(c, "NOW WITH POCKETS FOR YOUR FEELINGS", 0.1, 0.51, 0.8, 0.03, (1, 1, 1))
    c.rect(0.1, 0.1, 0.9, 0.36, (0.97, 0.96, 0.9))
    c.text("NAME:", 0.13, 0.33, 0.035, (0.2, 0.2, 0.3))
    c.scribble(rng, 0.32, 0.29, 0.85, 0.008, (0.1, 0.2, 0.6), 0.015)
    c.text("SUBJECT:", 0.13, 0.22, 0.035, (0.2, 0.2, 0.3))
    c.scribble(rng, 0.42, 0.18, 0.78, 0.008, (0.1, 0.2, 0.6), 0.015)
    if rng.random() < 0.7:
        c.circle(0.7, 0.45, 0.06, (0.1, 0.2, 0.6), ring=0.008)
        c.text("+", 0.67, 0.475, 0.06, (0.1, 0.2, 0.6))
    c.noise(rng, 0.02)
    return c.image(name)


@obj("five_subject", eras=(1, 2, 3), mass=0.7, weight=1.1, tags=("school",))
def five_subject(b, rng, pal):
    w, h, t = 0.215, 0.28, 0.024
    col = pal.color("loud")
    b.box((w, h, t), mat="pages")
    b.box((w, h, 0.0015), loc=(0, 0, t / 2 + 0.0008), mat="cover")
    b.plane(w * 0.99, h * 0.99, loc=(0, 0, t / 2 + 0.0017), mat="print", cuts=3)
    b.box((w, h, 0.0015), loc=(0, 0, -t / 2 - 0.0008), mat="cover")
    for i in range(5):           # the divider tabs, staggered down the right edge
        y = h / 2 - 0.03 - i * 0.052
        b.box((0.016, 0.04, 0.0012), loc=(w / 2 + 0.006, y, t / 2 - 0.004 - i * 0.004), mat=f"tab{i}")
    for i in range(22):
        y = -h / 2 + 0.01 + i * (h - 0.02) / 21
        b.torus(0.0135, 0.0011, loc=(-w / 2 - 0.002, y, 0), rot=(PI / 2, 0, 0), mat="spiral", seg=12, rseg=4)
    tabs = [(0.95, 0.2, 0.2), (0.2, 0.45, 0.95), (0.2, 0.8, 0.3), (1.0, 0.85, 0.1), (0.6, 0.3, 0.85)]
    out = {"pages": ("paper", {}), "cover": P(col, 0.5), "print": PR(_fivesub_cover(rng, "fs", col), 0.5),
           "spiral": MET(SILVER, 0.3)}
    for i in range(5):
        out[f"tab{i}"] = P(tabs[i], 0.45, coat=0.3)
    return out


def _patch_print(rng, name, kind):
    bgs = [(0.95, 0.85, 0.1), (0.05, 0.05, 0.07), (1.0, 0.3, 0.6), (0.1, 0.6, 0.9), (0.2, 0.75, 0.3)]
    bg = bgs[int(rng.integers(0, len(bgs)))]
    c = _cv(96, 96, (1, 1, 1))
    c.circle(0.5, 0.5, 0.48, (0.05, 0.05, 0.07))
    c.circle(0.5, 0.5, 0.43, bg)
    ink = (0.05, 0.05, 0.07) if sum(bg) > 1.5 else (1, 1, 1)
    if kind == 0:      # x-eyed smiley
        for s in (-1, 1):
            c.line([(0.5 + s * 0.15 - 0.06, 0.66), (0.5 + s * 0.15 + 0.06, 0.54)], 0.04, ink)
            c.line([(0.5 + s * 0.15 - 0.06, 0.54), (0.5 + s * 0.15 + 0.06, 0.66)], 0.04, ink)
        c.line([(0.28, 0.38), (0.4, 0.27), (0.6, 0.27), (0.72, 0.38)], 0.05, ink)
        c.line([(0.55, 0.3), (0.58, 0.22)], 0.05, (1, 0.4, 0.5))
    elif kind == 1:    # alien head
        c.circle(0.5, 0.55, 0.28, (0.4, 1.0, 0.2))
        c.poly([(0.26, 0.5), (0.74, 0.5), (0.5, 0.15)], (0.4, 1.0, 0.2))
        for s in (-1, 1):
            c.poly([(0.5 + s * 0.05, 0.48), (0.5 + s * 0.24, 0.6), (0.5 + s * 0.18, 0.42)], (0.05, 0.05, 0.07))
    elif kind == 2:    # peace
        c.circle(0.5, 0.5, 0.3, ink, ring=0.06)
        c.line([(0.5, 0.2), (0.5, 0.8)], 0.06, ink)
        c.line([(0.5, 0.5), (0.29, 0.29)], 0.06, ink)
        c.line([(0.5, 0.5), (0.71, 0.29)], 0.06, ink)
    else:              # skate or die
        _ct(c, "SKATE", 0.5, 0.66, 0.7, 0.16, ink)
        _ct(c, "OR DIE", 0.5, 0.44, 0.7, 0.16, (0.9, 0.1, 0.1))
    c.noise(rng, 0.02)
    return c.image(name)


@obj("backpack", eras=(1, 2, 3), mass=0.9, weight=1.2, big=True, hero=(0, -1, 0), tags=("school",))
def backpack(b, rng, pal):
    """One-strap-only backpack: suede bottom, front pocket, a pile of zipper pulls, iron-on patches, pins."""
    col = pal.color("loud") if rng.random() < 0.6 else pal.color("body")
    pocket = col if rng.random() < 0.5 else pal.color("loud")
    W, D, H = 0.3, 0.14, 0.42
    b.box((W, D, H), mat="pack", bevel=0.05, seg=3)
    b.box((W * 0.78, 0.055, H * 0.46), loc=(0, -D / 2 - 0.01, -H * 0.17), mat="pocket", bevel=0.026, seg=3)
    b.box((W + 0.004, D + 0.004, 0.07), loc=(0, 0, -H / 2 + 0.033), mat="suede", bevel=0.034, seg=3)
    # zippers: main arc across the top front, pocket zip across its top
    arc = [(-W / 2 * math.cos(t) * 0.92, -D / 2 + 0.006 - 0.02 * math.sin(t) * 0.0,
            H / 2 - 0.08 + 0.07 * math.sin(t)) for t in np.linspace(0.15, PI - 0.15, 14)]
    arc = [(x, -D / 2 + 0.004, z) for x, _, z in arc]
    b.tube(arc, 0.0035, mat="zip", seg=6)
    zy = -D / 2 - 0.038
    pz = H * 0.06 - 0.03
    b.tube([(-W * 0.36, zy, pz - 0.01), (0, zy - 0.002, pz + 0.004), (W * 0.36, zy, pz - 0.01)], 0.003, mat="zip", seg=6)
    pulls = []
    for (x, y, z) in [arc[3], arc[10], (-W * 0.25, zy, pz - 0.006), (W * 0.2, zy, pz - 0.006)]:
        b.box((0.008, 0.005, 0.012), loc=(x, y - 0.004, z - 0.006), mat="slider")
        pulls.append((x, y - 0.008, z - 0.014))
    pc = [NEON[int(i)] for i in rng.integers(0, len(NEON), 4)]
    for k, (x, y, z) in enumerate(pulls):
        b.tube([(x, y, z), (x + 0.004, y - 0.004, z - 0.02), (x - 0.002, y - 0.006, z - 0.04)], 0.0025,
               mat=f"pull{k}", seg=6)
        b.sphere(0.006, loc=(x - 0.002, y - 0.006, z - 0.045), mat=f"pull{k}", seg=8)
    # straps and grab loop on the back
    for s in (-1, 1):
        b.tube([(s * 0.07, D / 2, H / 2 - 0.06), (s * 0.09, D / 2 + 0.035, 0.05), (s * 0.11, D / 2 + 0.03, -0.12),
                (s * 0.12, D / 2 - 0.005, -H / 2 + 0.05)], 0.012, mat="strap", seg=6)
    b.torus(0.03, 0.006, loc=(0, 0.02, H / 2 + 0.002), rot=(PI / 2, 0, 0), arc=PI, mat="strap", seg=10, rseg=6)
    # patches and pins
    specs = {}
    spots = [(-0.075, -D / 2 - 0.038, -0.11), (0.075, -D / 2 - 0.038, -0.07), (0.09, -D / 2 - 0.004, 0.08)]
    kinds = rng.permutation(4)
    for k, (x, y, z) in enumerate(spots[:int(rng.integers(2, 4))]):
        r = float(rng.uniform(0.026, 0.034))
        b.extrude(ellipse(2 * r, 2 * r, 20), 0.002, loc=(x, y - 0.002, z), rot=(PI / 2, 0, float(rng.normal(0, 0.3))),
                  mat=f"patch{k}")
        specs[f"patch{k}"] = PR(_patch_print(rng, f"bpp{k}", int(kinds[k])), 0.85)
    tag = _cv(128, 48, (0.45, 0.28, 0.15))
    _ct(tag, "JANSPORK", 0.5, 0.75, 0.86, 0.45, (0.95, 0.85, 0.65))
    b.plane(0.05, 0.019, loc=(0, -D / 2 - 0.0385, -H * 0.17 - 0.06), rot=(PI / 2, 0, 0), mat="tag", cuts=2)
    for k in range(int(rng.integers(1, 4))):
        x, z = float(rng.uniform(-0.1, 0.1)), float(rng.uniform(0.02, 0.12))
        b.cyl(0.011, 0.004, loc=(x, -D / 2 - 0.003, z), rot=(PI / 2, 0, 0), mat=f"pin{k}", seg=16)
        specs[f"pin{k}"] = P(NEON[int(rng.integers(0, len(NEON)))], 0.2, coat=0.9)
    specs.update({"pack": ("fabric", {"color": col}), "pocket": ("fabric", {"color": pocket}),
                  "suede": ("fabric", {"color": (0.42, 0.27, 0.15)}), "zip": P((0.06, 0.06, 0.07), 0.5),
                  "slider": MET((0.7, 0.7, 0.72), 0.3), "strap": ("fabric", {"color": (0.08, 0.08, 0.09)}),
                  "tag": PR(tag.image("bpt"), 0.6)})
    for k in range(4):
        specs[f"pull{k}"] = P(pc[k], 0.35, coat=0.5)
    return specs


@obj("gel_pens", eras=(2,), mass=0.08, weight=1.2, tags=("school",))
def gel_pens(b, rng, pal):
    """A fistful of glitter gel pens: clear barrels, sparkly ink tubes, see-through caps, the good ones."""
    n = int(rng.integers(5, 8))
    cols = [(1.0, 0.3, 0.7), (0.6, 0.3, 1.0), (0.2, 0.8, 1.0), (0.4, 1.0, 0.3), (1.0, 0.8, 0.1), (1.0, 0.5, 0.1),
            (0.95, 0.95, 1.0), (0.2, 0.3, 1.0)]
    order = rng.permutation(len(cols))[:n]
    specs = {"barrel": T((0.92, 0.95, 1.0), 0.05), "tip": CHROME()}
    L = 0.14
    for k, ci in enumerate(order):
        col = cols[int(ci)]
        y = (k - (n - 1) / 2) * 0.0135
        x0 = float(rng.uniform(-0.01, 0.01))
        rz = float(rng.normal(0, 0.03))
        b.frame = Matrix.Rotation(rz, 4, "Z")
        b.cyl(0.0055, L * 0.62, loc=(x0, y, 0), rot=(0, PI / 2, 0), mat="barrel", seg=14)
        b.cyl(0.0019, L * 0.6, loc=(x0, y, 0), rot=(0, PI / 2, 0), mat=f"ink{k}", seg=8)
        b.cyl(0.006, L * 0.16, loc=(x0 + L * 0.38, y, 0), rot=(0, PI / 2, 0), mat=f"grip{k}", seg=14)
        b.cyl(0.0052, 0.012, r2=0.0012, loc=(x0 + L * 0.5, y, 0), rot=(0, PI / 2, 0), mat="tip", seg=10)
        b.cyl(0.0064, L * 0.28, loc=(x0 - L * 0.36, y, 0), rot=(0, PI / 2, 0), mat=f"cap{k}", seg=14)
        b.box((L * 0.2, 0.0025, 0.002), loc=(x0 - L * 0.36, y, 0.0068), mat=f"cap{k}")
        specs[f"ink{k}"] = PR(_glitter(rng, f"gl{k}", col), 0.3, metal=0.7)
        specs[f"grip{k}"] = T(col, 0.3)
        specs[f"cap{k}"] = T(col, 0.1)
    b.frame = Matrix.Identity(4)
    if rng.random() < 0.5:
        b.box((0.012, n * 0.0135 + 0.004, 0.014), loc=(-0.005, 0, 0), mat="band", bevel=0.004)
        specs["band"] = RUB((0.85, 0.65, 0.4))
    return specs


MARKERS = [("CHERRY", (0.9, 0.08, 0.15)), ("BLUEBERRY", (0.15, 0.3, 0.95)), ("LICORICE", (0.06, 0.06, 0.07)),
           ("LIME", (0.4, 0.85, 0.15)), ("ORANGE", (1.0, 0.5, 0.05)), ("GRAPE", (0.5, 0.15, 0.7)),
           ("CINNAMON", (0.55, 0.25, 0.1)), ("MINT", (0.1, 0.75, 0.6)), ("BANANA", (1.0, 0.88, 0.1))]
SNIFF = ["DO NOT EAT", "SNIFF RESPONSIBLY", "SMELLS LIKE 3RD GRADE", "NOT A SNACK", "TEACHER SAID STOP"]


def _marker_label(rng, name, flavor, col):
    c = _cv(320, 96, (0.97, 0.97, 0.95))
    c.rect(0, 0, 1, 1, (0.97, 0.97, 0.95))
    c.rect(0.0, 0.0, 0.22, 1.0, col)
    c.circle(0.11, 0.5, 0.3, (1, 1, 1))
    c.circle(0.11, 0.5, 0.22, col)
    c.poly([(0.105, 0.72), (0.13, 0.85), (0.15, 0.72)], (0.2, 0.7, 0.2))
    _lt(c, "MR. SKETCHY", 0.25, 0.85, 0.5, 0.3, (0.1, 0.1, 0.12))
    _lt(c, flavor, 0.25, 0.45, 0.5, 0.26, col)
    _lt(c, str(SNIFF[int(rng.integers(0, len(SNIFF)))]), 0.25, 0.15, 0.7, 0.11, (0.4, 0.4, 0.42), bold=False)
    c.noise(rng, 0.015)
    return _rot(c).image(name)


@obj("scented_markers", eras=(0, 1), mass=0.1, weight=1.1, tags=("school",))
def scented_markers(b, rng, pal):
    """Fat scented markers with fruit-colored caps; one cap is always missing and that one is dried out."""
    n = int(rng.integers(4, 7))
    pick = rng.permutation(len(MARKERS))[:n]
    specs = {"felt": P((0.2, 0.2, 0.2), 0.9)}
    for k, mi in enumerate(pick):
        flavor, col = MARKERS[int(mi)]
        y = (k - (n - 1) / 2) * 0.021
        x0 = float(rng.uniform(-0.006, 0.006))
        L = 0.105
        b.lathe([(0.0, -L / 2), (0.0085, -L / 2), (0.0095, -L / 2 + 0.004), (0.0095, L / 2 - 0.006), (0.0075, L / 2),
                 (0.0, L / 2)], loc=(x0, y, 0), rot=(0, PI / 2, 0), mat=f"label{k}", seg=18)
        capped = rng.random() < 0.75
        if capped:
            b.lathe([(0.0, 0.0), (0.0102, 0.0), (0.0102, 0.03), (0.009, 0.036), (0.006, 0.04), (0.0, 0.04)],
                    loc=(x0 + L / 2 - 0.012, y, 0), rot=(0, PI / 2, 0), mat=f"cap{k}", seg=18)
            b.box((0.025, 0.003, 0.003), loc=(x0 + L / 2 + 0.008, y, 0.0105), mat=f"cap{k}")
        else:
            b.cyl(0.0075, 0.008, r2=0.005, loc=(x0 + L / 2 + 0.004, y, 0), rot=(0, PI / 2, 0), mat=f"cap{k}", seg=14)
            b.box((0.012, 0.007, 0.003), loc=(x0 + L / 2 + 0.013, y, 0), rot=(0, 0.35, 0), mat="felt")
            specs["felt"] = P(col, 0.95)
        b.lathe([(0.0, 0.0), (0.0098, 0.0), (0.0098, 0.006), (0.0, 0.006)], loc=(x0 - L / 2 - 0.006, y, 0),
                rot=(0, PI / 2, 0), mat=f"cap{k}", seg=18)
        img = _marker_label(rng, f"mk{k}", flavor, col)
        specs[f"label{k}"] = PR(img, 0.35)
        specs[f"cap{k}"] = P(col, 0.3, coat=0.4)
    return specs


CRAYON_COLS = [(0.9, 0.1, 0.12), (1.0, 0.45, 0.1), (1.0, 0.85, 0.1), (0.3, 0.75, 0.2), (0.1, 0.45, 0.85),
               (0.45, 0.2, 0.7), (0.95, 0.4, 0.65), (0.45, 0.25, 0.12), (0.06, 0.06, 0.07), (0.95, 0.95, 0.92),
               (0.1, 0.75, 0.75), (0.75, 0.75, 0.2)]


def _crayon_box_print(rng, name, back=False):
    c = _cv(260, 280, (1.0, 0.84, 0.1))
    zig = (0.85, 0.1, 0.35)
    c.rect(0, 0, 1, 0.16, zig)
    _zig(c, 0, 1, 0.17, 0.035, 14, 0.035, zig)
    c.rect(0, 0.86, 1, 1.0, zig)
    _zig(c, 0, 1, 0.85, 0.035, 14, 0.035, zig)
    if back:
        c.rect(0.25, 0.3, 0.75, 0.7, (0.6, 0.6, 0.62))
        _ct(c, "SHARPENER", 0.5, 0.26, 0.8, 0.08, (0.2, 0.1, 0.4))
        _ct(c, "NOT FOR FINGERS", 0.5, 0.14, 0.8, 0.05, (1, 1, 1))
        return c.image(name)
    _ct(c, "CRAYOLOL", 0.5, 0.82, 0.9, 0.14, (0.25, 0.1, 0.5), out=(1, 1, 1))
    c.circle(0.5, 0.45, 0.17, (0.25, 0.1, 0.5))
    c.circle(0.5, 0.45, 0.14, (1, 1, 1), ring=0.012)
    _ct(c, "64", 0.5, 0.53, 0.25, 0.17, (1, 1, 1))
    _ct(c, "CRAYONS", 0.5, 0.36, 0.25, 0.05, (1, 1, 1))
    _ct(c, "WITH BUILT-IN SHARPENER", 0.5, 0.25, 0.9, 0.055, (0.25, 0.1, 0.5))
    for i in range(6):
        x = 0.1 + i * 0.16
        col = CRAYON_COLS[i]
        c.rect(x - 0.025, 0.02, x + 0.025, 0.12, col)
        c.poly([(x - 0.025, 0.12), (x + 0.025, 0.12), (x, 0.15)], col)
    _ct(c, "NON-TOXIC (WE CHECKED)", 0.5, 0.665, 0.8, 0.035, (0.25, 0.1, 0.5), bold=False)
    c.noise(rng, 0.015)
    return c.image(name)


@obj("crayon_box", eras=(0, 1, 2), mass=0.4, weight=1.2, hero=(0, -1, 0.7), tags=("school",))
def crayon_box(b, rng, pal):
    """The 64-box: stadium seating for crayons, the sharpener in the back, half the points already gone."""
    W, D, H = 0.13, 0.05, 0.14
    b.box((W, D, H), mat="box", bevel=0.0015)
    b.plane(W, H, loc=(0, -D / 2 - 0.0004, 0), rot=(PI / 2, 0, 0), mat="front", cuts=3)
    b.plane(W, H, loc=(0, D / 2 + 0.0004, 0), rot=(PI / 2, 0, PI), mat="back", cuts=3)
    b.box((0.04, 0.012, 0.03), loc=(0, D / 2 + 0.006, -0.02), mat="sharp", bevel=0.002)
    b.cyl(0.006, 0.006, loc=(0, D / 2 + 0.0125, -0.02), rot=(PI / 2, 0, 0), mat="hole", seg=12)
    b.box((W, 0.002, 0.045), loc=(0, D / 2 + 0.008, H / 2 + 0.02), rot=(-0.35, 0, 0), mat="box")    # open lid
    for row in range(4):
        y = -D / 2 + 0.0065 + row * 0.0123
        for i in range(16):
            x = -W / 2 + 0.0045 + i * (W - 0.009) / 15
            if rng.random() < 0.06:
                continue
            k = int(rng.integers(0, len(CRAYON_COLS)))
            top = H / 2 + 0.004 + row * 0.011 + float(rng.uniform(-0.003, 0.002))
            b.cyl(0.0037, 0.04, loc=(x, y, top - 0.02), mat=f"c{k}", seg=8)
            dull = rng.random() < 0.35
            b.cyl(0.0037, 0.009 if not dull else 0.005, r2=0.0008 if not dull else 0.0022,
                  loc=(x, y, top + (0.0045 if not dull else 0.0025)), mat=f"c{k}", seg=8)
    specs = {"box": P((1.0, 0.84, 0.1), 0.6), "front": PR(_crayon_box_print(rng, "cb"), 0.6),
             "back": PR(_crayon_box_print(rng, "cbb", back=True), 0.6), "sharp": P((0.6, 0.6, 0.62), 0.4),
             "hole": P(BLACK, 0.8)}
    for k, col in enumerate(CRAYON_COLS):
        specs[f"c{k}"] = ("wax", {"color": col})
    return specs


def _lunch_art(rng, name, w=320, h=220):
    c = _show_art(rng, name, w, h)
    c.rect(0, 0, 1, 0.025, (0.6, 0.6, 0.62))
    c.rect(0, 0.975, 1, 1, (0.6, 0.6, 0.62))
    return c


def _thermos(b, rng, loc, rot, art_mat, cup_mat):
    L = 0.12
    b.lathe([(0.0, 0.0), (0.024, 0.0), (0.026, 0.004), (0.026, L * 0.8), (0.022, L * 0.86), (0.0, L * 0.86)],
            loc=loc, rot=rot, mat=art_mat, seg=22)
    b.lathe([(0.0, L * 0.83), (0.028, L * 0.83), (0.029, L), (0.0, L)], loc=loc, rot=rot, mat=cup_mat, seg=22)


@obj("tin_lunchbox", eras=(0, 1), mass=0.8, weight=1.1, big=True, hero=(0, -1, 0.3), tags=("school", "lunch"))
def tin_lunchbox(b, rng, pal):
    """The embossed metal lunch box with a Saturday-morning cartoon on it, and its matching plastic thermos."""
    W, D, H = 0.2, 0.09, 0.155
    b.box((W, D, H), mat="tin", bevel=0.004)
    b.box((W + 0.003, D + 0.003, 0.004), loc=(0, 0, H / 2 - 0.035), mat="tin", bevel=0.0012)        # lid lip
    b.plane(W * 0.9, H * 0.66, loc=(0, -D / 2 - 0.0006, -0.012), rot=(PI / 2, 0, 0), mat="art", cuts=4)
    b.plane(W * 0.9, H * 0.66, loc=(0, D / 2 + 0.0006, -0.012), rot=(PI / 2, 0, PI), mat="art2", cuts=4)
    b.plane(W * 0.9, D * 0.8, loc=(0, 0, H / 2 + 0.0006), mat="top", cuts=3)
    b.box((0.028, 0.006, 0.02), loc=(0, -D / 2 - 0.004, H / 2 - 0.03), mat="latch", bevel=0.0015)
    for s in (-1, 1):
        b.box((0.016, 0.022, 0.01), loc=(s * 0.045, 0, H / 2 + 0.004), mat="handle", bevel=0.002)
    b.tube([(-0.045, 0, H / 2 + 0.008), (-0.04, 0, H / 2 + 0.028), (0.0, 0, H / 2 + 0.032), (0.04, 0, H / 2 + 0.028),
            (0.045, 0, H / 2 + 0.008)], 0.0055, mat="handle", seg=8)
    art = _lunch_art(rng, "lb")
    top = _cv(256, 110, NEON[int(rng.integers(0, len(NEON)))])
    _memphis(top, rng, [(1, 1, 1)] + NEON, 18)
    specs = {"tin": MET(tuple(float(v) for v in art.a[art.h - 2, 3, :3]), 0.35),
             "art": PR(art.image("lba"), 0.25, metal=0.35), "art2": PR(_lunch_art(rng, "lbb").image("lbb"), 0.25, metal=0.35),
             "top": PR(top.image("lbt"), 0.25, metal=0.35), "latch": CHROME(), "handle": P(BLACK, 0.4)}
    if rng.random() < 0.8:
        th = _show_art(rng, "th", 256, 128)
        _thermos(b, rng, (W / 2 + 0.034, -0.01, -H / 2), (0, 0, PI / 2), "thermos", "cup")
        specs["thermos"] = PR(th.image("tha"), 0.3)
        specs["cup"] = P((0.85, 0.1, 0.1) if rng.random() < 0.5 else (0.1, 0.3, 0.85), 0.35)
    return specs


@obj("plastic_lunchbox", eras=(1, 2), mass=0.5, weight=1.1, big=True, hero=(0, -1, 0.3), tags=("school", "lunch"))
def plastic_lunchbox(b, rng, pal):
    """The molded plastic one that replaced the tin: fat rounded corners, two-tone, a raised sticker panel."""
    W, D, H = 0.2, 0.1, 0.15
    base = NEON[int(rng.integers(0, len(NEON)))]
    lid = [(0.95, 0.95, 0.95), (0.55, 0.2, 0.95), (0.1, 0.8, 0.85), (1.0, 0.2, 0.6)][int(rng.integers(0, 4))]
    b.box((W, D, H * 0.75), loc=(0, 0, -H * 0.125), mat="base", bevel=0.024, seg=4)
    b.box((W + 0.004, D + 0.004, H * 0.3), loc=(0, 0, H * 0.33), mat="lid", bevel=0.022, seg=4)
    b.box((W * 0.74, 0.01, H * 0.5), loc=(0, -D / 2 - 0.002, -H * 0.12), mat="base", bevel=0.008)       # sticker panel
    b.plane(W * 0.68, H * 0.44, loc=(0, -D / 2 - 0.0075, -H * 0.12), rot=(PI / 2, 0, 0), mat="art", cuts=3)
    for s in (-1, 1):                  # snap latches on the ends
        b.box((0.012, 0.03, 0.04), loc=(s * (W / 2 + 0.004), 0, H * 0.2), mat="lid", bevel=0.004)
    b.box((0.12, 0.024, 0.01), loc=(0, 0, H / 2 + 0.03), mat="lid", bevel=0.005)                       # molded handle
    for s in (-1, 1):
        b.box((0.016, 0.024, 0.03), loc=(s * 0.052, 0, H / 2 + 0.018), mat="lid", bevel=0.005)
    art = _show_art(rng, "plb", 288, 192)
    return {"base": P(base, 0.3, coat=0.4), "lid": P(lid, 0.3, coat=0.4), "art": PR(art.image("plba"), 0.25)}


# =====================================================================================================
# B) LUNCH TRADE
# =====================================================================================================

LUNCH = dict(tags=("lunch",))


def _launch_sleeve(rng, name):
    c = _cv(256, 300, (1.0, 0.85, 0.1))
    c.rect(0, 0.0, 1, 0.12, (0.85, 0.08, 0.1))
    c.rect(0, 0.62, 1, 1.0, (0.1, 0.25, 0.75))
    _ct(c, "LAUNCHABLES", 0.5, 0.93, 0.92, 0.14, (1.0, 0.85, 0.1), out=(0.85, 0.08, 0.1))
    _ct(c, "TURKEY-ISH & CHEDDAR-ADJACENT", 0.5, 0.74, 0.9, 0.06, (1, 1, 1))
    for i in range(4):                       # the build-your-own stack drawing
        y = 0.25 + i * 0.07
        c.circle(0.32, y, 0.11, (0.9, 0.75, 0.45) if i % 3 == 0 else (0.95, 0.65, 0.65) if i % 3 == 1 else (1, 0.75, 0.2))
    _burst(c, 0.73, 0.38, 0.15, (0.85, 0.08, 0.1), ring=(1, 1, 1))
    _ct(c, "BUILD", 0.73, 0.45, 0.2, 0.06, (1, 1, 1))
    _ct(c, "YOUR OWN", 0.73, 0.38, 0.2, 0.045, (1, 1, 1))
    _ct(c, "REGRET", 0.73, 0.31, 0.2, 0.05, (1, 1, 1))
    _ct(c, "CRACKERS, CHEESE & A LITTLE SAD MEAT", 0.5, 0.09, 0.94, 0.05, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("launchables", eras=(1, 2), mass=0.12, weight=1.2, group="era", **LUNCH)
def launchables(b, rng, pal):
    """The build-it-yourself lunch tray: crackers, cheese squares, meat circles, yellow sleeve half off."""
    W, D, H = 0.16, 0.11, 0.024
    b.box((W, D, 0.002), loc=(0, 0, -H / 2), mat="tray")
    for x in (-W / 2, -W / 6, W / 6, W / 2):
        b.box((0.002, D, H), loc=(x, 0, 0), mat="tray")
    for y in (-D / 2, D / 2):
        b.box((W, 0.002, H), loc=(0, y, 0), mat="tray")
    for i in range(7):          # crackers on edge in the left well
        b.cyl(0.021, 0.0042, loc=(-W / 3 - 0.012 + i * 0.0045, 0, 0.004), rot=(0, PI / 2 + 0.25, 0), mat="cracker", seg=18)
    for i in range(6):          # cheese squares
        b.box((0.042, 0.042, 0.003), loc=(0, 0.002 * (i % 2), -H / 2 + 0.003 + i * 0.0032), rot=(0, 0, 0.12 * (i % 3)),
              mat="cheese")
    for i in range(5):          # meat rounds
        b.cyl(0.022, 0.0022, loc=(W / 3, 0, -H / 2 + 0.003 + i * 0.0025), mat="meat", seg=20)
    sx = -W / 2 + 0.01
    b.box((0.09, D + 0.006, 0.0015), loc=(sx, 0, H / 2 + 0.002), mat="sleeve")
    b.box((0.09, D + 0.006, 0.0015), loc=(sx, 0, -H / 2 - 0.002), mat="sleeve")
    for y in (-D / 2 - 0.003, D / 2 + 0.003):
        b.box((0.09, 0.0015, H + 0.005), loc=(sx, y, 0), mat="sleeve")
    b.plane(0.088, D + 0.004, loc=(sx, 0, H / 2 + 0.0029), mat="print", cuts=3)
    return {"tray": P((0.95, 0.95, 0.93), 0.2, coat=0.6), "cracker": ("crust", {"color": (0.88, 0.72, 0.42)}),
            "cheese": P((1.0, 0.7, 0.15), 0.5), "meat": P((0.92, 0.62, 0.6), 0.45), "sleeve": P((1.0, 0.85, 0.1), 0.6),
            "print": PR(_launch_sleeve(rng, "ls"), 0.55)}


def _pouch_print(rng, name):
    c = _cv(512, 384, (0.82, 0.83, 0.86))
    for half in (0.25, 0.75):
        x0 = half - 0.22
        c.circle(half, 0.62, 0.17, (1.0, 0.75, 0.1))
        for i in range(12):
            t = 2 * PI * i / 12
            c.line([(half + 0.09 * math.cos(t), 0.62 + 0.18 * math.sin(t)),
                    (half + 0.12 * math.cos(t), 0.62 + 0.26 * math.sin(t))], 0.02, (1.0, 0.6, 0.1))
        for k in range(3):
            _squig(c, x0, x0 + 0.44, 0.28 - k * 0.06, 0.02, 0.025, (0.1, 0.4 + k * 0.15, 0.85), f=3)
        _ct(c, "CAPRI SUNK", half, 0.92, 0.42, 0.16, (0.05, 0.25, 0.7), out=(1, 1, 1))
        _ct(c, str(rng.choice(["PACIFIC COOLER-ISH", "MOUNTAIN COOLER", "WILD CHERRY", "STRAWBERRY KIWI COPE"])),
            half, 0.4, 0.42, 0.06, (0.85, 0.1, 0.2))
        _ct(c, "10% JUICE. 90% FOIL.", half, 0.12, 0.4, 0.05, (0.15, 0.15, 0.2))
    c.noise(rng, 0.015)
    return c.image(name)


def _pouch(b, w, h, t, mat, loc=(0, 0, 0), n=24, rings=14):
    rs = []
    for j in range(rings):
        z = h * j / (rings - 1)
        u = z / h
        th = t * (0.8 + 0.2 * math.sin(u * PI)) * (1 - u ** 3) + 0.0006
        ww = w * (1.0 - 0.06 * (1 - u) ** 6)
        rs.append([(loc[0] + ww / 2 * math.cos(2 * PI * i / n), loc[1] + th / 2 * math.sin(2 * PI * i / n), loc[2] + z)
                   for i in range(n)])
    b.loft(rs, mat=mat)


@obj("drink_pouch", eras=(0, 1, 2, 3), mass=0.03, weight=1.2, group="era", hero=(0, -1, 0), **LUNCH)
def drink_pouch(b, rng, pal):
    """The foil drink pouch, straw stabbed through the dot on the third try."""
    w, h = 0.1, 0.15
    _pouch(b, w, h, 0.034, "foil", loc=(0, 0, -h / 2))
    b.box((w, 0.0015, 0.014), loc=(0, 0, h / 2 - 0.006), mat="seal")
    hit = rng.random() < 0.8
    if hit:
        b.tube([(0.028, -0.004, h / 2 - 0.035), (0.03, -0.012, h / 2 + 0.02), (0.031, -0.016, h / 2 + 0.05)], 0.0028,
               mat="straw", seg=8)
    else:
        b.tube([(0.02, -0.03, -h / 2 + 0.01), (0.07, -0.04, -h / 2 + 0.005), (0.12, -0.035, -h / 2 + 0.006)], 0.0028,
               mat="straw", seg=8)
    return {"foil": PR(_pouch_print(rng, "cp"), 0.2, metal=0.55), "seal": MET((0.8, 0.8, 0.82), 0.25),
            "straw": P((0.95, 0.95, 0.97), 0.3)}


def _wrap_label(rng, name, w, h, bg, title, sub, col, out=(1, 1, 1), sun=False):
    """A label that wraps a lathe: art repeated at u=0.25 and u=0.75 so it faces both ways."""
    c = _cv(w, h, bg)
    for half in (0.25, 0.75):
        if sun:
            _burst(c, half, 0.55, 0.32, (1.0, 0.85, 0.1), n=18)
        _ct(c, title, half, 0.72, 0.44, 0.34, col, out=out)
        _ct(c, sub, half, 0.24, 0.44, 0.13, col)
    c.noise(rng, 0.012)
    return c.image(name)


@obj("orange_jug", eras=(1, 2), mass=0.6, weight=1.0, group="special", hero=(0, -1, 0), **LUNCH)
def orange_jug(b, rng, pal):
    """The orange 'drink' jug every mom thought was juice. It was not juice."""
    prof = [(0.0, -0.09), (0.036, -0.09), (0.042, -0.08), (0.043, -0.03), (0.039, -0.02), (0.039, 0.03),
            (0.043, 0.04), (0.04, 0.065), (0.02, 0.085), (0.016, 0.09), (0.0, 0.09)]
    b.lathe(prof, mat="drink", seg=28)
    b.lathe([(0.0, -0.02), (0.0402, -0.022), (0.0402, 0.032), (0.0, 0.03)], mat="label", seg=28)
    b.lathe([(0.0, 0.088), (0.018, 0.088), (0.018, 0.108), (0.0, 0.108)], mat="cap", seg=20)
    for i in range(10):
        b.box((0.002, 0.002, 0.018), loc=(0.018 * math.cos(i * 0.628), 0.018 * math.sin(i * 0.628), 0.098),
              rot=(0, 0, i * 0.628), mat="cap")
    img = _wrap_label(rng, "sd", 384, 96, (1.0, 0.55, 0.05), "SUNNY D-GEN", "TANGY ORANGE-ISH. 2% JUICE",
                      (0.05, 0.25, 0.7), sun=True)
    return {"drink": P((1.0, 0.5, 0.05), 0.12, coat=1.0), "label": PR(img, 0.3),
            "cap": P(tuple(rng.choice([(0.05, 0.05, 0.07), (0.95, 0.95, 0.95), (1.0, 0.85, 0.1)])), 0.4)}


def _foil_top(rng, name, col):
    c = _cv(96, 96, (0.85, 0.85, 0.88))
    c.circle(0.5, 0.5, 0.42, col)
    _ct(c, "LITTLE", 0.5, 0.66, 0.7, 0.16, (1, 1, 1))
    _ct(c, "SHRUG", 0.5, 0.44, 0.7, 0.18, (1, 1, 1))
    return c.image(name)


@obj("mini_barrels", eras=(1, 2), mass=0.12, weight=1.0, group="special", **LUNCH)
def mini_barrels(b, rng, pal):
    """Twist-top mini barrels of colored sugar water. The blue one was the currency of the lunch table."""
    cols = [(0.95, 0.1, 0.15), (0.1, 0.4, 1.0), (0.55, 0.2, 0.85), (0.3, 0.9, 0.2), (1.0, 0.55, 0.05)]
    n = int(rng.integers(3, 6))
    order = rng.permutation(len(cols))[:n]
    specs = {}
    for k, ci in enumerate(order):
        x, y = (k % 3 - 1) * 0.042 + float(rng.normal(0, 0.003)), (k // 3) * 0.044 - 0.02
        tipped = rng.random() < 0.3
        rot = (PI / 2, 0, float(rng.uniform(0, 6.28))) if tipped else (0, 0, 0)
        z = 0.0 if not tipped else -0.006
        b.lathe([(0.0, -0.026), (0.015, -0.026), (0.019, -0.012), (0.0195, 0.0), (0.019, 0.012), (0.015, 0.024),
                 (0.0, 0.024)], loc=(x, y, z), rot=rot, mat=f"bar{k}", seg=22)
        for hz in (-0.016, 0.014):
            b.lathe([(0.0, hz - 0.002), (0.0192, hz - 0.002), (0.0198, hz), (0.0192, hz + 0.002), (0.0, hz + 0.002)],
                    loc=(x, y, z), rot=rot, mat=f"hoop{k}", seg=22)
        if tipped:
            b.extrude(ellipse(0.03, 0.03, 20), 0.002, loc=(x, y - 0.025, z), rot=(PI / 2, 0, 0), mat=f"top{k}")
        else:
            b.extrude(ellipse(0.03, 0.03, 20), 0.002, loc=(x, y, 0.025), mat=f"top{k}")
        specs[f"bar{k}"] = T(cols[int(ci)], 0.12)
        specs[f"hoop{k}"] = T(tuple(v * 0.7 for v in cols[int(ci)]), 0.2)
        specs[f"top{k}"] = PR(_foil_top(rng, f"lt{k}", cols[int(ci)]), 0.25, metal=0.6)
    return specs


@obj("squeeze_buddy", eras=(1, 2), mass=0.08, weight=1.0, group="special", hero=(0, -1, 0), **LUNCH)
def squeeze_buddy(b, rng, pal):
    """A character-shaped squeeze drink: twist off his head, squeeze his guts out. That's lunch."""
    col = [(0.95, 0.1, 0.2), (0.1, 0.5, 1.0), (0.4, 0.9, 0.2), (0.6, 0.2, 0.9), (1.0, 0.5, 0.05)][int(rng.integers(0, 5))]
    b.lathe([(0.0, -0.06), (0.019, -0.06), (0.023, -0.05), (0.024, -0.01), (0.021, 0.02), (0.016, 0.035),
             (0.011, 0.04), (0.0, 0.04)], mat="body", seg=24)
    b.lathe([(0.0, -0.035), (0.0242, -0.035), (0.0242, -0.012), (0.0, -0.012)], mat="label", seg=24)
    b.lathe([(0.0, 0.038), (0.016, 0.038), (0.019, 0.05), (0.018, 0.062), (0.012, 0.07), (0.0, 0.072)], mat="head",
            seg=20)
    b.cyl(0.024, 0.003, loc=(0, 0, 0.068), mat="head", seg=20)                    # tiny hat brim
    b.cyl(0.011, 0.012, loc=(0, 0, 0.076), mat="head", seg=16)
    for s in (-1, 1):
        b.sphere(0.0062, loc=(s * 0.0065, -0.0155, 0.056), mat="eye", seg=10)
        b.sphere(0.0028, loc=(s * 0.006, -0.021, 0.0555), mat="pupil", seg=8)
        b.tube([(s * 0.021, -0.005, 0.0), (s * 0.03, -0.008, -0.012), (s * 0.027, -0.012, -0.024)], 0.004, mat="body",
               seg=6)
    b.torus(0.007, 0.0014, loc=(0, -0.017, 0.047), rot=(PI / 2, 0, PI), arc=PI, mat="pupil", seg=10, rseg=4)
    nm = str(rng.choice(["BERRY B. LOONY", "GRAPE APE-IT", "CHERRY CHUCKLES", "LEMON LEROY", "BLUE BLOOPER"]))
    img = _wrap_label(rng, "sq", 384, 72, (1, 1, 1), "SQUEEZURZ", nm, col, out=(0.05, 0.05, 0.07))
    return {"body": T(col, 0.12), "label": PR(img, 0.35), "head": P(col, 0.3, coat=0.5), "eye": P(WHITE, 0.2),
            "pupil": P(BLACK, 0.3)}


def _dip_lid(rng, name):
    c = _cv(256, 160, (0.8, 0.82, 0.86))
    c.rect(0.03, 0.05, 0.97, 0.95, (0.15, 0.5, 0.9))
    _critter(c, 0.2, 0.45, 0.17, (0.65, 0.6, 0.62), rng, kind=2, shades=True)
    _ct(c, "PLUNKAROOS", 0.62, 0.85, 0.66, 0.2, (1.0, 0.85, 0.1), out=(0.85, 0.1, 0.3))
    _ct(c, "COOKIES + FROSTING", 0.62, 0.52, 0.62, 0.09, (1, 1, 1))
    _ct(c, "= A FOOD GROUP", 0.62, 0.36, 0.62, 0.09, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("frosting_dip", eras=(1, 2), mass=0.05, weight=1.0, group="special", **LUNCH)
def frosting_dip(b, rng, pal):
    """Cookies plus a well of frosting with sprinkles, foil lid peeled back. Everyone traded up for these."""
    W, D, H = 0.1, 0.06, 0.016
    b.extrude(rounded_rect(W, D, 0.01, 4), 0.003, loc=(0, 0, -H / 2), mat="tray")
    b.extrude(rounded_rect(W, D, 0.01, 4), H, mat="tray")
    frost = [(0.98, 0.95, 0.85), (1.0, 0.7, 0.8), (0.55, 0.32, 0.16)][int(rng.integers(0, 3))]
    b.sphere(0.022, loc=(W / 4, 0, H / 2), scale=(1.0, 1.15, 0.28), mat="frost", seg=20)
    scols = [(1, 0.2, 0.3), (0.2, 0.5, 1.0), (1.0, 0.9, 0.1), (0.3, 0.9, 0.3)]
    for i in range(26):
        a, r = float(rng.uniform(0, 6.28)), float(rng.uniform(0, 0.018))
        b.cyl(0.0009, 0.004, loc=(W / 4 + r * math.cos(a), r * math.sin(a) * 1.1, H / 2 + 0.005),
              rot=(PI / 2, 0, float(rng.uniform(0, 6.28))), mat=f"spr{i % 4}", seg=5)
    for i in range(9):
        x, y = -W / 4 + float(rng.normal(0, 0.012)), float(rng.normal(0, 0.012))
        z = H / 2 + float(rng.uniform(-0.002, 0.004))
        if i % 3 == 0:
            b.extrude([(0.008 * math.cos(PI / 2 + PI * k / 5) * (1 if k % 2 == 0 else 0.5),
                        0.008 * math.sin(PI / 2 + PI * k / 5) * (1 if k % 2 == 0 else 0.5)) for k in range(10)], 0.003,
                      loc=(x, y, z), rot=(float(rng.normal(0, 0.3)), float(rng.normal(0, 0.3)), 0), mat="cookie")
        else:
            b.cyl(0.0065, 0.003, loc=(x, y, z), rot=(float(rng.normal(0, 0.4)), float(rng.normal(0, 0.4)), 0),
                  mat="cookie", seg=12)
    th = 1.15
    b.plane(W, D, loc=(0, D / 2 + math.cos(th) * D / 2, H / 2 + math.sin(th) * D / 2), rot=(th, 0, 0), mat="lid", cuts=3)
    specs = {"tray": P((0.97, 0.97, 0.97), 0.3), "frost": P(frost, 0.4), "cookie": ("crust", {"color": (0.82, 0.6, 0.35)}),
             "lid": PR(_dip_lid(rng, "dl"), 0.25, metal=0.4)}
    for i, sc in enumerate(scols):
        specs[f"spr{i}"] = P(sc, 0.4)
    return specs


def _gusher_box(rng, name):
    c = _cv(220, 280, (0.45, 0.1, 0.65))
    _burst(c, 0.5, 0.58, 0.45, (0.95, 0.1, 0.45), n=22)
    for i in range(7):
        x = 0.12 + i * 0.13
        c.circle(x, 0.22 + 0.03 * math.sin(i * 2), 0.06, NEON[i % len(NEON)])
        c.line([(x, 0.2), (x + 0.01, 0.1)], 0.02, NEON[i % len(NEON)])
    _ct(c, "FRUIT", 0.5, 0.85, 0.8, 0.12, (1, 1, 1), out=(0.1, 0.0, 0.2))
    _ct(c, "GUSHIES", 0.5, 0.7, 0.92, 0.17, (0.4, 1.0, 0.2), out=(0.1, 0.0, 0.2))
    _ct(c, "MOUTH FLOOD GUARANTEED", 0.5, 0.45, 0.9, 0.05, (1, 1, 1))
    _ct(c, "6 POUCHES - 0 FRUIT", 0.5, 0.08, 0.9, 0.045, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("gusher_box", eras=(1, 2), mass=0.1, weight=1.1, group="era", hero=(0, -1, 0.4), **LUNCH)
def gusher_box(b, rng, pal):
    """The box of liquid-center fruit snacks, one pouch torn open and spilling."""
    W, D, H = 0.085, 0.03, 0.11
    b.box((W, D, H), loc=(0, 0.02, 0), mat="box", bevel=0.001)
    b.plane(W, H, loc=(0, 0.02 - D / 2 - 0.0004, 0), rot=(PI / 2, 0, 0), mat="print", cuts=3)
    b.box((0.06, 0.045, 0.006), loc=(0.01, -0.04, -H / 2 + 0.004), rot=(0, 0, 0.3), mat="pouch", bevel=0.0028)
    cols = [(0.9, 0.1, 0.2), (0.2, 0.4, 1.0), (0.4, 0.9, 0.2), (0.9, 0.4, 0.8)]
    for i in range(int(rng.integers(5, 9))):
        x, y = float(rng.uniform(-0.04, 0.05)), float(rng.uniform(-0.075, -0.02))
        b.sphere(0.0075, loc=(x, y, -H / 2 + 0.01), scale=(1.1, 1.0, 0.75), mat=f"g{i % 4}", seg=12)
    specs = {"box": P((0.45, 0.1, 0.65), 0.5), "print": PR(_gusher_box(rng, "gb"), 0.4),
             "pouch": MET((0.6, 0.3, 0.75), 0.25)}
    for i, col in enumerate(cols):
        specs[f"g{i}"] = T(col, 0.25)
    return specs


def _ribbon(b, pts, w, mat, side=None):
    rings = []
    for i, p in enumerate(pts):
        a, c = np.array(pts[max(i - 1, 0)]), np.array(pts[min(i + 1, len(pts) - 1)])
        t = c - a
        t = t / (np.linalg.norm(t) + 1e-9)
        s = np.array(side) if side is not None else np.cross(t, (0, 0, 1))
        s = s / (np.linalg.norm(s) + 1e-9)
        p = np.array(p)
        rings.append([tuple(p - s * w / 2), tuple(p + s * w / 2)])
    return b.loft(rings, mat=mat, cap=False, closed=False)


JOKES = ["KNOCK KNOCK. WHO'S THERE. LUNCH.", "WHY DID THE FRUIT CROSS THE ROAD", "TONGUE TATTOO INSIDE (NOT REALLY)",
         "MEASURE YOUR FRIENDS", "THIS IS 36 INCHES OF FOOD", "WHAT'S PURPLE AND COSTS A DOLLAR"]


def _strip_paper(rng, name):
    c = _cv(512, 64, (0.97, 0.97, 0.95))
    x = 0.01
    i = 0
    while x < 0.95:
        s = "FRUIT BY THE YARD" if i % 2 == 0 else str(JOKES[int(rng.integers(0, len(JOKES)))])
        x = c.text(s, x, 0.78, 0.55, (0.15, 0.3, 0.85) if i % 2 else (0.85, 0.1, 0.2), bold=i % 2 == 0) + 0.03
        i += 1
    for k in range(40):
        c.rect(k / 40, 0.0, k / 40 + 0.002, 0.15, (0.3, 0.3, 0.35))
    return _rot(c).image(name)


@obj("fruit_strip", eras=(1, 2, 3), mass=0.03, weight=1.1, group="era", **LUNCH)
def fruit_strip(b, rng, pal):
    """Three feet of rolled fruit leather, half unrolled, paper backing printed with jokes nobody laughed at."""
    col = [(0.85, 0.05, 0.15), (0.2, 0.4, 0.9), (0.95, 0.4, 0.1), (0.5, 0.1, 0.6)][int(rng.integers(0, 4))]
    b.cyl(0.02, 0.025, loc=(-0.075, 0, 0.02), rot=(PI / 2, 0, 0), mat="fruit", seg=22)
    b.cyl(0.0205, 0.0255, loc=(-0.075, 0, 0.02), rot=(PI / 2, 0, 0), mat="paperroll", seg=22, cap=False)
    n = 18
    L = 0.19
    pts = [(-0.075 + L * i / (n - 1), 0.004 * math.sin(i * 0.7), 0.001 + 0.002 * math.sin(i * 1.3)) for i in range(n)]
    pts[0] = (-0.075, 0, 0.0005)
    _ribbon(b, pts, 0.025, "paper")
    fp = [p for p in pts[:int(n * 0.55)]]
    _ribbon(b, [(x, y, z + 0.0012) for x, y, z in fp], 0.0245, "fruit")
    return {"fruit": P(col, 0.25, coat=0.8), "paperroll": PR(_strip_paper(rng, "fbr"), 0.8),
            "paper": PR(_strip_paper(rng, "fby"), 0.8)}


@obj("ring_candy", eras=(1, 2, 3), mass=0.02, weight=1.1, group="era", **LUNCH)
def ring_candy(b, rng, pal):
    """The giant-jewel candy ring. Worn for status, licked in public, sticky until Thursday."""
    col = [(0.95, 0.05, 0.25), (0.1, 0.4, 1.0), (0.95, 0.35, 0.65), (0.4, 0.9, 0.15), (1.0, 0.55, 0.05)][int(rng.integers(0, 5))]
    band = NEON[int(rng.integers(0, len(NEON)))]
    b.torus(0.011, 0.0028, loc=(0, 0, -0.012), rot=(PI / 2, 0, 0), mat="band", seg=20, rseg=8)
    b.cyl(0.011, 0.008, r2=0.013, loc=(0, 0, 0.002), mat="band", seg=16)
    b.cyl(0.017, 0.007, r2=0.012, loc=(0, 0, 0.0095), mat="gem", seg=8)       # pavilion
    b.cyl(0.017, 0.003, loc=(0, 0, 0.0145), mat="gem", seg=8)                   # girdle
    b.cyl(0.017, 0.008, r2=0.009, loc=(0, 0, 0.02), mat="gem", seg=8)           # crown + table
    return {"band": P(band, 0.3, coat=0.5), "gem": P(col, 0.05, coat=1.0)}


def _pushpop_label(rng, name, col):
    c = _cv(384, 96, col)
    for i in range(10):
        c.rect(i / 10, 0.0, i / 10 + 0.05, 1.0, tuple(min(1, v * 1.2 + 0.1) for v in col))
    c.rect(0, 0.3, 1, 0.75, (0.05, 0.05, 0.07))
    _ct(c, "SHOVE POP", 0.5, 0.7, 0.7, 0.38, (1.0, 0.9, 0.1))
    c.text("DON'T LET YOUR POP GO SOFT", 0.05, 0.22, 0.12, (1, 1, 1))
    return _rot(c).image(name)


@obj("push_pop", eras=(1, 2), mass=0.03, weight=1.0, group="special", **LUNCH)
def push_pop(b, rng, pal):
    col = [(0.95, 0.1, 0.25), (0.1, 0.45, 1.0), (0.45, 0.9, 0.15), (1.0, 0.5, 0.05)][int(rng.integers(0, 4))]
    rot = (0, PI / 2, 0)
    b.lathe([(0.0, -0.05), (0.0125, -0.05), (0.0125, 0.03), (0.0, 0.03)], rot=rot, mat="label", seg=20)
    b.lathe([(0.0, 0.03), (0.0105, 0.03), (0.0105, 0.055), (0.009, 0.06), (0.0, 0.061)], rot=rot, mat="candy", seg=20)
    b.lathe([(0.0, 0.028), (0.0135, 0.028), (0.0135, 0.066), (0.0, 0.068)], rot=rot, mat="cap", seg=20)
    b.lathe([(0.0, -0.065), (0.004, -0.065), (0.004, -0.05), (0.0, -0.05)], rot=rot, mat="stick", seg=12)
    b.lathe([(0.0, -0.07), (0.011, -0.07), (0.011, -0.065), (0.0, -0.065)], rot=rot, mat="stick", seg=16)
    return {"label": PR(_pushpop_label(rng, "pp", col), 0.4), "candy": P(col, 0.08, coat=1.0), "cap": T((0.95, 0.97, 1.0), 0.05),
            "stick": P(col, 0.35)}


def _sour_print(rng, name):
    c = _cv(256, 160, (0.05, 0.05, 0.07))
    c.rect(0, 0, 0.1, 1, (0.4, 1.0, 0.1))
    c.rect(0.9, 0, 1, 1, (0.4, 1.0, 0.1))
    c.circle(0.3, 0.45, 0.28, (0.4, 1.0, 0.1))
    for s in (-1, 1):
        x = 0.3 + s * 0.07
        c.line([(x - 0.03, 0.58), (x + 0.03, 0.5)], 0.04, (0.05, 0.05, 0.07))
        c.line([(x - 0.03, 0.5), (x + 0.03, 0.58)], 0.04, (0.05, 0.05, 0.07))
    _zig(c, 0.2, 0.4, 0.32, 0.03, 6, 0.035, (0.05, 0.05, 0.07))
    for k in range(3):
        c.line([(0.12 + k * 0.05, 0.8), (0.1 + k * 0.05, 0.92)], 0.03, (1, 1, 1))
    _ct(c, "WAR", 0.7, 0.9, 0.36, 0.22, (1.0, 0.9, 0.1))
    _ct(c, "HEAD", 0.7, 0.66, 0.36, 0.2, (1.0, 0.9, 0.1))
    _ct(c, "ACHE", 0.7, 0.44, 0.36, 0.2, (0.4, 1.0, 0.1))
    _ct(c, "EXTREME SOUR", 0.7, 0.18, 0.34, 0.08, (1, 1, 1))
    c.text("SIDE EFFECTS: FACE", 0.18, 0.08, 0.06, (0.6, 0.6, 0.6))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("sour_pack", eras=(1, 2), mass=0.03, weight=1.0, group="special", **LUNCH)
def sour_pack(b, rng, pal):
    """The face-melting sour candy bag, a few twist-wrapped pieces loose. Held in mouth for 30 seconds on a dare."""
    b.box((0.08, 0.05, 0.009), mat="wrap", bevel=0.0035)
    b.plane(0.072, 0.05, loc=(0, 0, 0.0047), mat="print", cuts=3)
    for s in (-1, 1):
        b.box((0.006, 0.05, 0.002), loc=(s * 0.042, 0, 0), mat="wrap")
    cols = [(0.4, 1.0, 0.1), (1.0, 0.85, 0.1), (1.0, 0.2, 0.3), (0.2, 0.5, 1.0)]
    specs = {"wrap": P((0.05, 0.05, 0.07), 0.25, coat=0.6), "print": PR(_sour_print(rng, "wh"), 0.25)}
    for i in range(int(rng.integers(2, 5))):
        x, y = float(rng.uniform(-0.04, 0.04)), -0.04 - float(rng.uniform(0, 0.02))
        a = float(rng.uniform(0, 3))
        b.sphere(0.0075, loc=(x, y, 0.0), mat=f"sw{i}", seg=12)
        for s in (-1, 1):
            b.cyl(0.0055, 0.008, r2=0.0012, loc=(x + s * 0.011 * math.cos(a), y + s * 0.011 * math.sin(a), 0),
                  rot=(0, s * PI / 2, 0), mat=f"sw{i}", seg=8)
        specs[f"sw{i}"] = P(cols[i % 4], 0.1, coat=1.0)
    return specs


@obj("baby_bottle_pop", eras=(2, 3), mass=0.03, weight=1.0, group="special", **LUNCH)
def baby_bottle_pop(b, rng, pal):
    col = [(0.1, 0.45, 1.0), (0.95, 0.3, 0.6), (0.4, 0.9, 0.2), (0.6, 0.2, 0.9)][int(rng.integers(0, 4))]
    candy = [(0.95, 0.1, 0.2), (0.1, 0.6, 1.0), (0.95, 0.5, 0.05)][int(rng.integers(0, 3))]
    b.lathe([(0.0, -0.04), (0.014, -0.04), (0.015, -0.035), (0.015, 0.012), (0.012, 0.016), (0.0, 0.016)], mat="bottle",
            seg=22)
    b.lathe([(0.0, -0.025), (0.0152, -0.025), (0.0152, 0.0), (0.0, 0.0)], mat="label", seg=22)
    b.lathe([(0.0, 0.014), (0.0145, 0.014), (0.0145, 0.026), (0.0, 0.026)], mat="ring", seg=22)
    b.lathe([(0.0, 0.026), (0.009, 0.026), (0.0065, 0.035), (0.0055, 0.045), (0.0068, 0.052), (0.0055, 0.058),
             (0.0, 0.06)], mat="candy", seg=18)
    img = _wrap_label(rng, "bbp", 320, 72, (1, 1, 1), "BABY BOTTLE FLOP", "SUCK IT. LITERALLY.", col,
                      out=(0.05, 0.05, 0.07))
    return {"bottle": T(col, 0.1), "label": PR(img, 0.35), "ring": P(col, 0.3, coat=0.5), "candy": P(candy, 0.05, coat=1.0)}


def _wonder_foil(rng, name):
    c = _cv(384, 192, (0.85, 0.1, 0.25))
    cols = [(0.85, 0.1, 0.25), (1.0, 0.8, 0.1), (0.1, 0.4, 0.95), (0.55, 0.2, 0.85)]
    for i in range(12):
        c.rect(0, i / 12, 1, (i + 1) / 12, cols[i % 4])
    for _ in range(30):
        _star(c, float(rng.uniform(0, 1)), float(rng.uniform(0.05, 0.95)), 0.04, (1, 1, 1))
    c.rect(0, 0.36, 1, 0.64, (0.1, 0.05, 0.25))
    for half in (0.25, 0.75):
        _ct(c, "WONDER BAWL", half, 0.6, 0.44, 0.2, (1.0, 0.85, 0.1))
    return c.image(name)


@obj("wonder_ball", eras=(1, 2), mass=0.04, weight=1.0, group="era", **LUNCH)
def wonder_ball(b, rng, pal):
    """The foil chocolate ball with the surprise inside. The surprise was always a smaller disappointment."""
    b.sphere(0.03, mat="foil", seg=24)
    b.sphere(0.0285, loc=(0.0, -0.004, 0.0015), mat="choc", seg=24)
    for i in range(int(rng.integers(3, 7))):
        b.sphere(0.0045, loc=(float(rng.uniform(-0.03, 0.03)), -0.038 - float(rng.uniform(0, 0.02)), -0.024),
                 mat=f"c{i % 3}", seg=10)
    b.box((0.03, 0.022, 0.0006), loc=(0.028, -0.03, 0.018), rot=(0.6, -0.4, 0.3), mat="foil")
    return {"foil": PR(_wonder_foil(rng, "wb"), 0.2, metal=0.75), "choc": ("crust", {"color": (0.35, 0.18, 0.08)}),
            "c0": P((1.0, 0.3, 0.6), 0.3), "c1": P((0.2, 0.8, 1.0), 0.3), "c2": P((1.0, 0.9, 0.2), 0.3)}


@obj("orb_bottle", eras=(2,), mass=0.4, weight=1.0, group="special", hero=(0, -1, 0), **LUNCH)
def orb_bottle(b, rng, pal):
    """The 1997 drink with gel balls floating in it like a lava lamp you were supposed to drink."""
    prof = [(0.0, -0.1), (0.026, -0.1), (0.03, -0.09), (0.03, 0.03), (0.026, 0.05), (0.013, 0.075), (0.012, 0.09),
            (0.0, 0.09)]
    b.lathe(prof, mat="bottle", seg=26)
    b.lathe([(0.0, 0.088), (0.0135, 0.088), (0.0135, 0.104), (0.0, 0.104)], mat="cap", seg=18)
    b.lathe([(0.0, -0.088), (0.0302, -0.088), (0.0302, -0.07), (0.0, -0.07)], mat="label", seg=26)
    cols = [(1.0, 0.2, 0.5), (0.2, 0.7, 1.0), (1.0, 0.85, 0.1), (0.5, 1.0, 0.2)]
    for i in range(14):
        a, r = float(rng.uniform(0, 6.28)), float(rng.uniform(0, 0.018))
        b.sphere(float(rng.uniform(0.004, 0.0065)), loc=(r * math.cos(a), r * math.sin(a), float(rng.uniform(-0.06, 0.03))),
                 mat=f"o{i % 4}", seg=10)
    img = _wrap_label(rng, "orb", 320, 48, (0.05, 0.05, 0.12), "ORBEDZ", "TEXTURALLY ENHANCED", (0.5, 1.0, 0.9),
                      out=(0.4, 0.1, 0.6))
    specs = {"bottle": T((0.92, 0.95, 1.0), 0.04), "cap": P((0.1, 0.1, 0.12), 0.4),
             "label": PR(img, 0.3)}
    for i, col in enumerate(cols):
        specs[f"o{i}"] = P(col, 0.1, coat=1.0)
    return specs


@obj("crystal_cola", eras=(1,), mass=0.6, weight=1.0, group="special", hero=(0, -1, 0), **LUNCH)
def crystal_cola(b, rng, pal):
    """The clear cola of 1993. Tasted like a cola that had seen a ghost."""
    prof = [(0.0, -0.11), (0.024, -0.11), (0.03, -0.1), (0.031, -0.06), (0.026, -0.04), (0.03, -0.01), (0.03, 0.03),
            (0.022, 0.06), (0.014, 0.085), (0.013, 0.1), (0.0, 0.1)]
    b.lathe(prof, mat="bottle", seg=26)
    b.lathe([(0.0, -0.105), (0.0285, -0.105), (0.0285, 0.03), (0.014, 0.07), (0.0, 0.07)], mat="liquid", seg=22)
    b.lathe([(0.0, 0.098), (0.0145, 0.098), (0.0145, 0.116), (0.0, 0.116)], mat="cap", seg=18)
    b.lathe([(0.0, -0.035), (0.0305, -0.035), (0.0305, 0.012), (0.0, 0.012)], mat="label", seg=26)
    nm, _e, (base, hi, ink) = [s for s in _pd.SODA if s[0] == "CRYSTAL PEPPY"][0]
    c = _cv(384, 96, (0.92, 0.94, 0.97))
    for half in (0.25, 0.75):
        c.rect(half - 0.24, 0.0, half + 0.24, 0.18, hi)
        c.rect(half - 0.24, 0.82, half + 0.24, 1.0, hi)
        _ct(c, "CRYSTAL", half, 0.75, 0.4, 0.26, ink)
        _ct(c, "PEPPY", half, 0.45, 0.4, 0.26, (0.85, 0.1, 0.15))
    c.text("CLEARLY A MISTAKE  CAFFEINE FREE-ISH  CLEARLY A MISTAKE", 0.0, 0.14, 0.09, (1, 1, 1))
    return {"bottle": T((0.95, 0.97, 1.0), 0.03), "liquid": ("water", {}), "cap": P((0.05, 0.2, 0.6), 0.35),
            "label": PR(c.image("cc"), 0.3)}


def _chip_print(rng, name):
    c = _cv(512, 256, (0.85, 0.08, 0.1))
    for half in (0.25, 0.75):
        _burst(c, half, 0.55, 0.38, (1.0, 0.55, 0.05), n=24)
        c.poly([(half - 0.1, 0.18), (half + 0.1, 0.18), (half, 0.42)], (1.0, 0.7, 0.15))
        c.poly([(half - 0.02, 0.22), (half + 0.16, 0.26), (half + 0.08, 0.44)], (0.95, 0.55, 0.05))
        _ct(c, "3D", half - 0.12, 0.95, 0.12, 0.22, (1, 1, 1), out=(0.1, 0.1, 0.4))
        _ct(c, "DORKITOS", half, 0.75, 0.44, 0.22, (1.0, 0.9, 0.1), out=(0.1, 0.1, 0.12))
        _ct(c, "NACHO CHEESIER", half, 0.52, 0.32, 0.08, (1, 1, 1))
        _ct(c, "NOW IN 3D! (DON'T ASK)", half, 0.12, 0.44, 0.06, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("chip_bag_3d", eras=(2,), mass=0.05, weight=1.1, group="era", hero=(0, -1, 0), **LUNCH)
def chip_bag_3d(b, rng, pal):
    """The 1998 puffed-up 3D chips: a pillow bag of air and, somewhere, nine chips."""
    w, h = 0.16, 0.2
    rs = []
    n, rings = 24, 14
    for j in range(rings):
        u = j / (rings - 1)
        z = -h / 2 + h * u
        th = 0.055 * math.sin(PI * u) ** 0.7 + 0.001
        ww = w * (0.94 + 0.06 * math.sin(PI * u))
        rs.append([(ww / 2 * math.cos(2 * PI * i / n), th / 2 * math.sin(2 * PI * i / n), z) for i in range(n)])
    b.loft(rs, mat="bag")
    for s in (-1, 1):
        b.box((w, 0.002, 0.014), loc=(0, 0, s * (h / 2 + 0.005)), mat="seal")
    for i in range(int(rng.integers(3, 7))):
        x = float(rng.uniform(-0.07, 0.07))
        b.extrude([(-0.009, -0.007), (0.009, -0.007), (0.0, 0.009)], 0.007, loc=(x, -0.05 - float(rng.uniform(0, 0.02)),
                  -h / 2 + 0.005), rot=(float(rng.normal(0, 0.5)), float(rng.normal(0, 0.5)), float(rng.uniform(0, 6))),
                  mat="chip", bevel=0.003)
    return {"bag": PR(_chip_print(rng, "chip"), 0.2, metal=0.3), "seal": P((0.85, 0.08, 0.1), 0.25, coat=0.5),
            "chip": ("crust", {"color": (1.0, 0.55, 0.1)})}


def _splurge_print(rng, name):
    c = _cv(512, 256, (0.45, 0.85, 0.1))
    for k in range(4):
        xs = np.linspace(0, 1, 26)
        ys = [0.5 + 0.3 * (1 if i % 2 else -1) * float(rng.uniform(0.4, 1)) for i in range(26)]
        c.line(list(zip(xs.tolist(), ys)), 0.03, (0.05, 0.05, 0.07) if k % 2 else (0.9, 0.1, 0.1))
    for half in (0.25, 0.75):
        c.rect(half - 0.23, 0.36, half + 0.23, 0.68, (0.05, 0.05, 0.07))
        _ct(c, "SPLURGE", half, 0.64, 0.44, 0.26, (0.9, 0.1, 0.1), out=(1, 1, 1))
        _ct(c, "FEED THE RUSH. POOR THE WALLET.", half, 0.24, 0.44, 0.06, (0.05, 0.05, 0.07))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("splurge_can", eras=(1, 2), mass=0.02, weight=1.2, group="era", hero=(0, -1, 0), **LUNCH)
def splurge_can(b, rng, pal):
    """The lime-green citrus soda of 1997: neon can, red letters, the energy drink before energy drinks."""
    prof = [(0.0, -0.061), (0.025, -0.0615), (0.032, -0.055), (0.033, 0.05), (0.028, 0.06), (0.027, 0.0615),
            (0.0, 0.0615)]
    b.lathe(prof, mat="print", seg=32)
    b.lathe([(0.0, 0.0605), (0.0272, 0.0605), (0.0275, 0.064), (0.0, 0.063)], mat="lid", seg=28)
    b.box((0.012, 0.02, 0.0012), loc=(0, -0.006, 0.0645), mat="lid", bevel=0.0005)
    return {"print": PR(_splurge_print(rng, "spl"), 0.2, metal=0.6), "lid": MET((0.8, 0.8, 0.82), 0.25)}


def _pizza_top(rng, name):
    c = _cv(320, 320, (0.97, 0.95, 0.9))
    for i in range(16):
        for j in (0, 1):
            col = (0.85, 0.08, 0.1) if (i + j) % 2 == 0 else (0.97, 0.95, 0.9)
            c.rect(i / 16, j * 0.04, (i + 1) / 16, j * 0.04 + 0.04, col)
            c.rect(i / 16, 0.92 + j * 0.04, (i + 1) / 16, 0.96 + j * 0.04, col)
    c.poly([(0.2, 0.62), (0.5, 0.82), (0.8, 0.62), (0.72, 0.62), (0.5, 0.75), (0.28, 0.62)], (0.1, 0.05, 0.05))
    c.poly([(0.22, 0.6), (0.5, 0.8), (0.78, 0.6)], (0.85, 0.08, 0.1))
    c.rect(0.62, 0.7, 0.67, 0.8, (0.85, 0.08, 0.1))
    for k in range(3):
        c.circle(0.645 + k * 0.02, 0.83 + k * 0.03, 0.015 + k * 0.006, (0.75, 0.75, 0.75))
    c.rect(0.3, 0.5, 0.7, 0.6, (0.95, 0.85, 0.6))
    c.rect(0.46, 0.5, 0.54, 0.57, (0.4, 0.2, 0.1))
    _ct(c, "PIZZA HUTCH", 0.5, 0.45, 0.84, 0.13, (0.85, 0.08, 0.1), out=(0.1, 0.05, 0.05))
    _ct(c, "PERSONAL PAN-IC PIZZA", 0.5, 0.26, 0.8, 0.055, (0.1, 0.05, 0.05))
    _ct(c, "READ A BOOK. EARN A PIZZA. LEARN NOTHING.", 0.5, 0.17, 0.86, 0.035, (0.4, 0.3, 0.3))
    c.noise(rng, 0.02)
    return c.image(name)


def _bookit_button(rng, name):
    c = _cv(128, 128, (1, 1, 1))
    c.circle(0.5, 0.5, 0.48, (0.1, 0.25, 0.75))
    c.circle(0.5, 0.5, 0.4, (1.0, 0.85, 0.1))
    _star(c, 0.5, 0.5, 0.36, (0.85, 0.08, 0.1), n=5, inner=0.45)
    _ct(c, "BOOKED", 0.5, 0.62, 0.62, 0.15, (1, 1, 1), out=(0.1, 0.05, 0.1))
    _ct(c, "IT!", 0.5, 0.43, 0.4, 0.18, (1, 1, 1), out=(0.1, 0.05, 0.1))
    for i in range(10):
        t = 2 * PI * i / 10
        _star(c, 0.5 + 0.44 * math.cos(t), 0.5 + 0.44 * math.sin(t), 0.03, (1, 1, 1))
    return c.image(name)


@obj("pizza_box", eras=(0, 1), mass=0.15, weight=1.0, group="special", **LUNCH)
def pizza_box(b, rng, pal):
    """The personal pan pizza you earned by reading, with the star button you wore to prove it."""
    S, H = 0.17, 0.035
    b.box((S, S, H), mat="box", bevel=0.002)
    b.plane(S * 0.98, S * 0.98, loc=(0, 0, H / 2 + 0.0004), mat="top", cuts=3)
    for s in (-1, 1):
        b.box((0.03, 0.002, 0.012), loc=(s * 0.05, -S / 2 - 0.001, 0.0), mat="box")
    x, y = float(rng.uniform(0.035, 0.05)), float(rng.uniform(-0.06, -0.05))
    b.cyl(0.028, 0.005, loc=(x, y, H / 2 + 0.003), rot=(0.05, -0.08, 0), mat="pinrim", seg=24)
    b.extrude(ellipse(0.054, 0.054, 28), 0.0012, loc=(x, y, H / 2 + 0.0057), rot=(0.05, -0.08, 0), mat="button")
    return {"box": ("cardboard", {"color": (0.95, 0.93, 0.88)}), "top": PR(_pizza_top(rng, "ph"), 0.6),
            "pinrim": MET((0.8, 0.8, 0.82), 0.3), "button": PR(_bookit_button(rng, "bi"), 0.15)}


def _square_pizza(rng, name):
    c = _cv(96, 96, (0.92, 0.55, 0.15))
    c.rect(0.04, 0.04, 0.96, 0.96, (0.98, 0.78, 0.3))
    for _ in range(22):
        x, y = rng.uniform(0.1, 0.9, 2)
        c.rect(float(x) - 0.03, float(y) - 0.03, float(x) + 0.03, float(y) + 0.03, (0.8, 0.15, 0.08))
    for _ in range(30):
        x, y = rng.uniform(0.05, 0.95, 2)
        c.circle(float(x), float(y), 0.02, (1.0, 0.9, 0.55))
    return c.image(name)


@obj("lunch_tray", eras=(0, 1, 2), mass=0.6, weight=1.0, group="special", big=True, **LUNCH)
def lunch_tray(b, rng, pal):
    """The cafeteria compartment tray: rectangle pizza, tater tots, canned corn, a spork, a bad decision."""
    W, D = 0.3, 0.22
    col = [(0.85, 0.75, 0.6), (0.6, 0.7, 0.8), (0.82, 0.6, 0.62), (0.75, 0.8, 0.65)][int(rng.integers(0, 4))]
    b.box((W, D, 0.004), mat="tray", bevel=0.0015)
    h = 0.016
    for y in (-D / 2, D / 2):
        b.box((W, 0.006, h), loc=(0, y, h / 2), mat="tray", bevel=0.002)
    for x in (-W / 2, W / 2):
        b.box((0.006, D, h), loc=(x, 0, h / 2), mat="tray", bevel=0.002)
    b.box((0.005, D, h * 0.8), loc=(0.02, 0, h * 0.4), mat="tray", bevel=0.002)
    b.box((W / 2 - 0.02, 0.005, h * 0.8), loc=(0.02 + (W / 2 - 0.02) / 2, 0.0, h * 0.4), mat="tray", bevel=0.002)
    b.box((W / 2 + 0.02, 0.005, h * 0.8), loc=(-W / 2 + (W / 2 + 0.02) / 2, D / 2 - 0.04, h * 0.4), mat="tray", bevel=0.002)
    b.box((0.1, 0.09, 0.009), loc=(-0.065, -0.025, 0.0065), rot=(0, 0, float(rng.normal(0, 0.08))), mat="crust", bevel=0.002)
    b.plane(0.096, 0.086, loc=(-0.065, -0.025, 0.0112), rot=(0, 0, 0), mat="pizza", cuts=3)
    for i in range(int(rng.integers(5, 9))):
        b.cyl(0.0065, 0.016, loc=(0.06 + (i % 4) * 0.018, -0.07 + (i // 4) * 0.025, 0.009),
              rot=(PI / 2, 0, float(rng.uniform(0, 6))), mat="tot", seg=10)
    for i in range(30):
        b.sphere(0.0038, loc=(float(rng.uniform(0.04, 0.13)), float(rng.uniform(0.02, 0.09)), 0.005), mat="corn", seg=6)
    spork = [(-0.05, -0.0025), (0.02, -0.0025), (0.03, -0.008), (0.05, -0.008), (0.056, -0.004), (0.056, 0.004),
             (0.05, 0.008), (0.03, 0.008), (0.02, 0.0025), (-0.05, 0.0025)]
    b.extrude(spork, 0.0025, loc=(-0.05, D / 2 - 0.02, 0.006), rot=(0, 0, 0.05), mat="spork", bevel=0.0008)
    return {"tray": P(col, 0.55), "crust": ("crust", {"color": (0.85, 0.6, 0.3)}), "pizza": PR(_square_pizza(rng, "sqp"), 0.5),
            "tot": ("crust", {"color": (0.8, 0.55, 0.25)}), "corn": P((1.0, 0.82, 0.15), 0.3), "spork": P(WHITE, 0.4)}


def _milk_print(rng, name):
    c = _cv(160, 200, (0.97, 0.97, 0.97))
    c.rect(0, 0, 1, 0.45, (0.42, 0.24, 0.12))
    c.rect(0, 0.45, 1, 0.5, (0.1, 0.3, 0.75))
    _ct(c, "MOOVILLE", 0.5, 0.92, 0.9, 0.13, (0.1, 0.3, 0.75))
    _ct(c, "DAIRY", 0.5, 0.76, 0.6, 0.1, (0.1, 0.3, 0.75))
    c.circle(0.5, 0.58, 0.07, (1, 1, 1))
    c.circle(0.47, 0.6, 0.02, BLACK)
    c.circle(0.55, 0.56, 0.025, BLACK)
    _ct(c, "CHOCOLATE", 0.5, 0.38, 0.86, 0.12, (1, 1, 1))
    _ct(c, "LOWFAT MILK", 0.5, 0.24, 0.8, 0.07, (1, 1, 1))
    _ct(c, "1/2 PINT", 0.5, 0.12, 0.5, 0.07, (1.0, 0.85, 0.5))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("school_milk", eras=(0, 1, 2), mass=0.25, weight=1.0, group="special", hero=(0, -1, 0.3), **LUNCH)
def school_milk(b, rng, pal):
    """The half-pint chocolate milk carton, opened wrong, spout torn into a ragged mouth."""
    S, H = 0.06, 0.075
    b.box((S, S, H), mat="carton", bevel=0.001)
    b.plane(S, H, loc=(0, -S / 2 - 0.0004, 0), rot=(PI / 2, 0, 0), mat="print", cuts=3)
    b.plane(S, H, loc=(S / 2 + 0.0004, 0, 0), rot=(PI / 2, 0, PI / 2), mat="print", cuts=3)
    b.extrude([(-S / 2, 0), (S / 2, 0), (0, 0.022)], S, loc=(0, 0, H / 2), rot=(PI / 2, 0, PI / 2), mat="carton")
    b.box((0.004, S, 0.012), loc=(0, 0, H / 2 + 0.026), mat="carton")
    return {"carton": P((0.97, 0.97, 0.97), 0.6), "print": PR(_milk_print(rng, "mk"), 0.6)}


# =====================================================================================================
# C) SPORTS MEMORABILIA
# =====================================================================================================

SPORT = dict(tags=("sports",))


@obj("card_toploader", eras=(0, 1), mass=0.02, weight=1.1, group="era", **SPORT)
def card_toploader(b, rng, pal):
    """A rookie card in a rigid top-loader, penny-sleeved, because it was going to pay for college."""
    w, h = 0.064, 0.089
    b.box((w + 0.012, h + 0.008, 0.0025), loc=(0, -0.002, 0), mat="loader", bevel=0.001)
    b.box((w, h, 0.0006), mat="stock")
    b.plane(w, h, loc=(0, 0, 0.0014), mat="card", cuts=3)
    b.plane(w, h, loc=(0, 0, -0.0014), rot=(PI, 0, 0), mat="back", cuts=2)
    return {"loader": T((0.95, 0.97, 1.0), 0.04), "stock": P(WHITE, 0.6),
            "card": PR(_sports_card(rng, "tlc").image("tlc"), 0.3), "back": PR(_sports_card(rng, "tlb", back=True).image("tlb"), 0.6)}


def _wax_print(rng, name, brand, sport, year):
    col = [(0.85, 0.1, 0.12), (0.1, 0.25, 0.7), (0.15, 0.55, 0.3), (0.05, 0.05, 0.07), (0.95, 0.75, 0.1)][int(rng.integers(0, 5))]
    c = _cv(192, 256, col)
    for i in range(8):
        c.rect(0, i / 8, 1, i / 8 + 0.03, tuple(min(1, v + 0.15) for v in col))
    c.rect(0.05, 0.62, 0.95, 0.9, (1, 1, 1))
    _ct(c, brand, 0.5, 0.86, 0.86, 0.14, col)
    _ct(c, year, 0.5, 0.56, 0.5, 0.12, (1, 1, 1), out=(0, 0, 0))
    _ct(c, sport, 0.5, 0.4, 0.86, 0.1, (1.0, 0.9, 0.2), out=(0, 0, 0))
    _burst(c, 0.84, 0.56, 0.1, (1.0, 0.9, 0.1))
    _ct(c, "GUM!", 0.84, 0.59, 0.14, 0.05, (0.85, 0.1, 0.1))
    c.text("15 PICTURE CARDS", 0.06, 0.16, 0.045, (1, 1, 1))
    c.text("1 STALE GUM", 0.06, 0.1, 0.045, (1, 1, 1))
    c.noise(rng, 0.02)
    return c.image(name)


@obj("wax_pack", eras=(0, 1), mass=0.03, weight=1.1, group="era", **SPORT)
def wax_pack(b, rng, pal):
    """A torn wax pack of cards: crimped wax wrapper, a pink slab of gum that could cut glass, two cards out."""
    brand = str(CARD_BRANDS[int(rng.integers(0, len(CARD_BRANDS)))])
    sport = SPORTS[int(rng.integers(0, len(SPORTS)))]
    year = str(1987 + int(rng.integers(0, 8)))
    b.box((0.066, 0.092, 0.006), mat="wax", bevel=0.0022)
    b.plane(0.062, 0.088, loc=(0, 0, 0.0031), mat="print", cuts=3)
    for s in (-1, 1):
        b.box((0.066, 0.006, 0.0015), loc=(0, s * 0.048, 0), mat="wax")
    b.box((0.058, 0.075, 0.0025), loc=(0.03, -0.035, -0.002), rot=(0, 0, 0.5), mat="gum", bevel=0.0006)
    specs = {"wax": P((0.8, 0.8, 0.82), 0.2, coat=0.8), "print": PR(_wax_print(rng, "wx", brand, sport, year), 0.25),
             "gum": P((0.98, 0.72, 0.78), 0.65)}
    for k in range(2):
        x, y, a = 0.04 + k * 0.025, 0.02 - k * 0.02, -0.4 - k * 0.35
        b.box((0.064, 0.089, 0.0006), loc=(x, y, -0.004 - k * 0.001), rot=(0, 0, a), mat="stock")
        b.plane(0.064, 0.089, loc=(x, y, -0.0036 - k * 0.001), rot=(0, 0, a), mat=f"card{k}", cuts=2)
        specs[f"card{k}"] = PR(_sports_card(rng, f"wc{k}", sport=sport).image(f"wc{k}"), 0.35)
    specs["stock"] = P(WHITE, 0.6)
    return specs


def _seam(R, n=64):
    pts = []
    a, bb = 0.75, 0.25
    for i in range(n + 1):
        t = 2 * PI * i / n
        x = a * math.cos(t) + bb * math.cos(3 * t)
        y = a * math.sin(t) - bb * math.sin(3 * t)
        z = 2 * math.sqrt(a * bb) * math.sin(2 * t)
        m = math.sqrt(x * x + y * y + z * z)
        pts.append((x / m * R, y / m * R, z / m * R))
    return pts


def _ball_print(rng, name):
    c = _cv(512, 256, (0.95, 0.93, 0.86))
    c.noise(rng, 0.02)
    ink = (0.1, 0.15, 0.55)
    nm = str(PLAYERS[int(rng.integers(0, len(PLAYERS)))]).split()
    c.scribble(rng, 0.6, 0.55, 0.85, 0.012, ink, 0.03)
    c.scribble(rng, 0.62, 0.45, 0.8, 0.012, ink, 0.025)
    c.line([(0.6, 0.56), (0.58, 0.42), (0.86, 0.5)], 0.01, ink)
    _lt(c, "#" + str(int(rng.integers(1, 60))), 0.83, 0.42, 0.06, 0.08, ink, bold=False)
    c.text(nm[-1], 0.64, 0.36, 0.05, ink)
    c.text("OFFICIAL-ISH LEAGUE BALL", 0.1, 0.55, 0.035, (0.2, 0.2, 0.2))
    c.text("CORK CENTER (PROBABLY)", 0.12, 0.49, 0.03, (0.2, 0.2, 0.2))
    return c.image(name)


@obj("signed_baseball", eras=(0, 1, 2), mass=0.15, weight=1.0, group="special", **SPORT)
def signed_baseball(b, rng, pal):
    """An autographed ball on its little stand. The signature is real. The person is not famous."""
    R = 0.037
    b.sphere(R, mat="ball", seg=28)
    pts = _seam(R * 1.005)
    b.tube(pts, 0.0011, mat="stitch", seg=5)
    for i in range(0, len(pts) - 1, 1):
        p = np.array(pts[i])
        q = np.array(pts[i + 1])
        t = q - p
        nrm = p / np.linalg.norm(p)
        s = np.cross(t, nrm)
        s = s / (np.linalg.norm(s) + 1e-9) * 0.003
        b.tube([tuple(p - s + nrm * 0.0003), tuple(p + s + nrm * 0.0003)], 0.0007, mat="stitch", seg=4)
    b.lathe([(0.0, -R - 0.012), (0.022, -R - 0.012), (0.022, -R - 0.004), (0.016, -R + 0.002), (0.0, -R + 0.002)],
            mat="stand", seg=24)
    return {"ball": PR(_ball_print(rng, "bb"), 0.6), "stitch": P((0.8, 0.08, 0.1), 0.6),
            "stand": P((0.05, 0.05, 0.07), 0.2, coat=0.8)}


def _finger_print(rng, name, col, ink, city, nick):
    c = _cv(200, 280, col)
    _ct(c, "#1", 0.5, 0.42, 0.7, 0.2, ink, out=(1, 1, 1))
    _ct(c, city, 0.5, 0.18, 0.86, 0.06, ink)
    _ct(c, nick, 0.5, 0.11, 0.86, 0.06, ink)
    return c.image(name)


@obj("foam_finger", eras=(0, 1, 2), mass=0.08, weight=1.0, group="special", **SPORT)
def foam_finger(b, rng, pal):
    """The giant foam #1 hand. Bought in the third inning, lost in the parking lot."""
    city, nick, c1, c2 = _team(rng)
    hand = [(-0.06, -0.12), (0.06, -0.12), (0.065, -0.02), (0.068, 0.03), (0.055, 0.045), (0.04, 0.04), (0.035, 0.05),
            (0.02, 0.052), (0.012, 0.048), (0.01, 0.05), (-0.002, 0.052), (-0.012, 0.05), (-0.012, 0.16),
            (-0.02, 0.172), (-0.04, 0.172), (-0.048, 0.16), (-0.05, 0.04), (-0.07, 0.02), (-0.08, -0.02),
            (-0.065, -0.04)]
    b.extrude(hand, 0.028, mat="foam", bevel=0.006)
    b.box((0.13, 0.02, 0.03), loc=(0, -0.13, 0), mat="cuff", bevel=0.005)
    return {"foam": PR(_finger_print(rng, "ff", c1, c2, city, nick), 0.95), "cuff": ("foam", {"color": c2})}


def _pennant_print(rng, name, city, nick, c1, c2):
    c = _cv(512, 160, c1)
    c.rect(0.0, 0.0, 0.12, 1.0, (0.95, 0.95, 0.95))
    _lt(c, city, 0.16, 0.86, 0.5, 0.26, c2)
    _lt(c, nick, 0.16, 0.52, 0.6, 0.3, (1, 1, 1), out=c2)
    _star(c, 0.2, 0.18, 0.08, c2)
    _star(c, 0.29, 0.18, 0.08, c2)
    c.noise(rng, 0.03)
    return c.image(name)


@obj("felt_pennant", eras=(0, 1, 2), mass=0.03, weight=1.0, group="special", **SPORT)
def felt_pennant(b, rng, pal):
    city, nick, c1, c2 = _team(rng)
    L, H = 0.3, 0.1
    b.extrude([(-L / 2, -H / 2), (L / 2, -0.002), (L / 2, 0.002), (-L / 2, H / 2)], 0.002, mat="felt")
    b.box((0.02, H + 0.004, 0.004), loc=(-L / 2 + 0.006, 0, 0), mat="strip")
    for i in range(6):
        y = -H / 2 + 0.008 + i * (H - 0.016) / 5
        b.tube([(-L / 2 - 0.004, y, 0), (-L / 2 - 0.018, y + 0.002, 0.0), (-L / 2 - 0.03, y - 0.001, 0)], 0.0012,
               mat="strip", seg=4)
    return {"felt": PR(_pennant_print(rng, "pn", city, nick, c1, c2), 1.0), "strip": ("fabric", {"color": (0.95, 0.95, 0.95)})}


@obj("bobblehead", eras=(1, 2, 3), mass=0.3, weight=1.0, group="special", hero=(0, -1, 0.2), **SPORT)
def bobblehead(b, rng, pal):
    """Stadium giveaway bobblehead: tiny body, enormous head on a spring, a face only a promo budget could love."""
    city, nick, c1, c2 = _team(rng)
    skin = SKIN[int(rng.integers(0, len(SKIN)))]
    b.box((0.07, 0.055, 0.016), loc=(0, 0, -0.07), mat="base", bevel=0.004)
    lab = _cv(256, 64, c1)
    _ct(lab, f"{city} {nick}", 0.5, 0.75, 0.92, 0.5, (1, 1, 1))
    b.plane(0.066, 0.014, loc=(0, -0.0281, -0.07), rot=(PI / 2, 0, 0), mat="label", cuts=2)
    for s in (-1, 1):
        b.cyl(0.006, 0.035, loc=(s * 0.009, 0, -0.045), mat="pants", seg=10)
        b.box((0.012, 0.02, 0.007), loc=(s * 0.009, -0.004, -0.06), mat="shoe", bevel=0.002)
    b.lathe([(0.0, -0.03), (0.017, -0.03), (0.02, -0.0), (0.021, 0.012), (0.012, 0.018), (0.0, 0.018)], mat="jersey", seg=16)
    b.tube([(-0.02, 0, 0.01), (-0.03, -0.008, -0.01), (-0.022, -0.016, -0.025)], 0.0045, mat="jersey", seg=6)
    b.tube([(0.02, 0, 0.01), (0.03, -0.01, 0.0), (0.024, -0.02, 0.01)], 0.0045, mat="jersey", seg=6)
    b.tube([(0.024, -0.02, 0.008), (0.02, -0.03, 0.055)], 0.0028, mat="bat", seg=8)
    b.tube(helix(0.004, 0.003, 4, 10, start=(0, 0, 0.016)), 0.0008, mat="spring", seg=4)
    hz = 0.055
    b.sphere(0.032, loc=(0, 0, hz), scale=(1.0, 0.95, 1.05), mat="skin", seg=20)
    b.lathe([(0.0, 0.0), (0.0335, 0.0), (0.03, 0.016), (0.018, 0.028), (0.0, 0.031)], loc=(0, 0, hz + 0.006), mat="cap", seg=20)
    b.box((0.04, 0.025, 0.003), loc=(0, -0.038, hz + 0.008), rot=(-0.15, 0, 0), mat="cap", bevel=0.001)
    for s in (-1, 1):
        b.sphere(0.0065, loc=(s * 0.011, -0.027, hz - 0.002), mat="eye", seg=10)
        b.sphere(0.0033, loc=(s * 0.011, -0.0325, hz - 0.003), mat="pupil", seg=8)
        b.sphere(0.006, loc=(s * 0.032, 0, hz - 0.004), scale=(0.5, 1, 1.2), mat="skin", seg=8)
    b.torus(0.012, 0.0018, loc=(0, -0.026, hz - 0.012), rot=(PI / 2, 0, PI), arc=PI, mat="pupil", seg=12, rseg=4)
    b.sphere(0.005, loc=(0, -0.032, hz - 0.006), mat="skin", seg=8)
    return {"base": P(c1, 0.3, coat=0.5), "label": PR(lab.image("bhl"), 0.4), "pants": P((0.95, 0.95, 0.95), 0.4),
            "shoe": P(BLACK, 0.4), "jersey": P(c1, 0.35), "bat": ("wood", {}), "spring": MET((0.6, 0.6, 0.62), 0.3),
            "skin": P(skin, 0.45), "cap": P(c2 if sum(c2) < 2.5 else c1, 0.4), "eye": P(WHITE, 0.2), "pupil": P(BLACK, 0.3)}


def _jersey_print(rng, name, c1, c2, player, num, pin):
    c = _cv(256, 256, c1)
    if pin:
        for i in range(16):
            c.rect(i / 16, 0, i / 16 + 0.006, 1, c2)
    for i in range(0, 256, 4):
        c.rect(0, i / 256, 1, i / 256 + 0.006, tuple(v * 0.92 for v in c1))
    last = player.split()[-1]
    _ct(c, last, 0.5, 0.92, 0.86, 0.12, (1, 1, 1), out=c2)
    _ct(c, num, 0.5, 0.72, 0.8, 0.5, (1, 1, 1), out=c2, d=0.025)
    c.rect(0.0, 0.0, 1.0, 0.04, c2)
    c.noise(rng, 0.03)
    return c.image(name)


def _torn(rng, w, h, n=28, jag=0.012):
    pts = []
    for i in range(n):
        t = 2 * PI * i / n
        x, y = w / 2 * math.cos(t), h / 2 * math.sin(t)
        x = max(-w / 2, min(w / 2, x * 1.4))
        y = max(-h / 2, min(h / 2, y * 1.4))
        pts.append((x + float(rng.uniform(-jag, jag)), y + float(rng.uniform(-jag, jag))))
    return pts


@obj("jersey_scrap", eras=(0, 1, 2), mass=0.08, weight=1.0, group="special", **SPORT)
def jersey_scrap(b, rng, pal):
    """A torn chunk of a replica jersey: mesh weave, name across the shoulders, the big tackle-twill number."""
    city, nick, c1, c2 = _team(rng)
    player = str(PLAYERS[int(rng.integers(0, len(PLAYERS)))])
    num = str(int(rng.integers(1, 99)))
    b.extrude(_torn(rng, 0.2, 0.2), 0.003, mat="jersey")
    return {"jersey": PR(_jersey_print(rng, "js", c1, c2, player, num, rng.random() < 0.3), 0.9)}


def _cap_logo(rng, name, c1, c2, city):
    c = _cv(96, 96, c1)
    c.circle(0.5, 0.5, 0.45, c2)
    c.circle(0.5, 0.5, 0.38, c1)
    _ct(c, city[0], 0.5, 0.78, 0.6, 0.55, (1, 1, 1), out=c2)
    return c.image(name)


@obj("snapback_cap", eras=(1, 2), mass=0.12, weight=1.0, group="special", hero=(0, -1, 0.5), **SPORT)
def snapback_cap(b, rng, pal):
    """A two-tone snapback with a flat brim and the gold sticker nobody ever peeled off."""
    city, nick, c1, c2 = _team(rng)
    R = 0.075
    b.lathe([(0.0, 0.0), (R, 0.0), (R * 0.98, 0.03), (R * 0.85, 0.065), (R * 0.55, 0.09), (0.0, 0.1)], mat="crown", seg=28,
            scale=(1, 1.1, 1))
    b.sphere(0.006, loc=(0, 0, 0.1), mat="brim", seg=10)
    for k in range(6):
        a = PI * k / 3 + PI / 6
        pts = [(R * f * math.cos(a), R * 1.1 * f * math.sin(a), z) for f, z in ((1.002, 0.002), (0.99, 0.03),
               (0.86, 0.065), (0.56, 0.09), (0.05, 0.1))]
        b.tube(pts, 0.0011, mat="seam", seg=4)
    brim = [(0.075 * math.cos(t), -R * 0.9 - 0.075 * math.sin(t) * 0.95) for t in np.linspace(0, PI, 18)]
    brim += [(-0.075 * math.cos(t) * 0.98, -R * 0.9 + 0.02 * math.sin(t)) for t in np.linspace(0, PI, 8)[1:-1]]
    b.extrude(brim, 0.004, loc=(0, 0, 0.004), rot=(-0.08, 0, 0), mat="brim", bevel=0.0012)
    b.cyl(0.012, 0.0008, loc=(0.025, -R * 1.25, 0.0105), rot=(-0.08, 0, 0), mat="sticker", seg=16)
    b.extrude(rounded_rect(0.05, 0.042, 0.01), 0.004, loc=(0, -0.0785, 0.038), rot=(PI / 2 - 0.4, 0, 0), mat="logo")
    b.box((0.06, 0.006, 0.012), loc=(0, R * 1.08, 0.012), mat="snap")
    for i in range(6):
        b.cyl(0.0022, 0.004, loc=(-0.025 + i * 0.01, R * 1.08 + 0.003, 0.012), rot=(PI / 2, 0, 0), mat="snap", seg=8)
    return {"crown": P(c1, 0.85), "brim": P(c2, 0.8), "seam": ("fabric", {"color": tuple(v * 0.7 for v in c1)}),
            "sticker": MET((0.95, 0.75, 0.3), 0.2), "logo": PR(_cap_logo(rng, "cl", c1, c2, city), 0.8),
            "snap": P(BLACK, 0.35)}


def _ticket(rng, name):
    t1, t2 = rng.choice(len(TEAMS), 2, replace=False)
    a, bb = TEAMS[int(t1)], TEAMS[int(t2)]
    c = _cv(384, 150, (0.97, 0.95, 0.88))
    c.rect(0, 0.82, 0.76, 1.0, a[2])
    _lt(c, "TICKETMASHER", 0.03, 0.97, 0.4, 0.12, (1, 1, 1))
    _lt(c, f"{a[0]} {a[1]}", 0.03, 0.74, 0.7, 0.13, a[2])
    _lt(c, f"VS {bb[0]} {bb[1]}", 0.03, 0.58, 0.7, 0.1, (0.15, 0.15, 0.2))
    _lt(c, f"GAME {int(rng.integers(1, 81))}  {['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP'][int(rng.integers(0, 6))]} "
        f"{int(rng.integers(1, 29))} 19{int(rng.integers(87, 99))}", 0.03, 0.42, 0.7, 0.08, (0.15, 0.15, 0.2))
    c.text(f"SEC {int(rng.integers(100, 340))}  ROW {chr(65 + int(rng.integers(0, 26)))}  SEAT {int(rng.integers(1, 30))}",
           0.03, 0.28, 0.08, (0.6, 0.05, 0.05), bold=True)
    c.text("RAIN OR SHINE. MOSTLY RAIN.", 0.03, 0.12, 0.06, (0.4, 0.4, 0.4))
    for i in range(16):
        c.rect(0.775, i / 16, 0.78, i / 16 + 0.03, (0.4, 0.4, 0.4))
    c.text("ADMIT", 0.81, 0.9, 0.08, (0.15, 0.15, 0.2))
    c.text("ONE", 0.83, 0.74, 0.1, (0.15, 0.15, 0.2), bold=True)
    c.text(f"${int(rng.integers(4, 18))}.50", 0.81, 0.45, 0.09, (0.6, 0.05, 0.05))
    for i in range(18):
        c.rect(0.81 + i * 0.009, 0.08, 0.81 + i * 0.009 + float(rng.uniform(0.002, 0.006)), 0.28, (0.1, 0.1, 0.1))
    c.noise(rng, 0.02)
    return c.image(name)


@obj("ticket_stubs", eras=(0, 1, 2), mass=0.01, weight=1.0, group="special", **SPORT)
def ticket_stubs(b, rng, pal):
    specs = {"stock": P((0.97, 0.95, 0.88), 0.8)}
    for k in range(int(rng.integers(2, 4))):
        x, y, a = k * 0.012, k * 0.018, float(rng.normal(0, 0.25))
        b.box((0.14, 0.055, 0.0005), loc=(x, y, k * 0.0009), rot=(0, 0, a), mat="stock")
        b.plane(0.14, 0.055, loc=(x, y, k * 0.0009 + 0.0003), rot=(0, 0, a), mat=f"t{k}", cuts=2)
        specs[f"t{k}"] = PR(_ticket(rng, f"tk{k}"), 0.7)
    return specs


@obj("mini_helmet", eras=(0, 1, 2), mass=0.2, weight=1.0, group="special", hero=(1, -0.4, 0.3), **SPORT)
def mini_helmet(b, rng, pal):
    """A mini replica football helmet: glossy shell, center stripe, grey facemask, the logo decal."""
    city, nick, c1, c2 = _team(rng)
    R = 0.05
    b.sphere(R, scale=(0.9, 1.15, 0.95), mat="shell", seg=24)
    stripe = [(0, R * 1.15 * math.cos(t) * 1.01, R * 0.95 * math.sin(t) * 1.01) for t in np.linspace(-0.6, PI - 0.3, 16)]
    stripe = [(0, -y, z) for _, y, z in stripe]
    b.tube(stripe, 0.006, mat="stripe", seg=8)
    for zz in (-0.012, 0.004):
        b.tube([(R * 0.85 * math.cos(t), -R * 1.2 - 0.004 * math.sin(t), zz) for t in np.linspace(0.3, PI - 0.3, 10)][::1],
               0.0028, mat="mask", seg=6)
    b.tube([(0, -R * 1.24, -0.03), (0, -R * 1.24, 0.008), (0, -R * 1.1, 0.02)], 0.0028, mat="mask", seg=6)
    for s in (-1, 1):
        b.tube([(s * R * 0.8, -R * 0.6, 0.01), (s * R * 0.85, -R * 1.18, 0.006)], 0.0028, mat="mask", seg=6)
        b.tube([(s * R * 0.8, -R * 0.6, -0.025), (s * R * 0.85, -R * 1.18, -0.012)], 0.0028, mat="mask", seg=6)
        b.cyl(0.004, 0.004, loc=(s * R * 0.9, 0.0, -0.01), rot=(0, PI / 2, 0), mat="pad", seg=10)
    b.extrude(ellipse(0.036, 0.036, 24), 0.002, loc=(R * 0.9, 0.006, 0.012), rot=(PI / 2, 0, PI / 2), mat="decal")
    b.extrude(ellipse(0.036, 0.036, 24), 0.002, loc=(-R * 0.9, 0.006, 0.012), rot=(PI / 2, 0, -PI / 2), mat="decal")
    return {"shell": P(c1, 0.15, coat=1.0), "pad": P(BLACK, 0.6), "stripe": P(c2, 0.2, coat=1.0),
            "mask": P((0.6, 0.6, 0.62), 0.35), "decal": PR(_cap_logo(rng, "hd", c1, c2, city), 0.2)}


@obj("card_binder_sheet", eras=(0, 1), mass=0.04, weight=1.0, group="special", **SPORT)
def card_binder_sheet(b, rng, pal):
    """A 9-pocket binder page of commons, sorted by team, one empty slot where the good card used to be."""
    W, H = 0.23, 0.29
    b.box((W, H, 0.0008), mat="sheet")
    specs = {"sheet": P((0.86, 0.89, 0.93), 0.08, coat=1.0), "ring": P((0.96, 0.96, 0.96), 0.5), "seam": T((0.85, 0.88, 0.92), 0.2)}
    sport = SPORTS[int(rng.integers(0, len(SPORTS)))]
    empty = int(rng.integers(0, 9))
    for i in range(9):
        cx, cy = -W / 2 + 0.03 + 0.038 + (i % 3) * 0.068, H / 2 - 0.01 - 0.048 - (i // 3) * 0.093
        if i == empty and rng.random() < 0.7:
            continue
        b.plane(0.063, 0.088, loc=(cx, cy, 0.0006), mat=f"card{i}", cuts=2)
        specs[f"card{i}"] = PR(_sports_card(rng, f"bs{i}", 100, 140, sport=sport).image(f"bs{i}"), 0.3)
    for k in range(4):
        b.box((0.203, 0.0012, 0.0012), loc=(-W / 2 + 0.0335 + 0.1015, H / 2 - 0.01 - k * 0.093 + 0.0005, 0.0006), mat="seam")
        b.box((0.0012, 0.28, 0.0012), loc=(-W / 2 + 0.034 + k * 0.068, H / 2 - 0.01 - 0.14, 0.0006), mat="seam")
    for y in (-0.1, 0.0, 0.1):
        b.torus(0.004, 0.0012, loc=(-W / 2 + 0.012, y, 0.0005), mat="ring", seg=12, rseg=4)
    return specs


def _satin_print(rng, name, c1, c2, city):
    c = _cv(320, 320, c1)
    c.rect(0, 0.82, 1, 1, c2)
    for i in range(6):
        c.rect(0, 0.84 + i * 0.026, 1, 0.85 + i * 0.026, c1 if i % 2 else tuple(min(1, v + 0.3) for v in c2))
    c.rect(0.28, 0, 0.33, 0.82, tuple(v * 0.8 for v in c1))
    _lt(c, city[0] + city[1:].lower().upper(), 0.4, 0.66, 0.55, 0.14, (1, 1, 1), out=c2)
    for _ in range(6):
        x = float(rng.uniform(0, 1))
        c.line([(x, 0), (x + 0.1, 0.8)], 0.01, tuple(min(1, v + 0.12) for v in c1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("satin_jacket", eras=(1,), mass=0.15, weight=1.0, group="special", **SPORT)
def satin_jacket(b, rng, pal):
    """A shredded chunk of the shiny team jacket everybody's cousin had: satin shell, striped knit collar, snaps."""
    city, nick, c1, c2 = _team(rng)
    W, H = 0.2, 0.18
    b.extrude(_torn(rng, W, H, 30, 0.014), 0.005, mat="satin")
    for i in range(4):
        b.cyl(0.0045, 0.003, loc=(-W / 2 + 0.305 * W, H / 2 - 0.04 - i * 0.04, 0.0035), mat="snap", seg=12)
    return {"satin": PR(_satin_print(rng, "sj", c1, c2, city), 0.22), "snap": CHROME()}


# =====================================================================================================
# D) SLIMED  (the orange-splat kids' cable one-of-one)
# =====================================================================================================

SLIMED = dict(group="special", eras=(1, 2), tags=("slimed",))


def _splat_logo(rng, name, w=320, h=256):
    c = _cv(w, h, ORANGE)
    _ct(c, CABLE, 0.5, 0.62, 0.86, 0.22, (1, 1, 1), out=(0.05, 0.05, 0.07))
    return c


@obj("slime_tub", mass=0.3, weight=1.0, hero=(0, -1, 0.4), **SLIMED)
def slime_tub(b, rng, pal):
    """The tub of official green slime, lid off, slime making a break for it."""
    R, H = 0.045, 0.06
    b.lathe([(0.0, 0.0), (R * 0.94, 0.0), (R, H), (R * 0.9, H), (R * 0.86, 0.006), (0.0, 0.006)], mat="tub", seg=28)
    b.lathe([(0.0, 0.012), (R * 1.002, 0.012), (R * 1.002, H - 0.012), (0.0, H - 0.012)], mat="label", seg=28)
    b.sphere(R * 0.95, loc=(0, 0, H - 0.004), scale=(1.0, 1.0, 0.35), mat="slime", seg=20)
    for i in range(int(rng.integers(3, 6))):
        a = float(rng.uniform(PI, 2 * PI))
        b.tube([(R * math.cos(a), R * math.sin(a), H), (R * 1.05 * math.cos(a), R * 1.05 * math.sin(a), H - 0.015),
                (R * 1.03 * math.cos(a), R * 1.03 * math.sin(a), H - float(rng.uniform(0.02, 0.045)))],
               lambda t: 0.006 * (1.0 - 0.4 * t), mat="slime", seg=8)
    b.cyl(R * 1.05, 0.008, loc=(R * 2.2, R * 0.4, 0.004), rot=(0.0, 0.08, 0), mat="lid", seg=28)
    c = _cv(512, 128, ORANGE)
    for half in (0.25, 0.75):
        _splat(c, half, 0.5, 0.42, SLIME_G, rng)
        _ct(c, CABLE, half, 0.8, 0.4, 0.17, (1, 1, 1), out=(0.05, 0.05, 0.07))
        _ct(c, "GLOPP", half, 0.56, 0.36, 0.34, (1, 1, 1), out=(0.1, 0.4, 0.05))
        _ct(c, "MAKES A NOISE. WE DON'T KNOW WHY.", half, 0.14, 0.44, 0.08, (0.05, 0.05, 0.07))
    return {"tub": P(SLIME_G, 0.3, coat=0.4), "label": PR(c.image("st"), 0.35),
            "slime": P((0.35, 1.0, 0.05), 0.05, coat=1.0), "lid": P(ORANGE, 0.3, coat=0.4)}


@obj("splat_sign", mass=0.15, weight=1.0, **SLIMED)
def splat_sign(b, rng, pal):
    """The orange splat logo sign off the studio wall. Our splat, our letters, our lawsuit-free goo."""
    pts = _splat_shape(rng, n=72)
    S = 0.11
    b.extrude([(x * S, y * S * 0.8) for x, y in pts], 0.008, mat="sign")
    b.extrude([(x * S * 1.04, y * S * 0.84) for x, y in pts], 0.004, loc=(0, 0, -0.005), mat="edge")
    c = _cv(320, 256, ORANGE)
    _ct(c, CABLE, 0.5, 0.6, 0.78, 0.2, (1, 1, 1), out=(0.05, 0.05, 0.07))
    return {"sign": PR(c.image("ss"), 0.35), "edge": P((0.05, 0.05, 0.07), 0.4)}


@obj("putty_egg", mass=0.06, weight=1.0, **SLIMED)
def putty_egg(b, rng, pal):
    """The plastic egg of noise putty. Push your finger in. Act surprised. Get sent to the hall."""
    col = [(0.1, 0.8, 0.9), (1.0, 0.3, 0.6), (0.55, 0.2, 0.9), (0.1, 0.35, 0.95)][int(rng.integers(0, 4))]
    putty = [(0.45, 1.0, 0.15), (1.0, 0.5, 0.05), (1.0, 0.9, 0.1)][int(rng.integers(0, 3))]
    egg = [(0.0, -0.04), (0.018, -0.037), (0.027, -0.025), (0.031, -0.01), (0.032, 0.0), (0.0, 0.0)]
    b.lathe(egg, mat="egg", seg=24)
    top = [(0.0, 0.0), (0.032, 0.0), (0.03, 0.015), (0.024, 0.03), (0.013, 0.043), (0.0, 0.047)]
    b.lathe(top, loc=(0.05, 0.01, -0.04), rot=(PI, 0, 0), mat="egg2", seg=24)
    b.sphere(0.03, loc=(0, 0, 0.004), scale=(1.0, 1.0, 0.45), mat="putty", seg=18)
    b.sphere(0.012, loc=(0.02, -0.025, 0.0), scale=(1.4, 1.0, 0.6), mat="putty", seg=12)
    lab = _cv(128, 64, (1, 1, 1))
    _ct(lab, "TOOT", 0.5, 0.92, 0.9, 0.4, (0.85, 0.1, 0.3), out=(0.05, 0.05, 0.07))
    _ct(lab, "PUTTY", 0.5, 0.42, 0.9, 0.35, (0.1, 0.4, 0.9))
    b.plane(0.026, 0.013, loc=(0, -0.0315, -0.012), rot=(PI / 2 + 0.25, 0, 0), mat="label", cuts=2)
    return {"egg": P(col, 0.25, coat=0.6), "egg2": P(col, 0.25, coat=0.6), "putty": ("clay", {"color": putty}),
            "label": PR(lab.image("tp"), 0.3)}


def _floom_lid(rng, name, col):
    c = _cv(128, 128, col)
    _splat(c, 0.5, 0.5, 0.42, ORANGE, rng)
    _ct(c, "FLOOM", 0.5, 0.62, 0.7, 0.24, (1, 1, 1), out=(0.05, 0.05, 0.07))
    _ct(c, "IT'S FOAM. IT'S CLAY.", 0.5, 0.3, 0.7, 0.07, (0.05, 0.05, 0.07))
    _ct(c, "IT'S IN THE CARPET.", 0.5, 0.2, 0.7, 0.07, (0.05, 0.05, 0.07))
    return c.image(name)


@obj("foam_bead_tub", mass=0.1, weight=1.0, **SLIMED)
def foam_bead_tub(b, rng, pal):
    """The tub of foam-bead clay, a sticky crunchy mound of it out on the table, the rest in the carpet forever."""
    col = NEON[int(rng.integers(0, len(NEON)))]
    R = 0.032
    b.lathe([(0.0, 0.0), (R, 0.0), (R * 1.05, 0.04), (R * 0.95, 0.04), (R * 0.9, 0.004), (0.0, 0.004)], mat="tub", seg=24)
    b.extrude(ellipse(R * 2.2, R * 2.2, 28), 0.006, loc=(R * 2.4, -0.005, 0.003), rot=(0, 0.1, 0.3), mat="lid")
    pile = [(float(rng.normal(0, 0.012)), float(rng.normal(-0.04, 0.01)), 0.0) for _ in range(46)]
    for i, (x, y, _) in enumerate(pile):
        d = math.hypot(x, y + 0.04)
        z = max(0.0, 0.022 - d * 1.3) + float(rng.uniform(0, 0.004))
        b.sphere(0.0042, loc=(x, y, z), mat=f"bead{i % 2}", seg=8)
    for i in range(14):
        b.sphere(0.0042, loc=(float(rng.normal(0, 0.016)), float(rng.normal(0, 0.016)), 0.036), mat=f"bead{i % 2}", seg=8)
    alt = NEON[int(rng.integers(0, len(NEON)))]
    return {"tub": P((0.9, 0.92, 0.95), 0.1, coat=1.0), "lid": PR(_floom_lid(rng, "fl", alt), 0.35),
            "bead0": ("foam", {"color": col}), "bead1": ("foam", {"color": tuple(min(1, v * 0.85 + 0.1) for v in col)})}


def _vhs_cover(rng, name):
    c = _show_art(rng, name, 192, 336, shows=CABLE_SHOWS, logo=None)
    c.rect(0, 0, 1, 0.1, ORANGE)
    _splat(c, 0.2, 0.06, 0.07, (1, 1, 1), rng)
    _lt(c, CABLE + " VIDEO", 0.32, 0.075, 0.64, 0.04, (1, 1, 1))
    _burst(c, 0.8, 0.68, 0.1, (1.0, 0.9, 0.1))
    _ct(c, "3 EPS!", 0.8, 0.7, 0.16, 0.04, (0.85, 0.1, 0.2))
    return c.image(name)


@obj("orange_vhs", mass=0.25, weight=1.2, **SLIMED)
def orange_vhs(b, rng, pal):
    """An orange clamshell kids' VHS of a cartoon taped off a cable channel that was mostly slime."""
    W, H, T_ = 0.115, 0.205, 0.03
    b.box((W, H, T_), mat="shell", bevel=0.004)
    b.plane(W * 0.84, H * 0.88, loc=(0.002, 0, T_ / 2 + 0.0002), mat="art", cuts=3)
    for y in (-0.06, 0.06):
        b.cyl(0.004, 0.03, loc=(-W / 2 - 0.001, y, 0), rot=(PI / 2, 0, 0), mat="shell", seg=10)
    b.box((0.006, 0.03, 0.01), loc=(W / 2 + 0.002, 0, 0), mat="shell", bevel=0.002)
    sp = _cv(64, 320, ORANGE)
    spr = _rot(sp)
    _ct(spr, str(CABLE_SHOWS[int(rng.integers(0, len(CABLE_SHOWS)))]), 0.5, 0.7, 0.9, 0.4, (1, 1, 1),
        out=(0.05, 0.05, 0.07))
    b.plane(H * 0.9, T_ * 0.8, loc=(-W / 2 - 0.0042, 0, 0), rot=(PI / 2, 0, -PI / 2), mat="spine", cuts=2)
    sp_img = spr.image("vsp")
    return {"shell": P(ORANGE, 0.35, coat=0.3),
            "art": PR(_vhs_cover(rng, "vc"), 0.35), "spine": PR(sp_img, 0.4)}


def _dare_flag(rng, name):
    c = _cv(320, 192, (0.95, 0.15, 0.1))
    for i in range(8):
        for j in range(5):
            if (i + j) % 2 == 0:
                c.rect(i / 8, j / 5, (i + 1) / 8, (j + 1) / 5, (1.0, 0.55, 0.05))
    _splat(c, 0.5, 0.5, 0.42, SLIME_G, rng, out=(0.05, 0.05, 0.07))
    _ct(c, "DOUBLE", 0.5, 0.78, 0.6, 0.2, (1, 1, 1), out=(0.05, 0.05, 0.07))
    _ct(c, "DOG DARE", 0.5, 0.48, 0.7, 0.2, (1.0, 0.9, 0.1), out=(0.05, 0.05, 0.07))
    return _rot(c).image(name)


@obj("dare_flag", mass=0.15, weight=1.0, hero=(0, -1, 0.2), **SLIMED)
def dare_flag(b, rng, pal):
    """The obstacle-course flag you had to grab before the clock ran out. Slime drip on the pole: authentic."""
    b.cyl(0.006, 0.26, loc=(0, 0, 0.0), mat="pole", seg=12)
    b.sphere(0.011, loc=(0, 0, 0.135), mat="finial", seg=12)
    b.cyl(0.04, 0.012, loc=(0, 0, -0.13), mat="base", seg=24)
    n = 12
    pts = [(0.006 + 0.15 * i / (n - 1), -0.01 * math.sin(i * 0.8), 0.07) for i in range(n)]
    _ribbon(b, pts, 0.09, "flag", side=(0, 0, -1))
    b.tube([(0.007, -0.004, 0.03), (0.0075, -0.006, 0.0), (0.007, -0.006, -0.03)], lambda t: 0.004 * (1 - 0.5 * t),
           mat="slime", seg=8)
    return {"pole": P((0.95, 0.95, 0.95), 0.3), "finial": P((1.0, 0.85, 0.1), 0.25, coat=0.6), "base": P(BLACK, 0.4),
            "flag": PR(_dare_flag(rng, "df"), 0.7), "slime": ("slime", {"color": SLIME_G})}


def _cereal_front(rng, name):
    show = str(CABLE_SHOWS[int(rng.integers(0, len(CABLE_SHOWS)))])
    c = _show_art(rng, name, 256, 352, title=show + " O'S")
    c.rect(0.0, 0.0, 1.0, 0.22, ORANGE)
    for _ in range(12):
        x, y = rng.uniform(0.05, 0.95), rng.uniform(0.03, 0.2)
        c.circle(float(x), float(y), 0.03, NEON[int(rng.integers(0, len(NEON)))], ring=0.02)
    _burst(c, 0.8, 0.66, 0.12, (1.0, 0.2, 0.4), ring=(1, 1, 1))
    _ct(c, "FREE", 0.8, 0.7, 0.18, 0.05, (1, 1, 1))
    _ct(c, "SLIME", 0.8, 0.64, 0.18, 0.045, (1, 1, 1))
    _ct(c, "INSIDE!", 0.8, 0.585, 0.18, 0.04, (1, 1, 1))
    c.rect(0.05, 0.23, 0.95, 0.3, (0.05, 0.05, 0.07))
    _ct(c, "WITH SLIME-FLAVORED MARSHMALLOWS", 0.5, 0.29, 0.86, 0.045, SLIME_G)
    _splat(c, 0.12, 0.1, 0.07, (1, 1, 1), rng)
    _ct(c, CABLE, 0.12, 0.11, 0.12, 0.02, ORANGE)
    c.text("PART OF THIS COMPLETE BREAKFAST", 0.26, 0.08, 0.025, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


@obj("slime_cereal", mass=0.4, weight=1.0, big=True, hero=(0, -1, 0.2), **SLIMED)
def slime_cereal(b, rng, pal):
    """A cartoon tie-in cereal box: neon O's, slime marshmallows, a toy that broke on the drive home."""
    W, D, H = 0.19, 0.06, 0.27
    b.box((W, D, H), mat="box", bevel=0.001)
    b.plane(W, H, loc=(0, -D / 2 - 0.0004, 0), rot=(PI / 2, 0, 0), mat="front", cuts=3)
    b.plane(W, H, loc=(0, D / 2 + 0.0004, 0), rot=(PI / 2, 0, PI), mat="back", cuts=3)
    for i in range(int(rng.integers(5, 12))):
        b.torus(0.007, 0.0028, loc=(float(rng.uniform(-0.09, 0.09)), -D / 2 - float(rng.uniform(0.01, 0.05)), -H / 2 + 0.003),
                rot=(float(rng.normal(0, 0.3)), float(rng.normal(0, 0.3)), 0), mat=f"o{i % 3}", seg=12, rseg=6)
    return {"box": P(ORANGE, 0.6), "front": PR(_cereal_front(rng, "cf"), 0.55), "back": PR(_cereal_front(rng, "cbk"), 0.55),
            "o0": ("crust", {"color": (1.0, 0.4, 0.6)}), "o1": ("crust", {"color": (0.4, 0.9, 0.3)}),
            "o2": ("crust", {"color": (1.0, 0.8, 0.2)})}


def _tape_lid(rng, name):
    c = _cv(192, 192, (1.0, 0.45, 0.7))
    for i in range(48):
        t = 2 * PI * i / 48
        L = 0.06 if i % 4 == 0 else 0.03
        c.line([(0.5 + 0.47 * math.cos(t), 0.5 + 0.47 * math.sin(t)), (0.5 + (0.47 - L) * math.cos(t),
                0.5 + (0.47 - L) * math.sin(t))], 0.01, (1, 1, 1))
    c.circle(0.5, 0.5, 0.36, (0.6, 0.1, 0.65))
    _ct(c, "BUBBLE", 0.5, 0.7, 0.6, 0.14, (1, 1, 1), out=(0.05, 0.05, 0.07))
    _ct(c, "TAPEWORM", 0.5, 0.55, 0.62, 0.12, (1.0, 0.9, 0.1), out=(0.05, 0.05, 0.07))
    _ct(c, "6 FT. OF GUM", 0.5, 0.38, 0.5, 0.07, (1, 1, 1))
    _ct(c, "0 FT. OF DIGNITY", 0.5, 0.3, 0.5, 0.06, (1, 1, 1))
    return c.image(name)


@obj("bubble_tape", mass=0.06, weight=1.1, **SLIMED)
def bubble_tape(b, rng, pal):
    """The tape-measure case of shredded gum, pulled out across the desk to measure everything but the gum."""
    R, H = 0.034, 0.02
    b.lathe([(0.0, 0.0), (R, 0.0), (R, H), (0.0, H)], mat="case", seg=28)
    b.extrude(ellipse(R * 2, R * 2, 32), 0.0012, loc=(0, 0, H + 0.0006), mat="lid")
    b.box((0.014, 0.004, 0.012), loc=(R * 0.95, -0.008, H / 2), mat="case")
    pts = [(R + 0.005 + i * 0.012, -0.012 + 0.006 * math.sin(i * 0.5), 0.001 + 0.0015 * math.sin(i)) for i in range(14)]
    pts[0] = (R + 0.002, -0.012, H / 2)
    _ribbon(b, pts, 0.016, "gum")
    return {"case": P((0.95, 0.4, 0.65), 0.3, coat=0.5), "lid": PR(_tape_lid(rng, "bt"), 0.3),
            "gum": P((1.0, 0.68, 0.8), 0.55)}


def _sticker_sheet(rng, name):
    c = _cv(240, 320, (0.97, 0.97, 0.95))
    c.rect(0.0, 0.0, 1.0, 0.06, ORANGE)
    _lt(c, CABLE + " GROSS-OUT STICKERS", 0.04, 0.05, 0.92, 0.035, (1, 1, 1))
    words = ["SLIMED!", "GROSS!", "EWW!", "NOT FAIR!", "I DON'T KNOW", "DOUBLE DARE", "GOOEY", "BOOGER", "PHYSICAL"]
    for i in range(3):
        for j in range(4):
            cx, cy = 0.2 + i * 0.3, 0.84 - j * 0.22
            if rng.random() < 0.15:          # this one got peeled off and stuck on a little brother
                c.circle(cx, cy, 0.1, (0.85, 0.85, 0.82), ring=0.006)
                continue
            k = int(rng.integers(0, 3))
            if k == 0:
                _splat(c, cx, cy, 0.1, SLIME_G if rng.random() < 0.5 else ORANGE, rng, out=(0.05, 0.05, 0.07))
                _ct(c, str(words[int(rng.integers(0, len(words)))]), cx, cy + 0.02, 0.24, 0.04, (1, 1, 1),
                    out=(0.05, 0.05, 0.07))
            elif k == 1:
                _critter(c, cx, cy, 0.075, NEON[int(rng.integers(0, len(NEON)))], rng)
            else:
                _burst(c, cx, cy, 0.1, NEON[int(rng.integers(0, len(NEON)))], ring=(0.05, 0.05, 0.07))
                _ct(c, str(words[int(rng.integers(0, len(words)))]), cx, cy + 0.02, 0.24, 0.04, (0.05, 0.05, 0.07))
    c.noise(rng, 0.012)
    return c.image(name)


@obj("slime_stickers", mass=0.01, weight=1.0, **SLIMED)
def slime_stickers(b, rng, pal):
    b.box((0.15, 0.2, 0.0008), rot=(0, 0, float(rng.normal(0, 0.1))), mat="paper")
    b.plane(0.15, 0.2, loc=(0, 0, 0.0005), rot=(0, 0, float(rng.normal(0, 0.0))), mat="print", cuts=3)
    return {"paper": P((0.97, 0.97, 0.95), 0.8), "print": PR(_sticker_sheet(rng, "sk"), 0.4)}


def _blimp_skin(rng, name):
    c = _cv(512, 256, ORANGE)
    c.rect(0, 0.0, 1, 0.08, (0.95, 0.95, 0.95))
    _ct(c, CABLE, 0.5, 0.36, 0.7, 0.18, (1, 1, 1), out=(0.05, 0.05, 0.07))
    _splat(c, 0.12, 0.25, 0.12, SLIME_G, rng)
    _splat(c, 0.88, 0.25, 0.12, SLIME_G, rng)
    c.noise(rng, 0.012)
    return _rot(c).image(name)


@obj("kid_blimp", mass=0.12, weight=1.0, hero=(0, -1, 0.3), **SLIMED)
def kid_blimp(b, rng, pal):
    """The toy of the awards-show blimp: orange, splat-logo'd, would not fly no matter how hard you threw it."""
    L, R = 0.09, 0.034
    prof = [(R * math.sqrt(max(0.0, 1 - (z / L) ** 2)) * (1.0 - 0.15 * max(0, z / L)), z) for z in np.linspace(-L, L, 16)]
    prof[0] = (0.0, -L)
    prof[-1] = (0.0, L)
    b.lathe(prof, rot=(0, PI / 2, 0), mat="skin", seg=24)
    for a in (0, PI / 2, PI, 3 * PI / 2):
        b.extrude([(0.0, 0.0), (0.035, 0.0), (0.04, 0.026), (0.016, 0.012)], 0.003,
                  loc=(-L + 0.03, 0, 0), rot=(a + PI / 2, 0, PI), mat="fin")
    b.box((0.04, 0.016, 0.012), loc=(0.005, 0, -R - 0.003), mat="gondola", bevel=0.004)
    for s in (-1, 1):
        b.cyl(0.004, 0.012, loc=(0.0, s * 0.016, -R + 0.002), rot=(0, PI / 2, 0), mat="gondola", seg=10)
        b.box((0.0012, 0.003, 0.016), loc=(0.007, s * 0.016, -R + 0.002), mat="prop")
    return {"skin": PR(_blimp_skin(rng, "bl"), 0.3), "fin": P((0.05, 0.05, 0.07), 0.35), "gondola": P(WHITE, 0.35),
            "prop": P(BLACK, 0.4)}


@obj("chews_trophy", mass=0.5, weight=1.0, hero=(0, -1, 0.3), **SLIMED)
def chews_trophy(b, rng, pal):
    """The orange goblet trophy from the kids' choice-ish awards, dripping slime off the rim on purpose."""
    b.box((0.07, 0.07, 0.03), loc=(0, 0, -0.08), mat="base", bevel=0.003)
    b.lathe([(0.0, -0.065), (0.022, -0.065), (0.012, -0.055), (0.007, -0.03), (0.01, -0.02), (0.006, -0.01),
             (0.0, -0.01)], mat="cup", seg=24)
    b.lathe([(0.0, -0.012), (0.012, -0.012), (0.03, 0.01), (0.04, 0.045), (0.042, 0.06), (0.038, 0.06), (0.0, 0.05)],
            mat="cup", seg=28)
    for s in (-1, 1):
        b.torus(0.014, 0.0035, loc=(s * 0.045, 0, 0.03), rot=(PI / 2, 0, 0), arc=PI, mat="cup", seg=12, rseg=6)
    b.sphere(0.04, loc=(0, 0, 0.058), scale=(1.0, 1.0, 0.18), mat="slime", seg=20)
    for i in range(7):
        a = 2 * PI * i / 7 + float(rng.uniform(0, 0.4))
        d = float(rng.uniform(0.015, 0.045))
        r = 0.041
        b.tube([(r * math.cos(a), r * math.sin(a), 0.058), (r * 1.06 * math.cos(a), r * 1.06 * math.sin(a), 0.05),
                (r * 0.98 * math.cos(a) * (1 - d * 2), r * 0.98 * math.sin(a) * (1 - d * 2), 0.058 - d)],
               lambda t: 0.005 * (1 - 0.5 * t), mat="slime", seg=8)
    pl = _cv(192, 64, (0.85, 0.7, 0.3))
    _ct(pl, "KIDS' CHEWS AWARD", 0.5, 0.88, 0.9, 0.3, (0.1, 0.08, 0.05))
    _ct(pl, f"FAVORITE BURP 19{int(rng.integers(88, 99))}", 0.5, 0.42, 0.9, 0.24, (0.1, 0.08, 0.05))
    b.plane(0.058, 0.019, loc=(0, -0.0356, -0.08), rot=(PI / 2, 0, 0), mat="plaque", cuts=2)
    return {"base": P(BLACK, 0.3, coat=0.6), "cup": P(ORANGE, 0.25, coat=0.7), "slime": ("slime", {"color": SLIME_G}),
            "plaque": PR(pl.image("cpl"), 0.25, metal=0.6)}


# =====================================================================================================
# lore
# =====================================================================================================

LORE_NAMES = {
    "trapped_keeper": "Trapped Keeper Zip Binder", "neon_folder": "Liza Frankly Folder", "five_subject": "Five Starved Notebook",
    "backpack": "JanSpork Backpack", "gel_pens": "Gelly Rolled Gel Pens", "scented_markers": "Mr. Sketchy Scented Markers",
    "crayon_box": "Crayolol 64 Box", "tin_lunchbox": "Tin Lunch Box + Thermos", "plastic_lunchbox": "Plastic Lunch Box",
    "launchables": "Launchables", "drink_pouch": "Capri Sunk Pouch", "orange_jug": "Sunny D-Gen",
    "mini_barrels": "Little Shrug Barrels", "squeeze_buddy": "Squeezurz", "frosting_dip": "Plunkaroos",
    "gusher_box": "Fruit Gushies", "fruit_strip": "Fruit by the Yard", "ring_candy": "Ring Plop", "push_pop": "Shove Pop",
    "sour_pack": "Warheadache", "baby_bottle_pop": "Baby Bottle Flop", "wonder_ball": "Wonder Bawl", "orb_bottle": "Orbedz",
    "crystal_cola": "Crystal Peppy", "chip_bag_3d": "3D Dorkitos", "splurge_can": "Splurge", "pizza_box": "Pizza Hutch Pan Pizza",
    "lunch_tray": "Cafeteria Tray", "school_milk": "Mooville Chocolate Milk",
    "card_toploader": "Rookie Card (Top-Loaded)", "wax_pack": "Wax Pack", "signed_baseball": "Signed Baseball",
    "foam_finger": "Foam #1 Finger", "felt_pennant": "Felt Pennant", "bobblehead": "Giveaway Bobblehead",
    "jersey_scrap": "Replica Jersey Scrap", "snapback_cap": "Snapback", "ticket_stubs": "Ticket Stubs",
    "mini_helmet": "Mini Helmet", "card_binder_sheet": "9-Pocket Binder Page", "satin_jacket": "Satin Team Jacket Scrap",
    "slime_tub": "Pickleodeon Glopp", "splat_sign": "Orange Splat Sign", "putty_egg": "Toot Putty Egg",
    "foam_bead_tub": "Floom", "orange_vhs": "Orange Clamshell VHS", "dare_flag": "Double Dog Dare Flag",
    "slime_cereal": "Cartoon Tie-In Cereal", "bubble_tape": "Bubble Tapeworm", "slime_stickers": "Gross-Out Sticker Sheet",
    "kid_blimp": "Toy Blimp", "chews_trophy": "Kids' Chews Award",
}

LORE_NOTES = {
    "trapped_keeper": ["velcro flap opened during the test. whole class turned around", "zipper ate a worksheet",
                       "banned in three districts for the noise", "the cover was the personality"],
    "neon_folder": ["from the book fair, paid in quarters", "the unicorn has seen things", "pocket held one permission slip, unsigned",
                    "traded for two scratch-and-sniff stickers and regret"],
    "five_subject": ["subject 1: math. subjects 2 through 5: drawings of cars", "spiral bent into a weapon by october",
                     "tabs color-coded, then abandoned", "NAME: field filled out in three different inks"],
    "backpack": ["one strap only. two straps was social death", "every zipper pull a personality", "suede bottom, wet from the bus floor",
                 "patch says skate or die. owner did neither"],
    "gel_pens": ["glitter ink on black paper or nothing", "the white one was worth more than lunch", "half of them skip",
                 "notes passed in sparkle purple"],
    "scented_markers": ["sniffed, not used", "licorice: nobody's favorite, still the first one dead", "cap lost on day one",
                        "a nose full of blue raspberry before 9am"],
    "crayon_box": ["64 colors, one sharpener, zero points", "the sharpener ate the good blue", "burnt sienna untouched",
                   "smells exactly like 1990"],
    "tin_lunchbox": ["the thermos smelled like milk forever", "dented in a playground duel", "cartoon peeled at the corners",
                     "latch held by hope"],
    "plastic_lunchbox": ["latches snapped by week three", "sticker panel half picked off", "the tin ones were banned, this was the rebound"],
    "launchables": ["built a stack, ate it in two bites", "cheese that did not need a fridge, apparently", "traded crackers 1:1 for nothing",
                    "status symbol of the lunch table"],
    "drink_pouch": ["straw went through the back on the first try", "squeezed it, wore it", "a 90s handshake: foil, straw, panic"],
    "orange_jug": ["mom thought it was juice", "2% juice, 98% orange", "shook it, the stuff at the bottom stayed at the bottom"],
    "mini_barrels": ["blue one was currency", "bit the foil, did not twist", "drank the red, wore the red"],
    "squeeze_buddy": ["twisted his head off. no remorse", "squeezed until he wheezed", "the face was the only fruit"],
    "frosting_dip": ["ran out of frosting with four cookies left. every time", "licked the lid", "worth two Launchables in trade"],
    "gusher_box": ["the gush was the point", "pouch torn with teeth", "flavor rush reported to the nurse"],
    "fruit_strip": ["unrolled down the hallway", "the paper had jokes. the jokes had no punchline", "measured a friend, ate the measurement"],
    "ring_candy": ["engaged for the length of recess", "licked on, stuck on", "the ring outlasted the friendship"],
    "push_pop": ["pushed too far, lost it to the floor", "shared, regrettably", "cap lost, lint added"],
    "sour_pack": ["held it 30 seconds on a dare. face never came back", "tears were the flavor", "the bag was the warning label"],
    "baby_bottle_pop": ["dipped, licked, dipped again", "sticky to the elbow", "commercial song still stuck"],
    "wonder_ball": ["surprise inside was a smaller surprise", "foil peeled in one perfect sheet, once", "candy rattled like a maraca"],
    "orb_bottle": ["looked like a lava lamp", "tasted like a lava lamp", "discontinued for the obvious reasons"],
    "crystal_cola": ["clear, but why", "tasted like cola had seen a ghost", "the future, for one summer"],
    "chip_bag_3d": ["bag of air, nine chips", "chips were also mostly air", "fingers orange until thursday"],
    "splurge_can": ["green, loud, legal for some reason", "two of these before a test", "the energy drink before energy drinks"],
    "pizza_box": ["read five books. three were pamphlets", "earned it, ate it in the car", "the star button outlived the pizza"],
    "lunch_tray": ["rectangle pizza on tuesdays", "corn ran into the pizza compartment, a crime", "spork used as a catapult"],
    "school_milk": ["opened the wrong side", "spout torn into a mouth", "chocolate was the only right answer"],
    "card_toploader": ["rookie card. college fund. both gone", "sleeved and top-loaded like a relic", "checked the price guide monthly"],
    "wax_pack": ["gum could cut glass", "three of the same common", "pack smelled better than any card in it"],
    "signed_baseball": ["signature real, person not famous", "caught on a foul, signed in the parking lot", "kept off the shelf, out of the sun"],
    "foam_finger": ["bought in the third, lost by the ninth", "#1 claim unverified", "chewed on during the rain delay"],
    "felt_pennant": ["thumbtacked over the bed", "faded on one side from the window", "team folded. pennant stayed"],
    "bobblehead": ["first 10,000 fans", "head bigger than the career", "still nodding at nothing"],
    "jersey_scrap": ["replica. very replica", "name on the back traded the next year", "torn in a backyard tackle"],
    "snapback_cap": ["sticker never came off", "brim flat, like the season", "snaps set to the last hole"],
    "ticket_stubs": ["rain or shine. mostly rain", "kept in a shoebox for 30 years", "the game everybody claims they were at"],
    "mini_helmet": ["from the gumball machine at the stadium", "facemask bent from a toss", "decal half peeled, team half real"],
    "card_binder_sheet": ["sorted by team, then by vibes", "one empty slot. the good one", "nine commons, zero value"],
    "satin_jacket": ["the jacket of every cousin in 1992", "satin squeaks when you walk", "torn off in a parking lot fight over it"],
    "slime_tub": ["slime makes a noise. nobody knows why", "lid lost in the couch", "contents: green, legally"],
    "splat_sign": ["off the studio wall, allegedly", "splat is ours", "orange enough to taste"],
    "putty_egg": ["pushed finger in, acted shocked", "sent to the hall for it", "the noise was the whole product"],
    "foam_bead_tub": ["in the carpet forever", "crunchy and sticky at once", "the lid lies about how much fun it is"],
    "orange_vhs": ["taped over grandpa's wedding", "clamshell orange enough to find in the dark", "tracking adjusted, never fixed"],
    "dare_flag": ["grabbed it with two seconds left", "physical challenge, failed", "slime on the pole is authentic"],
    "slime_cereal": ["toy broke in the car", "marshmallows tasted green", "milk turned a color with no name"],
    "bubble_tape": ["six feet of gum, one foot of dignity", "measured everything except the gum", "case kept for the crayons after"],
    "slime_stickers": ["best one stuck on a little brother", "GROSS! sticker on a teacher's chair", "backing paper is the souvenir"],
    "kid_blimp": ["did not fly. thrown anyway", "orange was the brand", "propellers lost in the yard"],
    "chews_trophy": ["favorite burp, 1990-something", "slime drip is part of the design", "the only award anyone in the family won"],
}
