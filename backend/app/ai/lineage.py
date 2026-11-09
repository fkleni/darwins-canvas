"""What the story remembers about a creature's ancestry."""

from pydantic import BaseModel, ConfigDict

from app.ai.schemas import Narration
from app.sim.species import Species

MAX_TRAITS = 8  # traits remembered per creature; when over the cap the newest win
RECENT_EVENTS = 4  # how many past events the story remembers


def merge_traits(inherited: tuple[str, ...], new: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Add new traits to inherited ones: no duplicates, newest kept when over the cap."""
    merged: list[str] = []
    seen: set[str] = set()
    for trait in (*inherited, *new):
        key = trait.strip().lower()
        if key not in seen:
            seen.add(key)
            merged.append(trait.strip())
    return tuple(merged[-MAX_TRAITS:])


class Chronicle(BaseModel):
    """The story-side memory of one creature. Derived once, never edited."""

    model_config = ConfigDict(frozen=True)

    origin: str  # the species the whole lineage started from
    name: str
    traits: tuple[str, ...]  # inherited and acquired, capped
    recent_events: tuple[str, ...] = ()  # event labels, oldest first


def founder_chronicle(species: Species) -> Chronicle:
    """The memory of a lineage's root: the species itself, no events yet."""
    return Chronicle(
        origin=species.name,
        name=species.name,
        traits=merge_traits((), species.base_traits),
    )


def descend(parent: Chronicle, narration: Narration, event_label: str) -> Chronicle:
    """The memory of a child: the parent's memory plus what just happened."""
    return Chronicle(
        origin=parent.origin,
        name=narration.name,
        traits=merge_traits(parent.traits, narration.traits),
        recent_events=(*parent.recent_events, event_label)[-RECENT_EVENTS:],
    )


def history_text(chronicle: Chronicle) -> str:
    """The ancestry as a plain block of text, ready to put into a prompt."""
    events = " -> ".join(chronicle.recent_events) or "none yet"
    traits = "; ".join(chronicle.traits) or "none recorded"
    return (
        f"Lineage origin: {chronicle.origin}\n"
        f"Current form: {chronicle.name}\n"
        f"Inherited traits: {traits}\n"
        f"Recent events (oldest first): {events}"
    )