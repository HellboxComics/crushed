"""SELF-REVIEW: every step of a build shows its work and checks itself (kits/DESIGN.md, "Self-review").

Your AI should see its own output, realize what is wrong and correct it on its own (Cody, 2026-10-03). So every step
writes down, in the item's build folder (review.json), what it made (its pictures) and its own checks - exact ones
measured by code, and looks by the judge brain where only eyes can tell. When the model fails, the engineer starts
from the FIRST step whose check failed - the way Claude found the Duracell's label bugs by hand that day - instead of
guessing from the finished model.

    R = review.Sheet(build_dir)               # a fresh sheet for this build
    R.step("words", files=[...], checks=[("no word is a piece of another", True, "7 words")])
    R.first_failure()                         # {"step", "check", "detail", "files"} or None
    R.text()                                  # the sheet in words, for the engineer
"""
import json
import os
import time


class Sheet:
    def __init__(self, build_dir, fresh=True):
        self.path = os.path.join(build_dir, "review.json")
        self.steps = []
        if not fresh:
            try:
                self.steps = json.load(open(self.path)).get("steps", [])
            except Exception:
                self.steps = []
        self.save()

    def step(self, name, files=(), checks=(), note=""):
        """One step's work: its pictures and its checks [(what, ok True/False/None, detail)]."""
        self.steps.append({"step": name, "at": time.time(), "note": note,
                           "files": [f for f in files if f and os.path.exists(f)],
                           "checks": [{"check": c, "ok": ok, "detail": str(det)[:400]} for c, ok, det in checks]})
        self.save()
        return [c for c, ok, _ in checks if ok is False]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"steps": self.steps}, f, indent=1)
        os.replace(tmp, self.path)

    def first_failure(self):
        for s in self.steps:
            for c in s["checks"]:
                if c["ok"] is False:
                    return {"step": s["step"], "check": c["check"], "detail": c["detail"], "files": s["files"]}
        return None

    def text(self):
        if not self.steps:
            return "(no review sheet)"
        out = []
        for s in self.steps:
            marks = "; ".join(f"{'FAILED' if c['ok'] is False else 'ok' if c['ok'] else '?'} {c['check']}"
                              + (f" ({c['detail']})" if c["detail"] else "") for c in s["checks"]) or "no checks"
            out.append(f"- {s['step']}: {marks}" + (f" [pictures: {', '.join(os.path.basename(f) for f in s['files'])}]"
                                                    if s["files"] else ""))
        ff = self.first_failure()
        out.append(f"FIRST STEP THAT WENT WRONG: {ff['step']} - {ff['check']} ({ff['detail']})" if ff else
                   "Every step's own checks passed - the problem shows only in the finished model.")
        return "\n".join(out)


def load(build_dir):
    return Sheet(build_dir, fresh=False)


# ------------------------------------------------------------------ exact checks for a round item's label
def pieces(words):
    """Words that are only a piece of another word on the label (a word the photo's edge cut off)."""
    import re
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    toks = [t for w in words for t in str(w).split()]
    return [w for w in words if len(str(w).split()) == 1 and len(norm(w)) >= 3 and
            any(len(norm(t)) > len(norm(w)) and (norm(t).startswith(norm(w)) or norm(t).endswith(norm(w))) for t in toks)]


def front_length(cov):
    """How much of the label's length the main photo covers at the front (0..1). Below 0.9: the main photo shows only
    part of the item - its other parts can't be checked against it."""
    import numpy as np
    W = cov.shape[1]
    front = cov[:, W // 2 - 8:W // 2 + 8].max(1)
    return float((front > 0.05).mean())


def metal_share(mr_png):
    """How much of a label is marked as metal ink (the blue channel of its metal/roughness map)."""
    import numpy as np
    from PIL import Image
    return float((np.asarray(Image.open(mr_png).convert("RGB"))[..., 2] > 127).mean())


LOOK_Q = """Picture 1 was made by unrolling the printed label of {product} flat from real photos (left to right =
along the item, from its {top} end; top to bottom = once around it, the main photo's side in the middle band, other
photos at the top and bottom edges; smeared streaks = parts no photo saw). Picture 2 is the main photo.
Is anything in picture 1 WRONG as an unrolled label of this item: a part stretched or squashed along its length, a
part doubled, a different object, a different version of the item, or the item's metal ends inside the label?
Answer ONLY JSON: {{"problems": ["short, specific"], "ok": true or false}}"""


FACES_Q = """Picture 1 is the flat texture map of a box model of {product}: its six sides laid out (front, back,
left, right, top, bottom), each made from a real photo, a sister box's photo, or rebuilt from printed facts.
Picture 2 is the main photo of the real item. Is anything on picture 1 WRONG for this item: a side upside down or
mirrored, a side stretched or squashed, a watermark or website text, a different product's panel, room light or
shadow on a side, a side left blank that should be printed?
Answer ONLY JSON: {{"problems": ["short, specific, naming the side"], "ok": true or false}}"""


def look_faces(atlas_png, photo, product, use):
    """The judge brain looks at a box's six sides next to the main photo."""
    import vet as V
    try:
        v = V.ask(use, FACES_Q.format(product=product), [atlas_png, photo], think=False, side=1280) or {}
    except Exception as e:
        return None, f"could not look: {e}"
    probs = [str(p) for p in (v.get("problems") or []) if str(p).strip()]
    ok = v.get("ok")
    ok = (not probs) if ok is None else bool(ok) and not probs
    return ok, "; ".join(probs)[:400] or "nothing wrong seen"


def box_checks(src, sides=("front", "back", "left", "right", "top", "bottom")):
    """Exact checks on a box's sides (skin.box_skin's sources): [(what, ok, detail)]."""
    out = []
    front = (src.get("front") or {}).get("source")
    out.append(("the front is a real photo of this item", front == "photo", f"front: {front}"))
    missing = [s for s in sides if s not in src]
    out.append(("every side is made", not missing, ", ".join(missing) or "all six"))
    gaps = {s: v.get("no_fact_for") for s, v in src.items() if v.get("source") == "rebuilt" and v.get("no_fact_for")}
    out.append(("rebuilt sides carry what this kind normally has", None if gaps else True,
                "; ".join(f"{s}: no fact found for {', '.join(g)}" for s, g in gaps.items()) or "all drawn"))
    return out


def look_unrolled(real_png, photo, product, use, top="top"):
    """The judge brain looks at the unrolled label next to the main photo (only eyes can tell some things)."""
    import vet as V
    try:
        v = V.ask(use, LOOK_Q.format(product=product, top=top), [real_png, photo], think=False, side=1280) or {}
    except Exception as e:
        return None, f"could not look: {e}"
    probs = [str(p) for p in (v.get("problems") or []) if str(p).strip()]
    ok = v.get("ok")
    ok = (not probs) if ok is None else bool(ok) and not probs
    return ok, "; ".join(probs)[:400] or "nothing wrong seen"


# ------------------------------------------------------------------ the one rule the label writer may never break
def only_words(texts, words):
    """Only words read off real photos may be printed (Cody's rule: nothing is ever invented). Kept here, locked,
    so the label writer's own file (layout.py) can be improved by the engineer without this rule being weakened."""
    allowed = " ".join(str(w) for w in words).lower()
    out = []
    for t in texts or []:
        if not isinstance(t, dict) or not str(t.get("text", "")).strip():
            continue
        if all(tok.lower().strip(".,:;") in allowed for tok in str(t["text"]).split()):
            out.append(t)
    return out


# ------------------------------------------------------------------ the insides and the materials: receipts
def insides_step(spec, recipe, physics):
    """What is inside the model and what each material is made to behave like, each with its receipt - so nobody
    has to take the insides on trust. [(what, ok, detail)]: ok None = a handbook value, not measured on this item."""
    checks = []
    srcs = (recipe or {}).get("checked_against") or []
    named = [s.get("source") for s in srcs if isinstance(s, dict) and s.get("source")]
    parts = [q.get("part") for q in (recipe or {}).get("inside") or []]
    checks.append(("the insides come from a recipe with receipts", bool(parts) and bool(named),
                   (f"{len(parts)} inside parts ({', '.join(parts)}) from: " + "; ".join(named)) if parts and named
                   else ("no inside parts" if not parts else "inside parts with NO source named")))
    kinds = sorted({q.get("kind") for q in (recipe or {}).get("inside") or [] if q.get("kind")} |
                   {m.get("kind") for m in ((spec or {}).get("materials") or {}).values() if m.get("kind")})
    rows = []
    for k in kinds:
        ph = (physics or {}).get(k) or {}
        rows.append(f"{k}: density {ph.get('density', '?')} kg/m3, stiffness {ph.get('stiffness', '?')} Pa, "
                    f"yield {ph.get('yield', '?')} Pa, fails by {ph.get('fails', '?')}")
    checks.append(("every material has crush numbers (density, stiffness, yield)",
                   None if rows else False,
                   ("handbook values for the material kind, not measured on this item: " + " | ".join(rows))
                   if rows else "no materials"))
    return checks
