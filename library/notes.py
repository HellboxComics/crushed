"""YOUR NOTES ON AN ITEM: a direction from you that your AI follows for that item - "use the blue box design",
"the 1999 version with the hologram", "it's the 12-count box". Kept in ~/crushed-render/remaster/notes/<item>.json:

    {"note": "Build the blue box design of this item, from inside its era.", "repick": true, "at": ..., "by": "Cody"}

What a note does:
  - your AI reads it everywhere it decides something about the item: which photos are the right version (the
    ranking and the pick), what kind of thing it is (family), what it knows about the item (the dossier), and how
    it breaks it into parts;
  - it writes new searches for it (so the hunt looks for that version);
  - "repick": true sets aside the old pick and the photos it was chosen from (moved to remaster/_set_aside/, never
    deleted) so the hunt and the pick start over for the version the note asks for. Done once per note.

    notes.add(cid, "Build the blue box design", repick=True)     # from a phone message or by hand
    n = notes.get(cid)                                           # {"note": ...} or {}
"""
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
DIR = os.path.join(WORK, "notes")

SEARCH_Q = """We are finding photos of one exact real product version. The catalog item: {product} ({year}; the same
era is {y0} to {y1}). The owner's note about which version to build: "{note}".
Write 6 short Google Images searches (3 to 7 words each) that would find clear photos of THAT version - its front,
and its back and sides. Vary the words the way collectors and sellers describe it (vintage, year, box, back, side).
Answer ONLY JSON: {{"searches": ["...", "..."]}}"""


def _path(cid):
    return os.path.join(DIR, cid + ".json")


def get(cid):
    try:
        return json.load(open(_path(cid)))
    except Exception:
        return {}


def add(cid, note, repick=False, by="Cody"):
    os.makedirs(DIR, exist_ok=True)
    n = {"note": note.strip(), "repick": bool(repick), "at": time.time(), "by": by, "applied": None}
    tmp = _path(cid) + ".tmp"
    json.dump(n, open(tmp, "w"), indent=1)
    os.replace(tmp, _path(cid))
    return n


def text(cid):
    return get(cid).get("note", "")


def searches(card, note, use, log=print):
    """New searches your AI writes for the version the note asks for."""
    if not (use and note):
        return []
    import vet as V
    y = card.get("year") or 0
    body = {"model": use, "stream": False, "format": "json", "think": False, "options": {"temperature": 0.3},
            "messages": [{"role": "user", "content": SEARCH_Q.format(product=card.get("product"), year=y or "?",
                                                                   y0=y - 3 if y else "?", y1=y + 3 if y else "?",
                                                                   note=note)}]}
    try:
        txt = V._call("/api/chat", body).get("message", {}).get("content", "{}")
        got = json.loads(re.search(r"\{.*\}", txt, re.S).group(0)).get("searches") or []
    except Exception as e:
        log(f"[note] could not write searches for the note: {e}")
        return []
    return [str(q)[:80] for q in got if str(q).strip()][:6]


def apply_repick(cid, out_dir, hb, log=print):
    """Once per note: the old pick, its photo choices and rankings go to remaster/_set_aside/ so the hunt and the pick
    start over for the version the note asks for. Returns True when it set things aside."""
    n = get(cid)
    if not n.get("repick") or n.get("applied"):
        return False
    aside = os.path.join(WORK, "_set_aside", f"{cid}-note-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(aside, exist_ok=True)
    moved = []
    for name in ("candidates.json", "vetted.json", "shown.json", "pick_sheet.jpg"):
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            shutil.move(p, os.path.join(aside, name))
            moved.append(name)
    for k in os.listdir(out_dir) if os.path.isdir(out_dir) else []:
        if k.startswith("round_"):
            shutil.move(os.path.join(out_dir, k), os.path.join(aside, k))
    pf = os.path.join(hb, "picks.json")
    try:
        picks = json.load(open(pf))
    except Exception:
        picks = {}
    if cid in picks:
        json.dump({cid: picks[cid]}, open(os.path.join(aside, "old_pick.json"), "w"), indent=1)
        try:
            sys.path.insert(0, HERE)
            import run as R                                 # the locked read-modify-write helper, when there
            R.update_json(pf, lambda d: (d.pop(cid, None), d)[1])
        except Exception:
            picks.pop(cid, None)
            json.dump(picks, open(pf, "w"), indent=1)
        moved.append("your old pick")
    open(os.path.join(aside, "NOTE.txt"), "w").write(
        f"Set aside because of your note on {cid}: \"{n['note']}\" - the hunt and the pick start over for that "
        f"version. Nothing here is needed any more; delete it whenever you like.\n")
    n["applied"] = time.time()
    json.dump(n, open(_path(cid), "w"), indent=1)
    log(f"[note] {cid}: your note \"{n['note']}\" - set aside {', '.join(moved) or 'nothing'}; hunting that version")
    return True
