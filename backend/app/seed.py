"""Seeds SIMULATED crew data. Every number is drawn from ranges in thresholds.yaml.
Deterministic (fixed random seed) so the demo looks the same every time."""
from __future__ import annotations

import random

from sqlmodel import Session, delete, select

from .config import load_thresholds
from .engine.baseline import compute_baseline
from .engine.rules import v
from .models import (ActionLog, Baseline, CheckIn, CrewMember, DownlinkItem, MissionState, Observation,
                     RadiationEvent)

# Fictional crew - not real people.
CREW = [
    ("c1", "Cmdr. Ada Okafor", "Commander"),
    ("c2", "Dr. Lin Moreau", "Flight Engineer / Medical Officer"),
    ("c3", "Sami Varga", "Mission Specialist"),
]
HISTORY_DAYS = 14   # mission days of history ending today
SPARSE_PREFLIGHT_DRAWS = 4  # pre-flight lab draws for sparse metrics (ASSUMPTION, simulation only)


def _draw(rng: random.Random, mean: float, sd: float, lo: float, hi: float, integer: bool) -> float:
    x = min(max(rng.gauss(mean, sd), lo), hi)
    return float(round(x)) if integer else round(x, 1)


def personal_params(rng: random.Random, cfg: dict) -> tuple[float, float]:
    """Each crew member gets their own normal: population mean shifted by up to ~1 SD."""
    mean, sd = v(cfg["sim_mean"]), v(cfg["sim_sd"])
    return mean + rng.uniform(-1, 1) * sd, sd


def seed(session: Session, mission_day: int = 120, profile: str = "mars_transit", rnd_seed: int = 42) -> None:
    th = load_thresholds()
    rng = random.Random(rnd_seed)
    for tbl in (ActionLog, CheckIn, DownlinkItem, RadiationEvent, Observation, Baseline, CrewMember, MissionState):
        session.exec(delete(tbl))
    session.add(MissionState(id=1, profile=profile, mission_day=mission_day))
    baseline_days = int(v(th["global"]["baseline_days"]))

    for cid, name, role in CREW:
        session.add(CrewMember(id=cid, name=name, role=role))
        for metric, cfg in th["metrics"].items():
            mean, sd = personal_params(rng, cfg)
            lo, hi = v(cfg["sim_min"]), v(cfg["sim_max"])
            integer = cfg["sim_mean"]["unit"] == "count"
            sparse = cfg.get("sparse", False)

            # Pre-flight baseline period (negative mission days)
            n_pre = SPARSE_PREFLIGHT_DRAWS if sparse else baseline_days
            pre = [_draw(rng, mean, sd, lo, hi, integer) for _ in range(n_pre)]
            if cfg.get("assess") != "adherence":
                b = compute_baseline(pre, min_sd=v(cfg["min_sd"]))
                session.add(Baseline(crew_id=cid, metric=metric, mean=round(b.mean, 2), sd=round(b.sd, 2), n=b.n))

            # In-flight history, ending today
            interval = int(v(cfg["lab_interval_days"])) if sparse else 1
            for day in range(mission_day - HISTORY_DAYS + 1, mission_day + 1):
                if sparse and (mission_day - day) % interval != 0:
                    continue
                session.add(Observation(crew_id=cid, mission_day=day, metric=metric,
                                        value=_draw(rng, mean, sd, lo, hi, integer),
                                        provenance=cfg["provenance"]))
    session.commit()


def seed_if_empty(session: Session) -> None:
    if session.exec(select(CrewMember)).first() is None:
        seed(session)
