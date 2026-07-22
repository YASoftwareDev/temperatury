"""Embeddable climate-warming-ranking widget (weather.com style) + a builder.

Two static pages are produced under ``output/``:

* ``widget.html`` - a self-contained, iframe-embeddable ranking widget. It reads
  its options from the URL query (``?n=&country=&theme=&lang=&title=``), fetches
  the country ranking from the same-origin ``charts/_global.json`` (so it stays
  current with every build), and renders a compact, branded, theme-aware card
  that links back to the site. No external JS; flags come from flagcdn.
* ``embed.html`` - a builder where a visitor picks a size/options, sees a live
  preview, and copies the ``<iframe>`` snippet to paste on their own page.

Country names are localized in the browser via ``Intl.DisplayNames`` from the
ISO code, so one file serves every language.
"""

from __future__ import annotations

from pathlib import Path

SITE = "https://yasoftwaredev.github.io/temperatury/"

_WIDGET = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Climate warming ranking</title>
<style>
  :root { color-scheme: light dark;
    --bg:#fbfaf7; --card:#fff; --ink:#232220; --muted:#6f6c66; --line:#e6e3dc;
    --warm:#c0392b; --cool:#1f6feb; --hi:rgba(230,126,34,.16); }
  @media (prefers-color-scheme: dark) { :root {
    --bg:#17161a; --card:#201f24; --ink:#ece9e3; --muted:#9a968e; --line:#33313a;
    --warm:#f2765f; --cool:#6ea8ff; --hi:rgba(242,153,74,.18); } }
  :root[data-theme="dark"] { --bg:#17161a; --card:#201f24; --ink:#ece9e3;
    --muted:#9a968e; --line:#33313a; --warm:#f2765f; --cool:#6ea8ff;
    --hi:rgba(242,153,74,.18); }
  :root[data-theme="light"] { --bg:#fbfaf7; --card:#fff; --ink:#232220;
    --muted:#6f6c66; --line:#e6e3dc; --warm:#c0392b; --cool:#1f6feb;
    --hi:rgba(230,126,34,.16); }
  * { box-sizing:border-box; }
  html,body { margin:0; height:100%; }
  body { font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:transparent; color:var(--ink); }
  .cw { display:flex; flex-direction:column; height:100%; background:var(--card);
    border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  .cw-head { display:flex; align-items:baseline; gap:.4rem; padding:.55rem .7rem .4rem;
    border-bottom:1px solid var(--line); }
  .cw-head b { font-size:.9rem; }
  .cw-head span { font-size:.7rem; color:var(--muted); margin-inline-start:auto; white-space:nowrap; }
  .cw-list { flex:1; overflow-y:auto; }
  .cw-row { display:flex; align-items:center; gap:.5rem; padding:.4rem .7rem;
    text-decoration:none; color:inherit; border-bottom:1px solid var(--line); }
  .cw-row:last-child { border-bottom:0; }
  .cw-row:hover { background:var(--hi); }
  .cw-row.cw-hi { background:var(--hi); font-weight:600; }
  .cw-rank { width:1.9rem; text-align:end; color:var(--muted);
    font-variant-numeric:tabular-nums; font-size:.85rem; }
  .cw-flag { width:20px; height:15px; border-radius:2px; flex:0 0 auto;
    box-shadow:0 0 0 1px rgba(0,0,0,.14); object-fit:cover; }
  .cw-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .cw-val { font-variant-numeric:tabular-nums; white-space:nowrap; }
  .cw-val.warm { color:var(--warm); } .cw-val.cool { color:var(--cool); }
  .cw-foot { padding:.4rem .7rem; border-top:1px solid var(--line);
    font-size:.68rem; color:var(--muted); text-align:center; }
  .cw-foot a { color:inherit; text-decoration:none; }
  .cw-foot a:hover { text-decoration:underline; }
  .cw-err { padding:1rem; text-align:center; color:var(--muted); }
</style>
</head>
<body>
<div class="cw">
  <div class="cw-head"><b id="cw-title">Climate warming ranking</b>
    <span id="cw-sub">°C / decade, 1940-2025</span></div>
  <div class="cw-list" id="cw-list"><div class="cw-err">…</div></div>
  <div class="cw-foot"><a id="cw-brand" target="_blank" rel="noopener">Data: temperatury →</a></div>
</div>
<script>
(function () {
  var q = new URLSearchParams(location.search);
  var n = Math.max(1, Math.min(50, parseInt(q.get("n") || "8", 10) || 8));
  var hi = (q.get("country") || "").toLowerCase();
  var lang = (q.get("lang") || "en").split("-")[0];
  var theme = q.get("theme");
  if (theme === "light" || theme === "dark")
    document.documentElement.setAttribute("data-theme", theme);
  if (q.get("title")) document.getElementById("cw-title").textContent = q.get("title");
  var site = "SITE_URL";
  // Signed number, but a value rounding to zero shows a bare unsigned zero.
  function fs(v, dp) { var s = v.toFixed(dp); return parseFloat(s) === 0 ? (0).toFixed(dp) : (v > 0 ? "+" : "") + s; }
  var brand = document.getElementById("cw-brand");
  brand.href = site + "?utm_source=widget";
  var names = null;
  try { names = new Intl.DisplayNames([lang], { type: "region" }); } catch (e) {}
  function cname(cc) { var u = (cc || "").toUpperCase();
    if (names) { try { return names.of(u) || u; } catch (e) {} } return u; }
  var list = document.getElementById("cw-list");
  fetch("charts/_global.json").then(function (r) {
    if (!r.ok) throw 0; return r.json();
  }).then(function (d) {
    var cs = (d && d.countries) || [];
    if (!cs.length) throw 0;
    var rows;
    if (hi) {
      var idx = -1;
      for (var i = 0; i < cs.length; i++) if (cs[i].cc === hi) { idx = i; break; }
      if (idx < 0) rows = cs.slice(0, n);
      else { var s = Math.max(0, Math.min(idx - Math.floor((n - 1) / 2), cs.length - n));
        rows = cs.slice(s, s + n); }
    } else { rows = cs.slice(0, n); }
    list.innerHTML = "";
    rows.forEach(function (c) {
      var a = document.createElement("a");
      a.className = "cw-row" + (c.cc === hi ? " cw-hi" : "");
      a.href = site + "?utm_source=widget"; a.target = "_blank"; a.rel = "noopener";
      var rk = document.createElement("span"); rk.className = "cw-rank"; rk.textContent = "#" + c.rank;
      var fl = document.createElement("img"); fl.className = "cw-flag"; fl.loading = "lazy";
      fl.width = 20; fl.height = 15; fl.alt = ""; fl.src = "https://flagcdn.com/20x15/" + c.cc + ".png";
      var nm = document.createElement("span"); nm.className = "cw-name"; nm.textContent = cname(c.cc);
      var vl = document.createElement("span"); vl.className = "cw-val " + (c.t >= 0 ? "warm" : "cool");
      vl.textContent = fs(c.t, 2);
      a.appendChild(rk); a.appendChild(fl); a.appendChild(nm); a.appendChild(vl);
      list.appendChild(a);
    });
  }).catch(function () {
    list.innerHTML = '<div class="cw-err">Ranking unavailable</div>';
  });
})();
</script>
</body>
</html>
"""

_CITY_WIDGET = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>City warming widget</title>
<style>
  :root { color-scheme: light dark;
    --bg:#fbfaf7; --card:#fff; --ink:#232220; --muted:#6f6c66; --line:#e6e3dc;
    --warm:#c0392b; --cool:#1f6feb; }
  @media (prefers-color-scheme: dark) { :root {
    --card:#201f24; --ink:#ece9e3; --muted:#9a968e; --line:#33313a;
    --warm:#f2765f; --cool:#6ea8ff; } }
  :root[data-theme="dark"] { --card:#201f24; --ink:#ece9e3; --muted:#9a968e;
    --line:#33313a; --warm:#f2765f; --cool:#6ea8ff; }
  :root[data-theme="light"] { --card:#fff; --ink:#232220; --muted:#6f6c66;
    --line:#e6e3dc; --warm:#c0392b; --cool:#1f6feb; }
  * { box-sizing:border-box; }
  html,body { margin:0; height:100%; }
  body { font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:transparent; color:var(--ink); }
  .cw { display:flex; flex-direction:column; height:100%; background:var(--card);
    border:1px solid var(--line); border-radius:10px; overflow:hidden; text-decoration:none; color:inherit; }
  .cw-stripes { display:flex; flex:0 0 38%; min-height:48px; }
  .cw-stripes i { flex:1; }
  .cw-body { flex:1; padding:.55rem .8rem; display:flex; flex-direction:column; justify-content:center; }
  .cw-place { font-weight:700; font-size:1.05rem; line-height:1.15; overflow:hidden;
    text-overflow:ellipsis; white-space:nowrap; }
  .cw-fig { display:flex; align-items:baseline; gap:.25rem; margin:.05rem 0 0; }
  .cw-fig b { font-size:1.9rem; font-weight:700; color:var(--warm); line-height:1;
    font-variant-numeric:tabular-nums; }
  .cw-fig.cool b { color:var(--cool); }
  .cw-fig small { font-size:.72rem; color:var(--muted); }
  .cw-sub { font-size:.8rem; color:var(--muted); margin-top:.15rem; }
  .cw-foot { padding:.35rem .7rem; border-top:1px solid var(--line); font-size:.68rem;
    color:var(--muted); text-align:center; }
  .cw-err { padding:1rem; text-align:center; color:var(--muted); margin:auto; }
</style>
</head>
<body>
<a class="cw" id="cw" target="_blank" rel="noopener">
  <div class="cw-stripes" id="stripes"></div>
  <div class="cw-body" id="body"><div class="cw-err">...</div></div>
  <div class="cw-foot" id="foot">temperatury &rarr;</div>
</a>
<script>
(function () {
  var q = new URLSearchParams(location.search);
  var slug = (q.get("city") || "").toLowerCase();
  // Language chooses which localized city page the card links to; city pages
  // live at <site>/<lang>/<slug>.html, never at the site root.
  var lang = (q.get("lang") || "en").split("-")[0];
  if (!/^[a-z]{2}$/.test(lang)) lang = "en";
  var theme = q.get("theme");
  if (theme === "light" || theme === "dark")
    document.documentElement.setAttribute("data-theme", theme);
  var site = "SITE_URL";
  var card = document.getElementById("cw"), body = document.getElementById("body"),
      stripes = document.getElementById("stripes");
  function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  // Signed number, but a value rounding to zero shows a bare unsigned zero.
  function fs(v, dp) { var s = v.toFixed(dp); return parseFloat(s) === 0 ? (0).toFixed(dp) : (v > 0 ? "+" : "") + s; }
  // Warming-stripe colour (blue below the baseline, red above), matching the site.
  function scol(v) { var lo = -1.0, hi = 1.5, x = Math.max(lo, Math.min(hi, v)), a, b, k;
    if (x < 0) { k = (x - lo) / (0 - lo); a = [8, 48, 107]; b = [247, 247, 247]; }
    else { k = x / hi; a = [247, 247, 247]; b = [165, 15, 21]; }
    return "rgb(" + Math.round(a[0]+(b[0]-a[0])*k) + "," + Math.round(a[1]+(b[1]-a[1])*k)
      + "," + Math.round(a[2]+(b[2]-a[2])*k) + ")"; }
  if (!slug) { body.innerHTML = '<div class="cw-err">No city set</div>'; return; }
  card.href = site + lang + "/" + slug + ".html?utm_source=widget";
  fetch("charts/_global.json").then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (d) {
      var rk = (d && d.ranking) || [], e = null;
      for (var i = 0; i < rk.length; i++) if (rk[i].s === slug) { e = rk[i]; break; }
      if (!e) throw 0;
      var name = q.get("name") || e.n, warm = e.t >= 0;
      (e.st || []).forEach(function (v) {
        var s = document.createElement("i"); s.style.background = scol(v); stripes.appendChild(s); });
      body.innerHTML = '<div class="cw-place">' + esc(name) + '</div>'
        + '<div class="cw-fig' + (warm ? "" : " cool") + '"><b>' + fs(e.t, 2)
        + '</b><small>\\u00B0C / decade</small></div>'
        + '<div class="cw-sub">' + fs(e.dt, 1) + ' \\u00B0C since 1940</div>';
    }).catch(function () { body.innerHTML = '<div class="cw-err">City unavailable</div>'; });
})();
</script>
</body>
</html>
"""

_EMBED = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Embed the climate warming ranking widget</title>
<style>
  :root { color-scheme:light; --bg:#fbfaf7; --ink:#232220; --muted:#6f6c66;
    --line:#e6e3dc; --accent:#c0392b; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:960px; margin:0 auto; padding:2.5rem 1.5rem 4rem; }
  h1 { font-size:1.9rem; margin:0 0 .3rem; }
  p.lead { color:var(--muted); margin:.2rem 0 2rem; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:2rem; align-items:start; }
  @media (max-width:720px){ .grid { grid-template-columns:1fr; } }
  label { display:block; font-size:.85rem; color:var(--muted); margin:.9rem 0 .25rem; }
  select, input { font:inherit; font-size:.95rem; padding:.45rem .6rem; width:100%;
    border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--ink); }
  .row2 { display:flex; gap:.8rem; } .row2 > div { flex:1; }
  .preview { border:1px dashed var(--line); border-radius:10px; padding:1rem;
    display:flex; justify-content:center; background:#fff; min-height:200px; }
  textarea { width:100%; height:90px; font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    padding:.6rem; border:1px solid var(--line); border-radius:6px; margin-top:1rem;
    background:#fff; color:var(--ink); resize:vertical; }
  button { font:inherit; font-weight:600; margin-top:.6rem; padding:.5rem 1rem;
    border:0; border-radius:6px; background:var(--accent); color:#fff; cursor:pointer; }
  .hint { font-size:.8rem; color:var(--muted); margin-top:.4rem; }
  a { color:var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Embed a climate warming widget</h1>
  <p class="lead">Two live, auto-updating widgets: the country warming ranking, or a
     single city's warming stripes. Configure it, copy the snippet, paste it on your
     site. Free to use with attribution.</p>
  <div class="grid">
    <div>
      <label for="mode">Widget</label>
      <select id="mode">
        <option value="rank" selected>Country warming ranking</option>
        <option value="city">Single city</option>
      </select>
      <div id="cityfield" hidden>
        <label for="city">City</label>
        <input id="city" list="cities" autocomplete="off" placeholder="Type a city, e.g. Warsaw">
        <datalist id="cities"></datalist>
      </div>
      <label for="size">Size</label>
      <select id="size">
        <option value="300x150|3">Badge - 300 × 150 (top 3)</option>
        <option value="300x300|7" selected>Card - 300 × 300 (top 7)</option>
        <option value="300x520|14">Tall - 300 × 520 (top 14)</option>
        <option value="520x180|4">Wide - 520 × 180 (top 4)</option>
      </select>
      <div class="row2">
        <div><label for="theme">Theme</label>
          <select id="theme"><option value="auto">Auto</option>
            <option value="light">Light</option><option value="dark">Dark</option></select></div>
        <div><label for="lang">Language</label>
          <select id="lang"><option value="en">English</option><option value="pl">Polski</option>
            <option value="de">Deutsch</option><option value="fr">Français</option>
            <option value="es">Español</option></select></div>
      </div>
      <div id="countryfield">
        <label for="country">Highlight a country (optional)</label>
        <input id="country" placeholder="ISO code, e.g. pl, us, de - blank for the global top">
      </div>
      <textarea id="code" readonly></textarea>
      <button id="copy">Copy embed code</button>
      <div class="hint" id="hint"></div>
    </div>
    <div>
      <label>Live preview</label>
      <div class="preview"><iframe id="prev" title="preview" style="border:0"></iframe></div>
    </div>
  </div>
</div>
<script>
(function () {
  var SITE = "SITE_URL";
  var $ = function (id) { return document.getElementById(id); };
  var nameToSlug = {};   // localized/English name -> slug, for the city picker

  function mode() { return $("mode").value; }
  function opts() {
    var sz = $("size").value.split("|"); var wh = sz[0].split("x");
    var typed = ($("city").value || "").trim();
    return { w: +wh[0], h: +wh[1], n: sz[1], theme: $("theme").value, lang: $("lang").value,
      country: ($("country").value || "").trim().toLowerCase(),
      city: nameToSlug[typed.toLowerCase()] || typed.toLowerCase() };
  }
  function params(o) {
    var p, base;
    if (mode() === "city") {
      base = "citywidget.html"; p = ["city=" + encodeURIComponent(o.city), "lang=" + o.lang];
    } else {
      base = "widget.html"; p = ["n=" + o.n, "lang=" + o.lang];
      if (o.country) p.push("country=" + encodeURIComponent(o.country));
    }
    if (o.theme !== "auto") p.push("theme=" + o.theme);
    return { file: base, q: "?" + p.join("&") };
  }
  function code(o) {
    var pr = params(o);
    // Absolute URL so the snippet works on any page.
    return '<iframe src="' + SITE + pr.file + pr.q + '" width="' + o.w + '" height="' + o.h +
      '" style="border:0;overflow:hidden" loading="lazy" ' +
      'title="' + (mode() === "city" ? "City warming" : "Climate warming ranking") + '"></iframe>';
  }
  function refresh() {
    var isCity = mode() === "city";
    $("cityfield").hidden = !isCity;
    $("countryfield").hidden = isCity;
    var o = opts(), pr = params(o);
    $("prev").width = o.w; $("prev").height = o.h;
    $("prev").src = pr.file + pr.q;   // relative preview, same origin
    $("code").value = code(o);
  }
  ["mode", "size", "theme", "lang", "country", "city"].forEach(function (id) {
    $(id).addEventListener("input", refresh);
    $(id).addEventListener("change", refresh);
  });
  $("copy").addEventListener("click", function () {
    $("code").select();
    try { document.execCommand("copy"); } catch (e) {}
    if (navigator.clipboard) navigator.clipboard.writeText($("code").value).catch(function(){});
    $("hint").textContent = "Copied! Paste it into your page's HTML.";
  });
  // Deep-link support: a city page can open this builder pre-set to its city
  // (embed.html?mode=city&city=<slug>).
  var iq = new URLSearchParams(location.search);
  if (iq.get("mode") === "city") $("mode").value = "city";
  // Populate the city picker from the same ranking the widgets use.
  fetch("charts/_global.json").then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      var rk = (d && d.ranking) || [], dl = $("cities"), slugToName = {};
      rk.slice().sort(function (a, b) { return a.n.localeCompare(b.n); }).forEach(function (c) {
        nameToSlug[c.n.toLowerCase()] = c.s; slugToName[c.s] = c.n;
        var o = document.createElement("option"); o.value = c.n; dl.appendChild(o);
      });
      var want = (iq.get("city") || "").toLowerCase();
      if (want && slugToName[want]) $("city").value = slugToName[want];
      else if (!$("city").value && rk.length) $("city").value = rk[0].n;  // a valid default
      refresh();
    }).catch(function () {});
  refresh();
})();
</script>
</body>
</html>
"""


def build_widgets(output_dir: Path) -> int:
    """Write ``widget.html``, ``citywidget.html`` and ``embed.html``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "widget.html").write_text(
        _WIDGET.replace("SITE_URL", SITE), encoding="utf-8")
    (output_dir / "citywidget.html").write_text(
        _CITY_WIDGET.replace("SITE_URL", SITE), encoding="utf-8")
    (output_dir / "embed.html").write_text(
        _EMBED.replace("SITE_URL", SITE), encoding="utf-8")
    return 3
