"""
Cosmic Scout — Composite Cycle Engine
cycles.py  (v1.0.0 — Tuesday 3 November 2026)

Every value shown on the dashboard is computed here from the user's profile
(wake time, date, latitude) plus the ephemeris. No cycle is assumed from a
birth date and no value is faked. Each cycle reports:

    amplitude    current position on the cycle, -1.0 (trough) .. +1.0 (peak)
    rising       True if heading toward a peak (drives the two-tone bar headroom)
    peak_ahead   amplitude at the next peak (light segment target); == amplitude
                 when falling, so no headroom is drawn on a descending cycle
    phase_word   e.g. "RISING", "PEAK", "DIP", "TROUGH"
    timing       plain-language "when", where a time value belongs (not the bar)
    badge        evidence grade per the evidence-spine spec
    channel      one-line named mechanism (the "name the channel" test)
    detail       longer explanation surfaced when the row is tapped

Design rule enforced here: the numeric composite (TODAY'S WINDOW) blends ONLY
the two validated, channelled daily cycles — circadian and ultradian. Nothing
below the validated tier is ever summed into a score; those ride as their own
badged layers.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math

try:
    import ephem
    _HAVE_EPHEM = True
except Exception:  # pragma: no cover - ephem is a hard dep in the real app
    _HAVE_EPHEM = False


# --- evidence badges (mirror the evidence-spine spec) -----------------------
BADGE_VALIDATED   = "VALIDATED"
BADGE_EMERGING    = "EMERGING"
BADGE_CONTESTED   = "CONTESTED"
BADGE_TRADITIONAL = "TRADITIONAL"


@dataclass
class CycleState:
    key: str
    name: str
    icon: str            # single-glyph marker for the row
    amplitude: float     # current, -1..1
    rising: bool
    peak_ahead: float    # amplitude at next peak; == amplitude when falling
    phase_word: str
    timing: str
    badge: str
    hue: str             # bar colour (hex)
    channel: str
    detail: str
    sub_bars: list = None   # optional [SubBar] rendered thinner beneath a heading


@dataclass
class SubBar:
    """A named driver shown as a thinner bar under a heading cycle."""
    key: str
    name: str
    amplitude: float
    rising: bool
    peak_ahead: float
    phase_word: str
    timing: str
    hue: str
    channel: str
    badge: str
    detail: str = ""


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def _clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


def _hours_since_wake(now: datetime, wake: datetime) -> float:
    """Hours since today's wake time, wrapped into [0, 24)."""
    delta = (now - wake).total_seconds() / 3600.0
    return delta % 24.0


# --------------------------------------------------------------------------- #
#  age brackets and lifestyle light multiplier
# --------------------------------------------------------------------------- #
def age_bracket(age):
    """Directional bracket (not per-year precision). None -> 'prime' default."""
    if age is None:
        return "prime"
    if age < 30:
        return "young"
    if age < 45:
        return "prime"
    if age < 60:
        return "middle"
    return "older"


# testosterone daily-swing amplitude by bracket: steep young, flattens with age.
_T_AMP_BY_BRACKET = {"young": 1.00, "prime": 0.85, "middle": 0.62, "older": 0.40}
# melatonin amplitude also declines with age.
_MEL_AMP_BY_BRACKET = {"young": 1.00, "prime": 0.92, "middle": 0.78, "older": 0.60}
# circadian phase advances with age (older = earlier), delays in the young.
_PHASE_SHIFT_BY_BRACKET = {"young": +0.6, "prime": 0.0, "middle": -0.4, "older": -0.9}


def light_multiplier(profile) -> float:
    """0.4..1.0 scaling on melatonin + seasonal amplitude, from the three
    light-exposure answers. Same retinal light channel gates both, so this
    multiplier is applied to both the nightly melatonin bar and the seasonal bar.
    Worst-case lifestyle floors near 0.4; ideal natural-light life = 1.0."""
    sun = {"<1": 0.0, "1-3": 0.5, "3+": 1.0}.get(getattr(profile, "sun_hours", "1-3"), 0.5)
    eve = {"bright": 0.0, "moderate": 0.5, "dark": 1.0}.get(
        getattr(profile, "evening_light", "moderate"), 0.5)
    reg = {"irregular": 0.0, "somewhat": 0.5, "consistent": 1.0}.get(
        getattr(profile, "sleep_regular", "somewhat"), 0.5)
    # evening light is the strongest masker, then regularity, then daytime sun
    score = 0.30 * sun + 0.40 * eve + 0.30 * reg      # 0..1
    return round(0.4 + 0.6 * score, 3)                # 0.4..1.0


def _sex_of(profile) -> str:
    return getattr(profile, "sex", "unspecified") or "unspecified"


# --------------------------------------------------------------------------- #
#  circadian  (channel: light -> SCN -> cortisol / temperature / melatonin)
# --------------------------------------------------------------------------- #
def _driver_raw(kind: str, h: float, phase_shift: float) -> float:
    """Named circadian driver curves, wake-anchored, hours-since-wake h.
    phase_shift (hours) advances/delays the whole curve by age bracket."""
    hs = h - phase_shift
    if kind == "cortisol":
        return math.cos(2 * math.pi * (hs - 1.0) / 24.0)      # morning peak
    if kind == "temperature":
        return math.cos(2 * math.pi * (hs - 10.0) / 24.0)     # late-afternoon peak
    if kind == "melatonin":
        return math.cos(2 * math.pi * (hs - 16.0) / 24.0)     # biological-night peak
    if kind == "testosterone":
        return math.cos(2 * math.pi * (hs - 0.5) / 24.0)      # morning-high
    return 0.0


def _mk_subbar(key, name, kind, h, phase_shift, amp_scale, hue, badge, channel, detail):
    raw = _driver_raw(kind, h, phase_shift)
    ahead = _driver_raw(kind, h + 0.25, phase_shift)
    rising = ahead > raw
    amp = _clamp(raw * amp_scale)
    peak_val, _ = _sample_next_peak(
        lambda t: _driver_raw(kind, t, phase_shift), h, 24.0)
    peak_ahead = _clamp(peak_val * amp_scale) if rising else amp
    if amp > 0.6 and (not rising or (peak_ahead - amp) < 0.06):
        word = "PEAK"
    elif amp < -0.6:
        word = "TROUGH"
    else:
        word = "RISING" if rising else "FALLING"
    return SubBar(key=key, name=name, amplitude=amp, rising=rising,
                  peak_ahead=peak_ahead, phase_word=word, timing="",
                  hue=hue, channel=channel, badge=badge, detail=detail)


def circadian_drivers(now, wake, profile):
    """Named hormonal sub-bars under the Circadian heading, sex- and age-aware."""
    h = _hours_since_wake(now, wake)
    age = profile.effective_age() if hasattr(profile, "effective_age") else None
    br = age_bracket(age)
    ps = _PHASE_SHIFT_BY_BRACKET[br]
    mel_scale = _MEL_AMP_BY_BRACKET[br] * light_multiplier(profile)
    subs = [
        _mk_subbar("cortisol", "Cortisol", "cortisol", h, ps, 1.0,
                   "#e6b84a", BADGE_VALIDATED,
                   "Light \u2192 SCN \u2192 HPA axis; cortisol awakening response",
                   "Cortisol peaks ~30\u201345 min after waking, then declines; "
                   "drives the morning cognitive peak."),
        _mk_subbar("temperature", "Body temperature", "temperature", h, ps, 0.9,
                   "#d0724a", BADGE_VALIDATED,
                   "SCN-driven core body temperature rhythm",
                   "Core temperature rises through the day, peaks late afternoon, "
                   "troughs pre-dawn."),
        _mk_subbar("melatonin", "Melatonin", "melatonin", h, ps, mel_scale,
                   "#6a7fd0", BADGE_VALIDATED,
                   "Darkness \u2192 pineal melatonin (amplitude falls with age & light)",
                   "Melatonin rises ~2h before habitual sleep and marks biological "
                   "night; amplitude is reduced by age and by evening light."),
    ]
    if _sex_of(profile) == "male":
        t_scale = _T_AMP_BY_BRACKET[br]
        subs.insert(0, _mk_subbar(
            "testosterone", "Testosterone (daily)", "testosterone", h, ps, t_scale,
            "#3ecf8e", BADGE_VALIDATED,
            "HPG axis daily rhythm; morning-high, evening-low (flattens with age)",
            "Male testosterone runs highest in the early morning and declines "
            "through the day; steep when young, flatter with age. Modeled from the "
            "typical curve, not a measurement of your blood level."))
    return subs


def _circadian_raw(h: float) -> float:
    """
    Approximate wake-anchored alertness curve.
    Morning rise, post-lunch dip, afternoon recovery, biological-night trough.
    Deliberately an approximation, labelled as such in the app.
    Peak ~5h after wake (analytical morning peak, tech notes §2); low ~22h after
    wake, i.e. ~2h before habitual waking, where alertness bottoms out with the
    core-temperature minimum (Cajochen et al. 1999). The fall is slow (17h), the
    pre-wake rise quick (7h).
    """
    hm = h % 24.0
    if 5.0 <= hm < 22.0:
        phase = math.pi * (hm - 5.0) / 17.0              # peak -> low
    else:
        phase = math.pi + math.pi * ((hm - 22.0) % 24.0) / 7.0   # low -> peak
    main = math.cos(phase)
    dip = 0.40 * math.exp(-((h - 7.0) ** 2) / (2 * 1.3 ** 2))  # post-lunch dip
    return main - dip


def _sample_next_peak(fn, t0: float, span: float, step: float = 0.05):
    """Scan ahead for the next local maximum of fn; return (value, hours_ahead)."""
    prev = fn(t0)
    rising = None
    t = t0
    while t < t0 + span:
        t += step
        cur = fn(t)
        if cur > prev:
            rising = True
        elif cur < prev and rising:            # just passed a local max
            return prev, (t - step) - t0
        prev = cur
    # no clear peak in span: return the max seen
    return prev, span


def circadian_state(now: datetime, wake: datetime, profile=None) -> CycleState:
    h = _hours_since_wake(now, wake)
    amp = _clamp(_circadian_raw(h))
    ahead = _circadian_raw(h + 0.25)
    rising = ahead > _circadian_raw(h)

    peak_val, peak_in = _sample_next_peak(_circadian_raw, h, 24.0)
    peak_val = _clamp(peak_val)
    peak_ahead = peak_val if rising else amp

    headroom = peak_ahead - amp
    if rising and amp < -0.45 and (h % 24.0) < 3.0:
        word = "WAKING"            # sleep inertia: just up, still near the low
    elif rising and headroom > 0.06 and amp < 0.90:
        word = "RISING"
    elif amp > 0.60:
        word = "PEAK"
    elif amp < -0.45:
        word = "TROUGH"
    elif 5.5 <= h <= 8.5 and not rising:
        word = "DIP"
    elif rising:
        word = "RISING"
    else:
        word = "FALLING"

    if rising:
        timing = f"peak in {_fmt_in(peak_in)}"
    else:
        trough_val, trough_in = _sample_next_peak(
            lambda t: -_circadian_raw(t), h, 24.0)   # next trough = peak of negative
        timing = f"low till {_fmt_in(trough_in)}"

    detail = (
        "Your ~24h master clock, entrained by light through the retina to the "
        "suprachiasmatic nucleus, driving cortisol, core body temperature, "
        "alertness and melatonin. Analytical focus peaks late morning; a genuine "
        "post-lunch dip follows; afternoon recovery precedes the evening "
        "wind-down. The named drivers below are modeled, wake-anchored curves."
    )
    subs = circadian_drivers(now, wake, profile) if profile is not None else None
    return CycleState(
        key="circadian", name="Circadian", icon="\u2609",
        amplitude=amp, rising=rising, peak_ahead=peak_ahead,
        phase_word=word, timing=timing, badge=BADGE_VALIDATED,
        hue="#e6b84a",
        channel="Light \u2192 SCN \u2192 cortisol / temperature / melatonin",
        detail=detail, sub_bars=subs,
    )


# --------------------------------------------------------------------------- #
#  ultradian  (channel: Basic Rest-Activity Cycle, ~90 min)
# --------------------------------------------------------------------------- #
_BRAC_MIN = 90.0

def ultradian_state(now: datetime, wake: datetime) -> CycleState:
    mins = (_hours_since_wake(now, wake) * 60.0) % _BRAC_MIN
    phase = 2 * math.pi * mins / _BRAC_MIN
    amp = _clamp(math.cos(phase) * 0.85)          # slightly damped
    rising = math.sin(phase) < 0                  # cos increasing when sin<0
    # next peak of a cosine is at phase 0 / 2pi
    mins_to_peak = (_BRAC_MIN - mins) % _BRAC_MIN
    peak_ahead = 0.85 if rising else amp

    if rising and (peak_ahead - amp) > 0.06 and amp < 0.75:
        word = "RISING"
    elif amp > 0.5:
        word = "PEAK"
    elif amp < -0.5:
        word = "TROUGH"
    else:
        word = "RISING" if rising else "FALLING"
    timing = (f"crest in {int(round(mins_to_peak))} min" if rising
              else f"reset in {int(round((_BRAC_MIN/2 - mins) % _BRAC_MIN))} min")

    detail = (
        "The Basic Rest-Activity Cycle: a ~90-minute pulse of focus followed by "
        "a ~20-minute recovery trough that runs through the waking day. Discovered "
        "by Kleitman, the same rhythm that structures sleep stages. Work with the "
        "crest, rest on the trough."
    )
    return CycleState(
        key="ultradian", name="Ultradian (BRAC)", icon="\u223f",  # sine wave
        amplitude=amp, rising=rising, peak_ahead=peak_ahead,
        phase_word=word, timing=timing, badge=BADGE_VALIDATED,
        hue="#5cc98b",
        channel="~90-min rest-activity pulse (Kleitman)",
        detail=detail,
    )


# --------------------------------------------------------------------------- #
#  seasonal / circannual  (channel: photoperiod)
# --------------------------------------------------------------------------- #
def _daylight_hours(day_of_year: int, latitude: float) -> float:
    decl = math.radians(23.44) * math.sin(2 * math.pi * (day_of_year - 81) / 365.0)
    phi = math.radians(latitude)
    x = -math.tan(phi) * math.tan(decl)
    x = max(-1.0, min(1.0, x))
    H = math.acos(x)                     # half-day angle
    return 24.0 * H / math.pi


def _seasonal_testosterone_raw(doy: int, latitude: float) -> float:
    """Male seasonal testosterone: autumn-high, spring-low. Peaks ~October in the
    northern hemisphere (day ~288); phase flips across the equator. This is out of
    phase with the daylight-driven mood signal, by design — different literature."""
    hemi = 1.0 if latitude >= 0 else -1.0
    peak_doy = 288.0                                    # ~mid-October (N. hemisphere)
    return hemi * math.cos(2 * math.pi * (doy - peak_doy) / 365.0)


def seasonal_state(now: datetime, latitude: float, profile=None) -> CycleState:
    doy = now.timetuple().tm_yday
    dl = _daylight_hours(doy, latitude)
    dl_next = _daylight_hours(doy + 1, latitude)

    lengths = [_daylight_hours(d, latitude) for d in range(1, 366)]
    dmin, dmax = min(lengths), max(lengths)
    span = (dmax - dmin) or 1.0
    base_amp = 2 * (dl - dmin) / span - 1.0
    mult = light_multiplier(profile) if profile is not None else 1.0
    amp = _clamp(base_amp * mult)
    rising = dl_next > dl
    peak_ahead = _clamp(1.0 * mult) if rising else amp

    if abs(amp) > 0.9 * mult and mult > 0:
        word = "PEAK" if amp > 0 else "TROUGH"
    else:
        word = "LENGTHENING" if rising else "SHORTENING"
    target = "summer solstice" if rising else "winter solstice"
    timing = f"days {'lengthening' if rising else 'shortening'} \u00b7 toward {target}"

    detail = (
        "The yearly light cycle set by Earth's axial tilt. Longer days lift mood "
        "and energy for most people; the winter trough is the seasonal-affective "
        "window. Your amplitude is scaled by how much natural light you get \u2014 "
        "daytime sun, dark evenings and a regular schedule let the real cycle show; "
        "indoor light and irregular sleep flatten it. Computed from date and latitude."
    )

    subs = None
    if profile is not None:
        mood = SubBar(
            key="seasonal_mood", name="Mood & energy (photoperiod)",
            amplitude=amp, rising=rising, peak_ahead=peak_ahead,
            phase_word=word, timing="", hue="#e07b4a", badge=BADGE_VALIDATED,
            channel="Photoperiod \u2192 melatonin duration \u2192 mood / energy",
            detail="Daylight-driven seasonal mood and energy; lowest in deep "
                   "winter, climbing with the light.")
        subs = [mood]
        if _sex_of(profile) == "male":
            traw = _seasonal_testosterone_raw(doy, latitude)
            traw_next = _seasonal_testosterone_raw(doy + 2, latitude)
            t_amp = _clamp(traw * mult)
            t_rising = traw_next > traw
            season = ("autumn-high window" if t_amp > 0.3 else
                      "spring-low window" if t_amp < -0.3 else "mid-range")
            subs.append(SubBar(
                key="seasonal_testosterone", name="Testosterone (seasonal)",
                amplitude=t_amp, rising=t_rising,
                peak_ahead=_clamp(1.0 * mult) if t_rising else t_amp,
                phase_word="RISING" if t_rising else "FALLING", timing="",
                hue="#3ecf8e", badge=BADGE_EMERGING,
                channel="Photoperiod \u2192 melatonin/thyroid \u2192 HPG axis (autumn-high)",
                detail=("Male testosterone shows a circannual pattern \u2014 higher "
                        "in autumn, lower in spring. Real but modest and not universal; "
                        f"you are in the {season}. Out of phase with the daylight "
                        "mood signal because it tracks the photoperiod differently.")))

    return CycleState(
        key="seasonal", name="Seasonal", icon="\u2735",
        amplitude=amp, rising=rising, peak_ahead=peak_ahead,
        phase_word=word, timing=timing, badge=BADGE_VALIDATED,
        hue="#e07b4a",
        channel="Photoperiod (day length) \u2192 mood / energy",
        detail=detail, sub_bars=subs,
    )


# --------------------------------------------------------------------------- #
#  lunar  (channel: gravity -> tides is real; personal effects CONTESTED)
# --------------------------------------------------------------------------- #
def lunar_state(now: datetime) -> CycleState:
    if _HAVE_EPHEM:
        m = ephem.Moon(now)
        illum = float(m.phase)                     # 0..100 % illuminated
        later = ephem.Moon(now + timedelta(hours=6))
        waxing = float(later.phase) > illum
        nf = ephem.next_full_moon(now).datetime()
        nn = ephem.next_new_moon(now).datetime()
    else:                                          # approximation fallback
        epoch = datetime(2000, 1, 6, 18, 14)       # a known new moon
        syn = 29.53058867
        days = (now - epoch).total_seconds() / 86400.0
        age = days % syn
        illum = 50.0 * (1 - math.cos(2 * math.pi * age / syn))
        waxing = age < syn / 2
        nf = now + timedelta(days=(syn / 2 - age) % syn)
        nn = now + timedelta(days=(syn - age) % syn)

    amp = _clamp(illum / 50.0 - 1.0)               # new=-1, full=+1
    peak_ahead = 1.0 if waxing else amp

    if illum > 96:
        word = "FULL"
    elif illum < 4:
        word = "NEW"
    else:
        word = "WAXING" if waxing else "WANING"

    if waxing:
        days_to = max(0.0, (nf - now).total_seconds() / 86400.0)
        timing = f"full in {days_to:.1f} d"
    else:
        days_to = max(0.0, (nn - now).total_seconds() / 86400.0)
        timing = f"new in {days_to:.1f} d"

    detail = (
        "The Moon's gravity drives ocean tides \u2014 that channel is real and exact. "
        "Claimed effects on personal mood or sleep are weak and contested, so this "
        "row is shown for the sky, not as a driver of your day. Illumination and "
        "phase are computed from the ephemeris."
    )
    return CycleState(
        key="lunar", name="Lunar & Tides", icon="\u263d",   # moon
        amplitude=amp, rising=waxing, peak_ahead=peak_ahead,
        phase_word=word, timing=timing, badge=BADGE_CONTESTED,
        hue="#6aa5e0",
        channel="Gravity \u2192 tides (real) \u00b7 personal effects unproven",
        detail=detail,
    )


# --------------------------------------------------------------------------- #
#  menstrual  (female, opt-in; channel: HPG axis ~monthly)
# --------------------------------------------------------------------------- #
def menstrual_state(now: datetime, profile) -> CycleState:
    """~monthly hormonal cycle. Female profiles, opt-in. Age-aware: reports the
    perimenopausal / post-menopausal transition rather than a phantom cycle."""
    age = profile.effective_age() if hasattr(profile, "effective_age") else None
    length = getattr(profile, "menstrual_avg_length", 28) or 28
    start = getattr(profile, "menstrual_cycle_start", None)

    # post-menopause: no active cycle to show
    if age is not None and age >= 55:
        return CycleState(
            key="menstrual", name="Menstrual", icon="\u2640",
            amplitude=0.0, rising=False, peak_ahead=0.0,
            phase_word="POST-MENOPAUSE", timing="cycle has ended",
            badge=BADGE_VALIDATED, hue="#d06aa5",
            channel="HPG axis \u2014 cyclical phase has ended",
            detail="Past the typical menopausal transition; the monthly hormonal "
                   "cycle no longer applies. Longer-term hormonal shifts continue.",
            sub_bars=None)

    if not start:
        return CycleState(
            key="menstrual", name="Menstrual", icon="\u2640",
            amplitude=0.0, rising=False, peak_ahead=0.0,
            phase_word="NO DATA", timing="set last cycle start in profile",
            badge=BADGE_VALIDATED, hue="#d06aa5",
            channel="HPG axis \u2192 mood / energy / cognition (~monthly)",
            detail="Enter your last cycle start date in your profile to compute "
                   "the current phase.", sub_bars=None)

    try:
        start_d = datetime.fromisoformat(start)
    except ValueError:
        start_d = None
    if start_d is None:
        day_in = 0
    else:
        day_in = ((now - start_d).days % length)

    # phase amplitude: follicular rise -> ovulation peak (~mid) -> luteal fall
    frac = day_in / float(length)
    amp = _clamp(math.sin(2 * math.pi * (frac - 0.0)) )   # 0 at menses, +peak ~ovulation
    rising = math.cos(2 * math.pi * frac) > 0
    peri = age is not None and 45 <= age < 55

    if day_in <= 1:
        word = "MENSTRUAL"
    elif frac < 0.45:
        word = "FOLLICULAR"
    elif frac < 0.55:
        word = "OVULATION"
    else:
        word = "LUTEAL"
    timing = f"day {day_in + 1} of ~{length}"
    if peri:
        timing += " \u00b7 perimenopausal (cycles may be irregular)"

    detail = (
        "The ~monthly hormonal cycle of the hypothalamic-pituitary-gonadal axis, "
        "with real cyclical variation in mood, energy, cognitive style and pain "
        "sensitivity across the follicular, ovulatory and luteal phases. "
        + ("You may be in the perimenopausal transition, when cycle length and "
           "regularity shift." if peri else "")
    )
    return CycleState(
        key="menstrual", name="Menstrual", icon="\u2640",
        amplitude=amp, rising=rising, peak_ahead=1.0 if rising else amp,
        phase_word=word, timing=timing, badge=BADGE_VALIDATED,
        hue="#d06aa5",
        channel="HPG axis \u2192 mood / energy / cognition (~monthly)",
        detail=detail, sub_bars=None)


# --------------------------------------------------------------------------- #
#  composite  (validated tier only: circadian + ultradian)
# --------------------------------------------------------------------------- #
@dataclass
class Composite:
    amplitude: float
    rising: bool
    peak_ahead: float
    headline: str
    timing: str
    hue: str = "#ff6b6b"


def composite_window(circ: CycleState, ultra: CycleState) -> Composite:
    amp = _clamp(0.78 * circ.amplitude + 0.22 * ultra.amplitude)
    rising = circ.rising
    peak_ahead = _clamp(0.78 * circ.peak_ahead + 0.22 * ultra.peak_ahead) if rising else amp

    if circ.phase_word == "WAKING":
        headline = "Waking up \u2014 ease in; daylight and movement help"
    elif circ.phase_word == "DIP":
        headline = "Recovery dip \u2014 lighter tasks, short reset"
    elif circ.amplitude > 0.5 and circ.rising:
        headline = "Analytical peak \u2014 best for focused, demanding work"
    elif circ.amplitude > 0.5:
        headline = "Strong window \u2014 hold momentum on hard tasks"
    elif circ.amplitude < -0.4:
        headline = "Biological night \u2014 rest, avoid decisions"
    elif circ.rising:
        headline = "Climbing \u2014 warm into deeper work"
    else:
        headline = "Winding down \u2014 shift to routine tasks"

    return Composite(amp, rising, peak_ahead, headline, circ.timing)


# --------------------------------------------------------------------------- #
#  top-level assembly
# --------------------------------------------------------------------------- #
def day_cycles(now: datetime, wake: datetime, latitude=None, profile=None):
    """Return (composite, [rows]) for the DAY scale.

    Sex- and age-aware when a profile is supplied. Rows are the heading cycles,
    each carrying named sub-bars where relevant. Sex filtering:
      * male   -> testosterone sub-bars (daily under Circadian, seasonal under Seasonal)
      * female -> Menstrual heading (opt-in), no testosterone
    Composite (TODAY'S WINDOW) blends only the validated tier: circadian + ultradian.

    Back-compat: callers may pass latitude= positionally; if profile is given its
    latitude is used and the positional value is ignored."""
    if profile is not None:
        # where the person is now sets the season; birth latitude if not set
        cur = getattr(profile, "current_latitude", None)
        lat = cur if cur is not None else getattr(profile, "latitude", 0.0)
    else:
        lat = latitude if latitude is not None else 0.0

    circ = circadian_state(now, wake, profile)
    ultra = ultradian_state(now, wake)
    seas = seasonal_state(now, lat, profile)
    moon = lunar_state(now)
    comp = composite_window(circ, ultra)

    rows = [circ, ultra, seas]
    if profile is not None and _sex_of(profile) == "female" \
            and getattr(profile, "menstrual_tracking", False):
        rows.append(menstrual_state(now, profile))
    rows.append(moon)
    return comp, rows


def _fmt_in(hours: float) -> str:
    if hours < 1.0:
        return f"{int(round(hours * 60))} min"
    h = int(hours)
    m = int(round((hours - h) * 60))
    return f"{h}h" if m == 0 else f"{h}h {m}m"


if __name__ == "__main__":
    now = datetime.now()
    wake = now.replace(hour=7, minute=0, second=0, microsecond=0)
    comp, rows = day_cycles(now, wake, latitude=25.03)
    print("COMPOSITE:", comp.headline, "|", round(comp.amplitude, 2),
          "| rising" if comp.rising else "| falling")
    for r in rows:
        print(f"  {r.name:18s} amp={r.amplitude:+.2f} peak_ahead={r.peak_ahead:+.2f} "
              f"{r.phase_word:12s} {r.timing:22s} [{r.badge}]")
