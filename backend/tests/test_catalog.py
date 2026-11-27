import json
import random
from pathlib import Path

import pytest

from app.catalog import CatalogError, FormCatalog
from app.sim.events import EVENTS
from app.sim.evolve import evolve
from app.sim.models import Status, WorldState
from app.sim.species import DEFAULT_SPECIES

SHIPPED = Path(__file__).parent.parent / "assets" / "forms"


def make_folder(tmp_path, descriptions, pictures):
    (tmp_path / "forms.json").write_text(json.dumps(descriptions), encoding="utf-8")
    for name in pictures:
        (tmp_path / name).write_bytes(b"fake picture")
    return tmp_path


def creature(changed=(), **adapted_changes):
    founder = DEFAULT_SPECIES.founder()
    adapted = WorldState.baseline().model_copy(update=adapted_changes)
    return founder.model_copy(update={"adapted_to": adapted, "changed": changed})


def full_folder(tmp_path, pictures):
    keys = {name.split(".")[0] for name in pictures}
    return make_folder(tmp_path, {key: f"description of {key}" for key in keys}, pictures)


def test_a_complete_folder_loads(tmp_path):
    folder = make_folder(tmp_path, {"base": "a human"}, ["base.jpg"])
    assert FormCatalog.load(folder).find("base").image == "base.jpg"


def test_a_missing_descriptions_file_is_refused(tmp_path):
    (tmp_path / "base.jpg").write_bytes(b"x")
    with pytest.raises(CatalogError):
        FormCatalog.load(tmp_path)


def test_a_missing_folder_is_refused(tmp_path):
    with pytest.raises(CatalogError):
        FormCatalog.load(tmp_path / "nowhere")


def test_invalid_json_is_refused(tmp_path):
    (tmp_path / "forms.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(CatalogError):
        FormCatalog.load(tmp_path)


@pytest.mark.parametrize("content", [["a list"], {"base": ""}, {"base": 5}])
def test_descriptions_must_be_a_map_of_non_empty_text(tmp_path, content):
    (tmp_path / "forms.json").write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(CatalogError):
        FormCatalog.load(tmp_path)


def test_a_picture_without_a_description_is_refused_to_catch_typos(tmp_path):
    folder = make_folder(tmp_path, {"base": "a human"}, ["base.jpg", "gravity_upp.jpg"])
    with pytest.raises(CatalogError):
        FormCatalog.load(folder)


def test_the_base_picture_is_required(tmp_path):
    folder = make_folder(tmp_path, {"base": "a human", "gravity_up": "squat"}, ["gravity_up.jpg"])
    with pytest.raises(CatalogError):
        FormCatalog.load(folder)


def test_the_founder_gets_the_base_form(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg"]))
    form = catalog.resolve(DEFAULT_SPECIES.founder())
    assert (form.key, form.image) == ("base", "base.jpg")
    assert form.description == "description of base"


def test_the_most_specific_available_picture_wins(tmp_path):
    names = ["base.jpg", "gravity_up.jpg", "temperature_down.jpg", "gravity_up__temperature_down.jpg"]
    catalog = FormCatalog.load(full_folder(tmp_path, names))
    assert catalog.resolve(creature(gravity=1.6, temperature=7.0)).key == "gravity_up__temperature_down"


def test_without_the_pair_the_strongest_single_wins(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg", "gravity_up.jpg", "temperature_down.jpg"]))
    assert catalog.resolve(creature(gravity=1.6, temperature=7.0)).key == "temperature_down"


def test_without_any_matching_picture_the_base_is_used(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg"]))
    assert catalog.resolve(creature(gravity=1.6, temperature=7.0)).key == "base"


def test_the_latest_event_decides_between_singles_when_the_pair_is_missing(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg", "gravity_up.jpg", "temperature_down.jpg"]))
    recent = creature(gravity=1.6, temperature=-1.0, changed=("gravity",))
    older = creature(gravity=1.6, temperature=-1.0)
    assert catalog.resolve(recent).key == "gravity_up"
    assert catalog.resolve(older).key == "temperature_down"


def test_the_pair_picture_still_wins_when_it_exists(tmp_path):
    names = ["base.jpg", "gravity_up.jpg", "temperature_down.jpg", "gravity_up__temperature_down.jpg"]
    catalog = FormCatalog.load(full_folder(tmp_path, names))
    recent = creature(gravity=1.6, temperature=-1.0, changed=("gravity",))
    assert catalog.resolve(recent).key == "gravity_up__temperature_down"


def test_an_extinct_creature_gets_the_extinct_picture(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg", "extinct.jpg"]))
    dead = creature(gravity=1.6).model_copy(update={"status": Status.EXTINCT})
    assert catalog.resolve(dead).key == "extinct"


def test_an_extinct_creature_falls_back_to_the_base_picture(tmp_path):
    catalog = FormCatalog.load(full_folder(tmp_path, ["base.jpg"]))
    dead = creature(gravity=1.6).model_copy(update={"status": Status.EXTINCT})
    assert catalog.resolve(dead).key == "base"


def test_descriptions_without_pictures_are_allowed_and_reported(tmp_path):
    folder = make_folder(tmp_path, {"base": "a human", "water_up": "aquatic"}, ["base.jpg"])
    catalog = FormCatalog.load(folder)
    assert catalog.find("water_up") is None
    assert catalog.missing_pictures() == ["water_up"]


def test_when_one_key_has_several_files_the_preferred_extension_wins(tmp_path):
    folder = make_folder(tmp_path, {"base": "a human"}, ["base.png", "base.jpg"])
    assert FormCatalog.load(folder).find("base").image == "base.jpg"


def test_the_shipped_catalog_loads_and_every_picture_is_described():
    catalog = FormCatalog.load(SHIPPED)
    assert catalog.find("base") is not None


@pytest.mark.parametrize("event_id", list(EVENTS))
def test_every_preset_event_leads_to_a_picture_in_the_shipped_catalog(event_id):
    catalog = FormCatalog.load(SHIPPED)
    child = evolve(DEFAULT_SPECIES.founder(), EVENTS[event_id], random.Random(0))
    assert catalog.resolve(child).image