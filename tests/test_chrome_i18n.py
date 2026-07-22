"""Client-i18n for chrome outside <main>, the live-news href, and the topbar
search - the switched-language surfaces Codex flagged (#2/#4/#5).

The whole-<main> parity test does not cover the topbar (map link, city-search
placeholder), the footer, or the news link's href. These assert they follow an
in-place language switch too.
"""
import json
from urllib.parse import quote

import pytest
from playwright.sync_api import sync_playwright

import i18ndict
from tests.conftest import ROOT, build

_CHROME_JS = """() => {
  const q = s => document.querySelector(s);
  const el = q('#cp-search');
  return {
    map: (q('.tb-link') ? q('.tb-link').textContent : '').replace(/\\s+/g, ' ').trim(),
    ph: el ? el.getAttribute('placeholder') : null,
    aria: el ? el.getAttribute('aria-label') : null,
    footer: (q('footer') ? q('footer').textContent : '').replace(/\\s+/g, ' ').trim(),
    news: q('.news-btn') ? q('.news-btn').getAttribute('href') : ''
  };
}"""


def _chrome(uri, switch_to=None):
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
                f"document.documentElement.lang === {switch_to!r}", timeout=4000)
            pg.wait_for_timeout(100)
        data = pg.evaluate(_CHROME_JS)
        b.close()
        return data


@pytest.mark.parity
@pytest.mark.slow
def test_chrome_follows_switch():
    """Topbar map link, city-search placeholder+aria, and footer localise on an
    EN-shell -> PL switch, matching the server-rendered PL page."""
    build("krakow", "en,pl", client_i18n=True)
    client = _chrome((ROOT / "output/en/krakow.html").as_uri(), switch_to="pl")
    build("krakow", "pl", client_i18n=False)
    server = _chrome((ROOT / "output/pl/krakow.html").as_uri())

    pl = i18ndict.merged_table("pl")
    assert client["map"] == server["map"] == pl["map_label"]
    assert client["ph"] == server["ph"] == pl["choose_city"]
    assert client["aria"] == server["aria"] == pl["choose_city"]
    # footer carries a {date} and the source links; whole textContent must match.
    assert client["footer"] == server["footer"]
    assert "Embed widget" not in client["footer"] or pl["widget_label"] in client["footer"]


@pytest.mark.parity
@pytest.mark.slow
def test_news_href_follows_switch():
    """#4: the live-news link's Google News query is rebuilt in the switched
    language (localized phrase + hl), not left in the shell's SEO language."""
    build("krakow", "en,pl", client_i18n=True)
    before = _chrome((ROOT / "output/en/krakow.html").as_uri())
    after = _chrome((ROOT / "output/en/krakow.html").as_uri(), switch_to="pl")

    assert "hl=en" in before["news"]
    assert "hl=pl" in after["news"], f"news href kept SEO language: {after['news']}"
    pl_phrase = i18ndict.merged_table("pl")["extreme_weather"]
    assert quote(pl_phrase) in after["news"], (
        f"news query not in PL: {after['news']} (want {pl_phrase!r})")


@pytest.mark.parity
@pytest.mark.slow
def test_search_lists_all_cities_cross_language():
    """#2: under client-i18n every language's topbar search lists every city; a
    city with no shell in that language links cross-folder to a shell it has."""
    build("tokyo", "en,pl,ja", client_i18n=True)

    def _cities(lang):
        raw = (ROOT / f"output/{lang}/_cities.js").read_text(encoding="utf-8")
        data = json.loads(raw.replace("window.__cpData=", "").rstrip(";\n"))
        return {row[0]: row[1] for row in data["c"]}

    pl = _cities("pl")   # Tokyo has no PL shell
    en = _cities("en")   # Tokyo always has an EN shell
    assert "Tokyo" in pl, "cross-language city missing from PL search"
    assert pl["Tokyo"].startswith("../") and pl["Tokyo"].endswith("/tokyo.html"), \
        f"PL search should link Tokyo to an existing shell, got {pl['Tokyo']!r}"
    assert en["Tokyo"] == "tokyo.html", \
        f"EN search should link Tokyo in-folder, got {en['Tokyo']!r}"


@pytest.mark.parity
@pytest.mark.slow
def test_landing_switcher_navigates():
    """The landing map/dashboard is still rendered per-language and loads no
    i18n runtime, so its language switcher must NAVIGATE (not call the undefined
    window.__setLang)."""
    build("tokyo", "en,pl,ja", client_i18n=True)
    pl_index = (ROOT / "output/pl/index.html").read_text(encoding="utf-8")
    import re
    m = re.search(r'class="lang-select"[^>]*onchange="([^"]*)"', pl_index)
    assert m, "landing has no language switcher"
    assert "__setLang" not in m.group(1), \
        f"landing switcher wrongly switches in place: {m.group(1)!r}"
    assert '<option value="../en/index.html"' in pl_index, \
        "landing switcher should navigate to sibling index pages"


@pytest.mark.parity
@pytest.mark.slow
def test_landing_omni_no_cross_language_404():
    """The landing omni search must link a city/alias with no shell in this
    language to one it has (tier-aware), not a 404 same-folder URL."""
    build("tokyo", "en,pl,ja", client_i18n=True)
    pl_index = (ROOT / "output/pl/index.html").read_text(encoding="utf-8")
    ja_index = (ROOT / "output/ja/index.html").read_text(encoding="utf-8")
    # PL is not a Tokyo shell: no omni row may point at a same-folder tokyo.html.
    assert '"tokyo.html"' not in pl_index, \
        "landing omni links a same-folder page that does not exist in PL (404)"
    assert '"../en/tokyo.html' in pl_index or '"../ja/tokyo.html' in pl_index, \
        "landing omni should link Tokyo cross-folder to an existing shell"
    # JA is a Tokyo shell: it links same-folder.
    assert '"tokyo.html"' in ja_index, "JA landing omni should link Tokyo in-folder"
