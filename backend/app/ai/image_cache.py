"""A folder of pictures we already generated, so the same one is never paid for twice."""

import hashlib
import json
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.ai.image_prompt import ImageRequest


class GeneratedImage(BaseModel):
    """A picture we hold in memory: its bytes and what kind of picture it is."""

    model_config = ConfigDict(frozen=True)

    data: bytes
    media_type: str


def sniff_media_type(data: bytes) -> str | None:
    """Recognise a picture by its first bytes; None for anything else (an HTML error page...)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def cache_key(request: ImageRequest, model: str) -> str:
    """A fingerprint of everything that decides what the picture looks like."""
    parts = [model, request.prompt, request.seed, request.width, request.height]
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()


class ImageCache:
    """Stores pictures as files named after their key."""

    def __init__(self, directory: Path):
        self._directory = Path(directory)

    def _path(self, key: str) -> Path:
        if not key.isalnum():
            raise ValueError(f"invalid cache key: {key!r}")
        return self._directory / f"{key}.img"

    def get(self, key: str) -> GeneratedImage | None:
        """The stored picture, or None when we do not have a good copy."""
        path = self._path(key)
        if not path.is_file():
            return None
        data = path.read_bytes()
        media_type = sniff_media_type(data)
        if media_type is None:
            path.unlink(missing_ok=True)  # a damaged entry is worse than none
            return None
        return GeneratedImage(data=data, media_type=media_type)

    def put(self, key: str, data: bytes) -> GeneratedImage:
        """Store a picture. Refuses anything that is not a picture."""
        media_type = sniff_media_type(data)
        if media_type is None:
            raise ValueError("refusing to cache something that is not a picture")
        path = self._path(key)
        self._directory.mkdir(parents=True, exist_ok=True)
        temporary = self._directory / f"{key}.{uuid.uuid4().hex}.tmp"
        temporary.write_bytes(data)
        temporary.replace(path)
        return GeneratedImage(data=data, media_type=media_type)