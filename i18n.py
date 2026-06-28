"""Translations for the website and the chart labels.

Each language is a flat dict of strings; ``{...}`` fields are filled with
``str.format``. Add a language by adding one entry to ``TRANSLATIONS`` and
listing its code in ``LANGUAGES`` — everything else (pages, charts, switcher)
is generated from this table.
"""

from __future__ import annotations

# Order shown in the switcher; first entry is the site default (root URL).
LANGUAGES = ["pl", "en", "de"]
DEFAULT_LANG = "pl"

# Native language names for the switcher (same in every language).
LANG_NAMES = {"pl": "Polski", "en": "English", "de": "Deutsch"}


TRANSLATIONS: dict[str, dict] = {
    "en": {
        "html_lang": "en",
        "per_decade_c": "°C / decade",
        "per_decade_days": "days / decade",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        # charts
        "threshold_title": "Hot & freezing days per year — {name}",
        "threshold_hot": "hot days (>{t:.0f} °C)",
        "threshold_freeze": "freezing days (<{t:.0f} °C)",
        "days_per_year": "Days per year",
        "year": "Year",
        "month": "Month",
        "yearly_title": "Annual mean temperature through the years — {name}",
        "yearly_ylabel": "Annual mean temperature (°C)",
        "annual_mean": "annual mean",
        "trend": "trend",
        "anomaly_title": "Annual temperature anomaly — {name}",
        "anomaly_ylabel": "Anomaly (°C)",
        "vs_baseline": "vs. {lo}–{hi} mean ({base:.1f} °C)",
        "vs_full": "vs. full-period mean ({base:.1f} °C)",
        "heatmap_title": "Monthly mean temperature by year — {name}",
        "heatmap_cbar": "Monthly mean (°C)",
        "anom_heatmap_title": "Monthly anomaly vs. {base} — {name}",
        "anom_heatmap_cbar": "Anomaly vs. {base} (°C)",
        "full_period": "full-period",
        "dashboard_suptitle": "{name} temperatures {start}–{end} "
                              "(source: Open-Meteo reanalysis)",
        # page
        "page_title": "{name} temperatures",
        "subtitle": "{start}–{end} · {days} days · warmest {wy} ({wv:.1f} °C), "
                    "coldest {cy} ({cv:.1f} °C)",
        "card_trend": "Warming trend",
        "card_mean": "Mean daily temp",
        "card_warmest": "Warmest year",
        "card_coldest": "Coldest year",
        "cap_yearly": "Annual mean temperature with least-squares trend",
        "cap_anomalies": "Yearly anomaly vs. 1961–1990 (blue cooler, red warmer)",
        "cap_heatmap": "Monthly mean by year — which seasons warm",
        "cap_anom_heatmap": "Monthly anomaly vs. 1961–1990 — warming per month",
        "cap_threshold": "Hot (&gt;18 °C) &amp; freezing (&lt;0 °C) days per year",
        "hint": "Click anywhere or press Esc to close",
        "site_title": "European capital temperatures",
        "map_heading": "Temperatures across Europe",
        "map_sub": "Pick a capital on the map — or from the list",
        "choose_city": "Choose a city…",
        "back_to_map": "🗺 Map",
        "range_title": "Monthly temperature range across the years — {name}",
        "range_min_max": "min–max {start}–{end}",
        "range_average": "average",
        "range_latest": "latest ({year})",
        "range_ylabel": "Monthly mean temperature (°C)",
        "cap_range": "Each month's min–max range over the years, with the latest "
                     "year — is it hugging the warm edge?",
        "footer": 'Generated {date} · data from '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  'historical reanalysis (ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'source on GitHub</a>',
    },
    "pl": {
        "html_lang": "pl",
        "per_decade_c": "°C / dekadę",
        "per_decade_days": "dni / dekadę",
        "months": ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                   "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"],
        "threshold_title": "Dni gorące i mroźne w roku — {name}",
        "threshold_hot": "dni gorące (>{t:.0f} °C)",
        "threshold_freeze": "dni mroźne (<{t:.0f} °C)",
        "days_per_year": "Liczba dni w roku",
        "year": "Rok",
        "month": "Miesiąc",
        "yearly_title": "Średnia roczna temperatura na przestrzeni lat — {name}",
        "yearly_ylabel": "Średnia roczna temperatura (°C)",
        "annual_mean": "średnia roczna",
        "trend": "trend",
        "anomaly_title": "Roczna anomalia temperatury — {name}",
        "anomaly_ylabel": "Anomalia (°C)",
        "vs_baseline": "względem średniej {lo}–{hi} ({base:.1f} °C)",
        "vs_full": "względem średniej z całego okresu ({base:.1f} °C)",
        "heatmap_title": "Średnia miesięczna temperatura wg lat — {name}",
        "heatmap_cbar": "Średnia miesięczna (°C)",
        "anom_heatmap_title": "Anomalia miesięczna względem {base} — {name}",
        "anom_heatmap_cbar": "Anomalia względem {base} (°C)",
        "full_period": "całego okresu",
        "dashboard_suptitle": "Temperatury — {name} {start}–{end} "
                              "(źródło: reanaliza Open-Meteo)",
        "page_title": "Temperatury — {name}",
        "subtitle": "{start}–{end} · {days} dni · najcieplejszy {wy} "
                    "({wv:.1f} °C), najzimniejszy {cy} ({cv:.1f} °C)",
        "card_trend": "Trend ocieplenia",
        "card_mean": "Średnia dobowa",
        "card_warmest": "Najcieplejszy rok",
        "card_coldest": "Najzimniejszy rok",
        "cap_yearly": "Średnia roczna temperatura z linią trendu",
        "cap_anomalies": "Roczna anomalia względem 1961–1990 "
                         "(niebieski chłodniej, czerwony cieplej)",
        "cap_heatmap": "Średnie miesięczne wg lat — które pory roku się ocieplają",
        "cap_anom_heatmap": "Anomalia miesięczna względem 1961–1990 — "
                            "ocieplenie w każdym miesiącu",
        "cap_threshold": "Dni gorące (&gt;18 °C) i mroźne (&lt;0 °C) w roku",
        "hint": "Kliknij gdziekolwiek lub naciśnij Esc, aby zamknąć",
        "site_title": "Temperatury stolic Europy",
        "map_heading": "Temperatury w Europie",
        "map_sub": "Wybierz stolicę na mapie — lub z listy",
        "choose_city": "Wybierz miasto…",
        "back_to_map": "🗺 Mapa",
        "range_title": "Zakres miesięcznych temperatur na przestrzeni lat — {name}",
        "range_min_max": "min–maks {start}–{end}",
        "range_average": "średnia",
        "range_latest": "ostatni ({year})",
        "range_ylabel": "Średnia miesięczna temperatura (°C)",
        "cap_range": "Zakres min–maks każdego miesiąca w kolejnych latach, "
                     "z ostatnim rokiem — czy zbliża się do maksimum?",
        "footer": 'Wygenerowano {date} · dane z '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(reanaliza historyczna ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'źródło na GitHub</a>',
    },
    "de": {
        "html_lang": "de",
        "per_decade_c": "°C / Dekade",
        "per_decade_days": "Tage / Dekade",
        "months": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "threshold_title": "Heiße und Frosttage pro Jahr — {name}",
        "threshold_hot": "heiße Tage (>{t:.0f} °C)",
        "threshold_freeze": "Frosttage (<{t:.0f} °C)",
        "days_per_year": "Tage pro Jahr",
        "year": "Jahr",
        "month": "Monat",
        "yearly_title": "Jährliche Mitteltemperatur über die Jahre — {name}",
        "yearly_ylabel": "Jährliche Mitteltemperatur (°C)",
        "annual_mean": "Jahresmittel",
        "trend": "Trend",
        "anomaly_title": "Jährliche Temperaturanomalie — {name}",
        "anomaly_ylabel": "Anomalie (°C)",
        "vs_baseline": "ggü. Mittel {lo}–{hi} ({base:.1f} °C)",
        "vs_full": "ggü. Gesamtmittel ({base:.1f} °C)",
        "heatmap_title": "Monatliche Mitteltemperatur nach Jahr — {name}",
        "heatmap_cbar": "Monatsmittel (°C)",
        "anom_heatmap_title": "Monatsanomalie ggü. {base} — {name}",
        "anom_heatmap_cbar": "Anomalie ggü. {base} (°C)",
        "full_period": "Gesamtzeitraum",
        "dashboard_suptitle": "Temperaturen — {name} {start}–{end} "
                              "(Quelle: Open-Meteo Reanalyse)",
        "page_title": "Temperaturen — {name}",
        "subtitle": "{start}–{end} · {days} Tage · wärmstes {wy} ({wv:.1f} °C), "
                    "kältestes {cy} ({cv:.1f} °C)",
        "card_trend": "Erwärmungstrend",
        "card_mean": "Mittlere Tagestemperatur",
        "card_warmest": "Wärmstes Jahr",
        "card_coldest": "Kältestes Jahr",
        "cap_yearly": "Jährliche Mitteltemperatur mit Trendlinie",
        "cap_anomalies": "Jährliche Anomalie ggü. 1961–1990 "
                         "(blau kühler, rot wärmer)",
        "cap_heatmap": "Monatsmittel nach Jahr — welche Jahreszeiten sich erwärmen",
        "cap_anom_heatmap": "Monatsanomalie ggü. 1961–1990 — Erwärmung je Monat",
        "cap_threshold": "Heiße (&gt;18 °C) &amp; Frosttage (&lt;0 °C) pro Jahr",
        "hint": "Klicken Sie irgendwo oder drücken Sie Esc zum Schließen",
        "site_title": "Temperaturen europäischer Hauptstädte",
        "map_heading": "Temperaturen in Europa",
        "map_sub": "Wählen Sie eine Hauptstadt auf der Karte — oder aus der Liste",
        "choose_city": "Stadt wählen…",
        "back_to_map": "🗺 Karte",
        "range_title": "Monatliche Temperaturspanne über die Jahre — {name}",
        "range_min_max": "Min–Max {start}–{end}",
        "range_average": "Durchschnitt",
        "range_latest": "aktuell ({year})",
        "range_ylabel": "Monatliche Mitteltemperatur (°C)",
        "cap_range": "Min–Max-Spanne jedes Monats über die Jahre, mit dem "
                     "aktuellen Jahr — liegt es am oberen Rand?",
        "footer": 'Erstellt {date} · Daten von '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(historische Reanalyse ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'Quelle auf GitHub</a>',
    },
}


def get(lang: str) -> dict:
    """Return the translation table for ``lang`` (falls back to default)."""
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
