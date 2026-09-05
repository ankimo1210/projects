from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from quantcurve.curve import ZeroCurve
from quantcurve.io import REQUIRED_COLUMNS
from quantcurve.pricing import model_quote


def raw_row(
    obs_id: str,
    instrument_id: str,
    instrument_type: str,
    maturity: float,
    quote: float | None,
    *,
    timestamp: str = "2026-01-15T15:00:00Z",
    bid: float | None = None,
    ask: float | None = None,
    coupon: float | None = None,
    frequency: int | None = None,
    liquidity: float = 0.8,
) -> dict[str, object]:
    rate = instrument_type != "bond"
    return {
        "obs_id": obs_id,
        "instrument_id": instrument_id,
        "source": "COMPOSITE",
        "timestamp": timestamp,
        "currency": "USD",
        "instrument_type": instrument_type,
        "maturity_date": (date(2026, 1, 15) + timedelta(days=round(maturity * 365))).isoformat(),
        "maturity_years": maturity,
        "start_years": 0,
        "coupon_rate": coupon if instrument_type == "bond" else None,
        "payment_frequency": frequency or (2 if instrument_type == "bond" or maturity > 2 else 1),
        "day_count": "ACT/365F",
        "quote_type": "clean_price" if instrument_type == "bond" else ("simple_rate" if instrument_type == "deposit" else "par_rate"),
        "quote_value": quote,
        "quote_unit": "PRICE_POINTS" if instrument_type == "bond" else "PERCENT",
        "bid": bid,
        "ask": ask,
        "liquidity_score": liquidity,
        "settlement_days": 2,
    }


def make_market_frame() -> pd.DataFrame:
    curve = ZeroCurve(np.array([0.0, 30.0]), np.array([0.02, 0.02]), method="pchip")
    rows: list[dict[str, object]] = []
    specifications = []
    specifications.extend(("deposit", t, None) for t in (1 / 12, 0.25, 0.5, 0.75, 1.0))
    specifications.extend(("ois_swap", t, None) for t in (1.0, 1.5, 1.5, 1.5, 2.0, 3.0, 4.0, 4.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0))
    specifications.extend(("bond", t, c) for t, c in ((2.4, 0.025), (6.7, 0.03), (12.2, 0.018), (21.3, 0.027)))
    for index, (instrument_type, maturity, coupon) in enumerate(specifications):
        normalized = pd.Series(
            {
                "instrument_type": instrument_type,
                "maturity_years": maturity,
                "payment_frequency": 2 if instrument_type == "bond" or maturity > 2 else 1,
                "coupon_rate": coupon,
            }
        )
        quote = model_quote(normalized, curve)
        raw_quote = quote if instrument_type == "bond" else 100 * quote
        half = 0.025 if instrument_type == "bond" else 0.01
        rows.append(
            raw_row(
                f"OBS{index:04d}",
                f"INS{index:04d}",
                instrument_type,
                maturity,
                raw_quote,
                bid=raw_quote - half,
                ask=raw_quote + half,
                coupon=coupon,
            )
        )
    return pd.DataFrame(rows).loc[:, REQUIRED_COLUMNS]


def write_market_csv(path: Path) -> Path:
    make_market_frame().to_csv(path, index=False)
    return path
