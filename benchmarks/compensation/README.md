# Compensation Index Benchmark — Synthetic Stratigraphic Sequences

## Problem

Given a time series of surface elevation profiles across a synthetic sedimentary basin,
compute the **compensation index κ** and **compensation timescale T_c**.

## Background

Compensational stacking describes the tendency of depositional systems to fill
topographic lows over time, producing more uniform stratigraphic architecture
than would result from purely random channel placement.  The compensation
index κ and compensation timescale T_c quantify this behavior from a
stratigraphic record.

The standard approach (Straub et al., 2009) is to track how the standard deviation
of thickness increments, σ_ss(T), scales with the time elapsed (T) between 
depositional surfaces. On a log-log plot of σ vs. T, two power-law regimes are 
distinguished:

- **Short timescales (T ≪ T_c):** σ ∝ T^κ — the system is influenced by autogenics.
- **Long timescales (T ≫ T_c):** σ ∝ T^κ — the system is influenced only by allogenics.

**κ** is the slope of the best-fit line through either timescale regime in
log-log space. It is interpreted as follows:

| κ value | Stacking behaviour |
|---------|--------------------|
| κ = 0.5 | Random (Poissonian) stacking |
| 0.5 < κ < 1 | Compensational stacking (κ ≈ 0.75 is typical) |
| κ < 0.5 | Anticompensational stacking |

**T_c** (units: number of depositional events) is the compensation timescale —
the transition point between the two regimes, found at the intersection of the
two fitted lines in log-log space.  Small T_c indicates that compensation
establishes itself quickly; large T_c indicates a weak or slow compensational
tendency.

**Key references:**

- Straub, K. M., Paola, C., Mohrig, D., Wolinsky, M. A., & George, T. (2009).
  Compensational stacking of channelized sedimentary deposits.
  *Journal of Sedimentary Research*, 79(9), 673–688.
  <https://doi.org/10.2110/jsr.2009.070>
- Wang, Y., Straub, K. M., & Hajek, E. A. (2011). Scale-dependent compensational
  stacking: An estimate of autogenic time scales in channelized sedimentary
  deposits. *Geology*, 39(9), 811–814.
  <https://doi.org/10.1130/G32068.1>
- Straub, K. M., and Y. Wang (2013), Influence of water and sediment supply on the
  long-term evolution of alluvial fans and deltas: Statistical characterization of
  basin-filling sedimentation patterns, J. Geophys. Res. Earth Surf., 118, 
  1602–1616, doi:10.1002/jgrf.20095.


## Input data

The input CSV datasets are derived from the
[DeltaRCM Triangle Stacking Model](https://github.com/DeltaRCM/triangle_stacking_model/tree/main).
The CSV data and benchmark images are included in this repository; the model
script is not. The datasets use the same model parameters and differ in
avulsion strategy and mean avulsion period. The stacking model is based on the
description in Wang et al., 2011:

> We model basin filling with discrete triangular elements that are meant to represent channel or lobe deposits. During each time step one element is deposited in the basin while the subsidence is set to balance mean basin aggradation. An approximation of the avulsion process is modeled by placing channel elements with the following rules. At every nth time step during basin filling, the active channel relocates to the absolute topographic low in the model domain. For all other time steps deposition follows a random walk with elements moving one channel width left or right of the previous element.

| File | Avulsion strategy | Avulsion period | Description |
|------|------------------|------------------|-------------|
| `data/compensational_stacking.csv` | `'low'` — avulse to topographic minimum | 1 timestep | Compensational sequence |
| `data/random_stacking.csv` | `'random'` — avulse to a random position | 1 timestep | Random stacking sequence |
| `../compensation_sensitivity/data/compensational_stacking_meanX.csv` | `'low'` — avulse to topographic minimum | 15 timesteps | Compensational sequence |
| `../compensation_sensitivity/data/compensational_stacking_mean2X.csv` | `'low'` — avulse to topographic minimum | 30 timesteps | Compensational sequence |

This benchmark validates the two T_A = 1 datasets. The T_A = 15 and T_A = 30
datasets are used by the companion
[`compensation_sensitivity`](../compensation_sensitivity/) benchmark.

### CSV format

Each file has **2001 rows** (timesteps) and **41 columns**:

| Column | Description |
|--------|-------------|
| `timestep` | Integer index of the depositional event (0 – 1999) |
| `col_0` … `col_39` | Cumulative surface elevation at each of the 40 spatial grid points |

Rows are ordered in time (earliest first).  Each cell value is the total
accumulated elevation at that spatial position after the given timestep.
Incremental thicknesses deposited at step *t* are the row-wise differences
`elevation[t] − elevation[t−1]`.

The 40 spatial columns are dimensionless grid units (channel width ≈ 5 grid
units).  Each row represents one depositional event. 

## Submission format

Create a YAML file named `results.yaml` with one top-level key for each
T_A = 1 dataset:

```yaml
compensational_stacking:
  kappa: <float>

random_stacking:
  kappa: <float>
```

- Dataset keys must match the CSV file stems exactly
  (`compensational_stacking` and `random_stacking`).
- `kappa` is dimensionless.

## Scoring

Scoring compares submitted `kappa` values against theoretical values for the
two T_A = 1 datasets. The companion sensitivity benchmark reports κ and T_c
values for the longer avulsion periods without treating them as ground truth.
Two metrics are reported per submission:

| Metric | Description |
|--------|-------------|
| **Absolute error** | \|κ_submitted − κ_reference\| for each dataset |
| **Relative error (%)** | \|κ_submitted − κ_reference\| / κ_reference × 100 for each dataset |

Run the scorer locally:

```bash
# Score one submission:
python scoring/score.py submissions/my-method/results.yaml

# Score all submissions under submissions/:
python scoring/score.py
```

A `score_output.json` is written next to each `results.yaml`.

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method, containing
   `results.yaml` and `metadata.yaml` (copy the metadata template from
   `submissions/sandplover/`).
3. Open a pull request.  CI will automatically score your submission against the
   reference values and post the results as a build artifact.
