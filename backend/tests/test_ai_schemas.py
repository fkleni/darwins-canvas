import pytest
from pydantic import ValidationError

from app.ai.schemas import EventTranslation, Narration, ParameterChange


def narration_data(**overrides):
    data = {
        "name": "Frostback Walker",
        "description": "A stocky biped that roams the ice plains in small packs.",
        "traits": ["thick insulating fat", "broad snow-gripping feet"],
        "visual_notes": "Broad shoulders, heavy fur coat, low rounded ears.",
        "story": "When the ice came, only the stockiest survivors kept their warmth.",
    }
    data.update(overrides)
    return data


def event_data(**overrides):
    data = {
        "is_valid_event": True,
        "label": "Ice Age",
        "description": "Global temperatures plunge.",
        "changes": [{"parameter": "temperature", "change": -20}],
    }
    data.update(overrides)
    return data


# --- Narration --------------------------------------------------------


def test_a_complete_narration_is_accepted():
    assert Narration(**narration_data()).name == "Frostback Walker"


def test_text_is_stripped_of_surrounding_whitespace():
    assert Narration(**narration_data(name="  Frostback Walker  ")).name == "Frostback Walker"


def test_a_blank_name_is_rejected():
    with pytest.raises(ValidationError):
        Narration(**narration_data(name="   "))


@pytest.mark.parametrize(
    "traits",
    [["only one"], ["a one", "a two", "a three", "a four", "a five"]],
)
def test_traits_must_number_between_two_and_four(traits):
    with pytest.raises(ValidationError):
        Narration(**narration_data(traits=traits))


@pytest.mark.parametrize("bad_trait", ["x", "y" * 61])
def test_a_trait_must_be_a_short_phrase(bad_trait):
    with pytest.raises(ValidationError):
        Narration(**narration_data(traits=["fine trait", bad_trait]))


@pytest.mark.parametrize("model", [Narration, ParameterChange, EventTranslation])
def test_every_field_carries_a_description_for_the_model(model):
    missing = [name for name, field in model.model_fields.items() if not field.description]
    assert missing == []


# --- ParameterChange --------------------------------------------------


def test_an_unknown_parameter_is_rejected():
    with pytest.raises(ValidationError):
        ParameterChange(parameter="gravty", change=2)


@pytest.mark.parametrize("bad_multiplier", [0, -1])
def test_a_ratio_parameter_needs_a_positive_multiplier(bad_multiplier):
    with pytest.raises(ValidationError):
        ParameterChange(parameter="gravity", change=bad_multiplier)


def test_a_linear_parameter_may_be_negative():
    assert ParameterChange(parameter="temperature", change=-20).change == -20


# --- EventTranslation -------------------------------------------------


def test_a_valid_event_is_accepted_and_its_changes_are_parsed():
    translation = EventTranslation(**event_data())
    assert translation.changes[0].parameter == "temperature"


def test_a_valid_event_needs_at_least_one_change():
    with pytest.raises(ValidationError):
        EventTranslation(**event_data(changes=[]))


def test_a_valid_event_needs_a_label():
    with pytest.raises(ValidationError):
        EventTranslation(**event_data(label=None))


def test_a_parameter_may_not_appear_twice():
    twice = [
        {"parameter": "temperature", "change": -10},
        {"parameter": "temperature", "change": -5},
    ]
    with pytest.raises(ValidationError):
        EventTranslation(**event_data(changes=twice))


def test_a_rejected_event_needs_a_reason():
    with pytest.raises(ValidationError):
        EventTranslation(is_valid_event=False)


def test_a_rejected_event_with_a_reason_is_accepted():
    translation = EventTranslation(
        is_valid_event=False, rejection_reason="That is not a change to the environment."
    )
    assert not translation.is_valid_event