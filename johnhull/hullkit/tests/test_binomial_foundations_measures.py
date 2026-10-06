"""Hull GE section 13.2: P probability and option-specific required return."""

import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations


def test_hull_physical_probability_and_55_96_percent_option_return():
    result = foundations.physical_comparison(20, 22, 18, 1, 0, 0.04, 0.25, physical_drift=0.10)
    assert result["physical_probability"] == pytest.approx(0.6266, abs=0.00005)
    assert result["physical_payoff_expectation"] == pytest.approx(0.6266, abs=0.00005)
    assert 100 * result["required_discount_rate"] == pytest.approx(55.96, abs=0.005)
    assert result["risk_neutral_probability"] == pytest.approx(0.5503, abs=0.00005)
    assert result["price"] == pytest.approx(0.545, abs=0.0005)
    # Independent two-state replication does not consume the actual-world probability.
    delta, bank = np.linalg.solve([[22, math.exp(0.01)], [18, math.exp(0.01)]], [1, 0])
    independent_price = delta * 20 + bank
    independent_p = (20 * math.exp(0.10 * 0.25) - 18) / 4
    assert result["required_discount_rate"] == pytest.approx(
        math.log(independent_p / independent_price) / 0.25, abs=1e-12
    )
    assert result["physical_payoff_expectation"] * math.exp(
        -result["required_discount_rate"] * 0.25
    ) == pytest.approx(independent_price, abs=1e-12)
    assert result["risk_free_discounted_physical_payoff"] > independent_price + 0.05


def test_risk_neutral_growth_and_price_are_unchanged_by_physical_drift():
    results = [
        foundations.physical_comparison(20, 22, 18, 1, 0, 0.04, 0.25, physical_drift=mu)
        for mu in [0.02, 0.04, 0.1]
    ]
    assert [r["price"] for r in results] == pytest.approx([results[0]["price"]] * 3, abs=1e-12)
    assert all(
        r["q_stock_expectation"] == pytest.approx(20 * math.exp(0.01), abs=1e-12) for r in results
    )
    for mu, result in zip([0.02, 0.04, 0.1], results, strict=True):
        assert result["p_stock_expectation"] == pytest.approx(20 * math.exp(mu * 0.25), abs=1e-12)


def test_zero_payoff_has_no_defined_required_return():
    result = foundations.physical_comparison(20, 22, 18, 0, 0, 0.04, 0.25, physical_drift=0.1)
    assert result["required_discount_rate"] is None
