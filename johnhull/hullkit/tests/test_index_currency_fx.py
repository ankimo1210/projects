"""Hull 17.5 Garman-Kohlhagen, IV and inversion with correct notionals."""

import math

import pytest
from hullkit import _index_currency as index
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


@pytest.mark.parametrize("sigma,printed", [(0.2, 0.0639), (0.1, 0.0285)])
def test_example_17_2_trial_prices(sigma, printed):
    result = index.carry_option_details(1.6, 1.6, 0.08, 0.11, sigma, 4 / 12)
    assert result["call"] == pytest.approx(printed, abs=5e-5)


def test_example_17_2_iv_against_independent_integrated_payoff_root():
    def residual(sigma):
        width = sigma * math.sqrt(4 / 12)
        log_mean = math.log(1.6) + (0.08 - 0.11 - 0.5 * sigma**2) * 4 / 12
        cutoff = (math.log(1.6) - log_mean) / width
        expected = quad(
            lambda z: (math.exp(log_mean + width * z) - 1.6) * norm.pdf(z), cutoff, 12, epsabs=1e-12
        )[0]
        return math.exp(-0.08 * 4 / 12) * expected - 0.043

    reference = brentq(residual, 0.1, 0.2, xtol=1e-13)
    iv = index.carry_implied_vol(0.043, 1.6, 1.6, 0.08, 0.11, 4 / 12)
    assert iv == pytest.approx(0.14111938, abs=5e-9)
    assert iv == pytest.approx(0.141, abs=0.0005)
    assert iv == pytest.approx(reference, abs=1e-9)
    assert index.carry_option_details(1.6, 1.6, 0.08, 0.11, iv, 4 / 12)["call"] == pytest.approx(
        0.043, abs=1e-10
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_currency_inversion_prices_with_correct_domestic_notional_factor(kind):
    direct = index.carry_option_details(1.6, 1.55, 0.08, 0.11, 0.2, 4 / 12)[kind]
    inverse = index.currency_inversion(1.6, 1.55, 0.08, 0.11, 0.2, 4 / 12, kind=kind)
    assert inverse["domestic_value"] == pytest.approx(direct, abs=1e-14)
    assert inverse["inverse_spot"] == pytest.approx(1 / 1.6)
    assert inverse["inverse_strike"] == pytest.approx(1 / 1.55)
    assert inverse["inverse_notional"] == pytest.approx(1.55)
    assert inverse["domestic_value"] == pytest.approx(
        1.6 * 1.55 * inverse["foreign_unit_value"], abs=1e-14
    )


def test_inverted_terminal_put_cash_is_the_original_domestic_call():
    strike = 1.55
    for terminal in [0.8, 1.55, 2.3]:
        # Buy K inverse puts (domestic units as underlying), then convert foreign cash.
        foreign_cash = strike * max(1 / strike - 1 / terminal, 0)
        assert terminal * foreign_cash == pytest.approx(max(terminal - strike, 0), abs=1e-14)


def test_reciprocal_and_implied_vol_require_positive_strike_and_maturity():
    with pytest.raises(ValueError):
        index.currency_inversion(1.6, 0, 0.08, 0.11, 0.2, 4 / 12)
    with pytest.raises(ValueError):
        index.carry_implied_vol(0.043, 1.6, 1.6, 0.08, 0.11, 0)


@pytest.mark.parametrize("strike,sigma", [(200, 0.3), (150, 0.2)])
def test_tiny_positive_fx_call_retains_volatility_against_independent_density(strike, sigma):
    width = sigma * math.sqrt(0.1)
    log_mean = math.log(100) + (0.05 - 0.03 - 0.5 * sigma**2) * 0.1
    cutoff = (math.log(strike) - log_mean) / width
    price = (
        math.exp(-0.05 * 0.1)
        * quad(
            lambda z: (math.exp(log_mean + width * z) - strike) * norm.pdf(z),
            cutoff,
            15,
            epsabs=1e-26,
            epsrel=1e-11,
        )[0]
    )
    assert 0 < price < 1e-8
    assert index.carry_implied_vol(price, 100, strike, 0.05, 0.03, 0.1) == pytest.approx(
        sigma, abs=1e-9
    )


def test_exact_deterministic_bound_has_zero_iv_but_upper_bound_has_no_finite_iv():
    from hullkit.bsm import call_price

    lower = float(call_price(1.6, 1.5, 0.08, 0, 0.5, q=0.11))
    assert index.carry_implied_vol(lower, 1.6, 1.5, 0.08, 0.11, 0.5) == pytest.approx(0)
    with pytest.raises(ValueError):
        index.carry_implied_vol(1.6 * math.exp(-0.11 * 0.5), 1.6, 1.5, 0.08, 0.11, 0.5)
