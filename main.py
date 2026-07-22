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
    write_cities_js,
    write_lang_redirect,
    write_page_js,
)


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
                        citylangs: dict | None = None) -> None:
    _WORKER["locations"] = locations
    _WORKER["languages"] = languages
    _WORKER["analogs"] = analogs or {}
    _WORKER["rankpct"] = rankpct or {}
    _WORKER["citylangs"] = citylangs or {}


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
    shared = {**payloads, "_range": range_data}
    if records_data is not None:
        shared["_records"] = records_data
    # Client-i18n serves one shell per city, so the {english: localized} chart-
    # label map cannot be baked per page. Ship each label's serialisable recipe
    # instead (flattened across charts); the browser rebuilds the map from the
    # active dictionary on load and on every language switch. Language-neutral,
    # so it rides the shared per-city JSON, not the per-language pages.
    if CLIENT_I18N:
        shared["_labels"] = [pair for cs in specs.values() for pair in cs]
    charts_dir = OUTPUT_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    (charts_dir / f"{location.slug}.json").write_text(
        json.dumps(shared, ensure_ascii=False), encoding="utf-8")
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
                   df_cur=df_cur, season=season)
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
        locations = [LOCATIONS[key] for key in sorted(LOCATIONS)]
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
    _outlines = Path(__file__).resolve().parent / "assets" / "country_outlines.json"
    if _outlines.is_file():
        (OUTPUT_DIR / "charts").mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "charts" / "country_outlines.json").write_bytes(_outlines.read_bytes())
    for _lang in i18n.LANGUAGES:
        for _png in (OUTPUT_DIR / _lang).glob("*.png"):
            _png.unlink()
    _charts_dir = OUTPUT_DIR / "charts"
    if _charts_dir.is_dir():
        for _svg in _charts_dir.glob("*.svg"):
            _svg.unlink()
    # Server->client (R1-hybrid) or SEO-tier cutover: a restored cache may carry
    # per-language city pages this build no longer generates (a city now renders
    # only its SEO shells). Drop any <lang>/<slug>.html whose language is not in
    # that city's SEO set, so the deployed site is not bloated with stale,
    # pre-cutover pages (which could push it back over the 1 GB Pages cap) or
    # serve outdated content. Only cities in THIS build are touched (so a
    # --location build never prunes another city), and non-city pages (index,
    # embed) are keyed by name, not a city slug, so they are never matched.
    if CLIENT_I18N:
        _seo = {loc.slug: set(langtier.seo_languages_for(loc, i18n.LANGUAGES))
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
        g_citylangs = {loc.slug: langtier.seo_languages_for(loc, i18n.LANGUAGES)
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
    (OUTPUT_DIR / "charts" / "_global.json").write_text(
        json.dumps(g_payload, ensure_ascii=False), encoding="utf-8")
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
    # Localized place names {slug: {lang: name}} for the ranking (drawn in the
    # browser from the shared payload, so names are localized client-side).
    from report import all_place_names
    (OUTPUT_DIR / "charts" / "_names.json").write_text(
        json.dumps(all_place_names(), ensure_ascii=False), encoding="utf-8")
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
    # Open Graph share cards (1200x630): one per country + a world card, so a
    # link to any city previews its country's warming stat on social media.
    n_cards = ogcards.build_cards(g_payload, OUTPUT_DIR)
    print(f"Wrote {n_cards} share cards to {OUTPUT_DIR / 'og'}.")
    # Embeddable ranking widget + its embed-code builder (reads _global.json).
    widget.build_widgets(OUTPUT_DIR)
    print(f"Wrote the embeddable widget + builder to {OUTPUT_DIR}.")

    # Render cities across a process pool - cities are independent (each writes
    # its own files). TEMPERATURY_JOBS overrides the worker count (default: all
    # cores). Each worker gets the analogs so every page server-renders them.
    jobs = int(os.environ.get("TEMPERATURY_JOBS") or 0) or (os.cpu_count() or 1)
    jobs = max(1, min(jobs, len(tasks)))
    written = 0
    if jobs == 1:
        _init_render_worker(locations, i18n.LANGUAGES, g_analogs, g_rankpct,
                            g_citylangs)
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
                                           g_rankpct, g_citylangs)) as pool:
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

    # Each language's index.html is the world map (climate zones) with the
    # world/regional dashboard embedded below it; root redirects to it.
    for lang in i18n.LANGUAGES:
        gtr = globaltext.overlay(i18n.get(lang), lang)
        g_i18n: dict[str, str] = {}
        for cs in g_specs.values():
            g_i18n.update(localize_specs(cs, gtr))
        build_map_page(OUTPUT_DIR / lang, locations, lang, i18n.LANGUAGES, gtr,
                       g_i18n, g_meta, len(locations), preview_locs=preview_locs,
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
        # Shared per-language city list for the topbar search - written once here
        # and referenced by every city page (browser-cached), instead of inlining
        # ~35 KB into each of the (cities x languages) pages. Regenerated each
        # build so the search stays current even on incrementally-cached pages.
        _cities = [loc for loc in locations
                   if getattr(loc, "kind", "city") == "city"]
        if CLIENT_I18N:
            # Every language reaches every city (a switch is client-side), so the
            # search lists ALL cities; a city with no shell in this language links
            # to one it does have (its first SEO shell, always including en), which
            # then auto-localizes to the visitor's saved language on arrival.
            def _url_of(loc, _lang=lang):
                shells = g_citylangs.get(loc.slug, [])
                if _lang in shells:
                    return f"{loc.slug}.html"
                folder = shells[0] if shells else "en"
                return f"../{folder}/{loc.slug}.html"
            write_cities_js(OUTPUT_DIR / lang / "_cities.js", _cities,
                            i18n.get(lang), url_of=_url_of)
        else:
            # Storage-tiering: only cities whose page exists in THIS language, so
            # the search never links a 404.
            write_cities_js(
                OUTPUT_DIR / lang / "_cities.js",
                [loc for loc in _cities
                 if lang in g_citylangs.get(loc.slug, [])],
                i18n.get(lang))
        # Shared city-page runtime: everything that used to be inlined into
        # every city page but is identical across a language's cities.
        write_page_js(OUTPUT_DIR / lang, i18n.get(lang), lang)
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
