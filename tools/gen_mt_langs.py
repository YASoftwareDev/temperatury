"""Machine-translate the UI strings into every Google-Translate language.

One-off scaffolding to widen language coverage: reads the English table, protects
{placeholders}/HTML tags, translates via the free Google endpoint in aligned
chunks, restores, and writes i18n_data/<code>.json. Resumable (skips codes whose
JSON already exists) and safe (any string that loses a placeholder in translation
keeps its English source, so a template never breaks). These are MACHINE
translations - flagged with "_mt": true - and want native review.

Usage: .venv/bin/python tools/gen_mt_langs.py [--only code,code] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import langcodes
from deep_translator import GoogleTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "i18n_data"
EN = i18n.get("en")
KEYS = [k for k, v in EN.items() if isinstance(v, str) and k not in ("html_lang", "dir")]

# Protect {placeholders}, {name:.1f} specs, and HTML tags from the translator.
_TOKEN = re.compile(r"\{[^}]*\}|<[^>]+>")
_MAXCHARS = 4500   # Google's hard limit is 5000; leave margin for expansion


def _protect(s: str):
    toks: list[str] = []
    def sub(m):
        toks.append(m.group(0))
        return f"⟦{len(toks) - 1}⟧"   # ⟦N⟧
    return _TOKEN.sub(sub, s), toks


def _restore(s: str, toks: list[str]) -> str | None:
    # Tolerate spaces the MT may inject inside the sentinel.
    counts: Counter = Counter()

    def put(m):
        i = int(m.group(1))
        if i < len(toks):
            counts[i] += 1
            return toks[i]
        return m.group(0)
    s = re.sub(r"⟦\s*(\d+)\s*⟧", put, s)
    # Every sentinel must be restored EXACTLY once by index. Presence-of-token
    # is not enough: identical repeated tags (<li>, <b>) would mask a lost copy,
    # and a duplicated index would inject an extra tag - both must be rejected.
    if counts != Counter(range(len(toks))):
        return None
    if "⟦" in s or "⟧" in s:               # a mangled sentinel fragment survived
        return None
    # light spacing cleanup for the sentinel/MT artefacts
    s = re.sub(r"\s+([%.,;:!?)،؟])", r"\1", s)
    s = re.sub(r"([(+])\s+", r"\1", s)
    s = re.sub(r"  +", " ", s)
    return s.strip()


def _chunks(texts):
    cur, n = [], 0
    for t in texts:
        if cur and n + len(t) + 1 > _MAXCHARS:
            yield cur; cur, n = [], 0
        cur.append(t); n += len(t) + 1
    if cur:
        yield cur


def _translate_batch(tr: GoogleTranslator, protected: list[str]) -> list[str]:
    """Translate a list of protected strings, keeping alignment. Newline-join per
    chunk; if the line count comes back wrong, fall back to one-by-one."""
    out: list[str] = []
    for chunk in _chunks(protected):
        joined = "\n".join(chunk)
        try:
            res = tr.translate(joined).split("\n")
        except Exception:
            res = []
        if len(res) == len(chunk):
            out.extend(res)
        else:                              # misaligned -> per-string
            for one in chunk:
                for attempt in range(3):
                    try:
                        out.append(tr.translate(one)); break
                    except Exception:
                        time.sleep(1.5 * (attempt + 1))
                else:
                    out.append(one)        # give up -> protected form (kept EN on restore)
        time.sleep(0.4)
    return out


def _is_rtl(code: str) -> bool:
    try:
        return langcodes.Language.get(code).maximize().script in ("Arab", "Hebr", "Thaa", "Syrc", "Nkoo")
    except Exception:
        return False


def _autonym(code: str) -> str:
    try:
        n = langcodes.Language.get(code).autonym()
        return n[:1].upper() + n[1:] if n else code
    except Exception:
        return code


def gen_one(app_code: str, g_code: str) -> dict:
    tr = GoogleTranslator(source="en", target=g_code)
    protected, tokmaps = [], []
    for k in KEYS:
        p, toks = _protect(EN[k])
        protected.append(p); tokmaps.append(toks)
    translated = _translate_batch(tr, protected)
    out: dict[str, str] = {}
    kept_en = 0
    for k, tr_s, toks in zip(KEYS, translated, tokmaps):
        r = _restore(tr_s, toks)
        if r is None or not r:
            out[k] = EN[k]; kept_en += 1     # safety: broken/empty -> English
        else:
            out[k] = r
    out["_mt"] = True                        # machine-translated marker
    print(f"  {app_code}: {len(KEYS)} strings, {kept_en} kept EN (placeholder-safe)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    supported = GoogleTranslator(source="en", target="es").get_supported_languages(as_dict=True)
    # {english_name: g_code}. Normalise g_code to an app/BCP-47 code.
    norm = {"zh-CN": "zh", "iw": "he", "jw": "jv", "tl": "tl"}
    existing = set(i18n.LANGUAGES)
    targets = []
    for _name, g in sorted(supported.items()):
        app = norm.get(g, g)
        if app in existing or app in ("en",):
            continue
        if "-" in app and app not in ("zh-TW",):   # skip regional dupes except a couple
            continue
        targets.append((app, g))
    if args.only:
        want = set(args.only.split(","))
        targets = [(a, g) for a, g in targets if a in want]
    if args.limit:
        targets = targets[: args.limit]

    print(f"{len(targets)} new languages to translate (Google supports {len(supported)}).")
    done = 0
    for app, g in targets:
        p = DATA_DIR / f"{app}.json"
        if p.exists():
            print(f"  {app}: exists, skip"); continue
        for attempt in range(3):
            try:
                block = gen_one(app, g)
                p.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
                done += 1
                break
            except Exception as e:
                print(f"  {app}: attempt {attempt+1} failed: {e}")
                time.sleep(3 * (attempt + 1))
    print(f"DONE: wrote {done} new language files.")


if __name__ == "__main__":
    main()
