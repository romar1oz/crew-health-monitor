"""Database engine. URL can be overridden with CREWCHECK_DB_URL (tests use a temp file)."""
from __future__ import annotations

import os
from functools import lru_cache

from sqlmodel import Session, SQLModel, create_engine

from .config import BACKEND_DIR


@lru_cache
def get_engine():
    url = os.environ.get("CREWCHECK_DB_URL", f"sqlite:///{BACKEND_DIR / 'crewcheck.db'}")
    return create_engine(url, connect_args={"check_same_thread": False})


def init_db() -> None:
    from . import models  # noqa: F401  (registers tables)
    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as s:
        yield s
