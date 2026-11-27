"""One full evolution step: parent creature + event -> child creature."""

import random

from app.sim.adaptation import adapt, assess
from app.sim.events import Event, apply_event
from app.sim.models import Creature, Status
from app.sim.mutation import mutate


class ExtinctLineageError(Exception):
    """Raised when someone tries to evolve a creature that is already extinct."""


def evolve(parent: Creature, event: Event, rng: random.Random | None = None) -> Creature:
    """Apply an event to a parent creature and return its descendant.

    The parent is never modified. The name is a placeholder: the AI layer
    (Phase 2) will name the child. Pass a seeded rng to make the cosmetic
    mutation reproducible (tests do this).
    """
    if parent.status == Status.EXTINCT:
        raise ExtinctLineageError(f"{parent.name} is extinct and cannot evolve")

    rng = rng or random.Random()
    world = apply_event(parent.world, event)
    adapted_to = adapt(world, parent.adapted_to)
    depth = parent.depth + 1
    final_score, status = assess(world, adapted_to, parent.body_size, depth)
    appearance, mutation = mutate(parent.appearance, event, rng)

    return Creature(
        name="Unnamed descendant",
        depth=depth,
        body_size=parent.body_size,
        appearance=appearance,
        world=world,
        adapted_to=adapted_to,
        score=final_score,
        status=status,
        mutation=mutation,
        changed=tuple(event.changes),
    )