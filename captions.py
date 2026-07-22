"""Neutral rewrites of the few chart captions that read colloquially.

The per-chart captions live in :mod:`i18n`; a couple were phrased casually (a
rhetorical question, an editorial aside). These neutral, factual replacements
override those keys for every language via :func:`overlay`, so the tone is
consistent without touching the large translation table.
"""

from __future__ import annotations

_CAPTIONS: dict[str, dict[str, str]] = {
    "en": {
        "cap_range": "Each month's minimum-maximum range across all years, with "
            "the most recent year overlaid.",
        "cap_stripes": "One stripe per year, coloured by its departure from the "
            "1961-1990 average: blue cooler, red warmer. The transition from "
            "blue to red is the warming.",
    },
    "pl": {
        "cap_range": "Zakres minimum-maksimum dla każdego miesiąca w całym "
            "okresie, z nałożonym najnowszym rokiem.",
        "cap_stripes": "Jeden pas na rok, zabarwiony według odchylenia od "
            "średniej 1961-1990: niebieski chłodniej, czerwony cieplej. "
            "Przejście od niebieskiego do czerwonego to ocieplenie.",
    },
    "de": {
        "cap_range": "Minimum-Maximum-Spanne jedes Monats über alle Jahre, mit "
            "dem jüngsten Jahr überlagert.",
        "cap_stripes": "Ein Streifen pro Jahr, gefärbt nach der Abweichung vom "
            "Mittel 1961-1990: Blau kühler, Rot wärmer. Der Übergang von Blau zu "
            "Rot ist die Erwärmung.",
    },
    "fr": {
        "cap_range": "Amplitude minimum-maximum de chaque mois sur toutes les "
            "années, avec l'année la plus récente superposée.",
        "cap_stripes": "Une bande par an, colorée selon l'écart à la moyenne "
            "1961-1990 : bleu plus frais, rouge plus chaud. Le passage du bleu au "
            "rouge est le réchauffement.",
    },
    "es": {
        "cap_range": "Rango mínimo-máximo de cada mes en todos los años, con el "
            "año más reciente superpuesto.",
        "cap_stripes": "Una franja por año, coloreada según su desviación de la "
            "media 1961-1990: azul más frío, rojo más cálido. La transición de "
            "azul a rojo es el calentamiento.",
    },
    "uk": {
        "cap_range": "Діапазон мінімум-максимум для кожного місяця за всі роки, з "
            "накладеним найновішим роком.",
        "cap_stripes": "Одна смуга на рік, забарвлена за відхиленням від "
            "середнього 1961-1990: синій прохолодніше, червоний тепліше. Перехід "
            "від синього до червоного це потепління.",
    },
    "ru": {
        "cap_range": "Диапазон минимум-максимум для каждого месяца за все годы, с "
            "наложенным последним годом.",
        "cap_stripes": "Одна полоса на год, окрашенная по отклонению от среднего "
            "1961-1990: синий холоднее, красный теплее. Переход от синего к красному это потепление.",
    },
    "it": {
        "cap_range": "Intervallo minimo-massimo di ogni mese su tutti gli anni, "
            "con l'anno più recente sovrapposto.",
        "cap_stripes": "Una striscia per anno, colorata secondo lo scarto dalla "
            "media 1961-1990: blu più fresco, rosso più caldo. Il passaggio dal "
            "blu al rosso è il riscaldamento.",
    },
    "pt": {
        "cap_range": "Amplitude mínimo-máximo de cada mês em todos os anos, com o "
            "ano mais recente sobreposto.",
        "cap_stripes": "Uma faixa por ano, colorida pelo desvio da média "
            "1961-1990: azul mais frio, vermelho mais quente. A transição de "
            "azul para vermelho é o aquecimento.",
    },
    "nl": {
        "cap_range": "Minimum-maximumbereik van elke maand over alle jaren, met "
            "het recentste jaar eroverheen.",
        "cap_stripes": "Eén streep per jaar, gekleurd naar de afwijking van het "
            "gemiddelde 1961-1990: blauw koeler, rood warmer. De overgang van "
            "blauw naar rood is de opwarming.",
    },
    "tr": {
        "cap_range": "Her ayın tüm yıllar boyunca minimum-maksimum aralığı, en "
            "son yıl üzerine bindirilmiş.",
        "cap_stripes": "Yıl başına bir şerit, 1961-1990 ortalamasından sapmasına "
            "göre renklendirilmiş: mavi daha serin, kırmızı daha sıcak. Maviden "
            "kırmızıya geçiş ısınmadır.",
    },
    "id": {
        "cap_range": "Rentang minimum-maksimum tiap bulan sepanjang tahun, dengan "
            "tahun terbaru ditumpangkan.",
        "cap_stripes": "Satu garis per tahun, diwarnai menurut simpangan dari "
            "rata-rata 1961-1990: biru lebih sejuk, merah lebih hangat. "
            "Peralihan dari biru ke merah adalah pemanasan.",
    },
    "vi": {
        "cap_range": "Khoảng tối thiểu-tối đa của mỗi tháng qua các năm, với năm "
            "gần nhất chồng lên.",
        "cap_stripes": "Mỗi năm một vạch, tô màu theo độ lệch so với trung bình "
            "1961-1990: xanh mát hơn, đỏ ấm hơn. Sự chuyển từ xanh sang đỏ là sự "
            "nóng lên.",
    },
    "zh": {
        "cap_range": "每个月在所有年份中的最小-最大范围，并叠加最近一年。",
        "cap_stripes": "每年一条色带，按其相对 1961-1990 年平均值的偏差着色：蓝较"
            "冷，红较暖。由蓝转红即为升温。",
    },
    "ja": {
        "cap_range": "各月の全期間における最小-最大の範囲。最新年を重ねて表示。",
        "cap_stripes": "1年につき1本の帯で、1961〜1990年平均からの偏差で着色（青は"
            "低め、赤は高め）。青から赤への推移が温暖化を表す。",
    },
    "ko": {
        "cap_range": "각 월의 전체 기간 최소-최대 범위. 최근 연도를 겹쳐 표시.",
        "cap_stripes": "연도마다 한 줄씩, 1961-1990년 평균과의 편차로 색을 입힘: 파랑은 더 서늘, 빨강은 더 따뜻. 파랑에서 빨강으로의 변화가 온난화.",
    },
    "hi": {
        "cap_range": "प्रत्येक माह का सभी वर्षों में न्यूनतम-अधिकतम परास, नवीनतम वर्ष "
            "के साथ अध्यारोपित।",
        "cap_stripes": "प्रति वर्ष एक पट्टी, 1961-1990 औसत से विचलन के अनुसार रंगी: नीला ठंडा, लाल गर्म। नीले से लाल की ओर बदलाव ही तापन है।",
    },
    "bn": {
        "cap_range": "সব বছর জুড়ে প্রতিটি মাসের সর্বনিম্ন-সর্বোচ্চ পরিসর, সাম্প্রতিকতম "
            "বছর উপরিস্থাপিত।",
        "cap_stripes": "প্রতি বছরে একটি ডোরা, ১৯৬১-১৯৯০ গড় থেকে বিচ্যুতি অনুসারে "
            "রঙিন: নীল শীতল, লাল উষ্ণ। নীল থেকে লালে রূপান্তরই উষ্ণায়ন।",
    },
    "ar": {
        "cap_range": "نطاق الحد الأدنى-الأقصى لكل شهر عبر جميع السنوات، مع تراكب "
            "أحدث سنة.",
        "cap_stripes": "شريط واحد لكل سنة، مُلوَّن حسب انحرافه عن متوسط 1961-1990: الأزرق أبرد، الأحمر أدفأ. الانتقال من الأزرق إلى الأحمر هو الاحترار.",
    },
    "ur": {
        "cap_range": "تمام برسوں میں ہر ماہ کی کم از کم-زیادہ سے زیادہ حد، تازہ "
            "ترین سال کے ساتھ اوپر رکھی گئی۔",
        "cap_stripes": "ہر سال کے لیے ایک پٹی، 1961-1990 اوسط سے انحراف کے مطابق "
            "رنگین: نیلا ٹھنڈا، سرخ گرم۔ نیلے سے سرخ کی طرف تبدیلی ہی حدت ہے۔",
    },
    "fa": {
        "cap_range": "بازهٔ کمینه-بیشینهٔ هر ماه در همهٔ سال‌ها، با هم‌پوشانی "
            "جدیدترین سال.",
        "cap_stripes": "هر سال یک نوار، رنگ‌آمیزی‌شده بر پایهٔ انحراف از میانگین "
            "۱۹۶۱-۱۹۹۰: آبی خنک‌تر، قرمز گرم‌تر. گذار از آبی به قرمز همان گرمایش "
            "است.",
    },
}

import extra_i18n  # noqa: E402
extra_i18n.fill(_CAPTIONS, "captions")


def overlay(tr: dict, lang: str) -> dict:
    """Return ``tr`` with the neutral caption rewrites merged in (English
    backfills any language not listed)."""
    keys = {**_CAPTIONS["en"], **_CAPTIONS.get(lang, {})}
    return {**tr, **keys}
