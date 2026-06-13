"""Tests for la_book.algebra."""

import numpy as np
import pytest
from la_book import algebra


def test_rref_identity_for_invertible():
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    R, pivots = algebra.rref(A)
    np.testing.assert_allclose(R, np.eye(2), atol=1e-12)
    assert pivots == [0, 1]


def test_rref_rank_deficient():
    # Third row = first + second: rank 2.
    A = np.array([[1.0, 2.0, 3.0], [0.0, 1.0, 1.0], [1.0, 3.0, 4.0]])
    R, pivots = algebra.rref(A)
    assert len(pivots) == 2
    assert algebra.rank(A) == 2
    assert np.all(R[2] == 0.0)


def test_rank_matches_numpy():
    rng = np.random.default_rng(0)
    A = rng.standard_normal((5, 3))
    B = A @ rng.standard_normal((3, 6))  # rank <= 3 by construction
    assert algebra.rank(B) == np.linalg.matrix_rank(B) == 3


def test_gram_schmidt_orthonormal_and_spans():
    rng = np.random.default_rng(1)
    V = rng.standard_normal((5, 3))
    Q = algebra.gram_schmidt(V)
    np.testing.assert_allclose(Q.T @ Q, np.eye(3), atol=1e-10)
    # Same span: projecting V's columns onto col(Q) must reproduce them.
    np.testing.assert_allclose(Q @ (Q.T @ V), V, atol=1e-10)


def test_gram_schmidt_drops_dependent_columns():
    v = np.array([1.0, 2.0, 3.0])
    V = np.column_stack([v, 2 * v, np.array([1.0, 0.0, 0.0])])
    Q = algebra.gram_schmidt(V)
    assert Q.shape[1] == 2


def test_projection_matrix_idempotent_symmetric():
    rng = np.random.default_rng(2)
    A = rng.standard_normal((6, 2))
    P = algebra.projection_matrix(A)
    np.testing.assert_allclose(P @ P, P, atol=1e-10)
    np.testing.assert_allclose(P, P.T, atol=1e-10)
    # P fixes vectors already in the column space.
    np.testing.assert_allclose(P @ A[:, 0], A[:, 0], atol=1e-10)


def test_least_squares_matches_lstsq():
    rng = np.random.default_rng(3)
    A = rng.standard_normal((20, 4))
    b = rng.standard_normal(20)
    x, res = algebra.least_squares(A, b)
    x_ref = np.linalg.lstsq(A, b, rcond=None)[0]
    np.testing.assert_allclose(x, x_ref, atol=1e-10)
    assert res == pytest.approx(np.linalg.norm(A @ x_ref - b))


def test_ridge_zero_lambda_is_least_squares_and_shrinks():
    rng = np.random.default_rng(4)
    A = rng.standard_normal((30, 3))
    b = rng.standard_normal(30)
    x0 = algebra.ridge(A, b, 0.0)
    x_ls, _ = algebra.least_squares(A, b)
    np.testing.assert_allclose(x0, x_ls, atol=1e-10)
    x_big = algebra.ridge(A, b, 1e6)
    assert np.linalg.norm(x_big) < np.linalg.norm(x_ls)


def test_power_iteration_dominant_eigenpair():
    A = np.array([[2.0, 1.0], [1.0, 2.0]])  # eigenvalues 3 and 1
    lam, v = algebra.power_iteration(A, n_iter=100)
    assert lam == pytest.approx(3.0, abs=1e-8)
    np.testing.assert_allclose(A @ v, lam * v, atol=1e-6)


def test_markov_stationary():
    P = np.array([[0.9, 0.1], [0.5, 0.5]])
    pi = algebra.markov_stationary(P)
    assert pi.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(pi @ P, pi, atol=1e-12)


def test_page_rank_sums_to_one_and_is_stationary():
    from la_book.datasets import make_web_graph

    _, adj = make_web_graph()
    r = algebra.page_rank(adj)
    assert r.sum() == pytest.approx(1.0)
    # r must be a fixed point of the Google matrix iteration.
    n = adj.shape[0]
    out = adj.sum(axis=1, keepdims=True)
    T = np.where(out > 0, adj / np.where(out == 0, 1.0, out), 1.0 / n)
    G = 0.85 * T + 0.15 / n
    np.testing.assert_allclose(r @ G, r, atol=1e-10)


def test_conjugate_gradient_solves_spd():
    rng = np.random.default_rng(5)
    M = rng.standard_normal((8, 8))
    A = M @ M.T + 8 * np.eye(8)
    b = rng.standard_normal(8)
    x, res = algebra.conjugate_gradient(A, b)
    np.testing.assert_allclose(A @ x, b, atol=1e-7)
    assert res[-1] < 1e-9


def test_gradient_descent_quadratic_converges():
    A = np.array([[3.0, 0.0], [0.0, 1.0]])
    b = np.array([3.0, 2.0])
    path = algebra.gradient_descent_quadratic(A, b, lr=0.3, n_iter=300)
    np.testing.assert_allclose(path[-1], np.linalg.solve(A, b), atol=1e-6)


def test_newton_one_step_on_quadratic():
    A = np.array([[4.0, 1.0], [1.0, 3.0]])
    b = np.array([1.0, 2.0])
    path = algebra.newton_method(
        grad=lambda x: A @ x - b,
        hess=lambda x: A,
        x0=np.array([5.0, -5.0]),
        n_iter=1,
    )
    np.testing.assert_allclose(path[-1], np.linalg.solve(A, b), atol=1e-10)
