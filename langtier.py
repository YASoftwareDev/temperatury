"""Language tiering: which languages each city's page is built in.

The full product of every city x all 32 languages does not fit the ~1 GB
GitHub Pages artifact cap once the data backfill approaches the 5,531-city
roster (measured 2026-07-19: ~6.6 KB gz per page -> ~1.35 GB projected).
Instead of capping cities or dropping languages site-wide:

* the **most-populous ~1,500 cities** (plus every non-city reference point and
  the landing pages) keep **all** site languages - these are the pages people
  actually open in every language;
* the long tail is built in **English plus the languages spoken in the city's
  country** - a Polish page for every Polish village, a Tamil page for Tamil
  Nadu towns, but no Yoruba page for a Siberian outpost nobody will request.

Tier assignment ranks the FULL city roster (config.LOCATIONS) by GeoNames
population, so a city's tier never changes as the data cache grows - only new
pages appear, none silently lose languages between deploys.
"""
from __future__ import annotations

import json
from pathlib import Path

import countries
from config import Location

# How many cities (by population, over the full roster) get every language.
FULL_TIER = 1500

# ISO-2 country -> site languages spoken there (besides English, which every
# page keeps). Only codes from i18n.LANGUAGES appear here. A country absent
# from the map builds its tail cities in English only.
COUNTRY_LANGS: dict[str, tuple[str, ...]] = {
    # Europe
    "pl": ("pl",), "ua": ("uk",), "de": ("de",), "at": ("de",), "li": ("de",),
    "ch": ("de", "fr", "it"), "lu": ("fr", "de"), "be": ("fr", "nl", "de"),
    "fr": ("fr",), "mc": ("fr",), "nl": ("nl",), "it": ("it",), "sm": ("it",),
    "va": ("it",), "es": ("es",), "pt": ("pt",), "tr": ("tr",), "cy": ("tr",),
    "ru": ("ru",), "by": ("ru",),
    # Americas
    "mx": ("es",), "ar": ("es",), "co": ("es",), "cl": ("es",), "pe": ("es",),
    "ve": ("es",), "ec": ("es",), "gt": ("es",), "cu": ("es",), "bo": ("es",),
    "do": ("es",), "hn": ("es",), "py": ("es",), "sv": ("es",), "ni": ("es",),
    "cr": ("es",), "pa": ("es",), "uy": ("es",), "pr": ("es",), "us": ("es",),
    "br": ("pt",), "ca": ("fr",), "ht": ("fr",), "sr": ("nl",), "aw": ("nl",),
    "cw": ("nl",), "sx": ("nl",), "gf": ("fr",), "gp": ("fr",), "mq": ("fr",),
    # Middle East / North Africa
    "sa": ("ar",), "eg": ("ar",), "ly": ("ar",), "sd": ("ar",), "ye": ("ar",),
    "sy": ("ar",), "iq": ("ar",), "jo": ("ar",), "lb": ("ar",), "ps": ("ar",),
    "kw": ("ar",), "qa": ("ar",), "bh": ("ar",), "ae": ("ar",), "om": ("ar",),
    "mr": ("ar",), "so": ("ar",), "eh": ("ar",),
    "dz": ("ar", "fr"), "ma": ("ar", "fr"), "tn": ("ar", "fr"),
    "ir": ("fa",), "af": ("fa",),
    # Sub-Saharan Africa
    "sn": ("fr",), "ci": ("fr",), "ml": ("fr",), "bf": ("fr",), "ne": ("fr", "ha"),
    "tg": ("fr",), "ga": ("fr",), "cg": ("fr",), "cf": ("fr",), "mg": ("fr",),
    "gn": ("fr",), "km": ("fr", "ar"), "dj": ("fr", "ar"), "td": ("fr", "ar", "ha"),
    "cm": ("fr", "ha"), "bj": ("fr", "yo"), "rw": ("fr", "sw"), "bi": ("fr", "sw"),
    "cd": ("fr", "sw"), "ke": ("sw",), "tz": ("sw",), "ug": ("sw",),
    "ng": ("ha", "yo"), "gh": ("ha",), "et": ("am",),
    "ao": ("pt",), "mz": ("pt",), "gw": ("pt",), "cv": ("pt",), "st": ("pt",),
    "gq": ("es", "fr", "pt"), "re": ("fr",), "sc": ("fr",), "mu": ("fr",),
    # Asia
    "cn": ("zh",), "tw": ("zh",), "hk": ("zh",), "mo": ("zh", "pt"),
    "sg": ("zh", "ta", "id"), "jp": ("ja",), "kr": ("ko",), "kp": ("ko",),
    "vn": ("vi",), "th": ("th",), "mm": ("my",), "ph": ("tl",),
    "id": ("id",), "my": ("id", "ta", "zh"), "bn": ("id",), "tl": ("pt", "id"),
    "in": ("hi", "bn", "ta", "te", "mr", "pa", "ur"),
    "pk": ("ur", "pa"), "bd": ("bn",), "lk": ("ta",),
    "kz": ("ru",), "kg": ("ru",), "tj": ("ru", "fa"),
    # Oceania
    "fj": ("hi",), "nc": ("fr",), "pf": ("fr",), "vu": ("fr",),
}

# GeoNames per-city population (same file the ranking uses). Missing -> 0.
try:
    _POP: dict = json.loads(
        (Path(__file__).resolve().parent / "data" / "city_pop.json")
        .read_text(encoding="utf-8"))
except (OSError, ValueError):
    _POP = {}


def full_tier_slugs(locations: list[Location], top: int = FULL_TIER) -> set[str]:
    """The slugs that keep every language: the ``top`` most-populous cities of
    the FULL roster (stable across deploys as the data cache grows)."""
    cities = [l for l in locations if getattr(l, "kind", "city") == "city"]
    cities.sort(key=lambda l: _POP.get(l.slug) or 0, reverse=True)
    return {l.slug for l in cities[:top]}


def languages_for(loc: Location, full: bool, site_langs: list[str]) -> list[str]:
    """The languages this location's page is built in, in site order (so the
    hreflang x-default stays languages[0], same as before tiering)."""
    if full or getattr(loc, "kind", "city") != "city":
        return list(site_langs)
    cc = countries.country_code(loc) or ""
    keep = {"en", *COUNTRY_LANGS.get(cc, ())}
    picked = [lg for lg in site_langs if lg in keep]
    # A restricted TEMPERATURY_LANGS build may exclude every kept language;
    # build the first site language rather than no page at all.
    return picked or [site_langs[0]]


# --- client-i18n SEO tiering ------------------------------------------------
# Under client-side i18n (R1-hybrid) the browser localises one shell per city
# into any language, so storage no longer scales with language count. Only a
# few languages per city are PRE-RENDERED as static shells - for crawlers and
# the no-JS baseline. SEO_PRERENDER is how many: English plus the city's
# country primary language (the two that matter most for local search). Raise
# it to widen crawlable-language coverage at a proportional storage cost.
SEO_PRERENDER = 2

# --- size tiering (roster >> 1 GB Pages cap) ---------------------------------
# Measured 2026-08-10 on a clean build: 24 MB fixed + ~161 KB per rendered city
# (49 KB chart JSON, 31 KB English shell, 73 KB other-language shells, 8 KB OG
# card). At the >=10k-population roster (32,671 primaries) that projects to
# ~5.3 GB - five times the 1 GB cap. Capping the roster or dropping languages
# site-wide are both worse than spending the bytes where they are actually
# read, so cities are tiered by population:
#
#   * the top RICH_TIER cities pre-render every SEO language - these are what
#     people open and what gets shared;
#   * every other city pre-renders ONE shell. Nothing is lost to a visitor: the
#     language switcher, search and the map all still work client-side.
#
# This covers the language-shell share of the per-city cost ONLY. Slimming that
# shell and shipping a lite chart payload for the tail are still to do, and
# both are required before the roster can actually grow - see
# ~/projects/tasks/doing/temperatury-10k-roster.md. Do not read this tier as
# "the page size problem is solved".
#
# Ranking is by GeoNames population over the FULL roster, so a city's tier never
# changes as the data cache grows.
RICH_TIER = 2000


def rich_tier_slugs(locations: list[Location], top: int = RICH_TIER) -> set[str]:
    """Slugs that get the full-size treatment (see RICH_TIER)."""
    cities = [l for l in locations if getattr(l, "kind", "city") == "city"]
    cities.sort(key=lambda l: _POP.get(l.slug) or 0, reverse=True)
    return {l.slug for l in cities[:top]}


def seo_languages_for(loc: Location, site_langs: list[str],
                      rich: bool = True) -> list[str]:
    """Which languages to PRE-RENDER (static shell) for this location: English
    first, then the country's languages, capped at SEO_PRERENDER. Every OTHER
    site language is reachable in the browser via the language switcher, at no
    per-city storage cost.

    ``rich=False`` (a size-tier tail city) prerenders only the FIRST of those.
    English stays first deliberately: other code treats a city's first shell as
    the link target for languages it was not built in, and English is the one
    language every visitor's switcher can fall back through.
    """
    cc = countries.country_code(loc) or ""
    ordered = ["en"] if "en" in site_langs else []
    for lg in COUNTRY_LANGS.get(cc, ()):
        if lg in site_langs and lg not in ordered:
            ordered.append(lg)
    if not ordered:
        ordered = list(site_langs[:1])
    cap = SEO_PRERENDER if rich else 1
    return ordered[:max(1, cap)] or [site_langs[0]]
