"""Hull GE 14.5: correlation construction and independent covariance laws."""

import math

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic


@pytest.mark.parametrize("rho", [-1, -.75, 0, .6, 1])
def test_source_correlation_equation_including_singular_endpoints(rho):
    n, dt = 50000, .2
    normals = np.random.default_rng(145).standard_normal((n, 2))
    increments = stochastic.correlated_wiener_increments(normals, rho, dt)
    covariance = dt*np.array([[1, rho], [rho, 1]])
    observed = np.cov(increments, rowvar=False)
    # Independent Gaussian/Wishart covariance standard errors.
    se = np.sqrt((np.outer(np.diag(covariance), np.diag(covariance))+covariance**2)/(n-1))
    assert np.all(np.abs(observed-covariance) < 6*se)
    assert np.all(np.abs(increments.mean(axis=0)) < 6*math.sqrt(dt/n))
    if abs(rho) < 1:
        # Independent Cholesky factorization recovers the same noise transform.
        independent = normals @ np.linalg.cholesky(covariance).T
        assert np.allclose(increments, independent, atol=1e-12, rtol=0)
    else:
        assert np.allclose(increments[:, 1], rho*increments[:, 0], atol=1e-12, rtol=0)


def test_zero_time_and_invalid_covariance_parameters():
    assert stochastic.correlated_wiener_increments([[1, 2]], .4, 0) == pytest.approx(np.zeros((1, 2)), abs=1e-12)
    for rho, dt in [(1.01, 1), (.4, -1)]:
        with pytest.raises(ValueError):
            stochastic.correlated_wiener_increments([[1, 2]], rho, dt)
