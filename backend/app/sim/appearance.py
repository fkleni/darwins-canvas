"""What a creature looks like, and which looks are neighbours of each other."""

from pydantic import BaseModel, ConfigDict, model_validator


def _build_graph(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Turn 'a is next to b' pairs into a neighbour lookup that works both ways."""
    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    return graph


# Each trait is a graph: a value may only change into one of its neighbours.
TRAIT_GRAPHS = {
    "skin_color": _build_graph([
        ("pale", "cream"), ("cream", "tan"), ("tan", "brown"), ("brown", "dark"),
        ("dark", "charcoal"), ("pale", "light_gray"), ("light_gray", "slate"),
        ("slate", "charcoal"), ("tan", "olive"), ("olive", "moss"),
    ]),
    "eye_color": _build_graph([
        ("brown", "hazel"), ("brown", "black"), ("hazel", "amber"), ("hazel", "green"),
        ("green", "blue"), ("blue", "gray"), ("gray", "black"), ("amber", "red"),
    ]),
    "eye_size": _build_graph([
        ("tiny", "small"), ("small", "medium"), ("medium", "large"), ("large", "huge"),
    ]),
    "pattern": _build_graph([
        ("none", "freckled"), ("freckled", "spotted"), ("spotted", "mottled"),
        ("mottled", "striped"),
    ]),
}


class Appearance(BaseModel):
    """The cosmetic look of a creature. Read-only once created."""

    model_config = ConfigDict(frozen=True)

    skin_color: str
    eye_color: str
    eye_size: str
    pattern: str

    @model_validator(mode="after")
    def values_must_exist(self) -> "Appearance":
        for trait, graph in TRAIT_GRAPHS.items():
            value = getattr(self, trait)
            if value not in graph:
                raise ValueError(f"{value!r} is not a valid {trait}; options: {sorted(graph)}")
        return self


def neighbours(trait: str, value: str) -> list[str]:
    """The values a trait may change into, starting from the current value."""
    return TRAIT_GRAPHS[trait][value]



# How dark each skin colour is. Events push colour lighter or darker along this scale.
SKIN_DARKNESS = {
    "pale": 0, "cream": 1, "light_gray": 1, "tan": 2, "slate": 2,
    "olive": 3, "brown": 3, "moss": 4, "dark": 4, "charcoal": 5,
}


class Mutation(BaseModel):
    """A record of the one cosmetic change between a parent and its child."""

    model_config = ConfigDict(frozen=True)

    trait: str
    old: str
    new: str
    adaptive: bool  # True when an event pushed the change, False when it was pure chance