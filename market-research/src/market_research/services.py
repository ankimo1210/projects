"""Shared offline research run used by the CLI and Streamlit entry points."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .backtest import BacktestResult, run_backtest, run_prefix_strategy
from .contracts import Instrument, MacroObservation, PriceBar
from .prices import assess_bars


@dataclass(frozen=True, slots=True)
class DemoRun:
    mode: str
    run_id: str
    input_hash: str
    prices: pd.DataFrame
    bars: tuple[PriceBar, ...]
    macro_observations: tuple[MacroObservation, ...]
    target_weights: pd.DataFrame
    backtest: BacktestResult


def build_demo_run() -> DemoRun:
    """Create a fixed synthetic run without reading account files or the network."""
    close_index = pd.bdate_range("2026-06-01", periods=60, tz="UTC") + pd.Timedelta(hours=20)
    decision_index = close_index + pd.Timedelta(hours=1)
    alpha = [100.0 + 0.35 * n + 2.0 * math.sin(n / 5) for n in range(len(close_index))]
    beta = [70.0 + 0.15 * n + 1.5 * math.cos(n / 7) for n in range(len(close_index))]
    prices = pd.DataFrame({"DEMO:ALPHA": alpha, "DEMO:BETA": beta}, index=decision_index)
    instruments = (
        Instrument("DEMO", "ALPHA", "USD", "UTC"),
        Instrument("DEMO", "BETA", "USD", "UTC"),
    )
    bars = tuple(
        PriceBar(
            instrument=instrument,
            provider="synthetic-demo",
            interval="1d",
            bar_start=close_at.to_pydatetime() - timedelta(hours=8),
            bar_end=close_at.to_pydatetime(),
            available_at=decision_at.to_pydatetime(),
            observed_at=decision_at.to_pydatetime(),
            close=float(prices.loc[decision_at, instrument.instrument_id]),
            adjustment="raw",
            revision_id="demo-v1",
        )
        for close_at, decision_at in zip(close_index, decision_index, strict=True)
        for instrument in instruments
    )

    def strategy(prefix: pd.DataFrame) -> pd.Series:
        series = prefix["DEMO:ALPHA"]
        alpha_weight = 0.6 if series.iloc[-1] >= series.tail(5).mean() else 0.2
        return pd.Series({"DEMO:ALPHA": alpha_weight, "DEMO:BETA": 0.4})

    target = run_prefix_strategy(prices, strategy)
    result = run_backtest(
        target,
        prices.pct_change(),
        base_currency="USD",
        return_currencies={instrument.instrument_id: "USD" for instrument in instruments},
        commission_bps=3,
        slippage_bps=2,
    )
    rows = (
        MacroObservation(
            "DEMO_CPI",
            date(2026, 6, 1),
            decision_index[10].to_pydatetime(),
            100.0,
            "synthetic-demo",
            "first",
            "actual",
        ),
        MacroObservation(
            "DEMO_CPI",
            date(2026, 6, 1),
            decision_index[30].to_pydatetime(),
            101.0,
            "synthetic-demo",
            "revised",
            "actual",
        ),
    )
    payload = {
        "schema": "demo-v2",
        "prices": [
            [close_at.isoformat(), decision_at.isoformat(), round(a, 10), round(b, 10)]
            for close_at, decision_at, a, b in zip(
                close_index, decision_index, alpha, beta, strict=True
            )
        ],
        "commission_bps": 3,
        "slippage_bps": 2,
    }
    input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return DemoRun(
        mode="synthetic-demo",
        run_id=input_hash[:16],
        input_hash=input_hash,
        prices=prices,
        bars=assess_bars(bars, decision_index[-1].to_pydatetime()),
        macro_observations=rows,
        target_weights=target,
        backtest=result,
    )
