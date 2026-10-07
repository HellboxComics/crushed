"""eBay listings as a source (Cody, 2026-10-07 00:32: "one easy search on ebay and I find every angle"): a listing is
ONE copy photographed from every side. Its main photo gets the careful look; a good listing lends ALL its photos to
the label; three wrong listings in a row stop the hunt. Checked with fake pages - no network."""
import os
import sys
import tempfile

W = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
import dossier as DS  # noqa: E402
import google_images as G  # noqa: E402
REAL_LISTINGS = G.listings

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


search = ('<a href="https://www.ebay.com/itm/257348577422?_skw=x">a</a> <a href="https://www.ebay.com/itm/257348577422">again</a>'
          '<a href="https://www.ebay.com/itm/123456789012">b</a>')
check(G.listing_ids(search) == ["257348577422", "123456789012"], "each listing on the search page once, in order")
item = ('<img src="https://i.ebayimg.com/images/g/hTMAAeSwfxlphozV/s-l500.webp"> <img src="https://i.ebayimg.com/images/g/hTMAAeSwfxlphozV/s-l64.jpg">'
        '<img src="https://i.ebayimg.com/images/g/AbCdEf123456/s-l140.jpg">')
check(G.listing_photos(item) == ["https://i.ebayimg.com/images/g/hTMAAeSwfxlphozV/s-l1600.jpg",
                                 "https://i.ebayimg.com/images/g/AbCdEf123456/s-l1600.jpg"], "every gallery photo once, at eBay's largest size")
check(DS.listing_query({"name": "Duracell Coppertop AA alkaline battery, circa 1998"}) == "Duracell Coppertop AA alkaline battery",
      "the eBay search is the item's name, without the era words")

# the hunt: listing 1 wrong, listing 2 this item (5 photos), listing 3 this item
def fake_listings(q, most=8, log=print):
    return [{"page": f"https://www.ebay.com/itm/{n}", "title": f"L{n}", "photos": [f"https://i.ebayimg.com/images/g/L{n}p{k}/s-l1600.jpg" for k in range(5)]}
            for n in (1, 2, 3)]


G.listings = fake_listings


def fake_dl(url, d):
    f = os.path.join(d, url.split("/g/")[1].split("/")[0] + ".jpg")
    Image.new("RGB", (64, 64)).save(f)
    return f


DS._download = fake_dl
looked = []


def fake_careful(dos, use, log=print, only=None):
    for p in only:
        looked.append(os.path.basename(p["file"]))
        exact = "L1p" not in p["file"]
        p.update(labeled=True, match="exact" if exact else "wrong", years=[1998, 1998], quality=7,
                 faces=[{"face": "label", "box": [0.1, 0.1, 0.9, 0.9]}], items=1)


DS.careful_looks = fake_careful
quick_seen = []


def fake_quick(dos, quick, log=print):
    for p in dos["photos"]:
        if "quick" not in p:
            quick_seen.append(os.path.basename(p["file"]))
            p["quick"] = {"same_item": not p["file"].endswith("p4.jpg"), "kind": "photo", "product_shown": "a 9V pack"}


DS.quick_look = fake_quick
DS.plan = lambda dos: ({"label": {"photo": None}}, [])
dos = {"cid": "x_aa", "route": "round", "identity": {"name": "Duracell Coppertop AA, circa 1998", "years": [1995, 1999]},
       "photos": [], "searches": [], "faces": {}, "gaps": []}
os.makedirs(os.path.join(W, "dossier"), exist_ok=True)
said = []
new = DS.hunt_listings(dos, "x_aa", "judge", log=said.append)
check(looked == ["L1p0.jpg", "L2p0.jpg", "L3p0.jpg"], f"only each listing's main photo gets the careful look ({looked})")
check(len(quick_seen) == 15, f"every photo of every listing gets the quick look ({len(quick_seen)})")
check(new == 6, f"the two good listings lend their other photos - all but the one the quick look says is not the item ({new})")
src = {os.path.basename(p["file"]) for p in DS._round_sources(dos)}
check("L2p3.jpg" in src and "L3p4.jpg" not in src and not any(s.startswith("L1") for s in src), "a good listing's photos are label sources; a wrong one's are not")
check(all(p.get("listing") for p in dos["photos"]) and dos["listings_hunted"] == DS.LISTINGS, "each photo keeps its listing; the hunt is recorded")
check(DS.hunt_listings(dos, "x_aa", "judge", log=said.append) == 0, "once per version")
# three wrong listings in a row: stop
dos2 = dict(dos, photos=[], listings_hunted=None)
looked.clear()
G.listings = lambda q, most=8, log=print: [{"page": f"p{n}", "title": "", "photos": [f"https://i.ebayimg.com/images/g/L1p{n}x/s-l1600.jpg"]} for n in range(6)]
DS.hunt_listings(dos2, "x_aa", "judge", log=said.append)
check(len(looked) == 3 and any("three eBay listings" in x for x in said), "three wrong listings in a row and the eBay hunt stops")
opened = []
G._open = lambda url, scroll=True, js=None, log=print, typed=None: (opened.append(url) or ("", ""))
REAL_LISTINGS("duracell powercheck aa", log=lambda *a: None)
check(len(opened) == 2 and "LH_Sold=1" in opened[1] and "LH_Sold" not in opened[0], f"eBay is searched for sale AND sold ({opened})")
check(DS.hunt_due({"listings_hunted": None, "around_hunted": DS.VERSION}), "an item hunted before eBay was added still gets the eBay hunt")
src = open(DS.__file__).read()
check(src.index("hunt_listings(dos, cid, use, log)\n") < src.index("    hunt_faces(dos, cid, need, log)"), "the dossier hunts eBay first, before the image searches")
print(f"ALL {ok} PASS")
