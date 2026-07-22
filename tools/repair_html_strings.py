"""Repair machine-translated strings whose HTML markup got corrupted.

The batch translator protects whole `<tag>`s with sentinels, but a string with
several identical tags (guide_body's many <li>/<b>, the footer's two <a>) can
lose one copy while an identical tag masks the loss - shipping broken markup or
a raw sentinel fragment. This re-translates only the affected (file, key) pairs
with a TAG-SAFE method: split the English source on its tags, translate only the
prose runs (protecting {placeholders} and &entities;), and reassemble with the
original tags byte-for-byte. A prose run whose placeholder can't be restored
keeps its English text, so a tag is never emitted broken.

Usage: .venv/bin/python tools/repair_html_strings.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402
from tools.gen_mt_langs import EN, _restore, _translate_batch  # noqa: E402
from tools.fill_missing_keys import GCODE  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "i18n_data"
TAG = re.compile(r"<[^>]+>")
SENTINEL = re.compile(r"⟦|⟧")
# Protect {placeholders} and &entities; inside a prose run (tags already split out).
_SEG_TOKEN = re.compile(r"\{[^}]*\}|&[#a-zA-Z0-9]+;")


def _protect_seg(s: str):
    toks: list[str] = []

    def sub(m):
        toks.append(m.group(0))
        return f"⟦{len(toks) - 1}⟧"
    return _SEG_TOKEN.sub(sub, s), toks


def _translate_html_aware(tr: GoogleTranslator, source: str) -> str:
    parts = re.split(r"(<[^>]+>)", source)      # even idx = prose, odd idx = tag
    idxs = [i for i, p in enumerate(parts) if i % 2 == 0 and p.strip()]
    protected, tokmaps = [], []
    for i in idxs:
        p, toks = _protect_seg(parts[i])
        protected.append(p); tokmaps.append(toks)
    translated = _translate_batch(tr, protected)
    for j, i in enumerate(idxs):
        r = _restore(translated[j], tokmaps[j]) if j < len(translated) else None
        if not r:
            continue                            # keep the English prose run
        lead = parts[i][: len(parts[i]) - len(parts[i].lstrip())]
        trail = parts[i][len(parts[i].rstrip()):]
        parts[i] = lead + r + trail
    return "".join(parts)


def _is_broken(v: str, en: str) -> bool:
    # Ordered comparison: for HTML snippets the tag SEQUENCE matters (which <a>
    # wraps which text), so a reordered-but-same-set string is still broken.
    return bool(SENTINEL.search(v)) or TAG.findall(v) != TAG.findall(en)


def main():
    en = i18n.get("en")
    html_keys = [k for k, v in en.items()
                 if isinstance(v, str) and len(TAG.findall(v)) >= 2]
    print("HTML-rich keys:", html_keys)
    repaired = 0
    for p in sorted(DATA_DIR.glob("*.json")):
        code = p.stem
        if code.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        broken = [k for k in html_keys
                  if isinstance(d.get(k), str) and _is_broken(d[k], en[k])]
        if not broken:
            continue
        g = GCODE.get(code, code)
        try:
            tr = GoogleTranslator(source="en", target=g)
        except Exception as e:
            print(f"  {code}: cannot init translator ({e}); English-fallback")
            for k in broken:
                d[k] = en[k]
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            repaired += 1
            continue
        fixed = []
        for k in broken:
            new = _translate_html_aware(tr, en[k])
            if _is_broken(new, en[k]):          # still not clean -> full English
                new = en[k]
                fixed.append(f"{k}=EN")
            else:
                fixed.append(k)
            d[k] = new
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        repaired += 1
        print(f"  {code}: repaired {fixed}")
    print(f"DONE: repaired {repaired} files.")


if __name__ == "__main__":
    main()
