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
    spans = [internal._STEM_YEARS.search(internal._stem(p.name))
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
    assert internal._progress({}) == []
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
    assert internal._progress(paths) == []


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
    assert internal._progress(paths) == []
    # The refusal is about the undatable file specifically: the two the walk
    # CAN date still chart, so this is not the repo being unusable.
    assert internal._progress(
        {n: paths[n] for n in ("base", "side")})[-1][1] == 2


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

    assert internal._progress(paths) == []
    # ... and the two committed ones on their own still chart, so the refusal is
    # about the undatable file, not about the repo being unusable.
    assert internal._progress({n: paths[n] for n in ("a", "b")})[-1][1] == 2


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
    assert "no other honest source" in " ".join(html.split())
    assert _kpis(html)[1] == "0"


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


def test_a_file_kind_is_read_off_its_own_name():
    """The breakdown has nothing but the file name to go on. The current-year
    pairs are the case that bites: ``_2026_current_extremes`` is an extremes
    file by suffix and a current-year file by shape, and counting it under
    extremes would inflate a dataset the coverage map reports."""
    assert internal._dataset_of("krakow_1940-2025.tpy") == ("krakow", "mean",
                                                            (1940, 2025))
    assert internal._dataset_of("krakow_1940-2025_precip.tpy")[1] == "precip"
    assert internal._dataset_of("krakow_2026_current.tpy") == ("krakow",
                                                               "current", None)
    assert internal._dataset_of("krakow_2026_current_extremes.tpy")[1] == "current"
    # A slug with a dot survives - _stem exists because 24 of them have one.
    assert internal._dataset_of("st.-petersburg_1940-2025.tpy")[0] == "st.-petersburg"
    # Nothing the stems recognise: no slug, so the roster filter drops it.
    assert internal._dataset_of("_global.json") == ("", "other", None)


def test_a_cache_from_another_window_is_not_counted(monkeypatch):
    """A cache left behind by an earlier coverage window is a real file, but it
    is not one of the locations any tile on this page counts - and counting it
    would push the breakdown's mean column past the covered total it is printed
    next to."""
    first = {"a_1940-2025.tpy": 1_754_000_000,
             "a_1950-2020.tpy": 1_754_000_000,
             "b_1940-2025.tpy": 1_754_000_000}
    rows = internal._daily(first, {"a", "b"}, (1940, 2025))
    assert [r["mean"] for r in rows] == [2]
    # Without the window it is three files on that day, which is the bug.
    assert internal._daily(first, {"a", "b"})[0]["mean"] == 3
    # ... and a slug that left the roster is dropped either way.
    assert internal._daily(first, {"a"}, (1940, 2025))[0]["mean"] == 1


def _day_rows(spec):
    """[(day, mean_added)] as _daily returns it, for the pace tests."""
    return [{"day": day, "mean": n, "total": n, "led": "mean" if n else None,
             **{k: 0 for k in internal.DS_KEYS if k != "mean"}}
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
    assert pace["per_day"] == 300                     # 2,700 / 9, not / 3
    assert pace["remaining"] == 9_900
    assert pace["days_left"] == 33                    # 9,900 / 300
    assert pace["eta"] == "2026-09-26"                # 24 Aug + 33 days
    assert pace["as_of"] == today.isoformat()


def test_a_fleet_that_stopped_reads_as_stopped():
    """The window ends on the build day, not on the last day with data, so a
    gatherer that died a fortnight ago cannot keep reporting the pace it had
    while it ran."""
    rows = _day_rows([("2026-08-01", 5_000), ("2026-08-02", 5_000)])
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
    rows = _day_rows([("2026-08-20", 10), ("2026-08-24", 10)])
    assert internal._pace(rows, 30_000, 30_000, today=dt.date(2026, 8, 24)) is None


def test_the_runway_axis_is_the_roster_not_the_series_own_maximum():
    """Scaling to the series' own top makes any rate look like an arrival: the
    line ends in the top right corner whatever it did. The top guide is the
    roster, so 100 locations out of 30,000 draw as 100 out of 30,000."""
    series = [("2026-08-10", 40), ("2026-08-24", 100)]
    svg = internal._runway_svg(series, 30_000, None)
    assert ">30,000<" in svg and ">100 (0.3%)<" in svg
    assert "29,900 locations still to gather" in svg


def test_the_projection_is_drawn_only_when_there_is_a_pace():
    series = [("2026-08-10", 40), ("2026-08-24", 100)]
    assert "ic-proj" not in internal._runway_svg(series, 30_000, None)
    pace = internal._pace(_day_rows([("2026-08-16", 30), ("2026-08-24", 30)]),
                          100, 30_000, today=dt.date(2026, 8, 24))
    assert "ic-proj" in internal._runway_svg(series, 30_000, pace)


def test_the_cadence_strip_ends_on_the_build_day_so_a_stall_is_visible():
    """One cell per UTC day, not one cell per day that committed something: a
    skipped day would close the gap and the strip would show an unbroken
    rotation while the fleet was down."""
    rows = _day_rows([("2026-08-20", 75), ("2026-08-22", 900)])
    strip = internal._cadence_strip(rows, today=dt.date(2026, 8, 24))
    assert strip.count('<span class="d-') == 5        # 20th through 24th
    assert strip.count('class="d-none"') == 3         # 21st, 23rd, 24th
    assert "2026-08-21: nothing committed" in strip
    assert strip.endswith("<span>2026-08-24</span></div>")


def test_the_cadence_strip_never_reaches_before_the_history():
    """Empty cells mean "nothing was committed that day". Days before the first
    commit are days the question does not apply to, and drawing 20 of them would
    read as three weeks of a dead fleet."""
    rows = _day_rows([("2026-08-23", 75)])
    strip = internal._cadence_strip(rows, today=dt.date(2026, 8, 24))
    assert strip.count('<span class="d-') == 2
    assert "<span>2026-08-23</span>" in strip


def test_the_panel_states_the_window_every_projected_figure_came_from():
    """An arrival date with no window attached is read as a schedule. The tile
    that carries it has to say what it was averaged over, in the same tile."""
    d = internal.collect(1940, 2025)
    if not d["pace"]:
        pytest.skip("no pace in this checkout")
    html = internal.render(d, "en")
    assert f'mean of the last {internal.PACE_WINDOW} days' in html
    assert "not a schedule" in html
    assert d["pace"]["eta"] in html


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
            assert not errors, errors
        finally:
            b.close()
