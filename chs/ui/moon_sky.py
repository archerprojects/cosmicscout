"""
Cosmic Scout — ui/moon_sky.py  (v1.0.0 — Tuesday 3 November 2026)

Moon & Sky page (Cosmos wing). Presents the astronomy engine: current moon phase
with a drawn phase disc, upcoming phases, this month's traditional full-moon name,
the year's solar events, and approximate upcoming eclipses. The astronomy cards are
VALIDATED; a "Moon and you" card renders the evidence split (spine §5): tides
VALIDATED, personal sleep/mood CONTESTED, menstrual link EMERGING. Works with or without an active profile (the sky is global). Times are
UTC. Light theme.
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF, QSize

from ui.theme import LIGHT, BADGE_COLORS_LIGHT
from engines import astronomy as A

_DARK = "#3a3f52"
_LIT = "#f7f4e6"


class MoonDisc(QWidget):
    """Draws the illuminated fraction of the Moon with correct waxing orientation."""

    def __init__(self, illumination, waxing, parent=None):
        super().__init__(parent)
        self._f = max(0.0, min(1.0, illumination / 100.0))
        self._waxing = waxing
        self.setMinimumSize(96, 96)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(110, 110)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        R = min(w, h) / 2.0 - 3
        cx, cy = w / 2.0, h / 2.0
        disc = QRectF(cx - R, cy - R, 2 * R, 2 * R)

        # dark disc
        p.setPen(QPen(QColor(LIGHT["border"]), 1))
        p.setBrush(QBrush(QColor(_DARK)))
        p.drawEllipse(disc)

        # clip to the disc, draw lit semicircle + terminator ellipse
        from PyQt5.QtGui import QPainterPath
        clip = QPainterPath()
        clip.addEllipse(disc)
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)

        f = self._f
        # lit half-disc: waxing -> right (start -90, span 180); waning -> left
        p.setBrush(QColor(_LIT))
        start = -90 if self._waxing else 90
        p.drawPie(disc, int(start * 16), int(180 * 16))

        # terminator ellipse (lit if gibbous, dark if crescent)
        ew = R * abs(1.0 - 2.0 * f)
        p.setBrush(QColor(_LIT if f > 0.5 else _DARK))
        p.drawEllipse(QRectF(cx - ew, cy - R, 2 * ew, 2 * R))
        p.end()


def build_page(state):
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
        t = QLabel(title); t.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["text"])
        row.addWidget(t)
        if badge_text:
            row.addWidget(badge(badge_text))
        row.addStretch(1); return row

    page = QWidget()
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
    outer.addWidget(scroll)
    body = QWidget(); lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)
    scroll.setWidget(body)

    h = QHBoxLayout()
    title = QLabel("Moon & Sky")
    title.setStyleSheet("font-size:24px;font-weight:bold;color:%s;" % LIGHT["text"])
    h.addWidget(title); h.addStretch(1)      # no page-wide badge: each card carries its own
    lay.addLayout(h)
    sub = QLabel("Where the Moon and Sun are right now, and what's coming \u2014 computed "
                 "offline from the ephemeris. Times in UTC. Each card shows its own "
                 "evidence grade.")
    sub.setWordWrap(True); sub.setStyleSheet("color:%s;font-size:14px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    mp = A.moon_phase()
    now = datetime.utcnow()

    # --- current moon ---
    c1 = card(); c1l = QHBoxLayout(c1); c1l.setContentsMargins(20, 16, 20, 16); c1l.setSpacing(18)
    c1l.addWidget(MoonDisc(mp["illumination"], mp["waxing"]))
    col = QVBoxLayout(); col.setSpacing(3)
    nm = QLabel(mp["phase_name"]); nm.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    col.addWidget(nm)
    det = QLabel("%.0f%% illuminated \u00b7 %s \u00b7 %.1f days into the cycle"
                 % (mp["illumination"], "waxing" if mp["waxing"] else "waning", mp["age_days"]))
    det.setStyleSheet("font-size:14px;color:%s;" % LIGHT["subtle"])
    col.addWidget(det)
    fmn = A.full_moon_name(mp["next_full"].month)
    blue = A.is_blue_moon(mp["next_full"])
    fm_txt = "Next full moon: <b>%s</b> (%s)%s" % (
        fmn["primary"], mp["next_full"].strftime("%b %-d"),
        " \u2014 a <b>Blue Moon</b>" if blue else "")
    fml = QLabel(fm_txt); fml.setWordWrap(True)
    fml.setStyleSheet("font-size:14px;color:%s;" % LIGHT["text"])
    col.addWidget(fml)
    alt = QLabel("Also called: %s. %s" % (", ".join(fmn["alternates"]), fmn["note"]))
    alt.setWordWrap(True); alt.setStyleSheet("font-size:12px;color:%s;" % LIGHT["subtle"])
    col.addWidget(alt)
    c1l.addLayout(col, 1)
    lay.addWidget(c1)

    # --- the Moon and you: the evidence split, one voice per claim ---
    cy = card(); cyl = QVBoxLayout(cy); cyl.setContentsMargins(20, 16, 20, 18); cyl.setSpacing(10)
    cyl.addLayout(head_row("The Moon and you"))
    for claim, grade, text, cite in (
        ("Tides", "VALIDATED",
         "The Moon's gravity raises the ocean tides: springs at new and full moon, "
         "neaps at the quarters.",
         "Classical tidal physics (Newton, Principia, 1687)."),
        ("Sleep and mood", "CONTESTED",
         "Some field studies find sleep shortening before the full moon; others "
         "find nothing. Any effect is small and easily masked by artificial light.",
         "Casiraghi et al. 2021, Science Advances 7:eabe0465; Cajochen et al. 2013, "
         "Current Biology 23:1485\u20131488 (retrospective; file-drawer critique)."),
        ("Menstrual timing", "EMERGING",
         "Long records suggest some cycles temporarily line up with the Moon's light "
         "and gravity cycles; intermittent, small, and not a fixed 'lunar' cycle.",
         "Helfrich-F\u00f6rster et al. 2021, Science Advances 7:eabe1358; Ecochard "
         "et al. 2024, Science Advances 10:eadg9646."),
    ):
        cyl.addLayout(head_row(claim, grade))
        tl = QLabel(text); tl.setWordWrap(True)
        tl.setStyleSheet("font-size:13px;color:%s;" % LIGHT["text"]); cyl.addWidget(tl)
        cl = QLabel(cite); cl.setWordWrap(True)
        cl.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"]); cyl.addWidget(cl)
    lay.addWidget(cy)

    # --- upcoming phases ---
    c2 = card(); c2l = QVBoxLayout(c2); c2l.setContentsMargins(20, 16, 20, 18); c2l.setSpacing(8)
    c2l.addLayout(head_row("Upcoming Phases", "VALIDATED"))
    g = QGridLayout(); g.setHorizontalSpacing(16); g.setVerticalSpacing(5)
    phases = [("New", mp["next_new"]), ("First Quarter", mp["next_first_quarter"]),
              ("Full", mp["next_full"]), ("Last Quarter", mp["next_last_quarter"])]
    phases.sort(key=lambda x: x[1])
    for i, (label, when) in enumerate(phases):
        l1 = QLabel(label); l1.setStyleSheet("font-size:14px;color:%s;" % LIGHT["text"])
        l2 = QLabel(when.strftime("%a %b %-d, %H:%M")); l2.setStyleSheet("font-size:14px;color:%s;" % LIGHT["subtle"])
        g.addWidget(l1, i, 0); g.addWidget(l2, i, 1)
    c2l.addLayout(g)
    lay.addWidget(c2)

    # --- solar events this year ---
    c3 = card(); c3l = QVBoxLayout(c3); c3l.setContentsMargins(20, 16, 20, 18); c3l.setSpacing(8)
    c3l.addLayout(head_row("Solar Events %d" % now.year, "VALIDATED"))
    g3 = QGridLayout(); g3.setHorizontalSpacing(16); g3.setVerticalSpacing(5)
    for i, ev in enumerate(A.solar_events(now.year)):
        upcoming = ev["when"] >= now
        name = QLabel(("\u25b6 " if upcoming else "") + ev["name"])
        name.setStyleSheet("font-size:14px;color:%s;%s"
                           % (LIGHT["accent"] if upcoming else LIGHT["text"],
                              "font-weight:bold;" if upcoming else ""))
        when = QLabel(ev["when"].strftime("%b %-d, %H:%M"))
        when.setStyleSheet("font-size:14px;color:%s;" % LIGHT["subtle"])
        g3.addWidget(name, i, 0); g3.addWidget(when, i, 1)
    c3l.addLayout(g3)
    lay.addWidget(c3)

    # --- eclipses ---
    c4 = card(); c4l = QVBoxLayout(c4); c4l.setContentsMargins(20, 16, 20, 18); c4l.setSpacing(8)
    c4l.addLayout(head_row("Upcoming Eclipses", "VALIDATED"))
    ecl = A.next_eclipses(count=4)
    if not ecl:
        c4l.addWidget(QLabel("None detected in the near future."))
    else:
        for e in ecl:
            row = QLabel("%s \u2014 %s" % (e["when"].strftime("%b %-d, %Y"), e["kind"]))
            row.setStyleSheet("font-size:14px;color:%s;" % LIGHT["text"])
            c4l.addWidget(row)
    cav = QLabel("Approximate: flagged from the Moon's closeness to a node. Type "
                 "(total/partial/annular) and visibility are not computed.")
    cav.setWordWrap(True); cav.setStyleSheet("font-size:12px;color:%s;" % LIGHT["subtle"])
    c4l.addWidget(cav)
    lay.addWidget(c4)

    # --- lunar birthday (this year) — only with an active profile birth date ---
    prof = getattr(state, "active_profile", None)
    if prof is not None and getattr(prof, "birth_date", None):
        from datetime import date as _date
        from engines import lunar_calendar as _lc
        try:
            _bd = _date.fromisoformat(prof.birth_date)
        except (ValueError, TypeError):
            _bd = None
        if _bd is not None:
            lb = _lc.lunar_birth_date(_bd)
            occ = _lc.lunar_birthday_in_year(_bd, now.year)
            c5 = card(); c5l = QVBoxLayout(c5)
            c5l.setContentsMargins(20, 16, 20, 18); c5l.setSpacing(8)
            c5l.addLayout(head_row("Lunar Birthday %d" % now.year, "TRADITIONAL"))
            if occ is not None:
                big = QLabel(occ.strftime("%A, %B %-d, %Y"))
                big.setStyleSheet("font-size:17px;font-weight:bold;color:%s;"
                                  % LIGHT["accent"])
                c5l.addWidget(big)
                if lb.available:
                    sub = QLabel("Your lunar birth date \u2014 %s \u2014 falls here on "
                                 "the solar calendar this year. It shifts annually."
                                 % lb.traditional())
                    sub.setWordWrap(True)
                    sub.setStyleSheet("font-size:13px;color:%s;" % LIGHT["subtle"])
                    c5l.addWidget(sub)
                # days-away cue
                delta = (occ - now.date()).days
                if delta == 0:
                    tag = "Today."
                elif delta > 0:
                    tag = "In %d day%s." % (delta, "" if delta == 1 else "s")
                else:
                    tag = "%d day%s ago." % (-delta, "" if delta == -1 else "s")
                tl = QLabel(tag)
                tl.setStyleSheet("font-size:13px;color:%s;font-weight:bold;"
                                 % LIGHT["text"])
                c5l.addWidget(tl)
            else:
                na = QLabel("Lunar birthday unavailable for this year "
                            "(birth date outside the 1900\u20132099 lunar table).")
                na.setWordWrap(True)
                na.setStyleSheet("font-size:13px;color:%s;" % LIGHT["subtle"])
                c5l.addWidget(na)
            lay.addWidget(c5)

    lay.addStretch(1)
    return page
