"""The judge grades the model against the photo the label was BUILT from (one clean copy), not against the pick
when the pick shows several cells (2026-10-05 22:38: it demanded text it read on the other cells in the pick)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run.py")).read()
i = src.index("verdict = inspect(shots, judge_photo")
block = src[i - 700:i]
check('label_source.json' in block and 'judge_photo = src["file"] if' in block, "the judge's photo is the label's source photo when it exists, else the pick")
check('inspect(shots, picked["file"]' not in src, "no judge call grades against the pick by right any more")
print(f"ALL {ok} PASS")
