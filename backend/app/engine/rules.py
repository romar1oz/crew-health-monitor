"""Assessment rules: per-metric status and per-domain status. Pure functions.

Rule (all numbers from config/thresholds.yaml):
  RED   if today's value crosses an absolute safety limit (no waiting period), or
        the value is >= z_red SD worse than the personal baseline for >= persistence days in a row
  AMBER if >= z_amber SD worse than baseline for >= persistence days in a row
  GREEN otherwise (a 'watch' note is added if it is deviating but not yet persistent)
  UNKNOWN if there is no value for today
Domain status = worst metric status (RED > AMBER > GREEN; UNKNOWN only if nothing is known).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from .baseline import badness, trailing_count, z_score

GREEN, AMBER, RED, UNKNOWN = "GREEN", "AMBER", "RED", "UNKNOWN"
SEVERITY = {UNKNOWN: -1, GREEN: 0, AMBER: 1, RED: 2}


@dataclass
class MetricResult:
    metric: str
    status: str
    reason: str
    rule: str
    label: str = ""
    domain: str = ""
    unit: str = ""
    provenance: str = ""
    value: float | None = None
    baseline_mean: float | None = None
    baseline_sd: float | None = None
    z: float | None = None
    badness: float | None = None
    days_persisting: int = 0
    persistence_needed: int = 0
    watch: bool = False
    history: list = field(default_factory=list)  # recent values incl. today
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DomainResult:
    domain: str
    status: str
    title: str = ""
    meaning: str = ""
    rule: str = ""
    protocol_id: str | None = None
    triggers: list = field(default_factory=list)  # MetricResult dicts that are flagged or on watch
    metrics: list = field(default_factory=list)   # all MetricResult dicts
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _fmt(x: float) -> str:
    return f"{x:.0f}" if abs(x) >= 100 else f"{x:.1f}"


def assess_metric(
    metric: str,
    values: Sequence[float | None],
    mean: float,
    sd: float,
    *,
    worse_when: str,
    z_amber: float,
    z_red: float,
    persistence: int,
    sparse: bool = False,
    abs_red_above: float | None = None,
    abs_red_below: float | None = None,
    label: str = "",
    unit: str = "",
    provenance: str = "",
    domain: str = "",
) -> MetricResult:
    """`values` is chronological, last item = today (None = missing).
    If sparse=True (e.g. weekly labs), missing entries are skipped and persistence
    counts consecutive *measurements* instead of days."""
    unit_word = "measurements" if sparse else "days"
    rule = (f"AMBER if >= {z_amber:g} SD worse than your baseline for >= {persistence} {unit_word} in a row; "
            f"RED if >= {z_red:g} SD for >= {persistence} {unit_word}")
    if abs_red_above is not None:
        rule += f", or immediately if above {abs_red_above:g} {unit}"
    if abs_red_below is not None:
        rule += f", or immediately if below {abs_red_below:g} {unit}"
    rule += "."
    series = [v for v in values if v is not None] if sparse else list(values)
    base = dict(metric=metric, rule=rule, label=label or metric, domain=domain, unit=unit,
                provenance=provenance, baseline_mean=mean, baseline_sd=sd,
                persistence_needed=persistence, history=list(series))

    if not series or series[-1] is None:
        return MetricResult(status=UNKNOWN, reason="No data for today.", **base)

    today = float(series[-1])
    z = z_score(today, mean, sd)
    bad = badness(z, worse_when)

    def bad_of(v):
        return None if v is None else badness(z_score(v, mean, sd), worse_when)

    bads = [bad_of(v) for v in series]
    amber_streak = trailing_count([b is not None and b >= z_amber for b in bads])
    red_streak = trailing_count([b is not None and b >= z_red for b in bads])

    direction = {"high": "above", "low": "below", "both": "away from"}[worse_when]
    dev = f"{_fmt(today)} {unit} is {abs(z):.1f} SD {('above' if z > 0 else 'below')} your baseline of {_fmt(mean)} {unit}"
    common = dict(value=today, z=round(z, 2), badness=round(bad, 2), days_persisting=amber_streak, **base)

    if abs_red_above is not None and today > abs_red_above:
        return MetricResult(status=RED, reason=f"{_fmt(today)} {unit} is above the safety limit of {abs_red_above:g} {unit}. Safety limits act immediately.", **common)
    if abs_red_below is not None and today < abs_red_below:
        return MetricResult(status=RED, reason=f"{_fmt(today)} {unit} is below the safety limit of {abs_red_below:g} {unit}. Safety limits act immediately.", **common)
    if red_streak >= persistence:
        return MetricResult(status=RED, reason=f"{dev}, and has been >= {z_red:g} SD {direction} it for {red_streak} {unit_word} in a row.", **common)
    if amber_streak >= persistence:
        return MetricResult(status=AMBER, reason=f"{dev}, and has been >= {z_amber:g} SD {direction} it for {amber_streak} {unit_word} in a row.", **common)
    if amber_streak > 0:
        return MetricResult(status=GREEN, watch=True,
                            reason=f"{dev}. Deviating for {amber_streak} of {persistence} {unit_word} needed to raise a flag - watching.", **common)
    return MetricResult(status=GREEN, reason=f"{_fmt(today)} {unit} is within your normal range (baseline {_fmt(mean)} ± {_fmt(sd)} {unit}).", **common)


def worst_status(statuses: Sequence[str]) -> str:
    if not statuses:
        return UNKNOWN
    return max(statuses, key=lambda s: SEVERITY[s])


def protocol_id_for(domain: str, status: str) -> str | None:
    """Protocols live in content/protocols/{domain}_{status}.yaml (lowercase)."""
    if status in (AMBER, RED):
        return f"{domain}_{status.lower()}"
    return None


def assess_domain(domain: str, metric_results: Sequence[MetricResult], text: dict | None = None,
                  rule: str = "") -> DomainResult:
    text = text or {}
    status = worst_status([m.status for m in metric_results])
    triggers = [m.to_dict() for m in metric_results if m.status in (AMBER, RED) or m.watch]
    triggers.sort(key=lambda t: -SEVERITY[t["status"]])
    return DomainResult(
        domain=domain,
        status=status,
        title=text.get("title", domain),
        meaning=text.get("meaning", {}).get(status, ""),
        rule=rule or "Domain status = the worst status of its metrics.",
        protocol_id=protocol_id_for(domain, status),
        triggers=triggers,
        metrics=[m.to_dict() for m in metric_results],
    )


# ---------------------------------------------------------------------------
# Full crew assessment from the thresholds config (still pure: data in, data out)
# ---------------------------------------------------------------------------
def v(entry: Any) -> Any:
    """Read the numeric value of a thresholds.yaml entry."""
    return entry["value"] if isinstance(entry, dict) and "value" in entry else entry


def assess_crew(
    thresholds: dict,
    domain_text: dict,
    baselines: dict[str, tuple[float, float]],
    series: dict[str, list[float | None]],
    *,
    mission_day: int,
    mission_profile: str,
    radiation_event_doses: Sequence[float] = (),
    spe_active: bool = False,
) -> list[dict]:
    from .models_est import assess_bone, assess_radiation  # local import avoids a cycle

    g = thresholds["global"]
    z_amber, z_red, persistence = v(g["z_amber"]), v(g["z_red"]), int(v(g["persistence_days"]))

    by_domain: dict[str, list[MetricResult]] = {"cardiovascular": [], "behavioral": [], "immune": []}
    for name, cfg in thresholds["metrics"].items():
        if cfg.get("assess") == "adherence" or cfg["domain"] not in by_domain:
            continue
        mean, sd = baselines.get(name, (None, None))
        if mean is None:
            res = MetricResult(metric=name, status=UNKNOWN, reason="No personal baseline.", rule="",
                               label=cfg["label"], domain=cfg["domain"], provenance=cfg["provenance"])
        else:
            res = assess_metric(
                name, series.get(name, []), mean, sd,
                worse_when=cfg["worse_when"], z_amber=z_amber, z_red=z_red,
                persistence=int(v(cfg.get("persistence", persistence))),
                sparse=bool(cfg.get("sparse", False)),
                abs_red_above=v(cfg["abs_red_above"]) if "abs_red_above" in cfg else None,
                abs_red_below=v(cfg["abs_red_below"]) if "abs_red_below" in cfg else None,
                label=cfg["label"], unit=cfg["sim_mean"]["unit"], provenance=cfg["provenance"],
                domain=cfg["domain"],
            )
        by_domain[cfg["domain"]].append(res)

    out = [assess_domain(d, ms, domain_text.get(d)).to_dict() for d, ms in by_domain.items()]
    out.append(assess_bone(thresholds, series.get("exercise_minutes", []), mission_day,
                           persistence, domain_text.get("bone")).to_dict())
    m = thresholds["missions"][mission_profile]
    out.append(assess_radiation(thresholds, mission_day, v(m["daily_dose_msv"]),
                                radiation_event_doses, spe_active, domain_text.get("radiation")).to_dict())
    order = ["cardiovascular", "bone", "immune", "behavioral", "radiation"]  # challenge text order
    return sorted(out, key=lambda d: order.index(d["domain"]))
