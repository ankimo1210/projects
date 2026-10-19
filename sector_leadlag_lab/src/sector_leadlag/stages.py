"""Shared builders of the stages: the signal of a pairing, the baskets and the strategies.

Every stage runner takes ``(study, prior)`` and returns a JSON-ready dict; ``prior`` holds the
results of the stages it depends on (see ``cli.REQUIRES``).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import (
    Spec,
    full_correlation,
    lead_lag_signal,
    long_short,
    prior_subspace,
    target,
)
from .strategy import CAPITAL, TOP, CashLong, cash_long, long_short_returns, selection_spread
from .study import Study
from .timing import pair_rows

SCALE = 1e-4  # coefficients are reported in units of 1e-4, as in the decay paper
MIN_DAYS = 5  # a period with fewer days gets no regression


def cut(frame, period):
    return frame.loc[period[0] : period[1]]


def build_signal(
    study: Study,
    variant: str,
    *,
    us_ret: pd.DataFrame | None = None,
    jp_c2c: pd.DataFrame | None = None,
    spec: Spec = Spec(),
) -> pd.DataFrame:
    """ẑ_J for every Japanese day with a full window, under one pairing (design §5.2, §6)."""
    us_ret = study.us_returns() if us_ret is None else us_ret
    jp_c2c = study.etf_c2c() if jp_c2c is None else jp_c2c
    rows = pair_rows(variant, us_ret, jp_c2c, study.s_map)
    c_full, _ = full_correlation(rows)
    c0 = target(c_full, prior_subspace(rows.us_names, rows.jp_names))
    return lead_lag_signal(rows, us_ret, study.s_map, c0, study.jp_days, spec)


@dataclass(frozen=True)
class Returns:
    """Per-sector returns of one price series."""

    o2c: pd.DataFrame
    c2o: pd.DataFrame
    c2c: pd.DataFrame


def etf_returns(study: Study) -> Returns:
    p = study.etf
    return Returns(bk.open_to_close(p), bk.close_to_open(p), bk.close_to_close(p))


def basket_series(study: Study, weights: pd.DataFrame) -> Returns:
    p, sector = study.stocks, study.stocks.sector
    parts = (bk.open_to_close(p), bk.close_to_open(p), bk.close_to_close(p))
    return Returns(*(bk.basket_returns(weights, r, sector) for r in parts))


@dataclass(frozen=True)
class Baskets:
    median: pd.DataFrame  # trailing median traded value of every name (design §7.1)
    main: pd.DataFrame  # H1: all names, weighted by the median
    top10: pd.DataFrame  # H1 secondary: the 10 most traded names, equal weights


def h1_baskets(study: Study) -> Baskets:
    median = bk.trailing_value(study.stocks)
    sector = study.stocks.sector
    return Baskets(
        median, bk.liquidity_weights(median, sector), bk.top_equal_weights(median, sector)
    )


def etf_long_short(signal: pd.DataFrame, study: Study, returns: pd.DataFrame) -> pd.Series:
    """The paper's long-short on the ETFs that traded that day."""
    return long_short_returns(long_short(signal, bk.traded(study.etf)), returns)


def basket_long_short(signal: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """The same long-short on the baskets; every sector can be chosen (design §6)."""
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    return long_short_returns(long_short(signal, available), returns)


def fit_summary(fit: ev.PanelFit) -> dict:
    return {
        "beta_1e4": fit.beta[0] / SCALE,
        "se_1e4": fit.se[0] / SCALE,
        "t": fit.t,
        "p": fit.p,
        "obs": fit.n_obs,
        "days": fit.n_days,
    }


def fit_in(returns: pd.DataFrame, sz: pd.DataFrame, period, controls=()) -> dict | None:
    """The panel regression over ``period``, or None when it has too few days."""
    y, x = cut(returns, period), cut(sz, period)
    days = y.index.intersection(x.index)
    if len(days) < MIN_DAYS:
        return None
    return fit_summary(ev.panel_fit(y, x, [cut(c, period) for c in controls]))


def h2_series(
    study: Study,
    signal: pd.DataFrame,
    median: pd.DataFrame,
    *,
    capital: float = CAPITAL,
    cost_bp: float = 0.0,
) -> tuple[CashLong, pd.Series]:
    """H2 1 (the cash-only strategy) and H2 2 (the selection spread) on the days of ``signal``."""
    p, sector = study.stocks, study.stocks.sector
    quoted_open, quoted_close = bk.quoted(p)
    budget = capital / (TOP * bk.PER_SECTOR)
    picks = bk.h2_picks(median, quoted_close, sector, budget)
    cash = cash_long(
        signal,
        picks,
        quoted_open,
        quoted_close,
        bk.traded(p),
        sector,
        capital=capital,
        cost_bp=cost_bp,
    )
    pick_returns = bk.basket_returns(picks.astype(float), bk.open_to_close(p), sector)
    return cash, selection_spread(signal, pick_returns)


def cash_summary(cash: CashLong) -> dict:
    return {
        **ev.describe(cash.returns),
        "mean_names": float(cash.names.mean()) if len(cash.names) else 0.0,
        "invested": float(cash.invested.mean()) if len(cash.invested) else 0.0,
    }
