#!/usr/bin/env python
"""
Score a submitted compensation-sensitivity result (intercomparison datasets).

Two datasets with no universal theoretical reference are reported as-is for
cross-submission comparison:
    compensational_stacking_meanX    (mean avulsion period = 15 events)
    compensational_stacking_mean2X   (mean avulsion period = 30 events)

Usage
-----
    # Score one submission:
    python score.py submissions/my-method/results.yaml [--output score_output.json]

    # Score all submissions under ../submissions/ (skipping 'example'):
    python score.py

The script exits with code 0 on success and prints a JSON summary to stdout.
For a single submission, --output sets the destination; default is
score_output.json next to the submission.  In all-submissions mode, each
result is written next to its results.yaml.

Expected directory layout (relative to this script):
    ../submissions/<method>/results.yaml
    ../data/<dataset>.csv  -- benchmark input data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

BENCHMARK_DIR = HERE.parent
SUBMISSIONS_DIR = BENCHMARK_DIR / "submissions"

from scoring.benchmark import load_config
from scoring.compile import compile_results_table, discover_submissions, load_yaml
from scoring.output import write_score_output


def parse_args():
    p = argparse.ArgumentParser(
        description="Score a compensation-sensitivity submission."
    )
    p.add_argument(
        "submission",
        nargs="?",
        help="Path to submitted results.yaml (omit to score all submissions).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Where to write the JSON result (default: score_output.json next to submission).",
    )
    return p.parse_args()


def validate_submission(data: dict, path: Path, datasets: dict) -> None:
    """Confirm all dataset keys are present with both kappa and Tc fields."""
    for dataset in datasets:
        if dataset not in data:
            print(
                f"ERROR: dataset key '{dataset}' missing from {path}",
                file=sys.stderr,
            )
            sys.exit(1)
        for field in ("kappa", "Tc"):
            if field not in data[dataset]:
                print(
                    f"ERROR: field '{field}' missing under '{dataset}' in {path}",
                    file=sys.stderr,
                )
                sys.exit(1)


def score_submission(submission_data: dict, datasets: dict) -> dict:
    """
    Collect the submitted κ and T_c for all intercomparison datasets.

    Parameters
    ----------
    submission_data:
        Parsed results.yaml dict.
    datasets:
        The ``datasets`` dict from BenchmarkConfig.

    Returns
    -------
    dict
        Per-dataset submitted values keyed by dataset name.
    """
    reported = {}
    for ds_name in datasets:
        ds = submission_data[ds_name]
        reported[ds_name] = {
            "kappa_submitted": float(ds["kappa"]),
            "Tc_submitted":    float(ds["Tc"]),
        }
    return reported


def _build_sensitivity_record(score_data: dict, _: Path) -> dict:
    """Extract per-dataset reported values from a score_output.json dict."""
    return dict(score_data.get("datasets", {}))


def main():
    args = parse_args()
    config = load_config(BENCHMARK_DIR)
    datasets = config.datasets  # dict of dataset_name → {label, reported_fields, ...}

    # Verify the input data directory is accessible (informational only).
    data_dir = (BENCHMARK_DIR / config.scoring["data_dir"]).resolve()
    if not data_dir.is_dir():
        print(
            f"WARNING: input data directory not found: {data_dir}\n"
            f"  Expected at: {data_dir}\n"
            f"  Submission values will still be recorded.",
            file=sys.stderr,
        )

    if args.submission is None:
        if args.output:
            print(
                "ERROR: --output can only be used when scoring one submission.",
                file=sys.stderr,
            )
            sys.exit(2)

        submissions = discover_submissions(SUBMISSIONS_DIR, "results.yaml")

        if not submissions:
            print(
                f"No results.yaml files found under {SUBMISSIONS_DIR}",
                file=sys.stderr,
            )
            sys.exit(0)

    else:
        submissions = [Path(args.submission).resolve()]
        if not submissions[0].is_file():
            print(
                f"ERROR: submission file not found: {submissions[0]}",
                file=sys.stderr,
            )
            sys.exit(1)

    all_results = []
    for submission_path in submissions:
        print(f"Scoring: {submission_path.relative_to(SUBMISSIONS_DIR.parent)}")
        print(f"  datasets: {', '.join(datasets)}")
        print()

        try:
            submission_data = load_yaml(submission_path)
        except Exception as exc:
            print(f"ERROR: failed to load {submission_path}: {exc}", file=sys.stderr)
            sys.exit(1)

        validate_submission(submission_data, submission_path, datasets)
        reported = score_submission(submission_data, datasets)

        results = {
            "submission": str(submission_path),
            "datasets": reported,
        }

        out_path = Path(args.output) if args.output else None
        written = write_score_output(results, submission_path, out_path)
        all_results.append(results)
        print(f"  Results written to: {written}")
        print()

    # Compile results_table.json when running in all-submissions mode.
    if args.submission is None:
        tbl_path = compile_results_table(
            submissions, BENCHMARK_DIR, _build_sensitivity_record
        )
        print(f"Compiled {len(submissions)} submission(s) → {tbl_path}")

    output = all_results if args.submission is None else all_results[0]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
