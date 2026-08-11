"""°C / °F parity: the same page, read in either unit, says the same thing.

The site converts entirely in the browser - the server always renders Celsius
(so a no-JS reader and every crawler still get a real number) and charts.js
re-expresses it. Three things have to hold for that to be honest:

* the three conversion CLASSES are applied correctly - an absolute temperature
  takes the 32 offset, a difference or a rate does not, and days/mm/years are
  never touched (the classic Fahrenheit bug);
* label composition agrees between the server (plots.compose_label, which bakes
  the landing's °F map) and the browser (charts.js composeLabel, which rebuilds
  a city page's map from the shipped recipes);
* a switch is LOSSLESS - flipping to °F and back reproduces the original page
  text exactly, because everything re-renders from the stored Celsius source
  rather than from its own displayed text.
"""
import contextlib
import functools
import http.server
import json
import re
import threading

import pytest
from playwright.sync_api import sync_playwright

import chartpack
import i18n
from plots import compose_label, to_f
from tests.conftest import ROOT, build

SLUG = "krakow"


@contextlib.contextmanager
def _serve(directory):
    """Serve output/ over loopback so the page's fetch('../charts/..') resolves
    (file:// fetch is CORS-blocked), which is what makes the charts real here."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


# --- the conversion classes ------------------------------------------------
def test_conversion_classes():
    assert to_f(0, "abs") == 32
    assert to_f(100, "abs") == 212
    assert to_f(0, "delta") == 0          # no offset on a difference
    assert to_f(0.3, "delta") == pytest.approx(0.54)
    assert to_f(1, "ddays") == pytest.approx(1.8)


@pytest.mark.parametrize("recipe, c, f", [
    # a warming RATE: scaled, never offset
    ([["k", "trend", {}], ["t", " "], ["n", 0.3012, "delta", 2, 1], ["t", " "],
      ["k", "per_decade_c", {}]],
     "trend +0.30 °C / decade", "trend +0.54 °F / decade"),
    # an absolute threshold inside a translated template
    ([["k", "threshold_hot", {"t": 18}, {"t": "abs"}]],
     "hot days (>18 °C)", "hot days (>64 °F)"),
    ([["k", "threshold_freeze", {"t": 0}, {"t": "abs"}]],
     "freezing days (<0 °C)", "freezing days (<32 °F)"),
    # an absolute baseline mean
    ([["k", "vs_baseline", {"lo": 1961, "hi": 1990, "base": 7.8},
       {"base": "abs"}]],
     "vs. 1961-1990 mean (7.8 °C)", "vs. 1961-1990 mean (46.0 °F)"),
    # degree-days: scaled, and the composite unit follows
    ([["k", "dd_ylabel", {}]],
     "Degree-days per year (°C·days)", "Degree-days per year (°F·days)"),
    # a day-to-day JUMP is a difference, so 6 -> 11, not 43
    ([["t", "≥"], ["n", 6.0, "delta", 0, 0], ["t", " "], ["u"], ["t", " "],
      ["k", "volatility_jump", {}]],
     "≥6 °C day-to-day jump", "≥11 °F day-to-day jump"),
    # a days-per-decade rate is NOT a temperature and must not move
    ([["t", "+3.4 "], ["k", "per_decade_days", {}]],
     "+3.4 days / decade", "+3.4 days / decade"),
])
def test_compose_label_units(recipe, c, f):
    tr = i18n.get("en")
    assert compose_label(recipe, tr) == c
    assert compose_label(recipe, tr, "F") == f


# --- the browser -----------------------------------------------------------
# US locale -> Fahrenheit by default; en-GB -> Celsius. Both go through the same
# autoUnit() the head bootstrap runs before first paint.
_F_LOCALE, _C_LOCALE = "en-US", "en-GB"


def _texts(pg):
    """The figures this test watches, as the reader sees them."""
    return pg.evaluate("""() => ({
      unit: document.documentElement.getAttribute('data-unit'),
      trend: document.querySelector('.rh-figure .tval').textContent,
      rate_unit: document.querySelector('.rh-figure .rh-unit').textContent,
      mean: document.querySelector('.rh-chip .tval').textContent,
      mean_unit: document.querySelector('.rh-chip .tunit').textContent,
      since: (document.querySelector('.rh-meta') || {}).textContent || '',
    })""")


def _chart_first(pg, chart):
    """The first non-null raw value a chart actually plotted.

    City-page charts render lazily (an IntersectionObserver, so first paint is
    not spent on canvases nobody scrolls to), so bring the canvas into view and
    wait for its instance before reading it."""
    cid = f"c-{SLUG}-{chart}"
    pg.eval_on_selector(f"#{cid}", "el => el.scrollIntoView()")
    pg.wait_for_function("(cid) => !!(window.__charts || {})[cid]", arg=cid,
                         timeout=20000)
    return pg.evaluate(
        """(cid) => {
             var d = window.__charts[cid].data.datasets[0].data;
             for (var i = 0; i < d.length; i++) if (d[i] != null) return d[i];
             return null;
           }""", cid)


def _src(pg, sel):
    """The Celsius value a rendered figure was derived from."""
    return float(pg.eval_on_selector(sel, "el => el.getAttribute('data-c')"))


def _payload_first(chart, key="raw"):
    # Arrays ship packed (chartpack); unpack exactly like the browser does.
    p = chartpack.unpack_tree(json.loads(
        (ROOT / f"output/charts/{SLUG}.json").read_text("utf-8")))[chart]
    vals = p[key]["data"] if isinstance(p.get(key), dict) else p[key]
    return next(v for v in vals if v is not None)


@pytest.mark.parity
@pytest.mark.slow
def test_fahrenheit_page_and_charts():
    build(SLUG, "en", client_i18n=True)
    with _serve(ROOT / "output") as base, sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(locale=_F_LOCALE)
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="load")
        pg.wait_for_function(
            f"!!(window.__charts && window.__charts['c-{SLUG}-yearly-trend'])",
            timeout=20000)
        t = _texts(pg)

        # A US visitor lands on °F with no interaction at all.
        assert t["unit"] == "F"
        assert "°F" in t["rate_unit"] and "°C" not in t["rate_unit"]
        assert t["mean_unit"] == "°F"

        # The figures are the Celsius source converted by their own class: the
        # annual mean is an absolute temperature, the trend a rate.
        srv = chartpack.unpack_tree(json.loads(
            (ROOT / f"output/charts/{SLUG}.json").read_text("utf-8")))
        mean_c = _src(pg, ".rh-chip .tval")
        rate_c = _src(pg, ".rh-figure .tval")
        assert float(t["mean"]) == pytest.approx(to_f(mean_c, "abs"), abs=0.051)
        assert float(t["trend"]) == pytest.approx(to_f(rate_c, "delta"),
                                                  abs=0.0051)
        assert srv["yearly-trend"]["tk"] == "abs"

        # Chart DATA converts with the chart's own class, and the axis title
        # follows. Annual mean = absolute; the anomaly bars = a difference.
        assert _chart_first(pg, "yearly-trend") == pytest.approx(
            to_f(_payload_first("yearly-trend"), "abs"), abs=0.011)
        assert _chart_first(pg, "anomalies") == pytest.approx(
            to_f(_payload_first("anomalies", "values"), "delta"), abs=0.011)
        # Threshold days are counted in DAYS: no tk, so the plotted numbers must
        # be bit-identical to the payload even on a °F page.
        assert srv["threshold-days"].get("tk") is None
        days_src = next(v for v in srv["threshold-days"]["series"][0]["raw"]
                        if v is not None)
        assert _chart_first(pg, "threshold-days") == days_src

        labels = pg.evaluate("window.__ci18n")
        joined = "\n".join(labels.values())
        assert "°C" not in joined, "a °F page still shows °C in a chart label"
        assert "hot days (>64 °F)" in joined
        b.close()


@pytest.mark.parity
@pytest.mark.slow
def test_unit_toggle_round_trip():
    """Switching °C -> °F -> °C restores the page byte for byte.

    This is the property that catches conversion done in place: anything that
    reads its own rendered text instead of the stored Celsius source drifts a
    little on every flip, and two flips is enough to see it."""
    build(SLUG, "en", client_i18n=True)
    with _serve(ROOT / "output") as base, sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(locale=_C_LOCALE)
        pg.goto(f"{base}/en/{SLUG}.html", wait_until="load")
        pg.wait_for_function(
            f"!!(window.__charts && window.__charts['c-{SLUG}-yearly-trend'])",
            timeout=20000)

        before = _texts(pg)
        assert before["unit"] == "C"
        chart_c = _chart_first(pg, "yearly-trend")

        def pick(unit):
            pg.evaluate(
                """(u) => document.querySelector(
                     '.tpref-unit [data-axis="unit"][data-val=' + JSON.stringify(u) + ']'
                   ).click()""", unit)
            pg.wait_for_function(
                "(u) => document.documentElement.getAttribute('data-unit') === u",
                arg=unit, timeout=5000)

        # Expected values come from the stored Celsius SOURCE, not from the
        # rounded °C on screen - rounding twice is exactly the drift this test
        # is here to catch.
        mean_c = _src(pg, ".rh-chip .tval")
        rate_c = _src(pg, ".rh-figure .tval")

        pick("F")
        hot = _texts(pg)
        assert hot["unit"] == "F"
        assert float(hot["mean"]) == pytest.approx(to_f(mean_c, "abs"), abs=0.051)
        assert float(hot["trend"]) == pytest.approx(to_f(rate_c, "delta"),
                                                    abs=0.0051)
        assert "°F" in hot["rate_unit"] and "°C" not in hot["rate_unit"]
        assert _chart_first(pg, "yearly-trend") == pytest.approx(
            to_f(chart_c, "abs"), abs=0.011)

        pick("C")
        assert _texts(pg) == before
        assert _chart_first(pg, "yearly-trend") == pytest.approx(chart_c,
                                                                 abs=1e-9)
        b.close()


@pytest.mark.parity
@pytest.mark.slow
def test_landing_bakes_a_fahrenheit_label_map():
    """The landing is server-composed per language and ships no client
    dictionary, so its °F chart labels have to be baked. Assert the baked map
    exists, keys off the Celsius label, and carries no stray °C."""
    build(SLUG, "en", client_i18n=True)
    html = (ROOT / "output/en/index.html").read_text("utf-8")
    m = re.search(r"window\.__ci18nF = (\{.*?\});\n", html, re.S)
    assert m, "no __ci18nF baked into the landing"
    fmap = json.loads(m.group(1))
    cmap = json.loads(
        re.search(r"window\.__ci18n = (\{.*?\});\n", html, re.S).group(1))
    assert set(fmap) == set(cmap), "the °F map must key off the same labels"
    assert fmap, "empty °F label map"
    for k, v in fmap.items():
        if "°C" in cmap[k]:
            assert "°F" in v and "°C" not in v, f"{k!r} kept °C in the °F map"


@pytest.mark.parity
@pytest.mark.slow
def test_automatic_unit_uses_only_the_primary_locale_region():
    """A Polish page opened in Fahrenheit. Reported from the live site.

    The rule scanned ALL of navigator.languages and took the first tag carrying a
    region, so a Polish visitor whose list is ["pl", "en-US", "en"] was read as
    American: a bare "pl" carries no region, so the loop fell through to a
    SECONDARY entry. Only the PRIMARY locale counts now, and a region-less tag is
    not evidence of a country.

    The VISITOR'S REGION decides on every language - an American reading the
    Polish page does get Fahrenheit. The page's language is deliberately NOT
    consulted; unit is a property of the reader, not of the content.

    Waits for `load`, not `domcontentloaded`: the deferred appearance.js carried a
    SECOND copy of this rule and silently overwrote the head bootstrap's answer,
    which is why fixing the bootstrap alone changed nothing on screen.
    """
    build(SLUG, "en,pl", client_i18n=True)
    pl = (ROOT / f"output/pl/{SLUG}.html").as_uri()
    en = (ROOT / f"output/en/{SLUG}.html").as_uri()

    def unit(uri, langs):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(locale=langs[0])
            pg.add_init_script(
                "Object.defineProperty(navigator,'languages',{get:()=>%r});" % (langs,))
            pg.goto(uri, wait_until="load")
            pg.wait_for_timeout(600)          # let the deferred appearance.js apply
            got = pg.evaluate("document.documentElement.getAttribute('data-unit')")
            b.close()
            return got

    # THE REPORT: a Polish reader whose browser lists en-US after a region-less pl.
    assert unit(pl, ["pl", "en-US", "en"]) == "C", "the Polish page opened in F"
    assert unit(en, ["pl", "en-US", "en"]) == "C", \
        "a secondary en-US was mistaken for the visitor's region"
    # A region-less primary is no evidence either way -> the metric default.
    assert unit(pl, ["pl"]) == "C"
    assert unit(en, ["en"]) == "C", "a region-less 'en' must not imply the US"

    # The visitor's region wins REGARDLESS of the page language: same reader,
    # both languages, Fahrenheit either way.
    assert unit(en, ["en-US"]) == "F", "an American reader lost Fahrenheit"
    assert unit(pl, ["en-US"]) == "F", \
        "the visitor's region must decide on the Polish page too"
    assert unit(pl, ["es-PR"]) == "F", "a Fahrenheit territory lost Fahrenheit"
    # ...and a metric region stays metric on the English page.
    assert unit(en, ["en-GB"]) == "C", "a British reader got Fahrenheit"
    assert unit(en, ["pl-PL"]) == "C"
