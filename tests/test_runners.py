"""
End-to-end tests for scoring/runners.py and scoring/compile.py.

Each (reference_type, data_type) combination handled by a registered runner
gets at least one happy-path test plus error-path tests.  Synthetic fixtures
are kept minimal — the smallest data that exercises the code path.

Map tests use a tiny (10×10 pixel) in-memory GeoTIFF so they do not depend on
any gitignored benchmark data files.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
import yaml
from rasterio.transform import from_bounds
from shapely.geometry import LineString

from scoring.benchmark import BenchmarkConfig, ReferenceEntry
from scoring.compile import compile_all
from scoring.runners import (
    RUNNERS,
    make_extract_fn,
    score_one_identification,
    score_one_identification_vs_reference,
    score_one_map,
    score_one_value,
)


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    """Write *data* as YAML to *path*."""
    path.write_text(yaml.dump(data), encoding="utf-8")


def _make_config(
    *,
    benchmark_dir: Path,
    slug: str = "test_bench",
    reference_type: str = "validation",
    data_type: str = "value",
    submission_file_pattern: str = "results.yaml",
    scoring: dict | None = None,
    references: dict[str, ReferenceEntry] | None = None,
) -> BenchmarkConfig:
    """Construct a minimal BenchmarkConfig without touching the filesystem."""
    return BenchmarkConfig(
        name="Test Benchmark",
        slug=slug,
        tagline="A test benchmark",
        domain="fluvial",
        status="active",
        reference_type=reference_type,
        data_type=data_type,
        submission_file_pattern=submission_file_pattern,
        scoring=scoring or {},
        references=references,
        website={},
        benchmark_dir=benchmark_dir,
    )


# ---------------------------------------------------------------------------
# value runner — validation
# ---------------------------------------------------------------------------


class TestScoreOneValueValidation:
    """Tests for score_one_value with reference_type='validation'."""

    def _config(self, tmp_path, refs=None, metrics=None):
        default_refs = {
            "ds_a": ReferenceEntry(label="Dataset A", fields={"kappa": 1.0}),
        }
        default_metrics = [
            {"name": "abs_error"},
            {"name": "rel_error_pct"},
        ]
        return _make_config(
            benchmark_dir=tmp_path,
            reference_type="validation",
            data_type="value",
            scoring={"metrics": metrics if metrics is not None else default_metrics},
            references=refs if refs is not None else default_refs,
        )

    def test_single_ref_schema(self, tmp_path):
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 0.9}})
        config = self._config(tmp_path)

        result = score_one_value(sub, config)

        assert result["submission"] == str(sub)
        assert result["benchmark"] == "test_bench"
        assert "vs_references" in result
        assert "vs_references_summary" in result
        # single ref → summary is empty
        assert result["vs_references_summary"] == {}

    def test_single_ref_values(self, tmp_path):
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 1.1}})
        config = self._config(tmp_path)

        result = score_one_value(sub, config)
        ds = result["vs_references"]["ds_a"]

        assert ds["kappa_reference"] == pytest.approx(1.0)
        assert ds["kappa_submitted"] == pytest.approx(1.1)
        assert ds["abs_error"] == pytest.approx(0.1)
        # |1.1 - 1.0| / 1.0 * 100 = 10 %
        assert ds["rel_error_pct"] == pytest.approx(10.0)

    def test_two_refs_summary_populated(self, tmp_path):
        refs = {
            "ds_a": ReferenceEntry(label="A", fields={"kappa": 1.0}),
            "ds_b": ReferenceEntry(label="B", fields={"kappa": 2.0}),
        }
        config = self._config(tmp_path, refs=refs)
        sub = tmp_path / "results.yaml"
        # Submit kappa=1.1 for ds_a (error 0.1) and kappa=2.1 for ds_b (error 0.1)
        _write_yaml(sub, {"ds_a": {"kappa": 1.1}, "ds_b": {"kappa": 2.1}})

        result = score_one_value(sub, config)

        summary = result["vs_references_summary"]
        assert "abs_error" in summary
        # Both errors are 0.1 → mean=0.1, std=0.0
        assert summary["abs_error"]["mean"] == pytest.approx(0.1)
        assert summary["abs_error"]["std"] == pytest.approx(0.0)

    def test_missing_top_level_key_raises(self, tmp_path):
        sub = tmp_path / "results.yaml"
        # Missing 'ds_a' entirely
        _write_yaml(sub, {"other_key": {"kappa": 0.5}})
        config = self._config(tmp_path)

        with pytest.raises(ValueError, match="missing.*top-level key.*ds_a"):
            score_one_value(sub, config)

    def test_missing_field_raises(self, tmp_path):
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"wrong_field": 0.9}})
        config = self._config(tmp_path)

        with pytest.raises(ValueError, match="'kappa' missing under"):
            score_one_value(sub, config)

    def test_unknown_metric_raises(self, tmp_path):
        config = self._config(tmp_path, metrics=[{"name": "nonexistent_metric"}])
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 1.0}})

        with pytest.raises(ValueError, match="Unknown value metric.*nonexistent_metric"):
            score_one_value(sub, config)

    def test_no_references_raises(self, tmp_path):
        config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="validation",
            data_type="value",
            references=None,
        )
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {})

        with pytest.raises(ValueError, match="no 'references:'"):
            score_one_value(sub, config)

    def test_fields_as_list_raises_for_validation(self, tmp_path):
        """When a validation benchmark accidentally has list fields, raise clearly."""
        refs = {
            "ds_a": ReferenceEntry(label="A", fields=["kappa"]),
        }
        config = self._config(tmp_path, refs=refs)
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 1.0}})

        with pytest.raises(ValueError, match="expected 'fields' to be a dict"):
            score_one_value(sub, config)


# ---------------------------------------------------------------------------
# value runner — reference (same code path as validation)
# ---------------------------------------------------------------------------


class TestScoreOneValueReference:
    def test_basic(self, tmp_path):
        refs = {"ds_a": ReferenceEntry(label="A", fields={"kappa": 0.8})}
        config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="reference",
            data_type="value",
            scoring={"metrics": [{"name": "abs_error"}]},
            references=refs,
        )
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 0.9}})

        result = score_one_value(sub, config)

        assert "vs_references" in result
        assert result["vs_references"]["ds_a"]["abs_error"] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# value runner — intercomparison
# ---------------------------------------------------------------------------


class TestScoreOneValueIntercomparison:
    def _config(self, tmp_path, refs=None):
        default_refs = {
            "ds_a": ReferenceEntry(label="A", fields=["kappa", "Tc"]),
        }
        return _make_config(
            benchmark_dir=tmp_path,
            reference_type="intercomparison",
            data_type="value",
            scoring={},
            references=refs if refs is not None else default_refs,
        )

    def test_basic_reported_schema(self, tmp_path):
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 0.6, "Tc": 15.0}})
        config = self._config(tmp_path)

        result = score_one_value(sub, config)

        assert "reported" in result
        assert "vs_references" not in result
        assert result["reported"]["ds_a"]["kappa"] == pytest.approx(0.6)
        assert result["reported"]["ds_a"]["Tc"] == pytest.approx(15.0)

    def test_missing_top_level_key_raises(self, tmp_path):
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"wrong": {"kappa": 0.6}})
        config = self._config(tmp_path)

        with pytest.raises(ValueError, match="missing.*top-level key.*ds_a"):
            score_one_value(sub, config)

    def test_missing_field_raises(self, tmp_path):
        sub = tmp_path / "results.yaml"
        # Provides kappa but not Tc
        _write_yaml(sub, {"ds_a": {"kappa": 0.6}})
        config = self._config(tmp_path)

        with pytest.raises(ValueError, match="'Tc' missing under"):
            score_one_value(sub, config)

    def test_fields_as_dict_raises_for_intercomparison(self, tmp_path):
        """When an intercomparison benchmark has dict fields, raise clearly."""
        refs = {
            "ds_a": ReferenceEntry(label="A", fields={"kappa": 1.0}),
        }
        config = self._config(tmp_path, refs=refs)
        sub = tmp_path / "results.yaml"
        _write_yaml(sub, {"ds_a": {"kappa": 0.9}})

        with pytest.raises(ValueError, match="expected 'fields' to be a list"):
            score_one_value(sub, config)


# ---------------------------------------------------------------------------
# identification runner — distribution-only (intercomparison)
# ---------------------------------------------------------------------------


class TestScoreOneIdentification:
    def _config(self, tmp_path, columns=None):
        return _make_config(
            benchmark_dir=tmp_path,
            reference_type="intercomparison",
            data_type="identification",
            submission_file_pattern="results.csv",
            scoring={"columns": columns if columns is not None else ["height_m", "length_m"]},
            references=None,
        )

    def test_basic_reported_schema(self, tmp_path):
        import pandas as pd
        sub = tmp_path / "results.csv"
        df = pd.DataFrame({"height_m": [0.5, 1.0, 1.5], "length_m": [5.0, 10.0, 15.0]})
        df.to_csv(sub, index=False)
        config = self._config(tmp_path)

        result = score_one_identification(sub, config)

        assert result["benchmark"] == "test_bench"
        assert "reported" in result
        reported = result["reported"]
        assert reported["n_bedforms"] == 3
        assert "height_m" in reported
        assert "length_m" in reported
        assert reported["height_m"]["mean"] == pytest.approx(1.0)
        assert reported["height_m"]["min"] == pytest.approx(0.5)
        assert reported["height_m"]["max"] == pytest.approx(1.5)

    def test_missing_column_raises(self, tmp_path):
        import pandas as pd
        sub = tmp_path / "results.csv"
        df = pd.DataFrame({"height_m": [0.5, 1.0]})  # missing length_m
        df.to_csv(sub, index=False)
        config = self._config(tmp_path)

        with pytest.raises(ValueError, match="missing required columns.*length_m"):
            score_one_identification(sub, config)

    def test_nonexistent_csv_raises(self, tmp_path):
        config = self._config(tmp_path)
        sub = tmp_path / "does_not_exist.csv"

        with pytest.raises(ValueError, match="Could not read"):
            score_one_identification(sub, config)


# ---------------------------------------------------------------------------
# identification runner — vs. reference (not yet implemented)
# ---------------------------------------------------------------------------


class TestScoreOneIdentificationVsReference:
    def test_reference_raises_not_implemented(self, tmp_path):
        config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="reference",
            data_type="identification",
        )
        sub = tmp_path / "results.csv"
        sub.write_text("height_m\n1.0\n")

        with pytest.raises(NotImplementedError):
            score_one_identification_vs_reference(sub, config)

    def test_validation_raises_not_implemented(self, tmp_path):
        config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="validation",
            data_type="identification",
        )
        sub = tmp_path / "results.csv"
        sub.write_text("height_m\n1.0\n")

        with pytest.raises(NotImplementedError):
            score_one_identification_vs_reference(sub, config)


# ---------------------------------------------------------------------------
# map runner — fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def map_fixture(tmp_path):
    """
    Set up a minimal map benchmark environment:

    * A 10×10 GeoTIFF at EPSG:32648 (500m east, 1000m north)
    * A reference GeoJSON polyline
    * A submission GeoJSON polyline (identical to reference → perfect score)

    Returns ``(config, submission_path)``.
    """
    # Create the directory layout
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sub_dir = tmp_path / "submissions" / "mymethod"
    sub_dir.mkdir(parents=True)

    # --- raster (10 columns × 10 rows, 100 m pixels) ----------------------
    west, north = 400_000.0, 6_100_000.0
    pixel_size = 100.0
    east = west + 10 * pixel_size
    south = north - 10 * pixel_size
    transform = from_bounds(west, south, east, north, width=10, height=10)
    raster_path = data_dir / "mask.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="uint8",
        crs="EPSG:32648",
        transform=transform,
    ) as dst:
        dst.write(np.zeros((1, 10, 10), dtype=np.uint8))

    # --- reference GeoJSON -----------------------------------------------
    ref_line = LineString([(400_100.0, 6_099_500.0), (400_900.0, 6_099_500.0)])
    ref_gdf = gpd.GeoDataFrame(geometry=[ref_line], crs="EPSG:32648")
    ref_path = data_dir / "ref.geojson"
    ref_gdf.to_file(ref_path, driver="GeoJSON")

    # --- submission GeoJSON (identical to reference → near-zero error) ---
    sub_path = sub_dir / "results.geojson"
    ref_gdf.to_file(sub_path, driver="GeoJSON")

    # --- config -----------------------------------------------------------
    config = _make_config(
        benchmark_dir=tmp_path,
        reference_type="reference",
        data_type="map",
        submission_file_pattern="results.geojson",
        scoring={
            "raster_grid": "data/mask.tif",
            "metrics": [
                {"name": "mean_distance_error_m", "direction": "lower_better"},
                {"name": "pixel_f1", "direction": "higher_better", "result_path": "pixel_f1.f1"},
            ],
        },
        references={
            "ref_moodie": ReferenceEntry(
                label="Moodie 2026",
                file="data/ref.geojson",
            ),
        },
    )

    return config, sub_path


# ---------------------------------------------------------------------------
# map runner — tests
# ---------------------------------------------------------------------------


class TestScoreOneMap:
    def test_basic_schema(self, map_fixture):
        config, sub_path = map_fixture

        result = score_one_map(sub_path, config)

        assert result["benchmark"] == "test_bench"
        assert "vs_references" in result
        assert "vs_references_summary" in result
        # Only one reference → summary is empty
        assert result["vs_references_summary"] == {}

    def test_basic_values(self, map_fixture):
        config, sub_path = map_fixture

        result = score_one_map(sub_path, config)

        ref_scores = result["vs_references"]["ref_moodie"]
        # Identical lines → distance error ≈ 0
        assert ref_scores["mean_distance_error_m"] == pytest.approx(0.0, abs=1.0)
        # Identical lines → F1 ≈ 1.0
        assert ref_scores["pixel_f1"]["f1"] == pytest.approx(1.0, abs=0.05)

    def test_missing_raster_raises(self, map_fixture, tmp_path):
        config, sub_path = map_fixture
        # Point to a nonexistent raster
        bad_config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="reference",
            data_type="map",
            scoring={
                "raster_grid": "data/nonexistent.tif",
                "metrics": [],
            },
            references={"ref": ReferenceEntry(label="R", file="data/ref.geojson")},
        )
        with pytest.raises(FileNotFoundError, match="Benchmark raster not found"):
            score_one_map(sub_path, bad_config)

    def test_no_raster_grid_key_raises(self, map_fixture, tmp_path):
        config, sub_path = map_fixture
        bad_config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="reference",
            data_type="map",
            scoring={"metrics": []},  # no raster_grid key
            references={"ref": ReferenceEntry(label="R", file="data/ref.geojson")},
        )
        with pytest.raises(ValueError, match="'scoring.raster_grid' is not set"):
            score_one_map(sub_path, bad_config)

    def test_missing_reference_file_raises(self, map_fixture):
        config, sub_path = map_fixture
        # Override references to point at nonexistent GeoJSON
        bad_config = _make_config(
            benchmark_dir=config.benchmark_dir,
            reference_type="reference",
            data_type="map",
            scoring=config.scoring,
            references={
                "ref_missing": ReferenceEntry(label="Missing", file="data/no_such.geojson"),
            },
        )
        with pytest.raises(FileNotFoundError, match="Reference GeoJSON not found"):
            score_one_map(sub_path, bad_config)

    def test_no_references_raises(self, map_fixture, tmp_path):
        config, sub_path = map_fixture
        bad_config = _make_config(
            benchmark_dir=tmp_path,
            reference_type="reference",
            data_type="map",
            scoring={"raster_grid": "data/mask.tif", "metrics": []},
            references=None,
        )
        with pytest.raises(ValueError, match="no 'references:'"):
            score_one_map(sub_path, bad_config)

    def test_unknown_metric_raises(self, map_fixture):
        config, sub_path = map_fixture
        bad_config = _make_config(
            benchmark_dir=config.benchmark_dir,
            reference_type="reference",
            data_type="map",
            scoring={
                "raster_grid": "data/mask.tif",
                "metrics": [{"name": "nonexistent_map_metric"}],
            },
            references=config.references,
        )
        with pytest.raises(ValueError, match="Unknown map metric.*nonexistent_map_metric"):
            score_one_map(sub_path, bad_config)


# ---------------------------------------------------------------------------
# compile_all integration tests
# ---------------------------------------------------------------------------


def _write_benchmark_yaml(bdir: Path, data: dict) -> None:
    """Write a minimal benchmark.yaml that load_config can read."""
    _write_yaml(bdir / "benchmark.yaml", data)


class TestCompileAll:
    def test_value_validation_compile(self, tmp_path):
        """compile_all produces a results_table.json with the correct schema."""
        from scoring.benchmark import load_config

        bdir = tmp_path / "comp_bench"
        bdir.mkdir()
        _write_benchmark_yaml(
            bdir,
            {
                "name": "Compile Test",
                "slug": "compile_test",
                "tagline": "A compile test",
                "domain": "fluvial",
                "status": "active",
                "reference_type": "validation",
                "data_type": "value",
                "submission": {"file_pattern": "results.yaml"},
                "references": {
                    "ds_a": {
                        "label": "Dataset A",
                        "fields": {"kappa": 1.0},
                    }
                },
                "scoring": {
                    "metrics": [
                        {"name": "abs_error", "direction": "lower_better"},
                    ]
                },
            },
        )

        # Two real submissions
        for method in ("method_alpha", "method_beta"):
            sub_dir = bdir / "submissions" / method
            sub_dir.mkdir(parents=True)
            _write_yaml(sub_dir / "results.yaml", {"ds_a": {"kappa": 0.95}})
            _write_yaml(
                sub_dir / "metadata.yaml",
                {"method_name": method, "author_name": "Tester"},
            )

        # Example directory — must be skipped
        example_dir = bdir / "submissions" / "example"
        example_dir.mkdir(parents=True)
        _write_yaml(example_dir / "results.yaml", {"ds_a": {"kappa": 0.0}})

        config = load_config(bdir)
        dest = compile_all(bdir, config, score_one_value)

        assert dest.exists()
        records = json.loads(dest.read_text())
        assert len(records) == 2  # example skipped

        for rec in records:
            assert rec["method_name"] in ("method_alpha", "method_beta")
            assert "vs_references" in rec
            assert "vs_references_summary" in rec
            assert rec["vs_references"]["ds_a"]["abs_error"] == pytest.approx(0.05)

    def test_identification_compile(self, tmp_path):
        """compile_all works for identification benchmarks."""
        import pandas as pd
        from scoring.benchmark import load_config

        bdir = tmp_path / "id_bench"
        bdir.mkdir()
        _write_benchmark_yaml(
            bdir,
            {
                "name": "ID Compile Test",
                "slug": "id_compile_test",
                "tagline": "Identification compile test",
                "domain": "fluvial",
                "status": "active",
                "reference_type": "intercomparison",
                "data_type": "identification",
                "submission": {"file_pattern": "results.csv"},
                "scoring": {"columns": ["height_m"]},
            },
        )

        sub_dir = bdir / "submissions" / "my_method"
        sub_dir.mkdir(parents=True)
        df = pd.DataFrame({"height_m": [1.0, 2.0, 3.0]})
        df.to_csv(sub_dir / "results.csv", index=False)
        _write_yaml(
            sub_dir / "metadata.yaml",
            {"method_name": "my_method"},
        )

        config = load_config(bdir)
        dest = compile_all(bdir, config, score_one_identification)

        records = json.loads(dest.read_text())
        assert len(records) == 1
        assert records[0]["method_name"] == "my_method"
        assert "reported" in records[0]
        assert records[0]["reported"]["n_bedforms"] == 3

    def test_example_submission_skipped(self, tmp_path):
        """Submissions inside the example/ directory are never scored."""
        import pandas as pd
        from scoring.benchmark import load_config

        bdir = tmp_path / "skip_bench"
        bdir.mkdir()
        _write_benchmark_yaml(
            bdir,
            {
                "name": "Skip Test",
                "slug": "skip_test",
                "tagline": "Skip example test",
                "domain": "fluvial",
                "status": "active",
                "reference_type": "intercomparison",
                "data_type": "identification",
                "submission": {"file_pattern": "results.csv"},
                "scoring": {"columns": ["height_m"]},
            },
        )

        # Only the example/ submission exists — after skipping it, table is empty.
        example_dir = bdir / "submissions" / "example"
        example_dir.mkdir(parents=True)
        pd.DataFrame({"height_m": [1.0]}).to_csv(
            example_dir / "results.csv", index=False
        )

        config = load_config(bdir)
        dest = compile_all(bdir, config, score_one_identification)

        records = json.loads(dest.read_text())
        assert records == []


# ---------------------------------------------------------------------------
# dispatch table
# ---------------------------------------------------------------------------


class TestDispatchTable:
    EXPECTED_KEYS = {
        ("validation",      "value"),
        ("reference",       "value"),
        ("intercomparison", "value"),
        ("intercomparison", "identification"),
        ("reference",       "identification"),
        ("validation",      "identification"),
        ("reference",       "map"),
        ("validation",      "map"),
    }

    def test_all_expected_keys_present(self):
        assert self.EXPECTED_KEYS.issubset(set(RUNNERS.keys()))

    def test_all_values_are_callable(self):
        for key, fn in RUNNERS.items():
            assert callable(fn), f"RUNNERS[{key!r}] is not callable"
