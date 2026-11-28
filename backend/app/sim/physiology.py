"""Hidden inner traits of a creature: the body details no picture can show."""

from pydantic import BaseModel, ConfigDict, Field

LEVEL_NAMES = ("very low", "low", "average", "high", "very high")
START_LEVEL = 2
MAX_LEVEL = len(LEVEL_NAMES) - 1


class Physiology(BaseModel):
    """Five-step levels (0 to 4) of the inner traits. Read-only once created."""

    model_config = ConfigDict(frozen=True)

    bone_density: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)
    cellular_repair: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)
    metabolic_rate: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)
    lung_efficiency: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)
    water_retention: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)
    night_vision: int = Field(default=START_LEVEL, ge=0, le=MAX_LEVEL)


TRAITS = tuple(Physiology.model_fields)


class Mutation(BaseModel):
    """A record of the one inner change between a parent and its child."""

    model_config = ConfigDict(frozen=True)

    trait: str
    old: int
    new: int
    adaptive: bool  # True when an event pushed the change, False when it was pure chance