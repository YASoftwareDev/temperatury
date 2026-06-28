"""Fetching and caching of historical daily temperature data.

Data comes from the Open-Meteo historical reanalysis archive. The raw
download is cached as a CSV per location/time-span so repeated runs are
offline and instant.

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
_REQUEST_TIMEOUT = 90
# Retries guard against transient TLS/read timeouts on shared CI runners.
_MAX_ATTEMPTS = 4


def _cache_path(location: Location, start_year: int, end_year: int) -> Path:
    """Return the on-disk CSV path for a given location and span."""
    return DATA_DIR / f"{location.slug}_{start_year}-{end_year}.csv"


def _download(location: Location, start_year: int, end_year: int) -> pd.DataFrame:
    """Download daily mean temperatures from the Open-Meteo archive.

    Returns a DataFrame indexed by a ``DatetimeIndex`` with a single
    ``temperature_2m_mean`` column. Raises on network or schema errors so
    failures surface loudly rather than producing a silent empty plot.
    """
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": f"{start_year}-01-01",
        "end_date": f"{end_year}-12-31",
        "daily": "temperature_2m_mean",
        "timezone": location.timezone,
    }
    response = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            if attempt == _MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Failed to download temperature data for {location.name} "
                    f"after {_MAX_ATTEMPTS} attempts: {error}"
                ) from error
            # Exponential backoff: 2s, 4s, 8s …
            time.sleep(2 * attempt)

    payload = response.json()
    daily = payload.get("daily")
    if not daily or "time" not in daily or "temperature_2m_mean" not in daily:
        raise RuntimeError(
            f"Unexpected response from Open-Meteo for {location.name}: "
            f"missing 'daily' temperature fields."
        )

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temperature_2m_mean": daily["temperature_2m_mean"],
        }
    )
    return frame.set_index("date").sort_index()


def load_temperatures(
    location: Location,
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load daily mean temperatures, using the on-disk cache when possible.

    Parameters
    ----------
    location:
        Place to analyse.
    start_year, end_year:
        Inclusive range of complete calendar years.
    refresh:
        When ``True`` the cache is ignored and data is re-downloaded.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(location, start_year, end_year)

    if path.exists() and not refresh:
        frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    else:
        frame = _download(location, start_year, end_year)
        frame.to_csv(path)

    # Drop days the archive could not fill (NaN) so downstream stats are clean.
    frame = frame.dropna(subset=["temperature_2m_mean"])
    if frame.empty:
        raise RuntimeError(f"No temperature data available for {location.name}.")
    return frame
