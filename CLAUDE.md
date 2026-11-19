# benchmarks — project context for Claude Code

## What this project is

**benchmarks** is a repository within the **sandpiper** project — an umbrella effort to build
open, community-facing tools and resources for geomorphology research. sandplover (a Python
package for delta analysis) is a sibling project under the same umbrella.

The goal of this repo is to give the community (researchers, software developers, students) a
shared set of real-world problems they can run any tool against and compare results fairly.

It is explicitly *not* a competition — more like a shared test suite for geomorphology software.

## Design principles

- **Output-only submissions.** Contributors submit a result file (GeoJSON, CSV, raster), not code.
  Any tool, language, or workflow is welcome.
- **Real-world data.** Each benchmark uses actual field or laboratory data, not purely synthetic inputs. 
  (Synthetic inputs are also acceptable.)
- **Minimal infrastructure.** Scoring scripts are plain Python (`geopandas`, `rasterio`, `scipy`,
  `numpy`, `shapely`). No heavy ML frameworks in the scoring layer.
- **CI-scored.** GitHub Actions runs the scorer automatically on every PR that adds a submission,
  posting results as a build artifact.
- **Openly licensed data only.** All inputs and reference solutions must be CC-BY or equivalent.

## Benchmark taxonomy

Every benchmark is classified by two independent attributes. Together they determine
which scoring metrics apply, how results are displayed, and what chart type the website
generates. **Every benchmark has exactly one reference type and one data type.**

### Reference type

| Value | Meaning |
|---|---|
| `validation` | A known analytical or theoretical answer exists; submissions are scored against it |
| `reference` | One or more expert interpretations exist; submissions are compared to them, but they are not treated as absolute truth |
| `intercomparison` | No ground truth; submissions are shown side-by-side to reveal method differences |

### Data type

| Value | Meaning |
|---|---|
| `identification` | Submission is a table of detected objects with per-object attributes (e.g. a CSV of bedform heights, lengths) |
| `map` | Submission is compared spatially — a vector (GeoJSON polyline/polygon/point) or raster compared for distance, overlap, or pixel agreement |
| `value` | Submission is a small set of scalar numbers, compared by MAE / relative error against references or against each other |

### Current benchmarks

| Benchmark | Reference type | Data type | Notes |
|---|---|---|---|
| `river_dunes` | intercomparison | identification | Distributions of H, L, d compared across methods |
| `shoreline` | reference | map · vector polyline | Submissions scored against expert-digitized polylines |
| `compensation` | validation | value | Two T_A = 1 datasets with theoretical κ reference values |
| `compensation_sensitivity` | intercomparison | value | Two T_A = 15/30 datasets; κ and T_c compared across methods |

## `benchmark.yaml` schema

Each benchmark has a `benchmark.yaml` at its root directory — the single source of truth
for the benchmark's identity, taxonomy, submission format, metrics, and website config.
All scoring scripts, compile scripts, and website templates read from it.

```yaml
# ── Identity ───────────────────────────────────────────────────────
name:    "Human-readable benchmark name"
slug:    "public-route"        # URL path segment; may differ from the directory name
tagline: "One-sentence description for benchmark cards"
domain:  "fluvial"             # fluvial | coastal | stratigraphy | aeolian | lab | other
status:  "active"              # active | draft | archived

# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "validation"   # validation | reference | intercomparison
data_type:      "value"        # identification | map | value

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "results.yaml" # glob pattern for submission files

# ── Datasets (value benchmarks) ────────────────────────────────────
datasets:
  <dataset_key>:
    label:            "Human label for the dataset"
    data_file:        "data/file.csv"
    reference_values:          # validation only
      kappa: 1.0
    scored_fields:    [kappa]  # validation only
    reported_fields:  [kappa, Tc]  # intercomparison only

# ── References (map benchmarks) ────────────────────────────────────
references:
  manifest: "data/references.yaml"

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  raster_grid: "data/input.tif"   # map benchmarks; gitignored, downloaded separately
  data_dir:    "../other/data/"   # value benchmarks that share data with a sibling
  metrics:
    - name:        metric_name
      label:       "Human label"
      unit:        m
      direction:   lower_better   # lower_better | higher_better
      result_path: "nested.key"   # optional; dotted path into a vs_references entry when
                                  #   the scorer stores the metric as a nested object rather
                                  #   than a flat scalar (e.g. "pixel_f1.f1" or
                                  #   "roughness_agreement.relative_difference_pct").
                                  #   Omit when the metric is already a flat scalar.

# ── Website ────────────────────────────────────────────────────────
website:
  map_panel:                      # map benchmarks only
    raster:      "data/input.tif"
    land_color:  "#e8dfc7"
    water_color: "#c5dfe2"
    crs:         "EPSG:32648"     # CRS of the raster / projected submissions; required when
                                  #   submissions may be in geographic coordinates (lon/lat)
                                  #   so the site can reproject lines onto the map canvas
    crs_proj4:   "+proj=utm +zone=48 +datum=WGS84 +units=m +no_defs"
                                  # proj4 definition string for `crs`; must be provided
                                  #   together with `crs`
```

Fields that point to gitignored files (e.g. `scoring.raster_grid`) are optional hints;
scoring scripts detect missing files at startup and exit with a clear, actionable message.

## Repo structure

Benchmarks live under `benchmarks/`, separate from repository-level
documentation, configuration, and website files. Each benchmark uses a
consistent layout:

```
<repository-root>/
├── CLAUDE.md                    ← you are here
├── README.md                    ← table of all benchmarks
├── CONTRIBUTING.md
├── brainstorm.md                ← ideas for future benchmarks
├── score.py                     ← top-level scoring CLI (score one submission or compile all)
├── .github/
│   └── workflows/
│       └── score.yml            ← CI workflow (score on PRs; compile on push to main)
├── scoring/                     ← shared scoring library
│   ├── benchmark.py             ← loads benchmark.yaml → BenchmarkConfig
│   ├── compile.py               ← discover submissions, compile results_table.json
│   ├── metadata.py              ← reads metadata.yaml
│   ├── output.py                ← writes score_output.json and results_table.json
│   ├── runners.py               ← score_one_* functions + RUNNERS dispatch table
│   └── metrics/
│       ├── value_metrics.py
│       ├── identification_metrics.py
│       └── map_metrics.py
├── assets/                      ← website styles and scripts
├── index.html                   ← generated locally; published from gh-pages, not tracked
└── benchmarks/
    └── <benchmark-name>/        ← one folder per benchmark
        ├── benchmark.yaml       ← benchmark identity, taxonomy, schema, scoring config
        ├── README.md            ← problem statement, data description, results table
        ├── index.html           ← generated locally; published from gh-pages, not tracked
        ├── results_table.json   ← auto-generated by scoring; published with the gh-pages site
        ├── data/                ← input data and reference digitizations
        │   ├── <input>          ← benchmark input (raster, image, CSV, …); large files gitignored
        │   ├── references.yaml  ← manifest of reference digitizations with provenance metadata
        │   └── ref_<author>_<year>.geojson  ← one or more expert reference solutions
        └── submissions/
            ├── example/
            │   └── metadata.yaml  ← template for contributors
            └── <method-name>/
                ├── <result-file>  ← the submission (GeoJSON, CSV, raster, …)
                ├── metadata.yaml
                └── score_output.json  ← written by score.py; uploaded as CI artifact
```

**Data files:** Large binary inputs (GeoTIFFs, etc.) are gitignored (`*.tif`, `*.tiff` in
`.gitignore`) and distributed separately. Each benchmark README documents where to obtain them.

## Scoring conventions

All benchmarks are scored by a single top-level CLI, `score.py`, which reads
`benchmark.yaml` to understand what to compute and dispatches to the correct
runner automatically:

```
# Score one submission:
python score.py <benchmark> <submission> [--output results.json]

# Compile all submissions → results_table.json:
python score.py <benchmark> [--compile]
```

`<benchmark>` is either a directory path (e.g. `benchmarks/compensation/`) or a
benchmark slug (e.g. `compensation`).  Both forms work from the repository root.

- Exits with code 0 on success; prints a JSON summary to stdout (single-submission mode).
- Writes `score_output.json` next to the submission (or to `--output`).
- All metrics are computed against **every** reference in the `references:` block of `benchmark.yaml`.
- Output structure has two top-level keys:
  - `vs_references` — per-reference metric dicts, keyed by the reference slug.
  - `vs_references_summary` — mean and std across references (populated only when ≥2 references exist; empty dict `{}` otherwise).

Compile mode discovers all submissions, scores each one, and aggregates them:

- Walks `submissions/` and scores every file matching `submission.file_pattern`.
- Merges scoring results with the adjacent `metadata.yaml` for each submission.
- Writes `<benchmark_dir>/results_table.json` (a JSON array, one record per submission).
  This generated file is not tracked on `main`; CI includes it in the published site.
- Missing `metadata.yaml` files are handled gracefully (fields default to `null`).

Common metric patterns across benchmarks:

| Output type | Typical metrics |
|---|---|
| Polyline GeoJSON | Mean distance error, pixel F1, shape/roughness agreement |
| Polygon GeoJSON | IoU, area error |
| Point GeoJSON | Mean distance error, detection F1 |
| CSV of measurements | MAE / RMSE per column |
| Binary raster mask | Pixel F1, IoU |

**CI workflow**

**`score` job** — triggered on pull requests that touch `benchmarks/*/submissions/**`:
- Detects changed submission files via `git diff`
- Runs `python score.py <benchmark_slug> <submission_path>` for each changed submission
- Uploads `score_output.json` as a build artifact

**`compile` job** — triggered on relevant pushes to `main`:
- Runs `python score.py <benchmark_dir> --compile` for every benchmark
- Builds the static site into `_site/` and publishes it to the `gh-pages` branch
- Generated HTML pages and results tables are not committed to `main`

## Future benchmarks

See `brainstorm.md` for a full list of ideas across deltas, rivers, barrier islands,
aeolian dunes, alluvial fans, riverbed dunes, stratigraphy, and laboratory experiments.
Priority candidates: Colville delta channel network (RivGraph), dune crestline extraction,
single-thread river centerline, compensation statistic (κ), lab RGB → channel mask.
