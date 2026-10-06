"""Hull §5.4 source forward prices and financed cash trades."""

import pytest
from hullkit import _forward_pricing as f
from scipy.integrate import solve_ivp


def test_source_all_six_values():
    fair = f.no_income_forward(40, 0.05, 0.25)
    assert fair == pytest.approx(40.50, abs=0.005)
    assert f.carry_cash(40, 0.05, 0.25, 43)["carry_profit"] == pytest.approx(2.50, abs=0.005)
    assert f.carry_cash(40, 0.05, 0.25, 39)["reverse_profit"] == pytest.approx(1.50, abs=0.005)
    assert f.no_income_forward(930, 0.06, 4 / 12) == pytest.approx(948.79, abs=0.005)
    strip = f.no_income_forward(70, 0.04, 0.25)
    assert strip == pytest.approx(70.70, abs=0.005)
    assert strip - 70 == pytest.approx(0.70, abs=0.005)


def test_independent_financing_ode_and_zero_entry_cash():
    loan = solve_ivp(lambda t, y: 0.05 * y, (0, 0.25), [40], rtol=1e-11, atol=1e-11).y[0, -1]
    a = f.carry_cash(40, 0.05, 0.25, 43)
    assert a["carry_profit"] == pytest.approx(43 - loan, abs=1e-9)
    assert a["entry_cash"] == pytest.approx(0, abs=1e-12)
    assert f.no_income_forward(40, -0.05, 0.25) < 40
