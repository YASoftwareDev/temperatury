"""Interactive (Chart.js) widgets for the monthly-range and record charts.

The per-year monthly values are embedded as inline JSON and drawn client-side
so the reader can pick any year from the full range. No external data file and
no fetch — each widget is self-contained apart from the Chart.js CDN include
(added once per page by :mod:`report`).
"""

from __future__ import annotations

import json

import pandas as pd

from plots import monthly_pivot

_MONTHS = list(range(1, 13))

# Loaded once per page (alongside the lightbox script).
CHARTJS_INCLUDE = (
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/'
    'dist/chart.umd.min.js"></script>'
)

SHARED_JS = """<script>
function _opts(months) {
  return {responsive: true, maintainAspectRatio: false,
    interaction: {intersect: false, mode: 'index'},
    plugins: {legend: {labels: {boxWidth: 12, color: '#475569'}}},
    scales: {x: {offset: true, ticks: {color: '#475569'}},
             y: {ticks: {color: '#475569'},
                 title: {display: true, text: '\\u00B0C', color: '#475569'}}}};
}
function buildRange(base, d, months) {
  var years = Object.keys(d.years);
  var initial = years[years.length - 1];
  var sel = document.getElementById(base + '-y');
  var chart = new Chart(document.getElementById(base).getContext('2d'), {
    type: 'line',
    data: {labels: months, datasets: [
      {label: 'max', data: d.max, borderColor: 'rgba(148,163,184,.6)',
       borderWidth: 1, pointRadius: 0, fill: false},
      {label: 'min', data: d.min, borderColor: 'rgba(148,163,184,.6)',
       backgroundColor: 'rgba(148,163,184,.22)', borderWidth: 1,
       pointRadius: 0, fill: '-1'},
      {label: 'avg', data: d.avg, borderColor: '#334155', borderDash: [5, 4],
       borderWidth: 1.5, pointRadius: 0},
      {label: initial, data: d.years[initial], borderColor: '#d62728',
       backgroundColor: '#d62728', showLine: false, pointRadius: 4,
       spanGaps: true}
    ]}, options: _opts(months)});
  sel.addEventListener('change', function () {
    chart.data.datasets[3].label = sel.value;
    chart.data.datasets[3].data = d.years[sel.value];
    chart.update();
  });
}
function buildRecords(base, d, months) {
  var years = Object.keys(d.years);
  var initial = years[years.length - 1];
  var sel = document.getElementById(base + '-y');
  var chart = new Chart(document.getElementById(base).getContext('2d'), {
    type: 'line',
    data: {labels: months, datasets: [
      {label: 'rec high', data: d.recHigh, borderColor: 'rgba(185,28,28,.5)',
       borderWidth: 1, pointRadius: 0, fill: false},
      {label: 'rec low', data: d.recLow, borderColor: 'rgba(29,78,216,.5)',
       backgroundColor: 'rgba(148,163,184,.18)', borderWidth: 1,
       pointRadius: 0, fill: '-1'},
      {label: initial + ' \\u25B2', data: d.years[initial].high,
       borderColor: '#d62728', backgroundColor: '#d62728', showLine: false,
       pointRadius: 4, spanGaps: true},
      {label: initial + ' \\u25BC', data: d.years[initial].low,
       borderColor: '#2c7fb8', backgroundColor: '#2c7fb8', showLine: false,
       pointRadius: 4, spanGaps: true}
    ]}, options: _opts(months)});
  sel.addEventListener('change', function () {
    var y = sel.value;
    chart.data.datasets[2].label = y + ' \\u25B2';
    chart.data.datasets[2].data = d.years[y].high;
    chart.data.datasets[3].label = y + ' \\u25BC';
    chart.data.datasets[3].data = d.years[y].low;
    chart.update();
  });
}
</script>"""


def _row(values) -> list:
    """A month row as plain floats (None for missing months)."""
    return [None if pd.isna(v) else round(float(v), 1) for v in values]


def range_payload(df: pd.DataFrame, extra: pd.DataFrame | None = None) -> dict:
    """Per-month min/max/avg envelope and every year's 12 monthly means.

    ``extra`` (the partial current year) is appended so it becomes a selectable
    year in the widget, without affecting the static trend charts that use the
    full-year frame only.
    """
    if extra is not None and not extra.empty:
        df = pd.concat([df, extra])
    pivot = monthly_pivot(df).reindex(columns=_MONTHS)
    years = {str(int(y)): _row(pivot.loc[y].to_numpy()) for y in pivot.index}
    return {
        "min": _row(pivot.min(axis=0).to_numpy()),
        "max": _row(pivot.max(axis=0).to_numpy()),
        "avg": _row(pivot.mean(axis=0).to_numpy()),
        "years": years,
    }


def records_payload(df_ext: pd.DataFrame, extra: pd.DataFrame | None = None) -> dict:
    """All-time record high/low per month and every year's monthly extremes.

    ``extra`` (the partial current year's max/min) is appended so the current
    year is selectable in the records widget.
    """
    if extra is not None and not extra.empty:
        df_ext = pd.concat([df_ext, extra])
    ym = [df_ext.index.year, df_ext.index.month]
    monthly_max = (df_ext["temperature_2m_max"].groupby(ym).max()
                   .unstack().reindex(columns=_MONTHS))
    monthly_min = (df_ext["temperature_2m_min"].groupby(ym).min()
                   .unstack().reindex(columns=_MONTHS))
    years = {
        str(int(y)): {
            "high": _row(monthly_max.loc[y].to_numpy()),
            "low": _row(monthly_min.loc[y].to_numpy()),
        }
        for y in monthly_max.index
    }
    return {
        "recHigh": _row(monthly_max.max(axis=0).to_numpy()),
        "recLow": _row(monthly_min.min(axis=0).to_numpy()),
        "years": years,
    }


def _widget(base: str, kind: str, title: str, cap: str, year_label: str,
            payload: dict, months: list) -> str:
    """Common widget shell: title, year <select>, canvas, caption, init call."""
    years = sorted(payload["years"], key=int)
    options = "".join(
        f'<option value="{y}"{" selected" if y == years[-1] else ""}>{y}</option>'
        for y in years
    )
    fn = "buildRange" if kind == "range" else "buildRecords"
    data = json.dumps(payload, ensure_ascii=False)
    labels = json.dumps(months, ensure_ascii=False)
    return (
        f'<figure class="iwidget">'
        f'<div class="iwhead"><strong>{title}</strong>'
        f'<label class="ypick">{year_label}: '
        f'<select id="{base}-y">{options}</select></label></div>'
        f'<div class="ican"><canvas id="{base}"></canvas></div>'
        f'<figcaption>{cap}</figcaption>'
        f'<script>{fn}("{base}",{data},{labels});</script>'
        f'</figure>'
    )


def range_widget_html(slug: str, title: str, cap: str, year_label: str,
                      payload: dict, months: list) -> str:
    return _widget(f"rng-{slug}", "range", title, cap, year_label, payload, months)


def records_widget_html(slug: str, title: str, cap: str, year_label: str,
                        payload: dict, months: list) -> str:
    return _widget(f"rec-{slug}", "records", title, cap, year_label, payload, months)
