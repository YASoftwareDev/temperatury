/* Appearance preferences: lets each visitor choose the site's look and keeps it.
   The look is driven entirely by data-* attributes on <html> (see the token
   system in page.css / landing.css). A tiny inline bootstrap in <head> applies
   the saved choice before first paint (no flash); this file adds the panel UI
   that changes it. On any change we persist to localStorage and dispatch a
   `themechange` event so charts.js re-colours the canvases.

   Axes:
     dir      objective | editorial | product | atlas   (layout + neutrals)
     accent   cobalt | red | teal | forest | amber | slate
     font     sans | serif                               (headline face)
     density  comfortable | compact
     hero     plain | tint | map
     theme    light | dark
   accent/font are only stored when the visitor overrides them; otherwise they
   follow the direction/base default. Picking a direction clears those overrides. */
(function () {
  "use strict";
  var KEY = "temperatury:appearance";
  var root = document.documentElement;

  /* Localized UI strings, baked per page as window.__tpref by report.py
     (_tpref_i18n). The inline English stays as the fallback for a page built
     before the map was injected. */
  function T(k, fb) {
    try { return (window.__tpref && window.__tpref[k]) || fb; }
    catch (e) { return fb; }
  }

  var DIRS = [
    ["objective", "pref_style_objective", "Objective"],
    ["editorial", "pref_style_editorial", "Editorial"],
    ["product", "pref_style_product", "Product"],
    ["atlas", "pref_style_atlas", "Atlas"]
  ];
  var ACCENTS = [
    ["cobalt", "#2f5fd0", "pref_acc_cobalt", "Cobalt"],
    ["red", "#d64541", "pref_acc_red", "Red"],
    ["teal", "#0f8a7e", "pref_acc_teal", "Teal"],
    ["forest", "#2f7d5b", "pref_acc_forest", "Forest"],
    ["amber", "#b9741a", "pref_acc_amber", "Amber"],
    ["slate", "#425a6e", "pref_acc_slate", "Slate"]
  ];

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; }
    catch (e) { return {}; }
  }
  function save(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) {} }
  var prefs = load();

  function osTheme() {
    return window.matchMedia && matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light";
  }
  function cur(axis, fallback) {
    if (axis === "theme") return prefs.theme || osTheme();
    if (axis === "dir") return prefs.dir || "objective";
    if (axis === "density") return prefs.density || "comfortable";
    if (axis === "hero") return prefs.hero || "tint";
    return prefs[axis] || fallback; /* accent/font: may be undefined = default */
  }

  function apply() {
    root.setAttribute("data-dir", cur("dir"));
    root.setAttribute("data-theme", cur("theme"));
    root.setAttribute("data-density", cur("density"));
    root.setAttribute("data-hero", cur("hero"));
    if (prefs.accent) root.setAttribute("data-accent", prefs.accent);
    else root.removeAttribute("data-accent");
    if (prefs.font) root.setAttribute("data-font", prefs.font);
    else root.removeAttribute("data-font");
    save(prefs);
    window.dispatchEvent(new Event("themechange"));
  }

  function set(axis, val) {
    if (axis === "dir") { prefs.dir = val; delete prefs.accent; delete prefs.font; }
    else if (val == null) { delete prefs[axis]; }
    else { prefs[axis] = val; }
    apply();
    sync();
  }

  /* ---------- UI ---------- */
  var STYLE = [
    '#tpref-btn{display:inline-flex;align-items:center;gap:.35rem;font:inherit;',
      'font-size:.82rem;font-weight:550;cursor:pointer;color:var(--ink);',
      'background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);',
      'padding:.32rem .6rem;line-height:1;white-space:nowrap;}',
    '#tpref-btn:hover{border-color:var(--line-2);}',
    '#tpref-btn svg{width:1rem;height:1rem;display:block;}',
    '#tpref-panel{position:fixed;z-index:200;top:0;inset-inline-end:0;width:min(92vw,320px);',
      'max-height:100vh;overflow:auto;background:var(--panel);color:var(--ink);',
      'border-inline-start:1px solid var(--line);box-shadow:-8px 0 30px rgba(0,0,0,.14);',
      'transform:translateX(100%);transition:transform .22s ease;',
      'padding:1.1rem 1.15rem 2rem;font-family:var(--sans);}',
    '[dir="rtl"] #tpref-panel{transform:translateX(-100%);}',
    '#tpref-panel.open{transform:translateX(0);}',
    '#tpref-panel h2{font-family:var(--hdr);font-size:1.05rem;font-weight:600;margin:0;}',
    '.tpref-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.3rem;}',
    '.tpref-x{background:none;border:0;cursor:pointer;color:var(--muted);font-size:1.35rem;',
      'line-height:1;padding:.1rem .3rem;}',
    '.tpref-x:hover{color:var(--ink);}',
    '.tpref-note{color:var(--muted);font-size:.78rem;margin:0 0 1rem;line-height:1.4;}',
    '.tpref-grp{margin:0 0 1.05rem;}',
    '.tpref-lbl{display:block;font-size:.66rem;font-weight:700;letter-spacing:.1em;',
      'text-transform:uppercase;color:var(--muted);margin-bottom:.4rem;}',
    '.tpref-seg{display:flex;flex-wrap:wrap;gap:.3rem;}',
    '.tpref-seg button{flex:1 1 auto;font:inherit;font-size:.8rem;font-weight:550;cursor:pointer;',
      'color:var(--muted);background:var(--panel-2);border:1px solid var(--line);',
      'border-radius:var(--radius);padding:.4rem .5rem;white-space:nowrap;}',
    '.tpref-seg button:hover{color:var(--ink);}',
    '.tpref-seg button[aria-pressed="true"]{color:var(--ink);border-color:var(--accent);',
      'box-shadow:0 0 0 1px var(--accent) inset;}',
    '.tpref-sw{display:flex;gap:.45rem;flex-wrap:wrap;}',
    '.tpref-sw button{width:1.7rem;height:1.7rem;border-radius:50%;cursor:pointer;',
      'border:1px solid rgba(0,0,0,.15);padding:0;position:relative;}',
    '.tpref-sw button[aria-pressed="true"]{box-shadow:0 0 0 2px var(--panel),0 0 0 4px var(--ink);}',
    '#tpref-scrim{position:fixed;inset:0;z-index:199;background:rgba(0,0,0,.28);',
      'opacity:0;visibility:hidden;transition:opacity .22s ease;}',
    '#tpref-scrim.open{opacity:1;visibility:visible;}'
  ].join("");

  var GEAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.14.6.65 1.05 1.28 1.05H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';

  var panel, scrim, btn, lastFocus = null;
  function focusables() {
    return Array.prototype.slice.call(panel.querySelectorAll(
      'button, [href], input, select, [tabindex]:not([tabindex="-1"])'));
  }

  /* opts entries are [value, i18n key, English fallback] */
  function seg(host, opts, axis) {
    opts.forEach(function (o) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = T(o[1], o[2]);
      b.dataset.axis = axis; b.dataset.val = o[0];
      b.addEventListener("click", function () { set(axis, o[0]); });
      host.appendChild(b);
    });
  }
  function group(title) {
    var g = document.createElement("div"); g.className = "tpref-grp";
    var l = document.createElement("span"); l.className = "tpref-lbl"; l.textContent = title;
    g.appendChild(l); return g;
  }

  function build() {
    var st = document.createElement("style"); st.id = "tpref-style"; st.textContent = STYLE;
    document.head.appendChild(st);

    scrim = document.createElement("div"); scrim.id = "tpref-scrim";
    scrim.addEventListener("click", close);

    panel = document.createElement("div"); panel.id = "tpref-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", T("pref_title", "Appearance"));
    panel.setAttribute("aria-hidden", "true");

    var head = document.createElement("div"); head.className = "tpref-head";
    var h = document.createElement("h2"); h.textContent = T("pref_title", "Appearance");
    var x = document.createElement("button"); x.className = "tpref-x"; x.type = "button";
    x.setAttribute("aria-label", T("pref_close", "Close")); x.innerHTML = "&times;";
    x.addEventListener("click", close);
    head.appendChild(h); head.appendChild(x); panel.appendChild(head);

    var note = document.createElement("p"); note.className = "tpref-note";
    note.textContent = T("pref_note",
      "Choose how the site looks. Your choice is saved on this device.");
    panel.appendChild(note);

    var gTheme = group(T("pref_theme", "Theme"));
    var sTheme = document.createElement("div"); sTheme.className = "tpref-seg";
    seg(sTheme, [["light", "pref_light", "Light"], ["dark", "pref_dark", "Dark"]], "theme");
    gTheme.appendChild(sTheme); panel.appendChild(gTheme);

    var gDir = group(T("pref_style", "Style"));
    var sDir = document.createElement("div"); sDir.className = "tpref-seg";
    seg(sDir, DIRS, "dir");
    gDir.appendChild(sDir); panel.appendChild(gDir);

    var gAcc = group(T("pref_accent", "Accent"));
    var sAcc = document.createElement("div"); sAcc.className = "tpref-sw";
    ACCENTS.forEach(function (a) {
      var b = document.createElement("button");
      b.type = "button"; b.dataset.axis = "accent"; b.dataset.val = a[0];
      b.style.background = a[1]; b.title = T(a[2], a[3]);
      b.setAttribute("aria-label", b.title);
      b.addEventListener("click", function () { set("accent", a[0]); });
      sAcc.appendChild(b);
    });
    gAcc.appendChild(sAcc); panel.appendChild(gAcc);

    var gFont = group(T("pref_headline", "Headline font"));
    var sFont = document.createElement("div"); sFont.className = "tpref-seg";
    seg(sFont, [["sans", "pref_sans", "Sans-serif"], ["serif", "pref_serif", "Serif"]], "font");
    gFont.appendChild(sFont); panel.appendChild(gFont);

    var gDen = group(T("pref_density", "Density"));
    var sDen = document.createElement("div"); sDen.className = "tpref-seg";
    seg(sDen, [["comfortable", "pref_comfortable", "Comfortable"],
               ["compact", "pref_compact", "Compact"]], "density");
    gDen.appendChild(sDen); panel.appendChild(gDen);

    var gHero = group(T("pref_header", "Page header"));
    var sHero = document.createElement("div"); sHero.className = "tpref-seg";
    seg(sHero, [["plain", "pref_plain", "Plain"], ["tint", "pref_tint", "Tint"]], "hero");
    gHero.appendChild(sHero); panel.appendChild(gHero);

    document.body.appendChild(scrim);
    document.body.appendChild(panel);

    btn = document.createElement("button");
    btn.id = "tpref-btn"; btn.type = "button";
    btn.setAttribute("aria-haspopup", "dialog"); btn.setAttribute("aria-expanded", "false");
    var btnLabel = T("pref_title", "Appearance");
    btn.setAttribute("aria-label", btnLabel);
    btn.innerHTML = GEAR;                         /* label added as text, never HTML */
    var bt = document.createElement("span");
    bt.className = "tpref-btn-t"; bt.textContent = btnLabel;
    btn.appendChild(bt);
    btn.addEventListener("click", open);
    mount(btn);

    document.addEventListener("keydown", function (e) {
      if (!panel.classList.contains("open")) return;
      if (e.key === "Escape") { close(); return; }
      if (e.key === "Tab") {                       /* keep focus within the panel */
        var f = focusables(); if (!f.length) return;
        var first = f[0], last = f[f.length - 1], a = document.activeElement;
        if (e.shiftKey && (a === first || !panel.contains(a))) { last.focus(); e.preventDefault(); }
        else if (!e.shiftKey && (a === last || !panel.contains(a))) { first.focus(); e.preventDefault(); }
      }
    });
    sync();
  }

  /* place the trigger in the top bar next to the language control, else float it */
  function mount(el) {
    var anchor = document.querySelector(".topbar-in") ||
                 document.querySelector(".topbar") || document.body;
    if (anchor.classList.contains("topbar-in") || anchor.classList.contains("topbar")) {
      el.style.marginInlineStart = ".2rem";
      anchor.appendChild(el);
    } else {
      el.style.position = "fixed"; el.style.top = "10px"; el.style.insetInlineEnd = "10px";
      el.style.zIndex = "120";
      anchor.appendChild(el);
    }
  }

  function open() {
    lastFocus = document.activeElement;
    panel.classList.add("open"); scrim.classList.add("open");
    panel.setAttribute("aria-hidden", "false"); btn.setAttribute("aria-expanded", "true");
    var f = focusables(); if (f.length) f[0].focus();   /* move focus into the panel */
  }
  function close() {
    panel.classList.remove("open"); scrim.classList.remove("open");
    panel.setAttribute("aria-hidden", "true"); btn.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus();  /* restore focus to the trigger */
  }

  function sync() {
    if (!panel) return;
    var effFont = prefs.font || (cur("dir") === "editorial" ? "serif" : "sans");
    var vals = {
      theme: cur("theme"), dir: cur("dir"), density: cur("density"),
      hero: cur("hero"), accent: prefs.accent || "cobalt", font: effFont
    };
    panel.querySelectorAll("[data-axis]").forEach(function (b) {
      var a = b.dataset.axis, v = b.dataset.val;
      b.setAttribute("aria-pressed", String(vals[a]) === v ? "true" : "false");
    });
  }

  apply();  /* re-affirm attrs + fire themechange once charts may exist */
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", build);
  else build();
})();
