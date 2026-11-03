"""
Cosmic Scout — data/store.py  (v1.0.0 — Tuesday 3 November 2026)

Local JSON persistence under ~/.local/share/cosmicscout/. Zero network.
The single write path for all app data: profiles, daily logs, settings.
Layout (ported from the proven v1 scheme):

    ~/.local/share/cosmicscout/
        profiles/<alias>.json      one file per profile
        journal/<alias>/<date>.json  one file per daily log entry
        settings.json              last_alias, scale, space-weather opt-in, units

Models stay pure (data/models.py); every disk touch goes through here.
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from data.models import Profile, DailyLog

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME",
                               str(Path.home() / ".local" / "share"))) / "cosmicscout"
PROFILES_DIR = DATA_DIR / "profiles"
JOURNAL_DIR = DATA_DIR / "journal"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "last_alias": None,
    "scale": "Day",                     # dashboard scale, persisted
    "space_weather_enabled": False,     # the app's ONLY network switch
    "space_weather_endpoints": None,    # None -> engine defaults
    "units": "metric",
    "saved_locations": [],              # list of SavedLocation dicts (recents, newest-first)
    "location_on_dashboard": False,     # show the location control on the dashboard
    "last_seen_timezone": None,         # for detecting travel between sessions
    "tropical_sources": [               # Tropical wing out-links (user-editable)
        {"name": "Cainer", "url": "https://www.cainer.com/daily-horoscope/"},
        {"name": "Free Will Astrology \u2014 Rob Brezsny", "url": "https://freewillastrology.com/"},
        {"name": "Astrology Zone \u2014 Susan Miller", "url": "https://www.astrologyzone.com/"},
    ],
    "shengxiao_sources": [              # Twelve-Animals out-links (user-editable)
        {"name": "China Highlights \u2014 Chinese Zodiac",
         "url": "https://www.chinahighlights.com/travelguide/chinese-zodiac/"},
    ],
    "bazi_sources": [                  # BaZi Four-Pillars out-links (user-editable)
        {"name": "Your Chinese Astrology \u2014 BaZi",
         "url": "https://www.yourchineseastrology.com/calendar/bazi/"},
    ],
    "trad_earth_sources": [            # Earth-Traditions out-links (user-editable)
        {"name": "Sun Bear Medicine Wheel \u2014 guide",
         "url": "https://www.crystalvaults.com/medicine-wheel-guide/"},
    ],
    "sidereal_sources": [              # Vedic/sidereal out-links (user-editable)
        {"name": "Drik Panchang \u2014 Janma Nakshatra",
         "url": "https://www.drikpanchang.com/utilities/horoscope/hindu-birthstar-calculator.html"},
    ],
}


def ensure_dirs():
    for d in (PROFILES_DIR, JOURNAL_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


# --- profiles ---------------------------------------------------------------
def list_profiles() -> List[str]:
    ensure_dirs()
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def load_profile(alias: str) -> Optional[Profile]:
    path = PROFILES_DIR / f"{alias}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return Profile.from_json(json.load(f))
    except Exception:
        return None


def save_profile(profile: Profile) -> Path:
    ensure_dirs()
    path = PROFILES_DIR / f"{profile.alias}.json"
    with open(path, "w") as f:
        json.dump(profile.to_json(), f, indent=2)
    return path


def delete_profile(alias: str) -> bool:
    path = PROFILES_DIR / f"{alias}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# --- daily logs --------------------------------------------------------------
def list_log_dates(alias: str) -> List[str]:
    d = JOURNAL_DIR / alias
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def load_log(alias: str, log_date: str) -> Optional[DailyLog]:
    path = JOURNAL_DIR / alias / f"{log_date}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return DailyLog.from_json(json.load(f))
    except Exception:
        return None


def save_log(alias: str, log: DailyLog) -> Path:
    ensure_dirs()
    d = JOURNAL_DIR / alias
    d.mkdir(exist_ok=True)
    path = d / f"{log.log_date}.json"
    with open(path, "w") as f:
        json.dump(log.to_json(), f, indent=2)
    return path


# --- settings ----------------------------------------------------------------
def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                s.update(json.load(f))
        except Exception:
            pass                        # corrupt settings -> defaults, never crash
    return s


def save_settings(settings: dict):
    ensure_dirs()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
