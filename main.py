"""Command-line entry point for the temperature analysis.

Examples
--------
    python main.py                          # Warszawa, 1940..last full year
    python main.py --location krakow
    python main.py --lat 48.85 --lon 2.35 --name Paris
    python main.py --start 1980 --end 2024 --refresh
"""

from __future__ import annotations

import argparse
import datetime as dt

from config import (
    DEFAULT_LOCATION,
    EARLIEST_YEAR,
    LOCATIONS,
    OUTPUT_DIR,
    Location,
)
from data import load_temperatures
from plots import annual_means, linear_trend, save_all


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
    means = annual_means(df)
    slope, _ = linear_trend(means.index.to_numpy(float), means.to_numpy())
    warmest = means.idxmax()
    coldest = means.idxmin()
    print(f"\n{location.name}: {df.index.year.min()}–{df.index.year.max()} "
          f"({len(df):,} days)")
    print(f"  overall mean daily temp : {df['temperature_2m_mean'].mean():.2f} °C")
    print(f"  warming trend           : {slope * 10:+.2f} °C / decade")
    print(f"  warmest year            : {warmest} ({means[warmest]:.2f} °C)")
    print(f"  coldest year            : {coldest} ({means[coldest]:.2f} °C)")


def main() -> None:
    args = _parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start ({args.start}) must not exceed --end ({args.end}).")

    location = _resolve_location(args)
    print(f"Loading {location.name} temperatures {args.start}–{args.end} …")
    df = load_temperatures(location, args.start, args.end, refresh=args.refresh)

    _print_summary(df, location)

    paths = save_all(df, location, OUTPUT_DIR)
    print("\nWrote:")
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
