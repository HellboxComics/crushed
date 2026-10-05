"""Each printed line is listed once (2026-10-05 13:52: the Duracell's label words were read off 4 pictures and
joined by exact spelling only - 37 'words', every line printed two or three times, the model scrambled). The data
below is that build's words.json as it was, with a per-picture record like run.label_words makes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import review  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


WORDS = ["DURACELL®", "Patented", "DURACELL", "DURACELL® POWERCHECK™", "DURACELL INC..", "Bethel, CT 06801",
         "BEST IF INSTALLED BY:", "JAN 2001", "TEST", "100%", "Test", "at", "1500", "PRESS DOTS", "TO TEST", "ALT",
         "- Test at 70°F/21°C", "DURACE M", "MN 1500 LAS 15 VOLIS", "SIZE", "BATTERY", "LR6", "MAY", "MAR", "SIZE AA",
         "MAY EXPLODE OR LEAK.", "CHARGE OR DISPOSE OF IN FIES", "CAUTION: DO NOT CONNECT UM", "MN 1500", "Ma",
         "Test at 70°F/21°C", "DURACELL INC.,", "MN 1500 LRS 15 VOLTS", "Patented DURACELL INC. Bethel, CT 06801",
         "BEST IF INSTALLED BY: JAN 2001", "ALKALINE 1.5 Volts", "ALKALINE 1,5 Volts"]
BY_PNG = {
    # the copper side: the big logo on its own, the PowerCheck line, the meter
    "side1.png": ["DURACELL", "DURACELL® POWERCHECK™", "TEST", "100%", "PRESS DOTS", "TO TEST", "ALKALINE 1.5 Volts"],
    # the black side, read in pieces
    "side2.png": ["DURACELL®", "Patented", "DURACELL INC..", "Bethel, CT 06801", "BEST IF INSTALLED BY:", "JAN 2001",
                  "Test", "at", "- Test at 70°F/21°C", "MN 1500 LAS 15 VOLIS", "SIZE", "SIZE AA", "BATTERY", "LR6",
                  "MAY", "MAY EXPLODE OR LEAK.", "CHARGE OR DISPOSE OF IN FIES", "CAUTION: DO NOT CONNECT UM",
                  "ALT", "MAR", "Ma", "1500", "MN 1500"],
    # the cut-outs: the same lines read whole, and once more with a misread
    "item1.png": ["DURACE M", "Test at 70°F/21°C", "DURACELL INC.,", "MN 1500 LRS 15 VOLTS", "BATTERY",
                  "Patented DURACELL INC. Bethel, CT 06801", "BEST IF INSTALLED BY: JAN 2001"],
    "item2.png": ["DURACELL", "MN 1500 LRS 15 VOLTS", "Test at 70°F/21°C", "Patented DURACELL INC. Bethel, CT 06801",
                  "BEST IF INSTALLED BY: JAN 2001", "ALKALINE 1,5 Volts"],
}

kept, folded = review.one_per_print(WORDS, BY_PNG)
print("kept:", kept)
print("folded:", folded)
import re  # noqa: E402
norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())

# A. one spelling per print
check(len([k for k in kept if norm(k) == "duracell"]) == 1, "DURACELL / DURACELL(R) is one line")
check("DURACE M" not in kept and folded.get("DURACE M") == "DURACELL", "the misread 'DURACE M' folds into DURACELL")
check(not any(norm(k).startswith("mn1500") and len(norm(k)) > 6 for k in kept) and "MN 1500" in kept and "LR6" in kept,
      "both garbled readings of the model line go (one as a second spelling, one as a smear); MN 1500 and LR6 carry it")
check(len([k for k in kept if norm(k).startswith("alkaline")]) == 1, "ALKALINE 1.5 / 1,5 Volts is one line")
check(len([k for k in kept if "70f21c" in norm(k)]) == 1, "'Test at 70F' with and without the dash is one line")
check(len([k for k in kept if norm(k) == "duracellinc"]) <= 1, "DURACELL INC.. / INC., is one line")

# C. pieces seen only beside their line fold into it; a piece seen on its own stays
check("Test" not in kept and "at" not in kept, "'Test' and 'at' (seen only beside 'Test at 70F') fold into the line")
check("1500" not in kept and "SIZE" not in kept and "MAY" not in kept, "'1500', 'SIZE', 'MAY' fold into their lines")
check("DURACELL" in kept and "DURACELL® POWERCHECK™" in kept,
      "the DURACELL logo, seen on its own on the copper side, stays beside 'DURACELL(R) POWERCHECK'")
check("TEST" in kept, "'TEST' (its own print on the meter) stays beside 'TO TEST'")

# B. a glued copy is dropped; the facts stay exactly once
date = [k for k in kept if "jan2001" in norm(k) or "installedby" in norm(k)]
check(sum(1 for k in kept if "jan2001" in norm(k)) == 1 and sum(1 for k in kept if "installedby" in norm(k)) == 1,
      f"the date line's facts appear once ({date})")
maker = [k for k in kept if "bethel" in norm(k) or "patented" in norm(k)]
check(sum(1 for k in kept if "bethel" in norm(k)) == 1 and sum(1 for k in kept if "patented" in norm(k)) == 1,
      f"the maker's line facts appear once ({maker})")
check(len(kept) <= 25 and len(folded) >= 12, f"37 readings came down to {len(kept)} lines ({len(folded)} folded)")
# nothing real was lost: every fact token of the real label is still printable
have = {t for k in kept for t in norm(k).split()} | {norm(k) for k in kept}
alltoks = " ".join(norm(t) for k in kept for t in k.split())
for must in ("duracell", "powercheck", "100", "mn1500", "lr6", "bethel", "06801", "jan2001", "sizeaa", "explode", "alkaline"):
    check(must in alltoks.replace(" ", ""), f"the fact '{must}' is still there")

# the rule is idempotent and harmless on a clean list
again, f2 = review.one_per_print(kept, BY_PNG)
check(again == kept and not f2, "running it again changes nothing")
clean = ["DURACELL", "SIZE AA", "MN 1500", "LR6", "1.5 VOLTS"]
check(review.one_per_print(clean)[0] == clean, "a clean list with no picture record is untouched")
# with no picture record, a piece is never dropped (no evidence), but a glued copy still is
k3, f3 = review.one_per_print(["BEST IF INSTALLED BY:", "JAN 2001", "BEST IF INSTALLED BY: JAN 2001", "MN 1500"])
check("BEST IF INSTALLED BY: JAN 2001" not in k3 and "JAN 2001" in k3 and "MN 1500" in k3,
      "without pictures: the glued copy goes, the pieces stay")


# D. a smear (2026-10-05 14:20, from the run's own log): two reads agreed on 'MN 1500 LAS 15 VOLIS' off a blurry
# strip, while the other picture confirmed the clean pieces. The smear goes; the pieces carry its facts.
W2 = ["MN 1500 LAS 15 VOLIS", "100%", "DURACELL", "JAN 2001", "SIZE AA", "ALKALINE 1.5 Volts", "MN1500", "LR6",
      "MN 1500", "DURACELL® POWERCHECK™", "CAUTION: DO NOT CONNECT UM", "CHARGE OR DISPOSE OF IN FIES"]
P2 = {"side2.png": ["MN 1500 LAS 15 VOLIS", "CAUTION: DO NOT CONNECT UM", "CHARGE OR DISPOSE OF IN FIES"],
      "item2.png": ["100%", "DURACELL", "JAN 2001", "SIZE AA", "ALKALINE 1.5 Volts", "MN1500", "LR6", "MN 1500",
                    "DURACELL® POWERCHECK™"]}
k4, f4 = review.one_per_print(W2, P2)
check("MN 1500 LAS 15 VOLIS" not in k4 and f4.get("MN 1500 LAS 15 VOLIS", "").startswith("a smear of"),
      f"the smear goes: {f4.get('MN 1500 LAS 15 VOLIS')}")
check("MN 1500" in k4 and "LR6" in k4 and "ALKALINE 1.5 Volts" in k4, "the clean pieces that carry its facts stay")
check("CAUTION: DO NOT CONNECT UM" in k4 and "CHARGE OR DISPOSE OF IN FIES" in k4,
      "a line read only once, with words no other line carries, is NOT called a smear (it is the only reading)")
# the spelling tie: 'LRS 15 VOLTS' vs 'LAS 15 VOLIS', one picture each - the one whose words other readings carry wins
k5, f5 = review.one_per_print(["MN 1500 LAS 15 VOLIS", "MN 1500 LRS 15 VOLTS", "1.5 VOLTS"],
                              {"a.png": ["MN 1500 LAS 15 VOLIS"], "b.png": ["MN 1500 LRS 15 VOLTS", "1.5 VOLTS"]})
check("MN 1500 LRS 15 VOLTS" in k5 and "MN 1500 LAS 15 VOLIS" not in k5, f"on a tie the better-supported spelling wins ({k5})")

k6, f6 = review.one_per_print(["DURACELL", "DURACELL® POWERCHECK™", "SIZE", "SIZE AA"],
                              {"a.png": ["DURACELL", "DURACELL® POWERCHECK™", "SIZE", "SIZE AA"]})
check("DURACELL" in k6 and "SIZE" not in k6, "a long word read as its own line (the logo) stays even when only seen beside a longer line; a short piece folds")

print(f"ALL {ok} PASS")
