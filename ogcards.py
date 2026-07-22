"""Generate Open Graph share cards (1200x630 PNG) - one per country plus a world
card - so a link to any city page previews a compelling climate stat on social
media (X / Facebook / LinkedIn) instead of a bare title.

Each card shows the country's warming rate, how it ranks globally, and how much
of the world it is warming faster than, over a warming-stripes header echoing the
site. Text is English (share cards travel globally; the page itself is localized).

Rendered at build time with Pillow using a bundled DejaVu font (so CI reproduces
the output exactly, not relying on system fonts). Country names come from ICU
(generated once via Node's Intl.DisplayNames) so they match the on-page labels.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_ASSETS = Path(__file__).resolve().parent / "assets" / "fonts"
_BOLD = str(_ASSETS / "DejaVuSans-Bold.ttf")
_REG = str(_ASSETS / "DejaVuSans.ttf")

W, H = 1200, 630
_BG = (251, 250, 247)
_INK = (35, 34, 32)
_MUTED = (110, 108, 102)
_WARM = (192, 57, 43)
_COOL = (31, 111, 235)
_SITE = "yasoftwaredev.github.io/temperatury"

# ISO 3166-1 alpha-2 -> English country name (ICU / Intl.DisplayNames), for the
# countries our cities cover. Kept in sync with countries.py's coverage.
CC_NAMES: dict[str, str] = {
    "ad": "Andorra", "ae": "United Arab Emirates", "af": "Afghanistan",
    "al": "Albania", "am": "Armenia", "ao": "Angola", "ar": "Argentina",
    "at": "Austria", "au": "Australia", "az": "Azerbaijan",
    "ba": "Bosnia & Herzegovina", "bd": "Bangladesh", "be": "Belgium",
    "bf": "Burkina Faso", "bg": "Bulgaria", "bh": "Bahrain", "bi": "Burundi",
    "bj": "Benin", "bn": "Brunei", "bo": "Bolivia", "br": "Brazil",
    "bs": "Bahamas", "bt": "Bhutan", "bw": "Botswana", "by": "Belarus",
    "bz": "Belize", "ca": "Canada", "cd": "Congo - Kinshasa",
    "cf": "Central African Republic", "cg": "Congo - Brazzaville",
    "ch": "Switzerland", "ci": "Côte d’Ivoire", "cl": "Chile", "cm": "Cameroon",
    "cn": "China", "co": "Colombia", "cr": "Costa Rica", "cu": "Cuba",
    "cv": "Cape Verde", "cy": "Cyprus", "cz": "Czechia", "de": "Germany",
    "dj": "Djibouti", "dk": "Denmark", "do": "Dominican Republic", "dz": "Algeria",
    "ec": "Ecuador", "ee": "Estonia", "eg": "Egypt", "er": "Eritrea",
    "es": "Spain", "et": "Ethiopia", "fi": "Finland", "fj": "Fiji",
    "fm": "Micronesia", "fr": "France", "ga": "Gabon", "gb": "United Kingdom",
    "ge": "Georgia", "gh": "Ghana", "gl": "Greenland", "gm": "Gambia",
    "gn": "Guinea", "gq": "Equatorial Guinea", "gr": "Greece", "gt": "Guatemala",
    "gw": "Guinea-Bissau", "gy": "Guyana", "hk": "Hong Kong", "hn": "Honduras",
    "hr": "Croatia", "ht": "Haiti", "hu": "Hungary", "id": "Indonesia",
    "ie": "Ireland", "il": "Israel", "in": "India", "iq": "Iraq", "ir": "Iran",
    "is": "Iceland", "it": "Italy", "jm": "Jamaica", "jo": "Jordan", "jp": "Japan",
    "ke": "Kenya", "kg": "Kyrgyzstan", "kh": "Cambodia", "ki": "Kiribati",
    "km": "Comoros", "kp": "North Korea", "kr": "South Korea", "kw": "Kuwait",
    "kz": "Kazakhstan", "la": "Laos", "lb": "Lebanon", "li": "Liechtenstein",
    "lk": "Sri Lanka", "lr": "Liberia", "ls": "Lesotho", "lt": "Lithuania",
    "lu": "Luxembourg", "lv": "Latvia", "ly": "Libya", "ma": "Morocco",
    "mc": "Monaco", "md": "Moldova", "me": "Montenegro", "mg": "Madagascar",
    "mh": "Marshall Islands", "mk": "North Macedonia", "ml": "Mali",
    "mm": "Myanmar", "mn": "Mongolia", "mr": "Mauritania", "mt": "Malta",
    "mu": "Mauritius", "mv": "Maldives", "mw": "Malawi", "mx": "Mexico",
    "my": "Malaysia", "mz": "Mozambique", "na": "Namibia", "nc": "New Caledonia",
    "ne": "Niger", "ng": "Nigeria", "ni": "Nicaragua", "nl": "Netherlands",
    "no": "Norway", "np": "Nepal", "nz": "New Zealand", "om": "Oman",
    "pa": "Panama", "pe": "Peru", "pg": "Papua New Guinea", "ph": "Philippines",
    "pk": "Pakistan", "pl": "Poland", "pt": "Portugal", "py": "Paraguay",
    "qa": "Qatar", "ro": "Romania", "rs": "Serbia", "ru": "Russia", "rw": "Rwanda",
    "sa": "Saudi Arabia", "sb": "Solomon Islands", "sc": "Seychelles",
    "sd": "Sudan", "se": "Sweden", "sg": "Singapore", "si": "Slovenia",
    "sk": "Slovakia", "sl": "Sierra Leone", "sm": "San Marino", "sn": "Senegal",
    "so": "Somalia", "sr": "Suriname", "ss": "South Sudan", "sv": "El Salvador",
    "sy": "Syria", "sz": "Eswatini", "td": "Chad", "tg": "Togo", "th": "Thailand",
    "tj": "Tajikistan", "tl": "Timor-Leste", "tm": "Turkmenistan", "tn": "Tunisia",
    "to": "Tonga", "tr": "Türkiye", "tw": "Taiwan", "tz": "Tanzania",
    "ua": "Ukraine", "ug": "Uganda", "us": "United States", "uy": "Uruguay",
    "uz": "Uzbekistan", "va": "Vatican City", "ve": "Venezuela", "vn": "Vietnam",
    "vu": "Vanuatu", "ws": "Samoa", "xk": "Kosovo", "ye": "Yemen",
    "za": "South Africa", "zm": "Zambia", "zw": "Zimbabwe",
}


def country_name(cc: str) -> str:
    return CC_NAMES.get(cc, cc.upper())


def _ramp(t: float) -> tuple[int, int, int]:
    """Warming-stripe colour for t in [0,1]: deep blue -> pale -> deep red."""
    t = max(0.0, min(1.0, t))
    cold, mid, hot = (49, 84, 145), (238, 236, 228), (165, 30, 34)
    if t < 0.5:
        a, b, k = cold, mid, t / 0.5
    else:
        a, b, k = mid, hot, (t - 0.5) / 0.5
    return (round(a[0] + (b[0] - a[0]) * k),
            round(a[1] + (b[1] - a[1]) * k),
            round(a[2] + (b[2] - a[2]) * k))


def _stripes(draw: ImageDraw.ImageDraw, y0: int, h: int) -> None:
    """A warming-stripes band across the top: cool on the left, warm on the
    right (the site's signature motif)."""
    n = 60
    bw = W / n
    for i in range(n):
        draw.rectangle([round(i * bw), y0, round((i + 1) * bw), y0 + h],
                       fill=_ramp(i / (n - 1)))


def _ramp_anom(v: float) -> tuple[int, int, int]:
    """Colour for a decade anomaly (°C) on a fixed blue->pale->red scale, matching
    the site's inline stripes so the shared card reads the same as the table."""
    lo, hi = -1.0, 1.5
    x = max(lo, min(hi, v))
    cold, mid, hot = (49, 84, 145), (238, 236, 228), (165, 30, 34)
    if x < 0:
        a, b, k = cold, mid, (x - lo) / (0 - lo)
    else:
        a, b, k = mid, hot, x / hi
    return (round(a[0] + (b[0] - a[0]) * k),
            round(a[1] + (b[1] - a[1]) * k),
            round(a[2] + (b[2] - a[2]) * k))


def _stripes_real(draw: ImageDraw.ImageDraw, st: list, y0: int, h: int) -> None:
    """The city's OWN warming stripes - one bar per decade anomaly in ``st`` -
    so the share card is that city's real fingerprint, not a generic ramp."""
    vals = [v for v in (st or []) if v is not None]
    if not vals:
        _stripes(draw, y0, h)
        return
    bw = W / len(vals)
    for i, v in enumerate(vals):
        draw.rectangle([round(i * bw), y0, round((i + 1) * bw), y0 + h],
                       fill=_ramp_anom(v))


def _fit_font(draw, text, path, size, max_w):
    """Largest font <= size whose text width fits max_w."""
    while size > 20:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 3
    return ImageFont.truetype(path, size)


def _card(country: str, trend: float, rank: int, total: int, n_cities: int,
          pct: int, subtitle: str) -> Image.Image:
    img = Image.new("RGB", (W, H), _BG)
    d = ImageDraw.Draw(img)
    _stripes(d, 0, 74)
    warm = trend >= 0
    accent = _WARM if warm else _COOL

    d.text((70, 120), subtitle.upper(), font=ImageFont.truetype(_REG, 26),
           fill=_MUTED)
    name_font = _fit_font(d, country, _BOLD, 76, W - 140)
    d.text((70, 158), country, font=name_font, fill=_INK)

    big = (("+" if warm else "") + f"{trend:.2f}") + "°C"
    big_font = ImageFont.truetype(_BOLD, 132)
    d.text((66, 258), big, font=big_font, fill=accent)
    bw = d.textlength(big, font=big_font)
    d.text((66 + bw + 24, 340), "per decade", font=ImageFont.truetype(_REG, 40),
           fill=_MUTED)
    d.text((70, 420), "1940-2025 " + ("warming" if warm else "cooling") + " trend",
           font=ImageFont.truetype(_REG, 30), fill=_MUTED)

    line = (f"Warming faster than {pct}% of the world"
            if warm else "Cooling, against the global trend")
    d.text((70, 486), line, font=_fit_font(d, line, _BOLD, 40, W - 140), fill=_INK)
    meta = f"#{rank} of {total} countries  ·  {n_cities} cit" + \
           ("y" if n_cities == 1 else "ies")
    d.text((70, 540), meta, font=ImageFont.truetype(_REG, 32), fill=_MUTED)

    site_font = ImageFont.truetype(_REG, 28)
    sw = d.textlength(_SITE, font=site_font)
    d.text((W - 70 - sw, 588), _SITE, font=site_font, fill=_MUTED)
    return img


def _world_card(mean_trend: float, n_cities: int, n_countries: int) -> Image.Image:
    img = Image.new("RGB", (W, H), _BG)
    d = ImageDraw.Draw(img)
    _stripes(d, 0, 74)
    d.text((70, 130), "GLOBAL WARMING, CITY BY CITY",
           font=ImageFont.truetype(_REG, 26), fill=_MUTED)
    d.text((70, 168), "Temperatures worldwide",
           font=ImageFont.truetype(_BOLD, 72), fill=_INK)
    big = f"+{mean_trend:.2f}°C"
    d.text((66, 268), big, font=ImageFont.truetype(_BOLD, 132), fill=_WARM)
    d.text((70, 430), "average warming per decade, 1940-2025",
           font=ImageFont.truetype(_REG, 34), fill=_MUTED)
    d.text((70, 500), f"{n_cities:,} cities across {n_countries} countries",
           font=ImageFont.truetype(_BOLD, 40), fill=_INK)
    site_font = ImageFont.truetype(_REG, 28)
    sw = d.textlength(_SITE, font=site_font)
    d.text((W - 70 - sw, 588), _SITE, font=site_font, fill=_MUTED)
    return img


def _city_card(name: str, country: str, total: float, trend: float,
               rank: int, total_cities: int, pct: int, st: list,
               analog: dict | None = None) -> Image.Image:
    """One city's share card: its own stripes, the visceral total-warming number,
    and where it sits worldwide. Total warming leads (more shareable than /decade)."""
    img = Image.new("RGB", (W, H), _BG)
    d = ImageDraw.Draw(img)
    _stripes_real(d, st, 0, 74)
    warm = total >= 0
    accent = _WARM if warm else _COOL

    d.text((70, 120), country.upper(), font=ImageFont.truetype(_REG, 26), fill=_MUTED)
    name_font = _fit_font(d, name, _BOLD, 76, W - 140)
    d.text((70, 158), name, font=name_font, fill=_INK)

    big = (("+" if warm else "") + f"{total:.1f}") + "°C"
    big_font = ImageFont.truetype(_BOLD, 132)
    d.text((66, 258), big, font=big_font, fill=accent)
    bw = d.textlength(big, font=big_font)
    d.text((66 + bw + 24, 344), "since 1940", font=ImageFont.truetype(_REG, 40),
           fill=_MUTED)
    d.text((70, 420), f"{('+' if trend >= 0 else '')}{trend:.2f}°C per decade  ·  "
           + ("warming trend" if warm else "cooling trend"),
           font=ImageFont.truetype(_REG, 30), fill=_MUTED)

    line = (f"Warming faster than {pct}% of the world's cities"
            if warm else "Cooling, against the global trend")
    d.text((70, 486), line, font=_fit_font(d, line, _BOLD, 40, W - 140), fill=_INK)
    # The 2050 analog is the stronger hook, so it takes the last line when present
    # (the percentile above already conveys ranking); else fall back to the rank.
    if analog and analog.get("n"):
        a_line = f"By 2050, it could feel like {analog['n']} does today"
        d.text((70, 540), a_line, font=_fit_font(d, a_line, _BOLD, 32, W - 140),
               fill=accent)
    else:
        d.text((70, 540), f"#{rank} of {total_cities:,} cities worldwide",
               font=ImageFont.truetype(_REG, 32), fill=_MUTED)

    site_font = ImageFont.truetype(_REG, 28)
    sw = d.textlength(_SITE, font=site_font)
    d.text((W - 70 - sw, 588), _SITE, font=site_font, fill=_MUTED)
    return img


def _save_card(img: Image.Image, path: Path) -> None:
    """Save a share card as a palette PNG (~3x smaller than 24-bit).

    The cards are discrete warming-stripe bands plus flat-colour text on a solid
    ground - well under 256 colours - so 256-colour quantization is visually
    lossless while cutting each card from ~60 KB to ~20 KB. og:image consumers
    (Facebook, X, Slack, ...) render palette PNGs identically.
    """
    img.convert("RGB").quantize(
        colors=256, method=Image.Quantize.FASTOCTREE).save(path, optimize=True)


def build_cards(payload: dict, output_dir: Path) -> int:
    """Write ``output_dir/og/<cc>.png`` for every country in the ranking plus a
    ``world.png``. Returns the number of cards written."""
    og = output_dir / "og"
    og.mkdir(parents=True, exist_ok=True)
    written = 0
    for c in payload.get("countries", []):
        card = _card(country_name(c["cc"]), c["t"], c["rank"], c["total"],
                     c["n"], c["pct"], "How fast it is warming")
        _save_card(card, og / f"{c['cc']}.png")
        written += 1
    ranking = payload.get("ranking", [])
    if ranking:
        mean = sum(r["t"] for r in ranking) / len(ranking)
        n_countries = len(payload.get("countries", []))
        _save_card(_world_card(mean, len(ranking), n_countries),
                   og / "world.png")
        written += 1
        # One card per city - the share image behind every city page's og:image.
        # Ranking is sorted fastest-first, so the index is the global rank.
        cog = og / "city"
        cog.mkdir(parents=True, exist_ok=True)
        total_cities = len(ranking)
        analogs = payload.get("analogs", {})
        for i, r in enumerate(ranking):
            rank = i + 1
            pct = round(100 * (total_cities - rank) / total_cities) if total_cities else 0
            _save_card(
                _city_card(r["n"], country_name(r["cc"]),
                           r["dt"], r["t"], rank,
                           total_cities, pct, r.get("st"),
                           analogs.get(r["s"])),
                cog / f"{r['s']}.png")
            written += 1
    return written
