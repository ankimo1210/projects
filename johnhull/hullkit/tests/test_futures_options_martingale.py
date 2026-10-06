"""Hull 18.6 martingale law, settlement expectation and futures PDE."""
import math

import numpy as np
import pytest
from hullkit import _futures_options as futures
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("current", [70, 100, 130])
def test_conditional_mean_and_zero_settlement_against_density(current):
    law = futures.futures_risk_neutral_law(current, .25, .4)
    width = math.sqrt(law["log_variance"])
    mean = quad(lambda z: math.exp(law["log_mean"]+width*z)*norm.pdf(z), -12, 12, epsabs=1e-10)[0]
    assert [mean, law["mean"]] == pytest.approx([current, current], abs=1e-10)
    assert math.exp(-.05*.4)*(mean-current) == pytest.approx(0, abs=1e-10)
    assert law["log_mean"]-math.log(current) == pytest.approx(-.25**2*.4/2)


def test_crr_transition_conditional_mean_is_one_not_exp_rate():
    result = futures.futures_tree_transition(100, .05, .25, .1)
    p = result["probability"]
    assert p == pytest.approx((1-result["down"])/(result["up"]-result["down"]), abs=1e-14)
    assert p*result["up"]+(1-p)*result["down"] == pytest.approx(1, abs=1e-14)
    assert result["discounted_settlement_mean"] == pytest.approx(0, abs=1e-12)
    assert p*result["up"]+(1-p)*result["down"] < math.exp(.05*.1)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_futures_pde_using_independent_finite_differences(kind):
    def price(f, time):
        return futures.black_details(f, 105, .05, .25, time)[kind]
    forward, time, hf, ht = 100, .8, .01, 1e-5
    value = price(forward, time)
    gamma = (price(forward+hf, time)-2*value+price(forward-hf, time))/hf**2
    theta = -(price(forward, time+ht)-price(forward, time-ht))/(2*ht)
    assert futures.futures_pde_residual(forward, .05, .25, value, theta, gamma) == pytest.approx(0, abs=3e-6)


def test_zero_drift_law_against_independent_stock_euler_fixed_seed_mc():
    rng = np.random.default_rng(1806)
    count, steps, time, sigma, initial = 40000, 128, .8, .25, 100
    samples = np.full(count, initial, dtype=float)
    dt = time/steps
    for _ in range(steps):
        samples *= 1+sigma*math.sqrt(dt)*rng.standard_normal(count)
    assert np.min(samples) > 0
    law = futures.futures_risk_neutral_law(initial, sigma, time)
    assert abs(samples.mean()-law["mean"]) <= 6*samples.std(ddof=1)/math.sqrt(count)
    centered_square = (samples-initial)**2
    euler_variance = initial**2*math.expm1(steps*math.log1p(sigma**2*dt))
    variance_se = centered_square.std(ddof=1)/math.sqrt(count)
    assert abs(centered_square.mean()-euler_variance) <= 6*variance_se
    assert abs(centered_square.mean()-law["variance"]) <= 6*variance_se+abs(law["variance"]-euler_variance)


def test_zero_volatility_transition_is_deterministic_without_dividing_by_zero():
    result = futures.futures_tree_transition(100, .05, 0, .1)
    assert [result["up"], result["down"], result["discounted_settlement_mean"]] == pytest.approx([1, 1, 0])
    assert result["probability"] is None
