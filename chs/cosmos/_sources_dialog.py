"""
Cosmic Scout — cosmos/_sources_dialog.py  (v1.1.0 — Monday 9 November 2026)

Editor for a Cosmos tab's "Further Reading" links. Works on any tab key through
AppState.links / set_links / reset_links, which store the list in the active
profile. Add and delete rows freely; there is no minimum or maximum. Reset
fills the rows with the shipped defaults, and Save then lets the tab follow the
defaults again. Each row shows the dot from the last link check. Save accepts
only http(s) addresses (validated on Save, never per field). Out-links only;
no third-party text is stored.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from ui.theme import LIGHT
from cosmos import links as L
from cosmos._links_section import _dot


class SourcesDialog(QDialog):
    def __init__(self, state, parent=None, sources_key="tropical"):
        super().__init__(parent)
        self.state = state
        self.key = sources_key

        self.setWindowTitle("Edit Links — %s" % L.TAB_TITLES.get(sources_key, sources_key))
        self.setMinimumWidth(560)
        self._rows = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        intro = QLabel("Name and link for each source. These open in your browser and "
                       "are saved with this profile — add your own, delete any, or "
                       "reset to the defaults.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:%s;font-size:11px;" % LIGHT["subtle"])
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._holder = QWidget()
        self._rows_lay = QVBoxLayout(self._holder)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(6)
        self._rows_lay.addStretch(1)
        scroll.setWidget(self._holder)
        root.addWidget(scroll, 1)

        add = QPushButton("+ Add link")
        add.clicked.connect(lambda: self._add_row("", ""))
        root.addWidget(add, 0, Qt.AlignmentFlag.AlignLeft)

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

        for src in state.links(sources_key):
            self._add_row(src.get("name", ""), src.get("url", ""))

    def _add_row(self, name, url):
        row = QWidget()
        hbox = QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(6)
        hbox.addWidget(_dot(self.state.link_check(url).get("status") if url else None))
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Name")
        name_edit.setMaximumWidth(180)
        url_edit = QLineEdit(url)
        url_edit.setPlaceholderText("https://…")
        rm = QPushButton("×")
        rm.setFixedWidth(28)
        rm.setToolTip("Delete this link")
        rm.clicked.connect(lambda: self._remove_row(row))
        hbox.addWidget(name_edit)
        hbox.addWidget(url_edit, 1)
        hbox.addWidget(rm)
        self._rows_lay.insertWidget(self._rows_lay.count() - 1, row)
        self._rows.append((row, name_edit, url_edit))

    def _remove_row(self, row):
        self._rows = [r for r in self._rows if r[0] is not row]
        row.deleteLater()

    def _do_reset(self):
        for row, _, _ in self._rows:
            row.deleteLater()
        self._rows = []
        for src in L.defaults(self.key):
            self._add_row(src["name"], src["url"])

    def _save(self):
        items, bad = [], []
        for _, name_edit, url_edit in self._rows:
            name = name_edit.text().strip()
            url = url_edit.text().strip()
            if not name and not url:
                continue                              # blank row: ignored
            if not name or not L.valid_url(url):
                bad.append(name or url or "(blank)")
                continue
            items.append({"name": name, "url": url})
        if bad:
            QMessageBox.warning(
                self, "Check these links",
                "Each link needs a name and an address starting with http:// or "
                "https://. Fix or delete:\n\n" + "\n".join("• " + b for b in bad))
            return
        if items == L.defaults(self.key):
            self.state.reset_links(self.key)          # follow the shipped defaults
        else:
            self.state.set_links(self.key, items)
        self.accept()
