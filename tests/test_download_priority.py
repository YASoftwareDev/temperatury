"""The download queue must honour country GDP priority *and* still spread work.

Two contracts pull against each other and both are load-bearing:

* every fetcher should cover wealthier countries' cities first (early visitors
  skew that way), so the queue is sorted by `countries.download_priority_key`;
* `--shuffle` exists so that several contributors sharing one repo - or two
  machines of one fleet - do not all download the same cities, because
  `tools/daily-chunk.sh` never refreshes the working tree's `data/`, so a
  fetcher only sees what it personally fetched and a duplicate download is
  quota spent for nothing.

Shuffling the whole queue satisfies the second and makes the first inert;
sorting without shuffling satisfies the first and makes every contributor march
the identical list. The queue therefore randomises *within* the priority window
only - the same window-then-shuffle idiom `--top-pop` already uses.
"""
import random
import sys
from concurrent.futures import Future
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import config
import countries
import om_parallel


def test_priority_key_orders_by_gdp_then_slug():
    rich = min(config.LOCATIONS.values(),
               key=lambda l: countries.download_priority_key(l))
    assert countries.gdp_per_capita(countries.country_code(rich)) == max(
        countries.gdp_per_capita(countries.country_code(l))
        for l in config.LOCATIONS.values())

    # Ties fall back to slug, so the order is stable across runs/machines.
    tied = sorted((l for l in config.LOCATIONS.values()
                   if countries.country_code(l) == "de"),
                  key=countries.download_priority_key)
    assert [l.slug for l in tied] == sorted(l.slug for l in tied)


def test_reference_points_keep_a_country_less_default():
    """Ocean/region points have no country; the key must not crash on them."""
    refs = [l for l in config.LOCATIONS.values()
            if getattr(l, "kind", "city") != "city"]
    assert refs, "expected some non-city reference points"
    for ref in refs:
        assert countries.country_code(ref) is None
        assert countries.download_priority_key(ref)[0] == -countries._GDP_DEFAULT


def _spread(queue, seed):
    """om_parallel's own --shuffle reordering, under a pinned seed."""
    random.seed(seed)
    return om_parallel._spread_within_window(list(queue))


def test_shuffle_stays_inside_the_priority_window():
    queue = [f"city{i:04d}" for i in range(om_parallel._SHUFFLE_WINDOW + 200)]
    out = _spread(queue, seed=1)

    # Priority still decides which cities are in play: the window's membership is
    # untouched (only its internal order moves) and the tail keeps its order.
    assert set(out[:om_parallel._SHUFFLE_WINDOW]) == set(
        queue[:om_parallel._SHUFFLE_WINDOW])
    assert out[om_parallel._SHUFFLE_WINDOW:] == queue[om_parallel._SHUFFLE_WINDOW:]
    assert out != queue, "a shuffle that changes nothing spreads no work"


def test_two_fetchers_do_not_march_the_same_order():
    """The regression this pins: without shuffling, every fetcher's first picks
    are byte-identical, so the second one spends its quota re-downloading."""
    queue = [f"city{i:04d}" for i in range(om_parallel._SHUFFLE_WINDOW + 200)]
    first = _spread(queue, seed=1)[:20]
    second = _spread(queue, seed=2)[:20]
    assert first != second


class _Args:
    """The argparse namespace `run()` expects, for a single offline mean pass."""
    start, end = 1940, 2025
    groups = ["mean"]
    top_pop = 0
    workers = 1
    max_seconds = 0
    shuffle = False


class _NeverCached:
    """Stand-in cache path that reports every city as still missing, so the
    scheduled order does not depend on how full this checkout's data/ is."""

    def exists(self):
        return False


def _scheduled_slugs(monkeypatch, **overrides):
    """Run `om_parallel.run()` with the network stubbed out, returning the city
    slugs in the order it actually scheduled them."""
    args = _Args()
    for key, value in overrides.items():
        setattr(args, key, value)

    seen: list[str] = []

    def _record(chunk, daily, parse, path_fn, start, end):
        seen.extend(loc.slug for loc in chunk)
        return len(chunk), 0

    for group in args.groups:
        daily, parse, _, chunk_sz = om_parallel.GROUPS[group]
        monkeypatch.setitem(om_parallel.GROUPS, group,
                            (daily, parse, lambda l, s, e: _NeverCached(), chunk_sz))
    monkeypatch.setattr(om_parallel, "_fetch_chunk", _record)
    # Serial submission keeps the recorded order deterministic.
    monkeypatch.setattr(om_parallel, "ThreadPoolExecutor",
                        lambda max_workers=None: _SerialExecutor())
    om_parallel.run(args)
    return seen


class _SerialExecutor:
    """Minimal ThreadPoolExecutor stand-in: runs each submission immediately."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *a, **kw):
        # A real Future, already resolved: om_parallel drives these through
        # as_completed(), which needs the genuine internals.
        future: Future = Future()
        future.set_result(fn(*a, **kw))
        return future


def test_run_schedules_the_gdp_priority_order(monkeypatch):
    """Pins the whole point of the change: the queue `run()` actually builds is
    the GDP-priority order, not config's dict order. Without this, reverting the
    sort in run() leaves every other test in this file passing."""
    scheduled = _scheduled_slugs(monkeypatch)

    expected = [l.slug for l in sorted(config.LOCATIONS.values(),
                                       key=countries.download_priority_key)]
    assert scheduled == expected

    dict_order = [l.slug for l in config.LOCATIONS.values()]
    assert scheduled != dict_order, "priority order coincides with dict order"


def test_run_shuffles_only_inside_the_priority_window(monkeypatch):
    """With --shuffle, the cities in play must still be the priority head."""
    ordered = _scheduled_slugs(monkeypatch)
    shuffled = _scheduled_slugs(monkeypatch, shuffle=True)

    window = om_parallel._SHUFFLE_WINDOW
    assert set(shuffled[:window]) == set(ordered[:window])
    assert shuffled[:window] != ordered[:window], "shuffle spread nothing"
    assert shuffled[window:] == ordered[window:], "tail order disturbed"


def test_daily_chunk_asks_for_the_spread_on_every_pass():
    """The window shuffle only protects contributors if the shared entry point
    actually passes --shuffle. Dropping it from a pass is the regression that
    made every contributor fetch the same cities, so pin the invocation."""
    script = (Path(__file__).resolve().parent.parent
              / "tools" / "daily-chunk.sh").read_text(encoding="utf-8")
    calls = [ln for ln in script.splitlines() if "om_parallel.py" in ln
             and not ln.lstrip().startswith("#")]
    assert calls, "expected daily-chunk.sh to invoke om_parallel.py"
    for call in calls:
        assert "--shuffle" in call, f"pass without --shuffle: {call.strip()}"


def test_sync_wrapper_keeps_the_gatherer_non_destructive():
    """tools/sync-and-gather.sh fast-forwards a dedicated clone before gathering.

    Two invariants are easy to "simplify" away and both lose data if they go:
    `reset --hard`/`clean` would discard cities this clone fetched but has not
    pushed yet, and the fast-forward must stay `--ff-only` so a diverged clone
    is never rewritten.
    """
    script = (Path(__file__).resolve().parent.parent
              / "tools" / "sync-and-gather.sh").read_text(encoding="utf-8")
    for destructive in ("reset --hard", "clean -", "push --force", "checkout -f"):
        assert destructive not in script, f"destructive git in gatherer: {destructive}"
    assert "--ff-only" in script
    assert "hash-object" in script, "redundant files must be matched by content"


def test_daily_chunk_still_never_touches_the_checked_out_branch():
    """daily-chunk.sh is data-only by construction because it may run while a
    feature branch is checked out. The sync belongs in the wrapper only - folding
    it in here would fast-forward whatever branch happens to be out."""
    script = (Path(__file__).resolve().parent.parent
              / "tools" / "daily-chunk.sh").read_text(encoding="utf-8")
    body = [ln for ln in script.splitlines() if not ln.lstrip().startswith("#")]
    for mutating in ("git pull", "git merge", "git rebase", "git reset"):
        offenders = [ln for ln in body if mutating in ln]
        assert not offenders, f"{mutating} in daily-chunk.sh: {offenders}"
