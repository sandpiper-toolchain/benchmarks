#!/usr/bin/env python
"""
Score a submitted shoreline against one or more Selenga benchmark references.

Usage
-----
    python score.py [path/to/submission.geojson] [--output results.json]

With no submission path, all GeoJSON files under ../submissions/ are scored
and each result is written next to its input file.

The script exits with code 0 on success and prints a JSON summary to stdout.
It writes results to --output for a single submission, or to score_output.json
next to each submission in all-submissions mode.

Expected directory layout (relative to this script):
    ../data/selenga_clipped.tif   -- benchmark input mask
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
DATA_DIR = HERE.parent / "data"
MASK_PATH = DATA_DIR / "selenga_clipped.tif"
REFERENCES_YAML = DATA_DIR / "references.yaml"

sys.path.insert(0, str(HERE))
from metrics import mean_distance_error, pixel_f1, roughness_agreement


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


def main():
    args = parse_args()

    if args.submission is None:
        if args.output:
            print(
                "ERROR: --output can only be used when scoring one submission.",
                file=sys.stderr,
            )
            sys.exit(2)

        submissions_dir = HERE.parent / "submissions"
        if not submissions_dir.is_dir():
            print(
                f"ERROR: submissions directory not found: {submissions_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
        submissions = sorted(
            path.resolve()
            for path in submissions_dir.rglob("*.geojson")
            if path.relative_to(submissions_dir).parts[0] != "example"
        )
        if not submissions:
            print(
                f"ERROR: no submission GeoJSON files found in {submissions_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        submissions = [Path(args.submission).resolve()]
        if not submissions[0].is_file():
            print(
                f"ERROR: submission file not found: {submissions[0]}",
                file=sys.stderr,
            )
            sys.exit(1)

    if not MASK_PATH.exists():
        print(f"ERROR: benchmark mask not found: {MASK_PATH}", file=sys.stderr)
        sys.exit(1)

    refs = load_references()
    all_results = []
    for submission in submissions:
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
        out_path = (
            Path(args.output) if args.output
            else submission.parent / "score_output.json"
        )
        out_path.write_text(json.dumps(results, indent=2))
        all_results.append(results)
        print(f"Results written to: {out_path}")

    print()
    output = all_results if args.submission is None else all_results[0]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
