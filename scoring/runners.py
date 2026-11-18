"""
Runner functions for sandpiper benchmark scoring.

Each runner implements the same interface::

    def score_one_*(submission_path: Path, config: BenchmarkConfig) -> dict: ...

The module exposes a ``RUNNERS`` dispatch table keyed by
``(reference_type, data_type)`` tuples (the
:attr:`~scoring.benchmark.BenchmarkConfig.runner_key` property).  The
top-level ``score.py`` CLI looks up the right runner from this table and calls
it with a submission path and the loaded config.

Runners return a normalised dict that always has ``"submission"`` and
``"benchmark"`` keys plus one of:

* ``"vs_references"`` + ``"vs_references_summary"`` — validation, reference,
  and map benchmarks.
* ``"reported"`` — intercomparison benchmarks (value or identification).

Public symbols
--------------
``score_one_value``
    Value benchmarks (validation / reference / intercomparison).
``score_one_identification``
    Intercomparison identification benchmarks (distribution-only).
``score_one_identification_vs_reference``
    Reference/validation identification benchmarks (not yet implemented).
``score_one_map``
    Map benchmarks (reference / validation).
``make_extract_fn``
    Return the right ``extract_fn`` argument for
    :func:`~scoring.compile.compile_all`.
``RUNNERS``
    Dispatch table: ``(reference_type, data_type)`` → runner callable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scoring.benchmark import BenchmarkConfig
from scoring.compile import _make_extract_fn, load_yaml
from scoring.metrics.value_metrics import abs_error, rel_error_pct, mae, rmse
from scoring.metrics.identification_metrics import distribution_stats
from scoring.metrics.map_metrics import mean_distance_error, pixel_f1


# ---------------------------------------------------------------------------
# metric dispatch tables
# ---------------------------------------------------------------------------

#: Mapping from metric name (as written in ``benchmark.yaml``) to the
#: corresponding value-metric function.
VALUE_METRIC_FNS = {
    "abs_error":     abs_error,
    "rel_error_pct": rel_error_pct,
    "mae":           mae,
    "rmse":          rmse,
}

#: Mapping from metric name (as written in ``benchmark.yaml``) to the
#: corresponding map-metric function.
MAP_METRIC_FNS = {
    "mean_distance_error_m": mean_distance_error,
    "pixel_f1":              pixel_f1,
}

#: Map metrics that require the benchmark raster as a third argument.
_MAP_METRICS_NEEDING_MASK = {"pixel_f1"}


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _get_nested(d: dict, dotted_path: str):
    """
    Traverse *d* by a dotted key path and return the leaf value.

    For example, ``_get_nested(scores, "pixel_f1.f1")`` is equivalent to
    ``scores["pixel_f1"]["f1"]``.

    Parameters
    ----------
    d:
        A (possibly nested) dict.
    dotted_path:
        A dot-separated key path.

    Returns
    -------
    object
        The value at the leaf of the path.

    Raises
    ------
    KeyError
        If any key in the path is absent.
    """
    obj = d
    for key in dotted_path.split("."):
        obj = obj[key]
    return obj


def _summarise_across_refs(per_ref: dict[str, dict], metrics: list[dict]) -> dict:
    """
    Compute mean and std across references for each configured metric.

    Called when ``≥2`` references exist.

    Parameters
    ----------
    per_ref:
        ``vs_references`` dict: ``{ref_key: {metric_name: value_or_nested_dict}}``.
    metrics:
        List of metric config dicts from ``scoring.metrics`` in
        ``benchmark.yaml``.  Each dict has a ``name`` key and an optional
        ``result_path`` key.  ``result_path`` is a dotted path into the
        per-ref dict that locates the scalar to aggregate (e.g.
        ``"pixel_f1.f1"``); when absent the metric value is assumed to be a
        flat scalar stored directly under ``name``.

    Returns
    -------
    dict
        ``{metric_name: {"mean": float, "std": float}}``
    """
    summary: dict = {}
    for m in metrics:
        name        = m["name"]
        result_path = m.get("result_path")
        vals: list[float] = []
        for ref_scores in per_ref.values():
            try:
                scalar = (
                    _get_nested(ref_scores, result_path) if result_path
                    else ref_scores[name]
                )
                vals.append(float(scalar))
            except (KeyError, TypeError):
                continue
        if vals:
            arr = np.array(vals, dtype=float)
            summary[name] = {
                "mean": round(float(np.mean(arr)), 6),
                "std":  round(float(np.std(arr, ddof=0)), 6),
            }
    return summary


# ---------------------------------------------------------------------------
# value runner
# ---------------------------------------------------------------------------

def score_one_value(submission_path: Path, config: BenchmarkConfig) -> dict:
    """
    Score a value benchmark submission.

    Handles all three reference types:

    * **validation / reference** — ``fields`` is a dict mapping field name to
      its known or expert truth value; configured metrics are computed against
      each target.  Results are returned under ``vs_references``.
    * **intercomparison** — ``fields`` is a list of field names; submitted
      values are collected as-is with no comparison.  Results are returned
      under ``reported``.

    Parameters
    ----------
    submission_path:
        Path to the submission ``results.yaml``.
    config:
        Loaded :class:`~scoring.benchmark.BenchmarkConfig`.

    Returns
    -------
    dict
        Normalised scoring dict with ``"submission"``, ``"benchmark"``, and
        either ``"vs_references"`` + ``"vs_references_summary"`` (validation /
        reference) or ``"reported"`` (intercomparison).

    Raises
    ------
    ValueError
        If the config has no ``references:`` block, if a required key is
        missing from the submission, or if a metric name is not recognised.
    """
    submission_path = Path(submission_path)

    if config.references is None:
        raise ValueError(
            f"Value benchmark '{config.slug}' has no 'references:' block in "
            "benchmark.yaml."
        )

    submission_data = load_yaml(submission_path)
    metrics_config: list[dict] = config.scoring.get("metrics", [])

    result: dict = {
        "submission": str(submission_path),
        "benchmark":  config.slug,
    }

    if config.reference_type == "intercomparison":
        # Collect submitted field values as-is — no comparison target.
        reported: dict = {}
        for ref_key, ref_entry in config.references.items():
            fields = ref_entry.fields
            if not isinstance(fields, list):
                raise ValueError(
                    f"[{config.slug}] Reference '{ref_key}': expected 'fields' to be a "
                    f"list for an intercomparison benchmark, got "
                    f"{type(fields).__name__}."
                )
            if ref_key not in submission_data:
                raise ValueError(
                    f"[{config.slug}] Submission {submission_path} is missing "
                    f"top-level key '{ref_key}'."
                )
            ref_submission = submission_data[ref_key]
            reported[ref_key] = {}
            for field_name in fields:
                if field_name not in ref_submission:
                    raise ValueError(
                        f"[{config.slug}] Submission {submission_path}: field "
                        f"'{field_name}' missing under '{ref_key}'."
                    )
                reported[ref_key][field_name] = float(ref_submission[field_name])
        result["reported"] = reported

    else:
        # validation or reference — fields is a dict: {field_name: truth_value}
        vs_references: dict = {}
        for ref_key, ref_entry in config.references.items():
            fields = ref_entry.fields
            if not isinstance(fields, dict):
                raise ValueError(
                    f"[{config.slug}] Reference '{ref_key}': expected 'fields' to be a "
                    f"dict for a {config.reference_type} benchmark, got "
                    f"{type(fields).__name__}."
                )
            if ref_key not in submission_data:
                raise ValueError(
                    f"[{config.slug}] Submission {submission_path} is missing "
                    f"top-level key '{ref_key}'."
                )
            ref_submission = submission_data[ref_key]
            ref_scores: dict = {}

            for field_name, truth_value in fields.items():
                if field_name not in ref_submission:
                    raise ValueError(
                        f"[{config.slug}] Submission {submission_path}: field "
                        f"'{field_name}' missing under '{ref_key}'."
                    )
                submitted_value = float(ref_submission[field_name])
                truth_value     = float(truth_value)
                ref_scores[f"{field_name}_reference"] = truth_value
                ref_scores[f"{field_name}_submitted"] = submitted_value

                for m in metrics_config:
                    metric_name = m["name"]
                    fn = VALUE_METRIC_FNS.get(metric_name)
                    if fn is None:
                        raise ValueError(
                            f"[{config.slug}] Unknown value metric '{metric_name}'. "
                            f"Available: {sorted(VALUE_METRIC_FNS)}."
                        )
                    ref_scores[metric_name] = round(fn(submitted_value, truth_value), 6)

            vs_references[ref_key] = ref_scores

        summary: dict = {}
        if len(vs_references) >= 2 and metrics_config:
            summary = _summarise_across_refs(vs_references, metrics_config)

        result["vs_references"]         = vs_references
        result["vs_references_summary"] = summary

    return result


# ---------------------------------------------------------------------------
# identification runner — distribution-only (intercomparison)
# ---------------------------------------------------------------------------

def score_one_identification(submission_path: Path, config: BenchmarkConfig) -> dict:
    """
    Score an intercomparison identification benchmark submission.

    Loads the submission CSV, validates that all columns declared in
    ``scoring.columns`` are present, and computes distribution statistics for
    each column.  Returns results under ``reported``.

    ``n_bedforms`` (total row count) is included as a top-level key inside
    ``reported`` alongside the per-column stats.

    Parameters
    ----------
    submission_path:
        Path to the submission ``results.csv``.
    config:
        Loaded :class:`~scoring.benchmark.BenchmarkConfig`.

    Returns
    -------
    dict
        Normalised scoring dict with ``"submission"``, ``"benchmark"``, and
        ``"reported"``.

    Raises
    ------
    ValueError
        If the CSV cannot be read or is missing required columns.
    """
    submission_path = Path(submission_path)
    columns: list[str] = config.scoring.get("columns", [])

    try:
        df = pd.read_csv(submission_path)
    except Exception as exc:
        raise ValueError(
            f"[{config.slug}] Could not read submission CSV "
            f"{submission_path}: {exc}"
        ) from exc

    missing_cols = [c for c in columns if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"[{config.slug}] Submission {submission_path} is missing required "
            f"columns: {missing_cols}.  Found: {list(df.columns)}"
        )

    reported: dict = {"n_bedforms": int(len(df))}
    for col in columns:
        reported[col] = distribution_stats(df[col])

    return {
        "submission": str(submission_path),
        "benchmark":  config.slug,
        "reported":   reported,
    }


# ---------------------------------------------------------------------------
# identification runner — vs. reference (future)
# ---------------------------------------------------------------------------

def score_one_identification_vs_reference(
    submission_path: Path,
    config: BenchmarkConfig,
) -> dict:
    """
    Score a reference/validation identification benchmark.

    .. note::
        **Not yet implemented.**  This combination requires new metric
        functions (detection F1 with configurable matching, per-attribute MAE
        on matched pairs) that do not yet exist in
        ``scoring/metrics/identification_metrics.py``.  See
        ``SCORING_REFACTOR_PLAN.md`` Step 3 for the planned design.

    Raises
    ------
    NotImplementedError
        Always.
    """
    raise NotImplementedError(
        f"[{config.slug}] The ({config.reference_type!r}, 'identification') runner "
        "is not yet implemented.  See SCORING_REFACTOR_PLAN.md Step 3 for details."
    )


# ---------------------------------------------------------------------------
# map runner
# ---------------------------------------------------------------------------

def score_one_map(submission_path: Path, config: BenchmarkConfig) -> dict:
    """
    Score a map benchmark submission against all configured reference GeoJSONs.

    Calls each metric function listed in ``scoring.metrics`` for every
    reference entry.  When ``≥2`` references exist the results are aggregated
    into ``vs_references_summary`` using ``result_path`` pointers declared in
    the metric config.

    The benchmark raster (``scoring.raster_grid``) must exist on disk — it is
    required by the ``pixel_f1`` metric.

    Parameters
    ----------
    submission_path:
        Path to the submission GeoJSON.
    config:
        Loaded :class:`~scoring.benchmark.BenchmarkConfig`.

    Returns
    -------
    dict
        Normalised scoring dict with ``"submission"``, ``"benchmark"``,
        ``"vs_references"``, and ``"vs_references_summary"``.

    Raises
    ------
    ValueError
        If the config has no ``references:`` block, a reference entry has no
        ``file:`` key, or a metric name is not recognised.
    FileNotFoundError
        If the benchmark raster or a reference GeoJSON does not exist on disk.
    """
    submission_path = Path(submission_path)

    if config.references is None:
        raise ValueError(
            f"Map benchmark '{config.slug}' has no 'references:' block in "
            "benchmark.yaml."
        )

    metrics_config: list[dict] = config.scoring.get("metrics", [])

    # Resolve and validate the benchmark raster path.
    raster_grid_rel: str | None = config.scoring.get("raster_grid")
    if not raster_grid_rel:
        raise ValueError(
            f"[{config.slug}] 'scoring.raster_grid' is not set in benchmark.yaml."
        )
    mask_path = (config.benchmark_dir / raster_grid_rel).resolve()
    if not mask_path.exists():
        raise FileNotFoundError(
            f"[{config.slug}] Benchmark raster not found: {mask_path}\n"
            f"  This file is not committed to git.  Obtain it as described in "
            f"the benchmark README and place it at:\n  {mask_path}"
        )

    vs_references: dict = {}
    for ref_key, ref_entry in config.references.items():
        if ref_entry.file is None:
            raise ValueError(
                f"[{config.slug}] Reference '{ref_key}' has no 'file:' key in "
                "benchmark.yaml."
            )
        ref_path = (config.benchmark_dir / ref_entry.file).resolve()
        if not ref_path.exists():
            raise FileNotFoundError(
                f"[{config.slug}] Reference GeoJSON not found: {ref_path}"
            )

        ref_scores: dict = {}
        for m in metrics_config:
            metric_name = m["name"]
            fn = MAP_METRIC_FNS.get(metric_name)
            if fn is None:
                raise ValueError(
                    f"[{config.slug}] Unknown map metric '{metric_name}'. "
                    f"Available: {sorted(MAP_METRIC_FNS)}."
                )
            if metric_name in _MAP_METRICS_NEEDING_MASK:
                ref_scores[metric_name] = fn(submission_path, ref_path, mask_path)
            else:
                ref_scores[metric_name] = fn(submission_path, ref_path)

        vs_references[ref_key] = ref_scores

    summary: dict = {}
    if len(vs_references) >= 2 and metrics_config:
        summary = _summarise_across_refs(vs_references, metrics_config)

    return {
        "submission":            str(submission_path),
        "benchmark":             config.slug,
        "vs_references":         vs_references,
        "vs_references_summary": summary,
    }


# ---------------------------------------------------------------------------
# compile extract-fn helper
# ---------------------------------------------------------------------------

def make_extract_fn(config: BenchmarkConfig):
    """
    Return the right ``extract_fn`` to pass to :func:`~scoring.compile.compile_all`.

    For most benchmark types the generic
    :func:`~scoring.compile._make_extract_fn` result (built inside
    :func:`~scoring.compile.compile_all` when ``extract_fn=None``) is correct.
    Map benchmarks additionally inject ``geojson_files`` into each compiled
    record so the website display layer can render the submission polyline.

    Parameters
    ----------
    config:
        The loaded :class:`~scoring.benchmark.BenchmarkConfig`.

    Returns
    -------
    Callable or None
        ``None`` for all non-map benchmarks — :func:`~scoring.compile.compile_all`
        will then build its own extract function automatically.
        A wrapper callable for map benchmarks that adds ``geojson_files`` on
        top of the standard ``vs_references`` / ``vs_references_summary`` fields.
    """
    if config.data_type != "map":
        return None   # compile_all uses _make_extract_fn(config) automatically

    benchmark_dir = config.benchmark_dir
    base_extract  = _make_extract_fn(config)

    def _map_extract(score_data: dict, submission_path: Path) -> dict:
        record = base_extract(score_data, submission_path)
        try:
            rel = submission_path.relative_to(benchmark_dir).as_posix()
        except ValueError:
            rel = str(submission_path)
        record["geojson_files"] = [rel]
        return record

    return _map_extract


# ---------------------------------------------------------------------------
# dispatch table
# ---------------------------------------------------------------------------

RUNNERS: dict[tuple[str, str], object] = {
    # ── value ─────────────────────────────────────────────────────────────
    ("validation",      "value"):          score_one_value,
    ("reference",       "value"):          score_one_value,
    ("intercomparison", "value"):          score_one_value,

    # ── identification ────────────────────────────────────────────────────
    # distribution-only (no ground truth):
    ("intercomparison", "identification"): score_one_identification,
    # vs. reference (future — requires new detection metrics):
    ("reference",       "identification"): score_one_identification_vs_reference,
    ("validation",      "identification"): score_one_identification_vs_reference,

    # ── map ───────────────────────────────────────────────────────────────
    ("reference",       "map"):            score_one_map,
    ("validation",      "map"):            score_one_map,   # future-proof
}
