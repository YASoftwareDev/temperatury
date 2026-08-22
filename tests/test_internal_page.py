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
import functools
import http.server
import json
import re
import subprocess
import threading

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


def test_both_cache_figures_are_what_is_on_disk(built):
    """Both, not just the headline. The sub-label has to name WHICH files its
    number covers: mean_bytes is the COVERED mean series, while 11 mean files on
    disk belong to slugs that have left the roster. A label reading as a
    partition of all 15,482 files while the number means something narrower is
    the defect, not the number."""
    import codec
    import config
    files = [p for p in config.DATA_DIR.iterdir() if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    mean = [codec.cached_path(config.DATA_DIR / f"{loc.slug}_1940-2025{codec.SUFFIX}")
            for loc in config.LOCATIONS.values()]
    present = [p for p in mean if p]
    mean_bytes = sum(p.stat().st_size for p in present)
    assert internal._bytes(total) in built
    # The whole sentence, because the wording IS the fix: "Cache on disk / of
    # which X is the mean series" read as a partition of every file in data/,
    # while X counts only the roster's COVERED mean files - 11 mean files on
    # disk belong to slugs that have left the roster.
    assert (f"{len(files):,} files in data/; the {len(present):,} covered mean "
            f"series account for {internal._bytes(mean_bytes)}") in built
    assert "Data directory" in built and "Cache on disk" not in built


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


def test_the_covered_year_span_on_the_real_cache_matches_the_page(built):
    import config
    spans = [internal._STEM_YEARS.search(internal._stem(p.name))
             for p in config.DATA_DIR.iterdir() if p.is_file()]
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
    for langs, want in ((["en"], "../en/"), (["pl", "de"], "../pl/"),
                        ([], "../en/")):
        out = tmp_path / "-".join(langs or ["none"])
        page = internal.build_internal_page(out, 1940, 2025, langs)
        html = page.read_text("utf-8")
        assert f'data-src="{want}index.html?embed=1&amp;grid=1#tab=map"' in html, langs


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
