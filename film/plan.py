"""The crushed.buzz hero film: one place that says what happens when. 24 fps, 21:9 (OpenSea's homepage hero
is 3440 x 1440; Franky the Frog's is exactly that, 23 s, 24 fps). Both render.py and cut.py read this.

The shape is a teaser trailer squeezed into 24 seconds: calm and dark -> pressure -> a fast montage -> title
-> one last short beat (the "button"). It loops on the homepage, so it starts and ends on black.
"""
FPS = 24
W, H = 3440, 1440
LIME = (204, 255, 0)          # CCFF00
BONE = (233, 230, 223)        # the site's off-white
DIM = (125, 122, 116)


def _serials():
    import json
    import os
    m = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collection",
                                    "manifest.json")))
    return {r["traits"].get("One of One"): r["id"] for r in m["tokens"] if r["traits"].get("One of One", "None") != "None"}


SERIAL = _serials()
NAMES = {v: k for k, v in SERIAL.items()}
COUNT = len(SERIAL)
HERO = SERIAL["TRICK OR TREAT"]


# ---- the rendered shots. cam: (start, end) of (camera position, aim point, vertical field of view in degrees)
SHOTS = [
    # 0:00 cold open. A dying bulb finds the cube in the dark: candy wrappers, a pumpkin pail. Close, slow.
    dict(name="open_a", cube=HERO, frames=36, rig="dark",
         cam=(((-0.16, -0.40, 0.40), (-0.06, -0.02, 0.29), 15), ((0.02, -0.38, 0.38), (0.05, -0.02, 0.28), 14))),
    dict(name="open_b", cube=HERO, frames=36, rig="dark",
         cam=(((0.10, -0.44, 0.06), (0.02, -0.15, 0.12), 17), ((0.04, -0.42, 0.13), (-0.02, -0.15, 0.17), 16))),
    # 0:03 the words, over the cube as a black shape with an orange and purple edge
    dict(name="concept", cube=HERO, frames=144, rig="silhouette",
         cam=(((1.05, -1.75, 0.22), (0, 0, 0.17), 24), ((0.80, -1.33, 0.20), (0, 0, 0.17), 24))),
    # 0:09 lights on: the Halloween block, low and turning
    dict(name="reveal", cube=HERO, frames=120, rig="halloween", orbit=(-28, 52, 1.15, (0.09, 0.16)), shift=0.075,
         cam=(None, (0, 0, 0.16), 30)),
]

# ---- 0:14 the montage: the best of the rest, each held a little shorter than the one before
# picked by title, so a re-freeze that moves a one-of-one to another serial can't put the wrong cube in the film
MONTAGE_TITLES = ["SOLID GOLD", "CCFF00", "CONSOLE WARS", "MIXTAPE", "STILL ALIVE", "UNDER THE MATTRESS", "BE MINE",
                  "BASS BOOSTED", "LIGHT THE FUSE", "IT'S AWAKE", "Y2K", "LOW RES", "SPACE OPERA", "EGG HUNT",
                  "SLIMED", "BE KIND REWIND", "CLAY DAY", "STOP THE PRESSES"]
MONTAGE = [SERIAL[t] for t in MONTAGE_TITLES]


MONTAGE_FRAMES = 144


def montage_holds():
    """How many frames each montage cube stays up: 15 down to 3, always accelerating, summing to 144."""
    n = len(MONTAGE)
    raw = [15 * (3 / 15) ** (i / (n - 1)) for i in range(n)]
    k = MONTAGE_FRAMES / sum(raw)
    holds = [max(3, round(r * k)) for r in raw]
    i = 0
    while sum(holds) != MONTAGE_FRAMES:          # fix rounding without breaking "never slower than before"
        d = 1 if sum(holds) < MONTAGE_FRAMES else -1
        j = i % n
        if d > 0 or holds[j] > 3:
            holds[j] += d
            if holds != sorted(holds, reverse=True):
                holds[j] -= d
        i += 1
    return holds


# ---- the words. (first frame, last frame, text, size as a share of the frame height, color)
CARDS = [
    (82, 112, "EVERY CRAZE HAD A BUZZ.", 0.064, BONE),
    (118, 148, "THEN THE BUZZ WORE OFF.", 0.064, BONE),
    (154, 182, "THE STUFF DIDN'T.", 0.064, BONE),
    (188, 214, "SO WE CRUSHED IT.", 0.076, LIME),
]
END = dict(black=6, title=54, button=30, fade=6)   # 576 frames = 24.0 s in all
