"""Generate a self-contained static web page for GitHub Pages.

``build_site`` writes ``<slug>.html`` into a per-language output directory next
to the localised PNGs produced by :mod:`plots`. Each page carries a city
switcher (same language) and a language switcher (same city, sibling language
folder). No external CSS/JS/CDN — everything is inline.
"""

from __future__ import annotations

import datetime as dt
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
  <nav>${nav}</nav>
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
      <img src="${slug}_threshold-days.png" alt="">
      <figcaption>${cap_threshold}</figcaption>
    </figure>
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


def _city_nav(current: Location, nav_locations: list[Location]) -> str:
    """Pill links to every city page in the current language."""
    links = []
    for loc in nav_locations:
        cls = ' class="active"' if loc.slug == current.slug else ""
        links.append(f'<a href="{loc.slug}.html"{cls}>{loc.name}</a>')
    return "".join(links)


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
) -> Path:
    """Write ``<slug>.html`` (localised) into ``output_dir``; return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.slug
    stats = summary_stats(df)

    html = _PAGE.substitute(
        html_lang=tr["html_lang"],
        title=tr["page_title"].format(name=location.name),
        subtitle=tr["subtitle"].format(
            start=stats["start"], end=stats["end"], days=f"{stats['days']:,}",
            wy=stats["warmest_year"], wv=stats["warmest_value"],
            cy=stats["coldest_year"], cv=stats["coldest_value"],
        ),
        nav=_city_nav(location, nav_locations),
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
        cap_threshold=tr["cap_threshold"],
        hint=tr["hint"],
        footer=tr["footer"].format(date=dt.date.today().isoformat()),
        slug=slug,
    )

    path = output_dir / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


def write_redirect(path: Path, target: str, lang: str) -> Path:
    """Write a tiny meta-refresh page at ``path`` pointing to ``target``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_REDIRECT.substitute(target=target, lang=lang), encoding="utf-8")
    return path
