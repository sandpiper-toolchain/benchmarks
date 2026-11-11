#!/usr/bin/env python
"""
Compile all submissions into a single results_table.json at the benchmark root.

This is a pure **intercomparison** benchmark — there is no ground-truth reference.
The script reads each submission's result.csv, computes distribution-level summary
statistics for the three geometry columns, merges those with the submission's
metadata.yaml, and writes the aggregated table.

Usage
-----
    python benchmarks/river_dunes/scoring/compile_results.py benchmarks/river_dunes/

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

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REQUIRED_COLS = {"height_m", "length_m", "depth_m"}


def parse_args():
    p = argparse.ArgumentParser(
        description="Compile all Paraná River bedform submissions into results_table.json."
    )
    p.add_argument(
        "benchmark_dir",
        help="Path to the benchmark directory (e.g. benchmarks/river_dunes/).",
    )
    return p.parse_args()


def read_metadata(metadata_path: Path) -> dict:
    """
    Read a submission's metadata.yaml.  Missing fields default to None.
    """
    defaults = {
        "method_name":        None,
        "method_description": None,
        "method_type":        None,
        "tool_name":          None,
        "tool_version":       None,
        "tool_url":           None,
        "author_name":        None,
        "author_orcid":       None,
        "preferred_citation": None,
        "date":               None,
        "notes":              None,
    }

    if not metadata_path.exists():
        return defaults

    try:
        with open(metadata_path) as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not read {metadata_path}: {exc}", file=sys.stderr)
        return defaults

    result = dict(defaults)
    for key in defaults:
        val = data.get(key)
        if val is not None:
            result[key] = str(val) if key == "date" else val
    return result


def _distribution_stats(series: pd.Series) -> dict:
    """
    Return a dict of summary statistics for a numeric Series.
    """
    arr = series.dropna().to_numpy(dtype=float)
    if len(arr) == 0:
        return {"mean": None, "median": None, "std": None, "p25": None, "p75": None}
    return {
        "mean":   round(float(np.mean(arr)),              4),
        "median": round(float(np.median(arr)),            4),
        "std":    round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
        "p25":    round(float(np.percentile(arr, 25)),    4),
        "p75":    round(float(np.percentile(arr, 75)),    4),
    }


def summarise_csv(csv_path: Path) -> dict | None:
    """
    Load a result.csv and compute per-column distribution statistics.

    Returns None on error.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not read {csv_path}: {exc}", file=sys.stderr)
        return None

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        print(
            f"  WARNING: {csv_path} is missing required columns {missing} — skipping.",
            file=sys.stderr,
        )
        return None

    return {
        "n_bedforms": int(len(df)),
        "height_m":   _distribution_stats(df["height_m"]),
        "length_m":   _distribution_stats(df["length_m"]),
        "depth_m":    _distribution_stats(df["depth_m"]),
    }


def collect_records(submissions_dir: Path) -> list[dict]:
    """
    Walk submissions_dir recursively, build one record per result.csv found.
    """
    records = []

    csv_files = sorted(submissions_dir.rglob("result.csv"))

    for csv_path in csv_files:
        print(f"  processing: {csv_path.relative_to(submissions_dir.parent)}")

        stats = summarise_csv(csv_path)
        if stats is None:
            continue

        metadata_path = csv_path.parent / "metadata.yaml"
        meta = read_metadata(metadata_path)

        record = {**meta, **stats}
        records.append(record)

    return records


def main():
    args = parse_args()
    benchmark_dir = Path(args.benchmark_dir).resolve()

    if not benchmark_dir.is_dir():
        print(f"ERROR: benchmark directory not found: {benchmark_dir}", file=sys.stderr)
        sys.exit(1)

    submissions_dir = benchmark_dir / "submissions"
    if not submissions_dir.is_dir():
        print(f"ERROR: submissions/ directory not found: {submissions_dir}", file=sys.stderr)
        sys.exit(1)

    records = collect_records(submissions_dir)

    output_path = benchmark_dir / "results_table.json"
    output_path.write_text(json.dumps(records, indent=2))

    print(f"\nCompiled {len(records)} submission(s) → {output_path}")


if __name__ == "__main__":
    main()
