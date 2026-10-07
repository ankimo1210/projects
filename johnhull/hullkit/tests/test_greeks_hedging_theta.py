"""Hull 19.5: calendar theta, daily units and independent terminal-density changes."""

import math

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


def test_example_19_2_annual_calendar_and_trading_units():
    result = greeks.theta_units(49, 50, 0.05, 0.2, 0.3846)
    assert result["annual"] == pytest.approx(-4.31, abs=0.005)
    assert result["per_calendar_day"] == pytest.approx(-0.0118, abs=0.00005)
    assert result["per_trading_day"] == pytest.approx(-0.0171, abs=0.00005)
    assert result["annual"] == pytest.approx(result["per_calendar_day"] * 365, abs=1e-12)
    assert result["annual"] == pytest.approx(result["per_trading_day"] * 252, abs=1e-12)


@pytest.mark.parametrize(
    "spot,kind,yield_rate", [(49, "call", 0), (49, "put", 0), (20, "put", 0), (100, "call", 0.3)]
)
def test_theta_is_negative_remaining_time_derivative_of_independent_density(spot, kind, yield_rate):
    time, step = 0.3846, 1e-5
    value = greeks.theta_units(spot, 50, 0.05, 0.2, time, kind=kind, yield_rate=yield_rate)[
        "annual"
    ]
    reference = -(
        density(spot, 50, 0.05, 0.2, time + step, kind, yield_rate)
        - density(spot, 50, 0.05, 0.2, time - step, kind, yield_rate)
    ) / (2 * step)
    assert value == pytest.approx(reference, abs=2e-8)
    if spot == 20 or yield_rate == 0.3:
        assert value > 0


def test_call_put_theta_difference_and_nondividend_call_sign():
    call = greeks.theta_units(49, 50, 0.05, 0.2, 0.3846)["annual"]
    put = greeks.theta_units(49, 50, 0.05, 0.2, 0.3846, kind="put")["annual"]
    assert put - call == pytest.approx(0.05 * 50 * math.exp(-0.05 * 0.3846), abs=1e-12)
    assert call < 0


def test_greek_diffusive_formula_requires_positive_time_and_volatility():
    for sigma, time in [(0, 0.4), (0.2, 0), (0.2, -1)]:
        with pytest.raises(ValueError):
            greeks.theta_units(49, 50, 0.05, sigma, time)
