"""
Cosmic Scout — ui/records/profile_dialog.py  (v1.0.0 — Tuesday 3 November 2026)

The Records > Profile surface. Two parts:

  * ProfileForm (QDialog) — create/edit one profile. Ported from the proven v1
    dialog: MM/dd/yyyy date, QLineEdit time, lat/lon as free text parsed on Save
    (no validators, QTimeEdit / lat-lon spinboxes still banned). Extended with the
    v1.2 fields: current location, wake time, and the menstrual opt-in.
    The dialog VALIDATES and BUILDS a Profile, then hands it back — it does NOT
    write to disk. The caller persists via app_state/store (single write path).

  * ProfilePage (QWidget) — multi-profile manager: list every saved profile, set
    the active one (drives the dashboard), and New / Edit / Delete. On any change
    it calls the on_change callback so the dashboard rebinds immediately.

parse_coordinate() is carried verbatim from v1 (all four spec formats plus
comma-decimal), the single source of truth for coordinate parsing.
"""

from datetime import date

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QFrame, QDoubleSpinBox, QDateEdit, QMessageBox, QListWidget,
    QListWidgetItem, QSpinBox, QComboBox, QScrollArea,
)
from PyQt5.QtCore import Qt, QDate

from ui.theme import LIGHT
from data.models import Profile
from data import store
from engines import lunar_calendar

C = LIGHT


# --------------------------------------------------------------------------- #
#  coordinate parser (carried verbatim from v1 — the one parser)
# --------------------------------------------------------------------------- #
def format_coordinate(value: float, is_lat: bool) -> str:
    """Display form for a stored coordinate: 6 decimals (~0.1 m) + N/S/E/W,
    e.g. 51.641111\u00b0 N. parse_coordinate() reads it straight back."""
    if is_lat:
        hemi = "N" if value >= 0 else "S"
    else:
        hemi = "E" if value >= 0 else "W"
    return f"{abs(value):.6f}\u00b0 {hemi}"


def parse_coordinate(text: str, is_lat: bool) -> float:
    """
    Parse a coordinate in any common format:
        Decimal:  25.0330  /  -25.0330  /  25.0330° N  /  25.0330 S
        DMS:      51°38′28″N  /  51°38'28"N  /  51 38 28 N
        DM:       51°38.5′N   /  51 38.5 N
    Comma decimals (25,0330) accepted. Direction letter (N/S/E/W) or a leading
    minus sets the sign. Returns a decimal float, or raises ValueError.
    """
    import re

    raw = text.strip().upper()
    if not raw:
        raise ValueError("Empty coordinate")

    # direction letter, if present (strip it first so it doesn't confuse parsing)
    direction = None
    if raw and raw[-1] in ("N", "S", "E", "W"):
        direction = raw[-1]
        raw = raw[:-1].strip()

    # leading sign
    negative = raw.startswith("-")

    # pull the numeric components: degrees [minutes [seconds]].
    # Accept °, ′/', ″/" and plain whitespace as separators; commas as decimals.
    norm = (raw.replace(",", ".")
               .replace("°", " ").replace("º", " ")
               .replace("′", " ").replace("’", " ").replace("'", " ")
               .replace("″", " ").replace("”", " ").replace('"', " ")
               .replace("D", " ").replace("M", " ").replace("S", " "))
    nums = re.findall(r"-?\d+(?:\.\d+)?", norm)
    if not nums:
        raise ValueError(f"Cannot parse coordinate: {text!r}")

    deg = abs(float(nums[0]))
    minutes = float(nums[1]) if len(nums) >= 2 else 0.0
    seconds = float(nums[2]) if len(nums) >= 3 else 0.0
    if not (0 <= minutes < 60) or not (0 <= seconds < 60):
        raise ValueError("Minutes and seconds must be between 0 and 60")

    value = deg + minutes / 60.0 + seconds / 3600.0

    if direction in ("S", "W") or negative:
        value = -value

    if is_lat and not (-90.0 <= value <= 90.0):
        raise ValueError("Latitude must be between -90 and 90")
    if not is_lat and not (-180.0 <= value <= 180.0):
        raise ValueError("Longitude must be between -180 and 180")
    return value


def _parse_hhmm(raw: str):
    """Return normalised 'HH:MM' or None if invalid/empty."""
    parts = raw.strip().split(":")
    if len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        except ValueError:
            pass
    return None


# --------------------------------------------------------------------------- #
#  small styled helpers
# --------------------------------------------------------------------------- #
_DIALOG_SS = f"""
QDialog, QWidget {{ background:{C['bg']}; color:{C['text']}; font-size:15px; }}
QLineEdit, QDoubleSpinBox, QDateEdit, QSpinBox {{
    background:{C['input']}; color:{C['input_txt']};
    border:1px solid {C['border']}; border-radius:4px; padding:5px 8px;
}}
QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QSpinBox:focus {{
    border:2px solid {C['accent']};
}}
QPushButton {{ background:{C['accent']}; color:#ffffff; border:none;
    border-radius:5px; padding:7px 18px; font-weight:bold; }}
QPushButton:hover {{ background:#1a5c32; }}
QPushButton#cancel {{ background:{C['panel']}; color:{C['text']};
    border:1px solid {C['border']}; }}
QPushButton#cancel:hover {{ background:#e0e0de; }}
QCheckBox {{ background:transparent; }}
"""


def _input_css():
    return (f"background:{C['input']};color:{C['input_txt']};"
            f"border:1px solid {C['border']};border-radius:4px;padding:4px 8px;")


def _lbl(text, small=False, muted=False, bold=False):
    l = QLabel(text)
    l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    col = "#777777" if muted else C["text"]
    size = 11 if small else 13
    weight = "font-weight:bold;" if bold else ""
    l.setStyleSheet(f"color:{col};font-size:{size}px;background:transparent;{weight}")
    l.setWordWrap(True)
    return l


def _divider():
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setFrameShadow(QFrame.Plain)
    f.setStyleSheet(f"background:{C['border']};max-height:1px;border:none;margin:3px 0;")
    return f


def _row(label_text, widget, suffix=""):
    h = QHBoxLayout()
    lbl = QLabel(label_text); lbl.setFixedWidth(150)
    lbl.setStyleSheet(f"color:{C['text']};font-size:15px;background:transparent;")
    h.addWidget(lbl); h.addWidget(widget)
    if suffix:
        s = QLabel(suffix); s.setWordWrap(True)   # wrap: never widen the form past the dialog
        s.setStyleSheet("color:#777777;font-size:13px;background:transparent;")
        h.addWidget(s, 1)
    h.addStretch()
    return h


# --------------------------------------------------------------------------- #
#  the create / edit dialog
# --------------------------------------------------------------------------- #
class ProfileForm(QDialog):
    def __init__(self, parent=None, existing: Profile = None):
        super().__init__(parent)
        self.setWindowTitle("New Scout Profile" if not existing else "Edit Profile")
        self.setMinimumWidth(540)
        # Fit any screen: open at a comfortable height, cap to the available
        # desktop so the form scrolls instead of overflowing. Buttons are pinned
        # outside the scroll area, so Save is always reachable.
        try:
            from PyQt5.QtWidgets import QApplication
            avail = QApplication.primaryScreen().availableGeometry().height()
        except Exception:
            avail = 900
        self.resize(600, min(760, int(avail * 0.9)))
        self.setMaximumHeight(int(avail * 0.95))
        self.setStyleSheet(_DIALOG_SS)
        self._result = None
        self._existing = existing
        self._build(existing)

    def _build(self, existing):
        # Outer dialog layout: a scrollable body + a pinned button row, so a tall
        # form never outgrows the screen and Save is ALWAYS reachable.
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        vl = QVBoxLayout(body); vl.setSpacing(10); vl.setContentsMargins(20, 16, 20, 16)

        vl.addWidget(_lbl(
            "Only what a calculation needs is stored — alias, birth date/time, "
            "coordinates, wake time — locally on your device. Nothing is transmitted.",
            small=True, muted=True))
        vl.addWidget(_divider())

        # alias
        vl.addWidget(_lbl("Profile identifier", bold=True))
        self._alias = QLineEdit(existing.alias if existing else "scout_01")
        self._alias.setPlaceholderText("e.g. scout_01")
        vl.addLayout(_row("Alias", self._alias))
        vl.addWidget(_lbl("No real name needed — any label works.", small=True, muted=True))
        vl.addWidget(_divider())

        # birth date & time
        vl.addWidget(_lbl("Birth date & time", bold=True))
        self._bdate = QDateEdit(); self._bdate.setCalendarPopup(True)
        self._bdate.setDisplayFormat("MM/dd/yyyy")
        if existing:
            try:
                bd = date.fromisoformat(existing.birth_date)
            except (ValueError, TypeError):
                bd = date(1980, 1, 1)
            self._bdate.setDate(QDate(bd.year, bd.month, bd.day))
        else:
            self._bdate.setDate(QDate(1980, 1, 1))
        vl.addLayout(_row("Birth date", self._bdate, "MM/DD/YYYY"))

        # lunar birth date — derived, read-only, updates live with the picker
        self._lunar_lbl = _lbl("", small=True, muted=True)
        vl.addWidget(self._lunar_lbl)
        self._bdate.dateChanged.connect(self._refresh_lunar)
        self._refresh_lunar()

        trow = QHBoxLayout()
        self._time_known = QCheckBox("Birth time known")
        self._time_known.setChecked(existing.birth_time_known if existing else False)
        self._btime = QLineEdit(); self._btime.setFixedWidth(100)
        self._btime.setPlaceholderText("14:30"); self._btime.setMaxLength(5)
        if existing and existing.birth_time:
            self._btime.setText(existing.birth_time)
        self._btime.setEnabled(self._time_known.isChecked())
        self._time_known.toggled.connect(self._btime.setEnabled)
        trow.addWidget(self._time_known); trow.addWidget(self._btime)
        trow.addWidget(_lbl("  24-hour  HH:MM", muted=True)); trow.addStretch()
        vl.addLayout(trow)
        vl.addWidget(_lbl("Without birth time: Moon sign, Rising sign and houses unavailable.",
                          small=True, muted=True))
        vl.addWidget(_divider())

        # birth coordinates
        vl.addWidget(_lbl("Birth location coordinates", bold=True))
        vl.addWidget(_lbl("Accepts:  25.0330° N  ·  25.0330 N  ·  25.0330  ·  -25.0330",
                          small=True, muted=True))
        self._lat = QLineEdit(); self._lat.setFixedWidth(180)
        self._lat.setPlaceholderText("0.0000  or  25.0330° N")
        if existing:
            self._lat.setText(format_coordinate(existing.latitude, is_lat=True))
        vl.addLayout(_row("Latitude", self._lat, "N = positive,  S = negative"))
        self._lon = QLineEdit(); self._lon.setFixedWidth(180)
        self._lon.setPlaceholderText("0.0000  or  121.5654° E")
        if existing:
            self._lon.setText(format_coordinate(existing.longitude, is_lat=False))
        vl.addLayout(_row("Longitude", self._lon, "E = positive,  W = negative"))
        vl.addWidget(_divider())

        # current location (optional): sets local time and season; set in Settings
        vl.addWidget(_lbl("Current location  (optional — your local time and season)", bold=True))
        if existing and existing.current_latitude is not None:
            cur = (f"{existing.current_latitude:.4f}, {existing.current_longitude:.4f}"
                   f"  · {existing.current_timezone or 'timezone not set'}")
        else:
            cur = ("Not set — the dashboard uses this computer's clock and your "
                   "birth latitude.")
        vl.addWidget(_lbl(cur))
        vl.addWidget(_lbl("To set or change it: save or close this editor, then go to "
                          "<b>Records → Settings → Set current location</b> and use "
                          "<b>Find a city…</b> or <b>Enter manually…</b>."))
        vl.addWidget(_divider())

        # UTC offset + wake time
        vl.addWidget(_lbl("Timezone & daily rhythm", bold=True))
        self._utc = QDoubleSpinBox(); self._utc.setRange(-12, 14)
        self._utc.setDecimals(2); self._utc.setSingleStep(0.25)   # quarter hours: Nepal +5.75
        self._utc.setFixedWidth(130); self._utc.setPrefix("UTC ")
        self._utc.setValue(existing.utc_offset if existing else 0.0)
        vl.addLayout(_row("Birth UTC offset", self._utc, "London summer +1.00 · Nepal +5.75"))
        vl.addWidget(_lbl("The offset where and when you were born, including daylight "
                          "saving. Setting a current location in Settings never changes it.",
                          small=True, muted=True))

        self._wake = QLineEdit(); self._wake.setFixedWidth(100)
        self._wake.setPlaceholderText("07:00"); self._wake.setMaxLength(5)
        self._wake.setText(existing.wake_time if existing else "07:00")
        vl.addLayout(_row("Wake time", self._wake, "24-hour HH:MM · drives the dashboard"))
        vl.addWidget(_divider())

        # biology — selects which cycles are relevant + scales their amplitude
        vl.addWidget(_lbl("Biology", bold=True))
        vl.addWidget(_lbl("Determines which verified cycles apply to you. Required — "
                          "the app tailors to your physiology.", small=True, muted=True))
        self._sex = QComboBox(); self._sex.setStyleSheet(_input_css())
        self._sex.addItems(["male", "female"])
        if existing and existing.sex in ("male", "female"):
            self._sex.setCurrentText(existing.sex)
        self._sex.setFixedWidth(160)
        vl.addLayout(_row("Biological sex", self._sex,
                          "drives testosterone vs menstrual cycles"))

        self._bioage = QSpinBox(); self._bioage.setRange(0, 120); self._bioage.setFixedWidth(90)
        self._bioage.setSpecialValueText("—")     # 0 shows as blank = not supplied
        self._bioage.setValue(existing.biological_age if (existing and existing.biological_age)
                              else 0)
        vl.addLayout(_row("Biological age", self._bioage,
                          "optional · only if you have real testing · refines the model"))
        vl.addWidget(_lbl("Leave blank to use age from birth date. Enter a tested "
                          "biological age only if you have it — don't guess.",
                          small=True, muted=True))
        vl.addWidget(_divider())

        # light exposure — scales melatonin + seasonal amplitude (same retinal channel)
        vl.addWidget(_lbl("Light exposure", bold=True))
        vl.addWidget(_lbl("Natural light drives your melatonin and seasonal cycles. "
                          "These let the app show the real amplitude of those cycles "
                          "for your lifestyle.", small=True, muted=True))
        self._sun = QComboBox(); self._sun.setStyleSheet(_input_css()); self._sun.setFixedWidth(200)
        self._sun.addItems(["Less than 1 hour", "1 to 3 hours", "More than 3 hours"])
        self._sun.setCurrentIndex({"<1": 0, "1-3": 1, "3+": 2}.get(
            existing.sun_hours if existing else "1-3", 1))
        vl.addLayout(_row("Direct sunlight / day", self._sun))

        self._eve = QComboBox(); self._eve.setStyleSheet(_input_css()); self._eve.setFixedWidth(200)
        self._eve.addItems(["Bright (screens, lights)", "Moderate / dimmed", "Dark (minimal light)"])
        self._eve.setCurrentIndex({"bright": 0, "moderate": 1, "dark": 2}.get(
            existing.evening_light if existing else "moderate", 1))
        vl.addLayout(_row("Light before sleep", self._eve, "the 3 hours before bed"))

        self._sleep = QComboBox(); self._sleep.setStyleSheet(_input_css()); self._sleep.setFixedWidth(200)
        self._sleep.addItems(["No — shifts / irregular", "Somewhat consistent", "Very consistent"])
        self._sleep.setCurrentIndex({"irregular": 0, "somewhat": 1, "consistent": 2}.get(
            existing.sleep_regular if existing else "somewhat", 1))
        vl.addLayout(_row("Regular sleep schedule", self._sleep))
        vl.addWidget(_divider())

        # menstrual opt-in
        vl.addWidget(_lbl("Monthly cycle tracking  (optional opt-in)", bold=True))
        self._mens = QCheckBox("Track a ~monthly hormonal cycle")
        self._mens.setChecked(existing.menstrual_tracking if existing else False)
        vl.addWidget(self._mens)
        mrow = QHBoxLayout()
        self._mstart = QLineEdit(); self._mstart.setFixedWidth(130)
        self._mstart.setPlaceholderText("YYYY-MM-DD")
        if existing and existing.menstrual_cycle_start:
            self._mstart.setText(existing.menstrual_cycle_start)
        self._mlen = QSpinBox(); self._mlen.setRange(21, 35); self._mlen.setFixedWidth(70)
        self._mlen.setValue(existing.menstrual_avg_length if existing else 28)
        mrow.addWidget(_lbl("Last start", muted=True)); mrow.addWidget(self._mstart)
        mrow.addSpacing(12)
        mrow.addWidget(_lbl("Avg length", muted=True)); mrow.addWidget(self._mlen)
        mrow.addWidget(_lbl("days", muted=True)); mrow.addStretch()
        vl.addLayout(mrow)
        self._mens.toggled.connect(self._mstart.setEnabled)
        self._mens.toggled.connect(self._mlen.setEnabled)
        self._mstart.setEnabled(self._mens.isChecked())
        self._mlen.setEnabled(self._mens.isChecked())
        vl.addWidget(_divider())

        # form body finished — mount it in the scroll area
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # buttons — pinned below the scroll area, always visible
        btnbar = QWidget()
        btnbar.setObjectName("btnbar")
        btnbar.setStyleSheet(
            f"QWidget#btnbar {{ background:{C['bg']}; "
            f"border-top:1px solid {C['border']}; }}"
            f"QPushButton {{ background:{C['accent']}; color:#ffffff; border:none; "
            f"border-radius:5px; padding:7px 18px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:#1a5c32; }}"
            f"QPushButton#cancel {{ background:{C['panel']}; color:{C['text']}; "
            f"border:1px solid {C['border']}; }}"
            f"QPushButton#cancel:hover {{ background:#e0e0de; }}")
        brow = QHBoxLayout(btnbar)
        brow.setContentsMargins(20, 12, 20, 12)
        cancel = QPushButton("Cancel"); cancel.setObjectName("cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save profile"); save.clicked.connect(self._save)
        brow.addWidget(cancel); brow.addStretch(); brow.addWidget(save)
        outer.addWidget(btnbar)

    def _refresh_lunar(self):
        """Recompute the read-only lunar birth date from the picker."""
        qd = self._bdate.date()
        lb = lunar_calendar.lunar_birth_date(date(qd.year(), qd.month(), qd.day()))
        self._lunar_lbl.setText("Lunar birth date:  " + lb.profile_line())

    def _save(self):
        editing = getattr(self, "_editing", None)   # set by ProfilePage on edit
        alias = self._alias.text().strip().replace(" ", "_")
        if not alias:
            QMessageBox.warning(self, "Alias required", "Please enter an alias.")
            return

        qd = self._bdate.date()
        bd = date(qd.year(), qd.month(), qd.day())

        bt = None
        if self._time_known.isChecked():
            bt = _parse_hhmm(self._btime.text())
            if bt is None:
                QMessageBox.warning(self, "Invalid time",
                    "Enter birth time in 24-hour format HH:MM (e.g. 14:30).")
                return

        if not self._lat.text().strip() or not self._lon.text().strip():
            QMessageBox.warning(self, "Birth location required",
                "Enter the birth latitude and longitude. Charts and the season "
                "of birth are computed from them.")
            return
        try:
            lat = parse_coordinate(self._lat.text().strip(), is_lat=True)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid latitude", str(e)); return
        try:
            lon = parse_coordinate(self._lon.text().strip(), is_lat=False)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid longitude", str(e)); return

        prior = editing or self._existing     # current location is managed in Settings

        wake = _parse_hhmm(self._wake.text()) or "07:00"

        mstart = self._mstart.text().strip() or None
        if self._mens.isChecked() and mstart:
            try:
                date.fromisoformat(mstart)
            except ValueError:
                QMessageBox.warning(self, "Invalid date",
                    "Cycle start must be YYYY-MM-DD."); return

        self._result = Profile(
            alias=alias,
            birth_date=bd.isoformat(),
            birth_time=bt,
            birth_time_known=self._time_known.isChecked(),
            latitude=lat,
            longitude=lon,
            utc_offset=self._utc.value(),
            current_latitude=prior.current_latitude if prior else None,
            current_longitude=prior.current_longitude if prior else None,
            current_timezone=prior.current_timezone if prior else None,
            wake_time=wake,
            sex=self._sex.currentText(),
            biological_age=(self._bioage.value() or None),
            sun_hours=["<1", "1-3", "3+"][self._sun.currentIndex()],
            evening_light=["bright", "moderate", "dark"][self._eve.currentIndex()],
            sleep_regular=["irregular", "somewhat", "consistent"][self._sleep.currentIndex()],
            menstrual_tracking=self._mens.isChecked(),
            menstrual_cycle_start=mstart if self._mens.isChecked() else None,
            menstrual_avg_length=self._mlen.value(),
            created=(editing.created if editing else date.today().isoformat()),
        )
        self.accept()

    def result_profile(self):
        return self._result


# --------------------------------------------------------------------------- #
#  the Records > Profile page (multi-profile manager)
# --------------------------------------------------------------------------- #
class ProfilePage(QWidget):
    def __init__(self, state, on_change=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_change = on_change or (lambda: None)
        self.setStyleSheet(f"background:{C['bg']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28); root.setSpacing(12)

        title = QLabel("Profiles"); title.setStyleSheet(
            f"font-size:24px;font-weight:bold;color:{C['text']};")
        root.addWidget(title)
        root.addWidget(_lbl("The active profile drives every calculation. "
                            "Set one active, or keep several and switch.",
                            small=True, muted=True))

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{C['input']};border:1px solid {C['border']};"
            f"border-radius:8px;padding:4px;}}"
            f"QListWidget::item{{padding:8px;}}"
            f"QListWidget::item:selected{{background:{C['accent']};color:#fff;"
            f"border-radius:5px;}}")
        self._list.itemDoubleClicked.connect(lambda _it: self._set_active())
        root.addWidget(self._list, 1)

        btns = QHBoxLayout()
        for text, slot, primary in (
            ("Set active", self._set_active, True),
            ("New…",       self._new,        False),
            ("Edit…",      self._edit,       False),
            ("Delete",     self._delete,     False),
        ):
            b = QPushButton(text); b.setCursor(Qt.PointingHandCursor)
            if not primary:
                b.setObjectName("cancel")
            b.setStyleSheet(_DIALOG_SS)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch()
        root.addLayout(btns)

        self._status = _lbl("", small=True, muted=True)
        root.addWidget(self._status)

        self._refresh()

    def _refresh(self):
        self._list.clear()
        active = self.state.active_profile.alias if self.state.active_profile else None
        for alias in self.state.profiles():
            label = f"{alias}    ● active" if alias == active else alias
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, alias)
            self._list.addItem(item)
            if alias == active:
                self._list.setCurrentItem(item)
        if not self.state.profiles():
            self._status.setText("No profiles yet — New… to create your first.")
        else:
            self._status.setText(f"{len(self.state.profiles())} profile(s). "
                                 f"Data path: ~/.local/share/cosmicscout/")

    def _selected_alias(self):
        it = self._list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _set_active(self):
        alias = self._selected_alias()
        if alias:
            self.state.set_active(alias)
            self._refresh()
            self.on_change()

    def _new(self):
        dlg = ProfileForm(self)
        if dlg.exec_():
            p = dlg.result_profile()
            self.state.save_profile(p, make_active=True)
            self._refresh()
            self.on_change()

    def _edit(self):
        alias = self._selected_alias()
        if not alias:
            return
        if self.state.active_profile and self.state.active_profile.alias == alias:
            existing = self.state.active_profile
        else:
            existing = store.load_profile(alias)
        if existing is None:
            return
        dlg = ProfileForm(self, existing=existing)
        dlg._editing = existing          # preserve created timestamp on save
        if dlg.exec_():
            p = dlg.result_profile()
            was_active = (self.state.active_profile and
                          self.state.active_profile.alias == p.alias)
            self.state.save_profile(p, make_active=was_active)
            self._refresh()
            self.on_change()

    def _delete(self):
        alias = self._selected_alias()
        if not alias:
            return
        if QMessageBox.question(
            self, "Delete profile",
            f"Delete profile '{alias}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes:
            self.state.delete_profile(alias)
            self._refresh()
            self.on_change()


def build_page(state, on_change=None):
    return ProfilePage(state, on_change=on_change)
