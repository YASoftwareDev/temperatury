"""Rebuild i18n.py's _EXTRA_LANGS block from every i18n_data/<code>.json.

Preserves the curated (code, native-name, dir) entries already in _EXTRA_LANGS
and appends one entry per newly-added language file, with the native name from
langcodes autonyms and RTL detected from the script. langcodes is used here at
generation time only, so i18n.py keeps no extra runtime dependency.
"""
from __future__ import annotations

import re
from pathlib import Path

import langcodes

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
import i18n  # noqa: E402


# Scripts where a language-menu label is conventionally title-cased AND the
# script is genuinely bicameral. Georgian (Geor) is excluded: it is effectively
# caseless and its Mtavruli "capital" form is wrong for a menu label.
_TITLECASE_SCRIPTS = {"Latn", "Cyrl", "Grek", "Armn"}


def autonym(code: str) -> str:
    try:
        lang = langcodes.Language.get(code)
        n = lang.autonym() or lang.display_name()
    except Exception:
        return code
    if not n:
        return code
    try:
        script = lang.maximize().script
    except Exception:
        script = None
    if script in _TITLECASE_SCRIPTS:
        return n[:1].upper() + n[1:]
    return n   # trust langcodes' own casing (CJK, Arabic, Georgian, Indic, ...)


def is_rtl(code: str) -> bool:
    try:
        return langcodes.Language.get(code).maximize().script in (
            "Arab", "Hebr", "Thaa", "Syrc", "Nkoo")
    except Exception:
        return False


def main():
    existing = [(c, n, d) for c, n, d in i18n._EXTRA_LANGS]      # curated, keep order
    have = {c for c, _, _ in existing}
    files = sorted(p.stem for p in (ROOT / "i18n_data").glob("*.json")
                   if not p.stem.startswith("_"))
    new = []
    for c in files:
        if c in have or c in ("en",):
            continue
        new.append((c, autonym(c), "rtl" if is_rtl(c) else "ltr"))
    new.sort(key=lambda t: t[1].casefold())
    allentries = existing + new
    print(f"{len(existing)} existing + {len(new)} new = {len(allentries)} extra languages")

    # Render the Python list block.
    lines = ["_EXTRA_LANGS = ["]
    for c, n, d in allentries:
        lines.append(f'    ({c!r}, {n!r}, {d!r}),')
    lines.append("]")
    block = "\n".join(lines)

    src = (ROOT / "i18n.py").read_text(encoding="utf-8")
    new_src = re.sub(r"_EXTRA_LANGS = \[.*?\n\]", block, src, count=1, flags=re.S)
    assert new_src != src and "_EXTRA_LANGS = [" in new_src
    (ROOT / "i18n.py").write_text(new_src, encoding="utf-8")
    print(f"rewrote _EXTRA_LANGS ({len(allentries)} entries). RTL: "
          + ", ".join(c for c, _, d in new if d == "rtl"))


if __name__ == "__main__":
    main()
