"""Hull 20.6: conditional IV response, not a cross-sectional smile slope."""

import math

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from scipy.integrate import quad
from scipy.stats import norm


def density_price(spot, strike, rate, yield_rate, sigma, time, kind):
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
            epsabs=1e-14,
        )[0]
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_textbook_negative_conditional_iv_response_lowers_delta(kind):
    result = smile.minimum_variance_delta(49, 50, 0.05, 0, 0.2, 0.3846, -0.001, kind=kind)
    assert result["vega_correction"] == pytest.approx(-0.01210524275, abs=1e-10)
    assert result["minimum_variance_delta"] == pytest.approx(
        result["bsm_delta"] + result["vega_correction"], abs=1e-12
    )
    assert result["minimum_variance_delta"] < result["bsm_delta"]


@pytest.mark.parametrize("kind", ["call", "put"])
def test_zero_conditional_response_recovers_fixed_iv_delta(kind):
    result = smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, 0, kind=kind)
    assert result["minimum_variance_delta"] == pytest.approx(result["bsm_delta"], abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_chain_rule_against_independent_full_payoff_repricing_with_sigma_of_spot(kind):
    ds, response = 0.001, -0.001
    up = density_price(49 + ds, 50, 0.05, 0.03, 0.2 + response * ds, 0.3846, kind)
    down = density_price(49 - ds, 50, 0.05, 0.03, 0.2 - response * ds, 0.3846, kind)
    result = smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, response, kind=kind)
    assert result["minimum_variance_delta"] == pytest.approx((up - down) / (2 * ds), abs=2e-9)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_first_order_two_factor_distribution_direct_covariance_minimum(kind):
    result = smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, -0.001, kind=kind)
    ds = np.array([-0.1, -0.1, 0.1, 0.1])
    independent_iv_noise = np.array([-0.002, 0.002, -0.002, 0.002])
    div = -0.001 * ds + independent_iv_noise
    dv = result["bsm_delta"] * ds + result["vega"] * div
    direct = np.dot(ds - ds.mean(), dv - dv.mean()) / np.dot(ds - ds.mean(), ds - ds.mean())
    assert result["minimum_variance_delta"] == pytest.approx(direct, abs=1e-12)

    def variance(hedge):
        return np.var(dv - hedge * ds)

    optimum = result["minimum_variance_delta"]
    assert variance(optimum) < variance(result["bsm_delta"])
    assert variance(optimum) < variance(optimum - 0.02)
    assert variance(optimum) < variance(optimum + 0.02)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_exact_two_factor_repricing_covariance_converges_to_local_formula(kind):
    result = smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, -0.001, kind=kind)
    errors = []
    base = density_price(49, 50, 0.05, 0.03, 0.2, 0.3846, kind)
    for scale in [1, 0.5, 0.25]:
        ds = scale * np.array([-0.2, -0.2, 0.2, 0.2])
        noise = scale * np.array([-0.004, 0.004, -0.004, 0.004])
        changes = np.array(
            [
                density_price(49 + x, 50, 0.05, 0.03, 0.2 - 0.001 * x + eta, 0.3846, kind) - base
                for x, eta in zip(ds, noise, strict=True)
            ]
        )
        covariance_hedge = np.dot(ds, changes - changes.mean()) / np.dot(ds, ds)
        errors.append(abs(covariance_hedge - result["minimum_variance_delta"]))
        assert np.var(changes - result["minimum_variance_delta"] * ds) < np.var(
            changes - result["bsm_delta"] * ds
        )
    assert errors[0] / errors[1] > 3.5 and errors[1] / errors[2] > 3.5
    assert errors[-1] < 1e-5


def test_price_unit_rescaling_also_rescales_response_per_spot_unit():
    a = smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, -0.001)
    b = smile.minimum_variance_delta(4900, 5000, 0.05, 0.03, 0.2, 0.3846, -0.00001)
    assert a["minimum_variance_delta"] == pytest.approx(b["minimum_variance_delta"], abs=1e-12)


def test_nonfinite_conditional_response_is_undefined():
    with pytest.raises(ValueError):
        smile.minimum_variance_delta(49, 50, 0.05, 0.03, 0.2, 0.3846, math.nan)
