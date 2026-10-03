"""Your AI writes its own kit for a kind of thing it has never met: studied once, checked by code, used by every
later item of that kind; a one-photo organic guess is never the way a whole thing is built."""
import json
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, "/home/claude/crushed/library")
import kitmaker as KM
import kits
import families
import vet
from PIL import Image

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


photo = os.path.join(W, "p.jpg")
Image.new("RGB", (600, 600), (120, 120, 120)).save(photo)
asked = []
STUDIED = {"what": "a soft stuffed toy with a plastic face", "looks_like": ["teddy bear", "Beanie Baby"], "not": ["action figure"],
           "construction": "soft (sewn fabric, fur, foam)",
           "parts": [{"part": "fur body", "material": "plush_fur", "hard": False, "printed": False, "how": "sewn and stuffed"},
                     {"part": "eyes", "material": "molded_plastic", "hard": True, "printed": False, "how": "snapped in"},
                     {"part": "beak", "material": "molded_plastic", "hard": True, "printed": False, "how": "glued"},
                     {"part": "tush tag", "material": "fabric", "hard": False, "printed": True, "how": "sewn into the seam"},
                     {"part": "feet", "material": "fabric", "hard": False, "printed": False, "how": "sewn"}],
           "zones": [{"name": "body", "kind": "fabric", "typical": ["fur color", "pattern"], "expect": []},
                     {"name": "bottom", "kind": "form", "typical": ["the maker's molded name"],
                      "expect": [{"what": "the maker", "pattern": r"\bTIGER\b|\bHASBRO\b|\bMADE IN\b", "search": "bottom tag"}]}],
           "standard_sizes": False, "size_search": "", "side_words": {"back": ["back view"], "bottom": ["bottom", "underside"]},
           "views_needed": ["front", "back", "left", "right", "bottom"]}


def fake_ask(model, q, images, think=False, **k):
    asked.append(q)
    if q.startswith("[kit]"):
        return json.loads(json.dumps(STUDIED))
    if q.startswith("[family]"):
        return {"family": "organic_toy", "confidence": 4, "why": "fuzzy", "second": "general", "kind_name": "plush toy",
                "material_outside": "fur", "is_package": False}
    return {}


vet.ask = fake_ask
card = {"id": "furby_test", "product": "Furby gray with pink ears, circa 1998", "size": [0.12, 0.12, 0.15], "year": 1998}
kk, kit = KM.ensure("plush toy", card, photo, "stand-in", log=print)
check(kk == "plush_toy" and kit["builder"] == "assembly" and len(kit["parts"]) == 5, f"a new kind is studied and written: {kk}")
check("plush_toy" in kits.library()["families"] and "plush_toy" in families.library()["families"],
      "every part of the asset maker sees the learned kit")
n = len(asked)
kk2, _ = KM.ensure("Plush Toy", card, photo, "stand-in", log=print)
check(kk2 == "plush_toy" and len(asked) == n, "the next item of that kind uses it without studying again")
check(kits.typical(kit, "bottom") == ["the maker's molded name"] and kits.zones(kit)[0]["kind"] == "fabric",
      "its zones work like a hand-written kit's")
bad = json.loads(json.dumps(STUDIED))
bad["parts"][0]["material"] = "unobtainium"
bad["zones"][0]["kind"] = "hologram"
probs = KM.check(bad)
check(any("unobtainium" in p for p in probs) and any("hologram" in p for p in probs), f"a bad kit is caught by code: {probs}")
fl = families.classify(dict(card), photo, use="stand-in", log=print)
check(fl["family"] == "plush_toy", f"an unsure family answer with a kind name becomes the studied kit: {fl['family']}")
b, why = families.builder(families.get("organic_toy"))
check(b == "assembly", "a soft thing is built from its parts, never guessed whole from one photo")
print(f"\n{ok} checks passed")
