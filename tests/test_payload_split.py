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
        assert f'window.__chartsBase = ["{BASE}"]' in html
        index = (ROOT / "output/en/index.html").read_text(encoding="utf-8")
        assert f'window.__chartsBase = ["{BASE}"]' in index
    finally:
        import shutil
        shutil.rmtree(ROOT / "payloads-test", ignore_errors=True)


def test_default_build_is_unsplit():
    _build("krakow", {})
    assert (ROOT / "output/charts/krakow.json").is_file()
    html = (ROOT / "output/en/krakow.html").read_text(encoding="utf-8")
    assert "window.__chartsBase = null" in html, \
        "unset knobs must fall back to the relative ../charts/ fetch"


def test_split_build_with_two_origins_bakes_the_list():
    pdir = "payloads-test2/charts"
    two = "https://a.test/charts/,https://b.test/charts/"
    _build("krakow", {"TEMPERATURY_PAYLOAD_DIR": pdir,
                      "TEMPERATURY_PAYLOAD_BASE": two})
    try:
        html = (ROOT / "output/en/krakow.html").read_text(encoding="utf-8")
        assert ('window.__chartsBase = ["https://a.test/charts/", '
                '"https://b.test/charts/"]') in html
    finally:
        import shutil
        shutil.rmtree(ROOT / "payloads-test2", ignore_errors=True)


def test_payload_shard_python_js_parity():
    """The browser resolver (window.__payloadBase) and report.payload_shard
    must agree for every slug, or a payload would be pushed to one origin and
    fetched from another. Pin the parity on real roster slugs, including the
    non-ASCII/parenthesised/comma shapes."""
    import config
    from playwright.sync_api import sync_playwright
    from report import payload_shard

    slugs = sorted(config.LOCATIONS)[::997]           # ~33 spread samples
    slugs += ["newcastle-(za)", "mianzhu,-deyang,-sichuan", "al'met'yevsk"]
    slugs = [s for s in slugs if s in config.LOCATIONS]
    js = """(slugs) => slugs.map(slug => {
      var u = unescape(encodeURIComponent(slug)), h = 5381;
      for (var i = 0; i < u.length; i++)
        h = (((h << 5) + h) + u.charCodeAt(i)) >>> 0;
      return h % 2;
    })"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            got = b.new_page().evaluate(js, slugs)
        finally:
            b.close()
    want = [payload_shard(s, 2) for s in slugs]
    assert got == want, [
        (s, w, g) for s, w, g in zip(slugs, want, got) if w != g][:5]
    # and the shards actually split the roster, not degenerate to one side
    all_shards = [payload_shard(s, 2) for s in config.LOCATIONS]
    frac = sum(all_shards) / len(all_shards)
    assert 0.4 < frac < 0.6, f"degenerate shard split: {frac:.2f}"


def test_shard_payloads_tool_is_idempotent(tmp_path):
    from report import payload_shard
    d = tmp_path / "charts"
    d.mkdir()
    names = ["krakow.json", "krakow_w.json", "nuuk.json", "tokyo.json"]
    for f in names:
        (d / f).write_text("{}")
    for _ in range(2):                       # second run must be a no-op
        subprocess.run([sys.executable, "tools/shard_payloads.py",
                        str(d), "2"], cwd=ROOT, check=True,
                       capture_output=True)
    for f in names:
        slug = f[:-7] if f.endswith("_w.json") else f[:-5]
        want = d / f"shard-{payload_shard(slug, 2)}" / f
        assert want.is_file(), f"{f} not in its shard dir"
    assert not list(d.glob("*.json")), "flat files left behind"
