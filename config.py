"""Configuration for the temperature analysis project.

Locations are keyed by an ASCII slug; the default the root URL opens to is
``DEFAULT_LOCATION``. Coordinates for the European capitals plus a few extra
Polish cities are listed in ``LOCATIONS``.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Project paths -------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

# Open-Meteo historical reanalysis archive (free, no API key).
# Daily data is available from 1940 onwards.
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
EARLIEST_YEAR = 1940

# Letters with no usable NFKD decomposition — transliterate explicitly.
_TRANSLIT = {
    "ł": "l", "Ł": "L", "ß": "ss", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE", "đ": "d", "Đ": "D", "ș": "s", "Ș": "S",
    "ț": "t", "Ț": "T", "ı": "i",
}


def slugify(name: str) -> str:
    """ASCII, URL- and filename-safe slug (handles Polish/Romanian/etc.)."""
    for src, dst in _TRANSLIT.items():
        name = name.replace(src, dst)
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().replace(" ", "-")


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


def _loc(name: str, lat: float, lon: float, tz: str) -> tuple[str, Location]:
    """Build a (slug-key, Location) pair."""
    location = Location(name, lat, lon, tz)
    return location.slug, location


# European capitals + a few extra Polish cities. Keyed by ASCII slug.
LOCATIONS: dict[str, Location] = dict([
    # --- European capitals ---
    _loc("Tirana", 41.3275, 19.8189, "Europe/Tirane"),
    _loc("Andorra la Vella", 42.5063, 1.5218, "Europe/Andorra"),
    _loc("Vienna", 48.2082, 16.3738, "Europe/Vienna"),
    _loc("Minsk", 53.9006, 27.5590, "Europe/Minsk"),
    _loc("Brussels", 50.8503, 4.3517, "Europe/Brussels"),
    _loc("Sarajevo", 43.8563, 18.4131, "Europe/Sarajevo"),
    _loc("Sofia", 42.6977, 23.3219, "Europe/Sofia"),
    _loc("Zagreb", 45.8150, 15.9819, "Europe/Zagreb"),
    _loc("Nicosia", 35.1856, 33.3823, "Asia/Nicosia"),
    _loc("Prague", 50.0755, 14.4378, "Europe/Prague"),
    _loc("Copenhagen", 55.6761, 12.5683, "Europe/Copenhagen"),
    _loc("Tallinn", 59.4370, 24.7536, "Europe/Tallinn"),
    _loc("Helsinki", 60.1699, 24.9384, "Europe/Helsinki"),
    _loc("Paris", 48.8566, 2.3522, "Europe/Paris"),
    _loc("Berlin", 52.5200, 13.4050, "Europe/Berlin"),
    _loc("Athens", 37.9838, 23.7275, "Europe/Athens"),
    _loc("Budapest", 47.4979, 19.0402, "Europe/Budapest"),
    _loc("Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    _loc("Dublin", 53.3498, -6.2603, "Europe/Dublin"),
    _loc("Rome", 41.9028, 12.4964, "Europe/Rome"),
    _loc("Pristina", 42.6629, 21.1655, "Europe/Belgrade"),
    _loc("Riga", 56.9496, 24.1052, "Europe/Riga"),
    _loc("Vaduz", 47.1410, 9.5209, "Europe/Vaduz"),
    _loc("Vilnius", 54.6872, 25.2797, "Europe/Vilnius"),
    _loc("Luxembourg", 49.6116, 6.1319, "Europe/Luxembourg"),
    _loc("Valletta", 35.8989, 14.5146, "Europe/Malta"),
    _loc("Chișinău", 47.0105, 28.8638, "Europe/Chisinau"),
    _loc("Monaco", 43.7384, 7.4246, "Europe/Monaco"),
    _loc("Podgorica", 42.4304, 19.2594, "Europe/Podgorica"),
    _loc("Amsterdam", 52.3676, 4.9041, "Europe/Amsterdam"),
    _loc("Skopje", 41.9981, 21.4254, "Europe/Skopje"),
    _loc("Oslo", 59.9139, 10.7522, "Europe/Oslo"),
    _loc("Lisbon", 38.7223, -9.1393, "Europe/Lisbon"),
    _loc("Bucharest", 44.4268, 26.1025, "Europe/Bucharest"),
    _loc("Moscow", 55.7558, 37.6173, "Europe/Moscow"),
    _loc("San Marino", 43.9424, 12.4578, "Europe/San_Marino"),
    _loc("Belgrade", 44.7866, 20.4489, "Europe/Belgrade"),
    _loc("Bratislava", 48.1486, 17.1077, "Europe/Bratislava"),
    _loc("Ljubljana", 46.0569, 14.5058, "Europe/Ljubljana"),
    _loc("Madrid", 40.4168, -3.7038, "Europe/Madrid"),
    _loc("Stockholm", 59.3293, 18.0686, "Europe/Stockholm"),
    _loc("Bern", 46.9480, 7.4474, "Europe/Zurich"),
    _loc("Kyiv", 50.4501, 30.5234, "Europe/Kyiv"),
    _loc("London", 51.5074, -0.1278, "Europe/London"),
    _loc("Vatican City", 41.9029, 12.4534, "Europe/Vatican"),
    # --- the Polish capital and a few extra Polish cities ---
    _loc("Warszawa", 52.2297, 21.0122, "Europe/Warsaw"),
    _loc("Kraków", 50.0647, 19.9450, "Europe/Warsaw"),
    _loc("Gdańsk", 54.3520, 18.6466, "Europe/Warsaw"),
    _loc("Wrocław", 51.1079, 17.0385, "Europe/Warsaw"),
    _loc("Poznań", 52.4064, 16.9252, "Europe/Warsaw"),
    _loc("Rabka-Zdrój", 49.6089, 19.9686, "Europe/Warsaw"),
])

DEFAULT_LOCATION = "warszawa"
