"""Hull 17.5 Garman-Kohlhagen, IV and inversion with correct notionals."""
import math

import pytest
from hullkit import _index_currency as index
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


@pytest.mark.parametrize("sigma,printed", [(.2, .0639), (.1, .0285)])
def test_example_17_2_trial_prices(sigma, printed):
    result = index.carry_option_details(1.6, 1.6, .08, .11, sigma, 4/12)
    assert result["call"] == pytest.approx(printed, abs=5e-5)


def test_example_17_2_iv_against_independent_integrated_payoff_root():
    def residual(sigma):
        width = sigma*math.sqrt(4/12)
        log_mean = math.log(1.6)+(.08-.11-.5*sigma**2)*4/12
        cutoff = (math.log(1.6)-log_mean)/width
        expected = quad(lambda z: (math.exp(log_mean+width*z)-1.6)*norm.pdf(z), cutoff, 12, epsabs=1e-12)[0]
        return math.exp(-.08*4/12)*expected-.043
    reference = brentq(residual, .1, .2, xtol=1e-13)
    iv = index.carry_implied_vol(.043, 1.6, 1.6, .08, .11, 4/12)
    assert iv == pytest.approx(.14111938, abs=5e-9)
    assert iv == pytest.approx(.141, abs=.0005)
    assert iv == pytest.approx(reference, abs=1e-9)
    assert index.carry_option_details(1.6, 1.6, .08, .11, iv, 4/12)["call"] == pytest.approx(.043, abs=1e-10)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_currency_inversion_prices_with_correct_domestic_notional_factor(kind):
    direct = index.carry_option_details(1.6, 1.55, .08, .11, .2, 4/12)[kind]
    inverse = index.currency_inversion(1.6, 1.55, .08, .11, .2, 4/12, kind=kind)
    assert inverse["domestic_value"] == pytest.approx(direct, abs=1e-14)
    assert inverse["inverse_spot"] == pytest.approx(1/1.6)
    assert inverse["inverse_strike"] == pytest.approx(1/1.55)
    assert inverse["inverse_notional"] == pytest.approx(1.55)
    assert inverse["domestic_value"] == pytest.approx(1.6*1.55*inverse["foreign_unit_value"], abs=1e-14)


def test_inverted_terminal_put_cash_is_the_original_domestic_call():
    strike = 1.55
    for terminal in [.8, 1.55, 2.3]:
        # Buy K inverse puts (domestic units as underlying), then convert foreign cash.
        foreign_cash = strike*max(1/strike-1/terminal, 0)
        assert terminal*foreign_cash == pytest.approx(max(terminal-strike, 0), abs=1e-14)


def test_reciprocal_and_implied_vol_require_positive_strike_and_maturity():
    with pytest.raises(ValueError):
        index.currency_inversion(1.6, 0, .08, .11, .2, 4/12)
    with pytest.raises(ValueError):
        index.carry_implied_vol(.043, 1.6, 1.6, .08, .11, 0)
