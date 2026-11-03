"""
Cosmic Scout — ui/records/patterns.py  (v1.0.0 — Tuesday 3 November 2026)

The Records > Patterns surface. Two engines, both biased to silence:

  KNOWN-cycle correlation (pattern_analysis.correlate)
    * under 14 usable days  -> "keep logging" progress state, no findings
    * enough data, nothing significant -> "no reliable pattern yet"
    * real findings -> plain-language lines, provisional-flagged under 30 days

  RHYTHM DISCOVERY (pattern_analysis.detect_multidien)
    Searches the Overall series for an UNKNOWN 2..40-day period (21..35 masked
    unless the profile is male) via Lomb-Scargle
    with a bootstrap false-alarm gate. Because discovery is the highest
    hallucination risk in the app, every discovery result is wrapped in a
    maturity disclaimer: a once-per-session modal on first view (this process),
    plus a persistent inline badge on the result card, stating the dataset may
    not be mature enough for firm conclusions and to keep logging accurately.

It deliberately shows WHY circadian/ultradian are absent (a daily log can't
resolve an intraday rhythm) so their absence doesn't read as an omission.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
    QMessageBox,
)
from PyQt5.QtCore import Qt

from ui.theme import LIGHT
from data import store
from engines import pattern_analysis as pa

C = LIGHT

# once-per-session (process lifetime) guard for the discovery maturity modal
_DISCOVERY_MODAL_SHOWN = False


def _lbl(t, size=15, muted=False, bold=False):
    l = QLabel(t)
    l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    col = "#777777" if muted else C["text"]
    l.setStyleSheet(f"color:{col};font-size:{size}px;background:transparent;"
                    f"{'font-weight:bold;' if bold else ''}")
    l.setWordWrap(True)
    return l


def _divider():
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setFrameShadow(QFrame.Plain)
    f.setStyleSheet(f"background:{C['border']};max-height:1px;border:none;margin:6px 0;")
    return f


def _card(title, hue):
    w = QFrame()
    w.setObjectName("PatCard")   # scope the style: QLabel is a QFrame subclass
    w.setStyleSheet(f"QFrame#PatCard{{background:{C['panel']};border:1px solid {C['border']};"
                    f"border-left:4px solid {hue};border-radius:8px;}}")
    return w


class PatternsPage(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setStyleSheet(f"background:{C['bg']};")
        root = QVBoxLayout(self); root.setContentsMargins(30, 22, 30, 22); root.setSpacing(10)

        root.addWidget(_lbl("Patterns", size=24, bold=True))
        root.addWidget(_lbl(
            "Correlations between your daily log and the cycles a once-a-day entry "
            "can actually resolve — the lunar phase, the season, the day of week, "
            "and your cycle phase (if tracked). This tool is built to stay quiet "
            "unless a pattern is real.", size=13, muted=True))

        refresh = QPushButton("Analyse my log")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setStyleSheet(
            f"QPushButton{{background:{C['accent']};color:#fff;border:none;"
            f"border-radius:5px;padding:7px 16px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#1a5c32;}}")
        refresh.clicked.connect(self._analyse)
        hb = QHBoxLayout(); hb.addWidget(refresh); hb.addStretch(1)
        root.addLayout(hb)
        root.addWidget(_divider())

        self._scroll = QScrollArea(); self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;}")
        self._body = QWidget(); self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 0, 0, 0); self._body_lay.setSpacing(8)
        self._scroll.setWidget(self._body)
        root.addWidget(self._scroll, 1)

        self._analyse()

    def _clear(self):
        while self._body_lay.count():
            w = self._body_lay.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _analyse(self):
        self._clear()
        if self.state.active_profile is None:
            self._body_lay.addWidget(_lbl(
                "Activate a profile in Records → Profile first.", size=14, muted=True))
            self._body_lay.addStretch(1)
            return

        alias = self.state.active_profile.alias
        logs = [store.load_log(alias, d) for d in store.list_log_dates(alias)]
        logs = [l for l in logs if l is not None]
        result = pa.correlate(logs, self.state.active_profile)

        # status line
        if result.status == "insufficient":
            self._status_card("Keep logging", result.message, "#4aa8e0")
        elif result.status == "none":
            self._status_card("No reliable pattern yet", result.message, "#9a9ab8")
        else:
            self._status_card(result.message,
                              f"From {result.n_days} logged days.", "#3ecf8e")
            for f in result.findings:
                self._finding_card(f)

        # --- rhythm discovery (unknown multi-day period) -------------------
        self._body_lay.addWidget(_divider())
        self._body_lay.addWidget(_lbl("Rhythm discovery", size=17, bold=True))
        profile = self.state.active_profile
        if getattr(profile, "sex", None) == "male":
            band = "an unknown 2–40 day cycle"
        else:
            band = ("an unknown 2–40 day cycle, skipping 21–35 days so the menstrual "
                    "cycle is never reported as a new rhythm")
        self._body_lay.addWidget(_lbl(
            f"Searches your Overall wellbeing for {band}. Unlike "
            "the correlations above, this looks for a rhythm nobody named in "
            "advance — the hardest thing to do honestly, so it needs the most data.",
            size=13, muted=True))
        disc = pa.detect_multidien(logs, profile=profile)
        self._discovery_card(disc)

        # what was / wasn't tested — transparency
        self._body_lay.addWidget(_divider())
        if result.gated_targets:
            names = {"lunar": "lunar", "seasonal": "seasonal",
                     "weekday": "day-of-week", "menstrual": "cycle phase"}
            g = ", ".join(names.get(t, t) for t in result.gated_targets)
            self._body_lay.addWidget(_lbl(
                f"Not enough data yet to test: {g}.", size=13, muted=True))
        self._body_lay.addWidget(_lbl(
            "Circadian and ultradian rhythms aren’t tested here: they rise and fall "
            "several times a day, so a once-daily entry can’t resolve them. See them "
            "live on the dashboard instead.", size=13, muted=True))
        self._body_lay.addStretch(1)

    def _status_card(self, title, body, hue):
        card = _card(title, hue)
        lay = QVBoxLayout(card); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(4)
        lay.addWidget(_lbl(title, size=16, bold=True))
        lay.addWidget(_lbl(body, size=13, muted=True))
        self._body_lay.addWidget(card)

    def _finding_card(self, f):
        card = _card("", "#3ecf8e")
        lay = QVBoxLayout(card); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(3)
        lay.addWidget(_lbl(pa.describe_finding(f), size=15))
        meta = f"r = {f.r:+.2f} · {f.n} days"
        if f.provisional:
            meta += " · provisional (under 30 days — a lead, not a fact)"
        lay.addWidget(_lbl(meta, size=13, muted=True))
        self._body_lay.addWidget(card)

    # --- rhythm discovery rendering ---------------------------------------
    def _discovery_card(self, d):
        hue = {"insufficient": "#4aa8e0", "none": "#9a9ab8",
               "found": "#a98ad0"}.get(d.status, "#9a9ab8")
        card = _card("", hue)
        lay = QVBoxLayout(card); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(4)

        if d.status == "found":
            head = QHBoxLayout(); head.setSpacing(8)
            head.addWidget(_lbl(f"Candidate ~{d.period_days:.1f}-day rhythm",
                                size=16, bold=True))
            head.addWidget(self._maturity_badge(d.provisional), 0, Qt.AlignVCenter)
            head.addStretch(1)
            lay.addLayout(head)
            lay.addWidget(_lbl(d.message, size=13, muted=True))
            lay.addWidget(_lbl(
                f"Signal power {d.power:.1f} vs a noise ceiling of {d.threshold:.1f} "
                f"(95th percentile of your own shuffled data) · {d.n_days} days.",
                size=12, muted=True))
        else:
            title = ("Keep logging" if d.status == "insufficient"
                     else "No multi-day rhythm found")
            lay.addWidget(_lbl(title, size=16, bold=True))
            lay.addWidget(_lbl(d.message, size=13, muted=True))

        self._body_lay.addWidget(card)

        # session-scoped maturity modal on first discovery view this run
        if d.status in ("found", "none"):
            self._maybe_show_discovery_modal(d)

    def _maturity_badge(self, provisional):
        text = "PROVISIONAL" if provisional else "EARLY DATA"
        b = QLabel(text)
        b.setStyleSheet(
            "color:#a98ad0;background:rgba(0,0,0,20);padding:3px 10px;"
            "border-radius:8px;font-weight:bold;font-size:11px;letter-spacing:1px;")
        b.setFixedHeight(20)
        return b

    def _maybe_show_discovery_modal(self, d):
        global _DISCOVERY_MODAL_SHOWN
        if _DISCOVERY_MODAL_SHOWN:
            return
        _DISCOVERY_MODAL_SHOWN = True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("About rhythm discovery")
        box.setText("Read this before trusting a discovered rhythm.")
        box.setInformativeText(
            "Rhythm discovery searches your data for a cycle that was never named "
            "in advance. A search like this can always surface a 'best' candidate "
            "— so Cosmic Scout only reports one when it beats what your own data "
            "produces after being randomly shuffled.\n\n"
            "Even then, at this much data a finding is a LEAD, not a fact. A few "
            "months of accurate daily entries is the minimum for a multi-day "
            "rhythm to mean anything, and irregular or guessed answers will "
            "manufacture rhythms that aren't real.\n\n"
            "Keep logging honestly and consistently. The more accurate days you "
            "add, the more this can be trusted — or correctly rejected.")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()


def build_page(state):
    return PatternsPage(state)
