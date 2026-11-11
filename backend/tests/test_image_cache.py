import pytest

from app.ai.image_cache import GeneratedImage, ImageCache, cache_key, sniff_media_type
from app.ai.image_prompt import ImageRequest

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 20


def request(**overrides):
    values = {"prompt": "a creature", "seed": 1}
    values.update(overrides)
    return ImageRequest(**values)


@pytest.mark.parametrize(
    "data, expected",
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (WEBP, "image/webp"),
        (b"<html>error</html>", None),
        (b"", None),
    ],
)
def test_a_picture_is_recognised_by_its_first_bytes(data, expected):
    assert sniff_media_type(data) == expected


def test_the_same_request_always_has_the_same_key():
    assert cache_key(request(), "flux") == cache_key(request(), "flux")


@pytest.mark.parametrize(
    "changed",
    [{"prompt": "another creature"}, {"seed": 2}, {"width": 512}, {"height": 512}],
)
def test_any_change_to_the_request_changes_the_key(changed):
    assert cache_key(request(**changed), "flux") != cache_key(request(), "flux")


def test_a_different_model_changes_the_key():
    assert cache_key(request(), "flux") != cache_key(request(), "turbo")


def test_a_missing_entry_is_a_miss(tmp_path):
    assert ImageCache(tmp_path).get("nothing") is None


def test_a_stored_picture_comes_back_unchanged(tmp_path):
    cache = ImageCache(tmp_path)
    cache.put("k", JPEG)
    assert cache.get("k") == GeneratedImage(data=JPEG, media_type="image/jpeg")


def test_put_returns_the_validated_picture(tmp_path):
    stored = ImageCache(tmp_path).put("k", PNG)
    assert stored == GeneratedImage(data=PNG, media_type="image/png")


def test_the_cache_folder_is_created_on_demand(tmp_path):
    folder = tmp_path / "a" / "b"
    ImageCache(folder).put("k", PNG)
    assert (folder / "k.img").is_file()


def test_a_corrupt_entry_is_forgotten(tmp_path):
    (tmp_path / "k.img").write_bytes(b"not a picture")
    cache = ImageCache(tmp_path)
    assert cache.get("k") is None
    assert not (tmp_path / "k.img").exists()


def test_storing_leaves_no_temporary_files_behind(tmp_path):
    ImageCache(tmp_path).put("k", JPEG)
    assert [path.name for path in tmp_path.iterdir()] == ["k.img"]


def test_entries_do_not_overwrite_each_other(tmp_path):
    cache = ImageCache(tmp_path)
    cache.put("a", JPEG)
    cache.put("b", PNG)
    assert cache.get("a").data == JPEG
    assert cache.get("b").data == PNG


def test_something_that_is_not_a_picture_is_refused_and_nothing_is_written(tmp_path):
    with pytest.raises(ValueError):
        ImageCache(tmp_path).put("k", b"<html>error</html>")
    assert not any(tmp_path.iterdir())


def test_a_key_that_could_escape_the_folder_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ImageCache(tmp_path).get("../secret")