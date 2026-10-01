"""Object library registry.

Every object is original, generic geometry. Nothing copies a real product's
trade dress: era is communicated by shape, color and material only.

A definition function receives (Builder, rng, Palette) and returns a dict
mapping material-slot keys to material specs. Objects are built lying with
their most recognizable face toward +Z unless `hero` says otherwise.
"""
from dataclasses import dataclass, field

ERAS = ["1985-1990", "1991-1996", "1997-2002", "2003-2008", "2009-2026"]


@dataclass
class Def:
    name: str
    fn: object
    eras: tuple
    mass: float                 # kg, for the block's weight
    weight: float = 1.0         # selection weight
    hero: tuple = (0, 0, 1)
    group: str = "era"          # era | crypto | filler
    big: bool = False           # large items get pressed hardest
    tags: tuple = field(default_factory=tuple)


REG = {}


def obj(name, eras=(0, 1, 2, 3, 4), mass=0.1, weight=1.0, hero=(0, 0, 1), group="era", big=False, tags=()):
    def deco(fn):
        REG[name] = Def(name, fn, tuple(eras), mass, weight, hero, group, big, tuple(tags))
        return fn
    return deco


# -- material spec shorthands ----------------------------------------------------

def P(c, rough=0.38, **kw):
    return ("plastic", {"color": tuple(c), "rough": rough, **kw})


def T(c, rough=0.1):
    return ("translucent", {"color": tuple(c), "rough": rough})


def RUB(c=(0.06, 0.06, 0.06)):
    return ("rubber", {"color": tuple(c)})


def MET(c=(0.75, 0.75, 0.76), rough=0.3):
    return ("metal", {"color": tuple(c), "rough": rough})


def CHROME():
    return ("chrome", {})


def PR(img, rough=0.45, **kw):
    return ("printed", {"image": img, "rough": rough, **kw})


# -- shared gift-block constants ---------------------------------------------------

LIME = (0.7, 1.0, 0.0)          # CCFF00 (a touch greener here, AgX drifts it toward yellow)
NEON = 0.9                      # how hard the lime glows
NEON_SPEC = ("plastic", {"color": LIME, "rough": 0.3, "coat": 0.5, "glow": NEON})


# -- era palettes ----------------------------------------------------------------

BEIGE = (0.84, 0.8, 0.68)
YELLOWED = (0.8, 0.74, 0.55)
BLACK = (0.05, 0.05, 0.055)
CHARCOAL = (0.16, 0.16, 0.17)
GREY = (0.55, 0.55, 0.56)
WHITE = (0.92, 0.92, 0.9)
SILVER = (0.72, 0.73, 0.75)

PALETTES = {
    0: {"body": [BEIGE, YELLOWED, BLACK, CHARCOAL, (0.55, 0.12, 0.1), (0.2, 0.25, 0.5), SILVER, (0.45, 0.3, 0.18)],
        "loud": [(1.0, 0.2, 0.55), (0.1, 0.8, 0.75), (1.0, 0.85, 0.1), (0.95, 0.1, 0.1), (0.1, 0.35, 0.9),
                 (0.55, 0.2, 0.8)],
        "clear": 0.03},
    1: {"body": [BLACK, CHARCOAL, GREY, (0.3, 0.25, 0.45), (0.1, 0.4, 0.45), BEIGE, (0.2, 0.2, 0.3)],
        "loud": [(0.5, 1.0, 0.1), (1.0, 0.1, 0.6), (0.45, 0.2, 0.85), (0.1, 0.75, 0.8), (1.0, 0.5, 0.0),
                 (1.0, 0.95, 0.2)],
        "clear": 0.15},
    2: {"body": [BEIGE, SILVER, CHARCOAL, WHITE, (0.3, 0.45, 0.7)],
        "loud": [(0.1, 0.5, 0.9), (0.55, 0.2, 0.8), (0.4, 0.85, 0.1), (1.0, 0.5, 0.1), (0.95, 0.2, 0.35),
                 (0.35, 0.35, 0.4), (0.7, 0.85, 0.95)],
        "clear": 0.6},
    3: {"body": [WHITE, BLACK, SILVER, (0.2, 0.2, 0.22), (0.85, 0.5, 0.65), (0.25, 0.35, 0.6)],
        "loud": [(0.45, 0.9, 0.2), (1.0, 0.35, 0.6), (0.1, 0.6, 1.0), (1.0, 0.55, 0.1), (0.95, 0.1, 0.1)],
        "clear": 0.08},
    4: {"body": [WHITE, BLACK, SILVER, (0.2, 0.2, 0.22), (0.88, 0.88, 0.9), (0.15, 0.25, 0.42), (0.85, 0.62, 0.55)],
        "loud": [(0.8, 1.0, 0.0), (0.2, 0.9, 0.5), (1.0, 0.3, 0.55), (0.3, 0.4, 1.0), (1.0, 0.6, 0.1),
                 (0.6, 0.3, 1.0)],
        "clear": 0.05},
}


class Palette:
    def __init__(self, era, rng):
        self.era = era
        self.rng = rng
        self.p = PALETTES[era]

    def pick(self, key):
        seq = self.p[key]
        return tuple(seq[self.rng.integers(0, len(seq))])

    def body(self, loud=0.25, clear=None, rough=0.38):
        """A main housing material appropriate for the era."""
        clear = self.p["clear"] if clear is None else clear
        r = self.rng.random()
        if r < clear:
            return T(self.pick("loud") if self.rng.random() < 0.8 else (0.85, 0.87, 0.9),
                     rough=float(self.rng.uniform(0.05, 0.25)))
        if r < clear + loud:
            return P(self.pick("loud"), rough)
        return P(self.pick("body"), rough)

    def loud(self):
        return P(self.pick("loud"))

    def color(self, key="loud"):
        return self.pick(key)


def load():
    from . import era, crypto, filler, modern, degen, special, gifts, holiday, games, toys, tech, life, room  # noqa: F401
    import glob
    import importlib
    import os
    from .. import lore
    intl = [importlib.import_module(f"{__name__}.{os.path.basename(f)[:-3]}")      # the international crews
            for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "intl_*.py")))]
    for mod in (games, toys, tech, life, room, *intl):          # these modules carry their own names and evidence-log notes
        for k, v in getattr(mod, "LORE_NAMES", {}).items():
            lore.NAMES.setdefault(k, v)
        for k, v in getattr(mod, "LORE_NOTES", {}).items():
            lore.NOTES.setdefault(k, v)
    return REG
