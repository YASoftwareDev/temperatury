"""City URLs must survive two things the naive form gets wrong: a #fragment,
and a language that never pre-rendered the page.

An ALIAS city (a town sharing a covered city's grid cell) is offered as
"<primary>.html#as=<name>" - a URL that already carries a fragment. And under
SEO tiering a city has shells in only a couple of languages, so any link built
as "<slug>.html" 404s in every other language folder. Both were live bugs.
"""
import contextlib
import functools
import http.server
import json
import threading
from urllib.parse import unquote

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import build

SLUG = "krakow"


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
def test_alias_pick_keeps_embed_mode_and_a_clean_alias():
    """?embed=1 has to land in the QUERY, not inside the fragment.

    Appending it to an alias URL produced "...#as=Nowa%20Huta?embed=1": the
    iframe's location.search stayed empty so the embedded page kept its own top
    bar, and the alias parsed as "Nowa Huta?embed=1" - the relabelled heading
    and every keyed caption carried the query string as part of the town name.
    """
    out = build(SLUG, "en", client_i18n=True)
    omni = json.loads((out / "en" / "_omni.json").read_text(encoding="utf-8"))
    alias = next((c for c in omni["c"] if "#as=" in c[1]), None)
    assert alias, "build produced no alias entries, so this test proves nothing"
    alias_name, alias_url = alias[0], alias[1]

    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            pg = b.new_context().new_page()
            pg.goto(f"{base}/en/index.html", wait_until="load")
            pg.wait_for_function(
                "window.__omniData && (window.__omniData.c||[]).length > 0",
                timeout=8000)
            pg.evaluate("(u) => window.__regionShow(u)", alias_url)

            src = pg.evaluate("document.getElementById('region-frame').src")
            parsed = pg.evaluate("(s) => { var u = new URL(s);"
                                 " return {search: u.search, hash: u.hash}; }", src)
            assert "embed=1" in parsed["search"], \
                f"embed mode never engaged; ?embed=1 ended up in the fragment: {src}"
            assert parsed["hash"].startswith("#as="), \
                f"alias fragment lost or reordered: {src}"
            assert "embed=1" not in parsed["hash"], \
                f"the query leaked into the alias name: {src}"
            assert unquote(parsed["hash"][len("#as="):]) == alias_name
        finally:
            b.close()


@pytest.mark.slow
def test_freeform_lookup_snaps_to_a_url_that_exists_in_this_language():
    """The "check any place" lookup snaps a geocoded point to the nearest covered
    city. It used to open "<slug>.html", which only exists in the languages that
    city pre-rendered - so in every other language folder the visitor landed on a
    404. It must use the same tier-aware URL the map dots and search already use.

    Driven through the real text-lookup path with the geocoder stubbed, so the
    assertion covers lookupResolved itself rather than a reimplementation.
    """
    # Krakow's SEO tier is English + its country's language, so it pre-renders
    # en and pl but NOT de - making /de/ a folder where the naive
    # "<slug>.html" link has nothing to point at.
    out = build(SLUG, "en,pl,de", client_i18n=True)
    assert (out / "en" / f"{SLUG}.html").is_file(), "en shell missing"
    # The premise, asserted rather than assumed: without a pruned language this
    # test would pass no matter what lookupResolved does.
    assert not (out / "de" / f"{SLUG}.html").is_file(), \
        "de shell exists, so nothing is pruned and this test proves nothing"

    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            pg = b.new_context().new_page()
            # A place ~1 km from Krakow: inside NEAR_DEG, so it snaps.
            pg.route(
                "**/geocoding-api.open-meteo.com/**",
                lambda r: r.fulfill(status=200, content_type="application/json",
                                    body=json.dumps({"results": [{
                                        "name": "Testowo", "latitude": 50.07,
                                        "longitude": 19.95, "country_code": "PL"}]})))
            pg.goto(f"{base}/de/index.html", wait_until="load")
            pg.wait_for_function(
                "window.__omniData && (window.__omniData.g||[]).length > 0",
                timeout=8000)

            pg.fill("#omni-input", "Testowo")
            pg.wait_for_selector("#omni-results li", timeout=8000)
            pg.keyboard.press("Enter")
            pg.wait_for_function(
                "location.pathname.indexOf('index.html') < 0", timeout=8000)

            landed = pg.evaluate("location.href")
            assert "#as=Testowo" in unquote(landed), f"alias label lost: {landed}"
            status = pg.evaluate(
                "(u) => fetch(u, {method:'GET'}).then(r => r.status)",
                pg.evaluate("location.href.split('#')[0]"))
            assert status == 200, f"freeform lookup landed on a {status}: {landed}"
        finally:
            b.close()
