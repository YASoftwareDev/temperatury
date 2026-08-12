"""The payload split: per-city chart JSON can build into a separate directory
and be fetched from a second Pages origin (TEMPERATURY_PAYLOAD_DIR/_BASE),
while meta files and, with the knobs unset, everything else stay exactly as
before. CI is the only intended user of the knobs; local builds and every
other test run unset."""
import json
import os
import subprocess
import sys

from tests.conftest import ROOT

BASE = "https://example.test/charts/"


def _build(slug: str, extra_env: dict) -> None:
    env = {**os.environ, "TEMPERATURY_OFFLINE": "1", "TEMPERATURY_LANGS": "en",
           **extra_env}
    env.pop("TEMPERATURY_SERVER_I18N", None)
    subprocess.run([sys.executable, "main.py", "--location", slug],
                   cwd=ROOT, env=env, check=True, capture_output=True)


def test_split_build_separates_payloads_and_bakes_the_base(tmp_path):
    pdir = "payloads-test/charts"
    _build("krakow", {"TEMPERATURY_PAYLOAD_DIR": pdir,
                      "TEMPERATURY_PAYLOAD_BASE": BASE})
    try:
        assert (ROOT / pdir / "krakow.json").is_file(), \
            "the per-city payload should build into the payload dir"
        assert not (ROOT / "output/charts/krakow.json").exists(), \
            "the per-city payload must not also land in the site artifact"
        # Meta files stay on the main site.
        assert (ROOT / "output/charts/_global.json").is_file()
        assert (ROOT / "output/charts/_base.json").is_file()
        html = (ROOT / "output/en/krakow.html").read_text(encoding="utf-8")
        assert f'window.__chartsBase = "{BASE}"' in html
        index = (ROOT / "output/en/index.html").read_text(encoding="utf-8")
        assert f'window.__chartsBase = "{BASE}"' in index
    finally:
        import shutil
        shutil.rmtree(ROOT / "payloads-test", ignore_errors=True)


def test_default_build_is_unsplit():
    _build("krakow", {})
    assert (ROOT / "output/charts/krakow.json").is_file()
    html = (ROOT / "output/en/krakow.html").read_text(encoding="utf-8")
    assert "window.__chartsBase = null" in html, \
        "unset knobs must fall back to the relative ../charts/ fetch"
