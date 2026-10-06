"""The label texture IS the real photo (stitched, de-glared, sharpened) - the documented way photo-scanning tools
texture a model - never a redraw from a word list (2026-10-05 20:33, after a week lost to that redraw)."""
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import run  # noqa: E402
import skin  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


tex = os.path.join(W, "tex"); os.makedirs(tex)
H, Wd = 400, 900
a = np.zeros((H, Wd, 3), np.uint8); a[:, :int(0.38 * Wd)] = (200, 125, 70); a[:, int(0.38 * Wd):] = (18, 18, 18)
a[180:220, 500:800] = (240, 240, 240)                                   # a white word on the black body
real = os.path.join(tex, "real.png"); Image.fromarray(a).save(real)
cov = np.zeros((H, Wd), np.uint8); cov[int(0.3 * H):int(0.65 * H)] = int(0.2 * 255)
cover = os.path.join(tex, "real_seen.png"); Image.fromarray(cov).save(cover)

# no drawing room and no upscaler here: both are skipped and SAID so; the untouched photo is the label
def boom(*a, **k):
    raise RuntimeError("no drawing room in this test")
skin.cleanup = boom
import turnaround as T  # noqa: E402
T.upscale = boom
png, mr, notes = run.photo_label("X AA cell", real, cover, tex, "judge", "along", log=lambda *a: None)
check(os.path.exists(png) and np.array_equal(np.asarray(Image.open(png).convert("RGB")), a), "the label is the real photo, pixel for pixel, when nothing can be cleaned or sharpened")
check(notes.get("cleaned") is None and "skipped" in notes.get("clean_note", ""), f"the skipped clean-up is written down: {notes.get('clean_note')}")
check(notes.get("sharpened") is None and "skipped" in notes.get("sharp_note", ""), f"the skipped sharpening is written down: {notes.get('sharp_note')}")
m = np.asarray(Image.open(mr).convert("RGB"))
check(m[200, 100, 2] == 255 and m[200, 600, 2] == 0, "the metal map marks the measured copper band as metal and the black body as a printed sleeve")
check(notes.get("bands") == 2, f"two bands measured ({notes.get('bands_note')})")

# the clean-up, when it runs, is kept only if the judge reads the same words
def fake_clean(product, src, out, reads):
    Image.fromarray(np.clip(a.astype(int) + 10, 0, 255).astype(np.uint8)).save(out)
skin.cleanup = fake_clean
skin.same_words = lambda a_, b_, judge=None, log=print: True
png, mr, notes = run.photo_label("X AA cell", real, cover, tex, "judge", "along", log=lambda *a: None)
check(notes.get("cleaned") is True and np.asarray(Image.open(png))[0, 0, 0] == 210, "a clean-up that keeps the words is used")
skin.same_words = lambda a_, b_, judge=None, log=print: False
png, mr, notes = run.photo_label("X AA cell", real, cover, tex, "judge", "along", log=lambda *a: None)
check(notes.get("cleaned") is None and np.asarray(Image.open(png))[0, 0, 0] == 200, "a clean-up that changes the words is thrown away")

src = open(run.__file__).read()
check("LAY.make(" not in src, "nothing in run.py redraws the label from words any more")
print(f"ALL {ok} PASS")
