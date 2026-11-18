import random

import pytest
from pydantic import ValidationError

from app.ai.image_prompt import (
    COVERING,
    FOSSIL_STYLE,
    IMAGE_SIZE,
    STRICT_COVERING,
    STYLE,
    appearance_phrase,
    build_founder_image_request,
    build_image_request,
    lineage_seed,
    retry_request,
    scrub_counts,
)
from app.ai.schemas import Narration
from app.sim.appearance import Appearance
from app.sim.events import EVENTS
from app.sim.evolve import evolve
from app.sim.models import Status
from app.sim.species import SPECIES

HUMAN = SPECIES["human"]


def narration(visual_notes="Broad shoulders, thick legs, a slightly stooped posture."):
    return Narration(
        name="Heavyframe Walker",
        description="A stocky human descendant with a lowered stance and dense bones.",
        traits=["denser leg bones", "lowered center of mass"],
        visual_notes=visual_notes,
        story="As gravity doubled, only the sturdiest bodies kept walking on.",
    )


def child_after(steps):
    creature = HUMAN.founder()
    rng = random.Random(0)
    for _ in range(steps):
        creature = evolve(creature, EVENTS["heavy_gravity"], rng)
    return creature


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Six thick legs and two eyes.", "thick legs and eyes."),
        ("A four-legged crawler", "A crawler"),
        ("eight long arms", "long arms"),
        ("2 large eyes", "large eyes"),
        ("Broad shoulders, heavy fur coat", "Broad shoulders, heavy fur coat"),
        ("a single dark patch on the back", "a single dark patch on the back"),
    ],
)
def test_counts_of_body_parts_are_removed(text, expected):
    assert scrub_counts(text) == expected


def test_the_founders_look_in_words():
    assert appearance_phrase(HUMAN.appearance) == "tan skin, brown eyes, no markings"


def test_eye_size_and_pattern_appear_in_the_look():
    look = Appearance(skin_color="pale", eye_color="blue", eye_size="large", pattern="spotted")
    assert appearance_phrase(look) == "pale skin, large blue eyes, spotted markings"


def test_the_prompt_starts_with_the_style_and_names_the_ancestry():
    request = build_image_request(narration(), child_after(1), "Human", seed=1)
    assert request.prompt.startswith(STYLE)
    assert "evolved from human ancestors" in request.prompt


def test_the_prompt_uses_the_look_decided_by_the_simulation():
    child = child_after(1)
    request = build_image_request(narration(), child, "Human", seed=1)
    assert appearance_phrase(child.appearance) in request.prompt


def test_the_prompt_carries_the_visual_notes_without_counts():
    request = build_image_request(
        narration("Six thick legs and a long tail."), child_after(1), "Human", seed=1
    )
    assert "thick legs and a long tail" in request.prompt
    assert "Six" not in request.prompt


def test_an_extinct_creature_is_drawn_as_a_fossil_without_skin_colour():
    child = child_after(3)
    assert child.status == Status.EXTINCT
    request = build_image_request(narration(), child, "Human", seed=1)
    assert request.prompt.startswith(FOSSIL_STYLE)
    assert appearance_phrase(child.appearance) not in request.prompt


def test_a_living_descendant_is_always_described_as_covered():
    request = build_image_request(narration(), child_after(1), "Human", seed=1)
    assert COVERING in request.prompt


def test_a_fossil_prompt_has_no_covering_clause():
    request = build_image_request(narration(), child_after(3), "Human", seed=1)
    assert COVERING not in request.prompt


def test_even_the_longest_notes_keep_the_prompt_short_enough_for_a_url():
    notes = " ".join(["stocky"] * 40)[:200]
    request = build_image_request(narration(notes), child_after(1), "Human", seed=1)
    assert len(request.prompt) < 700


def test_the_seed_and_the_default_size_are_carried():
    request = build_image_request(narration(), child_after(1), "Human", seed=123)
    assert request.seed == 123
    assert (request.width, request.height) == (IMAGE_SIZE, IMAGE_SIZE)


def test_the_same_lineage_always_gets_the_same_seed():
    assert lineage_seed("lineage-1") == lineage_seed("lineage-1")


def test_different_lineages_get_different_seeds():
    assert lineage_seed("lineage-1") != lineage_seed("lineage-2")


def test_a_seed_fits_in_a_signed_32_bit_integer():
    assert 0 <= lineage_seed("anything") < 2**31


def test_the_founder_prompt_describes_the_species_and_its_look():
    request = build_founder_image_request(HUMAN, seed=1)
    assert request.prompt.startswith(STYLE)
    assert "adult human" in request.prompt
    assert appearance_phrase(HUMAN.appearance) in request.prompt


def test_a_species_without_a_visual_description_is_refused():
    blank = HUMAN.model_copy(update={"visual_description": ""})
    with pytest.raises(ValueError):
        build_founder_image_request(blank, seed=1)


def test_an_image_request_is_read_only():
    request = build_founder_image_request(HUMAN, seed=1)
    with pytest.raises(ValidationError):
        request.seed = 2


def test_a_retry_request_has_a_new_seed_and_a_stricter_covering():
    original = build_founder_image_request(HUMAN, seed=10)
    retry = retry_request(original, attempt=2)
    assert retry.seed != original.seed
    assert retry.prompt.startswith(original.prompt)
    assert STRICT_COVERING in retry.prompt


def test_a_retry_request_leaves_the_original_untouched():
    original = build_founder_image_request(HUMAN, seed=10)
    before = original.model_dump()
    retry_request(original, attempt=2)
    assert original.model_dump() == before


def test_retry_seeds_differ_by_attempt_and_stay_in_range():
    original = build_founder_image_request(HUMAN, seed=2**31 - 2)
    seeds = {retry_request(original, attempt).seed for attempt in (2, 3)}
    assert len(seeds) == 2
    assert all(0 <= seed < 2**31 for seed in seeds)


def test_even_a_retry_prompt_stays_short_enough_for_a_url():
    notes = " ".join(["stocky"] * 40)[:200]
    request = build_image_request(narration(notes), child_after(1), "Human", seed=1)
    assert len(retry_request(request, attempt=3).prompt) < 800