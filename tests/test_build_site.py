import json
from argparse import Namespace

import build_site
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


def test_build_site_uses_configured_slug_for_page_path(tmp_path, monkeypatch):
    benchmark_dir = tmp_path / "source-directory"
    benchmark_dir.mkdir()
    (benchmark_dir / "benchmark.yaml").write_text(
        'name: Example\n'
        'slug: public-route\n'
        'reference_type: reference\n'
        'data_type: value\n'
        'submission:\n'
        '  file_pattern: results.yaml\n',
        encoding="utf-8",
    )
    output_dir = tmp_path / "site"

    monkeypatch.setattr(build_site, "discover_benchmarks", lambda: [benchmark_dir])
    monkeypatch.setattr(
        build_site,
        "parse_args",
        lambda: Namespace(slug="public-route", no_index=False, output_dir=output_dir),
    )

    build_site.main()

    assert (output_dir / "benchmarks" / "public-route" / "index.html").is_file()
    assert not (output_dir / "benchmarks" / "source-directory" / "index.html").exists()
    index = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="benchmarks/public-route/"' in index
