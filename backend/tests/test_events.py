import pytest
from pydantic import ValidationError

from app.sim import config
from app.sim.events import EVENTS, Event, apply_event
from app.sim.models import WorldState


def test_apply_event_returns_a_new_world_and_keeps_the_old_one():
    world = WorldState.baseline()
    new_world = apply_event(world, EVENTS["heavy_gravity"])
    assert new_world.gravity == 2.0
    assert world.gravity == 1.0


def test_a_single_event_change_is_capped():
    huge = Event(id="x", label="x", description="x", changes={"gravity": 1000})
    limit = config.PARAMETERS["gravity"]["max_event_change"]
    assert apply_event(WorldState.baseline(), huge).gravity == limit


def test_world_values_stay_inside_their_bounds():
    flood = Event(id="x", label="x", description="x", changes={"water": 30})
    world = WorldState.baseline().model_copy(update={"water": 95.0})
    assert apply_event(world, flood).water == 100.0


def test_event_rejects_an_unknown_parameter():
    with pytest.raises(ValidationError):
        Event(id="x", label="x", description="x", changes={"gravty": 2})