"""Deterministic recipes: token id -> everything needed to rebuild that block.

The whole collection derives from COLLECTION_SEED. Conditions are dealt from
a fixed deck (exact counts, shuffled once) so rarity is guaranteed, not
probabilistic. Publish sha256(manifest.json) on-chain before mint.
"""
import numpy as np

from .objects import ERAS, load

SUPPLY = 888
COLLECTION_SEED = 19972008

CONDITIONS = {          # exact counts across all 888
    "EMPTY": 1,
    "UNCRUSHED": 1,
    "GOLD": 11,
    "BIOHAZARD": 19,
    "CLEAN": 27,
    "BURNT": 36,
    "SOAKED": 36,
}                       # JUNK: the other 757
CRYPTO_RATE = 0.10

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


GOLDABLE = {"sneaker", "pizza_crust", "tv_remote", "corded_phone", "cassette", "pager", "controller_16bit",
            "controller_modern", "joystick", "flip_phone", "candybar_phone", "walkman", "mouse", "yoyo",
            "sunglasses", "headphones", "puzzle_cube", "aa_batteries", "floppy", "vhs", "digital_camera",
            "mp3_player", "energy_can", "soda_can", "skate_wheel", "brick_game", "game_cart", "roller_skate"}


def _gold(rng, heroes, reg):
    """One totally inappropriate gold object: always something you can name."""
    idx = [i for i, h in enumerate(heroes) if h in GOLDABLE]
    return int(rng.choice(idx)) if idx else int(rng.integers(0, len(heroes)))


def era_of(token_id):
    return min(3, (token_id - 1) * 4 // SUPPLY)


def intensity_of(token_id):
    """The collection gets progressively more fucked up."""
    return 0.55 + 0.45 * (token_id - 1) / (SUPPLY - 1)


def deck():
    rng = np.random.default_rng([COLLECTION_SEED, 0])
    conds = []
    for k, n in CONDITIONS.items():
        conds += [k] * n
    conds += ["JUNK"] * (SUPPLY - len(conds))
    conds = list(rng.permutation(conds))
    ids = [i + 1 for i in range(SUPPLY) if conds[i] != "EMPTY"]
    contaminated = set(int(x) for x in rng.choice(ids, int(SUPPLY * CRYPTO_RATE), replace=False))
    return conds, contaminated


_DECK = None


def recipe(token_id):
    global _DECK
    if _DECK is None:
        _DECK = deck()
    conds, contaminated = _DECK
    reg = load()
    rng = np.random.default_rng([COLLECTION_SEED, token_id])
    era = era_of(token_id)
    inten = intensity_of(token_id)
    cond = str(conds[token_id - 1])

    def pool(e, group="era"):
        return [d for d in reg.values() if d.group == group and e in d.eras]

    n_hero = int(rng.integers(26, 36) + round(inten * 10))
    heroes = []
    counts = {}
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

    crypto = None
    if token_id in contaminated:
        p = pool(era, "crypto")
        w = np.array([d.weight for d in p])
        crypto = p[rng.choice(len(p), p=w / w.sum())].name

    fp = pool(era, "filler")
    fw = np.array([d.weight for d in fp])
    n_fill = int(rng.integers(60, 80) + round(inten * 30))
    fillers = [fp[i].name for i in rng.choice(len(fp), n_fill, p=fw / fw.sum())]

    clean = None
    if cond == "CLEAN":
        clean = CLEAN_FINISHES[int(rng.integers(0, len(CLEAN_FINISHES)))]

    tape = 0
    if any(h in CASSETTEY for h in heroes) and cond != "CLEAN" and rng.random() < 0.85:
        tape = int(rng.integers(2, 5))

    if cond == "EMPTY":
        kg = STRAP_KG
    else:
        kg = sum(reg[n].mass for n in heroes + fillers + ([crypto] if crypto else [])) * PACKING + STRAP_KG
    if cond == "EMPTY":
        heroes, fillers, crypto, tape = [], [], None, 0

    return {
        "id": token_id,
        "weight_lb": round(kg * 2.20462, 1),
        "name": f"CRUSHED #{token_id:04d}",
        "era": ERAS[era],
        "era_index": era,
        "condition": cond,
        "clean": clean,
        "intensity": inten,
        "heroes": heroes,
        "crypto": crypto,
        "fillers": fillers,
        "tape_loops": tape,
        "wires": int(rng.integers(2, 6) + round(inten * 3)),
        "gold_index": _gold(rng, heroes, reg) if cond == "GOLD" else None,
        "straps": [float(-0.082 + rng.normal(0, 0.004)), float(0.082 + rng.normal(0, 0.004))],
        "seed": int(rng.integers(0, 1 << 30)),
    }
