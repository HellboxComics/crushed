"""Tech: the gadgets of 1985-2008 (regular cubes), plus three one-of-one shelves:
DIAL-UP (the family computer and its free trial discs), BE KIND REWIND (Friday night at the video store) and
CAR AUDIO (the trunk that rattled the block). Every brand on them is a parody; every mascot is our own."""
import math

import numpy as np
from mathutils import Matrix

from .. import tex
from ..geo import ellipse, helix, rounded_rect
from . import BEIGE, BLACK, CHARCOAL, CHROME, MET, P, PR, RUB, SILVER, T, WHITE, YELLOWED, obj

SP = dict(group="special")
TAU = 2 * math.pi
E = 0.0004          # how far a print floats over the surface it sits on
Canvas = tex.Canvas


def _ch(rng, seq):
    return seq[int(rng.integers(0, len(seq)))]


def _rgb(c):
    return tuple(float(x) for x in c)


def _alpha_from_bg(c, bg):
    """Make every pixel that still matches the background transparent (for stickers and legends)."""
    d = np.abs(c.a[..., :3] - np.array(bg, dtype=np.float32)).sum(axis=2)
    c.a[..., 3] = (d > 0.02).astype(np.float32)


def _sheet(b, w, h, mat, bow=0.006, curl=0.0, n=9, wob=0.0, loc=(0, 0, 0), rot=(0, 0, 0)):
    """A sheet of paper (UV 0..1 over the whole print) with a bow and an optional curl at the top edge."""
    rows = []
    for j in range(n):
        v = j / (n - 1)
        y = -h / 2 + h * v
        z0 = curl * v ** 3
        rows.append([(-w / 2 + w * i / (n - 1), y,
                      z0 + bow * (1 - abs(i - (n - 1) / 2) / ((n - 1) / 2)) + wob * math.sin(j * 1.7 + i))
                     for i in range(n)])
    b.loft(rows, mat=mat, closed=False, cap=False, loc=loc, rot=rot)


def _disc(b, mat="data", r=0.06, loc=(0, 0, 0), rot=(0, 0, 0), t=0.0012):
    """A CD: the clear hub ring (slot "hub") and the shiny data area."""
    b.lathe([(0.0075, t / 2), (0.0172, t / 2), (0.0172, -t / 2), (0.0075, -t / 2)], loc=loc, rot=rot, mat="hub", seg=40)
    b.lathe([(0.017, t / 2), (r, t / 2), (r, -t / 2), (0.017, -t / 2)], loc=loc, rot=rot, mat=mat, seg=48)


HUB = T((0.88, 0.9, 0.93), 0.05)


def _disc_print(c):
    """Cut a canvas to a CD: transparent outside the rim and inside the hub."""
    asp = c.w / c.h
    d = np.hypot((c.x - 0.5) * asp, c.y - 0.5)
    c.a[..., 3] = ((d < 0.497) & (d > 0.143)).astype(np.float32)


def _barcode(c, rng, x0, y0, x1, y1, ink=(0.05, 0.05, 0.05)):
    x = x0
    while x < x1:
        w = float(rng.choice([0.004, 0.007, 0.011])) * (x1 - x0) / 0.3
        if rng.random() < 0.6:
            c.rect(x, y0, min(x + w, x1), y1, ink)
        x += w * 1.6


# == prints =========================================================================================

def _blippy(c, cx, cy, s, body=(1.0, 0.86, 0.1), ink=(0.05, 0.05, 0.08), pose=0):
    """BLIPPY, the AIMLESS messenger mascot: a yellow jellybean with one big eye, an antenna and sneakers.
    Our own critter; he waves, he jumps, he sleeps (away message)."""
    asp = c.w / c.h
    sx = s / asp
    c.line([(cx, cy + s * 0.5), (cx + sx * 0.15, cy + s * 0.85)], s * 0.06, ink)          # antenna
    c.circle(cx + sx * 0.15, cy + s * 0.88, s * 0.09, (1.0, 0.25, 0.4))
    for lx in (-0.18, 0.18):                                                               # legs + sneakers
        jump = 0.12 if pose == 1 else 0.0
        c.line([(cx + sx * lx, cy - s * 0.3), (cx + sx * lx * 1.2, cy - s * (0.62 - jump))], s * 0.07, ink)
        c.poly([(cx + sx * lx * 1.2 - sx * 0.1, cy - s * (0.6 - jump)), (cx + sx * lx * 1.2 + sx * 0.18, cy - s * (0.6 - jump)),
                (cx + sx * lx * 1.2 + sx * 0.18, cy - s * (0.72 - jump)), (cx + sx * lx * 1.2 - sx * 0.1, cy - s * (0.72 - jump))],
               (0.9, 0.1, 0.15))
    arm = 0.55 if pose == 0 else (0.75 if pose == 1 else 0.05)
    c.line([(cx + sx * 0.3, cy), (cx + sx * 0.55, cy + s * arm)], s * 0.07, ink)
    c.line([(cx - sx * 0.3, cy), (cx - sx * 0.5, cy - s * 0.15 + (s * 0.6 if pose == 1 else 0))], s * 0.07, ink)
    pts = [(cx + sx * 0.36 * math.cos(a), cy + s * 0.5 * math.sin(a)) for a in np.linspace(0, TAU, 40)[:-1]]
    c.poly(pts, ink)
    pts = [(cx + sx * 0.32 * math.cos(a), cy + s * 0.46 * math.sin(a)) for a in np.linspace(0, TAU, 40)[:-1]]
    c.poly(pts, body)
    if pose == 2:                                                                          # asleep: Z Z Z
        c.line([(cx - sx * 0.14, cy + s * 0.12), (cx + sx * 0.14, cy + s * 0.12)], s * 0.05, ink)
        c.text("Z", cx + sx * 0.4, cy + s * 0.75, s * 0.3, ink, bold=True)
    else:
        c.circle(cx, cy + s * 0.12, s * 0.17, (1, 1, 1))
        c.circle(cx, cy + s * 0.12, s * 0.17, ink, ring=s * 0.03)
        c.circle(cx + sx * 0.04, cy + s * 0.1, s * 0.07, ink)
    c.line([(cx - sx * 0.1, cy - s * 0.2), (cx, cy - s * 0.25), (cx + sx * 0.1, cy - s * 0.2)], s * 0.04, ink)


def _lime_guy(c, cx, cy, r):
    """LIMEWHY's lime: a slice with an attitude and headphones."""
    asp = c.w / c.h
    rx = r / asp
    c.circle(cx, cy, r, (0.15, 0.45, 0.08))
    c.circle(cx, cy, r * 0.88, (0.85, 0.95, 0.55))
    c.circle(cx, cy, r * 0.8, (0.5, 0.85, 0.15))
    for k in range(8):
        a = k * TAU / 8
        c.line([(cx, cy), (cx + rx * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a))], r * 0.05, (0.85, 0.95, 0.6))
    ink = (0.05, 0.08, 0.03)
    for sx in (-1, 1):
        c.circle(cx + sx * rx * 0.3, cy + r * 0.12, r * 0.16, (1, 1, 1))
        c.circle(cx + sx * rx * 0.3, cy + r * 0.1, r * 0.07, ink)
        c.line([(cx + sx * rx * 0.48, cy + r * 0.38), (cx + sx * rx * 0.12, cy + r * 0.26)], r * 0.07, ink)
        c.rect(cx + sx * rx * 1.02 - rx * 0.12, cy - r * 0.2, cx + sx * rx * 1.02 + rx * 0.12, cy + r * 0.2, (0.1, 0.1, 0.1))
    c.line([(cx - rx, cy + r * 0.15), (cx - rx * 0.7, cy + r * 1.05), (cx + rx * 0.7, cy + r * 1.05), (cx + rx, cy + r * 0.15)],
           r * 0.08, (0.1, 0.1, 0.1))
    c.line([(cx - rx * 0.3, cy - r * 0.35), (cx, cy - r * 0.28), (cx + rx * 0.35, cy - r * 0.42)], r * 0.07, ink)


def _nap_cat(c, cx, cy, r):
    """NAPPSTER's cat: round grey head, asleep on the job, headphones on, a drool bubble. Ours."""
    asp = c.w / c.h
    rx = r / asp
    ink = (0.05, 0.05, 0.06)
    for sx in (-1, 1):
        c.poly([(cx + sx * rx * 0.85, cy + r * 0.3), (cx + sx * rx * 0.75, cy + r * 1.15), (cx + sx * rx * 0.2, cy + r * 0.8)], ink)
        c.poly([(cx + sx * rx * 0.72, cy + r * 0.4), (cx + sx * rx * 0.68, cy + r * 0.95), (cx + sx * rx * 0.32, cy + r * 0.72)],
               (0.95, 0.6, 0.65))
    c.circle(cx, cy, r, ink)
    c.circle(cx, cy, r * 0.9, (0.62, 0.62, 0.66))
    for sx in (-1, 1):
        c.line([(cx + sx * rx * 0.5, cy + r * 0.1), (cx + sx * rx * 0.35, cy + r * 0.02), (cx + sx * rx * 0.2, cy + r * 0.1)],
               r * 0.07, ink)
        for k in (-1, 0, 1):
            c.line([(cx + sx * rx * 0.35, cy - r * 0.3), (cx + sx * rx * 1.1, cy - r * 0.3 + k * r * 0.15)], r * 0.03, ink)
        c.rect(cx + sx * rx * 0.98 - rx * 0.13, cy - r * 0.25, cx + sx * rx * 0.98 + rx * 0.13, cy + r * 0.25, (0.85, 0.1, 0.1))
    c.poly([(cx - rx * 0.08, cy - r * 0.15), (cx + rx * 0.08, cy - r * 0.15), (cx, cy - r * 0.25)], (0.95, 0.5, 0.6))
    c.circle(cx + rx * 0.25, cy - r * 0.45, r * 0.12, (0.7, 0.9, 1.0), ring=r * 0.03)
    c.line([(cx - rx * 0.95, cy + r * 0.2), (cx - rx * 0.6, cy + r * 1.1), (cx + rx * 0.6, cy + r * 1.1), (cx + rx * 0.95, cy + r * 0.2)],
           r * 0.08, (0.1, 0.1, 0.1))


def _wheel_print(rng, name, ring=(0.93, 0.93, 0.92), ink=(0.62, 0.62, 0.64)):
    """A click wheel seen from above: MENU at 12, skip at 3 and 9, play/pause at 6."""
    c = Canvas(256, 256, (*ring, 1))
    c.text("MENU", 0.37, 0.92, 0.07, ink, bold=True)
    for sx in (-1, 1):
        x = 0.5 + sx * 0.37
        c.poly([(x - sx * 0.04, 0.54), (x - sx * 0.04, 0.46), (x + sx * 0.0, 0.5)], ink)
        c.poly([(x + sx * 0.0, 0.54), (x + sx * 0.0, 0.46), (x + sx * 0.04, 0.5)], ink)
        c.rect(x + sx * 0.045 - 0.006, 0.46, x + sx * 0.045 + 0.006, 0.54, ink)
    c.poly([(0.43, 0.16), (0.43, 0.08), (0.48, 0.12)], ink)
    c.rect(0.52, 0.08, 0.535, 0.16, ink)
    c.rect(0.55, 0.08, 0.565, 0.16, ink)
    d = np.hypot(c.x - 0.5, c.y - 0.5)
    c.a[..., 3] = ((d < 0.5) & (d > 0.19)).astype(np.float32)
    return c.image(name)


def _pod_screen(rng, name, color=False):
    bg = (0.97, 0.97, 0.98) if color else (0.62, 0.68, 0.72)
    ink = (0.05, 0.05, 0.08)
    c = Canvas(256, 192, (*bg, 1))
    c.rect(0, 0.86, 1, 1, (0.75, 0.78, 0.85) if color else (0.5, 0.56, 0.6))
    c.text_fit(_ch(rng, ["EYE-POD", "NOW PLAYING", "MUSIC"]), 0.06, 0.97, 0.7, 0.1, ink, bold=True)
    c.rect(0.82, 0.89, 0.95, 0.96, ink)
    rows = ["PLAYLISTS", "ARTISTS", "SONGS", "SHUFFLE SONGS", "EXTRAS", "SETTINGS", "BACKLIGHT"]
    sel = int(rng.integers(0, 5))
    for i, t in enumerate(rows[:6]):
        y = 0.82 - i * 0.135
        if i == sel:
            c.rect(0, y - 0.13, 1, y + 0.005, (0.2, 0.45, 0.9) if color else ink)
        c.text(t, 0.06, y - 0.02, 0.08, (1, 1, 1) if i == sel else ink, bold=True)
        c.text(">", 0.9, y - 0.02, 0.08, (1, 1, 1) if i == sel else ink, bold=True)
    img = c.image(name)
    img["lcd"] = True
    return img



# == A) ERA: the gadgets ============================================================================

@obj("yapper_boy", eras=(1,), mass=0.7, weight=1.1, hero=(0, -1, 0))
def yapper_boy(b, rng, pal):
    """The movie-kid tape recorder: a silver brick with a carry handle bigger than the kid's hand and a mic
    on a stalk that pulls out the side. Slows your voice down. Prank calls the hotel."""
    W, D, H = 0.17, 0.062, 0.105
    b.box((W, D, H), loc=(0, 0, H / 2), mat="body", bevel=0.009, seg=3)
    b.box((W * 0.98, D * 0.6, 0.012), loc=(0, 0, H - 0.002), mat="trim", bevel=0.004)
    b.tube([(-0.062, 0, H), (-0.06, 0, H + 0.03), (-0.04, 0, H + 0.052), (0.04, 0, H + 0.052), (0.06, 0, H + 0.03),
            (0.062, 0, H)], 0.009, mat="trim", seg=12)
    for i in range(5):                                          # piano keys on top, REC is red
        b.box((0.016, 0.022, 0.008), loc=(-0.04 + i * 0.02, -0.017, H + 0.006), mat="rec" if i == 0 else "key",
              bevel=0.002)
    ang = float(rng.uniform(-0.2, 0.35))
    x0 = W / 2
    tip = (x0 + 0.085 * math.cos(ang), -0.01, H * 0.65 + 0.085 * math.sin(ang))
    b.tube([(x0 - 0.01, -0.01, H * 0.65), tip], 0.0045, mat="stalk", seg=10)
    b.sphere(0.016, loc=tip, scale=(1.2, 1, 1), mat="foam", seg=16)
    b.plane(W * 0.92, H * 0.82, loc=(0, -D / 2 - E, H * 0.47), rot=(math.pi / 2, 0, 0), mat="face", cuts=3)
    c = Canvas(512, 320, (0.72, 0.73, 0.76, 1))
    for i in range(14):                                         # speaker grille slots, left
        c.rect(0.05, 0.12 + i * 0.05, 0.36, 0.14 + i * 0.05, (0.15, 0.15, 0.17))
    c.rect(0.43, 0.3, 0.95, 0.72, (0.08, 0.08, 0.1))            # cassette window
    c.rect(0.46, 0.34, 0.92, 0.68, (0.3, 0.27, 0.22))
    for cx in (0.58, 0.8):
        c.circle(cx, 0.51, 0.08, (0.92, 0.92, 0.9))
        c.circle(cx, 0.51, 0.035, (0.1, 0.1, 0.1))
    nm = _ch(rng, ["YAPPER BOY", "YAPPER BOY DELUXE", "YAPPER BOY II"])
    c.text_fit(nm, 0.43, 0.93, 0.54, 0.13, (0.05, 0.05, 0.1), bold=True)
    c.text("SLO-MO VOICE", 0.43, 0.2, 0.065, (0.85, 0.1, 0.1), bold=True)
    c.circle(0.9, 0.13, 0.04, (0.95, 0.1, 0.1))
    c.noise(rng, 0.015)
    body = _ch(rng, [SILVER, SILVER, (0.6, 0.62, 0.66), (0.85, 0.85, 0.87)])
    return {"body": MET(body, 0.4), "trim": P(BLACK, 0.5), "key": P(CHARCOAL, 0.45), "rec": P((0.9, 0.08, 0.08), 0.35),
            "stalk": CHROME(), "foam": ("foam", {"color": (0.05, 0.05, 0.05)}), "face": PR(c.image("yapface"), 0.4)}


@obj("yak_toy", eras=(1, 2), mass=0.06, weight=1.2)
def yak_toy(b, rng, pal):
    """The handheld voice recorder toy: a fat translucent pill with one huge thumb button. Six seconds of
    memory, all of it fart noises."""
    b.sphere(0.045, scale=(0.72, 1.35, 0.42), mat="body", seg=28)
    b.cyl(0.019, 0.016, loc=(0, 0.018, 0.016), mat="btn", seg=24)
    b.cyl(0.0175, 0.004, loc=(0, 0.018, 0.025), mat="btn", seg=24, r2=0.014)
    b.cyl(0.008, 0.01, loc=(0, -0.022, 0.016), mat="btn2", seg=16)
    for i in range(3):
        for j in range(4):
            b.cyl(0.0022, 0.004, loc=(-0.0085 + j * 0.0057, -0.042 + i * 0.006, 0.0105), mat="hole", seg=8)
    b.torus(0.009, 0.0022, loc=(0, 0.064, 0), rot=(0, math.pi / 2, 0), mat="btn2", seg=14)
    b.plane(0.026, 0.012, loc=(0, -0.006, 0.0195), rot=(0.2, 0, 0), mat="label", cuts=2)
    c = Canvas(256, 112, (0.98, 0.95, 0.2, 1))
    c.text_fit(_ch(rng, ["YAK BAKK", "YAK BAKK 2", "YAK BAKK XL"]), 0.06, 0.88, 0.9, 0.5, (0.85, 0.05, 0.3), bold=True)
    c.text_fit("PUSH TO TALK", 0.1, 0.3, 0.8, 0.18, (0.05, 0.05, 0.1), bold=True)
    col = _ch(rng, [(1.0, 0.2, 0.55), (0.1, 0.75, 0.85), (0.55, 0.2, 0.85), (0.4, 0.9, 0.1), (1.0, 0.5, 0.0)])
    return {"body": T(col, 0.12), "btn": P(_ch(rng, [(1.0, 0.9, 0.1), (0.95, 0.1, 0.1), (0.1, 0.4, 0.95)]), 0.3),
            "btn2": P(CHARCOAL, 0.4), "hole": P(BLACK, 0.8), "label": PR(c.image("yak"), 0.35)}


def _clip_cart(rng, name):
    bands = ["THE FROSTED TIPS", "BACKSEAT BOYZ", "LOVEBUZZ 5", "DIAL TONE GIRLS", "MALL RAT", "BOY BAND 5000",
             "GLITTER GLITTER", "SK8R GRL", "DJ DIAL-UP"]
    col = _ch(rng, [(1.0, 0.3, 0.6), (0.2, 0.6, 1.0), (0.6, 0.3, 0.95), (1.0, 0.6, 0.1), (0.3, 0.9, 0.3)])
    c = Canvas(128, 128, (*col, 1))
    c.circle(0.5, 0.55, 0.3, (1, 1, 1, 0.35))
    c.text_fit(_ch(rng, bands), 0.06, 0.92, 0.88, 0.16, (0.05, 0.05, 0.1), bold=True)
    c.text("1 MIN", 0.3, 0.2, 0.12, (1, 1, 1), bold=True)
    return c.image(name)


@obj("clip_player", eras=(2,), mass=0.03, weight=1.2)
def clip_player(b, rng, pal):
    """BIT CLIPZ: a music player the size of a cracker that plays one minute of one song, off a chip the size
    of a stamp. On a keychain clip, with spare song chips rattling around."""
    s = 0.042
    b.box((s, s, 0.014), mat="body", bevel=0.006, seg=3)
    b.cyl(0.011, 0.004, loc=(0, -0.003, 0.008), mat="btn", seg=20)
    b.plane(0.008, 0.008, loc=(0, -0.003, 0.0102), mat="playico", cuts=1)
    b.box((0.026, 0.026, 0.006), loc=(0, s / 2 + 0.002, 0.006), mat="cart", bevel=0.001)
    b.plane(0.022, 0.014, loc=(0, s / 2 + 0.0075, 0.0094), mat="cartlabel", cuts=1)
    b.torus(0.008, 0.0016, loc=(-s / 2 - 0.004, s / 2, 0), rot=(math.pi / 2, 0, 0.7), mat="clip", seg=14)
    b.tube([(-s / 2 - 0.01, s / 2 + 0.005, 0), (-s / 2 - 0.022, s / 2 + 0.02, 0), (-s / 2 - 0.016, s / 2 + 0.035, 0)],
           0.0022, mat="clip", seg=8)
    specs = {"body": pal.body(loud=0.7, clear=0.3), "btn": P(_ch(rng, [WHITE, (1.0, 0.9, 0.1), BLACK]), 0.3),
             "cart": P(CHARCOAL, 0.4), "clip": CHROME(), "cartlabel": PR(_clip_cart(rng, "hc0"), 0.4)}
    c = Canvas(64, 64, (0, 0, 0, 1))
    c.poly([(0.25, 0.15), (0.25, 0.85), (0.85, 0.5)], (1, 1, 1))
    specs["playico"] = PR(c.image("hcplay"), 0.4)
    for k in range(int(rng.integers(2, 4))):
        x, y = 0.04 + 0.022 * k, float(rng.uniform(-0.03, 0.03))
        rz = float(rng.uniform(0, 1))
        b.box((0.026, 0.026, 0.005), loc=(x, y, -0.004), rot=(0, 0, rz), mat="cart", bevel=0.0008)
        b.plane(0.022, 0.022, loc=(x, y, -0.004 + 0.0029), rot=(0, 0, rz), mat=f"cl{k}", cuts=1)
        specs[f"cl{k}"] = PR(_clip_cart(rng, f"hc{k + 1}"), 0.4)
    return specs


def _pod(b, rng, w, h, d, wheel_r, screen_wh, body, back, wheel_ring, screen_color, metal_body=False):
    b.box((w, h, d * 0.55), loc=(0, 0, d * 0.22), mat="body", bevel=min(0.006, w * 0.12), seg=3)
    b.box((w * 0.995, h * 0.995, d * 0.5), loc=(0, 0, -d * 0.2), mat="back", bevel=min(0.007, w * 0.14), seg=3)
    sw, sh = screen_wh
    b.plane(sw, sh, loc=(0, h / 2 - sh / 2 - h * 0.08, d / 2 + E), mat="lcd", cuts=2)
    wy = -h / 2 + wheel_r + h * 0.09
    b.cyl(wheel_r, 0.001, loc=(0, wy, d / 2), mat="wheel", seg=40)
    b.plane(wheel_r * 2, wheel_r * 2, loc=(0, wy, d / 2 + 0.0006), mat="wheelprint", cuts=2)
    b.cyl(wheel_r * 0.38, 0.0016, loc=(0, wy, d / 2 + 0.0007), mat="center", seg=32)
    b.plane(w * 0.5, w * 0.16, loc=(0, -h * 0.18, -d / 2 - 0.0004 - d * 0.0), rot=(math.pi, 0, 0), mat="engrave", cuts=1)
    c = Canvas(256, 80, (0, 0, 0, 1))
    c.text_fit("EYE-POD", 0.08, 0.85, 0.84, 0.6, (1, 1, 1), bold=True)
    c.text_fit("DESIGNED BY A GUY IN A TURTLENECK", 0.04, 0.2, 0.92, 0.12, (1, 1, 1))
    _alpha_from_bg(c, (0, 0, 0))
    c.a[..., :3] = 0.25
    ringc = tuple(float(x) for x in wheel_ring)
    return {"body": body, "back": back, "lcd": ("screen", {"image": _pod_screen(rng, "pod", screen_color), "glow": 0.35}),
            "wheel": P(ringc, 0.5), "wheelprint": PR(_wheel_print(rng, "wheel", ringc, tuple(x * 0.65 for x in ringc)), 0.5,
                                                      alpha_from_image=True),
            "center": P(ringc if metal_body else WHITE, 0.3),
            "engrave": PR(c.image("podengr"), 0.2, alpha_from_image=True)}


def _earbuds(b, rng, start, length=0.2):
    x, y, z = start
    pts = [(x, y, z)]
    ang = float(rng.uniform(1.0, 2.1))
    for i in range(12):
        ang += float(rng.normal(0, 0.35))
        x += math.cos(ang) * length / 12
        y += math.sin(ang) * length / 12
        pts.append((x, y, z + float(rng.normal(0, 0.002))))
    b.tube(pts, 0.0013, mat="buds", seg=6)
    for k in (-1, 1):
        a = ang + k * 0.6
        q = [pts[-1]]
        for i in range(6):
            q.append((q[-1][0] + math.cos(a) * 0.01, q[-1][1] + math.sin(a) * 0.01, z))
            a += float(rng.normal(0, 0.4))
        b.tube(q, 0.0012, mat="buds", seg=6)
        b.sphere(0.0075, loc=q[-1], scale=(1, 1, 0.75), mat="buds", seg=12)
        b.cyl(0.0068, 0.002, loc=(q[-1][0], q[-1][1], q[-1][2] + 0.0055), mat="mesh", seg=12)


@obj("eye_pod", eras=(3,), mass=0.15, weight=1.6)
def eye_pod(b, rng, pal):
    """The white one. Mirror-chrome back, a wheel you rubbed with your thumb, and the white earbuds that
    told the whole bus what you had."""
    specs = _pod(b, rng, 0.062, 0.104, 0.013, 0.0195, (0.044, 0.033), P(WHITE, 0.12, coat=1.0), CHROME(),
                 (0.93, 0.93, 0.92), False)
    _earbuds(b, rng, (0.018, 0.052, 0.002))
    specs.update(buds=P(WHITE, 0.3), mesh=P((0.55, 0.55, 0.58), 0.6))
    return specs


@obj("mini_pod", eras=(3,), mass=0.1, weight=1.3)
def mini_pod(b, rng, pal):
    """The mini: anodized aluminum in five colors, the click wheel printed in the same color as the shell."""
    col = _ch(rng, [(0.85, 0.45, 0.62), (0.3, 0.55, 0.9), (0.5, 0.8, 0.35), (0.85, 0.75, 0.4), (0.78, 0.79, 0.8)])
    tint = tuple(min(1.0, 0.55 + 0.45 * x) for x in col)
    specs = _pod(b, rng, 0.05, 0.091, 0.013, 0.0165, (0.034, 0.024), MET(col, 0.38), MET(col, 0.38), tint, False, True)
    b.box((0.05, 0.004, 0.012), loc=(0, 0.0455, 0), mat="cap", bevel=0.0015)
    b.box((0.05, 0.004, 0.012), loc=(0, -0.0455, 0), mat="cap", bevel=0.0015)
    specs["cap"] = P((0.85, 0.86, 0.88), 0.25)
    return specs


@obj("nano_pod", eras=(3,), mass=0.04, weight=1.3)
def nano_pod(b, rng, pal):
    """The nano: thinner than a pencil, glossy, a color screen the size of a postage stamp. Scratched by
    looking at it."""
    blk = rng.random() < 0.5
    specs = _pod(b, rng, 0.04, 0.09, 0.0069, 0.0145, (0.03, 0.023), P(BLACK if blk else WHITE, 0.08, coat=1.0),
                 CHROME(), (0.12, 0.12, 0.13) if blk else (0.93, 0.93, 0.92), True)
    return specs


@obj("razor_phone", eras=(3,), mass=0.1, weight=1.5)
def razor_phone(b, rng, pal):
    """The razor-thin metal flip phone: etched keypad that glowed blue, the chin at the bottom, and the
    hinge that cracked open with one flick of the wrist."""
    w, h, d = 0.053, 0.098, 0.0069
    b.box((w, h, d), loc=(0, -h / 2, 0), mat="body", bevel=0.0025)
    b.box((w * 0.92, 0.012, d * 1.25), loc=(0, -h + 0.004, -d * 0.12), mat="body", bevel=0.003)    # the chin
    b.plane(w * 0.9, h * 0.8, loc=(0, -h * 0.47, d / 2 + E), mat="keys", cuts=3)
    ang = float(rng.uniform(0.15, 0.5))
    b.frame = Matrix.Rotation(ang, 4, "X")
    b.box((w, h, d), loc=(0, h / 2, 0), mat="body", bevel=0.0025)
    b.plane(w * 0.84, h * 0.6, loc=(0, h * 0.52, d / 2 + E), mat="lcd", cuts=2)
    b.plane(w * 0.2, 0.004, loc=(0, h * 0.9, d / 2 + E), mat="grill", cuts=1)
    b.plane(w * 0.42, w * 0.3, loc=(0, h * 0.6, -d / 2 - E), rot=(math.pi, 0, 0), mat="outlcd", cuts=1)
    b.cyl(0.004, 0.003, loc=(0, h * 0.86, -d / 2 - 0.001), mat="lens", seg=16)
    b.frame = Matrix.Identity(4)
    b.cyl(0.0045, w * 0.94, rot=(0, math.pi / 2, 0), mat="hinge", seg=14)
    b.box((0.012, 0.016, 0.004), loc=(-w / 2 + 0.008, 0.012, -d / 2 - 0.002), mat="hinge", bevel=0.0015)  # antenna bump
    col = _ch(rng, [SILVER, SILVER, SILVER, (0.95, 0.4, 0.62), (0.12, 0.12, 0.14), (0.2, 0.3, 0.6), (0.85, 0.75, 0.55)])
    c = Canvas(256, 320, (*[min(1, x * 0.95) for x in col], 1))
    lab = "123456789*0#"
    for r in range(4):
        for q in range(3):
            x0, y1 = 0.1 + q * 0.28, 0.66 - r * 0.15
            c.rect(x0, y1 - 0.12, x0 + 0.26, y1, (0.3, 0.55, 1.0), soft=0.004)
            c.rect(x0 + 0.01, y1 - 0.11, x0 + 0.25, y1 - 0.01, tuple(min(1, x * 0.9) for x in col))
            c.text(lab[r * 3 + q], x0 + 0.1, y1 - 0.03, 0.06, (0.25, 0.5, 1.0), bold=True)
    c.rect(0.1, 0.72, 0.9, 0.96, (0.3, 0.55, 1.0), soft=0.004)
    c.circle(0.5, 0.84, 0.08, (0.3, 0.55, 1.0), ring=0.012)
    c.text("SEND", 0.14, 0.82, 0.04, (0.2, 0.8, 0.3), bold=True)
    c.text("END", 0.74, 0.82, 0.04, (0.9, 0.2, 0.2), bold=True)
    c.text_fit("RAZZED V3", 0.32, 0.08, 0.36, 0.035, (0.15, 0.15, 0.18))
    keys = c.image("razrkeys")
    s = Canvas(192, 240, (0.05, 0.15, 0.35, 1))
    s.gradient((0.1, 0.35, 0.8), (0.02, 0.05, 0.2))
    s.text_fit(_ch(rng, ["12:47", "1 NEW TEXT", "HELLO MOTTO", "RINGTONE: FROG REMIX", "3 MISSED CALLS"]),
               0.08, 0.6, 0.84, 0.12, (1, 1, 1), bold=True)
    s.text("T-MOBILLY", 0.08, 0.95, 0.06, (1, 1, 1))
    for i in range(4):
        s.rect(0.72 + i * 0.06, 0.88, 0.76 + i * 0.06, 0.9 + i * 0.02, (1, 1, 1))
    o = Canvas(96, 64, (0.02, 0.02, 0.03, 1))
    o.text("12:47", 0.12, 0.7, 0.35, (0.4, 0.7, 1.0), bold=True)
    return {"body": MET(col, 0.28), "hinge": MET(col, 0.35), "keys": PR(keys, 0.25, metal=0.6), "lens": ("lens", {}),
            "lcd": ("screen", {"image": s.image("razrlcd"), "glow": 0.4}), "grill": P(BLACK, 0.6),
            "outlcd": ("screen", {"image": o.image("razrout"), "glow": 0.5})}


@obj("snake_phone", eras=(2,), mass=0.13, weight=1.6)
def snake_phone(b, rng, pal):
    """The brick that never died: blue-grey shell, one big navi key, a green screen with Snake on it.
    Dropped down the stairs, battery flew out, put it back in, still worked."""
    w, h = 0.048, 0.113
    poly = []
    for i in range(40):                     # a lozenge: wide hips, waisted at the screen, fat round top
        a = TAU * i / 40
        x, y = math.cos(a), math.sin(a)
        ww = w / 2 * (1 - 0.06 * math.cos(2 * math.asin(max(-1, min(1, y)))))
        poly.append((ww * (abs(x) ** 0.55) * (1 if x >= 0 else -1), h / 2 * (abs(y) ** 0.7) * (1 if y >= 0 else -1)))
    b.extrude(poly, 0.012, loc=(0, 0, 0.006), mat="cover", bevel=0.003)
    b.extrude(poly, 0.01, loc=(0, 0, -0.005), scale=(0.98, 0.98, 1), mat="back", bevel=0.003)
    b.plane(0.033, 0.024, loc=(0, 0.023, 0.0121 + E), mat="lcd", cuts=2)
    b.extrude(ellipse(0.03, 0.012, 20), 0.004, loc=(0, -0.004, 0.0125), mat="navi", bevel=0.0012)
    b.plane(0.036, 0.04, loc=(0, -0.033, 0.0121 + E), mat="keys", cuts=2)
    b.plane(0.02, 0.006, loc=(0, 0.047, 0.0121 + E), mat="brand", cuts=1)
    s = Canvas(168, 120, (0.62, 0.72, 0.42, 1))
    ink = (0.08, 0.12, 0.05)
    s.rect(0.03, 0.04, 0.97, 0.85, ink)
    s.rect(0.05, 0.06, 0.95, 0.83, (0.62, 0.72, 0.42))
    x, y = 0.2, 0.3
    path = [(x, y)]
    for d in [(1, 0)] * 6 + [(0, 1)] * 3 + [(1, 0)] * 5 + [(0, -1)] * 2:
        x, y = x + d[0] * 0.04, y + d[1] * 0.07
        path.append((x, y))
    for (px, py) in path:
        s.rect(px - 0.018, py - 0.03, px + 0.018, py + 0.03, ink)
    s.rect(0.78, 0.6, 0.81, 0.65, ink)
    s.text(str(int(rng.integers(30, 999))).rjust(4, "0"), 0.05, 0.98, 0.11, ink, bold=True)
    k = Canvas(160, 192, (0.12, 0.13, 0.15, 1))
    lab = "123456789*0#"
    k.rect(0.05, 0.84, 0.3, 0.98, (0.8, 0.82, 0.85), soft=0.03)
    k.text("C", 0.13, 0.95, 0.08, (0.1, 0.1, 0.1), bold=True)
    for r in range(4):
        for q in range(3):
            cx, cy = 0.2 + q * 0.3, 0.72 - r * 0.19
            k.circle(cx, cy, 0.07, (0.8, 0.82, 0.85))
            k.text(lab[r * 3 + q], cx - 0.04, cy + 0.04, 0.07, (0.1, 0.1, 0.1), bold=True)
    br = Canvas(128, 40, (0.25, 0.32, 0.45, 1))
    br.text_fit("NO-KIDDING", 0.06, 0.8, 0.88, 0.55, (0.9, 0.92, 0.95), bold=True)
    cover = _ch(rng, [(0.25, 0.32, 0.45), (0.25, 0.32, 0.45), (0.3, 0.3, 0.33), (0.6, 0.1, 0.12), (0.15, 0.35, 0.6)])
    return {"cover": P(cover, 0.42), "back": P((0.18, 0.2, 0.24), 0.5), "navi": P((0.15, 0.25, 0.55), 0.3),
            "lcd": PR(s.image("snake"), 0.2), "keys": PR(k.image("3310keys"), 0.4), "brand": PR(br.image("nk"), 0.3)}


@obj("sidekick_phone", eras=(3,), mass=0.18, weight=1.2)
def sidekick_phone(b, rng, pal):
    """The swivel-screen texter: the screen flipped around to reveal a full keyboard, a trackball, and the
    first time you could AIM from the back of algebra."""
    W, H = 0.13, 0.064
    poly = rounded_rect(W, H, 0.026, 6)
    b.extrude(poly, 0.012, loc=(0, 0, 0), mat="base", bevel=0.003)
    b.plane(W * 0.72, H * 0.78, loc=(-0.006, 0, 0.006 + E), mat="kbd", cuts=3)
    for sx in (-1, 1):
        b.box((0.012, 0.012, 0.004), loc=(sx * 0.055, H / 2 - 0.002, 0.004), mat="accent", bevel=0.0015)
    ang = float(rng.uniform(0.35, 0.95))
    b.frame = Matrix.Translation((-W / 2 + 0.02, H / 2 - 0.02, 0.012)) @ Matrix.Rotation(ang, 4, "Z")
    b.extrude(poly, 0.009, loc=(W / 2 - 0.02, -H / 2 + 0.02, 0), mat="lid", bevel=0.003)
    b.plane(W * 0.62, H * 0.7, loc=(W / 2 - 0.022, -H / 2 + 0.02, 0.0046 + E), mat="lcd", cuts=2)
    b.sphere(0.0055, loc=(W / 2 - 0.02 + 0.052, -H / 2 + 0.02, 0.005), mat="ball", seg=14)
    b.box((0.006, 0.02, 0.003), loc=(W / 2 - 0.02 - 0.054, -H / 2 + 0.02, 0.005), mat="accent", bevel=0.001)
    b.frame = Matrix.Identity(4)
    b.cyl(0.006, 0.026, loc=(-W / 2 + 0.02, H / 2 - 0.02, 0.006), mat="accent", seg=16)
    k = Canvas(384, 192, (0.12, 0.12, 0.14, 1))
    rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM.,"]
    for r, row in enumerate(rows):
        for i, ch in enumerate(row):
            x0, y1 = 0.04 + r * 0.03 + i * 0.093, 0.92 - r * 0.28
            k.rect(x0, y1 - 0.22, x0 + 0.08, y1, (0.82, 0.84, 0.86), soft=0.01)
            k.text(ch, x0 + 0.025, y1 - 0.06, 0.1, (0.1, 0.1, 0.1), bold=True)
    k.rect(0.3, 0.02, 0.7, 0.12, (0.82, 0.84, 0.86), soft=0.01)
    s = Canvas(256, 160, (0.9, 0.92, 0.95, 1))
    s.rect(0, 0.84, 1, 1, (0.2, 0.2, 0.25))
    s.text("SIDEKICKED", 0.04, 0.97, 0.1, (0.6, 1.0, 0.2), bold=True)
    for i, line in enumerate(["XXSK8RGRLXX: WYA", "ME: ALGEBRA LOL", "XXSK8RGRLXX: BRB", "ME: G2G TEACHER"]):
        s.text_fit(line, 0.04, 0.78 - i * 0.18, 0.92, 0.1, (0.1, 0.1, 0.3) if i % 2 else (0.6, 0.05, 0.3), bold=True)
    acc = _ch(rng, [(0.6, 1.0, 0.1), (1.0, 0.3, 0.6), (0.2, 0.7, 1.0), (1.0, 0.55, 0.1)])
    return {"base": P(CHARCOAL, 0.4), "lid": P(_ch(rng, [SILVER, (0.85, 0.85, 0.88), (0.2, 0.2, 0.22), acc]), 0.3, coat=0.5),
            "kbd": PR(k.image("skkbd"), 0.4), "accent": P(acc, 0.35), "ball": T((0.85, 0.9, 1.0), 0.05),
            "lcd": ("screen", {"image": s.image("sklcd"), "glow": 0.35})}


@obj("crackberry", eras=(3,), mass=0.14, weight=1.3)
def crackberry(b, rng, pal):
    """The email phone: a keyboard of forty tiny chiclets, a scroll wheel on the side, a red light blinking
    at dinner. Thumbs never recovered."""
    w, h, d = 0.062, 0.112, 0.017
    b.box((w, h, d), mat="body", bevel=0.007, seg=3)
    b.plane(0.05, 0.04, loc=(0, 0.022, d / 2 + E), mat="lcd", cuts=2)
    b.plane(0.054, 0.046, loc=(0, -0.03, d / 2 + E), mat="kbd", cuts=3)
    b.cyl(0.006, 0.006, loc=(w / 2 + 0.001, 0.012, 0), rot=(0, math.pi / 2, 0), mat="wheel", seg=18)
    b.box((0.012, 0.004, 0.006), loc=(0.016, h / 2 + 0.001, 0), mat="wheel", bevel=0.001)
    b.cyl(0.0018, 0.001, loc=(0.022, 0.05, d / 2), mat="led", seg=10)
    k = Canvas(256, 224, (0.08, 0.08, 0.09, 1))
    rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    for r, row in enumerate(rows):
        for i, ch in enumerate(row):
            cx = 0.07 + i * 0.096 + r * 0.03
            cy = 0.85 - r * 0.24
            k.circle(cx, cy, 0.04, (0.86, 0.86, 0.84))
            k.text(ch, cx - 0.017, cy + 0.03, 0.055, (0.1, 0.1, 0.1), bold=True)
    k.rect(0.3, 0.06, 0.7, 0.14, (0.86, 0.86, 0.84), soft=0.02)
    s = Canvas(256, 200, (0.95, 0.96, 0.98, 1))
    s.rect(0, 0.86, 1, 1, (0.1, 0.15, 0.3))
    s.text("CRACKBERRY", 0.04, 0.97, 0.09, (1, 1, 1), bold=True)
    for i, line in enumerate(["RE: RE: RE: TPS REPORT", "FWD: FWD: FUNNY.PPS", "Y U NO REPLY", "SENT FROM MY CRACKBERRY"]):
        s.rect(0.04, 0.78 - i * 0.19 - 0.12, 0.08, 0.78 - i * 0.19 - 0.04, (0.95, 0.75, 0.1))
        s.text_fit(line, 0.11, 0.78 - i * 0.19, 0.86, 0.08, (0.05, 0.05, 0.1), bold=True)
    return {"body": P(_ch(rng, [BLACK, CHARCOAL, (0.15, 0.2, 0.35), SILVER]), 0.35, coat=0.3),
            "lcd": ("screen", {"image": s.image("bblcd"), "glow": 0.35}), "kbd": PR(k.image("bbkbd"), 0.35),
            "wheel": P(SILVER, 0.4), "led": P((1.0, 0.05, 0.05), 0.3, glow=3.0)}


@obj("pda", eras=(2,), mass=0.15, weight=1.2)
def pda(b, rng, pal):
    """The stylus organizer: a green-grey screen you wrote on in a made-up alphabet, four round app buttons,
    and a stylus that was lost by Tuesday."""
    w, h, d = 0.08, 0.118, 0.016
    b.box((w, h, d), mat="body", bevel=0.006, seg=3)
    b.plane(0.06, 0.062, loc=(0, 0.018, d / 2 + E), mat="lcd", cuts=2)
    b.plane(0.06, 0.018, loc=(0, -0.025, d / 2 + E), mat="graf", cuts=2)
    for i, x in enumerate((-0.03, -0.015, 0.015, 0.03)):
        b.cyl(0.0055, 0.003, loc=(x, -0.046, d / 2), mat="btn", seg=16)
    b.box((0.012, 0.008, 0.003), loc=(0, -0.046, d / 2), mat="btn", bevel=0.0012)
    b.cyl(0.0025, 0.11, loc=(w / 2 + 0.002, 0, d * 0.25), rot=(math.pi / 2, 0, 0), mat="stylus", seg=10)
    out = float(rng.uniform(0.02, 0.08))
    b.cyl(0.0024, 0.105, loc=(w / 2 + 0.03, -0.01 + out, -d / 2 + 0.003), rot=(math.pi / 2, 0, float(rng.normal(0, 0.15))),
          mat="stylus", seg=10, r2=0.0012)
    s = Canvas(256, 256, (0.66, 0.72, 0.6, 1))
    ink = (0.08, 0.1, 0.08)
    s.rect(0, 0.88, 0.45, 1, ink)
    s.text("DATEBOOK", 0.03, 0.97, 0.07, (0.66, 0.72, 0.6), bold=True)
    for i, (t, ev) in enumerate([("8:00", "STANDUP-ISH"), ("9:00", ""), ("10:00", "SYNERGY MTG"), ("12:00", "LUNCH"),
                                 ("1:00", "Y2K PREP"), ("3:00", "")]):
        y = 0.82 - i * 0.12
        s.text(t, 0.04, y, 0.06, ink, bold=True)
        s.rect(0.25, y - 0.075, 0.97, y - 0.07, ink)
        s.text_fit(ev, 0.27, y, 0.7, 0.06, ink)
    g = Canvas(256, 80, (0.75, 0.77, 0.72, 1))
    g.rect(0.2, 0.08, 0.8, 0.92, (0.66, 0.72, 0.6))
    g.rect(0.495, 0.1, 0.505, 0.9, ink)
    g.text("ABC", 0.24, 0.3, 0.2, ink)
    g.text("123", 0.62, 0.3, 0.2, ink)
    for i in range(2):
        g.circle(0.09, 0.3 + i * 0.4, 0.1, ink, ring=0.02)
        g.circle(0.91, 0.3 + i * 0.4, 0.1, ink, ring=0.02)
    br = _ch(rng, ["SWEATY PALM V", "SWEATY PALM III", "SWEATY PALM PRO"])
    g.text_fit(br, 0.22, 0.98, 0.56, 0.1, (0.3, 0.3, 0.3))
    s.text_fit(br, 0.5, 0.97, 0.47, 0.07, ink)
    return {"body": MET(_ch(rng, [(0.55, 0.56, 0.58), (0.35, 0.36, 0.38), (0.6, 0.62, 0.66)]), 0.45),
            "lcd": PR(s.image("palmlcd"), 0.2), "graf": PR(g.image("palmgraf"), 0.5),
            "btn": P((0.25, 0.26, 0.28), 0.4), "stylus": MET(SILVER, 0.25)}


def _snapshot(rng, name):
    """An instant print: the white frame with the fat chin, a washed-out flash photo, sharpie on the chin."""
    c = Canvas(176, 212, (0.96, 0.95, 0.92, 1))
    x0, x1, y0, y1 = 0.06, 0.94, 0.25, 0.95
    scene = int(rng.integers(0, 4))
    if scene == 0:          # living room, red eye
        c.rect(x0, y0, x1, y1, (0.55, 0.4, 0.25))
        c.rect(x0, y0, x1, 0.45, (0.35, 0.25, 0.2))
        c.circle(0.5, 0.65, 0.16, (0.95, 0.75, 0.6))
        c.rect(0.33, y0, 0.67, 0.5, _rgb(rng.uniform(0.1, 0.9, 3)))
        for sx in (-1, 1):
            c.circle(0.5 + sx * 0.06, 0.68, 0.025, (1, 1, 1))
            c.circle(0.5 + sx * 0.06, 0.68, 0.014, (0.95, 0.05, 0.05))
        c.rect(0.4, 0.58, 0.6, 0.6, (0.4, 0.1, 0.1))
    elif scene == 1:        # birthday cake
        c.rect(x0, y0, x1, y1, (0.15, 0.12, 0.1))
        c.rect(0.25, 0.32, 0.75, 0.55, (0.95, 0.8, 0.85))
        for i in range(5):
            c.rect(0.3 + i * 0.1, 0.55, 0.32 + i * 0.1, 0.66, (0.4, 0.6, 1.0))
            c.circle(0.31 + i * 0.1, 0.69, 0.02, (1.0, 0.85, 0.3))
    elif scene == 2:        # backyard, the dog
        c.rect(x0, y0, x1, y1, (0.5, 0.75, 0.95))
        c.rect(x0, y0, x1, 0.55, (0.3, 0.6, 0.2))
        c.circle(0.45, 0.48, 0.12, (0.65, 0.45, 0.25))
        c.circle(0.6, 0.58, 0.07, (0.65, 0.45, 0.25))
        c.circle(0.62, 0.6, 0.012, (0, 0, 0))
    else:                   # thumb over the lens
        c.rect(x0, y0, x1, y1, (0.3, 0.3, 0.35))
        c.circle(0.15, 0.6, 0.3, (0.9, 0.6, 0.5, 0.9))
    c.rect(x0, y0, x1, y1, (1, 1, 0.9, 0.18))
    ink = _ch(rng, [(0.05, 0.05, 0.05), (0.1, 0.1, 0.45), (0.7, 0.05, 0.1)])
    c.text_fit(_ch(rng, ["XMAS 89", "SHAKE IT", "DONT SHOW MOM", "TANYAS B-DAY", "SUMMER 94", "LOL WHO", "RUFUS!", "1997"]),
               0.1, 0.19, 0.8, 0.09, ink, bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


@obj("instant_camera", eras=(0, 1, 2), mass=0.6, weight=1.3, hero=(0, -1, 0))
def instant_camera(b, rng, pal):
    """The boxy instant camera: a black wedge with a lens like a porthole, a flip-up flash, a sunset stripe
    down the face and a fresh print sliding out of its mouth."""
    W, D, H = 0.12, 0.15, 0.1
    prof = [(-D / 2, 0.0), (D / 2, 0.0), (D / 2, H * 0.35), (-D / 2 + 0.03, H), (-D / 2, H)]
    b.extrude(prof, W, rot=(math.pi / 2, 0, math.pi / 2), mat="body", bevel=0.006)
    fy = -D / 2
    b.cyl(0.026, 0.02, loc=(-0.012, fy - 0.008, H * 0.58), rot=(math.pi / 2, 0, 0), mat="barrel", seg=28)
    b.cyl(0.018, 0.004, loc=(-0.012, fy - 0.019, H * 0.58), rot=(math.pi / 2, 0, 0), mat="lens", seg=24)
    b.box((0.024, 0.02, 0.016), loc=(0.032, fy + 0.01, H + 0.004), mat="body", bevel=0.003)
    b.plane(0.02, 0.012, loc=(0.032, fy - E, H + 0.004), rot=(math.pi / 2, 0, 0), mat="flash", cuts=1)
    b.box((0.03, 0.016, 0.014), loc=(-0.03, fy + 0.045, H - 0.002), mat="body", bevel=0.003)   # viewfinder
    b.cyl(0.006, 0.006, loc=(0.045, fy + 0.01, H * 0.62), rot=(math.pi / 2, 0, 0), mat="red", seg=16)
    b.plane(0.016, H * 0.5, loc=(-0.045, fy - E, H * 0.38), rot=(math.pi / 2, 0, 0), mat="stripe", cuts=2)
    b.plane(W * 0.7, 0.014, loc=(0, fy - E, H * 0.14), rot=(math.pi / 2, 0, 0), mat="brand", cuts=1)
    b.box((0.09, 0.006, 0.006), loc=(0, fy - 0.001, H * 0.27), mat="slot")
    out = float(rng.uniform(0.0, 0.03))
    b.frame = Matrix.Translation((0, fy - 0.004 + 0.03 - out, H * 0.27)) @ Matrix.Rotation(0.22, 4, "X")
    b.box((0.079, 0.096, 0.0012), loc=(0, -0.048, 0), mat="photoback")
    b.plane(0.079, 0.096, loc=(0, -0.048, 0.0007), rot=(0, 0, math.pi), mat="photo", cuts=2)
    b.frame = Matrix.Identity(4)
    st = Canvas(32, 256, (0, 0, 0, 1))
    st.gradient((1.0, 0.55, 0.1), (0.55, 0.15, 0.7))
    for i, col in enumerate([(1.0, 0.85, 0.2), (1.0, 0.45, 0.2), (0.95, 0.2, 0.45), (0.55, 0.2, 0.8)]):
        st.rect(0, 1 - (i + 1) * 0.25, 1, 1 - i * 0.25, col)
    br = Canvas(320, 40, (0.05, 0.05, 0.05, 1))
    br.text_fit(_ch(rng, ["POLARVOID 600", "POLARVOID ONE STEP-ISH", "POLARVOID SUN 666"]), 0.05, 0.85, 0.9, 0.6,
                (0.9, 0.9, 0.9), bold=True)
    return {"body": P(_ch(rng, [BLACK, BLACK, (0.1, 0.1, 0.12), (0.85, 0.85, 0.82)]), 0.55, texture=0.6),
            "barrel": P(BLACK, 0.4), "lens": ("lens", {}), "flash": T((0.95, 0.95, 0.95), 0.4),
            "red": P((0.9, 0.08, 0.08), 0.3), "stripe": PR(st.image("pvstripe"), 0.4), "brand": PR(br.image("pvbrand"), 0.4),
            "slot": P((0.02, 0.02, 0.02), 0.8), "photoback": P((0.08, 0.08, 0.08), 0.6),
            "photo": PR(_snapshot(rng, "pvph"), 0.35)}


@obj("instant_photos", eras=(0, 1, 2), mass=0.05, weight=1.3)
def instant_photos(b, rng, pal):
    """A loose fan of instant prints: square-ish photo, fat white chin, sharpie caption. Shook them anyway."""
    specs = {"back": P((0.07, 0.07, 0.07), 0.6)}
    for k in range(int(rng.integers(2, 5))):
        x, y = (float(v) for v in rng.normal(0, 0.018, 2))
        rz = float(rng.uniform(-0.6, 0.6))
        z = k * 0.0016
        b.box((0.088, 0.107, 0.0012), loc=(x, y, z), rot=(0, 0, rz), mat="back")
        b.plane(0.088, 0.107, loc=(x, y, z + 0.0007), rot=(0, 0, rz), mat=f"p{k}", cuts=2)
        specs[f"p{k}"] = PR(_snapshot(rng, f"ph{k}"), 0.3)
    return specs


@obj("fruit_computer", eras=(2,), mass=15.0, weight=1.1, big=True, hero=(0, -1, 0))
def fruit_computer(b, rng, pal):
    """The translucent all-in-one: candy-colored see-through back with the tube showing inside, a handle on
    top, a hockey-puck mouse somewhere. Came in five fruits. Nobody bought a printer that matched."""
    W, Hh = 0.38, 0.37
    zc = 0.21
    b.box((W, 0.05, Hh), loc=(0, 0, zc), mat="ice", bevel=0.03, seg=3)
    b.box((W * 0.99, 0.052, 0.1), loc=(0, -0.001, 0.07), mat="fruit", bevel=0.02, seg=3)
    b.plane(0.29, 0.22, loc=(0, -0.0265, zc + 0.04), rot=(math.pi / 2, 0, 0), mat="screen", cuts=8)
    b.box((0.31, 0.006, 0.24), loc=(0, -0.024, zc + 0.04), mat="bezel", bevel=0.01)
    for sx in (-1, 1):
        b.plane(0.06, 0.035, loc=(sx * 0.13, -0.0275, 0.075), rot=(math.pi / 2, 0, 0), mat="grille", cuts=1)
    b.box((0.13, 0.004, 0.012), loc=(0, -0.027, 0.06), mat="tray", bevel=0.002)
    b.plane(0.05, 0.012, loc=(0, -0.0275, 0.097), rot=(math.pi / 2, 0, 0), mat="logo", cuts=1)
    rings = []
    for j, (t, s, zo) in enumerate(((0.02, 1.0, 0.0), (0.12, 0.92, 0.0), (0.24, 0.72, 0.02), (0.33, 0.5, 0.04),
                                    (0.37, 0.36, 0.05))):
        pts = rounded_rect(W * s * 0.98, Hh * s * 0.98, 0.05 * s + 0.01, 5)
        rings.append([(x, t, zc + y + zo) for x, y in pts])
    b.loft(rings, mat="fruit")
    b.cyl(0.15, 0.25, r2=0.06, loc=(0, 0.15, zc + 0.03), rot=(-math.pi / 2, 0, 0), mat="tube", seg=4)
    b.tube([(-0.09, 0.03, zc + Hh / 2 - 0.01), (-0.08, 0.07, zc + Hh / 2 + 0.03), (0.08, 0.07, zc + Hh / 2 + 0.03),
            (0.09, 0.03, zc + Hh / 2 - 0.01)], 0.012, mat="fruit", seg=10)
    b.box((0.16, 0.2, 0.02), loc=(0, 0.1, 0.0), mat="fruit", bevel=0.008)
    fruit = _ch(rng, [(0.0, 0.55, 0.65), (1.0, 0.45, 0.05), (0.5, 0.15, 0.6), (0.45, 0.8, 0.1), (0.9, 0.1, 0.25),
                      (0.15, 0.35, 0.85)])
    s = Canvas(320, 240, (0.45, 0.5, 0.75, 1))
    s.gradient((0.35, 0.55, 0.85), (0.6, 0.45, 0.8))
    s.rect(0, 0.93, 1, 1, (0.92, 0.92, 0.92))
    s.text("FILE EDIT VIEW SPECIAL", 0.08, 0.99, 0.05, (0.1, 0.1, 0.1))
    s.rect(0.82, 0.72, 0.95, 0.85, (0.75, 0.75, 0.78))
    s.text("HD", 0.85, 0.69, 0.05, (1, 1, 1), bold=True)
    s.rect(0.2, 0.25, 0.7, 0.75, (0.92, 0.92, 0.92))
    s.rect(0.2, 0.69, 0.7, 0.75, (0.6, 0.6, 0.65))
    s.text_fit("WELCOME TO SMAC OS 8.6", 0.23, 0.6, 0.44, 0.07, (0.1, 0.1, 0.1), bold=True)
    s.text_fit("THINK DIFFERENTER", 0.23, 0.45, 0.44, 0.06, (0.1, 0.1, 0.4))
    s.noise(rng, 0.01)
    g = Canvas(96, 64, (0.1, 0.1, 0.12, 1))
    for i in range(6):
        for j in range(10):
            g.circle(0.07 + j * 0.095, 0.15 + i * 0.14, 0.035, (0.0, 0.0, 0.0))
    lg = Canvas(160, 40, (0.85, 0.87, 0.9, 1))
    lg.text_fit("ISMACK", 0.1, 0.85, 0.8, 0.65, (0.25, 0.25, 0.3), bold=True)
    _alpha_from_bg(lg, (0.85, 0.87, 0.9))
    return {"ice": T((0.88, 0.9, 0.93), 0.18), "fruit": T(fruit, 0.12), "bezel": P((0.82, 0.84, 0.86), 0.3),
            "screen": ("screen", {"image": s.image("imacscr"), "glow": 0.3, "crack_scale": 6.0}),
            "grille": PR(g.image("imacgr"), 0.6), "tray": P((0.6, 0.62, 0.65), 0.3), "tube": P(CHARCOAL, 0.6),
            "logo": PR(lg.image("imaclogo"), 0.3, alpha_from_image=True)}


def _cow_print(rng, name, side=0):
    c = Canvas(384, 320, (0.96, 0.95, 0.92, 1))
    for _ in range(int(rng.integers(6, 10))):
        cx, cy = rng.uniform(0, 1, 2)
        r = float(rng.uniform(0.07, 0.17))
        pts = []
        for k in range(14):
            a = TAU * k / 14
            rr = r * float(rng.uniform(0.6, 1.3))
            pts.append((float(cx) + rr * math.cos(a) * 0.85, float(cy) + rr * math.sin(a)))
        c.poly(tex._smooth(pts + [pts[0]], 4), (0.04, 0.04, 0.04))
    ink = (0.05, 0.05, 0.05)
    if side == 0:
        c.rect(0.08, 0.66, 0.92, 0.86, (0.96, 0.95, 0.92))
        c.text_fit("MOOTEWAY 2000", 0.11, 0.83, 0.78, 0.15, ink, bold=True)
        c.rect(0.15, 0.2, 0.85, 0.34, (0.96, 0.95, 0.92))
        c.text_fit("YOU GOT A FRIEND IN THE BIZ-NESS", 0.17, 0.31, 0.66, 0.08, ink, bold=True)
    else:
        c.rect(0.3, 0.55, 0.7, 0.95, (0.96, 0.95, 0.92))
        c.poly([(0.5, 0.92), (0.38, 0.75), (0.46, 0.75), (0.46, 0.6), (0.54, 0.6), (0.54, 0.75), (0.62, 0.75)], ink)
        c.text("THIS SIDE UP", 0.32, 0.56, 0.05, ink, bold=True)
        c.rect(0.08, 0.06, 0.6, 0.24, (0.96, 0.95, 0.92))
        c.text_fit("PENTIUMMY II 400MHZ", 0.1, 0.21, 0.48, 0.06, ink, bold=True)
        c.text_fit("SHIPPED FROM SOUTH DAKOTA-ISH", 0.1, 0.12, 0.48, 0.05, ink)
    c.noise(rng, 0.02)
    return c.image(name)


@obj("cow_box", eras=(1, 2), mass=1.5, weight=1.0, big=True, hero=(0, -1, 0))
def cow_box(b, rng, pal):
    """The computer box with cow spots: black-and-white holstein cardboard, flaps open, the most exciting
    box that ever came to the house."""
    W, D, H = 0.3, 0.24, 0.24
    t = 0.004
    b.box((W, D, t), loc=(0, 0, t / 2), mat="inside")
    for sx in (-1, 1):
        b.box((t, D, H), loc=(sx * (W / 2 - t / 2), 0, H / 2), mat="inside")
        b.plane(D, H, loc=(sx * (W / 2 + E), 0, H / 2), rot=(math.pi / 2, 0, sx * math.pi / 2), mat="side", cuts=3)
    for sy in (-1, 1):
        b.box((W, t, H), loc=(0, sy * (D / 2 - t / 2), H / 2), mat="inside")
        b.plane(W, H, loc=(0, sy * (D / 2 + E), H / 2), rot=(math.pi / 2, 0, 0 if sy < 0 else math.pi), mat="front",
                cuts=3)
    for sy in (-1, 1):
        a = float(rng.uniform(0.3, 1.2))
        b.frame = Matrix.Translation((0, sy * D / 2, H)) @ Matrix.Rotation(math.pi / 2 - sy * a, 4, "X")
        b.box((W, D / 2, t), loc=(0, D / 4, 0), mat="flap")
        b.frame = Matrix.Identity(4)
    for sx in (-1, 1):
        a = float(rng.uniform(0.2, 1.4))
        b.frame = Matrix.Translation((sx * W / 2, 0, H)) @ Matrix.Rotation(-(math.pi / 2 - sx * a), 4, "Y")
        b.box((W * 0.45, D, t), loc=(W * 0.225, 0, 0), mat="flap")
        b.frame = Matrix.Identity(4)
    b.box((W * 0.7, D * 0.6, 0.06), loc=(0, 0, 0.035), mat="foam")
    return {"inside": ("cardboard", {"color": (0.62, 0.48, 0.32)}), "front": PR(_cow_print(rng, "cowf", 0), 0.85),
            "side": PR(_cow_print(rng, "cows", 1), 0.85), "flap": PR(_cow_print(rng, "cowt", 2), 0.85),
            "foam": ("foam", {"color": (0.95, 0.95, 0.95)})}


@obj("beige_tower", eras=(1, 2), mass=9.0, weight=1.0, big=True, hero=(0, -1, 0))
def beige_tower(b, rng, pal):
    """The beige tower: two drive bays, a floppy slot, a TURBO button nobody understood and a red LED
    display bragging about megahertz."""
    W, D, H = 0.19, 0.42, 0.42
    b.box((W, D, H), loc=(0, 0, H / 2), mat="case", bevel=0.006)
    fy = -D / 2
    b.box((W * 1.02, 0.02, H * 1.0), loc=(0, fy - 0.006, H / 2), mat="bezel", bevel=0.008)
    fy -= 0.016
    for i in range(2):
        z = H - 0.06 - i * 0.05
        b.box((0.15, 0.006, 0.042), loc=(0, fy - 0.002, z), mat="bay", bevel=0.002)
        if i == 0:
            b.box((0.12, 0.004, 0.006), loc=(0, fy - 0.005, z - 0.004), mat="slot")
            b.box((0.012, 0.004, 0.006), loc=(0.055, fy - 0.006, z - 0.012), mat="btn", bevel=0.001)
            b.cyl(0.0025, 0.003, loc=(-0.06, fy - 0.006, z - 0.012), rot=(math.pi / 2, 0, 0), mat="led_g", seg=10)
    z = H - 0.17
    b.box((0.105, 0.006, 0.028), loc=(0.02, fy - 0.002, z), mat="bay", bevel=0.002)
    b.box((0.085, 0.004, 0.004), loc=(0.02, fy - 0.005, z + 0.004), mat="slot")
    b.box((0.014, 0.004, 0.006), loc=(0.05, fy - 0.006, z - 0.008), mat="btn", bevel=0.001)
    b.box((0.03, 0.01, 0.03), loc=(-0.05, fy - 0.004, 0.12), mat="btn", bevel=0.004)          # POWER
    b.box((0.014, 0.008, 0.01), loc=(-0.05, fy - 0.004, 0.17), mat="btn", bevel=0.002)         # TURBO
    b.box((0.012, 0.008, 0.01), loc=(-0.05, fy - 0.004, 0.19), mat="btn", bevel=0.002)         # RESET
    b.cyl(0.006, 0.01, loc=(0.05, fy - 0.004, 0.19), rot=(math.pi / 2, 0, 0), mat="lock", seg=16)
    b.plane(0.06, 0.028, loc=(0.035, fy - 0.0025, 0.155), rot=(math.pi / 2, 0, 0), mat="mhz", cuts=1)
    b.plane(0.05, 0.05, loc=(0.045, fy - 0.0025, 0.07), rot=(math.pi / 2, 0, 0), mat="sticker", cuts=1)
    b.plane(W * 0.8, 0.05, loc=(0, fy - 0.0025, 0.03), rot=(math.pi / 2, 0, 0), mat="vent", cuts=1)
    m = Canvas(192, 96, (0.08, 0.08, 0.08, 1))
    m.rect(0.04, 0.3, 0.6, 0.95, (0.15, 0.02, 0.02))
    m.text(_ch(rng, ["66", "33", "99", "100", "133"]), 0.07, 0.88, 0.5, (1.0, 0.12, 0.08), bold=True)
    m.text("MHZ", 0.64, 0.75, 0.2, (0.85, 0.85, 0.85), bold=True)
    m.circle(0.72, 0.18, 0.06, (0.2, 1.0, 0.2))
    m.circle(0.9, 0.18, 0.06, (1.0, 0.6, 0.1))
    m.text("PWR HDD", 0.04, 0.24, 0.12, (0.85, 0.85, 0.85))
    mh = m.image("mhz")
    mh["lcd"] = True
    s = Canvas(128, 128, (0.92, 0.92, 0.92, 1))
    s.rect(0.03, 0.03, 0.97, 0.97, (0.1, 0.2, 0.6))
    s.circle(0.5, 0.55, 0.36, (1, 1, 1), ring=0.05)
    s.text_fit("PENTIUMMY", 0.12, 0.7, 0.76, 0.14, (1, 1, 1), bold=True)
    s.text_fit("INTELLIGENT", 0.15, 0.5, 0.7, 0.09, (1, 1, 1))
    s.text_fit("INSIDE-ISH", 0.18, 0.38, 0.64, 0.09, (1, 1, 1))
    s.text_fit("WINDOZE 95 READY", 0.08, 0.13, 0.84, 0.07, (1.0, 0.85, 0.1), bold=True)
    v = Canvas(256, 48, (0.82, 0.8, 0.7, 1))
    for i in range(16):
        v.rect(0.03 + i * 0.06, 0.2, 0.06 + i * 0.06, 0.8, (0.2, 0.2, 0.18))
    case = _ch(rng, [BEIGE, BEIGE, YELLOWED, (0.88, 0.86, 0.78)])
    return {"case": P(case, 0.5), "bezel": P(case, 0.45), "bay": P(tuple(x * 0.95 for x in case), 0.45),
            "slot": P(BLACK, 0.8), "btn": P(tuple(x * 0.85 for x in case), 0.45), "led_g": P((0.1, 1.0, 0.2), 0.3, glow=2.0),
            "lock": CHROME(), "mhz": PR(mh, 0.2, glow=1.2), "sticker": PR(s.image("pentium"), 0.3),
            "vent": PR(v.image("towervent"), 0.6)}


@obj("cdr_spindle", eras=(2, 3), mass=0.6, weight=1.1)
def cdr_spindle(b, rng, pal):
    """The cake box of blank discs: black base, a post up the middle, a stack of shiny CD-Rs and a smoky
    clear dome that never screwed back on straight."""
    b.cyl(0.07, 0.012, loc=(0, 0, 0.006), mat="base", seg=48)
    b.cyl(0.0068, 0.13, loc=(0, 0, 0.07), mat="base", seg=16)
    n = float(rng.uniform(0.015, 0.07))
    b.lathe([(0.0075, 0.012), (0.06, 0.012), (0.06, 0.012 + n), (0.0075, 0.012 + n)], mat="discs", seg=48)
    for i in range(int(n / 0.004)):
        b.torus(0.06, 0.0004, loc=(0, 0, 0.013 + i * 0.004), mat="edge", seg=32, rseg=4)
    b.plane(0.12, 0.12, loc=(0, 0, 0.012 + n + E), mat="top", cuts=6)
    lid_off = rng.random() < 0.5
    if lid_off:
        b.frame = Matrix.Translation((0.11, 0.02, 0.0)) @ Matrix.Rotation(math.pi / 2 - 0.15, 4, "Y")
    b.lathe([(0.066, 0.0), (0.0665, 0.0), (0.0665, 0.12), (0.06, 0.135), (0.0, 0.137)], loc=(0, 0, 0.012),
            mat="dome", seg=48)
    b.plane(0.08, 0.08, loc=(0, 0, 0.012 + 0.137 + E), mat="lidlabel", cuts=2)
    b.frame = Matrix.Identity(4)
    br = _ch(rng, ["VERBATUMMY", "MEMOWRECKS", "TDKAY", "SONNY"])
    c = Canvas(256, 256, (0.1, 0.1, 0.12, 1))
    c.circle(0.5, 0.5, 0.48, (0.1, 0.25, 0.65))
    c.text_fit(br, 0.15, 0.78, 0.7, 0.12, (1, 1, 1), bold=True)
    c.text_fit("50 PACK CD-R", 0.2, 0.55, 0.6, 0.1, (1.0, 0.85, 0.1), bold=True)
    c.text_fit("700MB 80MIN 52X", 0.22, 0.38, 0.56, 0.07, (1, 1, 1))
    c.text_fit("BURN BABY BURN", 0.25, 0.25, 0.5, 0.06, (1, 1, 1))
    _disc_print(c)
    gold = rng.random() < 0.4
    t = Canvas(256, 256, (0.9, 0.9, 0.92, 1))
    t.text_fit(br + " CD-R", 0.18, 0.7, 0.64, 0.09, (0.1, 0.2, 0.6), bold=True)
    for i in range(4):
        t.rect(0.22, 0.4 - i * 0.07, 0.78, 0.405 - i * 0.07, (0.6, 0.6, 0.65))
    _disc_print(t)
    return {"base": P(BLACK, 0.4), "discs": ("disc", {"color": (0.85, 0.75, 0.4) if gold else (0.45, 0.55, 0.85),
                                                       "film": float(rng.uniform(400, 650))}),
            "edge": P((0.25, 0.25, 0.3), 0.3), "top": PR(t.image("cdrtop"), 0.3, alpha_from_image=True),
            "dome": T((0.82, 0.84, 0.88), 0.08), "lidlabel": PR(c.image("cdrlid"), 0.3, alpha_from_image=True)}


@obj("os_box", eras=(1, 2), mass=0.8, weight=1.0, hero=(0, 0, 1))
def os_box(b, rng, pal):
    """Boxed OS software: a fat cardboard box of floppies or one CD, clouds on the front, a window cracked
    clean through the middle of the logo. Start me up."""
    W, H, D = 0.19, 0.24, 0.05
    b.box((W, H, D), mat="box", bevel=0.002)
    b.plane(W, H, loc=(0, 0, D / 2 + E), mat="front", cuts=3)
    b.plane(D, H, loc=(W / 2 + E, 0, 0), rot=(0, math.pi / 2, 0), mat="spine", cuts=2)
    b.plane(W, H, loc=(0, 0, -D / 2 - E), rot=(math.pi, 0, 0), mat="back", cuts=2)
    nm = _ch(rng, ["WINDOZE 95", "WINDOZE 95", "WINDOZE 98", "WINDOZE ME (SORRY)", "OFFICE SPACE 97"])
    c = Canvas(320, 400, (0.4, 0.6, 0.9, 1))
    c.gradient((0.25, 0.5, 0.95), (0.6, 0.8, 1.0))
    for _ in range(9):
        cx, cy = rng.uniform(0, 1), rng.uniform(0.0, 1)
        for k in range(5):
            c.circle(float(cx) + (k - 2) * 0.06, float(cy) + 0.02 * math.sin(k * 2), 0.05 + 0.02 * (k % 2), (1, 1, 1, 0.85))
    x0, y0, s = 0.25, 0.42, 0.5
    c.rect(x0 - 0.02, y0 - 0.02, x0 + s + 0.02, y0 + s * 0.8 + 0.02, (0.1, 0.1, 0.1))
    for i, col in enumerate([(0.1, 0.1, 0.1), (0.95, 0.75, 0.2), (0.95, 0.75, 0.2), (0.1, 0.1, 0.1)]):
        qx, qy = i % 2, i // 2
        c.rect(x0 + qx * s / 2 + 0.01, y0 + qy * s * 0.4 + 0.01, x0 + (qx + 1) * s / 2 - 0.01, y0 + (qy + 1) * s * 0.4 - 0.01,
               (0.55, 0.8, 0.95))
    c.line([(x0 + 0.08, y0 + 0.35), (x0 + 0.2, y0 + 0.2), (x0 + 0.15, y0 + 0.12), (x0 + 0.32, y0 + 0.03)], 0.012, (1, 1, 1))
    c.line([(x0 + 0.2, y0 + 0.2), (x0 + 0.38, y0 + 0.27)], 0.01, (1, 1, 1))
    c.rect(0, 0.0, 1, 0.3, (0.08, 0.08, 0.1))
    c.text_fit(nm, 0.06, 0.25, 0.88, 0.1, (1, 1, 1), bold=True)
    c.text_fit(_ch(rng, ["NOW WITH FEWER CRASHES", "INCLUDES 13 FLOPPIES", "WHERE DO YOU WANT TO CRASH TODAY?",
                         "PLUG AND PRAY", "UPGRADE - REQUIRES PATIENCE"]), 0.06, 0.1, 0.88, 0.045, (1.0, 0.85, 0.2))
    c.text("MACROHARD", 0.06, 0.97, 0.05, (0.1, 0.1, 0.3), bold=True)
    sp = Canvas(80, 400, (0.08, 0.08, 0.1, 1))
    sp.text_fit(nm[:12], 0.08, 0.95, 0.84, 0.1, (1, 1, 1), bold=True)
    sp.rect(0.15, 0.1, 0.85, 0.5, (0.4, 0.6, 0.9))
    bk = Canvas(320, 400, (0.96, 0.96, 0.95, 1))
    bk.text("SYSTEM REQUIREMENTS", 0.06, 0.95, 0.05, (0.1, 0.1, 0.1), bold=True)
    for i, line in enumerate(["386DX OR HIGHER", "4MB RAM (8 IF RICH)", "50MB HARD DISK", "VGA OR BETTER",
                              "A MOUSE OR A DREAM", "PATIENCE: LOTS"]):
        bk.text(line, 0.08, 0.85 - i * 0.07, 0.035, (0.2, 0.2, 0.2))
    _barcode(bk, rng, 0.55, 0.05, 0.94, 0.17)
    return {"box": ("cardboard", {"color": (0.9, 0.9, 0.9)}), "front": PR(c.image("osbox"), 0.35),
            "spine": PR(sp.image("osspine"), 0.35), "back": PR(bk.image("osback"), 0.4)}


# == B) DIAL-UP: the family computer, 1996-2001 =====================================================
DIAL = dict(group="special", eras=(1, 2), tags=("dialup",))


def _aohell_disc(rng, name):
    c = Canvas(384, 384, (0.08, 0.15, 0.5, 1))
    c.gradient((0.05, 0.2, 0.65), (0.02, 0.06, 0.25))
    for k in range(10):
        c.circle(0.5, 0.5, 0.15 + k * 0.035, (0.3, 0.55, 1.0, 0.25), ring=0.006)
    c.poly([(0.33, 0.6), (0.5, 0.92), (0.67, 0.6)], (1.0, 0.85, 0.1))           # the little pitchfork-person
    c.circle(0.5, 0.82, 0.05, (0.08, 0.15, 0.5))
    c.poly([(0.44, 0.86), (0.42, 0.95), (0.47, 0.88)], (0.95, 0.15, 0.1))
    c.poly([(0.56, 0.86), (0.58, 0.95), (0.53, 0.88)], (0.95, 0.15, 0.1))
    c.text_fit("AOHELL", 0.24, 0.42, 0.52, 0.12, (1, 1, 1), bold=True)
    c.text_fit(_ch(rng, ["VERSION 4.0", "VERSION 5.0", "VERSION 3.0 FOR WINDOZE"]), 0.3, 0.26, 0.4, 0.05, (1.0, 0.85, 0.1))
    c.text_fit(_ch(rng, ["1000 HOURS FREE*", "700 HOURS FREE*", "500 HOURS FREE*"]), 0.2, 0.2, 0.6, 0.06, (1, 1, 1), bold=True)
    c.text_fit("*MUST BE USED IN THE FIRST 45 MINUTES", 0.22, 0.11, 0.56, 0.025, (0.8, 0.85, 1.0))
    _disc_print(c)
    return c.image(name)


@obj("trial_cd", mass=0.016, weight=1.0, **DIAL)
def trial_cd(b, rng, pal):
    """The free trial disc. Arrived in the mail, in the cereal box, in the bag at the store, under the
    windshield wiper. Coaster count at its peak: one per household per day."""
    _disc(b)
    b.plane(0.12, 0.12, loc=(0, 0, 0.0006 + E), mat="print", cuts=6)
    return {"hub": HUB, "data": ("disc", {"color": (0.85, 0.85, 0.88), "film": float(rng.uniform(380, 620))}),
            "print": PR(_aohell_disc(rng, "aohcd"), 0.35, alpha_from_image=True)}


@obj("trial_tin", mass=0.08, weight=1.0, **DIAL)
def trial_tin(b, rng, pal):
    """The fancy one: the trial disc in a little metal tin, lid printed in silver and blue, hinged open
    with the disc winking inside. Too nice to throw out. Too useless to keep."""
    s, t = 0.135, 0.012
    b.box((s, s, t), loc=(0, 0, t / 2), mat="tin", bevel=0.004)
    b.box((s - 0.006, s - 0.006, 0.002), loc=(0, 0, t - 0.0005), mat="inside")
    _disc(b, loc=(0, 0, t + 0.0003))
    b.plane(0.12, 0.12, loc=(0, 0, t + 0.0009 + E), mat="cdprint", cuts=6)
    ang = float(rng.uniform(0.6, 1.15))
    b.frame = Matrix.Translation((0, s / 2, t)) @ Matrix.Rotation(ang, 4, "X")
    b.box((s + 0.002, s + 0.002, 0.004), loc=(0, -s / 2, 0.002), mat="tin", bevel=0.0015)
    b.plane(s * 0.97, s * 0.97, loc=(0, -s / 2, 0.004 + E), mat="lid", cuts=4)
    b.frame = Matrix.Identity(4)
    c = Canvas(320, 320, (0.75, 0.77, 0.8, 1))
    c.rect(0.06, 0.06, 0.94, 0.94, (0.08, 0.2, 0.6))
    c.rect(0.06, 0.06, 0.94, 0.3, (0.75, 0.77, 0.8))
    c.poly([(0.38, 0.5), (0.5, 0.82), (0.62, 0.5)], (1.0, 0.85, 0.1))
    c.circle(0.5, 0.72, 0.045, (0.08, 0.2, 0.6))
    c.text_fit("AOHELL", 0.2, 0.46, 0.6, 0.1, (1, 1, 1), bold=True)
    c.text_fit("YOUVE GOT MALWARE", 0.12, 0.26, 0.76, 0.06, (0.08, 0.2, 0.6), bold=True)
    c.text_fit("1000 HOURS FREE INSIDE", 0.14, 0.16, 0.72, 0.05, (0.08, 0.2, 0.6))
    return {"hub": HUB, "tin": MET((0.78, 0.8, 0.84), 0.25), "inside": MET((0.6, 0.62, 0.66), 0.4),
            "data": ("disc", {"color": (0.85, 0.85, 0.88), "film": 500.0}),
            "cdprint": PR(_aohell_disc(rng, "tincd"), 0.35, alpha_from_image=True),
            "lid": PR(c.image("tinlid"), 0.25, metal=0.55)}


@obj("modem_56k", mass=0.4, weight=1.0, **DIAL)
def modem_56k(b, rng, pal):
    """The external 56K: a flat box with a row of lights that blinked through the handshake, the scream
    that came with it, and the one family member who picked up the phone at 98%."""
    W, D, H = 0.16, 0.13, 0.032
    prof = [(-D / 2, 0.0), (D / 2, 0.0), (D / 2, H), (-D / 2 + 0.02, H), (-D / 2, H * 0.55)]
    b.extrude(prof, W, rot=(math.pi / 2, 0, math.pi / 2), mat="body", bevel=0.004)
    b.plane(W * 0.9, H * 0.5, loc=(0, -D / 2 - E, H * 0.28), rot=(math.pi / 2, 0, 0), mat="face", cuts=2)
    leds = ["AA", "CD", "OH", "RD", "SD", "TR", "MR", "HS"]
    on = rng.random(8) < 0.6
    for i in range(8):
        x = -W * 0.38 + i * W * 0.76 / 7
        b.cyl(0.0022, 0.003, loc=(x, -D / 2 + 0.004, H * 0.72), rot=(-0.7, 0, 0), mat="on" if on[i] else "off", seg=10)
    b.plane(W * 0.8, D * 0.5, loc=(0, -0.008, H + E), mat="top", cuts=2)
    for i in range(5):
        b.box((0.12, 0.003, 0.002), loc=(0, 0.04 + i * 0.0055, H), mat="vent")
    c = Canvas(384, 64, (0.15, 0.15, 0.16, 1))
    for i, l in enumerate(leds):
        c.text(l, 0.05 + i * 0.118, 0.68, 0.3, (0.85, 0.85, 0.85), bold=True)
    t = Canvas(320, 200, (0.15, 0.15, 0.16, 1))
    t.text_fit("THEIR ROBOTICS", 0.06, 0.9, 0.88, 0.14, (0.9, 0.9, 0.9), bold=True)
    t.text_fit("SPORTSTIR 56K FAXMODEM", 0.06, 0.66, 0.88, 0.1, (1.0, 0.3, 0.2), bold=True)
    t.text_fit("X2 V.90 - UP TO 56000 BPS (LOL)", 0.06, 0.45, 0.88, 0.06, (0.8, 0.8, 0.8))
    t.text_fit("EEEE-AWWWW-KSSSHHHH", 0.06, 0.25, 0.88, 0.07, (0.8, 0.8, 0.8))
    col = _ch(rng, [CHARCOAL, CHARCOAL, BEIGE, (0.2, 0.2, 0.25)])
    if col == BEIGE:
        c.a[..., :3] = np.where(c.a[..., :3] < 0.3, np.array(BEIGE, dtype=np.float32) * 0.9, 0.15)
        t.a[..., :3] = np.where(t.a[..., :3].sum(axis=2, keepdims=True) < 0.5, np.array(BEIGE, dtype=np.float32) * 0.9,
                                t.a[..., :3] * 0.3)
    return {"body": P(col, 0.45), "face": PR(c.image("modemface"), 0.4), "top": PR(t.image("modemtop"), 0.4),
            "on": P((1.0, 0.15, 0.08) if rng.random() < 0.3 else (0.2, 1.0, 0.15), 0.2, glow=3.0),
            "off": P((0.25, 0.08, 0.06), 0.25), "vent": P(BLACK, 0.8)}


_KB_ROWS = [
    [("ESC", 1), (None, 1), ("F1", 1), ("F2", 1), ("F3", 1), ("F4", 1), (None, .5), ("F5", 1), ("F6", 1), ("F7", 1),
     ("F8", 1), (None, .5), ("F9", 1), ("F10", 1), ("F11", 1), ("F12", 1)],
    [("'", 1)] + [(k, 1) for k in "1234567890-="] + [("BKSP", 2)],
    [("TAB", 1.5)] + [(k, 1) for k in "QWERTYUIOP()"] + [("/", 1.5)],
    [("CAPS", 1.75)] + [(k, 1) for k in "ASDFGHJKL:'"] + [("ENTER", 2.25)],
    [("SHIFT", 2.25)] + [(k, 1) for k in "ZXCVBNM,./"] + [("SHIFT", 2.75)],
    [("CTRL", 1.5), (None, 1), ("ALT", 1.5), ("", 7), ("ALT", 1.5), (None, 1), ("CTRL", 1.5)],
]


@obj("beige_keyboard", mass=1.2, weight=1.0, big=True, **DIAL)
def beige_keyboard(b, rng, pal):
    """The whole beige keyboard: grey modifier keys, a numpad, three green lights, a coiled cord, and
    enough crumbs under the keys to feed a family through Y2K."""
    u = 0.019
    rowsz = [0.0, 1.5, 2.5, 3.5, 4.5, 5.5]
    W = 23.0 * u
    Hh = 6.6 * u
    b.box((W + 0.02, Hh + 0.03, 0.022), loc=(W / 2 - 0.01 + 0.0, -Hh / 2 + 0.005, -0.004), mat="case", bevel=0.004)
    lc = Canvas(1536, 448, (0.5, 0.5, 0.5, 1))
    ink = (0.18, 0.18, 0.2)

    def key(x, y, w, label, mod):
        cx, cy = x + w * u / 2, -y - u / 2
        b.box((w * u - 0.0028, u - 0.0028, 0.009), loc=(cx, cy, 0.011), mat="mod" if mod else "key", bevel=0.0015)
        if label:
            ux = (cx - u * 0.38 * w + 0.01) / (W + 0.02)
            vy = (cy + Hh + 0.01) / (Hh + 0.03) + 0.025
            lc.text_fit(label, ux, vy, (w * u * 0.7) / (W + 0.02), 0.033 if len(label) == 1 else 0.022, ink, bold=True)

    for r, row in enumerate(_KB_ROWS):
        x = 0.0
        y = rowsz[r] * u
        for lab, w in row:
            if lab is not None:
                key(x, y, w, lab, (len(lab) > 1 and lab[0] != "F") or lab in ("", "ESC"))
            x += w * u
    nav = [["INS", "HOME", "PGUP"], ["DEL", "END", "PGDN"]]
    for r in range(2):
        for q in range(3):
            key((15.5 + q) * u, (1.5 + r) * u, 1, nav[r][q], True)
    for (q, r, lab) in ((1, 4.5, "^"), (0, 5.5, "<"), (1, 5.5, "V"), (2, 5.5, ">")):
        key((15.5 + q) * u, r * u, 1, lab, True)
    pad = [["NUM", "/", "*", "-"], ["7", "8", "9", "+"], ["4", "5", "6", None], ["1", "2", "3", "ENT"], ["0", None, ".", None]]
    for r in range(5):
        for q in range(4):
            lab = pad[r][q]
            if lab is None:
                continue
            w = 2 if lab == "0" else 1
            key((19 + q) * u, (1.5 + r) * u, w, lab, lab in ("NUM", "ENT", "+"))
    for i in range(3):
        b.cyl(0.0018, 0.001, loc=((19.4 + i * 1.2) * u, -0.2 * u, 0.0075), mat="led", seg=8)
    lc.text_fit("CLICKY-TEK 101", 0.69, 0.985, 0.18, 0.03, (0.3, 0.3, 0.32), bold=True)
    _alpha_from_bg(lc, (0.5, 0.5, 0.5))
    b.plane(W + 0.02, Hh + 0.03, loc=(W / 2 - 0.01, -Hh / 2 + 0.005, 0.0156), mat="legend", cuts=1)
    coil = [(W * 0.3 + 0.007 * math.cos(TAU * i / 12), 0.03 + 0.0005 * i, 0.007 * math.sin(TAU * i / 12))
            for i in range(84)]
    b.tube(coil, 0.0022, mat="cord", seg=6)
    yel = float(rng.uniform(0.0, 0.6))
    case = tuple(BEIGE[i] * (1 - yel) + YELLOWED[i] * yel for i in range(3))
    return {"case": P(case, 0.5), "key": P(tuple(min(1, x * 1.06) for x in case), 0.55),
            "mod": P((0.58, 0.58, 0.56), 0.55), "legend": PR(lc.image("kblegend"), 0.5, alpha_from_image=True),
            "led": P((0.2, 1.0, 0.2), 0.3, glow=2.0), "cord": P(case, 0.5)}


@obj("ball_mouse", mass=0.12, weight=1.0, **DIAL)
def ball_mouse(b, rng, pal):
    """The two-button ball mouse, its retaining ring twisted off and the grey rubber ball rolled away from
    it, the way it went every time it stopped tracking. Rollers wore a gasket of gunk."""
    tilt = float(rng.uniform(0.25, 0.6))
    b.frame = Matrix.Rotation(tilt, 4, "Y")                       # rolled onto its side: the empty socket shows
    rings = []
    for i in range(12):
        t = i / 11
        y = -0.06 + t * 0.12
        wd = 0.032 * math.sin(math.pi * (0.1 + 0.8 * t)) + 0.006
        ht = 0.036 * math.sin(math.pi * (0.05 + 0.75 * t)) + 0.004
        rings.append([(wd * math.cos(TAU * k / 18), y, max(0.0, ht * math.sin(TAU * k / 18))) for k in range(18)])
    b.loft(rings, mat="body")
    b.box((0.0016, 0.045, 0.004), loc=(0, 0.034, 0.0345), rot=(-0.35, 0, 0), mat="seam")           # button split
    b.box((0.052, 0.0016, 0.004), loc=(0, 0.012, 0.0405), mat="seam")
    b.box((0.06, 0.112, 0.002), loc=(0, 0, -0.0004), mat="belly", bevel=0.001)
    b.cyl(0.0145, 0.003, loc=(0, -0.01, -0.0008), mat="hole", seg=24)
    b.plane(0.026, 0.01, loc=(0, 0.035, -0.0016), rot=(math.pi, 0, 0), mat="label", cuts=1)
    b.frame = Matrix.Identity(4)
    rx, ry = float(rng.uniform(0.05, 0.075)), float(rng.uniform(-0.05, 0.02))
    b.torus(0.017, 0.0035, loc=(rx, ry, 0.0035), mat="belly", seg=24, rseg=6)
    b.box((0.004, 0.006, 0.002), loc=(rx + 0.017, ry, 0.006), mat="belly")
    b.sphere(0.011, loc=(rx + float(rng.uniform(-0.02, 0.02)), ry - 0.045, 0.011), mat="ball", seg=20)
    cord = [(0, 0.062, 0.006)]
    x, y, z = cord[0]
    ang = math.pi / 2
    for i in range(14):
        ang += float(rng.normal(0, 0.45))
        x += math.cos(ang) * 0.016
        y += math.sin(ang) * 0.016
        cord.append((x, y, 0.002))
    b.tube(cord, 0.0018, mat="body", seg=8)
    lab = Canvas(192, 80, (0.9, 0.9, 0.88, 1))
    lab.text_fit("MOUSE SYSTEMZ", 0.05, 0.85, 0.9, 0.3, (0.1, 0.1, 0.1), bold=True)
    lab.text_fit("2 BUTTON SERIAL", 0.05, 0.4, 0.9, 0.18, (0.3, 0.3, 0.3))
    yel = float(rng.uniform(0, 0.6))
    case = tuple(BEIGE[i] * (1 - yel) + YELLOWED[i] * yel for i in range(3))
    return {"body": P(case, 0.45), "belly": P(tuple(x * 0.8 for x in case), 0.6), "hole": P(BLACK, 0.8),
            "seam": P((0.25, 0.24, 0.2), 0.7), "ball": ("rubber", {"color": (0.35, 0.36, 0.38)}),
            "label": PR(lab.image("mouselab"), 0.5)}


def _rj11(b, pos, d, mat_clear="plug", mat_pin="pins"):
    x, y, z = pos
    a = math.atan2(d[1], d[0])
    b.box((0.016, 0.01, 0.008), loc=(x, y, z), rot=(0, 0, a), mat=mat_clear, bevel=0.0008)
    b.box((0.012, 0.004, 0.0015), loc=(x + math.cos(a) * 0.002, y + math.sin(a) * 0.002, z + 0.0045), rot=(0.25, 0, a),
          mat=mat_clear)
    for k in range(4):
        o = -0.003 + k * 0.002
        b.box((0.004, 0.0008, 0.002), loc=(x + math.cos(a) * 0.006 - math.sin(a) * o, y + math.sin(a) * 0.006 + math.cos(a) * o,
                                            z - 0.0035), rot=(0, 0, a), mat=mat_pin)


@obj("phone_cord", mass=0.05, weight=1.0, **DIAL)
def phone_cord(b, rng, pal):
    """Twenty-five feet of beige phone line, from the kitchen jack to the computer in the den, clear
    plastic plug on each end with the little clip already snapped off."""
    pts = []
    loops = float(rng.uniform(2.5, 3.5))
    n = 120
    for i in range(n):
        t = i / (n - 1)
        a = TAU * loops * t
        r = 0.05 + 0.012 * math.sin(a * 0.7) + float(rng.normal(0, 0.001))
        pts.append((r * math.cos(a) + 0.01 * t, r * math.sin(a), 0.004 * math.sin(a * 0.5) + 0.006 * t))
    tail = [pts[-1]]
    for i in range(6):
        tail.append((tail[-1][0] + 0.01, tail[-1][1] - 0.006, tail[-1][2]))
    b.tube(pts + tail[1:], 0.0019, mat="cord", seg=6)
    head = [pts[0]]
    for i in range(5):
        head.append((head[-1][0] - 0.004, head[-1][1] - 0.01, head[-1][2]))
    b.tube(head, 0.0019, mat="cord", seg=6)
    _rj11(b, (head[-1][0] - 0.004, head[-1][1] - 0.01, head[-1][2]), (-0.4, -1.0))
    _rj11(b, (tail[-1][0] + 0.009, tail[-1][1] - 0.005, tail[-1][2]), (1.0, -0.6))
    col = _ch(rng, [BEIGE, (0.85, 0.83, 0.78), (0.3, 0.3, 0.32), WHITE])
    return {"cord": P(col, 0.5), "plug": T((0.9, 0.92, 0.95), 0.1), "pins": MET((0.95, 0.75, 0.35), 0.2)}


@obj("mousepad", mass=0.06, weight=1.0, **DIAL)
def mousepad(b, rng, pal):
    """The screensaver mousepad: winged floppy disks flying across a night sky, a parody of the
    screensaver your dad paid for. The fabric pilled where the mouse lived."""
    W, H = 0.235, 0.195
    b.extrude(rounded_rect(W, H, 0.012, 4), 0.004, mat="foam", bevel=0.0012)
    b.plane(W * 0.985, H * 0.985, loc=(0, 0, 0.002 + E), mat="top", cuts=4)
    c = Canvas(512, 424, (0.02, 0.02, 0.06, 1))
    for _ in range(80):
        x, y = rng.uniform(0, 1, 2)
        c.circle(float(x), float(y), float(rng.uniform(0.002, 0.006)), (1, 1, 1))
    for _ in range(int(rng.integers(5, 8))):
        x, y = float(rng.uniform(0.08, 0.92)), float(rng.uniform(0.25, 0.85))
        s = float(rng.uniform(0.06, 0.1))
        sx = s * 424 / 512
        col = _ch(rng, [(0.15, 0.15, 0.9), (0.9, 0.15, 0.15), (0.1, 0.1, 0.1), (0.95, 0.9, 0.1)])
        for k in (-1, 1):       # feathered wings
            for f in range(3):
                c.poly([(x + k * sx * 0.4, y + s * 0.3), (x + k * sx * (1.0 + f * 0.15), y + s * (0.95 - f * 0.25)),
                        (x + k * sx * (0.95 + f * 0.1), y + s * (0.7 - f * 0.25))], (0.95, 0.95, 0.95))
        c.rect(x - sx * 0.45, y - s * 0.45, x + sx * 0.45, y + s * 0.45, col)
        c.rect(x - sx * 0.25, y + s * 0.15, x + sx * 0.25, y + s * 0.45, (0.75, 0.75, 0.78))
        c.rect(x - sx * 0.3, y - s * 0.4, x + sx * 0.3, y - s * 0.05, (0.95, 0.95, 0.92))
    c.rect(0, 0, 1, 0.16, (0.05, 0.05, 0.12))
    c.text_fit("SCREEN SAVIOR 3.0", 0.05, 0.13, 0.6, 0.08, (1.0, 0.85, 0.2), bold=True)
    c.text_fit("FLYING FLOPPIES", 0.68, 0.11, 0.28, 0.05, (0.7, 0.8, 1.0))
    c.noise(rng, 0.03)
    return {"foam": ("foam", {"color": (0.08, 0.08, 0.08)}), "top": PR(c.image("mpad"), 0.85)}


@obj("im_stickers", mass=0.004, weight=1.0, **DIAL)
def im_stickers(b, rng, pal):
    """A sheet of AIMLESS messenger stickers starring BLIPPY: away message, door opening, door slamming.
    Half of them already on a binder."""
    W, H = 0.1, 0.14
    c = Canvas(320, 448, (0.96, 0.96, 0.98, 1))
    c.rect(0, 0.9, 1, 1, (0.1, 0.2, 0.6))
    c.text_fit("AIMLESS MESSENGER", 0.04, 0.98, 0.92, 0.06, (1.0, 0.85, 0.1), bold=True)
    labels = ["BRB", "AWAY", "G2G", "LOL", "ASL?", "*DOOR OPENS*", "*DOOR SLAMS*", "IDLE 3H"]
    used = rng.random(6) < 0.3
    for i in range(6):
        cx, cy = 0.27 + (i % 2) * 0.46, 0.76 - (i // 2) * 0.3
        if used[i]:
            c.rect(cx - 0.2, cy - 0.13, cx + 0.2, cy + 0.13, (0.85, 0.85, 0.88))
            continue
        c.rect(cx - 0.2, cy - 0.13, cx + 0.2, cy + 0.13, _ch(rng, [(0.1, 0.25, 0.7), (0.05, 0.05, 0.1), (0.9, 0.2, 0.4)]))
        _blippy(c, cx - 0.08, cy + 0.01, 0.17, pose=i % 3)
        c.text_fit(labels[(i + int(rng.integers(0, 8))) % 8], cx - 0.0, cy + 0.03, 0.18, 0.05, (1, 1, 1), bold=True)
    c.text_fit("YOU HAVE 1 NEW BUDDY", 0.1, 0.06, 0.8, 0.035, (0.1, 0.2, 0.6), bold=True)
    _sheet(b, W, H, "sheet", bow=0.004, curl=float(rng.uniform(0.0, 0.025)))
    return {"sheet": PR(c.image("aimsheet"), 0.45)}


@obj("p2p_sleeve", mass=0.02, weight=1.0, **DIAL)
def p2p_sleeve(b, rng, pal):
    """A paper CD sleeve from the song-sharing years, its sticker from the app that got the whole
    dorm's internet cut off: a sour lime in headphones, or a cat asleep on the download button."""
    W = 0.125
    _sheet(b, W, W, "sleeve", bow=0.003, n=7)
    _disc(b, loc=(0.03, 0.012, -0.002), mat="data")
    b.plane(0.12, 0.12, loc=(0.03, 0.012, -0.0034), rot=(math.pi, 0, 0), mat="burn", cuts=4)
    lime = rng.random() < 0.5
    c = Canvas(400, 400, (0.97, 0.97, 0.95, 1))
    c.circle(0.5, 0.5, 0.36, (0.75, 0.82, 0.9, 0.6))
    c.circle(0.5, 0.5, 0.36, (0.6, 0.65, 0.7), ring=0.01)
    if lime:
        c.rect(0.0, 0.84, 1, 1, (0.2, 0.6, 0.1))
        c.text_fit("LIMEWHY", 0.06, 0.97, 0.88, 0.12, (1, 1, 1), bold=True)
        _lime_guy(c, 0.5, 0.5, 0.22)
        c.text_fit("SHARE EVERYTHING. REGRET EVERYTHING.", 0.04, 0.1, 0.92, 0.04, (0.2, 0.5, 0.1), bold=True)
    else:
        c.rect(0.0, 0.84, 1, 1, (0.1, 0.1, 0.1))
        c.text_fit("NAPPSTER", 0.06, 0.97, 0.88, 0.12, (1, 1, 1), bold=True)
        _nap_cat(c, 0.5, 0.48, 0.2)
        c.text_fit("DOWNLOADING 1 OF 1 - 3.2 KB/S", 0.04, 0.1, 0.92, 0.04, (0.1, 0.1, 0.1), bold=True)
    m = Canvas(256, 256, (0, 0, 0, 1))
    m.a[..., :3] = 0.0
    ink = (0.05, 0.05, 0.08)
    m.a[..., :3] = (0.85, 0.75, 0.4)
    m.text_fit(_ch(rng, ["DOWNLOADED", "NAPPED 4 U", "TOP 40 (PROBLY)"]), 0.18, 0.75, 0.64, 0.1, ink, bold=True)
    m.text_fit("SONG FINAL REAL.MP3", 0.18, 0.32, 0.64, 0.07, ink)
    _disc_print(m)
    return {"hub": HUB, "sleeve": PR(c.image("p2psleeve"), 0.75), "data": ("disc", {"color": (0.85, 0.75, 0.4), "film": 520.0}),
            "burn": PR(m.image("p2pburn"), 0.4, alpha_from_image=True)}


@obj("skin_printout", mass=0.006, weight=1.0, **DIAL)
def skin_printout(b, rng, pal):
    """An inkjet printout of a media-player skin somebody was proud of: the spectrum bars, the scrolling
    title, the slogan about whipping a farm animal. Banding from the cyan cartridge running low."""
    W, H = 0.17, 0.22
    c = Canvas(400, 520, (0.98, 0.98, 0.96, 1))
    c.text_fit("WINDAMP 2.91 - SKIN: " + _ch(rng, ["TOXIC NEON", "CHROME DRAGON", "X-FILEZ", "MATRIX GREEN"]),
               0.05, 0.97, 0.9, 0.025, (0.2, 0.2, 0.2))
    x0, x1, y0, y1 = 0.06, 0.94, 0.45, 0.9
    base = _ch(rng, [(0.15, 0.17, 0.2), (0.1, 0.12, 0.1), (0.25, 0.15, 0.35)])
    c.rect(x0, y0, x1, y1, base)
    c.rect(x0, y1 - 0.04, x1, y1, (0.3, 0.35, 0.6))
    c.text_fit("WINDAMP", x0 + 0.02, y1 - 0.008, 0.3, 0.025, (1, 1, 1), bold=True)
    c.rect(x0 + 0.03, y0 + 0.2, x0 + 0.38, y1 - 0.06, (0, 0, 0))
    c.text("3:14", x0 + 0.06, y1 - 0.08, 0.06, (0.2, 1.0, 0.2), bold=True)
    for i in range(14):
        hgt = float(rng.uniform(0.02, 0.16))
        x = x0 + 0.05 + i * 0.022
        for k in range(int(hgt / 0.012)):
            col = (0.2, 1.0, 0.2) if k < 6 else (1.0, 0.85, 0.1) if k < 10 else (1.0, 0.2, 0.1)
            c.rect(x, y0 + 0.21 + k * 0.012, x + 0.016, y0 + 0.219 + k * 0.012, col)
    c.rect(x0 + 0.41, y1 - 0.12, x1 - 0.03, y1 - 0.06, (0, 0, 0))
    c.text_fit("IT REALLY WHIPS THE ALPACAS BUTT", x0 + 0.43, y1 - 0.075, 0.46, 0.02, (0.2, 1.0, 0.2), bold=True)
    c.text_fit("128KBPS 44KHZ STEREO", x0 + 0.43, y1 - 0.14, 0.46, 0.018, (0.2, 1.0, 0.2))
    for i in range(5):
        c.rect(x0 + 0.03 + i * 0.075, y0 + 0.04, x0 + 0.09 + i * 0.075, y0 + 0.1, (0.6, 0.62, 0.66))
    c.poly([(x0 + 0.105, y0 + 0.055), (x0 + 0.105, y0 + 0.085), (x0 + 0.13, y0 + 0.07)], (0.1, 0.1, 0.1))
    c.rect(x0 + 0.45, y0 + 0.13, x1 - 0.04, y0 + 0.145, (0.5, 0.5, 0.5))
    c.rect(x0 + 0.6, y0 + 0.115, x0 + 0.63, y0 + 0.16, (0.8, 0.8, 0.85))
    ink = (0.1, 0.1, 0.4)
    c.scribble(rng, 0.08, 0.3, 0.7, 0.006, ink, 0.01)
    c.text("MY SKIN!!! DONT TOUCH", 0.08, 0.24, 0.03, ink, bold=True)
    for i in range(int(rng.integers(4, 9))):          # banding
        y = float(rng.uniform(0.0, 1.0))
        c.rect(0, y, 1, y + 0.004, (1.0, 0.75, 0.95, 0.5))
    c.noise(rng, 0.015)
    _sheet(b, W, H, "paper", bow=0.01, curl=float(rng.uniform(0.0, 0.05)), wob=0.002)
    return {"paper": PR(c.image("skin"), 0.85)}


@obj("hours_mailer", mass=0.03, weight=1.0, **DIAL)
def hours_mailer(b, rng, pal):
    """The envelope with the round lump in it: 1000 HOURS FREE in letters bigger than your address.
    Opened by the dog. Coaster number forty."""
    W, H = 0.235, 0.12
    rows = []
    n = 11
    for j in range(n):
        y = -H / 2 + H * j / (n - 1)
        row = []
        for i in range(n):
            x = -W / 2 + W * i / (n - 1)
            dx, dy = (x - 0.04) / 0.065, y / 0.055
            bump = 0.005 * max(0.0, 1 - dx * dx - dy * dy) ** 0.5
            row.append((x, y, bump))
        rows.append(row)
    b.loft(rows, mat="env", closed=False, cap=False)
    b.box((W, H, 0.001), loc=(0, 0, -0.0006), mat="back")
    c = Canvas(560, 288, (0.08, 0.2, 0.6, 1))
    c.gradient((0.05, 0.22, 0.7), (0.02, 0.1, 0.4))
    c.text_fit(_ch(rng, ["1000 HOURS FREE!", "1000 HOURS FREE!", "700 HOURS FREE!"]), 0.05, 0.92, 0.6, 0.17,
               (1.0, 0.85, 0.1), bold=True)
    c.text_fit("THE INTERNET IS IN THIS ENVELOPE", 0.05, 0.66, 0.6, 0.05, (1, 1, 1), bold=True)
    c.text_fit("AOHELL", 0.05, 0.52, 0.3, 0.1, (1, 1, 1), bold=True)
    c.rect(0.06, 0.06, 0.48, 0.32, (0.96, 0.96, 0.95))
    c.text("CURRENT RESIDENT", 0.08, 0.28, 0.04, (0.1, 0.1, 0.1))
    c.text("1234 ANY STREET", 0.08, 0.2, 0.04, (0.1, 0.1, 0.1))
    c.text("ANYTOWN USA 00000", 0.08, 0.12, 0.04, (0.1, 0.1, 0.1))
    c.rect(0.82, 0.74, 0.96, 0.95, (0.96, 0.96, 0.95))
    c.text_fit("PRSRT STD", 0.83, 0.9, 0.12, 0.035, (0.1, 0.1, 0.1))
    c.circle(0.75, 0.42, 0.24, (1, 1, 1, 0.08))
    c.text_fit("DO NOT BEND - CD INSIDE", 0.55, 0.12, 0.42, 0.05, (1, 1, 1), bold=True)
    c.noise(rng, 0.015)
    return {"env": PR(c.image("mailer"), 0.7), "back": ("paper", {"color": (0.92, 0.92, 0.9)})}


@obj("cdr_sharpie", mass=0.016, weight=1.0, **DIAL)
def cdr_sharpie(b, rng, pal):
    """A gold CD-R, Sharpie on the label side, burned at 4x after three coasters. Do not lend."""
    _disc(b)
    b.plane(0.12, 0.12, loc=(0, 0, 0.0006 + E), mat="label", cuts=6)
    c = Canvas(384, 384, (0.88, 0.78, 0.45, 1))
    c.circle(0.5, 0.5, 0.2, (0.8, 0.7, 0.4), ring=0.01)
    ink = _ch(rng, [(0.05, 0.05, 0.05), (0.05, 0.05, 0.4), (0.6, 0.0, 0.05)])
    t1 = _ch(rng, ["MP3Z VOL 7", "HOMEWORK", "NAPPED MIX", "DO NOT DELETE", "SENIOR YR MIX", "WAREZ", "QUAKE MAPS"])
    c.text_fit(t1, 0.2, 0.86, 0.6, 0.09, ink, bold=True)
    if rng.random() < 0.5:
        c.text_fit("(NOT PORN)", 0.3, 0.74, 0.4, 0.06, ink, bold=True)
    for i in range(3):
        c.scribble(rng, 0.18, 0.28 - i * 0.06, float(rng.uniform(0.5, 0.82)), 0.006, ink, 0.01)
    c.text_fit(_ch(rng, ["BURNED 4X", "650MB", "1999", "COPY 3"]), 0.62, 0.42, 0.25, 0.05, ink)
    _disc_print(c)
    return {"hub": HUB, "data": ("disc", {"color": (0.85, 0.75, 0.4), "film": float(rng.uniform(400, 650))}),
            "label": PR(c.image("cdrsharpie"), 0.4, alpha_from_image=True)}


# == C) BE KIND REWIND: Friday night at the video store ============================================
RENT = dict(group="special", eras=(0, 1, 2), tags=("rental",))
BB_BLUE = (0.05, 0.15, 0.55)
BB_YEL = (1.0, 0.8, 0.05)
MOVIES = ["JURASSIC PARKING", "HOME ALONE TOO LONG", "SPEED BUMP", "TITANIC-ISH", "THE MATRIXX", "DIE HARDLY",
          "TERMINATED 2", "BACK TO THE FUTON", "GHOSTBUSTED", "TOP GUNK", "FREE WILLY NILLY", "DUMB AND DUMBERER",
          "MRS. DOUBTFIRED", "INDEPENDENCE DAZE", "THE BLAIR WITCH PROJECT-ISH", "FAST TIMES AT RIDGEMONT LOW",
          "HONEY I SHRUNK THE BUDGET", "ARMAGEDDON OUTTA HERE"]


def _bb_logo(c, x, y, w, h):
    """BLOCKBUSTED: a yellow brick cracked clean in two, BLOCKBUSTED in fat navy letters. Our own mark."""
    c.poly([(x, y), (x + w * 0.46, y), (x + w * 0.42, y + h * 0.45), (x + w * 0.5, y + h * 0.6), (x + w * 0.44, y + h),
            (x, y + h)], BB_YEL)
    c.poly([(x + w * 0.52, y), (x + w, y), (x + w, y + h), (x + w * 0.5, y + h), (x + w * 0.56, y + h * 0.6),
            (x + w * 0.48, y + h * 0.45)], BB_YEL)
    c.text_fit("BLOCK", x + w * 0.04, y + h * 0.88, w * 0.4, h * 0.36, BB_BLUE, bold=True)
    c.text_fit("BUSTED", x + w * 0.56, y + h * 0.88, w * 0.42, h * 0.36, BB_BLUE, bold=True)
    c.text_fit("VIDEO", x + w * 0.36, y - h * 0.08, w * 0.28, h * 0.22, BB_YEL, bold=True)


def _rental_cover(rng, name, new=False, game=False):
    c = Canvas(320, 512, (*BB_BLUE, 1))
    _bb_logo(c, 0.1, 0.8, 0.8, 0.16)
    if game:
        c.rect(0.1, 0.25, 0.9, 0.72, (0.08, 0.08, 0.1))
        c.text_fit(_ch(rng, ["GAME RENTAL", "VIDEO GAME", "GAMES"]), 0.14, 0.68, 0.72, 0.08, (1, 1, 1), bold=True)
        c.text_fit("3 NIGHTS 5 DAYS-ISH", 0.14, 0.52, 0.72, 0.05, BB_YEL, bold=True)
        c.text_fit("RETURN WITH INSTRUCTIONS", 0.14, 0.4, 0.72, 0.035, (1, 1, 1))
        c.text_fit("NO BLOWING IN THE CART", 0.14, 0.33, 0.72, 0.035, (1, 1, 1))
    else:
        c.rect(0.1, 0.25, 0.9, 0.72, (0.95, 0.95, 0.92))
        c.text_fit(_ch(rng, MOVIES), 0.14, 0.68, 0.72, 0.07, BB_BLUE, bold=True)
        c.text_fit(_ch(rng, ["COMEDY", "ACTION", "DRAMA", "HORROR", "FAMILY", "SCI-FI", "NEW RELEASE"]), 0.14, 0.56,
                   0.5, 0.05, (0.8, 0.1, 0.1), bold=True)
        c.text_fit("PLEASE REWIND", 0.14, 0.46, 0.72, 0.05, BB_BLUE, bold=True)
        c.text_fit("LATE FEES APPLY. FOREVER.", 0.14, 0.38, 0.72, 0.03, BB_BLUE)
        _barcode(c, rng, 0.14, 0.27, 0.6, 0.33)
    c.text_fit("MAKE IT A BLOCKBUSTED NIGHT", 0.08, 0.16, 0.84, 0.035, BB_YEL, bold=True)
    if new:
        c.poly([(0.0, 0.62), (0.0, 0.75), (1.0, 0.95), (1.0, 0.82)], (0.85, 0.05, 0.08))
        c.text_fit("NEW RELEASE", 0.18, 0.86, 0.64, 0.06, (1, 1, 1), bold=True)
        c.circle(0.78, 0.2, 0.12, BB_YEL)
        c.text_fit("1 NIGHT", 0.68, 0.24, 0.2, 0.04, (0.85, 0.05, 0.08), bold=True)
        c.text_fit("GUARANTEED", 0.67, 0.17, 0.22, 0.025, (0.85, 0.05, 0.08), bold=True)
        c.text_fit("ISH", 0.74, 0.12, 0.08, 0.025, (0.85, 0.05, 0.08), bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


def _clamshell(b, rng, W, H, D, cover, open_ang=0.0, inside=None):
    """A rental clamshell: two trays joined down the long spine. The cover print goes on the lid."""
    t = 0.0025
    b.box((W, H, t), loc=(0, 0, t / 2), mat="case", bevel=0.001)
    for sx in (-1, 1):
        b.box((t, H, D / 2), loc=(sx * (W / 2 - t / 2), 0, D / 4), mat="case")
    for sy in (-1, 1):
        b.box((W, t, D / 2), loc=(0, sy * (H / 2 - t / 2), D / 4), mat="case")
    if inside:
        inside()
    b.frame = Matrix.Translation((-W / 2, 0, D / 2)) @ Matrix.Rotation(-open_ang, 4, "Y")
    b.box((W, H, t), loc=(W / 2, 0, D / 2 - t / 2), mat="case", bevel=0.001)
    b.box((W, H, D / 2), loc=(W / 2, 0, D / 4), mat="case", bevel=0.002)
    b.plane(W * 0.94, H * 0.96, loc=(W / 2, 0, D / 2 + E), mat=cover, cuts=3)
    b.box((0.003, H * 0.9, D * 0.7), loc=(-0.0012, 0, 0.0), mat="case", bevel=0.001)   # the spine hinge
    b.frame = Matrix.Identity(4)


def _vhs_inside(b, W, H, D):
    def f():
        b.box((min(W * 0.9, 0.1), min(H * 0.92, 0.187), 0.025), loc=(0, 0, 0.015), mat="tape", bevel=0.002)
        b.plane(0.08, 0.06, loc=(0, 0.04, 0.0276), mat="tapelab", cuts=1)
    return f


@obj("rental_vhs", mass=0.3, weight=1.0, **RENT)
def rental_vhs(b, rng, pal):
    """The rental clamshell: blue plastic, a yellow BLOCKBUSTED cover, the barcode, the category sticker,
    and a tape that was not rewound."""
    W, H, D = 0.125, 0.21, 0.032
    ang = 0.0 if rng.random() < 0.5 else float(rng.uniform(0.4, 1.8))
    _clamshell(b, rng, W, H, D, "cover", ang, _vhs_inside(b, W, H, D) if ang else None)
    lab = Canvas(256, 192, (0.97, 0.97, 0.95, 1))
    lab.text_fit("BLOCKBUSTED", 0.06, 0.9, 0.88, 0.15, BB_BLUE, bold=True)
    lab.text_fit(_ch(rng, MOVIES), 0.06, 0.6, 0.88, 0.1, (0.1, 0.1, 0.1), bold=True)
    lab.text_fit("BE KIND REWIND", 0.06, 0.3, 0.88, 0.12, (0.85, 0.05, 0.08), bold=True)
    return {"case": P(_ch(rng, [BB_BLUE, BB_BLUE, (0.08, 0.2, 0.65)]), 0.35), "cover": PR(_rental_cover(rng, "bbv"), 0.35),
            "tape": P(BLACK, 0.4), "tapelab": PR(lab.image("bbtape"), 0.4)}


@obj("new_release_case", mass=0.3, weight=1.0, **RENT)
def new_release_case(b, rng, pal):
    """The NEW RELEASE case: red sash sticker, the guarantee in fine print, out of stock since Tuesday,
    and the one copy left was behind the counter with a mustache guy's name on it."""
    W, H, D = 0.125, 0.21, 0.032
    _clamshell(b, rng, W, H, D, "cover", 0.0)
    b.plane(0.035, 0.035, loc=(W / 2 - 0.025, -H / 2 + 0.03, D + E * 2), rot=(0, 0, 0.3), mat="dot", cuts=1)
    d = Canvas(64, 64, (0, 0, 0, 1))
    d.circle(0.5, 0.5, 0.48, (1.0, 0.45, 0.05))
    d.text_fit("$3.99", 0.14, 0.62, 0.72, 0.22, (1, 1, 1), bold=True)
    d.a[..., 3] = (np.hypot(d.x - 0.5, d.y - 0.5) < 0.49).astype(np.float32)
    return {"case": P(BB_BLUE, 0.35), "cover": PR(_rental_cover(rng, "bbnr", new=True), 0.35),
            "dot": PR(d.image("bbdot"), 0.4, alpha_from_image=True)}


@obj("rental_game", mass=0.25, weight=1.0, **RENT)
def rental_game(b, rng, pal):
    """The game rental case: a smaller clamshell, a grey cartridge with a rental sticker over the art,
    and the save file of a stranger who was already on the last level."""
    W, H, D = 0.13, 0.17, 0.03
    def inside():
        b.box((0.11, 0.075, 0.016), loc=(0, 0.02, 0.01), mat="cart", bevel=0.002)
        b.box((0.11, 0.04, 0.012), loc=(0, -0.03, 0.008), mat="cart", bevel=0.002)
        b.plane(0.085, 0.05, loc=(0, 0.024, 0.0181), mat="cartlab", cuts=1)
        for i in range(10):
            b.box((0.002, 0.012, 0.001), loc=(-0.045 + i * 0.01, 0.054, 0.018), mat="cartrib")
    ang = float(rng.uniform(0.9, 2.2))
    _clamshell(b, rng, W, H, D, "cover", ang, inside)
    cl = Canvas(256, 160, (0.95, 0.95, 0.92, 1))
    cl.rect(0, 0.75, 1, 1, BB_BLUE)
    cl.text_fit("BLOCKBUSTED GAME RENTAL", 0.04, 0.95, 0.92, 0.12, BB_YEL, bold=True)
    cl.text_fit(_ch(rng, ["SUPER PLUMBER BROS 3", "STREET BRAWLER II", "MORTAL COMBO", "SONIC THE HEDGEHOG-ISH",
                          "GOLDENEYE 00-ISH", "TONY HAWG PRO SKATER"]), 0.04, 0.6, 0.92, 0.12, (0.1, 0.1, 0.1), bold=True)
    cl.text_fit("BLOW ON IT. IT WORKS.", 0.04, 0.32, 0.92, 0.08, (0.85, 0.05, 0.08), bold=True)
    _barcode(cl, rng, 0.06, 0.05, 0.6, 0.18)
    return {"case": P(_ch(rng, [BLACK, BB_BLUE]), 0.35), "cover": PR(_rental_cover(rng, "bbg", game=True), 0.35),
            "cart": P((0.55, 0.55, 0.56), 0.45), "cartrib": P((0.45, 0.45, 0.46), 0.5),
            "cartlab": PR(cl.image("bbcart"), 0.4)}


@obj("rental_card", mass=0.005, weight=1.0, **RENT)
def rental_card(b, rng, pal):
    """The membership card: blue plastic, the cracked brick, a barcode, a signature strip signed in
    gel pen. The most valuable ID a fourteen-year-old owned."""
    b.box((0.0856, 0.054, 0.0008), mat="card", bevel=0.0003)
    b.plane(0.0856, 0.054, loc=(0, 0, 0.0004 + E), mat="front", cuts=2)
    b.plane(0.0856, 0.054, loc=(0, 0, -0.0004 - E), rot=(math.pi, 0, 0), mat="back", cuts=2)
    c = Canvas(428, 270, (*BB_BLUE, 1))
    _bb_logo(c, 0.08, 0.55, 0.84, 0.35)
    c.text_fit("MEMBER", 0.08, 0.36, 0.4, 0.1, (1, 1, 1), bold=True)
    c.text_fit("SINCE " + str(int(rng.integers(1988, 2001))), 0.08, 0.23, 0.4, 0.08, BB_YEL, bold=True)
    c.text_fit(" ".join(str(int(rng.integers(1000, 9999))) for _ in range(3)), 0.08, 0.11, 0.6, 0.07, (1, 1, 1))
    k = Canvas(428, 270, (0.95, 0.95, 0.95, 1))
    k.rect(0.06, 0.62, 0.94, 0.82, (0.98, 0.98, 0.9))
    for i in range(10):
        k.rect(0.06, 0.62 + i * 0.02, 0.94, 0.63 + i * 0.02, (0.85, 0.88, 0.95))
    k.scribble(rng, 0.1, 0.72, 0.6, 0.012, _ch(rng, [(0.6, 0.1, 0.8), (0.1, 0.2, 0.7), (0.9, 0.2, 0.5)]), 0.03)
    _barcode(k, rng, 0.08, 0.15, 0.7, 0.42)
    k.text_fit("RESPONSIBLE FOR ALL RENTALS. EVEN THAT ONE.", 0.06, 0.95, 0.88, 0.06, (0.2, 0.2, 0.2))
    return {"card": P(BB_BLUE, 0.3), "front": PR(c.image("bbcard"), 0.25), "back": PR(k.image("bbcardb"), 0.35)}


@obj("latefee_receipt", mass=0.003, weight=1.0, **RENT)
def latefee_receipt(b, rng, pal):
    """The late fee receipt, curled from the thermal printer: one tape, nine days late, a total that
    could have bought the movie."""
    W, H = 0.075, 0.2
    c = Canvas(240, 640, (0.97, 0.96, 0.93, 1))
    ink = (0.15, 0.15, 0.2)
    c.text_fit("BLOCKBUSTED VIDEO", 0.06, 0.97, 0.88, 0.022, ink, bold=True)
    c.text_fit("STORE 0" + str(int(rng.integers(100, 999))), 0.25, 0.94, 0.5, 0.016, ink)
    y = 0.88
    total = 0.0
    for _ in range(int(rng.integers(1, 4))):
        days = int(rng.integers(2, 15))
        fee = round(days * 1.99 + 0.0, 2)
        total += fee
        c.text_fit(_ch(rng, MOVIES), 0.06, y, 0.88, 0.018, ink, bold=True)
        c.text_fit(f"{days} DAYS LATE", 0.06, y - 0.03, 0.5, 0.016, ink)
        c.text_fit(f"${fee:.2f}", 0.66, y - 0.03, 0.3, 0.016, ink)
        y -= 0.08
    c.text_fit("NOT REWOUND", 0.06, y, 0.5, 0.016, ink)
    c.text_fit("$1.00", 0.66, y, 0.3, 0.016, ink)
    total += 1.0
    y -= 0.05
    c.rect(0.06, y, 0.94, y + 0.003, ink)
    c.text_fit("LATE FEES", 0.06, y - 0.02, 0.5, 0.025, ink, bold=True)
    c.text_fit(f"${total:.2f}", 0.6, y - 0.02, 0.36, 0.025, ink, bold=True)
    c.text_fit("THANK YOU FOR YOUR", 0.12, y - 0.1, 0.76, 0.016, ink)
    c.text_fit("CONTRIBUTION", 0.2, y - 0.13, 0.6, 0.016, ink)
    _barcode(c, rng, 0.1, 0.04, 0.9, 0.09, ink)
    c.noise(rng, 0.01)
    rows = []
    n = 17
    r = 0.012 / float(rng.uniform(0.25, 1.0))           # tighter roll, tighter curl
    for j in range(n):
        v = j / (n - 1)
        if v <= 0.5:
            yy, zz = (v - 0.5) * H, 0.0
        else:
            a = (v - 0.5) * H / r
            yy, zz = r * math.sin(a), r * (1 - math.cos(a))
        rows.append([(-W / 2 + W * i / 4, yy, zz + 0.0008 * math.sin(i + j)) for i in range(5)])
    b.loft(rows, mat="paper", closed=False, cap=False)
    return {"paper": PR(c.image("latefee"), 0.8)}


@obj("car_rewinder", mass=0.6, weight=1.0, hero=(0, -1, 0), **RENT)
def car_rewinder(b, rng, pal):
    """The VHS rewinder shaped like a red sports car: pop the hood, drop the tape in, and it screamed
    through a two-hour movie in ninety seconds, then ejected the hood like a crash test."""
    L, Wd = 0.22, 0.12
    prof = [(-L / 2, 0.014), (L / 2, 0.014), (L / 2, 0.034), (L / 2 - 0.012, 0.046), (0.02, 0.054), (-0.012, 0.078),
            (-0.062, 0.08), (-0.092, 0.06), (-L / 2, 0.056)]
    b.extrude(prof, Wd, rot=(math.pi / 2, 0, 0), mat="body", bevel=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.022, 0.018, loc=(sx * 0.068, sy * (Wd / 2 - 0.004), 0.022), rot=(math.pi / 2, 0, 0), mat="tire", seg=24)
            b.cyl(0.012, 0.0202, loc=(sx * 0.068, sy * (Wd / 2 - 0.004), 0.022), rot=(math.pi / 2, 0, 0), mat="rim", seg=16)
    for sy in (-1, 1):
        b.plane(0.06, 0.018, loc=(-0.045, sy * (Wd / 2 + E), 0.07), rot=(math.pi / 2, 0, 0 if sy < 0 else math.pi),
                mat="glass", cuts=1)
        b.box((0.012, 0.024, 0.01), loc=(L / 2 - 0.002, sy * 0.035, 0.04), mat="lamp", bevel=0.002)
        b.box((0.006, 0.024, 0.008), loc=(-L / 2 + 0.002, sy * 0.035, 0.045), mat="tail", bevel=0.002)
    b.plane(0.04, 0.1, loc=(-0.0005, 0, 0.068), rot=(0, -0.63, 0), mat="glass", cuts=1)
    for sy in (-1, 1):                                                      # the rear wing
        b.box((0.008, 0.006, 0.02), loc=(-L / 2 + 0.014, sy * 0.04, 0.066), mat="body", bevel=0.002)
    b.box((0.03, Wd * 0.95, 0.005), loc=(-L / 2 + 0.012, 0, 0.078), rot=(0, 0.12, 0), mat="body", bevel=0.002)
    b.plane(0.07, 0.03, loc=(-0.035, 0, 0.0805), mat="stripe", cuts=1)
    hood = float(rng.uniform(0.0, 0.55))
    b.frame = Matrix.Translation((0.008, 0, 0.056)) @ Matrix.Rotation(-hood, 4, "Y")
    b.box((0.092, Wd * 0.88, 0.006), loc=(0.046, 0, 0), mat="body", bevel=0.002)
    b.plane(0.08, 0.06, loc=(0.046, 0, 0.0031 + E), mat="decal", cuts=1)
    b.frame = Matrix.Identity(4)
    b.box((0.085, 0.08, 0.002), loc=(0.052, 0, 0.0525), mat="tire")
    col = _ch(rng, [(0.85, 0.05, 0.05), (0.85, 0.05, 0.05), (0.85, 0.05, 0.05), (0.95, 0.8, 0.05), (0.1, 0.2, 0.7)])
    c = Canvas(256, 192, (*col, 1))
    c.rect(0, 0.3, 1, 0.42, (1, 1, 1))
    c.rect(0, 0.58, 1, 0.7, (1, 1, 1))
    c.text_fit("REWIND-O-MATIC", 0.04, 0.95, 0.92, 0.18, (1, 1, 1), bold=True)
    c.text_fit("TURBO", 0.25, 0.25, 0.5, 0.2, (0.05, 0.05, 0.05), bold=True)
    st = Canvas(128, 64, (*col, 1))
    st.rect(0, 0.3, 1, 0.42, (1, 1, 1))
    st.rect(0, 0.58, 1, 0.7, (1, 1, 1))
    return {"body": P(col, 0.2, coat=0.9), "tire": RUB(), "rim": CHROME(), "glass": P((0.05, 0.06, 0.08), 0.05, coat=1.0),
            "lamp": P((1.0, 1.0, 0.85), 0.2, glow=1.0), "tail": P((0.9, 0.05, 0.05), 0.2, glow=0.8),
            "decal": PR(c.image("rewdecal"), 0.2, coat=0.9), "stripe": PR(st.image("rewstripe"), 0.2, coat=0.9)}


@obj("popcorn_bag", mass=0.1, weight=1.0, **RENT)
def popcorn_bag(b, rng, pal):
    """Microwave popcorn, puffed and steaming, a butter stain through the THIS SIDE UP. Somebody pushed
    the POPCORN button and walked away."""
    W, H = 0.2, 0.14
    nu, nv = 13, 11
    top, bot = [], []
    for j in range(nv):
        v = j / (nv - 1)
        rt, rb = [], []
        for i in range(nu):
            u = i / (nu - 1)
            x, y = (u - 0.5) * W, (v - 0.5) * H
            puff = math.sin(math.pi * u) ** 0.6 * math.sin(math.pi * v) ** 0.6
            z = 0.028 * puff + 0.002 * math.sin(i * 1.9 + j * 2.3) * puff
            rt.append((x, y, z))
            rb.append((x, y, -0.012 * puff))
        top.append(rt)
        bot.append(rb)
    b.loft(top, mat="bag", closed=False, cap=False)
    b.loft([list(reversed(r)) for r in bot], mat="back", closed=False, cap=False)
    nm = _ch(rng, ["POP SECRETION", "ORVILLE READYBACHELOR", "ACT TWO-ISH"])
    c = Canvas(480, 336, (0.96, 0.94, 0.88, 1))
    c.rect(0, 0, 1, 1, (0.85, 0.08, 0.08) if nm != "POP SECRETION" else (0.1, 0.2, 0.55))
    c.rect(0.05, 0.08, 0.95, 0.92, (0.97, 0.95, 0.88))
    c.text_fit(nm, 0.08, 0.88, 0.84, 0.13, (0.85, 0.08, 0.08) if nm != "POP SECRETION" else (0.1, 0.2, 0.55), bold=True)
    c.text_fit("MOVIE THEATER BUTTER-ISH", 0.08, 0.68, 0.84, 0.07, (0.95, 0.6, 0.05), bold=True)
    c.poly([(0.36, 0.14), (0.64, 0.14), (0.7, 0.42), (0.3, 0.42)], (0.95, 0.95, 0.95))       # striped bucket
    for i in range(5):
        x0 = 0.3 + i * 0.08
        c.poly([(x0 + 0.012 + i * 0.002, 0.14), (x0 + 0.04 - i * 0.002 + 0.01, 0.14), (x0 + 0.06, 0.42), (x0 + 0.03, 0.42)],
               (0.85, 0.08, 0.08))
    for _ in range(40):                                                                      # heaped popcorn
        a = float(rng.uniform(0, math.pi))
        rr = float(rng.uniform(0, 1)) ** 0.5
        cx, cy = 0.5 + 0.2 * rr * math.cos(a), 0.42 + 0.14 * rr * math.sin(a)
        for k in range(3):
            c.circle(cx + (k - 1) * 0.012, cy + 0.012 * (k % 2), 0.02, (1.0, 0.95, 0.75) if k else (1.0, 0.85, 0.45))
    c.poly([(0.08, 0.45), (0.14, 0.52), (0.2, 0.45), (0.16, 0.45), (0.16, 0.38), (0.12, 0.38), (0.12, 0.45)], (0.1, 0.1, 0.1))
    c.text_fit("THIS SIDE UP", 0.07, 0.34, 0.18, 0.035, (0.1, 0.1, 0.1), bold=True)
    for _ in range(int(rng.integers(2, 5))):
        c.circle(float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.1, 0.9)), float(rng.uniform(0.05, 0.12)),
                 (0.85, 0.6, 0.15, 0.35))
    if rng.random() < 0.4:
        c.circle(0.78, 0.3, 0.08, (0.15, 0.08, 0.02, 0.6))
    return {"bag": PR(c.image("popcorn"), 0.75), "back": ("paper", {"color": (0.93, 0.9, 0.82)})}


@obj("theater_candy", mass=0.08, weight=1.0, **RENT)
def theater_candy(b, rng, pal):
    """Theater-box candy from the rack by the register: a long cardboard box, flap torn open, a few
    pieces rattling loose. Overpriced. Bought anyway."""
    W, H, D = 0.07, 0.115, 0.022
    b.box((W, H, D), mat="box", bevel=0.001)
    b.plane(W, H, loc=(0, 0, D / 2 + E), mat="front", cuts=2)
    b.plane(W, H, loc=(0, 0, -D / 2 - E), rot=(math.pi, 0, 0), mat="front", cuts=2)
    ang = float(rng.uniform(0.3, 1.5))
    b.frame = Matrix.Translation((0, H / 2, D / 2)) @ Matrix.Rotation(ang, 4, "X")
    b.box((W, D, 0.0008), loc=(0, D / 2, 0), mat="box")
    b.frame = Matrix.Identity(4)
    kind = int(rng.integers(0, 4))
    nm, bg, ink, piece = [("MILK DUDES", (0.95, 0.85, 0.2), (0.45, 0.2, 0.05), (0.35, 0.18, 0.08)),
                          ("SENIOR MINTS", (0.15, 0.4, 0.2), (1, 1, 1), (0.2, 0.12, 0.06)),
                          ("DOTTZ", (0.95, 0.95, 0.95), (0.85, 0.1, 0.4), None),
                          ("GOOBERED", (0.6, 0.15, 0.6), (1.0, 0.85, 0.2), (0.4, 0.22, 0.1))][kind]
    c = Canvas(224, 368, (*bg, 1))
    if kind == 2:
        for _ in range(40):
            c.circle(float(rng.uniform(0, 1)), float(rng.uniform(0, 1)), 0.04, _ch(rng, [(1, 0.2, 0.3), (1, 0.8, 0.1),
                                                                                         (0.3, 0.8, 0.2), (1, 0.5, 0.1)]))
        c.rect(0.05, 0.55, 0.95, 0.75, (0.95, 0.95, 0.95))
    c.text_fit(nm, 0.06, 0.72, 0.88, 0.14, ink, bold=True)
    c.text_fit(_ch(rng, ["THEATER BOX", "NOW WITH LESS", "CHEWY. TOO CHEWY.", "SHARE SIZE (NO)"]), 0.06, 0.35, 0.88,
               0.05, ink, bold=True)
    c.text_fit("NET WT 5 OZ", 0.06, 0.1, 0.5, 0.04, ink)
    specs = {"box": ("cardboard", {"color": bg}), "front": PR(c.image("tcandy"), 0.5)}
    pc = piece or _ch(rng, [(1, 0.2, 0.3), (1, 0.8, 0.1), (0.3, 0.8, 0.2)])
    for k in range(int(rng.integers(2, 5))):
        x, y = float(rng.uniform(-0.03, 0.05)), H / 2 + float(rng.uniform(0.005, 0.03))
        if kind == 2:
            b.cyl(0.008, 0.01, loc=(x, y, 0.0), rot=(float(rng.uniform(0, 2)), 0, 0), mat=f"pc{k}", seg=14)
            specs[f"pc{k}"] = P(_ch(rng, [(1, 0.2, 0.3), (1, 0.8, 0.1), (0.3, 0.8, 0.2), (1, 0.5, 0.1)]), 0.25, coat=0.6)
        else:
            b.sphere(0.0075, loc=(x, y, 0.0), scale=(1.1, 1, 0.8), mat=f"pc{k}", seg=12)
            specs[f"pc{k}"] = P(pc, 0.3, coat=0.4)
    return specs


@obj("dvd_case", mass=0.1, weight=1.0, **RENT)
def dvd_case(b, rng, pal):
    """The early-DVD keep case: black plastic, a clear sleeve over the cover, WIDESCREEN in a box, and a
    BLOCKBUSTED sticker over the actors' faces."""
    W, H, D = 0.135, 0.19, 0.014
    b.box((W, H, D), mat="case", bevel=0.002)
    b.box((0.004, H * 0.98, D * 1.02), loc=(-W / 2 + 0.002, 0, 0), mat="case", bevel=0.001)
    b.plane(W * 0.96, H * 0.96, loc=(0.002, 0, D / 2 + E), mat="cover", cuts=3)
    b.plane(0.07, 0.035, loc=(0.02, -0.055, D / 2 + E * 2), rot=(0, 0, float(rng.normal(0, 0.1))), mat="sticker", cuts=1)
    c = Canvas(320, 448, (0.05, 0.05, 0.08, 1))
    c.gradient(_ch(rng, [(1.0, 0.55, 0.15), (0.2, 0.75, 0.95), (0.95, 0.3, 0.4), (0.4, 0.9, 0.5)]), (0.15, 0.05, 0.25))
    c.rect(0, 0.86, 1, 0.9, (0.95, 0.95, 0.95))
    c.text_fit("DIGITAL VIDEO DISC", 0.2, 0.895, 0.6, 0.03, (0.05, 0.05, 0.05), bold=True)
    for k in range(3):
        cx = 0.25 + k * 0.25
        c.circle(cx, 0.55, 0.09, (0.06, 0.04, 0.08))
        c.rect(cx - 0.11, 0.18, cx + 0.11, 0.48, (0.06, 0.04, 0.08))
    c.text_fit(_ch(rng, ["THE GLITCH", "GLADIATOR-ISH", "SHREKT", "MEMENTOH", "FIGHT CLUBBED", "AMERICAN PIE CHART"]),
               0.06, 0.82, 0.88, 0.09, (1, 1, 1), bold=True)
    c.rect(0.06, 0.04, 0.4, 0.1, (0.95, 0.95, 0.95))
    c.text_fit("WIDESCREEN", 0.08, 0.09, 0.3, 0.035, (0.05, 0.05, 0.05), bold=True)
    c.text_fit("SPECIAL EDITION", 0.5, 0.09, 0.44, 0.035, (0.95, 0.8, 0.3), bold=True)
    s = Canvas(192, 96, (*BB_BLUE, 1))
    s.text_fit("BLOCKBUSTED", 0.05, 0.85, 0.9, 0.3, BB_YEL, bold=True)
    s.text_fit("RENTAL - DO NOT REMOVE", 0.05, 0.4, 0.9, 0.16, (1, 1, 1), bold=True)
    return {"case": P(BLACK, 0.35), "cover": PR(c.image("dvdcover"), 0.15, coat=1.0),
            "sticker": PR(s.image("dvdstk"), 0.4)}


@obj("dropbox_door", mass=1.2, weight=1.0, **RENT)
def dropbox_door(b, rng, pal):
    """A piece of the after-hours return slot, pried off the wall: painted steel, a flap that swung in,
    MOVIE RETURNS in vinyl letters, and one hundred thousand tapes shoved through it at 11:58 PM."""
    W, H = 0.26, 0.14
    b.box((W, H, 0.006), mat="plate", bevel=0.002)
    b.box((W * 0.7, 0.03, 0.01), loc=(0, -0.01, 0.002), mat="slot")
    b.frame = Matrix.Translation((0, 0.005, 0.006)) @ Matrix.Rotation(-float(rng.uniform(0.0, 0.5)), 4, "X")
    b.box((W * 0.72, 0.036, 0.003), loc=(0, -0.018, 0.0), mat="flap", bevel=0.001)
    b.frame = Matrix.Identity(4)
    b.plane(W * 0.9, 0.04, loc=(0, 0.045, 0.003 + E), mat="vinyl", cuts=1)
    b.plane(W * 0.9, 0.03, loc=(0, -0.05, 0.003 + E), mat="vinyl2", cuts=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(0.004, 0.003, loc=(sx * (W / 2 - 0.01), sy * (H / 2 - 0.01), 0.004), mat="rivet", seg=10)
    c = Canvas(512, 80, (*BB_BLUE, 1))
    c.text_fit("MOVIE RETURNS", 0.04, 0.85, 0.6, 0.7, (1, 1, 1), bold=True)
    c.text_fit("BLOCKBUSTED", 0.66, 0.75, 0.32, 0.5, BB_YEL, bold=True)
    c.noise(rng, 0.02)
    d = Canvas(512, 60, (*BB_BLUE, 1))
    d.text_fit("NO GAMES IN DROP BOX - BE KIND REWIND", 0.04, 0.8, 0.92, 0.6, BB_YEL, bold=True)
    return {"plate": MET(BB_BLUE, 0.55), "slot": P((0.02, 0.02, 0.02), 0.9), "flap": MET((0.6, 0.62, 0.65), 0.4),
            "vinyl": PR(c.image("dropv"), 0.5), "vinyl2": PR(d.image("dropv2"), 0.5), "rivet": CHROME()}


@obj("bkr_sticker", mass=0.02, weight=1.0, **RENT)
def bkr_sticker(b, rng, pal):
    """A BE KIND PLEASE REWIND sticker still stuck to a shard of black tape shell, the arrow pointing the
    way you never turned it."""
    b.box((0.1, 0.06, 0.012), mat="shell", bevel=0.002)
    for i in range(5):
        b.box((0.002, 0.03, 0.002), loc=(-0.035 + i * 0.006, -0.02, 0.006), mat="shell")
    _sheet(b, 0.075, 0.04, "sticker", bow=0.0015, curl=float(rng.uniform(0.0, 0.01)), n=6, loc=(0.008, 0.005, 0.0062))
    c = Canvas(300, 160, (0.98, 0.95, 0.2, 1))
    c.rect(0.02, 0.04, 0.98, 0.96, (0.9, 0.05, 0.1))
    c.rect(0.04, 0.08, 0.96, 0.92, (0.98, 0.95, 0.2))
    c.text_fit("BE KIND", 0.08, 0.86, 0.84, 0.3, (0.9, 0.05, 0.1), bold=True)
    c.text_fit("PLEASE REWIND", 0.08, 0.48, 0.84, 0.18, BB_BLUE, bold=True)
    c.poly([(0.1, 0.18), (0.22, 0.26), (0.22, 0.1)], BB_BLUE)
    c.poly([(0.2, 0.18), (0.32, 0.26), (0.32, 0.1)], BB_BLUE)
    c.rect(0.34, 0.15, 0.9, 0.21, BB_BLUE)
    return {"shell": P(BLACK, 0.4), "sticker": PR(c.image("bkr"), 0.4)}


# == D) CAR AUDIO: the trunk that rattled the block, 1988-2006 ======================================
AUDIO = dict(group="special", eras=(0, 1, 2, 3), tags=("caraudio",))
CAR_BRANDS = ["KICKSTANDZ", "ROCKFORD FOSSILGATE", "ALPINEAPPLE", "PIONEERD", "JLO AUDIO", "CERWIN VEGAS",
              "ORIONS BELT", "PHOENIX FOOLS GOLD", "HIFONICKS", "BOSSY AUDIO", "KENWOULD", "XPLODED", "MTXXX",
              "DIGITAL DESIGNS ON YOU", "AUDIOBAHNHOF", "SOUNDSTREAM OF CONSCIOUSNESS"]
WATTS = ["1000 WATTS", "2000 WATTS", "3500 WATTS MAX", "4000 WATTS PEAK", "10000 WATTS (PEAK) (LIE)"]


def _cone(b, R, depth, mat="cone", seg=40, loc=(0, 0, 0), sx=1.0):
    """A speaker cone: a shallow funnel from the dust cap out to the surround, scaled in X for ovals."""
    prof = [(R * 0.22, -depth), (R * 0.5, -depth * 0.6), (R * 0.8, -depth * 0.22), (R, 0.0)]
    b.lathe(prof, loc=loc, mat=mat, seg=seg, scale=(sx, 1, 1))


def _ring_frame(b, outer, inner_r, z0, z1, mat="frame"):
    """A flat basket rim: an outline with a hole in it. inner_r = (rx, ry) of the elliptical hole."""
    inner = []
    for (x, y) in outer:
        a = math.atan2(y, x)
        inner.append((inner_r[0] * math.cos(a), inner_r[1] * math.sin(a)))
    rings = [[(x, y, z1) for x, y in outer], [(x, y, z1) for x, y in inner], [(x, y, z0) for x, y in inner],
             [(x, y, z0) for x, y in outer], [(x, y, z1) for x, y in outer]]
    b.loft(rings, mat=mat, cap=False)


def _brand_dot(rng, name, brand=None, bg=(0.08, 0.08, 0.08), ink=(0.85, 0.85, 0.88), size=256):
    c = Canvas(size, size, (*bg, 1))
    c.circle(0.5, 0.5, 0.47, ink, ring=0.02)
    c.text_fit(brand or _ch(rng, CAR_BRANDS), 0.1, 0.56, 0.8, 0.14, ink, bold=True)
    d = np.hypot(c.x - 0.5, c.y - 0.5)
    c.a[..., 3] = (d < 0.5).astype(np.float32)
    return c.image(name)


@obj("speaker_6x9", mass=1.2, weight=1.0, **AUDIO)
def speaker_6x9(b, rng, pal):
    """The 6x9 oval for the rear deck: stamped basket, a cone in mica glitter or blue poly, a little
    tweeter on a bridge across the middle, and a sticker promising more watts than the car had."""
    a, bb = 0.23 / 2, 0.16 / 2
    sx = a / bb
    _ring_frame(b, ellipse(0.235, 0.165, 48), (a * 0.9, bb * 0.9), 0.0, 0.006)
    _cone(b, bb * 0.82, 0.035, loc=(0, 0, 0.0), sx=sx)
    sur = [(a * 0.86 * math.cos(TAU * i / 48), bb * 0.86 * math.sin(TAU * i / 48), 0.002) for i in range(49)]
    b.tube(sur, 0.0065, mat="surround", seg=8)
    b.cyl(0.03, 0.03, loc=(0, 0, -0.045), mat="magnet", seg=24)
    b.cyl(0.035, 0.005, loc=(0, 0, -0.06), mat="frame", seg=24)
    b.box((0.08, 0.008, 0.004), loc=(0, 0, 0.008), mat="frame", bevel=0.001)
    b.cyl(0.014, 0.012, loc=(0, 0, 0.012), mat="frame", seg=20)
    b.sphere(0.011, loc=(0, 0, 0.018), scale=(1, 1, 0.5), mat="tweet", seg=16)
    for k in range(4):
        ang = k * math.pi / 2 + math.pi / 4
        b.cyl(0.0035, 0.007, loc=(a * 0.92 * math.cos(ang), bb * 0.92 * math.sin(ang), 0.006), mat="screw", seg=8)
    b.plane(0.05, 0.05, loc=(-a * 0.55, bb * 0.0, 0.0065), mat="sticker", cuts=1)
    cone = _ch(rng, [("mica", (0.6, 0.6, 0.65)), ("poly", (0.1, 0.25, 0.75)), ("poly", (0.08, 0.08, 0.08)),
                     ("poly", (0.75, 0.75, 0.78))])
    return {"frame": MET((0.12, 0.12, 0.13), 0.5), "magnet": MET((0.25, 0.25, 0.27), 0.4),
            "cone": MET(cone[1], 0.35) if cone[0] == "mica" else P(cone[1], 0.35, coat=0.5),
            "surround": RUB((0.04, 0.04, 0.04)), "tweet": ("fabric", {"color": (0.1, 0.1, 0.1)}), "screw": CHROME(),
            "sticker": PR(_brand_dot(rng, "6x9dot", ink=(0.95, 0.75, 0.1)), 0.4, alpha_from_image=True)}


@obj("subwoofer", mass=7.0, weight=1.0, big=True, **AUDIO)
def subwoofer(b, rng, pal):
    """The 10 or the 12: a fat rubber surround you could pinch, a cone that hopped a quarter inch on every
    kick drum, a magnet stack heavier than the spare tire. Rattled the license plate off."""
    R = float(rng.choice([0.13, 0.155]))
    _ring_frame(b, rounded_rect(2 * R + 0.02, 2 * R + 0.02, R * 0.5, 8), (R * 0.93, R * 0.93), 0.0, 0.008)
    b.torus(R * 0.86, R * 0.07, loc=(0, 0, 0.01), mat="surround", seg=48, rseg=10)
    _cone(b, R * 0.8, 0.06, loc=(0, 0, 0.012))
    b.sphere(R * 0.22, loc=(0, 0, -0.04), scale=(1, 1, 0.35), mat="cap", seg=24)
    b.plane(R * 0.4, R * 0.4, loc=(0, 0, -0.04 + R * 0.22 * 0.35 + E), mat="capprint", cuts=2)
    b.cyl(R * 0.5, 0.06, loc=(0, 0, -0.1), mat="magnet", seg=32)
    b.cyl(R * 0.52, 0.006, loc=(0, 0, -0.067), mat="plate", seg=32)
    b.cyl(R * 0.52, 0.006, loc=(0, 0, -0.133), mat="plate", seg=32)
    for k in range(4):
        ang = k * math.pi / 2 + math.pi / 4
        b.box((0.02, R * 0.75, 0.004), loc=(R * 0.55 * math.cos(ang), R * 0.55 * math.sin(ang), -0.035),
              rot=(0, -0.5, ang - math.pi / 2), mat="frame")
        b.cyl(0.005, 0.008, loc=((R + 0.002) * math.cos(ang), (R + 0.002) * math.sin(ang), 0.008), mat="screw", seg=8)
    brand = _ch(rng, CAR_BRANDS)
    cone = _ch(rng, [(0.08, 0.08, 0.08), (0.08, 0.08, 0.08), (0.1, 0.25, 0.75), (0.75, 0.75, 0.78), (0.6, 0.05, 0.05)])
    return {"frame": MET((0.1, 0.1, 0.11), 0.45), "surround": RUB((0.04, 0.04, 0.045)), "cone": P(cone, 0.4, coat=0.3),
            "cap": P(cone, 0.25, coat=0.8), "magnet": MET((0.2, 0.2, 0.22), 0.35),
            "plate": MET(_ch(rng, [(0.85, 0.15, 0.15), (0.15, 0.35, 0.9), (0.75, 0.75, 0.78)]), 0.25), "screw": CHROME(),
            "capprint": PR(_brand_dot(rng, "subdot", brand, bg=cone, ink=(0.95, 0.95, 0.95)), 0.3, alpha_from_image=True)}


def _airbrush(rng, name):
    """An amp top airbrushed at the swap meet: a sunset gradient, flames licking up from the bottom,
    a lightning bolt, the brand in chrome-ish letters, and the watts."""
    top, bot = _ch(rng, [((0.1, 0.0, 0.3), (0.9, 0.1, 0.5)), ((0.0, 0.05, 0.2), (0.0, 0.7, 0.8)),
                         ((0.05, 0.05, 0.05), (0.6, 0.05, 0.05)), ((0.2, 0.0, 0.4), (1.0, 0.5, 0.0))])
    c = Canvas(512, 352, (0, 0, 0, 1))
    c.gradient(top, bot)
    for k in range(9):          # flames
        x = k / 8
        h = float(rng.uniform(0.25, 0.55))
        pts = [(x - 0.07, 0.0)]
        for t in np.linspace(0, 1, 8):
            pts.append((x - 0.07 * (1 - t) + 0.04 * math.sin(t * 6 + k), h * t))
        pts += [(x + 0.03 * math.sin(k), h + 0.05)]
        for t in np.linspace(1, 0, 8):
            pts.append((x + 0.07 * (1 - t) + 0.03 * math.sin(t * 5 + k), h * t))
        c.poly(pts, (1.0, 0.45, 0.05))
        c.poly([(px * 0.97 + x * 0.03, py * 0.7) for px, py in pts], (1.0, 0.85, 0.15))
    c.poly([(0.72, 0.95), (0.62, 0.6), (0.7, 0.62), (0.6, 0.3), (0.82, 0.7), (0.74, 0.68), (0.84, 0.95)], (0.6, 0.9, 1.0))
    brand = _ch(rng, CAR_BRANDS)
    c.text_fit(brand, 0.06, 0.92, 0.6, 0.12, (0.05, 0.05, 0.08), bold=True)
    c.text_fit(brand, 0.055, 0.925, 0.6, 0.12, (0.85, 0.88, 0.95), bold=True)
    c.text_fit(_ch(rng, WATTS), 0.06, 0.74, 0.55, 0.07, (1, 1, 1), bold=True)
    c.text_fit("CLASS A/B MONO BLOCK", 0.06, 0.64, 0.5, 0.04, (1, 1, 1))
    c.noise(rng, 0.03)
    return c.image(name)


@obj("car_amp", mass=4.0, weight=1.0, big=True, **AUDIO)
def car_amp(b, rng, pal):
    """The amp: an aluminum slab with fins like a radiator, an airbrushed top, a terminal block for the
    fat power wire and a row of lights that meant the alternator was crying."""
    L, Wd, H = 0.3, 0.2, 0.055
    b.box((L, Wd * 0.7, H), loc=(0, 0, H / 2), mat="body", bevel=0.004)
    b.plane(L * 0.96, Wd * 0.66, loc=(0, 0, H + E), mat="top", cuts=3)
    nf = 9
    for sy in (-1, 1):
        for i in range(nf):
            z = 0.006 + i * (H - 0.008) / (nf - 1)
            b.box((L, Wd * 0.15, 0.0028), loc=(0, sy * (Wd * 0.35 + Wd * 0.075), z), mat="fin", bevel=0.0008)
        b.box((L, 0.004, H), loc=(0, sy * (Wd * 0.35 + 0.002), H / 2), mat="fin")
    for sx in (-1, 1):
        b.box((0.012, Wd, H + 0.004), loc=(sx * (L / 2 + 0.006), 0, H / 2), mat="cap", bevel=0.004)
    ex = L / 2 + 0.012
    b.plane(Wd * 0.85, H * 0.8, loc=(ex + E, 0, H / 2), rot=(math.pi / 2, 0, math.pi / 2), mat="panel", cuts=2)
    for i, y in enumerate((-0.06, -0.035, -0.01)):
        b.box((0.008, 0.018, 0.016), loc=(ex + 0.004, y, H * 0.42), mat="term", bevel=0.001)
        b.cyl(0.004, 0.008, loc=(ex + 0.006, y, H * 0.42 + 0.012), mat="screw", seg=10)
    for y in (0.025, 0.045):
        for z in (H * 0.32, H * 0.62):
            b.cyl(0.0045, 0.01, loc=(ex + 0.005, y, z), rot=(0, math.pi / 2, 0), mat="rca", seg=12)
    b.cyl(0.0025, 0.004, loc=(ex + 0.002, 0.075, H * 0.75), rot=(0, math.pi / 2, 0), mat="led", seg=10)
    b.cyl(0.0025, 0.004, loc=(ex + 0.002, 0.075, H * 0.55), rot=(0, math.pi / 2, 0), mat="led2", seg=10)
    pn = Canvas(256, 96, (0.08, 0.08, 0.09, 1))
    for i, t in enumerate(["B+", "REM", "GND"]):
        pn.text(t, 0.06 + i * 0.12, 0.25, 0.12, (0.85, 0.85, 0.85), bold=True)
    pn.text("INPUT", 0.6, 0.9, 0.12, (0.85, 0.85, 0.85), bold=True)
    pn.text("PROT PWR", 0.6, 0.25, 0.1, (0.85, 0.85, 0.85))
    body = _ch(rng, [(0.1, 0.1, 0.11), (0.1, 0.1, 0.11), (0.7, 0.72, 0.75), (0.15, 0.2, 0.55), (0.55, 0.05, 0.08)])
    return {"body": MET(body, 0.3), "fin": MET(body, 0.32), "cap": P(BLACK, 0.4), "top": PR(_airbrush(rng, "amptop"), 0.25,
                                                                                         coat=0.9),
            "panel": PR(pn.image("amppanel"), 0.4), "term": MET((0.95, 0.75, 0.35), 0.2), "screw": CHROME(),
            "rca": MET((0.95, 0.75, 0.35), 0.2), "led": P((0.1, 1.0, 0.2), 0.3, glow=3.0),
            "led2": P((1.0, 0.1, 0.05), 0.3, glow=2.0 if rng.random() < 0.4 else 0.0)}


def _faceplate_print(rng, name):
    """A detachable faceplate's face: wild swoosh graphics, a blue VFD display, buttons everywhere."""
    c = Canvas(512, 140, (0.06, 0.06, 0.07, 1))
    acc = _ch(rng, [(0.1, 0.5, 1.0), (1.0, 0.45, 0.05), (0.6, 0.2, 1.0), (0.1, 0.9, 0.6), (1.0, 0.1, 0.3)])
    for k in range(3):
        xs = np.linspace(0, 1, 40)
        ys = 0.5 + 0.35 * np.sin(xs * (5 + k) + k * 1.3)
        c.line(list(zip(xs, ys)), 0.02 + k * 0.01, (*acc, 0.5 - k * 0.12))
    c.rect(0.3, 0.42, 0.72, 0.85, (0.01, 0.03, 0.06))
    vfd = (0.25, 0.75, 1.0)
    c.text_fit(_ch(rng, ["BASS BOOST", "TRK 07 3:47", "DISC 3", "FM 97.1", "WELCOME", "LOUDNESS", "EQ: ROCK"]),
               0.32, 0.8, 0.38, 0.28, vfd, bold=True)
    for i in range(10):
        c.rect(0.32 + i * 0.038, 0.46, 0.345 + i * 0.038, 0.46 + 0.02 * (1 + (i * 7) % 5), vfd)
    c.text_fit(_ch(rng, CAR_BRANDS), 0.03, 0.95, 0.24, 0.16, (0.9, 0.9, 0.92), bold=True)
    c.text_fit("CD/MP3 RECEIVER 50WX4", 0.03, 0.74, 0.24, 0.08, acc)
    for i in range(6):
        c.rect(0.3 + i * 0.07, 0.08, 0.36 + i * 0.07, 0.3, (0.22, 0.22, 0.25), soft=0.01)
        c.text(str(i + 1), 0.32 + i * 0.07, 0.25, 0.12, (0.85, 0.85, 0.85), bold=True)
    c.rect(0.76, 0.6, 0.98, 0.66, (0.01, 0.01, 0.01))           # CD slot
    c.text_fit("SRC  MUTE  DISP", 0.76, 0.35, 0.22, 0.09, (0.85, 0.85, 0.85))
    img = c.image(name)
    img["lcd"] = True
    return img


def _faceplate(b, rng, w, h, d, loc=(0, 0, 0), rot=(0, 0, 0)):
    b.frame = Matrix.Translation(loc) @ Matrix.Rotation(rot[0], 4, "X") @ Matrix.Rotation(rot[2], 4, "Z")
    b.box((w, h, d), mat="fp", bevel=0.004)
    b.plane(w * 0.97, h * 0.92, loc=(0, 0, d / 2 + E), mat="fpprint", cuts=3)
    b.cyl(0.013, 0.008, loc=(-w * 0.32, -h * 0.05, d / 2 + 0.004), mat="knob", seg=24)
    b.cyl(0.0105, 0.0085, loc=(-w * 0.32, -h * 0.05, d / 2 + 0.004), mat="knobring", seg=24)
    b.frame = Matrix.Identity(4)


@obj("head_unit", mass=1.5, weight=1.0, **AUDIO)
def head_unit(b, rng, pal):
    """The in-dash deck with the detachable face: blue display, a volume knob the size of a cookie,
    graphics that looked like a energy drink exploded. Face half popped off, ready for the case."""
    w, h = 0.178, 0.05
    b.box((w, h, 0.15), loc=(0, 0, -0.075 - 0.006), mat="chassis", bevel=0.002)
    for i in range(6):
        b.box((w * 0.9, 0.002, 0.003), loc=(0, h / 2, -0.03 - i * 0.02), mat="vent")
    b.box((w * 0.98, h * 0.98, 0.006), loc=(0, 0, -0.003), mat="chassis", bevel=0.001)
    b.box((0.03, 0.02, 0.06), loc=(0, -0.01, -0.18), mat="plug", bevel=0.002)
    pop = float(rng.uniform(0.0, 0.6))
    _faceplate(b, rng, w * 0.99, h * 0.98, 0.016, loc=(0, -h * pop * 0.5, 0.009 + pop * 0.02), rot=(pop * 0.6, 0, 0))
    return {"chassis": MET((0.15, 0.15, 0.16), 0.5), "vent": P(BLACK, 0.8), "plug": P((0.85, 0.85, 0.85), 0.5),
            "fp": P((0.08, 0.08, 0.09), 0.3, coat=0.6), "fpprint": PR(_faceplate_print(rng, "fp"), 0.2, glow=0.6),
            "knob": P((0.15, 0.15, 0.16), 0.35), "knobring": MET((0.75, 0.75, 0.8), 0.25)}


@obj("faceplate_case", mass=0.15, weight=1.0, **AUDIO)
def faceplate_case(b, rng, pal):
    """The faceplate's hard case: a little clamshell the size of a glasses case, so nobody smashed your
    window for a deck with no face. They smashed it anyway."""
    w, h, d = 0.195, 0.065, 0.026
    b.box((w, h, d / 2), loc=(0, 0, d / 4), mat="case", bevel=0.006)
    _faceplate(b, rng, 0.176, 0.049, 0.012, loc=(0, 0, d / 2 + 0.002))
    ang = float(rng.uniform(1.2, 2.2))
    b.frame = Matrix.Translation((0, h / 2, d / 2)) @ Matrix.Rotation(ang, 4, "X")
    b.box((w, h, d / 2), loc=(0, -h / 2, d / 4), mat="case", bevel=0.006)
    b.plane(w * 0.6, h * 0.4, loc=(0, -h / 2, d / 2 + E), mat="logo", cuts=1)
    b.frame = Matrix.Identity(4)
    for i in range(3):
        b.box((0.01, 0.004, 0.006), loc=(-0.05 + i * 0.05, h / 2 + 0.001, d / 2), mat="hinge", bevel=0.001)
    c = Canvas(256, 80, (0.1, 0.1, 0.11, 1))
    c.text_fit(_ch(rng, CAR_BRANDS), 0.06, 0.8, 0.88, 0.5, (0.35, 0.35, 0.38), bold=True)
    _alpha_from_bg(c, (0.1, 0.1, 0.11))
    return {"case": P((0.1, 0.1, 0.11), 0.6, texture=0.6), "logo": PR(c.image("fpcaselogo"), 0.6, alpha_from_image=True),
            "hinge": MET(SILVER, 0.3), "fp": P((0.08, 0.08, 0.09), 0.3, coat=0.6),
            "fpprint": PR(_faceplate_print(rng, "fpc"), 0.2, glow=0.3),
            "knob": P((0.15, 0.15, 0.16), 0.35), "knobring": MET((0.75, 0.75, 0.8), 0.25)}


def _rca_plug(b, p, d, mat_body, mat_ring):
    x, y, z = p
    a = math.atan2(d[1], d[0])
    rot = (0, math.pi / 2, a)
    b.cyl(0.0065, 0.026, loc=(x, y, z), rot=rot, mat=mat_body, seg=16)
    b.cyl(0.0058, 0.012, loc=(x + math.cos(a) * 0.018, y + math.sin(a) * 0.018, z), rot=rot, mat="gold", seg=16)
    b.cyl(0.0018, 0.012, loc=(x + math.cos(a) * 0.026, y + math.sin(a) * 0.026, z), rot=rot, mat="gold", seg=8)
    b.torus(0.0066, 0.0012, loc=(x + math.cos(a) * 0.004, y + math.sin(a) * 0.004, z), rot=rot, mat=mat_ring, seg=16,
            rseg=5)


@obj("rca_cables", mass=0.15, weight=1.0, **AUDIO)
def rca_cables(b, rng, pal):
    """Twisted-pair RCA interconnects, blue jacket, chunky gold plugs with a red ring and a white ring.
    Paid extra for the gold. Heard the difference. Didn't."""
    pts_a, pts_b = [], []
    n = 70
    turns = 9
    ang = 0.0
    x, y = -0.08, -0.05
    for i in range(n):
        t = i / (n - 1)
        ang += float(rng.normal(0, 0.12))
        x += math.cos(ang + 0.4 * math.sin(t * 7)) * 0.0045
        y += math.sin(ang + 0.4 * math.sin(t * 7)) * 0.0045 + 0.0012 * math.sin(t * 5)
        tw = TAU * turns * t
        pts_a.append((x, y + 0.0035 * math.cos(tw), 0.0035 * math.sin(tw)))
        pts_b.append((x, y - 0.0035 * math.cos(tw), -0.0035 * math.sin(tw)))
    jacket = _ch(rng, [(0.1, 0.3, 0.9), (0.1, 0.3, 0.9), (0.05, 0.05, 0.05), (0.85, 0.1, 0.1), (0.6, 0.6, 0.62)])
    b.tube(pts_a, 0.0028, mat="jacket", seg=8)
    b.tube(pts_b, 0.0028, mat="jacket2", seg=8)
    for pts, ring, sgn in ((pts_a, "red", 1), (pts_b, "white", -1)):
        for end in (0, -1):
            p = pts[end]
            q = pts[1 if end == 0 else -2]
            d = (p[0] - q[0], p[1] - q[1])
            L = math.hypot(*d) or 1.0
            d = (d[0] / L, d[1] / L)
            _rca_plug(b, (p[0] + d[0] * 0.012, p[1] + d[1] * 0.012 + sgn * 0.003, p[2]), d, "plugbody", ring)
    return {"jacket": P(jacket, 0.3, coat=0.5), "jacket2": P(tuple(x * 0.85 for x in jacket), 0.3, coat=0.5),
            "plugbody": MET((0.12, 0.12, 0.13), 0.3), "gold": ("gold", {}), "red": P((0.9, 0.05, 0.05), 0.3),
            "white": P(WHITE, 0.3)}


@obj("stiff_cap", mass=1.0, weight=1.0, **AUDIO)
def stiff_cap(b, rng, pal):
    """The stiffening capacitor: a chrome can the size of a soda bottle with a blue digital readout on
    top that dipped from 14.4 to 11.9 every time the bass hit. That was the point."""
    R, H = 0.035, 0.2
    b.cyl(R, H, loc=(0, 0, 0), rot=(0, math.pi / 2, 0), mat="can", seg=36)
    for sx in (-1, 1):
        b.cyl(R * 1.06, 0.03, loc=(sx * (H / 2 + 0.01), 0, 0), rot=(0, math.pi / 2, 0), mat="endcap", seg=36)
    b.plane(0.05, 0.022, loc=(H / 2 + 0.025 + E, 0, 0.012), rot=(0, math.pi / 2, 0), mat="lcd", cuts=1)
    for sy in (-1, 1):
        b.cyl(0.006, 0.014, loc=(H / 2 + 0.03, sy * 0.022, -0.016), rot=(0, math.pi / 2, 0), mat="gold", seg=12)
        b.cyl(0.0035, 0.01, loc=(H / 2 + 0.042, sy * 0.022, -0.016), rot=(0, math.pi / 2, 0), mat="screw", seg=10)
    # a band of print around the can (lathe UVs wrap it once)
    b.lathe([(R * 1.003, -H * 0.38), (R * 1.003, H * 0.38)], rot=(0, math.pi / 2, 0), mat="band", seg=48)
    d = Canvas(200, 88, (0.0, 0.03, 0.12, 1))
    volts = _ch(rng, ["14.4", "13.8", "12.1", "11.9", "14.1"])
    d.text_fit(volts + "V", 0.08, 0.85, 0.84, 0.7, (0.3, 0.75, 1.0), bold=True)
    dd = d.image("capvfd")
    dd["lcd"] = True
    c = Canvas(512, 160, (0.05, 0.05, 0.06, 1))
    brand = _ch(rng, CAR_BRANDS)
    c.text_fit(brand, 0.05, 0.85, 0.42, 0.22, (0.9, 0.9, 0.92), bold=True)
    c.text_fit(_ch(rng, ["1.0 FARAD", "2.0 FARAD", "3.5 FARAD", "5 FARAD (DIGITAL!)"]), 0.05, 0.5, 0.42, 0.18,
               (0.3, 0.75, 1.0), bold=True)
    c.text_fit("STIFFENING CAPACITOR - 20VDC", 0.05, 0.2, 0.42, 0.09, (0.8, 0.8, 0.8))
    c.text_fit(brand, 0.55, 0.85, 0.42, 0.22, (0.9, 0.9, 0.92), bold=True)
    c.text_fit("HIGH PERFORMANCE", 0.55, 0.5, 0.42, 0.12, (0.3, 0.75, 1.0), bold=True)
    t = Canvas(160, 512)                     # lathe UVs run v along the can: turn the print so text runs lengthwise
    t.a = np.ascontiguousarray(np.transpose(c.a, (1, 0, 2))[:, ::-1])
    return {"can": CHROME() if rng.random() < 0.5 else P(BLACK, 0.25, coat=0.9), "endcap": P(BLACK, 0.4),
            "band": PR(t.image("capwrap"), 0.25, coat=0.8, ext="REPEAT"),
            "lcd": PR(dd, 0.2, glow=2.5), "gold": ("gold", {}), "screw": CHROME()}


@obj("underglow", mass=0.4, weight=1.0, **AUDIO)
def underglow(b, rng, pal):
    """A neon underglow tube: glass-clear tube, gas glowing inside, black end caps and a cord to the
    switch on the dash. Made a Civic look like it was hovering. Got pulled over for it."""
    L = 0.3
    col = _ch(rng, [(0.15, 0.4, 1.0), (0.7, 0.15, 1.0), (0.1, 1.0, 0.4), (1.0, 0.1, 0.5), (0.1, 0.9, 1.0)])
    bend = float(rng.uniform(-0.03, 0.03))
    pts = [(-L / 2 + L * i / 10, bend * math.sin(math.pi * i / 10), 0) for i in range(11)]
    b.tube(pts, 0.0105, mat="glass", seg=16)
    b.tube(pts, 0.0085, mat="neon", seg=12)
    for sx in (-1, 1):
        b.cyl(0.0135, 0.03, loc=(sx * (L / 2 + 0.012), 0, 0), rot=(0, math.pi / 2, 0), mat="cap", seg=16)
    for sx, k in ((-1, 0), (1, 1)):
        b.box((0.016, 0.01, 0.006), loc=(sx * L * 0.3, 0, -0.013), mat="clip")
    cord = [(L / 2 + 0.027, 0, 0)]
    for i in range(10):
        cord.append((cord[-1][0] + 0.012, cord[-1][1] + 0.01 * math.sin(i), -0.002 * i))
    b.tube(cord, 0.002, mat="cap", seg=6)
    return {"glass": T((0.9, 0.95, 1.0), 0.03), "neon": P(col, 0.2, glow=14.0), "cap": P(BLACK, 0.4),
            "clip": P((0.2, 0.2, 0.2), 0.5)}


@obj("bass_knob", mass=0.1, weight=1.0, **AUDIO)
def bass_knob(b, rng, pal):
    """The remote bass knob, screwed under the dash by your knee: one fat knob, BASS in white letters, a
    red light, and a cable running all the way back to the trunk. Turned it to the right. Always."""
    b.box((0.06, 0.04, 0.03), loc=(0, 0, 0.015), mat="body", bevel=0.005)
    b.box((0.08, 0.04, 0.003), loc=(0, 0.0, 0.0015), mat="body", bevel=0.001)
    for sx in (-1, 1):
        b.cyl(0.0035, 0.004, loc=(sx * 0.034, 0, 0.004), mat="screw", seg=10)
    b.cyl(0.015, 0.016, loc=(0, -0.02 - 0.008, 0.017), rot=(math.pi / 2, 0, 0), mat="knob", seg=28)
    b.cyl(0.013, 0.002, loc=(0, -0.0365, 0.017), rot=(math.pi / 2, 0, 0), mat="cap", seg=28)
    b.box((0.002, 0.002, 0.009), loc=(0, -0.0372, 0.022), rot=(0, float(rng.uniform(-0.3, 1.2)), 0), mat="mark")
    b.plane(0.056, 0.026, loc=(0, -0.0201, 0.015), rot=(math.pi / 2, 0, 0), mat="face", cuts=1)
    b.cyl(0.0022, 0.003, loc=(0.022, -0.0205, 0.025), rot=(math.pi / 2, 0, 0), mat="led", seg=10)
    cord = [(0, 0.02, 0.012)]
    for i in range(14):
        cord.append((cord[-1][0] + 0.008 * math.sin(i * 0.7), cord[-1][1] + 0.01, cord[-1][2] - 0.0007 * i))
    b.tube(cord, 0.0022, mat="body", seg=6)
    c = Canvas(256, 120, (0.06, 0.06, 0.07, 1))
    c.text("BASS", 0.04, 0.9, 0.24, (1, 1, 1), bold=True)
    c.text("MIN", 0.04, 0.2, 0.12, (0.8, 0.8, 0.8))
    c.text("MAX", 0.8, 0.2, 0.12, (1.0, 0.2, 0.2), bold=True)
    for i in range(9):
        a = math.pi * (1.1 - i * 0.15)
        c.line([(0.5 + 0.12 * math.cos(a), 0.45 + 0.3 * math.sin(a)), (0.5 + 0.16 * math.cos(a), 0.45 + 0.4 * math.sin(a))],
               0.02, (0.8, 0.8, 0.8))
    return {"body": P((0.08, 0.08, 0.09), 0.45), "knob": P((0.15, 0.15, 0.16), 0.35), "cap": MET(SILVER, 0.2),
            "mark": P(WHITE, 0.3), "face": PR(c.image("bassknob"), 0.4), "screw": CHROME(),
            "led": P((1.0, 0.05, 0.05), 0.3, glow=3.0)}


@obj("cd_changer", mass=3.0, weight=1.0, big=True, **AUDIO)
def cd_changer(b, rng, pal):
    """The trunk-mounted CD changer: a steel box bolted to the trunk floor, a sliding door, and a
    magazine of ten discs you loaded once in 1998 and never changed again."""
    L, Wd, H = 0.26, 0.18, 0.08
    b.box((L, Wd, H), loc=(0, 0, H / 2), mat="body", bevel=0.004)
    b.plane(L * 0.6, Wd * 0.4, loc=(-0.03, 0.02, H + E), mat="label", cuts=2)
    fx = L / 2
    b.box((0.004, Wd * 0.75, H * 0.75), loc=(fx + 0.001, 0, H / 2), mat="slot")
    door = float(rng.uniform(0.6, 1.5))
    b.frame = Matrix.Translation((fx + 0.002, 0, H * 0.88)) @ Matrix.Rotation(-door, 4, "Y")
    b.box((0.003, Wd * 0.76, H * 0.76), loc=(0, 0, -H * 0.38), mat="door", bevel=0.0008)
    b.frame = Matrix.Identity(4)
    out = float(rng.uniform(0.02, 0.09))
    mx = fx - 0.11 + out
    b.box((0.13, Wd * 0.7, H * 0.68), loc=(mx, 0, H / 2), mat="mag", bevel=0.002)
    for i in range(10):
        z = H * 0.2 + i * H * 0.062
        b.box((0.002, Wd * 0.66, 0.0015), loc=(mx + 0.066, 0, z), mat="magslot")
        if i % 3 == 0 and out > 0.06:
            _disc(b, loc=(mx - 0.005, 0, z + 0.002), mat="discs", r=0.06, t=0.0012)
    b.plane(0.03, Wd * 0.4, loc=(mx + 0.0655 + E, 0, H * 0.82), rot=(0, math.pi / 2, 0), mat="maglab", cuts=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((0.03, 0.02, 0.006), loc=(sx * (L / 2 - 0.02), sy * (Wd / 2 + 0.01), 0.003), mat="bracket")
    c = Canvas(320, 160, (0.12, 0.12, 0.13, 1))
    br = _ch(rng, CAR_BRANDS)
    c.text_fit(br, 0.05, 0.9, 0.9, 0.22, (0.9, 0.9, 0.92), bold=True)
    c.text_fit(_ch(rng, ["10-DISC CD AUTOCHANGER", "12-DISC CHANGER", "6-DISC MAGAZINE CHANGER"]), 0.05, 0.6, 0.9, 0.12,
               (0.3, 0.75, 1.0), bold=True)
    c.text_fit("MOUNT HORIZONTAL OR VERTICAL", 0.05, 0.35, 0.9, 0.08, (0.8, 0.8, 0.8))
    c.text_fit("SHOCK PROOF-ISH", 0.05, 0.18, 0.9, 0.08, (0.8, 0.8, 0.8))
    m = Canvas(64, 128, (0.85, 0.85, 0.85, 1))
    for i in range(10):
        m.text(str(i + 1), 0.15, 0.95 - i * 0.095, 0.07, (0.1, 0.1, 0.1), bold=True)
    body = _ch(rng, [(0.15, 0.15, 0.16), (0.7, 0.72, 0.75), (0.1, 0.1, 0.1)])
    return {"body": MET(body, 0.45), "label": PR(c.image("chglab"), 0.4), "slot": P(BLACK, 0.8),
            "door": MET(body, 0.4), "mag": P((0.12, 0.12, 0.13), 0.5), "magslot": P(BLACK, 0.8),
            "maglab": PR(m.image("chgmag"), 0.5), "bracket": MET(SILVER, 0.4),
            "discs": ("disc", {"color": (0.85, 0.85, 0.88), "film": 520.0}), "hub": HUB}


@obj("cassette_adapter", mass=0.05, weight=1.0, **AUDIO)
def cassette_adapter(b, rng, pal):
    """The cassette adapter: a tape with no tape in it, a fake head where the tape should be, and a thin
    cord out the side to the portable CD player sliding around the passenger seat. Clicked forever."""
    W, H, D = 0.1, 0.064, 0.012
    b.box((W, H, D), mat="shell", bevel=0.0015)
    b.plane(W * 0.86, H * 0.62, loc=(0, 0.006, D / 2 + E), mat="label", cuts=2)
    b.box((0.065, 0.008, D * 0.95), loc=(0, -H / 2 + 0.002, 0), mat="shell2", bevel=0.001)
    b.box((0.012, 0.004, 0.008), loc=(0, -H / 2 - 0.0005, 0), mat="head", bevel=0.001)
    for sx in (-1, 1):
        b.cyl(0.0065, D * 1.02, loc=(sx * 0.021, 0.006, 0), mat="hub", seg=12)
    pts = [(W / 2, H * 0.2, 0)]
    x, y = pts[0][0], pts[0][1]
    ang = 0.0
    for i in range(22):
        ang += float(rng.normal(0, 0.45))
        x += math.cos(ang) * 0.012
        y += math.sin(ang) * 0.012
        pts.append((x, y, 0.0015 * math.sin(i)))
    b.tube(pts, 0.0014, mat="cord", seg=6)
    end = pts[-1]
    d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
    a = math.atan2(d[1], d[0])
    b.cyl(0.0035, 0.018, loc=(end[0] + math.cos(a) * 0.009, end[1] + math.sin(a) * 0.009, end[2]),
          rot=(0, math.pi / 2, a), mat="cord", seg=12)
    b.cyl(0.0017, 0.014, loc=(end[0] + math.cos(a) * 0.025, end[1] + math.sin(a) * 0.025, end[2]),
          rot=(0, math.pi / 2, a), mat="jack", seg=10)
    c = Canvas(320, 160, (0.92, 0.92, 0.9, 1))
    c.rect(0, 0.75, 1, 1, (0.9, 0.1, 0.1))
    c.text_fit("CAR CASSETTE ADAPTER", 0.04, 0.95, 0.92, 0.15, (1, 1, 1), bold=True)
    c.text_fit(_ch(rng, ["FOR DISCMANGLED", "FOR CD AND MP3", "PLAYS YOUR WALKMAYBE THRU YOUR CAR"]), 0.04, 0.68, 0.92,
               0.1, (0.1, 0.1, 0.1), bold=True)
    c.rect(0.2, 0.08, 0.8, 0.45, (0.25, 0.25, 0.28))
    for cx in (0.35, 0.65):
        c.circle(cx, 0.27, 0.12, (0.85, 0.85, 0.85))
        c.circle(cx, 0.27, 0.06, (0.1, 0.1, 0.1))
    return {"shell": P(_ch(rng, [BLACK, CHARCOAL, (0.85, 0.85, 0.87)]), 0.4), "shell2": P((0.2, 0.2, 0.22), 0.4),
            "head": MET(SILVER, 0.2), "hub": P(WHITE, 0.4), "label": PR(c.image("cassad"), 0.4),
            "cord": P(BLACK, 0.4), "jack": MET((0.95, 0.75, 0.35), 0.2)}


@obj("tweeter", mass=0.1, weight=1.0, **AUDIO)
def tweeter(b, rng, pal):
    """A component tweeter on its swivel cup: a little silk dome, a chrome ring, a stick-on base you
    glued to the dash and aimed at your own ear."""
    b.lathe([(0.0, -0.014), (0.022, -0.012), (0.025, 0.0), (0.0225, 0.004)], mat="cup", seg=32)
    b.torus(0.019, 0.0025, loc=(0, 0, 0.004), mat="ring", seg=32, rseg=6)
    b.sphere(0.015, loc=(0, 0, 0.0), scale=(1, 1, 0.55), mat="dome", seg=24)
    b.cyl(0.006, 0.01, loc=(0, 0, 0.012), mat="ring", seg=12)
    b.box((0.003, 0.03, 0.002), loc=(0, 0, 0.009), mat="ring")
    b.box((0.03, 0.003, 0.002), loc=(0, 0, 0.009), mat="ring")
    b.sphere(0.009, loc=(0.0, 0.0, -0.016), mat="cup", seg=12)
    b.cyl(0.024, 0.008, loc=(0.0, 0.0, -0.026), mat="cup", seg=24, r2=0.018)
    b.tube([(0, 0.02, -0.026), (0.01, 0.05, -0.028), (0.0, 0.08, -0.03)], 0.0016, mat="wire", seg=6)
    return {"cup": P((0.08, 0.08, 0.09), 0.35), "ring": CHROME(), "dome": ("fabric", {"color": (0.08, 0.08, 0.09)})
            if rng.random() < 0.6 else MET((0.85, 0.75, 0.4), 0.15), "wire": P((0.85, 0.1, 0.1), 0.4)}


@obj("amp_kit", mass=1.5, weight=1.0, **AUDIO)
def amp_kit(b, rng, pal):
    """The amp wiring kit: a coil of fat red power wire, a short blue ground, an inline fuse holder you
    could see the fuse through, and a ring terminal crimped with pliers."""
    pts = helix(0.05, 0.007, 3.2, 28, start=(0, 0, 0))
    pts = [(x + 0.004 * math.sin(i * 0.9), y, z + 0.002 * math.cos(i * 1.3)) for i, (x, y, z) in enumerate(pts)]
    b.tube(pts, 0.0045, mat="power", seg=10)
    tail = [pts[-1]]
    for i in range(6):
        tail.append((tail[-1][0] + 0.012, tail[-1][1] - 0.012, tail[-1][2] - 0.001))
    b.tube(tail, 0.0045, mat="power", seg=10)
    e = tail[-1]
    b.cyl(0.009, 0.05, loc=(e[0] + 0.018, e[1] - 0.018, e[2]), rot=(0, math.pi / 2, -math.pi / 4), mat="fuseh", seg=16)
    b.box((0.022, 0.006, 0.002), loc=(e[0] + 0.018, e[1] - 0.018, e[2]), rot=(0, 0, -math.pi / 4), mat="fuse", bevel=0.0005)
    b.cyl(0.0095, 0.014, loc=(e[0] + 0.004, e[1] - 0.004, e[2]), rot=(0, math.pi / 2, -math.pi / 4), mat="cap", seg=16)
    head = [pts[0]]
    for i in range(5):
        head.append((head[-1][0] - 0.01, head[-1][1] + 0.01, head[-1][2]))
    b.tube(head, 0.0045, mat="power", seg=10)
    h = head[-1]
    b.cyl(0.005, 0.014, loc=(h[0] - 0.005, h[1] + 0.005, h[2]), rot=(0, math.pi / 2, 3 * math.pi / 4), mat="ringt", seg=10)
    b.torus(0.008, 0.0022, loc=(h[0] - 0.017, h[1] + 0.017, h[2]), mat="ringt", seg=16, rseg=6)
    gnd = [(0.06, -0.06, 0.0)]
    for i in range(8):
        gnd.append((gnd[-1][0] - 0.01 + 0.004 * math.sin(i), gnd[-1][1] - 0.008, 0.001))
    b.tube(gnd, 0.0035, mat="ground", seg=8)
    b.plane(0.06, 0.03, loc=(0.0, 0.0, 0.032), mat="tag", cuts=1)
    c = Canvas(256, 128, (0.95, 0.85, 0.15, 1))
    c.text_fit("8 GAUGE AMP KIT", 0.05, 0.9, 0.9, 0.2, (0.05, 0.05, 0.05), bold=True)
    c.text_fit(_ch(rng, CAR_BRANDS), 0.05, 0.55, 0.9, 0.15, (0.8, 0.05, 0.05), bold=True)
    c.text_fit("1500W - 17FT POWER WIRE", 0.05, 0.25, 0.9, 0.1, (0.05, 0.05, 0.05))
    return {"power": P((0.85, 0.06, 0.06), 0.3, coat=0.6), "ground": P((0.1, 0.25, 0.85), 0.3, coat=0.6),
            "fuseh": T((0.9, 0.92, 0.95), 0.08), "fuse": P((0.1, 0.5, 1.0), 0.3), "cap": P(BLACK, 0.4),
            "ringt": ("gold", {}), "tag": PR(c.image("ampkit"), 0.5)}


@obj("audio_stickers", mass=0.01, weight=1.0, **AUDIO)
def audio_stickers(b, rng, pal):
    """The window decals: a long windshield banner in chrome die-cut letters, plus the stickers that came
    in every box, so the whole lot knew what was in your trunk before they heard it."""
    specs = {}
    brand = _ch(rng, CAR_BRANDS)
    c = Canvas(768, 112, (0.05, 0.05, 0.06, 1))
    c.text_fit(brand, 0.03, 0.88, 0.94, 0.75, (0.88, 0.9, 0.95), bold=True, spacing=1.05)
    _sheet(b, 0.24, 0.035, "banner", bow=0.004, curl=0.0, n=9, loc=(0, 0.04, 0), wob=0.0015)
    specs["banner"] = PR(c.image("banner"), 0.3)
    for k in range(int(rng.integers(3, 6))):
        x, y = float(rng.uniform(-0.09, 0.09)), float(rng.uniform(-0.06, 0.0))
        rz = float(rng.uniform(-0.6, 0.6))
        s = float(rng.uniform(0.045, 0.07))
        style = k % 3
        bg = _ch(rng, [(0.05, 0.05, 0.06), (0.95, 0.75, 0.1), (0.85, 0.05, 0.08), (0.95, 0.95, 0.95), (0.1, 0.3, 0.85)])
        ink = (0.05, 0.05, 0.06) if sum(bg) > 1.8 else (0.95, 0.95, 0.95)
        if style == 0:
            img = _brand_dot(rng, f"stk{k}", bg=bg, ink=ink)
            b.plane(s, s, loc=(x, y, 0.0005 * k), rot=(0, 0, rz), mat=f"s{k}", cuts=1)
            specs[f"s{k}"] = PR(img, 0.35, alpha_from_image=True)
        else:
            sc = Canvas(256, 96, (*bg, 1))
            sc.text_fit(_ch(rng, CAR_BRANDS), 0.05, 0.85, 0.9, 0.4, ink, bold=True)
            sc.text_fit(_ch(rng, ["CAR AUDIO", "AMPLIFIED", "COMPETITION SERIES", "SPL CHAMP-ISH", "BASS IS LOUD",
                                  "IF ITS TOO LOUD YOURE TOO OLD"]), 0.05, 0.35, 0.9, 0.2, ink)
            b.plane(s * 1.6, s * 0.6, loc=(x, y, 0.0005 * k), rot=(0, 0, rz), mat=f"s{k}", cuts=1)
            specs[f"s{k}"] = PR(sc.image(f"stk{k}"), 0.35)
    return specs


# == evidence log ===================================================================================

LORE_NAMES = {
    "yapper_boy": "Yapper Boy Tape Recorder", "yak_toy": "Yak Bakk Voice Recorder", "clip_player": "Bit Clipz Player",
    "eye_pod": "Eye-Pod (White)", "mini_pod": "Eye-Pod Mini-ish", "nano_pod": "Eye-Pod Nano-ish",
    "razor_phone": "Razzed V3 Flip Phone", "snake_phone": "No-Kidding Brick Phone", "sidekick_phone": "Sidekicked Swivel Phone",
    "crackberry": "Crackberry", "pda": "Sweaty Palm PDA", "instant_camera": "Polarvoid Instant Camera",
    "instant_photos": "Instant Prints", "fruit_computer": "iSmack Fruit Computer", "cow_box": "Mooteway 2000 Box",
    "beige_tower": "Beige Tower PC", "cdr_spindle": "CD-R Spindle (50 Pack)", "os_box": "Windoze Boxed Software",
    "trial_cd": "AOHell Free Trial Disc", "trial_tin": "AOHell Trial Tin", "modem_56k": "Sportstir 56K Modem",
    "beige_keyboard": "Clicky-Tek 101 Keyboard", "ball_mouse": "Ball Mouse (Ball Escaped)", "phone_cord": "Phone Line Cord",
    "mousepad": "Flying Floppies Mousepad", "im_stickers": "Aimless Messenger Sticker Sheet",
    "p2p_sleeve": "Song-Share CD Sleeve", "skin_printout": "Windamp Skin Printout", "hours_mailer": "1000 Hours Free Mailer",
    "cdr_sharpie": "Sharpie CD-R",
    "rental_vhs": "Blockbusted Rental Clamshell", "new_release_case": "New Release Case", "rental_game": "Game Rental Case",
    "rental_card": "Blockbusted Membership Card", "latefee_receipt": "Late Fee Receipt", "car_rewinder": "Rewind-O-Matic Turbo",
    "popcorn_bag": "Microwave Popcorn Bag", "theater_candy": "Theater-Box Candy", "dvd_case": "Early DVD Keep Case",
    "dropbox_door": "Return Slot Door", "bkr_sticker": "Be Kind Rewind Sticker",
    "speaker_6x9": "6x9 Oval Speaker", "subwoofer": "Subwoofer", "car_amp": "Airbrushed Amplifier",
    "head_unit": "Detachable-Face Head Unit", "faceplate_case": "Faceplate Hard Case", "rca_cables": "Twisted RCA Cables",
    "stiff_cap": "Stiffening Capacitor", "underglow": "Neon Underglow Tube", "bass_knob": "Remote Bass Knob",
    "cd_changer": "Trunk CD Changer", "cassette_adapter": "Cassette Adapter", "tweeter": "Swivel Tweeter",
    "amp_kit": "Amp Wiring Kit", "audio_stickers": "Car Audio Decals",
}

LORE_NOTES = {
    "yapper_boy": ["Slow-mo voice setting used for one purpose.", "Prank-called a hotel. Got a pizza.",
                   "Handle sized for a grown man's grip, given to a nine-year-old.", "Batteries: four C. Lasted one movie."],
    "yak_toy": ["Six seconds of memory.", "All six seconds: a burp.", "Played back in church at full volume.",
                "Confiscated twice, returned once."],
    "clip_player": ["Plays one minute of one song.", "Needs headphones to hear it at all.", "Song chips cost more than the song.",
                    "Clipped to a backpack zipper, lost by recess."],
    "eye_pod": ["Back scratched in the first hour.", "White earbuds worn on the outside of the hoodie, on purpose.",
                "4,000 songs, listened to 11.", "Wheel still clicks when you rub it."],
    "mini_pod": ["Came in pink. Dad got the green.", "Anodized, dented, still the best color.",
                 "Wheel printed in the same color as the shell.", "Held more songs than it ever needed to."],
    "nano_pod": ["Thinner than a pencil.", "Screen scratched by being looked at.", "Lived in a jeans coin pocket. Washed twice.",
                 "Still on the wrong song."],
    "razor_phone": ["Flipped shut to end arguments.", "Keypad glows blue in the dark.", "Antenna bump: the only flaw.",
                    "Ringtone downloaded for $2.99 a week, forever."],
    "snake_phone": ["Snake high score: 2,147. Unverified.", "Survived the stairs, the pool, the dog.",
                    "Battery still at three bars after a week.", "Front cover swapped for a flame one, then back."],
    "sidekick_phone": ["Screen swiveled open in class. Loud.", "Trackball full of pocket lint.",
                       "Texted the whole bus at once.", "Data plan: unlimited, then not."],
    "crackberry": ["Red light blinking at dinner.", "Thumbs never recovered.", "Scroll wheel worn smooth on one side.",
                   "Sent from my crackberry. Every time."],
    "pda": ["Wrote GRAFFITI letters, got wrong letters.", "Stylus lost by Tuesday; used a pen cap.",
            "Calendar entry: Y2K PREP.", "Beamed a contact once. Felt like the future."],
    "instant_camera": ["Shook the picture. Not supposed to.", "Flash fired in a mirror.", "Film cost a dollar a click.",
                       "Every photo came out green for the first minute."],
    "instant_photos": ["Thumb over the lens: 1 of 4.", "Red eyes, red cake, red dog.", "Sharpie caption smudged.",
                       "Dont show mom."],
    "fruit_computer": ["No floppy drive. Panic.", "Puck mouse held sideways for a year.", "Came in a fruit. Matched nothing else.",
                       "Handle used exactly once."],
    "cow_box": ["Box more exciting than the computer.", "Became a fort the same afternoon.", "Spots counted: 31.",
                "Shipped from a farm, according to the kids."],
    "beige_tower": ["Turbo button pressed. Nothing happened.", "Display reads 66. Means megahertz.",
                    "Yellowed on the side that faced the window.", "Hard drive light blinked through every thunderstorm."],
    "cdr_spindle": ["Fifty blanks, forty coasters.", "Lid never screwed back on straight.", "Burned at 52X, played at 0X.",
                    "Gold ones were for the good mixes."],
    "os_box": ["Thirteen floppies. Disk 11 bad.", "Plug and pray.", "Product key written on the box in pen.",
               "System requirements met, barely."],
    "trial_cd": ["Arrived in the mail daily.", "Used as a coaster, then a frisbee, then a mirror.", "1000 hours, 45 minutes to use them.",
                 "Microwaved once for the sparks."],
    "trial_tin": ["Too nice to throw out.", "Too useless to keep.", "Now holds paper clips.", "Lid printed better than the software."],
    "modem_56k": ["Handshake: eee-aww-ksshh.", "Somebody picked up the phone at 98 percent.", "Connected at 28.8. Always.",
                  "Lights blinked like it was thinking."],
    "beige_keyboard": ["Crumbs from three presidencies.", "W, A, S, D worn blank.", "Caps lock on, as usual.",
                       "Coiled cord stretched to the couch."],
    "ball_mouse": ["Ball escaped. Found under the fridge.", "Rollers wearing a gasket of gunk.",
                   "Cleaned with a fingernail, every Sunday.", "Cursor jumped anyway."],
    "phone_cord": ["Twenty-five feet from the kitchen jack.", "Clip snapped off both ends.", "Tripped over by Grandma, twice.",
                   "Unplugged to make a call. Download lost."],
    "mousepad": ["Fabric pilled where the mouse lived.", "Flying floppies, one per corner.", "Coffee ring, upper left.",
                 "Free with purchase, kept forever."],
    "im_stickers": ["Away message: brb, forever.", "Door slam sticker used most.", "Half on a binder, half on a locker.",
                    "Buddy list: 200. Talked to: 3."],
    "p2p_sleeve": ["Downloaded at 3.2 kilobytes a second.", "Song final real.mp3 was not the song.",
                   "Got the dorm internet cut off.", "Mascot sleeping on the job, as designed."],
    "skin_printout": ["Printed in color. Cartridge died halfway.", "Whips the alpaca, as advertised.",
                      "Pinned to the corkboard next to the band poster.", "Equalizer set to smiley face."],
    "hours_mailer": ["Opened by the dog.", "Addressed to current resident.", "Coaster number forty.", "Do not bend. Bent."],
    "cdr_sharpie": ["Labeled HOMEWORK. Was not homework.", "Burned at 4X after three coasters.", "Do not lend. Lent.",
                    "Skips on track 7, every time."],
    "rental_vhs": ["Not rewound.", "Category sticker peeled to the corner.", "Rented Friday, returned Tuesday, charged Wednesday.",
                   "Tracking adjusted, still fuzzy."],
    "new_release_case": ["Guaranteed in stock. Was not.", "Wall of forty cases, zero tapes.", "One-night rental, three-night keep.",
                         "Mustache guy had the last copy."],
    "rental_game": ["Somebody else's save file on the last level.", "Blew on it. It worked.", "No instructions. Never were.",
                    "Returned in the drop box. Against the rules."],
    "rental_card": ["Most valuable ID owned.", "Signed in gel pen.", "Lent to a friend. Friend kept the late fees.",
                    "Member since forever."],
    "latefee_receipt": ["Nine days late on a two-tape movie.", "Fee could have bought the movie.", "Thermal ink fading out of shame.",
                        "Thank you for your contribution."],
    "car_rewinder": ["Two hours in ninety seconds.", "Hood ejected like a crash test.", "Ate one tape. Only one.",
                     "Shaped like a car nobody could afford."],
    "popcorn_bag": ["Pushed the POPCORN button and walked away.", "Butter stain through THIS SIDE UP.", "Half kernels, half charcoal.",
                    "Smoke alarm went off at the good part."],
    "theater_candy": ["Bought at the register, overpriced.", "Rattled through the whole movie.", "Flap torn open with teeth.",
                      "Last piece fused to the box."],
    "dvd_case": ["Widescreen. Black bars. Dad complained.", "Rental sticker over the actors' faces.", "Disc scratched by the hub.",
                 "Special edition, regular movie."],
    "dropbox_door": ["Tapes shoved through at 11:58 PM.", "No games in the drop box. Games in the drop box.",
                     "Flap swung in, never fully out.", "Pried off when the store closed for good."],
    "bkr_sticker": ["Be kind. Rewind.", "Arrow pointed the way nobody turned it.", "Stuck on harder than the label.",
                    "The only rule anyone remembers."],
    "speaker_6x9": ["Rear deck, cooked by the sun.", "Promised 500 watts. Car had 40.", "Mica cone, glitter forever.",
                    "Rattled the back window loose."],
    "subwoofer": ["License plate rattled off on track 2.", "Surround pinchable, pinched.", "Magnet heavier than the spare tire.",
                  "Cone hopped a quarter inch per kick."],
    "car_amp": ["Airbrushed at the swap meet.", "Protect light: on.", "Alternator crying since 1998.",
                "Fins hot enough to fry an egg, tested."],
    "head_unit": ["Faceplate in the pocket, deck in the dash.", "Display: BASS BOOST, always.", "Volume knob size of a cookie.",
                  "Remembered the radio presets, forgot everything else."],
    "faceplate_case": ["Window smashed anyway.", "Case lost, face kept in the cup holder.", "Snaps shut louder than the stereo.",
                       "Logo worn off the lid."],
    "rca_cables": ["Gold plated. Heard the difference. Didn't.", "Red is right. Allegedly.", "Run next to the power wire. Whine.",
                   "Twisted pair, untwisted by Monday."],
    "stiff_cap": ["Readout dipped every bass hit. That was the point.", "One farad, one prayer.",
                  "Charged through a test light, once correctly.", "Glowed blue in the trunk for no one."],
    "underglow": ["Made a hatchback hover.", "Pulled over for it. Twice.", "Switch on the dash labeled NOS.",
                  "Cracked on the first speed bump."],
    "bass_knob": ["Turned to the right. Always.", "Screwed under the dash by the knee.", "Red light means trouble.",
                  "The knob was the whole personality."],
    "cd_changer": ["Loaded once in 1998.", "Disc 6 stuck since then.", "Bolted to the trunk floor, crooked.",
                   "Shock proof-ish, as advertised."],
    "cassette_adapter": ["Clicked forever.", "Cord tangled in the shifter.", "Tape deck ate it, spat it out, kept the cord.",
                         "Portable CD player sliding around the passenger seat."],
    "tweeter": ["Aimed at the driver's own ear.", "Glued to the dash, fell into the vent.", "Sizzled on the high hat.",
                "Silk dome poked once by a curious finger."],
    "amp_kit": ["Eight gauge, sold as four.", "Fuse blown before the first song.", "Ring terminal crimped with pliers.",
                "Ground screwed to the seat bolt. Bad idea."],
    "audio_stickers": ["Windshield banner bigger than the windshield.", "Brand stickers worth more than the gear.",
                       "If it's too loud you're too old.", "Applied crooked, never fixed."],
}
