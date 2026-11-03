"""
Cosmic Scout — ui/nav.py  (v1.0.0 — Tuesday 3 November 2026)

Navigation shell pieces. WingPage renders a section that has its own sub-nav —
Cosmos (the astro_* and trad_earth modules) and Records (Profile / Journal /
Settings) both use it. Light-themed, matching the application shell; only the
Dashboard cockpit is dark.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QButtonGroup,
    QFrame, QLabel,
)
from PyQt5.QtCore import Qt

from ui.theme import LIGHT


class WingPage(QWidget):
    """A section with a horizontal sub-nav and a content stack.

    items: list of (label, build_callable) where build_callable() -> QWidget
    Widgets are built lazily on first view so the skeleton starts fast.
    """

    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        self._items = items
        self._built = {}
        # paint an opaque background so no page behind this one bleeds through
        # at the edges when content is shorter/narrower than the viewport.
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"WingPage {{ background:{LIGHT['bg']}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sub-nav bar
        barw = QWidget()
        barw.setStyleSheet(f"background:{LIGHT['panel']};")
        bar = QHBoxLayout(barw)
        bar.setContentsMargins(24, 10, 24, 10)
        bar.setSpacing(6)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"color:{LIGHT['subtle']};font-weight:bold;font-size:12px;"
            f"letter-spacing:1px;")
        bar.addWidget(lbl)
        bar.addSpacing(14)

        self.group = QButtonGroup(self)
        for i, (label, _fn) in enumerate(items):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            b.setStyleSheet(self._btn_css())
            # size to the label so long names ("Earth Traditions") never clip;
            # there is ample horizontal room in the sub-nav row.
            b.setMinimumWidth(b.fontMetrics().horizontalAdvance(label) + 28)
            b.clicked.connect(lambda _, idx=i: self._show(idx))
            self.group.addButton(b, i)
            bar.addWidget(b)
        bar.addStretch(1)
        root.addWidget(barw)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{LIGHT['border']};")
        root.addWidget(line)

        self.stack = QStackedWidget()
        self.stack.setAutoFillBackground(True)
        # scoped to the stack itself: an unscoped rule would repaint every label
        # on every page with the page colour, boxing text inside cards
        self.stack.setObjectName("WingStack")
        self.stack.setStyleSheet(f"QStackedWidget#WingStack {{ background:{LIGHT['bg']}; }}")
        root.addWidget(self.stack, 1)

        for _ in items:
            self.stack.addWidget(QWidget())    # placeholder slots
        self._show(0)

    def _btn_css(self):
        return (
            f"QPushButton{{color:{LIGHT['subtle']};background:transparent;"
            f"border:none;padding:5px 10px;font-size:13px;}}"
            f"QPushButton:checked{{color:{LIGHT['accent']};font-weight:bold;"
            f"border-bottom:2px solid {LIGHT['accent']};}}"
        )

    def invalidate(self, keep=None):
        """Drop cached pages so each rebuilds from current state on its next view.
        `keep` is a label left as built (e.g. the Profile page that made the change).
        The visible page, unless kept, is rebuilt at once."""
        current = self.stack.currentIndex()
        for idx in list(self._built):
            if self._items[idx][0] == keep:
                continue
            w = self._built.pop(idx)
            slot = QWidget()
            self.stack.insertWidget(idx, slot)
            self.stack.removeWidget(w)
            w.deleteLater()
        if current not in self._built:
            self._show(current)
        else:
            self.stack.setCurrentIndex(current)

    def _show(self, idx):
        if idx not in self._built:
            _label, fn = self._items[idx]
            w = fn()
            # paint an opaque fill on THIS page's top-level widget only (scoped by
            # object name so card/colored child backgrounds are untouched), so no
            # previously-shown page bleeds through at the edges.
            w.setObjectName("WingContent")
            w.setAutoFillBackground(True)
            w.setStyleSheet((w.styleSheet() or "") +
                            f"\nQWidget#WingContent {{ background:{LIGHT['bg']}; }}")
            old = self.stack.widget(idx)
            self.stack.insertWidget(idx, w)
            self.stack.removeWidget(old)
            old.deleteLater()
            self._built[idx] = w
        self.stack.setCurrentIndex(idx)
