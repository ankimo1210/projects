"""Hull Table4.6 and duration Examples4.4/4.5."""

import numpy as np
import pytest
from hullkit import _rates_foundations as r

T = np.arange(0.5, 3.01, 0.5)
CF = np.array([5, 5, 5, 5, 5, 105])


def test_source_all_thirty_three_duration_values():
    a = r.bond_sensitivities(T, CF, 0.12)
    assert a["cash_present_values"] == pytest.approx(
        [4.709, 4.435, 4.176, 3.933, 3.704, 73.256], abs=0.0005
    )
    assert a["weights"] == pytest.approx([0.050, 0.047, 0.044, 0.042, 0.039, 0.778], abs=0.0005)
    assert T * a["weights"] == pytest.approx([0.025, 0.047, 0.066, 0.083, 0.098, 2.333], abs=0.0005)
    assert [CF.sum(), a["price"], a["weights"].sum(), a["macaulay"]] == pytest.approx(
        [130, 94.213, 1, 2.653], abs=0.0005
    )
    assert a["dollar_duration"] == pytest.approx(249.95, abs=0.005)
    assert -a["dollar_duration"] * 0.001 == pytest.approx(-0.250, abs=0.0005)
    assert a["price"] - a["dollar_duration"] * 0.001 == pytest.approx(93.963, abs=0.0005)
    y = r.convert_rate(0.12, None, 2)
    b = r.bond_sensitivities(T, CF, y, frequency=2)
    exact = r.bond_sensitivities(T, CF, y + 0.001, frequency=2)["price"]
    assert 100 * y == pytest.approx(12.3673, abs=0.00005)
    assert b["modified"] == pytest.approx(2.499, abs=0.0005)
    assert -b["dollar_duration"] == pytest.approx(-235.39, abs=0.005)
    assert -b["dollar_duration"] * 0.001 == pytest.approx(-0.235, abs=0.0005)
    assert b["price"] - b["dollar_duration"] * 0.001 == pytest.approx(93.978, abs=0.0005)
    assert exact == pytest.approx(93.978, abs=0.0005)
    assert 100 * (y + 0.001) == pytest.approx(12.4673, abs=0.00005)
    assert b["macaulay"] == pytest.approx(a["macaulay"], abs=1e-11)


@pytest.mark.parametrize("frequency", [None, 2])
def test_independent_price_difference_and_portfolio_duration(frequency):
    y = 0.12 if frequency is None else r.convert_rate(0.12, None, frequency)
    a = r.bond_sensitivities(T, CF, y, frequency=frequency)

    def price(q):
        factors = np.exp(-q * T) if frequency is None else (1 + q / frequency) ** (-frequency * T)
        return CF @ factors

    eps = 1e-6
    derivative = (price(y + eps) - price(y - eps)) / (2 * eps)
    assert a["dollar_duration"] == pytest.approx(-derivative, rel=1e-8)
    assert a["dv01"] == pytest.approx(-derivative * 1e-4, rel=1e-8)
    other = r.bond_sensitivities([1], [100], y, frequency=frequency)
    total = r.bond_sensitivities(np.r_[T, 1], np.r_[CF, 100], y, frequency=frequency)
    weighted = (a["price"] * a["modified"] + other["price"] * other["modified"]) / (
        a["price"] + other["price"]
    )
    assert total["modified"] == pytest.approx(weighted)
