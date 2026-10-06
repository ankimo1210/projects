"""Hull Table5.3/Example5.2 known-income forward."""

import numpy as np
import pytest
from hullkit import _forward_pricing as f


def test_source_all_seven_values():
    a = f.known_income_forward(900, [4 / 12], [40], [0.03], 0.04, 0.75)
    assert [a["income_pv"], a["net_spot"], a["forward"]] == pytest.approx(
        [39.60, 860.40, 886.60], abs=0.005
    )
    assert [910 - a["forward"], a["forward"] - 870] == pytest.approx([23.40, 16.60], abs=0.005)
    b = f.known_income_forward(
        50, [0.25, 0.5, 0.75], [0.75, 0.75, 0.75], [0.08, 0.08, 0.08], 0.08, 10 / 12
    )
    assert b["income_pv"] == pytest.approx(2.162, abs=0.0005)
    assert b["forward"] == pytest.approx(51.14, abs=0.005)


def test_independent_cash_repayment_linear_system_and_after_maturity_exclusion():
    ts = np.array([0.25, 0.5, 0.75])
    rates = np.full(3, 0.08)
    coupons = np.full(3, 0.75)
    loans = np.linalg.solve(np.diag(np.exp(rates * ts)), coupons)
    remaining_loan = 50 - loans.sum()
    a = f.known_income_forward(50, ts, coupons, rates, 0.08, 10 / 12)
    assert a["forward"] == pytest.approx(remaining_loan * np.exp(0.08 * 10 / 12), abs=1e-11)
    b = f.known_income_forward(50, [*ts, 2], [*coupons, 10], [*rates, 0.08], 0.08, 10 / 12)
    assert b["forward"] == pytest.approx(a["forward"])
