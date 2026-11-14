"""CrewCheck FastAPI entry point. Serves the API under /api and the static frontend at /."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="CrewCheck", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "CrewCheck"}


# Mounted last so /api routes take priority. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
