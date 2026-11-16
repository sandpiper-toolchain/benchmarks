from build_site import display_image_for


def test_display_image_for_non_map_benchmark(tmp_path):
    image = tmp_path / "display.png"
    image.write_bytes(b"preview")

    assert display_image_for(tmp_path, "value") == "display.png"
    assert display_image_for(tmp_path, "map") is None


def test_display_image_for_missing_image(tmp_path):
    assert display_image_for(tmp_path, "identification") is None
