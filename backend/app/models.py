"""Database tables (SQLModel + SQLite)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class CrewMember(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    role: str


class Baseline(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    crew_id: str = Field(index=True, foreign_key="crewmember.id")
    metric: str
    mean: float
    sd: float
    n: int


class Observation(SQLModel, table=True):
    """One value of one metric on one mission day (long format)."""
    id: int | None = Field(default=None, primary_key=True)
    crew_id: str = Field(index=True, foreign_key="crewmember.id")
    mission_day: int = Field(index=True)  # negative = pre-flight
    metric: str = Field(index=True)
    value: float
    provenance: str          # MEASURED | SELF-REPORTED | LAB-ENTERED | MODEL-ESTIMATED
    source: str = "seed"     # seed | checkin | lab | scenario


class CheckIn(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    crew_id: str = Field(index=True, foreign_key="crewmember.id")
    mission_day: int
    created_at: datetime = Field(default_factory=now)
    payload_json: str


class ActionLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    crew_id: str = Field(index=True, foreign_key="crewmember.id")
    protocol_id: str
    step_id: str
    done_at: datetime = Field(default_factory=now)


class RadiationEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mission_day: int
    dose_msv: float
    kind: str               # e.g. SEP
    note: str = ""


class DownlinkItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    crew_id: str = Field(index=True, foreign_key="crewmember.id")
    created_at: datetime = Field(default_factory=now)
    deliver_at: datetime
    payload_json: str
    status: str = "queued"  # queued | delivered


class MissionState(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    profile: str = "mars_transit"
    mission_day: int = 120
    spe_active: bool = False
