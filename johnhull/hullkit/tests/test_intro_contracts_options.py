"""Hull §1.5 option contract multipliers/premium and independent payoff expectation."""

import math

import pytest
from hullkit import _intro_contracts as c
from scipy.integrate import quad
from scipy.stats import norm


def test_source_apple_long_call_all_three_amounts():
    result = c.option_contract_cashflows(400, 340, 20.3)
    assert [result["premium_cash"], result["payoff"], result["profit"]] == pytest.approx(
        [-2030, 6000, 3970]
    )


def test_source_apple_short_put_all_three_amounts():
    result = c.option_contract_cashflows(250, 290, 12.7, kind="put", side="short")
    assert [result["premium_cash"], result["payoff"], result["profit"]] == pytest.approx(
        [1270, -4000, -2730]
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_payoff_expectation_against_independent_analytic_lognormal_value(kind):
    forward, strike, vol = 350, 340, 0.25
    threshold = (math.log(strike / forward) + 0.5 * vol**2) / vol
    lo, hi = (threshold, 10) if kind == "call" else (-10, threshold)

    def integrand(z):
        s = forward * math.exp(-0.5 * vol**2 + vol * z)
        return c.option_contract_cashflows(s, strike, 20.3, kind=kind)["payoff"] * norm.pdf(z)

    expected = quad(integrand, lo, hi, epsabs=1e-8)[0]
    d1 = (math.log(forward / strike) + 0.5 * vol**2) / vol
    d2 = d1 - vol
    analytic = (
        forward * norm.cdf(d1) - strike * norm.cdf(d2)
        if kind == "call"
        else strike * norm.cdf(-d2) - forward * norm.cdf(-d1)
    )
    assert expected == pytest.approx(100 * analytic, rel=1e-10)
    long = c.option_contract_cashflows([0, 340, 400], strike, 20.3, kind=kind)
    short = c.option_contract_cashflows([0, 340, 400], strike, 20.3, kind=kind, side="short")
    assert long["profit"] == pytest.approx(-short["profit"])
