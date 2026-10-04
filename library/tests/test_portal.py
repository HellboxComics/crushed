"""The portal: a typed note reaches its item; a new object becomes an item with a researched size and goes first in
line; a size nobody can find is asked for, never guessed; his photo joins the item's hunt."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, "/home/claude/crushed/library")
import portal as P
import notes as NT
import vet
from PIL import Image

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


sent = []
P._reply = lambda t: sent.append(t)
photo = os.path.join(W, "mine.jpg")
Image.new("RGB", (800, 600), (90, 90, 90)).save(photo)
os.makedirs(P.DIR, exist_ok=True)
os.makedirs(os.path.join(W, "library"), exist_ok=True)
json.dump({"duracell_coppertop_aa_1998": {"step": "in line"}}, open(os.path.join(W, "library", "status.json"), "w"))
json.dump([{"id": 1, "text": "duracell: the 1999 version with the hologram", "photo": None},
           {"id": 2, "text": "Sony Walkman WM-FX101 from the 90s", "photo": photo},
           {"id": 3, "text": "a weird no-name thing", "photo": None}], open(P.INBOX, "w"))


def fake_ask(model, q, images, think=False, **k):
    if q.startswith("Someone typed"):
        if "WM-FX101 from the 90s" in q:
            return {"product": "Sony Walkman WM-FX101 cassette player, circa 1996", "year": 1996, "kind": "gadget",
                    "size_known_mm": None, "size_search": "Sony WM-FX101 dimensions", "is_note": False}
        return {"product": "No-name thing, circa 1998", "year": 1998, "kind": "other", "size_known_mm": None,
                "size_search": "no-name thing dimensions", "is_note": False}
    if q.startswith("We need the real size"):
        return {"size_mm": [112, 36, 91], "source": "Sony manual", "quote": "112 x 36 x 91 mm"} if "Walkman" in q \
            else {"size_mm": None, "source": "", "quote": ""}
    return {}


vet.ask = fake_ask
import websearch
websearch.search = lambda q, n=8, log=None, browser=True: [{"title": "Sony manual", "snippet": "112 x 36 x 91 mm"}]
got = P.process(log=print, model="stand-in")
check(("note", "duracell_coppertop_aa_1998") in got and NT.get("duracell_coppertop_aa_1998").get("note", "").startswith("the 1999"),
      "a typed note reaches its item")
its = P.items()
cid = "sony_walkman_wm_fx101_cassette_player_1996"
check(cid in its and its[cid]["size"] == [0.112, 0.036, 0.091] and "Sony manual" in its[cid]["size_source"],
      f"a new object becomes an item with a researched size and its source")
check(P.queue_first()[0] == cid, "and goes first in line")
found = json.load(open(os.path.join(W, "hunt", cid, "found.json")))
check(found and found[0]["source"] == "your phone", "his photo joins the item's hunt")
import cards
check(cards.catalog(cid)["product"].startswith("Sony Walkman"), "the card reads the portal item like a catalog item")
nn = "no_name_thing_1998"
check(nn in its and its[nn]["size"] is None and nn not in P.queue_first() and any("can't find its real size" in s for s in sent),
      "a size nobody can find is asked for, never guessed, and the item waits")
json.dump([{"id": 4, "text": f"{nn}: size 5 x 4 x 3 cm", "photo": None}], open(P.INBOX, "w"))
P.process(log=print, model="stand-in")
check(P.items()[nn]["size"] == [0.05, 0.04, 0.03] and P.queue_first()[0] == nn, "his size reply puts it first in line")
check(len(sent) == 4 and all(sent), f"one reply per message: {len(sent)}")
# every message is marked done the moment it is handled: running again replies to nothing (2026-10-04: a 'continue'
# skipped the save, so replies repeated and notes were rewritten each run)
P.process(log=print, model="stand-in")
check(len(sent) == 4, "run again: no message is handled twice")
print(f"\n{ok} checks passed")
