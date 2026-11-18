from types import SimpleNamespace

import pytest
from google.genai import errors

from app.ai.gemini import INSPECTION_PROMPT, GeminiImageInspector
from app.ai.image_cache import GeneratedImage
from app.ai.provider import LLMError, LLMInvalidOutputError, LLMQuotaError
from app.ai.retry import BASE_DELAY, MAX_ATTEMPTS
from app.ai.safety import ImageInspector, ImageVerdict

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
IMAGE = GeneratedImage(data=JPEG, media_type="image/jpeg")
GOOD_VERDICT = ImageVerdict(
    shows_nudity=False,
    shows_graphic_violence=False,
    is_off_topic=False,
    reason="A creature illustration.",
)
GOOD_JSON = GOOD_VERDICT.model_dump_json()


class StubModels:
    """Stands in for client.models: plays prepared texts or errors, remembers every call."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class StubClient:
    def __init__(self, outcomes):
        self.models = StubModels(outcomes)


class RecordedSleeps:
    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


def api_error(kind, code):
    return kind(code, {"error": {"message": "test failure"}}, None)


def make_inspector(outcomes):
    client = StubClient(outcomes)
    sleeps = RecordedSleeps()
    return GeminiImageInspector(client=client, sleep=sleeps), client, sleeps


def test_a_verdict_is_parsed_from_the_models_json():
    inspector, _, _ = make_inspector([GOOD_JSON])
    assert inspector.inspect(IMAGE) == GOOD_VERDICT


def test_the_picture_the_instructions_and_a_fixed_temperature_are_sent():
    inspector, client, _ = make_inspector([GOOD_JSON])
    inspector.inspect(IMAGE)
    call = client.models.calls[0]
    picture, instructions = call["contents"]
    assert picture.inline_data.data == JPEG
    assert picture.inline_data.mime_type == "image/jpeg"
    assert instructions == INSPECTION_PROMPT
    assert call["config"]["temperature"] == 0
    assert call["config"]["response_json_schema"] == ImageVerdict.model_json_schema()


def test_a_malformed_answer_is_retried_with_a_note_about_the_mistake():
    inspector, client, _ = make_inspector(["not json at all", GOOD_JSON])
    assert inspector.inspect(IMAGE) == GOOD_VERDICT
    retry_instructions = client.models.calls[1]["contents"][1]
    assert retry_instructions.startswith(INSPECTION_PROMPT)
    assert "rejected" in retry_instructions


def test_it_gives_up_on_malformed_answers_after_the_attempt_limit():
    inspector, client, _ = make_inspector(["nope"] * MAX_ATTEMPTS)
    with pytest.raises(LLMInvalidOutputError):
        inspector.inspect(IMAGE)
    assert len(client.models.calls) == MAX_ATTEMPTS


def test_an_empty_or_blocked_answer_counts_as_invalid_output():
    inspector, _, _ = make_inspector([None] * MAX_ATTEMPTS)
    with pytest.raises(LLMInvalidOutputError):
        inspector.inspect(IMAGE)


def test_a_server_failure_is_retried_after_a_backoff():
    inspector, client, sleeps = make_inspector([api_error(errors.ServerError, 503), GOOD_JSON])
    assert inspector.inspect(IMAGE) == GOOD_VERDICT
    assert len(client.models.calls) == 2
    assert sleeps.delays == [BASE_DELAY]


def test_a_quota_error_is_not_retried():
    inspector, client, _ = make_inspector([api_error(errors.ClientError, 429), GOOD_JSON])
    with pytest.raises(LLMQuotaError):
        inspector.inspect(IMAGE)
    assert len(client.models.calls) == 1


def test_a_missing_api_key_fails_early(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError):
        GeminiImageInspector()


def test_it_satisfies_the_inspector_interface():
    inspector, _, _ = make_inspector([])
    assert isinstance(inspector, ImageInspector)