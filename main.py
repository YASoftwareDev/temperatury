"""Command-line entry point for the temperature analysis.

Generates a localised static site (one folder per language) under ``output/``:
each city's data is downloaded once (concurrently) and rendered into every
language, with a Leaflet map chooser as each language's landing page.

Examples
--------
    python main.py                          # Warszawa, all languages
    python main.py --location paris
    python main.py --all                    # every preset city, all languages
    python main.py --lat 48.85 --lon 2.35 --name Paris
    python main.py --start 1980 --end 2024 --refresh
"""

from __future__ import annotations

import argparse
import datetime as dt
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor

import i18n
import interactive
from config import (
    DEFAULT_LOCATION,
    EARLIEST_YEAR,
    LOCATIONS,
    OUTPUT_DIR,
    Location,
)
from data import (
    cache_signature,
    load_apparent_bulk,
    load_current_bulk,
    load_current_extremes_bulk,
    load_extremes_bulk,
    load_precip_bulk,
    load_temperatures_bulk,
)
from plots import RENDER_VERSION, localize_specs, save_all, summary_stats
from report import build_map_page, build_site, write_redirect


def _last_full_year() -> int:
    """The most recent calendar year that has already ended."""
    return dt.date.today().year - 1


def _resolve_location(args: argparse.Namespace) -> Location:
    """Pick a location from an explicit lat/lon or a named preset."""
    if args.lat is not None and args.lon is not None:
        return Location(args.name or "Custom", args.lat, args.lon)
    return LOCATIONS[args.location]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--location", choices=sorted(LOCATIONS), default=DEFAULT_LOCATION,
                        help="named preset location (default: %(default)s)")
    parser.add_argument("--all", action="store_true",
                        help="generate a page for every preset city, linked together")
    parser.add_argument("--lat", type=float, help="custom latitude (use with --lon)")
    parser.add_argument("--lon", type=float, help="custom longitude (use with --lat)")
    parser.add_argument("--name", help="label for a custom lat/lon location")
    parser.add_argument("--start", type=int, default=EARLIEST_YEAR,
                        help="first year (default: %(default)s)")
    parser.add_argument("--end", type=int, default=_last_full_year(),
                        help="last full year (default: last completed year)")
    parser.add_argument("--refresh", action="store_true",
                        help="re-download even if cached data exists")
    return parser.parse_args()


def _print_summary(df, location: Location) -> None:
    """Print the headline numbers to the terminal."""
    s = summary_stats(df)
    print(f"\n{location.name}: {s['start']}–{s['end']} ({s['days']:,} days)")
    print(f"  overall mean daily temp : {s['mean']:.2f} °C")
    print(f"  warming trend           : {s['trend_per_decade']:+.2f} °C / decade")
    print(f"  warmest year            : {s['warmest_year']} ({s['warmest_value']:.2f} °C)")
    print(f"  coldest year            : {s['coldest_year']} ({s['coldest_value']:.2f} °C)")


# Language whose axis/legend text is baked into the shared, language-neutral
# charts (titles are localised in the HTML instead). English reads as neutral.
CHART_LANG = "en"


# --- parallel rendering ----------------------------------------------------
# Rendering a city's charts (matplotlib) is the build bottleneck and each city
# is independent, so cities are rendered across a process pool. ``locations``
# and the language list are the same for every city, so they are shipped once
# per worker via the pool initializer instead of in every task.
_WORKER: dict = {}


def _init_render_worker(locations: list[Location], languages: list[str]) -> None:
    _WORKER["locations"] = locations
    _WORKER["languages"] = languages


def _render_city(task) -> tuple[str, int]:
    """Render one city: charts ONCE (shared), then a page per language.

    Charts are language-neutral (titles live in the HTML, not the PNG), so they
    are rendered a single time into ``output/charts`` and every language's page
    references them — instead of re-rendering the same image 21 times. Runs in a
    worker process.
    """
    location, df, df_ext, df_precip, df_app, df_cur, df_cur_ext, signature = task
    locations = _WORKER["locations"]
    languages = _WORKER["languages"]
    range_data = interactive.range_payload(df, extra=df_cur)
    records_data = (
        interactive.records_payload(df_ext, extra=df_cur_ext)
        if df_ext is not None else None)
    # Render the charts once as SVG (English text) and collect each text's
    # localisation recipe, so every language's page can localise the shared SVGs.
    charts_dir = OUTPUT_DIR / "charts"
    specs = save_all(df, location, charts_dir, i18n.get(CHART_LANG),
                     df_precip=df_precip, df_ext=df_ext, df_app=df_app,
                     signature=signature)
    n = 0
    for lang in languages:
        tr = i18n.get(lang)
        chart_i18n: dict[str, str] = {}
        for cs in specs.values():
            chart_i18n.update(localize_specs(cs, tr))
        build_site(df, location, OUTPUT_DIR / lang, locations, lang, languages, tr,
                   range_data=range_data, records_data=records_data,
                   has_precip=df_precip is not None,
                   has_dtr=df_ext is not None,
                   has_appheat=df_app is not None,
                   chart_i18n=chart_i18n)
        n += 1
    return location.slug, n


def main() -> None:
    args = _parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start ({args.start}) must not exceed --end ({args.end}).")

    # Optional TEMPERATURY_LANGS=pl,en restricts which languages render — lets a
    # CI build ship a fast subset (e.g. a map/HTML fix) without the full
    # 21-language chart render. Unset = every language (normal behaviour).
    _langs_env = os.environ.get("TEMPERATURY_LANGS", "").strip()
    if _langs_env:
        wanted = [c.strip() for c in _langs_env.split(",") if c.strip()]
        i18n.LANGUAGES = [l for l in i18n.LANGUAGES if l in wanted]
        print(f"Restricting to languages: {i18n.LANGUAGES}")

    if args.all:
        locations = [LOCATIONS[key] for key in sorted(LOCATIONS)]
    else:
        locations = [_resolve_location(args)]

    # Fetch all locations in a few bulk requests (cache-aware). Data is
    # language-neutral, so it is downloaded once and rendered in every language.
    print(f"Fetching {len(locations)} location(s) {args.start}–{args.end} …")
    frames = load_temperatures_bulk(locations, args.start, args.end,
                                    refresh=args.refresh)

    # Build only the cities we actually have data for (a rate-limited or
    # unreachable city is skipped rather than failing the whole site).
    missing = [loc.name for loc in locations if loc.slug not in frames]
    if missing:
        print(f"Note: {len(missing)} location(s) without data, skipped: "
              f"{', '.join(missing)}")
    locations = [loc for loc in locations if loc.slug in frames]
    if not locations:
        raise SystemExit("No location data available — nothing to build.")

    # Daily max/min (record highs/lows) — optional add-on dataset; a city
    # without it simply skips the record chart.
    extremes = load_extremes_bulk(locations, args.start, args.end,
                                  refresh=args.refresh)
    # Daily precipitation — optional add-on dataset (same backfill model).
    precip = load_precip_bulk(locations, args.start, args.end,
                              refresh=args.refresh)
    # Apparent temperature (humidity-aware heat index) — powers the heat-index
    # health chart; same optional-add-on backfill model.
    apparent = load_apparent_bulk(locations, args.start, args.end,
                                  refresh=args.refresh)
    # The year in progress (partial) — fed only to the interactive widgets so
    # readers can pick it, kept out of the static trend charts. Cached under a
    # distinct key; in offline mode only committed current-year data is used.
    current = load_current_bulk(locations, refresh=args.refresh)
    current_ext = load_current_extremes_bulk(locations, refresh=args.refresh)

    # Charts are now shared under output/charts; drop any per-language chart
    # PNGs left by an older build (restored from cache) so the deploy doesn't
    # carry ~20× stale duplicates.
    for _lang in i18n.LANGUAGES:
        for _png in (OUTPUT_DIR / _lang).glob("*.png"):
            _png.unlink()

    # Per-city render tasks (data + signature). The summary print stays in the
    # main process so log order is stable; ``signature`` lets a worker skip
    # re-rendering charts whose data + theme version are unchanged.
    tasks = []
    for location in locations:
        df = frames[location.slug]
        if len(locations) == 1:
            _print_summary(df, location)
        else:
            s = summary_stats(df)
            print(f"  {location.name:18s} mean {s['mean']:5.1f} °C  "
                  f"trend {s['trend_per_decade']:+.2f}/dec")
        signature = f"{RENDER_VERSION}:{cache_signature(location, args.start, args.end)}"
        tasks.append((location, df, extremes.get(location.slug),
                      precip.get(location.slug), apparent.get(location.slug),
                      current.get(location.slug), current_ext.get(location.slug),
                      signature))

    # Render cities across a process pool — matplotlib is the bottleneck and
    # cities are independent (each writes its own files). TEMPERATURY_JOBS
    # overrides the worker count (default: all cores).
    jobs = int(os.environ.get("TEMPERATURY_JOBS") or 0) or (os.cpu_count() or 1)
    jobs = max(1, min(jobs, len(tasks)))
    written = 0
    if jobs == 1:
        _init_render_worker(locations, i18n.LANGUAGES)
        for task in tasks:
            written += _render_city(task)[1]
    else:
        print(f"Rendering {len(tasks)} cities × {len(i18n.LANGUAGES)} languages "
              f"on {jobs} processes …")
        # ``fork`` inherits the parent's imports/data and avoids re-importing
        # __main__ (Python 3.14 defaults to forkserver, which would).
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=jobs, mp_context=ctx,
                                 initializer=_init_render_worker,
                                 initargs=(locations, i18n.LANGUAGES)) as pool:
            for _slug, n in pool.map(_render_city, tasks):
                written += n

    # Each language's index.html is the Leaflet map chooser; root redirects.
    for lang in i18n.LANGUAGES:
        build_map_page(OUTPUT_DIR / lang, locations, lang, i18n.LANGUAGES, i18n.get(lang))
        written += 1
    write_redirect(
        OUTPUT_DIR / "index.html",
        f"{i18n.DEFAULT_LANG}/index.html",
        i18n.DEFAULT_LANG,
    )
    written += 1

    print(f"\nWrote {written} files to {OUTPUT_DIR} "
          f"({len(locations)} cities × {len(i18n.LANGUAGES)} languages).")


if __name__ == "__main__":
    main()
