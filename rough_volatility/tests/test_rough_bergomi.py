"""Deterministic and stochastic gates for the rough Bergomi simulator."""

from dataclasses import replace

import numpy as np
import pytest
from rough_volatility.config import BergomiConfig
from rough_volatility.rough_bergomi import (
    build_operators,
    simulate_chunked,
    simulate_given_normals,
    volterra_increment_cross_covariance,
)
from scipy.integrate import quad


def _config(**changes: object) -> BergomiConfig:
    return replace(
        BergomiConfig(n_steps=64, n_paths=2000, chunk_size=500, keep_paths=20),
        **changes,
    )


def test_schur_operators_reconstruct_exact_volterra_diagonal() -> None:
    times = np.linspace(1 / 200, 1.0, 200)
    operators = build_operators(0.10, times)
    reconstructed = (
        operators.cross_op @ operators.cross_op.T
        + operators.residual_chol @ operators.residual_chol.T
    )
    np.testing.assert_allclose(np.diag(reconstructed), times**0.2, atol=1e-12)
    assert operators.diag_error <= 1e-12
    assert operators.jitter_used == 0.0


def test_increment_cross_covariance_matches_quadrature() -> None:
    h = 0.10
    times = np.linspace(0.05, 0.50, 10)
    actual = volterra_increment_cross_covariance(h, times)
    left = np.r_[0.0, times[:-1]]
    for row, column in [(0, 0), (3, 0), (3, 3), (9, 2), (9, 9)]:
        upper = min(times[column], times[row])
        expected = 0.0
        if upper > left[column]:
            expected = (
                np.sqrt(2 * h)
                * quad(
                    lambda value, target=times[row]: (target - value) ** (h - 0.5),
                    left[column],
                    upper,
                    points=[upper],
                )[0]
            )
        assert actual[row, column] == pytest.approx(expected, abs=1e-9)


def test_simulation_shapes_variance_normalization_and_forward_curve() -> None:
    config = _config(forward_variance=((0.0, 0.03), (0.5, 0.04), (1.0, 0.06)))
    times = np.linspace(1 / config.n_steps, 1.0, config.n_steps)
    operators = build_operators(config.h, times)
    rng = np.random.default_rng(70)
    normals = [rng.standard_normal((config.n_paths, config.n_steps)) for _ in range(3)]
    paths = simulate_given_normals(config, operators, *normals)
    assert paths.s.shape == (config.n_paths, config.n_steps + 1)
    assert paths.v.shape == paths.s.shape
    assert paths.driver.shape == (config.n_paths, config.n_steps)
    np.testing.assert_allclose(paths.v[:, 0], 0.03)
    expected_terminal = 0.06
    error = paths.v[:, -1].std(ddof=1) / np.sqrt(config.n_paths)
    assert abs(paths.v[:, -1].mean() - expected_terminal) < 5 * error


def test_chunk_size_does_not_change_seeded_results() -> None:
    config = _config(n_paths=600, chunk_size=600, keep_paths=15)
    times = np.linspace(1 / config.n_steps, 1.0, config.n_steps)
    operators = build_operators(config.h, times)
    whole = simulate_chunked(config, operators, 1210, maturity_indices=(16, 64))
    chunked = simulate_chunked(
        replace(config, chunk_size=137),
        operators,
        1210,
        maturity_indices=(16, 64),
    )
    for index in (16, 64):
        np.testing.assert_allclose(
            whole.s_by_maturity[index], chunked.s_by_maturity[index], atol=1e-13, rtol=1e-15
        )
    np.testing.assert_allclose(whole.s_sample, chunked.s_sample, atol=1e-13, rtol=1e-15)
    np.testing.assert_allclose(whole.v_sample, chunked.v_sample, atol=1e-13, rtol=1e-15)


@pytest.mark.slow
def test_forward_variance_and_spot_martingale_within_five_standard_errors() -> None:
    config = _config(n_steps=100, n_paths=40_000, chunk_size=5000, keep_paths=0)
    times = np.linspace(1 / config.n_steps, 1.0, config.n_steps)
    result = simulate_chunked(
        config,
        build_operators(config.h, times),
        72,
        maturity_indices=(5, 25, 100),
    )
    for check in result.ev_check["variance"]:
        assert abs(check["z_score"]) < 5.0
    terminal = result.s_by_maturity[100]
    standard_error = terminal.std(ddof=1) / np.sqrt(terminal.size)
    assert abs(terminal.mean() - config.s0 * np.exp(config.r)) < 5 * standard_error
