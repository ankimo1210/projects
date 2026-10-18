"""Synthetic zero-coupon bond returns and excess returns (design §4.3).

Yields are decimal, continuously compounded and annual; maturities are integer months. A
return month p is the holding period from the end of p-1 to the end of p. A purchase month
s indexes a target whose holding period starts at the end of s.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

import numpy as np
import pandas as pd

from .data.gsw import GswCurve

TLT_MONTHS = 204  # 17 years, close to TLT's effective duration
IEF_MONTHS = 90  # 7.5 years
TEN_MONTHS = 120
INSTRUMENTS = {"tlt": TLT_MONTHS, "ief": IEF_MONTHS, "z10": TEN_MONTHS}
DURATION = {"tlt": 17.0, "ief": 7.5, "z10": 10.0}
RX_YEARS = tuple(range(2, 11))


def grid_months() -> list[int]:
    months = {m for n in range(1, 11) for m in (12 * n, 12 * n - 1)}
    months |= {IEF_MONTHS, IEF_MONTHS - 1, TLT_MONTHS, TLT_MONTHS - 1}
    return sorted(months)


def holding_log_return(zeros: pd.DataFrame, n_months: int) -> pd.Series:
    """Log return over month p of an n-month zero bought at the end of p-1 and sold at the end of p."""
    bought = zeros[n_months].shift(1) * (n_months / 12.0)
    sold = zeros[n_months - 1] * ((n_months - 1) / 12.0)
    return (bought - sold).rename(n_months)


def excess_simple(log_return: pd.Series, cash: pd.Series) -> pd.Series:
    return np.expm1(log_return) - cash


def excess_log(log_return: pd.Series, cash: pd.Series) -> pd.Series:
    return log_return - np.log1p(cash)


def rx12(zeros: pd.DataFrame, n_years: int) -> pd.Series:
    """One-year log excess return of an n-year zero bought at the end of s (the paper's target)."""
    n = n_years
    return (n * zeros[12 * n] - (n - 1) * zeros[12 * (n - 1)].shift(-12) - zeros[12]).rename(n)


def rolling_forward_sum(monthly: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
    """Value at s = sum of the monthly values of s+1 .. s+horizon."""
    return monthly.rolling(horizon).sum().shift(-horizon)


@dataclass(frozen=True)
class Outcomes:
    rx12: pd.DataFrame  # purchase month x maturity in years (2..10), log excess
    xr1: pd.Series  # purchase month: next-month log excess return of the 10-year zero
    excess: pd.DataFrame  # return month x instrument (tlt, ief, z10): simple excess over cash
    monthly_log_excess: pd.DataFrame  # return month x maturity in years (2..10)

    @property
    def rxbar(self) -> pd.Series:
        return self.rx12.mean(axis=1, skipna=False)


def real_outcomes(zeros: pd.DataFrame, cash: pd.Series) -> Outcomes:
    log_excess = pd.concat(
        {n: excess_log(holding_log_return(zeros, 12 * n), cash) for n in RX_YEARS}, axis=1
    )
    excess = pd.concat(
        {
            name: excess_simple(holding_log_return(zeros, m), cash)
            for name, m in INSTRUMENTS.items()
        },
        axis=1,
    )
    targets = pd.concat({n: rx12(zeros, n) for n in RX_YEARS}, axis=1)
    return Outcomes(targets, log_excess[10].shift(-1), excess, log_excess)


def world_outcomes(log_excess: pd.DataFrame, excess: pd.DataFrame) -> Outcomes:
    """Outcomes of a synthetic world; rx12 is the sum of the next twelve monthly log excess returns."""
    return Outcomes(
        rolling_forward_sum(log_excess, 12), log_excess[10].shift(-1), excess, log_excess
    )


def daily_synthetic_returns(curve: GswCurve, n_months: int, start: date) -> pd.Series:
    """Simple daily return of a constant-maturity n-month zero between GSW observation days."""
    days = [d for d in sorted(curve.days, key=lambda d: d.obs_date) if d.obs_date >= start]
    years = n_months / 12.0
    values, index = [], []
    for prev, day in pairwise(days):
        tau = (day.obs_date - prev.obs_date).days / 365.25
        bought = curve.zeros([prev], [n_months])[0, 0]
        sold = curve.zeros([day], [12.0 * (years - tau)])[0, 0]
        values.append(np.expm1(years * bought - (years - tau) * sold))
        index.append(pd.Timestamp(day.obs_date))
    return pd.Series(values, index=pd.DatetimeIndex(index), dtype=float)


def delayed_switch_excess(
    curve: GswCurve, n_months: int, cash: pd.Series, trading_day: int = 5
) -> pd.DataFrame:
    """Excess return of month p when a switch decided at the end of p-1 executes at the close of
    the ``trading_day``-th GSW observation day of p (design R5).

    ``in``: cash until that day, then a fresh n-month zero. ``out``: the zero bought at the end
    of p-1 until that day, then cash. Cash accrues linearly in calendar days.
    """
    ends = {pd.Period(d.obs_date, freq="M"): d for d in curve.month_ends()}
    by_month = curve.days_by_month()
    years = n_months / 12.0
    rows: dict[pd.Period, tuple[float, float]] = {}
    for p in sorted(ends):
        start, days, rf = ends.get(p - 1), by_month.get(p, []), cash.get(p, np.nan)
        if start is None or len(days) <= trading_day or not np.isfinite(rf):
            continue
        end, switch = ends[p], days[trading_day - 1]
        t_old = (switch.obs_date - start.obs_date).days / 365.25
        t_new = (end.obs_date - switch.obs_date).days / 365.25
        bought = curve.zeros([start], [n_months])[0, 0]
        aged, fresh = curve.zeros([switch], [12.0 * (years - t_old), n_months])[0]
        sold = curve.zeros([end], [12.0 * (years - t_new)])[0, 0]
        old_leg = years * bought - (years - t_old) * aged
        new_leg = years * fresh - (years - t_new) * sold
        share = t_old / (t_old + t_new)
        out_total = np.exp(old_leg) * (1.0 + rf * (1.0 - share)) - 1.0
        in_total = (1.0 + rf * share) * np.exp(new_leg) - 1.0
        rows[p] = (in_total - rf, out_total - rf)
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=["in", "out"])
    frame.index = pd.PeriodIndex(frame.index, freq="M")
    return frame
