import random

import pytest

from app.sim import config
from app.sim.events import EVENTS, Event
from app.sim.evolve import ExtinctLineageError, evolve
from app.sim.models import Status
from app.sim.species import SPECIES


def founder():
    return SPECIES["human"].founder()


def run_chain(event_id, steps, seed=0):
    rng = random.Random(seed)
    creature = founder()
    chain = []
    for _ in range(steps):
        creature = evolve(creature, EVENTS[event_id], rng)
        chain.append(creature)
    return chain


# Design test: relies on gravity x2 per event and the human ceiling in config.
def test_doubling_gravity_kills_humans_by_the_third_evolution():
    first, second, third = run_chain("heavy_gravity", 3)
    assert [first.status, second.status, third.status] == [
        Status.ALIVE,
        Status.ALIVE,
        Status.EXTINCT,
    ]
    assert third.score == 0.0


def test_evolve_does_not_modify_the_parent():
    parent = founder()
    snapshot = parent.model_dump()
    evolve(parent, EVENTS["heavy_gravity"], random.Random(0))
    assert parent.model_dump() == snapshot


def test_an_extinct_creature_cannot_evolve():
    last = run_chain("heavy_gravity", 3)[-1]
    with pytest.raises(ExtinctLineageError):
        evolve(last, EVENTS["heavy_gravity"])


def test_the_grace_period_protects_the_first_evolutions():
    chain = run_chain("ice_age", 3)
    assert chain[1].score < config.SURVIVAL_THRESHOLD
    assert chain[1].status == Status.CRITICAL
    assert chain[2].status == Status.EXTINCT


def test_slow_change_is_survivable():
    slow = Event(id="slow", label="slow", description="slow", changes={"gravity": 1.3})
    creature = founder()
    for _ in range(5):
        creature = evolve(creature, slow, random.Random(0))
        assert creature.status == Status.ALIVE
        assert creature.score > 99


def test_a_child_records_its_mutation_and_the_root_has_none():
    root = founder()
    child = evolve(root, EVENTS["heavy_gravity"], random.Random(0))
    assert root.mutation is None
    assert child.mutation is not None