"""Fetching and caching of historical daily temperature data.

Data comes from the Open-Meteo historical reanalysis archive. The raw
download is cached as a CSV per location/time-span so repeated runs are
offline and instant. Multiple locations are fetched in a single request
(comma-separated coordinates) to stay well under Open-Meteo's rate limits.

CSV schema (one row per day):
    date                  ISO-8601 ``YYYY-MM-DD``
    temperature_2m_mean   daily mean 2 m air temperature, °C (float)
"""

from __future__ import annotations

import datetime as dt
import os
import time
from pathlib import Path

import requests
import pandas as pd

from config import ARCHIVE_URL, DATA_DIR, Location

# Offline mode (set in CI): render only from the committed cache, never fetch.
# Fetching is a local task - CI's shared IP is rate-limited by Open-Meteo.
_OFFLINE = os.environ.get("TEMPERATURY_OFFLINE") == "1"

# A paid Open-Meteo API key (export OPENMETEO_API_KEY=...) lifts the free-tier
# per-minute/hour/day limits - by far the fastest way to fill the backfill.
# When unset, the free archive endpoint is used and behaviour is unchanged.
_API_KEY = os.environ.get("OPENMETEO_API_KEY")
_ARCHIVE_URL = ("https://customer-archive-api.open-meteo.com/v1/archive"
                if _API_KEY else ARCHIVE_URL)

# Network timeout for the (potentially large) archive request, in seconds.
_REQUEST_TIMEOUT = 120
# Retries guard against transient timeouts and Open-Meteo rate limiting (429).
_MAX_ATTEMPTS = 6
# Locations per bulk request - a single call returns an aligned list.
_CHUNK = 15
# Pause between chunk requests so we never trip the per-minute burst limiter.
_CHUNK_PAUSE = 2.0


def _retry_after(response: requests.Response, attempt: int) -> float:
    """Seconds to wait after a 429 - honour Retry-After, else back off."""
    header = response.headers.get("Retry-After", "")
    if header.isdigit():
        return min(float(header), 60.0)
    return min(8.0 * attempt, 60.0)  # 8s, 16s, 24s …


def _cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Return the on-disk cache path (gzipped CSV) for a location and span."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}.csv.gz"


def _request(params: dict, what: str):
    """GET the archive with retry + 429-aware backoff; return parsed JSON."""
    if _API_KEY:
        params = {**params, "apikey": _API_KEY}
    response = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.get(_ARCHIVE_URL, params=params, timeout=_REQUEST_TIMEOUT)
            if response.status_code == 429 and attempt < _MAX_ATTEMPTS:
                time.sleep(_retry_after(response, attempt))
                continue
            response.raise_for_status()
            break
        except requests.RequestException as error:
            status = getattr(error.response, "status_code", None)
            # 4xx other than 429 (e.g. 400 request-too-large) won't fix on
            # retry - fail immediately instead of burning the backoff budget.
            fatal = status is not None and 400 <= status < 500 and status != 429
            if fatal or attempt == _MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Failed to download temperature data for {what} "
                    f"after {attempt} attempt(s): {error}"
                ) from error
            time.sleep(2 * attempt)

    assert response is not None  # loop either breaks with a response or raises
    return response.json()


def _parse_daily(daily: dict | None, name: str) -> pd.DataFrame:
    """Turn an Open-Meteo ``daily`` block into a date-indexed DataFrame."""
    if not daily or "time" not in daily or "temperature_2m_mean" not in daily:
        raise RuntimeError(
            f"Unexpected response from Open-Meteo for {name}: "
            f"missing 'daily' temperature fields."
        )
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temperature_2m_mean": daily["temperature_2m_mean"],
        }
    )
    return frame.set_index("date").sort_index()


def _clean(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """Drop unfilled (NaN) days and guard against an empty series."""
    frame = frame.dropna(subset=["temperature_2m_mean"])
    if frame.empty:
        raise RuntimeError(f"No temperature data available for {name}.")
    return frame


def load_temperatures(
    location: Location,
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load one location's daily mean temperatures, using the cache when able."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(location, start_year, end_year)

    if path.exists() and not refresh:
        frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    else:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "temperature_2m_mean",
            "timezone": location.timezone,
        }
        frame = _parse_daily(_request(params, location.name).get("daily"), location.name)
        frame.to_csv(path)

    return _clean(frame, location.name)


def load_temperatures_bulk(
    locations: list[Location],
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load many locations, fetching cache-misses in a few bulk requests.

    Returns a ``{slug: DataFrame}`` mapping. Cached locations are read from
    disk; the rest are downloaded in chunks (one HTTP request per chunk, with
    ``timezone=auto`` so each location uses its own local time).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[Location] = []

    for location in locations:
        path = _cache_path(location, start_year, end_year)
        if path.exists() and not refresh:
            frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            result[location.slug] = _clean(frame, location.name)
        else:
            to_fetch.append(location)

    if _OFFLINE and to_fetch:
        print(f"  (offline) {len(to_fetch)} location(s) not in cache, skipped")
        to_fetch = []

    for start in range(0, len(to_fetch), _CHUNK):
        if start:
            time.sleep(_CHUNK_PAUSE)  # space chunk requests apart
        chunk = to_fetch[start:start + _CHUNK]
        params = {
            "latitude": ",".join(str(loc.latitude) for loc in chunk),
            "longitude": ",".join(str(loc.longitude) for loc in chunk),
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "temperature_2m_mean",
            "timezone": "auto",
        }
        label = f"{len(chunk)} locations ({chunk[0].name}…)"
        try:
            payload = _request(params, label)
        except RuntimeError as error:
            # Don't abort the whole build for an unreachable / rate-limited
            # chunk - skip it (its cities are simply absent this run) and
            # carry on with whatever data we do have.
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(chunk, items):
            frame = _parse_daily(item.get("daily"), location.name)
            frame.to_csv(_cache_path(location, start_year, end_year))
            result[location.slug] = _clean(frame, location.name)

    return result


# --- daily extremes (record high/low) --------------------------------------
_EXTREME_COLS = ("temperature_2m_max", "temperature_2m_min")
# Two variables double the per-request cost, so fewer locations per call.
_EXTREME_CHUNK = 7


def _extremes_cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Cache path for the daily max/min dataset (separate from the means)."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}_extremes.csv.gz"


def _parse_extremes(daily: dict | None, name: str) -> pd.DataFrame:
    """Turn an Open-Meteo ``daily`` block of max/min into a DataFrame."""
    if not daily or "time" not in daily or any(c not in daily for c in _EXTREME_COLS):
        raise RuntimeError(
            f"Unexpected response from Open-Meteo for {name}: "
            f"missing 'daily' max/min fields."
        )
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temperature_2m_max": daily["temperature_2m_max"],
            "temperature_2m_min": daily["temperature_2m_min"],
        }
    )
    return frame.set_index("date").sort_index()


def load_extremes_bulk(
    locations: list[Location],
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load daily max/min for many locations (cache-aware, chunked, resilient).

    Returns ``{slug: DataFrame[max, min]}``; locations that can't be fetched
    are simply absent (their record chart is skipped).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[Location] = []

    for location in locations:
        path = _extremes_cache_path(location, start_year, end_year)
        if path.exists() and not refresh:
            frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            result[location.slug] = frame.dropna(subset=list(_EXTREME_COLS))
        else:
            to_fetch.append(location)

    if _OFFLINE and to_fetch:
        print(f"  (offline) {len(to_fetch)} location(s) without max/min cache, skipped")
        to_fetch = []

    for start in range(0, len(to_fetch), _EXTREME_CHUNK):
        if start:
            time.sleep(_CHUNK_PAUSE)
        chunk = to_fetch[start:start + _EXTREME_CHUNK]
        params = {
            "latitude": ",".join(str(loc.latitude) for loc in chunk),
            "longitude": ",".join(str(loc.longitude) for loc in chunk),
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": ",".join(_EXTREME_COLS),
            "timezone": "auto",
        }
        label = f"{len(chunk)} locations ({chunk[0].name}…) max/min"
        try:
            payload = _request(params, label)
        except RuntimeError as error:
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(chunk, items):
            frame = _parse_extremes(item.get("daily"), location.name)
            frame.to_csv(_extremes_cache_path(location, start_year, end_year))
            result[location.slug] = frame.dropna(subset=list(_EXTREME_COLS))

    return result


# --- precipitation ---------------------------------------------------------
def _precip_cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Cache path for the daily precipitation dataset."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}_precip.csv.gz"


def _parse_precip(daily: dict | None, name: str) -> pd.DataFrame:
    """Turn an Open-Meteo ``daily`` block of precipitation into a DataFrame."""
    if not daily or "time" not in daily or "precipitation_sum" not in daily:
        raise RuntimeError(
            f"Unexpected response from Open-Meteo for {name}: "
            f"missing 'daily' precipitation field."
        )
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "precipitation_sum": daily["precipitation_sum"],
        }
    )
    return frame.set_index("date").sort_index()


def load_precip_bulk(
    locations: list[Location],
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load daily precipitation for many locations (cache-aware, chunked)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[Location] = []

    for location in locations:
        path = _precip_cache_path(location, start_year, end_year)
        if path.exists() and not refresh:
            frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            result[location.slug] = frame.dropna(subset=["precipitation_sum"])
        else:
            to_fetch.append(location)

    if _OFFLINE and to_fetch:
        print(f"  (offline) {len(to_fetch)} location(s) without precip cache, skipped")
        to_fetch = []

    for start in range(0, len(to_fetch), _CHUNK):
        if start:
            time.sleep(_CHUNK_PAUSE)
        chunk = to_fetch[start:start + _CHUNK]
        params = {
            "latitude": ",".join(str(loc.latitude) for loc in chunk),
            "longitude": ",".join(str(loc.longitude) for loc in chunk),
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "precipitation_sum",
            "timezone": "auto",
        }
        label = f"{len(chunk)} locations ({chunk[0].name}…) precip"
        try:
            payload = _request(params, label)
        except RuntimeError as error:
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(chunk, items):
            frame = _parse_precip(item.get("daily"), location.name)
            frame.to_csv(_precip_cache_path(location, start_year, end_year))
            result[location.slug] = frame.dropna(subset=["precipitation_sum"])

    return result


# --- apparent temperature (heat index) -------------------------------------
def _apparent_cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Cache path for the daily apparent-temperature (heat-index) dataset."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}_apparent.csv.gz"


def _parse_apparent(daily: dict | None, name: str) -> pd.DataFrame:
    """Turn an Open-Meteo ``daily`` block of apparent-temp max into a DataFrame."""
    if not daily or "time" not in daily or "apparent_temperature_max" not in daily:
        raise RuntimeError(
            f"Unexpected response from Open-Meteo for {name}: "
            f"missing 'daily' apparent_temperature_max field."
        )
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "apparent_temperature_max": daily["apparent_temperature_max"],
        }
    )
    return frame.set_index("date").sort_index()


def load_apparent_bulk(
    locations: list[Location],
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load daily apparent-temperature max for many locations (humidity-aware).

    Powers the heat-index chart; a location without it simply skips that chart.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[Location] = []

    for location in locations:
        path = _apparent_cache_path(location, start_year, end_year)
        if path.exists() and not refresh:
            frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            result[location.slug] = frame.dropna(subset=["apparent_temperature_max"])
        else:
            to_fetch.append(location)

    if _OFFLINE and to_fetch:
        print(f"  (offline) {len(to_fetch)} location(s) without apparent cache, skipped")
        to_fetch = []

    for start in range(0, len(to_fetch), _CHUNK):
        if start:
            time.sleep(_CHUNK_PAUSE)
        chunk = to_fetch[start:start + _CHUNK]
        params = {
            "latitude": ",".join(str(loc.latitude) for loc in chunk),
            "longitude": ",".join(str(loc.longitude) for loc in chunk),
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "apparent_temperature_max",
            "timezone": "auto",
        }
        label = f"{len(chunk)} locations ({chunk[0].name}…) apparent"
        try:
            payload = _request(params, label)
        except RuntimeError as error:
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(chunk, items):
            frame = _parse_apparent(item.get("daily"), location.name)
            frame.to_csv(_apparent_cache_path(location, start_year, end_year))
            result[location.slug] = frame.dropna(subset=["apparent_temperature_max"])

    return result


def cache_signature(location: Location, start_year: int, end_year: int) -> str:
    """Content hash of a location's historical caches - for incremental builds.

    Covers the datasets that feed the rendered PNGs (mean, extremes, precip,
    apparent); current-year data is excluded because it only affects the HTML
    widgets, not the static charts. A city whose signature is unchanged since
    the last build can have its (expensive) chart rendering skipped.
    """
    import hashlib

    digest = hashlib.sha1()
    for path in (
        _cache_path(location, start_year, end_year),
        _extremes_cache_path(location, start_year, end_year),
        _precip_cache_path(location, start_year, end_year),
        _apparent_cache_path(location, start_year, end_year),
    ):
        if path.exists():
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


# --- current (partial) year ------------------------------------------------
# The ongoing calendar year is fetched separately so the interactive widgets
# can offer it as a selectable year *without* it polluting the static trend
# charts (a half-finished year would skew an annual mean). It is cached under a
# distinct ``_<year>_current`` key; in offline mode only the committed cache is
# used, so CI still renders whatever was last fetched locally.


def _current_span() -> tuple[int, str, str]:
    """Return ``(year, start_date, end_date)`` for the year in progress.

    ``end_date`` is today: the ERA5 archive has no future days (and a few
    days' lag), so requesting to today and dropping the trailing NaNs gives
    every day that is actually available.
    """
    today = dt.date.today()
    return today.year, f"{today.year}-01-01", today.isoformat()


def _current_cache_path(location: Location, year: int, suffix: str = "") -> Path:
    """Cache path for the current-year partial dataset (mean or extremes)."""
    tail = f"_current{suffix}"
    return DATA_DIR / f"{location.slug}_{year}{tail}.csv.gz"


def _load_current(
    locations: list[Location],
    columns: tuple[str, ...],
    suffix: str,
    parse,
    *,
    chunk: int,
    refresh: bool,
) -> dict[str, pd.DataFrame]:
    """Shared loader for the current (partial) year - mean or max/min.

    Mirrors the bulk loaders but targets ``year-01-01 … today`` and tolerates
    a location whose archive has no rows yet (it is simply omitted).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    year, start_date, end_date = _current_span()
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[Location] = []

    for location in locations:
        path = _current_cache_path(location, year, suffix)
        if path.exists() and not refresh:
            frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            frame = frame.dropna(subset=list(columns))
            if not frame.empty:
                result[location.slug] = frame
        else:
            to_fetch.append(location)

    if _OFFLINE and to_fetch:
        print(f"  (offline) {len(to_fetch)} location(s) without {year} cache, skipped")
        to_fetch = []

    for start in range(0, len(to_fetch), chunk):
        if start:
            time.sleep(_CHUNK_PAUSE)
        group = to_fetch[start:start + chunk]
        params = {
            "latitude": ",".join(str(loc.latitude) for loc in group),
            "longitude": ",".join(str(loc.longitude) for loc in group),
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(columns),
            "timezone": "auto",
        }
        label = f"{len(group)} locations ({group[0].name}…) {year}"
        try:
            payload = _request(params, label)
        except RuntimeError as error:
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(group, items):
            frame = parse(item.get("daily"), location.name)
            frame.to_csv(_current_cache_path(location, year, suffix))
            frame = frame.dropna(subset=list(columns))
            if not frame.empty:
                result[location.slug] = frame

    return result


def load_current_bulk(
    locations: list[Location], *, refresh: bool = False
) -> dict[str, pd.DataFrame]:
    """Current-year daily means (partial), for the monthly-range widget."""
    return _load_current(
        locations, ("temperature_2m_mean",), "", _parse_daily,
        chunk=_CHUNK, refresh=refresh,
    )


def load_current_extremes_bulk(
    locations: list[Location], *, refresh: bool = False
) -> dict[str, pd.DataFrame]:
    """Current-year daily max/min (partial), for the monthly-records widget."""
    return _load_current(
        locations, _EXTREME_COLS, "_extremes", _parse_extremes,
        chunk=_EXTREME_CHUNK, refresh=refresh,
    )
