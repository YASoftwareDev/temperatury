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

import time
from pathlib import Path

import requests
import pandas as pd

from config import ARCHIVE_URL, DATA_DIR, Location

# Network timeout for the (potentially large) archive request, in seconds.
_REQUEST_TIMEOUT = 120
# Retries guard against transient timeouts and Open-Meteo rate limiting (429).
_MAX_ATTEMPTS = 6
# Locations per bulk request — a single call returns an aligned list.
_CHUNK = 15
# Pause between chunk requests so we never trip the per-minute burst limiter.
_CHUNK_PAUSE = 2.0


def _retry_after(response: requests.Response, attempt: int) -> float:
    """Seconds to wait after a 429 — honour Retry-After, else back off."""
    header = response.headers.get("Retry-After", "")
    if header.isdigit():
        return min(float(header), 60.0)
    return min(8.0 * attempt, 60.0)  # 8s, 16s, 24s …


def _cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Return the on-disk cache path (gzipped CSV) for a location and span."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}.csv.gz"


def _request(params: dict, what: str):
    """GET the archive with retry + 429-aware backoff; return parsed JSON."""
    response = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=_REQUEST_TIMEOUT)
            if response.status_code == 429 and attempt < _MAX_ATTEMPTS:
                time.sleep(_retry_after(response, attempt))
                continue
            response.raise_for_status()
            break
        except requests.RequestException as error:
            if attempt == _MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Failed to download temperature data for {what} "
                    f"after {_MAX_ATTEMPTS} attempts: {error}"
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
            # chunk — skip it (its cities are simply absent this run) and
            # carry on with whatever data we do have.
            print(f"  ! skipping {label}: {error}")
            continue
        items = payload if isinstance(payload, list) else [payload]
        for location, item in zip(chunk, items):
            frame = _parse_daily(item.get("daily"), location.name)
            frame.to_csv(_cache_path(location, start_year, end_year))
            result[location.slug] = _clean(frame, location.name)

    return result
