"""Hull 19.8: vega units and gamma/vega hedge equations."""

import math
from fractions import Fraction

import pytest
from hullkit import _greeks_hedging as greeks
from scipy.integrate import quad
from scipy.stats import norm


def density(spot, strike, rate, sigma, time, kind, yield_rate=0):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
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


def test_example_19_5_vega_only_and_residual_gamma():
    result = greeks.vega_delta_hedge(0, -5000, -8000, 0.6, 0.5, 2)
    assert [
        result["option_quantity"],
        result["stock_quantity"],
        result["gamma_after"],
    ] == pytest.approx([4000, -2400, -3000])
    assert result["vega_residual"] == pytest.approx(0, abs=1e-12)


def test_example_19_5_gamma_vega_and_delta_neutral_positions():
    result = greeks.gamma_vega_delta_hedge(0, -5000, -8000, [0.6, 0.5], [0.5, 0.8], [2, 1.2])
    assert result["option_quantities"] == pytest.approx([400, 6000], abs=1e-10)
    assert result["stock_quantity"] == pytest.approx(-3240, abs=1e-10)
    assert result["residuals"] == pytest.approx([0, 0, 0], abs=1e-10)


def test_hedge_weights_against_independent_exact_rational_elimination():
    a, b, c, d = Fraction(1, 2), Fraction(4, 5), Fraction(2), Fraction(6, 5)
    denominator = a * d - b * c
    w1 = (5000 * d - b * 8000) / denominator
    w2 = (a * 8000 - c * 5000) / denominator
    result = greeks.gamma_vega_delta_hedge(0, -5000, -8000, [0.6, 0.5], [0.5, 0.8], [2, 1.2])
    assert result["option_quantities"] == pytest.approx([float(w1), float(w2)], abs=1e-10)


def test_example_19_6_vega_per_unit_and_volatility_point():
    result = greeks.vega_units(49, 50, 0.05, 0.2, 0.3846)
    assert result["per_unit_volatility"] == pytest.approx(12.1, abs=0.05)
    assert result["per_volatility_point"] == pytest.approx(0.121, abs=0.0005)
    assert result["per_volatility_point"] * 100 == pytest.approx(
        result["per_unit_volatility"], abs=1e-12
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_vega_against_independent_density_volatility_difference(kind):
    step = 1e-5
    reference = (
        density(49, 50, 0.05, 0.2 + step, 0.3846, kind)
        - density(49, 50, 0.05, 0.2 - step, 0.3846, kind)
    ) / (2 * step)
    assert greeks.vega_units(49, 50, 0.05, 0.2, 0.3846)["per_unit_volatility"] == pytest.approx(
        reference, abs=2e-8
    )


def test_vega_first_order_error_shrinks_quadratically_under_parallel_iv_shift():
    vega = greeks.vega_units(49, 50, 0.05, 0.2, 0.3846)["per_unit_volatility"]
    errors = []
    for shock in [0.01, 0.005, 0.0025]:
        exact = density(49, 50, 0.05, 0.2 + shock, 0.3846, "call") - density(
            49, 50, 0.05, 0.2, 0.3846, "call"
        )
        errors.append(abs(exact - vega * shock))
    assert errors[0] / errors[1] > 3.5
    assert errors[1] / errors[2] > 3.5


def test_zero_vega_and_singular_pair_cannot_neutralize_exposure():
    with pytest.raises(ValueError):
        greeks.vega_delta_hedge(0, -1, -1, 0.6, 0.5, 0)
    with pytest.raises(ValueError):
        greeks.gamma_vega_delta_hedge(0, -1, -1, [0.6, 0.5], [1, 2], [2, 4])
