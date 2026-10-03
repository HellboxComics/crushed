"""Smoke test (crash test only, generic answers): the dossier for a round item (Duracell AA, measured master) and a
circuit card (3dfx Voodoo2, pcb route), with Google returning nothing and the model giving plain answers."""
import json
import os
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
os.environ["CRUSHED_REMASTER_WORK"] = SCR + "/mine_work"
LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
import vet  # noqa: E402
import google_images  # noqa: E402
import websearch  # noqa: E402
import dossier as DS  # noqa: E402
import eraprint  # noqa: E402

ID = {"duracell_coppertop_aa_1998": {"brand": "Duracell", "line": "Coppertop", "variant": "AA", "count": "",
                                      "size_text": "", "kind": "object", "food": False, "sisters": ["AAA", "C", "D"]},
      "3dfx_voodoo2_12mb_1998": {"brand": "3dfx", "line": "Voodoo2", "variant": "12 MB PCI", "count": "",
                                 "size_text": "", "kind": "object", "food": False, "sisters": ["8 MB"]}}
cur = {}


def ask(model, text, images, think=True, side=1280):
    if text.startswith("[identity]"):
        return dict(ID[cur["cid"]])
    if text.startswith("[quick]"):
        return {"face": "label" if cur["cid"].startswith("dura") else "top", "product_shown": "", "same_line": True,
                "same_item": True, "kind": "photo", "era": "1998", "useful": 5}
    if text.startswith("[label]"):
        f = "label" if cur["cid"].startswith("dura") else "top"
        return {"faces": [{"face": f, "box": [0.1, 0.1, 0.9, 0.9], "straight_on": True, "turn": 0}], "match": "exact",
                "product_shown": "", "years": [1998, 1998], "quality": 7, "elements": []}
    if text.startswith("[panel-text]"):
        return {}
    raise RuntimeError(text[:50])


vet.ask = ask
vet.model = lambda: "m"
vet.quick_model = lambda: None
google_images.search_full = lambda q, most=30, min_side=500, log=print: []
websearch.search = lambda q, n=8, log=None, browser=True: []
pick = SCR + "/mine_work/library/duracell_coppertop_aa_1998/view_000.png"
for cid in ID:
    cur["cid"] = cid
    card = json.load(open(SCR + f"/mine_work/cards/{cid}.json"))
    if os.path.exists(DS.path(cid)):
        os.remove(DS.path(cid))
    d = DS.build(cid, card, {"file": pick}, log=lambda *a: None)
    print(cid, d["route"], {F: e["source"] for F, e in d["faces"].items()}, "searches", len(d["searches"]),
          "facts:", {k: f["status"] for k, f in d["facts"].items()})
    print("   gaps:", d["gaps"][:4])
    print("   printable:", {k: v for k, v in eraprint.from_dossier(d).items() if v})
    assert d["done"]
print("OK")
