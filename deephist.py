"""The "deep history" note: what temperature data exists before 1940.

The charts start in 1940 because they use the ERA5 reanalysis, whose record
begins that year. Earlier estimates are not merged into the ERA5 series, because
they rest on sparser observations and different methods with larger uncertainty.
This module supplies the short explanatory note and, for a city that holds one
of the world's long instrumental records, a line naming the record and its start
year (a documented fact, not a reconstructed value).

``RECORDS`` maps a city slug to ``(label, start_year)``. ``overlay(tr, lang)``
merges the localised note onto a language's table; the note is translated for
every supported language.
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
        "deephist_title": "Why is there no data before 1940?",
        "deephist_body":
            "<p>The charts begin in 1940 because they use the ERA5 reanalysis, "
            "whose record starts that year. Earlier data exists (the NOAA "
            "20th-Century Reanalysis extends to 1836, and a few stations hold "
            "multi-century records), but it relies on sparser, pre-satellite "
            "observations and carries larger uncertainty. It is not merged with "
            "the ERA5 series here, because the methods and error ranges differ.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} holds one of the longest instrumental "
            "temperature records, beginning in {year}.</p>",
    },
    "pl": {
        "deephist_title": "Dlaczego brakuje danych sprzed 1940 roku?",
        "deephist_body":
            "<p>Wykresy zaczynają się w 1940 roku, ponieważ korzystają z "
            "reanalizy ERA5, której zapis rozpoczyna się w tym roku. Wcześniejsze "
            "dane istnieją (reanaliza NOAA 20th-Century Reanalysis sięga 1836 "
            "roku, a kilka stacji ma wielowiekowe serie), lecz opierają się na "
            "rzadszych, przedsatelitarnych obserwacjach i mają większą "
            "niepewność. Nie są tu łączone z serią ERA5, ponieważ metody i "
            "zakresy błędu się różnią.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} prowadzi jedną z najdłuższych "
            "instrumentalnych serii temperatury, rozpoczętą w {year} roku.</p>",
    },
    "de": {
        "deephist_title": "Warum gibt es keine Daten vor 1940?",
        "deephist_body":
            "<p>Die Diagramme beginnen 1940, da sie die ERA5-Reanalyse "
            "verwenden, deren Aufzeichnung in diesem Jahr beginnt. Ältere Daten "
            "existieren (die NOAA 20th-Century Reanalysis reicht bis 1836, und "
            "einige Stationen führen mehrhundertjährige Reihen), beruhen jedoch "
            "auf spärlicheren, vorsatellitären Beobachtungen und weisen größere "
            "Unsicherheiten auf. Sie werden hier nicht mit der ERA5-Reihe "
            "zusammengeführt, da sich Methoden und Fehlerbereiche unterscheiden.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} führt eine der längsten instrumentellen "
            "Temperaturreihen, beginnend {year}.</p>",
    },
    "fr": {
        "deephist_title": "Pourquoi n'y a-t-il pas de données avant 1940 ?",
        "deephist_body":
            "<p>Les graphiques commencent en 1940 car ils utilisent la "
            "réanalyse ERA5, dont l'enregistrement débute cette année-là. Des "
            "données antérieures existent (la NOAA 20th-Century Reanalysis "
            "remonte à 1836, et quelques stations disposent de séries "
            "pluriséculaires), mais elles reposent sur des observations plus "
            "rares, antérieures aux satellites, et comportent une incertitude "
            "plus grande. Elles ne sont pas fusionnées avec la série ERA5 ici, "
            "car les méthodes et les marges d'erreur diffèrent.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} détient l'une des plus longues séries "
            "instrumentales de température, débutée en {year}.</p>",
    },
    "es": {
        "deephist_title": "¿Por qué no hay datos antes de 1940?",
        "deephist_body":
            "<p>Los gráficos comienzan en 1940 porque usan el reanálisis ERA5, "
            "cuyo registro empieza ese año. Existen datos anteriores (el NOAA "
            "20th-Century Reanalysis llega a 1836, y algunas estaciones tienen "
            "series de varios siglos), pero se basan en observaciones más "
            "escasas, previas a los satélites, y tienen mayor incertidumbre. No "
            "se combinan con la serie ERA5 aquí, porque los métodos y los "
            "márgenes de error difieren.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} mantiene uno de los registros "
            "instrumentales de temperatura más largos, iniciado en {year}.</p>",
    },
    "uk": {
        "deephist_title": "Чому немає даних до 1940 року?",
        "deephist_body":
            "<p>Графіки починаються в 1940 році, оскільки використовують "
            "реаналіз ERA5, запис якого стартує цього року. Раніші дані існують (реаналіз NOAA 20th-Century Reanalysis сягає 1836 року, а кілька "
            "станцій мають багатовікові ряди), але вони спираються на рідші, "
            "досупутникові спостереження й мають більшу невизначеність. Тут вони "
            "не поєднуються з рядом ERA5, бо методи та діапазони похибок "
            "різняться.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} веде один із найдовших інструментальних "
            "рядів температури, розпочатий у {year} році.</p>",
    },
    "ru": {
        "deephist_title": "Почему нет данных до 1940 года?",
        "deephist_body":
            "<p>Графики начинаются в 1940 году, поскольку используют реанализ "
            "ERA5, запись которого стартует в этом году. Более ранние данные "
            "существуют (реанализ NOAA 20th-Century Reanalysis доходит до 1836 "
            "года, а несколько станций ведут многовековые ряды), но они "
            "опираются на более редкие, доспутниковые наблюдения и имеют большую "
            "неопределённость. Здесь они не объединяются с рядом ERA5, так как "
            "методы и диапазоны погрешностей различаются.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} ведёт один из самых длинных "
            "инструментальных рядов температуры, начатый в {year} году.</p>",
    },
    "it": {
        "deephist_title": "Perché non ci sono dati prima del 1940?",
        "deephist_body":
            "<p>I grafici iniziano nel 1940 perché usano la rianalisi ERA5, il "
            "cui registro parte in quell'anno. Dati precedenti esistono (la NOAA 20th-Century Reanalysis risale al 1836 e alcune stazioni hanno "
            "serie plurisecolari), ma si basano su osservazioni più rade, "
            "precedenti ai satelliti, e hanno un'incertezza maggiore. Qui non "
            "vengono uniti alla serie ERA5, perché metodi e margini d'errore "
            "differiscono.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} mantiene una delle più lunghe serie "
            "strumentali di temperatura, iniziata nel {year}.</p>",
    },
    "pt": {
        "deephist_title": "Porque não há dados antes de 1940?",
        "deephist_body":
            "<p>Os gráficos começam em 1940 porque usam a reanálise ERA5, cujo "
            "registo começa nesse ano. Existem dados anteriores (a NOAA "
            "20th-Century Reanalysis recua até 1836, e algumas estações têm "
            "séries de vários séculos), mas assentam em observações mais "
            "escassas, anteriores aos satélites, e têm maior incerteza. Não são "
            "combinados com a série ERA5 aqui, porque os métodos e as margens de "
            "erro diferem.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} mantém um dos mais longos registos "
            "instrumentais de temperatura, iniciado em {year}.</p>",
    },
    "nl": {
        "deephist_title": "Waarom zijn er geen gegevens van vóór 1940?",
        "deephist_body":
            "<p>De grafieken beginnen in 1940 omdat ze de ERA5-heranalyse "
            "gebruiken, waarvan de reeks dat jaar begint. Eerdere gegevens "
            "bestaan (de NOAA 20th-Century Reanalysis reikt tot 1836, en enkele "
            "stations hebben reeksen van meerdere eeuwen), maar berusten op "
            "schaarsere, pre-satelliet-waarnemingen en hebben een grotere "
            "onzekerheid. Ze worden hier niet samengevoegd met de ERA5-reeks, "
            "omdat methoden en foutmarges verschillen.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} houdt een van de langste instrumentele "
            "temperatuurreeksen bij, begonnen in {year}.</p>",
    },
    "tr": {
        "deephist_title": "1940'tan önce neden veri yok?",
        "deephist_body":
            "<p>Grafikler 1940'ta başlar, çünkü kaydı o yıl başlayan ERA5 "
            "yeniden analizini kullanır. Daha eski veriler mevcuttur (NOAA "
            "20th-Century Reanalysis 1836'ya uzanır ve birkaç istasyonun "
            "yüzyıllar süren serileri vardır), ancak bunlar daha seyrek, uydu "
            "öncesi gözlemlere dayanır ve daha büyük belirsizlik taşır. "
            "Yöntemler ve hata aralıkları farklı olduğundan burada ERA5 "
            "serisiyle birleştirilmez.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label}, {year} yılında başlayan en uzun aletli "
            "sıcaklık kayıtlarından birini tutar.</p>",
    },
    "id": {
        "deephist_title": "Mengapa tidak ada data sebelum 1940?",
        "deephist_body":
            "<p>Grafik dimulai pada 1940 karena menggunakan reanalisis ERA5, "
            "yang catatannya mulai tahun itu. Data lebih awal ada (NOAA "
            "20th-Century Reanalysis mencapai 1836, dan beberapa stasiun "
            "memiliki seri berabad-abad), tetapi bertumpu pada pengamatan yang "
            "lebih jarang, pra-satelit, dan memiliki ketidakpastian lebih besar. "
            "Data itu tidak digabungkan dengan seri ERA5 di sini, karena metode "
            "dan rentang galatnya berbeda.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} memegang salah satu catatan suhu "
            "instrumental terpanjang, dimulai pada {year}.</p>",
    },
    "vi": {
        "deephist_title": "Vì sao không có dữ liệu trước năm 1940?",
        "deephist_body":
            "<p>Các biểu đồ bắt đầu từ năm 1940 vì dùng tái phân tích ERA5, có "
            "bản ghi bắt đầu năm đó. Dữ liệu sớm hơn vẫn tồn tại (NOAA "
            "20th-Century Reanalysis lùi tới 1836, và một số trạm có chuỗi nhiều "
            "thế kỷ), nhưng dựa trên quan trắc thưa hơn, trước vệ tinh, và có độ "
            "bất định lớn hơn. Chúng không được ghép với chuỗi ERA5 ở đây, vì "
            "phương pháp và biên sai số khác nhau.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} giữ một trong những chuỗi nhiệt độ đo "
            "đạc dài nhất, bắt đầu năm {year}.</p>",
    },
    "zh": {
        "deephist_title": "为什么 1940 年以前没有数据？",
        "deephist_body":
            "<p>图表从 1940 年开始，因为所用的 ERA5 再分析记录始于该年。更早的数据也"
            "存在（NOAA 20 世纪再分析可追溯到 1836 年，少数台站有数百年的序列）但"
            "它们依赖更稀疏的卫星前观测，不确定性更大。此处不将其与 ERA5 序列合并，"
            "因为方法与误差范围不同。</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} 保有最长的器测气温记录之一，始于 "
            "{year} 年。</p>",
    },
    "ja": {
        "deephist_title": "なぜ1940年以前のデータがないのか？",
        "deephist_body":
            "<p>グラフは1940年から始まります。用いるERA5再解析の記録がその年に"
            "始まるためです。より古いデータも存在し（NOAAの20世紀再解析は1836年"
            "まで遡り、数百年の記録を持つ観測点もあります）が、衛星以前のより疎らな"
            "観測に基づき、不確実性が大きくなります。手法と誤差範囲が異なるため、"
            "ここではERA5の系列とは結合していません。</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label}は最も長い器械観測の気温記録の一つを持ち、"
            "{year}年に始まります。</p>",
    },
    "ko": {
        "deephist_title": "왜 1940년 이전의 데이터가 없을까요?",
        "deephist_body":
            "<p>그래프는 1940년에 시작합니다. 사용하는 ERA5 재분석의 기록이 그해에 "
            "시작하기 때문입니다. 더 이른 자료도 있습니다 (NOAA 20세기 재분석은 "
            "1836년까지 거슬러 올라가고, 몇몇 관측소는 수백 년의 계열을 보유합니다), 그러나 위성 이전의 더 성긴 관측에 의존하며 불확실성이 큽니다. 방법과 "
            "오차 범위가 달라 여기서는 ERA5 계열과 결합하지 않습니다.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label}는 가장 긴 기기 관측 기온 기록 중 하나를 "
            "{year}년부터 보유하고 있습니다.</p>",
    },
    "hi": {
        "deephist_title": "1940 से पहले के आँकड़े क्यों नहीं हैं?",
        "deephist_body":
            "<p>ये चार्ट 1940 से शुरू होते हैं क्योंकि ये ERA5 पुनर्विश्लेषण का उपयोग "
            "करते हैं, जिसका अभिलेख उसी वर्ष शुरू होता है। पहले के आँकड़े मौजूद हैं (NOAA 20th-Century Reanalysis 1836 तक जाता है, और कुछ केंद्रों के पास "
            "शताब्दियों लंबी शृंखलाएँ हैं), पर वे उपग्रह-पूर्व की विरल प्रेक्षणों पर "
            "आधारित हैं और उनमें अनिश्चितता अधिक है। यहाँ इन्हें ERA5 शृंखला के साथ "
            "नहीं मिलाया गया, क्योंकि विधियाँ और त्रुटि-परास भिन्न हैं।</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} सबसे लंबे यांत्रिक तापमान अभिलेखों में से एक "
            "रखता है, जो {year} में आरंभ हुआ।</p>",
    },
    "bn": {
        "deephist_title": "১৯৪০ সালের আগের তথ্য কেন নেই?",
        "deephist_body":
            "<p>চার্টগুলি ১৯৪০ থেকে শুরু হয়, কারণ এগুলি ERA5 পুনর্বিশ্লেষণ ব্যবহার "
            "করে, যার নথি সেই বছর শুরু হয়। আগের তথ্য আছে (NOAA 20th-Century "
            "Reanalysis ১৮৩৬ পর্যন্ত পৌঁছায়, এবং কয়েকটি কেন্দ্রে শতাব্দীব্যাপী ধারা "
            "আছে), তবে সেগুলি উপগ্রহ-পূর্ব বিরল পর্যবেক্ষণের উপর নির্ভর করে এবং "
            "অনিশ্চয়তা বেশি। পদ্ধতি ও ত্রুটির পরিসর ভিন্ন হওয়ায় এখানে সেগুলি ERA5 "
            "ধারার সঙ্গে মেলানো হয়নি।</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} দীর্ঘতম যান্ত্রিক তাপমাত্রা নথিগুলির একটি "
            "রাখে, যা {year} সালে শুরু।</p>",
    },
    "ar": {
        "deephist_title": "لماذا لا توجد بيانات قبل عام 1940؟",
        "deephist_body":
            "<p>تبدأ الرسوم من 1940 لأنها تستخدم إعادة تحليل ERA5، الذي يبدأ سجله "
            "في ذلك العام. توجد بيانات أقدم (يمتد إعادة تحليل NOAA للقرن العشرين "
            "إلى 1836، ولدى بعض المحطات سلاسل تمتد قروناً)، لكنها تستند إلى أرصاد "
            "أندر سابقة للأقمار الصناعية وذات عدم يقين أكبر. لا تُدمج هنا مع سلسلة "
            "ERA5، لأن المناهج ونطاقات الخطأ مختلفة.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} يحفظ أحد أطول سجلات الحرارة المرصودة "
            "بالأجهزة، بدأ عام {year}.</p>",
    },
    "ur": {
        "deephist_title": "1940 سے پہلے کے اعداد و شمار کیوں نہیں ہیں؟",
        "deephist_body":
            "<p>چارٹ 1940 سے شروع ہوتے ہیں کیونکہ یہ ERA5 دوبارہ تجزیہ استعمال کرتے "
            "ہیں، جس کا ریکارڈ اسی سال شروع ہوتا ہے۔ اس سے پہلے کے اعداد و شمار موجود ہیں (NOAA کا بیسویں صدی کا دوبارہ تجزیہ 1836 تک جاتا ہے، اور چند مراکز "
            "کے پاس صدیوں پر محیط سلسلے ہیں)، مگر یہ سیارچوں سے پہلے کے کم مشاہدات پر "
            "مبنی ہیں اور ان میں غیر یقینی زیادہ ہے۔ یہاں انہیں ERA5 سلسلے کے ساتھ "
            "نہیں ملایا گیا، کیونکہ طریقے اور خطا کی حدود مختلف ہیں۔</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} درجہ حرارت کے طویل ترین آلاتی ریکارڈوں میں "
            "سے ایک رکھتا ہے، جو {year} میں شروع ہوا۔</p>",
    },
    "fa": {
        "deephist_title": "چرا پیش از ۱۹۴۰ داده‌ای وجود ندارد؟",
        "deephist_body":
            "<p>نمودارها از ۱۹۴۰ آغاز می‌شوند، زیرا از بازتحلیل ERA5 استفاده "
            "می‌کنند که سابقهٔ آن از همان سال شروع می‌شود. داده‌های پیش‌تر وجود "
            "دارد (بازتحلیل قرن بیستم NOAA تا ۱۸۳۶ می‌رسد و چند ایستگاه سری‌های "
            "چندصدساله دارند)، اما بر مشاهدات پراکنده‌ترِ پیش از ماهواره متکی‌اند "
            "و عدم قطعیت بیشتری دارند. اینجا با سری ERA5 ادغام نمی‌شوند، چون "
            "روش‌ها و بازه‌های خطا متفاوت‌اند.</p>",
        "deephist_record":
            "<p class=\"dh-here\">{label} یکی از طولانی‌ترین سوابق دمای ابزاری را "
            "نگه می‌دارد که در {year} آغاز شده است.</p>",
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
