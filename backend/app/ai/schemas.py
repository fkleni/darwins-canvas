"""The shapes of what we ask the language model to return."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.sim import config


class Narration(BaseModel):
    """The story side of a new creature.

    Score, status and extinction are NOT here on purpose: the simulation owns
    the numbers, the model only tells the story around them.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        min_length=2,
        max_length=40,
        description="A short, memorable species name of one to three words.",
    )
    description: str = Field(
        min_length=10,
        max_length=300,
        description="One or two sentences describing the creature and how it lives.",
    )
    traits: list[str] = Field(
        min_length=2,
        max_length=4,
        description="Two to four adaptive physical traits, each a short phrase.",
    )
    visual_notes: str = Field(
        min_length=10,
        max_length=200,
        description=(
            "Concrete visible features for an illustrator: shape, posture, texture. "
            "Never count limbs, eyes or fingers."
        ),
    )
    story: str = Field(
        min_length=20,
        max_length=500,
        description="Two or three sentences telling how this creature came to be, or why it perished.",
    )

    @field_validator("traits")
    @classmethod
    def traits_must_be_short_phrases(cls, value: list[str]) -> list[str]:
        for trait in value:
            if not 3 <= len(trait.strip()) <= 60:
                raise ValueError("each trait must be between 3 and 60 characters")
        return value


class ParameterChange(BaseModel):
    """One change to one world parameter, as proposed by the model."""

    parameter: str = Field(
        description="Exactly one of: gravity, radiation, temperature, oxygen, water."
    )
    change: float = Field(
        description=(
            "For gravity and radiation: a multiplier (2.0 means twice as strong, 0.5 half). "
            "For temperature (degrees C), oxygen and water (percentage points): an amount "
            "to add, negative to subtract."
        )
    )

    @model_validator(mode="after")
    def parameter_must_exist_and_make_sense(self) -> "ParameterChange":
        spec = config.PARAMETERS.get(self.parameter)
        if spec is None:
            raise ValueError(
                f"unknown parameter {self.parameter!r}; options: {sorted(config.PARAMETERS)}"
            )
        if spec["kind"] == "ratio" and self.change <= 0:
            raise ValueError(f"{self.parameter} is a multiplier and must be positive")
        return self


class EventTranslation(BaseModel):
    """The model's reading of a free-text event written by the user."""

    model_config = ConfigDict(str_strip_whitespace=True)

    is_valid_event: bool = Field(
        description=(
            "True only if the text describes a physical change to the planet's environment "
            "(gravity, radiation, temperature, oxygen, water). False for anything else."
        )
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=200,
        description="When is_valid_event is false: a short, polite reason. Otherwise null.",
    )
    label: str | None = Field(
        default=None,
        max_length=40,
        description="When valid: a short button-style name for the event. Otherwise null.",
    )
    description: str | None = Field(
        default=None,
        max_length=200,
        description="When valid: one sentence describing what happens to the planet. Otherwise null.",
    )
    changes: list[ParameterChange] = Field(
        default_factory=list,
        max_length=len(config.PARAMETERS),
        description="When valid: the world parameters that change. Otherwise an empty list.",
    )

    @model_validator(mode="after")
    def fields_must_match_validity(self) -> "EventTranslation":
        if self.is_valid_event:
            if not (self.label and self.description):
                raise ValueError("a valid event needs a label and a description")
            if not self.changes:
                raise ValueError("a valid event needs at least one change")
            names = [change.parameter for change in self.changes]
            if len(names) != len(set(names)):
                raise ValueError("each parameter may appear only once")
        elif not self.rejection_reason:
            raise ValueError("a rejected event needs a rejection_reason")
        return self