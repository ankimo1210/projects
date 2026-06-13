"""Tests for ode_book.systems — equilibria, conservation, fixed-point types."""

import numpy as np
from ode_book import systems


def test_logistic_equilibria():
    f = systems.logistic(r=0.8, K=2.0)
    assert abs(float(f(0.0, 2.0))) < 1e-12  # y = K is an equilibrium
    assert abs(float(f(0.0, 0.0))) < 1e-12  # y = 0 is an equilibrium
    assert f(0.0, 1.0) > 0  # below K -> grows


def test_sir_conserves_population():
    f = systems.sir(beta=0.5, gamma=0.2, N=1.0)
    deriv = f(0.0, np.array([0.7, 0.2, 0.1]))
    assert abs(float(np.sum(deriv))) < 1e-12  # S'+I'+R' = 0


def test_lotka_volterra_coexistence_equilibrium():
    alpha, beta, delta, gamma = 1.1, 0.4, 0.1, 0.4
    f = systems.lotka_volterra(alpha, beta, delta, gamma)
    eq = np.array([gamma / delta, alpha / beta])  # (x*, z*)
    np.testing.assert_allclose(f(0.0, eq), [0.0, 0.0], atol=1e-12)


def test_jacobian_of_linear_system_is_the_matrix():
    A = np.array([[0.0, 1.0], [-2.0, -0.3]])
    f = systems.linear_system(A)
    J = systems.jacobian(f, [0.0, 0.0])
    np.testing.assert_allclose(J, A, atol=1e-5)


def test_classify_fixed_point_covers_each_type():
    assert systems.classify_fixed_point([[0, 1], [-1, 0]]) == "center"
    assert systems.classify_fixed_point([[-1, 0], [0, -2]]) == "stable node"
    assert systems.classify_fixed_point([[1, 0], [0, 2]]) == "unstable node"
    assert systems.classify_fixed_point([[1, 0], [0, -1]]) == "saddle"
    assert systems.classify_fixed_point([[-0.1, 1], [-1, -0.1]]) == "stable spiral"
    assert systems.classify_fixed_point([[0.1, 1], [-1, 0.1]]) == "unstable spiral"


def test_vector_field_grid_shapes():
    f = systems.linear_system([[0, 1], [-1, 0]])
    X, _Y, U, _V = systems.vector_field_grid(f, (-2, 2), (-2, 2), n=10)
    assert X.shape == U.shape == (10, 10)
