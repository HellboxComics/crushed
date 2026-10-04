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


TIEBREAK = """[side] {pics} The product: {product}. This is its {face} side. Two careful looks at these same pictures
disagreed: one passed the model's side, the other named these problems: {problems}
Check each named problem against the pictures, slowly. A problem counts only if you can point to it in the
pictures (where, what). The model is shown with no light (its print) and under studio light (its materials); a
highlight that follows the shape is light, not a fault. Things in the photo that are not part of the item (a hand,
a tag, a background) are never a fault. Answer ONLY JSON:
{{"confirmed": ["each named problem that is really there, with where you see it"],
 "not_there": ["each named problem you cannot find"],
 "pass": true only if no named problem is really there}}"""


def _ask(use, text, images):
    import vet as V
    return V.ask(use, text, images, think=True, side=1600) or {}


def _side_crop(photo, box, like, name):
    """The part of a photo that shows one side (the dossier's box for that side, with a margin), saved next to the
    model's pictures. None when there is no box or it covers nearly the whole photo."""
    if not box or len(box) != 4:
        return None
    try:
        from PIL import Image
        im = Image.open(photo).convert("RGB")
        W, H = im.size
        x0, y0, x1, y1 = [max(0.0, min(1.0, float(b))) for b in box]
        if x1 - x0 >= 0.85 and y1 - y0 >= 0.85:
            return None
        mx, my = 0.15 * (x1 - x0), 0.15 * (y1 - y0)
        crop = im.crop((int(max(0, x0 - mx) * W), int(max(0, y0 - my) * H), int(min(1, x1 + mx) * W), int(min(1, y1 + my) * H)))
        if min(crop.size) < 40:
            return None
        p = os.path.join(os.path.dirname(like) or ".", name)
        crop.save(p)
        return p
    except Exception:
        return None


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


QUESTION_VERSION = 3        # bump when Q / TIEBREAK / the pictures shown change (a kept pass is keyed on it)


def sides(cid, renders, dos, use, route, product="", log=print, lit=None):
    """Every side of the model next to the real photo of that side, judged twice (two picture orders). renders =
    the unlit pictures (print exactly as drawn); lit = the same sides under studio light (materials).
    A side whose pictures (model unlit + lit, the real photo) and list are byte-for-byte what they were when it
    PASSED stays passed - kept, not asked again (Cody: keep what is good, redo what is bad)."""
    import kept
    faces = dos.get("faces") or {}
    lit = lit or {}
    kept_faces = {}
    out, failed, problems = {}, [], []
    if not use:
        return {"pass": False, "faces": {}, "failed": ["sides"], "problems": ["sides: no AI to judge the sides"]}
    jobs, keys, shown_of = [], {}, {}                     # every look at every side, asked several at a time
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
        if ref and not (route == "round" and face == "label"):
            # the judge gets THIS SIDE of the photo, not the whole photo: a battery's bottom was judged against the
            # whole picture of the battery lying down ("the model is a disc, not the cylindrical side", 2026-10-04)
            ref = _side_crop(ref, (e.get("view") or {}).get("box"), model, f"ref_{face}.png") or ref
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
        kk = kept.key("judge-side", [], cid, face, must, ref_note, use, QUESTION_VERSION)
        had = kept.get_pictures("judge-side", kk, shown + [ref])    # the same pictures, within render noise
        if had and had.get("pass"):
            kept_faces[face] = dict(had, kept=True)
            log(f"[judge] {cid} {face}: the same pictures as when it passed - kept, not judged again")
            continue
        keys[face] = kk
        shown_of[face] = shown + [ref]
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
    pics_of = {j[0]: (j[1], j[2]) for j in jobs}            # the first job's prompt pictures per face (model-first)
    for face, verdicts in by_face.items():
        ok = all(v.get("pass") is True for v in verdicts)
        probs = []
        for v in verdicts:
            for p in (v.get("problems") or []) + [f"missing: {m}" for m in (v.get("missing") or [])]:
                if p and p not in probs:
                    probs.append(str(p)[:200])
        agreed = len({bool(v.get("pass")) for v in verdicts}) == 1
        tie = None
        if not ok and not agreed and probs and face in pics_of:
            # the two looks disagree: the judge is a brain and one look can be wrong either way - a third look checks
            # the named problems one by one against the pictures (2026-10-04: the same unchanged label passed twice
            # and failed the third build on one look)
            q0, imgs = pics_of[face]
            pics = q0.split(" The product:")[0].replace("[side] ", "")
            try:
                tie = _ask(use, TIEBREAK.format(pics=pics, product=product, face=face, problems="; ".join(probs[:6])), imgs)
            except Exception as e:
                tie = {"pass": False, "confirmed": [f"could not take the third look: {e}"]}
            confirmed = [str(x)[:200] for x in (tie.get("confirmed") or [])]
            ok = tie.get("pass") is True and not confirmed
            log(f"[judge] {cid} {face}: the two looks disagreed - a third look " +
                ("found none of the named problems: it passes" if ok else f"confirmed: {'; '.join(confirmed)[:300]}"))
            if not ok:
                probs = confirmed or probs
        out[face] = {"pass": ok, "problems": probs[:6], "looks": len(verdicts) + (1 if tie is not None else 0),
                     "agreed": agreed, **({"third_look": tie} if tie is not None else {})}
        if ok and face in keys:                             # a pass is kept for the next build of the same pictures
            kept.put_pictures("judge-side", keys[face], shown_of[face], out[face], note=f"{cid} {face}")
        if not ok:
            failed.append(f"side_{face}")
            problems.append(f"side_{face}: " + ("; ".join(probs[:3]) or "the two looks disagreed"))
    for face, v in kept_faces.items():                      # the sides kept from a pass with the same pictures
        out[face] = v
    if not out:                                             # nothing judged is never a pass
        return {"pass": False, "faces": {}, "failed": ["sides"],
                "problems": ["sides: no side could be compared (the dossier has no sides, or the model no pictures)"]}
    return {"pass": not failed, "faces": out, "failed": failed, "problems": problems}
