"""Which way, and how far, a creature's body has moved away from the starting world."""

import math
from collections.abc import Collection

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
    strength: float  # how far the body has moved, in stress units
    recent: bool = False  # True when the latest event changed this parameter

    @property
    def key(self) -> str:
        return f"{self.parameter}_{self.sign}"

    @property
    def weight(self) -> float:
        """The strength used for ranking: recent adaptations count extra so the player sees them."""
        return self.strength * (config.FORM_RECENT_BOOST if self.recent else 1.0)


def adaptation_directions(adapted_to: WorldState, recent: Collection[str] = ()) -> list[Direction]:
    """The strongest adaptations, strongest first (at most FORM_MAX_DIRECTIONS).

    `recent` names the parameters changed by the latest event. The threshold is checked
    before the boost, so a boost can reorder adaptations but never invent one.
    """
    values = adapted_to.model_dump()
    found = []
    for name, spec in config.PARAMETERS.items():
        if spec["kind"] == "ratio":
            shift = math.log(values[name] / spec["baseline"])
        else:
            shift = (values[name] - spec["baseline"]) / spec["scale"]
        if abs(shift) >= config.FORM_THRESHOLD:
            sign = "up" if shift > 0 else "down"
            found.append(
                Direction(parameter=name, sign=sign, strength=abs(shift), recent=name in recent)
            )
    found.sort(key=lambda direction: -direction.weight)  # stable: ties keep config order
    return found[: config.FORM_MAX_DIRECTIONS]


def form_keys(adapted_to: WorldState, recent: Collection[str] = ()) -> list[str]:
    """Picture keys to try, most specific first, always ending with the base form."""
    directions = adaptation_directions(adapted_to, recent)
    order = list(config.PARAMETERS)
    keys = []
    if len(directions) == 2:
        in_config_order = sorted(directions, key=lambda d: order.index(d.parameter))
        keys.append(KEY_SEPARATOR.join(d.key for d in in_config_order))
    singles = sorted(directions, key=lambda d: not d.recent)  # stable: recent ones first
    keys.extend(d.key for d in singles)
    keys.append(BASE_KEY)
    return keys