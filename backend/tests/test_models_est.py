import pytest

from app.config import load_thresholds
from app.engine.models_est import (assess_bone, assess_radiation, cumulative_dose_msv,
                                   estimate_bone_loss_pct, exercise_adherence)
from app.engine.rules import AMBER, GREEN, RED, UNKNOWN

TH = load_thresholds()


def test_adherence_capped_at_one():
    assert exercise_adherence([240, 120, 60], 120) == pytest.approx((1 + 1 + 0.5) / 3)
    assert exercise_adherence([None, None], 120) is None


def test_bone_formula():
    # 1 %/month for 30.44 days, no exercise -> 1 %
    assert estimate_bone_loss_pct(30.44, 1.0, 0.5, 0.0) == pytest.approx(1.0)
    # full adherence halves it with effectiveness 0.5
    assert estimate_bone_loss_pct(30.44, 1.0, 0.5, 1.0) == pytest.approx(0.5)


def test_bone_green_with_good_exercise():
    d = assess_bone(TH, [120] * 7, mission_day=60, persistence=3)
    assert d.status == GREEN
    est = next(m for m in d.metrics if m["metric"] == "bone_loss_est")
    assert est["provenance"] == "MODEL-ESTIMATED" and "formula" in est["extra"]


def test_bone_amber_after_three_low_days():
    d = assess_bone(TH, [120, 120, 60, 60, 60], mission_day=30, persistence=3)
    assert d.status == AMBER


def test_bone_unknown_without_data():
    assert assess_bone(TH, [], mission_day=30, persistence=3).status == UNKNOWN


def test_cumulative_dose():
    assert cumulative_dose_msv(100, 1.8, [10, 5]) == pytest.approx(195)


def test_radiation_levels():
    limit = TH["radiation"]["career_limit_msv"]["value"]
    assert assess_radiation(TH, 10, 1.0).status == GREEN
    assert assess_radiation(TH, 1, limit * 0.6).status == AMBER
    assert assess_radiation(TH, 1, limit * 0.9).status == RED


def test_spe_forces_red():
    d = assess_radiation(TH, 10, 1.0, spe_active=True)
    assert d.status == RED and d.protocol_id == "radiation_red"
