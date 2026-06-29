"""Configuration for the temperature analysis project.

Locations are keyed by an ASCII slug and tagged with a region (for the grouped
city chooser). The default the root URL opens to is ``DEFAULT_LOCATION``.
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
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
EARLIEST_YEAR = 1940

# Display order of regions in the chooser.
REGIONS = ["Europe", "Asia", "Middle East", "Africa",
           "North America", "South America", "Oceania"]

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
    timezone: str = "UTC"
    region: str = "Europe"

    @property
    def slug(self) -> str:
        """ASCII, URL- and filename-safe identifier derived from the name."""
        return slugify(self.name)


# (region, name, lat, lon, timezone). Capitals worldwide + a few Polish cities.
_CITIES: list[tuple] = [
    # --- Europe ---
    ("Europe", "Tirana", 41.3275, 19.8189, "Europe/Tirane"),
    ("Europe", "Andorra la Vella", 42.5063, 1.5218, "Europe/Andorra"),
    ("Europe", "Vienna", 48.2082, 16.3738, "Europe/Vienna"),
    ("Europe", "Minsk", 53.9006, 27.5590, "Europe/Minsk"),
    ("Europe", "Brussels", 50.8503, 4.3517, "Europe/Brussels"),
    ("Europe", "Sarajevo", 43.8563, 18.4131, "Europe/Sarajevo"),
    ("Europe", "Sofia", 42.6977, 23.3219, "Europe/Sofia"),
    ("Europe", "Zagreb", 45.8150, 15.9819, "Europe/Zagreb"),
    ("Europe", "Nicosia", 35.1856, 33.3823, "Asia/Nicosia"),
    ("Europe", "Prague", 50.0755, 14.4378, "Europe/Prague"),
    ("Europe", "Copenhagen", 55.6761, 12.5683, "Europe/Copenhagen"),
    ("Europe", "Tallinn", 59.4370, 24.7536, "Europe/Tallinn"),
    ("Europe", "Helsinki", 60.1699, 24.9384, "Europe/Helsinki"),
    ("Europe", "Paris", 48.8566, 2.3522, "Europe/Paris"),
    ("Europe", "Berlin", 52.5200, 13.4050, "Europe/Berlin"),
    ("Europe", "Athens", 37.9838, 23.7275, "Europe/Athens"),
    ("Europe", "Budapest", 47.4979, 19.0402, "Europe/Budapest"),
    ("Europe", "Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    ("Europe", "Dublin", 53.3498, -6.2603, "Europe/Dublin"),
    ("Europe", "Rome", 41.9028, 12.4964, "Europe/Rome"),
    ("Europe", "Pristina", 42.6629, 21.1655, "Europe/Belgrade"),
    ("Europe", "Riga", 56.9496, 24.1052, "Europe/Riga"),
    ("Europe", "Vaduz", 47.1410, 9.5209, "Europe/Vaduz"),
    ("Europe", "Vilnius", 54.6872, 25.2797, "Europe/Vilnius"),
    ("Europe", "Luxembourg", 49.6116, 6.1319, "Europe/Luxembourg"),
    ("Europe", "Valletta", 35.8989, 14.5146, "Europe/Malta"),
    ("Europe", "Chișinău", 47.0105, 28.8638, "Europe/Chisinau"),
    ("Europe", "Monaco", 43.7384, 7.4246, "Europe/Monaco"),
    ("Europe", "Podgorica", 42.4304, 19.2594, "Europe/Podgorica"),
    ("Europe", "Amsterdam", 52.3676, 4.9041, "Europe/Amsterdam"),
    ("Europe", "Skopje", 41.9981, 21.4254, "Europe/Skopje"),
    ("Europe", "Oslo", 59.9139, 10.7522, "Europe/Oslo"),
    ("Europe", "Lisbon", 38.7223, -9.1393, "Europe/Lisbon"),
    ("Europe", "Bucharest", 44.4268, 26.1025, "Europe/Bucharest"),
    ("Europe", "Moscow", 55.7558, 37.6173, "Europe/Moscow"),
    ("Europe", "San Marino", 43.9424, 12.4578, "Europe/San_Marino"),
    ("Europe", "Belgrade", 44.7866, 20.4489, "Europe/Belgrade"),
    ("Europe", "Bratislava", 48.1486, 17.1077, "Europe/Bratislava"),
    ("Europe", "Ljubljana", 46.0569, 14.5058, "Europe/Ljubljana"),
    ("Europe", "Madrid", 40.4168, -3.7038, "Europe/Madrid"),
    ("Europe", "Stockholm", 59.3293, 18.0686, "Europe/Stockholm"),
    ("Europe", "Bern", 46.9480, 7.4474, "Europe/Zurich"),
    ("Europe", "Kyiv", 50.4501, 30.5234, "Europe/Kyiv"),
    ("Europe", "London", 51.5074, -0.1278, "Europe/London"),
    ("Europe", "Vatican City", 41.9029, 12.4534, "Europe/Vatican"),
    ("Europe", "Warszawa", 52.2297, 21.0122, "Europe/Warsaw"),
    ("Europe", "Kraków", 50.0647, 19.9450, "Europe/Warsaw"),
    ("Europe", "Gdańsk", 54.3520, 18.6466, "Europe/Warsaw"),
    ("Europe", "Wrocław", 51.1079, 17.0385, "Europe/Warsaw"),
    ("Europe", "Poznań", 52.4064, 16.9252, "Europe/Warsaw"),
    ("Europe", "Rabka-Zdrój", 49.6089, 19.9686, "Europe/Warsaw"),
    # --- Asia ---
    ("Asia", "Kabul", 34.5553, 69.2075, "Asia/Kabul"),
    ("Asia", "Yerevan", 40.1792, 44.4991, "Asia/Yerevan"),
    ("Asia", "Baku", 40.4093, 49.8671, "Asia/Baku"),
    ("Asia", "Dhaka", 23.8103, 90.4125, "Asia/Dhaka"),
    ("Asia", "Thimphu", 27.4728, 89.6390, "Asia/Thimphu"),
    ("Asia", "Bandar Seri Begawan", 4.9031, 114.9398, "Asia/Brunei"),
    ("Asia", "Phnom Penh", 11.5564, 104.9282, "Asia/Phnom_Penh"),
    ("Asia", "Beijing", 39.9042, 116.4074, "Asia/Shanghai"),
    ("Asia", "Tbilisi", 41.7151, 44.8271, "Asia/Tbilisi"),
    ("Asia", "New Delhi", 28.6139, 77.2090, "Asia/Kolkata"),
    ("Asia", "Jakarta", -6.2088, 106.8456, "Asia/Jakarta"),
    ("Asia", "Tokyo", 35.6762, 139.6503, "Asia/Tokyo"),
    ("Asia", "Astana", 51.1605, 71.4704, "Asia/Almaty"),
    ("Asia", "Bishkek", 42.8746, 74.5698, "Asia/Bishkek"),
    ("Asia", "Vientiane", 17.9757, 102.6331, "Asia/Vientiane"),
    ("Asia", "Kuala Lumpur", 3.1390, 101.6869, "Asia/Kuala_Lumpur"),
    ("Asia", "Malé", 4.1755, 73.5093, "Indian/Maldives"),
    ("Asia", "Ulaanbaatar", 47.8864, 106.9057, "Asia/Ulaanbaatar"),
    ("Asia", "Naypyidaw", 19.7633, 96.0785, "Asia/Yangon"),
    ("Asia", "Kathmandu", 27.7172, 85.3240, "Asia/Kathmandu"),
    ("Asia", "Pyongyang", 39.0392, 125.7625, "Asia/Pyongyang"),
    ("Asia", "Islamabad", 33.6844, 73.0479, "Asia/Karachi"),
    ("Asia", "Manila", 14.5995, 120.9842, "Asia/Manila"),
    ("Asia", "Seoul", 37.5665, 126.9780, "Asia/Seoul"),
    ("Asia", "Singapore", 1.3521, 103.8198, "Asia/Singapore"),
    ("Asia", "Colombo", 6.9271, 79.8612, "Asia/Colombo"),
    ("Asia", "Dushanbe", 38.5598, 68.7870, "Asia/Dushanbe"),
    ("Asia", "Bangkok", 13.7563, 100.5018, "Asia/Bangkok"),
    ("Asia", "Dili", -8.5569, 125.5603, "Asia/Dili"),
    ("Asia", "Ashgabat", 37.9601, 58.3261, "Asia/Ashgabat"),
    ("Asia", "Tashkent", 41.2995, 69.2401, "Asia/Tashkent"),
    ("Asia", "Hanoi", 21.0285, 105.8542, "Asia/Ho_Chi_Minh"),
    # --- Middle East ---
    ("Middle East", "Manama", 26.2285, 50.5860, "Asia/Bahrain"),
    ("Middle East", "Tehran", 35.6892, 51.3890, "Asia/Tehran"),
    ("Middle East", "Baghdad", 33.3152, 44.3661, "Asia/Baghdad"),
    ("Middle East", "Jerusalem", 31.7683, 35.2137, "Asia/Jerusalem"),
    ("Middle East", "Amman", 31.9454, 35.9284, "Asia/Amman"),
    ("Middle East", "Kuwait City", 29.3759, 47.9774, "Asia/Kuwait"),
    ("Middle East", "Beirut", 33.8938, 35.5018, "Asia/Beirut"),
    ("Middle East", "Muscat", 23.5880, 58.3829, "Asia/Muscat"),
    ("Middle East", "Doha", 25.2854, 51.5310, "Asia/Qatar"),
    ("Middle East", "Riyadh", 24.7136, 46.6753, "Asia/Riyadh"),
    ("Middle East", "Damascus", 33.5138, 36.2765, "Asia/Damascus"),
    ("Middle East", "Abu Dhabi", 24.4539, 54.3773, "Asia/Dubai"),
    ("Middle East", "Sanaa", 15.3694, 44.1910, "Asia/Aden"),
    ("Middle East", "Ankara", 39.9334, 32.8597, "Europe/Istanbul"),
    # --- Africa ---
    ("Africa", "Algiers", 36.7538, 3.0588, "Africa/Algiers"),
    ("Africa", "Luanda", -8.8390, 13.2894, "Africa/Luanda"),
    ("Africa", "Porto-Novo", 6.4969, 2.6289, "Africa/Porto-Novo"),
    ("Africa", "Gaborone", -24.6282, 25.9231, "Africa/Gaborone"),
    ("Africa", "Ouagadougou", 12.3714, -1.5197, "Africa/Ouagadougou"),
    ("Africa", "Bujumbura", -3.3614, 29.3599, "Africa/Bujumbura"),
    ("Africa", "Yaoundé", 3.8480, 11.5021, "Africa/Douala"),
    ("Africa", "Praia", 14.9330, -23.5133, "Atlantic/Cape_Verde"),
    ("Africa", "Bangui", 4.3947, 18.5582, "Africa/Bangui"),
    ("Africa", "N'Djamena", 12.1348, 15.0557, "Africa/Ndjamena"),
    ("Africa", "Moroni", -11.7172, 43.2473, "Indian/Comoro"),
    ("Africa", "Kinshasa", -4.4419, 15.2663, "Africa/Kinshasa"),
    ("Africa", "Brazzaville", -4.2634, 15.2429, "Africa/Brazzaville"),
    ("Africa", "Djibouti", 11.5721, 43.1456, "Africa/Djibouti"),
    ("Africa", "Cairo", 30.0444, 31.2357, "Africa/Cairo"),
    ("Africa", "Malabo", 3.7504, 8.7371, "Africa/Malabo"),
    ("Africa", "Asmara", 15.3229, 38.9251, "Africa/Asmara"),
    ("Africa", "Addis Ababa", 9.0300, 38.7400, "Africa/Addis_Ababa"),
    ("Africa", "Libreville", 0.4162, 9.4673, "Africa/Libreville"),
    ("Africa", "Banjul", 13.4549, -16.5790, "Africa/Banjul"),
    ("Africa", "Accra", 5.6037, -0.1870, "Africa/Accra"),
    ("Africa", "Conakry", 9.6412, -13.5784, "Africa/Conakry"),
    ("Africa", "Bissau", 11.8817, -15.6178, "Africa/Bissau"),
    ("Africa", "Abidjan", 5.3600, -4.0083, "Africa/Abidjan"),
    ("Africa", "Nairobi", -1.2921, 36.8219, "Africa/Nairobi"),
    ("Africa", "Maseru", -29.3151, 27.4869, "Africa/Maseru"),
    ("Africa", "Monrovia", 6.3004, -10.7969, "Africa/Monrovia"),
    ("Africa", "Tripoli", 32.8872, 13.1913, "Africa/Tripoli"),
    ("Africa", "Antananarivo", -18.8792, 47.5079, "Indian/Antananarivo"),
    ("Africa", "Lilongwe", -13.9626, 33.7741, "Africa/Blantyre"),
    ("Africa", "Bamako", 12.6392, -8.0029, "Africa/Bamako"),
    ("Africa", "Nouakchott", 18.0735, -15.9582, "Africa/Nouakchott"),
    ("Africa", "Port Louis", -20.1609, 57.5012, "Indian/Mauritius"),
    ("Africa", "Rabat", 34.0209, -6.8416, "Africa/Casablanca"),
    ("Africa", "Maputo", -25.9692, 32.5732, "Africa/Maputo"),
    ("Africa", "Windhoek", -22.5609, 17.0658, "Africa/Windhoek"),
    ("Africa", "Niamey", 13.5126, 2.1126, "Africa/Niamey"),
    ("Africa", "Abuja", 9.0765, 7.3986, "Africa/Lagos"),
    ("Africa", "Kigali", -1.9706, 30.1044, "Africa/Kigali"),
    ("Africa", "Dakar", 14.7167, -17.4677, "Africa/Dakar"),
    ("Africa", "Victoria", -4.6191, 55.4513, "Indian/Mahe"),
    ("Africa", "Freetown", 8.4657, -13.2317, "Africa/Freetown"),
    ("Africa", "Mogadishu", 2.0469, 45.3182, "Africa/Mogadishu"),
    ("Africa", "Pretoria", -25.7479, 28.2293, "Africa/Johannesburg"),
    ("Africa", "Juba", 4.8594, 31.5713, "Africa/Juba"),
    ("Africa", "Khartoum", 15.5007, 32.5599, "Africa/Khartoum"),
    ("Africa", "Mbabane", -26.3054, 31.1367, "Africa/Mbabane"),
    ("Africa", "Dodoma", -6.1630, 35.7516, "Africa/Dar_es_Salaam"),
    ("Africa", "Lomé", 6.1725, 1.2314, "Africa/Lome"),
    ("Africa", "Tunis", 36.8065, 10.1815, "Africa/Tunis"),
    ("Africa", "Kampala", 0.3476, 32.5825, "Africa/Kampala"),
    ("Africa", "Lusaka", -15.3875, 28.3228, "Africa/Lusaka"),
    ("Africa", "Harare", -17.8252, 31.0335, "Africa/Harare"),
    # --- North America ---
    ("North America", "Nassau", 25.0443, -77.3504, "America/Nassau"),
    ("North America", "Belmopan", 17.2514, -88.7705, "America/Belize"),
    ("North America", "Ottawa", 45.4215, -75.6972, "America/Toronto"),
    ("North America", "San José", 9.9281, -84.0907, "America/Costa_Rica"),
    ("North America", "Havana", 23.1136, -82.3666, "America/Havana"),
    ("North America", "Santo Domingo", 18.4861, -69.9312, "America/Santo_Domingo"),
    ("North America", "San Salvador", 13.6929, -89.2182, "America/El_Salvador"),
    ("North America", "Guatemala City", 14.6349, -90.5069, "America/Guatemala"),
    ("North America", "Port-au-Prince", 18.5944, -72.3074, "America/Port-au-Prince"),
    ("North America", "Tegucigalpa", 14.0723, -87.1921, "America/Tegucigalpa"),
    ("North America", "Kingston", 17.9714, -76.7920, "America/Jamaica"),
    ("North America", "Mexico City", 19.4326, -99.1332, "America/Mexico_City"),
    ("North America", "Managua", 12.1149, -86.2362, "America/Managua"),
    ("North America", "Panama City", 8.9824, -79.5199, "America/Panama"),
    ("North America", "Washington", 38.9072, -77.0369, "America/New_York"),
    # --- South America ---
    ("South America", "Buenos Aires", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    ("South America", "La Paz", -16.4897, -68.1193, "America/La_Paz"),
    ("South America", "Brasília", -15.7939, -47.8828, "America/Sao_Paulo"),
    ("South America", "Santiago", -33.4489, -70.6693, "America/Santiago"),
    ("South America", "Bogotá", 4.7110, -74.0721, "America/Bogota"),
    ("South America", "Quito", -0.1807, -78.4678, "America/Guayaquil"),
    ("South America", "Georgetown", 6.8013, -58.1551, "America/Guyana"),
    ("South America", "Asunción", -25.2637, -57.5759, "America/Asuncion"),
    ("South America", "Lima", -12.0464, -77.0428, "America/Lima"),
    ("South America", "Paramaribo", 5.8520, -55.2038, "America/Paramaribo"),
    ("South America", "Montevideo", -34.9011, -56.1645, "America/Montevideo"),
    ("South America", "Caracas", 10.4806, -66.9036, "America/Caracas"),
    # --- Oceania ---
    ("Oceania", "Canberra", -35.2809, 149.1300, "Australia/Sydney"),
    ("Oceania", "Suva", -18.1248, 178.4501, "Pacific/Fiji"),
    ("Oceania", "Tarawa", 1.3290, 172.9790, "Pacific/Tarawa"),
    ("Oceania", "Majuro", 7.1164, 171.1858, "Pacific/Majuro"),
    ("Oceania", "Palikir", 6.9248, 158.1611, "Pacific/Pohnpei"),
    ("Oceania", "Wellington", -41.2865, 174.7762, "Pacific/Auckland"),
    ("Oceania", "Port Moresby", -9.4438, 147.1803, "Pacific/Port_Moresby"),
    ("Oceania", "Apia", -13.8507, -171.7514, "Pacific/Apia"),
    ("Oceania", "Honiara", -9.4456, 159.9729, "Pacific/Guadalcanal"),
    ("Oceania", "Nuku'alofa", -21.1393, -175.2026, "Pacific/Tongatapu"),
    ("Oceania", "Port Vila", -17.7333, 168.3273, "Pacific/Efate"),
]

LOCATIONS: dict[str, Location] = {}
for _region, _name, _lat, _lon, _tz in _CITIES:
    _city = Location(_name, _lat, _lon, _tz, _region)
    LOCATIONS[_city.slug] = _city

DEFAULT_LOCATION = "warszawa"
