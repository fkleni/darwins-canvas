import httpx
from urllib.parse import quote

# Anything starting with "scratch_" is ignored by git (see .gitignore).
OUTPUT = "scratch_output.jpg"

prompt = "concept art of a six-legged giraffe-like herbivore, dense armored hide, alien high-gravity planet, detailed, dark background"
url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=512&height=512&seed=42"

response = httpx.get(url, timeout=120, follow_redirects=True)
print("Status code:", response.status_code)
print("Type:", response.headers.get("content-type"))

if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
    with open(OUTPUT, "wb") as f:
        f.write(response.content)
    print("Saved:", OUTPUT)
else:
    print(response.text[:500])