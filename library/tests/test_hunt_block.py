"""The photo hunt and a Google block (2026-10-04): a captcha is never 'a search with no results' - but a hunt
that already searched for every side it meant to search is not thrown away because the NEXT search was blocked.
The Duracell ran 11 of 12 searches (5+ for each end), hit a captcha on the 12th, and the whole dossier was marked
incomplete; every retry did the same. Now: incomplete only when a needed side was never searched at all."""
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dossier as DS  # noqa: E402
import google_images as G  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def fresh():
    return {"photos": [], "searches": [], "route": "round", "family_lib": "general",
            "identity": {"name": "Acme Alkaline AA", "brand": "Acme", "line": "Acme Alkaline", "variant": "AA",
                         "year": 1998, "years": [1995, 1999], "sisters": []}}


DS.save = lambda dos: None
plan = DS.queries(fresh()["identity"], "round", ["top", "bottom"], (), None)
faces = [f for f, _ in plan]
check(len(plan) >= 4 and {"top", "bottom"} <= set(faces), f"the plan searches both ends ({len(plan)} searches: {faces[:6]})")


def google_that_blocks_after(n):
    calls = [0]

    def fake(q, most=30, min_side=500, log=print):
        calls[0] += 1
        if calls[0] > n:
            raise G.Captcha("Google Images asks a person to tick 'I'm not a robot' in the reference browser on the Mac")
        return []                                           # a real search, nothing worth keeping
    return fake, calls


# 1. tonight's case: every end was searched, then the block -> the hunt counts, the item goes on
first_bottom = faces.index("bottom")
both_done = max(faces.index("top"), first_bottom) + 1
G.search_full, calls = google_that_blocks_after(both_done)
dos = fresh()
DS.hunt_faces(dos, "acme_aa", ["top", "bottom"], log=lambda *a: None)
check("hunt_incomplete" not in dos and len(dos["searches"]) == both_done,
      f"a block after both ends were searched does not void the hunt ({len(dos['searches'])} searches kept)")

# 2. the block comes before one end was ever searched -> incomplete, tried again later
G.search_full, calls = google_that_blocks_after(first_bottom if faces[0] == "top" else 0)
dos = fresh()
DS.hunt_faces(dos, "acme_aa", ["top", "bottom"], log=lambda *a: None)
check(dos.get("hunt_incomplete", "").startswith("Google Images asks a person"),
      "a block before a needed side was searched at all leaves the hunt incomplete")

# 3. a block on the very first search -> incomplete (never 'a hunt with no results')
G.search_full, calls = google_that_blocks_after(0)
dos = fresh()
DS.hunt_faces(dos, "acme_aa", ["top", "bottom"], log=lambda *a: None)
check(dos.get("hunt_incomplete") and not dos["searches"], "a block on the first search: nothing recorded, incomplete")

# 4. no block at all -> clean
G.search_full, calls = google_that_blocks_after(999)
dos = fresh()
DS.hunt_faces(dos, "acme_aa", ["top", "bottom"], log=lambda *a: None)
check("hunt_incomplete" not in dos and len(dos["searches"]) == len(plan), "no block: every planned search runs")

print(f"ALL {ok} PASS")
