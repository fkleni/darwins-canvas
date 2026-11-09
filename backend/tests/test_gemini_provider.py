from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors
from pydantic import BaseModel

from app.ai.gemini import DEFAULT_MODEL, GeminiProvider
from app.ai.provider import (
    LLMError,
    LLMInvalidOutputError,
    LLMProvider,
    LLMQuotaError,
    LLMUnavailableError,
)


class Greeting(BaseModel):
    text: str


class StubModels:
    """Stands in for client.models: returns a prepared text or raises a prepared error."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return SimpleNamespace(text=self.outcome)


class StubClient:
    def __init__(self, outcome):
        self.models = StubModels(outcome)


def provider_returning(outcome):
    client = StubClient(outcome)
    return GeminiProvider(client=client), client


def api_error(kind, code):
    return kind(code, {"error": {"message": "test failure"}}, None)


def test_returns_a_validated_model_from_json_text():
    provider, _ = provider_returning('{"text": "hello"}')
    assert provider.generate("hi", Greeting) == Greeting(text="hello")


def test_sends_the_prompt_schema_and_model_to_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    provider, client = provider_returning('{"text": "hello"}')
    provider.generate("say hi", Greeting)
    call = client.models.calls[0]
    assert call["contents"] == "say hi"
    assert call["model"] == DEFAULT_MODEL
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"] == Greeting.model_json_schema()


def test_the_model_name_can_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "some-other-model")
    provider, client = provider_returning('{"text": "hello"}')
    provider.generate("x", Greeting)
    assert client.models.calls[0]["model"] == "some-other-model"


@pytest.mark.parametrize("bad_text", [None, "", "not json at all", '{"wrong": 1}'])
def test_unusable_text_becomes_an_invalid_output_error(bad_text):
    provider, _ = provider_returning(bad_text)
    with pytest.raises(LLMInvalidOutputError):
        provider.generate("x", Greeting)


def test_http_429_becomes_a_quota_error():
    provider, _ = provider_returning(api_error(errors.ClientError, 429))
    with pytest.raises(LLMQuotaError):
        provider.generate("x", Greeting)


@pytest.mark.parametrize("code", [500, 503])
def test_server_side_errors_become_unavailable_errors(code):
    provider, _ = provider_returning(api_error(errors.ServerError, code))
    with pytest.raises(LLMUnavailableError):
        provider.generate("x", Greeting)


def test_network_failures_become_unavailable_errors():
    provider, _ = provider_returning(httpx.ConnectError("no network"))
    with pytest.raises(LLMUnavailableError):
        provider.generate("x", Greeting)


@pytest.mark.parametrize("code", [400, 401, 404])
def test_client_mistakes_stay_plain_llm_errors(code):
    provider, _ = provider_returning(api_error(errors.ClientError, code))
    with pytest.raises(LLMError) as caught:
        provider.generate("x", Greeting)
    assert type(caught.value) is LLMError

def test_a_missing_api_key_fails_early(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError):
        GeminiProvider()


def test_satisfies_the_provider_interface():
    provider, _ = provider_returning("{}")
    assert isinstance(provider, LLMProvider)