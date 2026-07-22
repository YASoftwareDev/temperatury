"""Machine-translate the map-UI strings that live only as inline English defaults.

build_map_page looks these up with `tr.get("<key>", "<english>")`, but the keys
were never added to any i18n table, so the dot quick-view popup, the base-map
switcher, the data-coverage overlay and a couple of labels render English in
EVERY language. This extracts their English source straight from report.py (so
there is a single source of truth), machine-translates them into every other
language, and writes `i18n_data/_mapui.json` = `{lang: {key: value}}` with an
`en` block. i18n.get() layers this in, so `tr.get(...)` then finds the localized
string with no call-site change.

Usage: .venv/bin/python tools/gen_mapui.py
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import i18n  # noqa: E402
from tools.gen_mt_langs import _protect, _restore, _translate_batch  # noqa: E402
from tools.fill_missing_keys import GCODE  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

OUT = ROOT / "i18n_data" / "_mapui.json"
# The keys build_map_page looks up with an inline English default.
_KEYS = [
    "lookup_searching", "lookup_loading", "lookup_notfound", "lookup_error",
    "lookup_short", "lookup_since", "lookup_perdec", "lookup_warmtrend",
    "lookup_cooltrend", "lookup_faster", "lookup_cooling", "lookup_busy",
    "grid_toggle", "grid_all", "grid_some", "grid_none", "grid_tip",
    "basemap_label", "basemap_map", "basemap_terrain", "basemap_atlas",
    "basemap_sat", "rank_people", "rank_legend",
    # appearance panel (assets/appearance.js, via window.__tpref)
    "pref_title", "pref_note", "pref_close", "pref_theme", "pref_light",
    "pref_dark", "pref_style", "pref_style_objective", "pref_style_editorial",
    "pref_style_product", "pref_style_atlas", "pref_accent", "pref_headline",
    "pref_sans", "pref_serif", "pref_density", "pref_comfortable",
    "pref_compact", "pref_header", "pref_plain", "pref_tint",
    "pref_acc_cobalt", "pref_acc_red", "pref_acc_teal", "pref_acc_forest",
    "pref_acc_amber", "pref_acc_slate",
    # topbar warming badge (assets/charts.js, via window.__tpref)
    "hb_world", "hb_since", "hb_title",
]


def _extract_english() -> dict:
    """Pull each key's inline English default out of report.py, the source of
    truth, so this generator can never drift from what the code actually ships.

    Uses ast so multi-line implicitly-concatenated string defaults are captured
    whole (a single ast.Constant)."""
    tree = ast.parse((ROOT / "report.py").read_text(encoding="utf-8"))
    want = set(_KEYS)
    en: dict = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and len(node.args) == 2
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[1], ast.Constant)):
            key = node.args[0].value
            if key in want and key not in en:
                en[key] = node.args[1].value
    missing = want - set(en)
    if missing:
        raise SystemExit(f"could not find English defaults for: {sorted(missing)}")
    return {k: en[k] for k in _KEYS}


def _translate(g_code: str, en: dict) -> dict:
    tr = GoogleTranslator(source="en", target=g_code)
    items = list(en.items())
    protected, tokmaps = [], []
    for _k, v in items:
        p, toks = _protect(v)
        protected.append(p); tokmaps.append(toks)
    translated = _translate_batch(tr, protected)
    out = {}
    for (k, v), tr_s, toks in zip(items, translated, tokmaps):
        r = _restore(tr_s, toks) if tr_s is not None else None
        out[k] = r if r else v
    return out


def main():
    en = _extract_english()
    result = {"en": en}
    targets = [lg for lg in i18n.LANGUAGES if lg != "en"]
    print(f"{len(targets)} languages x {len(en)} map-UI keys")
    for i, lg in enumerate(targets, 1):
        for attempt in range(3):
            try:
                result[lg] = _translate(GCODE.get(lg, lg), en)
                break
            except Exception as e:
                print(f"  {lg}: attempt {attempt+1} failed: {e}")
        else:
            result[lg] = dict(en)
        if i % 20 == 0 or i == len(targets):
            print(f"  {i}/{len(targets)} ({lg})")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"DONE: wrote {OUT}")


if __name__ == "__main__":
    main()
