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
class ReferenceEntry:
    """One entry in the ``references:`` block of a ``benchmark.yaml``.

    Fields are optional and vary by benchmark type:

    * Value benchmarks supply ``data_file`` and ``fields``.
    * Map benchmarks supply ``file``.
    * Identification benchmarks have no comparison target and therefore no
      ``ReferenceEntry`` objects at all.

    ``fields`` encoding:

    * **Validation** — a ``dict`` mapping field name to its known truth value,
      e.g. ``{"kappa": 1.0}``.  The runner scores submitted values against these.
    * **Intercomparison** — a plain ``list`` of field names, e.g. ``["kappa", "Tc"]``.
      The runner collects and reports submitted values as-is.
    """

    label: str
    data_file: str | None = None   # relative path; value benchmarks only
    fields: dict | list | None = None  # dict → validation; list → intercomparison
    file: str | None = None        # relative path; map benchmarks only


@dataclass
class BenchmarkConfig:
    """Parsed and validated contents of a benchmark's ``benchmark.yaml``."""

    name: str
    slug: str
    tagline: str                   # one-sentence description for benchmark cards
    domain: str                    # fluvial | coastal | stratigraphy | aeolian | lab | other
    status: str                    # active | draft | archived
    reference_type: str            # validation | reference | intercomparison
    data_type: str                 # identification | map | value
    submission_file_pattern: str
    scoring: dict
    references: dict[str, ReferenceEntry] | None  # None for identification benchmarks
    website: dict                  # may be empty dict
    benchmark_dir: Path            # absolute path to the benchmark directory

    @property
    def runner_key(self) -> tuple[str, str]:
        """Return ``(reference_type, data_type)`` — the dispatch key for runner lookup."""
        return (self.reference_type, self.data_type)


def _parse_references(raw_refs: dict) -> dict[str, ReferenceEntry]:
    """Convert the ``references:`` YAML block into a dict of :class:`ReferenceEntry`."""
    result: dict[str, ReferenceEntry] = {}
    for key, entry in raw_refs.items():
        result[key] = ReferenceEntry(
            label=entry.get("label", key),
            data_file=entry.get("data_file"),
            fields=entry.get("fields"),
            file=entry.get("file"),
        )
    return result


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

    # Parse unified references block.  Each entry is a named key → ReferenceEntry.
    # Identification benchmarks have no references key; references is None for them.
    raw_refs = raw.get("references") or {}
    references: dict[str, ReferenceEntry] | None = (
        _parse_references(raw_refs) if raw_refs else None
    )

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
        references=references,
        website=raw.get("website", {}),
        benchmark_dir=benchmark_dir,
    )
