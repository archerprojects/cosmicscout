# Cosmic Scout

*Version 1.0.0 — Tuesday 3 November 2026*

A personal astrology and chronobiology desktop application for Linux (Flatpak).
Cosmic Scout computes profile-driven cycle guidance — it is a calculator, not a
static reference — and grades everything it shows by one honest test: *can a
channel of influence be named and traced?*

> Series note: previously Cosmic Harmony Scout (v1–v4) and Cosmic Compass (v5–v6);
> renamed Cosmic Scout at v1. Biorhythm has been removed — tested and found
> invalid (Hines 1998).

## Screenshots

![Dashboard — composite guidance with evidence-badged cycle bars](screenshots/CS-1.png)

![Cosmos — Tropical Zodiac with natal chart](screenshots/CS-2.png)

## Architecture

Cosmic Scout runs entirely offline except for one opt-in feature (NOAA space
weather, off by default).

- **Dashboard** — the dark guidance cockpit. *Today's Window* blends only the
  validated tier (circadian + ultradian); below it, one diverging bar per cycle,
  each with its evidence badge and named sub-bars (cortisol, temperature,
  melatonin, and sex- and age-aware hormonal cycles). Day / Week / Month scales.
- **Cycles** — the reasoning behind every bar: the named channel, the evidence
  grade, and how it reads right now.
- **Records** — *Profile* (several profiles allowed), *Journal* (a 12-question
  daily log with CSV export), *Patterns* (correlations with the log and rhythm
  discovery, both biased to silence) and *Settings* (current location from an
  offline city list, and the single network opt-in).
- **Cosmos** — Moon & Sky, Tropical Zodiac (season-of-birth science and natal
  chart), Shēngxiào, BaZi, Vedic and Earth Traditions, all computed locally,
  with editable out-links.
- **About** — how we decide what's real: the name-the-channel test, the badge
  legend and cited sources.

## Run from source

```bash
pip install -r requirements.txt
python3 chs/main.py
```

## Build (Flatpak)

A ready-built bundle, `CosmicScout-1.0.0-x86_64.flatpak`, is attached to the 1.0.0
release on GitHub. Install it with:

```bash
flatpak install --user CosmicScout-1.0.0-x86_64.flatpak
flatpak run org.cosmicscout.app
```

It uses the KDE 5.15-24.08 runtime, which Flathub marks end-of-life; Flatpak fetches
it from Flathub on install. Release 1.0.1 moves Cosmic Scout to PyQt6 on the KDE 6.11
runtime. To build the bundle yourself:

```bash
flatpak-builder --user --install-deps-from=flathub --force-clean \
    --repo=repo --default-branch=stable build-dir flatpak/org.cosmicscout.app.yml
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    repo CosmicScout-1.0.0-x86_64.flatpak org.cosmicscout.app stable
```

## Licence

GPL-3.0-or-later. Developer: archerprojects <archer.projects@proton.me>.

Bundled and third-party components, including the Swiss Ephemeris parts used
under the AGPL-3.0, are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Data attribution

City location data (`chs/data/cities15k.json.gz`) is derived from
[GeoNames](https://www.geonames.org/), licensed under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
The dataset is trimmed to cities with population ≥ 15,000 (name, country,
IANA timezone, latitude, longitude) and used entirely offline; the app makes
no calls to GeoNames.
