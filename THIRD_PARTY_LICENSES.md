# Cosmic Scout — Third-Party Licences

*Version 1.1.0 — Monday 9 November 2026*

Cosmic Scout itself is licensed **GPL-3.0-or-later** (see `LICENSE`). It bundles or
depends on the components below. Licences were checked against each project's own
published metadata on 3 November 2026.

| Component | How it is used | Licence | Source |
|---|---|---|---|
| **Swiss Ephemeris** (Astrodienst AG): ephemeris data files `chs/flatlib/resources/swefiles/` | Bundled | **AGPL-3.0** (chosen from Astrodienst's AGPL / Professional dual licence) | https://www.astro.com/swisseph/ |
| **pyswisseph** 2.10.3.2: Python bindings to the Swiss Ephemeris | Dependency | **AGPL-3.0** | https://pypi.org/project/pyswisseph/ |
| **flatlib** 0.2.3 (FlatAngle): `chs/flatlib/` | Bundled, unmodified | MIT (`chs/flatlib/LICENSE`) | https://github.com/flatangle/flatlib |
| **lunardate** 0.3.0 (LI Daobing): `chs/lunardate.py` | Bundled, unmodified | GPL-3.0-or-later; derived from "lunar" (Fung F. Lee & Ricky Yeung), GPL-2+ | https://github.com/lidaobing/python-lunardate |
| **PyEphem** (`ephem`) 4.2.1 | Dependency | MIT | https://pypi.org/project/ephem/ |
| **PyQt6** 6.11.0 (Riverbank Computing) | Dependency | GPL v3 | https://pypi.org/project/PyQt6/ |
| **GeoNames** city data: `chs/data/cities15k.json.gz` (trimmed) | Bundled data | CC BY 4.0 | https://www.geonames.org/ |

## Swiss Ephemeris and the AGPL

Astrodienst requires anyone distributing software that contains parts of the Swiss
Ephemeris to choose either the GNU Affero General Public License or the Swiss
Ephemeris Professional License. Cosmic Scout uses those parts under the **AGPL-3.0**.
GPLv3 section 13 permits combining GPLv3 code with AGPLv3 code; each part keeps its
own licence. The complete corresponding source of Cosmic Scout, including the Swiss
Ephemeris parts, is in this repository.
