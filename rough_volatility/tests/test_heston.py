"""Tests for the full-truncation Heston benchmark and CRN wiring."""

from dataclasses import replace

import numpy as np
import pytest
from rough_volatility.config import BergomiConfig, HestonConfig
from rough_volatility.heston import expected_variance, simulate_given_normals
from rough_volatility.option_pricing import smile_from_terminals
from rough_volatility.rough_bergomi import (
    build_operators,
)
from rough_volatility.rough_bergomi import (
    simulate_given_normals as simulate_bergomi_given_normals,
)


def test_expected_variance_formula() -> None:
    config = HestonConfig(v0=0.09, theta=0.04, kappa=2.0)
    times = np.array([0.0, 0.5, 1.0])
    expected = 0.04 + 0.05 * np.exp(-2.0 * times)
    np.testing.assert_allclose(expected_variance(config, times), expected)


def test_heston_shapes_positivity_and_reproducibility() -> None:
    config = HestonConfig()
    times = np.linspace(1 / 100, 1.0, 100)
    rng = np.random.default_rng(80)
    z = rng.standard_normal((2000, 100))
    z_perp = rng.standard_normal((2000, 100))
    first = simulate_given_normals(config, 100.0, 0.0, times, z, z_perp)
    second = simulate_given_normals(config, 100.0, 0.0, times, z, z_perp)
    assert first.s.shape == (2000, 101)
    assert first.v.shape == first.s.shape
    assert first.driver.shape == z.shape
    assert np.all(first.v >= 0)
    np.testing.assert_array_equal(first.s, second.s)


def test_heston_and_bergomi_share_the_same_spot_driver() -> None:
    n_paths, n_steps = 10, 16
    rng = np.random.default_rng(81)
    z = rng.standard_normal((n_paths, n_steps))
    z_perp = rng.standard_normal((n_paths, n_steps))
    residual = rng.standard_normal((n_paths, n_steps))
    times = np.linspace(1 / n_steps, 1.0, n_steps)
    heston = simulate_given_normals(HestonConfig(), 100.0, 0.0, times, z, z_perp)
    bergomi_config = replace(BergomiConfig(), n_steps=n_steps, n_paths=n_paths, chunk_size=n_paths)
    bergomi = simulate_bergomi_given_normals(
        bergomi_config,
        build_operators(bergomi_config.h, times),
        z,
        z_perp,
        residual,
    )
    np.testing.assert_array_equal(heston.driver, bergomi.driver)


@pytest.mark.slow
def test_martingale_and_expected_variance_within_sampling_error() -> None:
    config = HestonConfig()
    n_paths, n_steps = 60_000, 500
    times = np.linspace(1 / n_steps, 1.0, n_steps)
    rng = np.random.default_rng(82)
    paths = simulate_given_normals(
        config,
        100.0,
        0.0,
        times,
        rng.standard_normal((n_paths, n_steps)),
        rng.standard_normal((n_paths, n_steps)),
    )
    terminal_spot = paths.s[:, -1]
    spot_se = terminal_spot.std(ddof=1) / np.sqrt(n_paths)
    assert abs(terminal_spot.mean() - 100.0) < 5 * spot_se
    for index in (25, 125, 500):
        values = paths.v[:, index]
        variance_se = values.std(ddof=1) / np.sqrt(n_paths)
        target = expected_variance(config, times[index - 1])
        assert abs(values.mean() - target) < 5 * variance_se + 3e-4


@pytest.mark.slow
def test_nearly_deterministic_variance_produces_flat_smile() -> None:
    config = HestonConfig(nu=1e-4)
    n_paths, n_steps = 120_000, 100
    times = np.linspace(1 / n_steps, 1.0, n_steps)
    rng = np.random.default_rng(83)
    half = n_paths // 2
    z_half = rng.standard_normal((half, n_steps))
    z_perp_half = rng.standard_normal((half, n_steps))
    paths = simulate_given_normals(
        config,
        100.0,
        0.0,
        times,
        np.vstack((z_half, -z_half)),
        np.vstack((z_perp_half, -z_perp_half)),
    )
    smile = smile_from_terminals(paths.s[:, -1], 100.0, np.linspace(-0.1, 0.1, 7), maturity=1.0)
    assert smile["ok"].all()
    assert np.max(np.abs(smile["iv"] - np.sqrt(config.theta))) < 0.003
