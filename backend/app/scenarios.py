"""Demo scenarios: reset to the deterministic seed, then apply documented deviations.
Deviations are expressed in SD from each crew member's OWN baseline and clamped to the
sim_min/sim_max ranges in thresholds.yaml, so the story never invents out-of-range numbers."""
from __future__ import annotations

import json
import re

from sqlmodel import Session, delete, select

from .config import BACKEND_DIR, load_thresholds
from .engine.rules import v
from .models import Baseline, Observation
from .seed import seed

SCENARIO_DIR = BACKEND_DIR / "scenarios"


def load_scenario(name: str) -> dict | None:
    if not re.fullmatch(r"[a-z0-9_]+", name):
        return None
    p = SCENARIO_DIR / f"{name}.json"
    if not p.exists() or name == "sample_donki":
        return None
    return json.loads(p.read_text())


def apply_scenario(session: Session, sc: dict) -> dict:
    seed(session, mission_day=sc["mission_day"], profile=sc["profile"])
    th = load_thresholds()["metrics"]
    applied = []
    for d in sc.get("deviations", []):
        m, cfg = d["metric"], th[d["metric"]]
        b = session.exec(select(Baseline).where(Baseline.crew_id == sc["crew_id"], Baseline.metric == m)).one()
        value = min(max(b.mean + d["z"] * b.sd, v(cfg["sim_min"])), v(cfg["sim_max"]))
        value = round(value) if cfg["sim_mean"]["unit"] == "count" else round(value, 1)
        for back in d["days_before_today"]:
            day = sc["mission_day"] - back
            session.exec(delete(Observation).where(Observation.crew_id == sc["crew_id"],
                                                   Observation.mission_day == day, Observation.metric == m))
            session.add(Observation(crew_id=sc["crew_id"], mission_day=day, metric=m, value=value,
                                    provenance=cfg["provenance"], source="scenario"))
        applied.append({"metric": m, "value": value, "z": d["z"], "days": d["days_before_today"]})
    session.commit()
    return {"loaded": sc["name"], "title": sc["title"], "crew_id": sc["crew_id"], "applied": applied}
