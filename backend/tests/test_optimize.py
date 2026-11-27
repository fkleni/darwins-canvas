import os

from PIL import Image

from app.optimize import optimize_picture


def make_noise_picture(path, side=600, file_format="JPEG"):
    """A picture full of random noise, so that it cannot be compressed away to nothing."""
    Image.frombytes("RGB", (side, side), os.urandom(side * side * 3)).save(path, file_format)
    return path


def test_a_large_picture_is_shrunk_to_the_requested_size(tmp_path):
    source = make_noise_picture(tmp_path / "big.jpg")
    target = tmp_path / "out" / "big.webp"
    optimize_picture(source, target, size=256)
    with Image.open(target) as result:
        assert result.size == (256, 256)


def test_the_result_is_a_webp(tmp_path):
    source = make_noise_picture(tmp_path / "big.jpg")
    target = tmp_path / "big.webp"
    optimize_picture(source, target, size=256)
    with Image.open(target) as result:
        assert result.format == "WEBP"


def test_the_result_is_smaller_than_the_source(tmp_path):
    source = make_noise_picture(tmp_path / "big.jpg")
    target = tmp_path / "big.webp"
    optimize_picture(source, target, size=256)
    assert target.stat().st_size < source.stat().st_size


def test_a_small_picture_is_never_enlarged(tmp_path):
    source = make_noise_picture(tmp_path / "small.jpg", side=100)
    target = tmp_path / "small.webp"
    optimize_picture(source, target, size=768)
    with Image.open(target) as result:
        assert result.size == (100, 100)


def test_a_non_square_picture_is_cropped_to_a_square(tmp_path):
    source = tmp_path / "wide.jpg"
    Image.new("RGB", (400, 200), (120, 80, 60)).save(source)
    target = tmp_path / "wide.webp"
    optimize_picture(source, target, size=128)
    with Image.open(target) as result:
        assert result.size == (128, 128)


def test_the_source_file_is_not_modified(tmp_path):
    source = make_noise_picture(tmp_path / "big.jpg")
    before = source.read_bytes()
    optimize_picture(source, tmp_path / "big.webp", size=256)
    assert source.read_bytes() == before


def test_the_target_folder_is_created_when_missing(tmp_path):
    source = make_noise_picture(tmp_path / "big.jpg", side=200)
    target = tmp_path / "a" / "b" / "big.webp"
    optimize_picture(source, target, size=128)
    assert target.is_file()


def test_png_sources_work_too(tmp_path):
    source = make_noise_picture(tmp_path / "big.png", side=200, file_format="PNG")
    target = tmp_path / "big.webp"
    optimize_picture(source, target, size=128)
    with Image.open(target) as result:
        assert result.size == (128, 128)