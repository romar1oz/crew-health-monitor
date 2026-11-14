from app.engine.rules import (AMBER, GREEN, RED, UNKNOWN, MetricResult, assess_domain,
                              assess_metric, protocol_id_for, worst_status)

# Metric "worse when high": baseline 100 ± 10. 125 = +2.5 SD (amber level), 135 = +3.5 SD (red level).
KW = dict(mean=100, sd=10, worse_when="high", z_amber=2.0, z_red=3.0, persistence=3)


def run(values, **over):
    return assess_metric("m", values, **{**KW, **over})


def test_normal_is_green():
    r = run([100, 102, 98])
    assert r.status == GREEN and not r.watch


def test_two_days_deviation_does_not_flag():
    r = run([100, 125, 125])
    assert r.status == GREEN
    assert r.watch and r.days_persisting == 2


def test_three_days_deviation_flags_amber():
    r = run([100, 125, 125, 125])
    assert r.status == AMBER and r.days_persisting == 3


def test_three_days_at_red_level_flags_red():
    assert run([135, 135, 135]).status == RED


def test_red_level_only_two_days_is_amber_if_amber_persistent():
    assert run([125, 135, 135]).status == AMBER


def test_gap_in_deviation_resets_streak():
    assert run([125, 125, 100, 125, 125]).status == GREEN


def test_missing_day_breaks_daily_streak():
    assert run([125, 125, None, 125, 125]).status == GREEN


def test_direction_good_side_never_flags():
    # 3 days far BELOW baseline on a "worse when high" metric is fine
    assert run([60, 60, 60]).status == GREEN


def test_worse_when_low():
    assert run([75, 75, 75], worse_when="low").status == AMBER


def test_worse_when_both():
    assert run([75, 75, 75], worse_when="both").status == AMBER
    assert run([125, 125, 125], worse_when="both").status == AMBER


def test_absolute_limit_is_immediate():
    r = run([100, 100, 111], abs_red_above=110)
    assert r.status == RED and "safety limit" in r.reason


def test_absolute_lower_limit():
    assert run([100, 89], abs_red_below=90).status == RED


def test_missing_today_is_unknown():
    assert run([100, 100, None]).status == UNKNOWN
    assert run([]).status == UNKNOWN


def test_sparse_counts_measurements_not_days():
    r = run([125, None, None, 125], sparse=True, persistence=2)
    assert r.status == AMBER and r.days_persisting == 2


def test_result_explains_itself():
    r = run([100, 125, 125, 125])
    assert "3 days in a row" in r.reason and "baseline" in r.reason
    assert "3 days" in r.rule and r.z == 2.5


def _m(status, watch=False):
    return MetricResult(metric="x", status=status, reason="", rule="", watch=watch)


def test_worst_of_aggregation():
    assert worst_status([GREEN, AMBER, GREEN]) == AMBER
    assert worst_status([AMBER, RED]) == RED
    assert worst_status([UNKNOWN, GREEN]) == GREEN
    assert worst_status([UNKNOWN, UNKNOWN]) == UNKNOWN
    assert worst_status([]) == UNKNOWN


def test_domain_result_triggers_and_protocol():
    d = assess_domain("behavioral", [_m(GREEN), _m(AMBER), _m(GREEN, watch=True)],
                      {"title": "Behavioral", "meaning": {"AMBER": "off normal"}})
    assert d.status == AMBER
    assert d.meaning == "off normal"
    assert d.protocol_id == "behavioral_amber"
    assert len(d.triggers) == 2  # the amber one + the watch one


def test_protocol_ids():
    assert protocol_id_for("radiation", RED) == "radiation_red"
    assert protocol_id_for("radiation", GREEN) is None
