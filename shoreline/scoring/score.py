#!/usr/bin/env python
"""
Score a submitted shoreline against the Selenga benchmark reference.

Usage
-----
    python score.py <path/to/submission.geojson> [--output results.json]

The script exits with code 0 on success and prints a JSON summary to stdout.
It also writes the same JSON to --output (default: score_output.json in the
submission directory) for CI artifact capture.

Expected directory layout (relative to this script):
    ../data/selenga_clipped.tif   -- benchmark input mask
    ../data/reference.geojson     -- reference shoreline (ground truth)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
MASK_PATH = DATA_DIR / "selenga_clipped.tif"
REFERENCE_PATH = DATA_DIR / "reference.geojson"

sys.path.insert(0, str(HERE))
from metrics import mean_distance_error, pixel_f1, roughness_agreement


def parse_args():
    p = argparse.ArgumentParser(description="Score a Selenga shoreline submission.")
    p.add_argument("submission", help="Path to submitted GeoJSON polyline.")
    p.add_argument(
        "--output",
        default=None,
        help="Where to write the JSON result (default: score_output.json next to submission).",
    )
    return p.parse_args()


def main():
    args = parse_args()
    submission = Path(args.submission).resolve()

    if not submission.exists():
        print(f"ERROR: submission file not found: {submission}", file=sys.stderr)
        sys.exit(1)
    if not MASK_PATH.exists():
        print(f"ERROR: benchmark mask not found: {MASK_PATH}", file=sys.stderr)
        sys.exit(1)
    if not REFERENCE_PATH.exists():
        print(f"ERROR: reference shoreline not found: {REFERENCE_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Scoring: {submission.name}")
    print(f"  mask      : {MASK_PATH}")
    print(f"  reference : {REFERENCE_PATH}")
    print()

    mde   = mean_distance_error(submission, REFERENCE_PATH)
    f1    = pixel_f1(submission, REFERENCE_PATH, MASK_PATH)
    rough = roughness_agreement(submission, REFERENCE_PATH, MASK_PATH)

    results = {
        "submission": str(submission),
        "mean_distance_error_m": round(mde, 3),
        "pixel_f1": {k: round(v, 4) for k, v in f1.items()},
        "roughness_agreement": {k: round(v, 4) for k, v in rough.items()},
    }

    out_path = (
        Path(args.output) if args.output
        else submission.parent / "score_output.json"
    )
    out_path.write_text(json.dumps(results, indent=2))

    print(json.dumps(results, indent=2))
    print(f"\nResults written to: {out_path}")


if __name__ == "__main__":
    main()
