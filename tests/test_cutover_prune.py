"""Cutover safety: a client-i18n build must prune stale per-language city pages
a server-era (or higher-SEO-tier) cache carried, so the first client deploy is
not bloated with orphaned pre-cutover pages.
"""
import pytest

from tests.conftest import ROOT, build


@pytest.mark.parity
@pytest.mark.slow
def test_client_build_prunes_stale_server_pages():
    # 1. Server-render krakow in four languages (simulates the cached server-era
    #    output/): a per-language page in each.
    build("krakow", "en,pl,de,fr", client_i18n=False)
    for lang in ("en", "pl", "de", "fr"):
        assert (ROOT / f"output/{lang}/krakow.html").exists(), \
            f"server build should have written {lang}/krakow.html"

    # 2. Client-i18n build over the same cache. Krakow's SEO shells are en + pl
    #    (Poland's primary), so de/ and fr/ krakow pages are now stale.
    build("krakow", "en,pl,de,fr", client_i18n=True)

    assert (ROOT / "output/en/krakow.html").exists(), "SEO shell en must remain"
    assert (ROOT / "output/pl/krakow.html").exists(), "SEO shell pl must remain"
    assert not (ROOT / "output/de/krakow.html").exists(), \
        "stale non-SEO page de/krakow.html should have been pruned"
    assert not (ROOT / "output/fr/krakow.html").exists(), \
        "stale non-SEO page fr/krakow.html should have been pruned"
    # Non-city pages (the per-language landing) are keyed by name, not a city
    # slug, so they are never pruned.
    assert (ROOT / "output/de/index.html").exists(), \
        "the landing index page must not be pruned"
