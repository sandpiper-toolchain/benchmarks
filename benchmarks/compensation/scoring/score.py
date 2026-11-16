#!/usr/bin/env python
"""
Score a submitted compensation-index result (validation datasets only).

Two datasets are scored against theoretical κ references (Straub et al., 2009):
    compensational_stacking   κ_reference = 1.0  (compensational)
    random_stacking           κ_reference = 0.50  (Poissonian / random walk)

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
from scoring.metrics.value_metrics import abs_error, rel_error_pct
from scoring.output import write_score_output


def parse_args():
    p = argparse.ArgumentParser(description="Score a compensation-index submission.")
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
    """Confirm all validation dataset keys are present with the required kappa field."""
    for dataset in datasets:
        if dataset not in data:
            print(
                f"ERROR: dataset key '{dataset}' missing from {path}",
                file=sys.stderr,
            )
            sys.exit(1)
        if "kappa" not in data[dataset]:
            print(
                f"ERROR: field 'kappa' missing under '{dataset}' in {path}",
                file=sys.stderr,
            )
            sys.exit(1)


def score_submission(submission_data: dict, datasets: dict) -> dict:
    """
    Compute metrics for all validation datasets.

    Parameters
    ----------
    submission_data:
        Parsed results.yaml dict.
    datasets:
        The ``datasets`` dict from BenchmarkConfig (keys = dataset names,
        values contain ``reference_values``).

    Returns
    -------
    dict
        Per-dataset scoring results keyed by dataset name.
    """
    theoretical = {}
    for ds_name, ds_config in datasets.items():
        kappa_ref = float(ds_config["reference_values"]["kappa"])
        kappa_sub = float(submission_data[ds_name]["kappa"])
        theoretical[ds_name] = {
            "kappa_reference": kappa_ref,
            "kappa_submitted": kappa_sub,
            "abs_error":       round(abs_error(kappa_sub, kappa_ref), 6),
            "rel_error_pct":   round(rel_error_pct(kappa_sub, kappa_ref), 4),
        }
    return theoretical


def _build_compensation_record(score_data: dict, _: Path) -> dict:
    """Extract per-dataset theoretical scores from a score_output.json dict."""
    theoretical = score_data.get("vs_references", {}).get("theoretical", {})
    return {ds: theoretical.get(ds) for ds in theoretical} if theoretical else {}


def main():
    args = parse_args()
    config = load_config(BENCHMARK_DIR)
    datasets = config.datasets  # dict of dataset_name → {label, reference_values, ...}

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
        for ds_name, ds_config in datasets.items():
            kappa_ref = ds_config["reference_values"]["kappa"]
            print(f"  {ds_name}: κ_reference = {kappa_ref}")
        print()

        try:
            submission_data = load_yaml(submission_path)
        except Exception as exc:
            print(f"ERROR: failed to load {submission_path}: {exc}", file=sys.stderr)
            sys.exit(1)

        validate_submission(submission_data, submission_path, datasets)
        theoretical = score_submission(submission_data, datasets)

        results = {
            "submission": str(submission_path),
            "vs_references": {
                "theoretical": theoretical,
            },
            "vs_references_summary": {},
        }

        out_path = Path(args.output) if args.output else None
        written = write_score_output(results, submission_path, out_path)
        all_results.append(results)
        print(f"  Results written to: {written}")
        print()

    # Compile results_table.json when running in all-submissions mode.
    if args.submission is None:
        tbl_path = compile_results_table(
            submissions, BENCHMARK_DIR, _build_compensation_record
        )
        print(f"Compiled {len(submissions)} submission(s) → {tbl_path}")

    output = all_results if args.submission is None else all_results[0]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
