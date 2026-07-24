/* Interactive climate charts (Chart.js) - one builder per archetype.
 *
 * Each city page embeds a language-neutral JSON payload per chart (numbers +
 * English label strings) and calls renderChart(canvasId, payload). Labels are
 * localised in-browser via window.__ci18n ({english: localized}, the same map
 * that localised the old SVG text); month names via window.__cmonths. So the
 * data is shared across all 21 languages and only the labels differ per page.
 *
 * Interactions come free from Chart.js - hover tooltips (exact values),
 * click-legend to toggle a series - plus scroll-zoom / drag-pan on the year
 * axis via chartjs-plugin-zoom. Heatmaps use chartjs-chart-matrix.
 */
(function () {
  "use strict";

  // --- localisation helpers -------------------------------------------------
  function T(s) {
    if (s == null) return s;
    var m = window.__ci18n || {};
    return Object.prototype.hasOwnProperty.call(m, s) ? m[s] : s;
  }
  function months() {
    return window.__cmonths || ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  }
  // A label may carry a "\n" (multi-line axis title) - Chart.js takes an array.
  function lines(s) { return T(s).split("\n"); }

  // --- chart-label recipes (client-i18n) ------------------------------------
  // Under client-side i18n one shell serves every language, so __ci18n cannot be
  // baked per page. Instead charts/<slug>.json ships each label's serialisable
  // RECIPE (a part-list, mirroring plots.compose_label) and we rebuild __ci18n in
  // the browser from the active dictionary (window.__i18n) - on load and again on
  // every language switch. pyfmt reproduces Python str.format for the only specs
  // the chart templates use ({name}, {name:.0f}/.1f, {name:+.Nf}); composite
  // numbers arrive pre-formatted as literal parts, so no locale drift.
  function pyfmt(tmpl, kw) {
    return String(tmpl).replace(/\{(\w+)(?::([^}]*))?\}/g, function (_, name, spec) {
      if (!kw || !(name in kw)) return "{" + name + "}";
      var v = kw[name];
      if (spec) {
        var m = /^(\+)?\.(\d+)f$/.exec(spec);
        if (m) {
          var num = Number(v), s = num.toFixed(+m[2]);
          if (m[1] && num >= 0 && s.charAt(0) !== "+") s = "+" + s;
          return s;
        }
      }
      return String(v);
    });
  }
  function composeLabel(recipe, D) {
    var out = "";
    for (var i = 0; i < recipe.length; i++) {
      var part = recipe[i];
      if (part[0] === "t") { out += part[1]; }
      else { var t = D[part[1]]; out += (t == null ? part[1] : pyfmt(t, part[2] || {})); }
    }
    return out;
  }
  // Rebuild window.__ci18n = {english_label: localized} from the shipped recipes
  // and the active dictionary. Called with the labels on first load (stored for
  // reuse) and argument-less on a language switch.
  window.__composeChartI18n = function (labels) {
    if (labels) window.__chartLabels = labels;
    var L = window.__chartLabels, D = window.__i18n;
    if (!L || !D) return;
    var map = {};
    for (var i = 0; i < L.length; i++) map[L[i][0]] = composeLabel(L[i][1], D);
    window.__ci18n = map;
  };

  // ISO-2 country code -> flag emoji (regional-indicator letters). Renders a flag
  // on Apple/Android/Linux, degrades to the two letters on Windows.
  /* Country <select>s label options "<flag>  Name". A native select's type-ahead
     matches the option's LEADING character, which is the flag emoji, so typing
     "p" never reaches Poland. Match on the name instead: repeated same letter
     cycles through the matches, a longer burst is treated as a prefix. */
  function attachFlagTypeahead(sel) {
    if (!sel || sel.__flagTa) return;
    sel.__flagTa = 1;
    var buf = "", at = 0;
    sel.addEventListener("keydown", function (e) {
      if (!e.key || e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
      var now = Date.now(), ch = e.key.toLowerCase();
      buf = (now - at < 900 ? buf : "") + ch; at = now;
      var cycle = buf.split("").every(function (c) { return c === ch; });
      var q = cycle ? ch : buf;
      var o = sel.options, n = o.length, cur = sel.selectedIndex;
      function nameOf(i) {                       /* strip the flag + padding */
        return (o[i].textContent || "").replace(/^[^\p{L}\p{N}]+/u, "").toLowerCase();
      }
      for (var k = 1; k <= n; k++) {
        var idx = cycle ? (cur + k) % n : (k - 1);
        if (nameOf(idx).indexOf(q) === 0) {
          sel.selectedIndex = idx;
          sel.dispatchEvent(new Event("change", { bubbles: true }));
          break;
        }
      }
      e.preventDefault();
    });
  }

  function flagEmoji(cc) {
    cc = (cc || "").toUpperCase();
    if (!/^[A-Z]{2}$/.test(cc)) return "";
    return String.fromCodePoint(0x1F1E6 + cc.charCodeAt(0) - 65,
                                0x1F1E6 + cc.charCodeAt(1) - 65);
  }

  // --- colour scales for heatmaps ------------------------------------------
  function lerp(a, b, t) { return a + (b - a) * t; }
  function mix(c1, c2, t) {
    return "rgb(" + Math.round(lerp(c1[0], c2[0], t)) + "," +
      Math.round(lerp(c1[1], c2[1], t)) + "," +
      Math.round(lerp(c1[2], c2[2], t)) + ")";
  }
  function ramp(stops, t) {
    t = Math.max(0, Math.min(1, t));
    var n = stops.length - 1, i = Math.min(n - 1, Math.floor(t * n));
    return mix(stops[i], stops[i + 1], t * n - i);
  }
  // RdYlBu reversed (cold blue -> yellow -> hot red): absolute temperatures.
  var RDYLBU = [[49, 54, 149], [69, 117, 180], [116, 173, 209], [171, 217, 233],
    [224, 243, 248], [255, 255, 191], [254, 224, 144], [253, 174, 97],
    [244, 109, 67], [215, 48, 39], [165, 0, 38]];
  // RdBu reversed (blue -> white -> red): diverging anomalies around zero.
  var RDBU = [[33, 102, 172], [103, 169, 207], [209, 229, 240],
    [247, 247, 247], [253, 219, 199], [239, 138, 98], [178, 24, 43]];
  // Snap a value to a discrete step-wide colour band (matching the old static
  // heatmaps); values outside [vmin,vmax] saturate to the end bands.
  function heatColor(v, vmin, vmax, diverging, step) {
    if (v == null || isNaN(v)) return "rgba(0,0,0,0)";
    var stops = diverging ? RDBU : RDYLBU;
    var span = vmax - vmin;
    if (!(span > 0) || !(step > 0)) return ramp(stops, 0.5);
    var nb = Math.max(1, Math.round(span / step));
    var idx = Math.max(0, Math.min(nb - 1, Math.floor((v - vmin) / step)));
    return ramp(stops, (idx + 0.5) / nb);
  }

  // --- shared Chart.js option blocks ---------------------------------------
  // Chart CHROME (ticks, labels, gridlines, overlay lines) reads live theme
  // colours from CSS custom properties on <html> at BUILD time, so a rebuild
  // (theme switch -> destroy + re-render) re-reads the current palette. Read
  // the var on EACH call, never capture once.
  function cssVar(n, fb){ try { var v = getComputedStyle(document.documentElement).getPropertyValue(n).trim(); return v || fb; } catch(e){ return fb; } }
  function chartMuted(){ return cssVar('--muted', '#475569'); }
  function chartGrid(){  return cssVar('--line',  '#eceae4'); }
  function chartLine(){  return cssVar('--ink',   '#0f172a'); }
  // The warm/cool DATA encoding is baked into payloads server-side as fixed
  // hexes. Map those onto the themed --warm/--cool tokens on the way into a
  // dataset, so a theme switch re-colours the series the same way the chrome
  // getters re-colour the axes. Resolve per call and never write the result
  // back to the payload: __chartPayloads is re-rendered on every switch, so a
  // cached value would pin the canvas to whichever theme drew it first.
  // Any colour that is not part of the encoding passes through untouched.
  var THEMED_HEX = { '#d62728': '--warm', '#2c7fb8': '--cool' };
  function themed(c){
    var tok = THEMED_HEX[String(c).toLowerCase()];
    return tok ? cssVar(tok, c) : c;
  }
  function baseOpts(extra) {
    var o = {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { labels: { boxWidth: 12, usePointStyle: true, color: chartMuted() } },
        tooltip: { callbacks: {} }
      },
      scales: {}
    };
    return Object.assign(o, extra || {});
  }
  // Legend that omits datasets flagged __hidden (raw points / trend lines whose
  // value is already conveyed by the LOESS entry) - an explicit flag rather than
  // matching an invisible label string.
  function hideLegend() {
    return {
      labels: { boxWidth: 12, usePointStyle: true, color: chartMuted(),
        filter: function (item, data) {
          return !data.datasets[item.datasetIndex].__hidden;
        } },
      // Clicking a series entry toggles every dataset in its group (raw points +
      // trend line follow the LOESS), not just the one legend row.
      onClick: function (_e, item, legend) {
        var chart = legend.chart;
        var grp = chart.data.datasets[item.datasetIndex].group;
        if (grp == null) {
          var vis = chart.isDatasetVisible(item.datasetIndex);
          chart.setDatasetVisibility(item.datasetIndex, !vis);
        } else {
          var on = chart.isDatasetVisible(item.datasetIndex);
          chart.data.datasets.forEach(function (d, i) {
            if (d.group === grp) chart.setDatasetVisibility(i, !on);
          });
        }
        chart.update();
      }
    };
  }
  // Zoom / pan on the x (year) axis. Wheel zoom is gated behind Ctrl so a plain
  // scroll still moves the PAGE (the canvas no longer hijacks the wheel, and the
  // laggy "keeps zooming" feel is gone); pinch zooms on touch, drag pans. The
  // view is clamped to the real data range so it can never get lost off-screen -
  // that, plus the per-chart reset button, means you can always get back.
  function zoomPlugin() {
    return {
      zoom: {
        wheel: { enabled: true, modifierKey: "ctrl", speed: 0.06 },
        pinch: { enabled: true },
        drag: { enabled: false },
        mode: "x",
        onZoomComplete: syncFigureButtons
      },
      pan: { enabled: true, mode: "x", onPanComplete: syncFigureButtons },
      limits: { x: { min: "original", max: "original", minRange: 3 } }
    };
  }
  // Year axis. Only whole years are labelled (no 1939.5 / 2025.5 half-ticks),
  // and when the data years are passed the axis is clamped to them (+ half a
  // year of breathing room) so it ends at the last year instead of padding out
  // to a round 2040.
  function intYear(v) { return v % 1 === 0 ? "" + v : ""; }
  // Build nice WHOLE-year ticks spanning the axis. Generating them explicitly
  // (rather than filtering Chart's auto-ticks) guarantees labels always render -
  // a plain "hide non-integers" callback blanks *every* tick when Chart happens
  // to pick a fractional step (e.g. 2.5-year) on a short or odd range.
  function yearTicks(axis) {
    var lo = Math.ceil(axis.min), hi = Math.floor(axis.max), span = hi - lo;
    if (!(span > 0)) { axis.ticks = [{ value: Math.round(axis.min) }]; return; }
    var step = span <= 12 ? 2 : span <= 30 ? 5 : span <= 80 ? 10 : 20;
    var start = Math.ceil(lo / step) * step, out = [];
    for (var y = start; y <= hi; y += step) out.push({ value: y });
    if (!out.length) out = [{ value: lo }, { value: hi }];
    axis.ticks = out;
  }
  function yearScale(title, xs) {
    var s = { type: "linear",
      title: { display: !!title, text: title, color: chartMuted() },
      ticks: { color: chartMuted(), callback: intYear, maxRotation: 0, autoSkip: false },
      afterBuildTicks: yearTicks,
      grid: { color: chartGrid() } };
    if (xs && xs.length) {
      // A couple of years of breathing room on each side so the first/last data
      // point isn't glued to the axis edge (but still ends near the last year,
      // never padding out to a round 2040).
      var pad = Math.max(1.2, (xs[xs.length - 1] - xs[0]) * 0.02);
      s.min = xs[0] - pad;
      s.max = xs[xs.length - 1] + pad;
    }
    return s;
  }
  function valScale(title) {
    return { title: { display: !!title, text: title, color: chartMuted() },
      ticks: { color: chartMuted() }, grid: { color: chartGrid() } };
  }

  // --- builders -------------------------------------------------------------
  // Trend: faint raw points/bars + bold LOESS + dashed robust trend line.
  function mkTrend(ctx, p) {
    var isBar = p.raw.style === "bars";
    // Three independent legend entries (raw / LOESS / trend), matching the old
    // static chart; raw has no entry when it carries no label (e.g. volatility).
    var raw = {
      type: isBar ? "bar" : "line",
      label: p.raw.label ? T(p.raw.label) : undefined,
      __hidden: !p.raw.label,   // legend entry suppressed (see hideLegend)
      data: p.raw.data, borderColor: themed(p.raw.color),
      backgroundColor: isBar ? themed(p.raw.color) + "73" : themed(p.raw.color),
      borderWidth: 0, pointRadius: isBar ? 0 : 2.4,
      showLine: false, order: 3
    };
    var loess = {
      type: "line", label: T(p.loess.label), data: p.loess.data,
      borderColor: themed(p.loess.color), borderWidth: 2.6, pointRadius: 0,
      tension: 0.3, order: 1
    };
    var trend = {
      type: "line", label: T(p.trend.label), data: p.trend.line,
      borderColor: themed(p.trend.color), borderWidth: 1.6, borderDash: [6, 4],
      pointRadius: 0, order: 2
    };
    return new Chart(ctx, {
      type: isBar ? "bar" : "line",
      data: { labels: p.x, datasets: [raw, loess, trend] },
      options: baseOpts({
        plugins: { legend: hideLegend(), zoom: zoomPlugin() },
        scales: { x: yearScale(lines(p.xlabel)[0], p.x), y: valScale(lines(p.ylabel)) }
      })
    });
  }

  // Multitrend: N series, each faint points + LOESS + dashed trend.
  function mkMultitrend(ctx, p) {
    var ds = [];
    // Each series' raw points + (optional) trend line are hidden from the legend
    // and grouped with its LOESS entry, so clicking that entry toggles them all.
    p.series.forEach(function (s, i) {
      var g = "s" + i;
      ds.push({ type: "line", group: g, __hidden: true, data: s.raw,
        borderColor: themed(s.color), showLine: false, pointRadius: 2.2,
        pointBackgroundColor: themed(s.color) + "b0", order: 3 });
      ds.push({ type: "line", group: g, label: T(s.label), data: s.loess,
        borderColor: themed(s.color), borderWidth: 2.6, pointRadius: 0, tension: 0.3,
        order: 1 });
      if (s.trend) {
        ds.push({ type: "line", group: g, __hidden: true, data: s.trend,
          borderColor: themed(s.color), borderWidth: 1.3, borderDash: [6, 4],
          pointRadius: 0, order: 2 });
      }
    });
    return new Chart(ctx, {
      type: "line", data: { labels: p.x, datasets: ds },
      options: baseOpts({
        plugins: { legend: hideLegend(), zoom: zoomPlugin() },
        scales: { x: yearScale(lines(p.xlabel)[0], p.x), y: valScale(lines(p.ylabel)) }
      })
    });
  }

  // Anomaly bars: diverging bars (blue cool / red warm) + LOESS overlay.
  function mkAnomalyBars(ctx, p) {
    var colors = p.values.map(function (v) {
      return v == null ? "#ccc" : themed(v >= 0 ? p.posColor : p.negColor);
    });
    var bars = { type: "bar", data: p.values,
      backgroundColor: colors, borderWidth: 0, order: 2 };
    var smooth = { type: "line", data: p.loess, borderColor: chartLine(),
      borderWidth: 2, pointRadius: 0, tension: 0.3, order: 1 };
    return new Chart(ctx, {
      type: "bar", data: { labels: p.x, datasets: [bars, smooth] },
      options: baseOpts({
        plugins: {
          legend: { display: false },
          zoom: zoomPlugin(),
          tooltip: { callbacks: { label: function (c) {
            return (c.raw == null ? "" : (c.raw >= 0 ? "+" : "") + c.raw + " °C");
          } } }
        },
        scales: { x: yearScale(lines(p.xlabel)[0], p.x), y: valScale(lines(p.ylabel)) }
      })
    });
  }

  // Warming stripes: one bar per year, coloured by anomaly, no axes/gaps.
  function mkStripes(ctx, p) {
    var lim = p.limit || 1;
    var colors = p.anom.map(function (v) {
      return v == null ? "rgba(0,0,0,0)" : ramp(RDBU, (v / lim + 1) / 2);
    });
    return new Chart(ctx, {
      type: "bar",
      data: { labels: p.years, datasets: [{ data: p.years.map(function () { return 1; }),
        backgroundColor: colors, borderWidth: 0 }] },
      options: baseOpts({
        categoryPercentage: 1.0, barPercentage: 1.0,
        plugins: {
          legend: { display: false },
          zoom: zoomPlugin(),
          tooltip: { callbacks: {
            title: function (c) { return "" + p.years[c[0].dataIndex]; },
            label: function (c) {
              var v = p.anom[c.dataIndex];
              return v == null ? "" : (v >= 0 ? "+" : "") + v + " °C";
            } } }
        },
        scales: {
          x: { type: "category", ticks: { color: chartMuted(), autoSkip: true,
            maxRotation: 0, autoSkipPadding: 24 }, grid: { display: false },
            title: { display: true, text: lines(p.xlabel)[0], color: chartMuted() } },
          y: { display: false, min: 0, max: 1 }
        }
      })
    });
  }

  // Seasonal shift: early-decade vs late-decade monthly curves + fill between.
  function mkSeasonShift(ctx, p) {
    return new Chart(ctx, {
      type: "line",
      data: { labels: months(), datasets: [
        { label: T(p.early.label), data: p.early.data, borderColor: themed(p.early.color),
          backgroundColor: themed(p.early.color), borderWidth: 2, pointRadius: 3,
          tension: 0.35 },
        { label: T(p.late.label), data: p.late.data, borderColor: themed(p.late.color),
          backgroundColor: themed(p.late.color) + "22", borderWidth: 2, pointRadius: 3,
          tension: 0.35, fill: "-1" }
      ] },
      options: baseOpts({
        scales: { x: { ticks: { color: chartMuted() }, grid: { display: false } },
          y: valScale(lines(p.ylabel)) }
      })
    });
  }

  // Year x month heatmap via chartjs-chart-matrix.
  function mkMatrix(ctx, p) {
    var mon = months();
    var data = [];
    for (var yi = 0; yi < p.years.length; yi++) {
      for (var mi = 0; mi < 12; mi++) {
        data.push({ x: mon[mi], y: p.years[yi], v: p.cells[yi][mi] });
      }
    }
    return new Chart(ctx, {
      type: "matrix",
      data: { datasets: [{
        label: T(p.cbarLabel), data: data,
        backgroundColor: function (c) {
          return heatColor(c.raw.v, p.vmin, p.vmax, p.diverging, p.step);
        },
        borderWidth: 0,
        width: function (c) {
          var a = c.chart.chartArea; return a ? a.width / 12 - 0.5 : 8;
        },
        height: function (c) {
          var a = c.chart.chartArea;
          return a ? a.height / p.years.length - 0.2 : 4;
        }
      }] },
      options: baseOpts({
        interaction: { intersect: true, mode: "nearest" },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            title: function (c) { return c[0].raw.x + " " + c[0].raw.y; },
            label: function (c) {
              var v = c.raw.v;
              return T(p.cbarLabel) + ": " + (v == null ? "-" : v + " °C");
            } } }
        },
        scales: {
          x: { type: "category", labels: mon, offset: true,
            ticks: { color: chartMuted() }, grid: { display: false },
            title: { display: true, text: lines(p.xlabel)[0], color: chartMuted() } },
          y: { type: "linear", offset: true,
            min: p.years[0] - 0.5, max: p.years[p.years.length - 1] + 0.5,
            ticks: { color: chartMuted(), callback: intYear },
            grid: { display: false },
            title: { display: true, text: lines(p.ylabel)[0], color: chartMuted() } }
        }
      })
    });
  }

  // Horizontal bars: a zone's most extreme cities by warming rate (red warming,
  // blue cooling). Used only by the global dashboard's per-zone extremes chart.
  function mkCityBars(ctx, p) {
    var colors = p.values.map(function (v) {
      return themed(v >= 0 ? p.posColor : p.negColor);
    });
    return new Chart(ctx, {
      type: "bar",
      data: { labels: p.labels,
        datasets: [{ data: p.values, backgroundColor: colors, borderWidth: 0 }] },
      options: baseOpts({
        indexAxis: "y",
        interaction: { intersect: false, mode: "nearest", axis: "y" },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (c) {
            return (c.raw >= 0 ? "+" : "") + c.raw + " " + T(p.xlabel);
          } } }
        },
        scales: {
          x: valScale(lines(p.xlabel)),
          y: { ticks: { color: chartMuted(), autoSkip: false }, grid: { display: false } }
        }
      })
    });
  }

  var BUILDERS = {
    trend: mkTrend, multitrend: mkMultitrend, anomalybars: mkAnomalyBars,
    stripes: mkStripes, seasonshift: mkSeasonShift, matrix: mkMatrix,
    citybars: mkCityBars
  };

  // Replace a canvas with a small visible notice so a failed chart reads as an
  // error rather than a silent blank (and the cause is still logged).
  function failNotice(el, canvasId, err) {
    if (window.console) console.error("chart " + canvasId, err);
    var wrap = el.parentNode;
    if (wrap) {
      var msg = document.createElement("div");
      msg.className = "chart-error";
      msg.setAttribute("role", "img");
      msg.textContent = "⚠ " + (window.__chartErr || "chart unavailable");
      wrap.replaceChild(msg, el);
    }
  }

  // Live chart instances keyed by canvas id, so the reset-zoom button can find
  // the chart for its figure at click time (charts render after an async fetch,
  // long after the buttons are wired up). The payload is kept alongside so a
  // language switch can rebuild the chart with freshly-composed labels.
  window.__charts = {};
  window.__chartPayloads = {};
  window.renderChart = function (canvasId, payload) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var fn = BUILDERS[payload && payload.kind];
    if (!fn) { failNotice(el, canvasId, "unknown chart kind: " + (payload && payload.kind)); return null; }
    try {
      var inst = fn(el.getContext("2d"), payload);
      if (inst) {
        window.__charts[canvasId] = inst;
        window.__chartPayloads[canvasId] = payload;
        syncFigureButtons();
      }
      return inst;
    } catch (e) { failNotice(el, canvasId, e); return null; }
  };

  // Language switch (client-i18n): recompose the label map from the current
  // dictionary and rebuild every live chart so axis/legend/trend text follows
  // the new language. Charts drawn via renderChart (per-city and the landing
  // dashboard alike) are all tracked in __charts. No-op when no recipes shipped
  // (server-i18n build) - the baked __ci18n already matches the page language.
  window.__relocalizeCharts = function () {
    if (!window.__chartLabels) return;
    window.__composeChartI18n();
    Object.keys(window.__charts).forEach(function (cid) {
      var inst = window.__charts[cid], payload = window.__chartPayloads[cid];
      if (inst && payload) { try { inst.destroy(); } catch (e) {} window.renderChart(cid, payload); }
    });
  };

  // Runtime theme switch (light/dark + palettes): the CSS custom properties on
  // <html> change, so every chart is destroyed and re-rendered - the chrome
  // getters (chartMuted/chartGrid/chartLine) then re-read the new palette at
  // build time. The standalone range/records widgets live in window.__extraCharts
  // (not __charts) and carry their own destroy/rebuild closures.
  window.__applyChartTheme = function () {
    Object.keys(window.__charts).forEach(function (cid) {
      var inst = window.__charts[cid], payload = window.__chartPayloads[cid];
      if (inst && payload) { try { inst.destroy(); } catch (e) {} window.renderChart(cid, payload); }
    });
    if (window.__extraCharts) {
      Object.keys(window.__extraCharts).forEach(function (k) {
        var e = window.__extraCharts[k];
        if (e) { try { e.destroy(); } catch (err) {} try { e.rebuild(); } catch (err) {} }
      });
    }
  };
  window.addEventListener('themechange', window.__applyChartTheme);

  // Global dashboard: draw the region-comparison chart once, then (re)draw the
  // three per-zone charts whenever the zone <select> changes. Chart instances
  // are tracked and destroyed before each redraw so switching zones doesn't leak
  // canvases. Reuses the same archetype builders as the per-city charts.
  window.renderGlobal = function (data) {
    var live = {};
    function draw(cid, payload) {
      if (live[cid]) { live[cid].destroy(); live[cid] = null; }
      live[cid] = window.renderChart(cid, payload);
    }
    draw("g-comparison", data.comparison);
    // Climate-zone picker: a row of pill buttons (one active at a time).
    var bar = document.getElementById("g-region");
    var btns = bar ? [].slice.call(bar.querySelectorAll("[data-zone]")) : [];
    function drawZone(key) {
      var r = data.regions[key];
      if (!r) return;
      var name = "";
      btns.forEach(function (b) {
        var on = b.getAttribute("data-zone") === key;
        b.classList.toggle("active", on);
        if (on) name = (b.textContent || "").trim();
      });
      draw("g-anomaly", r.anomaly);
      draw("g-stripes", r.stripes);
      draw("g-heatmap", r.heatmap);
      document.querySelectorAll(".zone-name").forEach(function (el) {
        el.textContent = name;
      });
    }
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        drawZone(b.getAttribute("data-zone"));
      });
    });
    var pre = bar ? bar.querySelector("[data-zone].active") : null;
    var initial = (pre && pre.getAttribute("data-zone")) ||
      (btns[0] && btns[0].getAttribute("data-zone")) ||
      (data.order && data.order[0]) || "world";
    drawZone(initial);
    if (data.ranking) renderRanking(data.ranking, data.countries || [], data.gt || 0);
    if (data.countries) renderCountryStat(data.countries, data.tzcc || {});
    // Sorted trend distribution + world-city average power the "check any place"
    // lookup's "faster than N%" line without another network round-trip.
    window.__trends = (data.ranking || []).map(function (r) { return r.t; })
      .sort(function (a, b) { return a - b; });
    window.__gt = data.gt || 0;
    // Full ranking (per-city slug/name/trend/since-1940) so the "your region"
    // hero can fill its stat for the visitor's nearest city from data already
    // loaded here - no extra request.
    window.__ranking = data.ranking || [];
    // Per-city climate analogs (past/future look-alike cities) so the hero can
    // show "in 1940 it felt like X; by 2050, like Y" for the resolved city.
    window.__analogs = data.analogs || {};
    // Country list for the omni search (localized client-side from the codes).
    window.__countries = data.countries || [];
    if (window.initOmni) window.initOmni();
    if (window.applyHero) window.applyHero();
  };

  // --- "Check any place on Earth" -------------------------------------------
  // Geocode a free-text place, pull its 1940→ daily record straight from
  // Open-Meteo (both APIs are free, key-less and CORS-enabled), then compute the
  // warming trend + stripes in the browser. So towns too small for our prebuilt
  // set still get a real answer - computed on the visitor's machine, never stale.
  // Signed number that never shows "+0.0" or "-0.00": a value rounding to zero
  // prints a bare unsigned zero, so a near-flat city reads honestly.
  function fmtSigned(v, dp) {
    var s = v.toFixed(dp);
    if (parseFloat(s) === 0) return (0).toFixed(dp);
    return (v > 0 ? "+" : "") + s;
  }
  function luStripeColor(v) {
    if (v == null) return "#8080802e";
    var lo = -1.0, hi = 1.5, x = Math.max(lo, Math.min(hi, v)), a, b, k;
    if (x < 0) { k = (x - lo) / (0 - lo); a = [8, 48, 107]; b = [247, 247, 247]; }
    else { k = x / hi; a = [247, 247, 247]; b = [103, 0, 13]; }
    return "rgb(" + Math.round(a[0] + (b[0] - a[0]) * k) + ","
      + Math.round(a[1] + (b[1] - a[1]) * k) + ","
      + Math.round(a[2] + (b[2] - a[2]) * k) + ")";
  }
  function luMedian(arr) {
    if (!arr.length) return 0;
    arr.sort(function (a, b) { return a - b; });
    var m = Math.floor(arr.length / 2);
    return arr.length % 2 ? arr[m] : (arr[m - 1] + arr[m]) / 2;
  }
  // One omni search: type a city, country, region or any place. Cities, countries
  // and regions come from the site's own data (instant, offline); anything else is
  // geocoded and its climate computed live (see lookupPlace). Selecting a result
  // navigates to a city, filters the map/ranking, or shows the "any place" card.
  window.initOmni = function () {
    var input = document.getElementById("omni-input");
    if (!input || input.__wired) return;
    input.__wired = true;
    var box = document.getElementById("omni-results");
    var statusEl = document.getElementById("lookup-status");
    var out = document.getElementById("lookup-result");
    var sec = document.getElementById("omni");
    var L = {};
    try { L = JSON.parse(sec.getAttribute("data-i18n") || "{}"); } catch (e) {}
    var lang = (document.documentElement.lang || "en").split("-")[0];
    var DATA = window.__omniData || { c: [], r: [], g: [] };
    // Covered-city coordinates [lat, lon, slug]. A freeform place lookup snaps to
    // the nearest of these within NEAR_DEG (~one ERA5 cell) and opens that city's
    // page (relabelled) instead of a live 85-year fetch - instant and quota-proof.
    var GEO = DATA.g || [];
    var NEAR_DEG = 0.15;   // ~16 km: within a single reanalysis cell -> same record
    function nearestCity(lat, lon) {
      var best = null, bestD = Infinity, cl = Math.cos(lat * Math.PI / 180);
      for (var i = 0; i < GEO.length; i++) {
        var dy = lat - GEO[i][0], dx = (lon - GEO[i][1]) * cl;
        var d = dy * dy + dx * dx;
        if (d < bestD) { bestD = d; best = GEO[i][2]; }
      }
      return bestD <= NEAR_DEG * NEAR_DEG ? best : null;
    }
    function onorm(s) {
      return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }
    // Precompute each city's search key (localized + original name) once.
    var CITY = DATA.c.map(function (c) {
      return { disp: c[0], url: c[1], sub: c[2], key: onorm(c[0] + " " + (c[3] || "")) };
    });
    var REGION = (DATA.r || []).map(function (r) {
      return { key: r[0], label: r[1], nkey: onorm(r[1]) };
    });
    function oflag(cc) {
      if (!cc || cc.length !== 2) return "";
      var A = 0x1F1E6, u = cc.toUpperCase();
      return String.fromCodePoint(A + u.charCodeAt(0) - 65)
           + String.fromCodePoint(A + u.charCodeAt(1) - 65);
    }
    var odn = null;
    try { odn = new Intl.DisplayNames([lang], { type: "region" }); } catch (e) { odn = null; }
    function ocountry(cc) {
      var up = (cc || "").toUpperCase();
      if (odn) { try { return odn.of(up) || up; } catch (e) {} }
      return up;
    }

    // Cache each computed result in localStorage so a repeat lookup (or a shared
    // link opened again) is instant and costs the free Open-Meteo API nothing.
    // Only the small computed stats are stored, keyed by the query text, with an
    // LRU index capping how much we keep. All storage access is best-effort.
    var CACHE_PREFIX = "tmp_lu_", CACHE_IDX = "tmp_lu_:idx",
        CACHE_MAX = 80, CACHE_TTL = 180 * 864e5;   // ~6 months; the record grows yearly
    function cacheKey(q) { return CACHE_PREFIX + q.toLowerCase().replace(/\s+/g, " "); }
    function cacheGet(q) {
      try {
        var raw = localStorage.getItem(cacheKey(q));
        if (!raw) return null;
        var o = JSON.parse(raw);
        if (!o || !o.s || (Date.now() - (o.t || 0)) > CACHE_TTL) return null;
        return o;
      } catch (e) { return null; }
    }
    function cachePut(q, place, s) {
      try {
        var key = cacheKey(q);
        localStorage.setItem(key, JSON.stringify({ place: place, s: s, t: Date.now() }));
        var idx = JSON.parse(localStorage.getItem(CACHE_IDX) || "[]");
        idx = idx.filter(function (k) { return k !== key; });
        idx.push(key);
        while (idx.length > CACHE_MAX) { localStorage.removeItem(idx.shift()); }
        localStorage.setItem(CACHE_IDX, JSON.stringify(idx));
      } catch (e) {}
    }

    // The "check any place" path: geocode the text, pull its 1940-> daily record
    // from Open-Meteo, compute the trend in-browser (result cached in localStorage).
    function luErr(err) {
      var m = err && err.message;
      statusEl.textContent = m === "notfound"
          ? (L.notfound || "Place not found.")
        : m === "busy"
          ? (L.busy || "The free climate service is over its daily request "
                      + "limit right now. Please try again later.")
          : (L.error || "Could not load data.");
    }
    // Fetch + compute the trend for an already-resolved place (lat/lon known).
    // Shared by the text lookup and the world autocomplete picks. ``key`` is the
    // localStorage cache key (the typed query for a text lookup, else the name).
    function lookupResolved(p, key) {
      var q = key || p.name;
      // Snap to a covered city sharing this point's grid cell: open its page
      // (relabelled to the searched place) instead of a live fetch. Covers small
      // villages (below the alias floor) and works when the daily quota is spent.
      var near = nearestCity(p.latitude, p.longitude);
      if (near) { oclose(); location.href = near + ".html#as=" + encodeURIComponent(p.name); return; }
      out.hidden = true;
      var cached = cacheGet(q);
      if (cached) { showResult(cached.place, cached.s); return; }
      statusEl.textContent = L.loading || "Loading 85 years of data...";
      var endYear = new Date().getFullYear() - 1;
      fetch("https://archive-api.open-meteo.com/v1/archive?latitude="
            + p.latitude + "&longitude=" + p.longitude
            + "&start_date=1940-01-01&end_date=" + endYear + "-12-31"
            + "&daily=temperature_2m_mean&timezone=UTC")
        .then(function (r) {
          // The 85-year daily request is heavy; the free per-IP quota can run
          // out. A 429 means "try later", not the generic "try again".
          if (r.status === 429) throw new Error("busy");
          if (!r.ok) throw new Error("error");
          return r.json();
        })
        .then(function (d) { render(q, p, d); })
        .catch(luErr);
    }
    // The "check any place" text path: geocode the typed query, then resolve it.
    function lookupPlace(q) {
      q = (q || "").trim();
      if (!q) return;
      var cached = cacheGet(q);
      if (cached) { out.hidden = true; showResult(cached.place, cached.s); return; }
      statusEl.textContent = L.searching || "Finding the place...";
      fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&language=" + lang
            + "&name=" + encodeURIComponent(q))
        .then(function (r) {
          if (r.status === 429) throw new Error("busy");   // shared free-service daily limit
          return r.json();
        })
        .then(function (g) {
          if (!g.results || !g.results.length) throw new Error("notfound");
          lookupResolved(g.results[0], q);
        })
        .catch(luErr);
    }

    // Reduce the daily series to the handful of stats the card shows: the trend
    // (per-decade + total, Theil-Sen), the decade-anomaly stripes, and the span.
    // Returns null (bad data) or the string "short" (too few years) as sentinels.
    function computeStats(data) {
      var times = data.daily && data.daily.time;
      var vals = data.daily && data.daily.temperature_2m_mean;
      if (!times || !vals) return null;
      var sum = {}, cnt = {};
      for (var i = 0; i < times.length; i++) {
        var v = vals[i];
        if (v == null) continue;
        var y = +times[i].slice(0, 4);
        sum[y] = (sum[y] || 0) + v; cnt[y] = (cnt[y] || 0) + 1;
      }
      var years = Object.keys(cnt).map(Number)
        .filter(function (y) { return cnt[y] >= 300; })       // near-complete years
        .sort(function (a, b) { return a - b; });
      if (years.length < 10) return "short";
      var am = years.map(function (y) { return sum[y] / cnt[y]; });
      // Theil-Sen slope (median pairwise): robust, matches the site's method.
      var slopes = [];
      for (var a2 = 0; a2 < years.length; a2++)
        for (var b2 = a2 + 1; b2 < years.length; b2++)
          slopes.push((am[b2] - am[a2]) / (years[b2] - years[a2]));
      var slope = luMedian(slopes);
      // Decade-anomaly stripes vs the 1961-1990 baseline (same as the prebuilt set).
      var bs = 0, bn = 0;
      for (var k = 0; k < years.length; k++)
        if (years[k] >= 1961 && years[k] <= 1990) { bs += am[k]; bn++; }
      var base = bn ? bs / bn : am.reduce(function (s, x) { return s + x; }, 0) / am.length;
      var ds = {}, dn = {};
      for (var k2 = 0; k2 < years.length; k2++) {
        var dd = Math.floor(years[k2] / 10) * 10;
        ds[dd] = (ds[dd] || 0) + (am[k2] - base); dn[dd] = (dn[dd] || 0) + 1;
      }
      var decades = [1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020];
      var st = decades.map(function (dd) { return dn[dd] ? ds[dd] / dn[dd] : null; });
      return {
        y0: years[0], y1: years[years.length - 1],
        perDec: slope * 10, total: slope * (years[years.length - 1] - years[0]), st: st
      };
    }
    // Format + inject the card from precomputed stats. The percentile is derived
    // live from window.__trends, so a cached result still ranks against the world.
    function showResult(place, s) {
      var T = window.__trends || [], pct = null;
      if (T.length) {
        var below = 0;
        for (var t2 = 0; t2 < T.length; t2++) if (T[t2] < s.perDec) below++;
        pct = Math.round(100 * below / T.length);
      }
      var warm = s.total >= 0;
      var name = place.name + (place.admin1 && place.admin1 !== place.name
        ? ", " + place.admin1 : "");
      var country = place.country || "";
      var stripesHtml = s.st.map(function (v) {
        return '<i style="background:' + luStripeColor(v) + '"></i>';
      }).join("");
      var big = fmtSigned(s.total, 1) + "°C";
      var perDecTxt = fmtSigned(s.perDec, 2) + "°C "
        + (L.perdec || "per decade") + " · "
        + (warm ? (L.warm || "warming trend") : (L.cool || "cooling trend"));
      var faster = (pct == null) ? "" : ('<p class="lu-faster">' + (warm
        ? (L.faster || "warming faster than {pct}% of the world's cities").replace("{pct}", pct)
        : (L.cooling || "Cooling, against the global trend")) + "</p>");
      // Localized extreme-weather news: L.news doubles as the query term, so the
      // search reads naturally in the visitor's language and stays current.
      var newsUrl = "https://news.google.com/search?q="
        + encodeURIComponent('"' + place.name + '" ' + (L.news || "extreme weather"))
        + "&hl=" + lang;
      out.innerHTML =
        '<p class="lu-place">' + esc(name) + "</p>"
        + '<p class="lu-sub">' + esc(country) + " · " + s.y0 + "-" + s.y1 + "</p>"
        + '<div class="lu-stripes">' + stripesHtml + "</div>"
        + '<div><span class="lu-big ' + (warm ? "warm" : "cool") + '">' + big
          + '</span><span class="lu-since">' + (L.since || "since 1940") + "</span></div>"
        + '<p class="lu-meta">' + perDecTxt + "</p>"
        + faster
        + '<a class="lu-news" href="' + newsUrl + '" target="_blank" rel="noopener noreferrer">'
          + esc(L.news || "Extreme weather") + "</a>";
      statusEl.textContent = "";
      out.hidden = false;
    }
    // Fetch path: compute, show, and remember a slim copy for next time.
    function render(q, place, data) {
      var s = computeStats(data);
      if (s === null) { statusEl.textContent = L.error || "Could not load data."; return; }
      if (s === "short") { statusEl.textContent = L.short || "Not enough data."; return; }
      showResult(place, s);
      cachePut(q, { name: place.name, admin1: place.admin1 || "",
                    country: place.country || "" }, s);
    }
    function esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
      });
    }

    // ---- the search dropdown ----
    var shown = [], cur = -1;
    function oclose() {
      box.hidden = true; box.innerHTML = ""; shown = []; cur = -1;
      input.setAttribute("aria-expanded", "false");
    }
    function scrollTo(id) {
      var el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    // Act on a chosen result: navigate to a city, filter the map to a continent,
    // filter the ranking to a country, or geocode an arbitrary place. The map and
    // ranking actions reuse the page's own controls so behaviour stays in one place.
    function act(it) {
      oclose();
      if (it.t === "city") { location.href = it.url; return; }
      if (it.t === "region") {
        var btn = document.querySelector('#map-region button[data-region="' + it.key + '"]');
        if (btn) btn.click();
        scrollTo("map");
      } else if (it.t === "country") {
        var rc = document.getElementById("rank-country-filter");
        if (rc) { rc.value = it.cc; rc.dispatchEvent(new Event("change")); }
        scrollTo("ranking");
      } else if (it.t === "place") {           // a geocoded world place (lat/lon known)
        input.blur(); scrollTo("omni"); lookupResolved(it.place);
      } else if (it.t === "anywhere") {
        input.blur(); scrollTo("omni"); lookupPlace(it.q);
      }
    }
    function omark(k) {
      var els = box.querySelectorAll(".omni-opt");
      Array.prototype.forEach.call(els, function (li, i) { li.classList.toggle("on", i === k); });
      cur = k;
      if (k >= 0 && els[k]) els[k].scrollIntoView({ block: "nearest" });
    }
    function ohead(text) {
      var h = document.createElement("li");
      h.className = "omni-h"; h.setAttribute("role", "presentation");
      h.textContent = text; box.appendChild(h);
    }
    function orow(it) {
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.className = "omni-opt" + (it.t === "anywhere" ? " omni-any" : "");
      var n = document.createElement("span"); n.className = "omni-n"; n.textContent = it.label;
      li.appendChild(n);
      if (it.sub) {
        var s = document.createElement("span"); s.className = "omni-sub"; s.textContent = it.sub;
        li.appendChild(s);
      }
      var idx = shown.length; shown.push(it);
      li.addEventListener("mousedown", function (e) { e.preventDefault(); act(it); });
      li.addEventListener("mousemove", function () { omark(idx); });
      box.appendChild(li);
    }
    function obuild(q, places) {
      shown = []; box.innerHTML = ""; cur = -1;
      var nq = onorm(q);
      if (!nq) { oclose(); return; }
      // Cities from our own set (localized + original name matched).
      var cm = 0;
      for (var i = 0; i < CITY.length && cm < 6; i++)
        if (CITY[i].key.indexOf(nq) >= 0) {
          if (cm === 0) ohead(L.g_cities || "Cities");
          orow({ t: "city", label: CITY[i].disp, sub: CITY[i].sub, url: CITY[i].url }); cm++;
        }
      // Countries from the loaded ranking payload (localized name matched).
      var countries = window.__countries || [], qm = 0, seen = {};
      for (var j = 0; j < countries.length && qm < 4; j++) {
        var cc = countries[j].cc; if (!cc || seen[cc]) continue;
        var nm = ocountry(cc);
        if (onorm(nm).indexOf(nq) >= 0) {
          seen[cc] = 1;
          if (qm === 0) ohead(L.g_countries || "Countries");
          orow({ t: "country", cc: cc, label: nm, sub: oflag(cc) }); qm++;
        }
      }
      // Continents / regions.
      var rm = 0;
      for (var k = 0; k < REGION.length; k++)
        if (REGION[k].nkey.indexOf(nq) >= 0) {
          if (rm === 0) ohead(L.g_regions || "Regions");
          orow({ t: "region", key: REGION[k].key, label: REGION[k].label }); rm++;
        }
      // Whole-world places from the geocoder (filled in async by scheduleGeo).
      if (places && places.length) {
        ohead(L.g_places || "Places");
        places.forEach(function (pl) { orow(pl); });
      }
      // Always offer the geocoded "any place" lookup last.
      orow({ t: "anywhere", q: q,
             label: (L.g_anywhere || 'Check any place: "{q}"').replace("{q}", q) });
      box.hidden = false; input.setAttribute("aria-expanded", "true");
    }
    // Debounced whole-world autocomplete: after a short pause, ask the Open-Meteo
    // geocoder (free, keyless, CORS) for matching places and merge them into the
    // dropdown. Stale responses (a newer query) are ignored.
    var geoTimer = null;
    function scheduleGeo(q) {
      if (geoTimer) { clearTimeout(geoTimer); geoTimer = null; }
      if (!q || onorm(q).length < 3) return;
      geoTimer = setTimeout(function () {
        fetch("https://geocoding-api.open-meteo.com/v1/search?count=6&language="
              + lang + "&name=" + encodeURIComponent(q))
          .then(function (r) { return r.ok ? r.json() : {}; })
          .then(function (g) {
            if (input.value.trim() !== q) return;   // a newer query superseded this
            var places = (g.results || []).map(function (p) {
              var lbl = p.name + (p.admin1 && p.admin1 !== p.name ? ", " + p.admin1 : "");
              return { t: "place", label: lbl, sub: p.country || "",
                       place: { name: p.name, admin1: p.admin1 || "",
                                country: p.country || "",
                                latitude: p.latitude, longitude: p.longitude } };
            });
            if (places.length) obuild(q, places);
          })
          .catch(function () {});
      }, 220);
    }
    function onQuery(q) { obuild(q, null); scheduleGeo(q); }
    input.addEventListener("input", function () { onQuery(input.value.trim()); });
    input.addEventListener("focus", function () { if (input.value.trim()) onQuery(input.value.trim()); });
    input.addEventListener("keydown", function (e) {
      if (box.hidden) {
        if (e.key === "Enter" && input.value.trim()) { e.preventDefault(); onQuery(input.value.trim()); }
        return;
      }
      if (e.key === "ArrowDown") { e.preventDefault(); omark(Math.min(cur + 1, shown.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); omark(Math.max(cur - 1, 0)); }
      else if (e.key === "Enter") { e.preventDefault(); var k = cur >= 0 ? cur : 0; if (shown[k]) act(shown[k]); }
      else if (e.key === "Escape") { oclose(); }
    });
    document.addEventListener("click", function (e) { if (!e.target.closest("#omni")) oclose(); });
  };

  // Per-country headline: a country picker (localized names) defaulting to the
  // page language's country, and a one-line warming stat built from a localized
  // template. Reuses the country aggregates from the ranking payload.
  function renderCountryStat(rows, tzcc) {
    var sec = document.getElementById("country-stat");
    var sel = document.getElementById("cstat-select");
    var line = document.getElementById("cstat-line");
    if (!sec || !sel || !line || !rows || !rows.length) return;
    var tmpl = sec.getAttribute("data-tmpl") || "";
    // Prefer the visitor's own country, guessed from their browser timezone
    // (offline, no permission); fall back to the page language's country.
    var want = sec.getAttribute("data-default") || "";
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz && tzcc && tzcc[tz]) want = tzcc[tz];
    } catch (e) {}
    var lang = (document.documentElement.lang || "en").split("-")[0];
    var names = null;
    try { names = new Intl.DisplayNames([lang], { type: "region" }); }
    catch (e) { names = null; }
    function name(cc) {
      var up = (cc || "").toUpperCase();
      if (names) { try { return names.of(up) || up; } catch (e) {} }
      return up;
    }
    var byCc = {};
    rows.forEach(function (r) { byCc[r.cc] = r; });
    // Options sorted by localized country name.
    var opts = rows.map(function (r) { return { cc: r.cc, nm: name(r.cc) }; });
    opts.sort(function (a, b) { return a.nm.localeCompare(b.nm, lang); });
    sel.innerHTML = "";
    opts.forEach(function (o) {
      var op = document.createElement("option");
      op.value = o.cc; op.textContent = flagEmoji(o.cc) + "  " + o.nm;
      sel.appendChild(op);
    });
    attachFlagTypeahead(sel);
    var tmplCool = sec.getAttribute("data-tmpl-cool") || tmpl;
    function show(cc) {
      var c = byCc[cc];
      if (!c) return;
      var trend = fmtSigned(c.t, 2);
      // Cooling countries get a template that doesn't say "warming faster than".
      line.innerHTML = (c.t >= 0 ? tmpl : tmplCool)
        .replace("{country}", "<b>" + name(cc) + "</b>")
        .replace("{trend}", trend)
        .replace("{pct}", c.pct)
        .replace("{rank}", c.rank)
        .replace("{total}", c.total);
    }
    var langDefault = sec.getAttribute("data-default") || "";
    var start = byCc[want] ? want
      : (byCc[langDefault] ? langDefault : opts[0].cc);
    sel.value = start;
    sel.addEventListener("change", function () { show(sel.value); });
    show(start);
  }

  // World warming-ranking table: one row per city, searchable by name,
  // filterable by continent, and sortable by clicking a column header. Each row
  // keeps its FIXED global rank (position by warming rate) so filtering/sorting
  // never changes "you're #123 worldwide". Country names are localized from the
  // ISO code (Intl.DisplayNames), so no name tables ship.
  function renderRanking(rows, countryRows, gt) {
    var body = document.getElementById("rank-body");
    if (!body || !rows || !rows.length) return;
    var lang = (document.documentElement.lang || "en").split("-")[0];
    var regionNames = null;
    try { regionNames = new Intl.DisplayNames([lang], { type: "region" }); }
    catch (e) { regionNames = null; }
    function country(cc) {
      var up = (cc || "").toUpperCase();
      if (regionNames) { try { return regionNames.of(up) || up; } catch (e) {} }
      return up;
    }
    function norm(s) {
      return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }
    function flagImg(cc) {
      var f = document.createElement("img");
      f.className = "rank-flag"; f.loading = "lazy"; f.width = 20; f.height = 15;
      f.alt = ""; f.src = "https://flagcdn.com/20x15/" + cc + ".png";
      return f;
    }
    // Localized city name from the shared table (window.__names), else the default.
    function localName(slug, def) {
      var m = window.__names;
      return (m && m[slug] && m[slug][lang]) || def;
    }
    // Small "W" that opens the city's Wikipedia article in the PAGE language.
    // Special:Search?...&go=Go behaves like the search-box Go button: an exact
    // title match jumps straight to the article, otherwise it shows results -
    // so it never 404s. Strip a trailing " (CC)" disambiguator (e.g. the two
    // Suzhous) since that suffix is ours, not part of any Wikipedia title.
    function wikiLink(name) {
      var q = name.replace(/\s*\([^)]*\)\s*$/, "").trim() || name;
      var a = document.createElement("a");
      a.className = "rank-wiki";
      a.href = "https://" + lang + ".wikipedia.org/wiki/Special:Search?search="
             + encodeURIComponent(q) + "&go=Go";
      a.target = "_blank"; a.rel = "noopener noreferrer";
      a.textContent = "W"; a.title = "Wikipedia: " + q;
      a.setAttribute("aria-label", "Wikipedia: " + q);
      return a;
    }
    function valTd(t) {
      var v = document.createElement("td");
      v.className = "rank-val " + (t >= 0 ? "warm" : "cool");
      v.textContent = fmtSigned(t, 2);
      return v;
    }
    // Inline warming stripes (Ed-Hawkins style): 9 decade-mean anomalies mapped
    // to a fixed blue->white->red scale so colours compare across rows.
    function lerp(a, b, t) { return Math.round(a + (b - a) * t); }
    function stripeColor(v) {
      if (v == null) return null;
      var lo = -1.0, hi = 1.5, x = Math.max(lo, Math.min(hi, v));
      if (x < 0) { var t = (x - lo) / (0 - lo);      // -1..0 -> blue..white
        return "rgb(" + lerp(8, 247, t) + "," + lerp(48, 247, t) + "," + lerp(107, 247, t) + ")"; }
      var u = x / hi;                                 // 0..1.5 -> white..red
      return "rgb(" + lerp(247, 103, u) + "," + lerp(247, 0, u) + "," + lerp(247, 13, u) + ")";
    }
    function stripesEl(st) {
      var wrap = document.createElement("span");
      wrap.className = "rank-stripes";
      if (!st || !st.length) return wrap;
      wrap.setAttribute("aria-hidden", "true");
      wrap.title = "1940s → 2020s";
      st.forEach(function (v) {
        var b = document.createElement("i");
        var c = stripeColor(v);
        if (c) b.style.background = c; else b.className = "empty";
        wrap.appendChild(b);
      });
      return wrap;
    }
    // "+2.4°C · 1.6×" - total warming across the record, and how many times the
    // world-city average rate (gt) this row warms. Both symbols are language-neutral.
    // Compact population: 1.4B / 38M / 800k people.
    function popText(p) {
      if (!p || p < 1000) return "";
      var n = p >= 1e9 ? (p / 1e9).toFixed(1) + "B"
        : p >= 1e6 ? Math.round(p / 1e6) + "M"
        : Math.round(p / 1e3) + "k";
      return n + " " + (window.__rankPeople || "people");
    }
    // "+2.4°C · 1.6× · 38M people" - total warming, times the world-city average
    // rate this row warms, and (countries only) how many people live there.
    function metaEl(dt, t, pop) {
      var s = document.createElement("span");
      s.className = "rc-meta";
      var parts = [];
      if (dt != null) parts.push(fmtSigned(dt, 1) + "°C");
      // "× the world average" only makes sense for a warming place; a negative
      // multiple would be nonsense for the handful of cities that have cooled.
      if (gt && gt > 0 && t != null && t > 0) parts.push((t / gt).toFixed(1) + "×");
      var pt = popText(pop);
      if (pt) parts.push(pt);
      s.textContent = parts.join(" · ");
      return s;
    }
    function cityCell(flagCc, nameNode, wikiNode, st, dt, t, pop) {
      var td = document.createElement("td");
      td.className = "rank-city";
      var top = document.createElement("div");
      top.className = "rc-top";
      top.appendChild(flagImg(flagCc));
      top.appendChild(nameNode);
      if (wikiNode) top.appendChild(wikiNode);
      var sub = document.createElement("div");
      sub.className = "rc-sub";
      sub.appendChild(stripesEl(st));
      sub.appendChild(metaEl(dt, t, pop));
      td.appendChild(top);
      td.appendChild(sub);
      return td;
    }
    // Each row element is built ONCE; filtering/sorting/paging re-append subsets.
    // CITY rows: rank, flag + city link, country, trend.
    var cityItems = rows.map(function (r, i) {
      var cty = country(r.cc);
      var tr = document.createElement("tr");
      var num = document.createElement("td");
      num.className = "rank-num"; num.textContent = String(i + 1);
      var dn = localName(r.s, r.n);   // localized display name (Munich -> Monachium)
      var a = document.createElement("a"); a.href = r.s + ".html"; a.textContent = dn;
      var c1 = cityCell(r.cc, a, wikiLink(dn), r.st, r.dt, r.t, r.pop);
      var c2 = document.createElement("td"); c2.className = "rank-cty"; c2.textContent = cty;
      tr.appendChild(num); tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(valTd(r.t));
      // Search matches the localized AND the default name, so either works.
      return { rank: i + 1, num: num, nn: norm(dn + " " + r.n), cc: r.cc, ccn: norm(cty),
               region: r.r || "", sec: 0, t: r.t, el: tr };
    });
    // COUNTRY rows: rank, flag + country name, city count, mean trend.
    var countryItems = (countryRows || []).map(function (c, i) {
      var cty = country(c.cc);
      var tr = document.createElement("tr");
      var num = document.createElement("td");
      num.className = "rank-num"; num.textContent = String(c.rank || i + 1);
      var nm = document.createElement("span"); nm.className = "rc-name"; nm.textContent = cty;
      var c1 = cityCell(c.cc, nm, null, c.st, c.dt, c.t, c.pop);
      var c2 = document.createElement("td"); c2.className = "rank-cty"; c2.textContent = String(c.n);
      tr.appendChild(num); tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(valTd(c.t));
      // Clicking a country row drops into city mode filtered to that country.
      tr.classList.add("rank-clickable");
      tr.title = country(c.cc);
      tr.addEventListener("click", function () { focusCountry(c.cc); });
      return { rank: c.rank || i + 1, num: num, nn: norm(cty), cc: c.cc, ccn: norm(cty),
               region: "", sec: c.n, t: c.t, el: tr };
    });

    var search = document.getElementById("rank-search");
    var regionSel = document.getElementById("rank-region");
    var countrySel = document.getElementById("rank-country-filter");
    if (countrySel) {   // populate the country filter (city mode)
      var seen = {}, clist = [];
      cityItems.forEach(function (it) {
        if (!seen[it.cc]) { seen[it.cc] = 1; clist.push({ cc: it.cc, nm: country(it.cc) }); }
      });
      clist.sort(function (a, b) { return a.nm.localeCompare(b.nm, lang); });
      clist.forEach(function (c) {
        var op = document.createElement("option");
        op.value = c.cc; op.textContent = flagEmoji(c.cc) + "  " + c.nm;
        countrySel.appendChild(op);
      });
      attachFlagTypeahead(countrySel);
    }
    var count = document.getElementById("rank-count");
    var empty = document.getElementById("rank-empty");
    var more = document.getElementById("rank-more");
    var heads = [].slice.call(document.querySelectorAll(".rank-sort"));
    // Column header labels: city mode shows City|Country, country mode Country|Cities.
    var toggle = document.getElementById("rank-toggle");
    var tbtns = toggle ? [].slice.call(toggle.querySelectorAll("button")) : [];
    var L_city = heads[1] ? heads[1].textContent : "";
    var L_country = heads[2] ? heads[2].textContent : "";
    var L_cities = tbtns[0] ? tbtns[0].textContent : L_city;
    if (!countryItems.length && toggle) toggle.style.display = "none";

    var LIMIT = 100;
    // Default mode follows whichever toggle button ships pre-marked .active in
    // the HTML (country by default - the country ranking is the headline view).
    var mode = "city";
    tbtns.forEach(function (x) { if (x.classList.contains("active")) mode = x.getAttribute("data-mode"); });
    var sortKey = "trend", sortDir = "desc", limit = LIMIT;
    function keyOf(h) { var k = h.getAttribute("data-key"); return k === "rank" ? "trend" : k; }
    function cmp(a, b) {
      var d;
      if (sortKey === "city") d = a.nn.localeCompare(b.nn, lang);
      else if (sortKey === "country")
        d = (mode === "country") ? (a.sec - b.sec) : a.ccn.localeCompare(b.ccn, lang);
      else d = a.t - b.t;
      d = sortDir === "asc" ? d : -d;      // direction applies to the primary key
      if (d === 0) d = a.rank - b.rank;    // ties always keep global-rank order
      return d;
    }
    function render() {
      var active = mode === "country" ? countryItems : cityItems;
      if (heads[1]) heads[1].textContent = (mode === "country" ? L_country : L_city);
      if (heads[2]) heads[2].textContent = (mode === "country" ? L_cities : L_country);
      heads.forEach(function (h) {
        h.setAttribute("aria-sort", keyOf(h) === sortKey
          ? (sortDir === "asc" ? "ascending" : "descending") : "none");
      });
      var q = search ? norm(search.value) : "";
      var reg = (mode === "city" && regionSel) ? regionSel.value : "";
      var ctry = (mode === "city" && countrySel) ? countrySel.value : "";
      var sel = active.filter(function (it) {
        return (!reg || it.region === reg) && (!ctry || it.cc === ctry) &&
          (!q || it.nn.indexOf(q) >= 0);
      });
      sel.sort(cmp);
      var shown = Math.min(limit, sel.length);
      // When a filter narrows the list, number it 1..N locally (keeping the fixed
      // global rank as a small "#123" beside it); unfiltered, the number IS the
      // global rank.
      var filtered = !!(reg || ctry || q);
      var frag = document.createDocumentFragment();
      for (var i = 0; i < shown; i++) {
        var it = sel[i];
        if (filtered) {
          it.num.innerHTML = "";
          it.num.appendChild(document.createTextNode(String(i + 1)));
          var gr = document.createElement("span");
          gr.className = "rank-grank"; gr.textContent = "#" + it.rank;
          it.num.appendChild(gr);
        } else {
          it.num.textContent = String(it.rank);
        }
        frag.appendChild(it.el);
      }
      body.innerHTML = "";
      body.appendChild(frag);
      if (count) count.textContent = shown + " / " + sel.length;
      if (empty) empty.hidden = sel.length > 0;
      if (more) {
        // Just the label - the running "shown / total" count (above) already
        // conveys progress; a "(NNN remaining)" here misreads as "clicking loads
        // all NNN", but each click only adds the next page.
        more.hidden = sel.length - shown <= 0;
        more.textContent = more.getAttribute("data-label") || "Show more";
      }
    }
    // Switch to city mode, filtered to one country (from a clicked country row).
    function focusCountry(cc) {
      mode = "city";
      tbtns.forEach(function (x) {
        x.classList.toggle("active", x.getAttribute("data-mode") === "city");
      });
      if (regionSel) { regionSel.style.display = ""; regionSel.value = ""; }
      if (countrySel) { countrySel.style.display = ""; countrySel.value = cc; }
      if (search) search.value = "";
      sortKey = "trend"; sortDir = "desc"; limit = LIMIT; render();
    }
    heads.forEach(function (h) {
      h.addEventListener("click", function () {
        var k = keyOf(h);
        if (k === sortKey) sortDir = sortDir === "asc" ? "desc" : "asc";
        else { sortKey = k; sortDir = (k === "trend") ? "desc" : "asc"; }
        limit = LIMIT; render();
      });
    });
    if (search) search.addEventListener("input", function () { limit = LIMIT; render(); });
    // Region and country are two granularities of the same "narrow it down"
    // gesture, so picking one clears the other (avoids empty intersections).
    if (regionSel) regionSel.addEventListener("change", function () {
      if (regionSel.value && countrySel) countrySel.value = "";
      limit = LIMIT; render();
    });
    if (countrySel) countrySel.addEventListener("change", function () {
      if (countrySel.value && regionSel) regionSel.value = "";
      limit = LIMIT; render();
    });
    if (more) more.addEventListener("click", function () { limit += LIMIT; render(); });
    // Cities / Countries toggle: swaps the dataset; the continent + country
    // filters only make sense for cities, so they hide in country mode.
    tbtns.forEach(function (b) {
      b.addEventListener("click", function () {
        mode = b.getAttribute("data-mode");
        tbtns.forEach(function (x) { x.classList.toggle("active", x === b); });
        var cityOnly = mode === "country" ? "none" : "";
        if (regionSel) { regionSel.style.display = cityOnly; regionSel.value = ""; }
        if (countrySel) { countrySel.style.display = cityOnly; countrySel.value = ""; }
        if (search) search.value = "";
        sortKey = "trend"; sortDir = "desc"; limit = LIMIT; render();
      });
    });
    // A link from a city page (index.html#cities / #countries) opens that mode.
    var hash = (location.hash || "").replace("#", "");
    if (hash === "cities" || hash === "countries") {
      mode = hash === "countries" ? "country" : "city";
      tbtns.forEach(function (x) {
        x.classList.toggle("active", x.getAttribute("data-mode") === mode);
      });
    }
    // Apply the initial mode's filter visibility (country mode hides city-only filters).
    if (mode === "country") {
      if (regionSel) regionSel.style.display = "none";
      if (countrySel) countrySel.style.display = "none";
    }
    render();
    if (hash === "cities" || hash === "countries") {
      var rsec = document.getElementById("ranking");
      if (rsec) rsec.scrollIntoView();
    }
  }

  // Called when the shared chart JSON fails to load: mark every not-yet-drawn
  // chart canvas as unavailable rather than leaving the page silently blank.
  window.chartsUnavailable = function (err) {
    if (window.console) console.error("charts data load failed", err);
    document.querySelectorAll(".chart-wrap canvas").forEach(function (el) {
      failNotice(el, el.id, err);
    });
  };

  // --- per-chart fullscreen -------------------------------------------------
  // Each chart figure gets a corner button that expands it to fill the screen
  // via the native Fullscreen API. Chart.js is responsive (maintainAspectRatio
  // off) and watches its container with a ResizeObserver, so it redraws to the
  // enlarged box on its own - no re-render call needed. ESC also exits.
  var ICON_EXPAND =
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3' +
    'M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
  var ICON_COLLAPSE =
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M8 3v3a2 2 0 0 1-2 2H3' +
    'M16 3v3a2 2 0 0 0 2 2h3M8 21v-3a2 2 0 0 0-2-2H3M16 21v-3a2 2 0 0 1 2-2h3"/></svg>';
  var ICON_RESET =
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7' +
    'L3 8"/><path d="M3 3v5h5"/></svg>';

  // The live Chart instance for a figure's canvas (if it has been drawn yet).
  function chartOf(fig) {
    var c = fig && fig.querySelector("canvas");
    return (c && window.__charts[c.id]) || null;
  }
  // A chart is zoomable only if it actually configured the zoom plugin (the
  // extremes/citybars charts don't), so the reset button appears only there.
  function isZoomable(chart) {
    return !!(chart && chart.options && chart.options.plugins &&
      chart.options.plugins.zoom && chart.options.plugins.zoom.zoom);
  }
  // Reset button: present on every zoomable chart (so it's always available),
  // and brightened (.z) while that chart is actually zoomed or panned.
  function syncFigureButtons() {
    document.querySelectorAll(".charts figure .rz-btn").forEach(function (b) {
      var chart = chartOf(b.parentNode), zoomable = isZoomable(chart);
      b.style.display = zoomable ? "" : "none";
      if (zoomable) {
        var z = typeof chart.isZoomedOrPanned === "function" &&
          chart.isZoomedOrPanned();
        b.classList.toggle("z", !!z);
      }
    });
  }

  function fsElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }
  function requestFs(el) {
    var fn = el.requestFullscreen || el.webkitRequestFullscreen;
    if (fn) { try { fn.call(el); } catch (e) { /* needs a user gesture */ } }
  }
  function exitFs() {
    var fn = document.exitFullscreen || document.webkitExitFullscreen;
    if (fn) fn.call(document);
  }
  function fsSupported(el) {
    return !!(el.requestFullscreen || el.webkitRequestFullscreen);
  }

  function initFullscreen() {
    var figs = document.querySelectorAll(".charts figure");
    if (!figs.length) return;
    var label = window.__cfs || "Fullscreen";
    var rzLabel = window.__crz || "Reset zoom";
    figs.forEach(function (fig) {
      // Only figures that actually hold a chart.
      if (!fig.querySelector("canvas")) return;
      // Reset-zoom button - always attached (hidden until the chart is zoomed),
      // so there is always a way back from a zoomed/panned view.
      if (!fig.querySelector(".rz-btn")) {
        var rz = document.createElement("button");
        rz.type = "button";
        rz.className = "rz-btn";
        rz.setAttribute("aria-label", rzLabel);
        rz.title = rzLabel;
        rz.innerHTML = ICON_RESET;
        rz.style.display = "none";
        rz.addEventListener("click", function (e) {
          e.preventDefault();
          var chart = chartOf(fig);
          if (chart && typeof chart.resetZoom === "function") chart.resetZoom();
          syncFigureButtons();
        });
        fig.appendChild(rz);
        // Refresh the zoomed-state highlight after any wheel/drag interaction
        // (more reliable than the plugin's completion callbacks alone).
        var cv = fig.querySelector("canvas");
        if (cv) {
          var refresh = function () { setTimeout(syncFigureButtons, 80); };
          cv.addEventListener("wheel", refresh, { passive: true });
          cv.addEventListener("pointerup", refresh);
        }
      }
      // Fullscreen button - only where the Fullscreen API is available.
      if (!fsSupported(fig) || fig.querySelector(".fs-btn")) return;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "fs-btn";
      btn.setAttribute("aria-label", label);
      btn.title = label;
      btn.innerHTML = ICON_EXPAND;
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        if (fsElement() === fig) exitFs(); else requestFs(fig);
      });
      fig.appendChild(btn);
    });
    syncFigureButtons();
    // Swap each button's icon to match its figure's fullscreen state.
    function onChange() {
      var cur = fsElement();
      document.querySelectorAll(".charts figure .fs-btn").forEach(function (b) {
        b.innerHTML = (b.parentNode === cur) ? ICON_COLLAPSE : ICON_EXPAND;
      });
    }
    document.addEventListener("fullscreenchange", onChange);
    document.addEventListener("webkitfullscreenchange", onChange);
  }

  // --- alias arrival --------------------------------------------------------
  // A search hit for a smaller city that shares THIS city's ~11 km Open-Meteo
  // grid cell links here as <primary>.html#as=<name>. Both places resolve to the
  // same reanalysis point, so the record shown IS the searched city's climate:
  // relabel the heading to that name and note the shared cell. One committed
  // dataset is thus reachable by every overlapping city name, with no per-name
  // page or duplicated 85-year record.
  function initAliasHeading() {
    var m = /(?:^|[#&])as=([^&]*)/.exec(location.hash || "");
    var head = document.getElementById("pagehead");
    if (!m || !head) return;
    var alias;
    try { alias = decodeURIComponent(m[1].replace(/\+/g, " ")).trim(); }
    catch (e) { return; }
    if (!alias) return;
    var header = head.closest("header");
    var primary = (header && header.getAttribute("data-name")) || head.textContent;
    if (!primary) return;

    // The record is the primary's grid cell, which IS the searched town's
    // climate - so make the whole visible page read about the town the visitor
    // asked for, not the primary. Replace every visible mention of the primary
    // name (heading, subtitle, the 1940/2050 analog lines, chart titles) with
    // the alias. Text nodes only, so hrefs/data-* keep the primary's slug. The
    // shared-cell note below (appended after) is the one place both are named.
    if (primary !== alias) {
      var swap = function (root) {
        if (!root) return;
        var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
        var hits = [], n;
        while ((n = w.nextNode()))
          if (n.nodeValue.indexOf(primary) >= 0) hits.push(n);
        hits.forEach(function (t) { t.nodeValue = t.nodeValue.split(primary).join(alias); });
      };
      swap(header);
      swap(document.querySelector("main"));
      document.title = document.title.indexOf(primary) >= 0
        ? document.title.split(primary).join(alias)
        : alias + " - " + document.title;
    }
    head.textContent = alias;

    // Explain WHY this town shows another place's record: they share one
    // reanalysis grid cell. Both names appear here for full transparency.
    var tmpl = header && header.getAttribute("data-gridnote");
    if (tmpl && header) {
      var note = document.createElement("p");
      note.className = "grid-alias-note";
      note.style.cssText = "margin:.35rem 0 0;font-size:.85rem;opacity:.75;max-width:52ch";
      note.textContent = tmpl.replace(/\{alias\}/g, alias).replace(/\{city\}/g, primary);
      header.appendChild(note);
    }
  }

  // Type-to-filter city search in the top bar. The list is the shared,
  // browser-cached window.__cpData (from _cities.js); moved here from a per-page
  // inline <script> so it is not duplicated across every city page. No-ops on
  // pages without the search box (e.g. the map/index page).
  function initCityPicker() {
    var inp = document.getElementById("cp-search");
    var box = document.getElementById("cp-results");
    if (!inp || !box) return;
    var C = window.__cpData || { c: [] };
    function norm(s) {
      return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }
    var N = C.c.map(function (c) { return norm(c[0]); });
    var cur = -1, shown = [];
    function close() {
      box.hidden = true; inp.setAttribute("aria-expanded", "false"); cur = -1;
    }
    function go(i) { var c = C.c[i]; if (c) location.href = c[1]; }
    function mark(k) {
      [].forEach.call(box.children, function (li, i) {
        li.classList.toggle("on", i === k);
      });
      cur = k;
      if (k >= 0 && box.children[k]) {
        box.children[k].scrollIntoView({ block: "nearest" });
      }
    }
    function render(q) {
      var nq = norm(q); shown = []; box.innerHTML = "";
      if (!nq) { close(); return; }
      for (var i = 0; i < C.c.length && shown.length < 60; i++) {
        if (N[i].indexOf(nq) >= 0) shown.push(i);
      }
      if (!shown.length) { close(); return; }
      shown.forEach(function (idx) {
        var c = C.c[idx];
        var li = document.createElement("li");
        li.setAttribute("role", "option");
        var n = document.createElement("span"); n.textContent = c[0];
        var s = document.createElement("span");
        s.className = "cp-sub"; s.textContent = c[2];
        li.appendChild(n); li.appendChild(s); box.appendChild(li);
      });
      box.hidden = false; inp.setAttribute("aria-expanded", "true"); cur = -1;
    }
    inp.addEventListener("input", function () { render(inp.value); });
    inp.addEventListener("focus", function () { if (inp.value) render(inp.value); });
    inp.addEventListener("keydown", function (e) {
      if (box.hidden) return;
      if (e.key === "ArrowDown") {
        e.preventDefault(); mark(Math.min(cur + 1, box.children.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault(); mark(Math.max(cur - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault(); var k = cur >= 0 ? cur : 0;
        if (shown[k] != null) go(shown[k]);
      } else if (e.key === "Escape") { close(); }
    });
    box.addEventListener("mousedown", function (e) {
      var li = e.target.closest("li"); if (!li) return;
      e.preventDefault();
      var k = [].indexOf.call(box.children, li);
      if (shown[k] != null) go(shown[k]);
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".cp-combo")) close();
    });
  }

  // "Your region" hero (landing page only). Opens on the visitor's nearest city
  // that already has records: geolocate, then snap READ-ONLY to the nearest
  // covered city (window.__omniData.g) and show its warming stat from the
  // already-loaded ranking (window.__ranking). Never triggers an Open-Meteo
  // fetch. Degrades silently: on denied/unavailable/insecure-context geolocation
  // the server-rendered default city stays, with no console error.
  var HERO_NEAR_DEG = 0.15;   // ~16 km: within one reanalysis cell -> same record
  function heroNearestSlug(lat, lon) {
    var g = (window.__omniData && window.__omniData.g) || [];
    var best = null, bestD = Infinity, cl = Math.cos(lat * Math.PI / 180);
    for (var i = 0; i < g.length; i++) {
      var dy = lat - g[i][0], dx = (lon - g[i][1]) * cl, d = dy * dy + dx * dx;
      if (d < bestD) { bestD = d; best = g[i][2]; }
    }
    return bestD <= HERO_NEAR_DEG * HERO_NEAR_DEG ? best : null;
  }
  function heroCityName(slug) {
    var c = (window.__omniData && window.__omniData.c) || [];
    var url = slug + ".html";
    for (var i = 0; i < c.length; i++) if (c[i][1] === url) return c[i][0];
    return null;
  }
  function heroSet(id, txt) {
    var el = document.getElementById(id);
    if (el) el.textContent = txt;
  }
  // A city's decade anomalies -> a hard-stop warming-stripes gradient for the
  // hero backdrop (mirrors _stripe_gradient_css in report.py).
  function heroStripeBg(st) {
    if (!st || !st.length) return null;
    var n = st.length, stops = [];
    for (var i = 0; i < n; i++) {
      stops.push(luStripeColor(st[i]) + " " + (i * 100 / n).toFixed(2) + "% "
                 + ((i + 1) * 100 / n).toFixed(2) + "%");
    }
    return "linear-gradient(96deg," + stops.join(",") + ")";
  }
  // A city's decade anomalies -> a filled area chart for the "your region" hero,
  // the same idiom as the map card and the city-page hero (_hero_spark_svg in
  // report.py). Colour flows from --warm/--cool via the .warm/.cool class +
  // currentColor, so a theme switch re-tints it; nulls skipped; "" if < 2 decades.
  function heroSpark(st, alt) {
    if (!st || !st.length) return "";
    var pts = [];
    for (var i = 0; i < st.length; i++) if (st[i] != null) pts.push([i, st[i]]);
    if (pts.length < 2) return "";
    var W = 880, H = 132, padX = 6, padT = 12, padB = 12;
    var vals = pts.map(function (p) { return p[1]; });
    var lo = Math.min.apply(null, vals.concat(0));
    var hi = Math.max.apply(null, vals.concat(0.001));
    var rng = (hi - lo) || 1, iw = W - 2 * padX, ih = H - padT - padB, span = (st.length - 1) || 1;
    function X(i) { return padX + i * (iw / span); }
    function Y(v) { return padT + ih - ((v - lo) / rng) * ih; }
    var lv = pts[pts.length - 1][1], cls = lv >= 0 ? "warm" : "cool";
    var zero = Y(0).toFixed(1);
    var poly = pts.map(function (p) { return X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1); }).join(" ");
    var x0 = X(pts[0][0]).toFixed(1), xn = X(pts[pts.length - 1][0]).toFixed(1);
    return '<svg class="rh-spark ' + cls + '" viewBox="0 0 ' + W + ' ' + H
      + '" role="img" aria-label="' + (alt || "") + '">'
      + '<line class="rh-spark-base" x1="' + padX + '" y1="' + zero + '" x2="' + (W - padX) + '" y2="' + zero + '"/>'
      + '<defs><linearGradient id="rhg" x1="0" y1="0" x2="0" y2="1">'
      + '<stop class="rh-spark-g0" offset="0"/><stop class="rh-spark-g1" offset="1"/></linearGradient></defs>'
      + '<polygon class="rh-spark-fill" points="' + x0 + ',' + zero + ' ' + poly + ' ' + xn + ',' + zero + '"/>'
      + '<polyline class="rh-spark-line" points="' + poly + '"/>'
      + '<circle class="rh-spark-dot" cx="' + xn + '" cy="' + Y(lv).toFixed(1) + '" r="4"/></svg>';
  }
  // Share of cities warming slower than this one (from the sorted __trends).
  function heroPercentile(t) {
    var T = window.__trends || [];
    if (!T.length) return null;
    var below = 0;
    for (var i = 0; i < T.length; i++) if (T[i] < t) below++;
    return Math.round(100 * below / T.length);
  }
  // Apply the visitor's resolved position to the hero. Needs both a resolved
  // position and the loaded ranking; a no-op until both are present, and called
  // again from renderGlobal so it runs whenever the second one arrives.
  // --- Country border silhouette behind the hero (engraved-outline treatment) ---
  // Border paths ship once in charts/country_outlines.json (keyed by lowercase
  // ISO alpha-2) and are fetched lazily, so the geometry is never duplicated into
  // the (cities x languages) pages. non-scaling-stroke keeps a constant ~1px line
  // whatever the country's own viewBox.
  var __outlinesP = null;
  function heroOutlines() {
    if (!__outlinesP) {
      __outlinesP = fetch("../charts/country_outlines.json")
        .then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; });
    }
    return __outlinesP;
  }
  function injectHeroOutline(host, cc) {
    cc = (cc || "").toLowerCase();
    if (!host || !/^[a-z]{2}$/.test(cc)) return;
    if (host.getAttribute("data-outline") === cc) return;  // already drawn
    heroOutlines().then(function (map) {
      var o = map[cc], box = host.querySelector(".rh-silho");
      if (!o) { if (box) box.parentNode.removeChild(box);
                host.removeAttribute("data-outline"); return; }
      if (!box) {
        box = document.createElement("div");
        box.className = "rh-silho";
        box.setAttribute("aria-hidden", "true");
        host.insertBefore(box, host.firstChild);  // behind the scrim + content
      }
      box.innerHTML = '<svg viewBox="0 0 ' + o.w + ' ' + o.h + '" '
        + 'preserveAspectRatio="xMidYMid meet"><path d="' + o.d + '" '
        + 'fill="rgba(255,255,255,.06)" stroke="rgba(255,255,255,.55)" '
        + 'stroke-width="1.15" vector-effect="non-scaling-stroke" '
        + 'stroke-linejoin="round"></path></svg>';
      host.setAttribute("data-outline", cc);
    });
  }
  function initCityHeroOutline() {
    var h = document.querySelector("header.region-hero[data-cc]");
    if (h) injectHeroOutline(h, h.getAttribute("data-cc"));
  }

  function applyHero() {
    var host = document.getElementById("region-hero");
    if (!host || !window.__heroPos) return;
    var rank = window.__ranking;
    if (!rank || !rank.length) return;
    var slug = heroNearestSlug(window.__heroPos.lat, window.__heroPos.lon);
    if (!slug) { heroSet("rh-hint", host.getAttribute("data-default-note") || ""); return; }
    var entry = null;
    for (var i = 0; i < rank.length; i++) {
      if (rank[i].s === slug) { entry = rank[i]; break; }
    }
    if (!entry) return;
    // Never update the hero from a partial row: if the trend/since numbers are
    // missing, keep the coherent server-rendered default rather than pairing a
    // new city name with a stale number.
    if (typeof entry.t !== "number" || typeof entry.dt !== "number") return;
    var name = heroCityName(slug) || entry.n;
    heroSet("rh-name", name);
    heroSet("rh-trend", fmtSigned(entry.t, 2));
    heroSet("rh-cta-label", (host.getAttribute("data-cta") || "{name}")
      .replace("{name}", name));
    var link = document.getElementById("rh-link");
    if (link) link.setAttribute("href", slug + ".html");
    heroSet("rh-hint", host.getAttribute("data-near") || "");
    // Swap the ribbon to this city's own warming stripes (the base gradient is
    // fixed; --rh-stripes drives the bottom data ribbon, see .region-hero::before).
    var bg = heroStripeBg(entry.st);
    if (bg) host.style.setProperty("--rh-stripes", bg);
    // Swap the decade area chart to this city (same idiom as the city page).
    var sp = document.getElementById("rh-spark");
    if (sp) sp.innerHTML = heroSpark(entry.st, host.getAttribute("data-chart-alt") || "");
    // Draw this city's country border silhouette behind the hero.
    injectHeroOutline(host, entry.cc);
    // Rebuild the secondary line: total warming since 1940 + rate percentile.
    var since = (host.getAttribute("data-since") || "{v}")
      .replace("{v}", fmtSigned(entry.dt, 1) + " °C");
    var meta = document.getElementById("rh-meta");
    if (meta) {
      var pct = heroPercentile(entry.t);
      var faster = (pct != null)
        ? (host.getAttribute("data-faster") || "").replace("{pct}", pct) : "";
      meta.innerHTML = "";
      var b = document.createElement("b"); b.textContent = since;
      meta.appendChild(b);
      if (faster) meta.appendChild(document.createTextNode(" · " + faster));
    }
    // Climate analog ("in 1940 it felt like X; by 2050, like Y") for this city,
    // from the shared per-city analogs. Localise the look-alike city's name via
    // the shared names table; templates come from the hero's data attributes.
    var box = document.getElementById("rh-analog");
    if (box) {
      var lang = (document.documentElement.lang || "en").split("-")[0];
      var ana = (window.__analogs || {})[slug] || {};
      function locName(a) {
        var m = window.__names && window.__names[a.s];
        return (m && (m[lang] || m.en)) || a.n;
      }
      function fill(tmpl, a) {
        return tmpl.replace("{city}", name).replace("{analog}", locName(a))
                   .replace("{d}", a.d);
      }
      var lines = [];
      var pT = host.getAttribute("data-analog-past");
      var fT = host.getAttribute("data-analog-future");
      if (ana.past && pT) lines.push(fill(pT, ana.past));
      if (ana.future && fT) lines.push(fill(fT, ana.future));
      box.innerHTML = "";
      if (lines.length) {
        box.className = "analog";
        var em = document.createElement("span");
        em.className = "analog-emoji"; em.setAttribute("aria-hidden", "true");
        em.textContent = "🌡️";
        var wrap = document.createElement("div"); wrap.className = "analog-lines";
        lines.forEach(function (l) {
          var p = document.createElement("p"); p.className = "analog-line";
          p.textContent = l; wrap.appendChild(p);
        });
        box.appendChild(em); box.appendChild(wrap);
      } else { box.className = ""; }
    }
  }
  window.applyHero = applyHero;
  function initHero() {
    var host = document.getElementById("region-hero");
    if (!host || host.getAttribute("data-geo") === "1") return;
    host.setAttribute("data-geo", "1");
    applyHero();   // in case the ranking + a cached position are already present
    // Graceful fallback: no Geolocation API, or an insecure context (file://,
    // plain http) where it is blocked - keep the server-rendered default city.
    if (!navigator.geolocation || window.isSecureContext === false) return;
    heroSet("rh-hint", host.getAttribute("data-locating")
      || (document.getElementById("rh-hint") || {}).textContent || "");
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        window.__heroPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        applyHero();
      },
      function () {   // denied or unavailable: restore the default note, keep city
        heroSet("rh-hint", host.getAttribute("data-default-note") || "");
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 6 * 3600e3 }
    );
  }

  // Localized client-side UI strings baked per page as window.__tpref by
  // report.py (_tpref_i18n); the inline English stays as the fallback.
  function TP(k, fb) {
    try { return (window.__tpref && window.__tpref[k]) || fb; }
    catch (e) { return fb; }
  }

  // Warming badge in the topbar: the REAL world-city average warming since 1940,
  // computed from this site's data (charts/_world.json). Never fabricated - if
  // the figure is unavailable, no badge is shown at all.
  function initHeatBadge() {
    var nav = document.querySelector(".topbar .tb-nav")
      || document.querySelector(".topbar-in");
    if (!nav || nav.querySelector(".heat-badge")) return;
    fetch("../charts/_world.json").then(function (r) { return r.ok ? r.json() : null; })
      .then(function (w) {
        if (!w || typeof w.gdt !== "number" || nav.querySelector(".heat-badge")) return;
        var b = document.createElement("span");
        b.className = "heat-badge";
        // Focusable + labelled so the explanation is reachable by keyboard and
        // announced by screen readers, not just on mouse hover.
        b.tabIndex = 0;
        b.title = TP("hb_title",
          "Average warming of the world's major cities since 1940, "
          + "equal-weighted, computed from this site's data");
        // Built as nodes (not innerHTML) so a localized string is never parsed
        // as markup. Reads: [dot] World cities +1.1 °C since 1940
        var dot = document.createElement("span"); dot.className = "hb-dot";
        var lab = document.createElement("span"); lab.className = "hb-lab";
        // "(2194)" is appended parenthetically: it answers "averaged over what?"
        // and needs no grammar, so it works in every language with no new string.
        // Omitted entirely when the count is absent - never invent one.
        lab.textContent = TP("hb_world", "World cities")
          + (typeof w.gn === "number" && w.gn > 0 ? " (" + w.gn.toLocaleString() + ")" : "");
        var since = document.createElement("span"); since.className = "hb-since";
        since.textContent = TP("hb_since", "since 1940");
        b.appendChild(dot);
        b.appendChild(lab);
        b.appendChild(document.createTextNode(" " + fmtSigned(w.gdt, 1) + " °C "));
        b.appendChild(since);
        b.setAttribute("aria-label",
          b.textContent.replace(/\s+/g, " ").trim() + ". " + b.title);
        nav.appendChild(b);
      }).catch(function () {});
  }
  function initPage() {
    initFullscreen(); initAliasHeading(); initCityPicker(); initHero();
    initCityHeroOutline(); initHeatBadge();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPage);
  } else {
    initPage();
  }
})();

// --- Interactive range/records widgets ------------------------------------
// Global (outside the IIFE) so a city page's draw(C) - which runs after its
// charts/<slug>.json fetch resolves - can init these from the shared payload
// (C._range / C._records). Moved here from a per-page inline <script> so the
// ~3 KB of widget code is downloaded once (cached) instead of inlined into
// every city page in every language. Month labels come from window.__cmonths.
// Chrome colours for the standalone widgets read the live theme CSS vars on
// <html> (same contract as the in-IIFE chartMuted/chartGrid/chartLine). Read
// on each build so a theme-switch rebuild picks up the new palette.
function _cssv(n, fb){ try { var v = getComputedStyle(document.documentElement).getPropertyValue(n).trim(); return v || fb; } catch(e){ return fb; } }
// Warm/cool encoding for the widgets below, which live outside the main chart
// module. Read per build (they are destroyed and rebuilt on 'themechange'),
// with the light hexes as the fallback if the tokens are ever absent.
function _warm(){ return _cssv('--warm', '#d62728'); }
function _cool(){ return _cssv('--cool', '#2c7fb8'); }
// Register a range/records widget's destroy/rebuild pair so a 'themechange'
// (via window.__applyChartTheme) can re-theme it. Keyed by canvas base id so a
// re-init of the same widget overwrites rather than accumulating entries.
function _registerExtraChart(base, destroy, rebuild) {
  window.__extraCharts = window.__extraCharts || {};
  window.__extraCharts[base] = {destroy: destroy, rebuild: rebuild};
}
function _opts(months) {
  var mu = _cssv('--muted', '#475569');
  return {responsive: true, maintainAspectRatio: false,
    interaction: {intersect: false, mode: 'index'},
    plugins: {legend: {labels: {boxWidth: 12, color: mu}}},
    scales: {x: {offset: true, ticks: {color: mu}},
             y: {ticks: {color: mu},
                 title: {display: true, text: '°C', color: mu}}}};
}
function buildRange(base, d, months) {
  var years = Object.keys(d.years);
  var sel = document.getElementById(base + '-y');
  var chart;
  function build() {
    var initial = (sel && sel.value) || years[years.length - 1];
    var mu = _cssv('--muted', '#475569'), ln = _cssv('--line', '#eceae4');
    chart = new Chart(document.getElementById(base).getContext('2d'), {
      type: 'line',
      data: {labels: months, datasets: [
        {label: 'max', data: d.max, borderColor: mu,
         borderWidth: 1, pointRadius: 0, fill: false},
        {label: 'min', data: d.min, borderColor: mu,
         backgroundColor: ln, borderWidth: 1,
         pointRadius: 0, fill: '-1'},
        {label: 'avg', data: d.avg, borderColor: mu, borderDash: [5, 4],
         borderWidth: 1.5, pointRadius: 0},
        {label: initial, data: d.years[initial], borderColor: _warm(),
         backgroundColor: _warm(), showLine: false, pointRadius: 4,
         spanGaps: true}
      ]}, options: _opts(months)});
  }
  build();
  sel.addEventListener('change', function () {
    chart.data.datasets[3].label = sel.value;
    chart.data.datasets[3].data = d.years[sel.value];
    chart.update();
  });
  _registerExtraChart(base, function () { try { chart.destroy(); } catch (e) {} }, build);
}
function buildRecords(base, d, months) {
  var years = Object.keys(d.years);
  var sel = document.getElementById(base + '-y');
  var chart;
  function build() {
    var initial = (sel && sel.value) || years[years.length - 1];
    var ln = _cssv('--line', '#eceae4');
    chart = new Chart(document.getElementById(base).getContext('2d'), {
      type: 'line',
      data: {labels: months, datasets: [
        {label: 'rec high', data: d.recHigh, borderColor: 'rgba(185,28,28,.5)',
         borderWidth: 1, pointRadius: 0, fill: false},
        {label: 'rec low', data: d.recLow, borderColor: 'rgba(29,78,216,.5)',
         backgroundColor: ln, borderWidth: 1,
         pointRadius: 0, fill: '-1'},
        {label: initial + ' ▲', data: d.years[initial].high,
         borderColor: _warm(), backgroundColor: _warm(), showLine: false,
         pointRadius: 4, spanGaps: true},
        {label: initial + ' ▼', data: d.years[initial].low,
         borderColor: _cool(), backgroundColor: _cool(), showLine: false,
         pointRadius: 4, spanGaps: true}
      ]}, options: _opts(months)});
  }
  build();
  sel.addEventListener('change', function () {
    var y = sel.value;
    chart.data.datasets[2].label = y + ' ▲';
    chart.data.datasets[2].data = d.years[y].high;
    chart.data.datasets[3].label = y + ' ▼';
    chart.data.datasets[3].data = d.years[y].low;
    chart.update();
  });
  _registerExtraChart(base, function () { try { chart.destroy(); } catch (e) {} }, build);
}
