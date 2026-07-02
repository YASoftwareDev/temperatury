/* Interactive climate charts (Chart.js) — one builder per archetype.
 *
 * Each city page embeds a language-neutral JSON payload per chart (numbers +
 * English label strings) and calls renderChart(canvasId, payload). Labels are
 * localised in-browser via window.__ci18n ({english: localized}, the same map
 * that localised the old SVG text); month names via window.__cmonths. So the
 * data is shared across all 21 languages and only the labels differ per page.
 *
 * Interactions come free from Chart.js — hover tooltips (exact values),
 * click-legend to toggle a series — plus scroll-zoom / drag-pan on the year
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
  // A label may carry a "\n" (multi-line axis title) — Chart.js takes an array.
  function lines(s) { return T(s).split("\n"); }

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
  var MUTED = "#475569";
  function baseOpts(extra) {
    var o = {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { labels: { boxWidth: 12, usePointStyle: true, color: MUTED } },
        tooltip: { callbacks: {} }
      },
      scales: {}
    };
    return Object.assign(o, extra || {});
  }
  // Legend that omits datasets flagged __hidden (raw points / trend lines whose
  // value is already conveyed by the LOESS entry) — an explicit flag rather than
  // matching an invisible label string.
  function hideLegend() {
    return {
      labels: { boxWidth: 12, usePointStyle: true, color: MUTED,
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
  // Scroll/pinch-zoom + drag-pan on the x (year) axis.
  function zoomPlugin() {
    return {
      zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
      pan: { enabled: true, mode: "x" }
    };
  }
  function yearScale(title) {
    return { type: "linear", title: { display: !!title, text: title, color: MUTED },
      ticks: { color: MUTED, callback: function (v) { return "" + v; },
        maxRotation: 0, autoSkipPadding: 20 },
      grid: { color: "#eceae4" } };
  }
  function valScale(title) {
    return { title: { display: !!title, text: title, color: MUTED },
      ticks: { color: MUTED }, grid: { color: "#eceae4" } };
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
      data: p.raw.data, borderColor: p.raw.color,
      backgroundColor: isBar ? p.raw.color + "73" : p.raw.color,
      borderWidth: 0, pointRadius: isBar ? 0 : 2.4,
      showLine: false, order: 3
    };
    var loess = {
      type: "line", label: T(p.loess.label), data: p.loess.data,
      borderColor: p.loess.color, borderWidth: 2.6, pointRadius: 0,
      tension: 0.3, order: 1
    };
    var trend = {
      type: "line", label: T(p.trend.label), data: p.trend.line,
      borderColor: p.trend.color, borderWidth: 1.6, borderDash: [6, 4],
      pointRadius: 0, order: 2
    };
    return new Chart(ctx, {
      type: isBar ? "bar" : "line",
      data: { labels: p.x, datasets: [raw, loess, trend] },
      options: baseOpts({
        plugins: { legend: hideLegend(), zoom: zoomPlugin() },
        scales: { x: yearScale(lines(p.xlabel)[0]), y: valScale(lines(p.ylabel)) }
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
        borderColor: s.color, showLine: false, pointRadius: 2.2,
        pointBackgroundColor: s.color + "b0", order: 3 });
      ds.push({ type: "line", group: g, label: T(s.label), data: s.loess,
        borderColor: s.color, borderWidth: 2.6, pointRadius: 0, tension: 0.3,
        order: 1 });
      if (s.trend) {
        ds.push({ type: "line", group: g, __hidden: true, data: s.trend,
          borderColor: s.color, borderWidth: 1.3, borderDash: [6, 4],
          pointRadius: 0, order: 2 });
      }
    });
    return new Chart(ctx, {
      type: "line", data: { labels: p.x, datasets: ds },
      options: baseOpts({
        plugins: { legend: hideLegend(), zoom: zoomPlugin() },
        scales: { x: yearScale(lines(p.xlabel)[0]), y: valScale(lines(p.ylabel)) }
      })
    });
  }

  // Anomaly bars: diverging bars (blue cool / red warm) + LOESS overlay.
  function mkAnomalyBars(ctx, p) {
    var colors = p.values.map(function (v) {
      return v == null ? "#ccc" : (v >= 0 ? p.posColor : p.negColor);
    });
    var bars = { type: "bar", data: p.values,
      backgroundColor: colors, borderWidth: 0, order: 2 };
    var smooth = { type: "line", data: p.loess, borderColor: "#0f172a",
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
        scales: { x: yearScale(lines(p.xlabel)[0]), y: valScale(lines(p.ylabel)) }
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
          x: { type: "category", ticks: { color: MUTED, autoSkip: true,
            maxRotation: 0, autoSkipPadding: 24 }, grid: { display: false },
            title: { display: true, text: lines(p.xlabel)[0], color: MUTED } },
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
        { label: T(p.early.label), data: p.early.data, borderColor: p.early.color,
          backgroundColor: p.early.color, borderWidth: 2, pointRadius: 3,
          tension: 0.35 },
        { label: T(p.late.label), data: p.late.data, borderColor: p.late.color,
          backgroundColor: p.late.color + "22", borderWidth: 2, pointRadius: 3,
          tension: 0.35, fill: "-1" }
      ] },
      options: baseOpts({
        scales: { x: { ticks: { color: MUTED }, grid: { display: false } },
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
              return T(p.cbarLabel) + ": " + (v == null ? "—" : v + " °C");
            } } }
        },
        scales: {
          x: { type: "category", labels: mon, offset: true,
            ticks: { color: MUTED }, grid: { display: false },
            title: { display: true, text: lines(p.xlabel)[0], color: MUTED } },
          y: { type: "linear", offset: true,
            min: p.years[0] - 0.5, max: p.years[p.years.length - 1] + 0.5,
            ticks: { color: MUTED, callback: function (v) { return "" + v; } },
            grid: { display: false },
            title: { display: true, text: lines(p.ylabel)[0], color: MUTED } }
        }
      })
    });
  }

  var BUILDERS = {
    trend: mkTrend, multitrend: mkMultitrend, anomalybars: mkAnomalyBars,
    stripes: mkStripes, seasonshift: mkSeasonShift, matrix: mkMatrix
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

  window.renderChart = function (canvasId, payload) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var fn = BUILDERS[payload && payload.kind];
    if (!fn) { failNotice(el, canvasId, "unknown chart kind: " + (payload && payload.kind)); return null; }
    try { return fn(el.getContext("2d"), payload); }
    catch (e) { failNotice(el, canvasId, e); return null; }
  };

  // Called when the shared chart JSON fails to load: mark every not-yet-drawn
  // chart canvas as unavailable rather than leaving the page silently blank.
  window.chartsUnavailable = function (err) {
    if (window.console) console.error("charts data load failed", err);
    document.querySelectorAll(".chart-wrap canvas").forEach(function (el) {
      failNotice(el, el.id, err);
    });
  };
})();
