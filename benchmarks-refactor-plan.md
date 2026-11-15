# Sandpiper Benchmarks — Refactor Architecture Plan

**Status:** In progress — phases 1–5 complete (phase 4 / CI done alongside phase 4)  
**Scope:** All existing benchmarks + future-proofing  
**Covers:** Python scoring · `benchmark.yaml` schema · Python build site · Chart.js

---

## 1. Motivation & Design Principles

The repo started with three benchmarks that share almost nothing structurally. Each has its own scoring script, its own compile script, its own ad hoc output format, and the website hard-codes each benchmark by name. Adding a fourth benchmark means copying boilerplate, extending an already-crowded `index.html`, and writing bespoke JS chart code. This does not scale.

**Four goals:**

| Goal | How it is addressed |
|---|---|
| Consistent benchmark structure | A `benchmark.yaml` per benchmark declares type, references, metrics, and submission format |
| Maintainable scoring code | Shared Python library at repo root; per-benchmark scripts become thin wrappers; one top-level runner |
| Scalable website | Python build script generates per-benchmark pages from templates; index regenerated automatically |
| Interactive charts | Chart.js replaces hand-coded SVG; chart type selected automatically from taxonomy |

> **Guiding constraint:** Existing benchmarks must remain fully functional throughout the refactor. Each phase should leave the repo in a working, deployable state.

---

## 2. The Benchmark Taxonomy

Every benchmark is classified by two independent attributes. Together they determine which scoring metrics apply, how results are displayed, and what chart type is generated.

**Every benchmark has exactly one reference type and one data type. No mixed types.**

### Attribute 1 — Reference type

- **validation** — a known analytical or theoretical answer exists; submissions are scored against it
- **reference** — one or more expert interpretations exist; submissions are compared to them, but not treated as absolute truth
- **intercomparison** — no ground truth; submissions are shown side by side to reveal method differences

### Attribute 2 — Data type

- **identification** — submission is a table of detected objects with per-object attributes (e.g. a CSV of bedform heights, lengths, depths)
- **map** — submission is compared spatially; either a vector (GeoJSON polyline/polygon/point) or raster compared for distance, overlap, or pixel agreement
- **value** — submission is a small set of scalar numbers, compared by MAE / relative error against references or against each other

### Benchmarks mapped to the taxonomy

| Benchmark | Reference type | Data type | Notes |
|---|---|---|---|
| `river_dunes` | intercomparison | identification | No ground truth; distributions of H, L, d compared across methods |
| `shoreline` | reference | map · vector polyline | Submissions scored against expert-digitized polylines; multiple refs supported |
| `compensation` | validation | value | Two datasets with theoretical κ references (T_A = 1); one submission file covers both datasets |
| `compensation_sensitivity` | intercomparison | value | Two datasets with no reference (T_A = 15, T_A = 30); separate submission, separate benchmark |

> **On the compensation split:** The original `compensation` benchmark mixed validation and intercomparison datasets in a single benchmark, requiring branching logic in both scoring code and the website. The two purposes are genuinely different: `compensation` tests whether a tool recovers a known κ, while `compensation_sensitivity` explores how κ and T_c change as the avulsion period scales up. Splitting eliminates all special-casing. Contributors submit one `results.yaml` to `compensation` (covering `compensational_stacking` and `random_stacking`) and a separate `results.yaml` to `compensation_sensitivity` (covering `compensational_stacking_meanX` and `compensational_stacking_mean2X`). The input CSV data files live in a shared `data/` directory referenced by both benchmarks.

### Chart type matrix

| Reference type | Data type | Primary chart | Notes |
|---|---|---|---|
| intercomparison | identification | Horizontal boxplot (min, p25, median, p75, max — one row per method) via `@sgratzl/chartjs-chart-boxplot` | Metric toggled by segmented control |
| reference / validation | map | Horizontal bar, one bar per method | Second panel: canvas map for vector submissions |
| validation | value | Horizontal bar with vertical reference-value marker | chartjs-plugin-annotation for the marker line |
| intercomparison | value | Horizontal bar, no reference marker | Dataset toggled by segmented control |

---

## 3. The `benchmark.yaml` Schema

Each benchmark gets a `benchmark.yaml` at its root directory. This is the single source of truth for the benchmark's identity, taxonomy, submission format, metrics, and website config. All scoring scripts, compile scripts, and website templates read from it.

**Separating "what the benchmark is" from "where data lives at runtime":** Fields like `scoring.raster_grid` point to files that are gitignored and downloaded separately. The schema treats these as optional hints; scoring scripts that need them should detect missing files early and exit with a clear message rather than a stack trace.

### Example — `river_dunes` (intercomparison · identification)

```yaml
# ── Identity ───────────────────────────────────────────────────────
name:    "Paraná River Bedform Geometry"
slug:    "river_dunes"          # must match the directory name
tagline: "Identify and measure dunes across 370 bathymetric profiles"
domain:  "fluvial"              # fluvial | coastal | stratigraphy | aeolian | lab | other
status:  "active"               # active | draft | archived

# ── Taxonomy ───────────────────────────────────────────────────────
reference_type: "intercomparison"
data_type:      "identification"

# ── Submission format ──────────────────────────────────────────────
submission:
  file_pattern: "result.csv"
  required_columns:
    - name: height_m
      type: float
      unit: m
    - name: length_m
      type: float
      unit: m
    - name: depth_m
      type: float
      unit: m
  optional_columns:
    - name: profile_id
      type: int

# ── Scoring ────────────────────────────────────────────────────────
scoring:
  mode:    "distribution_summary"  # computes stats per required column
  columns: [height_m, length_m, depth_m]
  stats:   [mean, median, std, p25, p75]
```

### Example — `shoreline` (reference · map)

```yaml
name:    "Selenga Delta Shoreline"
slug:    "shoreline"
tagline: "Trace the land–water boundary from a binary delta mask"
domain:  "delta"
status:  "active"

reference_type: "reference"
data_type:      "map"
map_subtype:    "vector"    # vector | raster
geometry_type:  "polyline"  # polyline | polygon | point

submission:
  file_pattern: "*.geojson"

references:
  manifest: "data/references.yaml"  # existing file, unchanged

scoring:
  raster_grid: "data/selenga_clipped.tif"  # gitignored; downloaded separately
  metrics:
    - name:      mean_distance_error_m
      label:     "Mean distance error"
      unit:      m
      direction: lower_better
    - name:      pixel_f1
      label:     "Pixel F1"
      unit:      ""
      direction: higher_better
    - name:      roughness_relative_difference_pct
      label:     "Roughness difference"
      unit:      "%"
      direction: lower_better

website:
  map_panel:
    raster:      "data/selenga_clipped.tif"
    land_color:  "#e8dfc7"
    water_color: "#c5dfe2"
```

### Example — `compensation` (validation · value)

```yaml
name:    "Compensation Index — Validation"
slug:    "compensation"
tagline: "Compute κ for two synthetic sequences with known theoretical values"
domain:  "stratigraphy"
status:  "active"

reference_type: "validation"
data_type:      "value"

submission:
  file_pattern: "results.yaml"
  # Expected keys: compensational_stacking.kappa, random_stacking.kappa

datasets:
  compensational_stacking:
    label:            "Compensational stacking, T_A = 1"
    reference_values:
      kappa: 1.0
    scored_fields:    [kappa]
  random_stacking:
    label:            "Random stacking, T_A = 1"
    reference_values:
      kappa: 0.50
    scored_fields:    [kappa]

scoring:
  metrics:
    - name:      abs_error
      label:     "Absolute error"
      direction: lower_better
    - name:      rel_error_pct
      label:     "Relative error (%)"
      direction: lower_better
```

### Example — `compensation_sensitivity` (intercomparison · value)

```yaml
name:    "Compensation Index — Sensitivity"
slug:    "compensation_sensitivity"
tagline: "Compare κ and T_c across methods for scaled avulsion periods"
domain:  "stratigraphy"
status:  "active"

reference_type: "intercomparison"
data_type:      "value"

submission:
  file_pattern: "results.yaml"
  # Expected keys: compensational_stacking_meanX.{kappa, Tc}
  #                compensational_stacking_mean2X.{kappa, Tc}

datasets:
  compensational_stacking_meanX:
    label:           "Compensational stacking, T_A = 15"
    reported_fields: [kappa, Tc]
  compensational_stacking_mean2X:
    label:           "Compensational stacking, T_A = 30"
    reported_fields: [kappa, Tc]

scoring:
  # No reference values — values reported as-is for cross-submission comparison
  reported_fields: [kappa, Tc]
```

---

## 4. New Repository Structure

```
<repo-root>/
├── CLAUDE.md                        # update: add taxonomy + schema docs
├── README.md
├── CONTRIBUTING.md
├── brainstorm.md
│
├── run_all.py                       # NEW: discovers + runs all benchmark score.py
├── build_site.py                    # NEW: reads benchmark.yaml + results_table.json,
│                                    #      renders templates, writes per-benchmark HTML
│
├── scoring/                         # NEW: shared Python library
│   ├── __init__.py
│   ├── benchmark.py                 # BenchmarkConfig: load + validate benchmark.yaml
│   ├── metadata.py                  # canonical metadata.yaml reader
│   ├── output.py                    # write_score_output(), write_results_table()
│   └── metrics/
│       ├── __init__.py
│       ├── map_metrics.py           # MDE, pixel_f1, roughness (from shoreline/metrics.py)
│       ├── value_metrics.py         # abs_error, rel_error_pct, mae, rmse
│       └── identification_metrics.py  # distribution_stats() (from river_dunes)
│
├── templates/                       # NEW: HTML templates for build_site.py
│   ├── benchmark_page.html          # per-benchmark page template
│   └── index.html                   # index page template
│
├── .github/workflows/
│   └── score.yml                    # CHANGED: score job + compile + build + deploy
│
├── assets/
│   ├── benchmark-dashboard.css      # CHANGED: extend with benchmark-page panel styles
│   ├── benchmark-dashboard.js       # CHANGED: strip to index-only code
│   └── benchmark-page.js            # NEW: generic Chart.js benchmark page
│
├── index.html                       # CHANGED: regenerated by build_site.py
│
└── benchmarks/
    ├── river_dunes/
    │   ├── benchmark.yaml           # NEW
    │   ├── index.html               # NEW: generated by build_site.py (committed by CI)
    │   ├── README.md
    │   ├── results_table.json
    │   ├── data/
    │   ├── scoring/
    │   │   ├── score.py             # NEW (replaces compile_results.py)
    │   │   └── compile_results.py   # kept as alias or removed
    │   └── submissions/
    │
    ├── shoreline/
    │   ├── benchmark.yaml           # NEW
    │   ├── index.html               # NEW: generated
    │   ├── README.md
    │   ├── results_table.json
    │   ├── data/
    │   ├── scoring/
    │   │   ├── score.py             # CHANGED: reads benchmark.yaml + calls shared lib
    │   │   └── metrics.py           # CHANGED: thin re-export from shared lib
    │   └── submissions/
    │
    ├── compensation/
    │   ├── benchmark.yaml           # NEW (validation only: T_A=1 datasets)
    │   ├── index.html               # NEW: generated
    │   ├── README.md                # CHANGED: clarify split; point to compensation_sensitivity
    │   ├── results_table.json
    │   ├── data/                    # CSV files shared with compensation_sensitivity
    │   ├── scoring/
    │   │   ├── score.py             # CHANGED: validation datasets only
    │   │   └── metrics.py           # CHANGED: thin re-export
    │   └── submissions/
    │
    └── compensation_sensitivity/    # NEW benchmark directory
        ├── benchmark.yaml           # NEW (intercomparison: T_A=15, T_A=30 datasets)
        ├── index.html               # NEW: generated
        ├── README.md                # NEW
        ├── results_table.json       # NEW (empty array initially)
        ├── data/                    # symlink or relative path to compensation/data/
        ├── scoring/
        │   ├── score.py             # NEW
        │   └── metrics.py           # re-export
        └── submissions/
            └── example/
                └── metadata.yaml
```

> **`river_dunes` special case:** Currently has only `compile_results.py`, no `score.py`. After the refactor it gets a unified `score.py` that scores all submissions and writes `results_table.json` in one pass. The old `compile_results.py` can be removed or kept as a one-line alias.

> **`compensation_sensitivity` data:** The input CSVs live in `compensation/data/`. The sensitivity benchmark's `scoring/score.py` references them via a relative path. The `benchmark.yaml` `scoring.data_dir` field points to `../compensation/data/`.

---

## 5. Python Scoring Infrastructure

### Shared library — `scoring/`

#### `scoring/benchmark.py`

Loads and validates `benchmark.yaml`. Returns a `BenchmarkConfig` dataclass consumed by all scripts.

```python
class BenchmarkConfig:
    name: str
    slug: str
    reference_type: str           # validation | reference | intercomparison
    data_type: str                # identification | map | value
    submission_file_pattern: str
    scoring: dict
    datasets: dict | None         # populated for multi-dataset benchmarks
    references_manifest: Path | None
    website: dict

def load_config(benchmark_dir: Path) -> BenchmarkConfig: ...
```

#### `scoring/metadata.py`

Canonical set of standard `metadata.yaml` fields (superset of what any benchmark currently uses), plus a reader that returns a flat dict with `None` defaults for missing fields. Replaces the duplicate `read_metadata()` functions currently in each benchmark.

#### `scoring/output.py`

```python
def write_score_output(results: dict, submission_path: Path, out_path: Path | None = None) -> Path:
    """Write score_output.json next to the submission (or to out_path)."""
    ...

def write_results_table(records: list[dict], benchmark_dir: Path) -> Path:
    """Write results_table.json at the benchmark root."""
    ...
```

#### `scoring/metrics/map_metrics.py`

Extracted verbatim from `benchmarks/shoreline/scoring/metrics.py`. Exports `mean_distance_error`, `pixel_f1`, `roughness_agreement`. The shoreline benchmark's own `metrics.py` becomes a one-line re-export.

#### `scoring/metrics/value_metrics.py`

Exports `abs_error`, `rel_error_pct`, `mae`, `rmse`. Extracted from the compensation benchmark.

#### `scoring/metrics/identification_metrics.py`

Exports `distribution_stats(series: pd.Series) → dict`. Extracted from `river_dunes/scoring/compile_results.py`.

### Per-benchmark `score.py`

Each benchmark's `score.py` becomes a thin wrapper (~50 lines) that:

1. Calls `load_config(HERE.parent)` to get `BenchmarkConfig`
2. Finds all submissions using the config's `file_pattern`
3. Calls the appropriate shared scorer for the `data_type`
4. Writes `score_output.json` per submission and `results_table.json` at the benchmark root

The existing CLI interface is preserved for backward compatibility:

```bash
# Score one submission:
python benchmarks/shoreline/scoring/score.py submissions/my-method/result.geojson

# Score all submissions (default when no arg given):
python benchmarks/shoreline/scoring/score.py
```

**Missing data handling:** If a scoring script requires a file that is gitignored (e.g. a large raster), it must detect the missing file at startup and exit with a clear, actionable message — not a stack trace. Example:

```
ERROR: benchmark raster not found: benchmarks/shoreline/data/selenga_clipped.tif
  This file is not committed to git. Download it from:
  https://...
```

### Top-level `run_all.py`

```python
#!/usr/bin/env python
"""Run scoring for all benchmarks and regenerate all results_table.json files.

Usage:
    python run_all.py                  # run all benchmarks
    python run_all.py shoreline        # run one benchmark by slug
    python run_all.py --dry-run        # list what would run without executing
"""
def main():
    score_scripts = sorted(Path("benchmarks").glob("*/scoring/score.py"))
    for score_py in score_scripts:
        slug = score_py.parent.parent.name
        subprocess.run([sys.executable, str(score_py)], check=True)
```

This is the single script that CI calls. Contributors run it locally to regenerate all results after adding a submission.

---

## 6. Website Architecture

### Approach: Python build script

Rather than introducing Jekyll (which requires Ruby, restricts plugins in native GitHub Pages mode, and complicates the benchmark.yaml → page-data pipeline), website pages are generated by a plain Python script that runs in CI alongside the scoring step.

**`build_site.py`** at the repo root:

1. Discovers all benchmarks by globbing `benchmarks/*/benchmark.yaml`
2. For each benchmark, loads `benchmark.yaml` and `results_table.json`
3. Renders `templates/benchmark_page.html` with that data, writing to `benchmarks/<slug>/index.html`
4. Renders `templates/index.html` with the full list of benchmarks, writing to `index.html`

Templates use Python's stdlib `string.Template` or `jinja2` (preferred for readability; add to CI `pip install` line). No Ruby, no Gemfile, no Jekyll config.

The generated HTML files are committed to `main` by the CI compile job alongside `results_table.json`, exactly as today. GitHub Pages continues to serve from the `main` branch with no settings change required.

**What the template receives** for each benchmark page:

```python
context = {
    "config":        benchmark_config_dict,       # full benchmark.yaml contents
    "results":       results_table_list,           # parsed results_table.json
    "benchmark_config_json": json.dumps(...),      # inlined as window.BENCHMARK_CONFIG
}
```

The `window.BENCHMARK_CONFIG` JSON is embedded inline in a `<script>` tag, so the page-level JS receives structured config without an extra fetch.

### Chart.js implementation — `assets/benchmark-page.js`

Load Chart.js 4.x from cdnjs (pinned exact version). The script does the following on page load:

1. Reads `window.BENCHMARK_CONFIG`
2. Fetches `results_table.json` (relative URL, same benchmark dir)
3. Calls the renderer for the benchmark's `reference_type × data_type` combination
4. Instantiates the Chart.js chart and wires up segmented controls

**Chart.js versions:**
- `cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`
- `cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js`
- `cdn.jsdelivr.net/npm/@sgratzl/chartjs-chart-boxplot@4.4.4/build/index.umd.min.js` (identification benchmarks only — included conditionally in the template)

| Benchmark | Chart.js type | Special handling |
|---|---|---|
| `river_dunes` | Horizontal boxplot (`boxplot` type, `indexAxis: 'y'`) via `@sgratzl/chartjs-chart-boxplot` | Data: `{ min, q1, median, q3, max }` per method per metric. No custom plugin needed. Metric toggled by segmented control. |
| `shoreline` | Horizontal bar | Value = mean across references when multiple exist. Metric toggled. Map panel (canvas) preserved from existing code. |
| `compensation` | Horizontal bar + annotation | Vertical reference-value line via chartjs-plugin-annotation. Dataset toggled by segmented control. |
| `compensation_sensitivity` | Horizontal bar | No reference marker. Dataset toggled by segmented control. |

**Shared JS utilities (internal to `benchmark-page.js`):**

- `methodLabel(record)` — `method_name || author_name || tool_name`
- `buildSegmented(container, options, onChange)` — renders a segmented toggle
- `methodCard(record, config)` — renders per-method sidebar card HTML
- `formatValue(v, digits, unit)` — localized number formatting with units
- `getMetricValue(record, metricName, config)` — extracts a scalar from a results-table record

### Index page

The revised `index.html` is generated by `build_site.py` from `templates/index.html`. It lists benchmarks from the discovered `benchmark.yaml` files (name, tagline, domain, submission count). No inline charts — those live on per-benchmark pages. Benchmark count and method count are computed at build time.

> **Note on PR visibility:** Per-benchmark pages only show results after CI has committed the compiled `results_table.json` and regenerated the HTML. A contributor's PR will not show their result on the live site until it is merged and the compile job runs. This is by design and should be documented clearly in `CONTRIBUTING.md`.

---

## 7. CI Changes

### Before vs. after

| | Before | After |
|---|---|---|
| **score job** (PR trigger) | Detects changed `result.geojson` files only; runs benchmark-specific `score.py` per file | Detects which benchmark *directories* contain changed submission files; runs `python run_all.py <slug>` per affected benchmark |
| **compile job** (push to main) | Finds each `compile_results.py`; runs it; commits changed `results_table.json` | Runs `python run_all.py`; then runs `python build_site.py`; commits changed `results_table.json` and generated HTML |

### Detecting affected benchmarks (score job) — corrected

The file pattern filter must be scoped to `submissions/` to avoid re-running scoring on PRs that only change a README or `benchmark.yaml`:

```bash
changed_benchmarks=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \
  | grep '^benchmarks/.*/submissions/' \
  | cut -d/ -f2 \
  | sort -u)

for slug in $changed_benchmarks; do
  echo "=== Scoring $slug ==="
  python run_all.py "$slug"
done
```

> **Why this matters:** The previous draft used `grep '^benchmarks/'` which would trigger the score job on any file touched under `benchmarks/`, including README edits, `benchmark.yaml` changes, and `results_table.json` itself. The corrected version fires only when a file under `submissions/` changes.

### Full updated `score.yml` (outline)

```yaml
name: Score and compile

on:
  pull_request:
    paths: ["benchmarks/*/submissions/**"]
  push:
    branches: [main]
    paths: ["benchmarks/*/submissions/**", "benchmarks/*/benchmark.yaml",
            "build_site.py", "templates/**", "assets/**"]

jobs:
  score:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install geopandas rasterio scipy numpy shapely pyyaml jinja2
      - name: Detect changed benchmarks and score
        run: |
          git fetch origin ${{ github.base_ref }} --depth=1
          changed=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \
            | grep '^benchmarks/.*/submissions/' \
            | cut -d/ -f2 | sort -u || true)
          for slug in $changed; do
            python run_all.py "$slug"
          done
      - uses: actions/upload-artifact@v4
        with:
          name: scores
          path: "**/score_output.json"

  compile:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install geopandas rasterio scipy numpy shapely pyyaml jinja2
      - run: python run_all.py
      - run: python build_site.py
      - name: Commit updated files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add '**/results_table.json' '**/index.html' 'index.html'
          if git diff --cached --quiet; then
            echo "Nothing changed."
          else
            git commit -m "chore: update results and site [skip ci]"
            git push
        ```

The key improvement: CI no longer needs to understand per-benchmark script names or submission file patterns. Adding a new benchmark requires zero CI changes.

---

## 8. Implementation Phases

Python track (phases 1–4) and website track (phases 5–7) are independent and can run in parallel. Within each track, phases must be sequential.

### ✅ Phase 1 — Taxonomy & `benchmark.yaml` files *(done)*
*Config only — no Python or website changes*

Create `benchmark.yaml` for all four benchmarks (including the new `compensation_sensitivity`) using the annotated examples in §3. Create the `compensation_sensitivity/` directory skeleton with an empty `submissions/example/` and stub `README.md`. Verify that every field currently hardcoded in each benchmark's scoring script is representable in the schema. Update `CLAUDE.md` with the taxonomy and schema documentation.

**Files touched:**
- `benchmarks/river_dunes/benchmark.yaml`
- `benchmarks/shoreline/benchmark.yaml`
- `benchmarks/compensation/benchmark.yaml`
- `benchmarks/compensation_sensitivity/` (new directory + benchmark.yaml + README.md + submissions/example/metadata.yaml)
- `CLAUDE.md`

### ✅ Phase 2 — Shared Python scoring library *(done)*
*New `scoring/` at repo root; existing scripts untouched*

Create the `scoring/` package as described in §5. Extract metric functions from the three existing benchmarks without modifying those benchmarks. Write pytest unit tests for all shared metric functions to establish a regression baseline. Existing benchmark scripts must continue to work unchanged at the end of this phase.

**Files touched:**
- `scoring/__init__.py`
- `scoring/benchmark.py`
- `scoring/metadata.py`
- `scoring/output.py`
- `scoring/metrics/map_metrics.py`
- `scoring/metrics/value_metrics.py`
- `scoring/metrics/identification_metrics.py`
- `tests/test_metrics.py`

### ✅ Phase 3 — Per-benchmark script refactor + `run_all.py` *(done)*

*Existing scripts rewritten to use shared library; compensation split goes live*

Refactor each benchmark's scoring script(s) to use the Phase 2 shared library. Add `score.py` to `river_dunes` (unified script replacing `compile_results.py`). Create `score.py` for `compensation_sensitivity`. Create `run_all.py` at the repo root. Verify that `python run_all.py` reproduces all existing `results_table.json` files with no meaningful differences.

**Files touched:**
- `run_all.py`
- `benchmarks/river_dunes/scoring/score.py` (new)
- `benchmarks/shoreline/scoring/score.py` (refactored)
- `benchmarks/shoreline/scoring/metrics.py` (thin re-export)
- `benchmarks/compensation/scoring/score.py` (refactored: validation datasets only)
- `benchmarks/compensation/scoring/metrics.py` (thin re-export)
- `benchmarks/compensation_sensitivity/scoring/score.py` (new)
- `benchmarks/compensation_sensitivity/scoring/metrics.py` (re-export)
- `benchmarks/compensation_sensitivity/results_table.json` (created as empty array)

### ✅ Phase 4 — CI update *(done)*
*score.yml simplified; compile job also runs build_site.py*

Updated `.github/workflows/score.yml` as described in §7:
- **`on:`** — added `push` trigger on `main` for `submissions/**`, `benchmark.yaml`, `build_site.py`, `templates/**`, `assets/**`
- **`score` job** — fixed detection: `grep '^benchmarks/.*/submissions/'` + `cut -d/ -f2` extracts slug; calls `python run_all.py "$slug"` per affected benchmark; `if-no-files-found: ignore` on the artifact upload
- **`compile` job** — now calls `python run_all.py` then `python build_site.py`; stages `results_table.json` **and** generated `index.html` files; commit message updated
- **`jinja2`** added to both jobs' `pip install` line

Also fixed a Phase 3 oversight: `benchmarks/shoreline/scoring/score.py` was not writing `results_table.json` and would exit with an error when the gitignored raster is absent, causing `run_all.py` to fail in CI. The script was extended to:
1. Compile `results_table.json` from existing `score_output.json` files after scoring (like the other benchmarks do)
2. Demote the raster check to a `WARNING` in all-submissions mode so the compile job succeeds even without the raster

**Files touched:**
- `.github/workflows/score.yml`
- `benchmarks/shoreline/scoring/score.py` (Phase 3 fix: compilation + graceful raster handling)

### ✅ Phase 5 — Python build script skeleton *(done)*
*New `build_site.py` + `templates/`; simplified index (benchmark cards, no inline charts)*

Wrote `build_site.py` and Jinja2 HTML templates that produce valid per-benchmark `index.html` files and a regenerated root `index.html`. The index drops the old per-benchmark chart sections entirely and replaces them with auto-generated benchmark cards driven by `benchmark.yaml` data. The root index is now fully static (no JS). Added `tagline`, `domain`, `status` to `BenchmarkConfig`.

**Files touched:**
- `scoring/benchmark.py` — added `tagline`, `domain`, `status` to `BenchmarkConfig` + `load_config()`
- `build_site.py` — CLI: `python build_site.py [slug] [--no-index]`
- `templates/benchmark_page.html` — skeleton with `window.BENCHMARK_CONFIG` embedded, `#benchmark-root` placeholder
- `templates/index.html` — static template: hero, stat cards (counts at build time), benchmark card grid, principles
- `assets/benchmark-dashboard.css` — Phase 5 block appended: `.benchmark-cards`, `.benchmark-card`, `.card-*`, `.tag`/`.tag--*`, `.page-hero`, `.breadcrumb`, `.page-title`, `.page-tagline`, `.meta-tags`, `.meta-tag`
- `benchmarks/*/index.html` (4 generated files)
- `index.html` (regenerated — 135 lines, fully static, no JS)

**Notes for Phase 6:**

- `window.BENCHMARK_CONFIG` is already embedded in every benchmark page as inline JSON. It contains the full parsed `benchmark.yaml` (name, slug, tagline, domain, status, reference_type, data_type, scoring metrics, datasets, website config). `Path` objects are excluded; the dict is JSON-safe.
- The page fetches `results_table.json` relative to its own URL — no path gymnastics needed. The file already exists next to each `index.html`.
- The JS entry point is `<div id="benchmark-root">` in `templates/benchmark_page.html`. Phase 6 populates this div.
- The script tag at the bottom of `benchmark_page.html` has a placeholder comment: `<!-- benchmark-page.js will be added in Phase 6 -->` — just replace it with `<script src="../../assets/benchmark-page.js" defer></script>`.
- **Shoreline map canvas:** The existing `benchmark-dashboard.js` has the full GeoTIFF + proj4 canvas rendering logic. It should be ported/adapted into `benchmark-page.js` rather than re-written from scratch. The map config lives in `window.BENCHMARK_CONFIG.website.map_panel` (`raster`, `land_color`, `water_color`).
- **Chart type dispatch table** (reference_type × data_type):
  - `intercomparison` × `identification` → horizontal boxplot via `@sgratzl/chartjs-chart-boxplot` (`boxplot` type, `indexAxis: 'y'`), metric toggled by segmented control; no custom plugin needed
  - `reference` × `map` → horizontal bar + map canvas panel, metric toggled
  - `validation` × `value` → horizontal bar + chartjs-plugin-annotation reference-value line, dataset toggled
  - `intercomparison` × `value` → horizontal bar, no reference marker, dataset toggled
- **`results_table.json` field shapes** differ by benchmark type — the JS needs to know how to extract a scalar from each record:
  - `river_dunes` (identification): boxplot data object built as `{ min: record[metric].min, q1: record[metric].p25, median: record[metric].median, q3: record[metric].p75, max: record[metric].max }` — the five stats are stored as top-level keys on the metric sub-object (see Phase 5a)
  - `shoreline` (map): `record.vs_references_summary[metric].mean` (or fall back to single-ref `record.vs_references[refStem][metric]`); `runtime_seconds` is a top-level field
  - `compensation` (validation · value): `record[dataset][field]` e.g. `record.compensational_stacking.abs_error`; reference value at `record[dataset].kappa_reference`
  - `compensation_sensitivity` (intercomparison · value): `record[dataset].kappa_submitted` / `record[dataset].Tc_submitted`
- **Method label:** use `record.method_name || record.author_name || record.tool_name` (first non-null).
- **CSS:** the existing `benchmark-dashboard.css` has `.panel`, `.panel-header`, `.segmented`, `.chart-wrap`, `.chart-empty`, `.method-row`, `.method-name`, `.method-meta`, `.benchmark-note`, `.map-stage`, `.map-canvas`, `.map-legend`, etc. — reuse these in the benchmark page layout before adding new rules.
- **Chart.js CDN pins** (from plan §6): `chart.umd.min.js@4.4.1` and `chartjs-plugin-annotation@3.0.1` from cdnjs.cloudflare.com; `@sgratzl/chartjs-chart-boxplot@4.4.4` from cdn.jsdelivr.net (identification benchmarks only).

### Phase 5a ✅ — Boxplot stat additions for `river_dunes`
*Extend identification scoring to emit the five stats the boxplot plugin needs*

The `@sgratzl/chartjs-chart-boxplot` plugin expects `{ min, q1, median, q3, max }` per data point. The current `distribution_stats()` function computes `[mean, median, std, p25, p75]` — `min` and `max` are missing. This phase adds them to the shared library and propagates the change through the `river_dunes` config and results table.

**Changes:**

1. **`scoring/metrics/identification_metrics.py`** — add `"min"` and `"max"` to the default stats list in `distribution_stats()`. The function already uses `pd.Series.describe()` / `np.percentile`, so `series.min()` and `series.max()` are trivial additions. Keep existing stats so no downstream breakage.

2. **`benchmarks/river_dunes/benchmark.yaml`** — extend `scoring.stats` to include `min` and `max`:
   ```yaml
   scoring:
     stats: [min, mean, median, std, p25, p75, max]
   ```

3. **`benchmarks/river_dunes/results_table.json`** — regenerate by running `python run_all.py river_dunes`. Each metric sub-object will now include `min` and `max` keys alongside the existing ones.

4. **`tests/test_metrics.py`** — verify that `distribution_stats()` output includes `min` and `max` with correct values.

**No other benchmarks are affected.** `identification_metrics.py` is only called by `river_dunes/scoring/score.py`.

**Files touched:**
- `scoring/metrics/identification_metrics.py`
- `benchmarks/river_dunes/benchmark.yaml`
- `benchmarks/river_dunes/results_table.json` (regenerated)
- `tests/test_metrics.py`

### Phase 6 ✅ — Chart.js benchmark page template
*The main visual work: generic benchmark page JS + completed layout*

Write `assets/benchmark-page.js` and complete `templates/benchmark_page.html`. The JS reads `window.BENCHMARK_CONFIG` (embedded by `build_site.py`) and fetches `results_table.json` (relative URL), then renders Chart.js charts appropriate to the taxonomy. All four existing benchmarks must render correctly. Use the existing color palette (`#257180` teal, `#cb6040` orange).

See the **Notes for Phase 6** block at the end of Phase 5 above for all implementation details: config shape, results_table field extraction patterns, chart dispatch table, method label logic, CSS classes to reuse, CDN pins, and shoreline map canvas porting notes.

**Files touched:**
- `assets/benchmark-page.js`
- `templates/benchmark_page.html` (complete)
- `assets/benchmark-dashboard.css` (extend with benchmark-page panel styles)

### Phase 7 — Index page polish + CONTRIBUTING.md
*Complete the index template visually; remove dead JS; update contributor docs*

Phase 5 already produced a working static index with benchmark cards. Phase 7 completes the visual design: finalize card styling, add any domain-color accents or domain icons, verify mobile layout. Remove `benchmark-dashboard.js` entirely (the index is now static). Update `CONTRIBUTING.md` to explain that the site regenerates on merge to main.

**Files touched:**
- `templates/index.html` (visual polish)
- `assets/benchmark-dashboard.js` (delete or reduce to empty stub)
- `assets/benchmark-dashboard.css` (any index-specific additions)
- `CONTRIBUTING.md`

---

## Appendix: Design decisions record

| Decision | Rationale |
|---|---|
| No `mixed` reference type | Forces a clean taxonomy. The compensation benchmark's two purposes (validation vs. intercomparison) are genuinely different benchmarks. Eliminating `mixed` removes all branching from scoring code and website JS. |
| One submission per benchmark | Simplest possible mental model for contributors. Reduces scoring script complexity. The compensation split makes this feasible. |
| Python build script over Jekyll | Fits the repo's "minimal infrastructure" principle. No Ruby dependency. No plugin whitelist. The pipeline (benchmark.yaml + results_table.json → HTML) is trivial Python. Generated files committed to main like results_table.json already is — no Pages settings change required. |
| Generated HTML committed to git | Matches existing pattern for `results_table.json`. Keeps Pages serving from branch with no configuration change. Generated files are clearly marked in the directory structure and can be audited in PRs. |
| Fix CI grep to `submissions/` scope | Prevents the score job from triggering on README edits, benchmark.yaml changes, or results_table.json updates — all of which currently would cause it to re-run scoring unnecessarily. |
| `compensation_sensitivity` data lives in `compensation/data/` | Avoids duplicating large-ish CSV files. The sensitivity benchmark's score.py and benchmark.yaml reference the sibling directory by relative path. |
| Boxplot plugin over floating bar + custom median plugin for `river_dunes` | `@sgratzl/chartjs-chart-boxplot` renders the full 5-number summary (min, p25, median, p75, max) natively — no custom Chart.js plugin code to write or maintain. Shows more information than IQR-only floating bars. The only cost is a conditional extra `<script>` tag on identification benchmark pages and adding `min`/`max` to `distribution_stats()`. |
