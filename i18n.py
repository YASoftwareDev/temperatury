"""Translations for the website and the chart labels.

Each language is a flat dict of strings; ``{...}`` fields are filled with
``str.format``. Add a language by adding one entry to ``TRANSLATIONS`` and
listing its code in ``LANGUAGES``, everything else (pages, charts, switcher)
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
        "map_coverage": "{done} of {total} cities analysed so far - the rest are added day by day.",
        "cur_so_far": "{year} so far (to {day} {month}): {v} °C on average, {d} °C vs the 1961-1990 mean for the same days of the year.",
        "cmp_title": "Compare two cities",
        "cmp_hint": "Each curve is that city's yearly anomaly vs its own 1961-1990 baseline, so places with different climates compare fairly.",
        "cmp_city_a": "First city",
        "cmp_city_b": "Second city",
        "kpi_rate": "World warming rate",
        "kpi_since": "World warming since 1940",
        "kpi_cities": "Cities analysed",
        "kpi_warmest": "Warmest year (world average)",
        "sum_season": "Fastest-warming season here: {season} ({v} °C per decade).",
        "sum_month": "Fastest-warming month here: {month} ({v} °C per decade).",
        "season_winter": "winter",
        "season_spring": "spring",
        "season_summer": "summer",
        "season_autumn": "autumn",
        "grid_alias_note": "The temperature record is computed per ~11 km climate-data grid cell. {alias} shares its cell with {city}, so both show the same 1940-present history.",
        "map_coverage_help": "Help gather the data",
        "qv_nodata": "No data for this city yet.",
        "qv_nearest": "Nearest analysed city",
        "per_decade_days": "days / decade",
        "ns": "n.s.",
        "smoothed": "smoothed (LOESS)",
        "guide_title": "ℹ️ How to read these charts",
        "guide_body":
            "<li><b>Dots / bars</b>: the value for each individual year.</li>"
            "<li><b>Bold coloured curve</b>: a LOESS smoother: the local trend, "
            "free to bend, so you can see the rate change over time (e.g. warming "
            "accelerating after ~1985).</li>"
            "<li><b>Dashed line</b>: the straight robust (Theil-Sen) trend; its "
            "slope is the “per decade” figure in the legend.</li>"
            "<li><b>p&lt;0.05 / n.s.</b>: Mann-Kendall significance: whether the "
            "trend is statistically real or could just be noise (n.s. = not "
            "significant). Temperature is usually highly significant; rainfall "
            "often isn't.</li>"
            "<li><b>Shaded band</b>: the full historical range across all years "
            "for that month.</li>"
            "<li><b>Heatmap colours</b>: temperature (blue cold → red warm); read "
            "a column from bottom to top to watch that month change over the "
            "years.</li>",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        # charts
        "threshold_title": "Hot & freezing days per year, {name}",
        "threshold_hot": "hot days (>{t:.0f} °C)",
        "threshold_freeze": "freezing days (<{t:.0f} °C)",
        "days_per_year": "Days per year",
        "year": "Year",
        "month": "Month",
        "yearly_title": "Annual mean temperature through the years, {name}",
        "yearly_ylabel": "Annual mean temperature (°C)",
        "annual_mean": "annual mean",
        "trend": "trend",
        "anomaly_title": "Annual temperature anomaly, {name}",
        "anomaly_ylabel": "Anomaly (°C)",
        "vs_baseline": "vs. {lo}-{hi} mean ({base:.1f} °C)",
        "vs_full": "vs. full-period mean ({base:.1f} °C)",
        "heatmap_title": "Monthly mean temperature by year, {name}",
        "heatmap_cbar": "Monthly mean (°C)",
        "anom_heatmap_title": "Monthly anomaly vs. {base}, {name}",
        "anom_heatmap_cbar": "Anomaly vs. {base} (°C)",
        "full_period": "full-period",
        "dashboard_suptitle": "{name} temperatures {start}-{end} "
                              "(source: Open-Meteo reanalysis)",
        # page
        "page_title": "{name} temperatures",
        "subtitle": "{start}-{end} · {days} days · warmest {wy} ({wv:.1f} °C), "
                    "coldest {cy} ({cv:.1f} °C)",
        "card_trend": "Warming trend",
        "card_mean": "Mean daily temp",
        "card_warmest": "Warmest year",
        "card_coldest": "Coldest year",
        "share": "Share",
        "share_copied": "Link copied",
        "climate_news": "Climate news",
        "extreme_weather": "Extreme weather",
        "analog_line": "By 2050, the local climate could feel more like {analog} does "
                       "today, about +{d} °C warmer.",
        "analog_past": "In 1940, the local climate felt more like {analog} does today, "
                       "about {d} °C cooler.",
        "cap_yearly": "Annual mean with a LOESS smoother (shows acceleration) and "
                      "a robust Theil-Sen trend + significance",
        "cap_anomalies": "Each year compared to the 1961-1990 average: red bars "
                         "warmer, blue cooler. The shift from mostly blue to mostly "
                         "red is the warming.",
        "cap_heatmap": "Every month's average for every year as a colour grid "
                       "(2 °C bands). Read a column upward to watch that month warm "
                       "over the decades.",
        "cap_anom_heatmap": "Same grid, but each month is measured against its own "
                            "1961-1990 normal, so only the change shows (red warmer "
                            "than usual, blue cooler), the seasonal cycle removed.",
        "cap_threshold": "Days each year above 18 °C (hot) and below 0 °C (freezing). "
                         "The two robust trends crossing means hot days now outnumber "
                         "freezing days.",
        "hint": "Click anywhere or press Esc to close",
        "site_title": "World city temperatures",
        "intro": "How the world's major cities have warmed since 1940: daily temperature records from the ERA5 climate reanalysis.",
        "map_heading": "Temperatures around the world",
        "map_sub": "Pick a city on the map or from the list",
        "map_filter": "Show a continent or country",
        "omni_ph": "Search a city, country, region or any place",
        "omni_cities": "Cities",
        "omni_countries": "Countries",
        "omni_regions": "Continents",
        "omni_places": "Places worldwide",
        "omni_anywhere": 'Check any place: "{q}"',
        "nav_ranking": "Ranking",
        "nav_dashboard": "Climate dashboard",
        "regions": {"Europe": "Europe", "Asia": "Asia",
                    "Middle East": "Middle East", "Africa": "Africa",
                    "North America": "North America",
                    "South America": "South America", "Oceania": "Oceania"},
        "choose_city": "Choose a city...",
        "back_to_map": "🗺 Map",
        "range_title": "Monthly temperature range across the years, {name}",
        "range_min_max": "min-max {start}-{end}",
        "range_average": "average",
        "range_latest": "latest ({year})",
        "range_ylabel": "Monthly mean temperature (°C)",
        "cap_range": "Each month's min-max range over the years, with the latest year. Is it hugging the warm edge?",
        "record_title": "Monthly record high/low daily temperature, {name}",
        "record_band": "record range {start}-{end}",
        "record_latest_high": "{year} highs",
        "record_latest_low": "{year} lows",
        "record_ylabel": "Daily temperature (°C)",
        "cap_records": "Each month's all-time record daily high and low, with the "
                       "latest year's extremes",
        "volatility_title": "Day-to-day temperature swings per year, {name}",
        "volatility_jump": "day-to-day jump",
        "volatility_ylabel": "Days with a big jump",
        "cap_volatility": "How often big day-to-day temperature jumps happen "
                          "each year (≥6 °C), temperature variability",
        "per_decade_mm": "mm / decade",
        "precip_title": "Annual precipitation, {name}",
        "precip_ylabel": "Precipitation (mm / year)",
        "precip_annual": "annual total",
        "cap_precip": "Total yearly precipitation (rain and snow water) with a trend",
        "stripes_title": "Warming stripes, {name}",
        "stripes_cbar": "Anomaly vs. {lo}-{hi} (°C)",
        "cap_stripes": "Each stripe is one year's temperature: blue cooler, red "
                       "warmer than the 1961-1990 average. The drift from blue to "
                       "red is the warming, with nothing to read but colour.",
        "season_title": "Growing-season length, {name}",
        "season_ylabel": "Growing-season length (days)",
        "season_annual": "season length",
        "cap_season": "Length of the thermal growing season each year (run of days "
                      "with a daily mean ≥ 5 °C): the frost-free window farming "
                      "depends on, lengthening as the climate warms.",
        "dtr_title": "Diurnal temperature range (day − night), {name}",
        "dtr_ylabel": "Mean daily max − min (°C)",
        "dtr_annual": "annual mean range",
        "cap_dtr": "The average gap between each day's high and low. A shrinking "
                   "range is a greenhouse fingerprint: nights warming faster than "
                   "days; a widening one can signal drying.",
        "seasonshift_title": "How the seasonal cycle shifted, {name}",
        "seasonshift_ylabel": "Monthly mean temperature (°C)",
        "cap_seasonshift": "The average year for the first vs. the last decade of "
                           "record. The gap between the curves at each month shows "
                           "which parts of the year warmed most (often winters more "
                           "than summers).",
        "health_heading": "Health-impact indicators",
        "health_sub": "How the warming trends above translate into recognised heat-, "
                      "cold- and extreme-event exposure metrics. Each chart appears "
                      "where the data it needs is available.",
        "degreedays_title": "Heating & cooling degree-days, {name}",
        "dd_ylabel": "Degree-days per year (°C·days)",
        "hdd_label": "heating (< {t:.0f} °C)",
        "cdd_label": "cooling (> {t:.0f} °C)",
        "per_decade_dd": "°C·days / decade",
        "cap_degreedays": "The annual thermal-comfort burden: heating need (below "
                          "18 °C) falls while cooling need (above 22 °C) rises, a proxy for cold exposure and air-conditioning demand.",
        "heatwave_title": "Heat-wave days per year, {name}",
        "heatwave_ylabel": "Heat-wave days per year",
        "heatwave_series": "heat-wave days",
        "cap_heatwave": "Days in a heat wave: a run of ≥3 days with the daily high "
                        "above the local 1961-1990 90th percentile. Sustained daytime "
                        "heat is the main driver of heat-wave excess mortality.",
        "tropic_title": "Tropical nights per year, {name}",
        "tropic_ylabel": "Nights per year",
        "tropic_series": "nights ≥ {t:.0f} °C",
        "cap_tropic": "Nights when the low stays at or above 20 °C, so the body gets "
                      "no overnight relief, a leading, often-overlooked driver of "
                      "heat-related death.",
        "coldspell_title": "Cold-spell days per year, {name}",
        "coldspell_ylabel": "Cold-spell days per year",
        "coldspell_series": "cold-spell days",
        "cap_coldspell": "Days in a cold spell: a run of ≥3 days with the daily low "
                         "below the local 1961-1990 10th percentile. Prolonged cold "
                         "drives winter cardiovascular and respiratory excess deaths.",
        "heavyrain_title": "Heavy-rain days per year, {name}",
        "heavyrain_ylabel": "Days per year",
        "heavyrain_series": "days ≥ {mm:.0f} mm",
        "cap_heavyrain": "Days with at least 20 mm of rain (ETCCDI R20mm), flood-triggering downpours that bring injury, displacement "
                         "and waterborne disease.",
        "heatindex_title": "Dangerous heat-index days per year, {name}",
        "heatindex_ylabel": "Days per year",
        "heat_strong": "≥ {t:.0f} °C (extreme caution)",
        "heat_danger": "≥ {t:.0f} °C (danger)",
        "cap_heatindex": "Days the apparent temperature (heat index, which folds in "
                         "humidity) reaches heat-stress levels, the metric public "
                         "heat advisories use. Needs the apparent-temperature dataset.",
        "footer": 'Generated {date} · data from '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  'historical reanalysis (ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'source on GitHub</a>',
    },
    "pl": {
        "html_lang": "pl",
        "per_decade_c": "°C / dekadę",
        "map_coverage": "Przeanalizowano dotąd {done} z {total} miast - reszta dochodzi z dnia na dzień.",
        "cur_so_far": "Rok {year} dotychczas (do {day} {month}): średnio {v} °C, {d} °C względem średniej 1961-1990 dla tych samych dni roku.",
        "cmp_title": "Porównaj dwa miasta",
        "cmp_hint": "Każda krzywa to roczna anomalia danego miasta względem jego własnej średniej 1961-1990, więc miejsca o różnym klimacie porównują się uczciwie.",
        "cmp_city_a": "Pierwsze miasto",
        "cmp_city_b": "Drugie miasto",
        "kpi_rate": "Tempo ocieplania świata",
        "kpi_since": "Ocieplenie świata od 1940",
        "kpi_cities": "Przeanalizowane miasta",
        "kpi_warmest": "Najcieplejszy rok (średnia światowa)",
        "sum_season": "Najszybciej ocieplająca się pora roku: {season} ({v} °C na dekadę).",
        "sum_month": "Najszybciej ocieplający się miesiąc: {month} ({v} °C na dekadę).",
        "season_winter": "zima",
        "season_spring": "wiosna",
        "season_summer": "lato",
        "season_autumn": "jesień",
        "grid_alias_note": "Dane o temperaturze liczone są dla komórek siatki klimatycznej ~11 km. {alias} leży w tej samej komórce co {city}, więc mają identyczny zapis od 1940 roku.",
        "map_coverage_help": "Pomóż zbierać dane",
        "qv_nodata": "Dla tego miasta nie ma jeszcze danych.",
        "qv_nearest": "Najbliższe przeanalizowane miasto",
        "per_decade_days": "dni / dekadę",
        "ns": "nieist.",
        "smoothed": "wygładzenie (LOESS)",
        "guide_title": "ℹ️ Jak czytać te wykresy",
        "guide_body":
            "<li><b>Punkty / słupki</b>: wartość dla każdego roku.</li>"
            "<li><b>Pogrubiona krzywa</b>: wygładzenie LOESS: lokalny trend, który "
            "może się wyginać, więc widać zmianę tempa w czasie (np. przyspieszające "
            "ocieplenie po ~1985).</li>"
            "<li><b>Linia przerywana</b>: prosty, odporny trend (Theil-Sen); jego "
            "nachylenie to wartość „na dekadę” w legendzie.</li>"
            "<li><b>p&lt;0,05 / nieist.</b>: istotność Manna-Kendalla: czy trend "
            "jest statystycznie realny, czy może być tylko szumem (nieist. = "
            "nieistotny). Temperatura jest zwykle istotna; opady często nie.</li>"
            "<li><b>Zacieniony obszar</b>: pełny historyczny zakres ze wszystkich "
            "lat dla danego miesiąca.</li>"
            "<li><b>Kolory mapy ciepła</b>: temperatura (niebieski zimno → czerwony "
            "ciepło); czytaj kolumnę z dołu do góry, by zobaczyć zmianę miesiąca "
            "przez lata.</li>",
        "months": ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                   "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"],
        "threshold_title": "Dni gorące i mroźne w roku, {name}",
        "threshold_hot": "dni gorące (>{t:.0f} °C)",
        "threshold_freeze": "dni mroźne (<{t:.0f} °C)",
        "days_per_year": "Liczba dni w roku",
        "year": "Rok",
        "month": "Miesiąc",
        "yearly_title": "Średnia roczna temperatura na przestrzeni lat, {name}",
        "yearly_ylabel": "Średnia roczna temperatura (°C)",
        "annual_mean": "średnia roczna",
        "trend": "trend",
        "anomaly_title": "Roczna anomalia temperatury, {name}",
        "anomaly_ylabel": "Anomalia (°C)",
        "vs_baseline": "względem średniej {lo}-{hi} ({base:.1f} °C)",
        "vs_full": "względem średniej z całego okresu ({base:.1f} °C)",
        "heatmap_title": "Średnia miesięczna temperatura wg lat, {name}",
        "heatmap_cbar": "Średnia miesięczna (°C)",
        "anom_heatmap_title": "Anomalia miesięczna względem {base}, {name}",
        "anom_heatmap_cbar": "Anomalia względem {base} (°C)",
        "full_period": "całego okresu",
        "dashboard_suptitle": "Temperatury, {name} {start}-{end} "
                              "(źródło: reanaliza Open-Meteo)",
        "page_title": "Temperatury, {name}",
        "subtitle": "{start}-{end} · {days} dni · najcieplejszy {wy} "
                    "({wv:.1f} °C), najzimniejszy {cy} ({cv:.1f} °C)",
        "card_trend": "Trend ocieplenia",
        "card_mean": "Średnia dobowa",
        "card_warmest": "Najcieplejszy rok",
        "card_coldest": "Najzimniejszy rok",
        "share": "Udostępnij",
        "share_copied": "Skopiowano link",
        "climate_news": "Wiadomości o klimacie",
        "extreme_weather": "Ekstremalna pogoda",
        "lookup_title": "Sprawdź dowolne miejsce na Ziemi",
        "lookup_sub": "Mapa pokazuje duże miasta - ale ociepla się wszędzie. "
                      "Wyszukaj dowolne miasteczko lub wieś.",
        "lookup_ph": "Wpisz miasto, wieś lub adres...",
        "lookup_go": "Sprawdź",
        "lookup_searching": "Szukanie miejsca...",
        "lookup_loading": "Wczytywanie 85 lat danych...",
        "lookup_notfound": "Nie znaleziono miejsca. Spróbuj innej pisowni.",
        "lookup_error": "Nie udało się wczytać danych. Spróbuj ponownie.",
        "lookup_busy": "Bezpłatny serwis danych klimatycznych przekroczył dzienny limit zapytań. Spróbuj ponownie później.",
        "lookup_short": "Za mało danych dla tego miejsca.",
        "lookup_since": "od 1940",
        "lookup_perdec": "na dekadę",
        "lookup_warmtrend": "trend ocieplenia",
        "lookup_cooltrend": "trend ochładzania",
        "lookup_faster": "ociepla się szybciej niż {pct}% miast świata",
        "lookup_cooling": "Ochładza się, wbrew globalnemu trendowi",
        "analog_line": "Do 2050 roku tutejszy klimat może przypominać miasto {analog}, "
                       "o około {d} °C cieplej niż dziś.",
        "analog_past": "W 1940 roku tutejszy klimat przypominał miasto {analog}, "
                       "o około {d} °C chłodniej niż dziś.",
        "cap_yearly": "Średnia roczna z wygładzeniem LOESS (pokazuje przyspieszenie) "
                      "i odpornym trendem Theila-Sena + istotność",
        "cap_anomalies": "Każdy rok względem średniej 1961-1990: czerwone słupki "
                         "cieplej, niebieskie chłodniej. Przejście od niebieskich do "
                         "czerwonych to ocieplenie.",
        "cap_heatmap": "Średnia każdego miesiąca w każdym roku jako siatka kolorów "
                       "(pasma 2 °C). Czytaj kolumnę w górę, by zobaczyć ocieplanie "
                       "się miesiąca przez dekady.",
        "cap_anom_heatmap": "Ta sama siatka, ale każdy miesiąc względem własnej normy "
                            "1961-1990, więc widać tylko zmianę (czerwony cieplej, "
                            "niebieski chłodniej), cykl sezonowy usunięty.",
        "cap_threshold": "Dni w roku powyżej 18 °C (gorące) i poniżej 0 °C (mroźne). "
                         "Przecięcie odpornych trendów oznacza, że dni gorących jest "
                         "już więcej niż mroźnych.",
        "hint": "Kliknij gdziekolwiek lub naciśnij Esc, aby zamknąć",
        "site_title": "Temperatury miast świata",
        "intro": "Jak ocieplały się największe miasta świata od 1940 roku: dobowe zapisy temperatury z reanalizy klimatycznej ERA5.",
        "map_heading": "Temperatury na świecie",
        "map_sub": "Wybierz miasto na mapie lub z listy",
        "map_filter": "Pokaż kontynent lub kraj",
        "omni_ph": "Szukaj miasta, kraju, regionu lub dowolnego miejsca",
        "omni_cities": "Miasta",
        "omni_countries": "Kraje",
        "omni_regions": "Kontynenty",
        "omni_places": "Miejsca na świecie",
        "omni_anywhere": 'Sprawdź dowolne miejsce: "{q}"',
        "nav_ranking": "Ranking",
        "nav_dashboard": "Panel klimatyczny",
        "regions": {"Europe": "Europa", "Asia": "Azja",
                    "Middle East": "Bliski Wschód", "Africa": "Afryka",
                    "North America": "Ameryka Północna",
                    "South America": "Ameryka Południowa", "Oceania": "Oceania"},
        "choose_city": "Wybierz miasto...",
        "back_to_map": "🗺 Mapa",
        "range_title": "Zakres miesięcznych temperatur na przestrzeni lat, {name}",
        "range_min_max": "min-maks {start}-{end}",
        "range_average": "średnia",
        "range_latest": "ostatni ({year})",
        "range_ylabel": "Średnia miesięczna temperatura (°C)",
        "cap_range": "Zakres min-maks każdego miesiąca w kolejnych latach, "
                     "z ostatnim rokiem. Czy zbliża się do maksimum?",
        "record_title": "Miesięczne rekordy dobowe (maksimum i minimum), {name}",
        "record_band": "zakres rekordów {start}-{end}",
        "record_latest_high": "maksima {year}",
        "record_latest_low": "minima {year}",
        "record_ylabel": "Temperatura dobowa (°C)",
        "cap_records": "Rekordowe dobowe maksimum i minimum każdego miesiąca, "
                       "z ekstremami ostatniego roku",
        "volatility_title": "Skoki temperatury z dnia na dzień w roku, {name}",
        "volatility_jump": "skok z dnia na dzień",
        "volatility_ylabel": "Dni z dużym skokiem",
        "cap_volatility": "Jak często zdarzają się duże skoki temperatury z dnia "
                          "na dzień (≥6 °C), zmienność temperatury",
        "per_decade_mm": "mm / dekadę",
        "precip_title": "Roczne opady, {name}",
        "precip_ylabel": "Opady (mm / rok)",
        "precip_annual": "suma roczna",
        "cap_precip": "Roczna suma opadów (deszcz i woda ze śniegu) z linią trendu",
        "stripes_title": "Pasy ocieplenia, {name}",
        "stripes_cbar": "Anomalia względem {lo}-{hi} (°C)",
        "cap_stripes": "Każdy pas to jeden rok: niebieski chłodniejszy, czerwony "
                       "cieplejszy od średniej 1961-1990. Przejście od niebieskiego "
                       "do czerwonego to ocieplenie, czytelne samym kolorem.",
        "season_title": "Długość sezonu wegetacyjnego, {name}",
        "season_ylabel": "Długość sezonu wegetacyjnego (dni)",
        "season_annual": "długość sezonu",
        "cap_season": "Długość termicznego sezonu wegetacyjnego w każdym roku (ciąg "
                      "dni ze średnią dobową ≥ 5 °C): bezmroźne okno, od którego "
                      "zależy rolnictwo, wydłużające się wraz z ociepleniem.",
        "dtr_title": "Dobowa amplituda temperatury (dzień − noc), {name}",
        "dtr_ylabel": "Średnie dobowe maks − min (°C)",
        "dtr_annual": "średnia roczna amplituda",
        "cap_dtr": "Średnia różnica między dziennym maksimum a minimum. Malejąca "
                   "amplituda to ślad efektu cieplarnianego: noce ocieplają się "
                   "szybciej niż dni; rosnąca może oznaczać osuszanie.",
        "seasonshift_title": "Jak zmienił się cykl sezonowy, {name}",
        "seasonshift_ylabel": "Średnia miesięczna temperatura (°C)",
        "cap_seasonshift": "Przeciętny rok dla pierwszej i ostatniej dekady danych. "
                           "Odstęp między krzywymi w każdym miesiącu pokazuje, które "
                           "części roku ociepliły się najbardziej (często zimy "
                           "bardziej niż lata).",
        "health_heading": "Wskaźniki wpływu na zdrowie",
        "health_sub": "Jak powyższe trendy ocieplenia przekładają się na uznane miary "
                      "narażenia na upał, mróz i zjawiska ekstremalne. Każdy wykres "
                      "pojawia się tam, gdzie dostępne są potrzebne dane.",
        "degreedays_title": "Stopniodni grzania i chłodzenia, {name}",
        "dd_ylabel": "Stopniodni w roku (°C·dni)",
        "hdd_label": "grzanie (< {t:.0f} °C)",
        "cdd_label": "chłodzenie (> {t:.0f} °C)",
        "per_decade_dd": "°C·dni / dekadę",
        "cap_degreedays": "Roczne obciążenie komfortem cieplnym: zapotrzebowanie na "
                          "grzanie (poniżej 18 °C) spada, a na chłodzenie (powyżej "
                          "22 °C) rośnie, przybliżenie narażenia na zimno i potrzeby "
                          "klimatyzacji.",
        "heatwave_title": "Dni fali upałów w roku, {name}",
        "heatwave_ylabel": "Dni fali upałów w roku",
        "heatwave_series": "dni fali upałów",
        "cap_heatwave": "Dni w fali upałów: ciąg ≥3 dni z dobowym maksimum powyżej "
                        "lokalnego 90. percentyla z lat 1961-1990. Długotrwały upał "
                        "w dzień to główny czynnik nadmiarowej śmiertelności w falach "
                        "upałów.",
        "tropic_title": "Noce tropikalne w roku, {name}",
        "tropic_ylabel": "Nocy w roku",
        "tropic_series": "noce ≥ {t:.0f} °C",
        "cap_tropic": "Noce, gdy minimum nie spada poniżej 20 °C, więc organizm nie "
                      "ma nocnej ulgi, wiodący, często pomijany czynnik zgonów "
                      "związanych z upałem.",
        "coldspell_title": "Dni fali mrozów w roku, {name}",
        "coldspell_ylabel": "Dni fali mrozów w roku",
        "coldspell_series": "dni fali mrozów",
        "cap_coldspell": "Dni w fali mrozów: ciąg ≥3 dni z dobowym minimum poniżej "
                         "lokalnego 10. percentyla z lat 1961-1990. Długotrwały mróz "
                         "zwiększa zimową nadmiarową śmiertelność sercowo-naczyniową "
                         "i oddechową.",
        "heavyrain_title": "Dni ulewnych deszczy w roku, {name}",
        "heavyrain_ylabel": "Dni w roku",
        "heavyrain_series": "dni ≥ {mm:.0f} mm",
        "cap_heavyrain": "Dni z opadem co najmniej 20 mm (ETCCDI R20mm), ulewy "
                         "wywołujące powodzie, niosące urazy, przesiedlenia i choroby "
                         "przenoszone przez wodę.",
        "heatindex_title": "Dni groźnego indeksu upału w roku, {name}",
        "heatindex_ylabel": "Dni w roku",
        "heat_strong": "≥ {t:.0f} °C (skrajna ostrożność)",
        "heat_danger": "≥ {t:.0f} °C (niebezpiecznie)",
        "cap_heatindex": "Dni, gdy temperatura odczuwalna (indeks upału uwzględniający "
                         "wilgotność) osiąga poziom stresu cieplnego, miara z "
                         "ostrzeżeń przed upałem. Wymaga zbioru temperatury "
                         "odczuwalnej.",
        "footer": 'Wygenerowano {date} · dane z '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(reanaliza historyczna ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'źródło na GitHub</a>',
        # Appearance panel (client-side, window.__tpref). Curated: these
        # override the machine-translated i18n_data/_mapui.json layer.
        "pref_title": "Wygląd",
        "pref_note": "Wybierz wygląd witryny. Twój wybór zostanie zapisany "
                     "na tym urządzeniu.",
        "pref_close": "Zamknij",
        "pref_theme": "Motyw",
        "pref_light": "Jasny",
        "pref_dark": "Ciemny",
        "pref_style": "Styl",
        "pref_style_objective": "Rzeczowy",
        "pref_style_editorial": "Redakcyjny",
        "pref_style_product": "Produktowy",
        "pref_style_atlas": "Atlas",
        "pref_accent": "Akcent",
        "pref_headline": "Krój nagłówków",
        "pref_sans": "Bezszeryfowy",
        "pref_serif": "Szeryfowy",
        "pref_density": "Gęstość",
        "pref_comfortable": "Komfortowa",
        "pref_compact": "Kompaktowa",
        "pref_header": "Nagłówek strony",
        "pref_plain": "Zwykły",
        "pref_tint": "Odcień",
        "pref_acc_cobalt": "Kobaltowy",
        "pref_acc_red": "Czerwony",
        "pref_acc_teal": "Morski",
        "pref_acc_forest": "Leśny",
        "pref_acc_amber": "Bursztynowy",
        "pref_acc_slate": "Grafitowy",
        "hb_world": "Miasta świata",
        "hb_since": "od 1940",
        "hb_title": "Średnie ocieplenie głównych miast świata od 1940 r., "
                    "równomiernie ważone, obliczone na podstawie danych "
                    "z tej witryny",
    },
    "de": {
        "html_lang": "de",
        "extreme_weather": "Extremwetter",
        "share": "Teilen",
        "nav_dashboard": "Klima-Dashboard",
        "analog_past": "1940 fühlte sich das hiesige Klima eher wie {analog} heute an, etwa {d} °C kühler.",
        "analog_line": "Bis 2050 könnte sich das hiesige Klima eher wie {analog} heute anfühlen, etwa +{d} °C wärmer.",
        "per_decade_c": "°C / Dekade",
        "map_coverage": "Bisher {done} von {total} Städten analysiert - der Rest kommt Tag für Tag hinzu.",
        "cur_so_far": "{year} bisher (bis {day}. {month}): im Mittel {v} °C, {d} °C gegenüber dem Mittel 1961-1990 für dieselben Tage des Jahres.",
        "cmp_title": "Zwei Städte vergleichen",
        "cmp_hint": "Jede Kurve zeigt die Jahresanomalie der Stadt gegenüber ihrem eigenen Mittel 1961-1990, sodass Orte mit unterschiedlichem Klima fair vergleichbar sind.",
        "cmp_city_a": "Erste Stadt",
        "cmp_city_b": "Zweite Stadt",
        "kpi_rate": "Erwärmungsrate der Welt",
        "kpi_since": "Erwärmung der Welt seit 1940",
        "kpi_cities": "Analysierte Städte",
        "kpi_warmest": "Wärmstes Jahr (Weltmittel)",
        "sum_season": "Am schnellsten erwärmt sich hier: {season} ({v} °C pro Dekade).",
        "sum_month": "Am schnellsten erwärmt sich hier: {month} ({v} °C pro Dekade).",
        "season_winter": "Winter",
        "season_spring": "Frühling",
        "season_summer": "Sommer",
        "season_autumn": "Herbst",
        "grid_alias_note": "Die Temperaturdaten werden je ~11-km-Klimarasterzelle berechnet. {alias} liegt in derselben Zelle wie {city}, daher zeigen beide denselben Verlauf seit 1940.",
        "map_coverage_help": "Hilf beim Sammeln der Daten",
        "qv_nodata": "Für diese Stadt gibt es noch keine Daten.",
        "qv_nearest": "Nächstgelegene analysierte Stadt",
        "per_decade_days": "Tage / Dekade",
        "ns": "n. s.",
        "smoothed": "Glättung (LOESS)",
        "guide_title": "ℹ️ So lesen Sie diese Diagramme",
        "guide_body":
            "<li><b>Punkte / Balken</b>: der Wert für jedes einzelne Jahr.</li>"
            "<li><b>Fette farbige Kurve</b>: LOESS-Glättung: der lokale Trend, der "
            "sich biegen darf, sodass die Änderung der Rate sichtbar wird (z. B. "
            "beschleunigte Erwärmung nach ~1985).</li>"
            "<li><b>Gestrichelte Linie</b>: der gerade robuste (Theil-Sen) Trend; "
            "seine Steigung ist der Wert „pro Dekade“ in der Legende.</li>"
            "<li><b>p&lt;0,05 / n. s.</b>: Mann-Kendall-Signifikanz: ob der Trend "
            "statistisch real ist oder nur Rauschen sein könnte (n. s. = nicht "
            "signifikant). Temperatur ist meist signifikant, Niederschlag oft "
            "nicht.</li>"
            "<li><b>Schattiertes Band</b>: die gesamte historische Spanne über "
            "alle Jahre für diesen Monat.</li>"
            "<li><b>Heatmap-Farben</b>: Temperatur (blau kalt → rot warm); lesen "
            "Sie eine Spalte von unten nach oben, um die Veränderung des Monats "
            "über die Jahre zu sehen.</li>",
        "months": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "threshold_title": "Heiße und Frosttage pro Jahr, {name}",
        "threshold_hot": "heiße Tage (>{t:.0f} °C)",
        "threshold_freeze": "Frosttage (<{t:.0f} °C)",
        "days_per_year": "Tage pro Jahr",
        "year": "Jahr",
        "month": "Monat",
        "yearly_title": "Jährliche Mitteltemperatur über die Jahre, {name}",
        "yearly_ylabel": "Jährliche Mitteltemperatur (°C)",
        "annual_mean": "Jahresmittel",
        "trend": "Trend",
        "anomaly_title": "Jährliche Temperaturanomalie, {name}",
        "anomaly_ylabel": "Anomalie (°C)",
        "vs_baseline": "ggü. Mittel {lo}-{hi} ({base:.1f} °C)",
        "vs_full": "ggü. Gesamtmittel ({base:.1f} °C)",
        "heatmap_title": "Monatliche Mitteltemperatur nach Jahr, {name}",
        "heatmap_cbar": "Monatsmittel (°C)",
        "anom_heatmap_title": "Monatsanomalie ggü. {base}, {name}",
        "anom_heatmap_cbar": "Anomalie ggü. {base} (°C)",
        "full_period": "Gesamtzeitraum",
        "dashboard_suptitle": "Temperaturen, {name} {start}-{end} "
                              "(Quelle: Open-Meteo Reanalyse)",
        "page_title": "Temperaturen, {name}",
        "subtitle": "{start}-{end} · {days} Tage · wärmstes {wy} ({wv:.1f} °C), "
                    "kältestes {cy} ({cv:.1f} °C)",
        "card_trend": "Erwärmungstrend",
        "card_mean": "Mittlere Tagestemperatur",
        "card_warmest": "Wärmstes Jahr",
        "card_coldest": "Kältestes Jahr",
        "cap_yearly": "Jahresmittel mit LOESS-Glättung (zeigt Beschleunigung) und "
                      "robustem Theil-Sen-Trend + Signifikanz",
        "cap_anomalies": "Jedes Jahr im Vergleich zum Mittel 1961-1990: rote Balken "
                         "wärmer, blaue kühler. Der Wechsel von Blau zu Rot ist die "
                         "Erwärmung.",
        "cap_heatmap": "Der Monatsdurchschnitt jedes Jahres als Farbraster "
                       "(2-°C-Stufen). Lesen Sie eine Spalte nach oben, um die "
                       "Erwärmung des Monats über die Jahrzehnte zu sehen.",
        "cap_anom_heatmap": "Dasselbe Raster, aber jeder Monat an seiner eigenen Norm "
                            "1961-1990 gemessen, sodass nur die Änderung sichtbar ist "
                            "(rot wärmer, blau kühler), Jahreszyklus entfernt.",
        "cap_threshold": "Tage pro Jahr über 18 °C (heiß) und unter 0 °C (Frost). Wo "
                         "sich die robusten Trends kreuzen, gibt es nun mehr heiße "
                         "als Frosttage.",
        "hint": "Klicken Sie irgendwo oder drücken Sie Esc zum Schließen",
        "site_title": "Temperaturen der Städte weltweit",
        "intro": "Wie sich die großen Städte der Welt seit 1940 erwärmt haben: tägliche Temperaturdaten aus der ERA5-Klimareanalyse.",
        "map_heading": "Temperaturen weltweit",
        "map_sub": "Wählen Sie eine Stadt auf der Karte oder aus der Liste",
        "regions": {"Europe": "Europa", "Asia": "Asien",
                    "Middle East": "Naher Osten", "Africa": "Afrika",
                    "North America": "Nordamerika",
                    "South America": "Südamerika", "Oceania": "Ozeanien"},
        "choose_city": "Stadt wählen...",
        "back_to_map": "🗺 Karte",
        "range_title": "Monatliche Temperaturspanne über die Jahre, {name}",
        "range_min_max": "Min-Max {start}-{end}",
        "range_average": "Durchschnitt",
        "range_latest": "aktuell ({year})",
        "range_ylabel": "Monatliche Mitteltemperatur (°C)",
        "cap_range": "Min-Max-Spanne jedes Monats über die Jahre, mit dem "
                     "aktuellen Jahr. Liegt es am oberen Rand?",
        "record_title": "Monatliche Rekord-Höchst-/Tiefstwerte (Tageswerte), {name}",
        "record_band": "Rekordspanne {start}-{end}",
        "record_latest_high": "Höchstwerte {year}",
        "record_latest_low": "Tiefstwerte {year}",
        "record_ylabel": "Tagestemperatur (°C)",
        "cap_records": "Rekord-Tageshöchst- und -tiefstwerte je Monat, mit den "
                       "Extremen des aktuellen Jahres",
        "volatility_title": "Tag-zu-Tag-Temperatursprünge pro Jahr, {name}",
        "volatility_jump": "Tagessprung",
        "volatility_ylabel": "Tage mit großem Sprung",
        "cap_volatility": "Wie oft große Tag-zu-Tag-Temperatursprünge pro Jahr "
                          "auftreten (≥6 °C), Temperaturschwankung",
        "per_decade_mm": "mm / Dekade",
        "precip_title": "Jährlicher Niederschlag, {name}",
        "precip_ylabel": "Niederschlag (mm / Jahr)",
        "precip_annual": "Jahressumme",
        "cap_precip": "Jährliche Niederschlagssumme (Regen und Schmelzwasser) mit Trend",
        "stripes_title": "Erwärmungsstreifen, {name}",
        "stripes_cbar": "Anomalie ggü. {lo}-{hi} (°C)",
        "cap_stripes": "Jeder Streifen ist ein Jahr: blau kühler, rot wärmer als "
                       "das Mittel 1961-1990. Der Übergang von Blau zu Rot ist die "
                       "Erwärmung, allein an der Farbe ablesbar.",
        "season_title": "Länge der Vegetationsperiode, {name}",
        "season_ylabel": "Länge der Vegetationsperiode (Tage)",
        "season_annual": "Länge der Periode",
        "cap_season": "Länge der thermischen Vegetationsperiode pro Jahr (Folge von "
                      "Tagen mit Tagesmittel ≥ 5 °C): das frostfreie Fenster, von "
                      "dem die Landwirtschaft abhängt, das sich mit der Erwärmung "
                      "verlängert.",
        "dtr_title": "Tagesgang der Temperatur (Tag − Nacht), {name}",
        "dtr_ylabel": "Mittleres Tagesmax − -min (°C)",
        "dtr_annual": "jährliche mittlere Spanne",
        "cap_dtr": "Der mittlere Abstand zwischen Tageshoch und -tief. Eine "
                   "schrumpfende Spanne ist ein Treibhaus-Fingerabdruck: Nächte "
                   "erwärmen sich schneller als Tage; eine wachsende kann "
                   "Austrocknung anzeigen.",
        "seasonshift_title": "Wie sich der Jahreszyklus verschob, {name}",
        "seasonshift_ylabel": "Monatliche Mitteltemperatur (°C)",
        "cap_seasonshift": "Das durchschnittliche Jahr der ersten gegenüber der "
                           "letzten Dekade. Der Abstand der Kurven je Monat zeigt, "
                           "welche Teile des Jahres sich am stärksten erwärmten (oft "
                           "Winter mehr als Sommer).",
        "health_heading": "Gesundheitsrelevante Indikatoren",
        "health_sub": "Wie sich die Erwärmungstrends oben in anerkannte Maße für "
                      "Hitze-, Kälte- und Extremereignis-Belastung übersetzen. Jedes "
                      "Diagramm erscheint, wo die nötigen Daten vorliegen.",
        "degreedays_title": "Heiz- und Kühlgradtage, {name}",
        "dd_ylabel": "Gradtage pro Jahr (°C·Tage)",
        "hdd_label": "Heizen (< {t:.0f} °C)",
        "cdd_label": "Kühlen (> {t:.0f} °C)",
        "per_decade_dd": "°C·Tage / Dekade",
        "cap_degreedays": "Die jährliche thermische Komfortlast: der Heizbedarf "
                          "(unter 18 °C) sinkt, der Kühlbedarf (über 22 °C) steigt, ein Maß für Kältebelastung und Klimaanlagenbedarf.",
        "heatwave_title": "Hitzewellentage pro Jahr, {name}",
        "heatwave_ylabel": "Hitzewellentage pro Jahr",
        "heatwave_series": "Hitzewellentage",
        "cap_heatwave": "Tage in einer Hitzewelle: eine Folge von ≥3 Tagen mit "
                        "Tageshöchstwert über dem lokalen 90. Perzentil von "
                        "1961-1990. Anhaltende Tageshitze ist der Haupttreiber der "
                        "Übersterblichkeit bei Hitzewellen.",
        "tropic_title": "Tropennächte pro Jahr, {name}",
        "tropic_ylabel": "Nächte pro Jahr",
        "tropic_series": "Nächte ≥ {t:.0f} °C",
        "cap_tropic": "Nächte, in denen das Minimum nicht unter 20 °C fällt, sodass "
                      "der Körper keine nächtliche Erholung hat, ein führender, oft "
                      "übersehener Treiber hitzebedingter Todesfälle.",
        "coldspell_title": "Kältewellentage pro Jahr, {name}",
        "coldspell_ylabel": "Kältewellentage pro Jahr",
        "coldspell_series": "Kältewellentage",
        "cap_coldspell": "Tage in einer Kältewelle: eine Folge von ≥3 Tagen mit "
                         "Tagestiefstwert unter dem lokalen 10. Perzentil von "
                         "1961-1990. Anhaltende Kälte treibt die winterliche "
                         "Übersterblichkeit (Herz-Kreislauf, Atemwege).",
        "heavyrain_title": "Starkregentage pro Jahr, {name}",
        "heavyrain_ylabel": "Tage pro Jahr",
        "heavyrain_series": "Tage ≥ {mm:.0f} mm",
        "cap_heavyrain": "Tage mit mindestens 20 mm Regen (ETCCDI R20mm), überschwemmungsauslösende Güsse mit Verletzungen, "
                         "Vertreibung und wasserbürtigen Krankheiten.",
        "heatindex_title": "Gefährliche Hitzeindex-Tage pro Jahr, {name}",
        "heatindex_ylabel": "Tage pro Jahr",
        "heat_strong": "≥ {t:.0f} °C (erhöhte Vorsicht)",
        "heat_danger": "≥ {t:.0f} °C (Gefahr)",
        "cap_heatindex": "Tage, an denen die gefühlte Temperatur (Hitzeindex inkl. "
                         "Luftfeuchte) Hitzestress-Niveaus erreicht, das Maß "
                         "amtlicher Hitzewarnungen. Benötigt den Datensatz der "
                         "gefühlten Temperatur.",
        "footer": 'Erstellt {date} · Daten von '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(historische Reanalyse ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'Quelle auf GitHub</a>',
        # Appearance panel (client-side, window.__tpref). Curated: these
        # override the machine-translated i18n_data/_mapui.json layer.
        "pref_title": "Darstellung",
        "pref_note": "Wähle, wie die Website aussieht. Deine Auswahl wird "
                     "auf diesem Gerät gespeichert.",
        "pref_close": "Schließen",
        "pref_theme": "Design",
        "pref_light": "Hell",
        "pref_dark": "Dunkel",
        "pref_style": "Stil",
        "pref_style_objective": "Sachlich",
        "pref_style_editorial": "Redaktionell",
        "pref_style_product": "Produkt",
        "pref_style_atlas": "Atlas",
        "pref_accent": "Akzent",
        "pref_headline": "Überschriftenschrift",
        "pref_sans": "Serifenlos",
        "pref_serif": "Mit Serifen",
        "pref_density": "Dichte",
        "pref_comfortable": "Komfortabel",
        "pref_compact": "Kompakt",
        "pref_header": "Seitenkopf",
        "pref_plain": "Schlicht",
        "pref_tint": "Tönung",
        "pref_acc_cobalt": "Kobaltblau",
        "pref_acc_red": "Rot",
        "pref_acc_teal": "Blaugrün",
        "pref_acc_forest": "Waldgrün",
        "pref_acc_amber": "Bernstein",
        "pref_acc_slate": "Schiefergrau",
        "hb_world": "Weltstädte",
        "hb_since": "seit 1940",
        "hb_title": "Durchschnittliche Erwärmung der großen Städte der Welt "
                    "seit 1940, gleich gewichtet, berechnet aus den Daten "
                    "dieser Website",
    },
    "fr": {
        "html_lang": "fr",
        "extreme_weather": "Météo extrême",
        "share": "Partager",
        "nav_dashboard": "Tableau climatique",
        "analog_past": "En 1940, le climat local ressemblait davantage à {analog} aujourd'hui, environ {d} °C de moins.",
        "analog_line": "D'ici 2050, le climat local pourrait ressembler à {analog} aujourd'hui, environ +{d} °C de plus.",
        "per_decade_c": "°C / décennie",
        "map_coverage": "{done} villes sur {total} analysées à ce jour - le reste arrive jour après jour.",
        "cur_so_far": "{year} jusqu'ici (au {day} {month}) : {v} °C en moyenne, {d} °C par rapport à la moyenne 1961-1990 pour les mêmes jours de l'année.",
        "cmp_title": "Comparer deux villes",
        "cmp_hint": "Chaque courbe est l'anomalie annuelle de la ville par rapport à sa propre moyenne 1961-1990, ce qui rend comparables des climats différents.",
        "cmp_city_a": "Première ville",
        "cmp_city_b": "Deuxième ville",
        "kpi_rate": "Rythme du réchauffement mondial",
        "kpi_since": "Réchauffement mondial depuis 1940",
        "kpi_cities": "Villes analysées",
        "kpi_warmest": "Année la plus chaude (moyenne mondiale)",
        "sum_season": "Saison au réchauffement le plus rapide ici : {season} ({v} °C par décennie).",
        "sum_month": "Mois au réchauffement le plus rapide ici : {month} ({v} °C par décennie).",
        "season_winter": "hiver",
        "season_spring": "printemps",
        "season_summer": "été",
        "season_autumn": "automne",
        "grid_alias_note": "Les données de température sont calculées par cellule de grille climatique d'environ 11 km. {alias} partage sa cellule avec {city} : les deux affichent donc le même historique depuis 1940.",
        "map_coverage_help": "Aidez à collecter les données",
        "qv_nodata": "Pas encore de données pour cette ville.",
        "qv_nearest": "Ville analysée la plus proche",
        "per_decade_days": "jours / décennie",
        "ns": "n.s.",
        "smoothed": "lissage (LOESS)",
        "guide_title": "ℹ️ Comment lire ces graphiques",
        "guide_body":
            "<li><b>Points / barres</b>: la valeur de chaque année.</li>"
            "<li><b>Courbe colorée en gras</b>: un lissage LOESS : la tendance "
            "locale, libre de s'infléchir, pour voir l'évolution du rythme dans le "
            "temps (p. ex. un réchauffement qui s'accélère après ~1985).</li>"
            "<li><b>Ligne pointillée</b>: la tendance droite robuste (Theil-Sen) ; "
            "sa pente est la valeur « par décennie » dans la légende.</li>"
            "<li><b>p&lt;0,05 / n.s.</b>: significativité de Mann-Kendall : la "
            "tendance est-elle statistiquement réelle ou simple bruit (n.s. = non "
            "significatif). La température est généralement significative ; les "
            "précipitations souvent non.</li>"
            "<li><b>Bande ombrée</b>: toute l'amplitude historique sur l'ensemble "
            "des années pour ce mois.</li>"
            "<li><b>Couleurs de la carte thermique</b>: température (bleu froid → "
            "rouge chaud) ; lisez une colonne de bas en haut pour suivre l'évolution "
            "du mois au fil des ans.</li>",
        "months": ["janv.", "févr.", "mars", "avr.", "mai", "juin",
                   "juil.", "août", "sept.", "oct.", "nov.", "déc."],
        "threshold_title": "Jours chauds et de gel par an, {name}",
        "threshold_hot": "jours chauds (>{t:.0f} °C)",
        "threshold_freeze": "jours de gel (<{t:.0f} °C)",
        "days_per_year": "Jours par an",
        "year": "Année",
        "month": "Mois",
        "yearly_title": "Température moyenne annuelle au fil des ans, {name}",
        "yearly_ylabel": "Température moyenne annuelle (°C)",
        "annual_mean": "moyenne annuelle",
        "trend": "tendance",
        "anomaly_title": "Anomalie de température annuelle, {name}",
        "anomaly_ylabel": "Anomalie (°C)",
        "vs_baseline": "par rapport à la moyenne {lo}-{hi} ({base:.1f} °C)",
        "vs_full": "par rapport à la moyenne de toute la période ({base:.1f} °C)",
        "heatmap_title": "Température moyenne mensuelle par année, {name}",
        "heatmap_cbar": "Moyenne mensuelle (°C)",
        "anom_heatmap_title": "Anomalie mensuelle par rapport à {base}, {name}",
        "anom_heatmap_cbar": "Anomalie par rapport à {base} (°C)",
        "full_period": "toute la période",
        "dashboard_suptitle": "Températures, {name} {start}-{end} "
                              "(source : réanalyse Open-Meteo)",
        "page_title": "Températures, {name}",
        "subtitle": "{start}-{end} · {days} jours · plus chaude {wy} ({wv:.1f} °C), "
                    "plus froide {cy} ({cv:.1f} °C)",
        "card_trend": "Tendance au réchauffement",
        "card_mean": "Temp. moyenne journalière",
        "card_warmest": "Année la plus chaude",
        "card_coldest": "Année la plus froide",
        "cap_yearly": "Moyenne annuelle avec un lissage LOESS (montre l'accélération) "
                      "et une tendance robuste de Theil-Sen + significativité",
        "cap_anomalies": "Chaque année comparée à la moyenne 1961-1990 : barres rouges "
                         "plus chaudes, bleues plus froides. Le passage du bleu au "
                         "rouge est le réchauffement.",
        "cap_heatmap": "La moyenne de chaque mois pour chaque année en grille de "
                       "couleurs (paliers de 2 °C). Lisez une colonne vers le haut "
                       "pour voir le mois se réchauffer au fil des décennies.",
        "cap_anom_heatmap": "La même grille, mais chaque mois mesuré par rapport à sa "
                            "propre normale 1961-1990, ne montrant que le changement "
                            "(rouge plus chaud, bleu plus froid), cycle saisonnier "
                            "retiré.",
        "cap_threshold": "Jours par an au-dessus de 18 °C (chauds) et au-dessous de "
                         "0 °C (gel). Le croisement des tendances robustes signifie "
                         "qu'il y a désormais plus de jours chauds que de jours de gel.",
        "hint": "Cliquez n'importe où ou appuyez sur Échap pour fermer",
        "site_title": "Températures des villes du monde",
        "intro": "Comment les grandes villes du monde se sont réchauffées depuis 1940 : relevés quotidiens de température issus de la réanalyse climatique ERA5.",
        "map_heading": "Températures dans le monde",
        "map_sub": "Choisissez une ville sur la carte ou dans la liste",
        "regions": {"Europe": "Europe", "Asia": "Asie",
                    "Middle East": "Moyen-Orient", "Africa": "Afrique",
                    "North America": "Amérique du Nord",
                    "South America": "Amérique du Sud", "Oceania": "Océanie"},
        "choose_city": "Choisir une ville...",
        "back_to_map": "🗺 Carte",
        "range_title": "Amplitude des températures mensuelles au fil des ans, {name}",
        "range_min_max": "min-max {start}-{end}",
        "range_average": "moyenne",
        "range_latest": "récent ({year})",
        "range_ylabel": "Température moyenne mensuelle (°C)",
        "cap_range": "L'amplitude min-max de chaque mois au fil des ans, avec l'année "
                     "la plus récente. Frôle-t-elle le bord chaud ?",
        "record_title": "Records journaliers mensuels (max/min), {name}",
        "record_band": "amplitude des records {start}-{end}",
        "record_latest_high": "maxima {year}",
        "record_latest_low": "minima {year}",
        "record_ylabel": "Température journalière (°C)",
        "cap_records": "Le record journalier absolu, haut et bas, de chaque mois, "
                       "avec les extrêmes de l'année la plus récente",
        "volatility_title": "Sauts de température d'un jour à l'autre par an, {name}",
        "volatility_jump": "saut journalier",
        "volatility_ylabel": "Jours avec un grand saut",
        "cap_volatility": "Fréquence des grands sauts de température d'un jour à "
                          "l'autre chaque année (≥6 °C), variabilité thermique",
        "per_decade_mm": "mm / décennie",
        "precip_title": "Précipitations annuelles, {name}",
        "precip_ylabel": "Précipitations (mm / an)",
        "precip_annual": "total annuel",
        "cap_precip": "Précipitations annuelles totales (pluie et eau de neige) "
                      "avec une tendance",
        "stripes_title": "Bandes du réchauffement, {name}",
        "stripes_cbar": "Anomalie par rapport à {lo}-{hi} (°C)",
        "cap_stripes": "Chaque bande est une année : bleu plus froid, rouge plus "
                       "chaud que la moyenne 1961-1990. Le glissement du bleu au "
                       "rouge est le réchauffement, lisible à la seule couleur.",
        "season_title": "Durée de la saison de végétation, {name}",
        "season_ylabel": "Durée de la saison de végétation (jours)",
        "season_annual": "durée de la saison",
        "cap_season": "Durée de la saison de végétation thermique chaque année "
                      "(suite de jours dont la moyenne ≥ 5 °C) : la fenêtre sans "
                      "gel dont dépend l'agriculture, qui s'allonge avec le "
                      "réchauffement.",
        "dtr_title": "Amplitude thermique diurne (jour − nuit), {name}",
        "dtr_ylabel": "Moyenne max − min journalier (°C)",
        "dtr_annual": "amplitude moyenne annuelle",
        "cap_dtr": "L'écart moyen entre le maximum et le minimum du jour. Une "
                   "amplitude qui rétrécit est une empreinte de l'effet de serre : les nuits se réchauffent plus vite que les jours ; une amplitude "
                   "qui s'élargit peut signaler un assèchement.",
        "seasonshift_title": "Comment le cycle saisonnier s'est déplacé, {name}",
        "seasonshift_ylabel": "Température moyenne mensuelle (°C)",
        "cap_seasonshift": "L'année moyenne de la première décennie face à la "
                           "dernière. L'écart entre les courbes à chaque mois montre "
                           "quelles parties de l'année se sont le plus réchauffées "
                           "(souvent les hivers plus que les étés).",
        "health_heading": "Indicateurs d'impact sanitaire",
        "health_sub": "Comment les tendances au réchauffement ci-dessus se traduisent "
                      "en mesures reconnues d'exposition à la chaleur, au froid et aux "
                      "événements extrêmes. Chaque graphique apparaît là où les "
                      "données nécessaires sont disponibles.",
        "degreedays_title": "Degrés-jours de chauffage et de climatisation, {name}",
        "dd_ylabel": "Degrés-jours par an (°C·jours)",
        "hdd_label": "chauffage (< {t:.0f} °C)",
        "cdd_label": "climatisation (> {t:.0f} °C)",
        "per_decade_dd": "°C·jours / décennie",
        "cap_degreedays": "La charge annuelle de confort thermique : le besoin de "
                          "chauffage (sous 18 °C) baisse tandis que le besoin de "
                          "climatisation (au-dessus de 22 °C) augmente, un indicateur "
                          "d'exposition au froid et de demande de climatisation.",
        "heatwave_title": "Jours de canicule par an, {name}",
        "heatwave_ylabel": "Jours de canicule par an",
        "heatwave_series": "jours de canicule",
        "cap_heatwave": "Jours en canicule : une série de ≥3 jours dont le maximum "
                        "dépasse le 90e centile local de 1961-1990. La chaleur diurne "
                        "prolongée est le principal moteur de la surmortalité des "
                        "canicules.",
        "tropic_title": "Nuits tropicales par an, {name}",
        "tropic_ylabel": "Nuits par an",
        "tropic_series": "nuits ≥ {t:.0f} °C",
        "cap_tropic": "Nuits où le minimum reste au moins à 20 °C, sans répit nocturne "
                      "pour l'organisme, un moteur majeur, souvent négligé, des décès "
                      "liés à la chaleur.",
        "coldspell_title": "Jours de vague de froid par an, {name}",
        "coldspell_ylabel": "Jours de vague de froid par an",
        "coldspell_series": "jours de vague de froid",
        "cap_coldspell": "Jours en vague de froid : une série de ≥3 jours dont le "
                         "minimum est sous le 10e centile local de 1961-1990. Le froid "
                         "prolongé alimente la surmortalité hivernale (cardiovasculaire "
                         "et respiratoire).",
        "heavyrain_title": "Jours de fortes pluies par an, {name}",
        "heavyrain_ylabel": "Jours par an",
        "heavyrain_series": "jours ≥ {mm:.0f} mm",
        "cap_heavyrain": "Jours avec au moins 20 mm de pluie (ETCCDI R20mm), des averses provoquant inondations, blessures, déplacements et "
                         "maladies hydriques.",
        "heatindex_title": "Jours d'indice de chaleur dangereux par an, {name}",
        "heatindex_ylabel": "Jours par an",
        "heat_strong": "≥ {t:.0f} °C (extrême prudence)",
        "heat_danger": "≥ {t:.0f} °C (danger)",
        "cap_heatindex": "Jours où la température ressentie (indice de chaleur "
                         "intégrant l'humidité) atteint des niveaux de stress thermique, la mesure des alertes canicule. Nécessite le jeu "
                         "de données de température ressentie.",
        "footer": 'Généré le {date} · données de '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(réanalyse historique ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'source sur GitHub</a>',
        # Appearance panel (client-side, window.__tpref). Curated: these
        # override the machine-translated i18n_data/_mapui.json layer.
        "pref_title": "Apparence",
        "pref_note": "Choisissez l'apparence du site. Votre choix est "
                     "enregistré sur cet appareil.",
        "pref_close": "Fermer",
        "pref_theme": "Thème",
        "pref_light": "Clair",
        "pref_dark": "Sombre",
        "pref_style": "Style",
        "pref_style_objective": "Sobre",
        "pref_style_editorial": "Éditorial",
        "pref_style_product": "Produit",
        "pref_style_atlas": "Atlas",
        "pref_accent": "Accent",
        "pref_headline": "Police des titres",
        "pref_sans": "Sans empattement",
        "pref_serif": "Avec empattements",
        "pref_density": "Densité",
        "pref_comfortable": "Confortable",
        "pref_compact": "Compacte",
        "pref_header": "En-tête de page",
        "pref_plain": "Simple",
        "pref_tint": "Teinte",
        "pref_acc_cobalt": "Cobalt",
        "pref_acc_red": "Rouge",
        "pref_acc_teal": "Sarcelle",
        "pref_acc_forest": "Forêt",
        "pref_acc_amber": "Ambre",
        "pref_acc_slate": "Ardoise",
        "hb_world": "Villes du monde",
        "hb_since": "depuis 1940",
        "hb_title": "Réchauffement moyen des grandes villes du monde depuis "
                    "1940, à pondération égale, calculé à partir des données "
                    "de ce site",
    },
    "es": {
        "html_lang": "es",
        "extreme_weather": "Clima extremo",
        "share": "Compartir",
        "nav_dashboard": "Panel climático",
        "analog_past": "En 1940, el clima local se parecía más a {analog} de hoy, unos {d} °C menos.",
        "analog_line": "Para 2050, el clima local podría parecerse a {analog} de hoy, unos +{d} °C más.",
        "per_decade_c": "°C / década",
        "map_coverage": "{done} de {total} ciudades analizadas hasta ahora - el resto se añade día a día.",
        "cur_so_far": "{year} hasta ahora (al {day} de {month}): {v} °C de media, {d} °C frente a la media de 1961-1990 para los mismos días del año.",
        "cmp_title": "Comparar dos ciudades",
        "cmp_hint": "Cada curva es la anomalía anual de esa ciudad frente a su propia media de 1961-1990, de modo que lugares con climas distintos se comparan con justicia.",
        "cmp_city_a": "Primera ciudad",
        "cmp_city_b": "Segunda ciudad",
        "kpi_rate": "Ritmo de calentamiento mundial",
        "kpi_since": "Calentamiento mundial desde 1940",
        "kpi_cities": "Ciudades analizadas",
        "kpi_warmest": "Año más cálido (media mundial)",
        "sum_season": "Estación que más se calienta aquí: {season} ({v} °C por década).",
        "sum_month": "Mes que más se calienta aquí: {month} ({v} °C por década).",
        "season_winter": "invierno",
        "season_spring": "primavera",
        "season_summer": "verano",
        "season_autumn": "otoño",
        "grid_alias_note": "Los datos de temperatura se calculan por celda de una malla climática de ~11 km. {alias} comparte celda con {city}, así que ambas muestran el mismo registro desde 1940.",
        "map_coverage_help": "Ayuda a recopilar los datos",
        "qv_nodata": "Aún no hay datos para esta ciudad.",
        "qv_nearest": "Ciudad analizada más cercana",
        "per_decade_days": "días / década",
        "ns": "n.s.",
        "smoothed": "suavizado (LOESS)",
        "guide_title": "ℹ️ Cómo leer estos gráficos",
        "guide_body":
            "<li><b>Puntos / barras</b>: el valor de cada año.</li>"
            "<li><b>Curva de color en negrita</b>: un suavizado LOESS: la tendencia "
            "local, libre de curvarse, para ver el cambio de ritmo en el tiempo "
            "(p. ej. un calentamiento que se acelera después de ~1985).</li>"
            "<li><b>Línea discontinua</b>: la tendencia recta robusta (Theil-Sen); "
            "su pendiente es la cifra « por década » de la leyenda.</li>"
            "<li><b>p&lt;0,05 / n.s.</b>: significancia de Mann-Kendall: si la "
            "tendencia es estadísticamente real o solo ruido (n.s. = no "
            "significativa). La temperatura suele ser significativa; la "
            "precipitación a menudo no.</li>"
            "<li><b>Banda sombreada</b>: todo el rango histórico de todos los años "
            "para ese mes.</li>"
            "<li><b>Colores del mapa de calor</b>: temperatura (azul frío → rojo "
            "cálido); lea una columna de abajo arriba para ver cómo cambia ese mes "
            "a lo largo de los años.</li>",
        "months": ["ene", "feb", "mar", "abr", "may", "jun",
                   "jul", "ago", "sep", "oct", "nov", "dic"],
        "threshold_title": "Días cálidos y de helada al año, {name}",
        "threshold_hot": "días cálidos (>{t:.0f} °C)",
        "threshold_freeze": "días de helada (<{t:.0f} °C)",
        "days_per_year": "Días al año",
        "year": "Año",
        "month": "Mes",
        "yearly_title": "Temperatura media anual a lo largo de los años, {name}",
        "yearly_ylabel": "Temperatura media anual (°C)",
        "annual_mean": "media anual",
        "trend": "tendencia",
        "anomaly_title": "Anomalía de temperatura anual, {name}",
        "anomaly_ylabel": "Anomalía (°C)",
        "vs_baseline": "respecto a la media {lo}-{hi} ({base:.1f} °C)",
        "vs_full": "respecto a la media de todo el período ({base:.1f} °C)",
        "heatmap_title": "Temperatura media mensual por año, {name}",
        "heatmap_cbar": "Media mensual (°C)",
        "anom_heatmap_title": "Anomalía mensual respecto a {base}, {name}",
        "anom_heatmap_cbar": "Anomalía respecto a {base} (°C)",
        "full_period": "todo el período",
        "dashboard_suptitle": "Temperaturas, {name} {start}-{end} "
                              "(fuente: reanálisis Open-Meteo)",
        "page_title": "Temperaturas, {name}",
        "subtitle": "{start}-{end} · {days} días · más cálido {wy} ({wv:.1f} °C), "
                    "más frío {cy} ({cv:.1f} °C)",
        "card_trend": "Tendencia de calentamiento",
        "card_mean": "Temp. media diaria",
        "card_warmest": "Año más cálido",
        "card_coldest": "Año más frío",
        "cap_yearly": "Media anual con un suavizado LOESS (muestra la aceleración) "
                      "y una tendencia robusta de Theil-Sen + significancia",
        "cap_anomalies": "Cada año comparado con la media de 1961-1990: barras rojas "
                         "más cálidas, azules más frías. El cambio de azul a rojo es "
                         "el calentamiento.",
        "cap_heatmap": "La media de cada mes en cada año como cuadrícula de colores "
                       "(bandas de 2 °C). Lea una columna hacia arriba para ver cómo "
                       "se calienta ese mes a lo largo de las décadas.",
        "cap_anom_heatmap": "La misma cuadrícula, pero cada mes medido frente a su "
                            "propia normal de 1961-1990, mostrando solo el cambio "
                            "(rojo más cálido, azul más frío), ciclo estacional "
                            "eliminado.",
        "cap_threshold": "Días al año por encima de 18 °C (cálidos) y por debajo de "
                         "0 °C (helada). El cruce de las tendencias robustas significa "
                         "que ya hay más días cálidos que de helada.",
        "hint": "Haga clic en cualquier lugar o pulse Esc para cerrar",
        "site_title": "Temperaturas de las ciudades del mundo",
        "intro": "Cómo se han calentado las grandes ciudades del mundo desde 1940: registros diarios de temperatura del reanálisis climático ERA5.",
        "map_heading": "Temperaturas en el mundo",
        "map_sub": "Elija una ciudad en el mapa o de la lista",
        "regions": {"Europe": "Europa", "Asia": "Asia",
                    "Middle East": "Oriente Medio", "Africa": "África",
                    "North America": "América del Norte",
                    "South America": "América del Sur", "Oceania": "Oceanía"},
        "choose_city": "Elegir una ciudad...",
        "back_to_map": "🗺 Mapa",
        "range_title": "Rango de temperaturas mensuales a lo largo de los años, {name}",
        "range_min_max": "mín-máx {start}-{end}",
        "range_average": "promedio",
        "range_latest": "reciente ({year})",
        "range_ylabel": "Temperatura media mensual (°C)",
        "cap_range": "El rango mín-máx de cada mes a lo largo de los años, con el año "
                     "más reciente. ¿Se acerca al extremo cálido?",
        "record_title": "Récords diarios mensuales (máx/mín), {name}",
        "record_band": "rango de récords {start}-{end}",
        "record_latest_high": "máximos {year}",
        "record_latest_low": "mínimos {year}",
        "record_ylabel": "Temperatura diaria (°C)",
        "cap_records": "El récord diario absoluto, alto y bajo, de cada mes, con los "
                       "extremos del año más reciente",
        "volatility_title": "Saltos de temperatura de un día a otro al año, {name}",
        "volatility_jump": "salto diario",
        "volatility_ylabel": "Días con un gran salto",
        "cap_volatility": "Con qué frecuencia ocurren grandes saltos de temperatura "
                          "de un día a otro cada año (≥6 °C), variabilidad térmica",
        "per_decade_mm": "mm / década",
        "precip_title": "Precipitación anual, {name}",
        "precip_ylabel": "Precipitación (mm / año)",
        "precip_annual": "total anual",
        "cap_precip": "Precipitación anual total (lluvia y agua de nieve) "
                      "con una tendencia",
        "stripes_title": "Franjas del calentamiento, {name}",
        "stripes_cbar": "Anomalía respecto a {lo}-{hi} (°C)",
        "cap_stripes": "Cada franja es un año: azul más frío, rojo más cálido que "
                       "la media 1961-1990. El paso del azul al rojo es el "
                       "calentamiento, legible solo por el color.",
        "season_title": "Duración de la estación de crecimiento, {name}",
        "season_ylabel": "Duración de la estación de crecimiento (días)",
        "season_annual": "duración de la estación",
        "cap_season": "Duración de la estación de crecimiento térmica cada año "
                      "(racha de días con media diaria ≥ 5 °C): la ventana sin "
                      "heladas de la que depende la agricultura, que se alarga con "
                      "el calentamiento.",
        "dtr_title": "Amplitud térmica diurna (día − noche), {name}",
        "dtr_ylabel": "Media de máx − mín diario (°C)",
        "dtr_annual": "amplitud media anual",
        "cap_dtr": "La diferencia media entre el máximo y el mínimo del día. Una "
                   "amplitud que se reduce es una huella del efecto invernadero: las noches se calientan más rápido que los días; una que se "
                   "amplía puede indicar desecación.",
        "seasonshift_title": "Cómo se desplazó el ciclo estacional, {name}",
        "seasonshift_ylabel": "Temperatura media mensual (°C)",
        "cap_seasonshift": "El año medio de la primera década frente a la última. La "
                           "distancia entre las curvas en cada mes muestra qué partes "
                           "del año se calentaron más (a menudo los inviernos más que "
                           "los veranos).",
        "health_heading": "Indicadores de impacto en la salud",
        "health_sub": "Cómo las tendencias de calentamiento anteriores se traducen en "
                      "medidas reconocidas de exposición al calor, al frío y a eventos "
                      "extremos. Cada gráfico aparece donde están disponibles los "
                      "datos necesarios.",
        "degreedays_title": "Grados-día de calefacción y refrigeración, {name}",
        "dd_ylabel": "Grados-día por año (°C·días)",
        "hdd_label": "calefacción (< {t:.0f} °C)",
        "cdd_label": "refrigeración (> {t:.0f} °C)",
        "per_decade_dd": "°C·días / década",
        "cap_degreedays": "La carga anual de confort térmico: la necesidad de "
                          "calefacción (por debajo de 18 °C) baja mientras la de "
                          "refrigeración (por encima de 22 °C) sube, un indicador de "
                          "exposición al frío y demanda de aire acondicionado.",
        "heatwave_title": "Días de ola de calor al año, {name}",
        "heatwave_ylabel": "Días de ola de calor al año",
        "heatwave_series": "días de ola de calor",
        "cap_heatwave": "Días en ola de calor: una racha de ≥3 días con la máxima "
                        "diaria por encima del percentil 90 local de 1961-1990. El "
                        "calor diurno sostenido es el principal motor de la "
                        "sobremortalidad por olas de calor.",
        "tropic_title": "Noches tropicales al año, {name}",
        "tropic_ylabel": "Noches al año",
        "tropic_series": "noches ≥ {t:.0f} °C",
        "cap_tropic": "Noches en que la mínima no baja de 20 °C, sin alivio nocturno "
                      "para el cuerpo, un motor principal, a menudo pasado por alto, "
                      "de las muertes por calor.",
        "coldspell_title": "Días de ola de frío al año, {name}",
        "coldspell_ylabel": "Días de ola de frío al año",
        "coldspell_series": "días de ola de frío",
        "cap_coldspell": "Días en ola de frío: una racha de ≥3 días con la mínima "
                         "diaria por debajo del percentil 10 local de 1961-1990. El "
                         "frío prolongado impulsa la sobremortalidad invernal "
                         "(cardiovascular y respiratoria).",
        "heavyrain_title": "Días de lluvia intensa al año, {name}",
        "heavyrain_ylabel": "Días al año",
        "heavyrain_series": "días ≥ {mm:.0f} mm",
        "cap_heavyrain": "Días con al menos 20 mm de lluvia (ETCCDI R20mm), aguaceros "
                         "que provocan inundaciones, con lesiones, desplazamientos y "
                         "enfermedades transmitidas por el agua.",
        "heatindex_title": "Días de índice de calor peligroso al año, {name}",
        "heatindex_ylabel": "Días al año",
        "heat_strong": "≥ {t:.0f} °C (precaución extrema)",
        "heat_danger": "≥ {t:.0f} °C (peligro)",
        "cap_heatindex": "Días en que la sensación térmica (índice de calor que "
                         "incluye la humedad) alcanza niveles de estrés térmico, la medida de los avisos de calor. Requiere el conjunto de datos "
                         "de sensación térmica.",
        "footer": 'Generado el {date} · datos de '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(reanálisis histórico ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'código en GitHub</a>',
        # Appearance panel (client-side, window.__tpref). Curated: these
        # override the machine-translated i18n_data/_mapui.json layer.
        "pref_title": "Apariencia",
        "pref_note": "Elige el aspecto del sitio. Tu elección se guarda en "
                     "este dispositivo.",
        "pref_close": "Cerrar",
        "pref_theme": "Tema",
        "pref_light": "Claro",
        "pref_dark": "Oscuro",
        "pref_style": "Estilo",
        "pref_style_objective": "Sobrio",
        "pref_style_editorial": "Editorial",
        "pref_style_product": "Producto",
        "pref_style_atlas": "Atlas",
        "pref_accent": "Acento",
        "pref_headline": "Fuente de titulares",
        "pref_sans": "Sin serifa",
        "pref_serif": "Con serifa",
        "pref_density": "Densidad",
        "pref_comfortable": "Cómoda",
        "pref_compact": "Compacta",
        "pref_header": "Encabezado de página",
        "pref_plain": "Simple",
        "pref_tint": "Tinte",
        "pref_acc_cobalt": "Cobalto",
        "pref_acc_red": "Rojo",
        "pref_acc_teal": "Verde azulado",
        "pref_acc_forest": "Verde bosque",
        "pref_acc_amber": "Ámbar",
        "pref_acc_slate": "Pizarra",
        "hb_world": "Ciudades del mundo",
        "hb_since": "desde 1940",
        "hb_title": "Calentamiento medio de las principales ciudades del "
                    "mundo desde 1940, con igual ponderación, calculado a "
                    "partir de los datos de este sitio",
    },
    "uk": {
        "html_lang": "uk",
        # Climate analog sentences: present in en/pl/de/fr/es; uk was missing
        # them and fell back to English. Placeholders {analog} and {d} must stay.
        # "місто" before {analog} keeps the undeclined city name grammatical
        # (it reads as apposition), the same trick the Polish strings use.
        "analog_line": "До 2050 року місцевий клімат може нагадувати місто {analog}, "
                       "приблизно на +{d} °C тепліше, ніж сьогодні.",
        "analog_past": "У 1940 році місцевий клімат нагадував місто {analog}, "
                       "приблизно на {d} °C прохолодніше, ніж сьогодні.",
        "extreme_weather": "Екстремальна погода",
        "share": "Поділитися",
        "nav_dashboard": "Кліматична панель",
        "per_decade_c": "°C / десятиліття",
        "map_coverage": "Проаналізовано {done} з {total} міст - решта додається день за днем.",
        "cur_so_far": "{year} досі (до {day} {month}): у середньому {v} °C, {d} °C відносно середнього 1961-1990 для тих самих днів року.",
        "cmp_title": "Порівняти два міста",
        "cmp_hint": "Кожна крива - це річна аномалія міста відносно його власного середнього 1961-1990, тож місця з різним кліматом порівнюються чесно.",
        "cmp_city_a": "Перше місто",
        "cmp_city_b": "Друге місто",
        "kpi_rate": "Темп потепління світу",
        "kpi_since": "Потепління світу з 1940",
        "kpi_cities": "Проаналізовані міста",
        "kpi_warmest": "Найтепліший рік (світове середнє)",
        "sum_season": "Найшвидше теплішає тут: {season} ({v} °C за десятиліття).",
        "sum_month": "Найшвидше теплішає тут: {month} ({v} °C за десятиліття).",
        "season_winter": "зима",
        "season_spring": "весна",
        "season_summer": "літо",
        "season_autumn": "осінь",
        "grid_alias_note": "Дані про температуру обчислюються для комірок кліматичної сітки ~11 км. {alias} лежить у тій самій комірці, що й {city}, тож обидві мають однаковий запис від 1940 року.",
        "map_coverage_help": "Допоможіть зібрати дані",
        "qv_nodata": "Для цього міста ще немає даних.",
        "qv_nearest": "Найближче проаналізоване місто",
        "per_decade_days": "днів / десятиліття",
        "ns": "нез.",
        "smoothed": "згладжування (LOESS)",
        "guide_title": "ℹ️ Як читати ці графіки",
        "guide_body":
            "<li><b>Точки / стовпчики</b>: значення для кожного року.</li>"
            "<li><b>Жирна кольорова крива</b>: згладжування LOESS: локальний тренд, "
            "який може вигинатися, тож видно зміну темпу з часом (напр., потепління, "
            "що прискорюється після ~1985).</li>"
            "<li><b>Пунктирна лінія</b>: прямий стійкий тренд (Тейла-Сена); його "
            "нахил це значення « за десятиліття » в легенді.</li>"
            "<li><b>p&lt;0,05 / нез.</b>: значущість Манна-Кендалла: чи тренд "
            "статистично реальний, чи це лише шум (нез. = незначущий). Температура "
            "зазвичай значуща; опади часто ні.</li>"
            "<li><b>Затінена смуга</b>: увесь історичний діапазон за всі роки для "
            "цього місяця.</li>"
            "<li><b>Кольори теплової карти</b>: температура (синій холодно → "
            "червоний тепло); читайте стовпець знизу вгору, щоб побачити зміну "
            "місяця впродовж років.</li>",
        "months": ["січ", "лют", "бер", "кві", "тра", "чер",
                   "лип", "сер", "вер", "жов", "лис", "гру"],
        "threshold_title": "Спекотні та морозні дні на рік, {name}",
        "threshold_hot": "спекотні дні (>{t:.0f} °C)",
        "threshold_freeze": "морозні дні (<{t:.0f} °C)",
        "days_per_year": "Днів на рік",
        "year": "Рік",
        "month": "Місяць",
        "yearly_title": "Середня річна температура впродовж років, {name}",
        "yearly_ylabel": "Середня річна температура (°C)",
        "annual_mean": "середня річна",
        "trend": "тренд",
        "anomaly_title": "Річна аномалія температури, {name}",
        "anomaly_ylabel": "Аномалія (°C)",
        "vs_baseline": "відносно середньої {lo}-{hi} ({base:.1f} °C)",
        "vs_full": "відносно середньої за весь період ({base:.1f} °C)",
        "heatmap_title": "Середня місячна температура за роками, {name}",
        "heatmap_cbar": "Середня місячна (°C)",
        "anom_heatmap_title": "Місячна аномалія відносно {base}, {name}",
        "anom_heatmap_cbar": "Аномалія відносно {base} (°C)",
        "full_period": "усього періоду",
        "dashboard_suptitle": "Температури, {name} {start}-{end} "
                              "(джерело: реаналіз Open-Meteo)",
        "page_title": "Температури, {name}",
        "subtitle": "{start}-{end} · {days} днів · найтепліший {wy} ({wv:.1f} °C), "
                    "найхолодніший {cy} ({cv:.1f} °C)",
        "card_trend": "Тренд потепління",
        "card_mean": "Середня добова темп.",
        "card_warmest": "Найтепліший рік",
        "card_coldest": "Найхолодніший рік",
        "cap_yearly": "Середня річна зі згладжуванням LOESS (показує прискорення) "
                      "та стійким трендом Тейла-Сена + значущість",
        "cap_anomalies": "Кожен рік порівняно із середньою 1961-1990: червоні "
                         "стовпчики тепліші, сині холодніші. Перехід від синього до "
                         "червоного це потепління.",
        "cap_heatmap": "Середнє кожного місяця за кожен рік як кольорова сітка "
                       "(смуги по 2 °C). Читайте стовпець угору, щоб побачити "
                       "потепління місяця впродовж десятиліть.",
        "cap_anom_heatmap": "Та сама сітка, але кожен місяць виміряно відносно власної "
                            "норми 1961-1990, тож видно лише зміну (червоний тепліше, "
                            "синій холодніше), сезонний цикл прибрано.",
        "cap_threshold": "Днів на рік вище 18 °C (спекотні) та нижче 0 °C (морозні). "
                         "Перетин стійких трендів означає, що спекотних днів тепер "
                         "більше, ніж морозних.",
        "hint": "Клацніть будь-де або натисніть Esc, щоб закрити",
        "site_title": "Температури міст світу",
        "intro": "Як потепліли найбільші міста світу від 1940 року: щоденні записи температури з кліматичного реаналізу ERA5.",
        "map_heading": "Температури у світі",
        "map_sub": "Оберіть місто на карті або зі списку",
        "regions": {"Europe": "Європа", "Asia": "Азія",
                    "Middle East": "Близький Схід", "Africa": "Африка",
                    "North America": "Північна Америка",
                    "South America": "Південна Америка", "Oceania": "Океанія"},
        "choose_city": "Оберіть місто...",
        "back_to_map": "🗺 Карта",
        "range_title": "Діапазон місячних температур впродовж років, {name}",
        "range_min_max": "мін-макс {start}-{end}",
        "range_average": "середня",
        "range_latest": "останній ({year})",
        "range_ylabel": "Середня місячна температура (°C)",
        "cap_range": "Діапазон мін-макс кожного місяця впродовж років, з останнім "
                     "роком. Чи тулиться він до теплого краю?",
        "record_title": "Місячні добові рекорди (макс/мін), {name}",
        "record_band": "діапазон рекордів {start}-{end}",
        "record_latest_high": "максимуми {year}",
        "record_latest_low": "мінімуми {year}",
        "record_ylabel": "Добова температура (°C)",
        "cap_records": "Абсолютний добовий рекорд, високий і низький, кожного місяця, "
                       "з екстремумами останнього року",
        "volatility_title": "Добові стрибки температури на рік, {name}",
        "volatility_jump": "добовий стрибок",
        "volatility_ylabel": "Днів із великим стрибком",
        "cap_volatility": "Як часто трапляються великі добові стрибки температури "
                          "щороку (≥6 °C), мінливість температури",
        "per_decade_mm": "мм / десятиліття",
        "precip_title": "Річні опади, {name}",
        "precip_ylabel": "Опади (мм / рік)",
        "precip_annual": "річна сума",
        "cap_precip": "Річна сума опадів (дощ і вода зі снігу) з лінією тренду",
        "stripes_title": "Смуги потепління, {name}",
        "stripes_cbar": "Аномалія відносно {lo}-{hi} (°C)",
        "cap_stripes": "Кожна смуга це один рік: синій холодніший, червоний "
                       "тепліший за середню 1961-1990. Перехід від синього до "
                       "червоного це потепління, читається самим лише кольором.",
        "season_title": "Тривалість вегетаційного періоду, {name}",
        "season_ylabel": "Тривалість вегетаційного періоду (днів)",
        "season_annual": "тривалість періоду",
        "cap_season": "Тривалість термічного вегетаційного періоду щороку (низка "
                      "днів із середньою добовою ≥ 5 °C): безморозне вікно, від "
                      "якого залежить сільське господарство, що подовжується з "
                      "потеплінням.",
        "dtr_title": "Добова амплітуда температури (день − ніч), {name}",
        "dtr_ylabel": "Середнє добове макс − мін (°C)",
        "dtr_annual": "середня річна амплітуда",
        "cap_dtr": "Середня різниця між денним максимумом і мінімумом. Амплітуда, "
                   "що зменшується, це слід парникового ефекту: ночі теплішають "
                   "швидше за дні; зростання може свідчити про висихання.",
        "seasonshift_title": "Як змістився сезонний цикл, {name}",
        "seasonshift_ylabel": "Середня місячна температура (°C)",
        "cap_seasonshift": "Усереднений рік першого десятиліття проти останнього. "
                           "Відстань між кривими в кожному місяці показує, які "
                           "частини року потеплішали найбільше (часто зими більше, "
                           "ніж літо).",
        "health_heading": "Показники впливу на здоров'я",
        "health_sub": "Як наведені вище тренди потепління переходять у визнані міри "
                      "впливу спеки, холоду та екстремальних явищ. Кожен графік "
                      "з'являється там, де доступні потрібні дані.",
        "degreedays_title": "Градусо-дні опалення та охолодження, {name}",
        "dd_ylabel": "Градусо-дні на рік (°C·дні)",
        "hdd_label": "опалення (< {t:.0f} °C)",
        "cdd_label": "охолодження (> {t:.0f} °C)",
        "per_decade_dd": "°C·дні / десятиліття",
        "cap_degreedays": "Річне навантаження теплового комфорту: потреба в опаленні "
                          "(нижче 18 °C) спадає, а в охолодженні (вище 22 °C) зростає, наближення впливу холоду та потреби в кондиціонуванні.",
        "heatwave_title": "Дні хвиль спеки на рік, {name}",
        "heatwave_ylabel": "Дні хвиль спеки на рік",
        "heatwave_series": "дні хвиль спеки",
        "cap_heatwave": "Дні у хвилі спеки: низка ≥3 днів із добовим максимумом вище "
                        "місцевого 90-го перцентиля 1961-1990. Тривала денна спека є головним чинником надлишкової смертності під час хвиль спеки.",
        "tropic_title": "Тропічні ночі на рік, {name}",
        "tropic_ylabel": "Ночей на рік",
        "tropic_series": "ночі ≥ {t:.0f} °C",
        "cap_tropic": "Ночі, коли мінімум не опускається нижче 20 °C, тож організм не "
                      "має нічного перепочинку, провідний, часто недооцінений чинник "
                      "смертей, пов'язаних зі спекою.",
        "coldspell_title": "Дні хвиль холоду на рік, {name}",
        "coldspell_ylabel": "Дні хвиль холоду на рік",
        "coldspell_series": "дні хвиль холоду",
        "cap_coldspell": "Дні у хвилі холоду: низка ≥3 днів із добовим мінімумом нижче "
                         "місцевого 10-го перцентиля 1961-1990. Тривалий холод посилює "
                         "зимову надлишкову смертність (серцево-судинну та дихальну).",
        "heavyrain_title": "Дні сильних дощів на рік, {name}",
        "heavyrain_ylabel": "Днів на рік",
        "heavyrain_series": "дні ≥ {mm:.0f} мм",
        "cap_heavyrain": "Дні щонайменше з 20 мм дощу (ETCCDI R20mm), зливи, що "
                         "спричиняють повені, травми, переселення та хвороби, що "
                         "передаються через воду.",
        "heatindex_title": "Дні небезпечного індексу спеки на рік, {name}",
        "heatindex_ylabel": "Днів на рік",
        "heat_strong": "≥ {t:.0f} °C (надзвичайна обережність)",
        "heat_danger": "≥ {t:.0f} °C (небезпека)",
        "cap_heatindex": "Дні, коли відчутна температура (індекс спеки з урахуванням "
                         "вологості) сягає рівнів теплового стресу, міра офіційних "
                         "попереджень про спеку. Потребує набору даних відчутної "
                         "температури.",
        "footer": 'Згенеровано {date} · дані з '
                  '<a href="https://open-meteo.com/">Open-Meteo</a> '
                  '(історичний реаналіз ERA5) · '
                  '<a href="https://github.com/YASoftwareDev/temperatury">'
                  'код на GitHub</a>',
        # Appearance panel (client-side, window.__tpref). Curated: these
        # override the machine-translated i18n_data/_mapui.json layer.
        "pref_title": "Вигляд",
        "pref_note": "Виберіть вигляд сайту. Ваш вибір збережеться на цьому "
                     "пристрої.",
        "pref_close": "Закрити",
        "pref_theme": "Тема",
        "pref_light": "Світла",
        "pref_dark": "Темна",
        "pref_style": "Стиль",
        "pref_style_objective": "Діловий",
        "pref_style_editorial": "Редакційний",
        "pref_style_product": "Продуктовий",
        "pref_style_atlas": "Атлас",
        "pref_accent": "Акцент",
        "pref_headline": "Шрифт заголовків",
        "pref_sans": "Без засічок",
        "pref_serif": "Із засічками",
        "pref_density": "Щільність",
        "pref_comfortable": "Комфортна",
        "pref_compact": "Компактна",
        "pref_header": "Заголовок сторінки",
        "pref_plain": "Простий",
        "pref_tint": "Відтінок",
        "pref_acc_cobalt": "Кобальтовий",
        "pref_acc_red": "Червоний",
        "pref_acc_teal": "Бірюзовий",
        "pref_acc_forest": "Лісовий",
        "pref_acc_amber": "Бурштиновий",
        "pref_acc_slate": "Графітовий",
        "hb_world": "Міста світу",
        "hb_since": "з 1940",
        "hb_title": "Середнє потепління великих міст світу від 1940 року, "
                    "з рівною вагою, обчислене за даними цього сайту",
    },
}


# --- additional languages, loaded from i18n_data/<code>.json ----------------
# The languages above are hand-authored; the rest are translated into JSON
# files (one per language) so the set can scale to the world's most-spoken
# tongues. Order below is the switcher order appended after the originals;
# ``dir`` is "rtl" for right-to-left scripts (Arabic, Urdu, Persian).
import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_EXTRA_LANGS = [
    ('zh', '中文', 'ltr'),
    ('hi', 'हिन्दी', 'ltr'),
    ('ar', 'العربية', 'rtl'),
    ('pt', 'Português', 'ltr'),
    ('bn', 'বাংলা', 'ltr'),
    ('ru', 'Русский', 'ltr'),
    ('id', 'Bahasa Indonesia', 'ltr'),
    ('ja', '日本語', 'ltr'),
    ('ur', 'اردو', 'rtl'),
    ('it', 'Italiano', 'ltr'),
    ('tr', 'Türkçe', 'ltr'),
    ('ko', '한국어', 'ltr'),
    ('fa', 'فارسی', 'rtl'),
    ('vi', 'Tiếng Việt', 'ltr'),
    ('nl', 'Nederlands', 'ltr'),
    ('sw', 'Kiswahili', 'ltr'),
    ('tl', 'Filipino', 'ltr'),
    ('th', 'ไทย', 'ltr'),
    ('ta', 'தமிழ்', 'ltr'),
    ('mr', 'मराठी', 'ltr'),
    ('te', 'తెలుగు', 'ltr'),
    ('ha', 'Hausa', 'ltr'),
    ('pa', 'ਪੰਜਾਬੀ', 'ltr'),
    ('my', 'မြန်မာ', 'ltr'),
    ('am', 'አማርኛ', 'ltr'),
    ('yo', 'Yorùbá', 'ltr'),
    ('af', 'Afrikaans', 'ltr'),
    ('ak', 'Akan', 'ltr'),
    ('gn', 'Avañe’ẽ', 'ltr'),
    ('ay', 'Aymara', 'ltr'),
    ('az', 'Azərbaycan', 'ltr'),
    ('ms', 'Bahasa Malaysia', 'ltr'),
    ('bm', 'Bamanakan', 'ltr'),
    ('su', 'Basa Sunda', 'ltr'),
    ('bs', 'Bosanski', 'ltr'),
    ('ca', 'Català', 'ltr'),
    ('ceb', 'Cebuano', 'ltr'),
    ('zh-TW', 'Chinese（Taiwan）', 'ltr'),
    ('sn', 'ChiShona', 'ltr'),
    ('co', 'Corsu', 'ltr'),
    ('cy', 'Cymraeg', 'ltr'),
    ('da', 'Dansk', 'ltr'),
    ('dv', 'Divehi', 'rtl'),
    ('et', 'Eesti', 'ltr'),
    ('eo', 'Esperanto', 'ltr'),
    ('eu', 'Euskara', 'ltr'),
    ('ee', 'Eʋegbe', 'ltr'),
    ('fy', 'Frysk', 'ltr'),
    ('ga', 'Gaeilge', 'ltr'),
    ('gl', 'Galego', 'ltr'),
    ('gom', 'Goan Konkani', 'ltr'),
    ('gd', 'Gàidhlig', 'ltr'),
    ('hmn', 'Hmong', 'ltr'),
    ('hr', 'Hrvatski', 'ltr'),
    ('ig', 'Igbo', 'ltr'),
    ('rw', 'Ikinyarwanda', 'ltr'),
    ('ilo', 'Ilokano', 'ltr'),
    ('xh', 'IsiXhosa', 'ltr'),
    ('zu', 'IsiZulu', 'ltr'),
    ('jv', 'Jawa', 'ltr'),
    ('ht', 'Kreyòl Ayisyen', 'ltr'),
    ('kri', 'Krio', 'ltr'),
    ('ku', 'Kurdî (kurmancî)', 'ltr'),
    ('lv', 'Latviešu', 'ltr'),
    ('lt', 'Lietuvių', 'ltr'),
    ('la', 'Lingua latina', 'ltr'),
    ('ln', 'Lingála', 'ltr'),
    ('lg', 'Luganda', 'ltr'),
    ('lb', 'Lëtzebuergesch', 'ltr'),
    ('hu', 'Magyar', 'ltr'),
    ('mg', 'Malagasy', 'ltr'),
    ('mt', 'Malti', 'ltr'),
    ('lus', 'Mizo', 'ltr'),
    ('mi', 'Māori', 'ltr'),
    ('no', 'Norsk', 'ltr'),
    ('ny', 'Nyanja', 'ltr'),
    ('om', 'Oromoo', 'ltr'),
    ('uz', 'O‘zbek', 'ltr'),
    ('ro', 'Română', 'ltr'),
    ('qu', 'Runasimi', 'ltr'),
    ('sm', 'Samoan', 'ltr'),
    ('st', 'Sesotho', 'ltr'),
    ('nso', 'Sesotho sa Leboa', 'ltr'),
    ('sq', 'Shqip', 'ltr'),
    ('sk', 'Slovenčina', 'ltr'),
    ('sl', 'Slovenščina', 'ltr'),
    ('so', 'Soomaali', 'ltr'),
    ('fi', 'Suomi', 'ltr'),
    ('sv', 'Svenska', 'ltr'),
    ('ts', 'Tsonga', 'ltr'),
    ('tk', 'Türkmen dili', 'ltr'),
    ('is', 'Íslenska', 'ltr'),
    ('cs', 'Čeština', 'ltr'),
    ('haw', 'ʻŌlelo Hawaiʻi', 'ltr'),
    ('el', 'Ελληνικά', 'ltr'),
    ('be', 'Беларуская', 'ltr'),
    ('bg', 'Български', 'ltr'),
    ('ky', 'Кыргызча', 'ltr'),
    ('mk', 'Македонски', 'ltr'),
    ('mn', 'Монгол', 'ltr'),
    ('sr', 'Српски', 'ltr'),
    ('tt', 'Татар', 'ltr'),
    ('tg', 'Тоҷикӣ', 'ltr'),
    ('kk', 'Қазақ тілі', 'ltr'),
    ('hy', 'Հայերեն', 'ltr'),
    ('yi', 'ייִדיש', 'rtl'),
    ('he', 'עברית', 'rtl'),
    ('ug', 'ئۇيغۇرچە', 'rtl'),
    ('sd', 'سنڌي', 'rtl'),
    ('ps', 'پښتو', 'rtl'),
    ('ckb', 'کوردیی ناوەندی', 'rtl'),
    ('doi', 'डोगरी', 'ltr'),
    ('ne', 'नेपाली', 'ltr'),
    ('bho', 'भोजपुरी', 'ltr'),
    ('mai', 'मैथिली', 'ltr'),
    ('sa', 'संस्कृत भाषा', 'ltr'),
    ('as', 'অসমীয়া', 'ltr'),
    ('gu', 'ગુજરાતી', 'ltr'),
    ('or', 'ଓଡ଼ିଆ', 'ltr'),
    ('kn', 'ಕನ್ನಡ', 'ltr'),
    ('ml', 'മലയാളം', 'ltr'),
    ('si', 'සිංහල', 'ltr'),
    ('lo', 'ລາວ', 'ltr'),
    ('ka', 'ქართული', 'ltr'),
    ('ti', 'ትግርኛ', 'ltr'),
    ('km', 'ខ្មែរ', 'ltr'),
]
_DIRECTIONS: dict[str, str] = {code: "ltr" for code in LANGUAGES}
_DATA_DIR = _Path(__file__).parent / "i18n_data"
for _code, _native, _dir in _EXTRA_LANGS:
    _path = _DATA_DIR / f"{_code}.json"
    if not _path.exists():
        continue  # translated file not added yet, language simply absent
    _block = _json.loads(_path.read_text(encoding="utf-8"))
    _block["html_lang"] = _code  # force the correct BCP-47 code
    TRANSLATIONS[_code] = _block
    LANG_NAMES[_code] = _native
    _DIRECTIONS[_code] = _dir
    if _code not in LANGUAGES:
        LANGUAGES.append(_code)

# Inject text direction into every table so templates set <html dir=...>.
for _code in TRANSLATIONS:
    TRANSLATIONS[_code]["dir"] = _DIRECTIONS.get(_code, "ltr")


def direction(lang: str) -> str:
    """Text direction ('ltr'/'rtl') for a language code."""
    return _DIRECTIONS.get(lang, "ltr")


# Supplementary map-UI strings (dot quick-view, base-map switcher, data-coverage
# overlay) that the map page looks up with tr.get(); English source + machine
# translations live in _mapui.json so they localize in every language. Layered
# under each dict below, so a curated string always wins.
try:
    _MAPUI: dict = _json.loads((_DATA_DIR / "_mapui.json").read_text(encoding="utf-8"))
except FileNotFoundError:
    _MAPUI = {}


def get(lang: str) -> dict:
    """Return the translation table for ``lang``.

    Every language is layered over English, so a key a translation has not filled
    in yet falls back to English instead of crashing the build. This lets new
    languages be added incrementally (translate the common strings first, refine
    the long-tail later)."""
    base = TRANSLATIONS.get(lang)
    if base is None:                       # unknown language -> default, still layered
        lang, base = DEFAULT_LANG, TRANSLATIONS[DEFAULT_LANG]
    d = dict(base) if lang == "en" else {**TRANSLATIONS["en"], **base}
    _mui = _MAPUI.get(lang) or _MAPUI.get("en")
    if _mui:
        for _k, _v in _mui.items():
            d.setdefault(_k, _v)
    return d
