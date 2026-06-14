"""Tests for ode_book.advanced — BVP, eigenvalues, SDE, control, ODE fitting."""

import numpy as np
from ode_book import advanced, solvers, systems


def test_shooting_bvp_recovers_cubic():
    # y'' = 6x, y(0)=0, y(1)=1  =>  y = x^3.
    x, y = advanced.shooting_bvp(lambda t, yy, yp: 6 * t, 0.0, 1.0, 0.0, 1.0, n=400)
    np.testing.assert_allclose(y, x**3, atol=1e-4)


def test_sturm_liouville_eigenvalues_match_analytic():
    eig = advanced.sturm_liouville_eigenvalues(n_modes=3, length=1.0, n_grid=600)
    analytic = (np.arange(1, 4) * np.pi) ** 2  # (n pi)^2
    np.testing.assert_allclose(eig, analytic, rtol=2e-3)


def test_euler_maruyama_reduces_to_ode_without_noise():
    # Zero diffusion => the SDE is just the deterministic OU ODE.
    t = np.linspace(0, 5, 500)
    kappa, theta, y0 = 0.8, 0.03, 0.09
    Y = advanced.euler_maruyama(lambda tt, y: kappa * (theta - y), lambda tt, y: 0.0, y0, t, seed=0)
    exact = theta + (y0 - theta) * np.exp(-kappa * t)
    np.testing.assert_allclose(Y, exact, atol=1e-3)


def test_ou_ensemble_mean_tracks_deterministic_solution():
    t = np.linspace(0, 6, 200)
    kappa, theta, sigma, y0 = 1.0, 0.0, 0.3, 1.0
    paths = advanced.ou_ensemble(kappa, theta, sigma, y0, t, n_paths=400, seed=1)
    mean = paths.mean(axis=0)
    deterministic = theta + (y0 - theta) * np.exp(-kappa * t)
    assert np.max(np.abs(mean - deterministic)) < 0.05  # within Monte-Carlo error


def test_lqr_stabilizes_double_integrator():
    A = [[0.0, 1.0], [0.0, 0.0]]  # double integrator x'' = u
    B = [[0.0], [1.0]]
    K, cl = advanced.lqr(A, B, Q=np.eye(2), R=[[1.0]])
    assert np.all(cl.real < 0)  # closed loop is stable
    assert K.shape == (1, 2)


def test_place_poles_hits_targets():
    A = [[0.0, 1.0], [0.0, 0.0]]
    B = [[0.0], [1.0]]
    _K, poles = advanced.place_poles(A, B, [-2.0, -3.0])
    np.testing.assert_allclose(np.sort(poles.real), [-3.0, -2.0], atol=1e-8)


def test_fit_linear_system_recovers_matrix():
    A_true = np.array([[-0.5, 1.0], [-1.0, -0.5]])  # stable spiral
    t = np.linspace(0, 6, 120)
    Y = solvers.rk4(systems.linear_system(A_true), [1.0, 0.0], t)
    A_fit = advanced.fit_linear_system(t, Y)
    np.testing.assert_allclose(A_fit, A_true, atol=1e-2)
