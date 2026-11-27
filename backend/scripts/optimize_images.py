"""Turns the full-size originals into small WebP pictures for the app.

Reads  assets/originals/*  and writes  assets/forms/<same name>.webp.
Run from the backend folder:  python -m scripts.optimize_images
"""

from pathlib import Path

from app.optimize import optimize_picture

ORIGINALS = Path("assets/originals")
OUTPUT = Path("assets/forms")
SOURCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

before = after = 0
for source in sorted(ORIGINALS.iterdir()):
    if source.suffix.lower() not in SOURCE_SUFFIXES:
        continue
    target = OUTPUT / f"{source.stem}.webp"
    optimize_picture(source, target)
    before += source.stat().st_size
    after += target.stat().st_size
    print(f"{source.name:22} {source.stat().st_size // 1024:5} KB -> {target.stat().st_size // 1024:4} KB")
print(f"total: {before // 1024} KB -> {after // 1024} KB")