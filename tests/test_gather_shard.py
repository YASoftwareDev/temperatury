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
    # Without --shuffle the priority order inside each half is untouched.
    assert mine == [l for l in LOCS if om_parallel._shard_of(l.slug, 4) == 1]


def test_two_shards_never_share_owned_work():
    a, _ = om_parallel._apply_shard(LOCS, (1, 3), shuffle=False)
    b, _ = om_parallel._apply_shard(LOCS, (2, 3), shuffle=False)
    assert not {l.slug for l in a} & {l.slug for l in b}


def test_shard_arg_parses_and_rejects():
    assert om_parallel._shard_arg("2/4") == (2, 4)
    assert om_parallel._shard_arg(" 1/1 ") == (1, 1)
    for bad in ("0/4", "5/4", "4", "a/b", "1/0", "-1/4", "1/4/2", ""):
        with pytest.raises(argparse.ArgumentTypeError):
            om_parallel._shard_arg(bad)


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
