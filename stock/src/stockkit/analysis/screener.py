"""Simple screener: evaluate a list of symbols against rules.

Rules are callables `rule(snapshot_dict, prices_df) -> bool`. Helpers below
generate common ones.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from stockkit.analysis import fundamental, technical
from stockkit.data.providers.yfinance_provider import get_prices

Rule = Callable[[dict[str, Any], pd.DataFrame], bool]


def pe_below(threshold: float) -> Rule:
    def _r(snap, _p):
        v = snap.get("pe")
        return v is not None and v < threshold

    return _r


def roe_above(threshold: float) -> Rule:
    def _r(snap, _p):
        v = snap.get("roe")
        return v is not None and v > threshold

    return _r


def dividend_yield_above(threshold: float) -> Rule:
    def _r(snap, _p):
        v = snap.get("dividend_yield")
        return v is not None and v > threshold

    return _r


def above_sma(window: int = 200) -> Rule:
    def _r(_snap, prices):
        if prices is None or prices.empty:
            return False
        last = prices["close"].iloc[-1]
        s = technical.sma(prices, window).iloc[-1]
        return pd.notna(s) and last > s

    return _r


def rsi_between(low: float = 30, high: float = 70) -> Rule:
    def _r(_snap, prices):
        if prices is None or prices.empty:
            return False
        v = technical.rsi(prices).iloc[-1]
        return pd.notna(v) and low <= v <= high

    return _r


def screen(
    symbols: list[str],
    rules: list[Rule],
    period: str = "1y",
) -> pd.DataFrame:
    """Run rules on each symbol; return matched snapshot rows."""
    rows = []
    for sym in symbols:
        snap = fundamental.snapshot(sym)
        try:
            prices = get_prices(sym, period=period)
        except Exception:
            prices = pd.DataFrame()
        try:
            ok = all(rule(snap, prices) for rule in rules)
        except Exception:
            ok = False
        if ok:
            rows.append(snap)
    return pd.DataFrame(rows).set_index("symbol") if rows else pd.DataFrame()
