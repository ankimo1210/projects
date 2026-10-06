"""Hull 18.8 spot/forward coordinates and maturity-bond discount."""

import math

import pytest
from hullkit import _futures_options as futures
from scipy.integrate import quad
from scipy.stats import norm


def test_example_18_7_gold_price_d_values_and_discount_input():
    result = futures.black_from_discount(1240, 1200, math.exp(-0.05 * 0.5), 0.2, 0.5)
    assert result["call"] == pytest.approx(88.37, abs=0.005)
    assert result["call"] == pytest.approx(88.3737066, abs=5e-8)
    assert [result["d1"], result["d2"]] == pytest.approx([0.3026, 0.1611], abs=5e-5)


@pytest.mark.parametrize("yield_rate", [0, 0.03, 0.12])
def test_gold_forward_price_against_independent_spot_density(yield_rate):
    spot = 1240 * math.exp(-(0.05 - yield_rate) * 0.5)
    result = futures.spot_futures_equivalence(spot, 1200, 0.05, yield_rate, 0.2, 0.5)
    log_mean = math.log(spot) + (0.05 - yield_rate - 0.2**2 / 2) * 0.5
    width = 0.2 * math.sqrt(0.5)
    cutoff = (math.log(1200) - log_mean) / width
    value = (
        math.exp(-0.05 * 0.5)
        * quad(
            lambda z: (math.exp(log_mean + width * z) - 1200) * norm.pdf(z), cutoff, 12, epsabs=1e-9
        )[0]
    )
    assert result["futures_call"] == pytest.approx(value, abs=1e-9)
    assert result["spot_call"] == pytest.approx(value, abs=1e-9)


def test_explicit_maturity_bond_discount_against_forward_measure_integral():
    forward, strike, sigma, time, bond = 1240, 1200, 0.2, 0.5, 0.97
    width = sigma * math.sqrt(time)
    log_mean = math.log(forward) - width**2 / 2
    cutoff = (math.log(strike) - log_mean) / width
    call_expectation = quad(
        lambda z: (math.exp(log_mean + width * z) - strike) * norm.pdf(z), cutoff, 12, epsabs=1e-9
    )[0]
    put_expectation = quad(
        lambda z: (strike - math.exp(log_mean + width * z)) * norm.pdf(z), -12, cutoff, epsabs=1e-9
    )[0]
    result = futures.black_from_discount(forward, strike, bond, sigma, time)
    assert [result["call"], result["put"]] == pytest.approx(
        [bond * call_expectation, bond * put_expectation], abs=1e-9
    )
    assert result["call"] - result["put"] == pytest.approx(bond * (forward - strike), abs=1e-11)


def test_discount_factor_must_be_positive_and_one_at_expiry():
    with pytest.raises(ValueError):
        futures.black_from_discount(1240, 1200, 0, 0.2, 0.5)
    with pytest.raises(ValueError):
        futures.black_from_discount(1240, 1200, 0.97, 0.2, 0)
    assert futures.black_from_discount(1240, 1200, 1, 0.2, 0)["call"] == pytest.approx(40)
