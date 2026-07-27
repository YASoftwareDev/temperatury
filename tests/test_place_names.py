"""The per-language exonym slices keep each browser reader's own fallback chain.

`_names.<lang>.json` replaced one {slug: {lang: name}} table (309 KB gzipped,
fetched in full before the landing could draw its ranking) with a per-language
slice. The saving is only safe if the slice does not quietly hand a reader a
fallback it never had: charts.js has THREE readers and they disagree on purpose.

* the ranking (`localName` -> `nameOwn`) shows this language's own exonym or the
  city's default name, which is where our "(CC)" disambiguators live;
* the "did you know" facts (`cityName`) and the hero's climate-analog lines
  (`locName`) both go through `nameAny`, which falls back to English first.

Collapsing the slice to `own or english` would silently give the ranking the
English fallback - renaming several hundred rows on every non-English page and
dropping the disambiguators that keep two same-named cities apart.
"""
import re

import pytest

import i18n
import report


def test_slice_splits_own_names_from_the_english_fallback():
    pl = report.place_names_for("pl")
    assert set(pl) == {"l", "f"}
    assert not set(pl["l"]) & set(pl["f"]), "a slug must not be in both maps"
    # Ground truth is report._CITY_NAMES, not data/city_names.json: the module adds
    # the map's reference points (oceans, poles) to the table at import.
    names = report._CITY_NAMES
    for slug, name in pl["f"].items():
        assert "pl" not in names[slug], f"{slug} has a Polish name; belongs in l"
        assert name == names[slug]["en"]
    for slug, name in pl["l"].items():
        assert name == names[slug]["pl"]


def test_a_regional_variant_has_no_names_of_its_own():
    """Why main.py emits slices per BASE code, not per site language.

    charts.js fetches `_names.<lang.split('-')[0]>.json`, so a slice for a
    regional variant would never be fetched - and this asserts it would also be
    pointless: the exonym table is keyed by base code, so zh-TW's own map is
    empty and zh carries the real names.

    Scope: this pins the DATA reason. That main.py's emitted filename set follows
    it (a 4-language en/pl/zh-TW/zh build writes 3 slices, and a stale
    `_names.zh-TW.json` is pruned) was verified against real builds during review.
    """
    variants = [c for c in i18n.LANGUAGES if "-" in c]
    assert variants, "expected at least one regional variant (zh-TW)"
    for code in variants:
        base = code.split("-")[0]
        assert base in i18n.LANGUAGES, f"{code} falls back to {base}, which must exist"
        assert report.place_names_for(code)["l"] == {}, \
            f"{code} has no exonyms of its own; it must not get a slice"
        assert report.place_names_for(base)["l"], f"{base} must carry the real names"


def test_english_slice_needs_no_fallback():
    en = report.place_names_for("en")
    assert en["f"] == {}, "English is the fallback; it cannot fall back to itself"


def test_a_language_with_no_exonyms_gets_english_only():
    # Most of the 132 site languages have no GeoNames exonyms of their own. Their
    # slice must still carry the English names the analog/facts readers expect.
    slice_ = report.place_names_for("ceb")
    assert slice_["l"] == {}
    assert len(slice_["f"]) > 400


def test_disambiguated_cities_are_kept_out_of_the_own_language_map():
    """The precondition for the ranking keeping its "(CC)" suffixes.

    'Aberdeen (HK)' is OUR disambiguator (vs Aberdeen, Scotland), carried on the
    ranking's DEFAULT name; the exonym table's English name is a bare 'Aberdeen'.
    So on a Polish page these slugs must sit only in `f`, which `nameOwn` does not
    read - that is what makes the ranking fall back to the default.

    This asserts the slice, which is all this module can see; that the RENDERED
    row still reads "Suzhou (CN)" is asserted in a browser (see the review's
    Playwright pass), since the default name comes from config.LOCATIONS.
    """
    pl = report.place_names_for("pl")
    disambiguated = [s for s in pl["f"] if re.search(r"-\([a-z]{2}\)$", s)]
    assert disambiguated, "expected at least one '(cc)'-disambiguated city"
    for slug in disambiguated:
        assert slug not in pl["l"]


@pytest.mark.parametrize("reader,expected", [
    # (slug present only in `f`) -> nameOwn misses, nameAny hits.
    ("nameOwn", None),
    ("nameAny", "Aberdeen"),
])
def test_reader_semantics_match_the_two_maps(reader, expected):
    """Mirror of charts.js nameOwn/nameAny against a real slice."""
    pl = report.place_names_for("pl")
    slug = "aberdeen-(hk)"
    assert slug in pl["f"] and slug not in pl["l"]
    got = (pl["l"].get(slug) if reader == "nameOwn"
           else pl["l"].get(slug) or pl["f"].get(slug))
    assert got == expected
