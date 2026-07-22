"""Interactive (Chart.js) widgets for the monthly-range and record charts.

The per-year monthly values ship once in the shared per-city
``charts/<slug>.json`` (keys ``_range``/``_records``) and are drawn client-side
from that fetch, so the reader can pick any year from the full range without the
data being duplicated into all 32 language copies of every page. Each widget's
HTML is just a shell (title, year picker, canvas); :mod:`report` inits it after
the fetch resolves.
"""

from __future__ import annotations

import pandas as pd

from plots import monthly_pivot

_MONTHS = list(range(1, 13))

# Loaded once per page (alongside the lightbox script).
CHARTJS_INCLUDE = (
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/'
    'dist/chart.umd.min.js"></script>'
)

# The widget render functions (buildRange/buildRecords/_opts) live in the shared
# assets/charts.js so they are downloaded once and cached, not inlined per page.
# The page inits each widget from its charts/<slug>.json fetch (see report._PAGE).


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


def _widget(base: str, title: str, cap: str, year_label: str,
            payload: dict, months: list,
            title_attr: str = "", cap_attr: str = "",
            year_attr: str = "") -> str:
    """Common widget shell: title, year <select>, canvas, caption.

    Only the shell is emitted here - the (language-neutral) data payload is NOT
    inlined. It ships once in the shared per-city ``charts/<slug>.json`` (under
    ``_range``/``_records``) and the page inits the widget from that fetch, so the
    ~23 KB of data is not duplicated into all 32 language copies of every page.
    ``months`` is accepted for signature symmetry; labels come from
    ``window.__cmonths`` at render time.
    """
    # The year <option> rows are NOT emitted here: the shared _page.js fills
    # them from the fetched payload's own year list (ascending, latest
    # preselected - the same rows the server used to inline). ~90 options x 2
    # widgets x 32 languages per city was a measurable slice of the site.
    return (
        f'<figure class="iwidget">'
        f'<div class="iwhead"><strong{title_attr}>{title}</strong>'
        f'<label class="ypick"><span{year_attr}>{year_label}</span>: '
        f'<select id="{base}-y"></select></label></div>'
        f'<div class="ican"><canvas id="{base}"></canvas></div>'
        f'<figcaption{cap_attr}>{cap}</figcaption>'
        f'</figure>'
    )


def range_widget_html(slug: str, title: str, cap: str, year_label: str,
                      payload: dict, months: list, **attrs) -> str:
    return _widget(f"rng-{slug}", title, cap, year_label, payload, months, **attrs)


def records_widget_html(slug: str, title: str, cap: str, year_label: str,
                        payload: dict, months: list, **attrs) -> str:
    return _widget(f"rec-{slug}", title, cap, year_label, payload, months, **attrs)
