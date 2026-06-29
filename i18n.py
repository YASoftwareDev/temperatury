"""Translations for the website and the chart labels.

Each language is a flat dict of strings; ``{...}`` fields are filled with
``str.format``. Add a language by adding one entry to ``TRANSLATIONS`` and
listing its code in ``LANGUAGES`` — everything else (pages, charts, switcher)
is generated from this table.
"""

from __future__ import annotations

# Order shown in the switcher; first entry is the site default (root URL).
LANGUAGES = ["pl", "en", "de", "fr", "es", "uk"]
DEFAULT_LANG = "pl"

# Native language names for the switcher (same in every language).
LANG_NAMES = {"pl": "Polski", "en": "English", "de": "Deutsch",
              "fr": "Français", "es": "Español", "uk": "Українська"}


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
        "site_title": "World capital temperatures",
        "map_heading": "Temperatures around the world",
        "map_sub": "Pick a capital on the map — or from the list",
        "regions": {"Europe": "Europe", "Asia": "Asia",
                    "Middle East": "Middle East", "Africa": "Africa",
                    "North America": "North America",
                    "South America": "South America", "Oceania": "Oceania"},
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
        "stripes_title": "Warming stripes — {name}",
        "stripes_cbar": "Anomaly vs. {lo}–{hi} (°C)",
        "cap_stripes": "Each stripe is one year's temperature — blue cooler, red "
                       "warmer than the 1961–1990 average. The drift from blue to "
                       "red is the warming, with nothing to read but colour.",
        "season_title": "Growing-season length — {name}",
        "season_ylabel": "Growing-season length (days)",
        "season_annual": "season length",
        "cap_season": "Length of the thermal growing season each year (run of days "
                      "with a daily mean ≥ 5 °C) — the frost-free window farming "
                      "depends on, lengthening as the climate warms.",
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
        "site_title": "Temperatury stolic świata",
        "map_heading": "Temperatury na świecie",
        "map_sub": "Wybierz stolicę na mapie — lub z listy",
        "regions": {"Europe": "Europa", "Asia": "Azja",
                    "Middle East": "Bliski Wschód", "Africa": "Afryka",
                    "North America": "Ameryka Północna",
                    "South America": "Ameryka Południowa", "Oceania": "Oceania"},
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
        "stripes_title": "Pasy ocieplenia — {name}",
        "stripes_cbar": "Anomalia względem {lo}–{hi} (°C)",
        "cap_stripes": "Każdy pas to jeden rok — niebieski chłodniejszy, czerwony "
                       "cieplejszy od średniej 1961–1990. Przejście od niebieskiego "
                       "do czerwonego to ocieplenie, czytelne samym kolorem.",
        "season_title": "Długość sezonu wegetacyjnego — {name}",
        "season_ylabel": "Długość sezonu wegetacyjnego (dni)",
        "season_annual": "długość sezonu",
        "cap_season": "Długość termicznego sezonu wegetacyjnego w każdym roku (ciąg "
                      "dni ze średnią dobową ≥ 5 °C) — bezmroźne okno, od którego "
                      "zależy rolnictwo, wydłużające się wraz z ociepleniem.",
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
        "site_title": "Temperaturen der Welthauptstädte",
        "map_heading": "Temperaturen weltweit",
        "map_sub": "Wählen Sie eine Hauptstadt auf der Karte — oder aus der Liste",
        "regions": {"Europe": "Europa", "Asia": "Asien",
                    "Middle East": "Naher Osten", "Africa": "Afrika",
                    "North America": "Nordamerika",
                    "South America": "Südamerika", "Oceania": "Ozeanien"},
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
        "stripes_title": "Erwärmungsstreifen — {name}",
        "stripes_cbar": "Anomalie ggü. {lo}–{hi} (°C)",
        "cap_stripes": "Jeder Streifen ist ein Jahr — blau kühler, rot wärmer als "
                       "das Mittel 1961–1990. Der Übergang von Blau zu Rot ist die "
                       "Erwärmung, allein an der Farbe ablesbar.",
        "season_title": "Länge der Vegetationsperiode — {name}",
        "season_ylabel": "Länge der Vegetationsperiode (Tage)",
        "season_annual": "Länge der Periode",
        "cap_season": "Länge der thermischen Vegetationsperiode pro Jahr (Folge von "
                      "Tagen mit Tagesmittel ≥ 5 °C) — das frostfreie Fenster, von "
                      "dem die Landwirtschaft abhängt, das sich mit der Erwärmung "
                      "verlängert.",
        "footer": 'Erstellt {date} · Daten von '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(historische Reanalyse ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'Quelle auf GitHub</a>',
    },
    "fr": {
        "html_lang": "fr",
        "per_decade_c": "°C / décennie",
        "per_decade_days": "jours / décennie",
        "ns": "n.s.",
        "smoothed": "lissage (LOESS)",
        "guide_title": "ℹ️ Comment lire ces graphiques",
        "guide_body":
            "<li><b>Points / barres</b> — la valeur de chaque année.</li>"
            "<li><b>Courbe colorée en gras</b> — un lissage LOESS : la tendance "
            "locale, libre de s'infléchir, pour voir l'évolution du rythme dans le "
            "temps (p. ex. un réchauffement qui s'accélère après ~1985).</li>"
            "<li><b>Ligne pointillée</b> — la tendance droite robuste (Theil–Sen) ; "
            "sa pente est la valeur « par décennie » dans la légende.</li>"
            "<li><b>p&lt;0,05 / n.s.</b> — significativité de Mann–Kendall : la "
            "tendance est-elle statistiquement réelle ou simple bruit (n.s. = non "
            "significatif). La température est généralement significative ; les "
            "précipitations souvent non.</li>"
            "<li><b>Bande ombrée</b> — toute l'amplitude historique sur l'ensemble "
            "des années pour ce mois.</li>"
            "<li><b>Couleurs de la carte thermique</b> — température (bleu froid → "
            "rouge chaud) ; lisez une colonne de bas en haut pour suivre l'évolution "
            "du mois au fil des ans.</li>",
        "months": ["janv.", "févr.", "mars", "avr.", "mai", "juin",
                   "juil.", "août", "sept.", "oct.", "nov.", "déc."],
        "threshold_title": "Jours chauds et de gel par an — {name}",
        "threshold_hot": "jours chauds (>{t:.0f} °C)",
        "threshold_freeze": "jours de gel (<{t:.0f} °C)",
        "days_per_year": "Jours par an",
        "year": "Année",
        "month": "Mois",
        "yearly_title": "Température moyenne annuelle au fil des ans — {name}",
        "yearly_ylabel": "Température moyenne annuelle (°C)",
        "annual_mean": "moyenne annuelle",
        "trend": "tendance",
        "anomaly_title": "Anomalie de température annuelle — {name}",
        "anomaly_ylabel": "Anomalie (°C)",
        "vs_baseline": "par rapport à la moyenne {lo}–{hi} ({base:.1f} °C)",
        "vs_full": "par rapport à la moyenne de toute la période ({base:.1f} °C)",
        "heatmap_title": "Température moyenne mensuelle par année — {name}",
        "heatmap_cbar": "Moyenne mensuelle (°C)",
        "anom_heatmap_title": "Anomalie mensuelle par rapport à {base} — {name}",
        "anom_heatmap_cbar": "Anomalie par rapport à {base} (°C)",
        "full_period": "toute la période",
        "dashboard_suptitle": "Températures — {name} {start}–{end} "
                              "(source : réanalyse Open-Meteo)",
        "page_title": "Températures — {name}",
        "subtitle": "{start}–{end} · {days} jours · plus chaude {wy} ({wv:.1f} °C), "
                    "plus froide {cy} ({cv:.1f} °C)",
        "card_trend": "Tendance au réchauffement",
        "card_mean": "Temp. moyenne journalière",
        "card_warmest": "Année la plus chaude",
        "card_coldest": "Année la plus froide",
        "cap_yearly": "Moyenne annuelle avec un lissage LOESS (montre l'accélération) "
                      "et une tendance robuste de Theil–Sen + significativité",
        "cap_anomalies": "Chaque année comparée à la moyenne 1961–1990 — barres rouges "
                         "plus chaudes, bleues plus froides. Le passage du bleu au "
                         "rouge est le réchauffement.",
        "cap_heatmap": "La moyenne de chaque mois pour chaque année en grille de "
                       "couleurs (paliers de 2 °C). Lisez une colonne vers le haut "
                       "pour voir le mois se réchauffer au fil des décennies.",
        "cap_anom_heatmap": "La même grille, mais chaque mois mesuré par rapport à sa "
                            "propre normale 1961–1990, ne montrant que le changement "
                            "(rouge plus chaud, bleu plus froid) — cycle saisonnier "
                            "retiré.",
        "cap_threshold": "Jours par an au-dessus de 18 °C (chauds) et au-dessous de "
                         "0 °C (gel). Le croisement des tendances robustes signifie "
                         "qu'il y a désormais plus de jours chauds que de jours de gel.",
        "hint": "Cliquez n'importe où ou appuyez sur Échap pour fermer",
        "site_title": "Températures des capitales du monde",
        "map_heading": "Températures dans le monde",
        "map_sub": "Choisissez une capitale sur la carte — ou dans la liste",
        "regions": {"Europe": "Europe", "Asia": "Asie",
                    "Middle East": "Moyen-Orient", "Africa": "Afrique",
                    "North America": "Amérique du Nord",
                    "South America": "Amérique du Sud", "Oceania": "Océanie"},
        "choose_city": "Choisir une ville…",
        "back_to_map": "🗺 Carte",
        "range_title": "Amplitude des températures mensuelles au fil des ans — {name}",
        "range_min_max": "min–max {start}–{end}",
        "range_average": "moyenne",
        "range_latest": "récent ({year})",
        "range_ylabel": "Température moyenne mensuelle (°C)",
        "cap_range": "L'amplitude min–max de chaque mois au fil des ans, avec l'année "
                     "la plus récente — frôle-t-elle le bord chaud ?",
        "record_title": "Records journaliers mensuels (max/min) — {name}",
        "record_band": "amplitude des records {start}–{end}",
        "record_latest_high": "maxima {year}",
        "record_latest_low": "minima {year}",
        "record_ylabel": "Température journalière (°C)",
        "cap_records": "Le record journalier absolu, haut et bas, de chaque mois, "
                       "avec les extrêmes de l'année la plus récente",
        "volatility_title": "Sauts de température d'un jour à l'autre par an — {name}",
        "volatility_jump": "saut journalier",
        "volatility_ylabel": "Jours avec un grand saut",
        "cap_volatility": "Fréquence des grands sauts de température d'un jour à "
                          "l'autre chaque année (≥6 °C) — variabilité thermique",
        "per_decade_mm": "mm / décennie",
        "precip_title": "Précipitations annuelles — {name}",
        "precip_ylabel": "Précipitations (mm / an)",
        "precip_annual": "total annuel",
        "cap_precip": "Précipitations annuelles totales (pluie et eau de neige) "
                      "avec une tendance",
        "stripes_title": "Bandes du réchauffement — {name}",
        "stripes_cbar": "Anomalie par rapport à {lo}–{hi} (°C)",
        "cap_stripes": "Chaque bande est une année — bleu plus froid, rouge plus "
                       "chaud que la moyenne 1961–1990. Le glissement du bleu au "
                       "rouge est le réchauffement, lisible à la seule couleur.",
        "season_title": "Durée de la saison de végétation — {name}",
        "season_ylabel": "Durée de la saison de végétation (jours)",
        "season_annual": "durée de la saison",
        "cap_season": "Durée de la saison de végétation thermique chaque année "
                      "(suite de jours dont la moyenne ≥ 5 °C) — la fenêtre sans "
                      "gel dont dépend l'agriculture, qui s'allonge avec le "
                      "réchauffement.",
        "footer": 'Généré le {date} · données de '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(réanalyse historique ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'source sur GitHub</a>',
    },
    "es": {
        "html_lang": "es",
        "per_decade_c": "°C / década",
        "per_decade_days": "días / década",
        "ns": "n.s.",
        "smoothed": "suavizado (LOESS)",
        "guide_title": "ℹ️ Cómo leer estos gráficos",
        "guide_body":
            "<li><b>Puntos / barras</b> — el valor de cada año.</li>"
            "<li><b>Curva de color en negrita</b> — un suavizado LOESS: la tendencia "
            "local, libre de curvarse, para ver el cambio de ritmo en el tiempo "
            "(p. ej. un calentamiento que se acelera después de ~1985).</li>"
            "<li><b>Línea discontinua</b> — la tendencia recta robusta (Theil–Sen); "
            "su pendiente es la cifra « por década » de la leyenda.</li>"
            "<li><b>p&lt;0,05 / n.s.</b> — significancia de Mann–Kendall: si la "
            "tendencia es estadísticamente real o solo ruido (n.s. = no "
            "significativa). La temperatura suele ser significativa; la "
            "precipitación a menudo no.</li>"
            "<li><b>Banda sombreada</b> — todo el rango histórico de todos los años "
            "para ese mes.</li>"
            "<li><b>Colores del mapa de calor</b> — temperatura (azul frío → rojo "
            "cálido); lea una columna de abajo arriba para ver cómo cambia ese mes "
            "a lo largo de los años.</li>",
        "months": ["ene", "feb", "mar", "abr", "may", "jun",
                   "jul", "ago", "sep", "oct", "nov", "dic"],
        "threshold_title": "Días cálidos y de helada al año — {name}",
        "threshold_hot": "días cálidos (>{t:.0f} °C)",
        "threshold_freeze": "días de helada (<{t:.0f} °C)",
        "days_per_year": "Días al año",
        "year": "Año",
        "month": "Mes",
        "yearly_title": "Temperatura media anual a lo largo de los años — {name}",
        "yearly_ylabel": "Temperatura media anual (°C)",
        "annual_mean": "media anual",
        "trend": "tendencia",
        "anomaly_title": "Anomalía de temperatura anual — {name}",
        "anomaly_ylabel": "Anomalía (°C)",
        "vs_baseline": "respecto a la media {lo}–{hi} ({base:.1f} °C)",
        "vs_full": "respecto a la media de todo el período ({base:.1f} °C)",
        "heatmap_title": "Temperatura media mensual por año — {name}",
        "heatmap_cbar": "Media mensual (°C)",
        "anom_heatmap_title": "Anomalía mensual respecto a {base} — {name}",
        "anom_heatmap_cbar": "Anomalía respecto a {base} (°C)",
        "full_period": "todo el período",
        "dashboard_suptitle": "Temperaturas — {name} {start}–{end} "
                              "(fuente: reanálisis Open-Meteo)",
        "page_title": "Temperaturas — {name}",
        "subtitle": "{start}–{end} · {days} días · más cálido {wy} ({wv:.1f} °C), "
                    "más frío {cy} ({cv:.1f} °C)",
        "card_trend": "Tendencia de calentamiento",
        "card_mean": "Temp. media diaria",
        "card_warmest": "Año más cálido",
        "card_coldest": "Año más frío",
        "cap_yearly": "Media anual con un suavizado LOESS (muestra la aceleración) "
                      "y una tendencia robusta de Theil–Sen + significancia",
        "cap_anomalies": "Cada año comparado con la media de 1961–1990 — barras rojas "
                         "más cálidas, azules más frías. El cambio de azul a rojo es "
                         "el calentamiento.",
        "cap_heatmap": "La media de cada mes en cada año como cuadrícula de colores "
                       "(bandas de 2 °C). Lea una columna hacia arriba para ver cómo "
                       "se calienta ese mes a lo largo de las décadas.",
        "cap_anom_heatmap": "La misma cuadrícula, pero cada mes medido frente a su "
                            "propia normal de 1961–1990, mostrando solo el cambio "
                            "(rojo más cálido, azul más frío) — ciclo estacional "
                            "eliminado.",
        "cap_threshold": "Días al año por encima de 18 °C (cálidos) y por debajo de "
                         "0 °C (helada). El cruce de las tendencias robustas significa "
                         "que ya hay más días cálidos que de helada.",
        "hint": "Haga clic en cualquier lugar o pulse Esc para cerrar",
        "site_title": "Temperaturas de las capitales del mundo",
        "map_heading": "Temperaturas en el mundo",
        "map_sub": "Elija una capital en el mapa — o de la lista",
        "regions": {"Europe": "Europa", "Asia": "Asia",
                    "Middle East": "Oriente Medio", "Africa": "África",
                    "North America": "América del Norte",
                    "South America": "América del Sur", "Oceania": "Oceanía"},
        "choose_city": "Elegir una ciudad…",
        "back_to_map": "🗺 Mapa",
        "range_title": "Rango de temperaturas mensuales a lo largo de los años — {name}",
        "range_min_max": "mín–máx {start}–{end}",
        "range_average": "promedio",
        "range_latest": "reciente ({year})",
        "range_ylabel": "Temperatura media mensual (°C)",
        "cap_range": "El rango mín–máx de cada mes a lo largo de los años, con el año "
                     "más reciente — ¿se acerca al extremo cálido?",
        "record_title": "Récords diarios mensuales (máx/mín) — {name}",
        "record_band": "rango de récords {start}–{end}",
        "record_latest_high": "máximos {year}",
        "record_latest_low": "mínimos {year}",
        "record_ylabel": "Temperatura diaria (°C)",
        "cap_records": "El récord diario absoluto, alto y bajo, de cada mes, con los "
                       "extremos del año más reciente",
        "volatility_title": "Saltos de temperatura de un día a otro al año — {name}",
        "volatility_jump": "salto diario",
        "volatility_ylabel": "Días con un gran salto",
        "cap_volatility": "Con qué frecuencia ocurren grandes saltos de temperatura "
                          "de un día a otro cada año (≥6 °C) — variabilidad térmica",
        "per_decade_mm": "mm / década",
        "precip_title": "Precipitación anual — {name}",
        "precip_ylabel": "Precipitación (mm / año)",
        "precip_annual": "total anual",
        "cap_precip": "Precipitación anual total (lluvia y agua de nieve) "
                      "con una tendencia",
        "stripes_title": "Franjas del calentamiento — {name}",
        "stripes_cbar": "Anomalía respecto a {lo}–{hi} (°C)",
        "cap_stripes": "Cada franja es un año — azul más frío, rojo más cálido que "
                       "la media 1961–1990. El paso del azul al rojo es el "
                       "calentamiento, legible solo por el color.",
        "season_title": "Duración de la estación de crecimiento — {name}",
        "season_ylabel": "Duración de la estación de crecimiento (días)",
        "season_annual": "duración de la estación",
        "cap_season": "Duración de la estación de crecimiento térmica cada año "
                      "(racha de días con media diaria ≥ 5 °C) — la ventana sin "
                      "heladas de la que depende la agricultura, que se alarga con "
                      "el calentamiento.",
        "footer": 'Generado el {date} · datos de '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(reanálisis histórico ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'código en GitHub</a>',
    },
    "uk": {
        "html_lang": "uk",
        "per_decade_c": "°C / десятиліття",
        "per_decade_days": "днів / десятиліття",
        "ns": "нез.",
        "smoothed": "згладжування (LOESS)",
        "guide_title": "ℹ️ Як читати ці графіки",
        "guide_body":
            "<li><b>Точки / стовпчики</b> — значення для кожного року.</li>"
            "<li><b>Жирна кольорова крива</b> — згладжування LOESS: локальний тренд, "
            "який може вигинатися, тож видно зміну темпу з часом (напр., потепління, "
            "що прискорюється після ~1985).</li>"
            "<li><b>Пунктирна лінія</b> — прямий стійкий тренд (Тейла–Сена); його "
            "нахил — це значення « за десятиліття » в легенді.</li>"
            "<li><b>p&lt;0,05 / нез.</b> — значущість Манна–Кендалла: чи тренд "
            "статистично реальний, чи це лише шум (нез. = незначущий). Температура "
            "зазвичай значуща; опади часто ні.</li>"
            "<li><b>Затінена смуга</b> — увесь історичний діапазон за всі роки для "
            "цього місяця.</li>"
            "<li><b>Кольори теплової карти</b> — температура (синій холодно → "
            "червоний тепло); читайте стовпець знизу вгору, щоб побачити зміну "
            "місяця впродовж років.</li>",
        "months": ["січ", "лют", "бер", "кві", "тра", "чер",
                   "лип", "сер", "вер", "жов", "лис", "гру"],
        "threshold_title": "Спекотні та морозні дні на рік — {name}",
        "threshold_hot": "спекотні дні (>{t:.0f} °C)",
        "threshold_freeze": "морозні дні (<{t:.0f} °C)",
        "days_per_year": "Днів на рік",
        "year": "Рік",
        "month": "Місяць",
        "yearly_title": "Середня річна температура впродовж років — {name}",
        "yearly_ylabel": "Середня річна температура (°C)",
        "annual_mean": "середня річна",
        "trend": "тренд",
        "anomaly_title": "Річна аномалія температури — {name}",
        "anomaly_ylabel": "Аномалія (°C)",
        "vs_baseline": "відносно середньої {lo}–{hi} ({base:.1f} °C)",
        "vs_full": "відносно середньої за весь період ({base:.1f} °C)",
        "heatmap_title": "Середня місячна температура за роками — {name}",
        "heatmap_cbar": "Середня місячна (°C)",
        "anom_heatmap_title": "Місячна аномалія відносно {base} — {name}",
        "anom_heatmap_cbar": "Аномалія відносно {base} (°C)",
        "full_period": "усього періоду",
        "dashboard_suptitle": "Температури — {name} {start}–{end} "
                              "(джерело: реаналіз Open-Meteo)",
        "page_title": "Температури — {name}",
        "subtitle": "{start}–{end} · {days} днів · найтепліший {wy} ({wv:.1f} °C), "
                    "найхолодніший {cy} ({cv:.1f} °C)",
        "card_trend": "Тренд потепління",
        "card_mean": "Середня добова темп.",
        "card_warmest": "Найтепліший рік",
        "card_coldest": "Найхолодніший рік",
        "cap_yearly": "Середня річна зі згладжуванням LOESS (показує прискорення) "
                      "та стійким трендом Тейла–Сена + значущість",
        "cap_anomalies": "Кожен рік порівняно із середньою 1961–1990 — червоні "
                         "стовпчики тепліші, сині холодніші. Перехід від синього до "
                         "червоного — це потепління.",
        "cap_heatmap": "Середнє кожного місяця за кожен рік як кольорова сітка "
                       "(смуги по 2 °C). Читайте стовпець угору, щоб побачити "
                       "потепління місяця впродовж десятиліть.",
        "cap_anom_heatmap": "Та сама сітка, але кожен місяць виміряно відносно власної "
                            "норми 1961–1990, тож видно лише зміну (червоний тепліше, "
                            "синій холодніше) — сезонний цикл прибрано.",
        "cap_threshold": "Днів на рік вище 18 °C (спекотні) та нижче 0 °C (морозні). "
                         "Перетин стійких трендів означає, що спекотних днів тепер "
                         "більше, ніж морозних.",
        "hint": "Клацніть будь-де або натисніть Esc, щоб закрити",
        "site_title": "Температури столиць світу",
        "map_heading": "Температури у світі",
        "map_sub": "Оберіть столицю на карті — або зі списку",
        "regions": {"Europe": "Європа", "Asia": "Азія",
                    "Middle East": "Близький Схід", "Africa": "Африка",
                    "North America": "Північна Америка",
                    "South America": "Південна Америка", "Oceania": "Океанія"},
        "choose_city": "Оберіть місто…",
        "back_to_map": "🗺 Карта",
        "range_title": "Діапазон місячних температур впродовж років — {name}",
        "range_min_max": "мін–макс {start}–{end}",
        "range_average": "середня",
        "range_latest": "останній ({year})",
        "range_ylabel": "Середня місячна температура (°C)",
        "cap_range": "Діапазон мін–макс кожного місяця впродовж років, з останнім "
                     "роком — чи тулиться він до теплого краю?",
        "record_title": "Місячні добові рекорди (макс/мін) — {name}",
        "record_band": "діапазон рекордів {start}–{end}",
        "record_latest_high": "максимуми {year}",
        "record_latest_low": "мінімуми {year}",
        "record_ylabel": "Добова температура (°C)",
        "cap_records": "Абсолютний добовий рекорд, високий і низький, кожного місяця, "
                       "з екстремумами останнього року",
        "volatility_title": "Добові стрибки температури на рік — {name}",
        "volatility_jump": "добовий стрибок",
        "volatility_ylabel": "Днів із великим стрибком",
        "cap_volatility": "Як часто трапляються великі добові стрибки температури "
                          "щороку (≥6 °C) — мінливість температури",
        "per_decade_mm": "мм / десятиліття",
        "precip_title": "Річні опади — {name}",
        "precip_ylabel": "Опади (мм / рік)",
        "precip_annual": "річна сума",
        "cap_precip": "Річна сума опадів (дощ і вода зі снігу) з лінією тренду",
        "stripes_title": "Смуги потепління — {name}",
        "stripes_cbar": "Аномалія відносно {lo}–{hi} (°C)",
        "cap_stripes": "Кожна смуга — це один рік: синій холодніший, червоний "
                       "тепліший за середню 1961–1990. Перехід від синього до "
                       "червоного — це потепління, читається самим лише кольором.",
        "season_title": "Тривалість вегетаційного періоду — {name}",
        "season_ylabel": "Тривалість вегетаційного періоду (днів)",
        "season_annual": "тривалість періоду",
        "cap_season": "Тривалість термічного вегетаційного періоду щороку (низка "
                      "днів із середньою добовою ≥ 5 °C) — безморозне вікно, від "
                      "якого залежить сільське господарство, що подовжується з "
                      "потеплінням.",
        "footer": 'Згенеровано {date} · дані з '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(історичний реаналіз ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'код на GitHub</a>',
    },
}


def get(lang: str) -> dict:
    """Return the translation table for ``lang`` (falls back to default)."""
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
