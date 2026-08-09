# Client-side i18n (R1-hybrid) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop pre-rendering one HTML page per (city × language). Ship one pre-rendered shell per city (in its SEO language) plus a small per-language dictionary applied in the browser, so language count stops multiplying stored HTML.

**Architecture:** Every localized string becomes a keyed lookup — the same `window.__ci18n` + `T()` pattern `charts.js` already uses for chart labels, generalized to the whole page. The shell carries language-neutral structure, per-city numbers, and `data-i18n` keys; `output/i18n/<lang>.js` carries `window.__i18n = {key: localized}` (the merged translation table); a new `assets/i18n-runtime.js` walks `[data-i18n]` and fills text/attrs, filling `{var}` placeholders from per-element `data-i18n-vars`. One SEO language per city stays fully server-rendered for crawlers and no-JS; all other languages are applied client-side.

**Tech Stack:** Python 3.14 static generator (`report.py`, `main.py`, `i18n.py`), vanilla-JS runtime (`assets/charts.js` + new `assets/i18n-runtime.js`), Playwright (already installed) for parity tests, pytest (new; project has no test suite today).

---

## Background (why — measured 2026-07-20)

Full 32-language build of 2,194 cities: uncompressed published site **958 MB** (GitHub Pages limit is 1 GB, uncompressed). HTML is **82%** of that and scales as `cities × languages`. Full 5,335-city roster projects to **~1.78 GB** — over the cap. Per-page raw avg **24.2 KB**; per-language marginal cost today **~128 MB**.

R1-hybrid changes the per-language cost to **~24 KB** (one dictionary): full-roster HTML drops from ~1,460 MB to ~128 MB (one SEO language/city), full artifact ~1.78 GB → **~0.45 GB**, and it **removes language tiering entirely** (all cities, all languages) while making 100+ languages feasible (single-digit MB).

The mechanism already exists in miniature: `assets/charts.js` lines 17-27 define `T(s)` reading `window.__ci18n` (a `{english→localized}` map) and `window.__cmonths`. This plan generalizes it.

## The three-category split (the whole design in one table)

| Category | Varies by | Where it lives | Example |
|---|---|---|---|
| Static UI text | language only | `output/i18n/<lang>.js` (dict) | button labels, chart captions, reading guide, hero/analog/season **templates** |
| Per-city data | city only | shell HTML + `charts/<slug>.json` | trend `+0.32`, warmest year `2024`, the city's localized-name map, chart-label **recipes** |
| Composed strings | both | assembled in the browser | "By 2050, {city} feels like {analog}, +{d} °C warmer" |

Composed strings = a **template** (dict) filled with **vars** (shell). The shell keeps the server-rendered text as inner content (SEO/no-JS fallback); the client overwrites it for non-SEO languages.

## File structure

**Create:**
- `assets/i18n-runtime.js` — DOM localizer: walk `[data-i18n]`, fill text/attrs from `window.__i18n`, interpolate `data-i18n-vars`, set `<html lang dir>`, re-apply on language switch. One responsibility: apply a dictionary to the DOM.
- `i18ndict.py` — build `output/i18n/<lang>.js` = `window.__i18n = {merged translation table}`. One responsibility: serialize per-language dictionaries.
- `tests/__init__.py`, `tests/conftest.py`, `tests/test_i18n_parity.py`, `tests/test_i18n_dict_complete.py` — parity + completeness harness (project has no tests today).
- `pytest.ini` — register markers, testpaths.

**Modify:**
- `report.py` — `build_site` emits `data-i18n` keys + `data-i18n-vars` instead of pre-substituted strings (gated by a flag during rollout); add per-page `window.__cityNames` and `<script src="../i18n/<lang>.js">`; SEO head keeps only pre-rendered langs' hreflang.
- `assets/charts.js` — fold `__ci18n`/`T()` into the shared dict (chart-label recipes localized client-side); expose a re-render hook for language switch.
- `main.py` — call `i18ndict.build_lang_dicts`; render each city in its SEO language(s) only; sitemap lists pre-rendered URLs only.
- `langtier.py` — repurpose from storage-tiering to **SEO-tiering** (which languages get pre-rendered per city); default 1.

## Rollout strategy (non-negotiable: the site stays live at every step)

Parallel track, flag-gated, parity-proven, then cutover:

1. Phases 0-2 build the runtime + dict + prove one block (hero) at **byte-for-visible-text parity** behind `TEMPERATURY_CLIENT_I18N=1`. Default build path unchanged.
2. Phase 3 converts every localized surface, still flag-gated, parity-gated per surface.
3. Phases 4-5 add in-place switching + SEO tiering.
4. Phase 6 flips the default and deletes the per-language full render only after parity passes for all 32 languages.
5. Phase 7 adds languages beyond 32 to prove the payoff.

`TEMPERATURY_CLIENT_I18N` unset ⇒ today's behavior exactly. Set ⇒ shell + client i18n. This lets `main` stay deployable throughout.

---

## Phase 0: Parity harness (prove equivalence before changing anything)

**Files:**
- Create: `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_i18n_dict_complete.py`

- [ ] **Step 1: Register pytest**

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
markers =
    parity: client-i18n vs server-render output parity (needs a build)
    slow: renders pages via headless chromium
```

- [ ] **Step 2: Shared build fixture**

Create `tests/conftest.py`:

```python
import os, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

def _build(location: str, langs: str, client_i18n: bool):
    env = {**os.environ, "TEMPERATURY_OFFLINE": "1", "TEMPERATURY_LANGS": langs}
    if client_i18n:
        env["TEMPERATURY_CLIENT_I18N"] = "1"
    subprocess.run([sys.executable, "main.py", "--location", location],
                   cwd=ROOT, env=env, check=True, capture_output=True)

@pytest.fixture(scope="session")
def built_krakow():
    _build("krakow", "en,pl", client_i18n=False)
    return ROOT / "output"
```

- [ ] **Step 3: Dictionary completeness test (pure Python, fast)**

Create `tests/test_i18n_dict_complete.py`:

```python
import re
import i18n, i18ndict  # i18ndict created in Phase 1; this test fails until then

def test_every_lang_dict_covers_ui_keys():
    """Every language's dict must define every key the English dict defines,
    falling back to English text but never MISSING a key (a missing key would
    render an empty element client-side)."""
    en = i18ndict.merged_table("en")
    for lang in i18n.LANGUAGES:
        d = i18ndict.merged_table(lang)
        missing = [k for k in en if k not in d]
        assert not missing, f"{lang} dict missing keys: {missing[:10]}"
```

- [ ] **Step 4: Run — expect import failure (i18ndict not built yet)**

Run: `.venv/bin/python -m pytest tests/test_i18n_dict_complete.py -q`
Expected: FAIL (`ModuleNotFoundError: i18ndict`). This is the red state driving Phase 1.

- [ ] **Step 5: Commit**

```bash
git add pytest.ini tests/
git commit -m "test: add i18n parity harness scaffold"
```

---

## Phase 1: Client i18n runtime + per-language dictionary

**Files:**
- Create: `assets/i18n-runtime.js`, `i18ndict.py`
- Modify: `main.py` (call the dict builder), `report.py` (copy the new asset to `output/`)

- [ ] **Step 1: Write `i18ndict.merged_table` + emitter**

Create `i18ndict.py`. `merged_table(lang)` merges every per-language source currently scattered across `report.py` and the overlay modules into one flat `{key: str}`. Sources (all already exist): `i18n.get(lang)`, `captions.overlay({}, lang)`, `deephist.overlay({}, lang)`, `ranktext.overlay({}, lang)`, and the report-local tables `_HERO_I18N`, `_FS_LABEL`, `_RZ_LABEL` plus the season/KPI keys (already in `i18n_data`).

```python
"""Per-language dictionaries for client-side i18n (R1-hybrid).

merged_table(lang) is the single flat {key: localized} table that the browser
applies. It merges every per-language source the server used to bake into pages:
the base i18n table plus the caption/deephist/ranktext overlays and report.py's
hero/fullscreen/reset-zoom tables. build_lang_dicts writes one small JS file per
language (window.__i18n = {...}); a page includes only its language's file.
"""
from __future__ import annotations

import json
from pathlib import Path

import captions
import deephist
import i18n
import ranktext
from report import _FS_LABEL, _HERO_I18N, _RZ_LABEL


def _hero_flat(lang: str) -> dict:
    """report.py keeps hero/fs/rz strings in per-language dicts keyed by a short
    name; flatten them to namespaced keys the shell references as data-i18n."""
    out = {}
    for src, prefix in ((_HERO_I18N, "hero"), (_FS_LABEL, "fs"), (_RZ_LABEL, "rz")):
        block = src.get(lang) or src["en"]
        if isinstance(block, dict):
            for k, v in block.items():
                out[f"{prefix}_{k}"] = v
        else:  # _FS_LABEL/_RZ_LABEL are plain strings
            out[prefix] = block
    return out


def merged_table(lang: str) -> dict:
    """The full flat dictionary the browser applies for one language."""
    t: dict = {}
    t.update(i18n.get(lang))               # base UI + captions live here already
    t.update(captions.overlay({}, lang))   # chart captions
    t.update(deephist.overlay({}, lang))   # deep-history explainer
    t.update(ranktext.overlay({}, lang))   # ranking strings
    t.update(_hero_flat(lang))             # hero/fullscreen/reset-zoom
    return {k: v for k, v in t.items() if isinstance(v, str)}


def build_lang_dicts(output_dir: Path, languages: list[str]) -> int:
    """Write output/i18n/<lang>.js for each language. Returns count."""
    d = output_dir / "i18n"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for lang in languages:
        payload = json.dumps(merged_table(lang), ensure_ascii=False,
                             separators=(",", ":"))
        (d / f"{lang}.js").write_text(
            f"window.__i18n={payload};window.__lang={json.dumps(lang)};"
            f"window.__dir={json.dumps(i18n.direction(lang))};\n",
            encoding="utf-8")
        n += 1
    return n
```

- [ ] **Step 2: Verify the dict builder against the completeness test**

Run: `.venv/bin/python -m pytest tests/test_i18n_dict_complete.py -q`
Expected: PASS (every language covers English's keys, via English fallback in `i18n.get`).

- [ ] **Step 3: Measure a dict's real size (grounds the payoff claim)**

Run:
```bash
.venv/bin/python -c "import i18ndict,json; \
d=i18ndict.merged_table('pl'); \
print(len(d),'keys', len(json.dumps(d,ensure_ascii=False))//1024,'KB')"
```
Expected: ~250-320 keys, ~18-28 KB. Record it.

- [ ] **Step 4: Write the DOM runtime**

Create `assets/i18n-runtime.js`:

```javascript
/* Client-side i18n runtime (R1-hybrid). A page includes ../i18n/<lang>.js which
 * sets window.__i18n = {key: localized}. This walks [data-i18n] nodes and fills
 * textContent (or an attribute via data-i18n-attr), interpolating {var} from a
 * per-element data-i18n-vars JSON. Server-baked inner text stays as the SEO /
 * no-JS fallback; we only overwrite when the dict has the key. Generalises the
 * window.__ci18n + T() pattern already in charts.js from chart labels to the
 * whole page. */
(function () {
  function dict() { return window.__i18n || {}; }
  function fmt(tmpl, vars) {
    return tmpl.replace(/\{(\w+)\}/g, function (_, k) {
      return vars && k in vars ? vars[k] : "{" + k + "}";
    });
  }
  function localize(el, D) {
    var key = el.getAttribute("data-i18n");
    var s = D[key];
    if (s == null) return;                       // no key -> keep server text
    var vraw = el.getAttribute("data-i18n-vars");
    if (vraw) { try { s = fmt(s, JSON.parse(vraw)); } catch (e) {} }
    var attr = el.getAttribute("data-i18n-attr"); // e.g. aria-label / placeholder
    if (attr) { el.setAttribute(attr, s); }
    else if (el.getAttribute("data-i18n-html") === "1") { el.innerHTML = s; }
    else { el.textContent = s; }
  }
  function applyI18n(root) {
    var D = dict(), r = root || document;
    var nodes = r.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) localize(nodes[i], D);
    // Localised city name: window.__cityNames = {lang: name} baked per page.
    if (window.__cityNames && window.__lang) {
      var nm = window.__cityNames[window.__lang] || window.__cityNames.en;
      var h = document.getElementById("pagehead");
      if (nm && h && !/#as=/.test(location.hash)) h.textContent = nm;
    }
    if (window.__lang) document.documentElement.lang = window.__lang;
    if (window.__dir) document.documentElement.dir = window.__dir;
  }
  window.__applyI18n = applyI18n;
  if (document.readyState !== "loading") applyI18n();
  else document.addEventListener("DOMContentLoaded", function () { applyI18n(); });
})();
```

- [ ] **Step 5: Wire the builder + asset copy into main.py**

In `main.py`, next to the existing `write_page_js` / `write_cities_js` loop over languages, add a one-time dict build. Modify the per-language section (around `main.py:370`, the `for lang in i18n.LANGUAGES:` landing loop) to additionally call, ONCE before the loop:

```python
import i18ndict
n_dicts = i18ndict.build_lang_dicts(OUTPUT_DIR, i18n.LANGUAGES)
print(f"Wrote {n_dicts} language dictionaries to {OUTPUT_DIR / 'i18n'}.")
```

Ensure `assets/i18n-runtime.js` is copied to `output/` alongside `charts.js` (find the existing `shutil.copy(... 'charts.js' ...)` in `main.py`/`report.py` and copy `i18n-runtime.js` the same way).

- [ ] **Step 6: Build and verify the artifacts exist**

Run: `TEMPERATURY_OFFLINE=1 TEMPERATURY_LANGS=en,pl .venv/bin/python main.py --location krakow`
Then: `ls output/i18n/pl.js output/i18n-runtime.js && head -c 80 output/i18n/pl.js`
Expected: both files exist; `pl.js` starts `window.__i18n={`.

- [ ] **Step 7: Commit**

```bash
git add i18ndict.py assets/i18n-runtime.js main.py
git commit -m "feat: per-language i18n dictionaries + client-side DOM runtime"
```

---

## Phase 2: Convert the hero (proof of concept, flag-gated, parity-proven)

Goal: with `TEMPERATURY_CLIENT_I18N=1`, the hero renders identically to today after the runtime applies the dict. Prove it headless.

**Files:**
- Modify: `report.py` (the hero block in `_PAGE` + `build_site` substitution), `tests/test_i18n_parity.py`

- [ ] **Step 1: Add the flag and a keyed-attr helper in report.py**

Near the top of `build_site` (report.py ~line 636):

```python
import os
_CLIENT_I18N = bool(os.environ.get("TEMPERATURY_CLIENT_I18N"))

def _i18n_attr(key: str, vars: dict | None = None) -> str:
    """Emit data-i18n attributes for the runtime. Empty string when the flag is
    off, so the default build is byte-identical to today."""
    if not _CLIENT_I18N:
        return ""
    out = f' data-i18n="{key}"'
    if vars:
        out += " data-i18n-vars='" + json.dumps(vars, separators=(",", ":")) + "'"
    return out
```

- [ ] **Step 2: Key the hero "since 1940" line**

In `_PAGE`, the hero currently has (report.py ~line 197):

```html
    <p class="rh-meta">${hero_meta}</p>
    ${hero_pct}
```

`hero_meta` is `_hero_str(lang,"since").format(v="<b>+1.2 °C</b>")`. Convert to keep the baked text as fallback AND carry the key+var. Change the `_PAGE` line to:

```html
    <p class="rh-meta"${hero_meta_attr}>${hero_meta}</p>
    ${hero_pct}
```

In `build_site`, where `hero_meta` is computed (report.py ~line 652), add:

```python
hero_meta_attr = _i18n_attr("hero_since", {"v": f"<b>{_signed(_dt, 1)} °C</b>"})
```

Add `hero_meta_attr=hero_meta_attr` to the `_PAGE.substitute(...)` call (report.py ~line 825). Note the dict value for `hero_since` contains `{v}` and the runtime must inject HTML — set `data-i18n-html="1"` on this element by extending `_i18n_attr` with an `html=True` param, OR (simpler) strip the `<b>` and style via CSS. Use `data-i18n-html`:

```python
def _i18n_attr(key, vars=None, html=False):
    if not _CLIENT_I18N: return ""
    out = f' data-i18n="{key}"'
    if html: out += ' data-i18n-html="1"'
    if vars: out += " data-i18n-vars='" + json.dumps(vars, separators=(",", ":")) + "'"
    return out
```
and `hero_meta_attr = _i18n_attr("hero_since", {"v": ...}, html=True)`.

- [ ] **Step 3: Include the runtime + dict + city-names in the page**

The city page currently ends with `<script src="_page.js"></script>` (report.py ~line 303 region, added in commit 35d4ac4). When `_CLIENT_I18N`, also emit before it:

```html
  <script>window.__cityNames = ${city_names_json};</script>
  <script src="../i18n/${lang}.js"></script>
  <script src="../i18n-runtime.js"></script>
```

Add substitution vars: build `city_names_json` from the existing `_names` data for this slug across `languages` (small; sparse exonyms):

```python
from report import _local_name  # already in-module
city_names_json = json.dumps(
    {lg: _local_name(slug, lg, location.name) for lg in languages},
    ensure_ascii=False, separators=(",", ":")) if _CLIENT_I18N else "{}"
```
Gate the three script lines in `_PAGE` behind a `${i18n_head}` var that is `""` when the flag is off.

- [ ] **Step 4: Write the parity test**

Create `tests/test_i18n_parity.py`:

```python
import os, subprocess, sys
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

def _build(client):
    env = {**os.environ, "TEMPERATURY_OFFLINE": "1", "TEMPERATURY_LANGS": "en,pl"}
    if client: env["TEMPERATURY_CLIENT_I18N"] = "1"
    subprocess.run([sys.executable, "main.py", "--location", "krakow"],
                   cwd=ROOT, env=env, check=True, capture_output=True)

def _text(url, block, apply_wait=True):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http")
                 else r.continue_())
        pg.goto(url, wait_until="domcontentloaded")
        if apply_wait: pg.wait_for_timeout(300)
        t = pg.text_content(block); b.close(); return t

@pytest.mark.parity
@pytest.mark.slow
def test_hero_parity_pl():
    _build(client=False)
    server = _text((ROOT / "output/pl/krakow.html").as_uri(), ".rh-inner")
    _build(client=True)
    client = _text((ROOT / "output/pl/krakow.html").as_uri(), ".rh-inner")
    assert " ".join(client.split()) == " ".join(server.split())
```

- [ ] **Step 5: Run parity — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_i18n_parity.py::test_hero_parity_pl -q`
Expected: PASS (the client-applied Polish hero text equals the server-rendered Polish hero text). If it fails, the diff pinpoints the missing key/var.

- [ ] **Step 6: Commit**

```bash
git add report.py tests/test_i18n_parity.py
git commit -m "feat: client-i18n hero (flag-gated) with headless parity test"
```

---

## Phase 3: Convert every localized surface (recipe + full inventory)

Apply the Phase 2 recipe to every localized surface. Each is: (a) add `${..._attr}` to the `_PAGE` element, (b) compute the attr with `_i18n_attr(key, vars, html?)`, (c) pass it to `substitute`, (d) extend `test_i18n_parity.py` with a parity assertion for that block, (e) run, (f) commit. Static text (no vars) uses `_i18n_attr(key)`; the dict already holds the key.

**Complete inventory (data-i18n key ← current source):**

| Surface (`_PAGE`) | Key(s) | Vars (per-city) |
|---|---|---|
| `rh-eyebrow` (hero_range) | — | none — it's a year range (numbers); leave server-rendered |
| hero "since" | `hero_since` | `{v}` total warming |
| hero percentile (`rh-pct`) | `hero_faster` | `{pct}` |
| season line (`rh-pct`) | `sum_season`/`sum_month` | `{season}`/`{month}`, `{v}` |
| chips | `card_mean`,`card_warmest`,`card_coldest` | none (labels) |
| analog lines | `analog_line`,`analog_past` | `{city}`,`{analog}`,`{d}` |
| curyear strip | `cur_so_far` | `{year}`,`{day}`,`{month}`,`{v}`,`{d}` |
| share button | `share`,`share_copied` | none |
| news button | `extreme_weather` | none (label); the href stays server-built |
| reading guide | `guide_title`,`guide_body` | none |
| every `<figure>` caption | `cap_*` + `*_title` | title takes `{name}` = city (from `__cityNames`) |
| health headings | `health_heading`,`health_sub` | none |
| widgets | `range_title`,`record_title`,`cap_range`,`cap_records`,`year` | `{name}` |
| deep history | `deephist_title`,`deephist_body`,`deephist_record` | `{label}`,`{year}` |
| grid alias note | `grid_alias_note` | `{alias}`,`{city}` (already client-applied — unify) |
| footer / widget link | `footer`,`widget_label` | none |
| topbar map link / picker | `map_label`,`choose_city` | none |
| lang switch | `_lang_nav` → rebuild as in-place switch (Phase 4) | — |

**The `{name}` (city) var:** figure titles like `"..., {name}"` need the localized city name. The runtime already sets `window.__cityNames`; extend `applyI18n` so any `data-i18n-vars` referencing `{name}` is filled from `__cityNames[__lang]` automatically (add `name` to the vars object in `localize` before `fmt`).

- [ ] **Step 1: Extend the runtime to auto-provide `{name}`**

In `assets/i18n-runtime.js` `localize`, before `fmt`:

```javascript
    var vars = {};
    if (vraw) { try { vars = JSON.parse(vraw); } catch (e) {} }
    if (window.__cityNames && window.__lang && vars.name == null)
      vars.name = window.__cityNames[window.__lang] || window.__cityNames.en;
    s = fmt(s, vars);
```
(Drop the earlier inline `vraw` parse; use this unified block.)

- [ ] **Step 2..N: Convert each row above**

For each inventory row, apply the a-f recipe. Worked example (chips, static labels), in `_PAGE`:

```html
      <div class="rh-chip"><span${card_mean_attr}>${card_mean}</span><b>${mean} °C</b></div>
      <div class="rh-chip"><span${card_warmest_attr}>${card_warmest}</span><b>${warmest_year}</b></div>
      <div class="rh-chip"><span${card_coldest_attr}>${card_coldest}</span><b>${coldest_year}</b></div>
```
in `build_site`:
```python
card_mean_attr = _i18n_attr("card_mean")
card_warmest_attr = _i18n_attr("card_warmest")
card_coldest_attr = _i18n_attr("card_coldest")
```
and add the three to `substitute(...)`. Then extend the parity test with `.rh-chips` and run.

For `<figure>` captions, the captions are emitted by the `_fig`/`_titled` helpers (report.py ~line 676). Modify `_titled` to attach `data-i18n` on the `<strong class="fig-title">` (key = the title key, var `{name}`) and on the description span (key = the `cap_*` key), gated by `_CLIENT_I18N`. This converts all 16 figures in one helper change — verify with a parity assertion over `section.charts`.

- [ ] **Step final: Full-page parity for both languages**

Extend `test_i18n_parity.py` with a whole-`<main>` + hero parity test for `pl` (and a Cyrillic/RTL smoke: `ru`, `ar`) and run:

Run: `.venv/bin/python -m pytest tests/test_i18n_parity.py -q`
Expected: PASS — every visible text block matches the server-rendered language.

Commit after each converted surface (frequent commits), final commit:
```bash
git commit -am "feat: client-i18n covers all localized city-page surfaces (flag-gated, parity green)"
```

---

## Phase 4: In-place language switch (no navigation) + selection

Today the switcher navigates to `../<lang>/<slug>.html`. With client-i18n there is one shell, so switching = fetch `i18n/<lang>.js`, set `window.__i18n`, re-apply, re-localize charts.

**Files:** Modify `assets/i18n-runtime.js`, `assets/charts.js`, `report.py` (`_lang_nav`).

- [ ] **Step 1: Switch function in the runtime**

Add to `assets/i18n-runtime.js`:

```javascript
  window.__setLang = function (lang) {
    var s = document.createElement("script");
    s.src = "../i18n/" + lang + ".js";
    s.onload = function () {
      try { localStorage.setItem("temperatury.lang", lang); } catch (e) {}
      applyI18n();
      if (window.__relocalizeCharts) window.__relocalizeCharts();
    };
    document.head.appendChild(s);
  };
```

- [ ] **Step 2: Chart re-localization hook**

In `assets/charts.js`, the chart-label recipes must localize from the dict, not a pre-baked `__ci18n`. Expose `window.__relocalizeCharts` that re-runs `renderChart` for each live chart using the current `window.__i18n`. Port `localize_specs` (plots.py) label composition to JS: ship the per-chart **recipe** (label key + kwargs) in `charts/<slug>.json`, compose the label in `T()` from `window.__i18n[key]` + kwargs. (Recipe emission: add the specs to the shared per-city JSON in `main.py:_render_city` where `chart_i18n` is currently computed.)

- [ ] **Step 3: Rebuild `_lang_nav` as a switch button**

When `_CLIENT_I18N`, `_lang_nav` emits a `<select>` whose `onchange` calls `window.__setLang(this.value)` instead of navigating:

```python
opts.append(f'<option value="{code}"{sel}>{LANG_NAMES[code]}</option>')
# ...
return (f'<select class="lang-select" aria-label="{label}" '
        'onchange="if(this.value)window.__setLang(this.value)">'
        + "".join(opts) + "</select>")
```

- [ ] **Step 4: Initial language selection**

The shell is pre-rendered in its SEO language. On load, if the visitor's saved/preferred language differs and a dict exists, `__setLang` to it. Add to the runtime's DOMContentLoaded:

```javascript
    try {
      var want = localStorage.getItem("temperatury.lang");
      if (want && want !== window.__lang) window.__setLang(want);
    } catch (e) {}
```

- [ ] **Step 5: Headless switch test**

Add to `tests/test_i18n_parity.py`: load `en` shell, call `__setLang('pl')`, assert `.rh-inner` text equals the server-rendered `pl`. Run and commit.

---

## Phase 5: SEO tiering (which languages get pre-rendered) + head/hreflang/sitemap

**Files:** Modify `langtier.py` (repurpose), `report.py` (`_seo_head`), `main.py` (render loop + sitemap).

- [ ] **Step 1: Repurpose `langtier` to SEO-tiering**

Replace storage-tiering with `seo_languages_for(loc) -> list[str]`: the languages to PRE-RENDER for a city (default `["en"]` or the country's primary via the existing `COUNTRY_LANGS`, tunable by a `SEO_TIER` constant). All other languages are client-only. Keep the function name stable where `main.py` calls it.

```python
SEO_PRERENDER = 1  # languages pre-rendered per city (for crawlers/no-JS)

def seo_languages_for(loc, site_langs):
    cc = countries.country_code(loc) or ""
    primary = [lg for lg in COUNTRY_LANGS.get(cc, ()) if lg in site_langs]
    ordered = (["en"] + primary) if "en" in site_langs else (primary or site_langs[:1])
    seen, out = set(), []
    for lg in ordered:
        if lg not in seen: seen.add(lg); out.append(lg)
    return out[:max(1, SEO_PRERENDER)] or [site_langs[0]]
```

- [ ] **Step 2: Render loop uses SEO languages**

In `main.py:_render_city`, replace the tiering language list with `seo_languages_for(location, i18n.LANGUAGES)` when `_CLIENT_I18N`. Each such page is a shell that can become any language client-side.

- [ ] **Step 3: hreflang lists only pre-rendered languages**

`_seo_head` currently emits `<link hreflang>` for all `languages`. When `_CLIENT_I18N`, pass only the city's pre-rendered languages (the crawlable URLs). Add `x-default` to the first.

- [ ] **Step 4: Sitemap lists shells only**

`main.py` sitemap glob already lists existing `*.html` — with SEO-tiering it naturally lists only pre-rendered shells. Verify count drops.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: SEO-tier pre-rendering + hreflang/sitemap for client-i18n"
```

---

## Phase 6: Cutover + measure

- [ ] **Step 1: Full parity sweep across all 32 languages**

Build one representative city both ways for every language; assert whole-`<main>` text parity per language (extend the harness to loop `i18n.LANGUAGES`). Run:
`.venv/bin/python -m pytest tests/ -q`
Expected: all PASS. **Do not proceed if any language differs.**

- [ ] **Step 2: Flip the default**

Make `_CLIENT_I18N` default **on** (invert the flag: `TEMPERATURY_SERVER_I18N` to opt back into the old path). Update CI (`.github/workflows`) env if it pins anything.

- [ ] **Step 3: Full build + measure the win**

Run: `rm -rf output && TEMPERATURY_OFFLINE=1 heavy run -- .venv/bin/python main.py --all`
Then: `du -sm output && tar -C output -cf - . | gzip -6 | wc -c`
Expected: uncompressed **≈450 MB** at 2,194 cities (vs 958 MB). Record before/after.

- [ ] **Step 4: Remove dead code**

Delete storage-tiering leftovers in `langtier.py`, per-language duplication no longer used. Keep `write_page_js`/`_cities.js`. Commit.

- [ ] **Step 5: Deploy + verify live**

Push; after CI, verify a shell loads, switches language in-place, and Googlebot-fetch (`gh`/curl) sees the SEO language's text server-rendered.

---

## Phase 7: Unlock more languages (the payoff)

- [ ] **Step 1: Add a language as a dict only**

Add a new `i18n_data/<code>.json` (e.g. a 33rd language) and its `LANG_NAMES` entry; do **not** add per-city rendering. Build and confirm: `output/i18n/<code>.js` exists, the switcher lists it, a page localizes to it client-side — with **zero** new per-city HTML.

- [ ] **Step 2: Document the "add a language" procedure**

Append to `README.md`: adding a language = one `i18n_data/<code>.json` + `LANG_NAMES` entry; no rebuild of city pages; storage cost ~24 KB.

- [ ] **Step 3: Commit**

```bash
git commit -am "docs: adding a language is now one dictionary file (~24 KB)"
```

---

## Risks & mitigations

- **SEO for client-only languages** (the big one): only the pre-rendered SEO language(s) per city are strongly indexed. Mitigation: `SEO_PRERENDER` is tunable — set to 3-5 to pre-render the top languages per city for SEO while the long tail is client-only. This trades the storage/SEO axis explicitly.
- **No-JS / crawler baseline:** the SEO language is fully server-rendered; the page is readable and indexed without JS. Only language *switching* needs JS.
- **Flash of SEO-language before switch:** `__setLang` runs at DOMContentLoaded; brief. Mitigation: gate body visibility until first `applyI18n`, or accept the flash (content is correct, just in the SEO language momentarily).
- **Inflected-language grammar in composed sentences:** same limitation as today's server templates (the analog/season sentences already substitute names) — no regression; noted in the alias work.
- **Chart-label recipe port (Phase 4 Step 2):** the riskiest single task; keep the server `localize_specs` as the source of truth and mirror its formatting exactly in JS, with a unit test comparing a sample of composed labels server-vs-JS.
- **Missing dict key ⇒ empty element:** prevented by `test_i18n_dict_complete` (Phase 0) running in CI and by the runtime's "no key ⇒ keep server text" fallback.

## Self-review

- **Spec coverage:** the three-category split, per-language dict, DOM runtime, hero POC, full-surface conversion, in-place switch, SEO tiering, cutover, and the "add a language" payoff each map to a phase. ✓
- **Placeholder scan:** new components (`i18ndict.py`, `i18n-runtime.js`, tests) have complete code; the repetitive per-surface conversions are given as an exact recipe + a worked example + a complete key inventory (not "similar to above" — the recipe is the same four edits per row). ✓
- **Type/name consistency:** `merged_table`/`build_lang_dicts` (i18ndict), `window.__i18n`/`__lang`/`__dir`/`__cityNames`/`__applyI18n`/`__setLang`/`__relocalizeCharts` (runtime), `_i18n_attr`/`_CLIENT_I18N` (report), `seo_languages_for`/`SEO_PRERENDER` (langtier) are used consistently across phases. ✓
- **Gap flagged:** Phase 4 Step 2 (chart-label recipe → JS) is the one task whose exact code depends on porting `plots.localize_specs`; it is scoped with its own parity unit test rather than left implicit.
