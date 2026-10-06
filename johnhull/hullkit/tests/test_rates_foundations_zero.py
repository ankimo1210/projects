"""Hull §4.5 zero investment pin and independent differential equation."""

import pytest
from hullkit import _rates_foundations as r
from scipy.integrate import solve_ivp


def test_source_zero_investment_amount():
    assert r.zero_investment(100, 0.05, 5) == pytest.approx(128.40, abs=0.005)


def test_independent_cash_account_ode():
    ode = solve_ivp(lambda t, y: 0.05 * y, (0, 5), [100.0], rtol=1e-11, atol=1e-11)
    amount = r.zero_investment(100, 0.05, 5)
    assert amount == pytest.approx(ode.y[0, -1], rel=1e-10)
    assert r.zero_investment(100, -0.05, 5) == pytest.approx(10000 / amount)
