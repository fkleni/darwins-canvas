"""Base species: the creatures a lineage can start from."""

from pydantic import BaseModel, Field

from app.sim.models import Creature, WorldState

from app.sim.appearance import Appearance


class Species(BaseModel):
    """A starting species. Pure data: the simulation never special-cases one."""

    id: str
    name: str
    body_size: int = Field(ge=1, le=5)
    appearance: Appearance
    base_traits: tuple[str, ...] = ()
    visual_description: str = ""

    def founder(self) -> Creature:
        """The root of a lineage: depth 0, perfectly tuned to the starting planet."""
        world = WorldState.baseline()
        return Creature(
            name=self.name,
            depth=0,
            body_size=self.body_size,
            appearance=self.appearance,
            world=world,
            adapted_to=world.model_copy(),
        )


SPECIES = {
    s.id: s
    for s in [
        Species(
            id="human",
            name="Human",
            body_size=4,
            appearance=Appearance(
                skin_color="tan", eye_color="brown", eye_size="medium", pattern="none"),
            base_traits=(
                "upright bipedal posture",
                "large complex brain",
                "dexterous grasping hands",
                "mostly hairless skin",
            ),
            visual_description=(
                "an adult human standing upright in a neutral pose, plain simple clothing"
            ),
        ),
    ]
}

DEFAULT_SPECIES_ID = "human"