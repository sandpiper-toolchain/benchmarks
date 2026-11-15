"""
Output helpers for sandpiper benchmark scoring scripts.

Provides two convenience functions used by all per-benchmark ``score.py``
scripts:

- ``write_score_output`` — write ``score_output.json`` next to a submission
- ``write_results_table`` — write ``results_table.json`` at the benchmark root
"""

from __future__ import annotations

import json
from pathlib import Path


def write_score_output(
    results: dict,
    submission_path: Path,
    out_path: Path | None = None,
) -> Path:
    """
    Write scoring results to ``score_output.json``.

    By default the file is written next to the submission file.  Pass
    *out_path* to override the destination.

    Parameters
    ----------
    results:
        The scoring results dict to serialise.
    submission_path:
        Path to the submission file (used to derive the default output
        location).
    out_path:
        Explicit destination path.  When ``None`` the file is written to
        ``submission_path.parent / "score_output.json"``.

    Returns
    -------
    Path
        The path that was written.
    """
    destination = Path(out_path) if out_path is not None else Path(submission_path).parent / "score_output.json"
    destination.write_text(json.dumps(results, indent=2))
    return destination


def write_results_table(records: list[dict], benchmark_dir: Path) -> Path:
    """
    Write the compiled results table to ``results_table.json``.

    Parameters
    ----------
    records:
        List of record dicts, one per submission.
    benchmark_dir:
        Path to the benchmark root directory.

    Returns
    -------
    Path
        The path that was written (``benchmark_dir / "results_table.json"``).
    """
    destination = Path(benchmark_dir) / "results_table.json"
    destination.write_text(json.dumps(records, indent=2))
    return destination
