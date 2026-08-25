"""The unlisted internal data-status page (``output/internal/index.html``).

"Hidden" here means unlisted, not secret: GitHub Pages is public and static, so
there is no authentication to be had. What the page must actually satisfy is
therefore mechanical and testable - it exists, it tells crawlers to stay away,
and no other file the build emits points at it. The second half is the one that
rots silently: a well-meaning "add it to the nav" or a sitemap that starts
globbing the whole tree would publish it without anything failing.

The figures are checked against a source the page does not itself produce
(``charts/_coverage.json``, written by ``coveragegrid.py`` from the same
file-existence rule), so a drift between the two shows up as a test failure
rather than as two pages quoting different totals.
"""
import contextlib
import datetime as dt
import functools
import http.server
import json
import re
import subprocess
import threading
import types

import pytest

import internal
from tests.conftest import ROOT, build

OUT = ROOT / "output"
PAGE = OUT / "internal" / "index.html"
# Everything the build publishes that could carry a link. .py is excluded on
# purpose: the generator naturally names its own output path.
LINKABLE = ("*.html", "*.js", "*.json", "*.xml", "*.txt", "*.css")


@pytest.fixture(scope="module")
def built():
    build("krakow", "en", client_i18n=True)
    return PAGE.read_text("utf-8")


@pytest.fixture(scope="module")
def disk(built):
    """The data/ listing as it stood just after ``built`` rendered.

    A gatherer adds cache files while the suite runs (twice a day on the machine
    that backfills), so a test that re-lists the directory and compares what it
    finds against the already-rendered page is comparing two different moments -
    a failure that reproduces at 02:20 and nowhere else. One listing, taken next
    to the build, leaves only the build's own duration.
    """
    import codec
    import config
    sizes = {p: p.stat().st_size
             for p in config.DATA_DIR.iterdir() if p.is_file()}
    mean = (codec.cached_path(config.DATA_DIR / f"{l.slug}_1940-2025{codec.SUFFIX}")
            for l in config.LOCATIONS.values())
    # codec stays the authority on which format counts as cached; the listing
    # decides what is IN the snapshot, so the two halves cannot disagree.
    return types.SimpleNamespace(sizes=sizes,
                                 mean=[p for p in mean if p in sizes])


def _kpis(html: str) -> list[str]:
    return re.findall(r'class="k-val">([^<]*)<', html)


def test_the_build_generates_the_page(built):
    assert PAGE.exists()
    assert "<h1>Data status</h1>" in built
    # Every tab is server-rendered; nothing waits on a fetch to have content.
    for key in ("overview", "covmap", "regions", "progress", "gaps"):
        assert f'id="tp-{key}"' in built, key
        assert f'id="tab-{key}"' in built, key


def test_the_page_asks_crawlers_to_stay_away(built):
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in built


def test_nothing_else_the_build_emits_links_to_it(built):
    """Unlisted only holds while it stays unlinked - from the sitemap, the
    language switcher, the omni search index and every other page alike."""
    offenders = []
    for pattern in LINKABLE:
        for path in OUT.rglob(pattern):
            if internal_dir_owns(path):
                continue
            if "internal/" in path.read_text("utf-8", errors="ignore"):
                offenders.append(str(path.relative_to(OUT)))
    assert not offenders, f"these files link to the internal page: {offenders}"


def internal_dir_owns(path) -> bool:
    return (OUT / "internal") in path.parents


def test_it_is_absent_from_the_sitemap_and_the_roster(built):
    sitemap = (OUT / "sitemap.xml").read_text("utf-8")
    assert "internal" not in sitemap
    # The omni search index is built client-side from this roster; a page that
    # is not in it cannot be found by searching.
    base = json.loads((OUT / "charts" / "_base.json").read_text("utf-8"))
    assert not [r for r in base["c"] if "internal" in str(r[0])]


def test_headline_numbers_match_the_coverage_grid(built):
    """The page and the map's overlay must not be able to disagree: both count
    the same file-existence rule over the same roster, so their totals are equal
    or one of them is wrong."""
    cov = json.loads((OUT / "charts" / "_coverage.json").read_text("utf-8"))
    targets = sum(c["m"] for c in cov["cells"])
    covered = sum(c["n"] for c in cov["cells"])
    vals = _kpis(built)
    assert vals[0] == f"{targets:,}", vals
    assert vals[1] == f"{covered:,}", vals
    assert f"{covered / targets * 100:.1f}% of the roster" in built


def test_the_roster_sublabel_halves_sum_to_the_headline():
    """The two halves are counted by different predicates - kind == "city" and
    "has a country code". They pick out the same 21 entries today, so a label
    built from the wrong one is invisible on the real roster; forcing them apart
    is the only way to see which one it uses. They have to keep summing to the
    headline, or the tile contradicts itself."""
    d = internal.collect(1940, 2025)
    assert d["no_cc"] == d["targets"] - d["cities"], (
        "the predicates already differ on the real roster - check that the "
        "Overview and Regions labels still agree before relaxing this")
    d["no_cc"] += 1                      # one city that carries no country code
    html = internal.render(d, "en")
    assert (f'{d["cities"]:,} cities + {d["targets"] - d["cities"]:,} '
            "ocean/region reference points") in html


def test_both_cache_figures_are_what_is_on_disk(built, disk):
    """Both, not just the headline. The sub-label has to name WHICH files its
    number covers: mean_bytes is the COVERED mean series, while 11 mean files on
    disk belong to slugs that have left the roster. A label reading as a
    partition of all 15,482 files while the number means something narrower is
    the defect, not the number."""
    total = sum(disk.sizes.values())
    mean_bytes = sum(disk.sizes[p] for p in disk.mean)
    assert internal._bytes(total) in built
    # The whole sentence, because the wording IS the fix: an earlier label read
    # as a partition of every file in data/ while its number counted only the
    # roster's COVERED mean files.
    assert (f"{len(disk.sizes):,} files in data/; the {len(disk.mean):,} covered "
            f"mean series account for {internal._bytes(mean_bytes)}") in built
    assert "Data directory" in built


def test_the_covered_year_span_reads_dotted_slug_cache_files(tmp_path, monkeypatch):
    """24 roster slugs contain a dot ("st.-petersburg", "sault-ste.-marie"),
    and splitting the filename on the first one dropped 16 real cache files out
    of this scan. Every dated cache file spans 1940-2025 today, so the visible
    number was masked by the other 15,092 - this pins the mechanism, not the
    masked value:
    with the old split the span below reads 1940-2025 instead of 1900-2025."""
    import config
    (tmp_path / "st.-petersburg_1900-2020.tpy").write_text("x")
    (tmp_path / "krakow_1940-2025.tpy").write_text("x")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    d = internal.collect(1940, 2025)
    assert (d["years_lo"], d["years_hi"]) == (1900, 2025)


def test_the_covered_year_span_on_the_real_cache_matches_the_page(built, disk):
    spans = [internal._STEM_DATASET.search(internal._stem(p.name))
             for p in disk.sizes]
    spans = [m for m in spans if m]
    lo = min(int(m.group(1)) for m in spans)
    hi = max(int(m.group(2)) for m in spans)
    assert f'class="k-val">{lo}–{hi}<' in built


def test_the_region_and_country_tables_reconcile_with_the_totals():
    """The tabs must be views on one count, not four independent ones: a region
    or country table that does not add up to the roster is showing numbers
    nothing produced."""
    d = internal.collect(1940, 2025)
    assert sum(r["m"] for r in d["regions"]) == d["targets"]
    assert sum(r["n"] for r in d["regions"]) == d["covered"]
    # Countries exclude the ocean/region reference points, which have no code.
    assert sum(c["m"] for c in d["countries"]) == d["targets"] - d["no_cc"]
    assert all(c["n"] <= c["m"] for c in d["countries"]), "more data than targets"
    # Gaps and the zero-coverage list are selections of those same rows, listed
    # worst first. Asserted as membership + ordering, not by restating the
    # production sort key - that would only re-run the implementation.
    assert ({c["cc"] for c in d["gaps"]}
            == {c["cc"] for c in d["countries"] if c["n"] < c["m"]})
    missing = [c["m"] - c["n"] for c in d["gaps"]]
    assert missing == sorted(missing, reverse=True), "gaps are not worst-first"
    assert ({c["cc"] for c in d["empty"]}
            == {c["cc"] for c in d["countries"] if c["n"] == 0})


def test_the_map_frame_falls_back_when_english_was_not_built(tmp_path):
    """A restricted TEMPERATURY_LANGS build has no en/ folder, and a frame
    pointing at one would be a blank panel where the map should be."""
    for langs, want in ((["en"], "../en/"), (["pl", "de"], "../pl/")):
        out = tmp_path / "-".join(langs)
        page = internal.build_internal_page(out, 1940, 2025, langs)
        html = page.read_text("utf-8")
        assert f'data-src="{want}index.html?embed=1&amp;grid=1#tab=map"' in html, langs


def test_a_build_with_no_language_says_so_rather_than_framing_a_missing_page(tmp_path):
    """With no language at all the fallback had nowhere left to fall: it framed
    ``../en/``, which such a build never writes, so the tab would have rendered
    a blank iframe with nothing on the page explaining it."""
    page = internal.build_internal_page(tmp_path, 1940, 2025, [])
    html = page.read_text("utf-8")
    assert "language folder for it to point at." in html
    assert 'data-src="../' not in html and "int-frame" not in html
    # The tab is still there and the other tabs still carry their figures - a
    # missing map is not a reason to publish a page with a hole in it.
    assert 'id="tp-covmap"' in html and 'class="k-val">' in html


def test_a_checkout_with_no_data_directory_still_builds(tmp_path, monkeypatch):
    """The page is written on the build's last step, after every other file. A
    checkout that has gathered nothing yet has no data/ at all, and that is the
    zero state this page exists to describe - not a FileNotFoundError that
    fails the build once all the real work is already done."""
    import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "never-gathered")
    d = internal.collect(1940, 2025)
    assert (d["covered"], d["n_files"], d["total_bytes"]) == (0, 0, 0)
    assert d["targets"] > 0, "the roster comes from the code, not from data/"
    assert internal._progress({}, {}) == []
    html = internal.render(d, "en")
    assert "class=\"k-val\">\u2014<" in html, "no covered years to show"
    assert "0.0% of the roster" in html


def test_progress_series_lands_exactly_on_the_covered_count():
    """A cumulative count of raw git additions overshoots what is present now by
    every file later renamed or dropped (11,300 additions against 7,784 files
    present, 2026-08-22). Counting only files that still exist is what makes the
    series end where the Overview tab says it does."""
    d = internal.collect(1940, 2025)
    if not d["progress"]:
        pytest.skip("no usable git history for data/ in this checkout")
    assert d["progress"][-1][1] == d["covered"]
    days = [day for day, _ in d["progress"]]
    assert days == sorted(days)
    counts = [n for _, n in d["progress"]]
    assert counts == sorted(counts), "a cumulative series cannot go down"


def test_the_gaps_note_counts_the_rows_it_actually_renders():
    """The note used to say "The 30 countries" while the table renders at most
    30 - so on a smaller roster it contradicted the rows right under it."""
    d = internal.collect(1940, 2025)
    assert len(d["gaps"]) > 30, "roster too small for this test to mean anything"
    assert "The 30 countries with the most roster" in internal.render(d, "en")
    d["gaps"] = d["gaps"][:4]
    small = internal.render(d, "en")
    assert "The 4 countries with the most roster" in small
    assert "The 30 countries" not in small


def test_a_shallow_clone_is_refused_rather_than_charted(tmp_path, monkeypatch):
    """A depth-1 clone's single grafted commit has no parents, so every file in
    it reports as an ADDITION. The walk therefore returns the whole cache dated
    to one day - a "series" asserting the entire roster landed at once - and an
    empty result never arrives to trigger the honest fallback. It has to be
    refused explicitly."""
    import config

    def run(*args, cwd):
        subprocess.run(args, cwd=cwd, check=True, capture_output=True)

    src = tmp_path / "src"
    (src / "data").mkdir(parents=True)
    run("git", "init", "-q", cwd=src)
    run("git", "config", "user.email", "t@example.invalid", cwd=src)
    run("git", "config", "user.name", "t", cwd=src)
    for i in (1, 2, 3):
        (src / "data" / f"f{i}.tpy").write_text("x")
        run("git", "add", "-A", cwd=src)
        run("git", "commit", "-qm", f"add f{i}", cwd=src)
    clone = tmp_path / "clone"
    run("git", "clone", "-q", "--depth", "1", f"file://{src}", str(clone),
        cwd=tmp_path)

    # The premise, demonstrated rather than assumed: three files added across
    # three commits all report as added in the clone's single commit.
    walk = subprocess.run(
        ["git", "log", "--diff-filter=A", "--name-only", "--no-renames",
         "--format=C %ct", "--", "data/"],
        cwd=clone, capture_output=True, text=True, check=True).stdout
    assert walk.count("data/f") == 3, walk

    monkeypatch.setattr(config, "ROOT", clone)
    paths = {f"f{i}": clone / "data" / f"f{i}.tpy" for i in (1, 2, 3)}
    assert internal._progress(paths, internal._first_added({p.name for p in paths.values()})) == []


def _repo(path):
    """A git repo with data/, isolated from the developer's own git config."""
    (path / "data").mkdir(parents=True)
    for args in (("init", "-q", "-b", "trunk"),
                 ("config", "user.email", "t@example.invalid"),
                 ("config", "user.name", "t"),
                 ("config", "commit.gpgsign", "false")):
        subprocess.run(("git", *args), cwd=path, check=True, capture_output=True)
    return path


def _commit(repo, msg):
    subprocess.run(("git", "add", "-A"), cwd=repo, check=True, capture_output=True)
    subprocess.run(("git", "commit", "-qm", msg), cwd=repo, check=True,
                   capture_output=True)


def test_a_file_carried_only_by_a_merge_makes_the_series_refuse(tmp_path,
                                                                monkeypatch):
    """A merge can introduce a file that is in NEITHER parent, and the walk
    simplifies such a merge away - so that file is datable nowhere and would be
    missing from a series drawn anyway, which the panel would then describe as
    ending on the Overview's count "by construction".

    --first-parent would make the merge's own additions visible, but it also
    re-dates every ordinary side-branch file to the merge that landed it, which
    is not "the commit that first added that file" as the panel says (measured
    on this repo: 10 tracked files change attribution). Refusing is the honest
    end of that trade: no misdated points, and no series that quietly omits a
    covered location."""
    import config
    repo = _repo(tmp_path / "r")
    (repo / "data" / "base.tpy").write_text("x")
    _commit(repo, "base")
    subprocess.run(("git", "checkout", "-q", "-b", "side"), cwd=repo, check=True,
                   capture_output=True)
    (repo / "data" / "side.tpy").write_text("x")
    _commit(repo, "side add")
    subprocess.run(("git", "checkout", "-q", "trunk"), cwd=repo, check=True,
                   capture_output=True)
    subprocess.run(("git", "merge", "-q", "--no-commit", "--no-ff", "side"),
                   cwd=repo, capture_output=True)
    (repo / "data" / "only-in-merge.tpy").write_text("x")
    _commit(repo, "merge side, plus a file neither parent has")

    # The premise, demonstrated rather than assumed: the file is in no parent.
    for parent in ("HEAD^1", "HEAD^2"):
        tree = subprocess.run(("git", "ls-tree", "-r", "--name-only", parent,
                               "--", "data/"), cwd=repo, check=True,
                              capture_output=True, text=True).stdout
        assert "only-in-merge" not in tree, parent

    monkeypatch.setattr(config, "ROOT", repo)
    paths = {n: repo / "data" / f"{n}.tpy"
             for n in ("base", "side", "only-in-merge")}
    assert internal._progress(paths, internal._first_added({p.name for p in paths.values()})) == []
    # The refusal is about the undatable file specifically: the two the walk
    # CAN date still chart, so this is not the repo being unusable.
    assert internal._progress(
        {n: paths[n] for n in ("base", "side")},
        internal._first_added({p.name for p in paths.values()}))[-1][1] == 2


def test_a_series_that_cannot_date_every_covered_file_is_refused(tmp_path,
                                                                 monkeypatch):
    """The panel tells the reader its last value equals the Overview tile "by
    construction". A series built from only the files git can date ends BELOW
    the covered count, quietly making that sentence false - so it is refused
    instead, which is what the fallback note has always said would happen to
    "a cache that was never committed"."""
    import config
    repo = _repo(tmp_path / "r")
    for name in ("a", "b"):
        (repo / "data" / f"{name}.tpy").write_text("x")
        _commit(repo, f"add {name}")
    (repo / "data" / "c.tpy").write_text("x")      # present, never committed
    monkeypatch.setattr(config, "ROOT", repo)
    paths = {n: repo / "data" / f"{n}.tpy" for n in ("a", "b", "c")}

    assert internal._progress(paths, internal._first_added({p.name for p in paths.values()})) == []
    # ... and the two committed ones on their own still chart, so the refusal is
    # about the undatable file, not about the repo being unusable.
    assert internal._progress({n: paths[n] for n in ("a", "b")},
                               internal._first_added({p.name for p in paths.values()}))[-1][1] == 2


def test_no_figure_is_invented():
    """Every number rendered comes from the roster or the data directory, so a
    build with an empty coverage window has nothing to show - and shows nothing
    rather than a placeholder."""
    d = internal.collect(1800, 1801)      # no cache file can match
    assert d["covered"] == 0
    assert d["progress"] == []
    html = internal.render(d, "en")
    # Whitespace-normalised: the note is wrapped prose, so where its source
    # happens to break lines is not part of what this pins.
    flat = " ".join(html.split())
    # Nothing covered, so that is what the note says - and no chart, no pace and
    # no placeholder stand in for the series it does not have.
    assert "nothing is covered yet" in flat
    assert "ic-line" not in html and "Current pace" not in flat
    assert _kpis(html)[1] == "0"
    # The coverage figures need no history, so they are still there: hiding them
    # with the chart cost the reader the only number still available.
    assert "0.0% of the roster" in flat and "Still to gather" in flat


def test_the_daily_breakdown_is_in_the_same_unit_as_the_tile_above_it():
    """The Progress table puts a per-day "+ mean" column next to a cumulative
    one that the panel says ends on the Overview's covered count. That only
    holds if the breakdown counts the same files the covered set does - roster
    slugs, this window - so the two columns are checked against each other and
    against the tile rather than assumed to agree."""
    d = internal.collect(1940, 2025)
    if not d["progress"]:
        pytest.skip("no usable git history for data/ in this checkout")
    assert sum(r["mean"] for r in d["daily"]) == d["covered"]
    days = [r["day"] for r in d["daily"]]
    assert days == sorted(days)
    # Every day the cumulative series knows about is a day the breakdown knows
    # about: the series is built from a subset of the same walk.
    assert {day for day, _ in d["progress"]} <= set(days)


def test_the_day_tables_dataset_columns_are_the_datasets_they_name():
    """Nothing asserted anything about the three "+ dataset" columns: swapping
    precip and extremes in the render printed the extremes count under "+ precip"
    on the live page with every test green. The headers are derived from the same
    tuple the cells are, so they cannot drift apart."""
    ts = int(dt.datetime(2026, 8, 24, 12, tzinfo=dt.UTC).timestamp())
    files = {"a_1940-2025.tpy": ts}
    files.update({f"p{i}_1940-2025_precip.tpy": ts for i in range(3)})
    files.update({f"e{i}_1940-2025_extremes.tpy": ts for i in range(7)})
    slugs = {"a"} | {f"p{i}" for i in range(3)} | {f"e{i}" for i in range(7)}
    daily = internal._daily(files, slugs, {(1940, 2025)})
    html = _panel([("2026-08-24", 1)], daily, None)
    body = html.split("<th>Led by</th>", 1)[1]
    # 1 mean, 3 precip, 7 extremes - distinct, so a swapped column is visible.
    assert re.search(r"\+1</td>.*\+3</td>.*\+7</td>", body, re.S)


def test_a_tie_has_no_leader():
    """"Led by" is a claim about the two counts in its own row. Taking the
    maximum outright broke ties by key order, so a day of equal mean and
    precipitation - the rotation lands a fixed 75-location chunk, so equal days
    are ordinary arithmetic, not a freak - printed "Led by Mean temperature"
    beside its own two equal columns."""
    ts = int(dt.datetime(2026, 8, 24, 12, tzinfo=dt.UTC).timestamp())
    files = {f"m{i}_1940-2025.tpy": ts for i in range(3)}
    files.update({f"p{i}_1940-2025_precip.tpy": ts for i in range(3)})
    slugs = {f"m{i}" for i in range(3)} | {f"p{i}" for i in range(3)}
    row = internal._daily(files, slugs, {(1940, 2025)})[0]
    assert row["mean"] == row["precip"] == 3 and row["led"] is None
    html = _panel([("2026-08-24", 3)], [row], None, today=dt.date(2026, 8, 24))
    # A tie is the other kind of uncoloured cell, and the rotation note asks
    # whether anything landed, not whether the cell got a colour: keyed on the
    # leader instead of the total, a tie day read as a stalled fleet.
    assert "slowed, not stalled" in html and "nothing this page counts" not in html
    body = html.split("<th>Led by</th>", 1)[1]
    # The dash and the uncoloured cell were already there for it: nothing had to
    # be added to say "no dataset led this day", only stopped from naming one.
    assert '<span class="int-nil">-</span>' in body and "d-mean" not in body
    assert 'class="d-none"' in internal._cadence_strip(
        [row], today=dt.date(2026, 8, 24))


def test_a_complete_roster_has_no_band_to_describe():
    """The chart drops its "still to gather" label once the line reaches the top,
    but the note kept explaining the band above the line - describing a strip of
    chart that is not there, on the one build the whole tab is counting towards."""
    rows = _day_rows([("2026-08-20", 50), ("2026-08-21", 50)])
    html = _panel([("2026-08-20", 50), ("2026-08-21", 100)], rows, None,
                  targets=100, covered=100)
    assert "the work that is left" not in html
    assert "the line has reached it" in " ".join(html.split())
    assert "locations still to gather" not in html
    # One short of it, the label counts one location, not "1 locations".
    one = _panel([("2026-08-20", 50), ("2026-08-21", 99)], rows, None,
                 targets=100, covered=99)
    assert "1 location still to gather" in one


def test_the_no_series_panel_states_only_what_that_state_implies():
    """Empty series, empty breakdown, no pace - reached either because nothing is
    covered or because the walk refused, and the coverage tile beside the note
    says which. Offered as a disjunction it told a reader looking at a 40%
    covered tile that nothing was covered yet, and a reader with an empty roster
    that their repository might be broken. And no pace tile may appear, because
    no window was measured to report on."""
    # A covered cache with no usable history is the state this branch exists for
    # (shallow clone, undatable file): the tiles must report what the Overview
    # tab reports, not zero.
    flat = " ".join(_panel([], [], None, targets=100, covered=40).split())
    assert "40.0%" in flat and "40 of 100 locations" in flat
    assert "Still to gather" in flat and ">60<" in flat
    assert "Current pace" not in flat and "no arrival date follows" not in flat
    assert "nothing is covered yet" not in flat
    for cause in ("no repository", "a shallow clone", "never committed",
                  "carried only by a merge"):
        assert cause in flat, cause
    # Nothing covered is the other state, and none of those four causes can be
    # it: _progress returns before it ever consults the walk.
    empty = " ".join(_panel([], [], None, targets=100, covered=0).split())
    assert "nothing is covered yet" in empty
    for cause in ("no repository", "a shallow clone", "carried only by a merge"):
        assert cause not in empty, cause
    # ... and the two figures that never needed the history are still shown.
    assert "Roster covered" in flat and "Still to gather" in flat
    # The opening paragraph sends the reader to "the panels below" for the
    # datasets that move while coverage does not. This branch renders none of
    # them - one note stands where all three were.
    assert "panels below are for" not in flat
    live = _panel([("2026-08-24", 100)], _day_rows([("2026-08-24", 100)]), None)
    assert "panels below are for" in " ".join(live.split())


def test_an_uncoloured_led_day_is_not_a_stalled_fleet():
    """The rotation note asked the MARKUP whether anything happened, and a day led
    by apparent temperature is drawn in the same uncoloured cell as a day nothing
    dates to - so a month of apparent-only gathering read as "the fleet is
    stalled" directly above a table naming its leader."""
    ts = int(dt.datetime.now(dt.UTC).timestamp())
    daily = internal._daily({f"a{i}_1940-2025_apparent.tpy": ts for i in range(4)},
                            {f"a{i}" for i in range(4)}, {(1940, 2025)})
    assert daily[0]["led"] == "apparent"        # uncoloured, but not nothing
    html = _panel([("2026-08-24", 1)], daily, None)
    assert "nothing this page counts" not in html
    assert "slowed, not stalled" in html


def test_the_active_window_is_exactly_the_strip_it_describes():
    """The guard was only tested 45 days out, so widening the window by one day -
    counting a day that is NOT in the strip as activity - printed "slowed, not
    stalled" over 30 empty cells with the whole suite green. The strip is closed
    at both ends, so the guard is too: the last day inside counts, and neither
    the day before the strip starts nor one dated after the build day does."""
    today = dt.date(2026, 8, 24)
    inside = today - dt.timedelta(days=internal.CADENCE_DAYS - 1)
    before = inside - dt.timedelta(days=1)
    # A commit timestamp ahead of the build day: the strip stops at today, so
    # such a day has no cell either, and counting it printed the same false
    # sentence over the same 30 empty cells.
    after = today + dt.timedelta(days=1)
    for day, expected in ((inside, "slowed, not stalled"),
                          (before, "nothing this page counts"),
                          (after, "nothing this page counts")):
        rows = _day_rows([(day.isoformat(), 50)])
        html = _panel([(day.isoformat(), 50)], rows, None, today=today)
        assert expected in " ".join(html.split()), day
    # Both really are outside: the strip they would have to appear in has no cell
    # for either, which is the whole reason they may not count as activity. The
    # strip itself is still drawn, because the note above it says every one of
    # its cells is empty - dropped, that sentence stood over nothing at all.
    for day in (before, after):
        rows = _day_rows([(day.isoformat(), 50)])
        assert day.isoformat() not in internal._cadence_strip(rows, today=today)
        html = _panel([(day.isoformat(), 50)], rows, None, today=today)
        assert 'class="int-cad"' in html, day
        # The strip drops the day; the day table below it does not. That is what
        # the strip's docstring offers in exchange for a cell it will not draw,
        # and nothing was checking that the exchange happened.
        assert f"<td>{day.isoformat()}</td>" in html, day


def test_the_rotation_note_does_not_call_a_stalled_fleet_merely_slowed():
    """The sentence sits directly above the strip and describes it. Ungated, it
    told the reader "slowed, not stalled" over a month of empty cells - the strip
    exists precisely so a stalled fleet looks stalled. What it may NOT say is
    that the fleet stalled: the strip sees only entries this page counts, so a
    month of committing caches for departed slugs, or from another year, is
    invisible to it."""
    old = _day_rows([("2026-06-01", 50), ("2026-07-10", 50)])
    html = _panel([("2026-06-01", 50), ("2026-07-10", 100)], old, None,
                  today=dt.date(2026, 8, 24))
    assert "slowed, not stalled" not in html
    assert "nothing this page counts has landed on any of those days" in " ".join(html.split())
    # ... and it says it the usual way when the strip has anything in it. The
    # day is pinned: read off the wall clock, this half of the test silently
    # inverted 30 days after it was written.
    live = _day_rows([("2026-08-20", 50), ("2026-08-24", 50)])
    assert "slowed, not stalled" in _panel([("2026-08-24", 100)], live, None,
                                           today=dt.date(2026, 8, 24))


def test_the_first_point_sentence_describes_the_first_point():
    """The prose asserts a number and a date about the chart beside it. Pointed at
    series[-1] instead it read "it stands at 7,934 because that is what had been
    committed by 2026-08-24, and the last is the same 7,934" - false about the
    chart, and nothing failed."""
    rows = _day_rows([("2026-08-10", 40), ("2026-08-24", 60)])
    # Whitespace-normalised: the note is wrapped prose in the source.
    flat = " ".join(_panel([("2026-08-10", 40), ("2026-08-24", 100)],
                           rows, None).split())
    assert "stands at 40 because that is what had been committed by 2026-08-10" in flat
    assert "the last is the same 100" in flat


def test_the_projection_follows_the_average_on_the_branch_the_page_takes():
    """The clamped branch (the line meeting the roster inside the horizon) was
    pinned; the ordinary one - the branch every build at 24% coverage takes - was
    not, so doubling the slope passed. The endpoint must be the window's average
    carried over the horizon."""
    rows = _day_rows([("2026-08-10", 0), ("2026-08-24", 90)])
    pace = internal._pace(rows, 1_000, 30_000, today=dt.date(2026, 8, 24))
    svg = internal._runway_svg([("2026-08-10", 500), ("2026-08-24", 1_000)],
                               30_000, pace)
    assert _proj_days(svg, dt.date(2026, 8, 10), dt.date(2026, 8, 24)) == \
        internal.PACE_HORIZON          # the full horizon, not a clamped crossing
    pts = re.search(r'class="ic-proj" points="([^"]+)"', svg).group(1).split()
    (_, y0), (_, y1) = (tuple(float(v) for v in p.split(",")) for p in pts)
    ih = 320 - 18 - 34
    gained = pace["per_day"] * internal.PACE_HORIZON
    assert (y0 - y1) == pytest.approx(ih * gained / 30_000, abs=0.2)


def test_the_goal_bar_segments_are_gathered_and_remaining():
    """Both widths come from the same helper, so pointing the second at `covered`
    drew a bar 24% + 24% wide with half the track blank, under a label saying
    25,044 remaining - and no test looked at the widths."""
    html = _panel([("2026-08-24", 2_500)], _day_rows([("2026-08-24", 2_500)]),
                  None, targets=10_000)
    bar = html.split('class="int-goal"', 1)[1].split("</div>", 1)[0]
    assert 'class="g-done" style="width:25.00%"' in bar
    assert 'class="g-left" style="width:75.00%"' in bar


def test_the_tables_cumulative_column_is_the_number_the_tile_reports():
    """The column is built by a running sum in the renderer, and nothing read the
    rendered cell: summing the day TOTALS instead of the mean column prints
    "16,321 / 49.5%" in a table sitting directly under a tile that reads 24.1%,
    beside prose promising the two agree by construction."""
    d = internal.collect(1940, 2025)
    if not d["progress"]:
        pytest.skip("no usable git history for data/ in this checkout")
    html = internal.render(d, "en")
    body = html.split("<th>Led by</th>", 1)[1]
    newest = re.search(r"<tr><td>[^<]+</td>"
                       r'<td class="int-num">([\d,]+)</td>'
                       r'<td class="int-num">([\d.]+)%</td>', body)
    assert newest.group(1) == f'{d["covered"]:,}'
    assert newest.group(2) == f'{internal._pct(d["covered"], d["targets"]):.1f}'


def test_this_years_current_year_cache_is_counted_by_the_build():
    """_daily takes the acceptable windows from collect, and the tests that pin
    the windows all hand them in themselves - so dropping the build year at the
    call site left every one of them green while the current-year column went to
    zero on the real cache."""
    import config
    d = internal.collect(1940, 2025)
    if not d["daily"]:
        pytest.skip("no usable git history for data/ in this checkout")
    # Counted over the files the history can date, not the directory listing: a
    # gatherer runs on this machine twice a day, and a cache file it has written
    # but not yet committed is a documented state - one would otherwise fail this
    # test rather than skip it, and re-listing after collect() would compare two
    # moments besides.
    cur = dt.date.today().year
    dated = internal._first_added({p.name for p in config.DATA_DIR.iterdir()
                                   if p.is_file()})
    want = {internal._dataset_of(n)[0] for n in dated
            if internal._dataset_of(n)[1:] == ("current", (cur, cur))
            and internal._dataset_of(n)[0] in config.LOCATIONS}
    assert sum(r["current"] for r in d["daily"]) == len(want) > 0


def test_a_checkout_with_history_and_a_cache_does_not_degrade():
    """Every real-data test here skips when the tab has no series - the honest
    response to a shallow clone. That also makes a mutation that BLANKS the tab
    invisible: the run stays green while the page loses its chart, its table and
    both pace tiles. In a checkout that has both history and a committed cache -
    the deploy's own condition, fetch-depth: 0 - it must not degrade."""
    import config
    names = {p.name for p in config.DATA_DIR.iterdir() if p.is_file()}
    if not names:
        pytest.skip("no cache in this checkout")
    dated = internal._first_added(names)
    if dated is None or len(dated) != len(names):
        # The premise is a checkout whose cache is committed. A gatherer writes
        # files here twice a day, and the tab's documented answer to one that is
        # not committed yet is the refusal note - which is what the siblings skip
        # on, not something this test may read as a regression.
        pytest.skip("cache not fully committed in this checkout")
    d = internal.collect(1940, 2025)
    assert d["progress"] and d["daily"], "a full checkout has to chart"
    # And the pace follows the window, both ways: present when the last
    # PACE_WINDOW days gained locations, absent when they did not.
    today = dt.datetime.now(dt.UTC).date()
    start = today - dt.timedelta(days=internal.PACE_WINDOW - 1)
    gained = sum(r["mean"] for r in d["daily"]
                 if start <= dt.date.fromisoformat(r["day"]) <= today)
    assert bool(d["pace"]) == (gained > 0)


def test_a_location_in_both_encodings_counts_once():
    """codec.cached_path counts a location once when both encodings are present -
    that is what "covered" means. Counting FILES here made the mean column exceed
    the covered total the prose beside it promises it equals, and doubled the pace
    built from the same column. daily-chunk.sh ships leftover .csv.gz on purpose,
    so the pair is designed for."""
    import codec
    old, new = 1_753_000_000, 1_754_000_000
    files = {f"a_1940-2025{codec.LEGACY_SUFFIX}": old,
             f"a_1940-2025{codec.SUFFIX}": new,
             f"b_1940-2025{codec.SUFFIX}": new}
    rows = internal._daily(files, {"a", "b"}, {(1940, 2025)})
    assert sum(r["mean"] for r in rows) == 2          # two locations, three files
    # ... on the day of the file codec.cached_path returns for the entry, which is
    # the file _progress dates the same location from. Dating it from the earlier
    # encoding instead puts the chart and the table on different days for one
    # location, and the prose asserts the chart's number.
    day = dt.datetime.fromtimestamp(new, dt.UTC).date().isoformat()
    assert [(r["day"], r["mean"]) for r in rows] == [(day, 2)]
    assert dt.datetime.fromtimestamp(old, dt.UTC).date().isoformat() not in str(rows)
    # The strip counts the same unit it was folded into, or a day of two files
    # for one location reads as one file rather than one entry.
    strip = internal._cadence_strip(rows, today=dt.date.fromisoformat(day))
    assert "2 cache entries (mean temperature +2)" in strip


def test_a_folded_entry_dates_from_the_same_file_whatever_the_walk_listed_first():
    """A current-year cache and its _current_extremes half are one entry, and the
    two halves can land on different days. Ranked by encoding alone they tied, so
    the day the strip drew depended on which name git log happened to emit first -
    the same cache rendering two different histories."""
    import codec
    early = int(dt.datetime(2026, 8, 20, 12, tzinfo=dt.UTC).timestamp())
    late = int(dt.datetime(2026, 8, 24, 12, tzinfo=dt.UTC).timestamp())
    windows = {(1940, 2025), (2026, 2026)}
    bare, half = f"x_2026_current{codec.SUFFIX}", f"x_2026_current_extremes{codec.SUFFIX}"
    # The canonical file is the LATER one here on purpose: with the halves merely
    # tied, the earliest timestamp would win and the day would still look right
    # for the wrong reason.
    for order in ({bare: late, half: early}, {half: early, bare: late}):
        rows = internal._daily(order, {"x"}, windows)
        # The canonical name wins, whatever the walk listed first - and it is the
        # file the Overview tab counts for the same location.
        assert [(r["day"], r["current"]) for r in rows] == [("2026-08-24", 1)]


def test_an_empty_cell_never_claims_more_than_the_breakdown_knows():
    """The strip is drawn from the FILTERED breakdown, so an empty cell cannot
    mean "no cache file dates to this day": the day may hold files whose slug has
    left the roster (11 of them in this checkout) or whose year window the page
    does not count - the state the 1 January rollover produces for every
    current-year cache of the year before."""
    day = int(dt.datetime(2026, 8, 21, 12, tzinfo=dt.UTC).timestamp())
    # The state the wording exists for: a counted entry on an earlier day, and a
    # day whose only dated file the filter drops. The strip must render that day
    # as a cell - an all-filtered history returns "" and would let this pass
    # without ever producing the sentence.
    earlier = int(dt.datetime(2026, 8, 19, 12, tzinfo=dt.UTC).timestamp())
    rows = internal._daily({"kept_1940-2025.tpy": earlier,
                            "gone_1940-2025.tpy": day}, {"kept"}, {(1940, 2025)})
    strip = internal._cadence_strip(rows, today=dt.date(2026, 8, 21))
    assert "2026-08-21: no counted cache entry dates to this day" in strip


def test_a_file_kind_is_read_off_its_own_name():
    """The breakdown has nothing but the file name to go on. The current-year
    pairs are the case that bites: ``_2026_current_extremes`` is an extremes
    file by suffix and a current-year file by shape, and counting it under
    extremes would inflate a dataset the coverage map reports."""
    assert internal._dataset_of("krakow_1940-2025.tpy") == ("krakow", "mean",
                                                            (1940, 2025))
    assert internal._dataset_of("krakow_1940-2025_precip.tpy")[1] == "precip"
    assert internal._dataset_of("krakow_2026_current.tpy") == ("krakow",
                                                               "current",
                                                               (2026, 2026))
    assert internal._dataset_of("krakow_2026_current_extremes.tpy")[1] == "current"
    # A slug with a dot survives - _stem exists because 24 of them have one.
    assert internal._dataset_of("st.-petersburg_1940-2025.tpy")[0] == "st.-petersburg"
    # Nothing the stems recognise: no slug, so the roster filter drops it.
    assert internal._dataset_of("_global.json") == ("", "other", None)
    # A kind that does not exist yet keeps its slug and its window, so it marks
    # the day it landed on instead of vanishing from the breakdown. Only the
    # dropping half of that promise was pinned; a future gatherer adding a
    # dataset would have found out from the live page.
    assert internal._dataset_of("krakow_1940-2025_humidity.tpy") == (
        "krakow", "other", (1940, 2025))
    # A VERSIONED kind is the other half of that promise, and it goes the other
    # way: the suffix group takes letters only, so the digit drops the whole name
    # to no slug and the roster filter removes it. The docstring says so rather
    # than the group being widened, because no versioned kind exists.
    assert internal._dataset_of("krakow_1940-2025_precip_v2.tpy") == (
        "", "other", None)
    ts = int(dt.datetime(2026, 8, 24, 12, tzinfo=dt.UTC).timestamp())
    row = internal._daily({"krakow_1940-2025_humidity.tpy": ts}, {"krakow"},
                          {(1940, 2025)})[0]
    assert row["day"] == "2026-08-24"      # it marks the day it landed on
    assert row["other"] == 1 and row["led"] == "other"


def test_last_years_current_year_cache_is_not_this_year_s():
    """The Overview tab counts current-year files for the build's own year. The
    breakdown counted any of them, so a stale 2025 file landed under "Current
    year" in a 2026 build - the two tabs describing the same directory
    differently."""
    ts = int(dt.datetime(2026, 1, 1, 12, tzinfo=dt.UTC).timestamp())
    files = {"krakow_2025_current.tpy": ts, "krakow_2026_current.tpy": ts}
    rows = internal._daily(files, {"krakow"}, {(1940, 2025), (2026, 2026)})
    assert [r["current"] for r in rows] == [1]


def test_a_cache_from_another_window_is_not_counted(monkeypatch):
    """A cache left behind by an earlier coverage window is a real file, but it
    is not one of the locations any tile on this page counts - and counting it
    would push the breakdown's mean column past the covered total it is printed
    next to."""
    first = {"a_1940-2025.tpy": 1_754_000_000,
             "a_1950-2020.tpy": 1_754_000_000,
             "b_1940-2025.tpy": 1_754_000_000}
    rows = internal._daily(first, {"a", "b"}, {(1940, 2025)})
    assert [r["mean"] for r in rows] == [2]
    # ... and a slug that left the roster is dropped too.
    assert internal._daily(first, {"a"}, {(1940, 2025)})[0]["mean"] == 1


def _day_rows(spec, precip=7):
    """[(day, mean_added)] as _daily returns it, for the pace tests.

    Every row carries enrichment files too: with total == mean, a pace that
    summed the wrong column - counting precipitation files as locations gained -
    passed every test in this file. On the live data that mutation moves the
    arrival date 41 days earlier."""
    return [{"day": day, "mean": n, "precip": precip, "total": n + precip,
             "led": "mean" if n else ("precip" if precip else None),
             **{k: 0 for k in internal.DS_KEYS if k not in ("mean", "precip")}}
            for day, n in spec]


def test_the_pace_counts_calendar_days_not_the_days_that_worked():
    """The rotation gives mean coverage roughly one day in three, so a pace
    averaged over "days that appear in the series" reports the pace of the good
    days as the pace of the fleet - three times the truth. The window is
    calendar days ending on the build's own day, and the days in between count
    as the zeros they are."""
    today = dt.date(2026, 8, 24)
    rows = _day_rows([("2026-08-16", 900), ("2026-08-19", 900),
                      ("2026-08-22", 900)])
    pace = internal._pace(rows, covered=2_700, targets=12_600, today=today)
    assert pace["window"] == 9 and pace["gained"] == 2_700
    # The mean column, not the day totals: those rows hold precipitation files
    # too, and counting them would report locations the fleet never gathered.
    assert sum(r["total"] for r in rows) > 2_700
    assert pace["per_day"] == 300                     # 2,700 / 9, not / 3
    assert pace["remaining"] == 9_900
    assert pace["days_left"] == 33                    # 9,900 / 300
    assert pace["eta"] == "2026-09-26"                # 24 Aug + 33 days
    assert pace["as_of"] == today.isoformat()


def test_a_fleet_that_stopped_reads_as_stopped():
    """The window ends on the build day, not on the last day with data, so a
    gatherer that died a fortnight ago cannot keep reporting the pace it had
    while it ran."""
    rows = _day_rows([("2026-07-20", 0), ("2026-08-01", 5_000),
                      ("2026-08-02", 5_000)])
    # The zero row is what makes this test the one it says it is: without history
    # reaching back past the window, _pace refuses on the short-history guard and
    # a window that ended on the last day WITH data would pass unnoticed.
    assert internal._pace(rows, 10_000, 30_000, today=dt.date(2026, 8, 24)) is None


def test_no_pace_is_projected_from_a_window_the_history_does_not_cover():
    """A cache committed for the first time yesterday would otherwise average
    its whole backlog over nine days and project an arrival date from one day of
    evidence."""
    rows = _day_rows([("2026-08-23", 4_000), ("2026-08-24", 100)])
    assert internal._pace(rows, 4_100, 30_000, today=dt.date(2026, 8, 24)) is None
    # The same rows with the history reaching back far enough do project.
    rows = _day_rows([("2026-08-10", 0)]) + rows
    assert internal._pace(rows, 4_100, 30_000, today=dt.date(2026, 8, 24))


def test_a_complete_roster_projects_nothing():
    """The history has to reach back past the window, or this passes on the
    short-history refusal and never reaches the completion one: with the rows
    starting inside the window, deleting `covered >= targets` from _pace leaves
    it green."""
    rows = _day_rows([("2026-08-10", 10), ("2026-08-24", 10)])
    assert internal._pace(rows, 29_999, 30_000, today=dt.date(2026, 8, 24))
    assert internal._pace(rows, 30_000, 30_000, today=dt.date(2026, 8, 24)) is None


def test_the_runway_axis_is_the_roster_not_the_series_own_maximum():
    """Scaling to the series' own top makes any rate look like an arrival: the
    line ends in the top right corner whatever it did. The top guide is the
    roster, so 100 locations out of 30,000 draw as 100 out of 30,000."""
    series = [("2026-08-10", 40), ("2026-08-24", 100)]
    svg = internal._runway_svg(series, 30_000, None)
    assert ">30,000<" in svg and ">100 (0.3%)<" in svg
    assert "29,900 locations still to gather" in svg
    # Decoded from the drawing, not from the labels: scaled to the series' own
    # top the line ends ON the top guide, and the four guides collapse onto one
    # row - both invisible to any assertion over the text.
    ys = [float(p.split(",")[1])
          for p in re.search(r'class="ic-line" points="([^"]+)"', svg).group(1).split()]
    top_guide, base = 18.0, 18.0 + (320 - 18 - 34)
    assert base - ys[-1] == pytest.approx((base - top_guide) * 100 / 30_000, abs=0.2)
    guides = sorted({round(float(y), 1) for y in
                     re.findall(r'class="ic-grid" x1="[\d.]+" y1="([\d.]+)"', svg)})
    assert len(guides) == 5, guides


def test_the_cadence_strip_ends_on_the_build_day_so_a_stall_is_visible():
    """One cell per UTC day, not one cell per day that committed something: a
    skipped day would close the gap and the strip would show an unbroken
    rotation while the fleet was down."""
    rows = _day_rows([("2026-08-20", 75), ("2026-08-22", 900)])
    strip = internal._cadence_strip(rows, today=dt.date(2026, 8, 24))
    assert strip.count('<span class="d-') == 5        # 20th through 24th
    assert strip.count('class="d-none"') == 3         # 21st, 23rd, 24th
    assert "2026-08-21: no counted cache entry dates to this day" in strip
    assert strip.endswith("<span>2026-08-24</span></div>")


def _tile(html: str, label: str) -> str:
    """One KPI card, so a test can pin what a tile says rather than what the page
    says somewhere. Bounded at both ends - the last card has no card after it to
    stop at, and an unbounded slice would run to the end of the document and
    quietly restore the "somewhere on the page" it exists to rule out."""
    for card in html.split('<div class="int-kpis">', 1)[1].split('<div class="int-kpi">'):
        if f'<div class="k-lbl">{label}</div>' in card:
            return card.split('<div class="int-goal"', 1)[0]
    raise AssertionError(f"no {label!r} tile in this panel")


def _panel(series, daily, pace, targets=30_000, covered=None, today=None):
    """The Progress panel from the same dict `collect` hands it. `covered` is what
    the panel falls back to with no series - the state where the coverage tiles
    still render and the history-sourced half does not."""
    return internal._progress_panel(
        {"progress": series, "daily": daily, "pace": pace, "targets": targets,
         "covered": covered if covered is not None
         else (series[-1][1] if series else 0)}, today=today)


def test_the_no_pace_tiles_state_nothing_the_page_did_not_measure():
    """_pace refuses for three reasons and the tile has to name the one that
    applies, because the panel holds the same three inputs _pace refused on.
    Naming all three at once put "the last 9 days gained nothing" over a table
    row of +500 on a complete roster, and offered "the roster is complete" beside
    a tile reading 28,000 still to gather. Each state is checked against the
    panel's own numbers, not just for the absence of a measured-looking figure."""
    # Deliberately NOT the wall-clock day: a branch that read the clock instead
    # of the day the build stamped would pass against a date that is today.
    today = dt.date(2027, 5, 20)
    W = internal.PACE_WINDOW

    def day(n):
        return (today - dt.timedelta(days=n)).isoformat()

    short = _day_rows([(day(1), 4_000), (day(0), 100)])
    html = _panel([(day(1), 4_000), (day(0), 4_100)], short, None, today=today)
    assert f"shorter than that {W}-day window" in html
    # The other two are false here: 4,100 of 30,000, and 4,000 gained yesterday.
    assert "gained no location" not in html and "roster is complete" not in html
    assert '<div class="k-val">0<span class="k-unit"> per day' not in html
    # ... and no dashed continuation is described, because none is drawn.
    assert "ic-proj" not in html and "dashed continuation" not in html

    full = _day_rows([(day(8), 500), (day(2), 500)])
    html = _panel([(day(8), 500), (day(2), 1_000)], full, None,
                  targets=1_000, covered=1_000, today=today)
    assert "roster is complete" in html and "gained no location" not in html

    # Two rows on purpose: the history reaches back well before the window and
    # is still committing precipitation inside it, which is the shape the group
    # rotation actually produces. Read off the newest day instead of the oldest,
    # the tile called that history too short to measure.
    stalled = _day_rows([(day(23), 2_000), (day(1), 0)])
    html = _panel([(day(23), 2_000)], stalled, None, targets=30_000,
                  covered=2_000, today=today)
    assert "gained no location" in html and "roster is complete" not in html
    assert "shorter than" not in html

    # The boundary between the last two causes, from both sides. A history
    # beginning exactly on the window's first day COVERS the window, so a day of
    # precipitation and no mean is a window that gained nothing; one day later is
    # a history too short to measure. Either threshold shifted by a day named the
    # other cause, and the whole suite stayed green.
    for n, expected, wrong in ((W - 1, "gained no location", "shorter than"),
                               (W - 2, f"shorter than that {W}-day window",
                                "gained no location")):
        rows = _day_rows([(day(n), 0 if n == W - 1 else 500)])
        html = _panel([(day(n), 100)], rows, None, targets=30_000, covered=100,
                      today=today)
        assert expected in html and wrong not in html, n


def test_a_one_day_series_does_not_describe_a_chart_that_is_not_there():
    """A build whose cache landed in a single commit has one point: _runway_svg
    draws nothing, and prose about "the band above the line" would be describing
    a chart the reader cannot see."""
    rows = _day_rows([("2026-08-24", 100)])
    html = _panel([("2026-08-24", 100)], rows, None)
    assert "<svg" not in html
    assert "band above the line" not in html
    assert "A line needs two days" in html


def test_a_one_day_series_with_a_pace_still_describes_no_dashed_line():
    """A cache committed in a single day draws no chart, and _pace can still
    return a rate - the note's projection clause is gated on the chart, not on
    the pace alone. Without that half of the guard the page describes a dashed
    continuation on a chart it did not render."""
    rows = _day_rows([("2026-08-10", 0), ("2026-08-24", 40)])
    pace = internal._pace(rows, 40, 30_000, today=dt.date(2026, 8, 24))
    assert pace, "the window has to yield a pace for this to test anything"
    html = _panel([("2026-08-24", 40)], rows, pace)
    assert "<svg" not in html and "dashed continuation" not in html


def test_a_series_with_no_dated_day_renders_no_prose_about_a_strip():
    """The rotation heading, its note, the legend and the day table are all
    drawn from the day breakdown. With a series but no breakdown the section
    rendered as a heading, a sentence telling the reader every cell in a strip
    that was not there was empty, a legend, and a table of column headings with
    no rows under it."""
    html = _panel([("2026-08-24", 100)], [], None)
    assert "Which group led each day" not in html
    assert "the strip below is empty" not in html
    assert "int-cad" not in html and "int-legend" not in html
    assert "<th>Led by</th>" not in html
    # The coverage half needs no history and still renders.
    assert "Distance to a complete roster" in html and "100 gathered" in html


def test_a_history_dated_past_the_build_day_is_named_as_that():
    """_pace refuses a wholly future-dated history under its short-history test,
    and the tile repeated that reason beside a table listing more days than the
    window has. The state is a clock that ran ahead, not a history that is too
    short, and the tile names it."""
    today = dt.date(2026, 8, 24)
    spec = [((today + dt.timedelta(days=n)).isoformat(), 50)
            for n in range(1, internal.PACE_WINDOW + 5)]
    rows = _day_rows(spec)
    html = _panel([(spec[-1][0], 650)], rows, None, today=today)
    # Through _esc, like every other tile subtitle: the apostrophe is escaped.
    assert internal._esc(
        "falls after this build's own day (2026-08-24)") in html
    assert "shorter than that" not in html
    # The table really does list more days than the window, which is what made
    # the old wording false rather than merely imprecise.
    assert html.count("<tr><td>") > internal.PACE_WINDOW


def test_a_day_led_by_a_dataset_with_no_column_is_not_a_row_of_zeros():
    """The table carries a count column for three of the six datasets a day can
    be led by. A day of nothing but apparent-temperature files printed three
    zeros and a "Led by Apparent temperature" pill beside them, which reads as a
    day that committed nothing and mislabelled it."""
    row = {"day": "2026-08-24", "total": 500, "led": "apparent",
           **{k: 0 for k in internal.DS_KEYS}}
    row["apparent"] = 500
    html = _panel([("2026-08-24", 100)], [row], None, today=dt.date(2026, 8, 24))
    assert '<th class="int-num">+ all datasets</th>' in html
    body = html.split("<th>Led by</th>", 1)[1]
    assert body.count('class="int-nil">0<') == 3       # mean, precip, extremes
    assert "+500" in body and "Apparent temperature" in body


def test_the_cadence_tooltip_accounts_for_every_file_it_counts():
    """The strip's empty cell means "no counted cache entry dates to it" - that is
    the stall signal the panel promises. A day of apparent-temperature files has
    no leader among the four coloured datasets, and counting only those four made
    it claim exactly that."""
    ts = int(dt.datetime(2026, 8, 24, 12, tzinfo=dt.UTC).timestamp())
    # Through _daily, not hand-built rows: that a day of apparent files gets no
    # coloured leader is the half of this the strip depends on.
    day = internal._daily({f"a{i}_1940-2025_apparent.tpy": ts for i in range(7)},
                          {f"a{i}" for i in range(7)}, {(1940, 2025)})
    assert day[0]["led"] == "apparent" and day[0]["total"] == 7
    strip = internal._cadence_strip(day, today=dt.date(2026, 8, 24))
    assert "7 cache entries (apparent temperature +7)" in strip
    # Uncoloured, because only four datasets have a colour token - but the cell
    # is not the empty one that means no counted entry dates to that day.
    assert '<span class="d-none"' in strip
    # A leader among the coloured four never hides the rest of the day either.
    files = {f"a{i}_1940-2025_apparent.tpy": ts for i in range(500)}
    files["b_1940-2025.tpy"] = ts
    day = internal._daily(files, {f"a{i}" for i in range(500)} | {"b"}, {(1940, 2025)})
    strip = internal._cadence_strip(day, today=dt.date(2026, 8, 24))
    assert ("501 cache entries (mean temperature +1, "
            "apparent temperature +500)") in strip
    # And the leader is the dataset that actually led: scoped to the four the
    # strip colours, a table column headed "Led by" named the runner-up.
    assert day[0]["led"] == "apparent"
    html = _panel([("2026-08-24", 1)], day, None)
    assert '<span class="int-led d-none">Apparent temperature</span>' in html
    assert "d-mean" not in html.split('<th>Led by</th>')[1]


def test_the_arrival_date_is_an_exact_ceiling():
    """days_left was ceil'd in floats, where remaining / (gained / window) lands a
    hair under a whole number and rounds up to the next one - an arrival date a
    day later than the window actually says.

    The pair matters: at gained=1, remaining=1 both forms give 9, so a test built
    on it pins nothing. 23 gained and 69 to go is exactly 27 days, and the float
    form says 28."""
    rows = _day_rows([("2026-08-10", 0), ("2026-08-24", 23)])
    pace = internal._pace(rows, 29_931, 30_000, today=dt.date(2026, 8, 24))
    assert (pace["gained"], pace["remaining"]) == (23, 69)
    assert pace["days_left"] == 27 and pace["eta"] == "2026-09-20"


def test_a_pace_below_one_is_shown_as_the_fraction_it_was_computed_from():
    """Rounding put "0 per day" on the tile beside an arrival date 900 days out -
    a figure the window never measured, next to a date computed from the figure
    it did."""
    rows = _day_rows([("2026-08-16", 0), ("2026-08-24", 1)])
    pace = internal._pace(rows, 100, 200, today=dt.date(2026, 8, 24))
    html = _panel([("2026-08-16", 99), ("2026-08-24", 100)], rows, pace, targets=200)
    assert '<div class="k-val">0<span class="k-unit"> per day' not in html
    assert "0.11" in html and pace["eta"] in html
    assert "(1 location gained)" in html          # not "1 locations"


def _proj_days(svg, first_day, last_drawn_day, horizon=internal.PACE_HORIZON):
    """How many days the dashed projection spans, decoded back through the same
    transform _runway_svg used to draw it."""
    pts = re.search(r'class="ic-proj" points="([^"]+)"', svg).group(1).split()
    (x0, _), (x1, _) = (tuple(float(v) for v in p.split(",")) for p in pts)
    span = last_drawn_day.toordinal() + horizon - first_day.toordinal()
    return round((x1 - x0) / ((920 - 68 - 116) / span), 2)


def test_the_chart_and_the_tile_give_the_same_arrival_date():
    """The tile counts from the build day; the series ends on the last day a mean
    file was committed, which the group rotation makes a different day two turns
    in three. Anchored on the series, the dashed line crossed the roster before
    the tile's date - twice here, and the chart's crossing was two days in the
    past."""
    rows = _day_rows([("2026-08-10", 50), ("2026-08-20", 40)])
    pace = internal._pace(rows, 90, 100, today=dt.date(2026, 8, 24))
    assert pace["as_of"] == "2026-08-24" and pace["days_left"] == 3
    svg = internal._runway_svg([("2026-08-10", 50), ("2026-08-20", 90)], 100, pace)
    # 10 still to gather at 40/9 a day: the line crosses 2.25 days after the day
    # the tile counts from, and the tile ceils that same 2.25 to its 3.
    assert _proj_days(svg, dt.date(2026, 8, 10), dt.date(2026, 8, 24)) == 2.25
    assert ">2026-08-24<" in svg      # the axis names the day it is anchored on
    # The flat run to the build day is drawn, not measured: every point with a
    # tooltip is a day a mean file was actually committed. Carried as a data
    # point instead, the chart offered "2026-08-24: 90 covered" as a commit date
    # in a panel whose note says each point is one.
    assert re.findall(r"<title>([^:]+):", svg) == ["2026-08-10", "2026-08-20"]
    # ... and it is DRAWN: the line carries a third point at the build day, which
    # the projection then leaves from. Removed, every assertion above stayed
    # green while the filled area cut diagonally back to the baseline from the
    # last commit day and the dashed line started where the line never reached.
    line = re.search(r'class="ic-line" points="([^"]+)"', svg).group(1).split()
    proj = re.search(r'class="ic-proj" points="([^"]+)"', svg).group(1).split()
    assert len(line) == 3 and line[-1] == proj[0]


def test_the_anchor_never_moves_a_series_backwards():
    """The anchor closes the gap the group rotation opens, which is always the
    same one: a series ending BEFORE the build day. A series ending after it
    needs a commit dated in the future, and the chart then keeps the dates the
    commits give it - clamped to the build day instead, the line would run past
    its own "as of now" marker. Replaced by the build day outright, nothing
    failed."""
    today = dt.date(2026, 8, 24)
    ahead = (today + dt.timedelta(days=1)).isoformat()
    rows = _day_rows([("2026-08-16", 100), (ahead, 100)])
    pace = internal._pace(rows, 200, 30_000, today=today)
    svg = internal._runway_svg([("2026-08-16", 100), (ahead, 200)], 30_000, pace)
    assert pace["as_of"] == today.isoformat()
    assert f">{ahead}<" in svg and f">{today.isoformat()}<" not in svg


def test_the_cadence_strip_shows_at_most_a_month():
    """Uncapped, a strip renders one cell per day of project history: by the time
    the fleet has run a year the rotation it exists to show is a smear."""
    rows = _day_rows([("2020-01-01", 5), ("2026-08-24", 5)])
    strip = internal._cadence_strip(rows, today=dt.date(2026, 8, 24))
    assert strip.count('<span class="d-') == internal.CADENCE_DAYS
    assert "<span>2026-07-26</span>" in strip     # 30 days ending on the build day


def test_the_panel_states_the_window_every_projected_figure_came_from():
    """An arrival date with no window attached is read as a schedule, so the
    window has to reach the reader with the date: the pace tile states it, and
    the tile carrying the date names it. They sit side by side, which is why the
    eta tile says "the pace window" rather than pointing at a position - at every
    desktop width the pace tile is beside it, not above it."""
    d = internal.collect(1940, 2025)
    if not d["pace"]:
        pytest.skip("no pace in this checkout")
    html = internal.render(d, "en")
    # In these two tiles, not merely somewhere on the page: a window sentence
    # three panels away from the date does not travel with it.
    pace_tile = _tile(html, "Current pace")
    eta_tile = _tile(html, "Complete at that pace")
    assert f'mean of the last {internal.PACE_WINDOW} days' in pace_tile
    assert "not a schedule" in eta_tile
    assert d["pace"]["eta"] in eta_tile
    # The eta tile's only pointer back to that window. Deleted, the date stood
    # with nothing naming what produced it and nothing failed.
    assert "pace window" in eta_tile


def test_the_whole_tab_is_rendered_for_one_day():
    """`_pace` and the panel each used to read the clock, so a build that crossed
    UTC midnight could publish a pace tile ending on one day beside a cadence
    strip ending on the next. `collect` stamps the day once and `render` hands it
    on; a stamp from months ago must reach the panel."""
    d = internal.collect(1940, 2025)
    if not d["daily"]:
        pytest.skip("no usable git history for data/ in this checkout")
    stale = dict(d, today="2027-01-01")
    html = internal.render(stale, "en")
    # Every cadence day is then long past, which only shows if render used the
    # stamp instead of the clock.
    assert "nothing this page counts has landed on any of those days" in " ".join(html.split())
    assert "<span>2027-01-01</span>" in html


def test_the_legend_is_the_four_the_caption_promises():
    """The strip's caption says a cell is coloured "when the day's leading dataset
    is one of the four below". Built from every dataset instead, six entries
    render under a caption saying four - two of them datasets that can never
    colour a cell."""
    rows = _day_rows([("2026-08-24", 50)])
    html = _panel([("2026-08-24", 50)], rows, None, today=dt.date(2026, 8, 24))
    legend = html.split('<div class="int-legend">', 1)[1].split("</div>", 1)[0]
    assert legend.count("<b>") == 4 == len(internal.DS_COLOURED)
    assert "one of the four below" in html
    for key in internal.DS_COLOURED:
        assert internal.DS_LABEL[key] in legend, key
    for key in set(internal.DS_KEYS) - set(internal.DS_COLOURED):
        assert internal.DS_LABEL[key] not in legend, key


def test_every_dataset_colour_reaches_the_built_stylesheet():
    """The Progress tab's colour layer is the whole point of the cadence strip,
    and it lives in a file the build only copies. A renamed token, a dropped
    .d-* rule, or a landing.src.css edit committed without re-running
    tools/build-css.sh leaves `--d` undefined: background falls back to
    transparent, which is exactly the empty cell this page defines as "nothing
    was committed". A month of gathering would read as a dead fleet with every
    other test still green."""
    css = (ROOT / "assets" / "landing.css").read_text("utf-8")
    for key in internal.DS_COLOURED:
        # Twice: the light default and the dark re-step. Dark is not a flip -
        # the same all-pairs separation has to hold on the darker surface.
        assert css.count(f"--ds-{key}:") >= 2, key
        # Each of the three surfaces that paints the class, not just the class
        # somewhere: they are one comma-joined rule, and losing a single arm of
        # it takes out exactly one surface while the others keep it green.
        for selector in (f".int-cad>.d-{key}", f".int-legend .d-{key}",
                         f".int-led.d-{key}"):
            assert selector in css, selector
    # The uncoloured class must stay uncoloured: an uncoloured leader is drawn
    # like a day no file dates to, so it may never take a dataset colour.
    assert ".d-none{" not in css and ".int-cad>.d-none" not in css


# --- browser ----------------------------------------------------------------


@contextlib.contextmanager
def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.mark.slow
def test_every_tab_switches_and_the_framed_map_renders():
    """The coverage tab is deliberately not a second map: it frames the site's
    own map page with ?embed=1&grid=1, which has to hide that page's chrome and
    come up already in coverage mode. If either half regresses the tab shows
    either a duplicated site or a map with no overlay - both silent."""
    from playwright.sync_api import sync_playwright

    out = build("krakow", "en", client_i18n=True)
    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            pg = b.new_page(locale="en-GB",
                            viewport={"width": 1400, "height": 1000})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console",
                  lambda m: errors.append(m.text) if m.type == "error" else None)
            # A tab the visitor picked on the public site, which framing the map
            # must not overwrite: the framed page runs the landing's own tab
            # controller, and that controller persists whichever tab it shows.
            pg.goto(f"{base}/en/index.html", wait_until="load")
            pg.evaluate("localStorage.setItem('temperatury:tab', 'ranking-cities')")

            pg.goto(f"{base}/internal/index.html", wait_until="load")
            # No appearance controls here: with no .topbar they both land in the
            # same fixed corner, and the buried unit toggle writes the PUBLIC
            # site's °C/°F choice.
            assert pg.eval_on_selector_all("#tpref-btn, .tpref-unit",
                                           "els => els.length") == 0

            for key in ("overview", "covmap", "regions", "progress", "gaps"):
                pg.click(f"#tab-{key}")
                assert pg.is_visible(f"#tp-{key}"), key
                assert pg.get_attribute(f"#tab-{key}", "aria-selected") == "true"
                # Exactly one panel at a time.
                shown = pg.eval_on_selector_all(
                    "#internal-tabs .tabpanel:not([hidden])", "els => els.length")
                assert shown == 1, f"{shown} panels visible on {key}"

            # Sorting is what makes a 200-row table usable; assert it reorders.
            pg.click("#tab-regions")
            first = pg.inner_text("table.int-sortable tbody tr:first-child td")
            pg.click("table.int-sortable th[data-col='3']")
            assert pg.inner_text(
                "table.int-sortable tbody tr:first-child td") != first

            pg.click("#tab-covmap")
            frame = pg.frame_locator("#cov-frame")
            frame.locator("#map canvas").wait_for(timeout=40000)
            inner = next(f for f in pg.frames if f != pg.main_frame)
            inner.wait_for_function(
                "window.__mapLayerVisible "
                "&& window.__mapLayerVisible('grid-fill-0') === 'visible'",
                timeout=40000)
            # ?embed=1 drops the framed page's standalone chrome.
            assert inner.evaluate(
                "getComputedStyle(document.querySelector('.topbar')).display") == "none"
            assert inner.evaluate(
                "document.getElementById('grid-toggle').getAttribute('aria-pressed')"
            ) == "true"
            # ... and the framed page left the visitor's own tab choice alone.
            assert pg.evaluate(
                "localStorage.getItem('temperatury:tab')") == "ranking-cities"

            # The colour layer, as the browser computes it: a selector that does
            # not apply and a token that does not resolve both leave the cell
            # transparent - the page's own sign for a day no counted entry dates to.
            pg.click("#tab-progress")
            # No panel to inspect on a checkout with no usable history (shallow
            # clone, no repo, empty data/): that is a documented state, and its
            # sibling tests skip on it rather than fail.
            if not pg.eval_on_selector_all(".int-cad > span", "els => els.length"):
                pytest.skip("no progress panel in this checkout")
            painted = pg.evaluate("""() => {
                const seen = {};
                for (const el of document.querySelectorAll('.int-cad > span'))
                  seen[el.className] = getComputedStyle(el).backgroundColor;
                const led = document.querySelector('.int-led');
                seen.pill = led
                  ? getComputedStyle(led, '::before').backgroundColor : null;
                return seen;
            }""")
            cells = {k: v for k, v in painted.items() if k.startswith("d-")}
            coloured = {k: v for k, v in cells.items() if k != "d-none"}
            assert coloured, painted
            assert painted["pill"], painted      # the pill's dot, not just cells
            for cls, bg in list(coloured.items()) + [("pill", painted["pill"])]:
                assert bg not in ("rgba(0, 0, 0, 0)", "transparent"), (cls, bg)
            # Distinct datasets stay distinct: one token feeding them all would
            # pass every assertion above and lose the strip's whole meaning.
            assert len(set(coloured.values())) > 1, painted
            assert not errors, errors
        finally:
            b.close()
