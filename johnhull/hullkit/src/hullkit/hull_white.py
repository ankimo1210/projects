"""One-factor Hull–White pricing and exact Gaussian simulation.

The implementation uses ``r_t = x_t + phi(t)`` with a zero-mean Ornstein–Uhlenbeck
factor.  Curves are the ``(times, continuously_compounded_zero_rates)`` tuples used
throughout :mod:`hullkit.rates`.  Prices returned by this module are time-zero
nominal prices unless a function explicitly accepts a future state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq, least_squares
from scipy.special import ndtr

from . import rates

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class HullWhiteParams:
    """Constant one-factor Hull–White mean reversion and volatility."""

    mean_reversion: float
    volatility: float

    def validate(self) -> None:
        """Reject non-finite, non-positive reversion or negative volatility."""
        if not math.isfinite(self.mean_reversion) or self.mean_reversion <= 0.0:
            raise ValueError("mean_reversion must be finite and positive")
        if not math.isfinite(self.volatility) or self.volatility < 0.0:
            raise ValueError("volatility must be finite and non-negative")


@dataclass(frozen=True)
class HullWhiteSwaption:
    """European swaption represented as an option on a unit-notional coupon bond.

    ``fixed_cashflows`` contains fixed coupons and the terminal notional.  A
    receiver swaption is a call on that coupon bond with strike one; a payer is
    the corresponding put.
    """

    expiry: float
    payment_times: tuple[float, ...]
    fixed_cashflows: tuple[float, ...]
    option_type: str = "receiver"

    def validate(self) -> None:
        """Validate ordering, positive cash flows, and payer/receiver direction."""
        if not math.isfinite(self.expiry) or self.expiry < 0.0:
            raise ValueError("swaption expiry must be finite and non-negative")
        times = np.asarray(self.payment_times, dtype=float)
        cashflows = np.asarray(self.fixed_cashflows, dtype=float)
        if (
            times.ndim != 1
            or cashflows.ndim != 1
            or not times.size
            or times.size != cashflows.size
        ):
            raise ValueError("payment_times and fixed_cashflows must be equal non-empty vectors")
        if not np.all(np.isfinite(times)) or not np.all(np.isfinite(cashflows)):
            raise ValueError("swaption times and cash flows must be finite")
        if np.any(np.diff(times) <= 0.0) or np.any(times <= self.expiry):
            raise ValueError("swaption payments must be ordered strictly after expiry")
        if np.any(cashflows <= 0.0):
            raise ValueError("Jamshidian decomposition requires positive fixed cash flows")
        if self.option_type not in {"receiver", "payer"}:
            raise ValueError("option_type must be 'receiver' or 'payer'")


def hw_b(t, maturity, mean_reversion):
    r"""Hull–White loading ``B(t,T)=(1-exp(-a(T-t)))/a``."""
    t = float(t)
    maturity = float(maturity)
    mean_reversion = float(mean_reversion)
    if not all(map(math.isfinite, (t, maturity, mean_reversion))):
        raise ValueError("Hull-White times and mean reversion must be finite")
    if t < 0.0 or maturity < t:
        raise ValueError("Hull-White times must satisfy 0 <= t <= maturity")
    if mean_reversion <= 0.0:
        raise ValueError("mean_reversion must be positive")
    return -math.expm1(-mean_reversion * (maturity - t)) / mean_reversion


def hw_phi(t, curve, params):
    r"""Deterministic shift that fits the initial curve exactly.

    For constant ``a`` and ``sigma``,

    .. math::
       \phi(t)=f^M(0,t)+\frac{\sigma^2}{2a^2}(1-e^{-at})^2.
    """
    params.validate()
    t = float(t)
    if not math.isfinite(t) or t < 0.0:
        raise ValueError("shift time must be finite and non-negative")
    a = params.mean_reversion
    sigma = params.volatility
    adjustment = sigma**2 * (-math.expm1(-a * t)) ** 2 / (2.0 * a**2)
    return rates.instantaneous_forward(t, curve) + adjustment


def hw_discount_bond(t, maturity, state, curve, params):
    r"""Price ``P(t,T)`` conditional on the zero-mean factor ``x_t=state``."""
    params.validate()
    t = float(t)
    maturity = float(maturity)
    state = float(state)
    if not all(map(math.isfinite, (t, maturity, state))):
        raise ValueError("bond inputs must be finite")
    if t < 0.0 or maturity < t:
        raise ValueError("bond times must satisfy 0 <= t <= maturity")
    if maturity == t:
        return 1.0
    a = params.mean_reversion
    sigma = params.volatility
    b = hw_b(t, maturity, a)
    variance_adjustment = sigma**2 * (-math.expm1(-2.0 * a * t)) * b**2 / (4.0 * a)
    return rates.forward_discount(t, maturity, curve) * math.exp(
        -b * state - variance_adjustment
    )


def hw_exact_transition(state, start, end, params, *, normal=0.0):
    """Exact OU transition from ``start`` to ``end`` for supplied standard normals."""
    params.validate()
    start = float(start)
    end = float(end)
    if not math.isfinite(start) or not math.isfinite(end) or start < 0.0 or end < start:
        raise ValueError("transition times must satisfy 0 <= start <= end")
    state_array = np.asarray(state, dtype=float)
    normal_array = np.asarray(normal, dtype=float)
    if not np.all(np.isfinite(state_array)) or not np.all(np.isfinite(normal_array)):
        raise ValueError("transition state and normal draws must be finite")
    dt = end - start
    decay = math.exp(-params.mean_reversion * dt)
    variance = (
        params.volatility**2
        * (-math.expm1(-2.0 * params.mean_reversion * dt))
        / (2.0 * params.mean_reversion)
    )
    result = state_array * decay + math.sqrt(max(variance, 0.0)) * normal_array
    return float(result) if result.ndim == 0 else result


def simulate_hw_paths(times, initial_state, params, *, n_paths=10_000, seed=42):
    """Simulate exact zero-mean Hull–White factor paths on an arbitrary time grid."""
    params.validate()
    grid = np.asarray(times, dtype=float)
    if grid.ndim != 1 or not grid.size or not np.all(np.isfinite(grid)):
        raise ValueError("times must be a non-empty finite one-dimensional grid")
    if grid[0] < 0.0 or np.any(np.diff(grid) <= 0.0):
        raise ValueError("times must be non-negative and strictly increasing")
    if not isinstance(n_paths, int) or n_paths <= 0:
        raise ValueError("n_paths must be a positive integer")
    initial_state = float(initial_state)
    if not math.isfinite(initial_state):
        raise ValueError("initial_state must be finite")
    rng = np.random.default_rng(seed)
    paths = np.empty((n_paths, grid.size), dtype=float)
    paths[:, 0] = initial_state
    for index in range(1, grid.size):
        paths[:, index] = hw_exact_transition(
            paths[:, index - 1],
            grid[index - 1],
            grid[index],
            params,
            normal=rng.standard_normal(n_paths),
        )
    return paths


def _option_direction(option_type):
    if option_type == "call":
        return 1.0
    if option_type == "put":
        return -1.0
    raise ValueError("option_type must be 'call' or 'put'")


def _bond_option_volatility(expiry, bond_maturity, params):
    a = params.mean_reversion
    variance = params.volatility**2 * (-math.expm1(-2.0 * a * expiry)) / (2.0 * a)
    return hw_b(expiry, bond_maturity, a) * math.sqrt(max(variance, 0.0))


def hw_zcb_option(expiry, bond_maturity, strike, curve, params, *, option_type="call"):
    """Time-zero European option on a zero-coupon bond in Hull–White 1F."""
    params.validate()
    expiry = float(expiry)
    bond_maturity = float(bond_maturity)
    strike = float(strike)
    direction = _option_direction(option_type)
    if not all(map(math.isfinite, (expiry, bond_maturity, strike))):
        raise ValueError("bond-option inputs must be finite")
    if expiry < 0.0 or bond_maturity < expiry or strike < 0.0:
        raise ValueError("option inputs require 0 <= expiry <= maturity and strike >= 0")
    p_expiry = rates.discount_factor(expiry, curve)
    p_maturity = rates.discount_factor(bond_maturity, curve)
    volatility = _bond_option_volatility(expiry, bond_maturity, params)
    intrinsic_forward = direction * (p_maturity - strike * p_expiry)
    if volatility <= 1e-15 or strike == 0.0:
        return max(intrinsic_forward, 0.0)
    d1 = math.log(p_maturity / (strike * p_expiry)) / volatility + 0.5 * volatility
    d2 = d1 - volatility
    return direction * (
        p_maturity * float(ndtr(direction * d1))
        - strike * p_expiry * float(ndtr(direction * d2))
    )


def hw_jamshidian_swaption(spec, curve, params):
    """Price a European payer or receiver swaption by Jamshidian decomposition."""
    spec.validate()
    params.validate()
    times = np.asarray(spec.payment_times, dtype=float)
    cashflows = np.asarray(spec.fixed_cashflows, dtype=float)

    def coupon_bond_minus_one(state):
        prices = np.asarray(
            [hw_discount_bond(spec.expiry, time, state, curve, params) for time in times]
        )
        return float(np.dot(cashflows, prices) - 1.0)

    lower, upper = -0.05, 0.05
    for _ in range(20):
        if coupon_bond_minus_one(lower) > 0.0 and coupon_bond_minus_one(upper) < 0.0:
            break
        lower *= 2.0
        upper *= 2.0
    else:
        raise ValueError("could not bracket the Jamshidian root")
    root = brentq(coupon_bond_minus_one, lower, upper, xtol=1e-14, rtol=1e-14)
    strikes = [hw_discount_bond(spec.expiry, time, root, curve, params) for time in times]
    bond_option_type = "call" if spec.option_type == "receiver" else "put"
    return float(
        sum(
            cashflow
            * hw_zcb_option(
                spec.expiry,
                time,
                strike,
                curve,
                params,
                option_type=bond_option_type,
            )
            for time, cashflow, strike in zip(times, cashflows, strikes, strict=True)
        )
    )


def calibrate_hw1f(specs, market_prices, curve, initial_guess=(0.1, 0.01)):
    """Calibrate constant ``(a, sigma)`` to synthetic European swaption prices."""
    specs = tuple(specs)
    prices = np.asarray(market_prices, dtype=float)
    if not specs or prices.ndim != 1 or prices.size != len(specs):
        raise ValueError("specs and market_prices must be equal non-empty vectors")
    if not np.all(np.isfinite(prices)) or np.any(prices < 0.0):
        raise ValueError("market prices must be finite and non-negative")
    for spec in specs:
        spec.validate()
    initial = np.asarray(initial_guess, dtype=float)
    if initial.shape != (2,) or not np.all(np.isfinite(initial)) or np.any(initial <= 0.0):
        raise ValueError("initial_guess must contain positive mean reversion and volatility")
    scale = max(float(np.max(prices)), 1e-8)

    def residuals(log_parameters):
        candidate = HullWhiteParams(*np.exp(log_parameters))
        model = np.asarray([hw_jamshidian_swaption(spec, curve, candidate) for spec in specs])
        return (model - prices) / scale

    result = least_squares(
        residuals,
        np.log(initial),
        bounds=(np.log([1e-5, 1e-7]), np.log([5.0, 1.0])),
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
        max_nfev=2_000,
    )
    if not result.success:
        raise ValueError(f"Hull-White calibration failed: {result.message}")
    return HullWhiteParams(*np.exp(result.x))
