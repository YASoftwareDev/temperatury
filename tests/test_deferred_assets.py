"""The page must survive its own laziness.

Chart.js and charts.js are deferred, and the payloads they need (the per-city chart
JSON, the map markers, the search index) are fetched rather than inlined. That keeps
first paint fast, but it means inline code can run before the API it calls exists,
and a fetch can resolve before the deferred script does. Every failure in that family
is SILENT - a guarded `if (window.X)` skips, a `.then(undefined)` passes the payload
through unexpanded - so each test here asserts an OBSERVABLE effect rather than the
absence of an exception.

Each test names the regression it pins; all of them were live bugs, not hypotheticals.
"""
import contextlib
import functools
import http.server
import json
import threading
import time
import urllib.parse

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import build

SLUG = "krakow"

# A city page rendered BEFORE the topbar list became a sidecar still carries
# <script src="_cities.js">, which no longer exists. Harmless: charts.js is a
# shared, always-fresh asset and fetches _cities.json instead (verified - the
# search still returns cities on such a page), and one full re-render clears it.
# Tests that load a cached sibling page (the landing's region embed) therefore
# tolerate exactly this request. A FRESH page referencing it would still fail
# test_city_search_list_is_lazy_and_still_finds_cities.
RETIRED_ASSET = "_cities.js"


def _assert_only_retired_asset_failed(failed, errors):
    assert all(u.endswith(RETIRED_ASSET) for u in failed), f"unexpected 404s: {failed}"
    unexpected = [e for e in errors
                  if not (failed and "Failed to load resource" in e)]
    assert not unexpected, unexpected[:3]


@contextlib.contextmanager
def _serve(directory):
    """Serve output/ over loopback: file:// fetches are CORS-blocked, and every
    payload here arrives by fetch."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


@contextlib.contextmanager
def _page(errors_out, **kw):
    with sync_playwright() as p:
        b = p.chromium.launch()
        # en-GB, not Playwright's en-US default: a US locale renders Fahrenheit and
        # would change every figure asserted below (see test_units.py).
        pg = b.new_page(locale="en-GB", viewport={"width": 1280, "height": 1000}, **kw)
        pg.on("pageerror", lambda e: errors_out.append(f"pageerror: {e}"))
        pg.on("console",
              lambda m: errors_out.append(f"console: {m.text}") if m.type == "error" else None)
        try:
            yield pg
        finally:
            b.close()


def _settle(pg, ms=2500):
    """Scroll the page so every IntersectionObserver-gated chart renders."""
    pg.wait_for_timeout(800)
    height = pg.evaluate("document.body.scrollHeight")
    for y in range(0, height, 700):
        pg.evaluate(f"window.scrollTo(0,{y})")
        pg.wait_for_timeout(150)
    pg.wait_for_timeout(ms)


def _chart_state(pg):
    return pg.evaluate("""() => {
      const ids = Object.keys(window.__charts || {});
      const bad = ids.filter(i => {
        const L = window.__charts[i].data && window.__charts[i].data.labels;
        return L && L.some(l => String(l).indexOf('_years') >= 0);
      });
      const years = ids.map(i => {
        const L = window.__charts[i].data && window.__charts[i].data.labels;
        return (L && L.length > 3 && /^\\d{4}$/.test(String(L[0]))) ? L.length : 0;
      }).filter(Boolean);
      return {n: ids.length, bad, years,
              widgets: Object.keys(window.__extraCharts || {}).length,
              notices: document.querySelectorAll(
                '.chart-fail,.chart-error,.chart-unavailable').length};
    }""")


@pytest.mark.slow
def test_hoisted_year_axis_is_put_back_before_drawing():
    """A city's charts share one year axis, stored once as _years with the copies
    replaced by a sentinel. If __expandYears does not run, Chart.js draws a category
    axis whose single label is the literal string "_years" - a broken chart that
    throws nothing.
    """
    out = build(SLUG, "en", client_i18n=True)
    payload = json.loads((out / "charts" / f"{SLUG}.json").read_text(encoding="utf-8"))
    assert "_years" in payload, "build should hoist the shared year axis"
    refs = [k for k, v in payload.items()
            if isinstance(v, dict) and (v.get("years") == "_years" or v.get("x") == "_years")]
    assert len(refs) > 5, f"expected many charts to share the axis, got {refs}"

    errors = []
    with _serve(out) as base, _page(errors) as pg:
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="load")
        _settle(pg)
        st = _chart_state(pg)
    assert st["n"] >= 8, f"charts did not render: {st}"
    assert not st["bad"], f"charts drew a literal '_years' axis: {st['bad']}"
    assert st["years"] and all(n > 3 for n in st["years"]), f"year axes look wrong: {st}"
    assert st["notices"] == 0, "a chart reported failure"
    assert not errors, errors[:3]


@pytest.mark.slow
def test_page_survives_charts_js_arriving_late():
    """The regression that broke the degree-C/F switch in production.

    _page.js is render-blocking while charts.js is deferred, so its payload fetch can
    resolve first. Looking the API up "later" is not enough - later still beat the
    script, `window.__expandYears is not a function` threw, and the whole chart chain
    died, leaving the unit toggle with nothing to re-render. Holding charts.js back
    makes that ordering the rule instead of a race.
    """
    out = build(SLUG, "en", client_i18n=True)
    errors = []
    with _serve(out) as base, _page(errors) as pg:
        pg.route("**/charts.js", lambda r: (time.sleep(3), r.continue_())[-1])
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(6500)
        _settle(pg, ms=1500)
        st = _chart_state(pg)
    assert not errors, f"late charts.js broke the page: {errors[:3]}"
    assert not st["bad"], f"charts drew a literal '_years' axis: {st['bad']}"
    assert st["n"] >= 1, f"nothing rendered once charts.js arrived: {st}"


@pytest.mark.slow
def test_inline_hooks_survive_the_deferred_script():
    """Three inline call sites need charts.js, which is deferred; each was guarded, so
    each would have failed silently. Asserted by effect:

    * initRegionEmbed - the landing's region iframe would never be seeded;
    * __unitHooks - built text (the compare stat rows) would stop following a unit
      switch, which is what "I cannot switch between C and F" looked like;
    * renderGlobal - the whole landing render would be skipped.
    """
    out = build(SLUG, "en", client_i18n=True)
    errors, failed = [], []
    with _serve(out) as base, _page(errors) as pg:
        pg.on("response",
              lambda r: failed.append(r.url) if r.status >= 400 else None)
        pg.goto(f"{base}/en/index.html", wait_until="load")
        pg.wait_for_timeout(3000)

        # renderGlobal ran: the ranking payload reached the page.
        assert pg.evaluate("!!window.__gd"), "renderGlobal never received the payload"
        # initRegionEmbed ran: the iframe is seeded, and at a URL that exists.
        src = pg.evaluate("""() => { const f = document.querySelector('#region-embed iframe');
                                     return f ? f.getAttribute('src') : null; }""")
        assert src, "region iframe was never seeded (initRegionEmbed did not run)"
        target = urllib.parse.urljoin(f"{base}/en/index.html", src)
        assert pg.request.get(target).status == 200, f"region iframe points at {src}"
        # __unitHooks: the COMPARE hook specifically. Asserting only that the list
        # is non-empty proves nothing - charts.js pushes five hooks of its own, so
        # deleting the inline registration would leave that green. The compare
        # redraw is identified by the chart id it renders into.
        assert pg.evaluate("""(window.__unitHooks || []).some(
            function (f) { return f.toString().indexOf('c-cmp') >= 0; })"""), \
            "the inline compare-row unit hook is not registered"

        # The unit-switch EFFECT is asserted on a city page: the landing's figures
        # come from the ranking, which holds a single row in a one-city build.
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="load")
        pg.wait_for_timeout(2500)
        before = pg.evaluate("""[...document.querySelectorAll('.tval')]
                                  .slice(0, 5).map(e => e.textContent.trim())""")
        pg.evaluate("""() => document.querySelector(
            '.tpref-unit [data-axis="unit"][data-val="F"]').click()""")
        pg.wait_for_function(
            "document.documentElement.getAttribute('data-unit') === 'F'", timeout=5000)
        pg.wait_for_timeout(1200)
        after = pg.evaluate("""[...document.querySelectorAll('.tval')]
                                 .slice(0, 5).map(e => e.textContent.trim())""")
    assert before and after and before != after, \
        f"unit switch did not rewrite the figures: {before} -> {after}"
    _assert_only_retired_asset_failed(failed, errors)


@pytest.mark.slow
def test_a_failed_map_fetch_does_not_kill_the_session():
    """_map.json is shared by the map and the compare pickers through one cached
    promise. Caching the REJECTION meant a single transient failure permanently
    disabled both, silently and with no retry.
    """
    out = build(SLUG, "en", client_i18n=True)
    assert (out / "charts" / "_base.json").is_file(), \
        "the shared roster base should be written"
    errors = []
    with _serve(out) as base, _page(errors) as pg:
        state = {"fail": True, "n": 0}

        def route(r):
            state["n"] += 1
            r.abort() if state["fail"] else r.continue_()

        pg.route("**/_base.json", route)
        # Aborting a request logs "Failed to load resource"; that IS the scenario.
        expected = "Failed to load resource"
        pg.goto(f"{base}/en/index.html", wait_until="load")
        pg.wait_for_timeout(1500)
        pg.evaluate("window.__initMap && window.__initMap()")
        pg.wait_for_timeout(1500)
        assert state["n"] >= 1, "no attempt was made to fetch the markers"
        assert pg.evaluate("!window.__mapDataP"), \
            "a rejected promise stayed cached - map and compare are now permanently dead"
        # Heal it: a later interaction must retry rather than reuse the failure.
        state["fail"] = False
        attempts = state["n"]
        pg.evaluate("window.__loadMapData()")
        pg.wait_for_timeout(2000)
        assert state["n"] > attempts, "the failure was cached; no retry happened"
        assert pg.evaluate("(window.__mapCities || []).length") >= 1, \
            "markers did not load on the retry"
    unexpected = [e for e in errors if expected not in e]
    assert not unexpected, unexpected[:3]


@pytest.mark.slow
def test_city_search_list_is_lazy_and_still_finds_cities():
    """The topbar city list used to ship as a blocking <script> on every city page.

    At full roster it is ~22 KB gzipped - larger than the page carrying it - and
    only this search box ever reads it. Measured before the move: as a blocking
    mid-body script it cost nothing in first paint (aborting the request left FCP
    unchanged), so what this protects is entry-path bytes. Three things have to
    hold: it is NOT requested on load, typing still returns cities, and a failed
    fetch does not disable the search for the rest of the visit.
    """
    out = build(SLUG, "en", client_i18n=True)
    assert (out / "charts" / "_base.json").is_file(), \
        "the shared roster base is missing"
    html = (out / "en" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert "_cities.js" not in html, "the city list is a blocking <script> again"

    errors, reqs = [], []
    with _serve(out) as base, _page(errors) as pg:
        state = {"fail": True}

        def route(r):
            reqs.append(1)
            r.abort() if state["fail"] else r.continue_()

        pg.route("**/_base.json", route)
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="load")
        pg.wait_for_timeout(1200)
        assert not reqs, "the city list is on the entry path; it should load on first use"

        pg.click("#cp-search")
        pg.fill("#cp-search", "kra")
        pg.wait_for_timeout(700)
        assert reqs, "using the search box did not load the list"
        attempts = len(reqs)

        state["fail"] = False          # a later keystroke must RETRY, not reuse it
        pg.fill("#cp-search", "krak")
        pg.wait_for_selector("#cp-results li", timeout=5000)
        assert len(reqs) > attempts, "the failed fetch was cached; the search stayed dead"
        hits = pg.evaluate("""[...document.querySelectorAll('#cp-results li')]
                                .map(li => li.textContent.toLowerCase())""")
        assert any("krak" in h for h in hits), f"search returned no city: {hits[:5]}"
    # Aborting a request logs "Failed to load resource"; that IS the scenario.
    unexpected = [e for e in errors if "Failed to load resource" not in e]
    assert not unexpected, unexpected[:3]


@pytest.mark.slow
def test_search_index_is_a_sidecar_and_still_searchable():
    """The index moved out of the landing HTML (it was three quarters of it). It must
    still arrive and wire the search, and must not be inlined again.
    """
    out = build(SLUG, "en", client_i18n=True)
    index = (out / "en" / "index.html").read_text(encoding="utf-8")
    assert "window.__omniData=" not in index, "the search index is inline again"
    assert (out / "charts" / "_base.json").is_file(), \
        "the shared roster base was not written"

    errors, fetched, failed = [], [], []
    with _serve(out) as base, _page(errors) as pg:
        pg.on("response", lambda r: fetched.append(r.url) if "_base.json" in r.url else None)
        pg.on("response",
              lambda r: failed.append(r.url) if r.status >= 400 else None)
        pg.goto(f"{base}/en/index.html", wait_until="load")
        pg.wait_for_timeout(3000)
        assert fetched, "the page never fetched the roster base"
        assert pg.evaluate("((window.__omniData || {}).c || []).length") >= 1
        assert pg.evaluate("!!document.getElementById('omni-input').__wired"), \
            "the search was never wired to the loaded index"
        # A wired listener is not a working search: a broken initOmni that binds
        # handlers but matches nothing would pass everything above. Type a real
        # query and require the built city back.
        pg.fill("#omni-input", "krak")
        pg.wait_for_selector("#omni-results li", timeout=5000)
        hits = pg.evaluate("""[...document.querySelectorAll('#omni-results li')]
                                .map(li => li.textContent.toLowerCase())""")
        assert any("krak" in h for h in hits), f"search returned no city: {hits[:5]}"
    _assert_only_retired_asset_failed(failed, errors)


@pytest.mark.slow
def test_compare_deep_link_prefills_before_charts_js_runs():
    """A #cmp= deep link runs cmpReady() INLINE, at document-parse time -
    before deferred charts.js has defined __rosterData. The map-data loader
    must therefore join __ready first; calling __rosterData synchronously
    threw a TypeError that killed the whole compare block (found in review).
    The roster also disambiguates homonyms as "name-(cc)" and one slug even
    carries literal commas, so the hash parser must accept more than
    [a-z0-9-] and resolve the separator by lookup (raw and percent-encoded
    forms both).
    """
    # Slugs with committed data whose shape stresses the parser: a
    # "(cc)"-disambiguated one and (when covered) the comma-bearing one. A
    # build has at most the cities it was built with, so each deep link
    # compares the city to itself - for the comma slug that also puts a
    # comma on BOTH sides of the real separator.
    import codec
    import config

    def _covered(pred):
        # Cities only: compare lists __mapCities, which excludes the
        # region/ocean reference points (vostok,-antarctica is NOT a pick).
        return next((l.slug for l in config.LOCATIONS.values()
                     if pred(l.slug)
                     and getattr(l, "kind", "city") == "city"
                     and codec.cached_path(
                         config.DATA_DIR / f"{l.slug}_1940-2025{codec.SUFFIX}")),
                    None)
    slugs = [s for s in (_covered(lambda s: "(" in s) or SLUG,
                         _covered(lambda s: "," in s)) if s]
    for slug in slugs:
        out = build(slug, "en", client_i18n=True)
        _q = urllib.parse.quote(slug, safe="")
        for frag in (f"#cmp={slug},{slug}", f"#cmp={_q},{_q}"):
            errors = []
            with _serve(out) as base, _page(errors) as pg:
                pg.goto(f"{base}/en/index.html{frag}", wait_until="load")
                pg.wait_for_function(
                    "document.getElementById('cmp-a').value !== ''",
                    timeout=8000)
                assert pg.input_value("#cmp-a") == pg.input_value("#cmp-b") != ""
            # A single-city build's landing 404s assets of unbuilt cities (the
            # default region-hero page); only script errors are the regression.
            real = [e for e in errors if "404" not in e]
            assert not real, (slug, frag, real[:3])
