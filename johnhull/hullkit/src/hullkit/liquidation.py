"""Margin, liquidation, oracle-risk, and loss-waterfall mechanics.

The accounting is intentionally deterministic.  Every deficit is assigned to
an auction recovery, insurance fund, ADL capacity, socialized-loss pool, or an
explicit uncovered balance.  This makes cash conservation and system solvency
testable without exchange-specific infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .perpetuals import MarketSnapshot, position_pnl

LiquidationMethod = Literal["forced_sale", "auction"]


def _non_negative(value: float, name: str) -> float:
    value = float(value)
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


@dataclass(frozen=True)
class MarginAccount:
    """A quote-margined linear perpetual position.

    ``quantity`` is signed: positive is long and negative is short.
    """

    collateral: float
    quantity: float
    entry_price: float
    contract_multiplier: float = 1.0
    initial_margin_rate: float = 0.10
    maintenance_margin_rate: float = 0.05
    liquidation_fee_rate: float = 0.005

    def __post_init__(self) -> None:
        _non_negative(self.collateral, "collateral")
        if not np.isfinite(self.quantity) or self.quantity == 0.0:
            raise ValueError("quantity must be finite and non-zero")
        if not np.isfinite(self.entry_price) or self.entry_price <= 0.0:
            raise ValueError("entry_price must be finite and positive")
        if not np.isfinite(self.contract_multiplier) or self.contract_multiplier <= 0.0:
            raise ValueError("contract_multiplier must be finite and positive")
        for value, name in (
            (self.initial_margin_rate, "initial_margin_rate"),
            (self.maintenance_margin_rate, "maintenance_margin_rate"),
            (self.liquidation_fee_rate, "liquidation_fee_rate"),
        ):
            if not np.isfinite(value) or not 0.0 <= value < 1.0:
                raise ValueError(f"{name} must lie in [0, 1)")
        if self.maintenance_margin_rate > self.initial_margin_rate:
            raise ValueError("maintenance margin cannot exceed initial margin")


def account_equity(
    account: MarginAccount, mark_price: float, funding_cashflow: float = 0.0
) -> float:
    """Collateral plus unrealized PnL and accumulated funding."""

    side = "long" if account.quantity > 0.0 else "short"
    pnl = position_pnl(
        "linear",
        account.entry_price,
        mark_price,
        abs(account.quantity),
        side=side,
        contract_multiplier=account.contract_multiplier,
    )
    if not np.isfinite(funding_cashflow):
        raise ValueError("funding_cashflow must be finite")
    return float(account.collateral + pnl + funding_cashflow)


def margin_requirement(
    account: MarginAccount, mark_price: float, *, initial: bool = False
) -> float:
    """Initial or maintenance margin on current linear notional."""

    if not np.isfinite(mark_price) or mark_price <= 0.0:
        raise ValueError("mark_price must be finite and positive")
    rate = account.initial_margin_rate if initial else account.maintenance_margin_rate
    return float(abs(account.quantity) * account.contract_multiplier * mark_price * rate)


def liquidation_triggered(
    account: MarginAccount,
    mark_price: float,
    funding_cashflow: float = 0.0,
) -> bool:
    """Whether equity is at or below maintenance margin."""

    equity = account_equity(account, mark_price, funding_cashflow)
    requirement = margin_requirement(account, mark_price)
    tolerance = 1e-12 * max(1.0, abs(equity), abs(requirement))
    return equity <= requirement + tolerance


def bankruptcy_price(account: MarginAccount, funding_cashflow: float = 0.0) -> float:
    """Linear-contract price at which account equity is exactly zero."""

    capital = account.collateral + float(funding_cashflow)
    price = account.entry_price - capital / (account.quantity * account.contract_multiplier)
    return float(price)


def liquidation_price(account: MarginAccount, funding_cashflow: float = 0.0) -> float:
    """Price at which equity equals current-notional maintenance margin."""

    capital = account.collateral + float(funding_cashflow)
    unit = abs(account.quantity) * account.contract_multiplier
    if account.quantity > 0.0:
        denominator = unit * (1.0 - account.maintenance_margin_rate)
        price = (unit * account.entry_price - capital) / denominator
    else:
        denominator = unit * (1.0 + account.maintenance_margin_rate)
        price = (unit * account.entry_price + capital) / denominator
    return float(price)


@dataclass(frozen=True)
class OracleRisk:
    """Oracle staleness and mark/index dislocation flags for one snapshot."""

    age: float
    mark_index_dislocation: float
    last_index_dislocation: float
    stale: bool
    dislocated: bool

    @property
    def usable(self) -> bool:
        """True when the oracle is neither stale nor dislocated."""
        return not self.stale and not self.dislocated


def assess_oracle_risk(
    snapshot: MarketSnapshot,
    *,
    max_age: float,
    max_mark_dislocation: float,
) -> OracleRisk:
    """Flag stale-oracle and mark/index dislocation independently."""

    max_age = _non_negative(max_age, "max_age")
    max_dislocation = _non_negative(max_mark_dislocation, "max_mark_dislocation")
    basis = snapshot.mark_index_basis
    return OracleRisk(
        age=snapshot.oracle_age,
        mark_index_dislocation=basis,
        last_index_dislocation=snapshot.last_index_dislocation,
        stale=snapshot.oracle_age > max_age,
        dislocated=abs(basis) > max_dislocation,
    )


@dataclass(frozen=True)
class OracleShock:
    """Observed vs latent index and mark after a latency or manipulation shock."""

    observed_index: float
    latent_index: float
    shocked_mark: float
    observed_dislocation: float
    latent_dislocation: float


def oracle_shock(
    snapshot: MarketSnapshot,
    *,
    latency_return: float = 0.0,
    mark_manipulation: float = 0.0,
) -> OracleShock:
    """Separate an unobserved latency move from a mark manipulation shock."""

    if not np.isfinite(latency_return) or latency_return <= -1.0:
        raise ValueError("latency_return must be finite and greater than -1")
    if not np.isfinite(mark_manipulation) or mark_manipulation <= -1.0:
        raise ValueError("mark_manipulation must be finite and greater than -1")
    latent = snapshot.index_price * (1.0 + latency_return)
    mark = snapshot.mark_price * (1.0 + mark_manipulation)
    return OracleShock(
        observed_index=snapshot.index_price,
        latent_index=float(latent),
        shocked_mark=float(mark),
        observed_dislocation=float(mark / snapshot.index_price - 1.0),
        latent_dislocation=float(mark / latent - 1.0),
    )


def execution_price(
    index_price: float,
    quantity: float,
    *,
    method: LiquidationMethod = "forced_sale",
    impact_bps: float = 100.0,
    auction_improvement: float = 0.5,
) -> float:
    """Synthetic close-out price for forced-sale and auction comparisons."""

    if not np.isfinite(index_price) or index_price <= 0.0:
        raise ValueError("index_price must be finite and positive")
    if not np.isfinite(quantity) or quantity == 0.0:
        raise ValueError("quantity must be finite and non-zero")
    impact_bps = _non_negative(impact_bps, "impact_bps")
    if not np.isfinite(auction_improvement) or not 0.0 <= auction_improvement <= 1.0:
        raise ValueError("auction_improvement must lie in [0, 1]")
    if method == "forced_sale":
        impact = impact_bps * 1e-4
    elif method == "auction":
        impact = impact_bps * 1e-4 * (1.0 - auction_improvement)
    else:
        raise ValueError("method must be 'forced_sale' or 'auction'")
    direction = -1.0 if quantity > 0.0 else 1.0
    return float(index_price * (1.0 + direction * impact))


@dataclass(frozen=True)
class LiquidationLedger:
    """Cash-conserving close-out ledger across trader, insurance, ADL, and socialized legs."""

    execution_price: float
    account_equity: float
    liquidation_fee: float
    trader_return: float
    auction_recovery: float
    insurance_used: float
    insurance_fund_before: float
    insurance_fund_after: float
    adl_used: float
    socialized_loss: float
    uncovered_loss: float
    conservation_error: float

    @property
    def solvent(self) -> bool:
        """True when losses are fully covered and the ledger conserves cash."""
        return self.uncovered_loss <= 1e-12 and abs(self.conservation_error) <= 1e-10


def liquidation_waterfall(
    account: MarginAccount,
    close_price: float,
    *,
    insurance_fund: float,
    auction_recovery: float = 0.0,
    adl_capacity: float = 0.0,
    social_loss_capacity: float = float("inf"),
    funding_cashflow: float = 0.0,
) -> LiquidationLedger:
    """Allocate close-out equity/deficit through a transparent waterfall.

    Coverage order is auction recovery, insurance fund, ADL, then socialized
    loss.  ``uncovered_loss`` remains explicit when all capacities are
    exhausted.  Liquidation fees are charged only against positive equity and
    credited to the insurance fund.
    """

    if not np.isfinite(close_price) or close_price <= 0.0:
        raise ValueError("close_price must be finite and positive")
    insurance_before = _non_negative(insurance_fund, "insurance_fund")
    auction_capacity = _non_negative(auction_recovery, "auction_recovery")
    adl_capacity = _non_negative(adl_capacity, "adl_capacity")
    if np.isnan(social_loss_capacity) or social_loss_capacity < 0.0:
        raise ValueError("social_loss_capacity must be non-negative")

    equity = account_equity(account, close_price, funding_cashflow)
    notional = abs(account.quantity) * account.contract_multiplier * close_price
    fee = min(max(equity, 0.0), notional * account.liquidation_fee_rate)
    trader_return = max(equity - fee, 0.0)
    remaining = max(-equity, 0.0)

    auction_used = min(auction_capacity, remaining)
    remaining -= auction_used
    insurance_used = min(insurance_before, remaining)
    remaining -= insurance_used
    adl_used = min(adl_capacity, remaining)
    remaining -= adl_used
    socialized = min(social_loss_capacity, remaining)
    remaining -= socialized
    uncovered = remaining
    insurance_after = insurance_before + fee - insurance_used

    sources = auction_used + insurance_used + adl_used + socialized + uncovered
    conservation = equity + sources - trader_return - fee
    return LiquidationLedger(
        execution_price=float(close_price),
        account_equity=float(equity),
        liquidation_fee=float(fee),
        trader_return=float(trader_return),
        auction_recovery=float(auction_used),
        insurance_used=float(insurance_used),
        insurance_fund_before=float(insurance_before),
        insurance_fund_after=float(insurance_after),
        adl_used=float(adl_used),
        socialized_loss=float(socialized),
        uncovered_loss=float(uncovered),
        conservation_error=float(conservation),
    )
