"""Manual check: a short real evolution chain, narrated by Gemini.

Run from the backend folder:  python -m scripts.check_narrator
"""

import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.ai.gemini import GeminiProvider  # noqa: E402
from app.ai.lineage import descend, founder_chronicle  # noqa: E402
from app.ai.narrator import narrate  # noqa: E402
from app.ai.provider import LLMError  # noqa: E402
from app.catalog import FormCatalog  # noqa: E402
from app.sim.events import EVENTS  # noqa: E402
from app.sim.evolve import evolve  # noqa: E402
from app.sim.models import Status  # noqa: E402
from app.sim.species import DEFAULT_SPECIES  # noqa: E402

provider = GeminiProvider()
catalog = FormCatalog.load(Path("assets/forms"))
rng = random.Random(1)
species = DEFAULT_SPECIES
creature = species.founder()
chronicle = founder_chronicle(species)

for event_id in ("great_flood", "ice_age", "heavy_gravity"):
    event = EVENTS[event_id]
    child = evolve(creature, event, rng)
    form = catalog.resolve(child)
    print(f"=== {event.label}: score {child.score:.0f}, {child.status.value}, picture {form.image}")
    try:
        narration = narrate(provider, chronicle, child, event, form)
    except LLMError as error:
        print(f"{type(error).__name__}: {error}")
        break
    print(narration.model_dump_json(indent=2))
    creature = child.model_copy(update={"name": narration.name})
    chronicle = descend(chronicle, narration, event.label)
    if child.status == Status.EXTINCT:
        print("--- the lineage ended ---")
        break