"""Hull 19.1 sale valuation, quantities and risk-neutral pricing."""

import math

import pytest
from hullkit import _greeks_hedging as greeks
from scipy.integrate import quad
from scipy.stats import norm


def density_price(spot, strike, rate, drift, sigma, time, kind):
    width = sigma * math.sqrt(time)
    log_mean = math.log(spot) + (drift - sigma**2 / 2) * time
    cutoff = (math.log(strike) - log_mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(log_mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )


def test_source_running_example_theoretical_unit_total_and_sale_difference():
    result = greeks.sold_option_valuation(49, 50, 0.05, 0.2, 0.3846, 100000, 300000)
    assert result["unit_value"] == pytest.approx(2.40, abs=0.005)
    assert result["unit_value"] == pytest.approx(2.400461, abs=5e-7)
    assert 100000 * round(result["unit_value"], 2) == pytest.approx(240000)
    assert result["theoretical_value"] == pytest.approx(100000 * result["unit_value"], abs=1e-9)
    assert result["sale_difference"] == pytest.approx(60000, abs=50)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_valuation_against_independent_discounted_terminal_density(kind):
    result = greeks.sold_option_valuation(49, 50, 0.05, 0.2, 0.3846, 100000, 300000, kind=kind)
    reference = density_price(49, 50, 0.05, 0.05, 0.2, 0.3846, kind)
    assert result["unit_value"] == pytest.approx(reference, abs=1e-11)


def test_source_physical_drift_13_percent_is_not_used_for_risk_neutral_price():
    physical = density_price(49, 50, 0.05, 0.13, 0.2, 0.3846, "call")
    result = greeks.sold_option_valuation(49, 50, 0.05, 0.2, 0.3846, 100000, 300000)
    assert physical > result["unit_value"] + 0.5


def test_positive_number_of_underlying_units_is_required():
    with pytest.raises(ValueError):
        greeks.sold_option_valuation(49, 50, 0.05, 0.2, 0.3846, 0, 300000)
