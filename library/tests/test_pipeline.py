"""run.py's own pipeline() for Pop-Tarts 1997 in TRIAL mode (nothing published, nothing sent): your pick is in, so
it goes straight to the dossier (cached from test_dossier) and the box build; it must reach the carton step, which
needs Blender (not in this sandbox) - run_blender is replaced by a recorder to show the exact arguments."""
import json
import os
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
os.environ["CRUSHED_REMASTER_WORK"] = SCR + "/mine_work"
os.environ["CRUSHED_TRIAL"] = "1"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
sys.path.insert(0, SCR)
import recorded as R  # noqa: E402
import run  # noqa: E402
import vet  # noqa: E402
import turnaround as T  # noqa: E402

CID = "poptarts_frosted_strawberry_1997"
card_path = os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "cards", CID + ".json")
before = json.load(open(card_path))


def ask(model, text, images, think=True, side=1280):
    if text.lstrip().startswith("[family]"):
        return {"family": "folding_carton", "confidence": 9, "why": "a printed paperboard Pop-Tarts box",
                "second": "rigid_case", "material_outside": "printed paperboard", "is_package": True}
    if "brand name and product name lockup" in text:
        return dict(R.LOGO_BOX)
    if "main product picture" in text:
        return dict(R.PHOTO_BOX)
    raise RuntimeError("no recorded answer: " + text[:60])


def no_room(*a, **k):
    raise RuntimeError("the drawing room isn't running in this sandbox")


vet.ask = ask
vet.model = lambda: "qwen3.8:27b-q8_0"
T.upscale = no_room
T.photo_mask = no_room
blender = []


def fake_blender(script, *args):
    blender.append((script, args))
    raise SystemExit("stop here: Blender is not in this sandbox")


run.run_blender = fake_blender
try:
    run.pipeline(CID, redo=False)
except SystemExit as e:
    print("stopped as planned:", e)
print("Blender would run:", blender)
script, args = blender[0]
assert script == "carton.py" and args[-1].endswith("contents.json"), args
print("contents.json:", json.load(open(args[-1]))["layout"], json.load(open(args[-1]))["status"])
after = json.load(open(card_path))
print("era_print in card before/after (TRIAL leaves the card file alone):", "era_print" in before, "era_print" in after)
print("OK")
