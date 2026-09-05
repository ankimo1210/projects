"""Owner-side robust log-linear discount baseline, NOT a candidate starter.

QuantLib supplies continuous-time curve evaluation. Explicit real-year cash
flows avoid silently rounding synthetic maturities through calendar schedules.
This is a plumbing baseline, not a claim to optimal fit quality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import QuantLib as ql  # noqa: N813 — upstream's conventional Python alias
from datasets import GRID
from pricing import quote
from scipy.optimize import least_squares

REFERENCE = ql.Date(15, 1, 2026)
NODE_DAYS = np.array(
    [0, 30, 91, 182, 274, 365, 548, 730, 1095, 1825, 2555, 3650, 5475, 7300, 9125, 10950]
)
NODE_TIMES = NODE_DAYS / 365


class DiscountCurve:
    def __init__(self, zero):
        dates = [REFERENCE + int(d) for d in NODE_DAYS]
        values = np.r_[1.0, np.exp(-NODE_TIMES[1:] * np.asarray(zero))]
        self.curve = ql.DiscountCurve(dates, values.tolist(), ql.Actual365Fixed())

    def discount(self, t):
        x = np.asarray(t, dtype=float)
        return np.array([self.curve.discount(float(v)) for v in x.ravel()]).reshape(x.shape)

    def frame(self):
        df = self.discount(GRID)
        forwards = [self.curve.forwardRate(float(t), float(t), ql.Continuous).rate() for t in GRID]
        return pd.DataFrame(
            dict(
                maturity_years=GRID,
                zero_rate=-np.log(df) / GRID,
                discount_factor=df,
                forward_rate=forwards,
            )
        )


def clean_market(frame):
    data = frame.copy()
    before = len(data)
    for col in (
        "maturity_years",
        "quote_value",
        "bid",
        "ask",
        "liquidity_score",
        "payment_frequency",
        "coupon_rate",
    ):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data[
        np.isfinite(data.quote_value)
        & np.isfinite(data.maturity_years)
        & data.maturity_years.between(1 / 12, 30)
    ].copy()
    bond = data.instrument_type.eq("bond")
    spread = (data.ask - data.bid).abs()
    units = (~bond & (data.quote_value.abs() < 0.15) & (spread < 0.0005)) | (
        bond & (data.quote_value.abs() < 5) & (spread < 0.02)
    )
    data.loc[units, ["quote_value", "bid", "ask"]] *= 100
    data["timestamp"] = pd.to_datetime(data.timestamp, utc=True, errors="coerce")
    data = data.sort_values("timestamp", ascending=False).drop_duplicates("instrument_id")
    data = data[data.timestamp >= pd.Timestamp("2026-01-14", tz="UTC")].copy()
    if len(data) < 16:
        raise ValueError("not enough usable observations for the baseline")
    return data, dict(
        input_rows=before,
        usable_instruments=len(data),
        unit_repairs=int(units.sum()),
        heuristic_cleaning=True,
    )


def fit(data):
    rows = data.to_dict("records")
    scale = np.maximum(
        (data.ask - data.bid).abs().to_numpy() / 2,
        np.where(data.instrument_type.eq("bond"), 0.02, 0.003),
    )

    def residual(z):
        curve = DiscountCurve(z)
        return (
            np.array([quote(row, curve.discount) for row in rows]) - data.quote_value.to_numpy()
        ) / scale

    result = least_squares(
        residual,
        np.full(len(NODE_DAYS) - 1, 0.02),
        bounds=(-0.10, 0.25),
        loss="soft_l1",
        max_nfev=300,
    )
    if not result.success:
        raise RuntimeError(f"baseline did not converge: {result.message}")
    return DiscountCurve(result.x), dict(
        nfev=result.nfev,
        objective=float(result.cost),
        quantlib_version=ql.__version__,
        converged=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("refusing to overwrite baseline output")
    data, quality = clean_market(pd.read_csv(args.market_data))
    curve, info = fit(data)
    args.output_dir.mkdir(parents=True)
    curve.frame().to_csv(args.output_dir / "curve.csv", index=False)
    (args.output_dir / "diagnostics.json").write_text(
        json.dumps(dict(quality=quality, fit=info), indent=2) + "\n"
    )
    print(json.dumps(dict(quality=quality, fit=info)))
