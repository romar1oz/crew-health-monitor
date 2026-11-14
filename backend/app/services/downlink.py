"""Builds the privacy-controlled summary and queues it behind the simulated comms delay."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from ..config import load_thresholds
from ..engine.rules import v
from ..models import ActionLog, CrewMember, DownlinkItem
from ..services_assessment import assess, mission_state


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite may hand back naive UTC


def build_summary(session: Session, crew_id: str, domains: list[str], include_metrics: bool,
                  include_actions: bool, note: str) -> dict:
    """Only what the astronaut ticked is included. Default = domain statuses only."""
    a = assess(session, crew_id)
    out_domains = []
    for d in a["domains"]:
        if d["domain"] not in domains:
            continue
        item = {"domain": d["domain"], "title": d["title"], "status": d["status"]}
        if include_metrics:
            item["details"] = [{"label": t["label"], "value": t["value"], "unit": t["unit"],
                               "provenance": t["provenance"], "reason": t["reason"]} for t in d["triggers"]]
        out_domains.append(item)
    summary = {"crew_id": crew_id, "crew_name": session.get(CrewMember, crew_id).name,
               "mission_day": a["mission_day"], "mission_profile": a["mission_profile"],
               "simulated_data": True, "domains": out_domains}
    if include_actions:
        rows = session.exec(select(ActionLog).where(ActionLog.crew_id == crew_id)).all()
        summary["actions_completed"] = [{"protocol_id": r.protocol_id, "step_id": r.step_id,
                                         "done_at": r.done_at.isoformat(timespec="seconds")} for r in rows]
    if note.strip():
        summary["crew_note"] = note.strip()
    return summary


def delay_info(profile: str) -> dict:
    th = load_thresholds()
    real = v(th["missions"][profile]["one_way_delay_s"])
    accel = v(th["demo"]["time_acceleration"])
    return {"real_one_way_delay_s": real, "demo_acceleration": accel, "demo_delay_s": real / accel}


def queue_summary(session: Session, crew_id: str, summary: dict) -> DownlinkItem:
    st = mission_state(session)
    info = delay_info(st.profile)
    now = utcnow()
    item = DownlinkItem(crew_id=crew_id, created_at=now, deliver_at=now + timedelta(seconds=info["demo_delay_s"]),
                        payload_json=json.dumps({"meta": {"profile": st.profile, **info}, "summary": summary}))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def serialize(item: DownlinkItem) -> dict:
    now = utcnow()
    remaining = max(0.0, (_aware(item.deliver_at) - now).total_seconds())
    return {"id": item.id, "crew_id": item.crew_id, "created_at": _aware(item.created_at).isoformat(),
            "deliver_at": _aware(item.deliver_at).isoformat(), "seconds_remaining": round(remaining, 1),
            "status": "delivered" if remaining <= 0 else "queued", **json.loads(item.payload_json)}
