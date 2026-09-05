"""Zero-curve representations.

Two families are provided:

* :class:`PiecewiseLinearZeroCurve` - the simple baseline (linear
  interpolation of continuously compounded zero rates between knots, flat
  extrapolation of the zero rate at both ends).
* :class:`FunctionCurve` - a diagnostic curve built from a known ``D(t)`` for
  pricing verification.
* :class:`BSplineForwardCurve` - the advanced model: the instantaneous forward
  rate is a cubic B-spline, ``log D(t) = -int_0^t f(s) ds`` is obtained
  analytically from the basis antiderivatives, so discount factors are strictly
  positive for any coefficients (negative rates included).

Both expose ``discount``, ``zero`` and ``forward`` on arbitrary maturities and
can be bumped by an additive zero-rate shift function (parallel or key-rate).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np
import pandas as pd
from scipy.interpolate import BSpline

ArrayLike = np.ndarray | float | list


class ZeroCurve(ABC):
    """Abstract continuously compounded zero curve."""

    @abstractmethod
    def log_discount(self, t: ArrayLike) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def forward(self, t: ArrayLike) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    def discount(self, t: ArrayLike) -> np.ndarray:
        return np.exp(self.log_discount(t))

    def zero(self, t: ArrayLike) -> np.ndarray:
        """Continuously compounded zero rate; the t -> 0 limit is the forward at 0."""
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        out = np.empty_like(t_arr)
        positive = t_arr > 1e-12
        out[positive] = -self.log_discount(t_arr[positive]) / t_arr[positive]
        if np.any(~positive):
            out[~positive] = self.forward(np.zeros(int(np.sum(~positive))))
        return out if np.ndim(t) else float(out[0])

    def bumped(self, shift: Callable[[np.ndarray], np.ndarray]) -> "BumpedCurve":
        return BumpedCurve(self, shift)

    def grid_frame(self, grid: np.ndarray) -> pd.DataFrame:
        grid = np.asarray(grid, dtype=float)
        return pd.DataFrame(
            {
                "maturity_years": grid,
                "zero_rate": self.zero(grid),
                "discount_factor": self.discount(grid),
                "forward_rate": self.forward(grid),
            }
        )


class BumpedCurve(ZeroCurve):
    """``z_b(t) = z(t) + shift(t)``; the forward is differentiated numerically."""

    def __init__(self, base: ZeroCurve, shift: Callable[[np.ndarray], np.ndarray]):
        self.base = base
        self.shift = shift

    def log_discount(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        return self.base.log_discount(t_arr) - self.shift(t_arr) * t_arr

    def forward(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        h = 1e-4
        lo = np.maximum(t_arr - h, 0.0)
        hi = t_arr + h
        return -(self.log_discount(hi) - self.log_discount(lo)) / (hi - lo)


class FunctionCurve(ZeroCurve):
    """Diagnostic curve defined directly by a known discount function ``D(t)``.

    Used to verify the pricing formulas against an externally specified curve
    (flat, sloped, humped, negative) independently of any fitted model. If no
    forward function is supplied the forward is a central difference of
    ``log D``.
    """

    def __init__(self, discount_fn: Callable[[np.ndarray], np.ndarray], forward_fn: Callable[[np.ndarray], np.ndarray] | None = None):
        self.discount_fn = discount_fn
        self.forward_fn = forward_fn

    def log_discount(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        d = np.asarray(self.discount_fn(t_arr), dtype=float)
        if np.any(~np.isfinite(d)) or np.any(d <= 0.0):
            raise ValueError("discount function must be finite and strictly positive")
        return np.log(d)

    def forward(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        if self.forward_fn is not None:
            return np.asarray(self.forward_fn(t_arr), dtype=float)
        h = 1e-5
        lo = np.maximum(t_arr - h, 0.0)
        hi = t_arr + h
        return -(self.log_discount(hi) - self.log_discount(lo)) / (hi - lo)


class PiecewiseLinearZeroCurve(ZeroCurve):
    """Linear interpolation in the zero rate; flat zero extrapolation."""

    def __init__(self, knots: np.ndarray, zeros: np.ndarray):
        knots = np.asarray(knots, dtype=float)
        zeros = np.asarray(zeros, dtype=float)
        if knots.ndim != 1 or len(knots) == 0 or len(knots) != len(zeros):
            raise ValueError("knots and zeros must be equal-length 1-D arrays")
        if np.any(np.diff(knots) <= 0) or knots[0] <= 0:
            raise ValueError("knots must be strictly increasing and positive")
        if not np.all(np.isfinite(zeros)):
            raise ValueError("zero rates must be finite")
        self.knots = knots
        self.zeros = zeros

    def zero(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        out = np.interp(t_arr, self.knots, self.zeros)
        return out if np.ndim(t) else float(out[0])

    def log_discount(self, t: ArrayLike) -> np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        return -np.interp(t_arr, self.knots, self.zeros) * t_arr

    def forward(self, t: ArrayLike) -> np.ndarray:
        """f(t) = z(t) + t z'(t); the slope is taken on the segment containing t."""
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        z = np.interp(t_arr, self.knots, self.zeros)
        slope = np.zeros_like(t_arr)
        if len(self.knots) > 1:
            seg = np.clip(np.searchsorted(self.knots, t_arr, side="right") - 1, 0, len(self.knots) - 2)
            dz = np.diff(self.zeros) / np.diff(self.knots)
            inside = (t_arr > self.knots[0]) & (t_arr < self.knots[-1])
            slope[inside] = dz[seg[inside]]
        return z + t_arr * slope


def _gauss_legendre_nodes(a: np.ndarray, b: np.ndarray, n: int = 3) -> tuple[np.ndarray, np.ndarray]:
    x, w = np.polynomial.legendre.leggauss(n)
    half = (b - a) / 2.0
    mid = (a + b) / 2.0
    nodes = (mid[:, None] + half[:, None] * x[None, :]).ravel()
    weights = (half[:, None] * w[None, :]).ravel()
    return nodes, weights


class BSplineForwardCurve(ZeroCurve):
    """Instantaneous forward rate as a clamped cubic B-spline on ``[0, t_max]``.

    Beyond ``t_max`` the forward is extrapolated flat at ``f(t_max)``; before 0
    the forward is ``f(0)`` (never needed in practice).
    """

    def __init__(self, interior_knots: np.ndarray, t_max: float, coeffs: np.ndarray | None = None, degree: int = 3):
        interior = np.asarray(interior_knots, dtype=float)
        if np.any(interior <= 0) or np.any(interior >= t_max):
            raise ValueError("interior knots must lie strictly inside (0, t_max)")
        if np.any(np.diff(interior) <= 0):
            raise ValueError("interior knots must be strictly increasing")
        self.degree = int(degree)
        self.t_max = float(t_max)
        self.interior = interior
        self.knot_vector = np.concatenate([np.zeros(degree + 1), interior, np.full(degree + 1, t_max)])
        self.n_basis = len(self.knot_vector) - degree - 1
        self._basis = [BSpline(self.knot_vector, np.eye(self.n_basis)[k], degree, extrapolate=False) for k in range(self.n_basis)]
        self._anti = [b.antiderivative() for b in self._basis]
        self._second = [b.derivative(2) for b in self._basis]
        self.coeffs = np.zeros(self.n_basis) if coeffs is None else np.asarray(coeffs, dtype=float)
        if len(self.coeffs) != self.n_basis:
            raise ValueError("coefficient vector has the wrong length")

    # --- design matrices -------------------------------------------------
    def design_forward(self, t: ArrayLike) -> np.ndarray:
        """Matrix ``B[j, k] = B_k(t_j)`` with flat extrapolation outside [0, t_max]."""
        t_arr = np.clip(np.atleast_1d(np.asarray(t, dtype=float)), 0.0, self.t_max)
        cols = [np.nan_to_num(b(t_arr), nan=0.0) for b in self._basis]
        return np.column_stack(cols)

    def design_integral(self, t: ArrayLike) -> np.ndarray:
        """Matrix ``A[j, k] = int_0^{t_j} B_k(s) ds`` (flat-forward beyond t_max)."""
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        t_in = np.clip(t_arr, 0.0, self.t_max)
        cols = []
        b_end = self.design_forward(np.array([self.t_max]))[0]
        excess = np.maximum(t_arr - self.t_max, 0.0)
        for k, anti in enumerate(self._anti):
            val = np.nan_to_num(anti(t_in), nan=0.0)
            cols.append(val + excess * b_end[k])
        return np.column_stack(cols)

    def penalty_matrix(self, weight: Callable[[np.ndarray], np.ndarray] | None = None) -> np.ndarray:
        """``Omega[k, l] = int_0^{t_max} w(s) B_k''(s) B_l''(s) ds`` (Gauss quadrature).

        ``weight`` is an optional maturity-dependent roughness weight (default
        1). Cubic B-splines have piecewise-linear second derivatives, so with a
        smooth weight the 4-point rule per knot interval is essentially exact.
        """
        breaks = np.unique(self.knot_vector)
        nodes, weights = _gauss_legendre_nodes(breaks[:-1], breaks[1:], n=4)
        if weight is not None:
            weights = weights * np.asarray(weight(nodes), dtype=float)
        d2 = np.column_stack([np.nan_to_num(s(nodes), nan=0.0) for s in self._second])
        return (d2 * weights[:, None]).T @ d2

    # --- curve interface -------------------------------------------------
    def with_coeffs(self, coeffs: np.ndarray) -> "BSplineForwardCurve":
        new = BSplineForwardCurve.__new__(BSplineForwardCurve)
        new.__dict__.update(self.__dict__)
        new.coeffs = np.asarray(coeffs, dtype=float)
        return new

    def forward(self, t: ArrayLike) -> np.ndarray:
        return self.design_forward(t) @ self.coeffs

    def log_discount(self, t: ArrayLike) -> np.ndarray:
        return -(self.design_integral(t) @ self.coeffs)


def tent_bump(centers: np.ndarray, index: int) -> Callable[[np.ndarray], np.ndarray]:
    """Key-rate bump shape: piecewise-linear tent centred at ``centers[index]``.

    The first tent is flat (=1) before its centre, the last is flat after its
    centre, so the tents form a partition of unity and the key-rate
    sensitivities aggregate to the parallel sensitivity up to convexity.
    """
    centers = np.asarray(centers, dtype=float)
    c = centers[index]
    left = centers[index - 1] if index > 0 else None
    right = centers[index + 1] if index + 1 < len(centers) else None

    def shape(t: np.ndarray) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        out = np.zeros_like(t)
        if left is None:
            out = np.where(t <= c, 1.0, out)
        else:
            out = np.where((t >= left) & (t <= c), (t - left) / (c - left), out)
        if right is None:
            out = np.where(t >= c, 1.0, out)
        else:
            out = np.where((t > c) & (t <= right), (right - t) / (right - c), out)
        return out

    return shape


def parallel_bump(size: float) -> Callable[[np.ndarray], np.ndarray]:
    return lambda t: np.full_like(np.asarray(t, dtype=float), size)
