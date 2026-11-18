"""Downloads pictures from Pollinations, politely: spaced out and retried."""

import logging
import os
import threading
import time
from collections.abc import Callable
from urllib.parse import quote

import httpx

from app.ai.image_cache import GeneratedImage, sniff_media_type
from app.ai.image_prompt import ImageRequest

DEFAULT_BASE_URL = "https://image.pollinations.ai/prompt"
DEFAULT_MODEL = "flux"
DEFAULT_MIN_INTERVAL = 15.0  # seconds between two requests to the service
MAX_ATTEMPTS = 3
BASE_DELAY = 5.0  # seconds to wait after the first temporary failure; doubles each time
TIMEOUT = 120.0  # generating a picture is slow

logger = logging.getLogger(__name__)


class ImageError(Exception):
    """Anything that goes wrong while asking for a picture."""


class ImageUnavailableError(ImageError):
    """The service is busy or unreachable right now. Worth trying again later."""


class PollinationsClient:
    """Downloads pictures one at a time and never hammers the service.

    It does not cache: deciding which pictures may be kept is the safety gate's job.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        min_interval: float | None = None,
        safe: bool = True,
        http_get: Callable = httpx.get,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._base_url = (
            base_url or os.environ.get("POLLINATIONS_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._api_key = api_key or os.environ.get("POLLINATIONS_API_KEY")
        self._model = model or os.environ.get("POLLINATIONS_MODEL", DEFAULT_MODEL)
        if min_interval is None:
            min_interval = float(os.environ.get("POLLINATIONS_MIN_INTERVAL", DEFAULT_MIN_INTERVAL))
        self._min_interval = min_interval
        self._safe = safe
        self._http_get = http_get
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._last_call: float | None = None

    @property
    def model(self) -> str:
        return self._model

    def download(self, request: ImageRequest) -> GeneratedImage:
        """Download one picture. Only one request is in flight at a time."""
        with self._lock:
            return self._download_with_retry(request)

    def _wait_for_turn(self) -> None:
        """Sleep until enough time has passed since our previous request."""
        if self._last_call is None:
            return
        wait = self._last_call + self._min_interval - self._clock()
        if wait > 0:
            logger.info("waiting %.0fs before the next request", wait)
            self._sleep(wait)

    def _download_with_retry(self, request: ImageRequest) -> GeneratedImage:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_for_turn()
            try:
                return self._download(request)
            except ImageUnavailableError as error:
                if attempt == MAX_ATTEMPTS:
                    raise
                delay = BASE_DELAY * 2 ** (attempt - 1)
                logger.warning(
                    "%s; retrying in %.0fs (attempt %d of %d)", error, delay, attempt, MAX_ATTEMPTS
                )
                self._sleep(delay)
        raise AssertionError("unreachable: the last attempt always returns or raises")

    def _download(self, request: ImageRequest) -> GeneratedImage:
        url = f"{self._base_url}/{quote(request.prompt, safe='')}"
        params = {
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
            "model": self._model,
            "safe": str(self._safe).lower(),
            "private": "true",
            "nologo": "true",
        }
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        logger.info("requesting a picture from the service")
        self._last_call = self._clock()
        try:
            response = self._http_get(
                url, params=params, headers=headers, timeout=TIMEOUT, follow_redirects=True
            )
        except httpx.HTTPError as error:
            raise ImageUnavailableError(f"could not reach the image service: {error}") from error

        status = response.status_code
        if status in (402, 429) or status >= 500:
            raise ImageUnavailableError(f"image service busy, over quota or down (HTTP {status})")
        if status != 200:
            raise ImageError(f"image service refused the request (HTTP {status})")
        media_type = sniff_media_type(response.content)
        if media_type is None:
            raise ImageError("the image service answered with something that is not a picture")
        return GeneratedImage(data=response.content, media_type=media_type)