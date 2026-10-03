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

Q = """[side] {first} and {second}. The product: {product}. This is its {face} side.
{ref_note}
What must be printed on this side (from the item's dossier): {must}
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
    return V.ask(use, text, images, think=True, side=1280) or {}


def sides(cid, renders, dos, use, route, product="", log=print):
    faces = dos.get("faces") or {}
    out, failed, problems = {}, [], []
    if not use:
        return {"pass": False, "faces": {}, "failed": ["sides"], "problems": ["sides: no AI to judge the sides"]}
    for face, e in faces.items():
        names = ["label_0"] if (route == "round" and face == "label") else [face]
        model = next((renders[n] for n in names if n in renders), None)
        if not model:
            continue
        must = "; ".join(f"{m.get('what')}" + (f" \"{str(m.get('text'))[:60]}\"" if m.get("text") else "")
                         for m in e.get("must_show", [])) or "nothing listed"
        ref = e.get("photo") if e.get("photo") and os.path.exists(e.get("photo")) else None
        if e.get("source") == "template_photo":
            ref_note = ("The real photo is of a SISTER product (" + str(e.get("product_shown", "")) + "); these parts "
                        "differ on ours and must show OUR values instead: " + ", ".join(e.get("swap", [])) + ".")
        elif ref:
            ref_note = "The real photo shows this exact item."
        else:
            ref_note = "There is no real photo of this side; judge the model's side on the list and the print only."
        verdicts = []
        for order in ((model, ref), (ref, model)) if ref else ((model,),):
            imgs = [x for x in order if x]
            if ref:
                first = "Picture 1 is the 3D model's side" if order[0] == model else "Picture 1 is the real photo"
                second = "picture 2 is the real photo" if order[0] == model else "picture 2 is the 3D model's side"
            else:
                first, second = "Picture 1 is the 3D model's side", "there is no second picture"
            try:
                v = _ask(use, Q.format(first=first, second=second, product=product, face=face, ref_note=ref_note,
                                       must=must), imgs)
            except Exception as ex:
                v = {"pass": False, "problems": [f"could not judge: {ex}"]}
            verdicts.append(v)
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
