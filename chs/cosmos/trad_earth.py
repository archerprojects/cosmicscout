"""
Cosmic Scout — cosmos/trad_earth.py  (v1.0.1 — Sunday 8 November 2026)

Earth Traditions — a set of birth-sign systems from around the world, each carried
on its own terms with honest provenance. Every section states plainly what it is:
genuinely ancient, or a modern synthesis. TRADITIONAL badge throughout (which means
"on its own terms," never "lesser"), except the app's own archetype convergence,
which is presented as the app's framework.

Sections
  * Archetypes      — the app's 12-station convergence, keyed to the Sun sign.
  * Ogham           — Graves' Celtic tree calendar (The White Goddess, 1948).
                      MODERN druidic synthesis, not an attested ancient system.
  * Medicine Wheel  — Sun Bear / Bear Tribe Earth Astrology (1980). A MODERN
                      neo-shamanic creation, NOT an attested Indigenous system;
                      some Native communities object to its framing. Never labelled
                      "Native astrology."
  * Tzolk'in        — Maya 260-day sacred count. GENUINELY ancient, still in use.
                      Computed from the verified GMT correlation (JDN 584283 = 4 Ahau).
  * Arabic mansions — the 28 lunar mansions (al-manazil). An ancient system; the
                      mansion is read from the Moon's ecliptic longitude at birth.
  * Egyptian        — a MODERN synthesis mapping Egyptian deities to the solar
                      months. NOT an ancient Egyptian system.
  * Tibetan         — the 12 animals reached Tibet from China via Buddhism (~7th-8th
                      c. CE); shown in its Buddhist framing.
  * Personal Year   — Western numerology's 9-year cycle.

Pure compute at top (ephem only for the Arabic mansion's Moon longitude).
"""

from datetime import date

from cosmos.astro_tropical import sun_sign
from cosmos.astro_shengxiao import animal_for_year

_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
          "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# --- the app's archetype convergence (Aries -> Pisces) ---
ARCHETYPES = [
    ("Pioneer / Warrior",   "the spark that begins; courage to go first."),
    ("Earth Keeper",        "steadiness, the body, what endures and is tended."),
    ("Messenger / Trickster", "connection, language, the play of ideas."),
    ("Nurturer / Mother",   "care, belonging, the making of a home."),
    ("Sovereign / Ruler",   "radiance, the courage to be seen and to lead."),
    ("Healer / Analyst",    "service, discernment, the craft of making whole."),
    ("Harmoniser / Bridge", "balance, relationship, the meeting of opposites."),
    ("Depth Seeker",        "intensity, transformation, what lies beneath."),
    ("Seeker / Wanderer",   "the horizon, meaning, the long journey out."),
    ("Elder / Builder",     "mastery, structure, the long view and the summit."),
    ("Visionary / Rebel",   "the future, the outsider's clarity, the new pattern."),
    ("Mystic / Dreamer",    "dissolution, compassion, the return to the whole."),
]

# --- Ogham: Graves' 13-tree calendar (modern druidic) ---
OGHAM = [
    ((12, 24), (1, 20), "Birch (Beth)"), ((1, 21), (2, 17), "Rowan (Luis)"),
    ((2, 18), (3, 17), "Ash (Nion)"), ((3, 18), (4, 14), "Alder (Fearn)"),
    ((4, 15), (5, 12), "Willow (Saille)"), ((5, 13), (6, 9), "Hawthorn (Huath)"),
    ((6, 10), (7, 7), "Oak (Duir)"), ((7, 8), (8, 4), "Holly (Tinne)"),
    ((8, 5), (9, 1), "Hazel (Coll)"), ((9, 2), (9, 29), "Vine (Muin)"),
    ((9, 30), (10, 27), "Ivy (Gort)"), ((10, 28), (11, 24), "Reed (Ngetal)"),
    ((11, 25), (12, 23), "Elder (Ruis)"),
]

# --- Medicine Wheel: Sun Bear's canonical moons + totems (modern neo-shamanic) ---
MEDICINE_WHEEL = [
    ((12, 22), (1, 19), "Earth Renewal", "Snow Goose"),
    ((1, 20), (2, 18), "Rest and Cleansing", "Otter"),
    ((2, 19), (3, 20), "Big Winds", "Cougar"),
    ((3, 21), (4, 19), "Budding Trees", "Red Hawk"),
    ((4, 20), (5, 20), "Frogs Return", "Beaver"),
    ((5, 21), (6, 20), "Corn Planting", "Deer"),
    ((6, 21), (7, 21), "Strong Sun", "Flicker"),
    ((7, 22), (8, 21), "Ripe Berries", "Sturgeon"),
    ((8, 22), (9, 21), "Harvest", "Brown Bear"),
    ((9, 22), (10, 22), "Ducks Fly", "Raven"),
    ((10, 23), (11, 21), "Freeze Up", "Snake"),
    ((11, 22), (12, 21), "Long Snows", "Elk"),
]

# --- Egyptian: modern synthesis, one deity per solar month (Aries -> Pisces) ---
EGYPTIAN = ["Horus", "Hathor", "Thoth", "Khonsu", "Ra", "Isis",
            "Ma'at", "Anubis", "Neith", "Khnum", "Nut", "Osiris"]

# --- Maya Tzolk'in ---
_TZOLKIN_SIGNS = ["Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik",
                  "Lamat", "Muluc", "Oc", "Chuen", "Eb", "Ben", "Ix", "Men",
                  "Cib", "Caban", "Etznab", "Cauac", "Ahau"]

# --- Arabic 28 lunar mansions (al-manazil) ---
_MANSIONS = [
    "Al Sharatain", "Al Butain", "Al Thurayya", "Al Dabaran", "Al Haq'ah",
    "Al Han'ah", "Al Dhira", "Al Nathrah", "Al Tarf", "Al Jabhah", "Al Zubrah",
    "Al Sarfah", "Al Awwa", "Al Simak", "Al Ghafr", "Al Zubana", "Al Iklil",
    "Al Qalb", "Al Shaulah", "Al Na'am", "Al Baldah", "Sa'd al-Dhabih",
    "Sa'd Bula", "Sa'd al-Su'ud", "Sa'd al-Akhbiyah", "Al Fargh al-Muqaddam",
    "Al Fargh al-Mu'akhkhar", "Batn al-Hut",
]

_PERSONAL_YEAR = {
    1: "New beginnings", 2: "Partnership", 3: "Expression", 4: "Foundation",
    5: "Change", 6: "Harmony", 7: "Reflection", 8: "Achievement", 9: "Completion",
}


def _parse(iso):
    try:
        return date.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


def _in_range(m, d, table):
    for start, end, *payload in table:
        if start <= end:
            hit = start <= (m, d) <= end
        else:  # year wrap
            hit = (m, d) >= start or (m, d) <= end
        if hit:
            return payload
    return None


def archetype(sign_name):
    if sign_name not in _ORDER:
        return None
    name, teaching = ARCHETYPES[_ORDER.index(sign_name)]
    return {"name": name, "teaching": teaching}


def ogham_sign(iso):
    d = _parse(iso)
    if d is None:
        return None
    p = _in_range(d.month, d.day, OGHAM)
    return p[0] if p else None


def medicine_wheel(iso):
    d = _parse(iso)
    if d is None:
        return None
    p = _in_range(d.month, d.day, MEDICINE_WHEEL)
    return {"moon": p[0], "totem": p[1]} if p else None


def egyptian_sign(sign_name):
    if sign_name not in _ORDER:
        return None
    return EGYPTIAN[_ORDER.index(sign_name)]


def tzolkin(iso):
    d = _parse(iso)
    if d is None:
        return None
    delta = (d.toordinal() + 1721425) - 584283      # JDN - GMT anchor (4 Ahau)
    name = _TZOLKIN_SIGNS[(19 + delta) % 20]
    tone = ((delta + 3) % 13) + 1
    return {"tone": tone, "sign": name}


def arabic_mansion(profile):
    """The lunar mansion from the Moon's ecliptic longitude at birth. Needs birth
    time for precision (the Moon moves ~13 deg/day ~ one mansion/day)."""
    import math
    import ephem
    d = _parse(profile.birth_date)
    if d is None:
        return None
    time_known = bool(profile.birth_time_known and profile.birth_time)
    hhmm = profile.birth_time if time_known else "12:00"
    off = float(profile.utc_offset or 0.0)
    dt = ephem.Date("%04d/%02d/%02d %s" % (d.year, d.month, d.day, hhmm)) - off / 24.0
    # ecliptic of date (epoch=dt), not pyephem's default J2000 frame
    lon = math.degrees(ephem.Ecliptic(ephem.Moon(dt), epoch=dt).lon) % 360.0
    idx = int(lon // (360.0 / 28))
    return {"index": idx + 1, "name": _MANSIONS[idx], "approx": not time_known}


def tibetan(iso, birth_time=None, utc_offset=0.0):
    rec = animal_for_year(iso, birth_time, utc_offset)
    if rec is None:
        return None
    return {"name": "%s %s" % (rec["year_element"], rec["animal"]),
            "animal": rec["animal"], "element": rec["year_element"]}


def personal_year(iso, year):
    d = _parse(iso)
    if d is None:
        return None
    total = d.month + d.day + year

    def reduce9(n):
        while n > 9:
            n = sum(int(c) for c in str(n))
        return n
    num = reduce9(total)
    return {"number": num, "theme": _PERSONAL_YEAR.get(num, "")}


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

    def card():
        f = QFrame(); f.setObjectName("Card")
        f.setStyleSheet("QFrame#Card{background:%s;border:1px solid %s;border-radius:10px;}"
                        % (LIGHT["panel"], LIGHT["border"]))
        return f

    def badge(text):
        b = QLabel(text)
        b.setStyleSheet("color:%s;background:rgba(0,0,0,20);padding:2px 9px;border-radius:8px;"
                        "font-weight:bold;font-size:11px;" % BADGE_COLORS_LIGHT.get(text, "#888"))
        b.setFixedHeight(19); return b

    def tradition(title, badge_text, value, body, note):
        c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(20, 14, 20, 16); cl.setSpacing(6)
        hr = QHBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
        hr.addWidget(t); hr.addWidget(badge(badge_text)); hr.addStretch(1)
        cl.addLayout(hr)
        v = QLabel(value); v.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["accent"])
        cl.addWidget(v)
        if body:
            b = QLabel(body); b.setWordWrap(True); b.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
            cl.addWidget(b)
        if note:
            n = QLabel(note); n.setWordWrap(True); n.setStyleSheet("font-size:10px;color:%s;" % LIGHT["subtle"])
            cl.addWidget(n)
        return c

    page = QWidget()
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer.addWidget(scroll)
    body = QWidget(); lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)
    scroll.setWidget(body)

    title = QLabel("Earth Traditions")
    title.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    lay.addWidget(title)
    sub = QLabel("Birth-sign systems from around the world, each on its own terms \u2014 "
                 "with honest provenance for what is ancient and what is modern.")
    sub.setWordWrap(True); sub.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    profile = getattr(state, "active_profile", None)
    if profile is None:
        c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(20, 24, 20, 24)
        m = QLabel("No profile yet. Create one in Records \u2192 Profile to read your date "
                   "into these traditions.")
        m.setWordWrap(True); m.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        cl.addWidget(m); lay.addWidget(c); lay.addStretch(1); return page

    bd = profile.birth_date
    ss = sun_sign(bd)
    sign = ss["sign"] if ss else None

    if sign:
        ar = archetype(sign)
        lay.addWidget(tradition(
            "Archetype", "TRADITIONAL", ar["name"], ar["teaching"],
            "The app's own 12-station convergence \u2014 the animal is local, the "
            "teaching is universal. Keyed to your Sun sign (%s)." % sign))

    og = ogham_sign(bd)
    if og:
        lay.addWidget(tradition(
            "Ogham \u00b7 Celtic Tree", "TRADITIONAL", og, "",
            "Robert Graves' tree calendar (The White Goddess, 1948) \u2014 a modern "
            "druidic synthesis, not a directly attested ancient Celtic system."))

    mw = medicine_wheel(bd)
    if mw:
        lay.addWidget(tradition(
            "Medicine Wheel", "TRADITIONAL", "%s \u2014 %s" % (mw["totem"], mw["moon"] + " Moon"), "",
            "From Sun Bear / the Bear Tribe's Earth Astrology (1980) \u2014 a modern "
            "neo-shamanic creation, NOT an attested Indigenous system, and one some "
            "Native communities object to. Offered on those terms, not as \u201cNative "
            "astrology.\u201d"))

    tz = tzolkin(bd)
    if tz:
        lay.addWidget(tradition(
            "Maya Tzolk'in", "TRADITIONAL", "%d %s" % (tz["tone"], tz["sign"]), "",
            "The 260-day sacred count \u2014 genuinely ancient and still kept by "
            "day-keepers in Guatemala. Computed from the standard GMT correlation."))

    am = arabic_mansion(profile)
    if am:
        note = ("The Moon's 28 daily mansions \u2014 an ancient system also mirrored in "
                "Indian nakshatra and Chinese xiu.")
        if am["approx"]:
            note += " Approximate: add your birth time for a precise mansion."
        lay.addWidget(tradition(
            "Arabic Lunar Mansion", "TRADITIONAL",
            "Mansion %d \u2014 %s" % (am["index"], am["name"]), "", note))

    if sign:
        eg = egyptian_sign(sign)
        lay.addWidget(tradition(
            "Egyptian", "TRADITIONAL", eg, "",
            "A modern synthesis mapping Egyptian deities to the solar months "
            "(via your Sun sign) \u2014 not an ancient Egyptian system."))

    tb = tibetan(bd, profile.birth_time if (profile.birth_time_known and profile.birth_time)
                 else None, profile.utc_offset)
    if tb:
        lay.addWidget(tradition(
            "Tibetan", "TRADITIONAL", tb["name"], "",
            "The same twelve animals reached Tibet from China via Buddhism (~7th-8th "
            "century CE), carried in a Buddhist karmic framework."))

    from datetime import date as _date
    py = personal_year(bd, _date.today().year)
    if py:
        lay.addWidget(tradition(
            "Personal Year", "TRADITIONAL", "%d \u2014 %s" % (py["number"], py["theme"]),
            "Your numerology year for %d." % _date.today().year,
            "Western numerology's 9-year cycle (birth month + day + current year, "
            "reduced)."))

    # --- editable out-links ---
    c5 = card(); c5l = QVBoxLayout(c5); c5l.setContentsMargins(20, 16, 20, 18); c5l.setSpacing(10)
    hr = QHBoxLayout()
    t5 = QLabel("Further Reading"); t5.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
    hr.addWidget(t5); hr.addStretch(1)
    edit_btn = QPushButton("Edit sources"); hr.addWidget(edit_btn)
    c5l.addLayout(hr)
    n5 = QLabel("Opens in your browser \u2014 yours to change, replace, or add to.")
    n5.setWordWrap(True); n5.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    c5l.addWidget(n5)
    links_box = QVBoxLayout(); links_box.setSpacing(6); c5l.addLayout(links_box)

    def render_links():
        while links_box.count():
            it = links_box.takeAt(0); w = it.widget()
            if w:
                w.deleteLater()
        for src in state.trad_earth_sources():
            b = QPushButton("%s  \u2197" % src["name"]); b.setStyleSheet("text-align:left;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, u=src["url"]: QDesktopServices.openUrl(QUrl(u)))
            links_box.addWidget(b)

    def open_editor():
        from cosmos._sources_dialog import SourcesDialog
        if SourcesDialog(state, page, sources_key="trad_earth").exec():
            render_links()

    edit_btn.clicked.connect(open_editor)
    render_links()
    lay.addWidget(c5)

    lay.addStretch(1)
    return page
