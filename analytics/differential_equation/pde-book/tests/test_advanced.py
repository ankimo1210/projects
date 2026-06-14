"""Tests for pde_book.advanced — spectral, KdV, reaction-diffusion, 2-D wave."""

import numpy as np
from pde_book import advanced


def test_spectral_heat_is_exact_for_a_mode():
    # On a periodic domain a single Fourier mode decays exactly; spectral method
    # should reproduce e^{-alpha k^2 t} to machine precision.
    n, length, alpha = 64, 2 * np.pi, 0.5
    x = np.linspace(0, length, n, endpoint=False)
    m = 3
    u0 = np.sin(m * x)
    dt, steps = 0.01, 50
    U = advanced.solve_heat_spectral(u0, alpha, length, dt, steps)
    exact = np.exp(-alpha * m**2 * steps * dt) * np.sin(m * x)
    np.testing.assert_allclose(U[-1], exact, atol=1e-12)


def test_kdv_soliton_keeps_shape_and_moves_at_amp_squared():
    n, length = 256, 40.0
    dx = length / n
    x = np.linspace(0, length, n, endpoint=False)
    amp, x0 = 1.0, 10.0
    u0 = advanced.kdv_soliton(x, 0.0, amp, x0, length)
    dt, steps = 0.0025, 800
    U = advanced.solve_kdv(u0, dx, dt, steps)
    t_end = steps * dt
    exact = advanced.kdv_soliton(x, t_end, amp, x0, length)
    # soliton retains amplitude 3*amp^2 and travels right at speed amp^2
    assert abs(U[-1].max() - 3 * amp**2) < 0.1
    assert np.max(np.abs(U[-1] - exact)) < 0.15
    # invariants: mass and momentum conserved
    assert abs(U[-1].sum() - U[0].sum()) * dx < 1e-6
    assert abs((U[-1] ** 2).sum() - (U[0] ** 2).sum()) * dx < 1e-3


def test_gray_scott_forms_structure_and_stays_bounded():
    u0, v0 = advanced.gray_scott_seed(n=64, seed=0)
    u, v = advanced.solve_gray_scott(
        u0, v0, Du=0.16, Dv=0.08, feed=0.035, kill=0.06, dx=1.0, dt=1.0, steps=2000
    )
    assert np.all(np.isfinite(u)) and np.all(np.isfinite(v))
    assert u.min() > -0.05 and u.max() < 1.05  # bounded
    assert v.max() > 0.1  # the v species survived and spread (a pattern, not decay to 0)
    assert v.std() > 1e-3  # spatially non-uniform


def test_wave_2d_matches_standing_mode():
    n, length, c = 41, 1.0, 1.0
    x = np.linspace(0, length, n)
    dx = x[1] - x[0]
    u0 = advanced.wave_mode_2d(x, x, 0.0, c, mode=(1, 1), length=length)
    dt = 0.5 * dx / c  # 2-D CFL needs <= 1/sqrt(2) ~ 0.707
    steps = 40
    U = advanced.solve_wave_2d(u0, np.zeros_like(u0), c, dx, dt, steps)
    exact = advanced.wave_mode_2d(x, x, steps * dt, c, mode=(1, 1), length=length)
    np.testing.assert_allclose(U[-1], exact, atol=5e-3)
