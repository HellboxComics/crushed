"""THE ERA OF AN ITEM, AS A RANGE PEOPLE USE: a 1998 battery is a "90s" battery, a 2003 one an "early 2000s" one.
One exact year made the hunt narrow (few photos are labeled "1998") and made your AI throw out good references
from a year or two away; a relative range finds more photos and matches how collectors and sellers describe
things (Cody, 2026-10-03: "instead of 1998 it should just be 90s. instead of 2003 it should just be early 2000s").

  before 2000   the whole decade: 1998 -> "90s" (1990-1999), 1985 -> "80s" (1980-1989)
  2000 on       early / mid / late part of the decade: 2003 -> "early 2000s" (2000-2003), 2005 -> "mid 2000s"
                (2004-2006), 2008 -> "late 2000s" (2007-2009), 2012 -> "early 2010s" (2010-2013)

    era.span(1998)    -> (1990, 1999)
    era.words(1998)   -> "90s"           (for searches and questions; never the exact year)
    era.off(1996, 1998) -> 0             (years outside the item's range; 0 = inside it)
"""


def _parts(year):
    y = int(year)
    d = y // 10 * 10
    if y < 2000:
        return d, d + 9, f"{str(d)[2:]}s" if d >= 1900 else f"{d}s"
    k = y - d
    part, a, b = ("early", 0, 3) if k <= 3 else ("mid", 4, 6) if k <= 6 else ("late", 7, 9)
    return d + a, d + b, f"{part} {d}s"


def span(year):
    """(first year, last year) of the item's era; (1900, 2100) when the year is unknown."""
    try:
        a, b, _ = _parts(year)
        return a, b
    except (TypeError, ValueError):
        return 1900, 2100


def words(year):
    """How people say the era: '90s', 'early 2000s' - '' when the year is unknown."""
    try:
        return _parts(year)[2]
    except (TypeError, ValueError):
        return ""


def off(made, year):
    """How many years an item made in `made` falls outside the era of `year` (0 when inside it, None if unknown)."""
    try:
        a, b = span(year)
        m = int(str(made)[:4])
    except (TypeError, ValueError):
        return None
    if not 1800 < m < 2200:
        return None
    return 0 if a <= m <= b else (a - m if m < a else m - b)


def describe(year):
    """'90s (1990-1999)' - for questions to your AI."""
    a, b = span(year)
    w = words(year)
    return f"{w} ({a}-{b})" if w else "unknown era"


def in_words(text, year):
    """A search with one exact year in it, said with the era words instead: "duracell AA 1998 back" ->
    "duracell AA 90s back" (any year inside the item's era; years outside it are left alone)."""
    import re
    a, b = span(year)
    w = words(year)
    if not w:
        return text
    out = re.sub(r"\b(19\d\d|20\d\d)s?\b", lambda m: w if a <= int(m.group(1)) <= b else m.group(0), str(text))
    return " ".join(dict.fromkeys(out.split()))          # "90s ... 90s" -> once
