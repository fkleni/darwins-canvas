"""The contract every language-model backend must follow."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LLMError(Exception):
    """Anything that goes wrong while asking a language model (network, quota, ...)."""


class LLMInvalidOutputError(LLMError):
    """The model answered, but not in the shape we asked for."""

class LLMQuotaError(LLMError):
    """The provider refused because a rate limit or quota was hit (HTTP 429)."""

class LLMUnavailableError(LLMError):
    """The provider is temporarily unable to answer (HTTP 5xx or a network failure).

    Worth retrying after a short wait, or worth falling back to another provider.
    """


@runtime_checkable
class LLMProvider(Protocol):
    """Anything that can turn a prompt into a validated Pydantic object."""

    def generate[T: BaseModel](self, prompt: str, schema: type[T]) -> T:
        """Ask the model and return its answer parsed into `schema`.

        Raises LLMInvalidOutputError if the answer does not fit the schema and
        LLMError for any other failure.
        """
        ...