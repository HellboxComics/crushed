"""The label notices what it lacks (what every label of its kind carries) and finds it in more photos of the item:
every line of a flat/peeled label of this very item, only the missing parts from any other photo, never a second
date code, never a different product line, every word with its receipt."""
import os
import sys
import tempfile

sys.path.insert(0, "/home/claude/crushed/library")
import labelparts as LP
from PIL import Image

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


d = tempfile.mkdtemp()
files = {}
for n in ("flat", "back", "other_line", "too_late", "pick"):
    files[n] = os.path.join(d, n + ".jpg")
    Image.new("RGB", (600, 400)).save(files[n])
q = lambda **k: dict({"same_line": True, "same_item": True, "kind": "photo", "years": [1996, 2001], "face": "back",
                      "useful": 5}, **k)
dos = {"identity": {"years": [1990, 1999], "year": 1998, "brand": "Duracell", "line": "PowerCheck"},
       "picked": files["pick"],
       "photos": [{"file": files["pick"], "quick": q()},
                  {"file": files["other_line"], "quick": q(same_line=False)},
                  {"file": files["too_late"], "quick": q(years=[2015, 2020])},
                  {"file": files["back"], "quick": q(kind="photo"), "url": "https://example.com/b.jpg"},
                  {"file": files["flat"], "quick": q(kind="flat"), "url": "https://example.com/f.jpg"}]}
reads = {files["flat"]: ["DURACELL", "SIZE AA BATTERY", "PRESS DOTS TO TEST", "MN 1500 LR6 1.5 VOLTS",
                         "CAUTION: DO NOT CONNECT IMPROPERLY", "BEST IF INSTALLED BY: MAR 2003"],
         files["back"]: ["Made in U.S.A.", "SOME AD COPY"],
         files["other_line"]: ["CAUTION: A DIFFERENT PRODUCT"], files["too_late"]: ["Made in China"]}
seen = []
read = lambda pngs: (seen.extend(pngs) or [w for p in pngs for w in reads.get(p, [])])
words = ["DURACELL", "DURACELL® POWERCHECK™", "BEST IF INSTALLED BY:", "JAN 2001"]
check({e["what"].split(" (")[0] for e in LP.missing(words, LP.expected("cylindrical_cell"))} ==
      {"the size", "the model numbers", "the voltage", "a caution line", "where it was made"},
      "it knows what its label lacks (size, model numbers, voltage, caution, where it was made)")
added, receipts, still = LP.find("t", dos, words, "cylindrical_cell", "stand-in", "stand-in", read, log=print, web=False)
check("SIZE AA BATTERY" in added and "MN 1500 LR6 1.5 VOLTS" in added and "CAUTION: DO NOT CONNECT IMPROPERLY" in added,
      f"found on the flat label: {added}")
check("PRESS DOTS TO TEST" in added, "every line of a flat label of this very item counts")
check(not any("MAR 2003" in a for a in added), "a second date code never replaces the item's own")
check("Made in U.S.A." in added and "SOME AD COPY" not in added, "from another photo only the missing part")
check(files["other_line"] not in seen and files["too_late"] not in seen and files["pick"] not in seen,
      "never a different product line, never far outside the era")
check(not still and all(r["photo"] and r["url"] for r in receipts), f"nothing missing now, every word with its receipt")
print(f"\n{ok} checks passed")
