"""The gate between a freshly generated picture and the player's screen.

Every picture is checked by a second model before anyone can see it. A rejected
picture is replaced by a new attempt; a picture we could not check is not shown.
"""

import logging
import threading
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.ai.image_cache import GeneratedImage, ImageCache, cache_key
from app.ai.image_prompt import ImageRequest, retry_request
from app.ai.pollinations import ImageError
from app.ai.provider import LLMError

logger = logging.getLogger(__name__)

MAX_PICTURE_ATTEMPTS = 3


class ImageVerdict(BaseModel):
    """What the inspecting model says about one picture. Every flag is true when there is a problem."""

    shows_nudity: bool = Field(
        description=(
            "True if the picture shows a human or human-like body that is nude or not fully "
            "covered by clothing, hide, fur or scales, or any sexual content. When unsure, answer true."
        )
    )
    shows_graphic_violence: bool = Field(
        description="True if the picture shows gore, wounds or graphic violence. When unsure, answer true."
    )
    is_off_topic: bool = Field(
        description=(
            "True if the picture is NOT a single creature, character or fossil specimen drawn as an "
            "illustration: for example text, a logo, a screenshot, an error page, several unrelated "
            "subjects or an empty image. When unsure, answer true."
        )
    )
    reason: str = Field(
        max_length=200,
        description="One short sentence explaining the verdict, without graphic detail.",
    )

    @property
    def is_acceptable(self) -> bool:
        return not (self.shows_nudity or self.shows_graphic_violence or self.is_off_topic)


@runtime_checkable
class ImageInspector(Protocol):
    """Anything that can look at a picture and give a verdict."""

    def inspect(self, image: GeneratedImage) -> ImageVerdict: ...


class ImageDownloader(Protocol):
    """Anything that can fetch a picture for a request."""

    @property
    def model(self) -> str: ...

    def download(self, request: ImageRequest) -> GeneratedImage: ...


class ImageOutcome(StrEnum):
    CACHED = "cached"  # an approved picture was already stored
    APPROVED = "approved"  # freshly generated and passed the inspection
    REJECTED = "rejected"  # every attempt was judged unsuitable
    UNVERIFIED = "unverified"  # we could not inspect it, so we do not show it
    UNAVAILABLE = "unavailable"  # the picture service failed


class GateResult(BaseModel):
    """The answer of the gate. `image` is None whenever there is nothing safe to show."""

    model_config = ConfigDict(frozen=True)

    outcome: ImageOutcome
    image: GeneratedImage | None = None
    attempts: int = 0
    reason: str = ""


class SafeImageService:
    """Gives out only pictures that passed the inspection, and caches only those."""

    def __init__(self, cache: ImageCache, downloader: ImageDownloader, inspector: ImageInspector):
        self._cache = cache
        self._downloader = downloader
        self._inspector = inspector
        self._lock = threading.Lock()

    def get(self, request: ImageRequest) -> GateResult:
        key = cache_key(request, self._downloader.model)
        cached = self._cache.get(key)
        if cached is not None:
            logger.info("approved picture found in the cache")
            return GateResult(outcome=ImageOutcome.CACHED, image=cached)
        with self._lock:
            cached = self._cache.get(key)  # someone may have finished it while we waited
            if cached is not None:
                return GateResult(outcome=ImageOutcome.CACHED, image=cached)
            return self._produce(request, key)

    def _produce(self, request: ImageRequest, key: str) -> GateResult:
        last_reason = ""
        for attempt in range(1, MAX_PICTURE_ATTEMPTS + 1):
            candidate = request if attempt == 1 else retry_request(request, attempt)
            try:
                image = self._downloader.download(candidate)
            except ImageError as error:
                logger.warning("could not get a picture: %s", error)
                return GateResult(outcome=ImageOutcome.UNAVAILABLE, attempts=attempt, reason=str(error))
            try:
                verdict = self._inspector.inspect(image)
            except LLMError as error:
                logger.warning("could not inspect the picture, so it is not shown: %s", error)
                return GateResult(outcome=ImageOutcome.UNVERIFIED, attempts=attempt, reason=str(error))
            if verdict.is_acceptable:
                stored = self._cache.put(key, image.data)
                return GateResult(
                    outcome=ImageOutcome.APPROVED,
                    image=stored,
                    attempts=attempt,
                    reason=verdict.reason,
                )
            last_reason = verdict.reason
            logger.warning(
                "picture rejected on attempt %d of %d: %s", attempt, MAX_PICTURE_ATTEMPTS, last_reason
            )
        return GateResult(
            outcome=ImageOutcome.REJECTED, attempts=MAX_PICTURE_ATTEMPTS, reason=last_reason
        )