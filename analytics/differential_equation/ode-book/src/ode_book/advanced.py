"""Advanced ODE topics backing notebook 09.

Boundary-value problems (shooting), Sturm-Liouville eigenvalues, stochastic
differential equations (Euler-Maruyama), linear control (LQR / pole placement),
and fitting an ODE's parameters to data ("training" a vector field). Each is a
small, self-contained reference implementation with a test pinning it to a known
answer.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .solvers import rk4


# --------------------------------------------------------------------------- #
# Boundary-value problems via the shooting method.
# --------------------------------------------------------------------------- #
def shooting_bvp(f2, a, b, alpha, beta, n=400, s_guess=(0.0, 1.0), tol=1e-8, max_iter=50):
    """Solve the 2nd-order BVP y'' = f2(x, y, y'), y(a)=alpha, y(b)=beta.

    Reduces to the IVP [y, y']' = [y', f2] and uses the secant method on the
    unknown initial slope s = y'(a) to hit y(b) = beta. Returns (x, y).
    """
    x = np.linspace(a, b, n)

    def endpoint(s):
        def rhs(t, state):
            y, yp = state
            return np.array([yp, f2(t, y, yp)])

        Y = rk4(rhs, [alpha, s], x)
        return Y[-1, 0], Y

    s0, s1 = s_guess
    g0 = endpoint(s0)[0] - beta
    for _ in range(max_iter):
        v1, Y1 = endpoint(s1)
        g1 = v1 - beta
        if abs(g1) < tol:
            return x, Y1[:, 0]
        denom = g1 - g0
        if abs(denom) < 1e-300:  # pragma: no cover - degenerate guesses
            break
        s0, s1, g0 = s1, s1 - g1 * (s1 - s0) / denom, g1
    return x, endpoint(s1)[1][:, 0]


def sturm_liouville_eigenvalues(n_modes=5, length=1.0, n_grid=400):
    """Smallest eigenvalues of -y'' = lambda y with y(0)=y(L)=0.

    Analytic spectrum is (n pi / L)^2; here computed from the discrete Dirichlet
    Laplacian so the notebook can compare numeric vs exact.
    """
    dx = length / (n_grid - 1)
    m = n_grid - 2
    main = 2.0 * np.ones(m) / dx**2
    off = -1.0 * np.ones(m - 1) / dx**2
    T = np.diag(main) + np.diag(off, 1) + np.diag(off, -1)
    eig = np.sort(np.linalg.eigvalsh(T))
    return eig[:n_modes]


# --------------------------------------------------------------------------- #
# Stochastic differential equations: Euler-Maruyama.
# --------------------------------------------------------------------------- #
def euler_maruyama(drift: Callable, diffusion: Callable, y0, t, seed=0):
    """One path of dY = drift(t, Y) dt + diffusion(t, Y) dW via Euler-Maruyama.

    drift/diffusion take (t, y) and return scalars (1-D SDE). Returns Y of the
    same length as ``t``. Brownian increments are seeded for reproducibility.
    """
    t = np.asarray(t, dtype=float)
    rng = np.random.default_rng(seed)
    y = float(y0)
    Y = np.empty(t.size)
    Y[0] = y
    for k in range(t.size - 1):
        dt = t[k + 1] - t[k]
        dw = np.sqrt(dt) * rng.standard_normal()
        y = y + drift(t[k], y) * dt + diffusion(t[k], y) * dw
        Y[k + 1] = y
    return Y


def ou_ensemble(kappa, theta, sigma, y0, t, n_paths=400, seed=0):
    """Ensemble of Ornstein-Uhlenbeck paths dY=kappa(theta-Y)dt+sigma dW.

    Returns an array of shape (n_paths, len(t)). The ensemble mean tracks the
    deterministic ODE theta+(y0-theta)e^{-kappa t}; the variance approaches
    sigma^2/(2 kappa).
    """
    t = np.asarray(t, dtype=float)
    out = np.empty((n_paths, t.size))
    for p in range(n_paths):
        out[p] = euler_maruyama(
            lambda tt, y: kappa * (theta - y), lambda tt, y: sigma, y0, t, seed=seed + p
        )
    return out


# --------------------------------------------------------------------------- #
# Linear control: LQR and pole placement for dx/dt = A x + B u.
# --------------------------------------------------------------------------- #
def lqr(A, B, Q, R):
    """Continuous-time LQR gain K (u = -K x) minimizing int x'Qx + u'Ru.

    Solves the algebraic Riccati equation; the closed loop A - B K is stable.
    Returns (K, eigenvalues of A - B K).
    """
    from scipy.linalg import solve_continuous_are

    A, B, Q, R = (np.atleast_2d(np.asarray(m, dtype=float)) for m in (A, B, Q, R))
    P = solve_continuous_are(A, B, Q, R)
    K = np.linalg.solve(R, B.T @ P)
    return K, np.linalg.eigvals(A - B @ K)


def place_poles(A, B, desired):
    """Pole placement: gain K (u = -K x) putting eig(A - B K) at ``desired``.

    Thin wrapper over scipy.signal.place_poles. Returns (K, achieved poles).
    """
    from scipy.signal import place_poles as _place

    A = np.atleast_2d(np.asarray(A, dtype=float))
    B = np.atleast_2d(np.asarray(B, dtype=float))
    res = _place(A, B, np.asarray(desired, dtype=complex))
    return res.gain_matrix, np.linalg.eigvals(A - B @ res.gain_matrix)


# --------------------------------------------------------------------------- #
# Fitting an ODE to data — the gradient-based idea behind Neural ODEs.
# --------------------------------------------------------------------------- #
def fit_linear_system(t, Y, A0=None):
    """Recover the matrix A of dx/dt = A x from an observed trajectory ``Y``.

    Minimizes the trajectory mismatch ||rk4(A) - Y|| over the entries of A with
    a least-squares optimizer — the same "differentiate the loss through the
    solver" idea that trains a Neural ODE, on the simplest (linear) field.
    Returns the fitted A (dim x dim).
    """
    from scipy.optimize import least_squares

    from .systems import linear_system

    t = np.asarray(t, dtype=float)
    Y = np.asarray(Y, dtype=float)
    dim = Y.shape[1]
    if A0 is None:
        A0 = np.zeros((dim, dim))

    def residual(theta):
        A = theta.reshape(dim, dim)
        pred = rk4(linear_system(A), Y[0], t)
        return (pred - Y).ravel()

    sol = least_squares(residual, np.asarray(A0, dtype=float).ravel())
    return sol.x.reshape(dim, dim)
