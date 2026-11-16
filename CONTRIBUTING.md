# Contributing to sandpiper

## Adding a submission to an existing benchmark

1. **Fork** this repository and create a branch.
2. Inside the benchmark folder (e.g. `benchmarks/shoreline/`), create
   a subfolder under `submissions/` named after your method:
   ```
   submissions/your-method-name/
   ├── result.geojson   # your output shoreline (GeoJSON polyline)
   └── metadata.yaml    # see submissions/example/metadata.yaml
   ```
3. Your `result.geojson` must be a valid GeoJSON `LineString` or
   `MultiLineString` with a defined CRS (any projected CRS is fine —
   the scorer will reproject automatically).
4. Fill in `metadata.yaml` — at minimum provide `method_name`,
   `tool_name`, `tool_version`, and `date`.
5. Open a pull request. CI will automatically score your submission and
   upload a `score_output.json` artifact with the results.

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

Scoring scripts are plain Python with minimal dependencies:
`geopandas`, `rasterio`, `scipy`, `numpy`, `shapely`, `pyyaml`.
Avoid adding heavy ML frameworks to the scoring layer.
