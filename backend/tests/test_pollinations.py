import logging
import threading
from types import SimpleNamespace
from urllib.parse import quote

import httpx
import pytest

from app.ai.image_cache import GeneratedImage
from app.ai.image_prompt import ImageRequest
from app.ai.pollinations import (
    BASE_DELAY,
    DEFAULT_BASE_URL,
    MAX_ATTEMPTS,
    ImageError,
    ImageUnavailableError,
    PollinationsClient,
)

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
REQUEST = ImageRequest(prompt="a creature, with spots & stripes", seed=7, width=512, height=512)
OTHER = ImageRequest(prompt="another creature", seed=8)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in (
        "POLLINATIONS_BASE_URL",
        "POLLINATIONS_API_KEY",
        "POLLINATIONS_MODEL",
        "POLLINATIONS_MIN_INTERVAL",
    ):
        monkeypatch.delenv(name, raising=False)


class StubHttp:
    """Stands in for httpx.get: plays prepared answers and remembers every call."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClock:
    """Time that only moves when someone sleeps."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def ok(data=JPEG):
    return SimpleNamespace(status_code=200, content=data)


def status(code):
    return SimpleNamespace(status_code=code, content=b"")


def make_client(outcomes, **options):
    http = StubHttp(outcomes)
    clock = FakeClock()
    client = PollinationsClient(http_get=http, sleep=clock.sleep, clock=clock, **options)
    return client, http, clock


def test_a_picture_is_downloaded_and_returned():
    client, http, _ = make_client([ok()])
    assert client.download(REQUEST) == GeneratedImage(data=JPEG, media_type="image/jpeg")
    assert len(http.calls) == 1


def test_the_prompt_goes_into_the_url_and_the_rest_into_parameters():
    client, http, _ = make_client([ok()])
    client.download(REQUEST)
    url, kwargs = http.calls[0]
    assert url == f"{DEFAULT_BASE_URL}/{quote(REQUEST.prompt, safe='')}"
    assert "%26" in url  # the ampersand in the prompt cannot be mistaken for a parameter
    assert kwargs["params"] == {
        "width": 512,
        "height": 512,
        "seed": 7,
        "model": "flux",
        "safe": "true",
        "private": "true",
        "nologo": "true",
    }


def test_the_model_name_is_exposed():
    client, _, _ = make_client([])
    assert client.model == "flux"


def test_safe_mode_can_be_switched_off():
    client, http, _ = make_client([ok()], safe=False)
    client.download(REQUEST)
    assert http.calls[0][1]["params"]["safe"] == "false"


def test_an_api_key_is_sent_as_a_bearer_token():
    client, http, _ = make_client([ok()], api_key="secret")
    client.download(REQUEST)
    assert http.calls[0][1]["headers"] == {"Authorization": "Bearer secret"}


def test_without_an_api_key_no_authorization_header_is_sent():
    client, http, _ = make_client([ok()])
    client.download(REQUEST)
    assert http.calls[0][1]["headers"] == {}


def test_the_address_and_model_can_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("POLLINATIONS_BASE_URL", "https://example.test/img/")
    monkeypatch.setenv("POLLINATIONS_MODEL", "turbo")
    client, http, _ = make_client([ok()])
    client.download(REQUEST)
    url, kwargs = http.calls[0]
    assert url.startswith("https://example.test/img/a%20creature")
    assert kwargs["params"]["model"] == "turbo"
    assert client.model == "turbo"


def test_a_second_download_waits_for_the_minimum_interval():
    client, _, clock = make_client([ok(), ok()], min_interval=15.0)
    client.download(REQUEST)
    client.download(OTHER)
    assert clock.sleeps == [15.0]


def test_no_waiting_when_enough_time_has_already_passed():
    client, _, clock = make_client([ok(), ok()], min_interval=15.0)
    client.download(REQUEST)
    clock.now += 20
    client.download(OTHER)
    assert clock.sleeps == []


def test_simultaneous_downloads_are_spaced_out_not_sent_together():
    client, http, clock = make_client([ok(), ok()], min_interval=15.0)
    threads = [
        threading.Thread(target=lambda request=request: client.download(request))
        for request in (REQUEST, OTHER)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(http.calls) == 2
    assert clock.sleeps == [15.0]


def test_a_busy_service_is_retried_after_a_backoff_that_also_respects_the_spacing():
    client, http, clock = make_client([status(503), ok()], min_interval=15.0)
    assert client.download(REQUEST).media_type == "image/jpeg"
    assert len(http.calls) == 2
    assert clock.sleeps == [BASE_DELAY, 15.0 - BASE_DELAY]


@pytest.mark.parametrize("code", [402, 429])
def test_quota_style_statuses_are_treated_as_temporary(code):
    client, http, _ = make_client([status(code), ok()])
    client.download(REQUEST)
    assert len(http.calls) == 2


def test_a_network_failure_is_treated_as_temporary():
    client, http, _ = make_client([httpx.ConnectError("down"), ok()])
    client.download(REQUEST)
    assert len(http.calls) == 2


def test_it_gives_up_after_the_attempt_limit():
    client, http, _ = make_client([status(503)] * MAX_ATTEMPTS)
    with pytest.raises(ImageUnavailableError):
        client.download(REQUEST)
    assert len(http.calls) == MAX_ATTEMPTS


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_our_own_mistakes_are_never_retried(code):
    client, http, _ = make_client([status(code), ok()])
    with pytest.raises(ImageError) as caught:
        client.download(REQUEST)
    assert type(caught.value) is ImageError
    assert len(http.calls) == 1


def test_something_that_is_not_a_picture_is_refused():
    client, _, _ = make_client([ok(b"<html>quota page</html>")])
    with pytest.raises(ImageError):
        client.download(REQUEST)


def test_the_api_key_never_appears_in_an_error_message():
    client, _, _ = make_client([status(500)] * MAX_ATTEMPTS, api_key="secret")
    with pytest.raises(ImageUnavailableError) as caught:
        client.download(REQUEST)
    assert "secret" not in str(caught.value)


def test_a_busy_service_is_a_kind_of_image_error():
    assert issubclass(ImageUnavailableError, ImageError)


def test_waiting_for_the_spacing_is_logged(caplog):
    client, _, _ = make_client([ok(), ok()], min_interval=15.0)
    client.download(REQUEST)
    with caplog.at_level(logging.INFO, logger="app.ai.pollinations"):
        client.download(OTHER)
    assert "waiting 15s" in caplog.text


def test_a_temporary_failure_is_logged_before_the_retry(caplog):
    client, _, _ = make_client([status(503), ok()])
    with caplog.at_level(logging.WARNING, logger="app.ai.pollinations"):
        client.download(REQUEST)
    assert "retrying in 5s" in caplog.text