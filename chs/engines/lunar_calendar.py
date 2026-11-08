"""
Cosmic Scout — engines/lunar_calendar.py  (v1.1.0 — Monday 9 November 2026)

The lunisolar (Chinese) calendar engine. Pure compute, no Qt — so both the UI
(profile dialog, Moon & Sky page) AND any future correlation code can align on
lunar-year phase from the SAME source, with no duplication or drift.

Deliberately kept distinct from the Li Chun boundary used by the Shengxiao/BaZi
zodiac (cosmos/astro_shengxiao.py). Those two answer different questions:

    * Li Chun  = a SOLAR term (sun at ecliptic longitude 315°, ~Feb 4). Fixed by
      the sun alone; it sets the zodiac-animal year boundary.
    * Lunar birthday = a MOON-anchored date. The Chinese New Year is the new moon
      that starts the lunar year (the month numbering is anchored so lunar month
      11 contains the December solstice; New Year is normally the 2nd new moon
      after that solstice, adjusted for leap months). A person's lunar birth date
      is a (lunar month, lunar day) pair, and the Gregorian date it falls on
      SHIFTS every year.

These must never share code: one is a sun position, the other a moon phase.

Two questions this module answers:

    lunar_birth_date(greg_date)
        -> LunarBirth: the fixed traditional lunar date of a birth (month, day,
           leap flag, zodiac stem-branch). Does not change over a lifetime.

    lunar_birthday_in_year(greg_birth_date, year)
        -> date | None: the Gregorian date that lunar birth date lands on in a
           given year. This is the value that moves annually.

Range: the vendored lunardate table covers Chinese years 1900–2099. Anything
outside raises in the library; every entry point here CATCHES that and returns an
`available=False` result (or None) instead of crashing. Living users are all in
range; pre-1900 births are unsupported by design.

Leap-month / missing-day fallback (documented, not hidden):
  * If a birth fell in a LEAP month, the annual occurrence is computed in the
    ordinary month of the target year when that year has no matching leap month
    (the common convention — observe in the regular month).
  * If the birth day (e.g. a 30th) does not exist in the target year's version of
    that month (which can be 29 days), the occurrence falls back to the last day
    of that lunar month.
"""

from dataclasses import dataclass
from datetime import date

from lunardate import LunarDate


# Heavenly-Stem / Earthly-Branch for the zodiac label. Standard sexagenary
# formula anchors on Jia-Zi: stem = (year-4)%10, branch = (year-4)%12.
# Tone-marked Hanyu Pinyin (DejaVu Sans renders every diacritic — verified).
_STEMS = ["Jiǎ", "Yǐ", "Bǐng", "Dīng", "Wù", "Jǐ", "Gēng", "Xīn", "Rén", "Guǐ"]
_STEM_ELEM = {"Jiǎ": "Wood", "Yǐ": "Wood", "Bǐng": "Fire", "Dīng": "Fire",
              "Wù": "Earth", "Jǐ": "Earth", "Gēng": "Metal", "Xīn": "Metal",
              "Rén": "Water", "Guǐ": "Water"}
_BRANCHES = ["Zǐ", "Chǒu", "Yín", "Mǎo", "Chén", "Sì",
             "Wǔ", "Wèi", "Shēn", "Yǒu", "Xū", "Hài"]
_BRANCH_ANIMAL = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
                  "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
_ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th",
        8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th", 13: "13th",
        14: "14th", 15: "15th", 16: "16th", 17: "17th", 18: "18th", 19: "19th",
        20: "20th", 21: "21st", 22: "22nd", 23: "23rd", 24: "24th", 25: "25th",
        26: "26th", 27: "27th", 28: "28th", 29: "29th", 30: "30th"}

# lunardate table bounds (Chinese-calendar years).
_MIN_YEAR = 1900
_MAX_YEAR = 2099


@dataclass
class LunarBirth:
    available: bool
    year: int = 0            # lunar year (== Gregorian year of birth, effectively)
    month: int = 0           # lunar month 1..12
    day: int = 0             # lunar day 1..30
    leap: bool = False       # born in a leap month?
    animal: str = ""         # zodiac animal (Tiger, ...)
    stem: str = ""           # heavenly stem, pinyin (Rén, ...)
    branch: str = ""         # earthly branch, pinyin (Yín, ...)
    element: str = ""        # stem element (Water, ...)
    greg: object = None      # the source Gregorian birth date (datetime.date)
    note: str = ""           # for the unavailable case

    def traditional(self) -> str:
        """e.g. '18th day of the 2nd lunar month, 1962 (Water Tiger)'."""
        if not self.available:
            return self.note or "Lunar date unavailable"
        lead = "leap " if self.leap else ""
        return (f"{_ORD.get(self.day, str(self.day))} day of the {lead}"
                f"{_ORD.get(self.month, str(self.month))} lunar month, {self.year} "
                f"({self.element} {self.animal})")

    def profile_line(self) -> str:
        """Profile display: English ordinals for month/day, tone-marked pinyin
        stem-branch, English animal. No Gregorian — it equals the birth date
        shown above. e.g.
        '2nd lunar month, 18th day \u00b7 Rén Yín (Water Tiger)'."""
        if not self.available:
            return self.note or "Lunar date unavailable"
        lead = "leap " if self.leap else ""
        return (f"{_ORD.get(self.month, str(self.month))} {lead}lunar month, "
                f"{_ORD.get(self.day, str(self.day))} day \u00b7 "
                f"{self.stem} {self.branch} ({self.element} {self.animal})")


def _in_range(y: int) -> bool:
    return _MIN_YEAR <= y <= _MAX_YEAR


def lunar_birth_date(greg_date) -> LunarBirth:
    """Fixed lunar birth date from a Gregorian date. Never raises."""
    if greg_date is None:
        return LunarBirth(False, note="No birth date")
    if not _in_range(greg_date.year):
        return LunarBirth(False, note=f"Lunar date unavailable "
                          f"(outside {_MIN_YEAR}\u2013{_MAX_YEAR})")
    try:
        ld = LunarDate.from_solar_date(greg_date.year, greg_date.month,
                                       greg_date.day)
    except Exception:
        return LunarBirth(False, note="Lunar date could not be computed")

    # sexagenary stem/branch from the lunar year (Jia-Zi anchored formula)
    stem = _STEMS[(ld.year - 4) % 10]
    branch = _BRANCHES[(ld.year - 4) % 12]
    animal = _BRANCH_ANIMAL[(ld.year - 4) % 12]
    return LunarBirth(
        True, year=ld.year, month=ld.month, day=ld.day,
        leap=bool(ld.is_leap_month), animal=animal, stem=stem, branch=branch,
        element=_STEM_ELEM.get(stem, ""), greg=greg_date)


def lunar_birthday_in_year(greg_birth_date, year: int):
    """Gregorian date of a person's lunar birthday in `year`, or None.

    Handles the two edge cases documented in the module header: a leap-month
    birth observed in the ordinary month, and a day that doesn't exist in the
    target month (fall back to that month's last day).
    """
    lb = lunar_birth_date(greg_birth_date)
    if not lb.available or not _in_range(year):
        return None

    # try the exact (month, day, leap) first; then non-leap; then clamp the day.
    for leap_try in ((lb.leap,) if lb.leap else (False,)) + (False,):
        for day_try in range(lb.day, 0, -1):   # clamp down to a day that exists
            try:
                return LunarDate(year, lb.month, day_try, leap_try).to_solar_date()
            except Exception:
                continue
    return None


# --- self-tests (run: python3 -m engines.lunar_calendar) -------------------- #
if __name__ == "__main__":
    # Known case: born 1962-03-23 -> lunar M2 D18 (Water Tiger);
    # 2026 occurrence -> 2026-04-05 (Sunday).
    b = date(1962, 3, 23)
    lb = lunar_birth_date(b)
    assert lb.available and (lb.year, lb.month, lb.day) == (1962, 2, 18), lb
    assert lb.animal == "Tiger" and lb.element == "Water", (lb.element, lb.animal)
    assert lb.stem == "Rén" and lb.branch == "Yín", (lb.stem, lb.branch)
    occ = lunar_birthday_in_year(b, 2026)
    assert occ == date(2026, 4, 5), occ
    # out-of-range guard
    assert not lunar_birth_date(date(1850, 1, 1)).available
    assert lunar_birthday_in_year(b, 2200) is None
    print("lunar_calendar self-tests PASS")
    print("  born 1962-03-23 ->", lb.profile_line())
    print("  2026 lunar birthday ->", occ.strftime("%A, %B %-d, %Y"))
