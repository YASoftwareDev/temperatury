"""Scoped machine-translation fill for the "Use my location" reset label.

`region_reset` lives in i18n.py's TRANSLATIONS table, curated for the six core
languages only. Because `i18n.get()` layers every language over English FIRST,
a key already present in the English table can never be filled from the
`_mapui.json` side-table - the English value always wins. The only place a
long-tail translation for such a key takes effect is `i18n_data/<code>.json`.

So this fills exactly that one key into every long-tail language file, leaving
every other key untouched. Resumable: a file that already carries the key is
skipped, so an interrupted run just continues.

Usage: .venv/bin/python tools/fill_region_reset.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.fill_missing_keys import GCODE  # noqa: E402
from tools.gen_mt_langs import _protect, _restore  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "i18n_data"
KEY = "region_reset"
EN = "📍 Use my location"


def _translate(code: str, text: str) -> str | None:
    """Translate one string, preserving the leading emoji. The pin is part of
    the label's meaning, not words - it is stripped before translating and put
    back after, so no translator can drop or duplicate it."""
    emoji, body = "", text
    if text.startswith("📍"):
        emoji, body = "📍 ", text[1:].lstrip()
    protected, toks = _protect(body)
    out = None
    for attempt in range(3):
        try:
            out = GoogleTranslator(source="en", target=code).translate(protected)
            break
        except Exception as e:                       # network/quota flake
            if attempt == 2:
                print(f"  {code}: giving up ({e})")
                return None
            time.sleep(2 * (attempt + 1))
    if not out:
        return None
    restored = _restore(out, toks)
    return emoji + restored if restored else None


def main() -> None:
    files = sorted(DATA_DIR.glob("*.json"))
    filled = skipped = failed = 0
    for path in files:
        if path.name.startswith("_"):                # side tables, not languages
            continue
        code = path.stem
        block = json.loads(path.read_text(encoding="utf-8"))
        if KEY in block:
            skipped += 1
            continue
        value = _translate(GCODE.get(code, code), EN)
        if not value:
            failed += 1
            continue
        block[KEY] = value
        path.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        filled += 1
        print(f"  {code}: {value}")
    print(f"DONE: filled {filled}, already present {skipped}, failed {failed}.")


if __name__ == "__main__":
    main()
