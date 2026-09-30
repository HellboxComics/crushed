"""Write a template PNG for every art slot, so a layer made elsewhere can be drawn over the right shape.

    python3 blender/slots.py                # templates -> assets/slots/_templates/
    python3 blender/slots.py --list         # slot names and sizes only

Put finished art in assets/slots/ as <slot>.png (or <slot>_<anything>.png for several variants).
"""
import argparse
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from crushed import tex  # noqa: E402

ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    out = os.path.join(tex.SLOT_DIR, "_templates")
    if not a.list:
        os.makedirs(out, exist_ok=True)
    for n in tex.SLOT_NAMES:
        fn = getattr(tex, n)
        real = inspect.unwrap(fn) if hasattr(fn, "__wrapped__") else fn
        rng = np.random.default_rng(1)
        try:
            # call the procedural version directly: the wrapper would hand back any art already in the slot
            orig = fn.__closure__[0].cell_contents
            extra = [] if len(inspect.signature(orig).parameters) <= 2 else ["STAMP"][:len(
                [p for p in list(inspect.signature(orig).parameters.values())[2:] if p.default is inspect._empty])]
            img = orig(rng, f"tpl_{n}", *extra)
        except Exception as e:  # noqa: BLE001
            print(f"{n:18s} skipped ({e})")
            continue
        w, h = img.size
        print(f"{n:18s} {w}x{h}")
        if not a.list:
            img.filepath_raw = os.path.join(out, n + ".png")
            img.file_format = "PNG"
            img.save()


if __name__ == "__main__":
    main()
