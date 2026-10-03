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
