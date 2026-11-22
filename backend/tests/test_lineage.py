import pytest
from pydantic import ValidationError

from app.ai.lineage import (
    MAX_TRAITS,
    RECENT_EVENTS,
    descend,
    founder_chronicle,
    history_text,
    merge_traits,
)
from app.ai.schemas import Narration
from app.sim.species import DEFAULT_SPECIES


def narration(name="Frostback Walker", traits=("thick fat layer", "broad snow-gripping feet")):
    return Narration(
        name=name,
        description="A stocky predator that roams the ice plains in small packs.",
        traits=list(traits),
        visual_notes="Broad shoulders, heavy fur coat, low rounded ears.",
        story="When the ice came, only the stockiest survivors kept their warmth.",
    )


def test_merge_traits_ignores_duplicates_regardless_of_case_and_spacing():
    assert merge_traits(("Thick Fat",), ["thick fat ", "new trait"]) == ("Thick Fat", "new trait")


def test_merge_traits_keeps_inherited_first_then_new():
    assert merge_traits(("a trait", "b trait"), ["c trait"]) == ("a trait", "b trait", "c trait")


def test_merge_traits_keeps_the_newest_when_over_the_cap():
    inherited = tuple(f"old trait {i}" for i in range(MAX_TRAITS))
    result = merge_traits(inherited, ["fresh trait a", "fresh trait b"])
    assert len(result) == MAX_TRAITS
    assert result[-2:] == ("fresh trait a", "fresh trait b")
    assert result[0] == "old trait 2"


def test_a_founder_starts_from_the_species_name_and_base_traits():
    species = DEFAULT_SPECIES
    chronicle = founder_chronicle(species)
    assert chronicle.name == species.name
    assert chronicle.origin == species.name
    assert chronicle.traits == species.base_traits
    assert chronicle.recent_events == ()


def test_a_descendant_inherits_traits_and_remembers_the_event():
    parent = founder_chronicle(DEFAULT_SPECIES)
    child = descend(parent, narration(), "Ice Age")
    assert child.name == "Frostback Walker"
    assert set(parent.traits) <= set(child.traits)
    assert "thick fat layer" in child.traits
    assert child.recent_events == ("Ice Age",)


def test_a_descendant_keeps_the_origin_of_the_lineage():
    parent = founder_chronicle(DEFAULT_SPECIES)
    child = descend(parent, narration(), "Ice Age")
    grandchild = descend(child, narration(name="Second Form"), "Heavy Gravity")
    assert grandchild.origin == DEFAULT_SPECIES.name


def test_only_the_most_recent_events_are_remembered():
    chronicle = founder_chronicle(DEFAULT_SPECIES)
    labels = [f"Event {i}" for i in range(RECENT_EVENTS + 2)]
    for label in labels:
        chronicle = descend(chronicle, narration(), label)
    assert chronicle.recent_events == tuple(labels[-RECENT_EVENTS:])


def test_history_text_for_a_founder_says_nothing_happened_yet():
    text = history_text(founder_chronicle(DEFAULT_SPECIES))
    assert "none yet" in text
    assert DEFAULT_SPECIES.name in text


def test_history_text_lists_events_oldest_first():
    chronicle = founder_chronicle(DEFAULT_SPECIES)
    chronicle = descend(chronicle, narration(), "Heavy Gravity")
    chronicle = descend(chronicle, narration(name="Second Form"), "Ice Age")
    text = history_text(chronicle)
    assert "Heavy Gravity -> Ice Age" in text
    assert "Second Form" in text


def test_a_chronicle_is_read_only():
    chronicle = founder_chronicle(DEFAULT_SPECIES)
    with pytest.raises(ValidationError):
        chronicle.name = "Somebody Else"