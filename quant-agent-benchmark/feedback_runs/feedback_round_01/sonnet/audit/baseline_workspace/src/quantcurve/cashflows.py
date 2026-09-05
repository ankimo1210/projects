"""Cash-flow schedule construction and instrument pricing.

Every instrument type is priced from a single ``discount_fn`` callable
mapping a maturity in years to a discount factor, so the same functions
serve calibration, repricing diagnostics, and risk (via bumped curves).

Schedule conventions (see ``market_data/CONVENTIONS.md``):

- Deposits have a single cash flow at ``T`` (simple interest).
- OIS swaps and bonds pay every ``1/payment_frequency`` years. Payments
  are generated *forward* from the valuation date (t=0) at multiples of
  the period, with a short stub inserted at the final payment if ``T``
  is not an exact multiple of the period. This keeps both legs' payment
  dates aligned to the same anchor (t=0) and only ever creates a single,
  final stub period, which is the assumption documented in MODEL_RISKS.md.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

_EPS = 1e-9


def payment_times(maturity_years: float, frequency: int) -> np.ndarray:
    """Payment times (years from valuation date) for a regular fixed leg.

    Regular payments fall every ``1/frequency`` years; a stub is appended
    at ``maturity_years`` if it is not an exact multiple of the period.
    """
    if maturity_years <= 0:
        raise ValueError("maturity_years must be positive")
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    step = 1.0 / frequency
    times: list[float] = []
    i = 1
    while i * step < maturity_years - _EPS:
        times.append(i * step)
        i += 1
    if not times or abs(times[-1] - maturity_years) > _EPS:
        times.append(maturity_years)
    return np.asarray(times, dtype=float)


def year_fractions(times: np.ndarray) -> np.ndarray:
    """ACT/365F-style year fractions between consecutive payment times, from t=0."""
    prev = np.concatenate(([0.0], times[:-1]))
    return times - prev


def deposit_model_rate(discount_fn, maturity_years: float) -> float:
    """Simple annual rate implied by the curve for a deposit maturing at T."""
    d = float(discount_fn(maturity_years))
    return (1.0 / d - 1.0) / maturity_years


def deposit_pv(discount_fn, maturity_years: float, market_rate: float, notional: float = 1_000_000.0) -> float:
    """Receiver-fixed PV: lend `notional` at t=0, receive notional*(1+rT) at T."""
    d = float(discount_fn(maturity_years))
    return notional * ((1.0 + market_rate * maturity_years) * d - 1.0)


def swap_model_par_rate(discount_fn, maturity_years: float, frequency: int) -> float:
    """Par fixed rate solving r * sum(alpha_i D(t_i)) = 1 - D(T)."""
    times = payment_times(maturity_years, frequency)
    alphas = year_fractions(times)
    discounts = np.asarray([discount_fn(t) for t in times], dtype=float)
    annuity = float(np.sum(alphas * discounts))
    if annuity <= 0:
        raise FloatingPointError("non-positive annuity encountered in swap pricing")
    return (1.0 - discounts[-1]) / annuity


def swap_pv(discount_fn, maturity_years: float, frequency: int, market_rate: float, notional: float = 1_000_000.0) -> float:
    """Receiver-fixed swap PV: receive fixed annuity, pay float leg (= 1 - D(T))."""
    times = payment_times(maturity_years, frequency)
    alphas = year_fractions(times)
    discounts = np.asarray([discount_fn(t) for t in times], dtype=float)
    annuity = float(np.sum(alphas * discounts))
    return notional * (market_rate * annuity - (1.0 - discounts[-1]))


def bond_cashflows(maturity_years: float, coupon_rate: float, frequency: int, face: float = 100.0):
    """Payment times (from t=0) and level cash-flow amounts for a bullet bond."""
    times = payment_times(maturity_years, frequency)
    coupon_amt = coupon_rate / frequency * face
    amounts = np.full(times.shape, coupon_amt)
    amounts[-1] += face
    return times, amounts


def bond_model_price(discount_fn, maturity_years: float, coupon_rate: float, frequency: int, face: float = 100.0) -> float:
    times, amounts = bond_cashflows(maturity_years, coupon_rate, frequency, face)
    discounts = np.asarray([discount_fn(t) for t in times], dtype=float)
    return float(np.sum(amounts * discounts))


def bond_pv(discount_fn, maturity_years: float, coupon_rate: float, frequency: int, market_price: float, face: float = 100.0) -> float:
    """Receiver-fixed PV of holding a bond bought at `market_price`."""
    return bond_model_price(discount_fn, maturity_years, coupon_rate, frequency, face) - market_price


def bond_ytm(maturity_years: float, coupon_rate: float, frequency: int, price: float, face: float = 100.0) -> float:
    """Standalone yield-to-maturity under the bond's own periodic compounding.

    Used only for data-quality reference checks (independent of the fitted
    discount curve), never for the primary curve calibration.
    """
    times, amounts = bond_cashflows(maturity_years, coupon_rate, frequency, face)

    def price_at_yield(y: float) -> float:
        discounts = (1.0 + y / frequency) ** (-frequency * times)
        return float(np.sum(amounts * discounts)) - price

    for lo, hi in ((-0.9 * frequency, 5.0), (-0.999 * frequency, 50.0)):
        try:
            return brentq(price_at_yield, lo, hi, xtol=1e-10, maxiter=500)
        except ValueError:
            continue
    raise ValueError("could not bracket a yield-to-maturity solution")
