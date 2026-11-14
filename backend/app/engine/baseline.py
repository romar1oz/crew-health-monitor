"""Personal baseline math. Pure functions: no database, no web framework."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Baseline:
    mean: float
    sd: float
    n: int


def compute_baseline(values: Iterable[float | None], min_sd: float = 0.0) -> Baseline:
    """Mean and sample SD of pre-flight values. SD is floored at `min_sd` so tiny
    pre-flight variability does not make every small change look huge."""
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        raise ValueError("A baseline needs at least 2 values")
    sd = max(statistics.stdev(vals), min_sd)
    if sd <= 0:
        raise ValueError("Baseline SD is zero; set a min_sd floor")
    return Baseline(mean=statistics.fmean(vals), sd=sd, n=len(vals))


def z_score(value: float, mean: float, sd: float) -> float:
    if sd <= 0:
        raise ValueError("sd must be > 0")
    return (value - mean) / sd


def badness(z: float, worse_when: str) -> float:
    """Turn a signed z-score into 'how many SD in the BAD direction'.
    Positive = worse than baseline; zero or negative = fine."""
    if worse_when == "high":
        return z
    if worse_when == "low":
        return -z
    if worse_when == "both":
        return abs(z)
    raise ValueError(f"unknown worse_when: {worse_when!r}")


def trailing_count(flags: Sequence[bool]) -> int:
    """How many True values in a row at the END of the list (= days persisting up to today)."""
    n = 0
    for f in reversed(flags):
        if not f:
            break
        n += 1
    return n
