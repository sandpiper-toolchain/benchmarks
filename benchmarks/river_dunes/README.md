# River Bedform Geometry Benchmark — Paraná River

## Problem

Given a set of 1-D bathymetric bed-elevation profiles from the Paraná River,
detect individual bedforms in each profile and extract their key geometric
properties:

| Property | Symbol | Unit |
|----------|--------|------|
| Bedform height | *H* | m |
| Bedform length | *L* | m |
| Bedform depth | *d* | m |

Submissions are a single CSV file — one row per detected bedform, across all
370 profiles.

**This benchmark is an adaptation of the exhaustive testing in a 2024 peer-reviewed study.**
The study should be referenced and cited for complete information and proper attribution.
> Scheiber, L., Zomer, J., Wang, L., Cisneros, J., Gutierrez, R. R., & Lefebvre, A. (2024). Automated bedform identification—A meta-analysis of current methods and the heterogeneity of their outputs. JGR: Earth Surface. https://doi.org/10.1029/2023JF007607  

## Why intercomparison, not scoring

There is no authoritative ground-truth delineation for this dataset.  Expert
analysts differ substantially in which bedforms they identify and in the
geometric measurements they assign to each.  The goal of this benchmark is
therefore **not** to rank methods against a reference, but to place any new
tool or workflow in context alongside documented methods from the literature.
Comparing the distributions of *H*, *L*, and *d* — and the total number of
detected bedforms — reveals method-specific biases and sensitivities that
would otherwise be invisible.

## Input data

| File | Description |
|------|-------------|
| `data/Parana-370BFPs_Format-NT2D/ParanaBFP-<N>.txt` | 370 bed-elevation profiles (NT2D format; see below). |

### Data provenance

The profiles were collected from the Paraná River.
The original publication for the data is Parsons et al., 2005.

The data are distributed with the **Bedforms-ATM** software package:

> Bedforms-ATM. Available at: https://sourceforge.net/projects/bedforms-atm/

### NT2D file format

Each `ParanaBFP-<N>.txt` file contains a single profile in NT2D format:

```
<profile_index>
<point_index>  <x_nominal_m>  <x_precise_m>  <z_m>
<point_index>  <x_nominal_m>  <x_precise_m>  <z_m>
...
```

- Line 1 — the integer profile number (matches `<N>` in the filename).
- Lines 2 onward — tab-separated: sequential point index, nominal downstream
  distance (m), precise downstream distance (m), and bed elevation (m,
  negative downward).

## Submission format

A single CSV file named `result.csv` with one row per detected bedform:

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `profile_id` | int | No | Profile number (1–370; matches `ParanaBFP-<N>.txt`). |
| `height_m` | float | Yes | Bedform height *H* (crest elevation minus trough elevation), in metres. |
| `length_m` | float | Yes | Bedform length *L* (crest-to-crest or trough-to-trough distance), in metres. |
| `depth_m` | float | Yes | Bedform depth *d* (depth of the bedform trough below the local mean bed level), in metres. |

Rows may be in any order. Include a header row.

Example (with optional `profile_id`):

```
profile_id,height_m,length_m,depth_m
1,0.85,42.3,0.52
1,0.72,38.1,0.44
2,1.14,55.0,0.68
...
```

Example (without `profile_id`):

```
height_m,length_m,depth_m
0.85,42.3,0.52
0.72,38.1,0.44
1.14,55.0,0.68
...
```

## Intercomparison summary

The compile script reads every `result.csv` in `submissions/`, computes
distribution-level summary statistics for each geometry column, and writes
`results_table.json`.  Run it locally with:

```bash
python benchmarks/river_dunes/scoring/compile_results.py benchmarks/river_dunes/
```

The compiled table reports, for each submission:

| Field | Description |
|-------|-------------|
| `n_bedforms` | Total number of detected bedforms across all profiles. |
| `height_m` | `{mean, median, std, p25, p75}` of *H* across all bedforms. |
| `length_m` | `{mean, median, std, p25, p75}` of *L* across all bedforms. |
| `depth_m` | `{mean, median, std, p25, p75}` of *d* across all bedforms. |

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method:
   ```
   submissions/my-method/
   ├── result.csv      # your per-bedform geometry table
   └── metadata.yaml  # tool name, version, author — copy from an existing submission
   ```
3. Open a pull request.  CI will run `compile_results.py` to regenerate
   `results_table.json` and commit the updated table to `main`.

## Results

The table below is generated automatically from `results_table.json`.
Statistics are computed across **all** detected bedforms pooled from all profiles.

| Method | *n* bedforms | *H* mean (m) | *L* mean (m) | *d* mean (m) | Date |
|--------|-------------|-------------|-------------|-------------|------|
| Cisneros et al. — BAMBI | 5001 | — | — | — | 2020 |
| Scheiber, Lojek et al. | — | — | — | — | 2021 |
| Wang et al. — DPA | — | — | — | — | 2020 |
| Lefebvre et al. | — | — | — | — | 2021 |
| Zomer et al. | — | — | — | — | 2021 |

> **Note:** Run `python benchmarks/river_dunes/scoring/compile_results.py benchmarks/river_dunes/` to regenerate
> this table from the current submissions.

## References

Automated bedform detection and the broader context of method intercomparison
for riverbed bedform characterization:

- Bedforms-ATM software: https://sourceforge.net/projects/bedforms-atm/
- Scheiber, L., Zomer, J., Wang, L., Cisneros, J., Gutierrez, R. R., & Lefebvre, A. (2024).
  Automated bedform identification—A meta-analysis of current methods and the heterogeneity
  of their outputs. *JGR: Earth Surface*. https://doi.org/10.1029/2023JF007607
- Parsons, D. R., Best, J. L., Orfeo, O., Hardy, R. J., Kostaschuk, R., and Lane, S. N. (2005). 
  Morphology and flow fields of three-dimensional dunes, Rio Paraná, Argentina: Results from 
  simultaneous multibeam echo sounding and acoustic Doppler current profiling. *JGR: Earth Surface*.
  https://doi.org/10.1029/2004JF000231
- Cisneros, J., Best, J., van Dijk, T. et al. Dunes in the world's big rivers are characterized 
  by low-angle lee-side slopes and a complex shape (2020). Nature Geoscience 13, 
  156--162. https://doi.org/10.1038/s41561-019-0511-7
- Lefebvre, A., Herrling, G., Becker, M., Zorndt, A., Krämer, K., Winter, C. (2021). 
  Morphology of estuarine bedforms, Weser Estuary, Germany. Earth Surface Processes 
  and Landforms https://doi.org/10.1002/esp.5243
- Scheiber, L., Lojek, O., Götschenberg, A., Visscher, J., and Schlurmann, T. (2021) 
  Robust methods for the decomposition and interpretation of compound dunes applied to 
  a complex hydromorphological setting. Earth Surf. Process. Landforms, 46: 478--489. 
  https://doi.org/10.1002/esp.5040. 
- Wang, L., Yu, Q., Zhang, Y., Flemming, B. W., Wang, Y., and Gao, S. (2020) An automated 
  procedure to calculate the morphological parameters of superimposed rhythmic bedforms. 
  Earth Surf. Process. Landforms, 45: 3496--3509. https://doi.org/10.1002/esp.4983
- Zomer, J. Y., Naqshband, S., Vermeulen, B., & Hoitink, A. J. F. (2021). Rapidly 
  migrating secondary bedforms can persist on the lee of slowly migrating primary 
  river dunes. Journal of Geophysical Research: Earth Surface, 126, e2020JF005918.
  https://doi.org/10.1029/2020JF005918
