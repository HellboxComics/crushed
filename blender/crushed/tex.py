"""Procedural raster textures (labels, screens, prints) drawn with numpy.

No PIL, no fonts on disk: this runs inside stock Blender. Text uses a tiny
built-in 5x7 bitmap font, which is exactly the right look for LCDs, stamped
steel and cheap labels anyway.
"""
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
    """Linear-ish colours in this module are specified in display space."""
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


def lcd(rng, name, text=None, bg=(0.55, 0.62, 0.45), ink=(0.08, 0.1, 0.06), w=256, h=96):
    c = Canvas(w, h, (*bg, 1))
    t = text or rng.choice(["911", "143", "07734", "8008", "1337", "420", "555-0199", "HELLO", "88:88",
                            "12:00", "LOW BATT", "ERROR", "GM", "NO SIGNAL", "0.00"])
    c.text(t, 0.08, 0.8, 0.55, ink, bold=True)
    c.noise(rng, 0.02)
    return c.image(name)


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
