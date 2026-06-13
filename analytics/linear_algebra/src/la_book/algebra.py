"""Core linear-algebra helpers shared by the notebooks.

All functions are small, NumPy-only, and favor clarity over speed: they exist
so the notebooks can show *what* an algorithm does, not to compete with LAPACK.
"""

from __future__ import annotations

import numpy as np


def rref(A, tol: float = 1e-10):
    """Reduced row echelon form via Gauss-Jordan with partial pivoting.

    Returns (R, pivot_cols).
    """
    R = np.array(A, dtype=float)
    n_rows, n_cols = R.shape
    pivots: list[int] = []
    row = 0
    for col in range(n_cols):
        if row >= n_rows:
            break
        # Partial pivoting: bring the largest remaining entry to the pivot row.
        p = row + int(np.argmax(np.abs(R[row:, col])))
        if abs(R[p, col]) < tol:
            continue
        R[[row, p]] = R[[p, row]]
        R[row] = R[row] / R[row, col]
        for r in range(n_rows):
            if r != row:
                R[r] = R[r] - R[r, col] * R[row]
        pivots.append(col)
        row += 1
    R[np.abs(R) < tol] = 0.0
    return R, pivots


def rank(A, tol: float = 1e-10) -> int:
    """Rank = number of pivot columns in the RREF."""
    return len(rref(A, tol=tol)[1])


def gram_schmidt(V, tol: float = 1e-12):
    """Orthonormalize the columns of V (classical Gram-Schmidt).

    Linearly dependent columns are dropped. Returns Q with orthonormal columns.
    """
    V = np.array(V, dtype=float)
    basis: list[np.ndarray] = []
    for j in range(V.shape[1]):
        v = V[:, j].copy()
        for q in basis:
            v -= (q @ V[:, j]) * q
        norm = np.linalg.norm(v)
        if norm > tol:
            basis.append(v / norm)
    if not basis:
        return np.empty((V.shape[0], 0))
    return np.column_stack(basis)


def projection_matrix(A):
    """P = A (A^T A)^{-1} A^T — orthogonal projection onto col(A).

    Accepts a single vector (1-D) or a matrix whose columns span the subspace.
    Uses `solve`, never an explicit inverse.
    """
    A = np.array(A, dtype=float)
    if A.ndim == 1:
        A = A[:, None]
    G = A.T @ A
    return A @ np.linalg.solve(G, A.T)


def project_onto(b, A):
    """Orthogonal projection of vector b onto col(A)."""
    return projection_matrix(A) @ np.asarray(b, dtype=float)


def least_squares(A, b):
    """Solve min ||Ax - b||_2 via QR. Returns (x, residual_norm)."""
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    Q, R = np.linalg.qr(A)
    x = np.linalg.solve(R, Q.T @ b)
    return x, float(np.linalg.norm(A @ x - b))


def ridge(A, b, lam: float):
    """Ridge regression: solve (A^T A + lam I) x = A^T b."""
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    n = A.shape[1]
    return np.linalg.solve(A.T @ A + lam * np.eye(n), A.T @ b)


def power_iteration(A, n_iter: int = 200, seed: int = 0, return_history: bool = False):
    """Dominant eigenpair by repeated multiplication.

    Returns (lam, v) or (lam, v, history) where history is the Rayleigh
    quotient after each step.
    """
    rng = np.random.default_rng(seed)
    A = np.asarray(A, dtype=float)
    v = rng.standard_normal(A.shape[0])
    v /= np.linalg.norm(v)
    history = []
    lam = 0.0
    for _ in range(n_iter):
        w = A @ v
        v = w / np.linalg.norm(w)
        lam = float(v @ A @ v)
        history.append(lam)
    if return_history:
        return lam, v, np.array(history)
    return lam, v


def markov_stationary(P):
    """Stationary distribution pi of a row-stochastic matrix P (pi P = pi)."""
    P = np.asarray(P, dtype=float)
    w, V = np.linalg.eig(P.T)
    i = int(np.argmin(np.abs(w - 1.0)))
    pi = np.real(V[:, i])
    return pi / pi.sum()


def page_rank(
    adj,
    damping: float = 0.85,
    tol: float = 1e-12,
    max_iter: int = 200,
    return_history: bool = False,
):
    """PageRank by power iteration on the Google matrix.

    adj[i, j] = 1 means page i links to page j. Dangling pages (no outlinks)
    are treated as linking to every page uniformly.
    """
    A = np.asarray(adj, dtype=float)
    n = A.shape[0]
    out = A.sum(axis=1, keepdims=True)
    T = np.where(out > 0, A / np.where(out == 0, 1.0, out), 1.0 / n)
    G = damping * T + (1.0 - damping) / n
    r = np.full(n, 1.0 / n)
    history = [r.copy()]
    for _ in range(max_iter):
        r_new = r @ G
        history.append(r_new.copy())
        if np.abs(r_new - r).sum() < tol:
            r = r_new
            break
        r = r_new
    if return_history:
        return r, np.array(history)
    return r


def gradient_descent_quadratic(A, b, lr: float, n_iter: int = 50, x0=None):
    """Minimize f(x) = 0.5 x^T A x - b^T x with fixed-step gradient descent.

    Returns the path as an array of shape (n_iter + 1, n).
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    x = np.zeros_like(b) if x0 is None else np.array(x0, dtype=float)
    path = [x.copy()]
    for _ in range(n_iter):
        x = x - lr * (A @ x - b)
        path.append(x.copy())
    return np.array(path)


def jacobi(A, b, n_iter: int = 100, x0=None, return_history: bool = False):
    """Jacobi iteration: split A = D + R, update x <- D^{-1}(b - R x).

    Converges when A is (e.g.) strictly diagonally dominant. Returns x, or
    (x, residual_norms) when return_history is True.
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    d = np.diag(A)
    R = A - np.diag(d)
    x = np.zeros_like(b) if x0 is None else np.array(x0, dtype=float)
    res = [float(np.linalg.norm(A @ x - b))]
    for _ in range(n_iter):
        x = (b - R @ x) / d  # all components updated from the OLD x
        res.append(float(np.linalg.norm(A @ x - b)))
    return (x, np.array(res)) if return_history else x


def gauss_seidel(A, b, n_iter: int = 100, x0=None, return_history: bool = False):
    """Gauss-Seidel iteration: like Jacobi but uses already-updated components
    within the same sweep (forward substitution on the lower-triangular part).

    Usually converges about twice as fast as Jacobi.
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    n = b.size
    x = np.zeros_like(b) if x0 is None else np.array(x0, dtype=float)
    res = [float(np.linalg.norm(A @ x - b))]
    for _ in range(n_iter):
        for i in range(n):
            x[i] = (b[i] - A[i, :i] @ x[:i] - A[i, i + 1 :] @ x[i + 1 :]) / A[i, i]
        res.append(float(np.linalg.norm(A @ x - b)))
    return (x, np.array(res)) if return_history else x


def conjugate_gradient(A, b, tol: float = 1e-10, max_iter: int | None = None, x0=None):
    """Conjugate gradient for symmetric positive definite A.

    Returns (x, residual_norms).
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    n = b.size
    x = np.zeros(n) if x0 is None else np.array(x0, dtype=float)
    r = b - A @ x
    p = r.copy()
    rs = float(r @ r)
    res = [np.sqrt(rs)]
    for _ in range(max_iter if max_iter is not None else n):
        Ap = A @ p
        alpha = rs / float(p @ Ap)
        x = x + alpha * p
        r = r - alpha * Ap
        rs_new = float(r @ r)
        res.append(np.sqrt(rs_new))
        if np.sqrt(rs_new) < tol:
            break
        p = r + (rs_new / rs) * p
        rs = rs_new
    return x, np.array(res)


def newton_method(grad, hess, x0, n_iter: int = 20):
    """Newton's method for minimization: x <- x - H(x)^{-1} grad(x).

    Returns the path as an array of shape (n_iter + 1, n).
    """
    x = np.array(x0, dtype=float)
    path = [x.copy()]
    for _ in range(n_iter):
        x = x - np.linalg.solve(hess(x), grad(x))
        path.append(x.copy())
    return np.array(path)
