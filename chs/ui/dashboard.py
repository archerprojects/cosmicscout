"""
Cosmic Scout — Composite Guidance Dashboard
dashboard.py  (v1.1.0 — Monday 9 November 2026)

v1.11: optional NOAA space-weather row (CONTESTED), fetched off-thread.
v1.3: consumes a real data.models.Profile (attribute access), not a dict.
The active profile is supplied by app_state; None renders an honest empty state
inviting the user to create one in Records. The scale toggle is seeded from,
and reports back to, app_state so it persists across sessions.

The app's home surface. A dark framed dashboard of horizontal, centre-diverging
bars, one per real cycle, plus a validated-tier composite headline row.

Bar grammar (one axis, one unit = amplitude):
    * bar diverges from a centre baseline: right = favourable phase, left = adverse
    * DARK segment  = current amplitude (where you are now)
    * LIGHT segment = same hue, lower opacity, current -> next peak (headroom).
      Present only while the cycle is RISING; its absence means "descending".
    * timing (a *time* value) lives in the right-hand readout, never in the bar.

Every row carries its evidence badge. The badge legend is one tap from any row.
Tapping a row opens that cycle's explanation (mechanism, badge, why it matters).
"""

from dataclasses import dataclass
import sys, os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QDialog, QFrame, QScrollArea,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QThread, QTimer

# make the package root (chs/) importable whether run standalone or via main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engines.cycles import (                      # noqa: E402
    day_cycles, CycleState, _sex_of,
    BADGE_VALIDATED, BADGE_EMERGING, BADGE_CONTESTED, BADGE_TRADITIONAL,
)
from engines import space_weather                 # noqa: E402
from data import geo                              # noqa: E402
from ui.theme import DARK, BADGE_COLORS           # noqa: E402


class _SWFetch(QThread):
    """Fetches the NOAA space-weather reading off the UI thread, warming the
    space_weather cache. On finish, the dashboard rebuilds to show it."""
    def __init__(self, state):
        super().__init__()
        self._state = state

    def run(self):
        try:
            space_weather.refresh(self._state)
        except Exception:
            pass

# --- dark palette (dashboard cockpit; the rest of the app stays light) -------
C_BG      = DARK["bg"]
C_CARD    = DARK["card"]
C_TRACK   = DARK["track"]
C_TEXT    = DARK["text"]
C_SUBTLE  = DARK["subtle"]
C_CENTER  = DARK["center"]
C_COMP    = DARK["comp"]


@dataclass
class EmptyNote:
    """A row with no bar: an honest 'nothing reliable yet' state."""
    key: str
    name: str
    icon: str
    message: str
    badge: str
    hue: str
    detail: str


def _f(size, bold=False, weight=None):
    f = QFont("DejaVu Sans", size)
    if bold:
        f.setBold(True)
    if weight:
        f.setWeight(weight)
    return f


# --------------------------------------------------------------------------- #
#  a single cycle row (icon | name+badge | diverging bar | readout)
# --------------------------------------------------------------------------- #
class CycleRow(QWidget):
    clicked = pyqtSignal(str)

    ROW_H = 74
    BAR_X0 = 92
    BAR_X1 = 542
    BAR_H = 12

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setFixedHeight(self.ROW_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(720)

    def mousePressEvent(self, e):
        self.clicked.emit(self.state.key)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = self.state
        is_bar = isinstance(s, CycleState)
        hue = QColor(s.hue)

        # icon disc
        disc = QRectF(20, self.ROW_H / 2 - 18, 36, 36)
        p.setPen(Qt.PenStyle.NoPen)
        dc = QColor(s.hue); dc.setAlpha(38)
        p.setBrush(dc)
        p.drawEllipse(disc)
        p.setPen(QPen(hue))
        p.setFont(_f(15))
        p.drawText(disc, Qt.AlignmentFlag.AlignCenter, s.icon)

        # name
        p.setPen(QPen(QColor(C_TEXT)))
        p.setFont(_f(11, bold=True))
        p.drawText(self.BAR_X0, 16, 320, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, s.name)

        # badge pill (right of name)
        name_w = p.fontMetrics().horizontalAdvance(s.name)
        self._draw_badge(p, self.BAR_X0 + name_w + 12, 8, s.badge)

        if is_bar:
            self._draw_bar(p, s, hue)
            self._draw_readout(p, s.phase_word, s.timing)
        else:
            # empty-state message in place of the bar
            p.setPen(QPen(QColor(C_SUBTLE)))
            p.setFont(_f(10))
            p.drawText(self.BAR_X0, 40, self.BAR_X1 - self.BAR_X0 + 150, 24,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, s.message)
        p.end()

    def _draw_badge(self, p, x, y, badge):
        col = QColor(BADGE_COLORS.get(badge, "#888"))
        txt = badge
        p.setFont(_f(8, bold=True))
        w = p.fontMetrics().horizontalAdvance(txt) + 16
        rect = QRectF(x, y, w, 16)
        bg = QColor(col); bg.setAlpha(38)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(bg)
        p.drawRoundedRect(rect, 8, 8)
        p.setPen(QPen(col))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

    def _draw_bar(self, p, s, hue):
        y = 48
        x0, x1 = self.BAR_X0, self.BAR_X1
        cx = (x0 + x1) / 2.0
        half = (x1 - x0) / 2.0
        h = self.BAR_H
        r = h / 2.0

        # track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_TRACK))
        p.drawRoundedRect(QRectF(x0, y, x1 - x0, h), r, r)

        # headroom (light) segment first, so dark overlaps cleanly
        if s.rising and abs(s.peak_ahead) > abs(s.amplitude):
            hx0 = cx + s.amplitude * half
            hx1 = cx + s.peak_ahead * half
            light = QColor(hue); light.setAlpha(115)
            p.setBrush(light)
            self._seg(p, hx0, hx1, y, h, r)

        # current (dark) segment from centre
        p.setBrush(hue)
        self._seg(p, cx, cx + s.amplitude * half, y, h, r)

        # centre baseline tick
        p.setPen(QPen(QColor(C_CENTER), 1))
        p.drawLine(int(cx), y - 4, int(cx), y + h + 4)

    @staticmethod
    def _seg(p, xa, xb, y, h, r):
        lo, hi = (xa, xb) if xa <= xb else (xb, xa)
        if hi - lo < 1:
            hi = lo + 1
        p.drawRoundedRect(QRectF(lo, y, hi - lo, h), r, r)

    def _draw_readout(self, p, word, timing):
        rx, rw = self.BAR_X1 + 22, 150
        p.setPen(QPen(QColor(C_TEXT)))
        p.setFont(_f(11, bold=True))
        p.drawText(rx, 16, rw, 20, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, word)
        p.setPen(QPen(QColor(C_SUBTLE)))
        p.setFont(_f(9))
        p.drawText(rx, 44, rw, 18, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, timing)


class SubBarRow(QWidget):
    """A thinner, indented named-driver bar rendered beneath a heading cycle."""
    clicked = pyqtSignal(str)
    ROW_H = 34
    BAR_X0 = 118          # indented past the heading's icon+name
    NAME_W = 170          # bar starts this far past BAR_X0, leaving room for the name
    BAR_X1 = 542
    BAR_H = 7

    def __init__(self, sub, parent=None):
        super().__init__(parent)
        self.sub = sub
        self.setFixedHeight(self.ROW_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(720)

    def mousePressEvent(self, e):
        self.clicked.emit(self.sub.key)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = self.sub; hue = QColor(s.hue)

        # small connector tick + name
        # thin diverging bar; the name column ends 10px before it
        y = self.ROW_H / 2 - self.BAR_H / 2
        x0, x1 = self.BAR_X0 + self.NAME_W, self.BAR_X1
        p.setPen(QPen(QColor(C_SUBTLE))); p.setFont(_f(9))
        name_w = int(x0) - 72 - 10
        name = p.fontMetrics().elidedText("\u2514 " + s.name, Qt.TextElideMode.ElideRight, name_w)
        p.drawText(72, 0, name_w, self.ROW_H, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        cx = (x0 + x1) / 2.0; half = (x1 - x0) / 2.0; h = self.BAR_H; r = h / 2.0
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(C_TRACK))
        p.drawRoundedRect(QRectF(x0, y, x1 - x0, h), r, r)
        if s.rising and abs(s.peak_ahead) > abs(s.amplitude):
            light = QColor(hue); light.setAlpha(115); p.setBrush(light)
            CycleRow._seg(p, cx + s.amplitude * half, cx + s.peak_ahead * half, y, h, r)
        p.setBrush(hue)
        CycleRow._seg(p, cx, cx + s.amplitude * half, y, h, r)
        p.setPen(QPen(QColor(C_CENTER), 1)); p.drawLine(int(cx), int(y) - 3, int(cx), int(y + h) + 3)

        # compact readout (phase word only)
        p.setPen(QPen(QColor(C_SUBTLE))); p.setFont(_f(8, bold=True))
        p.drawText(self.BAR_X1 + 22, 0, 150, self.ROW_H,
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, s.phase_word)
        p.end()


# --------------------------------------------------------------------------- #
#  composite headline row (validated tier only)
# --------------------------------------------------------------------------- #
class CompositeRow(QWidget):
    ROW_H = 94
    BAR_X0 = 92
    BAR_X1 = 542

    def __init__(self, comp, parent=None):
        super().__init__(parent)
        self.comp = comp
        self.setFixedHeight(self.ROW_H)
        self.setMinimumWidth(720)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = self.comp; hue = QColor(C_COMP)

        # filled icon disc
        disc = QRectF(18, self.ROW_H / 2 - 20, 40, 40)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(hue)
        p.drawEllipse(disc)
        p.setPen(QPen(QColor("#ffffff"))); p.setFont(_f(17, bold=True))
        p.drawText(disc, Qt.AlignmentFlag.AlignCenter, "\u25c9")

        p.setPen(QPen(QColor(C_TEXT))); p.setFont(_f(12, bold=True))
        title = "TODAY\u2019S WINDOW"
        p.drawText(self.BAR_X0, 14, 360, 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        sub_x = self.BAR_X0 + p.fontMetrics().horizontalAdvance(title) + 12
        p.setPen(QPen(QColor(C_SUBTLE))); p.setFont(_f(8, bold=True))
        p.drawText(sub_x, 15, 240, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "circadian + ultradian")

        # diverging bar
        y, x0, x1 = 52, self.BAR_X0, self.BAR_X1
        cx = (x0 + x1) / 2.0; half = (x1 - x0) / 2.0; h = 14; r = 7
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(C_TRACK))
        p.drawRoundedRect(QRectF(x0, y, x1 - x0, h), r, r)
        if c.rising and abs(c.peak_ahead) > abs(c.amplitude):
            light = QColor(hue); light.setAlpha(115); p.setBrush(light)
            CycleRow._seg(p, cx + c.amplitude * half, cx + c.peak_ahead * half, y, h, r)
        p.setBrush(hue)
        CycleRow._seg(p, cx, cx + c.amplitude * half, y, h, r)
        p.setPen(QPen(QColor(C_CENTER), 1)); p.drawLine(int(cx), y - 5, int(cx), y + h + 5)

        # headline readout
        p.setPen(QPen(QColor(C_TEXT))); p.setFont(_f(11, bold=True))
        p.drawText(self.BAR_X1 + 22, 44, 150, 20, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   c.headline.split(" \u2014 ")[0])
        p.setPen(QPen(QColor(C_SUBTLE))); p.setFont(_f(9))
        tail = c.headline.split(" \u2014 ")[-1]
        p.drawText(self.BAR_X0, 74, 470, 16, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{tail} \u00b7 {c.timing}")
        p.end()


# --------------------------------------------------------------------------- #
#  cycle info dialog (opened on row tap)
# --------------------------------------------------------------------------- #
class CycleDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.setWindowTitle(state.name)
        self.setStyleSheet(f"background:{C_CARD};")
        self.setFixedWidth(440)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 22, 24, 22); lay.setSpacing(12)

        title = QLabel(f"{getattr(state, 'icon', '\u2514')}  {state.name}")
        title.setFont(_f(16, bold=True)); title.setStyleSheet(f"color:{C_TEXT};")
        lay.addWidget(title)

        badge = QLabel(state.badge)
        bc = BADGE_COLORS.get(state.badge, "#888")
        badge.setFont(_f(9, bold=True))
        badge.setStyleSheet(
            f"color:{bc}; background:rgba(255,255,255,18); "
            f"padding:3px 10px; border-radius:8px;")
        badge.setFixedWidth(badge.fontMetrics().horizontalAdvance(state.badge) + 26)
        lay.addWidget(badge)

        # an EmptyNote (honest empty state) has no channel; show the line only
        # for states that name one
        channel = getattr(state, "channel", None)
        if channel:
            chan = QLabel("Channel:  " + channel)
            chan.setWordWrap(True); chan.setFont(_f(10))
            chan.setStyleSheet(f"color:{C_SUBTLE};")
            lay.addWidget(chan)

        body = QLabel(state.detail)
        body.setWordWrap(True); body.setFont(_f(10))
        body.setStyleSheet(f"color:{C_TEXT};")
        lay.addWidget(body)

        more = QLabel("Tap-through in the full app opens this cycle\u2019s page in Cycles.")
        more.setWordWrap(True); more.setFont(_f(8))
        more.setStyleSheet(f"color:{C_SUBTLE};")
        lay.addWidget(more)


# --------------------------------------------------------------------------- #
#  the dashboard
# --------------------------------------------------------------------------- #
class Dashboard(QWidget):
    def __init__(self, profile, now=None, parent=None, state=None):
        super().__init__(parent)
        self.profile = profile          # data.models.Profile or None
        self.state = state              # app_state.AppState or None
        # live unless a fixed time is passed (tests); live time is the current
        # location's local time, else the computer's clock
        self._live = now is None
        self.now = now or self._local_now()
        self.scale = getattr(state, "scale", "Day") or "Day"
        self._sw_thread = None          # background space-weather fetch
        # Opaque, self-scoped dark fill so the light stack behind never shows
        # through and child widgets don't inherit a bare background rule.
        self.setObjectName("Dashboard")
        self.setAutoFillBackground(True)
        # a QWidget subclass only paints its stylesheet background with this set
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"QWidget#Dashboard {{ background:{C_BG}; }}")
        self.setMinimumSize(760, 560)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(28, 24, 28, 24)
        self.root.setSpacing(6)
        self._build_header()
        # scrollable body so rows never overlap or run off the bottom
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"QScrollArea {{ background:{C_BG}; border:none; }}")
        self._body_host = QWidget()
        self._body_host.setStyleSheet(f"background:{C_BG};")
        self.body = QVBoxLayout(self._body_host); self.body.setSpacing(4)
        self.body.setContentsMargins(0, 0, 0, 0)
        self._scroll.setWidget(self._body_host)
        self.root.addWidget(self._scroll, 1)
        self._build_footer()
        self._rebuild()
        if self._live:                     # move the bars with the clock
            self._clock = QTimer(self)
            self._clock.timeout.connect(self._tick)
            self._clock.start(60_000)

    def _local_now(self):
        return geo.local_now(getattr(self.profile, "current_timezone", None))

    def _tick(self):
        self.now = self._local_now()
        self._date_lbl.setText(self.now.strftime("%A, %d %B %Y").upper())
        self._rebuild()

    # header: profile + date (left), scale toggle (right)
    def _build_header(self):
        bar = QHBoxLayout()
        left = QVBoxLayout(); left.setSpacing(2)
        alias = QLabel(self.profile.alias if self.profile else "No profile")
        alias.setFont(_f(20, bold=True)); alias.setStyleSheet(f"color:{C_TEXT};")
        self._date_lbl = date = QLabel(self.now.strftime("%A, %d %B %Y").upper())
        date.setFont(_f(9, bold=True)); date.setStyleSheet(f"color:{C_SUBTLE}; letter-spacing:1px;")
        left.addWidget(alias); left.addWidget(date)
        if (self.profile is not None and self.state is not None
                and self.state.location_on_dashboard()):
            loc = self._location_line()
            if loc:
                loclbl = QLabel(loc); loclbl.setFont(_f(9))
                loclbl.setStyleSheet(f"color:{C_SUBTLE};")
                left.addWidget(loclbl)
        bar.addLayout(left); bar.addStretch(1)

        self.toggle_group = QButtonGroup(self)
        tog = QHBoxLayout(); tog.setSpacing(0)
        for i, name in enumerate(("Day", "Week", "Month")):
            b = QPushButton(name); b.setCheckable(True); b.setFixedSize(72, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setChecked(name == self.scale)
            b.setFont(_f(9, bold=True))
            b.setStyleSheet(self._toggle_css())
            b.clicked.connect(lambda _, n=name: self._set_scale(n))
            self.toggle_group.addButton(b, i); tog.addWidget(b)
        tw = QWidget(); tw.setLayout(tog)
        tw.setStyleSheet("background:transparent;")   # no light app-theme box behind the toggle
        bar.addWidget(tw, 0, Qt.AlignmentFlag.AlignTop)
        self.root.addLayout(bar)

        line = QFrame(); line.setFixedHeight(1)
        line.setStyleSheet(f"background:{C_TRACK};")
        self.root.addWidget(line)
        self.root.addSpacing(6)

    def _toggle_css(self):
        return (
            f"QPushButton{{color:{C_SUBTLE};background:{C_CARD};border:1px solid {C_TRACK};}}"
            f"QPushButton:checked{{color:{C_BG};background:{C_TEXT};border:1px solid {C_TEXT};}}"
        )

    def _build_footer(self):
        f = QHBoxLayout()
        legend = QPushButton("\u2295  Evidence badge legend")
        legend.setFont(_f(9)); legend.setCursor(Qt.CursorShape.PointingHandCursor)
        legend.setStyleSheet(f"QPushButton{{color:{C_SUBTLE};background:transparent;border:none;}}")
        legend.clicked.connect(self._show_legend)
        f.addWidget(legend); f.addStretch(1)
        note = QLabel("Cosmic Scout \u00b7 offline except features you switch on")
        note.setFont(_f(8)); note.setStyleSheet(f"color:{C_CENTER};")
        f.addWidget(note)
        self.root.addLayout(f)

    def _set_scale(self, name):
        self.scale = name
        if self.state is not None:
            self.state.set_scale(name)
        self._rebuild()

    # rebuild body for the current scale
    def _rebuild(self):
        while self.body.count():
            w = self.body.takeAt(0).widget()
            if w:
                w.deleteLater()

        if self.profile is None:
            self._empty_state()
            return

        if self.scale == "Day":
            comp, rows = day_cycles(
                self.now,
                self._wake_dt(),
                profile=self.profile,
            )
            self.body.addWidget(CompositeRow(comp))
            self.body.addSpacing(4)
            for r in rows:
                self._add_row(r)
        elif self.scale == "Week":
            _, rows = day_cycles(self.now, self._wake_dt(), profile=self.profile)
            self._scale_note("THIS WEEK", "your daily cycles carried across the week")
            self._add_row(rows[0])   # circadian, as the week's dominant driver
            self._add_row(EmptyNote(
                "circaseptan", "Weekly rhythm", "\u25f7",
                "No validated endogenous weekly personal cycle \u2014 "
                "circaseptan patterns are contested and largely social.",
                BADGE_CONTESTED, "#e0a03a",
                "Seven-day rhythms appear in immune and cardiovascular data, but the "
                "weekly mood pattern tracks the working week, not an internal clock."))
        else:  # Month
            _, rows = day_cycles(self.now, self._wake_dt(), profile=self.profile)
            by_key = {r.key: r for r in rows}
            self._scale_note("THIS MONTH", "the honest monthly set")
            self._add_row(by_key["seasonal"])
            self._add_row(by_key["lunar"])
            self._add_row(EmptyNote(
                "multidien", "Discovered rhythm", "\u2795",
                "Detecting \u2014 rhythm discovery needs at least 120 days of "
                "Overall entries (Records \u203a Patterns).",
                BADGE_EMERGING, "#4aa8e0",
                "Real endogenous multi-day cycles exist and are individual. We find "
                "yours by measuring your log, never by assuming one from your birth date."))
            if "menstrual" in by_key:
                self._add_row(by_key["menstrual"])
            elif _sex_of(self.profile) == "female":
                self._add_row(EmptyNote(
                    "menstrual", "Menstrual", "\u25cb",
                    "Enable tracking in Records to show this real ~monthly hormonal cycle.",
                    BADGE_VALIDATED, "#c86ba0",
                    "A real hormonal cycle with clear effects on mood and emotional "
                    "processing (cognitive-performance effects are not reliably shown)."))

        self._maybe_space_weather()

    def _maybe_space_weather(self):
        """Add the CONTESTED space-weather row when the opt-in is on. Never blocks:
        reads the cache, and kicks an off-thread fetch when the cache is cold."""
        if self.state is None or not self.state.space_weather_enabled():
            return
        sw = space_weather.current_state(self.state)
        if sw is None:
            self._add_row(EmptyNote(
                "spaceweather", "Space weather", "\u2600",
                "Checking NOAA SWPC\u2026", BADGE_CONTESTED, "#e0a03a",
                "Live geomagnetic data from NOAA SWPC. Real instrument data; "
                "personal-biology effects are not established."))
            self._start_sw_fetch()
        elif sw.get("ok"):
            self._add_row(EmptyNote(
                "spaceweather", "Space weather", "\u2600",
                "Geomagnetic activity: Kp %.0f \u2014 %s." % (sw["kp"], sw["level"]),
                BADGE_CONTESTED, "#e0a03a",
                "Kp is a real, measured planetary geomagnetic index (0\u20139). Auroras "
                "and grid effects are real at high Kp; personal-biology effects (mood, "
                "sleep) are not established \u2014 shown as context, never scored."))
        else:
            self._add_row(EmptyNote(
                "spaceweather", "Space weather", "\u2600",
                sw.get("detail", "Unavailable."), BADGE_CONTESTED, "#e0a03a",
                "The app tried NOAA SWPC and couldn't get a reading. Everything else "
                "stays offline."))

    def _start_sw_fetch(self):
        if self._sw_thread is not None and self._sw_thread.isRunning():
            return
        self._sw_thread = _SWFetch(self.state)
        self._sw_thread.finished.connect(self._on_sw_ready)
        self._sw_thread.start()

    def _on_sw_ready(self):
        # cache is warm now; rebuild renders the real reading (no new fetch)
        self._rebuild()

    def _scale_note(self, title, sub):
        w = QWidget(); w.setFixedHeight(40)
        lay = QHBoxLayout(w); lay.setContentsMargins(2, 0, 0, 0)
        t = QLabel(title); t.setFont(_f(11, bold=True)); t.setStyleSheet(f"color:{C_TEXT};")
        s = QLabel("  " + sub); s.setFont(_f(9)); s.setStyleSheet(f"color:{C_SUBTLE};")
        lay.addWidget(t); lay.addWidget(s); lay.addStretch(1)
        self.body.addWidget(w)

    def _add_row(self, state):
        row = CycleRow(state)
        row.clicked.connect(self._open_cycle)
        self.body.addWidget(row)
        self._rows = getattr(self, "_rows", {})
        self._rows[state.key] = state
        # named driver sub-bars beneath a heading cycle
        for sub in (getattr(state, "sub_bars", None) or []):
            sr = SubBarRow(sub)
            sr.clicked.connect(self._open_sub)
            self.body.addWidget(sr)
            self._subs = getattr(self, "_subs", {})
            self._subs[sub.key] = sub

    def _open_sub(self, key):
        sub = getattr(self, "_subs", {}).get(key)
        if sub is not None:
            CycleDialog(sub, self).exec()

    def _open_cycle(self, key):
        st = self._rows.get(key)
        if st is not None:
            CycleDialog(st, self).exec()

    def _show_legend(self):
        d = QDialog(self); d.setWindowTitle("Evidence badges")
        d.setStyleSheet(f"background:{C_CARD};"); d.setFixedWidth(430)
        lay = QVBoxLayout(d); lay.setContentsMargins(24, 22, 24, 22); lay.setSpacing(10)
        head = QLabel("How we grade what you see"); head.setFont(_f(15, bold=True))
        head.setStyleSheet(f"color:{C_TEXT};"); lay.addWidget(head)
        rows = [
            (BADGE_VALIDATED, "Named channel, positive controlled evidence."),
            (BADGE_EMERGING, "A real channel, promising but incomplete \u2014 or under-studied."),
            (BADGE_CONTESTED, "Tested, inconsistent; the mechanism is disputed."),
            (BADGE_TRADITIONAL, "A cultural/symbolic system \u2014 meaning, not causation."),
        ]
        for badge, desc in rows:
            r = QHBoxLayout()
            bc = BADGE_COLORS[badge]
            pill = QLabel(badge); pill.setFont(_f(8, bold=True))
            pill.setStyleSheet(f"color:{bc};background:rgba(255,255,255,18);"
                               f"padding:3px 9px;border-radius:8px;")
            pill.setFixedWidth(pill.fontMetrics().horizontalAdvance(badge) + 24)
            d2 = QLabel(desc); d2.setWordWrap(True); d2.setFont(_f(9))
            d2.setStyleSheet(f"color:{C_TEXT};")
            r.addWidget(pill, 0, Qt.AlignmentFlag.AlignTop); r.addWidget(d2, 1)
            lay.addLayout(r)
        d.exec()

    def _wake_dt(self):
        wh, wm = self.profile.wake_hm()
        return self.now.replace(hour=wh, minute=wm, second=0, microsecond=0)

    def _location_line(self):
        p = self.profile
        if p is None or p.current_latitude is None:
            return ""
        tz = getattr(p, "current_timezone", None) or "—"
        return f"\U0001F4CD {p.current_latitude:.2f}, {p.current_longitude:.2f} · {tz}"

    def _empty_state(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0, 40, 0, 0); lay.setSpacing(10)
        t = QLabel("No profile yet")
        t.setFont(_f(16, bold=True)); t.setStyleSheet(f"color:{C_TEXT};")
        s = QLabel("Create a profile in Records to compute your cycles. "
                   "Nothing is transmitted \u2014 all calculation is local.")
        s.setWordWrap(True); s.setFont(_f(10)); s.setStyleSheet(f"color:{C_SUBTLE};")
        lay.addWidget(t); lay.addWidget(s); lay.addStretch(1)
        self.body.addWidget(w)

