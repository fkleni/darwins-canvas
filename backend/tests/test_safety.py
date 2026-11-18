import threading

import pytest

from app.ai.fake import FakeInspector
from app.ai.image_cache import GeneratedImage, ImageCache, cache_key
from app.ai.image_prompt import STRICT_COVERING, ImageRequest
from app.ai.pollinations import ImageUnavailableError
from app.ai.provider import LLMError, LLMInvalidOutputError, LLMQuotaError, LLMUnavailableError
from app.ai.safety import (
    MAX_PICTURE_ATTEMPTS,
    ImageInspector,
    ImageOutcome,
    ImageVerdict,
    SafeImageService,
)

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
IMAGE = GeneratedImage(data=JPEG, media_type="image/jpeg")
OTHER_IMAGE = GeneratedImage(data=PNG, media_type="image/png")
REQUEST = ImageRequest(prompt="a creature", seed=5)


def verdict(**flags):
    values = {
        "shows_nudity": False,
        "shows_graphic_violence": False,
        "is_off_topic": False,
        "reason": "Verdict prepared for the test.",
    }
    values.update(flags)
    return ImageVerdict(**values)


GOOD = verdict()
BAD = verdict(shows_nudity=True, reason="Rejected by the test.")


class StubDownloader:
    """Plays prepared pictures (or failures) and remembers every request."""

    model = "flux"

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def download(self, request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_service(tmp_path, downloads, verdicts):
    cache = ImageCache(tmp_path)
    downloader = StubDownloader(downloads)
    inspector = FakeInspector(verdicts)
    return SafeImageService(cache, downloader, inspector), downloader, inspector, cache


@pytest.mark.parametrize(
    "flags, acceptable",
    [
        ({}, True),
        ({"shows_nudity": True}, False),
        ({"shows_graphic_violence": True}, False),
        ({"is_off_topic": True}, False),
        ({"shows_nudity": True, "is_off_topic": True}, False),
    ],
)
def test_a_picture_is_acceptable_only_when_no_problem_is_flagged(flags, acceptable):
    assert verdict(**flags).is_acceptable is acceptable


@pytest.mark.parametrize("name", list(ImageVerdict.model_fields))
def test_every_verdict_field_carries_a_description_for_the_model(name):
    assert ImageVerdict.model_fields[name].description


def test_an_approved_picture_is_returned_and_cached(tmp_path):
    service, downloader, inspector, cache = make_service(tmp_path, [IMAGE], [GOOD])
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.APPROVED
    assert result.image == IMAGE
    assert result.attempts == 1
    assert inspector.inspected == [IMAGE]
    assert cache.get(cache_key(REQUEST, "flux")) == IMAGE


def test_the_second_request_comes_from_the_cache_without_any_work(tmp_path):
    service, downloader, inspector, _ = make_service(tmp_path, [IMAGE], [GOOD])
    service.get(REQUEST)
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.CACHED
    assert result.image == IMAGE
    assert len(downloader.requests) == 1
    assert len(inspector.inspected) == 1


def test_a_rejected_picture_is_replaced_by_a_new_attempt_and_never_cached(tmp_path):
    service, downloader, _, cache = make_service(tmp_path, [OTHER_IMAGE, IMAGE], [BAD, GOOD])
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.APPROVED
    assert result.attempts == 2
    assert result.image == IMAGE
    first, second = downloader.requests
    assert first == REQUEST
    assert second.seed != REQUEST.seed
    assert STRICT_COVERING in second.prompt
    assert cache.get(cache_key(REQUEST, "flux")) == IMAGE


def test_when_every_attempt_is_rejected_there_is_no_picture_and_nothing_is_cached(tmp_path):
    service, downloader, _, _ = make_service(
        tmp_path, [IMAGE] * MAX_PICTURE_ATTEMPTS, [BAD] * MAX_PICTURE_ATTEMPTS
    )
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.REJECTED
    assert result.image is None
    assert result.attempts == MAX_PICTURE_ATTEMPTS
    assert result.reason == BAD.reason
    assert len(downloader.requests) == MAX_PICTURE_ATTEMPTS
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize(
    "error",
    [
        LLMError("x"),
        LLMQuotaError("x"),
        LLMUnavailableError("x"),
        LLMInvalidOutputError("x"),
    ],
)
def test_a_picture_that_cannot_be_inspected_is_not_shown_and_not_cached(tmp_path, error):
    service, downloader, _, _ = make_service(tmp_path, [IMAGE, IMAGE], [error])
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.UNVERIFIED
    assert result.image is None
    assert len(downloader.requests) == 1  # no point generating more pictures we cannot check
    assert not any(tmp_path.iterdir())


def test_a_failed_download_is_reported_and_nothing_is_inspected(tmp_path):
    service, _, inspector, _ = make_service(tmp_path, [ImageUnavailableError("down")], [])
    result = service.get(REQUEST)
    assert result.outcome == ImageOutcome.UNAVAILABLE
    assert result.image is None
    assert inspector.inspected == []


def test_two_simultaneous_requests_run_the_pipeline_once(tmp_path):
    service, downloader, _, _ = make_service(tmp_path, [IMAGE], [GOOD])
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(service.get(REQUEST))) for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(downloader.requests) == 1
    assert {result.outcome for result in results} == {ImageOutcome.APPROVED, ImageOutcome.CACHED}


def test_the_fake_inspector_fails_loudly_when_it_runs_out_of_verdicts():
    with pytest.raises(AssertionError):
        FakeInspector([]).inspect(IMAGE)


def test_the_fake_inspector_satisfies_the_inspector_interface():
    assert isinstance(FakeInspector([]), ImageInspector)