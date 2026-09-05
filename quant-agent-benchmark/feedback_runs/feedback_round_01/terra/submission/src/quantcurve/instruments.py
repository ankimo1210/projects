"""Typed market-observation records. Pricing logic is intentionally absent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
