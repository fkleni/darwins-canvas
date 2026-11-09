"""Retrying a language-model call the right way for each kind of failure."""

import time
from collections.abc import Callable

from pydantic import BaseModel

from app.ai.provider import LLMInvalidOutputError, LLMProvider, LLMUnavailableError

MAX_ATTEMPTS = 3  # total tries, shared by every kind of retryable failure
BASE_DELAY = 1.0  # seconds to wait after the first failure; doubles each time


def _repair_prompt(original: str, error: LLMInvalidOutputError) -> str:
    """The original prompt plus a note telling the model what was wrong with its answer."""
    return (
        f"{original}\n\n"
        "Your previous answer was rejected because it did not match the required format:\n"
        f"{str(error)[:600]}\n"
        "Answer again and fix exactly these problems."
    )


def generate_with_retry[T: BaseModel](
    provider: LLMProvider,
    prompt: str,
    schema: type[T],
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Ask the model, retrying only the failures that retrying can fix.

    Invalid output: ask again, showing the model its mistake.
    Unavailable:    wait (1s, 2s, ...) and ask again.
    Quota or any other error: raised at once, retrying cannot help.
    """
    current_prompt = prompt
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return provider.generate(current_prompt, schema)
        except LLMInvalidOutputError as error:
            if attempt == MAX_ATTEMPTS:
                raise
            current_prompt = _repair_prompt(prompt, error)
        except LLMUnavailableError:
            if attempt == MAX_ATTEMPTS:
                raise
            sleep(BASE_DELAY * 2 ** (attempt - 1))
    raise AssertionError("unreachable: the last attempt always returns or raises")