"""Machine-translate the module-local dashboard/UI tables into every new language.

globaltext/captions/deephist/ranktext and report (hero + button labels) keep
hand-translated per-language tables covering only the original languages. This
fills the gap for every other site language and writes
`i18n_data/_dashboard_mt.json` = `{table: {lang: value}}`, which `extra_i18n.fill`
/ `fill_flat` merge in UNDER the curated tables. Placeholders and the
(non-repeating) HTML tags in these strings are protected exactly as in
gen_mt_langs; a string that loses a placeholder keeps its English source.

Targets are computed PER TABLE (a language curated in one table may still be
missing from another), so nothing curated is ever re-translated.

Usage: .venv/bin/python tools/gen_dashboard_mt.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Keep the module tables CURATED-only while we compute what needs translating -
# the modules call extra_i18n.fill() at import, which would otherwise make every
# MT language look "already covered" and this generator regenerate nothing. Must
# be set BEFORE importing the modules below.
os.environ["TEMPERATURY_SKIP_EXTRA_I18N"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402
import globaltext, captions, deephist, ranktext, report  # noqa: E402
from tools.gen_mt_langs import _protect, _restore, _translate_batch  # noqa: E402
from tools.fill_missing_keys import GCODE  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "i18n_data" / "_dashboard_mt.json"

# {lang: {key: value}} tables.
TABLES = {
    "globaltext": globaltext._TEXT,
    "captions": captions._CAPTIONS,
    "deephist": deephist._TEXT,
    "ranktext": ranktext._TEXT,
    "hero": report._HERO_I18N,
}
# Flat {lang: string} tables -> (english-key-label, table).
_FLAT = {
    "ranktext_note": ("rank_note", ranktext._NOTE),
    "fs_label": ("fs_label", report._FS_LABEL),
    "rz_label": ("rz_label", report._RZ_LABEL),
    "widget_label": ("widget_label", report._WIDGET_LABEL),
    "lang_label": ("lang_label", report._LANG_LABEL),
}


def _translate_items(g_code: str, en_items: list[tuple[str, str]]) -> dict:
    tr = GoogleTranslator(source="en", target=g_code)
    protected, tokmaps = [], []
    for _k, v in en_items:
        p, toks = _protect(v)
        protected.append(p); tokmaps.append(toks)
    translated = _translate_batch(tr, protected)
    out: dict[str, str] = {}
    for (k, v), tr_s, toks in zip(en_items, translated, tokmaps):
        r = _restore(tr_s, toks) if tr_s is not None else None
        out[k] = r if r else v          # placeholder-safe: broken -> English
    return out


def _with_retry(g_code, en_items, label):
    for attempt in range(3):
        try:
            return _translate_items(g_code, en_items)
        except Exception as e:
            print(f"  {label}: attempt {attempt+1} failed: {e}")
            time.sleep(2 * (attempt + 1))
    return {k: v for k, v in en_items}       # English fallback


def main():
    result: dict = {}
    for name, table in TABLES.items():
        result[name] = {}
        en = {k: v for k, v in table["en"].items() if isinstance(v, str)}
        # Per (lang, key): a curated block may be PARTIAL (present with some keys
        # but missing others), so translate whatever a language still lacks - not
        # just entirely-absent languages.
        n = 0
        for lg in i18n.LANGUAGES:
            if lg == "en":
                continue
            have = table.get(lg, {})
            miss = [(k, en[k]) for k in en if k not in have]
            if miss:
                result[name][lg] = _with_retry(GCODE.get(lg, lg), miss, f"{lg}/{name}")
                n += 1
        print(f"{name}: filled {n} languages (missing keys)")
    for fname, (fkey, ftbl) in _FLAT.items():
        result[fname] = {}
        miss = [lg for lg in i18n.LANGUAGES if lg != "en" and lg not in ftbl]
        print(f"{fname}: {len(miss)} languages x 1 key")
        for lg in miss:
            result[fname][lg] = _with_retry(GCODE.get(lg, lg),
                                            [(fkey, ftbl["en"])], f"{lg}/{fname}")[fkey]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"DONE: wrote {OUT}.")


if __name__ == "__main__":
    main()
