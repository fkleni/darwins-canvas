"""Base species: the creatures a lineage can start from."""

from pydantic import BaseModel, Field

from app.sim.appearance import Appearance
from app.sim.models import Creature, WorldState


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
            id="gray_wolf",
            name="Gray Wolf",
            body_size=4,
            appearance=Appearance(
                skin_color="slate", eye_color="amber", eye_size="medium", pattern="none"
            ),
            base_traits=(
                "four-legged running stance",
                "keen sense of smell",
                "thick double-layered fur",
                "strong jaws and sharp teeth",
            ),
            visual_description=(
                "an adult gray wolf standing alert on all fours, long legs, "
                "lean athletic build, seen from the side"
            ),
        ),
    ]
}

DEFAULT_SPECIES_ID = "gray_wolf"
DEFAULT_SPECIES = SPECIES[DEFAULT_SPECIES_ID]