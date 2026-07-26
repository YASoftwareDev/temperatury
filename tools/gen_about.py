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

Usage: .venv/bin/python tools/gen_about.py              # regenerate everything
       .venv/bin/python tools/gen_about.py --keys a5   # re-translate one item

``--keys`` merges into the existing file and re-translates only the items named,
which is what an edit to a single answer needs - a full run re-translates 130+
languages and rewrites strings nobody changed.
"""
from __future__ import annotations

import json
import re
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


_ENTITY_FIXES = [
    # Machine translation mangles HTML entities in predictable ways, and a broken
    # one renders as literal text ("& nbsp;") on the page. Repair the shapes seen
    # across the 130+ outputs rather than shipping visible markup.
    (re.compile(r"&\s*#\s*(\d+)\s*;"), r"&#\1;"),      # "& # 8211;"
    (re.compile(r"&(\d{3,5});"), r"&#\1;"),              # "&8211;" - lost the #
    (re.compile(r"&\s*nbsp\s*;", re.I), "&nbsp;"),       # "& nbsp;"
    (re.compile(r"&\u043d\u0431\u0441\u043f;"), "&nbsp;"),  # Cyrillic-transliterated &nbsp;
    (re.compile(r"(\d{4})\s*&\s*(\d{4})"), r"\1&#8211;\2"),  # "1961&1990": the en dash was eaten
]


def fix_entities(s: str) -> str:
    """Repair entities the translator broke. Idempotent, so it is safe to run
    over an already-clean string (and over the stored file, to heal old runs)."""
    for rx, rep in _ENTITY_FIXES:
        s = rx.sub(rep, s)
    return s


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
        out[k] = fix_entities(r) if r else v   # tag/placeholder-safe: broken -> English
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
    only = None
    if "--keys" in sys.argv:
        only = set(sys.argv[sys.argv.index("--keys") + 1].split(","))
        en_items = [(k, v) for k, v in en_items if k in only]
        if not en_items:
            raise SystemExit(f"no About items match {sorted(only)}")
    prev: dict = {}
    if only and OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    result: dict[str, dict] = {**prev}
    result["en"] = {**result.get("en", {}), **{k: v for k, v in en_items}}
    targets = [lg for lg in i18n.LANGUAGES if lg != "en"]
    print(f"Translating {len(en_items)} About strings into {len(targets)} languages "
          + (f"(keys: {sorted(only)})" if only else "..."))
    for n, lg in enumerate(targets, 1):
        got = _with_retry(GCODE.get(lg, lg), en_items, lg)
        result[lg] = {**result.get(lg, {}), **got} if only else got
        if n % 10 == 0 or n == len(targets):
            print(f"  {n}/{len(targets)} done ({lg})")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {OUT} ({len(result)} languages).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
