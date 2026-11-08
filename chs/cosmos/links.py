"""
Cosmic Scout — cosmos/links.py  (v1.1.0 — Monday 9 November 2026)

Cosmos "Further Reading" out-links: the shipped defaults for each tab, URL
validation, and the user-started link check.

Links are stored per profile (Profile.cosmos_links, keyed by tab). A tab the
user has never edited has no entry and follows the defaults shipped here, so a
release can improve them. Each stored link is {"name", "url"} plus, once
checked, {"status", "checked"}.

Network: the check runs only when the user presses Check links, and contacts
only the sites listed on that tab: one request per site, no user data, a
generic client name. Nothing here runs on its own.
"""

import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from PyQt6.QtCore import QThread, pyqtSignal

# tab key -> shipped default links
DEFAULT_LINKS = {
    "moon_sky": [
        {"name": "NASA — Moon", "url": "https://moon.nasa.gov/"},
        {"name": "US Naval Observatory — Moon phases",
         "url": "https://aa.usno.navy.mil/data/MoonPhases"},
    ],
    "tropical": [
        {"name": "Cainer", "url": "https://www.cainer.com/daily-horoscope/"},
        {"name": "Free Will Astrology — Rob Brezsny", "url": "https://freewillastrology.com/"},
        {"name": "Astrology Zone — Susan Miller", "url": "https://www.astrologyzone.com/"},
    ],
    "shengxiao": [
        {"name": "China Highlights — Chinese Zodiac",
         "url": "https://www.chinahighlights.com/travelguide/chinese-zodiac/"},
    ],
    "bazi": [
        {"name": "Your Chinese Astrology — BaZi",
         "url": "https://www.yourchineseastrology.com/calendar/bazi/"},
    ],
    "trad_earth": [
        {"name": "Sun Bear Medicine Wheel — guide",
         "url": "https://www.crystalvaults.com/medicine-wheel-guide/"},
    ],
    "sidereal": [
        {"name": "Drik Panchang — Janma Nakshatra",
         "url": "https://www.drikpanchang.com/utilities/horoscope/hindu-birthstar-calculator.html"},
    ],
}

TAB_TITLES = {
    "moon_sky": "Moon & Sky",
    "tropical": "Tropical Zodiac",
    "shengxiao": "Twelve Animals",
    "bazi": "BaZi Four Pillars",
    "trad_earth": "Earth Traditions",
    "sidereal": "Vedic (Sidereal)",
}

# check status -> (dot colour, tooltip)
STATUS_OK = "ok"
STATUS_REFUSED = "refused"
STATUS_FAILED = "failed"
STATUS_DOTS = {
    STATUS_OK:      ("#2e7d52", "Confirmed: the site answered"),
    STATUS_REFUSED: ("#c87820", "The site refused the automated check — open it to confirm"),
    STATUS_FAILED:  ("#8b2020", "No answer: not found, server error, timeout or no such site"),
    None:           ("#c0c0bc", "Not checked yet"),
}

_USER_AGENT = "CosmicScout link check"
_REFUSED_CODES = (401, 403, 429)


def defaults(key):
    return [dict(x) for x in DEFAULT_LINKS.get(key, [])]


def valid_url(url):
    """True for an http(s) address with a host; nothing else is ever opened."""
    try:
        u = urllib.parse.urlparse(url.strip())
    except ValueError:
        return False
    return u.scheme in ("http", "https") and bool(u.netloc) and " " not in url.strip()


def classify(code):
    """HTTP status code -> link status."""
    if 200 <= code < 400:
        return STATUS_OK
    if code in _REFUSED_CODES:
        return STATUS_REFUSED
    return STATUS_FAILED


def check_url(url, timeout=8):
    """One request to `url` (HEAD, then GET if HEAD is not allowed) -> status."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method,
                                     headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return classify(resp.status)
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (405, 501):
                continue                       # server refuses HEAD: try GET once
            return classify(e.code)
        except Exception:
            return STATUS_FAILED
    return STATUS_FAILED


class LinkChecker(QThread):
    """Checks a list of URLs off the UI thread; emits {url: status} when done."""
    done = pyqtSignal(dict)

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self._urls = list(dict.fromkeys(urls))      # unique, order kept

    def run(self):
        self.done.emit({u: check_url(u) for u in self._urls})


def today():
    return date.today().isoformat()
