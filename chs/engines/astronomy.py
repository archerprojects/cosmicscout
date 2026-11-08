"""
Cosmic Scout — engines/astronomy.py  (v1.0.1 — Sunday 8 November 2026)

The Moon & Sky engine: moon phase, solar events, and approximate eclipse
detection, all computed offline from ephem. VALIDATED — this is astronomy, not
divination. Geocentric (phase, terms and eclipses are effectively global); local
rise/set and tides are a separate concern and not computed here.

Public API:
    moon_phase(dt)            -> dict(illumination, waxing, phase_name, age_days,
                                      next_new, next_full, next_first_quarter,
                                      next_last_quarter)
    full_moon_name(month)     -> dict(primary, alternates, note)
    is_blue_moon(dt_full)     -> bool
    solar_events(year)        -> list[dict(name, when)]
    next_eclipses(dt, count)  -> list[dict(kind, when, approx)]

Eclipse detection is APPROXIMATE: it flags a syzygy as an eclipse when the Moon
is close enough to a node (|ecliptic latitude| below a limit). Verified to catch
the known 2026 eclipses with no false positives, but it does not compute
magnitude, type (total/partial/annular) or visibility.
"""

import math
from datetime import datetime

import ephem

SYNODIC = 29.530588853

_PHASE_NAMES = ["New", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
                "Full", "Waning Gibbous", "Last Quarter", "Waning Crescent"]

# Northern-Hemisphere Farmers'-Almanac tradition (provenance stated on the page).
_FULL_MOON_NAMES = {
    1:  ("Wolf Moon",       ["Quiet Moon", "Cold Moon"]),
    2:  ("Snow Moon",       ["Hunger Moon", "Storm Moon"]),
    3:  ("Worm Moon",       ["Crow Moon", "Sap Moon"]),
    4:  ("Pink Moon",       ["Sprouting Grass Moon", "Egg Moon"]),
    5:  ("Flower Moon",     ["Milk Moon", "Hare Moon"]),
    6:  ("Strawberry Moon", ["Dyad Moon", "Lotus Moon"]),
    7:  ("Buck Moon",       ["Thunder Moon", "Hay Moon"]),
    8:  ("Sturgeon Moon",   ["Grain Moon", "Green Corn Moon"]),
    9:  ("Harvest Moon",    ["Barley Moon", "Chrysanthemum Moon"]),
    10: ("Hunter's Moon",   ["Blood Moon", "Falling Leaves Moon"]),
    11: ("Beaver Moon",     ["Frost Moon", "Mourning Moon"]),
    12: ("Cold Moon",       ["Oak Moon", "Bitter Moon"]),
}


def _dt(ephem_date):
    return ephem.Date(ephem_date).datetime()


def moon_phase(dt=None):
    """Phase state for a datetime (UTC). dt=None -> now."""
    d = ephem.Date(dt) if dt is not None else ephem.now()
    prev_new = ephem.previous_new_moon(d)
    next_new = ephem.next_new_moon(d)
    lunation = float(next_new) - float(prev_new)
    frac = (float(d) - float(prev_new)) / lunation if lunation else 0.0
    name = _PHASE_NAMES[int(round(frac / 0.125)) % 8]
    return {
        "illumination": round(ephem.Moon(d).phase, 1),   # percent illuminated
        "waxing": frac < 0.5,
        "phase_name": name,
        "age_days": round((float(d) - float(prev_new)), 1),
        "next_new": _dt(next_new),
        "next_full": _dt(ephem.next_full_moon(d)),
        "next_first_quarter": _dt(ephem.next_first_quarter_moon(d)),
        "next_last_quarter": _dt(ephem.next_last_quarter_moon(d)),
    }


def full_moon_name(month):
    primary, alternates = _FULL_MOON_NAMES[month]
    return {"primary": primary, "alternates": alternates,
            "note": "Northern-Hemisphere Farmers'-Almanac tradition."}


def is_blue_moon(dt_full):
    """True if the full moon at dt_full is the second full moon in its month."""
    d = ephem.Date(dt_full)
    prev_full = ephem.previous_full_moon(ephem.Date(float(d) - 1))
    p = _dt(prev_full)
    f = _dt(d)
    return p.year == f.year and p.month == f.month


def solar_events(year):
    """Equinoxes, solstices, perihelion and aphelion for a calendar year (UTC)."""
    events = []
    start = ephem.Date(datetime(year, 1, 1))
    end = ephem.Date(datetime(year + 1, 1, 1))

    # equinoxes + solstices, labelled by the Sun's ecliptic longitude
    labels = {0: "Spring Equinox", 90: "Summer Solstice",
              180: "Autumn Equinox", 270: "Winter Solstice"}
    d = start
    for _ in range(8):
        eq = ephem.next_equinox(d)
        so = ephem.next_solstice(d)
        nxt = eq if float(eq) < float(so) else so
        if float(nxt) >= float(end):
            break
        lon = round(math.degrees(ephem.Ecliptic(ephem.Sun(nxt), epoch=nxt).lon)) % 360
        key = min(labels, key=lambda k: min(abs(lon - k), 360 - abs(lon - k)))
        events.append({"name": labels[key], "when": _dt(nxt)})
        d = ephem.Date(float(nxt) + 1)

    # perihelion (min) / aphelion (max) Earth-Sun distance, scan then refine
    def dist(dd):
        return ephem.Sun(dd).earth_distance
    lo_d = start
    hi_d = start
    lo_v = dist(start)
    hi_v = lo_v
    dd = start
    while float(dd) < float(end):
        v = dist(dd)
        if v < lo_v:
            lo_v, lo_d = v, dd
        if v > hi_v:
            hi_v, hi_d = v, dd
        dd = ephem.Date(float(dd) + 1)
    events.append({"name": "Perihelion", "when": _dt(lo_d)})
    events.append({"name": "Aphelion", "when": _dt(hi_d)})

    events.sort(key=lambda e: e["when"])
    return events


def next_eclipses(dt=None, count=4):
    """Upcoming approximate eclipses. Solar at new moon, lunar at full moon,
    flagged when the Moon is near a node."""
    d = ephem.Date(dt) if dt is not None else ephem.now()
    SOLAR_LIMIT = 1.5    # deg ecliptic latitude
    LUNAR_LIMIT = 1.0
    out = []
    cursor = d
    guard = 0
    while len(out) < count and guard < 60:
        guard += 1
        nm = ephem.next_new_moon(cursor)
        fm = ephem.next_full_moon(cursor)
        nxt = nm if float(nm) < float(fm) else fm
        is_new = float(nm) < float(fm)
        lat = abs(math.degrees(ephem.Ecliptic(ephem.Moon(nxt), epoch=nxt).lat))
        if is_new and lat < SOLAR_LIMIT:
            out.append({"kind": "Solar eclipse", "when": _dt(nxt), "approx": True})
        elif (not is_new) and lat < LUNAR_LIMIT:
            out.append({"kind": "Lunar eclipse", "when": _dt(nxt), "approx": True})
        cursor = ephem.Date(float(nxt) + 1)
    return out
