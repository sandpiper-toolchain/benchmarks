#!/usr/bin/env python
"""
Aggregate all score_output.json files in a benchmark's submissions/ directory
into a single results_table.json at the benchmark root.

Usage
-----
    python benchmarks/shoreline/scoring/compile_results.py benchmarks/shoreline/

The script walks <benchmark_dir>/submissions/ looking for every
score_output.json.  For each one it reads the adjacent metadata.yaml (if
present) and merges the scoring results with the submission metadata.

The output is written to <benchmark_dir>/results_table.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def parse_args():
    p = argparse.ArgumentParser(
        description="Compile all score_output.json files into results_table.json."
    )
    p.add_argument(
        "benchmark_dir",
        help="Path to the benchmark directory (e.g. benchmarks/shoreline/).",
    )
    return p.parse_args()


def read_metadata(metadata_path: Path) -> dict:
    """
    Read a submission's metadata.yaml and return a flat dict of the fields
    we care about for the results table.  Missing fields default to None
    rather than raising an error so that incomplete metadata does not block
    the compile step.

    Parameters
    ----------
    metadata_path:
        Path to the metadata.yaml file.

    Returns
    -------
    dict with keys: method_name, tool_name, tool_version, tool_url,
    author_name, date, runtime_seconds.
    """
    defaults = {
        "method_name": None,
        "tool_name": None,
        "tool_version": None,
        "tool_url": None,
        "author_name": None,
        "date": None,
        "runtime_seconds": None,
    }

    if not metadata_path.exists():
        return defaults

    try:
        with open(metadata_path) as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: could not read {metadata_path}: {exc}", file=sys.stderr)
        return defaults

    return {
        "method_name": data.get("method_name"),
        "tool_name":    data.get("tool_name"),
        "tool_version": data.get("tool_version"),
        "tool_url":     data.get("tool_url"),
        "author_name":  data.get("author_name"),
        "date":         str(data["date"]) if data.get("date") is not None else None,
        "runtime_seconds": data.get("runtime_seconds"),
    }


def collect_records(submissions_dir: Path) -> list[dict]:
    """
    Walk submissions_dir recursively and build one record per
    score_output.json found.

    Parameters
    ----------
    submissions_dir:
        Path to the benchmark's submissions/ folder.

    Returns
    -------
    List of record dicts, each containing metadata fields plus the scoring
    results copied from score_output.json.
    """
    records = []

    # Sort for reproducible ordering in the output file
    score_files = sorted(submissions_dir.rglob("score_output.json"))

    for score_path in score_files:
        # Read the scoring results
        try:
            with open(score_path) as fh:
                score_data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING: could not read {score_path}: {exc}", file=sys.stderr)
            continue

        # Read the adjacent metadata.yaml (may not exist)
        metadata_path = score_path.parent / "metadata.yaml"
        meta = read_metadata(metadata_path)

        record = {
            **meta,
            "geojson_files": sorted(
                path.relative_to(submissions_dir.parent).as_posix()
                for path in score_path.parent.rglob("*.geojson")
            ),
            "vs_references":         score_data.get("vs_references", {}),
            "vs_references_summary": score_data.get("vs_references_summary", {}),
        }
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

    print(f"Compiled {len(records)} submission(s) → {output_path}")


if __name__ == "__main__":
    main()
