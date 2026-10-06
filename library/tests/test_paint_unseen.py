"""The side no photo shows is inferred by Hunyuan3D-Paint (installed and proven on the Mac) painting the exact label
shell in its own UV layout; the real stitched pixels go over it wherever a photo saw the label (2026-10-05 20:47).
A failure keeps the band-filled label and says so on the review sheet - nothing stops."""
import json
import os
import sys
import tempfile
import types

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import run  # noqa: E402
import families  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


json.dump({"ok": True, "painted": True}, open(os.path.join(families.WORK, "hunyuan_proven.json"), "w"))
d = os.path.join(W, "library", "cell"); tex = os.path.join(d, "texture"); mdir = os.path.join(d, "model")
os.makedirs(tex); os.makedirs(mdir)
spec = {"id": "cell_spec"}
open(os.path.join(mdir, "cell_spec.glb"), "wb").write(b"glb")
# the label in UV orientation (reads == "along": the texture was rotated -90): 400 wide x 900 tall
H, Wd = 900, 400
real = np.zeros((H, Wd, 3), np.uint8); real[:] = (200, 30, 30)                 # the real photo: red
Image.fromarray(real).save(os.path.join(d, "label.png"))
mr = np.zeros((H, Wd, 3), np.uint8); mr[..., 1] = 115; Image.fromarray(mr).save(os.path.join(d, "label_mr.png"))
# what the photos saw, in the label's reading orientation (900 wide x 400 tall), the middle third of the way around
cov = np.zeros((400, 900), np.uint8); cov[130:270, :] = int(0.2 * 255)
Image.fromarray(cov).save(os.path.join(tex, "real_seen.png"))
json.dump({"file": "/x/p.jpg", "mask": "/x/p_mask.png"}, open(os.path.join(tex, "label_source.json"), "w"))

calls = {}
run.reference = lambda f, out, upright=False: os.path.join(out, "ref.png")
run.make_room = lambda *a, **k: None
run.status = lambda *a, **k: None
run.boundary = lambda *a, **k: None
run.say = lambda *a, **k: None


def fake_paint(ref, out, bare=None, part=None):
    calls.update(ref=ref, bare=bare, part=part)
    # the Apple-chip build writes paint_pbr.png: one atlas, the label on the TOP half (atlas.json says so); the
    # bottom half (the other parts) is painted blue here so a wrong crop would show
    atlas = np.full((512, 256, 3), (30, 30, 200), np.uint8); atlas[:256] = (30, 200, 30)                    # green = label
    Image.fromarray(atlas).save(os.path.join(out, "paint_pbr.png"))
    json.dump({"atlas": {"label": [0.0, 0.5, 1.0, 1.0], "steel": [0.0, 0.0, 1.0, 0.5]}, "main": "label"}, open(os.path.join(out, "atlas.json"), "w"))
    Image.fromarray(np.full((512, 256), 255, np.uint8)).save(os.path.join(out, "textured_metallic.jpg"))
    Image.fromarray(np.full((512, 256), 60, np.uint8)).save(os.path.join(out, "textured_roughness.jpg"))
    return os.path.join(out, "textured.glb")
run.hunyuan_paint = fake_paint

changed = run.paint_unseen("cell", d, mdir, spec, tex, "along")
check(changed is True, "the label changed, so Blender runs again")
check(calls.get("part") == "label" and calls.get("bare", "").endswith("cell_spec.glb"), f"Hunyuan painted the model's LABEL part in its own UV layout ({calls})")
lab = np.asarray(Image.open(os.path.join(d, "label.png")).convert("RGB")).astype(int)
# after the -90 rotation the seen band (rows 130-270 of 400) becomes columns of the 400-wide map
seen_cols = lab[:, 150:250]; unseen_cols = lab[:, 0:60]
check(seen_cols[..., 0].mean() > 180 and seen_cols[..., 1].mean() < 60, f"where a photo saw the label the real pixels stay (red: {seen_cols.mean((0, 1)).round()})")
check(unseen_cols[..., 1].mean() > 180 and unseen_cols[..., 0].mean() < 60, f"where no photo saw it the inferred paint shows (green: {unseen_cols.mean((0, 1)).round()})")
m = np.asarray(Image.open(os.path.join(d, "label_mr.png")).convert("RGB")).astype(int)
check(m[:, 0:60, 2].mean() > 200 and m[:, 150:250, 2].mean() < 30, "the metal/roughness map follows the same split (Hunyuan's where inferred, ours where seen)")
R = json.load(open(os.path.join(d, "review.json")))["steps"]
st = [s for s in R if s["step"].startswith("the unseen side")]
check(st and all(c["ok"] is True for c in st[-1]["checks"]) and "inferred" in st[-1]["checks"][0]["detail"], f"the review sheet says so: {st[-1]['checks'][0]['detail'] if st else None}")
check(os.path.exists(os.path.join(tex, "label_painted.png")), "the painter's own map is kept for the page")

# a failure: the band-filled label stays, the sheet says why, nothing stops
Image.fromarray(real).save(os.path.join(d, "label.png"))
def boom(*a, **k):
    raise RuntimeError("the painter ran out of memory")
run.hunyuan_paint = boom
changed = run.paint_unseen("cell", d, mdir, spec, tex, "along")
lab2 = np.asarray(Image.open(os.path.join(d, "label.png")).convert("RGB"))
check(changed is False and np.array_equal(lab2, real), "when the painter fails the label is left as it was")
R = json.load(open(os.path.join(d, "review.json")))["steps"]
last = [s for s in R if s["step"].startswith("the unseen side")][-1]
check(last["checks"][0]["ok"] is None and "ran out of memory" in last["checks"][0]["detail"], "and the sheet says why")

# not proven on this Mac: skipped, said
json.dump({"ok": False}, open(os.path.join(families.WORK, "hunyuan_proven.json"), "w"))
changed = run.paint_unseen("cell", d, mdir, spec, tex, "along")
check(changed is False, "with no proof the painter works on this Mac, the step is skipped and said")
print(f"ALL {ok} PASS")
