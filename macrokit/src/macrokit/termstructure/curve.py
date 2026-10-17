"""Svensson curves fitted to MoF par yields plus the overnight call rate (design §3.3).

MoF publishes semiannual-compounding yields of fixed-coupon JGBs splined across
issues; they are treated as par yields of semiannual-pay bonds. The overnight
call rate anchors the short end because MoF has nothing under one year.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
from scipy.optimize import least_squares

OVERNIGHT_T = 1.0 / 365.0
HALF_YEARS = np.arange(1, 81) / 2.0  # coupon dates up to 40 years
TAU_GRID = (0.5, 1.0, 2.0, 5.0, 10.0)
TAU_BOUNDS = (0.05, 30.0)
MAX_MONTHS = 360


def svensson_zero(params: np.ndarray, t_years: np.ndarray) -> np.ndarray:
    """Continuously compounded zero yield (annual %) at maturities ``t_years``."""
    b0, b1, b2, b3, tau1, tau2 = params
    t = np.asarray(t_years, dtype=float)
    x1 = t / tau1
    x2 = t / tau2
    f1 = -np.expm1(-x1) / x1
    f2 = -np.expm1(-x2) / x2
    return b0 + b1 * f1 + b2 * (f1 - np.exp(-x1)) + b3 * (f2 - np.exp(-x2))


def par_yields(params: np.ndarray, maturities_years: np.ndarray) -> np.ndarray:
    """Annual % coupon pricing a semiannual-pay bond at par: c = 200 (1 - P(T)) / sum P(t_i)."""
    maturities = np.asarray(maturities_years, dtype=float)
    index = np.rint(maturities * 2).astype(int) - 1
    if (np.abs((index + 1) / 2 - maturities) > 1e-9).any() or index.max() >= len(HALF_YEARS):
        raise ValueError("par_yields needs maturities that are multiples of 0.5 up to 40 years")
    disc = np.exp(-svensson_zero(params, HALF_YEARS) / 100 * HALF_YEARS)
    annuity = np.cumsum(disc)
    return 200 * (1 - disc[index]) / annuity[index]


@dataclass(frozen=True)
class CurveFit:
    obs_date: date
    params: np.ndarray
    tenors: np.ndarray
    observed: np.ndarray  # par yields, annual %
    fitted: np.ndarray
    overnight: float | None

    @property
    def errors_bp(self) -> np.ndarray:
        return (self.fitted - self.observed) * 100.0


def fit_svensson(
    tenors: np.ndarray,
    par: np.ndarray,
    overnight: float | None,
    previous: np.ndarray | None = None,
    *,
    obs_date: date,
) -> CurveFit:
    """Least-squares Svensson fit to par yields (equal weights) and the overnight point.

    Solved from the previous month's parameters and a fixed grid of (tau1, tau2)
    starts; the lowest cost wins, so the result is deterministic.
    """
    tenors = np.asarray(tenors, dtype=float)
    par = np.asarray(par, dtype=float)

    def residuals(p: np.ndarray) -> np.ndarray:
        res = par_yields(p, tenors) - par
        if overnight is not None:
            res = np.append(res, svensson_zero(p, np.array([OVERNIGHT_T]))[0] - overnight)
        return res

    level = float(par[-1])
    short = float(overnight if overnight is not None else par[0])
    starts = [] if previous is None else [np.asarray(previous, dtype=float)]
    starts += [
        np.array([level, short - level, 0.0, 0.0, tau1, tau2])
        for tau1 in TAU_GRID
        for tau2 in TAU_GRID
        if tau2 > tau1
    ]
    lower = [-np.inf] * 4 + [TAU_BOUNDS[0]] * 2
    upper = [np.inf] * 4 + [TAU_BOUNDS[1]] * 2
    best = None
    for x0 in starts:
        x0 = np.clip(x0, lower, upper)
        sol = least_squares(residuals, x0, bounds=(lower, upper), x_scale="jac", max_nfev=2000)
        if best is None or sol.cost < best.cost:
            best = sol
    return CurveFit(obs_date, best.x, tenors, par, par_yields(best.x, tenors), overnight)


def overnight_at(con: duckdb.DuckDBPyConnection, day: date) -> float | None:
    """Last daily call rate on or before ``day`` in the same month, else that month's average."""
    first = day.replace(day=1)
    row = con.execute(
        "SELECT yield_pct FROM market_rates WHERE curve = 'jp_call_on' "
        "AND obs_date <= ? AND obs_date >= ? ORDER BY obs_date DESC LIMIT 1",
        [day, first],
    ).fetchone()
    if row is not None:
        return float(row[0])
    row = con.execute(
        "SELECT yield_pct FROM market_rates WHERE curve = 'jp_call_on_mavg' AND obs_date = ?",
        [first],
    ).fetchone()
    return None if row is None else float(row[0])


def fit_month_ends(con: duckdb.DuckDBPyConnection, start: date, end: date) -> list[CurveFit]:
    """One fit per calendar month: the last day in the month that has JGB rows."""
    rows = con.execute(
        "SELECT obs_date, tenor_y, yield_pct FROM market_rates WHERE curve = 'jgb' "
        "AND obs_date BETWEEN ? AND ? ORDER BY obs_date, tenor_y",
        [start, end],
    ).fetchall()
    by_day: dict[date, list[tuple[float, float]]] = {}
    for obs_date, tenor, value in rows:
        by_day.setdefault(obs_date, []).append((tenor, value))
    month_end: dict[tuple[int, int], date] = {}
    for day in by_day:
        month_end[(day.year, day.month)] = day  # days arrive sorted, the last one wins
    fits: list[CurveFit] = []
    previous = None
    for day in sorted(month_end.values()):
        tenors, par = (np.array(v) for v in zip(*by_day[day], strict=True))
        fit = fit_svensson(tenors, par, overnight_at(con, day), previous, obs_date=day)
        fits.append(fit)
        previous = fit.params
    return fits


@dataclass(frozen=True)
class ZeroPanel:
    dates: tuple[date, ...]
    months: np.ndarray  # 1..M, contiguous
    yields: np.ndarray  # (T, M) continuously compounded annual %

    def __post_init__(self) -> None:
        if not np.array_equal(self.months, np.arange(1, len(self.months) + 1)):
            raise ValueError("ZeroPanel.months must be 1..M")
        if self.yields.shape != (len(self.dates), len(self.months)):
            raise ValueError("ZeroPanel.yields must be (len(dates), len(months))")

    def column(self, n: int) -> np.ndarray:
        return self.yields[:, n - 1]

    def columns(self, ns: np.ndarray) -> np.ndarray:
        return self.yields[:, np.asarray(ns) - 1]

    def window(self, start: date, end: date) -> ZeroPanel:
        keep = [i for i, d in enumerate(self.dates) if start <= d <= end]
        return ZeroPanel(tuple(self.dates[i] for i in keep), self.months, self.yields[keep])


def zero_panel(fits: Sequence[CurveFit], max_months: int = MAX_MONTHS) -> ZeroPanel:
    months = np.arange(1, max_months + 1)
    yields = np.vstack([svensson_zero(f.params, months / 12.0) for f in fits])
    return ZeroPanel(tuple(f.obs_date for f in fits), months, yields)


def month_ends(n: int, start_year: int = 2000) -> tuple[date, ...]:
    """Calendar month-ends for synthetic panels (n months from January ``start_year``)."""
    out = []
    for i in range(n):
        year, month = start_year + i // 12, i % 12 + 1
        out.append(date(year, month, calendar.monthrange(year, month)[1]))
    return tuple(out)
