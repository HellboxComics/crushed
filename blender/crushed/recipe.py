"""Deterministic recipes: token id -> everything needed to rebuild that block,
and every trait that describes it.

The whole collection derives from COLLECTION_SEED. Conditions, one-of-ones and
contaminants are dealt from fixed decks (exact counts, shuffled once), so the
rarity curve is designed, not rolled. Publish sha256(manifest.json) on-chain
before mint so nobody (including us) can move a one-of-one afterwards.
"""
import numpy as np

from . import lore
from .objects import ERAS, load

SUPPLY = 888
COLLECTION_SEED = 19972008

ONE_OF_ONES = ["EMPTY", "UNCRUSHED", "SOLID GOLD", "MIXTAPE", "LEFTOVERS", "DOUBLE A", "SCREEN TIME", "BULL TRAP"]

CONDITIONS = {          # exact counts across all 888 (plus the 8 one-of-ones)
    "GOLD": 11,
    "BIOHAZARD": 19,
    "CLEAN": 27,
    "BURNT": 36,
    "SOAKED": 36,
}                       # JUNK: the other 751

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
}

GOLDABLE = {"sneaker", "pizza_crust", "tv_remote", "corded_phone", "cassette", "pager", "controller_16bit",
            "controller_modern", "joystick", "flip_phone", "candybar_phone", "walkman", "mouse", "yoyo",
            "sunglasses", "headphones", "puzzle_cube", "aa_batteries", "floppy", "vhs", "digital_camera",
            "mp3_player", "energy_can", "soda_can", "skate_wheel", "brick_game", "game_cart", "roller_skate",
            "calculator"}

MONOCULTURES = {   # one-of-ones that are made of one idea
    "MIXTAPE": [("cassette", 30), ("vhs", 4), ("walkman", 3), ("boombox", 1)],
    "LEFTOVERS": [("pizza_crust", 42)],
    "DOUBLE A": [("aa_batteries", 44), ("tv_remote", 4)],
    "SCREEN TIME": [("crt", 3), ("brick_game", 4), ("handheld", 4), ("candybar_phone", 4), ("flip_phone", 4),
                    ("pager", 4), ("digital_camera", 3), ("mp3_player", 4), ("calculator", 4), ("virtual_pet", 4)],
    "BULL TRAP": [("bull", 22), ("red_candle", 12), ("paper_hand", 3), ("crumpled_chart", 4), ("bear", 1)],
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
}

LOCKED = ("SOAKED", "BURNT", "BIOHAZARD", "GOLD")


def era_of(token_id):
    return min(3, (token_id - 1) * 4 // SUPPLY)


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


def deck():
    rng = np.random.default_rng([COLLECTION_SEED, 0])
    conds = list(ONE_OF_ONES)
    for k, n in CONDITIONS.items():
        conds += [k] * n
    conds += ["JUNK"] * (SUPPLY - len(conds))
    conds = [str(c) for c in rng.permutation(conds)]
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

    # the headliner: the first thing you see, front and centre
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
            e = int(np.clip(era + rng.choice([-1, 1]), 0, 3))
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
    if one == "LEFTOVERS":
        fp = [d for d in fp if d.name in ("cardboard_scrap", "packaging", "crumpled_paper", "receipt")]
    fw = np.array([d.weight for d in fp])
    n_fill = int(rng.integers(60, 80) + round(inten * 30))
    fillers = [fp[i].name for i in rng.choice(len(fp), n_fill, p=fw / fw.sum())]

    clean = None
    if cond == "CLEAN":
        clean = CLEAN_FINISHES[int(rng.integers(0, len(CLEAN_FINISHES)))]
    if one == "SOLID GOLD":
        clean = ("SOLID GOLD", ("gold", {"rough": 0.2}))

    tape = 0
    if any(h in CASSETTEY for h in heroes) and cond != "CLEAN" and rng.random() < 0.85:
        tape = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.25, 0.25, 0.2, 0.15, 0.1, 0.05]))
    if one == "MIXTAPE":
        tape = 8
    wires = int(rng.integers(1, 6) + round(inten * 2.5))
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
        "name": f"CRUSHED #{token_id:04d}",
        "era": ERAS[era],
        "era_index": era,
        "condition": cond,
        "one_of_one": one,
        "clean": clean,
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
            name, note, k = "Gold " + name, "why", 1
        lines.append(f"{k} {name}" + (f" ({note})" if note else ""))
        if len(lines) >= 5:
            break
    if r["crypto"]:
        c = r["crypto"]
        notes = lore.NOTES[c]
        lines.append(f"1 {CONTAMINANT_NAMES[c]} ({notes[int(rng.integers(0, len(notes)))]})")
    t = dict(r["traits"])
    head = lore.ONE_OF_ONES[one] + " " if one else ""
    sign = lore.SIGNOFFS[int(rng.integers(0, len(lore.SIGNOFFS)))]
    return (f"{head}Recovered from {t['Recovered From']}. {lore.smells_like(t['Smell'])} "
            f"Contents (partial): {'; '.join(lines)}. Weight {r['weight_lb']} lb. {sign}")


def metadata(r, image_uri, animation_uri=None):
    attrs = [{"trait_type": k, "value": v} for k, v in r["traits"]]
    attrs.append({"trait_type": "Weight (lb)", "value": r["weight_lb"], "display_type": "number"})
    attrs.append({"trait_type": "Item Count", "value": r["items"], "display_type": "number"})
    m = {"name": r["name"], "description": description(r), "image": image_uri, "attributes": attrs}
    if animation_uri:
        m["animation_url"] = animation_uri
    return m
