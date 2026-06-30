"""Generate a self-contained static web page for GitHub Pages.

``build_site`` writes ``<slug>.html`` into a per-language output directory next
to the localised PNGs produced by :mod:`plots`. Each page carries a city
switcher (same language) and a language switcher (same city, sibling language
folder). No external CSS/JS/CDN — everything is inline.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from string import Template

import interactive
from config import REGIONS, Location
from i18n import LANG_NAMES
from plots import summary_stats


def _grouped_options(
    locations: list[Location], current_slug: str | None, tr: dict | None = None
) -> str:
    """City <option>s grouped into <optgroup> by region (config order)."""
    region_names = (tr or {}).get("regions", {})
    by_region: dict[str, list[Location]] = {}
    for loc in locations:
        by_region.setdefault(loc.region, []).append(loc)
    out = []
    for region in REGIONS:
        cities = sorted(by_region.get(region, []), key=lambda location: location.name)
        if not cities:
            continue
        label = region_names.get(region, region)
        out.append(f'<optgroup label="{label}">')
        for loc in cities:
            sel = " selected" if loc.slug == current_slug else ""
            out.append(f'<option value="{loc.slug}.html"{sel}>{loc.name}</option>')
        out.append("</optgroup>")
    return "".join(out)

_PAGE = Template(
    """<!DOCTYPE html>
<html lang="${html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  :root {
    color-scheme: light;
    --bg: #fbfaf7;
    --ink: #232220;
    --muted: #6f6c66;
    --line: #e6e3dc;
    --accent: #c0392b;
    --serif: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype",
             Palatino, "Times New Roman", serif;
    --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
            Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  /* A thin warming-stripes band — the site's quiet climate signature. */
  body::before {
    content: ""; display: block; height: 4px;
    background: linear-gradient(90deg, #08306b, #2c7fb8, #cfe3ee,
                #fddbc7, #f4a582, #e34a33, #b2182b);
  }
  body {
    margin: 0;
    font-family: var(--sans);
    background: var(--bg);
    color: var(--ink);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  a { color: var(--accent); }
  header {
    padding: 3rem 1.5rem 1.75rem;
    text-align: center;
    border-bottom: 1px solid var(--line);
  }
  header h1 { margin: 0 0 .45rem; font-family: var(--serif); font-weight: 600;
              letter-spacing: -.01em; font-size: clamp(1.85rem, 4vw, 2.7rem); }
  header p { margin: 0; color: var(--muted); font-size: .95rem; }
  nav { margin-top: 1.1rem; display: flex; flex-wrap: wrap;
        gap: .45rem; justify-content: center; }
  nav a {
    color: var(--ink); text-decoration: none; font-size: .85rem;
    padding: .3rem .8rem; border-radius: 4px;
    border: 1px solid var(--line); background: #fff;
  }
  nav a:hover { border-color: #c2bdb2; }
  nav a.active { background: var(--ink); border-color: var(--ink); color: #fff; }
  nav.langs { margin-top: .6rem; }
  nav.langs a { font-size: .8rem; padding: .25rem .65rem; }
  nav.langs a.active { background: var(--accent); border-color: var(--accent); }
  .chooser { margin-top: 1.1rem; display: flex; flex-wrap: wrap;
             gap: .45rem; justify-content: center; align-items: center; }
  .chooser a {
    color: var(--ink); text-decoration: none; font-size: .85rem;
    padding: .3rem .8rem; border-radius: 4px;
    border: 1px solid var(--line); background: #fff;
  }
  .chooser a:hover { border-color: #c2bdb2; }
  .chooser select {
    background: #fff; color: var(--ink); border: 1px solid var(--line);
    border-radius: 4px; padding: .3rem .7rem; font-size: .9rem; font-family: inherit;
  }
  #map { height: 70vh; min-height: 460px; border-radius: 6px;
         border: 1px solid var(--line); margin: 1.5rem 0; }
  .leaflet-popup-content a { color: var(--accent); font-weight: 600; }
  main { max-width: 1080px; margin: 0 auto; padding: 2rem 1.5rem; }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1px;
    background: var(--line);
    border: 1px solid var(--line);
    border-radius: 6px;
    overflow: hidden;
    margin: .5rem 0 2.5rem;
  }
  .card { background: #fff; padding: 1.1rem 1.25rem; }
  .card .label { font-size: .72rem; text-transform: uppercase;
                 letter-spacing: .06em; color: var(--muted); }
  .card .value { font-family: var(--serif); font-size: 1.8rem; font-weight: 600;
                 margin-top: .3rem; }
  .card.trend .value { color: var(--accent); }
  details.guide { background: #fff; border: 1px solid var(--line);
                  border-radius: 6px; padding: .7rem 1.15rem; margin: 0 0 2rem; }
  details.guide summary { cursor: pointer; font-weight: 600; color: var(--ink); }
  details.guide ul { margin: .8rem 0 .3rem 1.1rem; padding: 0;
                     color: #4a4843; font-size: .9rem; }
  details.guide li { margin: .35rem 0; }
  details.guide b { color: var(--ink); }
  .iwidget { background: #fff; border: 1px solid var(--line); border-radius: 6px;
             padding: .6rem .7rem; display: flex; flex-direction: column; margin: 0; }
  .iwhead { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center;
            justify-content: space-between; color: var(--ink); padding: .2rem .25rem .4rem; }
  .iwhead strong { font-size: .95rem; font-family: var(--serif); font-weight: 600; }
  .ypick { color: var(--muted); font-size: .85rem; }
  .ypick select { background: #fff; color: var(--ink); border: 1px solid var(--line);
                  border-radius: 4px; padding: .15rem .4rem; font-size: .85rem; }
  .ican { position: relative; height: 300px; }
  .iwidget figcaption { color: var(--muted); font-size: .85rem; padding: .5rem .25rem 0;
                        text-align: center; }
  h2.section { font-family: var(--serif); font-weight: 600; font-size: 1.5rem;
               letter-spacing: -.01em; margin: 3rem 0 .25rem;
               padding-top: 1.5rem; border-top: 1px solid var(--line); }
  .section-sub { margin: 0 0 1.25rem; color: var(--muted); font-size: .92rem;
                 max-width: 60ch; }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1.5rem;
  }
  figure {
    margin: 0;
    background: #fff;
    border-radius: 6px;
    padding: .6rem;
    border: 1px solid var(--line);
  }
  figure img { width: 100%; height: auto; display: block; border-radius: 3px; }
  figcaption { color: var(--muted); font-size: .85rem; padding: .6rem .3rem .15rem;
               text-align: center; line-height: 1.45; }
  .charts figure { cursor: zoom-in; transition: border-color .15s ease,
                   box-shadow .15s ease; }
  .charts figure:hover { border-color: #c9c5bc;
                         box-shadow: 0 6px 20px rgba(0,0,0,.06); }
  .lightbox {
    position: fixed; inset: 0; z-index: 50;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 2rem; cursor: zoom-out;
    background: rgba(28, 27, 24, .92);
  }
  .lightbox[hidden] { display: none; }
  .lightbox img {
    max-width: 96vw; max-height: 88vh;
    background: #fff; border-radius: 6px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, .4);
  }
  .lightbox p { color: #f0efe9; margin: .9rem 0 0; font-size: .95rem;
                text-align: center; }
  .lightbox .hint { color: #b8b4aa; font-size: .8rem; margin-top: .4rem; }
  footer { text-align: center; color: var(--muted); font-size: .82rem;
           padding: 2.5rem 1.5rem 3.5rem; border-top: 1px solid var(--line);
           margin-top: 2.5rem; }
  footer a { color: var(--accent); }
</style>
</head>
<body>
${chart_js}
<header>
  <h1>${title}</h1>
  <p>${subtitle}</p>
  <div class="chooser">${chooser}</div>
  <nav class="langs">${lang_nav}</nav>
</header>
<main>
  <section class="stats">
    <div class="card trend">
      <div class="label">${card_trend}</div>
      <div class="value">${trend} ${trend_unit}</div>
    </div>
    <div class="card">
      <div class="label">${card_mean}</div>
      <div class="value">${mean} °C</div>
    </div>
    <div class="card">
      <div class="label">${card_warmest}</div>
      <div class="value">${warmest_year}</div>
    </div>
    <div class="card">
      <div class="label">${card_coldest}</div>
      <div class="value">${coldest_year}</div>
    </div>
  </section>

  <details class="guide">
    <summary>${guide_title}</summary>
    <ul>${guide_body}</ul>
  </details>

  <section class="charts">
    <figure>
      <img src="${slug}_yearly-trend.png" alt="">
      <figcaption>${cap_yearly}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_anomalies.png" alt="">
      <figcaption>${cap_anomalies}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_warming-stripes.png" alt="">
      <figcaption>${cap_stripes}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_monthly-heatmap.png" alt="">
      <figcaption>${cap_heatmap}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_monthly-anomaly.png" alt="">
      <figcaption>${cap_anom_heatmap}</figcaption>
    </figure>
    ${range_widget}
    ${records_widget}
    <figure>
      <img src="${slug}_threshold-days.png" alt="">
      <figcaption>${cap_threshold}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_growing-season.png" alt="">
      <figcaption>${cap_season}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_seasonal-shift.png" alt="">
      <figcaption>${cap_seasonshift}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_volatility.png" alt="">
      <figcaption>${cap_volatility}</figcaption>
    </figure>
    ${dtr_figure}
    ${precip_figure}
  </section>

  <h2 class="section">${health_heading}</h2>
  <p class="section-sub">${health_sub}</p>
  <section class="charts">
    <figure>
      <img src="${slug}_degree-days.png" alt="">
      <figcaption>${cap_degreedays}</figcaption>
    </figure>
    ${heatwave_figure}
    ${tropic_figure}
    ${coldspell_figure}
    ${heavyrain_figure}
    ${heatindex_figure}
  </section>
</main>
<footer>${footer}</footer>

<div id="lightbox" class="lightbox" hidden>
  <img id="lightbox-img" src="" alt="">
  <p id="lightbox-cap"></p>
  <p class="hint">${hint}</p>
</div>
<script>
(function () {
  var box = document.getElementById('lightbox');
  var img = document.getElementById('lightbox-img');
  var cap = document.getElementById('lightbox-cap');

  function open(figure) {
    var thumb = figure.querySelector('img');
    var caption = figure.querySelector('figcaption');
    img.src = thumb.src;
    cap.textContent = caption ? caption.textContent : '';
    box.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function close() {
    box.hidden = true;
    img.src = '';
    document.body.style.overflow = '';
  }

  document.querySelectorAll('.charts figure').forEach(function (figure) {
    figure.addEventListener('click', function () { open(figure); });
  });
  box.addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();
</script>
</body>
</html>
"""
)

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


def _city_chooser(current: Location, nav_locations: list[Location], tr: dict) -> str:
    """A 'back to map' link plus a region-grouped dropdown of every city."""
    head = f'<option value="index.html">{tr["choose_city"]}</option>'
    options = head + _grouped_options(nav_locations, current.slug, tr)
    select = (
        '<select onchange="if(this.value)location.href=this.value" '
        f'aria-label="{tr["choose_city"]}">{options}</select>'
    )
    return f'<a href="index.html">{tr["back_to_map"]}</a>{select}'


def _lang_nav(current_lang: str, languages: list[str], slug: str) -> str:
    """Pill links to the same city in each sibling-language folder."""
    links = []
    for code in languages:
        cls = ' class="active"' if code == current_lang else ""
        links.append(f'<a href="../{code}/{slug}.html"{cls}>{LANG_NAMES[code]}</a>')
    return "".join(links)


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
) -> Path:
    """Write ``<slug>.html`` (localised) into ``output_dir``; return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.slug
    stats = summary_stats(df)
    chart_js = interactive.CHARTJS_INCLUDE + interactive.SHARED_JS
    range_widget = interactive.range_widget_html(
        slug, tr["range_title"].format(name=location.name), tr["cap_range"],
        tr["year"], range_data, tr["months"])
    records_widget = (
        interactive.records_widget_html(
            slug, tr["record_title"].format(name=location.name),
            tr["cap_records"], tr["year"], records_data, tr["months"])
        if records_data else ""
    )
    precip_figure = (
        f'<figure>\n      <img src="{slug}_precipitation.png" alt="">\n'
        f'      <figcaption>{tr["cap_precip"]}</figcaption>\n    </figure>'
        if has_precip else ""
    )
    dtr_figure = (
        f'<figure>\n      <img src="{slug}_diurnal-range.png" alt="">\n'
        f'      <figcaption>{tr["cap_dtr"]}</figcaption>\n    </figure>'
        if has_dtr else ""
    )

    def _fig(name: str, cap_key: str) -> str:
        return (
            f'<figure>\n      <img src="{slug}_{name}.png" alt="">\n'
            f'      <figcaption>{tr[cap_key]}</figcaption>\n    </figure>'
        )

    # Health-impact panels, each gated on the dataset it needs.
    heatwave_figure = _fig("heatwave", "cap_heatwave") if has_dtr else ""
    tropic_figure = _fig("tropical-nights", "cap_tropic") if has_dtr else ""
    coldspell_figure = _fig("cold-spells", "cap_coldspell") if has_dtr else ""
    heavyrain_figure = _fig("heavy-rain", "cap_heavyrain") if has_precip else ""
    heatindex_figure = _fig("heat-index", "cap_heatindex") if has_appheat else ""

    html = _PAGE.substitute(
        html_lang=tr["html_lang"],
        title=tr["page_title"].format(name=location.name),
        subtitle=tr["subtitle"].format(
            start=stats["start"], end=stats["end"], days=f"{stats['days']:,}",
            wy=stats["warmest_year"], wv=stats["warmest_value"],
            cy=stats["coldest_year"], cv=stats["coldest_value"],
        ),
        chooser=_city_chooser(location, nav_locations, tr),
        lang_nav=_lang_nav(lang, languages, slug),
        trend=f"{stats['trend_per_decade']:+.2f}",
        trend_unit=tr["per_decade_c"],
        mean=f"{stats['mean']:.1f}",
        warmest_year=stats["warmest_year"],
        coldest_year=stats["coldest_year"],
        card_trend=tr["card_trend"],
        card_mean=tr["card_mean"],
        card_warmest=tr["card_warmest"],
        card_coldest=tr["card_coldest"],
        cap_yearly=tr["cap_yearly"],
        cap_anomalies=tr["cap_anomalies"],
        cap_heatmap=tr["cap_heatmap"],
        cap_anom_heatmap=tr["cap_anom_heatmap"],
        chart_js=chart_js,
        range_widget=range_widget,
        records_widget=records_widget,
        cap_threshold=tr["cap_threshold"],
        cap_volatility=tr["cap_volatility"],
        cap_stripes=tr["cap_stripes"],
        cap_season=tr["cap_season"],
        cap_seasonshift=tr["cap_seasonshift"],
        dtr_figure=dtr_figure,
        precip_figure=precip_figure,
        health_heading=tr["health_heading"],
        health_sub=tr["health_sub"],
        cap_degreedays=tr["cap_degreedays"],
        heatwave_figure=heatwave_figure,
        tropic_figure=tropic_figure,
        coldspell_figure=coldspell_figure,
        heavyrain_figure=heavyrain_figure,
        heatindex_figure=heatindex_figure,
        guide_title=tr["guide_title"],
        guide_body=tr["guide_body"],
        hint=tr["hint"],
        footer=tr["footer"].format(date=dt.date.today().isoformat()),
        slug=slug,
    )

    path = output_dir / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


_MAP_PAGE = Template(
    """<!DOCTYPE html>
<html lang="${html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root {
    color-scheme: light;
    --bg:#fbfaf7; --ink:#232220; --muted:#6f6c66; --line:#e6e3dc; --accent:#c0392b;
    --serif: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype", Palatino,
             "Times New Roman", serif;
    --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
            Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  body::before { content:""; display:block; height:4px;
    background: linear-gradient(90deg,#08306b,#2c7fb8,#cfe3ee,#fddbc7,#f4a582,#e34a33,#b2182b); }
  body { margin:0; font-family:var(--sans); background:var(--bg); color:var(--ink);
         line-height:1.6; -webkit-font-smoothing:antialiased; }
  header { padding:3rem 1.5rem 1.5rem; text-align:center;
           border-bottom:1px solid var(--line); }
  header h1 { margin:0 0 .45rem; font-family:var(--serif); font-weight:600;
              letter-spacing:-.01em; font-size:clamp(1.85rem,4vw,2.7rem); }
  header p { margin:0; color:var(--muted); font-size:.95rem; }
  nav.langs { margin-top:1rem; display:flex; flex-wrap:wrap; gap:.45rem;
              justify-content:center; }
  nav.langs a { color:var(--ink); text-decoration:none; font-size:.82rem;
                padding:.25rem .65rem; border-radius:4px;
                border:1px solid var(--line); background:#fff; }
  nav.langs a.active { background:var(--accent); border-color:var(--accent); color:#fff; }
  main { max-width:1080px; margin:0 auto; padding:1.75rem 1.5rem; }
  .chooser { display:flex; justify-content:center; margin-bottom:.25rem; }
  .chooser select { background:#fff; color:var(--ink); border:1px solid var(--line);
                    border-radius:4px; padding:.4rem 1rem; font-size:.95rem;
                    font-family:inherit; }
  #map { height:70vh; min-height:480px; border-radius:6px;
         border:1px solid var(--line); margin:1rem 0; }
  .leaflet-popup-content a { color:var(--accent); font-weight:600; text-decoration:none; }
  footer { text-align:center; color:var(--muted); font-size:.82rem;
           padding:2.5rem 1.5rem 3.5rem; border-top:1px solid var(--line);
           margin-top:2rem; }
  footer a { color:var(--accent); }
</style>
</head>
<body>
<header>
  <h1>${heading}</h1>
  <p>${sub}</p>
  <nav class="langs">${lang_nav}</nav>
</header>
<main>
  <div class="chooser">
    <select onchange="if(this.value)location.href=this.value" aria-label="${choose}">
      ${options}
    </select>
  </div>
  <div id="map"></div>
</main>
<footer>${footer}</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var cities = ${markers};
  var map = L.map('map', { scrollWheelZoom: false }).setView([54, 15], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 12, attribution: '© OpenStreetMap'
  }).addTo(map);
  cities.forEach(function (c) {
    L.marker([c.lat, c.lon]).addTo(map)
      .bindTooltip(c.n)
      .on('click', function () { location.href = c.s; });
  });
</script>
</body>
</html>
"""
)


def build_map_page(
    output_dir: Path,
    locations: list[Location],
    lang: str,
    languages: list[str],
    tr: dict,
) -> Path:
    """Write the localised chooser page (Leaflet map + dropdown) as index.html."""
    output_dir.mkdir(parents=True, exist_ok=True)
    markers = [
        {"n": loc.name, "s": f"{loc.slug}.html",
         "lat": loc.latitude, "lon": loc.longitude}
        for loc in locations
    ]
    options = [f'<option value="">{tr["choose_city"]}</option>',
               _grouped_options(locations, None, tr)]

    html = _MAP_PAGE.substitute(
        html_lang=tr["html_lang"],
        title=tr["site_title"],
        heading=tr["map_heading"],
        sub=tr["map_sub"],
        choose=tr["choose_city"],
        lang_nav=_lang_nav(lang, languages, "index"),
        options="".join(options),
        markers=json.dumps(markers, ensure_ascii=False),
        footer=tr["footer"].format(date=dt.date.today().isoformat()),
    )
    path = output_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def write_redirect(path: Path, target: str, lang: str) -> Path:
    """Write a tiny meta-refresh page at ``path`` pointing to ``target``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_REDIRECT.substitute(target=target, lang=lang), encoding="utf-8")
    return path
