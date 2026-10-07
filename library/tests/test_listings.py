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
REAL_SEARCH = G.search_listings

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

# the hunt: two searches (catalog name, printed name), listings ranked by title words; 1 wrong, 2 and 3 this item
searched = []


def fake_search(q, most=24, log=print):
    searched.append(q)
    return [{"id": str(n), "page": f"https://www.ebay.com/itm/{n}", "title": t} for n, t in
            ((9, "Duracell PowerCheck AAA batteries"), (1, "Duracell Coppertop AA battery lot"), (2, "Duracell Coppertop AA battery 1998"),
             (3, "Duracell Coppertop AA alkaline battery"))]


G.search_listings = fake_search
G.listing = lambda page, log=print: [f"https://i.ebayimg.com/images/g/L{page.rsplit('/', 1)[1]}p{k}/s-l1600.jpg" for k in range(5)]


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
dos = {"cid": "x_aa", "route": "round", "identity": {"name": "DURACELL POWERCHECK", "years": [1995, 1999]},
       "inputs": {"product": "Duracell Coppertop AA alkaline battery, circa 1998"},
       "photos": [], "searches": [], "faces": {}, "gaps": []}
os.makedirs(os.path.join(W, "dossier"), exist_ok=True)
said = []
new = DS.hunt_listings(dos, "x_aa", "judge", log=said.append)
check(searched == ["DURACELL POWERCHECK", "Duracell Coppertop AA alkaline battery"], f"eBay searched by the printed name and the catalog's name ({searched})")
check(looked == ["L3p0.jpg", "L9p0.jpg", "L1p0.jpg", "L2p0.jpg"], f"the listing whose title shares most words is opened first; only main photos get the careful look ({looked})")
check(len(quick_seen) == 20, f"every photo of every listing gets the quick look ({len(quick_seen)})")
check(new == 9, f"the two good listings lend their other photos - all but the one the quick look says is not the item ({new})")
src = {os.path.basename(p["file"]) for p in DS._round_sources(dos)}
check("L2p3.jpg" in src and "L3p4.jpg" not in src and not any(s.startswith("L1") for s in src), "a good listing's photos are label sources; a wrong one's are not")
check(all(p.get("listing") for p in dos["photos"]) and dos["listings_hunted"] == DS.LISTINGS, "each photo keeps its listing; the hunt is recorded")
check(DS.hunt_listings(dos, "x_aa", "judge", log=said.append) == 0, "once per version")
# three wrong listings in a row: stop
dos2 = dict(dos, photos=[], listings_hunted=None)
looked.clear()
G.search_listings = lambda q, most=24, log=print: [{"id": str(n), "page": f"p{n}", "title": ""} for n in range(6)]
G.listing = lambda page, log=print: [f"https://i.ebayimg.com/images/g/L1p{page}x/s-l1600.jpg"]
DS.hunt_listings(dos2, "x_aa", "judge", log=said.append)
check(len(looked) == 6, f"wrong listings do not stop the hunt: every ranked listing is looked at ({len(looked)})")
opened = []
G._open = lambda url, scroll=True, js=None, log=print, typed=None: (opened.append(url) or ("", [["https://www.ebay.com/itm/257348577422?x=0", ""], ["https://www.ebay.com/itm/Duracell-AA/257348577422?x=1", "Duracell AA Opens in a new window or tab"]]))
rows = REAL_SEARCH("duracell powercheck aa", log=lambda *a: None)
check(rows and rows[0]["id"] == "257348577422" and rows[0]["title"] == "Duracell AA", f"a result's picture link (no text) and title link are one listing, titled by the text ({rows[:1]})")
check(len(opened) == 2 and "LH_Sold=1" in opened[1] and "LH_Sold" not in opened[0], f"eBay is searched for sale AND sold ({opened})")
check(DS.hunt_due({"listings_hunted": None, "around_hunted": DS.VERSION}), "an item hunted before eBay was added still gets the eBay hunt")
src = open(DS.__file__).read()
check(src.index("hunt_listings(dos, cid, use, log)\n") < src.index("    hunt_faces(dos, cid, need, log)"), "the dossier hunts eBay first, before the image searches")
# the printed name and the era outrank the catalog's generic words
G.search_listings = lambda q, most=24, log=print: [{"id": "7", "page": "p7", "title": "Duracell Coppertop Variations, AA, AAA Batteries - Alkaline Battery"},
                                                    {"id": "8", "page": "p8", "title": "Vintage Duracell PowerCheck AA battery"}]
G.listing = lambda page, log=print: [f"https://i.ebayimg.com/images/g/X{page}y/s-l1600.jpg"]
looked.clear()
dos3 = {"cid": "x_aa", "route": "round", "identity": {"name": "DURACELL POWERCHECK ALKALINE", "year": 1998, "years": [1995, 1999]},
        "inputs": {"product": "Duracell Coppertop AA alkaline battery, circa 1998"}, "photos": [], "searches": [], "faces": {}, "gaps": []}
DS.hunt_listings(dos3, "x_aa", "judge", log=lambda *a: None)
check(looked and "Xp8y" in looked[0], f"the vintage PowerCheck listing is opened before the modern 40-pack ({looked})")
# common words weigh little, the brand is required (11:50: "1.5 Volts" lifted an Osco and an Energizer listing)
G.search_listings = lambda q, most=24, log=print: (
    [{"id": "o", "page": "po", "title": "VINTAGE 1.5 Volts Osco Alkaline battery Display"},
     {"id": "e", "page": "pe", "title": "Vintage Energizer AAA Batteries 1.5 Volt Alkaline"},
     {"id": "g", "page": "pg", "title": "Pair Vintage Duracell Powercheck AA Batteries"}]
    + [{"id": f"m{i}", "page": f"pm{i}", "title": f"Duracell AA Batteries 1.5 Volts Alkaline {i} pack"} for i in range(8)])
looked.clear()
dos4 = {"cid": "x_aa", "route": "round", "identity": {"name": "DURACELL POWERCHECK ALKALINE 1.5 Volts", "brand": "Duracell", "year": 1998,
        "years": [1995, 1999]}, "inputs": {"product": "Duracell Coppertop AA alkaline battery, circa 1998"}, "photos": [], "searches": [], "faces": {}, "gaps": []}
DS.hunt_listings(dos4, "x_aa", "judge", log=lambda *a: None)
check(looked and "Xpgy" in looked[0] and not any("Xpoy" in x or "Xpey" in x for x in looked), f"the rare word wins and other brands are never opened ({looked[:3]})")
# turned down only for its printed date: one focused design question decides (12:30: Cody's 6-cell listing)
G.search_listings = lambda q, most=24, log=print: [{"id": "c", "page": "pc", "title": "Duracell PowerCheck Power Check Meter 6 AA Batteries"}]
G.listing = lambda page, log=print: [f"https://i.ebayimg.com/images/g/C{k}zz/s-l1600.jpg" for k in range(4)]


def era_wrong(dos, use, log=print, only=None):
    for p in only:
        p.update(labeled=True, match="wrong", why="its years [2003, 2003] are outside the era [1990, 1999]", years=[2003, 2003],
                 faces=[{"face": "label", "box": None}], items=6)


DS.careful_looks = era_wrong
asked_design = []
DS._ask = lambda model, text, images, think=False, side=1280: (asked_design.append(images) or {"same_design": True, "why": "same PowerCheck label"})
dos5 = {"cid": "x_aa", "route": "round", "picked": "/p/pick.jpg", "identity": {"name": "DURACELL POWERCHECK", "brand": "Duracell", "years": [1990, 1999]},
        "inputs": {"product": "Duracell Coppertop AA alkaline battery"}, "photos": [], "searches": [], "faces": {}, "gaps": []}
n5 = DS.hunt_listings(dos5, "x_aa", "judge", log=lambda *a: None)
check(asked_design and asked_design[0][1] == "/p/pick.jpg" and n5 >= 2, f"an era-only 'wrong' gets the design question against the pick, and the listing counts ({n5})")
check(DS.listing_query({"name": "DURACELL POWERCHECK ALKALINE 1.5 Volts"}) == "DURACELL POWERCHECK ALKALINE", "ratings like '1.5 Volts' never go into the search")
print(f"ALL {ok} PASS")
