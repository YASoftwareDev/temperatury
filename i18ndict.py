"""Per-language dictionaries for client-side i18n (R1-hybrid).

``merged_table(lang)`` is the single flat ``{key: localized}`` table the browser
applies. It merges every per-language source the server used to bake into pages:
the base i18n table plus the caption/deephist/ranktext overlays and report.py's
hero / fullscreen / reset-zoom tables. ``build_lang_dicts`` writes one small JS
file per language (``window.__i18n = {...}``); a page includes only its own
language's file, so a language costs ~one dictionary instead of a full set of
pre-rendered pages.
"""
from __future__ import annotations

import json
from pathlib import Path

import captions
import deephist
import i18n
import ranktext
from report import _FS_LABEL, _HERO_I18N, _RZ_LABEL, _WIDGET_LABEL, _map_label


def _hero_flat(lang: str) -> dict:
    """Flatten report.py's hero/fullscreen/reset-zoom tables to namespaced keys
    the shell references as ``data-i18n``. ``_HERO_I18N`` is a dict-per-language
    (falls back to English where a language is absent); ``_FS_LABEL``/``_RZ_LABEL``
    are plain strings per language."""
    out: dict = {}
    block = _HERO_I18N.get(lang) or _HERO_I18N["en"]
    for k, v in block.items():
        out[f"hero_{k}"] = v
    out["fs"] = _FS_LABEL.get(lang, _FS_LABEL["en"])
    out["rz"] = _RZ_LABEL.get(lang, _RZ_LABEL["en"])
    return out


def merged_table(lang: str) -> dict:
    """The full flat dictionary the browser applies for one language."""
    t: dict = {}
    t.update(i18n.get(lang))               # base UI + most captions live here
    t.update(captions.overlay({}, lang))   # extra chart captions
    t.update(deephist.overlay({}, lang))   # deep-history explainer
    t.update(ranktext.overlay({}, lang))   # ranking strings
    t.update(_hero_flat(lang))             # hero / fullscreen / reset-zoom
    # Chrome outside <main> (topbar "back to map" link with its emoji stripped,
    # and the embed link) - shown per-language but not present in the base table
    # in the exact form the shell renders.
    t["map_label"] = _map_label(i18n.get(lang))
    t["widget_label"] = _WIDGET_LABEL.get(lang, _WIDGET_LABEL["en"])
    return {k: v for k, v in t.items() if isinstance(v, str)}


def build_lang_dicts(output_dir: Path, languages: list[str]) -> int:
    """Write ``output/i18n/<lang>.js`` for each language. Returns the count."""
    d = output_dir / "i18n"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for lang in languages:
        table = merged_table(lang)
        payload = json.dumps(table, ensure_ascii=False, separators=(",", ":"))
        # Localized month names ride in the dict (an array, so filtered out of
        # the string-only table) so a language switch updates month labels in
        # both the page (@months.N refs) and the charts (charts.js reads it).
        months = json.dumps(i18n.get(lang).get("months") or [],
                            ensure_ascii=False, separators=(",", ":"))
        (d / f"{lang}.js").write_text(
            f"window.__i18n={payload};"
            f"window.__cmonths={months};"
            f"window.__lang={json.dumps(lang)};"
            f"window.__dir={json.dumps(i18n.direction(lang))};\n",
            encoding="utf-8")
        n += 1
    return n
