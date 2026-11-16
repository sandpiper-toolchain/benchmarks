"""
Canonical metadata reader for sandpiper benchmark submissions.

Every submission directory may contain a ``metadata.yaml`` file.  This
module defines the authoritative set of fields (a superset of all fields
used across existing benchmarks) and provides a single reader that returns
a flat dict with ``None`` defaults for any missing field.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Superset of all metadata fields across all benchmarks.
METADATA_FIELDS: tuple[str, ...] = (
    "method_name",
    "method_description",
    "method_version",
    "method_url",
    "author_name",
    "author_orcid",
    "preferred_citation",
    "date",
    "notes",
    "runtime_seconds",
    "runtime_machine",
    "runtime_notes",
)


def read_metadata(metadata_path: Path) -> dict:
    """
    Read a submission's ``metadata.yaml`` and return a flat dict.

    All fields in ``METADATA_FIELDS`` are always present in the returned
    dict; missing fields default to ``None``.  The ``date`` field is
    coerced to ``str`` when present.

    This function never raises: a missing or malformed file causes a
    WARNING on stderr and returns the all-``None`` defaults dict.

    Parameters
    ----------
    metadata_path:
        Path to the submission's ``metadata.yaml``.

    Returns
    -------
    dict
        Flat dict with one key per entry in ``METADATA_FIELDS``.
    """
    defaults: dict = {k: None for k in METADATA_FIELDS}

    if not Path(metadata_path).exists():
        return defaults

    try:
        with open(metadata_path) as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        print(
            f"  WARNING: could not read {metadata_path}: {exc}",
            file=sys.stderr,
        )
        return defaults

    result = dict(defaults)
    for key in METADATA_FIELDS:
        val = data.get(key)
        if val is not None:
            result[key] = str(val) if key == "date" else val
    return result
