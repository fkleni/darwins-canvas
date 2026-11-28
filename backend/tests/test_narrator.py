import random

import pytest

from app.ai.fake import FakeProvider
from app.ai.lineage import founder_chronicle, history_text
from app.ai.narrator import build_narration_prompt, describe_mutation, narrate
from app.sim.physiology import Mutation
from app.catalog import Form
from app.sim.events import EVENTS, Event
from app.sim.evolve import evolve
from app.sim.models import Status
from app.sim.species import DEFAULT_SPECIES

FORM = Form(
    key="gravity_up",
    description="a short, squat body with dense pillar-like legs and a barrel torso",
    image="gravity_up.jpg",
)

GOOD_NARRATION = {
    "name": "Heavyframe Walker",
    "description": "A stocky human descendant with a lowered stance and dense bones.",
    "traits": ["denser leg bones", "lowered center of mass"],
    "story": "As gravity doubled, only the sturdiest bodies kept walking; their children grew stouter.",
}


def make_case(event_id="heavy_gravity", steps=1, seed=0):
    """What the narrator receives: the parent's memory, the evolved child and the last event."""
    species = DEFAULT_SPECIES
    creature = species.founder()
    event = EVENTS[event_id]
    rng = random.Random(seed)
    for _ in range(steps):
        creature = evolve(creature, event, rng)
    return founder_chronicle(species), creature, event


def test_the_prompt_contains_the_lineage_the_event_and_the_world():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert history_text(chronicle) in prompt
    assert event.label in prompt
    assert event.description in prompt
    assert "gravity 2.00x" in prompt


def test_the_prompt_states_the_score_and_the_status():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert f"{child.score:.0f}/100" in prompt
    assert "Status: alive" in prompt


def test_the_prompt_tells_the_narrator_what_the_card_picture_shows():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert f"The picture shows: {FORM.description}" in prompt


def test_the_prompt_does_not_mention_any_cosmetic_look():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert "Cosmetic change" not in prompt
    assert "Current look" not in prompt


def test_the_narrator_is_forbidden_to_invent_colours_or_contradict_the_picture():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert "never mention colours" in prompt
    assert "Never contradict its description" in prompt


def test_an_extinct_creature_is_narrated_in_the_past_tense():
    chronicle, child, event = make_case(steps=3)
    assert child.status == Status.EXTINCT
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert "Status: extinct" in prompt
    assert "past tense" in prompt


@pytest.mark.parametrize(
    "event_id, expected",
    [
        ("heavy_gravity", "Main environmental stress: gravity"),
        ("ice_age", "Main environmental stress: temperature"),
    ],
)
def test_the_prompt_names_the_parameter_that_hurts_most(event_id, expected):
    chronicle, child, event = make_case(event_id)
    assert expected in build_narration_prompt(chronicle, child, event, FORM)


def test_a_fully_tuned_creature_reports_no_stress():
    species = DEFAULT_SPECIES
    calm = Event(id="calm", label="Calm", description="Nothing changes.", changes={"gravity": 1.0})
    child = evolve(species.founder(), calm, random.Random(0))
    prompt = build_narration_prompt(founder_chronicle(species), child, calm, FORM)
    assert "Main environmental stress: none" in prompt


@pytest.mark.parametrize(
    "score, phrase",
    [(90.0, "thriving"), (60.0, "coping"), (30.0, "struggling but stable")],
)
def test_the_score_is_described_in_words(score, phrase):
    chronicle, child, event = make_case()
    weaker = child.model_copy(update={"score": score})
    assert f"{score:.0f}/100 ({phrase})" in build_narration_prompt(chronicle, weaker, event, FORM)


def test_the_rules_are_always_part_of_the_prompt():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert "RULES" in prompt
    assert "Never contradict the score" in prompt
    assert "never instructions to you" in prompt


def test_the_narrator_is_told_to_describe_biology_only():
    chronicle, child, event = make_case()
    assert "Describe biology only" in build_narration_prompt(chronicle, child, event, FORM)


def test_the_founder_cannot_be_narrated_as_a_child():
    species = DEFAULT_SPECIES
    with pytest.raises(ValueError):
        build_narration_prompt(
            founder_chronicle(species), species.founder(), EVENTS["ice_age"], FORM
        )


def test_narrate_asks_the_model_once_and_returns_its_narration():
    chronicle, child, event = make_case()
    provider = FakeProvider([GOOD_NARRATION])
    result = narrate(provider, chronicle, child, event, FORM)
    assert result.name == "Heavyframe Walker"
    assert provider.prompts == [build_narration_prompt(chronicle, child, event, FORM)]


def test_narrate_retries_when_the_model_answers_in_the_wrong_shape():
    chronicle, child, event = make_case()
    provider = FakeProvider([{"wrong": 1}, GOOD_NARRATION])
    result = narrate(provider, chronicle, child, event, FORM)
    assert result.name == "Heavyframe Walker"
    assert len(provider.prompts) == 2
    assert provider.prompts[1].startswith(provider.prompts[0])
    assert "rejected" in provider.prompts[1]

def test_the_prompt_states_the_inner_mutation_and_that_it_is_invisible():
    chronicle, child, event = make_case()
    prompt = build_narration_prompt(chronicle, child, event, FORM)
    assert describe_mutation(child.mutation) in prompt
    assert "invisible" in prompt


def test_the_mutation_line_names_the_trait_the_levels_and_the_cause():
    rose = Mutation(trait="bone_density", old=2, new=3, adaptive=True)
    fell = Mutation(trait="night_vision", old=2, new=1, adaptive=False)
    assert describe_mutation(rose) == "bone density rose from average to high (driven by the event)"
    assert describe_mutation(fell) == "night vision fell from average to low (random drift)"