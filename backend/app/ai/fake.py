"""A scripted stand-in for a real language model, used in tests."""

from pydantic import BaseModel, ValidationError

from app.ai.provider import LLMInvalidOutputError


class FakeProvider:
    """Plays back prepared answers, in order, and remembers every prompt it saw.

    Each scripted answer is either a dict (what a model would return as JSON)
    or an exception instance (a failure to simulate).
    """

    def __init__(self, responses: list[dict | Exception]):
        self._responses = list(responses)
        self.prompts: list[str] = []

    def generate[T: BaseModel](self, prompt: str, schema: type[T]) -> T:
        self.prompts.append(prompt)
        if not self._responses:
            raise AssertionError("FakeProvider ran out of scripted responses")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        try:
            return schema.model_validate(response)
        except ValidationError as error:
            raise LLMInvalidOutputError(str(error)) from error