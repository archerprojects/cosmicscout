"""
Cosmic Scout — app_state.py  (v1.1.0 — Monday 9 November 2026)

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
from cosmos import links as cosmos_links


class AppState:
    def __init__(self):
        self.settings: dict = store.load_settings()
        self.active_profile: Optional[Profile] = None
        self.scale: str = self.settings.get("scale", "Day")
        self._migrate_shared_links()

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

    # --- Cosmos Further Reading links (per profile) ----------------------------
    # A tab the profile has never edited follows the shipped defaults
    # (cosmos/links.py); check results are kept per URL, apart from the lists,
    # so checking never freezes a tab's defaults.
    def links_editable(self) -> bool:
        return self.active_profile is not None

    def links(self, key: str) -> list:
        p = self.active_profile
        if p is not None and key in p.cosmos_links:
            return [dict(x) for x in p.cosmos_links[key]]
        return cosmos_links.defaults(key)

    def links_customised(self, key: str) -> bool:
        p = self.active_profile
        return p is not None and key in p.cosmos_links

    def set_links(self, key: str, items: list):
        p = self.active_profile
        if p is None:
            return
        p.cosmos_links[key] = [{"name": x["name"], "url": x["url"]} for x in items]
        store.save_profile(p)

    def reset_links(self, key: str):
        p = self.active_profile
        if p is None:
            return
        p.cosmos_links.pop(key, None)
        store.save_profile(p)

    def link_check(self, url: str) -> dict:
        p = self.active_profile
        return dict(p.cosmos_link_checks.get(url, {})) if p is not None else {}

    def record_link_checks(self, results: dict):
        """results: url -> status, from cosmos.links.LinkChecker."""
        p = self.active_profile
        if p is None:
            return
        day = cosmos_links.today()
        for url, status in results.items():
            p.cosmos_link_checks[url] = {"status": status, "checked": day}
        store.save_profile(p)

    def _migrate_shared_links(self):
        """1.0.x kept one shared list per tab in settings (<tab>_sources). Copy any
        list that differs from the shipped default into every profile that has no
        entry for that tab, then drop the shared keys. Runs once; a no-op after."""
        keys = [k for k in list(self.settings) if k.endswith("_sources")]
        if not keys:
            return
        aliases = store.list_profiles()
        for skey in keys:
            tab = skey[:-len("_sources")]
            items = [{"name": x.get("name", ""), "url": x.get("url", "")}
                     for x in (self.settings.get(skey) or [])]
            if items and items != cosmos_links.defaults(tab):
                for alias in aliases:
                    prof = store.load_profile(alias)
                    if prof is not None and tab not in prof.cosmos_links:
                        prof.cosmos_links[tab] = items
                        store.save_profile(prof)
            self.settings.pop(skey, None)
        store.save_settings(self.settings)

    def units(self) -> str:
        return self.settings.get("units", "metric")

    def set_units(self, u: str):
        self.settings["units"] = u
        store.save_settings(self.settings)
