"""
Shared compile helpers for sandpiper benchmark scoring scripts.

Provides three functions used by every ``score.py``:

- ``load_yaml``             -- safe YAML loader (returns empty dict on empty file)
- ``discover_submissions``  -- walk a submissions/ directory, skipping the example folder
- ``compile_results_table`` -- merge score_output.json + metadata.yaml → results_table.json
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

from scoring.metadata import read_metadata
from scoring.output import write_results_table


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict (empty dict on empty file)."""
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def discover_submissions(submissions_dir: Path, pattern: str) -> list[Path]:
    """
    Walk *submissions_dir* for files matching *pattern*, skipping the top-level
    ``example`` subdirectory.

    Parameters
    ----------
    submissions_dir:
        Path to the benchmark's ``submissions/`` directory.
    pattern:
        Glob pattern for submission files (e.g. ``"results.yaml"`` or ``"*.geojson"``).

    Returns
    -------
    list[Path]
        Sorted, resolved paths of matching files.  Empty list when none match.

    Raises
    ------
    SystemExit
        If *submissions_dir* does not exist.
    """
    if not submissions_dir.is_dir():
        print(f"ERROR: submissions directory not found: {submissions_dir}", file=sys.stderr)
        sys.exit(1)

    return sorted(
        path.resolve()
        for path in submissions_dir.rglob(pattern)
        if path.relative_to(submissions_dir).parts[0] != "example"
    )


def compile_results_table(
    submissions: list[Path],
    benchmark_dir: Path,
    extract_fn: Callable[[dict, Path], dict] | None = None,
) -> Path:
    """
    Build ``results_table.json`` by merging ``score_output.json`` with ``metadata.yaml``
    for each submission.

    For each path in *submissions*, reads ``metadata.yaml`` from the submission's
    directory, then reads ``score_output.json`` if present and calls *extract_fn* to
    pull benchmark-specific fields into the record.

    Parameters
    ----------
    submissions:
        Resolved paths to submission files (e.g. ``results.yaml`` or ``results.geojson``).
        Each file's parent directory should contain ``metadata.yaml`` and optionally
        ``score_output.json``.
    benchmark_dir:
        Benchmark root; ``results_table.json`` is written here.
    extract_fn:
        ``(score_data: dict, submission_path: Path) -> dict``
        Called once per submission to extract benchmark-specific fields from the
        parsed ``score_output.json``.  When ``score_output.json`` is absent,
        *score_data* is ``{}``.  Defaults to returning all of *score_data* unchanged.

    Returns
    -------
    Path
        The path of the written ``results_table.json``.
    """
    if extract_fn is None:
        def extract_fn(score_data: dict, _: Path) -> dict:  # type: ignore[misc]
            return dict(score_data)

    records = []
    for sub_path in submissions:
        meta = read_metadata(sub_path.parent / "metadata.yaml")
        record = dict(meta)

        score_path = sub_path.parent / "score_output.json"
        score_data = json.loads(score_path.read_text()) if score_path.exists() else {}

        record.update(extract_fn(score_data, sub_path))  # type: ignore[arg-type]
        records.append(record)

    return write_results_table(records, benchmark_dir)
