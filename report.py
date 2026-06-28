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

from config import Location
from i18n import LANG_NAMES
from plots import summary_stats

_PAGE = Template(
    """<!DOCTYPE html>
<html lang="${html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    line-height: 1.55;
  }
  header {
    padding: 2.5rem 1.5rem 1.5rem;
    text-align: center;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1px solid #1e293b;
  }
  header h1 { margin: 0 0 .35rem; font-size: clamp(1.6rem, 4vw, 2.4rem); }
  header p { margin: 0; color: #94a3b8; font-size: .95rem; }
  nav { margin-top: 1.1rem; display: flex; flex-wrap: wrap;
        gap: .5rem; justify-content: center; }
  nav a {
    color: #cbd5e1; text-decoration: none; font-size: .9rem;
    padding: .35rem .85rem; border-radius: 999px;
    border: 1px solid #334155; background: #1e293b;
  }
  nav a:hover { border-color: #64748b; }
  nav a.active { background: #2563eb; border-color: #2563eb; color: #fff; }
  nav.langs { margin-top: .6rem; }
  nav.langs a { font-size: .8rem; padding: .25rem .7rem; }
  nav.langs a.active { background: #0f766e; border-color: #0f766e; }
  .chooser { margin-top: 1.1rem; display: flex; flex-wrap: wrap;
             gap: .5rem; justify-content: center; align-items: center; }
  .chooser a {
    color: #cbd5e1; text-decoration: none; font-size: .9rem;
    padding: .35rem .85rem; border-radius: 999px;
    border: 1px solid #334155; background: #1e293b;
  }
  .chooser a:hover { border-color: #64748b; }
  .chooser select {
    background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
    border-radius: 999px; padding: .35rem .85rem; font-size: .9rem;
  }
  #map { height: 70vh; min-height: 460px; border-radius: 12px;
         border: 1px solid #334155; margin: 1.5rem 0; }
  .leaflet-popup-content a { color: #1d4ed8; font-weight: 600; }
  main { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0 2.25rem;
  }
  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
  }
  .card .label { font-size: .78rem; text-transform: uppercase;
                 letter-spacing: .04em; color: #94a3b8; }
  .card .value { font-size: 1.7rem; font-weight: 700; margin-top: .25rem; }
  .card.trend { border-color: #b91c1c; background: #2a1414; }
  .card.trend .value { color: #f87171; }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1.25rem;
  }
  figure {
    margin: 0;
    background: #f8fafc;
    border-radius: 12px;
    padding: .5rem;
    border: 1px solid #334155;
  }
  figure img { width: 100%; height: auto; display: block; border-radius: 8px; }
  figcaption { color: #475569; font-size: .85rem; padding: .5rem .25rem 0;
               text-align: center; }
  .charts figure { cursor: zoom-in; transition: transform .12s ease,
                   border-color .12s ease, box-shadow .12s ease; }
  .charts figure:hover { border-color: #64748b; transform: translateY(-2px);
                         box-shadow: 0 8px 24px rgba(0,0,0,.35); }
  .lightbox {
    position: fixed; inset: 0; z-index: 50;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 2rem; cursor: zoom-out;
    background: rgba(2, 6, 23, .93);
  }
  .lightbox[hidden] { display: none; }
  .lightbox img {
    max-width: 96vw; max-height: 88vh;
    background: #fff; border-radius: 10px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, .6);
  }
  .lightbox p { color: #cbd5e1; margin: .9rem 0 0; font-size: .95rem;
                text-align: center; }
  .lightbox .hint { color: #64748b; font-size: .8rem; margin-top: .4rem; }
  footer { text-align: center; color: #64748b; font-size: .82rem;
           padding: 2rem 1.5rem 3rem; }
  footer a { color: #93c5fd; }
</style>
</head>
<body>
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
      <img src="${slug}_monthly-heatmap.png" alt="">
      <figcaption>${cap_heatmap}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_monthly-anomaly.png" alt="">
      <figcaption>${cap_anom_heatmap}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_monthly-range.png" alt="">
      <figcaption>${cap_range}</figcaption>
    </figure>
    ${record_figure}
    <figure>
      <img src="${slug}_threshold-days.png" alt="">
      <figcaption>${cap_threshold}</figcaption>
    </figure>
    <figure>
      <img src="${slug}_volatility.png" alt="">
      <figcaption>${cap_volatility}</figcaption>
    </figure>
    ${precip_figure}
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
    """A 'back to map' link plus a dropdown of every city (scales to many)."""
    options = [f'<option value="index.html">{tr["choose_city"]}</option>']
    for loc in sorted(nav_locations, key=lambda location: location.name):
        selected = " selected" if loc.slug == current.slug else ""
        options.append(f'<option value="{loc.slug}.html"{selected}>{loc.name}</option>')
    select = (
        '<select onchange="if(this.value)location.href=this.value" '
        f'aria-label="{tr["choose_city"]}">{"".join(options)}</select>'
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
    has_records: bool = False,
    has_precip: bool = False,
) -> Path:
    """Write ``<slug>.html`` (localised) into ``output_dir``; return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.slug
    stats = summary_stats(df)
    record_figure = (
        f'<figure>\n      <img src="{slug}_monthly-records.png" alt="">\n'
        f'      <figcaption>{tr["cap_records"]}</figcaption>\n    </figure>'
        if has_records else ""
    )
    precip_figure = (
        f'<figure>\n      <img src="{slug}_precipitation.png" alt="">\n'
        f'      <figcaption>{tr["cap_precip"]}</figcaption>\n    </figure>'
        if has_precip else ""
    )

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
        cap_range=tr["cap_range"],
        record_figure=record_figure,
        cap_threshold=tr["cap_threshold"],
        cap_volatility=tr["cap_volatility"],
        precip_figure=precip_figure,
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
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         background:#0f172a; color:#e2e8f0; line-height:1.55; }
  header { padding:2.5rem 1.5rem 1.25rem; text-align:center;
           background:linear-gradient(135deg,#1e293b,#0f172a);
           border-bottom:1px solid #1e293b; }
  header h1 { margin:0 0 .35rem; font-size:clamp(1.6rem,4vw,2.4rem); }
  header p { margin:0; color:#94a3b8; font-size:.95rem; }
  nav.langs { margin-top:1rem; display:flex; flex-wrap:wrap; gap:.5rem;
              justify-content:center; }
  nav.langs a { color:#cbd5e1; text-decoration:none; font-size:.82rem;
                padding:.25rem .7rem; border-radius:999px;
                border:1px solid #334155; background:#1e293b; }
  nav.langs a.active { background:#0f766e; border-color:#0f766e; color:#fff; }
  main { max-width:1100px; margin:0 auto; padding:1.5rem; }
  .chooser { display:flex; justify-content:center; margin-bottom:.25rem; }
  .chooser select { background:#1e293b; color:#e2e8f0; border:1px solid #334155;
                    border-radius:999px; padding:.4rem 1rem; font-size:.95rem; }
  #map { height:70vh; min-height:480px; border-radius:12px;
         border:1px solid #334155; margin:1rem 0; }
  .leaflet-popup-content a { color:#1d4ed8; font-weight:600; text-decoration:none; }
  footer { text-align:center; color:#64748b; font-size:.82rem;
           padding:2rem 1.5rem 3rem; }
  footer a { color:#93c5fd; }
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
      .bindPopup('<a href="' + c.s + '">' + c.n + '</a>');
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
    options = [f'<option value="">{tr["choose_city"]}</option>']
    for loc in sorted(locations, key=lambda location: location.name):
        options.append(f'<option value="{loc.slug}.html">{loc.name}</option>')

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
