"""LABEL TEST: the same label made three ways on this Mac, side by side, each scored by the judge reading its
words back and shown on the finished 3D object - so the method is chosen from proof, not a guess.

  A  real photo pixels; gaps filled by carrying the real colors across (no AI)
  B  A, then Qwen-Image-Edit removes glare (an edit), kept only if every word survives
  C  Qwen-Image-Edit redraws the whole label clean, with the EXACT words (read off the real photo) spelled out
     for it; the judge reads them back

    .venv/bin/python library/lab.py duracell_coppertop_aa_1998
Results: ~/crushed-render/remaster/lab/<item>/lab.jpg and on the phone page.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run  # noqa: E402  (paths, helpers)
import skin  # noqa: E402
import metal  # noqa: E402
import turnaround as T  # noqa: E402
import vet as V  # noqa: E402

READ = 'Read every word and number printed in this picture, exactly as spelled. Answer ONLY JSON: {"words": ["..."]}'


def words(png, judge):
    try:
        return [w for w in V.ask(judge, READ, [png], think=False).get("words", []) if isinstance(w, str)]
    except Exception as e:
        print("could not read words:", e)
        return []


def score(got, truth):
    g = [w.lower() for w in got]
    t = [w.lower() for w in truth]
    kept = sum(1 for w in t if w in g) / max(len(t), 1)
    fake = sum(1 for w in g if w not in t) / max(len(g), 1)
    return round(kept, 2), round(fake, 2)


def build_and_render(cid, label_png, spec_path, out):
    base, mr = metal.metal_maps(Image.open(label_png).convert("RGB"))
    b, m = os.path.join(out, "b.png"), os.path.join(out, "mr.png")
    base.save(b)
    mr.save(m)
    run.run_blender("lathe.py", spec_path, out, b, m)
    spec = json.load(open(spec_path))
    glb = os.path.join(out, spec["id"] + ".glb")
    subprocess.run([sys.executable, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(out, "v.png"), "0,180"],
                   check=True, capture_output=True)
    return [os.path.join(out, "v_000.png"), os.path.join(out, "v_180.png")]


def main(cid):
    d = os.path.join(run.OUT, cid)
    lab_dir = os.path.join(run.WORK, "lab", cid)
    os.makedirs(lab_dir, exist_ok=True)
    cand = json.load(open(os.path.join(d, "candidates.json")))["files"]
    pick = json.load(open(os.path.expanduser("~/.hellbox/picks.json")))[cid]["pick"]
    picked = cand[int(pick) - 1]
    fam = json.load(open(os.path.join(HERE, "families.json"))).get(cid, {})
    spec_path = os.path.join(HERE, "shapes", "specs", fam["shape"] + ".json")
    spec = json.load(open(spec_path))
    along, around = skin.label_size(spec)
    reads = spec.get("label_reads", "around")
    product = json.load(open(os.path.join(run.WORK, "cards", cid + ".json")))["product"]
    judge = V.model()

    # the truth: the words actually printed, read off the real photo's unrolled label
    run.make_room("judging")
    truth = []
    for i, p in enumerate(skin.sides(picked, reads)):
        pp = os.path.join(lab_dir, f"side{i + 1}.png")
        p.save(pp)
        truth += [w for w in words(pp, judge) if w not in truth]
    print("[lab] words on the real label:", truth)

    lab, cov = skin.compose([picked], along, around)
    gaps = cov < 0.05
    A = skin.continue_bands(lab, gaps)
    a_png = os.path.join(lab_dir, "A.png")
    Image.fromarray((np.clip(A, 0, 1) * 255).astype(np.uint8)).save(a_png)

    run.make_room("drawing")
    b_png = os.path.join(lab_dir, "B.png")
    skin.cleanup(product, a_png, b_png, reads)
    Image.open(b_png).convert("RGB").resize(Image.open(a_png).size, Image.LANCZOS).save(b_png)

    c_png = os.path.join(lab_dir, "C.png")
    ref = Image.open(a_png).convert("RGB")
    if reads == "along":
        ref = ref.rotate(90, expand=True)
    w, h = skin.canvas(ref.width, ref.height)
    ref_p = os.path.join(lab_dir, "C_ref.png")
    ref.resize((w, h), Image.LANCZOS).save(ref_p)
    said = ", ".join(f'"{t}"' for t in truth)
    prompt = ("Picture 1 is a flat printed label made from a real photo (blurry, with glare, some areas smeared). "
              "Redraw it as the clean original print-ready label artwork: the same layout, colors, shapes and "
              "graphics in the same places, perfectly flat and sharp, no glare, no smears. The ONLY words printed on "
              f"it are exactly these, spelled exactly like this: {said}. Write each of them where it is in picture 1. "
              "Do not write any other words, letters or numbers anywhere. The product: ")
    T.draw_from_photos(product, [ref_p], c_png, width=w, height=h, prefix=prompt, seed=21)
    got = Image.open(c_png).convert("RGB")
    if reads == "along":
        got = got.rotate(-90, expand=True)
    got.resize(Image.open(a_png).size, Image.LANCZOS).save(c_png)

    run.make_room("judging")
    rows = []
    for name, png in (("A real pixels, no AI", a_png), ("B real + AI glare edit", b_png), ("C AI redraw, exact words", c_png)):
        k, f = score(words(png, judge), truth)
        views = build_and_render(cid, png, spec_path, os.path.join(lab_dir, name[0]))
        rows.append((name, png, views, k, f))
        print(f"[lab] {name}: words right {k:.0%}, made-up words {f:.0%}")
    sheet = Image.new("RGB", (3 * 520, 760), "white")
    dr = ImageDraw.Draw(sheet)
    for i, (name, png, views, k, f) in enumerate(rows):
        x = i * 520
        lab_im = Image.open(png).convert("RGB")
        if reads == "along":
            lab_im = lab_im.rotate(90, expand=True)
        lab_im.thumbnail((500, 330))
        sheet.paste(lab_im, (x + 10, 40))
        for j, v in enumerate(views):
            sheet.paste(Image.open(v).convert("RGB").resize((240, 320)), (x + 10 + j * 250, 400))
        dr.text((x + 10, 8), f"{name}   words right {k:.0%}   made-up {f:.0%}", fill="black")
    out = os.path.join(lab_dir, "lab.jpg")
    sheet.save(out, quality=90)
    shutil.copy(out, os.path.join(run.WORK, "lab.jpg"))
    json.dump({"truth": truth, "results": [{"method": r[0], "words_right": r[3], "made_up": r[4]} for r in rows]},
              open(os.path.join(lab_dir, "lab.json"), "w"), indent=1)
    try:
        import askfirst
        askfirst._send_photo(out, f"Label test for {product}: A real pixels, B + AI glare edit, C AI redraw with the "
                                  "exact words. Claude will read the scores; nothing to tap.", {"inline_keyboard": []})
    except Exception:
        pass
    print("[lab] done:", out)


if __name__ == "__main__":
    import fcntl
    lock = open(os.path.join(run.WORK, "run.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)      # the same one-at-a-time lock as the asset runs
    except OSError:
        sys.exit("an asset run is going - stop it first")
    main(sys.argv[1])
