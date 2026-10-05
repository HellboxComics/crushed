"""A printed element the dossier read as ONE line is found on the model when it is printed as several lines placed
apart (2026-10-05 13:49: 'Patented DURACELL INC. Bethel, CT 06801' failed at 0.72 as one run while every word of it
was on the label, three lines apart). A missing or misspelled element still fails."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import measure as MS  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


want = "Patented DURACELL INC. Bethel, CT 06801"
apart = "DURACELL  SIZE AA  Patented  MN 1500 LR6  DURACELL INC.,  BEST IF INSTALLED BY  JAN 2001  Bethel, CT 06801  1.5 VOLTS"
f, s = MS.text_found(want, apart)
check(f and s >= 0.8, f"the maker's line, printed as three lines apart, is found ({s})")
f, s = MS.text_found(want, "DURACELL  SIZE AA  Patented  MN 1500 LR6  DURACELL INC.,  BEST IF INSTALLED BY  JAN 2001  Bethe1, CT 06801")
check(f, f"a letter read wrong off the curved render ('Bethe1') still counts ({s})")
f, s = MS.text_found(want, "DURACELL  SIZE AA  Patented  MN 1500 LR6  DURACELL INC.,  BEST IF INSTALLED BY  JAN 2001")
check(not f, f"with the city and zip missing it is NOT found ({s})")
f, s = MS.text_found("MN 1500", "DURACELL  SIZE AA  MN 1500  LR6")
check(f and s == 1.0, "a short element as one run still passes exactly")
f, s = MS.text_found("MN 1500", "DURACELL  SIZE AA  LR6")
check(not f, "a short element that is not there still fails")
f, s = MS.text_found("SIZE AA", "DURACELL  SIZE  AA  LR6")
check(f, "two short words a line apart are found (spacing never matters)")
print(f"ALL {ok} PASS")
