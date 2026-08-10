"""Fleet sharding must be disjoint, complete, stable, and own-work-first.

Staggered cron times only make a fleet collision unlikely; `--shard I/N` makes
it impossible while every machine still has owned work: the city list is
hash-partitioned into N disjoint buckets, each machine drains its own bucket
before touching anyone else's, and the fallback tail keeps the dataset complete
even if a peer machine dies. All of that only holds if every machine computes
the identical partition with no coordination - hence the stability tests.
"""
import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import config
import om_parallel


LOCS = sorted(config.LOCATIONS.values(), key=lambda l: l.slug)


def test_partition_is_disjoint_and_complete():
    n = 4
    buckets = [[l for l in LOCS if om_parallel._shard_of(l.slug, n) == i]
               for i in range(n)]
    assert sum(len(b) for b in buckets) == len(LOCS)
    slugs = set()
    for b in buckets:
        assert not slugs.intersection(l.slug for l in b)
        slugs.update(l.slug for l in b)
    # A pathologically empty bucket would idle one machine of the fleet.
    assert all(b for b in buckets)


def test_partition_is_stable_across_calls():
    # crc32, not hash(): the bucket must be identical on every machine and run.
    assert [om_parallel._shard_of(l.slug, 4) for l in LOCS[:50]] == \
           [om_parallel._shard_of(l.slug, 4) for l in LOCS[:50]]


def test_owned_cities_queue_before_fallback():
    mine, rest = om_parallel._apply_shard(LOCS, (2, 4), shuffle=False)
    assert all(om_parallel._shard_of(l.slug, 4) == 1 for l in mine)
    assert all(om_parallel._shard_of(l.slug, 4) != 1 for l in rest)
    assert len(mine) + len(rest) == len(LOCS)
    # Without --shuffle the input order (GDP priority in production) is kept.
    assert mine == [l for l in LOCS if om_parallel._shard_of(l.slug, 4) == 1]


def test_two_shards_never_share_owned_work():
    a, _ = om_parallel._apply_shard(LOCS, (1, 3), shuffle=False)
    b, _ = om_parallel._apply_shard(LOCS, (2, 3), shuffle=False)
    assert not {l.slug for l in a} & {l.slug for l in b}


def test_no_bulk_request_mixes_owned_and_fallback_cities(monkeypatch):
    """The boundary chunk must not smuggle fallback cities into a request.

    Chunking `mine + rest` blindly would pad the last owned chunk with the
    first fallback cities, so a machine would fetch another shard's cities in
    the same bulk request while it still has owned work - exactly the
    collision sharding exists to rule out. Drives run() itself, so a
    regression in its chunk construction cannot slip past.
    """
    from tests.test_download_priority import (_Args, _NeverCached,
                                              _SerialExecutor)

    for shard in ((1, 4), (3, 4), (2, 3)):
        args = _Args()
        args.shard = shard
        chunks: list[list] = []
        monkeypatch.setattr(om_parallel, "_fetch_chunk",
                            lambda chunk, *a: (chunks.append(chunk), (len(chunk), 0))[1])
        daily, parse, _, chunk_sz = om_parallel.GROUPS["mean"]
        monkeypatch.setitem(om_parallel.GROUPS, "mean",
                            (daily, parse, lambda l, s, e: _NeverCached(), chunk_sz))
        monkeypatch.setattr(om_parallel, "ThreadPoolExecutor",
                            lambda max_workers=None: _SerialExecutor())
        om_parallel.run(args)

        idx, total = shard
        owned_flags = [{om_parallel._shard_of(l.slug, total) == idx - 1
                        for l in c} for c in chunks]
        assert chunks and all(len(f) == 1 for f in owned_flags)  # homogeneous
        # All owned chunks strictly before all fallback chunks.
        assert owned_flags == sorted(owned_flags, key=lambda f: f != {True})


def test_shard_arg_parses_and_rejects():
    assert om_parallel._shard_arg("2/4") == (2, 4)
    assert om_parallel._shard_arg(" 1/1 ") == (1, 1)
    for bad in ("0/4", "5/4", "4", "a/b", "1/0", "-1/4", "1/4/2", ""):
        with pytest.raises(argparse.ArgumentTypeError):
            om_parallel._shard_arg(bad)


def test_unknown_group_is_rejected():
    """A typo used to be filtered out silently, leaving an empty group list: the
    run fetched nothing and still exited 0, so an unattended gatherer reported
    "Nothing new to send" forever. Same invisible no-op as a bad shard value."""
    with pytest.raises(SystemExit):
        om_parallel.parse_args(["--groups", "means"])
    assert om_parallel.parse_args(["--groups", "mean,precip"]).groups == \
        ["mean", "precip"]


def test_per_city_write_failure_names_the_city(monkeypatch, capsys):
    """Silence here has twice disguised a total failure as ordinary pending
    work, after quota was already spent: a missing import made every write
    raise, and a slug containing "/" made two cities permanently unwritable."""
    loc = next(l for l in LOCS)
    monkeypatch.setattr(om_parallel.data, "_request", lambda p, w: {"daily": {}})
    monkeypatch.setattr(om_parallel, "_atomic_write",
                        lambda frame, path: (_ for _ in ()).throw(
                            ValueError("cannot write")))
    written, failed = om_parallel._fetch_chunk(
        [loc], "temperature_2m_mean", lambda d, n: None,
        lambda l, s, e: Path("/nonexistent/x.tpy"), 1940, 2025)
    out = capsys.readouterr().out
    assert (written, failed) == (0, 1)
    assert loc.slug in out and "cannot write" in out, out


def test_env_var_feeds_default(monkeypatch):
    monkeypatch.setenv("TEMPERATURY_SHARD", "3/4")
    assert om_parallel.parse_args([]).shard == (3, 4)
    # An explicit flag wins over the environment.
    assert om_parallel.parse_args(["--shard", "1/2"]).shard == (1, 2)
    monkeypatch.setenv("TEMPERATURY_SHARD", "nonsense")
    with pytest.raises(SystemExit):
        om_parallel.parse_args([])
    monkeypatch.delenv("TEMPERATURY_SHARD")
    assert om_parallel.parse_args([]).shard is None
