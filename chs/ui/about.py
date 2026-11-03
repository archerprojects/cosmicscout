"""
Cosmic Scout — ui/about.py  (v1.0.0 — Tuesday 3 November 2026)

The evidence spine made visible: how the app decides what to show and how it
labels it (the name-the-channel test), the badge legend, and a citations registry
for every scientific claim the app makes — plus data attribution, privacy, the
standard disclaimers, licence, version and developer.

Pure content: no profile, no compute, no network. Light theme.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt

from ui.theme import LIGHT, BADGE_COLORS_LIGHT

APP_VERSION = "1.0.0"


def _card():
    f = QFrame(); f.setObjectName("Card")
    f.setStyleSheet("QFrame#Card{background:%s;border:1px solid %s;border-radius:10px;}"
                    % (LIGHT["panel"], LIGHT["border"]))
    return f


def _h(text):
    t = QLabel(text)
    t.setStyleSheet("font-size:16px;font-weight:bold;color:%s;" % LIGHT["text"])
    return t


def _p(text, muted=False, size=14):
    q = QLabel(text)
    q.setTextInteractionFlags(Qt.TextSelectableByMouse); q.setWordWrap(True)
    q.setTextInteractionFlags(Qt.TextBrowserInteraction)
    q.setOpenExternalLinks(True)
    q.setStyleSheet("font-size:%dpx;color:%s;" % (size, LIGHT["subtle"] if muted else LIGHT["text"]))
    return q


def _badge_chip(name):
    b = QLabel(name)
    b.setStyleSheet("color:%s;background:rgba(0,0,0,20);padding:2px 9px;border-radius:8px;"
                    "font-weight:bold;font-size:12px;" % BADGE_COLORS_LIGHT.get(name, "#888"))
    b.setFixedHeight(20)
    return b


def build_page():
    page = QWidget()
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
    outer.addWidget(scroll)
    body = QWidget(); lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)
    scroll.setWidget(body)

    title = QLabel("About \u00b7 A mix of science and tradition")
    title.setStyleSheet("font-size:24px;font-weight:bold;color:%s;" % LIGHT["text"])
    lay.addWidget(title)
    lay.addWidget(_p("Cosmic Scout mixes validated science with living traditions. All cycle "
                     "information shown is graded and presented to you in its current state "
                     "of legitimacy. We based much of the app on science but realize there "
                     "is much science has yet to reveal.", muted=True))

    # --- name the channel ---
    c1 = _card(); l1 = QVBoxLayout(c1); l1.setContentsMargins(20, 16, 20, 18); l1.setSpacing(8)
    l1.addWidget(_h("The name-the-channel test"))
    l1.addWidget(_p("Claims badged as Validated have a scientifically researched "
                    "<b>channel of influence</b> that can be named and traced. They have a "
                    "carrier, a receptor or pathway, a dose, a demonstrable influence. A "
                    "cosmic origin carries no objection on its own; an <i>unnamed</i> "
                    "influence is harder to place. Circadian entrainment, for example, is "
                    "both cosmic and well-validated because its channel (light \u2192 the "
                    "eye's melanopsin \u2192 the SCN clock) is fully traced."))
    l1.addWidget(_p("Where possible, we badge the pattern and its explanation "
                    "<b>separately</b>. A pattern can be real while a traditional explanation "
                    "for it is uncertain. Constellation astrology has not shown clear "
                    "validity in research testing, yet season-of-birth has shown effects on "
                    "the body clock in many ways. Through time many cultures have "
                    "independently noticed the same rhythms. So while substantiated research "
                    "on some may be lacking, this also tells us the pattern was worth "
                    "noticing. It may be the mechanism is not realized yet."))
    lay.addWidget(c1)

    # --- badge legend ---
    c2 = _card(); l2 = QVBoxLayout(c2); l2.setContentsMargins(20, 16, 20, 18); l2.setSpacing(9)
    l2.addWidget(_h("Badge legend"))
    l2.addWidget(_p("All cycle information carries a badge showing its current "
                    "research-based standing:", muted=True))
    legend = [
        ("VALIDATED", "Named channel, replicated evidence. Shown as guidance."),
        ("EMERGING", "A real signal with a partly-traced mechanism; promising, not settled."),
        ("CONTESTED", "Genuinely disputed, or a real force with unproven personal effects."),
        ("TRADITIONAL", "Presented on its own terms \u2014 which means honestly, never as lesser."),
        ("REFUTED", "Tested and not supported. Kept only as an honest example, never shown as guidance."),
    ]
    for name, meaning in legend:
        row = QHBoxLayout(); row.setSpacing(10)
        chip = _badge_chip(name); chip.setMinimumWidth(112); chip.setAlignment(Qt.AlignCenter)
        row.addWidget(chip, 0, Qt.AlignTop)
        row.addWidget(_p(meaning), 1)
        l2.addLayout(row)
    lay.addWidget(c2)

    # --- citations registry ---
    c3 = _card(); l3 = QVBoxLayout(c3); l3.setContentsMargins(20, 16, 20, 18); l3.setSpacing(10)
    l3.addWidget(_h("Sources & citations"))

    def group(heading, badge_name, refs):
        hr = QHBoxLayout(); hr.setSpacing(8)
        gh = QLabel(heading); gh.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
        hr.addWidget(gh); hr.addWidget(_badge_chip(badge_name)); hr.addStretch(1)
        l3.addLayout(hr)
        for r in refs:
            item = _p("\u2022 " + r, muted=True, size=13)
            item.setContentsMargins(6, 0, 0, 0)
            l3.addWidget(item)
        l3.addSpacing(4)

    group("Chronobiology \u2014 the validated core", "VALIDATED", [
        "Nobel Prize in Physiology or Medicine 2017 \u2014 Hall, Rosbash & Young, for the "
        "molecular mechanism of the circadian clock.",
        "Kleitman N. (1963). Sleep and Wakefulness. Univ. of Chicago Press \u2014 the "
        "basic rest-activity cycle (BRAC) and the discovery of REM sleep.",
    ])
    group("Season of birth \u2192 chronotype", "VALIDATED", [
        "Ciarleglio C.M., Axley J.C., Strauss B.R., Gamble K.L., McMahon D.G. (2011). "
        "Perinatal photoperiod imprints the circadian clock. Nature Neuroscience 14(1):25\u201327. "
        "\u2014 causal, in mice.",
        "Vollmer C., Randler C., Di Milia L. (2012). Further evidence for the influence of "
        "photoperiod at birth on chronotype in a sample of German adolescents. Chronobiology "
        "International 29(10):1345\u20131351. \u2014 human association; the effect is small and "
        "not seen in every sample.",
    ])
    group("Biorhythm \u2014 not present", "REFUTED", [
        "Hines T.M. (1998). Comprehensive Review of Biorhythm Theory. Psychological Reports "
        "83(1):19\u201364. \u2014 134 studies; no predictive power beyond chance.",
    ])
    group("Traditions \u2014 on their own terms", "TRADITIONAL", [
        "Sun Bear & Wabun Wind (1980). The Medicine Wheel: Earth Astrology. \u2014 a modern "
        "neo-shamanic synthesis, not an attested Indigenous system.",
        "Graves R. (1948). The White Goddess. \u2014 the source of the modern Celtic "
        "tree-calendar (Ogham) synthesis.",
        "Maya Tzolk'in: Goodman\u2013Mart\u00ednez\u2013Thompson (GMT) correlation, "
        "JDN 584283 = 4 Ahau.",
        "Vedic chart & nakshatra: Lahiri ayanamsha (Indian government standard), via the "
        "Swiss Ephemeris.",
    ])
    lay.addWidget(c3)

    # --- data, attribution & privacy ---
    c4 = _card(); l4 = QVBoxLayout(c4); l4.setContentsMargins(20, 16, 20, 18); l4.setSpacing(8)
    l4.addWidget(_h("Data, attribution & privacy"))
    l4.addWidget(_p("No personal data is shared with a third party for any use other than "
                    "as required for app function. Astronomy is computed offline: charts "
                    "use the <b>Swiss Ephemeris</b> by Astrodienst (via pyswisseph and a "
                    "vendored copy of flatlib), used under the <b>AGPL-3.0</b>; Moon, Sun "
                    "and season events use <b>PyEphem</b> (MIT); the lunar calendar uses "
                    "<b>lunardate</b> (GPL-3.0-or-later). Full notices: THIRD_PARTY_LICENSES.md "
                    "in the source repository. "
                    "The city search uses the <b>GeoNames</b> gazetteer, \u00a9 GeoNames, "
                    "licensed <b>CC BY 4.0</b> "
                    "(<a href='https://creativecommons.org/licenses/by/4.0/'>creativecommons.org/licenses/by/4.0</a>).",
                    size=13))
    l4.addWidget(_p("All data stays on the local device. Cosmic Scout stores only what a "
                    "calculation needs (alias, birth date/time, coordinates, offset) as local "
                    "files. If you switch on Space Weather (off by default), the app fetches "
                    "current readings from NOAA SWPC and shows them as a CONTESTED layer; "
                    "they never change the validated composite. Nothing else uses the "
                    "network.",
                    size=13))
    lay.addWidget(c4)

    # --- disclaimers ---
    c5 = _card(); l5 = QVBoxLayout(c5); l5.setContentsMargins(20, 16, 20, 18); l5.setSpacing(6)
    l5.addWidget(_h("Please read"))
    l5.addWidget(_p("Cosmic Scout is for reflection and curiosity. It is <b>not</b> medical, "
                    "psychological, or professional advice, and nothing here diagnoses or "
                    "treats any condition \u2014 if something health-related concerns you, "
                    "talk to a qualified professional. Traditional systems are offered as "
                    "culture and meaning, not as predictions of the future.", size=13))
    lay.addWidget(c5)

    # --- app info ---
    c6 = _card(); l6 = QVBoxLayout(c6); l6.setContentsMargins(20, 16, 20, 18); l6.setSpacing(4)
    l6.addWidget(_h("Cosmic Scout %s" % APP_VERSION))
    l6.addWidget(_p("Licence: GPL-3.0-or-later. Bundled Swiss Ephemeris parts: AGPL-3.0.",
                    size=13, muted=True))
    l6.addWidget(_p("Developer: archerprojects &lt;archer.projects@proton.me&gt;.", size=13, muted=True))
    l6.addWidget(_p("Repository: <a href='https://github.com/archerprojects/CosmicScout'>"
                    "github.com/archerprojects/CosmicScout</a>.", size=13, muted=True))
    lay.addWidget(c6)

    lay.addStretch(1)
    return page
