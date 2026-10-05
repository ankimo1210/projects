"""Hull GE 14.8: fBM level covariance, memory and dense Gaussian paths."""

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from hullkit.weather import fractional_noise_autocovariance
from scipy.linalg import toeplitz


@pytest.mark.parametrize("hurst,derived_correlation", [(.9, .9330), (.5, .7071), (.1, .5359)])
def test_source_covariance_14_20_against_independent_integrated_fgn(hurst, derived_correlation):
    times = np.arange(1, 101)/100
    covariance = stochastic.fractional_brownian_covariance(times[:, None], times[None, :], hurst)
    increments = toeplitz(fractional_noise_autocovariance(100, hurst))*.01**(2*hurst)
    independent = increments.cumsum(axis=0).cumsum(axis=1)
    assert np.allclose(covariance, independent, atol=1e-12, rtol=0)
    assert stochastic.fractional_brownian_correlation(.5, 1, hurst) == pytest.approx(derived_correlation, abs=.00005)
    assert np.diag(covariance) == pytest.approx(times**(2*hurst), abs=1e-12)
    if hurst == .5:
        assert np.allclose(covariance, np.minimum(times[:, None], times[None, :]), atol=1e-12, rtol=0)


@pytest.mark.parametrize("hurst", [.9, .5, .1])
def test_figure_14_3_cholesky_paths_and_independent_spectral_fgn_mc(hurst):
    n, steps, dt = 15000, 100, .01
    times = np.arange(steps+1)*dt
    paths = stochastic.fractional_brownian_paths(times, hurst, n, rng=np.random.default_rng(148))
    fgn_covariance = toeplitz(fractional_noise_autocovariance(steps, hurst))*dt**(2*hurst)
    eigenvalues, eigenvectors = np.linalg.eigh(fgn_covariance)
    assert eigenvalues.min() > 0
    # Independent spectral sampling of increments, then accumulation to levels.
    factor = eigenvectors*np.sqrt(eigenvalues)
    noise = np.random.default_rng(14801).standard_normal((n, steps)) @ factor.T
    independent_paths = np.column_stack((np.zeros(n), noise.cumsum(axis=1)))
    indices = [25, 50, 100]
    expected = stochastic.fractional_brownian_covariance(times[indices, None], times[None, indices], hurst)
    se = np.sqrt((np.outer(np.diag(expected), np.diag(expected))+expected**2)/(n-1))
    for sample in [paths, independent_paths]:
        observed = np.cov(sample[:, indices], rowvar=False)
        assert np.all(np.abs(observed-expected) < 6*se)
    # Only the first adjacent pair per independent path is used for the SE.
    changes = np.diff(paths[:, :3], axis=1)
    increment_target = fgn_covariance[:2, :2]
    increment_se = np.sqrt((np.outer(np.diag(increment_target), np.diag(increment_target))+increment_target**2)/(n-1))
    assert np.all(np.abs(np.cov(changes, rowvar=False)-increment_target) < 6*increment_se)
    assert increment_target[0, 1]/increment_target[0, 0] == pytest.approx(2**(2*hurst-1)-1, abs=1e-12)
    assert np.allclose(paths[:, 0], 0, atol=1e-12, rtol=0)


def test_gaussian_conditional_covariance_distinguishes_markov_property():
    for hurst in [.9, .5, .1]:
        cov = stochastic.fractional_brownian_covariance(np.array([.25, .5, 1])[:, None], np.array([.25, .5, 1])[None, :], hurst)
        conditional = cov[0, 2]-cov[0, 1]*cov[1, 2]/cov[1, 1]
        if hurst == .5:
            assert conditional == pytest.approx(0, abs=1e-12)
        else:
            assert abs(conditional) > 1e-4


def test_correlation_at_zero_and_invalid_hurst_or_time_are_rejected():
    with pytest.raises(ValueError):
        stochastic.fractional_brownian_correlation(0, 1, .5)
    for s, hurst in [(1, 1), (-1, .5)]:
        with pytest.raises(ValueError):
            stochastic.fractional_brownian_covariance(s, 1, hurst)
