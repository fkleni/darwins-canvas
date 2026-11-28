"""Small inner changes between a parent and its child."""

import random

from app.sim import config
from app.sim.events import Event
from app.sim.physiology import MAX_LEVEL, TRAITS, Mutation, Physiology

# How the body answers an environmental push: (parameter, direction) -> (trait, step).
RESPONSES = {
    ("gravity", "up"): ("bone_density", +1),
    ("gravity", "down"): ("bone_density", -1),
    ("radiation", "up"): ("cellular_repair", +1),
    ("radiation", "down"): ("cellular_repair", -1),
    ("temperature", "down"): ("metabolic_rate", +1),
    ("temperature", "up"): ("metabolic_rate", -1),
    ("oxygen", "down"): ("lung_efficiency", +1),
    ("oxygen", "up"): ("lung_efficiency", -1),
    ("water", "down"): ("water_retention", +1),
    ("water", "up"): ("water_retention", -1),
}


def pushes_from_event(event: Event) -> list[tuple[str, int]]:
    """The (trait, step) pushes an event causes, in config order."""
    pushes = []
    for name, spec in config.PARAMETERS.items():
        if name not in event.changes:
            continue
        neutral = 1.0 if spec["kind"] == "ratio" else 0.0
        value = event.changes[name]
        if abs(value - neutral) < 1e-9:
            continue
        pushes.append(RESPONSES[(name, "up" if value > neutral else "down")])
    return pushes


def _can_move(physiology: Physiology, trait: str, step: int) -> bool:
    return 0 <= getattr(physiology, trait) + step <= MAX_LEVEL


def _apply(
    physiology: Physiology, trait: str, step: int, adaptive: bool
) -> tuple[Physiology, Mutation]:
    """Build the changed copy, plus the record of what changed."""
    old = getattr(physiology, trait)
    changed = physiology.model_copy(update={trait: old + step})
    return changed, Mutation(trait=trait, old=old, new=old + step, adaptive=adaptive)


def mutate(
    physiology: Physiology, event: Event, rng: random.Random
) -> tuple[Physiology, Mutation]:
    """Change exactly one inner trait by exactly one step."""
    pushes = [(t, s) for t, s in pushes_from_event(event) if _can_move(physiology, t, s)]
    if pushes and rng.random() < config.MUTATION_PRESSURE_CHANCE:
        trait, step = rng.choice(pushes)
        return _apply(physiology, trait, step, adaptive=True)

    movable = [(t, s) for t in TRAITS for s in (-1, 1) if _can_move(physiology, t, s)]
    trait, step = rng.choice(movable)
    return _apply(physiology, trait, step, adaptive=False)