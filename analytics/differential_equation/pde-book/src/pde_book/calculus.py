"""Calculus foundations — numerical and symbolic helpers.

This module backs ``00_calculus_foundations``: the prerequisite chapter that
builds the intuition ODE/PDE rely on. Everything is reproducible and needs no
downloads. Symbolic helpers use SymPy; numerical ones use NumPy/SciPy.

Design note: the numerical routines deliberately reimplement the "textbook"
definitions (difference quotients, Riemann sums, Simpson's rule) rather than
calling SciPy black boxes, so a learner can read the slope/area being computed.
A few thin SciPy wrappers are provided for the "this is what you use in
practice" contrast.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import sympy as sp
from scipy import integrate

Scalar = Callable[[float], float]


# --------------------------------------------------------------------------- #
# 1-D differentiation — the slope of a tangent as a limit of secant slopes.
# --------------------------------------------------------------------------- #
def secant_slope(f: Scalar, x: float, h: float) -> float:
    """Slope of the secant line through (x, f(x)) and (x+h, f(x+h))."""
    return (f(x + h) - f(x)) / h


def numerical_derivative(f: Scalar, x: float, h: float = 1e-5) -> float:
    """f'(x) via the symmetric (central) difference quotient.

    Central differences cancel the leading error term, so the estimate is
    O(h^2) accurate instead of O(h) for the forward difference.
    """
    return (f(x + h) - f(x - h)) / (2.0 * h)


def second_derivative(f: Scalar, x: float, h: float = 1e-4) -> float:
    """f''(x) via the standard three-point central stencil."""
    return (f(x + h) - 2.0 * f(x) + f(x - h)) / (h * h)


# --------------------------------------------------------------------------- #
# 1-D integration — area / accumulated quantity.
# --------------------------------------------------------------------------- #
def riemann_sum(f: Scalar, a: float, b: float, n: int, rule: str = "mid") -> float:
    """Riemann sum of f over [a, b] with n subintervals.

    rule: "left", "right", or "mid" (midpoint). Midpoint is the most accurate
    of the three for smooth f and is the natural "area of rectangles" picture.
    """
    edges = np.linspace(a, b, n + 1)
    dx = (b - a) / n
    if rule == "left":
        xs = edges[:-1]
    elif rule == "right":
        xs = edges[1:]
    elif rule == "mid":
        xs = 0.5 * (edges[:-1] + edges[1:])
    else:  # pragma: no cover - guards a typo
        raise ValueError("rule must be 'left', 'right', or 'mid'")
    return float(np.sum(f(xs)) * dx)


def trapezoid(f: Scalar, a: float, b: float, n: int) -> float:
    """Composite trapezoidal rule on [a, b] with n subintervals."""
    xs = np.linspace(a, b, n + 1)
    ys = f(xs)
    return float(np.trapezoid(ys, xs))


def simpson(f: Scalar, a: float, b: float, n: int) -> float:
    """Composite Simpson's rule on [a, b]; n must be even."""
    if n % 2 != 0:
        raise ValueError("Simpson's rule needs an even number of subintervals")
    xs = np.linspace(a, b, n + 1)
    ys = f(xs)
    return float(integrate.simpson(ys, x=xs))


def quad(f: Scalar, a: float, b: float) -> float:
    """Definite integral via SciPy's adaptive quadrature (the practical tool)."""
    value, _err = integrate.quad(f, a, b)
    return float(value)


def cumulative_integral(f: Scalar, xs: np.ndarray) -> np.ndarray:
    """F(x) = \\int_{xs[0]}^{x} f(t) dt sampled on xs (FTC demonstration).

    Returns an array the same length as xs with F[0] = 0. Differentiating the
    result numerically should recover f — that is the fundamental theorem.
    """
    xs = np.asarray(xs, dtype=float)
    ys = f(xs)
    return integrate.cumulative_trapezoid(ys, xs, initial=0.0)


# --------------------------------------------------------------------------- #
# Multivariable differentiation — f: R^n -> R.
# --------------------------------------------------------------------------- #
def partial_derivative(f: Callable, point, i: int, h: float = 1e-5) -> float:
    """Partial derivative df/dx_i at ``point`` via central differences."""
    point = np.asarray(point, dtype=float)
    step = np.zeros_like(point)
    step[i] = h
    return float((f(point + step) - f(point - step)) / (2.0 * h))


def gradient(f: Callable, point, h: float = 1e-5) -> np.ndarray:
    """Gradient vector of f at ``point`` — the direction of steepest ascent."""
    point = np.asarray(point, dtype=float)
    return np.array([partial_derivative(f, point, i, h) for i in range(point.size)])


def directional_derivative(f: Callable, point, direction, h: float = 1e-5) -> float:
    """Rate of change of f at ``point`` along (normalized) ``direction``.

    Equals grad(f) . u, where u is the unit vector along ``direction``.
    """
    direction = np.asarray(direction, dtype=float)
    u = direction / np.linalg.norm(direction)
    return float(gradient(f, point, h) @ u)


def hessian(f: Callable, point, h: float = 1e-4) -> np.ndarray:
    """Hessian matrix (second partials) of f at ``point`` via finite differences."""
    point = np.asarray(point, dtype=float)
    n = point.size
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            ei = np.zeros(n)
            ej = np.zeros(n)
            ei[i] = h
            ej[j] = h
            H[i, j] = (
                f(point + ei + ej) - f(point + ei - ej) - f(point - ei + ej) + f(point - ei - ej)
            ) / (4.0 * h * h)
    return 0.5 * (H + H.T)  # symmetrize: H is symmetric for smooth f


# --------------------------------------------------------------------------- #
# Taylor expansion — local polynomial approximation (symbolic, via SymPy).
# --------------------------------------------------------------------------- #
def taylor_series(expr, var, x0: float = 0.0, order: int = 4):
    """Truncated Taylor polynomial of a SymPy ``expr`` about ``x0``.

    Returns a SymPy expression with the big-O term removed, so it can be
    lambdified or pretty-printed directly.
    """
    return sp.series(expr, var, x0, order + 1).removeO()


def taylor_approx(expr, var, x0: float = 0.0, order: int = 4) -> Callable:
    """NumPy-callable f(x) for the order-``order`` Taylor polynomial about x0."""
    poly = taylor_series(expr, var, x0, order)
    return sp.lambdify(var, poly, "numpy")
