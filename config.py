"""Configuration for the temperature analysis project.

A single place to change the location and the analysed time span. The
location defaults to Warsaw (the capital of Poland — the project name
``temperatury`` is Polish); override it on the command line via ``main.py``.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path


def slugify(name: str) -> str:
    """ASCII, URL-safe slug. Handles Polish ``ł`` (no NFKD decomposition)."""
    text = name.replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().replace(" ", "-")

# Project paths -------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

# Open-Meteo historical reanalysis archive (free, no API key).
# Daily data is available from 1940 onwards.
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
EARLIEST_YEAR = 1940


@dataclass(frozen=True)
class Location:
    """An immutable description of a place to analyse."""

    name: str
    latitude: float
    longitude: float
    timezone: str = "Europe/Warsaw"

    @property
    def slug(self) -> str:
        """ASCII, URL- and filename-safe identifier derived from the name."""
        return slugify(self.name)


# A few convenient presets. Add your own or pass --lat/--lon on the CLI.
LOCATIONS: dict[str, Location] = {
    "warszawa": Location("Warszawa", 52.2297, 21.0122),
    "krakow": Location("Kraków", 50.0647, 19.9450),
    "gdansk": Location("Gdańsk", 54.3520, 18.6466),
    "wroclaw": Location("Wrocław", 51.1079, 17.0385),
    "poznan": Location("Poznań", 52.4064, 16.9252),
    "rabka": Location("Rabka-Zdrój", 49.6089, 19.9686),
}

DEFAULT_LOCATION = "warszawa"
