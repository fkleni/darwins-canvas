"""Scripted stand-ins for the real models, used in tests."""

from pydantic import BaseModel, ValidationError

from app.ai.image_cache import GeneratedImage
from app.ai.provider import LLMInvalidOutputError
from app.ai.safety import ImageVerdict


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


class FakeInspector:
    """Plays back prepared verdicts, in order, and remembers every picture it was shown."""

    def __init__(self, verdicts: list[ImageVerdict | Exception]):
        self._verdicts = list(verdicts)
        self.inspected: list[GeneratedImage] = []

    def inspect(self, image: GeneratedImage) -> ImageVerdict:
        self.inspected.append(image)
        if not self._verdicts:
            raise AssertionError("FakeInspector ran out of scripted verdicts")
        verdict = self._verdicts.pop(0)
        if isinstance(verdict, Exception):
            raise verdict
        return verdict