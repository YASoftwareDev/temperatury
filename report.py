"""Generate a self-contained static web page for GitHub Pages.

``build_site`` writes ``<slug>.html`` into a per-language output directory. The
charts are drawn in the browser with Chart.js (see :mod:`chartdata` and
``assets/charts.js``): each page fetches a shared, language-neutral
``charts/<slug>.json`` and localises the labels via an inline ``__ci18n`` map.
Each page carries a city switcher (same language) and a language switcher (same
city, sibling-language folder). CSS is inline; Chart.js + plugins load from CDN.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from html import escape as _esc
from pathlib import Path
from string import Template
from urllib.parse import quote

import captions
import deephist
import globaltext
import i18n
import interactive
import ranktext
import countries
from config import ALIASES, DEFAULT_LOCATION, REGIONS, Location, slugify
from globaldata import _ZONE_COLOR, _ZONE_NAME_KEY, zone_of

# Public site root - Open Graph image/URL tags must be ABSOLUTE for social
# scrapers (X / Facebook / LinkedIn) to resolve them; relative paths are ignored.
SITE_BASE = "https://yasoftwaredev.github.io/temperatury"
_SITE_NAME = "temperatury"

# R1-hybrid client-side i18n: when set, city pages carry data-i18n keys + the
# runtime + a per-language dictionary, so the browser localises the shell.
# Unset (default) reproduces the fully server-rendered pages byte-for-byte.
# R1-hybrid client-side i18n is the default. Set TEMPERATURY_SERVER_I18N=1 to opt
# back into the legacy per-(city x language) server render - the escape hatch the
# parity harness uses to build a server-rendered reference to diff against.
_CLIENT_I18N = not os.environ.get("TEMPERATURY_SERVER_I18N")


def _i18n_head(slug: str, lang: str, languages: list[str], name: str) -> str:
    """Per-page tail scripts for client i18n: the city's localized-name map, this
    language's dictionary, and the runtime. "" when the flag is off. Order:
    names + dict (sets window.__i18n/__lang/__dir) load before the runtime, which
    applies them on DOMContentLoaded."""
    if not _CLIENT_I18N:
        return ""
    names = json.dumps({lg: _local_name(slug, lg, name) for lg in languages},
                       ensure_ascii=False, separators=(",", ":"))
    return (f"<script>window.__cityNames={names};</script>\n"
            f'<script src="../i18n/{lang}.js"></script>\n'
            '<script src="../i18n-runtime.js"></script>')


def _i18n_attr(key: str, vars: dict | None = None, html: bool = False) -> str:
    """Emit ``data-i18n`` attributes for the client runtime, or "" when the flag
    is off (so the default build is unchanged). ``vars`` fill ``{placeholders}``
    client-side; ``html=True`` sets innerHTML (for values carrying markup)."""
    if not _CLIENT_I18N:
        return ""
    out = f' data-i18n="{key}"'
    if html:
        out += ' data-i18n-html="1"'
    if vars:
        out += " data-i18n-vars='" + _esc(
            json.dumps(vars, ensure_ascii=False, separators=(",", ":")),
            quote=True) + "'"
    return out


def _i18n_span(inner: str, key: str, vars: dict | None = None,
               html: bool = False) -> str:
    """Wrap already-rendered text in a keyed ``<span>`` so the client runtime can
    re-localize it on a language switch; return the text unchanged when the flag
    is off (byte-identical default build). For surfaces not already inside their
    own element (footer text, embed link). ``html=True`` when the value carries
    markup (e.g. the footer's source links), so the runtime sets innerHTML."""
    if not _CLIENT_I18N:
        return inner
    return f"<span{_i18n_attr(key, vars, html)}>{inner}</span>"

# Localized place names {slug: {lang: name}} from GeoNames (tools/gen_city_names.py),
# so a Polish page says "Monachium", a German one "Wien". Sparse: only real exonyms.
try:
    _CITY_NAMES = json.loads((Path(__file__).resolve().parent / "data"
                              / "city_names.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    _CITY_NAMES = {}

# The map's reference points (oceans, poles, regions) are not GeoNames cities, so
# they carry no exonyms; localize the ones that have an established name in a given
# language here. Only Polish for now; every other language falls back to English.
_REF_NAMES = {
    "Greenland Ice Sheet": {"pl": "Lądolód Grenlandzki"},
    "North Pole": {"pl": "Biegun Północny"},
    "Central Siberia": {"pl": "Syberia Środkowa"},
    "Northern Canada": {"pl": "Północna Kanada"},
    "Kazakh Steppe": {"pl": "Step Kazachski"},
    "Tibetan Plateau": {"pl": "Wyżyna Tybetańska"},
    "Central Sahara": {"pl": "Środkowa Sahara"},
    "Interior Brazil": {"pl": "Wnętrze Brazylii"},
    "Western Australia Outback": {"pl": "Interior Australii Zachodniej"},
    "New Guinea Highlands": {"pl": "Wyżyny Nowej Gwinei"},
    "Borneo Interior": {"pl": "Wnętrze Borneo"},
    "Vostok, Antarctica": {"pl": "Wostok, Antarktyda"},
    "Antarctic Peninsula": {"pl": "Półwysep Antarktyczny"},
    "Equatorial Atlantic": {"pl": "Atlantyk Równikowy"},
    "Equatorial Pacific": {"pl": "Pacyfik Równikowy"},
    "North Atlantic": {"pl": "Atlantyk Północny"},
    "North Pacific": {"pl": "Pacyfik Północny"},
    "Southern Ocean": {"pl": "Ocean Południowy"},
    "Central Indian Ocean": {"pl": "Środkowy Ocean Indyjski"},
    "Arctic Ocean": {"pl": "Ocean Arktyczny"},
}
for _name, _tr in _REF_NAMES.items():
    _CITY_NAMES.setdefault(slugify(_name), {}).update(_tr)


def _local_name(slug: str, lang: str, default: str) -> str:
    """The city's name in ``lang`` if we have an exonym, else the default name."""
    return _CITY_NAMES.get(slug, {}).get(lang, default)


def place_names_for(lang: str) -> dict:
    """One language's slice of the exonym table as ``{"l": ..., "f": ...}``:
    ``l`` is what ``lang`` itself calls each city, ``f`` the English exonym for
    the cities ``lang`` has no name for.

    The full table is ~1 MB (309 KB gzipped): 32 languages have exonyms in it and
    a visitor reads one of them, but the landing page fetched all 32 before it
    could draw the ranking. A slice is ~5-40 KB. (One slice per unique BASE
    language code - zh-TW shares zh's - and the languages with no exonyms of their
    own get an English-fallback-only file.)

    The two maps stay SEPARATE because the browser's three readers do not share
    one fallback chain: the ranking shows the language's own name or its own
    default (which carries our "(CC)" disambiguators), while the "did you know"
    facts and the hero's climate-analog lines fall back to English first. Baking
    ``l or f`` into one map would silently give the ranking the English fallback
    it never had (charts.js: nameOwn vs nameAny)."""
    own, fallback = {}, {}
    for slug, names in _CITY_NAMES.items():
        if lang in names:
            own[slug] = names[lang]
        elif "en" in names:
            fallback[slug] = names["en"]
    return {"l": own, "f": fallback}


def _seo_head(lang, languages, path, title, desc, jsonld=None):
    """SEO / social <head> block shared by every page: meta description,
    canonical, hreflang alternates for all languages (+ x-default), richer
    Open Graph / Twitter, and optional JSON-LD. ``path`` is the language-less
    file (e.g. "index.html" or "warszawa.html"); languages[0] is the site
    default (drives x-default)."""
    canonical = f"{SITE_BASE}/{lang}/{path}"
    d = _esc(desc or "", quote=True)
    t = _esc(title or "", quote=True)
    parts = [
        f'<meta name="description" content="{d}">',
        f'<link rel="canonical" href="{canonical}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:site_name" content="{_SITE_NAME}">',
        f'<meta property="og:locale" content="{lang}">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:description" content="{d}">',
    ]
    for lg in languages:
        parts.append(f'<link rel="alternate" hreflang="{lg}" '
                     f'href="{SITE_BASE}/{lg}/{path}">')
    parts.append(f'<link rel="alternate" hreflang="x-default" '
                 f'href="{SITE_BASE}/{languages[0]}/{path}">')
    if jsonld:
        parts.append('<script type="application/ld+json">'
                     + json.dumps(jsonld, ensure_ascii=False, separators=(",", ":"))
                     + '</script>')
    return "\n".join(parts)

# Latitudinal climate-zone bands (north→south) for the map overlay + legend -
# the geographic boundaries behind globaldata.zone_of (Equal Earth draws
# parallels as straight horizontal lines, so each is a simple horizontal band).
_ZONE_BAND_DEFS = [
    ("n-boreal", 90, 55),
    ("n-temperate", 55, 35),
    ("n-subtropical", 35, 23.5),
    ("tropical", 23.5, -23.5),
    ("s-subtropical", -23.5, -35),
    ("s-temperate", -35, -90),
]
from i18n import LANG_NAMES
from plots import BASELINE, _signed, annual_means, summary_stats

# Small inline globe (the site uses images/SVG, never flag/emoji glyphs, since
# emoji don't render on Windows) - marks the link to the world/regional page.
_GLOBE_SVG = (
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
    'stroke="currentColor" stroke-width="1.8" aria-hidden="true" '
    'style="vertical-align:-2px;margin-inline-end:.35rem"><circle cx="12" cy="12" '
    'r="9"/><path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18"/>'
    '</svg>')


# Folded-map icon for the "back to map" links (replaces a 🗺 emoji that renders
# as tofu on many devices), and a larger version for the floating home button.
_MAP_ICON = (
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" '
    'aria-hidden="true" style="vertical-align:-2px;margin-inline-end:.35rem">'
    '<path d="M9 3 3 5.4v15.6l6-2.4 6 2.4 6-2.4V3l-6 2.4z"/>'
    '<path d="M9 3v15.6M15 5.4V21"/></svg>')
_MAP_ICON_FAB = (
    '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M9 3 3 5.4v15.6l6-2.4 6 2.4 6-2.4V3l-6 2.4z"/>'
    '<path d="M9 3v15.6M15 5.4V21"/></svg>')


def _map_label(tr: dict) -> str:
    """The 'back to map' text with any leading map emoji stripped (we render an
    SVG icon instead)."""
    return (tr.get("back_to_map", "Map")
            .replace("🗺️", "").replace("🗺", "").strip())


def _topbar(home_href: str, lang_nav: str,
            nav_html: str = "", search_html: str = "") -> str:
    """The shared site top bar, identical on the landing page and every city page:
    a globe/brand home link, page-specific nav, an optional search slot, and the
    language picker. The appearance button (appearance.js) and the warming badge
    (charts.js, landing only) inject themselves into .topbar-in."""
    return (
        '<div class="topbar" id="topbar"><div class="topbar-in">'
        f'<a class="tb-home" href="{home_href}">{_GLOBE_SVG}'
        '<span class="tb-brand">temperatury</span></a>'
        f'<div class="tb-nav">{nav_html}</div>'
        f'<div class="tb-search">{search_html}</div>'
        f'<nav class="langs">{lang_nav}</nav>'
        '</div></div>'
    )


_PAGE = Template(
    """<!DOCTYPE html>
<html lang="${html_lang}" dir="${html_dir}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${title}">
<meta property="og:url" content="${og_url}">
<meta property="og:image" content="${og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
${seo_head}
<script>(function(){try{var d=document.documentElement,p={};try{p=JSON.parse(localStorage.getItem("temperatury:appearance"))||{}}catch(e){}var os=window.matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";d.setAttribute("data-dir",p.dir||"objective");d.setAttribute("data-theme",p.theme||os);d.setAttribute("data-density",p.density||"comfortable");d.setAttribute("data-hero",p.hero||"tint");d.setAttribute("data-unit",p.unit||(function(){try{var L=navigator.languages||[navigator.language||""];for(var i=0;i<L.length;i++){var m=/-([A-Za-z]{2})(?:$$|-)/.exec(L[i]||"");if(m)return["US","PR","GU","VI","AS","MP","BS","BZ","KY","PW","FM","MH"].indexOf(m[1].toUpperCase())>=0?"F":"C";}}catch(e){}return"C";})());if(p.accent)d.setAttribute("data-accent",p.accent);if(p.font)d.setAttribute("data-font",p.font);if(/[?&]embed=1/.test(location.search))d.setAttribute("data-embed","1");}catch(e){}})();</script>
<script>window.__tpref = ${tpref_i18n};window.__units = ${units_on};</script>
<link rel="stylesheet" href="../page.css">
<script defer src="../appearance.js"></script>
</head>
<body>
${chart_js}
${topbar}
<header class="region-hero" data-name="${place_name}" data-gridnote="${grid_note}"
        data-cc="${hero_cc}" style="--rh-stripes:${hero_bg}">
  <div class="rh-scrim"></div>
  <div class="rh-inner">
    <p class="rh-eyebrow">${hero_range}</p>
    <div class="rh-place">
      <svg class="rh-pin" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/>
      </svg>
      <h1 id="pagehead">${place_head}</h1>
    </div>
    <div class="rh-figure"><span>${trend}</span><span class="rh-unit"${trend_unit_attr}>${trend_unit}</span></div>
    <p class="rh-meta"${hero_meta_attr}>${hero_meta}</p>
    ${hero_pct}
    ${hero_spark_block}
    <div class="rh-chips">
      <div class="rh-chip"><span${card_mean_attr}>${card_mean}</span><b>${mean}</b></div>
      <div class="rh-chip"><span${card_warmest_attr}>${card_warmest}</span><b>${warmest_year}</b></div>
      <div class="rh-chip"><span${card_coldest_attr}>${card_coldest}</span><b>${coldest_year}</b></div>
    </div>
    ${analog_html}
  </div>
</header>
<main>
  ${curyear}

  <div class="share-row">
    <button type="button" class="share-btn" id="share-btn" data-copied="${copied_label}">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none"
           stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle>
        <circle cx="18" cy="19" r="3"></circle>
        <line x1="8.7" y1="10.6" x2="15.3" y2="6.6"></line>
        <line x1="8.7" y1="13.4" x2="15.3" y2="17.4"></line>
      </svg>
      <span class="share-label"${share_label_attr}>${share_label}</span>
    </button>
    <a class="news-btn" href="${news_url}"${news_data} target="_blank" rel="noopener noreferrer">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none"
           stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 5h13v14H4z"></path><path d="M17 8h3v9a2 2 0 0 1-2 2h-1"></path>
        <line x1="7" y1="9" x2="14" y2="9"></line><line x1="7" y1="13" x2="14" y2="13"></line>
      </svg>
      <span${news_label_attr}>${news_label}</span>
    </a>
  </div>

  <details class="guide">
    <summary${guide_title_attr}>${guide_title}</summary>
    <ul${guide_body_attr}>${guide_body}</ul>
  </details>

  <section class="charts story">
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-yearly-trend"></canvas></div>
      <figcaption>${cap_yearly}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-anomalies"></canvas></div>
      <figcaption>${cap_anomalies}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-warming-stripes"></canvas></div>
      <figcaption>${cap_stripes}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-monthly-heatmap"></canvas></div>
      <figcaption>${cap_heatmap}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-monthly-anomaly"></canvas></div>
      <figcaption>${cap_anom_heatmap}</figcaption>
    </figure>
    ${range_widget}
    ${records_widget}
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-threshold-days"></canvas></div>
      <figcaption>${cap_threshold}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-growing-season"></canvas></div>
      <figcaption>${cap_season}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-seasonal-shift"></canvas></div>
      <figcaption>${cap_seasonshift}</figcaption>
    </figure>
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-volatility"></canvas></div>
      <figcaption>${cap_volatility}</figcaption>
    </figure>
    ${dtr_figure}
    ${precip_figure}
  </section>

  <h2 class="section"${health_heading_attr}>${health_heading}</h2>
  <p class="section-sub"${health_sub_attr}>${health_sub}</p>
  <section class="charts story">
    <figure>
      <div class="chart-wrap"><canvas id="c-${slug}-degree-days"></canvas></div>
      <figcaption>${cap_degreedays}</figcaption>
    </figure>
    ${heatwave_figure}
    ${tropic_figure}
    ${coldspell_figure}
    ${heavyrain_figure}
    ${heatindex_figure}
  </section>

  ${deep_history}
</main>
<footer>${footer_html} · <a href="../embed.html?mode=city&amp;city=${slug}">${widget_label_html}</a></footer>

<script>
  // Only what is truly city-specific stays inline: this page's chart-label map
  // and its slug. Everything shared across a language's 2000+ city pages lives
  // once in _page.js (bootstrap, share button, topbar behaviour, month names) -
  // the single biggest lever on total site size.
  window.__ci18n = ${chart_i18n};
  window.__slug = ${slug_js};
</script>
<script src="_page.js"></script>
${i18n_head}
</body>
</html>
"""
)

# Per-language shared city-page runtime (written once per language folder).
# Holds every script that used to be inlined into each city page but does not
# vary by city: localized month names / chart-error / fullscreen / reset-zoom
# labels, the chart+widget bootstrap (city slug read from window.__slug), the
# share button, and the mobile topbar auto-hide. The widget year <select>s are
# also filled here, from the fetched payload's own year list, instead of
# shipping ~90 <option> rows per widget in every page.
_PAGE_JS = Template(
    """// Shared city-page runtime (one copy per language; pages set window.__slug).
window.__cmonths = ${months_json};
window.__chartErr = ${chart_err_json};
window.__cfs = ${fs_label_json};
window.__crz = ${rz_label_json};
(function () {
  var slug = window.__slug;
  if (!slug) return;
  function fillYears(base, byYear) {
    // Rebuild what the server used to inline: every year of the payload,
    // ascending, latest preselected (buildRange/buildRecords read the value).
    var sel = document.getElementById(base + '-y');
    if (!sel || sel.options.length) return;
    var ys = Object.keys(byYear).sort(function (a, b) { return a - b; });
    ys.forEach(function (y, i) {
      var o = document.createElement('option');
      o.value = y;
      o.textContent = y;
      if (i === ys.length - 1) o.selected = true;
      sel.appendChild(o);
    });
  }
  function draw(C) {
    ${chart_compose}
    function paint(id) {
      if (window.renderChart) window.renderChart('c-' + slug + '-' + id, C[id]);
    }
    var ids = Object.keys(C).filter(function (id) { return id.charAt(0) !== '_'; });
    // Lazy-render: construct each Chart.js canvas only as it nears the viewport,
    // not all ~19 at once. A synchronous burst of that many canvases on load
    // spikes memory/CPU - and when this page is the region-embed iframe on the
    // landing screen it lands on top of the main page's own charts, enough to
    // crash a memory-constrained browser tab. Above-the-fold figures still draw
    // immediately; the rest draw on scroll (in the iframe's own viewport).
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          io.unobserve(e.target);
          paint(e.target.getAttribute('data-cid'));
        });
      }, { rootMargin: '300px 0px' });
      ids.forEach(function (id) {
        var cv = document.getElementById('c-' + slug + '-' + id);
        if (cv) { cv.setAttribute('data-cid', id); io.observe(cv); }
        else paint(id);
      });
    } else {
      ids.forEach(paint);
    }
    var mo = window.__cmonths;
    if (C._range && window.buildRange && document.getElementById('rng-' + slug)) {
      fillYears('rng-' + slug, C._range.years);
      window.buildRange('rng-' + slug, C._range, mo);
    }
    if (C._records && window.buildRecords && document.getElementById('rec-' + slug)) {
      fillYears('rec-' + slug, C._records.years);
      window.buildRecords('rec-' + slug, C._records, mo);
    }
  }
  fetch('../charts/' + encodeURIComponent(slug) + '.json')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(window.__expandYears)
    .then(draw)
    .catch(function (e) {
      if (window.chartsUnavailable) window.chartsUnavailable(e);
      else if (window.console) console.error('charts load', e);
    });
})();
// Deep links to every chart: a small anchor appended to each caption. Click
// sets the URL (preserving any #as= alias relabel) and copies it, so one
// specific chart - "hot & freezing days in Skomielna Biala" - is shareable.
(function () {
  var slug = window.__slug;
  if (!slug) return;
  var LABEL = ${sec_label_json};
  var pfx = 'c-' + slug + '-';
  function secOf(cv) {
    var id = (cv && cv.id) || '';
    if (id.indexOf(pfx) === 0) return id.slice(pfx.length);
    if (id === 'rng-' + slug) return 'monthly-range';
    if (id === 'rec-' + slug) return 'monthly-records';
    return null;
  }
  function asName() {   // keep the alias part of the hash, still URL-encoded
    var m = /(?:^|[#&])as=([^&]*)/.exec(location.hash || '');
    return m ? m[1] : '';
  }
  function hashFor(sec) {
    var as = asName();
    return as ? '#as=' + as + '&sec=' + sec : '#sec-' + sec;
  }
  Array.prototype.forEach.call(document.getElementsByTagName('figure'),
                               function (fig) {
    var sec = secOf(fig.querySelector('canvas'));
    var cap = fig.querySelector('figcaption');
    if (!sec || !cap) return;
    fig.id = 'sec-' + sec;
    var a = document.createElement('a');
    a.className = 'sec-link';
    a.href = hashFor(sec);
    a.title = LABEL;
    a.setAttribute('aria-label', LABEL);
    a.textContent = '#';
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var h = hashFor(sec);
      if (history.replaceState) history.replaceState(null, '', h);
      var ok = function () {
        a.classList.add('ok');
        setTimeout(function () { a.classList.remove('ok'); }, 1500);
      };
      if (navigator.clipboard)
        navigator.clipboard.writeText(location.href.split('#')[0] + h)
                 .then(ok, ok);
      else ok();
      fig.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    cap.appendChild(document.createTextNode(' '));
    cap.appendChild(a);
  });
  // Arriving via a shared link (either #sec-name or #as=X&sec=name): scroll
  // once the ids exist. The figure boxes already have their final height from
  // CSS, so this works before the async chart data lands.
  var m = /(?:^|[#&])sec[=-]([a-z0-9-]+)/.exec(location.hash || '');
  if (m) {
    var el = document.getElementById('sec-' + m[1]);
    if (el) setTimeout(function () {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 250);
  }
})();
// One-tap share: native share sheet on mobile (with the city's OG card), else
// copy the link and flash a confirmation.
(function () {
  var b = document.getElementById('share-btn');
  if (!b) return;
  var url = location.href.split('#')[0];
  var label = b.querySelector('.share-label');
  b.addEventListener('click', function () {
    if (navigator.share) {
      navigator.share({ title: document.title, text: document.title, url: url })
        .catch(function () {});
      return;
    }
    // Read label + copied text at click time so a client language switch is
    // reflected (window.__i18n wins over the baked data-copied fallback).
    var orig = label ? label.textContent : '';
    var i18n = window.__i18n || {};
    var flash = function () {
      b.classList.add('copied');
      if (label) label.textContent = i18n.share_copied || b.getAttribute('data-copied') || 'Copied';
      setTimeout(function () {
        b.classList.remove('copied');
        if (label) label.textContent = orig;
      }, 1800);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(flash, function () { window.prompt('', url); });
    } else {
      window.prompt('', url);
    }
  });
})();
// Auto-hide the sticky top bar on scroll (mobile only), same as the main page.
(function () {
  var bar = document.getElementById('topbar');
  if (!bar) return;
  var mq = window.matchMedia('(max-width: 720px)');
  var lastY = window.pageYOffset || 0, ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var y = window.pageYOffset || 0;
      if (mq.matches) {
        if (y > lastY + 4 && y > 80) bar.classList.add('hide');
        else if (y < lastY - 4) bar.classList.remove('hide');
      } else { bar.classList.remove('hide'); }
      lastY = y;
      ticking = false;
    });
  }, { passive: true });
})();
"""
)


def write_page_js(output_dir: Path, tr: dict, lang: str) -> Path:
    """Write the shared per-language city-page runtime (``_page.js``)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "_page.js"
    path.write_text(_PAGE_JS.substitute(
        months_json=json.dumps(tr["months"], ensure_ascii=False),
        chart_err_json=json.dumps(_CHART_ERR.get(lang, _CHART_ERR["en"]),
                                  ensure_ascii=False),
        fs_label_json=json.dumps(_FS_LABEL.get(lang, _FS_LABEL["en"]),
                                 ensure_ascii=False),
        rz_label_json=json.dumps(_RZ_LABEL.get(lang, _RZ_LABEL["en"]),
                                 ensure_ascii=False),
        # Anchor-link tooltip: reuse the translated "Share" label.
        sec_label_json=json.dumps(tr.get("share", "Share"), ensure_ascii=False),
        # Client-i18n: rebuild the chart-label map from the shipped recipes +
        # the active dictionary before drawing (empty on a server-i18n build, so
        # the baked window.__ci18n is used unchanged).
        chart_compose=("if (C._labels && window.__composeChartI18n) "
                       "window.__composeChartI18n(C._labels);"
                       if _CLIENT_I18N else ""),
    ), encoding="utf-8")
    return path

_REDIRECT = Template(
    """<!DOCTYPE html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=${target}">
<link rel="canonical" href="${target}">
<title>temperatury</title>
</head>
<body><a href="${target}">temperatury →</a></body>
</html>
"""
)

# Root redirect that sends the visitor to the best language folder. Priority:
# their saved choice → their location (browser timezone → country → language) →
# their browser language preferences → the site default. A plain meta-refresh to
# the default is the no-JS / crawler fallback (the script runs first and wins).
_LANG_REDIRECT = Template(
    """<!DOCTYPE html>
<html lang="${default}">
<head>
<meta charset="utf-8">
<title>temperatury</title>
<script>
(function () {
  var S = ${supported}, DEF = "${default}", TZ = ${tzcc}, CL = ${cclang};
  function ok(l) { return (l && S.indexOf(l) >= 0) ? l : null; }
  function pick() {
    try { var s = localStorage.getItem("temperatury.lang"); if (ok(s)) return s; } catch (e) {}
    try { var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      var l = ok(CL[TZ[tz]]); if (l) return l; } catch (e) {}
    var L = navigator.languages || [navigator.language || ""];
    for (var i = 0; i < L.length; i++) {
      var m = ok((L[i] || "").slice(0, 2).toLowerCase()); if (m) return m;
    }
    return DEF;
  }
  location.replace(pick() + "/index.html");
})();
</script>
<meta http-equiv="refresh" content="0; url=${default}/index.html">
<link rel="canonical" href="${default}/index.html">
</head>
<body><a href="${default}/index.html">temperatury →</a></body>
</html>
"""
)


def _picker_data(city_locs: list[Location], tr: dict, url_of=None) -> list[list[str]]:
    """The searchable city list: [name, url, localized-continent] per city.

    The secondary label is the localized continent, to tell apart same-named
    places when searching. Sorted case-insensitively by name. ``url_of(loc)``
    resolves each city's link (defaults to ``<slug>.html`` in the same folder);
    client-i18n passes a resolver that points cross-language cities at an
    existing shell.
    """
    rnames = (tr or {}).get("regions", {})
    items = sorted(city_locs, key=lambda loc: loc.name.casefold())
    return [[loc.name,
             url_of(loc) if url_of else f"{loc.slug}.html",
             rnames.get(loc.region, loc.region)]
            for loc in items]


def write_cities_js(path: Path, city_locs: list[Location], tr: dict,
                    url_of=None) -> None:
    """Write the shared per-language city list read by the topbar search.

    Emits ``window.__cpData={...}`` to ``_cities.js`` in ``path``'s directory.
    Every city page in a language references this one file (browser-cached),
    instead of inlining the ~35 KB list into all of them. Regenerated each build
    so the search stays current even on incrementally-cached pages. ``url_of``
    resolves each city's link (see :func:`_picker_data`).
    """
    payload = json.dumps({"c": _picker_data(city_locs, tr, url_of)},
                         ensure_ascii=False)
    path.write_text("window.__cpData=" + payload + ";\n", encoding="utf-8")


def _city_picker(tr: dict, lang: str) -> str:
    """A single searchable combobox over every city.

    A type-to-filter search over the full city list: filtered client-side
    (accent-insensitive), navigable by keyboard or click. The list itself is not
    inlined here - it comes from the shared, browser-cached ``_cities.js``
    (``window.__cpData``, written once per build by ``write_cities_js``), so this
    markup is tiny and identical on every page. ``lang`` is accepted for
    call-site symmetry with the other pieces.
    """
    placeholder = tr["choose_city"]
    # Client-i18n: re-localize both the placeholder and the aria-label on a switch
    # (one key, two attributes); "" when the flag is off.
    pick_attr = (' data-i18n="choose_city" data-i18n-attr="placeholder aria-label"'
                 if _CLIENT_I18N else "")
    html = (
        '<div class="citypick"><div class="cp-combo">'
        f'<input type="search" id="cp-search" class="cp-input" role="combobox" '
        f'autocomplete="off" aria-autocomplete="list" aria-expanded="false" '
        f'aria-controls="cp-results" placeholder="{placeholder}" '
        f'aria-label="{placeholder}"{pick_attr}>'
        '<ul id="cp-results" class="cp-results" role="listbox" hidden></ul>'
        '</div></div>'
    )
    # The list data ships in the shared, browser-cached _cities.js
    # (window.__cpData); the search behaviour (type-to-filter, keyboard nav) is
    # in the shared charts.js (initCityPicker), so nothing is inlined per page.
    return html + '<script src="_cities.js"></script>'


def _city_chooser(current: Location, nav_locations: list[Location], tr: dict,
                  lang: str) -> str:
    """A 'back to map' link plus the searchable city picker."""
    picker = _city_picker(tr, lang)
    return f'<a href="index.html">{_MAP_ICON}{_map_label(tr)}</a>{picker}'


# Localised fallback shown (with a ⚠ icon, in charts.js) when a chart's data or
# render fails - a degraded state, so it lives here with the other per-language
# presentation strings rather than in the main i18n tables.
_CHART_ERR = {
    "en": "chart unavailable", "pl": "wykres niedostępny",
    "de": "Diagramm nicht verfügbar", "fr": "graphique indisponible",
    "es": "gráfico no disponible", "uk": "діаграма недоступна",
    "ru": "график недоступен", "it": "grafico non disponibile",
    "pt": "gráfico indisponível", "nl": "grafiek niet beschikbaar",
    "tr": "grafik kullanılamıyor", "id": "bagan tidak tersedia",
    "vi": "biểu đồ không khả dụng", "zh": "图表不可用",
    "ja": "グラフを表示できません", "ko": "차트를 사용할 수 없음",
    "hi": "चार्ट अनुपलब्ध", "bn": "চার্ট অনুপলব্ধ",
    "ar": "الرسم البياني غير متوفر", "fa": "نمودار در دسترس نیست",
    "ur": "چارٹ دستیاب نہیں",
}

# "Fullscreen" - accessible label/tooltip for the per-chart expand button
# (charts.js injects the button and reads this via window.__cfs).
_FS_LABEL = {
    "en": "Fullscreen", "pl": "Pełny ekran", "de": "Vollbild",
    "fr": "Plein écran", "es": "Pantalla completa", "uk": "На весь екран",
    "ru": "Полный экран", "it": "Schermo intero", "pt": "Ecrã inteiro",
    "nl": "Volledig scherm", "tr": "Tam ekran", "id": "Layar penuh",
    "vi": "Toàn màn hình", "zh": "全屏", "ja": "全画面表示", "ko": "전체 화면",
    "hi": "पूर्ण स्क्रीन", "bn": "পূর্ণ স্ক্রিন", "ar": "ملء الشاشة",
    "fa": "تمام‌صفحه", "ur": "پوری اسکرین",
}

# "Reset zoom" - label/tooltip for the per-chart zoom-reset button, which appears
# only while a chart is zoomed or panned (charts.js reads this via window.__crz).
_RZ_LABEL = {
    "en": "Reset zoom", "pl": "Resetuj powiększenie", "de": "Zoom zurücksetzen",
    "fr": "Réinitialiser le zoom", "es": "Restablecer zoom",
    "uk": "Скинути масштаб", "ru": "Сбросить масштаб", "it": "Reimposta zoom",
    "pt": "Repor zoom", "nl": "Zoom herstellen", "tr": "Yakınlaştırmayı sıfırla",
    "id": "Atur ulang zum", "vi": "Đặt lại thu phóng", "zh": "重置缩放",
    "ja": "ズームをリセット", "ko": "확대/축소 초기화", "hi": "ज़ूम रीसेट करें",
    "bn": "জুম রিসেট করুন", "ar": "إعادة ضبط التكبير",
    "fa": "بازنشانی بزرگ‌نمایی", "ur": "زوم ری سیٹ کریں",
}


def _tpref_i18n(tr: dict) -> str:
    """Client-side UI strings baked into every page as ``window.__tpref``.

    Covers the appearance panel (assets/appearance.js) and the global warming
    badge (assets/charts.js), neither of which can read the server-side
    dictionary. Every string is looked up with an inline English default so
    tools/gen_mapui.py can AST-extract it as the single source of truth and
    machine-translate it into i18n_data/_mapui.json for every language.
    """
    return json.dumps({
        # appearance panel
        "pref_title": tr.get("pref_title", "Appearance"),
        "pref_note": tr.get(
            "pref_note",
            "Choose how the site looks. Your choice is saved on this device."),
        "pref_close": tr.get("pref_close", "Close"),
        "pref_theme": tr.get("pref_theme", "Theme"),
        "pref_light": tr.get("pref_light", "Light"),
        "pref_dark": tr.get("pref_dark", "Dark"),
        "pref_style": tr.get("pref_style", "Style"),
        "pref_style_objective": tr.get("pref_style_objective", "Objective"),
        "pref_style_editorial": tr.get("pref_style_editorial", "Editorial"),
        "pref_style_product": tr.get("pref_style_product", "Product"),
        "pref_style_atlas": tr.get("pref_style_atlas", "Atlas"),
        "pref_accent": tr.get("pref_accent", "Accent"),
        "pref_headline": tr.get("pref_headline", "Headline font"),
        "pref_sans": tr.get("pref_sans", "Sans-serif"),
        "pref_serif": tr.get("pref_serif", "Serif"),
        "pref_density": tr.get("pref_density", "Density"),
        "pref_comfortable": tr.get("pref_comfortable", "Comfortable"),
        "pref_compact": tr.get("pref_compact", "Compact"),
        "pref_header": tr.get("pref_header", "Page header"),
        "pref_plain": tr.get("pref_plain", "Plain"),
        "pref_tint": tr.get("pref_tint", "Tint"),
        "pref_unit": tr.get("pref_unit", "Temperature unit"),
        "pref_unit_c": tr.get("pref_unit_c", "Celsius"),
        "pref_unit_f": tr.get("pref_unit_f", "Fahrenheit"),
        "pref_acc_cobalt": tr.get("pref_acc_cobalt", "Cobalt"),
        "pref_acc_red": tr.get("pref_acc_red", "Red"),
        "pref_acc_teal": tr.get("pref_acc_teal", "Teal"),
        "pref_acc_forest": tr.get("pref_acc_forest", "Forest"),
        "pref_acc_amber": tr.get("pref_acc_amber", "Amber"),
        "pref_acc_slate": tr.get("pref_acc_slate", "Slate"),
        # global warming badge in the topbar
        "hb_world": tr.get("hb_world", "World cities"),
        "hb_since": tr.get("hb_since", "since 1940"),
        "hb_title": tr.get(
            "hb_title",
            "Average warming of the world's major cities since 1940, "
            "equal-weighted, computed from this site's data"),
    }, ensure_ascii=False)


# "Language" - accessible label for the language <select> picker.
_LANG_LABEL = {
    "en": "Language", "pl": "Język", "de": "Sprache", "fr": "Langue",
    "es": "Idioma", "uk": "Мова", "ru": "Язык", "it": "Lingua",
    "pt": "Idioma", "nl": "Taal", "tr": "Dil", "id": "Bahasa",
    "vi": "Ngôn ngữ", "zh": "语言", "ja": "言語", "ko": "언어",
    "hi": "भाषा", "bn": "ভাষা", "ar": "اللغة", "fa": "زبان", "ur": "زبان",
}

# The country the per-country stat picker defaults to for each page language
# (ISO 3166-1 alpha-2). Multi-country languages point at their largest speaker
# base; the picker lets the reader choose any country regardless.
_LANG_CC = {
    "pl": "pl", "en": "us", "de": "de", "fr": "fr", "es": "es", "uk": "ua",
    "ru": "ru", "it": "it", "pt": "br", "nl": "nl", "tr": "tr", "id": "id",
    "vi": "vn", "zh": "cn", "ja": "jp", "ko": "kr", "hi": "in", "bn": "bd",
    "ar": "eg", "fa": "ir", "ur": "pk",
}


def _flag_emoji(cc: str) -> str:
    """ISO-2 country code -> flag emoji (regional-indicator letters). Renders as
    a flag on Apple/Android/Linux; degrades to the two letters on Windows."""
    cc = (cc or "").upper()
    if len(cc) != 2 or not cc.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in cc)

# "Embed widget" - footer link to the embeddable ranking widget builder.
_WIDGET_LABEL = {
    "en": "Embed widget", "pl": "Umieść widżet", "de": "Widget einbetten",
    "fr": "Intégrer le widget", "es": "Insertar widget", "uk": "Вставити віджет",
    "ru": "Встроить виджет", "it": "Incorpora widget", "pt": "Incorporar widget",
    "nl": "Widget insluiten", "tr": "Widget'ı yerleştir", "id": "Sematkan widget",
    "vi": "Nhúng widget", "zh": "嵌入小组件", "ja": "ウィジェットを埋め込む",
    "ko": "위젯 삽입", "hi": "विजेट एम्बेड करें", "bn": "উইজেট এম্বেড করুন",
    "ar": "أضف الأداة", "fa": "جاسازی ابزارک", "ur": "ویجٹ شامل کریں",
}

import extra_i18n  # noqa: E402
# NB: _CHART_ERR is deliberately NOT localized - it is the offline "chart
# unavailable" fallback that only appears when a chart can't be fetched (never on
# the live online site), and the parity harness treats it as language-neutral
# chrome. Localizing it broke client/server parity for no production benefit.
extra_i18n.fill_flat(_FS_LABEL, "fs_label")
extra_i18n.fill_flat(_RZ_LABEL, "rz_label")
extra_i18n.fill_flat(_LANG_LABEL, "lang_label")
extra_i18n.fill_flat(_WIDGET_LABEL, "widget_label")


def _lang_nav(current_lang: str, languages: list[str], slug: str,
              in_place: bool | None = None) -> str:
    """A compact language picker: a native <select> that jumps to the same page
    in each sibling-language folder. Far tighter than the old pill row and much
    easier on a phone (the tester flagged the row as wasted space).

    ``in_place`` switches via window.__setLang (client-i18n shells); navigation
    otherwise. Defaults to the build flag, but a page that is still rendered
    per-language and does NOT load the runtime (the landing map/dashboard) must
    pass ``in_place=False`` so its switcher navigates to a real sibling page."""
    if in_place is None:
        in_place = _CLIENT_I18N
    opts = []
    # Native name only, no flag: many languages span several countries (Punjabi,
    # Tamil, Swahili, Hausa...), so a single flag would misrepresent the others;
    # the native name is already an unambiguous, self-identifying label. In-place
    # switching uses the language CODE as the option value; navigation uses the
    # sibling-folder URL.
    for code in sorted(languages, key=lambda c: LANG_NAMES[c].casefold()):
        sel = " selected" if code == current_lang else ""
        value = code if in_place else f"../{code}/{slug}.html"
        opts.append(f'<option value="{value}"{sel}>{LANG_NAMES[code]}</option>')
    label = _LANG_LABEL.get(current_lang, _LANG_LABEL["en"])
    if in_place:
        onchange = "if(this.value)window.__setLang(this.value)"
    else:
        # Saving the chosen language lets the root redirect honour it next visit.
        onchange = ("if(this.value){try{localStorage.setItem("
                    "'temperatury.lang',this.value.split('/')[1])}catch(e){}"
                    "location.href=this.value}")
    return (f'<select class="lang-select" aria-label="{label}" '
            f'onchange="{onchange}">' + "".join(opts) + "</select>")


_EN_TR = i18n.get("en")  # canonical English strings, to detect untranslated keys


def _t(c: float, kind: str = "abs", dec: int = 1, signed: int = 0,
       unit: bool = False) -> str:
    """A server-rendered temperature the reader can flip to °F.

    The Celsius rendering is baked in, so a no-JS reader (and every crawler) sees
    a real number; alongside it ride the raw Celsius value and its conversion
    class, which ``charts.js`` uses to rewrite the span in place when the visitor
    picks °F. ``kind`` is abs / delta / ddays (see charts.js for what each means);
    ``signed`` 0 = plain, 1 = "+.Nf", 2 = the :func:`_signed` rule. ``unit``
    appends the unit token as its own span so it follows the same switch.

    Only for figures OUTSIDE a ``data-i18n`` element - a temperature inside a
    translated sentence goes through ``data-i18n-t`` instead (the runtime rewrites
    that element's whole text, which would eat a nested span).
    """
    if signed == 2:
        txt = _signed(c, dec)
    elif signed:
        txt = f"{c:+.{dec}f}"
    else:
        txt = f"{c:.{dec}f}"
    span = (f'<span class="tval" data-c="{c:.4f}" data-k="{kind}"'
            f' data-d="{dec}" data-s="{signed}">{txt}</span>')
    return (span + " " + _u("°C")) if unit else span


def _u(text: str) -> str:
    """A unit phrase that follows the °C/°F switch. charts.js swaps the °C inside
    it, so this takes the whole translated string ("°C / decade") as well as a
    bare token."""
    return f'<span class="tunit">{_esc(text)}</span>'


def _t_attr(spec: dict) -> str:
    """``data-i18n-t`` for temperature vars of a translated string: ``{var:
    [celsius, kind, decimals, signed]}``. Pairs with :func:`_i18n_attr`'s baked
    Celsius ``data-i18n-vars`` (the no-JS fallback)."""
    if not _CLIENT_I18N or not spec:
        return ""
    return " data-i18n-t='" + _esc(
        json.dumps(spec, ensure_ascii=False, separators=(",", ":")),
        quote=True) + "'"


def build_site(
    df,
    location: Location,
    output_dir: Path,
    nav_locations: list[Location],
    lang: str,
    languages: list[str],
    tr: dict,
    range_data: dict,
    records_data: dict | None = None,
    has_precip: bool = False,
    has_dtr: bool = False,
    has_appheat: bool = False,
    chart_i18n: dict | None = None,
    analog: dict | None = None,
    rank_pct: int | None = None,
    has_og_card: bool = False,
    og_card_ccs: frozenset | set = frozenset(),
    df_cur=None,
    season: tuple | None = None,
) -> Path:
    """Write ``<slug>.html`` (localised) into ``output_dir``; return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tr = captions.overlay(tr, lang)
    slug = location.slug
    disp = _local_name(slug, lang, location.name)   # localized display name
    # Under client-i18n the language switcher and per-page city-name map cover
    # EVERY site language (any is reachable in the browser), while ``languages``
    # (the pre-rendered SEO set) still drives the crawlable hreflang alternates.
    _switch_langs = list(i18n.LANGUAGES) if _CLIENT_I18N else languages
    stats = summary_stats(df)
    # Immersive "warming stripes" hero: the city's own annual anomalies (vs the
    # 1961-1990 baseline) baked as a CSS gradient behind the header, with its
    # headline warming figure over a scrim - the same language as the landing.
    _means = annual_means(df)
    _blo, _bhi = BASELINE
    _base = _means[(_means.index >= _blo) & (_means.index <= _bhi)]
    _baseline = _base.mean() if len(_base) else _means.mean()
    hero_bg = _stripe_gradient_css([float(v) for v in (_means - _baseline)])
    _span = max(1, stats["end"] - stats["start"])
    _dt = stats["trend_per_decade"] * _span / 10.0
    # Data-forward hero: the decade anomalies as a filled area chart (same idiom
    # as the map card), server-rendered as inline SVG so it needs no client JS.
    _decades = _decade_anomalies(_means, _baseline)
    hero_spark = _hero_spark_svg(_decades, tr.get("qv_chart_alt",
                                 "Decade-by-decade warming, filled area chart"))
    _dfirst = next((d0 for d0, v in zip(range(1940, 2030, 10), _decades)
                    if v is not None), 1940)
    _dlast = next((d0 for d0, v in zip(range(2020, 1930, -10), reversed(_decades))
                   if v is not None), 2020)
    hero_spark_block = (
        f'<div class="rh-spark-wrap">{hero_spark}'
        f'<div class="rh-spark-axis"><span>{_dfirst}</span>'
        f'<span>{_dlast}</span></div></div>'
    ) if hero_spark else ""
    hero_range = f"{stats['start']}-{stats['end']}"
    _dt_html = f"<b>{_t(_dt, 'delta', 1, 2, unit=True)}</b>"
    hero_meta = _hero_str(lang, "since").format(v=_dt_html)
    hero_meta_attr = _i18n_attr("hero_since", {"v": _dt_html}, html=True)
    # "Warming faster than N% of the world" - the city's place in the ranking,
    # reusing the landing hero's translated sentence. Only for ranked cities.
    hero_pct = ""
    if rank_pct is not None:
        _fa = _i18n_attr("hero_faster", {"pct": rank_pct})
        hero_pct = (f'<p class="rh-meta rh-pct"{_fa}>'
                    + _esc(_hero_str(lang, "faster").format(pct=rank_pct))
                    + '</p>')
    # Which season (month, in the tropics) warmed fastest - one more piece of
    # server-rendered prose the charts alone don't say out loud.
    if season:
        _skind, _skey, _sval = season
        if _skind == "month":
            _stmpl = tr.get("sum_month", "Fastest-warming month here: "
                                         "{month} ({v} °C per decade).")
            _months = tr.get("months") or []
            _slabel = _months[_skey - 1] if len(_months) >= 12 else str(_skey)
            # {month} resolves to the switched language's month name client-side.
            _sattr = _i18n_attr("sum_month",
                                {"month": f"@months.{_skey - 1}",
                                 "v": _signed(_sval, 2)}) + _t_attr(
                {"v": [round(_sval, 4), "delta", 2, 2]})
        else:
            _stmpl = tr.get("sum_season", "Fastest-warming season here: "
                                          "{season} ({v} °C per decade).")
            _slabel = tr.get(f"season_{_skey}", _skey)
            # {season} resolves to the switched language's season word.
            _sattr = _i18n_attr("sum_season",
                                {"season": f"@season_{_skey}",
                                 "v": _signed(_sval, 2)}) + _t_attr(
                {"v": [round(_sval, 4), "delta", 2, 2]})
        hero_pct += (f'<p class="rh-meta rh-pct"{_sattr}>'
                     + _esc(_stmpl.format(season=_slabel, month=_slabel,
                                          v=_signed(_sval, 2)))
                     + '</p>')
    place_head = _esc(disp)
    # Chart.js + the matrix (heatmap) and zoom/pan plugins, the range/records
    # widget helpers, and our shared per-archetype render layer (charts.js, a
    # root asset referenced from each per-language page).
    chart_js = (
        interactive.CHARTJS_INCLUDE
        + '<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-matrix@2.0.1/'
          'dist/chartjs-chart-matrix.min.js"></script>'
        + '<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.2.0/'
          'dist/chartjs-plugin-zoom.min.js"></script>'
        + '<script src="../charts.js"></script>'
    )
    range_widget = interactive.range_widget_html(
        slug, tr["range_title"].format(name=disp), tr["cap_range"],
        tr["year"], range_data, tr["months"],
        title_attr=_i18n_attr("range_title"), cap_attr=_i18n_attr("cap_range"),
        year_attr=_i18n_attr("year"))
    records_widget = (
        interactive.records_widget_html(
            slug, tr["record_title"].format(name=disp),
            tr["cap_records"], tr["year"], records_data, tr["months"],
            title_attr=_i18n_attr("record_title"),
            cap_attr=_i18n_attr("cap_records"), year_attr=_i18n_attr("year"))
        if records_data else ""
    )
    # Charts are shared/language-neutral, so the localised title lives in the
    # HTML caption (bold) above the description, and images come from ../charts.
    def _titled(title_key: str, cap_key: str, **fmt) -> str:
        title = tr[title_key].format(name=disp, **fmt)
        desc = tr[cap_key]
        if _CLIENT_I18N:
            # {name} is auto-provided by the runtime; any other fmt vars are
            # per-city, so bake them. The description wraps in a <span> so its
            # text node becomes keyable (text-only, so parity is unaffected).
            tattr = _i18n_attr(title_key, {k: v for k, v in fmt.items()} or None)
            return (f'<strong class="fig-title"{tattr}>{title}</strong>'
                    f'<br><span{_i18n_attr(cap_key)}>{desc}</span>')
        return f'<strong class="fig-title">{title}</strong><br>{desc}'

    def _fig(name: str, title_key: str, cap_key: str) -> str:
        return (
            f'<figure>\n      <div class="chart-wrap">'
            f'<canvas id="c-{slug}-{name}"></canvas></div>\n'
            f'      <figcaption>{_titled(title_key, cap_key)}</figcaption>\n    </figure>'
        )

    precip_figure = _fig("precipitation", "precip_title", "cap_precip") if has_precip else ""
    dtr_figure = _fig("diurnal-range", "dtr_title", "cap_dtr") if has_dtr else ""

    # Health-impact panels, each gated on the dataset it needs.
    heatwave_figure = _fig("heatwave", "heatwave_title", "cap_heatwave") if has_dtr else ""
    tropic_figure = _fig("tropical-nights", "tropic_title", "cap_tropic") if has_dtr else ""
    coldspell_figure = _fig("cold-spells", "coldspell_title", "cap_coldspell") if has_dtr else ""
    heavyrain_figure = _fig("heavy-rain", "heavyrain_title", "cap_heavyrain") if has_precip else ""
    heatindex_figure = _fig("heat-index", "heatindex_title", "cap_heatindex") if has_appheat else ""

    # Deep-history explainer (why the charts start in 1940); a city that is one
    # of the world's long-record places also gets a specific "applicable here" line.
    dh = deephist.overlay(tr, lang)
    _rec = deephist.record_for(slug)
    _rec_html = dh["deephist_record"].format(label=_rec[0], year=_rec[1]) if _rec else ""
    if _CLIENT_I18N:
        _body = f'<span{_i18n_attr("deephist_body", html=True)}>{dh["deephist_body"]}</span>'
        if _rec:
            _body += (f'<span{_i18n_attr("deephist_record", {"label": _rec[0], "year": _rec[1]}, html=True)}>'
                      f'{_rec_html}</span>')
        deep_history = (
            f'<details class="deephist"><summary{_i18n_attr("deephist_title")}>'
            f'{dh["deephist_title"]}</summary>'
            f'<div class="dh-body">{_body}</div></details>')
    else:
        deep_history = (
            f'<details class="deephist"><summary>{dh["deephist_title"]}</summary>'
            f'<div class="dh-body">{dh["deephist_body"]}{_rec_html}</div></details>'
        )

    # Climate analogs: "in 1940 this felt like X today" + "by 2050 it will feel
    # like Y today", two present-day cities that make the change concrete. Server
    # rendered (with localized analog names) so search engines index the text.
    # Each side is optional: a short-record or cooling city may have one or none.
    def _analog_line(side: str, key: str, default: str) -> tuple[str, str]:
        """Return (rendered line, data-i18n attr). {city} resolves to the
        switched-language city name via @name; {analog} (the analog city's name)
        is baked in the SEO language - usually canonical, so identical across
        languages except the few analog cities that have exonyms."""
        a = (analog or {}).get(side)
        if not a:
            return "", ""
        tmpl = tr.get(key, default)
        # Hide the analog rather than show an English fallback (which also scrambles
        # under RTL) when this language has no real translation for the sentence.
        if lang != "en" and tmpl == _EN_TR.get(key):
            return "", ""
        an = _local_name(a["s"], lang, a["n"])
        line = tmpl.format(city=disp, analog=an, d=a["d"])
        # {d} is a temperature DIFFERENCE, so °F scales it without the 32 offset.
        attr = (_i18n_attr(key, {"city": "@name", "analog": an, "d": a["d"]})
                + _t_attr({"d": [float(a["d"]), "delta", 1, 0]}))
        return line, attr

    _af_line, _af_attr = _analog_line(
        "future", "analog_line",
        "By 2050, {city} could feel more like {analog} does today, "
        "about +{d} °C warmer.")
    _ap_line, _ap_attr = _analog_line(
        "past", "analog_past",
        "In 1940, {city} felt more like {analog} does today, "
        "about {d} °C cooler.")
    analog_future_line = _af_line   # reused in the meta description below
    # 1940 then 2050
    _al = [(ln, at) for ln, at in ((_ap_line, _ap_attr), (_af_line, _af_attr)) if ln]
    analog_html = ""
    if _al:
        _rows = "".join(f'<p class="analog-line"{at}>{_esc(ln)}</p>' for ln, at in _al)
        analog_html = ('<div class="analog" id="analog">'
                       '<span class="analog-emoji" aria-hidden="true">🌡️</span>'
                       f'<div class="analog-lines">{_rows}</div></div>')

    # "This year so far": the partial current year against the same calendar
    # window (Jan 1 .. last cached day) of the city's own 1961-1990 baseline.
    # Rendered only where current-year data is cached and covers 30+ days, and
    # explicitly dated so the partial year cannot read as a full one.
    curyear_html = ""
    if df_cur is not None and len(df_cur):
        _cur_vals = df_cur["temperature_2m_mean"].dropna()
        if len(_cur_vals) >= 30:
            _last = _cur_vals.index.max()
            _bmask = ((df.index.year >= _blo) & (df.index.year <= _bhi)
                      & ((df.index.month < _last.month)
                         | ((df.index.month == _last.month)
                            & (df.index.day <= _last.day))))
            _bvals = df.loc[_bmask, "temperature_2m_mean"].dropna()
            if len(_bvals):
                _cm = float(_cur_vals.mean())
                _dv = _cm - float(_bvals.mean())
                _tmpl = tr.get(
                    "cur_so_far",
                    "{year} so far (to {day} {month}): {v} °C on average, "
                    "{d} °C vs the 1961-1990 mean for the same days of the year.")
                _mnames = tr.get("months") or []
                _mn = (_mnames[_last.month - 1] if len(_mnames) >= 12
                       else str(_last.month))
                # One sentence, two classes: {v} is an actual temperature,
                # {d} the anomaly against the same days of the baseline.
                _cy_attr = _i18n_attr("cur_so_far", {
                    "year": int(_last.year), "day": int(_last.day),
                    "month": f"@months.{_last.month - 1}",
                    "v": f"{_cm:.1f}", "d": _signed(_dv, 1)}) + _t_attr(
                    {"v": [round(_cm, 4), "abs", 1, 0],
                     "d": [round(_dv, 4), "delta", 1, 2]})
                curyear_html = (f'<p class="curyear"{_cy_attr}>' + _esc(_tmpl.format(
                    year=int(_last.year), day=int(_last.day), month=_mn,
                    v=f"{_cm:.1f}", d=_signed(_dv, 1))) + '</p>')

    _cc = countries.country_code(location)
    _title = tr["page_title"].format(name=disp)
    _subtitle = tr["subtitle"].format(
        start=stats["start"], end=stats["end"], days=f"{stats['days']:,}",
        wy=stats["warmest_year"], wv=stats["warmest_value"],
        cy=stats["coldest_year"], cv=stats["coldest_value"])
    # Fold the 2050 analog into the meta description too, for richer SEO snippets.
    _desc = f"{_title}. {_subtitle}"
    if analog_future_line:
        _desc = f"{_desc} {analog_future_line}"
    _desc = _desc[:300]
    _jsonld = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": _title, "description": _subtitle,
        "temporalCoverage": "1940/2025",
        "variableMeasured": "Daily mean near-surface air temperature",
        "spatialCoverage": {"@type": "Place", "name": disp,
                            "geo": {"@type": "GeoCoordinates",
                                    "latitude": round(location.latitude, 4),
                                    "longitude": round(location.longitude, 4)}},
        "creator": {"@type": "Organization", "name": _SITE_NAME},
        "isAccessibleForFree": True,
        "url": f"{SITE_BASE}/{lang}/{slug}.html"}
    html = _PAGE.substitute(
        html_lang=tr["html_lang"],
        title=_title,
        seo_head=_seo_head(lang, languages, f"{slug}.html", _title, _desc, _jsonld),
        # The most-populous cities get their OWN card (ogcards.CITY_CARDS); the
        # tail previews its country's card, and whatever has neither the world one.
        # Both sets come from ogcards via the render worker rather than being
        # re-derived, because "the country has a card" is NOT the same as "the city
        # has a country": a country needs a minimum number of cities to enter the
        # country ranking, so micro-states have no card and would 404 here.
        og_image=(f"{SITE_BASE}/og/city/{slug}.png" if (has_og_card and _cc)
                  else f"{SITE_BASE}/og/{_cc}.png" if _cc in og_card_ccs
                  else f"{SITE_BASE}/og/world.png"),
        og_url=f"{SITE_BASE}/{lang}/{slug}.html",
        share_label=tr.get("share", "Share"),
        copied_label=tr.get("share_copied", "Link copied"),
        analog_html=analog_html,
        curyear=curyear_html,
        # Live extreme-weather news search for this city - runs in the visitor's
        # browser (Google News), so results are always current and nothing is
        # stored. The localized "extreme weather" phrase is both the button label
        # and the query term, so the search reads naturally in the visitor's tongue.
        news_url=("https://news.google.com/search?q="
                  + quote(f'"{location.name}" '
                          + tr.get("extreme_weather", "extreme weather"))
                  + f"&hl={lang}"),
        # Client-i18n: the runtime rebuilds this href for the switched language
        # (localized phrase + hl) from the city name baked here; "" when flag off.
        news_data=(f' data-news="1" data-city="{_esc(location.name, quote=True)}"'
                   if _CLIENT_I18N else ""),
        news_label=tr.get("extreme_weather", "Extreme weather"),
        subtitle=_subtitle,
        # For an alias arrival (#as=<name>): the primary's own display name and a
        # localized "same grid cell as {city}" note, read by charts.js to relabel
        # the heading. ``_esc`` keeps quotes/brackets safe inside the attribute.
        place_name=_esc(disp, quote=True),
        grid_note=_esc(tr.get(
            "grid_alias_note",
            "The temperature record is computed per ~11 km climate-data grid "
            "cell. {alias} shares its cell with {city}, so both show the same "
            "1940-present history."),
            quote=True),
        html_dir=tr["dir"],
        # Client-i18n rebuilds this map in-browser from charts/<slug>.json's
        # recipes (so it follows a language switch), so the shell need not bake
        # it; server-i18n keeps the pre-composed map inline as before.
        chart_i18n=json.dumps({} if _CLIENT_I18N else (chart_i18n or {}),
                              ensure_ascii=False),
        months_json=json.dumps(tr["months"], ensure_ascii=False),
        chart_err_json=json.dumps(_CHART_ERR.get(lang, _CHART_ERR["en"]),
                                  ensure_ascii=False),
        fs_label_json=json.dumps(_FS_LABEL.get(lang, _FS_LABEL["en"]),
                                 ensure_ascii=False),
        rz_label_json=json.dumps(_RZ_LABEL.get(lang, _RZ_LABEL["en"]),
                                 ensure_ascii=False),
        tpref_i18n=_tpref_i18n(tr),
        units_on="1" if _CLIENT_I18N else "0",
        slug_js=json.dumps(slug),
        map_label=_map_label(tr),
        map_label_attr=_i18n_attr("map_label"),
        map_icon=_MAP_ICON,
        picker=_city_picker(tr, lang),
        lang_nav=_lang_nav(lang, _switch_langs, slug),
        topbar=_topbar("index.html", _lang_nav(lang, _switch_langs, slug),
                       search_html=_city_picker(tr, lang)),
        trend=_t(stats['trend_per_decade'], "delta", 2, 2),
        trend_unit=tr["per_decade_c"],
        trend_unit_attr=_i18n_attr("per_decade_c"),
        mean=_t(stats['mean'], "abs", 1, unit=True),
        warmest_year=stats["warmest_year"],
        coldest_year=stats["coldest_year"],
        # Immersive-stripes city hero.
        hero_bg=hero_bg,
        hero_cc=(_cc or "").lower(),
        hero_range=hero_range,
        hero_meta=hero_meta,
        hero_meta_attr=hero_meta_attr,
        hero_pct=hero_pct,
        hero_spark_block=hero_spark_block,
        i18n_head=_i18n_head(slug, lang, _switch_langs, location.name),
        # Static localized labels: keyed for the client runtime ("" when the
        # flag is off). {name} for figure titles is auto-provided client-side.
        card_mean_attr=_i18n_attr("card_mean"),
        card_warmest_attr=_i18n_attr("card_warmest"),
        card_coldest_attr=_i18n_attr("card_coldest"),
        share_label_attr=_i18n_attr("share"),
        news_label_attr=_i18n_attr("extreme_weather"),
        guide_title_attr=_i18n_attr("guide_title"),
        guide_body_attr=_i18n_attr("guide_body", html=True),
        health_heading_attr=_i18n_attr("health_heading"),
        health_sub_attr=_i18n_attr("health_sub"),
        place_head=place_head,
        card_mean=tr["card_mean"],
        card_warmest=tr["card_warmest"],
        card_coldest=tr["card_coldest"],
        cap_yearly=_titled("yearly_title", "cap_yearly"),
        cap_anomalies=_titled("anomaly_title", "cap_anomalies"),
        cap_heatmap=_titled("heatmap_title", "cap_heatmap"),
        cap_anom_heatmap=_titled("anom_heatmap_title", "cap_anom_heatmap",
                                 base=f"{BASELINE[0]}-{BASELINE[1]}"),
        chart_js=chart_js,
        range_widget=range_widget,
        records_widget=records_widget,
        cap_threshold=_titled("threshold_title", "cap_threshold"),
        cap_volatility=_titled("volatility_title", "cap_volatility"),
        cap_stripes=_titled("stripes_title", "cap_stripes"),
        cap_season=_titled("season_title", "cap_season"),
        cap_seasonshift=_titled("seasonshift_title", "cap_seasonshift"),
        dtr_figure=dtr_figure,
        precip_figure=precip_figure,
        health_heading=tr["health_heading"],
        health_sub=tr["health_sub"],
        cap_degreedays=_titled("degreedays_title", "cap_degreedays"),
        heatwave_figure=heatwave_figure,
        tropic_figure=tropic_figure,
        coldspell_figure=coldspell_figure,
        heavyrain_figure=heavyrain_figure,
        heatindex_figure=heatindex_figure,
        guide_title=tr["guide_title"],
        guide_body=tr["guide_body"],
        deep_history=deep_history,
        footer_html=_i18n_span(
            tr["footer"].format(date=dt.date.today().isoformat()),
            "footer", {"date": dt.date.today().isoformat()}, html=True),
        widget_label_html=_i18n_span(
            _WIDGET_LABEL.get(lang, _WIDGET_LABEL["en"]), "widget_label"),
        slug=slug,
    )

    path = output_dir / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


_MAP_PAGE = Template(
    """<!DOCTYPE html>
<html lang="${html_lang}" dir="${html_dir}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${title}">
<meta property="og:url" content="${og_url}">
<meta property="og:image" content="https://yasoftwaredev.github.io/temperatury/og/world.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
${seo_head}
<!-- world map rendered as SVG with D3 (Equal Earth, an equal-area projection) -->
<script>(function(){try{var d=document.documentElement,p={};try{p=JSON.parse(localStorage.getItem("temperatury:appearance"))||{}}catch(e){}var os=window.matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";d.setAttribute("data-dir",p.dir||"objective");d.setAttribute("data-theme",p.theme||os);d.setAttribute("data-density",p.density||"comfortable");d.setAttribute("data-hero",p.hero||"tint");d.setAttribute("data-unit",p.unit||(function(){try{var L=navigator.languages||[navigator.language||""];for(var i=0;i<L.length;i++){var m=/-([A-Za-z]{2})(?:$$|-)/.exec(L[i]||"");if(m)return["US","PR","GU","VI","AS","MP","BS","BZ","KY","PW","FM","MH"].indexOf(m[1].toUpperCase())>=0?"F":"C";}}catch(e){}return"C";})());if(p.accent)d.setAttribute("data-accent",p.accent);if(p.font)d.setAttribute("data-font",p.font);}catch(e){}})();</script>
<script>window.__tpref = ${tpref_i18n};window.__units = ${units_on};</script>
<link rel="stylesheet" href="../landing.css">
<script defer src="../appearance.js"></script>
</head>
<body>
${chart_js}
${topbar}
<header>
  <h1>${heading}</h1>
  <p class="intro">${intro}</p>
</header>
<div class="searchbar" role="search">
  <section class="omni" id="omni" data-i18n='${omni_i18n}'>
    <div class="omni-combo">
      <input type="search" id="omni-input" class="omni-input" role="combobox"
             autocomplete="off" aria-autocomplete="list" aria-expanded="false"
             aria-controls="omni-results" placeholder="${omni_ph}" aria-label="${omni_ph}">
      <ul id="omni-results" class="omni-results" role="listbox" hidden></ul>
    </div>
    <p class="lookup-status" id="lookup-status" role="status"></p>
    <div class="lookup-result" id="lookup-result" hidden></div>
  </section>
  <script>window.__omniData=${omni_data};</script>
</div>
<!-- "Did you know" hook, on the main view above the tabs so it greets every
     visitor. Filled by charts.js from the loaded ranking (window.__gd) - every
     figure is real data, never fabricated; the city/country facts link into the
     matching tab. Hidden until at least one fact is available. -->
<div class="dyk-wrap"><div class="dyk" id="dyk" data-i18n='${dyk_i18n}' hidden>
  <p class="dyk-label">${dyk_label}</p>
  <p class="dyk-fact" id="dyk-fact" aria-live="polite"></p>
  <div class="dyk-dots" id="dyk-dots" role="group" aria-label="${dyk_label}"></div>
</div></div>
<main>
  <div class="tabs" id="landing-tabs">
    <div class="tabstrip" role="tablist" aria-label="${tabs_label}">${tabstrip}</div>
    <section class="tabpanel" role="tabpanel" id="tp-region" aria-labelledby="tab-region" tabindex="0">
  <!-- "Selected region": the chosen city's full page shown inline in a frame
       (the city page's ?embed=1 mode hides its own top bar). charts.js
       (initRegionEmbed) sets the frame from the remembered selection or the
       server default, then the visitor's geolocated nearest city; the top
       search routes a picked city here instead of navigating away. -->
  <div class="region-embed" id="region-embed" data-default="${hero_default_slug}">
    <p class="region-embed-hint" id="region-embed-hint">${region_hint}</p>
    <iframe class="region-frame" id="region-frame" title="${region_frame_title}"
            loading="lazy" referrerpolicy="no-referrer"></iframe>
  </div>
  <!-- Load the remembered/default city at once (charts.js is already loaded
       above), so the tab opens on a city without waiting for geolocation. -->
  <script>window.initRegionEmbed&&window.initRegionEmbed();</script>
    </section><!-- /tp-region -->
    <section class="tabpanel famous" role="tabpanel" id="tp-famous" aria-labelledby="tab-famous" tabindex="0" hidden>
      <!-- Famous-cities carousel: charts.js initCarousel cycles a set of iconic /
           most-populous cities through this single hero card via renderHeroEntry
           (the same card view as "Your region"). The card carries the shared
           localised template attributes so renderHeroEntry can read them. -->
      <div class="carousel" id="famous-carousel" data-autoplay="6000"
           aria-roledescription="carousel" aria-label="${tab_famous}">
        <div class="carousel-stage">
          <button type="button" class="carousel-nav carousel-prev" aria-label="${carousel_prev}">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
          </button>
          <div class="carousel-card" data-cta="${hero_cta}" data-since="${hero_since_tmpl}"
               data-faster="${hero_faster_tmpl}" data-chart-alt="${hero_chart_alt}"
               data-analog-past="${hero_analog_past}" data-analog-future="${hero_analog_future}"
               aria-roledescription="slide" aria-live="polite">
            <div class="rh-inner">
              <p class="rh-place"><span class="rh-name"></span></p>
              <div class="rh-figure"><span class="rh-trend"></span><span class="rh-unit tunit">${hero_unit}</span></div>
              <p class="rh-meta"></p>
              <div class="rh-spark-wrap"><div class="rh-spark"></div>
                <div class="rh-spark-axis" hidden><span class="rh-axis-lo"></span><span class="rh-axis-hi"></span></div>
              </div>
              <div class="rh-analog"></div>
              <p class="rh-cta"><a class="rh-link" href="#"><span class="rh-cta-label"></span> <span aria-hidden="true">&rarr;</span></a></p>
            </div>
          </div>
          <button type="button" class="carousel-nav carousel-next" aria-label="${carousel_next}">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>
        <div class="carousel-dots" id="carousel-dots" role="group" aria-label="${tab_famous}"></div>
      </div>
    </section><!-- /tp-famous -->
    <section class="tabpanel" role="tabpanel" id="tp-map" aria-labelledby="tab-map" tabindex="0" hidden>
  <div class="map-filter" role="group" aria-label="${map_filter_label}">
    <div id="map-region" class="zonebtns">${map_region_buttons}</div>
    <select id="map-country" class="lang-select" aria-label="${rank_country}">
      <option value="">${rank_country}</option>
    </select>
    <button type="button" id="grid-toggle" class="grid-toggle" aria-pressed="false">
      ${grid_toggle}</button>
    <div id="map-basemap" class="basemap-switch" role="group" aria-label="${basemap_label}">
      <button type="button" data-base="map" class="active" aria-pressed="true">${basemap_map}</button>
      <button type="button" data-base="terrain" aria-pressed="false">${basemap_terrain}</button>
      <button type="button" data-base="atlas" aria-pressed="false">${basemap_atlas}</button>
      <button type="button" data-base="sat" aria-pressed="false">${basemap_sat}</button>
    </div>
  </div>
  <div id="map"></div>
  <div class="zone-legend" id="zone-legend">${zone_legend}</div>
  <div class="grid-legend" id="grid-legend" hidden>
    <span class="gl"><i class="gl-green"></i>${grid_all}</span>
    <span class="gl"><i class="gl-amber"></i>${grid_some}</span>
    <span class="gl"><i class="gl-red"></i>${grid_none}</span>
  </div>
  ${coverage_note}
  ${kpi_band}
    </section><!-- /tp-map -->
    <section class="tabpanel" role="tabpanel" id="tp-ranking-cities" aria-labelledby="tab-ranking-cities" tabindex="0" hidden>
  <section class="ranking" id="ranking-cities">
    <p class="section-sub tunit">${rank_intro}</p>
    <p class="rank-legend">${rank_legend}</p>
    <div class="rank-window" role="group" aria-label="${rank_win_label}">
      <button type="button" class="rw-btn is-on" data-win="1940" aria-pressed="true">${rank_win_full}</button>
      <button type="button" class="rw-btn" data-win="1975" aria-pressed="false">${rank_win_recent}</button>
    </div>
    <p class="rank-window-note">${rank_win_note}</p>
    <div class="rank-controls">
      <input type="search" id="rank-search" class="rank-search"
             autocomplete="off" placeholder="${rank_search}" aria-label="${rank_search}">
      <select id="rank-region" class="lang-select" aria-label="${zone0}">${rank_regions}</select>
      <select id="rank-country-filter" class="lang-select" aria-label="${rank_country}">
        <option value="">${rank_country}</option>
      </select>
    </div>
    <div class="rank-table-wrap">
      <table class="rank-table">
        <thead><tr>
          <th class="rank-num rank-sort" data-key="rank" aria-sort="ascending">#</th>
          <th class="rank-city rank-sort" data-key="city">${rank_city}</th>
          <th class="rank-cty rank-sort" data-key="country">${rank_country}</th>
          <th class="rank-val rank-sort tunit" data-key="trend">${rank_trend}</th>
        </tr></thead>
        <tbody id="rank-body"></tbody>
      </table>
      <p class="rank-empty" id="rank-empty" hidden>${rank_empty}</p>
      <div class="rank-foot">
        <button type="button" class="rank-more" id="rank-more" hidden
                data-label="${rank_more}"></button>
        <p class="rank-count" id="rank-count"></p>
        <!-- tunit: the note names the unit ("the trend in °C per decade") with no
           figure in it, so the °C/°F swap can run over the whole sentence -->
        <p class="rank-note tunit" id="rank-note">${rank_note}</p>
      </div>
    </div>
  </section>
    </section><!-- /tp-ranking-cities -->
    <section class="tabpanel" role="tabpanel" id="tp-ranking-countries" aria-labelledby="tab-ranking-countries" tabindex="0" hidden>
  <section class="ranking" id="ranking-countries">
    <p class="section-sub tunit">${rank_intro_countries}</p>
    <p class="rank-legend">${rank_legend}</p>
    <div class="rank-window" role="group" aria-label="${rank_win_label}">
      <button type="button" class="rw-btn is-on" data-win="1940" aria-pressed="true">${rank_win_full}</button>
      <button type="button" class="rw-btn" data-win="1975" aria-pressed="false">${rank_win_recent}</button>
    </div>
    <p class="rank-window-note">${rank_win_note}</p>
    <div class="rank-controls">
      <input type="search" id="crank-search" class="rank-search"
             autocomplete="off" placeholder="${rank_search_countries}" aria-label="${rank_search_countries}">
    </div>
    <div class="rank-table-wrap">
      <table class="rank-table">
        <thead><tr>
          <th class="rank-num crank-sort" data-key="rank" aria-sort="ascending">#</th>
          <th class="rank-city crank-sort" data-key="city">${rank_country}</th>
          <th class="rank-cty crank-sort" data-key="country">${rank_cities}</th>
          <th class="rank-val crank-sort tunit" data-key="trend">${rank_trend}</th>
        </tr></thead>
        <tbody id="crank-body"></tbody>
      </table>
      <p class="rank-empty" id="crank-empty" hidden>${rank_empty}</p>
      <div class="rank-foot">
        <p class="rank-count" id="crank-count"></p>
      </div>
    </div>
  </section>
    </section><!-- /tp-ranking-countries -->
    <section class="tabpanel" role="tabpanel" id="tp-dashboard" aria-labelledby="tab-dashboard" tabindex="0" hidden>
  <section class="cstat" id="country-stat"
           data-tmpl="${cstat_tmpl}" data-tmpl-cool="${cstat_tmpl_cool}"
           data-default="${cstat_default}">
    <h2 class="dash-h2">${cstat_title}</h2>
    <div class="cstat-row">
      <select id="cstat-select" class="lang-select"
              aria-label="${rank_country}"></select>
    </div>
    <p class="cstat-line" id="cstat-line"></p>
  </section>

  <section id="global">
    <h2 class="dash-h2">${global_heading}</h2>
    <p class="section-sub">${global_intro}</p>
    <section class="charts hero">
      <figure>
        <div class="chart-wrap tall"><canvas id="g-comparison"></canvas></div>
        <figcaption><strong class="fig-title">${comparison_title}</strong><br>${comparison_cap}</figcaption>
      </figure>
    </section>
    <div class="zonebar">
      <span class="zonebar-label">${choose_label}:</span>
      <div id="g-region" class="zonebtns" role="group" aria-label="${choose_label}">${zone_buttons}</div>
    </div>
    <section class="charts">
      <figure>
        <div class="chart-wrap"><canvas id="g-anomaly"></canvas></div>
        <figcaption><strong class="fig-title">${anomaly_title}: <span class="zone-name">${zone0}</span></strong><br>${anomaly_cap}</figcaption>
      </figure>
      <figure>
        <div class="chart-wrap"><canvas id="g-stripes"></canvas></div>
        <figcaption><strong class="fig-title">${stripes_title}: <span class="zone-name">${zone0}</span></strong><br>${stripes_cap}</figcaption>
      </figure>
      <figure>
        <div class="chart-wrap"><canvas id="g-heatmap"></canvas></div>
        <figcaption><strong class="fig-title">${heatmap_title}: <span class="zone-name">${zone0}</span></strong><br>${heatmap_cap}</figcaption>
      </figure>
    </section>
  </section>
    </section><!-- /tp-dashboard -->
    <section class="tabpanel" role="tabpanel" id="tp-compare" aria-labelledby="tab-compare" tabindex="0" hidden>
  <section class="compare" id="compare">
    <h2 class="dash-h2">${cmp_title}</h2>
    <p class="section-sub">${cmp_hint}</p>
    <div class="cmp-controls">
      <input id="cmp-a" class="rank-search" list="cmp-cities" autocomplete="off"
             placeholder="${cmp_city_a}" aria-label="${cmp_city_a}">
      <input id="cmp-b" class="rank-search" list="cmp-cities" autocomplete="off"
             placeholder="${cmp_city_b}" aria-label="${cmp_city_b}">
      <datalist id="cmp-cities"></datalist>
    </div>
    <figure class="cmp-figure" id="cmp-figure" hidden>
      <div class="chart-wrap"><canvas id="c-cmp"></canvas></div>
      <figcaption id="cmp-stats"></figcaption>
    </figure>
  </section>
    </section><!-- /tp-compare -->
    <section class="tabpanel" role="tabpanel" id="tp-about" aria-labelledby="tab-about" tabindex="0" hidden>
      ${about_html}
    </section><!-- /tp-about -->
    <section class="tabpanel" role="tabpanel" id="tp-report" aria-labelledby="tab-report" tabindex="0" hidden>
  <!-- Feedback form: opens a prefilled GitHub new-issue page (charts.js
       initReportForm). A public static page cannot hold a token to post an issue
       directly, so submission is completed by the reporter on GitHub. -->
  <div class="report-wrap">
    <h2 class="dash-h2">${report_heading}</h2>
    <p class="section-sub">${report_intro}</p>
    <form class="report-form" id="report-form"
          data-repo="https://github.com/YASoftwareDev/temperatury/issues/new">
      <label class="report-lbl" for="report-title">${report_title_lbl}</label>
      <input type="text" id="report-title" class="report-input" maxlength="140"
             autocomplete="off" placeholder="${report_title_ph}">
      <label class="report-lbl" for="report-desc">${report_desc_lbl}</label>
      <textarea id="report-desc" class="report-textarea" rows="6" maxlength="4000"
                placeholder="${report_desc_ph}"></textarea>
      <button type="submit" class="report-submit">${report_submit}</button>
      <p class="report-note">${report_note}</p>
      <p class="report-thanks" id="report-thanks" role="status" hidden>${report_thanks}</p>
    </form>
  </div>
    </section><!-- /tp-report -->
  </div><!-- /.tabs -->
</main>
<footer>${footer} · <a href="../embed.html">${widget_label}</a></footer>
<!-- maplibre-gl (~207 KB) is loaded lazily by __initMap on the first Map-tab
     open, not on every visit - most visitors never open the map. -->
<script>
  var cities = [], PREVIEW = [];      // filled by __loadMapData (see _map.json)
  var QV = ${qv_json};                // quick-view card strings (localized)
  var ZONE_COLOR = ${zone_color_json};
  var ZONE_BANDS = ${zone_bands_json};
  var GRID_TIP = ${grid_tip_js};      // "{n} of {m} cities with data" (localized)
  // The marker list lives in _map.json, not inline: ~295 KB of it, and the two
  // things that read it (the map itself, the compare pickers) are both behind
  // tabs. Whoever needs it first awaits this promise; later callers get the
  // resolved one. window.__mapCities is the real (analysed) subset - no regions,
  // no ocean reference points - which is what the compare pickers list.
  window.__loadMapData = function () {
    if (!window.__mapDataP) {
      window.__mapDataP = fetch('_map.json')
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (d) {
          cities = d.c || [];
          PREVIEW = d.p || [];
          window.__mapCities = cities.filter(function (c) {
            return c.k !== 'region' && c.k !== 'ocean';
          });
          return d;
        })
        // Drop the cached promise on failure, else one transient error would
        // hand every later caller the same rejection - permanently dead map AND
        // compare pickers, since both share this promise.
        .catch(function (e) { window.__mapDataP = null; throw e; });
    }
    return window.__mapDataP;
  };
  function setMapLoading(on) {
    var el = document.getElementById('map');
    if (el) el.classList[on ? 'add' : 'remove']('map-loading');
  }
  // Tiled Web-Mercator basemap (MapLibre GL). Mercator inflates the high
  // latitudes, but the overlays are all lon/lat so they register correctly, and
  // GPU rendering keeps the 4600-cell coverage grid smooth. Two keyless raster
  // sources: a clean street map (CARTO Voyager) and satellite (Esri imagery).
  // Lazy: the tab controller (charts.js) calls this only when the Map tab is first
  // shown, so first paint isn't blocked on MapLibre + the coverage grid fetch.
  window.__initMap = function () {
    if (window.__mapReady) return;
    // The markers (_map.json) and maplibre-gl are two INDEPENDENT round trips, so
    // both start in this same invocation and whichever finishes last re-enters to
    // find the other ready. Gating one on the other would put a whole round trip
    // back on the Map tab - the thing this deferral exists to avoid. Each branch
    // clears its flag on failure so a later tab open retries.
    var waiting = false;
    if (!window.__mapDataReady) {
      waiting = true;
      if (!window.__mapDataLoading) {
        window.__mapDataLoading = true;
        window.__loadMapData().then(function () {
          window.__mapDataLoading = false;
          window.__mapDataReady = true;
          window.__initMap();
        }).catch(function () { window.__mapDataLoading = false; setMapLoading(false); });
      }
    }
    // Lazy-load maplibre-gl (library + CSS) the first time the Map tab opens,
    // then re-enter once it's ready. Deferring this ~207 KB script off the
    // initial load is the single biggest win for entering-the-site speed.
    if (!window.maplibregl) {
      waiting = true;
      if (!window.__mapLoading) {
        window.__mapLoading = true;
        var css = document.createElement('link');
        css.rel = 'stylesheet';
        css.href = 'https://cdn.jsdelivr.net/npm/maplibre-gl@4/dist/maplibre-gl.css';
        document.head.appendChild(css);
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/maplibre-gl@4/dist/maplibre-gl.js';
        s.onload = function () { window.__mapLoading = false; window.__initMap(); };
        s.onerror = function () { window.__mapLoading = false; setMapLoading(false); };
        document.head.appendChild(s);
      }
    }
    if (waiting) { setMapLoading(true); return; }
    window.__mapReady = true;
    setMapLoading(false);
    // The "Map" basemap is a keyless VECTOR style (OpenFreeMap): its labels are
    // data, so we re-render them in the site's language after load - raster tiles
    // can't be localised because the labels are baked into the image. The terrain/
    // atlas/satellite rasters sit ON TOP of it, one shown at a time; picking "Map"
    // hides them all so the localised vector shows through. Data overlays (dots,
    // grid, bands) are added last, so they stay above every basemap.
    var lang = (document.documentElement.lang || 'en').split('-')[0];
    var RASTERS = [
      { key: 'terrain', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'],
        attr: 'Esri, USGS, NOAA' },
      { key: 'atlas', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}'],
        attr: 'Esri, National Geographic' },
      { key: 'sat', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        attr: 'Imagery &copy; Esri, Maxar, Earthstar Geographics' }
    ];
    // Re-label every name-based vector layer in the site language, falling back to
    // the romanised then the local name where a translation is missing.
    function localizeLabels(l) {
      var expr = ['coalesce', ['get', 'name:' + l], ['get', 'name:latin'], ['get', 'name']];
      (map.getStyle().layers || []).forEach(function (la) {
        if (la.type === 'symbol' && la.layout && la.layout['text-field'] &&
            JSON.stringify(la.layout['text-field']).indexOf('name') >= 0) {
          try { map.setLayoutProperty(la.id, 'text-field', expr); } catch (e) {}
        }
      });
    }

    var map = new maplibregl.Map({
      container: 'map',
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [12, 22], zoom: 1.2, minZoom: 0.5, maxZoom: 12,
      dragRotate: false, pitchWithRotate: false, cooperativeGestures: true,
      attributionControl: { compact: true }
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    /* Fullscreen, to match the per-chart expand button. MapLibre's own control
       rather than the charts.js .fs-btn: it also resizes the GL canvas and
       swaps the enter/exit icon. Its labels are English-only and it rewrites
       them on every toggle, so re-apply the localized one on each change. */
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');
    (function () {
      var lbl = window.__cfs || 'Fullscreen';
      function relabel() {
        var b = document.querySelector('.maplibregl-ctrl-fullscreen, ' +
                                       '.maplibregl-ctrl-shrink');
        if (b) { b.setAttribute('aria-label', lbl); b.title = lbl; }
      }
      relabel();
      document.addEventListener('fullscreenchange', relabel);
      document.addEventListener('webkitfullscreenchange', relabel);
    })();
    map.touchZoomRotate.disableRotation();

    function isRef(c) { return c.k === 'region' || c.k === 'ocean'; }
    // zone key -> colour, as a MapLibre "match" expression (fresh array each call).
    function zoneMatch() {
      var m = ['match', ['get', 'z']];
      Object.keys(ZONE_COLOR).forEach(function (k) { m.push(k, ZONE_COLOR[k]); });
      m.push('#c0392b');
      return m;
    }
    function cityFC(list) {
      return { type: 'FeatureCollection', features: list.map(function (c) {
        return { type: 'Feature',
          properties: { n: c.n || '', s: c.s || '', z: c.z, k: c.k || 'city',
                        r: c.r || '', cc: c.cc || '' },
          geometry: { type: 'Point', coordinates: [c.lon, c.lat] } };
      }) };
    }
    // Climate-zone bands: full-width latitude rectangles, faint over the basemap.
    function bandFC() {
      return { type: 'FeatureCollection', features: ZONE_BANDS.map(function (b) {
        return { type: 'Feature', properties: { c: ZONE_COLOR[b.key] },
          geometry: { type: 'Polygon', coordinates: [[[-180, b.lo], [180, b.lo],
                      [180, b.hi], [-180, b.hi], [-180, b.lo]]] } };
      }) };
    }

    var popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false,
                                       className: 'mappop', offset: 8 });
    var gridMode = false, activeRegion = '';
    var realCities = cities.filter(function (c) { return !isRef(c); });

    // --- continent/country picker: pure zoom -----------------------------------
    // Picking a region or country only fit-zooms the view. Nothing is filtered
    // out - not the city dots and not the coverage grid - so the rest of the
    // world stays visible around the selection.
    var countrySel = document.getElementById('map-country');
    function curCountry() { return countrySel ? countrySel.value : ''; }
    function fitToSelection() {
      var cty = curCountry(), b = null;
      realCities.forEach(function (c) {
        if (activeRegion && c.r !== activeRegion) return;
        if (cty && c.cc !== cty) return;
        if (!b) b = [c.lon, c.lat, c.lon, c.lat];
        else { b[0] = Math.min(b[0], c.lon); b[1] = Math.min(b[1], c.lat);
               b[2] = Math.max(b[2], c.lon); b[3] = Math.max(b[3], c.lat); }
      });
      if (!b) { map.easeTo({ center: [12, 22], zoom: 1.2, duration: 650 }); return; }
      if (b[0] === b[2] && b[1] === b[3])
        map.easeTo({ center: [b[0], b[1]], zoom: 6, duration: 650 });
      else
        map.fitBounds([[b[0], b[1]], [b[2], b[3]]],
                      { padding: 44, duration: 650, maxZoom: 7 });
    }

    // --- coverage grid (GPU fill layer, so 4600 cells stay smooth) ------------
    function gridColor() {
      return ['case', ['>=', ['get', 'n'], ['get', 'm']], '#16a34a',
                      ['==', ['get', 'n'], 0], '#dc2626', '#f59e0b'];
    }
    function loadGrid() {
      fetch('../charts/_coverage.json').then(function (r) { return r.ok ? r.json() : null; })
        .then(function (cov) {
          if (!cov || !cov.cells || !cov.cells.length) return;
          var cd = cov.cell || 0.25;
          var fc = { type: 'FeatureCollection', features: cov.cells.map(function (d) {
            return { type: 'Feature',
              properties: { n: d.n, m: d.m, r: d.r || '', cc: d.cc || '' },
              geometry: { type: 'Polygon', coordinates: [[[d.lo, d.la], [d.lo + cd, d.la],
                          [d.lo + cd, d.la + cd], [d.lo, d.la + cd], [d.lo, d.la]]] } };
          }) };
          map.addSource('grid', { type: 'geojson', data: fc });
          map.addLayer({ id: 'grid-fill', type: 'fill', source: 'grid',
            layout: { visibility: 'none' },
            paint: { 'fill-color': gridColor(), 'fill-opacity': 0.55 } }, 'cities');
          map.addLayer({ id: 'grid-line', type: 'line', source: 'grid',
            layout: { visibility: 'none' },
            paint: { 'line-color': '#ffffff', 'line-width': 0.4, 'line-opacity': 0.7 } }, 'cities');
          if (gridMode) setGridVisible(true);
          map.on('mousemove', 'grid-fill', function (e) {
            map.getCanvas().style.cursor = 'crosshair';
            var p = e.features[0].properties;
            popup.setLngLat(e.lngLat)
                 .setText(GRID_TIP.replace('{n}', p.n).replace('{m}', p.m)).addTo(map);
          });
          map.on('mouseleave', 'grid-fill', function () {
            map.getCanvas().style.cursor = ''; popup.remove();
          });
        }).catch(function () {});
    }
    function setGridVisible(on) {
      // The grid layers sit below 'cities'/'refs' (beforeId 'cities'), so the
      // coverage heatmap overlays the dots instead of replacing them - the same
      // "narrow the view, never hide places" behaviour as the continent filter.
      ['grid-fill', 'grid-line'].forEach(function (id) {
        if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
      });
    }

    // --- quick-view card: click a dot for headline stats, not a hard jump -----
    /* closeOnClick is off: the card now opens on hover AND on tap, and the
       built-in handler would race the tap - closing the popup the same click
       just opened. Dismissal is explicit (hover out, close button, or a click
       away, wired below). */
    var cardPopup = new maplibregl.Popup({ closeButton: true, closeOnClick: false,
                                           maxWidth: '300px', offset: 10 });
    /* The card opens on hover. Two things that has to get right:
       - mousemove fires continuously over a dot, so rebuild only when the
         hovered feature actually changes, otherwise the DOM is thrown away
         mid-interaction and the card flickers;
       - the card holds a link, so leaving the dot starts a short timer instead
         of closing outright, and hovering the card itself cancels it. */
    var cardKey = null, cardTimer = null;
    function cancelCardClose() {
      if (cardTimer) { clearTimeout(cardTimer); cardTimer = null; }
    }
    function scheduleCardClose() {
      cancelCardClose();
      cardTimer = setTimeout(function () { cardPopup.remove(); }, 260);
    }
    cardPopup.on('close', function () { cardKey = null; cancelCardClose(); });
    // Swap hysteresis: while a card is open, a DIFFERENT dot only takes over
    // after the pointer lingers on it (SWAP_MS). Dots merely skimmed while
    // travelling from the dot to the card's link no longer steal the card.
    var SWAP_MS = 150, swapTimer = null, swapKey = null;
    function cancelSwap() {
      if (swapTimer) { clearTimeout(swapTimer); swapTimer = null; }
      swapKey = null;
    }
    function hoverDot(key, show) {
      if (key === cardKey && cardPopup.isOpen()) { cancelCardClose(); cancelSwap(); return; }
      if (!cardPopup.isOpen()) { cancelSwap(); show(); return; }   // nothing up: open now
      if (key === swapKey) return;                                 // already counting down
      cancelSwap(); swapKey = key;
      swapTimer = setTimeout(function () {
        swapTimer = null; swapKey = null; show();
      }, SWAP_MS);
    }
    // One opener for every dot kind (real city, awaiting-data) so the whole map
    // behaves as one system: hover shows a card, the pointer can cross onto it
    // (grace-close), and re-hovering the same dot leaves it be.
    function openCard(key, lngLat, node) {
      cancelCardClose(); cancelSwap();
      popup.remove();                       // drop the plain name tooltip
      if (key === cardKey && cardPopup.isOpen()) return;
      cardKey = key;
      cardPopup.setLngLat(lngLat).setDOMContent(node).addTo(map);
      // Re-wire per open: MapLibre builds a fresh container each addTo.
      var el = cardPopup.getElement();
      if (el && !el.hoverWired) {
        el.hoverWired = true;
        el.addEventListener('mouseenter', function () { cancelCardClose(); cancelSwap(); });
        el.addEventListener('mouseleave', scheduleCardClose);
      }
    }
    function showCard(f) {
      var p = f.properties;
      openCard((p.s || '') + '|' + p.n, f.geometry.coordinates, qvCard(p));
    }
    var rankIdx = null;
    function rankOf(slug) {
      // The ranking arrives with _global.json (window.__gd); before it loads
      // the card just shows the name + link, nothing invented.
      var d = window.__gd;
      if (!d || !d.ranking || !d.ranking.length) return null;
      if (!rankIdx) {
        rankIdx = {};
        for (var i = 0; i < d.ranking.length; i++) rankIdx[d.ranking[i].s] = i;
      }
      var at = rankIdx[slug];
      return at == null ? null
                        : { row: d.ranking[at], pos: at + 1, total: d.ranking.length };
    }
    function qvEl(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text != null) n.textContent = text;
      return n;
    }
    function qvSigned(v, dec) { return (v >= 0 ? '+' : '') + v.toFixed(dec); }
    // °C/°F: charts.js owns the conversion; these read it at call time so the
    // card re-renders correctly after a switch (the map redraws its own cards).
    function qvTemp(v, dec) { return window.__tconv.fmt(v, 'delta', dec, 2); }
    function qvUnit(s) { return window.__tconv.swap(s); }
    function qvCss(name, fb) {   // themed token, light default as fallback
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fb;
    }
    // The nine decade-mean anomalies (vs the 1961-1990 normal) drawn as a
    // filled area: the rise reads as a shape before any number. Warm/cool by
    // the sign of the latest decade; nulls (decades with no data) are skipped,
    // so a short record just starts the curve later. Returns null when fewer
    // than two decades exist - nothing legible to plot.
    function qvSpark(st) {
      var pts = [];
      for (var i = 0; i < st.length; i++)
        if (st[i] != null) pts.push({ i: i, v: st[i] });
      if (pts.length < 2) return null;
      var W = 232, H = 52, padX = 6, padT = 6, padB = 6;
      var vals = pts.map(function (p) { return p.v; });
      var lo = Math.min.apply(null, vals.concat(0));
      var hi = Math.max.apply(null, vals.concat(0.001));
      var range = hi - lo || 1;
      var iw = W - 2 * padX, ih = H - padT - padB, span = (st.length - 1) || 1;
      function X(i) { return padX + i * (iw / span); }
      function Y(v) { return padT + ih - ((v - lo) / range) * ih; }
      var lv = pts[pts.length - 1].v;
      var col = lv >= 0 ? qvCss('--warm', '#d62728') : qvCss('--cool', '#2b6ca3');
      var hair = qvCss('--line', 'rgba(120,120,120,.4)');
      var zeroY = Y(0).toFixed(1);
      var poly = pts.map(function (p) { return X(p.i).toFixed(1) + ',' + Y(p.v).toFixed(1); }).join(' ');
      var x0 = X(pts[0].i).toFixed(1), xN = X(pts[pts.length - 1].i).toFixed(1);
      var gid = 'qvg' + Math.round(Y(0));
      return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H
        + '" width="100%" height="' + H + '" class="qv-spark" role="img" aria-label="'
        + (QV.chartAlt || 'Decade warming trend') + '">'
        + '<line x1="' + padX + '" y1="' + zeroY + '" x2="' + (W - padX) + '" y2="' + zeroY
        + '" stroke="' + hair + '" stroke-width="1" stroke-dasharray="2 3"/>'
        + '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">'
        + '<stop offset="0" stop-color="' + col + '" stop-opacity=".34"/>'
        + '<stop offset="1" stop-color="' + col + '" stop-opacity="0"/></linearGradient></defs>'
        + '<polygon points="' + x0 + ',' + zeroY + ' ' + poly + ' ' + xN + ',' + zeroY
        + '" fill="url(#' + gid + ')"/>'
        + '<polyline points="' + poly + '" fill="none" stroke="' + col
        + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        + '<circle cx="' + xN + '" cy="' + Y(lv).toFixed(1) + '" r="3.4" fill="' + col + '"/></svg>';
    }
    function qvCard(p) {
      var root = qvEl('div', 'qv');
      root.appendChild(qvEl('div', 'qv-name', p.n));
      // Slug = URL basename: tiered tail dots may carry ../<lang>/<slug>.html.
      var rk = rankOf((p.s || '').split('/').pop().replace(/\\.html$$/, ''));
      if (rk) {
        root.appendChild(qvEl('div', 'qv-trend ' + (rk.row.t >= 0 ? 'qv-warm' : 'qv-cool'),
                              qvTemp(rk.row.t, 2) + ' ' + qvUnit(QV.perDecade)));
        if (rk.row.dt != null)
          root.appendChild(qvEl('div', 'qv-line',
                                qvUnit(QV.since).replace(
                                  '{v}', qvTemp(rk.row.dt, 1) + ' '
                                         + window.__tconv.deg())));
        var pct = Math.floor(100 * (rk.total - rk.pos) / rk.total);
        root.appendChild(qvEl('div', 'qv-line',
                              '#' + rk.pos + ' / ' + rk.total + ' · '
                              + QV.faster.replace('{pct}', pct)));
        if (rk.row.st && rk.row.st.length) {
          var svg = qvSpark(rk.row.st);
          if (svg) {
            var w = qvEl('div', 'qv-sparkwrap');
            w.innerHTML = svg;   // built from numbers + theme tokens, no user data
            root.appendChild(w);
            root.appendChild(qvEl('div', 'qv-cap', QV.baseline));
          }
        }
      }
      if (p.s) {
        var a = qvEl('a', 'qv-open', QV.cta.replace('{name}', p.n));
        a.href = p.s;
        root.appendChild(a);
      }
      return root;
    }
    function havKm(la1, lo1, la2, lo2) {
      var R = 6371, dLa = (la2 - la1) * Math.PI / 180, dLo = (lo2 - lo1) * Math.PI / 180;
      var a = Math.sin(dLa / 2) * Math.sin(dLa / 2)
            + Math.cos(la1 * Math.PI / 180) * Math.cos(la2 * Math.PI / 180)
            * Math.sin(dLo / 2) * Math.sin(dLo / 2);
      return 2 * R * Math.asin(Math.sqrt(a));
    }

    map.on('load', function () {
      localizeLabels(lang);   // vector base -> site language
      // Raster basemaps above the vector base, below the overlays; hidden until picked.
      RASTERS.forEach(function (r) {
        map.addSource('r-' + r.key, { type: 'raster', tileSize: 256, tiles: r.tiles, attribution: r.attr });
        map.addLayer({ id: 'base-' + r.key, type: 'raster', source: 'r-' + r.key,
          layout: { visibility: 'none' } });
      });
      map.addSource('bands', { type: 'geojson', data: bandFC() });
      map.addLayer({ id: 'bands', type: 'fill', source: 'bands',
        paint: { 'fill-color': ['get', 'c'], 'fill-opacity': 0.12 } });
      if (PREVIEW && PREVIEW.length) {
        map.addSource('preview', { type: 'geojson', data: cityFC(PREVIEW) });
        map.addLayer({ id: 'preview', type: 'circle', source: 'preview',
          paint: { 'circle-radius': 2, 'circle-color': zoneMatch(), 'circle-opacity': 0.35 } });
      }
      map.addSource('cities', { type: 'geojson', data: cityFC(realCities) });
      map.addSource('refs', { type: 'geojson', data: cityFC(cities.filter(isRef)) });
      map.addLayer({ id: 'refs', type: 'circle', source: 'refs',
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 3.4, 8, 6],
          'circle-color': '#ffffff', 'circle-opacity': 0.9,
          'circle-stroke-width': 1.6,
          'circle-stroke-color': ['case', ['==', ['get', 'k'], 'ocean'], '#0e7490', zoneMatch()] } });
      map.addLayer({ id: 'cities', type: 'circle', source: 'cities',
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 2.8, 8, 6.5],
          'circle-color': zoneMatch(), 'circle-opacity': 0.95,
          'circle-stroke-width': 0.8, 'circle-stroke-color': '#ffffff' } });

      map.on('mouseenter', 'cities', function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mousemove', 'cities', function (e) {
        var f = e.features[0], p = f.properties;
        hoverDot((p.s || '') + '|' + p.n, function () { showCard(f); });
      });
      // Closing is deferred: the card carries a link, so the pointer has to be
      // able to travel from the dot onto the card without it vanishing en route.
      map.on('mouseleave', 'cities', function () {
        map.getCanvas().style.cursor = ''; cancelSwap(); scheduleCardClose();
      });
      map.on('click', 'cities', function (e) {
        var f = e.features[0], p = f.properties, key = (p.s || '') + '|' + p.n;
        // Clicking the dot itself opens the city, so no need to travel to the
        // card's link. On desktop the hover already opened this dot's card, so
        // the click navigates. On touch (no hover) the first tap opens the card
        // and a second tap - card now up for this dot - navigates.
        if (p.s && key === cardKey && cardPopup.isOpen()) { window.location.href = p.s; return; }
        cancelSwap(); showCard(f);   // also resolves a pending debounced swap
      });
      // Tapping empty map dismisses the card - on touch there is no mouseleave
      // to do it, so without this the card would stay pinned.
      map.on('click', function (e) {
        var hit = ['cities'];
        if (PREVIEW && PREVIEW.length) hit.push('preview');
        if (map.queryRenderedFeatures(e.point, { layers: hit }).length) return;
        cancelCardClose(); cardPopup.remove();
      });
      map.on('mousemove', 'refs', function (e) {
        popup.setLngLat(e.lngLat).setText(e.features[0].properties.n).addTo(map);
      });
      map.on('mouseleave', 'refs', function () { popup.remove(); });
      // Awaiting-data dots: no page yet, but the card still leads somewhere -
      // the nearest city that IS analysed (straight-line distance). Same hover
      // card + grace-close as the real dots, so the map reads as one system.
      function previewCard(f) {
        var c = f.geometry.coordinates, best = null, bd = Infinity;
        for (var i = 0; i < realCities.length; i++) {
          var d = havKm(c[1], c[0], realCities[i].lat, realCities[i].lon);
          if (d < bd) { bd = d; best = realCities[i]; }
        }
        var root = qvEl('div', 'qv');
        if (f.properties.n) root.appendChild(qvEl('div', 'qv-name', f.properties.n));
        root.appendChild(qvEl('div', 'qv-line', QV.nodata));
        if (best) {
          var ln = qvEl('div', 'qv-line');
          ln.appendChild(document.createTextNode(QV.nearest + ': '));
          var a = qvEl('a', null, best.n);
          a.href = best.s;
          ln.appendChild(a);
          ln.appendChild(document.createTextNode(' (~' + Math.round(bd) + ' km)'));
          root.appendChild(ln);
        }
        return root;
      }
      function showPreview(f) {
        openCard('preview|' + f.properties.n + '|' + f.geometry.coordinates.join(','),
                 f.geometry.coordinates, previewCard(f));
      }
      map.on('mouseenter', 'preview', function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mousemove', 'preview', function (e) {
        // A real dot under the pointer wins - its card is the richer one.
        if (map.queryRenderedFeatures(e.point, { layers: ['cities'] }).length) return;
        var f = e.features[0];
        hoverDot('preview|' + f.properties.n + '|' + f.geometry.coordinates.join(','),
                 function () { showPreview(f); });
      });
      map.on('mouseleave', 'preview', function () {
        map.getCanvas().style.cursor = ''; cancelSwap(); scheduleCardClose();
      });
      map.on('click', 'preview', function (e) {
        // Still needed on touch, where no hover event ever fires.
        if (map.queryRenderedFeatures(e.point, { layers: ['cities'] }).length) return;
        showPreview(e.features[0]);
      });

      loadGrid();
    });

    // --- continent pills + country select (reuse the existing controls) -------
    var regionHost = document.getElementById('map-region');
    var regionBtns = regionHost ? regionHost.querySelectorAll('button') : [];
    function setActiveRegion(key) {
      activeRegion = key || '';
      Array.prototype.forEach.call(regionBtns, function (b) {
        var on = key !== null && b.getAttribute('data-region') === key;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
    Array.prototype.forEach.call(regionBtns, function (b) {
      b.addEventListener('click', function () {
        setActiveRegion(b.getAttribute('data-region') || '');
        if (countrySel) countrySel.value = '';
        fitToSelection();
      });
    });
    if (countrySel) {
      var flang = (document.documentElement.lang || 'en').split('-')[0], fdn = null;
      try { fdn = new Intl.DisplayNames([flang], { type: 'region' }); } catch (e) { fdn = null; }
      function flagEmoji(cc) {
        if (!cc || cc.length !== 2) return '';
        var A = 0x1F1E6, u = cc.toUpperCase();
        return String.fromCodePoint(A + u.charCodeAt(0) - 65)
             + String.fromCodePoint(A + u.charCodeAt(1) - 65);
      }
      var seen = {}, opts = [];
      realCities.forEach(function (c) {
        if (!c.cc || seen[c.cc]) return; seen[c.cc] = 1;
        var up = c.cc.toUpperCase(), nm = up;
        if (fdn) { try { nm = fdn.of(up) || up; } catch (e) {} }
        opts.push({ cc: c.cc, nm: nm });
      });
      opts.sort(function (a, b) { return a.nm.localeCompare(b.nm, flang); });
      opts.forEach(function (o) {
        var op = document.createElement('option');
        // Name first, flag last, so the browser's native type-ahead matches the
        // country name (open and closed) - a leading flag emoji would capture it.
        op.value = o.cc; op.textContent = o.nm + '  ' + flagEmoji(o.cc);
        countrySel.appendChild(op);
      });
      countrySel.addEventListener('change', function () {
        setActiveRegion(countrySel.value ? null : '');
        fitToSelection();
      });
    }

    // --- coverage-grid toggle (overlays the grid on the dots, adds its legend) -
    var gridToggle = document.getElementById('grid-toggle');
    var zoneLegend = document.getElementById('zone-legend');
    var gridLegend = document.getElementById('grid-legend');
    if (gridToggle) {
      gridToggle.addEventListener('click', function () {
        gridMode = !gridMode;
        gridToggle.setAttribute('aria-pressed', gridMode ? 'true' : 'false');
        // Dots stay visible under the grid, so keep the climate-zone legend up
        // alongside the coverage legend rather than swapping one for the other.
        if (zoneLegend) zoneLegend.hidden = false;
        if (gridLegend) gridLegend.hidden = !gridMode;
        popup.remove();
        setGridVisible(gridMode);
      });
    }

    // --- basemap switch: street map <-> satellite -----------------------------
    var bmBtns = document.querySelectorAll('#map-basemap button');
    Array.prototype.forEach.call(bmBtns, function (b) {
      b.addEventListener('click', function () {
        var kind = b.getAttribute('data-base');   // 'map' shows the vector base (no raster)
        RASTERS.forEach(function (r) {
          if (map.getLayer('base-' + r.key))
            map.setLayoutProperty('base-' + r.key, 'visibility', r.key === kind ? 'visible' : 'none');
        });
        Array.prototype.forEach.call(bmBtns, function (x) {
          x.classList.toggle('active', x === b);
          x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
        });
      });
    });

    // The tab controller calls this when the Map tab is re-shown, in case the
    // GL canvas needs to reflow to the panel's current size.
    window.__mapResize = function () { try { map.resize(); } catch (e) {} };
  };
</script>
<script>
  window.__ci18n = ${chart_i18n};
  window.__ci18nF = ${chart_i18n_f};
  window.__cmonths = ${months_json};
  window.__chartErr = ${chart_err_json};
  window.__cfs = ${fs_label_json};
  window.__crz = ${rz_label_json};
  window.__rankPeople = ${rank_people_json};
  (function () {
    // Names and the payload go out TOGETHER, not one after the other: the ranking
    // needs both, so serializing them cost a whole round trip on the critical
    // path. Only this page's language is fetched, by BASE code - zh-TW reads
    // _names.zh.json, which is how the exonym table is keyed (see
    // report.place_names_for for the {l, f} shape). Missing names just leave every
    // city on its default name, so a failure here degrades rather than blocking
    // the payload.
    var lang = (document.documentElement.lang || 'en').split('-')[0];
    var NO_NAMES = { l: {}, f: {} };
    var names = fetch('../charts/_names.' + lang + '.json')
      .then(function (r) { return r.ok ? r.json() : NO_NAMES; })
      .catch(function () { return NO_NAMES; });
    var payload = fetch('../charts/_global.json')
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
    Promise.all([names, payload])
      .then(function (both) {
        window.__names = both[0];
        var d = both[1];
        window.__gd = d;   // the map's quick-view card reads the ranking here
        if (window.renderGlobal) window.renderGlobal(d);
      })
      .catch(function (e) {
        if (window.chartsUnavailable) window.chartsUnavailable(e);
        else if (window.console) console.error('global load', e);
      });
  })();
  // Wire the omni search now too - city/region search works immediately; the
  // country + "faster than N%" parts fill in once _global.json loads.
  if (window.initOmni) window.initOmni();
  // --- compare two cities: overlay their yearly-anomaly curves --------------
  // Reuses the per-city chart JSONs (each city's anomalies vs its own
  // 1961-1990 baseline, LOESS included - all server-computed) and the shared
  // multitrend renderer, so the overlay matches the site's other charts.
  (function () {
    var a = document.getElementById('cmp-a'), b = document.getElementById('cmp-b');
    var dl = document.getElementById('cmp-cities');
    var fig = document.getElementById('cmp-figure');
    var stats = document.getElementById('cmp-stats');
    if (!a || !b || !dl || !fig) return;
    /* Canvas needs a literal hex (charts.js re-themes these via --warm/--cool
       at build time); the legend dot is DOM, so it takes the var directly and
       both stay the same colour after a theme switch. */
    var COLORS = ['#d62728', '#2c7fb8'];
    var DOTVARS = ['var(--warm)', 'var(--cool)'];
    // The city list is a fetch (see __loadMapData) and building ~2300 <option>
    // nodes is real main-thread work, so both wait until Compare is actually
    // used. Every entry point below goes through cmpReady(); the promise is
    // shared with the map, so opening both tabs still fetches _map.json once.
    var bySlug = {}, byVal = {}, cmpReadyP = null;
    function cmpReady() {
      if (!cmpReadyP) {
        cmpReadyP = window.__loadMapData().then(function () {
          var frag = document.createDocumentFragment();
          (window.__mapCities || []).forEach(function (c) {
            if (!c.s) return;
            var slug = c.s.split('/').pop().replace('.html', '');
            var val = c.n + (c.cc ? ' (' + c.cc.toUpperCase() + ')' : '');
            bySlug[slug] = { n: c.n, val: val };
            byVal[val] = slug;
            var o = document.createElement('option');
            o.value = val;
            frag.appendChild(o);
          });
          dl.appendChild(frag);
        }).catch(function () { cmpReadyP = null; });   // let the next pick retry
      }
      return cmpReadyP;
    }
    var cache = {}, cur = null, seq = 0;
    function loadCity(slug) {
      if (!cache[slug])
        cache[slug] = fetch('../charts/' + slug + '.json').then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        }).then(window.__expandYears);
      return cache[slug];
    }
    function rankRow(slug) {
      var d = window.__gd;
      if (!d || !d.ranking) return null;
      for (var i = 0; i < d.ranking.length; i++)
        if (d.ranking[i].s === slug)
          return { r: d.ranking[i], pos: i + 1, total: d.ranking.length };
      return null;
    }
    function statRow(slug, color) {
      var rk = rankRow(slug);
      var row = document.createElement('div');
      row.className = 'cs-row';
      var dot = document.createElement('span');
      dot.className = 'cs-dot';
      dot.style.background = color;
      row.appendChild(dot);
      var parts = [bySlug[slug].n];
      if (rk) {
        var unit = (window.__ci18n || {})['°C / decade'] || '°C / decade';
        parts.push(window.__tconv.fmt(rk.r.t, 'delta', 2, 1) + ' '
                   + window.__tconv.swap(unit));
        if (rk.r.dt != null)
          parts.push(window.__tconv.fmt(rk.r.dt, 'delta', 1, 1) + ' '
                     + window.__tconv.deg());
        parts.push('#' + rk.pos + ' / ' + rk.total);
      }
      row.appendChild(document.createTextNode(' ' + parts.join(' · ')));
      return row;
    }
    function draw() {
      var sa = byVal[a.value], sb = byVal[b.value];
      if (!sa || !sb || sa === sb) return;
      var my = ++seq;
      Promise.all([loadCity(sa), loadCity(sb)]).then(function (ds) {
        if (my !== seq) return;   // a newer pick superseded this one
        var A = ds[0].anomalies, B = ds[1].anomalies;
        if (!A || !B) return;
        var years = A.x.slice();
        B.x.forEach(function (y) { if (years.indexOf(y) < 0) years.push(y); });
        years.sort(function (p, q) { return p - q; });
        function align(x, v) {
          var m = {};
          x.forEach(function (y, i) { m[y] = v[i]; });
          return years.map(function (y) { return m[y] == null ? null : m[y]; });
        }
        var payload = {
          kind: 'multitrend', x: years, xlabel: A.xlabel, ylabel: A.ylabel,
          series: [
            { label: bySlug[sa].n, color: COLORS[0],
              raw: align(A.x, A.values), loess: align(A.x, A.loess) },
            { label: bySlug[sb].n, color: COLORS[1],
              raw: align(B.x, B.values), loess: align(B.x, B.loess) }
          ]
        };
        if (cur) { cur.destroy(); cur = null; }
        fig.hidden = false;
        cur = window.renderChart('c-cmp', payload);
        while (stats.firstChild) stats.removeChild(stats.firstChild);
        stats.appendChild(statRow(sa, DOTVARS[0]));
        stats.appendChild(statRow(sb, DOTVARS[1]));
        if (history.replaceState)
          history.replaceState(null, '', '#cmp=' + sa + ',' + sb);
      }).catch(function () {});
    }
    a.addEventListener('change', function () { cmpReady().then(draw); });
    b.addEventListener('change', function () { cmpReady().then(draw); });
    // Typing starts before 'change' fires, so warm the list on focus - the
    // datalist has to be populated for the browser to suggest anything. Not
    // {once:true}: cmpReady is already idempotent, and a one-shot listener would
    // be spent by an attempt that failed, leaving focus unable to retry.
    a.addEventListener('focus', cmpReady);
    b.addEventListener('focus', cmpReady);
    // The stat rows under the overlay are built text; redraw on a °C/°F switch
    // (the chart itself rebuilds from its payload via 'themechange').
    if (window.__unitHooks) window.__unitHooks.push(draw);
    var m = (location.hash || '').match(/cmp=([a-z0-9'-]+),([a-z0-9'-]+)/);
    var cmpPrefilled = false;
    // A #cmp= deep link is the one case that needs the list immediately.
    if (m) {
      cmpReady().then(function () {
        if (!bySlug[m[1]] || !bySlug[m[2]]) return;
        a.value = bySlug[m[1]].val;
        b.value = bySlug[m[2]].val;
        cmpPrefilled = true;
        draw();
      });
    }
    // The Compare tab opens on YOUR city vs a randomly chosen notable city, so it
    // is useful before you pick anything. Reuses window.__heroSlug (the hero's
    // geolocated region); skipped when a #cmp= link, a prior pick, or a previous
    // prefill already filled it. Only fires while the Compare tab is visible so it
    // never fetches two city files the visitor may never look at.
    var ICONIC = ['tokyo', 'london', 'paris', 'beijing', 'shanghai', 'dubai',
      'singapore', 'sydney', 'moscow', 'istanbul', 'mumbai', 'delhi', 'cairo',
      'berlin', 'new-york', 'los-angeles', 'sao-paulo', 'rio-de-janeiro',
      'mexico-city', 'bangkok', 'jakarta', 'seoul', 'madrid', 'rome', 'toronto',
      'cape-town', 'nairobi', 'lagos', 'buenos-aires', 'hong-kong'];
    window.__cmpPrefill = function () {
      if (cmpPrefilled) return;
      var panel = document.getElementById('tp-compare');
      if (!panel || panel.hidden) return;
      if (a.value || b.value) return;
      cmpReady().then(function () {
        // Re-check after the await: the visitor may have typed or navigated away
        // while the city list was in flight.
        if (cmpPrefilled || panel.hidden || a.value || b.value) return;
        var mine = window.__heroSlug;
        if (!mine || !bySlug[mine]) return;
        var pool = ICONIC.filter(function (s) { return bySlug[s] && s !== mine; });
        if (!pool.length) return;
        var pick = pool[Math.floor(Math.random() * pool.length)];
        a.value = bySlug[mine].val;
        b.value = bySlug[pick].val;
        cmpPrefilled = true;
        draw();
      });
    };
  })();
  // Auto-hide the sticky top bar on scroll - mobile only (desktop keeps it
  // pinned). Hide when scrolling down past the bar, reveal on any scroll up.
  (function () {
    var bar = document.getElementById('topbar');
    if (!bar) return;
    var mq = window.matchMedia('(max-width: 720px)');
    var lastY = window.pageYOffset || 0, ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        var y = window.pageYOffset || 0;
        if (mq.matches) {
          if (y > lastY + 4 && y > 80) bar.classList.add('hide');
          else if (y < lastY - 4) bar.classList.remove('hide');
        } else {
          bar.classList.remove('hide');
        }
        lastY = y;
        ticking = false;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    if (mq.addEventListener) mq.addEventListener('change', function () {
      if (!mq.matches) bar.classList.remove('hide');
    });
  })();
</script>
</body>
</html>
"""
)


# "Your region" hero micro-copy per language. Kept here (like _CHART_ERR) rather
# than in the 32 i18n tables; _hero_str falls back to English per key. Placeholders
# {name} (city), {v} (e.g. "+2.5 C"), {pct} (0-100) are filled at render time.
_HERO_I18N = {
    "en": {"eyebrow": "Your region", "cta": "Explore {name}",
           "since": "{v} warmer than 1940",
           "faster": "warming faster than {pct}% of the world",
           "locating": "Finding the nearest city to you...",
           "near": "Nearest city with records to your location",
           "default": "A featured region. Allow location for yours."},
    "pl": {"eyebrow": "Twój region", "cta": "Poznaj miasto {name}",
           "since": "{v} cieplej niż w 1940",
           "faster": "ociepla się szybciej niż {pct}% świata",
           "locating": "Szukanie najbliższego miasta...",
           "near": "Najbliższe miasto z danymi względem Twojej lokalizacji",
           "default": "Wyróżniony region. Zezwól na lokalizację, aby zobaczyć swój."},
    "de": {"eyebrow": "Deine Region", "cta": "{name} entdecken",
           "since": "{v} wärmer als 1940",
           "faster": "erwärmt sich schneller als {pct}% der Welt",
           "locating": "Nächstgelegene Stadt wird gesucht...",
           "near": "Nächstgelegene Stadt mit Daten zu deinem Standort",
           "default": "Eine Beispielregion. Erlaube den Standort für deine."},
    "fr": {"eyebrow": "Votre région", "cta": "Découvrir {name}",
           "since": "{v} de plus qu'en 1940",
           "faster": "se réchauffe plus vite que {pct}% du monde",
           "locating": "Recherche de la ville la plus proche...",
           "near": "Ville avec données la plus proche de votre position",
           "default": "Une région en vedette. Autorisez la localisation pour la vôtre."},
    "es": {"eyebrow": "Tu región", "cta": "Explorar {name}",
           "since": "{v} más que en 1940",
           "faster": "se calienta más rápido que el {pct}% del mundo",
           "locating": "Buscando la ciudad más cercana...",
           "near": "Ciudad con datos más cercana a tu ubicación",
           "default": "Una región destacada. Permite la ubicación para ver la tuya."},
    "uk": {"eyebrow": "Ваш регіон", "cta": "Дослідити місто {name}",
           "since": "{v} тепліше, ніж у 1940",
           "faster": "теплішає швидше, ніж {pct}% світу",
           "locating": "Пошук найближчого міста...",
           "near": "Найближче місто з даними до вашого розташування",
           "default": "Показовий регіон. Дозвольте геолокацію, щоб побачити свій."},
    "ru": {"eyebrow": "Ваш регион", "cta": "Открыть город {name}",
           "since": "на {v} теплее, чем в 1940",
           "faster": "теплеет быстрее, чем {pct}% мира",
           "locating": "Поиск ближайшего города...",
           "near": "Ближайший город с данными к вашему местоположению",
           "default": "Пример региона. Разрешите геолокацию, чтобы увидеть свой."},
    "zh": {"eyebrow": "你所在的地区", "cta": "探索 {name}",
           "since": "比 1940 年高 {v}",
           "faster": "变暖速度快于全球 {pct}% 的地区",
           "locating": "正在查找最近的城市...",
           "near": "距您所在位置最近的有数据城市",
           "default": "精选地区。允许定位以查看你的地区。"},
    "ja": {"eyebrow": "あなたの地域", "cta": "{name} を見る",
           "since": "1940年より{v}高い",
           "faster": "世界の{pct}%より速く温暖化",
           "locating": "最寄りの都市を検索中...",
           "near": "あなたの位置に最も近い記録のある都市",
           "default": "注目の地域です。位置情報を許可すると自分の地域を表示します。"},
    "ko": {"eyebrow": "내 지역", "cta": "{name} 살펴보기",
           "since": "1940년보다 {v} 높음",
           "faster": "세계 {pct}%보다 빠르게 온난화",
           "locating": "가장 가까운 도시 검색 중...",
           "near": "내 위치에서 가장 가까운 기록 보유 도시",
           "default": "추천 지역입니다. 위치를 허용하면 내 지역이 표시됩니다."},
    "ar": {"eyebrow": "منطقتك", "cta": "استكشف {name}",
           "since": "أدفأ بمقدار {v} عن 1940",
           "faster": "يزداد احترارًا أسرع من {pct}% من العالم",
           "locating": "جارٍ البحث عن أقرب مدينة...",
           "near": "أقرب مدينة تتوفر لها بيانات من موقعك",
           "default": "منطقة مختارة. اسمح بالوصول إلى الموقع لعرض منطقتك."},
    "pt": {"eyebrow": "A sua região", "cta": "Explorar {name}",
           "since": "{v} mais quente que em 1940",
           "faster": "aquece mais rápido que {pct}% do mundo",
           "locating": "A procurar a cidade mais próxima...",
           "near": "Cidade com dados mais próxima da sua localização",
           "default": "Uma região em destaque. Permita a localização para ver a sua."},
    "bn": {"eyebrow": "আপনার অঞ্চল", "cta": "{name} দেখুন",
           "since": "১৯৪০ সালের চেয়ে {v} বেশি",
           "faster": "বিশ্বের {pct}% এর চেয়ে দ্রুত উষ্ণ হচ্ছে",
           "locating": "নিকটতম শহর খোঁজা হচ্ছে...",
           "near": "আপনার অবস্থানের নিকটতম তথ্যযুক্ত শহর",
           "default": "একটি নির্বাচিত অঞ্চল। নিজেরটি দেখতে অবস্থানের অনুমতি দিন।"},
    "id": {"eyebrow": "Wilayah Anda", "cta": "Jelajahi {name}",
           "since": "{v} lebih hangat dari 1940",
           "faster": "menghangat lebih cepat dari {pct}% dunia",
           "locating": "Mencari kota terdekat...",
           "near": "Kota terdekat dengan data dari lokasi Anda",
           "default": "Wilayah unggulan. Izinkan lokasi untuk melihat wilayah Anda."},
    "ur": {"eyebrow": "آپ کا علاقہ", "cta": "{name} دیکھیں",
           "since": "1940 کے مقابلے {v} زیادہ گرم",
           "faster": "دنیا کے {pct}% سے تیز گرم ہو رہا ہے",
           "locating": "قریب ترین شہر تلاش کیا جا رہا ہے...",
           "near": "آپ کے مقام کے قریب ترین ڈیٹا والا شہر",
           "default": "ایک نمایاں علاقہ۔ اپنا دیکھنے کے لیے مقام کی اجازت دیں۔"},
    "it": {"eyebrow": "La tua regione", "cta": "Esplora {name}",
           "since": "{v} più caldo del 1940",
           "faster": "si riscalda più rapidamente del {pct}% del mondo",
           "locating": "Ricerca della città più vicina...",
           "near": "Città con dati più vicina alla tua posizione",
           "default": "Una regione in evidenza. Consenti la posizione per vedere la tua."},
    "tr": {"eyebrow": "Bölgeniz", "cta": "Keşfet: {name}",
           "since": "1940'a göre {v} daha sıcak",
           "faster": "dünyanın %{pct}'sinden daha hızlı ısınıyor",
           "locating": "En yakın şehir aranıyor...",
           "near": "Konumunuza en yakın verili şehir",
           "default": "Öne çıkan bir bölge. Kendinizinki için konuma izin verin."},
    "fa": {"eyebrow": "منطقه شما", "cta": "کاوش {name}",
           "since": "{v} گرم‌تر از ۱۹۴۰",
           "faster": "سریع‌تر از {pct}٪ جهان گرم می‌شود",
           "locating": "در حال یافتن نزدیک‌ترین شهر...",
           "near": "نزدیک‌ترین شهر دارای داده به موقعیت شما",
           "default": "یک منطقه منتخب. برای دیدن منطقه خود، موقعیت مکانی را مجاز کنید."},
    "vi": {"eyebrow": "Khu vực của bạn", "cta": "Khám phá {name}",
           "since": "ấm hơn {v} so với 1940",
           "faster": "ấm lên nhanh hơn {pct}% thế giới",
           "locating": "Đang tìm thành phố gần nhất...",
           "near": "Thành phố có dữ liệu gần vị trí của bạn nhất",
           "default": "Khu vực nổi bật. Cho phép vị trí để xem khu vực của bạn."},
    "nl": {"eyebrow": "Jouw regio", "cta": "Ontdek {name}",
           "since": "{v} warmer dan in 1940",
           "faster": "warmt sneller op dan {pct}% van de wereld",
           "locating": "Dichtstbijzijnde stad zoeken...",
           "near": "Dichtstbijzijnde stad met gegevens bij jouw locatie",
           "default": "Een uitgelichte regio. Sta locatie toe voor die van jou."},
    "sw": {"eyebrow": "Eneo lako", "cta": "Chunguza {name}",
           "since": "{v} joto zaidi kuliko 1940",
           "faster": "linaongezeka joto haraka kuliko {pct}% ya dunia",
           "locating": "Inatafuta jiji lililo karibu zaidi...",
           "near": "Jiji lililo karibu na eneo lako lenye rekodi",
           "default": "Eneo lililoangaziwa. Ruhusu eneo ili kuona lako."},
    "tl": {"eyebrow": "Ang iyong rehiyon", "cta": "Tuklasin ang {name}",
           "since": "{v} mas mainit kaysa 1940",
           "faster": "mas mabilis uminit kaysa {pct}% ng mundo",
           "locating": "Hinahanap ang pinakamalapit na lungsod...",
           "near": "Pinakamalapit na lungsod na may datos sa iyong lokasyon",
           "default": "Isang tampok na rehiyon. Payagan ang lokasyon para makita ang iyo."},
    "th": {"eyebrow": "ภูมิภาคของคุณ", "cta": "สำรวจ {name}",
           "since": "อุ่นกว่าปี 1940 อยู่ {v}",
           "faster": "อุ่นขึ้นเร็วกว่า {pct}% ของโลก",
           "locating": "กำลังค้นหาเมืองที่ใกล้ที่สุด...",
           "near": "เมืองที่มีข้อมูลใกล้ตำแหน่งของคุณที่สุด",
           "default": "ภูมิภาคแนะนำ อนุญาตตำแหน่งเพื่อดูของคุณ"},
    "ta": {"eyebrow": "உங்கள் பகுதி", "cta": "{name} ஐ ஆராயுங்கள்",
           "since": "1940 ஐ விட {v} அதிகம்",
           "faster": "உலகின் {pct}% ஐ விட வேகமாக வெப்பமடைகிறது",
           "locating": "அருகிலுள்ள நகரம் தேடப்படுகிறது...",
           "near": "உங்கள் இருப்பிடத்திற்கு அருகிலுள்ள தரவுள்ள நகரம்",
           "default": "ஒரு சிறப்புப் பகுதி. உங்களுடையதைக் காண இருப்பிடத்தை அனுமதிக்கவும்."},
    "mr": {"eyebrow": "तुमचा प्रदेश", "cta": "{name} पाहा",
           "since": "1940 पेक्षा {v} जास्त",
           "faster": "जगाच्या {pct}% पेक्षा वेगाने तापत आहे",
           "locating": "सर्वात जवळचे शहर शोधत आहे...",
           "near": "तुमच्या स्थानाजवळील नोंदी असलेले शहर",
           "default": "एक निवडक प्रदेश. तुमचा पाहण्यासाठी स्थानाला परवानगी द्या."},
    "te": {"eyebrow": "మీ ప్రాంతం", "cta": "{name} అన్వేషించండి",
           "since": "1940 కంటే {v} ఎక్కువ",
           "faster": "ప్రపంచంలో {pct}% కంటే వేగంగా వేడెక్కుతోంది",
           "locating": "సమీప నగరం కోసం వెతుకుతోంది...",
           "near": "మీ ప్రాంతానికి సమీపంలోని డేటా ఉన్న నగరం",
           "default": "ఒక ఎంపిక ప్రాంతం. మీది చూడటానికి స్థానాన్ని అనుమతించండి."},
    "ha": {"eyebrow": "Yankinku", "cta": "Bincika {name}",
           "since": "{v} fiye da 1940",
           "faster": "yana ƙara zafi da sauri fiye da {pct}% na duniya",
           "locating": "Ana neman birni mafi kusa...",
           "near": "Birni mafi kusa da wurinka mai bayanai",
           "default": "Yanki na musamman. Ba da izinin wuri don ganin naka."},
    "pa": {"eyebrow": "ਤੁਹਾਡਾ ਖੇਤਰ", "cta": "{name} ਵੇਖੋ",
           "since": "1940 ਤੋਂ {v} ਵੱਧ",
           "faster": "ਦੁਨੀਆ ਦੇ {pct}% ਤੋਂ ਤੇਜ਼ੀ ਨਾਲ ਗਰਮ ਹੋ ਰਿਹਾ",
           "locating": "ਸਭ ਤੋਂ ਨੇੜਲਾ ਸ਼ਹਿਰ ਲੱਭ ਰਿਹਾ ਹੈ...",
           "near": "ਤੁਹਾਡੇ ਟਿਕਾਣੇ ਦੇ ਨੇੜੇ ਡਾਟਾ ਵਾਲਾ ਸ਼ਹਿਰ",
           "default": "ਇੱਕ ਚੁਣਿਆ ਖੇਤਰ। ਆਪਣਾ ਵੇਖਣ ਲਈ ਟਿਕਾਣੇ ਦੀ ਇਜਾਜ਼ਤ ਦਿਓ।"},
    "my": {"eyebrow": "သင့်ဒေသ", "cta": "{name} ကို ကြည့်ရန်",
           "since": "1940 ထက် {v} ပိုပူ",
           "faster": "ကမ္ဘာ့ {pct}% ထက် ပိုမြန်စွာ ပူနွေးလာသည်",
           "locating": "အနီးဆုံးမြို့ကို ရှာနေသည်...",
           "near": "သင့်တည်နေရာအနီးဆုံး မှတ်တမ်းရှိသောမြို့",
           "default": "အထူးဖော်ပြထားသောဒေသ။ သင့်ဒေသကိုကြည့်ရန် တည်နေရာခွင့်ပြုပါ။"},
    "am": {"eyebrow": "የእርስዎ ክልል", "cta": "{name} ይመልከቱ",
           "since": "ከ1940 በ{v} ይሞቃል",
           "faster": "ከዓለም {pct}% በበለጠ ፍጥነት እየሞቀ ነው",
           "locating": "በአቅራቢያ ያለ ከተማ በመፈለግ ላይ...",
           "near": "ወደ አካባቢዎ ቅርብ የሆነ መረጃ ያለው ከተማ",
           "default": "የተመረጠ ክልል። የእርስዎን ለማየት አካባቢን ይፍቀዱ።"},
    "yo": {"eyebrow": "Agbègbè rẹ", "cta": "Ṣàwárí {name}",
           "since": "{v} gbóná ju 1940 lọ",
           "faster": "ń móoru yára ju {pct}% àgbáyé lọ",
           "locating": "Ń wá ìlú tó súnmọ́ jù...",
           "near": "Ìlú tó súnmọ́ ọ jù tó ní àkọsílẹ̀",
           "default": "Agbègbè àyànfẹ́. Gba ìpò láyè láti rí tìrẹ."},
}
extra_i18n.fill(_HERO_I18N, "hero")


def _hero_str(lang: str, key: str) -> str:
    """A hero micro-copy string localised to ``lang``, English per-key fallback."""
    return (_HERO_I18N.get(lang) or {}).get(key) or _HERO_I18N["en"][key]


# Landing tab-strip labels. Same inline-6-languages + English-fallback pattern as
# _HERO_I18N (kept here, not in the 32 i18n tables). "region" reuses the hero
# eyebrow so the tab and the hero say the same thing.
_TAB_I18N = {
    "en": {"region": "Selected region", "famous": "Famous cities", "map": "Map",
           "ranking": "Ranking",
           "ranking_cities": "City ranking", "ranking_countries": "Country ranking",
           "dashboard": "Global", "compare": "Compare", "about": "About", "report": "Report an issue"},
    "pl": {"region": "Wybrany region", "famous": "Znane miasta", "map": "Mapa",
           "ranking": "Ranking",
           "ranking_cities": "Ranking miast", "ranking_countries": "Ranking krajów",
           "dashboard": "Globalnie", "compare": "Porównaj", "about": "O danych", "report": "Zgłoś uwagę"},
    "de": {"region": "Ausgewählte Region", "famous": "Berühmte Städte", "map": "Karte",
           "ranking": "Rangliste",
           "ranking_cities": "Städte-Rangliste", "ranking_countries": "Länder-Rangliste",
           "dashboard": "Global", "compare": "Vergleich", "about": "Info", "report": "Fehler melden"},
    "fr": {"region": "Région choisie", "famous": "Villes emblématiques", "map": "Carte",
           "ranking": "Classement",
           "ranking_cities": "Classement des villes", "ranking_countries": "Classement des pays",
           "dashboard": "Global", "compare": "Comparer", "about": "À propos", "report": "Signaler"},
    "es": {"region": "Región elegida", "famous": "Ciudades famosas", "map": "Mapa",
           "ranking": "Ranking",
           "ranking_cities": "Ranking de ciudades", "ranking_countries": "Ranking de países",
           "dashboard": "Global", "compare": "Comparar", "about": "Acerca de", "report": "Reportar"},
    "uk": {"region": "Обраний регіон", "famous": "Відомі міста", "map": "Мапа",
           "ranking": "Рейтинг",
           "ranking_cities": "Рейтинг міст", "ranking_countries": "Рейтинг країн",
           "dashboard": "Глобально", "compare": "Порівняти", "about": "Про дані", "report": "Повідомити"},
}


def _tab_str(lang: str, key: str) -> str:
    """A landing tab label localised to ``lang``, English per-key fallback."""
    return (_TAB_I18N.get(lang) or {}).get(key) or _TAB_I18N["en"][key]


# "Report an issue" tab: a small form that opens a prefilled GitHub new-issue
# page (a public static site cannot hold a token to post directly). Inline langs
# + English fallback for the long tail.
_REPORT_I18N = {
    "en": {"heading": "Report an error or suggestion",
           "intro": "Spotted something wrong, or have an idea to improve the site? "
                    "Send it to us as a GitHub issue.",
           "title_lbl": "Summary", "title_ph": "e.g. Wrong warming figure for Krakow",
           "desc_lbl": "Details (optional)",
           "desc_ph": "What did you find, and where (which city, tab or chart)?",
           "submit": "Open a GitHub issue",
           "note": "This opens a prefilled issue on GitHub in a new tab; a free "
                   "GitHub account is needed to post it.",
           "thanks": "Thanks! Finish posting on the GitHub tab that just opened."},
    "pl": {"heading": "Zgłoś błąd lub sugestię",
           "intro": "Widzisz błąd albo masz pomysł na ulepszenie strony? "
                    "Wyślij go do nas jako zgłoszenie na GitHub.",
           "title_lbl": "Krótki opis", "title_ph": "np. Błędna wartość ocieplenia dla Krakowa",
           "desc_lbl": "Szczegóły (opcjonalnie)",
           "desc_ph": "Co zauważyłeś i gdzie (które miasto, zakładka lub wykres)?",
           "submit": "Otwórz zgłoszenie na GitHub",
           "note": "Otworzy się wstępnie wypełnione zgłoszenie na GitHub w nowej "
                   "karcie; do wysłania potrzebne jest darmowe konto GitHub.",
           "thanks": "Dzięki! Dokończ wysyłanie na karcie GitHub, która się otworzyła."},
    "de": {"heading": "Fehler oder Vorschlag melden",
           "intro": "Etwas falsch entdeckt oder eine Idee zur Verbesserung? "
                    "Senden Sie es uns als GitHub-Issue.",
           "title_lbl": "Zusammenfassung", "title_ph": "z. B. Falscher Erwärmungswert für Krakau",
           "desc_lbl": "Details (optional)",
           "desc_ph": "Was haben Sie gefunden, und wo (welche Stadt, welcher Tab oder welches Diagramm)?",
           "submit": "GitHub-Issue öffnen",
           "note": "Öffnet ein vorausgefülltes Issue auf GitHub in einem neuen Tab; "
                   "zum Posten wird ein kostenloses GitHub-Konto benötigt.",
           "thanks": "Danke! Bitte im soeben geöffneten GitHub-Tab absenden."},
    "fr": {"heading": "Signaler une erreur ou une suggestion",
           "intro": "Vous avez repéré une erreur ou avez une idée pour améliorer le site ? "
                    "Envoyez-la sous forme de ticket GitHub.",
           "title_lbl": "Résumé", "title_ph": "ex. Valeur de réchauffement erronée pour Cracovie",
           "desc_lbl": "Détails (facultatif)",
           "desc_ph": "Qu'avez-vous trouvé, et où (quelle ville, quel onglet ou graphique) ?",
           "submit": "Ouvrir un ticket GitHub",
           "note": "Ouvre un ticket prérempli sur GitHub dans un nouvel onglet ; "
                   "un compte GitHub gratuit est nécessaire pour l'envoyer.",
           "thanks": "Merci ! Terminez l'envoi dans l'onglet GitHub qui vient de s'ouvrir."},
    "es": {"heading": "Informar de un error o sugerencia",
           "intro": "¿Has visto algo incorrecto o tienes una idea para mejorar el sitio? "
                    "Envíanoslo como incidencia en GitHub.",
           "title_lbl": "Resumen", "title_ph": "p. ej. Valor de calentamiento incorrecto para Cracovia",
           "desc_lbl": "Detalles (opcional)",
           "desc_ph": "¿Qué encontraste y dónde (qué ciudad, pestaña o gráfico)?",
           "submit": "Abrir una incidencia en GitHub",
           "note": "Abre una incidencia rellenada previamente en GitHub en una pestaña nueva; "
                   "se necesita una cuenta gratuita de GitHub para publicarla.",
           "thanks": "¡Gracias! Termina de publicarla en la pestaña de GitHub que se abrió."},
    "uk": {"heading": "Повідомити про помилку чи пропозицію",
           "intro": "Помітили щось не так або маєте ідею для покращення сайту? "
                    "Надішліть нам як issue на GitHub.",
           "title_lbl": "Стислий опис", "title_ph": "напр. Хибне значення потепління для Кракова",
           "desc_lbl": "Деталі (необовʼязково)",
           "desc_ph": "Що ви знайшли і де (яке місто, вкладка чи графік)?",
           "submit": "Відкрити issue на GitHub",
           "note": "Відкриє попередньо заповнене issue на GitHub у новій вкладці; "
                   "для надсилання потрібен безкоштовний акаунт GitHub.",
           "thanks": "Дякуємо! Завершіть надсилання у вкладці GitHub, що відкрилася."},
}


def _report_str(lang: str, key: str) -> str:
    return (_REPORT_I18N.get(lang) or {}).get(key) or _REPORT_I18N["en"][key]


# The "About" tab's Q&A: how the site works and how the data were gathered. The
# methodology is the same in every language, so the body is English (matching the
# English-fallback policy for the long tail); only the tab label is localised.
_ABOUT_HEADING_EN = "How this works"
_ABOUT_INTRO_EN = ("How the data behind these charts were gathered, and what the "
                   "numbers mean.")
_ABOUT_QA = [
    ("What does this site show?",
     "How the world's major cities have warmed since 1940. Every city gets its "
     "long-term temperature trend, its warming since 1940, its decade-by-decade "
     "pattern, and its rank among all covered cities."),
    ("Where does the data come from?",
     "The <a href=\"https://open-meteo.com/\" rel=\"noopener\">Open-Meteo</a> "
     "historical weather API, which serves the <strong>ERA5 climate "
     "reanalysis</strong> produced by ECMWF and Copernicus. It is free and "
     "key-less. Each city uses the daily mean near-surface air temperature (the "
     "air about 2 metres above the ground, the meteorological standard height) at "
     "its location, from 1&nbsp;January&nbsp;1940 to the last complete calendar year."),
    ("What is a \"reanalysis\"?",
     "A physically consistent reconstruction of past weather: a weather model is "
     "constrained by the historical observations (stations, ships, balloons, "
     "satellites) to produce temperatures everywhere on a regular grid (about "
     "25&nbsp;km), even where no station ever stood. It is the standard way "
     "climate scientists study long-term change."),
    ("Why is there no data before 1940?",
     "ERA5, the reanalysis this site uses, currently reaches back to 1940 "
     "(ECMWF is gradually extending it to earlier decades). Starting in 1940 also "
     "gives every city the same consistent record of about 85 years, which is long "
     "enough to measure a robust warming trend."),
    ("How do I read the charts?",
     "The recurring ones share a simple grammar. The decade area chart and the "
     "warming stripes show each decade compared with the 1961&#8211;1990 average: "
     "cool blue below it, warm red above it, so a run of red to the right is recent "
     "warming. A trend in <strong>°C&nbsp;/&nbsp;decade</strong> is how fast a place "
     "is warming; the total since 1940 is how much it has warmed overall. Each chart "
     "also has a short caption under it explaining what it shows."),
    ("What does the °C&nbsp;/&nbsp;decade trend mean?",
     "The slope of a straight-line fit through each year's average temperature "
     "from 1940 to today, expressed as degrees of warming per decade. "
     "A city at +0.3&nbsp;°C/decade has warmed about 2.5&nbsp;°C over "
     "the ~85-year record."),
    ("What are the decade anomalies and warming stripes?",
     "Each decade's average temperature compared with the <strong>1961–1990 "
     "baseline</strong> — the standard 30-year climate normal. A positive "
     "anomaly means that decade was warmer than the baseline. The stripes and the "
     "area charts draw these anomalies: cool blue below the baseline, warm red "
     "above it."),
    ("How is the ranking built?",
     "Cities are ordered by their warming rate (°C/decade). \"Warming faster "
     "than N%\" is a city's percentile among all covered cities. The country view "
     "aggregates each country's cities. Rank is fixed and global, so filtering or "
     "sorting never changes \"you are #123 worldwide.\""),
    ("What is \"check any place on Earth\"?",
     "The search box geocodes any place you type and pulls its own 1940– "
     "record straight from Open-Meteo, computing the trend in your browser — "
     "so even towns too small for the prebuilt set get a real, freshly computed "
     "answer."),
    ("What are the limits of this?",
     "Reanalysis is not the same as a single weather station: it is a grid-cell "
     "average, so very local effects (a specific valley, an urban heat island "
     "smaller than the cell) are smoothed out. Trends over 85 years are robust, "
     "but any single year should not be read too closely. The figures describe "
     "warming, which is one part of a changing climate."),
    ("Is it open source?",
     "Yes. The full pipeline — data fetching, trend computation and page "
     "generation — is on "
     "<a href=\"https://github.com/YASoftwareDev/temperatury\" rel=\"noopener\">"
     "GitHub</a>."),
]


# Machine-translated About Q&A for every language (tools/gen_about.py):
# {lang: {"heading","intro","q0","a0",...}}. Layered under the English source
# with per-item fallback, so a missing language or key just shows English.
_ABOUT_MT: dict[str, dict] = {}
_about_mt_path = os.path.join(os.path.dirname(__file__), "i18n_data", "_about.json")
if os.path.exists(_about_mt_path):
    with open(_about_mt_path, encoding="utf-8") as _f:
        _ABOUT_MT = json.load(_f)


def _about_html(tr: dict, lang: str) -> str:
    """The About/Q&A tab body: methodology localised via the machine-translated
    _about.json (English per-item fallback)."""
    block = _ABOUT_MT.get(lang) or {}
    heading = block.get("heading") or tr.get("about_heading", _ABOUT_HEADING_EN)
    intro = block.get("intro") or tr.get("about_intro", _ABOUT_INTRO_EN)
    # data-tprose: this page ships no i18n runtime, so charts.js re-derives these
    # answers from their pristine Celsius markup on a °C/°F switch - a unit swap
    # for all of them, plus the worked example's numbers (see BAKED_C.about_a5).
    items = "".join(
        f'<div class="qa">'
        f'<h3 class="qa-q" data-tprose="about_q{i}">{block.get(f"q{i}") or q}</h3>'
        f'<p class="qa-a" data-tprose="about_a{i}">{block.get(f"a{i}") or a}</p>'
        f'</div>'
        for i, (q, a) in enumerate(_ABOUT_QA))
    return (f'<div class="about-wrap"><h2 class="dash-h2">{_esc(heading)}</h2>'
            f'<p class="section-sub">{_esc(intro)}</p>{items}</div>')


# "Did you know" fact templates. charts.js computes each number from the loaded
# ranking (window.__gd) and fills the {placeholders}; every figure is real data.
# {city}/{country} are localised client-side; {b}/{/b} bracket the emphasised
# number (charts.js turns them into <b> nodes, so no markup is ever injected).
_DYK_I18N = {
    "en": {"label": "Did you know?",
           "fastest_city": "{city} is warming fastest of all — {b}{v} °C{/b} per decade.",
           "over2": "{b}{n}{/b} of {total} cities have warmed more than {b}2 °C{/b} since 1940.",
           "avg_since": "The average city has warmed {b}{v} °C{/b} since 1940.",
           "faster_world": "{b}{pct}%{/b} of cities warm faster than the world-city average.",
           "fastest_country": "{country} is the fastest-warming country — {b}{v} °C{/b} per decade."},
    "pl": {"label": "Czy wiesz, że?",
           "fastest_city": "{city} ociepla się najszybciej ze wszystkich — {b}{v} °C{/b} na dekadę.",
           "over2": "{b}{n}{/b} z {total} miast ociepliło się o ponad {b}2 °C{/b} od 1940.",
           "avg_since": "Przeciętne miasto ociepliło się o {b}{v} °C{/b} od 1940.",
           "faster_world": "{b}{pct}%{/b} miast ociepla się szybciej niż średnia światowa.",
           "fastest_country": "{country} to najszybciej ocieplający się kraj — {b}{v} °C{/b} na dekadę."},
    "de": {"label": "Wusstest du?",
           "fastest_city": "{city} erwärmt sich am schnellsten — {b}{v} °C{/b} pro Jahrzehnt.",
           "over2": "{b}{n}{/b} von {total} Städten haben sich seit 1940 um mehr als {b}2 °C{/b} erwärmt.",
           "avg_since": "Die durchschnittliche Stadt hat sich seit 1940 um {b}{v} °C{/b} erwärmt.",
           "faster_world": "{b}{pct}%{/b} der Städte erwärmen sich schneller als der Weltstädte-Schnitt.",
           "fastest_country": "{country} ist das Land mit der schnellsten Erwärmung — {b}{v} °C{/b} pro Jahrzehnt."},
    "fr": {"label": "Le saviez-vous ?",
           "fastest_city": "{city} se réchauffe le plus vite de toutes — {b}{v} °C{/b} par décennie.",
           "over2": "{b}{n}{/b} villes sur {total} se sont réchauffées de plus de {b}2 °C{/b} depuis 1940.",
           "avg_since": "La ville moyenne s'est réchauffée de {b}{v} °C{/b} depuis 1940.",
           "faster_world": "{b}{pct}%{/b} des villes se réchauffent plus vite que la moyenne mondiale.",
           "fastest_country": "{country} est le pays qui se réchauffe le plus vite — {b}{v} °C{/b} par décennie."},
    "es": {"label": "¿Sabías que?",
           "fastest_city": "{city} es la que más rápido se calienta — {b}{v} °C{/b} por década.",
           "over2": "{b}{n}{/b} de {total} ciudades se han calentado más de {b}2 °C{/b} desde 1940.",
           "avg_since": "La ciudad media se ha calentado {b}{v} °C{/b} desde 1940.",
           "faster_world": "El {b}{pct}%{/b} de las ciudades se calienta más rápido que la media mundial.",
           "fastest_country": "{country} es el país que más rápido se calienta — {b}{v} °C{/b} por década."},
    "uk": {"label": "Чи знаєте ви?",
           "fastest_city": "{city} теплішає найшвидше з усіх — {b}{v} °C{/b} за десятиліття.",
           "over2": "{b}{n}{/b} з {total} міст потепліли більш ніж на {b}2 °C{/b} від 1940.",
           "avg_since": "Пересічне місто потеплішало на {b}{v} °C{/b} від 1940.",
           "faster_world": "{b}{pct}%{/b} міст теплішають швидше за середню по світу.",
           "fastest_country": "{country} — країна, що теплішає найшвидше — {b}{v} °C{/b} за десятиліття."},
}


def _dyk_dict(lang: str) -> dict:
    """The 'Did you know' label + fact templates for ``lang``, English per-key
    fallback (so a partially-translated language still shows complete facts)."""
    base = dict(_DYK_I18N["en"])
    base.update({k: v for k, v in (_DYK_I18N.get(lang) or {}).items() if v})
    return base


def _stripe_rgb(v: float | None) -> tuple[int, int, int]:
    """Anomaly (degC) -> warming-stripe colour, matching charts.js luStripeColor:
    blue (-1.0) through white (0) to deep red (+1.5)."""
    if v is None:
        return (150, 150, 150)
    lo, hi = -1.0, 1.5
    x = max(lo, min(hi, v))
    if x < 0:
        k = (x - lo) / (0 - lo)
        a, b = (8, 48, 107), (247, 247, 247)
    else:
        k = x / hi
        a, b = (247, 247, 247), (103, 0, 13)
    return (round(a[0] + (b[0] - a[0]) * k),
            round(a[1] + (b[1] - a[1]) * k),
            round(a[2] + (b[2] - a[2]) * k))


def _stripe_gradient_css(st: list) -> str:
    """A city's decade anomalies -> a hard-stop CSS linear-gradient of warming
    stripes (cool 1940s on the left, warm today on the right), used as the hero
    backdrop. Mirrors the client-side builder in charts.js so the server default
    and the geolocated city look identical."""
    st = st or []
    n = len(st) or 1
    stops = []
    for i, v in enumerate(st):
        r, g, b = _stripe_rgb(v)
        stops.append(f"rgb({r},{g},{b}) {i * 100 / n:.2f}% {(i + 1) * 100 / n:.2f}%")
    return "linear-gradient(96deg," + ",".join(stops) + ")" if stops else "none"


def _decade_anomalies(means, baseline) -> list:
    """Nine decade-mean anomalies (degC vs the 1961-1990 baseline), 1940s..2020s,
    None where a decade has no data - the same series the map card draws, but
    computed from this city's own annual means."""
    out = []
    for d0 in range(1940, 2030, 10):
        yrs = means[(means.index >= d0) & (means.index < d0 + 10)]
        out.append(round(float(yrs.mean() - baseline), 2) if len(yrs) else None)
    return out


def _hero_spark_svg(decades: list, alt: str = "") -> str:
    """The decade anomalies as a filled area chart for the city-page hero, in the
    same visual language as the map quick-view card. Colours come from CSS classes
    (currentColor + --warm/--cool via .warm/.cool), so a theme switch re-colours it
    with no JS. Warm/cool by the sign of the latest decade; nulls are skipped."""
    pts = [(i, v) for i, v in enumerate(decades) if v is not None]
    if len(pts) < 2:
        return ""
    W, H, padX, padT, padB = 880, 132, 6, 12, 12
    vals = [v for _, v in pts]
    lo = min(vals + [0.0])
    hi = max(vals + [0.001])
    rng = (hi - lo) or 1
    iw = W - 2 * padX
    ih = H - padT - padB
    span = (len(decades) - 1) or 1

    def X(i):
        return padX + i * (iw / span)

    def Y(v):
        return padT + ih - ((v - lo) / rng) * ih

    lv = pts[-1][1]
    cls = "warm" if lv >= 0 else "cool"
    zero = f"{Y(0):.1f}"
    poly = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in pts)
    x0, xn = f"{X(pts[0][0]):.1f}", f"{X(pts[-1][0]):.1f}"
    return (
        f'<svg class="rh-spark {cls}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{_esc(alt)}">'
        f'<line class="rh-spark-base" x1="{padX}" y1="{zero}" x2="{W - padX}" y2="{zero}"/>'
        '<defs><linearGradient id="rhg" x1="0" y1="0" x2="0" y2="1">'
        '<stop class="rh-spark-g0" offset="0"/>'
        '<stop class="rh-spark-g1" offset="1"/></linearGradient></defs>'
        f'<polygon class="rh-spark-fill" points="{x0},{zero} {poly} {xn},{zero}"/>'
        f'<polyline class="rh-spark-line" points="{poly}"/>'
        f'<circle class="rh-spark-dot" cx="{xn}" cy="{Y(lv):.1f}" r="4"/></svg>'
    )


def _trend_percentile(t: float, sorted_trends: list) -> int:
    """What share of cities warm slower than this one (0-100), so the hero can
    say 'warming faster than N% of the world'."""
    n = len(sorted_trends)
    if not n:
        return 0
    below = sum(1 for x in sorted_trends if x < t)
    return round(100 * below / n)


def build_map_page(
    output_dir: Path,
    locations: list[Location],
    lang: str,
    languages: list[str],
    tr: dict,
    chart_i18n: dict,
    chart_i18n_f: dict,
    meta: dict,
    total_cities: int,
    preview_locs: list | None = None,
    ranking: list | None = None,
    target_cities: int | None = None,
    city_langs: dict | None = None,
    kpis: dict | None = None,
) -> Path:
    """Write the localised landing page (index.html): the world map with climate
    zones, plus the embedded world/regional dashboard below it.

    ``preview_locs`` (preview build only) are cities we intend to cover but do
    not have data for yet; they render as faint non-interactive map dots so the
    full scale of the project is visible.

    ``tr`` carries the dashboard overlay (:func:`globaltext.overlay`); ``meta`` is
    ``{"order": [...zone keys...]}`` from :func:`globaldata.compute_global` and
    ``chart_i18n`` is that dashboard's localised label map. ``ranking`` is the
    global per-city ranking (``{s, n, t, dt, ...}``); it seeds the "your region"
    hero with the default city's warming stat so the panel is populated on first
    paint, before geolocation resolves.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tr = captions.overlay(tr, lang)
    tr = ranktext.overlay(tr, lang)
    lo, hi = BASELINE
    fmt = {"name": "", "base": f"{lo}-{hi}", "lo": lo, "hi": hi}

    # "Your region" hero, shown before (and when there is no) geolocation. Seed
    # it with the site's default city and its headline warming stat so the panel
    # renders populated with no JS, geolocation, or network request; charts.js
    # then swaps in the visitor's nearest covered city if geolocation succeeds.
    hero_eyebrow = _hero_str(lang, "eyebrow")
    # Landing tab strip: "Your region" reuses the hero eyebrow; the rest come from
    # _tab_str. The server default selects the first tab (region); charts.js
    # re-selects from the URL hash / localStorage on load.
    tab_famous = _tab_str(lang, "famous")
    _tabs = [("region", _tab_str(lang, "region")), ("famous", tab_famous),
             ("map", _tab_str(lang, "map")),
             ("ranking-cities", _tab_str(lang, "ranking_cities")),
             ("ranking-countries", _tab_str(lang, "ranking_countries")),
             ("dashboard", _tab_str(lang, "dashboard")),
             ("compare", _tab_str(lang, "compare")), ("about", _tab_str(lang, "about")),
             ("report", _tab_str(lang, "report"))]
    tabstrip = "".join(
        f'<button type="button" class="tabbtn{" active" if i == 0 else ""}" '
        f'role="tab" id="tab-{k}" data-tab="{k}" aria-controls="tp-{k}" '
        f'aria-selected="{"true" if i == 0 else "false"}" '
        f'tabindex="{"0" if i == 0 else "-1"}">{_esc(lbl)}</button>'
        for i, (k, lbl) in enumerate(_tabs))
    tabs_label = tr.get("nav_sections", "Sections")
    hero_unit = tr["per_decade_c"]
    hero_cta = _hero_str(lang, "cta")
    hero_since_tmpl = _hero_str(lang, "since")
    hero_faster_tmpl = _hero_str(lang, "faster")
    hero_locating = _hero_str(lang, "locating")
    hero_near_note = _hero_str(lang, "near")
    hero_default_note = _hero_str(lang, "default")
    # Analog line templates (localized), filled client-side for the resolved city
    # ({city}/{analog}/{d}); same strings the city pages render server-side. Left
    # empty when this language has no real translation, so the client shows no
    # analog rather than an English fallback (which scrambles under RTL).
    def _analog_tmpl(key: str) -> str:
        en = _EN_TR.get(key) or ""
        v = tr.get(key, en)
        return "" if (lang != "en" and v == en) else _esc(v or "", quote=True)
    hero_analog_past = _analog_tmpl("analog_past")
    hero_analog_future = _analog_tmpl("analog_line")
    # Quick-view card strings (dot click): reuse the hero's translated
    # sentences; {v}/{pct}/{name} are filled client-side.
    qv_json = json.dumps({
        "cta": hero_cta,
        "since": hero_since_tmpl,
        "faster": hero_faster_tmpl,
        "perDecade": tr.get("per_decade_c", "°C / decade"),
        "nodata": tr.get("qv_nodata", "No data for this city yet."),
        "nearest": tr.get("qv_nearest", "Nearest analysed city"),
        "baseline": tr.get("qv_baseline", "Decade averages vs the 1961-1990 baseline"),
        "chartAlt": tr.get("qv_chart_alt", "Decade-by-decade warming, filled area chart"),
    }, ensure_ascii=False)
    # KPI band + zone sparkline cards: the landing's headline numbers, all
    # server-rendered from the same cell-weighted series the charts draw.
    def _sparkline_svg(vals: list, color: str,
                       w: int = 220, h: int = 48, pad: int = 4) -> str:
        pts = [float(v) for v in vals if v is not None]
        if len(pts) < 2:
            return ""
        pts = pts[::max(1, len(pts) // 60)]
        lo_, hi_ = min(pts), max(pts)
        rng = (hi_ - lo_) or 1.0

        def _x(i): return pad + i * (w - 2 * pad) / (len(pts) - 1)

        def _y(v): return pad + (hi_ - v) * (h - 2 * pad) / rng
        poly = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(pts))
        zero = ""
        if lo_ <= 0 <= hi_:
            zy = _y(0.0)
            zero = (f'<line x1="{pad}" y1="{zy:.1f}" x2="{w - pad}" '
                    f'y2="{zy:.1f}" stroke="#94a3b8" stroke-width="1" '
                    f'stroke-dasharray="3 3" opacity=".6"/>')
        return (f'<svg class="zc-spark" viewBox="0 0 {w} {h}" aria-hidden="true" '
                f'preserveAspectRatio="none">{zero}<polyline points="{poly}" '
                f'fill="none" stroke="{color}" stroke-width="2"/></svg>')

    n_analysed_early = sum(
        1 for loc in locations if getattr(loc, "kind", "city") == "city")
    kpi_band = ""
    if kpis:
        _unit = tr.get("per_decade_c", "°C / decade")
        # Values are HTML here (the °C/°F machinery needs its own spans); every
        # one is a number or a unit string we produced, escaped at the source.
        _cells = [
            (f"{_t(kpis['rate'], 'delta', 2, 2)} {_u(_unit)}",
             tr.get("kpi_rate", "World warming rate")),
            (f"{_t(kpis['since'], 'delta', 1, 2, unit=True)}",
             tr.get("kpi_since", "World warming since 1940")),
            (_esc(f"{n_analysed_early} / {target_cities}") if target_cities
             else _esc(str(n_analysed_early)),
             tr.get("kpi_cities", "Cities analysed")),
            (_esc(str(kpis["wy"])),
             tr.get("kpi_warmest", "Warmest year (world average)")),
        ]
        _cells_html = "".join(
            f'<div class="kpi"><b>{v}</b><span>{_esc(l)}</span></div>'
            for v, l in _cells)
        _cards = []
        for z in kpis.get("zones", []):
            # var() so dark mode can retheme it; a plain hex inline style
            # outranks any stylesheet rule and stayed dark-on-dark.
            _col = "var(--warm)" if z["t"] >= 0 else "var(--cool)"
            _cards.append(
                f'<div class="zcard">'
                f'<span class="zc-name">{_esc(tr[_ZONE_NAME_KEY[z["key"]]])}</span>'
                + _sparkline_svg(z["spark"], _ZONE_COLOR[z["key"]])
                + f'<b class="zc-trend" style="color:{_col}">'
                  f'{_t(z["t"], "delta", 2, 2)} {_u(_unit)}</b></div>')
        kpi_band = ('<div class="kpi-band">' + _cells_html + '</div>'
                    + ('<div class="zone-cards">' + "".join(_cards) + '</div>'
                       if _cards else ''))

    # Coverage note under the map: how far the data gathering has come, with a
    # pointer to CONTRIBUTING. Both numbers are computed, never estimated; the
    # note only appears while there is actually a gap to report.
    n_analysed = n_analysed_early
    coverage_note = ""
    if target_cities and target_cities > n_analysed:
        _cov = tr.get(
            "map_coverage",
            "{done} of {total} cities analysed so far - the rest are added "
            "day by day.")
        coverage_note = (
            '<p class="map-coverage">'
            + _esc(_cov.format(done=n_analysed, total=target_cities)) + ' '
            + '<a href="https://github.com/YASoftwareDev/temperatury/blob/main/'
              'CONTRIBUTING.md" target="_blank" rel="noopener">'
            + _esc(tr.get("map_coverage_help", "Help gather the data"))
            + '</a></p>')
    _rank_by_slug = {r["s"]: r for r in (ranking or [])}
    _all_trends = sorted(r["t"] for r in (ranking or []))
    _def_loc = next((lc for lc in locations if lc.slug == DEFAULT_LOCATION), None)
    hero_default_slug = f"{DEFAULT_LOCATION}.html"
    hero_default_name = _local_name(
        DEFAULT_LOCATION, lang,
        _def_loc.name if _def_loc else DEFAULT_LOCATION.replace("-", " ").title())
    _def_rank = _rank_by_slug.get(DEFAULT_LOCATION)
    hero_default_trend = _signed(_def_rank["t"], 2) if _def_rank else ""
    hero_default_cta = hero_cta.format(name=hero_default_name)
    # The city's own warming stripes (its `st` decade anomalies -> the blue->red
    # ramp) are the hero backdrop, baked as a CSS gradient so it is there on
    # first paint; charts.js swaps it when geolocation resolves.
    hero_bg = _stripe_gradient_css(_def_rank["st"]) if _def_rank else "none"
    # Secondary line: total warming since 1940 + how the city's rate ranks
    # against every other (a percentile, computed here and re-derived client-side).
    if _def_rank:
        _pct = _trend_percentile(_def_rank["t"], _all_trends)
        _since = hero_since_tmpl.format(v=f"{_signed(_def_rank['dt'], 1)} °C")
        _faster = hero_faster_tmpl.format(pct=_pct)
        hero_default_meta = f"<b>{_since}</b> · {_faster}"
    else:
        hero_default_meta = ""
    # Data-forward hero (same idiom as the city page + the map card): the default
    # city's decade area chart on first paint; charts.js re-renders it (and the
    # axis labels) for the geolocated city. Axis ends are the actual data extent
    # (first/last decade with data), matching the city page; it hides when there
    # is no chart to sit under.
    hero_chart_alt = tr.get("qv_chart_alt",
                            "Decade-by-decade warming, filled area chart")
    _def_st = _def_rank["st"] if _def_rank else None
    _def_spark = _hero_spark_svg(_def_st, hero_chart_alt) if _def_st else ""
    _def_idx = [i for i, v in enumerate(_def_st or []) if v is not None]
    _ax_lo = 1940 + 10 * _def_idx[0] if _def_idx else 1940
    _ax_hi = 1940 + 10 * _def_idx[-1] if _def_idx else 2020
    hero_default_spark = (
        '<div class="rh-spark-wrap"><div id="rh-spark" class="rh-spark">' + _def_spark + '</div>'
        f'<div class="rh-spark-axis" id="rh-spark-axis"{"" if _def_spark else " hidden"}>'
        f'<span id="rh-axis-lo" class="rh-axis-lo">{_ax_lo}</span>'
        f'<span id="rh-axis-hi" class="rh-axis-hi">{_ax_hi}</span></div></div>'
    )

    def _title(key: str) -> str:  # per-city chart title minus its ", {name}" tail
        # Strip whatever separator precedes {name} (dash, colon, comma, ...).
        return tr[key].split("{name}")[0].format(**fmt).strip().rstrip("---:,;· ").strip()

    # Each city dot is coloured by its climate zone; the map paints matching
    # latitude bands + a legend, so the geography reads against the dashboard.
    def _dot_url_slug(slug: str) -> str:
        # Language tiering / SEO tiering: a city without a page in THIS language
        # links to its first built language (always incl. English) instead of a
        # 404. Under client-i18n that shell then auto-localizes to the visitor's
        # saved language on arrival.
        langs = (city_langs or {}).get(slug)
        if not langs or lang in langs:
            return f"{slug}.html"
        return f"../{langs[0]}/{slug}.html"

    def _dot_url(loc) -> str:
        return _dot_url_slug(loc.slug)
    markers = [
        {"n": _local_name(loc.slug, lang, loc.name), "s": _dot_url(loc),
         "lat": loc.latitude, "lon": loc.longitude, "z": zone_of(loc.latitude),
         "k": getattr(loc, "kind", "city"),
         # Geographic continent + ISO-2 country, so the map dots can be filtered
         # to a region or a single country (ocean/region points have no country).
         "r": loc.region, "cc": (countries.country_code(loc) or "")}
        for loc in locations
    ]
    # Faint dots for cities awaiting data (preview build): position + zone + a
    # localized name, so the quick-view card can say which city has no data yet.
    preview_markers = [
        {"n": _local_name(loc.slug, lang, loc.name),
         "lat": loc.latitude, "lon": loc.longitude, "z": zone_of(loc.latitude)}
        for loc in (preview_locs or [])
    ]
    zone_legend = "".join(
        f'<span class="zl"><i style="background:{_ZONE_COLOR[k]}"></i>'
        f'{tr[_ZONE_NAME_KEY[k]]}</span>'
        for k, _hi, _lo in _ZONE_BAND_DEFS
    )
    zone_bands = [{"key": k, "hi": h, "lo": lo_} for k, h, lo_ in _ZONE_BAND_DEFS]
    def _zone_button(k: str) -> str:
        # "world" is the default view and its reset: it starts active and is set
        # apart (a "Worldwide" pill, then a divider) from the climate-zone
        # filters, so it's obvious that picking a zone narrows the whole world
        # and that clicking Worldwide returns to it.
        classes = ["wb", "active"] if k == "world" else []
        cls = f' class="{" ".join(classes)}"' if classes else ""
        swatch = "" if k == "world" else f'<i style="background:{_ZONE_COLOR[k]}"></i>'
        return (f'<button type="button" data-zone="{k}"{cls}>'
                f'{swatch}{tr[_ZONE_NAME_KEY[k]]}</button>')

    _btns = []
    for _k in meta["order"]:
        _btns.append(_zone_button(_k))
        if _k == "world":
            _btns.append('<span class="zonebtns-sep" aria-hidden="true"></span>')
    zone_buttons = "".join(_btns)
    # Only real cities feed the search; reference/ocean points live on the map only.
    city_locs = [loc for loc in locations if getattr(loc, "kind", "city") == "city"]
    # Continent filter for the ranking: "all" (the world label) + each region.
    _rnames = tr.get("regions", {})
    rank_regions = f'<option value="">{tr["region_world"]}</option>' + "".join(
        f'<option value="{r}">{_rnames.get(r, r)}</option>' for r in REGIONS)
    # Continent filter for the MAP: a row of pill buttons (World, then each
    # geographic region). data-region="" is the World reset; the country <select>
    # beside it is filled client-side from the markers' ISO codes.
    def _map_region_btn(key: str, label: str, active: bool = False) -> str:
        extra = ["wb"] if key == "" else []
        if active:
            extra.append("active")
        cls = f' class="{" ".join(extra)}"' if extra else ""
        pressed = "true" if active else "false"
        return (f'<button type="button" data-region="{key}" '
                f'aria-pressed="{pressed}"{cls}>{label}</button>')

    _mbtns = [_map_region_btn("", tr["region_world"], active=True),
              '<span class="zonebtns-sep" aria-hidden="true"></span>']
    _mbtns += [_map_region_btn(r, _rnames.get(r, r)) for r in REGIONS]
    map_region_buttons = "".join(_mbtns)
    chart_js = (
        interactive.CHARTJS_INCLUDE
        + '<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-matrix@2.0.1/'
          'dist/chartjs-chart-matrix.min.js"></script>'
        + '<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.2.0/'
          'dist/chartjs-plugin-zoom.min.js"></script>'
        + '<script src="../charts.js"></script>'
    )

    _map_desc = f'{tr["site_title"]} - {tr["map_sub"]}'[:300]
    _map_jsonld = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": tr["site_title"], "description": tr["map_sub"],
        "temporalCoverage": "1940/2025",
        "variableMeasured": "Daily mean near-surface air temperature",
        "spatialCoverage": {"@type": "Place", "name": "Worldwide"},
        "creator": {"@type": "Organization", "name": _SITE_NAME},
        "isAccessibleForFree": True,
        "url": f"{SITE_BASE}/{lang}/index.html"}
    # Client-side "look up any place" labels. Static labels fill the HTML; the
    # dynamic status/result labels ride in a data-i18n JSON the browser reads.
    _lookup_labels = {
        "searching": tr.get("lookup_searching", "Finding the place..."),
        "loading": tr.get("lookup_loading", "Loading 85 years of data..."),
        "notfound": tr.get("lookup_notfound", "Place not found - try another spelling."),
        "error": tr.get("lookup_error", "Could not load data - please try again."),
        "busy": tr.get("lookup_busy", "The free climate service is over its daily "
                       "request limit right now. Please try again later."),
        "short": tr.get("lookup_short", "Not enough record for this place."),
        "since": tr.get("lookup_since", "since 1940"),
        "perdec": tr.get("lookup_perdec", "per decade"),
        "warm": tr.get("lookup_warmtrend", "warming trend"),
        "cool": tr.get("lookup_cooltrend", "cooling trend"),
        "faster": tr.get("lookup_faster", "warming faster than {pct}% of the world's cities"),
        "cooling": tr.get("lookup_cooling", "Cooling, against the global trend"),
        "news": tr.get("extreme_weather", "Extreme weather")}
    # Omni search: one box that finds cities, countries, regions or any place. The
    # city + region lists are embedded (localized) for instant offline search;
    # countries are localized client-side from the loaded ranking. Each city row is
    # [display, url, region-label, original-name?] (original kept for search only).
    _omni_cities = []
    for loc in sorted(city_locs, key=lambda l: _local_name(l.slug, lang, l.name).casefold()):
        _dn = _local_name(loc.slug, lang, loc.name)
        # Tier-aware URL (like the map dots): a city with no shell in this
        # language links to one it has, not a 404 same-folder link.
        _row = [_dn, _dot_url(loc), _rnames.get(loc.region, loc.region)]
        if _dn != loc.name:
            _row.append(loc.name)
        _omni_cities.append(_row)
    # Alias cities share a built primary's grid cell (identical record): offer each
    # as a search entry that opens the primary's page relabelled to this name via
    # a #as= hash. Only aliases whose primary actually rendered (has data) qualify,
    # so the count grows automatically as the backfill fills more primaries. These
    # are APPENDED after the real cities, so an exact-named city still ranks first.
    _built_slugs = {loc.slug for loc in city_locs}
    for _aname, _pslug, _aregion in ALIASES:
        if _pslug not in _built_slugs:
            continue
        # Resolve the PRIMARY's shell tier-aware, then relabel via #as=, so an
        # alias in a language the primary wasn't pre-rendered in still opens.
        _url = _dot_url_slug(_pslug) + "#as=" + quote(_aname)
        _omni_cities.append([_aname, _url, _rnames.get(_aregion, _aregion)])
    _omni_regions = [[r, _rnames.get(r, r)] for r in REGIONS]
    # Coordinates of every covered (data-backed) city, so a freeform "check any
    # place" lookup can snap a geocoded point to the nearest city we ALREADY have
    # data for (same grid cell -> identical record) and open that page instead of
    # firing a live 85-year fetch. Makes any place near a covered city instant and
    # quota-proof - not just the pre-listed >15k aliases. [lat, lon, slug].
    _omni_geo = [[round(loc.latitude, 3), round(loc.longitude, 3), loc.slug]
                 for loc in city_locs]
    omni_data = json.dumps({"c": _omni_cities, "r": _omni_regions, "g": _omni_geo},
                           ensure_ascii=False)
    _omni_labels = dict(_lookup_labels)
    _omni_labels.update({
        "g_cities": tr.get("omni_cities", "Cities"),
        "g_countries": tr.get("omni_countries", "Countries"),
        "g_regions": tr.get("omni_regions", "Continents"),
        "g_places": tr.get("omni_places", "Places worldwide"),
        "g_anywhere": tr.get("omni_anywhere", 'Check any place: "{q}"')})
    omni_i18n = _esc(json.dumps(_omni_labels, ensure_ascii=False), quote=True)
    omni_ph = tr.get("omni_ph", "Search a city, country, region or any place")
    html = _MAP_PAGE.substitute(
        html_lang=tr["html_lang"],
        html_dir=tr["dir"],
        title=tr["site_title"],
        og_url=f"{SITE_BASE}/{lang}/index.html",
        seo_head=_seo_head(lang, languages, "index.html", tr["site_title"],
                           _map_desc, _map_jsonld),
        omni_i18n=omni_i18n,
        omni_ph=omni_ph,
        omni_data=omni_data,
        # "Your region" hero (seeded with the default city; JS swaps in the
        # visitor's nearest covered city on geolocation).
        hero_eyebrow=hero_eyebrow,
        tabstrip=tabstrip,
        tabs_label=tabs_label,
        tab_famous=tab_famous,
        carousel_prev=_esc(tr.get("carousel_prev", "Previous city")),
        carousel_next=_esc(tr.get("carousel_next", "Next city")),
        about_html=_about_html(tr, lang),
        report_heading=_report_str(lang, "heading"),
        report_intro=_report_str(lang, "intro"),
        report_title_lbl=_report_str(lang, "title_lbl"),
        report_title_ph=_esc(_report_str(lang, "title_ph"), quote=True),
        report_desc_lbl=_report_str(lang, "desc_lbl"),
        report_desc_ph=_esc(_report_str(lang, "desc_ph"), quote=True),
        report_submit=_report_str(lang, "submit"),
        report_note=_report_str(lang, "note"),
        report_thanks=_report_str(lang, "thanks"),
        dyk_label=_esc(_dyk_dict(lang)["label"]),
        dyk_i18n=_esc(json.dumps(_dyk_dict(lang), ensure_ascii=False), quote=True),
        hero_unit=hero_unit,
        hero_cta=hero_cta,
        hero_bg=hero_bg,
        region_hint=tr.get("choose_city", "Choose a city..."),
        region_frame_title=_tab_str(lang, "region"),
        hero_since_tmpl=hero_since_tmpl,
        hero_faster_tmpl=hero_faster_tmpl,
        hero_locating=hero_locating,
        hero_near_note=hero_near_note,
        hero_default_note=hero_default_note,
        hero_analog_past=hero_analog_past,
        hero_analog_future=hero_analog_future,
        hero_default_slug=hero_default_slug,
        hero_default_name=hero_default_name,
        hero_default_trend=hero_default_trend,
        hero_default_meta=hero_default_meta,
        hero_default_spark=hero_default_spark,
        hero_chart_alt=hero_chart_alt,
        hero_default_cta=hero_default_cta,
        heading=tr["map_heading"],
        intro=tr.get("intro", ""),
        # The landing map/dashboard is still rendered per-language and loads no
        # client-i18n runtime, so its switcher navigates to sibling index pages
        # (all languages exist) rather than calling window.__setLang.
        lang_nav=_lang_nav(lang, languages, "index", in_place=False),
        # No nav links in the bar: the tabs below are the primary navigation, so
        # Ranking/Dashboard links (and the warming badge) would only duplicate them.
        topbar=_topbar(
            "index.html", _lang_nav(lang, languages, "index", in_place=False)),
        map_region_buttons=map_region_buttons,
        map_filter_label=tr.get("map_filter", "Continent or country"),
        qv_json=qv_json,
        coverage_note=coverage_note,
        kpi_band=kpi_band,
        cmp_title=tr.get("cmp_title", "Compare two cities"),
        cmp_hint=tr.get(
            "cmp_hint",
            "Each curve is that city's yearly anomaly vs its own 1961-1990 "
            "baseline, so places with different climates compare fairly."),
        cmp_city_a=tr.get("cmp_city_a", "First city"),
        cmp_city_b=tr.get("cmp_city_b", "Second city"),
        zone_color_json=json.dumps(_ZONE_COLOR),
        zone_bands_json=json.dumps(zone_bands),
        zone_legend=zone_legend,
        # Data-coverage grid overlay: toggle label, three-state legend, and the
        # per-cell tooltip template (localized; {n}/{m} filled client-side).
        grid_toggle=tr.get("grid_toggle", "Data coverage"),
        grid_all=tr.get("grid_all", "All cities have data"),
        grid_some=tr.get("grid_some", "Partly downloaded"),
        grid_none=tr.get("grid_none", "Not downloaded yet"),
        grid_tip_js=json.dumps(tr.get("grid_tip", "{n} of {m} cities with data")),
        # Basemap switch (street map vs satellite tiles).
        basemap_label=tr.get("basemap_label", "Base map"),
        basemap_map=tr.get("basemap_map", "Map"),
        basemap_terrain=tr.get("basemap_terrain", "Terrain"),
        basemap_atlas=tr.get("basemap_atlas", "Atlas"),
        basemap_sat=tr.get("basemap_sat", "Satellite"),
        chart_js=chart_js,
        global_heading=tr["global_heading"],
        global_intro=tr["global_intro"].format(n=f"{total_cities:,}"),
        choose_label=tr["global_choose"],
        zone_buttons=zone_buttons,
        zone0=tr[_ZONE_NAME_KEY["world"]],
        comparison_title=tr["comparison_title"],
        comparison_cap=tr["comparison_cap"],
        anomaly_title=_title("anomaly_title"),
        anomaly_cap=tr["cap_anomalies"].format(**fmt),
        stripes_title=_title("stripes_title"),
        stripes_cap=tr["cap_stripes"].format(**fmt),
        heatmap_title=_title("anom_heatmap_title"),
        heatmap_cap=tr["cap_anom_heatmap"].format(**fmt),
        rank_title=tr["rank_title"],
        rank_cities_head=_tab_str(lang, "ranking_cities"),
        rank_countries_head=_tab_str(lang, "ranking_countries"),
        rank_intro=tr["rank_intro"],
        rank_intro_countries=tr.get("rank_intro_countries",
            "Every country ranked by how fast its cities are warming on average: "
            "the trend in °C per decade over 1940-2025. Search for yours."),
        rank_legend=tr.get("rank_legend",
            "In each row: total warming since 1940, and how many times the "
            "world-city average rate a place warms (2x = twice as fast)."),
        rank_people_json=json.dumps(tr.get("rank_people", "people")),
        rank_city=tr["rank_city"],
        rank_country=tr["rank_country"],
        rank_search=tr["rank_search"],
        rank_search_countries=tr.get("rank_search_countries", "Find a country…"),
        rank_win_label=tr.get("rank_win_label", "Warming window"),
        rank_win_full=tr.get("rank_win_full", "Since 1940"),
        rank_win_recent=tr.get("rank_win_recent", "Last 50 years"),
        rank_win_note=tr.get("rank_win_note",
            "Two views of the same places: warming across the full record, and the "
            "modern rate (since 1975) that the IPCC and WMO cite - it leaves out the "
            "cool mid-century aerosol dip that steepens a full-record trend."),
        rank_empty=tr["rank_empty"],
        rank_trend=tr["per_decade_c"],
        rank_regions=rank_regions,
        cstat_title=tr["cstat_title"],
        cstat_tmpl=tr["cstat_line"],
        cstat_tmpl_cool=tr.get("cstat_cool", tr["cstat_line"]),
        cstat_default=_LANG_CC.get(lang, "us"),
        rank_more=tr["rank_more"],
        rank_note=tr.get("rank_note",
            "Only cities with 10+ years of records and a known country are "
            "ranked, so a few places with sparse data are not listed yet."),
        rank_cities=tr["rank_cities"],
        rank_countries=tr["rank_countries"],
        chart_i18n=json.dumps(chart_i18n, ensure_ascii=False),
        # Same keys, rendered for a °F reader. This page is server-composed per
        # language and ships no client dictionary, so the switch has no recipes
        # to recompose from - it picks the other baked map instead.
        chart_i18n_f=json.dumps(chart_i18n_f, ensure_ascii=False),
        months_json=json.dumps(tr["months"], ensure_ascii=False),
        chart_err_json=json.dumps(_CHART_ERR.get(lang, _CHART_ERR["en"]),
                                  ensure_ascii=False),
        fs_label_json=json.dumps(_FS_LABEL.get(lang, _FS_LABEL["en"]),
                                 ensure_ascii=False),
        rz_label_json=json.dumps(_RZ_LABEL.get(lang, _RZ_LABEL["en"]),
                                 ensure_ascii=False),
        footer=tr["footer"].format(date=dt.date.today().isoformat()),
        widget_label=_WIDGET_LABEL.get(lang, _WIDGET_LABEL["en"]),
        tpref_i18n=_tpref_i18n(tr),
        units_on="1" if _CLIENT_I18N else "0",
    )
    path = output_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    # The map's marker list (~295 KB raw / ~53 KB gzipped for the full roster)
    # goes in a SIDECAR, not inline: maplibre already loads on the first Map-tab
    # open, and the compare pickers are behind their own tab, so no visitor needs
    # these bytes to see the landing page. Fetched by __loadMapData().
    (output_dir / "_map.json").write_text(
        json.dumps({"c": markers, "p": preview_markers}, ensure_ascii=False),
        encoding="utf-8")
    return path


def write_redirect(path: Path, target: str, lang: str) -> Path:
    """Write a tiny meta-refresh page at ``path`` pointing to ``target``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_REDIRECT.substitute(target=target, lang=lang), encoding="utf-8")
    return path


def write_lang_redirect(path: Path, languages: list[str], default: str,
                        tzcc: dict, cclang: dict) -> Path:
    """Write the root redirect that auto-picks the visitor's language folder
    (saved choice → location → browser language → default)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_LANG_REDIRECT.substitute(
        supported=json.dumps(sorted(languages)),
        default=default,
        tzcc=json.dumps(tzcc, ensure_ascii=False),
        cclang=json.dumps(cclang, ensure_ascii=False),
    ), encoding="utf-8")
    return path
