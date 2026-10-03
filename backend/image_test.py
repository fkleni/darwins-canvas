import httpx
from urllib.parse import quote

prompt = "concept art of a six-legged giraffe-like herbivore, dense armored hide, alien high-gravity planet, detailed, dark background"
url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=512&height=512&seed=42"

response = httpx.get(url, timeout=120, follow_redirects=True)
print("Durum kodu:", response.status_code)
print("Tür:", response.headers.get("content-type"))

if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
    with open("test_creature.jpg", "wb") as f:
        f.write(response.content)
    print("Kaydedildi: test_creature.jpg")
else:
    print(response.text[:500])