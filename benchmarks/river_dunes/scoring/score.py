#!/usr/bin/env python
"""
Score all submissions for the Paraná River Bedform Geometry benchmark.

This is an intercomparison/identification benchmark — there is no ground-truth
reference.  The script reads each submission's results.csv, computes
distribution-level summary statistics for the three geometry columns, merges
those with the submission's metadata.yaml, and writes the aggregated table.

Usage
-----
    python benchmarks/river_dunes/scoring/score.py

Output
------
<benchmark_dir>/results_table.json  — JSON array, one record per submission.

Each record contains:
    method metadata fields  (from metadata.yaml)
    n_bedforms              integer count of detected bedforms
    height_m                {mean, median, std, p25, p75}
    length_m                {mean, median, std, p25, p75}
    depth_m                 {mean, median, std, p25, p75}
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Shared library — repo root is 3 levels up from this file:
#   benchmarks/river_dunes/scoring/score.py  →  parents[2] = benchmarks/river_dunes
#   parents[2] is the benchmark dir; parents[3] is the repo root
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scoring.benchmark import load_config
from scoring.metadata import read_metadata
from scoring.metrics.identification_metrics import distribution_stats
from scoring.output import write_results_table

BENCHMARK_DIR = HERE.parent
SUBMISSIONS_DIR = BENCHMARK_DIR / "submissions"


def summarise_csv(csv_path: Path, columns: list[str]) -> dict | None:
    """
    Load a results.csv and compute per-column distribution statistics.

    Returns None on error.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not read {csv_path}: {exc}", file=sys.stderr)
        return None

    missing = set(columns) - set(df.columns)
    if missing:
        print(
            f"  WARNING: {csv_path} is missing required columns {missing} — skipping.",
            file=sys.stderr,
        )
        return None

    result: dict = {"n_bedforms": int(len(df))}
    for col in columns:
        result[col] = distribution_stats(df[col])
    return result


def collect_records(submissions_dir: Path, columns: list[str]) -> list[dict]:
    """Walk submissions_dir, build one record per results.csv found."""
    records = []

    for csv_path in sorted(submissions_dir.rglob("results.csv")):
        if csv_path.relative_to(submissions_dir).parts[0] == "example":
            continue

        print(f"  processing: {csv_path.relative_to(submissions_dir.parent)}")

        stats = summarise_csv(csv_path, columns)
        if stats is None:
            continue

        meta = read_metadata(csv_path.parent / "metadata.yaml")
        records.append({**meta, **stats})

    return records


def main():
    config = load_config(BENCHMARK_DIR)
    columns: list[str] = config.scoring["columns"]

    if not SUBMISSIONS_DIR.is_dir():
        print(
            f"ERROR: submissions directory not found: {SUBMISSIONS_DIR}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Scoring: {config.name}")
    print(f"  columns: {columns}")
    print()

    records = collect_records(SUBMISSIONS_DIR, columns)
    out_path = write_results_table(records, BENCHMARK_DIR)

    print(f"\nCompiled {len(records)} submission(s) → {out_path}")


if __name__ == "__main__":
    main()
