"""Command-line entry point for the temperature analysis.

Generates a localised static site (one folder per language) under ``output/``:
each city's data is downloaded once (concurrently) and rendered into every
language, with a Leaflet map chooser as each language's landing page.

Examples
--------
    python main.py                          # Warszawa, all languages
    python main.py --location paris
    python main.py --all                    # every preset city, all languages
    python main.py --lat 48.85 --lon 2.35 --name Paris
    python main.py --start 1980 --end 2024 --refresh
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor

import i18n
import i18ndict
import interactive
from config import (
    DEFAULT_LOCATION,
    EARLIEST_YEAR,
    LOCATIONS,
    OUTPUT_DIR,
    Location,
)
from data import (
    load_apparent_bulk,
    load_current_bulk,
    load_current_extremes_bulk,
    load_extremes_bulk,
    load_precip_bulk,
    load_temperatures_bulk,
)
import chartdata
import chartpack
import chartspec
import config
import countries
import globaldata
import globaltext
import langtier
import ogcards
import widget
import numpy as np

from plots import (
    localize_specs,
    monthly_pivot,
    robust_trend_line,
    summary_stats,
)
from report import (
    SITE_BASE,
    build_map_page,
    build_site,
    write_citybody_js,
    write_lang_redirect,
    write_page_js,
    write_roster_base,
    write_roster_delta,
)


# Cross-city constant chart fields, hoisted out of every per-city JSON into
# one committed file (regenerate: tools/gen_chart_spec.py after a full build).
# Missing file = no stripping, so a fresh clone still builds correct output.
_SPEC_PATH = config.ROOT / "charts_spec.json"
CHART_SPEC = (json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
              if _SPEC_PATH.exists() else {})

# Split publishing: per-city payloads (charts/<slug>.json + <slug>_w.json) are
# the site's scaling term and can outgrow the main Pages artifact's 1 GB cap,
# so CI writes them to a SEPARATE directory (TEMPERATURY_PAYLOAD_DIR) pushed
# to the temperatury-charts repo's own Pages site, and pages fetch them from
# TEMPERATURY_PAYLOAD_BASE (see report.PAYLOAD_BASE). Both unset = everything
# in output/ and fetched relatively, exactly as before - local builds and the
# test suite need no second origin.
PAYLOAD_DIR = (config.ROOT / os.environ["TEMPERATURY_PAYLOAD_DIR"]
               if os.environ.get("TEMPERATURY_PAYLOAD_DIR")
               else OUTPUT_DIR / "charts")


def _last_full_year() -> int:
    """The most recent calendar year that has already ended."""
    return dt.date.today().year - 1


def _resolve_location(args: argparse.Namespace) -> Location:
    """Pick a location from an explicit lat/lon or a named preset."""
    if args.lat is not None and args.lon is not None:
        return Location(args.name or "Custom", args.lat, args.lon)
    return LOCATIONS[args.location]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--location", choices=sorted(LOCATIONS), default=DEFAULT_LOCATION,
                        help="named preset location (default: %(default)s)")
    parser.add_argument("--all", action="store_true",
                        help="generate a page for every preset city, linked together")
    parser.add_argument("--lat", type=float, help="custom latitude (use with --lon)")
    parser.add_argument("--lon", type=float, help="custom longitude (use with --lat)")
    parser.add_argument("--name", help="label for a custom lat/lon location")
    parser.add_argument("--start", type=int, default=EARLIEST_YEAR,
                        help="first year (default: %(default)s)")
    parser.add_argument("--end", type=int, default=_last_full_year(),
                        help="last full year (default: last completed year)")
    parser.add_argument("--refresh", action="store_true",
                        help="re-download even if cached data exists")
    return parser.parse_args()


def _print_summary(df, location: Location) -> None:
    """Print the headline numbers to the terminal."""
    s = summary_stats(df)
    print(f"\n{location.name}: {s['start']}-{s['end']} ({s['days']:,} days)")
    print(f"  overall mean daily temp : {s['mean']:.2f} °C")
    print(f"  warming trend           : {s['trend_per_decade']:+.2f} °C / decade")
    print(f"  warmest year            : {s['warmest_year']} ({s['warmest_value']:.2f} °C)")
    print(f"  coldest year            : {s['coldest_year']} ({s['coldest_value']:.2f} °C)")


# Language whose axis/legend text is baked into the shared, language-neutral
# charts (titles are localised in the HTML instead). English reads as neutral.
CHART_LANG = "en"

# R1-hybrid (one pre-rendered shell per city + browser-applied per-language
# dictionaries) is the default. TEMPERATURY_SERVER_I18N=1 opts back into the
# legacy per-(city x language) server render. Read once at import (each build is a
# fresh process); mirrors report._CLIENT_I18N.
CLIENT_I18N = not os.environ.get("TEMPERATURY_SERVER_I18N")


# --- parallel rendering ----------------------------------------------------
# Rendering a city's charts (matplotlib) is the build bottleneck and each city
# is independent, so cities are rendered across a process pool. ``locations``
# and the language list are the same for every city, so they are shipped once
# per worker via the pool initializer instead of in every task.
_WORKER: dict = {}


def _init_render_worker(locations: list[Location], languages: list[str],
                        analogs: dict | None = None,
                        rankpct: dict | None = None,
                        citylangs: dict | None = None,
                        cardslugs: set | None = None,
                        cardccs: set | None = None,
                        richslugs: set | None = None) -> None:
    _WORKER["locations"] = locations
    _WORKER["languages"] = languages
    _WORKER["analogs"] = analogs or {}
    _WORKER["rankpct"] = rankpct or {}
    _WORKER["citylangs"] = citylangs or {}
    # Size tiering (langtier.RICH_TIER): cities outside this set render as
    # stub pages (head + hero static, chrome injected from _citybody.js).
    # None/empty = no stubbing at all (server-i18n parity builds).
    _WORKER["richslugs"] = richslugs or None
    # Which cities ogcards gave a personal share card, and which countries got one
    # at all (small countries miss the country ranking's minimum-cities threshold).
    # Passed in rather than recomputed so og:image cannot name a PNG that is absent.
    _WORKER["cardslugs"] = cardslugs or set()
    _WORKER["cardccs"] = cardccs or set()


def _fastest_season(df, lat: float):
    """Which season (month, in the tropics) warmed fastest, from per-month
    Theil-Sen trends of that month's yearly means.

    Returns ``("season", key, degC_per_decade)`` with key winter/spring/
    summer/autumn (hemisphere-aware month groups), ``("month", 1-12, v)``
    inside the tropics where the four-season frame means little, or ``None``
    when any month has under 30 years of data (no sentence over thin data).
    """
    piv = monthly_pivot(df)
    slopes: dict[int, float] = {}
    for m in range(1, 13):
        if m not in piv.columns:
            return None
        s = piv[m].dropna()
        if len(s) < 30:
            return None
        sl, _ = robust_trend_line(s.index.to_numpy(dtype=float),
                                  s.to_numpy(dtype=float))
        slopes[m] = sl * 10
    if abs(lat) <= 23.5:
        m = max(slopes, key=lambda k: slopes[k])
        return ("month", m, slopes[m])
    seasons = ({"winter": (12, 1, 2), "spring": (3, 4, 5),
                "summer": (6, 7, 8), "autumn": (9, 10, 11)} if lat > 0 else
               {"winter": (6, 7, 8), "spring": (9, 10, 11),
                "summer": (12, 1, 2), "autumn": (3, 4, 5)})
    sv = {k: sum(slopes[m] for m in ms) / 3 for k, ms in seasons.items()}
    k = max(sv, key=lambda x: sv[x])
    return ("season", k, sv[k])


def _render_city(task) -> tuple[str, int]:
    """Render one city: charts ONCE (shared), then a page per language.

    Charts are language-neutral (titles live in the HTML, not the PNG), so they
    are rendered a single time into ``output/charts`` and every language's page
    references them - instead of re-rendering the same image 21 times. Runs in a
    worker process.
    """
    location, df, df_ext, df_precip, df_app, df_cur, df_cur_ext = task
    locations = _WORKER["locations"]
    # Language tiering: popular cities render in every language, the long tail
    # in English + the languages of its country (see langtier.py).
    languages = (_WORKER.get("citylangs", {}).get(location.slug)
                 or _WORKER["languages"])
    analog = _WORKER.get("analogs", {}).get(location.slug)
    rank_pct = _WORKER.get("rankpct", {}).get(location.slug)
    season = _fastest_season(df, location.latitude)   # language-neutral, once
    range_data = interactive.range_payload(df, extra=df_cur)
    records_data = (
        interactive.records_payload(df_ext, extra=df_cur_ext)
        if df_ext is not None else None)
    # Compute each chart's data ONCE as a language-neutral JSON payload (charts
    # are drawn in the browser now - no matplotlib render). The same pass
    # collects each label's localisation recipe, so every language's page ships
    # the shared payload plus a {english: localized} label map.
    payloads, specs = chartdata.compute_payloads(
        df, location, i18n.get(CHART_LANG),
        df_precip=df_precip, df_ext=df_ext, df_app=df_app)
    # The data is language-neutral, so write it ONCE to a shared per-city JSON
    # that every language's page fetches (instead of inlining ~50 KB × 21 langs).
    # The range/records widget payloads ride along under reserved _-keys (the
    # page inits those widgets from this fetch too), so their ~23 KB is not
    # duplicated into all 32 language copies of every page.
    # Charts only: range_data/records_data are handed to build_site below as well,
    # so they must not be rewritten here. They carry no duplicated year axis anyway.
    _years = chartdata.dedupe_year_axes(payloads)
    # The monthly-range/records widgets are rich-tier only: their payloads are
    # over half a tail city's chart JSON (~17 KB of ~30 KB measured), and the
    # stub page drops the two widget figures to match (report._CITYBODY_JS
    # prunes on the same flags this write is gated on).
    _rich_set = _WORKER.get("richslugs")
    _stub = bool(_rich_set) and location.slug not in _rich_set
    shared = dict(payloads)
    if not _stub:
        shared["_range"] = range_data
    if _years:
        shared["_years"] = _years
    if records_data is not None and not _stub:
        shared["_records"] = records_data
    # Tail (stub) cities keep the monthly-range/records widgets ON DEMAND:
    # their payload (over half a tail city's chart JSON) rides a separate
    # <slug>_w.json that _page.js fetches only when the visitor scrolls the
    # widgets into view - visitors who never reach them cost nothing.
    widgets = {"_range": range_data} if _stub else None
    if widgets is not None and records_data is not None:
        widgets["_records"] = records_data
    # Client-i18n serves one shell per city, so the {english: localized} chart-
    # label map cannot be baked per page. Ship each label's serialisable recipe
    # instead (flattened across charts); the browser rebuilds the map from the
    # active dictionary on load and on every language switch. Language-neutral,
    # so it rides the shared per-city JSON, not the per-language pages.
    if CLIENT_I18N:
        shared["_labels"] = [pair for cs in specs.values() for pair in cs]
    charts_dir = PAYLOAD_DIR
    charts_dir.mkdir(parents=True, exist_ok=True)
    # Cross-city constant fields are stripped against the committed spec
    # (chartspec; charts.js merges them back), then numeric arrays ship as
    # verified-lossless packed ints (chartpack) - the Pages cap counts
    # uncompressed bytes, so this on-disk encoding is what actually shrinks
    # the artifact. charts.js __unpackCharts is the inverse. Strip precedes
    # pack: the spec matches unpacked scalar values.
    (charts_dir / f"{location.slug}.json").write_text(
        json.dumps(chartpack.pack_tree(chartspec.strip(shared, CHART_SPEC)),
                   ensure_ascii=False),
        encoding="utf-8")
    _wpath = charts_dir / f"{location.slug}_w.json"
    if widgets is not None:
        _wpath.write_text(
            json.dumps(chartpack.pack_tree(widgets), ensure_ascii=False),
            encoding="utf-8")
    else:
        # A city promoted to rich keeps its widgets inline again; a stale
        # sidecar in the CI cache would deploy unreferenced. The cached copy
        # may already live inside a shard dir (tools/shard_payloads.py).
        _wpath.unlink(missing_ok=True)
        for _shard_copy in charts_dir.glob(f"shard-*/{location.slug}_w.json"):
            _shard_copy.unlink(missing_ok=True)
    if charts_dir != OUTPUT_DIR / "charts":
        # Split build over a cache/worktree that once built unsplit: the same
        # payload must not ALSO ship (stale) inside the main site artifact.
        for _stale in (f"{location.slug}.json", f"{location.slug}_w.json"):
            (OUTPUT_DIR / "charts" / _stale).unlink(missing_ok=True)
    n = 0
    for lang in languages:
        tr = i18n.get(lang)
        chart_i18n: dict[str, str] = {}
        for cs in specs.values():
            chart_i18n.update(localize_specs(cs, tr))
        build_site(df, location, OUTPUT_DIR / lang, locations, lang, languages, tr,
                   range_data=range_data, records_data=records_data,
                   has_precip=df_precip is not None,
                   has_dtr=df_ext is not None,
                   has_appheat=df_app is not None,
                   chart_i18n=chart_i18n, analog=analog, rank_pct=rank_pct,
                   df_cur=df_cur, season=season,
                   has_og_card=location.slug in _WORKER.get("cardslugs", ()),
                   og_card_ccs=_WORKER.get("cardccs", frozenset()),
                   stub=_stub)
        n += 1
    return location.slug, n


def main() -> None:
    args = _parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start ({args.start}) must not exceed --end ({args.end}).")

    # Optional TEMPERATURY_LANGS=pl,en restricts which languages render - lets a
    # CI build ship a fast subset (e.g. a map/HTML fix) without the full
    # 21-language chart render. Unset = every language (normal behaviour).
    _langs_env = os.environ.get("TEMPERATURY_LANGS", "").strip()
    if _langs_env:
        wanted = [c.strip() for c in _langs_env.split(",") if c.strip()]
        i18n.LANGUAGES = [l for l in i18n.LANGUAGES if l in wanted]
        print(f"Restricting to languages: {i18n.LANGUAGES}")

    if args.all:
        # Prioritise the download queue by the city's country GDP per capita
        # (highest first): early visitors skew toward wealthier countries, so
        # their cities should be covered first as the backfill fills in. Cache-
        # aware fetching means already-downloaded cities are a no-op, so this
        # only steers which of the still-missing cities are fetched next.
        locations = sorted(LOCATIONS.values(), key=countries.download_priority_key)
    else:
        locations = [_resolve_location(args)]

    # Fetch all locations in a few bulk requests (cache-aware). Data is
    # language-neutral, so it is downloaded once and rendered in every language.
    print(f"Fetching {len(locations)} location(s) {args.start}-{args.end} …")
    frames = load_temperatures_bulk(locations, args.start, args.end,
                                    refresh=args.refresh)

    # Build only the cities we actually have data for (a rate-limited or
    # unreachable city is skipped rather than failing the whole site).
    missing = [loc.name for loc in locations if loc.slug not in frames]
    if missing:
        print(f"Note: {len(missing)} location(s) without data, skipped: "
              f"{', '.join(missing)}")
    locations = [loc for loc in locations if loc.slug in frames]
    if not locations:
        raise SystemExit("No location data available - nothing to build.")

    # Per-city payloads are stripped against the spec, so EVERY build path that
    # writes city charts must also publish the spec the client merges back in -
    # single-city test builds included, not just --all.
    if CHART_SPEC:
        (OUTPUT_DIR / "charts").mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "charts" / "_spec.json").write_text(
            json.dumps(CHART_SPEC, ensure_ascii=False), encoding="utf-8")

    # Daily max/min (record highs/lows) - optional add-on dataset; a city
    # without it simply skips the record chart.
    extremes = load_extremes_bulk(locations, args.start, args.end,
                                  refresh=args.refresh)
    # Daily precipitation - optional add-on dataset (same backfill model).
    precip = load_precip_bulk(locations, args.start, args.end,
                              refresh=args.refresh)
    # Apparent temperature (humidity-aware heat index) - powers the heat-index
    # health chart; same optional-add-on backfill model.
    apparent = load_apparent_bulk(locations, args.start, args.end,
                                  refresh=args.refresh)
    # The year in progress (partial) - fed only to the interactive widgets so
    # readers can pick it, kept out of the static trend charts. Cached under a
    # distinct key; in offline mode only committed current-year data is used.
    current = load_current_bulk(locations, refresh=args.refresh)
    current_ext = load_current_extremes_bulk(locations, refresh=args.refresh)

    # Charts are drawn in the browser now (Chart.js): ship the shared render
    # layer as a root asset, and drop stale artefacts a cached build may carry
    # (old per-language PNGs and the pre-interactive shared SVGs).
    from pathlib import Path
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # cold build: no restored cache
    _charts_js = Path(__file__).resolve().parent / "assets" / "charts.js"
    (OUTPUT_DIR / "charts.js").write_bytes(_charts_js.read_bytes())
    # Appearance runtime: the visitor-facing look/theme picker (a root asset each
    # page links). A tiny inline bootstrap in <head> applies the saved choice
    # before paint; this file adds the panel that changes it.
    _appearance_js = Path(__file__).resolve().parent / "assets" / "appearance.js"
    (OUTPUT_DIR / "appearance.js").write_bytes(_appearance_js.read_bytes())
    # Client-side i18n runtime (R1-hybrid): shared root asset that applies a
    # per-language dictionary to the pre-rendered shell in the browser.
    _i18n_rt = Path(__file__).resolve().parent / "assets" / "i18n-runtime.js"
    (OUTPUT_DIR / "i18n-runtime.js").write_bytes(_i18n_rt.read_bytes())
    # Per-language dictionaries (window.__i18n): one small file per language, so
    # a language costs ~one dictionary instead of a full set of rendered pages.
    _n_dicts = i18ndict.build_lang_dicts(OUTPUT_DIR, i18n.LANGUAGES)
    print(f"Wrote {_n_dicts} language dictionaries to {OUTPUT_DIR / 'i18n'}.")
    # City-page CSS is identical on every page and language-neutral, so ship it
    # once as a root asset each page links (browser-cached) instead of inlining
    # ~17 KB into every one of the (cities x languages) pages.
    _page_css = Path(__file__).resolve().parent / "assets" / "page.css"
    (OUTPUT_DIR / "page.css").write_bytes(_page_css.read_bytes())
    # Landing/world-map CSS: shared, language-neutral root asset the map page
    # links (browser-cached) instead of inlining ~17 KB into every language's
    # index.html. Both page.css and landing.css are generated from their
    # *.src.css sources by tools/build-css.sh (Tailwind v4); do not hand-edit.
    _landing_css = Path(__file__).resolve().parent / "assets" / "landing.css"
    (OUTPUT_DIR / "landing.css").write_bytes(_landing_css.read_bytes())
    # Country border silhouettes for the hero (shared, language-neutral, keyed by
    # ISO alpha-2). Shipped once and fetched client-side by every hero, so the
    # path bytes are never duplicated across the (cities x languages) pages.
    # ONE FILE PER COUNTRY: a hero draws a single country, so shipping all 174
    # (27.7 KB gzipped) put 27 KB of other countries' borders on the entry path of
    # the landing page AND every city page. A slice is 0.2-1.5 KB.
    _outlines = Path(__file__).resolve().parent / "assets" / "country_outlines.json"
    if _outlines.is_file():
        (OUTPUT_DIR / "charts").mkdir(parents=True, exist_ok=True)
        for _cc, _shape in json.loads(_outlines.read_text(encoding="utf-8")).items():
            (OUTPUT_DIR / "charts" / f"outline.{_cc}.json").write_text(
                json.dumps(_shape), encoding="utf-8")
    for _lang in i18n.LANGUAGES:
        for _png in (OUTPUT_DIR / _lang).glob("*.png"):
            _png.unlink()
    _charts_dir = OUTPUT_DIR / "charts"
    if _charts_dir.is_dir():
        for _svg in _charts_dir.glob("*.svg"):
            _svg.unlink()
        # CI restores output/ from a cache and deploys it as-is, so the combined
        # payloads this build replaced with per-language / per-country slices would
        # otherwise linger and ship forever - 1.1 MB nothing references.
        for _legacy in ("_names.json", "country_outlines.json"):
            (_charts_dir / _legacy).unlink(missing_ok=True)
    # Server->client (R1-hybrid) or SEO-tier cutover: a restored cache may carry
    # per-language city pages this build no longer generates (a city now renders
    # only its SEO shells). Drop any <lang>/<slug>.html whose language is not in
    # that city's SEO set, so the deployed site is not bloated with stale,
    # pre-cutover pages (which could push it back over the 1 GB Pages cap) or
    # serve outdated content. Only cities in THIS build are touched (so a
    # --location build never prunes another city), and non-city pages (index,
    # embed) are keyed by name, not a city slug, so they are never matched.
    if CLIENT_I18N:
        _rich_prune = langtier.rich_tier_slugs(list(LOCATIONS.values()))
        _seo = {loc.slug: set(langtier.seo_languages_for(
                    loc, i18n.LANGUAGES, loc.slug in _rich_prune))
                for loc in locations
                if getattr(loc, "kind", "city") == "city"}
        _pruned = 0
        for _lang in i18n.LANGUAGES:
            _ld = OUTPUT_DIR / _lang
            if not _ld.is_dir():
                continue
            for _html in _ld.glob("*.html"):
                _langs = _seo.get(_html.stem)
                if _langs is not None and _lang not in _langs:
                    _html.unlink()
                    _pruned += 1
        if _pruned:
            print(f"Pruned {_pruned} stale per-language city page(s) a pre-cutover "
                  "cache carried.")

    # Per-city render tasks (each carries its city's data). The summary print
    # stays in the main process so log order is stable. Charts are now cheap to
    # (re)compute (no matplotlib render), so every city is built every run.
    tasks = []
    for location in locations:
        df = frames[location.slug]
        if len(locations) == 1:
            _print_summary(df, location)
        else:
            s = summary_stats(df)
            print(f"  {location.name:18s} mean {s['mean']:5.1f} °C  "
                  f"trend {s['trend_per_decade']:+.2f}/dec")
        tasks.append((location, df, extremes.get(location.slug),
                      precip.get(location.slug), apparent.get(location.slug),
                      current.get(location.slug), current_ext.get(location.slug)))

    # World & regional dashboard: aggregate every city into latitudinal climate
    # zones + a world average (mean-of-anomalies), computed ONCE as a shared,
    # language-neutral payload. Computed BEFORE the city pages so each city page
    # can server-render its climate analogs (1940 past + 2050 future) into the
    # HTML for search engines, instead of fetching them client-side.
    g_payload, g_specs, g_meta = globaldata.compute_global(
        frames, locations, globaltext.overlay(i18n.get(CHART_LANG), CHART_LANG))
    g_analogs = g_payload.get("analogs", {})
    # Language tiering (the 32-language x full-roster product would blow the
    # ~1 GB Pages artifact cap): the most-populous cities keep every language,
    # tail cities build in English + their country's languages. Ranked over the
    # FULL roster so a city's tier is stable as the data cache grows.
    # Under client-i18n (R1-hybrid) storage no longer scales with languages, so
    # a city pre-renders only its SEO languages (English + country primary) as
    # shells; every language is reachable in the browser. Otherwise fall back to
    # storage-tiering (full langs for popular cities, en+local for the tail).
    if CLIENT_I18N:
        # Size tiering: only the top cities pre-render every SEO language; the
        # tail gets one shell (see langtier.RICH_TIER). Ranked over the FULL
        # roster so a city's tier is stable as the data cache grows.
        _rich = langtier.rich_tier_slugs(list(LOCATIONS.values()))
        g_citylangs = {loc.slug: langtier.seo_languages_for(
                           loc, i18n.LANGUAGES, loc.slug in _rich)
                       for loc in locations}
    else:
        _full = langtier.full_tier_slugs(list(LOCATIONS.values()))
        g_citylangs = {loc.slug: langtier.languages_for(
                           loc, loc.slug in _full, i18n.LANGUAGES)
                       for loc in locations}

    # Landing KPI band + zone sparkline cards, computed from the SAME
    # cell-weighted anomaly series the world/zone charts draw (so the band's
    # numbers always match the charts below it).
    def _series_kpis(reg: dict) -> dict | None:
        a = reg["anomaly"]
        yrs = np.asarray(a["x"], dtype=float)
        vals = np.asarray([v if v is not None else np.nan
                           for v in a["raw"]["data"]], dtype=float)
        ok = np.isfinite(vals)
        if int(ok.sum()) < 10:
            return None
        slope, _line = robust_trend_line(yrs[ok], vals[ok])
        span = float(yrs[ok].max() - yrs[ok].min())
        return {"t": round(slope * 10, 2), "dt": round(slope * span, 1),
                "wy": int(yrs[ok][int(np.argmax(vals[ok]))]),
                "spark": [v for v in a["loess"]["data"] if v is not None]}

    g_kpis = None
    _wk = _series_kpis(g_payload["regions"].get("world", {"anomaly": None})) \
        if g_payload["regions"].get("world") else None
    if _wk:
        g_kpis = {"rate": _wk["t"], "since": _wk["dt"], "wy": _wk["wy"],
                  "zones": [dict(key=z, t=zk["t"], spark=zk["spark"])
                            for z in g_payload["order"] if z != "world"
                            for zk in [_series_kpis(g_payload["regions"][z])]
                            if zk]}
    # Per-city "warming faster than N% of the world" hero badge. Floor, not
    # round, so the fastest city reads 99% - never a self-including 100%. A
    # small dev build (one city ranked against itself) shows no badge at all.
    _rk = g_payload.get("ranking") or []
    g_rankpct = ({r["s"]: (100 * (len(_rk) - i - 1)) // len(_rk)
                  for i, r in enumerate(_rk)} if len(_rk) >= 50 else {})
    (OUTPUT_DIR / "charts").mkdir(parents=True, exist_ok=True)
    # The ranking is _global.json's scaling term (one row per covered city,
    # measured ~563 KB of a 992 KB payload at 3,548 cities and every landing
    # visit downloads it); ship it columnar+packed (chartpack.pack_rows,
    # verified-inverse) and inflate client-side right after the fetch
    # (charts.js __inflateGlobal; the standalone widget carries its own copy).
    g_wire = dict(g_payload)
    # Explicit nulls (a city without population data carries "pop": null) are
    # dead wire bytes and indistinguishable from an absent key to every
    # consumer (all guard with typeof/!= null); drop them so the columnar
    # form's absent-key round trip verifies exactly.
    g_wire["ranking"] = chartpack.pack_rows(
        [{k: v for k, v in row.items() if v is not None}
         for row in (g_payload.get("ranking") or [])])
    (OUTPUT_DIR / "charts" / "_global.json").write_text(
        json.dumps(g_wire, ensure_ascii=False), encoding="utf-8")
    # Tiny real-data file for the topbar warming badge (fetched by every page).
    # Only the honest, computed world-city aggregates - no fabricated values. With
    # no ranking (e.g. a single custom-location build) emit null, not a bare 0.0,
    # so the client shows no badge rather than a misleading "+0.0".
    _has_rank = bool(g_payload.get("ranking"))
    (OUTPUT_DIR / "charts" / "_world.json").write_text(
        json.dumps({"gt": g_payload.get("gt") if _has_rank else None,
                    "gdt": g_payload.get("gdt") if _has_rank else None,
                    "gn": g_payload.get("gn") if _has_rank else None}),
        encoding="utf-8")
    # Localized place names for the ranking (drawn in the browser from the shared
    # payload, so names are localized client-side). One file PER LANGUAGE, not one
    # {slug: {lang: name}} table for all of them: the combined table is 309 KB
    # gzipped and the landing page had to fetch every language's names before it
    # could draw anything. A slice is 5-40 KB.
    # Keyed by the BASE language code, because that is what the browser asks for
    # (document.documentElement.lang.split('-')[0]) and how the exonym table is
    # keyed: zh-TW and zh share _names.zh.json. Emitting a regional variant its own
    # file would write an English-fallback-only slice nothing ever fetches.
    from report import place_names_for
    _name_langs = sorted({_l.split("-")[0] for _l in i18n.LANGUAGES})
    for _base in _name_langs:
        (OUTPUT_DIR / "charts" / f"_names.{_base}.json").write_text(
            json.dumps(place_names_for(_base), ensure_ascii=False),
            encoding="utf-8")
    # A restored cache may hold slices for languages (or regional variants) this
    # build no longer emits; they would deploy unreferenced.
    _want = {f"_names.{_b}.json" for _b in _name_langs}
    for _old in (OUTPUT_DIR / "charts").glob("_names.*.json"):
        if _old.name not in _want:
            _old.unlink()
    # Data-coverage grid: per-cell mean-file coverage over the FULL target set
    # (config.LOCATIONS, not just the rendered cities), so the map's overlay shows
    # which reanalysis cells still need downloading. Derived from committed files,
    # never live requests; the browser only colours the precomputed counts.
    import coveragegrid
    _cov = coveragegrid.compute_cells(args.start, args.end)
    (OUTPUT_DIR / "charts" / "_coverage.json").write_text(
        json.dumps(_cov, ensure_ascii=False), encoding="utf-8")
    _cov_have = sum(c["n"] for c in _cov["cells"])
    _cov_tot = sum(c["m"] for c in _cov["cells"])
    print(f"Wrote coverage grid ({len(_cov['cells'])} cells, "
          f"{_cov_have}/{_cov_tot} cities with data).")
    # Open Graph share cards (1200x630): one per country, a world card, and a
    # personal card for the most-populous cities (ogcards.CITY_CARDS) - the tail
    # previews its country's card instead of adding ~20 KB of PNG per page.
    g_cardslugs = ogcards.city_card_slugs(g_payload)
    g_cardccs = ogcards.country_card_ccs(g_payload)
    n_cards = ogcards.build_cards(g_payload, OUTPUT_DIR)
    print(f"Wrote {n_cards} share cards to {OUTPUT_DIR / 'og'} "
          f"({len(g_cardslugs)} per-city).")
    # Embeddable ranking widget + its embed-code builder (reads _global.json).
    widget.build_widgets(OUTPUT_DIR)
    print(f"Wrote the embeddable widget + builder to {OUTPUT_DIR}.")

    # Render cities across a process pool - cities are independent (each writes
    # its own files). TEMPERATURY_JOBS overrides the worker count (default: all
    # cores). Each worker gets the analogs so every page server-renders them.
    jobs = int(os.environ.get("TEMPERATURY_JOBS") or 0) or (os.cpu_count() or 1)
    jobs = max(1, min(jobs, len(tasks)))
    written = 0
    # Stub tiering only exists in the client-i18n build (_citybody.js relies on
    # the client runtime); the server-i18n parity build renders full pages.
    g_richslugs = _rich if CLIENT_I18N else None
    if jobs == 1:
        _init_render_worker(locations, i18n.LANGUAGES, g_analogs, g_rankpct,
                            g_citylangs, g_cardslugs, g_cardccs, g_richslugs)
        for task in tasks:
            written += _render_city(task)[1]
    else:
        print(f"Rendering {len(tasks)} cities × {len(i18n.LANGUAGES)} languages "
              f"on {jobs} processes …")
        # ``fork`` inherits the parent's imports/data and avoids re-importing
        # __main__ (Python 3.14 defaults to forkserver, which would).
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=jobs, mp_context=ctx,
                                 initializer=_init_render_worker,
                                 initargs=(locations, i18n.LANGUAGES, g_analogs,
                                           g_rankpct, g_citylangs,
                                           g_cardslugs, g_cardccs,
                                           g_richslugs)) as pool:
            for _slug, n in pool.map(_render_city, tasks):
                written += n

    # Preview build (TEMPERATURY_PREVIEW=1): plot every preset city we intend to
    # cover but do not have data for yet, as faint dots, so the full scale of the
    # project is visible while the data backfill catches up.
    preview_locs = []
    if os.environ.get("TEMPERATURY_PREVIEW"):
        _built = {loc.slug for loc in locations}
        preview_locs = [l for l in LOCATIONS.values()
                        if getattr(l, "kind", "city") == "city" and l.slug not in _built]
        print(f"Preview: {len(preview_locs)} cities awaiting data shown as faint dots.")

    # The language-neutral roster, written ONCE: coords, zones, kinds, regions,
    # canonical names and each city's shell set. The per-language _delta.json
    # (written in the loop below) layers localized names/labels over it.
    write_roster_base(OUTPUT_DIR / "charts" / "_base.json", locations,
                      g_citylangs, preview_locs)

    # Each language's index.html is the world map (climate zones) with the
    # world/regional dashboard embedded below it; root redirects to it.
    for lang in i18n.LANGUAGES:
        gtr = globaltext.overlay(i18n.get(lang), lang)
        g_i18n: dict[str, str] = {}
        g_i18n_f: dict[str, str] = {}
        for cs in g_specs.values():
            g_i18n.update(localize_specs(cs, gtr))
            g_i18n_f.update(localize_specs(cs, gtr, unit="F"))
        build_map_page(OUTPUT_DIR / lang, locations, lang, i18n.LANGUAGES, gtr,
                       g_i18n, g_i18n_f, g_meta, len(locations),
                       preview_locs=preview_locs,
                       ranking=g_payload.get("ranking"),
                       # Full target roster (every city we intend to cover), so
                       # the map can report real coverage progress.
                       target_cities=sum(
                           1 for l in LOCATIONS.values()
                           if getattr(l, "kind", "city") == "city"),
                       # Tiering: dots for cities without a page in this
                       # language link to the city's first built language.
                       city_langs=g_citylangs,
                       kpis=g_kpis)
        # Per-language roster overrides: only the localized names/labels that
        # differ from the language-neutral charts/_base.json (written once,
        # after this loop). The topbar search, map dots and omni index all
        # derive from that pair client-side - the old per-language
        # _cities.json/_map.json/_omni.json sidecars repeated the
        # language-invariant bulk once per language (~46 KB per city site-wide).
        write_roster_delta(OUTPUT_DIR / lang / "_delta.json", lang, locations,
                           i18n.get(lang))
        # The old sidecars (and the even older blocking _cities.js) linger in a
        # restored cache, and CI uploads output/ wholesale - drop them so they
        # cannot keep deploying unreferenced. (_map/_omni are dropped in
        # build_map_page.)
        for _legacy_sidecar in ("_cities.js", "_cities.json"):
            (OUTPUT_DIR / lang / _legacy_sidecar).unlink(missing_ok=True)
        # Shared city-page runtime: everything that used to be inlined into
        # every city page but is identical across a language's cities.
        write_page_js(OUTPUT_DIR / lang, i18n.get(lang), lang)
        # Stub (tail-tier) pages rebuild their body chrome from this script;
        # only meaningful in the client-i18n build.
        if CLIENT_I18N:
            write_citybody_js(OUTPUT_DIR / lang, i18n.get(lang), lang,
                              i18n.LANGUAGES)
        written += 1
    # Root index auto-picks the visitor's language folder (saved choice →
    # location via timezone → browser language → default).
    write_lang_redirect(
        OUTPUT_DIR / "index.html", i18n.LANGUAGES, i18n.DEFAULT_LANG,
        countries.tz_country_map(), countries.country_lang_map(),
    )
    written += 1

    # SEO: a sitemap of every rendered page + a robots.txt pointing at it.
    # Glob the actual HTML so only pages that exist (cities with data) are listed.
    pages = [f"{SITE_BASE}/"]
    for _lang in i18n.LANGUAGES:
        _d = OUTPUT_DIR / _lang
        if _d.exists():
            pages += [f"{SITE_BASE}/{_lang}/{_f.name}"
                      for _f in sorted(_d.glob("*.html"))]
    pages += [f"{SITE_BASE}/{_e}" for _e in ("embed.html", "widget.html")
              if (OUTPUT_DIR / _e).exists()]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "\n".join(f"  <url><loc>{u}</loc></url>" for u in pages)
               + "\n</urlset>\n")
    (OUTPUT_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUTPUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE}/sitemap.xml\n",
        encoding="utf-8")
    print(f"Wrote sitemap.xml ({len(pages)} URLs) and robots.txt.")

    print(f"\nWrote {written} files to {OUTPUT_DIR} "
          f"({len(locations)} cities × {len(i18n.LANGUAGES)} languages).")


if __name__ == "__main__":
    main()
