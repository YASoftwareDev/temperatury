"""Lazy add-on loading must hand the renderer exactly what eager loading did.

``main.py --all`` keeps the add-on datasets on disk as ``data.LazyFrame`` refs
and each render worker reads its own city's, so the parent stays inside the CI
runner's memory. Any drift between the two paths would change published charts
without failing anything, so these pin equality, including the current-year
rule that an all-NaN cache counts as absent.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codec
import data
from config import Location

LOC = Location("Testville", 50.0, 20.0)


def _frame(cols, n=400, nan_every=7):
    idx = pd.date_range("1940-01-01", periods=n, freq="D", name="date")
    rng = np.random.default_rng(1)
    out = pd.DataFrame({c: np.round(rng.uniform(-30, 40, n), 1) for c in cols},
                       index=idx)
    out.iloc[::nan_every, 0] = np.nan
    return out


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_OFFLINE", True)
    return tmp_path


@pytest.mark.parametrize("loader,path_fn,cols", [
    (data.load_extremes_bulk, data._extremes_cache_path, data._EXTREME_COLS),
    (data.load_precip_bulk, data._precip_cache_path, ("precipitation_sum",)),
    (data.load_apparent_bulk, data._apparent_cache_path,
     ("apparent_temperature_max",)),
])
def test_lazy_resolves_to_the_eager_frame(cache, loader, path_fn, cols):
    codec.write_frame(_frame(cols), path_fn(LOC, 1940, 2025))
    eager = loader([LOC], 1940, 2025)
    lazy = loader([LOC], 1940, 2025, lazy=True)
    assert isinstance(lazy[LOC.slug], data.LazyFrame)
    pd.testing.assert_frame_equal(eager[LOC.slug], data.resolve(lazy[LOC.slug]))


@pytest.mark.parametrize("loader,suffix,cols", [
    (data.load_current_bulk, "", ("temperature_2m_mean",)),
    (data.load_current_extremes_bulk, "_extremes", data._EXTREME_COLS),
])
def test_current_year_lazy_matches_eager(cache, loader, suffix, cols):
    year = data._current_span()[0]
    path = data._current_cache_path(LOC, year, suffix)
    codec.write_frame(_frame(cols), path)
    pd.testing.assert_frame_equal(
        loader([LOC])[LOC.slug], data.resolve(loader([LOC], lazy=True)[LOC.slug]))
    # All-NaN: eager omits the city, so lazy must resolve to None, not to an
    # empty frame the renderer would treat as present.
    codec.write_frame(_frame(cols, nan_every=1), path)
    assert LOC.slug not in loader([LOC])
    assert data.resolve(loader([LOC], lazy=True).get(LOC.slug)) is None


def test_resolve_passes_frames_and_none_through():
    f = _frame(("x",))
    assert data.resolve(f) is f
    assert data.resolve(None) is None
