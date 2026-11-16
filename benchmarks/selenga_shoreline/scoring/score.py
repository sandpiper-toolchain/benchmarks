#!/usr/bin/env python
"""
Score a submitted shoreline against one or more Selenga benchmark references.

Usage
-----
    python score.py [path/to/submission.geojson] [--output results.json]

With no submission path, all GeoJSON files under ../submissions/ are scored
and each result is written next to its input file.  After scoring, the script
compiles results_table.json at the benchmark root from existing score_output.json
files (so the compilation step succeeds even when the raster is not available).

The script exits with code 0 on success and prints a JSON summary to stdout.
It writes results to --output for a single submission, or to score_output.json
next to each submission in all-submissions mode.

Expected directory layout (relative to this script):
    ../data/selenga_clipped.tif   -- benchmark input mask (gitignored; download separately)
    ../data/references.yaml       -- list of reference digitizations
    ../data/<ref>.geojson         -- one or more reference shoreline files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

BENCHMARK_DIR = HERE.parent
DATA_DIR = BENCHMARK_DIR / "data"
MASK_PATH = DATA_DIR / "selenga_clipped.tif"
REFERENCES_YAML = DATA_DIR / "references.yaml"

from scoring.compile import compile_results_table, discover_submissions
from scoring.metrics.map_metrics import mean_distance_error, pixel_f1, roughness_agreement
from scoring.output import write_score_output


def parse_args():
    p = argparse.ArgumentParser(description="Score a Selenga shoreline submission.")
    p.add_argument(
        "submission",
        nargs="?",
        help="Path to submitted GeoJSON polyline (omit to score all submissions).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Where to write the JSON result (default: score_output.json next to submission).",
    )
    return p.parse_args()


def load_references() -> list[dict]:
    """
    Read references.yaml and return the list of reference dicts, each with
    a resolved 'path' key added pointing to the actual GeoJSON file.
    Exits with an error if the YAML or any listed file is missing.
    """
    if not REFERENCES_YAML.exists():
        print(f"ERROR: references manifest not found: {REFERENCES_YAML}", file=sys.stderr)
        sys.exit(1)

    with open(REFERENCES_YAML) as fh:
        config = yaml.safe_load(fh)

    refs = config.get("references", [])
    if not refs:
        print("ERROR: references.yaml lists no references.", file=sys.stderr)
        sys.exit(1)

    missing = []
    for entry in refs:
        path = DATA_DIR / entry["file"]
        entry["path"] = path
        if not path.exists():
            missing.append(str(path))

    if missing:
        print("ERROR: the following reference file(s) listed in references.yaml do not exist:",
              file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        sys.exit(1)

    return refs


def score_against_reference(submission: Path, ref_entry: dict) -> dict:
    """
    Run all three metrics for one reference and return a results dict.

    Parameters
    ----------
    submission:
        Resolved path to the submitted GeoJSON.
    ref_entry:
        One entry from references.yaml (with 'path' key added).

    Returns
    -------
    dict with keys mean_distance_error_m, pixel_f1, roughness_agreement.
    """
    ref_path = ref_entry["path"]

    mde   = mean_distance_error(submission, ref_path)
    f1    = pixel_f1(submission, ref_path, MASK_PATH)
    rough = roughness_agreement(submission, ref_path, MASK_PATH)

    return {
        "mean_distance_error_m": round(mde, 3),
        "pixel_f1": {k: round(v, 4) for k, v in f1.items()},
        "roughness_agreement": {k: round(v, 4) for k, v in rough.items()},
    }


def compute_summary(per_ref: dict[str, dict]) -> dict:
    """
    Compute mean and std across references for each scalar metric.

    Only called when there are ≥2 references.  Operates on three scalars:
      - mean_distance_error_m
      - pixel_f1 → f1 sub-key
      - roughness_agreement → relative_difference_pct sub-key

    Parameters
    ----------
    per_ref:
        Mapping from reference stem → score dict (output of score_against_reference).

    Returns
    -------
    dict with aggregated mean/std entries.
    """
    mde_vals    = [v["mean_distance_error_m"]                        for v in per_ref.values()]
    f1_vals     = [v["pixel_f1"]["f1"]                               for v in per_ref.values()]
    rough_vals  = [v["roughness_agreement"]["relative_difference_pct"] for v in per_ref.values()]

    def _agg(vals: list[float]) -> dict:
        arr = np.array(vals, dtype=float)
        return {"mean": round(float(np.mean(arr)), 4),
                "std":  round(float(np.std(arr, ddof=0)), 4)}

    return {
        "mean_distance_error_m":           _agg(mde_vals),
        "pixel_f1_f1":                     _agg(f1_vals),
        "roughness_relative_difference_pct": _agg(rough_vals),
    }


def score_one(submission: Path, refs: list[dict], out_path: Path | None = None) -> dict:
    """
    Score one submission against all references, write score_output.json,
    and return the results dict.
    """
    print(f"Scoring: {submission.name}")
    print(f"  mask        : {MASK_PATH}")
    print(f"  references  : {len(refs)}")
    for ref in refs:
        print(f"    {ref['file']}")
    print()

    vs_references: dict[str, dict] = {}
    for ref_entry in refs:
        stem = Path(ref_entry["file"]).stem
        print(f"  → scoring vs. {stem} ...", flush=True)
        vs_references[stem] = score_against_reference(submission, ref_entry)

    vs_references_summary: dict = {}
    if len(vs_references) >= 2:
        vs_references_summary = compute_summary(vs_references)

    results = {
        "submission": str(submission),
        "vs_references": vs_references,
        "vs_references_summary": vs_references_summary,
    }
    dest = write_score_output(results, submission, out_path)
    print(f"Results written to: {dest}")
    return results


def _build_shoreline_record(score_data: dict, submission_path: Path) -> dict:
    """Extract shoreline-specific fields from a score_output.json dict."""
    try:
        rel_path = submission_path.relative_to(BENCHMARK_DIR).as_posix()
    except ValueError:
        rel_path = str(submission_path)
    return {
        "geojson_files": [rel_path],
        "vs_references": score_data.get("vs_references", {}),
        "vs_references_summary": score_data.get("vs_references_summary", {}),
    }


def main():
    args = parse_args()

    if args.submission is None:
        # ── All-submissions mode ───────────────────────────────────────────────
        if args.output:
            print(
                "ERROR: --output can only be used when scoring one submission.",
                file=sys.stderr,
            )
            sys.exit(2)

        submissions_dir = BENCHMARK_DIR / "submissions"
        submissions = discover_submissions(submissions_dir, "results.geojson")
        if not submissions:
            print(
                f"ERROR: no submission GeoJSON files found in {submissions_dir}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Score submissions if the raster is available; warn and skip if not.
        # Either way, results_table.json is compiled from existing score_output.json
        # files so the compile job succeeds in CI where the raster is not present.
        all_results = []
        if not MASK_PATH.exists():
            print(
                f"WARNING: benchmark mask not found: {MASK_PATH}\n"
                f"  Scoring skipped — existing score_output.json files will be compiled.",
                file=sys.stderr,
            )
        else:
            refs = load_references()
            for submission in submissions:
                results = score_one(submission, refs)
                all_results.append(results)

        benchmark_dir = BENCHMARK_DIR
        tbl_path = compile_results_table(submissions, benchmark_dir, _build_shoreline_record)
        print(f"\nCompiled {len(submissions)} submission(s) → {tbl_path}")

        print()
        print(json.dumps(all_results, indent=2))

    else:
        # ── Single-submission mode ─────────────────────────────────────────────
        submission = Path(args.submission).resolve()
        if not submission.is_file():
            print(
                f"ERROR: submission file not found: {submission}",
                file=sys.stderr,
            )
            sys.exit(1)

        if not MASK_PATH.exists():
            print(f"ERROR: benchmark mask not found: {MASK_PATH}", file=sys.stderr)
            print(
                f"  This file is not committed to git. Obtain it from the benchmark data\n"
                f"  package described in benchmarks/shoreline/README.md.",
                file=sys.stderr,
            )
            sys.exit(1)

        refs = load_references()
        out_path = Path(args.output) if args.output else None
        results = score_one(submission, refs, out_path)

        print()
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
