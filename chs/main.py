#!/usr/bin/env python3
"""
Cosmic Scout — main.py  (v1.0.0 — Tuesday 3 November 2026)

Application entry point and MainWindow. A light shell with a top nav:

    Dashboard | Cycles | Records | Cosmos | About

Dashboard is the live dark cockpit (the composite guidance surface). Cycles and
About are single pages. Records and Cosmos are sub-navigated wings whose pages
build on first view. Any profile change refreshes every page (_profile_changed).

Run:  python3 chs/main.py   (or via cosmicscout.sh in the Flatpak)
"""

import os
import sys

# make the package root (chs/) importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (                       # noqa: E402
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QButtonGroup, QFrame, QMessageBox,
)
from PyQt5.QtCore import Qt, QSettings               # noqa: E402
from PyQt5.QtGui import QIcon                        # noqa: E402

from ui.theme import LIGHT, light_qss               # noqa: E402
from ui.dashboard import Dashboard                   # noqa: E402
from ui.nav import WingPage                          # noqa: E402
from ui import cycles_pages, about, moon_sky          # noqa: E402
from ui.records import profile_dialog, journal, settings, patterns  # noqa: E402
from app_state import AppState                        # noqa: E402
from cosmos import (                                 # noqa: E402
    astro_tropical, astro_shengxiao, astro_bazi, astro_sidereal, trad_earth,
)

APP_NAME = "Cosmic Scout"
NAV_ITEMS = ["Dashboard", "Cycles", "Records", "Cosmos", "About"]


class MainWindow(QMainWindow):
    def __init__(self, now=None):
        super().__init__()
        self.now = now            # None = live: each page reads the profile's local time
        self.state = AppState()
        self.state.load_last_profile()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 720)
        self.setMinimumSize(820, 600)
        self._restore_geometry()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topnav())
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # --- pages -----------------------------------------------------------
        self.dashboard = Dashboard(self.state.active_profile,
                                   now=self.now, state=self.state)
        self.stack.addWidget(self.dashboard)                            # Dashboard
        self.cycles = cycles_pages.build_page(self.state)
        self.stack.addWidget(self.cycles)                                # Cycles
        self.records = WingPage("Records", [                           # Records
            ("Profile",  lambda: profile_dialog.build_page(
                self.state, on_change=lambda: self._profile_changed(keep="Profile"))),
            ("Journal",  lambda: journal.build_page(self.state)),
            ("Patterns", lambda: patterns.build_page(self.state)),
            ("Settings", lambda: settings.build_page(
                self.state, on_change=lambda: self._profile_changed(keep="Settings"))),
        ])
        self.stack.addWidget(self.records)
        self.cosmos = WingPage("Cosmos", [                             # Cosmos
            ("Moon && Sky", lambda: moon_sky.build_page(self.state)),   # && = literal & on a button
            ("Tropical Zodiac", lambda: astro_tropical.build_page(self.state)),
            ("Sh\u0113ngxi\u00e0o", lambda: astro_shengxiao.build_page(self.state)),
            ("BaZi",      lambda: astro_bazi.build_page(self.state)),
            ("Vedic",     lambda: astro_sidereal.build_page(self.state)),
            ("Earth Traditions", lambda: trad_earth.build_page(self.state)),
        ])
        self.stack.addWidget(self.cosmos)
        self.stack.addWidget(about.build_page())                        # About

        self._select(0)
        self._check_travel()

    def _check_travel(self):
        """Announce (not act on) an OS-timezone change since last session.
        Local read only — no network, no IP. Points the user to Settings."""
        new_zone = self.state.detect_timezone_change()
        if new_zone:
            QMessageBox.information(
                self, "Location may have changed",
                f"Your system timezone is now {new_zone}.\n\n"
                f"If you've travelled, open Records \u2192 Settings to set your "
                f"current location. Nothing has been changed automatically.")

    def _build_topnav(self):
        barw = QWidget()
        barw.setStyleSheet(f"background:{LIGHT['bg']};")
        bar = QHBoxLayout(barw)
        bar.setContentsMargins(20, 10, 20, 8)
        bar.setSpacing(4)

        self.group = QButtonGroup(self)
        for i, name in enumerate(NAV_ITEMS):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            b.setFixedHeight(34)
            b.setStyleSheet(self._nav_css())
            b.clicked.connect(lambda _, idx=i: self._select(idx))
            self.group.addButton(b, i)
            bar.addWidget(b)
        bar.addStretch(1)

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        wl.addWidget(barw)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{LIGHT['border']};")
        wl.addWidget(line)
        return wrap

    def _nav_css(self):
        return (
            f"QPushButton{{color:{LIGHT['subtle']};background:transparent;"
            f"border:none;padding:6px 14px;font-size:13px;font-weight:bold;}}"
            f"QPushButton:checked{{color:{LIGHT['accent']};"
            f"border-bottom:2px solid {LIGHT['accent']};}}"
        )

    def _select(self, idx):
        self.stack.setCurrentIndex(idx)

    def _profile_changed(self, keep=None):
        """Refresh every page against the current active profile. Called after
        any profile add / edit / delete / set-active, and after Settings applies a
        location. Dashboard and Cycles rebuild now; the wing pages rebuild on their
        next view. `keep` is the Records page that made the change, left as is."""
        current = self.stack.currentIndex()
        self.dashboard = self._replace(self.dashboard, Dashboard(
            self.state.active_profile, now=self.now, state=self.state))
        self.cycles = self._replace(self.cycles, cycles_pages.build_page(self.state))
        self.records.invalidate(keep=keep)
        self.cosmos.invalidate()
        self.stack.setCurrentIndex(current)

    def _replace(self, old, new):
        idx = self.stack.indexOf(old)
        self.stack.insertWidget(idx, new)
        self.stack.removeWidget(old)
        old.deleteLater()
        return new

    def _restore_geometry(self):
        geom = QSettings("CosmicScout", "MainWindow").value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)

    def closeEvent(self, event):
        QSettings("CosmicScout", "MainWindow").setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def _app_icon():
    """Themed icon when installed (Flatpak hicolor tree); otherwise the repo's
    own 256px icon, so a run from source still shows it."""
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.join(here, "..", "flatpak", "icons", "256x256", "apps",
                            "org.cosmicscout.app.png")
    return QIcon.fromTheme("org.cosmicscout.app", QIcon(fallback))


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("org.cosmicscout.app")   # Wayland: match the .desktop icon
    app.setWindowIcon(_app_icon())
    app.setStyleSheet(light_qss())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
