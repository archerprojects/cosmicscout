"""
Cosmic Scout — cosmos/_sources_dialog.py  (v1.0.0 — Tuesday 3 November 2026)

Reusable editor for a Cosmos wing's "Further Reading" out-links. Generalized over
a sources_key: the dialog reads/writes via state.<key>_sources() /
set_<key>_sources() / reset_<key>_sources(). Defaults to "tropical" so existing
callers are unaffected. Seed defaults are just seeds — the user can rename,
replace, add, remove, or reset. Persisted through AppState -> data.store (the
single write path). Out-links only; no third-party text is stored.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget, QFrame,
)
from PyQt5.QtCore import Qt

from ui.theme import LIGHT

_TITLES = {
    "tropical": "Tropical Zodiac",
    "shengxiao": "Twelve Animals",
    "bazi": "BaZi Four Pillars",
    "trad_earth": "Earth Traditions",
    "sidereal": "Vedic (Sidereal)",
}


class SourcesDialog(QDialog):
    def __init__(self, state, parent=None, sources_key="tropical"):
        super().__init__(parent)
        self.state = state
        self.key = sources_key
        self._get = getattr(state, "%s_sources" % sources_key)
        self._set = getattr(state, "set_%s_sources" % sources_key)
        self._reset = getattr(state, "reset_%s_sources" % sources_key)

        self.setWindowTitle("Edit Sources \u2014 %s" % _TITLES.get(sources_key, sources_key))
        self.setMinimumWidth(520)
        self._rows = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        intro = QLabel("Name and link for each source. These open in the browser \u2014 "
                       "add your own, or reset to defaults.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:%s;font-size:11px;" % LIGHT["subtle"])
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._holder = QWidget()
        self._rows_lay = QVBoxLayout(self._holder)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(6)
        scroll.setWidget(self._holder)
        root.addWidget(scroll, 1)

        add = QPushButton("+ Add source")
        add.clicked.connect(lambda: self._add_row("", ""))
        root.addWidget(add, 0, Qt.AlignLeft)

        buttons = QHBoxLayout()
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._do_reset)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setStyleSheet("font-weight:bold;")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        for src in self._get():
            self._add_row(src.get("name", ""), src.get("url", ""))

    def _add_row(self, name, url):
        row = QWidget()
        hbox = QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(6)
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Name")
        name_edit.setMaximumWidth(180)
        url_edit = QLineEdit(url)
        url_edit.setPlaceholderText("https://\u2026")
        rm = QPushButton("\u00d7")
        rm.setFixedWidth(28)
        rm.clicked.connect(lambda: self._remove_row(row))
        hbox.addWidget(name_edit)
        hbox.addWidget(url_edit, 1)
        hbox.addWidget(rm)
        self._rows_lay.addWidget(row)
        self._rows.append((row, name_edit, url_edit))

    def _remove_row(self, row):
        self._rows = [r for r in self._rows if r[0] is not row]
        row.deleteLater()

    def _do_reset(self):
        for row, _, _ in self._rows:
            row.deleteLater()
        self._rows = []
        self._reset()
        for src in self._get():
            self._add_row(src.get("name", ""), src.get("url", ""))

    def _save(self):
        sources = []
        for _, name_edit, url_edit in self._rows:
            name = name_edit.text().strip()
            url = url_edit.text().strip()
            if name and url:
                sources.append({"name": name, "url": url})
        self._set(sources)
        self.accept()
