"""
Cosmic Scout — ui/natal_wheel.py  (v1.0.0 — Tuesday 3 November 2026)

Drawn natal wheel (QPainter). A reusable, resize-aware QWidget that renders a
computed chart: an element-coloured zodiac ring with sign glyphs, Placidus house
spokes, planet glyphs plotted at ecliptic longitude, and major-aspect chords in
the inner circle. Light theme only — the app is light everywhere except the
dashboard cockpit.

Consumes the dict produced by cosmos.astro_tropical.natal_chart():

    {
      "time_known": bool,
      "planets": [{"name","sign","lon","signlon","retro"}, ...],
      "asc": {"lon","sign"} | None,
      "mc":  {"lon","sign"} | None,
      "houses": [{"id","lon","size"}, ...],     # empty when time unknown
      "aspects": [{"a","b","angle","orb"}, ...],
    }

When time_known is False, houses and angles are absent: only the zodiac ring and
planet longitudes are drawn, with 0 Aries fixed to the left. When time is known,
the ring is rotated so the Ascendant sits at the left (9 o'clock) in the standard
counter-clockwise convention.
"""

import math

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize

from ui.theme import LIGHT

# Aries -> Pisces, in order
SIGN_GLYPHS = ["\u2648", "\u2649", "\u264A", "\u264B", "\u264C", "\u264D",
               "\u264E", "\u264F", "\u2650", "\u2651", "\u2652", "\u2653"]
# element per sign, Aries..Pisces (Fire, Earth, Air, Water repeating)
SIGN_ELEMENTS = ["Fire", "Earth", "Air", "Water"] * 3

ELEMENT_COLOR = {
    "Fire":  "#c0623c",
    "Earth": "#5c8a4a",
    "Air":   "#3c78c0",
    "Water": "#3fa0b0",
}

PLANET_GLYPH = {
    "Sun": "\u2609", "Moon": "\u263D", "Mercury": "\u263F", "Venus": "\u2640",
    "Mars": "\u2642", "Jupiter": "\u2643", "Saturn": "\u2644", "Uranus": "\u2645",
    "Neptune": "\u2646", "Pluto": "\u2647", "North Node": "\u260A",
    "South Node": "\u260B",
}

# 0 conjunction, 60 sextile, 90 square, 120 trine, 180 opposition
ASPECT_COLOR = {0: "#8a8a8a", 60: "#4aa8e0", 90: "#d05a5a",
                120: "#3ecf8e", 180: "#c8791f"}


class NatalWheel(QWidget):
    """Paints a natal chart dict. Call set_chart() to update."""

    def __init__(self, chart=None, parent=None):
        super().__init__(parent)
        self._chart = chart
        self.setMinimumSize(340, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_chart(self, chart):
        self._chart = chart
        self.update()

    def sizeHint(self):
        return QSize(460, 460)

    # ecliptic longitude -> screen point on a circle of radius r.
    # rot is the longitude pinned to the left (Ascendant, or 0 Aries).
    def _pt(self, cx, cy, r, lon, rot):
        a = math.radians(180.0 + (lon - rot))
        return QPointF(cx + r * math.cos(a), cy - r * math.sin(a))

    def paintEvent(self, _ev):
        c = self._chart
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        R = min(w, h) / 2.0 - 8.0
        r_sign_out = R
        r_sign_in = R * 0.82
        r_planet = R * 0.66
        r_inner = R * 0.50

        # base disc
        p.setPen(QPen(QColor(LIGHT["border"]), 1))
        p.setBrush(QBrush(QColor(LIGHT["input"])))
        p.drawEllipse(QRectF(cx - R, cy - R, 2 * R, 2 * R))

        if not c:
            p.setPen(QColor(LIGHT["subtle"]))
            p.drawText(self.rect(), Qt.AlignCenter, "No chart")
            p.end()
            return

        rot = 0.0
        if c.get("time_known") and c.get("asc"):
            rot = c["asc"]["lon"]

        # --- zodiac ring: tinted element sectors ---
        p.setPen(Qt.NoPen)
        for i in range(12):
            col = QColor(ELEMENT_COLOR[SIGN_ELEMENTS[i]])
            col.setAlpha(45)
            p.setBrush(col)
            start_screen = 180.0 + (i * 30.0 - rot)
            p.drawPie(QRectF(cx - r_sign_out, cy - r_sign_out,
                             2 * r_sign_out, 2 * r_sign_out),
                      int(round(start_screen * 16)), int(30 * 16))
        # knock out the centre to leave only the ring
        p.setBrush(QColor(LIGHT["input"]))
        p.drawEllipse(QRectF(cx - r_sign_in, cy - r_sign_in,
                             2 * r_sign_in, 2 * r_sign_in))

        # ring borders
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(LIGHT["border"]), 1))
        p.drawEllipse(QRectF(cx - r_sign_out, cy - r_sign_out, 2 * r_sign_out, 2 * r_sign_out))
        p.drawEllipse(QRectF(cx - r_sign_in, cy - r_sign_in, 2 * r_sign_in, 2 * r_sign_in))
        p.drawEllipse(QRectF(cx - r_inner, cy - r_inner, 2 * r_inner, 2 * r_inner))

        # sign dividers + glyphs
        gf = QFont("DejaVu Sans")
        gf.setPointSizeF(max(9.0, R * 0.055))
        for i in range(12):
            p.setPen(QPen(QColor(LIGHT["border"]), 1))
            p.drawLine(self._pt(cx, cy, r_sign_in, i * 30.0, rot),
                       self._pt(cx, cy, r_sign_out, i * 30.0, rot))
            g = self._pt(cx, cy, (r_sign_in + r_sign_out) / 2.0, i * 30.0 + 15.0, rot)
            p.setFont(gf)
            p.setPen(QColor(ELEMENT_COLOR[SIGN_ELEMENTS[i]]))
            p.drawText(QRectF(g.x() - 13, g.y() - 13, 26, 26),
                       Qt.AlignCenter, SIGN_GLYPHS[i])

        # --- house spokes (only when time is known) ---
        if c.get("time_known") and c.get("houses"):
            for hs in c["houses"]:
                is_angle = hs["id"] in ("House1", "House10")
                pen = QPen(QColor(LIGHT["accent"]) if is_angle else QColor(LIGHT["border"]))
                pen.setWidth(2 if is_angle else 1)
                p.setPen(pen)
                p.drawLine(self._pt(cx, cy, r_inner, hs["lon"], rot),
                           self._pt(cx, cy, r_sign_in, hs["lon"], rot))

        # --- aspect chords in the inner circle ---
        pos = {pl["name"]: pl["lon"] for pl in c.get("planets", [])}
        for asp in c.get("aspects", []):
            if asp["a"] in pos and asp["b"] in pos:
                col = QColor(ASPECT_COLOR.get(asp["angle"], "#888888"))
                col.setAlpha(120)
                pen = QPen(col)
                pen.setWidth(1)
                if asp["angle"] == 0:
                    pen.setStyle(Qt.DotLine)
                p.setPen(pen)
                p.drawLine(self._pt(cx, cy, r_inner, pos[asp["a"]], rot),
                           self._pt(cx, cy, r_inner, pos[asp["b"]], rot))

        # --- planets ---
        pf = QFont("DejaVu Sans")
        pf.setPointSizeF(max(10.0, R * 0.062))
        rf = QFont("DejaVu Sans")
        rf.setPointSizeF(max(7.0, R * 0.032))
        for pl in c.get("planets", []):
            lon = pl["lon"]
            p.setPen(QPen(QColor(LIGHT["subtle"]), 1))
            p.drawLine(self._pt(cx, cy, r_sign_in, lon, rot),
                       self._pt(cx, cy, r_planet + R * 0.05, lon, rot))
            g = self._pt(cx, cy, r_planet, lon, rot)
            p.setFont(pf)
            p.setPen(QColor(LIGHT["text"]))
            p.drawText(QRectF(g.x() - 13, g.y() - 13, 26, 26),
                       Qt.AlignCenter, PLANET_GLYPH.get(pl["name"], pl["name"][:2]))
            if pl.get("retro"):
                p.setFont(rf)
                p.setPen(QColor(LIGHT["neg"]))
                p.drawText(QRectF(g.x() + 7, g.y() + 3, 16, 12),
                           Qt.AlignLeft, "\u211E")

        p.end()
