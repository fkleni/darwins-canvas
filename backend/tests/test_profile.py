import pytest

from app.sim import config
from app.sim.models import WorldState
from app.sim.profile import BASE_KEY, Direction, adaptation_directions, form_keys


def adapted(**changes):
    return WorldState.baseline().model_copy(update=changes)


def test_a_body_still_tuned_to_the_baseline_has_no_adaptation():
    assert adaptation_directions(WorldState.baseline()) == []
    assert form_keys(WorldState.baseline()) == [BASE_KEY]


def test_a_ratio_parameter_is_measured_as_a_logarithm():
    (direction,) = adaptation_directions(adapted(gravity=1.6))
    assert (direction.parameter, direction.sign) == ("gravity", "up")
    assert direction.strength == pytest.approx(0.47, abs=0.01)


def test_a_linear_parameter_is_measured_in_units_of_its_scale():
    (direction,) = adaptation_directions(adapted(temperature=7.0))
    assert (direction.parameter, direction.sign) == ("temperature", "down")
    assert direction.strength == pytest.approx(8 / 12)


def test_the_sign_follows_the_direction_of_the_change():
    (direction,) = adaptation_directions(adapted(gravity=0.5))
    assert direction.sign == "down"


def test_small_shifts_do_not_count():
    assert adaptation_directions(adapted(gravity=1.2)) == []


def test_a_shift_beyond_the_threshold_counts():
    assert [d.key for d in adaptation_directions(adapted(gravity=1.4))] == ["gravity_up"]


def test_only_the_strongest_directions_are_kept_strongest_first():
    world = adapted(gravity=1.6, temperature=7.0, water=85.0)
    keys = [d.key for d in adaptation_directions(world)]
    assert keys == ["temperature_down", "water_up"]
    assert len(keys) == config.FORM_MAX_DIRECTIONS


def test_two_directions_give_a_pair_key_in_config_order_then_the_singles():
    world = adapted(gravity=1.6, temperature=7.0)
    assert form_keys(world) == [
        "gravity_up__temperature_down",
        "temperature_down",
        "gravity_up",
        BASE_KEY,
    ]


def test_one_direction_gives_that_key_then_the_base():
    assert form_keys(adapted(gravity=1.6)) == ["gravity_up", BASE_KEY]


def test_a_direction_has_a_key_made_of_its_parameter_and_sign():
    assert Direction(parameter="oxygen", sign="down", strength=0.5).key == "oxygen_down"


# --- the latest event ---------------------------------------------------


def test_a_recent_adaptation_is_weighted_up_for_ranking():
    plain = Direction(parameter="gravity", sign="up", strength=0.5)
    recent = Direction(parameter="gravity", sign="up", strength=0.5, recent=True)
    assert plain.weight == 0.5
    assert recent.weight == pytest.approx(0.5 * config.FORM_RECENT_BOOST)


def test_a_recent_adaptation_can_displace_an_older_weaker_one():
    world = adapted(temperature=-1.0, water=85.0, gravity=1.6)
    without = [d.key for d in adaptation_directions(world)]
    with_recent = [d.key for d in adaptation_directions(world, recent=("gravity",))]
    assert without == ["temperature_down", "water_up"]
    assert with_recent == ["temperature_down", "gravity_up"]


def test_a_recent_adaptation_below_the_threshold_still_does_not_count():
    assert adaptation_directions(adapted(gravity=1.2), recent=("gravity",)) == []


def test_among_the_singles_the_recent_one_comes_first():
    world = adapted(gravity=1.6, temperature=-1.0)
    assert form_keys(world, recent=("gravity",)) == [
        "gravity_up__temperature_down",
        "gravity_up",
        "temperature_down",
        BASE_KEY,
    ]


def test_without_a_recent_parameter_the_strongest_single_comes_first():
    world = adapted(gravity=1.6, temperature=-1.0)
    assert form_keys(world) == [
        "gravity_up__temperature_down",
        "temperature_down",
        "gravity_up",
        BASE_KEY,
    ]