"""
Cosmic Scout — data/models.py  (v1.0.1 — Sunday 8 November 2026)

Local data structures. Privacy rule (unchanged): store only what a calculation
needs, nothing else. No full name, city, email, device id, or analytics.

New in v1.2 vs the reconstructed v1:
  * Profile.wake_time      -> persists chronobiology wake time between sessions
  * Profile.menstrual_*    -> opt-in tracking for the real ~monthly hormonal cycle
Biorhythm is gone; nothing here references it.
"""

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional, Dict, List


@dataclass
class Profile:
    alias: str
    birth_date: str                       # ISO yyyy-mm-dd
    birth_time: Optional[str] = None       # HH:MM, optional
    birth_time_known: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    utc_offset: float = 0.0
    # current location (separate from birth location; sets local time and season)
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_timezone: Optional[str] = None    # IANA zone; UTC offset derived via zoneinfo
    # chronobiology
    wake_time: str = "07:00"               # HH:MM  (persisted; drives the dashboard)
    # biology that selects which cycles are relevant and scales their amplitude
    sex: str = "unspecified"               # "male" | "female" | "unspecified"
    biological_age: Optional[int] = None   # optional; refines chronological age when supplied
    # light-exposure lifestyle (scales melatonin + seasonal amplitude — same retinal channel)
    sun_hours: str = "1-3"                 # "<1" | "1-3" | "3+"  direct daylight per day
    evening_light: str = "moderate"        # "bright" | "moderate" | "dark"  (3h pre-sleep)
    sleep_regular: str = "somewhat"        # "irregular" | "somewhat" | "consistent"
    # opt-in real ~monthly cycle
    menstrual_tracking: bool = False
    menstrual_cycle_start: Optional[str] = None   # ISO date of last cycle start
    menstrual_avg_length: int = 28
    created: str = field(default_factory=lambda: date.today().isoformat())

    def wake_hm(self):
        h, m = self.wake_time.split(":")
        return int(h), int(m)

    def chrono_age(self, on: date = None) -> Optional[int]:
        """Chronological age from birth_date, exact. None if birth_date unparseable."""
        try:
            bd = date.fromisoformat(self.birth_date)
        except (ValueError, TypeError):
            return None
        d = on or date.today()
        return d.year - bd.year - ((d.month, d.day) < (bd.month, bd.day))

    def effective_age(self, on: date = None) -> Optional[int]:
        """Biological age if the user supplied one (real testing), else chronological.
        This is what the cycle engine's age modifiers read."""
        if self.biological_age is not None:
            return self.biological_age
        return self.chrono_age(on)

    def to_json(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: Dict) -> "Profile":
        known = {f: d[f] for f in cls.__dataclass_fields__ if f in d}
        return cls(**known)


@dataclass
class SavedLocation:
    """A named current-location the user has visited. App-level (shared across
    profiles). Coordinates come from the bundled gazetteer or manual entry; the
    UTC offset is NOT stored — it's derived from `timezone` (IANA) on use."""
    label: str                             # display name, e.g. "London"
    latitude: float
    longitude: float
    timezone: str                          # IANA zone id, e.g. "Europe/London"
    country: str = ""

    def to_json(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: Dict) -> "SavedLocation":
        known = {f: d[f] for f in cls.__dataclass_fields__ if f in d}
        return cls(**known)


@dataclass
class DailyLog:
    log_date: str                          # ISO yyyy-mm-dd
    answers: Dict[str, bool] = field(default_factory=dict)   # qNN -> yes/no
    note: str = ""

    def to_json(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: Dict) -> "DailyLog":
        return cls(**{f: d[f] for f in cls.__dataclass_fields__ if f in d})

    def positive_score(self) -> float:
        """0.0–1.0 overall positive-day score; negative indicators count inversely.
        (Carried from v1 — pattern_analysis consumes this.)"""
        if not self.answers:
            return 0.5
        total, score = 0, 0
        for q in DAILY_QUESTIONS:
            if q.key in self.answers:
                total += 1
                yes = self.answers[q.key]
                score += (0 if yes else 1) if q.negative else (1 if yes else 0)
        return score / total if total > 0 else 0.5


# canonical 12 questions; NEG = "yes" is the adverse answer
@dataclass
class Question:
    key: str
    text: str
    negative: bool = False


DAILY_QUESTIONS: List[Question] = [
    Question("q01", "Did you wake feeling rested?"),
    Question("q02", "Was your morning focus sharp?"),
    Question("q03", "Did you hit an afternoon energy dip?", negative=True),
    Question("q04", "Did you feel physically strong today?"),
    Question("q05", "Was your mood stable through the day?"),
    Question("q06", "Did creative or intuitive thinking flow easily?"),
    Question("q07", "Did you feel socially connected or open?"),
    Question("q08", "Was your digestion and appetite normal?"),
    Question("q09", "Was today an overall high-energy day?"),
    Question("q10", "Did you feel unusually high stress today?", negative=True),
    Question("q11", "Did you feel motivated and goal-directed today?"),
    Question("q12", "Did you notice heightened physical sensitivity today?", negative=True),
]


# question -> domain grouping (carried from v1 — pattern_analysis consumes this)
QUESTION_DOMAINS: Dict[str, List[str]] = {
    "Sleep":          ["q01"],
    "Cognition":      ["q02", "q06"],
    "Body":           ["q03", "q04", "q08", "q12"],
    "Mind & Emotion": ["q05", "q07", "q11"],
    "Overall":        ["q09", "q10"],
}
