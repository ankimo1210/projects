"""Portfolio returns: the paper's long-short and the cash-only long version (design §3.1, §7.2)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .baskets import LOT, PER_SECTOR
from .signal import top_sectors

TOP = 5
CAPITAL = 5_000_000.0


def long_short_returns(weights: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """The sum of w_{j,d} r_{j,d} on each day with a signal; a day without positions earns 0."""
    r = returns.reindex(index=weights.index, columns=weights.columns)
    return (weights * r).where(weights != 0).sum(axis=1)


@dataclass(frozen=True)
class CashLong:
    returns: pd.Series  # profit and loss over the capital, after costs
    names: pd.Series  # names bought at the open
    invested: pd.Series  # money paid at the open over the capital


def cash_long(
    signal: pd.DataFrame,
    picks: pd.DataFrame,
    quoted_open: pd.DataFrame,
    quoted_close: pd.DataFrame,
    traded: pd.DataFrame,
    sector: pd.Series,
    *,
    capital: float = CAPITAL,
    cost_bp: float = 0.0,
    top: int = TOP,
    per_sector: int = PER_SECTOR,
) -> CashLong:
    """Buy the picks of the top sectors at the open, sell them at the close (design §3.1, §7.2).

    Each name gets capital / (top x per_sector); shares are that budget over 100 x the previous
    quoted close, rounded down to whole lots. Costs are ``cost_bp`` of the traded value on the
    buy and on the sell. Unspent money earns nothing.
    """
    days = signal.index
    budget = capital / (top * per_sector)
    columns = picks.columns
    codes = sector.reindex(columns).to_numpy()
    chosen = top_sectors(signal, top).to_numpy()[:, codes - 1]
    hold = (
        picks.reindex(index=days, columns=columns, fill_value=False).to_numpy(dtype=bool)
        & chosen
        & traded.reindex(index=days, columns=columns, fill_value=False).to_numpy(dtype=bool)
    )
    previous = quoted_close.shift(1).reindex(index=days, columns=columns).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        lots = np.floor(budget / (LOT * previous))
    shares = np.where(hold & np.isfinite(lots), lots * LOT, 0.0)
    o = quoted_open.reindex(index=days, columns=columns).to_numpy()
    c = quoted_close.reindex(index=days, columns=columns).to_numpy()
    cost = cost_bp / 1e4
    pnl = np.where(shares > 0, shares * (c - o) - cost * shares * (o + c), 0.0)
    paid = np.where(shares > 0, shares * o, 0.0)
    return CashLong(
        pd.Series(pnl.sum(axis=1) / capital, index=days),
        pd.Series((shares > 0).sum(axis=1), index=days),
        pd.Series(paid.sum(axis=1) / capital, index=days),
    )


def selection_spread(signal: pd.DataFrame, pick_returns: pd.DataFrame, top: int = TOP) -> pd.Series:
    """H2 2: the top sectors' pick baskets minus all 17 (equal weights, no lots, no costs)."""
    chosen = top_sectors(signal, top)
    r = pick_returns.reindex(index=signal.index, columns=signal.columns)
    return (r.where(chosen).mean(axis=1) - r.mean(axis=1)).dropna()
