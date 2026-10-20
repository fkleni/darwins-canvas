import random

import pytest
from pydantic import ValidationError

from app.sim.appearance import SKIN_DARKNESS, Appearance, neighbours
from app.sim.events import EVENTS
from app.sim.mutation import mutate, pressure_from_event
from app.sim.species import SPECIES

HUMAN_LOOK = SPECIES["human"].appearance


def test_pink_is_not_a_valid_skin_color():
    with pytest.raises(ValidationError):
        Appearance(skin_color="pink", eye_color="brown", eye_size="medium", pattern="none")


def test_appearance_is_read_only():
    with pytest.raises(ValidationError):
        HUMAN_LOOK.skin_color = "pale"


def test_event_pressure_directions():
    assert pressure_from_event(EVENTS["ice_age"]) == "lighter"
    assert pressure_from_event(EVENTS["radiation_surge"]) == "darker"
    assert pressure_from_event(EVENTS["heavy_gravity"]) is None


@pytest.mark.parametrize("seed", range(50))
def test_a_mutation_is_one_trait_one_step_to_a_neighbour(seed):
    old = HUMAN_LOOK.model_dump()
    new_look, mutation = mutate(HUMAN_LOOK, EVENTS["ice_age"], random.Random(seed))
    changed = [name for name, value in new_look.model_dump().items() if value != old[name]]
    assert changed == [mutation.trait]
    assert mutation.new in neighbours(mutation.trait, mutation.old)


def test_the_same_seed_gives_the_same_mutation():
    first = mutate(HUMAN_LOOK, EVENTS["ice_age"], random.Random(7))
    second = mutate(HUMAN_LOOK, EVENTS["ice_age"], random.Random(7))
    assert first == second


def test_pressured_mutations_follow_the_pressure():
    mutations = [
        mutate(HUMAN_LOOK, EVENTS["ice_age"], random.Random(seed))[1] for seed in range(200)
    ]
    adaptive = [m for m in mutations if m.adaptive]
    assert adaptive
    assert all(m.trait == "skin_color" for m in adaptive)
    assert all(SKIN_DARKNESS[m.new] < SKIN_DARKNESS[m.old] for m in adaptive)


def test_no_pressure_means_no_adaptive_mutation():
    for seed in range(200):
        _, mutation = mutate(HUMAN_LOOK, EVENTS["heavy_gravity"], random.Random(seed))
        assert not mutation.adaptive