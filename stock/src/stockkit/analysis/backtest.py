"""Simple long/flat backtester.

Conventions:
- Input `prices` must contain 'close' (used for execution) and any indicator
  columns referenced by the signal function.
- A signal function returns a Series of {-1, 0, 1} aligned to prices.index:
    1  = enter/hold long
    0  = flat
   -1  = treated same as 0 in long-only mode (cash)
- Execution: position is taken at the *next bar's open* if available, else
  next bar's close (look-ahead-safe).
- No leverage, long-only, fully invested when in position.

Returns an `BacktestResult` dataclass with equity curve, trades and metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from stockkit.analysis import technical

SignalFn = Callable[[pd.DataFrame], pd.Series]
TRADING_DAYS = 252


@dataclass
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)


def run(
    prices: pd.DataFrame,
    signal: SignalFn,
    *,
    initial_cash: float = 1_000_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> BacktestResult:
    """Run a long/flat backtest.

    fee_bps + slippage_bps are charged on each entry and exit (one-way each
    leg), expressed in basis points of trade notional.
    """
    df = prices.copy()
    if "close" not in df.columns:
        raise ValueError("prices must contain 'close'")

    sig_raw = signal(df).reindex(df.index).fillna(0)
    # Long-only: clip -1 to 0
    target = (sig_raw > 0).astype(int)

    # Shift so today's signal acts on tomorrow (no look-ahead)
    pos = target.shift(1).fillna(0).astype(int)

    exec_price = df["open"] if "open" in df.columns else df["close"]
    # Daily simple return of the underlying using close-to-close
    asset_ret = df["close"].pct_change().fillna(0)

    # Position-day return: when pos == 1, gain asset_ret; otherwise 0
    strat_ret = asset_ret * pos

    # Trade detection
    pos_change = pos.diff().fillna(pos.iloc[0]).astype(int)
    cost_per_leg = (fee_bps + slippage_bps) / 10_000.0
    # Charge transaction cost on day of position change
    trade_costs = pos_change.abs() * cost_per_leg
    strat_ret = strat_ret - trade_costs

    equity = initial_cash * (1 + strat_ret).cumprod()

    trades = _extract_trades(df, pos, exec_price)

    metrics = _metrics(strat_ret, equity)
    return BacktestResult(
        equity=equity, returns=strat_ret, positions=pos, trades=trades, metrics=metrics
    )


def _extract_trades(
    prices: pd.DataFrame, pos: pd.Series, exec_price: pd.Series
) -> pd.DataFrame:
    rows = []
    in_trade = False
    entry_idx = None
    entry_px = None
    for ts, p in pos.items():
        if p == 1 and not in_trade:
            in_trade = True
            entry_idx = ts
            entry_px = float(exec_price.loc[ts])
        elif p == 0 and in_trade:
            exit_px = float(exec_price.loc[ts])
            rows.append(
                {
                    "entry_date": entry_idx,
                    "exit_date": ts,
                    "entry_price": entry_px,
                    "exit_price": exit_px,
                    "return": exit_px / entry_px - 1.0,
                    "bars": (ts - entry_idx).days,
                }
            )
            in_trade = False
    if in_trade and entry_idx is not None:
        last_ts = pos.index[-1]
        last_px = float(prices["close"].iloc[-1])
        rows.append(
            {
                "entry_date": entry_idx,
                "exit_date": last_ts,
                "entry_price": entry_px,
                "exit_price": last_px,
                "return": last_px / entry_px - 1.0,
                "bars": (last_ts - entry_idx).days,
                "open": True,
            }
        )
    return pd.DataFrame(rows)


def _metrics(rets: pd.Series, equity: pd.Series) -> dict[str, float]:
    if rets.empty:
        return {}
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    n = len(rets)
    years = n / TRADING_DAYS if n else 1.0
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    vol = float(rets.std() * np.sqrt(TRADING_DAYS))
    sharpe = float(rets.mean() / rets.std() * np.sqrt(TRADING_DAYS)) if rets.std() else 0.0
    cum = (1 + rets).cumprod()
    dd = cum / cum.cummax() - 1
    max_dd = float(dd.min())
    win_rate = float((rets[rets != 0] > 0).mean()) if (rets != 0).any() else 0.0
    return {
        "total_return": total_return,
        "cagr": cagr,
        "annual_vol": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "win_rate_daily": win_rate,
        "bars": float(n),
    }


# -------- preset signal functions --------

def signal_sma_cross(fast: int = 50, slow: int = 200) -> SignalFn:
    """Long when fast SMA > slow SMA."""

    def _s(df: pd.DataFrame) -> pd.Series:
        f = technical.sma(df, fast)
        s = technical.sma(df, slow)
        return (f > s).astype(int)

    return _s


def signal_rsi_reversion(buy: float = 30, sell: float = 55, window: int = 14) -> SignalFn:
    """Buy when RSI < buy, hold until RSI > sell."""

    def _s(df: pd.DataFrame) -> pd.Series:
        r = technical.rsi(df, window)
        out = pd.Series(0, index=df.index, dtype=int)
        holding = False
        for i, v in enumerate(r):
            if not holding and pd.notna(v) and v < buy:
                holding = True
            elif holding and pd.notna(v) and v > sell:
                holding = False
            out.iloc[i] = 1 if holding else 0
        return out

    return _s


def signal_macd_cross() -> SignalFn:
    """Long when MACD line > signal line."""

    def _s(df: pd.DataFrame) -> pd.Series:
        m = technical.macd(df)
        return (m["macd"] > m["signal"]).astype(int)

    return _s


def signal_donchian(window: int = 20) -> SignalFn:
    """Long on N-day high breakout, exit on N-day low (Turtle-style)."""

    def _s(df: pd.DataFrame) -> pd.Series:
        hi = df["high"].rolling(window).max().shift(1)
        lo = df["low"].rolling(window).min().shift(1)
        out = pd.Series(0, index=df.index, dtype=int)
        holding = False
        for i in range(len(df)):
            c = df["close"].iloc[i]
            if not holding and pd.notna(hi.iloc[i]) and c > hi.iloc[i]:
                holding = True
            elif holding and pd.notna(lo.iloc[i]) and c < lo.iloc[i]:
                holding = False
            out.iloc[i] = 1 if holding else 0
        return out

    return _s


PRESETS: dict[str, Callable[..., SignalFn]] = {
    "sma_cross": signal_sma_cross,
    "rsi_reversion": signal_rsi_reversion,
    "macd_cross": signal_macd_cross,
    "donchian": signal_donchian,
}
