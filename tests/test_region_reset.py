"""A manual pick pins "Selected region" away from geolocation FOREVER by design
(REGION_KEY in localStorage always wins over a fresh position) - right up until
the visitor travels. #region-reset must appear once something has pinned the
tab, and clicking it must drop the pin and let a fresh geolocation fix retake
the tab, rather than leaving a traveller stuck on wherever they clicked once.
"""
import contextlib
import functools
import http.server
import threading

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import build

SLUG = "krakow"
KRAKOW_LAT, KRAKOW_LON = 50.0647, 19.9450


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
def test_region_reset_clears_manual_pick_and_refollows_geolocation():
    out = build(SLUG, "en", client_i18n=True)
    errors, failed = [], []
    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            ctx = b.new_context(
                locale="en-GB", viewport={"width": 1280, "height": 1000},
                permissions=["geolocation"],
                geolocation={"latitude": KRAKOW_LAT, "longitude": KRAKOW_LON},
            )
            pg = ctx.new_page()
            pg.on("console",
                  lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("response",
                  lambda r: failed.append(r.url) if r.status >= 400 else None)

            pg.goto(f"{base}/en/index.html", wait_until="load")
            pg.wait_for_function(
                "(window.__omniData && (window.__omniData.g||[]).length > 0) "
                "&& (window.__ranking && window.__ranking.length > 0)",
                timeout=8000)

            # Nothing has pinned the tab yet: the reset control stays hidden.
            assert pg.is_hidden("#region-reset")

            # Simulate a manual pick (a "did you know" city click, a search
            # result, a map dot) - this is the SAME entry point all three use.
            pg.evaluate("window.__regionShow('other-city.html')")
            assert pg.evaluate("window.__regionManual") is True
            assert not pg.is_hidden("#region-reset")
            assert "other-city.html" in pg.evaluate(
                "document.getElementById('region-frame').src")
            assert pg.evaluate(
                "localStorage.getItem('temperatury:region')") is not None

            pg.click("#region-reset")
            # Geolocation resolves async; the visitor's real position (Krakow)
            # is the only covered city here, so it should retake the frame.
            pg.wait_for_function(
                "document.getElementById('region-frame').src"
                ".indexOf('krakow.html') >= 0",
                timeout=8000)
            assert pg.evaluate("window.__regionManual") is False
            assert pg.evaluate(
                "localStorage.getItem('temperatury:region')") is None
            assert pg.is_hidden("#region-reset")
        finally:
            b.close()
    # other-city.html?embed=1 404-ing is the scenario itself (a fake manual
    # pick); nothing else should have failed to load. The console mirrors that
    # same 404 as a generic "Failed to load resource" line with no URL in it,
    # so cross-check by COUNT against the already-verified failed-response list
    # rather than by matching text.
    assert all("other-city.html" in u for u in failed), f"unexpected 404s: {failed}"
    unexpected = [e for e in errors if "Failed to load resource" not in e]
    assert not unexpected, unexpected[:5]
    assert len(errors) <= len(failed), errors[:5]


@pytest.mark.slow
def test_region_reset_falls_back_to_default_when_geolocation_is_denied():
    """Denied/unavailable geolocation with no remembered city (temperatury:hero
    cache) must not leave the OLD manual pick on screen with the reset button
    now hidden - that looks like the reset silently did nothing. It should fall
    back to the same tier-aware server default a first-ever visit shows."""
    out = build(SLUG, "en", client_i18n=True)
    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            ctx = b.new_context()   # no geolocation permission granted -> denied
            pg = ctx.new_page()
            pg.goto(f"{base}/en/index.html", wait_until="load")
            pg.wait_for_function(
                "(window.__omniData && (window.__omniData.g||[]).length > 0) "
                "&& (window.__ranking && window.__ranking.length > 0)",
                timeout=8000)
            default = pg.evaluate(
                "document.getElementById('region-embed').getAttribute('data-default')")

            pg.evaluate("window.__regionShow('some-other-city.html')")
            assert pg.evaluate("window.__regionManual") is True

            pg.click("#region-reset")
            pg.wait_for_function(
                "document.documentElement && !window.__regionManual", timeout=8000)
            assert pg.evaluate(
                "document.getElementById('region-frame').src"
            ).endswith(default + "?embed=1"), \
                "denied geolocation with no cache should fall back to the default"
            assert pg.is_hidden("#region-reset")
        finally:
            b.close()
