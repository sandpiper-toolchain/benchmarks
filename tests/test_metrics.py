"""
Bare-minimum regression tests for the shared scoring metrics library.

These tests use only pure Python / numpy / pandas — no GeoJSON files,
no rasters, no benchmark data.  Their purpose is to anchor the numerical
behaviour of the shared metric functions so accidental regressions are
caught early.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# value_metrics
# ---------------------------------------------------------------------------

from scoring.metrics.value_metrics import abs_error, rel_error_pct, mae, rmse


def test_abs_error_basic():
    assert abs_error(1.2, 1.0) == pytest.approx(0.2)


def test_abs_error_negative_direction():
    assert abs_error(0.8, 1.0) == pytest.approx(0.2)


def test_abs_error_exact():
    assert abs_error(0.5, 0.5) == pytest.approx(0.0)


def test_rel_error_pct_basic():
    # |1.2 - 1.0| / 1.0 * 100 = 20 %
    assert rel_error_pct(1.2, 1.0) == pytest.approx(20.0)


def test_rel_error_pct_half():
    # |0.25 - 0.5| / 0.5 * 100 = 50 %
    assert rel_error_pct(0.25, 0.5) == pytest.approx(50.0)


def test_rel_error_pct_zero_reference_raises():
    with pytest.raises(ValueError, match="zero"):
        rel_error_pct(1.0, 0.0)


def test_mae_basic():
    # errors: [1, 1, 1] → mean = 1
    assert mae([2.0, 3.0, 4.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_mae_mixed():
    assert mae([0.0, 2.0], [1.0, 1.0]) == pytest.approx(1.0)


def test_rmse_basic():
    # errors: [1, 1] → rms = 1
    assert rmse([2.0, 3.0], [1.0, 2.0]) == pytest.approx(1.0)


def test_rmse_mixed():
    # errors: [0, 2] → rms = sqrt(2)
    assert rmse([1.0, 3.0], [1.0, 1.0]) == pytest.approx(math.sqrt(2))


# ---------------------------------------------------------------------------
# identification_metrics
# ---------------------------------------------------------------------------

from scoring.metrics.identification_metrics import distribution_stats


def test_distribution_stats_basic():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = distribution_stats(s)
    assert result["min"]    == pytest.approx(1.0)
    assert result["mean"]   == pytest.approx(3.0)
    assert result["median"] == pytest.approx(3.0)
    assert result["p25"]    == pytest.approx(2.0)
    assert result["p75"]    == pytest.approx(4.0)
    assert result["max"]    == pytest.approx(5.0)
    assert result["std"]    == pytest.approx(1.5811, rel=1e-3)


def test_distribution_stats_empty():
    result = distribution_stats(pd.Series([], dtype=float))
    assert result == {"min": None, "mean": None, "median": None, "std": None, "p25": None, "p75": None, "max": None}


def test_distribution_stats_drops_nan():
    s = pd.Series([1.0, float("nan"), 3.0])
    result = distribution_stats(s)
    assert result["min"]    == pytest.approx(1.0)
    assert result["mean"]   == pytest.approx(2.0)
    assert result["median"] == pytest.approx(2.0)
    assert result["max"]    == pytest.approx(3.0)


def test_distribution_stats_single_value():
    result = distribution_stats(pd.Series([42.0]))
    assert result["min"]    == pytest.approx(42.0)
    assert result["mean"]   == pytest.approx(42.0)
    assert result["median"] == pytest.approx(42.0)
    assert result["max"]    == pytest.approx(42.0)
    assert result["std"]    == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# map_metrics — import smoke test only (functions need rasters/GeoJSON)
# ---------------------------------------------------------------------------

import scoring.metrics.map_metrics as map_metrics_mod


def test_map_metrics_public_api():
    """Confirm the two public metric functions are importable."""
    assert callable(map_metrics_mod.mean_distance_error)
    assert callable(map_metrics_mod.pixel_f1)


# ---------------------------------------------------------------------------
# runner helpers (metric-adjacent)
# ---------------------------------------------------------------------------

from scoring.runners import _get_nested, _summarise_across_refs


def test_get_nested_flat():
    assert _get_nested({"a": 1}, "a") == 1


def test_get_nested_deep():
    assert _get_nested({"a": {"b": {"c": 42}}}, "a.b.c") == 42


def test_get_nested_missing_top_key_raises():
    with pytest.raises(KeyError):
        _get_nested({"a": 1}, "b")


def test_get_nested_missing_deep_key_raises():
    with pytest.raises(KeyError):
        _get_nested({"a": {"b": 1}}, "a.c")


def test_summarise_across_refs_single_ref():
    per_ref = {"ref_a": {"abs_error": 0.1}}
    metrics = [{"name": "abs_error"}]
    result = _summarise_across_refs(per_ref, metrics)
    assert result["abs_error"]["mean"] == pytest.approx(0.1)
    assert result["abs_error"]["std"] == pytest.approx(0.0)


def test_summarise_across_refs_two_refs():
    per_ref = {
        "ref_a": {"abs_error": 0.1},
        "ref_b": {"abs_error": 0.3},
    }
    metrics = [{"name": "abs_error"}]
    result = _summarise_across_refs(per_ref, metrics)
    assert result["abs_error"]["mean"] == pytest.approx(0.2)
    # ddof=0: std = sqrt(((0.1-0.2)^2 + (0.3-0.2)^2) / 2) = 0.1
    assert result["abs_error"]["std"] == pytest.approx(0.1)


def test_summarise_across_refs_with_result_path():
    per_ref = {
        "ref_a": {"pixel_f1": {"f1": 0.9, "precision": 0.95, "recall": 0.86}},
        "ref_b": {"pixel_f1": {"f1": 0.7, "precision": 0.80, "recall": 0.63}},
    }
    metrics = [{"name": "pixel_f1", "result_path": "pixel_f1.f1"}]
    result = _summarise_across_refs(per_ref, metrics)
    assert result["pixel_f1"]["mean"] == pytest.approx(0.8)
    assert result["pixel_f1"]["std"] == pytest.approx(0.1)


def test_summarise_across_refs_missing_key_skipped():
    per_ref = {
        "ref_a": {"abs_error": 0.1},
        "ref_b": {},  # missing metric — silently skipped
    }
    metrics = [{"name": "abs_error"}]
    result = _summarise_across_refs(per_ref, metrics)
    # Only one valid value → mean = 0.1, std = 0.0
    assert result["abs_error"]["mean"] == pytest.approx(0.1)
    assert result["abs_error"]["std"] == pytest.approx(0.0)
