# temperatury

Historical temperature analysis for cities worldwide (and any custom lat/lon),
using free [Open-Meteo](https://open-meteo.com/) reanalysis data (daily, from
1940). Produces both the **distribution** of temperatures and how they **change
through the years**.

**🌍 Live site:** https://yasoftwaredev.github.io/temperatury/ (auto-rebuilt from
fresh data on each push and yearly). Covers **world capitals plus major cities**
(~290 locations across 7 regions), picked from the **interactive Leaflet map** or
a **region-grouped dropdown**. Available in **6 languages** — Polish, English,
German, French, Spanish and Ukrainian (switcher in the header; charts, captions
and the reading guide are all localised). Add a city in `config.py`, a language
in `i18n.py`.

![Warszawa temperature dashboard](assets/dashboard.png)

## What it makes

A composite dashboard plus a dozen standalone PNGs and two interactive
(Chart.js) widgets in `output/`:

| View | Question it answers |
|------|---------------------|
| **Annual trend** | How does the yearly mean change over time? (LOESS curve + robust Theil–Sen trend, °C/decade, Mann–Kendall significance) |
| **Warming stripes** | The Ed-Hawkins one-stripe-per-year anomaly graphic — blue→red warming at a glance |
| **Anomaly bars** | How does each year compare to the 1961–1990 norm? (blue = cooler, red = warmer) |
| **Seasonal-cycle shift** | First-decade vs last-decade monthly curve — *which months* warmed most (often winters) |
| **Growing-season length** | Days/year warm enough to grow (thermal season, daily mean ≥ 5 °C), with a trend |
| **Hot & freezing days** | How many days a year exceed 18 °C or stay below 0 °C, and how is that changing? |
| **Diurnal range** | Mean daily max − min (day vs night) — a shrinking range is a greenhouse fingerprint (needs daily max/min) |
| **Month × year heatmap** | *Which months/seasons* are warming? (discrete 2 °C bands) |
| **Monthly anomaly heatmap** | How much has *each month* shifted vs. its 1961–1990 norm? (seasonal cycle removed, robust scale) |
| **Day-to-day swings** | How often big day-to-day temperature jumps (≥6 °C) happen each year — temperature variability/volatility, with a trend |
| **Annual precipitation** | Total yearly rainfall (mm) over the years, with a trend (where precipitation data is cached) |
| **Monthly min–max range** *(interactive)* | Pick any year and see where its 12 monthly means fall within the full historical envelope |
| **Monthly record high/low** *(interactive)* | Each month's all-time record daily high/low, with any selectable year's extremes — "hottest day ever in July?" |

Every view is time-aware: the hot/freezing-day counts track the distribution's
tails year by year, and the monthly-anomaly view
normalises each month to its own baseline so the warming signal stands out
even where the absolute heatmap is dominated by the seasonal cycle.

## Setup

```bash
uv venv .venv
uv pip install --python .venv -r requirements.txt
```

## Usage

```bash
.venv/bin/python main.py                       # Warszawa, 1940..last full year
.venv/bin/python main.py --location krakow     # preset: krakow/gdansk/wroclaw/poznan
.venv/bin/python main.py --all                 # every preset city, linked by a nav bar
.venv/bin/python main.py --lat 48.85 --lon 2.35 --name Paris
.venv/bin/python main.py --start 1980 --end 2024 --refresh
```

The published site (`--all`) builds one page per city with a switcher in the
header; the root `index.html` shows Warszawa.

Downloaded data is cached under `data/`; pass `--refresh` to re-download.

## Layout

- `config.py` — locations, paths, API constants
- `data.py` — download + cache daily temperatures
- `plots.py` — the chart functions (LOESS/Theil–Sen/Mann–Kendall stats) + dashboard composition
- `interactive.py` — the Chart.js monthly-range / records widgets (year picker)
- `report.py` — generates the static HTML page (with the city switcher)
- `main.py` — CLI entry point and summary printout

## Example (Warszawa, 1940–2025)

```
overall mean daily temp : 8.41 °C
warming trend           : +0.29 °C / decade
warmest year            : 2024 (11.46 °C)
coldest year            : 1940 (5.72 °C)
```

Data source: Open-Meteo historical reanalysis (ERA5). Free for non-commercial use.
