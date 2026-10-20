"""Data shapes of the simulation: what a world and a creature look like."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.sim import config

from app.sim import config
from app.sim.appearance import Appearance, Mutation


class WorldState(BaseModel):
    """The numbers describing an environment, or what a creature is adapted to."""

    gravity: float = Field(gt=0)
    radiation: float = Field(gt=0)
    temperature: float
    oxygen: float = Field(ge=0, le=100)
    water: float = Field(ge=0, le=100)

    @classmethod
    def baseline(cls) -> "WorldState":
        """The starting planet: every parameter at its baseline from config."""
        return cls(**{name: spec["baseline"] for name, spec in config.PARAMETERS.items()})


class Status(StrEnum):
    ALIVE = "alive"
    CRITICAL = "critical"
    EXTINCT = "extinct"


class Creature(BaseModel):
    """One node of the evolution tree, as far as the simulation cares."""

    name: str
    depth: int = Field(ge=0)  # 0 = the base species
    body_size: int = Field(ge=1, le=5)
    appearance: Appearance
    world: WorldState  # the world this creature lives in
    adapted_to: WorldState  # the world its body is tuned for
    score: float | None = Field(default=None, ge=0, le=100)  # None for the base species
    status: Status = Status.ALIVE
    mutation: Mutation | None = None  # what changed from the parent, None for the base species