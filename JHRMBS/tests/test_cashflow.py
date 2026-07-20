from __future__ import annotations

from datetime import date

import pytest
from jhrmbs.cashflow import CashflowAssumptions, CashflowPoint, generate_cashflows
from jhrmbs.risk import risk_summary


def test_cashflow_applies_schedule_then_prepayment() -> None:
    assumptions = CashflowAssumptions(
        face_amount=100.0,
        coupon_rate=0.12,
        current_factor=1.0,
        current_scheduled_factor=1.0,
    )
    rows = generate_cashflows(
        assumptions,
        [
            CashflowPoint(date(2026, 2, 1), 0.9, 0.0),
            CashflowPoint(date(2026, 3, 1), 0.8, 0.0),
        ],
    )
    assert rows[0].scheduled_principal == pytest.approx(10.0)
    assert rows[0].interest == pytest.approx(1.0)
    assert rows[1].scheduled_principal == pytest.approx(10.0)
    assert rows[1].ending_balance == pytest.approx(80.0)


def test_cleanup_lag_continues_normal_amortization_until_exercise() -> None:
    assumptions = CashflowAssumptions(
        face_amount=100.0,
        coupon_rate=0.0,
        current_factor=1.0,
        current_scheduled_factor=1.0,
        cleanup_threshold=0.95,
        cleanup_lag_months=2,
    )
    rows = generate_cashflows(
        assumptions,
        [
            CashflowPoint(date(2026, 2, 1), 0.9, 0.0),
            CashflowPoint(date(2026, 3, 1), 0.8, 0.0),
            CashflowPoint(date(2026, 4, 1), 0.7, 0.0),
        ],
    )
    assert rows[1].scheduled_principal == pytest.approx(10.0)
    assert rows[1].ending_balance == pytest.approx(80.0)
    assert rows[2].cleanup_exercised
    assert rows[2].cleanup_principal == pytest.approx(80.0)


def test_cleanup_is_scheduled_from_current_factor_when_already_below_threshold() -> None:
    assumptions = CashflowAssumptions(
        face_amount=100.0,
        coupon_rate=0.0,
        current_factor=0.09,
        current_scheduled_factor=0.5,
        cleanup_threshold=0.10,
        cleanup_lag_months=1,
    )
    rows = generate_cashflows(
        assumptions,
        [CashflowPoint(date(2026, 2, 1), 0.49, 0.0)],
    )
    assert rows[0].cleanup_exercised
    assert rows[0].cleanup_principal == pytest.approx(9.0)


def test_risk_summary_at_zero_yield_matches_undiscounted_cash() -> None:
    rows = generate_cashflows(
        CashflowAssumptions(100.0, 0.0, 1.0, 1.0),
        [CashflowPoint(date(2027, 1, 1), 0.0, 0.0)],
    )
    summary = risk_summary(
        rows,
        valuation_date=date(2026, 1, 1),
        current_balance=100.0,
        annual_effective_yield=0.0,
    )
    assert summary["present_value_jpy"] == pytest.approx(100.0)
    assert summary["dirty_price_per_100"] == pytest.approx(100.0)
    assert summary["wal_years"] == pytest.approx(365.0 / 365.25)
