#!/usr/bin/env python
"""Bulk-fill the site's data cache from Copernicus ERA5 daily statistics.

Why this exists
---------------
Open-Meteo is fetched one (or a few) cities per HTTP request and rate-limits
heavy 86-year pulls, so filling all 757 cities takes days. ERA5 lets us pull a
single *global* 0.25° daily grid per (variable, year) and extract **every** city
point from it locally — one download serves all cities.

Dataset: ``derived-era5-single-levels-daily-statistics`` (CDS), 1940-present,
0.25°, global. Frequency ``1_hourly`` so daily max/min are the true hourly
extremes. Requires a ``~/.cdsapirc`` and having accepted the dataset licence.

Output — the exact files ``main.py`` already reads (fill-only unless --overwrite):
    data/{slug}_1940-2025.csv.gz          date,temperature_2m_mean         (°C)
    data/{slug}_1940-2025_extremes.csv.gz date,temperature_2m_max,_min     (°C)
    data/{slug}_1940-2025_precip.csv.gz   date,precipitation_sum           (mm)

ERA5 units: 2 m temperature in Kelvin (−273.15 → °C); total precipitation in
metres (×1000 → mm). The day boundary is UTC (a single global grid can only use
one timezone); Open-Meteo used each city's local day. The difference is
climatologically negligible for trends and ≲0.5 °C for record extremes.

Flow (resumable): for each (variable-stat, year) download a global NetCDF to
``--staging/nc``, extract all city points to ``--staging/extract/{key}_{year}.pkl``
(tiny), then delete the NetCDF. Re-running skips any year already extracted and
any city file already present. After all years, assemble the per-city CSVs.

Usage
-----
    python tools/era5_extract.py                 # all groups, 1940-2025, all cities
    python tools/era5_extract.py --test          # 1 year, small area, 5 cities
    python tools/era5_extract.py --groups mean   # just the daily-mean cache
    python tools/era5_extract.py --overwrite     # replace existing caches too
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

DATASET = "derived-era5-single-levels-daily-statistics"
DATA_DIR = config.DATA_DIR
DEFAULT_STAGING = Path(__file__).resolve().parent.parent / "era5_staging"

# A "group" = one output cache file. Each maps to one or more ERA5 daily
# statistics of an ERA5 variable. ``key`` is the per-stat staging id; ``col`` is
# the output CSV column; ``conv`` turns raw ERA5 units into the site's units.
K = 273.15
_to_c = lambda a: a - K            # Kelvin  -> °C
_to_mm = lambda a: a * 1000.0      # metres  -> mm
GROUPS = {
    "mean": {
        "suffix": "",
        "stats": [("tmean", "2m_temperature", "daily_mean", "temperature_2m_mean", _to_c)],
    },
    "extremes": {
        "suffix": "_extremes",
        "stats": [
            ("tmax", "2m_temperature", "daily_maximum", "temperature_2m_max", _to_c),
            ("tmin", "2m_temperature", "daily_minimum", "temperature_2m_min", _to_c),
        ],
    },
    "precip": {
        "suffix": "_precip",
        "stats": [("precip", "total_precipitation", "daily_sum", "precipitation_sum", _to_mm)],
    },
}

_MONTHS = [f"{m:02d}" for m in range(1, 13)]
_DAYS = [f"{d:02d}" for d in range(1, 32)]


# --- CDS download ----------------------------------------------------------
def _client():
    import cdsapi
    return cdsapi.Client()


# CDS limits the number of *queued* requests per dataset per user, so we run a
# SINGLE serial worker (one request in flight at a time) and treat a queue-limit
# rejection as "wait your turn", not a failure — otherwise a full queue makes us
# skip years. These signals appear in the raised error / rejected-job message.
_QUEUE_SIGNALS = ("queued requests", "temporarily limited", "too many",
                  "rate limit", "429", "rejected")


def download_year(client, api_var, stat, year, nc_path, area, retries=60):
    """Retrieve one global (or --area) daily grid for a (variable, stat, year).

    Patient with CDS's per-dataset queue limit: a queue-limit rejection waits a
    flat 120 s and retries without consuming the (large) retry budget, so a busy
    queue only slows us down — it never drops a year.
    """
    request = {
        "product_type": "reanalysis",
        "variable": [api_var],
        "year": [str(year)],
        "month": _MONTHS,
        "day": _DAYS,
        "daily_statistic": stat,
        "time_zone": "utc+00:00",
        "frequency": "1_hourly",
        "data_format": "netcdf",
    }
    if area:
        request["area"] = area  # [N, W, S, E]
    tmp = nc_path.with_suffix(".nc.part")
    attempt = 0
    while True:
        attempt += 1
        try:
            client.retrieve(DATASET, request, str(tmp))
            tmp.replace(nc_path)
            return
        except Exception as error:  # noqa: BLE001 — CDS raises many types
            msg = str(error).lower()
            queue_limited = any(s in msg for s in _QUEUE_SIGNALS)
            if queue_limited:
                print(f"    … {api_var}/{stat}/{year} queue full, waiting 120s")
                time.sleep(120)
                attempt -= 1  # don't count a "wait your turn" against the budget
                continue
            if attempt >= retries:
                raise
            wait = min(30 * attempt, 300)
            print(f"    ! retry {attempt}/{retries} for {api_var}/{stat}/{year} "
                  f"in {wait}s: {error}")
            time.sleep(wait)


# --- point extraction ------------------------------------------------------
def _coord_name(ds, *candidates):
    for name in candidates:
        if name in ds.coords or name in ds.variables:
            return name
    return None


def _data_var(ds, latname, lonname):
    """The gridded field — the data var carrying both lat and lon dims."""
    for name, da in ds.data_vars.items():
        if latname in da.dims and lonname in da.dims:
            return name
    raise RuntimeError(f"no lat/lon data var in {list(ds.data_vars)}")


def extract_points(nc_path, lats, lons, slugs):
    """Nearest-gridpoint daily series for every city — returns date×slug frame."""
    import xarray as xr

    ds = xr.open_dataset(nc_path)
    try:
        latname = _coord_name(ds, "latitude", "lat")
        lonname = _coord_name(ds, "longitude", "lon")
        varname = _data_var(ds, latname, lonname)
        da = ds[varname]
        tname = _coord_name(ds, "valid_time", "time", "forecast_reference_time")

        # Match the grid's longitude convention (ERA5 netcdf is often 0..360).
        grid_lons = np.asarray(ds[lonname].values, dtype=float)
        qlons = np.asarray(lons, dtype=float)
        if grid_lons.max() > 180.0:
            qlons = np.where(qlons < 0, qlons + 360.0, qlons)

        lat_da = xr.DataArray(np.asarray(lats, dtype=float), dims="city")
        lon_da = xr.DataArray(qlons, dims="city")
        pts = da.sel({latname: lat_da, lonname: lon_da}, method="nearest")
        pts = pts.transpose(tname, "city")

        dates = pd.to_datetime(da[tname].values).normalize()
        frame = pd.DataFrame(np.asarray(pts.values, dtype="float32"),
                             index=dates, columns=list(slugs))
        frame.index.name = "date"
        return frame
    finally:
        ds.close()


# --- orchestration ---------------------------------------------------------
def _cities(args):
    locs = list(config.LOCATIONS.values())
    if args.cities:
        want = {s.strip() for s in args.cities.split(",")}
        locs = [l for l in locs if l.slug in want]
    if args.limit:
        locs = locs[: args.limit]
    slugs = [l.slug for l in locs]
    lats = [l.latitude for l in locs]
    lons = [l.longitude for l in locs]
    return slugs, lats, lons


def run(args):
    slugs, lats, lons = _cities(args)
    if not slugs:
        raise SystemExit("no cities selected")
    years = list(range(args.start, args.end + 1))
    nc_dir = args.staging / "nc"
    ex_dir = args.staging / "extract"
    nc_dir.mkdir(parents=True, exist_ok=True)
    ex_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    area = [args.area_n, args.area_w, args.area_s, args.area_e] if args.test else None
    if args.test:
        print(f"TEST mode: area={area}  years={years}  cities={len(slugs)}")

    client = None if args.assemble_only else _client()

    # --- phase 1: download + extract each (stat, year) to a small pickle ----
    for group in args.groups:
        for key, api_var, stat, _col, _conv in GROUPS[group]["stats"]:
            for year in years:
                ex_path = ex_dir / f"{key}_{year}.pkl"
                if ex_path.exists():
                    continue
                if args.assemble_only:
                    print(f"  (assemble-only) missing {ex_path.name}, skipped")
                    continue
                nc_path = nc_dir / f"{key}_{year}.nc"
                try:
                    if not nc_path.exists():
                        print(f"  ↓ {key} {year} …")
                        download_year(client, api_var, stat, year, nc_path, area)
                    frame = extract_points(nc_path, lats, lons, slugs)
                    frame.to_pickle(ex_path)
                    print(f"  ✓ {key} {year}: {frame.shape[0]} days × "
                          f"{frame.shape[1]} cities")
                    if not args.keep_nc:
                        nc_path.unlink(missing_ok=True)
                except Exception as error:  # noqa: BLE001
                    # One bad (variable, year) must not kill the whole worker —
                    # log and move on; a later resume run fills the gap.
                    print(f"  ✗ {key} {year} failed, skipping: {error}")

    if args.extract_only:
        print("\nextract-only: pickles written, skipping CSV assembly")
        return

    # --- phase 2: assemble per-city CSVs from the pickles -------------------
    written = skipped_existing = skipped_missing = 0
    for group in args.groups:
        spec = GROUPS[group]
        suffix = spec["suffix"]
        # Load every stat's full-period date×slug matrix once.
        mats = {}
        for key, _api, _stat, col, conv in spec["stats"]:
            parts = []
            for year in years:
                p = ex_dir / f"{key}_{year}.pkl"
                if p.exists():
                    parts.append(pd.read_pickle(p))
            if not parts:
                mats[key] = None
                continue
            big = pd.concat(parts).sort_index()
            big = conv(big).round(1)
            mats[key] = (col, big)

        for slug in slugs:
            path = DATA_DIR / f"{slug}_{args.start}-{args.end}{suffix}.csv.gz"
            if path.exists() and not args.overwrite:
                skipped_existing += 1
                continue
            cols = {}
            for key, _api, _stat, _col, _conv in spec["stats"]:
                if mats.get(key) is None:
                    cols = {}
                    break
                col, big = mats[key]
                if slug in big.columns:
                    cols[col] = big[slug]
            if not cols:
                skipped_missing += 1
                continue
            out = pd.DataFrame(cols).dropna(how="all")
            if out.empty:
                skipped_missing += 1
                continue
            out.index.name = "date"
            out.index = out.index.strftime("%Y-%m-%d")
            out.to_csv(path)
            written += 1

    print(f"\ndone: wrote {written}, kept {skipped_existing} existing, "
          f"{skipped_missing} without data")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1940)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--groups", default="mean,extremes,precip",
                    help="comma list of: mean, extremes, precip")
    ap.add_argument("--cities", default="", help="comma list of slugs (default: all)")
    ap.add_argument("--limit", type=int, default=0, help="cap number of cities")
    ap.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    ap.add_argument("--overwrite", action="store_true",
                    help="replace existing cache files (default: fill-only)")
    ap.add_argument("--keep-nc", action="store_true",
                    help="don't delete NetCDFs after extraction")
    ap.add_argument("--assemble-only", action="store_true",
                    help="skip downloads; build CSVs from existing pickles")
    ap.add_argument("--extract-only", action="store_true",
                    help="download+extract to pickles only; skip CSV assembly "
                         "(for parallel workers; run --assemble-only after)")
    ap.add_argument("--test", action="store_true",
                    help="small area + few years for a quick end-to-end check")
    ap.add_argument("--area-n", type=float, default=53.0)
    ap.add_argument("--area-w", type=float, default=20.0)
    ap.add_argument("--area-s", type=float, default=51.0)
    ap.add_argument("--area-e", type=float, default=22.0)
    args = ap.parse_args(argv)
    args.groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    bad = [g for g in args.groups if g not in GROUPS]
    if bad:
        ap.error(f"unknown group(s): {bad}")
    if args.test:
        args.end = 2023
        if args.start >= args.end:
            args.start = 2023
        if not args.cities and not args.limit:
            args.limit = 5
    return args


if __name__ == "__main__":
    run(parse_args())
