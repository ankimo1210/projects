import pytest
from ratesvol.rfr import compounded_in_arrears, simple_average


def test_constant_rate_compounds_like_the_closed_form():
    expected = ((1 + 0.05 / 360) ** 90 - 1) * 360 / 90
    assert compounded_in_arrears([0.05] * 90, [1] * 90) == pytest.approx(expected, rel=1e-12)


def test_weekend_fixing_counts_three_days():
    expected = ((1 + 0.05 / 360) * (1 + 0.06 * 3 / 360) - 1) * 360 / 4
    assert compounded_in_arrears([0.05, 0.06], [1, 3]) == pytest.approx(expected, rel=1e-12)
    assert simple_average([0.05, 0.06], [1, 3]) == pytest.approx(0.0575)


def test_compounding_beats_the_simple_average_for_positive_rates():
    rates, weights = [0.05] * 60 + [0.0525] * 30, [1] * 90
    assert compounded_in_arrears(rates, weights) > simple_average(rates, weights)


def test_shape_mismatch_is_rejected():
    with pytest.raises(ValueError):
        compounded_in_arrears([0.05, 0.05], [1])
