"""
Cosmic Scout — engines/space_weather.py  (v1.1.0 — Monday 9 November 2026)

The app's ONLY network feature, off by default, behind an explicit opt-in in
Settings. Source: NOAA SWPC public JSON (keyless, no account). Endpoints are
user-editable with a reset, because NOAA reorganises these feeds — as of July
2026 the solar-wind plasma feed is mid-migration (DSCOVR retired, SOLAR-1
incoming), so it is intentionally NOT a default; users can add it themselves.

Dashboard use: the current planetary Kp index is shown, when enabled, as a
CONTESTED-badged row. Kp is a REAL measured geomagnetic index (0–9); auroras and
power-grid effects are real at high Kp, but personal-biology effects (mood,
sleep) are not established. It is context, never scored into the validated
composite.

Networking never blocks the UI: refresh() does the blocking fetch off-thread and
warms a short-lived module cache; current_state() only ever reads that cache.
"""

import json
import time
import urllib.request

DEFAULT_ENDPOINTS = {
    "kp":      "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
    "f107":    "https://services.swpc.noaa.gov/json/f107_cm_flux.json",
    "sunspot": "https://services.swpc.noaa.gov/json/sunspot_report.json",
}

_CACHE = {"data": None, "ts": 0.0}
_TTL = 600.0          # seconds a reading stays fresh (10 min)
_ERR_TTL = 120.0      # shorter cooldown after a failure


def fetch(endpoint, timeout=8):
    """Fetch and parse one NOAA SWPC JSON endpoint. Raises on network/parse error."""
    req = urllib.request.Request(endpoint, headers={"User-Agent": "CosmicScout"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _endpoints(state):
    eps = None
    try:
        eps = state.space_weather_endpoints()
    except Exception:
        eps = None
    return eps or dict(DEFAULT_ENDPOINTS)


def _kp_level(kp):
    if kp < 4:
        return "quiet"
    if kp < 5:
        return "unsettled"
    if kp < 6:
        return "minor storm (G1)"
    if kp < 7:
        return "moderate storm (G2)"
    if kp < 8:
        return "strong storm (G3)"
    if kp < 9:
        return "severe storm (G4)"
    return "extreme storm (G5)"


def refresh(state, timeout=8):
    """Blocking fetch of the current Kp index; updates the module cache.
    Call this OFF the UI thread. Returns the result dict."""
    eps = _endpoints(state)
    try:
        data = fetch(eps.get("kp", DEFAULT_ENDPOINTS["kp"]), timeout=timeout)
        latest = data[-1]            # feed is time-ascending; last entry is newest
        kp = float(latest.get("estimated_kp", latest.get("kp_index")))
        result = {"ok": True, "kp": kp, "level": _kp_level(kp),
                  "time": latest.get("time_tag", "")}
    except Exception as exc:
        result = {"ok": False,
                  "detail": "Couldn't reach NOAA SWPC (%s)." % type(exc).__name__}
    _CACHE["data"] = result
    _CACHE["ts"] = time.time()
    return result


def current_state(state):
    """Return the cached reading if still fresh, else None (caller should call
    refresh() off-thread). Returns None when disabled."""
    try:
        if state is None or not state.space_weather_enabled():
            return None
    except Exception:
        return None
    data = _CACHE["data"]
    if data is None:
        return None
    ttl = _TTL if data.get("ok") else _ERR_TTL
    if (time.time() - _CACHE["ts"]) < ttl:
        return data
    return None
