"""
Cosmic Scout — cosmos/astro_bazi.py  (v1.1.0 — Monday 9 November 2026)

BaZi (八字) — the Four Pillars of Destiny. The peer of Shengxiao: same lived
tradition, carried on its own terms and TRADITIONAL-badged. Pure date/time
arithmetic (ephem only for solar terms and Li Chun), no new dependency.

Four pillars, each a Heavenly Stem + Earthly Branch:
  * Year  — sexagenary year on the Li Chun boundary (shared with Shengxiao).
  * Month — set by the true solar term (jie): the sun's apparent ecliptic
            longitude at the birth instant, in 30-degree segments from 315 (Li Chun).
            Month stem follows the Five-Tigers rule from the year stem.
  * Day   — day pillar from a verified anchor: 1900-01-01 = Jia-Xu. Advances 1/day.
  * Hour  — shichen (two-hour block) from the birth hour; stem by the Five-Rats
            rule from the day stem. Late-Zi (23:00-24:00) takes the next day's
            stem, matching professional practice.

Also: Day Master (day stem) and its element, a visible-element tally, a simplified
strength indicator (transparent weighted count — NOT a full hidden-stem analysis),
the current shichen, and the ten-year Luck Pillars (da yun) with direction and an
approximate start age (the three-days-to-a-year rule).

All pillar formulas were verified against the sxtwl reference calendar across
hundreds of dates: year, day and hour match exactly; month matches except within
the same day as a solar-term change, where independent ephemerides differ by
minutes. That boundary caveat is surfaced on the page.
"""

from datetime import date, datetime, timedelta

from cosmos.astro_shengxiao import BRANCHES, solar_year, is_li_chun_day   # (pinyin, animal, fixed_el), Li Chun year
from cosmos._links_section import build_links_card

_LINKS_NOTE = "Opens in your browser \u2014 yours to change, replace, or add to."

STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]
_EL_IDX = {e: i for i, e in enumerate(ELEMENTS)}

_ORD_1900 = date(1900, 1, 1).toordinal()     # verified: 1900-01-01 = Jia(0)-Xu(10)


def _stem_el(stem_idx):
    return stem_idx // 2                       # Jia/Yi=Wood, Bing/Ding=Fire, ...


def _branch_el(branch_idx):
    return _EL_IDX[BRANCHES[branch_idx][2]]


def _sun_longitude(dt_utc):
    import math
    import ephem
    d = ephem.Date(dt_utc)
    # ecliptic of date (epoch=d); pyephem's default J2000 frame drifts ~1 day per century
    return math.degrees(ephem.Ecliptic(ephem.Sun(d), epoch=d).lon) % 360.0


def _sexagenary_index(stem, branch):
    for k in range(60):
        if k % 10 == stem and k % 12 == branch:
            return k
    return 0


def _term_crossing(birth_utc, target_lon, forward):
    """Datetime the sun's apparent longitude reaches target_lon, searching up to
    ~40 days forward or backward from birth. Linear-interpolated to minute scale."""
    step = timedelta(hours=6)
    def diff(dt):
        return ((_sun_longitude(dt) - target_lon + 180) % 360) - 180
    t = birth_utc
    prev = diff(t)
    for _ in range(4 * 40):
        t2 = t + step if forward else t - step
        cur = diff(t2)
        if prev == 0 or (prev < 0) != (cur < 0):
            lo, hi = (t, t2) if forward else (t2, t)
            for _ in range(40):
                mid = lo + (hi - lo) / 2
                if (diff(lo) < 0) != (diff(mid) < 0):
                    hi = mid
                else:
                    lo = mid
            return lo + (hi - lo) / 2
        t, prev = t2, cur
    return None


def four_pillars(profile):
    """Full BaZi record from a Profile, or None if the birth date is unusable."""
    try:
        d = date.fromisoformat(profile.birth_date)
    except (ValueError, TypeError):
        return None

    time_known = bool(profile.birth_time_known and profile.birth_time)
    if time_known:
        hh, mm = (int(x) for x in profile.birth_time.split(":"))
    else:
        hh, mm = 12, 0
    utc_off = float(profile.utc_offset or 0.0)
    birth_utc = datetime(d.year, d.month, d.day, hh, mm) - timedelta(hours=utc_off)

    # YEAR (Li Chun) — the exact birth instant against the exact Li Chun instant
    sy = solar_year(d, "%02d:%02d" % (hh, mm), utc_off)
    ys, yb = (sy - 4) % 10, (sy - 4) % 12

    # DAY (anchor 1900-01-01 = Jia-Xu)
    n = d.toordinal() - _ORD_1900
    ds, db = n % 10, (n + 10) % 12

    # MONTH (true solar term)
    lon = _sun_longitude(birth_utc)
    seg = int(((lon - 315) % 360) // 30)       # 0 = Yin/Tiger month
    month_no = seg + 1
    mb = (2 + seg) % 12
    ms = ([2, 4, 6, 8, 0][ys % 5] + (month_no - 1)) % 10

    # HOUR (Five Rats; late-Zi rolls to next day's stem)
    hour = None
    if time_known:
        sh = ((hh + 1) // 2) % 12
        ds_for_hour = (n + 1) % 10 if hh == 23 else ds
        hs = ([0, 2, 4, 6, 8][ds_for_hour % 5] + sh) % 10
        hour = {"stem": hs, "branch": sh}

    pillars = {
        "year": {"stem": ys, "branch": yb},
        "month": {"stem": ms, "branch": mb},
        "day": {"stem": ds, "branch": db},
        "hour": hour,
    }

    dm_el = _stem_el(ds)     # Day Master element

    # element tally over every visible character
    tally = [0, 0, 0, 0, 0]
    chars = [(_stem_el(ys), 1), (_branch_el(yb), 1),
             (_stem_el(ms), 1), (_branch_el(mb), 2),   # month branch = seasonal weight
             (_stem_el(ds), 1), (_branch_el(db), 1)]
    for el, _w in chars:
        tally[el] += 1
    if hour:
        tally[_stem_el(hs)] += 1
        tally[_branch_el(sh)] += 1

    # simplified strength: support (same + resource) vs drain/control, month weighted
    support = {dm_el, (dm_el - 1) % 5}
    weaken = {(dm_el + 1) % 5, (dm_el + 2) % 5, (dm_el - 2) % 5}
    score = 0
    strength_chars = [(_branch_el(yb), 1), (_stem_el(ys), 1),
                      (_branch_el(mb), 2), (_stem_el(ms), 1), (_branch_el(db), 1)]
    if hour:
        strength_chars += [(_stem_el(hs), 1), (_branch_el(sh), 1)]
    for el, w in strength_chars:
        if el in support:
            score += w
        elif el in weaken:
            score -= w
    strength = "Strong" if score >= 3 else ("Weak" if score <= -3 else "Balanced")

    # current shichen (bug fix: uses the current HOUR, not a date field)
    from data import geo
    now_h = geo.local_now(getattr(profile, "current_timezone", None)).hour
    now_sh = ((now_h + 1) // 2) % 12

    # Luck Pillars (da yun)
    luck = _luck_pillars(profile, ys, ms, mb, birth_utc, seg)

    return {
        "time_known": time_known,
        "li_chun_unsure": (not time_known) and is_li_chun_day(d, utc_off),
        "pillars": pillars,
        "day_master": {"stem": ds, "element": ELEMENTS[dm_el]},
        "tally": tally,
        "strength": strength,
        "strength_score": score,
        "current_shichen": {"branch": now_sh, "animal": BRANCHES[now_sh][1]},
        "luck": luck,
    }


def _luck_pillars(profile, ys, ms, mb, birth_utc, seg):
    """Direction, approximate start age, and the sequence of ten-year pillars."""
    sex = getattr(profile, "sex", "unspecified")
    if sex not in ("male", "female"):
        return {"available": False, "reason": "Set sex in your profile to compute Luck Pillars."}

    year_yang = (ys % 2 == 0)
    forward = (year_yang and sex == "male") or (not year_yang and sex == "female")

    target = 315 + (seg + 1) * 30 if forward else 315 + seg * 30
    crossing = _term_crossing(birth_utc, target % 360, forward)
    start_age = None
    if crossing is not None:
        days = abs((crossing - birth_utc).total_seconds()) / 86400.0
        start_age = round(days / 3.0, 1)      # 3 days ~ 1 year

    month60 = _sexagenary_index(ms, mb)
    pillars = []
    for i in range(1, 9):
        idx = (month60 + i) % 60 if forward else (month60 - i) % 60
        s, b = idx % 10, idx % 12
        age0 = None if start_age is None else round(start_age + (i - 1) * 10, 1)
        pillars.append({"stem": s, "branch": b, "start_age": age0})
    return {"available": True, "forward": forward, "start_age": start_age, "pillars": pillars}


# ===========================================================================
# UI
# ===========================================================================
def _animal(branch):
    return BRANCHES[branch][1]


def build_page(state):
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout,
        QPushButton,
    )
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import Qt, QUrl
    from ui.theme import LIGHT, BADGE_COLORS_LIGHT

    EL_COLOR = {"Wood": "#5c8a4a", "Fire": "#c0623c", "Earth": "#b58a3c",
                "Metal": "#8a8f98", "Water": "#3c78c0"}

    def card():
        f = QFrame(); f.setObjectName("Card")
        f.setStyleSheet("QFrame#Card{background:%s;border:1px solid %s;border-radius:10px;}"
                        % (LIGHT["panel"], LIGHT["border"]))
        return f

    def badge(text):
        b = QLabel(text)
        b.setStyleSheet("color:%s;background:rgba(0,0,0,20);padding:2px 9px;border-radius:8px;"
                        "font-weight:bold;font-size:11px;" % BADGE_COLORS_LIGHT.get(text, "#888"))
        b.setFixedHeight(19); return b

    def head_row(title, badge_text=None):
        row = QHBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
        row.addWidget(t)
        if badge_text:
            row.addWidget(badge(badge_text))
        row.addStretch(1); return row

    page = QWidget()
    outer = QVBoxLayout(page); outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer.addWidget(scroll)
    body = QWidget(); lay = QVBoxLayout(body)
    lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)
    scroll.setWidget(body)

    h = QHBoxLayout()
    title = QLabel("B\u0101 Z\u00ec \u00b7 Four Pillars")
    title.setStyleSheet("font-size:20px;font-weight:bold;color:%s;" % LIGHT["text"])
    h.addWidget(title); h.addWidget(badge("TRADITIONAL")); h.addStretch(1)
    lay.addLayout(h)
    sub = QLabel("Your birth chart in stems and branches \u2014 a living tradition carried "
                 "on its own terms.")
    sub.setWordWrap(True); sub.setStyleSheet("color:%s;font-size:12px;" % LIGHT["subtle"])
    lay.addWidget(sub)

    profile = getattr(state, "active_profile", None)
    if profile is None:
        c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(20, 24, 20, 24)
        m = QLabel("No profile yet. Create one in Records \u2192 Profile to cast your pillars.")
        m.setWordWrap(True); m.setStyleSheet("color:%s;font-size:12px;" % LIGHT["text"])
        cl.addWidget(m); lay.addWidget(c); lay.addWidget(build_links_card(state, page, "bazi", card, _LINKS_NOTE)); lay.addStretch(1); return page

    bz = four_pillars(profile)
    if bz is None:
        m = QLabel("Add a birth date to your profile to cast your pillars.")
        m.setStyleSheet("color:%s;" % LIGHT["text"]); lay.addWidget(m); lay.addWidget(build_links_card(state, page, "bazi", card, _LINKS_NOTE)); lay.addStretch(1); return page

    # --- Four pillars grid ---
    c1 = card(); c1l = QVBoxLayout(c1); c1l.setContentsMargins(20, 16, 20, 18); c1l.setSpacing(10)
    c1l.addLayout(head_row("Four Pillars", "TRADITIONAL"))
    grid = QGridLayout(); grid.setHorizontalSpacing(18); grid.setVerticalSpacing(6)
    cols = [("Year", bz["pillars"]["year"]), ("Month", bz["pillars"]["month"]),
            ("Day", bz["pillars"]["day"]), ("Hour", bz["pillars"]["hour"])]
    for ci, (label, pil) in enumerate(cols):
        head = QLabel(label); head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.setStyleSheet("color:%s;font-weight:bold;font-size:11px;" % LIGHT["subtle"])
        grid.addWidget(head, 0, ci)
        if pil is None:
            box = QLabel("\u2014"); box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.setStyleSheet("color:%s;font-size:16px;" % LIGHT["subtle"])
            grid.addWidget(box, 1, ci)
            sub2 = QLabel("needs time"); sub2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub2.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
            grid.addWidget(sub2, 2, ci)
            continue
        stem_el = ELEMENTS[_stem_el(pil["stem"])]
        stem = QLabel(STEMS[pil["stem"]]); stem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stem.setStyleSheet("font-size:17px;font-weight:bold;color:%s;" % EL_COLOR[stem_el])
        grid.addWidget(stem, 1, ci)
        br = QLabel("%s (%s)" % (BRANCHES[pil["branch"]][0], _animal(pil["branch"])))
        br.setAlignment(Qt.AlignmentFlag.AlignCenter)
        br.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        grid.addWidget(br, 2, ci)
    if bz["pillars"]["day"]:
        dmk = QLabel("\u25b2 Day Master"); dmk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dmk.setStyleSheet("color:%s;font-size:11px;font-weight:bold;" % LIGHT["accent"])
        grid.addWidget(dmk, 3, 2)
    c1l.addLayout(grid)
    if bz["li_chun_unsure"]:
        unsure = QLabel("Born on Li Chun day, when the year and month pillars change. "
                        "Without a birth time this uses noon; add your birth time in "
                        "Records \u2192 Profile to settle them.")
        unsure.setWordWrap(True)
        unsure.setStyleSheet("color:%s;font-size:11px;" % LIGHT["warn"])
        c1l.addWidget(unsure)
    lay.addWidget(c1)

    # --- Day Master + strength ---
    dm = bz["day_master"]
    c2 = card(); c2l = QVBoxLayout(c2); c2l.setContentsMargins(20, 16, 20, 18); c2l.setSpacing(8)
    c2l.addLayout(head_row("Day Master", "TRADITIONAL"))
    dml = QLabel("Your Day Master is <b style='color:%s'>%s %s</b> \u2014 the self of the chart."
                 % (EL_COLOR[dm["element"]], dm["element"], STEMS[dm["stem"]]))
    dml.setWordWrap(True); dml.setStyleSheet("font-size:13px;color:%s;" % LIGHT["text"])
    c2l.addWidget(dml)
    st = QLabel("Simplified strength: <b>%s</b> (weighted visible-element count, score %+d). "
                "This is a transparent indicator, not a full hidden-stem reading."
                % (bz["strength"], bz["strength_score"]))
    st.setWordWrap(True); st.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    c2l.addWidget(st)
    # element tally line
    parts = []
    for i, e in enumerate(ELEMENTS):
        parts.append("<span style='color:%s'>%s %d</span>" % (EL_COLOR[e], e, bz["tally"][i]))
    tl = QLabel("Elements present: " + " \u00b7 ".join(parts))
    tl.setWordWrap(True); tl.setStyleSheet("font-size:11px;color:%s;" % LIGHT["text"])
    c2l.addWidget(tl)
    lay.addWidget(c2)

    # --- Luck pillars ---
    luck = bz["luck"]
    c3 = card(); c3l = QVBoxLayout(c3); c3l.setContentsMargins(20, 16, 20, 18); c3l.setSpacing(8)
    c3l.addLayout(head_row("Luck Pillars (d\u00e0 y\u00f9n)", "TRADITIONAL"))
    if not luck["available"]:
        m = QLabel(luck["reason"]); m.setWordWrap(True)
        m.setStyleSheet("font-size:12px;color:%s;" % LIGHT["warn"]); c3l.addWidget(m)
    else:
        dirn = "forward" if luck["forward"] else "backward"
        sa = "~%s yrs" % luck["start_age"] if luck["start_age"] is not None else "unknown"
        intro = QLabel("Running <b>%s</b>, first pillar begins at <b>%s</b> of age "
                       "(three-days-to-a-year rule)." % (dirn, sa))
        intro.setWordWrap(True); intro.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"])
        c3l.addWidget(intro)
        g = QGridLayout(); g.setHorizontalSpacing(14); g.setVerticalSpacing(4)
        for i, p in enumerate(luck["pillars"]):
            age = "" if p["start_age"] is None else "age %s" % p["start_age"]
            a = QLabel(age); a.setStyleSheet("font-size:10px;color:%s;" % LIGHT["subtle"])
            g.addWidget(a, 0, i)
            el = ELEMENTS[_stem_el(p["stem"])]
            pil = QLabel("%s\n%s" % (STEMS[p["stem"]], BRANCHES[p["branch"]][0]))
            pil.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pil.setStyleSheet("font-size:11px;color:%s;" % EL_COLOR[el])
            g.addWidget(pil, 1, i)
        c3l.addLayout(g)
    lay.addWidget(c3)

    # --- Right now (current shichen) ---
    cs = bz["current_shichen"]
    c4 = card(); c4l = QVBoxLayout(c4); c4l.setContentsMargins(20, 14, 20, 16)
    now = QLabel("Right now it is the hour of the <b>%s</b> (%s shichen)."
                 % (cs["animal"], BRANCHES[cs["branch"]][0]))
    now.setStyleSheet("font-size:12px;color:%s;" % LIGHT["text"]); c4l.addWidget(now)
    lay.addWidget(c4)

    # --- Boundary honesty ---
    c5 = card(); c5l = QVBoxLayout(c5); c5l.setContentsMargins(20, 14, 20, 16)
    note = QLabel("Boundary note: the month pillar follows the true solar term, computed "
                  "from the ephemeris. A birth on the same day as a term change sits right on "
                  "the boundary and may differ from sources using another ephemeris. The year "
                  "uses Li Chun; the day rolls at 23:00 (Zi hour).")
    note.setWordWrap(True); note.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    c5l.addWidget(note)
    lay.addWidget(c5)

    lay.addWidget(build_links_card(state, page, "bazi", card, _LINKS_NOTE))
    lay.addStretch(1)
    return page
