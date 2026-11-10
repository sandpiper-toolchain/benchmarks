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

## Repo structure

Each benchmark lives in its own top-level folder inside the repo.
The layout is consistent across benchmarks:

```
benchmarks/                      ← this git repo
├── CLAUDE.md                    ← you are here
├── README.md                    ← table of all benchmarks
├── CONTRIBUTING.md
├── brainstorm.md                ← ideas for future benchmarks
├── .github/
│   └── workflows/
│       └── score.yml            ← CI workflow (runs on every PR touching submissions/)
└── <benchmark-name>/            ← one folder per benchmark
    ├── README.md                ← problem statement, data description, results table
    ├── data/                    ← input data and reference solution
    │   ├── <input>              ← benchmark input (raster, image, CSV, …); large files gitignored
    │   └── <reference>         ← ground-truth output used for scoring
    ├── scoring/
    │   ├── metrics.py           ← scoring functions (importable)
    │   └── score.py             ← CLI: python score.py <submission> [--output results.json]
    └── submissions/
        ├── example/
        │   └── metadata.yaml    ← template for contributors
        └── <method-name>/
            ├── <result-file>    ← the submission (GeoJSON, CSV, raster, …)
            └── metadata.yaml
```

**Data files:** Large binary inputs (GeoTIFFs, etc.) are gitignored (`*.tif`, `*.tiff` in
`.gitignore`) and distributed separately. Each benchmark README documents where to obtain them.

## Scoring conventions

Scoring scripts follow a consistent interface:

```
python <benchmark>/scoring/score.py <submission> [--output results.json]
```

- Exits with code 0 on success; prints a JSON summary to stdout.
- Writes the same JSON to `--output` (default: `score_output.json` next to the submission).
- All metrics are computed against the reference solution in `<benchmark>/data/`.

Common metric patterns across benchmarks:

| Output type | Typical metrics |
|---|---|
| Polyline GeoJSON | Mean distance error, pixel F1, shape/roughness agreement |
| Polygon GeoJSON | IoU, area error |
| Point GeoJSON | Mean distance error, detection F1 |
| CSV of measurements | MAE / RMSE per column |
| Binary raster mask | Pixel F1, IoU |

## CI workflow

- Triggers on PRs that touch `*/submissions/**`
- Detects changed result files via `git diff`
- Runs `score.py` for each changed submission; `benchmark_dir` is the first path segment
- Uploads `score_output.json` as a build artifact

## Future benchmarks

See `brainstorm.md` for a full list of ideas across deltas, rivers, barrier islands,
aeolian dunes, alluvial fans, riverbed dunes, stratigraphy, and laboratory experiments.
Priority candidates: Colville delta channel network (RivGraph), dune crestline extraction,
single-thread river centerline, compensation statistic (κ), lab RGB → channel mask.

## Key people

- **Andrew Moodie** — project lead, geomorphology researcher, also develops sandplover
  (a separate Python package for delta analysis; sibling repo in the sandpiper project)
