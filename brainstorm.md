# Benchmark brainstorm

Ideas for future benchmarks, organized by domain.
Each entry lists the task, input data, expected output format, and candidate scoring approach.
This is a living document — open an issue to discuss any of these.

---

## Shared scoring infrastructure

Many benchmarks reduce to one of a small number of output types.
The scoring modules in `shoreline/scoring/` already cover polylines.
A shared library at the repo root could eventually serve all benchmarks:

| Output type | Scoring approach | Status |
|---|---|---|
| Polyline GeoJSON | Mean distance error, pixel F1, roughness agreement | ✅ built (`shoreline/`) |
| Polygon GeoJSON | IoU, area error, shape metrics | planned |
| Point GeoJSON | Mean distance error, detection F1 | planned |
| CSV of measurements | MAE / RMSE per column | planned |
| Binary raster mask | Pixel F1, IoU | planned |

---

## Deltas

| Benchmark | Task | Input | Output | Scoring | Notes / Inspiration |
|---|---|---|---|---|---|
| **Shoreline mapping** *(done)* | Extract ocean/delta boundary from a binary mask | Binary land/water GeoTIFF | Polyline GeoJSON | Mean distance error, pixel F1, roughness agreement | Selenga River Delta; sandplover |
| **Delta channel network extraction** | Extract the full distributary network as a graph | Binary land/water GeoTIFF | GeoJSON `MultiLineString` + node/edge CSV | Pixel F1 on rasterized network, graph edit distance | RivGraph; Colville River Delta (well-documented, complex bifurcations, published reference) |
| **Distributary inlet width** | Measure width of each distributary mouth at the shoreline | Binary mask + reference shoreline | CSV of per-inlet widths (m) | MAE vs. hand-measured widths | RivGraph, sandplover |
| **Delta lobe classification** | Identify active vs. abandoned lobes | Multi-temporal binary masks | Polygon GeoJSON with lobe class attribute | Per-class IoU | Literature (e.g. Bhattacharya & Giosan) |

---

## Barrier islands and coasts

| Benchmark | Task | Input | Output | Scoring | Notes |
|---|---|---|---|---|---|
| **Shoreline change rate** | Compute cross-shore change rate along transects (DSAS-style) | Two epoch shoreline GeoJSONs + baseline polyline | CSV of transect rates (m/yr) | MAE vs. DSAS reference output | Could use USGS barrier island lidar time series |
| **Barrier island centerline** | Medial axis / spine of island body | Binary land mask | Polyline GeoJSON | Distance error vs. hand-digitized spine | — |
| **Foredune crest and toe extraction** | Locate foredune crest and toe in cross-shore profile | 1 m lidar DEM | Two polyline GeoJSONs (crest, toe) | Cross-shore position error, vertical RMSE | USGS CoNED or similar open lidar |

---

## Aeolian dunes

| Benchmark | Task | Input | Output | Scoring | Notes / Inspiration |
|---|---|---|---|---|---|
| **Dune crestline extraction** | Trace dune crestlines from a DEM | Lidar or TanDEM-X DEM GeoTIFF | `MultiLineString` GeoJSON | Mean distance error, crestline density ratio | PyDune; Mayer et al. Dune Crest Finder; White Sands / Namib / Bodélé open DEMs |
| **Dune body segmentation** | Delineate individual dune polygons | DEM or optical image | Polygon GeoJSON (one feature per dune) | IoU, mean area error | — |
| **Dune migration rate** | Match crests between two epochs, measure displacement | Two crestline GeoJSONs (t1, t2) | CSV of matched-crest displacements (m) | MAE vs. manual tracking reference | — |
| **Slip-face orientation** | Classify lee vs. stoss side of each crestline segment | DEM + crestline GeoJSON | Per-feature bearing attribute on input GeoJSON | Mean angular error | — |

---

## Alluvial fans

| Benchmark | Task | Input | Output | Scoring | Notes |
|---|---|---|---|---|---|
| **Fan boundary delineation** | Outline the fan footprint | DEM + hillshade GeoTIFF | Polygon GeoJSON | IoU vs. hand-mapped reference | Many published fan inventories available |
| **Fan apex detection** | Locate the apex point | DEM | Point GeoJSON | Distance error (m) | — |
| **Active lobe vs. relict surface** | Classify surface zones by relative age | Multi-band optical or DEM | Polygon GeoJSON with age-class attribute | Per-class IoU | — |

---

## Rivers and fluvial geomorphology

| Benchmark | Task | Input | Output | Scoring | Notes / Inspiration |
|---|---|---|---|---|---|
| **Single-thread channel centerline** | Extract centerline of a single-thread river | Binary channel mask GeoTIFF | Polyline GeoJSON | Mean distance error, sinuosity agreement | RivGraph, pyGeoNet |
| **Braided river network graph** | Extract full braid-plain network as a graph | Binary channel mask GeoTIFF | GeoJSON network (nodes + edges) | Graph edit distance, link-level F1 | RivGraph; Brahmaputra or Wax Lake Outlet |
| **Channel width transects** | Measure bankfull width at regular intervals | Binary mask + centerline GeoJSON | CSV of along-stream widths (m) | MAE vs. reference transects | RivGraph, Hand et al. |
| **Meander geometry statistics** | Wavelength, amplitude, and radius of curvature per bend | Centerline GeoJSON | CSV of per-bend statistics | MAE per statistic | — |
| **Avulsion detection** | Detect whether a channel avulsion occurred between two epochs | Two binary mask GeoTIFFs (t1, t2) | Boolean flag + optional avulsion-zone polygon | Precision/recall on labelled avulsion events | — |

---

## Riverbed dunes (subaqueous bedforms)

| Benchmark | Task | Input | Output | Scoring | Notes |
|---|---|---|---|---|---|
| **Bedform crestline extraction** | Trace dune crestlines from multibeam bathymetry | Bathymetry GeoTIFF (gridded) | `MultiLineString` GeoJSON | Mean distance error, crest density ratio | Scoring code nearly identical to aeolian crestline; USGS Mississippi or Rhine open datasets |
| **Bedform geometry statistics** | Height, wavelength, and asymmetry per bedform | Bathymetry cross-section CSV or grid | CSV of per-bedform statistics | MAE per statistic vs. manual picks | — |
| **Bedform migration** | Measure dune displacement between repeat surveys (bedload proxy) | Two bathymetry GeoTIFFs (t1, t2) | CSV of matched-dune displacements (m) | MAE vs. reference tracking | — |

---

## Stratigraphy

### Compensation statistic

The compensation index (κ) quantifies how well a sedimentary system fills topographic lows before building upward — a key diagnostic for avulsion style and stratigraphic architecture.
The standard formulation uses a stratigraphic cross-section (or vertical-profile stack) to measure how successive layers compensate earlier relief.

| Benchmark | Task | Input | Output | Scoring | Notes / Inspiration |
|---|---|---|---|---|---|
| **Compensation statistic (κ)** | Compute κ from a stratigraphic cross section | Stratigraphic surfaces as a set of georeferenced horizon GeoTIFFs or a multi-layer NetCDF/CSV grid | Scalar κ value (and optionally the compensation curve — κ vs. window thickness) | MAE vs. reference κ computed from published algorithm; curve RMSE | Wang et al. (2011) original definition; sandplover `comp_stack` implementation is a natural reference |
| **Compensation curve** | Full κ(Δh) curve across a range of stratigraphic window thicknesses | Same as above | CSV of (window_thickness_m, kappa) pairs | Curve RMSE vs. reference; correct asymptotic behaviour check | Stratigraphic windows should span sub-layer to full-section thickness |
| **Stratigraphic heterogeneity index** | Characterise lateral variability in bed thickness | Horizon surfaces as above | Scalar or along-strike CSV | MAE vs. reference; distribution of thickness residuals | Connects to compensation: random compensation → κ → 1, compensational → κ < 1 |

### Other stratigraphy metrics

| Benchmark | Task | Input | Output | Scoring | Notes |
|---|---|---|---|---|---|
| **Bed thickness statistics** | Mean, std, and skewness of individual bed thicknesses from a vertical section | Horizon GeoTIFFs or a stratigraphic column CSV | CSV of summary statistics | MAE per statistic vs. reference column log | Standard in subsurface reservoir characterisation |
| **Lobe stacking pattern classification** | Classify stacking pattern as compensational, clustered, or random | Stratigraphic surfaces | Categorical label per sub-interval | Accuracy vs. labelled reference | Wang et al. (2011); Straub & Pyles (2012) |
| **Clinoform geometry extraction** | Locate and measure clinoform surfaces (topset/foreset/bottomset geometry) | Seismic section image or DEM cross section | CSV of break-point positions and dip angles | MAE on break-point position, angular RMSE on foreset dip | Applicable to deltaic and shelf-margin systems |
| **Subsidence / accommodation estimation** | Infer spatial pattern of accommodation from stratigraphic thickness map | Multi-horizon GeoTIFF stack | Accommodation-rate raster GeoTIFF | RMSE vs. reference (from model output or published backstripping) | Could use DeltaRCM or Stratigraphic Forward Model outputs |

---

## Laboratory experiment channel masks

This benchmark is larger in scope than the others: it uses a paired-image dataset from physical flume experiments, where both an RGB overhead photograph and a hand-classified binary channel mask exist for the same moment in time.
The task is to recover the channel mask (water vs. non-water) from the raw RGB image.

**Why this is different from the field benchmarks:**
- Input is RGB imagery, not a geophysical raster — tools may use colour thresholding, ML classifiers, or physics-based approaches.
- The dataset is large (many image pairs across multiple experiments and facilities), enabling both accuracy benchmarking and generalisation testing across lighting conditions, sediment colours, and experimental setups.
- Pixel-scale ground truth is available, so scoring is straightforward.

| Benchmark | Task | Input | Output | Scoring | Notes |
|---|---|---|---|---|---|
| **Channel mask from lab RGB (single image)** | Classify each pixel as channel (water) or non-channel from a single overhead photo | Single RGB GeoTIFF (or image + camera calibration) | Binary mask GeoTIFF (or equivalent raster) | Pixel F1, IoU, precision, recall vs. hand-classified reference mask | Baseline method: colour thresholding (e.g. in-situ calibration); upper bound: human-agreement F1 |
| **Channel mask from lab RGB (cross-experiment generalisation)** | Same task but scored separately on held-out experiments not seen during calibration | Multi-experiment RGB+mask dataset; train/test split by experiment ID | Binary mask per test image | F1 and IoU broken down by experiment; generalisation gap metric | Tests whether a calibration-free or transfer-learning approach is needed |
| **Shoreline / wetted-perimeter extraction from lab image** | Extract the water-edge polyline from a lab overhead photo | RGB GeoTIFF | Polyline GeoJSON (or pixel-space polyline) | Mean distance error vs. reference edge; F1 on edge pixels | Directly comparable to the field shoreline benchmark |
| **Channel mask time series** | Produce masks for a temporal sequence (morphodynamic experiment) | Time-ordered RGB image stack | Binary mask stack (raster or NetCDF) | Per-frame F1; temporal consistency metric (mask flickering penalty) | Large dataset; could include DeltaRCM, TDB, or St. Anthony Falls lab data |

**Candidate datasets:**
- St. Anthony Falls Laboratory (University of Minnesota) overhead experiment imagery
- Delft 3D / Froude-scaled delta experiments
- Any lab group willing to contribute paired RGB + hand-masked images under CC-BY

**Suggested data format for submissions:**
```
submissions/your-method-name/
├── masks/
│   ├── frame_0001.tif
│   ├── frame_0002.tif
│   └── ...
└── metadata.yaml
```

---

## Cross-cutting ideas

- **Multi-epoch change detection** — several domains (coasts, dunes, rivers) share the same two-epoch-mask structure; a single shared scoring module could handle all of them.
- **Uncertainty quantification** — allow submissions to include a confidence raster alongside the output; score calibration (reliability diagrams) as an optional extra metric.
- **Speed benchmark** — record wall-clock time on a reference machine as a secondary metric, opt-in for submitters who want to report it.
- **Synthetic data tier** — for each benchmark, include a synthetic (modelled) input with a known exact answer, so submitters can test their pipeline before running on real data.
