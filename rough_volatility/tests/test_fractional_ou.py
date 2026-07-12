"""Tests for ordinary and fractional OU log-volatility simulators."""

import numpy as np
from rough_volatility.estimators import hurst_variogram
from rough_volatility.fractional_ou import fou_euler, ou_exact


def test_exact_ou_stationary_moments_and_one_step_acf() -> None:
    kappa, sigma = 2.0, 0.8
    paths = ou_exact(
        kappa,
        mean=-1.0,
        sigma=sigma,
        x0=-1.0,
        n_steps=500,
        horizon=5.0,
        n_paths=20_000,
        rng=np.random.default_rng(50),
    )
    terminal = paths[:, -1]
    assert abs(terminal.mean() + 1.0) < 0.01
    assert abs(terminal.var(ddof=1) - sigma**2 / (2 * kappa)) < 0.01
    empirical = np.corrcoef(paths[:, -2], paths[:, -1])[0, 1]
    assert abs(empirical - np.exp(-kappa * 0.01)) < 0.01


def test_fractional_ou_zero_noise_mean_reverts() -> None:
    paths, _ = fou_euler(
        kappa=1.0,
        mean=2.0,
        nu=0.0,
        h=0.1,
        x0=-1.0,
        n_steps=50,
        horizon=1.0,
        n_paths=2,
        rng=np.random.default_rng(51),
    )
    assert np.all(np.diff(paths, axis=1) > 0)
    assert np.all(paths[:, -1] < 2.0)


def test_fractional_ou_has_local_hurst_scaling_and_positive_volatility() -> None:
    h = 0.10
    paths, diagnostics = fou_euler(
        kappa=2.0,
        mean=np.log(0.2),
        nu=0.4,
        h=h,
        x0=np.log(0.2),
        n_steps=16_384,
        horizon=4.0,
        n_paths=12,
        burn_in_steps=2048,
        rng=np.random.default_rng(52),
    )
    estimates = [hurst_variogram(path, lags=np.arange(1, 33)).h_hat for path in paths]
    assert abs(np.mean(estimates) - h) < 0.05
    assert np.all(np.isfinite(np.exp(paths)))
    assert np.all(np.exp(paths) > 0)
    assert diagnostics.method == "davies-harte"


def test_h_half_fractional_euler_matches_exact_ou_moments() -> None:
    kwargs = dict(
        kappa=1.5,
        mean=-0.4,
        x0=-0.4,
        n_steps=800,
        horizon=4.0,
        n_paths=12_000,
    )
    exact = ou_exact(sigma=0.7, rng=np.random.default_rng(53), **kwargs)
    fractional, _ = fou_euler(nu=0.7, h=0.5, rng=np.random.default_rng(54), **kwargs)
    assert abs(exact[:, -1].mean() - fractional[:, -1].mean()) < 0.015
    assert abs(exact[:, -1].var() - fractional[:, -1].var()) < 0.015


def test_fractional_ou_shape_and_reproducibility_with_burn_in() -> None:
    args = (2.0, 0.0, 0.3, 0.2, 0.0, 128, 1.0, 3)
    first, _ = fou_euler(*args, rng=np.random.default_rng(55), burn_in_steps=32)
    second, _ = fou_euler(*args, rng=np.random.default_rng(55), burn_in_steps=32)
    assert first.shape == (3, 129)
    np.testing.assert_array_equal(first, second)
