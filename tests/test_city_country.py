"""A city's country must come from the city, never from its timezone.

Timezones are not a country key. GeoNames files 41 Vietnamese cities under
``Asia/Bangkok``, so for as long as ``country_code`` derived the country from
the timezone the site showed Haiphong, Huế, Thanh Hóa and 38 more with a Thai
flag and counted their warming into Thailand's national ranking.

The roster TSV therefore carries a GeoNames ``cc`` column, and these tests pin
that it is present, well-formed, and actually preferred over the timezone.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
import countries


def _cities():
    return [l for l in config.LOCATIONS.values()
            if getattr(l, "kind", "city") == "city"]


def test_vietnamese_cities_filed_under_bangkok_are_vietnamese():
    """The reported defect, pinned by name."""
    for slug in ("thanh-hoa", "mong-cai", "ba-vi", "vinh-yen", "haiphong", "hue"):
        loc = config.LOCATIONS[slug]
        assert loc.timezone == "Asia/Bangkok", (
            f"{slug} no longer carries the timezone that caused the bug; the "
            "test is no longer exercising it")
        assert countries.country_code(loc) == "vn"


def test_every_city_has_a_country():
    """A city with no country gets no flag and drops out of the country
    ranking."""
    missing = [l.name for l in _cities() if countries.country_code(l) is None]
    assert not missing, f"{len(missing)} cities have no country: {missing[:10]}"


def test_browser_can_guess_a_country_for_every_city_timezone():
    """``tz_country_map`` is shipped to the browser so a visitor's country can be
    guessed from ``Intl…timeZone`` without a geolocation prompt. It was generated
    for the roster as it stood and never regrown with it, so a visitor in
    Detroit, Halifax, Irkutsk or Samarkand - 52 zones' worth - was guessed as
    nowhere and fell through to the default region."""
    tzcc = countries.tz_country_map()
    missing = sorted({l.timezone for l in _cities() if l.timezone not in tzcc})
    assert not missing, f"{len(missing)} city timezones unguessable: {missing[:10]}"


def test_roster_countries_are_two_letter_codes():
    rows = [r.split("\t") for r in
            (ROOT / "cities750k.tsv").read_text(encoding="utf-8").splitlines()
            if r.strip()]
    assert rows, "roster is empty"
    for r in rows:
        assert len(r) == 6, f"expected 6 columns, got {len(r)}: {r}"
        assert len(r[5]) == 2 and r[5].islower(), f"bad country code in {r}"


def test_alias_generation_accepts_the_rows_the_generator_now_emits():
    """`main()` builds the roster rows and hands the same list to
    `write_aliases`, which unpacked them positionally - so widening the row by a
    country column crashed regeneration after cities750k.tsv had been written
    and before city_aliases.tsv was."""
    import pathlib
    import tools.gen_cities as gen

    written = []
    orig = pathlib.Path.write_text
    pathlib.Path.write_text = lambda self, *a, **kw: written.append(self.name)
    try:
        gen.write_aliases([], [("Asia", "X", "1.0", "2.0", "UTC", "xx")], set())
    finally:
        pathlib.Path.write_text = orig
    assert written == ["city_aliases.tsv"]


def test_country_is_not_re_derived_from_the_timezone():
    """The fallback must stay a fallback: a roster city keeps its own country
    even when its timezone maps somewhere else entirely."""
    loc = config.LOCATIONS["thanh-hoa"]
    assert countries._TZ_CC[loc.timezone] == "th"   # the wrong answer, still there
    assert countries.country_code(loc) == "vn"      # and still not used
