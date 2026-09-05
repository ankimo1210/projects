"""Typed market-observation records and priceable instrument definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .conventions import DEFAULT_STUB_RULE, StubRule, ois_accruals, schedule_times

INSTRUMENT_TYPES = ("deposit", "ois_swap", "bond")
RATE_TYPES = ("deposit", "ois_swap")

#: Notional conventions for PV / DV01 (CONVENTIONS.md).
NOTIONAL = {"deposit": 1_000_000.0, "ois_swap": 1_000_000.0, "bond": 100.0}


@dataclass(frozen=True)
class MarketObservation:
    obs_id: str
    instrument_id: str
    source: str
    timestamp: datetime
    instrument_type: str
    maturity_years: float
    coupon_rate: float | None
    payment_frequency: int
    quote_type: str
    quote_value: float | None
    quote_unit: str
    bid: float | None
    ask: float | None
    liquidity_score: float

    def validate_basic(self) -> None:
        if self.instrument_type not in {"deposit", "ois_swap", "bond"}:
            raise ValueError(f"unsupported instrument type: {self.instrument_type}")
        if self.maturity_years <= 0:
            raise ValueError("maturity_years must be positive")
        if self.payment_frequency <= 0:
            raise ValueError("payment_frequency must be positive")
        if not 0.0 <= self.liquidity_score <= 1.0:
            raise ValueError("liquidity_score must be in [0, 1]")


@dataclass(frozen=True)
class Instrument:
    """A priceable instrument with its market quote in *decimal* units.

    ``quote``: deposits and OIS in decimal annual rate (0.02 = 2%), bonds in
    price points per 100 face. ``times`` are the cash-flow (or accrual) times,
    ``amounts``/``alphas`` the corresponding coefficients:

    * deposit: ``times = [T]``.
    * ois_swap: fixed-leg payment times and accruals ``alphas``.
    * bond: coupon times (last equals maturity) and coupon ``amounts`` per 100
      face; principal 100 at maturity is added at pricing time.
    """

    instrument_id: str
    instrument_type: str
    maturity: float
    quote: float
    times: np.ndarray
    alphas: np.ndarray
    amounts: np.ndarray
    frequency: int = 1
    coupon_rate: float = 0.0

    @property
    def is_rate(self) -> bool:
        return self.instrument_type in RATE_TYPES

    @property
    def notional(self) -> float:
        return NOTIONAL[self.instrument_type]


def build_instrument(
    instrument_id: str,
    instrument_type: str,
    maturity: float,
    quote: float,
    frequency: int = 1,
    coupon_rate: float | None = None,
    stub_rule: StubRule = DEFAULT_STUB_RULE,
) -> Instrument:
    """Construct the cash-flow representation of one instrument.

    Quotes must already be in decimal units (rates) or points (bond prices).
    """
    if instrument_type not in INSTRUMENT_TYPES:
        raise ValueError(f"unsupported instrument type: {instrument_type}")
    if not np.isfinite(maturity) or maturity <= 0:
        raise ValueError(f"{instrument_id}: maturity must be positive and finite")
    if not np.isfinite(quote):
        raise ValueError(f"{instrument_id}: quote must be finite")
    frequency = int(frequency)
    if instrument_type == "deposit":
        times = np.array([float(maturity)])
        return Instrument(instrument_id, instrument_type, float(maturity), float(quote), times, np.array([float(maturity)]), np.array([1.0]), 1, 0.0)
    if instrument_type == "ois_swap":
        if frequency <= 0:
            raise ValueError(f"{instrument_id}: payment_frequency must be positive")
        times = schedule_times(maturity, frequency, stub_rule)
        alphas = ois_accruals(times, frequency, stub_rule)
        return Instrument(instrument_id, instrument_type, float(maturity), float(quote), times, alphas, np.ones(len(times)), frequency, 0.0)
    # bond
    if coupon_rate is None or not np.isfinite(coupon_rate):
        raise ValueError(f"{instrument_id}: bond requires a finite coupon_rate")
    if frequency <= 0:
        raise ValueError(f"{instrument_id}: payment_frequency must be positive")
    times = schedule_times(maturity, frequency, stub_rule)
    coupon = 100.0 * float(coupon_rate) / frequency
    amounts = np.full(len(times), coupon)
    return Instrument(instrument_id, instrument_type, float(maturity), float(quote), times, np.full(len(times), 1.0 / frequency), amounts, frequency, float(coupon_rate))


def cash_flows(inst: Instrument) -> tuple[np.ndarray, np.ndarray]:
    """Fixed cash-flow times and amounts of the *receiver* position.

    Deposits: receive ``1 + rT`` at maturity per unit notional.
    OIS: fixed coupons ``r alpha_i`` at each fixed payment plus, for PV
    purposes, the floating leg is represented as ``1 - D(T)`` separately.
    Bonds: coupons and principal per 100 face.
    """
    if inst.instrument_type == "deposit":
        return inst.times, np.array([1.0 + inst.quote * inst.maturity])
    if inst.instrument_type == "ois_swap":
        return inst.times, inst.quote * inst.alphas
    amounts = inst.amounts.copy()
    amounts[-1] += 100.0
    return inst.times, amounts
