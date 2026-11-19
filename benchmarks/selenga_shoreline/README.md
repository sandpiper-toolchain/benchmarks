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

Two metrics are reported, each computed against every reference in
`data/references.yaml`:

| Metric | Description |
|--------|-------------|
| **Mean distance error (m)** | Average nearest-neighbour distance between submitted and reference polyline point sets. Lower is better. |
| **Pixel F1** | F1 score after rasterizing both polylines onto the benchmark grid. Closer to 1.0 is better. |

Run the scorer locally (from the **repository root**):

```bash
# Score one submission:
python score.py selenga_shoreline submissions/my-method/results.geojson

# Compile all submissions → results_table.json:
python score.py selenga_shoreline --compile
```

A `score_output.json` is written next to each submission GeoJSON.
The `--output` option overrides the destination when scoring a single submission.

> **Note:** scoring requires `data/selenga_clipped.tif`, which is not committed
> to git (it is too large).  Obtain it as described in the **Input data** section
> above.  Compile mode skips scoring and aggregates any existing
> `score_output.json` files, so `results_table.json` can be regenerated without
> the raster.

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method, containing
   `results.geojson` and `metadata.yaml` (copy the metadata template from
   `submissions/example/`).
3. Open a pull request. CI will automatically score your submission against
   all reference digitizations in `data/references.yaml` and post the results
   as a build artifact.

> **Note:** Scores are reported per reference and, when multiple references
> exist, as a mean ± std across them.  References are human-produced
> expert interpretations — inter-reference spread reflects natural
> digitization uncertainty, not scoring noise.
