"""Manual experiment: the same creature drawn with different wording, to pick the best look.

Uses the real Pollinations service and takes a few minutes. Run from the backend folder:
    python -m scripts.experiment_looks
"""

import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.ai.image_cache import ImageCache  # noqa: E402
from app.ai.image_prompt import (  # noqa: E402
    STYLE,
    ImageRequest,
    appearance_phrase,
    lineage_seed,
    scrub_counts,
)
from app.ai.pollinations import ImageError, PollinationsClient  # noqa: E402
from app.sim.events import EVENTS  # noqa: E402
from app.sim.evolve import evolve  # noqa: E402
from app.sim.species import SPECIES  # noqa: E402

OUTPUT = Path("scratch_looks")
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
NOTES = "Streamlined body, slightly webbed hands, smooth sleek skin, upright posture"

VARIANTS = {
    "A_current": (
        "a speculative creature evolved from human ancestors",
        "body covered in thick textured hide",
    ),
    "B_humanoid_hide": (
        "a speculative upright humanoid creature evolved from human ancestors",
        "body covered in thick textured hide",
    ),
    "C_humanoid_plates": (
        "a speculative upright humanoid creature evolved from human ancestors",
        "body covered in overlapping leathery plates and a rough woven wrap",
    ),
}

child = evolve(SPECIES["human"].founder(), EVENTS["great_flood"], random.Random(1))
seed = lineage_seed("demo-lineage")
client = PollinationsClient(ImageCache(OUTPUT / "cache"))

for label, (subject, covering) in VARIANTS.items():
    parts = [STYLE, subject, appearance_phrase(child.appearance), covering, scrub_counts(NOTES)]
    request = ImageRequest(prompt=", ".join(parts), seed=seed)
    try:
        image = client.generate(request)
    except ImageError as error:
        print(f"{label}: {type(error).__name__}: {error}")
        continue
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"{label}.{EXTENSIONS[image.media_type]}"
    path.write_bytes(image.data)
    print(f"{label}: {path}")