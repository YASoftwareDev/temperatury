"""Fill only the MISSING translatable keys of existing i18n_data files via MT.

Some curated language files predate later-added UI strings (omni search, the
analog sentences, etc.) and have been relying on English-fallback layering.
This machine-translates only those absent keys and merges them in, never
touching a key the file already has - so curated strings are preserved and
only the English-fallback gaps get localized. Files gain "_mt_partial": true
to record that some keys are machine-filled.

Usage: .venv/bin/python tools/fill_missing_keys.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402
from tools.gen_mt_langs import EN, KEYS, _protect, _restore, _translate_batch  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "i18n_data"
# app-code -> Google target code where they differ
GCODE = {"he": "iw", "jv": "jw", "zh": "zh-CN"}


def main():
    need = [k for k in KEYS]
    filled = 0
    for p in sorted(DATA_DIR.glob("*.json")):
        code = p.stem
        if code.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        missing = [k for k in need if k not in d]
        if not missing:
            continue
        g = GCODE.get(code, code)
        try:
            tr = GoogleTranslator(source="en", target=g)
            protected, tokmaps = [], []
            for k in missing:
                pr, toks = _protect(EN[k])
                protected.append(pr); tokmaps.append(toks)
            translated = _translate_batch(tr, protected)
            added = 0
            for k, tr_s, toks in zip(missing, translated, tokmaps):
                r = _restore(tr_s, toks)
                d[k] = r if (r) else EN[k]
                added += 1
            d.setdefault("_mt_partial", True)
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
            filled += 1
            print(f"  {code}: filled {added} missing keys")
        except Exception as e:
            print(f"  {code}: FAILED {e}")
            time.sleep(2)
    print(f"DONE: filled {filled} files.")


if __name__ == "__main__":
    main()
