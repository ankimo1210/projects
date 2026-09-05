"""Positive-discount zero-curve representations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator


ArrayLike = float | np.ndarray


@dataclass(frozen=True)
class ZeroCurve:
    """Continuously compounded zero curve with flat-zero extrapolation.

    Positivity follows from D(T)=exp(-T*z(T)); discount monotonicity is not
    imposed, so negative-rate regimes remain representable.
    """

    knots: np.ndarray
    rates: np.ndarray
    method: str = "cubic"

    def __post_init__(self) -> None:
        knots = np.asarray(self.knots, dtype=float)
        rates = np.asarray(self.rates, dtype=float)
        if knots.ndim != 1 or rates.shape != knots.shape or len(knots) < 2:
            raise ValueError("matching one-dimensional knots and rates required")
        if np.any(np.diff(knots) <= 0) or knots[0] < 0:
            raise ValueError("knots must be strictly increasing and non-negative")
        if not np.all(np.isfinite(rates)):
            raise ValueError("rates must be finite")
        object.__setattr__(self, "knots", knots)
        object.__setattr__(self, "rates", rates)
        if self.method == "cubic":
            interp = CubicSpline(knots, rates, bc_type="natural", extrapolate=False)
        elif self.method == "pchip":
            interp = PchipInterpolator(knots, rates, extrapolate=False)
        else:
            raise ValueError(f"unsupported interpolation method: {self.method}")
        object.__setattr__(self, "_interpolator", interp)

    def zero(self, maturity_years: ArrayLike) -> ArrayLike:
        scalar = np.isscalar(maturity_years)
        t = np.atleast_1d(np.asarray(maturity_years, dtype=float))
        if np.any(t < 0) or not np.all(np.isfinite(t)):
            raise ValueError("finite non-negative maturities required")
        clipped = np.clip(t, self.knots[0], self.knots[-1])
        values = np.asarray(self._interpolator(clipped), dtype=float)
        values[t <= self.knots[0]] = self.rates[0]
        values[t >= self.knots[-1]] = self.rates[-1]
        return float(values[0]) if scalar else values

    def zero_derivative(self, maturity_years: ArrayLike) -> ArrayLike:
        scalar = np.isscalar(maturity_years)
        t = np.atleast_1d(np.asarray(maturity_years, dtype=float))
        clipped = np.clip(t, self.knots[0], self.knots[-1])
        values = np.asarray(self._interpolator.derivative(1)(clipped), dtype=float)
        values[(t <= self.knots[0]) | (t >= self.knots[-1])] = 0.0
        return float(values[0]) if scalar else values

    def second_derivative(self, maturity_years: ArrayLike) -> ArrayLike:
        scalar = np.isscalar(maturity_years)
        t = np.atleast_1d(np.asarray(maturity_years, dtype=float))
        clipped = np.clip(t, self.knots[0], self.knots[-1])
        values = np.asarray(self._interpolator.derivative(2)(clipped), dtype=float)
        values[(t <= self.knots[0]) | (t >= self.knots[-1])] = 0.0
        return float(values[0]) if scalar else values

    def discount(
        self,
        maturity_years: ArrayLike,
        zero_bump: Callable[[np.ndarray], np.ndarray] | None = None,
    ) -> ArrayLike:
        scalar = np.isscalar(maturity_years)
        t = np.atleast_1d(np.asarray(maturity_years, dtype=float))
        z = np.asarray(self.zero(t), dtype=float)
        if zero_bump is not None:
            bump = np.asarray(zero_bump(t), dtype=float)
            if bump.shape != t.shape or not np.all(np.isfinite(bump)):
                raise ValueError("zero bump must return finite values matching maturity shape")
            z = z + bump
        values = np.exp(np.clip(-z * t, -700.0, 700.0))
        return float(values[0]) if scalar else values

    def forward(self, maturity_years: ArrayLike) -> ArrayLike:
        scalar = np.isscalar(maturity_years)
        t = np.atleast_1d(np.asarray(maturity_years, dtype=float))
        values = np.asarray(self.zero(t)) + t * np.asarray(self.zero_derivative(t))
        return float(values[0]) if scalar else values

