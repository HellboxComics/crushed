"""A round label short of real pixels most of the way around gets ONE hunt aimed at its other side, then the stitch
again (2026-10-06 10:21: 4 clean exact photos, all the same side, 32% real). Checked with a fake image search."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
import dossier as DS  # noqa: E402
import google_images as G  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


asked = []
G.search_full = lambda q, most=12, min_side=500, log=print: (asked.append(q) or [{"url": f"https://x.example/{len(asked)}_{i}.jpg", "w": 900, "h": 700, "page": "", "title": ""} for i in range(2)])
dl = []
def fake_dl(url, d):
    f = os.path.join(d, "p" + str(abs(hash(url)) % 10**8) + ".jpg")
    Image.new("RGB", (64, 64), (90, 60, 30)).save(f)
    dl.append(f)
    return f
DS._download = fake_dl
DS.quick_look = lambda dos, quick, log=print: None
DS.careful_looks = lambda dos, use, log=print, only=None: None
DS.plan = lambda dos: ({"label": {"photo": None}}, [])
dos = {"cid": "x_aa", "route": "round", "identity": {"brand": "Duracell", "line": "coppertop aa", "year": 1998, "years": [1995, 1999]},
       "photos": [], "searches": [{"q": "duracell coppertop aa 1998 wrapper", "n": 3}], "faces": {}, "gaps": []}
os.makedirs(os.path.join(W, "dossier"), exist_ok=True)
new = DS.hunt_around(dos, "x_aa", log=lambda *a: None, use="judge", quick="quick", coverage=0.32)
check(new == 12 and len(asked) == 6, f"six searches aimed at the other side, {new} new photos taken in ({len(asked)} searches)")
check(all(("back" in q or "other side" in q or "unrolled" in q or "rolling" in q or "lot" in q or "wrapper" in q) for q in asked), f"the searches ask for the other side: {asked[:3]}")
check("duracell coppertop aa 1998 wrapper" not in asked, "a search already run is not run again")
check(dos.get("around_hunted") == DS.VERSION and all(s.get("for") == "label (other side)" for s in dos["searches"][1:]), "recorded on the dossier with its version and its purpose")
check(DS.hunt_around(dos, "x_aa", log=lambda *a: None, use="judge", quick="quick", coverage=0.32) == 0, "once per dossier version")
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run.py")).read()
check("if seen_around < 0.7 and dos and dos.get(\"around_hunted\") != DS.VERSION" in src, "the label step hunts around when real pixels cover under 70%")
print(f"ALL {ok} PASS")
