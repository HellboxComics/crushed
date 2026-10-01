"""Procedural raster textures (labels, screens, prints) drawn with numpy.

No PIL, no fonts on disk: this runs inside stock Blender. Text uses a tiny
built-in 5x7 bitmap font, which is exactly the right look for LCDs, stamped
steel and cheap labels anyway.
"""
import math

import numpy as np
import bpy

_FONT = {
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11111 00010 00100 00010 00001 10001 01110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11100 10010 10001 10001 10001 10010 11100",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 10001 01010 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    " ": "00000 00000 00000 00000 00000 00000 00000", "-": "00000 00000 00000 11111 00000 00000 00000",
    ".": "00000 00000 00000 00000 00000 01100 01100", "#": "01010 01010 11111 01010 11111 01010 01010",
    "!": "00100 00100 00100 00100 00100 00000 00100", "/": "00001 00010 00010 00100 01000 01000 10000",
    ":": "00000 01100 01100 00000 01100 01100 00000", "$": "00100 01111 10100 01110 00101 11110 00100",
    "%": "11001 11010 00010 00100 01000 01011 10011", "+": "00000 00100 00100 11111 00100 00100 00000",
    "'": "00100 00100 01000 00000 00000 00000 00000", "?": "01110 10001 00001 00010 00100 00000 00100",
    "(": "00010 00100 01000 01000 01000 00100 00010", ")": "01000 00100 00010 00010 00010 00100 01000",
    ",": "00000 00000 00000 00000 01100 00100 01000", "&": "01100 10010 10100 01000 10101 10010 01101",
    "*": "00000 10101 01110 11111 01110 10101 00000", "=": "00000 00000 11111 00000 11111 00000 00000",
}


class Canvas:
    def __init__(self, w, h, bg=(1, 1, 1, 1)):
        self.w, self.h = w, h
        self.a = np.empty((h, w, 4), dtype=np.float32)
        self.a[:] = bg
        yy, xx = np.mgrid[0:h, 0:w]
        self.x = (xx + 0.5) / w
        self.y = 1.0 - (yy + 0.5) / h

    def _blend(self, mask, col):
        col = np.array(col if len(col) == 4 else (*col, 1.0), dtype=np.float32)
        m = (np.clip(mask, 0, 1) * col[3])[..., None]
        self.a[..., :3] = self.a[..., :3] * (1 - m) + col[:3] * m

    def rect(self, x0, y0, x1, y1, col, soft=0.0):
        d = np.maximum(np.maximum(x0 - self.x, self.x - x1), np.maximum(y0 - self.y, self.y - y1))
        self._blend(np.clip(0.5 - d / max(soft, 1.0 / self.w), 0, 1), col)

    def circle(self, cx, cy, r, col, soft=None, ring=None):
        asp = self.w / self.h
        d = np.hypot((self.x - cx) * asp, self.y - cy) - r
        if ring:
            d = np.abs(d + ring / 2) - ring / 2
        s = soft or 1.5 / self.h
        self._blend(np.clip(0.5 - d / s, 0, 1), col)

    def line(self, pts, width, col):
        asp = self.w / self.h
        mask = np.zeros((self.h, self.w), dtype=np.float32)
        for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
            px, py = (self.x - ax) * asp, self.y - ay
            vx, vy = (bx - ax) * asp, by - ay
            L = vx * vx + vy * vy + 1e-12
            t = np.clip((px * vx + py * vy) / L, 0, 1)
            d = np.hypot(px - t * vx, py - t * vy)
            mask = np.maximum(mask, np.clip((width / 2 - d) * self.h / 1.2 + 0.5, 0, 1))
        self._blend(mask, col)

    def text(self, s, x, y, size, col, spacing=1.2, bold=False):
        """Draw text with top-left at (x, y); size = glyph height (0..1 of canvas)."""
        px = size / 7.0
        pxw = px * self.h / self.w
        cx = x
        mask = np.zeros((self.h, self.w), dtype=np.float32)
        for ch in s.upper():
            g = _FONT.get(ch, _FONT["?"]).split()
            for r, row in enumerate(g):
                for c, bit in enumerate(row):
                    if bit == "1":
                        x0 = cx + c * pxw
                        y1 = y - r * px
                        grow = 0.25 * pxw if bold else 0
                        m = ((self.x >= x0 - grow) & (self.x <= x0 + pxw * 1.02 + grow)
                             & (self.y <= y1) & (self.y >= y1 - px * 1.02))
                        mask[m] = 1.0
            cx += 6 * pxw * spacing
        self._blend(mask, col)
        return cx

    def text_fit(self, s, x, y, maxw, size, col, spacing=1.0, bold=False):
        """Text that shrinks until it fits in maxw (canvas-width fraction) instead of running off the edge."""
        asp = self.h / self.w
        need = len(s) * 6 * (size / 7.0) * asp * spacing
        if need > maxw:
            size *= maxw / need
        return self.text(s, x, y, size, col, spacing=spacing, bold=bold)

    def poly(self, pts, col, acc=None):
        """Fill a polygon (even-odd). Points are (x, y) in 0..1 canvas space, y up. `acc` collects the mask."""
        mask = np.zeros((self.h, self.w), dtype=bool)
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            if y0 == y1:
                continue
            crosses = ((y0 <= self.y) & (self.y < y1)) | ((y1 <= self.y) & (self.y < y0))
            xint = x0 + (self.y - y0) * (x1 - x0) / (y1 - y0)
            mask ^= crosses & (self.x < xint)
        self._blend(mask.astype(np.float32), col)
        if acc is not None:
            acc |= mask

    def gradient(self, top, bottom):
        t = self.y[..., None]
        self.a[..., :3] = np.array(top, dtype=np.float32) * t + np.array(bottom, dtype=np.float32) * (1 - t)

    def scribble(self, rng, x0, y0, x1, width, col, amp=0.02):
        n = 40
        xs = np.linspace(x0, x1, n)
        ph = rng.uniform(0, 6)
        ys = y0 + amp * np.sin(xs * rng.uniform(60, 120) + ph) * rng.uniform(0.5, 1) \
            + amp * 0.5 * np.sin(xs * rng.uniform(150, 260))
        self.line(list(zip(xs, ys)), width, col)

    def noise(self, rng, amt=0.04):
        n = rng.normal(0, amt, (self.h, self.w, 1)).astype(np.float32)
        self.a[..., :3] = np.clip(self.a[..., :3] + n, 0, 1)

    def image(self, name):
        img = bpy.data.images.new(name, self.w, self.h, alpha=True)
        img.pixels.foreach_set(np.flipud(self.a).ravel())
        img.pack()
        return img


def srgb(c):
    """Linear-ish colors in this module are specified in display space."""
    return tuple(c)


# -- specific prints -----------------------------------------------------------

def cassette_label(rng, base, name):
    c = Canvas(256, 160, (*base, 1))
    stripe = rng.choice([(0.9, 0.2, 0.1), (0.1, 0.3, 0.8), (0.95, 0.7, 0.1), (0.1, 0.1, 0.1)])
    c.rect(0, 0.78, 1, 0.9, stripe)
    c.rect(0, 0.08, 1, 0.14, stripe)
    for i in range(3):
        c.rect(0.05, 0.68 - i * 0.07, 0.95, 0.685 - i * 0.07, (0.4, 0.4, 0.45))
    ink = rng.choice([(0.05, 0.05, 0.3), (0.1, 0.1, 0.1), (0.6, 0.05, 0.05)])
    c.scribble(rng, 0.08, 0.7, rng.uniform(0.5, 0.9), 0.012, ink)
    c.text(rng.choice(["A", "B"]), 0.05, 0.97, 0.12, (0.1, 0.1, 0.1), bold=True)
    c.text(rng.choice(["C-60", "C-90", "C-46", "HIGH BIAS", "NORMAL", "TYPE II"]), 0.62, 0.97, 0.07, (0.1, 0.1, 0.1))
    c.rect(0.18, 0.2, 0.82, 0.48, (0.15, 0.12, 0.1))
    for cx in (0.33, 0.67):
        c.circle(cx, 0.34, 0.09, (0.95, 0.95, 0.95))
        c.circle(cx, 0.34, 0.05, (0.2, 0.2, 0.2))
    c.noise(rng, 0.02)
    return c.image(name)


def sticker(rng, name, base=(0.95, 0.94, 0.9), lines=4, words=None):
    c = Canvas(256, 128, (*base, 1))
    for i in range(lines):
        c.rect(0.04, 0.8 - i * 0.18, 0.96, 0.81 - i * 0.18, (0.55, 0.6, 0.85))
    ink = rng.choice([(0.05, 0.05, 0.25), (0.1, 0.1, 0.1), (0.7, 0.05, 0.05)])
    if words:
        c.text(words, 0.06, 0.78, 0.2, ink, bold=True)
    for i in range(rng.integers(1, 3)):
        c.scribble(rng, 0.06, 0.55 - i * 0.18, rng.uniform(0.4, 0.9), 0.025, ink, 0.03)
    c.noise(rng, 0.02)
    return c.image(name)


def keypad(rng, name, rows=4, cols=3, key=(0.85, 0.85, 0.82), body=(0.2, 0.2, 0.2), ink=(0.1, 0.1, 0.1),
           labels="123456789*0#"):
    c = Canvas(192, 256, (*body, 1))
    k = 0
    for r in range(rows):
        for q in range(cols):
            x0 = 0.08 + q * (0.84 / cols)
            y1 = 0.94 - r * (0.9 / rows)
            c.rect(x0 + 0.02, y1 - 0.9 / rows + 0.03, x0 + 0.84 / cols - 0.02, y1, key, soft=0.02)
            if k < len(labels):
                c.text(labels[k], x0 + 0.84 / cols * 0.35, y1 - 0.9 / rows * 0.25, 0.07, ink, bold=True)
            k += 1
    c.noise(rng, 0.015)
    return c.image(name)


SCREENS_ON = {"on": False}   # SCREEN TIME: every screen you ever stared at, still on


def lcd(rng, name, text=None, bg=(0.55, 0.62, 0.45), ink=(0.08, 0.1, 0.06), w=256, h=96):
    c = Canvas(w, h, (*bg, 1))
    t = text or rng.choice(["911", "143", "07734", "8008", "1337", "420", "555-0199", "HELLO", "88:88",
                            "12:00", "LOW BATT", "ERROR", "GM", "NO SIGNAL", "0.00"])
    c.text_fit(t, 0.08, 0.8, 0.84, 0.55, ink, spacing=1.2, bold=True)
    c.noise(rng, 0.02)
    img = c.image(name)
    img["lcd"] = True
    return img


def notebook(rng, name, paper=(0.96, 0.95, 0.9)):
    c = Canvas(256, 320, (*paper, 1))
    for i in range(22):
        y = 0.9 - i * 0.04
        c.rect(0, y, 1, y + 0.003, (0.55, 0.7, 0.9))
    c.rect(0.14, 0, 0.145, 1, (0.9, 0.4, 0.4))
    ink = rng.choice([(0.1, 0.1, 0.5), (0.1, 0.1, 0.1)])
    for i in range(rng.integers(3, 9)):
        c.scribble(rng, 0.17, 0.88 - i * 0.08, rng.uniform(0.4, 0.95), 0.008, ink, 0.008)
    if rng.random() < 0.6:
        c.circle(rng.uniform(0.4, 0.8), rng.uniform(0.2, 0.5), 0.08, (0.8, 0.1, 0.1), ring=0.015)
    c.noise(rng, 0.02)
    return c.image(name)


def chart(rng, name):
    """A printed price chart that pumped and then very much did not."""
    c = Canvas(320, 240, (0.97, 0.97, 0.95, 1))
    for i in range(8):
        c.rect(0.05 + i * 0.12, 0.05, 0.052 + i * 0.12, 0.95, (0.85, 0.85, 0.85))
        c.rect(0.05, 0.1 + i * 0.11, 0.95, 0.102 + i * 0.11, (0.85, 0.85, 0.85))
    n = 26
    xs = np.linspace(0.08, 0.92, n)
    up = int(n * rng.uniform(0.55, 0.75))
    v = [0.2]
    for i in range(1, n):
        drift = 0.035 if i < up else -0.09
        v.append(float(np.clip(v[-1] + drift + rng.normal(0, 0.03), 0.06, 0.92)))
    for i in range(1, n):
        o, cl = v[i - 1], v[i]
        col = (0.1, 0.7, 0.3) if cl >= o else (0.85, 0.1, 0.1)
        x = xs[i]
        c.line([(x, min(o, cl) - 0.03), (x, max(o, cl) + 0.03)], 0.004, col)
        c.rect(x - 0.012, min(o, cl), x + 0.012, max(o, cl) + 0.004, col)
    c.text(rng.choice(["-94%", "-99%", "-87%", "REKT", "WAGMI?"]), 0.62, 0.95, 0.09, (0.85, 0.1, 0.1), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def pcb(rng, name):
    c = Canvas(256, 256, (0.05, 0.3, 0.12, 1))
    gold = (0.8, 0.65, 0.3)
    for _ in range(40):
        x, y = rng.uniform(0, 1, 2)
        pts = [(x, y)]
        for _ in range(rng.integers(2, 5)):
            if rng.random() < 0.5:
                x += rng.uniform(-0.3, 0.3)
            else:
                y += rng.uniform(-0.3, 0.3)
            pts.append((x, y))
        c.line(pts, 0.008, (0.1, 0.45, 0.18))
        c.circle(*pts[-1], 0.01, gold)
    for _ in range(5):
        x, y = rng.uniform(0.1, 0.8, 2)
        c.rect(x, y, x + rng.uniform(0.08, 0.2), y + rng.uniform(0.05, 0.12), (0.06, 0.06, 0.06))
    c.noise(rng, 0.02)
    return c.image(name)


def can_print(rng, name):
    base = rng.choice([(0.05, 0.05, 0.05), (0.1, 0.1, 0.3), (0.9, 0.9, 0.9), (0.2, 0.02, 0.05)])
    hi = rng.choice([(0.3, 1.0, 0.1), (1.0, 0.45, 0.0), (0.1, 0.8, 1.0), (1.0, 0.1, 0.4), (1.0, 0.9, 0.1)])
    c = Canvas(512, 256, (*base, 1))
    for k in range(3):
        xs = np.linspace(0, 1, 30)
        ys = 0.5 + 0.25 * np.sign(np.sin(xs * (18 + k * 7) + k)) * rng.uniform(0.3, 1, 30) + (k - 1) * 0.12
        c.line(list(zip(xs, ys)), 0.03, hi)
    c.text(rng.choice(["MEGA", "XTREME", "JOLT", "VOLTAGE", "HYPER", "RUSH"]), 0.25, 0.62, 0.25, (1, 1, 1),
           bold=True, spacing=1.1)
    c.text("ENERGY", 0.3, 0.3, 0.1, hi)
    return c.image(name)


def ramen(rng, name):
    base = rng.choice([(0.85, 0.1, 0.05), (0.95, 0.5, 0.05), (0.9, 0.75, 0.1)])
    c = Canvas(320, 256, (*base, 1))
    c.circle(0.5, 0.42, 0.3, (0.95, 0.95, 0.92))
    c.circle(0.5, 0.42, 0.24, (0.95, 0.8, 0.45))
    for i in range(6):
        xs = np.linspace(0.32, 0.68, 30)
        c.line(list(zip(xs, 0.3 + i * 0.04 + 0.015 * np.sin(xs * 60 + i))), 0.01, (0.98, 0.9, 0.6))
    c.text("NOODLE SOUP", 0.12, 0.95, 0.1, (1, 1, 0.9), bold=True)
    c.text(rng.choice(["BEEF", "CHICKEN", "SHRIMP", "SPICY"]), 0.35, 0.1, 0.08, (1, 1, 1))
    return c.image(name)


def screen(rng, name, kind=None):
    kind = kind or rng.choice(["off", "blue", "term", "off", "static"])
    if SCREENS_ON["on"] and kind == "off":
        kind = rng.choice(["blue", "term", "static"])
    if kind == "blue":
        c = Canvas(256, 192, (0.05, 0.1, 0.55, 1))
        c.rect(0.35, 0.8, 0.65, 0.88, (0.7, 0.7, 0.7))
        for i in range(6):
            c.rect(0.08, 0.7 - i * 0.08, rng.uniform(0.4, 0.92), 0.72 - i * 0.08, (0.9, 0.9, 0.95))
    elif kind == "term":
        c = Canvas(256, 192, (0.01, 0.03, 0.01, 1))
        for i in range(9):
            c.text("".join(rng.choice(list("ABCDEF0123456789 ")) for _ in range(12)), 0.05, 0.95 - i * 0.1,
                   0.06, (0.2, 0.9, 0.3))
    elif kind == "game":
        c = Canvas(128, 96, (0.08, 0.02, 0.14, 1))
        for i in range(5):
            c.rect(0.05 + i * 0.19, 0.1, 0.17 + i * 0.19, 0.1 + float(rng.uniform(0.1, 0.5)), (0.55, 1.0, 0.1))
        c.rect(0.45, 0.62, 0.55, 0.72, (1.0, 0.95, 0.2))
        c.text("1UP", 0.05, 0.95, 0.12, (1, 1, 1), bold=True)
        c.text(str(int(rng.integers(100, 99999))), 0.5, 0.95, 0.12, (1, 1, 1), bold=True)
    elif kind == "static":
        c = Canvas(128, 96, (0.2, 0.2, 0.2, 1))
        c.noise(rng, 0.35)
        return c.image(name)
    else:
        c = Canvas(64, 48, (0.03, 0.035, 0.035, 1))
    for i in range(0, c.h, 3):
        c.a[i, :, :3] *= 0.8
    return c.image(name)


def griptape_art(rng, name):
    c = Canvas(128, 512, (*rng.choice([(0.9, 0.9, 0.85), (0.1, 0.1, 0.1), (0.95, 0.35, 0.05)]), 1))
    style = rng.integers(0, 3)
    if style == 0:
        for i in range(10):
            for j in range(40):
                if (i + j) % 2 == 0:
                    c.rect(i / 10, j / 40, (i + 1) / 10, (j + 1) / 40, (0.05, 0.05, 0.05))
    elif style == 1:
        for k in range(5):
            xs = np.linspace(0, 1, 20)
            c.line(list(zip(xs, 0.1 + k * 0.08 + 0.08 * np.abs(np.sin(xs * 9 + k)))), 0.06,
                   (1.0, 0.3 + k * 0.12, 0.05))
    else:
        c.circle(0.5, 0.5, 0.3, (0.8, 0.1, 0.6))
        c.circle(0.5, 0.5, 0.2, (0.1, 0.8, 0.8))
    c.noise(rng, 0.03)
    return c.image(name)


def stamp(rng, name, text):
    c = Canvas(256, 64, (0.5, 0.5, 0.5, 1))
    c.text(text, 0.08, 0.85, 0.7, (0.0, 0.0, 0.0), bold=True, spacing=1.15)
    return c.image(name)


def battery(rng, name):
    a, b = [(0.1, 0.1, 0.1), (0.8, 0.1, 0.1)], [(0.1, 0.35, 0.8), (0.9, 0.9, 0.9)]
    a2 = [(0.1, 0.5, 0.2), (0.85, 0.85, 0.8)]
    top, bot = [a, b, a2][rng.integers(0, 3)]
    c = Canvas(256, 128, (*bot, 1))
    c.rect(0, 0.6, 1, 1, top)
    c.text("AA 1.5V", 0.1, 0.45, 0.2, (0.95, 0.95, 0.95) if bot[0] < 0.5 else (0.1, 0.1, 0.1), bold=True)
    c.text("ALKALINE", 0.55, 0.9, 0.12, (0.9, 0.9, 0.9))
    return c.image(name)


def cd_marker(rng, name):
    c = Canvas(256, 256, (0, 0, 0, 0))
    c.a[..., 3] = 0.0
    ink = rng.choice([(0.05, 0.05, 0.05), (0.1, 0.1, 0.5), (0.6, 0.0, 0.0)])
    t = rng.choice(["MIX 97", "JAMZ", "ROAD TRIP", "DONT TOUCH", "SUMMER 99", "BURN 3", "BACKUP", "MP3S"])
    c.text(t, 0.2, 0.75, 0.1, ink, bold=True)
    c.scribble(rng, 0.25, 0.3, 0.75, 0.01, ink, 0.02)
    # alpha channel from ink darkness
    c.a[..., 3] = (c.a[..., :3].sum(axis=2) > 0.01).astype(np.float32)
    return c.image(name)


# -- the 2009-2026 era, the degen shelf, and the one-of-one props --------------------------

def _smooth(pts, n=6):
    """Catmull-Rom through the points, so contours curve instead of zigzag."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(tuple(pts[-1]))
    return out


SKIN = [(0.98, 0.83, 0.72), (0.93, 0.72, 0.56), (0.8, 0.56, 0.4), (0.6, 0.4, 0.28), (0.4, 0.25, 0.18)]
HAIR = [(0.96, 0.82, 0.32), (0.4, 0.2, 0.1), (0.78, 0.22, 0.08), (0.06, 0.05, 0.07), (0.95, 0.4, 0.7), (0.2, 0.75, 0.8)]
SUIT = [(0.06, 0.06, 0.08), (0.9, 0.12, 0.35), (0.95, 0.95, 0.95), (0.15, 0.35, 0.9), (0.85, 0.1, 0.1), (0.55, 0.2, 0.85)]

# arm poses: (shoulder -> elbow -> hand) for the left and right arm, in figure units
_POSES = [
    (((-0.105, 0.835), (-0.17, 0.71), (-0.112, 0.59)), ((0.105, 0.835), (0.175, 0.925), (0.05, 0.985))),
    (((-0.105, 0.835), (-0.19, 0.93), (-0.045, 0.985)), ((0.105, 0.835), (0.19, 0.93), (0.045, 0.985))),
    (((-0.105, 0.835), (-0.16, 0.71), (-0.125, 0.57)), ((0.105, 0.835), (0.17, 0.7), (0.125, 0.545))),
    (((-0.105, 0.835), (-0.2, 0.78), (-0.27, 0.86)), ((0.105, 0.835), (0.17, 0.705), (0.112, 0.59))),
]


def figure(c, cx, y0, h, rng, outfit="bare", pose=None, flip=None):
    """A pin-up drawn in flat shapes: hair, face, shoulders, waist, hips, legs, heels. Stylized, never anatomical.
    outfit: bare | bikini | swim | bunny (ears, collar, bowtie, cuffs). cx is the center line, y0 the feet,
    h the full height including ears."""
    skin = SKIN[int(rng.integers(0, len(SKIN)))]
    hair = HAIR[int(rng.integers(0, len(HAIR)))]
    suit = SUIT[int(rng.integers(0, len(SUIT)))]
    trim = (0.98, 0.98, 0.98) if suit != (0.95, 0.95, 0.95) else (0.1, 0.1, 0.12)
    fl = -1.0 if (rng.random() < 0.5 if flip is None else flip) else 1.0
    pose = int(rng.integers(0, len(_POSES))) if pose is None else pose
    s = h / (1.17 if outfit == "bunny" else 1.0)
    asp = c.h / c.w
    shade = tuple(x * 0.62 for x in skin)
    acc = np.zeros((c.h, c.w), dtype=bool)

    def o(v):      # the lean: shoulders one way, hips the other
        return -0.05 * (v - 0.55)

    def pt(u, v):
        return (cx + fl * (u + o(v)) * s * asp, y0 + v * s)

    def fill(pts, col, smooth=True, skin_part=False):
        q = _smooth(pts) if smooth else pts
        c.poly([pt(*p) for p in q], col, acc if skin_part else None)

    def limb(a, b, w, col, skin_part=True):
        c.line([pt(*a), pt(*b)], w * s, col)
        if skin_part:
            m = np.zeros((c.h, c.w), dtype=np.float32)
            asp2 = c.w / c.h
            (ax, ay), (bx, by) = pt(*a), pt(*b)
            px, py = (c.x - ax) * asp2, c.y - ay
            vx, vy = (bx - ax) * asp2, by - ay
            t = np.clip((px * vx + py * vy) / (vx * vx + vy * vy + 1e-12), 0, 1)
            acc.__ior__(np.hypot(px - t * vx, py - t * vy) < w * s / 2)

    def mirror(pts):
        return [(-u, v) for u, v in pts]

    # hair first: a long fall behind the shoulders, then everything else in front of it
    c.circle(*pt(0, 0.94), 0.07 * s, hair)
    fill([(-0.072, 0.95), (-0.092, 0.9), (-0.1, 0.835), (-0.088, 0.775), (-0.04, 0.765), (0.04, 0.77), (0.08, 0.83),
          (0.075, 0.9), (0.068, 0.95)], hair)

    # torso and legs
    left = [(-0.028, 0.895), (-0.06, 0.862), (-0.108, 0.845), (-0.1, 0.805), (-0.095, 0.77), (-0.074, 0.725),
            (-0.059, 0.668), (-0.086, 0.62), (-0.108, 0.575), (-0.108, 0.53)]
    fill(left + mirror(left)[::-1], skin, skin_part=True)
    leg = [(-0.108, 0.56), (-0.104, 0.45), (-0.086, 0.345), (-0.064, 0.275), (-0.067, 0.2), (-0.056, 0.11),
           (-0.041, 0.048), (-0.031, 0.045), (-0.028, 0.11), (-0.036, 0.2), (-0.03, 0.275), (-0.02, 0.36),
           (-0.005, 0.5), (0.0, 0.545)]
    for side in (1, -1):
        fill([(side * u, v) for u, v in leg], skin, smooth=True, skin_part=True)
    (l0, l1, l2), (r0, r1, r2) = _POSES[pose]
    for a, b, d in (((l0, l1, l2)), ((r0, r1, r2))):
        limb(a, b, 0.04, skin)
        limb(b, d, 0.031, skin)
    fill([(-0.022, 0.83), (0.022, 0.83), (0.02, 0.905), (-0.02, 0.905)], skin, smooth=False, skin_part=True)

    # a little volume: the far side of everything falls into shade
    ys, xs = np.nonzero(acc)
    if len(xs):
        rel = (c.x - cx) * fl / (0.13 * s * asp)
        c._blend(acc * np.clip(rel * 0.55 + 0.2, 0, 1), (*shade, 0.55))

    # the stockings, if this is the bunny
    if outfit == "bunny":
        for side in (1, -1):
            fill([(side * u, v) for u, v in leg], (0.1, 0.07, 0.09, 0.62))

    # outfits
    if outfit == "bikini":
        for side in (1, -1):
            fill([(side * -0.088, 0.796), (side * -0.014, 0.786), (side * -0.03, 0.738), (side * -0.084, 0.748)], suit)
        fill([(-0.104, 0.598), (0.104, 0.598), (0.022, 0.535), (-0.022, 0.535)], suit, smooth=False)
        c.line([pt(-0.05, 0.795), pt(-0.02, 0.87), pt(0.0, 0.88), pt(0.02, 0.87), pt(0.05, 0.795)], 0.006 * s, suit)
    elif outfit in ("swim", "bunny"):
        top = 0.805 if outfit == "swim" else 0.795
        body = [(-0.09, top), (-0.094, 0.77), (-0.074, 0.725), (-0.059, 0.668), (-0.086, 0.62), (-0.108, 0.575),
                (-0.012, 0.528)]
        fill(body + mirror(body)[::-1], suit)
        if outfit == "swim":
            for side in (1, -1):
                c.line([pt(side * 0.06, 0.805), pt(side * 0.03, 0.868)], 0.012 * s, suit)
        else:
            c.line([pt(-0.07, 0.69), pt(-0.05, 0.775)], 0.006 * s, (1, 1, 1, 0.35))      # satin glint
            c.rect(*pt(-0.026, 0.855), *pt(0.026, 0.878), trim)                          # collar
            for side in (1, -1):                                                        # bowtie
                fill([(0.0, 0.862), (side * 0.045, 0.89), (side * 0.045, 0.835)], (0.92, 0.1, 0.25), smooth=False)
            c.circle(*pt(0, 0.862), 0.011 * s, (0.92, 0.1, 0.25))
            for d in (l2, r2):                                                          # cuffs
                c.circle(*pt(*d), 0.017 * s, trim)
            for side, tilt in ((-1, 0.0), (1, 0.55)):                                    # ears
                pts_e = [(side * 0.03 + 0.024 * math.cos(t) * math.cos(tilt * side) - 0.092 * math.sin(t) * math.sin(tilt * side),
                          1.075 + 0.024 * math.cos(t) * math.sin(tilt * side) + 0.092 * math.sin(t) * math.cos(tilt * side))
                         for t in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
                fill(pts_e, suit if suit != (0.95, 0.95, 0.95) else (0.85, 0.85, 0.88), smooth=False)
                fill([(u * 0.55 + side * 0.03 * 0.45 + 0.0, (v - 1.075) * 0.8 + 1.075)
                      for u, v in pts_e], (0.98, 0.6, 0.7), smooth=False)
    if outfit != "bare":
        for side in (1, -1):
            c.rect(*pt(side * 0.036 - 0.012, 0.0), *pt(side * 0.036 - 0.004, 0.03), (0.9, 0.1, 0.15))
    for side in (1, -1):     # heels
        fill([(side * 0.037, 0.05), (side * 0.09, 0.02), (side * 0.096, 0.008), (side * 0.03, 0.008)],
             (0.9, 0.08, 0.15), smooth=False)

    # head: hair frames the face; lips and a beauty mark
    c.circle(*pt(0.003, 0.925), 0.054 * s, skin)
    c.circle(*pt(0.012, 0.913), 0.0065 * s, (0.85, 0.08, 0.15))
    for ex in (-0.02, 0.022):
        c.line([pt(ex - 0.008, 0.934), pt(ex + 0.008, 0.936)], 0.004 * s, (0.1, 0.06, 0.06))
    fill([(-0.066, 0.935), (-0.05, 0.985), (0.0, 1.0), (0.05, 0.985), (0.062, 0.94), (0.02, 0.968), (-0.03, 0.972)], hair)


def app_grid(rng, name):
    c = Canvas(160, 344)
    a = rng.choice([(0.1, 0.2, 0.6), (0.6, 0.15, 0.5), (0.05, 0.4, 0.45), (0.25, 0.1, 0.5)])
    b = rng.choice([(0.95, 0.5, 0.2), (0.95, 0.3, 0.45), (0.3, 0.8, 0.9), (0.9, 0.85, 0.3)])
    c.gradient(a, b)
    cols = [(0.95, 0.2, 0.2), (0.2, 0.6, 0.95), (0.25, 0.85, 0.4), (0.95, 0.8, 0.15), (0.6, 0.3, 0.9),
            (0.95, 0.95, 0.95), (0.1, 0.1, 0.1), (0.95, 0.5, 0.1)]
    for r in range(5):
        for q in range(4):
            x = 0.09 + q * 0.225
            y = 0.9 - r * 0.135
            c.rect(x, y - 0.1, x + 0.17, y, cols[int(rng.integers(0, len(cols)))], soft=0.03)
    c.rect(0.05, 0.03, 0.95, 0.15, (1, 1, 1, 0.35), soft=0.05)
    for q in range(4):
        c.rect(0.09 + q * 0.225, 0.045, 0.26 + q * 0.225, 0.135, cols[int(rng.integers(0, len(cols)))], soft=0.03)
    c.text("1%", 0.78, 0.985, 0.03, (1, 1, 1), bold=True)
    c.noise(rng, 0.01)
    return c.image(name)


def lockscreen(rng, name):
    c = Canvas(160, 344)
    c.gradient(rng.choice([(0.05, 0.05, 0.2), (0.3, 0.05, 0.25), (0.02, 0.15, 0.2)]),
               rng.choice([(0.9, 0.3, 0.4), (0.2, 0.5, 0.9), (0.95, 0.6, 0.2)]))
    c.text(str(rng.choice(["3:07", "4:20", "2:47", "5:55", "1:11"])), 0.14, 0.86, 0.1, (1, 1, 1), bold=True)
    for i in range(4):
        c.rect(0.06, 0.6 - i * 0.12, 0.94, 0.68 - i * 0.12, (1, 1, 1, 0.3), soft=0.03)
    c.text(str(rng.choice(["1% BATTERY", "NO SERVICE", "24 UNREAD", "SCREEN TIME"])), 0.1, 0.06, 0.04, (1, 1, 1))
    c.noise(rng, 0.01)
    return c.image(name)


def vape_print(rng, name):
    c = Canvas(256, 96)
    a = rng.choice([(1.0, 0.3, 0.5), (0.2, 0.9, 0.8), (0.6, 0.3, 1.0), (1.0, 0.7, 0.1), (0.3, 0.6, 1.0)])
    b = rng.choice([(1.0, 0.9, 0.2), (0.9, 0.2, 0.8), (0.2, 1.0, 0.6), (1.0, 0.4, 0.2)])
    c.gradient(a, b)
    c.text(str(rng.choice(["MANGO ICE", "BLUE RAZZ", "WATERMELON", "GRAPE ICE", "PEACH"])), 0.08, 0.85, 0.21,
           (1, 1, 1), bold=True)
    c.text("5000 PUFFS", 0.08, 0.42, 0.22, (0.05, 0.05, 0.05), bold=True)
    c.text("0% NICOTINE LOL", 0.08, 0.18, 0.13, (1, 1, 1))
    return c.image(name)


# parody mastheads: in the ballpark of the real newsstand, never the real name
MASTHEADS = ["PLAYPEN", "PLAYBOI", "PLAYBUOY", "PENTHOUSE", "PLAYDOH", "HUSTLE", "PLAYBOY'S NEPHEW", "PLAYBAE",
             "NIGHTCAP", "HIGH ROLLER", "BACHELOR", "AFTER HOURS"]
MASTHEADS = [m for m in MASTHEADS if m not in ("PENTHOUSE",)]       # real titles stay out; the riffs stay in
COVER_LINES = ["THE ARTICLES ISSUE", "CENTERFOLD INSIDE!", "FICTION!!", "WHY YOU'RE BROKE", "BEST BAR TABS",
               "GIRLS OF THE GROUP CHAT", "BUY THE TOP", "HOT TUBS RANKED", "INTERVIEW: A LIAR", "WALLET TIPS",
               "DIVORCE LAWYERS", "BEER: A HISTORY", "MY BUDDY'S BOAT", "PLUS: CIGARS"]
BACKGROUNDS = [((0.1, 0.28, 0.6), (0.02, 0.07, 0.25)), ((0.8, 0.1, 0.15), (0.25, 0.02, 0.08)),
               ((0.05, 0.5, 0.55), (0.02, 0.15, 0.3)), ((0.35, 0.08, 0.55), (0.08, 0.02, 0.2)),
               ((0.96, 0.78, 0.15), (0.85, 0.35, 0.1)), ((0.08, 0.08, 0.1), (0.3, 0.05, 0.12))]


def bunny_head(c, cx, cy, r, col):
    """Our rabbit: a round head, two tall ears leaning apart, one eye, a bow tie. Nobody's logo; everybody's bunny."""
    asp = c.w / c.h
    for sx, lean in ((-1, 0.35), (1, 0.15)):
        c.poly([(cx + sx * r * 0.25 / asp, cy + r * 0.6), (cx + sx * r * (0.55 + lean) / asp, cy + r * 2.4),
                (cx + sx * r * (0.95 + lean) / asp, cy + r * 2.2), (cx + sx * r * 0.75 / asp, cy + r * 0.5)], col)
    c.circle(cx, cy, r, col)
    c.circle(cx + r * 0.35 / asp, cy + r * 0.15, r * 0.14, (0, 0, 0))
    c.poly([(cx - r * 0.55 / asp, cy - r * 1.1), (cx, cy - r * 0.95), (cx + r * 0.55 / asp, cy - r * 1.1),
            (cx + r * 0.55 / asp, cy - r * 1.55), (cx, cy - r * 1.35), (cx - r * 0.55 / asp, cy - r * 1.55)], col)


def mag_cover(rng, name):
    c = Canvas(192, 256)
    c.gradient(*BACKGROUNDS[int(rng.integers(0, len(BACKGROUNDS)))])
    c.circle(0.5, 0.5, 0.36, (1.0, 0.9, 0.5, 0.28))
    c.circle(0.5, 0.5, 0.27, (1.0, 0.9, 0.5, 0.22))
    figure(c, 0.5, 0.2, 0.67, rng, outfit=str(rng.choice(["bunny", "bunny", "bikini", "swim"])))
    mh = MASTHEADS[int(rng.integers(0, len(MASTHEADS)))]
    c.text_fit(mh, 0.06, 0.975, 0.72, 0.1, (1, 1, 1), bold=True, spacing=1.05)
    bunny_head(c, 0.9, 0.925, 0.055, (1, 1, 1))
    c.text(str(rng.choice(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]))
           + " " + str(int(rng.integers(1988, 2009))), 0.06, 0.865, 0.035, (1, 1, 1, 0.85))
    lines = [COVER_LINES[i] for i in rng.choice(len(COVER_LINES), 3, replace=False)]
    for i, (ln, col) in enumerate(zip(lines, ((1, 1, 0.55), (1, 1, 1), (1, 0.6, 0.7)))):
        c.text_fit(ln, 0.05, 0.175 - i * 0.055, 0.6, 0.042, col, bold=True, spacing=1.0)
    for i in range(14):
        c.rect(0.74 + i * 0.011, 0.03, 0.74 + i * 0.011 + (0.004 if i % 3 else 0.008), 0.1, (1, 1, 1))
    c.noise(rng, 0.015)
    return c.image(name)


def poster(rng, name):
    c = Canvas(384, 256)
    c.gradient(*BACKGROUNDS[int(rng.integers(0, len(BACKGROUNDS)))])
    for _ in range(22):
        c.circle(rng.uniform(0.04, 0.96), rng.uniform(0.05, 0.95), rng.uniform(0.004, 0.012), (1, 1, 1, 0.7))
    c.circle(0.27, 0.5, 0.42, (1.0, 0.9, 0.5, 0.22))
    figure(c, 0.27, 0.03, 0.94, rng, outfit=str(rng.choice(["bare", "bare", "bare", "bunny", "bikini"])))
    month = str(rng.choice(["JANUARY", "MARCH", "MAY", "JULY", "AUGUST", "OCTOBER"]))
    c.text_fit("MISS", 0.55, 0.88, 0.36, 0.17, (1, 1, 1), bold=True, spacing=1.0)
    c.text_fit(month, 0.55, 0.66, 0.38, 0.1, (1, 0.95, 0.4), bold=True, spacing=1.0)
    bio = rng.choice([("LOVES LONG WALKS", "AND ANALYZING CHARTS"), ("TURN-ONS: GREEN CANDLES", "TURN-OFFS: RUG PULLS"),
                      ("LIKES: LATE NIGHTS", "AND EARLY EXITS"), ("HOBBIES: HOT TUBS", "AND BAD TRADES"),
                      ("LOOKING FOR: A MAN", "WHO READS THE DOCS")])
    c.text_fit(bio[0], 0.53, 0.4, 0.42, 0.045, (1, 1, 1), spacing=1.0)
    c.text_fit(bio[1], 0.53, 0.32, 0.42, 0.045, (1, 1, 1), spacing=1.0)
    for fx in (0.334, 0.667):
        c.rect(fx - 0.004, 0.52, fx + 0.004, 0.56, (0.7, 0.7, 0.72))
        c.rect(fx - 0.004, 0.44, fx + 0.004, 0.48, (0.7, 0.7, 0.72))
    c.noise(rng, 0.015)
    return c.image(name)


def _bunny_tissue(c, rng):
    bunny_head(c, 0.5, 0.42, 0.12, (1.0, 1.0, 1.0, 0.9))


def tissue_print(rng, name):
    c = Canvas(128, 128, (*rng.choice([(0.75, 0.9, 0.95), (0.95, 0.8, 0.85), (0.85, 0.95, 0.8), (0.95, 0.92, 0.75)]), 1))
    for _ in range(18):
        x, y = rng.uniform(0, 1, 2)
        c.circle(x, y, rng.uniform(0.04, 0.08), (1, 1, 1, 0.8))
        c.circle(x, y, 0.02, (0.9, 0.7, 0.3))
    if rng.random() < 0.5:
        _bunny_tissue(c, rng)
        c.text_fit("BUNNY SOFT", 0.06, 0.2, 0.88, 0.12, (1, 1, 1), bold=True)
    else:
        c.text("SOFT", 0.08, 0.3, 0.2, (1, 1, 1), bold=True)
    return c.image(name)


def foil_print(rng, name):
    c = Canvas(64, 64)
    c.gradient(*rng.choice([((1.0, 0.85, 0.4), (0.8, 0.55, 0.15)), ((0.9, 0.92, 0.95), (0.55, 0.6, 0.68)),
                            ((0.3, 0.5, 0.95), (0.1, 0.2, 0.6))]))
    c.rect(0.06, 0.06, 0.94, 0.94, (1, 1, 1, 0.0))
    c.text("XL", 0.14, 0.72, 0.4, (0.15, 0.1, 0.05), bold=True)
    c.noise(rng, 0.03)
    return c.image(name)


def scratch_print(rng, name):
    c = Canvas(96, 224, (*rng.choice([(0.95, 0.85, 0.15), (0.9, 0.15, 0.2), (0.2, 0.75, 0.3)]), 1))
    c.text("LUCKY", 0.08, 0.95, 0.045, (1, 1, 1), bold=True)
    c.text("7S", 0.08, 0.89, 0.045, (1, 1, 1), bold=True)
    c.rect(0.08, 0.3, 0.92, 0.78, (0.72, 0.73, 0.76))
    for _ in range(7):
        c.scribble(rng, 0.12, rng.uniform(0.35, 0.72), 0.88, 0.05, (0.35, 0.36, 0.4), 0.03)
    c.text("TRY", 0.1, 0.25, 0.045, (0.1, 0.1, 0.1), bold=True)
    c.text("AGAIN", 0.1, 0.19, 0.045, (0.1, 0.1, 0.1), bold=True)
    c.noise(rng, 0.03)
    return c.image(name)


def beer_print(rng, name):
    base = rng.choice([(0.85, 0.85, 0.88), (0.95, 0.8, 0.25), (0.15, 0.3, 0.55), (0.6, 0.12, 0.1)])
    c = Canvas(256, 192, (*base, 1))
    c.rect(0, 0.3, 1, 0.72, (0.96, 0.95, 0.9) if base[0] < 0.8 else (0.1, 0.1, 0.12))
    ink = (0.1, 0.1, 0.12) if base[0] < 0.8 else (0.95, 0.95, 0.9)
    c.text(str(rng.choice(["LAGER", "LITE BEER", "COLD ONE", "PILSNER"])), 0.05, 0.62, 0.12, ink, bold=True)
    c.text("12 FL OZ", 0.05, 0.2, 0.08, (0.15, 0.15, 0.15) if base[0] > 0.5 else (1, 1, 1))
    c.noise(rng, 0.02)
    return c.image(name)


def matchbook_print(rng, name):
    c = Canvas(96, 128, (0.04, 0.04, 0.05, 1))
    c.rect(0.06, 0.06, 0.94, 0.94, (0.7, 0.1, 0.15, 0.0))
    c.text("GENTLEMENS", 0.08, 0.78, 0.06, (0.95, 0.75, 0.2), bold=True)
    c.text("CLUB", 0.14, 0.6, 0.12, (0.95, 0.15, 0.25), bold=True)
    c.text("OPEN LATE", 0.14, 0.25, 0.06, (1, 1, 1))
    c.noise(rng, 0.02)
    return c.image(name)


def mug_print(rng, name):
    base = rng.choice([(0.95, 0.95, 0.92), (0.95, 0.75, 0.2), (0.2, 0.5, 0.85), (0.15, 0.15, 0.17), (0.9, 0.3, 0.3)])
    c = Canvas(256, 128, (*base, 1))
    ink = (0.1, 0.1, 0.12) if sum(base) > 1.6 else (1, 1, 1)
    c.text("GM", 0.05, 0.78, 0.45, ink, bold=True)
    c.text("GM", 0.55, 0.78, 0.45, ink, bold=True)
    c.noise(rng, 0.015)
    return c.image(name)


def sun_label(rng, name):
    c = Canvas(256, 96, (1.0, 0.85, 0.15, 1))
    c.rect(0, 0, 1, 0.22, (0.1, 0.5, 0.95))
    c.text("SPF 100", 0.06, 0.85, 0.3, (0.9, 0.15, 0.1), bold=True)
    c.text("BROAD SPECTRUM", 0.08, 0.2, 0.12, (1, 1, 1), bold=True)
    return c.image(name)


def hdd_label(rng, name):
    c = Canvas(192, 128, (0.8, 0.82, 0.85, 1))
    c.rect(0.05, 0.6, 0.95, 0.66, (0.3, 0.3, 0.35))
    c.text("WALLET.DAT", 0.06, 0.52, 0.12, (0.1, 0.1, 0.12), bold=True)
    c.text("DO NOT DELETE", 0.06, 0.3, 0.09, (0.75, 0.1, 0.1), bold=True)
    c.text("S/N 88421", 0.06, 0.94, 0.08, (0.2, 0.2, 0.25))
    c.noise(rng, 0.03)
    return c.image(name)


def street_sign(rng, name):
    c = Canvas(512, 128, (0.96, 0.96, 0.94, 1))
    c.rect(0.012, 0.06, 0.988, 0.94, (0.05, 0.42, 0.22))
    c.text("HOOD ST", 0.14, 0.72, 0.42, (1, 1, 1), bold=True)
    c.text("100", 0.03, 0.88, 0.14, (1, 1, 1), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def newspaper(rng, name):
    c = Canvas(256, 320, (0.86, 0.85, 0.8, 1))
    c.text("THE LEDGER", 0.06, 0.96, 0.065, (0.05, 0.05, 0.05), bold=True)
    c.rect(0.04, 0.84, 0.96, 0.85, (0.05, 0.05, 0.05))
    c.text("EXTRA EXTRA", 0.06, 0.8, 0.06, (0.05, 0.05, 0.05), bold=True)
    c.rect(0.06, 0.4, 0.6, 0.64, (0.45, 0.45, 0.45))
    for i in range(12):
        c.rect(0.06, 0.36 - i * 0.025, rng.uniform(0.5, 0.94), 0.367 - i * 0.025, (0.3, 0.3, 0.3))
    for i in range(8):
        c.rect(0.65, 0.62 - i * 0.03, 0.94, 0.627 - i * 0.03, (0.3, 0.3, 0.3))
    c.noise(rng, 0.03)
    return c.image(name)


def play_money(rng, name):
    c = Canvas(256, 120, (0.68, 0.85, 0.65, 1))
    c.rect(0.02, 0.05, 0.98, 0.95, (0.85, 0.95, 0.8))
    c.rect(0.04, 0.1, 0.96, 0.9, (0.68, 0.85, 0.65))
    c.circle(0.5, 0.5, 0.28, (0.85, 0.95, 0.8))
    c.text("PLAY", 0.39, 0.62, 0.2, (0.15, 0.4, 0.2), bold=True)
    c.text("MONEY", 0.36, 0.38, 0.2, (0.15, 0.4, 0.2), bold=True)
    for x in (0.07, 0.83):
        c.text(str(rng.choice(["1", "5", "20", "100"])), x, 0.85, 0.2, (0.15, 0.4, 0.2), bold=True)
    c.noise(rng, 0.03)
    return c.image(name)


def card_print(rng, name):
    c = Canvas(96, 128, (0.96, 0.96, 0.94, 1))
    red = rng.random() < 0.5
    ink = (0.85, 0.05, 0.1) if red else (0.05, 0.05, 0.08)
    c.text(str(rng.choice(["A", "K", "Q", "J", "10", "7"])), 0.1, 0.92, 0.2, ink, bold=True)
    if red:
        c.poly([(0.5, 0.78), (0.72, 0.5), (0.5, 0.22), (0.28, 0.5)], ink)
    else:
        c.circle(0.42, 0.5, 0.16, ink)
        c.circle(0.58, 0.5, 0.16, ink)
        c.poly([(0.5, 0.78), (0.26, 0.45), (0.74, 0.45)], ink)
    c.noise(rng, 0.02)
    return c.image(name)


def badge_print(rng, name):
    c = Canvas(96, 128, (0.96, 0.96, 0.94, 1))
    c.rect(0, 0.72, 1, 1, (0.85, 0.1, 0.1))
    c.text("PRESS", 0.1, 0.92, 0.11, (1, 1, 1), bold=True)
    c.rect(0.28, 0.3, 0.72, 0.64, (0.6, 0.6, 0.62))
    c.text("ALL ACCESS", 0.1, 0.2, 0.055, (0.1, 0.1, 0.1), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def spectrum_print(rng, name):
    c = Canvas(512, 64)
    t = c.x
    h = (t * 5.0) % 6.0
    x = 1 - np.abs(h % 2 - 1)
    r = np.select([h < 1, h < 2, h < 3, h < 4, h < 5], [1, x, 0, 0, x], 1)
    g = np.select([h < 1, h < 2, h < 3, h < 4, h < 5], [x, 1, 1, x, 0], 0)
    b = np.select([h < 1, h < 2, h < 3, h < 4, h < 5], [0, 0, x, 1, 1], x)
    c.a[..., 0], c.a[..., 1], c.a[..., 2] = r, g, b
    for i in range(0, 512, 16):
        c.a[:, i:i + 2, :3] *= 0.85
    return c.image(name)


def sock_print(rng, name):
    c = Canvas(64, 128, (0.95, 0.95, 0.93, 1))
    col = rng.choice([(0.85, 0.1, 0.1), (0.1, 0.25, 0.8), (0.1, 0.1, 0.1)])
    c.rect(0, 0.82, 1, 0.88, col)
    c.rect(0, 0.72, 1, 0.78, col)
    c.noise(rng, 0.03)
    return c.image(name)


def watch_face(rng, name):
    c = Canvas(128, 128, (0.02, 0.02, 0.04, 1))
    for r, col in ((0.44, (1.0, 0.2, 0.35)), (0.35, (0.4, 1.0, 0.2)), (0.26, (0.2, 0.85, 1.0))):
        c.circle(0.5, 0.5, r, (*col, 0.25), ring=0.07)
        c.circle(0.5, 0.5, r, col, ring=0.07 * rng.uniform(0.3, 1.0))
    c.text(str(rng.choice(["9:41", "4:20", "3:07"])), 0.3, 0.6, 0.17, (1, 1, 1), bold=True, spacing=1.0)
    return c.image(name)


def sanitizer_label(rng, name):
    c = Canvas(256, 96, (0.95, 0.97, 0.98, 1))
    c.rect(0, 0, 1, 0.3, (0.1, 0.65, 0.85))
    c.text("KILLS", 0.06, 0.92, 0.38, (0.1, 0.55, 0.75), bold=True)
    c.text("99.9% OF GERMS", 0.06, 0.26, 0.11, (1, 1, 1), bold=True)
    return c.image(name)


def gas_label(rng, name):
    c = Canvas(128, 96, (1.0, 0.85, 0.1, 1))
    c.rect(0, 0, 1, 0.28, (0.05, 0.05, 0.05))
    c.text("GAS", 0.08, 0.92, 0.4, (0.85, 0.08, 0.05), bold=True)
    c.text("$9.99", 0.1, 0.22, 0.13, (1, 0.85, 0.1), bold=True)
    return c.image(name)


# -- gift-block prints ---------------------------------------------------------------------------

_LIME = (0.8, 1.0, 0.0)          # CCFF00
_VOID = (0.012, 0.012, 0.014)
_NEON_WORDS = ["MY NEON", "PROOF OF NEON", "ONE COLOR", "SQUARE", "IS THE WALLET", "NEON", "HEX", "ONE OF ONE"]


def neon_tile(rng, name, neg=False, big=False):
    """A flat CCFF00 tile with small black mono type. `neg` flips it: black tile, lime type. `big` is the headliner."""
    bg, ink = (_VOID, _LIME) if neg else (_LIME, (0.02, 0.02, 0.02))
    n = 512 if big else 192
    c = Canvas(n, n, (*ink, 1))
    c.rect(0.022, 0.022, 0.978, 0.978, bg)      # a hairline of the other color, so every tile reads as a tile
    if big:
        c.rect(0.035, 0.035, 0.965, 0.965, ink)
        c.rect(0.045, 0.045, 0.955, 0.955, bg)
        c.text("HEX /", 0.08, 0.92, 0.06, ink, bold=True)
        c.text_fit("CCFF00", 0.07, 0.64, 0.86, 0.3, ink, spacing=0.95, bold=True)
        c.text_fit("ONE COLOR.", 0.08, 0.34, 0.84, 0.06, ink, bold=True)
        c.text_fit("THOUSANDS OF", 0.08, 0.255, 0.84, 0.06, ink, bold=True)
        c.text_fit("UNIQUE IDENTITIES.", 0.08, 0.17, 0.84, 0.06, ink, bold=True)
        c.text("204 255 000", 0.08, 0.1, 0.04, ink)
        c.text("#0001", 0.76, 0.1, 0.04, ink)
        return c.image(name)
    style = int(rng.choice(7, p=[0.14, 0.16, 0.16, 0.1, 0.12, 0.14, 0.18]))
    num = str(int(rng.integers(1, 9999))).zfill(4)
    if style == 0:
        c.text(num, 0.08, 0.93, 0.07, ink)
        c.text_fit("CCFF00", 0.08, 0.2, 0.84, 0.075, ink, bold=True)
    elif style == 1:
        c.text_fit("CCFF00", 0.08, 0.6, 0.84, 0.3, ink, spacing=0.95, bold=True)
    elif style == 2:
        c.text("HEX", 0.08, 0.93, 0.09, ink, bold=True)
        c.text_fit("CCFF00", 0.08, 0.58, 0.84, 0.3, ink, spacing=0.95, bold=True)
    elif style == 3:
        for k, t in enumerate(("204", "255", "000")):
            c.text(t, 0.12, 0.9 - k * 0.3, 0.24, ink, bold=True)
    elif style == 4:
        c.rect(0.12, 0.12, 0.88, 0.88, ink)
        c.rect(0.17, 0.17, 0.83, 0.83, bg)
        c.text_fit("#CCFF00", 0.22, 0.54, 0.56, 0.08, ink, bold=True)
    elif style == 5:
        w = str(rng.choice(_NEON_WORDS))
        if len(w) > 9:
            a, b2 = w.rsplit(" ", 1)
            c.text_fit(a, 0.08, 0.68, 0.84, 0.18, ink, bold=True)
            c.text_fit(b2, 0.08, 0.42, 0.84, 0.18, ink, bold=True)
        else:
            c.text_fit(w, 0.08, 0.6, 0.84, 0.22, ink, bold=True)
    else:
        c.rect(0.08, 0.08, 0.2, 0.2, ink)
    return c.image(name)


_COMPANIES = ["HOOD ST PIG CO", "BULLS BEARS AND PIGS", "OINK HOLDINGS", "SLOP FUND LLC", "TROUGH CAPITAL"]


def _pig_head(c, cx, cy, r, skin=(0.96, 0.62, 0.72), dark=(0.8, 0.38, 0.5), ink=(0.1, 0.05, 0.06)):
    """A small flat pig face: head, two ears, snout with nostrils, two eyes."""
    asp = c.w / c.h
    for sx in (-1, 1):
        c.poly([(cx + sx * r * 0.35 / asp, cy + r * 0.8), (cx + sx * r * 1.05 / asp, cy + r * 1.15),
                (cx + sx * r * 1.0 / asp, cy + r * 0.3)], dark)
    c.circle(cx, cy, r, skin)
    c.circle(cx, cy - r * 0.22, r * 0.46, dark)
    c.circle(cx, cy - r * 0.22, r * 0.4, skin)
    for sx in (-1, 1):
        c.circle(cx + sx * r * 0.14 / asp, cy - r * 0.22, r * 0.07, ink)
        c.circle(cx + sx * r * 0.42 / asp, cy + r * 0.28, r * 0.09, ink)


def stock_cert(rng, name):
    paper, green = (0.93, 0.9, 0.78), (0.1, 0.35, 0.2)
    c = Canvas(320, 224, (*paper, 1))
    c.rect(0.02, 0.03, 0.98, 0.97, green)
    c.rect(0.03, 0.045, 0.97, 0.955, paper)
    c.rect(0.05, 0.07, 0.95, 0.93, green)
    c.rect(0.056, 0.083, 0.944, 0.917, paper)
    c.text_fit("SHARE CERTIFICATE", 0.1, 0.88, 0.8, 0.075, green, bold=True)
    _pig_head(c, 0.16, 0.6, 0.085)
    c.text_fit(str(rng.choice(_COMPANIES)), 0.28, 0.72, 0.62, 0.075, (0.08, 0.08, 0.1), bold=True)
    c.text_fit(str(rng.choice(["10", "69", "100", "420", "888", "1000"])) + " SHARES", 0.28, 0.55, 0.62, 0.12,
               (0.08, 0.08, 0.1), bold=True)
    c.text_fit("BULLS MAKE MONEY. BEARS MAKE MONEY.", 0.1, 0.32, 0.8, 0.045, (0.2, 0.2, 0.22))
    c.text_fit("PIGS GET SLAUGHTERED.", 0.1, 0.25, 0.8, 0.055, (0.75, 0.1, 0.1), bold=True)
    c.scribble(rng, 0.12, 0.14, 0.42, 0.012, (0.1, 0.1, 0.25), amp=0.02)
    c.circle(0.8, 0.17, 0.085, (0.85, 0.68, 0.2))
    c.circle(0.8, 0.17, 0.065, (0.95, 0.82, 0.35), ring=0.008)
    c.text("$", 0.775, 0.215, 0.09, (0.5, 0.35, 0.05), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def ticker_tape(rng, name):
    c = Canvas(2048, 64, (0.95, 0.94, 0.88, 1))
    green, red = (0.05, 0.5, 0.15), (0.75, 0.1, 0.1)
    toks = [("PIG +420%", green), ("RUG -100%", red), ("BULL +12%", green), ("BEAR -3%", red), ("OINK +69%", green),
            ("HOOD +8%", green), ("GM +1%", green), ("SLOP -42%", red), ("TRUFFLE +5%", green), ("EXIT -88%", red)]
    x = 0.01
    for k in rng.permutation(len(toks)).tolist() * 2:
        t, col = toks[k]
        x = c.text(t, x, 0.8, 0.6, col, bold=True) + 0.02
        if x > 0.93:
            break
    c.noise(rng, 0.02)
    return c.image(name)


def tie_print(rng, name):
    base = [(0.75, 0.08, 0.12), (0.08, 0.25, 0.6), (0.9, 0.45, 0.6), (0.1, 0.45, 0.25), (0.45, 0.1, 0.55)]
    col = base[int(rng.integers(0, len(base)))]
    light = tuple(min(1.0, x * 0.4 + 0.6) for x in col)
    c = Canvas(128, 256, (*col, 1))
    a = float(rng.uniform(0.15, 0.3))
    for k in range(-3, 14):
        y0 = k * 0.12
        c.poly([(0, y0), (1, y0 + a), (1, y0 + a + 0.035), (0, y0 + 0.035)], light)
    c.noise(rng, 0.02)
    return c.image(name)


def pixel_art(rng, name):
    """A tiny pixel picture in a room's palette: purple ground, a lime something in the middle, a few stars."""
    c = Canvas(64, 64, (0.1, 0.03, 0.18, 1))
    n = 16
    px = 1.0 / n
    for _ in range(int(rng.integers(3, 7))):
        i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
        c.rect(i * px, j * px, (i + 1) * px, (j + 1) * px, (0.9, 0.9, 1.0))
    col = tuple(rng.choice([(0.55, 1.0, 0.1), (0.45, 0.15, 0.75), (0.9, 0.3, 0.6)]))
    shape = int(rng.integers(0, 3))
    cells = {0: [(7, 4), (8, 4), (6, 5), (9, 5), (6, 6), (9, 6), (7, 7), (8, 7), (5, 8), (10, 8), (7, 9), (8, 9)],   # a bug
             1: [(6, 5), (9, 5), (5, 6), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (5, 7), (10, 7), (6, 8), (7, 8), (8, 8), (9, 8), (7, 9), (8, 9)],  # a heart
             2: [(x, y) for x in range(5, 11) for y in range(5, 11) if (x + y) % 2 == 0]}[shape]   # a checker
    for i, j in cells:
        c.rect(i * px, j * px, (i + 1) * px, (j + 1) * px, col)
    return c.image(name)


# -- the parody shelf: every product print, re-done with era brands in the ballpark ---------------------
from . import parody as _pd

ERA = {"i": None}          # the era being built; set by the builder so the shelf matches the year


def _brand(rng, table):
    return _pd.pick(rng, table, ERA["i"])


def can_print(rng, name):
    """Soda or energy, by era. Wraps a can laid flat: band, big name, a bolt of accent."""
    table = _pd.ENERGY if rng.random() < 0.45 else _pd.SODA
    nm, _e, (base, hi, ink) = _brand(rng, table)
    c = Canvas(512, 256, (*base, 1))
    for k in range(3):
        xs = np.linspace(0, 1, 30)
        ys = 0.5 + 0.25 * np.sign(np.sin(xs * (18 + k * 7) + k)) * rng.uniform(0.3, 1, 30) + (k - 1) * 0.12
        c.line(list(zip(xs, ys)), 0.03, hi)
    c.rect(0, 0.36, 1, 0.66, (*base, 0.85))
    c.text_fit(nm, 0.06, 0.62, 0.88, 0.24, ink, bold=True, spacing=1.05)
    c.text_fit(str(rng.choice(["12 FL OZ", "ZERO SUGAR LOL", "NOW WITH MORE", "CAFFEINE: YES", "NOT A DRINK"])),
               0.06, 0.2, 0.6, 0.07, ink)
    c.noise(rng, 0.015)
    return c.image(name)


def beer_print(rng, name):
    nm, _e, (base, hi, ink) = _brand(rng, _pd.BEER)
    c = Canvas(256, 192, (*base, 1))
    c.rect(0, 0.7, 1, 0.8, hi)
    c.rect(0, 0.18, 1, 0.24, hi)
    c.text_fit(nm, 0.06, 0.62, 0.88, 0.2, ink, bold=True)
    c.text_fit(str(rng.choice(["COLD WHEN YOU BOUGHT IT", "12 OF 12", "BEST SERVED WARM", "THE BANQUET-ISH BEER",
                               "LIGHT, IN THEORY"])), 0.06, 0.15, 0.88, 0.06, ink)
    c.noise(rng, 0.02)
    return c.image(name)


def ramen(rng, name):
    nm, _e, (base, hi, ink) = _brand(rng, _pd.RAMEN)
    c = Canvas(320, 256, (*base, 1))
    c.circle(0.5, 0.42, 0.3, (0.95, 0.95, 0.92))
    c.circle(0.5, 0.42, 0.24, (0.95, 0.8, 0.45))
    for i in range(6):
        xs = np.linspace(0.32, 0.68, 30)
        c.line(list(zip(xs, 0.3 + i * 0.04 + 0.015 * np.sin(xs * 60 + i))), 0.01, (0.98, 0.9, 0.6))
    c.text_fit(nm, 0.08, 0.96, 0.84, 0.12, ink, bold=True)
    c.text_fit(str(rng.choice(["PAYDAY FLAVOR", "BEEF-ADJACENT", "CHICKEN-ISH", "SPICY REGRET", "SHRIMP (1)"])),
               0.2, 0.1, 0.6, 0.07, ink)
    return c.image(name)


def vape_print(rng, name):
    nm, _e, (a, b, ink) = _brand(rng, _pd.VAPE)
    c = Canvas(256, 96)
    c.gradient(a, b)
    c.text_fit(nm, 0.06, 0.92, 0.5, 0.24, ink, bold=True)
    c.text_fit(str(rng.choice(_pd.VAPE_FLAVORS)), 0.06, 0.55, 0.88, 0.2, (0.05, 0.05, 0.05), bold=True)
    c.text_fit(str(rng.choice(["5000 PUFFS", "7000 PUFFS", "0% REGRET (LIE)"])), 0.06, 0.22, 0.6, 0.13, (1, 1, 1))
    return c.image(name)


def battery(rng, name):
    nm, _e, (top, band, ink) = _brand(rng, _pd.BATTERY)
    c = Canvas(256, 128, (*band, 1))
    c.rect(0, 0.0, 1, 0.62, top)
    c.text_fit(nm, 0.06, 0.55, 0.88, 0.26, ink, bold=True)
    c.text("AA 1.5V", 0.06, 0.95, 0.14, (0.1, 0.1, 0.1) if sum(band) > 1.5 else (1, 1, 1), bold=True)
    c.text_fit(str(rng.choice(["LASTS FOREVER (NO)", "ALKALINE", "LICKED, ONCE"])), 0.06, 0.18, 0.88, 0.1,
               ink)
    return c.image(name)


def sun_label(rng, name):
    nm, _e, (base, hi, ink) = _brand(rng, _pd.SUNSCREEN)
    c = Canvas(256, 96, (*base, 1))
    c.circle(0.85, 0.55, 0.3, (1.0, 0.85, 0.2))
    c.text_fit(nm, 0.05, 0.9, 0.7, 0.32, ink, bold=True)
    c.text_fit(str(rng.choice(["SPF 100, STILL BURNED", "SPF 4 (OIL)", "TANNING LOTION", "WATERPROOF-ISH"])),
               0.05, 0.38, 0.7, 0.18, hi, bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def tissue_print(rng, name):
    c = Canvas(128, 128, (*rng.choice([(0.75, 0.9, 0.95), (0.95, 0.8, 0.85), (0.85, 0.95, 0.8), (0.95, 0.92, 0.75)]), 1))
    for _ in range(18):
        x, y = rng.uniform(0, 1, 2)
        c.circle(x, y, rng.uniform(0.04, 0.08), (1, 1, 1, 0.8))
        c.circle(x, y, 0.02, (0.9, 0.7, 0.3))
    nm = str(rng.choice([b[0] for b in _pd.TISSUE]))
    if nm == "BUNNY SOFT":
        bunny_head(c, 0.5, 0.48, 0.12, (1.0, 1.0, 1.0, 0.95))
    c.text_fit(nm, 0.05, 0.24, 0.9, 0.14, (0.15, 0.25, 0.6), bold=True)
    c.text_fit("FOR WHATEVER", 0.05, 0.08, 0.6, 0.06, (0.15, 0.25, 0.6))
    return c.image(name)


def matchbook_print(rng, name):
    c = Canvas(96, 128, (0.05, 0.05, 0.06, 1))
    club = str(rng.choice(_pd.CLUBS))
    gold = (0.9, 0.75, 0.35)
    c.rect(0.05, 0.05, 0.95, 0.95, gold)
    c.rect(0.08, 0.08, 0.92, 0.92, (0.05, 0.05, 0.06))
    words = club.split()
    for i, w in enumerate(words[:3]):
        c.text_fit(w, 0.12, 0.88 - i * 0.13, 0.76, 0.11, gold, bold=True)
    pts = [(0.5, 0.42), (0.44, 0.3), (0.47, 0.18), (0.42, 0.12), (0.5, 0.15), (0.58, 0.12), (0.53, 0.18),
           (0.56, 0.3)]
    c.poly(pts, (1.0, 0.4, 0.6))
    c.circle(0.5, 0.47, 0.04, (1.0, 0.4, 0.6))
    c.text_fit("OPEN LATE", 0.18, 0.08, 0.64, 0.06, gold)
    return c.image(name)


def mug_print(rng, name):
    c = Canvas(256, 128, (0.96, 0.95, 0.92, 1))
    if rng.random() < 0.6:
        c.text("GM", 0.3, 0.85, 0.55, (0.05, 0.05, 0.05), bold=True)
        c.text_fit("EVERY SINGLE DAY", 0.25, 0.2, 0.5, 0.08, (0.4, 0.4, 0.4))
    else:
        nm = _pd.pick(rng, [(b[0], b[1], None) for b in _pd.COFFEE], ERA["i"])[0]
        c.circle(0.5, 0.62, 0.22, (0.05, 0.4, 0.25))
        c.circle(0.5, 0.62, 0.16, (0.96, 0.95, 0.92))
        c.circle(0.5, 0.62, 0.07, (0.05, 0.4, 0.25))
        c.text_fit(nm, 0.2, 0.28, 0.6, 0.16, (0.05, 0.4, 0.25), bold=True)
    c.noise(rng, 0.01)
    return c.image(name)


def sanitizer_label(rng, name):
    nm = _pd.pick(rng, [(b[0], b[1], None) for b in _pd.SANITIZER], ERA["i"])[0]
    c = Canvas(256, 96, (0.96, 0.97, 1.0, 1))
    c.rect(0, 0.0, 1, 0.3, (0.1, 0.35, 0.8))
    c.text_fit(nm, 0.05, 0.92, 0.9, 0.34, (0.1, 0.35, 0.8), bold=True)
    c.text_fit("KILLS 99.9% (NOT THE DIP)", 0.05, 0.24, 0.9, 0.14, (1, 1, 1), bold=True)
    return c.image(name)


def gas_label(rng, name):
    nm = _pd.pick(rng, [(b[0], b[1], None) for b in _pd.GAS], ERA["i"])[0]
    c = Canvas(128, 96, (0.95, 0.8, 0.1, 1))
    c.poly([(0.5, 0.95), (0.95, 0.5), (0.5, 0.05), (0.05, 0.5)], (0.05, 0.05, 0.05))
    c.poly([(0.5, 0.88), (0.88, 0.5), (0.5, 0.12), (0.12, 0.5)], (0.95, 0.8, 0.1))
    c.text_fit("GAS FEES", 0.2, 0.62, 0.6, 0.14, (0.05, 0.05, 0.05), bold=True)
    c.text_fit(nm, 0.22, 0.42, 0.56, 0.1, (0.75, 0.1, 0.1), bold=True)
    return c.image(name)


def hdd_label(rng, name):
    nm = _pd.pick(rng, [(b[0], b[1], None) for b in _pd.DRIVES], ERA["i"])[0]
    c = Canvas(192, 128, (0.85, 0.86, 0.88, 1))
    c.rect(0, 0.78, 1, 1, (0.1, 0.12, 0.2))
    c.text_fit(nm, 0.05, 0.96, 0.9, 0.14, (1, 1, 1), bold=True)
    c.text("WALLET.DAT", 0.06, 0.62, 0.12, (0.1, 0.1, 0.12), bold=True)
    c.text("DO NOT DELETE", 0.06, 0.4, 0.09, (0.75, 0.1, 0.1), bold=True)
    for i in range(30):
        c.rect(0.06 + i * 0.01, 0.06, 0.064 + i * 0.01 + (0.004 if i % 3 else 0), 0.2, (0.1, 0.1, 0.1))
    c.noise(rng, 0.02)
    return c.image(name)


def scratch_print(rng, name):
    c = Canvas(96, 224, (0.85, 0.1, 0.12, 1))
    c.rect(0.05, 0.75, 0.95, 0.97, (0.95, 0.8, 0.2))
    c.text_fit(str(rng.choice(_pd.LOTTERY)), 0.08, 0.93, 0.84, 0.07, (0.6, 0.05, 0.05), bold=True)
    for r in range(3):
        for q in range(3):
            x, y = 0.1 + q * 0.28, 0.66 - r * 0.17
            silver = rng.random() < 0.55
            c.rect(x, y - 0.13, x + 0.24, y, (0.75, 0.75, 0.78) if silver else (0.98, 0.95, 0.85))
            if not silver:
                c.text("$", x + 0.07, y - 0.02, 0.07, (0.1, 0.5, 0.15), bold=True)
    c.text_fit("NOT A WINNER", 0.08, 0.1, 0.84, 0.05, (1, 1, 1), bold=True)
    c.noise(rng, 0.03)
    return c.image(name)


def play_money(rng, name):
    c = Canvas(256, 120, (0.68, 0.85, 0.65, 1))
    c.rect(0.02, 0.05, 0.98, 0.95, (0.85, 0.95, 0.8))
    c.rect(0.04, 0.1, 0.96, 0.9, (0.68, 0.85, 0.65))
    c.circle(0.5, 0.5, 0.28, (0.85, 0.95, 0.8))
    c.text_fit(str(rng.choice(_pd.MONEY)), 0.28, 0.66, 0.44, 0.14, (0.15, 0.4, 0.2), bold=True)
    c.text_fit("NO CASH VALUE", 0.32, 0.36, 0.36, 0.1, (0.15, 0.4, 0.2), bold=True)
    for x in (0.07, 0.83):
        c.text(str(rng.choice(["1", "5", "20", "100", "500"])), x, 0.85, 0.2, (0.15, 0.4, 0.2), bold=True)
    c.noise(rng, 0.03)
    return c.image(name)


def griptape_art(rng, name):
    c = Canvas(128, 512, (0.06, 0.06, 0.07, 1))
    brand = str(rng.choice(_pd.SKATE))
    col = tuple(rng.choice([(0.95, 0.35, 0.05), (0.9, 0.1, 0.15), (1, 1, 1), (0.55, 1.0, 0.1)]))
    for k, w in enumerate(brand.split()[:3]):
        c.text_fit(w, 0.08, 0.95 - k * 0.07, 0.84, 0.06, col, bold=True)
    c.circle(0.5, 0.45, 0.32, col, ring=0.05)
    c.poly([(0.38, 0.5), (0.5, 0.6), (0.62, 0.5), (0.58, 0.32), (0.42, 0.32)], col)
    c.noise(rng, 0.05)
    return c.image(name)


def sticker(rng, name, base=(0.95, 0.94, 0.9), lines=4, words=None):
    c = Canvas(256, 128, (*base, 1))
    w = words or str(rng.choice(_pd.SKATE + ["NO REFUNDS", "HONK IF HODL", "MY OTHER CAR IS A LAMBO (NO)"]))
    bg = tuple(rng.choice([(0.05, 0.05, 0.05), (0.9, 0.1, 0.15), (0.1, 0.3, 0.85), (0.95, 0.8, 0.1)]))
    c.rect(0.03, 0.08, 0.97, 0.92, bg, soft=0.02)
    c.text_fit(w, 0.07, 0.68, 0.86, 0.36, (1, 1, 1) if sum(bg) < 1.5 else (0.05, 0.05, 0.05), bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


def sock_print(rng, name):
    c = Canvas(64, 128, (0.95, 0.95, 0.93, 1))
    col = tuple(rng.choice([(0.85, 0.1, 0.1), (0.1, 0.25, 0.8), (0.1, 0.1, 0.1)]))
    c.rect(0, 0.82, 1, 0.86, col)
    c.rect(0, 0.76, 1, 0.8, col)
    c.text_fit(str(rng.choice(_pd.SOCKS)), 0.08, 0.6, 0.84, 0.08, (0.4, 0.4, 0.4), bold=True)
    c.rect(0.55, 0.0, 1.0, 0.2, (0.85, 0.82, 0.65))
    c.noise(rng, 0.02)
    return c.image(name)


# -- drop-in art slots -----------------------------------------------------------------------------
# Every printed surface above is a slot. Put a PNG named after the slot in assets/slots/ (slot.png, or
# slot_anything.png for several variants, dealt per object) and it is used instead of the procedural one.
# Nothing in the recipe changes; the files are hashed into the manifest, so the final art stays reproducible.

import glob
import hashlib
import os

SLOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "slots")
SLOT_NAMES = ["sticker", "keypad", "notebook", "chart", "pcb", "can_print", "ramen", "screen", "griptape_art", "battery",
              "cd_marker", "app_grid", "lockscreen", "vape_print", "mag_cover", "poster", "tissue_print", "foil_print",
              "scratch_print", "beer_print", "matchbook_print", "mug_print", "sun_label", "hdd_label", "street_sign",
              "newspaper", "play_money", "card_print", "badge_print", "spectrum_print", "sock_print", "watch_face",
              "sanitizer_label", "gas_label", "pixel_art", "neon_tile", "stock_cert", "ticker_tape", "tie_print"]


def slot_files(slot):
    if not os.path.isdir(SLOT_DIR):
        return []
    hits = glob.glob(os.path.join(SLOT_DIR, slot + ".png")) + glob.glob(os.path.join(SLOT_DIR, slot + "_*.png"))
    return sorted(hits)


def slot_hashes():
    """{filename: sha256} of every slot file: part of the collection's provenance."""
    out = {}
    if os.path.isdir(SLOT_DIR):
        for f in sorted(glob.glob(os.path.join(SLOT_DIR, "*.png"))):
            with open(f, "rb") as fh:
                out[os.path.basename(f)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _slotted(fn):
    def wrapped(rng, name, *args, **kw):
        files = slot_files(fn.__name__)
        if files:
            path = files[int(rng.integers(0, len(files)))] if len(files) > 1 else files[0]
            img = bpy.data.images.load(path, check_existing=True)
            img.colorspace_settings.name = "sRGB"
            return img
        return fn(rng, name, *args, **kw)
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


for _n in SLOT_NAMES:
    globals()[_n] = _slotted(globals()[_n])
