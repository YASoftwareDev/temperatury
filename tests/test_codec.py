"""The cache encoding must round-trip climate data EXACTLY.

Every number the site shows is derived from these files, so a lossy or
misaligned codec would silently corrupt published trends rather than fail
loudly. These tests pin the properties the format depends on: exact values at
the API's own 0.1 precision, the missing-day sentinel surviving as NaN, the
implied date index landing on the right days, deterministic bytes (so two
contributors fetching the same city produce identical files and never
conflict), and the legacy .csv.gz path still loading during the migration.
"""
import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codec


def _frame(n=800, cols=("temperature_2m_mean",), seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1940-01-01", periods=n, freq="D", name="date")
    data = {c: np.round(rng.uniform(-40, 45, n), 1) for c in cols}
    return pd.DataFrame(data, index=idx)


def test_round_trip_is_exact():
    f = _frame()
    back = codec.decode(codec.encode(f))
    pd.testing.assert_frame_equal(f, back, check_freq=False)


def test_missing_days_survive_as_nan():
    f = _frame(n=50)
    f.iloc[0, 0] = np.nan
    f.iloc[7, 0] = np.nan
    f.iloc[-1, 0] = np.nan
    back = codec.decode(codec.encode(f))
    assert np.array_equal(np.isnan(f.iloc[:, 0].to_numpy()),
                          np.isnan(back.iloc[:, 0].to_numpy()))
    pd.testing.assert_frame_equal(f, back, check_freq=False)


def test_all_missing_column():
    """A city the API had nothing for must not decode as zeros."""
    f = _frame(n=30)
    f.iloc[:, 0] = np.nan
    assert codec.decode(codec.encode(f)).iloc[:, 0].isna().all()


def test_multi_column_order_preserved():
    f = _frame(cols=("temperature_2m_max", "temperature_2m_min"))
    back = codec.decode(codec.encode(f))
    assert list(back.columns) == ["temperature_2m_max", "temperature_2m_min"]
    pd.testing.assert_frame_equal(f, back, check_freq=False)


def test_dates_are_reconstructed_not_stored():
    """Dropping the date column is only safe if the index comes back identical."""
    f = _frame(n=400)
    back = codec.decode(codec.encode(f))
    assert back.index[0] == f.index[0] and back.index[-1] == f.index[-1]
    assert back.index.name == "date"
    assert back.index.equals(f.index)
    assert back.index.freq is None, "must match the legacy read_csv behaviour"


def test_leap_day_alignment():
    """An off-by-one in the implied index would silently shift every value."""
    idx = pd.date_range("2024-02-27", periods=5, freq="D", name="date")
    f = pd.DataFrame({"temperature_2m_mean": [1.0, 2.0, 3.0, 4.0, 5.0]}, index=idx)
    back = codec.decode(codec.encode(f))
    assert str(back.index[2].date()) == "2024-02-29"
    assert back.loc["2024-02-29", "temperature_2m_mean"] == 3.0


def test_extreme_but_real_values():
    f = _frame(n=6)
    f.iloc[:, 0] = [-89.2, 56.7, 0.0, -0.1, 0.1, 283.2]   # records + heavy rain
    pd.testing.assert_frame_equal(f, codec.decode(codec.encode(f)), check_freq=False)


def test_empty_frame_round_trips():
    """The current-year fetch returns an empty frame for a location whose
    archive has no rows yet, and the caller caches it so the next run does not
    re-request it. The old CSV writer accepted that; the codec must too."""
    empty = pd.DataFrame({"temperature_2m_mean": []},
                         index=pd.DatetimeIndex([], name="date"))
    back = codec.decode(codec.encode(empty))
    assert len(back) == 0
    assert list(back.columns) == ["temperature_2m_mean"]
    assert back.index.name == "date"


def test_body_longer_than_the_header_claims_is_rejected():
    """Header and body disagreeing about the row count would silently drop the
    remainder - truncation a measurement store must never do quietly."""
    import lzma
    import struct as _struct
    f = _frame(n=3)
    raw = lzma.decompress(codec.encode(f))
    tampered = raw[:6] + _struct.pack("<I", 2) + raw[10:]   # claim 2 of 3 rows
    with pytest.raises(ValueError, match="does not match its header"):
        codec.decode(lzma.compress(tampered, preset=1))


def test_bytes_are_deterministic():
    """Two contributors fetching the same city must produce identical bytes -
    that is what makes duplicate downloads merge instead of conflict."""
    f = _frame(seed=3)
    assert codec.encode(f) == codec.encode(f.copy())


def test_index_with_a_time_of_day_is_rejected():
    """Only the date is stored, so a timestamp would come back shifted to
    midnight - the index silently changing, same class as a value changing."""
    f = pd.DataFrame({"t": [1.0, 2.0]},
                     index=pd.DatetimeIndex(["2024-01-01 12:00",
                                             "2024-01-02 12:00"], name="date"))
    with pytest.raises(ValueError, match="time of day"):
        codec.encode(f)


def test_non_contiguous_index_is_rejected():
    """Dates are implied, so a gappy frame must fail loudly, never silently
    re-date its own values."""
    idx = pd.DatetimeIndex(["1940-01-01", "1940-01-03"], name="date")
    f = pd.DataFrame({"temperature_2m_mean": [1.0, 2.0]}, index=idx)
    with pytest.raises(ValueError, match="contiguous"):
        codec.encode(f)


def test_out_of_range_is_rejected():
    f = _frame(n=3)
    f.iloc[0, 0] = 5000.0        # 50,000 tenths - past int16
    with pytest.raises(ValueError, match="int16"):
        codec.encode(f)


def test_value_colliding_with_the_missing_sentinel_is_rejected():
    """-3276.8 quantizes onto MISSING and would decode back as NaN - a real
    measurement silently becoming "no observation". Must fail loudly instead."""
    f = _frame(n=3)
    f.iloc[1, 0] = -3276.8
    with pytest.raises(ValueError, match="int16"):
        codec.encode(f)


@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_infinity_is_rejected_not_stored_as_missing(bad):
    """NaN means "no observation"; an infinity means something went wrong
    upstream. Letting it decode back as NaN would disguise a corrupt value as a
    legitimate gap."""
    f = _frame(n=3)
    f.iloc[1, 0] = bad
    with pytest.raises(ValueError, match="not a measurement"):
        codec.encode(f)


def test_finer_precision_is_rejected_not_rounded():
    """"Lossless" has to fail loudly the day a source emits two decimals - a
    silently rounded measurement is indistinguishable from a real one."""
    f = _frame(n=3)
    f.iloc[1, 0] = 12.34
    with pytest.raises(ValueError, match="precision"):
        codec.encode(f)


def test_float64_representation_error_is_not_mistaken_for_precision():
    """12.3*10 is 123.00000000000001 in float64; that must still encode."""
    f = _frame(n=4)
    f.iloc[:, 0] = [12.3, -0.7, 45.9, 283.2]
    pd.testing.assert_frame_equal(f, codec.decode(codec.encode(f)),
                                  check_freq=False)


def test_atomic_write_lands_a_readable_file(tmp_path):
    """Pins the gatherer write path end to end: om_parallel._atomic_write once
    called codec without importing it, so every fetched city NameError'd into a
    swallowed handler and the fleet wrote nothing while spending quota."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import om_parallel
    f = _frame(n=12)
    p = tmp_path / "probe_1940-2025.tpy"
    om_parallel._atomic_write(f, p)
    assert p.exists() and not list(tmp_path.glob("*.part"))
    pd.testing.assert_frame_equal(f, codec.read_frame(p), check_freq=False)


@pytest.mark.parametrize("edge", [-3276.7, 3276.7])
def test_values_just_inside_the_sentinel_still_round_trip(edge):
    """The sentinel guard must not cost any representable value."""
    f = _frame(n=3)
    f.iloc[1, 0] = edge
    assert codec.decode(codec.encode(f)).iloc[1, 0] == edge


def test_reads_legacy_csv_gz(tmp_path):
    """A half-migrated cache (or a gatherer that has not pulled) must load."""
    f = _frame(n=20)
    old = tmp_path / "x_1940-2025.csv.gz"
    f.to_csv(old, compression={"method": "gzip", "mtime": 0})
    pd.testing.assert_frame_equal(f, codec.read_frame(old), check_freq=False)


def test_cached_path_accepts_either_format(tmp_path):
    new = tmp_path / "x_1940-2025.tpy"
    old = tmp_path / "x_1940-2025.csv.gz"
    assert codec.cached_path(new) is None
    old.write_bytes(gzip.compress(b"date,t\n"))
    assert codec.cached_path(new) == old          # legacy counts as cached
    codec.write_frame(_frame(n=5), new)
    assert codec.cached_path(new) == new          # current wins once present


def test_write_frame_is_atomic(tmp_path):
    """No .part file may survive, or `git add` would stage a partial blob."""
    p = tmp_path / "c_1940-2025.tpy"
    codec.write_frame(_frame(n=10), p)
    assert p.exists()
    assert not list(tmp_path.glob("*.part"))


def test_temp_name_is_unique_per_process(tmp_path, monkeypatch):
    """Two gatherer processes on one machine (an overrunning cron round meeting
    the next) can fetch the same city; a shared temp name would let one truncate
    the other's buffer and publish the result as complete.

    Observes the ACTUAL temp path write_frame uses - asserting on a name the
    test builds itself would pass even if the shared name came back.
    """
    import os

    seen = []
    real_replace = Path.replace
    monkeypatch.setattr(Path, "replace",
                        lambda self, target: (seen.append(self), real_replace(self, target))[1])
    p = tmp_path / "c_1940-2025.tpy"
    codec.write_frame(_frame(n=5), p)
    assert seen, "write_frame did not go through a temp file"
    assert str(os.getpid()) in seen[0].name, seen[0].name


def test_failed_encode_leaves_no_stray_temp(tmp_path):
    p = tmp_path / "c_1940-2025.tpy"
    bad = _frame(n=3)
    bad.iloc[0, 0] = 12.34                      # rejected by the precision guard
    with pytest.raises(ValueError):
        codec.write_frame(bad, p)
    assert not list(tmp_path.glob("*.part")) and not p.exists()


def test_smaller_than_legacy():
    """The whole point: the compact form must actually beat gzipped CSV."""
    f = _frame(n=31413)
    legacy = len(gzip.compress(f.to_csv().encode(), 9))
    assert len(codec.encode(f)) < legacy / 2
