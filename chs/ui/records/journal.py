"""
Cosmic Scout — ui/records/journal.py  (v1.0.0 — Tuesday 3 November 2026)

The daily log: the 12 canonical questions (data.models.DAILY_QUESTIONS), one
entry per calendar day, plus history and CSV export. Feeds pattern_analysis:
known-cycle correlation and multidien rhythm discovery (Records > Patterns).

Answer model is TRI-STATE by design: each question is Yes / No / unanswered.
Only answered questions are stored (DailyLog.answers), so positive_score()
divides by the count actually answered — a skipped question is absent, never a
silent "No". Negative-indicator questions (yes = adverse) are marked so the
reader knows the polarity; the scoring inverts them automatically.

Export writes a CSV: date, q01..q12 (yes/no/blank), score, note.
All local. No network.
"""

import csv
from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QDateEdit,
    QLineEdit, QScrollArea, QListWidget, QListWidgetItem, QButtonGroup,
    QFileDialog, QMessageBox, QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate

from ui.theme import LIGHT
from data.models import DAILY_QUESTIONS, DailyLog
from data import store

C = LIGHT

_YES, _NO = True, False


def _lbl(text, size=15, muted=False, bold=False):
    l = QLabel(text)
    l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    col = "#777777" if muted else C["text"]
    weight = "font-weight:bold;" if bold else ""
    l.setStyleSheet(f"color:{col};font-size:{size}px;background:transparent;{weight}")
    l.setWordWrap(True)
    return l


def _divider():
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setFrameShadow(QFrame.Plain)
    f.setStyleSheet(f"background:{C['border']};max-height:1px;border:none;margin:2px 0;")
    return f


class _QuestionRow(QWidget):
    """One question with a tri-state Yes/No selector (neither = unanswered)."""

    def __init__(self, q, parent=None):
        super().__init__(parent)
        self.key = q.key
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 3, 0, 3); lay.setSpacing(10)

        text = q.text + ("   (adverse if yes)" if q.negative else "")
        lbl = _lbl(text, size=14)
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(lbl, 1)

        self.group = QButtonGroup(self); self.group.setExclusive(True)
        self._btns = {}
        for val, name in ((_YES, "Yes"), (_NO, "No")):
            b = QPushButton(name); b.setCheckable(True); b.setFixedSize(56, 28)
            b.setCursor(Qt.PointingHandCursor); b.setStyleSheet(self._css())
            self.group.addButton(b)
            self._btns[val] = b
            lay.addWidget(b)

    def _css(self):
        return (
            f"QPushButton{{color:{C['subtle']};background:{C['input']};"
            f"border:1px solid {C['border']};border-radius:5px;font-size:13px;}}"
            f"QPushButton:checked{{color:#fff;background:{C['accent']};"
            f"border-color:{C['accent']};font-weight:bold;}}"
        )

    def set_value(self, val):
        """val: True, False, or None (clear)."""
        self.group.setExclusive(False)
        for v, b in self._btns.items():
            b.setChecked(val is not None and v == val)
        self.group.setExclusive(True)

    def value(self):
        for v, b in self._btns.items():
            if b.isChecked():
                return v
        return None


class JournalPage(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setStyleSheet(f"background:{C['bg']};")

        root = QVBoxLayout(self); root.setContentsMargins(28, 22, 28, 22); root.setSpacing(10)

        title = _lbl("Journal · Daily Log", size=24, bold=True)
        root.addWidget(title)

        if self.state.active_profile is None:
            root.addWidget(_lbl(
                "Create and activate a profile in Records → Profile first. "
                "The log is kept per profile.", size=14, muted=True))
            root.addStretch(1)
            return

        root.addWidget(_lbl(
            f"Logging for “{self.state.active_profile.alias}”. Answer what applies "
            f"— skipped questions are left blank, not counted as “No”.",
            size=13, muted=True))

        # date selector + score readout
        drow = QHBoxLayout()
        drow.addWidget(_lbl("Date", size=14))
        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("MM/dd/yyyy")
        self._date.setDate(QDate.currentDate())
        self._date.dateChanged.connect(self._load_for_date)
        self._date.setStyleSheet(
            f"QDateEdit{{background:{C['input']};color:{C['input_txt']};"
            f"border:1px solid {C['border']};border-radius:4px;padding:4px 8px;}}")
        drow.addWidget(self._date)
        self._score = _lbl("", size=13, muted=True)
        drow.addSpacing(14); drow.addWidget(self._score); drow.addStretch(1)
        root.addLayout(drow)
        root.addWidget(_divider())

        # body: questions (scroll) on the left, history on the right
        body = QHBoxLayout(); body.setSpacing(16)

        qwrap = QWidget(); qlay = QVBoxLayout(qwrap)
        qlay.setContentsMargins(0, 0, 0, 0); qlay.setSpacing(2)
        self._rows = {}
        for q in DAILY_QUESTIONS:
            r = _QuestionRow(q); self._rows[q.key] = r; qlay.addWidget(r)
        qlay.addWidget(_divider())
        qlay.addWidget(_lbl("Note (optional, keep it short)", size=13, muted=True))
        self._note = QLineEdit(); self._note.setMaxLength(280)
        self._note.setPlaceholderText("anything notable about today…")
        self._note.setStyleSheet(
            f"QLineEdit{{background:{C['input']};color:{C['input_txt']};"
            f"border:1px solid {C['border']};border-radius:4px;padding:6px 8px;}}")
        qlay.addWidget(self._note)
        qlay.addStretch(1)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setWidget(qwrap)
        scroll.setStyleSheet("QScrollArea{background:transparent;}")
        body.addWidget(scroll, 2)

        hwrap = QWidget(); hlay = QVBoxLayout(hwrap)
        hlay.setContentsMargins(0, 0, 0, 0); hlay.setSpacing(6)
        hlay.addWidget(_lbl("History", size=14, bold=True))
        self._history = QListWidget()
        self._history.setStyleSheet(
            f"QListWidget{{background:{C['input']};border:1px solid {C['border']};"
            f"border-radius:8px;padding:4px;}}"
            f"QListWidget::item{{padding:6px;}}"
            f"QListWidget::item:selected{{background:{C['accent']};color:#fff;"
            f"border-radius:5px;}}")
        self._history.itemClicked.connect(self._pick_history)
        hlay.addWidget(self._history, 1)
        body.addWidget(hwrap, 1)

        root.addLayout(body, 1)

        # buttons
        brow = QHBoxLayout()
        save = QPushButton("Save entry"); save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(self._primary_css()); save.clicked.connect(self._save)
        clear = QPushButton("Clear answers"); clear.setStyleSheet(self._plain_css())
        clear.clicked.connect(self._clear)
        export = QPushButton("Export CSV…"); export.setStyleSheet(self._plain_css())
        export.clicked.connect(self._export)
        brow.addWidget(save); brow.addWidget(clear); brow.addStretch(1); brow.addWidget(export)
        root.addLayout(brow)

        self._refresh_history()
        self._load_for_date()

    # --- styling helpers -----------------------------------------------------
    def _primary_css(self):
        return (f"QPushButton{{background:{C['accent']};color:#fff;border:none;"
                f"border-radius:5px;padding:7px 18px;font-weight:bold;}}"
                f"QPushButton:hover{{background:#1a5c32;}}")

    def _plain_css(self):
        return (f"QPushButton{{background:{C['panel']};color:{C['text']};"
                f"border:1px solid {C['border']};border-radius:5px;padding:7px 14px;}}"
                f"QPushButton:hover{{border-color:{C['accent']};}}")

    # --- data flow -----------------------------------------------------------
    def _current_date_iso(self):
        d = self._date.date()
        return date(d.year(), d.month(), d.day()).isoformat()

    def _clear(self):
        for r in self._rows.values():
            r.set_value(None)
        self._note.clear()
        self._update_score()

    def _load_for_date(self, *_):
        alias = self.state.active_profile.alias
        log = store.load_log(alias, self._current_date_iso())
        for key, r in self._rows.items():
            r.set_value(log.answers.get(key) if log else None)
        self._note.setText(log.note if log else "")
        self._update_score()

    def _collect_answers(self):
        return {k: r.value() for k, r in self._rows.items() if r.value() is not None}

    def _update_score(self):
        answers = self._collect_answers()
        if not answers:
            self._score.setText("no answers yet")
            return
        log = DailyLog(self._current_date_iso(), answers)
        self._score.setText(f"positive score: {log.positive_score():.2f}  "
                            f"({len(answers)}/{len(DAILY_QUESTIONS)} answered)")

    def _save(self):
        alias = self.state.active_profile.alias
        answers = self._collect_answers()
        if not answers and not self._note.text().strip():
            QMessageBox.information(self, "Nothing to save",
                                    "Answer at least one question, or add a note.")
            return
        log = DailyLog(self._current_date_iso(), answers, self._note.text().strip())
        store.save_log(alias, log)
        self._refresh_history()
        self._update_score()
        QMessageBox.information(self, "Saved",
                                f"Entry for {self._current_date_iso()} saved.")

    def _refresh_history(self):
        alias = self.state.active_profile.alias
        self._history.clear()
        for iso in reversed(store.list_log_dates(alias)):   # newest first
            log = store.load_log(alias, iso)
            score = f"{log.positive_score():.2f}" if (log and log.answers) else "—"
            item = QListWidgetItem(f"{iso}    score {score}")
            item.setData(Qt.UserRole, iso)
            self._history.addItem(item)

    def _pick_history(self, item):
        iso = item.data(Qt.UserRole)
        y, m, d = (int(x) for x in iso.split("-"))
        self._date.setDate(QDate(y, m, d))     # triggers _load_for_date

    def _export(self):
        alias = self.state.active_profile.alias
        dates = store.list_log_dates(alias)
        if not dates:
            QMessageBox.information(self, "Nothing to export", "No entries logged yet.")
            return
        default = str(store.DATA_DIR / f"{alias}_journal.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Export journal CSV", default,
                                              "CSV files (*.csv)")
        if not path:
            return
        keys = [q.key for q in DAILY_QUESTIONS]
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date"] + keys + ["score", "note"])
            for iso in dates:
                log = store.load_log(alias, iso)
                if not log:
                    continue
                cells = []
                for k in keys:
                    v = log.answers.get(k)
                    cells.append("" if v is None else ("yes" if v else "no"))
                score = f"{log.positive_score():.3f}" if log.answers else ""
                w.writerow([iso] + cells + [score, log.note])
        QMessageBox.information(self, "Exported", f"Wrote {len(dates)} entries to:\n{path}")


def build_page(state):
    return JournalPage(state)
