"""Machine-translate the About / "how this works" Q&A into every site language.

The About tab body (`report._ABOUT_QA`, plus its heading and intro) is authored
in English only. build_map_page renders the map page per language, so without a
translation the About tab would read English in all 130+ non-English builds.
This translates each question and answer (and the heading/intro) into every
language and writes `i18n_data/_about.json` = `{lang: {key: value}}` with an
`en` block. report._about_html layers it in, English per-item fallback.

The answers contain HTML (<a>, <strong>) and entities (&nbsp;, &#8202;); these
are protected exactly as in gen_mt_langs, and an item that loses a tag keeps its
English source (never a broken string).

Usage: .venv/bin/python tools/gen_about.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import i18n  # noqa: E402
import report  # noqa: E402
from tools.gen_mt_langs import _protect, _restore, _translate_batch  # noqa: E402
from tools.fill_missing_keys import GCODE  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

OUT = ROOT / "i18n_data" / "_about.json"


def _en_items() -> list[tuple[str, str]]:
    """(key, english) for the heading, intro, and each Q/A - the source of truth
    is report.py, so this can never drift from what the page renders."""
    items = [("heading", report._ABOUT_HEADING_EN),
             ("intro", report._ABOUT_INTRO_EN)]
    for i, (q, a) in enumerate(report._ABOUT_QA):
        items.append((f"q{i}", q))
        items.append((f"a{i}", a))
    return items


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
        out[k] = r if r else v          # tag/placeholder-safe: broken -> English
    return out


def _with_retry(g_code, en_items, label):
    for attempt in range(3):
        try:
            return _translate_items(g_code, en_items)
        except Exception as e:               # noqa: BLE001
            print(f"  {label}: attempt {attempt + 1} failed: {e}")
            time.sleep(2 * (attempt + 1))
    return {k: v for k, v in en_items}       # English fallback


def main() -> int:
    en_items = _en_items()
    result: dict[str, dict] = {"en": {k: v for k, v in en_items}}
    targets = [lg for lg in i18n.LANGUAGES if lg != "en"]
    print(f"Translating {len(en_items)} About strings into {len(targets)} languages ...")
    for n, lg in enumerate(targets, 1):
        result[lg] = _with_retry(GCODE.get(lg, lg), en_items, lg)
        if n % 10 == 0 or n == len(targets):
            print(f"  {n}/{len(targets)} done ({lg})")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {OUT} ({len(result)} languages).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
