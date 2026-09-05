"""Typed market-observation and calibration-instrument records.

``MarketObservation`` is the supplied raw-row schema and is kept unchanged.
``Instrument`` is the cleaned, normalised, curve-ready record produced by
:mod:`quantcurve.cleaning`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from .conventions import annual_frequency_for_swap, bond_schedule, swap_schedule

DEPOSIT = "deposit"
OIS_SWAP = "ois_swap"
BOND = "bond"
SUPPORTED_TYPES = (DEPOSIT, OIS_SWAP, BOND)

#: Notionals mandated by ``CONVENTIONS.md`` for risk reporting.
RATE_NOTIONAL = 1_000_000.0
BOND_FACE = 100.0


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
    """A cleaned instrument ready for curve calibration.

    ``quote`` is stored in *normalised input units*: percentage points for
    deposit simple rates and OIS par rates, price points per 100 face for bonds.
    ``half_spread`` uses the same units.
    """

    obs_id: str
    instrument_id: str
    instrument_type: str
    maturity_years: float
    coupon_rate: float | None
    payment_frequency: int
    quote: float
    half_spread: float
    liquidity_score: float
    weight: float
    source: str
    timestamp: str
    quality_factor: float = 1.0
    #: Quote-only uncertainty in yield-equivalent basis points (bid/ask width
    #: inflated by illiquidity).  The calibration weight adds an estimated
    #: model/idiosyncratic error to this in quadrature.
    sigma_quote_bp: float = 1.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    # -- schedule helpers -------------------------------------------------
    @property
    def is_rate_quote(self) -> bool:
        return self.instrument_type in (DEPOSIT, OIS_SWAP)

    @property
    def fixed_frequency(self) -> int:
        """Payment frequency actually used for pricing."""
        if self.instrument_type == OIS_SWAP:
            return annual_frequency_for_swap(self.maturity_years)
        return int(self.payment_frequency)

    def schedule(self) -> np.ndarray:
        if self.instrument_type == DEPOSIT:
            return np.array([self.maturity_years], dtype=float)
        if self.instrument_type == OIS_SWAP:
            return swap_schedule(self.maturity_years, self.fixed_frequency)[0]
        return bond_schedule(self.maturity_years, self.fixed_frequency)

    def notional(self) -> float:
        return BOND_FACE if self.instrument_type == BOND else RATE_NOTIONAL

    def with_weight(self, weight: float) -> "Instrument":
        return Instrument(
            obs_id=self.obs_id,
            instrument_id=self.instrument_id,
            instrument_type=self.instrument_type,
            maturity_years=self.maturity_years,
            coupon_rate=self.coupon_rate,
            payment_frequency=self.payment_frequency,
            quote=self.quote,
            half_spread=self.half_spread,
            liquidity_score=self.liquidity_score,
            weight=weight,
            source=self.source,
            timestamp=self.timestamp,
            quality_factor=self.quality_factor,
            sigma_quote_bp=self.sigma_quote_bp,
            notes=self.notes,
        )
