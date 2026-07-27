"""The "deep history" note: the long pre-1940 record a city holds, if any.

WHY the charts start in 1940 (the ERA5 reanalysis begins that year, and earlier
estimates rest on sparser observations with larger uncertainty) is answered once,
in the Q&A tab - ``report._ABOUT_QA``. What this module supplies is the part that
is per-city and lives nowhere else: for a place holding one of the world's long
instrumental records, a line naming that record and its start year (a documented
fact, not a reconstructed value).

``RECORDS`` maps a city slug to ``(label, start_year)``. ``overlay(tr, lang)``
merges the localised line onto a language's table; it is translated for every
supported language.
"""

from __future__ import annotations

# Label is a proper noun (the series/station name) so it reads correctly inside
# any language's sentence: no English connecting words.
RECORDS: dict[str, tuple[str, int]] = {
    "london": ("Central England (HadCET)", 1659),
    "amsterdam": ("De Bilt", 1706),
    "rotterdam": ("De Bilt", 1706),
    "the-hague": ("De Bilt", 1706),
    "utrecht": ("De Bilt", 1706),
    "stockholm": ("Stockholm", 1756),
    "uppsala": ("Uppsala", 1722),
    "berlin": ("Berlin", 1701),
    "vienna": ("Wien / Hohe Warte", 1775),
    "wien": ("Wien / Hohe Warte", 1775),
    "prague": ("Praha-Klementinum", 1775),
    "praha": ("Praha-Klementinum", 1775),
    "geneva": ("Genève", 1753),
    "milan": ("Milano", 1763),
    "milano": ("Milano", 1763),
    "turin": ("Torino", 1753),
    "torino": ("Torino", 1753),
    "padua": ("Padova", 1725),
    "warsaw": ("Warszawa", 1779),
    "warszawa": ("Warszawa", 1779),
    "budapest": ("Budapest", 1780),
    "paris": ("Paris", 1757),
    "madrid": ("Madrid", 1737),
    "st-petersburg": ("Sankt-Peterburg", 1743),
    "saint-petersburg": ("Sankt-Peterburg", 1743),
    "copenhagen": ("København", 1768),
    "tokyo": ("Tokyo", 1875),
}


# Neutral, concise note translated for every supported language.
_TEXT: dict[str, dict] = {
    "en": {
        "deephist_record":
            "{label} holds one of the longest instrumental temperature records, beginning in {year}.",
    },
    "pl": {
        "deephist_record":
            "{label} prowadzi jedną z najdłuższych instrumentalnych serii temperatury, rozpoczętą w {year} roku.",
    },
    "de": {
        "deephist_record":
            "{label} führt eine der längsten instrumentellen Temperaturreihen, beginnend {year}.",
    },
    "fr": {
        "deephist_record":
            "{label} détient l'une des plus longues séries instrumentales de température, débutée en {year}.",
    },
    "es": {
        "deephist_record":
            "{label} mantiene uno de los registros instrumentales de temperatura más largos, iniciado en {year}.",
    },
    "uk": {
        "deephist_record":
            "{label} веде один із найдовших інструментальних рядів температури, розпочатий у {year} році.",
    },
    "ru": {
        "deephist_record":
            "{label} ведёт один из самых длинных инструментальных рядов температуры, начатый в {year} году.",
    },
    "it": {
        "deephist_record":
            "{label} mantiene una delle più lunghe serie strumentali di temperatura, iniziata nel {year}.",
    },
    "pt": {
        "deephist_record":
            "{label} mantém um dos mais longos registos instrumentais de temperatura, iniciado em {year}.",
    },
    "nl": {
        "deephist_record":
            "{label} houdt een van de langste instrumentele temperatuurreeksen bij, begonnen in {year}.",
    },
    "tr": {
        "deephist_record":
            "{label}, {year} yılında başlayan en uzun aletli sıcaklık kayıtlarından birini tutar.",
    },
    "id": {
        "deephist_record":
            "{label} memegang salah satu catatan suhu instrumental terpanjang, dimulai pada {year}.",
    },
    "vi": {
        "deephist_record":
            "{label} giữ một trong những chuỗi nhiệt độ đo đạc dài nhất, bắt đầu năm {year}.",
    },
    "zh": {
        "deephist_record":
            "{label} 保有最长的器测气温记录之一，始于 {year} 年。",
    },
    "ja": {
        "deephist_record":
            "{label}は最も長い器械観測の気温記録の一つを持ち、{year}年に始まります。",
    },
    "ko": {
        "deephist_record":
            "{label}는 가장 긴 기기 관측 기온 기록 중 하나를 {year}년부터 보유하고 있습니다.",
    },
    "hi": {
        "deephist_record":
            "{label} सबसे लंबे यांत्रिक तापमान अभिलेखों में से एक रखता है, जो {year} में आरंभ हुआ।",
    },
    "bn": {
        "deephist_record":
            "{label} দীর্ঘতম যান্ত্রিক তাপমাত্রা নথিগুলির একটি রাখে, যা {year} সালে শুরু।",
    },
    "ar": {
        "deephist_record":
            "{label} يحفظ أحد أطول سجلات الحرارة المرصودة بالأجهزة، بدأ عام {year}.",
    },
    "ur": {
        "deephist_record":
            "{label} درجہ حرارت کے طویل ترین آلاتی ریکارڈوں میں سے ایک رکھتا ہے، جو {year} میں شروع ہوا۔",
    },
    "fa": {
        "deephist_record":
            "{label} یکی از طولانی‌ترین سوابق دمای ابزاری را نگه می‌دارد که در {year} آغاز شده است.",
    },
}

import extra_i18n  # noqa: E402
extra_i18n.fill(_TEXT, "deephist")


def overlay(tr: dict, lang: str) -> dict:
    """Return ``tr`` with deep-history strings merged in (English backfills)."""
    keys = {**_TEXT["en"], **_TEXT.get(lang, {})}
    return {**tr, **keys}


def record_for(slug: str):
    """``(label, year)`` for a city with a famous long record, else ``None``."""
    return RECORDS.get(slug)
