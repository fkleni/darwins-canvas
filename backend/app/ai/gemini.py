"""The real Gemini backend, behind the LLMProvider contract."""

import os

import httpx
from google import genai
from google.genai import errors
from pydantic import BaseModel, ValidationError

from app.ai.provider import (
    LLMError,
    LLMInvalidOutputError,
    LLMQuotaError,
    LLMUnavailableError,
)

DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiProvider:
    """Talks to the Gemini API and returns answers validated against a schema."""

    def __init__(self, api_key: str | None = None, model: str | None = None, client=None):
        if client is None:
            key = api_key or os.environ.get("GEMINI_API_KEY")
            if not key:
                raise LLMError("GEMINI_API_KEY is not set")
            client = genai.Client(api_key=key)
        self._client = client
        self._model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    def generate[T: BaseModel](self, prompt: str, schema: type[T]) -> T:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": schema.model_json_schema(),
                },
            )
        except errors.APIError as error:
            code = getattr(error, "code", None)
            if code == 429:
                raise LLMQuotaError(f"Gemini quota or rate limit hit: {error}") from error
            if isinstance(code, int) and code >= 500:
                raise LLMUnavailableError(f"Gemini is unavailable: {error}") from error
            raise LLMError(f"Gemini rejected the request: {error}") from error
        except httpx.HTTPError as error:
            raise LLMUnavailableError(f"Could not reach Gemini: {error}") from error

        text = response.text
        if not text:
            raise LLMInvalidOutputError("Gemini returned no text (empty or blocked answer)")
        try:
            return schema.model_validate_json(text)
        except ValidationError as error:
            raise LLMInvalidOutputError(str(error)) from error