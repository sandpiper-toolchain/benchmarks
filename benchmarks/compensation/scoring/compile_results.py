#!/usr/bin/env python
"""
Compile all scored submissions into results_table.json at the benchmark root.

For the two theoretically-scored datasets (compensational_stacking,
random_stacking), kappa error metrics are taken from each submission's
score_output.json.

For the two comparative datasets (compensational_stacking_meanX,
compensational_stacking_mean2X), submitted κ and T_c values are reported
as-is.  With a single submission only the values are shown.  With multiple
submissions the records sit side-by-side in the table so they can be compared
directly.

Usage
-----
    python benchmarks/compensation/scoring/compile_results.py benchmarks/compensation/

Output
------
<benchmark_dir>/results_table.json  — JSON array, one record per submission.

Each record contains:
    method metadata fields  (from metadata.yaml)
    compensational_stacking   {kappa_reference, kappa_submitted,
                                kappa_abs_error, kappa_rel_error_pct}
    random_stacking           {kappa_reference, kappa_submitted,
                                kappa_abs_error, kappa_rel_error_pct}
    compensational_stacking_meanX    {kappa_submitted, Tc_submitted}
    compensational_stacking_mean2X   {kappa_submitted, Tc_submitted}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

THEORETICAL_DATASETS = ("compensational_stacking", "random_stacking")
COMPARATIVE_DATASETS = (
    "compensational_stacking_meanX",
    "compensational_stacking_mean2X",
)

METADATA_FIELDS = (
    "method_name",
    "method_description",
    "tool_name",
    "tool_version",
    "tool_url",
    "author_name",
    "date",
    "notes",
)


def parse_args():
    p = argparse.ArgumentParser(
        description="Compile all compensation-benchmark submissions into results_table.json."
    )
    p.add_argument(
        "benchmark_dir",
        help="Path to the benchmark directory (e.g. benchmarks/compensation/).",
    )
    return p.parse_args()


def read_metadata(metadata_path: Path) -> dict:
    defaults = {k: None for k in METADATA_FIELDS}
    if not metadata_path.exists():
        return defaults
    try:
        with open(metadata_path) as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:
        print(f"  WARNING: could not read {metadata_path}: {exc}", file=sys.stderr)
        return defaults
    result = dict(defaults)
    for key in METADATA_FIELDS:
        val = data.get(key)
        if val is not None:
            result[key] = str(val) if key == "date" else val
    return result


def read_score_output(score_path: Path) -> dict | None:
    if not score_path.exists():
        return None
    try:
        with open(score_path) as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"  WARNING: could not read {score_path}: {exc}", file=sys.stderr)
        return None


def collect_records(submissions_dir: Path) -> list[dict]:
    records = []

    for results_yaml in sorted(submissions_dir.rglob("results.yaml")):
        if results_yaml.relative_to(submissions_dir).parts[0] == "example":
            continue

        sub_dir = results_yaml.parent
        print(f"  processing: {sub_dir.relative_to(submissions_dir.parent)}")

        meta = read_metadata(sub_dir / "metadata.yaml")
        score = read_score_output(sub_dir / "score_output.json")

        record = dict(meta)

        if score is not None:
            # Theoretically-scored datasets.
            theoretical = score.get("vs_references", {}).get("theoretical", {})
            for ds in THEORETICAL_DATASETS:
                ds_data = theoretical.get(ds, {})
                record[ds] = {k: ds_data.get(k) for k in (
                    "kappa_reference",
                    "kappa_submitted",
                    "kappa_abs_error",
                    "kappa_rel_error_pct",
                )}

            # Comparative datasets — submitted values only.
            comparative = score.get("comparative_datasets", {})
            for ds in COMPARATIVE_DATASETS:
                ds_data = comparative.get(ds, {})
                record[ds] = {k: ds_data.get(k) for k in (
                    "kappa_submitted",
                    "Tc_submitted",
                )}
        else:
            for ds in THEORETICAL_DATASETS + COMPARATIVE_DATASETS:
                record[ds] = None

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
        print(f"ERROR: submissions/ not found: {submissions_dir}", file=sys.stderr)
        sys.exit(1)

    records = collect_records(submissions_dir)

    output_path = benchmark_dir / "results_table.json"
    output_path.write_text(json.dumps(records, indent=2))
    print(f"\nCompiled {len(records)} submission(s) → {output_path}")


if __name__ == "__main__":
    main()
