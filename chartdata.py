"""Compute interactive-chart payloads (JSON) instead of rendering images.

Every chart that used to be a static matplotlib SVG is now drawn in the browser
with Chart.js (see ``charts.js``). This module reproduces each chart's *data*
— the same statistics ``plots.py`` computed for drawing (annual means, LOESS
smoother, robust Theil–Sen trend, threshold counts, monthly pivots, heatmap
matrices) — and returns it as a JSON-serialisable dict per city.

Localisation reuses the existing machinery: every human-readable label is passed
through a collector (:func:`_mk`), which records how to reproduce the string in
any language. ``build_site`` turns those recordings into the ``{english:
localized}`` map (``window.__ci18n``) the browser already applies — so the same
per-page translation map localises Chart.js labels exactly as it did the SVG
text, with no separate i18n path.

The payload carries English label strings (numbers baked in); the client swaps
them via ``__ci18n`` on load. Data is language-neutral, so it is embedded once
per city and shared across all languages.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import Location
from plots import (
    APPARENT_DANGER_C,
    APPARENT_STRONG_C,
    BASELINE,
    CDD_BASE_C,
    COLD_PCT,
    FREEZE_DAY_C,
    HDD_BASE_C,
    HEAT_PCT,
    HEAVY_RAIN_MM,
    HOT_DAY_C,
    SWING_C,
    TROPICAL_NIGHT_C,
    _doy_threshold,
    _season_length,
    _spell_mask,
    annual_means,
    loess,
    monthly_pivot,
    robust_trend_line,
    trend_significance,
)

_MONTHS = list(range(1, 13))


# --- label collector -------------------------------------------------------
# Mirrors plots._L/_Lf: each translatable string is recorded as (english, key,
# kwargs, closure) so plots.localize_specs() can reproduce it per language.
def _mk():
    """Return (specs, L, Lf): a fresh collector and its two recording helpers."""
    specs: list = []

    def L(tr: dict, key: str, **kw) -> str:
        s = tr[key].format(**kw)
        specs.append((s, key, kw, None))
        return s

    def Lf(tr: dict, fn) -> str:
        s = fn(tr)
        specs.append((s, None, None, fn))
        return s

    return specs, L, Lf


def _floats(arr) -> list:
    """NumPy/pandas array -> plain list of rounded floats (None for NaN)."""
    return [None if (v is None or (isinstance(v, float) and np.isnan(v)))
            else round(float(v), 2) for v in np.asarray(arr, dtype=float)]


def _trend_meta(years: np.ndarray, values: np.ndarray, tr: dict, Lf,
                unit_key: str, decimals: int, label_fn=None) -> dict:
    """Shared: robust trend line + per-decade figure + significance legend."""
    slope, line = robust_trend_line(years, values)
    sig = trend_significance(values, tr)
    per_decade = slope * 10

    def _default(t, s=per_decade, g=sig, uk=unit_key, d=decimals):
        return f"{t['trend']} {s:+.{d}f} {t[uk]} ({g})"

    fn = _default if label_fn is None else label_fn
    return {
        "line": _floats(line),
        "label": Lf(tr, lambda t, f=fn: f(t)),
        "perDecade": round(float(per_decade), 3),
    }


# --- archetype builders ----------------------------------------------------
def _trend_chart(years, values, tr, L, Lf, *, xlabel_key, ylabel_key,
                 raw_color, raw_style, raw_label_key, raw_label_kw,
                 loess_color, trend_unit_key, trend_decimals,
                 trend_label_fn=None):
    """One series drawn as faint raw points/bars + bold LOESS + dashed trend."""
    yf = np.asarray(values, dtype=float)
    yrs = np.asarray(years, dtype=float)
    return {
        "kind": "trend",
        "x": [int(y) for y in years],
        "xlabel": L(tr, xlabel_key),
        "ylabel": L(tr, ylabel_key),
        "raw": {
            "data": _floats(yf),
            "color": raw_color,
            "style": raw_style,
            "label": (L(tr, raw_label_key, **(raw_label_kw or {}))
                      if raw_label_key else None),
        },
        "loess": {"data": _floats(loess(yrs, yf)),
                  "color": loess_color, "label": L(tr, "smoothed")},
        "trend": {**_trend_meta(yrs, yf, tr, Lf, trend_unit_key,
                                trend_decimals, trend_label_fn),
                  "color": "#334155"},
    }


def _multitrend_chart(years, series, tr, L, Lf, *, xlabel_key, ylabel_key):
    """Two+ series, each faint points + LOESS + dashed trend (own legend line).

    ``series`` items: (values, color, label_key, label_kw, unit_key, decimals).
    The legend label carries "<series>: +N <unit>/decade (sig)".
    """
    yrs = np.asarray(years, dtype=float)
    out = []
    for values, color, lkey, lkw, unit_key, dec in series:
        v = np.asarray(values, dtype=float)

        def lf(t, lkey=lkey, lkw=lkw, unit_key=unit_key, dec=dec, v=v, yrs=yrs, tr=tr):
            slope, _ = robust_trend_line(yrs, v)
            sig = trend_significance(v, tr)
            return (f"{t[lkey].format(**lkw)}: {slope * 10:+.{dec}f} "
                    f"{t[unit_key]} ({sig})")

        meta = _trend_meta(yrs, v, tr, Lf, unit_key, dec, label_fn=lf)
        out.append({
            "color": color,
            "raw": _floats(v),
            "loess": _floats(loess(yrs, v)),
            "trend": meta["line"],
            "label": meta["label"],
        })
    return {
        "kind": "multitrend",
        "x": [int(y) for y in years],
        "xlabel": L(tr, xlabel_key),
        "ylabel": L(tr, ylabel_key),
        "series": out,
    }


def _matrix_chart(pivot, values, tr, L, *, step, cbar_key, cbar_kw, diverging):
    """Year×month heatmap: cell rows + range for the client's colour scale."""
    years = [int(y) for y in pivot.index]
    rows = [_floats(r) for r in values]
    finite = values[np.isfinite(values)]
    vmin = float(np.nanmin(finite)) if finite.size else 0.0
    vmax = float(np.nanmax(finite)) if finite.size else 1.0
    return {
        "kind": "matrix",
        "years": years,
        "monthsKey": "months",              # client reads tr.months (localised)
        "xlabel": L(tr, "month"),
        "ylabel": L(tr, "year"),
        "cells": rows,                       # rows[y][m] aligned to years/months
        "vmin": round(vmin, 2),
        "vmax": round(vmax, 2),
        "step": step,
        "diverging": diverging,
        "cbarLabel": L(tr, cbar_key, **(cbar_kw or {})),
    }


# --- per-chart payloads ----------------------------------------------------
def _yearly_trend(df, tr, L, Lf):
    means = annual_means(df)
    return _trend_chart(
        means.index.to_numpy(), means.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key="yearly_ylabel",
        raw_color="#2c7fb8", raw_style="points", raw_label_key="annual_mean",
        raw_label_kw={}, loess_color="#d62728",
        trend_unit_key="per_decade_c", trend_decimals=2)


def _anomalies(df, tr, L, Lf):
    means = annual_means(df)
    lo, hi = BASELINE
    base = means.loc[(means.index >= lo) & (means.index <= hi)]
    baseline = base.mean() if not base.empty else means.mean()
    anomaly = (means - baseline).to_numpy()
    years = [int(y) for y in means.index]
    empty = base.empty

    def ylab(t, base=baseline, lo=lo, hi=hi, e=empty):
        head = t["anomaly_ylabel"]
        tail = (t["vs_full"].format(base=base) if e
                else t["vs_baseline"].format(lo=lo, hi=hi, base=base))
        return f"{head}\n{tail}"

    return {
        "kind": "anomalybars",
        "x": years,
        "xlabel": L(tr, "year"),
        "ylabel": Lf(tr, ylab),
        "values": _floats(anomaly),
        "posColor": "#d62728",
        "negColor": "#2c7fb8",
        "loess": _floats(loess(means.index.to_numpy(float), anomaly)),
    }


def _warming_stripes(df, tr, L, Lf):
    means = annual_means(df)
    lo, hi = BASELINE
    base = means.loc[(means.index >= lo) & (means.index <= hi)]
    baseline = base.mean() if not base.empty else means.mean()
    anomaly = (means - baseline).to_numpy()
    limit = float(np.nanmax(np.abs(anomaly))) or 1.0
    return {
        "kind": "stripes",
        "years": [int(y) for y in means.index],
        "anom": _floats(anomaly),
        "limit": round(limit, 3),
        "xlabel": L(tr, "year"),
        "cbarLabel": L(tr, "stripes_cbar", lo=lo, hi=hi),
    }


def _monthly_heatmap(df, tr, L, Lf):
    pivot = monthly_pivot(df).reindex(columns=_MONTHS)
    return _matrix_chart(pivot, pivot.to_numpy(), tr, L,
                         step=2, cbar_key="heatmap_cbar", cbar_kw={},
                         diverging=False)


def _monthly_anomaly(df, tr, L, Lf):
    pivot = monthly_pivot(df).reindex(columns=_MONTHS)
    lo, hi = BASELINE
    base_rows = pivot.loc[(pivot.index >= lo) & (pivot.index <= hi)]
    baseline = base_rows.mean(axis=0) if not base_rows.empty else pivot.mean(axis=0)
    data = pivot.sub(baseline, axis=1).to_numpy()
    base_label = f"{lo}–{hi}" if not base_rows.empty else tr["full_period"]
    return _matrix_chart(pivot, data, tr, L,
                         step=0.5, cbar_key="anom_heatmap_cbar",
                         cbar_kw={"base": base_label}, diverging=True)


def _threshold_days(df, tr, L, Lf):
    temps = df["temperature_2m_mean"]
    grouped = temps.groupby(df.index.year)
    hot = grouped.agg(lambda s: int((s > HOT_DAY_C).sum()))
    freeze = grouped.agg(lambda s: int((s < FREEZE_DAY_C).sum()))
    years = hot.index.to_numpy()
    return _multitrend_chart(
        years,
        [(hot.to_numpy(), "#d62728", "threshold_hot", {"t": HOT_DAY_C},
          "per_decade_days", 1),
         (freeze.to_numpy(), "#2c7fb8", "threshold_freeze", {"t": FREEZE_DAY_C},
          "per_decade_days", 1)],
        tr, L, Lf, xlabel_key="year", ylabel_key="days_per_year")


def _volatility(df, tr, L, Lf):
    diff = df["temperature_2m_mean"].diff().abs()
    swings = (diff >= SWING_C).groupby(df.index.year).sum()
    yrs = swings.index.to_numpy(dtype=float)
    v = swings.to_numpy(dtype=float)
    return _trend_chart(
        swings.index.to_numpy(), swings.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key="volatility_ylabel",
        raw_color="#7c3aed", raw_style="points", raw_label_key=None,
        raw_label_kw=None, loess_color="#7c3aed",
        trend_unit_key="per_decade_days", trend_decimals=1,
        trend_label_fn=lambda t, yrs=yrs, v=v, tr=tr: (
            f"≥{SWING_C:.0f} °C {t['volatility_jump']}: "
            f"{robust_trend_line(yrs, v)[0] * 10:+.1f} {t['per_decade_days']} "
            f"({trend_significance(v, tr)})"))


def _precip(df_precip, tr, L, Lf):
    annual = df_precip["precipitation_sum"].groupby(df_precip.index.year).sum()
    return _trend_chart(
        annual.index.to_numpy(), annual.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key="precip_ylabel",
        raw_color="#2c7fb8", raw_style="bars", raw_label_key="precip_annual",
        raw_label_kw={}, loess_color="#0f766e",
        trend_unit_key="per_decade_mm", trend_decimals=0)


def _growing_season(df, tr, L, Lf):
    temps = df["temperature_2m_mean"]
    counts = temps.groupby(df.index.year).count()
    lengths = temps.groupby(df.index.year).agg(
        lambda s: _season_length(s.to_numpy(dtype=float)))
    lengths = lengths[counts >= 360]
    return _trend_chart(
        lengths.index.to_numpy(), lengths.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key="season_ylabel",
        raw_color="#15803d", raw_style="points", raw_label_key="season_annual",
        raw_label_kw={}, loess_color="#15803d",
        trend_unit_key="per_decade_days", trend_decimals=1)


def _diurnal_range(df_ext, tr, L, Lf):
    dtr = df_ext["temperature_2m_max"] - df_ext["temperature_2m_min"]
    annual = dtr.groupby(df_ext.index.year).mean()
    return _trend_chart(
        annual.index.to_numpy(), annual.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key="dtr_ylabel",
        raw_color="#7c3aed", raw_style="points", raw_label_key="dtr_annual",
        raw_label_kw={}, loess_color="#7c3aed",
        trend_unit_key="per_decade_c", trend_decimals=2)


def _seasonal_shift(df, tr, L, Lf):
    means = df["temperature_2m_mean"]
    years = means.index.year
    y0, y1 = int(years.min()), int(years.max())
    early_lo, early_hi = y0, y0 + 9
    late_lo, late_hi = y1 - 9, y1
    early = means[(years >= early_lo) & (years <= early_hi)]
    late = means[(years >= late_lo) & (years <= late_hi)]
    em = early.groupby(early.index.month).mean().reindex(_MONTHS).to_numpy()
    lm = late.groupby(late.index.month).mean().reindex(_MONTHS).to_numpy()
    return {
        "kind": "seasonshift",
        "monthsKey": "months",
        "xlabel": L(tr, "month"),
        "ylabel": L(tr, "seasonshift_ylabel"),
        "early": {"data": _floats(em), "color": "#2c7fb8",
                  "label": Lf(tr, lambda t, a=early_lo, b=early_hi: f"{a}–{b}")},
        "late": {"data": _floats(lm), "color": "#d62728",
                 "label": Lf(tr, lambda t, a=late_lo, b=late_hi: f"{a}–{b}")},
    }


def _degree_days(df, tr, L, Lf):
    mean = df["temperature_2m_mean"]
    hdd = (HDD_BASE_C - mean).clip(lower=0).groupby(mean.index.year).sum()
    cdd = (mean - CDD_BASE_C).clip(lower=0).groupby(mean.index.year).sum()
    return _multitrend_chart(
        hdd.index.to_numpy(),
        [(hdd.to_numpy(), "#1d4ed8", "hdd_label", {"t": HDD_BASE_C},
          "per_decade_dd", 0),
         (cdd.to_numpy(), "#b91c1c", "cdd_label", {"t": CDD_BASE_C},
          "per_decade_dd", 0)],
        tr, L, Lf, xlabel_key="year", ylabel_key="dd_ylabel")


def _count_single(annual, color, series_key, series_kw, tr, L, Lf, ylabel_key):
    """A one-series annual-count chart (heatwave/tropic/coldspell/heavyrain)."""
    return _trend_chart(
        annual.index.to_numpy(), annual.to_numpy(), tr, L, Lf,
        xlabel_key="year", ylabel_key=ylabel_key,
        raw_color=color, raw_style="points", raw_label_key=series_key,
        raw_label_kw=series_kw, loess_color=color,
        trend_unit_key="per_decade_days", trend_decimals=1)


def _heatwave(df_ext, tr, L, Lf):
    tmax = df_ext["temperature_2m_max"]
    thr = _doy_threshold(tmax, HEAT_PCT)
    doy = tmax.index.dayofyear.to_numpy()
    spell = _spell_mask(tmax.to_numpy(dtype=float) > thr[doy])
    annual = pd.Series(spell, index=tmax.index).groupby(tmax.index.year).sum()
    return _count_single(annual, "#b91c1c", "heatwave_series", {}, tr, L, Lf,
                         "heatwave_ylabel")


def _tropical_nights(df_ext, tr, L, Lf):
    tmin = df_ext["temperature_2m_min"]
    annual = (tmin >= TROPICAL_NIGHT_C).groupby(tmin.index.year).sum()
    return _count_single(annual, "#c2410c", "tropic_series",
                         {"t": TROPICAL_NIGHT_C}, tr, L, Lf, "tropic_ylabel")


def _cold_spells(df_ext, tr, L, Lf):
    tmin = df_ext["temperature_2m_min"]
    thr = _doy_threshold(tmin, COLD_PCT)
    doy = tmin.index.dayofyear.to_numpy()
    spell = _spell_mask(tmin.to_numpy(dtype=float) < thr[doy])
    annual = pd.Series(spell, index=tmin.index).groupby(tmin.index.year).sum()
    return _count_single(annual, "#1d4ed8", "coldspell_series", {}, tr, L, Lf,
                         "coldspell_ylabel")


def _heavy_rain(df_precip, tr, L, Lf):
    p = df_precip["precipitation_sum"]
    annual = (p >= HEAVY_RAIN_MM).groupby(p.index.year).sum()
    return _count_single(annual, "#0f766e", "heavyrain_series",
                         {"mm": HEAVY_RAIN_MM}, tr, L, Lf, "heavyrain_ylabel")


def _heat_index(df_app, tr, L, Lf):
    app = df_app["apparent_temperature_max"]
    strong = (app >= APPARENT_STRONG_C).groupby(app.index.year).sum()
    danger = (app >= APPARENT_DANGER_C).groupby(app.index.year).sum()
    return _multitrend_chart(
        strong.index.to_numpy(),
        [(strong.to_numpy(), "#f59e0b", "heat_strong", {"t": APPARENT_STRONG_C},
          "per_decade_days", 1),
         (danger.to_numpy(), "#b91c1c", "heat_danger", {"t": APPARENT_DANGER_C},
          "per_decade_days", 1)],
        tr, L, Lf, xlabel_key="year", ylabel_key="heatindex_ylabel")


# id -> (builder, required-frame). "mean" always present; others gate on data.
_CHARTS = [
    ("yearly-trend", _yearly_trend, "mean"),
    ("anomalies", _anomalies, "mean"),
    ("warming-stripes", _warming_stripes, "mean"),
    ("monthly-heatmap", _monthly_heatmap, "mean"),
    ("monthly-anomaly", _monthly_anomaly, "mean"),
    ("threshold-days", _threshold_days, "mean"),
    ("growing-season", _growing_season, "mean"),
    ("seasonal-shift", _seasonal_shift, "mean"),
    ("volatility", _volatility, "mean"),
    ("degree-days", _degree_days, "mean"),
    ("precipitation", _precip, "precip"),
    ("heavy-rain", _heavy_rain, "precip"),
    ("diurnal-range", _diurnal_range, "ext"),
    ("heatwave", _heatwave, "ext"),
    ("tropical-nights", _tropical_nights, "ext"),
    ("cold-spells", _cold_spells, "ext"),
    ("heat-index", _heat_index, "app"),
]


def compute_payloads(df: pd.DataFrame, location: Location, tr: dict, *,
                     df_precip: pd.DataFrame | None = None,
                     df_ext: pd.DataFrame | None = None,
                     df_app: pd.DataFrame | None = None):
    """Return (payloads, specs) for one city.

    ``payloads``: ``{chart_id: <json-serialisable dict>}`` — language-neutral
    data + English label strings, embedded once per city.
    ``specs``: ``{chart_id: [(english, key, kw, closure), ...]}`` — fed to
    ``plots.localize_specs`` per language to build the ``__ci18n`` swap map.
    """
    frames = {"mean": df, "precip": df_precip, "ext": df_ext, "app": df_app}
    payloads: dict[str, dict] = {}
    specs: dict[str, list] = {}
    for chart_id, builder, need in _CHARTS:
        frame = frames.get(need)
        if frame is None:
            continue
        coll, L, Lf = _mk()
        payloads[chart_id] = builder(frame, tr, L, Lf)
        specs[chart_id] = coll
    return payloads, specs
