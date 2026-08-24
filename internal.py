"""Unlisted internal data-status page (``output/internal/index.html``).

What the project has gathered so far, in one English page that the normal build
regenerates on every deploy. Nothing links to it: it is unlisted, not secret -
GitHub Pages is public and static, so there is no authentication to be had. It
carries ``robots: noindex,nofollow``, lives outside every language folder (so
the sitemap's per-language glob and the language switcher never see it) and is
absent from the shared roster the omni search index is built from. Nothing on
it would be a problem to publish: aggregate counts only, no machine identity.

Every figure is computed here from a source that exists on disk:

* the roster           - ``config.LOCATIONS`` (the same target set the coverage
                         overlay and ``tools/coverage.py`` count)
* what is covered      - presence of ``data/<slug>_<start>-<end>.tpy``, via
                         ``codec.cached_path``: byte-for-byte the rule
                         ``coveragegrid.compute_cells`` applies per cell, so the
                         page's totals and the map's cells agree by construction
* cache size / years   - ``stat().st_size`` and the ``_<start>-<end>`` stem of
                         the cached files themselves
* progress over time   - ``git log --diff-filter=A --name-only
                         --no-renames`` over ``data/``: the UTC commit date
                         each *currently present* cache file first appeared on.
                         That is what the axis says it is - when the file was
                         committed, not when the measurement was taken - and it
                         sees only a file's CURRENT name, so a re-encoded or
                         renamed cache re-dates to the commit that produced that
                         name. A shallow clone is rejected outright rather than
                         charted: its one grafted commit reports every file as an
                         addition, which would read as the whole roster landing
                         in a single day. That one walk feeds the whole Progress
                         tab: the cumulative series, the per-dataset day
                         breakdown that shows a flat coverage day was a
                         precipitation day, and the pace its arrival date is
                         extrapolated from - the only forward-looking figure on
                         the page, and labelled with the window it came from.

The coverage map is not re-implemented here: the tab frames the site's own map
page (``../<lang>/index.html?embed=1&grid=1#tab=map``), which already carries the
``charts/_coverage.json`` overlay with its zoom-aggregated levels and amber->lime
partial shading.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from collections import Counter
from html import escape as _esc
from pathlib import Path

import codec
import config
import countries

# Datasets tracked per city, in the order tools/coverage.py prints them. The
# suffix is what a cached file's stem carries after the year range.
DATASETS = [
    ("Mean temperature (historical)", ""),
    ("Precipitation", "_precip"),
    ("Extremes (daily max/min)", "_extremes"),
    ("Apparent temperature", "_apparent"),
]

_STEM_YEARS = re.compile(r"_(\d{4})-(\d{4})(?:_[a-z]+)?$")

# The same stem, kept apart because the daily breakdown needs the SUFFIX the
# generic one throws away, and the current-year files carry a different shape.
_STEM_DATASET = re.compile(r"_(\d{4})-(\d{4})(?:_([a-z]+))?$")
_STEM_CURRENT = re.compile(r"_(\d{4})_current(?:_[a-z]+)?$")

# Datasets the Progress tab breaks a day down into, in stacking order. "mean" is
# the one that means "covered" everywhere else in the build; the rest enrich
# cities that are already rendered, so they can move while coverage does not -
# which is the whole reason the tab shows them.
DS_KEYS = ("mean", "precip", "extremes", "apparent", "current", "other")
DS_LABEL = {"mean": "Mean temperature", "precip": "Precipitation",
            "extremes": "Extremes", "apparent": "Apparent temperature",
            "current": "Current year", "other": "Other"}
# Only the four that carry a colour token in landing.css get a coloured cell.
DS_COLOURED = ("mean", "precip", "extremes", "current")


def _dataset_of(name: str) -> tuple[str, str, tuple[int, int] | None]:
    """The location slug, dataset and year range a data/ file name belongs to.

    A cache kind neither stem recognises is "other" rather than dropped: a
    bucket that silently swallowed a new kind would understate the day it landed
    on. Every ``_<year>_current*`` file counts as current-year, the
    ``_current_extremes`` pairs included - one file kind more than the Overview
    tab's "Current year" row counts, because that row counts locations and this
    counts files. A name neither stem matches (the generated roster files) has
    no slug, so the roster filter drops it. The year range comes back with it so
    a caller can keep the breakdown to the window the page is built for: a cache
    left behind by an earlier window is a real file, but it is not one of the
    locations any tile on this page counts.
    """
    stem = _stem(name)
    m = _STEM_DATASET.search(stem)
    if m:
        got = m.group(3) or "mean"
        return (stem[:m.start()], got if got in DS_KEYS else "other",
                (int(m.group(1)), int(m.group(2))))
    m = _STEM_CURRENT.search(stem)
    if m:
        return stem[:m.start()], "current", None
    return "", "other", None


def _fmt(n: int) -> str:
    return f"{n:,}"


def _pct(n: int, m: int) -> float:
    return (100.0 * n / m) if m else 0.0


def _bytes(n: int) -> str:
    """Decimal units, the same units the Pages artifact budget is quoted in."""
    for unit, div in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n} B"


def _cached(data_dir: Path, stem: str) -> Path | None:
    return codec.cached_path(data_dir / f"{stem}{codec.SUFFIX}")


def _stem(name: str) -> str:
    """A cache file's name with its encoding suffix removed.

    Not ``name.split(".")[0]``: 24 roster slugs contain a dot ("st.-petersburg",
    "sault-ste.-marie", "fort-st.-john"), and splitting on the first one dropped
    16 real cache files out of the covered-year scan below.
    """
    for suffix in (codec.LEGACY_SUFFIX, codec.SUFFIX):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def collect(start_year: int, end_year: int) -> dict:
    """Every figure the page shows, read off the roster and the data directory."""
    data_dir = config.DATA_DIR
    locs = list(config.LOCATIONS.values())
    cities = [l for l in locs if getattr(l, "kind", "city") == "city"]

    # The mean file is what "covered" means everywhere in this project: it is
    # what coveragegrid counts per cell and what makes a city renderable.
    covered_path = {l.slug: _cached(data_dir, f"{l.slug}_{start_year}-{end_year}")
                    for l in locs}
    covered = {s for s, p in covered_path.items() if p is not None}
    covered_cities = sum(1 for l in cities if l.slug in covered)

    per_dataset = []
    for label, suffix in DATASETS:
        n = sum(1 for l in locs
                if _cached(data_dir, f"{l.slug}_{start_year}-{end_year}{suffix}"))
        per_dataset.append({"label": label, "n": n, "m": len(locs)})
    cur = dt.date.today().year
    n_cur = sum(1 for l in locs if _cached(data_dir, f"{l.slug}_{cur}_current"))
    per_dataset.append({"label": f"Current year ({cur})", "n": n_cur,
                        "m": len(locs)})

    # Cache weight and the covered span, from the files themselves.
    total_bytes = 0
    n_files = 0
    names: set[str] = set()
    years_lo: int | None = None
    years_hi: int | None = None
    # A checkout that has not gathered anything yet has no data/ at all. That
    # is the zero state the page is built to describe, so it must not take the
    # whole build down on its last step.
    for p in (data_dir.iterdir() if data_dir.is_dir() else ()):
        if not p.is_file():
            continue
        n_files += 1
        names.add(p.name)
        total_bytes += p.stat().st_size
        m = _STEM_YEARS.search(_stem(p.name))
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            years_lo = lo if years_lo is None else min(years_lo, lo)
            years_hi = hi if years_hi is None else max(years_hi, hi)
    mean_bytes = sum(p.stat().st_size for p in covered_path.values() if p)

    # One walk of the history for the whole tab. The daily breakdown and the
    # pace ride on the cumulative series' refusal: when a covered file cannot be
    # dated the series is not drawn, and a per-day breakdown built from the rest
    # would quietly understate exactly the days those files landed on.
    first = _first_added(names)
    progress = _progress(covered_path, first)
    daily = (_daily(first, set(config.LOCATIONS), (start_year, end_year))
             if progress else [])
    pace = _pace(daily, len(covered), len(locs)) if progress else None

    by_region: dict[str, dict] = {}
    for l in locs:
        r = by_region.setdefault(l.region, {"key": l.region, "m": 0, "n": 0})
        r["m"] += 1
        r["n"] += 1 if l.slug in covered else 0
    regions = sorted(by_region.values(), key=lambda d: -d["m"])

    by_cc: dict[str, dict] = {}
    for l in locs:
        cc = (countries.country_code(l) or "").upper()
        if not cc:
            continue          # ocean reference points and region centroids
        c = by_cc.setdefault(cc, {"cc": cc, "m": 0, "n": 0, "rc": Counter()})
        c["m"] += 1
        c["n"] += 1 if l.slug in covered else 0
        c["rc"][l.region] += 1
    for c in by_cc.values():
        c["region"] = c.pop("rc").most_common(1)[0][0]
    country_rows = sorted(by_cc.values(), key=lambda d: (-d["m"], d["cc"]))
    no_cc = sum(1 for l in locs if not countries.country_code(l))

    gaps = sorted((c for c in by_cc.values() if c["m"] - c["n"] > 0),
                  key=lambda d: (-(d["m"] - d["n"]), d["cc"]))
    empty = sorted((c for c in by_cc.values() if c["n"] == 0),
                   key=lambda d: (-d["m"], d["cc"]))

    return {
        "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "start_year": start_year, "end_year": end_year,
        "targets": len(locs), "cities": len(cities), "no_cc": no_cc,
        "covered": len(covered), "covered_cities": covered_cities,
        "datasets": per_dataset,
        "total_bytes": total_bytes, "mean_bytes": mean_bytes, "n_files": n_files,
        "years_lo": years_lo, "years_hi": years_hi,
        "regions": regions, "countries": country_rows,
        "gaps": gaps, "empty": empty,
        "progress": progress, "daily": daily, "pace": pace,
    }


def _first_added(names: set[str]) -> dict[str, int] | None:
    """UTC commit timestamp each ``data/<name>`` first appeared on.

    One walk of the history serves every figure on the Progress tab, so it is
    taken once per build and handed to the callers below. ``None`` means the
    history cannot answer at all - no repository, a walk that failed, or a
    shallow clone - and every caller turns that into a refusal to draw rather
    than into a chart it cannot source.

    A shallow clone has to be REJECTED explicitly, not detected by an empty
    result. Its single grafted commit has no parents, so every file in it reads
    as an addition and the walk returns the whole cache dated to one day - a
    one-point "series" asserting the entire roster landed at once. Verified on a
    depth-1 clone of a three-commit repository: all three files reported as
    added in the one commit, exit status 0.
    """
    def git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-c", "core.quotePath=false", *args],
                               cwd=config.ROOT, capture_output=True, text=True,
                               timeout=300)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout if r.returncode == 0 else None

    if (git("rev-parse", "--is-shallow-repository") or "true").strip() != "false":
        return None
    # --no-renames keeps the walk to tree comparison. Rename detection would
    # fold a rename into one R entry, which --diff-filter=A then drops, and it
    # has to read file CONTENTS - blobs the deploy build's blobless checkout
    # deliberately does not fetch.
    # NOT --first-parent, though it would make a merge's own additions visible:
    # it also re-dates an ordinary side-branch file to the merge that landed it,
    # which is not "the commit that first added that file" as the panel says
    # (measured on this repo: 10 tracked files change attribution). A file only
    # a merge carries stays undatable, and the completeness check in _progress
    # turns that into an honest refusal rather than a misdated point.
    log = git("log", "--diff-filter=A", "--name-only", "--no-renames",
              "--format=C %ct", "--", "data/")
    if log is None:
        return None
    first: dict[str, int] = {}
    ts = 0
    for line in log.splitlines():
        if line.startswith("C "):
            ts = int(line[2:])
            continue
        if not line.startswith("data/"):
            continue
        name = line[5:]
        if name in names:
            first[name] = ts   # log is newest-first: the last write is the earliest add
    return first


def _progress(covered_path: dict[str, Path | None],
              first: dict[str, int] | None = None) -> list[tuple[str, int]]:
    """Cumulative covered-location count by the date each cache file was committed.

    Only files present NOW are counted, so the series ends exactly on the
    roster's current covered count - a cumulative count of raw additions
    overshoots it by every file later renamed or dropped (11,300 additions
    against 7,784 files still present, measured 2026-08-22). Returns [] when
    nothing is covered, and when the history cannot date the files that are -
    the page says so rather than drawing a series it cannot source.

    Every covered file must be datable or the series is refused outright: one
    built from a subset ends BELOW the covered count, while the panel tells the
    reader its last value equals the Overview tile by construction.
    """
    want = {p.name for p in covered_path.values() if p is not None}
    if not want:
        return []
    if first is None:
        first = _first_added(want)
    if first is None:
        return []
    dated = {n: t for n, t in first.items() if n in want}
    if len(dated) != len(want):
        return []
    per: Counter = Counter()
    for t in dated.values():
        per[dt.datetime.fromtimestamp(t, dt.UTC).date().isoformat()] += 1
    out: list[tuple[str, int]] = []
    run = 0
    for day in sorted(per):
        run += per[day]
        out.append((day, run))
    return out


def _daily(first: dict[str, int] | None, slugs: set[str] | None = None,
           window: tuple[int, int] | None = None) -> list[dict]:
    """Cache files added per UTC day, split by dataset, oldest day first.

    The same walk the cumulative series uses, kept per-dataset instead of summed:
    it is what shows that a day the mean line is flat still landed hundreds of
    precipitation files, which is the question the single-line tab could not
    answer.

    Restricted to files whose slug is still on the roster and whose year range is
    the window the page is built for, so every count is in the same unit as the
    rest of the page and the mean column sums to exactly the covered total.
    Unfiltered it also counts cache files belonging to slugs that have LEFT the
    roster (3 mean files, measured 2026-08-24), and the table's own columns would
    then disagree with the tile above them.

    ``led`` is the dataset that took most of that day. The fetcher gives the
    hourly quota to whichever group runs first, so it reads the rotation rather
    than deciding anything.
    """
    if not first:
        return []
    per: dict[str, Counter] = {}
    for name, t in first.items():
        slug, ds, years = _dataset_of(name)
        if slugs is not None and slug not in slugs:
            continue
        if window is not None and years is not None and years != window:
            continue
        day = dt.datetime.fromtimestamp(t, dt.UTC).date().isoformat()
        per.setdefault(day, Counter())[ds] += 1
    out = []
    for day in sorted(per):
        c = per[day]
        row = {"day": day, "total": sum(c.values())}
        row.update({k: c.get(k, 0) for k in DS_KEYS})
        pick = [k for k in DS_COLOURED if c.get(k)]
        row["led"] = max(pick, key=lambda k: c[k]) if pick else None
        out.append(row)
    return out


# Three full turns of the three-day group rotation in tools/daily-chunk.sh: the
# hourly quota goes to whichever group leads a day, so a window that is not a
# whole number of cycles reads the rotation as a trend.
PACE_WINDOW = 9
PACE_HORIZON = 30          # days of projection drawn past the last measured day


def _pace(daily: list[dict], covered: int, targets: int,
          today: dt.date | None = None) -> dict | None:
    """Mean locations gained per day over the last ``PACE_WINDOW`` days, and
    where that lands if it holds.

    Measured against the calendar, not against the series: days on which nothing
    was committed are days at zero, and dropping them would report the pace of
    the good days as the pace of the fleet. The window ends on the build's own
    UTC day, so a fleet that stopped a week ago reads as stopped.

    ``None`` when the window gained nothing, when the roster is already complete,
    or when the history is too short to fill one window - none of those can be
    turned into an arrival date, and the panel prints what it knows instead.
    """
    if not daily or covered >= targets:
        return None
    today = today or dt.datetime.now(dt.UTC).date()
    start = today - dt.timedelta(days=PACE_WINDOW - 1)
    if dt.date.fromisoformat(daily[0]["day"]) > start:
        return None                      # the window reaches before the history
    gained = sum(r["mean"] for r in daily
                 if start <= dt.date.fromisoformat(r["day"]) <= today)
    if gained <= 0:
        return None
    per_day = gained / PACE_WINDOW
    remaining = targets - covered
    days_left = -(-remaining // per_day)          # ceil, without float surprises
    days_left = int(days_left)
    return {"window": PACE_WINDOW, "gained": gained, "per_day": per_day,
            "remaining": remaining, "days_left": days_left,
            "eta": (today + dt.timedelta(days=days_left)).isoformat(),
            "as_of": today.isoformat(), "horizon": PACE_HORIZON}


# --- rendering ---------------------------------------------------------------

def _bar(n: int, m: int) -> str:
    """A proportion as a bar, coloured the way the coverage overlay is: red at
    zero, green at complete, amber->lime in between."""
    p = _pct(n, m)
    cls = "z" if n == 0 else ("f" if n >= m else "p")
    return (f'<span class="int-bar {cls}" role="img" '
            f'aria-label="{p:.1f} percent"><i style="width:{p:.2f}%"></i></span>')


def _cov_row(label_html: str, n: int, m: int) -> str:
    return (f"<tr>{label_html}"
            f'<td class="int-num">{_fmt(m)}</td>'
            f'<td class="int-num">{_fmt(n)}</td>'
            f'<td class="int-num">{_pct(n, m):.1f}%</td>'
            f"<td>{_bar(n, m)}</td></tr>")


def _cc_cell(cc: str) -> str:
    """ISO code as the server-rendered text; the client upgrades it to the
    English country name via Intl.DisplayNames (the same source the ranking
    tables use), so no country-name table ships."""
    return (f'<td class="int-cc" data-cc="{_esc(cc)}" data-sort="{_esc(cc)}">'
            f"{_esc(cc)}</td>")


def _runway_svg(series: list[tuple[str, int]], targets: int,
                pace: dict | None) -> str:
    """The cumulative series as an inline SVG area chart, drawn against the WHOLE
    roster rather than against its own maximum.

    Scaling to the series' own top makes any rate look like an arrival: the line
    always ends in the top right corner. Scaling to the roster puts the work that
    is left on the same axis as the work that is done, which is the question the
    tab exists to answer, and it costs only that the early days sit flat near the
    bottom - which is true.

    Inline and server-drawn: pulling a chart library in for one figure would cost
    more than the whole page. Colours come from CSS custom properties, so it
    follows the theme like everything else.
    """
    if len(series) < 2 or targets <= 0:
        return ""
    days = [dt.date.fromisoformat(d) for d, _ in series]
    vals = [v for _, v in series]
    covered = vals[-1]
    W, H = 920, 320
    padL, padR, padT, padB = 68, 116, 18, 34
    iw, ih = W - padL - padR, H - padT - padB
    x0 = days[0].toordinal()
    # The projection needs room to the right of the last measured day; without a
    # pace the chart stops there.
    horizon = pace["horizon"] if pace else 0
    span = (days[-1].toordinal() + horizon - x0) or 1

    def X(ordinal):
        return padL + (ordinal - x0) * iw / span

    def Y(v):
        return padT + ih - (min(v, targets) / targets) * ih

    pts = " ".join(f"{X(d.toordinal()):.1f},{Y(v):.1f}" for d, v in zip(days, vals))
    area = (f"{X(x0):.1f},{padT + ih:.1f} {pts} "
            f"{X(days[-1].toordinal()):.1f},{padT + ih:.1f}")
    guides = []
    for k in range(5):
        v = targets * k / 4
        y = Y(v)
        guides.append(f'<line class="ic-grid" x1="{padL}" y1="{y:.1f}" '
                      f'x2="{W - padR}" y2="{y:.1f}"/>')
        guides.append(f'<text class="ic-lbl" x="{padL - 8}" y="{y + 4:.1f}" '
                      f'text-anchor="end">{_fmt(round(v))}</text>')
    gap = (f'<rect class="ic-gap" x="{padL}" y="{padT}" width="{iw}" '
           f'height="{max(0.0, Y(covered) - padT):.1f}"/>'
           f'<text class="ic-lbl" x="{padL + 10}" y="{padT + 18}">'
           f"{_fmt(targets - covered)} locations still to gather</text>")
    proj = ""
    if pace:
        end_v = covered + pace["per_day"] * horizon
        end_x = days[-1].toordinal() + horizon
        if end_v >= targets:            # stop the line where it meets the roster
            end_v = targets
            end_x = days[-1].toordinal() + pace["days_left"]
        proj = (f'<polyline class="ic-proj" points="'
                f'{X(days[-1].toordinal()):.1f},{Y(covered):.1f} '
                f'{X(end_x):.1f},{Y(end_v):.1f}"/>'
                f'<text class="ic-lbl" x="{X(end_x) + 8:.1f}" '
                f'y="{Y(end_v) + 4:.1f}">projected</text>')
    dots = "".join(f'<circle class="ic-dot" cx="{X(d.toordinal()):.1f}" '
                   f'cy="{Y(v):.1f}" r="2.6">'
                   f"<title>{d.isoformat()}: {_fmt(v)} covered, "
                   f"{_pct(v, targets):.1f}% of the roster</title></circle>"
                   for d, v in zip(days, vals))
    here = (f'<circle class="ic-dot" cx="{X(days[-1].toordinal()):.1f}" '
            f'cy="{Y(covered):.1f}" r="4.5"/>'
            f'<text class="ic-end" x="{X(days[-1].toordinal()) - 10:.1f}" '
            f'y="{Y(covered) - 14:.1f}" text-anchor="end">'
            f"{_fmt(covered)} ({_pct(covered, targets):.1f}%)</text>")
    ticks = [f'<text class="ic-lbl" x="{padL}" y="{H - 10}">'
             f"{days[0].isoformat()}</text>",
             f'<text class="ic-lbl" x="{X(days[-1].toordinal()):.1f}" y="{H - 10}" '
             f'text-anchor="middle">{days[-1].isoformat()}</text>']
    if pace:
        ticks.append(f'<text class="ic-lbl" x="{W - padR}" y="{H - 10}" '
                     f'text-anchor="end">+{horizon} d</text>')
    return (
        f'<svg class="int-chart int-run" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Locations with a committed mean cache file against the '
        f'roster of {_fmt(targets)}, {days[0].isoformat()} to '
        f'{days[-1].isoformat()}, ending at {_fmt(covered)}">'
        '<defs><linearGradient id="icg" x1="0" y1="0" x2="0" y2="1">'
        '<stop class="ic-g0" offset="0"/><stop class="ic-g1" offset="1"/>'
        "</linearGradient></defs>"
        + "".join(guides) + gap
        + f'<polygon class="ic-fill" points="{area}"/>'
        + f'<polyline class="ic-line" points="{pts}"/>'
        + proj + dots + here + "".join(ticks) + "</svg>"
    )


CADENCE_DAYS = 30          # ten turns of the rotation, and one screen wide


def _cadence_strip(daily: list[dict], today: dt.date | None = None) -> str:
    """One cell per UTC day, coloured by the dataset that led it.

    The point of the strip is the ROTATION, so the cell carries identity only -
    which group took the day - and the counts live in the table under it. A cell
    sized by volume would have to be scaled against the re-encode day, which is
    not gathering at all, and every ordinary day would collapse to a sliver.

    The strip ends on the build's own day, so days on which nothing was committed
    are drawn empty rather than skipped: a stalled fleet has to look stalled.
    """
    if not daily:
        return ""
    today = today or dt.datetime.now(dt.UTC).date()
    by = {r["day"]: r for r in daily}
    start = max(dt.date.fromisoformat(daily[0]["day"]),
                today - dt.timedelta(days=CADENCE_DAYS - 1))
    if start > today:
        return ""
    cells = []
    day = start
    while day <= today:
        r = by.get(day.isoformat())
        led = r["led"] if r else None
        parts = ", ".join(f"{DS_LABEL[k].lower()} +{_fmt(r[k])}"
                          for k in DS_COLOURED if r and r[k])
        title = (f"{day.isoformat()}: {_fmt(r['total'])} files, led by "
                 f"{DS_LABEL[led]} ({parts})" if led
                 else f"{day.isoformat()}: nothing committed")
        cells.append(f'<span class="d-{led or "none"}" '
                     f'title="{_esc(title)}"></span>')
        day += dt.timedelta(days=1)
    return (f'<div class="int-cad" role="img" aria-label="The dataset that led '
            f'each of the {len(cells)} days ending {today.isoformat()}">'
            + "".join(cells) + "</div>"
            + '<div class="int-cadnums"><span>' + start.isoformat()
            + "</span><span>one cell per UTC day, coloured by the group that "
              "led it</span><span>" + today.isoformat() + "</span></div>")


_TABS = [("overview", "Overview"), ("covmap", "Coverage map"),
         ("regions", "Regions and countries"), ("progress", "Progress"),
         ("gaps", "Gaps")]

# Small enough to inline: WAI-ARIA tab switching plus click-to-sort on the
# tables, and the ISO-code -> English-name upgrade. The landing page's own
# controller (charts.js initTabs) is not reused here because it ships inside the
# 160 KB landing runtime, and loading that runtime boots it - hero, city picker,
# roster fetches - none of which this page has a use for; its per-tab hooks also
# name the landing's own panels. It also persists the tab it selected - the
# public site's preference, not this page's; charts.js now skips that write
# while framed, so opening the Coverage map tab no longer moves it either.
_SCRIPT = """
(function () {
  var root = document.getElementById('internal-tabs');
  var tabs = [].slice.call(root.querySelectorAll('[role="tab"]'));
  var ids = tabs.map(function (t) { return t.getAttribute('data-tab'); });
  function panel(id) { return document.getElementById('tp-' + id); }
  function select(id, focus) {
    if (ids.indexOf(id) < 0) id = ids[0];
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-tab') === id;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.classList.toggle('active', on);
      t.tabIndex = on ? 0 : -1;
      var p = panel(t.getAttribute('data-tab'));
      if (p) p.hidden = !on;
      if (on && focus) t.focus();
    });
    if (window.history && history.replaceState)
      history.replaceState(null, '', '#tab=' + id);
    // The map frame is only pointed at its source once its tab is opened, so
    // landing on any other tab costs nothing.
    var f = document.getElementById('cov-frame');
    if (id === 'covmap' && f && !f.src) f.src = f.getAttribute('data-src');
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () { select(t.getAttribute('data-tab')); });
  });
  root.querySelector('[role="tablist"]').addEventListener('keydown', function (e) {
    var i = ids.indexOf((document.activeElement || {}).getAttribute
      ? document.activeElement.getAttribute('data-tab') : null);
    if (i < 0) return;
    var n = null;
    if (e.key === 'ArrowRight') n = (i + 1) % ids.length;
    else if (e.key === 'ArrowLeft') n = (i - 1 + ids.length) % ids.length;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = ids.length - 1;
    if (n === null) return;
    e.preventDefault();
    select(ids[n], true);
  });
  var m = /tab=([a-z]+)/.exec(location.hash || '');
  select(m ? m[1] : ids[0]);
  window.addEventListener('hashchange', function () {
    var h = /tab=([a-z]+)/.exec(location.hash || '');
    if (h) select(h[1]);
  });

  // ISO 3166 code -> English country name, from the browser's own data.
  var dn = null;
  try { dn = new Intl.DisplayNames(['en'], { type: 'region' }); } catch (e) {}
  if (dn) [].forEach.call(document.querySelectorAll('.int-cc[data-cc]'), function (td) {
    try {
      var n = dn.of(td.getAttribute('data-cc'));
      // data-sort follows the visible text, so the column sorts by country NAME
      // once the upgrade lands rather than by the ISO code behind it.
      if (n) { td.textContent = n; td.setAttribute('data-sort', n); }
    } catch (e) {}
  });

  // Click-to-sort. data-sort holds the comparable value (a number for every
  // numeric column, the rendered text otherwise), so sorting never has to parse
  // formatted output back.
  [].forEach.call(document.querySelectorAll('table.int-table'), function (tbl) {
    var body = tbl.tBodies[0];
    [].forEach.call(tbl.querySelectorAll('th[data-col]'), function (th) {
      th.addEventListener('click', function () {
        var col = +th.getAttribute('data-col');
        var desc = th.getAttribute('aria-sort') !== 'descending';
        [].forEach.call(tbl.querySelectorAll('th[data-col]'), function (o) {
          o.setAttribute('aria-sort', 'none');
        });
        th.setAttribute('aria-sort', desc ? 'descending' : 'ascending');
        var rows = [].slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[col].getAttribute('data-sort');
          var y = b.cells[col].getAttribute('data-sort');
          var nx = parseFloat(x), ny = parseFloat(y);
          var c = (isNaN(nx) || isNaN(ny)) ? String(x).localeCompare(String(y)) : nx - ny;
          return desc ? -c : c;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });
})();
"""

_PAGE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data status — temperatury (internal)</title>
<!-- Unlisted, not secret: nothing links here and no crawler is invited, but the
     page is served from a public static host and holds nothing that could not be
     published. -->
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<script>{boot}</script>
<link rel="stylesheet" href="../landing.css">
<!-- appearance.js is deliberately NOT loaded. It anchors its controls to
     .topbar, and with no top bar here BOTH of them fall back to the same fixed
     corner: the Appearance button's box completely covers the C/F unit
     toggle, so the toggle is hidden behind it and a mouse click is intercepted.
     It still takes keyboard focus though, and activating it there writes
     unit:"F" into the shared temperatury:appearance key, silently switching the
     PUBLIC site's units for that visitor. This page shows no temperatures and
     needs neither control; the inline bootstrap above still applies the
     visitor's saved theme. -->
</head>
<body>
<header>
  <h1>Data status</h1>
  <p class="intro">What the project has gathered so far. Rebuilt by
     <code>main.py</code> on every deploy.</p>
</header>
<main>
<p class="int-stamp">Generated {generated} &middot; coverage window
   {start_year}–{end_year} &middot; internal page, not linked from the site.</p>
<div class="tabs" id="internal-tabs">
  <div class="tabstrip" role="tablist" aria-label="Sections">{tabstrip}</div>
{panels}
</div>
</main>
<footer><p>temperatury — internal data status. Every figure on this page is
  computed at build time from the roster and the committed data cache; nothing
  here is estimated or filled in. The one exception is labelled where it appears:
  the Progress tab's pace and arrival date are arithmetic on a stated window of
  that same history, and they describe what would happen if it held, not a
  plan.</p></footer>
<script>{script}</script>
</body>
</html>
"""

# Same appearance bootstrap the public pages run, minus the unit choice (this
# page shows no temperatures): without it the page ignores a visitor's saved
# theme and flashes the light default.
_BOOT = ('(function(){try{var d=document.documentElement,p={};'
         'try{p=JSON.parse(localStorage.getItem("temperatury:appearance"))||{}}catch(e){}'
         'var os=window.matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches'
         '?"dark":"light";d.setAttribute("data-dir",p.dir||"objective");'
         'd.setAttribute("data-theme",p.theme||os);'
         'd.setAttribute("data-density",p.density||"comfortable");'
         'if(p.accent)d.setAttribute("data-accent",p.accent);'
         'if(p.font)d.setAttribute("data-font",p.font);}catch(e){}})();')


def _overview_panel(d: dict) -> str:
    kpis = [
        # The second half is targets - cities, not no_cc: they are the same 21
        # entries today, but only this way do the two halves sum to the total by
        # construction rather than by coincidence.
        ("Roster", _fmt(d["targets"]),
         f'{_fmt(d["cities"])} cities + {_fmt(d["targets"] - d["cities"])} '
         "ocean/region reference points"),
        ("With a mean cache file", _fmt(d["covered"]),
         f'{_pct(d["covered"], d["targets"]):.1f}% of the roster '
         f'({_fmt(d["covered_cities"])} cities)'),
        # "data/", not "cache": the directory also holds two generated roster
        # files (~1 MB), and mean_bytes is the COVERED mean series, not every
        # mean file on disk - 11 belong to slugs that have left the roster.
        ("Data directory", _bytes(d["total_bytes"]),
         f'{_fmt(d["n_files"])} files in data/; the {_fmt(d["covered"])} covered '
         f'mean series account for {_bytes(d["mean_bytes"])}'),
        ("Covered years",
         f'{d["years_lo"]}–{d["years_hi"]}' if d["years_lo"] else "—",
         "earliest and latest year of the dated ranges in the cache"),
    ]
    cards = "".join(
        f'<div class="int-kpi"><div class="k-lbl">{_esc(lbl)}</div>'
        f'<div class="k-val">{_esc(val)}</div>'
        f'<div class="k-sub">{_esc(sub)}</div></div>'
        for lbl, val, sub in kpis)
    rows = "".join(
        _cov_row(f'<td>{_esc(x["label"])}</td>', x["n"], x["m"])
        for x in d["datasets"])
    return f"""
  <div class="int-kpis">{cards}</div>
  <h2 class="int-h">Per-dataset coverage</h2>
  <p class="int-note">A location counts as covered for a dataset when the
     matching file exists in <code>data/</code> — the same file-existence
     test <code>tools/coverage.py</code> and the map's coverage overlay use.
     Never a live request.</p>
  <div class="int-wrap"><table class="int-table"><thead><tr>
    <th>Dataset</th><th class="int-num">Targets</th><th class="int-num">Cached</th>
    <th class="int-num">Share</th><th></th></tr></thead>
    <tbody>{rows}</tbody></table></div>
"""


def _covmap_panel(map_lang: str | None) -> str:
    if map_lang is None:
        return """
  <p class="int-note">This tab frames the site's own world map in coverage
     mode rather than drawing a second one, and this build rendered no
     language folder for it to point at. Run the build without a
     <code>TEMPERATURY_LANGS</code> restriction and the map returns; the
     figures on the other tabs are unaffected, since they are read from the
     roster and <code>data/</code> directly.</p>
"""
    src = f"../{map_lang}/index.html?embed=1&amp;grid=1#tab=map"
    return f"""
  <p class="int-note">The site's own world map, opened straight into coverage
     mode. Cells are 0.25&deg; (the reanalysis resolution) and aggregate as you
     zoom out; red means no location in the cell is downloaded, green means all
     of them are, and the amber-to-lime range in between shows how far along a
     partly-covered cell is. Source: <code>charts/_coverage.json</code>, written
     by <code>coveragegrid.py</code> in the same build as this page.</p>
  <iframe class="int-frame" id="cov-frame" title="Data coverage map"
          loading="lazy" referrerpolicy="no-referrer"
          data-src="{src}"></iframe>
  <p class="int-note">Not a second map: this frames
     <code>{_esc(map_lang)}/index.html</code> with <code>?embed=1&amp;grid=1</code>,
     which hides the public page's chrome and turns the coverage overlay on.</p>
"""


def _regions_panel(d: dict) -> str:
    rrows = "".join(
        _cov_row(f'<td data-sort="{_esc(r["key"])}">{_esc(r["key"])}</td>',
                 r["n"], r["m"])
        for r in d["regions"])
    crows = "".join(
        f"<tr>{_cc_cell(c['cc'])}"
        f'<td data-sort="{_esc(c["region"])}">{_esc(c["region"])}</td>'
        f'<td class="int-num" data-sort="{c["m"]}">{_fmt(c["m"])}</td>'
        f'<td class="int-num" data-sort="{c["n"]}">{_fmt(c["n"])}</td>'
        f'<td class="int-num" data-sort="{_pct(c["n"], c["m"]):.4f}">'
        f'{_pct(c["n"], c["m"]):.1f}%</td>'
        f'<td data-sort="{_pct(c["n"], c["m"]):.4f}">{_bar(c["n"], c["m"])}</td></tr>'
        for c in d["countries"])
    return f"""
  <h2 class="int-h">By region</h2>
  <div class="int-wrap"><table class="int-table"><thead><tr>
    <th>Region</th><th class="int-num">Targets</th><th class="int-num">Cached</th>
    <th class="int-num">Share</th><th></th></tr></thead>
    <tbody>{rrows}</tbody></table></div>
  <h2 class="int-h">By country</h2>
  <p class="int-note">{_fmt(len(d["countries"]))} countries and territories,
     largest roster first. Click a column heading to re-sort. The
     {_fmt(d["no_cc"])} roster entries with no country code are not listed
     here. A country's region is the one most of its roster
     entries fall in.</p>
  <div class="int-wrap int-scroll"><table class="int-table int-sortable"><thead><tr>
    <th data-col="0" class="int-sort" aria-sort="none">Country</th>
    <th data-col="1" class="int-sort" aria-sort="none">Region</th>
    <th data-col="2" class="int-sort int-num" aria-sort="descending">Targets</th>
    <th data-col="3" class="int-sort int-num" aria-sort="none">Cached</th>
    <th data-col="4" class="int-sort int-num" aria-sort="none">Share</th>
    <th></th></tr></thead>
    <tbody>{crows}</tbody></table></div>
"""


def _progress_panel(d: dict) -> str:
    series = d["progress"]
    if not series:
        return """
  <p class="int-note">No progress series in this build: either nothing is
     covered yet, or this checkout has no usable commit history for the cache
     files it does hold - a shallow clone, no repository, or a cache that was
     never committed. The tab has no other honest source, and nothing is
     estimated in its place.</p>
"""
    first_day, first_n = series[0]
    covered = series[-1][1]
    targets, daily, pace = d["targets"], d["daily"], d["pace"]
    remaining = targets - covered

    if pace:
        pace_kpis = [
            ("Current pace", _fmt(round(pace["per_day"])), "per day",
             f'mean of the last {pace["window"]} days, to {pace["as_of"]} '
             f'({_fmt(pace["gained"])} locations gained)'),
            ("Complete at that pace", pace["eta"], "",
             f'{_fmt(pace["days_left"])} days out - arithmetic on the window '
             "above, not a schedule"),
        ]
    else:
        # No pace is a statement about the fleet, not a gap in the page: say
        # which window came back empty rather than printing a dash.
        pace_kpis = [
            ("Current pace", "0", "per day",
             f"no location gained a mean cache file in the last "
             f"{PACE_WINDOW} days"),
            ("Complete at that pace", "none", "",
             "nothing to project from: the roster is complete, or the fleet is "
             "not adding locations"),
        ]
    kpis = [
        ("Roster covered", f"{_pct(covered, targets):.1f}%", "",
         f"{_fmt(covered)} of {_fmt(targets)} locations have a mean cache file"),
        ("Still to gather", _fmt(remaining), "",
         "locations with no mean cache file yet"),
        *pace_kpis,
    ]
    cards = "".join(
        f'<div class="int-kpi"><div class="k-lbl">{_esc(lbl)}</div>'
        f'<div class="k-val">{_esc(val)}'
        + (f'<span class="k-unit"> {_esc(unit)}</span>' if unit else "")
        + f'</div><div class="k-sub">{_esc(sub)}</div></div>'
        for lbl, val, unit, sub in kpis)

    cum, run = {}, 0
    for r in daily:
        run += r["mean"]
        cum[r["day"]] = run
    rows = "".join(
        f'<tr><td>{_esc(r["day"])}</td>'
        f'<td class="int-num">{_fmt(cum[r["day"]])}</td>'
        f'<td class="int-num">{_pct(cum[r["day"]], targets):.1f}%</td>'
        + "".join(f'<td class="int-num">'
                  + (f'+{_fmt(r[k])}' if r[k] else '<span class="int-nil">0</span>')
                  + "</td>" for k in ("mean", "precip", "extremes"))
        + "<td>" + (f'<span class="int-led d-{r["led"]}">'
                    f'{_esc(DS_LABEL[r["led"]])}</span>' if r["led"]
                    else '<span class="int-nil">-</span>') + "</td></tr>"
        for r in reversed(daily))
    legend = "".join(f'<b><i class="d-{k}"></i>{_esc(DS_LABEL[k])}</b>'
                     for k in DS_COLOURED)
    return f"""
  <h2 class="int-h">Distance to a complete roster</h2>
  <p class="int-note">Covered means the same thing here as everywhere else in
     this build: the location has a mean cache file. Precipitation, extremes and
     current-year files enrich cities that are already rendered, so they can move
     a great deal on a day coverage does not move at all - which is what the two
     panels below are for.</p>
  <div class="int-kpis">{cards}</div>
  <div class="int-goal" role="img" aria-label="{_pct(covered, targets):.1f} percent of the roster covered">
    <span class="g-done" style="width:{_pct(covered, targets):.2f}%"></span>
    <span class="g-left" style="width:{_pct(remaining, targets):.2f}%"></span>
  </div>
  <div class="int-goalnums"><span>{_fmt(covered)} gathered</span>
    <span>{_fmt(remaining)} remaining</span></div>

  <h2 class="int-h">Mean coverage against the full roster</h2>
  <p class="int-note">Each point counts roster locations whose mean cache file is
     present <em>now</em>, placed on the UTC day of the commit that first added
     that file. It measures when data landed in the repository, not when the
     measurements were taken, and it sees only a file's <em>current</em> name: a
     cache file that was re-encoded or renamed dates from the commit that
     produced the name it carries now, not from when its location was first
     gathered. The first point is therefore a cumulative total, not a starting
     line - it stands at {_fmt(first_n)} because that is what had been committed
     by {_esc(first_day)}, and the last is the same {_fmt(covered)} the Overview
     tab reports, by construction. The axis runs to the whole roster, so the band
     above the line is the work that is left; the dashed continuation extends the
     last {PACE_WINDOW} days' average and holds only while the fleet, the quota
     and the group rotation stay as they are. A re-encode dates thousands of
     files to one commit, so for the {PACE_WINDOW} days after one the pace above
     reads as gathering that never happened.</p>
  {_runway_svg(series, targets, pace)}

  <h2 class="int-h">Which group led each day</h2>
  <p class="int-note">The free tier meters by the hour and one chunk of 15
     locations across the whole window is heavy, so a run lands roughly 75
     locations before every further call comes back over-quota: whichever group
     runs first takes nearly all of it. <code>tools/daily-chunk.sh</code> rotates
     that leader by UTC day, which is why mean coverage advances on about one day
     in three and is flat - not stalled - on the other two.</p>
  {_cadence_strip(daily)}
  <div class="int-legend">{legend}</div>

  <div class="int-wrap"><table class="int-table"><thead><tr>
    <th>Commit date (UTC)</th><th class="int-num">Mean cumulative</th>
    <th class="int-num">Share of roster</th><th class="int-num">+ mean</th>
    <th class="int-num">+ precip</th><th class="int-num">+ extremes</th>
    <th>Led by</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
"""


def _gaps_panel(d: dict) -> str:
    top = d["gaps"][:30]
    grows = "".join(
        f"<tr>{_cc_cell(c['cc'])}"
        f'<td data-sort="{_esc(c["region"])}">{_esc(c["region"])}</td>'
        f'<td class="int-num" data-sort="{c["m"] - c["n"]}">{_fmt(c["m"] - c["n"])}</td>'
        f'<td class="int-num" data-sort="{c["m"]}">{_fmt(c["m"])}</td>'
        f'<td class="int-num" data-sort="{_pct(c["n"], c["m"]):.4f}">'
        f'{_pct(c["n"], c["m"]):.1f}%</td>'
        f'<td data-sort="{_pct(c["n"], c["m"]):.4f}">{_bar(c["n"], c["m"])}</td></tr>'
        for c in top)
    erows = "".join(
        f"<tr>{_cc_cell(c['cc'])}"
        f"<td>{_esc(c['region'])}</td>"
        f'<td class="int-num">{_fmt(c["m"])}</td></tr>'
        for c in d["empty"])
    rrows = "".join(
        f"<tr><td>{_esc(r['key'])}</td>"
        f'<td class="int-num">{_fmt(r["m"] - r["n"])}</td>'
        f'<td class="int-num">{_fmt(r["m"])}</td>'
        f'<td class="int-num">{_pct(r["n"], r["m"]):.1f}%</td>'
        f'<td>{_bar(r["n"], r["m"])}</td></tr>'
        for r in sorted(d["regions"], key=lambda x: -(x["m"] - x["n"])))
    n_empty = len(d["empty"])
    empty_block = ("" if not n_empty else f"""
  <h2 class="int-h">Nothing downloaded yet</h2>
  <p class="int-note">{_fmt(n_empty)} countries and territories have a roster
     entry but not one cached mean file.</p>
  <div class="int-wrap int-scroll"><table class="int-table"><thead><tr>
    <th>Country</th><th>Region</th><th class="int-num">Targets</th></tr></thead>
    <tbody>{erows}</tbody></table></div>
""")
    return f"""
  <h2 class="int-h">Largest gaps by country</h2>
  <p class="int-note">The {_fmt(len(top))} countries with the most roster
     locations still missing a mean cache file, out of
     {_fmt(len(d["gaps"]))} with any gap at all. Click a column heading to
     re-sort.</p>
  <div class="int-wrap"><table class="int-table int-sortable"><thead><tr>
    <th data-col="0" class="int-sort" aria-sort="none">Country</th>
    <th data-col="1" class="int-sort" aria-sort="none">Region</th>
    <th data-col="2" class="int-sort int-num" aria-sort="descending">Missing</th>
    <th data-col="3" class="int-sort int-num" aria-sort="none">Targets</th>
    <th data-col="4" class="int-sort int-num" aria-sort="none">Share done</th>
    <th></th></tr></thead>
    <tbody>{grows}</tbody></table></div>
  <h2 class="int-h">By region</h2>
  <div class="int-wrap"><table class="int-table"><thead><tr>
    <th>Region</th><th class="int-num">Missing</th><th class="int-num">Targets</th>
    <th class="int-num">Share done</th><th></th></tr></thead>
    <tbody>{rrows}</tbody></table></div>
{empty_block}"""


def render(d: dict, map_lang: str) -> str:
    bodies = {"overview": _overview_panel(d), "covmap": _covmap_panel(map_lang),
              "regions": _regions_panel(d), "progress": _progress_panel(d),
              "gaps": _gaps_panel(d)}
    tabstrip = "".join(
        f'<button type="button" class="tabbtn{" active" if i == 0 else ""}" '
        f'role="tab" id="tab-{k}" data-tab="{k}" aria-controls="tp-{k}" '
        f'aria-selected="{"true" if i == 0 else "false"}" '
        f'tabindex="{"0" if i == 0 else "-1"}">{_esc(lbl)}</button>'
        for i, (k, lbl) in enumerate(_TABS))
    panels = "".join(
        f'    <section class="tabpanel" role="tabpanel" id="tp-{k}" '
        f'aria-labelledby="tab-{k}" tabindex="0"'
        f'{"" if i == 0 else " hidden"}>{bodies[k]}    </section>\n'
        for i, (k, _lbl) in enumerate(_TABS))
    return _PAGE.format(boot=_BOOT, script=_SCRIPT, tabstrip=tabstrip,
                        panels=panels, generated=_esc(d["generated"]),
                        start_year=d["start_year"], end_year=d["end_year"])


def build_internal_page(output_dir: Path, start_year: int, end_year: int,
                        languages: list[str]) -> Path:
    """Write ``output/internal/index.html`` and return its path.

    ``languages`` is the set this build rendered; the coverage-map frame points
    at English when it exists (this page is English-only) and otherwise at
    whatever language the build does have, so a restricted TEMPERATURY_LANGS
    build still gets a working map instead of a broken frame. With no language
    at all there is nothing to frame, and the tab says so rather than pointing
    at an ``en/`` that was never written.
    """
    map_lang = "en" if "en" in languages else (languages[0] if languages else None)
    d = collect(start_year, end_year)
    path = output_dir / "internal" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(d, map_lang), encoding="utf-8")
    return path
