"""
Cosmic Scout — ui/cycles_pages.py  (v1.0.0 — Tuesday 3 November 2026)

The Cycles wing: the "why" behind every bar on the dashboard. It reads the same
composite cycle engine the dashboard uses (engines.cycles.day_cycles) and lays
each cycle out as a readable card — the named channel (the "name the channel"
test), the evidence badge, the current phase, and the longer explanation the
dashboard only surfaces on tap.

This page is a reader, not a second model: it computes nothing the dashboard
doesn't, so the two can never disagree. With an AppState it renders the active
profile's live cycles; without one (or with no active profile) it renders the
same explanations against a neutral 07:00 wake, so the wing is always
informative and never blank.
"""


from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy,
)
from PyQt5.QtCore import Qt

from ui.theme import LIGHT, BADGE_COLORS_LIGHT
from engines.cycles import day_cycles
from data import geo


# --- badge glossary (mirrors About + the evidence-spine spec) ----------------
_BADGE_MEANING = {
    "VALIDATED":   "Named channel, measured, replicated.",
    "EMERGING":    "Real channel; personal effect still firming up.",
    "CONTESTED":   "Tested, inconsistent; the mechanism is disputed.",
    "TRADITIONAL": "A cultural framework, offered as context, not physiology.",
}


def _badge_pill(badge):
    b = QLabel(badge)
    bc = BADGE_COLORS_LIGHT.get(badge, "#888")
    b.setStyleSheet(
        f"color:{bc};background:rgba(0,0,0,20);padding:3px 10px;"
        f"border-radius:8px;font-weight:bold;font-size:11px;letter-spacing:1px;")
    b.setFixedHeight(20)
    return b


def _phase_line(state):
    """'RISING · peak in 2h 10m' — phase word plus the engine's own timing."""
    parts = [state.phase_word]
    if getattr(state, "timing", ""):
        parts.append(state.timing)
    return "  \u00b7  ".join(parts)


def _cycle_card(state, is_sub=False):
    card = QFrame()
    card.setObjectName("Card")
    pad = 14 if is_sub else 18
    card.setStyleSheet(
        f"QFrame#Card{{background:{LIGHT['panel']};"
        f"border:1px solid {LIGHT['border']};border-radius:10px;}}"
        + (f"QFrame#Card{{margin-left:22px;}}" if is_sub else ""))
    cl = QVBoxLayout(card)
    cl.setContentsMargins(pad, pad - 2, pad, pad)
    cl.setSpacing(6)

    # header: icon + name + badge + phase
    head = QHBoxLayout()
    head.setSpacing(8)
    icon = getattr(state, "icon", "")
    title = f"{icon}  {state.name}" if icon else state.name
    t = QLabel(title)
    fs = 13 if is_sub else 15
    t.setStyleSheet(f"font-size:{fs}px;font-weight:bold;color:{LIGHT['text']};")
    head.addWidget(t)
    head.addWidget(_badge_pill(state.badge), 0, Qt.AlignVCenter)
    head.addStretch(1)
    phase = QLabel(_phase_line(state))
    phase.setStyleSheet(f"color:{LIGHT['accent']};font-size:12px;font-weight:bold;")
    head.addWidget(phase, 0, Qt.AlignVCenter)
    cl.addLayout(head)

    # the named channel — the core honesty claim
    ch = QLabel(state.channel)
    ch.setWordWrap(True)
    ch.setStyleSheet(
        f"color:{LIGHT['subtle']};font-size:12px;font-style:italic;"
        f"padding:1px 0;")
    cl.addWidget(ch)

    # the longer explanation
    if getattr(state, "detail", ""):
        d = QLabel(state.detail)
        d.setWordWrap(True)
        d.setStyleSheet(f"color:{LIGHT['text']};font-size:13px;")
        cl.addWidget(d)

    # named sub-drivers, thinner, indented
    for sub in (getattr(state, "sub_bars", None) or []):
        cl.addWidget(_cycle_card(sub, is_sub=True))

    return card


def _resolve(state):
    """Return (now, wake, profile) from an AppState, or neutral defaults."""
    profile = getattr(state, "active_profile", None) if state is not None else None
    now = geo.local_now(getattr(profile, "current_timezone", None))
    wake = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if state is not None:
        if profile is not None and hasattr(profile, "wake_hm"):
            try:
                wh, wm = profile.wake_hm()
                wake = now.replace(hour=wh, minute=wm, second=0, microsecond=0)
            except Exception:
                pass
    return now, wake, profile


def build_page(state=None):
    """Cycles wing. `state` optional: with an active profile the cards are live
    and personalised; without one they explain the same cycles generically."""
    now, wake, profile = _resolve(state)
    _comp, rows = day_cycles(now, wake, profile=profile)

    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # intro band
    band = QWidget()
    band.setStyleSheet(f"background:{LIGHT['bg']};")
    bl = QVBoxLayout(band)
    bl.setContentsMargins(36, 26, 36, 14)
    bl.setSpacing(6)
    h = QLabel("Cycles")
    h.setStyleSheet(f"font-size:24px;font-weight:bold;color:{LIGHT['text']};")
    bl.addWidget(h)
    sub = QLabel(
        "The explanation behind every bar on the dashboard \u2014 each cycle's "
        "named channel, its evidence grade, and how it reads right now."
        + ("" if profile is not None else
           "  No active profile, so these use a neutral 07:00 wake; open a "
           "profile in Records for your own figures."))
    sub.setWordWrap(True)
    sub.setStyleSheet(f"color:{LIGHT['subtle']};font-size:14px;")
    bl.addWidget(sub)
    outer.addWidget(band)

    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{LIGHT['border']};")
    outer.addWidget(line)

    # scrollable card list
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background:{LIGHT['bg']}; }}")   # scoped: don't box card labels
    inner = QWidget()
    il = QVBoxLayout(inner)
    il.setContentsMargins(36, 18, 36, 14)
    il.setSpacing(12)
    for r in rows:
        il.addWidget(_cycle_card(r))

    # badge legend footer
    legend = QFrame()
    legend.setObjectName("Card")
    legend.setStyleSheet(
        f"QFrame#Card{{background:{LIGHT['panel']};"
        f"border:1px solid {LIGHT['border']};border-radius:10px;}}")
    ll = QVBoxLayout(legend)
    ll.setContentsMargins(18, 14, 18, 14)
    ll.setSpacing(5)
    lh = QLabel("How to read the badges")
    lh.setStyleSheet(f"color:{LIGHT['subtle']};font-weight:bold;font-size:12px;")
    ll.addWidget(lh)
    for badge, meaning in _BADGE_MEANING.items():
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(_badge_pill(badge), 0, Qt.AlignTop)
        m = QLabel(meaning)
        m.setWordWrap(True)
        m.setStyleSheet(f"color:{LIGHT['text']};font-size:12px;")
        row.addWidget(m, 1)
        ll.addLayout(row)
    il.addWidget(legend)

    il.addStretch(1)
    scroll.setWidget(inner)
    outer.addWidget(scroll, 1)

    page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return page
