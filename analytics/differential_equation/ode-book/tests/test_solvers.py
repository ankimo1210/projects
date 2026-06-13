"""Tests for ode_book.solvers — accuracy, convergence order, shapes."""

import numpy as np
import pytest
from ode_book import solvers, systems


@pytest.fixture
def decay():
    """dy/dt = -y, y(0)=1, exact solution e^{-t}."""
    f = systems.exponential(-1.0)
    t = np.linspace(0, 4, 81)
    exact = np.exp(-t)
    return f, t, exact


def test_shapes_are_time_by_dim(decay):
    f, t, _ = decay
    Y = solvers.rk4(f, [1.0], t)
    assert Y.shape == (t.size, 1)


def test_rk4_more_accurate_than_euler(decay):
    f, t, exact = decay
    e_euler = solvers.global_error(solvers.euler(f, [1.0], t)[:, 0], exact)
    e_heun = solvers.global_error(solvers.heun(f, [1.0], t)[:, 0], exact)
    e_rk4 = solvers.global_error(solvers.rk4(f, [1.0], t)[:, 0], exact)
    assert e_rk4 < e_heun < e_euler
    assert e_rk4 < 1e-6


def test_euler_first_order_convergence():
    f = systems.exponential(-1.0)
    errs = []
    for n in (20, 40, 80):
        t = np.linspace(0, 2, n + 1)
        Y = solvers.euler(f, [1.0], t)[:, 0]
        errs.append(solvers.global_error(Y, np.exp(-t)))
    # halving dt roughly halves the error for a first-order method
    assert errs[0] / errs[1] > 1.7
    assert errs[1] / errs[2] > 1.7


def test_rk4_fourth_order_convergence():
    f = systems.exponential(-1.0)
    errs = []
    for n in (10, 20, 40):
        t = np.linspace(0, 2, n + 1)
        Y = solvers.rk4(f, [1.0], t)[:, 0]
        errs.append(solvers.global_error(Y, np.exp(-t)))
    # 4th order: halving dt cuts error ~16x (allow generous slack)
    assert errs[0] / errs[1] > 8
    assert errs[1] / errs[2] > 8


def test_solve_ivp_wrapper_matches_exact(decay):
    f, t, exact = decay
    Y = solvers.solve(f, [1.0], t, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(Y[:, 0], exact, atol=1e-7)


def test_undamped_oscillator_conserves_energy():
    # x'' + x = 0 with x(0)=1, v(0)=0: energy 0.5(v^2 + x^2) is conserved.
    f = systems.harmonic_oscillator(omega=1.0, gamma=0.0)
    t = np.linspace(0, 20, 4001)
    Y = solvers.rk4(f, [1.0, 0.0], t)
    energy = 0.5 * (Y[:, 1] ** 2 + Y[:, 0] ** 2)
    assert np.max(np.abs(energy - energy[0])) < 1e-4


def test_system_integration_returns_all_components():
    f = systems.lotka_volterra(1.1, 0.4, 0.1, 0.4)
    t = np.linspace(0, 5, 200)
    Y = solvers.rk4(f, [2.0, 1.0], t)
    assert Y.shape == (200, 2)
    assert np.all(Y > 0)  # populations stay positive on this window
