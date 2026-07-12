"""Statistical and deterministic tests for fractional Brownian motion."""

import numpy as np
import pytest
from rough_volatility.fbm import (
    cholesky_fgn,
    davies_harte_fgn,
    fbm_paths,
    fgn_autocovariance,
)


def test_h_half_has_white_noise_covariance() -> None:
    gamma = fgn_autocovariance(0.5, 12)
    np.testing.assert_allclose(gamma, np.r_[1.0, np.zeros(12)], atol=1e-14)


@pytest.mark.parametrize("h", [0.1, 0.5, 0.8])
def test_davies_harte_embedding_is_nonnegative(h: float) -> None:
    draws, diagnostics = davies_harte_fgn(h, 1024, 4, np.random.default_rng(10))
    assert draws.shape == (4, 1024)
    assert diagnostics.min_eigenvalue >= -1e-10 * diagnostics.max_eigenvalue
    assert diagnostics.clipped_mass >= 0


def test_davies_harte_empirical_increment_covariance() -> None:
    h = 0.10
    draws, _ = davies_harte_fgn(h, 32, 8000, np.random.default_rng(11))
    expected = fgn_autocovariance(h, 2)
    assert abs(draws[:, 0].var(ddof=1) - expected[0]) < 0.04
    assert abs(np.cov(draws[:, 0], draws[:, 1], ddof=1)[0, 1] - expected[1]) < 0.04
    assert abs(np.cov(draws[:, 0], draws[:, 2], ddof=1)[0, 1] - expected[2]) < 0.04


def test_fbm_shape_start_reproducibility_and_horizon_scaling() -> None:
    first = fbm_paths(0.25, 64, 5000, 2.0, np.random.default_rng(12))
    second = fbm_paths(0.25, 64, 5000, 2.0, np.random.default_rng(12))
    assert first.times.shape == (65,)
    assert first.paths.shape == (5000, 65)
    np.testing.assert_array_equal(first.paths, second.paths)
    np.testing.assert_array_equal(first.paths[:, 0], 0.0)
    assert abs(first.paths[:, -1].var(ddof=1) - 2.0**0.5) < 0.08


def test_davies_harte_and_cholesky_agree_on_low_order_moments() -> None:
    h, n, n_paths = 0.30, 24, 12_000
    dh, _ = davies_harte_fgn(h, n, n_paths, np.random.default_rng(20))
    chol = cholesky_fgn(h, n, n_paths, np.random.default_rng(21))
    assert abs(dh.var() - chol.var()) < 0.035
    assert abs(np.cov(dh[:, 0], dh[:, 1])[0, 1] - np.cov(chol[:, 0], chol[:, 1])[0, 1]) < 0.035


@pytest.mark.parametrize("h", [0.0, 1.0, -0.1])
def test_invalid_hurst_rejected(h: float) -> None:
    with pytest.raises(ValueError, match="Hurst"):
        fbm_paths(h, 16, 2, 1.0, np.random.default_rng(1))


def test_invalid_sizes_rejected() -> None:
    with pytest.raises(ValueError):
        davies_harte_fgn(0.1, 0, 1, np.random.default_rng(1))
