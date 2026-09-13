"""Hazard-rate curves and their calibration (Hull 11e, §24.4).

A :class:`HazardCurve` is a piecewise-constant default intensity.  The module
reproduces Example 24.1 (average → forward hazards from yield spreads) and
Example 24.2 (bootstrapping hazards from corporate bond prices with defaults at
the midpoints of six-month intervals).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
from scipy.optimize import brentq


@dataclass(frozen=True)
class HazardCurve:
    """Piecewise-constant hazard rate: ``hazards[i]`` applies on ``(knots[i-1], knots[i]]``.

    ``knots`` are strictly increasing and positive; the last hazard extrapolates flat.
    """

    knots: tuple[float, ...]
    hazards: tuple[float, ...]

    def __post_init__(self) -> None:
        knots = tuple(float(k) for k in self.knots)
        hazards = tuple(float(h) for h in self.hazards)
        if not knots or len(knots) != len(hazards):
            raise ValueError("HazardCurve: knots and hazards must be non-empty and equal length")
        if knots[0] <= 0.0 or any(b <= a for a, b in pairwise(knots)):
            raise ValueError("HazardCurve: knots must be positive and strictly increasing")
        if any(h < 0.0 or not math.isfinite(h) for h in hazards):
            raise ValueError("HazardCurve: hazards must be finite and >= 0")
        object.__setattr__(self, "knots", knots)
        object.__setattr__(self, "hazards", hazards)

    @classmethod
    def from_constant(cls, hazard: float, horizon: float = 100.0) -> HazardCurve:
        """Constant-hazard curve (flat extrapolation makes ``horizon`` immaterial)."""
        return cls((float(horizon),), (float(hazard),))

    def forward_hazard(self, t):
        """Instantaneous hazard at time ``t`` (array-friendly)."""
        t = np.asarray(t, dtype=float)
        idx = np.minimum(np.searchsorted(self.knots, t, side="left"), len(self.knots) - 1)
        return np.asarray(self.hazards)[idx]

    def cumulative_hazard(self, t):
        """∫₀ᵗ λ(u) du for scalar or array ``t`` (t >= 0)."""
        t = np.asarray(t, dtype=float)
        if np.any(t < 0.0):
            raise ValueError("cumulative_hazard: t must be >= 0")
        lower = np.concatenate([[0.0], self.knots[:-1]])
        upper = np.asarray(self.knots)
        hazards = np.asarray(self.hazards)
        total = np.zeros_like(t)
        for lo, hi, lam in zip(lower, upper, hazards, strict=True):
            total = total + lam * np.clip(np.minimum(t, hi) - lo, 0.0, None)
        total = total + hazards[-1] * np.clip(t - upper[-1], 0.0, None)
        return total

    def survival(self, t):
        """S(t) = exp(-∫₀ᵗ λ)."""
        return np.exp(-self.cumulative_hazard(t))

    def default_prob(self, t):
        """Q(t) = 1 - S(t)."""
        return 1.0 - self.survival(t)

    def default_prob_between(self, t0, t1):
        """Unconditional probability of default in (t0, t1]: S(t0) - S(t1)."""
        return self.survival(t0) - self.survival(t1)


def average_hazards_from_spreads(spreads, recovery: float):
    """Average hazard to each tenor from yield spreads: λ̄(T) = s(T)/(1-R) (Hull eq. 24.2)."""
    _check_recovery(recovery)
    return np.asarray(spreads, dtype=float) / (1.0 - recovery)


def forward_hazards_from_average(tenors, average_hazards) -> HazardCurve:
    """Convert average hazards λ̄(Tᵢ) into piecewise-constant forward hazards (Example 24.1)."""
    tenors = np.asarray(tenors, dtype=float)
    average = np.asarray(average_hazards, dtype=float)
    if tenors.shape != average.shape or tenors.ndim != 1:
        raise ValueError("tenors and average_hazards must be 1-D and equal length")
    cumulative = tenors * average
    previous_cum = np.concatenate([[0.0], cumulative[:-1]])
    previous_t = np.concatenate([[0.0], tenors[:-1]])
    forward = (cumulative - previous_cum) / (tenors - previous_t)
    return HazardCurve(tuple(tenors), tuple(forward))


def bond_price_from_yield(
    face: float, coupon_rate: float, maturity: float, yield_cc: float, freq: int = 2
) -> float:
    """Price of a coupon bond from a continuously compounded yield (coupon just paid)."""
    n = _periods(maturity, freq)
    coupon = face * coupon_rate / freq
    times = np.arange(1, n + 1) / freq
    return float(np.sum(coupon * np.exp(-yield_cc * times)) + face * math.exp(-yield_cc * maturity))


def risk_free_bond_price(
    face: float, coupon_rate: float, maturity: float, r: float, freq: int = 2
) -> float:
    """Value of the bond's promised cash flows discounted at the risk-free rate ``r``."""
    return bond_price_from_yield(face, coupon_rate, maturity, r, freq)


def forward_risk_free_value(
    face: float, coupon_rate: float, maturity: float, r: float, tau: float, freq: int = 2
) -> float:
    """Risk-free value at time ``tau`` of the cash flows still outstanding after ``tau``."""
    n = _periods(maturity, freq)
    coupon = face * coupon_rate / freq
    times = np.arange(1, n + 1) / freq
    remaining = times[times > tau + 1e-12]
    return float(
        np.sum(coupon * np.exp(-r * (remaining - tau))) + face * math.exp(-r * (maturity - tau))
    )


def expected_default_loss_pv(
    curve: HazardCurve,
    face: float,
    coupon_rate: float,
    maturity: float,
    r: float,
    recovery: float,
    freq: int = 2,
    default_step: float = 0.5,
) -> float:
    """PV of expected default losses on a bond, defaults at midpoints of ``default_step`` intervals.

    Loss on default at τ is (risk-free forward value at τ − R·face) discounted to today
    (Hull Example 24.2: 63.33 and 60.40 for the 1-year bond).
    """
    _check_recovery(recovery)
    n = round(maturity / default_step)
    if n <= 0 or abs(n * default_step - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of default_step intervals")
    total = 0.0
    for i in range(1, n + 1):
        t0, t1 = (i - 1) * default_step, i * default_step
        tau = 0.5 * (t0 + t1)
        forward_value = forward_risk_free_value(face, coupon_rate, maturity, r, tau, freq)
        loss = (forward_value - recovery * face) * math.exp(-r * tau)
        total += float(curve.default_prob_between(t0, t1)) * loss
    return total


@dataclass(frozen=True)
class BondBootstrapResult:
    """Bootstrapped hazard curve with the per-bond expected-loss PV targets it matched."""

    curve: HazardCurve
    expected_loss_pv: tuple[float, ...]
    risk_free_prices: tuple[float, ...]


def bootstrap_from_bonds(
    bond_prices,
    coupon_rate: float,
    maturities,
    r: float,
    recovery: float,
    face: float = 100.0,
    freq: int = 2,
    default_step: float = 0.5,
) -> BondBootstrapResult:
    """Solve piecewise-constant hazards so each bond's expected default loss matches its price gap.

    Bonds are processed in maturity order; the hazard on (Tᵢ₋₁, Tᵢ] is found by
    ``brentq`` so that ``expected_default_loss_pv`` equals risk-free price − market price
    (Hull Example 24.2: 2.46%, 3.48%, 3.74%).
    """
    _check_recovery(recovery)
    prices = np.asarray(bond_prices, dtype=float)
    tenors = np.asarray(maturities, dtype=float)
    if prices.shape != tenors.shape or prices.ndim != 1 or prices.size == 0:
        raise ValueError("bond_prices and maturities must be 1-D and equal length")
    if np.any(np.diff(tenors) <= 0.0) or tenors[0] <= 0.0:
        raise ValueError("maturities must be positive and strictly increasing")
    risk_free = [risk_free_bond_price(face, coupon_rate, float(T), r, freq) for T in tenors]
    targets = [rf - p for rf, p in zip(risk_free, prices, strict=True)]
    hazards: list[float] = []
    for i, T in enumerate(tenors):

        def gap(h: float, i: int = i, T: float = float(T)) -> float:
            trial = HazardCurve(tuple(tenors[: i + 1]), (*hazards, h))
            pv = expected_default_loss_pv(
                trial, face, coupon_rate, T, r, recovery, freq, default_step
            )
            return pv - targets[i]

        try:
            hazards.append(float(brentq(gap, 1e-10, 5.0, xtol=1e-14)))
        except ValueError as exc:
            raise ValueError(
                f"bootstrap_from_bonds: no hazard in (0, 5] reprices bond {i}"
            ) from exc
    curve = HazardCurve(tuple(tenors), tuple(hazards))
    return BondBootstrapResult(curve, tuple(targets), tuple(risk_free))


def _check_recovery(recovery: float) -> None:
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")


def _periods(maturity: float, freq: int) -> int:
    n = round(maturity * freq)
    if n <= 0 or abs(n / freq - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of coupon periods")
    return n
