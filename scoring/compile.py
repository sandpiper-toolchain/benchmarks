"""
Shared compile helpers for sandpiper benchmark scoring scripts.

Provides four functions used by every ``score.py``:

- ``load_yaml``             -- safe YAML loader (returns empty dict on empty file)
- ``discover_submissions``  -- walk a submissions/ directory, skipping the example folder
- ``compile_results_table`` -- merge score_output.json + metadata.yaml → results_table.json
- ``compile_all``           -- score every submission and write results_table.json
- ``_make_extract_fn``      -- return a generic extract function derived from reference_type
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

from scoring.metadata import read_metadata
from scoring.output import write_results_table, write_score_output


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


def _make_extract_fn(config) -> Callable[[dict, Path], dict]:
    """
    Return a generic extract function derived from *config.reference_type*.

    The returned function has the signature ``(score_data: dict, path: Path) -> dict``
    expected by :func:`compile_results_table`.

    For validation and reference benchmarks the extract function pulls
    ``vs_references`` and ``vs_references_summary`` from the scored output.
    For intercomparison benchmarks it pulls ``reported``.

    Parameters
    ----------
    config:
        A :class:`~scoring.benchmark.BenchmarkConfig` instance.

    Returns
    -------
    Callable
        ``(score_data, path) -> dict``
    """
    if config.reference_type in {"validation", "reference"}:
        def extract(score_data: dict, _path: Path) -> dict:
            return {
                "vs_references":         score_data.get("vs_references", {}),
                "vs_references_summary": score_data.get("vs_references_summary", {}),
            }
    else:  # intercomparison
        def extract(score_data: dict, _path: Path) -> dict:  # type: ignore[misc]
            return {"reported": score_data.get("reported", {})}
    return extract


def compile_all(
    benchmark_dir: Path,
    config,
    score_fn: Callable,
    extract_fn: Callable[[dict, Path], dict] | None = None,
) -> Path:
    """
    Score every submission in *benchmark_dir* and write ``results_table.json``.

    This is the central compile entry point used by the top-level ``score.py``
    CLI.  All runner types share the same pattern:

    1. Discover submissions matching ``config.submission_file_pattern``.
    2. Score each submission with *score_fn* and write ``score_output.json``
       next to it.
    3. Aggregate all scored outputs into ``results_table.json``.

    Parameters
    ----------
    benchmark_dir:
        Absolute path to the benchmark directory (e.g. ``benchmarks/compensation/``).
    config:
        A :class:`~scoring.benchmark.BenchmarkConfig` instance loaded from
        the benchmark's ``benchmark.yaml``.
    score_fn:
        ``(submission_path: Path, config: BenchmarkConfig) -> dict``
        Called once per submission; must return the normalised scoring dict.
    extract_fn:
        Optional ``(score_data: dict, submission_path: Path) -> dict``
        passed through to :func:`compile_results_table`.  When ``None``
        (the default) a generic function is built from *config* via
        :func:`_make_extract_fn`.  Runners that need to inject extra fields
        (e.g. the map runner adds ``geojson_files``) may pass a wrapper here.

    Returns
    -------
    Path
        The path of the written ``results_table.json``.
    """
    benchmark_dir = Path(benchmark_dir)
    submissions = discover_submissions(
        benchmark_dir / "submissions",
        config.submission_file_pattern,
    )
    for sub in submissions:
        result = score_fn(sub, config)
        write_score_output(result, sub)

    if extract_fn is None:
        extract_fn = _make_extract_fn(config)

    return compile_results_table(submissions, benchmark_dir, extract_fn)
