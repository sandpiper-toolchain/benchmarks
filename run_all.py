#!/usr/bin/env python
"""Run scoring for all benchmarks and regenerate all results_table.json files.

Usage
-----
    python run_all.py                  # run all benchmarks
    python run_all.py shoreline        # run one benchmark by slug
    python run_all.py --dry-run        # list what would run without executing
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_args():
    p = argparse.ArgumentParser(
        description="Run scoring for all (or one) sandpiper benchmark(s)."
    )
    p.add_argument(
        "slug",
        nargs="?",
        default=None,
        help="Benchmark slug to run (e.g. 'shoreline').  Omit to run all benchmarks.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would run without actually executing.",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Discover all score.py scripts, sorted for reproducible order.
    all_score_scripts = sorted(HERE.glob("benchmarks/*/scoring/score.py"))

    if not all_score_scripts:
        print("ERROR: no benchmarks/*/scoring/score.py scripts found.", file=sys.stderr)
        sys.exit(1)

    if args.slug is not None:
        score_scripts = [s for s in all_score_scripts if s.parents[1].name == args.slug]
        if not score_scripts:
            available = [s.parents[1].name for s in all_score_scripts]
            print(
                f"ERROR: no score.py found for slug '{args.slug}'.\n"
                f"  Available benchmarks: {available}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        score_scripts = all_score_scripts

    if args.dry_run:
        print("Dry run — would score:")
        for score_py in score_scripts:
            slug = score_py.parents[1].name
            print(f"  {slug}  ({score_py})")
        return

    failed = []
    for score_py in score_scripts:
        slug = score_py.parents[1].name
        print(f"=== Scoring {slug} ===")
        result = subprocess.run([sys.executable, str(score_py)])
        if result.returncode != 0:
            print(
                f"ERROR: scoring failed for '{slug}' (exit code {result.returncode}).",
                file=sys.stderr,
            )
            failed.append(slug)
        print()

    if failed:
        print(
            f"ERROR: {len(failed)} benchmark(s) failed: {failed}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
