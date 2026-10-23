import pytest
from pydantic import BaseModel

from app.ai.fake import FakeProvider
from app.ai.provider import LLMError, LLMInvalidOutputError, LLMProvider


class Greeting(BaseModel):
    text: str


def test_returns_a_validated_model():
    provider = FakeProvider([{"text": "hello"}])
    result = provider.generate("say hi", Greeting)
    assert result == Greeting(text="hello")


def test_records_every_prompt():
    provider = FakeProvider([{"text": "a"}, {"text": "b"}])
    provider.generate("first", Greeting)
    provider.generate("second", Greeting)
    assert provider.prompts == ["first", "second"]


def test_serves_responses_in_order():
    provider = FakeProvider([{"text": "a"}, {"text": "b"}])
    assert provider.generate("x", Greeting).text == "a"
    assert provider.generate("x", Greeting).text == "b"


def test_raises_scripted_errors():
    provider = FakeProvider([LLMError("quota exhausted")])
    with pytest.raises(LLMError):
        provider.generate("x", Greeting)


def test_wraps_invalid_output():
    provider = FakeProvider([{"wrong_field": 1}])
    with pytest.raises(LLMInvalidOutputError):
        provider.generate("x", Greeting)


def test_fails_loudly_when_responses_run_out():
    provider = FakeProvider([])
    with pytest.raises(AssertionError):
        provider.generate("x", Greeting)


def test_satisfies_the_provider_interface():
    assert isinstance(FakeProvider([]), LLMProvider)