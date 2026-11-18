#!/usr/bin/env python
"""Top-level scoring CLI for sandpiper benchmarks.

Usage
-----
Score a single submission::

    python score.py <benchmark> <submission_path>
    python score.py <benchmark> <submission_path> --output results.json

Compile all submissions into ``results_table.json``::

    python score.py <benchmark> --compile
    python score.py <benchmark>                  # same as --compile

``<benchmark>`` may be a directory path (absolute or relative) or a benchmark
slug.  Slugs are resolved to ``benchmarks/<slug>/`` relative to this file.

The script exits with code 0 on success and code 1 on any error.

For a single submission, the JSON result is printed to stdout and written to
``score_output.json`` next to the submission file (or to the path given by
``--output``).  For compile mode, ``results_table.json`` is written at the
benchmark root; a summary line is printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Ensure the repo root is on sys.path so `scoring` is importable regardless
# of the working directory.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


# ---------------------------------------------------------------------------
# benchmark directory resolution
# ---------------------------------------------------------------------------

def _resolve_benchmark_dir(arg: str) -> Path:
    """
    Resolve *arg* to a benchmark directory that contains ``benchmark.yaml``.

    Accepts:
    * An absolute or relative path to a benchmark directory.
    * A benchmark slug — tried as ``<repo_root>/benchmarks/<slug>/``.

    Parameters
    ----------
    arg:
        A directory path or benchmark slug supplied by the user.

    Returns
    -------
    Path
        Resolved, absolute path to the benchmark directory.

    Raises
    ------
    FileNotFoundError
        When no directory containing ``benchmark.yaml`` can be found.
    """
    # First try as a direct path.
    candidate = Path(arg)
    if not candidate.is_absolute():
        candidate = (HERE / arg).resolve()
    else:
        candidate = candidate.resolve()

    if (candidate / "benchmark.yaml").exists():
        return candidate

    # Fall back to treating arg as a slug.
    slug_candidate = (HERE / "benchmarks" / arg).resolve()
    if (slug_candidate / "benchmark.yaml").exists():
        return slug_candidate

    raise FileNotFoundError(
        f"Cannot find a benchmark directory for '{arg}'.\n"
        f"  Tried:\n"
        f"    {candidate}\n"
        f"    {slug_candidate}\n"
        f"  Make sure the directory contains a 'benchmark.yaml' file."
    )


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="score.py",
        description="Score sandpiper benchmark submissions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Score one submission:
  python score.py compensation submissions/my-method/results.yaml
  python score.py benchmarks/selenga_shoreline submissions/my-method/results.geojson

  # Score one submission and write to a custom output path:
  python score.py compensation submissions/my-method/results.yaml --output /tmp/out.json

  # Compile all submissions → results_table.json:
  python score.py compensation --compile
  python score.py benchmarks/river_dunes
""",
    )
    p.add_argument(
        "benchmark",
        help=(
            "Benchmark directory path or slug "
            "(e.g. 'compensation' or 'benchmarks/compensation/')."
        ),
    )
    p.add_argument(
        "submission",
        nargs="?",
        default=None,
        metavar="submission_path",
        help=(
            "Path to the submission file to score.  "
            "Omit (or use --compile) to compile all submissions."
        ),
    )
    p.add_argument(
        "--output", "-o",
        default=None,
        metavar="PATH",
        help=(
            "Destination for score_output.json.  "
            "Defaults to score_output.json next to the submission file.  "
            "Only valid in single-submission mode."
        ),
    )
    p.add_argument(
        "--compile",
        action="store_true",
        help=(
            "Compile all submissions into results_table.json.  "
            "This is the default when no submission path is given."
        ),
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    # -- guard against invalid flag combinations ----------------------------
    if args.output and (args.submission is None or args.compile):
        print(
            "ERROR: --output can only be used when scoring a single submission "
            "(not with --compile or when no submission path is given).",
            file=sys.stderr,
        )
        sys.exit(2)

    # -- resolve benchmark directory ----------------------------------------
    try:
        benchmark_dir = _resolve_benchmark_dir(args.benchmark)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # -- load config --------------------------------------------------------
    from scoring.benchmark import load_config
    from scoring.compile import compile_all
    from scoring.output import write_score_output
    from scoring.runners import RUNNERS, make_extract_fn

    try:
        config = load_config(benchmark_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR loading benchmark config: {exc}", file=sys.stderr)
        sys.exit(1)

    # -- look up runner -----------------------------------------------------
    runner_key = config.runner_key
    score_fn = RUNNERS.get(runner_key)
    if score_fn is None:
        print(
            f"ERROR: No runner is registered for benchmark type "
            f"({runner_key[0]!r}, {runner_key[1]!r}).\n"
            f"  Benchmark : {config.slug}\n"
            f"  Available : {sorted(RUNNERS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # -- dispatch -----------------------------------------------------------
    compile_mode = args.compile or args.submission is None

    if not compile_mode:
        # ── single-submission mode ─────────────────────────────────────────
        submission_path = Path(args.submission)
        if not submission_path.exists():
            print(
                f"ERROR: Submission file not found: {submission_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        out_path = Path(args.output) if args.output else None

        print(f"Scoring: {submission_path}")
        print(f"  benchmark : {config.slug}  ({runner_key[0]}, {runner_key[1]})")
        print()

        try:
            result = score_fn(submission_path, config)
        except NotImplementedError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

        dest = write_score_output(result, submission_path, out_path)
        print(f"Results written to: {dest}")
        print()
        print(json.dumps(result, indent=2))

    else:
        # ── compile mode ──────────────────────────────────────────────────
        print(f"Compiling: {config.slug}  ({runner_key[0]}, {runner_key[1]})")
        print(f"  benchmark dir: {benchmark_dir}")
        print()

        extract_fn = make_extract_fn(config)

        try:
            dest = compile_all(benchmark_dir, config, score_fn, extract_fn=extract_fn)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"Compiled results → {dest}")


if __name__ == "__main__":
    main()
