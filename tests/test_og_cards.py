"""Share-card tiering must never name a PNG the build did not write.

Only the most-populous cities get their own card (ogcards.CITY_CARDS); the rest fall
back to their country's, and whatever has neither to the world card. The trap is that
"this city has a country" is NOT the same as "that country has a card": a country only
gets one if it clears the country ranking's minimum-cities threshold, so micro-states
have none. Deriving the fallback from the city's country code alone pointed 30 cities
(Nuuk, Vaduz, San Marino, Luxembourg...) at a 404.
"""
import ogcards


def _payload(n_cities: int, countries: list[str]) -> dict:
    """A ranking of n_cities plus a country list that deliberately omits some of the
    countries the cities belong to - the shape that produced the bug."""
    ranking = []
    for i in range(n_cities):
        cc = "aa" if i % 2 == 0 else "zz"
        ranking.append({"s": f"city-{i:04d}", "n": f"City {i}", "cc": cc,
                        "t": 0.3, "dt": 2.5, "pop": n_cities - i})
    return {"ranking": ranking,
            "countries": [{"cc": cc, "t": 0.3, "rank": 1, "total": 1, "n": 10,
                           "pct": 50} for cc in countries]}


def test_only_the_most_populous_cities_get_their_own_card():
    p = _payload(ogcards.CITY_CARDS + 500, ["aa", "zz"])
    slugs = ogcards.city_card_slugs(p)
    assert len(slugs) == ogcards.CITY_CARDS
    pops = {r["s"]: r["pop"] for r in p["ranking"]}
    chosen_min = min(pops[s] for s in slugs)
    skipped_max = max(pops[s] for s in pops if s not in slugs)
    assert chosen_min > skipped_max, "the cut is not by population"


def test_card_slug_choice_is_deterministic():
    """report.build_site is told this set rather than recomputing it; a different
    tie-break between the two would silently mismatch og:image and the files."""
    p = _payload(ogcards.CITY_CARDS + 50, ["aa"])
    assert ogcards.city_card_slugs(p) == ogcards.city_card_slugs(p)


def test_country_cards_exist_only_for_ranked_countries():
    """The heart of the bug: a city's country code is not evidence of a country card.
    Cities here belong to aa/zz, but only aa is in the country ranking.
    """
    p = _payload(20, ["aa"])
    ccs = ogcards.country_card_ccs(p)
    assert ccs == {"aa"}
    city_ccs = {r["cc"] for r in p["ranking"]}
    assert "zz" in city_ccs and "zz" not in ccs, \
        "a country with cities but no card must not be reported as having one"


def test_a_city_in_an_unranked_country_has_no_country_card():
    """The 404 case, stated as the two facts report.build_site combines: the city is
    not in the personal-card set AND its country has no card, so the only correct
    target left is the world card.

    The ranking must exceed CITY_CARDS: with a short one every city gets its own
    card, the combination never occurs, and this test asserts nothing (it was
    written that way once, guarded by `if tail:`, and passed vacuously).
    """
    p = _payload(ogcards.CITY_CARDS + 50, ["aa"])
    slugs, ccs = ogcards.city_card_slugs(p), ogcards.country_card_ccs(p)
    tail = [r for r in p["ranking"] if r["s"] not in slugs and r["cc"] not in ccs]
    assert tail, "fixture produced no city with neither card - the case is untested"
    assert all(r["cc"] == "zz" for r in tail), \
        "only the unranked country's cities should fall through to the world card"


def test_empty_payload_is_survivable():
    assert ogcards.city_card_slugs({}) == set()
    assert ogcards.country_card_ccs({}) == set()
    assert ogcards.city_card_slugs({"ranking": []}) == set()


def _build_with_no_city_cards(tmp_slug="krakow"):
    """Build one city with the personal-card tier switched off, so the page has to use
    the fallback chain. Its country has no card either (a one-city ranking produces no
    country ranking), which is exactly the micro-state shape."""
    import os
    import subprocess
    import sys

    from tests.conftest import ROOT

    env = {**os.environ, "TEMPERATURY_OFFLINE": "1", "TEMPERATURY_LANGS": "en",
           "TEMPERATURY_CITY_CARDS": "0"}
    env.pop("TEMPERATURY_SERVER_I18N", None)
    subprocess.run([sys.executable, "main.py", "--location", tmp_slug],
                   cwd=ROOT, env=env, check=True, capture_output=True)
    return ROOT / "output", tmp_slug


def test_og_image_never_points_at_a_missing_file():
    """The regression itself, end to end.

    With no personal card and no country card, the page must fall through to the world
    card. Deriving the fallback from the city's country code instead named og/<cc>.png,
    which the build never wrote - a 404 on every social unfurl, visible nowhere on the
    site itself.
    """
    import re

    out, slug = _build_with_no_city_cards()
    html = (out / "en" / f"{slug}.html").read_text(encoding="utf-8")
    m = re.search(r'<meta property="og:image" content="[^"]*?/temperatury/([^"]+)"', html)
    assert m, "no og:image on the page"
    target = m.group(1)
    assert (out / target).is_file(), \
        f"og:image names {target}, which this build did not write"
    # Prove the fallback was actually exercised rather than the personal-card path:
    assert not (out / "og" / "city" / f"{slug}.png").exists(), \
        "TEMPERATURY_CITY_CARDS=0 should have suppressed the personal card"
    assert target == "og/world.png", \
        f"no personal card and no country card should mean the world card, got {target}"
