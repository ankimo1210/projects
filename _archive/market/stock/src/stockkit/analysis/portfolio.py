"""Portfolio analytics: returns, vol, sharpe, drawdown, correlation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stockkit.data.providers.yfinance_provider import get_prices

TRADING_DAYS = 252


def price_panel(symbols: list[str], period: str = "5y") -> pd.DataFrame:
    """Return wide DataFrame of adj_close per symbol."""
    cols = {}
    for s in symbols:
        df = get_prices(s, period=period)
        if df.empty:
            continue
        cols[s] = df["adj_close"] if "adj_close" in df.columns else df["close"]
    if not cols:
        return pd.DataFrame()
    out = pd.concat(cols, axis=1)
    out.columns = list(cols.keys())
    return out.dropna(how="all")


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna(how="all")


def cumulative_returns(prices: pd.DataFrame) -> pd.DataFrame:
    r = daily_returns(prices).fillna(0)
    return (1 + r).cumprod() - 1


def annualized_return(prices: pd.DataFrame) -> pd.Series:
    r = daily_returns(prices)
    return (1 + r.mean()) ** TRADING_DAYS - 1


def annualized_vol(prices: pd.DataFrame) -> pd.Series:
    return daily_returns(prices).std() * np.sqrt(TRADING_DAYS)


def sharpe(prices: pd.DataFrame, rf: float = 0.0) -> pd.Series:
    er = annualized_return(prices) - rf
    vol = annualized_vol(prices).replace(0, np.nan)
    return er / vol


def max_drawdown(prices: pd.DataFrame) -> pd.Series:
    cum = (1 + daily_returns(prices).fillna(0)).cumprod()
    peak = cum.cummax()
    dd = cum / peak - 1
    return dd.min()


def correlation(prices: pd.DataFrame) -> pd.DataFrame:
    return daily_returns(prices).corr()


def summary(prices: pd.DataFrame, rf: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "annual_return": annualized_return(prices),
            "annual_vol": annualized_vol(prices),
            "sharpe": sharpe(prices, rf=rf),
            "max_drawdown": max_drawdown(prices),
        }
    )


def weighted_portfolio(prices: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """Return a synthetic portfolio price series given weights (sum to 1)."""
    if weights is None:
        n = prices.shape[1]
        weights = {c: 1.0 / n for c in prices.columns}
    w = pd.Series(weights).reindex(prices.columns).fillna(0)
    w = w / w.sum() if w.sum() != 0 else w
    r = daily_returns(prices).fillna(0)
    port_r = (r * w).sum(axis=1)
    return (1 + port_r).cumprod()
