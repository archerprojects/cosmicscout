"""
Cosmic Scout — data/geo.py  (v1.1.0 — Monday 9 November 2026)

Offline city gazetteer + timezone→offset resolver. No network, ever.

Data: chs/data/cities15k.json.gz — GeoNames cities (population >= 15,000),
trimmed to [name, country_code, iana_timezone, lat, lon]. GeoNames is licensed
CC-BY 4.0; attribution is carried in README/About.

UTC offsets are NEVER stored — they are derived on demand from the city's IANA
timezone via the stdlib zoneinfo, so the offset is always DST-correct for the
date it's computed. A fixed stored offset would be wrong half the year.
"""

import gzip
import json
from pathlib import Path
from datetime import datetime
from functools import lru_cache

try:
    from zoneinfo import ZoneInfo
except ImportError:                      # pragma: no cover (3.8 fallback, unused on 3.12)
    ZoneInfo = None

_DATA = Path(__file__).with_name("cities15k.json.gz")

# record layout in the bundle
_N, _CC, _TZ, _LAT, _LON = range(5)


@lru_cache(maxsize=1)
def _cities():
    """Load the gazetteer once. Returns the raw list of [n, cc, tz, lat, lon]."""
    with gzip.open(_DATA, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def local_now(iana_tz: str = None) -> datetime:
    """Wall-clock time now (naive) in an IANA zone, e.g. the profile's current
    location; the computer's own local time when no zone is given or it fails."""
    if iana_tz and ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(iana_tz)).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.now()


def offset_for_timezone(iana_tz: str, when: datetime = None) -> float:
    """Current UTC offset in hours for an IANA zone, DST-correct. 0.0 on failure."""
    if ZoneInfo is None or not iana_tz:
        return 0.0
    try:
        dt = (when or datetime.now()).astimezone(ZoneInfo(iana_tz))
        off = dt.utcoffset()
        return round(off.total_seconds() / 3600.0, 2) if off else 0.0
    except Exception:
        return 0.0


def search(query: str, limit: int = 40):
    """Case-insensitive prefix/substring match on city name.
    Returns dicts: {name, country, timezone, lat, lon}. Population-ordered
    already in the file, so results come back most-populous-first."""
    q = query.strip().lower()
    if not q:
        return []
    out = []
    for c in _cities():
        if q in c[_N].lower():
            out.append(_as_dict(c))
            if len(out) >= limit:
                break
    return out


def in_timezone(iana_tz: str, limit: int = 60):
    """All cities in a given IANA zone (most-populous-first)."""
    out = []
    for c in _cities():
        if c[_TZ] == iana_tz:
            out.append(_as_dict(c))
            if len(out) >= limit:
                break
    return out


def _as_dict(c):
    return {"name": c[_N], "country": c[_CC], "timezone": c[_TZ],
            "lat": c[_LAT], "lon": c[_LON]}


def local_timezone_name() -> str:
    """The machine's IANA timezone (local, VPN-proof — OS-level, not network).
    Empty string if it can't be determined."""
    try:
        name = datetime.now().astimezone().tzinfo
        # tzinfo may be a ZoneInfo (has .key) or a fixed offset
        key = getattr(name, "key", None)
        if key:
            return key
    except Exception:
        pass
    # fallback: read /etc/timezone or TZ env
    import os
    tz = os.environ.get("TZ")
    if tz:
        return tz
    p = Path("/etc/timezone")
    if p.exists():
        try:
            return p.read_text().strip()
        except Exception:
            pass
    return ""
