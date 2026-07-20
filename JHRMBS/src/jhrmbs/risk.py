from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import numpy as np

from jhrmbs.cashflow import CashflowRow


def year_fraction(start: date, end: date) -> float:
    return max((end - start).days / 365.25, 0.0)


def weighted_average_life(rows: Sequence[CashflowRow], valuation_date: date) -> float:
    principal = np.asarray([row.total_principal for row in rows], dtype=float)
    if principal.sum() <= 0.0:
        return float("nan")
    times = np.asarray([year_fraction(valuation_date, row.payment_date) for row in rows])
    return float(times @ principal / principal.sum())


def present_value(
    rows: Sequence[CashflowRow],
    valuation_date: date,
    annual_effective_yield: float,
) -> float:
    if annual_effective_yield <= -1.0:
        raise ValueError("annual effective yield must be greater than -100%")
    times = np.asarray([year_fraction(valuation_date, row.payment_date) for row in rows])
    cashflows = np.asarray([row.total_cashflow for row in rows], dtype=float)
    return float(cashflows @ np.power(1.0 + annual_effective_yield, -times))


def risk_summary(
    rows: Sequence[CashflowRow],
    *,
    valuation_date: date,
    current_balance: float,
    annual_effective_yield: float,
    shift_basis_points: float = 1.0,
) -> dict[str, float]:
    if not rows:
        raise ValueError("cashflow rows are empty")
    if current_balance <= 0.0:
        raise ValueError("current_balance must be positive")
    shift = shift_basis_points / 10_000.0
    base = present_value(rows, valuation_date, annual_effective_yield)
    up = present_value(rows, valuation_date, annual_effective_yield + shift)
    down = present_value(rows, valuation_date, annual_effective_yield - shift)
    times = np.asarray([year_fraction(valuation_date, row.payment_date) for row in rows])
    cashflows = np.asarray([row.total_cashflow for row in rows], dtype=float)
    discounted = cashflows * np.power(1.0 + annual_effective_yield, -times)
    macaulay = float(times @ discounted / discounted.sum()) if discounted.sum() else float("nan")
    effective_duration = -(up - down) / (2.0 * base * shift)
    convexity = (up + down - 2.0 * base) / (base * shift * shift)
    principal_dates = [row.payment_date for row in rows if row.total_principal > 1e-8]
    final_maturity = (
        year_fraction(valuation_date, max(principal_dates)) if principal_dates else float("nan")
    )
    return {
        "current_balance_jpy": current_balance,
        "wal_years": weighted_average_life(rows, valuation_date),
        "final_principal_maturity_years": final_maturity,
        "present_value_jpy": base,
        "dirty_price_per_100": base / current_balance * 100.0,
        "macaulay_duration_years": macaulay,
        "effective_duration_years": effective_duration,
        "convexity": convexity,
        "annual_effective_yield_pct": annual_effective_yield * 100.0,
        "parallel_shift_basis_points": shift_basis_points,
        "total_principal_jpy": float(sum(row.total_principal for row in rows)),
        "total_interest_jpy": float(sum(row.interest for row in rows)),
    }
