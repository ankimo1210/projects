"""Hull §1.7 FX and protective-put examples, independent cash and analytic expectation."""

import math

import pytest
from hullkit import _intro_contracts as c
from scipy.integrate import quad
from scipy.stats import norm


def test_source_import_and_export_hedges_and_unhedged_payments():
    pay = c.fx_forward_hedge(10_000_000, 1.2225, [1.2, 1.3])
    receive = c.fx_forward_hedge(30_000_000, 1.2220, [1.2, 1.3], obligation="receive")
    assert pay["net_cash"] == pytest.approx([-12_225_000] * 2)
    assert pay["unhedged_cash"] == pytest.approx([-12_000_000, -13_000_000])
    assert receive["net_cash"] == pytest.approx([36_660_000] * 2)
    # Independent purchase foreign cash / sell future foreign receipts and settlement legs.
    for s, hedge in zip([1.2, 1.3], pay["hedge_payoff"], strict=True):
        assert -10_000_000 * s + hedge == pytest.approx(-10_000_000 * 1.2225)


def test_source_thousand_shares_ten_put_contracts_insurance_floor_and_cost():
    result = c.protected_holding(1000, [20, 27.5, 40], 27.5, 1, multiplier=100)
    assert result["contracts"] == pytest.approx(10)
    assert result["premium_per_contract"] == pytest.approx(100)
    assert result["premium_cost"] == pytest.approx(1000)
    assert result["terminal_value"][:2] == pytest.approx([27_500] * 2)
    assert result["value_after_premium"][:2] == pytest.approx([26_500] * 2)


def test_protected_holding_expected_value_against_independent_call_plus_cash_price():
    forward, strike, vol = 30, 27.5, 0.3
    barrier = (math.log(strike / forward) + 0.5 * vol**2) / vol

    def density(z):
        s = forward * math.exp(-0.5 * vol**2 + vol * z)
        return c.protected_holding(1000, s, strike, 1)["value_after_premium"] * norm.pdf(z)

    integral = quad(density, -10, barrier)[0] + quad(density, barrier, 10)[0]
    d1 = (math.log(forward / strike) + 0.5 * vol**2) / vol
    call = forward * norm.cdf(d1) - strike * norm.cdf(d1 - vol)
    assert integral == pytest.approx(1000 * (strike + call - 1), rel=1e-10)
