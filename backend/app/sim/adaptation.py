"""How a creature adapts to its world, and how well it copes afterwards."""

import math

from app.sim import config
from app.sim.models import Status, WorldState


def adapt_value(kind: str, world_value: float, adapted_value: float, max_shift: float) -> float:
    """Move one adaptation value toward the world, but no faster than max_shift."""
    if kind == "ratio":
        ratio = world_value / adapted_value
        ratio = min(max(ratio, 1 / max_shift), max_shift)
        return adapted_value * ratio
    gap = world_value - adapted_value
    gap = min(max(gap, -max_shift), max_shift)
    return adapted_value + gap


def adapt(world: WorldState, adapted_to: WorldState) -> WorldState:
    """One evolution step: return the creature's new adaptation values."""
    world_values = world.model_dump()
    adapted_values = adapted_to.model_dump()
    new_values = {
        name: adapt_value(spec["kind"], world_values[name], adapted_values[name], spec["max_shift"])
        for name, spec in config.PARAMETERS.items()
    }
    return WorldState(**new_values)


def stress_distance(kind: str, world_value: float, adapted_value: float, scale: float = 1.0) -> float:
    """How out of tune a creature is for ONE parameter (0 = perfectly tuned)."""
    if kind == "ratio":
        return abs(math.log(world_value / adapted_value))
    return abs(world_value - adapted_value) / scale


def distances(world: WorldState, adapted_to: WorldState) -> dict[str, float]:
    """The stress distance of every parameter, by name."""
    world_values = world.model_dump()
    adapted_values = adapted_to.model_dump()
    return {
        name: stress_distance(spec["kind"], world_values[name], adapted_values[name], spec.get("scale", 1.0))
        for name, spec in config.PARAMETERS.items()
    }


def bell_score(distance: float) -> float:
    """Turn a stress distance into a 0-100 score (100 = perfectly tuned)."""
    return 100 * math.exp(-((distance / config.SCORE_WIDTH) ** 2))


def score(world: WorldState, adapted_to: WorldState) -> float:
    """The adaptation score of a creature living in a world."""
    total_distance = math.hypot(*distances(world, adapted_to).values())
    return bell_score(total_distance)


def exceeds_hard_limit(world: WorldState, body_size: int) -> bool:
    """True when the world is physically unsurvivable for this body size."""
    return world.gravity > config.GRAVITY_CEILING_BY_BODY_SIZE[body_size]


def decide_status(final_score: float, depth: int) -> Status:
    """Alive, critical (protected) or extinct, from the score and the depth."""
    if final_score >= config.SURVIVAL_THRESHOLD:
        return Status.ALIVE
    if depth <= config.GRACE_EVOLUTIONS:
        return Status.CRITICAL
    return Status.EXTINCT


def assess(
    world: WorldState, adapted_to: WorldState, body_size: int, depth: int
) -> tuple[float, Status]:
    """The full verdict for a creature: its final score and its status."""
    if exceeds_hard_limit(world, body_size):
        final_score = 0.0
    else:
        final_score = score(world, adapted_to)
    return final_score, decide_status(final_score, depth)