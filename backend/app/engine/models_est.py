"""Model estimates (MODEL-ESTIMATED provenance): bone loss and radiation dose. Pure functions."""
from __future__ import annotations

from typing import Sequence

from .baseline import trailing_count
from .rules import AMBER, GREEN, RED, UNKNOWN, MetricResult, assess_domain, v

DAYS_PER_MONTH = 30.44  # calendar constant, not a physiological value

BONE_FORMULA = ("estimated loss % = loss_rate (%/month) × (mission_day / 30.44) "
                "× (1 − exercise_effectiveness × adherence)")
RADIATION_FORMULA = "cumulative dose = mission_day × daily_dose (mission profile) + Σ solar event doses"


def exercise_adherence(minutes: Sequence[float | None], target: float) -> float | None:
    """Mean of min(minutes/target, 1) over days with data. None if no data."""
    vals = [min(float(m) / target, 1.0) for m in minutes if m is not None]
    return sum(vals) / len(vals) if vals else None


def estimate_bone_loss_pct(mission_day: int, rate_pct_per_month: float,
                           effectiveness: float, adherence: float) -> float:
    adherence = max(0.0, min(adherence, 1.0))
    return rate_pct_per_month * (mission_day / DAYS_PER_MONTH) * (1 - effectiveness * adherence)


def assess_bone(thresholds: dict, exercise_minutes: Sequence[float | None], mission_day: int,
                persistence: int, text: dict | None = None):
    b = thresholds["bone"]
    target = v(b["exercise_target_min"])
    amber_below, red_below = v(b["adherence_amber_below"]), v(b["adherence_red_below"])
    adherence = exercise_adherence(exercise_minutes, target)
    if adherence is None or not exercise_minutes or exercise_minutes[-1] is None:
        r = MetricResult(metric="exercise_minutes", status=UNKNOWN, reason="No exercise logged today.",
                         rule="", label="Exercise adherence", domain="bone", provenance="SELF-REPORTED")
        return assess_domain("bone", [r], text)

    daily = [None if m is None else min(m / target, 1.0) for m in exercise_minutes]
    low_streak = trailing_count([d is not None and d < amber_below for d in daily])
    very_low_streak = trailing_count([d is not None and d < red_below for d in daily])
    today_min = float(exercise_minutes[-1])
    adh_rule = (f"AMBER if below {amber_below:.0%} of the {target:g} min/day target for >= {persistence} days; "
                f"RED if below {red_below:.0%} for >= {persistence} days.")
    if very_low_streak >= persistence:
        s, why = RED, f"Exercise below {red_below:.0%} of target for {very_low_streak} days in a row."
    elif low_streak >= persistence:
        s, why = AMBER, f"Exercise below {amber_below:.0%} of target for {low_streak} days in a row."
    else:
        s, why = GREEN, f"Today {today_min:.0f} of {target:g} min target."
    adh = MetricResult(metric="exercise_minutes", status=s, reason=why, rule=adh_rule,
                       label="Exercise adherence", domain="bone", unit="min", provenance="SELF-REPORTED",
                       value=today_min, days_persisting=low_streak, persistence_needed=persistence,
                       watch=(s == GREEN and low_streak > 0), history=list(exercise_minutes),
                       extra={"adherence_recent": round(adherence, 2), "target_min": target})

    rate, eff = v(b["loss_rate_pct_per_month"]), v(b["exercise_effectiveness"])
    loss = estimate_bone_loss_pct(mission_day, rate, eff, adherence)
    la, lr = v(b["loss_amber_pct"]), v(b["loss_red_pct"])
    ls = RED if loss >= lr else AMBER if loss >= la else GREEN
    est = MetricResult(metric="bone_loss_est", status=ls,
                       reason=f"Estimated {loss:.1f} % loss at mission day {mission_day} with {adherence:.0%} recent exercise adherence.",
                       rule=f"AMBER at >= {la:g} %, RED at >= {lr:g} % estimated loss.",
                       label="Estimated bone loss (weight-bearing sites)", domain="bone", unit="%",
                       provenance="MODEL-ESTIMATED", value=round(loss, 2),
                       extra={"formula": BONE_FORMULA, "inputs": {"loss_rate_pct_per_month": rate,
                              "exercise_effectiveness": eff, "adherence": round(adherence, 2),
                              "mission_day": mission_day}})
    return assess_domain("bone", [est, adh], text)


def cumulative_dose_msv(mission_day: int, daily_dose_msv: float, event_doses: Sequence[float] = ()) -> float:
    return mission_day * daily_dose_msv + sum(event_doses)


def assess_radiation(thresholds: dict, mission_day: int, daily_dose_msv: float,
                     event_doses: Sequence[float] = (), spe_active: bool = False, text: dict | None = None):
    r = thresholds["radiation"]
    limit, af, rf = v(r["career_limit_msv"]), v(r["amber_fraction"]), v(r["red_fraction"])
    dose = cumulative_dose_msv(mission_day, daily_dose_msv, event_doses)
    frac = dose / limit
    days_to_limit = max(0.0, (limit - dose) / daily_dose_msv) if daily_dose_msv > 0 else None
    if frac >= rf:
        s, why = RED, f"{dose:.0f} mSv = {frac:.0%} of the {limit:g} mSv career limit."
    elif frac >= af:
        s, why = AMBER, f"{dose:.0f} mSv = {frac:.0%} of the {limit:g} mSv career limit."
    else:
        s, why = GREEN, f"{dose:.0f} mSv = {frac:.0%} of the {limit:g} mSv career limit."
    dose_res = MetricResult(metric="cumulative_dose", status=s, reason=why,
                            rule=f"AMBER at >= {af:.0%} of limit, RED at >= {rf:.0%} of limit.",
                            label="Cumulative dose", domain="radiation", unit="mSv",
                            provenance="MODEL-ESTIMATED", value=round(dose, 1),
                            extra={"formula": RADIATION_FORMULA, "limit_msv": limit, "fraction": round(frac, 3),
                                   "daily_dose_msv": daily_dose_msv,
                                   "days_to_limit": None if days_to_limit is None else round(days_to_limit)})
    spe = MetricResult(metric="spe_active", status=RED if spe_active else GREEN,
                       reason="Solar particle event in progress - shelter now." if spe_active else "No active solar particle event.",
                       rule="RED immediately while a solar particle event is active.",
                       label="Solar particle event", domain="radiation", provenance="MEASURED",
                       value=1.0 if spe_active else 0.0)
    return assess_domain("radiation", [dose_res, spe], text)
