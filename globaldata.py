"""Aggregate the per-city data into regional and world climate dashboards.

A continent spans many climates, so averaging a whole continent's cities is not
meaningful. Instead cities are grouped into **latitudinal climate zones** (with
the hemisphere kept separate, since the seasons - and thus the monthly signal -
are mirrored across the equator), plus a **World** aggregate over every city.

Aggregation is the standard climate method: the *average of anomalies*. Each
city's annual (and monthly) values are first expressed as a departure from that
city's own 1961-1990 baseline, and only then averaged across the cities in a
zone. Averaging absolute temperatures across places with wildly different
climates is meaningless; averaging their anomalies answers the one question that
*is* comparable - how fast is this zone warming. Every 1940-2025 city cache
covers the full period, so a zone's city composition is stable year-to-year and
the average is unbiased over time.

The averaging is **area-weighted via a ~5° grid**: city anomalies are averaged
within their grid cell first, and the zone/world line is then the equal-weight
mean of the *cells*. A plain mean over cities would let the densest-sampled
regions dominate - while the backfill is filling the cache region-by-region
(Africa is ~76% fetched vs Europe's ~31% at the time of writing), and even at
full coverage the city list itself is denser in some regions than others. One
cell = one spatial sample makes the world line robust to both.

The payloads reuse :mod:`chartdata`'s archetype builders (trend / stripes /
matrix / multitrend) and its label-collection machinery, so the browser renders
them with the exact same code - and localises them through the same ``__ci18n``
map - as the per-city charts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from chartdata import (
    _floats,
    _matrix_chart,
    _mk,
    _multitrend_chart,
    _trend_chart,
)
import countries
from config import Location
from plots import BASELINE, annual_means, monthly_pivot, robust_trend_line

# Per-city population (GeoNames, via tools/gen_city_pop.py) so the ranking can
# show how many people each city holds. Sparse/optional; missing = no figure.
try:
    import json as _json
    from pathlib import Path as _Path
    _CITY_POP = _json.loads((_Path(__file__).resolve().parent / "data"
                             / "city_pop.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    _CITY_POP = {}

# How many warming / cooling extremes to surface per zone (top N + bottom M).
_EXTREME_TOP = 6
_EXTREME_BOTTOM = 3

_MONTHS = list(range(1, 13))

# A zone is plotted only when at least this many spatial samples back it - keeps
# the earliest, thinly-sampled zones from showing a one-city "average". Applied
# to grid cells in the zone aggregates (stage 2) and to cities in the gate that
# decides whether a zone appears at all.
_MIN_CITIES = 3

# Grid-cell size (degrees) for the area weighting: cities are averaged within
# their cell first, cells averaged with equal weight into the zone/world line.
_CELL_DEG = 5.0


def _cell_key(lat: float, lon: float) -> tuple[int, int]:
    """The ~5° grid cell a coordinate falls in (floor-division indices)."""
    return (int(np.floor(lat / _CELL_DEG)), int(np.floor(lon / _CELL_DEG)))


# --- climate zones ----------------------------------------------------------
# (key, display-order). Latitude bands; the hemisphere is kept distinct because
# January is midwinter north of the equator but midsummer south of it.
_ZONE_ORDER = [
    "tropical",
    "n-subtropical", "n-temperate", "n-boreal",
    "s-subtropical", "s-temperate",
]

# Distinct line colours for the zones in the comparison chart.
_ZONE_COLOR = {
    "tropical": "#e11d48",
    "n-subtropical": "#f59e0b",
    "n-temperate": "#16a34a",
    "n-boreal": "#2563eb",
    "s-subtropical": "#a855f7",
    "s-temperate": "#0891b2",
    "world": "#334155",
}

# i18n key holding each zone's localised name (defined in globaltext.py).
_ZONE_NAME_KEY = {
    "world": "region_world",
    "tropical": "region_tropical",
    "n-subtropical": "region_n_subtropical",
    "n-temperate": "region_n_temperate",
    "n-boreal": "region_n_boreal",
    "s-subtropical": "region_s_subtropical",
    "s-temperate": "region_s_temperate",
}


def zone_of(lat: float) -> str:
    """Map a latitude to its climate zone key (hemisphere-aware)."""
    if abs(lat) <= 23.5:
        return "tropical"
    if lat > 0:
        if lat <= 35:
            return "n-subtropical"
        if lat <= 55:
            return "n-temperate"
        return "n-boreal"
    if lat >= -35:
        return "s-subtropical"
    return "s-temperate"


# --- per-city anomaly contributions ----------------------------------------
def _baseline_mask(index: pd.Index) -> np.ndarray:
    lo, hi = BASELINE
    return (index >= lo) & (index <= hi)


def _annual_anomaly(df: pd.DataFrame) -> pd.Series:
    """City annual-mean anomaly (°C) vs its own 1961-1990 baseline, by year."""
    means = annual_means(df)
    base = means.loc[_baseline_mask(means.index)]
    baseline = base.mean() if not base.empty else means.mean()
    return means - baseline


def _monthly_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """City year×month anomaly (°C): each month vs its own 1961-1990 mean."""
    pivot = monthly_pivot(df).reindex(columns=_MONTHS)
    base = pivot.loc[_baseline_mask(pivot.index)]
    baseline = base.mean(axis=0) if not base.empty else pivot.mean(axis=0)
    return pivot.sub(baseline, axis=1)


# --- zone aggregation -------------------------------------------------------
class _Aggregate:
    """Accumulate a mean-of-anomalies over a fixed year grid.

    Used twice: per grid cell (cities added via :meth:`add`) and per zone
    (cell means added via :meth:`add_arrays`), so ``cities`` counts whatever
    the sample unit is at that stage - cities in a cell, cells in a zone.
    """

    def __init__(self, years: np.ndarray):
        self.years = years
        self._pos = {int(y): i for i, y in enumerate(years)}
        n = len(years)
        self.ann_sum = np.zeros(n)
        self.ann_cnt = np.zeros(n)
        self.mon_sum = np.zeros((n, 12))
        self.mon_cnt = np.zeros((n, 12))
        self.cities = 0

    def add(self, annual: pd.Series, monthly: pd.DataFrame) -> None:
        self.cities += 1
        for y, v in annual.items():
            i = self._pos.get(int(y))
            if i is not None and np.isfinite(v):
                self.ann_sum[i] += v
                self.ann_cnt[i] += 1
        mvals = monthly.to_numpy(dtype=float)
        for row, y in enumerate(monthly.index):
            i = self._pos.get(int(y))
            if i is None:
                continue
            r = mvals[row]
            ok = np.isfinite(r)
            self.mon_sum[i, ok] += r[ok]
            self.mon_cnt[i, ok] += 1

    def add_arrays(self, ann: np.ndarray, mon: np.ndarray) -> None:
        """Add one already-averaged sample (a cell mean) on the same year grid."""
        self.cities += 1
        ok = np.isfinite(ann)
        self.ann_sum[ok] += ann[ok]
        self.ann_cnt[ok] += 1
        okm = np.isfinite(mon)
        self.mon_sum[okm] += mon[okm]
        self.mon_cnt[okm] += 1

    def annual(self, min_cnt: int = _MIN_CITIES) -> np.ndarray:
        out = np.full(len(self.years), np.nan)
        ok = self.ann_cnt >= min_cnt
        out[ok] = self.ann_sum[ok] / self.ann_cnt[ok]
        return out

    def monthly(self, min_cnt: int = _MIN_CITIES) -> np.ndarray:
        out = np.full_like(self.mon_sum, np.nan)
        ok = self.mon_cnt >= min_cnt
        out[ok] = self.mon_sum[ok] / self.mon_cnt[ok]
        return out


# --- payload builders (reuse chartdata archetypes) --------------------------
def _anomaly_trend(years, values, tr, L, Lf, color) -> dict:
    """Annual-anomaly points + LOESS + Theil-Sen trend/decade (one zone)."""
    return _trend_chart(
        years, values, tr, L, Lf,
        xlabel_key="year", ylabel_key="anomaly_ylabel",
        raw_color="#94a3b8", raw_style="points",
        raw_label_key=None, raw_label_kw=None,
        loess_color=color, trend_unit_key="per_decade_c", trend_decimals=2,
        trend_color="#334155")


def _stripes(years, values, tr, L) -> dict:
    """Warming-stripes payload from a zone's annual anomaly series."""
    lo, hi = BASELINE
    finite = np.abs(values[np.isfinite(values)])
    limit = float(finite.max()) if finite.size else 1.0
    return {
        "kind": "stripes",
        "years": [int(y) for y in years],
        "anom": _floats(values),
        "limit": round(limit or 1.0, 3),
        "xlabel": L(tr, "year"),
        "cbarLabel": L(tr, "stripes_cbar", lo=lo, hi=hi),
    }


def _heatmap(years, month_values, tr, L) -> dict:
    """Year×month anomaly heatmap for one zone (diverging, ±0.5 °C bands)."""
    lo, hi = BASELINE
    pivot = pd.DataFrame(index=[int(y) for y in years])
    return _matrix_chart(pivot, month_values, tr, L,
                         step=0.5, cbar_key="anom_heatmap_cbar",
                         cbar_kw={"base": f"{lo}-{hi}"}, diverging=True)


def _city_extremes(stats, tr, L) -> dict:
    """Horizontal bars of a zone's most extreme cities by warming rate.

    ``stats``: list of ``(name, trend_per_decade)``. Shows the fastest-warming
    handful and, if the zone has enough places, the few slowest/cooling ones -
    the extreme cases within the zone, red for warming, blue for cooling.
    """
    ordered = sorted(stats, key=lambda s: s[1], reverse=True)
    picked = ordered[:_EXTREME_TOP]
    if len(ordered) > _EXTREME_TOP + _EXTREME_BOTTOM:
        picked = picked + ordered[-_EXTREME_BOTTOM:]
    return {
        "kind": "citybars",
        "labels": [n for n, _ in picked],
        "values": [round(float(t), 3) for _, t in picked],
        "xlabel": L(tr, "per_decade_c"),
        "posColor": "#d62728",
        "negColor": "#2c7fb8",
    }


def _comparison(years, zone_series, tr, L, Lf) -> dict:
    """Every zone's warming curve on one chart (LOESS anomalies, no trend line)."""
    series = [
        (values, _ZONE_COLOR[key], _ZONE_NAME_KEY[key], {}, "per_decade_c", 2)
        for key, values in zone_series
    ]
    return _multitrend_chart(years, series, tr, L, Lf,
                             xlabel_key="year", ylabel_key="anomaly_ylabel",
                             show_trend=False)


# A country needs at least this many cities to enter the country ranking - a
# single station is one city's weather, not a country-level signal, and those
# noisy singletons otherwise dominate the top of the board.
_COUNTRY_MIN_CITIES = 2

# Fixed decade axis for the inline warming-stripes bar: each city/country ships
# nine decade-mean anomalies (°C vs its 1961-1990 baseline), null where a decade
# has no data. A fixed axis lets country rows average city stripes decade-by-decade.
_STRIPE_DECADES = [1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]


def _mean_stripes(rows: list[list]) -> list:
    """Element-wise mean of several fixed-length stripe arrays, skipping nulls
    per decade (so a country's stripes reflect whatever cities have that decade)."""
    out: list = []
    for i in range(len(_STRIPE_DECADES)):
        vals = [r[i] for r in rows if i < len(r) and r[i] is not None]
        out.append(round(sum(vals) / len(vals), 2) if vals else None)
    return out


# Climate-analog horizon: project each city's recent mean temperature this many
# decades forward on its own trend, then find the city whose CURRENT mean matches
# - "by 2050, X will feel like Y does today". 2.5 decades ≈ 2025 → 2050.
_ANALOG_DECADES = 2.5


def _match_analog(a: dict, src: list[dict], target: float, warmer: bool):
    """Closest present-day city to ``target`` mean temp that is on the wanted side
    of city ``a`` (warmer or cooler), same hemisphere (comparable seasons), with a
    continentality penalty so oceanic != continental analogs. Returns it or None."""
    best, best_score = None, 1e9
    for b in src:
        if b["s"] == a["s"] or (a["lat"] >= 0) != (b["lat"] >= 0):
            continue
        side = (b["m"] - a["m"]) if warmer else (a["m"] - b["m"])
        if side < 0.3:                          # must be meaningfully warmer/cooler
            continue
        dm = abs(b["m"] - target)
        if dm > 1.5:                            # temperature must roughly match
            continue
        score = dm + 0.3 * abs(b.get("amp", 0.0) - a.get("amp", 0.0))
        if score < best_score:
            best_score, best = score, b
    return best


def _compute_analogs(src: list[dict]) -> dict:
    """For each city, find two present-day cities that make its past and future
    concrete: a warmer city matching where it is HEADED (recent mean projected
    forward on its trend -> "by 2050, X will feel like Y"), and a cooler city
    matching where it CAME FROM (its earliest-decade mean -> "in 1940, X felt like
    Z does today"). ``src`` items: {s, n, cc, lat, m, m0, amp, t}. Returns
    {slug: {future?: {s,n,cc,d}, past?: {s,n,cc,d}}} - each side optional."""
    out: dict = {}
    for a in src:
        entry: dict = {}
        # Future: where the city is heading, matched to a warmer city today. Only
        # for cities projected meaningfully WARMER (so the analog and the wording
        # are never inverted); a cooling/flat city simply gets no future line.
        proj = a["m"] + a["t"] * _ANALOG_DECADES
        if proj - a["m"] >= 0.3:
            fut = _match_analog(a, src, proj, warmer=True)
            if fut:
                entry["future"] = {"s": fut["s"], "n": fut["n"], "cc": fut["cc"],
                                   "d": round(proj - a["m"], 1)}
        # Past: where it came from - only for cities that actually WARMED since the
        # 1940s (m0), so the wording is never inverted; matched to a cooler city.
        m0 = a.get("m0")
        if m0 is not None and a["m"] - m0 >= 0.3:
            past = _match_analog(a, src, m0, warmer=False)
            if past:
                entry["past"] = {"s": past["s"], "n": past["n"], "cc": past["cc"],
                                 "d": round(a["m"] - m0, 1)}
        if entry:
            out[a["s"]] = entry
    return out


def _country_stats(ranking: list[dict]) -> list[dict]:
    """Aggregate the city ranking to countries: each country's mean city warming
    rate, sorted fastest-first, with a global rank and a "faster than N% of the
    world" percentile. Countries with fewer than ``_COUNTRY_MIN_CITIES`` cities
    are excluded (too noisy to represent a country). Feeds the per-country
    headline and the share cards.
    """
    by_cc: dict[str, list[dict]] = {}
    for r in ranking:
        by_cc.setdefault(r["cc"], []).append(r)
    stats = []
    for cc, rs in by_cc.items():
        if len(rs) < _COUNTRY_MIN_CITIES:
            continue
        ts = [r["t"] for r in rs]
        dts = [r["dt"] for r in rs]
        stats.append({"cc": cc, "t": round(sum(ts) / len(ts), 3),
                      "dt": round(sum(dts) / len(dts), 1),
                      "st": _mean_stripes([r["st"] for r in rs]),
                      "n": len(rs),
                      "pop": countries.country_population(cc)})
    stats.sort(key=lambda s: s["t"], reverse=True)
    total = len(stats)
    for i, s in enumerate(stats):
        s["rank"] = i + 1
        s["total"] = total
        # Share of countries this one is warming faster than (0-99%).
        s["pct"] = round(100 * (total - (i + 1)) / total) if total else 0
    return stats


# --- entry point ------------------------------------------------------------
def compute_global(frames: dict, locations: list[Location], tr: dict):
    """Aggregate all cities into world + zonal dashboards.

    ``frames``: ``{slug: daily-mean DataFrame}`` for every built city.
    ``tr``: the label language for the payload (English; localised client-side).

    Returns ``(payload, specs, meta)``:
      ``payload`` - ``{"comparison": <multitrend>, "regions": {zone: {anomaly,
        stripes, heatmap}}, "order": [...], "counts": {...}}`` (language-neutral).
      ``specs``   - ``{chart_id: [(english, recipe), ...]}`` for
        :func:`plots.localize_specs`.
      ``meta``    - ``{"order": [...zones with data...], "counts": {...}}`` for
        the server-rendered region <select>.
    """
    by_slug = {loc.slug: loc for loc in locations}
    # Common year grid across every contributing city.
    yr_lo = min(int(df.index.year.min()) for df in frames.values())
    yr_hi = max(int(df.index.year.max()) for df in frames.values())
    years = np.arange(yr_lo, yr_hi + 1)

    aggs: dict[str, _Aggregate] = {
        key: _Aggregate(years) for key in (_ZONE_ORDER + ["world"])
    }
    # Stage-1 accumulators, one per (zone, ~5° grid cell): cities average into
    # their cell, cells average with equal weight into the zone - see the module
    # docstring for why (region-skewed backfill + uneven city density).
    cell_aggs: dict[tuple[str, tuple[int, int]], _Aggregate] = {}
    # Cities contributing per zone (for the region <select> labels and the
    # minimum-sample gate; the _Aggregate counters count cells, not cities).
    city_count: dict[str, int] = {key: 0 for key in aggs}
    # Per-city warming rate (°C/decade), grouped by zone, for the extremes chart.
    city_stats: dict[str, list] = {key: [] for key in aggs}
    # Every real city's warming rate for the world ranking table (name, slug,
    # country, trend). Ocean/region reference points have no country and are
    # excluded - you can't move to Point Nemo.
    ranking: list[dict] = []
    analog_src: list[dict] = []   # {s,n,cc,lat,m,t} for the 2050 climate analog
    for slug, df in frames.items():
        loc = by_slug.get(slug)
        if loc is None:
            continue
        ann = _annual_anomaly(df)
        mon = _monthly_anomaly(df)
        z = zone_of(loc.latitude)
        cell = _cell_key(loc.latitude, loc.longitude)
        for key in ("world", z):
            city_count[key] += 1
            ca = cell_aggs.get((key, cell))
            if ca is None:
                ca = cell_aggs[(key, cell)] = _Aggregate(years)
            ca.add(ann, mon)
        yrs = ann.index.to_numpy(dtype=float)
        vals = ann.to_numpy(dtype=float)
        ok = np.isfinite(vals)
        if int(ok.sum()) >= 10:
            slope, _line = robust_trend_line(yrs[ok], vals[ok])
            entry = (loc.name, slope * 10)
            city_stats["world"].append(entry)
            city_stats[z].append(entry)
            cc = countries.country_code(loc)
            if cc:
                span = float(yrs[ok].max() - yrs[ok].min())
                # Decade-mean anomalies (fixed 1940→2020 axis) for the stripes bar.
                a = ann.dropna()
                dm = a.groupby((a.index.astype(int) // 10) * 10).mean().to_dict()
                st = [round(float(dm[d]), 2) if d in dm else None
                      for d in _STRIPE_DECADES]
                ranking.append({"n": loc.name, "s": loc.slug, "cc": cc,
                                "r": loc.region,
                                "pop": _CITY_POP.get(loc.slug),
                                "t": round(float(slope) * 10, 3),
                                # Total warming across the record - more visceral
                                # than °C/decade - and the stripes.
                                "dt": round(float(slope) * span, 1),
                                # Unrounded values kept only to aggregate gt/gdt
                                # from raw (avoids double-rounding); stripped below.
                                "_traw": float(slope) * 10,
                                "_dtraw": float(slope) * span,
                                "st": st})
                # Recent mean temp + seasonal amplitude (warmest-minus-coldest
                # month) - the amplitude captures continentality, so a warmer
                # Warsaw maps to another continental city, not a mild maritime one.
                amn = annual_means(df).dropna()
                if len(amn):
                    recent = amn[amn.index >= int(amn.index.max()) - 9]
                    early = amn[amn.index <= int(amn.index.min()) + 9]
                    mm = monthly_pivot(df).mean(axis=0).dropna()
                    amp = float(mm.max() - mm.min()) if len(mm) else 0.0
                    analog_src.append({
                        "s": loc.slug, "n": loc.name, "cc": cc,
                        "lat": loc.latitude, "amp": round(amp, 1),
                        "m": round(float(recent.mean()), 2),
                        # Earliest-decade mean (~1940s) for the "in 1940 it felt
                        # like ..." past analog.
                        "m0": round(float(early.mean()), 2),
                        "t": round(float(slope) * 10, 3)})
    # Stage 2: fold each cell's mean series into its zone with equal weight.
    # Inside a cell one city is a valid sample (min_cnt=1); the zone-level
    # _MIN_CITIES floor then applies to the number of *cells* per year.
    for (key, _cell), ca in cell_aggs.items():
        aggs[key].add_arrays(ca.annual(min_cnt=1), ca.monthly(min_cnt=1))

    ranking.sort(key=lambda r: r["t"], reverse=True)
    # "Global" reference = the average warming rate across every ranked city, so a
    # row can say "1.6× the world-city average". Land cities, so it runs hotter
    # than the true ocean-inclusive global mean; labelled as a city average.
    # Averaged from the unrounded per-city values, then rounded once, so a build-up
    # of per-city rounding can't shift the published aggregate's last digit.
    gt = round(sum(r["_traw"] for r in ranking) / len(ranking), 3) if ranking else 0.0
    # World-city average warming since 1940 (mean of each city's dt). Same caveat
    # as gt: an equal-weighted land-city average, not the true global mean.
    gdt = round(sum(r["_dtraw"] for r in ranking) / len(ranking), 1) if ranking else 0.0
    for r in ranking:  # drop the raw helpers so they never reach _global.json
        r.pop("_traw", None)
        r.pop("_dtraw", None)
    country_ranking = _country_stats(ranking)
    analogs = _compute_analogs(analog_src)

    # Which zones cleared the minimum-cities bar (world always qualifies).
    order = ["world"] + [k for k in _ZONE_ORDER if city_count[k] >= _MIN_CITIES]
    counts = {k: city_count[k] for k in order}

    payload: dict = {"regions": {}, "order": order, "counts": counts,
                     "ranking": ranking, "countries": country_ranking,
                     # World-city average warming rate (°C/decade) - the "× global"
                     # reference used in the ranking table.
                     "gt": gt,
                     # World-city average warming since 1940 (°C), for the badge.
                     "gdt": gdt,
                     # How many cities that average is taken over, so the badge can
                     # say what it averaged. Grows as the backfill adds cities.
                     "gn": len(ranking),
                     # {slug: {future?, past?}} - present-day cities matching this
                     # city's 2050 future and its 1940 past (each {s,n,cc,d}).
                     "analogs": analogs,
                     # IANA timezone -> country, so the browser can preselect the
                     # visitor's country in the per-country hook (offline, from
                     # Intl timezone; no geolocation permission).
                     "tzcc": countries.tz_country_map()}
    specs: dict[str, list] = {}

    def _add(chart_id: str, builder):
        coll, L, Lf = _mk()
        result = builder(L, Lf)
        specs[chart_id] = coll
        return result

    # Headline: every zone's warming curve overlaid (skip the world line - it is
    # the average of the zones and would flatten the contrast between them).
    zone_series = [(k, aggs[k].annual()) for k in order if k != "world"]
    payload["comparison"] = _add(
        "comparison", lambda L, Lf: _comparison(years, zone_series, tr, L, Lf))

    for key in order:
        agg = aggs[key]
        ann = agg.annual()
        mon = agg.monthly()
        color = _ZONE_COLOR[key]
        payload["regions"][key] = {
            "anomaly": _add(f"{key}:anomaly",
                            lambda L, Lf, a=ann, c=color:
                            _anomaly_trend(years, a, tr, L, Lf, c)),
            "stripes": _add(f"{key}:stripes",
                            lambda L, Lf, a=ann: _stripes(years, a, tr, L)),
            "heatmap": _add(f"{key}:heatmap",
                            lambda L, Lf, m=mon: _heatmap(years, m, tr, L)),
            "extremes": _add(f"{key}:extremes",
                             lambda L, Lf, k=key: _city_extremes(city_stats[k], tr, L)),
        }

    meta = {"order": order, "counts": counts}
    return payload, specs, meta
