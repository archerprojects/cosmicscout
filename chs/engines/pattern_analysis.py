"""
Cosmic Scout — engines/pattern_analysis.py  (v1.1.0 — Monday 9 November 2026)

Correlates the daily log against the chronobiology cycles that a daily entry can
actually resolve, and is deliberately biased toward reporting NOTHING unless a
signal is real.

WHY THESE TARGETS ONLY.  A once-a-day journal entry cannot see an intraday
rhythm — circadian and ultradian peak and trough several times between two
entries, so correlating a daily outcome against them is meaningless. The only
cycles with one stable value per day are:

    lunar         phase amplitude that day (ephemeris)
    seasonal      photoperiod position that day (date + latitude)
    weekday       day-of-week (the circaseptan question)
    menstrual     cycle phase that day (female, opt-in, if cycle-start known)

WHAT IT CORRELATES.  The five QUESTION_DOMAINS (Sleep, Cognition, Body,
Mind & Emotion, Overall), NOT the 12 individual questions. Domains cut the test
count from 12x4=48 to 5x4=20 and are more robust to single-question noise. Each
domain's daily value is the mean of its answered questions' positive scores
(negative-indicator questions already inverted upstream).

THE STATISTICS ARE THE PRODUCT.  With a few weeks of data this engine is swimming
in multiple-comparison risk, so it defends against false discovery on three
fronts and defaults to silence:

    1. Hard data gate.  Below MIN_DAYS_CORRELATION (14) usable days for a target,
       that target is not tested at all — it reports "keep logging", nothing else.
    2. False-discovery correction.  Benjamini-Hochberg across all tests actually
       run, controlling the false-discovery rate rather than per-test alpha.
       (Bonferroni at 20 tests would be so strict nothing real could surface;
       BH keeps power while holding FDR.)
    3. Effect-size floor.  A correlation must clear both the BH-significance test
       AND a minimum |r| (MIN_EFFECT) to be reported. Significant-but-tiny is
       suppressed.

Anything that fails any gate is not shown as a finding. The honest default output
is "no reliable pattern yet — keep logging."

detect_multidien (personal multi-day rhythm DISCOVERY) is the counterpart to
correlate(): instead of testing the log against KNOWN cycles, it searches the
Overall-wellbeing series for an unknown periodicity between 2 and 40 days using a
Lomb-Scargle periodogram (vendored, pure-Python Press & Rybicki form — no SciPy).

Discovery is the highest hallucination risk in the whole app: a periodogram will
ALWAYS return a "best" peak, even from pure noise. So the peak is not the finding
— surviving a bootstrap is. The observed series is shuffled BOOTSTRAP_ITERS times
(destroying any real time-ordering) and the peak power is recomputed each time;
the real peak must beat the 95th percentile of that null distribution to be
reported at all. On top of that:

    * 120-day hard floor (MIN_DAYS_MULTIDIEN): no detection is attempted below it
      (three full cycles of the longest 40-day period searched).
    * 180-day reliable line (RELIABLE_DAYS_MULTIDIEN): findings below it are
      flagged provisional.
    * 2..40 day search band (MULTIDIEN_MIN/MAX_PERIOD): deliberately excludes the
      intraday rhythms (handled on the dashboard).
    * Menstrual mask (MENSTRUAL_MASK, 21..35 days — the normal cycle range): those
      periods are removed from the search unless the profile is male, so the
      menstrual cycle (handled by correlate) is never reported as a novel rhythm.
      A male profile searches the full band: an individual male ~monthly rhythm
      is never asserted, but discovery may find one empirically.

The UI pairs every result with a maturity disclaimer (a once-per-session modal on
first view, plus a persistent inline badge) that states the dataset is not yet
mature enough to draw firm conclusions and to keep logging accurately.
"""

import math
import random
from datetime import datetime
from dataclasses import dataclass

from data.models import DAILY_QUESTIONS, QUESTION_DOMAINS

# thresholds
MIN_DAYS_CORRELATION = 14      # hard floor per target; below this, no test
RELIABLE_DAYS = 30             # results below this are flagged "provisional"
MIN_EFFECT = 0.30             # minimum |r| to report, even if significant
FDR_Q = 0.10                 # Benjamini-Hochberg false-discovery rate

# --- multidien DISCOVERY (detect_multidien) --------------------------------- #
MIN_DAYS_MULTIDIEN = 120      # hard floor: 3 cycles of the 40-day band edge
RELIABLE_DAYS_MULTIDIEN = 180 # below this, a detection is flagged provisional
MULTIDIEN_MIN_PERIOD = 2.0    # days — search band lower bound
MULTIDIEN_MAX_PERIOD = 40.0   # days — search band upper bound
MENSTRUAL_MASK = (21.0, 35.0) # days — removed from the band unless profile is male
BOOTSTRAP_ITERS = 1000        # null-distribution shuffles for the FAP gate
BOOTSTRAP_PCTILE = 95.0       # peak must beat this percentile of the null
_MULTIDIEN_FREQ_STEPS = 400   # frequency-grid resolution across the band

_NEG_KEYS = {q.key for q in DAILY_QUESTIONS if q.negative}


# --------------------------------------------------------------------------- #
#  per-day domain scores from a log
# --------------------------------------------------------------------------- #
def _answer_score(key, yes):
    """1.0 good / 0.0 adverse, negative-indicator questions inverted."""
    if key in _NEG_KEYS:
        return 0.0 if yes else 1.0
    return 1.0 if yes else 0.0


def _domain_scores(log):
    """{domain: mean positive-score of its answered questions} for one log.
    Domains with no answered question that day are omitted (not zero-filled)."""
    out = {}
    for domain, keys in QUESTION_DOMAINS.items():
        vals = [_answer_score(k, log.answers[k]) for k in keys if k in log.answers]
        if vals:
            out[domain] = sum(vals) / len(vals)
    return out


# --------------------------------------------------------------------------- #
#  per-day cycle value for each correlation target
# --------------------------------------------------------------------------- #
def _cycle_value(target, day_dt, profile):
    """Scalar value of a correlation target on a given date, or None if N/A."""
    # imported lazily to avoid a hard cycle-import at module load
    from engines import cycles
    if target == "lunar":
        return cycles.lunar_state(day_dt).amplitude
    if target == "seasonal":
        return cycles.seasonal_state(day_dt, getattr(profile, "latitude", 0.0)).amplitude
    if target == "weekday":
        return float(day_dt.weekday())            # 0=Mon .. 6=Sun (categorical-ish)
    if target == "menstrual":
        if getattr(profile, "sex", "") != "female" or not getattr(
                profile, "menstrual_tracking", False):
            return None
        if not getattr(profile, "menstrual_cycle_start", None):
            return None
        return cycles.menstrual_state(day_dt, profile).amplitude
    return None


def _targets_for(profile):
    t = ["lunar", "seasonal", "weekday"]
    if (getattr(profile, "sex", "") == "female"
            and getattr(profile, "menstrual_tracking", False)
            and getattr(profile, "menstrual_cycle_start", None)):
        t.append("menstrual")
    return t


# --------------------------------------------------------------------------- #
#  statistics
# --------------------------------------------------------------------------- #
def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _p_from_r(r, n):
    """Two-sided p-value for a Pearson r via the t-distribution, using a normal
    approximation to the t survival function (adequate for n>=14, no SciPy)."""
    if n < 3 or abs(r) >= 1.0:
        return 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    # t -> approx normal z (Fisher/large-df); good enough at our n and FDR gate
    z = abs(t) * (1 - 1.0 / (4 * df)) / math.sqrt(1 + t * t / (2 * df))
    # two-sided normal tail
    return 2 * (1 - _norm_cdf(z))


def _norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _benjamini_hochberg(pairs, q):
    """pairs: list of (key, p). Return the set of keys that pass BH at level q."""
    m = len(pairs)
    if m == 0:
        return set()
    ordered = sorted(pairs, key=lambda kp: kp[1])
    passed = set()
    thresh_rank = 0
    for i, (_key, p) in enumerate(ordered, start=1):
        if p <= (i / m) * q:
            thresh_rank = i
    for i, (key, _p) in enumerate(ordered, start=1):
        if i <= thresh_rank:
            passed.add(key)
    return passed


@dataclass
class Finding:
    domain: str
    target: str
    r: float
    p: float
    n: int
    direction: str       # "higher" / "lower"
    provisional: bool     # True if n < RELIABLE_DAYS


@dataclass
class PatternResult:
    findings: list          # [Finding] that passed every gate
    n_days: int             # usable log days
    tested: list            # [(domain, target, n)] actually tested
    gated_targets: list     # targets skipped for insufficient data
    status: str             # "insufficient" | "none" | "found"
    message: str


# --------------------------------------------------------------------------- #
#  main entry
# --------------------------------------------------------------------------- #
def correlate(logs, profile):
    """logs: iterable of DailyLog. Returns a PatternResult, biased to silence."""
    dated = []
    for log in logs:
        try:
            d = datetime.fromisoformat(log.log_date)
        except (ValueError, TypeError):
            continue
        ds = _domain_scores(log)
        if ds:
            dated.append((d, ds))
    n_days = len(dated)

    if n_days < MIN_DAYS_CORRELATION:
        need = MIN_DAYS_CORRELATION - n_days
        return PatternResult(
            [], n_days, [], [],
            "insufficient",
            f"Not enough data yet — {n_days} of {MIN_DAYS_CORRELATION} days needed "
            f"before any pattern can be trusted. Keep logging (~{need} more).")

    targets = _targets_for(profile)
    raw = []          # (domain, target, r, p, n)
    tested = []
    gated = []

    for target in targets:
        # build paired series across days where both domain and cycle value exist
        target_days = 0
        per_domain = {dom: ([], []) for dom in QUESTION_DOMAINS}
        for d, ds in dated:
            cv = _cycle_value(target, d, profile)
            if cv is None:
                continue
            target_days += 1
            for dom, score in ds.items():
                xs, ys = per_domain[dom]
                xs.append(cv)
                ys.append(score)
        if target_days < MIN_DAYS_CORRELATION:
            gated.append(target)
            continue
        for dom, (xs, ys) in per_domain.items():
            if len(xs) < MIN_DAYS_CORRELATION:
                continue
            r = _pearson(xs, ys)
            if r is None:
                continue
            p = _p_from_r(r, len(xs))
            raw.append((dom, target, r, p, len(xs)))
            tested.append((dom, target, len(xs)))

    if not raw:
        return PatternResult(
            [], n_days, tested, gated, "none",
            "Enough days logged, but no target had a full data series yet. "
            "Keep logging.")

    # Benjamini-Hochberg across everything actually tested
    keyed = [((dom, tgt), p) for (dom, tgt, r, p, n) in raw]
    passed = _benjamini_hochberg(keyed, FDR_Q)

    findings = []
    for dom, tgt, r, p, n in raw:
        if (dom, tgt) in passed and abs(r) >= MIN_EFFECT:
            findings.append(Finding(
                domain=dom, target=tgt, r=round(r, 3), p=round(p, 4), n=n,
                direction="higher" if r > 0 else "lower",
                provisional=n < RELIABLE_DAYS))

    if not findings:
        return PatternResult(
            [], n_days, tested, gated, "none",
            "No reliable pattern yet. Nothing cleared the significance and "
            "effect-size bar — which is the honest and common result at this "
            "much data. Keep logging.")

    findings.sort(key=lambda f: abs(f.r), reverse=True)
    prov = any(f.provisional for f in findings)
    msg = (f"{len(findings)} pattern(s) found"
           + (" — provisional (under 30 days; treat as a lead, not a fact)."
              if prov else "."))
    return PatternResult(findings, n_days, tested, gated, "found", msg)


def describe_finding(f):
    """Plain-language line for one finding."""
    tgt = {"lunar": "the lunar phase", "seasonal": "the season",
           "weekday": "the day of week", "menstrual": "your cycle phase"}.get(
        f.target, f.target)
    strength = ("strong" if abs(f.r) >= 0.5 else "moderate")
    return (f"{f.domain} tends to be {f.direction} with {tgt} "
            f"({strength}, r={f.r:+.2f}, n={f.n}"
            + (", provisional" if f.provisional else "") + ").")


# --------------------------------------------------------------------------- #
#  multidien discovery — Lomb-Scargle periodogram + bootstrap FAP
# --------------------------------------------------------------------------- #
def _lomb_scargle(times, values, freqs):
    """Normalized Lomb-Scargle periodogram (Press & Rybicki), pure Python.

    times, values: equal-length sequences (values need NOT be evenly spaced).
    freqs: angular-frequency-free — pass ordinary frequencies (cycles/day); the
    2*pi is applied here. Returns power at each freq, normalized by the data
    variance so peak heights are comparable across series. No SciPy/NumPy.
    """
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    if var <= 0:
        return [0.0] * len(freqs)
    out = []
    for f in freqs:
        w = 2.0 * math.pi * f
        # time offset tau that makes the sine/cosine terms orthogonal
        s2 = sum(math.sin(2 * w * t) for t in times)
        c2 = sum(math.cos(2 * w * t) for t in times)
        tau = math.atan2(s2, c2) / (2 * w) if w != 0 else 0.0
        cterm = sterm = csum = ssum = 0.0
        for t, v in zip(times, values):
            dv = v - mean
            cwt = math.cos(w * (t - tau))
            swt = math.sin(w * (t - tau))
            csum += dv * cwt
            ssum += dv * swt
            cterm += cwt * cwt
            sterm += swt * swt
        pc = (csum * csum / cterm) if cterm > 0 else 0.0
        ps = (ssum * ssum / sterm) if sterm > 0 else 0.0
        out.append(0.5 * (pc + ps) / var)
    return out


def _freq_grid(mask_menstrual=True):
    """Frequency grid (cycles/day) spanning the 2..40-day search band, minus the
    MENSTRUAL_MASK periods when mask_menstrual is set."""
    f_lo = 1.0 / MULTIDIEN_MAX_PERIOD
    f_hi = 1.0 / MULTIDIEN_MIN_PERIOD
    step = (f_hi - f_lo) / (_MULTIDIEN_FREQ_STEPS - 1)
    grid = [f_lo + i * step for i in range(_MULTIDIEN_FREQ_STEPS)]
    if mask_menstrual:
        lo, hi = MENSTRUAL_MASK
        grid = [f for f in grid if not (lo <= 1.0 / f <= hi)]
    return grid


@dataclass
class MultidienResult:
    status: str            # "insufficient" | "none" | "found"
    n_days: int
    period_days: float     # detected period (0.0 if none)
    power: float           # peak periodogram power
    threshold: float       # bootstrap 95th-percentile null power
    provisional: bool      # True if n_days < RELIABLE_DAYS_MULTIDIEN
    message: str


def _overall_series(logs):
    """(times_in_days, overall_scores) from logs that answered Overall's
    questions. times are day-offsets from the first log; gaps are preserved
    (Lomb-Scargle handles uneven sampling, which is the point)."""
    pts = []
    for log in logs:
        try:
            d = datetime.fromisoformat(log.log_date)
        except (ValueError, TypeError):
            continue
        keys = QUESTION_DOMAINS.get("Overall", [])
        vals = [_answer_score(k, log.answers[k]) for k in keys if k in log.answers]
        if vals:
            pts.append((d, sum(vals) / len(vals)))
    if not pts:
        return [], []
    pts.sort(key=lambda p: p[0])
    t0 = pts[0][0]
    times = [(d - t0).total_seconds() / 86400.0 for d, _ in pts]
    vals = [v for _, v in pts]
    return times, vals


def detect_multidien(logs, seed=None, profile=None):
    """Search the Overall-wellbeing series for an unknown 2..40-day rhythm.

    Returns a MultidienResult. Biased hard toward "none": a periodogram peak is
    only reported if it beats the 95th-percentile peak of BOOTSTRAP_ITERS
    shuffled (null) series. Below MIN_DAYS_MULTIDIEN days, nothing is attempted.
    The MENSTRUAL_MASK periods are searched only for a male profile; with no
    profile, they stay masked.
    """
    times, vals = _overall_series(logs)
    n = len(vals)

    if n < MIN_DAYS_MULTIDIEN:
        need = MIN_DAYS_MULTIDIEN - n
        return MultidienResult(
            "insufficient", n, 0.0, 0.0, 0.0, True,
            f"Rhythm discovery needs at least {MIN_DAYS_MULTIDIEN} days of "
            f"Overall entries — you have {n}. Keep logging (~{need} more) and "
            f"keep it accurate; this search is only as good as the data.")

    freqs = _freq_grid(mask_menstrual=getattr(profile, "sex", None) != "male")
    power = _lomb_scargle(times, vals, freqs)
    peak_i = max(range(len(power)), key=lambda i: power[i])
    peak_power = power[peak_i]
    peak_period = 1.0 / freqs[peak_i]

    # bootstrap null: shuffle values against the SAME sampling times, recompute
    # the max power each time. A real period survives; noise does not.
    rng = random.Random(seed)
    null_peaks = []
    shuffled = list(vals)
    for _ in range(BOOTSTRAP_ITERS):
        rng.shuffle(shuffled)
        p = _lomb_scargle(times, shuffled, freqs)
        null_peaks.append(max(p))
    null_peaks.sort()
    idx = min(len(null_peaks) - 1,
              int(math.ceil(BOOTSTRAP_PCTILE / 100.0 * len(null_peaks))) - 1)
    threshold = null_peaks[idx]

    provisional = n < RELIABLE_DAYS_MULTIDIEN
    if peak_power <= threshold:
        return MultidienResult(
            "none", n, 0.0, peak_power, threshold, provisional,
            "No multi-day rhythm stood out from noise. The strongest candidate "
            "did not beat what random shuffling of your own data produces — which "
            "is the honest, common result. Keep logging.")

    return MultidienResult(
        "found", n, round(peak_period, 1), peak_power, threshold, provisional,
        f"A candidate ~{peak_period:.1f}-day rhythm in your Overall wellbeing "
        f"cleared the noise floor"
        + (f" — provisional (under {RELIABLE_DAYS_MULTIDIEN} days; treat as a lead, not a fact)."
           if provisional else "."))
