"""dossier.build on poptarts_frosted_strawberry_1997 with the model and Google replaced by recorded answers (web
pages are read for real), then the box faces built from its plan and the carton contents written."""
import collections
import json
import os
import shutil
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
os.environ["CRUSHED_REMASTER_WORK"] = SCR + "/mine_work"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.join(os.path.dirname(LIB), "ai", "remaster"))
sys.path.insert(0, SCR)
import recorded as R  # noqa: E402
import vet  # noqa: E402
import google_images  # noqa: E402
import websearch  # noqa: E402
import dossier as DS  # noqa: E402

CID = "poptarts_frosted_strawberry_1997"
W = os.environ["CRUSHED_REMASTER_WORK"]
card = json.load(open(os.path.join(W, "cards", CID + ".json")))
cands = json.load(open(os.path.join(W, "library", CID, "candidates.json")))["files"]
picked = cands[0]                                    # ~/.hellbox/picks.json says pick 1
IDX = {b: i for i, b in enumerate(R.B)}
calls = collections.Counter()
unexpected = []


def fake_ask(model, text, images, think=True, side=1280):
    b = os.path.basename(images[0]) if images else ""
    i = IDX.get(b)
    if text.startswith("[identity]"):
        calls["identity"] += 1
        return dict(R.IDENTITY)
    if text.startswith("[quick]"):
        calls["quick"] += 1
        return R.quick(i) if i is not None else {"face": "none", "useful": 0}
    if text.startswith("[label]"):
        calls["careful look"] += 1
        if i in R.LABEL:
            return json.loads(json.dumps(R.LABEL[i]))
        unexpected.append((i, b))
        return {"faces": [], "match": "wrong", "quality": 0, "elements": []}
    if text.startswith("[panel-text]"):
        calls["panel read"] += 1
        return json.loads(json.dumps(R.PANEL.get(i, {})))
    if "brand name and product name lockup" in text:
        calls["logo box"] += 1
        return dict(R.LOGO_BOX)
    if "main product picture" in text:
        calls["picture box"] += 1
        return dict(R.PHOTO_BOX)
    raise RuntimeError("no recorded answer for: " + text[:80])


searches = []


def fake_google(q, most=30, min_side=500, log=print):
    searches.append(q)
    calls["google"] += 1
    return R.google(q)[:most]


def fake_web(q, n=8, log=None, browser=True):
    calls["web search"] += 1
    if log:
        log(f"[web] (recorded) '{q}'")
    return R.web(q)[:n]


vet.ask = fake_ask
vet.model = lambda: "qwen3.8:27b-q8_0"
vet.quick_model = lambda: "qwen3.6:35b"
google_images.search_full = fake_google
websearch.search = fake_web

# a clean start for this test (only this test's own output)
for p in (DS.path(CID),):
    if os.path.exists(p):
        os.remove(p)
shutil.rmtree(os.path.join(DS.DIR, "old"), ignore_errors=True)

dos = DS.build(CID, card, picked, log=print)
print("\n================ RESULT ================")
print("calls:", dict(calls))
print("unexpected careful looks:", unexpected)
print("searches run:", len(dos["searches"]))
for s in dos["searches"]:
    print(f"   [{s['for']}] {s['q']}  -> {s['n']} photos")
print("identity:", json.dumps({k: dos["identity"][k] for k in ("name", "count", "size_text", "food", "years", "sisters")}))
print("\nFACE PLAN")
for F, e in dos["faces"].items():
    print(f"  {F:7s} {e['source']:15s} {os.path.basename(e['photo'] or '-'):20s} match={e.get('match')} "
          f"swap={e.get('swap')} alt={[os.path.basename(a) for a in e.get('alternates', [])]}"
          f"{' layout_from=' + os.path.basename(e['layout_from']) if e.get('layout_from') else ''}  | {e['note']}")
    for m in e["must_show"][:6]:
        print(f"           must show: {m['what']}: {str(m['text'])[:70]} (item-specific {m['item_specific']})")
print("\nFACTS")
for k, f in dos["facts"].items():
    print(f"  {k:12s} {f['status']:14s} value={json.dumps(f['value'])[:110]}")
    for s in f["sources"][:5]:
        print(f"      receipt: {s['kind']} {s.get('url') or ''} {os.path.basename(s.get('file') or '')} | {s['quote'][:90]}")
    if f.get("checks"):
        print("      checks:", json.dumps(f["checks"])[:300])
    if f.get("reference"):
        print("      reference (not printed):", json.dumps(f["reference"]["source"])[:200], f["reference"]["years"])
print("\nGAPS")
for g in dos["gaps"]:
    print("  -", g)
assert not unexpected, unexpected
assert dos["facts"]["upc"]["value"] == "038000317101" and dos["facts"]["upc"]["status"] == "verified"
assert dos["faces"]["front"]["source"] == "exact_photo"
assert all(os.path.exists(p["file"]) for p in dos["photos"])

# ---- reused next time; a Redo sets it aside and keeps every photo
n_photos = len(dos["photos"])
again = DS.build(CID, card, picked, log=lambda *a: print("  (2nd)", *a))
assert again["made_at"] == dos["made_at"], "the finished dossier is reused"
calls.clear()
redo = DS.build(CID, card, picked, log=lambda *a: None, redo=True)
print(f"\nREDO: photos before {n_photos}, after {len(redo['photos'])}; set aside: {os.listdir(os.path.join(DS.DIR, 'old'))}; "
      f"new searches {len(redo['searches'])}: {[s['q'] for s in redo['searches']][:4]}...; calls {dict(calls)}")
assert len(redo["photos"]) >= n_photos
assert {p["file"] for p in dos["photos"]} <= {p["file"] for p in redo["photos"]}, "a Redo never loses a find"
json.dump(dos, open(DS.path(CID), "w"), indent=1)      # keep the first one for the build test below
print("\nOK")
