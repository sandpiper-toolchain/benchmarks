# Contributing to sandpiper benchmarks

## Adding a submission to an existing benchmark

1. **Fork** this repository and create a branch.
2. Inside the benchmark folder (e.g. `benchmarks/selenga_shoreline/`), create
   a subfolder under `submissions/` named after your method:
   ```
   submissions/your-method-name/
   ├── <result-file>    # your output (see benchmark README for the required format)
   └── metadata.yaml    # see submissions/example/metadata.yaml in the benchmark folder
   ```
3. The required result file name and format are defined in the benchmark's
   `benchmark.yaml` under the `submission:` block (e.g. `file_pattern: "results.geojson"`).
   Each benchmark's README also describes what the file must contain and any
   CRS or column requirements.
4. Fill in `metadata.yaml` — at minimum provide `method_name`,
   `method_version`, and `date`.  See the table below for all allowed
   fields.
5. Open a pull request. CI will automatically score your submission and
   upload a `score_output.json` artifact with the results.

   To test locally before opening a PR, run from the **repository root**:
   ```bash
   python score.py <benchmark_slug> submissions/your-method-name/<result-file>
   ```

### `metadata.yaml` fields

Every submission folder must contain a `metadata.yaml` file.
The table below defines all recognised fields; unknown fields are ignored.

| Field | Required | Description |
|---|---|---|
| `method_name` | **yes** | Short name of the method or tool (e.g. `"BAMBI"`, `"sandplover OAM"`) |
| `method_description` | **yes** | One-paragraph plain-English description of the approach |
| `method_version` | recommended | Version string of the tool or script (e.g. `"0.5.1"`, `"1.0"`) |
| `method_url` | recommended | URL for the tool's repository, documentation, or Zenodo archive |
| `author_name` | **yes** | Name(s) of the person(s) submitting the result (e.g. `"Smith et al."`) |
| `author_orcid` | optional | ORCID iD of the submitting author (e.g. `"0000-0000-0000-0000"`) |
| `preferred_citation` | optional | Full citation for the paper describing the method |
| `date` | **yes** | ISO 8601 date the result was produced (e.g. `"2025-01-15"`) |
| `notes` | optional | Caveats, preprocessing steps, parameter choices, or other remarks |
| `runtime_seconds` | optional | Wall-clock compute time in seconds (exclude pre/post-processing) |
| `runtime_machine` | optional | Hardware description (e.g. `"Intel i7-10700, 64 GB RAM"`) |
| `runtime_notes` | optional | Free-text notes on the runtime environment (e.g. `"single-thread, CPU"`) |

> **How the website updates:** once your PR is merged to `main`, CI
> recompiles the results tables, builds the site with `build_site.py`, and
> publishes it to the `gh-pages` branch. Your submission will appear on the
> live site after that step finishes (usually within a few minutes of merge).
> Generated HTML is not committed to `main`; you do not need to run any
> build or scoring scripts yourself.

## Adding a reference solution to an existing benchmark

> This section applies only to benchmarks of `reference_type` `reference`. 
> See below about defining new benchmarks for more information.

Reference solutions are one or more expert digitizations of the benchmark
answer (e.g. a hand-mapped shoreline).  They are **not** treated as
absolute ground truth — inter-reference spread reflects genuine
interpretation uncertainty.

To add a new reference digitization:

1. Add the GeoJSON file to the benchmark's `data/` directory, following the
   naming convention `ref_<author>_<year>.geojson`
   (e.g. `ref_smith_2026.geojson`).
2. Add a corresponding entry to `data/references.yaml` with full provenance
   metadata (author, ORCID if available, date, digitization method, any
   relevant notes).
3. Open a pull request describing how the reference was produced.

## Proposing a new benchmark

Open an issue describing:
- The geomorphic problem (shoreline mapping, channel width, etc.)
- The input data you can provide and its licence
- A proposed reference solution or ground truth (if applicable — see taxonomy below)
- Why this problem is useful to the community

Once the issue is discussed and the benchmark is accepted, create the
required files and open a pull request.

### Required files and directories

Every benchmark must include the following layout under `benchmarks/`:

```
benchmarks/<benchmark-name>/
├── benchmark.yaml      ← required: benchmark identity, taxonomy, submission format,
│                                   scoring config (see below)
├── README.md           ← required: problem statement, input data description,
│                                   instructions for downloading large data files,
│                                   data licence, etc.
├── data/               ← required: input data files and reference solutions;
│                                   [FUTURE: large binary files (GeoTIFFs, etc.) are 
│                                   gitignored and distributed separately — document 
│                                   the download location in the README]
└── submissions/        ← required: one subfolder per submission; can be empty
    └── example/           initially, but should include a template so contributors
        └── metadata.yaml  know what to fill in
```

The `data/` and `submissions/` folders may be empty at first (use a `.gitkeep`
file to track them), but all four items must be present before the benchmark
is merged.

### Benchmark taxonomy and `benchmark.yaml`

Every benchmark is classified by two independent attributes declared in
`benchmark.yaml`. Together they determine which scoring runner is used,
what output the scorer produces, and how results are displayed on the website.

#### Reference type

| Value | Meaning |
|---|---|
| `validation` | A known analytical or theoretical answer exists; submissions are scored against it |
| `reference` | One or more expert interpretations exist; submissions are compared to them, but they are not treated as absolute truth |
| `intercomparison` | No ground truth; submissions are shown side-by-side to reveal method differences |

#### Data type

| Value | Meaning |
|---|---|
| `value` | Submission is a small set of scalar numbers (e.g. a YAML file with computed statistics) |
| `identification` | Submission is a table of detected objects with per-object attributes (e.g. a CSV of bedform heights and lengths) |
| `map` | Submission is a spatial file — a vector GeoJSON (polyline, polygon, or point) or raster — compared geometrically against references |

#### Supported combinations

The scoring infrastructure dispatches entirely on the `(reference_type, data_type)` pair:

| `reference_type` | `data_type` | Status | Example benchmark |
|---|---|---|---|
| `validation` | `value` | ✅ implemented | `compensation` |
| `reference` | `value` | ✅ implemented | — |
| `intercomparison` | `value` | ✅ implemented | `compensation_sensitivity` |
| `intercomparison` | `identification` | ✅ implemented | `river_dunes` |
| `reference` | `map` | ✅ implemented | `selenga_shoreline` |
| `validation` | `map` | ✅ implemented | — |
| `reference` | `identification` | ⚠️ not yet implemented | — |
| `validation` | `identification` | ⚠️ not yet implemented | — |
| `intercomparison` | `map` | ⚠️ not yet implemented | — |

If your proposed benchmark requires a combination marked "not yet implemented",
mention it in the issue — adding a new runner is straightforward and can be
done as part of the same pull request.

#### `benchmark.yaml` overview

The `benchmark.yaml` file is the single source of truth for the benchmark.
The scoring CLI reads it to know what to compute; the website reads it to
know what to display.  Full examples for each reference type follow.

---

##### `validation`

A known theoretical or analytical answer exists.  `fields` is a dict mapping
each submitted field name to its truth value; the scorer computes the
configured error metrics against those targets.

```yaml
# ── Identity ───────────────────────────────────────────────────────
name:    "My Validation Benchmark"
slug:    "my-benchmark"          # URL path segment; keep it short and lowercase
tagline: "One-sentence description for benchmark cards"
domain:  "fluvial"               # fluvial | coastal | stratigraphy | aeolian | lab | other
status:  "active"                # active | draft | archived

# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "validation"
data_type:      "value"          # value | identification | map

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "results.yaml"   # glob pattern the scorer uses to find the result file

# ── References ─────────────────────────────────────────────────────
# Each entry is one dataset.  fields is a dict mapping field name → truth value.
# The scorer computes the configured metrics for each submitted field.
references:
  dataset_a:
    label:     "Dataset A"
    data_file: "data/dataset_a.csv"
    fields:                      # dict → validation; scored against known truth values
      myvarname: 1.0
  dataset_b:
    label:     "Dataset B"
    data_file: "data/dataset_b.csv"
    fields:
      myvarname: 0.5

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  metrics:
    - name:      abs_error
      label:     "Absolute error"
      direction: lower_better    # lower_better | higher_better
    - name:      rel_error_pct
      label:     "Relative error (%)"
      direction: lower_better
```

Available value metrics: `abs_error`, `rel_error_pct`, `mae`, `rmse`.

---

##### `reference`

One or more expert interpretations exist; submissions are compared to them but
they are not treated as absolute truth.  Inter-reference spread reflects genuine
interpretation uncertainty.

For `map` benchmarks each reference entry points to a GeoJSON file and the
scorer computes geometric metrics against each one.  For `value` benchmarks
the structure is identical to `validation` — `fields` is a dict of expert
values and the scorer computes error metrics against them.

```yaml
# ── Identity ───────────────────────────────────────────────────────
name:    "My Reference Benchmark"
slug:    "my-benchmark"
tagline: "One-sentence description for benchmark cards"
domain:  "coastal"               # fluvial | coastal | stratigraphy | aeolian | lab | other
status:  "active"

# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "reference"
data_type:      "map"
map_subtype:    "vector"         # vector | raster
geometry_type:  "polyline"       # polyline | polygon | point

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "results.geojson"

# ── References ─────────────────────────────────────────────────────
# Each entry is one expert-digitized reference solution.
# Provenance metadata (author, date, method) is kept in data/references.yaml;
# the scorer reads paths directly from the file: key here.
references:
  expert_a_2025:
    label: "Expert A 2025"
    file:  "data/ref_expert_a_2025.geojson"
  expert_b_2025:
    label: "Expert B 2025"
    file:  "data/ref_expert_b_2025.geojson"

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  raster_grid: "data/input.tif"  # gitignored; downloaded separately; required by pixel_f1
  metrics:
    - name:      mean_distance_error_m
      label:     "Mean distance error"
      unit:      m
      direction: lower_better
    - name:        pixel_f1
      label:       "Pixel F1"
      unit:        ""
      direction:   higher_better
      result_path: "pixel_f1.f1"  # scorer returns {precision, recall, f1}; extract f1 scalar

# ── Website ────────────────────────────────────────────────────────
# Required for map benchmarks only — see "Website configuration" below.
website:
  map_panel:
    raster:      "data/input.tif"
    reference:                   # a single reference line to overlay for visual context
      path: "data/ref_expert_a_2025.geojson"
      name: "reference (manual)"
    land_color:  "#e8dfc7"       # hex fill for land pixels in the binary mask
    water_color: "#c5dfe2"       # hex fill for water pixels
    crs:         "EPSG:32648"    # projected CRS of the raster and submission files
    crs_proj4:   "+proj=utm +zone=48 +datum=WGS84 +units=m +no_defs"
                                 # proj4 string for the same CRS; required together with crs
```

Available map metrics: `mean_distance_error_m`, `pixel_f1`.

The `result_path` field is required for any metric where the scorer returns a
nested dict rather than a flat scalar.  For example, `pixel_f1` returns
`{precision, recall, f1}` — setting `result_path: "pixel_f1.f1"` tells the
site to extract and display the `f1` value.  Omit `result_path` when the
metric is already a flat scalar (e.g. `mean_distance_error_m`).

---

##### `intercomparison`

No ground truth exists; submissions are shown side-by-side.

**Value data type** — `fields` is a plain list of field names.  The scorer
collects submitted values as-is and reports them without computing errors:

```yaml
# ── Identity ───────────────────────────────────────────────────────
name:    "My Intercomparison Benchmark"
slug:    "my-benchmark"
tagline: "One-sentence description for benchmark cards"
domain:  "fluvial"
status:  "active"

# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "intercomparison"
data_type:      "value"

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "results.yaml"

# ── References ─────────────────────────────────────────────────────
references:
  dataset_a:
    label:     "Dataset A"
    data_file: "data/dataset_a.csv"
    fields:    [myvarname, anothervarname]  # list → intercomparison; values reported as-is
  dataset_b:
    label:     "Dataset B"
    data_file: "data/dataset_b.csv"
    fields:    [myvarname, anothervarname]

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  data_dir: "data/"              # optional; only needed if data lives in a sibling directory
  # No metrics block: intercomparison value benchmarks report submitted values as-is.
```

**Identification data type** — no `references:` block at all.  The scorer
reads `scoring.columns` to determine which CSV columns to summarise, and
computes distribution statistics for each:

```yaml
# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "intercomparison"
data_type:      "identification"

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "results.csv"
  required_columns:              # documented for contributors; also validated by the scorer
    - name: height_m
      type: float
      unit: m
  optional_columns:
    - name: profile_id
      type: int

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  columns: [height_m, length_m, width_m]  # columns to compute distribution statistics for
  stats:   [min, mean, median, std, p25, p75, max]
```

---

#### Website configuration

The `website:` block is **only required for `map` benchmarks**.  Value and
identification benchmarks do not need it — the site generates result charts
automatically from `results_table.json`.

For map benchmarks, `website.map_panel` configures the interactive map canvas
shown alongside the results table on the benchmark's page.

| Field | Required | Description |
|---|---|---|
| `raster` | **yes** | Path to the benchmark raster (usually the same file as `scoring.raster_grid`). The site renders it as a coloured binary mask behind all submission lines. |
| `reference` | recommended | A single reference GeoJSON to overlay on the map for visual context. Contains `path` (file path relative to the benchmark directory) and `name` (display label shown in the map legend). When multiple references exist, pick the one most useful as a visual anchor. |
| `land_color` | **yes** | Hex colour for land pixels in the binary mask (e.g. `"#e8dfc7"`). |
| `water_color` | **yes** | Hex colour for water pixels (e.g. `"#c5dfe2"`). |
| `crs` | **yes** | EPSG code of the projected CRS used by the raster and expected by the scorer (e.g. `"EPSG:32648"`). The site reprojects submissions that arrive in geographic coordinates (lon/lat) into this CRS before drawing them on the canvas. |
| `crs_proj4` | **yes** | Proj4 string for the same CRS (e.g. `"+proj=utm +zone=48 +datum=WGS84 +units=m +no_defs"`). Must be provided together with `crs`. |

## Data licensing

All input datasets and reference solutions (digitizations) must be openly
licensed (CC-BY or equivalent). Please include a note in the benchmark
README about the data source and licence.

## Code style

Scoring is handled by a shared Python library under `scoring/` at the repository
root.  Metric functions live in `scoring/metrics/`; the dispatch logic lives in
`scoring/runners.py`; `score.py` at the repository root is the CLI entry point.
Dependencies are minimal: `geopandas`, `rasterio`, `scipy`, `numpy`, `shapely`,
`pyyaml`. Do not add heavy ML frameworks to the scoring layer.
