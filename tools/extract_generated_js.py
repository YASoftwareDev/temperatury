#!/usr/bin/env python3
"""Collect the JavaScript a build GENERATES into one directory a JS linter can read.

Linting ``assets/*.js`` covers only part of the client-side code. The rest is
emitted from Python - the per-language runtimes (``_page.js``, ``_citybody.js``)
and the inline ``<script>`` blocks that report.py writes into each page - and a
linter pointed at the source tree never sees any of it. That blind spot is not
theoretical: it hid a dead helper (``qvSigned``) on every landing page, and it
works the other way too, reporting ``buildRange`` as unused because the only
caller lives in a Python string.

What comes out is one file per DISTINCT block, not per page. Every city page
carries the same generated script with different numbers in it, so blocks are
deduplicated by content hash: a full-roster build and this one-city build
produce the same set of files to lint. Blocks are written with the line breaks
they had, so a linter's line numbers point at the block, and the header comment
names the page it came from.

``type="application/json"`` and ``application/ld+json`` blocks are data, not
code, and are skipped - the landing page alone carries ~50 KB of them.

Usage:
    python tools/extract_generated_js.py output /tmp/generated-js
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import Path

# Non-greedy, and it must not swallow a block that merely LINKS a script: those
# carry no body to lint.
_SCRIPT = re.compile(
    r'<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>', re.S | re.I)
_TYPE = re.compile(r'\btype\s*=\s*"([^"]+)"', re.I)
_DATA_TYPES = ("application/json", "application/ld+json")


def _is_code(attrs: str) -> bool:
    m = _TYPE.search(attrs)
    return not (m and m.group(1).lower() in _DATA_TYPES)


def collect(build_dir: Path, out_dir: Path) -> tuple[int, int]:
    """Write every distinct generated script under ``build_dir`` into ``out_dir``.

    Returns (files written, pages scanned). The generated ``.js`` files are
    copied whole; ``assets/`` copies of them are skipped by name, since those
    are linted at their source and would only report the same finding twice.
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    assets = {p.name for p in Path("assets").glob("*.js")} if Path("assets").is_dir() else set()
    seen: set[str] = set()
    written = pages = 0

    for js in sorted(build_dir.rglob("*.js")):
        if js.name in assets:
            continue                      # linted at source, not here
        body = js.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha1(body.encode()).hexdigest()[:8]
        if digest in seen:
            continue
        seen.add(digest)
        (out_dir / f"{js.stem}_{digest}.js").write_text(
            f"// generated file: {js.relative_to(build_dir)}\n{body}", encoding="utf-8")
        written += 1

    for page in sorted(build_dir.rglob("*.html")):
        pages += 1
        html = page.read_text(encoding="utf-8", errors="replace")
        for attrs, block in _SCRIPT.findall(html):
            if not _is_code(attrs) or not block.strip():
                continue
            digest = hashlib.sha1(block.encode()).hexdigest()[:8]
            if digest in seen:
                continue
            seen.add(digest)
            (out_dir / f"{page.stem}_inline_{digest}.js").write_text(
                f"// inline <script> from: {page.relative_to(build_dir)}\n{block}",
                encoding="utf-8")
            written += 1

    return written, pages


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    build_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    if not build_dir.is_dir():
        print(f"no build at {build_dir}: run main.py first", file=sys.stderr)
        return 2
    written, pages = collect(build_dir, out_dir)
    print(f"{written} distinct generated scripts from {pages} pages -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
