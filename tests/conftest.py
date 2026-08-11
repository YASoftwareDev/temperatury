import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def build(location: str, langs: str, client_i18n: bool) -> Path:
    """Build one city (offline) the client-i18n (default) or legacy server way;
    return output/. client_i18n=False drives the TEMPERATURY_SERVER_I18N escape
    hatch, which the parity tests use to render a server-side reference."""
    env = {**os.environ, "TEMPERATURY_OFFLINE": "1", "TEMPERATURY_LANGS": langs}
    env.pop("TEMPERATURY_SERVER_I18N", None)   # client-i18n is the default
    if not client_i18n:
        env["TEMPERATURY_SERVER_I18N"] = "1"   # opt into the legacy server render
    subprocess.run([sys.executable, "main.py", "--location", location],
                   cwd=ROOT, env=env, check=True, capture_output=True)
    return ROOT / "output"


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


def roster(out: Path, lang: str) -> dict:
    """The client-side roster view for ``lang``, mirroring charts.js
    __rosterData: base rows layered with the language's name overrides, and
    tier-aware URLs (same-folder when ``lang`` is one of the city's shells,
    else the first shell's folder)."""
    import json
    base = json.loads((out / "charts" / "_base.json").read_text("utf-8"))
    dpath = out / lang / "_delta.json"
    delta = json.loads(dpath.read_text("utf-8")) if dpath.exists() else {}
    over, rl = delta.get("n", {}), delta.get("r", {})
    rows = []
    for slug, lat, lon, z, k, r, cc, cn, shells in base["c"]:
        sh = shells.split(",") if shells else []
        url = (f"{slug}.html" if not sh or lang in sh
               else f"../{sh[0]}/{slug}.html")
        rows.append(dict(slug=slug, lat=lat, lon=lon, z=z, k=k, r=r, cc=cc,
                         cn=cn, n=over.get(slug, cn), s=url))
    by_slug = {x["slug"]: x for x in rows}
    return {"rows": rows, "aliases": base.get("a", []), "by_slug": by_slug,
            "rlabel": lambda key: rl.get(key, key)}
