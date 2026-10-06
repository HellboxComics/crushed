"""ONE STEP, TESTED ALONE (for the engineer; audit 2026-10-04: "it cannot test one step without a full rebuild").

Runs with the engineer's own copy of the code (this file's folder), on the item's current build folder, writing
into a step folder. Prints one JSON line starting with STEP. Steps:

  render_label  layout=<json file>                 draw a layout in exact type: png, metal map, text boxes,
                                                   overlaps, measured colors vs the real label (seconds)
  label                                             the whole label step: words -> layout rounds -> drawn label,
                                                   with the step's own checks (minutes, a few brain calls)
  build_parts   plan=<parts_plan.json>              the parts builder on a plan: the model, its parts measured,
                                                   what could not be built (about a minute)
  build_round   spec=<spec json>                    the round builder on a spec (about a minute)
  measure       glb=<model>                         the exact checks only on a model (minutes, no judge)
  judge_side    face=<name> glb=<model>             the judge's look at ONE side of a model (one or two brain calls)

    python steptest.py <step> <build dir> <out dir> key=value ...
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ownmods  # noqa: E402
ownmods.install()


def say(*a):
    print(*a, flush=True)


def _args(items):
    out = {}
    for it in items:
        if "=" in it:
            k, v = it.split("=", 1)
            out[k] = v
    return out


def _blender(script, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "shapes", script), "--", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Blender ({script}) failed: " + (r.stderr or r.stdout)[-600:])
    return r.stdout[-800:]


def render_label(d, out, a):
    import labelart
    import layout as LAY
    lay = json.load(open(a["layout"]))
    png, mr = labelart.render(lay, out, px=2048, name="step")
    boxes = json.load(open(os.path.join(out, "step_boxes.json")))
    real = os.path.join(d, "texture", "real.png")
    cover = os.path.join(d, "texture", "real_seen.png")
    colors = None
    if os.path.exists(real):
        share, fixes = LAY.color_check(png, real, cover if os.path.exists(cover) else None)
        colors = {"share": round(share, 2), "fixes": fixes[:10]}
    return {"png": png, "mr": mr, "texts": len(boxes.get("texts", [])), "overlaps": boxes.get("overlaps", []),
            "off_label": boxes.get("off_label", []), "colors_vs_real": colors, "pictures": [png]}


def label(d, out, a):
    """The label step as the build runs it (2026-10-05): the real photo made the texture - cleaned of glare and
    sharpened, the metal map from the measured bands. Nothing is redrawn from words."""
    tex = os.path.join(d, "texture")
    real = os.path.join(tex, "real.png")
    cover = os.path.join(tex, "real_seen.png")
    meta = json.load(open(os.path.join(tex, "label_meta.json"))) if os.path.exists(os.path.join(tex, "label_meta.json")) else {}
    if not os.path.exists(real):
        raise RuntimeError("this build has no texture/real.png - run the full build once first")
    import vet as V
    import run as R
    png, mr, notes = R.photo_label(meta.get("product", ""), real, cover, out, V.model(), "along", log=say)
    return {"png": png, "mr": mr, "notes": notes, "pictures": [png, real]}


def build_parts(d, out, a):
    plan = a.get("plan") or os.path.join(d, "parts_plan.json")
    name = "step_parts"
    log = _blender("assembly.py", plan, out, name)
    log += _blender("contract.py", os.path.join(out, name + ".blend"), out, name, "")
    glb = os.path.join(out, name + ".glb")
    asm = json.load(open(os.path.join(out, "assembly.json"))) if os.path.exists(os.path.join(out, "assembly.json")) else {}
    import review
    checks = review.parts_checks(json.load(open(plan)), asm)
    return {"glb": glb, "built_parts": asm.get("parts"), "flags": asm.get("flags"), "blender_said": log[-300:],
            "checks": [{"check": c, "ok": ok, "detail": det} for c, ok, det in checks], "pictures": _shots(glb, out)}


def build_round(d, out, a):
    spec = a.get("spec") or os.path.join(d, "shape.json")
    log = _blender("lathe.py", spec, out, os.path.join(d, "label.png"), os.path.join(d, "label_mr.png"))
    blends = [f for f in os.listdir(out) if f.endswith(".blend") and not f.endswith("_builder.blend")]
    if blends:
        log += _blender("contract.py", os.path.join(out, blends[0]), out, blends[0][:-6], "")
    glbs = [f for f in os.listdir(out) if f.endswith(".glb")]
    glb = os.path.join(out, glbs[0]) if glbs else None
    return {"glb": glb, "blender_said": log[-300:], "pictures": _shots(glb, out) if glb else []}


def _shots(glb, out):
    """Four views of a model, so the engineer can look at what one step built."""
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "preview.py"), "--", glb, os.path.join(out, "view.png"),
                        "0,90,180,270"], check=True, capture_output=True, timeout=600)
        return [os.path.join(out, f"view_{a:03d}.png") for a in (0, 90, 180, 270) if os.path.exists(os.path.join(out, f"view_{a:03d}.png"))]
    except Exception as e:
        say(f"[step] no views: {e}")
        return []


def measure(d, out, a):
    import dossier as DS
    import measure as MS
    import vet as V
    cid = os.path.basename(d.rstrip("/"))
    glb = a.get("glb") or os.path.join(d, "model", cid + ".glb")
    dos = DS.load(cid) or {"size_m": None, "faces": {}, "facts": {}}
    route = a.get("route") or ("round" if os.path.exists(os.path.join(d, "label.png")) else
                               "pcb" if os.path.exists(os.path.join(d, "parts.json")) else "box")
    m = MS.run(cid, out, glb, dos, route, use=V.model(), log=say)
    return {"pass": m["pass"], "failed": m["failed"], "problems": m["problems"][:12],
            "checks": {k: v for k, v in (m.get("checks") or {}).items()} if isinstance(m.get("checks"), dict) else m.get("checks"),
            "pictures": [v for v in (m.get("renders_lit") or m.get("renders") or {}).values()][:4]}


def judge_side(d, out, a):
    import dossier as DS
    import judge
    import measure as MS
    import vet as V
    cid = os.path.basename(d.rstrip("/"))
    glb = a.get("glb") or os.path.join(d, "model", cid + ".glb")
    face = a.get("face")
    if not face:
        raise RuntimeError("judge_side needs face=<name>")
    dos = DS.load(cid) or {"faces": {}}
    route = a.get("route") or ("round" if os.path.exists(os.path.join(d, "label.png")) else "box")
    m = MS.run(cid, out, glb, dos, route, use=V.model(), log=say)
    one = {"faces": {face: (dos.get("faces") or {}).get(face) or {}}}
    j = judge.sides(cid, m["renders"], one, V.model(), route, product=a.get("product", cid), log=say,
                    lit=m.get("renders_lit") or {})
    return {"face": face, "verdict": j["faces"].get(face), "pictures": [p for k, p in (m.get("renders_lit") or m["renders"]).items() if face in k][:4]}


STEPS = {"render_label": render_label, "label": label, "build_parts": build_parts, "build_round": build_round,
         "measure": measure, "judge_side": judge_side}

if __name__ == "__main__":
    step, d, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    t = time.time()
    try:
        res = STEPS[step](d, out, _args(sys.argv[4:]))
        res["seconds"] = int(time.time() - t)
        print("STEP " + json.dumps(res, default=str), flush=True)
    except Exception as e:
        print("STEP " + json.dumps({"error": str(e)[:800], "seconds": int(time.time() - t)}), flush=True)
        sys.exit(1)
