"""Environmental events and how they change a world."""

from pydantic import BaseModel, field_validator

from app.sim import config
from app.sim.models import WorldState


class Event(BaseModel):
    """One thing that can happen to the world.

    changes maps a parameter name to its change. For "ratio" parameters the
    number is a multiplier (2.0 = twice as much). For "linear" parameters it
    is an amount to add (-20 = twenty less).
    """

    id: str
    label: str
    description: str
    changes: dict[str, float]

    @field_validator("changes")
    @classmethod
    def known_parameters_only(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = set(value) - set(config.PARAMETERS)
        if unknown:
            raise ValueError(f"unknown world parameters: {sorted(unknown)}")
        return value


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def apply_event(world: WorldState, event: Event) -> WorldState:
    """Return a NEW world with the event applied. The old world is untouched."""
    values = world.model_dump()
    for name, change in event.changes.items():
        spec = config.PARAMETERS[name]
        limit = spec["max_event_change"]
        if spec["kind"] == "ratio":
            change = _clamp(change, 1 / limit, limit)
            new_value = values[name] * change
        else:
            change = _clamp(change, -limit, limit)
            new_value = values[name] + change
        values[name] = _clamp(new_value, spec["min"], spec["max"])
    return WorldState(**values)


def _preset(id: str, label: str, description: str, **changes: float) -> Event:
    return Event(id=id, label=label, description=description, changes=changes)


EVENTS = {
    e.id: e
    for e in [
        _preset("heavy_gravity", "Heavy Gravity",
                "The planet's gravity doubles.", gravity=2.0),
        _preset("ice_age", "Ice Age",
                "Global temperatures plunge.", temperature=-20.0),
        _preset("heatwave", "Heatwave",
                "Temperatures soar and surface water begins to evaporate.",
                temperature=20.0, water=-10.0),
        _preset("radiation_surge", "Radiation Surge",
                "A burst of cosmic radiation sweeps the surface.", radiation=2.0),
        _preset("thin_air", "Thin Air",
                "Atmospheric oxygen drops sharply.", oxygen=-6.0),
        _preset("great_flood", "Great Flood",
                "The oceans rise and swallow the lowlands.", water=20.0),
        _preset("great_drought", "Great Drought",
                "Rivers and lakes dry up across the world.", water=-25.0),
    ]
}