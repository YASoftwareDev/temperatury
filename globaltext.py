"""Localised strings specific to the global / regional climate dashboard.

Kept out of the big ``i18n.TRANSLATIONS`` table so the dashboard's ~12 extra
keys live in one reviewable place. :func:`overlay` merges a language's entries
onto its normal ``tr`` dict; the per-city chart keys the dashboard reuses
(``anomaly_ylabel``, ``stripes_cbar``, ``anom_heatmap_cbar``, ``year`` …) come
from the base ``tr`` unchanged, so only the genuinely new strings live here.

Keys:
  region_*          : climate-zone names (also the comparison-chart legend).
  global_heading    : page H1.        global_intro: subtitle ({n} = city count).
  global_choose     : zone <select> label.
  comparison_title / comparison_cap: the headline "who warms fastest" chart.
"""

from __future__ import annotations

# language -> {key: template}. English is the fallback for any missing language.
_TEXT: dict[str, dict] = {
    "en": {
        "region_world": "World",
        "region_tropical": "Tropics",
        "region_n_subtropical": "Northern Subtropics",
        "region_n_temperate": "Northern Temperate",
        "region_n_boreal": "Northern Boreal & Arctic",
        "region_s_subtropical": "Southern Subtropics",
        "region_s_temperate": "Southern Temperate",
        "global_heading": "Global & regional climate dashboard",
        "global_intro": "The same charts, aggregated worldwide and by latitudinal "
            "climate zone across {n} cities. Values are temperature anomalies: each city versus its own 1961-1990 normal, then averaged.",
        "global_choose": "Climate zone",
        "comparison_title": "How fast each climate zone is warming",
        "comparison_cap": "Each zone's smoothed annual temperature anomaly versus "
            "its 1961-1990 normal. A steeper climb means faster warming.",
    },
    "pl": {
        "region_world": "Świat",
        "region_tropical": "Strefa międzyzwrotnikowa",
        "region_n_subtropical": "Północne subtropiki",
        "region_n_temperate": "Północna strefa umiarkowana",
        "region_n_boreal": "Północna strefa borealna i Arktyka",
        "region_s_subtropical": "Południowe subtropiki",
        "region_s_temperate": "Południowa strefa umiarkowana",
        "global_heading": "Globalny i regionalny panel klimatyczny",
        "global_intro": "Te same wykresy, zagregowane globalnie i według stref "
            "klimatycznych szerokości geograficznej dla {n} miast. Wartości to "
            "anomalie temperatury: każde miasto względem własnej normy 1961-1990, "
            "następnie uśrednione.",
        "global_choose": "Strefa klimatyczna",
        "comparison_title": "Jak szybko ociepla się każda strefa klimatyczna",
        "comparison_cap": "Wygładzona roczna anomalia temperatury każdej strefy "
            "względem normy 1961-1990. Im bardziej stromy wzrost, tym szybsze "
            "ocieplenie.",
    },
    "de": {
        "region_world": "Welt",
        "region_tropical": "Tropen",
        "region_n_subtropical": "Nördliche Subtropen",
        "region_n_temperate": "Nördliche gemäßigte Zone",
        "region_n_boreal": "Nördliche boreale Zone & Arktis",
        "region_s_subtropical": "Südliche Subtropen",
        "region_s_temperate": "Südliche gemäßigte Zone",
        "global_heading": "Globales & regionales Klima-Dashboard",
        "global_intro": "Dieselben Diagramme, weltweit und nach Klimazonen der "
            "Breitengrade über {n} Städte aggregiert. Werte sind "
            "Temperaturanomalien: jede Stadt gegenüber ihrem eigenen Normalwert "
            "1961-1990, dann gemittelt.",
        "global_choose": "Klimazone",
        "comparison_title": "Wie schnell sich jede Klimazone erwärmt",
        "comparison_cap": "Geglättete jährliche Temperaturanomalie jeder Zone "
            "gegenüber dem Normalwert 1961-1990. Ein steilerer Anstieg bedeutet "
            "schnellere Erwärmung.",
    },
    "fr": {
        "region_world": "Monde",
        "region_tropical": "Tropiques",
        "region_n_subtropical": "Subtropiques nord",
        "region_n_temperate": "Zone tempérée nord",
        "region_n_boreal": "Zone boréale nord et Arctique",
        "region_s_subtropical": "Subtropiques sud",
        "region_s_temperate": "Zone tempérée sud",
        "global_heading": "Tableau de bord climatique mondial et régional",
        "global_intro": "Les mêmes graphiques, agrégés à l'échelle mondiale et par "
            "zone climatique de latitude sur {n} villes. Les valeurs sont des "
            "anomalies de température : chaque ville par rapport à sa propre "
            "normale 1961-1990, puis moyennées.",
        "global_choose": "Zone climatique",
        "comparison_title": "À quelle vitesse chaque zone climatique se réchauffe",
        "comparison_cap": "Anomalie annuelle lissée de chaque zone par rapport à "
            "la normale 1961-1990. Plus la hausse est forte, plus le réchauffement "
            "est rapide.",
    },
    "es": {
        "region_world": "Mundo",
        "region_tropical": "Trópicos",
        "region_n_subtropical": "Subtrópicos del norte",
        "region_n_temperate": "Templada del norte",
        "region_n_boreal": "Boreal del norte y Ártico",
        "region_s_subtropical": "Subtrópicos del sur",
        "region_s_temperate": "Templada del sur",
        "global_heading": "Panel climático mundial y regional",
        "global_intro": "Los mismos gráficos, agregados a nivel mundial y por zona "
            "climática de latitud en {n} ciudades. Los valores son anomalías de "
            "temperatura: cada ciudad frente a su propia normal de 1961-1990, y "
            "luego promediadas.",
        "global_choose": "Zona climática",
        "comparison_title": "Qué tan rápido se calienta cada zona climática",
        "comparison_cap": "Anomalía anual suavizada de cada zona frente a su normal "
            "de 1961-1990. Cuanto más pronunciada es la subida, más rápido es el "
            "calentamiento.",
    },
    "uk": {
        "region_world": "Світ",
        "region_tropical": "Тропіки",
        "region_n_subtropical": "Північні субтропіки",
        "region_n_temperate": "Північна помірна зона",
        "region_n_boreal": "Північна бореальна зона та Арктика",
        "region_s_subtropical": "Південні субтропіки",
        "region_s_temperate": "Південна помірна зона",
        "global_heading": "Глобальна та регіональна кліматична панель",
        "global_intro": "Ті самі графіки, агреговані глобально та за широтними "
            "кліматичними зонами по {n} містах. Значення це аномалії температури: "
            "кожне місто відносно власної норми 1961-1990, потім усереднені.",
        "global_choose": "Кліматична зона",
        "comparison_title": "Наскільки швидко теплішає кожна кліматична зона",
        "comparison_cap": "Згладжена річна аномалія температури кожної зони "
            "відносно норми 1961-1990. Крутіший підйом означає швидше потепління.",
    },
    "ru": {
        "region_world": "Мир",
        "region_tropical": "Тропики",
        "region_n_subtropical": "Северные субтропики",
        "region_n_temperate": "Северный умеренный пояс",
        "region_n_boreal": "Северный бореальный пояс и Арктика",
        "region_s_subtropical": "Южные субтропики",
        "region_s_temperate": "Южный умеренный пояс",
        "global_heading": "Глобальная и региональная климатическая панель",
        "global_intro": "Те же графики, агрегированные глобально и по широтным "
            "климатическим зонам по {n} городам. Значения это аномалии температуры: "
            "каждый город относительно своей нормы 1961-1990, затем усреднённые.",
        "global_choose": "Климатическая зона",
        "comparison_title": "Насколько быстро теплеет каждая климатическая зона",
        "comparison_cap": "Сглаженная годовая аномалия температуры каждой зоны "
            "относительно нормы 1961-1990. Чем круче рост, тем быстрее потепление.",
    },
    "it": {
        "region_world": "Mondo",
        "region_tropical": "Tropici",
        "region_n_subtropical": "Subtropici settentrionali",
        "region_n_temperate": "Temperata settentrionale",
        "region_n_boreal": "Boreale settentrionale e Artico",
        "region_s_subtropical": "Subtropici meridionali",
        "region_s_temperate": "Temperata meridionale",
        "global_heading": "Dashboard climatica globale e regionale",
        "global_intro": "Gli stessi grafici, aggregati a livello mondiale e per "
            "zona climatica di latitudine su {n} città. I valori sono anomalie di "
            "temperatura: ogni città rispetto alla propria norma 1961-1990, poi "
            "mediate.",
        "global_choose": "Zona climatica",
        "comparison_title": "Quanto velocemente si riscalda ogni zona climatica",
        "comparison_cap": "Anomalia annuale livellata di ogni zona rispetto alla "
            "norma 1961-1990. Una salita più ripida indica un riscaldamento più "
            "rapido.",
    },
    "pt": {
        "region_world": "Mundo",
        "region_tropical": "Trópicos",
        "region_n_subtropical": "Subtrópicos do norte",
        "region_n_temperate": "Temperada do norte",
        "region_n_boreal": "Boreal do norte e Ártico",
        "region_s_subtropical": "Subtrópicos do sul",
        "region_s_temperate": "Temperada do sul",
        "global_heading": "Painel climático global e regional",
        "global_intro": "Os mesmos gráficos, agregados a nível mundial e por zona "
            "climática de latitude em {n} cidades. Os valores são anomalias de "
            "temperatura: cada cidade face à sua própria normal de 1961-1990, "
            "depois calculada a média.",
        "global_choose": "Zona climática",
        "comparison_title": "A que velocidade cada zona climática está a aquecer",
        "comparison_cap": "Anomalia anual suavizada de cada zona face à sua normal "
            "de 1961-1990. Uma subida mais acentuada significa aquecimento mais "
            "rápido.",
    },
    "nl": {
        "region_world": "Wereld",
        "region_tropical": "Tropen",
        "region_n_subtropical": "Noordelijke subtropen",
        "region_n_temperate": "Noordelijk gematigd",
        "region_n_boreal": "Noordelijk boreaal & Arctisch",
        "region_s_subtropical": "Zuidelijke subtropen",
        "region_s_temperate": "Zuidelijk gematigd",
        "global_heading": "Mondiaal & regionaal klimaatdashboard",
        "global_intro": "Dezelfde grafieken, geaggregeerd wereldwijd en per "
            "klimaatzone op breedtegraad over {n} steden. Waarden zijn "
            "temperatuuranomalieën: elke stad ten opzichte van zijn eigen normaal "
            "1961-1990, daarna gemiddeld.",
        "global_choose": "Klimaatzone",
        "comparison_title": "Hoe snel elke klimaatzone opwarmt",
        "comparison_cap": "Gladgestreken jaarlijkse temperatuuranomalie van elke "
            "zone ten opzichte van de normaal 1961-1990. Een steilere stijging "
            "betekent snellere opwarming.",
    },
    "tr": {
        "region_world": "Dünya",
        "region_tropical": "Tropikler",
        "region_n_subtropical": "Kuzey Subtropikal",
        "region_n_temperate": "Kuzey Ilıman",
        "region_n_boreal": "Kuzey Boreal ve Arktik",
        "region_s_subtropical": "Güney Subtropikal",
        "region_s_temperate": "Güney Ilıman",
        "global_heading": "Küresel ve bölgesel iklim panosu",
        "global_intro": "Aynı grafikler, {n} şehir genelinde dünya çapında ve enlem "
            "iklim kuşağına göre toplulaştırıldı. Değerler sıcaklık anomalileridir: her şehir kendi 1961-1990 normaline göre, sonra ortalaması alınır.",
        "global_choose": "İklim kuşağı",
        "comparison_title": "Her iklim kuşağı ne kadar hızlı ısınıyor",
        "comparison_cap": "Her kuşağın 1961-1990 normaline göre düzleştirilmiş "
            "yıllık sıcaklık anomalisi. Daha dik bir yükseliş daha hızlı ısınma "
            "demektir.",
    },
    "id": {
        "region_world": "Dunia",
        "region_tropical": "Tropis",
        "region_n_subtropical": "Subtropis Utara",
        "region_n_temperate": "Sedang Utara",
        "region_n_boreal": "Boreal Utara & Arktik",
        "region_s_subtropical": "Subtropis Selatan",
        "region_s_temperate": "Sedang Selatan",
        "global_heading": "Dasbor iklim global & regional",
        "global_intro": "Grafik yang sama, diagregasi secara global dan menurut "
            "zona iklim lintang di {n} kota. Nilai adalah anomali suhu: setiap "
            "kota terhadap normal 1961-1990-nya sendiri, lalu dirata-ratakan.",
        "global_choose": "Zona iklim",
        "comparison_title": "Seberapa cepat setiap zona iklim menghangat",
        "comparison_cap": "Anomali suhu tahunan yang dihaluskan untuk setiap zona "
            "terhadap normal 1961-1990. Kenaikan yang lebih curam berarti "
            "pemanasan lebih cepat.",
    },
    "vi": {
        "region_world": "Thế giới",
        "region_tropical": "Nhiệt đới",
        "region_n_subtropical": "Cận nhiệt Bắc",
        "region_n_temperate": "Ôn đới Bắc",
        "region_n_boreal": "Hàn đới Bắc & Bắc Cực",
        "region_s_subtropical": "Cận nhiệt Nam",
        "region_s_temperate": "Ôn đới Nam",
        "global_heading": "Bảng điều khiển khí hậu toàn cầu & khu vực",
        "global_intro": "Cùng các biểu đồ, tổng hợp trên toàn cầu và theo đới khí "
            "hậu vĩ độ trên {n} thành phố. Giá trị là dị thường nhiệt độ: mỗi "
            "thành phố so với chuẩn 1961-1990 của chính nó, rồi lấy trung bình.",
        "global_choose": "Đới khí hậu",
        "comparison_title": "Mỗi đới khí hậu đang nóng lên nhanh thế nào",
        "comparison_cap": "Dị thường nhiệt độ hằng năm đã làm mượt của mỗi đới so "
            "với chuẩn 1961-1990. Độ dốc càng lớn thì nóng lên càng nhanh.",
    },
    "zh": {
        "region_world": "全球",
        "region_tropical": "热带",
        "region_n_subtropical": "北副热带",
        "region_n_temperate": "北温带",
        "region_n_boreal": "北方针叶林带与北极",
        "region_s_subtropical": "南副热带",
        "region_s_temperate": "南温带",
        "global_heading": "全球与区域气候仪表板",
        "global_intro": "相同的图表，按纬度气候带和全球对 {n} 个城市进行汇总。"
            "数值为温度距平：每个城市相对于其自身 1961-1990 年平均值，然后取平均。",
        "global_choose": "气候带",
        "comparison_title": "各气候带升温速度对比",
        "comparison_cap": "各气候带相对于 1961-1990 年常态的年度温度距平（平滑）。"
            "上升越陡，升温越快。",
    },
    "ja": {
        "region_world": "世界",
        "region_tropical": "熱帯",
        "region_n_subtropical": "北亜熱帯",
        "region_n_temperate": "北温帯",
        "region_n_boreal": "北方林帯・北極",
        "region_s_subtropical": "南亜熱帯",
        "region_s_temperate": "南温帯",
        "global_heading": "世界・地域の気候ダッシュボード",
        "global_intro": "同じグラフを、緯度の気候帯別および世界全体で {n} 都市について"
            "集計。値は気温偏差で、各都市を自身の1961〜1990年平年値と比較し平均した"
            "ものです。",
        "global_choose": "気候帯",
        "comparison_title": "各気候帯の温暖化の速さ",
        "comparison_cap": "各帯の1961〜1990年平年値に対する年平均気温偏差（平滑化）。"
            "傾きが急なほど温暖化が速い。",
    },
    "ko": {
        "region_world": "세계",
        "region_tropical": "열대",
        "region_n_subtropical": "북반구 아열대",
        "region_n_temperate": "북반구 온대",
        "region_n_boreal": "북반구 아한대·북극",
        "region_s_subtropical": "남반구 아열대",
        "region_s_temperate": "남반구 온대",
        "global_heading": "전 세계·지역 기후 대시보드",
        "global_intro": "동일한 차트를 위도 기후대별과 전 세계로 {n}개 도시에 대해 "
            "집계했습니다. 값은 기온 편차로, 각 도시를 자체 1961-1990년 평년값과 "
            "비교한 뒤 평균했습니다.",
        "global_choose": "기후대",
        "comparison_title": "각 기후대가 얼마나 빠르게 더워지는가",
        "comparison_cap": "각 기후대의 1961-1990년 평년 대비 연간 기온 편차(평활). "
            "상승이 가파를수록 온난화가 빠릅니다.",
    },
    "hi": {
        "region_world": "विश्व",
        "region_tropical": "उष्णकटिबंध",
        "region_n_subtropical": "उत्तरी उपोष्णकटिबंध",
        "region_n_temperate": "उत्तरी शीतोष्ण",
        "region_n_boreal": "उत्तरी बोरियल और आर्कटिक",
        "region_s_subtropical": "दक्षिणी उपोष्णकटिबंध",
        "region_s_temperate": "दक्षिणी शीतोष्ण",
        "global_heading": "वैश्विक और क्षेत्रीय जलवायु डैशबोर्ड",
        "global_intro": "वही चार्ट, {n} शहरों में अक्षांश जलवायु क्षेत्र के अनुसार और "
            "विश्व स्तर पर समेकित। मान तापमान विसंगतियाँ हैं: प्रत्येक शहर अपने "
            "1961-1990 सामान्य की तुलना में, फिर औसत।",
        "global_choose": "जलवायु क्षेत्र",
        "comparison_title": "प्रत्येक जलवायु क्षेत्र कितनी तेज़ी से गर्म हो रहा है",
        "comparison_cap": "प्रत्येक क्षेत्र की 1961-1990 सामान्य की तुलना में वार्षिक "
            "तापमान विसंगति (स्मूद)। जितनी तीव्र वृद्धि, उतनी तेज़ गर्मी।",
    },
    "bn": {
        "region_world": "বিশ্ব",
        "region_tropical": "ক্রান্তীয়",
        "region_n_subtropical": "উত্তর উপক্রান্তীয়",
        "region_n_temperate": "উত্তর নাতিশীতোষ্ণ",
        "region_n_boreal": "উত্তর বোরিয়াল ও আর্কটিক",
        "region_s_subtropical": "দক্ষিণ উপক্রান্তীয়",
        "region_s_temperate": "দক্ষিণ নাতিশীতোষ্ণ",
        "global_heading": "বৈশ্বিক ও আঞ্চলিক জলবায়ু ড্যাশবোর্ড",
        "global_intro": "একই চার্ট, {n}টি শহর জুড়ে অক্ষাংশ জলবায়ু অঞ্চল অনুযায়ী এবং "
            "বিশ্বব্যাপী সমষ্টিগত। মানগুলি তাপমাত্রার অসংগতি: প্রতিটি শহর তার নিজস্ব "
            "১৯৬১-১৯৯০ স্বাভাবিকের তুলনায়, তারপর গড়।",
        "global_choose": "জলবায়ু অঞ্চল",
        "comparison_title": "প্রতিটি জলবায়ু অঞ্চল কত দ্রুত উষ্ণ হচ্ছে",
        "comparison_cap": "প্রতিটি অঞ্চলের ১৯৬১-১৯৯০ স্বাভাবিকের তুলনায় বার্ষিক "
            "তাপমাত্রার অসংগতি (মসৃণ)। বৃদ্ধি যত খাড়া, উষ্ণায়ন তত দ্রুত।",
    },
    "ar": {
        "region_world": "العالم",
        "region_tropical": "المناطق المدارية",
        "region_n_subtropical": "شبه المدارية الشمالية",
        "region_n_temperate": "المعتدلة الشمالية",
        "region_n_boreal": "الشمالية الباردة والقطب الشمالي",
        "region_s_subtropical": "شبه المدارية الجنوبية",
        "region_s_temperate": "المعتدلة الجنوبية",
        "global_heading": "لوحة المناخ العالمية والإقليمية",
        "global_intro": "الرسوم نفسها، مجمّعة عالميًا وحسب النطاقات المناخية للعروض "
            "عبر {n} مدينة. القيم هي شذوذات في درجة الحرارة: كل مدينة مقارنةً "
            "بمعدّلها الطبيعي 1961-1990، ثم يُؤخذ المتوسط.",
        "global_choose": "النطاق المناخي",
        "comparison_title": "مدى سرعة احترار كل نطاق مناخي",
        "comparison_cap": "شذوذ درجة الحرارة السنوي المُنعَّم لكل نطاق مقارنةً بمعدّل "
            "1961-1990. كلما زاد انحدار الصعود زادت سرعة الاحترار.",
    },
    "ur": {
        "region_world": "دنیا",
        "region_tropical": "اشنکٹبندیی",
        "region_n_subtropical": "شمالی نیم اشنکٹبندیی",
        "region_n_temperate": "شمالی معتدل",
        "region_n_boreal": "شمالی بوریل و قطب شمالی",
        "region_s_subtropical": "جنوبی نیم اشنکٹبندیی",
        "region_s_temperate": "جنوبی معتدل",
        "global_heading": "عالمی اور علاقائی موسمیاتی ڈیش بورڈ",
        "global_intro": "وہی چارٹس، {n} شہروں میں عرض بلد کے موسمیاتی خطوں کے مطابق "
            "اور عالمی سطح پر مجتمع۔ اقدار درجہ حرارت کے انحرافات ہیں: ہر شہر اپنے "
            "1961-1990 معمول کے مقابلے میں، پھر اوسط۔",
        "global_choose": "موسمیاتی خطہ",
        "comparison_title": "ہر موسمیاتی خطہ کتنی تیزی سے گرم ہو رہا ہے",
        "comparison_cap": "ہر خطے کا 1961-1990 معمول کے مقابلے میں سالانہ درجہ حرارت "
            "کا انحراف (ہموار)۔ زیادہ تیز چڑھائی کا مطلب زیادہ تیز حدت۔",
    },
    "fa": {
        "region_world": "جهان",
        "region_tropical": "مناطق حاره",
        "region_n_subtropical": "نیمه‌حاره شمالی",
        "region_n_temperate": "معتدل شمالی",
        "region_n_boreal": "بوره‌آل شمالی و قطب شمال",
        "region_s_subtropical": "نیمه‌حاره جنوبی",
        "region_s_temperate": "معتدل جنوبی",
        "global_heading": "داشبورد اقلیمی جهانی و منطقه‌ای",
        "global_intro": "همان نمودارها، تجمیع‌شده به‌صورت جهانی و بر پایهٔ کمربندهای "
            "اقلیمی عرض جغرافیایی در {n} شهر. مقادیر ناهنجاری دما هستند: هر شهر "
            "نسبت به نرمال ۱۹۶۱-۱۹۹۰ خودش، سپس میانگین‌گیری.",
        "global_choose": "کمربند اقلیمی",
        "comparison_title": "هر کمربند اقلیمی چقدر سریع گرم می‌شود",
        "comparison_cap": "ناهنجاری سالانهٔ دمای هموارشدهٔ هر کمربند نسبت به نرمال "
            "۱۹۶۱-۱۹۹۰. شیب تندتر یعنی گرمایش سریع‌تر.",
    },
}


# Per-zone "most extreme cities" chart (added later; English backfills the rest).
_EXTREMES = {
    "en": {"extremes_title": "Most extreme cities",
           "extremes_cap": "The fastest-warming cities (red) and the slowest or "
           "cooling ones (blue), by warming rate per decade."},
    "pl": {"extremes_title": "Najbardziej skrajne miasta",
           "extremes_cap": "Najszybciej ocieplające się miasta (czerwone) oraz "
           "najwolniejsze lub ochładzające się (niebieskie), według tempa na dekadę."},
    "de": {"extremes_title": "Extremste Städte",
           "extremes_cap": "Die sich am schnellsten erwärmenden Städte (rot) und "
           "die langsamsten oder sich abkühlenden (blau), nach Rate pro Jahrzehnt."},
    "fr": {"extremes_title": "Villes les plus extrêmes",
           "extremes_cap": "Les villes se réchauffant le plus vite (rouge) et les "
           "plus lentes ou en refroidissement (bleu), par taux par décennie."},
    "es": {"extremes_title": "Ciudades más extremas",
           "extremes_cap": "Las ciudades que más rápido se calientan (rojo) y las "
           "más lentas o que se enfrían (azul), por ritmo por década."},
    "uk": {"extremes_title": "Найекстремальніші міста",
           "extremes_cap": "Міста, що найшвидше теплішають (червоні), і найповільніші "
           "чи ті, що холоднішають (сині), за темпом на десятиліття."},
    "ru": {"extremes_title": "Самые экстремальные города",
           "extremes_cap": "Быстрее всего теплеющие города (красные) и самые "
           "медленные или охлаждающиеся (синие), по темпу за десятилетие."},
    "it": {"extremes_title": "Città più estreme",
           "extremes_cap": "Le città che si riscaldano più in fretta (rosso) e le "
           "più lente o in raffreddamento (blu), per tasso per decennio."},
    "pt": {"extremes_title": "Cidades mais extremas",
           "extremes_cap": "As cidades que aquecem mais depressa (vermelho) e as "
           "mais lentas ou a arrefecer (azul), por ritmo por década."},
    "nl": {"extremes_title": "Meest extreme steden",
           "extremes_cap": "De snelst opwarmende steden (rood) en de traagste of "
           "afkoelende (blauw), per tempo per decennium."},
    "tr": {"extremes_title": "En uç şehirler",
           "extremes_cap": "En hızlı ısınan şehirler (kırmızı) ve en yavaş ya da "
           "soğuyanlar (mavi), on yıllık ısınma hızına göre."},
    "id": {"extremes_title": "Kota paling ekstrem",
           "extremes_cap": "Kota yang paling cepat menghangat (merah) dan yang "
           "paling lambat atau mendingin (biru), menurut laju pemanasan per dekade."},
    "vi": {"extremes_title": "Các thành phố cực đoan nhất",
           "extremes_cap": "Các thành phố nóng lên nhanh nhất (đỏ) và chậm nhất "
           "hoặc đang lạnh đi (xanh), theo tốc độ nóng lên mỗi thập kỷ."},
    "zh": {"extremes_title": "升温最极端的城市",
           "extremes_cap": "升温最快的城市（红）与最慢或正在变冷的城市（蓝），"
           "按每十年升温速率排列。"},
    "ja": {"extremes_title": "最も極端な都市",
           "extremes_cap": "最も速く温暖化する都市（赤）と、最も遅い、または寒冷化"
           "する都市（青）。10年あたりの昇温率順。"},
    "ko": {"extremes_title": "가장 극단적인 도시",
           "extremes_cap": "가장 빠르게 더워지는 도시(빨강)와 가장 느리거나 추워지는 "
           "도시(파랑), 10년당 온난화 속도 기준."},
    "hi": {"extremes_title": "सबसे चरम शहर",
           "extremes_cap": "सबसे तेज़ गर्म होते शहर (लाल) और सबसे धीमे या ठंडे होते "
           "शहर (नीला), प्रति दशक तापन दर के अनुसार।"},
    "bn": {"extremes_title": "সবচেয়ে চরম শহর",
           "extremes_cap": "দ্রুততম উষ্ণ হওয়া শহর (লাল) এবং সবচেয়ে ধীর বা শীতল হওয়া "
           "শহর (নীল), প্রতি দশকে উষ্ণায়ন হার অনুসারে।"},
    "ar": {"extremes_title": "المدن الأكثر تطرفاً",
           "extremes_cap": "المدن الأسرع احتراراً (أحمر) والأبطأ أو الآخذة في "
           "البرودة (أزرق)، حسب معدل الاحترار لكل عقد."},
    "ur": {"extremes_title": "سب سے انتہائی شہر",
           "extremes_cap": "سب سے تیز گرم ہونے والے شہر (سرخ) اور سب سے سست یا ٹھنڈے "
           "ہوتے شہر (نیلا)، فی دہائی حدت کی شرح کے مطابق۔"},
    "fa": {"extremes_title": "شهرهای بیشینه",
           "extremes_cap": "شهرهایی که سریع‌ترین گرمایش را دارند (قرمز) و کندترین "
           "یا در حال سردشدن (آبی)، بر پایهٔ نرخ گرمایش در هر دهه."},
}
for _lang, _kv in _EXTREMES.items():
    _TEXT.setdefault(_lang, {}).update(_kv)

import extra_i18n  # noqa: E402
extra_i18n.fill(_TEXT, "globaltext")


def overlay(tr: dict, lang: str) -> dict:
    """Return a copy of ``tr`` with this language's dashboard keys merged in.

    English backfills any key a language hasn't translated yet (per-key), so a
    newly-added string never crashes a build before every language has it.
    """
    keys = {**_TEXT["en"], **_TEXT.get(lang, {})}
    return {**tr, **keys}
