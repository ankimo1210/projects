"""Deterministic synthetic market data built from a *known* curve.

Tests that only check code paths can be satisfied by broken maths.  These
helpers instead generate quotes from an explicit Nelson-Siegel forward curve
using the documented conventions, so a test can assert that the pipeline
recovers the curve it was given -- which is the only end-to-end statement about
correctness that actually means anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from quantcurve.conventions import annual_frequency_for_swap, bond_schedule, swap_schedule
from quantcurve.curve import DiscountCurve

VALUATION_DATE = datetime(2026, 1, 15, tzinfo=timezone.utc)

DEPOSIT_TENORS = (1.0 / 12.0, 0.25, 0.5, 0.75, 1.0)
SWAP_TENORS = (1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0)
BOND_SPECS = (
    (2.4, 0.021, 2),
    (4.6, 0.028, 2),
    (8.3, 0.019, 2),
    (12.7, 0.026, 2),
    (18.2, 0.023, 2),
    (26.4, 0.030, 2),
)


@dataclass(frozen=True)
class NelsonSiegel:
    """Instantaneous forward ``f(T) = b0 + b1 e^{-T/tau} + b2 (T/tau) e^{-T/tau}``."""

    beta0: float = 0.028
    beta1: float = -0.016
    beta2: float = 0.021
    tau: float = 2.5

    def forward(self, t):
        t = np.asarray(t, dtype=float)
        x = t / self.tau
        decay = np.exp(-x)
        return self.beta0 + self.beta1 * decay + self.beta2 * x * decay

    def integrated_forward(self, t):
        t = np.asarray(t, dtype=float)
        x = t / self.tau
        decay = np.exp(-x)
        return (
            self.beta0 * t
            + self.beta1 * self.tau * (1.0 - decay)
            + self.beta2 * self.tau * (1.0 - decay * (1.0 + x))
        )

    def discount(self, t):
        return np.exp(-self.integrated_forward(t))

    def zero(self, t):
        t = np.asarray(t, dtype=float)
        return np.where(t > 0, self.integrated_forward(np.maximum(t, 1e-12)) / np.maximum(t, 1e-12), self.forward(0.0))


class NelsonSiegelCurve(DiscountCurve):
    """The synthetic truth exposed through the package's curve interface.

    Using the analytic curve (rather than a spline approximation of it) makes the
    pricing round-trip tests exact to machine precision, so a failure means the
    pricing code is wrong rather than the reference being coarse.
    """

    def __init__(self, model: "NelsonSiegel | None" = None) -> None:
        self.model = model or NelsonSiegel()
        self.max_calibrated_maturity = 30.0

    def integrated_forward(self, t):
        return self.model.integrated_forward(t)

    def forward(self, t):
        return self.model.forward(t)


def deposit_quote(curve: NelsonSiegel, maturity: float) -> float:
    d = float(curve.discount(np.array([maturity]))[0])
    return (1.0 / d - 1.0) / maturity * 100.0


def swap_quote(curve: NelsonSiegel, maturity: float) -> float:
    frequency = annual_frequency_for_swap(maturity)
    times, accrual = swap_schedule(maturity, frequency)
    discounts = np.asarray(curve.discount(times), dtype=float)
    return (1.0 - discounts[-1]) / (accrual * discounts.sum()) * 100.0


def bond_quote(curve: NelsonSiegel, maturity: float, coupon: float, frequency: int) -> float:
    times = bond_schedule(maturity, frequency)
    discounts = np.asarray(curve.discount(times), dtype=float)
    flows = np.full(times.shape, 100.0 * coupon / frequency)
    flows[-1] += 100.0
    return float(np.sum(flows * discounts))


def _row(
    index: int,
    instrument_type: str,
    maturity: float,
    quote: float,
    unit: str,
    quote_type: str,
    half_spread: float,
    coupon: float | None = None,
    frequency: int = 1,
    liquidity: float = 0.9,
    timestamp: datetime | None = None,
    source: str = "VENUE_A",
    obs_prefix: str = "OBS",
) -> dict:
    stamp = timestamp or (VALUATION_DATE + timedelta(hours=15))
    maturity_date = VALUATION_DATE + timedelta(days=round(maturity * 365.0))
    return {
        "obs_id": f"{obs_prefix}{index:04d}",
        "instrument_id": f"INS{index:04d}",
        "source": source,
        "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "currency": "USD",
        "instrument_type": instrument_type,
        "maturity_date": maturity_date.date().isoformat(),
        "maturity_years": maturity,
        "start_years": 0,
        "coupon_rate": "" if coupon is None else coupon,
        "payment_frequency": frequency,
        "day_count": "ACT/365F",
        "quote_type": quote_type,
        "quote_value": quote,
        "quote_unit": unit,
        "bid": quote - half_spread,
        "ask": quote + half_spread,
        "liquidity_score": liquidity,
        "settlement_days": 2,
    }


def clean_frame(curve: NelsonSiegel | None = None) -> pd.DataFrame:
    """A perfectly clean data set generated from ``curve``."""
    curve = curve or NelsonSiegel()
    rows: list[dict] = []
    index = 1
    for tenor in DEPOSIT_TENORS:
        rows.append(
            _row(index, "deposit", tenor, deposit_quote(curve, tenor), "PERCENT",
                 "simple_rate", 0.001, frequency=1)
        )
        index += 1
    for tenor in SWAP_TENORS:
        rows.append(
            _row(index, "ois_swap", tenor, swap_quote(curve, tenor), "PERCENT",
                 "par_rate", 0.0015, frequency=annual_frequency_for_swap(tenor))
        )
        index += 1
    for maturity, coupon, frequency in BOND_SPECS:
        rows.append(
            _row(index, "bond", maturity,
                 bond_quote(curve, maturity, coupon, frequency), "PRICE_POINTS",
                 "clean_price", 0.02, coupon=coupon, frequency=frequency)
        )
        index += 1
    return pd.DataFrame(rows)


def dirty_frame(curve: NelsonSiegel | None = None) -> pd.DataFrame:
    """The clean data set with one instance of every documented defect injected."""
    curve = curve or NelsonSiegel()
    frame = clean_frame(curve).copy()
    index = int(frame["instrument_id"].str[3:].astype(int).max())

    # 1. unit error: the 3M deposit quoted as a decimal rather than percent.
    mask = frame["maturity_years"] == 0.25
    for column in ("quote_value", "bid", "ask"):
        frame.loc[mask, column] = frame.loc[mask, column] / 100.0

    # 2. missing quote on the 5Y swap (bid/ask still present).
    mask = (frame["instrument_type"] == "ois_swap") & (frame["maturity_years"] == 5.0)
    frame.loc[mask, "quote_value"] = np.nan

    # 3. crossed market on the 10Y swap.
    mask = (frame["instrument_type"] == "ois_swap") & (frame["maturity_years"] == 10.0)
    bid = frame.loc[mask, "bid"].to_numpy()[0]
    ask = frame.loc[mask, "ask"].to_numpy()[0]
    frame.loc[mask, "bid"] = ask
    frame.loc[mask, "ask"] = bid

    # 4. wide, illiquid market on the 20Y swap.
    mask = (frame["instrument_type"] == "ois_swap") & (frame["maturity_years"] == 20.0)
    quote = frame.loc[mask, "quote_value"].to_numpy()[0]
    frame.loc[mask, "bid"] = quote - 0.05
    frame.loc[mask, "ask"] = quote + 0.05
    frame.loc[mask, "liquidity_score"] = 0.12

    # 5. stale duplicate of the 1Y deposit from a backup feed, off market.
    original = frame[(frame["instrument_type"] == "deposit")
                     & (frame["maturity_years"] == 1.0)].iloc[0].to_dict()
    duplicate = dict(original)
    duplicate["obs_id"] = "DUP0001"
    duplicate["source"] = "BACKUP_FEED"
    duplicate["timestamp"] = (VALUATION_DATE + timedelta(hours=9)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    duplicate["quote_value"] = float(original["quote_value"]) + 0.006

    # 6. genuinely stale observation (two weeks old) on a fresh instrument id.
    index += 1
    stale = _row(index, "ois_swap", 3.0, swap_quote(curve, 3.0) + 0.004, "PERCENT",
                 "par_rate", 0.0015, frequency=2,
                 timestamp=VALUATION_DATE - timedelta(days=13), source="VENUE_B")

    # 7. gross outlier: a 7Y swap 40bp away from the curve, with peers around it.
    index += 1
    outlier = _row(index, "ois_swap", 7.0, swap_quote(curve, 7.0) + 0.40, "PERCENT",
                   "par_rate", 0.0015, frequency=2, source="VENUE_B")
    index += 1
    peer_a = _row(index, "ois_swap", 7.0, swap_quote(curve, 7.0) + 0.0004, "PERCENT",
                  "par_rate", 0.0015, frequency=2, source="COMPOSITE")
    index += 1
    peer_b = _row(index, "ois_swap", 7.0, swap_quote(curve, 7.0) - 0.0003, "PERCENT",
                  "par_rate", 0.0015, frequency=2, source="VENUE_A")

    return pd.concat(
        [frame, pd.DataFrame([duplicate, stale, outlier, peer_a, peer_b])],
        ignore_index=True,
    )


def negative_rate_frame() -> pd.DataFrame:
    """A clean data set whose whole curve sits below zero."""
    return clean_frame(NelsonSiegel(beta0=-0.004, beta1=-0.006, beta2=0.004, tau=3.0))


def write_frame(frame: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target
