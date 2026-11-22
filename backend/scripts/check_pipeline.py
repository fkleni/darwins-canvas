"""Manual end-to-end check: simulation -> narration -> picture -> safety gate.

Needs GEMINI_API_KEY in backend/.env and uses the real Pollinations service.
It is slow on purpose (pictures are spaced out). Run from the backend folder:
    python -m scripts.check_pipeline

Only pictures that pass the inspection are written to disk. A rejected picture is
never saved: you only see the outcome line and the reason.
"""

import logging
import random
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.ai.gemini import GeminiImageInspector, GeminiProvider  # noqa: E402
from app.ai.image_cache import ImageCache  # noqa: E402
from app.ai.image_prompt import (  # noqa: E402
    build_founder_image_request,
    build_image_request,
    lineage_seed,
)
from app.ai.lineage import descend, founder_chronicle  # noqa: E402
from app.ai.narrator import narrate  # noqa: E402
from app.ai.pollinations import PollinationsClient  # noqa: E402
from app.ai.provider import LLMError  # noqa: E402
from app.ai.safety import SafeImageService  # noqa: E402
from app.sim.events import EVENTS  # noqa: E402
from app.sim.evolve import evolve  # noqa: E402
from app.sim.models import Status  # noqa: E402
from app.sim.species import DEFAULT_SPECIES  # noqa: E402

OUTPUT = Path("scratch_pipeline")
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

service = SafeImageService(ImageCache(OUTPUT / "cache"), PollinationsClient(), GeminiImageInspector())
provider = GeminiProvider()
species = DEFAULT_SPECIES
seed = lineage_seed("demo-lineage")
rng = random.Random(1)


def report(label, request):
    started = time.monotonic()
    result = service.get(request)
    seconds = time.monotonic() - started
    if result.image is None:
        return (
            f"{label}: NO PICTURE ({result.outcome.value} after {result.attempts} attempt(s)): "
            f"{result.reason}"
        )
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"{label}.{EXTENSIONS[result.image.media_type]}"
    path.write_bytes(result.image.data)
    return f"{label}: {result.outcome.value} -> {path} (attempts {result.attempts}, {seconds:.0f}s)"


print(report("0_founder", build_founder_image_request(species, seed)))

creature = species.founder()
chronicle = founder_chronicle(species)
for number, event_id in enumerate(("great_flood", "ice_age", "heavy_gravity"), start=1):
    event = EVENTS[event_id]
    child = evolve(creature, event, rng)
    try:
        narration = narrate(provider, chronicle, child, event)
    except LLMError as error:
        print(f"{type(error).__name__}: {error}")
        break
    print(f"{event.label}: score {child.score:.0f}, {child.status.value} -> {narration.name}")
    label = f"{number}_{event_id}_{child.status.value}"
    print(report(label, build_image_request(narration, child, species.name, seed)))
    creature = child.model_copy(update={"name": narration.name})
    chronicle = descend(chronicle, narration, event.label)
    if child.status == Status.EXTINCT:
        break