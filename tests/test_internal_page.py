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


def test_total_cache_bytes_is_what_is_on_disk(built):
    import config
    total = sum(p.stat().st_size for p in config.DATA_DIR.iterdir() if p.is_file())
    assert f"{total / 1e9:.2f} GB" in built or f"{total / 1e6:.2f} MB" in built


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


def test_no_figure_is_invented():
    """Every number rendered comes from the roster or the data directory, so a
    build with an empty coverage window has nothing to show - and shows nothing
    rather than a placeholder."""
    d = internal.collect(1800, 1801)      # no cache file can match
    assert d["covered"] == 0
    assert d["progress"] == []
    html = internal.render(d, "en")
    assert "no other honest source" in html
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
            pg.goto(f"{base}/internal/index.html", wait_until="load")

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
            assert not errors, errors
        finally:
            b.close()
