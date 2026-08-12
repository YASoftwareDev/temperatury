"""Map each city to its country (ISO 3166-1 alpha-2), for the warming rankings
and the share cards.

Cities from ``cities750k.tsv`` carry their own GeoNames country code, which is
what ``country_code`` uses. The rest fall back to ``_TZ_CC``, a timezone ->
country map, with ``_SLUG_OVERRIDE`` for a zone shared across a border where the
primary country isn't the city's.

A timezone does NOT identify a country, so the fallback is a last resort and not
a source of truth: GeoNames files 41 Vietnamese cities under ``Asia/Bangkok``,
and while the country came from the timezone the site showed every one of them
with a Thai flag and counted them toward Thailand in the warming ranking.

``_TZ_CC`` maps each zone to its PRIMARY country, which is the right answer for
its other job - ``tz_country_map`` ships it to the browser so a visitor's country
can be guessed from ``Intl…timeZone`` offline, and a browser reporting
``Asia/Bangkok`` really is most likely in Thailand.

Localised country *names* are produced in the browser via ``Intl.DisplayNames``
from the code (so a Polish page shows "Polska", English shows "Poland") - no
per-language name tables live here.
"""

from __future__ import annotations

from config import Location

# IANA timezone -> ISO 3166-1 alpha-2 (primary country), lowercase.
_TZ_CC: dict[str, str] = {
    "Africa/Abidjan": "ci",
    "Africa/Accra": "gh",
    "Africa/Addis_Ababa": "et",
    "Africa/Algiers": "dz",
    "Africa/Asmara": "er",
    "Africa/Bamako": "ml",
    "Africa/Bangui": "cf",
    "Africa/Banjul": "gm",
    "Africa/Bissau": "gw",
    "Africa/Blantyre": "mw",
    "Africa/Brazzaville": "cg",
    "Africa/Bujumbura": "bi",
    "Africa/Cairo": "eg",
    "Africa/Casablanca": "ma",
    "Africa/Ceuta": "es",
    "Africa/Conakry": "gn",
    "Africa/Dakar": "sn",
    "Africa/Dar_es_Salaam": "tz",
    "Africa/Djibouti": "dj",
    "Africa/Douala": "cm",
    "Africa/El_Aaiun": "eh",
    "Africa/Freetown": "sl",
    "Africa/Gaborone": "bw",
    "Africa/Harare": "zw",
    "Africa/Johannesburg": "za",
    "Africa/Juba": "ss",
    "Africa/Kampala": "ug",
    "Africa/Khartoum": "sd",
    "Africa/Kigali": "rw",
    "Africa/Kinshasa": "cd",
    "Africa/Lagos": "ng",
    "Africa/Libreville": "ga",
    "Africa/Lome": "tg",
    "Africa/Luanda": "ao",
    "Africa/Lubumbashi": "cd",
    "Africa/Lusaka": "zm",
    "Africa/Malabo": "gq",
    "Africa/Maputo": "mz",
    "Africa/Maseru": "ls",
    "Africa/Mbabane": "sz",
    "Africa/Mogadishu": "so",
    "Africa/Monrovia": "lr",
    "Africa/Nairobi": "ke",
    "Africa/Ndjamena": "td",
    "Africa/Niamey": "ne",
    "Africa/Nouakchott": "mr",
    "Africa/Ouagadougou": "bf",
    "Africa/Porto-Novo": "bj",
    "Africa/Sao_Tome": "st",
    "Africa/Tripoli": "ly",
    "Africa/Tunis": "tn",
    "Africa/Windhoek": "na",
    "America/Anchorage": "us",
    "America/Antigua": "ag",
    "America/Araguaina": "br",
    "America/Argentina/Buenos_Aires": "ar",
    "America/Argentina/Catamarca": "ar",
    "America/Argentina/Cordoba": "ar",
    "America/Argentina/Jujuy": "ar",
    "America/Argentina/La_Rioja": "ar",
    "America/Argentina/Mendoza": "ar",
    "America/Argentina/Rio_Gallegos": "ar",
    "America/Argentina/Salta": "ar",
    "America/Argentina/San_Juan": "ar",
    "America/Argentina/San_Luis": "ar",
    "America/Argentina/Tucuman": "ar",
    "America/Argentina/Ushuaia": "ar",
    "America/Aruba": "aw",
    "America/Asuncion": "py",
    "America/Bahia": "br",
    "America/Bahia_Banderas": "mx",
    "America/Barbados": "bb",
    "America/Belem": "br",
    "America/Belize": "bz",
    "America/Boa_Vista": "br",
    "America/Bogota": "co",
    "America/Boise": "us",
    "America/Campo_Grande": "br",
    "America/Cancun": "mx",
    "America/Caracas": "ve",
    "America/Cayenne": "gf",
    "America/Cayman": "ky",
    "America/Chicago": "us",
    "America/Chihuahua": "mx",
    "America/Ciudad_Juarez": "mx",
    "America/Costa_Rica": "cr",
    "America/Coyhaique": "cl",
    "America/Cuiaba": "br",
    "America/Curacao": "cw",
    "America/Dawson_Creek": "ca",
    "America/Denver": "us",
    "America/Detroit": "us",
    "America/Dominica": "dm",
    "America/Edmonton": "ca",
    "America/Eirunepe": "br",
    "America/El_Salvador": "sv",
    "America/Fortaleza": "br",
    "America/Glace_Bay": "ca",
    "America/Grand_Turk": "tc",
    "America/Guadeloupe": "gp",
    "America/Guatemala": "gt",
    "America/Guayaquil": "ec",
    "America/Guyana": "gy",
    "America/Halifax": "ca",
    "America/Havana": "cu",
    "America/Hermosillo": "mx",
    "America/Indiana/Indianapolis": "us",
    "America/Indiana/Vincennes": "us",
    "America/Iqaluit": "ca",
    "America/Jamaica": "jm",
    "America/Juneau": "us",
    "America/Kentucky/Louisville": "us",
    "America/Kralendijk": "bq",
    "America/La_Paz": "bo",
    "America/Lima": "pe",
    "America/Los_Angeles": "us",
    "America/Maceio": "br",
    "America/Managua": "ni",
    "America/Manaus": "br",
    "America/Martinique": "mq",
    "America/Matamoros": "mx",
    "America/Mazatlan": "mx",
    "America/Merida": "mx",
    "America/Mexico_City": "mx",
    "America/Moncton": "ca",
    "America/Monterrey": "mx",
    "America/Montevideo": "uy",
    "America/Nassau": "bs",
    "America/New_York": "us",
    "America/North_Dakota/New_Salem": "us",
    "America/Nuuk": "gl",
    "America/Ojinaga": "mx",
    "America/Panama": "pa",
    "America/Paramaribo": "sr",
    "America/Phoenix": "us",
    "America/Port-au-Prince": "ht",
    "America/Port_of_Spain": "tt",
    "America/Porto_Velho": "br",
    "America/Puerto_Rico": "pr",
    "America/Punta_Arenas": "cl",
    "America/Recife": "br",
    "America/Regina": "ca",
    "America/Rio_Branco": "br",
    "America/Santarem": "br",
    "America/Santiago": "cl",
    "America/Santo_Domingo": "do",
    "America/Sao_Paulo": "br",
    "America/St_Johns": "ca",
    "America/St_Kitts": "kn",
    "America/St_Lucia": "lc",
    "America/St_Thomas": "vi",
    "America/St_Vincent": "vc",
    "America/Swift_Current": "ca",
    "America/Tegucigalpa": "hn",
    "America/Tijuana": "mx",
    "America/Toronto": "ca",
    "America/Vancouver": "ca",
    "America/Whitehorse": "ca",
    "America/Winnipeg": "ca",
    "Asia/Aden": "ye",
    "Asia/Almaty": "kz",
    "Asia/Amman": "jo",
    "Asia/Anadyr": "ru",
    "Asia/Aqtau": "kz",
    "Asia/Aqtobe": "kz",
    "Asia/Ashgabat": "tm",
    "Asia/Atyrau": "kz",
    "Asia/Baghdad": "iq",
    "Asia/Bahrain": "bh",
    "Asia/Baku": "az",
    "Asia/Bangkok": "th",
    "Asia/Barnaul": "ru",
    "Asia/Beirut": "lb",
    "Asia/Bishkek": "kg",
    "Asia/Brunei": "bn",
    "Asia/Chita": "ru",
    "Asia/Colombo": "lk",
    "Asia/Damascus": "sy",
    "Asia/Dhaka": "bd",
    "Asia/Dili": "tl",
    "Asia/Dubai": "ae",
    "Asia/Dushanbe": "tj",
    "Asia/Famagusta": "cy",
    "Asia/Gaza": "ps",
    "Asia/Hebron": "ps",
    "Asia/Ho_Chi_Minh": "vn",
    "Asia/Hong_Kong": "hk",
    "Asia/Hovd": "mn",
    "Asia/Irkutsk": "ru",
    "Asia/Jakarta": "id",
    "Asia/Jayapura": "id",
    "Asia/Jerusalem": "il",
    "Asia/Kabul": "af",
    "Asia/Kamchatka": "ru",
    "Asia/Karachi": "pk",
    "Asia/Kathmandu": "np",
    "Asia/Kolkata": "in",
    "Asia/Krasnoyarsk": "ru",
    "Asia/Kuala_Lumpur": "my",
    "Asia/Kuching": "my",
    "Asia/Kuwait": "kw",
    "Asia/Macau": "mo",
    "Asia/Magadan": "ru",
    "Asia/Makassar": "id",
    "Asia/Manila": "ph",
    "Asia/Muscat": "om",
    "Asia/Nicosia": "cy",
    "Asia/Novokuznetsk": "ru",
    "Asia/Novosibirsk": "ru",
    "Asia/Omsk": "ru",
    "Asia/Oral": "kz",
    "Asia/Phnom_Penh": "kh",
    "Asia/Pontianak": "id",
    "Asia/Pyongyang": "kp",
    "Asia/Qatar": "qa",
    "Asia/Qostanay": "kz",
    "Asia/Qyzylorda": "kz",
    "Asia/Riyadh": "sa",
    "Asia/Sakhalin": "ru",
    "Asia/Samarkand": "uz",
    "Asia/Seoul": "kr",
    "Asia/Shanghai": "cn",
    "Asia/Singapore": "sg",
    "Asia/Taipei": "tw",
    "Asia/Tashkent": "uz",
    "Asia/Tbilisi": "ge",
    "Asia/Tehran": "ir",
    "Asia/Thimphu": "bt",
    "Asia/Tokyo": "jp",
    "Asia/Tomsk": "ru",
    "Asia/Ulaanbaatar": "mn",
    "Asia/Urumqi": "cn",
    "Asia/Vientiane": "la",
    "Asia/Vladivostok": "ru",
    "Asia/Yakutsk": "ru",
    "Asia/Yangon": "mm",
    "Asia/Yekaterinburg": "ru",
    "Asia/Yerevan": "am",
    "Atlantic/Azores": "pt",
    "Atlantic/Canary": "es",
    "Atlantic/Cape_Verde": "cv",
    "Atlantic/Faroe": "fo",
    "Atlantic/Madeira": "pt",
    "Atlantic/Reykjavik": "is",
    "Australia/Adelaide": "au",
    "Australia/Brisbane": "au",
    "Australia/Broken_Hill": "au",
    "Australia/Darwin": "au",
    "Australia/Hobart": "au",
    "Australia/Melbourne": "au",
    "Australia/Perth": "au",
    "Australia/Sydney": "au",
    "Europe/Amsterdam": "nl",
    "Europe/Andorra": "ad",
    "Europe/Astrakhan": "ru",
    "Europe/Athens": "gr",
    "Europe/Belgrade": "rs",
    "Europe/Berlin": "de",
    "Europe/Bratislava": "sk",
    "Europe/Brussels": "be",
    "Europe/Bucharest": "ro",
    "Europe/Budapest": "hu",
    "Europe/Chisinau": "md",
    "Europe/Copenhagen": "dk",
    "Europe/Dublin": "ie",
    "Europe/Guernsey": "gg",
    "Europe/Helsinki": "fi",
    "Europe/Isle_of_Man": "im",
    "Europe/Istanbul": "tr",
    "Europe/Jersey": "je",
    "Europe/Kaliningrad": "ru",
    "Europe/Kirov": "ru",
    "Europe/Kyiv": "ua",
    "Europe/Lisbon": "pt",
    "Europe/Ljubljana": "si",
    "Europe/London": "gb",
    "Europe/Luxembourg": "lu",
    "Europe/Madrid": "es",
    "Europe/Malta": "mt",
    "Europe/Mariehamn": "ax",
    "Europe/Minsk": "by",
    "Europe/Monaco": "mc",
    "Europe/Moscow": "ru",
    "Europe/Oslo": "no",
    "Europe/Paris": "fr",
    "Europe/Podgorica": "me",
    "Europe/Prague": "cz",
    "Europe/Riga": "lv",
    "Europe/Rome": "it",
    "Europe/Samara": "ru",
    "Europe/San_Marino": "sm",
    "Europe/Sarajevo": "ba",
    "Europe/Saratov": "ru",
    "Europe/Simferopol": "ua",
    "Europe/Skopje": "mk",
    "Europe/Sofia": "bg",
    "Europe/Stockholm": "se",
    "Europe/Tallinn": "ee",
    "Europe/Tirane": "al",
    "Europe/Ulyanovsk": "ru",
    "Europe/Vaduz": "li",
    "Europe/Vatican": "va",
    "Europe/Vienna": "at",
    "Europe/Vilnius": "lt",
    "Europe/Volgograd": "ru",
    "Europe/Warsaw": "pl",
    "Europe/Zagreb": "hr",
    "Europe/Zurich": "ch",
    "Indian/Antananarivo": "mg",
    "Indian/Comoro": "km",
    "Indian/Mahe": "sc",
    "Indian/Maldives": "mv",
    "Indian/Mauritius": "mu",
    "Indian/Mayotte": "yt",
    "Indian/Reunion": "re",
    "Pacific/Apia": "ws",
    "Pacific/Auckland": "nz",
    "Pacific/Bougainville": "pg",
    "Pacific/Chuuk": "fm",
    "Pacific/Efate": "vu",
    "Pacific/Fiji": "fj",
    "Pacific/Galapagos": "ec",
    "Pacific/Guadalcanal": "sb",
    "Pacific/Guam": "gu",
    "Pacific/Honolulu": "us",
    "Pacific/Kwajalein": "mh",
    "Pacific/Majuro": "mh",
    "Pacific/Noumea": "nc",
    "Pacific/Pago_Pago": "as",
    "Pacific/Palau": "pw",
    "Pacific/Pohnpei": "fm",
    "Pacific/Port_Moresby": "pg",
    "Pacific/Rarotonga": "ck",
    "Pacific/Saipan": "mp",
    "Pacific/Tahiti": "pf",
    "Pacific/Tarawa": "ki",
    "Pacific/Tongatapu": "to",
}

# Zones shared across a border where the tzdb's primary country isn't the city's.
_SLUG_OVERRIDE: dict[str, str] = {
    "pristina": "xk",  # Kosovo shares Europe/Belgrade with Serbia
}


def country_code(loc: Location) -> str | None:
    """ISO 3166-1 alpha-2 (lowercase) for a real city; None for ocean/region
    reference points (which have no country).

    ``loc.country`` (GeoNames, per city) wins where present. Deriving the country
    from the timezone is only a fallback for the curated entries, because a
    timezone maps to a country and not the other way round: 41 Vietnamese cities
    are filed under ``Asia/Bangkok`` in GeoNames and were being reported - flag,
    warming ranking and all - as Thai."""
    if getattr(loc, "kind", "city") != "city":
        return None
    return (getattr(loc, "country", None) or _SLUG_OVERRIDE.get(loc.slug)
            or _TZ_CC.get(loc.timezone))


def flag_url(cc: str) -> str:
    """A small flag PNG (20x15) for a lowercase ISO 3166-1 alpha-2 code."""
    return f"https://flagcdn.com/20x15/{cc}.png"


def tz_country_map() -> dict[str, str]:
    """A copy of the IANA-timezone -> ISO2 map, for the browser to guess the
    visitor's country from ``Intl…timeZone`` (offline, no geolocation prompt)."""
    return dict(_TZ_CC)


# Country (ISO2) -> the site language spoken there, for guessing the visitor's
# language from their location. Only countries whose primary language is one we
# actually ship are listed; anything else falls back to the browser's language
# preference, then the site default. Ambiguous multilingual countries are left
# out on purpose (let the browser decide).
_CC_LANG: dict[str, str] = {
    "us": "en", "gb": "en", "ca": "en", "au": "en", "nz": "en", "ie": "en",
    "pl": "pl",
    "de": "de", "at": "de", "ch": "de", "li": "de",
    "fr": "fr", "mc": "fr",
    "es": "es", "mx": "es", "ar": "es", "co": "es", "cl": "es", "pe": "es",
    "ve": "es", "ec": "es", "bo": "es", "py": "es", "uy": "es", "gt": "es",
    "cu": "es", "do": "es", "hn": "es", "ni": "es", "cr": "es", "pa": "es",
    "sv": "es",
    "ua": "uk",
    "ru": "ru", "by": "ru", "kz": "ru", "kg": "ru",
    "it": "it", "sm": "it", "va": "it",
    "pt": "pt", "br": "pt", "ao": "pt", "mz": "pt", "cv": "pt",
    "nl": "nl",
    "tr": "tr",
    "id": "id",
    "vn": "vi",
    "cn": "zh", "tw": "zh", "hk": "zh",
    "jp": "ja",
    "kr": "ko", "kp": "ko",
    "in": "hi",
    "bd": "bn",
    "eg": "ar", "sa": "ar", "dz": "ar", "ma": "ar", "iq": "ar", "sy": "ar",
    "ye": "ar", "jo": "ar", "lb": "ar", "ly": "ar", "tn": "ar", "ae": "ar",
    "om": "ar", "qa": "ar", "kw": "ar", "bh": "ar", "sd": "ar", "mr": "ar",
    "pk": "ur",
    "ir": "fa",
}


def country_lang_map() -> dict[str, str]:
    """A copy of the country -> site-language map (for language auto-detect)."""
    return dict(_CC_LANG)


# ISO-2 country code -> population (GeoNames countryInfo, 2018-era estimates).
# Feeds the "N people live in this warming country" figure in the country ranking.
_CC_POP: dict[str, int] = {
    "ad": 77006, "ae": 9630959, "af": 37172386, "ag": 96286, "ai": 13254, "al": 2866376,
    "am": 3090500, "an": 300000, "ao": 30809762, "aq": 0, "ar": 44494502, "as": 55465,
    "at": 8847037, "au": 24992369, "aw": 105845, "ax": 26711, "az": 10224900,
    "ba": 3323929, "bb": 286641, "bd": 161356039, "be": 11422068, "bf": 19751535,
    "bg": 7000039, "bh": 1569439, "bi": 11175378, "bj": 11485048, "bl": 8450, "bm": 63968,
    "bn": 428962, "bo": 11353142, "bq": 18012, "br": 209469333, "bs": 385640, "bt": 754394,
    "bv": 0, "bw": 2254126, "by": 9485386, "bz": 383071, "ca": 37058856, "cc": 628,
    "cd": 84068091, "cf": 4666377, "cg": 5244363, "ch": 8516543, "ci": 25069229,
    "ck": 21388, "cl": 18729160, "cm": 25216237, "cn": 1411778724, "co": 49648685,
    "cr": 4999441, "cs": 10829175, "cu": 11338138, "cv": 543767, "cw": 159849, "cx": 1500,
    "cy": 1189265, "cz": 10625695, "de": 82927922, "dj": 958920, "dk": 5797446,
    "dm": 71625, "do": 10627165, "dz": 42228429, "ec": 17084357, "ee": 1320884,
    "eg": 98423595, "eh": 273008, "er": 6209262, "es": 46723749, "et": 109224559,
    "fi": 5518050, "fj": 883483, "fk": 2638, "fm": 112640, "fo": 48497, "fr": 66987244,
    "ga": 2119275, "gb": 66488991, "gd": 111454, "ge": 3704500, "gf": 195506, "gg": 65228,
    "gh": 29767108, "gi": 33718, "gl": 56025, "gm": 2280102, "gn": 12414318, "gp": 443000,
    "gq": 1308974, "gr": 10727668, "gs": 30, "gt": 17247807, "gu": 165768, "gw": 1874309,
    "gy": 779004, "hk": 7396076, "hm": 0, "hn": 9587522, "hr": 3871833, "ht": 11123176,
    "hu": 9768785, "id": 267663435, "ie": 4853506, "il": 8883800, "im": 84077,
    "in": 1352617328, "io": 4000, "iq": 38433600, "ir": 81800269, "is": 353574,
    "it": 60431283, "je": 90812, "jm": 2934855, "jo": 9956011, "jp": 126529100,
    "ke": 51393010, "kg": 6315800, "kh": 16249798, "ki": 115847, "km": 832322, "kn": 52441,
    "kp": 25549819, "kr": 51635256, "kw": 4137309, "ky": 64174, "kz": 18276499,
    "la": 7061507, "lb": 6848925, "lc": 181889, "li": 37910, "lk": 21670000, "lr": 4818977,
    "ls": 2108132, "lt": 2789533, "lu": 607728, "lv": 1926542, "ly": 6678567,
    "ma": 36029138, "mc": 38682, "md": 3545883, "me": 622345, "mf": 37264, "mg": 26262368,
    "mh": 58413, "mk": 2082958, "ml": 19077690, "mm": 53708395, "mn": 3170208,
    "mo": 631636, "mp": 56882, "mq": 432900, "mr": 4403319, "ms": 9341, "mt": 483530,
    "mu": 1265303, "mv": 515696, "mw": 17563749, "mx": 126190788, "my": 31528585,
    "mz": 29495962, "na": 2448255, "nc": 284060, "ne": 22442948, "nf": 1828,
    "ng": 195874740, "ni": 6465513, "nl": 17231017, "no": 5314336, "np": 28087871,
    "nr": 12704, "nu": 2166, "nz": 4885500, "om": 4829483, "pa": 4176873, "pe": 31989256,
    "pf": 277679, "pg": 8606316, "ph": 106651922, "pk": 212215030, "pl": 37978548,
    "pm": 7012, "pn": 46, "pr": 3195153, "ps": 4569087, "pt": 10281762, "pw": 17907,
    "py": 6956071, "qa": 2781677, "re": 776948, "ro": 19473936, "rs": 6982084,
    "ru": 144478050, "rw": 12301939, "sa": 33699947, "sb": 652858, "sc": 96762,
    "sd": 41801533, "se": 10183175, "sg": 5638676, "sh": 7460, "si": 2067372, "sj": 2550,
    "sk": 5447011, "sl": 7650154, "sm": 33785, "sn": 15854360, "so": 15008154,
    "sr": 575991, "ss": 8260490, "st": 197700, "sv": 6420744, "sx": 40654, "sy": 16906283,
    "sz": 1136191, "tc": 37665, "td": 15477751, "tf": 140, "tg": 7889094, "th": 69428524,
    "tj": 9100837, "tk": 1466, "tl": 1267972, "tm": 5850908, "tn": 11565204, "to": 103197,
    "tr": 82319724, "tt": 1389858, "tv": 11508, "tw": 23451837, "tz": 56318348,
    "ua": 40000000, "ug": 42723139, "um": 0, "us": 327167434, "uy": 3449299,
    "uz": 32955400, "va": 921, "vc": 110211, "ve": 28870195, "vg": 29802, "vi": 106977,
    "vn": 95540395, "vu": 292680, "wf": 16025, "ws": 196130, "xk": 1845300, "ye": 28498687,
    "yt": 279471, "za": 57779622, "zm": 17351822, "zw": 16868409,
}


def country_population(cc: str) -> int:
    """Population for an ISO-2 country code, or 0 if unknown."""
    return _CC_POP.get((cc or "").lower(), 0)


# Approximate nominal GDP per capita (USD, ~2023, rounded), by ISO-2 code. These
# are public reference figures used ONLY to prioritise the data-download queue
# (wealthier countries first, since early visitors skew that way) - they are
# never displayed on the site. Unlisted countries fall back to _GDP_DEFAULT,
# which sits low in the table but not below it - the ten listed countries poorer
# than that default still queue after an unlisted one. Approximation is fine
# here: this only decides fetch order, never a displayed figure.
_GDP_PC: dict[str, int] = {
    "lu": 128000, "ie": 104000, "ch": 93000, "no": 87000, "sg": 85000,
    "qa": 81000, "us": 81000, "is": 79000, "dk": 68000, "au": 65000,
    "nl": 64000, "sm": 59000, "il": 55000, "se": 56000, "at": 56000,
    "fi": 54000, "de": 54000, "be": 54000, "ca": 54000, "ae": 53000,
    "hk": 51000, "gb": 49000, "nz": 48000, "fr": 46000, "mo": 45000,
    "ad": 42000, "mt": 38000, "it": 39000, "kr": 35000, "cy": 34000,
    "jp": 34000, "sa": 33000, "kw": 33000, "es": 33000, "si": 32000,
    "ee": 31000, "cz": 31000, "bh": 30000, "pt": 28000, "lt": 27000,
    "sk": 24000, "lv": 24000, "gr": 23000, "uy": 22000, "om": 22000,
    "pl": 22000, "hu": 22000, "hr": 20000, "pa": 18000, "ro": 18000,
    "cl": 17000, "cr": 14000, "bg": 15000, "ar": 14000, "mx": 13000,
    "ru": 13000, "tr": 13000, "cn": 12600, "kz": 13000, "my": 12000,
    "rs": 12000, "br": 11000, "me": 11000, "bw": 7500, "th": 7500,
    "za": 6500, "co": 6800, "pe": 7900, "ec": 6500, "id": 5000,
    "eg": 3500, "ph": 3900, "ma": 3700, "ua": 5000, "vn": 4300,
    "bd": 2700, "in": 2600, "ke": 2100, "ng": 2200, "gh": 2400,
    "pk": 1600, "et": 1500, "tz": 1200, "ug": 1000, "af": 400,
}
_GDP_DEFAULT = 3000


def gdp_per_capita(cc: str | None) -> int:
    """Approximate nominal GDP per capita (USD) for an ISO-2 code, or a low
    fallback if unlisted/unknown. For download-queue prioritisation only."""
    return _GDP_PC.get((cc or "").lower(), _GDP_DEFAULT)


def download_priority_key(loc: Location) -> tuple[int, str]:
    """Sort key for the data-download queue: highest GDP-per-capita country
    first (early visitors skew toward wealthier countries), ties broken by slug
    for a stable order. Ocean/region reference points have no country and so
    queue on the unlisted-country default, mid-pack; only their mean is used
    anyway (they are map-only, never rendered as a city page)."""
    return (-gdp_per_capita(country_code(loc)), loc.slug)
