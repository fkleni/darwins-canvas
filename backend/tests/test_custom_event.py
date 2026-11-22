import math
import random

import pytest

from app.sim import config
from app.sim.events import EVENTS, apply_event, custom_event, parameter_range
from app.sim.evolve import evolve
from app.sim.models import WorldState
from app.sim.species import DEFAULT_SPECIES


def test_the_gravity_slider_runs_from_a_third_to_triple():
    assert parameter_range("gravity") == (pytest.approx(1 / 3), 1.0, 3.0)


def test_a_single_slider_makes_a_single_change():
    assert custom_event({"gravity": 2.0}).changes == {"gravity": 2.0}


def test_sliders_left_at_neutral_are_dropped():
    event = custom_event({"gravity": 2.0, "radiation": 1.0, "temperature": 0.0})
    assert event.changes == {"gravity": 2.0}


@pytest.mark.parametrize("values", [{}, {"gravity": 1.0}, {"gravity": 1.0, "water": 0.0}])
def test_an_event_that_changes_nothing_is_refused(values):
    with pytest.raises(ValueError):
        custom_event(values)


def test_an_unknown_parameter_is_refused():
    with pytest.raises(ValueError):
        custom_event({"gravty": 2.0})


@pytest.mark.parametrize(
    "name, value",
    [("gravity", 5.0), ("gravity", 0.1), ("temperature", 40.0), ("oxygen", -9.0)],
)
def test_a_value_outside_the_slider_range_is_refused(name, value):
    with pytest.raises(ValueError):
        custom_event({name: value})


@pytest.mark.parametrize("name", list(config.PARAMETERS))
def test_both_ends_of_every_slider_are_accepted(name):
    low, _, high = parameter_range(name)
    assert custom_event({name: low}).changes == {name: low}
    assert custom_event({name: high}).changes == {name: high}


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_refused(bad):
    with pytest.raises(ValueError):
        custom_event({"temperature": bad})


def test_the_description_lists_changes_in_a_fixed_order_with_units():
    event = custom_event({"temperature": -10.0, "gravity": 2.0})
    assert event.description == "gravity x2, temperature -10 C"


def test_percentage_parameters_show_a_sign_and_a_percent_sign():
    assert custom_event({"oxygen": 4.0}).description == "oxygen +4%"


def test_a_custom_event_changes_the_world_like_any_other_event():
    event = custom_event({"gravity": 2.0, "water": -10.0})
    world = apply_event(WorldState.baseline(), event)
    assert world.gravity == 2.0
    assert world.water == 60.0


def test_a_custom_event_can_drive_an_evolution_step():
    child = evolve(DEFAULT_SPECIES.founder(), custom_event({"gravity": 2.0}), random.Random(0))
    assert child.depth == 1
    assert round(child.score) == 94


@pytest.mark.parametrize("event_id", list(EVENTS))
def test_every_preset_can_be_expressed_as_slider_values(event_id):
    preset = EVENTS[event_id]
    assert custom_event(preset.changes).changes == preset.changes