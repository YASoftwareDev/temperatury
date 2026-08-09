#!/usr/bin/env python
"""Show data-backfill progress: how many cities have each dataset cached.

Usage:  python tools/coverage.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

locs = list(config.LOCATIONS.values())
n = len(locs)
DATA = Path(__file__).resolve().parent.parent / "data"


def have(suffix: str) -> list:
    return [l for l in locs if (DATA / f"{l.slug}_1940-2025{suffix}.csv.gz").exists()]


def current_year() -> int:
    import datetime as dt
    return dt.date.today().year


def bar(k: int, total: int, width: int = 30) -> str:
    filled = round(width * k / total) if total else 0
    return "█" * filled + "·" * (width - filled)


print(f"\nData coverage — {n} cities\n")
datasets = [
    ("mean (historical)", ""),
    ("precip", "_precip"),
    ("extremes (max/min)", "_extremes"),
    ("apparent (heat index)", "_apparent"),
]
for label, suffix in datasets:
    got = have(suffix)
    print(f"  {label:24s} {bar(len(got), n)} {len(got):>4}/{n}")

cur = current_year()
cur_files = len(list(DATA.glob(f"*_{cur}_current.csv.gz")))
print(f"  {f'current year ({cur})':24s} {bar(cur_files, n)} {cur_files:>4}/{n}")

mean_have = have("")
print(f"\n  render-eligible now (mean cached): {len(mean_have)} cities")

by_region_total = Counter(l.region for l in locs)
by_region_have = Counter(l.region for l in mean_have)
print("\n  mean coverage by region:")
for region in config.REGIONS:
    t = by_region_total.get(region, 0)
    if t:
        print(f"    {region:16s} {by_region_have.get(region, 0):>4}/{t}")
print()
