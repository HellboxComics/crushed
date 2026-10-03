"""THE GENERAL ONE-OFF BUILDER, PART 1: your AI breaks any object into the parts it is really made of.

A person modeling something they have never modeled before blocks it out first: "a fabric body this big, a zipper
along the top, a strap, a logo patch on the front, jumper cables coiled inside". This does the same. Your AI looks at
the item's photos (every side the dossier found), its real size, its family and how it is made, and writes a parts
plan; library/shapes/assembly.py builds that plan in Blender, each part its own solid with its own material, at real
size, printed parts carrying their real artwork cut from the photos.

    plan = parts.plan(cid, card, dossier, use, out_json)     # -> the plan (also saved to out_json)

Every part shape is one a builder can make exactly: rounded_box, cylinder, lathe (a spun profile), sheet, tube (a
bent rod or cable along points), sphere, or organic (a sculpted part, made by the organic builder when it works on
this Mac, else a rounded stand-in that is flagged). Coordinates: millimeters, origin at the bottom center of the
object, x = left to right seen from the front, y = front (negative) to back (positive), z = up.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SHAPES = ("rounded_box", "cylinder", "lathe", "sheet", "tube", "sphere", "organic")
SIDES = ("+x", "-x", "+y", "-y", "+z", "-z")

ASK = """[parts] You are a senior 3D modeler blocking out a production model of a real object, built the way it is
manufactured. The object: {product} ({year}). Its family: {family} - {what}. Real overall size: {W} x {D} x {H} mm
(width x depth x height). How it is made: {made}
{notes}The pictures: {pics}
Break the object into its real parts (outside shell pieces, panels, trim, zipper, buttons, labels, straps, lids,
caps, and what is INSIDE when that is part of the item). Use only these shapes:
  rounded_box (size_mm [x,y,z], bevel_mm), cylinder (size_mm [diameter, diameter, height], axis "x"|"y"|"z"),
  lathe (profile_mm: [[radius, z], ...] bottom to top, axis z), sheet (a thin panel: size_mm with one tiny side),
  tube (path_mm: [[x,y,z], ...] points along it, radius_mm), sphere (size_mm), organic (a sculpted part: size_mm).
Coordinates in mm: origin at the bottom center of the whole object; x left->right seen from the front; y front (-) to
back (+); z up. Every part must sit inside the overall size. Give printed parts their artwork: "print": {{"picture":
<picture number>, "box": [x0, y0, x1, y1] fractions of that picture where the art is, "side": "-y" (front) | "+y" |
"-x" | "+x" | "+z" | "-z"}}.
Materials, one of: {kinds}.
Answer ONLY JSON:
{{"parts": [{{"name": "...", "shape": "...", "size_mm": [x, y, z], "at_mm": [x, y, z] (the part's center),
   "rotate_deg": [x, y, z], "bevel_mm": 0.0, "axis": "z", "profile_mm": [], "path_mm": [], "radius_mm": 0.0,
   "material": "<kind>", "color": [r, g, b] (0..1, the real material's color as seen in the photo, without the room
   light), "roughness": 0.5, "metallic": 0 or 1, "print": null, "inside": false,
   "why": "what in the pictures shows this part"}}],
 "not_modeled": ["details too small to model, which belong in the normal map instead"]}}"""


def _num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _vec(v, n=3, d=0.0):
    v = list(v or [])[:n]
    return [_num(x, d) for x in v] + [d] * (n - len(v))


def clean(plan, W, D, H, pics, kinds):
    """Keeps only parts a builder can make, inside the object's real size; every fix is written in 'fixed'."""
    out, fixed = [], []
    lim = (W / 2, D / 2, H)
    for i, p in enumerate(plan.get("parts") or []):
        if not isinstance(p, dict):
            continue
        name = str(p.get("name") or f"part_{i + 1}")[:40]
        shape = p.get("shape") if p.get("shape") in SHAPES else "rounded_box"
        size = [max(0.05, abs(x)) for x in _vec(p.get("size_mm"), 3, 1.0)]
        at = _vec(p.get("at_mm"), 3, 0.0)
        if shape == "tube":
            path = [_vec(q, 3) for q in (p.get("path_mm") or []) if isinstance(q, (list, tuple))]
            if len(path) < 2:
                fixed.append(f"{name}: a tube needs 2+ points - dropped")
                continue
            p["path_mm"] = [[min(max(x, -lim[0]), lim[0]), min(max(y, -lim[1]), lim[1]), min(max(z, 0), lim[2])]
                            for x, y, z in path]
        if shape == "lathe":
            prof = [[max(0.0, _num(q[0])), min(max(_num(q[1]), 0), H)] for q in (p.get("profile_mm") or [])
                    if isinstance(q, (list, tuple)) and len(q) >= 2]
            if len(prof) < 2:
                shape = "cylinder"
                fixed.append(f"{name}: lathe without a profile - made a cylinder")
            p["profile_mm"] = prof
        axis = p.get("axis") if p.get("axis") in ("x", "y", "z") else "z"
        ext = list(size)                                     # how far the part reaches along x, y, z
        if shape == "cylinder":
            dia, ln = min(size[0], size[1]), size[2]
            ext = {"x": [ln, dia, dia], "y": [dia, ln, dia], "z": [dia, dia, ln]}[axis]
        for k in range(3):                                   # the part stays inside the object's real size
            half = ext[k] / 2
            lo, hi = (-lim[k], lim[k]) if k < 2 else (0, lim[k])
            if ext[k] > (hi - lo) * 1.02:
                fixed.append(f"{name}: reaches {ext[k]:.1f} mm along {'xyz'[k]}, more than the object - fitted")
                f = (hi - lo) / ext[k]
                if shape == "cylinder":                      # shrink the matching measure of the cylinder
                    if ext[k] == size[2] and {"x": 0, "y": 1, "z": 2}[axis] == k:
                        size[2] *= f
                    else:
                        size[0] *= f
                        size[1] *= f
                else:
                    size[k] *= f
                ext[k] = hi - lo
                half = ext[k] / 2
            c = min(max(at[k], lo + half), hi - half)
            if abs(c - at[k]) > 0.5:
                fixed.append(f"{name}: moved {abs(c - at[k]):.1f} mm along {'xyz'[k]} to sit inside the object")
            at[k] = c
        mat = p.get("material") if p.get("material") in kinds else "molded_plastic"
        pr = p.get("print") if isinstance(p.get("print"), dict) else None
        if pr:
            n = int(_num(pr.get("picture"), 0))
            if not (1 <= n <= len(pics)):
                pr = None
            else:
                pr = {"photo": pics[n - 1], "box": [min(max(_num(b), 0), 1) for b in _vec(pr.get("box"), 4, 0)],
                      "side": pr.get("side") if pr.get("side") in SIDES else "-y"}
                if pr["box"][2] <= pr["box"][0] or pr["box"][3] <= pr["box"][1]:
                    pr = None
        out.append({"name": name, "shape": shape, "size_mm": size, "at_mm": at,
                    "rotate_deg": _vec(p.get("rotate_deg"), 3, 0.0), "bevel_mm": max(0.0, _num(p.get("bevel_mm"))),
                    "axis": axis,
                    "profile_mm": p.get("profile_mm") or [], "path_mm": p.get("path_mm") or [],
                    "radius_mm": max(0.2, _num(p.get("radius_mm"), 1.0)), "material": mat,
                    "color": [min(max(c, 0.02), 0.95) for c in _vec(p.get("color"), 3, 0.5)],
                    "roughness": min(max(_num(p.get("roughness"), 0.5), 0.02), 1.0),
                    "metallic": 1.0 if _num(p.get("metallic")) >= 0.5 else 0.0, "print": pr,
                    "inside": p.get("inside") is True, "why": str(p.get("why", ""))[:200]})
    return {"parts": out, "fixed": fixed, "not_modeled": plan.get("not_modeled") or []}


def plan(cid, card, dos, use, out_json, log=print, notes=""):
    import families
    import vet as V
    kinds = sorted(k for k in json.load(open(os.path.join(HERE, "factory", "physics.json"))) if not k.startswith("_"))
    W, D, H = (x * 1000 for x in (dos.get("size_m") or card.get("size") or [0.1, 0.1, 0.1])[:3])
    pics, names = [], []
    if dos.get("picked"):
        pics.append(dos["picked"])
        names.append("picture 1 = the picked photo (front)")
    for face, e in (dos.get("faces") or {}).items():
        if e.get("photo") and e["photo"] not in pics and e.get("source") in ("exact_photo", "template_photo") \
                and len(pics) < 4:
            pics.append(e["photo"])
            names.append(f"picture {len(pics)} = the {face}" + (" (a sister product)" if e["source"] == "template_photo" else ""))
    fam = families.get((card.get("family_lib") or {}).get("family", "general"))
    c = card.get("construction") or {}
    made = "; ".join(f"{L.get('part')}: {L.get('material')}" for L in c.get("layers", [])) or "unknown"
    kit_parts = fam.get("parts") or []                     # what every one of this kind is made of (its kit)
    if kit_parts:
        notes = (f"Every {fam.get('what', fam['family'])} is made of these parts (its kit; keep them, add what this one "
                 "has besides, drop only what this one truly lacks): "
                 + "; ".join(f"{x.get('part')} ({x.get('material')}, {'hard' if x.get('hard') else 'soft'})"
                             for x in kit_parts) + "\n") + notes
    q = ASK.format(product=card.get("product"), year=card.get("year"), family=fam["family"], what=fam["what"],
                   W=round(W), D=round(D), H=round(H), made=made, pics="; ".join(names) or "none",
                   kinds=", ".join(kinds), notes=(f"Notes from the owner: {notes}\n" if notes else ""))
    raw = V.ask(use, q, pics, think=True, side=1280) if (use and pics) else {}
    p = clean(raw or {}, W, D, H, pics, kinds)
    if not p["parts"]:
        raise RuntimeError("your AI could not break this object into parts from its photos")
    p.update({"cid": cid, "size_mm": [W, D, H], "pictures": pics, "family": fam["family"]})
    json.dump(p, open(out_json, "w"), indent=1)
    log(f"[parts] {cid}: {len(p['parts'])} parts - " + ", ".join(x["name"] for x in p["parts"][:12]))
    for f in p["fixed"]:
        log(f"[parts] fixed: {f}")
    return p
