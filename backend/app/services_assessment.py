"""Glue between the database and the pure rules engine."""
from __future__ import annotations

from sqlmodel import Session, select

from .config import load_domain_text, load_thresholds
from .engine.rules import assess_crew
from .models import Baseline, MissionState, Observation, RadiationEvent

WINDOW_DAYS = 14


def mission_state(session: Session) -> MissionState:
    return session.get(MissionState, 1) or MissionState()


def build_series(session: Session, crew_id: str, today: int) -> dict[str, list[float | None]]:
    """Per metric: list of values for the last WINDOW_DAYS mission days (None = missing)."""
    days = list(range(today - WINDOW_DAYS + 1, today + 1))
    rows = session.exec(select(Observation).where(Observation.crew_id == crew_id,
                                                  Observation.mission_day >= days[0],
                                                  Observation.mission_day <= today)).all()
    grid: dict[str, dict[int, float]] = {}
    for r in rows:
        grid.setdefault(r.metric, {})[r.mission_day] = r.value  # later rows overwrite (check-in wins)
    return {m: [vals.get(d) for d in days] for m, vals in grid.items()}


def assess(session: Session, crew_id: str) -> dict:
    st = mission_state(session)
    baselines = {b.metric: (b.mean, b.sd) for b in
                 session.exec(select(Baseline).where(Baseline.crew_id == crew_id)).all()}
    events = session.exec(select(RadiationEvent)).all()
    domains = assess_crew(load_thresholds(), load_domain_text(), baselines,
                          build_series(session, crew_id, st.mission_day),
                          mission_day=st.mission_day, mission_profile=st.profile,
                          radiation_event_doses=[e.dose_msv for e in events], spe_active=st.spe_active)
    return {"crew_id": crew_id, "mission_day": st.mission_day, "mission_profile": st.profile,
            "simulated_data": True, "domains": domains}
