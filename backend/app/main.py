"""CrewCheck FastAPI entry point. Serves the API under /api and the static frontend at /."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from .config import load_thresholds
from .db import get_engine, init_db
from .routers import core
from .seed import seed_if_empty

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_thresholds()  # fail fast if the honesty rules are violated
    init_db()
    with Session(get_engine()) as s:
        seed_if_empty(s)
    yield


app = FastAPI(title="CrewCheck", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "CrewCheck"}


app.include_router(core.router)

# Mounted last so /api routes take priority. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
