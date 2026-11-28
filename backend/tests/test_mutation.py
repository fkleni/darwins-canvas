import random

import pytest
from pydantic import ValidationError

from app.sim import config
from app.sim.events import EVENTS, Event
from app.sim.mutation import RESPONSES, mutate, pushes_from_event
from app.sim.physiology import MAX_LEVEL, START_LEVEL, TRAITS, Physiology

START = Physiology()
QUIET = Event(id="quiet", label="Quiet", description="Nothing changes.", changes={"gravity": 1.0})


def maxed(**overrides):
    values = {trait: MAX_LEVEL for trait in TRAITS}
    values.update(overrides)
    return Physiology(**values)


def test_a_new_physiology_starts_average_everywhere():
    assert all(getattr(START, trait) == START_LEVEL for trait in TRAITS)


def test_a_physiology_is_read_only():
    with pytest.raises(ValidationError):
        START.bone_density = 4


def test_levels_must_stay_on_the_scale():
    with pytest.raises(ValidationError):
        Physiology(bone_density=MAX_LEVEL + 1)


def test_every_direction_of_every_parameter_has_a_response():
    expected = {(name, way) for name in config.PARAMETERS for way in ("up", "down")}
    assert set(RESPONSES) == expected


@pytest.mark.parametrize(
    "event_id, expected",
    [
        ("heavy_gravity", [("bone_density", 1)]),
        ("ice_age", [("metabolic_rate", 1)]),
        ("heatwave", [("metabolic_rate", -1), ("water_retention", 1)]),
    ],
)
def test_pushes_follow_the_direction_of_each_change(event_id, expected):
    assert pushes_from_event(EVENTS[event_id]) == expected


def test_an_event_that_changes_nothing_pushes_nothing():
    assert pushes_from_event(QUIET) == []


@pytest.mark.parametrize("seed", range(50))
def test_a_mutation_is_one_trait_one_step(seed):
    new, mutation = mutate(START, EVENTS["ice_age"], random.Random(seed))
    changed = [t for t in TRAITS if getattr(new, t) != getattr(START, t)]
    assert changed == [mutation.trait]
    assert abs(mutation.new - mutation.old) == 1
    assert 0 <= mutation.new <= MAX_LEVEL


def test_the_same_seed_gives_the_same_mutation():
    first = mutate(START, EVENTS["ice_age"], random.Random(7))
    second = mutate(START, EVENTS["ice_age"], random.Random(7))
    assert first == second


def test_pressured_mutations_follow_the_pressure():
    mutations = [mutate(START, EVENTS["heavy_gravity"], random.Random(s))[1] for s in range(200)]
    adaptive = [m for m in mutations if m.adaptive]
    assert adaptive
    assert all(m.trait == "bone_density" and m.new == m.old + 1 for m in adaptive)


def test_no_pressure_means_no_adaptive_mutation():
    for seed in range(200):
        _, mutation = mutate(START, QUIET, random.Random(seed))
        assert not mutation.adaptive


def test_a_trait_at_the_top_of_the_scale_can_only_fall():
    for seed in range(100):
        _, mutation = mutate(maxed(), QUIET, random.Random(seed))
        assert mutation.new == MAX_LEVEL - 1


def test_a_pushed_trait_that_cannot_move_falls_back_to_chance():
    stuck = maxed(bone_density=MAX_LEVEL)
    for seed in range(100):
        _, mutation = mutate(stuck, EVENTS["heavy_gravity"], random.Random(seed))
        assert not mutation.adaptive