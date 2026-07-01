#!/usr/bin/env python
"""Concurrent Open-Meteo backfill — fills missing cities in parallel.

The original backfill fetches sequentially with pauses, badly under-using the
quota. This fetches many city-chunks at once with a thread pool (Open-Meteo
requests are I/O-bound, so concurrency — not raw CPU — is what helps). It
auto-scales to the available quota:

  * paid key  (OPENMETEO_API_KEY set → customer endpoint, no rate cap): 16 workers
  * free tier (measured ceiling ~5-6 concurrent heavy 86-yr requests):  5 workers

Writes the same data/{slug}_1940-2025[...].csv.gz files main.py reads, FILL-ONLY
(never overwrites an existing cache) and ATOMICALLY (temp + os.replace) so a
concurrent git-add or reader never sees a half-written file. Does NOT commit —
run alongside the ERA5 CDS worker (which writes staging pickles, not data/), then
commit once from the main session. Priority mean → precip → extremes: mean
unlocks a city's rendering.

Usage
-----
    python tools/om_parallel.py                 # all groups, missing cities
    python tools/om_parallel.py --groups mean   # just the rendering-critical set
    python tools/om_parallel.py --workers 10    # override auto worker count
    OPENMETEO_API_KEY=xxx python tools/om_parallel.py   # paid: 16 workers, uncapped
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
import data  # noqa: E402  (reuses its request/parse/cache-path helpers)

# group -> (daily-vars, parser, cache-path fn, cities-per-request chunk size)
GROUPS = {
    "mean":     ("temperature_2m_mean", data._parse_daily, data._cache_path, 15),
    "precip":   ("precipitation_sum", data._parse_precip, data._precip_cache_path, 15),
    "extremes": (",".join(data._EXTREME_COLS), data._parse_extremes,
                 data._extremes_cache_path, 7),
}


def _atomic_write(frame, path: Path) -> None:
    """Write a gzipped CSV atomically so readers never see a partial file."""
    tmp = path.with_suffix(path.suffix + ".part")
    frame.to_csv(tmp)
    os.replace(tmp, path)


def _fetch_chunk(chunk, daily, parse, path_fn, start, end):
    """Fetch one bulk request (many cities) and write each city's cache.

    Returns (written, failed). data._request already handles 429 with backoff,
    so a rate-limited chunk retries internally before giving up.
    """
    params = {
        "latitude": ",".join(str(l.latitude) for l in chunk),
        "longitude": ",".join(str(l.longitude) for l in chunk),
        "start_date": f"{start}-01-01",
        "end_date": f"{end}-12-31",
        "daily": daily,
        "timezone": "auto",
    }
    label = f"{len(chunk)} cities ({chunk[0].name}…)"
    try:
        payload = data._request(params, label)
    except Exception:  # noqa: BLE001 — rate-limited/unreachable chunk: skip, retry next run
        return 0, len(chunk)
    items = payload if isinstance(payload, list) else [payload]
    written = 0
    for loc, item in zip(chunk, items):
        try:
            frame = parse(item.get("daily"), loc.name)
            _atomic_write(frame, path_fn(loc, start, end))
            written += 1
        except Exception:  # noqa: BLE001 — one bad city shouldn't drop the chunk
            pass
    return written, len(chunk) - written


def run(args):
    locs = list(config.LOCATIONS.values())
    workers = args.workers or (16 if data._API_KEY else 5)
    endpoint = "PAID (uncapped)" if data._API_KEY else "free tier"
    print(f"Open-Meteo parallel backfill — {workers} workers, {endpoint}\n")

    for group in args.groups:
        daily, parse, path_fn, chunk_sz = GROUPS[group]
        missing = [l for l in locs if not path_fn(l, args.start, args.end).exists()]
        if not missing:
            print(f"[{group}] nothing missing")
            continue
        chunks = [missing[i:i + chunk_sz] for i in range(0, len(missing), chunk_sz)]
        print(f"[{group}] {len(missing)} cities in {len(chunks)} chunks")
        done = failed = 0
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_fetch_chunk, c, daily, parse, path_fn, args.start, args.end)
                    for c in chunks]
            for i, fut in enumerate(as_completed(futs), 1):
                w, f = fut.result()
                done += w
                failed += f
                if i % 5 == 0 or i == len(futs):
                    rate = done / max(time.time() - t0, 1e-9)
                    print(f"  {group}: {done} written, {failed} pending "
                          f"({rate:.1f} cities/s, chunk {i}/{len(futs)})")
        print(f"[{group}] done: {done} written, {failed} still missing "
              f"in {time.time() - t0:.0f}s")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1940)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--groups", default="mean,precip,extremes")
    ap.add_argument("--workers", type=int, default=0, help="0 = auto by quota")
    args = ap.parse_args(argv)
    args.groups = [g.strip() for g in args.groups.split(",") if g.strip() in GROUPS]
    return args


if __name__ == "__main__":
    run(parse_args())
