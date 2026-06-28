"""Generate a self-contained static web page for GitHub Pages.

``build_site`` writes ``index.html`` into the output directory next to the
PNGs produced by :mod:`plots`, so the whole folder can be published as-is.
The page has no external CSS/JS/CDN dependencies — everything is inline, so
it renders identically offline and on Pages.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from string import Template

from config import Location
from plots import summary_stats

_PAGE = Template(
    """<!DOCTYPE html>
<html lang="en">
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
  footer { text-align: center; color: #64748b; font-size: .82rem;
           padding: 2rem 1.5rem 3rem; }
  footer a { color: #93c5fd; }
</style>
</head>
<body>
<header>
  <h1>${title}</h1>
  <p>${subtitle}</p>
</header>
<main>
  <section class="stats">
    <div class="card trend">
      <div class="label">Warming trend</div>
      <div class="value">${trend} °C / decade</div>
    </div>
    <div class="card">
      <div class="label">Mean daily temp</div>
      <div class="value">${mean} °C</div>
    </div>
    <div class="card">
      <div class="label">Warmest year</div>
      <div class="value">${warmest_year}</div>
    </div>
    <div class="card">
      <div class="label">Coldest year</div>
      <div class="value">${coldest_year}</div>
    </div>
  </section>

  <section class="charts">
    <figure>
      <img src="${slug}_yearly-trend.png" alt="Annual mean temperature trend">
      <figcaption>Annual mean temperature with least-squares trend</figcaption>
    </figure>
    <figure>
      <img src="${slug}_anomalies.png" alt="Annual temperature anomalies">
      <figcaption>Yearly anomaly vs. 1961–1990 (blue cooler, red warmer)</figcaption>
    </figure>
    <figure>
      <img src="${slug}_monthly-heatmap.png" alt="Monthly mean temperature by year">
      <figcaption>Monthly mean by year — which seasons warm</figcaption>
    </figure>
    <figure>
      <img src="${slug}_histogram.png" alt="Distribution of daily temperatures">
      <figcaption>Distribution of daily mean temperatures</figcaption>
    </figure>
  </section>
</main>
<footer>
  Generated ${generated} · data from
  <a href="https://open-meteo.com/">Open-Meteo</a> historical reanalysis (ERA5) ·
  <a href="https://github.com/YASoftwareDev/temperatury">source on GitHub</a>
</footer>
</body>
</html>
"""
)


def build_site(df, location: Location, output_dir: Path) -> Path:
    """Write ``index.html`` into ``output_dir`` and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = location.name.lower().replace(" ", "-")
    stats = summary_stats(df)

    html = _PAGE.substitute(
        title=f"{location.name} temperatures",
        subtitle=(
            f"{stats['start']}–{stats['end']} · {stats['days']:,} days · "
            f"warmest {stats['warmest_year']} "
            f"({stats['warmest_value']:.1f} °C), "
            f"coldest {stats['coldest_year']} "
            f"({stats['coldest_value']:.1f} °C)"
        ),
        trend=f"{stats['trend_per_decade']:+.2f}",
        mean=f"{stats['mean']:.1f}",
        warmest_year=stats["warmest_year"],
        coldest_year=stats["coldest_year"],
        slug=slug,
        generated=dt.date.today().isoformat(),
    )

    path = output_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
