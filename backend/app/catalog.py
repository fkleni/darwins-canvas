"""The library of hand-made pictures, and what each one shows."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.sim.models import Creature, Status
from app.sim.profile import BASE_KEY, form_keys

EXTINCT_KEY = "extinct"
DESCRIPTIONS_FILE = "forms.json"
PICTURE_EXTENSIONS = (".webp", ".jpg", ".jpeg", ".png")  # earlier in the list wins


class CatalogError(Exception):
    """The folder of pictures is incomplete or inconsistent."""


class Form(BaseModel):
    """One picture of the library and the facts about what it shows."""

    model_config = ConfigDict(frozen=True)

    key: str
    description: str  # what the picture shows: the narrator is told this is the truth
    image: str  # file name inside the pictures folder


def _find_pictures(directory: Path) -> dict[str, str]:
    """Map each picture's key (its file name without extension) to its file name."""
    best: dict[str, tuple[int, str]] = {}
    for path in sorted(directory.iterdir()):
        suffix = path.suffix.lower()
        if suffix not in PICTURE_EXTENSIONS:
            continue
        rank = PICTURE_EXTENSIONS.index(suffix)
        current = best.get(path.stem)
        if current is None or rank < current[0]:
            best[path.stem] = (rank, path.name)
    return {stem: name for stem, (_, name) in best.items()}


class FormCatalog:
    """Finds the picture that fits a creature, falling back to simpler ones."""

    def __init__(self, directory: Path, descriptions: dict[str, str], pictures: dict[str, str]):
        self._directory = directory
        self._descriptions = descriptions
        self._pictures = pictures

    @classmethod
    def load(cls, directory: Path) -> "FormCatalog":
        """Read the folder. Fails early and loudly if anything is inconsistent."""
        directory = Path(directory)
        path = directory / DESCRIPTIONS_FILE
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CatalogError(f"{path} not found") from error
        except json.JSONDecodeError as error:
            raise CatalogError(f"{path} is not valid JSON: {error}") from error
        if not isinstance(raw, dict) or not all(
            isinstance(key, str) and isinstance(text, str) and text.strip()
            for key, text in raw.items()
        ):
            raise CatalogError(f"{DESCRIPTIONS_FILE} must map each key to a non-empty description")
        descriptions = {key: text.strip() for key, text in raw.items()}

        pictures = _find_pictures(directory)
        undescribed = sorted(set(pictures) - set(descriptions))
        if undescribed:
            raise CatalogError(f"pictures without a description in {DESCRIPTIONS_FILE}: {undescribed}")
        if BASE_KEY not in pictures:
            raise CatalogError(f"the base form needs a picture ({BASE_KEY}.jpg or similar)")
        return cls(directory, descriptions, pictures)

    @property
    def directory(self) -> Path:
        return self._directory

    def find(self, key: str) -> Form | None:
        """The form for this exact key, or None when there is no picture for it."""
        picture = self._pictures.get(key)
        if picture is None:
            return None
        return Form(key=key, description=self._descriptions[key], image=picture)

    def resolve(self, creature: Creature) -> Form:
        """The best available picture for a creature, favouring what its latest event changed."""
        if creature.status == Status.EXTINCT:
            keys = [EXTINCT_KEY, BASE_KEY]
        else:
            keys = form_keys(creature.adapted_to, creature.changed)
        for key in keys:
            form = self.find(key)
            if form is not None:
                return form
        raise CatalogError("no picture found, not even the base form")

    def missing_pictures(self) -> list[str]:
        """Keys that have a description but no picture yet."""
        return sorted(set(self._descriptions) - set(self._pictures))