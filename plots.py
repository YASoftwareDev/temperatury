"""Plotting of temperature distribution and long-term change.

Six views are produced:

* ``plot_threshold_days``          -- hot (>18°C) & freezing (<0°C) days per year
* ``plot_yearly_trend``            -- annual mean + LOESS smoother & robust trend
* ``plot_anomalies``               -- annual anomaly vs. a 1961-1990 baseline
* ``plot_monthly_heatmap``         -- year x month grid of monthly means
* ``plot_monthly_anomaly_heatmap`` -- per-month anomaly vs. 1961-1990
* ``plot_monthly_range``           -- per-month min-max envelope + latest year

Every plotting helper takes a translation table ``tr`` (see :mod:`i18n`) so all
labels are localised. ``build_dashboard`` arranges the views in one figure; each
helper can also draw onto a caller-supplied Axes for standalone PNGs.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless: render straight to files, no display needed
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.figure import Figure

from config import Location

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


# --- statistics helpers ----------------------------------------------------
def annual_means(df: pd.DataFrame) -> pd.Series:
    """Mean temperature for each calendar year, indexed by integer year."""
    series = df["temperature_2m_mean"].groupby(df.index.year).mean()
    series.index.name = "year"
    return series


def theil_sen(years: np.ndarray, values: np.ndarray) -> float:
    """Robust slope per year: the median of all pairwise slopes.

    Unlike least squares it shrugs off a few extreme years — the right summary
    for noisy series like precipitation or day-to-day swings.
    """
    i, j = np.triu_indices(len(years), k=1)
    dx = years[j] - years[i]
    ok = dx != 0
    slopes = (values[j] - values[i])[ok] / dx[ok]
    return float(np.median(slopes)) if slopes.size else 0.0


def robust_trend_line(years: np.ndarray, values: np.ndarray) -> tuple[float, np.ndarray]:
    """Theil–Sen slope-per-year plus the fitted straight line (constant slope).

    The straight line is what "X per decade" means visually; show it dashed
    alongside the LOESS curve so the headline number has something to anchor to.
    """
    slope = theil_sen(years, values)
    intercept = float(np.median(values - slope * years))
    return slope, slope * years + intercept


def _mann_kendall_p(values: np.ndarray) -> float:
    """Two-sided p-value for a monotone trend (Mann–Kendall, no SciPy)."""
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
    """Exact Mann–Kendall p-value (so significance never reads as a flat default)."""
    p = _mann_kendall_p(np.asarray(values, dtype=float))
    if p >= 0.05:
        return f"{tr['ns']}, p={p:.2f}"
    if p < 1e-4:
        return f"p={p:.0e}"   # e.g. p=4e-10
    return f"p={p:.4f}".rstrip("0")


def loess(years: np.ndarray, values: np.ndarray,
          bandwidth: float | None = None) -> np.ndarray:
    """Local-linear (LOESS-style) smoother revealing the *shape* of the trend.

    For each year, a Gaussian-weighted linear fit of nearby years — so the
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


# --- individual plots ------------------------------------------------------
def plot_threshold_days(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Count of hot (>18 °C) and freezing (<0 °C) days per year, with trends.

    A concrete, fully measurable view of the distribution's tails: as the
    climate warms, hot days climb and freezing days fall — both read straight
    off the day-count axis, each with its own per-decade rate.
    """
    temps = df["temperature_2m_mean"]
    grouped = temps.groupby(df.index.year)
    hot = grouped.agg(lambda s: int((s > HOT_DAY_C).sum()))
    freeze = grouped.agg(lambda s: int((s < FREEZE_DAY_C).sum()))
    years = hot.index.to_numpy(dtype=float)

    series = [
        (hot, "#d62728", tr["threshold_hot"].format(t=HOT_DAY_C)),
        (freeze, "#2c7fb8", tr["threshold_freeze"].format(t=FREEZE_DAY_C)),
    ]
    for data, color, label in series:
        values = data.to_numpy(dtype=float)
        slope, line = robust_trend_line(years, values)
        sig = trend_significance(values, tr)
        # Faint raw counts, a bold LOESS smoother (reveals the non-linear
        # shape of the change), and a thin dashed robust trend line that
        # carries the single per-decade rate + significance in the legend.
        ax.plot(years, values, color=color, linewidth=0.8, marker="o",
                markersize=2.0, alpha=0.25)
        ax.plot(years, loess(years, values), color=color, linewidth=2.6,
                label=f"{label}: {slope * 10:+.1f} {tr['per_decade_days']} ({sig})")
        ax.plot(years, line, color=color, linewidth=1.3, linestyle="--",
                alpha=0.8)

    ax.set_title(tr["threshold_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(tr["days_per_year"])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.margins(x=0.01)


def plot_yearly_trend(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Annual mean temperature with a LOESS smoother + robust trend figure."""
    means = annual_means(df)
    years = means.index.to_numpy(dtype=float)
    values = means.to_numpy()
    slope, line = robust_trend_line(years, values)
    sig = trend_significance(values, tr)

    ax.plot(years, values, marker="o", markersize=3, color="#2c7fb8",
            linewidth=1, alpha=0.45, label=tr["annual_mean"])
    ax.plot(years, loess(years, values), color="#d62728", linewidth=2.6,
            label=tr["smoothed"])
    ax.plot(years, line, color="#334155", linewidth=1.6, linestyle="--",
            label=f"{tr['trend']} {slope * 10:+.2f} {tr['per_decade_c']} ({sig})")
    ax.set_title(tr["yearly_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(tr["yearly_ylabel"])
    ax.legend()
    ax.grid(True, alpha=0.3)


def plot_anomalies(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Annual anomaly relative to the 1961-1990 mean (blue cooler, red warmer)."""
    means = annual_means(df)
    lo, hi = BASELINE
    baseline_years = means.loc[(means.index >= lo) & (means.index <= hi)]
    baseline = baseline_years.mean() if not baseline_years.empty else means.mean()

    anomaly = means - baseline
    colors = np.where(anomaly.to_numpy() >= 0, "#d62728", "#2c7fb8")
    ax.bar(means.index, anomaly.to_numpy(), color=colors, width=0.9)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.plot(means.index, loess(means.index.to_numpy(float), anomaly.to_numpy()),
            color="#0f172a", linewidth=2.0)
    label = (
        tr["vs_baseline"].format(lo=lo, hi=hi, base=baseline)
        if not baseline_years.empty
        else tr["vs_full"].format(base=baseline)
    )
    ax.set_title(tr["anomaly_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(f"{tr['anomaly_ylabel']}\n{label}")
    ax.grid(True, axis="y", alpha=0.3)


def plot_monthly_heatmap(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Year x month heatmap showing how each month evolves over the years."""
    pivot = monthly_pivot(df)
    data = pivot.to_numpy()

    # Discrete 2 °C bands in a high-contrast diverging palette: each band is a
    # distinct, temperature-intuitive colour (blue cold → yellow → red hot),
    # so individual months and their drift across years are easy to tell apart.
    step = 2
    vmin = np.floor(np.nanmin(data) / step) * step
    vmax = np.ceil(np.nanmax(data) / step) * step
    levels = np.arange(vmin, vmax + step, step)
    cmap = plt.get_cmap("RdYlBu_r", len(levels) - 1)
    norm = BoundaryNorm(levels, ncolors=cmap.N)

    image = ax.imshow(
        data,
        aspect="auto",
        cmap=cmap,
        norm=norm,
        origin="lower",
        interpolation="nearest",
        extent=(0.5, 12.5, pivot.index.min() - 0.5, pivot.index.max() + 0.5),
    )
    ax.set_title(tr["heatmap_title"].format(name=location.name))
    ax.set_xlabel(tr["month"])
    ax.set_ylabel(tr["year"])
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(tr["months"])
    colorbar = ax.figure.colorbar(
        image, ax=ax, fraction=0.046, pad=0.04, ticks=levels[::2]
    )
    colorbar.set_label(tr["heatmap_cbar"])


def plot_monthly_anomaly_heatmap(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Per-month anomaly heatmap: each month normalised to its 1961-1990 mean.

    Removing each month's own seasonal mean isolates the warming signal, so a
    centred diverging palette (white = no change) reveals how much every month
    has shifted — even small drifts the absolute heatmap hides.
    """
    pivot = monthly_pivot(df)
    lo, hi = BASELINE
    base_rows = pivot.loc[(pivot.index >= lo) & (pivot.index <= hi)]
    baseline = base_rows.mean(axis=0) if not base_rows.empty else pivot.mean(axis=0)
    data = pivot.sub(baseline, axis=1).to_numpy()

    # Symmetric 0.5 °C bands around zero so warming/cooling read at a glance.
    # A few extreme winter anomalies would otherwise stretch the scale and wash
    # out the smaller summer signal, so cap the range at the 96th percentile and
    # let outliers saturate (arrows on the colour bar).
    step = 0.5
    robust = np.nanpercentile(np.abs(data), 96)
    vmax = max(np.ceil(robust / step) * step, 2 * step)
    levels = np.arange(-vmax, vmax + step, step)
    cmap = plt.get_cmap("RdBu_r")
    norm = BoundaryNorm(levels, ncolors=cmap.N, extend="both")

    image = ax.imshow(
        data,
        aspect="auto",
        cmap=cmap,
        norm=norm,
        origin="lower",
        interpolation="nearest",
        extent=(0.5, 12.5, pivot.index.min() - 0.5, pivot.index.max() + 0.5),
    )
    base_label = f"{lo}–{hi}" if not base_rows.empty else tr["full_period"]
    ax.set_title(tr["anom_heatmap_title"].format(base=base_label, name=location.name))
    ax.set_xlabel(tr["month"])
    ax.set_ylabel(tr["year"])
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(tr["months"])
    colorbar = ax.figure.colorbar(
        image, ax=ax, fraction=0.046, pad=0.04, ticks=levels[::2]
    )
    colorbar.set_label(tr["anom_heatmap_cbar"].format(base=base_label))


def plot_monthly_range(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Each month's min–max envelope across all years, with the latest year.

    The shaded band is the full historical range of monthly means; the bold
    line is the most recent year — at a glance you see whether 'now' sits near
    the warm (top) edge of everything on record.
    """
    pivot = monthly_pivot(df)
    months = list(range(1, 13))
    mn = pivot.min(axis=0).to_numpy()
    mx = pivot.max(axis=0).to_numpy()
    avg = pivot.mean(axis=0).to_numpy()
    start, latest_year = int(pivot.index.min()), int(pivot.index.max())
    latest = pivot.loc[latest_year].to_numpy()

    ax.fill_between(months, mn, mx, color="#94a3b8", alpha=0.35,
                    label=tr["range_min_max"].format(start=start, end=latest_year))
    ax.plot(months, mx, color="#94a3b8", linewidth=0.8)
    ax.plot(months, mn, color="#94a3b8", linewidth=0.8)
    ax.plot(months, avg, color="#334155", linewidth=1.5, linestyle="--",
            label=tr["range_average"])
    ax.plot(months, latest, color="#d62728", linewidth=2.4, marker="o",
            markersize=4, label=tr["range_latest"].format(year=latest_year))
    ax.set_title(tr["range_title"].format(name=location.name))
    ax.set_xlabel(tr["month"])
    ax.set_ylabel(tr["range_ylabel"])
    ax.set_xticks(months)
    ax.set_xticklabels(tr["months"])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.margins(x=0.01)


def plot_record_range(
    df_ext: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Per-month all-time record daily high/low, with the latest year's extremes.

    Uses daily max/min (not means): the band is the hottest day and coldest day
    ever recorded in each month; the bold lines are the latest year's monthly
    extremes — so you see how close 'now' came to the records.
    """
    months = list(range(1, 13))
    by_month = df_ext.index.month
    rec_high = df_ext["temperature_2m_max"].groupby(by_month).max().reindex(months)
    rec_low = df_ext["temperature_2m_min"].groupby(by_month).min().reindex(months)

    latest_year = int(df_ext.index.year.max())
    recent = df_ext[df_ext.index.year == latest_year]
    rm = recent.index.month
    lat_high = recent["temperature_2m_max"].groupby(rm).max().reindex(months)
    lat_low = recent["temperature_2m_min"].groupby(rm).min().reindex(months)
    start = int(df_ext.index.year.min())

    ax.fill_between(months, rec_low.to_numpy(), rec_high.to_numpy(),
                    color="#cbd5e1", alpha=0.55,
                    label=tr["record_band"].format(start=start, end=latest_year))
    ax.plot(months, rec_high.to_numpy(), color="#b91c1c", linewidth=1.0)
    ax.plot(months, rec_low.to_numpy(), color="#1d4ed8", linewidth=1.0)
    ax.plot(months, lat_high.to_numpy(), color="#d62728", linewidth=2.2,
            marker="o", markersize=4,
            label=tr["record_latest_high"].format(year=latest_year))
    ax.plot(months, lat_low.to_numpy(), color="#2c7fb8", linewidth=2.2,
            marker="o", markersize=4,
            label=tr["record_latest_low"].format(year=latest_year))
    ax.set_title(tr["record_title"].format(name=location.name))
    ax.set_xlabel(tr["month"])
    ax.set_ylabel(tr["record_ylabel"])
    ax.set_xticks(months)
    ax.set_xticklabels(tr["months"])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.margins(x=0.01)


def plot_temp_volatility(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """How often big day-to-day temperature jumps happen, per year.

    Counts days whose daily mean differs from the previous day by at least
    ``SWING_C`` °C — a concrete measure of temperature variability ("how jumpy
    is the weather?") — with a trend line.
    """
    diff = df["temperature_2m_mean"].diff().abs()
    swings = (diff >= SWING_C).groupby(df.index.year).sum()
    years = swings.index.to_numpy(dtype=float)
    values = swings.to_numpy(dtype=float)
    slope, line = robust_trend_line(years, values)
    sig = trend_significance(values, tr)

    ax.plot(years, values, color="#7c3aed", linewidth=1.0, marker="o",
            markersize=2.5, alpha=0.35)
    ax.plot(years, loess(years, values), color="#7c3aed", linewidth=2.6,
            label=tr["smoothed"])
    ax.plot(years, line, color="#334155", linewidth=1.6, linestyle="--",
            label=(f"≥{SWING_C:.0f} °C {tr['volatility_jump']}: "
                   f"{slope * 10:+.1f} {tr['per_decade_days']} ({sig})"))
    ax.set_title(tr["volatility_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(tr["volatility_ylabel"])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.margins(x=0.01)


def plot_precip(
    df_precip: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Total annual precipitation per year, with a trend line."""
    annual = df_precip["precipitation_sum"].groupby(df_precip.index.year).sum()
    years = annual.index.to_numpy(dtype=float)
    values = annual.to_numpy(dtype=float)
    slope, line = robust_trend_line(years, values)
    sig = trend_significance(values, tr)

    ax.bar(years, values, color="#2c7fb8", alpha=0.45, width=0.9,
           label=tr["precip_annual"])
    ax.plot(years, loess(years, values), color="#0f766e", linewidth=2.6,
            label=tr["smoothed"])
    ax.plot(years, line, color="#d62728", linewidth=1.8, linestyle="--",
            label=f"{tr['trend']} {slope * 10:+.0f} {tr['per_decade_mm']} ({sig})")
    ax.set_title(tr["precip_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(tr["precip_ylabel"])
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="best")
    ax.margins(x=0.01)


def plot_warming_stripes(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Ed-Hawkins 'warming stripes': one stripe per year, coloured by anomaly.

    The most legible climate graphic there is — no axes to read, just a wall of
    colour shifting from blue (cool years) to red (warm). Same anomaly data as
    the bar chart, but stripped to pure colour so the long-run shift dominates.
    """
    means = annual_means(df)
    lo, hi = BASELINE
    baseline_years = means.loc[(means.index >= lo) & (means.index <= hi)]
    baseline = baseline_years.mean() if not baseline_years.empty else means.mean()
    anomaly = (means - baseline).to_numpy()
    years = means.index.to_numpy()

    # Symmetric colour scale around zero so blue/red are balanced.
    limit = float(np.nanmax(np.abs(anomaly))) or 1.0
    ax.imshow(anomaly[np.newaxis, :], cmap="RdBu_r", aspect="auto",
              vmin=-limit, vmax=limit,
              extent=(years[0] - 0.5, years[-1] + 0.5, 0, 1))
    ax.set_yticks([])
    ax.set_xlabel(tr["year"])
    ax.set_title(tr["stripes_title"].format(name=location.name))
    sm = plt.cm.ScalarMappable(cmap="RdBu_r",
                               norm=plt.Normalize(vmin=-limit, vmax=limit))
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.05, pad=0.02)
    cbar.set_label(tr["stripes_cbar"].format(lo=lo, hi=hi))


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


def plot_growing_season(
    df: pd.DataFrame, location: Location, ax: plt.Axes, tr: dict
) -> None:
    """Length of the thermal growing season (daily mean ≥ 5 °C) per year.

    A concrete agricultural consequence of warming: the frost-free growing
    window lengthening decade by decade. Bold LOESS curve + dashed robust trend.
    """
    temps = df["temperature_2m_mean"]
    counts = temps.groupby(df.index.year).count()
    lengths = temps.groupby(df.index.year).agg(
        lambda s: _season_length(s.to_numpy(dtype=float)))
    # Only whole years (drop a partial current year that would dip artificially).
    full = counts >= 360
    lengths = lengths[full]
    years = lengths.index.to_numpy(dtype=float)
    values = lengths.to_numpy(dtype=float)
    slope, line = robust_trend_line(years, values)
    sig = trend_significance(values, tr)

    ax.plot(years, values, color="#15803d", linewidth=0.8, marker="o",
            markersize=2.0, alpha=0.3, label=tr["season_annual"])
    ax.plot(years, loess(years, values), color="#15803d", linewidth=2.6,
            label=tr["smoothed"])
    ax.plot(years, line, color="#b45309", linewidth=1.6, linestyle="--",
            label=f"{tr['trend']} {slope * 10:+.1f} {tr['per_decade_days']} ({sig})")
    ax.set_title(tr["season_title"].format(name=location.name))
    ax.set_xlabel(tr["year"])
    ax.set_ylabel(tr["season_ylabel"])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.margins(x=0.01)


# --- composition -----------------------------------------------------------
def build_dashboard(df: pd.DataFrame, location: Location, tr: dict) -> Figure:
    """Arrange all five views in a single 3x2 figure (one slot left blank)."""
    fig, axes = plt.subplots(3, 2, figsize=(16, 16))
    plot_threshold_days(df, location, axes[0, 0], tr)
    plot_yearly_trend(df, location, axes[0, 1], tr)
    plot_anomalies(df, location, axes[1, 0], tr)
    plot_monthly_heatmap(df, location, axes[1, 1], tr)
    plot_monthly_anomaly_heatmap(df, location, axes[2, 0], tr)
    plot_monthly_range(df, location, axes[2, 1], tr)
    start, end = df.index.year.min(), df.index.year.max()
    fig.suptitle(
        tr["dashboard_suptitle"].format(name=location.name, start=start, end=end),
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def save_all(
    df: pd.DataFrame,
    location: Location,
    output_dir: Path,
    tr: dict,
    df_precip: pd.DataFrame | None = None,
) -> list[Path]:
    """Render the dashboard plus each standalone panel; return written paths.

    The monthly-range and record charts are interactive on the web (see
    :mod:`interactive`), so only their dashboard versions are rendered here.
    ``df_precip`` adds the annual precipitation panel when its data is given.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.slug
    written: list[Path] = []

    dashboard = build_dashboard(df, location, tr)
    dash_path = output_dir / f"{slug}_dashboard.png"
    dashboard.savefig(dash_path, dpi=120)
    plt.close(dashboard)
    written.append(dash_path)

    panels = {
        "threshold-days": plot_threshold_days,
        "yearly-trend": plot_yearly_trend,
        "warming-stripes": plot_warming_stripes,
        "anomalies": plot_anomalies,
        "monthly-heatmap": plot_monthly_heatmap,
        "monthly-anomaly": plot_monthly_anomaly_heatmap,
        "growing-season": plot_growing_season,
        "volatility": plot_temp_volatility,
    }
    for name, draw in panels.items():
        fig, ax = plt.subplots(figsize=(9, 5.5))
        draw(df, location, ax, tr)
        fig.tight_layout()
        path = output_dir / f"{slug}_{name}.png"
        # Higher DPI than the dashboard so panels stay crisp when opened full-page.
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)

    if df_precip is not None:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        plot_precip(df_precip, location, ax, tr)
        fig.tight_layout()
        path = output_dir / f"{slug}_precipitation.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)

    return written
