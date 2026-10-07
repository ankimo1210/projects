"""Hull 19.6: gamma-neutral hedge and quadratic delta-hedging error."""

import math

import pytest
from hullkit import _greeks_hedging as greeks
from hullkit import bsm
from scipy.integrate import quad
from scipy.stats import norm


def density(spot, kind):
    strike, rate, sigma, time = 50, 0.05, 0.2, 0.3846
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )


@pytest.mark.parametrize("move", [-2, 2])
def test_example_19_3_delta_neutral_negative_gamma_loss(move):
    result = greeks.taylor_pnl(0, -10000, 0, move, 0)
    assert result["total"] == pytest.approx(-20000)


def test_source_gamma_neutral_2000_options_and_1240_shares_sold():
    result = greeks.gamma_delta_hedge(0, -3000, 0.62, 1.5)
    assert [result["option_quantity"], result["stock_quantity"]] == pytest.approx([2000, -1240])
    assert [result["delta_residual"], result["gamma_residual"]] == pytest.approx([0, 0], abs=1e-12)
    # Independent equations for a book with a pre-existing delta.
    other = greeks.gamma_delta_hedge(-700, 2300, -0.4, 0.23)
    assert 2300 + 0.23 * other["option_quantity"] == pytest.approx(0, abs=1e-12)
    assert -700 - 0.4 * other["option_quantity"] + other["stock_quantity"] == pytest.approx(
        0, abs=1e-12
    )


def test_example_19_4_gamma_0066():
    assert bsm.gamma(49, 50, 0.05, 0.2, 0.3846) == pytest.approx(0.066, abs=0.0005)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_gamma_against_independent_terminal_payoff_density_second_difference(kind):
    step = 0.01
    reference = (
        density(49 + step, kind) - 2 * density(49, kind) + density(49 - step, kind)
    ) / step**2
    assert bsm.gamma(49, 50, 0.05, 0.2, 0.3846) == pytest.approx(reference, abs=3e-8)


def test_delta_hedged_price_error_has_quadratic_term_and_cubic_remainder():
    delta = float(bsm.call_delta(49, 50, 0.05, 0.2, 0.3846))
    gamma = float(bsm.gamma(49, 50, 0.05, 0.2, 0.3846))
    errors = []
    for move in [0.4, 0.2, 0.1]:
        exact = density(49 + move, "call") - density(49, "call") - delta * move
        predicted = greeks.taylor_pnl(0, gamma, 0, move, 0)["total"]
        assert exact > 0
        errors.append(abs(exact - predicted))
    assert errors[0] / errors[1] > 6
    assert errors[1] / errors[2] > 6


def test_zero_gamma_instrument_cannot_change_portfolio_gamma():
    with pytest.raises(ValueError):
        greeks.gamma_delta_hedge(0, -3000, 1, 0)
