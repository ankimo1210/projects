"""Hull 18.7 Black example, density reference and futures-tree convergence."""

import math

import pytest
from hullkit import _futures_options as futures
from hullkit.trees import crr_price
from scipy.integrate import quad
from scipy.stats import norm


def test_example_18_6_black_put_printed_values_and_d_truncation():
    result = futures.black_details(20, 20, 0.09, 0.25, 4 / 12)
    assert result["put"] == pytest.approx(1.12, abs=0.005)
    assert result["put"] == pytest.approx(1.116641457, abs=5e-10)
    assert result["d1"] == pytest.approx(0.072168784, abs=5e-10)
    assert math.trunc(result["d1"] * 100000) / 100000 == pytest.approx(0.07216)
    assert result["d2"] == pytest.approx(-result["d1"], abs=1e-14)
    assert [1 - result["N_d1"], 1 - result["N_d2"]] == pytest.approx([0.4712, 0.5288], abs=5e-5)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_black_against_independent_lognormal_payoff_integral(kind):
    forward, strike, rate, sigma, time = 24, 20, 0.09, 0.25, 4 / 12
    width = sigma * math.sqrt(time)
    log_mean = math.log(forward) - width**2 / 2
    cutoff = (math.log(strike) - log_mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    value = (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(log_mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )
    assert futures.black_details(forward, strike, rate, sigma, time)[kind] == pytest.approx(
        value, abs=1e-11
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_source_black_against_independent_futures_crr(kind):
    price = futures.black_details(20, 20, 0.09, 0.25, 4 / 12)[kind]
    reference = crr_price(20, 20, 0.09, 0.25, 4 / 12, 1600, q=0.09, kind=kind)
    assert price == pytest.approx(reference, abs=0.0003)


@pytest.mark.parametrize("sigma,time", [(0, 0.5), (0.25, 0)])
def test_black_boundaries_are_discounted_deterministic_payoff(sigma, time):
    result = futures.black_details(24, 20, 0.09, sigma, time)
    assert [result["call"], result["put"]] == pytest.approx([4 * math.exp(-0.09 * time), 0])


def test_black_lognormal_model_rejects_nonpositive_forward():
    with pytest.raises(ValueError):
        futures.black_details(-20, 20, 0.09, 0.25, 4 / 12)
