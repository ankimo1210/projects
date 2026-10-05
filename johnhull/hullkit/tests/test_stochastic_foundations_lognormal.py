"""Hull GE 14.7: lognormal law independently checked with stock Euler paths."""

import math

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from hullkit.sde import euler_maruyama
from scipy.stats import norm


@pytest.fixture(scope="module")
def stock_euler_logs():
    # Generate dS = mu*S*dt + sigma*S*dW, never exponentiating log increments.
    samples = []
    for steps, seed in [(8, 1478), (512, 147512)]:
        paths = euler_maruyama(lambda x, t: .05*x, lambda x, t: .5*x, 100, 1, steps, 20000, rng=np.random.default_rng(seed))
        assert np.all(paths[:, -1] > 0)  # No truncation/censoring of negative Euler states.
        samples.append(np.log(paths[:, -1]))
    return samples


def test_source_log_law_14_17_to_14_19_and_gaussian_exponential_moments():
    law = stochastic.gbm_log_law(100, .05, .5, 1)
    assert law["log_mean"] == pytest.approx(math.log(100)+.05-.5**2/2, abs=1e-12)
    assert law["log_variance"] == pytest.approx(.5**2, abs=1e-12)
    # Independent Gaussian moment generating function, evaluated at 1 and 2.
    first = math.exp(law["log_mean"]+law["log_variance"]/2)
    second = math.exp(2*law["log_mean"]+2*law["log_variance"])
    assert law["mean"] == pytest.approx(first, abs=1e-10)
    assert law["variance"] == pytest.approx(second-first**2, abs=1e-9)


def test_fine_stock_euler_log_moments_and_cdf_coverage_with_mc_standard_errors(stock_euler_logs):
    fine = stock_euler_logs[1]
    law = stochastic.gbm_log_law(100, .05, .5, 1)
    n = len(fine)
    assert abs(fine.mean()-law["log_mean"]) < 6*fine.std(ddof=1)/math.sqrt(n)
    squares = (fine-law["log_mean"])**2
    assert abs(squares.mean()-law["log_variance"]) < 6*squares.std(ddof=1)/math.sqrt(n)
    for p in [.1, .5, .9]:
        quantile = law["log_mean"]+math.sqrt(law["log_variance"])*norm.ppf(p)
        assert abs(np.mean(fine <= quantile)-p) < 6*math.sqrt(p*(1-p)/n)


def test_refinement_reduces_euler_log_variance_error_without_assuming_exact_finite_law(stock_euler_logs):
    coarse, fine = stock_euler_logs
    assert abs(fine.var(ddof=1)-.25) < abs(coarse.var(ddof=1)-.25)/2
    # Zero time is a point mass; the law still has a well-defined moment limit.
    law = stochastic.gbm_log_law(100, .05, .5, 0)
    assert [law["mean"], law["variance"], law["log_variance"]] == pytest.approx([100, 0, 0], abs=1e-12)
