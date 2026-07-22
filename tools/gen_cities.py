#!/usr/bin/env python
"""Regenerate cities750k.tsv — every city with population > 100,000.

(The filename is historical — the threshold was lowered 750k -> 250k -> 100k to
broaden global coverage; cities render as their Open-Meteo data is backfilled.)

Sources (download + unzip from https://download.geonames.org/export/dump/):
  - ``cities15000.txt`` — every city with population > 15,000.
  - ``countryInfo.txt`` — maps each country to a continent, so EVERY nation's
    cities are placed in a region (no country is dropped at the lower threshold).
Each qualifying city is mapped to a region and de-duplicated against the curated
list in config.py by proximity (~20 km), so e.g. GeoNames "Warsaw" doesn't
duplicate the curated "Warszawa".

Writes two files:
  - ``cities750k.tsv``   — the primaries (>100k, deduped). Columns: region, name,
    lat, lon, tz.
  - ``city_aliases.tsv`` — every smaller city that shares a primary's ~11 km
    Open-Meteo grid cell (identical record), so it is searchable by its own name
    and reuses the primary's data. Columns: primary_slug, alias_name, region,
    lat, lon.

Usage:  python tools/gen_cities.py /path/to/cities15000.txt /path/to/countryInfo.txt
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

MIN_POP = 100_000
# ~5.5 km: only merge near-identical points (a GeoNames duplicate entry, or the
# curated "Warszawa" vs GeoNames "Warsaw"), not genuinely distinct adjacent
# cities like Yokohama next to Tokyo - so the set approaches ALL >100k cities.
NEAR_DEG = 0.05

# ~11 km: one ERA5-Land reanalysis cell. Any GeoNames city (down to the 15k
# floor of cities15000.txt) within this of a primary resolves to the SAME
# Open-Meteo grid point, so it has an IDENTICAL 1940-> record. Rather than drop
# these overlapping places, we emit them as ALIASES that reuse the primary's
# already-committed data - reachable by their own name in search at zero extra
# fetch cost, which is how the site covers thousands of smaller towns.
GRID_DEG = 0.1
# Cap aliases per primary so one metropolis's ring of suburbs doesn't flood the
# search with near-identical points; the largest-population ones are kept.
MAX_ALIASES_PER_PRIMARY = 12

# Same slug within this box (~33 km, cos-scaled) = the same city whose curated
# and GeoNames coordinates disagree about the centre - a duplicate to skip, not
# a homonym. Only a genuinely distant namesake (Newcastle ZA vs Newcastle GB)
# earns a "(CC)"-suffixed entry. Without this, 19 metros (Lagos, Kinshasa,
# Bogotá, Toronto...) appeared twice: curated dot + a "(CC)" ghost ~10 km away.
DUP_NAME_DEG = 0.3

# GeoNames feature codes that are NOT standalone settlements and must never
# become primary map dots: PPLX = section/district of a city (Wola inside
# Warszawa), PPLQ/PPLW = abandoned/destroyed, PPLH/PPLCH = historical. They
# stay eligible as ALIASES - a district within a primary's grid cell shares
# its record, so "Wola" remains searchable and resolves to Warszawa.
_NON_CITY_FCODES = {"PPLX", "PPLQ", "PPLW", "PPLH", "PPLCH"}

# GeoNames continent code -> our region name. Antarctica is skipped (no cities).
_CONTINENT = {"EU": "Europe", "AS": "Asia", "AF": "Africa",
              "NA": "North America", "SA": "South America", "OC": "Oceania"}
# Countries the site groups under "Middle East" (a sub-split of Asia), matching
# the curated config; overrides the GeoNames continent for these.
_MIDDLE_EAST = set("TR IQ IR SA AE YE SY LB JO IL OM QA BH KW PS".split())


def load_region_map(country_info: Path) -> dict:
    """Build ISO-3166 alpha-2 -> region for EVERY country from GeoNames
    countryInfo.txt (col 0 = code, col 8 = continent), so no nation is dropped
    when the population threshold is lowered. Middle-East countries are split out
    of Asia to match the curated config."""
    region: dict[str, str] = {}
    for line in country_info.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) < 9:
            continue
        cc, cont = f[0].strip(), f[8].strip()
        if cc in _MIDDLE_EAST:
            region[cc] = "Middle East"
        elif cont in _CONTINENT:
            region[cc] = _CONTINENT[cont]
    return region


def _bucket(la: float, lo: float) -> tuple:
    """The GRID_DEG cell a coordinate falls in (the spatial-index key)."""
    return (round(la / GRID_DEG), round(lo / GRID_DEG))


def build_grid_index(primaries: list[tuple]) -> dict:
    """Index primaries by their GRID_DEG cell so an alias candidate only has to
    test the 3x3 block of cells around it (not all ~6k primaries)."""
    idx: dict[tuple, list] = {}
    for slug, name, la, lo, region in primaries:
        idx.setdefault(_bucket(la, lo), []).append((slug, name, la, lo, region))
    return idx


def nearest_primary(la: float, lo: float, idx: dict):
    """The closest primary within GRID_DEG of (la, lo), or None. Scans the cell
    plus its 8 neighbours - every point within GRID_DEG lands in one of those."""
    ci, cj = _bucket(la, lo)
    best = None
    best_d = None
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for slug, name, pla, plo, region in idx.get((ci + di, cj + dj), []):
                if abs(la - pla) >= GRID_DEG or abs(lo - plo) >= GRID_DEG:
                    continue
                d = (la - pla) ** 2 + (lo - plo) ** 2
                if best_d is None or d < best_d:
                    best_d = d
                    best = (slug, name, region)
    return best


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: python tools/gen_cities.py "
                         "<cities15000.txt> <countryInfo.txt>")
    src = Path(sys.argv[1])
    REGION = load_region_map(Path(sys.argv[2]))
    # De-dupe against the CURATED list only (config._CITIES), never against the
    # generated TSV itself — otherwise a second run dedupes against its own
    # output and produces nothing.
    coords = [(la, lo) for _, _, la, lo, _ in config._CITIES]
    slugs = {config.slugify(name) for _, name, _, _, _ in config._CITIES}
    # Where each accepted slug sits, for the same-name-nearby duplicate test.
    slug_pos = {config.slugify(name): (la, lo)
                for _, name, la, lo, _ in config._CITIES}
    rows: list[tuple] = []
    skipped = 0

    def near(la: float, lo: float) -> bool:
        # Longitude degrees shrink with latitude, so scale them by cos(lat) to
        # keep this a true ~5.5 km box everywhere. The unscaled test let
        # GeoNames "Wola" (a Warsaw district 3.6 km out, 0.052 deg of
        # longitude) slip past the merge and become its own map dot.
        k = math.cos(math.radians(la))
        return any(abs(la - a) < NEAR_DEG and abs(lo - o) * k < NEAR_DEG
                   for a, o in coords)

    # Read EVERY city (down to the 15k floor) once: the >100k subset becomes the
    # primaries written to the TSV; the rest are alias candidates for the grid
    # pass below.
    all_cities = []
    for line in src.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if len(f) < 18:
            continue
        try:
            pop = int(f[14])
        except ValueError:
            continue
        # f[7] = feature code, kept so districts can be barred from primaries
        # below (they stay in the pool as alias candidates).
        all_cities.append((pop, f[1], float(f[4]), float(f[5]), f[8], f[17],
                           f[7]))

    # Process qualifying cities LARGEST-FIRST, so when two fall within NEAR_DEG
    # the bigger one claims the slot. Otherwise a small city earlier in GeoNames
    # file order knocks out a nearby metropolis (lowering the threshold added many
    # such small neighbours, dropping Yokohama, Kyoto, etc.).
    cands = sorted((c for c in all_cities
                    if c[0] > MIN_POP and c[6] not in _NON_CITY_FCODES),
                   key=lambda c: -c[0])

    for pop, name, la, lo, cc, tz, _fc in cands:
        region = REGION.get(cc)
        if not region or near(la, lo):
            skipped += 1
            continue
        slug = config.slugify(name)
        if slug in slugs:
            # Same name close by = the same city (curated centre vs GeoNames
            # centre), not a homonym - skip instead of minting a "(CC)" ghost.
            pla_plo = slug_pos.get(slug)
            if pla_plo is not None:
                _k = math.cos(math.radians(la))
                if (abs(la - pla_plo[0]) < DUP_NAME_DEG
                        and abs(lo - pla_plo[1]) * _k < DUP_NAME_DEG):
                    skipped += 1
                    continue
            slug = f"{slug}-{cc.lower()}"
            if slug in slugs:
                skipped += 1
                continue
            name = f"{name} ({cc})"
        slugs.add(slug)
        slug_pos[slug] = (la, lo)
        coords.append((la, lo))
        rows.append((region, name, f"{la:.4f}", f"{lo:.4f}", tz))

    rows.sort(key=lambda r: (r[0], r[1]))
    out = Path(__file__).resolve().parent.parent / "cities750k.tsv"
    out.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} cities to {out} (skipped {skipped})")
    print("by region:", dict(Counter(r[0] for r in rows)))

    write_aliases(all_cities, rows, slugs)


def write_aliases(all_cities: list[tuple], rows: list[tuple],
                  primary_slugs: set) -> None:
    """Emit city_aliases.tsv: for every GeoNames city that ISN'T a primary but
    sits within GRID_DEG of one, record it as an alias of that primary. These
    reuse the primary's committed Open-Meteo record (same grid cell → identical
    data), so the site can list thousands more small towns without fetching any
    new data. Columns: primary_slug, alias_name, region, lat, lon."""
    # Primaries = the curated config cities + the >100k rows just generated.
    primaries = [(config.slugify(n), n, la, lo, r)
                 for r, n, la, lo, _ in config._CITIES]
    primaries += [(config.slugify(n), n, float(la), float(lo), r)
                  for r, n, la, lo, _ in rows]
    idx = build_grid_index(primaries)

    # Largest-first: if two candidates share a slug, the more populous one wins;
    # its nearest primary is the one it shares a grid cell with.
    best: dict[str, tuple] = {}   # alias_slug -> (pop, primary_slug, name, region, la, lo)
    for pop, name, la, lo, _cc, _tz, _fc in sorted(all_cities, key=lambda c: -c[0]):
        aslug = config.slugify(name)
        if not aslug or aslug in primary_slugs:
            continue
        prim = nearest_primary(la, lo, idx)
        if not prim:
            continue
        pslug, pregion = prim[0], prim[2]
        prev = best.get(aslug)
        if prev is None or pop > prev[0]:
            best[aslug] = (pop, pslug, name, pregion, la, lo)

    # Apply the per-primary cap, keeping the most populous aliases.
    per_primary: Counter = Counter()
    aliases: list[tuple] = []
    for pop, pslug, name, region, la, lo in sorted(best.values(), key=lambda v: -v[0]):
        if per_primary[pslug] >= MAX_ALIASES_PER_PRIMARY:
            continue
        per_primary[pslug] += 1
        aliases.append((pslug, name, region, f"{la:.4f}", f"{lo:.4f}"))

    aliases.sort(key=lambda a: (a[2], a[0], a[1]))
    out = Path(__file__).resolve().parent.parent / "city_aliases.tsv"
    out.write_text("".join("\t".join(a) + "\n" for a in aliases), encoding="utf-8")
    print(f"wrote {len(aliases)} aliases to {out} "
          f"(covering {len(per_primary)} primaries)")
    print("aliases by region:", dict(Counter(a[2] for a in aliases)))


if __name__ == "__main__":
    main()
