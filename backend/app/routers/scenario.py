from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..scenarios import apply_scenario, load_scenario
from ..seed import seed

router = APIRouter(prefix="/api")


@router.post("/scenario/{name}")
def load(name: str, session: Session = Depends(get_session)):
    if name == "reset":
        seed(session)
        return {"loaded": "reset"}
    sc = load_scenario(name)
    if sc is None:
        raise HTTPException(404, "Unknown scenario")
    return apply_scenario(session, sc)
