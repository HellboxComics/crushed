"""Planned objects: designed as data by the Mac's AI (assets/plan/items.json), built as real models by the remaster.
Until an object's model is approved it stands in as a plain block of its real size, so the plan can be checked,
sized and rendered end to end. Once assets/models/<name>/model.glb exists, that model replaces the block."""
import hashlib
import json
import os

from . import P, obj

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLAN = os.path.join(ROOT, "assets", "plan", "items.json")
ITEMS = json.load(open(PLAN)) if os.path.exists(PLAN) else {}
LORE_NAMES = {k: v.get("display", k.replace("_", " ").title()) for k, v in ITEMS.items()}
LORE_NOTES = {k: list(v.get("notes", [])) or ["recovered whole"] for k, v in ITEMS.items()}


def _register(name, it):
    sx, sy, sz = (float(x) for x in it["size"])
    h = hashlib.sha1(name.encode()).digest()
    col = tuple(0.25 + 0.6 * b / 255 for b in h[:3])

    def fn(b, rng, pal):
        b.box((sx, sy, sz), mat="body", bevel=min(sx, sy, sz) * 0.08)
        return {"body": P(col, 0.5)}
    obj(name, eras=tuple(it.get("eras", (0, 1, 2, 3, 4))), mass=float(it.get("mass", 0.1)),
        weight=float(it.get("weight", 1.0 if it.get("group", "special") == "special" else 0.12)),
        hero=tuple(it.get("hero", (0, -1, 0))), group=it.get("group", "special"), big=bool(it.get("big", False)),
        tags=tuple(it.get("tags", ())))(fn)


for _n, _it in ITEMS.items():
    _register(_n, _it)
