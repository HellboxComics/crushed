"""Strips from several photos are placed on the label by MATCHING FEATURES, OpenCV's documented way (SIFT, ratio
test, RANSAC) - never by a guessed half-turn or a guessed height (2026-10-05 17:34: 'the real label' was a collage
of strips at guessed places; every build failed for duplicates). A strip that shares nothing with the label so far
is left out, not guessed in."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
import skin  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


rng = np.random.default_rng(3)
H, W = 512, 1024
# a label with print on it: bands of color with many small marks (letters, boxes) - features a matcher can find
G = np.zeros((H, W, 3))
G[:, :, 0] = 0.75; G[:, :, 1] = 0.45; G[:, :, 2] = 0.2                  # copper
G[H // 3:] = 0.08                                                        # black body
for _ in range(260):
    y, x = rng.integers(0, H - 24), rng.integers(0, W - 40)
    h, w = rng.integers(6, 22), rng.integers(8, 40)
    G[y:y + h, x:x + w] = rng.random(3)
G = np.clip(G + rng.normal(0, 0.01, G.shape), 0, 1)
col = lambda a, b: (np.arange(W)[None, :] >= a * W) & (np.arange(W)[None, :] < b * W)


def strip(a, b, roll=0, down=0, rows=(0, 1)):
    """What one photo shows: columns a..b of the truth (wrapping), rows r0..r1 - presented at a WRONG place (rolled
    around by `roll`, shifted along by `down`), as an unregistered unroll would."""
    m = np.zeros((H, W), bool)
    r0, r1 = int(rows[0] * H), int(rows[1] * H)
    if a < b:
        m[r0:r1] = col(a, b)[0]
    else:
        m[r0:r1] = (col(a, 1) | col(0, b))[0]
    l = np.where(m[..., None], G, 0)
    w = m.astype(float)
    l, w = np.roll(l, roll, axis=1), np.roll(w, roll, axis=1)
    l, w = np.roll(l, down, axis=0), np.roll(w, down, axis=0)
    return l, w


front = strip(0.2, 0.6)
side = strip(0.45, 0.85, roll=-300, down=37)              # overlaps the front by 15% of the way around
far = strip(0.65, 0.95, roll=120)                         # shares nothing with the front
noise = (rng.random((H, W, 3)), col(0.1, 0.5)[0].astype(float) * np.ones((H, 1)))   # not this label at all
placed = skin.register_strips(front, [far, noise, side], W, log=print)
check(len(placed) == 3, f"of three strips the two from this label are placed - the far one through the side one on a second pass - and the noise is left out ({len(placed) - 1} placed)")
pl, pw = placed[1]
seen = pw > 0.5
err = np.abs(pl[seen] - G[seen]).mean()
check(seen.sum() > 0.3 * side[1].sum() and err < 0.06, f"the placed strip lands where the truth is (mean error {err:.3f} over {seen.sum()} px)")
check(seen[:, int(0.7 * W):int(0.83 * W)].mean() > 0.8, "it extends the label past the front's edge, at the right place")

# a chain: the far strip can be placed once the side strip (which it overlaps) is in
placed2 = skin.register_strips(front, [side, far], W, log=print)
check(len(placed2) == 3, f"a strip that overlaps a placed strip (not the front) is placed through it, like a panorama ({len(placed2) - 1} placed)")
pl, pw = placed2[2]; seen = pw > 0.5
check(np.abs(pl[seen] - G[seen]).mean() < 0.06, "and lands right")

# the label wraps around: a strip across the seam
front2 = strip(0.8, 0.2)
side2 = strip(0.1, 0.5, roll=400, down=-20)
placed3 = skin.register_strips(front2, [side2], W, log=print)
check(len(placed3) == 2, "a strip is placed across the wrap-around seam")
pl, pw = placed3[1]; seen = pw > 0.5
check(np.abs(pl[seen] - G[seen]).mean() < 0.06, "and lands right there too")

# a close-up (part of the length) is placed at the right height by matching, not by a guess
close = strip(0.3, 0.7, roll=-150, down=60, rows=(0.0, 0.45))
placed4 = skin.register_strips(front, [close], W, log=print)
pl, pw = placed4[1]; seen = pw > 0.5
check(len(placed4) == 2 and np.abs(pl[seen] - G[seen]).mean() < 0.06 and seen[int(0.3 * H):int(0.4 * H), int(0.62 * W):int(0.68 * W)].mean() > 0.8,
      "a close-up of one end lands at the end it shows - by matching")
print(f"ALL {ok} PASS")
