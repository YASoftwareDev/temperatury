"""Build-time data-coverage grid for the world map.

Partitions the target set (every ``config.LOCATIONS`` entry - the same set
``tools/coverage.py`` counts and the ranking is built from) into square cells at
the Open-Meteo reanalysis resolution and records, per cell, how many of its
cities already have a committed mean data file. The map renders these cells as a
green/amber/red overlay so it is obvious which regions still need downloading.

Coverage is derived purely from the presence of committed cache files
(``data/<slug>_<start>-<end>.csv.gz``) - never from live requests - so the
overlay reflects exactly what offline processing currently covers. The result is
written once to ``charts/_coverage.json`` and coloured client-side; the browser
never recomputes cell state from the full city list.
"""
from __future__ import annotations

import math
from collections import Counter

import config
import countries

# Reanalysis cell size in degrees. Open-Meteo's archive is ERA5 (0.25 deg); this
# is the single tunable knob - raise it for a coarser overlay, lower it for a
# finer one. Cells are squares [lo, la] .. [lo+CELL, la+CELL].
CELL_DEG = 0.25


def compute_cells(start_year: int, end_year: int,
                  cell_deg: float = CELL_DEG) -> dict:
    """Aggregate every target location into ``cell_deg`` squares.

    Returns ``{"cell": cell_deg, "cells": [{la, lo, n, m, r, cc}, ...]}`` where
    ``la``/``lo`` are the cell's south-west corner, ``m`` is the number of target
    cities in the cell and ``n`` how many of them have a mean data file. ``r`` and
    ``cc`` are the cell's dominant region and country so the map's existing
    region/country filters keep working in the grid view. Only cells containing at
    least one target city are emitted, so the overlay is sparse.
    """
    data_dir = config.DATA_DIR
    cells: dict[tuple[int, int], dict] = {}
    for loc in config.LOCATIONS.values():
        i = math.floor(loc.latitude / cell_deg)
        j = math.floor(loc.longitude / cell_deg)
        cell = cells.setdefault((i, j),
                                {"m": 0, "n": 0, "r": Counter(), "cc": Counter()})
        cell["m"] += 1
        # Same file-existence test as tools/coverage.py, so per-cell counts sum to
        # its totals exactly (no live request, no dependency on the render list).
        if (data_dir / f"{loc.slug}_{start_year}-{end_year}.csv.gz").exists():
            cell["n"] += 1
        cell["r"][loc.region] += 1
        cc = countries.country_code(loc) or ""
        if cc:
            cell["cc"][cc] += 1

    out = []
    for (i, j), cell in cells.items():
        out.append({
            "la": round(i * cell_deg, 4),
            "lo": round(j * cell_deg, 4),
            "n": cell["n"],
            "m": cell["m"],
            "r": cell["r"].most_common(1)[0][0],
            "cc": cell["cc"].most_common(1)[0][0] if cell["cc"] else "",
        })
    out.sort(key=lambda d: (d["la"], d["lo"]))
    return {"cell": cell_deg, "cells": out}
