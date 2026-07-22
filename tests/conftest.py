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
