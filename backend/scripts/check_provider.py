"""Manual check: asks the real Gemini API. Needs GEMINI_API_KEY in backend/.env.

Run from the backend folder:  python -m scripts.check_provider
"""

from dotenv import load_dotenv

load_dotenv()

from app.ai.gemini import GeminiProvider  # noqa: E402
from app.ai.provider import LLMError  # noqa: E402
from app.ai.schemas import EventTranslation, Narration  # noqa: E402

provider = GeminiProvider()


def show(title, prompt, schema):
    print(f"--- {title} ---")
    try:
        print(provider.generate(prompt, schema).model_dump_json(indent=2))
    except LLMError as error:
        print(f"{type(error).__name__}: {error}")


show(
    "Narration",
    "Invent a speculative descendant of humans that evolved on a planet whose "
    "gravity doubled. Be vivid but physically plausible.",
    Narration,
)
show(
    "Valid free-text event",
    "A player typed this event for a planet-evolution game: 'the sun grew much brighter'. "
    "Decide if it is a physical environmental change and translate it into parameter changes.",
    EventTranslation,
)
show(
    "Invalid free-text event",
    "A player typed this event for a planet-evolution game: 'a giant pizza falls from the sky'. "
    "Decide if it is a physical environmental change and translate it into parameter changes.",
    EventTranslation,
)