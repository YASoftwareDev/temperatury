"""The coverage grid is unreadable through the dots that sit on top of it.

"Data coverage" paints one cell per 0.25 deg with how many of its cities are
downloaded, but every city dot - analysed AND awaiting-data - stays above it by
design ("narrow the view, never hide places"). At roster scale that is tens of
thousands of dots over the very colours the visitor is trying to read, so
coverage mode carries a companion toggle that drops the dot layers.

Two things have to hold, and both were the reason the control is scoped to
coverage mode: it appears only while the grid is up, and leaving coverage mode
can never strand the map with no dots and no visible way back.
"""
import contextlib
import functools
import http.server
import threading

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import build

SLUG = "krakow"
DOT_LAYERS = ["cities", "refs", "preview"]


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


def _visibility(pg):
    """Layout visibility of each dot layer, None for layers this build has no
    data for (a one-city build has no awaiting-data 'preview' source)."""
    return {lid: pg.evaluate(f"window.__mapLayerVisible({lid!r})")
            for lid in DOT_LAYERS}


def _assert_dots(pg, shown):
    vis = _visibility(pg)
    assert any(v is not None for v in vis.values()), \
        "no dot layer exists at all - the map never finished loading"
    want = "visible" if shown else "none"
    bad = {k: v for k, v in vis.items() if v is not None and v != want}
    assert not bad, f"expected dots {want}, got {bad}"


@pytest.mark.slow
def test_coverage_mode_can_drop_the_city_dots():
    out = build(SLUG, "en", client_i18n=True)
    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            # en-GB, not Playwright's en-US default (see test_units.py).
            pg = b.new_page(locale="en-GB",
                            viewport={"width": 1280, "height": 1000})
            pg.goto(f"{base}/en/index.html", wait_until="load")
            # The map is lazy: MapLibre and the markers only load when the Map
            # tab is first opened, and the controls are inside that panel - so
            # open the tab for real rather than calling __initMap() behind it.
            pg.wait_for_timeout(800)
            pg.click("#tab-map")
            pg.wait_for_function("!!window.__mapLayerVisible", timeout=20000)
            pg.wait_for_function(
                "window.__mapLayerVisible('cities') !== null", timeout=20000)

            # Out of coverage mode the control does not exist for the visitor.
            assert pg.is_hidden("#dots-toggle")
            _assert_dots(pg, shown=True)

            pg.click("#grid-toggle")
            assert not pg.is_hidden("#dots-toggle")
            assert pg.get_attribute("#dots-toggle", "aria-pressed") == "true"
            _assert_dots(pg, shown=True)   # dots still on until asked

            pg.click("#dots-toggle")
            assert pg.get_attribute("#dots-toggle", "aria-pressed") == "false"
            _assert_dots(pg, shown=False)
            # The grid itself is what is left, and it must still be up.
            assert pg.evaluate("window.__mapLayerVisible('grid-fill')") in (
                "visible", None)

            # Leaving coverage mode takes the control away, so it has to restore
            # the dots on the way out - otherwise the map reads as broken.
            pg.click("#grid-toggle")
            assert pg.is_hidden("#dots-toggle")
            assert pg.get_attribute("#dots-toggle", "aria-pressed") == "true"
            _assert_dots(pg, shown=True)

            # Re-entering starts from the same clean state, not the old choice.
            pg.click("#grid-toggle")
            assert pg.get_attribute("#dots-toggle", "aria-pressed") == "true"
            _assert_dots(pg, shown=True)
        finally:
            b.close()
