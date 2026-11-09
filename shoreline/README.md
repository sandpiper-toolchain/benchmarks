# Shoreline Mapping Benchmark -- Selenga River Delta 

## Problem

Given a binary land/water mask of the Selenga River Delta (Lake Baikal,
Russia), extract the delta shoreline as a GeoJSON polyline.

## Input data

| File | Description |
|------|-------------|
| `data/selenga_clipped.tif` | Single-band binary GeoTIFF. Pixel value `1` = land, `0` = water. |
| `data/reference.geojson` | Hand-mapped reference shoreline (GeoJSON polyline, same CRS as mask). |

The mask is derived from a Landsat scene. The reference shoreline was
digitised manually against the same imagery.

## Scoring

Three metrics are reported:

| Metric | Description |
|--------|-------------|
| **Mean distance error (m)** | Average nearest-neighbour distance between submitted and reference polyline point sets. Lower is better. |
| **Pixel F1** | F1 score after rasterizing both polylines onto the benchmark grid. Closer to 1.0 is better. |
| **Roughness agreement (%)** | Relative % difference in area-normalised roughness `R = L / sqrt(A_land)`. Lower is better. |

Run the scorer locally:

```bash
python scoring/score.py submissions/my-method/result.geojson
```

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method:
   ```
   submissions/my-method/
   ├── result.geojson    # your extracted shoreline (polyline, any projected CRS)
   └── metadata.yaml     # tool name, version, author — copy from submissions/example/
   ```
3. Open a pull request. CI will automatically score your submission and post
   the results as a build artifact.

## Results

> Reference shoreline not yet committed — results table will be populated
> once `data/reference.geojson` is available.

| Method | Mean dist. error (m) | Pixel F1 | Roughness diff (%) |
|--------|----------------------|----------|--------------------|
| *(none yet)* | — | — | — |
