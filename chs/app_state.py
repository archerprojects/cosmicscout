"""
Cosmic Scout — app_state.py  (v1.0.0 — Tuesday 3 November 2026)

App-wide state: the active profile, the dashboard scale, and settings
(including the space-weather network opt-in). One source of truth; the
dashboard, Records and Cosmos pages all read from here. Persistence goes
through data.store — this object never touches the disk directly except
via store calls.
"""

from typing import Optional, List

from data import store
from data.models import Profile, SavedLocation
from data import geo


class AppState:
    def __init__(self):
        self.settings: dict = store.load_settings()
        self.active_profile: Optional[Profile] = None
        self.scale: str = self.settings.get("scale", "Day")

    # --- startup ------------------------------------------------------------
    def load_last_profile(self):
        """Restore the last-used profile, else the first on disk, else None."""
        aliases = store.list_profiles()
        last = self.settings.get("last_alias")
        if last and last in aliases:
            self.active_profile = store.load_profile(last)
        elif aliases:
            self.active_profile = store.load_profile(aliases[0])
        else:
            self.active_profile = None
        return self.active_profile

    # --- profiles -----------------------------------------------------------
    def profiles(self) -> List[str]:
        return store.list_profiles()

    def set_active(self, alias: str) -> Optional[Profile]:
        p = store.load_profile(alias)
        if p is not None:
            self.active_profile = p
            self.settings["last_alias"] = alias
            store.save_settings(self.settings)
        return p

    def save_profile(self, profile: Profile, make_active: bool = True):
        store.save_profile(profile)
        if make_active or (self.active_profile and
                           self.active_profile.alias == profile.alias):
            self.active_profile = profile
            self.settings["last_alias"] = profile.alias
            store.save_settings(self.settings)

    def delete_profile(self, alias: str):
        store.delete_profile(alias)
        if self.active_profile and self.active_profile.alias == alias:
            self.settings["last_alias"] = None
            store.save_settings(self.settings)
            self.load_last_profile()

    # --- dashboard scale ------------------------------------------------------
    def set_scale(self, name: str):
        self.scale = name
        self.settings["scale"] = name
        store.save_settings(self.settings)

    # --- saved locations (app-level, shared across profiles) ------------------
    def saved_locations(self) -> List[SavedLocation]:
        return [SavedLocation.from_json(d)
                for d in self.settings.get("saved_locations", [])]

    def add_saved_location(self, loc: SavedLocation):
        """Add to recents, newest-first, de-duplicated by (label, coords)."""
        existing = [d for d in self.settings.get("saved_locations", [])
                    if not (d.get("label") == loc.label
                            and abs(d.get("latitude", 0) - loc.latitude) < 1e-4
                            and abs(d.get("longitude", 0) - loc.longitude) < 1e-4)]
        self.settings["saved_locations"] = [loc.to_json()] + existing
        store.save_settings(self.settings)

    def remove_saved_location(self, label: str, lat: float, lon: float):
        self.settings["saved_locations"] = [
            d for d in self.settings.get("saved_locations", [])
            if not (d.get("label") == label
                    and abs(d.get("latitude", 0) - lat) < 1e-4
                    and abs(d.get("longitude", 0) - lon) < 1e-4)]
        store.save_settings(self.settings)

    def update_saved_location(self, old: SavedLocation, new: SavedLocation):
        """Replace one recent (matched by label + coords) in place, keeping its
        position. If the active profile's current location is that place, it is
        updated too, so the two never disagree."""
        def same(d, loc):
            return (d.get("label") == loc.label
                    and abs(d.get("latitude", 0) - loc.latitude) < 1e-4
                    and abs(d.get("longitude", 0) - loc.longitude) < 1e-4)
        self.settings["saved_locations"] = [
            new.to_json() if same(d, old) else d
            for d in self.settings.get("saved_locations", [])]
        store.save_settings(self.settings)
        p = self.active_profile
        if (p is not None and p.current_latitude is not None
                and abs(p.current_latitude - old.latitude) < 1e-4
                and abs(p.current_longitude - old.longitude) < 1e-4
                and p.current_timezone == old.timezone):
            self.apply_location_to_active(new)

    def clear_current_location(self) -> Optional[Profile]:
        """Drop the active profile's current location; it falls back to birth."""
        if self.active_profile is None:
            return None
        p = self.active_profile
        p.current_latitude = p.current_longitude = p.current_timezone = None
        self.save_profile(p, make_active=True)
        return p

    def apply_location_to_active(self, loc: SavedLocation) -> Optional[Profile]:
        """Write a location into the active profile's current-location fields.
        Only current_* change: utc_offset is the BIRTH offset the charts use and
        is never touched here. The current offset is derived from
        current_timezone on use (DST-correct), so it is not stored."""
        if self.active_profile is None:
            return None
        p = self.active_profile
        p.current_latitude = loc.latitude
        p.current_longitude = loc.longitude
        p.current_timezone = loc.timezone
        self.save_profile(p, make_active=True)
        self.add_saved_location(loc)
        return p

    # --- dashboard visibility of the location control -------------------------
    def location_on_dashboard(self) -> bool:
        return bool(self.settings.get("location_on_dashboard", False))

    def set_location_on_dashboard(self, on: bool):
        self.settings["location_on_dashboard"] = bool(on)
        store.save_settings(self.settings)

    # --- travel detection (local, VPN-proof; OS timezone only) ----------------
    def detect_timezone_change(self):
        """Return the new IANA zone if the machine's timezone differs from what
        we last recorded, else None. Reads OS timezone only — no network, no IP.
        Records the current zone as seen so the popup fires once per change."""
        current = geo.local_timezone_name()
        if not current:
            return None
        last = self.settings.get("last_seen_timezone")
        self.settings["last_seen_timezone"] = current
        store.save_settings(self.settings)
        if last is not None and last != current:
            return current
        return None

    # --- space weather opt-in (fetch: engines/space_weather.py) ---------------
    def space_weather_enabled(self) -> bool:
        return bool(self.settings.get("space_weather_enabled", False))

    def set_space_weather_enabled(self, on: bool):
        self.settings["space_weather_enabled"] = bool(on)
        store.save_settings(self.settings)

    def space_weather_endpoints(self):
        return self.settings.get("space_weather_endpoints")

    def set_space_weather_endpoints(self, endpoints):
        self.settings["space_weather_endpoints"] = endpoints
        store.save_settings(self.settings)

    # --- Tropical wing out-links (user-editable; seeded with three defaults) --
    def tropical_sources(self) -> list:
        return list(self.settings.get("tropical_sources") or [])

    def set_tropical_sources(self, sources: list):
        self.settings["tropical_sources"] = list(sources)
        store.save_settings(self.settings)

    def reset_tropical_sources(self):
        self.settings["tropical_sources"] = list(
            store.DEFAULT_SETTINGS["tropical_sources"])
        store.save_settings(self.settings)

    # --- Twelve-Animals out-links (user-editable; seeded default) -------------
    def shengxiao_sources(self) -> list:
        return list(self.settings.get("shengxiao_sources") or [])

    def set_shengxiao_sources(self, sources: list):
        self.settings["shengxiao_sources"] = list(sources)
        store.save_settings(self.settings)

    def reset_shengxiao_sources(self):
        self.settings["shengxiao_sources"] = list(
            store.DEFAULT_SETTINGS["shengxiao_sources"])
        store.save_settings(self.settings)

    # --- BaZi out-links --------------------------------------------------------
    def bazi_sources(self) -> list:
        return list(self.settings.get("bazi_sources") or [])

    def set_bazi_sources(self, sources: list):
        self.settings["bazi_sources"] = list(sources)
        store.save_settings(self.settings)

    def reset_bazi_sources(self):
        self.settings["bazi_sources"] = list(store.DEFAULT_SETTINGS["bazi_sources"])
        store.save_settings(self.settings)

    # --- Earth-Traditions out-links -------------------------------------------
    def trad_earth_sources(self) -> list:
        return list(self.settings.get("trad_earth_sources") or [])

    def set_trad_earth_sources(self, sources: list):
        self.settings["trad_earth_sources"] = list(sources)
        store.save_settings(self.settings)

    def reset_trad_earth_sources(self):
        self.settings["trad_earth_sources"] = list(
            store.DEFAULT_SETTINGS["trad_earth_sources"])
        store.save_settings(self.settings)

    # --- Vedic/sidereal out-links ---------------------------------------------
    def sidereal_sources(self) -> list:
        return list(self.settings.get("sidereal_sources") or [])

    def set_sidereal_sources(self, sources: list):
        self.settings["sidereal_sources"] = list(sources)
        store.save_settings(self.settings)

    def reset_sidereal_sources(self):
        self.settings["sidereal_sources"] = list(
            store.DEFAULT_SETTINGS["sidereal_sources"])
        store.save_settings(self.settings)

    def units(self) -> str:
        return self.settings.get("units", "metric")

    def set_units(self, u: str):
        self.settings["units"] = u
        store.save_settings(self.settings)
