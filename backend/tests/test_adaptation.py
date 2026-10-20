import pytest

from app.sim import config
from app.sim.adaptation import (
    adapt,
    assess,
    bell_score,
    decide_status,
    exceeds_hard_limit,
    stress_distance,
)
from app.sim.models import Status, WorldState

CEILING = config.GRAVITY_CEILING_BY_BODY_SIZE[4]


# Design table: tied to SCORE_WIDTH. Update the numbers if you tune that value.
@pytest.mark.parametrize(
    "gap, expected",
    [(1.25, 94), (1.5, 82), (2, 55), (3, 23), (4, 9)],
)
def test_score_curve_matches_the_design_table(gap, expected):
    assert round(bell_score(stress_distance("ratio", gap, 1.0))) == expected


def test_a_perfectly_tuned_creature_scores_100():
    world = WorldState.baseline()
    assert assess(world, world, body_size=4, depth=1) == (100.0, Status.ALIVE)


def test_ratio_adaptation_speed_is_limited():
    adapted = WorldState.baseline()
    heavy = adapted.model_copy(update={"gravity": 2.0})
    limit = config.PARAMETERS["gravity"]["max_shift"]
    assert adapt(heavy, adapted).gravity == pytest.approx(limit)


def test_linear_adaptation_speed_is_limited():
    adapted = WorldState.baseline()
    hot = adapted.model_copy(update={"temperature": adapted.temperature + 20.0})
    limit = config.PARAMETERS["temperature"]["max_shift"]
    assert adapt(hot, adapted).temperature == pytest.approx(adapted.temperature + limit)


def test_gravity_at_the_ceiling_is_survivable():
    world = WorldState.baseline().model_copy(update={"gravity": CEILING})
    assert not exceeds_hard_limit(world, body_size=4)


def test_gravity_above_the_ceiling_is_fatal():
    world = WorldState.baseline().model_copy(update={"gravity": CEILING + 0.1})
    assert exceeds_hard_limit(world, body_size=4)


def test_hard_limit_overrides_a_perfect_fit():
    world = WorldState.baseline().model_copy(update={"gravity": CEILING + 1})
    final, status = assess(world, world, body_size=4, depth=config.GRACE_EVOLUTIONS + 1)
    assert final == 0.0
    assert status == Status.EXTINCT


def test_low_score_inside_the_grace_period_is_critical():
    score = config.SURVIVAL_THRESHOLD - 1
    assert decide_status(score, config.GRACE_EVOLUTIONS) == Status.CRITICAL


def test_low_score_after_the_grace_period_is_extinct():
    score = config.SURVIVAL_THRESHOLD - 1
    assert decide_status(score, config.GRACE_EVOLUTIONS + 1) == Status.EXTINCT


def test_a_score_exactly_at_the_threshold_survives():
    score = config.SURVIVAL_THRESHOLD
    assert decide_status(score, config.GRACE_EVOLUTIONS + 1) == Status.ALIVE