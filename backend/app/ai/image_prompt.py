"""Turns what we know about a creature into a prompt for the image model."""

import hashlib
import re

from pydantic import BaseModel, ConfigDict

from app.ai.schemas import Narration
from app.sim.appearance import Appearance
from app.sim.models import Creature, Status
from app.sim.species import Species

IMAGE_SIZE = 768
MAX_SEED = 2_147_483_647  # the biggest seed every image service accepts

STYLE = (
    "family-friendly naturalist field-guide illustration of a single creature, "
    "ink and watercolor plate, full body, centered, plain dark neutral background, "
    "soft studio lighting"
)
COVERING = "body covered in thick textured hide"
STRICT_COVERING = "body fully covered by thick hide and a long loose cloak"
FOSSIL_STYLE = (
    "naturalist field-guide illustration of a single fossil skeleton specimen, "
    "bleached bones, centered, museum plate, plain dark neutral background, "
    "soft studio lighting"
)

_COUNT = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twin|dual|double|triple|single)"
_PART = r"(?:limbs?|legs?|arms?|eyes?|fingers?|toes?|digits?|heads?|tails?|wings?|horns?|tentacles?|ears?|antennae|claws?)"
_COUNTED_PART = re.compile(rf"\b{_COUNT}\s+((?:[\w'-]+\s+){{0,2}}?{_PART})\b", re.IGNORECASE)
_COUNTED_ADJECTIVE = re.compile(
    rf"\b{_COUNT}-(?:legged|limbed|armed|eyed|fingered|toed|headed|tailed|winged|horned|tentacled)\b",
    re.IGNORECASE,
)

_EYE_SIZE = {"tiny": "tiny ", "small": "small ", "medium": "", "large": "large ", "huge": "huge "}
_PATTERN = {
    "none": "no markings",
    "freckled": "freckled markings",
    "spotted": "spotted markings",
    "mottled": "mottled markings",
    "striped": "striped markings",
}


class ImageRequest(BaseModel):
    """Everything the image client needs to ask for one picture."""

    model_config = ConfigDict(frozen=True)

    prompt: str
    seed: int
    width: int = IMAGE_SIZE
    height: int = IMAGE_SIZE


def scrub_counts(text: str) -> str:
    """Remove 'six legs'-style counts: image models cannot count, so we never ask them to."""
    text = _COUNTED_PART.sub(r"\1", text)
    text = _COUNTED_ADJECTIVE.sub("", text)
    return " ".join(text.split())


def appearance_phrase(appearance: Appearance) -> str:
    """The cosmetic look, in plain words an image model understands."""
    skin = appearance.skin_color.replace("_", " ")
    eyes = f"{_EYE_SIZE[appearance.eye_size]}{appearance.eye_color} eyes"
    return f"{skin} skin, {eyes}, {_PATTERN[appearance.pattern]}"


def lineage_seed(lineage_id: str) -> int:
    """A stable number for a lineage: every creature of one lineage shares it.

    hashlib, not hash(): Python's built-in hash() of a string changes on every run.
    """
    digest = hashlib.sha256(lineage_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % MAX_SEED


def build_image_request(
    narration: Narration, creature: Creature, origin: str, seed: int
) -> ImageRequest:
    """The picture request for an evolved creature."""
    if creature.status == Status.EXTINCT:
        style, extras = FOSSIL_STYLE, []  # bones have no skin colour and need no covering
    else:
        style, extras = STYLE, [appearance_phrase(creature.appearance), COVERING]
    subject = f"a speculative creature evolved from {origin.lower()} ancestors"
    notes = scrub_counts(narration.visual_notes).rstrip(" .")
    return ImageRequest(prompt=", ".join([style, subject, *extras, notes]), seed=seed)


def build_founder_image_request(species: Species, seed: int) -> ImageRequest:
    """The picture request for the root of a lineage: the base species itself."""
    if not species.visual_description:
        raise ValueError(f"{species.name} has no visual_description")
    parts = [STYLE, species.visual_description, appearance_phrase(species.appearance)]
    return ImageRequest(prompt=", ".join(parts), seed=seed)


def retry_request(request: ImageRequest, attempt: int) -> ImageRequest:
    """The request for another try after a rejected picture: a new seed, a stricter covering."""
    return request.model_copy(
        update={
            "seed": (request.seed + attempt) % MAX_SEED,
            "prompt": f"{request.prompt}, {STRICT_COVERING}",
        }
    )