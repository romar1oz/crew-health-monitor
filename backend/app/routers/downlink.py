from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..config import load_thresholds
from ..db import get_session
from ..models import CrewMember, DownlinkItem
from ..services.downlink import build_summary, delay_info, queue_summary, serialize
from ..services_assessment import mission_state

router = APIRouter(prefix="/api")
DOMAINS = {"cardiovascular", "bone", "immune", "behavioral", "radiation"}


class DownlinkIn(BaseModel):
    crew_id: str
    domains: list[str] = Field(default_factory=list)   # nothing is included unless ticked
    include_metrics: bool = False
    include_actions: bool = False
    note: str = Field(default="", max_length=500)


def _summary(body: DownlinkIn, session: Session) -> dict:
    if session.get(CrewMember, body.crew_id) is None:
        raise HTTPException(404, "Unknown crew member")
    if not set(body.domains) <= DOMAINS:
        raise HTTPException(422, "Unknown domain")
    return build_summary(session, body.crew_id, body.domains, body.include_metrics, body.include_actions, body.note)


@router.post("/downlink/preview")
def preview(body: DownlinkIn, session: Session = Depends(get_session)):
    """Exactly what Earth would receive. Nothing is queued."""
    return {"summary": _summary(body, session), "meta": delay_info(mission_state(session).profile)}


@router.post("/downlink")
def enqueue(body: DownlinkIn, session: Session = Depends(get_session)):
    if not body.domains and not body.note.strip() and not body.include_actions:
        raise HTTPException(422, "Select at least one item to send")
    return serialize(queue_summary(session, body.crew_id, _summary(body, session)))


@router.get("/downlink")
def list_queue(session: Session = Depends(get_session)):
    items = session.exec(select(DownlinkItem).order_by(DownlinkItem.id.desc())).all()
    profile = mission_state(session).profile
    return {"profile": profile, "profile_label": load_thresholds()["missions"][profile]["label"], **delay_info(profile),
            "items": [serialize(i) for i in items]}


@router.delete("/downlink/{item_id}")
def cancel(item_id: int, session: Session = Depends(get_session)):
    """The crew controls their data: a queued item can be withdrawn before it is delivered."""
    item = session.get(DownlinkItem, item_id)
    if item is None:
        raise HTTPException(404, "Not found")
    if serialize(item)["status"] == "delivered":
        raise HTTPException(409, "Already delivered")
    session.delete(item)
    session.commit()
    return {"cancelled": item_id}
