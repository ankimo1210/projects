"""Simple daily backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    metrics: dict


def _calc_metrics(equity: pd.Series, ann_factor: int = 252) -> dict:
    ret = equity.pct_change().dropna()
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1
    years = len(equity) / ann_factor
    ann_ret = (1 + total_ret) ** (1 / max(years, 1e-9)) - 1
    ann_vol = ret.std() * np.sqrt(ann_factor)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    peak = equity.cummax()
    dd = (equity - peak) / peak
    max_dd = dd.min()
    return {
        "total_return": total_ret,
        "annual_return": ann_ret,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
    }


def run_backtest(
    prices_df: pd.DataFrame,
    ticker: str,
    signal_fn: Callable[[pd.Series], pd.Series],
    commission: float = 0.001,
    slippage: float = 0.001,
    initial_capital: float = 1_000_000,
) -> BacktestResult:
    """
    signal_fn: (close: pd.Series) -> pd.Series of {1 (long), 0 (flat), -1 (short)}
    Execution: next-day open after signal.
    """
    df = prices_df[prices_df["ticker"] == ticker].sort_values("timestamp").copy()
    if df.empty:
        return BacktestResult(pd.Series(dtype=float), pd.DataFrame(), {})

    close = df.set_index("timestamp")["close"]
    opens = df.set_index("timestamp")["open"] if "open" in df.columns else close

    signal = signal_fn(close).reindex(close.index, fill_value=0)
    position = signal.shift(1).fillna(0)   # execute next bar
    exec_price = opens                       # next open

    daily_ret = exec_price.pct_change().fillna(0)
    strategy_ret = position * daily_ret

    # commission on position change
    pos_change = position.diff().abs().fillna(0)
    cost = pos_change * (commission + slippage)
    net_ret = strategy_ret - cost

    equity = initial_capital * (1 + net_ret).cumprod()

    # trades log
    entries = pos_change[pos_change != 0].index
    trades = pd.DataFrame({
        "timestamp": entries,
        "position": position.loc[entries].values,
        "price": exec_price.loc[entries].values,
    })

    metrics = _calc_metrics(equity)
    metrics["trade_count"] = len(trades)
    metrics["win_rate"] = (
        (net_ret[net_ret != 0] > 0).mean() if (net_ret != 0).any() else 0.0
    )

    return BacktestResult(equity=equity, trades=trades, metrics=metrics)


# ---------------------------------------------------------------------------
# Built-in signal factories
# ---------------------------------------------------------------------------

def ma_cross_signal(close: pd.Series, fast: int = 20, slow: int = 60) -> pd.Series:
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    return (fast_ma > slow_ma).astype(int)


def zscore_reversion_signal(
    close: pd.Series, window: int = 60, entry: float = 2.0, exit_: float = 0.5
) -> pd.Series:
    from src.analytics.zscore import rolling_zscore
    z = rolling_zscore(close, window=window)
    pos = pd.Series(0, index=close.index)
    for i in range(1, len(z)):
        prev = pos.iloc[i - 1]
        zi = z.iloc[i]
        if pd.isna(zi):
            pos.iloc[i] = 0
        elif zi <= -entry:
            pos.iloc[i] = 1
        elif zi >= entry:
            pos.iloc[i] = -1
        elif prev != 0 and abs(zi) < exit_:
            pos.iloc[i] = 0
        else:
            pos.iloc[i] = prev
    return pos


def momentum_signal(close: pd.Series, window: int = 20) -> pd.Series:
    ret = close.pct_change(window)
    return (ret > 0).astype(int)


def volatility_breakout_signal(close: pd.Series, window: int = 20, mult: float = 1.0) -> pd.Series:
    rolling_high = close.rolling(window).max().shift(1)
    rolling_low = close.rolling(window).min().shift(1)
    atr = (rolling_high - rolling_low)
    upper = rolling_high + mult * atr
    pos = (close > upper).astype(int)
    return pos
