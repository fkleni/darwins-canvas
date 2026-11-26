"""Manual check: which picture does each preset event lead to?

Run from the backend folder:  python -m scripts.check_forms
"""

import random
from pathlib import Path

from app.catalog import FormCatalog
from app.sim.events import EVENTS
from app.sim.evolve import evolve
from app.sim.species import DEFAULT_SPECIES

catalog = FormCatalog.load(Path("assets/forms"))
print("descriptions without a picture:", catalog.missing_pictures() or "none")
print()

rng = random.Random(0)
for event in EVENTS.values():
    child = evolve(DEFAULT_SPECIES.founder(), event, rng)
    form = catalog.resolve(child)
    print(f"{event.label:16} -> {form.key:22} {form.image}")