#!/usr/bin/env python
"""Concurrent Open-Meteo backfill — fills missing cities in parallel.

The original backfill fetches sequentially with pauses, badly under-using the
quota. This fetches many city-chunks at once with a thread pool (Open-Meteo
requests are I/O-bound, so concurrency — not raw CPU — is what helps). It
auto-scales to the available quota:

  * paid key  (OPENMETEO_API_KEY set → customer endpoint, no rate cap): 16 workers
  * free tier (measured ceiling ~5-6 concurrent heavy 86-yr requests):  5 workers

Writes the same data/{slug}_1940-2025[...] cache files main.py reads, FILL-ONLY
(never overwrites an existing cache) and ATOMICALLY (temp + replace) so a
concurrent git-add or reader never sees a half-written file. Does NOT commit —
run alongside the ERA5 CDS worker (which writes staging pickles, not data/), then
commit once from the main session. Priority mean → precip → extremes: mean
unlocks a city's rendering. Within a group, cities queue by country GDP per
capita (see countries.download_priority_key); --shuffle randomises inside the
top window only, so many contributors spread out without losing that order.

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
import random
import re
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as _FuturesTimeout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import codec  # noqa: E402
import config  # noqa: E402
import countries  # noqa: E402
import data  # noqa: E402  (reuses its request/parse/cache-path helpers)

# --shuffle randomises within this many highest-priority cities rather than the
# whole queue, so contributors spread out without discarding the priority order.
_SHUFFLE_WINDOW = 500

# group -> (daily-vars, parser, cache-path fn, cities-per-request chunk size)
GROUPS = {
    "mean":     ("temperature_2m_mean", data._parse_daily, data._cache_path, 15),
    "precip":   ("precipitation_sum", data._parse_precip, data._precip_cache_path, 15),
    "extremes": (",".join(data._EXTREME_COLS), data._parse_extremes,
                 data._extremes_cache_path, 7),
}


def _atomic_write(frame, path: Path) -> None:
    """Write the compact cache blob atomically so readers never see a partial file.

    The encoding carries no timestamp, so the bytes are deterministic: everyone
    who fetches a given city writes an identical file, and overlapping downloads
    across contributors merge without a git conflict. That property is
    load-bearing (it is why duplicate work is harmless) - do not introduce any
    time- or host-dependent field into the format.
    """
    codec.write_frame(frame, path)


def _shard_of(slug: str, total: int) -> int:
    """Stable bucket for a city: crc32 of the slug, mod the shard count.

    crc32 (unlike ``hash()``) is identical across Python builds and platforms,
    so every machine in a fleet computes the same partition without ever
    talking to each other - that independence is the whole mechanism.
    """
    return zlib.crc32(slug.encode("utf-8")) % total


def _apply_shard(missing, shard, shuffle):
    """Split a missing-list into (owned, fallback) and queue owned first.

    Two sharded machines never touch the same city while both still have owned
    work queued (fallback requests can only overlap the final in-flight owned
    chunks) - a guarantee, unlike staggered start times. The fallback tail keeps
    the dataset complete anyway: a machine whose own slice is exhausted (or
    whose peer died) walks the others' cities, where the shuffle window is the
    only - and by then sufficient - overlap protection.
    """
    idx, total = shard
    mine = [l for l in missing if _shard_of(l.slug, total) == idx - 1]
    rest = [l for l in missing if _shard_of(l.slug, total) != idx - 1]
    if shuffle:
        mine, rest = _spread_within_window(mine), _spread_within_window(rest)
    return mine, rest


def _chunked(seq, size):
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def _spread_within_window(missing):
    """Randomise the highest-priority window of an already-prioritised queue.

    Spreads work across contributors WITHOUT discarding the priority order: they
    all draw from the same short head of the queue, but in a different order.
    Shuffling the whole queue instead would make the priority sort inert; not
    shuffling at all would make every contributor march the identical list and
    re-download each other's cities (daily-chunk.sh never refreshes the working
    tree's data/, so a fetcher only sees what it fetched itself).
    """
    head = missing[:_SHUFFLE_WINDOW]
    random.shuffle(head)
    return head + missing[_SHUFFLE_WINDOW:]


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
    except data.QuotaExhausted:
        # Not this chunk's problem: the whole budget is gone, so every queued
        # chunk would fail too. Propagate so run() can stop the pass at once.
        raise
    except Exception:  # noqa: BLE001 — rate-limited/unreachable chunk: skip, retry next run
        return 0, len(chunk)
    items = payload if isinstance(payload, list) else [payload]
    written = 0
    for loc, item in zip(chunk, items):
        try:
            frame = parse(item.get("daily"), loc.name)
            _atomic_write(frame, path_fn(loc, start, end))
            written += 1
        except Exception as exc:  # noqa: BLE001 — one bad city shouldn't drop the chunk
            # SAY SO. Staying silent here has twice turned a total failure into
            # something that reads like ordinary pending work: a missing import
            # made every write raise, and a slug containing "/" made two cities
            # unwritable for the life of the project. Quota was spent both times.
            print(f"  !! {loc.slug}: {type(exc).__name__}: {exc}")
    return written, len(chunk) - written


def run(args):
    # Wealthier countries' cities first (same priority as main.py --all): early
    # visitors skew that way, so the daily/VM backfill should cover them first as
    # it fills in. --shuffle keeps this order's top window and only reorders
    # inside it; --rendered-only narrows WHICH cities qualify, never their order.
    locs = sorted(config.LOCATIONS.values(), key=countries.download_priority_key)
    if args.rendered_only:
        # Enrich mode: only cities that already render (mean cache present), since
        # the extra datasets appear on built pages and enriching an unrendered
        # city would spend quota on something nobody can see. This filters the
        # queue, it does NOT reorder it - the GDP priority above still decides who
        # goes first. It used to re-sort by population here, which silently made
        # that priority irrelevant on the only pass that spends real quota.
        locs = [l for l in locs
                if getattr(l, "kind", "city") == "city"
                and codec.cached_path(
                    data._cache_path(l, args.start, args.end)) is not None]
        print(f"enrich scope: {len(locs)} already-rendered cities, in priority order")
    workers = args.workers or (16 if data._API_KEY else 5)
    endpoint = "PAID (uncapped)" if data._API_KEY else "free tier"
    print(f"Open-Meteo parallel backfill — {workers} workers, {endpoint}\n")

    # Wall-clock cap (portable stand-in for the `timeout` command, which is
    # absent on macOS): once the free quota is spent every remaining chunk only
    # 429-retries, so callers cap the run instead of grinding for hours.
    deadline = time.time() + args.max_seconds if args.max_seconds else None
    total_written = total_failed = 0

    for group in args.groups:
        if deadline and time.time() >= deadline:
            print(f"[{group}] skipped: time cap reached")
            break
        daily, parse, path_fn, chunk_sz = GROUPS[group]
        # Cached in EITHER format counts as present: re-fetching a city we
        # already hold in the legacy encoding would burn hourly quota to
        # produce a file that is already on disk.
        missing = [l for l in locs
                   if codec.cached_path(
                       path_fn(l, args.start, args.end)) is None]
        if not missing:
            print(f"[{group}] nothing missing")
            continue
        if args.shard:
            mine, rest = _apply_shard(missing, args.shard, args.shuffle)
            print(f"[{group}] shard {args.shard[0]}/{args.shard[1]}: "
                  f"{len(mine)} owned, {len(rest)} fallback after them")
            missing = mine + rest
            # Chunk the halves separately: one blind chunking would pad the
            # last owned chunk with fallback cities, putting another machine's
            # cities into a bulk request while owned work remains.
            chunks = _chunked(mine, chunk_sz) + _chunked(rest, chunk_sz)
        else:
            if args.shuffle:
                missing = _spread_within_window(missing)
            chunks = _chunked(missing, chunk_sz)
        print(f"[{group}] {len(missing)} cities in {len(chunks)} chunks")
        done = failed = 0
        exhausted = None
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_fetch_chunk, c, daily, parse, path_fn, args.start, args.end)
                    for c in chunks]
            try:
                remaining = max(deadline - time.time(), 0.0) if deadline else None
                for i, fut in enumerate(as_completed(futs, timeout=remaining), 1):
                    try:
                        w, f = fut.result()
                    except data.QuotaExhausted as spent:
                        for other in futs:
                            other.cancel()  # queued chunks drop; in-flight finish
                        exhausted = str(spent)
                        break
                    done += w
                    failed += f
                    if i % 5 == 0 or i == len(futs):
                        rate = done / max(time.time() - t0, 1e-9)
                        print(f"  {group}: {done} written, {failed} pending "
                              f"({rate:.1f} cities/s, chunk {i}/{len(futs)})")
            except _FuturesTimeout:
                for fut in futs:
                    fut.cancel()   # drop queued chunks; in-flight ones finish
                print(f"  {group}: time cap ({args.max_seconds}s) reached, stopping")
        print(f"[{group}] done: {done} written, {failed} still missing "
              f"in {time.time() - t0:.0f}s")
        total_written += done
        total_failed += failed
        if exhausted:
            # Every later group would only re-hit the same wall, so end the run
            # here rather than logging two more empty passes.
            print(f"[{group}] stopped: {exhausted}")
            break

    # Fetched cities but stored NONE of them: the fetch is fine and the store is
    # broken (an API precision change, a bad path, a full disk), which no
    # amount of retrying fixes. A spent quota with nothing to show for it must
    # not read as an ordinary quiet day, so signal it. A quota-exhausted run
    # writes nothing WITHOUT failures and stays successful.
    if total_failed and not total_written:
        print(f"ERROR: {total_failed} cities fetched, none could be stored - "
              f"see the !! lines above.")
        return 1
    return 0


def _shard_arg(value: str):
    """Parse and validate an ``I/N`` shard spec into a (1-based index, total)."""
    m = re.fullmatch(r"(\d+)/(\d+)", value.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            f"expected I/N (e.g. 2/4), got {value!r}")
    idx, total = int(m.group(1)), int(m.group(2))
    if total < 1 or not 1 <= idx <= total:
        raise argparse.ArgumentTypeError(
            f"need 1 <= I <= N, got {idx}/{total}")
    return idx, total


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1940)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--groups", default="mean,precip,extremes")
    ap.add_argument("--workers", type=int, default=0, help="0 = auto by quota")
    ap.add_argument("--shuffle", action="store_true",
                    help=f"randomise fetch order within the top {_SHUFFLE_WINDOW} "
                         "by priority (for many people sharing one repo)")
    ap.add_argument("--max-seconds", type=int, default=0,
                    help="stop after N seconds (0 = no cap); portable timeout")
    ap.add_argument("--rendered-only", action="store_true",
                    help="restrict to cities that already render (mean cached), "
                         "keeping the priority order; for the enrich pass")
    ap.add_argument("--shard", type=_shard_arg, default=None, metavar="I/N",
                    help="own the I-th of N hash-buckets of cities and fetch "
                         "those first, everyone else's only after; disjoint "
                         "across a fleet by construction (default: "
                         "$TEMPERATURY_SHARD if set)")
    args = ap.parse_args(argv)
    if args.shard is None and os.environ.get("TEMPERATURY_SHARD"):
        # A typo here must fail loudly, not silently fall back to the unsharded
        # queue - that would reintroduce fleet collisions invisibly.
        try:
            args.shard = _shard_arg(os.environ["TEMPERATURY_SHARD"])
        except argparse.ArgumentTypeError as e:
            ap.error(f"TEMPERATURY_SHARD: {e}")
    # An unknown group used to be dropped silently, so a typo meant a run that
    # fetched nothing and still exited 0 - the same invisible-no-op the bad
    # shard value produced. Fail the invocation instead.
    wanted = [g.strip() for g in args.groups.split(",") if g.strip()]
    unknown = [g for g in wanted if g not in GROUPS]
    if unknown or not wanted:
        ap.error(f"--groups must name at least one of {', '.join(GROUPS)}"
                 + (f" (unknown: {', '.join(unknown)})" if unknown else ""))
    args.groups = wanted
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
