"""SIDE BY SIDE: each side of the finished model next to the real photo of that same side, judged the way a buyer
compares a product shot with the real thing - one side at a time, at full size, twice (the second time with the
pictures swapped), and a side passes only when both looks pass.

    j = judge.sides(cid, renders, dossier, use, route)    # renders: {side: png} from measure.py
    j -> {"pass", "faces": {side: {"pass", "problems": [...]}}, "failed": [...], "problems": [...]}

A side whose plan uses a sister product's photo is judged knowing which parts were swapped (those may differ). A side
with no photo at all is judged on its plan's list of printed elements and its print quality only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

Q = """[side] {pics} The product: {product}. This is its {face} side (a round label is shown
turned four ways in a 2 x 2 grid - the real photo may show any of those turns, or several items at different turns).
The model is shown twice: once with NO light (its print exactly as drawn - judge sharpness, layout and any glare or
shadow baked into the print on this one) and once under studio light (judge its materials on this one: metal, gloss,
matte; a highlight or shading that follows the shape there is light, not a fault).
{ref_note}
What must be printed on this side (from the item's dossier): {must}
The real photo may show things that are NOT part of the item: a hang tag or price sticker, a hand, a stand, a box,
a background, other items, a watermark. The model must NOT have those, and missing them is never a fault.
Compare them as a buyer would. Answer ONLY JSON:
{{"same_layout": true if the model's side is laid out like the real one (same elements in the same places),
 "all_elements": true if every listed element is on the model's side and legible,
 "missing": ["listed elements not on the model's side, or not legible"],
 "print_ok": true if the model's print is sharp and clean - not blurry, smeared, stretched, cut off, mirrored,
   rotated wrong, and with no room light, glare or shadow baked into it,
 "problems": ["short and specific"],
 "pass": true only if all of the above are true}}"""


def _ask(use, text, images):
    import vet as V
    return V.ask(use, text, images, think=True, side=1600) or {}


def _strip(pngs, like, name="label_all_turns.png"):
    """Several pictures in one (the four turns of a round label; the real photos of its sides): four go in a 2 x 2
    grid, not a 1 x 4 strip, so each keeps its detail once the picture is sized for the brain (a 1 x 4 strip at
    1600 px left each turn 400 px wide - 'label text soft / low-resolution', 2026-10-04)."""
    if not pngs:
        return None
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in pngs]
    h = max(i.height for i in ims)
    ims = [i.resize((max(1, int(i.width * h / i.height)), h)) for i in ims]
    cols = 2 if len(ims) == 4 else len(ims)
    w = max(i.width for i in ims)
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (w * cols, h * rows), (255, 0, 255))
    for k, i in enumerate(ims):
        out.paste(i, ((k % cols) * w, (k // cols) * h))
    p = os.path.join(os.path.dirname(like) or ".", name)
    out.save(p)
    return p


def sides(cid, renders, dos, use, route, product="", log=print, lit=None):
    """Every side of the model next to the real photo of that side, judged twice (two picture orders). renders =
    the unlit pictures (print exactly as drawn); lit = the same sides under studio light (materials)."""
    faces = dos.get("faces") or {}
    lit = lit or {}
    out, failed, problems = {}, [], []
    if not use:
        return {"pass": False, "faces": {}, "failed": ["sides"], "problems": ["sides: no AI to judge the sides"]}
    jobs = []                                             # every look at every side, asked several at a time
    for face, e in faces.items():                         # when the brain server allows it
        if route == "round" and face == "label":              # a label wraps all the way round: all four turns,
            turns = ("label_0", "label_90", "label_180", "label_270")   # so it matches the photo's turn, whichever
            model = _strip([renders[n] for n in turns if n in renders], renders.get("label_0", ""))
            model_lit = _strip([lit[n] for n in turns if n in lit], lit.get("label_0", ""), "label_all_turns_lit.png") \
                if any(n in lit for n in turns) else None
        else:
            model, model_lit = renders.get(face), lit.get(face)
        if not model:
            continue
        must = "; ".join(f"{m.get('what')}" + (f" \"{str(m.get('text'))[:60]}\"" if m.get("text") else "")
                         for m in e.get("must_show", [])) or "nothing listed"
        ref = e.get("photo") if e.get("photo") and os.path.exists(e.get("photo")) else None
        wrap_refs = [ref] + [a for a in (e.get("alternates") or [])[:2] if a and os.path.exists(a)] if ref else []
        if route == "round" and face == "label" and len(wrap_refs) > 1:
            # a wrapped label: the real photos of this item from its different sides, side by side - the model's
            # four turns are judged against all of them, not against the one side the pick happens to show
            ref = _strip(wrap_refs, model, "label_real_sides.png")
        if e.get("source") == "template_photo":
            ref_note = ("The real photo is of a SISTER product (" + str(e.get("product_shown", "")) + "); these parts "
                        "differ on ours and must show OUR values instead: " + ", ".join(e.get("swap", [])) + ".")
        elif ref and route == "round" and face == "label" and len(wrap_refs) > 1:
            ref_note = ("The real photos (side by side) show this exact item from different sides; the label wraps all "
                        "the way round, so each part of it appears in at least one of them.")
        elif ref:
            ref_note = "The real photo shows this exact item."
        else:
            ref_note = "There is no real photo of this side; judge the model's side on the list and the print only."
            try:                                          # what this kind of thing normally has there (the kit)
                import kits
                typ = kits.typical(kits.get(dos.get("family_lib") or ""), face)
                if typ:
                    ref_note += " On this kind of item this side normally is: " + "; ".join(typ) + "."
            except Exception:
                pass
        shown = [model] + ([model_lit] if model_lit else [])
        for order in ((shown, ref), (ref, shown)) if ref else ((shown, None),):
            imgs, names = [], []
            for x in order:
                if x is None:
                    continue
                if isinstance(x, list):
                    imgs += x
                    names.append(f"picture {len(imgs) - len(x) + 1} is the 3D model's side with no light" +
                                 (f" and picture {len(imgs)} the same side under studio light" if len(x) > 1 else ""))
                else:
                    imgs.append(x)
                    names.append(f"picture {len(imgs)} is the real photo")
            pics = "; ".join(names).capitalize() + "." + ("" if ref else " There is no real photo.")
            jobs.append((face, Q.format(pics=pics, product=product, face=face, ref_note=ref_note, must=must), imgs))
    import vet as V
    answers = V.parallel(lambda j: _ask(use, j[1], j[2]), jobs)
    by_face = {}
    for (face, _, _), v in zip(jobs, answers):
        if isinstance(v, Exception) or not isinstance(v, dict):
            v = {"pass": False, "problems": [f"could not judge: {v}"]}
        by_face.setdefault(face, []).append(v)
    for face, verdicts in by_face.items():
        ok = all(v.get("pass") is True for v in verdicts)
        probs = []
        for v in verdicts:
            for p in (v.get("problems") or []) + [f"missing: {m}" for m in (v.get("missing") or [])]:
                if p and p not in probs:
                    probs.append(str(p)[:200])
        out[face] = {"pass": ok, "problems": probs[:6], "looks": len(verdicts), "agreed": len({bool(v.get("pass"))
                                                                                             for v in verdicts}) == 1}
        if not ok:
            failed.append(f"side_{face}")
            problems.append(f"side_{face}: " + ("; ".join(probs[:3]) or "the two looks disagreed"))
    if not out:                                             # nothing judged is never a pass
        return {"pass": False, "faces": {}, "failed": ["sides"],
                "problems": ["sides: no side could be compared (the dossier has no sides, or the model no pictures)"]}
    return {"pass": not failed, "faces": out, "failed": failed, "problems": problems}
