"""Shrinks a hand-made picture into the size and format the web card needs."""

from pathlib import Path

from PIL import Image, ImageOps

CARD_SIZE = 768  # pixels; the card shows the picture much smaller than this
WEBP_QUALITY = 82  # 0-100: higher is sharper and heavier


def optimize_picture(
    source: Path, target: Path, size: int = CARD_SIZE, quality: int = WEBP_QUALITY
) -> None:
    """Write `target` as a square WebP of at most `size` pixels. The source is never touched."""
    with Image.open(source) as picture:
        rgb = ImageOps.exif_transpose(picture).convert("RGB")
        side = min(size, *rgb.size)  # never enlarge a small picture
        square = ImageOps.fit(rgb, (side, side), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    square.save(target, "WEBP", quality=quality, method=6)