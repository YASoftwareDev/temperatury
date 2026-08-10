"""Compact on-disk encoding for the cached daily series.

The cache used to be gzipped CSV: an ISO date and a decimal string per day, per
city. Both halves are waste. The series is a CONTIGUOUS daily index (verified
across every family), so the dates are fully implied by a start date and a row
count; and every value the API returns carries one decimal, so a tenth-of-a-unit
integer stores it exactly. Measured over 20 real files: 108.5 KB -> 26.2 KB per
city, 4.1x, which is what brings a >=10k-population roster (32,671 cities) down
from 3.4 GB to 0.8 GB.

The encoding is deliberately NOT delta-coded. Delta buys a further 4% and costs
exact reasoning about int16 wraparound across the missing-day sentinel - a bad
trade for a format that must round-trip climate data byte-for-byte.

Format (the whole blob is LZMA-compressed):

    magic    b"TMPY"          4 bytes
    version  uint8            1
    n_cols   uint8            number of value columns
    n_rows   uint32           days
    start    int32            start date as a proleptic-ordinal day number
    names    uint16 len + UTF-8, per column
    values   int16 x n_rows, column-major; MISSING (-32768) marks NaN

Readers accept the legacy ``.csv.gz`` too, so a half-migrated cache - or a
gatherer that has not pulled yet - still loads.
"""
from __future__ import annotations

import datetime as _dt
import lzma
import struct
from pathlib import Path

import numpy as np
import pandas as pd

MAGIC = b"TMPY"
VERSION = 1
# int16 low end, reserved for "no observation that day". Real values never reach
# it: measured range across every family is [-30.9, 283.2] units, i.e. +-3000
# tenths, three orders of magnitude inside the sentinel.
MISSING = -32768
SCALE = 10          # tenths of a degree / millimetre - the API's own precision

SUFFIX = ".tpy"
LEGACY_SUFFIX = ".csv.gz"


def _quantize(values: np.ndarray) -> np.ndarray:
    """Float series -> int16 tenths, NaN -> MISSING.

    Rounds half away from zero (np.round is banker's rounding, which would map
    -0.05 and 0.05 to the same stored tenth on exactly-representable inputs).
    """
    v = np.asarray(values, dtype="float64")
    # NaN is legitimate - it means "no observation that day". An infinity is
    # neither a measurement nor an absence, so it must not quietly become one:
    # rejecting it here is the same rule as the sentinel check below.
    if np.any(np.isinf(v)):
        raise ValueError("non-finite value is not a measurement")
    real = ~np.isnan(v)
    scaled = np.where(real, v * SCALE, 0.0)
    q = np.trunc(scaled + np.copysign(0.5, v), where=real, out=np.zeros_like(v))
    # Refuse input finer than the format can hold rather than quietly rounding
    # it. Every source so far emits one decimal (verified across all families),
    # but "lossless round-trip" has to fail loudly the day that stops being
    # true - a silently rounded measurement is indistinguishable from a real
    # one. The tolerance absorbs float64 representation error only (12.3*10 is
    # 123.00000000000001), not genuine extra precision.
    if np.any(real & (np.abs(scaled - np.round(scaled)) > 1e-6)):
        raise ValueError(f"value carries more precision than 1/{SCALE} units")
    # Range-check the REAL values only, and reject the sentinel itself: a
    # genuine -3276.8 would otherwise quantize onto MISSING and decode back as
    # NaN - a measurement silently becoming "no observation", which is the one
    # failure this format must never have. Unreachable for temperature or
    # rainfall, but it costs one comparison to make it impossible.
    if np.any(real & ((q <= MISSING) | (q > 32767))):
        raise ValueError("value out of int16 range at 0.1 precision")
    return np.where(real, q, MISSING).astype(np.int16)


def encode(frame: pd.DataFrame) -> bytes:
    """Encode a date-indexed daily frame. The index must be contiguous daily."""
    if frame.index.name != "date":
        raise ValueError(f"expected a 'date' index, got {frame.index.name!r}")
    idx = pd.to_datetime(frame.index)
    # Only the DATE is stored, so a timestamp carrying a time of day would come
    # back shifted to midnight - the index silently changing, which is the same
    # class of failure as a value silently changing.
    if len(idx) and (idx != idx.normalize()).any():
        raise ValueError("index carries a time of day; only whole dates are stored")
    if len(idx) > 1:
        step = np.unique(np.diff(idx.to_numpy()).astype("timedelta64[D]"))
        if step.size != 1 or step[0] != np.timedelta64(1, "D"):
            raise ValueError("index is not contiguous daily; dates cannot be "
                             "dropped for this frame")
    # An empty frame is legitimate: the current-year fetch returns one for a
    # location whose archive has no rows yet, and the caller caches it so the
    # next run does not re-request it. There is no first date to record.
    # Ordinal 1, not 0: 0 is not a valid date ordinal. The value is never read
    # back for an empty frame, but it has to be decodable.
    start = idx[0].to_pydatetime().date().toordinal() if len(idx) else 1
    head = bytearray(MAGIC)
    head += struct.pack("<BBIi", VERSION, len(frame.columns), len(frame), start)
    for name in frame.columns:
        raw = str(name).encode("utf-8")
        head += struct.pack("<H", len(raw)) + raw
    body = b"".join(_quantize(frame[c].to_numpy()).tobytes()
                    for c in frame.columns)
    return lzma.compress(bytes(head) + body, preset=9)


def decode(blob: bytes) -> pd.DataFrame:
    """Inverse of :func:`encode`."""
    buf = lzma.decompress(blob)
    if buf[:4] != MAGIC:
        raise ValueError("not a temperatury cache blob")
    version, n_cols, n_rows, start = struct.unpack_from("<BBIi", buf, 4)
    if version != VERSION:
        raise ValueError(f"unsupported cache format version {version}")
    off = 4 + struct.calcsize("<BBIi")
    names = []
    for _ in range(n_cols):
        (ln,) = struct.unpack_from("<H", buf, off)
        off += 2
        names.append(buf[off:off + ln].decode("utf-8"))
        off += ln
    # Exact length, not "at least": trailing bytes would mean the header and
    # the body disagree about how many days this file holds, and decoding the
    # header's count would silently drop the remainder. Silent truncation is
    # the one outcome a measurement store must never have.
    if len(buf) - off != n_rows * n_cols * 2:
        raise ValueError("cache blob body does not match its header")
    flat = np.frombuffer(buf, dtype="<i2", count=n_rows * n_cols, offset=off)
    # Reproduce the LEGACY index exactly - microsecond resolution and no freq -
    # not merely the same instants. Downstream resample/reindex/merge was all
    # written against what read_csv produced, so a migration that quietly
    # changed the index dtype or attached a freq would be a behaviour change
    # wearing a storage change's clothes.
    if n_rows:
        dates = (pd.date_range(_dt.date.fromordinal(start), periods=n_rows,
                               freq="D", name="date")
                 ._with_freq(None).astype("datetime64[us]"))
    else:
        # No rows means no start date was meaningful; date_range cannot be
        # asked to expand the placeholder ordinal (it predates pandas' range).
        dates = pd.DatetimeIndex([], name="date").astype("datetime64[us]")
    data = {}
    for i, name in enumerate(names):
        col = flat[i * n_rows:(i + 1) * n_rows].astype("float64")
        col[col == MISSING] = np.nan
        data[name] = col / SCALE
    return pd.DataFrame(data, index=pd.Index(dates, name="date"))


def read_frame(path: Path) -> pd.DataFrame:
    """Load a cache file in either the current or the legacy CSV format."""
    path = Path(path)
    if path.suffix == SUFFIX:
        return decode(path.read_bytes())
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def write_frame(frame: pd.DataFrame, path: Path) -> None:
    """Write a cache file ATOMICALLY, so a concurrent reader or `git add` never
    sees a partial file (the gatherers rely on this - see om_parallel)."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(encode(frame))
    tmp.replace(path)


def legacy_path(path: Path) -> Path:
    """The pre-migration ``.csv.gz`` name for a current cache path."""
    return Path(str(path)[:-len(SUFFIX)] + LEGACY_SUFFIX)


def cached_path(path: Path) -> Path | None:
    """Whichever format actually exists for this cache entry, or None.

    A city counts as cached in EITHER format: during the migration - and on a
    gatherer that has not pulled the new code yet - re-fetching a city we
    already hold would burn the scarcest resource the project has (the hourly
    Open-Meteo quota) for a file that is already on disk.
    """
    path = Path(path)
    if path.exists():
        return path
    old = legacy_path(path)
    return old if old.exists() else None
