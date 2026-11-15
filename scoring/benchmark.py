"""
Load and validate benchmark.yaml configuration files.

Each benchmark directory contains a ``benchmark.yaml`` that is the single
source of truth for the benchmark's identity, taxonomy, submission format,
metrics, and website config.  This module provides a dataclass that all
scoring scripts and build tools consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_REFERENCE_TYPES = {"validation", "reference", "intercomparison"}
VALID_DATA_TYPES = {"identification", "map", "value"}


@dataclass
class BenchmarkConfig:
    """Parsed and validated contents of a benchmark's ``benchmark.yaml``."""

    name: str
    slug: str
    tagline: str                  # one-sentence description for benchmark cards
    domain: str                   # fluvial | coastal | stratigraphy | aeolian | lab | other
    status: str                   # active | draft | archived
    reference_type: str           # validation | reference | intercomparison
    data_type: str                # identification | map | value
    submission_file_pattern: str
    scoring: dict
    datasets: dict | None         # populated for value benchmarks; None otherwise
    references_manifest: Path | None  # resolved absolute path, or None
    website: dict                 # may be empty dict
    benchmark_dir: Path           # absolute path to the benchmark directory


def load_config(benchmark_dir: Path) -> BenchmarkConfig:
    """
    Load and validate ``benchmark.yaml`` from *benchmark_dir*.

    Parameters
    ----------
    benchmark_dir:
        Path to the benchmark directory (e.g. ``benchmarks/shoreline/``).

    Returns
    -------
    BenchmarkConfig

    Raises
    ------
    FileNotFoundError
        If ``benchmark.yaml`` does not exist in *benchmark_dir*.
    ValueError
        If ``reference_type`` or ``data_type`` hold an unrecognised value.
    """
    benchmark_dir = Path(benchmark_dir).resolve()
    yaml_path = benchmark_dir / "benchmark.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(
            f"benchmark.yaml not found in {benchmark_dir}\n"
            f"  Expected: {yaml_path}"
        )

    with open(yaml_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    reference_type = raw.get("reference_type", "")
    if reference_type not in VALID_REFERENCE_TYPES:
        raise ValueError(
            f"Invalid reference_type '{reference_type}' in {yaml_path}.\n"
            f"  Allowed values: {sorted(VALID_REFERENCE_TYPES)}"
        )

    data_type = raw.get("data_type", "")
    if data_type not in VALID_DATA_TYPES:
        raise ValueError(
            f"Invalid data_type '{data_type}' in {yaml_path}.\n"
            f"  Allowed values: {sorted(VALID_DATA_TYPES)}"
        )

    # Resolve references manifest path relative to benchmark_dir.
    refs_rel = raw.get("references", {}).get("manifest")
    references_manifest: Path | None = None
    if refs_rel:
        references_manifest = (benchmark_dir / refs_rel).resolve()

    return BenchmarkConfig(
        name=raw["name"],
        slug=raw["slug"],
        tagline=raw.get("tagline", ""),
        domain=raw.get("domain", ""),
        status=raw.get("status", "active"),
        reference_type=reference_type,
        data_type=data_type,
        submission_file_pattern=raw["submission"]["file_pattern"],
        scoring=raw.get("scoring", {}),
        datasets=raw.get("datasets"),
        references_manifest=references_manifest,
        website=raw.get("website", {}),
        benchmark_dir=benchmark_dir,
    )
