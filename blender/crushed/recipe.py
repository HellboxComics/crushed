"""Deterministic recipes: token id -> everything needed to rebuild that block,
and every trait that describes it.

The whole collection derives from COLLECTION_SEED. Conditions, one-of-ones and
contaminants are dealt from fixed decks (exact counts, shuffled once), so the
rarity curve is designed, not rolled. Publish sha256(manifest.json) on-chain
before mint so nobody (including us) can move a one-of-one afterwards.
"""
import numpy as np

from . import lore
from .objects import ERAS, NEON_SPEC, load

SUPPLY = 888
COLLECTION_SEED = 19972008

ONE_OF_ONES = [
    "EMPTY", "UNCRUSHED", "SOLID GOLD", "MIXTAPE", "LEFTOVERS", "DOUBLE A", "SCREEN TIME", "BULL TRAP",
    "LANDFILL DRIVE", "BLOW ON IT", "STILL ALIVE", "GAS FEES", "SAVE ICON", "COASTERS", "GM", "COLD STORAGE",
    "SLOW MOTION", "UNDER THE MATTRESS",
    "LOW RES", "CCFF00", "STOP THE PRESSES", "CLAY DAY",      # gift blocks, made for other people's worlds
]

CONDITIONS = {          # exact counts across all 888 (plus the one-of-ones)
    "GOLD": 11,
    "BIOHAZARD": 19,
    "CLEAN": 27,
    "BURNT": 36,
    "SOAKED": 36,
}                       # JUNK: the rest

CONTAMINANTS = {        # exact counts; 88 of 888 blocks are contaminated
    "red_candle": 16,
    "paper_hand": 12,
    "ramen_packet": 11,
    "crumpled_chart": 10,
    "broken_rocket": 9,
    "bull": 8,
    "bear": 7,
    "gold_coin": 6,
    "hardware_wallet": 5,
    "diamond": 3,
    "green_candle": 1,  # the rarest thing in the collection
}

CONTAMINANT_NAMES = {
    "red_candle": "Tiny Red Candle", "paper_hand": "Paper Hand", "ramen_packet": "Emergency Ramen",
    "crumpled_chart": "Crumpled Chart", "broken_rocket": "Broken Rocket", "bull": "Dead Bull",
    "bear": "Bear (Thriving)", "gold_coin": "Gold Coin", "hardware_wallet": "Suspicious Rectangle",
    "diamond": "Diamond", "green_candle": "Tiny Green Candle",
}

CLEAN_FINISHES = [
    ("BONE", ("plastic", {"color": (0.9, 0.89, 0.85), "rough": 0.45})),
    ("OBSIDIAN", ("plastic", {"color": (0.03, 0.03, 0.035), "rough": 0.3})),
    ("CHROME", ("chrome", {"rough": 0.12})),
    ("GRAPE", ("translucent", {"color": (0.45, 0.15, 0.75), "rough": 0.12})),
    ("SAFETY ORANGE", ("plastic", {"color": (1.0, 0.36, 0.02), "rough": 0.4})),
    ("ICE", ("translucent", {"color": (0.85, 0.9, 0.95), "rough": 0.18})),
]

PACKING = 1.6      # the gaps are packed with more of the same
STRAP_KG = 1.9

CASSETTEY = {"cassette", "vhs", "walkman", "boombox"}

# things big and dumb enough to be the first thing you see
HEADLINERS = {
    "crt": 3.0, "corded_phone": 3.0, "boombox": 2.5, "sneaker": 3.0, "controller_16bit": 2.5,
    "controller_modern": 2.5, "joystick": 2.0, "walkman": 2.0, "portable_cd": 2.0, "pager": 2.0,
    "flip_phone": 2.0, "candybar_phone": 2.0, "puzzle_cube": 2.0, "roller_skate": 1.5, "skateboard": 1.5,
    "lunchbox": 1.5, "tv_remote": 2.0, "brick_game": 2.0, "handheld": 2.0, "virtual_pet": 1.5,
    "digital_camera": 1.5, "mp3_player": 2.0, "vhs": 2.0, "cassette": 2.0, "keyboard_chunk": 1.2,
    "calculator": 1.5, "headphones": 1.2, "mouse": 1.5, "energy_can": 1.5, "disposable_camera": 1.2,
    "webcam": 1.0, "soda_can": 1.0, "yoyo": 1.0,
    "smartphone": 3.0, "tablet": 1.5, "earbuds_case": 1.5, "smartwatch": 1.0, "vr_headset": 2.0, "drone": 2.0,
    "fidget_spinner": 1.5, "selfie_stick": 1.0, "ring_light": 1.0, "vape": 1.5, "face_mask": 1.0,
    "hand_sanitizer": 1.0, "bluetooth_speaker": 1.5, "power_bank": 1.0,
    "magazine": 1.2, "beer_can": 0.8, "tissue_box": 0.8, "poker_chip": 0.6,
}

GOLDABLE = {"sneaker", "pizza_crust", "tv_remote", "corded_phone", "cassette", "pager", "controller_16bit",
            "controller_modern", "joystick", "flip_phone", "candybar_phone", "walkman", "mouse", "yoyo",
            "sunglasses", "headphones", "puzzle_cube", "aa_batteries", "floppy", "vhs", "digital_camera",
            "mp3_player", "energy_can", "soda_can", "skate_wheel", "brick_game", "game_cart", "roller_skate",
            "calculator", "smartphone", "fidget_spinner", "smartwatch", "earbuds_case", "dice", "poker_chip",
            "beer_can", "bluetooth_speaker", "power_bank", "vape"}

MONOCULTURES = {   # one-of-ones that are made of one idea
    "MIXTAPE": [("cassette", 40), ("walkman", 3), ("boombox", 1)],
    "LEFTOVERS": [("pizza_crust", 42)],
    "DOUBLE A": [("aa_batteries", 44), ("tv_remote", 4)],
    "SCREEN TIME": [("crt", 3), ("brick_game", 4), ("handheld", 4), ("candybar_phone", 4), ("flip_phone", 4),
                    ("pager", 4), ("digital_camera", 3), ("mp3_player", 4), ("calculator", 4), ("virtual_pet", 4)],
    "BULL TRAP": [("bull", 22), ("red_candle", 12), ("paper_hand", 3), ("crumpled_chart", 4), ("bear", 1)],
    "LANDFILL DRIVE": [("hdd", 28), ("gold_coin", 6), ("charger_brick", 3), ("usb_stick", 4), ("floppy", 3)],
    "BLOW ON IT": [("game_cart", 44), ("controller_16bit", 3), ("controller_modern", 2)],
    "STILL ALIVE": [("virtual_pet", 38), ("brick_game", 3), ("handheld", 3), ("aa_batteries", 4)],
    "GAS FEES": [("gas_can", 28), ("lighter", 5), ("gold_coin", 4)],
    "SAVE ICON": [("floppy", 64), ("usb_stick", 1)],
    "COASTERS": [("cd", 56), ("jewel_case", 10), ("beer_can", 6), ("shot_glass", 2)],
    "GM": [("coffee_mug", 32), ("energy_can", 5), ("gold_coin", 8), ("smartphone", 3)],
    "COLD STORAGE": [("cold_wallet", 40), ("hardware_wallet", 8), ("usb_stick", 3)],
    "SLOW MOTION": [("rescue_can", 10), ("whistle", 6), ("sunscreen", 8), ("swimsuit", 8), ("sunglasses", 6),
                    ("pager", 3), ("vhs", 4), ("walkman", 1)],
    "UNDER THE MATTRESS": [("magazine", 14), ("centerfold", 9), ("tissue_box", 5), ("tissues", 12), ("flashlight", 3),
                           ("sock", 4), ("foil_packet", 4)],
    "LOW RES": [("pixel_hoodie", 6), ("studio_headphones", 5), ("synth_keys", 4), ("cassette", 10), ("floppy", 6),
                ("ribbon_cable", 8), ("crt", 2), ("game_cart", 4), ("controller_16bit", 2)],
    "CCFF00": [("neon_square_big", 1), ("neon_square", 16), ("neon_diamond", 9), ("neon_cube", 8),
               ("neon_stack", 3), ("neon_frame", 4)],
    "STOP THE PRESSES": [("piggy_bank", 14), ("stock_cert", 5), ("ticker_tape", 4), ("necktie", 4), ("bull", 3),
                         ("bear", 3), ("corded_phone", 2), ("calculator", 2), ("newspaper", 3), ("street_sign", 1),
                         ("microphone", 1), ("press_badge", 2), ("play_money", 3), ("poker_chip", 2),
                         ("gold_coin", 2), ("neon_square", 2)],
    "CLAY DAY": [("clay_bull", 8), ("clay_bear", 7), ("clay_pig", 7), ("clay_frog", 6), ("clay_coin", 6),
                 ("clay_candle", 8)],
}

# one-of-ones whose gaps are packed with their own kind of debris
ONE_FILLERS = {
    "LEFTOVERS": ("cardboard_scrap", "packaging", "crumpled_paper", "receipt"),
    "LANDFILL DRIVE": ("pcb_chunk", "cardboard_scrap", "crumpled_paper", "wire_bit", "plastic_shard", "packaging"),
    "GAS FEES": ("receipt", "crumpled_paper"),
    "COASTERS": ("receipt", "bottle_cap", "crumpled_paper"),
    "SLOW MOTION": ("fabric_scrap", "plastic_film", "receipt", "gum_wrapper", "bottle_cap"),
    "UNDER THE MATTRESS": ("tissues", "crumpled_paper", "fabric_scrap", "foil_packet", "receipt"),
    "CCFF00": ("neon_bit",),
    "STOP THE PRESSES": ("receipt", "crumpled_paper", "bottle_cap"),
    "CLAY DAY": ("clay_blob",),
}

# one-of-ones whose contents get crushed gently (flat tiles should stay tiles)
ONE_SOFT = {"CCFF00": 0.25, "STOP THE PRESSES": 0.5, "CLAY DAY": 0.3}

# one-of-ones whose dense core (the mass behind everything) is not the era's junk
ONE_CORE = {
    "CCFF00": [(0.012, 0.012, 0.014), (0.02, 0.02, 0.022), (0.03, 0.03, 0.032)],
    "CLAY DAY": [(0.03, 0.03, 0.035), (0.95, 0.95, 0.93), (0.8, 1.0, 0.0), (0.96, 0.55, 0.68)],
}

# whole-block finishes for one-of-ones that are a single material
# one-of-ones made of paper, cloth or glass: loose electrical wire has no business on them
NO_WIRES = {"CLAY DAY", "UNDER THE MATTRESS", "SLOW MOTION", "GM", "GAS FEES", "STOP THE PRESSES", "COASTERS", "LEFTOVERS",
            "UNCRUSHED", "EMPTY", "BULL TRAP", "SOLID GOLD"}

ONE_FINISH = {
    "SOLID GOLD": ("SOLID GOLD", ("gold", {"rough": 0.2})),
    "CCFF00": ("CCFF00", NEON_SPEC),
    "COLD STORAGE": ("FROZEN", ("plastic", {"color": (0.74, 0.9, 1.0), "rough": 0.24, "coat": 0.9})),
}

ONE_OF_ONE_FLAVOR = {  # (smell, recovered from, headliner)
    "EMPTY": ("Nothing", "Nowhere", "Nothing"),
    "UNCRUSHED": ("Anticipation", "Right Next to the Crusher", "Everything"),
    "SOLID GOLD": ("Victory", "Estate of a Collector", None),
    "MIXTAPE": ("Magnetic Tape", "Every Car Glovebox", "Cassette Tape"),
    "LEFTOVERS": ("Friday Night", "Behind the Couch", "Pizza Crust"),
    "DOUBLE A": ("Fresh Batteries (Licked)", "Every Remote in the House", "AA Batteries"),
    "SCREEN TIME": ("Hot Dust on a CRT", "The Den", "CRT Monitor"),
    "BULL TRAP": ("Capitulation", "The Top", "Dead Bull"),
    "LANDFILL DRIVE": ("Wet Landfill", "Under Forty Feet of Garbage", "Hard Drive"),
    "BLOW ON IT": ("Hot Breath", "The Bottom of the Toy Box", "Game Cartridge"),
    "STILL ALIVE": ("Warm Plastic", "A Drawer, Still Beeping", "Virtual Pet"),
    "GAS FEES": ("Gasoline", "The Pump, 3 A.M.", "Gas Can"),
    "SAVE ICON": ("Static Electricity", "Every School Computer Lab", "Floppy Disk"),
    "COASTERS": ("Stale Beer", "Every Coffee Table", "Burned CD"),
    "GM": ("Burnt Coffee", "Every Timeline, 6 A.M.", "Coffee Mug"),
    "COLD STORAGE": ("Freezer Burn", "The Back of the Freezer", "Hardware Wallet"),
    "SLOW MOTION": ("Coconut Sunscreen", "The Beach, in Slow Motion", "Rescue Can"),
    "UNDER THE MATTRESS": ("Shame", "Under the Mattress", "Magazine"),
    "LOW RES": ("Warm Amplifier", "A Bedroom Studio, 3 A.M.", "Pixel Hoodie"),
    "CCFF00": ("Hot Plastic and Ozone", "The Neon Aisle", "Big Neon Square"),
    "STOP THE PRESSES": ("Bacon and Newsprint", "The Trading Floor, After the Bell", "Piggy Bank"),
    "CLAY DAY": ("Warm Plasticine", "A Desk, Mid-Pump", "Clay Bull"),
}

LOCKED = ("SOAKED", "BURNT", "BIOHAZARD", "GOLD")


def era_of(token_id):
    return min(len(ERAS) - 1, (token_id - 1) * len(ERAS) // SUPPLY)


def base_intensity(token_id):
    """The collection gets progressively more fucked up."""
    return 0.55 + 0.45 * (token_id - 1) / (SUPPLY - 1)


def _weighted(rng, table, cond):
    """Pick from (value, weight, conditions) rows. Rows tagged only with damage
    conditions (e.g. 'House Fire') appear on those conditions and nowhere else;
    tagged rows are boosted on their own conditions."""
    vals, ws = [], []
    for v, w, tags in table:
        if tags and all(t in LOCKED for t in tags) and cond not in tags:
            continue
        vals.append(v)
        ws.append(w * (4.0 if cond in tags else 1.0))
    ws = np.array(ws, dtype=float)
    return vals[int(rng.choice(len(vals), p=ws / ws.sum()))]


# eras (indexes into ERAS) each one-of-one may be dealt into; the rest can land anywhere
ONE_ERA = {
    "MIXTAPE": {0, 1}, "SCREEN TIME": {2, 3}, "LANDFILL DRIVE": {3, 4}, "BLOW ON IT": {1}, "STILL ALIVE": {2, 3},
    "GAS FEES": {2, 3, 4}, "SAVE ICON": {0, 1, 2}, "COASTERS": {1, 2, 3}, "GM": {4}, "COLD STORAGE": {3, 4},
    "SLOW MOTION": {1}, "UNDER THE MATTRESS": {0, 1, 2, 3}, "LOW RES": {1}, "CCFF00": {4},
    "STOP THE PRESSES": {4}, "CLAY DAY": {4},
}


def deck():
    rng = np.random.default_rng([COLLECTION_SEED, 0])
    conds = list(ONE_OF_ONES)
    for k, n in CONDITIONS.items():
        conds += [k] * n
    conds += ["JUNK"] * (SUPPLY - len(conds))
    conds = [str(c) for c in rng.permutation(conds)]
    for name, allowed in ONE_ERA.items():     # a one-of-one lands in an era its contents actually belong to
        i = conds.index(name)
        if era_of(i + 1) in allowed:
            continue
        cand = [j for j in range(SUPPLY) if era_of(j + 1) in allowed and conds[j] not in ONE_OF_ONES]
        j = cand[int(rng.integers(0, len(cand)))]
        conds[i], conds[j] = conds[j], conds[i]
    eligible = [i + 1 for i in range(SUPPLY) if conds[i] not in ONE_OF_ONES]
    items = []
    for k, n in CONTAMINANTS.items():
        items += [k] * n
    ids = rng.choice(eligible, len(items), replace=False)
    contaminant = {int(t): str(k) for t, k in zip(ids, rng.permutation(items))}
    return conds, contaminant


_DECK = None


def _gold(rng, heroes):
    """One totally inappropriate gold object: always something you can name."""
    idx = [i for i, h in enumerate(heroes) if h in GOLDABLE and i > 0]
    return int(rng.choice(idx)) if idx else 1


def recipe(token_id):
    global _DECK
    if _DECK is None:
        _DECK = deck()
    conds, contaminants = _DECK
    reg = load()
    rng = np.random.default_rng([COLLECTION_SEED, token_id])
    era = era_of(token_id)
    cond = conds[token_id - 1]
    one = cond if cond in ONE_OF_ONES else None
    inten = float(np.clip(base_intensity(token_id) + rng.normal(0, 0.04), 0.5, 1.0))

    def pool(e, group="era"):
        return [d for d in reg.values() if d.group == group and e in d.eras]

    # the headliner: the first thing you see, front and center
    hp = [d.name for d in pool(era) if d.name in HEADLINERS]
    hw = np.array([HEADLINERS[n] for n in hp])
    headliner = hp[int(rng.choice(len(hp), p=hw / hw.sum()))]

    n_hero = int(rng.integers(26, 36) + round(inten * 10))
    heroes = [headliner]
    counts = {headliner: 1}
    tries = 0
    while len(heroes) < n_hero and tries < 2000:
        tries += 1
        e = era
        if rng.random() < 0.15:
            e = int(np.clip(era + rng.choice([-1, 1]), 0, len(ERAS) - 1))
        p = pool(e)
        w = np.array([d.weight for d in p])
        d = p[rng.choice(len(p), p=w / w.sum())]
        if counts.get(d.name, 0) >= (1 if d.big else 3):
            continue
        if d.big and sum(1 for h in heroes if reg[h].big) >= 3:
            continue
        counts[d.name] = counts.get(d.name, 0) + 1
        heroes.append(d.name)

    if one in MONOCULTURES:
        heroes = [n for n, k in MONOCULTURES[one] for _ in range(k)]
        headliner = heroes[0]

    crypto = contaminants.get(token_id)

    fp = pool(era, "filler")
    if one in ONE_FILLERS:
        fp = [d for d in fp if d.name in ONE_FILLERS[one]]
    fw = np.array([d.weight for d in fp])
    n_fill = int(rng.integers(60, 80) + round(inten * 30))
    fillers = [fp[i].name for i in rng.choice(len(fp), n_fill, p=fw / fw.sum())]

    clean = None
    if cond == "CLEAN":
        clean = CLEAN_FINISHES[int(rng.integers(0, len(CLEAN_FINISHES)))]
    if one in ONE_FINISH:
        clean = ONE_FINISH[one]

    tape = 0
    if any(h in CASSETTEY for h in heroes) and cond != "CLEAN" and rng.random() < 0.85:
        tape = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.25, 0.25, 0.2, 0.15, 0.1, 0.05]))
    if one == "MIXTAPE":
        tape = 8
    wires = int(rng.integers(1, 6) + round(inten * 2.5))
    if one in NO_WIRES:
        wires = 0
    gold_index = _gold(rng, heroes) if cond == "GOLD" else None
    straps = [float(-0.082 + rng.normal(0, 0.004)), float(0.082 + rng.normal(0, 0.004))]
    seed = int(rng.integers(0, 1 << 30))

    if one == "EMPTY":
        heroes, fillers, crypto, tape, wires = [], [], None, 0, 0

    kg = sum(reg[n].mass for n in heroes + fillers + ([crypto] if crypto else [])) * PACKING + STRAP_KG
    if one == "EMPTY":
        kg = STRAP_KG

    # -- traits ---------------------------------------------------------------------
    trng = np.random.default_rng([COLLECTION_SEED, token_id, 7])
    smell = _weighted(trng, lore.SMELLS, cond)
    recovered = _weighted(trng, lore.RECOVERED, cond)
    head_name = lore.NAMES[headliner] if heroes else "Nothing"
    if one:
        s, rf, h = ONE_OF_ONE_FLAVOR[one]
        smell, recovered = s, rf
        head_name = h or head_name
    pressure = next(name for lim, name in lore.PRESSURE if inten < lim)
    if one in ("EMPTY", "UNCRUSHED"):
        pressure = "None Applied"

    traits = [
        ("Era", ERAS[era]),
        ("Condition", cond),
        ("Headliner", head_name),
        ("Contaminant", CONTAMINANT_NAMES[crypto] if crypto else "None"),
        ("Pressure", pressure),
        ("Smell", smell),
        ("Recovered From", recovered),
        ("Tape", lore.TAPE[tape]),
        ("Loose Wires", next(n for lim, n in lore.WIRES if wires <= lim) if wires else "None"),
    ]
    if clean and not one:
        traits.append(("Finish", clean[0]))
    if gold_index is not None:
        traits.append(("Gilded", lore.NAMES[heroes[gold_index]]))
    if one:
        traits.append(("One of One", one))

    return {
        "id": token_id,
        "recipe_id": token_id,
        "name": f"CRUSHED IT #{token_id:04d}",
        "era": ERAS[era],
        "era_index": era,
        "condition": cond,
        "one_of_one": one,
        "clean": clean,
        "core": ONE_CORE.get(one),
        "soft": ONE_SOFT.get(one, 1.0),
        "intensity": inten,
        "headliner": headliner if heroes else None,
        "heroes": heroes,
        "crypto": crypto,
        "fillers": fillers,
        "tape_loops": tape,
        "wires": wires,
        "gold_index": gold_index,
        "straps": straps,
        "seed": seed,
        "weight_lb": round(kg * 2.20462, 1),
        "items": len(heroes) + (1 if crypto else 0),
        "traits": traits,
    }


def description(r):
    """An evidence log. Partial, because nobody is counting all of that."""
    one = r["one_of_one"]
    if one in ("EMPTY", "UNCRUSHED"):
        return f"{lore.ONE_OF_ONES[one]} Weight {r['weight_lb']} lb."
    rng = np.random.default_rng([COLLECTION_SEED, r["recipe_id"], 11])
    seen, lines = set(), []
    order = [r["heroes"][0]] + [str(x) for x in rng.permutation(r["heroes"][1:])]
    gold = r["heroes"][r["gold_index"]] if r["gold_index"] is not None else None
    for n in ([gold] if gold else []) + order:
        if n in seen:
            continue
        seen.add(n)
        k = r["heroes"].count(n)
        notes = lore.NOTES.get(n, [""])
        note = notes[int(rng.integers(0, len(notes)))]
        name = lore.NAMES[n] if k == 1 else lore.plural(lore.NAMES[n])
        if n == gold:
            name, note, k = "Gold " + lore.NAMES[n], "why", 1
        lines.append(f"{k} {name}" + (f" ({note})" if note else ""))
        if len(lines) >= 5:
            break
    if r["crypto"]:
        c = r["crypto"]
        notes = lore.NOTES[c]
        lines.append(f"1 {lore.NAMES.get(c, CONTAMINANT_NAMES[c])} ({notes[int(rng.integers(0, len(notes)))]})")
    t = dict(r["traits"])
    head = lore.ONE_OF_ONES[one] + " " if one else ""
    sign = lore.SIGNOFFS[int(rng.integers(0, len(lore.SIGNOFFS)))]
    return (f"{head}Recovered from {t['Recovered From'].rstrip('.')}. {lore.smells_like(t['Smell'])} "
            f"Contents (partial): {'; '.join(lines)}. Weight {r['weight_lb']} lb. {sign}")


def metadata(r, image_uri, animation_uri=None):
    attrs = [{"trait_type": k, "value": v} for k, v in r["traits"]]
    attrs.append({"trait_type": "Weight (lb)", "value": r["weight_lb"], "display_type": "number"})
    attrs.append({"trait_type": "Item Count", "value": r["items"], "display_type": "number"})
    m = {"name": r["name"], "description": description(r), "image": image_uri, "attributes": attrs}
    if animation_uri:
        m["animation_url"] = animation_uri
    return m


def showcase(n=100):
    """The preview pile for the site: every one-of-one, some of each condition,
    some contaminated blocks, and the rest JUNK spread evenly across the eras."""
    conds, cont = deck()
    rng = np.random.default_rng([COLLECTION_SEED, 1])
    ids = [i + 1 for i, c in enumerate(conds) if c in ONE_OF_ONES]
    for c, k in (("GOLD", 4), ("BIOHAZARD", 5), ("CLEAN", 6), ("BURNT", 5), ("SOAKED", 5)):
        pool = [i + 1 for i, x in enumerate(conds) if x == c]
        ids += [int(x) for x in rng.choice(pool, k, replace=False)]
    junk = [i + 1 for i, x in enumerate(conds) if x == "JUNK"]
    dirty = [t for t in junk if t in cont]
    ids += [t for t, k in cont.items() if k == "green_candle"]
    ids += [int(x) for x in rng.choice(dirty, 8, replace=False)]
    rest = [t for t in junk if t not in ids]
    need = n - len(set(ids))
    step = len(rest) / need
    ids += [rest[int(i * step)] for i in range(need)]
    return sorted(set(ids))[:n]
