"use strict";

const state = {
  river: [],
  shoreline: [],
  riverMetric: "height_m",
  shorelineMetric: "mean_distance_error_m",
  raster: null,
  shorelineLayers: []
};

const riverMetrics = {
  height_m: { label: "Height", unit: "m", digits: 2 },
  length_m: { label: "Length", unit: "m", digits: 1 },
  depth_m: { label: "Depth", unit: "m", digits: 2 }
};

const shorelineMetrics = {
  mean_distance_error_m: {
    label: "Mean distance error",
    unit: "m",
    digits: 2,
    direction: "lower"
  },
  pixel_f1_f1: {
    label: "Pixel F1",
    unit: "",
    digits: 3,
    direction: "higher"
  },
  roughness_relative_difference_pct: {
    label: "Roughness difference",
    unit: "%",
    digits: 1,
    direction: "lower"
  },
  runtime_seconds: {
    label: "Compute time",
    unit: "s",
    digits: 2,
    direction: "lower"
  }
};

const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const preciseFormat = (value, digits) => Number(value).toLocaleString(undefined, {
  minimumFractionDigits: 0,
  maximumFractionDigits: digits
});

function safeText(value, fallback = "Unspecified method") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function xmlText(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;"
  })[character]);
}

function methodLabel(record) {
  return safeText(record.method_name || record.author_name || record.tool_name);
}

function renderRiverChart() {
  const target = document.getElementById("river-chart");
  const metric = riverMetrics[state.riverMetric];
  const records = state.river.filter(record => {
    const stats = record[state.riverMetric];
    return stats && [stats.p25, stats.p75, stats.median].every(value => Number.isFinite(Number(value)));
  });

  if (!records.length) {
    target.innerHTML = '<div class="chart-empty">No distribution data is available for this measurement yet.</div>';
    return;
  }

  const width = 780;
  const rowHeight = 58;
  const top = 14;
  const left = 185;
  const right = 28;
  const bottom = 38;
  const height = top + records.length * rowHeight + bottom;
  const plotWidth = width - left - right;
  const values = records.flatMap(record => [
    Number(record[state.riverMetric].p25),
    Number(record[state.riverMetric].p75)
  ]);
  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  if (minimum === maximum) maximum = minimum + 1;
  const padding = (maximum - minimum) * .08;
  minimum = minimum >= 0 ? 0 : minimum - padding;
  maximum += padding;
  const x = value => left + ((value - minimum) / (maximum - minimum)) * plotWidth;
  const tickStep = (maximum - minimum) / 4;
  const ticks = Array.from({ length: 5 }, (_, index) => minimum + tickStep * index);
  const rows = records.map((record, index) => {
    const stats = record[state.riverMetric];
    const y = top + index * rowHeight + rowHeight / 2;
    const p25 = Number(stats.p25);
    const p75 = Number(stats.p75);
    const median = Number(stats.median);
    return `
      <g class="chart-row">
        <text x="${left - 12}" y="${y + 4}" text-anchor="end" class="svg-label">${xmlText(methodLabel(record))}</text>
        <line x1="${x(p25)}" y1="${y}" x2="${x(p75)}" y2="${y}" class="range-line"/>
        <line x1="${x(p25)}" y1="${y - 6}" x2="${x(p25)}" y2="${y + 6}" class="range-cap"/>
        <line x1="${x(p75)}" y1="${y - 6}" x2="${x(p75)}" y2="${y + 6}" class="range-cap"/>
        <circle cx="${x(median)}" cy="${y}" r="5.5" class="median-dot"><title>${xmlText(methodLabel(record))}: median ${preciseFormat(median, metric.digits)} ${metric.unit}</title></circle>
        <text x="${left}" y="${y + 20}" class="svg-value">${preciseFormat(p25, metric.digits)}–${preciseFormat(p75, metric.digits)} ${metric.unit}</text>
      </g>`;
  }).join("");
  const grid = ticks.map(value => `
    <g>
      <line x1="${x(value)}" y1="${top - 4}" x2="${x(value)}" y2="${height - bottom + 2}" class="grid-line"/>
      <text x="${x(value)}" y="${height - 12}" text-anchor="middle" class="svg-tick">${preciseFormat(value, metric.digits)}</text>
    </g>`).join("");

  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${metric.label} distribution ranges by method, in ${metric.unit}">
      <style>
        .grid-line{stroke:#dce1db;stroke-width:1;stroke-dasharray:3 4}
        .range-line{stroke:#cb6040;stroke-width:6;stroke-linecap:round}
        .range-cap{stroke:#cb6040;stroke-width:2}
        .median-dot{fill:#257180;stroke:#fffefa;stroke-width:2}
        .svg-label{fill:#1d2929;font:600 12px 'Segoe UI',Arial,sans-serif}
        .svg-value{fill:#647170;font:11px 'Segoe UI',Arial,sans-serif}
        .svg-tick{fill:#647170;font:11px 'Segoe UI',Arial,sans-serif}
      </style>
      ${grid}${rows}
    </svg>`;
}

function renderRiverMethods() {
  const target = document.getElementById("river-methods");
  if (!state.river.length) {
    target.innerHTML = '<div class="chart-empty">No compiled bedform results are available yet.</div>';
    return;
  }
  target.innerHTML = state.river.map(record => {
    const label = methodLabel(record);
    const metadata = [record.method_type, record.date].filter(Boolean).join(" · ") || safeText(record.tool_name, "");
    const count = Number(record.n_bedforms);
    const link = typeof record.tool_url === "string" && /^https?:\/\//i.test(record.tool_url)
      ? `<a class="method-name" href="${xmlText(record.tool_url)}" target="_blank" rel="noopener noreferrer">${xmlText(label)} ↗</a>`
      : `<span class="method-name">${xmlText(label)}</span>`;
    return `<div class="method-row">
      <div>${link}<span class="method-meta">${xmlText(metadata || "Bedform detection method")}</span></div>
      <span class="method-count">${Number.isFinite(count) ? numberFormat.format(count) : "—"}<small>bedforms</small></span>
    </div>`;
  }).join("");
}

function getShoreValue(record, metricKey) {
  if (metricKey === "runtime_seconds") {
    if (record.runtime_seconds === null || record.runtime_seconds === undefined || record.runtime_seconds === "") {
      return NaN;
    }
    return Number(record.runtime_seconds);
  }

  const summary = record.vs_references_summary || {};
  if (summary[metricKey] && Number.isFinite(Number(summary[metricKey].mean))) {
    return Number(summary[metricKey].mean);
  }

  const values = Object.values(record.vs_references || {}).map(reference => {
    if (metricKey === "mean_distance_error_m") return Number(reference.mean_distance_error_m);
    if (metricKey === "pixel_f1_f1") return Number(reference.pixel_f1 && reference.pixel_f1.f1);
    if (metricKey === "roughness_relative_difference_pct") {
      return Number(reference.roughness_agreement && reference.roughness_agreement.relative_difference_pct);
    }
    return NaN;
  }).filter(Number.isFinite);
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : NaN;
}

function renderShorelineChart() {
  const target = document.getElementById("shoreline-chart");
  const metric = shorelineMetrics[state.shorelineMetric];
  const records = state.shoreline.map(record => ({
    label: methodLabel(record),
    value: getShoreValue(record, state.shorelineMetric)
  })).filter(record => Number.isFinite(record.value));

  if (!records.length) {
    target.innerHTML = '<div class="chart-empty">Waiting for scored shoreline submissions. Results will appear here when available.</div>';
    return;
  }

  const width = 540;
  const rowHeight = 57;
  const top = 12;
  const left = 166;
  const right = 60;
  const bottom = 35;
  const height = top + records.length * rowHeight + bottom;
  const plotWidth = width - left - right;
  const maximum = Math.max(...records.map(record => record.value), .00001);
  const axisMax = maximum * 1.12;
  const x = value => left + (value / axisMax) * plotWidth;
  const rows = records.map((record, index) => {
    const y = top + index * rowHeight + 10;
    const barWidth = Math.max(record.value > 0 ? 2 : 0, x(record.value) - left);
    return `<g>
      <text x="${left - 10}" y="${y + 15}" text-anchor="end" class="svg-label">${xmlText(record.label)}</text>
      <rect x="${left}" y="${y}" width="${barWidth}" height="22" rx="3" class="score-bar"><title>${xmlText(record.label)}: ${preciseFormat(record.value, metric.digits)} ${metric.unit}</title></rect>
      <text x="${Math.min(x(record.value) + 8, width - right + 3)}" y="${y + 15}" class="svg-value">${preciseFormat(record.value, metric.digits)}${metric.unit ? ` ${metric.unit}` : ""}</text>
    </g>`;
  }).join("");
  const ticks = Array.from({ length: 5 }, (_, index) => axisMax * index / 4).map(value => `
    <g>
      <line x1="${x(value)}" y1="${top}" x2="${x(value)}" y2="${height - bottom + 1}" class="grid-line"/>
      <text x="${x(value)}" y="${height - 10}" text-anchor="middle" class="svg-tick">${preciseFormat(value, metric.digits)}</text>
    </g>`).join("");

  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${metric.label} by shoreline method">
    <style>
      .grid-line{stroke:#dce1db;stroke-width:1;stroke-dasharray:3 4}
      .score-bar{fill:#257180}
      .svg-label{fill:#1d2929;font:600 11px 'Segoe UI',Arial,sans-serif}
      .svg-value{fill:#647170;font:11px 'Segoe UI',Arial,sans-serif}
      .svg-tick{fill:#647170;font:10px 'Segoe UI',Arial,sans-serif}
    </style>
    ${ticks}${rows}
  </svg>`;
}

function lineCoordinates(geojson) {
  const lines = [];
  function addGeometry(geometry) {
    if (!geometry) return;
    if (geometry.type === "LineString") lines.push(geometry.coordinates);
    else if (geometry.type === "MultiLineString") lines.push(...geometry.coordinates);
    else if (geometry.type === "GeometryCollection") geometry.geometries.forEach(addGeometry);
    else if (geometry.type !== "Point" && geometry.type !== "MultiPoint") {
      throw new Error("The GeoJSON must contain line geometry (LineString or MultiLineString).");
    }
  }
  if (geojson.type === "FeatureCollection" && Array.isArray(geojson.features)) {
    geojson.features.forEach(feature => addGeometry(feature.geometry));
  } else if (geojson.type === "Feature") {
    addGeometry(geojson.geometry);
  } else {
    addGeometry(geojson);
  }
  const validLines = lines.map(line => line.filter(point =>
    Array.isArray(point) && Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1]))
  )).filter(line => line.length > 1);
  if (!validLines.length) throw new Error("No usable shoreline lines were found in this GeoJSON.");
  return validLines;
}

const shorelineColors = ["#cb6040", "#5b55a5", "#24734f", "#b44878", "#805b32", "#257180"];

if (typeof window.proj4 === "function") {
  window.proj4.defs("EPSG:32648", "+proj=utm +zone=48 +datum=WGS84 +units=m +no_defs");
}

function mapLineCoordinates(lines) {
  return lines.map(line => line.map(point => {
    const [x, y] = point.map(Number);
    if (Math.abs(x) <= 180 && Math.abs(y) <= 90) {
      if (typeof window.proj4 !== "function") {
        throw new Error("The projection library did not load, so longitude/latitude shorelines cannot be aligned with the map.");
      }
      return window.proj4("EPSG:4326", "EPSG:32648", [x, y]);
    }
    return [x, y];
  }));
}

function renderMap() {
  const stage = document.getElementById("map-stage");
  const canvas = document.getElementById("map-canvas");
  const context = canvas.getContext("2d");
  const width = stage.clientWidth;
  const height = stage.clientHeight;
  if (!width || !height) return;

  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, width, height);

  if (!state.raster) return;

  const [minX, minY, maxX, maxY] = state.raster.bounds;
  const scale = Math.min(width / (maxX - minX), height / (maxY - minY));
  const drawWidth = (maxX - minX) * scale;
  const drawHeight = (maxY - minY) * scale;
  const offsetX = (width - drawWidth) / 2;
  const offsetY = (height - drawHeight) / 2;
  const project = point => [
    offsetX + (Number(point[0]) - minX) * scale,
    offsetY + (maxY - Number(point[1])) * scale
  ];

  context.drawImage(state.raster.canvas, offsetX, offsetY, drawWidth, drawHeight);
  state.shorelineLayers.forEach((layer, index) => {
    context.beginPath();
    layer.lines.forEach(line => {
      line.forEach((point, pointIndex) => {
        const [x, y] = project(point);
        if (pointIndex === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
    });
    context.strokeStyle = "#fffefa";
    context.lineWidth = 5;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.stroke();
    context.strokeStyle = shorelineColors[index % shorelineColors.length];
    context.lineWidth = 3;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.stroke();
  });

  document.getElementById("map-placeholder").hidden = true;
  const lineCount = state.shorelineLayers.reduce((count, layer) => count + layer.lines.length, 0);
  document.getElementById("map-caption").textContent =
    `Binary mask · ${numberFormat.format(state.shorelineLayers.length)} submission(s) · ${numberFormat.format(lineCount)} shoreline ${lineCount === 1 ? "line" : "lines"}`;
  renderMapLegend();
}

function renderMapLegend() {
  const items = [
    ["#e8dfc7", "Land"],
    ["#c5dfe2", "Water"],
    ...state.shorelineLayers.map((layer, index) => [
      shorelineColors[index % shorelineColors.length],
      layer.name
    ])
  ];
  document.getElementById("map-legend").innerHTML = items.map(([color, label], index) =>
    `<span class="map-legend-item"><span class="map-swatch${index > 1 ? " line" : ""}" style="background:${color}" aria-hidden="true"></span><span>${xmlText(label)}</span></span>`
  ).join("");
}

async function loadRaster() {
  if (!window.GeoTIFF || typeof window.GeoTIFF.fromArrayBuffer !== "function") {
    throw new Error("The GeoTIFF reader did not load. Check your internet connection and reload the page.");
  }
  const path = "benchmarks/shoreline/data/selenga_clipped.tif";
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  const tiff = await window.GeoTIFF.fromArrayBuffer(await response.arrayBuffer());
  const image = await tiff.getImage();
  const values = await image.readRasters({ interleave: true });
  const width = image.getWidth();
  const height = image.getHeight();
  const rasterCanvas = document.createElement("canvas");
  rasterCanvas.width = width;
  rasterCanvas.height = height;
  const rasterContext = rasterCanvas.getContext("2d");
  const imageData = rasterContext.createImageData(width, height);
  const colors = [[232, 223, 199], [197, 223, 226]];
  for (let index = 0; index < values.length; index += 1) {
    const color = colors[Number(values[index]) === 1 ? 1 : 0];
    const pixel = index * 4;
    imageData.data[pixel] = color[0];
    imageData.data[pixel + 1] = color[1];
    imageData.data[pixel + 2] = color[2];
    imageData.data[pixel + 3] = 255;
  }
  rasterContext.putImageData(imageData, 0, 0);
  state.raster = { canvas: rasterCanvas, bounds: image.getBoundingBox() };
  renderMap();
}

async function loadSubmissionLayers(records) {
  const entries = records.flatMap(record => {
    const paths = Array.isArray(record.geojson_files) ? record.geojson_files : [];
    return paths.map(path => ({
      name: paths.length > 1 ? `${methodLabel(record)} · ${path.split("/").pop()}` : methodLabel(record),
      path
    }));
  });
  const failures = [];
  const loaded = await Promise.all(entries.map(async entry => {
    try {
      const path = `benchmarks/shoreline/${entry.path}`;
      const response = await fetch(path);
      if (!response.ok) throw new Error(`${path} returned ${response.status}`);
      const geojson = await response.json();
      return { name: entry.name, lines: mapLineCoordinates(lineCoordinates(geojson)) };
    } catch (error) {
      failures.push(`${entry.name}: ${error.message}`);
      return null;
    }
  }));
  state.shorelineLayers = loaded.filter(Boolean);
  renderMap();
  return failures;
}

async function addUploadedGeoJSON(file) {
  const geojson = JSON.parse(await file.text());
  state.shorelineLayers.push({ name: file.name, lines: mapLineCoordinates(lineCoordinates(geojson)) });
  renderMap();
  document.getElementById("map-error").textContent = "";
}

async function loadResults(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error(`${path} must contain a JSON array`);
  return data;
}

async function initialize() {
  const [riverResult, shorelineResult] = await Promise.allSettled([
    loadResults("benchmarks/river_dunes/results_table.json"),
    loadResults("benchmarks/shoreline/results_table.json")
  ]);

  if (riverResult.status === "fulfilled") state.river = riverResult.value;
  else console.warn("Could not load benchmarks/river_dunes/results_table.json:", riverResult.reason);

  if (shorelineResult.status === "fulfilled") state.shoreline = shorelineResult.value;
  else console.info("No compiled shoreline results are available yet:", shorelineResult.reason);

  renderRiverChart();
  renderRiverMethods();
  renderShorelineChart();
  document.getElementById("method-count").textContent = numberFormat.format(state.river.length + state.shoreline.length);

  const mapResults = await Promise.allSettled([
    loadRaster(),
    loadSubmissionLayers(state.shoreline)
  ]);
  const mapErrors = [];
  if (mapResults[0].status === "rejected") mapErrors.push(mapResults[0].reason.message);
  if (mapResults[1].status === "fulfilled") mapErrors.push(...mapResults[1].value);
  else mapErrors.push(mapResults[1].reason.message);
  document.getElementById("map-error").textContent = mapErrors.join(" ");

  const anyLoaded = riverResult.status === "fulfilled" || shorelineResult.status === "fulfilled";
  document.getElementById("data-status").textContent = anyLoaded
    ? `Results loaded · ${state.river.length + state.shoreline.length} methods`
    : "Results unavailable · serve this page from the repository root";
  if (anyLoaded) document.getElementById("data-status-dot").classList.add("loaded");
}

document.querySelectorAll("[data-river-metric]").forEach(button => {
  button.addEventListener("click", () => {
    state.riverMetric = button.dataset.riverMetric;
    document.querySelectorAll("[data-river-metric]").forEach(item =>
      item.setAttribute("aria-pressed", String(item === button))
    );
    renderRiverChart();
  });
});

document.querySelectorAll("[data-shore-metric]").forEach(button => {
  button.addEventListener("click", () => {
    state.shorelineMetric = button.dataset.shoreMetric;
    document.querySelectorAll("[data-shore-metric]").forEach(item =>
      item.setAttribute("aria-pressed", String(item === button))
    );
    renderShorelineChart();
  });
});

document.getElementById("geojson-input").addEventListener("change", async event => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    await addUploadedGeoJSON(file);
  } catch (error) {
    document.getElementById("map-error").textContent = `Could not preview GeoJSON: ${error.message}`;
  }
});

const mapStage = document.getElementById("map-stage");
mapStage.addEventListener("dragover", event => {
  event.preventDefault();
  mapStage.classList.add("drop-active");
});
mapStage.addEventListener("dragleave", () => mapStage.classList.remove("drop-active"));
mapStage.addEventListener("drop", async event => {
  event.preventDefault();
  mapStage.classList.remove("drop-active");
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (!file) return;
  try {
    await addUploadedGeoJSON(file);
  } catch (error) {
    document.getElementById("map-error").textContent = `Could not preview GeoJSON: ${error.message}`;
  }
});

window.addEventListener("resize", renderMap);
initialize();
