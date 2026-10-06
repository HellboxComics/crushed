"""Every credible photo of a round item lends its label real pixels - exact or same artwork, one copy or several
(each cell is a strip), nothing laid over it (Cody, 2026-10-06 10:37: "there is no front and back on a round
object... reference all credible sources for a complete image")."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dossier as DS  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


lab = lambda **k: dict({"labeled": True, "faces": [{"face": "label", "box": [0.1, 0.1, 0.9, 0.9]}], "quality": 6}, **k)
dos = {"route": "round", "photos": [
    lab(file="/p/exact1.jpg", match="exact", items=1, quality=7),
    lab(file="/p/three.jpg", match="exact", items=3, quality=8),                 # the pick: three cells, three ways
    lab(file="/p/sister_same.jpg", match="sister", same_artwork=True, items=1),  # a 2001 copy, same artwork
    lab(file="/p/sister_other.jpg", match="sister", same_artwork=False, items=1),
    lab(file="/p/wrong.jpg", match="wrong", items=1),
    {"file": "/p/unlooked.jpg", "labeled": False, "quick": {"same_item": True}},
]}
src = [p["file"] for p in DS._round_sources(dos)]
check("/p/three.jpg" in src and "/p/sister_same.jpg" in src and "/p/exact1.jpg" in src, f"several copies and a same-artwork copy count as sources ({src})")
check("/p/wrong.jpg" not in src and "/p/sister_other.jpg" not in src and "/p/unlooked.jpg" not in src, "a wrong item, other artwork or a photo never looked at does not")
check(src[0] == "/p/exact1.jpg", "a single clean exact copy comes first (the front's authority)")
check(DS.ROUND_SOURCES >= 12, f"the looks continue until {DS.ROUND_SOURCES} sources")
# label_views: an alternate with several copies has no box, so every cell unrolls
dos["faces"] = {"label": {"source": "exact_photo", "photo": "/p/exact1.jpg", "view": {"box": [0.1, 0.1, 0.9, 0.9]},
                          "alternates": ["/p/three.jpg", "/p/sister_same.jpg"]}}
real = os.path.exists
os.path.exists = lambda p: True
views = DS.label_views(dos, {"file": "/p/three.jpg"}, want=20)
os.path.exists = real
by = {v["file"]: v for v in views}
check(by["/p/three.jpg"]["box"] is None and by["/p/exact1.jpg"]["box"] == [0.1, 0.1, 0.9, 0.9], "the front keeps its box; a many-cell alternate has none (every cell is a strip)")
# a cached dossier whose saved alternates predate the rule still gets every source
dos["faces"]["label"]["alternates"] = []
os.path.exists = lambda p: True
views2 = DS.label_views(dos, {"file": "/p/three.jpg"}, want=20)
os.path.exists = real
check({"/p/three.jpg", "/p/sister_same.jpg"} <= {v["file"] for v in views2}, "with no saved alternates the label still reads every source from the rule")
print(f"ALL {ok} PASS")
