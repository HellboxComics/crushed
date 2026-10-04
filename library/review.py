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


def failures(build_dir):
    """Every step check on the build's sheet that FAILED, as the build's own failures: (["step: <check>", ...],
    ["<step>: <check> (<detail>)", ...]). A check with ok None (not measured) is not a failure."""
    import re
    try:
        steps = json.load(open(os.path.join(build_dir, "review.json"))).get("steps", [])
    except Exception:
        return [], []
    names, probs = [], []
    for s in steps:
        for c in s.get("checks", []):
            if c.get("ok") is False:
                short = re.sub(r"\s+", " ", str(c.get("check", "")))[:70]
                names.append(f"step: {short}")
                probs.append(f"{s.get('step', '')[:50]}: {short}" + (f" ({c.get('detail', '')[:160]})" if c.get("detail") else ""))
    return names, probs


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
    """The judge brain looks at a box's six sides next to the main photo (kept while the pictures, question and
    brain are the same)."""
    import vet as V
    import kept
    k = kept.key("look-faces", [atlas_png, photo], FACES_Q, product, use)
    v = kept.get("look-faces", k)
    if v is None:
        try:
            v = V.ask(use, FACES_Q.format(product=product), [atlas_png, photo], think=False, side=1280) or {}
        except Exception as e:
            return None, f"could not look: {e}"
        kept.put("look-faces", k, v)
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
    """The judge brain looks at the unrolled label next to the main photo (only eyes can tell some things; kept
    while the pictures, question and brain are the same)."""
    import vet as V
    import kept
    k = kept.key("look-unrolled", [real_png, photo], LOOK_Q, product, top, use)
    v = kept.get("look-unrolled", k)
    if v is None:
        try:
            v = V.ask(use, LOOK_Q.format(product=product, top=top), [real_png, photo], think=False, side=1280) or {}
        except Exception as e:
            return None, f"could not look: {e}"
        kept.put("look-unrolled", k, v)
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


# ------------------------------------------------------------------ a circuit board: its sides and its parts
def pcb_checks(src, parts, kit_parts=()):
    """Exact checks on a circuit board build: the top is a real photo, the solder side is planned, the parts your AI
    found on the board make sense (enough of them, each with a height, each inside the board). [(what, ok, detail)]"""
    out = []
    front = (src.get("front") or {}).get("source")
    out.append(("the top of the board is a real photo of this item", front == "photo", f"top: {front}"))
    back = (src.get("back") or {}).get("source")
    out.append(("the solder side is planned from a photo (this item's or a sister card's)",
                back in ("photo", "template") if back else False, f"solder side: {back or 'not made'}"))
    parts = parts or []
    out.append(("parts were found standing on the board (chips, memory, capacitors, connectors)", len(parts) >= 3,
                f"{len(parts)} parts: " + ", ".join(sorted({str(p.get('type')) for p in parts})[:10])))
    no_h = [p for p in parts if not p.get("height_mm")]
    out.append(("every part has a height", not no_h, f"{len(no_h)} part(s) with no height" if no_h else "all have one"))
    outside = [p for p in parts if not all(0 <= v <= 1 for v in (p.get("box") or [2]))]
    out.append(("every part sits inside the board", not outside, f"{len(outside)} outside" if outside else "all inside"))
    big = [p for p in parts if (p["box"][2] - p["box"][0]) * (p["box"][3] - p["box"][1]) > 0.35]
    out.append(("no part covers more than a third of the board", not big,
                f"{len(big)} part(s) too big to be one part" if big else "sizes make sense"))
    if kit_parts:
        types = " ".join(str(p.get("type", "")).lower() for p in parts)
        miss = [k.get("part") for k in kit_parts
                if not any(w in types for w in str(k.get("part", "")).lower().split() if len(w) > 2)]
        out.append(("every part of this kind's kit was found", None if miss else True,
                    ("not found on this board: " + ", ".join(map(str, miss))) if miss else f"all {len(kit_parts)} kit parts"))
    return out


# ------------------------------------------------------------------ the parts builder: the plan checks itself
def parts_checks(plan, asm, kit_parts=()):
    """Exact checks on a parts plan and what Blender made of it: [(what, ok, detail)]. The plan is your AI's; these
    only measure it against the real size and the kit, so the engineer starts at the step that went wrong."""
    W, D, H = [float(x) for x in (plan.get("size_mm") or [0, 0, 0])[:3]]
    parts = plan.get("parts") or []
    out = []
    out.append(("the object was broken into parts", bool(parts), f"{len(parts)} parts: " +
                ", ".join(str(p.get('name')) for p in parts[:14])))
    # how far the planned parts reach (each part's center +/- half its size, rotation not counted)
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    rotated = []
    for p in parts:
        s = [float(x) for x in (p.get("size_mm") or [0, 0, 0])[:3]]
        a = [float(x) for x in (p.get("at_mm") or [0, 0, 0])[:3]]
        if p.get("shape") == "cylinder":
            dia, ln = min(s[0], s[1]), s[2]
            s = {"x": [ln, dia, dia], "y": [dia, ln, dia], "z": [dia, dia, ln]}.get(p.get("axis"), [dia, dia, ln])
        if p.get("shape") == "lathe" and p.get("profile_mm"):
            r = max(float(q[0]) for q in p["profile_mm"])
            zs = [float(q[1]) for q in p["profile_mm"]]
            s = [2 * r, 2 * r, max(zs) - min(zs)]
            a = [a[0], a[1], (max(zs) + min(zs)) / 2]
        if any(abs(float(x)) > 0.5 for x in (p.get("rotate_deg") or [0, 0, 0])):
            rotated.append(str(p.get("name")))
        for k in range(3):
            lo[k] = min(lo[k], a[k] - s[k] / 2)
            hi[k] = max(hi[k], a[k] + s[k] / 2)
    if parts:
        reach = [hi[k] - lo[k] for k in range(3)]
        off = [abs(reach[k] - [W, D, H][k]) / max([W, D, H][k], 1e-6) for k in range(3)]
        out.append(("the planned parts fill the real size (within 10% each way)", max(off) <= 0.10,
                    f"planned {reach[0]:.0f} x {reach[1]:.0f} x {reach[2]:.0f} mm, real {W:.0f} x {D:.0f} x {H:.0f} mm"))
        out.append(("parts that are turned (rotate_deg)", None if rotated else True,
                    ("turned: " + ", ".join(rotated)) if rotated else "no part is turned"))
    inside = [p for p in parts if p.get("inside")]
    if inside:
        def box_of(p):
            s = [float(x) for x in (p.get("size_mm") or [0, 0, 0])[:3]]
            a = [float(x) for x in (p.get("at_mm") or [0, 0, 0])[:3]]
            return [(a[k] - s[k] / 2, a[k] + s[k] / 2) for k in range(3)]
        outer = [box_of(p) for p in parts if not p.get("inside")]
        poke = [str(p.get("name")) for p in inside
                if not any(all(ob[k][0] - 0.5 <= bi[k][0] and bi[k][1] <= ob[k][1] + 0.5 for k in range(3))
                           for ob in outer for bi in [box_of(p)])]
        out.append(("every inside part fits within one outer part", not poke,
                    ("poking out of every outer part: " + ", ".join(poke)) if poke else f"{len(inside)} inside part(s) fit"))
    fixed = plan.get("fixed") or []
    out.append(("every part sat inside the real size as planned", not fixed,
                "; ".join(fixed)[:400] or "no part had to be moved or shrunk"))
    if kit_parts:
        names = " ".join(str(p.get("name", "")).lower() for p in parts)
        miss = [k.get("part") for k in kit_parts
                if not any(w in names for w in str(k.get("part", "")).lower().split() if len(w) > 2)]
        out.append(("every part of this kind's kit is in the plan", not miss,
                    ("missing: " + ", ".join(map(str, miss))) if miss else f"all {len(kit_parts)} kit parts planned"))
    printed = [p for p in parts if p.get("print")]
    out.append(("printed parts carry artwork cut from the photos", None, f"{len(printed)} printed part(s)"))
    guessed = [str(p.get("name")) for p in parts if not p.get("color_measured") and not p.get("inside")]
    out.append(("every visible part's color was measured off a photo where it shows (not guessed)",
                True if not guessed else None,
                ("color guessed, no photo box given: " + ", ".join(guessed)) if guessed else "all measured"))
    flags = (asm or {}).get("flags") or []
    stand = [f for f in flags if "stand-in" in f] + [f for f in fixed if "egg outline was used" in f]
    broke = [f for f in flags if "could not be built" in f]
    out.append(("every planned part was built", not broke, "; ".join(broke)[:400] or
                f"{(asm or {}).get('parts', len(parts))} built"))
    out.append(("every soft part has its own outline read off the photos (no stand-in, no default egg)", not stand,
                "; ".join(stand)[:400] or "every soft part lofted from its own outlines"))
    return out


def not_on_item(words, by_png, src_of, dossier):
    """Words read off a photo that the dossier's careful look says are laid OVER that photo (a caption, a watermark,
    a listing's text), or that read as a credit/site name (facts.not_printed): never printed. -> (kept, left out).
    Kept here, locked, next to only_words. (2026-10-04: 'Remember these?' - a caption - was read as label text.)"""
    import re
    import facts as FX
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    photos = {p.get("file"): p for p in (dossier or {}).get("photos") or [] if isinstance(p, dict)}
    overlay_of = {}                                             # normalized word -> True when some photo's overlay
    for png, lines in (by_png or {}).items():
        p = photos.get(src_of.get(png, png))
        if not p:
            continue
        ow = FX._overlay_words(p)
        for w in lines:
            if FX._on_overlay(w, ow):
                overlay_of[norm(w)] = True
    kept, out = [], []
    for w in words:
        n = norm(w)
        bad = FX.not_printed(w) or overlay_of.get(n) or any(k and len(n) >= 4 and (k.startswith(n) or k.endswith(n))
                                                            for k in overlay_of)
        (out if bad and n else kept).append(w)
    return kept, out


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
