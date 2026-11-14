from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import load_domain_text, load_thresholds
from ..db import get_session
from ..engine.models_est import RADIATION_FORMULA, assess_radiation, cumulative_dose_msv
from ..engine.rules import v
from ..models import CrewMember, RadiationEvent
from ..services.donki import get_space_weather
from ..services_assessment import mission_state

router = APIRouter(prefix="/api")


@router.get("/radiation/{crew_id}")
def radiation(crew_id: str, session: Session = Depends(get_session)):
    if session.get(CrewMember, crew_id) is None:
        raise HTTPException(404, "Unknown crew member")
    st, th = mission_state(session), load_thresholds()
    daily = v(th["missions"][st.profile]["daily_dose_msv"])
    events = session.exec(select(RadiationEvent)).all()
    doses = [e.dose_msv for e in events]
    d = assess_radiation(th, st.mission_day, daily, doses, st.spe_active, load_domain_text().get("radiation")).to_dict()
    r = th["radiation"]
    limit = v(r["career_limit_msv"])
    dose = cumulative_dose_msv(st.mission_day, daily, doses)
    return {"status": d["status"], "protocol_id": d["protocol_id"], "provenance": "MODEL-ESTIMATED",
            "formula": RADIATION_FORMULA, "mission_profile": st.profile, "mission_day": st.mission_day,
            "daily_dose_msv": daily, "cumulative_dose_msv": round(dose, 1), "limit_msv": limit,
            "fraction": round(dose / limit, 3), "amber_at_msv": v(r["amber_fraction"]) * limit,
            "red_at_msv": v(r["red_fraction"]) * limit,
            "days_to_limit": round(max(0.0, (limit - dose) / daily)) if daily > 0 else None,
            "spe_active": st.spe_active, "event_doses_msv": doses,
            "events": [{"mission_day": e.mission_day, "dose_msv": e.dose_msv, "kind": e.kind, "note": e.note} for e in events],
            "simulated_data": True}


class SpeIn(BaseModel):
    active: bool


@router.post("/radiation/spe")
def set_spe(body: SpeIn, session: Session = Depends(get_session)):
    """DEMO CONTROL: simulate a solar particle event starting/ending onboard."""
    st = mission_state(session)
    if body.active and not st.spe_active:
        session.add(RadiationEvent(mission_day=st.mission_day, kind="SEP", note="Simulated SPE (demo control)",
                                   dose_msv=v(load_thresholds()["radiation"]["spe_event_dose_msv"])))
    st.spe_active = body.active
    session.add(st)
    session.commit()
    return {"spe_active": st.spe_active}


@router.get("/space-weather")
def space_weather(refresh: bool = False):
    return get_space_weather(force=refresh)
