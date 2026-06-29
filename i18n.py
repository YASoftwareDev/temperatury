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
        "ns": "n.s.",
        "smoothed": "smoothed (LOESS)",
        "guide_title": "ℹ️ How to read these charts",
        "guide_body":
            "<li><b>Dots / bars</b> — the value for each individual year.</li>"
            "<li><b>Bold coloured curve</b> — a LOESS smoother: the local trend, "
            "free to bend, so you can see the rate change over time (e.g. warming "
            "accelerating after ~1985).</li>"
            "<li><b>Dashed line</b> — the straight robust (Theil–Sen) trend; its "
            "slope is the “per decade” figure in the legend.</li>"
            "<li><b>p&lt;0.05 / n.s.</b> — Mann–Kendall significance: whether the "
            "trend is statistically real or could just be noise (n.s. = not "
            "significant). Temperature is usually highly significant; rainfall "
            "often isn't.</li>"
            "<li><b>Shaded band</b> — the full historical range across all years "
            "for that month.</li>"
            "<li><b>Heatmap colours</b> — temperature (blue cold → red warm); read "
            "a column from bottom to top to watch that month change over the "
            "years.</li>",
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
        "cap_yearly": "Annual mean with a LOESS smoother (shows acceleration) and "
                      "a robust Theil–Sen trend + significance",
        "cap_anomalies": "Each year compared to the 1961–1990 average — red bars "
                         "warmer, blue cooler. The shift from mostly blue to mostly "
                         "red is the warming.",
        "cap_heatmap": "Every month's average for every year as a colour grid "
                       "(2 °C bands). Read a column upward to watch that month warm "
                       "over the decades.",
        "cap_anom_heatmap": "Same grid, but each month is measured against its own "
                            "1961–1990 normal, so only the change shows (red warmer "
                            "than usual, blue cooler) — the seasonal cycle removed.",
        "cap_threshold": "Days each year above 18 °C (hot) and below 0 °C (freezing). "
                         "The two robust trends crossing means hot days now outnumber "
                         "freezing days.",
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
        "record_title": "Monthly record high/low daily temperature — {name}",
        "record_band": "record range {start}–{end}",
        "record_latest_high": "{year} highs",
        "record_latest_low": "{year} lows",
        "record_ylabel": "Daily temperature (°C)",
        "cap_records": "Each month's all-time record daily high and low, with the "
                       "latest year's extremes",
        "volatility_title": "Day-to-day temperature swings per year — {name}",
        "volatility_jump": "day-to-day jump",
        "volatility_ylabel": "Days with a big jump",
        "cap_volatility": "How often big day-to-day temperature jumps happen "
                          "each year (≥6 °C) — temperature variability",
        "per_decade_mm": "mm / decade",
        "precip_title": "Annual precipitation — {name}",
        "precip_ylabel": "Precipitation (mm / year)",
        "precip_annual": "annual total",
        "cap_precip": "Total yearly precipitation (rain and snow water) with a trend",
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
        "ns": "nieist.",
        "smoothed": "wygładzenie (LOESS)",
        "guide_title": "ℹ️ Jak czytać te wykresy",
        "guide_body":
            "<li><b>Punkty / słupki</b> — wartość dla każdego roku.</li>"
            "<li><b>Pogrubiona krzywa</b> — wygładzenie LOESS: lokalny trend, który "
            "może się wyginać, więc widać zmianę tempa w czasie (np. przyspieszające "
            "ocieplenie po ~1985).</li>"
            "<li><b>Linia przerywana</b> — prosty, odporny trend (Theil–Sen); jego "
            "nachylenie to wartość „na dekadę” w legendzie.</li>"
            "<li><b>p&lt;0,05 / nieist.</b> — istotność Manna–Kendalla: czy trend "
            "jest statystycznie realny, czy może być tylko szumem (nieist. = "
            "nieistotny). Temperatura jest zwykle istotna; opady często nie.</li>"
            "<li><b>Zacieniony obszar</b> — pełny historyczny zakres ze wszystkich "
            "lat dla danego miesiąca.</li>"
            "<li><b>Kolory mapy ciepła</b> — temperatura (niebieski zimno → czerwony "
            "ciepło); czytaj kolumnę z dołu do góry, by zobaczyć zmianę miesiąca "
            "przez lata.</li>",
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
        "cap_yearly": "Średnia roczna z wygładzeniem LOESS (pokazuje przyspieszenie) "
                      "i odpornym trendem Theila–Sena + istotność",
        "cap_anomalies": "Każdy rok względem średniej 1961–1990 — czerwone słupki "
                         "cieplej, niebieskie chłodniej. Przejście od niebieskich do "
                         "czerwonych to ocieplenie.",
        "cap_heatmap": "Średnia każdego miesiąca w każdym roku jako siatka kolorów "
                       "(pasma 2 °C). Czytaj kolumnę w górę, by zobaczyć ocieplanie "
                       "się miesiąca przez dekady.",
        "cap_anom_heatmap": "Ta sama siatka, ale każdy miesiąc względem własnej normy "
                            "1961–1990, więc widać tylko zmianę (czerwony cieplej, "
                            "niebieski chłodniej) — cykl sezonowy usunięty.",
        "cap_threshold": "Dni w roku powyżej 18 °C (gorące) i poniżej 0 °C (mroźne). "
                         "Przecięcie odpornych trendów oznacza, że dni gorących jest "
                         "już więcej niż mroźnych.",
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
        "record_title": "Miesięczne rekordy dobowe — maksimum i minimum — {name}",
        "record_band": "zakres rekordów {start}–{end}",
        "record_latest_high": "maksima {year}",
        "record_latest_low": "minima {year}",
        "record_ylabel": "Temperatura dobowa (°C)",
        "cap_records": "Rekordowe dobowe maksimum i minimum każdego miesiąca, "
                       "z ekstremami ostatniego roku",
        "volatility_title": "Skoki temperatury z dnia na dzień w roku — {name}",
        "volatility_jump": "skok z dnia na dzień",
        "volatility_ylabel": "Dni z dużym skokiem",
        "cap_volatility": "Jak często zdarzają się duże skoki temperatury z dnia "
                          "na dzień (≥6 °C) — zmienność temperatury",
        "per_decade_mm": "mm / dekadę",
        "precip_title": "Roczne opady — {name}",
        "precip_ylabel": "Opady (mm / rok)",
        "precip_annual": "suma roczna",
        "cap_precip": "Roczna suma opadów (deszcz i woda ze śniegu) z linią trendu",
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
        "ns": "n. s.",
        "smoothed": "Glättung (LOESS)",
        "guide_title": "ℹ️ So lesen Sie diese Diagramme",
        "guide_body":
            "<li><b>Punkte / Balken</b> — der Wert für jedes einzelne Jahr.</li>"
            "<li><b>Fette farbige Kurve</b> — LOESS-Glättung: der lokale Trend, der "
            "sich biegen darf, sodass die Änderung der Rate sichtbar wird (z. B. "
            "beschleunigte Erwärmung nach ~1985).</li>"
            "<li><b>Gestrichelte Linie</b> — der gerade robuste (Theil–Sen) Trend; "
            "seine Steigung ist der Wert „pro Dekade“ in der Legende.</li>"
            "<li><b>p&lt;0,05 / n. s.</b> — Mann–Kendall-Signifikanz: ob der Trend "
            "statistisch real ist oder nur Rauschen sein könnte (n. s. = nicht "
            "signifikant). Temperatur ist meist signifikant, Niederschlag oft "
            "nicht.</li>"
            "<li><b>Schattiertes Band</b> — die gesamte historische Spanne über "
            "alle Jahre für diesen Monat.</li>"
            "<li><b>Heatmap-Farben</b> — Temperatur (blau kalt → rot warm); lesen "
            "Sie eine Spalte von unten nach oben, um die Veränderung des Monats "
            "über die Jahre zu sehen.</li>",
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
        "cap_yearly": "Jahresmittel mit LOESS-Glättung (zeigt Beschleunigung) und "
                      "robustem Theil–Sen-Trend + Signifikanz",
        "cap_anomalies": "Jedes Jahr im Vergleich zum Mittel 1961–1990 — rote Balken "
                         "wärmer, blaue kühler. Der Wechsel von Blau zu Rot ist die "
                         "Erwärmung.",
        "cap_heatmap": "Der Monatsdurchschnitt jedes Jahres als Farbraster "
                       "(2-°C-Stufen). Lesen Sie eine Spalte nach oben, um die "
                       "Erwärmung des Monats über die Jahrzehnte zu sehen.",
        "cap_anom_heatmap": "Dasselbe Raster, aber jeder Monat an seiner eigenen Norm "
                            "1961–1990 gemessen, sodass nur die Änderung sichtbar ist "
                            "(rot wärmer, blau kühler) — Jahreszyklus entfernt.",
        "cap_threshold": "Tage pro Jahr über 18 °C (heiß) und unter 0 °C (Frost). Wo "
                         "sich die robusten Trends kreuzen, gibt es nun mehr heiße "
                         "als Frosttage.",
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
        "record_title": "Monatliche Rekord-Höchst-/Tiefstwerte (Tageswerte) — {name}",
        "record_band": "Rekordspanne {start}–{end}",
        "record_latest_high": "Höchstwerte {year}",
        "record_latest_low": "Tiefstwerte {year}",
        "record_ylabel": "Tagestemperatur (°C)",
        "cap_records": "Rekord-Tageshöchst- und -tiefstwerte je Monat, mit den "
                       "Extremen des aktuellen Jahres",
        "volatility_title": "Tag-zu-Tag-Temperatursprünge pro Jahr — {name}",
        "volatility_jump": "Tagessprung",
        "volatility_ylabel": "Tage mit großem Sprung",
        "cap_volatility": "Wie oft große Tag-zu-Tag-Temperatursprünge pro Jahr "
                          "auftreten (≥6 °C) — Temperaturschwankung",
        "per_decade_mm": "mm / Dekade",
        "precip_title": "Jährlicher Niederschlag — {name}",
        "precip_ylabel": "Niederschlag (mm / Jahr)",
        "precip_annual": "Jahressumme",
        "cap_precip": "Jährliche Niederschlagssumme (Regen und Schmelzwasser) mit Trend",
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
