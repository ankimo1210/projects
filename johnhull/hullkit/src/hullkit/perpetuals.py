"""Deterministic perpetual-futures mechanics for teaching and audit.

The module keeps three price concepts separate: an external ``index_price``,
the venue's risk-management ``mark_price``, and the most recent traded
``last_price``.  Cash-flow signs are always from the position holder's point
of view: positive is a receipt and negative is a payment.

The routines deliberately model contract arithmetic and funding only.  They
do not connect to an exchange, download data, or claim to reproduce any one
venue's rulebook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

ContractKind = Literal["linear", "inverse", "quanto"]
PositionSide = Literal["long", "short"]


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _side_sign(side: PositionSide) -> float:
    if side == "long":
        return 1.0
    if side == "short":
        return -1.0
    raise ValueError("side must be 'long' or 'short'")


@dataclass(frozen=True)
class MarketSnapshot:
    """Index, mark, and last prices observed at a timestamp.

    ``timestamp`` and ``oracle_timestamp`` use the same caller-selected unit
    (normally seconds).  Their difference is the observable oracle age.
    """

    index_price: float
    mark_price: float
    last_price: float
    timestamp: float = 0.0
    oracle_timestamp: float = 0.0

    def __post_init__(self) -> None:
        _positive(self.index_price, "index_price")
        _positive(self.mark_price, "mark_price")
        _positive(self.last_price, "last_price")
        if not np.isfinite(self.timestamp) or not np.isfinite(self.oracle_timestamp):
            raise ValueError("timestamps must be finite")
        if self.oracle_timestamp > self.timestamp:
            raise ValueError("oracle_timestamp cannot be in the future")

    @property
    def oracle_age(self) -> float:
        return float(self.timestamp - self.oracle_timestamp)

    @property
    def mark_index_basis(self) -> float:
        return float(self.mark_price / self.index_price - 1.0)

    @property
    def last_index_dislocation(self) -> float:
        return float(self.last_price / self.index_price - 1.0)


def position_pnl(
    contract: ContractKind,
    entry_price: float,
    exit_price: float,
    quantity: float = 1.0,
    *,
    side: PositionSide = "long",
    contract_multiplier: float = 1.0,
    settlement_fx: float = 1.0,
) -> float:
    """PnL for linear, inverse, or quanto contracts.

    - ``linear`` returns quote-currency PnL
      ``q * multiplier * (exit - entry)``.
    - ``inverse`` returns base-asset PnL
      ``q * multiplier * (1 / entry - 1 / exit)``.
    - ``quanto`` returns settlement-currency PnL using the fixed conversion
      ``settlement_fx``.

    ``quantity`` is a non-negative contract count; direction is expressed by
    ``side`` so that a negative quantity cannot silently reverse the sign.
    """

    entry = _positive(entry_price, "entry_price")
    exit_ = _positive(exit_price, "exit_price")
    multiplier = _positive(contract_multiplier, "contract_multiplier")
    fx = _positive(settlement_fx, "settlement_fx")
    quantity = float(quantity)
    if not np.isfinite(quantity) or quantity < 0.0:
        raise ValueError("quantity must be finite and non-negative")
    signed_quantity = _side_sign(side) * quantity

    if contract == "linear":
        pnl = signed_quantity * multiplier * (exit_ - entry)
    elif contract == "inverse":
        pnl = signed_quantity * multiplier * (1.0 / entry - 1.0 / exit_)
    elif contract == "quanto":
        pnl = signed_quantity * multiplier * fx * (exit_ - entry)
    else:
        raise ValueError("contract must be 'linear', 'inverse', or 'quanto'")
    return float(pnl)


def position_notional(
    contract: ContractKind,
    price: float,
    quantity: float = 1.0,
    *,
    contract_multiplier: float = 1.0,
    settlement_fx: float = 1.0,
) -> float:
    """Absolute risk notional in each contract's settlement convention."""

    price = _positive(price, "price")
    multiplier = _positive(contract_multiplier, "contract_multiplier")
    fx = _positive(settlement_fx, "settlement_fx")
    quantity = float(quantity)
    if not np.isfinite(quantity) or quantity < 0.0:
        raise ValueError("quantity must be finite and non-negative")
    if contract == "linear":
        return quantity * multiplier * price
    if contract == "inverse":
        return quantity * multiplier
    if contract == "quanto":
        return quantity * multiplier * price * fx
    raise ValueError("contract must be 'linear', 'inverse', or 'quanto'")


@dataclass(frozen=True)
class FundingPolicy:
    """Premium-index funding rule, expressed per settlement interval."""

    clamp_lower: float = -0.0005
    clamp_upper: float = 0.0005
    absolute_cap: float = 0.0075
    interval_hours: float = 8.0

    def __post_init__(self) -> None:
        if self.clamp_lower > self.clamp_upper:
            raise ValueError("clamp_lower cannot exceed clamp_upper")
        if not np.isfinite(self.absolute_cap) or self.absolute_cap <= 0.0:
            raise ValueError("absolute_cap must be finite and positive")
        _positive(self.interval_hours, "interval_hours")


def funding_rate(
    snapshot: MarketSnapshot,
    *,
    interest_component: float = 0.0,
    policy: FundingPolicy | None = None,
) -> float:
    """Premium-index funding rate after clamp and absolute cap.

    The rule is ``premium + clamp(interest - premium)`` followed by a
    symmetric cap.  A positive rate means longs pay shorts.
    """

    policy = FundingPolicy() if policy is None else policy
    interest_component = float(interest_component)
    if not np.isfinite(interest_component):
        raise ValueError("interest_component must be finite")
    premium = snapshot.mark_index_basis
    clamped = np.clip(
        interest_component - premium,
        policy.clamp_lower,
        policy.clamp_upper,
    )
    return float(np.clip(premium + clamped, -policy.absolute_cap, policy.absolute_cap))


def funding_cashflow(
    notional: float,
    rate: float,
    *,
    side: PositionSide,
    intervals: float = 1.0,
) -> float:
    """Funding receipt/payment from the holder's point of view."""

    notional = float(notional)
    rate = float(rate)
    intervals = float(intervals)
    if not np.isfinite(notional) or notional < 0.0:
        raise ValueError("notional must be finite and non-negative")
    if not np.isfinite(rate):
        raise ValueError("rate must be finite")
    if not np.isfinite(intervals) or intervals < 0.0:
        raise ValueError("intervals must be finite and non-negative")
    return float(-_side_sign(side) * notional * rate * intervals)


def completed_funding_intervals(
    elapsed_hours: float,
    *,
    policy: FundingPolicy | None = None,
) -> int:
    """Number of fully completed funding settlements in elapsed wall time.

    Partial intervals do not accrue a cash flow in this deterministic venue
    baseline.  The tiny relative tolerance makes exact decimal representations
    of an interval boundary robust without rounding a genuinely partial period
    up to settlement.
    """

    policy = FundingPolicy() if policy is None else policy
    hours = float(elapsed_hours)
    if not np.isfinite(hours) or hours < 0.0:
        raise ValueError("elapsed_hours must be finite and non-negative")
    quotient = hours / policy.interval_hours
    return int(np.floor(quotient + 1e-12))


def settled_funding_cashflow(
    notional: float,
    rate: float,
    *,
    side: PositionSide,
    elapsed_hours: float,
    policy: FundingPolicy | None = None,
) -> float:
    """Funding cash flow over fully completed policy intervals."""

    policy = FundingPolicy() if policy is None else policy
    intervals = completed_funding_intervals(elapsed_hours, policy=policy)
    return funding_cashflow(notional, rate, side=side, intervals=intervals)


@dataclass(frozen=True)
class FundingLedger:
    """A zero-sum funding ledger, including venue residual for unmatched OI."""

    rate: float
    long_cashflow: float
    short_cashflow: float
    venue_residual: float

    @property
    def conservation_error(self) -> float:
        return float(self.long_cashflow + self.short_cashflow + self.venue_residual)


def matched_funding_ledger(
    long_notional: float,
    short_notional: float,
    rate: float,
    *,
    intervals: float = 1.0,
) -> FundingLedger:
    """Return cash flows for aggregate long/short notionals.

    Real matched open interest has equal long and short notional.  Keeping a
    venue residual explicit makes synthetic unmatched examples auditable
    instead of silently creating or destroying cash.
    """

    long_cf = funding_cashflow(long_notional, rate, side="long", intervals=intervals)
    short_cf = funding_cashflow(short_notional, rate, side="short", intervals=intervals)
    venue = -(long_cf + short_cf)
    return FundingLedger(float(rate), long_cf, short_cf, float(venue))


@dataclass(frozen=True)
class BasisPath:
    index_prices: np.ndarray
    mark_prices: np.ndarray
    basis: np.ndarray
    funding_rates: np.ndarray


def simulate_basis_feedback(
    index_prices,
    initial_mark_price: float,
    *,
    net_long_fraction: float = 0.0,
    basis_reversion: float = 0.50,
    imbalance_impact: float = 0.001,
    funding_feedback: float = 1.0,
    interest_component: float = 0.0,
    policy: FundingPolicy | None = None,
) -> BasisPath:
    """Deterministic basis/funding feedback over settlement intervals.

    The next basis equals the unreverted old basis plus an imbalance pressure
    minus the current funding charge.  This is a transparent stress baseline,
    not an empirical market-impact model.
    """

    index = np.asarray(index_prices, dtype=float)
    if index.ndim != 1 or index.size == 0 or np.any(~np.isfinite(index)) or np.any(index <= 0):
        raise ValueError("index_prices must be a non-empty positive 1-D array")
    initial_mark = _positive(initial_mark_price, "initial_mark_price")
    for value, name in (
        (net_long_fraction, "net_long_fraction"),
        (basis_reversion, "basis_reversion"),
        (imbalance_impact, "imbalance_impact"),
        (funding_feedback, "funding_feedback"),
    ):
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if not -1.0 <= net_long_fraction <= 1.0:
        raise ValueError("net_long_fraction must lie in [-1, 1]")
    if not 0.0 <= basis_reversion <= 1.0:
        raise ValueError("basis_reversion must lie in [0, 1]")
    if imbalance_impact < 0.0 or funding_feedback < 0.0:
        raise ValueError("impact and feedback coefficients must be non-negative")

    policy = FundingPolicy() if policy is None else policy
    mark = np.empty_like(index)
    basis = np.empty_like(index)
    rates = np.empty_like(index)
    mark[0] = initial_mark
    for i in range(index.size):
        basis[i] = mark[i] / index[i] - 1.0
        snapshot = MarketSnapshot(index[i], mark[i], mark[i])
        rates[i] = funding_rate(
            snapshot,
            interest_component=interest_component,
            policy=policy,
        )
        if i + 1 < index.size:
            next_basis = (
                (1.0 - basis_reversion) * basis[i]
                + imbalance_impact * net_long_fraction
                - funding_feedback * rates[i]
            )
            mark[i + 1] = index[i + 1] * max(1e-12, 1.0 + next_basis)
    return BasisPath(index.copy(), mark, basis, rates)
