"""Hull GE 16.3: index strikes, RSUs and market-leveraged stock units."""

import math
from fractions import Fraction

import pytest
from hullkit import _employee_options as employee
from scipy.integrate import quad
from scipy.stats import lognorm


@pytest.mark.parametrize("index,strike", [(2200, 33), (1700, 25.50)])
def test_source_index_linked_strikes(index, strike):
    result = employee.equity_award_payoffs(30, 30, 30, index, 2000)
    assert result["indexed_strike"] == pytest.approx(strike)
    assert result["indexed_option_payoff"] == pytest.approx(max(30-strike, 0))


def test_award_cash_values_against_independent_fraction_share_ledger():
    terminal, initial = Fraction(45), Fraction(30)
    msu_shares = terminal/initial
    result = employee.equity_award_payoffs(45, 30, 30, 2200, 2000)
    assert result["rsu_value"] == pytest.approx(float(terminal))
    assert result["msu_shares"] == pytest.approx(float(msu_shares))
    assert result["msu_value"] == pytest.approx(float(msu_shares*terminal))
    assert result["indexed_option_payoff"] == pytest.approx(12)


def test_msu_payoff_integral_against_independent_gbm_second_moment():
    s0, mu, sigma, t = 30, .1, .25, 2
    density = lognorm(s=sigma*math.sqrt(t), scale=s0*math.exp((mu-sigma**2/2)*t))
    expected = quad(lambda s: employee.equity_award_payoffs(s, s0, 30, 2000, 2000)["msu_value"]*density.pdf(s), 0, math.inf, epsabs=1e-9)[0]
    assert expected == pytest.approx(s0*math.exp((2*mu+sigma**2)*t), abs=1e-8)


def test_zero_terminal_stock_awards_are_worth_zero():
    result = employee.equity_award_payoffs(0, 30, 30, 2200, 2000)
    assert [result["rsu_value"], result["msu_shares"], result["msu_value"], result["indexed_option_payoff"]] == pytest.approx([0, 0, 0, 0])


def test_index_rebasing_requires_nonzero_initial_level():
    with pytest.raises(ValueError):
        employee.equity_award_payoffs(30, 30, 30, 2200, 0)
