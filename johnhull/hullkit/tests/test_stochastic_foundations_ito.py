"""Hull GE 14.6: local Ito coefficients and the no-dividend forward."""

import math

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from hullkit.mc import simulate_gbm_paths
from scipy.integrate import quad
from scipy.stats import norm


def test_source_ito_formula_against_independent_gaussian_increment_integral():
    x, a, b, dt = 3, .4, 1.2, 1e-5
    drift, diffusion = stochastic.ito_coefficients(a, b, 0, 2*x, 2)
    expected_change = quad(lambda z: ((x+a*dt+b*math.sqrt(dt)*z)**2-x*x)*norm.pdf(z), -10, 10, epsabs=1e-12)[0]
    assert drift == pytest.approx(expected_change/dt, abs=3e-6)
    assert diffusion == pytest.approx(2*x*b, abs=1e-12)
    # The time partial contributes separately and ln(x) has a nonzero correction.
    log_drift, log_diffusion = stochastic.ito_coefficients(.15*x, .3*x, .2, 1/x, -1/x**2)
    assert [log_drift, log_diffusion] == pytest.approx([.15-.3**2/2+.2, .3], abs=1e-12)


def test_source_forward_equations_14_15_and_14_16_via_independent_path_transform():
    spot, mu, sigma, rate, expiry, n = 100, .15, .3, .04, .5, 30000
    result = stochastic.forward_ito(spot, mu, sigma, rate, 0, expiry)
    initial_forward = spot*math.exp(rate*expiry)
    assert result["forward"] == pytest.approx(initial_forward, abs=1e-12)
    assert result["drift"] == pytest.approx((mu-rate)*initial_forward, abs=1e-12)
    assert result["diffusion"] == pytest.approx(sigma*initial_forward, abs=1e-12)
    paths = simulate_gbm_paths(spot, mu, sigma, expiry, 10, n, rng=np.random.default_rng(146))
    times = np.linspace(0, expiry, 11)
    forwards = paths*np.exp(rate*(expiry-times))
    assert np.allclose(forwards[:, -1], paths[:, -1], atol=1e-12, rtol=0)
    increments = np.diff(np.log(forwards), axis=1).ravel()
    dt = expiry/10
    target_mean = result["log_drift"]*dt
    assert abs(increments.mean()-target_mean) < 6*increments.std(ddof=1)/math.sqrt(len(increments))
    assert abs(increments.var(ddof=1)-sigma**2*dt) < 6*sigma**2*dt*math.sqrt(2/(len(increments)-1))
    target_terminal = initial_forward*math.exp((mu-rate)*expiry)
    assert abs(forwards[:, -1].mean()-target_terminal) < 6*forwards[:, -1].std(ddof=1)/math.sqrt(n)


def test_risk_neutral_forward_drift_zero_but_log_drift_has_ito_correction():
    result = stochastic.forward_ito(100, .04, .3, .04, .2, 1)
    assert result["drift"] == pytest.approx(0, abs=1e-12)
    assert result["log_drift"] == pytest.approx(-.3**2/2, abs=1e-12)
    with pytest.raises(ValueError):
        stochastic.forward_ito(100, .04, .3, .04, 2, 1)
