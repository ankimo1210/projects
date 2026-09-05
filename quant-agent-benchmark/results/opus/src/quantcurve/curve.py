"""Discount-curve objects.

Every curve in this package is defined through its **instantaneous forward
rate** ``f(T)``.  Discount factors follow from

.. math::  D(T) = \\exp\\left(-\\int_0^T f(u)\\,du\\right)

which is strictly positive for *any* finite forward curve.  Negative zero and
forward rates are therefore fully supported while discount factors can never
become non-positive -- the requirement in ``CONVENTIONS.md``.

Two concrete curves are provided:

``PiecewiseFlatForwardCurve``
    Piecewise-constant instantaneous forwards, i.e. log-linear interpolation of
    discount factors.  Used by the bootstrap baseline.

``SplineForwardCurve``
    Natural cubic spline in the instantaneous forward with *flat forward*
    extrapolation outside the knot range.  Used by the penalised estimator.

``BumpedCurve`` applies an additive shift to the **zero** rate and is used for
DV01 and key-rate risk, matching the documented "parallel one-basis-point yield
move" definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline

__all__ = [
    "DiscountCurve",
    "PiecewiseFlatForwardCurve",
    "SplineForwardCurve",
    "BumpedCurve",
    "curve_frame",
]

_EPS = 1.0e-12


class DiscountCurve:
    """Interface shared by every curve object used for pricing."""

    #: Largest maturity supported by directly observed information.
    max_calibrated_maturity: float = 0.0

    def integrated_forward(self, t: np.ndarray | float) -> np.ndarray:
        raise NotImplementedError

    def forward(self, t: np.ndarray | float) -> np.ndarray:
        raise NotImplementedError

    def discount(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        return np.exp(-self.integrated_forward(t))

    def zero(self, t: np.ndarray | float) -> np.ndarray:
        """Continuously compounded zero rate; the limit ``f(0)`` is used at T=0."""
        t = np.asarray(t, dtype=float)
        small = np.abs(t) < _EPS
        safe = np.where(small, 1.0, t)
        z = self.integrated_forward(safe) / safe
        if np.any(small):
            z = np.where(small, self.forward(np.zeros_like(safe)), z)
        return z

    def bumped(self, bump: Callable[[np.ndarray], np.ndarray]) -> "BumpedCurve":
        return BumpedCurve(self, bump)


@dataclass
class PiecewiseFlatForwardCurve(DiscountCurve):
    """Constant instantaneous forward on each interval ``(t_{k-1}, t_k]``.

    ``pillars`` must be strictly increasing and positive; ``forwards[k]`` is the
    forward applying on ``(pillars[k-1], pillars[k]]`` with ``pillars[-1] = 0``
    implied.  Beyond the last pillar the final forward is held flat.
    """

    pillars: np.ndarray
    forwards: np.ndarray
    label: str = "baseline"

    def __post_init__(self) -> None:
        self.pillars = np.asarray(self.pillars, dtype=float)
        self.forwards = np.asarray(self.forwards, dtype=float)
        if self.pillars.ndim != 1 or self.pillars.size == 0:
            raise ValueError("pillars must be a non-empty 1-D array")
        if self.pillars.size != self.forwards.size:
            raise ValueError("pillars and forwards must have equal length")
        if np.any(np.diff(self.pillars) <= 0) or self.pillars[0] <= 0:
            raise ValueError("pillars must be strictly increasing and positive")
        if not np.all(np.isfinite(self.forwards)):
            raise ValueError("forwards must be finite")
        widths = np.diff(np.concatenate(([0.0], self.pillars)))
        self._cum = np.concatenate(([0.0], np.cumsum(self.forwards * widths)))
        self.max_calibrated_maturity = float(self.pillars[-1])

    def integrated_forward(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        idx = np.searchsorted(self.pillars, t, side="left")
        idx = np.clip(idx, 0, self.pillars.size - 1)
        base_t = np.concatenate(([0.0], self.pillars))[idx]
        return self._cum[idx] + self.forwards[idx] * (t - base_t)

    def forward(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        idx = np.clip(np.searchsorted(self.pillars, t, side="left"), 0, self.pillars.size - 1)
        return self.forwards[idx]


@dataclass
class SplineForwardCurve(DiscountCurve):
    """Natural cubic spline instantaneous forward with flat-forward tails.

    Parameters
    ----------
    knots:
        Strictly increasing, positive knot maturities.
    forwards:
        Instantaneous forward rate (decimal) at each knot.
    """

    knots: np.ndarray
    forwards: np.ndarray
    label: str = "advanced"

    def __post_init__(self) -> None:
        self.knots = np.asarray(self.knots, dtype=float)
        self.forwards = np.asarray(self.forwards, dtype=float)
        if self.knots.ndim != 1 or self.knots.size == 0:
            raise ValueError("knots must be a non-empty 1-D array")
        if self.knots.size != self.forwards.size:
            raise ValueError("knots and forwards must have equal length")
        if np.any(np.diff(self.knots) <= 0) or self.knots[0] < 0:
            raise ValueError("knots must be strictly increasing and non-negative")
        if not np.all(np.isfinite(self.forwards)):
            raise ValueError("forwards must be finite")
        self._t0 = float(self.knots[0])
        self._t1 = float(self.knots[-1])
        self._f0 = float(self.forwards[0])
        self._f1 = float(self.forwards[-1])
        if self.knots.size == 1:
            self._spline = None
            self._anti = None
        else:
            # ``natural`` (zero second derivative at both ends) degenerates to the
            # straight line through two knots, so the same boundary condition can
            # be used for every knot count >= 2.
            self._spline = CubicSpline(
                self.knots, self.forwards, bc_type=((2, 0.0), (2, 0.0))
            )
            self._anti = self._spline.antiderivative()
        self.max_calibrated_maturity = self._t1

    def forward(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        if self._spline is None:
            return np.full(t.shape, self._f0)
        clipped = np.clip(t, self._t0, self._t1)
        return np.asarray(self._spline(clipped), dtype=float)

    def integrated_forward(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        front = self._f0 * np.minimum(t, self._t0)
        if self._spline is None:
            return front + self._f0 * np.maximum(t - self._t0, 0.0)
        mid_hi = np.clip(t, self._t0, self._t1)
        middle = np.where(
            t > self._t0,
            np.asarray(self._anti(mid_hi), dtype=float) - float(self._anti(self._t0)),
            0.0,
        )
        tail = self._f1 * np.maximum(t - self._t1, 0.0)
        return front + middle + tail


@dataclass
class BumpedCurve(DiscountCurve):
    """``base`` with an additive shift applied to the continuous zero rate."""

    base: DiscountCurve
    bump: Callable[[np.ndarray], np.ndarray]

    def __post_init__(self) -> None:
        self.max_calibrated_maturity = self.base.max_calibrated_maturity

    def integrated_forward(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        return self.base.integrated_forward(t) + np.asarray(self.bump(t), dtype=float) * t

    def forward(self, t: np.ndarray | float) -> np.ndarray:
        """Numerical derivative of ``d/dT [T * (z(T) + bump(T))]``."""
        t = np.asarray(t, dtype=float)
        h = 1.0e-6
        hi = self.integrated_forward(t + h)
        lo = self.integrated_forward(np.maximum(t - h, 0.0))
        return (hi - lo) / (t + h - np.maximum(t - h, 0.0))


def curve_frame(curve: DiscountCurve, grid: np.ndarray) -> dict[str, np.ndarray]:
    """Zero rates, discount factors and instantaneous forwards on ``grid``."""
    grid = np.asarray(grid, dtype=float)
    if np.any(np.diff(grid) <= 0):
        raise ValueError("grid must be strictly increasing")
    if grid[0] <= 0:
        raise ValueError("grid must start at a positive maturity")
    discount = curve.discount(grid)
    if np.any(~np.isfinite(discount)) or np.any(discount <= 0.0):
        raise ValueError("curve produced a non-positive or non-finite discount factor")
    zero = -np.log(discount) / grid
    forward = curve.forward(grid)
    return {
        "maturity_years": grid,
        "zero_rate": zero,
        "discount_factor": discount,
        "forward_rate": np.asarray(forward, dtype=float),
    }
