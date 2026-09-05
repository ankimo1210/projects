"""Zero-curve representations.

Both curves are parametrised directly by continuously-compounded zero
rates at a fixed set of knot maturities, in *rate space* (never log- or
sqrt-transformed), so negative zero/forward rates are natively supported
while the discount factor ``exp(-z*t)`` stays strictly positive for any
finite ``z`` -- there is no floor to violate.

- ``PiecewiseLinearZeroCurve`` (baseline): linear interpolation of the
  zero rate between knots, flat extrapolation beyond the ends. Simple,
  but produces a kinked (non-smooth) instantaneous forward curve.
- ``SplineZeroCurve`` (advanced): natural cubic spline on cumulative
  log-discount ``y(t) = z(t) * t``, giving a smooth forward curve
  (``f(t) = y'(t)``) and supporting an explicit curvature penalty during
  fitting.
- ``ShiftedCurve`` wraps any base curve with an additive zero-rate shift
  function, used to build parallel and key-rate bumps for risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import CubicSpline


def _atleast_1d_float(t):
    arr = np.asarray(t, dtype=float)
    scalar = arr.ndim == 0
    return np.atleast_1d(arr), scalar


def _restore(arr: np.ndarray, scalar: bool):
    return float(arr[0]) if scalar else arr


@dataclass
class PiecewiseLinearZeroCurve:
    knots: np.ndarray
    zero_rates: np.ndarray

    def __post_init__(self) -> None:
        self.knots = np.asarray(self.knots, dtype=float)
        self.zero_rates = np.asarray(self.zero_rates, dtype=float)
        if self.knots.shape != self.zero_rates.shape:
            raise ValueError("knots and zero_rates must have the same shape")
        if np.any(np.diff(self.knots) <= 0):
            raise ValueError("knots must be strictly increasing")

    def zero_rate(self, t):
        tt, scalar = _atleast_1d_float(t)
        z = np.interp(tt, self.knots, self.zero_rates)
        return _restore(z, scalar)

    def discount(self, t):
        tt, scalar = _atleast_1d_float(t)
        z = np.interp(tt, self.knots, self.zero_rates)
        d = np.exp(-z * tt)
        return _restore(d, scalar)

    def forward_rate(self, t):
        tt, scalar = _atleast_1d_float(t)
        k, z = self.knots, self.zero_rates
        slopes = np.diff(z) / np.diff(k)
        idx = np.clip(np.searchsorted(k, tt, side="right") - 1, 0, len(k) - 2)
        zt = np.interp(tt, k, z)
        f = zt + tt * slopes[idx]
        f = np.where(tt <= k[0], z[0], f)
        f = np.where(tt >= k[-1], z[-1], f)
        return _restore(f, scalar)


@dataclass
class SplineZeroCurve:
    knots: np.ndarray
    zero_rates: np.ndarray
    _spline: CubicSpline = field(init=False, repr=False)
    _dspline: CubicSpline = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.knots = np.asarray(self.knots, dtype=float)
        self.zero_rates = np.asarray(self.zero_rates, dtype=float)
        if self.knots.shape != self.zero_rates.shape:
            raise ValueError("knots and zero_rates must have the same shape")
        if np.any(np.diff(self.knots) <= 0):
            raise ValueError("knots must be strictly increasing")
        y = self.zero_rates * self.knots
        self._spline = CubicSpline(self.knots, y, bc_type="natural", extrapolate=False)
        self._dspline = self._spline.derivative()

    def _y(self, tt: np.ndarray) -> np.ndarray:
        k = self.knots
        tc = np.clip(tt, k[0], k[-1])
        y = self._spline(tc)
        below = tt < k[0]
        above = tt > k[-1]
        if np.any(below):
            f0, y0 = float(self._dspline(k[0])), float(self._spline(k[0]))
            y = np.where(below, y0 + f0 * (tt - k[0]), y)
        if np.any(above):
            fN, yN = float(self._dspline(k[-1])), float(self._spline(k[-1]))
            y = np.where(above, yN + fN * (tt - k[-1]), y)
        return y

    def zero_rate(self, t):
        tt, scalar = _atleast_1d_float(t)
        y = self._y(tt)
        safe_t = np.where(tt == 0.0, 1.0, tt)
        z = y / safe_t
        if np.any(tt == 0.0):
            f0 = float(self._dspline(self.knots[0]))
            z = np.where(tt == 0.0, f0, z)
        return _restore(z, scalar)

    def discount(self, t):
        tt, scalar = _atleast_1d_float(t)
        d = np.exp(-self._y(tt))
        return _restore(d, scalar)

    def forward_rate(self, t):
        tt, scalar = _atleast_1d_float(t)
        k = self.knots
        tc = np.clip(tt, k[0], k[-1])
        f = self._dspline(tc)
        below = tt < k[0]
        above = tt > k[-1]
        f = np.where(below, float(self._dspline(k[0])), f)
        f = np.where(above, float(self._dspline(k[-1])), f)
        return _restore(f, scalar)


@dataclass
class ShiftedCurve:
    """Wraps a base curve, adding ``shift_fn(t)`` to its zero rate."""

    base: object
    shift_fn: object

    def zero_rate(self, t):
        tt, scalar = _atleast_1d_float(t)
        z = np.atleast_1d(np.asarray(self.base.zero_rate(tt), dtype=float)) + np.atleast_1d(
            np.asarray(self.shift_fn(tt), dtype=float)
        )
        return _restore(z, scalar)

    def discount(self, t):
        tt, scalar = _atleast_1d_float(t)
        z = self.zero_rate(tt)
        d = np.exp(-np.atleast_1d(z) * tt)
        return _restore(d, scalar)
