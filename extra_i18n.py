"""Layer machine-translated dashboard strings under a curated per-language table.

Several modules (globaltext, captions, deephist, ranktext) keep their own
`{lang: {key: value}}` tables of map/dashboard strings, hand-translated for the
original languages only. When the site grew to 132 languages, every new language
fell back to English for zone names, chart captions, the deep-history note and
the ranking text. This loads machine translations for exactly those gaps from
`i18n_data/_dashboard_mt.json` and merges them in with `setdefault`, so a curated
string always wins and English remains the final fallback.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_MT_FILE = Path(__file__).resolve().parent / "i18n_data" / "_dashboard_mt.json"
# The MT generator sets this so the module tables stay CURATED-only while it
# computes what still needs translating (otherwise it would see its own prior
# output as "already covered" and regenerate nothing).
if os.environ.get("TEMPERATURY_SKIP_EXTRA_I18N"):
    _MT: dict = {}
else:
    try:
        _MT = json.loads(_MT_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _MT = {}


def fill(table: dict, module: str) -> None:
    """Add the machine-translated (lang, key) pairs a curated table lacks.

    Never overrides an existing curated value and never touches English."""
    for lang, kv in _MT.get(module, {}).items():
        dest = table.setdefault(lang, {})
        for key, value in kv.items():
            dest.setdefault(key, value)


def fill_flat(table: dict, module: str) -> None:
    """Same as ``fill`` for a flat ``{lang: value}`` table (one string per
    language), e.g. ranktext's ranking note."""
    for lang, value in _MT.get(module, {}).items():
        table.setdefault(lang, value)
