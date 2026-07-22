"""Chart-label parity: the browser composer reproduces the server's map.

The pre-cutover blocker was that chart axis/legend/trend labels did not follow a
client language switch - window.__ci18n was baked in the shell's SEO language.
The fix ships each label's serialisable recipe in charts/<slug>.json and rebuilds
__ci18n in the browser (charts.js composeLabel) from the active dictionary.

This asserts that browser composition (charts.js composeLabel/pyfmt over the
shipped recipes + a language's own output/i18n/<lang>.js dictionary) equals the
server-rendered page's baked window.__ci18n for that language - across scripts
(Latin/Cyrillic/RTL) and every label of a real city. If they match, a language
switch relabels the charts correctly, because the switch just recomposes this
same map from the same recipes and re-renders.
"""
import contextlib
import functools
import http.server
import json
import threading

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import ROOT, build


@contextlib.contextmanager
def _serve(directory):
    """Serve a directory over loopback HTTP so the page's fetch('../charts/..')
    resolves (file:// fetch is CORS-blocked, which is why the other parity tests
    can't render charts). Yields the base URL."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()

# Latin+diacritics, Cyrillic, RTL, plus two more Latin translations - a spread
# that exercises the "n.s." keyed significance part and the {base:.1f}/{t:.0f}
# format specs across alphabets.
LANGS = ["pl", "ru", "ar", "de", "fr"]


def _eval_client_map(en_page_uri, dict_js, labels):
    """Compose the map the way a switched browser does: load the EN shell (which
    pulls in charts.js -> window.__composeChartI18n), install a language's own
    dictionary, then compose __ci18n from the shipped recipes."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        # Block only the network (Chart.js CDN); local file:// scripts still load,
        # and composition needs no Chart instance.
        pg.route("**/*", lambda r: r.abort()
                 if r.request.url.startswith(("http://", "https://"))
                 else r.continue_())
        pg.goto(en_page_uri, wait_until="domcontentloaded")
        pg.wait_for_function("!!window.__composeChartI18n", timeout=5000)
        pg.evaluate(dict_js)  # sets window.__i18n (+ __cmonths/__lang/__dir)
        m = pg.evaluate(
            "(labels) => { window.__composeChartI18n(labels); return window.__ci18n; }",
            labels)
        b.close()
        return m


def _eval_server_map(server_page_uri):
    """The baked {english: localized} chart map a server-rendered page ships."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/*", lambda r: r.abort()
                 if r.request.url.startswith(("http://", "https://"))
                 else r.continue_())
        pg.goto(server_page_uri, wait_until="domcontentloaded")
        m = pg.evaluate("window.__ci18n || {}")
        b.close()
        return m


@pytest.mark.parity
@pytest.mark.slow
@pytest.mark.parametrize("lang", LANGS)
def test_chart_labels_match_server(lang):
    # Client build: capture the shipped recipes + the EN shell + the language's
    # dictionary BEFORE the server build overwrites output/.
    build("krakow", f"en,{lang}", client_i18n=True)
    labels = json.loads(
        (ROOT / "output/charts/krakow.json").read_text(encoding="utf-8"))["_labels"]
    assert labels, "client-i18n build shipped no chart-label recipes"
    dict_js = (ROOT / f"output/i18n/{lang}.js").read_text(encoding="utf-8")
    en_uri = (ROOT / "output/en/krakow.html").as_uri()
    client = _eval_client_map(en_uri, dict_js, labels)

    # Server reference: the same city rendered directly in <lang>.
    build("krakow", lang, client_i18n=False)
    server = _eval_server_map((ROOT / f"output/{lang}/krakow.html").as_uri())

    # Every label the server baked must be reproduced byte-for-byte by the client
    # composer (extra client keys are fine - the server page only carries the
    # subset of labels its charts use, same as the client).
    mismatches = {k: (server[k], client.get(k)) for k in server
                  if client.get(k) != server[k]}
    assert not mismatches, (
        f"{lang}: {len(mismatches)} chart labels differ (server -> client):\n"
        + "\n".join(f"  {k!r}\n    server={s!r}\n    client={c!r}"
                    for k, (s, c) in list(mismatches.items())[:12]))


@pytest.mark.parity
@pytest.mark.slow
def test_chart_labels_follow_switch_e2e():
    """End-to-end through the real runtime: the shell fetches charts/<slug>.json,
    draw() composes __ci18n from the recipes on load (SEO language), and a
    __setLang switch recomposes it (via i18n-runtime __setLang -> __relocalizeCharts)
    so chart labels follow the switch. Served over HTTP so the fetch resolves;
    Chart.js itself isn't loaded (external CDN blocked), but __ci18n is recomposed
    before any chart is drawn - that map IS what relabels the charts."""
    # Server references (baked maps) for en and pl.
    build("krakow", "en", client_i18n=False)
    server_en = _eval_server_map((ROOT / "output/en/krakow.html").as_uri())
    build("krakow", "pl", client_i18n=False)
    server_pl = _eval_server_map((ROOT / "output/pl/krakow.html").as_uri())

    # Client build, served over HTTP so draw()'s fetch works.
    build("krakow", "en,pl", client_i18n=True)
    with _serve(ROOT / "output") as base, sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        # Allow the loopback origin; block any external (CDN) request.
        pg.route("**/*", lambda r: r.continue_()
                 if "127.0.0.1" in r.request.url else r.abort())
        pg.goto(f"{base}/en/krakow.html", wait_until="domcontentloaded")
        # draw() ran once the fetch resolved -> recipes stored, __ci18n composed.
        pg.wait_for_function(
            "window.__chartLabels && window.__chartLabels.length"
            " && window.__ci18n && Object.keys(window.__ci18n).length",
            timeout=8000)
        on_load = pg.evaluate("window.__ci18n")
        # Switch language in place; charts.js __relocalizeCharts recomposes __ci18n.
        pg.evaluate("window.__setLang('pl')")
        pg.wait_for_function("document.documentElement.lang === 'pl'", timeout=8000)
        pg.wait_for_function(
            "window.__ci18n && window.__ci18n['trend +0.32 °C / decade (p=5e-11)']"
            " && window.__ci18n['trend +0.32 °C / decade (p=5e-11)'].indexOf('dekad') >= 0",
            timeout=8000)
        after_switch = pg.evaluate("window.__ci18n")
        b.close()

    load_bad = {k: (server_en[k], on_load.get(k)) for k in server_en
                if on_load.get(k) != server_en[k]}
    assert not load_bad, f"on load, {len(load_bad)} labels != server en: {list(load_bad)[:8]}"
    sw_bad = {k: (server_pl[k], after_switch.get(k)) for k in server_pl
              if after_switch.get(k) != server_pl[k]}
    assert not sw_bad, f"after switch, {len(sw_bad)} labels != server pl: {list(sw_bad)[:8]}"
