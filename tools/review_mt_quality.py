"""Back-translation audit of the machine-translated UI strings.

Machine translation fails in ways a placeholder check cannot see: a term of art
rendered literally, an imperative turned into a noun, a negation dropped. This
round-trips each translation back to English and reports the ones that come
back saying something different, so a human reviewer reads a short ranked list
instead of 126 languages.

It is a TRIAGE tool, not a verdict: a low score often just means the language
words the idea differently. Its output says "look here", never "this is wrong".

Usage: .venv/bin/python tools/review_mt_quality.py [--key region_reset] [--limit N]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.fill_missing_keys import GCODE  # noqa: E402
from deep_translator import GoogleTranslator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "i18n_data"   # overridable with --data-dir (audit another ref)

# English sources, kept here so the audit does not depend on import side effects.
SOURCES = {
    "region_reset": "📍 Use my location",
    "dyk.label": "Did you know?",
    "dyk.fastest_city": "{city} is warming fastest of all — {b}{v} °C{/b} per decade.",
    "dyk.over2": "{b}{n}{/b} of {total} cities have warmed more than {b}2 °C{/b} since 1940.",
    "dyk.avg_since": "The average city has warmed {b}{v} °C{/b} since 1940.",
    "dyk.faster_world": "{b}{pct}%{/b} of cities warm faster than the world-city average.",
    "dyk.fastest_country": "{country} is the fastest-warming country — {b}{v} °C{/b} per decade.",
}
_TOKEN = re.compile(r"\{[^}]*\}|[°%]|\d+")


def _norm(s: str) -> str:
    """Strip what a round trip is allowed to move: placeholders, digits, units,
    punctuation and case. What is left is the wording being judged."""
    s = _TOKEN.sub(" ", s or "")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return " ".join(s.lower().split())


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _values(key: str) -> dict:
    """{lang: translated} for one key, from wherever that key actually lives."""
    if key.startswith("dyk."):
        sub = key.split(".", 1)[1]
        mt = json.loads((DATA_DIR / "_dashboard_mt.json").read_text(encoding="utf-8"))
        return {lg: kv[sub] for lg, kv in mt.get("dyk", {}).items() if sub in kv}
    out = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        block = json.loads(path.read_text(encoding="utf-8"))
        if key in block:
            out[path.stem] = block[key]
    return out


def _back(code: str, text: str) -> str | None:
    for attempt in range(3):
        try:
            return GoogleTranslator(source=code, target="en").translate(text)
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2 * (attempt + 1))
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="region_reset", choices=sorted(SOURCES))
    ap.add_argument("--limit", type=int, default=0, help="only the first N languages")
    ap.add_argument("--data-dir", help="audit an i18n_data/ from elsewhere "
                                       "(e.g. one extracted from another ref)")
    ap.add_argument("--all", action="store_true", help="every key, not just one")
    ap.add_argument("--json", help="write the full result to this path, for a "
                                   "reviewer packet instead of a terminal read")
    args = ap.parse_args()
    if args.data_dir:
        global DATA_DIR
        DATA_DIR = Path(args.data_dir)

    if args.all or args.json:
        packet: dict = {}
        for key in sorted(SOURCES):
            en_k, vals_k = SOURCES[key], _values(key)
            langs_k = sorted(vals_k)[: args.limit or None]
            print(f"{key}: {len(langs_k)} languages", flush=True)
            for lg in langs_k:
                rt = _back(GCODE.get(lg, lg), vals_k[lg])
                packet.setdefault(lg, {})[key] = {
                    "en": en_k, "native": vals_k[lg], "back": rt,
                    "score": round(_similarity(en_k, rt), 3) if rt else None,
                }
        out = Path(args.json or "mt_review_packet.json")
        out.write_text(json.dumps(packet, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        flagged = sum(1 for kv in packet.values() for r in kv.values()
                      if r["score"] is not None and r["score"] < 0.45)
        print(f"\nwrote {out} - {len(packet)} languages, {flagged} entries under 0.45")
        return

    en = SOURCES[args.key]
    vals = _values(args.key)
    langs = sorted(vals)[: args.limit or None]
    print(f"# {args.key}\n# EN: {en}\n# languages: {len(langs)}\n")

    rows, failed = [], []
    for lg in langs:
        rt = _back(GCODE.get(lg, lg), vals[lg])
        if rt is None:
            failed.append(lg)
            continue
        rows.append((_similarity(en, rt), lg, vals[lg], rt))
    rows.sort()

    print(f"{'score':>6}  {'lang':<7} back-translation")
    print("-" * 78)
    for score, lg, native, rt in rows:
        print(f"{score:6.2f}  {lg:<7} {rt}")
        if score < 0.45:
            print(f"{'':6}  {'':<7} native: {native}")
    if failed:
        print(f"\nback-translation unavailable for: {', '.join(failed)}")
    weak = [r for r in rows if r[0] < 0.45]
    print(f"\n{len(weak)} of {len(rows)} scored under 0.45 - review these first.")


if __name__ == "__main__":
    main()
