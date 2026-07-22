"""Client-i18n vs server-render parity.

The core R1-hybrid guarantee: an English shell + a language's dictionary,
applied in the browser, reproduces the fully server-rendered page in that
language. Each test builds both ways and compares visible text.
"""
import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import ROOT, build


def _text(url, selector, switch_to=None):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/*", lambda r: r.abort()
                 if r.request.url.startswith(("http://", "https://"))
                 else r.continue_())
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(200)
        if switch_to:
            pg.evaluate(f"window.__setLang({switch_to!r})")
            pg.wait_for_function(
                f"document.documentElement.lang === {switch_to!r}", timeout=4000)
        t = pg.text_content(selector) or ""
        b.close()
        return " ".join(t.split())


def _norm(url, selector):  # server-rendered reference
    return _text(url, selector)


@pytest.mark.parity
@pytest.mark.slow
@pytest.mark.parametrize("lang", ["pl", "ru", "ar"])  # Latin+diacritics, Cyrillic, RTL
def test_hero_crosslang(lang):
    """Whole hero (.rh-inner): EN shell switched to <lang> == server-rendered
    <lang>. Covers the H1 city name, trend unit, since-line, season line, chips
    across scripts and text direction."""
    sel = ".rh-inner"
    build("krakow", f"en,{lang}", client_i18n=True)
    client = _text((ROOT / "output/en/krakow.html").as_uri(), sel, switch_to=lang)
    build("krakow", lang, client_i18n=False)
    server = _norm((ROOT / f"output/{lang}/krakow.html").as_uri(), sel)
    assert client == server, f"\nclient={client!r}\nserver={server!r}"


def _strip_chart_chrome(text):
    """Remove language-neutral chrome that isn't a translation:
    - the offline 'chart unavailable' fallback (window.__chartErr), shown only
      because charts can't fetch offline; Phase 4's concern. Online it never
      appears.
    - the JS-injected '#' section-permalink anchors, whose count varies by
      render timing.
    So this Phase 3 test measures the report.py page text surfaces."""
    from report import _CHART_ERR
    for msg in _CHART_ERR.values():
        text = text.replace(msg, "")
    return " ".join(t for t in text.split() if t != "#")


@pytest.mark.parity
@pytest.mark.slow
def test_main_crosslang_pl():
    """Whole <main> (minus offline chart chrome): EN shell switched to PL ==
    server-rendered PL. On failure the word-multiset diff pinpoints leftovers.
    """
    build("krakow", "en,pl", client_i18n=True)
    client = _strip_chart_chrome(
        _text((ROOT / "output/en/krakow.html").as_uri(), "main", switch_to="pl"))
    build("krakow", "pl", client_i18n=False)
    server = _strip_chart_chrome(
        _norm((ROOT / "output/pl/krakow.html").as_uri(), "main"))
    if client != server:
        from collections import Counter
        cw, sw = Counter(client.split()), Counter(server.split())
        only_client = list((cw - sw).elements())[:40]
        only_server = list((sw - cw).elements())[:40]
        raise AssertionError(
            f"main text differs.\n  only in client (en leftovers?): {only_client}\n"
            f"  only in server (pl expected):   {only_server}")
