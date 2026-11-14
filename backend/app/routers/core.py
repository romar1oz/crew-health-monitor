from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..config import load_thresholds
from ..db import get_session
from ..models import Baseline, CrewMember
from ..services_assessment import assess, mission_state

router = APIRouter(prefix="/api")


@router.get("/crew")
def list_crew(session: Session = Depends(get_session)):
    th = load_thresholds()["metrics"]
    out = []
    for c in session.exec(select(CrewMember)).all():
        bl = session.exec(select(Baseline).where(Baseline.crew_id == c.id)).all()
        out.append({"id": c.id, "name": c.name, "role": c.role,
                    "baselines": [{"metric": b.metric, "label": th[b.metric]["label"],
                                   "unit": th[b.metric]["sim_mean"]["unit"],
                                   "mean": b.mean, "sd": b.sd, "n": b.n} for b in bl]})
    return out


@router.get("/assessment/{crew_id}")
def get_assessment(crew_id: str, session: Session = Depends(get_session)):
    if session.get(CrewMember, crew_id) is None:
        raise HTTPException(404, "Unknown crew member")
    return assess(session, crew_id)


@router.get("/mission")
def get_mission(session: Session = Depends(get_session)):
    return mission_state(session)


@router.get("/thresholds")
def get_thresholds():
    """Full thresholds config incl. status/sources - used by the UI 'Why?' panels."""
    return load_thresholds()
