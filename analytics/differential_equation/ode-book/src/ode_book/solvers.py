"""Time-stepping solvers for ODE initial value problems.

The hand-written steppers (Euler / Heun / RK4) take a right-hand side
``f(t, y)`` where ``y`` is a scalar or a 1-D NumPy array, so the same code
integrates a single ODE or a coupled system. ``solve`` wraps
``scipy.integrate.solve_ivp`` for the "what you actually use" comparison.

All steppers share the signature ``(f, y0, t)`` and return an array ``Y`` of
shape ``(len(t), dim)`` so notebooks can plot or compare them uniformly.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.integrate import solve_ivp

RHS = Callable[[float, np.ndarray], np.ndarray]


def _as_array(y0) -> np.ndarray:
    return np.atleast_1d(np.asarray(y0, dtype=float))


def euler(f: RHS, y0, t: np.ndarray) -> np.ndarray:
    """Explicit (forward) Euler. First order: error per step O(dt^2)."""
    t = np.asarray(t, dtype=float)
    y = _as_array(y0)
    Y = np.empty((t.size, y.size))
    Y[0] = y
    for k in range(t.size - 1):
        dt = t[k + 1] - t[k]
        Y[k + 1] = Y[k] + dt * np.asarray(f(t[k], Y[k]), dtype=float)
    return Y


def heun(f: RHS, y0, t: np.ndarray) -> np.ndarray:
    """Heun's method (explicit trapezoid / RK2): predictor + corrector."""
    t = np.asarray(t, dtype=float)
    y = _as_array(y0)
    Y = np.empty((t.size, y.size))
    Y[0] = y
    for k in range(t.size - 1):
        dt = t[k + 1] - t[k]
        k1 = np.asarray(f(t[k], Y[k]), dtype=float)
        y_pred = Y[k] + dt * k1
        k2 = np.asarray(f(t[k + 1], y_pred), dtype=float)
        Y[k + 1] = Y[k] + 0.5 * dt * (k1 + k2)
    return Y


def rk4(f: RHS, y0, t: np.ndarray) -> np.ndarray:
    """Classical 4th-order Runge-Kutta. Error per step O(dt^5)."""
    t = np.asarray(t, dtype=float)
    y = _as_array(y0)
    Y = np.empty((t.size, y.size))
    Y[0] = y
    for k in range(t.size - 1):
        dt = t[k + 1] - t[k]
        tk = t[k]
        yk = Y[k]
        k1 = np.asarray(f(tk, yk), dtype=float)
        k2 = np.asarray(f(tk + 0.5 * dt, yk + 0.5 * dt * k1), dtype=float)
        k3 = np.asarray(f(tk + 0.5 * dt, yk + 0.5 * dt * k2), dtype=float)
        k4 = np.asarray(f(tk + dt, yk + dt * k3), dtype=float)
        Y[k + 1] = yk + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return Y


METHODS = {"euler": euler, "heun": heun, "rk4": rk4}


def integrate_ode(method: str, f: RHS, y0, t: np.ndarray) -> np.ndarray:
    """Dispatch to a named hand-written stepper ('euler' / 'heun' / 'rk4')."""
    try:
        stepper = METHODS[method]
    except KeyError:  # pragma: no cover - guards a typo
        raise ValueError(f"unknown method {method!r}; choose from {sorted(METHODS)}") from None
    return stepper(f, y0, t)


def solve(f: RHS, y0, t: np.ndarray, method: str = "RK45", **kwargs) -> np.ndarray:
    """Thin wrapper over scipy.integrate.solve_ivp evaluated on grid ``t``.

    Returns Y of shape (len(t), dim) to match the hand-written steppers. For
    stiff problems pass method="Radau" or "BDF".
    """
    t = np.asarray(t, dtype=float)
    y0 = _as_array(y0)
    sol = solve_ivp(f, (t[0], t[-1]), y0, t_eval=t, method=method, dense_output=False, **kwargs)
    if not sol.success:  # pragma: no cover - surfaced only on solver failure
        raise RuntimeError(f"solve_ivp failed: {sol.message}")
    return sol.y.T


def global_error(numeric: np.ndarray, exact: np.ndarray) -> float:
    """Max-norm of the error over the whole trajectory (for convergence plots)."""
    return float(np.max(np.abs(np.asarray(numeric) - np.asarray(exact))))
