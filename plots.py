"""Temperature statistics and computation helpers.

This module used to render matplotlib charts; the charts are now drawn in the
browser with Chart.js (see :mod:`chartdata` and ``assets/charts.js``), so only
the *computation* remains here - the statistics the charts are built from:
annual means, a robust Theil-Sen trend and its Mann-Kendall significance, a
dependency-free LOESS smoother, monthly pivots, and the growing-season /
heat-spell / calendar-day-percentile helpers behind the health indices.

``localize_specs`` turns a chart's collected label recipes into the
``{english: localized}`` map the browser applies (:mod:`chartdata` collects the
recipes; :mod:`main` calls this per language). No matplotlib dependency.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


# --- chart-text localisation -------------------------------------------------
# A label is stored as (english, recipe) where recipe is a serialisable list of
# parts, each either ("t", literal_text) or ("k", dict_key, kwargs). compose_label
# replays a recipe against a translation table; the browser mirrors it exactly
# (charts.js composeLabel) so a client-composed label matches the server byte for
# byte. Numbers are pre-formatted into "t" parts (language-neutral), so the only
# format specs a recipe leaves for .format/JS are the plain {lo}/{hi}/{base}/{t}
# in the keyed templates (see _sig_parts and chartdata for the composition).
def compose_label(recipe: list, tr: dict) -> str:
    """Replay one label recipe (list of parts) against ``tr``."""
    out = []
    for part in recipe:
        if part[0] == "t":
            out.append(part[1])
        else:
            _, key, kw = part
            out.append(tr[key].format(**kw))
    return "".join(out)


def localize_specs(specs: list, tr: dict) -> dict:
    """{english_string: string_in_tr's_language} for one chart's collected texts."""
    return {s_en: compose_label(recipe, tr) for s_en, recipe in specs}


def _sig_parts(values: np.ndarray) -> list:
    """Trend significance as recipe parts: the "n.s." word re-localises (a keyed
    part) while the p-value is language-neutral (a literal). Composed against a
    table it reproduces :func:`trend_significance` exactly."""
    p = _mann_kendall_p(np.asarray(values, dtype=float))
    if p >= 0.05:
        return [["k", "ns", {}], ["t", f", p={p:.2f}"]]
    if p < 1e-4:
        return [["t", f"p={p:.0e}"]]
    return [["t", f"p={p:.4f}".rstrip("0")]]


# Standard WMO climatological reference period for anomalies.
BASELINE = (1961, 1990)

# Daily-mean thresholds for the "hot" and "freezing" day counts.
HOT_DAY_C = 18.0
FREEZE_DAY_C = 0.0

# A "big jump" is a day-to-day change in daily mean of at least this many °C.
SWING_C = 6.0

# Thermal growing season: days whose daily mean stays at/above this threshold.
# Onset/end require this many consecutive days to ignore isolated warm/cold spells.
GROW_C = 5.0
GROW_RUN = 6

# --- health-impact thresholds ---------------------------------------------
# Heat/cold spells (ETCCDI WSDI/CSDI style): a run of >= SPELL_RUN days beyond a
# calendar-day percentile of the 1961-1990 baseline.
SPELL_RUN = 3
HEAT_PCT = 90    # daily-max exceedances -> heat wave
COLD_PCT = 10    # daily-min shortfalls  -> cold spell
# Tropical night (WMO): daily minimum stays at/above this (no nocturnal relief).
TROPICAL_NIGHT_C = 20.0
# Degree-day bases (population thermal-comfort / energy burden).
HDD_BASE_C = 18.0   # heating degree days below this mean
CDD_BASE_C = 22.0   # cooling degree days above this mean
# Heavy-rain day (ETCCDI R20mm): daily precipitation at/above this.
HEAVY_RAIN_MM = 20.0
# Apparent-temperature (heat-index) stress thresholds, NWS-style °C.
APPARENT_STRONG_C = 32.0   # "extreme caution" - heat exhaustion likely on exertion
APPARENT_DANGER_C = 41.0   # "danger" - heat stroke risk


# --- statistics helpers ----------------------------------------------------
def annual_means(df: pd.DataFrame) -> pd.Series:
    """Mean temperature for each calendar year, indexed by integer year."""
    series = df["temperature_2m_mean"].groupby(df.index.year).mean()
    series.index.name = "year"
    return series


def theil_sen(years: np.ndarray, values: np.ndarray) -> float:
    """Robust slope per year: the median of all pairwise slopes.

    Unlike least squares it shrugs off a few extreme years - the right summary
    for noisy series like precipitation or day-to-day swings.
    """
    # Drop non-finite points first: a single NaN year would otherwise poison the
    # median into NaN. The production loader (data._clean) already removes NaN
    # days, so for real builds this is a no-op; it is a guard against any caller
    # that skips that cleaning.
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    good = np.isfinite(years) & np.isfinite(values)
    years, values = years[good], values[good]
    if len(years) < 2:
        return 0.0
    i, j = np.triu_indices(len(years), k=1)
    dx = years[j] - years[i]
    ok = dx != 0
    slopes = (values[j] - values[i])[ok] / dx[ok]
    return float(np.median(slopes)) if slopes.size else 0.0


def robust_trend_line(years: np.ndarray, values: np.ndarray) -> tuple[float, np.ndarray]:
    """Theil-Sen slope-per-year plus the fitted straight line (constant slope).

    The straight line is what "X per decade" means visually; show it dashed
    alongside the LOESS curve so the headline number has something to anchor to.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    slope = theil_sen(years, values)
    # Compute the intercept from the finite points only (theil_sen already does
    # this for the slope); otherwise one NaN year would make the whole fitted
    # line NaN. Production data is pre-cleaned, so this is a guard, not a change.
    good = np.isfinite(years) & np.isfinite(values)
    yg, vg = years[good], values[good]
    intercept = float(np.median(vg - slope * yg)) if len(vg) else 0.0
    return slope, slope * years + intercept


def _mann_kendall_p(values: np.ndarray) -> float:
    """Two-sided p-value for a monotone trend (Mann-Kendall, no SciPy)."""
    n = len(values)
    if n < 4:
        return 1.0
    i, j = np.triu_indices(n, k=1)
    s = float(np.sum(np.sign(values[j] - values[i])))
    var = n * (n - 1) * (2 * n + 5) / 18.0
    if var <= 0:
        return 1.0
    z = (s - np.sign(s)) / math.sqrt(var)  # continuity-corrected
    return math.erfc(abs(z) / math.sqrt(2))  # = 2·(1 − Φ(|z|))


def trend_significance(values: np.ndarray, tr: dict) -> str:
    """Exact Mann-Kendall p-value (so significance never reads as a flat default)."""
    p = _mann_kendall_p(np.asarray(values, dtype=float))
    if p >= 0.05:
        return f"{tr['ns']}, p={p:.2f}"
    if p < 1e-4:
        return f"p={p:.0e}"   # e.g. p=4e-10
    return f"p={p:.4f}".rstrip("0")


def loess(years: np.ndarray, values: np.ndarray,
          bandwidth: float | None = None) -> np.ndarray:
    """Local-linear (LOESS-style) smoother revealing the *shape* of the trend.

    For each year, a Gaussian-weighted linear fit of nearby years - so the
    curve bends with the data (e.g. mid-century pause then steep modern rise)
    instead of forcing one straight line. Dependency-free.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    if bandwidth is None:
        span = float(years.max() - years.min())
        bandwidth = max(span / 8.0, 4.0)
    out = np.empty_like(values)
    for k, x in enumerate(years):
        w = np.exp(-0.5 * ((years - x) / bandwidth) ** 2)
        sw = w.sum()
        mx = (w * years).sum() / sw
        my = (w * values).sum() / sw
        var = (w * (years - mx) ** 2).sum()
        slope = (w * (years - mx) * (values - my)).sum() / var if var > 0 else 0.0
        out[k] = my + slope * (x - mx)
    return out


def summary_stats(df: pd.DataFrame) -> dict:
    """Headline figures used by both the CLI printout and the web page."""
    means = annual_means(df)
    slope = theil_sen(means.index.to_numpy(float), means.to_numpy())
    warmest = int(means.idxmax())
    coldest = int(means.idxmin())
    return {
        "start": int(df.index.year.min()),
        "end": int(df.index.year.max()),
        "days": int(len(df)),
        "mean": float(df["temperature_2m_mean"].mean()),
        "trend_per_decade": float(slope * 10),
        "warmest_year": warmest,
        "warmest_value": float(means[warmest]),
        "coldest_year": coldest,
        "coldest_value": float(means[coldest]),
    }


def monthly_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Year (rows) x month (cols) table of monthly mean temperatures."""
    monthly = df["temperature_2m_mean"].groupby(
        [df.index.year, df.index.month]
    ).mean()
    pivot = monthly.unstack(level=-1)
    pivot.index.name = "year"
    pivot.columns.name = "month"
    return pivot


# --- growing season --------------------------------------------------------
def _season_length(daily_mean: np.ndarray) -> float:
    """Thermal growing-season length (days) for one year's daily-mean series.

    Onset = start of the first ``GROW_RUN``-day run at/above ``GROW_C``; end =
    start of the first such run *below* it after midyear. Returns 0 if the
    season never opens, or the full length if it never closes (warm climates).
    """
    n = len(daily_mean)
    warm = daily_mean >= GROW_C

    def first_run_start(mask: np.ndarray, start: int = 0) -> int | None:
        run = 0
        for i in range(start, len(mask)):
            run = run + 1 if mask[i] else 0
            if run >= GROW_RUN:
                return i - GROW_RUN + 1
        return None

    onset = first_run_start(warm)
    if onset is None:
        return 0.0
    end = first_run_start(~warm, start=n // 2)
    if end is None:
        end = n
    return float(max(0, end - onset))


# --- health-impact index helpers -------------------------------------------
def _doy_threshold(series: pd.Series, pct: float, window: int = 7) -> np.ndarray:
    """Calendar-day percentile of the 1961-1990 baseline (±window-day pool).

    Returns a length-367 array indexed by day-of-year (1..366); the climate-
    relative threshold behind the heat-wave / cold-spell indices (ETCCDI style).
    """
    lo, hi = BASELINE
    base = series[(series.index.year >= lo) & (series.index.year <= hi)]
    by_doy: dict[int, list] = {}
    for d, v in zip(base.index.dayofyear.to_numpy(), base.to_numpy(dtype=float)):
        by_doy.setdefault(int(d), []).append(v)
    thr = np.full(367, np.nan)
    for d in range(1, 367):
        pool: list = []
        for w in range(-window, window + 1):
            pool.extend(by_doy.get((d - 1 + w) % 366 + 1, []))
        if pool:
            thr[d] = np.percentile(pool, pct)
    return thr


def _spell_mask(flag: np.ndarray) -> np.ndarray:
    """True where a day sits inside a run of >= SPELL_RUN consecutive True days."""
    out = np.zeros(len(flag), dtype=bool)
    i, n = 0, len(flag)
    while i < n:
        if flag[i]:
            j = i
            while j < n and flag[j]:
                j += 1
            if j - i >= SPELL_RUN:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out
