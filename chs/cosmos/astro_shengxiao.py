"""
Cosmic Scout — cosmos/astro_shengxiao.py  (v1.1.0 — Monday 9 November 2026)

The twelve-animal system (Shengxiao) — a first-class, lived tradition, carried on
its own terms and TRADITIONAL-badged (which means "presented on its own terms,"
never "lesser"). Calendrical, not sky-derived, but housed under cosmos/ as a
birth-sign system the user reads their date into.

Two elements, kept distinct so they are never conflated:
  * Year element (the Heavenly Stem) — this is the "Water Tiger" naming. It cycles
    Wood -> Fire -> Earth -> Metal -> Water across the 60-year sexagenary cycle.
  * Fixed element (the Earthly Branch) — the animal's own intrinsic element
    (Tiger is Wood in every year), used for compatibility.

Year boundary: the animal flips at Li Chun (Start of Spring, apparent solar
longitude 315 deg, ~Feb 3-4), computed from the bundled ephemeris in the ecliptic
of date and compared with the exact birth instant. This is the
traditionalist/professional boundary; popular custom uses Lunar New Year instead,
so pop sources may differ for late-Jan / early-Feb births. The page says so.

Pure compute at module top (ephem imported lazily). build_page() renders the
light-themed page.
"""

from datetime import date, datetime, timedelta
from cosmos._links_section import build_links_card

_LINKS_NOTE = "Opens in your browser \u2014 yours to change, replace, or add to."

# Earthly Branches, in order. (pinyin, animal, fixed element)
BRANCHES = [
    ("Zi",   "Rat",     "Water"), ("Chou", "Ox",      "Earth"),
    ("Yin",  "Tiger",   "Wood"),  ("Mao",  "Rabbit",  "Wood"),
    ("Chen", "Dragon",  "Earth"), ("Si",   "Snake",   "Fire"),
    ("Wu",   "Horse",   "Fire"),  ("Wei",  "Goat",    "Earth"),
    ("Shen", "Monkey",  "Metal"), ("You",  "Rooster", "Metal"),
    ("Xu",   "Dog",     "Earth"), ("Hai",  "Pig",     "Water"),
]
STEM_ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]  # by stem//2

TRAITS = {
    "Rat":     "Resourceful, quick-witted, adaptable; thrifty and alert.",
    "Ox":      "Steady, patient, dependable; hard-working and resolute.",
    "Tiger":   "Bold, competitive, energetic; a confident risk-taker.",
    "Rabbit":  "Gentle, tactful, sensitive; diplomatic and refined.",
    "Dragon":  "Ambitious, charismatic, spirited; a natural leader.",
    "Snake":   "Wise, private, perceptive; deliberate and elegant.",
    "Horse":   "Free-spirited, active, generous; independent and warm.",
    "Goat":    "Kind, artistic, empathetic; calm and considerate.",
    "Monkey":  "Clever, playful, inventive; sociable and curious.",
    "Rooster": "Observant, diligent, forthright; organised and proud.",
    "Dog":     "Loyal, honest, protective; fair-minded and prudent.",
    "Pig":     "Generous, sincere, easy-going; diligent and content.",
}

# San He — the four affinity trines
TRINES = [
    ["Rat", "Dragon", "Monkey"],
    ["Ox", "Snake", "Rooster"],
    ["Tiger", "Horse", "Dog"],
    ["Rabbit", "Goat", "Pig"],
]
# Liu He — secret-friend pairs
SECRET_FRIEND = {
    "Rat": "Ox", "Ox": "Rat", "Tiger": "Pig", "Pig": "Tiger",
    "Rabbit": "Dog", "Dog": "Rabbit", "Dragon": "Rooster", "Rooster": "Dragon",
    "Snake": "Monkey", "Monkey": "Snake", "Horse": "Goat", "Goat": "Horse",
}

_ANIMALS = [b[1] for b in BRANCHES]
_LI_CHUN_CACHE = {}


def _li_chun(year):
    """UTC datetime of Li Chun (solar longitude 315 deg) for a Gregorian year."""
    if year in _LI_CHUN_CACHE:
        return _LI_CHUN_CACHE[year]
    import math
    import ephem

    def solar_lon(d):
        # ecliptic of date (epoch=d); pyephem's default J2000 frame drifts ~1 day per century
        return math.degrees(ephem.Ecliptic(ephem.Sun(d), epoch=d).lon) % 360.0

    def signed(d):  # distance to 315, wrapped to [-180,180]
        return (solar_lon(d) - 315.0 + 180.0) % 360.0 - 180.0

    lo = ephem.Date(datetime(year, 1, 20))
    hi = ephem.Date(datetime(year, 2, 20))
    for _ in range(60):
        mid = (lo + hi) / 2
        if signed(lo) * signed(mid) <= 0:
            hi = mid
        else:
            lo = mid
    result = ephem.Date((lo + hi) / 2).datetime()
    _LI_CHUN_CACHE[year] = result
    return result


def _birth_utc(d, birth_time=None, utc_offset=0.0):
    """UTC instant of a local birth date + optional "HH:MM" (noon when unknown)."""
    hh, mm = (int(x) for x in birth_time.split(":")) if birth_time else (12, 0)
    return datetime(d.year, d.month, d.day, hh, mm) - timedelta(hours=float(utc_offset or 0.0))


def solar_year(d, birth_time=None, utc_offset=0.0):
    """The sexagenary (Li Chun) year a Gregorian date falls in. Compares the exact
    birth instant (local time + UTC offset; noon when the time is unknown) with
    the exact Li Chun instant."""
    return d.year if _birth_utc(d, birth_time, utc_offset) >= _li_chun(d.year) else d.year - 1


def is_li_chun_day(d, utc_offset=0.0):
    """True when local date d is the day Li Chun falls on, so the year (and the
    animal) depends on the birth time."""
    lc_local = _li_chun(d.year) + timedelta(hours=float(utc_offset or 0.0))
    return lc_local.date() == d


def pillar_for_year(y):
    """(stem_index, branch_index) for a sexagenary solar year."""
    return (y - 4) % 10, (y - 4) % 12


def _animal_record(y):
    stem, branch = pillar_for_year(y)
    pinyin, animal, fixed = BRANCHES[branch]
    year_elem = STEM_ELEMENTS[stem // 2]
    year_yy = "Yang" if stem % 2 == 0 else "Yin"
    animal_yy = "Yang" if branch % 2 == 0 else "Yin"
    return {
        "solar_year": y,
        "animal": animal,
        "branch": pinyin,
        "fixed_element": fixed,        # the animal's intrinsic element
        "year_element": year_elem,     # the stem element -> "Water Tiger"
        "year_yin_yang": year_yy,
        "animal_yin_yang": animal_yy,
        "name": "%s %s" % (year_elem, animal),   # headline, e.g. "Water Tiger"
        "traits": TRAITS[animal],
    }


def animal_for_year(birth_date_iso, birth_time=None, utc_offset=0.0):
    """Full record for a birth date (+ optional birth time and UTC offset), or
    None. "li_chun_unsure" is True when the birth time is unknown and the birth
    falls on Li Chun day, so the animal could be either year's."""
    try:
        d = date.fromisoformat(birth_date_iso)
    except (ValueError, TypeError):
        return None
    rec = _animal_record(solar_year(d, birth_time, utc_offset))
    rec["li_chun_unsure"] = (not birth_time) and is_li_chun_day(d, utc_offset)
    return rec


def _trine_of(animal):
    for t in TRINES:
        if animal in t:
            return [a for a in t if a != animal]
    return []


def _clash_of(animal):
    return _ANIMALS[(_ANIMALS.index(animal) + 6) % 12]


def relationship(a, b):
    """How animal a meets animal b: your-year / trine / friend / clash / neutral."""
    if a == b:
        return "same"
    if b in _trine_of(a):
        return "trine"
    if SECRET_FRIEND.get(a) == b:
        return "friend"
    if _clash_of(a) == b:
        return "clash"
    return "neutral"


# ===========================================================================
# UI
# ===========================================================================
def build_page(state):
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QPushButton,
    )
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import Qt, QUrl

    from ui.theme import LIGHT, BADGE_COLORS_LIGHT

    ELEMENT_COLOR = {
        "Wood": "#5c8a4a", "Fire": "#c0623c", "Earth": "#b58a3c",
        "Metal": "#8a8f98", "Water": "#3c78c0",
    }

    def card():
        f = QFrame()
        f.setObjectName("Card")
        f.setStyleSheet("QFrame#Card{background:%s;border:1px solid %s;border-radius:10px;}"
                        % (LIGHT["panel"], LIGHT["border"]))
        return f

    def badge(text):
        b = QLabel(text)
        b.setStyleSheet("color:%s;background:rgba(0,0,0,20);padding:2px 9px;border-radius:8px;"
                        "font-weight:bold;font-size:11px;" % BADGE_COLORS_LIGHT.get(text, "#888"))
        b.setFixedHeight(19)
        return b

    def head_row(title, badge_text=None):
        row = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
        row.addWidget(t)
        if badge_text:
            row.addWidget(badge(badge_text))
        row.addStretch(1)
        return row

    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer.addWidget(scroll)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28)
    lay.setSpacing(16)
    scroll.setWidget(body)

    h = QHBoxLayout()
    title = QLabel("Sh\u0113ngxi\u00e0o \u00b7 Twelve Animals")
    title.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    h.addWidget(title)
    h.addWidget(badge("TRADITIONAL"))
    h.addStretch(1)
    lay.addLayout(h)
    sub = QLabel("Your birth animal and its nature \u2014 a living tradition carried on "
                 "its own terms, not reduced to science.")
    sub.setWordWrap(True)
    sub.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    profile = getattr(state, "active_profile", None)
    if profile is None:
        empty = card()
        el = QVBoxLayout(empty)
        el.setContentsMargins(20, 24, 20, 24)
        m = QLabel("No profile yet. Create one in Records \u2192 Profile to see your animal.")
        m.setWordWrap(True)
        m.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        el.addWidget(m)
        lay.addWidget(empty)
        lay.addWidget(build_links_card(state, page, "shengxiao", card, _LINKS_NOTE))
        lay.addStretch(1)
        return page

    time_known = bool(profile.birth_time_known and profile.birth_time)
    rec = animal_for_year(profile.birth_date,
                          profile.birth_time if time_known else None,
                          profile.utc_offset)
    if rec is None:
        m = QLabel("Add a birth date to your profile to see your animal.")
        m.setStyleSheet("color:%s;" % LIGHT["text"])
        lay.addWidget(m)
        lay.addWidget(build_links_card(state, page, "shengxiao", card, _LINKS_NOTE))
        lay.addStretch(1)
        return page

    year_col = ELEMENT_COLOR.get(rec["year_element"], LIGHT["text"])
    fixed_col = ELEMENT_COLOR.get(rec["fixed_element"], LIGHT["subtle"])

    # --- Your animal ---
    c1 = card()
    c1l = QVBoxLayout(c1)
    c1l.setContentsMargins(20, 16, 20, 18)
    c1l.setSpacing(8)
    c1l.addLayout(head_row("Your Animal", "TRADITIONAL"))
    name = QLabel(rec["name"])
    name.setStyleSheet("font-size:26px;font-weight:bold;color:%s;" % year_col)
    c1l.addWidget(name)
    meta = QLabel("%s branch \u00b7 %s (year) \u00b7 sexagenary year %d"
                  % (rec["branch"], rec["year_yin_yang"], rec["solar_year"]))
    meta.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    c1l.addWidget(meta)
    traits = QLabel(rec["traits"])
    traits.setWordWrap(True)
    traits.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
    c1l.addWidget(traits)
    elem_note = QLabel(
        "Two elements, kept distinct: the <b>year element</b> is "
        "<b style='color:%s'>%s</b> (this is the \u201c%s\u201d in your sign's name); the "
        "%s's own <b>fixed element</b> is <b style='color:%s'>%s</b>, used for compatibility."
        % (year_col, rec["year_element"], rec["year_element"],
           rec["animal"], fixed_col, rec["fixed_element"]))
    elem_note.setWordWrap(True)
    elem_note.setStyleSheet("color:%s;font-size:11px;" % LIGHT["subtle"])
    c1l.addWidget(elem_note)
    if rec["li_chun_unsure"]:
        unsure = QLabel("You were born on Li Chun day, when the animal changes. Without "
                        "a birth time this uses noon; add your birth time in Records "
                        "\u2192 Profile to settle which year's animal is yours.")
        unsure.setWordWrap(True)
        unsure.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
        c1l.addWidget(unsure)
    lay.addWidget(c1)

    # --- This year ---
    today = date.today()
    cur = _animal_record(solar_year(today))
    rel = relationship(rec["animal"], cur["animal"])
    rel_txt = {
        "same": "This is your <b>zodiac year</b> (ben ming nian) \u2014 traditionally a year "
                "to move carefully rather than an automatically lucky one.",
        "trine": "Your animal and this year's are in the same <b>affinity trine</b> \u2014 "
                 "held to be a harmonious, well-supported year.",
        "friend": "This year's animal is your <b>secret friend</b> \u2014 held to be a "
                  "quietly favourable, supportive year.",
        "clash": "This year's animal is your <b>clash</b> (opposite) \u2014 tradition reads "
                 "it as a friction year that rewards patience.",
        "neutral": "A <b>neutral</b> year in the tradition \u2014 neither strong affinity "
                   "nor clash.",
    }[rel]
    c2 = card()
    c2l = QVBoxLayout(c2)
    c2l.setContentsMargins(20, 16, 20, 18)
    c2l.setSpacing(8)
    c2l.addLayout(head_row("This Year", "TRADITIONAL"))
    cy = QLabel("%d is the year of the <b style='color:%s'>%s</b>."
                % (today.year, ELEMENT_COLOR.get(cur["year_element"], LIGHT["text"]), cur["name"]))
    cy.setWordWrap(True)
    cy.setStyleSheet("color:%s;font-size:13px;" % LIGHT["text"])
    c2l.addWidget(cy)
    rl = QLabel(rel_txt)
    rl.setWordWrap(True)
    rl.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
    c2l.addWidget(rl)
    lay.addWidget(c2)

    # --- Compatibility ---
    trine = _trine_of(rec["animal"])
    friend = SECRET_FRIEND.get(rec["animal"], "\u2014")
    clash = _clash_of(rec["animal"])
    c3 = card()
    c3l = QVBoxLayout(c3)
    c3l.setContentsMargins(20, 16, 20, 18)
    c3l.setSpacing(6)
    c3l.addLayout(head_row("Compatibility", "TRADITIONAL"))
    for label, val, col in (
        ("Affinity trine", ", ".join(trine), LIGHT["accent"]),
        ("Secret friend", friend, LIGHT["accent"]),
        ("Clash (opposite)", clash, LIGHT["neg"]),
    ):
        row = QLabel("<b>%s:</b> <span style='color:%s'>%s</span>" % (label, col, val))
        row.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        c3l.addWidget(row)
    lay.addWidget(c3)

    # --- Boundary honesty ---
    c4 = card()
    c4l = QVBoxLayout(c4)
    c4l.setContentsMargins(20, 14, 20, 16)
    note = QLabel(
        "Boundary note: this uses <b>Li Chun</b> (Start of Spring, ~Feb 3\u20134) \u2014 the "
        "boundary used by traditionalists and professional astrologers. Popular custom "
        "changes the animal at <b>Lunar New Year</b> instead, so pop sources may give a "
        "different animal for a late-January or early-February birth.")
    note.setWordWrap(True)
    note.setStyleSheet("color:%s;font-size:11px;" % LIGHT["subtle"])
    c4l.addWidget(note)
    lay.addWidget(c4)

    lay.addWidget(build_links_card(state, page, "shengxiao", card, _LINKS_NOTE))
    lay.addStretch(1)
    return page
