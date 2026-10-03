from fastapi import FastAPI

app = FastAPI(title="Darwin's Canvas")

@app.get("/health")
def health():
    return {"status": "ok"}