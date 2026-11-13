#!/usr/bin/env python
"""
Score a submitted compensation-index result.

Two datasets are scored against theoretical κ references (Straub et al., 2009):
    compensational_stacking   κ_reference = 0.75  (typical compensational)
    random_stacking           κ_reference = 0.50  (Poissonian / random walk)

Two datasets have no universal theoretical reference.  Their κ and T_c values
are reported as-is for cross-submission comparison:
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
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SUBMISSIONS_DIR = HERE.parent / "submissions"

sys.path.insert(0, str(HERE))
from metrics import (
    KAPPA_REFERENCE,
    COMPARATIVE_DATASETS,
    score_theoretical,
    report_comparative,
)

THEORETICAL_DATASETS = tuple(KAPPA_REFERENCE)
ALL_DATASETS = THEORETICAL_DATASETS + COMPARATIVE_DATASETS


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


def load_yaml(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def validate_submission(data: dict, path: Path) -> None:
    """
    Confirm all four dataset keys are present with the required sub-fields.

    Theoretical datasets require only ``kappa``.
    Comparative datasets require both ``kappa`` and ``Tc``.
    """
    for dataset in ALL_DATASETS:
        if dataset not in data:
            print(
                f"ERROR: dataset key '{dataset}' missing from {path}",
                file=sys.stderr,
            )
            sys.exit(1)

    for dataset in THEORETICAL_DATASETS:
        if "kappa" not in data[dataset]:
            print(
                f"ERROR: field 'kappa' missing under '{dataset}' in {path}",
                file=sys.stderr,
            )
            sys.exit(1)

    for dataset in COMPARATIVE_DATASETS:
        for field in ("kappa", "Tc"):
            if field not in data[dataset]:
                print(
                    f"ERROR: field '{field}' missing under '{dataset}' in {path}",
                    file=sys.stderr,
                )
                sys.exit(1)


def score_submission(submission_data: dict) -> tuple[dict, dict]:
    """
    Compute metrics for all four datasets.

    Returns
    -------
    theoretical : dict
        Per-dataset scoring results for the two theoretically-referenced datasets.
    comparative : dict
        Per-dataset reported values for the two comparative datasets.
    """
    theoretical = {}
    for dataset in THEORETICAL_DATASETS:
        sub = submission_data[dataset]
        result = score_theoretical(dataset, float(sub["kappa"]))
        theoretical[dataset] = {
            "kappa_reference":     result["kappa_reference"],
            "kappa_submitted":     result["kappa_submitted"],
            "kappa_abs_error":     round(result["kappa_abs_error"], 6),
            "kappa_rel_error_pct": round(result["kappa_rel_error_pct"], 4),
        }

    comparative = {}
    for dataset in COMPARATIVE_DATASETS:
        sub = submission_data[dataset]
        comparative[dataset] = report_comparative(
            dataset,
            kappa_sub=float(sub["kappa"]),
            Tc_sub=float(sub["Tc"]),
        )

    return theoretical, comparative


def main():
    args = parse_args()

    if args.submission is None:
        if args.output:
            print(
                "ERROR: --output can only be used when scoring one submission.",
                file=sys.stderr,
            )
            sys.exit(2)

        if not SUBMISSIONS_DIR.is_dir():
            print(
                f"ERROR: submissions directory not found: {SUBMISSIONS_DIR}",
                file=sys.stderr,
            )
            sys.exit(1)

        submissions = sorted(
            path.resolve()
            for path in SUBMISSIONS_DIR.rglob("results.yaml")
            if path.relative_to(SUBMISSIONS_DIR).parts[0] != "example"
        )

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
        print(f"  theoretical datasets : {', '.join(THEORETICAL_DATASETS)}")
        for ds in THEORETICAL_DATASETS:
            print(f"    {ds}: κ_reference = {KAPPA_REFERENCE[ds]}")
        print(f"  comparative datasets : {', '.join(COMPARATIVE_DATASETS)}")
        print()

        try:
            submission_data = load_yaml(submission_path)
        except Exception as exc:
            print(f"ERROR: failed to load {submission_path}: {exc}", file=sys.stderr)
            sys.exit(1)

        validate_submission(submission_data, submission_path)

        theoretical, comparative = score_submission(submission_data)

        # Follow repo-wide output convention:
        #   vs_references         — metric dicts keyed by reference name;
        #                           here the reference is "theoretical".
        #   vs_references_summary — mean/std across references (empty: one ref).
        #   comparative_datasets  — submitted values for datasets without a
        #                           theoretical reference, for cross-submission
        #                           comparison.
        results = {
            "submission": str(submission_path),
            "vs_references": {
                "theoretical": theoretical,
            },
            "vs_references_summary": {},
            "comparative_datasets": comparative,
        }

        out_path = (
            Path(args.output) if args.output
            else submission_path.parent / "score_output.json"
        )
        out_path.write_text(json.dumps(results, indent=2))
        all_results.append(results)
        print(f"  Results written to: {out_path}")
        print()

    output = all_results if args.submission is None else all_results[0]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
