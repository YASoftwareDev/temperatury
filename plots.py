"""Plotting of temperature distribution and long-term change.

Five views are produced:

* ``plot_threshold_days``          -- hot (>18°C) & freezing (<0°C) days per year
* ``plot_yearly_trend``            -- annual mean per year + least-squares trend
* ``plot_anomalies``               -- annual anomaly vs. a 1961-1990 baseline
* ``plot_monthly_heatmap``         -- year x month grid of monthly means
* ``plot_monthly_anomaly_heatmap`` -- per-month anomaly vs. 1961-1990

``build_dashboard`` arranges them in one figure; each helper can also draw
onto a caller-supplied Axes for standalone PNGs.
"""

from __future__ import annotations

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


# --- statistics helpers ----------------------------------------------------
def annual_means(df: pd.DataFrame) -> pd.Series:
    """Mean temperature for each calendar year, indexed by integer year."""
    series = df["temperature_2m_mean"].groupby(df.index.year).mean()
    series.index.name = "year"
    return series


def linear_trend(years: np.ndarray, values: np.ndarray) -> tuple[float, np.ndarray]:
    """Fit ``values ~ years`` and return (slope_per_year, fitted_line)."""
    slope, intercept = np.polyfit(years, values, 1)
    return slope, slope * years + intercept


def summary_stats(df: pd.DataFrame) -> dict:
    """Headline figures used by both the CLI printout and the web page."""
    means = annual_means(df)
    slope, _ = linear_trend(means.index.to_numpy(float), means.to_numpy())
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
def plot_threshold_days(df: pd.DataFrame, location: Location, ax: plt.Axes) -> None:
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
        (hot, "#d62728", f"hot days (>{HOT_DAY_C:.0f} °C)"),
        (freeze, "#2c7fb8", f"freezing days (<{FREEZE_DAY_C:.0f} °C)"),
    ]
    for data, color, label in series:
        values = data.to_numpy(dtype=float)
        slope, fitted = linear_trend(years, values)
        ax.plot(years, values, color=color, linewidth=1.0, marker="o",
                markersize=2.5, alpha=0.4)
        ax.plot(years, fitted, color=color, linewidth=2.6,
                label=f"{label}: {slope * 10:+.1f} days / decade")

    ax.set_title(f"Hot & freezing days per year — {location.name}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Days per year")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.margins(x=0.01)


def plot_yearly_trend(df: pd.DataFrame, location: Location, ax: plt.Axes) -> None:
    """Annual mean temperature per year with a least-squares trend line."""
    means = annual_means(df)
    years = means.index.to_numpy(dtype=float)
    values = means.to_numpy()
    slope, fitted = linear_trend(years, values)

    ax.plot(years, values, marker="o", markersize=3, color="#2c7fb8",
            linewidth=1, label="annual mean")
    ax.plot(years, fitted, color="#d62728", linewidth=2.5,
            label=f"trend {slope * 10:+.2f} °C / decade")
    ax.set_title(f"Annual mean temperature through the years — {location.name}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual mean temperature (°C)")
    ax.legend()
    ax.grid(True, alpha=0.3)


def plot_anomalies(df: pd.DataFrame, location: Location, ax: plt.Axes) -> None:
    """Annual anomaly relative to the 1961-1990 mean (blue cooler, red warmer)."""
    means = annual_means(df)
    lo, hi = BASELINE
    baseline_years = means.loc[(means.index >= lo) & (means.index <= hi)]
    baseline = baseline_years.mean() if not baseline_years.empty else means.mean()

    anomaly = means - baseline
    colors = np.where(anomaly.to_numpy() >= 0, "#d62728", "#2c7fb8")
    ax.bar(means.index, anomaly.to_numpy(), color=colors, width=0.9)
    ax.axhline(0, color="black", linewidth=0.8)
    label = (
        f"vs. {lo}-{hi} mean ({baseline:.1f} °C)"
        if not baseline_years.empty
        else f"vs. full-period mean ({baseline:.1f} °C)"
    )
    ax.set_title(f"Annual temperature anomaly — {location.name}")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Anomaly (°C)\n{label}")
    ax.grid(True, axis="y", alpha=0.3)


def plot_monthly_heatmap(df: pd.DataFrame, location: Location, ax: plt.Axes) -> None:
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
    ax.set_title(f"Monthly mean temperature by year — {location.name}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
    colorbar = ax.figure.colorbar(
        image, ax=ax, fraction=0.046, pad=0.04, ticks=levels[::2]
    )
    colorbar.set_label("Monthly mean (°C)")


def plot_monthly_anomaly_heatmap(
    df: pd.DataFrame, location: Location, ax: plt.Axes
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
    base_label = f"{lo}–{hi}" if not base_rows.empty else "full-period"
    ax.set_title(f"Monthly anomaly vs. {base_label} — {location.name}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
    colorbar = ax.figure.colorbar(
        image, ax=ax, fraction=0.046, pad=0.04, ticks=levels[::2]
    )
    colorbar.set_label(f"Anomaly vs. {base_label} (°C)")


# --- composition -----------------------------------------------------------
def build_dashboard(df: pd.DataFrame, location: Location) -> Figure:
    """Arrange all four views in a single 2x2 figure."""
    fig, axes = plt.subplots(3, 2, figsize=(16, 16))
    plot_threshold_days(df, location, axes[0, 0])
    plot_yearly_trend(df, location, axes[0, 1])
    plot_anomalies(df, location, axes[1, 0])
    plot_monthly_heatmap(df, location, axes[1, 1])
    plot_monthly_anomaly_heatmap(df, location, axes[2, 0])
    axes[2, 1].axis("off")  # no fifth chart for this slot
    start, end = df.index.year.min(), df.index.year.max()
    fig.suptitle(
        f"{location.name} temperatures {start}-{end} "
        f"(source: Open-Meteo reanalysis)",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def save_all(df: pd.DataFrame, location: Location, output_dir: Path) -> list[Path]:
    """Render the dashboard plus each standalone panel; return written paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.slug
    written: list[Path] = []

    dashboard = build_dashboard(df, location)
    dash_path = output_dir / f"{slug}_dashboard.png"
    dashboard.savefig(dash_path, dpi=120)
    plt.close(dashboard)
    written.append(dash_path)

    panels = {
        "threshold-days": plot_threshold_days,
        "yearly-trend": plot_yearly_trend,
        "anomalies": plot_anomalies,
        "monthly-heatmap": plot_monthly_heatmap,
        "monthly-anomaly": plot_monthly_anomaly_heatmap,
    }
    for name, draw in panels.items():
        fig, ax = plt.subplots(figsize=(9, 5.5))
        draw(df, location, ax)
        fig.tight_layout()
        path = output_dir / f"{slug}_{name}.png"
        # Higher DPI than the dashboard so panels stay crisp when opened full-page.
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)

    return written
