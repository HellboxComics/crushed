"""REAL MATERIALS (every builder): a part's base color, metallic and roughness are kept inside the real-world range
of its material kind (library/materials.json) - steel can't come out as dark as lead, paint can't be bare metal.
What is changed is printed, so the build log says it.

    color, metallic, rough = realmat.fit(kind, color, metallic, rough, name)
"""
import json
import os

_R = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "materials.json")))["kinds"]


def fit(kind, color, metallic, rough, name=""):
    r = _R.get(kind)
    if not r:
        return list(color), metallic, rough
    color = list(color)[:3]
    notes = []
    lo, hi = r["metallic"]
    m2 = min(max(metallic, lo), hi)
    if abs(m2 - metallic) > 1e-6:
        notes.append(f"metallic {metallic:.2f} -> {m2:.2f}")
    lo, hi = r["roughness"]
    r2 = min(max(rough, lo), hi)
    if abs(r2 - rough) > 1e-6:
        notes.append(f"roughness {rough:.2f} -> {r2:.2f}")
    b = sum(color) / 3
    lo, hi = r["base"]
    if b > 1e-6 and not (lo <= b <= hi):
        k = min(max(b, lo), hi) / b                          # same hue, real brightness
        color = [min(c * k, 1.0) for c in color]
        notes.append(f"base brightness {b:.2f} -> {sum(color) / 3:.2f}")
    if notes:
        print(f"[materials] {name} ({kind.replace('_', ' ')}): kept in its real range: {', '.join(notes)}")
    return color, m2, r2
