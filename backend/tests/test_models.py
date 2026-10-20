import pytest
from pydantic import ValidationError

from app.sim import config
from app.sim.models import Creature, WorldState
from app.sim.species import SPECIES


def test_baseline_world_matches_config():
    world = WorldState.baseline().model_dump()
    for name, spec in config.PARAMETERS.items():
        assert world[name] == spec["baseline"]


def test_creature_rejects_a_body_size_outside_1_to_5():
    data = SPECIES["human"].founder().model_dump()
    data["body_size"] = 9
    with pytest.raises(ValidationError):
        Creature.model_validate(data)


def test_gravity_must_be_positive():
    with pytest.raises(ValidationError):
        WorldState(gravity=0, radiation=1, temperature=15, oxygen=21, water=70)