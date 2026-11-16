import json

from build_site import display_image_for, export_site_assets


def test_display_image_for_non_map_benchmark(tmp_path):
    image = tmp_path / "display.png"
    image.write_bytes(b"preview")

    assert display_image_for(tmp_path, "value") == "display.png"
    assert display_image_for(tmp_path, "map") is None


def test_display_image_for_missing_image(tmp_path):
    assert display_image_for(tmp_path, "identification") is None


def test_export_site_assets_copies_results_and_map_inputs(tmp_path, capsys):
    benchmark_dir = tmp_path / "source"
    output_dir = tmp_path / "site" / "benchmarks" / "shoreline"
    (benchmark_dir / "submissions" / "method").mkdir(parents=True)
    (benchmark_dir / "data").mkdir()
    (benchmark_dir / "submissions" / "method" / "line.geojson").write_text(
        '{"type":"FeatureCollection","features":[]}', encoding="utf-8"
    )
    (benchmark_dir / "data" / "reference.geojson").write_text(
        '{"type":"FeatureCollection","features":[]}', encoding="utf-8"
    )
    results = [{"geojson_files": ["submissions/method/line.geojson"]}]

    export_site_assets(
        benchmark_dir,
        output_dir,
        results,
        {
            "map_panel": {
                "reference": {"path": "data/reference.geojson"},
                "raster": "data/missing.tif",
            }
        },
    )

    assert json.loads((output_dir / "results_table.json").read_text()) == results
    assert (output_dir / "submissions" / "method" / "line.geojson").is_file()
    assert (output_dir / "data" / "reference.geojson").is_file()
    assert "optional site asset not found" in capsys.readouterr().err
