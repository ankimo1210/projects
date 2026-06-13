"""Tests for fourier_book.spectral."""

import numpy as np
from fourier_book import spectral


def _grid(n, L):
    return np.linspace(0.0, L, n, endpoint=False)


def test_spectral_derivative_of_sine():
    L = 2 * np.pi
    x = _grid(64, L)
    u = np.sin(x)
    np.testing.assert_allclose(spectral.spectral_derivative(u, L), np.cos(x), atol=1e-9)


def test_spectral_second_derivative_of_sine():
    L = 2 * np.pi
    x = _grid(64, L)
    u = np.sin(3 * x)
    np.testing.assert_allclose(
        spectral.spectral_derivative(u, L, order=2), -9 * np.sin(3 * x), atol=1e-8
    )


def test_heat_single_mode_matches_analytic():
    L = 2 * np.pi
    x = _grid(128, L)
    m, alpha, t = 4, 0.1, 0.5
    u0 = np.sin(m * x)
    expected = np.exp(-alpha * m**2 * t) * np.sin(m * x)  # k = m when L = 2π
    np.testing.assert_allclose(spectral.solve_heat_spectral(u0, L, alpha, t), expected, atol=1e-10)


def test_heat_high_modes_decay_faster():
    L = 2 * np.pi
    x = _grid(128, L)
    alpha, t = 0.05, 0.3
    low = spectral.solve_heat_spectral(np.sin(1 * x), L, alpha, t)
    high = spectral.solve_heat_spectral(np.sin(8 * x), L, alpha, t)
    # Amplitude = energy proxy; the high mode should be far more damped.
    assert np.max(np.abs(high)) < np.max(np.abs(low))


def test_wave_single_standing_mode():
    L = 2 * np.pi
    x = _grid(128, L)
    m, c, t = 3, 1.0, 0.4
    u0 = np.sin(m * x)
    v0 = np.zeros_like(x)
    expected = np.cos(c * m * t) * np.sin(m * x)  # ω = c|k| = c·m
    np.testing.assert_allclose(spectral.solve_wave_spectral(u0, v0, L, c, t), expected, atol=1e-10)


def test_poisson_recovers_solution():
    L = 2 * np.pi
    x = _grid(128, L)
    f = -np.sin(x)  # zero mean; u'' = -sin x  ->  u = sin x
    u = spectral.solve_poisson_spectral(f, L)
    np.testing.assert_allclose(u, np.sin(x), atol=1e-10)
    # Sanity: differentiating the solution twice returns f.
    np.testing.assert_allclose(spectral.spectral_derivative(u, L, order=2), f, atol=1e-9)


def test_wavenumbers_basic():
    L = 2 * np.pi
    k = spectral.wavenumbers(8, L)
    assert np.isclose(k[0], 0.0)
    assert np.isclose(k[1], 1.0)  # 2π · (1/8) / (2π/8) = 1
