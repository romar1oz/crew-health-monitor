"""Check-in submission, symptom list, and the simulated live vitals stream (SSE)."""
from __future__ import annotations

import asyncio
import json
import random

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, delete, select

from ..config import CONTENT_DIR, load_thresholds
from ..db import get_session
from ..engine.rules import v
from ..models import Baseline, CheckIn, CrewMember, Observation
from ..services_assessment import assess, mission_state

router = APIRouter(prefix="/api")


class CheckInIn(BaseModel):
    crew_id: str
    sleep_hours: float = Field(ge=0, le=24)
    sleep_quality: int = Field(ge=1, le=5)
    mood: int = Field(ge=1, le=5)
    fatigue: int = Field(ge=1, le=5)
    symptoms: list[str] = []
    exercise_minutes: float = Field(ge=0, le=600)
    pvt_mean_rt: float | None = Field(default=None, ge=0, le=60000)
    pvt_lapses: int | None = Field(default=None, ge=0, le=1000)
    pvt_false_starts: int | None = Field(default=None, ge=0, le=1000)
    pvt_duration_s: int | None = None


@router.get("/symptoms")
def symptoms():
    return yaml.safe_load((CONTENT_DIR / "symptoms.yaml").read_text())["symptoms"]


@router.post("/checkins")
def submit_checkin(body: CheckInIn, session: Session = Depends(get_session)):
    if session.get(CrewMember, body.crew_id) is None:
        raise HTTPException(404, "Unknown crew member")
    th = load_thresholds()["metrics"]
    day = mission_state(session).mission_day
    values = {
        "sleep_hours": body.sleep_hours, "sleep_quality": body.sleep_quality, "mood": body.mood,
        "fatigue": body.fatigue, "symptom_count": len(body.symptoms),
        "exercise_minutes": body.exercise_minutes,
    }
    if body.pvt_mean_rt is not None:
        values["pvt_mean_rt"] = body.pvt_mean_rt
    if body.pvt_lapses is not None:
        values["pvt_lapses"] = body.pvt_lapses
    for metric, value in values.items():
        # A re-submitted check-in replaces today's value instead of adding a duplicate.
        session.exec(delete(Observation).where(Observation.crew_id == body.crew_id,
                                               Observation.mission_day == day,
                                               Observation.metric == metric))
        session.add(Observation(crew_id=body.crew_id, mission_day=day, metric=metric, value=float(value),
                                provenance=th[metric]["provenance"], source="checkin"))
    session.add(CheckIn(crew_id=body.crew_id, mission_day=day, payload_json=body.model_dump_json()))
    session.commit()
    return assess(session, body.crew_id)


@router.get("/vitals/stream/{crew_id}")
async def vitals_stream(crew_id: str, max_events: int | None = Query(default=None, ge=1, le=10000),
                        interval_s: float = Query(default=1.0, ge=0.05, le=10),
                        session: Session = Depends(get_session)):
    """SIMULATED wearable stream: values drawn around the crew member's own baseline,
    limited to the sim_min/sim_max ranges in thresholds.yaml."""
    if session.get(CrewMember, crew_id) is None:
        raise HTTPException(404, "Unknown crew member")
    th = load_thresholds()["metrics"]
    names = [m for m, c in th.items() if c["provenance"] == "MEASURED" and c["domain"] == "cardiovascular"]
    bl = {b.metric: b for b in session.exec(select(Baseline).where(Baseline.crew_id == crew_id)).all()}
    rng = random.Random()

    async def gen():
        n = 0
        while max_events is None or n < max_events:
            ev = {"simulated": True, "provenance": "MEASURED", "n": n}
            for m in names:
                b = bl[m]
                lo, hi = v(th[m]["sim_min"]), v(th[m]["sim_max"])
                ev[m] = round(min(max(rng.gauss(b.mean, b.sd * 0.6), lo), hi), 1)
            yield f"data: {json.dumps(ev)}\n\n"
            n += 1
            await asyncio.sleep(interval_s)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
