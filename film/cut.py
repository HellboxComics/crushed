"""Edit the hero film: put the rendered shots in order, add the words, the dying-bulb flicker, the montage speed-up,
the end card, grain and vignette, and encode the MP4.

    python3 film/cut.py --src renders/film --out renders/crushed_buzz_hero.mp4
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan  # noqa: E402

FONT = {w: os.path.join(HERE, "fonts", f"IBMPlexMono-{w}.ttf") for w in ("Bold", "Medium", "Light")}
_fonts = {}


def font(weight, px):
    k = (weight, px)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT[weight], px)
    return _fonts[k]


class Cut:
    def __init__(self, src, scale, square=False):
        self.src = src
        self.fw, self.h = round(plan.W * scale), round(plan.H * scale)    # the rendered frame
        self.w = self.h if square else self.fw                            # the square cut keeps the middle
        self.cache = {}
        self.rng = np.random.default_rng(888)
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        r = np.hypot((xx - self.w / 2) / (self.w / 2), (yy - self.h / 2) / (self.h / 2))
        self.vignette = np.clip(1.08 - 0.42 * r ** 2.2, 0.35, 1.0)[..., None]

    # ---- sources
    def shot(self, name, n):
        """Frame n (1-based) of a rendered shot; with a draft step, the nearest frame rendered before it."""
        d = os.path.join(self.src, name)
        step = int(open(os.path.join(d, ".done")).read() or 1) if os.path.exists(os.path.join(d, ".done")) else 1
        n = 1 + ((n - 1) // step) * step
        p = os.path.join(d, f"{n:04d}.png")
        if p not in self.cache:
            if len(self.cache) > 40:
                self.cache.clear()
            im = Image.open(p).convert("RGB")
            if im.size != (self.fw, self.h):
                im = im.resize((self.fw, self.h), Image.LANCZOS)
            if self.w != self.fw:
                x0 = (self.fw - self.w) // 2
                im = im.crop((x0, 0, x0 + self.w, self.h))
            self.cache[p] = np.asarray(im, dtype=np.float32) / 255
        return self.cache[p].copy()

    def black(self):
        return np.zeros((self.h, self.w, 3), np.float32)

    def push(self, img, k):
        """Zoom in by k (1.0 = none) around the center: the slow push that keeps a still from feeling frozen."""
        if k <= 1.0001:
            return img
        h, w = img.shape[:2]
        cw, ch = w / k, h / k
        x0, y0 = (w - cw) / 2, (h - ch) / 2
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        im = im.resize((w, h), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        return np.asarray(im, dtype=np.float32) / 255

    # ---- words
    def text(self, img, s, size, color, alpha=1.0, y=0.5, weight="Medium", track=0.14, glow=0.0):
        px = max(8, round(self.h * size))
        f = font(weight, px)
        widths = [f.getlength(ch) for ch in s]
        gap = px * track
        total = sum(widths) + gap * (len(s) - 1)
        if total > self.w * 0.88:                       # too wide for this frame (the square cut): shrink to fit
            px = max(8, int(px * self.w * 0.88 / total))
            f = font(weight, px)
            widths = [f.getlength(ch) for ch in s]
            gap = px * track
            total = sum(widths) + gap * (len(s) - 1)
        layer = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(layer)
        x = (self.w - total) / 2
        top = self.h * y - px * 0.62
        for ch, cw in zip(s, widths):
            d.text((x, top), ch, font=f, fill=255)
            x += cw + gap
        m = np.asarray(layer, np.float32)[..., None] / 255 * alpha
        col = np.array(color, np.float32) / 255
        if glow:
            g = np.asarray(layer.filter(ImageFilter.GaussianBlur(px * 0.35)), np.float32)[..., None] / 255
            img = img + g * col * glow * alpha
        return img * (1 - m) + col * m

    # ---- finishing
    def finish(self, img, f):
        img = img * self.vignette
        g = self.rng.normal(0, 0.018, (self.h // 2, self.w // 2, 1)).astype(np.float32)
        g = np.repeat(np.repeat(g, 2, 0), 2, 1)[: self.h, : self.w]
        img = img + g * (0.35 + 0.65 * np.sqrt(np.clip(img.mean(-1, keepdims=True), 0, 1)))
        return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def fade(f, a, b, fin=5, fout=4):
    """0..1 for a card shown from frame a to b, with a quick fade in and out."""
    if f < a or f > b:
        return 0.0
    return min(1.0, (f - a + 1) / fin, (b - f + 1) / fout)


def bulb(n):
    """The dying bulb: a seeded flicker. Starts dark, catches, stutters, mostly holds."""
    r = np.random.default_rng(31)
    v = np.ones(n, np.float32) * 0.9
    v[:3] = 0.0
    v[3:5] = (0.8, 0.15)
    v[5:7] = 0.0
    for i in range(7, n):
        if r.random() < 0.10:
            v[i] = r.uniform(0.0, 0.35)
        elif r.random() < 0.08:
            v[i] = 1.25                       # a surge
        else:
            v[i] = r.uniform(0.82, 0.98)
    return v


def frames(c):
    """Yield every finished frame of the film, in order."""
    yield from opening(c)
    yield from concept(c)
    yield from reveal(c)
    yield from montage(c)
    yield from ending(c)


def opening(c):
    fl = bulb(72)
    for i in range(72):
        name, n = ("open_a", i + 1) if i < 36 else ("open_b", i - 35)
        yield c.shot(name, n) * fl[i] * 0.95


def concept(c):
    for i in range(144):
        f = 72 + i
        img = c.shot("concept", i + 1) * 0.8
        for a, b, s, size, col in plan.CARDS:
            al = fade(f, a, b)
            if al:
                img = img * (1 - 0.35 * al)          # the picture steps back while a line is up
                img = c.text(img, s, size, col, al, y=0.5, glow=0.6 if col == plan.LIME else 0.0)
        yield img


def reveal(c):
    for i in range(120):
        img = c.shot("reveal", i + 1)
        if i < 2:
            img = img * 0.4 + np.array([1.0, 0.55, 0.15], np.float32) * (0.6 if i == 0 else 0.3)   # lights slam on
        al = fade(i, 46, 119, fin=8, fout=1)
        if al:
            img = c.text(img, "TRICK OR TREAT", 0.05, plan.BONE, al, y=0.085, weight="Bold", track=0.2)
            img = c.text(img, f"ONE OF ONE  ·  01/{plan.COUNT}", 0.024, plan.LIME, al, y=0.15, track=0.3)
        yield img


def montage(c):
    holds = plan.montage_holds()
    late = len(holds) - 7
    for k, (cube, hold) in enumerate(zip(plan.MONTAGE, holds)):
        for i in range(hold):
            img = c.push(c.shot(f"m_{cube:04d}", 1), 1.0 + 0.05 * (i + 1) / hold)
            if k >= late and i == 0:
                img = img * 0.5 + 0.5                  # the last cuts hit with a white flash
            img = c.text(img, plan.NAMES[cube], 0.04, plan.BONE, 1.0, y=0.085, weight="Bold", track=0.2)
            img = c.text(img, f"ONE OF ONE  ·  {k + 2:02d}/{plan.COUNT}", 0.024, plan.LIME, 1.0, y=0.15, track=0.3)
            yield img


def ending(c):
    e = plan.END
    for i in range(e["black"]):
        yield c.black()
    for i in range(e["title"]):
        img = c.black()
        img = c.text(img, "crushed.buzz", 0.115, plan.LIME, min(1.0, (i + 1) / 6), y=0.45, weight="Bold",
                     track=0.04, glow=0.9)
        if i >= 14:
            img = c.text(img, f"888 CUBES  ·  {plan.COUNT} ONE-OF-ONES  ·  SOON", 0.026, (170, 166, 158), min(1.0, (i - 13) / 6),
                         y=0.6, track=0.3)
        yield img
    for i in range(e["button"] + e["fade"]):
        al = min(1.0, (i + 1) / 3) * (1.0 if i < e["button"] else 1 - (i - e["button"] + 1) / e["fade"])
        yield c.text(c.black(), "WE KEPT THE IMPORTANT SHIT.", 0.04, plan.BONE, al, y=0.5, track=0.2)


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("no ffmpeg: pip install imageio-ffmpeg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="renders/film")
    ap.add_argument("--out", default="renders/crushed_buzz_hero.mp4")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--stills", help="also save these frame numbers as PNGs here (storyboard)", default=None)
    ap.add_argument("--square", action="store_true", help="the 1:1 cut for phones (the middle of the frame)")
    ap.add_argument("--silent", action="store_true", help="leave the sound off")
    a = ap.parse_args()
    c = Cut(a.src, a.scale, a.square)
    pick = set(range(0, 576, 24)) if a.stills else set()
    if a.stills:
        os.makedirs(a.stills, exist_ok=True)
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{c.w}x{c.h}",
           "-r", str(plan.FPS), "-i", "-"]
    mix = os.path.join(HERE, "audio", "hero_mix.wav")            # made by film/sound.py; silent film without it
    if os.path.exists(mix) and not a.silent:
        cmd += ["-i", mix, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = 0
    for f, img in enumerate(frames(c)):
        im = c.finish(img, f)
        p.stdin.write(im.tobytes())
        if f in pick:
            im.save(os.path.join(a.stills, f"{f:03d}.png"))
        n += 1
    p.stdin.close()
    p.wait()
    print(f"[cut] {n} frames, {n / plan.FPS:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()
