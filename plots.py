"""Plotting of temperature distribution and long-term change.

Four views are produced:

* ``plot_histogram``        -- distribution of daily mean temperatures
* ``plot_yearly_trend``     -- annual mean per year + least-squares trend
* ``plot_anomalies``        -- annual anomaly vs. a 1961-1990 baseline
* ``plot_monthly_heatmap``  -- year x month grid of monthly means

``build_dashboard`` arranges all four in one figure; each helper can also
draw onto a caller-supplied Axes for standalone PNGs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless: render straight to files, no display needed
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from config import Location

# Standard WMO climatological reference period for anomalies.
BASELINE = (1961, 1990)


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
def plot_histogram(df: pd.DataFrame, location: Location, ax: plt.Axes) -> None:
    """Distribution of daily mean temperatures with the mean marked."""
    temps = df["temperature_2m_mean"]
    ax.hist(temps, bins=40, color="#4c8bf5", edgecolor="white", alpha=0.9)
    ax.axvline(
        temps.mean(),
        color="#d62728",
        linestyle="--",
        linewidth=2,
        label=f"mean {temps.mean():.1f} °C",
    )
    ax.set_title(f"Distribution of daily mean temperature — {location.name}")
    ax.set_xlabel("Daily mean temperature (°C)")
    ax.set_ylabel("Number of days")
    ax.legend()


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
    image = ax.imshow(
        data,
        aspect="auto",
        cmap="RdBu_r",
        origin="lower",
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
    colorbar = ax.figure.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Monthly mean (°C)")


# --- composition -----------------------------------------------------------
def build_dashboard(df: pd.DataFrame, location: Location) -> Figure:
    """Arrange all four views in a single 2x2 figure."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    plot_histogram(df, location, axes[0, 0])
    plot_yearly_trend(df, location, axes[0, 1])
    plot_anomalies(df, location, axes[1, 0])
    plot_monthly_heatmap(df, location, axes[1, 1])
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
        "histogram": plot_histogram,
        "yearly-trend": plot_yearly_trend,
        "anomalies": plot_anomalies,
        "monthly-heatmap": plot_monthly_heatmap,
    }
    for name, draw in panels.items():
        fig, ax = plt.subplots(figsize=(9, 5.5))
        draw(df, location, ax)
        fig.tight_layout()
        path = output_dir / f"{slug}_{name}.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        written.append(path)

    return written
