"""Command-line entry point for the temperature analysis.

Examples
--------
    python main.py                          # Warszawa, 1940..last full year
    python main.py --location krakow
    python main.py --all                    # every preset city + linked index
    python main.py --lat 48.85 --lon 2.35 --name Paris
    python main.py --start 1980 --end 2024 --refresh
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil

from config import (
    DEFAULT_LOCATION,
    EARLIEST_YEAR,
    LOCATIONS,
    OUTPUT_DIR,
    Location,
)
from data import load_temperatures
from plots import save_all, summary_stats
from report import build_site


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


def _generate(location: Location, nav: list[Location], args: argparse.Namespace) -> list:
    """Fetch one city, render its charts + page, and print its summary."""
    print(f"Loading {location.name} temperatures {args.start}–{args.end} …")
    df = load_temperatures(location, args.start, args.end, refresh=args.refresh)
    _print_summary(df, location)
    paths = save_all(df, location, OUTPUT_DIR)
    paths.append(build_site(df, location, OUTPUT_DIR, nav))
    return paths


def main() -> None:
    args = _parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start ({args.start}) must not exceed --end ({args.end}).")

    if args.all:
        locations = [LOCATIONS[key] for key in sorted(LOCATIONS)]
        landing = LOCATIONS[DEFAULT_LOCATION]
    else:
        locations = [_resolve_location(args)]
        landing = locations[0]

    paths: list = []
    for location in locations:
        paths.extend(_generate(location, locations, args))

    # The root index.html shows the landing city (its page is self-contained,
    # so a straight copy keeps every relative link and image valid).
    landing_slug = landing.slug
    index_path = OUTPUT_DIR / "index.html"
    shutil.copyfile(OUTPUT_DIR / f"{landing_slug}.html", index_path)
    paths.append(index_path)

    print("\nWrote:")
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
