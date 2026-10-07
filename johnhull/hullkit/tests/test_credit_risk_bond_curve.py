"""Hull Ex24.1/2: yield bootstrap vs direct surviving cashflows/recovery states."""

import math

import numpy as np
import pytest
from hullkit import _credit_risk as c
from hullkit.credit_curve import HazardCurve
from scipy.optimize import root


def test_source_example_24_1_average_vs_interval_hazards():
    result = c.spread_hazards([1, 2, 3], [0.015, 0.018, 0.0195], 0.4)
    assert result["average"] == pytest.approx([0.025, 0.03, 0.0325])
    assert result["curve"].hazards == pytest.approx([0.025, 0.035, 0.0375])
    assert result["curve"].survival(3) == pytest.approx(math.exp(-(0.025 + 0.035 + 0.0375)))


def test_source_example_24_2_all_bond_price_and_loss_points():
    result = c.bond_curve_from_yields([1, 2, 3], [0.065, 0.068, 0.0695], 0.08, 0.05, 0.4)
    assert result["prices"] == pytest.approx([101.33, 101.99, 102.47], abs=0.005)
    assert result["risk_free"] == pytest.approx([102.83, 105.52, 108.08], abs=0.005)
    assert result["loss_pv"] == pytest.approx([1.50, 3.53, 5.61], abs=0.005)
    assert np.array(result["curve"].hazards) * 100 == pytest.approx([2.46, 3.48, 3.74], abs=0.005)
    for maturity, price in zip([1, 2, 3], result["prices"], strict=True):
        table = c.bond_credit_table(result["curve"], 100, 0.08, maturity, 0.05, 0.4)
        assert table["value"] == pytest.approx(price, abs=1e-10)
    one = c.bond_credit_table(result["curve"], 100, 0.08, 1, 0.05, 0.4)
    assert one["default_forward_values"] == pytest.approx([104.12, 102.71], abs=0.005)
    assert one["discounted_default_losses"] == pytest.approx([63.33, 60.40], abs=0.005)


def test_bootstrap_independent_simultaneous_equations_over_recovery_events():
    result = c.bond_curve_from_yields([1, 2, 3], [0.065, 0.068, 0.0695], 0.08, 0.05, 0.4)

    def state_price(hazards, years):
        previous, price = 1, 0
        for half in range(1, 2 * years + 1):
            end = half / 2
            cumulative = sum(hazards[j] * max(min(end - j, 1), 0) for j in range(years))
            surviving = math.exp(-cumulative)
            price += 4 * surviving * math.exp(-0.05 * end)
            price += 40 * (previous - surviving) * math.exp(-0.05 * (end - 0.25))
            previous = surviving
        return price + 100 * previous * math.exp(-0.05 * years)

    solved = root(
        lambda rates: [
            state_price(rates, years) - price
            for years, price in zip([1, 2, 3], result["prices"], strict=True)
        ],
        [0.02, 0.03, 0.04],
    )
    assert solved.success
    assert solved.x == pytest.approx(result["curve"].hazards, abs=1e-10)


def test_zero_hazard_direct_value_equals_promised_payments():
    table = c.bond_credit_table(HazardCurve.from_constant(0), 100, 0.08, 2, 0.05, 0.4)
    independent = sum(4 * math.exp(-0.05 * j / 2) for j in range(1, 5)) + 100 * math.exp(-0.1)
    assert table["value"] == pytest.approx(independent)
    assert table["loss_pv"] == pytest.approx(0, abs=1e-12)
