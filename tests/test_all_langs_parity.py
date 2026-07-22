"""Full 32-language cutover gate.

Before flipping client-i18n on by default, prove the EN shell + each language's
dictionary reproduces the fully server-rendered page in that language - for ALL
supported languages, not just the sampled subset - across the hero and the whole
<main>. This is the parity sweep the plan requires before the default flips.
"""
import pytest
from playwright.sync_api import sync_playwright

import i18n
from tests.conftest import ROOT, build
from tests.test_i18n_parity import _strip_chart_chrome

# Every language except the shell base (en shells are already the reference).
LANGS = [lg for lg in i18n.LANGUAGES if lg != "en"]


def _hero_and_main(uri, switch_to=None):
    """Read the hero (.rh-inner) and whole <main> in one page load, optionally
    after an in-place switch. Charts can't fetch over file://, so their offline
    'unavailable' chrome is stripped from <main> (language-neutral)."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/*", lambda r: r.abort()
                 if r.request.url.startswith(("http://", "https://"))
                 else r.continue_())
        pg.goto(uri, wait_until="domcontentloaded")
        pg.wait_for_timeout(200)
        if switch_to:
            pg.evaluate(f"window.__setLang({switch_to!r})")
            pg.wait_for_function(
                f"document.documentElement.lang === {switch_to!r}", timeout=5000)
            pg.wait_for_timeout(100)
        hero = " ".join((pg.text_content(".rh-inner") or "").split())
        main = _strip_chart_chrome(pg.text_content("main") or "")
        b.close()
        return hero, main


@pytest.mark.parity
@pytest.mark.slow
@pytest.mark.parametrize("lang", LANGS)
def test_page_parity_all_langs(lang):
    build("krakow", f"en,{lang}", client_i18n=True)
    c_hero, c_main = _hero_and_main(
        (ROOT / "output/en/krakow.html").as_uri(), switch_to=lang)
    build("krakow", lang, client_i18n=False)
    s_hero, s_main = _hero_and_main((ROOT / f"output/{lang}/krakow.html").as_uri())

    assert c_hero == s_hero, f"{lang} hero differs:\n client={c_hero!r}\n server={s_hero!r}"
    if c_main != s_main:
        from collections import Counter
        cw, sw = Counter(c_main.split()), Counter(s_main.split())
        raise AssertionError(
            f"{lang} <main> differs.\n  only client: {list((cw - sw).elements())[:30]}\n"
            f"  only server: {list((sw - cw).elements())[:30]}")
