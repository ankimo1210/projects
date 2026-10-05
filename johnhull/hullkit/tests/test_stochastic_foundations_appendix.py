"""Hull GE 14 appendix: quadratic variation and multivariable Ito terms."""

import math

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from hullkit.sde import brownian_paths, quadratic_variation
from scipy.stats import chi2


@pytest.mark.parametrize("steps", [16, 256])
def test_source_squared_normal_moments_and_accumulated_qv_with_mc_se(steps):
    maturity, diffusion, n = 2, 1.4, 12000
    mean, variance = stochastic.brownian_quadratic_variation_moments(maturity, steps, diffusion)
    # Independent scaled chi-square law, not a substitution epsilon^2 == 1.
    chi_mean, chi_variance = chi2.stats(steps, moments="mv")
    scale = diffusion**2*maturity/steps
    assert [mean, variance] == pytest.approx([scale*chi_mean, scale**2*chi_variance], abs=1e-12)
    assert chi2.stats(1, moments="mv") == pytest.approx([1, 2], abs=1e-12)
    values = diffusion**2*quadratic_variation(brownian_paths(maturity, steps, n, rng=np.random.default_rng(14_337+steps)))
    assert abs(values.mean()-mean) < 6*math.sqrt(variance/n)
    squares = (values-mean)**2
    assert abs(squares.mean()-variance) < 6*squares.std(ddof=1)/math.sqrt(n)
    assert variance == pytest.approx(2*diffusion**4*maturity*(maturity/steps), abs=1e-12)


@pytest.mark.parametrize("rho", [-.6, 0, .6])
def test_source_multivariable_product_ito_term_with_independent_gaussian_mc(rho):
    s1, s2, mu1, mu2, sigma1, sigma2, maturity = 100, 80, .1, .07, .2, .35, .5
    correlation = np.array([[1, rho], [rho, 1]])
    drift, loading = stochastic.multivariate_ito_coefficients(
        [mu1*s1, mu2*s2], [[sigma1*s1, 0], [0, sigma2*s2]], 0,
        [s2, s1], [[0, 1], [1, 0]], driver_covariance=correlation)
    rate = mu1+mu2+rho*sigma1*sigma2
    assert drift == pytest.approx(rate*s1*s2, abs=1e-12)
    assert loading == pytest.approx([sigma1*s1*s2, sigma2*s1*s2], abs=1e-12)
    # Independent library Gaussian sampling, followed by exact stock endpoints.
    noise = np.random.default_rng(14_310).multivariate_normal([0, 0], maturity*correlation, size=60000)
    first = s1*np.exp((mu1-sigma1**2/2)*maturity+sigma1*noise[:, 0])
    second = s2*np.exp((mu2-sigma2**2/2)*maturity+sigma2*noise[:, 1])
    products = first*second
    expected = s1*s2*math.exp(rate*maturity)
    assert abs(products.mean()-expected) < 6*products.std(ddof=1)/math.sqrt(len(products))


def test_source_one_state_multiple_drivers_matches_equivalent_single_variance():
    x, rho = 100, .4
    a = .12*x
    b = np.array([.2*x, .3*x])
    correlation = np.array([[1, rho], [rho, 1]])
    drift, loading = stochastic.multivariate_ito_coefficients([a], [b], 0, [1/x], [[-1/x**2]], driver_covariance=correlation)
    variance_rate = b @ correlation @ b
    independent = stochastic.ito_coefficients(a, math.sqrt(variance_rate), 0, 1/x, -1/x**2)
    assert drift == pytest.approx(independent[0], abs=1e-12)
    assert loading == pytest.approx([.2, .3], abs=1e-12)
    with pytest.raises(ValueError):
        stochastic.multivariate_ito_coefficients([a], [b], 0, [1/x], [[-1/x**2]], driver_covariance=[[1, 2], [2, 1]])
