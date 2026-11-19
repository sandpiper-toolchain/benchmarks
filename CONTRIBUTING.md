# Contributing to sandpiper

## Adding a submission to an existing benchmark

1. **Fork** this repository and create a branch.
2. Inside the benchmark folder (e.g. `benchmarks/shoreline/`), create
   a subfolder under `submissions/` named after your method:
   ```
   submissions/your-method-name/
   ├── results.geojson   # your output shoreline (GeoJSON polyline)
   └── metadata.yaml    # see submissions/example/metadata.yaml
   ```
3. Your `results.geojson` must be a valid GeoJSON `LineString` or
   `MultiLineString` with a defined CRS (any projected CRS is fine —
   the scorer will reproject automatically).
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

## Adding a reference solution

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
- A proposed reference solution (one or more expert interpretations — how
  were they produced?)
- Why this problem is useful to the community

## Data licensing

All input datasets and reference solutions (digitizations) must be openly
licensed (CC-BY or equivalent). Please include a note in the benchmark
README about the data source and licence.

## Code style

Scoring is handled by a shared Python library under `scoring/` at the repository
root.  Metric functions live in `scoring/metrics/`; the dispatch logic lives in
`scoring/runners.py`; `score.py` at the repository root is the CLI entry point.
Dependencies are minimal: `geopandas`, `rasterio`, `scipy`, `numpy`, `shapely`,
`pyyaml`.  Avoid adding heavy ML frameworks to the scoring layer.
