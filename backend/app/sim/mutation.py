"""Small cosmetic changes between a parent and its child."""

import random

from app.sim import config
from app.sim.appearance import SKIN_DARKNESS, TRAIT_GRAPHS, Appearance, Mutation, neighbours
from app.sim.events import Event


def pressure_from_event(event: Event) -> str | None:
    """Which way an event pushes skin colour: 'darker', 'lighter' or None."""
    if event.changes.get("radiation", 1.0) > 1.0:
        return "darker"
    if event.changes.get("temperature", 0.0) <= -10.0:
        return "lighter"
    return None


def _pressured_choice(appearance: Appearance, pressure: str, rng: random.Random) -> str | None:
    """A neighbouring skin colour in the pushed direction, or None if there is none."""
    current = SKIN_DARKNESS[appearance.skin_color]
    candidates = neighbours("skin_color", appearance.skin_color)
    if pressure == "darker":
        options = [value for value in candidates if SKIN_DARKNESS[value] > current]
    else:
        options = [value for value in candidates if SKIN_DARKNESS[value] < current]
    return rng.choice(options) if options else None


def _apply(
    appearance: Appearance, trait: str, new_value: str, adaptive: bool
) -> tuple[Appearance, Mutation]:
    """Build the changed copy of an appearance, plus the record of what changed."""
    old_value = getattr(appearance, trait)
    changed = appearance.model_copy(update={trait: new_value})
    return changed, Mutation(trait=trait, old=old_value, new=new_value, adaptive=adaptive)


def mutate(
    appearance: Appearance, event: Event, rng: random.Random
) -> tuple[Appearance, Mutation]:
    """Change exactly one trait by exactly one step."""
    pressure = pressure_from_event(event)
    if pressure is not None and rng.random() < config.MUTATION_PRESSURE_CHANCE:
        new_color = _pressured_choice(appearance, pressure, rng)
        if new_color is not None:
            return _apply(appearance, "skin_color", new_color, adaptive=True)

    trait = rng.choice(sorted(TRAIT_GRAPHS))
    new_value = rng.choice(neighbours(trait, getattr(appearance, trait)))
    return _apply(appearance, trait, new_value, adaptive=False)