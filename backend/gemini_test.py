import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()
MODEL = "gemini-3.5-flash-lite"


class Creature(BaseModel):
    name: str
    description: str
    traits: list[str]


client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model=MODEL,
    contents="Invent a fictional giraffe-like creature living on a high-gravity planet.",
    config={
        "response_mime_type": "application/json",
        "response_schema": Creature,
    },
)

print(response.text)
print()
print(response.parsed)