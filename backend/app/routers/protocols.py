from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..engine.protocols import load_protocol
from ..models import ActionLog, CrewMember

router = APIRouter(prefix="/api")


class ActionIn(BaseModel):
    crew_id: str
    protocol_id: str
    step_id: str


@router.get("/protocols/{protocol_id}")
def get_protocol(protocol_id: str):
    p = load_protocol(protocol_id)
    if p is None:
        raise HTTPException(404, "Unknown protocol")
    return p


@router.post("/actions")
def log_action(body: ActionIn, session: Session = Depends(get_session)):
    p = load_protocol(body.protocol_id)
    if p is None or body.step_id not in p["nodes"] or session.get(CrewMember, body.crew_id) is None:
        raise HTTPException(404, "Unknown crew member, protocol or step")
    existing = session.exec(select(ActionLog).where(ActionLog.crew_id == body.crew_id,
                                                    ActionLog.protocol_id == body.protocol_id,
                                                    ActionLog.step_id == body.step_id)).first()
    if existing is None:
        existing = ActionLog(**body.model_dump())
        session.add(existing)
        session.commit()
        session.refresh(existing)
    return {"id": existing.id, "done_at": existing.done_at.isoformat(timespec="seconds"), **body.model_dump()}


@router.get("/actions/{crew_id}")
def list_actions(crew_id: str, session: Session = Depends(get_session)):
    rows = session.exec(select(ActionLog).where(ActionLog.crew_id == crew_id).order_by(ActionLog.id)).all()
    return [{"protocol_id": r.protocol_id, "step_id": r.step_id, "done_at": r.done_at.isoformat(timespec="seconds")} for r in rows]
