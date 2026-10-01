"""Toys: three craze one-of-ones (the fuzzy gremlin, the bean-bag bubble, SPACE OPERA) and the toy aisle for the
regular cubes. Every character, cast member, ship and brand here is original or a parody; shapes evoke the era,
the faces, names and art are ours."""
import math
from contextlib import contextmanager

import numpy as np

from .. import tex
from ..geo import ellipse, rounded_rect, xform
from . import BLACK, CHROME, MET, P, PR, T, WHITE, obj

GREM = dict(group="special", eras=(2,), tags=("gremlin",))
BEAN = dict(group="special", eras=(1, 2), tags=("beanie",))
OPERA = dict(group="special", eras=(0, 1, 2), tags=("opera",))
PI = math.pi


@contextmanager
def _at(b, loc=(0, 0, 0), rot=(0, 0, 0), s=1.0):
    """Build a sub-assembly somewhere else, turned and scaled (so one toy can sit inside its own box)."""
    old = b.frame
    b.frame = old @ xform(loc, rot, (s, s, s))
    try:
        yield
    finally:
        b.frame = old


def _pick(rng, seq):
    return seq[int(rng.integers(0, len(seq)))]


def _clear(rng, a=0.13, tint=(0.95, 0.97, 1.0)):
    """Clear blister/acrylic plastic: a nearly see-through glossy skin with a couple of light streaks. (A true
    transmissive shell goes smoky-black on this stage once two walls overlap, and you can't see the toy inside.)"""
    c = tex.Canvas(64, 64, (*tint, 1))
    c.a[..., 3] = a
    m = np.clip(1 - np.abs((c.x + c.y * 0.6) - float(rng.uniform(0.5, 0.9))) / 0.06, 0, 1)
    m2 = np.clip(1 - np.abs((c.x + c.y * 0.6) - float(rng.uniform(0.25, 0.4))) / 0.025, 0, 1)
    c.a[..., 3] = np.maximum(c.a[..., 3], 0.45 * np.maximum(m, m2))
    return PR(c.image("clear"), 0.04, alpha_from_image=True)


def _fab(c):
    return ("fabric", {"color": tuple(c)})


def _heart(w, h, n=32, cx=0.0, cy=0.0):
    pts = []
    for i in range(n):
        t = 2 * PI * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x / 32 * w, cy + (y + 2.5) / 30 * h))
    return pts


def _leaf(L, W, n=10, sx=1):
    """A pointed ear: base at x=0, tip at x=L (mirrored with sx)."""
    top = [(sx * L * i / n, W * math.sin(PI * i / n) ** 0.7 * (1 - 0.35 * i / n)) for i in range(n + 1)]
    bot = [(x, -y * 0.8) for x, y in reversed(top[1:-1])]
    pts = top + bot
    return pts if sx > 0 else list(reversed(pts))


# ================================================================================================
# canvases
# ================================================================================================

def _streaks(c, rng, amt=0.16, run=10):
    """Fur: vertical brushed streaks multiplied into whatever is painted."""
    n = rng.normal(0, 1, (c.h + run, c.w)).astype(np.float32)
    cs = np.cumsum(n, axis=0)
    n = (cs[run:] - cs[:-run]) / math.sqrt(run)
    c.a[..., :3] = np.clip(c.a[..., :3] * (1 + amt * n[..., None]), 0, 1)


def _stars(c, rng, n=60, col=(1, 1, 1)):
    xs, ys = rng.uniform(0, 1, n), rng.uniform(0, 1, n)
    for x, y in zip(xs, ys):
        c.rect(x, y, x + 1.5 / c.w, y + 1.5 / c.h, (*col, float(rng.uniform(0.4, 1))))


def _shadow_text(c, s, x, y, maxw, size, col, shadow, off=0.012):
    c.text_fit(s, x + off * c.h / c.w, y - off, maxw, size, shadow, bold=True)
    c.text_fit(s, x, y, maxw, size, col, bold=True)


# -- gremlin -------------------------------------------------------------------------------------

FURS = {   # name: (base, accent, pattern, belly)
    "TIGER": ((0.95, 0.56, 0.12), (0.1, 0.07, 0.05), "stripe", (1.0, 0.92, 0.78)),
    "LEOPARD": ((0.9, 0.74, 0.45), (0.28, 0.16, 0.07), "spot", (0.98, 0.93, 0.82)),
    "SNOW OWL": ((0.96, 0.96, 0.94), (0.55, 0.55, 0.62), "fleck", (0.98, 0.85, 0.9)),
    "MIDNIGHT": ((0.08, 0.08, 0.1), (0.4, 0.4, 0.48), "fleck", (0.6, 0.6, 0.68)),
    "BUBBLEGUM": ((1.0, 0.45, 0.72), (0.85, 0.25, 0.55), "fleck", (1.0, 0.9, 0.95)),
    "GRAPE SODA": ((0.5, 0.28, 0.8), (0.3, 0.12, 0.55), "fleck", (0.98, 0.86, 0.4)),
    "ZEBRA": ((0.96, 0.96, 0.96), (0.05, 0.05, 0.05), "stripe", (0.98, 0.62, 0.78)),
    "COCOA": ((0.42, 0.26, 0.15), (0.24, 0.13, 0.07), "fleck", (0.95, 0.85, 0.7)),
    "LAGOON": ((0.12, 0.68, 0.74), (0.05, 0.3, 0.4), "spot", (0.98, 0.95, 0.75)),
    "CHERRY BOMB": ((0.85, 0.08, 0.14), (0.98, 0.98, 0.98), "fleck", (0.98, 0.95, 0.95)),
}
REBOOT_FURS = {
    "ELECTRIC": ((0.15, 0.5, 1.0), (1.0, 0.3, 0.7), "fleck", (1.0, 0.95, 0.4)),
    "TEAL SWIRL": ((0.1, 0.8, 0.7), (0.6, 0.2, 0.9), "stripe", (0.95, 0.95, 0.95)),
    "HOT PINK": ((1.0, 0.2, 0.6), (0.2, 0.1, 0.4), "spot", (0.6, 0.95, 1.0)),
    "LIME OUT": ((0.6, 0.95, 0.1), (0.1, 0.4, 0.9), "fleck", (0.95, 0.95, 0.95)),
}


def _t_fur(rng, name, key, table=FURS):
    base, acc, pat, _ = table[key]
    c = tex.Canvas(256, 256, (*base, 1))
    if pat == "stripe":
        ph = rng.uniform(0, 6)
        m = np.sin(2 * PI * (c.x * 9 + 0.18 * np.sin(2 * PI * c.y * 3 + ph))) - 0.35
        c._blend(np.clip(m * 4, 0, 1), acc)
    elif pat == "spot":
        for _ in range(46):
            x, y = rng.uniform(0, 1, 2)
            r = rng.uniform(0.025, 0.045)
            c.circle(x, y, r, acc, ring=r * 0.45)
            c.circle(x, y, r * 0.5, tuple(0.5 * b + 0.5 * a for a, b in zip(acc, base)))
    else:
        for _ in range(70):
            x, y = rng.uniform(0, 1, 2)
            c.circle(x, y, rng.uniform(0.006, 0.016), (*acc, 0.6))
    _streaks(c, rng, 0.22, 12)
    return c.image(name)


def _t_lcd_eye(rng, name, mood):
    c = tex.Canvas(96, 96, (0.02, 0.02, 0.03, 1))
    if mood == "heart":
        c.poly(_heart(0.7, 0.66, 36, 0.5, 0.47), (1.0, 0.2, 0.45))
    elif mood == "x":
        c.line([(0.25, 0.25), (0.75, 0.75)], 0.12, (1.0, 0.3, 0.2))
        c.line([(0.25, 0.75), (0.75, 0.25)], 0.12, (1.0, 0.3, 0.2))
    elif mood == "spiral":
        pts = [(0.5 + 0.04 * a * math.cos(a * 1.6), 0.5 + 0.04 * a * math.sin(a * 1.6)) for a in np.linspace(0, 9, 60)]
        c.line(pts, 0.06, (0.5, 0.2, 1.0))
    else:
        col = (0.2, 0.75, 1.0) if mood == "blue" else (0.3, 1.0, 0.45)
        c.circle(0.5, 0.48, 0.34, col)
        c.circle(0.5, 0.48, 0.17, (0.02, 0.02, 0.05))
        c.circle(0.6, 0.6, 0.07, (1, 1, 1))
    grid = ((np.floor(c.x * 96) % 4 == 0) | (np.floor(c.y * 96) % 4 == 0)).astype(np.float32)
    c._blend(grid * 0.5, (0, 0, 0))
    return c.image(name)


def _t_grem_box_front(rng, name, fur):
    c = tex.Canvas(200, 276, (0.3, 0.1, 0.5, 1))
    c.gradient((0.45, 0.1, 0.6), (0.05, 0.45, 0.55))
    for k in range(8):                                   # late-90s swooshes
        a = rng.uniform(0, 6)
        pts = [(t, 0.15 + 0.12 * k + 0.05 * math.sin(t * 7 + a)) for t in np.linspace(0, 1, 30)]
        c.line(pts, 0.012, (1.0, 0.85, 0.2, 0.35))
    c.rect(0.0, 0.84, 1.0, 1.0, (1.0, 0.85, 0.1))
    _shadow_text(c, "FURBLIN", 0.07, 0.975, 0.86, 0.13, (0.75, 0.05, 0.4), (0.25, 0.0, 0.15))
    c.text_fit("BY TIGHTR ELECTRONICS", 0.15, 0.858, 0.7, 0.03, (0.25, 0.0, 0.15))
    c.rect(0.08, 0.2, 0.92, 0.8, (0.02, 0.02, 0.05))         # window (punched out below)
    c.text_fit("HE TALKS. HE LEARNS.", 0.05, 0.17, 0.9, 0.05, (1, 1, 1), bold=True)
    c.text_fit("HE WILL NOT SHUT UP.", 0.05, 0.105, 0.9, 0.05, (1.0, 0.9, 0.2), bold=True)
    c.text_fit("COLOR: " + fur + "   AGES 6+   NOT A PET", 0.05, 0.04, 0.9, 0.025, (1, 1, 1))
    c.circle(0.86, 0.86, 0.075, (0.95, 0.15, 0.25))
    c.text_fit("NEW!", 0.795, 0.875, 0.13, 0.04, (1, 1, 1), bold=True)
    c.noise(rng, 0.015)
    c.a[(c.x > 0.09) & (c.x < 0.91) & (c.y > 0.21) & (c.y < 0.79), 3] = 0.0
    return c.image(name)


def _t_grem_box_side(rng, name):
    c = tex.Canvas(140, 276, (0.05, 0.45, 0.55, 1))
    c.gradient((0.45, 0.1, 0.6), (0.05, 0.45, 0.55))
    c.text_fit("FURBLIN", 0.08, 0.95, 0.84, 0.09, (1.0, 0.85, 0.1), bold=True)
    lines = ["WHAT DOES HE WANT?", "NOBODY KNOWS.", "", "SPEAKS FURBLISH", "LEARNS ENGLISH", "WAKES AT 3AM",
             "", "NOT A SPY.", "PROBABLY.", "", "4 AA NOT INCL."]
    for i, s in enumerate(lines):
        c.text_fit(s, 0.08, 0.8 - i * 0.055, 0.84, 0.035, (1, 1, 1))
    c.rect(0.1, 0.04, 0.9, 0.12, (1, 1, 1))
    for i in range(30):
        x = 0.12 + i * 0.025
        c.rect(x, 0.05, x + 0.012 * (1 + i % 3 // 2), 0.11, (0, 0, 0))
    c.noise(rng, 0.015)
    return c.image(name)


FURBLISH = [("GRUB-NAH", "FEED ME"), ("ZEEP", "SLEEP"), ("OOH-BLIK", "DANCE"), ("NAH-NAH", "NO"),
            ("SKREE", "PET ME"), ("DOO-DOO", "UH OH"), ("KEE-YAH", "AGAIN"), ("WUB-WUB", "LOVE YOU"),
            ("BLORT", "SICK"), ("HAH-MUH", "TICKLE"), ("ZORP-ZORP", "WHO ARE YOU"), ("EEP", "SCARED")]


def _t_dictionary(rng, name):
    c = tex.Canvas(180, 250, (0.98, 0.95, 0.85, 1))
    c.rect(0, 0.78, 1, 1, (0.5, 0.25, 0.8))
    c.text_fit("FURBLISH", 0.08, 0.96, 0.84, 0.09, (1.0, 0.85, 0.1), bold=True)
    c.text_fit("TO ENGLISH DICTIONARY", 0.08, 0.85, 0.84, 0.04, (1, 1, 1))
    words = list(FURBLISH)
    rng.shuffle(words)
    for i, (f, e) in enumerate(words[:9]):
        y = 0.72 - i * 0.07
        c.text_fit(f, 0.07, y, 0.42, 0.035, (0.5, 0.15, 0.6), bold=True)
        c.text_fit("= " + e, 0.5, y, 0.45, 0.035, (0.15, 0.15, 0.2))
    c.text_fit("KEEP AWAY FROM WATER. AND YOU.", 0.06, 0.07, 0.88, 0.025, (0.5, 0.25, 0.8))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_grem_stickers(rng, name):
    c = tex.Canvas(256, 192, (0.97, 0.97, 0.98, 1))
    c.rect(0, 0.9, 1, 1, (0.5, 0.25, 0.8))
    c.text_fit("SPEAK FURBLISH! STICKERS", 0.04, 0.98, 0.92, 0.07, (1, 1, 1), bold=True)
    cols = [(1.0, 0.45, 0.72), (0.95, 0.56, 0.12), (0.12, 0.68, 0.74), (0.5, 0.28, 0.8), (1.0, 0.85, 0.1)]
    for i in range(4):
        for j in range(3):
            x, y = 0.13 + i * 0.245, 0.72 - j * 0.28
            if rng.random() < 0.2:
                c.circle(x, y, 0.11, (0.85, 0.85, 0.88), ring=0.008)        # already peeled off
                continue
            col = cols[(i + j * 2) % len(cols)]
            c.circle(x, y, 0.115, (1, 1, 1))
            c.circle(x, y, 0.1, col)
            word = FURBLISH[(i * 3 + j) % len(FURBLISH)][0]
            if (i + j) % 3 == 0:                                         # a sleepy eye glyph
                c.circle(x, y + 0.01, 0.05, (1, 1, 1))
                c.circle(x, y + 0.0, 0.025, (0.1, 0.1, 0.1))
                c.rect(x - 0.05 * 0.75, y + 0.02, x + 0.05 * 0.75, y + 0.065, col)
            else:
                c.text_fit(word, x - 0.08, y + 0.02, 0.16, 0.05, (1, 1, 1), bold=True)
    c.noise(rng, 0.01)
    return c.image(name)


def _t_aa_card(rng, name):
    c = tex.Canvas(160, 220, (0.1, 0.1, 0.12, 1))
    c.rect(0, 0.78, 1, 1, (0.85, 0.55, 0.15))
    c.text_fit("DURASMELL", 0.07, 0.95, 0.86, 0.09, (0.1, 0.1, 0.12), bold=True)
    c.text_fit("4 PACK AA", 0.07, 0.83, 0.86, 0.04, (0.1, 0.1, 0.12))
    c.circle(0.5, 0.97, 0.03, (0.02, 0.02, 0.02))
    c.text_fit("FOR TOYS THAT NEVER SLEEP", 0.06, 0.1, 0.88, 0.03, (1, 1, 1))
    c.text_fit("LASTS UNTIL 3AM", 0.06, 0.05, 0.88, 0.03, (0.85, 0.55, 0.15))
    c.noise(rng, 0.015)
    return c.image(name)


# -- beanie ----------------------------------------------------------------------------------------

BEAN_NAMES = {"bear": ["RETIREMENT", "BUBBLES", "FLOOR PRICE", "GRAIL"], "dog": ["TAGGED", "MINT", "PROVENANCE"],
              "pig": ["BAGHOLDER", "OINKVESTOR"], "lobster": ["PINCHED", "SCARCITY"], "elephant": ["ESCROW", "APPRAISAL"],
              "frog": ["FLOOR", "RIBBIT RETIRED"], "flamingo": ["PUMP", "BUBBLES II"]}


def _t_heart_tag(rng, name):
    c = tex.Canvas(128, 128, (0.82, 0.04, 0.1, 1))
    mask = np.zeros((128, 128), dtype=bool)
    c.poly(_heart(0.98, 0.98, 48, 0.5, 0.5), (0.9, 0.75, 0.3), acc=mask)
    c.poly(_heart(0.86, 0.86, 48, 0.5, 0.505), (0.82, 0.04, 0.1))
    c.text_fit("WHY", 0.22, 0.68, 0.56, 0.3, (1, 1, 1), bold=True)
    c.text_fit("BEANIE", 0.3, 0.33, 0.4, 0.06, (1.0, 0.9, 0.6))
    c.text_fit("BUBBLES", 0.3, 0.25, 0.4, 0.06, (1.0, 0.9, 0.6))
    c.a[..., 3] = mask
    return c.image(name)


def _t_tiedye(rng, name):
    c = tex.Canvas(192, 192, (1, 1, 1, 1))
    cx, cy = rng.uniform(0.3, 0.7, 2)
    a = np.arctan2(c.y - cy, c.x - cx)
    r = np.hypot(c.x - cx, c.y - cy)
    h = (a / (2 * PI) + r * 2.5) % 1.0
    cols = np.array([(1.0, 0.2, 0.3), (1.0, 0.6, 0.1), (1.0, 0.95, 0.2), (0.2, 0.85, 0.3), (0.2, 0.5, 1.0),
                     (0.6, 0.25, 0.9)], dtype=np.float32)
    idx = np.floor(h * 6).astype(int) % 6
    c.a[..., :3] = cols[idx]
    _streaks(c, rng, 0.1, 6)
    return c.image(name)


def _t_dalmatian(rng, name):
    c = tex.Canvas(192, 192, (0.97, 0.97, 0.95, 1))
    for _ in range(40):
        x, y = rng.uniform(0, 1, 2)
        c.circle(x, y, rng.uniform(0.015, 0.04), (0.05, 0.05, 0.05))
    _streaks(c, rng, 0.06, 6)
    return c.image(name)


def _t_price_guide(rng, name):
    c = tex.Canvas(210, 280, (1.0, 0.95, 0.3, 1))
    c.rect(0, 0.84, 1, 1, (0.85, 0.05, 0.1))
    c.text_fit("BEAN COUNTER", 0.04, 0.98, 0.92, 0.1, (1, 1, 1), bold=True)
    c.text_fit("THE BEAN BAG PRICE GUIDE  JUNE 1998", 0.05, 0.865, 0.9, 0.025, (1, 0.95, 0.5))
    c.rect(0.05, 0.42, 0.55, 0.81, (0.6, 0.85, 1.0))           # cover photo: a bear and its heart tag
    c.circle(0.3, 0.6, 0.11, (0.45, 0.3, 0.6))
    c.circle(0.3, 0.74, 0.07, (0.45, 0.3, 0.6))
    c.circle(0.23, 0.79, 0.03, (0.45, 0.3, 0.6))
    c.circle(0.37, 0.79, 0.03, (0.45, 0.3, 0.6))
    c.poly(_heart(0.12, 0.09, 24, 0.43, 0.7), (0.85, 0.05, 0.1))
    c.text_fit("$5,000", 0.58, 0.8, 0.4, 0.07, (0.85, 0.05, 0.1), bold=True)
    c.text_fit("BEAR?!", 0.58, 0.72, 0.4, 0.07, (0.85, 0.05, 0.1), bold=True)
    c.text_fit("RETIRED", 0.58, 0.6, 0.4, 0.04, (0.1, 0.1, 0.4), bold=True)
    c.text_fit("= RICH", 0.58, 0.54, 0.4, 0.04, (0.1, 0.1, 0.4), bold=True)
    rows = [("RETIREMENT BEAR", "$4,200"), ("TAGGED DOG", "$950"), ("PINCHED LOBSTER", "$1,800"),
            ("ESCROW ELEPHANT", "$3,000"), ("BAGHOLDER PIG", "$75"), ("PUMP FLAMINGO", "$600"),
            ("ANY BEAR NO TAG", "$0.50")]
    for i, (a, p) in enumerate(rows):
        y = 0.37 - i * 0.046
        c.text_fit(a, 0.05, y, 0.6, 0.03, (0.1, 0.1, 0.1))
        c.text_fit(p, 0.72, y, 0.24, 0.03, (0.85, 0.05, 0.1), bold=True)
    c.rect(0, 0, 1, 0.04, (0.85, 0.05, 0.1))
    c.text_fit("WHICH ONES WILL PAY FOR COLLEGE", 0.05, 0.035, 0.9, 0.022, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_certificate(rng, name):
    c = tex.Canvas(240, 180, (0.97, 0.94, 0.84, 1))
    gold = (0.75, 0.6, 0.25)
    c.rect(0.03, 0.04, 0.97, 0.96, gold)
    c.rect(0.045, 0.06, 0.955, 0.94, (0.97, 0.94, 0.84))
    c.rect(0.06, 0.08, 0.94, 0.92, gold)
    c.rect(0.065, 0.087, 0.935, 0.913, (0.97, 0.94, 0.84))
    c.text_fit("CERTIFICATE OF AUTHENTICITY", 0.1, 0.86, 0.8, 0.07, (0.4, 0.05, 0.1), bold=True)
    c.text_fit("LIMITED EDITION", 0.3, 0.73, 0.4, 0.05, (0.1, 0.1, 0.1))
    c.text_fit("THIS CERTIFIES THAT YOUR BEAN BAG", 0.12, 0.6, 0.76, 0.04, (0.2, 0.2, 0.2))
    c.text_fit("IS ONE OF ONLY 12,000,000", 0.12, 0.52, 0.76, 0.04, (0.2, 0.2, 0.2))
    c.text_fit("NO. " + str(int(rng.integers(100000, 9999999))), 0.12, 0.4, 0.4, 0.05, (0.4, 0.05, 0.1), bold=True)
    c.scribble(rng, 0.12, 0.2, 0.5, 0.008, (0.1, 0.15, 0.45), 0.02)
    c.line([(0.12, 0.16), (0.5, 0.16)], 0.004, (0.3, 0.3, 0.3))
    c.text_fit("PRESIDENT OF SCARCITY", 0.12, 0.14, 0.38, 0.03, (0.3, 0.3, 0.3))
    c.circle(0.77, 0.27, 0.15, (0.85, 0.7, 0.25))
    c.circle(0.77, 0.27, 0.12, (0.95, 0.82, 0.35), ring=0.01)
    c.text_fit("WHY", 0.715, 0.31, 0.11, 0.07, (0.6, 0.45, 0.1), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


def _t_teeny_insert(rng, name, n):
    c = tex.Canvas(160, 110, (1, 1, 1, 1))
    c.rect(0, 0.62, 1, 1, (0.85, 0.08, 0.1))
    c.text_fit("MCDOUBTFUL'S", 0.05, 0.94, 0.9, 0.14, (1.0, 0.82, 0.1), bold=True)
    c.text_fit("TEENY WEENIES", 0.05, 0.56, 0.9, 0.12, (0.85, 0.08, 0.1), bold=True)
    c.text_fit(f"COLLECT ALL 10. YOU HAVE #{n}", 0.05, 0.33, 0.9, 0.06, (0.1, 0.1, 0.1))
    c.text_fit("DO NOT EAT. DO NOT OPEN.", 0.05, 0.18, 0.9, 0.06, (0.1, 0.1, 0.1))
    c.text_fit("HAPPY-ISH MEAL TOY", 0.05, 0.08, 0.9, 0.05, (0.85, 0.08, 0.1))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_plate(rng, name, s="RETIRED"):
    c = tex.Canvas(160, 40, (0.85, 0.7, 0.3, 1))
    c.rect(0.02, 0.08, 0.98, 0.92, (0.75, 0.6, 0.22), soft=0.02)
    c.text_fit(s, 0.08, 0.75, 0.84, 0.5, (0.15, 0.1, 0.02), bold=True)
    return c.image(name)


# -- space opera -------------------------------------------------------------------------------------

CAST = {   # kind: (card name, card color)
    "jax": ("DUSK RANGER JAX", (0.85, 0.15, 0.1)),
    "vex": ("OVERLORD VEX", (0.1, 0.1, 0.12)),
    "glorp": ("GLORP OF THE DUNES", (0.1, 0.5, 0.25)),
    "marshal": ("STAR MARSHAL ODA", (0.1, 0.3, 0.75)),
    "moth": ("THE MOTH ORACLE", (0.45, 0.2, 0.6)),
}
KINDS = list(CAST)
SKIN = [(0.98, 0.83, 0.7), (0.85, 0.62, 0.45), (0.6, 0.4, 0.28), (0.4, 0.26, 0.18)]


def _portrait(c, cx, cy, r, kind):
    """A head-and-shoulders bust on a card: shapes only, the cast is ours."""
    a = c.h / c.w
    if kind == "jax":
        c.rect(cx - 1.3 * r * a, cy - 1.6 * r, cx + 1.3 * r * a, cy - 0.7 * r, (0.85, 0.75, 0.55))
        c.circle(cx, cy + 0.25 * r, r * 0.95, (0.45, 0.25, 0.1))
        c.circle(cx, cy - 0.1 * r, r * 0.8, (0.9, 0.72, 0.55))
        c.rect(cx - 0.75 * r * a, cy + 0.1 * r, cx + 0.75 * r * a, cy + 0.35 * r, (0.95, 0.5, 0.1))
        c.rect(cx - 0.3 * r * a, cy - 0.5 * r, cx + 0.3 * r * a, cy - 0.45 * r, (0.4, 0.15, 0.1))
    elif kind == "vex":
        c.rect(cx - 1.4 * r * a, cy - 1.6 * r, cx + 1.4 * r * a, cy - 0.6 * r, (0.6, 0.05, 0.08))
        c.poly([(cx - 0.6 * r * a, cy + 0.5 * r), (cx - 1.2 * r * a, cy + 1.4 * r), (cx - 0.3 * r * a, cy + 0.8 * r)],
               (0.95, 0.75, 0.2))
        c.poly([(cx + 0.6 * r * a, cy + 0.5 * r), (cx + 1.2 * r * a, cy + 1.4 * r), (cx + 0.3 * r * a, cy + 0.8 * r)],
               (0.95, 0.75, 0.2))
        c.circle(cx, cy, r, (0.7, 0.05, 0.1))
        c.rect(cx - 0.08 * r * a, cy + 0.2 * r, cx + 0.08 * r * a, cy + 1.0 * r, (0.95, 0.75, 0.2))
        for k in range(-3, 4):
            x = cx + k * 0.17 * r * a
            c.rect(x - 0.04 * r * a, cy - 0.25 * r, x + 0.04 * r * a, cy + 0.1 * r, (0.02, 0.02, 0.02))
    elif kind == "glorp":
        c.rect(cx - 1.2 * r * a, cy - 1.6 * r, cx + 1.2 * r * a, cy - 0.7 * r, (0.5, 0.2, 0.6))
        c.circle(cx, cy - 0.1 * r, r * 0.95, (0.35, 0.75, 0.25))
        for k in (-1, 0, 1):
            ex, ey = cx + k * 0.55 * r * a, cy + (1.0 if k == 0 else 0.8) * r
            c.line([(cx + k * 0.25 * r * a, cy + 0.4 * r), (ex, ey)], 0.08 * r, (0.35, 0.75, 0.25))
            c.circle(ex, ey, 0.22 * r, (1, 1, 0.9))
            c.circle(ex, ey, 0.1 * r, (0.05, 0.05, 0.05))
        c.rect(cx - 0.5 * r * a, cy - 0.55 * r, cx + 0.5 * r * a, cy - 0.4 * r, (0.1, 0.25, 0.08))
    elif kind == "marshal":
        c.rect(cx - 1.4 * r * a, cy - 1.6 * r, cx + 1.4 * r * a, cy - 0.7 * r, (0.95, 0.5, 0.1))
        c.circle(cx, cy - 0.05 * r, r * 1.05, (0.75, 0.9, 1.0, 0.5))
        c.circle(cx, cy - 0.15 * r, r * 0.6, (0.6, 0.4, 0.28))
        c.circle(cx, cy - 0.05 * r, r * 1.05, (0.9, 0.95, 1.0), ring=0.1 * r)
        c.line([(cx + 0.6 * r * a, cy + 0.8 * r), (cx + 0.9 * r * a, cy + 1.5 * r)], 0.05 * r, (0.7, 0.7, 0.75))
        c.circle(cx + 0.9 * r * a, cy + 1.5 * r, 0.12 * r, (1.0, 0.2, 0.2))
    else:
        c.rect(cx - 1.4 * r * a, cy - 1.6 * r, cx + 1.4 * r * a, cy - 0.6 * r, (0.92, 0.9, 0.85))
        for sx in (-1, 1):
            pts = [(cx + sx * (0.3 + 0.5 * t) * r * a, cy + (0.6 + 0.9 * t - 0.4 * t * t) * r) for t in np.linspace(0, 1, 8)]
            c.line(pts, 0.07 * r, (0.6, 0.55, 0.45))
        c.circle(cx, cy, r, (0.92, 0.9, 0.85))
        c.circle(cx, cy - 0.1 * r, r * 0.62, (0.2, 0.18, 0.22))
        c.circle(cx - 0.25 * r * a, cy, 0.12 * r, (1.0, 0.9, 0.4))
        c.circle(cx + 0.25 * r * a, cy, 0.12 * r, (1.0, 0.9, 0.4))


def _logo(c, x, y, w, size):
    _shadow_text(c, "SPACE", x, y, w, size, (1.0, 0.85, 0.1), (0.85, 0.3, 0.05), off=0.01)
    _shadow_text(c, "OPERA", x, y - size * 1.15, w, size, (1.0, 0.85, 0.1), (0.85, 0.3, 0.05), off=0.01)


def _t_cardback(rng, name, kind):
    nm, col = CAST[kind]
    c = tex.Canvas(200, 300, (0.02, 0.02, 0.06, 1))
    _stars(c, rng, 90)
    c.circle(0.5, 0.955, 0.03, (0, 0, 0))
    c.rect(0.05, 0.86, 0.3, 0.93, (0.15, 0.35, 0.85))
    c.text_fit("KENNEL", 0.07, 0.915, 0.21, 0.04, (1, 1, 1), bold=True)
    _logo(c, 0.33, 0.93, 0.6, 0.09)
    c.rect(0.05, 0.2, 0.95, 0.72, (0.25, 0.1, 0.35))         # the photo panel behind the bubble
    c.circle(0.75, 0.62, 0.12, (0.85, 0.45, 0.2))
    c.circle(0.3, 0.42, 0.18, (0.9, 0.65, 0.4))
    _portrait(c, 0.3, 0.46, 0.13, kind)
    c.rect(0.0, 0.06, 1.0, 0.17, col)
    c.text_fit(nm, 0.05, 0.145, 0.9, 0.06, (1, 1, 1), bold=True)
    c.text_fit("3 3/4 INCH ACTION FIGURE", 0.05, 0.05, 0.9, 0.025, (0.9, 0.9, 0.9))
    c.poly([(0.78, 0.86), (0.84, 0.82), (0.9, 0.86), (0.88, 0.79), (0.94, 0.75), (0.87, 0.74), (0.84, 0.68),
            (0.81, 0.74), (0.74, 0.75), (0.8, 0.79)], (1.0, 0.2, 0.2))
    c.text("NEW", 0.79, 0.785, 0.025, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_card_rear(rng, name):
    c = tex.Canvas(200, 300, (0.1, 0.25, 0.6, 1))
    c.text_fit("COLLECT ALL 12!", 0.06, 0.96, 0.88, 0.06, (1.0, 0.85, 0.1), bold=True)
    for i in range(12):
        x, y = 0.08 + (i % 3) * 0.3, 0.84 - (i // 3) * 0.19
        c.rect(x, y - 0.15, x + 0.25, y, (0.02, 0.02, 0.06))
        _portrait(c, x + 0.125, y - 0.07, 0.045, KINDS[i % len(KINDS)])
    c.rect(0.05, 0.03, 0.95, 0.08, (1, 1, 1))
    c.text_fit("MAIL AWAY: 5 PROOFS + $2.50 + 8 WEEKS", 0.07, 0.07, 0.86, 0.025, (0.1, 0.1, 0.1))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_trading_card(rng, name, kind, num):
    nm, col = CAST[kind]
    border = _pick(rng, [(0.15, 0.35, 0.85), (0.85, 0.15, 0.12), (0.95, 0.75, 0.1), (0.1, 0.55, 0.3)])
    c = tex.Canvas(100, 140, (*border, 1))
    c.rect(0.07, 0.2, 0.93, 0.9, (1, 1, 1))
    c.rect(0.1, 0.22, 0.9, 0.88, (0.05, 0.05, 0.12))
    _stars(c, rng, 25)
    c.circle(0.7, 0.75, 0.08, (0.85, 0.45, 0.2))
    _portrait(c, 0.5, 0.52, 0.16, kind)
    c.rect(0.07, 0.06, 0.93, 0.18, (1, 1, 1))
    c.text_fit(nm, 0.1, 0.155, 0.8, 0.06, (0.1, 0.1, 0.1), bold=True)
    c.text_fit("SPACE OPERA", 0.1, 0.98, 0.55, 0.05, (1, 1, 1), bold=True)
    c.circle(0.84, 0.95, 0.06, (1, 1, 1))
    c.text_fit(str(num), 0.79, 0.975, 0.1, 0.05, (0.1, 0.1, 0.1), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def _t_card_back(rng, name):
    c = tex.Canvas(100, 140, (0.75, 0.72, 0.65, 1))
    c.rect(0.06, 0.05, 0.94, 0.95, (0.9, 0.88, 0.82))
    c.text_fit("SPACE OPERA", 0.1, 0.92, 0.8, 0.06, (0.6, 0.1, 0.1), bold=True)
    for i in range(10):
        c.line([(0.12, 0.75 - i * 0.065), (0.88 - 0.2 * (i % 3) / 2, 0.75 - i * 0.065)], 0.008, (0.4, 0.38, 0.35))
    c.text_fit("1977-ISH  KENNEL", 0.1, 0.1, 0.8, 0.04, (0.4, 0.38, 0.35))
    return c.image(name)


def _t_space_scene(rng, name, w=256, h=200, title=True):
    c = tex.Canvas(w, h, (0.02, 0.02, 0.08, 1))
    c.gradient((0.02, 0.02, 0.1), (0.25, 0.05, 0.3))
    _stars(c, rng, 120)
    c.circle(0.78, 0.35, 0.22, (0.9, 0.5, 0.2))
    c.circle(0.75, 0.38, 0.17, (0.95, 0.65, 0.3))
    c.line([(0.5, 0.28), (0.78, 0.4), (1.0, 0.48)], 0.02, (0.95, 0.85, 0.6))
    for k in range(3):                              # three wedge ships in formation, beams flying
        x, y = 0.12 + 0.16 * k, 0.55 - 0.1 * k
        c.poly([(x, y), (x + 0.12, y + 0.03), (x, y + 0.06), (x + 0.03, y + 0.03)], (0.85, 0.85, 0.82))
        c.rect(x - 0.015, y + 0.022, x, y + 0.038, (0.3, 0.7, 1.0))
        c.line([(x + 0.13, y + 0.03), (x + 0.3, y + 0.06)], 0.008, (1.0, 0.2, 0.2))
    _portrait(c, 0.15, 0.2, 0.1, "jax")
    _portrait(c, 0.4, 0.17, 0.08, "glorp")
    _portrait(c, 0.92, 0.8, 0.09, "vex")
    if title:
        _logo(c, 0.05, 0.95, 0.5, 0.12)
    c.noise(rng, 0.015)
    return c.image(name)


def _t_vhs_front(rng, name):
    c = tex.Canvas(200, 300, (0.02, 0.02, 0.03, 1))
    _stars(c, rng, 80)
    c.text_fit("THE", 0.4, 0.97, 0.2, 0.04, (0.9, 0.9, 0.9))
    _logo(c, 0.1, 0.92, 0.8, 0.12)
    c.text_fit("TRILOGY", 0.22, 0.68, 0.56, 0.06, (1.0, 0.85, 0.1), bold=True)
    for k, kind in enumerate(["jax", "vex", "glorp"]):
        _portrait(c, 0.22 + k * 0.28, 0.42, 0.09, kind)
    c.rect(0.0, 0.17, 1.0, 0.25, (0.8, 0.65, 0.2))
    c.text_fit("DIGITALLY REMASTERED (AGAIN)", 0.04, 0.235, 0.92, 0.04, (0.1, 0.05, 0.0), bold=True)
    c.text_fit("NOW WITH 40% MORE CGI", 0.1, 0.12, 0.8, 0.035, (0.9, 0.9, 0.9))
    c.text_fit("3 TAPES   PARTS 4 5 6", 0.1, 0.07, 0.8, 0.03, (0.7, 0.7, 0.7))
    c.text_fit("WE STARTED IN THE MIDDLE", 0.1, 0.035, 0.8, 0.025, (0.7, 0.7, 0.7))
    c.noise(rng, 0.015)
    return c.image(name)


def _t_vhs_spine(rng, name, part):
    c = tex.Canvas(300, 36, (0.05, 0.05, 0.06, 1))
    c.rect(0.02, 0.15, 0.98, 0.85, (0.95, 0.95, 0.92))
    c.text_fit("SPACE OPERA", 0.04, 0.72, 0.5, 0.45, (0.1, 0.1, 0.1), bold=True)
    c.text_fit(f"PART {part}", 0.7, 0.72, 0.25, 0.45, (0.7, 0.1, 0.1), bold=True)
    return c.image(name)


def _t_opera_stickers(rng, name):
    c = tex.Canvas(256, 192, (0.95, 0.95, 0.97, 1))
    c.rect(0, 0.88, 1, 1, (0.02, 0.02, 0.08))
    c.text_fit("SPACE OPERA STICKERS", 0.04, 0.975, 0.92, 0.07, (1.0, 0.85, 0.1), bold=True)
    words = ["PEW PEW", "ZAP!", "HYPERJUMP", "TEAM VEX", "GLORP LIVES", "SAVE THE GALAXY"]
    k = 0
    for i in range(4):
        for j in range(3):
            x, y = 0.13 + i * 0.245, 0.7 - j * 0.28
            if rng.random() < 0.18:
                c.rect(x - 0.1, y - 0.11, x + 0.1, y + 0.11, (0.82, 0.82, 0.85))
                continue
            if (i + j) % 2:
                c.circle(x, y, 0.12, (0.02, 0.02, 0.1))
                _portrait(c, x, y - 0.01, 0.06, KINDS[k % len(KINDS)])
            else:
                c.rect(x - 0.11, y - 0.07, x + 0.11, y + 0.07, _pick(rng, [(1.0, 0.85, 0.1), (0.85, 0.15, 0.1),
                                                                          (0.15, 0.35, 0.85)]))
                c.text_fit(words[k % len(words)], x - 0.1, y + 0.03, 0.2, 0.06, (1, 1, 1), bold=True)
            k += 1
    c.noise(rng, 0.01)
    return c.image(name)


def _t_case_lid(rng, name):
    c = tex.Canvas(256, 180, (0.02, 0.02, 0.06, 1))
    _stars(c, rng, 70)
    _logo(c, 0.06, 0.94, 0.55, 0.14)
    c.text_fit("COLLECTOR'S CASE", 0.06, 0.58, 0.55, 0.06, (1, 1, 1), bold=True)
    c.text_fit("HOLDS 24 FIGURES. OR YOUR LUNCH.", 0.06, 0.48, 0.55, 0.035, (0.8, 0.8, 0.8))
    _portrait(c, 0.8, 0.55, 0.16, "vex")
    _portrait(c, 0.7, 0.2, 0.1, "moth")
    _portrait(c, 0.9, 0.2, 0.1, "marshal")
    c.text_fit("KENNEL", 0.06, 0.12, 0.2, 0.05, (0.3, 0.5, 1.0), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


def _t_mailer(rng, name):
    c = tex.Canvas(160, 120, (0.97, 0.97, 0.95, 1))
    c.rect(0, 0.75, 1, 1, (0.85, 0.15, 0.1))
    c.text_fit("SPECIAL OFFER", 0.06, 0.95, 0.88, 0.12, (1, 1, 1), bold=True)
    c.text_fit("MAIL-AWAY FIGURE", 0.06, 0.66, 0.88, 0.09, (0.1, 0.1, 0.1), bold=True)
    c.text_fit("THE MYSTERY STRANGER", 0.06, 0.48, 0.88, 0.07, (0.85, 0.15, 0.1))
    c.text_fit("ARRIVED IN ONLY 11 WEEKS", 0.06, 0.32, 0.88, 0.05, (0.3, 0.3, 0.3))
    c.text_fit("KENNEL  SPACE OPERA", 0.06, 0.14, 0.88, 0.06, (0.15, 0.35, 0.85), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


# -- era toys -------------------------------------------------------------------------------------

def _t_label(rng, name, words, sub="", bg=(1.0, 0.85, 0.1), ink=(0.1, 0.1, 0.1), w=200, h=70):
    c = tex.Canvas(w, h, (*bg, 1))
    c.text_fit(words, 0.05, 0.85 if sub else 0.72, 0.9, 0.5 if sub else 0.55, ink, bold=True)
    if sub:
        c.text_fit(sub, 0.05, 0.3, 0.9, 0.18, ink)
    c.noise(rng, 0.015)
    return c.image(name)


def _t_reel(rng, name):
    c = tex.Canvas(128, 128, (0, 0, 0, 0))
    c.a[..., 3] = 0
    mask = np.hypot(c.x - 0.5, c.y - 0.5) < 0.495
    c.circle(0.5, 0.5, 0.49, (0.97, 0.97, 0.95))
    for i in range(7):
        a = 2 * PI * i / 7 + 0.2
        x, y = 0.5 + 0.34 * math.cos(a), 0.5 + 0.34 * math.sin(a)
        col = _pick(rng, [(0.3, 0.6, 0.9), (0.85, 0.5, 0.2), (0.2, 0.6, 0.3), (0.8, 0.3, 0.4), (0.6, 0.5, 0.8)])
        c.rect(x - 0.06, y - 0.06, x + 0.06, y + 0.06, (0.05, 0.05, 0.05))
        c.rect(x - 0.05, y - 0.05, x + 0.05, y + 0.05, col)
        c.circle(x + 0.01, y + 0.01, 0.02, (1, 1, 0.8, 0.6))
    c.circle(0.5, 0.5, 0.08, (0.2, 0.2, 0.2))
    c.text_fit("VIEWMEISTER", 0.3, 0.62, 0.4, 0.05, (0.7, 0.1, 0.1), bold=True)
    c.text_fit("3D GRAND CANYON-ISH", 0.3, 0.36, 0.4, 0.035, (0.3, 0.3, 0.3))
    c.a[..., 3] = mask
    return c.image(name)


def _t_oven_front(rng, name, body):
    c = tex.Canvas(200, 140, (*body, 1))
    c.rect(0.08, 0.2, 0.72, 0.62, (0.95, 0.95, 0.95))
    c.rect(0.11, 0.24, 0.69, 0.58, (0.12, 0.08, 0.1))
    c.rect(0.11, 0.24, 0.69, 0.3, (1.0, 0.6, 0.2, 0.6))
    c.text_fit("QUEASY-BAKE", 0.06, 0.95, 0.88, 0.2, (1, 1, 1), bold=True)
    c.text_fit("OVEN", 0.06, 0.74, 0.3, 0.1, (1.0, 0.95, 0.4), bold=True)
    c.text_fit("100 WATT", 0.75, 0.55, 0.22, 0.07, (1, 1, 1))
    c.text_fit("COOKS!", 0.75, 0.43, 0.22, 0.07, (1, 1, 1))
    c.text_fit("SORT OF", 0.75, 0.31, 0.22, 0.07, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


# ================================================================================================
# A) THE FUZZY GREMLIN
# ================================================================================================

def _gremlin(b, baby=False, lcd=False, k=""):
    """Our owl-gremlin: egg body, heavy-lidded googly eyes under angry brows, a hooked beak, pointed leaf ears
    swept up and back, a three-hair top tuft, big orange feet. Front is -Y."""
    sz = 1.08 if baby else 1.0
    b.sphere(0.06, scale=(1.0 * sz, 0.92, 1.1 if not baby else 0.98), mat="fur" + k, seg=24)
    b.sphere(0.045, loc=(0, -0.042, -0.02), scale=(0.82, 0.32, 0.92), mat="belly" + k, seg=16)
    ez, ex, er = (0.018, 0.023, 0.021) if baby else (0.022, 0.024, 0.019)
    for sx in (-1, 1):
        x = sx * ex
        if lcd:
            b.cyl(er * 1.1, 0.012, loc=(x, -0.05, ez), rot=(PI / 2, 0, 0), mat="rim" + k, seg=20)
            b.plane(er * 1.5, er * 1.5, loc=(x, -0.0572, ez), rot=(PI / 2, 0, 0), mat="screen" + k, cuts=2)
            b.torus(er * 1.08, 0.0018, loc=(x, -0.0565, ez), rot=(PI / 2, 0, 0), mat="rim" + k, seg=20, rseg=5)
        else:
            b.sphere(er, loc=(x, -0.043, ez), mat="eye" + k, seg=16)
            b.sphere(er * 0.62, loc=(x, -0.043 - er * 0.88, ez - 0.002), scale=(1, 0.35, 1), mat="iris" + k, seg=12)
            b.sphere(er * 0.32, loc=(x, -0.043 - er * 1.02, ez - 0.002), scale=(1, 0.4, 1), mat="pupil" + k, seg=10)
            b.sphere(er * 0.12, loc=(x + 0.004, -0.043 - er * 1.1, ez + 0.004), mat="eye" + k, seg=6)
        # the heavy half-lid, drooped forward: the sleepy-scheming look (the LCD reboot animates its lids on screen)
        if lcd:
            b.sphere(0.016, loc=(sx * 0.022, -0.05, ez + 0.03), rot=(0, -sx * 0.45, 0), scale=(1.5, 0.55, 0.42),
                     mat="fur" + k, seg=10)
            continue
        prof = [(er * 1.08 * math.cos(a), er * 1.08 * math.sin(a)) for a in np.linspace(0, PI / 2, 7)]
        prof[-1] = (0.0, prof[-1][1])
        b.lathe(prof, loc=(x, -0.043 if not lcd else -0.047, ez), rot=(0.55, 0, 0), mat="lid" + k, seg=18)
        # angry owl brows
        b.sphere(0.016, loc=(sx * 0.022, -0.05, ez + 0.026), rot=(0, -sx * 0.45, 0), scale=(1.5, 0.55, 0.42),
                 mat="fur" + k, seg=10)
    # hooked beak, upper over lower
    b.lathe([(0.0, 0.0), (0.012, 0.002), (0.011, 0.01), (0.006, 0.02), (0.0, 0.026)], loc=(0, -0.052, -0.004),
            rot=(PI / 2 + 0.45, 0, 0), scale=(1.15, 0.8, 1), mat="beak" + k, seg=14)
    b.sphere(0.008, loc=(0, -0.058, -0.014), scale=(1.1, 0.8, 0.55), mat="beak2" + k, seg=10)
    # leaf ears swept up and back
    L, W = (0.04, 0.02) if baby else (0.058, 0.024)
    for sx in (-1, 1):
        rot = (PI / 2, sx * -0.75, -sx * 0.35)
        b.extrude(_leaf(L, W, 10, sx), 0.005, loc=(sx * 0.05, 0.004, 0.03), rot=rot, mat="fur" + k)
        b.extrude(_leaf(L * 0.8, W * 0.6, 10, sx), 0.002, loc=(sx * 0.052, 0.0, 0.031), rot=rot, mat="ear" + k)
    # three-hair top tuft
    for i in range(3):
        a = (i - 1) * 0.5
        pts = [(0, 0.0, 0.058 if not baby else 0.052), (0.012 * math.sin(a), 0.004, 0.08), (0.03 * math.sin(a), 0.02, 0.095),
               (0.038 * math.sin(a), 0.035, 0.09)]
        b.tube(pts, lambda t: 0.0045 * (1 - t) + 0.0008, mat="tuft" + k, seg=6)
    # feet
    for sx in (-1, 1):
        b.sphere(0.017, loc=(sx * 0.026, -0.03, -0.062 if not baby else -0.054), scale=(1.15, 1.5, 0.45),
                 mat="foot" + k, seg=12)
        for t in (-1, 0, 1):
            b.sphere(0.006, loc=(sx * 0.026 + t * 0.009, -0.054, -0.064 if not baby else -0.056), mat="foot" + k, seg=8)


def _gremlin_mats(rng, k="", lcd=False, table=FURS, fur=None):
    key = fur or _pick(rng, list(table))
    base, acc, pat, belly = table[key]
    lidc = _pick(rng, [(0.98, 0.8, 0.7), (0.95, 0.65, 0.75), (0.85, 0.75, 0.6), (0.6, 0.45, 0.4)])
    beak = _pick(rng, [(1.0, 0.6, 0.1), (1.0, 0.8, 0.15), (0.95, 0.45, 0.15)])
    s = {"fur" + k: PR(_t_fur(rng, "grfur", key, table), 0.95), "belly" + k: _fab(belly),
         "lid" + k: P(lidc, 0.35), "beak" + k: P(beak, 0.3, coat=0.4), "beak2" + k: P(tuple(x * 0.8 for x in beak), 0.3),
         "ear" + k: _fab(_pick(rng, [(1.0, 0.7, 0.8), (0.95, 0.85, 0.75), acc])), "tuft" + k: _fab(acc),
         "foot" + k: P(beak, 0.4)}
    if lcd:
        img = _t_lcd_eye(rng, "greye", _pick(rng, ["blue", "green", "heart", "x", "spiral", "blue"]))
        s.update({"rim" + k: P(BLACK, 0.2, coat=0.8), "screen" + k: PR(img, 0.1, glow=1.6)})
    else:
        s.update({"eye" + k: P(WHITE, 0.15, coat=0.9),
                  "iris" + k: P(_pick(rng, [(0.15, 0.45, 0.85), (0.45, 0.25, 0.1), (0.2, 0.6, 0.3), (0.55, 0.2, 0.7)]),
                                0.1, coat=1.0),
                  "pupil" + k: P(BLACK, 0.05, coat=1.0)})
    return s, key


@obj("gremlin", eras=(2,), mass=0.6, weight=1.0, hero=(0, -1, 0), group="era", tags=("gremlin",))
def gremlin(b, rng, pal):
    """The late-90s fuzzy owl-gremlin that talked all night. Original face, era-true colorways."""
    _gremlin(b)
    return _gremlin_mats(rng)[0]


@obj("gremlin_baby", mass=0.35, hero=(0, -1, 0), **GREM)
def gremlin_baby(b, rng, pal):
    _gremlin(b, baby=True)
    return _gremlin_mats(rng, fur=_pick(rng, ["BUBBLEGUM", "SNOW OWL", "LAGOON", "GRAPE SODA", "CHERRY BOMB"]))[0]


@obj("gremlin_keychain", mass=0.03, hero=(0, -1, 0), **GREM)
def gremlin_keychain(b, rng, pal):
    with _at(b, s=0.36):
        _gremlin(b)
    b.cyl(0.0025, 0.006, loc=(0, 0.006, 0.037), mat="ring", seg=8)
    b.torus(0.004, 0.0009, loc=(0, 0.006, 0.043), rot=(0, PI / 2, 0), mat="ring", seg=12, rseg=5)
    for i in range(4):
        b.torus(0.0028, 0.0007, loc=(0, 0.006, 0.049 + i * 0.0045), rot=(0, PI / 2, (i % 2) * PI / 2), mat="ring",
                seg=10, rseg=4)
    b.torus(0.014, 0.0012, loc=(0, 0.006, 0.08), rot=(0, PI / 2, 0), mat="ring", seg=24, rseg=6)
    s, _ = _gremlin_mats(rng)
    s["ring"] = CHROME()
    return s


@obj("gremlin_reboot", mass=0.7, hero=(0, -1, 0), **dict(GREM, eras=(4,)))
def gremlin_reboot(b, rng, pal):
    """The 2010s comeback: same gremlin, LCD eyes that roll, louder fur, worse attitude."""
    _gremlin(b, lcd=True)
    return _gremlin_mats(rng, lcd=True, table=REBOOT_FURS)[0]


@obj("gremlin_box", mass=0.9, hero=(0, -1, 0), **GREM)
def gremlin_box(b, rng, pal):
    W, D, H = 0.16, 0.11, 0.22
    t = 0.0015
    b.box((W, t, H), loc=(0, D / 2, 0), mat="card")
    b.box((t, D, H), loc=(-W / 2, 0, 0), mat="card")
    b.box((t, D, H), loc=(W / 2, 0, 0), mat="card")
    b.box((W, D, t), loc=(0, 0, -H / 2), mat="card")
    with _at(b, loc=(0, D / 2, H / 2), rot=(-2.2, 0, 0)):          # the top flap, torn open to look
        b.box((W, D, t), loc=(0, -D / 2, 0), mat="card")
        b.plane(W, D, loc=(0, -D / 2, t / 2 + 0.0006), mat="top", cuts=2)
    b.plane(W, H, loc=(0, -D / 2 - 0.0005, 0), rot=(PI / 2, 0, 0), mat="front", cuts=3)
    b.plane(W * 0.84, H * 0.6, loc=(0, -D / 2 + 0.004, 0), rot=(PI / 2, 0, 0), mat="window", cuts=2)
    for sx in (-1, 1):
        b.plane(D, H, loc=(sx * (W / 2 + 0.0012), 0, 0), rot=(PI / 2, 0, sx * PI / 2), mat="side", cuts=2)
    b.plane(W - 0.01, H - 0.01, loc=(0, D / 2 - 0.0015, 0), rot=(PI / 2, 0, 0), mat="insert", cuts=2)
    b.box((0.06, 0.04, 0.012), loc=(0, 0.0, -0.088), mat="tray", bevel=0.002)      # the molded seat
    with _at(b, loc=(0, 0.004, -0.006), s=0.72):
        _gremlin(b, k="g")
    s, fur = _gremlin_mats(rng, k="g")
    s.update({"card": ("cardboard", {"color": (0.85, 0.82, 0.75)}), "front": PR(_t_grem_box_front(rng, "gbf", fur), 0.4,
              alpha_from_image=True), "window": _clear(rng),
              "side": PR(_t_grem_box_side(rng, "gbs"), 0.4), "top": PR(_t_grem_box_side(rng, "gbt"), 0.4),
              "insert": PR(_t_fur(rng, "gbin", "GRAPE SODA"), 0.7), "tray": P((0.9, 0.9, 0.92), 0.2)})
    return s


@obj("gremlin_dictionary", mass=0.04, **GREM)
def gremlin_dictionary(b, rng, pal):
    w, h = 0.1, 0.14
    rz = float(rng.normal(0, 0.08))
    b.box((w, h, 0.003), rot=(0, 0, rz), mat="pages")
    b.plane(w, h, loc=(0, 0, 0.0016), rot=(0, 0, rz), mat="cover", cuts=3)
    for dy in (-0.035, 0.035):
        b.box((0.002, 0.012, 0.001), loc=(-w / 2 + 0.003, dy, 0.002), rot=(0, 0, rz), mat="staple")
    b.box((w * 0.98, h * 0.98, 0.002), loc=(0.006, -0.004, -0.0025), rot=(0, 0, rz + 0.04), mat="pages")
    return {"pages": ("paper", {"color": (0.97, 0.95, 0.88)}), "cover": PR(_t_dictionary(rng, "gdict"), 0.6),
            "staple": CHROME()}


@obj("gremlin_batteries", mass=0.12, **GREM)
def gremlin_batteries(b, rng, pal):
    """The blister 4-pack of AAs the gremlin ate every week, and the screw-down battery door it came off of."""
    w, h = 0.08, 0.11
    b.box((w, h, 0.0012), mat="cardb")
    b.plane(w, h, loc=(0, 0, 0.0007), mat="card", cuts=3)
    b.box((0.066, 0.06, 0.016), loc=(0, -0.008, 0.008), mat="blister", bevel=0.004)
    img = tex.battery(rng, "graa")
    for i in range(4):
        x = -0.024 + i * 0.016
        b.cyl(0.00725, 0.049, loc=(x, -0.008, 0.0085), rot=(PI / 2, 0, 0), mat="aa", seg=16)
        b.cyl(0.0027, 0.0025, loc=(x, 0.0175, 0.0085), rot=(PI / 2, 0, 0), mat="cap", seg=10)
    # the battery door, lying on top at an angle
    with _at(b, loc=(0.03, 0.03, 0.02), rot=(0.2, 0.1, 0.7)):
        b.box((0.045, 0.06, 0.003), mat="door", bevel=0.001)
        b.box((0.012, 0.008, 0.004), loc=(0, 0.032, 0), mat="door", bevel=0.001)
        b.cyl(0.004, 0.0035, loc=(0, -0.022, 0.0005), mat="screw", seg=12)
        b.box((0.006, 0.0008, 0.001), loc=(0, -0.022, 0.0025), mat="slot")
        for i in range(5):
            b.box((0.03, 0.0015, 0.0008), loc=(0, -0.008 + i * 0.006, 0.0018), mat="door")
    return {"cardb": ("cardboard", {}), "card": PR(_t_aa_card(rng, "graac"), 0.4), "blister": _clear(rng),
            "aa": ("printed", {"image": img, "rough": 0.3, "metal": 0.2, "ext": "REPEAT"}), "cap": MET((0.75, 0.75, 0.77), 0.2),
            "door": P(_pick(rng, [(0.85, 0.75, 0.62), (0.15, 0.15, 0.17), (0.92, 0.9, 0.86)]), 0.45),
            "screw": CHROME(), "slot": P(BLACK)}


@obj("gremlin_sling", mass=0.08, **GREM)
def gremlin_sling(b, rng, pal):
    """The padded cloth carry pouch with a shoulder strap, so it could talk at you hands-free."""
    b.sphere(0.06, loc=(0, 0, 0.0), scale=(1.0, 0.75, 0.42), mat="pad", seg=20)
    b.torus(0.044, 0.006, loc=(0, 0.004, 0.022), mat="trim", seg=24, rseg=8)
    b.sphere(0.04, loc=(0, 0.004, 0.02), scale=(1.0, 1.0, 0.2), mat="inside", seg=16)
    strap = [(0.046 * math.cos(a) * (1 + 0.5 * math.sin(a)), 0.004 + 0.11 * math.sin(a), 0.022 - 0.014 * math.sin(a))
             for a in np.linspace(0.0, PI, 30)]
    b.tube(strap, 0.0065, mat="trim", seg=8)
    b.box((0.022, 0.014, 0.006), loc=(0.0, 0.114, 0.009), mat="buckle", bevel=0.002)
    b.plane(0.05, 0.026, loc=(0, -0.038, 0.012), rot=(0.9, 0, 0), mat="patch", cuts=2)
    for sx in (-1, 1):       # the ears sticking out of the top
        b.extrude(_leaf(0.04, 0.016, 10, sx), 0.004, loc=(sx * 0.02, 0.012, 0.026), rot=(0.25, 0, sx * 0.6), mat="fur")
    pad = _pick(rng, [(0.5, 0.25, 0.8), (0.1, 0.6, 0.65), (1.0, 0.45, 0.7)])
    return {"pad": _fab(pad), "trim": _fab(_pick(rng, [(1.0, 0.85, 0.1), (0.95, 0.95, 0.95), (0.3, 0.9, 0.3)])),
            "inside": _fab(tuple(c * 0.35 for c in pad)), "buckle": P(BLACK, 0.3),
            "fur": PR(_t_fur(rng, "gslf", _pick(rng, list(FURS))), 0.95),
            "patch": PR(_t_label(rng, "gsl", "FURBLIN", "ON THE GO", bg=(1.0, 0.85, 0.1), ink=(0.5, 0.1, 0.5)), 0.6)}


@obj("gremlin_stickers", mass=0.01, **GREM)
def gremlin_stickers(b, rng, pal):
    b.plane(0.12, 0.09, rot=(0, 0, float(rng.normal(0, 0.1))), mat="sheet", cuts=4)
    b.box((0.12, 0.09, 0.0006), loc=(0, 0, -0.0004), rot=(0, 0, 0), mat="back")
    return {"sheet": PR(_t_grem_stickers(rng, "gstk"), 0.25, coat=0.6), "back": ("paper", {"color": (0.95, 0.93, 0.85)})}


@obj("gremlin_fur", mass=0.005, weight=1.5, **GREM)
def gremlin_fur(b, rng, pal):
    """Locks of loose fur from the one somebody tried to give a haircut."""
    for j in range(int(rng.integers(3, 6))):
        cx, cy = (float(v) for v in rng.normal(0, 0.022, 2))
        a0 = float(rng.uniform(0, 2 * PI))
        k = f"f{j % 3}"
        for _ in range(int(rng.integers(14, 22))):
            a = a0 + float(rng.normal(0, 0.18))
            L = float(rng.uniform(0.025, 0.045))
            ox, oy = (float(v) for v in rng.normal(0, 0.0015, 2))
            bend = float(rng.normal(0, 0.25))
            b.tube([(cx + ox, cy + oy, 0), (cx + ox + L * 0.5 * math.cos(a), cy + oy + L * 0.5 * math.sin(a), 0.003),
                    (cx + ox + L * math.cos(a + bend), cy + oy + L * math.sin(a + bend), 0.001)],
                   lambda t: 0.0014 * (1 - t) + 0.0003, mat=k, seg=5)
    base, acc, _, belly = FURS[_pick(rng, list(FURS))]
    return {"f0": _fab(base), "f1": _fab(base), "f2": _fab(acc if rng.random() < 0.5 else belly)}


# ================================================================================================
# B) THE BEAN-BAG BUBBLE
# ================================================================================================

def _tag(b, at, k, rot=0.0, protector=False):
    """The heart hang tag on its red plastic loop: the only part that was ever worth anything."""
    x, y, z = at
    b.torus(0.006, 0.0008, loc=(x, y, z), rot=(PI / 2, 0, rot), mat="loop" + k, seg=12, rseg=4)
    with _at(b, loc=(x + 0.022 * math.cos(rot - 0.6), y + 0.022 * math.sin(rot - 0.6), 0.002), rot=(0, 0, rot - 0.6 - PI / 2)):
        b.extrude(_heart(0.034, 0.034, 32), 0.0008, mat="tagedge" + k)
        b.plane(0.035, 0.035, loc=(0, 0, 0.00045), mat="tag" + k, cuts=2)
        if protector:
            b.box((0.042, 0.044, 0.005), loc=(0, -0.001, 0), mat="prot" + k, bevel=0.0015)


def _tag_mats(rng, k=""):
    return {"loop" + k: P((0.85, 0.05, 0.1), 0.3), "tagedge" + k: P((0.8, 0.05, 0.1), 0.4),
            "tag" + k: PR(_t_heart_tag(rng, "htag"), 0.3, alpha_from_image=True), "prot" + k: _clear(rng)}


def _beanie(b, kind, k="", tag=True, protector=False):
    """A bean-bag animal sprawled belly-down (head toward +X), and its heart tag. Returns the tag's ear spot."""
    F, D, E = "fab" + k, "dark" + k, "eye" + k
    legs = lambda zs=0.008, l=1.6: [b.sphere(0.014, loc=(sx * 0.03, sy * 0.04, zs), rot=(0, 0, sx * sy * 0.6),  # noqa: E731
                                             scale=(l, 0.8, 0.5), mat=F, seg=10) for sx in (-1, 1) for sy in (-1, 1)]
    ear = (0.05, 0.03, 0.04)
    if kind in ("bear", "dog"):
        b.sphere(0.04, loc=(0, 0, 0.018), scale=(1.3, 1.0, 0.5), mat=F, seg=22)
        legs()
        b.sphere(0.03, loc=(0.062, 0, 0.024), scale=(1.0, 1.05, 0.85), mat=F, seg=22)
        snout = 1.0 if kind == "bear" else 1.5
        b.sphere(0.013, loc=(0.085 + 0.006 * (snout - 1), 0, 0.02), scale=(snout, 1.1, 0.8), mat=D, seg=12)
        b.sphere(0.005, loc=(0.098 + 0.014 * (snout - 1), 0, 0.027), mat=E, seg=8)
        for sy in (-1, 1):
            b.sphere(0.0035, loc=(0.078, sy * 0.012, 0.039), mat=E, seg=8)
            if kind == "bear":
                b.sphere(0.011, loc=(0.056, sy * 0.025, 0.043), scale=(0.5, 1, 1), mat=F, seg=10)
            else:
                b.sphere(0.012, loc=(0.06, sy * 0.034, 0.02), rot=(0, 0, sy * 0.3), scale=(1.6, 0.8, 0.3), mat=D, seg=10)
        if kind == "dog":
            b.tube([(-0.05, 0, 0.02), (-0.065, 0.01, 0.024), (-0.075, 0.02, 0.02)], 0.004, mat=F, seg=6)
            ear = (0.06, 0.04, 0.022)
        else:
            ear = (0.056, 0.03, 0.05)
    elif kind == "pig":
        b.sphere(0.045, loc=(0, 0, 0.022), scale=(1.2, 1.0, 0.55), mat=F, seg=22)
        legs(0.006, 1.2)
        b.sphere(0.03, loc=(0.06, 0, 0.026), scale=(1.0, 1.05, 0.85), mat=F, seg=22)
        b.cyl(0.012, 0.01, loc=(0.09, 0, 0.024), rot=(0, PI / 2, 0), mat=D, seg=14)
        for sy in (-1, 1):
            b.sphere(0.0025, loc=(0.0955, sy * 0.004, 0.025), mat=E, seg=6)
            b.sphere(0.0035, loc=(0.077, sy * 0.012, 0.042), mat=E, seg=8)
            b.extrude([(-0.008, 0), (0.008, 0), (0.0, 0.014)], 0.003, loc=(0.055, sy * 0.022, 0.048),
                      rot=(0.3 * sy, -0.5, PI / 2), mat=F)
        b.tube([(-0.052 + 0.006 * math.cos(a), 0.006 * math.sin(a), 0.03 + 0.0015 * a) for a in np.linspace(0, 9, 18)],
               0.0018, mat=F, seg=5)
        ear = (0.055, 0.025, 0.055)
    elif kind == "lobster":
        b.sphere(0.03, loc=(0.02, 0, 0.016), scale=(1.4, 0.9, 0.5), mat=F, seg=18)
        for i in range(4):
            b.sphere(0.022 - i * 0.003, loc=(-0.025 - i * 0.017, 0, 0.012), scale=(0.7, 1.0, 0.45), mat=F, seg=12)
        for sy in (-1, 0, 1):
            b.sphere(0.012, loc=(-0.1, sy * 0.012, 0.008), rot=(0, 0, sy * 0.5), scale=(1.3, 0.6, 0.25), mat=F, seg=10)
        for sy in (-1, 1):
            b.tube([(0.04, sy * 0.015, 0.016), (0.06, sy * 0.04, 0.014), (0.08, sy * 0.045, 0.014)], 0.005, mat=F, seg=8)
            b.sphere(0.017, loc=(0.1, sy * 0.05, 0.014), scale=(1.4, 0.7, 0.45), mat=F, seg=12)
            b.sphere(0.012, loc=(0.122, sy * 0.06, 0.013), rot=(0, 0, sy * -0.4), scale=(1.5, 0.45, 0.4), mat=F, seg=10)
            b.tube([(0.05, sy * 0.006, 0.02), (0.1, sy * 0.02, 0.025), (0.14, sy * 0.01, 0.02)], 0.0012, mat=F, seg=4)
            b.sphere(0.004, loc=(0.052, sy * 0.01, 0.03), mat=E, seg=8)
        ear = (0.085, 0.045, 0.02)
    elif kind == "elephant":
        b.sphere(0.042, loc=(0, 0, 0.02), scale=(1.25, 1.0, 0.52), mat=F, seg=22)
        legs(0.008, 1.3)
        b.sphere(0.032, loc=(0.06, 0, 0.026), scale=(1.0, 1.05, 0.85), mat=F, seg=22)
        for sy in (-1, 1):
            b.sphere(0.03, loc=(0.052, sy * 0.045, 0.026), rot=(0.0, 0, sy * 0.3), scale=(0.7, 1.0, 0.12), mat=D, seg=14)
            b.sphere(0.0035, loc=(0.082, sy * 0.013, 0.04), mat=E, seg=8)
        b.tube([(0.088, 0, 0.026), (0.108, 0, 0.018), (0.122, 0.004, 0.008), (0.13, 0.015, 0.006)],
               lambda t: 0.009 - 0.004 * t, mat=F, seg=8)
        ear = (0.05, 0.06, 0.03)
    elif kind == "frog":
        b.sphere(0.045, loc=(0, 0, 0.014), scale=(1.1, 1.15, 0.38), mat=F, seg=22)
        b.sphere(0.028, loc=(0.05, 0, 0.016), scale=(0.9, 1.4, 0.55), mat=F, seg=18)
        for sy in (-1, 1):
            b.sphere(0.011, loc=(0.058, sy * 0.022, 0.03), mat=F, seg=12)
            b.sphere(0.006, loc=(0.064, sy * 0.024, 0.036), mat=E, seg=8)
            b.tube([(-0.03, sy * 0.03, 0.008), (-0.06, sy * 0.07, 0.006), (-0.02, sy * 0.085, 0.005),
                    (-0.06, sy * 0.1, 0.004)], 0.008, mat=F, seg=8)
            b.sphere(0.012, loc=(-0.065, sy * 0.104, 0.003), scale=(1.2, 1.0, 0.25), mat=D, seg=10)
            b.tube([(0.04, sy * 0.03, 0.008), (0.06, sy * 0.06, 0.006)], 0.006, mat=F, seg=8)
            b.sphere(0.009, loc=(0.064, sy * 0.066, 0.004), scale=(1.2, 1.0, 0.25), mat=D, seg=10)
        b.tube([(0.065, -0.02, 0.022), (0.075, 0, 0.022), (0.065, 0.02, 0.022)], 0.0015, mat=D, seg=5)
        ear = (0.055, 0.035, 0.025)
    else:   # flamingo
        b.sphere(0.035, loc=(0, 0, 0.018), scale=(1.4, 0.9, 0.55), mat=F, seg=22)
        for sy in (-1, 1):
            b.sphere(0.022, loc=(-0.01, sy * 0.024, 0.024), rot=(0, 0, -sy * 0.3), scale=(1.4, 0.55, 0.3), mat=D, seg=12)
            b.tube([(-0.02, sy * 0.008, 0.008), (-0.08, sy * 0.02, 0.004), (-0.13, sy * 0.016, 0.004)], 0.003, mat=F, seg=6)
        b.tube([(0.04, 0, 0.02), (0.07, 0.02, 0.016), (0.085, 0.0, 0.014), (0.1, -0.03, 0.014), (0.12, -0.03, 0.016)],
               0.007, mat=F, seg=10)
        b.sphere(0.014, loc=(0.125, -0.028, 0.018), mat=F, seg=12)
        b.lathe([(0.006, 0.0), (0.005, 0.01), (0.003, 0.018), (0.0, 0.024)], loc=(0.134, -0.028, 0.015),
                rot=(0, PI / 2 + 0.6, 0), mat=D, seg=10)
        b.sphere(0.0028, loc=(0.128, -0.04, 0.024), mat=E, seg=6)
        b.sphere(0.0028, loc=(0.128, -0.016, 0.024), mat=E, seg=6)
        ear = (0.12, -0.012, 0.02)
    # the tush tag at the back
    b.box((0.012, 0.004, 0.018), loc=(-0.055 if kind != "lobster" else -0.09, -0.015, 0.006), rot=(0.6, 0, 0.3),
          mat="tush" + k)
    if tag:
        _tag(b, ear, k, rot=0.9 if kind != "flamingo" else -0.4, protector=protector)


BEAN_COLORS = {
    "bear": [(0.48, 0.28, 0.65), (0.55, 0.35, 0.2), (0.95, 0.95, 0.95), (0.2, 0.45, 0.85), (0.1, 0.1, 0.1), "tiedye"],
    "dog": ["dalmatian", (0.6, 0.4, 0.22), (0.85, 0.75, 0.55)],
    "pig": [(1.0, 0.68, 0.75)],
    "lobster": [(0.9, 0.12, 0.08)],
    "elephant": [(0.45, 0.55, 0.75), (0.6, 0.6, 0.65)],
    "frog": [(0.2, 0.7, 0.2), (0.4, 0.85, 0.1)],
    "flamingo": [(1.0, 0.45, 0.65)],
}
DARK = {"bear": (0.96, 0.9, 0.8), "dog": (0.15, 0.1, 0.08), "pig": (0.95, 0.5, 0.6), "lobster": (0.8, 0.08, 0.06),
        "elephant": (0.95, 0.75, 0.8), "frog": (0.95, 0.85, 0.2), "flamingo": (0.1, 0.1, 0.1)}


def _beanie_mats(rng, kind, k=""):
    col = _pick(rng, BEAN_COLORS[kind])
    if col == "tiedye":
        fab = PR(_t_tiedye(rng, "tdye"), 0.95)
    elif col == "dalmatian":
        fab = PR(_t_dalmatian(rng, "dalm"), 0.95)
    else:
        fab = _fab(col)
    dark = DARK[kind]
    if kind == "bear" and col in ((0.95, 0.95, 0.95),):
        dark = (0.85, 0.82, 0.78)
    if kind == "dog" and col == "dalmatian":
        dark = (0.08, 0.08, 0.08)
    s = {"fab" + k: fab, "dark" + k: _fab(dark), "eye" + k: P(BLACK, 0.05, coat=1.0),
         "tush" + k: _fab((0.97, 0.97, 0.95))}
    s.update(_tag_mats(rng, k))
    return s


def _bean_obj(kind):
    def fn(b, rng, pal):
        _beanie(b, kind, protector=rng.random() < 0.35)
        return _beanie_mats(rng, kind)
    fn.__name__ = "beanie_" + kind
    return fn


for _kind in ("dog", "pig", "lobster", "elephant", "frog", "flamingo"):
    obj("beanie_" + _kind, mass=0.12, **BEAN)(_bean_obj(_kind))
obj("beanie_bear", mass=0.12, eras=(1, 2), group="era", tags=("beanie",))(_bean_obj("bear"))


@obj("beanie_tag_protector", mass=0.01, **BEAN)
def beanie_tag_protector(b, rng, pal):
    """Loose clear tag protectors, some still holding a heart tag snipped off something 'worthless'."""
    specs = {}
    for i in range(int(rng.integers(3, 6))):
        x, y = (float(v) for v in rng.normal(0, 0.025, 2))
        rz = float(rng.uniform(0, 2 * PI))
        with _at(b, loc=(x, y, i * 0.006), rot=(0, 0, rz)):
            b.box((0.042, 0.046, 0.005), mat="prot", bevel=0.0015)
            b.box((0.004, 0.01, 0.0055), loc=(0, 0.025, 0), mat="prot")
            if rng.random() < 0.7:
                b.extrude(_heart(0.034, 0.034, 32), 0.0008, mat="tagedge")
                b.plane(0.035, 0.035, loc=(0, 0, 0.00045), mat="tag", cuts=2)
    specs.update(_tag_mats(rng))
    specs["prot"] = _clear(rng)
    return specs


@obj("beanie_price_guide", mass=0.2, **BEAN)
def beanie_price_guide(b, rng, pal):
    w, h = 0.21, 0.28
    b.box((w, h, 0.004), mat="pages")
    b.plane(w, h, loc=(0, 0, 0.0021), mat="cover", cuts=4)
    return {"pages": ("paper", {"color": (0.95, 0.94, 0.9)}), "cover": PR(_t_price_guide(rng, "bpg"), 0.35, coat=0.4)}


@obj("beanie_display_case", mass=0.4, hero=(0, -0.6, 0.8), **BEAN)
def beanie_display_case(b, rng, pal):
    """The clear acrylic case: the bear never touched air again."""
    W, D, H, t = 0.16, 0.11, 0.075, 0.002
    b.box((W + 0.01, D + 0.01, 0.012), loc=(0, 0, -H / 2 - 0.006), mat="base", bevel=0.002)
    for sx in (-1, 1):
        b.box((t, D, H), loc=(sx * W / 2, 0, 0), mat="acryl")
        b.box((W, t, H), loc=(0, sx * D / 2, 0), mat="acryl")
    b.box((W + t, D + t, t), loc=(0, 0, H / 2), mat="acryl")
    b.plane(0.06, 0.012, loc=(0, -D / 2 - 0.0056, -H / 2 - 0.006), rot=(PI / 2, 0, 0), mat="plate", cuts=2)
    kind = _pick(rng, ["bear", "bear", "lobster", "elephant", "pig"])
    with _at(b, loc=(-0.01, -0.005, -H / 2), s=0.62 if kind != "lobster" else 0.55):
        _beanie(b, kind)
    s = _beanie_mats(rng, kind)
    s.update({"base": P(BLACK, 0.25, coat=0.6), "acryl": _clear(rng),
              "plate": PR(_t_plate(rng, "bplate", _pick(rng, ["RETIRED", "MINT W/ TAG", "1ST GEN", "DO NOT TOUCH"])), 0.25,
                          metal=0.8)})
    return s


@obj("beanie_teeny", mass=0.03, **BEAN)
def beanie_teeny(b, rng, pal):
    """The fast-food mini, still sealed in its baggie with the insert, because opening it kills the value."""
    rings = []
    for i in range(9):
        u = i / 8
        x = -0.05 + 0.1 * u
        w = 0.04 + 0.004 * math.sin(PI * u)
        th = 0.004 + 0.012 * math.sin(PI * u) ** 0.5
        rings.append([(x, -w, 0), (x, 0, -th * 0.4), (x, w, 0), (x, 0, th)])
    b.loft(rings, mat="bag")
    for sx in (-1, 1):
        b.box((0.004, 0.084, 0.0008), loc=(sx * 0.051, 0, 0), mat="seal")
    kind = _pick(rng, ["bear", "pig", "dog", "frog", "lobster", "elephant"])
    with _at(b, loc=(-0.008, 0.0, -0.002), s=0.4):
        _beanie(b, kind)
    b.plane(0.05, 0.034, loc=(0.02, 0.012, 0.0055), rot=(0, 0, 0.08), mat="insert", cuts=2)
    s = _beanie_mats(rng, kind)
    s.update({"bag": _clear(rng), "seal": _clear(rng, 0.35),
              "insert": PR(_t_teeny_insert(rng, "tins", int(rng.integers(1, 11))), 0.5)})
    return s


@obj("beanie_certificate", mass=0.01, **BEAN)
def beanie_certificate(b, rng, pal):
    rz = float(rng.normal(0, 0.06))
    b.plane(0.2, 0.15, rot=(0, 0, rz), mat="paper", cuts=4)
    b.cyl(0.018, 0.0012, loc=(0.05 * math.cos(rz) + 0.002, 0.0, 0.0008), mat="seal", seg=20)
    b.extrude([(-0.006, 0), (0.006, 0), (0.008, -0.03), (0.0, -0.024), (-0.008, -0.03)], 0.0005,
              loc=(0.05, -0.012, 0.0002), mat="ribbon")
    return {"paper": PR(_t_certificate(rng, "bcert"), 0.6), "seal": ("gold", {"rough": 0.3}),
            "ribbon": P((0.6, 0.05, 0.1), 0.4)}


# ================================================================================================
# C) SPACE OPERA
# ================================================================================================

def _fig(b, kind, k="", rng=None):
    """A 3 3/4 inch figure from our space-opera cast, standing (z up), facing -Y."""
    L, TP, SK, X = "leg" + k, "top" + k, "skin" + k, "acc" + k
    robe = kind == "moth"
    if robe:
        b.lathe([(0.0, 0.0), (0.017, 0.0), (0.014, 0.03), (0.012, 0.06), (0.0, 0.07)], mat=TP, seg=14)
    else:
        for sx in (-1, 1):
            b.box((0.011, 0.012, 0.04), loc=(sx * 0.0072, 0, 0.022), mat=L, bevel=0.002)
            b.box((0.012, 0.017, 0.006), loc=(sx * 0.0072, -0.002, 0.003), mat="boot" + k, bevel=0.0015)
        b.box((0.026, 0.014, 0.01), loc=(0, 0, 0.044), mat=L, bevel=0.002)
        b.box((0.027, 0.003, 0.004), loc=(0, -0.007, 0.048), mat=X)                 # belt
    b.box((0.028, 0.015, 0.028), loc=(0, 0, 0.062), mat=TP, bevel=0.003)
    for sx in (-1, 1):
        b.tube([(sx * 0.017, 0, 0.073), (sx * 0.02, -0.004, 0.058), (sx * 0.021, -0.009, 0.046)], 0.0045, mat=TP, seg=8)
        b.sphere(0.0042, loc=(sx * 0.021, -0.01, 0.043), mat=SK, seg=8)
    b.cyl(0.0035, 0.006, loc=(0, 0, 0.078), mat=SK, seg=8)
    if kind == "jax":
        b.sphere(0.0085, loc=(0, 0, 0.087), mat=SK, seg=14)
        b.sphere(0.009, loc=(0, 0.002, 0.09), scale=(1.02, 1.0, 0.8), mat="hair" + k, seg=12)
        b.box((0.018, 0.004, 0.004), loc=(0, -0.008, 0.091), mat=X, bevel=0.001)
        b.box((0.012, 0.004, 0.003), loc=(0.021, -0.015, 0.046), mat="gun" + k)
        b.box((0.004, 0.012, 0.003), loc=(0.021, -0.024, 0.047), mat="gun" + k)
    elif kind == "vex":
        b.sphere(0.0098, loc=(0, 0, 0.088), scale=(1, 1, 1.1), mat=TP, seg=14)
        b.box((0.012, 0.003, 0.0045), loc=(0, -0.0095, 0.088), mat="visor" + k)
        b.box((0.003, 0.004, 0.012), loc=(0, -0.008, 0.095), mat=X)
        for sx in (-1, 1):
            b.tube([(sx * 0.007, 0, 0.094), (sx * 0.014, 0.002, 0.1), (sx * 0.016, 0.006, 0.108)],
                   lambda t: 0.003 * (1 - t) + 0.0006, mat=X, seg=6)
            b.sphere(0.006, loc=(sx * 0.016, 0, 0.074), scale=(1.2, 1.1, 0.7), mat=X, seg=10)
        b.box((0.034, 0.0025, 0.07), loc=(0, 0.009, 0.045), rot=(-0.08, 0, 0), mat="cape" + k)
    elif kind == "glorp":
        b.sphere(0.013, loc=(0, 0, 0.09), scale=(1.15, 1.0, 0.9), mat=SK, seg=14)
        for sx in (-1, 0, 1):
            top = (sx * 0.01, -0.002, 0.11 if sx == 0 else 0.105)
            b.tube([(sx * 0.004, 0, 0.098), top], 0.0012, mat=SK, seg=5)
            b.sphere(0.0035, loc=top, mat="eyew" + k, seg=8)
            b.sphere(0.0016, loc=(top[0], top[1] - 0.003, top[2]), mat="visor" + k, seg=6)
        b.box((0.016, 0.003, 0.002), loc=(0, -0.012, 0.086), mat="visor" + k)
    elif kind == "marshal":
        b.sphere(0.007, loc=(0, 0, 0.088), mat=SK, seg=12)
        b.sphere(0.0125, loc=(0, 0, 0.089), mat="dome" + k, seg=16)
        b.cyl(0.011, 0.004, loc=(0, 0, 0.078), mat=X, seg=14)
        b.tube([(0.008, 0, 0.098), (0.012, 0.002, 0.108)], 0.0007, mat=X, seg=4)
        b.sphere(0.0016, loc=(0.012, 0.002, 0.109), mat="gun" + k, seg=6)
        b.box((0.02, 0.008, 0.024), loc=(0, 0.011, 0.062), mat=X, bevel=0.002)
    else:
        b.sphere(0.0095, loc=(0, 0, 0.087), mat=TP, seg=14)
        b.sphere(0.0068, loc=(0, -0.004, 0.086), mat="visor" + k, seg=12)
        for sx in (-1, 1):
            b.sphere(0.0013, loc=(sx * 0.0028, -0.01, 0.087), mat="eyew" + k, seg=6)
            b.tube([(sx * 0.003, 0, 0.096), (sx * 0.01, -0.002, 0.108), (sx * 0.02, 0.0, 0.112)],
                   lambda t: 0.0025 * (1 - t) + 0.0006, mat=X, seg=5)
    rng = rng or np.random.default_rng(0)
    pal = {
        "jax": dict(top=(0.88, 0.8, 0.62), leg=(0.5, 0.35, 0.2), acc=(0.95, 0.5, 0.1), hair=(0.45, 0.25, 0.1)),
        "vex": dict(top=(0.6, 0.05, 0.08), leg=(0.08, 0.08, 0.09), acc=(0.95, 0.75, 0.2), hair=(0, 0, 0)),
        "glorp": dict(top=(0.5, 0.2, 0.6), leg=(0.45, 0.35, 0.25), acc=(0.3, 0.2, 0.1), hair=(0, 0, 0)),
        "marshal": dict(top=(0.95, 0.5, 0.1), leg=(0.55, 0.55, 0.58), acc=(0.7, 0.7, 0.74), hair=(0, 0, 0)),
        "moth": dict(top=(0.92, 0.9, 0.84), leg=(0.9, 0.88, 0.8), acc=(0.6, 0.55, 0.45), hair=(0, 0, 0)),
    }[kind]
    skin = {"glorp": (0.35, 0.75, 0.25), "moth": (0.3, 0.28, 0.3)}.get(kind, _pick(rng, SKIN))
    return {L: P(pal["leg"], 0.45), TP: P(pal["top"], 0.45), SK: P(skin, 0.45), X: P(pal["acc"], 0.35),
            "boot" + k: P((0.15, 0.1, 0.07) if kind != "marshal" else (0.2, 0.2, 0.22), 0.4),
            "hair" + k: P(pal["hair"], 0.5), "gun" + k: P(BLACK, 0.4), "visor" + k: P(BLACK, 0.15, coat=0.8),
            "cape" + k: P((0.05, 0.05, 0.06), 0.5), "eyew" + k: P((1.0, 0.95, 0.6) if kind == "moth" else WHITE, 0.2),
            "dome" + k: _clear(rng, 0.18, (0.85, 0.93, 1.0))}


@obj("opera_saber", mass=0.25, **OPERA)
def opera_saber(b, rng, pal):
    """The collapsible toy laser sword: two blade sections out, the third jammed forever."""
    hilt = [(0.0, 0.0), (0.016, 0.0), (0.017, 0.006), (0.014, 0.01), (0.014, 0.075), (0.017, 0.08), (0.017, 0.1),
            (0.021, 0.112), (0.021, 0.118), (0.015, 0.12), (0.0, 0.12)]
    R = (0, PI / 2, 0)
    b.lathe(hilt, loc=(-0.13, 0, 0), rot=R, mat="hilt", seg=20)
    for i in range(7):
        b.torus(0.0145, 0.0022, loc=(-0.13 + 0.016 + i * 0.0085, 0, 0), rot=R, mat="grip", seg=18, rseg=5)
    b.box((0.012, 0.008, 0.006), loc=(-0.13 + 0.09, 0, 0.017), mat="button", bevel=0.002)
    b.box((0.03, 0.01, 0.004), loc=(-0.13 + 0.05, 0, -0.016), mat="hilt", bevel=0.001)
    for i in range(3):
        b.box((0.003, 0.003, 0.003), loc=(-0.13 + 0.035 + i * 0.012, 0, -0.019), mat="button")
    x = -0.01
    for r, L in ((0.012, 0.09), (0.0098, 0.09), (0.0078, 0.06 if rng.random() < 0.6 else 0.09)):
        b.cyl(r, L, loc=(x + L / 2, 0, 0), rot=R, mat="blade", seg=16)
        b.torus(r, 0.0012, loc=(x + L - 0.002, 0, 0), rot=R, mat="collar", seg=16, rseg=4)
        x += L - 0.006
    b.sphere(0.0078, loc=(x + 0.005, 0, 0), scale=(0.9, 1, 1), mat="blade", seg=12)
    col = _pick(rng, [(0.2, 1.0, 0.2), (0.2, 0.5, 1.0), (1.0, 0.1, 0.1), (0.7, 0.2, 1.0)])
    return {"hilt": MET((0.7, 0.7, 0.72), 0.3), "grip": P(BLACK, 0.6), "button": P((0.9, 0.1, 0.1), 0.3),
            "blade": P(col, 0.15, coat=0.6, glow=1.8), "collar": P(tuple(c * 0.7 for c in col), 0.3)}


@obj("opera_carded", mass=0.06, hero=(0, -1, 0), **OPERA)
def opera_carded(b, rng, pal):
    """A figure still sealed on its cardback. Nobody opened these. Okay, everybody opened these."""
    kind = _pick(rng, KINDS)
    w, h = 0.1, 0.15
    b.box((w, 0.0009, h), mat="cardb")
    b.plane(w, h, loc=(0, -0.0006, 0), rot=(PI / 2, 0, 0), mat="front", cuts=3)
    b.plane(w, h, loc=(0, 0.0006, 0), rot=(PI / 2, 0, PI), mat="rear", cuts=3)
    b.box((0.05, 0.022, 0.1), loc=(0.016, -0.011, -0.012), mat="bubble", bevel=0.006)
    b.box((0.012, 0.016, 0.02), loc=(-0.018, -0.008, -0.04), mat="bubble", bevel=0.003)   # accessory pocket
    with _at(b, loc=(0.016, -0.011, -0.058), s=0.88):
        s = _fig(b, kind, rng=rng)
    b.box((0.003, 0.012, 0.003), loc=(-0.018, -0.008, -0.04), mat="gun")
    s.update({"cardb": ("cardboard", {}), "front": PR(_t_cardback(rng, "opcard", kind), 0.35, coat=0.3),
              "rear": PR(_t_card_rear(rng, "oprear"), 0.4), "bubble": _clear(rng)})
    return s


@obj("opera_figures", mass=0.06, **OPERA)
def opera_figures(b, rng, pal):
    """Loose figures, one missing its gun, one chewed by a younger brother."""
    s = {}
    kinds = list(KINDS)
    rng.shuffle(kinds)
    n = int(rng.integers(2, 4))
    for i in range(n):
        x = (i - (n - 1) / 2) * 0.045
        with _at(b, loc=(x, float(rng.normal(0, 0.01)), 0.008), rot=(PI / 2, 0, float(rng.normal(0, 0.4)))):
            s.update(_fig(b, kinds[i], k=str(i), rng=rng))
    return s


@obj("opera_ship", mass=0.5, big=True, **OPERA)
def opera_ship(b, rng, pal):
    """THE RUSTY COMET: our freighter. Swept wedge hull, twin engines, bubble cockpit, a dorsal fin."""
    hull = [(0.11, 0.0), (0.02, 0.03), (-0.04, 0.085), (-0.075, 0.085), (-0.06, 0.03), (-0.09, 0.025), (-0.09, -0.025),
            (-0.06, -0.03), (-0.075, -0.085), (-0.04, -0.085), (0.02, -0.03)]
    b.extrude(hull, 0.016, mat="hull", bevel=0.002)
    b.extrude([(0.06, 0.0), (0.0, 0.022), (-0.07, 0.022), (-0.07, -0.022), (0.0, -0.022)], 0.012, loc=(0, 0, 0.012),
              mat="hull", bevel=0.002)
    b.sphere(0.013, loc=(0.04, 0, 0.02), scale=(1.5, 0.9, 0.7), mat="glass", seg=14)
    b.extrude([(0.0, 0.0), (-0.05, 0.0), (-0.06, 0.035), (-0.035, 0.035)], 0.003, loc=(0, 0, 0.0), rot=(PI / 2, 0, 0),
              mat="stripe")
    for sy in (-1, 1):
        b.cyl(0.011, 0.07, loc=(-0.06, sy * 0.05, 0.004), rot=(0, PI / 2, 0), mat="engine", seg=16)
        b.cyl(0.0085, 0.004, loc=(-0.096, sy * 0.05, 0.004), rot=(0, PI / 2, 0), mat="glow", seg=16)
        b.box((0.07, 0.006, 0.0012), loc=(-0.02, sy * 0.05, 0.0086), rot=(0, 0, -sy * 0.55), mat="stripe")
        b.cyl(0.0022, 0.05, loc=(-0.01, sy * 0.056, 0.0), rot=(0, PI / 2, 0), mat="engine", seg=8)
        for gx in (0.02, -0.05):
            b.cyl(0.0015, 0.01, loc=(gx, sy * 0.02, -0.012), mat="engine", seg=6)
            b.cyl(0.004, 0.0015, loc=(gx, sy * 0.02, -0.017), mat="engine", seg=10)
    b.box((0.04, 0.004, 0.0012), loc=(0.02, 0, 0.0186), mat="stripe")
    hc = _pick(rng, [(0.9, 0.9, 0.87), (0.85, 0.82, 0.75), (0.75, 0.78, 0.8)])
    return {"hull": P(hc, 0.45), "glass": T((0.4, 0.6, 0.9), 0.05), "stripe": P(_pick(rng, [(0.95, 0.45, 0.1),
            (0.85, 0.12, 0.1), (0.15, 0.35, 0.8)]), 0.4), "engine": P((0.35, 0.35, 0.38), 0.5),
            "glow": P((0.3, 0.7, 1.0), 0.2, glow=2.0)}


@obj("opera_mask", mass=0.2, hero=(0, -1, 0), **OPERA)
def opera_mask(b, rng, pal):
    """OVERLORD VEX's helm, the drugstore costume version: crimson, gold ram horns, a crest and a slit visor."""
    b.sphere(0.065, scale=(0.82, 0.6, 1.0), mat="helm", seg=24)
    b.box((0.012, 0.11, 0.025), loc=(0, 0.0, 0.055), mat="gold", bevel=0.004)
    b.sphere(0.03, loc=(0, -0.034, 0.015), scale=(1.6, 0.35, 0.3), mat="gold", seg=14)
    b.box((0.085, 0.01, 0.016), loc=(0, -0.037, 0.0), mat="visor", bevel=0.003)
    for i in range(-3, 4):
        b.box((0.004, 0.006, 0.02), loc=(i * 0.011, -0.041, 0.0), mat="gold", bevel=0.0008)
    for sx in (-1, 1):
        pts = [(sx * (0.045 + 0.03 * math.sin(a * 0.5)) + sx * 0.0, 0.01 - 0.03 * math.sin(a), 0.03 + 0.03 * math.cos(a))
               for a in np.linspace(0, 3.6, 12)]
        b.tube(pts, lambda t: 0.012 * (1 - t) + 0.002, mat="gold", seg=10)
        b.box((0.03, 0.012, 0.03), loc=(sx * 0.03, -0.03, -0.035), rot=(0, sx * 0.3, 0), mat="helm", bevel=0.004)
    for i in range(4):
        b.box((0.035, 0.008, 0.004), loc=(0, -0.034, -0.03 - i * 0.008), mat="visor", bevel=0.001)
    b.tube([(-0.05, 0.02, 0.0), (0.0, 0.05, 0.0), (0.05, 0.02, 0.0)], 0.0015, mat="elastic", seg=5)
    return {"helm": P((0.6, 0.04, 0.07), 0.25, coat=0.6), "gold": P((0.95, 0.72, 0.2), 0.3, coat=0.5),
            "visor": P(BLACK, 0.15, coat=0.8), "elastic": P(BLACK, 0.6)}


@obj("opera_case", mass=0.6, big=True, **OPERA)
def opera_case(b, rng, pal):
    W, D, H = 0.2, 0.15, 0.07
    b.box((W, D, H), mat="vinyl", bevel=0.012, seg=3)
    b.plane(W * 0.9, D * 0.86, loc=(0, 0, H / 2 + 0.0006), mat="lid", cuts=3)
    b.box((W + 0.002, D + 0.002, 0.004), loc=(0, 0, 0.004), mat="zip", bevel=0.0015)
    b.tube([(-0.035, -D / 2, 0.0), (-0.03, -D / 2 - 0.025, 0.0), (0.03, -D / 2 - 0.025, 0.0), (0.035, -D / 2, 0.0)],
           0.005, mat="vinyl", seg=8)
    b.box((0.01, 0.006, 0.02), loc=(0.07, -D / 2 - 0.002, 0.004), mat="zip", bevel=0.001)
    return {"vinyl": P(BLACK, 0.3, coat=0.6), "lid": PR(_t_case_lid(rng, "opcase"), 0.3, coat=0.5),
            "zip": MET((0.75, 0.75, 0.78), 0.3)}


@obj("opera_lunchbox", mass=0.5, hero=(0, -1, 0), **OPERA)
def opera_lunchbox(b, rng, pal):
    W, D, H = 0.2, 0.09, 0.17
    b.box((W, D, H), mat="tin", bevel=0.008)
    b.plane(W * 0.92, H * 0.84, loc=(0, -D / 2 - 0.0006, -0.005), rot=(PI / 2, 0, 0), mat="art", cuts=3)
    b.plane(W * 0.92, H * 0.84, loc=(0, D / 2 + 0.0006, -0.005), rot=(PI / 2, 0, PI), mat="art2", cuts=3)
    for sx in (-1, 1):
        b.plane(D * 0.8, H * 0.84, loc=(sx * (W / 2 + 0.0006), 0, -0.005), rot=(PI / 2, 0, sx * PI / 2), mat="art2", cuts=2)
    b.box((W + 0.002, D + 0.002, 0.004), loc=(0, 0, H / 2 - 0.02), mat="rim")
    b.torus(0.032, 0.005, loc=(0, 0, H / 2 + 0.006), rot=(PI / 2, 0, 0), arc=PI, mat="handle", seg=14)
    b.box((0.012, 0.006, 0.02), loc=(0, -D / 2 - 0.003, H / 2 - 0.02), mat="rim", bevel=0.001)
    return {"tin": MET((0.85, 0.15, 0.1), 0.35), "art": PR(_t_space_scene(rng, "oplb"), 0.25, metal=0.3),
            "art2": PR(_t_space_scene(rng, "oplb2", 200, 180, title=False), 0.25, metal=0.3),
            "rim": MET((0.75, 0.75, 0.78), 0.3), "handle": P(BLACK, 0.4)}


@obj("opera_vhs", mass=0.7, **OPERA)
def opera_vhs(b, rng, pal):
    """The boxed trilogy: three tapes in a slipcase, 'digitally remastered', for the second time this decade."""
    W, Lz, T_ = 0.11, 0.2, 0.08
    t = 0.0015
    b.box((W, Lz, t), loc=(0, 0, T_ / 2), mat="case")
    b.box((W, Lz, t), loc=(0, 0, -T_ / 2), mat="case")
    b.box((W, t, T_), loc=(0, Lz / 2, 0), mat="case")
    b.box((W, t, T_), loc=(0, -Lz / 2, 0), mat="case")
    b.box((t, Lz, T_), loc=(-W / 2, 0, 0), mat="case")
    b.plane(W, Lz, loc=(0, 0, T_ / 2 + t), mat="front", cuts=3)
    for i in range(3):
        z = -T_ / 2 + 0.014 + i * 0.026
        out = 0.004 + 0.012 * (i == 1)
        b.box((0.103, 0.188, 0.024), loc=(out, 0, z), mat="tape", bevel=0.001)
        b.plane(0.18, 0.02, loc=(0.103 / 2 + out + 0.0005, 0, z), rot=(PI / 2, 0, PI / 2), mat=f"spine{i}", cuts=2)
    s = {"case": ("cardboard", {"color": (0.1, 0.1, 0.12)}), "front": PR(_t_vhs_front(rng, "opvhs"), 0.3, coat=0.4),
         "tape": P(BLACK, 0.35)}
    for i in range(3):
        s[f"spine{i}"] = PR(_t_vhs_spine(rng, f"opsp{i}", 4 + i), 0.4)
    return s


@obj("opera_cards", mass=0.02, **OPERA)
def opera_cards(b, rng, pal):
    s = {}
    n = int(rng.integers(3, 6))
    for i in range(n):
        rz = (i - n / 2) * 0.25 + float(rng.normal(0, 0.05))
        with _at(b, loc=(i * 0.012, i * 0.004, i * 0.0011), rot=(0, 0, rz)):
            b.box((0.064, 0.089, 0.0006), mat="stock")
            if i == 0 and rng.random() < 0.5:
                b.plane(0.064, 0.089, loc=(0, 0, 0.0004), mat="back", cuts=2)
            else:
                b.plane(0.064, 0.089, loc=(0, 0, 0.0004), mat=f"c{i}", cuts=2)
                s[f"c{i}"] = PR(_t_trading_card(rng, f"opc{i}", _pick(rng, KINDS), int(rng.integers(1, 67))), 0.4)
    s.update({"stock": ("paper", {"color": (0.85, 0.82, 0.76)}), "back": PR(_t_card_back(rng, "opcb"), 0.6)})
    return s


@obj("opera_stickers", mass=0.01, **OPERA)
def opera_stickers(b, rng, pal):
    b.plane(0.12, 0.09, rot=(0, 0, float(rng.normal(0, 0.1))), mat="sheet", cuts=4)
    return {"sheet": PR(_t_opera_stickers(rng, "opstk"), 0.25, coat=0.6)}


@obj("opera_mailaway", mass=0.05, **OPERA)
def opera_mailaway(b, rng, pal):
    """The mail-away mystery figure: white box, baggie, eleven weeks of checking the mailbox."""
    b.box((0.08, 0.06, 0.025), loc=(-0.02, 0, 0.0125), mat="box", bevel=0.001)
    b.plane(0.08, 0.06, loc=(-0.02, 0, 0.0256), mat="label", cuts=2)
    rings = []
    for i in range(7):
        u = i / 6
        x = 0.03 + 0.11 * u
        rings.append([(x, -0.03, 0.002), (x, 0, 0.0), (x, 0.03, 0.002), (x, 0, 0.022 * math.sin(PI * u) ** 0.4 + 0.003)])
    b.loft(rings, mat="bag")
    with _at(b, loc=(0.035, 0.0, 0.006), rot=(PI / 2, 0, -PI / 2), s=0.95):
        s = _fig(b, _pick(rng, ["marshal", "moth"]), rng=rng)
    s.update({"box": ("cardboard", {"color": (0.95, 0.95, 0.93)}), "label": PR(_t_mailer(rng, "opmail"), 0.5),
              "bag": _clear(rng)})
    return s


# ================================================================================================
# D) THE TOY AISLE (regular cubes)
# ================================================================================================

def _loud(rng, *cols):
    return P(_pick(rng, list(cols)), 0.35)


@obj("trip_it", eras=(1, 2), mass=0.25, weight=1.0)
def trip_it(b, rng, pal):
    """The ankle-hop toy: a hoop for your ankle, a long stem, a ball at the end and a lap counter."""
    b.torus(0.04, 0.007, mat="hoop", seg=28, rseg=8)
    b.tube([(0.04, 0, 0), (0.12, 0, 0.0), (0.2, 0, 0.0)], 0.0065, mat="stem", seg=10)
    b.sphere(0.035, loc=(0.23, 0, 0.0), mat="ball", seg=18)
    b.box((0.03, 0.022, 0.016), loc=(0.07, 0, 0.006), mat="counter", bevel=0.003)
    b.plane(0.022, 0.012, loc=(0.07, 0, 0.0142), mat="lcd", cuts=2)
    img = tex.lcd(rng, "tripl", text=str(int(rng.integers(12, 9999))).rjust(4, "0"))
    return {"hoop": _loud(rng, (0.55, 0.2, 0.85), (1.0, 0.2, 0.6), (0.1, 0.75, 0.8)),
            "stem": _loud(rng, (0.5, 1.0, 0.1), (1.0, 0.5, 0.0), (1.0, 0.95, 0.2)),
            "ball": _loud(rng, (1.0, 0.2, 0.6), (0.1, 0.75, 0.8), (0.5, 1.0, 0.1)), "counter": P((0.15, 0.15, 0.17), 0.4),
            "lcd": PR(img, 0.2)}


@obj("flop_it", eras=(2, 3), mass=0.45, weight=1.0)
def flop_it(b, rng, pal):
    """FLOP. TWIST. PULL. The arc-shaped command toy: bop cap in the middle, twist knob one end, pull handle the other."""
    R = 0.16
    pts = [(R * math.sin(a), R * (1 - math.cos(a)) - 0.03, 0) for a in np.linspace(-0.62, 0.62, 16)]
    b.tube(pts, lambda t: 0.024 - 0.004 * abs(t - 0.5), mat="body", seg=16)
    b.cyl(0.024, 0.016, loc=(0, -0.03, 0.022), mat="bop", seg=22)
    b.sphere(0.024, loc=(0, -0.03, 0.03), scale=(1, 1, 0.35), mat="bop", seg=18)
    x0, y0 = pts[0][0], pts[0][1]
    x1, y1 = pts[-1][0], pts[-1][1]
    b.cyl(0.02, 0.03, loc=(x0 - 0.012, y0 + 0.008, 0), rot=(0, PI / 2, -0.62), mat="twist", seg=10)
    for i in range(10):
        a = 2 * PI * i / 10
        b.box((0.03, 0.004, 0.004), loc=(x0 - 0.012, y0 + 0.008 + 0.02 * math.cos(a) * 0.6, 0.02 * math.sin(a)),
              rot=(a, 0, -0.62), mat="twist")
    b.tube([(x1, y1, 0), (x1 + 0.03, y1 + 0.02, 0)], 0.006, mat="pull", seg=8)
    b.cyl(0.008, 0.05, loc=(x1 + 0.036, y1 + 0.024, 0), rot=(PI / 2, 0, 0.62), mat="pull", seg=12)
    for i in range(6):
        b.cyl(0.0022, 0.002, loc=(0.06 + (i % 3) * 0.008, -0.012 + (i // 3) * 0.008, 0.022), mat="grill", seg=6)
    return {"body": P((0.5, 0.15, 0.75), 0.35), "bop": P((1.0, 0.85, 0.1), 0.3, coat=0.4),
            "twist": P((0.3, 0.85, 0.15), 0.4), "pull": P((0.3, 0.85, 0.15), 0.4), "grill": P(BLACK, 0.6)}


@obj("kush_ball", eras=(1, 2), mass=0.05, weight=1.0)
def kush_ball(b, rng, pal):
    """The rubber-filament ball: a thousand floppy strands, every one of them dusty."""
    n = 170
    ga = PI * (3 - math.sqrt(5))
    cols = 3 if rng.random() < 0.6 else 2
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - y * y)
        a = ga * i
        d = (r * math.cos(a), r * math.sin(a), y)
        L = 0.035 + float(rng.uniform(-0.004, 0.004))
        sag = 0.004
        pts = [(d[0] * 0.006, d[1] * 0.006, d[2] * 0.006), (d[0] * L * 0.6, d[1] * L * 0.6, d[2] * L * 0.6 - sag),
               (d[0] * L, d[1] * L, d[2] * L - sag * 2)]
        k = f"c{(i * 7 // 11) % cols}"
        b.tube(pts, 0.0009, mat=k, seg=4, cap=False)
        b.sphere(0.0017, loc=pts[-1], mat=k, seg=6)
    b.sphere(0.01, mat="c0", seg=10)
    palette = [(1.0, 0.2, 0.6), (0.1, 0.75, 0.8), (1.0, 0.85, 0.1), (0.5, 1.0, 0.1), (1.0, 0.45, 0.05), (0.55, 0.2, 0.85)]
    idx = rng.permutation(len(palette))
    return {f"c{i}": P(palette[idx[i]], 0.6) for i in range(3)}


@obj("moon_shooz", eras=(1, 2), mass=0.6, weight=1.0)
def moon_shooz(b, rng, pal):
    """Mini trampolines strapped to your feet: a plastic tub, a black mat on bungee cords, a sole and two straps."""
    for sx, rz in ((-1, 0.2), (1, -0.15)):
        with _at(b, loc=(sx * 0.062, 0, 0), rot=(0, 0, rz)):
            b.lathe([(0.0, -0.016), (0.04, -0.016), (0.052, 0.0), (0.052, 0.004), (0.047, 0.004), (0.036, -0.01),
                     (0.0, -0.01)], mat="rim", seg=28)
            b.cyl(0.033, 0.002, loc=(0, 0, -0.004), mat="mat", seg=24)
            for i in range(12):
                a = 2 * PI * i / 12
                b.tube([(0.049 * math.cos(a), 0.049 * math.sin(a), 0.004), (0.033 * math.cos(a + 0.26),
                        0.033 * math.sin(a + 0.26), -0.003)], 0.0022, mat="band", seg=5)
            sole = [(x * 0.9, y) for x, y in ellipse(0.075, 0.04, 24)]
            b.extrude(sole, 0.006, loc=(0, 0, 0.004), rot=(0, 0, PI / 2 + 0.2), mat="plate", bevel=0.0015)
            for dy in (-0.014, 0.016):
                pts = [(-0.024, 0, 0.007), (-0.02, 0, 0.022), (0.0, 0, 0.03), (0.02, 0, 0.022), (0.024, 0, 0.007)]
                with _at(b, loc=(0, dy, 0), rot=(0, 0, 0.2)):
                    b.tube(pts, 0.004, mat="strap", seg=6)
    rimc = _pick(rng, [(0.15, 0.4, 0.9), (1.0, 0.25, 0.6), (0.4, 0.85, 0.2), (0.55, 0.2, 0.85)])
    return {"rim": P(rimc, 0.35), "mat": P(BLACK, 0.7), "band": P((0.08, 0.08, 0.08), 0.6),
            "plate": P(_pick(rng, [(1.0, 0.85, 0.1), (0.9, 0.9, 0.9), (0.1, 0.75, 0.8)]), 0.35),
            "strap": _fab(_pick(rng, [(0.1, 0.1, 0.12), (1.0, 0.85, 0.1)]))}


@obj("blow_up_gloves", eras=(1, 2), mass=0.15, weight=1.0)
def blow_up_gloves(b, rng, pal):
    """Inflatable boxing gloves. Every punch made the same squeak."""
    col = _pick(rng, [(0.9, 0.08, 0.08), (0.9, 0.08, 0.08), (0.1, 0.35, 0.9)])
    for sx in (-1, 1):
        with _at(b, loc=(sx * 0.06, 0, 0), rot=(0, 0, sx * 0.2)):
            b.sphere(0.045, loc=(0, 0.03, 0.0), scale=(1.0, 1.3, 0.85), mat="vinyl", seg=22)
            b.tube([(sx * -0.03, -0.01, 0.004), (sx * -0.046, 0.016, 0.012), (sx * -0.04, 0.045, 0.018),
                    (sx * -0.024, 0.06, 0.02)], lambda t: 0.016 - 0.005 * t, mat="vinyl", seg=12)         # thumb
            b.cyl(0.031, 0.036, loc=(0, -0.03, -0.002), rot=(PI / 2, 0, 0), mat="vinyl", seg=20, r2=0.034)
            b.box((0.07, 0.016, 0.01), loc=(0, -0.03, 0.03), mat="cuff", bevel=0.003)                   # wrist strap
            b.torus(0.033, 0.0025, loc=(0, -0.047, -0.002), rot=(PI / 2, 0, 0), mat="cuff", seg=22, rseg=5)
            b.cyl(0.004, 0.008, loc=(sx * 0.024, -0.02, 0.03), mat="valve", seg=8)
            b.plane(0.045, 0.026, loc=(0, 0.035, 0.0385), rot=(-0.1, 0, 0), mat="star", cuts=2)
    star = _t_label(rng, "bgl", "CHAMP!", "INFLATE ME", bg=(1, 1, 1), ink=col, w=120, h=70)
    return {"vinyl": P(col, 0.12, coat=1.0), "cuff": P((0.95, 0.95, 0.95), 0.15, coat=1.0),
            "valve": P((0.9, 0.9, 0.9), 0.3), "star": PR(star, 0.15)}


@obj("soggy_blaster", eras=(1, 2), mass=0.6, weight=1.0, hero=(0, -1, 0))
def soggy_blaster(b, rng, pal):
    """The neon pump water blaster: tank on top, pump slide underneath, an orange nozzle, a lawsuit-level range."""
    b.box((0.2, 0.03, 0.035), loc=(0, 0, 0), mat="body", bevel=0.01)
    b.cyl(0.009, 0.06, loc=(0.125, 0, 0.004), rot=(0, PI / 2, 0), mat="nozzle", seg=14)
    b.cyl(0.004, 0.006, loc=(0.158, 0, 0.004), rot=(0, PI / 2, 0), mat="tip", seg=10)
    b.box((0.04, 0.026, 0.07), loc=(-0.06, 0, -0.045), rot=(0, -0.35, 0), mat="body", bevel=0.008)
    b.box((0.008, 0.01, 0.02), loc=(-0.025, 0, -0.025), mat="tip", bevel=0.002)
    b.tube([(-0.015, 0, -0.018), (-0.02, 0, -0.045), (-0.045, 0, -0.05)], 0.003, mat="body", seg=6)
    b.lathe([(0.0, 0.0), (0.024, 0.0), (0.026, 0.01), (0.026, 0.06), (0.018, 0.072), (0.008, 0.075), (0.008, 0.082),
             (0.0, 0.082)], loc=(-0.03, 0, 0.02), rot=(0, -PI / 2 + 0.15, 0), mat="tank", seg=20)
    b.cyl(0.011, 0.012, loc=(-0.112, 0, 0.034), rot=(0, PI / 2, 0), mat="tip", seg=12)
    b.box((0.09, 0.024, 0.02), loc=(0.07, 0, -0.025), mat="pump", bevel=0.006)
    for i in range(5):
        b.box((0.004, 0.026, 0.02), loc=(0.04 + i * 0.012, 0, -0.026), mat="pump")
    b.plane(0.08, 0.022, loc=(0.0, -0.0155, 0.004), rot=(PI / 2, 0, 0), mat="decal", cuts=2)
    body = _pick(rng, [(0.5, 1.0, 0.1), (0.1, 0.75, 0.8), (1.0, 0.85, 0.1)])
    return {"body": P(body, 0.3), "nozzle": P((1.0, 0.5, 0.0), 0.3), "tip": P((1.0, 0.5, 0.0), 0.35),
            "tank": T(_pick(rng, [(1.0, 0.5, 0.05), (0.2, 0.6, 1.0), (0.95, 0.3, 0.6)]), 0.1),
            "pump": P((0.55, 0.2, 0.85), 0.35),
            "decal": PR(_t_label(rng, "soggy", "SOGGY 50", "PRESSURIZED!", bg=(1.0, 0.5, 0.0), ink=(1, 1, 1)), 0.3)}


@obj("nerd_blaster", eras=(1, 2, 3), mass=0.35, weight=1.0, hero=(0, -1, 0))
def nerd_blaster(b, rng, pal):
    """The orange-and-blue foam dart blaster and the darts that ended up on the roof."""
    b.box((0.14, 0.03, 0.04), loc=(0, 0, 0), mat="body", bevel=0.008)
    b.cyl(0.011, 0.04, loc=(0.085, 0, 0.004), rot=(0, PI / 2, 0), mat="slide", seg=14)
    b.cyl(0.007, 0.004, loc=(0.106, 0, 0.004), rot=(0, PI / 2, 0), mat="dark", seg=12)
    b.box((0.05, 0.034, 0.024), loc=(-0.01, 0, 0.026), mat="slide", bevel=0.005)
    for i in range(4):
        b.box((0.004, 0.036, 0.024), loc=(-0.03 + i * 0.012, 0, 0.026), mat="dark")
    b.box((0.034, 0.024, 0.07), loc=(-0.045, 0, -0.045), rot=(0, -0.3, 0), mat="grip", bevel=0.007)
    b.box((0.008, 0.01, 0.018), loc=(-0.012, 0, -0.03), mat="trigger", bevel=0.002)
    b.tube([(0.0, 0, -0.02), (0.002, 0, -0.045), (-0.025, 0, -0.05)], 0.003, mat="grip", seg=6)
    b.plane(0.05, 0.018, loc=(0.02, -0.0155, -0.006), rot=(PI / 2, 0, 0), mat="decal", cuts=2)
    for i in range(int(rng.integers(2, 5))):
        x, z = float(rng.uniform(0.0, 0.1)), -0.03 - i * 0.014                 # darts lying under the barrel
        ry = float(rng.normal(0, 0.15))
        y = float(rng.normal(0, 0.006))
        b.cyl(0.0065, 0.06, loc=(x, y, z), rot=(0, PI / 2 + ry, 0), mat="dart", seg=12)
        b.cyl(0.0068, 0.008, loc=(x + 0.033 * math.cos(ry), y, z - 0.033 * math.sin(ry)), rot=(0, PI / 2 + ry, 0),
              mat="tipd", seg=12)
    return {"body": P((1.0, 0.5, 0.05), 0.35), "slide": P((0.15, 0.4, 0.9), 0.35), "dark": P((0.1, 0.1, 0.1), 0.5),
            "grip": P((1.0, 0.5, 0.05), 0.4), "trigger": P((1.0, 0.85, 0.1), 0.35),
            "dart": ("foam", {"color": _pick(rng, [(0.15, 0.4, 0.9), (0.4, 0.85, 0.2)])}),
            "tipd": P((1.0, 0.5, 0.05), 0.5),
            "decal": PR(_t_label(rng, "nerd", "NERD", "FOAM POWER", bg=(0.15, 0.4, 0.9), ink=(1.0, 0.85, 0.1)), 0.3)}


def _muscle(b, k="", stretch=0.0, tights=False):
    """A beefcake figure standing (z up), facing -Y. stretch pulls the right arm out like taffy."""
    S, TR, H = "skin" + k, "trunks" + k, "hair" + k
    for sx in (-1, 1):
        b.tube([(sx * 0.012, 0, 0.0), (sx * 0.013, 0, 0.03), (sx * 0.012, 0, 0.06)], lambda t: 0.009 - 0.002 * t + 0.003 * t,
               mat=TR if tights else S, seg=10)
        b.sphere(0.009, loc=(sx * 0.012, -0.004, -0.002), scale=(1, 1.6, 0.6), mat="boot" + k, seg=10)
    b.sphere(0.022, loc=(0, 0, 0.072), scale=(1.0, 0.75, 0.6), mat=TR, seg=14)
    b.sphere(0.03, loc=(0, 0, 0.105), scale=(1.15, 0.7, 0.9), mat=S, seg=16)
    for sx in (-1, 1):
        b.sphere(0.014, loc=(sx * 0.012, -0.016, 0.112), scale=(1.2, 0.6, 0.9), mat=S, seg=10)   # pecs
        b.sphere(0.014, loc=(sx * 0.033, 0, 0.127), mat=S, seg=12)                                 # delts
    b.cyl(0.008, 0.012, loc=(0, 0, 0.135), mat=S, seg=10)
    b.sphere(0.013, loc=(0, -0.002, 0.15), scale=(0.9, 1.0, 1.1), mat=S, seg=14)
    b.sphere(0.0135, loc=(0, 0.003, 0.156), scale=(0.95, 1.0, 0.8), mat=H, seg=12)
    # left arm flexed
    b.tube([(-0.038, 0, 0.125), (-0.06, 0, 0.12), (-0.064, -0.004, 0.145)], lambda t: 0.009 + 0.003 * math.sin(PI * t),
           mat=S, seg=10)
    b.sphere(0.008, loc=(-0.064, -0.004, 0.153), mat=S, seg=10)
    # right arm: normal or stretched out to arm's length and then some
    L = 0.05 + stretch
    b.tube([(0.038, 0, 0.125), (0.038 + L * 0.5, -0.003, 0.12 - stretch * 0.1), (0.038 + L, 0.0, 0.11 - stretch * 0.25)],
           lambda t: 0.009 - 0.004 * math.sin(PI * t) * (stretch > 0.01), mat=S, seg=10)
    b.sphere(0.009, loc=(0.038 + L + 0.006, 0, 0.11 - stretch * 0.25), mat=S, seg=10)


@obj("stretch_man", eras=(0, 1), mass=0.5, weight=1.0, hero=(0, -1, 0))
def stretch_man(b, rng, pal):
    """The gel-filled muscle man: one arm pulled to twice its length, slowly not coming back."""
    _muscle(b, stretch=float(rng.uniform(0.07, 0.12)))
    return {"skin": ("plastic", {"color": (0.95, 0.72, 0.5), "rough": 0.5, "texture": 0.4}),
            "trunks": P(_pick(rng, [(0.1, 0.3, 0.85), (0.85, 0.1, 0.1)]), 0.45), "hair": P((0.95, 0.8, 0.3), 0.5),
            "boot": P((0.95, 0.72, 0.5), 0.5)}


@obj("wrestler_fig", eras=(1, 2), mass=0.15, weight=1.0, hero=(0, -1, 0))
def wrestler_fig(b, rng, pal):
    """A rubbery wrestling figure in neon tights with a gold title belt the size of his torso."""
    _muscle(b, tights=True)
    b.cyl(0.025, 0.012, loc=(0, 0, 0.088), mat="belt", seg=20)
    b.cyl(0.012, 0.004, loc=(0, -0.026, 0.088), rot=(PI / 2, 0, 0), mat="plate", seg=16)
    b.box((0.03, 0.004, 0.005), loc=(0, -0.012, 0.162), mat="band")
    b.tube([(0, 0.01, 0.155), (0, 0.02, 0.135), (0.004, 0.022, 0.118)], 0.005, mat="hair", seg=6)   # the mullet
    tights = _pick(rng, [(1.0, 0.2, 0.6), (0.5, 1.0, 0.1), (0.1, 0.75, 0.8), (1.0, 0.85, 0.1), (0.55, 0.2, 0.85)])
    return {"skin": P(_pick(rng, SKIN), 0.45), "trunks": P(tights, 0.3), "hair": P(_pick(rng, [(0.95, 0.8, 0.3),
            (0.1, 0.08, 0.06), (0.45, 0.25, 0.1)]), 0.5), "boot": P((0.95, 0.95, 0.95), 0.4),
            "belt": P((0.08, 0.08, 0.08), 0.4), "plate": ("gold", {"rough": 0.25}), "band": P(tights, 0.4)}


def _car(b, L, k="", rng=None):
    b.box((L, L * 0.45, L * 0.2), loc=(0, 0, L * 0.16), mat="paint" + k, bevel=L * 0.06)
    b.box((L * 0.5, L * 0.4, L * 0.16), loc=(-L * 0.06, 0, L * 0.33), mat="paint" + k, bevel=L * 0.06)
    b.box((L * 0.52, L * 0.41, L * 0.1), loc=(-L * 0.06, 0, L * 0.34), mat="glass" + k, bevel=L * 0.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(L * 0.12, L * 0.06, loc=(sx * L * 0.32, sy * L * 0.23, L * 0.1), rot=(PI / 2, 0, 0), mat="tire" + k, seg=12)


@obj("micro_cars", eras=(0, 1), mass=0.03, weight=1.0)
def micro_cars(b, rng, pal):
    """A fistful of tiny cars, the kind you lost in the carpet by the dozen."""
    s = {}
    for i in range(int(rng.integers(4, 7))):
        x, y = (float(v) for v in rng.normal(0, 0.018, 2))
        with _at(b, loc=(x, y, 0.0), rot=(0, 0, float(rng.uniform(0, 2 * PI)))):
            _car(b, float(rng.uniform(0.022, 0.03)), k=str(i))
        s.update({f"paint{i}": P(_pick(rng, [(0.9, 0.1, 0.1), (0.1, 0.35, 0.9), (1.0, 0.85, 0.1), (0.1, 0.6, 0.3),
                                              (0.95, 0.95, 0.95), (0.1, 0.1, 0.1), (0.8, 0.8, 0.82)]), 0.25, coat=0.8),
                  f"glass{i}": P((0.15, 0.2, 0.3), 0.1, coat=1.0), f"tire{i}": P(BLACK, 0.6)})
    return s


@obj("loop_track", eras=(0, 1, 2), mass=0.2, weight=1.0, hero=(0, -1, 0))
def loop_track(b, rng, pal):
    """Orange plastic race track with the loop-de-loop, the blue connector tabs and one car that never made it."""
    w, h, t = 0.034, 0.006, 0.0015
    prof = [(-w / 2, h), (-w / 2, 0), (w / 2, 0), (w / 2, h), (w / 2 - t, h), (w / 2 - t, t), (-w / 2 + t, t),
            (-w / 2 + t, h)]
    R, drift = 0.06, 0.04
    path = [(-0.17 + 0.17 * i / 6, 0.0, 0.0) for i in range(6)]
    for a in np.linspace(-PI / 2, 3 * PI / 2, 40):
        path.append((R * math.cos(a), drift * (a + PI / 2) / (2 * PI), R + R * math.sin(a)))
    path += [(0.17 * i / 6, drift, 0.0) for i in range(1, 7)]
    rings = []
    for i, p in enumerate(path):
        q0, q1 = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tv = np.array(q1) - np.array(q0)
        tv /= np.linalg.norm(tv) + 1e-9
        side = np.array((0.0, 1.0, 0.0))
        nv = np.cross(tv, side)
        rings.append([tuple(np.array(p) + side * u + nv * v) for u, v in prof])
    b.loft(rings, mat="track")
    for x in (-0.17, 0.17):
        b.box((0.01, 0.012, 0.002), loc=(x - 0.004 * np.sign(x), drift if x > 0 else 0.0, 0.0015), mat="tab")
    with _at(b, loc=(0.1, drift, 0.002)):
        _car(b, 0.03, k="c")
    return {"track": P((1.0, 0.45, 0.02), 0.3, coat=0.3), "tab": P((0.15, 0.35, 0.9), 0.4),
            "paintc": P(_pick(rng, [(0.85, 0.1, 0.5), (0.1, 0.6, 0.9), (0.95, 0.85, 0.1)]), 0.25, coat=0.8),
            "glassc": P((0.15, 0.2, 0.3), 0.1, coat=1.0), "tirec": P(BLACK, 0.6)}


@obj("robo_car", eras=(0, 1, 2), mass=0.25, weight=1.0, hero=(0, -1, 0))
def robo_car(b, rng, pal):
    """The robot-that-is-also-a-car: hood for a chest, wheels on the shins, a spoiler for wings. Ours, not theirs."""
    for sx in (-1, 1):
        b.box((0.016, 0.018, 0.05), loc=(sx * 0.014, 0, 0.025), mat="limb", bevel=0.002)
        b.box((0.02, 0.026, 0.008), loc=(sx * 0.014, -0.004, 0.004), mat="limb", bevel=0.002)
        b.cyl(0.011, 0.008, loc=(sx * 0.025, 0.002, 0.028), rot=(0, PI / 2, 0), mat="tire", seg=14)
        b.cyl(0.005, 0.009, loc=(sx * 0.025, 0.002, 0.028), rot=(0, PI / 2, 0), mat="chrome", seg=10)
    b.box((0.04, 0.02, 0.012), loc=(0, 0, 0.056), mat="limb", bevel=0.002)
    b.box((0.056, 0.03, 0.04), loc=(0, 0, 0.083), mat="paint", bevel=0.004)
    b.box((0.05, 0.004, 0.018), loc=(0, -0.016, 0.092), rot=(-0.25, 0, 0), mat="glass", bevel=0.001)   # windshield chest
    for sx in (-1, 1):
        b.box((0.012, 0.004, 0.006), loc=(sx * 0.018, -0.016, 0.071), mat="light", bevel=0.001)
        b.cyl(0.012, 0.008, loc=(sx * 0.036, 0, 0.1), rot=(0, PI / 2, 0), mat="tire", seg=14)
        b.box((0.012, 0.014, 0.042), loc=(sx * 0.038, -0.002, 0.075), mat="paint", bevel=0.002)
        b.box((0.012, 0.012, 0.01), loc=(sx * 0.038, -0.004, 0.051), mat="limb", bevel=0.002)
    b.box((0.08, 0.012, 0.004), loc=(0, 0.02, 0.108), mat="paint", bevel=0.001)                    # spoiler wings
    for sx in (-1, 1):
        b.box((0.004, 0.006, 0.014), loc=(sx * 0.03, 0.017, 0.1), mat="limb")
    b.box((0.018, 0.018, 0.02), loc=(0, 0, 0.114), mat="limb", bevel=0.003)
    b.box((0.016, 0.004, 0.006), loc=(0, -0.009, 0.116), mat="visor", bevel=0.001)
    b.box((0.003, 0.003, 0.012), loc=(0.007, 0, 0.13), mat="chrome")
    paint = _pick(rng, [(0.95, 0.85, 0.1), (0.9, 0.12, 0.1), (0.15, 0.35, 0.9), (0.1, 0.1, 0.1)])
    b.plane(0.012, 0.012, loc=(0, -0.0152, 0.077), rot=(PI / 2, 0, 0), mat="badge", cuts=2)
    bc = tex.Canvas(64, 64, (0.75, 0.1, 0.1, 1))
    bc.poly([(0.55, 0.95), (0.25, 0.45), (0.5, 0.45), (0.4, 0.05), (0.78, 0.6), (0.52, 0.6)], (1.0, 0.85, 0.2))
    return {"paint": P(paint, 0.25, coat=0.7), "limb": P(_pick(rng, [(0.6, 0.6, 0.63), (0.15, 0.15, 0.17)]), 0.4),
            "tire": P(BLACK, 0.6), "chrome": CHROME(), "glass": P((0.3, 0.55, 0.85), 0.05, coat=1.0),
            "light": P((1.0, 0.95, 0.7), 0.2, glow=0.5), "visor": P((0.2, 0.8, 1.0), 0.1, glow=0.8),
            "badge": PR(bc.image("robobadge"), 0.3)}


def _clam(b, R, H, open_angle, lid_inner, k=""):
    """A palm-size compact playset: base dish + hinged lid, opened."""
    pts = rounded_rect(R * 2, R * 2, R * 0.6, 6)
    b.extrude(pts, H, loc=(0, 0, H / 2), mat="shell" + k, bevel=0.002)
    b.extrude(pts, 0.002, loc=(0, 0, H + 0.0005), scale=(0.9, 0.9, 1), mat="floor" + k)
    with _at(b, loc=(0, R, H), rot=(-open_angle, 0, 0)):
        b.extrude(pts, H * 0.8, loc=(0, -R, H * 0.4), mat="shell" + k, bevel=0.002)
        b.plane(R * 1.7, R * 1.7, loc=(0, -R, -0.0008), rot=(PI, 0, PI), mat=lid_inner, cuts=2)
    b.cyl(0.003, R * 0.6, loc=(0, R, H), rot=(0, PI / 2, 0), mat="shell" + k, seg=10)


@obj("pocket_playset", eras=(1, 2), mass=0.08, weight=1.0, hero=(0, -0.7, 0.7))
def pocket_playset(b, rng, pal):
    """The pink pocket compact that opened into a tiny house, with a peg doll you lost within the hour."""
    R, H = 0.04, 0.016
    _clam(b, R, H, 1.9, "wall")
    b.box((0.024, 0.016, 0.006), loc=(-0.015, -0.012, H + 0.004), mat="bed", bevel=0.002)
    b.box((0.022, 0.014, 0.003), loc=(-0.015, -0.012, H + 0.008), mat="sheet", bevel=0.001)
    for i in range(4):
        b.box((0.012, 0.005, 0.004 * (i + 1)), loc=(0.02, -0.012 + i * 0.005, H + 0.002 * (i + 1)), mat="stairs")
    b.cyl(0.004, 0.012, loc=(0.008, 0.012, H + 0.007), mat="dress", seg=10, r2=0.0025)
    b.sphere(0.0035, loc=(0.008, 0.012, H + 0.016), mat="head", seg=10)
    b.sphere(0.0038, loc=(0.008, 0.0125, H + 0.0175), scale=(1, 1, 0.7), mat="hair", seg=10)
    c = tex.Canvas(96, 96, (0.7, 0.9, 1.0, 1))
    for i in range(6):
        c.rect(0, i / 6, 1, i / 6 + 0.06, (1.0, 0.85, 0.9))
    c.rect(0.2, 0.2, 0.45, 0.55, (1, 1, 1))
    c.rect(0.23, 0.23, 0.42, 0.52, (0.5, 0.75, 1.0))
    c.rect(0.6, 0.0, 0.85, 0.5, (0.95, 0.5, 0.75))
    c.circle(0.8, 0.8, 0.08, (1.0, 0.85, 0.2))
    c.text_fit("MOLLY POCKET", 0.08, 0.96, 0.84, 0.1, (0.85, 0.2, 0.55), bold=True)
    return {"shell": P(_pick(rng, [(1.0, 0.45, 0.7), (0.95, 0.6, 0.8), (0.85, 0.35, 0.65)]), 0.3, coat=0.5),
            "floor": P((0.6, 0.9, 0.75), 0.4), "wall": PR(c.image("pockw"), 0.4), "bed": P((1.0, 0.95, 0.6), 0.4),
            "sheet": P((0.55, 0.75, 1.0), 0.4), "stairs": P((0.95, 0.95, 0.95), 0.4),
            "dress": P((0.6, 0.3, 0.85), 0.4), "head": P((0.98, 0.83, 0.7), 0.4), "hair": P((0.96, 0.82, 0.32), 0.4)}


@obj("monster_playset", eras=(1,), mass=0.12, weight=1.0, hero=(0, -1, 0.3))
def monster_playset(b, rng, pal):
    """The black-and-green horned-beast clamshell: the whole head opened into a doom fortress for one tiny guy."""
    b.sphere(0.05, loc=(0, 0, 0.0), scale=(1.0, 0.95, 0.85), mat="shell", seg=20)
    b.torus(0.05, 0.0025, loc=(0, 0, -0.003), mat="seam", seg=28, rseg=4)
    for sx in (-1, 1):
        b.sphere(0.012, loc=(sx * 0.02, -0.04, 0.012), scale=(1.2, 0.6, 0.8), mat="eye", seg=12)
        b.tube([(sx * 0.03, -0.005, 0.03), (sx * 0.05, 0.0, 0.055), (sx * 0.045, 0.01, 0.075)],
               lambda t: 0.009 * (1 - t) + 0.001, mat="horn", seg=8)
    b.sphere(0.03, loc=(0, -0.034, -0.015), scale=(1.1, 0.6, 0.45), mat="jaw", seg=14)
    for i in range(-3, 4):
        b.lathe([(0.003, 0), (0.0, 0.009)], loc=(i * 0.008, -0.05, -0.008), rot=(PI, 0, 0), mat="teeth", seg=6)
    for i in range(5):
        x = float(rng.uniform(-0.035, 0.035))
        b.tube([(x, -0.02, 0.04), (x, -0.04, 0.03), (x * 1.1, -0.047, 0.012 - i * 0.002)],
               lambda t: 0.003 * (1 - t) + 0.0012, mat="slime", seg=6)
    with _at(b, loc=(0.065, -0.03, -0.042), s=0.25):
        _muscle(b, k="m", tights=True)
    return {"shell": P((0.06, 0.06, 0.07), 0.3, coat=0.5), "seam": P((0.3, 0.9, 0.1), 0.3),
            "eye": P((0.4, 1.0, 0.1), 0.2, glow=1.0), "horn": P((0.15, 0.15, 0.16), 0.35),
            "jaw": P((0.12, 0.12, 0.13), 0.35), "teeth": P((0.95, 0.95, 0.85), 0.35), "slime": ("slime", {"color": (0.3, 0.95, 0.1)}),
            "skinm": P((0.98, 0.83, 0.7), 0.45), "trunksm": P((0.9, 0.15, 0.1), 0.4), "hairm": P((0.96, 0.82, 0.32), 0.5),
            "bootm": P((0.1, 0.1, 0.1), 0.4)}


@obj("bug_oven", eras=(0, 1, 2), mass=0.5, weight=1.0)
def bug_oven(b, rng, pal):
    """The bug-maker: a hot little oven, a metal mold full of bug-shaped dents, goop, and rubber bugs."""
    b.box((0.09, 0.09, 0.04), loc=(-0.045, 0, 0.02), mat="oven", bevel=0.005)
    b.box((0.07, 0.07, 0.004), loc=(-0.045, 0, 0.041), mat="plate")
    b.plane(0.06, 0.016, loc=(-0.045, -0.0455, 0.022), rot=(PI / 2, 0, 0), mat="label", cuts=2)
    b.cyl(0.006, 0.008, loc=(-0.075, -0.048, 0.03), rot=(PI / 2, 0, 0), mat="knob", seg=10)
    with _at(b, loc=(0.045, -0.01, 0.003), rot=(0, 0, 0.15)):
        b.box((0.07, 0.05, 0.006), mat="mold", bevel=0.001)
        b.box((0.03, 0.008, 0.004), loc=(0.05, 0, 0), mat="handle", bevel=0.001)
        for i, (bx, by) in enumerate(((-0.018, 0.0), (0.0, 0.012), (0.018, -0.004))):
            b.sphere(0.008, loc=(bx, by, 0.0031), scale=(1.5, 0.8, 0.15), mat=f"bug{i % 2}", seg=10)
            for sx in (-1, 1):
                for j in (-1, 0, 1):
                    b.box((0.0012, 0.008, 0.0005), loc=(bx + j * 0.005, by + sx * 0.008, 0.0032), rot=(0, 0, sx * j * 0.4),
                          mat=f"bug{i % 2}")
    b.lathe([(0.0, 0.0), (0.012, 0.0), (0.012, 0.045), (0.006, 0.055), (0.002, 0.065), (0.0, 0.065)],
            loc=(0.05, 0.045, 0.012), rot=(PI / 2, 0, 0.4), mat="bottle", seg=16)
    for i in range(3):
        x, y = float(rng.uniform(-0.09, 0.08)), float(rng.uniform(-0.07, -0.05))
        b.sphere(0.009, loc=(x, y, 0.003), rot=(0, 0, float(rng.uniform(0, 3))), scale=(1.5, 0.7, 0.35), mat=f"bug{i % 2}",
                 seg=10)
    return {"oven": P((0.2, 0.2, 0.22), 0.4), "plate": MET((0.6, 0.6, 0.62), 0.35), "knob": P((0.95, 0.85, 0.1), 0.4),
            "label": PR(_t_label(rng, "bugov", "CREEPY CRAWLSPACE", "THING-A-BAKER", bg=(0.4, 0.9, 0.1),
                                 ink=(0.1, 0.1, 0.1)), 0.4),
            "mold": MET((0.75, 0.75, 0.78), 0.3), "handle": P(BLACK, 0.5),
            "bug0": ("slime", {"color": (0.3, 0.95, 0.2)}), "bug1": ("slime", {"color": (0.6, 0.2, 0.9)}),
            "bottle": P(_pick(rng, [(0.95, 0.4, 0.1), (0.4, 0.9, 0.1), (0.6, 0.2, 0.9)]), 0.3)}


@obj("toy_oven", eras=(1, 2), mass=0.8, weight=1.0, hero=(0, -1, 0))
def toy_oven(b, rng, pal):
    """The light-bulb oven: purple and pink, two fake burners, one real burn."""
    W, D, H = 0.16, 0.11, 0.1
    body = _pick(rng, [(0.6, 0.3, 0.85), (1.0, 0.5, 0.75), (0.85, 0.35, 0.7)])
    b.box((W, D, H), mat="body", bevel=0.01)
    b.plane(W * 0.92, H * 0.8, loc=(0, -D / 2 - 0.0006, -0.002), rot=(PI / 2, 0, 0), mat="front", cuts=3)
    for sx in (-1, 1):
        b.cyl(0.022, 0.004, loc=(sx * 0.04, 0.0, H / 2 + 0.002), mat="burner", seg=20)
        b.torus(0.014, 0.0015, loc=(sx * 0.04, 0.0, H / 2 + 0.0045), mat="coil", seg=18, rseg=4)
    b.box((W * 0.9, 0.02, 0.03), loc=(0, D / 2 - 0.01, H / 2 + 0.015), mat="trim", bevel=0.004)
    for i in range(3):
        b.cyl(0.006, 0.008, loc=(-0.04 + i * 0.04, D / 2 - 0.022, H / 2 + 0.02), rot=(PI / 2, 0, 0), mat="knob", seg=10)
    b.box((0.05, 0.004, 0.006), loc=(-0.025, -D / 2 - 0.003, -0.032), mat="trim", bevel=0.001)
    b.box((0.06, 0.04, 0.008), loc=(0.11, -0.03, -H / 2 + 0.004), mat="pan", bevel=0.002)
    return {"body": P(body, 0.3, coat=0.4), "front": PR(_t_oven_front(rng, "toyov", body), 0.3),
            "burner": P((0.15, 0.15, 0.17), 0.5), "coil": P((1.0, 0.35, 0.1), 0.4),
            "trim": P(_pick(rng, [(1.0, 0.8, 0.95), (0.95, 0.95, 0.95), (0.4, 0.95, 0.85)]), 0.35),
            "knob": P((1.0, 0.85, 0.2), 0.35), "pan": MET((0.7, 0.7, 0.72), 0.3)}


@obj("tickle_monster", eras=(2,), mass=0.5, weight=1.0, hero=(0, -1, 0))
def tickle_monster(b, rng, pal):
    """Red plush cyclops with a laugh box in its gut. Squeeze, it giggles. Squeeze at 2am, it giggles anyway."""
    b.sphere(0.055, loc=(0, 0, 0.05), scale=(1.0, 0.85, 1.1), mat="fur", seg=20)
    b.sphere(0.03, loc=(0, -0.04, 0.035), scale=(1.0, 0.4, 1.1), mat="belly", seg=14)
    b.sphere(0.022, loc=(0, -0.042, 0.085), scale=(1.0, 0.6, 1.0), mat="eye", seg=16)
    b.sphere(0.009, loc=(0.003, -0.054, 0.083), scale=(1, 0.5, 1), mat="pupil", seg=10)
    b.sphere(0.024, loc=(0, -0.042, 0.05), scale=(1.2, 0.35, 0.5), mat="mouth", seg=14)
    b.sphere(0.012, loc=(0, -0.048, 0.045), scale=(1.1, 0.4, 0.5), mat="tongue", seg=10)
    for sx in (-1, 1):
        b.lathe([(0.008, 0), (0.006, 0.012), (0.0, 0.022)], loc=(sx * 0.025, -0.01, 0.105), rot=(0, sx * 0.4, 0),
                mat="horn", seg=10)
        b.tube([(sx * 0.05, 0, 0.06), (sx * 0.075, -0.015, 0.04), (sx * 0.08, -0.03, 0.025)], 0.011, mat="fur", seg=10)
        b.sphere(0.017, loc=(sx * 0.024, -0.02, 0.0), scale=(1.0, 1.6, 0.6), mat="fur", seg=12)
    b.plane(0.026, 0.018, loc=(0.085, -0.033, 0.02), rot=(PI / 2, 0, 0.3), mat="tag", cuts=2)
    b.box((0.03, 0.012, 0.03), loc=(0.0, 0.048, 0.03), mat="box", bevel=0.003)
    for i in range(3):
        b.box((0.016, 0.002, 0.002), loc=(0.0, 0.055, 0.022 + i * 0.006), mat="grill")
    tag = _t_label(rng, "tickle", "TICKLE ME", "TRY ME!", bg=(1.0, 0.85, 0.1), ink=(0.85, 0.1, 0.1), w=120, h=80)
    return {"fur": _fab((0.85, 0.06, 0.08)), "belly": _fab((0.6, 0.25, 0.75)), "eye": P(WHITE, 0.15, coat=0.9),
            "pupil": P(BLACK, 0.05, coat=1.0), "mouth": P((0.15, 0.02, 0.04), 0.6), "tongue": _fab((0.25, 0.55, 1.0)),
            "horn": _fab((1.0, 0.85, 0.2)), "tag": PR(tag, 0.4), "box": P((0.95, 0.95, 0.95), 0.4),
            "grill": P(BLACK, 0.6)}


@obj("stereo_viewer", eras=(0, 1, 2), mass=0.2, weight=1.0, hero=(0, -0.5, 0.85))
def stereo_viewer(b, rng, pal):
    """The red stereo picture viewer and a reel of 3D photos of somewhere you never went."""
    b.box((0.1, 0.06, 0.07), loc=(0, 0, 0.0), mat="body", bevel=0.014, seg=3)
    b.box((0.11, 0.04, 0.05), loc=(0, -0.03, -0.004), mat="body", bevel=0.012, seg=3)
    for sx in (-1, 1):
        b.cyl(0.012, 0.012, loc=(sx * 0.022, -0.054, 0.0), rot=(PI / 2, 0, 0), mat="body", seg=16)
        b.cyl(0.009, 0.002, loc=(sx * 0.022, -0.06, 0.0), rot=(PI / 2, 0, 0), mat="lens", seg=16)
    b.box((0.012, 0.012, 0.04), loc=(0.058, 0.0, 0.0), rot=(0, 0.3, 0), mat="lever", bevel=0.003)
    b.box((0.06, 0.01, 0.004), loc=(0, 0.034, 0.03), mat="dark")
    with _at(b, loc=(0, 0.02, 0.025), rot=(PI / 2 - 0.15, 0, 0)):
        b.cyl(0.044, 0.0012, mat="reel", seg=28)
        b.plane(0.088, 0.088, loc=(0, 0, -0.0007), rot=(PI, 0, 0), mat="reelp", cuts=2)
        b.plane(0.088, 0.088, loc=(0, 0, 0.0007), mat="reelp", cuts=2)
    with _at(b, loc=(0.09, 0.03, -0.034)):
        b.cyl(0.044, 0.0012, mat="reel", seg=28)
        b.plane(0.088, 0.088, loc=(0, 0, 0.0007), mat="reelp2", cuts=2)
    return {"body": P((0.82, 0.08, 0.08), 0.3, coat=0.5), "lens": P((0.1, 0.1, 0.12), 0.05, coat=1.0),
            "lever": P((0.82, 0.08, 0.08), 0.3), "dark": P(BLACK, 0.5), "reel": P((0.97, 0.97, 0.95), 0.4),
            "reelp": PR(_t_reel(rng, "reel1"), 0.4, alpha_from_image=True),
            "reelp2": PR(_t_reel(rng, "reel2"), 0.4, alpha_from_image=True)}


# ================================================================================================
# lore
# ================================================================================================

LORE_NAMES = {
    "gremlin": "Furblin (Talking Owl-Gremlin)",
    "gremlin_baby": "Baby Furblin",
    "gremlin_keychain": "Furblin Keychain",
    "gremlin_reboot": "Furblin, LED-Eye Reboot",
    "gremlin_box": "Furblin, Sealed Window Box",
    "gremlin_dictionary": "Furblish-English Dictionary",
    "gremlin_batteries": "AA 4-Pack and Battery Door",
    "gremlin_sling": "Furblin Carry Sling",
    "gremlin_stickers": "Speak Furblish! Sticker Sheet",
    "gremlin_fur": "Loose Furblin Fur",
    "beanie_bear": "Bean-Bag Bear, Heart Tag Attached",
    "beanie_dog": "Bean-Bag Dog",
    "beanie_pig": "Bean-Bag Pig",
    "beanie_lobster": "Bean-Bag Lobster",
    "beanie_elephant": "Bean-Bag Elephant",
    "beanie_frog": "Bean-Bag Frog",
    "beanie_flamingo": "Bean-Bag Flamingo",
    "beanie_tag_protector": "Heart Tag Protectors",
    "beanie_price_guide": "Bean Counter Price Guide",
    "beanie_display_case": "Acrylic Display Case (Occupied)",
    "beanie_teeny": "Teeny Weenie, Sealed",
    "beanie_certificate": "Certificate of Authenticity",
    "opera_saber": "Collapsible Laser Sword",
    "opera_carded": "Space Opera Figure, Carded",
    "opera_figures": "Loose Space Opera Figures",
    "opera_ship": "The Rusty Comet",
    "opera_mask": "Overlord Vex Costume Helm",
    "opera_case": "Collector's Carry Case",
    "opera_lunchbox": "Space Opera Lunchbox",
    "opera_vhs": "The Space Opera Trilogy (Remastered Again)",
    "opera_cards": "Space Opera Trading Cards",
    "opera_stickers": "Space Opera Sticker Sheet",
    "opera_mailaway": "Mail-Away Mystery Figure",
    "trip_it": "Trip-It Ankle Hopper",
    "flop_it": "Flop-It",
    "kush_ball": "Kush Ball",
    "moon_shooz": "Moon Shooz",
    "blow_up_gloves": "Inflatable Boxing Gloves",
    "soggy_blaster": "Soggy 50 Water Blaster",
    "nerd_blaster": "NERD Foam Dart Blaster",
    "stretch_man": "Stretch Armslow",
    "wrestler_fig": "Wrestling Figure (Champion, Allegedly)",
    "micro_cars": "Micro Machinations",
    "loop_track": "Not Wheels Loop Track",
    "robo_car": "Transmogrifier Robot Car",
    "pocket_playset": "Molly Pocket Compact",
    "monster_playset": "Mighty Minimum Doom Head",
    "bug_oven": "Creepy Crawlspace Thing-A-Baker",
    "toy_oven": "Queasy-Bake Oven",
    "tickle_monster": "Tickle Me Grumbo",
    "stereo_viewer": "Viewmeister 3D Viewer",
}

LORE_NOTES = {
    "gremlin": ["woke up at 3am and said something in Furblish. nobody slept again",
                "rumored to record conversations. banned from a government building, allegedly",
                "battery door screw stripped by Christmas night",
                "tried to make it sleep by covering its eyes. it learned to resent that"],
    "gremlin_baby": ["the 'baby' cost more than the adult", "higher voice, same demands",
                     "fed it imaginary food 400 times. still hungry"],
    "gremlin_keychain": ["did not talk. somehow still judged you", "fur worn bald from riding in a jeans pocket",
                         "clipped to a backpack, lost to a bus seat"],
    "gremlin_reboot": ["LED eyes now. rolls them at you. personally", "has an app. the app also talks",
                       "the 90s kids bought it for their kids, then kept it", "it remembers you. it never forgot"],
    "gremlin_box": ["mint in box. that was the plan", "parents paid triple to a guy in a parking lot",
                    "window scratched from checking if he was still in there", "he was. he's always in there"],
    "gremlin_dictionary": ["GRUB-NAH means FEED ME. it always means FEED ME", "the only book read cover to cover that year",
                           "dog-eared at EEP"],
    "gremlin_batteries": ["four AAs a week, minimum", "the battery door: screw lost, held on with tape",
                          "stole these out of the TV remote. the TV remote never recovered"],
    "gremlin_sling": ["so it could talk at you hands-free", "worn to school once. confiscated by 9:15"],
    "gremlin_stickers": ["two missing. they're on the fridge. since 1998", "SKREE means PET ME, per sticker"],
    "gremlin_fur": ["someone tried a haircut", "the scissors were from the kitchen drawer",
                    "it looks better now, said nobody"],
    "beanie_bear": ["tag protector on, tag crease-free, value: imaginary", "the purple one. it was going to be the college fund",
                    "mom bought six. for the kids. for the 'kids'", "still in the closet, still 'worth something'"],
    "beanie_dog": ["the tush tag says 1997. the price guide said $950. the market said no",
                   "chewed by a real dog, which felt personal"],
    "beanie_pig": ["named BAGHOLDER. the tag knew before we did", "never once sold above retail"],
    "beanie_lobster": ["rare color variant, said the guy at the flea market", "claw mended with red thread. resale value: gone",
                       "retired. like it had a pension"],
    "beanie_elephant": ["royal blue version worth $3,000, per guide", "this is the grey one. per guide: no"],
    "beanie_frog": ["beans leaking from the left leg since the 90s", "slept with it. tag still on. priorities"],
    "beanie_flamingo": ["the neck flops over every time. by design?", "bought at a card shop, fifteen minutes before close, 1998"],
    "beanie_tag_protector": ["the protector cost more than the animal attached to it",
                             "tags snipped off the 'worthless' ones and kept just in case",
                             "a clear plastic coffin for a paper heart"],
    "beanie_price_guide": ["read like scripture every month", "the prices only went up, until the issue they didn't",
                           "pencil checkmarks next to every bear we owned"],
    "beanie_display_case": ["the bear never touched air again", "UV protection, sold separately",
                            "displayed on a shelf above a bed nobody slept in"],
    "beanie_teeny": ["ordered 40 Happy-ish Meals. threw away 40 burgers", "still sealed. that's the whole point",
                     "#4 of 10. we had #4 nine times"],
    "beanie_certificate": ["one of only 12,000,000", "signed by the President of Scarcity",
                           "framed. the frame was worth more"],
    "opera_saber": ["third blade section jammed since 1997", "WHOOSH noise was made by mouth",
                    "took out a ceiling light in round one", "the hilt rattles. there's a battery in there somewhere"],
    "opera_carded": ["unpunched. probably", "the bubble is yellowed and slightly crushed. like all of us",
                     "dad says it'll pay for college. dad has said a lot of things"],
    "opera_figures": ["missing the blaster. always missing the blaster", "Glorp's middle eye chewed off",
                      "the cape got lost in the sandbox at a birthday party"],
    "opera_ship": ["the canopy pops off, then stays off", "landing gear: two of four", "flew it around the yard until dinner"],
    "opera_mask": ["drugstore Halloween, 1983-ish", "breathed through the slit. fogged instantly",
                   "elastic snapped during trick-or-treat. carried it home"],
    "opera_case": ["holds 24 figures. had 7", "smells exactly like 1984", "zipper still works. that's the miracle"],
    "opera_lunchbox": ["the thermos is gone. we don't talk about the thermos", "rust on the hinge, PB&J in the seams",
                       "traded a whole pudding cup for one look inside"],
    "opera_vhs": ["digitally remastered again. now with 40% more CGI", "the shrink wrap was torn by a dog",
                  "part 5 eaten by the VCR. rewound by pencil"],
    "opera_cards": ["came with a stick of gum that could cut glass", "the gum stain is on card 23",
                    "flipped against the wall at recess. lost the good one"],
    "opera_stickers": ["half on a bedroom door", "PEW PEW sticker on the family car, still there"],
    "opera_mailaway": ["five proofs of purchase, $2.50, eleven weeks", "checked the mailbox daily like a sentry",
                       "the figure was fine. the wait was the toy"],
    "trip_it": ["hit your other ankle 400 times. counted all of them", "lap counter stopped at a number we never beat",
                "played alone in the driveway until the streetlights came on"],
    "flop_it": ["FLOP IT. TWIST IT. PULL IT. CRUSH IT", "the voice still plays when crushed. listen",
                "pulled the pull too hard. it stayed pulled"],
    "kush_ball": ["collected dog hair, carpet lint and cereal", "one strand chewed off by a sibling",
                  "named before the other kush. we were innocent"],
    "moon_shooz": ["sprained an ankle by lunch", "the bungee cords snapped with a noise like a gunshot",
                   "never once felt like the moon"],
    "blow_up_gloves": ["slow leak since 1995", "the squeak was the best part", "punched a brother, the valve popped out"],
    "soggy_blaster": ["pumped it 40 times. soaked the neighbor's window", "the tank leaks into your armpit",
                      "a water gun with the range of a garden hose. it was a war crime"],
    "nerd_blaster": ["the darts are on the roof", "the suction tips fell off by Tuesday", "jammed on the first trigger pull"],
    "stretch_man": ["arm pulled out in 1988, still coming back", "the gel inside smells like corn syrup and regret",
                    "tied him in a knot. he didn't untie"],
    "wrestler_fig": ["champion belt bigger than his torso", "suplexed off a bunk bed", "his name was on the box. the box is gone"],
    "micro_cars": ["vacuumed up 3 of them", "stepped on the rest at 2am", "the whole set fit in a pencil case"],
    "loop_track": ["the car never made the loop", "connected it down the stairs. still never made the loop",
                   "the blue tabs broke first"],
    "robo_car": ["transforms in 47 steps, never the same way twice", "the arms come off. one did",
                 "ours. not theirs. same vibes"],
    "pocket_playset": ["the doll was lost within the hour", "the hinge cracked from opening it 10,000 times",
                       "smaller than a cookie. contained a whole house"],
    "monster_playset": ["the tiny guy fit perfect in the vent. he's still in the vent",
                        "doom zone in your pocket", "the eyes glowed green. or we imagined that"],
    "bug_oven": ["the oven got hot enough to brand you. we know", "goop stains on the kitchen table, forever",
                 "rubber bugs in mom's shoe. on purpose"],
    "toy_oven": ["powered by one light bulb and hope", "the cake was raw in the middle every time",
                 "ate it anyway", "burnt a finger on the slot. once. twice"],
    "tickle_monster": ["fist-fight in a big-box store, Black Friday", "the laugh box giggles by itself at 2am",
                       "TRY ME tag still on the hand", "squeezed it so much the laugh slowed down"],
    "stereo_viewer": ["the Grand Canyon in 3D, 7 frames at a time", "click, click, click, same reel, every Sunday",
                      "red plastic, never got old"],
}
