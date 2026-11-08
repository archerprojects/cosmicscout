"""
Cosmic Scout — cosmos/astro_tropical.py  (v1.0.1 — Sunday 8 November 2026)

The season-anchored (tropical) zodiac and the honest science that sits under it.
User-facing label: "Tropical Zodiac". Everything keyed to the profile is computed
locally — the birth data never leaves the device.

Four layers, graded separately per the evidence spine:

  * Sun sign / natal chart      TRADITIONAL — presented on its own terms.
      Constellation-determinism is contested when tested (Carlson 1985 + reanalyses);
      shown here as a tradition, not as a validated predictor.
  * Season of birth -> chronotype   VALIDATED (small, real, associational in humans).
      Channel: perinatal photoperiod imprints the SCN circadian clock. Demonstrated
      causally in mammals (Ciarleglio et al., Nature Neuroscience 2011); in humans,
      day-length at birth is *associated* with adult chronotype (Vollmer et al. 2012).
      A tendency, not a destiny; effect size is small.
  * Conception-window lens      CONTEXT (exploratory) — which trimesters met which
      photoperiod. Same perinatal-light channel, shown as developmental context.
  * Curated out-links           three named, contrasting voices; user-editable.
      Out-links only — no third-party text is reproduced.

Pure compute lives at module top (no Qt). build_page() assembles the light-themed
page and draws the wheel via ui.natal_wheel.NatalWheel.
"""

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Sign reference (tropical). element, modality, glyph, ruling planet, traits.
# Ruling planets and traits are TRADITIONAL reference (widely-published common
# attributions), not scientific claims — presented on their own terms.
# ---------------------------------------------------------------------------
SIGN_INFO = {
    "Aries":       ("Fire",  "Cardinal", "\u2648", "Mars",
        "Bold, direct, and driven; a natural initiator who leads from the front."),
    "Taurus":      ("Earth", "Fixed",    "\u2649", "Venus",
        "Steady, patient, and sensual; values comfort, loyalty, and the tangible."),
    "Gemini":      ("Air",   "Mutable",  "\u264A", "Mercury",
        "Curious, quick, and communicative; adaptable and endlessly interested."),
    "Cancer":      ("Water", "Cardinal", "\u264B", "Moon",
        "Nurturing, intuitive, and protective; deeply tied to home and feeling."),
    "Leo":         ("Fire",  "Fixed",    "\u264C", "Sun",
        "Warm, expressive, and proud; a generous heart that draws the spotlight."),
    "Virgo":       ("Earth", "Mutable",  "\u264D", "Mercury",
        "Precise, practical, and analytical; finds meaning in service and craft."),
    "Libra":       ("Air",   "Cardinal", "\u264E", "Venus",
        "Gracious, fair-minded, and relational; seeks balance, beauty, and harmony."),
    "Scorpio":     ("Water", "Fixed",    "\u264F", "Pluto (trad. Mars)",
        "Intense, perceptive, and determined; drawn to depth and transformation."),
    "Sagittarius": ("Fire",  "Mutable",  "\u2650", "Jupiter",
        "Optimistic, adventurous, and philosophical; a seeker of meaning and horizon."),
    "Capricorn":   ("Earth", "Cardinal", "\u2651", "Saturn",
        "Disciplined, ambitious, and responsible; builds for the long term."),
    "Aquarius":    ("Air",   "Fixed",    "\u2652", "Uranus (trad. Saturn)",
        "Independent, inventive, and humane; thinks ahead and values the collective."),
    "Pisces":      ("Water", "Mutable",  "\u2653", "Neptune (trad. Jupiter)",
        "Imaginative, empathic, and fluid; attuned to dream, art, and compassion."),
}

# sign start boundaries (month, day, sign). Dates before Aquarius' start and on/after
# Capricorn's start are Capricorn (year wrap). Fixed table -> date-only, no ephemeris.
_SIGN_BOUNDS = [
    (1, 20, "Aquarius"), (2, 19, "Pisces"), (3, 21, "Aries"), (4, 20, "Taurus"),
    (5, 21, "Gemini"), (6, 21, "Cancer"), (7, 23, "Leo"), (8, 23, "Virgo"),
    (9, 23, "Libra"), (10, 23, "Scorpio"), (11, 22, "Sagittarius"), (12, 22, "Capricorn"),
]

# approximate equinox/solstice day-of-year (non-leap; good to ~1 day)
_MAR_EQUINOX, _JUN_SOLSTICE, _SEP_EQUINOX, _DEC_SOLSTICE = 79, 172, 265, 355


def _parse(iso):
    try:
        return date.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Sun sign — local date-range lookup (works from the birth date alone)
# ---------------------------------------------------------------------------
def sun_sign(birth_date_iso):
    """Return {sign, element, modality, glyph, cusp} or None."""
    d = _parse(birth_date_iso)
    if d is None:
        return None
    sign = "Capricorn"
    for bm, bd, name in _SIGN_BOUNDS:
        if (d.month, d.day) >= (bm, bd):
            sign = name
    # cusp flag: within one day of any boundary in this year
    cusp = False
    for bm, bd, _ in _SIGN_BOUNDS:
        try:
            b = date(d.year, bm, bd)
        except ValueError:
            continue
        if abs((d - b).days) <= 1:
            cusp = True
            break
    elem, modality, glyph, ruler, traits = SIGN_INFO[sign]
    return {"sign": sign, "element": elem, "modality": modality,
            "glyph": glyph, "cusp": cusp, "ruler": ruler, "traits": traits}


# ---------------------------------------------------------------------------
# Season of birth — VALIDATED (small): perinatal photoperiod -> SCN -> chronotype
# ---------------------------------------------------------------------------
def _season(doy, north):
    """(season, lengthening, magnitude) for a day-of-year in a hemisphere."""
    if _MAR_EQUINOX <= doy < _JUN_SOLSTICE:
        season_n = "Spring"
    elif _JUN_SOLSTICE <= doy < _SEP_EQUINOX:
        season_n = "Summer"
    elif _SEP_EQUINOX <= doy < _DEC_SOLSTICE:
        season_n = "Autumn"
    else:
        season_n = "Winter"
    # daylength lengthening in the north from Dec solstice to Jun solstice
    lengthening_n = (doy >= _DEC_SOLSTICE) or (doy < _JUN_SOLSTICE)
    if north:
        season, lengthening = season_n, lengthening_n
    else:
        flip = {"Spring": "Autumn", "Summer": "Winter",
                "Autumn": "Spring", "Winter": "Summer"}
        season, lengthening = flip[season_n], (not lengthening_n)
    magnitude = {"Summer": "long", "Winter": "short"}.get(season, "moderate")
    return season, lengthening, magnitude


def season_of_birth(birth_date_iso, latitude):
    """Return the honest season-of-birth read, or None."""
    d = _parse(birth_date_iso)
    if d is None:
        return None
    north = (latitude is None) or (latitude >= 0)
    doy = d.timetuple().tm_yday
    season, lengthening, magnitude = _season(doy, north)
    trend = "lengthening" if lengthening else "shortening"
    # Vollmer 2012 direction: birth during lengthening days -> slightly later chronotype
    lean = "evening-leaning" if lengthening else "morning-leaning"
    near_equator = (latitude is not None) and (abs(latitude) < 10.0)
    return {
        "season": season,
        "hemisphere": "Northern" if north else "Southern",
        "daylength": magnitude,
        "trend": trend,
        "chronotype_lean": lean,
        "near_equator": near_equator,
    }


# ---------------------------------------------------------------------------
# Conception window — developmental-light CONTEXT (exploratory)
# ---------------------------------------------------------------------------
def conception_window(birth_date_iso, latitude):
    """Approx conception date (birth - 266d) and the season each trimester met."""
    d = _parse(birth_date_iso)
    if d is None:
        return None
    north = (latitude is None) or (latitude >= 0)
    conception = d - timedelta(days=266)
    trimesters = []
    for label, off in (("First", 45), ("Second", 133), ("Third", 224)):
        mid = conception + timedelta(days=off)
        season, lengthening, _ = _season(mid.timetuple().tm_yday, north)
        trimesters.append({"label": label, "mid": mid.isoformat(),
                           "season": season,
                           "trend": "lengthening" if lengthening else "shortening"})
    return {"conception": conception.isoformat(), "trimesters": trimesters}


# ---------------------------------------------------------------------------
# Natal chart — flatlib. Full wheel when birth time is known; else planets only.
# ---------------------------------------------------------------------------
_NATAL_IDS = None      # resolved lazily so the module imports without flatlib present


def _offset_string(utc_offset):
    """float hours -> flatlib '+HH:MM' / '-HH:MM'."""
    sign = "+" if utc_offset >= 0 else "-"
    mins = int(round(abs(utc_offset) * 60))
    return "%s%02d:%02d" % (sign, mins // 60, mins % 60)


def _aspects(planets):
    """Major aspects with tightened orbs (8 for luminaries, else 6)."""
    lum = {"Sun", "Moon"}
    out = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            a, b = planets[i], planets[j]
            sep = abs(a["lon"] - b["lon"]) % 360.0
            if sep > 180.0:
                sep = 360.0 - sep
            orb_allow = 8.0 if (a["name"] in lum or b["name"] in lum) else 6.0
            for ang in (0, 60, 90, 120, 180):
                delta = abs(sep - ang)
                if delta <= orb_allow:
                    out.append({"a": a["name"], "b": b["name"],
                                "angle": ang, "orb": round(delta, 2)})
                    break
    return out


def natal_chart(profile):
    """Compute a natal chart dict from a Profile, or None if uncomputable."""
    global _NATAL_IDS
    d = _parse(profile.birth_date)
    if d is None:
        return None

    from flatlib import const
    from flatlib.datetime import Datetime
    from flatlib.geopos import GeoPos
    from flatlib.chart import Chart

    if _NATAL_IDS is None:
        _NATAL_IDS = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
                      const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE,
                      const.PLUTO, const.NORTH_NODE]

    time_known = bool(profile.birth_time_known and profile.birth_time)
    hhmm = profile.birth_time if time_known else "12:00"
    dt = Datetime(d.strftime("%Y/%m/%d"), hhmm, _offset_string(profile.utc_offset or 0.0))
    pos = GeoPos(float(profile.latitude or 0.0), float(profile.longitude or 0.0))
    # Placidus explicitly: flatlib's own default is Alcabitius. Placidus is
    # undefined above the polar circles, so fall back to Porphyry there.
    house_system = "Placidus"
    try:
        chart = Chart(dt, pos, IDs=_NATAL_IDS, hsys=const.HOUSES_PLACIDUS)
    except Exception:
        house_system = "Porphyry"
        chart = Chart(dt, pos, IDs=_NATAL_IDS, hsys=const.HOUSES_PORPHYRIUS)

    planets = []
    for pid in _NATAL_IDS:
        o = chart.get(pid)
        try:
            retro = bool(o.isRetrograde())
        except Exception:
            retro = False
        planets.append({"name": o.id, "sign": o.sign, "lon": o.lon,
                        "signlon": o.signlon, "retro": retro})

    result = {
        "time_known": time_known,
        "planets": planets,
        "aspects": _aspects(planets),
        "asc": None, "mc": None, "houses": [], "house_system": house_system,
    }
    if time_known:
        asc, mc = chart.get(const.ASC), chart.get(const.MC)
        result["asc"] = {"lon": asc.lon, "sign": asc.sign}
        result["mc"] = {"lon": mc.lon, "sign": mc.sign}
        result["houses"] = [{"id": h.id, "lon": h.lon, "size": h.size}
                            for h in chart.houses]
    return result


# ===========================================================================
# UI
# ===========================================================================
DEFAULT_SOURCES = [
    {"name": "Cainer", "url": "https://www.cainer.com/daily-horoscope/"},
    {"name": "Free Will Astrology \u2014 Rob Brezsny", "url": "https://freewillastrology.com/"},
    {"name": "Astrology Zone \u2014 Susan Miller", "url": "https://www.astrologyzone.com/"},
]


def _deg(signlon):
    dd = int(signlon)
    mm = int(round((signlon - dd) * 60))
    if mm == 60:
        dd, mm = dd + 1, 0
    return "%d\u00b0%02d'" % (dd, mm)


def build_page(state):
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
        QGridLayout, QPushButton, QSizePolicy,
    )
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import Qt, QUrl

    from ui.theme import LIGHT, BADGE_COLORS_LIGHT
    from ui.natal_wheel import NatalWheel, ELEMENT_COLOR

    def badge(text):
        b = QLabel(text)
        col = BADGE_COLORS_LIGHT.get(text, "#888")
        b.setStyleSheet(
            "color:%s;background:rgba(0,0,0,20);padding:2px 9px;border-radius:8px;"
            "font-weight:bold;font-size:11px;" % col)
        b.setFixedHeight(19)
        return b

    def card():
        f = QFrame()
        f.setObjectName("Card")
        f.setStyleSheet("QFrame#Card{background:%s;border:1px solid %s;border-radius:10px;}"
                        % (LIGHT["panel"], LIGHT["border"]))
        return f

    def section_head(title, badge_text=None):
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

    # header
    head = QHBoxLayout()
    title = QLabel("Tropical Zodiac")
    title.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    head.addWidget(title)
    head.addStretch(1)
    lay.addLayout(head)
    sub = QLabel("Your season-anchored sign and natal chart, computed locally from "
                 "your birth data \u2014 alongside the honest science of birth timing.")
    sub.setWordWrap(True)
    sub.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    profile = getattr(state, "active_profile", None)
    if profile is None:
        empty = card()
        el = QVBoxLayout(empty)
        el.setContentsMargins(20, 24, 20, 24)
        msg = QLabel("No profile yet. Create one in Records \u2192 Profile to see "
                     "your sign, chart, and birth-timing read.")
        msg.setWordWrap(True)
        msg.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        el.addWidget(msg)
        lay.addWidget(empty)
        lay.addStretch(1)
        return page

    chart = natal_chart(profile)
    ss = sun_sign(profile.birth_date)

    # --- Sun sign (from the chart's Sun when available, else the date table) ---
    sun_from_chart = None
    if chart:
        for pl in chart["planets"]:
            if pl["name"] == "Sun":
                sun_from_chart = pl
                break
    sign_name = sun_from_chart["sign"] if sun_from_chart else (ss["sign"] if ss else None)
    if sign_name:
        elem, modality, glyph, ruler, traits = SIGN_INFO[sign_name]
        c1 = card()
        cl = QHBoxLayout(c1)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(16)
        gl = QLabel(glyph)
        gl.setStyleSheet("font-size:38px;color:%s;" % ELEMENT_COLOR[elem])
        cl.addWidget(gl, 0, Qt.AlignmentFlag.AlignTop)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        name = QLabel("Sun in %s" % sign_name)
        name.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["text"])
        meta = QLabel("%s \u00b7 %s \u00b7 ruled by %s" % (elem, modality, ruler))
        meta.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
        txt.addWidget(name)
        txt.addWidget(meta)
        trait_lbl = QLabel(traits)
        trait_lbl.setWordWrap(True)
        trait_lbl.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        txt.addWidget(trait_lbl)
        if ss and ss["cusp"]:
            cusp = QLabel("Born near a sign boundary \u2014 you may also identify "
                          "with the neighbouring sign.")
            cusp.setWordWrap(True)
            cusp.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
            txt.addWidget(cusp)
        cl.addLayout(txt)
        cl.addStretch(1)
        lay.addWidget(c1)

    # --- Natal chart: wheel + positions ---
    natal_card = card()
    ncl = QVBoxLayout(natal_card)
    ncl.setContentsMargins(20, 16, 20, 18)
    ncl.setSpacing(12)
    ncl.addLayout(section_head("Natal Chart", "TRADITIONAL"))

    if not chart:
        ncl.addWidget(QLabel("Add a birth date to your profile to draw your chart."))
    else:
        if not chart["time_known"]:
            note = QLabel("Birth time not set \u2014 showing planetary sign positions only. "
                          "Houses, the Ascendant and the Midheaven need your exact birth "
                          "time; the Moon may shift sign within a day.")
            note.setWordWrap(True)
            note.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
            ncl.addWidget(note)
        elif chart["house_system"] != "Placidus":
            note = QLabel("Placidus houses can't be drawn this close to the pole, so "
                          "the houses use the Porphyry system. The Ascendant and "
                          "Midheaven are exact.")
            note.setWordWrap(True)
            note.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
            ncl.addWidget(note)

        wheel_row = QHBoxLayout()
        wheel_row.setSpacing(18)
        wheel = NatalWheel(chart)
        wheel.setMinimumSize(380, 380)
        wheel_row.addWidget(wheel, 3)

        # positions grid
        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        from ui.natal_wheel import PLANET_GLYPH
        hdr = ["", "Body", "Sign", "Pos", ""]
        for cidx, htext in enumerate(hdr):
            hl = QLabel(htext)
            hl.setStyleSheet("color:%s;font-weight:bold;font-size:10px;" % LIGHT["subtle"])
            grid.addWidget(hl, 0, cidx)
        for ridx, pl in enumerate(chart["planets"], start=1):
            elem = SIGN_INFO.get(pl["sign"], ("Air", "", ""))[0]
            g = QLabel(PLANET_GLYPH.get(pl["name"], ""))
            g.setStyleSheet("font-size:15px;color:%s;" % LIGHT["text"])
            grid.addWidget(g, ridx, 0)
            nm = QLabel(pl["name"])
            nm.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
            grid.addWidget(nm, ridx, 1)
            sg = QLabel(pl["sign"])
            sg.setStyleSheet("font-size:12px;color:%s;" % ELEMENT_COLOR.get(elem, LIGHT["text"]))
            grid.addWidget(sg, ridx, 2)
            dg = QLabel(_deg(pl["signlon"]))
            dg.setStyleSheet("font-size:12px;color:%s;" % LIGHT["subtle"])
            grid.addWidget(dg, ridx, 3)
            if pl["retro"]:
                rl = QLabel("\u211E")
                rl.setStyleSheet("font-size:12px;color:%s;" % LIGHT["neg"])
                grid.addWidget(rl, ridx, 4)
        if chart["time_known"] and chart["asc"] and chart["mc"]:
            base = len(chart["planets"]) + 1
            for k, (lbl, ang) in enumerate((("Asc", chart["asc"]), ("MC", chart["mc"]))):
                al = QLabel(lbl)
                al.setStyleSheet("font-size:12px;font-weight:bold;color:%s;" % LIGHT["accent"])
                grid.addWidget(al, base + k, 1)
                asg = QLabel(ang["sign"])
                asg.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
                grid.addWidget(asg, base + k, 2)
                adg = QLabel(_deg(ang["lon"] % 30))
                adg.setStyleSheet("font-size:12px;color:%s;" % LIGHT["subtle"])
                grid.addWidget(adg, base + k, 3)
        grid.setRowStretch(grid.rowCount(), 1)
        grid_wrap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        wheel_row.addWidget(grid_wrap, 2)
        ncl.addLayout(wheel_row)
    lay.addWidget(natal_card)

    # --- Season of birth (VALIDATED) ---
    sob = season_of_birth(profile.birth_date, profile.latitude)
    if sob:
        c3 = card()
        c3l = QVBoxLayout(c3)
        c3l.setContentsMargins(20, 16, 20, 18)
        c3l.setSpacing(8)
        c3l.addLayout(section_head("Season of Birth", "VALIDATED"))
        line1 = QLabel("You were born in <b>%s</b> (%s hemisphere), when days were "
                       "<b>%s</b> and <b>%s</b>."
                       % (sob["season"], sob["hemisphere"], sob["daylength"], sob["trend"]))
        line1.setWordWrap(True)
        line1.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        c3l.addWidget(line1)
        read = QLabel(
            "Day-length around birth is associated with adult <b>chronotype</b>: one "
            "line of evidence links birth during lengthening days to a slightly later "
            "(evening) rhythm. Your birth timing leans <b>%s</b> \u2014 a small tendency, "
            "not a rule. Today's light habits and sleep schedule matter far more."
            % sob["chronotype_lean"])
        read.setWordWrap(True)
        read.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        c3l.addWidget(read)
        chan = QLabel(
            "Channel: perinatal photoperiod imprints the SCN circadian clock \u2014 shown "
            "causally in mammals (Ciarleglio et al., <i>Nature Neuroscience</i> 2011); in "
            "humans it is an association (Vollmer et al. 2012). Effect size is small.")
        chan.setWordWrap(True)
        chan.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
        c3l.addWidget(chan)
        if sob["near_equator"]:
            eq = QLabel("Born near the equator: day-length barely varies with season, so "
                        "this effect is weaker still for you.")
            eq.setWordWrap(True)
            eq.setStyleSheet("font-size:11px;color:%s;" % LIGHT["warn"])
            c3l.addWidget(eq)
        lay.addWidget(c3)

    # --- Conception window (context) ---
    cw = conception_window(profile.birth_date, profile.latitude)
    if cw:
        c4 = card()
        c4l = QVBoxLayout(c4)
        c4l.setContentsMargins(20, 16, 20, 18)
        c4l.setSpacing(8)
        c4l.addLayout(section_head("Conception-Window Lens", "EMERGING"))
        intro = QLabel("Working back ~266 days from your birth places conception around "
                       "<b>%s</b>. Which photoperiod each trimester developed under is shown "
                       "below as developmental-light context \u2014 exploratory, not a prediction."
                       % cw["conception"])
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        c4l.addWidget(intro)
        for tri in cw["trimesters"]:
            row = QLabel("\u2022 <b>%s trimester</b> (~%s): %s, days %s"
                         % (tri["label"], tri["mid"], tri["season"], tri["trend"]))
            row.setWordWrap(True)
            row.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
            c4l.addWidget(row)
        lay.addWidget(c4)

    # --- Further reading (editable out-links) ---
    c5 = card()
    c5l = QVBoxLayout(c5)
    c5l.setContentsMargins(20, 16, 20, 18)
    c5l.setSpacing(10)
    head5 = QHBoxLayout()
    h5 = QLabel("Further Reading")
    h5.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
    head5.addWidget(h5)
    head5.addStretch(1)
    edit_btn = QPushButton("Edit sources")
    head5.addWidget(edit_btn)
    c5l.addLayout(head5)
    note5 = QLabel("Three contrasting voices \u2014 these open in your browser and are "
                   "yours to change.")
    note5.setWordWrap(True)
    note5.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    c5l.addWidget(note5)

    links_box = QVBoxLayout()
    links_box.setSpacing(6)
    c5l.addLayout(links_box)

    def render_links():
        while links_box.count():
            item = links_box.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for src in state.tropical_sources():
            b = QPushButton("%s  \u2197" % src["name"])
            b.setStyleSheet("text-align:left;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            url = src["url"]
            b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_box.addWidget(b)

    def open_editor():
        from cosmos._sources_dialog import SourcesDialog
        dlg = SourcesDialog(state, page)
        if dlg.exec():
            render_links()

    edit_btn.clicked.connect(open_editor)
    render_links()
    lay.addWidget(c5)

    lay.addStretch(1)
    return page
