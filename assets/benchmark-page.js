"use strict";
(function () {

  /* ── Globals ─────────────────────────────────────────────────── */

  const CFG = window.BENCHMARK_CONFIG;

  /* ── Utilities ───────────────────────────────────────────────── */

  function xmlText(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[c])
    );
  }

  function safeText(v, fallback) {
    return typeof v === "string" && v.trim() ? v.trim() : (fallback || "Unknown method");
  }

  function methodLabel(r) {
    return safeText(r.method_name || r.author_name || r.tool_name);
  }

  function fmt(value, digits, unit) {
    if (!Number.isFinite(value)) return "—";
    const s = value.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits != null ? digits : 3,
    });
    return unit ? s + " " + unit : s;
  }

  // Resolve a dotted path like "pixel_f1.f1" against an object.
  function getPath(obj, path) {
    if (!path || obj == null) return undefined;
    return path.split(".").reduce(function (acc, k) {
      return acc != null ? acc[k] : undefined;
    }, obj);
  }

  // Derive a human-readable label and unit from a column name like "height_m".
  function colMeta(col) {
    var knownUnits = { m: "m", km: "km", cm: "cm", mm: "mm", s: "s", ms: "ms", pct: "%" };
    var parts = col.split("_");
    var rawUnit = parts[parts.length - 1];
    var unit = knownUnits[rawUnit] || "";
    var labelParts = unit ? parts.slice(0, -1) : parts;
    var label = labelParts.map(function (p) {
      return p.charAt(0).toUpperCase() + p.slice(1);
    }).join(" ");
    return { label: label, unit: unit };
  }

  // Convert a reported field name to a display label (kappa → κ, Tc → T_c).
  function fieldLabel(f) {
    if (f === "kappa") return "κ";
    if (f === "Tc") return "Tₐ";
    return f;
  }

  // Dynamic chart container height: scale with the number of rows.
  function chartH(n) { return Math.max(200, n * 52 + 60); }

  /* ── Chart instance management ───────────────────────────────── */
  // Instances are stored on the canvas element to allow safe recreation on
  // toggle changes without tracking extra module-level state.

  function destroyChart(canvasEl) {
    if (canvasEl && canvasEl._bpChart) {
      canvasEl._bpChart.destroy();
      canvasEl._bpChart = null;
    }
  }

  // Show an empty-state message inside a chart container, destroying any
  // existing chart on the canvas so it can be re-created later.
  function showEmpty(containerEl, message) {
    var canvas = containerEl.querySelector("canvas");
    if (canvas) destroyChart(canvas);
    // Hide canvas, show/create a sibling empty-state div.
    if (canvas) canvas.style.display = "none";
    var existing = containerEl.querySelector(".chart-empty");
    if (existing) {
      existing.textContent = message;
    } else {
      var div = document.createElement("div");
      div.className = "chart-empty";
      div.style.minHeight = "180px";
      div.textContent = message;
      containerEl.appendChild(div);
    }
  }

  function hideEmpty(containerEl) {
    var empty = containerEl.querySelector(".chart-empty");
    if (empty) empty.remove();
    var canvas = containerEl.querySelector("canvas");
    if (canvas) canvas.style.display = "";
  }

  /* ── Segmented control ───────────────────────────────────────── */

  function buildSegmented(options, initialKey, onChange) {
    var wrap = document.createElement("div");
    wrap.className = "segmented";
    options.forEach(function (opt) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = opt.label;
      btn.dataset.key = opt.key;
      btn.setAttribute("aria-pressed", String(opt.key === initialKey));
      btn.addEventListener("click", function () {
        wrap.querySelectorAll("button").forEach(function (b) {
          b.setAttribute("aria-pressed", String(b === btn));
        });
        onChange(opt.key);
      });
      wrap.appendChild(btn);
    });
    return wrap;
  }

  /* ── Method list ─────────────────────────────────────────────── */

  function renderMethodList(containerEl, records, getCount) {
    if (!records.length) {
      containerEl.innerHTML = '<div class="chart-empty" style="min-height:80px">No submissions yet.</div>';
      return;
    }
    containerEl.innerHTML = records.map(function (r) {
      var label = methodLabel(r);
      var meta = [r.method_type, r.date].filter(Boolean).join(" · ");
      var link = r.tool_url && /^https?:\/\//i.test(r.tool_url)
        ? '<a class="method-name" href="' + xmlText(r.tool_url) + '" target="_blank" rel="noopener noreferrer">' + xmlText(label) + " ↗</a>"
        : '<span class="method-name">' + xmlText(label) + "</span>";
      var countInfo = getCount ? getCount(r) : null;
      var countHtml = countInfo
        ? '<span class="method-count">' + xmlText(countInfo.value) + "<small>" + xmlText(countInfo.label) + "</small></span>"
        : "";
      return '<div class="method-row"><div>' + link
        + '<span class="method-meta">' + xmlText(meta || "") + "</span></div>"
        + countHtml + "</div>";
    }).join("");
  }

  /* ── Chart.js: horizontal bar ────────────────────────────────── */

  function makeBarChart(canvasEl, labels, values, opts) {
    opts = opts || {};
    destroyChart(canvasEl);

    // Compute x-axis bounds.  When a reference value is provided we must ensure
    // it falls inside the visible range; pad 15 % beyond the larger of the two.
    var finite = values.filter(Number.isFinite);
    var dataMax = finite.length ? Math.max.apply(null, finite) : 0;
    var ceiling = opts.refValue != null && Number.isFinite(opts.refValue)
      ? Math.max(dataMax, opts.refValue)
      : dataMax;
    var axisMax = ceiling > 0 ? ceiling * 1.18 : (opts.minX != null ? opts.minX + 1 : 1);

    // Build annotation only when plugin is registered and a reference is set.
    var annotationOpts;
    if (opts.refValue != null && Number.isFinite(opts.refValue)) {
      var refLabel = opts.refLabel != null ? opts.refLabel : ("ref = " + fmt(opts.refValue, opts.digits || 3));
      annotationOpts = {
        annotations: {
          refLine: {
            type: "line",
            xMin: opts.refValue,
            xMax: opts.refValue,
            borderColor: "#cb6040",
            borderWidth: 2,
            borderDash: [5, 3],
            label: {
              display: true,
              content: refLabel,
              position: "start",
              backgroundColor: "rgba(203,96,64,0.08)",
              color: "#cb6040",
              font: { size: 10, weight: "bold" },
              padding: { x: 5, y: 3 },
            },
          },
        },
      };
    }

    var unit = opts.unit || "";
    var digits = opts.digits != null ? opts.digits : 3;

    var chart = new window.Chart(canvasEl, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: "#257180",
          borderRadius: 3,
          borderSkipped: false,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 20 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return fmt(ctx.raw, digits, unit);
              },
            },
          },
          annotation: annotationOpts,
        },
        scales: {
          x: {
            min: opts.minX != null ? opts.minX : 0,
            max: axisMax,
            title: { display: !!unit, text: unit },
            grid: { color: "#dce1db" },
            ticks: { font: { size: 10 }, color: "#647170" },
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11 }, color: "#1d2929" },
          },
        },
      },
    });
    canvasEl._bpChart = chart;
    return chart;
  }

  /* ── Chart.js: boxplot ───────────────────────────────────────── */

  function makeBoxplotChart(canvasEl, labels, data, opts) {
    opts = opts || {};
    destroyChart(canvasEl);
    var unit = opts.unit || "";
    var digits = opts.digits != null ? opts.digits : 2;
    var chart = new window.Chart(canvasEl, {
      type: "boxplot",
      data: {
        labels: labels,
        datasets: [{
          label: opts.label || "",
          data: data,
          backgroundColor: "rgba(37,113,128,0.22)",
          borderColor: "#257180",
          borderWidth: 1.5,
          medianColor: "#cb6040",
          whiskerColor: "#647170",
          itemRadius: 0,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 20 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var d = ctx.raw;
                if (!d) return "—";
                return [
                  "min " + fmt(d.min, digits, unit),
                  "p25 " + fmt(d.q1, digits, unit),
                  "med " + fmt(d.median, digits, unit),
                  "p75 " + fmt(d.q3, digits, unit),
                  "max " + fmt(d.max, digits, unit),
                ].join(" · ");
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: !!unit, text: unit },
            grid: { color: "#dce1db" },
            ticks: { font: { size: 10 }, color: "#647170" },
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11 }, color: "#1d2929" },
          },
        },
      },
    });
    canvasEl._bpChart = chart;
    return chart;
  }

  /* ── Map: canvas rendering ────────────────────────────────────── */

  var lineColors = ["#cb6040", "#5b55a5", "#24734f", "#b44878", "#805b32", "#257180"];

  function lineCoords(geojson) {
    var lines = [];
    function addGeom(g) {
      if (!g) return;
      if (g.type === "LineString") lines.push(g.coordinates);
      else if (g.type === "MultiLineString") lines.push.apply(lines, g.coordinates);
      else if (g.type === "GeometryCollection") g.geometries.forEach(addGeom);
    }
    if (geojson.type === "FeatureCollection") geojson.features.forEach(function (f) { addGeom(f.geometry); });
    else if (geojson.type === "Feature") addGeom(geojson.geometry);
    else addGeom(geojson);
    return lines.map(function (l) {
      return l.filter(function (p) {
        return Array.isArray(p) && p.length >= 2 && Number.isFinite(+p[0]) && Number.isFinite(+p[1]);
      });
    }).filter(function (l) { return l.length > 1; });
  }

  function projectLines(lines, crsCode) {
    if (!crsCode || crsCode.toUpperCase() === "EPSG:4326" || typeof window.proj4 !== "function") return lines;
    return lines.map(function (line) {
      return line.map(function (pt) {
        var x = +pt[0], y = +pt[1];
        // If coords look like lon/lat, reproject to target CRS.
        if (Math.abs(x) <= 180 && Math.abs(y) <= 90) {
          return window.proj4("EPSG:4326", crsCode, [x, y]);
        }
        return [x, y];
      });
    });
  }

  function paintMap(mapWrap, mapState) {
    var stage = mapWrap.querySelector("#map-stage");
    var canvas = mapWrap.querySelector("#map-canvas");
    if (!stage || !canvas) return;
    var ctx = canvas.getContext("2d");
    var W = stage.clientWidth, H = stage.clientHeight;
    if (!W || !H) return;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!mapState.raster) return;

    var bounds = mapState.raster.bounds;  // [minX, minY, maxX, maxY]
    var bw = bounds[2] - bounds[0], bh = bounds[3] - bounds[1];
    var scale = Math.min(W / bw, H / bh);
    var dw = bw * scale, dh = bh * scale;
    var ox = (W - dw) / 2, oy = (H - dh) / 2;
    function proj(pt) {
      return [ox + (+pt[0] - bounds[0]) * scale, oy + (bounds[3] - +pt[1]) * scale];
    }
    ctx.drawImage(mapState.raster.canvas, ox, oy, dw, dh);
    mapState.layers.forEach(function (layer, i) {
      ctx.beginPath();
      layer.lines.forEach(function (line) {
        line.forEach(function (pt, j) {
          var p = proj(pt);
          j === 0 ? ctx.moveTo(p[0], p[1]) : ctx.lineTo(p[0], p[1]);
        });
      });
      ctx.strokeStyle = "#fffefa"; ctx.lineWidth = 5;
      ctx.lineJoin = ctx.lineCap = "round"; ctx.stroke();
      ctx.strokeStyle = lineColors[i % lineColors.length]; ctx.lineWidth = 3; ctx.stroke();
    });

    var ph = mapWrap.querySelector("#map-placeholder");
    if (ph) ph.hidden = true;

    var cap = mapWrap.querySelector("#map-caption");
    if (cap) {
      var lineCount = mapState.layers.reduce(function (n, l) { return n + l.lines.length; }, 0);
      cap.textContent = mapState.layers.length + " submission(s) · " + lineCount + " shoreline line(s)";
    }

    // Legend
    var legendEl = mapWrap.querySelector("#map-legend");
    if (legendEl) {
      var mp = (CFG.website || {}).map_panel || {};
      var items = [[mp.land_color || "#e8dfc7", "Land"], [mp.water_color || "#c5dfe2", "Water"]].concat(
        mapState.layers.map(function (l, i) { return [lineColors[i % lineColors.length], l.name]; })
      );
      legendEl.innerHTML = items.map(function (item, i) {
        return '<span class="map-legend-item">'
          + '<span class="map-swatch' + (i > 1 ? " line" : "") + '" style="background:' + xmlText(item[0]) + '" aria-hidden="true"></span>'
          + '<span>' + xmlText(item[1]) + "</span></span>";
      }).join("");
    }
  }

  async function loadRaster(mapWrap, mapState) {
    if (!window.GeoTIFF || typeof window.GeoTIFF.fromArrayBuffer !== "function") {
      throw new Error("GeoTIFF library did not load — check your connection and reload.");
    }
    var mp = (CFG.website || {}).map_panel || {};
    var rasterPath = mp.raster;
    if (!rasterPath) throw new Error("No raster path in benchmark config (website.map_panel.raster).");
    var resp = await fetch(rasterPath);
    if (!resp.ok) throw new Error(rasterPath + " returned HTTP " + resp.status);
    var tiff = await window.GeoTIFF.fromArrayBuffer(await resp.arrayBuffer());
    var img = await tiff.getImage();
    var vals = await img.readRasters({ interleave: true });
    var W = img.getWidth(), H = img.getHeight();
    var c = document.createElement("canvas");
    c.width = W; c.height = H;
    var cx = c.getContext("2d");
    var id = cx.createImageData(W, H);
    function hexRgb(hex) {
      var m = hex.replace("#", "").match(/.{2}/g);
      return m ? m.map(function (h) { return parseInt(h, 16); }) : [200, 200, 200];
    }
    var landRgb = hexRgb(mp.land_color || "#e8dfc7");
    var waterRgb = hexRgb(mp.water_color || "#c5dfe2");
    for (var i = 0; i < vals.length; i++) {
      var color = Number(vals[i]) === 1 ? waterRgb : landRgb;
      var p = i * 4;
      id.data[p] = color[0]; id.data[p + 1] = color[1]; id.data[p + 2] = color[2]; id.data[p + 3] = 255;
    }
    cx.putImageData(id, 0, 0);
    mapState.raster = { canvas: c, bounds: img.getBoundingBox() };
    paintMap(mapWrap, mapState);
  }

  async function loadLayers(records, mapWrap, mapState, crsCode) {
    var entries = records.flatMap(function (r) {
      var paths = Array.isArray(r.geojson_files) ? r.geojson_files : [];
      return paths.map(function (p) {
        return {
          name: paths.length > 1 ? methodLabel(r) + " · " + p.split("/").pop() : methodLabel(r),
          path: p,
        };
      });
    });
    var errors = [];
    var loaded = await Promise.all(entries.map(async function (entry) {
      try {
        var resp = await fetch(entry.path);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        var gj = await resp.json();
        return { name: entry.name, lines: projectLines(lineCoords(gj), crsCode) };
      } catch (e) {
        errors.push(entry.name + ": " + e.message);
        return null;
      }
    }));
    mapState.layers = loaded.filter(Boolean);
    paintMap(mapWrap, mapState);
    return errors;
  }

  /* ── Renderer: identification (river_dunes) ───────────────────── */

  function renderIdentification(root, cfg, records) {
    var cols = (cfg.scoring && cfg.scoring.columns) || [];
    var colOpts = cols.map(function (col) { return { key: col, label: colMeta(col).label }; });
    var activeCol = cols[0] || "height_m";

    root.innerHTML = [
      '<div class="results-layout">',
      '  <div class="panel">',
      '    <div class="panel-header" id="chart-ph">',
      '      <div>',
      '        <h3>Bedform geometry</h3>',
      '        <p class="panel-subtitle">Intercomparison · 5-number summary per method</p>',
      '      </div>',
      '    </div>',
      '    <div id="chart-container" style="position:relative">',
      '      <canvas id="main-chart"></canvas>',
      '    </div>',
      '    <div class="chart-legend" style="margin-top:10px">',
      '      <span class="legend-item"><span class="legend-range"></span>IQR (p25–p75)</span>',
      '      <span class="legend-item"><span class="legend-median"></span>Median</span>',
      '    </div>',
      '  </div>',
      '  <div class="panel">',
      '    <div class="panel-header">',
      '      <div><h3>Methods</h3>',
      '      <p class="panel-subtitle">' + xmlText(records.length) + " submission" + (records.length !== 1 ? "s" : "") + "</p></div>",
      '    </div>',
      '    <div class="method-list" id="methods-list"></div>',
      '  </div>',
      '</div>',
    ].join("\n");

    // Metric toggle — only when there are multiple columns.
    if (colOpts.length > 1) {
      var seg = buildSegmented(colOpts, activeCol, function (key) {
        activeCol = key;
        drawBoxplot();
      });
      root.querySelector("#chart-ph").appendChild(seg);
    }

    renderMethodList(root.querySelector("#methods-list"), records, function (r) {
      var n = Number(r.n_bedforms);
      return Number.isFinite(n) ? { value: n.toLocaleString(), label: "bedforms" } : null;
    });

    function drawBoxplot() {
      var container = root.querySelector("#chart-container");
      var valid = records.filter(function (r) {
        var s = r[activeCol];
        return s && s.median != null && s.p25 != null && s.p75 != null;
      });
      if (!valid.length) {
        showEmpty(container, "No data available for this metric.");
        return;
      }
      hideEmpty(container);
      container.style.height = chartH(valid.length) + "px";
      var meta = colMeta(activeCol);
      var labels = valid.map(methodLabel);
      var data = valid.map(function (r) {
        var s = r[activeCol];
        return { min: s.min, q1: s.p25, median: s.median, q3: s.p75, max: s.max };
      });
      makeBoxplotChart(root.querySelector("#main-chart"), labels, data, {
        label: meta.label,
        unit: meta.unit,
        digits: 2,
      });
    }

    drawBoxplot();
  }

  /* ── Renderer: map (shoreline) ────────────────────────────────── */

  function renderMap(root, cfg, records) {
    var mp = (cfg.website || {}).map_panel || {};
    var metrics = (cfg.scoring && cfg.scoring.metrics) || [];
    var activeMetric = metrics[0] || null;
    var crsCode = mp.crs || null;

    root.innerHTML = [
      '<div class="shoreline-grid">',
      '  <div class="panel map-panel" id="map-panel-wrap">',
      '    <div class="panel-header">',
      '      <div><h3>Map</h3>',
      '      <p class="panel-subtitle">Drag-and-drop or upload a GeoJSON to preview on the map</p></div>',
      '    </div>',
      '    <div id="map-stage" class="map-stage">',
      '      <canvas id="map-canvas"></canvas>',
      '      <div id="map-placeholder" class="map-placeholder">',
      '        <strong>Map loading…</strong>',
      '        <span>Submissions appear as coloured lines once the raster loads.</span>',
      '      </div>',
      '    </div>',
      '    <div class="map-legend" id="map-legend"></div>',
      '    <div class="map-controls">',
      '      <p class="map-caption" id="map-caption">Binary mask</p>',
      '      <label class="upload-button">Upload GeoJSON',
      '        <input type="file" id="geojson-input" accept=".geojson,.json">',
      '      </label>',
      '    </div>',
      '    <p class="map-error" id="map-error"></p>',
      '  </div>',
      '  <div class="panel" id="chart-side">',
      '    <div class="panel-header" id="chart-ph">',
      '      <div><h3>Scores</h3>',
      '      <p class="panel-subtitle">Mean across reference digitizations</p></div>',
      '    </div>',
      '    <div id="chart-container" style="position:relative">',
      '      <canvas id="main-chart"></canvas>',
      '    </div>',
      '    <div class="method-list" id="methods-list" style="margin-top:16px"></div>',
      '  </div>',
      '</div>',
    ].join("\n");

    // Metric toggle.
    if (metrics.length > 1) {
      var metricOpts = metrics.map(function (m) { return { key: m.name, label: m.label || m.name }; });
      var seg = buildSegmented(metricOpts, activeMetric.name, function (key) {
        activeMetric = metrics.find(function (m) { return m.name === key; });
        drawBar();
      });
      root.querySelector("#chart-ph").appendChild(seg);
    }

    renderMethodList(root.querySelector("#methods-list"), records, function (r) {
      var t = Number(r.runtime_seconds);
      return Number.isFinite(t) ? { value: t.toLocaleString(undefined, { maximumFractionDigits: 1 }), label: "s" } : null;
    });

    // Extract the display scalar for a map metric from a results record.
    // Uses metric.result_path (a dotted path) for nested values, so it works
    // for any benchmark that stores a metric as a nested object (e.g. pixel_f1).
    function extractVal(record, metric) {
      var summary = record.vs_references_summary || {};
      var resultPath = metric.result_path || metric.name;
      // Prefer the pre-computed mean from the summary (populated when ≥2 references exist).
      if (summary[metric.name] && Number.isFinite(+summary[metric.name].mean)) {
        return +summary[metric.name].mean;
      }
      // Fall back: average over individual references.
      var refs = Object.values(record.vs_references || {});
      var vals = refs.map(function (ref) {
        return +getPath(ref, resultPath);
      }).filter(Number.isFinite);
      return vals.length ? vals.reduce(function (a, b) { return a + b; }, 0) / vals.length : NaN;
    }

    function drawBar() {
      var container = root.querySelector("#chart-container");
      if (!activeMetric) { showEmpty(container, "No metrics configured."); return; }
      var data = records.map(function (r) {
        return { label: methodLabel(r), value: extractVal(r, activeMetric) };
      }).filter(function (d) { return Number.isFinite(d.value); });
      if (!data.length) {
        showEmpty(container, "No scored submissions yet.");
        return;
      }
      hideEmpty(container);
      if (activeMetric.direction === "lower_better") data.sort(function (a, b) { return a.value - b.value; });
      else data.sort(function (a, b) { return b.value - a.value; });
      container.style.height = chartH(data.length) + "px";
      makeBarChart(
        root.querySelector("#main-chart"),
        data.map(function (d) { return d.label; }),
        data.map(function (d) { return d.value; }),
        { unit: activeMetric.unit || "", digits: 3 }
      );
    }

    drawBar();

    // Register CRS projection if the config provides a proj4 string.
    if (crsCode && mp.crs_proj4 && window.proj4) {
      window.proj4.defs(crsCode, mp.crs_proj4);
    }

    var mapState = { raster: null, layers: [] };
    var mapWrap = root.querySelector("#map-panel-wrap");
    var errEl = root.querySelector("#map-error");

    // File-upload handler.
    root.querySelector("#geojson-input").addEventListener("change", async function (ev) {
      var file = ev.target.files && ev.target.files[0];
      if (!file) return;
      try {
        var gj = JSON.parse(await file.text());
        mapState.layers.push({ name: file.name, lines: projectLines(lineCoords(gj), crsCode) });
        paintMap(mapWrap, mapState);
        errEl.textContent = "";
      } catch (e) {
        errEl.textContent = "Could not preview GeoJSON: " + e.message;
      }
    });

    // Drag-and-drop handler.  The CSS selector `.drop-active .map-stage` expects
    // the class on a parent of the stage, so it goes on the panel wrapper.
    var stage = root.querySelector("#map-stage");
    var panelWrap = root.querySelector("#map-panel-wrap");
    stage.addEventListener("dragover", function (e) {
      e.preventDefault();
      panelWrap.classList.add("drop-active");
    });
    stage.addEventListener("dragleave", function () { panelWrap.classList.remove("drop-active"); });
    stage.addEventListener("drop", async function (e) {
      e.preventDefault();
      panelWrap.classList.remove("drop-active");
      var file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      try {
        var gj = JSON.parse(await file.text());
        mapState.layers.push({ name: file.name, lines: projectLines(lineCoords(gj), crsCode) });
        paintMap(mapWrap, mapState);
        errEl.textContent = "";
      } catch (err) {
        errEl.textContent = "Could not preview GeoJSON: " + err.message;
      }
    });

    window.addEventListener("resize", function () { paintMap(mapWrap, mapState); });

    // Load raster + existing submission layers asynchronously.
    Promise.allSettled([
      loadRaster(mapWrap, mapState),
      loadLayers(records, mapWrap, mapState, crsCode),
    ]).then(function (results) {
      var errs = [];
      if (results[0].status === "rejected") errs.push(results[0].reason.message);
      if (results[1].status === "fulfilled") errs.push.apply(errs, results[1].value);
      else errs.push(results[1].reason.message);
      errEl.textContent = errs.join(" · ");
    });
  }

  /* ── Renderer: validation × value (compensation) ─────────────── */

  function renderValidationValue(root, cfg, records) {
    var datasets = cfg.datasets || {};
    var datasetKeys = Object.keys(datasets);
    var metrics = (cfg.scoring && cfg.scoring.metrics) || [];
    var activeDataset = datasetKeys[0] || null;

    // Build the full set of toggle options for a given dataset:
    //   · one option per scored_field  (shows submitted value + reference line)
    //   · one option per scoring metric (shows computed error value, no reference line)
    function metricOptions(dsKey) {
      var dsCfg = datasets[dsKey] || {};
      var opts = [];
      (dsCfg.scored_fields || []).forEach(function (f) {
        var refVal = (dsCfg.reference_values || {})[f];
        opts.push({
          key: "__field__" + f,
          label: fieldLabel(f),
          isField: true,
          field: f,
          refValue: refVal,
        });
      });
      metrics.forEach(function (m) {
        opts.push({ key: m.name, label: m.label || m.name, isField: false, metric: m });
      });
      return opts;
    }

    var metricOpts = metricOptions(activeDataset);
    var activeMetricKey = metricOpts.length ? metricOpts[0].key : null;
    var dsOpts = datasetKeys.map(function (k) {
      return { key: k, label: (datasets[k].label || k) };
    });

    root.innerHTML = [
      '<div class="results-layout">',
      '  <div class="panel">',
      '    <div class="panel-header">',
      '      <div>',
      '        <h3>' + xmlText(cfg.name) + "</h3>",
      '        <p class="panel-subtitle">Validation · compare submitted values to theoretical reference</p>',
      '      </div>',
      '      <div id="toggles" style="display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start"></div>',
      '    </div>',
      '    <div id="chart-container" style="position:relative">',
      '      <canvas id="main-chart"></canvas>',
      '    </div>',
      '    <p class="chart-footnote" id="chart-footnote"></p>',
      '  </div>',
      '  <div class="panel">',
      '    <div class="panel-header">',
      '      <div><h3>Methods</h3>',
      '      <p class="panel-subtitle">' + xmlText(records.length) + " submission" + (records.length !== 1 ? "s" : "") + "</p></div>",
      '    </div>',
      '    <div class="method-list" id="methods-list"></div>',
      '  </div>',
      '</div>',
    ].join("\n");

    renderMethodList(root.querySelector("#methods-list"), records);

    var togglesEl = root.querySelector("#toggles");

    // Dataset segmented control — only shown when more than one dataset exists.
    var metricSegWrap = document.createElement("div");
    togglesEl.appendChild(metricSegWrap);
    if (datasetKeys.length > 1) {
      var dsSegWrap = document.createElement("div");
      togglesEl.insertBefore(dsSegWrap, metricSegWrap);
      dsSegWrap.appendChild(buildSegmented(dsOpts, activeDataset, function (key) {
        activeDataset = key;
        metricOpts = metricOptions(activeDataset);
        activeMetricKey = metricOpts.length ? metricOpts[0].key : null;
        rebuildMetricSeg();
        drawBar();
      }));
    }

    function rebuildMetricSeg() {
      metricSegWrap.innerHTML = "";
      if (metricOpts.length > 1) {
        metricSegWrap.appendChild(buildSegmented(metricOpts, activeMetricKey, function (key) {
          activeMetricKey = key;
          drawBar();
        }));
      }
    }
    rebuildMetricSeg();

    function drawBar() {
      var container = root.querySelector("#chart-container");
      var opt = metricOpts.find(function (o) { return o.key === activeMetricKey; });
      if (!opt) { showEmpty(container, "No metrics configured."); return; }

      var data, refValue, unit, digits, footnote;

      if (opt.isField) {
        // Submitted field value view — bars show the raw submitted value,
        // annotation marks the reference.
        data = records.map(function (r) {
          var ds = r[activeDataset] || {};
          return { label: methodLabel(r), value: +ds[opt.field + "_submitted"] };
        }).filter(function (d) { return Number.isFinite(d.value); });
        refValue = Number.isFinite(opt.refValue) ? opt.refValue : null;
        unit = ""; digits = 4;
        footnote = refValue != null
          ? "Reference: " + fieldLabel(opt.field) + " = " + fmt(refValue, 4) + " (from benchmark definition)"
          : "";
      } else {
        // Error metric view — no reference line.
        data = records.map(function (r) {
          var ds = r[activeDataset] || {};
          return { label: methodLabel(r), value: +ds[opt.metric.name] };
        }).filter(function (d) { return Number.isFinite(d.value); });
        refValue = null;
        unit = opt.metric.unit || ""; digits = 3;
        footnote = "";
        if (opt.metric.direction === "lower_better") data.sort(function (a, b) { return a.value - b.value; });
        else if (opt.metric.direction === "higher_better") data.sort(function (a, b) { return b.value - a.value; });
      }

      if (!data.length) {
        showEmpty(container, "No scored submissions yet.");
        root.querySelector("#chart-footnote").textContent = "";
        return;
      }
      hideEmpty(container);
      // For field views: sort ascending (closest to reference last makes bar easier to read).
      if (opt.isField) data.sort(function (a, b) { return a.value - b.value; });

      container.style.height = chartH(data.length) + "px";
      makeBarChart(
        root.querySelector("#main-chart"),
        data.map(function (d) { return d.label; }),
        data.map(function (d) { return d.value; }),
        { unit: unit, digits: digits, refValue: refValue }
      );
      root.querySelector("#chart-footnote").textContent = footnote;
    }

    drawBar();
  }

  /* ── Renderer: intercomparison × value (compensation_sensitivity) */

  function renderIntercomparisonValue(root, cfg, records) {
    var datasets = cfg.datasets || {};
    var datasetKeys = Object.keys(datasets);
    var activeDataset = datasetKeys[0] || null;

    function fieldOpts(dsKey) {
      var dsCfg = datasets[dsKey] || {};
      var fields = dsCfg.reported_fields
        || (cfg.scoring && cfg.scoring.reported_fields)
        || [];
      return fields.map(function (f) { return { key: f, label: fieldLabel(f) }; });
    }

    var fOpts = fieldOpts(activeDataset);
    var activeField = fOpts.length ? fOpts[0].key : null;
    var dsOpts = datasetKeys.map(function (k) {
      return { key: k, label: datasets[k].label || k };
    });

    root.innerHTML = [
      '<div class="results-layout">',
      '  <div class="panel">',
      '    <div class="panel-header">',
      '      <div>',
      '        <h3>' + xmlText(cfg.name) + "</h3>",
      '        <p class="panel-subtitle">Intercomparison · no theoretical reference</p>',
      '      </div>',
      '      <div id="toggles" style="display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start"></div>',
      '    </div>',
      '    <div id="chart-container" style="position:relative">',
      '      <canvas id="main-chart"></canvas>',
      '    </div>',
      '  </div>',
      '  <div class="panel">',
      '    <div class="panel-header">',
      '      <div><h3>Methods</h3>',
      '      <p class="panel-subtitle">' + xmlText(records.length) + " submission" + (records.length !== 1 ? "s" : "") + "</p></div>",
      '    </div>',
      '    <div class="method-list" id="methods-list"></div>',
      '  </div>',
      '</div>',
    ].join("\n");

    renderMethodList(root.querySelector("#methods-list"), records);

    var togglesEl = root.querySelector("#toggles");
    var fieldSegWrap = document.createElement("div");

    if (datasetKeys.length > 1) {
      var dsSegWrap = document.createElement("div");
      togglesEl.appendChild(dsSegWrap);
      dsSegWrap.appendChild(buildSegmented(dsOpts, activeDataset, function (key) {
        activeDataset = key;
        fOpts = fieldOpts(activeDataset);
        activeField = fOpts.length ? fOpts[0].key : null;
        rebuildFieldSeg();
        drawBar();
      }));
    }
    togglesEl.appendChild(fieldSegWrap);

    function rebuildFieldSeg() {
      fieldSegWrap.innerHTML = "";
      if (fOpts.length > 1) {
        fieldSegWrap.appendChild(buildSegmented(fOpts, activeField, function (key) {
          activeField = key;
          drawBar();
        }));
      }
    }
    rebuildFieldSeg();

    function drawBar() {
      var container = root.querySelector("#chart-container");
      var data = records.map(function (r) {
        var ds = r[activeDataset] || {};
        return { label: methodLabel(r), value: +ds[activeField + "_submitted"] };
      }).filter(function (d) { return Number.isFinite(d.value); });

      if (!data.length) {
        showEmpty(container, "No submissions yet.");
        return;
      }
      hideEmpty(container);
      container.style.height = chartH(data.length) + "px";
      var meta = colMeta(activeField);
      makeBarChart(
        root.querySelector("#main-chart"),
        data.map(function (d) { return d.label; }),
        data.map(function (d) { return d.value; }),
        { unit: meta.unit, digits: 4, minX: 0 }
      );
    }

    drawBar();
  }

  /* ── Entry point ─────────────────────────────────────────────── */

  async function main() {
    if (!CFG) return;
    var root = document.getElementById("benchmark-root");
    if (!root) return;

    if (typeof window.Chart === "undefined") {
      root.innerHTML = '<div class="chart-empty">Chart.js did not load — check your internet connection and reload.</div>';
      return;
    }

    // Register chartjs-plugin-annotation when present (validation benchmarks).
    if (window.ChartAnnotation) {
      window.Chart.register(window.ChartAnnotation);
    }

    var records;
    try {
      var resp = await fetch("results_table.json");
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      records = await resp.json();
      if (!Array.isArray(records)) throw new Error("results_table.json must be a JSON array");
    } catch (err) {
      root.innerHTML = '<div class="chart-empty">'
        + "Could not load results: " + xmlText(err.message) + "<br>"
        + "<small>During local development, serve from the repository root so relative paths resolve correctly.</small>"
        + "</div>";
      return;
    }

    var rt = CFG.reference_type;
    var dt = CFG.data_type;

    if (dt === "identification") {
      renderIdentification(root, CFG, records);
    } else if (dt === "map") {
      renderMap(root, CFG, records);
    } else if (rt === "validation" && dt === "value") {
      renderValidationValue(root, CFG, records);
    } else if (rt === "intercomparison" && dt === "value") {
      renderIntercomparisonValue(root, CFG, records);
    } else {
      root.innerHTML = '<div class="chart-empty">No chart renderer for taxonomy: '
        + xmlText(rt) + " × " + xmlText(dt) + "</div>";
    }
  }

  main().catch(function (err) {
    console.error("benchmark-page.js:", err);
    var root = document.getElementById("benchmark-root");
    if (root) root.innerHTML = '<div class="chart-empty">An error occurred rendering this page: ' + xmlText(err.message) + "</div>";
  });

})();
