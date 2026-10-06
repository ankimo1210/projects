"""Hull GE appendix 15A: a general lognormal payoff and completed-square integrals."""

import math

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit._binomial_foundations import binomial_call_tails
from scipy.integrate import quad
from scipy.stats import lognorm


@pytest.mark.parametrize("mean,w,k", [(40, .2, 42), (120, .7, 80), (10, .05, 12)])
def test_general_source_identity_against_two_independent_integral_coordinates(mean, w, k):
    result = foundations.lognormal_call_moments(mean, w, k)
    m = math.log(mean)-w*w/2
    density = lognorm(s=w, scale=math.exp(m))
    direct = quad(lambda v: (v-k)*density.pdf(v), k, math.inf, epsabs=1e-10)[0]
    probability = quad(density.pdf, k, math.inf, epsabs=1e-11)[0]
    first = quad(lambda v: v*density.pdf(v), k, math.inf, epsabs=1e-10)[0]
    lower = (math.log(k)-m)/w
    # Combine density with the exponential before evaluation to avoid overflow.
    normal = quad(lambda z: (math.exp(m+w*z-z*z/2)-k*math.exp(-z*z/2))/math.sqrt(2*math.pi), lower, math.inf, epsabs=1e-10)[0]
    assert result["log_mean"] == pytest.approx(m, abs=1e-14)
    assert result["payoff_mean"] == pytest.approx(direct, abs=1e-8)
    assert result["payoff_mean"] == pytest.approx(normal, abs=1e-8)
    assert result["exercise_probability"] == pytest.approx(probability, abs=1e-10)
    assert result["truncated_mean"] == pytest.approx(first, abs=1e-8)
    assert result["conditional_mean"] == pytest.approx(first/probability, abs=1e-6)


@pytest.mark.parametrize("s,k,r,sigma,t", [(42, 40, .1, .2, .5), (40, 60, .03, .3, 5)])
def test_source_bsm_substitution_and_independent_binomial_limit(s, k, r, sigma, t):
    result = foundations.lognormal_call_moments(s*math.exp(r*t), sigma*math.sqrt(t), k)
    price = math.exp(-r*t)*result["payoff_mean"]
    assert price == pytest.approx(float(bsm.call_price(s, k, r, sigma, t)), abs=1e-12)
    tails = binomial_call_tails(s, k, r, sigma, t, 4000)
    assert price == pytest.approx(tails["price"], abs=.005)
    assert result["exercise_probability"] == pytest.approx(tails["cash_tail"], abs=.01)
    assert result["stock_weight"] == pytest.approx(tails["stock_tail"], abs=.01)


@pytest.mark.parametrize("mean", [30, 50])
def test_zero_log_sd_is_deterministic(mean):
    result = foundations.lognormal_call_moments(mean, 0, 40)
    assert result["payoff_mean"] == pytest.approx(max(mean-40, 0))
    assert result["exercise_probability"] == pytest.approx(float(mean > 40))


def test_zero_strike_expected_payoff_is_mean():
    assert foundations.lognormal_call_moments(40, .2, 0)["payoff_mean"] == pytest.approx(40)


def test_negative_log_sd_is_undefined():
    with pytest.raises(ValueError):
        foundations.lognormal_call_moments(40, -.1, 42)
