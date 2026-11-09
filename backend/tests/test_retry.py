import pytest
from pydantic import BaseModel

from app.ai.fake import FakeProvider
from app.ai.provider import (
    LLMError,
    LLMInvalidOutputError,
    LLMQuotaError,
    LLMUnavailableError,
)
from app.ai.retry import BASE_DELAY, MAX_ATTEMPTS, generate_with_retry


class Greeting(BaseModel):
    text: str


GOOD = {"text": "hello"}
BAD = {"wrong": 1}  # does not fit Greeting, so the provider reports invalid output


class RecordedSleeps:
    """Stands in for time.sleep: remembers the delays instead of waiting."""

    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


def run(responses):
    provider = FakeProvider(responses)
    sleeps = RecordedSleeps()
    return provider, sleeps, lambda: generate_with_retry(provider, "ask", Greeting, sleep=sleeps)


def test_a_first_try_success_needs_no_retry_and_no_waiting():
    provider, sleeps, call = run([GOOD])
    assert call() == Greeting(text="hello")
    assert len(provider.prompts) == 1
    assert sleeps.delays == []


def test_invalid_output_is_retried_without_waiting():
    provider, sleeps, call = run([BAD, GOOD])
    assert call() == Greeting(text="hello")
    assert len(provider.prompts) == 2
    assert sleeps.delays == []


def test_the_retry_prompt_shows_the_model_what_was_wrong():
    provider, _, call = run([BAD, GOOD])
    call()
    assert provider.prompts[0] == "ask"
    assert provider.prompts[1].startswith("ask")
    assert "rejected" in provider.prompts[1]


def test_repair_notes_do_not_pile_up_between_retries():
    provider, _, call = run([BAD, BAD, GOOD])
    call()
    assert provider.prompts[2].count("rejected") == 1


def test_unavailable_is_retried_after_a_wait_with_the_same_prompt():
    provider, sleeps, call = run([LLMUnavailableError("down"), GOOD])
    assert call() == Greeting(text="hello")
    assert sleeps.delays == [BASE_DELAY]
    assert provider.prompts[1] == provider.prompts[0]


def test_the_wait_doubles_after_each_failure():
    _, sleeps, call = run([LLMUnavailableError("down"), LLMUnavailableError("down"), GOOD])
    call()
    assert sleeps.delays == [BASE_DELAY, BASE_DELAY * 2]


def test_it_gives_up_on_invalid_output_after_the_attempt_limit():
    provider, _, call = run([BAD] * MAX_ATTEMPTS)
    with pytest.raises(LLMInvalidOutputError):
        call()
    assert len(provider.prompts) == MAX_ATTEMPTS


def test_it_gives_up_on_unavailable_after_the_limit_without_a_final_wait():
    provider, sleeps, call = run([LLMUnavailableError("down")] * MAX_ATTEMPTS)
    with pytest.raises(LLMUnavailableError):
        call()
    assert len(provider.prompts) == MAX_ATTEMPTS
    assert len(sleeps.delays) == MAX_ATTEMPTS - 1


@pytest.mark.parametrize("error", [LLMQuotaError("limit"), LLMError("rejected")])
def test_quota_and_other_errors_are_never_retried(error):
    provider, sleeps, call = run([error, GOOD])
    with pytest.raises(type(error)):
        call()
    assert len(provider.prompts) == 1
    assert sleeps.delays == []