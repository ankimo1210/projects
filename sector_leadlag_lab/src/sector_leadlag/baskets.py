"""Sector baskets of stocks, their weights and returns (design §7).

Prices come from yfinance with splits adjusted (``data.yf``), so close times volume is the traded
value, and same-day ratios such as open-to-close need no adjustment. Share counts for the H2
strategy need the prices that were actually quoted, so ``quoted`` undoes the split adjustment.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import pit

LOOKBACK = 60
TOP_SECONDARY = 10
PER_SECTOR = 3
LOT = 100
SECTORS = tuple(range(1, 18))


@dataclass(frozen=True)
class Panel:
    """Daily data on the Japanese trading days; one column per stock (or per ETF sector)."""

    open: pd.DataFrame
    close: pd.DataFrame
    adj_close: pd.DataFrame
    volume: pd.DataFrame
    dividends: pd.DataFrame
    splits: pd.DataFrame
    sector: pd.Series  # column -> sector code 1-17

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> Panel:
        rows = slice(start, end)
        return Panel(
            self.open.loc[rows],
            self.close.loc[rows],
            self.adj_close.loc[rows],
            self.volume.loc[rows],
            self.dividends.loc[rows],
            self.splits.loc[rows],
            self.sector,
        )


def traded(panel: Panel) -> pd.DataFrame:
    return panel.volume.fillna(0.0) > 0


def open_to_close(panel: Panel) -> pd.DataFrame:
    return (panel.close / panel.open - 1.0).where(traded(panel))


def close_to_open(panel: Panel) -> pd.DataFrame:
    """Overnight: today's open plus a dividend going ex today, over the previous close."""
    previous = panel.close.shift(1)
    return ((panel.open + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def close_to_close(panel: Panel) -> pd.DataFrame:
    previous = panel.close.shift(1)
    return ((panel.close + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def price_close_to_close(panel: Panel) -> pd.DataFrame:
    """Close over the previous close, without the dividend: how a price index moves (design §9)."""
    return (panel.close / panel.close.shift(1) - 1.0).where(traded(panel))


def quoted(panel: Panel) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open and close as quoted on the day: yfinance's backward split adjustment undone."""
    ratio = panel.splits.where(panel.splits > 0, 1.0).fillna(1.0)
    after = ratio.iloc[::-1].cumprod().iloc[::-1].shift(-1, fill_value=1.0)
    return panel.open * after, panel.close * after


def trailing_value(panel: Panel, lookback: int = LOOKBACK) -> pd.DataFrame:
    """Median traded value over the ``lookback`` trading days before each day (R2)."""
    value = panel.close * panel.volume.fillna(0.0)
    median = value.rolling(lookback, min_periods=lookback).median().shift(1)
    dates = value.index.to_series()
    pit.check_lookback(pd.Series(dates.shift(1).to_numpy(), index=value.index))
    return median


def _sector_totals(frame: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """Per-day sums of the columns of each sector, spread back onto the columns."""
    codes = sector.reindex(frame.columns).to_numpy()
    totals = frame.T.groupby(codes).sum().T
    return pd.DataFrame(
        totals.reindex(columns=codes).to_numpy(), index=frame.index, columns=frame.columns
    )


def liquidity_weights(median: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """H1 main basket: every name, weighted by its trailing median traded value (§7.1)."""
    value = median.where(median > 0).fillna(0.0)
    totals = _sector_totals(value, sector)
    return (value / totals.where(totals > 0)).fillna(0.0)


def _rank_in_sector(score: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    codes = sector.reindex(score.columns).to_numpy()
    return score.T.groupby(codes).rank(ascending=False, method="first").T


def top_equal_weights(
    median: pd.DataFrame, sector: pd.Series, n: int = TOP_SECONDARY
) -> pd.DataFrame:
    """H1 secondary basket: the n most traded names of each sector, equally weighted (§7.1)."""
    chosen = (_rank_in_sector(median.where(median > 0), sector) <= n).astype(float)
    totals = _sector_totals(chosen, sector)
    return (chosen / totals.where(totals > 0)).fillna(0.0)


def h2_picks(
    median: pd.DataFrame,
    quoted_close: pd.DataFrame,
    sector: pd.Series,
    budget: float,
    per_sector: int = PER_SECTOR,
) -> pd.DataFrame:
    """H2: per sector, the most traded names whose 100-share lot fits the budget (§7.2).

    The lot is priced at the previous day's quoted close, so the picks of day d use d-1 only.
    """
    previous = quoted_close.shift(1)
    affordable = (previous * LOT <= budget) & (median > 0)
    rank = _rank_in_sector(median.where(affordable), sector)
    return rank <= per_sector


def basket_returns(weights: pd.DataFrame, returns: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """Weighted mean return of each sector's names that traded; weights renormalised to 1."""
    weights = weights.reindex(index=returns.index, columns=returns.columns, fill_value=0.0)
    live = weights.where(returns.notna() & (weights > 0), 0.0)
    codes = sector.reindex(returns.columns).to_numpy()
    num = (live * returns.fillna(0.0)).T.groupby(codes).sum().T
    den = live.T.groupby(codes).sum().T
    out = num / den.where(den > 0)
    return out.reindex(columns=list(SECTORS))
