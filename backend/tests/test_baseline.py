import pytest

from app.engine.baseline import badness, compute_baseline, trailing_count, z_score


def test_mean_and_sample_sd():
    b = compute_baseline([2, 4, 4, 4, 5, 5, 7, 9])
    assert b.mean == pytest.approx(5.0)
    assert b.sd == pytest.approx(2.138, abs=1e-3)  # sample SD (n-1)
    assert b.n == 8


def test_missing_values_ignored():
    assert compute_baseline([1, None, 3]).n == 2


def test_sd_floor_applied():
    assert compute_baseline([5, 5, 5, 5], min_sd=0.5).sd == 0.5


def test_zero_sd_without_floor_rejected():
    with pytest.raises(ValueError):
        compute_baseline([5, 5, 5])


def test_too_few_values_rejected():
    with pytest.raises(ValueError):
        compute_baseline([5])


def test_z_score():
    assert z_score(70, 60, 5) == 2.0
    with pytest.raises(ValueError):
        z_score(1, 1, 0)


@pytest.mark.parametrize("z,direction,expected", [
    (2.0, "high", 2.0), (2.0, "low", -2.0), (-2.0, "low", 2.0), (-2.0, "both", 2.0),
])
def test_badness_direction(z, direction, expected):
    assert badness(z, direction) == expected


def test_badness_unknown_direction():
    with pytest.raises(ValueError):
        badness(1, "sideways")


@pytest.mark.parametrize("flags,n", [
    ([], 0), ([False], 0), ([True], 1), ([True, False, True, True], 2), ([True] * 5, 5),
])
def test_trailing_count(flags, n):
    assert trailing_count(flags) == n
