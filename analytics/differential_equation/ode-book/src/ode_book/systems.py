"""Right-hand-side factories for the model systems studied in the book.

Each factory returns a callable ``f(t, y)`` ready for the steppers in
``solvers`` or for ``scipy.integrate.solve_ivp``. Keeping the models here (not
inline in notebooks) means the tests can pin their qualitative behaviour
(equilibria, conserved quantities) independently of the prose.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# First-order scalar models.
# --------------------------------------------------------------------------- #
def exponential(r: float):
    """dy/dt = r y  (Malthusian growth / decay)."""

    def f(t, y):
        return r * np.asarray(y, dtype=float)

    return f


def logistic(r: float, K: float):
    """dy/dt = r y (1 - y/K)  (logistic / bounded growth)."""

    def f(t, y):
        y = np.asarray(y, dtype=float)
        return r * y * (1.0 - y / K)

    return f


# --------------------------------------------------------------------------- #
# Linear systems and oscillators.
# --------------------------------------------------------------------------- #
def linear_system(A):
    """dx/dt = A x for a constant matrix A."""
    A = np.asarray(A, dtype=float)

    def f(t, x):
        return A @ np.asarray(x, dtype=float)

    return f


def harmonic_oscillator(omega: float, gamma: float = 0.0, forcing=None):
    """Damped, optionally forced oscillator written as a 2-D first-order system.

    State y = [x, v]. The second-order equation
        x'' + 2 gamma x' + omega^2 x = F(t)
    becomes x' = v, v' = -omega^2 x - 2 gamma v + F(t).
    ``forcing`` is an optional callable F(t) (default: free oscillation).
    """

    def f(t, y):
        x, v = y
        drive = 0.0 if forcing is None else float(forcing(t))
        return np.array([v, -(omega**2) * x - 2.0 * gamma * v + drive])

    return f


def pendulum(omega: float = 1.0, gamma: float = 0.0):
    """Nonlinear pendulum: theta'' + 2 gamma theta' + omega^2 sin(theta) = 0."""

    def f(t, y):
        theta, vel = y
        return np.array([vel, -(omega**2) * np.sin(theta) - 2.0 * gamma * vel])

    return f


# --------------------------------------------------------------------------- #
# Nonlinear / population / epidemic models.
# --------------------------------------------------------------------------- #
def lotka_volterra(alpha: float, beta: float, delta: float, gamma: float):
    """Predator-prey model. State y = [prey x, predator z].

    x' = alpha x - beta x z
    z' = delta x z - gamma z
    """

    def f(t, y):
        x, z = y
        return np.array([alpha * x - beta * x * z, delta * x * z - gamma * z])

    return f


def sir(beta: float, gamma: float, N: float = 1.0):
    """SIR epidemic model. State y = [S, I, R], total population N conserved.

    S' = -beta S I / N
    I' =  beta S I / N - gamma I
    R' =  gamma I
    """

    def f(t, y):
        S, I, _R = y  # R does not enter the dynamics (only S and I do)
        infection = beta * S * I / N
        return np.array([-infection, infection - gamma * I, gamma * I])

    return f


def van_der_pol(mu: float):
    """Van der Pol oscillator (limit cycle): x'' - mu (1 - x^2) x' + x = 0."""

    def f(t, y):
        x, v = y
        return np.array([v, mu * (1.0 - x * x) * v - x])

    return f


def lorenz(sigma: float = 10.0, rho: float = 28.0, beta: float = 8.0 / 3.0):
    """Lorenz system (the gateway to chaos). State y = [x, y, z].

    x' = sigma (y - x)
    y' = x (rho - z) - y
    z' = x y - beta z
    The classic (10, 28, 8/3) parameters produce the butterfly attractor.
    """

    def f(t, s):
        x, y, z = s
        return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])

    return f


# --------------------------------------------------------------------------- #
# Fixed-point / linear-stability analysis (phase-plane chapter).
# --------------------------------------------------------------------------- #
def jacobian(f, point, t: float = 0.0, h: float = 1e-6) -> np.ndarray:
    """Jacobian of a (time-independent) vector field at ``point``."""
    point = np.asarray(point, dtype=float)
    n = point.size
    J = np.zeros((n, n))
    for j in range(n):
        step = np.zeros(n)
        step[j] = h
        J[:, j] = (np.asarray(f(t, point + step)) - np.asarray(f(t, point - step))) / (2.0 * h)
    return J


def classify_fixed_point(J, tol: float = 1e-9) -> str:
    """Classify a 2-D fixed point from its Jacobian's eigenvalues.

    Returns one of: 'saddle', 'stable node', 'unstable node',
    'stable spiral', 'unstable spiral', 'center', or 'degenerate'.
    """
    eig = np.linalg.eigvals(np.asarray(J, dtype=float))
    re = eig.real
    im = eig.imag
    if np.any(np.abs(im) > tol):  # complex conjugate pair
        a = re[0]
        if a > tol:
            return "unstable spiral"
        if a < -tol:
            return "stable spiral"
        return "center"
    # real eigenvalues
    if np.any(np.abs(re) < tol):
        return "degenerate"
    if re[0] * re[1] < 0:
        return "saddle"
    return "stable node" if np.all(re < 0) else "unstable node"


def vector_field_grid(f, xlim, ylim, n: int = 20, t: float = 0.0):
    """Sample a 2-D vector field on a grid. Returns (X, Y, U, V) for quiver."""
    xs = np.linspace(xlim[0], xlim[1], n)
    ys = np.linspace(ylim[0], ylim[1], n)
    X, Y = np.meshgrid(xs, ys)
    U = np.zeros_like(X)
    V = np.zeros_like(Y)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            dx, dy = f(t, np.array([X[i, j], Y[i, j]]))
            U[i, j] = dx
            V[i, j] = dy
    return X, Y, U, V
