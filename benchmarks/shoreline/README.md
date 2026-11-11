# Shoreline Mapping Benchmark -- Selenga River Delta 

## Problem

Given a binary land/water mask of the Selenga River Delta (Lake Baikal,
Russia), extract the delta shoreline as a GeoJSON polyline.

## Input data

| File | Description |
|------|-------------|
| `data/selenga_clipped.tif` | Single-band binary GeoTIFF. Pixel value `1` = water, `0` = land. |
| `data/references.yaml` / `data/ref_*.geojson` | Reference shoreline(s); see `references.yaml` for provenance. |

The mask is derived from a Landsat scene. Reference shorelines are
hand-digitised against the same imagery by one or more contributors.
They represent expert interpretations, not absolute ground truth — small
differences between references reflect genuine uncertainty in shoreline
placement.

## Scoring

Three metrics are reported, each computed against every reference in
`data/references.yaml`:

| Metric | Description |
|--------|-------------|
| **Mean distance error (m)** | Average nearest-neighbour distance between submitted and reference polyline point sets. Lower is better. |
| **Pixel F1** | F1 score after rasterizing both polylines onto the benchmark grid. Closer to 1.0 is better. |
| **Roughness agreement (%)** | Relative % difference in area-normalised roughness `R = L / sqrt(A_land)`. Lower is better. |

Run the scorer locally:

```bash
# Score one submission:
python scoring/score.py submissions/my-method/result.geojson

# Score all GeoJSON files under submissions/ (excluding the example template):
python scoring/score.py
```

In all-submissions mode, a `score_output.json` is written next to each GeoJSON.
The `--output` option is only available when scoring a single submission.

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method:
   ```
   submissions/my-method/
   ├── result.geojson    # your extracted shoreline (polyline, any projected CRS)
   └── metadata.yaml     # tool name, version, author — copy from submissions/example/
   ```
3. Open a pull request. CI will automatically score your submission against
   all reference digitizations in `data/references.yaml` and post the results
   as a build artifact.

> **Note:** Scores are reported per reference and, when multiple references
> exist, as a mean ± std across them.  References are human-produced
> expert interpretations — inter-reference spread reflects natural
> digitization uncertainty, not scoring noise.

## Results

> Reference shorelines not yet committed — results table will be populated
> once `data/ref_*.geojson` files are available.

| Method | MDE vs. refs (m) | Pixel F1 vs. refs | Roughness diff (%) | Date |
|--------|------------------|-------------------|--------------------|------|
| *(none yet)* | — | — | — | — |

*±  values indicate mean ± std across multiple references.*
