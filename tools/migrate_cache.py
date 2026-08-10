#!/usr/bin/env python
"""Convert the cache from gzipped CSV to the compact codec format.

Every file is verified by decoding what was just written and comparing it, with
no tolerance, against the frame read from the original - the original is only
unlinked once its replacement is proven to read back identically. A failure
leaves that city's legacy file in place (readers still accept it), so a partial
run degrades to a partial migration rather than to data loss.

Usage:
    python tools/migrate_cache.py --dry-run     # report, touch nothing
    python tools/migrate_cache.py               # convert
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codec  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = sorted(DATA.glob("*.csv.gz"))
    if args.limit:
        files = files[:args.limit]
    if not files:
        print("nothing to migrate")
        return 0

    old_bytes = new_bytes = 0
    done = failed = 0
    for i, src in enumerate(files, 1):
        dst = Path(str(src)[:-len(codec.LEGACY_SUFFIX)] + codec.SUFFIX)
        try:
            legacy = pd.read_csv(src, parse_dates=["date"]).set_index("date")
            blob = codec.encode(legacy)
            # Prove the replacement before destroying the original.
            pd.testing.assert_frame_equal(legacy, codec.decode(blob))
        except Exception as exc:  # noqa: BLE001 - report and keep the legacy file
            print(f"  SKIP {src.name}: {type(exc).__name__}: {exc}")
            failed += 1
            continue
        old_bytes += src.stat().st_size
        new_bytes += len(blob)
        done += 1
        if not args.dry_run:
            # Via a temp file: an interrupted write must not leave a partial
            # .tpy, which codec.cached_path would then PREFER over the intact
            # legacy file still sitting next to it.
            tmp = dst.with_suffix(dst.suffix + ".part")
            tmp.write_bytes(blob)
            tmp.replace(dst)
            src.unlink()
        if i % 500 == 0:
            print(f"  {i}/{len(files)}...", flush=True)

    verb = "would convert" if args.dry_run else "converted"
    print(f"{verb} {done} file(s), {failed} skipped")
    if done:
        print(f"  {old_bytes/2**20:.0f} MB -> {new_bytes/2**20:.0f} MB "
              f"({old_bytes/max(new_bytes,1):.2f}x smaller)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
