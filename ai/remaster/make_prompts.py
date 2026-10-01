"""Write one plain-text prompt per object for the remaster: what the real thing is, its era, and the details that
make it recognizable. Never overwrites a prompt that already exists (so edits stay). These are starting points: the local AI
rewrites each one into an exact physical description before drawing (see the brief).

    python3 ai/remaster/make_prompts.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "blender"))
import bpy  # noqa: E402,F401
from crushed import lore  # noqa: E402
from crushed.objects import ERAS, load  # noqa: E402

OUT = os.path.join(ROOT, "ai", "remaster", "prompts")
os.makedirs(OUT, exist_ok=True)
reg = load()
n = 0
for name, d in sorted(reg.items()):
    if d.group == "filler" or name not in lore.NAMES:
        continue
    p = os.path.join(OUT, name + ".txt")
    if os.path.exists(p):
        continue
    years = f"{ERAS[min(d.eras)].split('-')[0]}-{ERAS[max(d.eras)].split('-')[1]}"
    doc = " ".join((d.fn.__doc__ or "").split())
    what = doc if len(doc) > 40 else f"{lore.NAMES[name].lower()}. {doc}"
    text = f"{what} The real object as it was sold and used in {years}, worn from use."
    open(p, "w").write(text.strip() + "\n")
    n += 1
print(f"{n} new prompts in {OUT}")
