/* Client-side i18n runtime (R1-hybrid). A page includes ../i18n/<lang>.js which
 * sets window.__i18n = {key: localized}. This walks [data-i18n] nodes and fills
 * textContent (or an attribute via data-i18n-attr, or innerHTML via
 * data-i18n-html="1"), interpolating {var} from a per-element data-i18n-vars
 * JSON. Server-baked inner text stays as the SEO / no-JS fallback; a node is
 * only overwritten when the dict has its key. Generalises the window.__ci18n +
 * T() pattern already in charts.js from chart labels to the whole page. */
(function () {
  function dict() { return window.__i18n || {}; }
  function fmt(tmpl, vars) {
    return tmpl.replace(/\{(\w+)\}/g, function (_, k) {
      return vars && k in vars ? vars[k] : "{" + k + "}";
    });
  }
  function cityName() {
    // On an alias arrival (<primary>.html#as=<searched town>), the whole page
    // reads as the searched town, so {name} and the H1 must be the alias, not
    // the primary - otherwise charts.js relabels the H1 while keyed captions
    // snap back to the primary.
    var m = /[#&]as=([^&]*)/.exec(location.hash || "");
    if (m) {
      try { return decodeURIComponent(m[1].replace(/\+/g, " ")).trim(); }
      catch (e) {}
    }
    if (window.__cityNames && window.__lang)
      return window.__cityNames[window.__lang] || window.__cityNames.en;
    return null;
  }
  function resolveRefs(vars) {
    // A var value "@key" is resolved from the ACTIVE dict (so it follows the
    // language on switch), "@months.N" from the localized month array. Used for
    // month and season names, which are themselves translatable.
    var D = dict(), M = window.__cmonths || [];
    for (var k in vars) {
      var v = vars[k];
      if (typeof v !== "string" || v.charAt(0) !== "@") continue;
      var ref = v.slice(1);
      if (ref === "name") {
        var nm = cityName(); if (nm != null) vars[k] = nm;
      } else if (ref.indexOf("months.") === 0) {
        var i = parseInt(ref.slice(7), 10);
        if (M[i] != null) vars[k] = M[i];
      } else if (D[ref] != null) { vars[k] = D[ref]; }
    }
    return vars;
  }
  function localize(el, D) {
    var key = el.getAttribute("data-i18n");
    var s = D[key];
    if (s == null) return;                          // no key -> keep server text
    var vars = {};
    var vraw = el.getAttribute("data-i18n-vars");
    if (vraw) { try { vars = JSON.parse(vraw); } catch (e) {} }
    // {name} (the localized city name) is auto-provided so figure titles and
    // widget headings need not bake it per element.
    if (vars.name == null) { var nm = cityName(); if (nm != null) vars.name = nm; }
    s = fmt(s, resolveRefs(vars));
    var attr = el.getAttribute("data-i18n-attr");   // one or more, space-separated
    if (attr) { attr.split(/\s+/).forEach(function (a) { if (a) el.setAttribute(a, s); }); }
    else if (el.getAttribute("data-i18n-html") === "1") { el.innerHTML = s; }
    else { el.textContent = s; }
  }
  function applyI18n(root) {
    var D = dict(), r = root || document;
    var nodes = r.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) localize(nodes[i], D);
    // Localised city name in the H1 (cityName() already yields the alias on an
    // #as= arrival, matching the keyed captions).
    var nm = cityName(), h = document.getElementById("pagehead");
    if (nm && h) h.textContent = nm;
    // Live-news link: rebuild its Google News query in the active language (the
    // localized "extreme weather" phrase + hl), for the current city/alias - the
    // href is baked in the SEO language and would otherwise not follow a switch.
    var nb = document.querySelector("a[data-news]");
    if (nb) {
      var phrase = D.extreme_weather || "extreme weather";
      var city = nm || nb.getAttribute("data-city") || "";
      nb.setAttribute("href", "https://news.google.com/search?q="
        + encodeURIComponent('"' + city + '" ' + phrase)
        + "&hl=" + (window.__lang || "en"));
    }
    if (window.__lang) document.documentElement.lang = window.__lang;
    if (window.__dir) document.documentElement.dir = window.__dir;
  }
  window.__applyI18n = applyI18n;

  // Switch language in place (no navigation): load the dict, re-apply, re-render
  // charts. Used by the language <select>.
  window.__setLang = function (lang) {
    if (lang === window.__lang) return;
    window.__wantLang = lang;   // guard: rapid switches must land on the last pick
    var s = document.createElement("script");
    s.src = "../i18n/" + lang + ".js";
    s.onload = function () {
      if (window.__wantLang !== lang) return;   // superseded by a later switch
      try { localStorage.setItem("temperatury.lang", lang); } catch (e) {}
      applyI18n();
      if (window.__relocalizeCharts) window.__relocalizeCharts();
    };
    document.head.appendChild(s);
  };

  function boot() {
    applyI18n();
    // Honour a saved preference that differs from the pre-rendered SEO language.
    try {
      var want = localStorage.getItem("temperatury.lang");
      if (want && want !== window.__lang) window.__setLang(want);
    } catch (e) {}
  }
  if (document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
