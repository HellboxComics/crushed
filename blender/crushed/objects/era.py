"""The nostalgic stuff. 1985-2008, generic shapes only."""
import math

from mathutils import Matrix

from .. import tex
from ..geo import ellipse, helix, rounded_rect
from . import BLACK, CHARCOAL, CHROME, MET, P, PR, RUB, SILVER, T, WHITE, BEIGE, obj


def _cord(b, rng, start, length, r=0.0022, mat="cord", curl=None):
    """A cable flopping away from `start`."""
    pts = [start]
    x, y, z = start
    ang = rng.uniform(0, 2 * math.pi)
    n = 14
    for i in range(n):
        ang += rng.normal(0, 0.6)
        step = length / n
        x += math.cos(ang) * step
        y += math.sin(ang) * step
        z += rng.normal(0, step * 0.3)
        pts.append((x, y, z))
    b.tube(pts, r, mat=mat, seg=8)


# -- audio ---------------------------------------------------------------------------

@obj("cassette", eras=(0, 1, 2), mass=0.05, weight=2.0)
def cassette(b, rng, pal):
    w, h, d = 0.1, 0.064, 0.012
    clear = rng.random() < (0.5 if pal.era >= 1 else 0.25)
    b.box((w, h, d), mat="shell", bevel=0.0015)
    b.plane(w * 0.9, h * 0.8, loc=(0, 0.002, d / 2 + 0.0003), mat="label")
    b.plane(w * 0.9, h * 0.8, loc=(0, 0.002, -d / 2 - 0.0003), rot=(math.pi, 0, 0), mat="label2")
    for sx in (-1, 1):
        b.cyl(0.011, d * 0.6, loc=(sx * 0.021, 0.0, 0), mat="reel", seg=16)
    b.box((w * 0.6, 0.012, d * 1.05), loc=(0, -h / 2 + 0.006, 0), mat="shell", bevel=0.001)
    shell = T((0.8, 0.82, 0.85), 0.15) if clear else P(pal.color("body") if rng.random() < 0.6 else BLACK)
    base = tuple(rng.choice([(0.95, 0.94, 0.9), (0.95, 0.85, 0.3), (0.9, 0.3, 0.3), (0.3, 0.5, 0.85),
                             (0.95, 0.95, 0.95)]))
    return {"shell": shell, "label": PR(tex.cassette_label(rng, base, "cas")),
            "label2": PR(tex.cassette_label(rng, base, "cas2")), "reel": P(WHITE)}


@obj("vhs", eras=(0, 1, 2), mass=0.22, weight=1.6)
def vhs(b, rng, pal):
    w, h, d = 0.187, 0.103, 0.025
    b.box((w, h, d), mat="shell", bevel=0.002)
    for sx in (-1, 1):
        b.plane(0.045, 0.028, loc=(sx * 0.045, 0.012, d / 2 + 0.0003), mat="window")
    b.plane(0.08, 0.035, loc=(0, -0.03, d / 2 + 0.0004), mat="label")
    b.plane(0.16, 0.018, loc=(0, h / 2 + 0.0004, 0), rot=(-math.pi / 2, 0, 0), mat="spine")
    return {"shell": P(BLACK, 0.5, texture=0.4), "window": T((0.1, 0.1, 0.1), 0.05),
            "label": PR(tex.sticker(rng, "vhs", words=rng.choice(["REC", "SP", "EP", "XMAS", "DO NOT TAPE OVER"]))),
            "spine": PR(tex.sticker(rng, "vhs2", lines=1))}


@obj("boombox", eras=(0, 1), mass=3.5, weight=1.2, big=True, hero=(0, -1, 0))
def boombox(b, rng, pal):
    w, h, d = 0.46, 0.25, 0.14
    b.box((w, d, h), mat="body", bevel=0.01)
    for sx in (-1, 1):
        b.lathe([(0.0, 0.0), (0.03, 0.004), (0.07, 0.012), (0.085, 0.004), (0.093, 0.0), (0.093, -0.01)],
                loc=(sx * 0.135, -d / 2 - 0.004, -0.015), rot=(math.pi / 2, 0, 0), mat="cone", seg=28)
        b.torus(0.094, 0.006, loc=(sx * 0.135, -d / 2 - 0.004, -0.015), rot=(math.pi / 2, 0, 0), mat="trim",
                seg=28, rseg=8)
    b.plane(0.11, 0.07, loc=(0, -d / 2 - 0.0005, -0.02), rot=(math.pi / 2, 0, 0), mat="deck")
    for i in range(6):
        b.box((0.016, 0.02, 0.012), loc=(-0.05 + i * 0.02, -0.02, h / 2 + 0.004), mat="keys", bevel=0.002)
    b.tube([(-0.17, 0, h / 2), (-0.16, 0, h / 2 + 0.06), (0.16, 0, h / 2 + 0.06), (0.17, 0, h / 2)], 0.009,
           mat="trim", seg=10)
    b.plane(0.2, 0.03, loc=(0, -d / 2 - 0.0005, 0.085), rot=(math.pi / 2, 0, 0), mat="dial")
    rng2 = rng
    return {"body": pal.body(loud=0.2, clear=0.0) if rng.random() < 0.6 else P(SILVER, 0.3),
            "cone": P((0.08, 0.08, 0.08), 0.8, texture=0.5), "trim": CHROME(), "keys": P(SILVER, 0.25),
            "deck": PR(tex.cassette_label(rng2, (0.1, 0.1, 0.12), "deck")),
            "dial": PR(tex.lcd(rng2, "dial", "FM 88 92 96 100 104 108", bg=(0.15, 0.15, 0.15), ink=(0.9, 0.6, 0.2)))}


@obj("walkman", eras=(0, 1), mass=0.3, weight=1.2)
def walkman(b, rng, pal):
    w, h, d = 0.115, 0.085, 0.032
    b.box((w, h, d), mat="body", bevel=0.004)
    b.plane(0.075, 0.048, loc=(0.005, 0.0, d / 2 + 0.0004), mat="window")
    for i in range(5):
        b.box((0.012, 0.008, 0.006), loc=(-0.035 + i * 0.016, h / 2 + 0.003, 0.004), mat="keys", bevel=0.0015)
    b.box((0.02, 0.06, 0.003), loc=(0, 0, -d / 2 - 0.003), mat="keys")
    body = P(pal.color("loud"), 0.3) if rng.random() < 0.4 else MET(rng.choice([SILVER, (0.2, 0.3, 0.6),
                                                                              (0.6, 0.15, 0.15)]), 0.35)
    return {"body": body, "keys": MET(SILVER, 0.3),
            "window": PR(tex.cassette_label(rng, (0.12, 0.12, 0.14), "wm"), rough=0.1)}


@obj("headphones", eras=(0, 1, 2), mass=0.08)
def headphones(b, rng, pal):
    R = 0.075
    b.torus(R, 0.003, rot=(math.pi / 2, 0, 0), mat="band", seg=28, rseg=6, arc=math.pi)
    for sx in (-1, 1):
        b.cyl(0.032, 0.022, loc=(sx * R, 0, -0.012), rot=(0, math.pi / 2, 0), mat="foam", seg=20)
        b.cyl(0.02, 0.008, loc=(sx * (R + 0.012), 0, -0.012), rot=(0, math.pi / 2, 0), mat="cup", seg=16)
    _cord(b, rng, (R + 0.015, 0, -0.03), 0.25, 0.0012)
    return {"band": MET(SILVER, 0.25), "cup": P(BLACK),
            "foam": ("foam", {"color": tuple(rng.choice([(0.95, 0.45, 0.1), (0.1, 0.1, 0.1), (0.9, 0.2, 0.2)]))}),
            "cord": RUB()}


@obj("portable_cd", eras=(1, 2), mass=0.25, weight=1.2)
def portable_cd(b, rng, pal):
    r = 0.068
    b.cyl(r, 0.024, mat="body", seg=40)
    b.cyl(r * 0.92, 0.003, loc=(0, 0, 0.013), mat="lid", seg=40)
    b.cyl(0.02, 0.002, loc=(0.0, -0.03, 0.0155), mat="window", seg=20)
    for i in range(5):
        a = -0.5 + i * 0.22
        b.box((0.012, 0.006, 0.005), loc=(math.cos(a - math.pi / 2) * r, math.sin(a - math.pi / 2) * r, 0),
              rot=(0, 0, a), mat="keys", bevel=0.0015)
    return {"body": pal.body(clear=0.35), "lid": pal.body(clear=0.4 if pal.era == 2 else 0.1),
            "window": T((0.2, 0.2, 0.25)), "keys": P(CHARCOAL)}


@obj("cd", eras=(1, 2, 3), mass=0.016, weight=2.0)
def cd(b, rng, pal):
    b.lathe([(0.0075, 0.0006), (0.06, 0.0006), (0.06, -0.0006), (0.0075, -0.0006)], mat="data", seg=48)
    b.plane(0.11, 0.11, loc=(0, 0, 0.0008), mat="marker", cuts=6)
    burned = pal.era >= 2 and rng.random() < 0.7
    color = (0.45, 0.6, 0.95) if burned and rng.random() < 0.5 else (0.85, 0.75, 0.4) if burned else (0.85, 0.85, 0.88)
    parts = {"data": ("disc", {"color": color, "film": float(rng.uniform(350, 650))}),
             "marker": PR(tex.cd_marker(rng, "cdm"), rough=0.3, alpha_from_image=True)}
    if rng.random() < 0.45:
        b.box((0.142, 0.125, 0.0104), loc=(0.004, 0.0, -0.007), mat="case", bevel=0.001)
        parts["case"] = T((0.9, 0.92, 0.95), 0.03)
    return parts


@obj("jewel_case", eras=(1, 2, 3), mass=0.08)
def jewel_case(b, rng, pal):
    b.box((0.142, 0.125, 0.0104), mat="case", bevel=0.001)
    b.plane(0.12, 0.12, loc=(0.005, 0, 0.0035), mat="insert")
    return {"case": T((0.9, 0.92, 0.95), 0.03),
            "insert": PR(tex.griptape_art(rng, "insert"), 0.3)}


# -- phones & pagers -----------------------------------------------------------------

@obj("corded_phone", eras=(0, 1, 2), mass=1.1, weight=1.5, big=True)
def corded_phone(b, rng, pal):
    # low wedge base with a sloped keypad face
    prof = [(-0.1, 0.0), (0.1, 0.0), (0.1, 0.03), (-0.1, 0.06)]
    b.extrude(prof, 0.19, rot=(math.pi / 2, 0, math.pi / 2), mat="body", bevel=0.008)
    b.plane(0.075, 0.085, loc=(0.0, 0.035, 0.047), rot=(-0.15, 0, 0), mat="keys")
    # two cradle prongs
    for sx in (-1, 1):
        b.box((0.025, 0.03, 0.02), loc=(sx * 0.07, -0.05, 0.06), mat="body", bevel=0.006)
    # handset: slim grip, fat ear and mouth pieces angled down
    b.frame = Matrix.Translation((0, -0.05, 0.085))
    b.box((0.13, 0.034, 0.022), mat="body", bevel=0.009)
    for sx in (-1, 1):
        b.box((0.055, 0.052, 0.034), loc=(sx * 0.085, 0, -0.008), rot=(0, sx * 0.25, 0), mat="body", bevel=0.012)
        b.cyl(0.018, 0.002, loc=(sx * 0.09, 0, -0.026), mat="grille", seg=16)
    b.frame = Matrix.Identity(4)
    b.tube(helix(0.008, 0.006, 16, 12, start=(0.11, -0.05, 0.07)), 0.0022, mat="cord", seg=6)
    clear = pal.era == 2 and rng.random() < 0.7
    body = T(rng.choice([(0.55, 0.2, 0.8), (0.2, 0.5, 0.95), (0.9, 0.3, 0.5), (0.4, 0.85, 0.2)]), 0.12) \
        if clear else P(rng.choice([BEIGE, (0.7, 0.1, 0.1), BLACK, WHITE, (0.9, 0.85, 0.75)]))
    return {"body": body, "keys": PR(tex.keypad(rng, "phonekeys", key=(0.9, 0.9, 0.88),
                                                 body=(0.25, 0.25, 0.25))), "cord": body,
            "grille": P(CHARCOAL, 0.6)}


@obj("pager", eras=(1, 2), mass=0.08, weight=2.0)
def pager(b, rng, pal):
    w, h, d = 0.06, 0.045, 0.018
    b.box((w, h, d), mat="body", bevel=0.005, seg=3)
    b.plane(0.038, 0.016, loc=(-0.004, 0.006, d / 2 + 0.0004), mat="lcd")
    for i in range(3):
        b.cyl(0.0035, 0.004, loc=(-0.016 + i * 0.012, -0.013, d / 2), mat="btn", seg=12)
    b.box((0.03, 0.035, 0.002), loc=(0, 0, -d / 2 - 0.003), mat="body")
    return {"body": pal.body(loud=0.2, clear=0.45 if pal.era == 2 else 0.1),
            "lcd": PR(tex.lcd(rng, "pg"), 0.15), "btn": P(CHARCOAL, 0.6)}


@obj("flip_phone", eras=(2, 3), mass=0.1, weight=1.5)
def flip_phone(b, rng, pal):
    w, h, d = 0.048, 0.09, 0.011
    b.box((w, h, d), loc=(0, -h / 2, 0), mat="body", bevel=0.004)
    b.plane(0.038, 0.06, loc=(0, -h / 2 - 0.005, d / 2 + 0.0004), mat="keys")
    ang = rng.uniform(0.2, 0.7)
    b.frame = Matrix.Rotation(ang, 4, "X")
    b.box((w, h, d), loc=(0, h / 2, 0), mat="body", bevel=0.004)
    b.plane(0.036, 0.045, loc=(0, h / 2 + 0.005, d / 2 + 0.0004), mat="lcd")
    b.frame = Matrix.Identity(4)
    b.cyl(0.006, w, loc=(0, 0, 0), rot=(0, math.pi / 2, 0), mat="hinge", seg=12)
    slim = pal.era == 3
    body = MET(rng.choice([SILVER, (0.85, 0.45, 0.6), (0.15, 0.15, 0.18), (0.2, 0.35, 0.7)]), 0.3) if slim \
        else pal.body(clear=0.3)
    return {"body": body, "hinge": MET(SILVER, 0.3),
            "keys": PR(tex.keypad(rng, "fkeys", key=(0.75, 0.8, 0.9) if slim else (0.8, 0.8, 0.8),
                                  body=(0.2, 0.2, 0.22))),
            "lcd": ("screen", {"image": tex.screen(rng, "fl", rng.choice(["blue", "off", "term"])), "glow": 0.3})}


@obj("candybar_phone", eras=(2,), mass=0.13, weight=1.2)
def candybar_phone(b, rng, pal):
    w, h, d = 0.047, 0.115, 0.022
    b.box((w, h, d), mat="body", bevel=0.008, seg=3)
    b.plane(0.034, 0.03, loc=(0, 0.028, d / 2 + 0.0004), mat="lcd")
    b.plane(0.036, 0.05, loc=(0, -0.025, d / 2 + 0.0004), mat="keys")
    b.cyl(0.004, 0.02, loc=(0.015, h / 2 + 0.008, 0), rot=(math.pi / 2, 0, 0), mat="ant", seg=10)
    return {"body": pal.body(loud=0.4, clear=0.35), "ant": RUB(),
            "lcd": PR(tex.lcd(rng, "cb", bg=(0.45, 0.6, 0.45)), 0.2),
            "keys": PR(tex.keypad(rng, "cbk", key=(0.85, 0.85, 0.8), body=(0.3, 0.3, 0.3)))}


# -- screens & computers -------------------------------------------------------------

@obj("crt", eras=(0, 1, 2), mass=12.0, weight=1.4, big=True)
def crt(b, rng, pal):
    W, Hh = 0.38, 0.34
    b.box((W, Hh, 0.05), loc=(0, 0, 0.0), mat="bezel", bevel=0.012)
    b.cyl(0.28, 0.3, r2=0.12, loc=(0, 0, -0.17), rot=(0, 0, math.pi / 4), mat="bezel", seg=4)
    f = b.plane(0.31, 0.25, loc=(0, 0.012, 0.027), mat="screen", cuts=10)
    verts = {v for fa in f for v in fa.verts}
    for v in verts:
        x, y = v.co.x / 0.155, (v.co.y - 0.012) / 0.125
        v.co.z += 0.012 * (1 - 0.5 * (x * x + y * y))
    b.cyl(0.006, 0.004, loc=(0.15, -0.15, 0.026), mat="btn", seg=12)
    b.plane(0.08, 0.012, loc=(-0.1, -0.15, 0.0255), mat="vent")
    beige = pal.era < 2 or rng.random() < 0.6
    return {"bezel": P(BEIGE if beige else pal.color("loud"), 0.45) if beige or rng.random() < 0.5
            else T(pal.color("loud"), 0.15),
            "screen": ("screen", {"image": tex.screen(rng, "crt"), "glow": 0.25, "crack_scale": 6.0}),
            "btn": P(CHARCOAL), "vent": P((0.1, 0.1, 0.1), 0.8)}


@obj("keyboard_chunk", eras=(0, 1, 2), mass=0.5, weight=1.0)
def keyboard_chunk(b, rng, pal):
    cols, rows = rng.integers(5, 9), 4
    kw = 0.019
    b.box((cols * kw + 0.01, rows * kw + 0.01, 0.015), loc=(0, 0, -0.006), mat="case", bevel=0.002)
    for r in range(rows):
        for c in range(cols):
            if rng.random() < 0.1:
                continue
            b.box((kw * 0.86, kw * 0.86, 0.009), loc=((c - cols / 2 + 0.5) * kw, (r - rows / 2 + 0.5) * kw, 0.006),
                  rot=(rng.normal(0, 0.05), rng.normal(0, 0.05), 0), mat="key" if rng.random() < 0.9 else "key2",
                  bevel=0.0015)
    return {"case": P(BEIGE if pal.era < 2 else pal.color("body")), "key": P((0.9, 0.88, 0.8), 0.5),
            "key2": P((0.55, 0.55, 0.52), 0.5)}


@obj("mouse", eras=(1, 2), mass=0.1, weight=1.3)
def mouse(b, rng, pal):
    rings = []
    for i in range(12):
        t = i / 11
        y = -0.055 + t * 0.11
        wd = 0.03 * math.sin(math.pi * (0.1 + 0.8 * t)) + 0.006
        ht = 0.035 * math.sin(math.pi * (0.05 + 0.75 * t)) + 0.004
        ring = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            ring.append((wd * math.cos(a), y, max(0.0, ht * math.sin(a))))
        rings.append(ring)
    b.loft(rings, mat="body")
    b.plane(0.0015, 0.04, loc=(0, 0.035, 0.037), mat="seam")
    _cord(b, rng, (0, 0.058, 0.01), 0.22, 0.0018)
    return {"body": pal.body(loud=0.05, clear=0.35), "seam": P(BLACK), "cord": P(BEIGE if pal.era < 2 else CHARCOAL)}


@obj("floppy", eras=(0, 1, 2), mass=0.02, weight=2.0)
def floppy(b, rng, pal):
    b.box((0.09, 0.094, 0.0033), mat="body", bevel=0.0008)
    b.box((0.05, 0.03, 0.0038), loc=(0.0, 0.032, 0), mat="shutter")
    b.plane(0.07, 0.05, loc=(0, -0.018, 0.0018), mat="label")
    b.cyl(0.013, 0.0038, loc=(0, 0.0, 0), mat="shutter", seg=16)
    return {"body": pal.body(loud=0.3, clear=0.4 if pal.era == 2 else 0.05),
            "shutter": MET(SILVER, 0.25),
            "label": PR(tex.sticker(rng, "fl", words=rng.choice(["DISK 1", "DOS", "BACKUP", "GAMES", "HW", "TERM"])))}


@obj("calculator", eras=(0, 1), mass=0.1, weight=1.3)
def calculator(b, rng, pal):
    w, h, d = 0.075, 0.13, 0.012
    b.box((w, h, d), mat="body", bevel=0.003)
    b.plane(0.058, 0.02, loc=(0, 0.043, d / 2 + 0.0004), mat="lcd")
    b.plane(0.03, 0.008, loc=(0.012, 0.059, d / 2 + 0.0004), mat="solar")
    b.plane(0.064, 0.078, loc=(0, -0.018, d / 2 + 0.0004), mat="keys")
    return {"body": P(rng.choice([CHARCOAL, BLACK, (0.55, 0.52, 0.48), SILVER]), 0.4),
            "lcd": PR(tex.lcd(rng, "calc", rng.choice(["5318008", "58008", "0.", "7734", "ERROR", "80085"])), 0.15),
            "solar": P((0.12, 0.08, 0.06), 0.1),
            "keys": PR(tex.keypad(rng, "calck", rows=5, cols=4, labels="789/456*123-0.=+C", key=(0.8, 0.8, 0.78),
                                  body=(0.15, 0.15, 0.15)))}


@obj("webcam", eras=(2,), mass=0.12)
def webcam(b, rng, pal):
    b.sphere(0.03, mat="body", seg=20)
    b.cyl(0.012, 0.02, loc=(0, 0, 0.022), mat="ring", seg=16)
    b.cyl(0.009, 0.002, loc=(0, 0, 0.033), mat="lens", seg=16)
    b.cyl(0.02, 0.008, loc=(0, 0, -0.045), mat="ring", seg=16)
    b.cyl(0.004, 0.02, loc=(0, 0, -0.035), mat="ring", seg=8)
    return {"body": T(pal.color("loud"), 0.15), "ring": P(CHARCOAL), "lens": ("lens", {})}


@obj("digital_camera", eras=(2, 3), mass=0.25, weight=1.3)
def digital_camera(b, rng, pal):
    w, h, d = 0.11, 0.06, 0.035
    b.box((w, h, d), mat="body", bevel=0.005)
    b.cyl(0.02, 0.018, loc=(0.02, -0.004, d / 2 + 0.009), mat="barrel", seg=24)
    b.cyl(0.013, 0.003, loc=(0.02, -0.004, d / 2 + 0.018), mat="lens", seg=24)
    b.plane(0.02, 0.01, loc=(-0.035, 0.018, d / 2 + 0.0004), mat="flash")
    b.cyl(0.005, 0.004, loc=(-0.04, h / 2, 0), rot=(math.pi / 2, 0, 0), mat="barrel", seg=12)
    b.plane(0.05, 0.038, loc=(0.0, 0, -d / 2 - 0.0004), rot=(math.pi, 0, 0), mat="lcd")
    return {"body": MET(rng.choice([SILVER, (0.3, 0.3, 0.32), (0.6, 0.15, 0.2)]), 0.35)
            if rng.random() < 0.7 else pal.body(),
            "barrel": MET(SILVER, 0.2), "lens": ("lens", {}), "flash": T((0.95, 0.95, 0.95), 0.4),
            "lcd": ("screen", {"image": tex.screen(rng, "dc", rng.choice(["off", "static", "blue"])), "glow": 0.2})}


@obj("mp3_player", eras=(2, 3), mass=0.06, weight=1.3)
def mp3_player(b, rng, pal):
    w, h, d = 0.05, 0.09, 0.014
    b.box((w, h, d), mat="body", bevel=0.005, seg=3)
    b.plane(0.036, 0.03, loc=(0, 0.024, d / 2 + 0.0004), mat="lcd")
    for (x, y) in ((0, -0.012), (0, -0.034), (-0.011, -0.023), (0.011, -0.023)):
        b.box((0.008, 0.008, 0.003), loc=(x, y, d / 2), mat="btn", bevel=0.0012)
    b.cyl(0.004, 0.003, loc=(0, -0.023, d / 2), mat="btn2", seg=12)
    return {"body": pal.body(loud=0.45, clear=0.3 if pal.era == 2 else 0.0),
            "lcd": PR(tex.lcd(rng, "mp3", rng.choice(["TRACK 07", "SHUFFLE", "03:47", "LOW BATT", "128KBPS"]),
                              bg=(0.35, 0.5, 0.75), ink=(0.05, 0.05, 0.15)), 0.15),
            "btn": P(CHARCOAL, 0.5), "btn2": CHROME()}


@obj("memory_card", eras=(2, 3), mass=0.004)
def memory_card(b, rng, pal):
    n = rng.integers(1, 4)
    poly = [(-0.012, -0.016), (0.012, -0.016), (0.012, 0.012), (0.008, 0.016), (-0.012, 0.016)]
    for i in range(n):
        b.extrude(poly, 0.0021, loc=(i * 0.012, i * 0.004, i * 0.003), rot=(0, 0, rng.normal(0, 0.4)),
                  mat="card")
    return {"card": P(rng.choice([(0.1, 0.25, 0.7), BLACK, (0.6, 0.1, 0.1), SILVER]), 0.3)}


@obj("usb_stick", eras=(3, 4), mass=0.01, weight=1.2)
def usb_stick(b, rng, pal):
    b.box((0.045, 0.018, 0.009), mat="body", bevel=0.003)
    b.box((0.013, 0.012, 0.0045), loc=(0.029, 0, 0), mat="plug")
    if rng.random() < 0.5:
        b.box((0.02, 0.02, 0.011), loc=(0.037, 0, 0), mat="body", bevel=0.003)
    return {"body": pal.body(loud=0.5, clear=0.2), "plug": MET(SILVER, 0.2)}


@obj("charger_brick", eras=(3, 4), mass=0.3)
def charger_brick(b, rng, pal):
    b.box((0.11, 0.05, 0.03), mat="body", bevel=0.005)
    _cord(b, rng, (0.055, 0, 0), 0.3, 0.003)
    _cord(b, rng, (-0.055, 0, 0), 0.2, 0.003)
    return {"body": P(rng.choice([BLACK, WHITE, CHARCOAL]), 0.5), "cord": P(BLACK, 0.5)}


# -- games ------------------------------------------------------------------------

def _bone(w, h):
    pts = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        x = math.cos(a) * w / 2
        y = math.sin(a) * h / 2
        pinch = 1.0 - 0.28 * math.exp(-((x / (w * 0.18)) ** 2))
        pts.append((x, y * pinch))
    return pts


@obj("controller_16bit", eras=(1,), mass=0.12, weight=1.8)
def controller_16bit(b, rng, pal):
    b.extrude(_bone(0.135, 0.058), 0.022, mat="body", bevel=0.004)
    b.box((0.024, 0.008, 0.006), loc=(-0.042, 0, 0.012), mat="dpad", bevel=0.001)
    b.box((0.008, 0.024, 0.006), loc=(-0.042, 0, 0.012), mat="dpad", bevel=0.001)
    for i, (x, y) in enumerate(((0.038, -0.01), (0.05, 0.002), (0.038, 0.014), (0.026, 0.002))):
        b.cyl(0.0055, 0.006, loc=(x, y, 0.012), mat=f"btn{i % 2}", seg=14)
    for x in (-0.008, 0.008):
        b.box((0.01, 0.004, 0.003), loc=(x, -0.01, 0.0115), rot=(0, 0, 0.5), mat="dpad", bevel=0.001)
    _cord(b, rng, (0, 0.03, 0), 0.3, 0.0022)
    gray = rng.random() < 0.6
    return {"body": P((0.62, 0.62, 0.64) if gray else CHARCOAL, 0.45), "dpad": P(BLACK, 0.4),
            "btn0": P(rng.choice([(0.4, 0.25, 0.55), (0.8, 0.1, 0.1), (0.2, 0.2, 0.2)]), 0.3),
            "btn1": P(rng.choice([(0.55, 0.45, 0.7), (0.1, 0.3, 0.8), (0.85, 0.75, 0.1)]), 0.3),
            "cord": P(BLACK, 0.5)}


@obj("controller_modern", eras=(2, 3, 4), mass=0.2, weight=1.5)
def controller_modern(b, rng, pal):
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        x = math.cos(a) * 0.075
        y = math.sin(a) * 0.035
        if y < 0:
            y *= 1.0 + 1.6 * math.exp(-(((abs(x) - 0.05) / 0.018) ** 2))
        pts.append((x, y))
    b.extrude(pts, 0.03, mat="body", bevel=0.006)
    for sx in (-1, 1):
        b.cyl(0.009, 0.012, loc=(sx * 0.022, -0.014, 0.02), mat="stick", seg=16)
        b.cyl(0.011, 0.003, loc=(sx * 0.022, -0.014, 0.027), mat="stick", seg=16)
        b.box((0.03, 0.012, 0.014), loc=(sx * 0.05, 0.035, 0.004), rot=(0.3, 0, 0), mat="stick", bevel=0.003)
    for i, (x, y) in enumerate(((0.05, 0.0), (0.06, 0.01), (0.05, 0.02), (0.04, 0.01))):
        b.cyl(0.0045, 0.006, loc=(x, y, 0.016), mat=f"b{i}", seg=12)
    b.box((0.02, 0.007, 0.005), loc=(-0.05, 0.01, 0.016), mat="stick")
    b.box((0.007, 0.02, 0.005), loc=(-0.05, 0.01, 0.016), mat="stick")
    body = pal.body(loud=0.2, clear=0.55 if pal.era == 2 else 0.0)
    cols = [(0.1, 0.7, 0.2), (0.9, 0.1, 0.1), (0.1, 0.3, 0.9), (0.95, 0.8, 0.1)]
    out = {"body": body, "stick": P(CHARCOAL, 0.6)}
    for i in range(4):
        out[f"b{i}"] = P(cols[i], 0.25) if rng.random() < 0.5 else T(cols[i], 0.1)
    return out


@obj("joystick", eras=(0,), mass=0.35, weight=1.6)
def joystick(b, rng, pal):
    b.box((0.09, 0.09, 0.035), mat="base", bevel=0.006)
    tilt = (rng.normal(0, 0.3), rng.normal(0, 0.3), 0)
    b.cyl(0.006, 0.08, loc=(0, 0, 0.055), rot=tilt, mat="stick", seg=12)
    b.sphere(0.014, loc=(math.sin(tilt[1]) * 0.08, -math.sin(tilt[0]) * 0.08, 0.095), mat="knob", seg=14)
    b.cyl(0.008, 0.008, loc=(0.03, 0.03, 0.02), mat="knob", seg=14)
    _cord(b, rng, (0, 0.045, 0), 0.3)
    return {"base": P(BLACK, 0.5), "stick": P(BLACK, 0.3), "knob": P((0.8, 0.05, 0.05), 0.25), "cord": P(BLACK)}


@obj("game_cart", eras=(0, 1), mass=0.07, weight=1.4)
def game_cart(b, rng, pal):
    w, h, d = 0.11, 0.075, 0.018
    b.box((w, h, d), mat="body", bevel=0.002)
    for i in range(7):
        b.box((0.1, 0.002, 0.0015), loc=(0, h / 2 - 0.004 - i * 0.004, d / 2), mat="body")
    b.plane(0.08, 0.04, loc=(0, -0.01, d / 2 + 0.0004), mat="label")
    return {"body": P(rng.choice([(0.35, 0.35, 0.37), (0.6, 0.6, 0.6), BLACK]), 0.5),
            "label": PR(tex.griptape_art(rng, "cart"), 0.35)}


@obj("brick_game", eras=(1,), mass=0.12, weight=1.2)
def brick_game(b, rng, pal):
    w, h, d = 0.075, 0.13, 0.022
    b.box((w, h, d), mat="body", bevel=0.006)
    b.plane(0.05, 0.05, loc=(0, 0.028, d / 2 + 0.0004), mat="lcd")
    for (x, y) in ((-0.02, -0.03), (-0.02, -0.046), (-0.03, -0.038), (-0.01, -0.038)):
        b.cyl(0.005, 0.005, loc=(x, y, d / 2), mat="btn", seg=12)
    b.cyl(0.009, 0.005, loc=(0.022, -0.036, d / 2), mat="btn2", seg=16)
    b.cyl(0.006, 0.005, loc=(0.01, -0.05, d / 2), mat="btn2", seg=16)
    return {"body": pal.body(loud=0.6), "lcd": PR(tex.lcd(rng, "bg", rng.choice(["GAME OVER", "99999", "HI 0000"])),
                                                   0.2),
            "btn": P(BLACK), "btn2": P(rng.choice([(0.9, 0.85, 0.1), (0.9, 0.1, 0.1)]))}


@obj("handheld", eras=(3, 4), mass=0.2, weight=1.0)
def handheld(b, rng, pal):
    b.extrude(rounded_rect(0.16, 0.07, 0.03, 6), 0.02, mat="body", bevel=0.004)
    b.plane(0.07, 0.045, loc=(0, 0.004, 0.0105), mat="lcd")
    b.box((0.02, 0.007, 0.004), loc=(-0.058, 0, 0.011), mat="btn")
    b.box((0.007, 0.02, 0.004), loc=(-0.058, 0, 0.011), mat="btn")
    for (x, y) in ((0.055, 0.008), (0.064, -0.004)):
        b.cyl(0.006, 0.004, loc=(x, y, 0.011), mat="btn", seg=12)
    return {"body": pal.body(loud=0.4), "btn": P(CHARCOAL),
            "lcd": ("screen", {"image": tex.screen(rng, "hh", rng.choice(["off", "blue", "static"])), "glow": 0.3})}


@obj("virtual_pet", eras=(2,), mass=0.04, weight=1.3)
def virtual_pet(b, rng, pal):
    b.extrude(ellipse(0.046, 0.052, 28), 0.016, mat="body", bevel=0.005)
    b.plane(0.02, 0.018, loc=(0, 0.005, 0.0085), mat="lcd")
    for i in range(3):
        b.cyl(0.0028, 0.003, loc=(-0.009 + i * 0.009, -0.014, 0.008), mat="btn", seg=10)
    b.torus(0.008, 0.0012, loc=(0, 0.032, 0), rot=(0, math.pi / 2, 0), mat="chain", seg=14, rseg=5)
    return {"body": T(pal.color("loud"), 0.15), "btn": P(WHITE),
            "lcd": PR(tex.lcd(rng, "vp", rng.choice(["HUNGRY", "DEAD", "FEED ME", "SICK", "ZZZ"])), 0.2),
            "chain": MET(SILVER, 0.2)}


@obj("puzzle_cube", eras=(0, 1), mass=0.1, weight=1.5)
def puzzle_cube(b, rng, pal):
    s = 0.019
    cols = ["s0", "s1", "s2", "s3", "s4", "s5"]
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                if rng.random() < 0.06:
                    continue
                c = (x * s, y * s, z * s)
                b.box((s * 0.97, s * 0.97, s * 0.97), loc=c, mat="core", bevel=0.0015)
                for ax, v in ((0, x), (1, y), (2, z)):
                    if v == 0:
                        continue
                    rot = [(0, math.pi / 2 * v, 0), (-math.pi / 2 * v, 0, 0), (0, 0 if v > 0 else math.pi, 0)][ax]
                    off = list(c)
                    off[ax] += v * s * 0.49
                    b.plane(s * 0.82, s * 0.82, loc=off, rot=rot, mat=cols[rng.integers(0, 6)], cuts=1)
    palette = [(0.9, 0.1, 0.1), (0.1, 0.6, 0.2), (0.1, 0.3, 0.9), (0.95, 0.95, 0.95), (1.0, 0.85, 0.1),
               (1.0, 0.45, 0.05)]
    out = {"core": P(BLACK, 0.4)}
    for i, c in enumerate(cols):
        out[c] = P(palette[i], 0.25)
    return out


@obj("yoyo", eras=(0, 1), mass=0.05, weight=1.3)
def yoyo(b, rng, pal):
    prof = [(0.0, 0.017), (0.02, 0.017), (0.028, 0.013), (0.029, 0.006), (0.008, 0.002), (0.004, 0.0)]
    b.lathe(prof, mat="a", seg=28)
    b.lathe([(r, -z) for r, z in reversed(prof)], mat="b", seg=28)
    pts = [(0.004, 0, 0)] + [(0.004 + i * 0.012, rng.normal(0, 0.01), rng.normal(0, 0.006)) for i in range(1, 12)]
    b.tube(pts, 0.0008, mat="string", seg=5)
    c = pal.color("loud")
    return {"a": T(c, 0.1) if rng.random() < 0.3 else P(c, 0.25), "b": P(c, 0.25),
            "string": ("fabric", {"color": (0.95, 0.95, 0.9)})}


@obj("army_men", eras=(0, 1), mass=0.04, weight=1.5)
def army_men(b, rng, pal):
    for k in range(rng.integers(2, 5)):
        b.frame = Matrix.Translation((k * 0.03 - 0.04, rng.normal(0, 0.012), 0)) @ \
            Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
        b.cyl(0.012, 0.003, loc=(0, 0, 0.0), mat="green", seg=14)
        for sx in (-1, 1):
            b.cyl(0.0035, 0.024, loc=(sx * 0.004, 0, 0.014), rot=(sx * 0.2, 0, 0), mat="green", seg=8)
        b.box((0.013, 0.008, 0.017), loc=(0, 0, 0.034), mat="green", bevel=0.002)
        b.sphere(0.0045, loc=(0, 0, 0.048), mat="green", seg=10)
        b.sphere(0.0058, loc=(0, 0, 0.05), scale=(1, 1, 0.55), mat="green", seg=10)
        b.cyl(0.0014, 0.03, loc=(0.008, -0.008, 0.038), rot=(1.2, 0, 0.3), mat="green", seg=6)
        b.cyl(0.0022, 0.012, loc=(-0.008, -0.006, 0.036), rot=(1.0, 0, 0), mat="green", seg=6)
    b.frame = Matrix.Identity(4)
    return {"green": ("army", {"color": tuple(rng.choice([(0.22, 0.36, 0.12), (0.27, 0.34, 0.15),
                                                          (0.2, 0.3, 0.1)]))})}


# -- wearables -------------------------------------------------------------------------

def _foot(t, L):
    """Half-width of a shoe footprint at t (0 heel .. 1 toe)."""
    return L * (0.115 + 0.075 * math.sin(math.pi * min(1.0, t * 1.05)) ** 0.7 - 0.02 * math.exp(-((t - 0.45) / 0.12) ** 2))


@obj("sneaker", eras=(0, 1, 2, 3, 4), mass=0.45, weight=1.6, hero=(0, -1, 0))
def sneaker(b, rng, pal):
    L = 0.28
    high = pal.era <= 1 and rng.random() < 0.55
    sole_h = 0.028
    n = 22
    # sole: footprint extrusion
    fp = []
    for i in range(n):
        t = i / (n - 1)
        fp.append((-L / 2 + t * L, _foot(t, L)))
    for i in range(n - 1, -1, -1):
        t = i / (n - 1)
        fp.append((-L / 2 + t * L, -_foot(t, L)))
    b.extrude(fp, sole_h, loc=(0, 0, sole_h / 2), mat="sole", bevel=0.006)
    b.extrude([(x * 1.01, y * 1.01) for x, y in fp], 0.008, loc=(0, 0, sole_h * 0.85), mat="mid")
    # upper: arched cross sections, low at the toe, high at the collar
    rings = []
    for i in range(n):
        t = i / (n - 1)
        x = -L / 2 + 0.006 + t * (L - 0.012)
        w = _foot(t, L) * 0.96
        collar = (0.13 if high else 0.075)
        if t < 0.3:
            h = 0.07 + (collar - 0.07) * math.sin(math.pi * t / 0.6)
        else:
            h = 0.03 + (collar - 0.03) * (1 - (t - 0.3) / 0.7) ** 1.3
        h = max(h, 0.028) if t < 0.97 else 0.02
        ring = []
        for k in range(18):
            a = math.pi * k / 17
            ring.append((x, math.cos(a) * w, sole_h + math.sin(a) * h * (0.9 + 0.1 * math.sin(a))))
        rings.append(ring)
    b.loft(rings, mat="upper", closed=False, cap=False)
    # collar opening and tongue
    top = 0.075 if not high else 0.13
    b.sphere(0.032, loc=(-L * 0.3, 0, sole_h + top - 0.004), scale=(1.4, 0.9, 0.18), mat="lining", seg=16)
    b.box((0.06, 0.05, 0.008), loc=(-L * 0.12, 0, sole_h + top - 0.005), rot=(0, -0.55, 0), mat="upper", bevel=0.003)
    for i in range(5):
        xx = -L * 0.05 + i * 0.02
        zz = sole_h + (top - 0.01) - i * (0.01 if not high else 0.016)
        b.box((0.006, 0.075, 0.003), loc=(xx, 0, zz + 0.012), rot=(0, 0.3, 0), mat="lace", bevel=0.001)
    # side panels: toe cap and heel counter in the accent color
    for sy in (-1, 1):
        b.extrude([(0.0, 0.0), (0.06, 0.0), (0.075, 0.03), (0.03, 0.045), (-0.01, 0.03)], 0.002,
                  loc=(-L / 2 + 0.005, sy * _foot(0.08, L) * 1.02, sole_h), rot=(math.pi / 2, 0, 0), mat="panel")
        b.extrude([(0.0, 0.0), (0.09, 0.0), (0.05, 0.04), (0.0, 0.03)], 0.002,
                  loc=(L * 0.1, sy * _foot(0.72, L) * 0.98, sole_h), rot=(math.pi / 2, 0, 0), mat="panel")
    up = tuple(rng.choice([WHITE, BLACK, (0.85, 0.1, 0.1), (0.2, 0.3, 0.7), (0.9, 0.9, 0.85), (0.3, 0.3, 0.32)]))
    acc = pal.color("loud")
    return {"upper": ("fabric", {"color": up}) if rng.random() < 0.4 else P(up, 0.5),
            "sole": RUB((0.93, 0.91, 0.86)) if rng.random() < 0.7 else RUB((0.55, 0.35, 0.2)),
            "mid": P(acc, 0.4), "lace": ("fabric", {"color": WHITE if up != WHITE else acc}),
            "panel": P(acc, 0.4), "lining": ("fabric", {"color": (0.1, 0.1, 0.1)})}


@obj("sunglasses", eras=(0, 1, 2, 3, 4), mass=0.03, weight=1.5)
def sunglasses(b, rng, pal):
    for sx in (-1, 1):
        shape = rounded_rect(0.052, 0.04, 0.012, 4)
        b.extrude(shape, 0.004, loc=(sx * 0.031, 0, 0), mat="lens")
        ring = [(x * 1.12, y * 1.15) for x, y in shape]
        b.tube([(sx * 0.031 + x, y, 0) for x, y in ring] + [(sx * 0.031 + ring[0][0], ring[0][1], 0)], 0.0028,
               mat="frame", seg=6, cap=False)
        b.tube([(sx * 0.06, 0.012, 0), (sx * 0.063, 0.012, -0.05), (sx * 0.064, 0.0, -0.13),
                (sx * 0.064, -0.02, -0.145)], 0.0022, mat="frame", seg=6)
    b.tube([(-0.006, 0.01, 0), (0, 0.014, 0), (0.006, 0.01, 0)], 0.003, mat="frame", seg=6)
    return {"lens": ("lens", {"color": tuple(rng.choice([(0.05, 0.05, 0.06), (0.4, 0.1, 0.5), (0.1, 0.2, 0.4)])),
                              "film": float(rng.uniform(200, 600))}),
            "frame": P(pal.color("loud") if rng.random() < 0.6 else BLACK, 0.3)}


@obj("roller_skate", eras=(0,), mass=1.1, weight=1.1, hero=(0, -1, 0))
def roller_skate(b, rng, pal):
    prof = [(-0.12, 0.0), (0.12, 0.0), (0.13, 0.03), (0.05, 0.05), (-0.02, 0.07), (-0.05, 0.17),
            (-0.12, 0.17), (-0.13, 0.05)]
    b.extrude(prof, 0.085, rot=(math.pi / 2, 0, 0), loc=(0, 0, 0.03), mat="boot", bevel=0.01)
    b.box((0.24, 0.07, 0.01), loc=(0, 0, 0.025), mat="plate")
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.026, 0.02, loc=(sx * 0.085, sy * 0.042, 0.0), rot=(math.pi / 2, 0, 0), mat="wheel", seg=20)
    b.cyl(0.018, 0.03, loc=(0.135, 0, 0.01), rot=(0, 1.2, 0), mat="stop", seg=14)
    return {"boot": P(rng.choice([WHITE, (1.0, 0.4, 0.7), (0.1, 0.1, 0.1)]), 0.35), "plate": MET(SILVER, 0.3),
            "wheel": P(pal.color("loud"), 0.3), "stop": RUB((0.5, 0.1, 0.1))}


@obj("slap_bracelet", eras=(1,), mass=0.01)
def slap_bracelet(b, rng, pal):
    pts = [(0.03 * math.cos(a / 20 * 5.5), 0.03 * math.sin(a / 20 * 5.5), 0) for a in range(21)]
    rings = []
    for (x, y, z) in pts:
        rings.append([(x * 1.0, y * 1.0, -0.012), (x * 1.03, y * 1.03, -0.012), (x * 1.03, y * 1.03, 0.012),
                      (x, y, 0.012)])
    b.loft(rings, mat="band")
    return {"band": P(pal.color("loud"), 0.3)}


# -- school -----------------------------------------------------------------------------

@obj("notebook", eras=(0, 1, 2, 3, 4), mass=0.3, weight=1.3)
def notebook(b, rng, pal):
    w, h = 0.2, 0.26
    b.box((w, h, 0.012), mat="pages")
    b.plane(w * 0.96, h * 0.97, loc=(0.004, 0, 0.0062), mat="page")
    if rng.random() < 0.6:
        b.box((w, h, 0.0015), loc=(0, 0, -0.0068), mat="cover")
    for i in range(18):
        y = -h / 2 + 0.01 + i * (h - 0.02) / 17
        b.torus(0.007, 0.0009, loc=(-w / 2 + 0.002, y, 0), rot=(math.pi / 2, 0, 0), mat="spiral", seg=12, rseg=4)
    return {"pages": ("paper", {}), "page": PR(tex.notebook(rng, "nb"), 0.85),
            "cover": ("cardboard", {"color": pal.color("loud")}), "spiral": MET(SILVER, 0.3)}


@obj("pencil", eras=(0, 1, 2, 3, 4), mass=0.01, weight=1.2)
def pencil(b, rng, pal):
    n = rng.integers(1, 4)
    for i in range(n):
        y = i * 0.01
        b.cyl(0.0038, 0.15, loc=(0, y, 0), rot=(0, math.pi / 2, 0), mat="paint", seg=6)
        b.cyl(0.0038, 0.02, r2=0.0006, loc=(0.085, y, 0), rot=(0, math.pi / 2, 0), mat="wood", seg=6)
        b.cyl(0.004, 0.012, loc=(-0.081, y, 0), rot=(0, math.pi / 2, 0), mat="ferrule", seg=12)
        b.cyl(0.0038, 0.008, loc=(-0.091, y, 0), rot=(0, math.pi / 2, 0), mat="eraser", seg=12)
    return {"paint": P(rng.choice([(1.0, 0.75, 0.05), (1.0, 0.75, 0.05), (0.2, 0.3, 0.8), (0.1, 0.1, 0.1)]), 0.3),
            "wood": ("wood", {}), "ferrule": MET((0.8, 0.7, 0.4), 0.3), "eraser": RUB((0.95, 0.5, 0.55))}


@obj("binder", eras=(0, 1), mass=0.4, weight=1.0)
def binder(b, rng, pal):
    b.box((0.26, 0.3, 0.035), mat="cover", bevel=0.004)
    b.plane(0.24, 0.28, loc=(0, 0, 0.0178), mat="art")
    b.box((0.05, 0.06, 0.004), loc=(0.11, 0, 0.02), mat="flap", bevel=0.002)
    return {"cover": P(pal.color("loud"), 0.5), "art": PR(tex.griptape_art(rng, "binder"), 0.4),
            "flap": ("fabric", {"color": (0.1, 0.1, 0.1)})}


@obj("lunchbox", eras=(0, 1), mass=0.6, weight=1.0, big=True, hero=(0, -1, 0))
def lunchbox(b, rng, pal):
    b.box((0.2, 0.1, 0.17), mat="tin", bevel=0.01)
    b.plane(0.18, 0.15, loc=(0, -0.0505, 0), rot=(math.pi / 2, 0, 0), mat="art")
    b.torus(0.03, 0.005, loc=(0, 0, 0.09), rot=(math.pi / 2, 0, 0), arc=math.pi, mat="handle", seg=12)
    return {"tin": MET(pal.color("loud"), 0.35), "art": PR(tex.griptape_art(rng, "lunch"), 0.25, metal=0.3),
            "handle": P(BLACK)}


@obj("slime", eras=(1,), mass=0.12, weight=1.3)
def slime(b, rng, pal):
    b.lathe([(0.0, -0.03), (0.028, -0.03), (0.032, 0.02), (0.034, 0.028), (0.0, 0.028)], mat="can", seg=24)
    b.sphere(0.03, loc=(0.02, 0.0, 0.03), scale=(1.4, 1.0, 0.6), mat="slime", seg=18)
    return {"can": P(rng.choice([(0.1, 0.8, 0.2), (0.95, 0.5, 0.05), (0.6, 0.2, 0.8)]), 0.3),
            "slime": ("slime", {"color": tuple(rng.choice([(0.3, 0.95, 0.2), (0.95, 0.3, 0.6), (0.2, 0.7, 1.0)]))})}


# -- boards & wheels ------------------------------------------------------------------

@obj("skateboard", eras=(1, 2), mass=1.8, weight=1.3, big=True, hero=(0, 0, -1))
def skateboard(b, rng, pal):
    L = 0.4
    pts = rounded_rect(L, 0.2, 0.09, 8)
    jag = [(x if x < L / 2 - 0.1 else L / 2 - 0.1 + rng.uniform(-0.02, 0.02), y) for x, y in pts]
    b.extrude(jag, 0.012, mat="deck")
    b.plane(L * 0.96, 0.19, loc=(0, 0, 0.0063), mat="grip")
    b.plane(L * 0.96, 0.19, loc=(0, 0, -0.0063), rot=(math.pi, 0, 0), mat="art")
    x = -L / 2 + 0.07
    b.box((0.04, 0.15, 0.025), loc=(x, 0, -0.02), mat="truck", bevel=0.004)
    b.cyl(0.004, 0.2, loc=(x, 0, -0.035), rot=(math.pi / 2, 0, 0), mat="truck", seg=10)
    for sy in (-1, 1):
        b.cyl(0.027, 0.032, loc=(x, sy * 0.085, -0.035), rot=(math.pi / 2, 0, 0), mat="wheel", seg=22)
    return {"deck": ("wood", {}), "grip": P((0.04, 0.04, 0.04), 0.95, texture=1.0),
            "art": PR(tex.griptape_art(rng, "deck"), 0.4), "truck": MET(SILVER, 0.35),
            "wheel": P(rng.choice([WHITE, (0.95, 0.9, 0.5), pal.color("loud")]), 0.45)}


@obj("skate_wheel", eras=(1, 2), mass=0.1, weight=1.2)
def skate_wheel(b, rng, pal):
    n = rng.integers(1, 3)
    for i in range(n):
        b.lathe([(0.011, -0.016), (0.022, -0.016), (0.027, -0.012), (0.028, 0.0), (0.027, 0.012),
                 (0.022, 0.016), (0.011, 0.016), (0.011, -0.016)], loc=(i * 0.06, 0, 0), mat="pu", seg=28)
        b.cyl(0.011, 0.008, loc=(i * 0.06, 0, 0), mat="bearing", seg=16)
    return {"pu": P(rng.choice([WHITE, (0.95, 0.9, 0.5), (0.1, 0.8, 0.9), (0.95, 0.3, 0.1)]), 0.5),
            "bearing": MET(SILVER, 0.2)}


# -- power & misc -----------------------------------------------------------------------

@obj("aa_batteries", eras=(0, 1, 2, 3, 4), mass=0.1, weight=1.8)
def aa_batteries(b, rng, pal):
    n = rng.integers(2, 5)
    img = tex.battery(rng, "aa")
    for i in range(n):
        y = i * 0.0145 - n * 0.007
        rot = (0, math.pi / 2, rng.normal(0, 0.15))
        b.cyl(0.00725, 0.049, loc=(0, y, 0), rot=rot, mat="label", seg=20)
        b.cyl(0.0027, 0.0028, loc=(0.026, y, 0), rot=rot, mat="cap", seg=12)
    return {"label": ("printed", {"image": img, "rough": 0.3, "metal": 0.2, "ext": "REPEAT"}),
            "cap": MET(SILVER, 0.2)}


@obj("tv_remote", eras=(0, 1, 2, 3, 4), mass=0.15, weight=1.5)
def tv_remote(b, rng, pal):
    w, h, d = 0.05, 0.18, 0.02
    b.box((w, h, d), mat="body", bevel=0.006, seg=3)
    b.plane(0.04, 0.08, loc=(0, -0.02, d / 2 + 0.0004), mat="keys")
    for i, c in enumerate(("r", "g", "y", "bl")):
        b.box((0.008, 0.006, 0.003), loc=(-0.015 + i * 0.01, 0.035, d / 2), mat=c, bevel=0.001)
    b.cyl(0.006, 0.003, loc=(0.013, 0.07, d / 2), mat="r", seg=12)
    b.plane(0.02, 0.006, loc=(0, h / 2 + 0.0004, 0), rot=(-math.pi / 2, 0, 0), mat="ir")
    return {"body": P(rng.choice([BLACK, CHARCOAL, (0.4, 0.4, 0.42), SILVER]), 0.45),
            "keys": PR(tex.keypad(rng, "rk", rows=5, cols=3, labels="123456789-0+", key=(0.6, 0.6, 0.62),
                                  body=(0.1, 0.1, 0.1), ink=(0.95, 0.95, 0.95))),
            "r": P((0.85, 0.1, 0.1)), "g": P((0.1, 0.7, 0.2)), "y": P((0.9, 0.8, 0.1)), "bl": P((0.1, 0.3, 0.85)),
            "ir": T((0.2, 0.02, 0.02), 0.1)}


@obj("extension_cord", eras=(0, 1, 2, 3, 4), mass=0.6, weight=1.2)
def extension_cord(b, rng, pal):
    b.box((0.25, 0.055, 0.035), mat="body", bevel=0.006)
    for i in range(4):
        x = -0.09 + i * 0.055
        b.plane(0.022, 0.028, loc=(x, 0, 0.0178), mat="outlet")
    b.box((0.02, 0.02, 0.008), loc=(-0.105, 0, 0.018), mat="switch", bevel=0.002)
    col = rng.choice([WHITE, BEIGE, (0.95, 0.45, 0.05), BLACK])
    _cord(b, rng, (0.125, 0, 0), 0.4, 0.004)
    return {"body": P(col, 0.45), "cord": P(col, 0.5),
            "outlet": PR(tex.keypad(rng, "outlet", rows=1, cols=1, labels=" ", key=(0.1, 0.1, 0.1),
                                    body=tuple(col)), 0.5),
            "switch": T((0.9, 0.1, 0.05), 0.2)}


@obj("pizza_crust", eras=(0, 1, 2, 3, 4), mass=0.05, weight=1.4)
def pizza_crust(b, rng, pal):
    arc = rng.uniform(0.6, 1.1)
    R = 0.17
    n = 18
    pts = [(R * math.cos(arc * i / n), R * math.sin(arc * i / n), 0) for i in range(n + 1)]
    b.tube(pts, lambda t: 0.012 + 0.004 * math.sin(t * 17) + 0.004 * math.sin(t * 5.3), mat="crust", seg=12)
    if rng.random() < 0.7:
        # what's left of the slice: a bite-shaped wedge of cheese, maybe pepperoni
        bite = rng.uniform(0.25, 0.6)
        ch = [(R * bite * math.cos(arc / 2), R * bite * math.sin(arc / 2))]
        ch += [(R * math.cos(arc * i / n) * 0.96, R * math.sin(arc * i / n) * 0.96) for i in range(n + 1)]
        b.extrude(ch, 0.005, loc=(0, 0, -0.005), mat="cheese")
        for _ in range(rng.integers(1, 4)):
            rr = R * rng.uniform(bite + 0.1, 0.85)
            aa = arc * rng.uniform(0.2, 0.8)
            b.cyl(0.013, 0.003, loc=(rr * math.cos(aa), rr * math.sin(aa), -0.001), mat="pep", seg=16)
    return {"crust": ("crust", {}), "cheese": P((0.98, 0.78, 0.3), 0.35), "pep": P((0.6, 0.08, 0.05), 0.45)}


@obj("soda_can", eras=(0, 1, 2, 3, 4), mass=0.015, weight=1.4)
def soda_can(b, rng, pal):
    prof = [(0.0, -0.061), (0.025, -0.0615), (0.032, -0.055), (0.033, 0.05), (0.028, 0.06), (0.027, 0.0615),
            (0.0, 0.0615)]
    b.lathe(prof, mat="print", seg=32, rot=(0, math.pi / 2, 0))
    return {"print": ("printed", {"image": tex.can_print(rng, "soda"), "rough": 0.2, "metal": 0.6})}


@obj("energy_can", eras=(3, 4), mass=0.02, weight=2.0)
def energy_can(b, rng, pal):
    prof = [(0.0, -0.085), (0.024, -0.086), (0.0295, -0.079), (0.0295, 0.075), (0.026, 0.084), (0.025, 0.0855),
            (0.0, 0.0855)]
    b.lathe(prof, mat="print", seg=32, rot=(0, math.pi / 2, 0))
    return {"print": ("printed", {"image": tex.can_print(rng, "nrg"), "rough": 0.18, "metal": 0.7})}


@obj("film_canister", eras=(0, 1, 2), mass=0.012, weight=1.0)
def film_canister(b, rng, pal):
    for i in range(rng.integers(1, 3)):
        b.cyl(0.0155, 0.05, loc=(i * 0.034, 0, 0), rot=(0, math.pi / 2, 0), mat="can", seg=20)
        b.cyl(0.0165, 0.007, loc=(i * 0.034 + 0.027, 0, 0), rot=(0, math.pi / 2, 0), mat="lid", seg=20)
    return {"can": P(BLACK, 0.4), "lid": P(rng.choice([(0.6, 0.6, 0.62), (0.1, 0.1, 0.1)]), 0.5)}


@obj("disposable_camera", eras=(1, 2, 3, 4), mass=0.1, weight=1.1)
def disposable_camera(b, rng, pal):
    b.box((0.11, 0.055, 0.033), mat="wrap", bevel=0.004)
    b.cyl(0.012, 0.008, loc=(0.02, 0, 0.018), mat="barrel", seg=18)
    b.cyl(0.008, 0.002, loc=(0.02, 0, 0.023), mat="lens", seg=16)
    b.plane(0.022, 0.012, loc=(-0.035, 0.015, 0.0168), mat="flash")
    b.cyl(0.006, 0.006, loc=(0.045, 0.028, 0.008), rot=(math.pi / 2, 0, 0), mat="barrel", seg=16)
    return {"wrap": P(rng.choice([(1.0, 0.8, 0.1), (0.1, 0.55, 0.25), (0.1, 0.3, 0.8)]), 0.3),
            "barrel": P(BLACK), "lens": ("lens", {}), "flash": T((0.95, 0.95, 0.95), 0.4)}


@obj("glow_stick", eras=(2, 3, 4), mass=0.02)
def glow_stick(b, rng, pal):
    col = rng.choice([(0.3, 1.0, 0.2), (1.0, 0.2, 0.7), (0.2, 0.7, 1.0), (1.0, 0.6, 0.1)])
    bend = rng.uniform(0.0, 0.8)
    pts = [(0.075 * math.sin(bend * (t / 10 - 0.5)) / max(bend, 1e-3), 0,
            0.075 * (1 - math.cos(bend * (t / 10 - 0.5))) / max(bend, 1e-3)) for t in range(11)]
    b.tube(pts, 0.0045, mat="glow", seg=10)
    return {"glow": ("slime", {"color": tuple(col)})}


@obj("lighter", eras=(1, 2, 3, 4), mass=0.02)
def lighter(b, rng, pal):
    b.box((0.025, 0.012, 0.06), mat="body", bevel=0.004)
    b.box((0.02, 0.011, 0.012), loc=(0, 0, 0.036), mat="top")
    b.cyl(0.004, 0.009, loc=(0.005, 0, 0.042), rot=(math.pi / 2, 0, 0), mat="top", seg=12)
    return {"body": T(pal.color("loud"), 0.1), "top": MET(SILVER, 0.3)}


@obj("milk_caps", eras=(1,), mass=0.02)
def milk_caps(b, rng, pal):
    n = rng.integers(3, 8)
    for i in range(n):
        b.cyl(0.02, 0.0015, loc=(rng.normal(0, 0.01), rng.normal(0, 0.01), i * 0.0018),
              rot=(rng.normal(0, 0.05), rng.normal(0, 0.05), 0), mat=f"c{i % 3}", seg=24)
    b.cyl(0.021, 0.003, loc=(0.03, 0.01, 0), mat="slammer", seg=24)
    return {"c0": ("cardboard", {"color": pal.color("loud")}), "c1": ("cardboard", {"color": pal.color("loud")}),
            "c2": ("cardboard", {"color": (0.95, 0.95, 0.9)}), "slammer": CHROME()}
