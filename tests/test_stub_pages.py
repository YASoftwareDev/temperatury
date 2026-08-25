"""Tail (non-rich) city pages are stubs: full head + hero stay static for
SEO; topbar/figures/footer arrive client-side from _citybody.js."""
import pytest

import config
import langtier

from tests.conftest import ROOT, build


def _tail_and_rich_slugs():
    """One buildable (cached-data) tail slug and one rich slug."""
    import codec
    locs = list(config.LOCATIONS.values())
    rich = langtier.rich_tier_slugs(locs)

    def cached(loc):
        return codec.cached_path(
            config.DATA_DIR / f"{loc.slug}_1940-2025{codec.SUFFIX}")
    tail = next(l.slug for l in locs if l.slug not in rich and cached(l))
    rich_slug = next(l.slug for l in locs if l.slug in rich and cached(l))
    return tail, rich_slug


@pytest.fixture(scope="module")
def built_pages():
    tail, rich = _tail_and_rich_slugs()
    build(tail, "en", client_i18n=True)
    build(rich, "en", client_i18n=True)
    return {
        "tail": (ROOT / "output" / "en" / f"{tail}.html").read_text("utf-8"),
        "rich": (ROOT / "output" / "en" / f"{rich}.html").read_text("utf-8"),
        "out": ROOT / "output",
    }


def test_stub_keeps_head_and_hero(built_pages):
    html = built_pages["tail"]
    assert "<title>" in html and 'property="og:title"' in html
    assert 'class="region-hero"' in html and 'id="pagehead"' in html


def test_stub_drops_shared_chrome(built_pages):
    html = built_pages["tail"]
    assert "<nav" not in html
    assert 'class="share-row"' not in html
    assert 'class="guide"' not in html
    assert "chart-wrap" not in html          # figures come from _citybody.js
    assert "<footer>" not in html


def test_stub_loads_citybody_before_page_js(built_pages):
    html = built_pages["tail"]
    assert html.index("_citybody.js") < html.index("_page.js")


def test_rich_page_unchanged(built_pages):
    html = built_pages["rich"]
    assert "<nav" in html and "chart-wrap" in html and "<footer>" in html
    assert "_citybody.js" not in html


def test_citybody_asset_exists_and_carries_sentinel(built_pages):
    js = (built_pages["out"] / "en" / "_citybody.js").read_text("utf-8")
    assert "__S__" in js
    assert "chart-wrap" in js and "share-row" in js and "<nav" in js


@pytest.mark.slow
def test_stub_widgets_load_on_demand():
    """Stub pages keep the monthly-range/records widgets, but their payload
    (over half a tail city's chart JSON) rides a separate <slug>_w.json that
    is fetched only when a widget scrolls into view."""
    import contextlib
    import functools
    import http.server
    import threading
    from playwright.sync_api import sync_playwright

    tail, _ = _tail_and_rich_slugs()
    out = build(tail, "en", client_i18n=True)
    assert (out / "charts" / f"{tail}_w.json").is_file(), \
        "the widget sidecar was not written"

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

    with _serve(out) as base, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            pg = b.new_page()
            wreq = []
            pg.on("request",
                  lambda r: wreq.append(r.url) if "_w.json" in r.url else None)
            pg.goto(f"{base}/en/{tail}.html", wait_until="load")
            pg.wait_for_timeout(2000)
            assert not wreq, "_w.json is on the entry path; it must be lazy"
            assert pg.locator(".iwidget").count() >= 1, \
                "widget shells were not injected on the stub page"
            pg.evaluate(f"document.getElementById('rng-{tail}').scrollIntoView()")
            pg.wait_for_function(
                f"(document.getElementById('rng-{tail}-y')||{{}})"
                ".options?.length > 0", timeout=8000)
            assert wreq, "scrolling to the widget never fetched _w.json"
        finally:
            b.close()
