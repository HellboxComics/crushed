"""The hero film's sound, mixed to the frame from public-domain (CC0) recordings in film/audio/.

    python3 film/sound.py            -> film/audio/hero_mix.wav (cut.py lays it under the picture)

The bulb buzz follows the same flicker curve cut.py uses for the picture, and every montage cut gets its own
crunch, so sound and picture can't drift apart. Trailer shape: dread -> a hit on each line -> a dead-silent
beat -> lights slam on -> a riser under the montage -> black silence -> the slam on the title.
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan  # noqa: E402
from cut import bulb, ffmpeg  # noqa: E402

SR = 48000
AUD = os.path.join(HERE, "audio")
LEN = 576 / plan.FPS


def load(name):
    raw = subprocess.run([ffmpeg(), "-loglevel", "error", "-i", os.path.join(AUD, name + ".mp3"), "-f", "f32le",
                          "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    return a / (np.abs(a).max() + 1e-9)                      # every sound starts at full scale; gains set the mix


def sec(frame):
    return frame / plan.FPS


class Mix:
    def __init__(self):
        self.out = np.zeros((int(LEN * SR), 2), np.float32)
        self.cache = {}

    def snd(self, name):
        if name not in self.cache:
            self.cache[name] = load(name)
        return self.cache[name]

    def put(self, name, at, gain_db=0.0, src=0.0, length=None, fade_in=0.005, fade_out=0.02, env=None):
        """Lay `name` (from `src` seconds into it) at `at` seconds, `gain_db` loud, optionally cut to `length`."""
        a = self.snd(name)[int(src * SR):]
        if length is not None:
            a = a[: int(length * SR)]
        a = a.copy()
        n = len(a)
        if not n:
            return
        fi, fo = max(1, int(fade_in * SR)), max(1, int(fade_out * SR))
        a[: min(fi, n)] *= np.linspace(0, 1, min(fi, n))[:, None]
        a[-min(fo, n):] *= np.linspace(1, 0, min(fo, n))[:, None]
        if env is not None:
            a *= env(np.arange(n) / SR)[:, None]
        i = int(at * SR)
        j = min(len(self.out), i + n)
        if j > i:
            self.out[i:j] += a[: j - i] * 10 ** (gain_db / 20)

    def master(self):
        x = np.tanh(self.out * 1.4) / np.tanh(1.4)             # soft clip: hits stay punchy without cracking
        tail = int(0.4 * SR)
        x[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 2
        return x / (np.abs(x).max() + 1e-9) * 10 ** (-1 / 20)  # peak at -1 dB


def build():
    m = Mix()
    # ---- 0:00-0:09 dread: a low room tone, a drone creeping in, and the dying bulb
    m.put("terror_ambience", 0.0, -20, src=8.0, length=8.55, fade_in=1.2, fade_out=0.35)
    m.put("braams_drone", 2.5, -24, src=14.0, length=6.05, fade_in=2.5, fade_out=0.35)
    fl = bulb(72)
    t_fl = np.arange(len(fl)) / plan.FPS

    def buzz(t):
        return np.interp(t, t_fl, np.clip(fl, 0, 1.3)) ** 1.5
    m.put("lights_flicker_on", 0.0, -6, src=3.0, length=3.0, fade_out=0.04, env=buzz)
    for f in range(1, 72):                                     # a filament tick each time the bulb catches again
        if fl[f - 1] < 0.4 <= fl[f]:
            m.put("light_switch", sec(f) - 0.01, -14, src=2.11, length=0.18)
    # ---- 0:03-0:09 a low hit under each line, a braam under the last
    for a, b, text, size, col in plan.CARDS:
        if col == plan.LIME:
            m.put("braam", sec(a) - 0.03, -4, length=8.55 - sec(a) + 0.03, fade_out=0.12)
        else:
            m.put("sub_a", sec(a) - 0.5, -18, src=0.0, length=1.2, fade_in=0.4, fade_out=0.4)
    # 0:08.6 everything drops out: one beat of dead air before the lights
    # ---- 0:09 lights slam on
    m.put("light_switch", 9.0 - 0.02, -2, src=2.11, length=0.3)
    m.put("hard_hit", 9.0, -1, length=4.0, fade_out=1.0)
    m.put("big_boom", 9.0, -6, length=3.5, fade_out=1.0)
    m.put("scary_violins", 9.15, -12, src=1.0, length=5.0, fade_in=0.4, fade_out=0.5)
    m.put("braams_drone", 9.4, -18, src=25.0, length=4.8, fade_in=1.0, fade_out=0.6)
    # ---- 0:11.7-0:20 a riser that climbs under the reveal and the whole montage, cut dead at 0:20
    m.put("riser_hit", 20.0 - 8.3, 3, src=0.0, length=8.3, fade_in=1.5, fade_out=0.03)
    # ---- 0:14-0:20 a crunch on every cut, louder as they come faster
    f = 336
    crunch = [("crushed_can", 0.84), ("crushing_can2", 0.34), ("metal_smash", 0.04)]
    holds = plan.montage_holds()
    for k, hold in enumerate(holds):
        name, peak = crunch[k % 3]
        m.put(name, sec(f) - 0.01, -8 + 8 * k / (len(holds) - 1), src=peak, length=max(0.18, hold / plan.FPS + 0.08),
              fade_out=0.05)
        if k % 4 == 0:
            m.put("sub_a", sec(f), -14, src=1.0, length=0.35, fade_out=0.15)
        f += hold
    # ---- 0:20 black. silence. 0:20.25 the title lands like a press closing
    t = sec(480 + plan.END["black"])
    m.put("hard_hit", t, 0, length=5.0, fade_out=2.0)
    m.put("big_boom", t, -2, length=3.75, fade_out=1.5)
    m.put("hydraulic_press", t - 0.02, -4)
    m.put("metal_smash", t - 0.01, -6, src=0.04, length=0.5, fade_out=0.2)
    # ---- 0:22.5 the last line, over the dying tail
    m.put("sub_a", sec(480 + plan.END["black"] + plan.END["title"]) - 0.3, -12, length=1.5, fade_in=0.3, fade_out=0.6)
    return m.master()


def main():
    x = build()
    out = os.path.join(AUD, "hero_mix.wav")
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    subprocess.run([ffmpeg(), "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", out],
                   input=pcm.tobytes(), check=True)
    print(f"[sound] {len(x) / SR:.1f} s -> {out}")


if __name__ == "__main__":
    main()
