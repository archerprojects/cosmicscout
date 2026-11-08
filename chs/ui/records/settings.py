"""
Cosmic Scout — ui/records/settings.py  (v1.0.1 — Sunday 8 November 2026)

The Settings surface (set-once, low-traffic). Holds:

  * Current location — recents dropdown + city search over the bundled offline
    gazetteer (data/geo.py, GeoNames CC-BY). Pick a city -> confirm -> writes
    current lat/lon + IANA zone into the active profile; the current UTC offset is
    derived DST-correct via zoneinfo on use. The birth UTC offset is never changed. Selecting from recents is one tap. Manual entry is
    the rare fallback for a place not in the table, and it too saves to recents.
  * Show-on-dashboard checkbox — the location control is here by default; the
    traveller can surface it on the dashboard. Off by default (noise otherwise).
  * Space Weather opt-in — the app's ONLY network switch, OFF by default, with an
    editable NOAA endpoint set + reset. When on, the dashboard fetches NOAA SWPC
    off-thread (engines/space_weather.py); when off, nothing is fetched.
  * Units + data path (read-only).

This page itself performs no network calls; it only records the opt-in and the
endpoints.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QDialog,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt

from ui.theme import LIGHT
from data.models import SavedLocation
from data import geo
from engines.space_weather import DEFAULT_ENDPOINTS

C = LIGHT


def _lbl(t, size=15, muted=False, bold=False):
    l = QLabel(t)
    l.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    col = "#777777" if muted else C["text"]
    l.setStyleSheet(f"color:{col};font-size:{size}px;background:transparent;"
                    f"{'font-weight:bold;' if bold else ''}")
    l.setWordWrap(True)
    return l


def _divider():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setFrameShadow(QFrame.Shadow.Plain)
    f.setStyleSheet(f"background:{C['border']};max-height:1px;border:none;margin:6px 0;")
    return f


def _input_css():
    return (f"background:{C['input']};color:{C['input_txt']};"
            f"border:1px solid {C['border']};border-radius:4px;padding:5px 8px;")


def _primary_css():
    return (f"QPushButton{{background:{C['accent']};color:#fff;border:none;"
            f"border-radius:5px;padding:7px 16px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#1a5c32;}}")


def _plain_css():
    return (f"QPushButton{{background:{C['panel']};color:{C['text']};"
            f"border:1px solid {C['border']};border-radius:5px;padding:6px 14px;}}"
            f"QPushButton:hover{{border-color:{C['accent']};}}"
            f"QPushButton:disabled{{color:#aaaaaa;background:{C['bg']};border-color:#dddddd;}}")


# --------------------------------------------------------------------------- #
#  city search dialog (over the bundled offline gazetteer)
# --------------------------------------------------------------------------- #
class CitySearchDialog(QDialog):
    """Search the bundled gazetteer; optionally pre-filtered to one IANA zone."""

    def __init__(self, parent=None, filter_zone=None):
        super().__init__(parent)
        self.setWindowTitle("Find a city")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog{{background:{C['bg']};}}")
        self._picked = None

        v = QVBoxLayout(self); v.setContentsMargins(18, 16, 18, 16); v.setSpacing(8)

        if filter_zone:
            v.addWidget(_lbl(f"Cities in your detected timezone ({filter_zone}). "
                             f"Type to search all cities instead.", size=13, muted=True))
        else:
            v.addWidget(_lbl("Type a city name (population 15,000+). "
                             "Coordinates and timezone fill automatically.",
                             size=13, muted=True))

        self._search = QLineEdit(); self._search.setPlaceholderText("e.g. London")
        self._search.setStyleSheet(_input_css())
        self._search.textChanged.connect(self._on_search)
        v.addWidget(self._search)

        self._results = QListWidget()
        self._results.setStyleSheet(
            f"QListWidget{{background:{C['input']};border:1px solid {C['border']};"
            f"border-radius:6px;}}QListWidget::item{{padding:7px;}}"
            f"QListWidget::item:selected{{background:{C['accent']};color:#fff;}}")
        self._results.itemDoubleClicked.connect(lambda _i: self._accept())
        v.addWidget(self._results, 1)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(_plain_css())
        cancel.clicked.connect(self.reject)
        pick = QPushButton("Select"); pick.setStyleSheet(_primary_css())
        pick.clicked.connect(self._accept)
        row.addWidget(cancel); row.addStretch(); row.addWidget(pick)
        v.addLayout(row)

        # seed: zone cities if filtered, else empty until typed
        if filter_zone:
            self._populate(geo.in_timezone(filter_zone))

    def _on_search(self, text):
        self._populate(geo.search(text) if text.strip() else [])

    def _populate(self, cities):
        self._results.clear()
        for c in cities:
            off = geo.offset_for_timezone(c["timezone"])
            item = QListWidgetItem(
                f"{c['name']}, {c['country']}   ·   {c['timezone']}  (UTC{off:+g})")
            item.setData(Qt.ItemDataRole.UserRole, c)
            self._results.addItem(item)

    def _accept(self):
        it = self._results.currentItem()
        if not it:
            QMessageBox.information(self, "No city selected", "Pick a city from the list.")
            return
        self._picked = it.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def picked(self):
        return self._picked


# --------------------------------------------------------------------------- #
#  manual coordinate entry (fallback for places not in the table)
# --------------------------------------------------------------------------- #
class ManualLocationDialog(QDialog):
    def __init__(self, parent=None, existing: SavedLocation = None):
        super().__init__(parent)
        self.setWindowTitle("Edit location" if existing else "Enter location manually")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"QDialog{{background:{C['bg']};}}")
        self._result = None
        from ui.records.profile_dialog import parse_coordinate  # reuse the one parser
        self._parse = parse_coordinate

        v = QVBoxLayout(self); v.setContentsMargins(18, 16, 18, 16); v.setSpacing(8)
        v.addWidget(_lbl("For a place not in the city list. It will be saved to your "
                         "recents so you only enter it once.", size=13, muted=True))
        self._label = QLineEdit(); self._label.setPlaceholderText("Name (e.g. Base Camp)")
        self._label.setStyleSheet(_input_css()); v.addWidget(self._label)
        self._lat = QLineEdit(); self._lat.setPlaceholderText("Latitude  e.g. 27.9881 or 27.9881 N")
        self._lat.setStyleSheet(_input_css()); v.addWidget(self._lat)
        self._lon = QLineEdit(); self._lon.setPlaceholderText("Longitude  e.g. 86.9250 or 86.9250 E")
        self._lon.setStyleSheet(_input_css()); v.addWidget(self._lon)
        self._tz = QLineEdit(); self._tz.setPlaceholderText("IANA timezone  e.g. Asia/Kathmandu")
        self._tz.setStyleSheet(_input_css()); v.addWidget(self._tz)
        if existing is not None:
            self._label.setText(existing.label)
            self._lat.setText(str(existing.latitude))
            self._lon.setText(str(existing.longitude))
            self._tz.setText(existing.timezone)
            self._country = existing.country
        else:
            self._country = ""
        v.addWidget(_lbl("Timezone must be a valid IANA id so the UTC offset stays "
                         "DST-correct. Leave blank to use UTC.", size=13, muted=True))

        row = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(_plain_css())
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.setStyleSheet(_primary_css())
        save.clicked.connect(self._save)
        row.addWidget(cancel); row.addStretch(); row.addWidget(save)
        v.addLayout(row)

    def _save(self):
        label = self._label.text().strip()
        if not label:
            QMessageBox.warning(self, "Name required", "Give the location a name."); return
        try:
            lat = self._parse(self._lat.text().strip() or "0", is_lat=True)
            lon = self._parse(self._lon.text().strip() or "0", is_lat=False)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid coordinate", str(e)); return
        tz = self._tz.text().strip() or "UTC"
        # validate the zone by attempting to derive an offset
        if geo.ZoneInfo is not None:
            try:
                geo.ZoneInfo(tz)
            except Exception:
                QMessageBox.warning(self, "Invalid timezone",
                    f"'{tz}' is not a valid IANA timezone id."); return
        self._result = SavedLocation(label=label, latitude=lat, longitude=lon,
                                     timezone=tz, country=self._country)
        self.accept()

    def result(self):
        return self._result


# --------------------------------------------------------------------------- #
#  the Settings page
# --------------------------------------------------------------------------- #
class SettingsPage(QWidget):
    def __init__(self, state, on_change=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_change = on_change or (lambda: None)   # active profile changed
        self.setStyleSheet(f"background:{C['bg']};")

        root = QVBoxLayout(self); root.setContentsMargins(30, 22, 30, 22); root.setSpacing(8)
        root.addWidget(_lbl("Settings", size=24, bold=True))

        # ---- current location -------------------------------------------------
        root.addWidget(_lbl("Current location", size=16, bold=True))
        root.addWidget(_lbl("Where you are now. It sets the local time and the season "
                            "the dashboard and Cycles use. Separate from birth location; "
                            "when not set, the computer's clock and your birth latitude "
                            "are used.", size=13, muted=True))

        if self.state.active_profile is None:
            root.addWidget(_lbl("Activate a profile first (Records → Profile) to set its "
                                "current location.", size=14, muted=True))
        else:
            cur = self._current_str()
            self._cur_lbl = _lbl(cur, size=14)
            root.addWidget(self._cur_lbl)

            # set / change row: what sets the current location, said in words
            srow = QHBoxLayout()
            self._set_lbl = _lbl("", size=14, bold=True)
            self._set_lbl.setWordWrap(False)
            srow.addWidget(self._set_lbl)
            find = QPushButton("Find a city\u2026"); find.setStyleSheet(_primary_css())
            find.clicked.connect(lambda: self._find_city(None))
            manual = QPushButton("Enter manually\u2026"); manual.setStyleSheet(_plain_css())
            manual.clicked.connect(self._manual)
            self._cur_edit = QPushButton("Edit\u2026"); self._cur_edit.setStyleSheet(_plain_css())
            self._cur_edit.clicked.connect(self._edit_current)
            self._cur_clear = QPushButton("Clear"); self._cur_clear.setStyleSheet(_plain_css())
            self._cur_clear.clicked.connect(self._clear_current)
            for b in (find, manual, self._cur_edit, self._cur_clear):
                srow.addWidget(b)
            srow.addStretch()
            root.addLayout(srow)

            rrow = QHBoxLayout()
            rrow.addWidget(_lbl("Recents", size=14))
            self._recents = QComboBox(); self._recents.setStyleSheet(
                f"QComboBox{{{_input_css()}}} QComboBox QAbstractItemView{{"
                f"background:{C['input']};color:{C['text']};}}")
            self._recents.setMinimumWidth(240)
            rrow.addWidget(self._recents)
            self._rec_use = QPushButton("Use"); self._rec_use.setStyleSheet(_plain_css())
            self._rec_use.clicked.connect(self._use_recent)
            self._rec_edit = QPushButton("Edit\u2026"); self._rec_edit.setStyleSheet(_plain_css())
            self._rec_edit.clicked.connect(self._edit_recent)
            self._rec_remove = QPushButton("Remove"); self._rec_remove.setStyleSheet(_plain_css())
            self._rec_remove.clicked.connect(self._remove_recent)
            for b in (self._rec_use, self._rec_edit, self._rec_remove):
                rrow.addWidget(b)
            rrow.addStretch()
            root.addLayout(rrow)
            self._reload_recents()
            self._sync_current_buttons()

        # dashboard visibility
        self._dash_cb = QCheckBox("Show the location control on the dashboard")
        self._dash_cb.setChecked(self.state.location_on_dashboard())
        self._dash_cb.setStyleSheet(f"color:{C['text']};background:transparent;")
        self._dash_cb.toggled.connect(self.state.set_location_on_dashboard)
        root.addWidget(self._dash_cb)
        root.addWidget(_lbl("Off by default — useful if you travel often. Change takes "
                            "effect next time the dashboard is opened.", size=13, muted=True))

        root.addWidget(_divider())

        # ---- space weather ----------------------------------------------------
        root.addWidget(_lbl("Space weather  (the only network feature)", size=16, bold=True))
        self._sw_cb = QCheckBox("Enable space weather — contacts NOAA SWPC when on")
        self._sw_cb.setChecked(self.state.space_weather_enabled())
        self._sw_cb.setStyleSheet(f"color:{C['text']};background:transparent;")
        self._sw_cb.toggled.connect(self._toggle_sw)
        root.addWidget(self._sw_cb)
        root.addWidget(_lbl("OFF by default. When enabled the app contacts NOAA "
                            "(services.swpc.noaa.gov) for global solar data; everything "
                            "else stays fully offline. This is the one time the app "
                            "reaches the network.", size=13, muted=True))

        self._sw_status = _lbl("", size=13, muted=True)
        root.addWidget(self._sw_status)

        erow = QHBoxLayout()
        edit_ep = QPushButton("Edit NOAA endpoints…"); edit_ep.setStyleSheet(_plain_css())
        edit_ep.clicked.connect(self._edit_endpoints)
        reset_ep = QPushButton("Reset endpoints"); reset_ep.setStyleSheet(_plain_css())
        reset_ep.clicked.connect(self._reset_endpoints)
        erow.addWidget(edit_ep); erow.addWidget(reset_ep); erow.addStretch()
        root.addLayout(erow)
        self._refresh_sw_status()

        root.addWidget(_divider())

        # ---- units + data path -----------------------------------------------
        urow = QHBoxLayout()
        urow.addWidget(_lbl("Units", size=14))
        self._units = QComboBox(); self._units.addItems(["metric", "imperial"])
        self._units.setCurrentText(self.state.units())
        self._units.setStyleSheet(f"QComboBox{{{_input_css()}}}")
        self._units.currentTextChanged.connect(self.state.set_units)
        urow.addWidget(self._units); urow.addStretch()
        root.addLayout(urow)

        from data.store import DATA_DIR
        root.addWidget(_lbl(f"Data path (local, never transmitted):  {DATA_DIR}",
                            size=13, muted=True))
        root.addWidget(_lbl("City data © GeoNames, CC-BY 4.0.", size=13, muted=True))

        root.addStretch(1)

    # --- location helpers ----------------------------------------------------
    def _current_str(self):
        p = self.state.active_profile
        if p and p.current_latitude is not None:
            where = f"Now: {p.current_latitude:.4f}, {p.current_longitude:.4f}"
            if not p.current_timezone:     # no zone known: show no offset (never the birth one)
                return where + "  · timezone not set"
            off = geo.offset_for_timezone(p.current_timezone)
            return f"{where}  · {p.current_timezone} (UTC{off:+g})"
        if p:
            return "Now: using birth location (no current location set)"
        return ""

    def _reload_recents(self):
        self._recents.clear()
        for loc in self.state.saved_locations():
            off = geo.offset_for_timezone(loc.timezone)
            self._recents.addItem(f"{loc.label}  ({loc.timezone}, UTC{off:+g})", loc)
        none = self._recents.count() == 0
        if none:
            self._recents.addItem("— no saved locations yet —", None)
        for b in (self._rec_use, self._rec_edit, self._rec_remove):
            b.setVisible(not none)

    def _confirm_and_apply(self, loc: SavedLocation):
        off = geo.offset_for_timezone(loc.timezone)
        if QMessageBox.question(
            self, "Set current location",
            f"Set current location to {loc.label}?\n\n"
            f"{loc.latitude:.4f}, {loc.longitude:.4f}\n"
            f"{loc.timezone}  ·  UTC{off:+g} (today, DST-adjusted)\n\n"
            f"This updates the active profile’s current location. Your birth details, "
            f"including the UTC offset at birth, are not changed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.state.apply_location_to_active(loc)
        self._after_location_change()

    def _sync_current_buttons(self):
        p = self.state.active_profile
        has = p is not None and p.current_latitude is not None
        self._set_lbl.setText("Change:" if has else "Set current location:")
        self._cur_edit.setVisible(has); self._cur_clear.setVisible(has)

    def _after_location_change(self):
        self._cur_lbl.setText(self._current_str())
        self._sync_current_buttons()
        self._reload_recents()
        self.on_change()

    def _current_location(self):
        p = self.state.active_profile
        if p is None or p.current_latitude is None:
            return None
        for loc in self.state.saved_locations():   # reuse the saved name if known
            if (abs(loc.latitude - p.current_latitude) < 1e-4
                    and abs(loc.longitude - p.current_longitude) < 1e-4):
                return loc
        return SavedLocation(label="Current location", latitude=p.current_latitude,
                             longitude=p.current_longitude,
                             timezone=p.current_timezone or "UTC")

    def _edit_current(self):
        cur = self._current_location()
        if cur is None:
            return
        dlg = ManualLocationDialog(self, existing=cur)
        if dlg.exec() and dlg.result():
            self.state.apply_location_to_active(dlg.result())
            self._after_location_change()

    def _clear_current(self):
        if QMessageBox.question(
                self, "Clear current location",
                "Clear the current location? The dashboard will use this computer's "
                "clock and your birth latitude. Saved recents are kept.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.state.clear_current_location()
        self._after_location_change()

    def _edit_recent(self):
        loc = self._recents.currentData()
        if loc is None:
            return
        dlg = ManualLocationDialog(self, existing=loc)
        if dlg.exec() and dlg.result():
            self.state.update_saved_location(loc, dlg.result())
            self._after_location_change()

    def _remove_recent(self):
        loc = self._recents.currentData()
        if loc is None:
            return
        if QMessageBox.question(
                self, "Remove saved location",
                f"Remove {loc.label} from your recent locations? Your current "
                f"location is not changed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.state.remove_saved_location(loc.label, loc.latitude, loc.longitude)
        self._after_location_change()

    def _use_recent(self):
        loc = self._recents.currentData()
        if loc is not None:
            self._confirm_and_apply(loc)

    def _find_city(self, filter_zone):
        dlg = CitySearchDialog(self, filter_zone=filter_zone)
        if dlg.exec() and dlg.picked():
            c = dlg.picked()
            loc = SavedLocation(label=c["name"], latitude=c["lat"], longitude=c["lon"],
                                timezone=c["timezone"], country=c["country"])
            self._confirm_and_apply(loc)

    def _manual(self):
        dlg = ManualLocationDialog(self)
        if dlg.exec() and dlg.result():
            self._confirm_and_apply(dlg.result())

    # --- space weather helpers -----------------------------------------------
    def _toggle_sw(self, on):
        self.state.set_space_weather_enabled(on)
        self._refresh_sw_status()

    def _refresh_sw_status(self):
        if self.state.space_weather_enabled():
            self._sw_status.setText(
                "Enabled. The dashboard contacts NOAA SWPC (services.swpc.noaa.gov) "
                "to show current geomagnetic activity (Kp). Only NOAA is contacted, "
                "and only your request is sent \u2014 no personal data. Everything else "
                "stays offline.")
        else:
            self._sw_status.setText("Disabled. The app makes no network calls.")

    def _endpoints(self):
        return self.state.space_weather_endpoints() or dict(DEFAULT_ENDPOINTS)

    def _edit_endpoints(self):
        eps = self._endpoints()
        dlg = QDialog(self); dlg.setWindowTitle("NOAA SWPC endpoints")
        dlg.setMinimumWidth(560); dlg.setStyleSheet(f"QDialog{{background:{C['bg']};}}")
        v = QVBoxLayout(dlg); v.setContentsMargins(16, 14, 16, 14); v.setSpacing(6)
        v.addWidget(_lbl("One key=url per line. These are public NOAA JSON feeds; "
                         "edit only if NOAA reorganises them.", size=13, muted=True))
        editor = QPlainTextEdit()
        editor.setPlainText("\n".join(f"{k}={u}" for k, u in eps.items()))
        editor.setStyleSheet(_input_css())
        v.addWidget(editor)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(_plain_css())
        cancel.clicked.connect(dlg.reject)
        save = QPushButton("Save"); save.setStyleSheet(_primary_css())
        def _do():
            parsed = {}
            for line in editor.toPlainText().splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, u = line.split("=", 1)
                parsed[k.strip()] = u.strip()
            if parsed:
                self.state.set_space_weather_endpoints(parsed)
            dlg.accept()
        save.clicked.connect(_do)
        row.addWidget(cancel); row.addStretch(); row.addWidget(save)
        v.addLayout(row)
        dlg.exec()

    def _reset_endpoints(self):
        self.state.set_space_weather_endpoints(None)
        QMessageBox.information(self, "Endpoints reset",
                                "NOAA endpoints restored to defaults.")


def build_page(state, on_change=None):
    return SettingsPage(state, on_change=on_change)
