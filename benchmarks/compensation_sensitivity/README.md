# Compensation Index — Sensitivity Benchmark

## Overview

This benchmark is a companion to the [`compensation`](../compensation/) benchmark.
It uses the same synthetic stratigraphic model but with longer mean avulsion periods
(T_A = 15 and T_A = 30 depositional events), where no universal theoretical reference
value for κ exists.

Because there is no ground truth, this is an **intercomparison** benchmark: submitted
κ and T_c values are displayed side-by-side across methods to reveal how different
tools respond as the avulsion period scales up.

Submissions compare the best-fit κ for the sub-compensation timescale, and the compensation timescale T_c. In addition to required files and complete metadata, submissions may optionally include the script used for fitting. 


## Relationship to `compensation`

| Benchmark | Datasets | Reference type | Scored against |
|-----------|----------|----------------|----------------|
| `compensation` | `compensational_stacking` (T_A = 1), `random_stacking` (T_A = 1) | validation | Theoretical κ reference values |
| `compensation_sensitivity` | `compensational_stacking_meanX` (T_A = 15), `compensational_stacking_mean2X` (T_A = 30) | intercomparison | Each other (no ground truth) |

## Input data

The input CSV datasets are derived from the
[DeltaRCM Triangle Stacking Model](https://github.com/DeltaRCM/triangle_stacking_model/tree/main).
The CSV data and benchmark images are retained in this repository. These CSV
files live in this benchmark's [`data/`](data/) directory:

| File | Avulsion period | Description |
|------|----------------|-------------|
| `data/compensational_stacking_meanX.csv` | T_A = 15 events | Compensational stacking, medium avulsion period |
| `data/compensational_stacking_mean2X.csv` | T_A = 30 events | Compensational stacking, long avulsion period |

See the [`compensation` README](../compensation/README.md) for details on the
CSV format and model description.

## Submission format

Create a YAML file named `results.yaml` with two top-level keys:

```yaml
compensational_stacking_meanX:
  kappa: <float>
  Tc: <float>

compensational_stacking_mean2X:
  kappa: <float>
  Tc: <float>
```

- `kappa` is dimensionless.
- `Tc` is in units of depositional events.

## How to submit

1. Fork this repository.
2. Create a folder under `submissions/` named after your method, containing
   `results.yaml` and `metadata.yaml` (copy the metadata template from
   `submissions/example/`).
3. Open a pull request. CI will post your submitted values as a build artifact.
