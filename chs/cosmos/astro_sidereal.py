"""
Cosmic Scout — cosmos/astro_sidereal.py  (v1.0.1 — Sunday 8 November 2026)

Vedic (sidereal) astrology. The sidereal zodiac is fixed to the actual stars, not
the seasons, so it sits ~24 degrees behind the tropical zodiac (the ayanamsha).
Most people's sidereal Sun lands in the previous sign from their tropical one.

Built entirely on machinery already proven: the tropical natal chart (flatlib) is
computed once, then every longitude is shifted by the Lahiri ayanamsha (from
pyswisseph, evaluated at the birth instant) to get the sidereal chart. Because a
constant offset preserves angular separations, the aspects carry over unchanged.
The drawn wheel is the same NatalWheel used by the Tropical page.

Also derives the Janma Nakshatra — the lunar mansion (27 of them, 13 deg 20' each,
four padas) the Moon occupies in the sidereal zodiac. TRADITIONAL.

Deferred to Phase 2 (not built): the Vimshottari dasha timing system.
"""

from datetime import date

from cosmos.astro_tropical import natal_chart, _offset_string, SIGN_INFO

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]


def _ayanamsha(profile):
    """Lahiri ayanamsha (degrees) at the birth instant, from pyswisseph."""
    import swisseph as swe
    from flatlib.datetime import Datetime
    d = date.fromisoformat(profile.birth_date)
    time_known = bool(profile.birth_time_known and profile.birth_time)
    hhmm = profile.birth_time if time_known else "12:00"
    dt = Datetime(d.strftime("%Y/%m/%d"), hhmm, _offset_string(profile.utc_offset or 0.0))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(dt.jd)


def sidereal_chart(profile):
    """Sidereal (Lahiri) chart + Janma Nakshatra, or None."""
    trop = natal_chart(profile)
    if trop is None:
        return None
    ay = _ayanamsha(profile)

    def shift(lon):
        return (lon - ay) % 360.0

    def sign_of(lon):
        return SIGNS[int(lon // 30)]

    planets = []
    for p in trop["planets"]:
        slon = shift(p["lon"])
        planets.append({"name": p["name"], "lon": slon, "sign": sign_of(slon),
                        "signlon": slon % 30, "retro": p["retro"]})

    out = {
        "time_known": trop["time_known"],
        "planets": planets,
        "aspects": trop["aspects"],          # unchanged: constant offset preserves angles
        "asc": None, "mc": None, "houses": [],
        "ayanamsha": round(ay, 3),
    }
    if trop["time_known"]:
        if trop["asc"]:
            a = shift(trop["asc"]["lon"])
            out["asc"] = {"lon": a, "sign": sign_of(a)}
        if trop["mc"]:
            m = shift(trop["mc"]["lon"])
            out["mc"] = {"lon": m, "sign": sign_of(m)}
        out["houses"] = [{"id": h["id"], "lon": shift(h["lon"]), "size": h["size"]}
                         for h in trop["houses"]]

    moon = next((p for p in planets if p["name"] == "Moon"), None)
    if moon:
        seg = 360.0 / 27
        idx = int(moon["lon"] // seg)
        pada = int((moon["lon"] % seg) // (seg / 4)) + 1
        out["nakshatra"] = {"name": NAKSHATRAS[idx], "pada": pada,
                            "moon_sign": moon["sign"]}
    return out


# ===========================================================================
# UI
# ===========================================================================
def _deg(signlon):
    dd = int(signlon)
    mm = int(round((signlon - dd) * 60))
    if mm == 60:
        dd, mm = dd + 1, 0
    return "%d\u00b0%02d'" % (dd, mm)


def build_page(state):
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout,
        QPushButton, QSizePolicy,
    )
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import Qt, QUrl
    from ui.theme import LIGHT, BADGE_COLORS_LIGHT
    from ui.natal_wheel import NatalWheel, ELEMENT_COLOR, PLANET_GLYPH

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

    def head_row(title, badge_text=None):
        row = QHBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
        row.addWidget(t)
        if badge_text:
            row.addWidget(badge(badge_text))
        row.addStretch(1); return row

    page = QWidget()
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer.addWidget(scroll)
    body = QWidget(); lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)
    scroll.setWidget(body)

    h = QHBoxLayout()
    title = QLabel("Vedic \u00b7 Sidereal")
    title.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    h.addWidget(title); h.addWidget(badge("TRADITIONAL")); h.addStretch(1)
    lay.addLayout(h)
    sub = QLabel("Your chart on the star-fixed (sidereal) zodiac, and your birth-star "
                 "(Janma Nakshatra) \u2014 computed locally from your birth data.")
    sub.setWordWrap(True); sub.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    profile = getattr(state, "active_profile", None)
    if profile is None:
        c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(20, 24, 20, 24)
        m = QLabel("No profile yet. Create one in Records \u2192 Profile to see your "
                   "sidereal chart and nakshatra.")
        m.setWordWrap(True); m.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        cl.addWidget(m); lay.addWidget(c); lay.addStretch(1); return page

    chart = sidereal_chart(profile)
    if chart is None:
        m = QLabel("Add a birth date to your profile to compute your sidereal chart.")
        m.setStyleSheet("color:%s;" % LIGHT["text"]); lay.addWidget(m); lay.addStretch(1); return page

    sun = next((p for p in chart["planets"] if p["name"] == "Sun"), None)

    # --- sidereal Sun ---
    if sun:
        elem = SIGN_INFO[sun["sign"]][0]
        c1 = card(); cl = QHBoxLayout(c1); cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(16)
        gl = QLabel(SIGN_INFO[sun["sign"]][2]); gl.setStyleSheet("font-size:38px;color:%s;" % ELEMENT_COLOR[elem])
        cl.addWidget(gl)
        col = QVBoxLayout(); col.setSpacing(2)
        nm = QLabel("Sun in %s (sidereal)" % sun["sign"])
        nm.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["text"])
        col.addWidget(nm)
        meta = QLabel("%s \u00b7 %s \u00b7 Lahiri ayanamsha %.2f\u00b0"
                      % (elem, _deg(sun["signlon"]), chart["ayanamsha"]))
        meta.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
        col.addWidget(meta)
        cl.addLayout(col); cl.addStretch(1)
        lay.addWidget(c1)

    # --- nakshatra ---
    if "nakshatra" in chart:
        nk = chart["nakshatra"]
        c2 = card(); c2l = QVBoxLayout(c2); c2l.setContentsMargins(20, 16, 20, 18); c2l.setSpacing(6)
        c2l.addLayout(head_row("Janma Nakshatra", "TRADITIONAL"))
        v = QLabel("%s \u2014 pada %d" % (nk["name"], nk["pada"]))
        v.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["accent"])
        c2l.addWidget(v)
        b = QLabel("Your birth-star: the lunar mansion the Moon occupied at birth "
                   "(Moon in sidereal %s). One of 27 mansions of 13\u00b020', each in four "
                   "padas." % nk["moon_sign"])
        b.setWordWrap(True); b.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        c2l.addWidget(b)
        if not chart["time_known"]:
            w = QLabel("Approximate \u2014 the Moon moves ~13\u00b0/day, so add your birth "
                       "time to pin the nakshatra exactly.")
            w.setWordWrap(True); w.setStyleSheet("font-size:11px;color:%s;" % LIGHT["warn"])
            c2l.addWidget(w)
        lay.addWidget(c2)

    # --- wheel + positions ---
    c3 = card(); c3l = QVBoxLayout(c3); c3l.setContentsMargins(20, 16, 20, 18); c3l.setSpacing(12)
    c3l.addLayout(head_row("Sidereal Chart", "TRADITIONAL"))
    if not chart["time_known"]:
        note = QLabel("Birth time not set \u2014 planetary sign positions only; houses, "
                      "Ascendant and Midheaven need your exact birth time.")
        note.setWordWrap(True); note.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
        c3l.addWidget(note)
    row = QHBoxLayout(); row.setSpacing(18)
    wheel = NatalWheel(chart); wheel.setMinimumSize(380, 380)
    row.addWidget(wheel, 3)
    grid_wrap = QWidget(); grid = QGridLayout(grid_wrap)
    grid.setContentsMargins(0, 0, 0, 0); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(4)
    for ci, htext in enumerate(["", "Body", "Sign", "Pos", ""]):
        hl = QLabel(htext); hl.setStyleSheet("color:%s;font-weight:bold;font-size:10px;" % LIGHT["subtle"])
        grid.addWidget(hl, 0, ci)
    for ri, p in enumerate(chart["planets"], start=1):
        elem = SIGN_INFO.get(p["sign"], ("Air", "", ""))[0]
        g = QLabel(PLANET_GLYPH.get(p["name"], "")); g.setStyleSheet("font-size:15px;color:%s;" % LIGHT["text"])
        grid.addWidget(g, ri, 0)
        nm = QLabel(p["name"]); nm.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        grid.addWidget(nm, ri, 1)
        sg = QLabel(p["sign"]); sg.setStyleSheet("font-size:12px;color:%s;" % ELEMENT_COLOR.get(elem, LIGHT["text"]))
        grid.addWidget(sg, ri, 2)
        dg = QLabel(_deg(p["signlon"])); dg.setStyleSheet("font-size:12px;color:%s;" % LIGHT["subtle"])
        grid.addWidget(dg, ri, 3)
        if p["retro"]:
            rl = QLabel("\u211E"); rl.setStyleSheet("font-size:12px;color:%s;" % LIGHT["neg"])
            grid.addWidget(rl, ri, 4)
    grid.setRowStretch(grid.rowCount(), 1)
    grid_wrap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    row.addWidget(grid_wrap, 2)
    c3l.addLayout(row)
    lay.addWidget(c3)

    # --- ayanamsha explainer ---
    c4 = card(); c4l = QVBoxLayout(c4); c4l.setContentsMargins(20, 14, 20, 16)
    ex = QLabel("Why it differs from the Tropical page: the sidereal zodiac is fixed to "
                "the stars, so it sits behind the seasonal (tropical) zodiac by the "
                "ayanamsha (~%.1f\u00b0 for you). Your sidereal Sun is usually the sign "
                "before your tropical one. This uses the Lahiri ayanamsha, the Indian "
                "government standard." % chart["ayanamsha"])
    ex.setWordWrap(True); ex.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    c4l.addWidget(ex)
    lay.addWidget(c4)

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
        for src in state.sidereal_sources():
            b = QPushButton("%s  \u2197" % src["name"]); b.setStyleSheet("text-align:left;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, u=src["url"]: QDesktopServices.openUrl(QUrl(u)))
            links_box.addWidget(b)

    def open_editor():
        from cosmos._sources_dialog import SourcesDialog
        if SourcesDialog(state, page, sources_key="sidereal").exec():
            render_links()

    edit_btn.clicked.connect(open_editor)
    render_links()
    lay.addWidget(c5)

    lay.addStretch(1)
    return page
