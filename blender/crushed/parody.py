"""Parody brands, by product and by era. In the ballpark of the real shelf, never the real name or mark:
everyone knows what it is, nobody's logo is in it. Era index: 0 1985-90, 1 1991-96, 2 1997-02, 3 2003-08,
4 2009-26. A brand listed under several eras was on the shelf for all of them."""

def pick(rng, table, era=None):
    rows = [b for b in table if era is None or era in b[1]] or table
    return rows[int(rng.integers(0, len(rows)))]


ALL = (0, 1, 2, 3, 4)
# (name, eras, colors: (base, accent, ink))
SODA = [("KOAK CLASSIK", ALL, ((0.8, 0.05, 0.08), (1, 1, 1), (1, 1, 1))),
        ("PEPPY", ALL, ((0.05, 0.2, 0.6), (0.85, 0.1, 0.15), (1, 1, 1))),
        ("MOUNTAIN DUDE", ALL, ((0.1, 0.45, 0.15), (0.9, 0.85, 0.1), (1, 1, 1))),
        ("SURJ", (1, 2), ((0.1, 0.5, 0.15), (0.95, 0.2, 0.1), (1, 1, 1))),
        ("CRYSTAL PEPPY", (1,), ((0.85, 0.88, 0.92), (0.05, 0.2, 0.6), (0.05, 0.2, 0.6))),
        ("NEW KOAK", (0,), ((0.8, 0.05, 0.08), (0.95, 0.85, 0.2), (1, 1, 1))),
        ("TABB", (0,), ((0.85, 0.2, 0.45), (1, 1, 1), (1, 1, 1))),
        ("DR PEPPA", ALL, ((0.45, 0.05, 0.1), (1, 1, 1), (1, 1, 1))),
        ("SPRYTE", ALL, ((0.05, 0.45, 0.2), (0.95, 0.9, 0.2), (1, 1, 1))),
        ("SHASTY", (0, 1), ((0.9, 0.5, 0.1), (1, 1, 1), (1, 1, 1))),
        ("BAJA BLAST-OFF", (3, 4), ((0.05, 0.7, 0.75), (0.1, 0.25, 0.6), (1, 1, 1)))]
ENERGY = [("RED BULLISH", (2, 3, 4), ((0.15, 0.25, 0.6), (0.85, 0.1, 0.15), (0.95, 0.75, 0.2))),
          ("MOONSTER", (3, 4), ((0.05, 0.05, 0.05), (0.4, 1.0, 0.1), (0.4, 1.0, 0.1))),
          ("ROCKSTARR", (3, 4), ((0.05, 0.05, 0.05), (0.95, 0.75, 0.1), (1, 1, 1))),
          ("BALLZ", (2, 3), ((0.15, 0.25, 0.75), (1, 1, 1), (1, 1, 1))),
          ("JOLTED", (0, 1, 2), ((0.9, 0.1, 0.1), (1, 0.9, 0.1), (1, 1, 1))),
          ("FIVE LOCO", (3, 4), ((0.2, 0.05, 0.3), (1.0, 0.3, 0.6), (1, 1, 1))),
          ("PRIME TIME", (4,), ((0.55, 0.85, 1.0), (1, 1, 1), (0.1, 0.1, 0.2))),
          ("C-LSIUS", (4,), ((0.95, 0.95, 0.95), (0.9, 0.3, 0.2), (0.1, 0.1, 0.1))),
          ("BANG BANG", (4,), ((0.1, 0.1, 0.12), (0.9, 0.2, 0.6), (1, 1, 1)))]
BEER = [("BUD LIGHT-ISH", ALL, ((0.15, 0.3, 0.75), (0.9, 0.9, 0.95), (1, 1, 1))),
        ("NATTY LIGHTWEIGHT", ALL, ((0.85, 0.85, 0.9), (0.1, 0.3, 0.7), (0.1, 0.3, 0.7))),
        ("PBJ", ALL, ((0.95, 0.95, 0.95), (0.1, 0.25, 0.6), (0.8, 0.1, 0.1))),
        ("KEYSTONED", ALL, ((0.75, 0.82, 0.9), (0.1, 0.2, 0.55), (0.1, 0.2, 0.55))),
        ("MILWAUKEE'S WORST", ALL, ((0.85, 0.8, 0.7), (0.05, 0.1, 0.35), (0.05, 0.1, 0.35))),
        ("COURSE LIGHT", ALL, ((0.85, 0.87, 0.9), (0.6, 0.1, 0.1), (0.6, 0.1, 0.1))),
        ("ZIMMA", (1, 2), ((0.8, 0.85, 0.9), (0.6, 0.6, 0.65), (0.1, 0.1, 0.15))),
        ("SMIRKOFF ICE", (2, 3), ((0.85, 0.88, 0.92), (0.8, 0.1, 0.1), (0.1, 0.15, 0.4))),
        ("WHITE PAW", (4,), ((0.95, 0.95, 0.95), (0.1, 0.1, 0.1), (0.1, 0.1, 0.1))),
        ("MIKE'S HARDLY LEMONADE", (2, 3, 4), ((0.95, 0.85, 0.2), (0.1, 0.1, 0.1), (0.1, 0.1, 0.1)))]
RAMEN = [("BOTTOM RAMEN", ALL, ((0.85, 0.1, 0.05), (1, 0.85, 0.2), (1, 1, 1))),
         ("MARUCHUMP", ALL, ((0.9, 0.55, 0.05), (0.85, 0.1, 0.05), (1, 1, 1))),
         ("CUP NOODZ", ALL, ((0.95, 0.95, 0.95), (0.85, 0.1, 0.1), (0.85, 0.1, 0.1)))]
VAPE = [("JOOL", (3, 4), ((0.15, 0.15, 0.17), (0.9, 0.9, 0.95), (1, 1, 1))),
        ("PUFF BARF", (4,), ((1.0, 0.3, 0.5), (1.0, 0.9, 0.2), (1, 1, 1))),
        ("SELF BAR", (4,), ((0.3, 0.6, 1.0), (0.6, 0.3, 1.0), (1, 1, 1))),
        ("GEEK BAR-F", (4,), ((0.1, 0.9, 0.6), (1.0, 0.4, 0.8), (1, 1, 1)))]
VAPE_FLAVORS = ["MANGO REGRET", "BLUE RAZZ ICE", "COTTON CANDY CRISIS", "MIAMI MINT", "STRAWBERRY KIWI COPE",
                "WATERMELON ICE", "GRAPE APE", "BANANA REGRET"]
BATTERY = [("DURASMELL", ALL, ((0.1, 0.1, 0.1), (0.75, 0.45, 0.2), (1, 1, 1))),
           ("ENERGIZED", ALL, ((0.1, 0.1, 0.1), (0.75, 0.75, 0.75), (1, 1, 1))),
           ("NEVEREADY", (0, 1), ((0.1, 0.1, 0.1), (0.85, 0.1, 0.1), (1, 1, 1))),
           ("RAYOWHACK", ALL, ((0.1, 0.35, 0.8), (0.95, 0.95, 0.95), (1, 1, 1))),
           ("AMAZON BASICALLY", (4,), ((0.1, 0.1, 0.12), (1.0, 0.6, 0.1), (1, 1, 1)))]
SUNSCREEN = [("BANANA BLOAT", ALL, ((0.97, 0.9, 0.3), (0.1, 0.5, 0.95), (0.1, 0.3, 0.7))),
             ("COPPERTONED", ALL, ((0.95, 0.75, 0.4), (0.9, 0.3, 0.1), (0.4, 0.2, 0.05))),
             ("HAWAIIAN TOXIC", ALL, ((0.95, 0.55, 0.1), (0.1, 0.55, 0.3), (1, 1, 1)))]
TISSUE = [("KLEENEXXX", ALL), ("HUFFS", ALL), ("SCOTCH SOFTIES", ALL), ("BUNNY SOFT", ALL)]
CLUBS = ["PEPPERMINT HIPPO", "RICK'S CABERNET", "DEJA BOO", "THE SCORED CLUB", "THE VELVET ROOM", "CHEETAHS-ISH",
         "THE PONY TAIL", "BADA BOOM"]
COFFEE = [("STARBUX", (2, 3, 4)), ("DUNKED ON", ALL), ("MCCAFE-ISH", (3, 4)), ("FOLGIN'S", ALL)]
SANITIZER = [("PURE-ISH", (3, 4)), ("GERM-X-ACTLY", (3, 4)), ("SANITY-ZER", (4,))]
GAS = [("EXXOFF", ALL), ("SHELLED", ALL), ("TAXACO", ALL), ("MOBILE HOME", ALL), ("SUNOCOPE", ALL), ("CITGOES", ALL)]
DRIVES = [("SEAGRAVE", ALL), ("WESTERN DIGITILT", ALL), ("MAXTORE", (1, 2)), ("QUANTUMB", (1, 2)), ("IOMEGALODON", (1, 2))]
TAPES = [("MAXHELL", ALL), ("TDKAY", ALL), ("MEMOWRECKS", ALL), ("SONNY", ALL), ("BASFF", (0, 1))]
LOTTERY = ["POWERBAWL", "MEGA MILLIONAIRES", "LUCKY 7S", "CASH 4 LIFE-ISH", "HOT STREAK", "BLAZING 7S"]
SKATE = ["THRASHED", "NO BEER", "VANZ", "STUSHY", "BONG-A-BILLA", "ZOO YORKED", "POWELL PERALTA-ISH", "FREEDOM FRIES"]
APPS = ["FACEPLANT", "INSTAGRAMPA", "SNAPCHUMP", "TINDERBOX", "VENMOAN", "TIKTOCK", "UBERLY", "DOORDASHED",
        "ROBBERHOOD", "COINBASED", "PHANTOMLIMB", "METAMASKED", "ONLYFUNDS", "CANDY CRUSHED"]
APPS = [a for a in APPS if a not in ("ROBBERHOOD",)]       # the chain's own brand stays out, by its rules
WIN_SCREENS = ["WINDOZE 95", "WINDOZE 98", "WINDOZE ME (SORRY)", "WINDOZE XP", "MAC OH-S"]
MONEY = ["MONOPOOLY", "MONOPOLY-ISH", "BANK OF NOWHERE"]
SOCKS = ["HANDS", "FRUIT OF THE GLOOM", "GOLD TOED"]
