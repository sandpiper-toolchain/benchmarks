# Contributing to sandpiper

## Adding a submission to an existing benchmark

1. **Fork** this repository and create a branch.
2. Inside the benchmark folder (e.g. `shoreline/`), create
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
5. Open a pull request. CI will run the scorer and post results as a
   build artifact.

## Proposing a new benchmark

Open an issue describing:
- The geomorphic problem (shoreline mapping, channel width, etc.)
- The input data you can provide and its licence
- A proposed reference solution (how was it produced?)
- Why this problem is useful to the community

## Data licensing

All input datasets and reference solutions must be openly licensed (CC-BY or
equivalent). Please include a note in the benchmark README about the data
source and licence.

## Code style

Scoring scripts are plain Python with minimal dependencies:
`geopandas`, `rasterio`, `scipy`, `numpy`, `shapely`.
Avoid adding heavy ML frameworks to the scoring layer.
