"""Localized strings for the world warming-ranking table.

Same override pattern as :mod:`captions` / :mod:`deephist`: a per-language dict
plus :func:`overlay`, which merges the strings onto a language's table and
backfills any missing language from English. The country *name* column is filled
in the browser with ``Intl.DisplayNames`` from the ISO code, so only the section
chrome (title, intro, headers, search) is translated here.
"""

from __future__ import annotations

_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "rank_title": "World warming ranking",
        "rank_intro": "Every city ranked by how fast it is warming: the trend "
            "in °C per decade over 1940-2025. Search for yours.",
        "rank_city": "City",
        "rank_country": "Country",
        "rank_search": "Find a city…",
        "rank_empty": "No city matches that search.",
        "cstat_title": "How is your country warming?",
        "cstat_line": "{country}: {trend}°C per decade since 1940, faster than "
            "{pct}% of the world. Rank #{rank} of {total}.",
        "cstat_cool": "{country}: {trend}°C per decade since 1940. Cooling, "
            "against the global trend. Rank #{rank} of {total}.",
        "rank_more": "Show more",
        "rank_cities": "Cities",
        "rank_countries": "Countries",
    },
    "pl": {
        "rank_title": "Światowy ranking ocieplenia",
        "rank_intro": "Każde miasto uszeregowane według tempa ocieplenia: trend "
            "w °C na dekadę w latach 1940-2025. Wyszukaj swoje.",
        "rank_city": "Miasto",
        "rank_country": "Kraj",
        "rank_search": "Znajdź miasto…",
        "rank_empty": "Żadne miasto nie pasuje do wyszukiwania.",
        "cstat_title": "Jak ociepla się twój kraj?",
        "cstat_line": "{country}: {trend}°C na dekadę od 1940 roku, szybciej niż "
            "{pct}% świata. Miejsce #{rank} z {total}.",
        "cstat_cool": "{country}: {trend}°C na dekadę od 1940 roku. Chłodzenie, "
            "wbrew globalnemu trendowi. Miejsce #{rank} z {total}.",
        "rank_legend": "W każdym wierszu: całkowite ocieplenie od 1940 roku oraz "
            "ile razy szybciej niż średnia miast świata dane miejsce się ociepla "
            "(2x = dwa razy szybciej).",
        "rank_people": "ludzi",
        "rank_more": "Pokaż więcej",
        "rank_cities": "Miasta",
        "rank_countries": "Kraje",
    },
    "de": {
        "rank_title": "Weltweite Erwärmungsrangliste",
        "rank_intro": "Jede Stadt nach ihrem Erwärmungstempo geordnet: der Trend "
            "in °C pro Jahrzehnt von 1940-2025. Suchen Sie Ihre.",
        "rank_city": "Stadt",
        "rank_country": "Land",
        "rank_search": "Stadt suchen…",
        "rank_empty": "Keine Stadt passt zu dieser Suche.",
        "cstat_title": "Wie stark erwärmt sich Ihr Land?",
        "cstat_line": "{country}: {trend}°C pro Jahrzehnt seit 1940, schneller "
            "als {pct}% der Welt. Platz #{rank} von {total}.",
        "rank_more": "Mehr anzeigen",
        "rank_cities": "Städte",
        "rank_countries": "Länder",
    },
    "fr": {
        "rank_title": "Classement mondial du réchauffement",
        "rank_intro": "Chaque ville classée selon sa vitesse de réchauffement : "
            "la tendance en °C par décennie sur 1940-2025. Cherchez la vôtre.",
        "rank_city": "Ville",
        "rank_country": "Pays",
        "rank_search": "Rechercher une ville…",
        "rank_empty": "Aucune ville ne correspond à cette recherche.",
        "cstat_title": "Comment se réchauffe votre pays ?",
        "cstat_line": "{country} : {trend}°C par décennie depuis 1940, plus vite "
            "que {pct}% du monde. Rang #{rank} sur {total}.",
        "rank_more": "Voir plus",
        "rank_cities": "Villes",
        "rank_countries": "Pays",
    },
    "es": {
        "rank_title": "Ranking mundial de calentamiento",
        "rank_intro": "Cada ciudad clasificada por su velocidad de calentamiento: "
            "la tendencia en °C por década entre 1940-2025. Busca la tuya.",
        "rank_city": "Ciudad",
        "rank_country": "País",
        "rank_search": "Buscar una ciudad…",
        "rank_empty": "Ninguna ciudad coincide con esa búsqueda.",
        "cstat_title": "¿Cómo se calienta tu país?",
        "cstat_line": "{country}: {trend}°C por década desde 1940, más rápido que "
            "el {pct}% del mundo. Puesto #{rank} de {total}.",
        "rank_more": "Ver más",
        "rank_cities": "Ciudades",
        "rank_countries": "Países",
    },
    "uk": {
        "rank_title": "Світовий рейтинг потепління",
        "rank_intro": "Кожне місто впорядковане за швидкістю потепління: тренд "
            "у °C за десятиліття протягом 1940-2025. Знайдіть своє.",
        "rank_city": "Місто",
        "rank_country": "Країна",
        "rank_search": "Знайти місто…",
        "rank_empty": "Жодне місто не відповідає цьому запиту.",
        "cstat_title": "Як нагрівається ваша країна?",
        "cstat_line": "{country}: {trend}°C за десятиліття від 1940 року, швидше "
            "за {pct}% світу. Місце #{rank} з {total}.",
        "rank_more": "Показати більше",
        "rank_cities": "Міста",
        "rank_countries": "Країни",
    },
    "ru": {
        "rank_title": "Мировой рейтинг потепления",
        "rank_intro": "Каждый город упорядочен по скорости потепления: тренд "
            "в °C за десятилетие за 1940-2025. Найдите свой.",
        "rank_city": "Город",
        "rank_country": "Страна",
        "rank_search": "Найти город…",
        "rank_empty": "Ни один город не соответствует этому запросу.",
        "cstat_title": "Как теплеет ваша страна?",
        "cstat_line": "{country}: {trend}°C за десятилетие с 1940 года, быстрее, "
            "чем {pct}% мира. Место #{rank} из {total}.",
        "rank_more": "Показать больше",
        "rank_cities": "Города",
        "rank_countries": "Страны",
    },
    "it": {
        "rank_title": "Classifica mondiale del riscaldamento",
        "rank_intro": "Ogni città ordinata per velocità di riscaldamento: la "
            "tendenza in °C per decennio nel 1940-2025. Cerca la tua.",
        "rank_city": "Città",
        "rank_country": "Paese",
        "rank_search": "Cerca una città…",
        "rank_empty": "Nessuna città corrisponde a questa ricerca.",
        "cstat_title": "Come si sta riscaldando il tuo paese?",
        "cstat_line": "{country}: {trend}°C per decennio dal 1940, più veloce del "
            "{pct}% del mondo. Posizione #{rank} su {total}.",
        "rank_more": "Mostra altro",
        "rank_cities": "Città",
        "rank_countries": "Paesi",
    },
    "pt": {
        "rank_title": "Ranking mundial de aquecimento",
        "rank_intro": "Cada cidade classificada pela velocidade de aquecimento: a "
            "tendência em °C por década entre 1940-2025. Procure a sua.",
        "rank_city": "Cidade",
        "rank_country": "País",
        "rank_search": "Procurar uma cidade…",
        "rank_empty": "Nenhuma cidade corresponde a essa busca.",
        "cstat_title": "Como o seu país está a aquecer?",
        "cstat_line": "{country}: {trend}°C por década desde 1940, mais rápido que "
            "{pct}% do mundo. Posição #{rank} de {total}.",
        "rank_more": "Ver mais",
        "rank_cities": "Cidades",
        "rank_countries": "Países",
    },
    "nl": {
        "rank_title": "Wereldwijde opwarmingsranglijst",
        "rank_intro": "Elke stad gerangschikt op opwarmingssnelheid: de trend "
            "in °C per decennium over 1940-2025. Zoek de jouwe.",
        "rank_city": "Stad",
        "rank_country": "Land",
        "rank_search": "Zoek een stad…",
        "rank_empty": "Geen stad komt overeen met die zoekopdracht.",
        "cstat_title": "Hoe snel warmt jouw land op?",
        "cstat_line": "{country}: {trend}°C per decennium sinds 1940, sneller dan "
            "{pct}% van de wereld. Plaats #{rank} van {total}.",
        "rank_more": "Meer tonen",
        "rank_cities": "Steden",
        "rank_countries": "Landen",
    },
    "tr": {
        "rank_title": "Dünya ısınma sıralaması",
        "rank_intro": "Her şehir ısınma hızına göre sıralandı: 1940-2025 arasında "
            "on yıl başına °C cinsinden eğilim. Kendinizinkini arayın.",
        "rank_city": "Şehir",
        "rank_country": "Ülke",
        "rank_search": "Bir şehir bul…",
        "rank_empty": "Bu aramayla eşleşen şehir yok.",
        "cstat_title": "Ülkeniz nasıl ısınıyor?",
        "cstat_line": "{country}: 1940'tan beri on yılda {trend}°C, dünyanın "
            "{pct}%'inden daha hızlı. Sıralama #{rank}/{total}.",
        "rank_more": "Daha fazla göster",
        "rank_cities": "Şehirler",
        "rank_countries": "Ülkeler",
    },
    "id": {
        "rank_title": "Peringkat pemanasan dunia",
        "rank_intro": "Setiap kota diperingkat menurut kecepatan pemanasannya: "
            "tren dalam °C per dekade sepanjang 1940-2025. Cari milik Anda.",
        "rank_city": "Kota",
        "rank_country": "Negara",
        "rank_search": "Cari kota…",
        "rank_empty": "Tidak ada kota yang cocok dengan pencarian itu.",
        "cstat_title": "Seberapa cepat negara Anda memanas?",
        "cstat_line": "{country}: {trend}°C per dekade sejak 1940, lebih cepat dari "
            "{pct}% dunia. Peringkat #{rank} dari {total}.",
        "rank_more": "Tampilkan lainnya",
        "rank_cities": "Kota",
        "rank_countries": "Negara",
    },
    "vi": {
        "rank_title": "Xếp hạng nóng lên toàn cầu",
        "rank_intro": "Mỗi thành phố được xếp hạng theo tốc độ nóng lên: xu hướng "
            "tính bằng °C mỗi thập kỷ trong giai đoạn 1940-2025. Tìm thành phố của bạn.",
        "rank_city": "Thành phố",
        "rank_country": "Quốc gia",
        "rank_search": "Tìm một thành phố…",
        "rank_empty": "Không có thành phố nào khớp với tìm kiếm đó.",
        "cstat_title": "Đất nước bạn đang nóng lên nhanh thế nào?",
        "cstat_line": "{country}: {trend}°C mỗi thập kỷ kể từ 1940, nhanh hơn "
            "{pct}% thế giới. Hạng #{rank} trên {total}.",
        "rank_more": "Xem thêm",
        "rank_cities": "Thành phố",
        "rank_countries": "Quốc gia",
    },
    "zh": {
        "rank_title": "全球变暖排名",
        "rank_intro": "每座城市按变暖速度排名：1940-2025 年间每十年的 °C 趋势。"
            "搜索你的城市。",
        "rank_city": "城市",
        "rank_country": "国家",
        "rank_search": "查找城市…",
        "rank_empty": "没有城市与该搜索匹配。",
        "cstat_title": "你的国家变暖有多快？",
        "cstat_line": "{country}：自1940年以来每十年 {trend}°C，比全球 {pct}% 更快。"
            "排名 #{rank}/{total}。",
        "rank_more": "显示更多",
        "rank_cities": "城市",
        "rank_countries": "国家",
    },
    "ja": {
        "rank_title": "世界の温暖化ランキング",
        "rank_intro": "各都市を温暖化の速さで順位付け：1940-2025年の10年あたりの "
            "°C の傾向。あなたの都市を検索。",
        "rank_city": "都市",
        "rank_country": "国",
        "rank_search": "都市を検索…",
        "rank_empty": "その検索に一致する都市はありません。",
        "cstat_title": "あなたの国はどれだけ温暖化している？",
        "cstat_line": "{country}：1940年以降10年あたり {trend}°C、世界の {pct}% より速い。"
            "順位 #{rank}/{total}。",
        "rank_more": "もっと見る",
        "rank_cities": "都市",
        "rank_countries": "国",
    },
    "ko": {
        "rank_title": "세계 온난화 순위",
        "rank_intro": "모든 도시를 온난화 속도로 순위를 매김: 1940-2025년 10년당 "
            "°C 추세. 당신의 도시를 검색하세요.",
        "rank_city": "도시",
        "rank_country": "국가",
        "rank_search": "도시 찾기…",
        "rank_empty": "검색과 일치하는 도시가 없습니다.",
        "cstat_title": "당신의 나라는 얼마나 빠르게 더워지고 있나요?",
        "cstat_line": "{country}: 1940년 이후 10년당 {trend}°C, 세계 {pct}%보다 빠름. "
            "순위 #{rank}/{total}.",
        "rank_more": "더 보기",
        "rank_cities": "도시",
        "rank_countries": "국가",
    },
    "hi": {
        "rank_title": "विश्व तापन रैंकिंग",
        "rank_intro": "हर शहर को उसके गर्म होने की गति के अनुसार क्रमबद्ध: "
            "1940-2025 में प्रति दशक °C में रुझान। अपना शहर खोजें।",
        "rank_city": "शहर",
        "rank_country": "देश",
        "rank_search": "शहर खोजें…",
        "rank_empty": "इस खोज से कोई शहर मेल नहीं खाता।",
        "cstat_title": "आपका देश कितनी तेज़ी से गर्म हो रहा है?",
        "cstat_line": "{country}: 1940 से प्रति दशक {trend}°C, दुनिया के {pct}% से "
            "तेज़। रैंक #{rank}/{total}।",
        "rank_more": "और दिखाएं",
        "rank_cities": "शहर",
        "rank_countries": "देश",
    },
    "bn": {
        "rank_title": "বিশ্ব উষ্ণায়ন র‍্যাঙ্কিং",
        "rank_intro": "প্রতিটি শহর তার উষ্ণ হওয়ার গতি অনুসারে সাজানো: 1940-2025 "
            "জুড়ে প্রতি দশকে °C-এ প্রবণতা। আপনারটি খুঁজুন।",
        "rank_city": "শহর",
        "rank_country": "দেশ",
        "rank_search": "একটি শহর খুঁজুন…",
        "rank_empty": "এই অনুসন্ধানের সাথে কোনো শহর মেলে না।",
        "cstat_title": "আপনার দেশ কত দ্রুত উষ্ণ হচ্ছে?",
        "cstat_line": "{country}: 1940 সাল থেকে প্রতি দশকে {trend}°C, বিশ্বের {pct}% "
            "এর চেয়ে দ্রুত। র‍্যাঙ্ক #{rank}/{total}।",
        "rank_more": "আরও দেখান",
        "rank_cities": "শহর",
        "rank_countries": "দেশ",
    },
    "ar": {
        "rank_title": "ترتيب الاحترار العالمي",
        "rank_intro": "كل مدينة مرتبة حسب سرعة احترارها: الاتجاه بوحدة °C لكل عقد "
            "خلال 1940-2025. ابحث عن مدينتك.",
        "rank_city": "المدينة",
        "rank_country": "الدولة",
        "rank_search": "ابحث عن مدينة…",
        "rank_empty": "لا توجد مدينة تطابق هذا البحث.",
        "cstat_title": "كيف يزداد بلدك احترارًا؟",
        "cstat_line": "{country}: {trend}°C لكل عقد منذ 1940، أسرع من {pct}% من "
            "العالم. المرتبة #{rank} من {total}.",
        "rank_more": "عرض المزيد",
        "rank_cities": "المدن",
        "rank_countries": "الدول",
    },
    "ur": {
        "rank_title": "عالمی حدت کی درجہ بندی",
        "rank_intro": "ہر شہر اس کی گرمی کی رفتار کے مطابق درجہ بند: 1940-2025 کے "
            "دوران فی دہائی °C میں رجحان۔ اپنا شہر تلاش کریں۔",
        "rank_city": "شہر",
        "rank_country": "ملک",
        "rank_search": "شہر تلاش کریں…",
        "rank_empty": "اس تلاش سے کوئی شہر مماثل نہیں۔",
        "cstat_title": "آپ کا ملک کتنی تیزی سے گرم ہو رہا ہے؟",
        "cstat_line": "{country}: 1940 سے فی دہائی {trend}°C، دنیا کے {pct}% سے تیز۔ "
            "درجہ #{rank} از {total}۔",
        "rank_more": "مزید دکھائیں",
        "rank_cities": "شہر",
        "rank_countries": "ممالک",
    },
    "fa": {
        "rank_title": "رتبه‌بندی گرمایش جهانی",
        "rank_intro": "هر شهر بر اساس سرعت گرم شدنش رتبه‌بندی شده: روند بر حسب °C "
            "در هر دهه طی 1940-2025. شهر خود را جستجو کنید.",
        "rank_city": "شهر",
        "rank_country": "کشور",
        "rank_search": "جستجوی شهر…",
        "rank_empty": "هیچ شهری با این جستجو مطابقت ندارد.",
        "cstat_title": "کشور شما چقدر گرم می‌شود؟",
        "cstat_line": "{country}: {trend}°C در هر دهه از سال 1940، سریع‌تر از {pct}% "
            "جهان. رتبه #{rank} از {total}.",
        "rank_more": "نمایش بیشتر",
        "rank_cities": "شهرها",
        "rank_countries": "کشورها",
    },
}


# Why the ranking lists fewer cities than the map's "cities with data": a place
# is ranked only if it has >=10 years of records and resolves to a country, so
# sparse or country-less points (oceans, reference sites) are held out.
_NOTE = {
    "en": "Only cities with 10+ years of records and a known country are ranked, "
        "so a few places with sparse data are not listed yet.",
    "pl": "W rankingu są tylko miasta z co najmniej 10 latami danych i znanym "
        "krajem, więc kilka miejsc z ubogimi danymi jeszcze się nie pojawia.",
    "de": "Gewertet werden nur Städte mit mindestens 10 Jahren Daten und bekanntem "
        "Land; einige Orte mit spärlichen Daten fehlen daher noch.",
    "fr": "Seules les villes avec au moins 10 ans de données et un pays connu sont "
        "classées ; quelques lieux aux données rares ne figurent pas encore.",
    "es": "Solo se clasifican las ciudades con 10 o más años de datos y un país "
        "conocido, por lo que algunos lugares con datos escasos aún no aparecen.",
    "uk": "У рейтингу лише міста, що мають щонайменше 10 років даних і відому "
        "країну, тож кілька місць із бідними даними ще не показані.",
    "ru": "В рейтинг входят только города с не менее чем 10 годами данных и "
        "известной страной, поэтому несколько мест со скудными данными пока нет.",
    "it": "In classifica solo le città con almeno 10 anni di dati e un paese noto, "
        "quindi alcuni luoghi con dati scarsi non sono ancora elencati.",
    "pt": "Só entram no ranking cidades com 10 ou mais anos de dados e um país "
        "conhecido, por isso alguns locais com dados escassos ainda não aparecem.",
    "nl": "Alleen steden met minstens 10 jaar gegevens en een bekend land worden "
        "gerangschikt; enkele plaatsen met weinig gegevens ontbreken nog.",
    "tr": "Sıralamaya yalnızca en az 10 yıllık verisi ve bilinen bir ülkesi olan "
        "şehirler girer; verisi az olan birkaç yer henüz listede değil.",
    "id": "Hanya kota dengan data 10 tahun atau lebih dan negara yang diketahui "
        "yang masuk peringkat, jadi beberapa tempat berdata sedikit belum tampil.",
    "vi": "Chỉ các thành phố có từ 10 năm dữ liệu trở lên và thuộc một quốc gia xác "
        "định mới được xếp hạng, nên vài nơi ít dữ liệu chưa xuất hiện.",
    "zh": "仅收录拥有 10 年以上数据且国家明确的城市，因此少数数据稀少的地点暂未列出。",
    "ja": "ランキングは10年以上のデータと判明した国を持つ都市のみが対象のため、"
        "データの少ない一部の地点はまだ表示されません。",
    "ko": "10년 이상의 데이터와 확인된 국가가 있는 도시만 순위에 포함되므로, "
        "데이터가 적은 일부 지역은 아직 표시되지 않습니다.",
    "hi": "केवल 10 या अधिक वर्षों के डेटा और ज्ञात देश वाले शहरों को रैंक किया जाता है, "
        "इसलिए कम डेटा वाले कुछ स्थान अभी सूची में नहीं हैं।",
    "bn": "শুধুমাত্র 10 বছর বা তার বেশি তথ্য এবং পরিচিত দেশ থাকা শহরগুলিই তালিকাভুক্ত হয়, "
        "তাই কম তথ্যের কিছু স্থান এখনও দেখা যাচ্ছে না।",
    "ar": "لا تُصنَّف سوى المدن التي لديها 10 سنوات من البيانات على الأقل وبلد معروف، "
        "لذا لا تظهر بعد بضعة أماكن ذات بيانات قليلة.",
    "ur": "درجہ بندی میں صرف وہ شہر شامل ہیں جن کے پاس کم از کم 10 سال کا ڈیٹا اور "
        "معلوم ملک ہو، اس لیے کم ڈیٹا والے چند مقامات ابھی درج نہیں۔",
    "fa": "فقط شهرهایی که دست‌کم 10 سال داده و کشوری مشخص دارند رتبه‌بندی می‌شوند، "
        "بنابراین چند مکان با داده‌های اندک هنوز فهرست نشده‌اند.",
}


import extra_i18n  # noqa: E402
extra_i18n.fill(_TEXT, "ranktext")
extra_i18n.fill_flat(_NOTE, "ranktext_note")


def overlay(tr: dict, lang: str) -> dict:
    """Return ``tr`` with the ranking strings merged in (English backfills any
    language not yet listed)."""
    keys = {**_TEXT["en"], **_TEXT.get(lang, {})}
    keys["rank_note"] = _NOTE.get(lang, _NOTE["en"])
    return {**tr, **keys}
