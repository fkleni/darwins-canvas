"""Which way, and how far, a creature's body has moved away from the starting world."""

import math

from pydantic import BaseModel, ConfigDict

from app.sim import config
from app.sim.models import WorldState

BASE_KEY = "base"
KEY_SEPARATOR = "__"


class Direction(BaseModel):
    """One parameter the body has adapted away from its baseline, and the way it went."""

    model_config = ConfigDict(frozen=True)

    parameter: str
    sign: str  # "up" or "down"
    strength: float

    @property
    def key(self) -> str:
        return f"{self.parameter}_{self.sign}"


def adaptation_directions(adapted_to: WorldState) -> list[Direction]:
    """The strongest adaptations, strongest first (at most FORM_MAX_DIRECTIONS)."""
    values = adapted_to.model_dump()
    found = []
    for name, spec in config.PARAMETERS.items():
        if spec["kind"] == "ratio":
            shift = math.log(values[name] / spec["baseline"])
        else:
            shift = (values[name] - spec["baseline"]) / spec["scale"]
        if abs(shift) >= config.FORM_THRESHOLD:
            sign = "up" if shift > 0 else "down"
            found.append(Direction(parameter=name, sign=sign, strength=abs(shift)))
    found.sort(key=lambda direction: -direction.strength)  # stable: ties keep config order
    return found[: config.FORM_MAX_DIRECTIONS]


def form_keys(adapted_to: WorldState) -> list[str]:
    """Picture keys to try, most specific first, always ending with the base form."""
    directions = adaptation_directions(adapted_to)
    order = list(config.PARAMETERS)
    keys = []
    if len(directions) == 2:
        in_config_order = sorted(directions, key=lambda d: order.index(d.parameter))
        keys.append(KEY_SEPARATOR.join(d.key for d in in_config_order))
    keys.extend(d.key for d in directions)
    keys.append(BASE_KEY)
    return keys